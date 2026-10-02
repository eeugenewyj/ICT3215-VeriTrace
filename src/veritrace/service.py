import hashlib
import json
import time
import uuid
from pathlib import Path

from .agents.claims import extract_claims, load_prompt
from .agents.citations import validate_citations
from .agents.tools import ToolBackend, ToolLedger
from .agents.verify import verify_claims
from .cases.integrity import verify_originals
from .cases.registry import register_case, sha256_file
from .errors import DependencyError, IntegrityError, VeriTraceError
from .evidence.index import EvidenceIndex
from .parsers.base import CoverageEntry
from .parsers.edge import EdgeAdapter
from .parsers.runner import ParserRunner
from .parsers.pins import pinned_command
from .parsers.windows import WindowsCsvAdapter
from .parsers.userassist import UserAssistAdapter
from .report.models import RunResult
from .report.render import render_report
from .runtime.budget import ContextBudget
from .runtime.client import OllamaClient
from .settings import FAMILIES


class UnavailableAdapter:
    def __init__(self, family, reason):
        self.identity = {"family": family, "unavailable": reason}
    def extract(self, case, items):
        raise DependencyError(self.identity["unavailable"])


def build_adapters(settings):
    adapters = {}
    for family in settings.enabled_families:
        try:
            command = settings.parser_commands.get(family)
            path = settings.parser_profiles.get(family)
            if not command or path is None:
                raise DependencyError(f"{family}: parser command/profile not configured")
            profile = json.loads(path.read_text(encoding="utf-8"))
            if sha256_file(path) != settings.parser_config_hashes.get(family) or profile.get("version") != settings.parser_versions.get(family):
                raise DependencyError(f"{family}: parser profile/version hash does not match configuration")
            sample = profile.get("acquired_sample", {})
            if sample.get("verified") is not True or not sample.get("source_sha256") or not sample.get("comparison_record"):
                raise DependencyError(f"{family}: acquired-sample comparison not recorded")
            hashes = profile.get("command_hashes", {})
            command = pinned_command(command, hashes)
            if family == "edge_history" and profile.get("schema") == "hindsight-history-2026.06-v1":
                adapters[family] = EdgeAdapter(command, profile["version"], settings.parser_config_hashes[family], runner=ParserRunner(settings.parser_timeout_s, version=profile["version"], config_sha256=settings.parser_config_hashes[family]))
            elif family in ("lnk", "jumplist", "prefetch", "recyclebin") and profile.get("schema") == "zimmerman-csv-source-v1":
                adapters[family] = WindowsCsvAdapter(family, command, profile["version"], settings.parser_config_hashes[family], runner=ParserRunner(settings.parser_timeout_s, version=profile["version"], config_sha256=settings.parser_config_hashes[family]))
            elif family == "userassist" and profile.get("schema") == "userassist-plugin-0.5-v1":
                batch = Path(profile.get("batch_path", ""))
                if not batch.is_file() or str(batch.resolve()) not in hashes or profile.get("plugin_version") != "0.5":
                    raise DependencyError("UserAssist batch/plugin configuration not pinned")
                adapters[family] = UserAssistAdapter(command, profile["version"], settings.parser_config_hashes[family], batch, runner=ParserRunner(settings.parser_timeout_s, version=profile["version"], config_sha256=settings.parser_config_hashes[family]))
            else:
                raise DependencyError(f"{family}: validated mapping not installed")
        except (VeriTraceError, OSError, ValueError) as exc:
            adapters[family] = UnavailableAdapter(family, str(exc))
    return adapters


def pending_coverage(case, settings):
    values = [CoverageEntry(item_id=i.item_id, family=i.family, status="failed" if i.family in settings.enabled_families else "unsupported", reason="Not processed; inspect run errors" if i.family in settings.enabled_families else "Family outside enabled coverage") for i in case.manifest.items]
    present = {i.family for i in case.manifest.items}
    values.extend(CoverageEntry(family=f, status="unavailable-in-input" if f in settings.enabled_families else "unsupported", reason="No source supplied" if f in settings.enabled_families else "Family outside enabled coverage") for f in FAMILIES if f not in present)
    return values


def run_case(input_dir: Path, output_dir: Path, settings, *, client=None, budget=None, adapters=None):
    started = time.perf_counter()
    case = register_case(input_dir, output_dir)
    ledger = ToolLedger(case.working_root / "tool_calls.jsonl")
    ledger.path.touch(exist_ok=False)
    owned = client is None
    client = client or OllamaClient(settings)
    claims, assessments, records, claim_errors, errors, metadata = [], [], [], {}, [], {}
    coverage = pending_coverage(case, settings)
    with EvidenceIndex(case.working_root / "evidence.sqlite") as index:
        tools = ToolBackend(case, index, build_adapters(settings) if adapters is None else adapters, ledger)
        try:
            metadata = client.metadata()
            budget = budget or ContextBudget(settings, metadata)
            claims = extract_claims(case, client, budget)
            verification = verify_claims(case, claims, client, budget, tools)
            assessments, claim_errors = verification.assessments, verification.claim_errors
            coverage = tools.coverage
            for assessment in assessments:
                validate_citations(case, assessment, index, ledger)
            cited = sorted({record_id for a in assessments for record_id in a.cited_record_ids})
            records = [index.get(case.manifest.case_id, record_id) for record_id in cited]
            verify_originals(case)
        except IntegrityError as exc:
            assessments, records = [], []
            errors.append({"code": exc.code, "message": str(exc)})
        except VeriTraceError as exc:
            errors.append({"code": exc.code, "message": str(exc)})
        except (OSError, ValueError) as exc:
            errors.append({"code": "output_or_schema_error", "message": str(exc)})
        finally:
            if tools.extracted:
                coverage = tools.coverage
            if owned:
                client.__exit__(None, None, None)
    # Recheck originals on error paths too; compromised findings are cleared.
    try:
        verify_originals(case)
    except IntegrityError as exc:
        assessments, records = [], []
        errors.append({"code": exc.code, "message": str(exc)})
    status = "error" if errors else "partial" if claim_errors or any(c.status == "failed" for c in coverage) else "complete"
    runtime = {"case_metadata": case.manifest.model_dump(mode="json", exclude={"items"}), "model_calls": getattr(client, "calls", None), "resource_measurements": "unknown; collect host observations during the desktop benchmark", "model": metadata, "settings": settings.model_dump(mode="json"), "prompt_hashes": {name: hashlib.sha256(load_prompt(name).encode()).hexdigest() for name in ("claims", "verify")}, "duration_s": time.perf_counter() - started, "enabled_families": settings.enabled_families, "gpu_backend": "unknown; retain desktop benchmark logs", "interpretation": "Available-evidence assessment; investigator makes final decision"}
    names = ("report.html", "claims.json", "assessments.json", "coverage.json", "run.json", "tool_calls.jsonl", "evidence.sqlite", "registration.json")
    result = RunResult(run_id="run_" + uuid.uuid4().hex[:20], case_id=case.manifest.case_id, testimony=case.testimony, testimony_sha256=case.testimony_sha256, status=status, claims=claims, assessments=assessments, claim_errors=claim_errors, errors=errors, coverage=coverage, records=records, tool_receipts=ledger.entries, runtime_metadata=runtime, output_paths={n: str(case.working_root / n) for n in names})
    for name, values in (("claims", claims), ("assessments", assessments), ("coverage", coverage)):
        (case.working_root / f"{name}.json").write_text(json.dumps([v.model_dump(mode="json") for v in values], ensure_ascii=False, indent=2), encoding="utf-8")
    (case.working_root / "run.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
    render_report(result, case.working_root)
    return result
