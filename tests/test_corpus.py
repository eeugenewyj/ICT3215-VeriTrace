import json

import pytest


def corpus_case(case_id, base_id, split):
    return {"case_id": case_id, "base_case_id": base_id, "split": split, "input_path": case_id, "claims": [{"claim_id": "claim01", "expected_status": "unverified", "action_ground_truth": {"performed": True}, "evidence_basis": "missing-only", "reviewers": ["member1", "member2"], "resolution": "agreed"}]}


def test_corpus_refuses_split_leakage_and_absence_only_contradiction(tmp_path):
    from veritrace.evaluation.corpus import load_corpus
    from veritrace.errors import InputError
    path = tmp_path / "labels.json"
    data = {"schema_version": 1, "frozen_config_sha256": "0" * 64, "cases": [corpus_case("case01", "case01", "development"), corpus_case("variant01", "case01", "held-out")]}
    path.write_text(json.dumps(data))
    with pytest.raises(InputError):
        load_corpus(path)
    data["cases"] = [corpus_case("case01", "case01", "development")]
    data["cases"][0]["claims"][0]["expected_status"] = "contradicted"
    path.write_text(json.dumps(data))
    with pytest.raises(InputError):
        load_corpus(path)


def test_corpus_requires_independent_label_review(tmp_path):
    from veritrace.evaluation.corpus import load_corpus
    from veritrace.errors import InputError
    path = tmp_path / "labels.json"
    data = {"schema_version": 1, "frozen_config_sha256": "0" * 64, "cases": [corpus_case("case01", "case01", "development")]}
    path.write_text(json.dumps(data))
    assert len(load_corpus(path).cases) == 1
    data["cases"][0]["claims"][0]["reviewers"] = ["member1", "member1"]
    path.write_text(json.dumps(data))
    with pytest.raises(InputError):
        load_corpus(path)
