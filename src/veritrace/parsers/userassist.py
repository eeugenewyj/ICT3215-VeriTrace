import csv
import re
import uuid
from pathlib import Path

from ..cases.registry import sha256_file, check_ancestors
from ..errors import DependencyError, ParserError, InputError
from ..evidence.models import EvidenceRecord, SourceLocator, stable_record_id
from ..evidence.time import native_time
from .base import CoverageEntry, ExtractionResult
from .runner import ParserRunner


class UserAssistAdapter:
    def __init__(self, command, version, config_sha256, batch_path, *, runner=None):
        self.command, self.batch_path = command, Path(batch_path)
        self.identity = {"name": "RECmd/UserAssist", "version": version, "config_sha256": config_sha256, "normalization": "userassist-plugin-0.5-v1"}
        self.runner = runner or ParserRunner(version=version, config_sha256=config_sha256)

    def extract(self, case, items):
        records, coverage = [], []
        for item in items:
            try:
                if not self.batch_path.is_file():
                    raise DependencyError("Pinned UserAssist batch configuration is missing")
                output = case.working_root / "raw/userassist" / f"{item.item_id}-{uuid.uuid4().hex[:8]}"
                source = case.working_root / "evidence" / item.acquired_path
                self.runner.run([*self.command, "-f", str(source), "--bn", str(self.batch_path), "--csv", str(output), "--csvf", "export.csv", "--dt", "o"], output)
                local = self.read_export(case, item, source, output)
                records.extend(local)
                coverage.append(CoverageEntry(item_id=item.item_id, family="userassist", status="parsed" if local else "parsed-with-no-records", record_count=len(local), companion_handling=["RECmd log replay uses supplied adjacent working-copy logs; see parser receipt for replay diagnostics."]))
            except (DependencyError, ParserError, InputError, OSError, ValueError) as exc:
                coverage.append(CoverageEntry(item_id=item.item_id, family="userassist", status="failed", error_code=getattr(exc, "code", "parser_schema"), reason=str(exc)))
        return ExtractionResult(records=records, coverage=coverage)

    def read_export(self, case, item, source, output):
        path = output / "export.csv"
        if not path.is_file():
            raise ParserError("RECmd batch CSV is missing")
        records = []
        digest = sha256_file(path)
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            required = {"HivePath", "KeyPath", "ValueName", "ValueData", "ValueData2", "ValueData3", "PluginDetailFile"}
            if not required.issubset(reader.fieldnames or []):
                raise ParserError("Unsupported RECmd batch schema")
            previous = reader.line_num
            for row in reader:
                line, previous = previous + 1, reader.line_num
                if "\\UserAssist\\" not in row["KeyPath"] or not row["KeyPath"].endswith("\\Count"):
                    raise ParserError("Batch includes sources outside UserAssist Count keys")
                if Path(row["HivePath"]).resolve() != source.resolve():
                    raise ParserError("Batch identifies another source hive")
                detail = row.get("PluginDetailFile")
                if not detail:
                    raise DependencyError("No decoded UserAssist plugin detail; generic Registry output is insufficient")
                detail_path = Path(detail) if Path(detail).is_absolute() else output / detail
                check_ancestors(detail_path)
                if not detail_path.resolve().is_relative_to(output) or not detail_path.is_file():
                    raise ParserError("Plugin detail is missing or outside controlled output")
                with detail_path.open(encoding="utf-8-sig", newline="") as details:
                    plugin_rows = list(csv.DictReader(details))
                if not any(r.get("ProgramName") == row["ValueData"] and r.get("RunCounter") for r in plugin_rows):
                    raise DependencyError("Decoded UserAssist fields cannot be corroborated in plugin detail")
                if not row["ValueData2"].startswith("Last executed: ") or not row["ValueData3"].startswith("Run count: "):
                    raise ParserError("Unsupported UserAssist decoder field format")
                raw_time = row["ValueData2"].removeprefix("Last executed: ").strip()
                normalized = native_time(raw_time.replace(" ", "T") + "Z" if raw_time else None, "iso8601", "userassist_last_execution")
                stamp = normalized.model_copy(update={"raw_value": raw_time, "normalization_basis": "RegistryPlugin.UserAssist 0.5 explicitly exports LastExecuted.ToUniversalTime(); verify pinned plugin", "raw_precision": "100 nanoseconds as exported; UTC view uses microseconds"})
                locator = SourceLocator(kind="registry_value", identifiers={"key_path": row["KeyPath"], "value_name": row["ValueName"]})
                row["plugin_detail_sha256"] = sha256_file(detail_path)
                row["raw_binary_value"] = None  # Preserved in source hive; not exported by this plugin.
                records.append(EvidenceRecord(record_id=stable_record_id(case.manifest.case_id, "userassist", item.calculated_sha256, locator), case_id=case.manifest.case_id, family="userassist", item_id=item.item_id, source_sha256=item.calculated_sha256, original_path=item.original_path, locator=locator, times=[stamp], account=item.account, sid=item.sid, application="Windows UserAssist", target=row["ValueData"], parser=self.identity, raw_fields=row, raw_output_locator={"path": path.relative_to(case.working_root).as_posix(), "line": line, "sha256": digest}, limitations=["GUI program-activity trace, not attribution to a person; counter/focus fields have plugin-specific semantics.", "Raw encoded name and original hive locator retained; binary value bytes remain in the preserved hive and are not exported by this plugin.", "Registry key last-write time is not used as an action timestamp."]))
        return records
