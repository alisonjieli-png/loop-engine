"""Provider-independent typed judgments. Records grant no effects or acceptance.

Immutable questions describe choices, ordered scores or Boolean probabilities.
Response admission checks exact question identities, finite distributions and
score consistency. The gateway and owning Loop enforce execution authority.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import math
from typing import Protocol

REQUEST_VERSION = "decision_batch_request/v1"
RESULT_VERSION = "decision_batch_result/v1"
QUESTION_KINDS = ("choice", "score", "boolean_probability")
CHOICE, SCORE, BOOLEAN_PROBABILITY = QUESTION_KINDS
PROVIDER_CAPABILITY = "typed_decisions/v1"


class DecisionProtocolError(ValueError):
    """A typed request or result violates the selected decision contract."""


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def strict_json(value):
    def unique(pairs):
        result = {}
        for key, item in pairs:
            if key in result:
                raise DecisionProtocolError("duplicate_json_field")
            result[key] = item
        return result
    try:
        return json.loads(value, object_pairs_hook=unique,
            parse_constant=lambda _value: (_ for _ in ()).throw(DecisionProtocolError("nonfinite_value")))
    except (ValueError, TypeError, RecursionError, UnicodeError):
        raise DecisionProtocolError("invalid_json") from None


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _probability(value):
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
        raise DecisionProtocolError("invalid_probability")
    return float(value)


@dataclass(frozen=True)
class DecisionQuestion:
    question_id: str
    kind: str
    instructions: str = field(repr=False)
    choices: tuple[tuple[str, str | None], ...] = ()
    levels: tuple[str, ...] = ()
    positive: str = ""
    negative: str = ""

    def __post_init__(self):
        if not _text(self.question_id) or not _text(self.instructions) or self.kind not in QUESTION_KINDS:
            raise DecisionProtocolError("invalid_question")
        if type(self.choices) not in (list, tuple) or type(self.levels) not in (list, tuple):
            raise DecisionProtocolError("invalid_question_criteria")
        if any(type(row) not in (tuple, list) or len(row) != 2 or not _text(row[0])
               or row[1] is not None and not isinstance(row[1], str) for row in self.choices):
            raise DecisionProtocolError("invalid_choice_criteria")
        if any(not _text(value) for value in self.levels):
            raise DecisionProtocolError("invalid_score_levels")
        if not isinstance(self.positive, str) or not isinstance(self.negative, str):
            raise DecisionProtocolError("invalid_boolean_criteria")
        choices = tuple(tuple(row) for row in self.choices)
        if len({row[0] for row in choices}) != len(choices):
            raise DecisionProtocolError("duplicate_choice")
        if self.kind == CHOICE and (not choices or self.levels or self.positive or self.negative):
            raise DecisionProtocolError("invalid_choice_question")
        if self.kind == SCORE and (len(self.levels) < 2 or choices or self.positive or self.negative):
            raise DecisionProtocolError("invalid_score_question")
        if self.kind == BOOLEAN_PROBABILITY and (choices or self.levels):
            raise DecisionProtocolError("invalid_boolean_question")
        object.__setattr__(self, "choices", choices)
        object.__setattr__(self, "levels", tuple(self.levels))

    def to_dict(self):
        return {"question_id": self.question_id, "kind": self.kind, "instructions": self.instructions,
                "choices": dict(self.choices), "levels": list(self.levels),
                "positive": self.positive, "negative": self.negative}

    @classmethod
    def from_dict(cls, value):
        names = {"question_id", "kind", "instructions", "choices", "levels", "positive", "negative"}
        if not isinstance(value, dict) or set(value) - names or not {"question_id", "kind", "instructions"} <= set(value):
            raise DecisionProtocolError("invalid_question_fields")
        fields = dict(value)
        if "choices" in fields:
            if not isinstance(fields["choices"], dict):
                raise DecisionProtocolError("invalid_choice_criteria")
            fields["choices"] = tuple(fields["choices"].items())
        return cls(**fields)


@dataclass(frozen=True)
class DecisionBatchRequest:
    state_json: str = field(repr=False)
    questions: tuple[DecisionQuestion, ...] = field(repr=False)
    semantic_call_id: str = ""

    def __post_init__(self):
        state = strict_json(self.state_json)
        if type(state) not in (str, dict, list):
            raise DecisionProtocolError("state_must_be_text_or_structured_data")
        if type(self.questions) not in (tuple, list) or not self.questions:
            raise DecisionProtocolError("questions_required")
        questions = tuple(self.questions)
        if any(not isinstance(item, DecisionQuestion) for item in questions):
            raise DecisionProtocolError("typed_questions_required")
        if len({item.question_id for item in questions}) != len(questions):
            raise DecisionProtocolError("duplicate_question_identity")
        if (not isinstance(self.semantic_call_id, str) or len(self.semantic_call_id) > 192
                or any(character.isspace() for character in self.semantic_call_id)):
            raise DecisionProtocolError("invalid_semantic_call_identity")
        object.__setattr__(self, "state_json", canonical(state))
        object.__setattr__(self, "questions", questions)

    @classmethod
    def from_dict(cls, value):
        if (not isinstance(value, dict) or set(value) - {"record_type", "state", "questions", "semantic_call_id"}
                or value.get("record_type") != REQUEST_VERSION or "state" not in value
                or not isinstance(value.get("questions"), list)):
            raise DecisionProtocolError("invalid_decision_batch")
        return cls(canonical(value["state"]), tuple(DecisionQuestion.from_dict(item) for item in value["questions"]),
                   value.get("semantic_call_id", ""))

    def to_dict(self):
        return {"record_type": REQUEST_VERSION, "state": strict_json(self.state_json),
                "questions": [item.to_dict() for item in self.questions], "semantic_call_id": self.semantic_call_id}

    @property
    def content_digest(self):
        return hashlib.sha256(canonical(self.to_dict()).encode()).hexdigest()


def admit_answers(request, answers):
    """Validate every answer, returning only the normalized contract fields."""
    if not isinstance(request, DecisionBatchRequest) or not isinstance(answers, dict):
        raise DecisionProtocolError("invalid_answers")
    if set(answers) != {item.question_id for item in request.questions}:
        raise DecisionProtocolError("answer_identity_mismatch")
    admitted = {}
    for question in request.questions:
        value = answers[question.question_id]
        if not isinstance(value, dict) or value.get("kind") != question.kind:
            raise DecisionProtocolError("answer_kind_mismatch")
        if question.kind == BOOLEAN_PROBABILITY:
            if set(value) != {"kind", "probability"}:
                raise DecisionProtocolError("invalid_boolean_answer")
            admitted[question.question_id] = {"kind": question.kind, "probability": _probability(value["probability"])}
            continue
        field_name = CHOICE if question.kind == CHOICE else SCORE
        if set(value) != {"kind", field_name, "probabilities", "confidence"}:
            raise DecisionProtocolError("invalid_answer_fields")
        expected = set(dict(question.choices)) if question.kind == CHOICE else {str(i) for i in range(len(question.levels))}
        probabilities = value["probabilities"]
        if not isinstance(probabilities, dict) or set(probabilities) != expected:
            raise DecisionProtocolError("probability_identity_mismatch")
        probabilities = {key: _probability(mass) for key, mass in probabilities.items()}
        if not math.isclose(sum(probabilities.values()), 1.0, rel_tol=0, abs_tol=0.00001):
            raise DecisionProtocolError("probabilities_do_not_sum_to_one")
        selected = value[field_name]
        if question.kind == CHOICE:
            if not isinstance(selected, str) or selected not in expected or probabilities[selected] != max(probabilities.values()):
                raise DecisionProtocolError("invalid_selected_choice")
        elif (type(selected) not in (int, float) or not math.isfinite(selected)
              or not math.isclose(selected, sum(int(key) * mass for key, mass in probabilities.items()),
                                  rel_tol=0, abs_tol=0.00001)):
            raise DecisionProtocolError("score_does_not_match_distribution")
        admitted[question.question_id] = {"kind": question.kind, field_name: selected,
            "probabilities": probabilities, "confidence": _probability(value["confidence"])}
    return admitted


GUIDANCE_VERSION = "decision_guidance/v1"
#: Advisory guidance kinds: bias toward, bias away from, or note for attention.
GUIDANCE_KINDS = ("prefer", "avoid", "consider")
MAXIMUM_GUIDANCE_ITEMS = 32


@dataclass(frozen=True)
class DecisionGuidance:
    """Advisory guidance returned beside the typed answers, never instead of them.

    Guidance may bias what the owning Loop considers next. It never binds: it
    cannot change an admitted answer, satisfy or bypass a station guard, grant
    an effect or accept an outcome. A guidance engine can therefore sit behind
    the same typed edge as a deciding engine without gaining authority."""
    guidance_id: str
    kind: str
    target: str
    weight: float
    reason: str = ""

    def __post_init__(self):
        if (not _text(self.guidance_id) or len(self.guidance_id) > 128 or self.kind not in GUIDANCE_KINDS
                or not _text(self.target) or len(self.target) > 512
                or not isinstance(self.reason, str) or len(self.reason) > 512):
            raise DecisionProtocolError("invalid_guidance")
        object.__setattr__(self, "weight", _probability(self.weight))

    def to_dict(self):
        return {"record_type": GUIDANCE_VERSION, "guidance_id": self.guidance_id, "kind": self.kind,
                "target": self.target, "weight": self.weight, "reason": self.reason, "binding": False}


def admit_guidance(items):
    """Admit advisory guidance on its own path, separate from the typed answers."""
    if type(items) not in (tuple, list) or len(items) > MAXIMUM_GUIDANCE_ITEMS:
        raise DecisionProtocolError("invalid_guidance")
    admitted = tuple(items)
    if any(not isinstance(item, DecisionGuidance) for item in admitted):
        raise DecisionProtocolError("typed_guidance_required")
    if len({item.guidance_id for item in admitted}) != len(admitted):
        raise DecisionProtocolError("duplicate_guidance_identity")
    return admitted


@dataclass(frozen=True)
class DecisionProviderResult:
    """Transient provider response; only digests and counts belong in history.

    ``in_process`` marks an answer computed inside this process (rules, a
    local classifier or reranker). Such an answer sent no provider request, so
    it counts no physical request and no model call, and the model gateway
    refuses it as a provider result. ``guidance`` is advisory and travels
    apart from ``answers``, which alone carry the binding typed decision."""
    ok: bool
    model: str
    answers: dict = field(default_factory=dict, repr=False)
    prompt_tokens: int | None = None
    eval_tokens: int | None = None
    error_code: str = ""
    physical_requests: int = 0
    response_received: bool = False
    in_process: bool = False
    guidance: tuple = ()

    def __post_init__(self):
        if (type(self.ok) is not bool or type(self.response_received) is not bool
                or type(self.in_process) is not bool
                or not _text(self.model) or not isinstance(self.answers, dict)
                or type(self.physical_requests) is not int or self.physical_requests not in (0, 1)
                or self.in_process and self.physical_requests != 0
                or self.ok and not self.response_received
                or self.ok and not self.in_process and self.physical_requests != 1):
            raise DecisionProtocolError("invalid_provider_result")
        object.__setattr__(self, "guidance", admit_guidance(self.guidance))
        for value in (self.prompt_tokens, self.eval_tokens):
            if value is not None and (type(value) is not int or value < 0):
                raise DecisionProtocolError("invalid_provider_usage")
        if not isinstance(self.error_code, str):
            raise DecisionProtocolError("invalid_provider_result")

    @property
    def total_tokens(self):
        return None if self.prompt_tokens is None or self.eval_tokens is None else self.prompt_tokens + self.eval_tokens


class DecisionProvider(Protocol):
    """Provider implementations compose with the gateway without inheritance."""
    DEFAULT_MODEL: str
    def decision_capabilities(self) -> dict: ...
    def prepare_decisions(self, request: DecisionBatchRequest, *, model: str): ...
    def decide_questions(self, request: DecisionBatchRequest, *, model: str, timeout: float) -> DecisionProviderResult: ...


def self_test():
    from .contract_checks import run_checks
    return run_checks()
