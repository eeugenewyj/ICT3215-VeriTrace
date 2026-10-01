"""Hindsight 2026.06 History JSONL mapping, derived from pinned source.

Acquired Edge 154 compatibility still requires a victim sample comparison.
Native SQLite enrichment selects only fixed tables/columns on working copies.
"""
import json
import shutil
import sqlite3
import uuid
from pathlib import Path

from ..cases.registry import sha256_file
from ..errors import ParserError
from ..evidence.models import EvidenceRecord, SourceLocator, stable_record_id
from ..evidence.time import native_time
from .base import CoverageEntry, ExtractionResult
from .runner import ParserRunner


class EdgeAdapter:
    def __init__(self, command, version, config_sha256, *, runner=None):
        self.command = command
        self.identity = {"name": "Hindsight", "version": version, "config_sha256": config_sha256, "normalization": "edge-history-2026.06-v1"}
        self.runner = runner or ParserRunner(version=version, config_sha256=config_sha256)

    def extract(self, case, items):
        records, coverage = [], []
        for item in items:
            try:
                local = self._extract_item(case, item)
                records.extend(local)
                companions = ["Working profile uses supplied History-wal/History-shm if present; originals remain untouched"]
                coverage.append(CoverageEntry(item_id=item.item_id, family="edge_history", status="parsed" if local else "parsed-with-no-records", record_count=len(local), companion_handling=companions))
            except (ParserError, OSError, sqlite3.Error, ValueError) as exc:
                coverage.append(CoverageEntry(item_id=item.item_id, family="edge_history", status="failed", reason=str(exc), error_code=getattr(exc, "code", "parser_schema")))
        return ExtractionResult(records=records, coverage=coverage)

    def _extract_item(self, case, item):
        folder = case.working_root / "raw" / "edge" / f"{item.item_id}-{uuid.uuid4().hex[:8]}"
        profile = folder / "input"
        profile.mkdir(parents=True)
        source = case.working_root / "evidence" / item.acquired_path
        shutil.copyfile(source, profile / "History")
        companion_sources = []
        for suffix in ("-wal", "-shm"):
            relative = item.acquired_path + suffix
            companion = next((i for i in case.manifest.items if i.acquired_path == relative), None)
            if companion:
                shutil.copyfile(case.working_root / "evidence" / relative, profile / ("History" + suffix))
                companion_sources.append({"item_id": companion.item_id, "sha256": companion.calculated_sha256})
        output = folder / "output"
        prefix = output / "hindsight"
        command = [*self.command, "-i", str(profile), "-o", str(prefix), "-f", "jsonl", "--only", "history,downloads"]
        self.runner.run(command, output)
        export = prefix.with_suffix(".jsonl")
        if not export.is_file():
            raise ParserError("Hindsight did not create the required JSONL export")
        digest = sha256_file(export)
        records, types = [], set()
        uri = (profile / "History").as_uri() + "?mode=ro"
        with sqlite3.connect(uri, uri=True) as db:
            db.row_factory = sqlite3.Row
            # Preparing these fixed queries detects malformed/unsupported source schemas.
            native_visits = list(db.execute("SELECT v.id,v.url AS url_id,u.url,v.visit_time FROM visits v JOIN urls u ON v.url=u.id"))
            native_downloads = list(db.execute("SELECT * FROM downloads"))
            chains = list(db.execute("SELECT id,chain_index,url FROM downloads_url_chains ORDER BY id,chain_index"))
            for line_number, line in enumerate(export.read_text(encoding="utf-8").splitlines(), 1):
                if not line.strip():
                    continue
                raw = json.loads(line)
                dtype = raw.get("data_type")
                if dtype not in ("chrome:history:page_visited", "chrome:history:file_downloaded"):
                    raise ParserError(f"Undeclared Hindsight export type at line {line_number}: {dtype}")
                if raw.get("source_item", "History") != "History":
                    raise ParserError("Export contains a source outside the declared History database")
                types.add(dtype)
                is_visit = dtype.endswith("page_visited")
                rows = native_visits if is_visit else native_downloads
                supplied_id = raw.get("visit_id" if is_visit else "download_id")
                candidates = []
                for row in rows:
                    if supplied_id is not None and row["id"] != supplied_id:
                        continue
                    if is_visit:
                        if raw.get("url") != row["url"]:
                            continue
                        if supplied_id is None:
                            stamp = native_time(raw.get("datetime"), "iso8601", "parser_visit").normalized_utc
                            native = native_time(row["visit_time"], "webkit_microseconds", "visit").normalized_utc
                            if stamp is None or native is None or abs((stamp - native).total_seconds()) > 0.000001:
                                continue
                    else:
                        target = raw.get("target_path") or raw.get("full_path") or raw.get("current_path")
                        native_target = dict(row).get("target_path") or dict(row).get("full_path") or dict(row).get("current_path")
                        if target is None or native_target is None or target.replace("/", "\\").casefold() != native_target.replace("/", "\\").casefold():
                            continue
                        if supplied_id is None:
                            stamp = native_time(raw.get("datetime"), "iso8601", "parser_start").normalized_utc
                            native = native_time(dict(row).get("start_time"), "webkit_microseconds", "download_start").normalized_utc
                            if stamp is None or native is None or abs((stamp - native).total_seconds()) > 0.000001:
                                continue
                    candidates.append(row)
                resolution = "resolved" if len(candidates) == 1 else "ambiguous" if len(candidates) > 1 else "unresolved"
                event_role = raw.get("timestamp_desc", "Visit" if is_visit else "File Downloaded")
                identity = {"table": "visits" if is_visit else "downloads", "event_role": event_role}
                times, limitations = [], ["A browser record does not establish a human actor or that a PDF was read."]
                if resolution == "resolved":
                    row = dict(candidates[0])
                    identity["id"] = row["id"]
                    if is_visit:
                        identity["urls_id"] = row["url_id"]
                        times.append(native_time(row["visit_time"], "webkit_microseconds", "visit_time"))
                    else:
                        related = [dict(c) for c in chains if c["id"] == row["id"]]
                        identity["chain_indices"] = [c["chain_index"] for c in related]
                        raw = raw | {"native_url_chain": related}
                        for field, role in (("start_time", "download_started"), ("end_time", "download_completed"), ("last_access_time", "download_last_access")):
                            if field in row:
                                times.append(native_time(row[field], "webkit_microseconds", role))
                    raw = raw | {"native_row": row, "companion_sources": companion_sources}
                else:
                    identity.update(raw_export_line=line_number, candidate_ids=[r["id"] for r in candidates])
                    times.append(native_time(raw.get("datetime"), "iso8601", "parser_time"))
                    limitations.append("Original row identity is ambiguous/unresolved; this record is not a validated citation.")
                locator = SourceLocator(kind="sqlite", identifiers=identity, resolution=resolution)
                records.append(EvidenceRecord(record_id=stable_record_id(case.manifest.case_id, "edge_history", item.calculated_sha256, locator), case_id=case.manifest.case_id, family="edge_history", item_id=item.item_id, source_sha256=item.calculated_sha256, original_path=item.original_path, locator=locator, times=times, account=item.account, sid=item.sid, application="Edge", target=raw.get("target_path") or raw.get("full_path") or raw.get("url"), parser=self.identity, raw_fields=raw, raw_output_locator={"path": export.relative_to(case.working_root).as_posix(), "line": line_number, "sha256": digest}, limitations=limitations))
            if native_visits and "chrome:history:page_visited" not in types or native_downloads and "chrome:history:file_downloaded" not in types:
                raise ParserError("Hindsight omitted a nonempty supported source table; inspect its parser log/schema")
        return records
