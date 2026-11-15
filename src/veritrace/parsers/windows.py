"""Source-derived CSV contracts. Real executable/sample validation is separate."""
import csv
import struct
import uuid
from pathlib import Path

from ..cases.registry import sha256_file
from ..errors import ParserError
from ..evidence.models import EvidenceRecord, SourceLocator, stable_record_id
from ..evidence.time import native_time
from .base import CoverageEntry, ExtractionResult
from .runner import ParserRunner


MAPPINGS = {
    "lnk": {"tool": "LECmd", "source": "SourceFile", "required": {"SourceFile", "TargetCreated", "TargetModified", "TargetAccessed"}, "target": ("LocalPath", "TargetIDAbsolutePath", "RelativePath"), "times": {"TargetCreated": "target_file_created", "TargetModified": "target_file_modified", "TargetAccessed": "target_file_accessed", "TrackerCreatedOn": "tracker_created"}},
    "jumplist": {"tool": "JLECmd", "source": "SourceFile", "required": {"SourceFile"}, "target": ("Path", "LocalPath", "TargetIDAbsolutePath", "RelativePath"), "times": {"CreationTime": "jumplist_creation_time", "LastModified": "destlist_entry_modified", "TargetCreated": "target_file_created", "TargetModified": "target_file_modified", "TargetAccessed": "target_file_accessed"}},
    "prefetch": {"tool": "PECmd", "source": "SourceFilename", "required": {"SourceFilename", "ExecutableName", "LastRun", "ParsingError"}, "target": ("ExecutableName",), "times": {field: "prefetch_" + field for field in ("LastRun", *[f"PreviousRun{i}" for i in range(7)])}},
    "recyclebin": {"tool": "RBCmd", "source": "SourceName", "required": {"SourceName", "FileName", "FileType", "DeletedOn", "FileSize"}, "target": ("FileName",), "times": {"DeletedOn": "recycle_bin_deletion"}},
}


def is_prefetch_timeline(headers):
    """PECmd's *_Timeline.csv: RunTime + ExecutableName, never the main export's LastRun.

    PECmd 2026.10.3.0 added SourceFilename and PathValidated to the timeline,
    so match on the defining columns instead of the exact older two-column set.
    """
    return {"ExecutableName", "RunTime"}.issubset(headers) and "LastRun" not in headers


def empty_custom_destinations(source):
    """Recognize only a complete v2 known-category container with no stored entries."""
    if not source.name.casefold().endswith(".customdestinations-ms") or source.stat().st_size != 24:
        return False
    version, categories, reserved, category_type, _, footer = struct.unpack("<6I", source.read_bytes())
    return (version, categories, reserved, category_type, footer) == (2, 1, 0, 1, 0xBABFFBAB)


class WindowsCsvAdapter:
    def __init__(self, family, command, version, config_sha256, *, runner=None):
        self.family, self.command = family, command
        self.mapping = MAPPINGS[family]
        self.identity = {"name": self.mapping["tool"], "version": version, "config_sha256": config_sha256, "normalization": "zimmerman-csv-source-v1", "datetime_format": "o"}
        self.runner = runner or ParserRunner(version=version, config_sha256=config_sha256)

    def extract(self, case, items):
        records, coverage = [], []
        for item in items:
            try:
                output = case.working_root / "raw" / self.family / f"{item.item_id}-{uuid.uuid4().hex[:8]}"
                source = case.working_root / "evidence" / item.acquired_path
                self.runner.run([*self.command, "-f", str(source), "--csv", str(output), "--csvf", "export.csv", "--dt", "o"], output)
                local = self.read_exports(case, item, source, output)
                records.extend(local)
                coverage.append(CoverageEntry(item_id=item.item_id, family=self.family, status="parsed" if local else "parsed-with-no-records", record_count=len(local)))
            except (ParserError, ValueError, OSError) as exc:
                coverage.append(CoverageEntry(item_id=item.item_id, family=self.family, status="failed", error_code=getattr(exc, "code", "parser_schema"), reason=str(exc)))
        return ExtractionResult(records=records, coverage=coverage)

    def read_exports(self, case, item, source, output):
        files = sorted(output.glob("*.csv"))
        records, recognized = [], 0
        for path in files:
            digest = sha256_file(path)
            with path.open(encoding="utf-8-sig", newline="") as stream:
                reader = csv.DictReader(stream)
                headers = set(reader.fieldnames or [])
                if self.family == "prefetch" and is_prefetch_timeline(headers):
                    continue  # Separate PECmd timeline; runtime slots come from its full CSV.
                if not self.mapping["required"].issubset(headers):
                    raise ParserError("Unsupported CSV schema; no guessed fields")
                if self.family == "jumplist" and not ({"EntryNumber", "Path"}.issubset(headers) or {"EntryName", "LocalPath"}.issubset(headers)):
                    raise ParserError("Unsupported automatic/custom Jump List schema")
                recognized += 1
                previous_line = reader.line_num
                for number, row in enumerate(reader, 1):
                    start_line, previous_line = previous_line + 1, reader.line_num
                    reported = row.get(self.mapping["source"])
                    if not reported or Path(reported).name.casefold() != source.name.casefold() or Path(reported).is_absolute() and Path(reported).resolve() != source.resolve():
                        raise ParserError("CSV row identifies a different source file")
                    if self.family == "prefetch" and row.get("ParsingError", "").lower() != "false":
                        raise ParserError("PECmd reports a parsing error")
                    target = next((row.get(k) for k in self.mapping["target"] if row.get(k)), None)
                    if self.family == "jumplist" and target == row.get("Path") and target:
                        target = target.split(" ==> ", 1)[0]  # Retain the known-folder identifier; raw fields keep the parser label.
                    identity = {"source_file": item.acquired_path, "parser_item": number}
                    if self.family == "jumplist":
                        identity["entry_number" if row.get("EntryNumber") else "entry_name"] = row.get("EntryNumber") or row.get("EntryName")
                    locator = SourceLocator(kind="parser_item", identifiers=identity)
                    times = []
                    for field, role in self.mapping["times"].items():
                        if not row.get(field):
                            continue
                        if self.family == "jumplist" and field == "CreationTime" and row.get("FileBirthDroid"):
                            role = "destlist_birth_object_id_created"
                        stamp = native_time(row[field], "iso8601", role)
                        if role == "destlist_birth_object_id_created":
                            stamp = stamp.model_copy(update={"normalization_basis": "JLECmd derives CreationTime from the birth object ID UUID; this is not a recorded file interaction time."})
                        times.append(stamp)
                    limits = ["Parser item identifies the source file and export row; compare acquired samples before enabling this mapping.", "Artefact activity does not identify a human actor."]
                    row["source_file_timestamps_scope"] = "SourceCreated/SourceModified/SourceAccessed describe the parser working copy, not acquired victim filesystem metadata."
                    if self.family in ("lnk", "jumplist"):
                        limits.append("Target-file timestamps are distinct from interaction times; recent-item traces alone do not prove a PDF was read.")
                        limits.append("Parser SourceCreated/SourceModified/SourceAccessed are working-copy metadata; excluded from victim evidence timestamps.")
                    elif self.family == "prefetch":
                        limits.append("Prefetch is program-execution context; missing Prefetch does not prove non-execution.")
                    else:
                        relative = item.acquired_path
                        name = Path(relative).name
                        expected = str(Path(relative).with_name("$R" + name[2:])).replace("\\", "/") if name.startswith("$I") else None
                        supplied = any(i.acquired_path.replace("\\", "/") == expected for i in case.manifest.items) if expected else None
                        row["content_companion_supplied"] = supplied
                        limits.append(f"Recycle Bin content companion supplied: {supplied}; deletion-to-Recycle-Bin does not establish permanent deletion.")
                    records.append(EvidenceRecord(record_id=stable_record_id(case.manifest.case_id, self.family, item.calculated_sha256, locator, item_id=item.item_id), case_id=case.manifest.case_id, family=self.family, item_id=item.item_id, source_sha256=item.calculated_sha256, original_path=item.original_path, locator=locator, times=times, account=item.account, sid=item.sid, application=row.get("AppIdDescription") or row.get("ExecutableName"), target=target, parser=self.identity, raw_fields=row, raw_output_locator={"path": path.relative_to(case.working_root).as_posix(), "line": start_line, "row": number, "sha256": digest}, limitations=limits))
        if not recognized:
            if self.family == "jumplist" and not files and empty_custom_destinations(source):
                return []  # JLECmd emits no CSV for this structurally verified empty form.
            raise ParserError("Expected main CSV export is missing")
        return records
