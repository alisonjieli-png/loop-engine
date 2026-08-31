"""Typed admission and deterministic repair of untrusted model responses.

This component sits after ModelGateway transport and before any semantic
consumer. It may remove only approved non-semantic envelopes, parse JSON,
validate an optional JSON Schema, and return a typed candidate disposition.
It never invents keys, changes values, grants authority, or commits effects.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field, replace
from typing import Mapping

from jsonschema import Draft202012Validator

from ..loop.loop_role import LoopRelationship, LoopRole, LoopRoleIdentity
from ..loop.recursive_loop import Loop, LoopConfig, StepOutcome


_NORMALIZATION_STRATEGIES = (
    "strict_json", "json_markdown_fence_removed",
    "approved_json_preamble_removed", "double_encoded_json_unwrapped")
_APPROVED_PREAMBLE = re.compile(
    r"\s*(?:here\s+it\s+is|here\s+is\s+the\s+(?:requested\s+)?json|"
    r"here's\s+the\s+(?:requested\s+)?json|json\s+response|response)\s*:\s*"
    r"(?P<body>\{.*\})\s*", flags=re.IGNORECASE | re.DOTALL)
_JSON_FENCE = re.compile(
    r"\s*```(?:json)?\s*\n?(?P<body>.*?)\n?```\s*",
    flags=re.IGNORECASE | re.DOTALL)


class ModelResponseRepairStalled(RuntimeError):
    """A response repair cycle repeated without semantic progress."""


@dataclass(frozen=True)
class ModelResponseAdmissionPolicy:
    """Allowed meaning-preserving normalization strategies."""

    allowed_strategies: tuple[str, ...] = _NORMALIZATION_STRATEGIES
    expected_root_type: str = "object"

    def __post_init__(self) -> None:
        strategies = tuple(self.allowed_strategies)
        if (not strategies or len(strategies) != len(set(strategies))
                or any(item not in _NORMALIZATION_STRATEGIES
                       for item in strategies)):
            raise ValueError("response admission strategies are invalid")
        if self.expected_root_type != "object":
            raise ValueError("version 1 response admission expects an object")
        object.__setattr__(self, "allowed_strategies", strategies)


@dataclass(frozen=True)
class ModelResponseAdmissionRequest:
    """Raw provider text plus its exact expected response contract."""

    raw_text: str = field(repr=False, compare=False)
    contract_ref: str
    contract_digest: str
    schema: Mapping[str, object] | None = field(
        default=None, repr=False, compare=False)
    policy: ModelResponseAdmissionPolicy = field(
        default_factory=ModelResponseAdmissionPolicy)

    def __post_init__(self) -> None:
        if not isinstance(self.raw_text, str):
            raise ValueError("raw model response must be text")
        if not self.contract_ref.strip() or len(self.contract_digest) != 64:
            raise ValueError("response admission contract identity is invalid")
        if self.schema is not None:
            Draft202012Validator.check_schema(dict(self.schema))

    @property
    def raw_digest(self) -> str:
        return hashlib.sha256(self.raw_text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ModelResponseAdmissionResult:
    """Admitted object or a typed rejection with no raw text."""

    admitted: bool
    value: dict | None = field(default=None, repr=False, compare=False)
    strategy: str = "unparsed"
    failure_code: str = ""
    raw_digest: str = ""
    normalized_digest: str = ""
    schema_errors: tuple[str, ...] = ()
    transformation_trace: tuple[str, ...] = ()
    loop_id: str = ""
    model_calls: int = 0

    def to_dict(self) -> dict:
        return {
            "record_type": "model_response_admission_result/v1",
            "admitted": self.admitted, "strategy": self.strategy,
            "failure_code": self.failure_code, "raw_digest": self.raw_digest,
            "normalized_digest": self.normalized_digest,
            "schema_errors": list(self.schema_errors),
            "transformation_trace": list(self.transformation_trace),
            "loop_id": self.loop_id, "model_calls": self.model_calls}


def _canonical_digest(value: object) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False).encode("utf-8")).hexdigest()


def _candidate_texts(request: ModelResponseAdmissionRequest):
    raw = request.raw_text
    allowed = set(request.policy.allowed_strategies)
    if "strict_json" in allowed:
        yield "strict_json", raw, ()
    if "json_markdown_fence_removed" in allowed:
        match = _JSON_FENCE.fullmatch(raw)
        if match is not None:
            yield ("json_markdown_fence_removed",
                   match.group("body").strip(),
                   ("removed_exact_markdown_json_fence",))
    if "approved_json_preamble_removed" in allowed:
        match = _APPROVED_PREAMBLE.fullmatch(raw)
        if match is not None:
            yield ("approved_json_preamble_removed",
                   match.group("body").strip(),
                   ("removed_approved_nonsemantic_json_preamble",))
    if "double_encoded_json_unwrapped" in allowed:
        try:
            outer = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            outer = None
        if isinstance(outer, str):
            yield ("double_encoded_json_unwrapped", outer,
                   ("unwrapped_one_json_string_layer",))


def _admit(request: ModelResponseAdmissionRequest) \
        -> ModelResponseAdmissionResult:
    saw_non_object = False
    for strategy, candidate, trace in _candidate_texts(request):
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if not isinstance(value, dict):
            saw_non_object = True
            continue
        errors = ()
        if request.schema is not None:
            validator = Draft202012Validator(dict(request.schema))
            errors = tuple(sorted(
                error.message for error in validator.iter_errors(value)))
        if errors:
            return ModelResponseAdmissionResult(
                False, None, strategy, "schema_validation_failed",
                request.raw_digest, _canonical_digest(value), errors, trace)
        return ModelResponseAdmissionResult(
            True, value, strategy, "", request.raw_digest,
            _canonical_digest(value), (), trace)
    return ModelResponseAdmissionResult(
        False, None, "unparsed",
        "root_not_object" if saw_non_object else "invalid_json",
        request.raw_digest)


def admit_model_response_as_loop(
        request: ModelResponseAdmissionRequest, *, parent=None, ledger=None
        ) -> ModelResponseAdmissionResult:
    """Admit one untrusted response through a deterministic component Loop."""
    if not isinstance(request, ModelResponseAdmissionRequest):
        raise TypeError("model response admission requires its typed request")
    config = LoopConfig(
        framework="custom", custom_steps=("admit",), power="light",
        allowable_modes=("deterministic",),
        preferred_modes=("deterministic",),
        delegated_modes=("deterministic",),
        logical_kind="execution", replay_guarantee="event_equivalent",
        exit_condition="accepted_success")
    identity = LoopRoleIdentity(LoopRole.SOLUTION, "solution.validator")
    relationship = (LoopRelationship.spawned_by(parent.loop_id)
                    if parent is not None else LoopRelationship.starting())
    loop = (parent.spawn(
        "admit one untrusted model response", config, identity=identity,
        relationship=relationship) if parent is not None else Loop(
            "admit one untrusted model response", config, ledger=ledger,
            identity=identity, relationship=relationship))
    holder = {}

    def handler(active, _step, _context):
        holder["value"] = _admit(request)
        admission_record = holder["value"].to_dict()
        admission_record.pop("loop_id", None)
        active.ledger.record(
            loop_id=active.loop_id, event="custom",
            custom_kind="model_response_admission",
            admission=admission_record)
        return StepOutcome(
            "response:admitted" if holder["value"].admitted
            else "response:rejected", "deterministic",
            1.0 if holder["value"].admitted else 0.0,
            failed=not holder["value"].admitted)

    run = loop.run(handler=handler, max_steps=2)
    value = holder.get("value")
    if not isinstance(value, ModelResponseAdmissionResult):
        raise TypeError("model response admission returned the wrong type")
    if run.model_calls != 0:
        raise RuntimeError("deterministic response admission called a model")
    return replace(value, loop_id=run.loop_id, model_calls=0)


def self_test() -> dict:
    """Exercise deterministic wrappers, schema rejection, and redaction."""
    digest = hashlib.sha256(b"contract").hexdigest()

    def admit(text, schema=None):
        return admit_model_response_as_loop(ModelResponseAdmissionRequest(
            text, "fixture.response/v1", digest, schema=schema))

    strict = admit('{"ok":true}')
    fenced = admit('```json\n{"ok":true}\n```')
    preamble = admit('Here is the JSON: {"ok":true}')
    doubled = admit(json.dumps('{"ok":true}'))
    prose = admit('Explanation before {"ok":true} after')
    schema = admit('{"ok":"yes"}', {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object", "properties": {"ok": {"type": "boolean"}},
        "required": ["ok"], "additionalProperties": False})
    raw_safe = "Here is the JSON" not in json.dumps(preamble.to_dict())
    tests = [{
        "test": "approved_response_envelopes_are_repaired_deterministically",
        "passed": all(item.admitted for item in (
            strict, fenced, preamble, doubled))
        and [strict.strategy, fenced.strategy, preamble.strategy,
             doubled.strategy] == list(_NORMALIZATION_STRATEGIES),
        "detail": ", ".join(item.strategy for item in (
            strict, fenced, preamble, doubled)),
    }, {
        "test": "arbitrary_prose_and_schema_mismatch_are_rejected",
        "passed": (not prose.admitted and prose.failure_code == "invalid_json"
                   and not schema.admitted
                   and schema.failure_code == "schema_validation_failed"),
        "detail": f"{prose.failure_code}; {schema.failure_code}",
    }, {
        "test": "admission_records_digests_not_raw_model_text",
        "passed": raw_safe and len(preamble.raw_digest) == 64,
        "detail": preamble.raw_digest,
    }]
    return {"record_type": "model_response_admission_test/v1",
            "tests": tests, "passed": sum(item["passed"] for item in tests),
            "total": len(tests),
            "all_passed": all(item["passed"] for item in tests)}


__all__ = (
    "ModelResponseAdmissionPolicy", "ModelResponseAdmissionRequest",
    "ModelResponseAdmissionResult", "ModelResponseRepairStalled",
    "admit_model_response_as_loop")
