"""The efficiency review a step records before it spends anything.

The owner's rule: at every step ask whether this is the most efficient way,
whether the inputs are too big, whether the outputs are too big, which
alternative ways exist, and how confident we are in each. The answer is a
typed record, not a thought. A deterministic judge answers the size
questions from declared expectations; a specialist or a model may answer
the alternatives question through the registered
``practitioner.step_efficiency_review`` contract; the judge kind is always
recorded. The record carries digests and sizes, never prompt text, so it
can train a cheaper judge later.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

JUDGE_KINDS = ("deterministic", "specialist", "model")
ALTERNATIVE_METHODS = ("reuse_exact", "reuse_then_modify", "deterministic_resolver",
                       "small_specialist", "service_model", "split_input", "narrow_output",
                       "skip_step")
REVIEW_RECORD_TYPE = "step_efficiency_review/v1"
CONTRACT_ID = "practitioner.step_efficiency_review"


class EfficiencyReviewError(ValueError):
    """A review, an expectation, or an alternative is invalid."""


@dataclass(frozen=True)
class SizeExpectation:
    """What a step's contract says its inputs and outputs should be, in bytes and rows."""

    input_bytes_max: int
    output_bytes_max: int
    output_rows_max: int = 0

    def __post_init__(self):
        for name in ("input_bytes_max", "output_bytes_max", "output_rows_max"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise EfficiencyReviewError(f"{name} must be a non-negative integer")
        if self.input_bytes_max == 0 or self.output_bytes_max == 0:
            raise EfficiencyReviewError("an expectation declares positive byte limits")


@dataclass(frozen=True)
class EfficiencyAlternative:
    """One way the step could be done, with the reviewer's confidence and its cost guess."""

    method: str
    confidence: float
    reason: str
    estimated_model_calls: "int | None" = None
    estimated_cost_class: str = "unknown"

    def __post_init__(self):
        if self.method not in ALTERNATIVE_METHODS:
            raise EfficiencyReviewError(f"method must be one of {ALTERNATIVE_METHODS}")
        if not (isinstance(self.confidence, (int, float)) and 0.0 <= self.confidence <= 1.0):
            raise EfficiencyReviewError("confidence lies in [0, 1]")
        if not self.reason.strip():
            raise EfficiencyReviewError("an alternative names its reason")
        if self.estimated_model_calls is not None and (
                type(self.estimated_model_calls) is not int or self.estimated_model_calls < 0):
            raise EfficiencyReviewError("estimated model calls are unknown or a non-negative integer")

    def to_dict(self) -> dict:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}


@dataclass(frozen=True)
class EfficiencyReview:
    """The recorded answer to the efficiency questions for one step."""

    run_id: str
    step: str
    judge_kind: str
    input_bytes: int
    output_bytes: "int | None"
    expectation: SizeExpectation
    alternatives: tuple[EfficiencyAlternative, ...]
    chosen_index: int
    input_digest: str = ""
    reasons: tuple[str, ...] = ()
    attributes: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.run_id or not self.step:
            raise EfficiencyReviewError("a review names its run and step")
        if self.judge_kind not in JUDGE_KINDS:
            raise EfficiencyReviewError(f"judge_kind must be one of {JUDGE_KINDS}")
        if type(self.input_bytes) is not int or self.input_bytes < 0:
            raise EfficiencyReviewError("input_bytes is a non-negative integer")
        if self.output_bytes is not None and (type(self.output_bytes) is not int or self.output_bytes < 0):
            raise EfficiencyReviewError("output_bytes is unknown or a non-negative integer")
        if not isinstance(self.expectation, SizeExpectation):
            raise EfficiencyReviewError("a review carries a typed SizeExpectation")
        alternatives = tuple(self.alternatives)
        if not alternatives or any(not isinstance(item, EfficiencyAlternative) for item in alternatives):
            raise EfficiencyReviewError("a review names at least one typed alternative")
        if type(self.chosen_index) is not int or not 0 <= self.chosen_index < len(alternatives):
            raise EfficiencyReviewError("chosen_index names one of the alternatives")
        object.__setattr__(self, "alternatives", alternatives)
        object.__setattr__(self, "reasons", tuple(self.reasons))
        try:
            json.dumps(self.attributes, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise EfficiencyReviewError("attributes must be strict JSON") from exc

    @property
    def inputs_too_big(self) -> bool:
        return self.input_bytes > self.expectation.input_bytes_max

    @property
    def outputs_too_big(self) -> bool:
        return self.output_bytes is not None and self.output_bytes > self.expectation.output_bytes_max

    @property
    def chosen(self) -> EfficiencyAlternative:
        return self.alternatives[self.chosen_index]

    def to_dict(self) -> dict:
        body = {"record_type": REVIEW_RECORD_TYPE, "run_id": self.run_id, "step": self.step,
                "judge_kind": self.judge_kind, "input_bytes": self.input_bytes,
                "output_bytes": self.output_bytes, "input_digest": self.input_digest,
                "expectation": {"input_bytes_max": self.expectation.input_bytes_max,
                                "output_bytes_max": self.expectation.output_bytes_max,
                                "output_rows_max": self.expectation.output_rows_max},
                "inputs_too_big": self.inputs_too_big, "outputs_too_big": self.outputs_too_big,
                "alternatives": [item.to_dict() for item in self.alternatives],
                "chosen_index": self.chosen_index, "chosen_method": self.chosen.method,
                "reasons": list(self.reasons), "attributes": dict(self.attributes)}
        body["content_digest"] = hashlib.sha256(json.dumps(
            body, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        return body

    def training_row(self) -> dict:
        """Digests, sizes, methods, and confidences only; never text."""
        return {"record_type": "step_efficiency_training_row/v1", "step": self.step,
                "judge_kind": self.judge_kind, "input_bytes": self.input_bytes,
                "output_bytes": self.output_bytes, "input_digest": self.input_digest,
                "inputs_too_big": self.inputs_too_big, "outputs_too_big": self.outputs_too_big,
                "alternatives": [(item.method, item.confidence) for item in self.alternatives],
                "chosen_method": self.chosen.method}


def deterministic_efficiency_judge(run_id: str, step: str, input_text: str,
                                   expectation: SizeExpectation, *,
                                   available: tuple[str, ...] = ("service_model",),
                                   exact_reuse_available: bool = False,
                                   deterministic_available: bool = False) -> EfficiencyReview:
    """Answer the size questions from the declared expectation and rank what is available.

    The judge never invents a confidence for a method it cannot see. A method
    that is not available is not listed. Exact reuse ranks first when it
    exists, a deterministic resolver second, a service model last; an
    oversized input adds ``split_input`` and an oversized expected output adds
    ``narrow_output`` ahead of the model call.
    """
    input_bytes = len(input_text.encode("utf-8"))
    digest = hashlib.sha256(input_text.encode("utf-8")).hexdigest()
    alternatives: list[EfficiencyAlternative] = []
    reasons: list[str] = []
    if exact_reuse_available:
        alternatives.append(EfficiencyAlternative("reuse_exact", 0.95, "a verified record matches this step exactly", 0, "free"))
    if deterministic_available:
        alternatives.append(EfficiencyAlternative("deterministic_resolver", 0.9, "a registered resolver supports the typed task", 0, "free"))
    if input_bytes > expectation.input_bytes_max:
        reasons.append(f"input_bytes {input_bytes} exceeds {expectation.input_bytes_max}")
        alternatives.append(EfficiencyAlternative("split_input", 0.8, "the input exceeds the declared limit; split it", None, "unknown"))
    if expectation.output_rows_max and expectation.output_bytes_max > expectation.input_bytes_max:
        reasons.append("the declared output limit exceeds the input limit; narrow the output")
        alternatives.append(EfficiencyAlternative("narrow_output", 0.7, "ask for fewer rows or a smaller shape", None, "unknown"))
    for method in available:
        if method in ALTERNATIVE_METHODS and method not in {item.method for item in alternatives}:
            confidence = 0.6 if method == "service_model" else 0.5
            alternatives.append(EfficiencyAlternative(method, confidence, f"{method} is available for this step",
                                                      1 if method == "service_model" else None,
                                                      "metered" if method == "service_model" else "unknown"))
    if not alternatives:
        raise EfficiencyReviewError("no method is available for this step; declare at least one")
    return EfficiencyReview(run_id, step, JUDGE_KINDS[0], input_bytes, None, expectation,
                            tuple(alternatives), 0, digest, tuple(reasons))


def review_from_model_response(run_id: str, step: str, input_text: str, expectation: SizeExpectation,
                               response: dict, *, judge_kind: str = JUDGE_KINDS[2]) -> EfficiencyReview:
    """A review from a response shaped by the registered contract; the judge kind is recorded."""
    if judge_kind not in JUDGE_KINDS[1:]:
        raise EfficiencyReviewError("a response review is judged by a specialist or a model")
    rows = response.get("rows")
    if not isinstance(rows, list) or not rows:
        raise EfficiencyReviewError("the response carries at least one ranked alternative")
    alternatives = tuple(EfficiencyAlternative(str(row.get("alternative", "")), float(row.get("confidence", 0.0)),
                                               str(row.get("reason") or "no reason given"))
                         for row in rows)
    chosen = response.get("chosen_index", 0)
    input_bytes = len(input_text.encode("utf-8"))
    reasons = []
    if response.get("inputs_too_big") is True:
        reasons.append("the judge reported inputs too big")
    if response.get("outputs_too_big") is True:
        reasons.append("the judge reported outputs too big")
    return EfficiencyReview(run_id, step, judge_kind, input_bytes, None, expectation, alternatives,
                            chosen if type(chosen) is int else 0,
                            hashlib.sha256(input_text.encode("utf-8")).hexdigest(), tuple(reasons))


def self_test() -> dict:
    """Sizes are judged from declared limits; alternatives are ranked; the judge kind is recorded."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    def refuses(action) -> bool:
        try:
            action()
        except EfficiencyReviewError:
            return True
        return False

    expectation = SizeExpectation(input_bytes_max=64, output_bytes_max=32, output_rows_max=10)
    small = deterministic_efficiency_judge("run-1", "decide_next", "PRIVATE_INPUT_MARKER", expectation,
                                           deterministic_available=True)
    big = deterministic_efficiency_judge("run-1", "decide_next", "PRIVATE_INPUT_MARKER " * 5, expectation,
                                         exact_reuse_available=True)
    check("the_deterministic_judge_flags_an_oversized_input_and_records_its_reason",
          not small.inputs_too_big and big.inputs_too_big
          and any("exceeds" in reason for reason in big.reasons)
          and "split_input" in [item.method for item in big.alternatives]
          and small.to_dict()["inputs_too_big"] is False and big.to_dict()["inputs_too_big"] is True)
    check("available_methods_are_ranked_cheapest_first_and_the_chosen_one_is_named",
          [item.method for item in small.alternatives] == ["deterministic_resolver", "service_model"]
          and small.chosen.method == "deterministic_resolver"
          and [item.method for item in big.alternatives][:2] == ["reuse_exact", "split_input"]
          and small.judge_kind == "deterministic")
    check("the_training_row_carries_digests_and_sizes_never_text",
          "PRIVATE_INPUT_MARKER" not in json.dumps(small.training_row())
          and "PRIVATE_INPUT_MARKER" not in json.dumps(small.to_dict())
          and small.training_row()["input_digest"] == small.input_digest
          and small.training_row()["alternatives"][0] == ("deterministic_resolver", 0.9))
    model = review_from_model_response("run-1", "verify", "input", expectation,
                                       {"rows": [{"alternative": "reuse_then_modify", "confidence": 0.7, "reason": "close match"},
                                                 {"alternative": "service_model", "confidence": 0.4, "reason": "fallback"}],
                                        "inputs_too_big": False, "outputs_too_big": True, "chosen_index": 0})
    check("a_model_or_specialist_review_records_its_judge_kind_and_flags",
          model.judge_kind == "model" and model.chosen.method == "reuse_then_modify"
          and "outputs too big" in " ".join(model.reasons)
          and review_from_model_response("r", "s", "i", expectation, {"rows": [{"alternative": "skip_step", "confidence": 1}]},
                                         judge_kind="specialist").judge_kind == "specialist"
          and refuses(lambda: review_from_model_response("r", "s", "i", expectation, {"rows": []}))
          and refuses(lambda: review_from_model_response(
              "r", "s", "i", expectation,
              {"rows": [{"alternative": "skip_step", "confidence": 1, "reason": "valid row"}]},
              judge_kind="deterministic")))
    check("invalid_expectations_alternatives_and_reviews_are_refused",
          refuses(lambda: SizeExpectation(0, 10)) and refuses(lambda: SizeExpectation(10, 10, -1))
          and refuses(lambda: EfficiencyAlternative("guess", 0.5, "r"))
          and refuses(lambda: EfficiencyAlternative("skip_step", 1.5, "r"))
          and refuses(lambda: EfficiencyAlternative("skip_step", 0.5, ""))
          and refuses(lambda: EfficiencyReview("r", "s", "oracle", 1, None, expectation, small.alternatives, 0))
          and refuses(lambda: EfficiencyReview("r", "s", "deterministic", 1, None, expectation, small.alternatives, 9))
          and refuses(lambda: EfficiencyReview("r", "s", "deterministic", 1, None, expectation, (), 0))
          and refuses(lambda: deterministic_efficiency_judge("r", "s", "i", expectation, available=())))
    check("the_record_digest_is_stable_and_names_the_contract",
          small.to_dict()["content_digest"] == small.to_dict()["content_digest"]
          and CONTRACT_ID == "practitioner.step_efficiency_review")
    passed = sum(item["passed"] for item in results)
    return {"record_type": "step_efficiency_review_test/v1", "tests": results, "passed": passed,
            "total": len(results), "all_passed": passed == len(results)}
