"""Opt-in real integration; never substitutes synthetic evidence for an acquisition."""
import json
import os
from pathlib import Path

import pytest


@pytest.mark.integration
def test_acquired_case_has_real_tools_resolvable_citations_and_unchanged_originals(tmp_path):
    from veritrace.service import run_case
    from veritrace.settings import load_settings
    from veritrace.cases.models import RegisteredCase
    from veritrace.cases.integrity import verify_originals
    from veritrace.agents.tools import ToolLedger, ToolReceipt
    from veritrace.agents.citations import validate_citations
    from veritrace.evidence.index import EvidenceIndex
    case_path, config_path = os.environ.get("VERITRACE_CASE_PATH"), os.environ.get("VERITRACE_CONFIG_PATH")
    if not case_path or not config_path:
        pytest.skip("Owner must supply acquired victim case and validated local configuration")
    output = tmp_path / "acquired-run"
    settings = load_settings(Path(config_path))
    result = run_case(Path(case_path), output, settings)
    assert result.status == "complete", result.errors or result.claim_errors
    assert any(r.name == "extract_case" and r.error is None for r in result.tool_receipts)
    registered = RegisteredCase.model_validate_json((output / "registration.json").read_bytes())
    verify_originals(registered)
    for item in registered.manifest.items:
        if item.family in settings.enabled_families:
            assert any(c.item_id == item.item_id and c.status in ("parsed", "parsed-with-no-records") for c in result.coverage)
    ledger = ToolLedger(output / "tool_calls.jsonl")
    ledger.entries = [ToolReceipt.model_validate_json(line) for line in (output / "tool_calls.jsonl").read_text(encoding="utf-8").splitlines()]
    with EvidenceIndex(output / "evidence.sqlite") as index:
        for assessment in result.assessments:
            validate_citations(registered, assessment, index, ledger)
