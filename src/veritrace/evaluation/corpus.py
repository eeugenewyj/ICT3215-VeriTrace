import hashlib
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, model_validator

from ..cases.models import FrozenModel, SafeId, Sha256
from ..errors import InputError, VeriTraceError
from .metrics import classification_metrics


class Label(FrozenModel):
    claim_id: SafeId
    expected_status: Literal["supported", "contradicted", "unverified", "inconclusive"]
    action_ground_truth: dict[str, Any]
    evidence_basis: str
    reviewers: list[str]
    resolution: str
    source_sentence: str | None = None
    start: int | None = Field(default=None, ge=0)
    end: int | None = Field(default=None, ge=0)
    action: str | None = None
    target: str | None = None
    negated: bool | None = None
    atomic_index: int | None = Field(default=None, ge=0)
    known_relevant_record_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def reviewed(self):
        if len(set(self.reviewers)) < 2 or not self.resolution.strip():
            raise ValueError("Expected labels need two independent reviewers and a resolution")
        if self.expected_status == "contradicted" and self.evidence_basis == "missing-only":
            raise ValueError("Missing-only evidence cannot contradict")
        if (self.start is None) != (self.end is None) or self.start is not None and self.end <= self.start:
            raise ValueError("Invalid label source span")
        return self


class CorpusCase(FrozenModel):
    case_id: SafeId
    base_case_id: SafeId
    split: Literal["development", "held-out"]
    input_path: str
    claims: list[Label]


class Corpus(FrozenModel):
    schema_version: int = Field(default=1, ge=1, le=1)
    frozen_config_sha256: Sha256
    cases: list[CorpusCase]

    @model_validator(mode="after")
    def no_leakage(self):
        ids, splits = set(), {}
        for case in self.cases:
            if case.case_id in ids:
                raise ValueError("Duplicate corpus case ID")
            ids.add(case.case_id)
            if case.base_case_id in splits and splits[case.base_case_id] != case.split:
                raise ValueError("A base case and every variant must stay in the same split")
            splits[case.base_case_id] = case.split
            claim_ids = [c.claim_id for c in case.claims]
            if not case.claims or len(set(claim_ids)) != len(claim_ids):
                raise ValueError("Case labels must be nonempty with unique IDs")
        return self


def load_corpus(path):
    try:
        return Corpus.model_validate_json(path.read_bytes())
    except (OSError, ValueError) as exc:
        raise InputError(f"Invalid labelled corpus: {exc}") from exc


def configuration_fingerprint(settings):
    from ..agents.claims import load_prompt
    from ..cases.registry import sha256_file
    paths = [settings.budget_profile, settings.tokenizer_path, *settings.parser_profiles.values()]
    data = {"settings": settings.model_dump(mode="json"), "prompts": {n: hashlib.sha256(load_prompt(n).encode()).hexdigest() for n in ("claims", "verify")}, "prerequisite_hashes": {str(p): sha256_file(p) if p.is_file() else "missing" for p in paths if p is not None}}
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def evaluate_corpus(corpus_path, output_dir, settings, *, config_path=None):
    from ..service import run_case
    from ..cases.registry import check_ancestors
    corpus_path, output_dir = Path(corpus_path).absolute(), Path(output_dir).absolute()
    check_ancestors(corpus_path)
    check_ancestors(output_dir)
    corpus = load_corpus(corpus_path)
    if configuration_fingerprint(settings) != corpus.frozen_config_sha256.lower():
        raise InputError("Frozen evaluation configuration does not match")
    if output_dir.exists():
        raise InputError("Evaluation output already exists")
    inputs = []
    for case in corpus.cases:
        path = (corpus_path.parent / case.input_path).absolute()
        check_ancestors(path)
        inputs.append((case, path.resolve()))
    output_dir = output_dir.resolve()
    protected_files = [corpus_path, config_path, settings.budget_profile, settings.tokenizer_path, *settings.parser_profiles.values()]
    for path in protected_files:
        if path is not None:
            path = Path(path).absolute()
            check_ancestors(path)
            if path.resolve().is_relative_to(output_dir):
                raise InputError("Evaluation output overlaps configuration, prerequisite or label files")
    if any(output_dir.is_relative_to(path) or path.is_relative_to(output_dir) for _, path in inputs):
        raise InputError("Evaluation output overlaps a corpus input folder")
    if any(corpus_path.resolve().is_relative_to(path) for _, path in inputs):
        raise InputError("Ground-truth labels must be outside every agent input folder")
    if any(label.source_sentence is None or label.start is None for case in corpus.cases for label in case.claims):
        raise InputError("Executable evaluation needs exact source-span anchors; IDs alone are insufficient")
    output_dir.mkdir(parents=True, exist_ok=False)
    expected, predicted, comparisons, human_packet, cases = [], [], [], [], []
    citations, tools, source_failures = 0, 0, 0
    tool_successes, retrieved_relevant = 0, 0
    expected_relevant = sum(len(set(l.known_relevant_record_ids)) for c in corpus.cases for l in c.claims)
    for label_case, path in inputs:
        try:
            result = run_case(path, output_dir / label_case.case_id, settings)
            if result.case_id != label_case.case_id:
                raise InputError("Corpus case ID differs from input manifest")
            by_id = {a.claim_id: a for a in result.assessments}
            matched = set()
            cases.append({"case_id": label_case.case_id, "split": label_case.split, "status": result.status, "metadata": result.runtime_metadata})
            tools += len(result.tool_receipts)
            tool_successes += sum(r.error is None for r in result.tool_receipts)
            source_failures += sum(c.status == "failed" for c in result.coverage)
            for label in label_case.claims:
                matches = [c for c in result.claims if c.start == label.start and c.end == label.end and c.sentence == label.source_sentence and (label.action is None or c.action == label.action)]
                peers = [l for l in label_case.claims if l.start == label.start and l.end == label.end and l.source_sentence == label.source_sentence and (l.action is None or label.action is None or l.action == label.action)]
                if label.atomic_index is not None:
                    claim = matches[label.atomic_index] if label.atomic_index < len(matches) and sum(l.atomic_index == label.atomic_index for l in peers) == 1 else None
                else:
                    claim = matches[0] if len(matches) == 1 and len(peers) == 1 else None
                if claim and claim.claim_id in matched:
                    claim = None
                assessment = by_id.get(claim.claim_id) if claim else None
                if claim:
                    matched.add(claim.claim_id)
                verdict = assessment.status if assessment else "operational_error"
                expected.append(label.expected_status)
                predicted.append(verdict)
                returned = {i for r in result.tool_receipts if claim and r.claim_id == claim.claim_id for i in r.returned_record_ids}
                relevant = set(label.known_relevant_record_ids)
                retrieved_relevant += len(returned & relevant)
                cited = assessment.cited_record_ids if assessment else []
                citations += len(cited)
                human_packet.extend({"case_id": label_case.case_id, "label_claim_id": label.claim_id, "generated_claim_id": claim.claim_id, "record_id": i, "relevant": None, "sufficient": None} for i in cited)
                comparisons.append({"case_id": label_case.case_id, "label_claim_id": label.claim_id, "generated_claim_id": claim.claim_id if claim else None, "expected": label.expected_status, "predicted": verdict, "target_matches": claim.target == label.target if claim and label.target is not None else None, "negation_matches": claim.negated == label.negated if claim and label.negated is not None else None})
            cases[-1]["extra_generated_claims"] = len(result.claims) - len(matched)
        except VeriTraceError as exc:
            cases.append({"case_id": label_case.case_id, "split": label_case.split, "error": exc.code, "message": str(exc)})
            expected.extend(l.expected_status for l in label_case.claims)
            predicted.extend("operational_error" for _ in label_case.claims)
            comparisons.extend({"case_id": label_case.case_id, "label_claim_id": l.claim_id, "generated_claim_id": None, "expected": l.expected_status, "predicted": "operational_error", "target_matches": None, "negation_matches": None, "error": exc.code} for l in label_case.claims)
    metrics = classification_metrics(expected, predicted)
    metrics.update(tool_calls=tools, tool_dispatch_successes=tool_successes, parser_source_failures=source_failures, cited_record_count=citations, known_relevant_retrieved=retrieved_relevant, known_relevant_total=expected_relevant, human_relevance="pending independent ratings; mechanical validity is not relevance")
    result = {"corpus_sha256": hashlib.sha256(corpus_path.read_bytes()).hexdigest(), "config_sha256": corpus.frozen_config_sha256, "metrics": metrics, "comparisons": comparisons, "cases": cases, "human_citation_review": human_packet, "alignment": "One-to-one exact source span and optional action/atomic occurrence index; unmatched/ambiguous labels count as operational errors. Target and negation correctness are measured separately."}
    (output_dir / "evaluation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
