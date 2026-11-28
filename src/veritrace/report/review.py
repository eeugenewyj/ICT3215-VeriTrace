"""Create a fresh report view from a recorded run, without model inference."""
import hashlib
import json
from pathlib import Path

from pydantic import ValidationError

from ..cases.registry import check_ancestors, sha256_file
from ..errors import InputError, IntegrityError
from .coverage import load_diagnostics, read_registration
from .models import RunResult
from .render import render_report


def regenerate_report(run_dir, output_dir, diagnostics_path=None):
    source, output = Path(run_dir).absolute(), Path(output_dir).absolute()
    check_ancestors(source)
    check_ancestors(output)
    source, output = source.resolve(), output.resolve()
    if output.exists() or source.is_relative_to(output) or output.is_relative_to(source):
        raise InputError("Choose a fresh report directory outside the recorded run")
    try:
        run_path = source / "run.json"
        check_ancestors(run_path)
        original = run_path.read_bytes()
        result = RunResult.model_validate_json(original)
        case = read_registration(source)
        if case is None or case.manifest.case_id != result.case_id:
            raise InputError("Recorded run registration is missing or belongs to another case")
        for protected_root in (case.source_root.resolve(), case.working_root.resolve()):
            if output.is_relative_to(protected_root) or protected_root.is_relative_to(output):
                raise InputError("Report output overlaps original case input or working evidence")
        diagnostics, supporting = load_diagnostics(diagnostics_path, result, case) if diagnostics_path else (None, None)
        protected = {run_path: hashlib.sha256(original).hexdigest(), source / "registration.json": sha256_file(source / "registration.json")}
        if diagnostics_path:
            protected[Path(diagnostics_path)] = sha256_file(Path(diagnostics_path))
            protected[supporting] = diagnostics.supporting_report_sha256.lower()
        output.mkdir(parents=True, exist_ok=False)
        (output / "run.json").write_bytes(original)
        (output / "registration.json").write_bytes((source / "registration.json").read_bytes())
        if diagnostics:
            (output / "coverage-diagnostics.json").write_text(diagnostics.model_dump_json(indent=2), encoding="utf-8")
            (output / "coverage-diagnostics-evidence.json").write_bytes(supporting.read_bytes())
            if sha256_file(output / "coverage-diagnostics-evidence.json") != diagnostics.supporting_report_sha256.lower():
                raise IntegrityError("Copied supporting diagnostic report hash mismatch")
        report = render_report(result, output, diagnostics=diagnostics)
        receipt = {"source_run": str(source), "source_run_sha256": protected[run_path], "report": str(report), "recorded_status": result.status, "model_inference_performed": False, "assessments_changed": False, "parser_outcomes_changed": False, "diagnostics_sha256": sha256_file(output / "coverage-diagnostics.json") if diagnostics else None}
        for path, digest in protected.items():
            if sha256_file(path) != digest:
                raise IntegrityError("Recorded run or diagnostic input changed during report generation")
        (output / "report-review.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        return receipt
    except (OSError, ValidationError) as exc:
        raise InputError(f"Cannot regenerate recorded report: {exc}") from exc
