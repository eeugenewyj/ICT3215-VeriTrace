import pytest


def test_metrics_keep_operational_errors_in_denominator():
    from veritrace.evaluation.metrics import macro_f1, classification_metrics
    truth = ["supported", "supported", "contradicted", "unverified", "inconclusive"]
    predicted = ["supported", "operational_error", "supported", "unverified", "inconclusive"]
    assert macro_f1(truth, predicted) == 0.625
    result = classification_metrics(truth, predicted)
    assert result["accuracy"] == 0.6
    assert result["operational_failure_rate"] == 0.2
    assert result["confusion"]["supported"]["operational_error"] == 1


def test_perfect_and_all_failed_macro_f1():
    from veritrace.evaluation.metrics import macro_f1
    labels = ["supported", "contradicted", "unverified", "inconclusive"]
    assert macro_f1(labels, labels) == 1.0
    assert macro_f1(labels, ["operational_error"] * 4) == 0.0
    with pytest.raises(ValueError):
        macro_f1(labels, [])
