import subprocess
import time
from pathlib import Path

from ..cases.registry import sha256_file
from ..errors import ParserError
from .base import ParserRun


class ParserRunner:
    def __init__(self, timeout_s=120, *, version=None, config_sha256=None):
        self.timeout_s, self.version, self.config_sha256 = timeout_s, version, config_sha256

    def run(self, command: list[str], output_dir: Path) -> ParserRun:
        if not command or any(not isinstance(a, str) for a in command):
            raise ParserError("Parser command must be a nonempty argument array")
        output_dir.mkdir(parents=True, exist_ok=False)
        started, stdout, stderr, exit_code, error = time.perf_counter(), "", "", None, None
        try:
            process = subprocess.run(command, cwd=output_dir, shell=False, timeout=self.timeout_s, capture_output=True, text=True, encoding="utf-8", errors="replace")
            stdout, stderr, exit_code = process.stdout, process.stderr, process.returncode
            if exit_code:
                error = "parser_exit"
        except subprocess.TimeoutExpired as exc:
            stdout, stderr = exc.stdout or "", exc.stderr or ""
            error = "parser_timeout"
        except OSError as exc:
            stderr, error = str(exc), "parser_missing"
        for name, value in (("stdout.txt", stdout), ("stderr.txt", stderr)):
            if isinstance(value, bytes):
                value = value.decode("utf-8", errors="replace")
            (output_dir / name).write_text(value, encoding="utf-8")
        hashes = {p.relative_to(output_dir).as_posix(): sha256_file(p) for p in output_dir.rglob("*") if p.is_file()}
        result = ParserRun(command=command, version=self.version, config_sha256=self.config_sha256, exit_code=exit_code, duration_s=time.perf_counter() - started, stdout_path=output_dir / "stdout.txt", stderr_path=output_dir / "stderr.txt", output_hashes=hashes, error_code=error)
        (output_dir / "parser_run.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
        if error:
            failure = ParserError(f"Parser failed ({error}); see {output_dir / 'parser_run.json'}")
            failure.code, failure.receipt = error, result
            raise failure
        return result
