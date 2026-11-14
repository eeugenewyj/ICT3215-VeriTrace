import json
import sys

import pytest


def test_runner_preserves_arguments_and_output_hashes(tmp_path):
    from veritrace.parsers.runner import ParserRunner
    special = "file with spaces & résumé"
    run = ParserRunner(timeout_s=3).run([sys.executable, "-c", "import sys,json; print(json.dumps(sys.argv[1:]))", special], tmp_path / "raw")
    assert json.loads(run.stdout_path.read_text()) == [special]
    assert run.exit_code == 0
    assert len(run.output_hashes["stdout.txt"]) == 64


@pytest.mark.parametrize("mode", ["exit", "timeout", "missing"])
def test_runner_retains_failure_receipt(tmp_path, mode):
    from veritrace.parsers.runner import ParserRunner
    from veritrace.errors import VeriTraceError
    command = [sys.executable, "-c", "raise SystemExit(3)"]
    if mode == "timeout":
        command = [sys.executable, "-c", "import time; time.sleep(10)"]
    elif mode == "missing":
        command = [str(tmp_path / "missing.exe")]
    output = tmp_path / "raw"
    with pytest.raises(VeriTraceError):
        ParserRunner(timeout_s=0.1).run(command, output)
    receipt = json.loads((output / "parser_run.json").read_text())
    assert receipt["error_code"] in ("parser_exit", "parser_timeout", "parser_missing")
