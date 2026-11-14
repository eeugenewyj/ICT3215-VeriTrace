import json


def test_evaluation_aligns_by_span_and_keeps_operational_failures(tmp_path, monkeypatch):
    from veritrace.evaluation.corpus import configuration_fingerprint, evaluate_corpus
    from veritrace.settings import Settings
    from veritrace import service
    from tests.test_corpus import corpus_case
    from tests.test_report import result
    settings = Settings()
    good = corpus_case("case01", "case01", "development")
    bad = corpus_case("case02", "case02", "held-out")
    for case in (good, bad):
        label = case["claims"][0]
        label.update(claim_id="label01", source_sentence="I downloaded report.pdf.", start=0, end=24, action="download_file", expected_status="supported", evidence_basis="positive source", target="report.pdf", negated=False)
    path = tmp_path / "labels.json"
    path.write_text(json.dumps({"schema_version": 1, "frozen_config_sha256": configuration_fingerprint(settings), "cases": [good, bad]}))
    def run_case(input_dir, output_dir, settings):
        value = result()
        if input_dir.name == "case02":
            value = value.model_copy(update={"case_id": "case02", "assessments": [], "status": "partial", "claim_errors": {"claim01": {"code": "model_error", "message": "offline"}}})
        return value
    monkeypatch.setattr(service, "run_case", run_case)
    output = tmp_path / "evaluation"
    evaluated = evaluate_corpus(path, output, settings)
    assert evaluated["metrics"]["count"] == 2
    assert evaluated["metrics"]["operational_failure_rate"] == 0.5
    assert evaluated["comparisons"][0]["generated_claim_id"] == "claim01"
    assert (output / "evaluation.json").is_file()


def test_evaluation_refuses_outputs_inside_case_inputs(tmp_path):
    import pytest
    from veritrace.evaluation.corpus import configuration_fingerprint, evaluate_corpus
    from veritrace.settings import Settings
    from veritrace.errors import InputError
    from tests.test_corpus import corpus_case
    from tests.factories import write_case
    settings = Settings()
    root = write_case(tmp_path)
    case = corpus_case("case01", "case01", "development")
    case["input_path"] = "input"
    case["claims"][0].update(source_sentence="I downloaded report.pdf.", start=0, end=24)
    labels = tmp_path / "labels.json"
    labels.write_text(json.dumps({"schema_version": 1, "frozen_config_sha256": configuration_fingerprint(settings), "cases": [case]}))
    with pytest.raises(InputError):
        evaluate_corpus(labels, root / "evaluation", settings)
    assert not (root / "evaluation").exists()


def labelled_file(tmp_path, cases, settings):
    from veritrace.evaluation.corpus import configuration_fingerprint
    path = tmp_path / "labels.json"
    for case in cases:
        for label in case["claims"]:
            label.update(source_sentence="I downloaded report.pdf.", start=0, end=24)
    path.write_text(json.dumps({"schema_version": 1, "frozen_config_sha256": configuration_fingerprint(settings), "cases": cases}))
    return path


def test_failed_case_remains_in_retrieval_denominator(tmp_path, monkeypatch):
    from veritrace import service
    from veritrace.errors import InputError
    from veritrace.evaluation.corpus import evaluate_corpus
    from veritrace.settings import Settings
    from tests.test_corpus import corpus_case
    settings = Settings()
    case = corpus_case("case01", "case01", "held-out")
    case["claims"][0]["known_relevant_record_ids"] = ["a" * 64]
    path = labelled_file(tmp_path, [case], settings)
    def fail(*args):
        raise InputError("source unavailable")
    monkeypatch.setattr(service, "run_case", fail)
    evaluated = evaluate_corpus(path, tmp_path / "evaluation", settings)
    assert evaluated["metrics"]["known_relevant_total"] == 1
    assert evaluated["metrics"]["known_relevant_retrieved"] == 0
    assert len(evaluated["comparisons"]) == 1
    assert evaluated["comparisons"][0]["predicted"] == "operational_error"


def test_atomic_labels_cannot_reuse_one_generated_prediction(tmp_path, monkeypatch):
    from veritrace import service
    from veritrace.evaluation.corpus import evaluate_corpus
    from veritrace.settings import Settings
    from tests.test_corpus import corpus_case
    from tests.test_report import result
    settings = Settings()
    case = corpus_case("case01", "case01", "held-out")
    case["claims"][0].update(expected_status="supported", evidence_basis="positive", target="report.pdf", action="download_file")
    second = dict(case["claims"][0], claim_id="claim02", target="other.pdf")
    case["claims"].append(second)
    path = labelled_file(tmp_path, [case], settings)
    monkeypatch.setattr(service, "run_case", lambda *args: result())
    evaluated = evaluate_corpus(path, tmp_path / "evaluation", settings)
    assigned = [r["generated_claim_id"] for r in evaluated["comparisons"] if r["generated_claim_id"]]
    assert len(assigned) == len(set(assigned))
    assert evaluated["metrics"]["accuracy"] < 1


def test_cross_case_overlap_is_rejected_before_any_execution(tmp_path, monkeypatch):
    import pytest
    from veritrace import service
    from veritrace.errors import InputError
    from veritrace.evaluation.corpus import evaluate_corpus
    from veritrace.settings import Settings
    from tests.test_corpus import corpus_case
    settings = Settings()
    first = corpus_case("case01", "case01", "development")
    second = corpus_case("case02", "case02", "held-out")
    second["input_path"] = "evaluation/case01"
    path = labelled_file(tmp_path, [first, second], settings)
    calls = []
    monkeypatch.setattr(service, "run_case", lambda *args: calls.append(args))
    with pytest.raises(InputError):
        evaluate_corpus(path, tmp_path / "evaluation", settings)
    assert not calls and not (tmp_path / "evaluation").exists()
