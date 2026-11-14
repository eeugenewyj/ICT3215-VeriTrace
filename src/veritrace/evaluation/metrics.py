LABELS = ("supported", "contradicted", "unverified", "inconclusive")
PREDICTIONS = (*LABELS, "operational_error")


def classification_metrics(expected, predicted):
    if len(expected) != len(predicted) or any(e not in LABELS for e in expected) or any(p not in PREDICTIONS for p in predicted):
        raise ValueError("Metrics require aligned valid truth/prediction lists")
    confusion = {e: {p: 0 for p in PREDICTIONS} for e in LABELS}
    for e, p in zip(expected, predicted, strict=True):
        confusion[e][p] += 1
    scores = []
    for label in LABELS:
        tp = sum(e == label and p == label for e, p in zip(expected, predicted, strict=True))
        fp = sum(e != label and p == label for e, p in zip(expected, predicted, strict=True))
        fn = sum(e == label and p != label for e, p in zip(expected, predicted, strict=True))
        scores.append(0.0 if 2 * tp + fp + fn == 0 else 2 * tp / (2 * tp + fp + fn))
    count = len(expected)
    return {"count": count, "confusion": confusion, "macro_f1": sum(scores) / 4,
            "accuracy": sum(e == p for e, p in zip(expected, predicted, strict=True)) / count if count else 0.0,
            "operational_failure_rate": predicted.count("operational_error") / count if count else 0.0,
            "zero_denominator_policy": "0; no observations is not evidence of success"}


def macro_f1(expected, predicted):
    return classification_metrics(expected, predicted)["macro_f1"]
