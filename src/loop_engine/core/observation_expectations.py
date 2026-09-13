"""Passive expectation checks for observations inside existing classified Loops.

This is a value-validation primitive, not an executor or another runtime.
Schemas and binding facts are structured inputs. Semantic expectations remain
questions for a reasoning Loop; matching a schema never accepts a task.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import re

from jsonschema import Draft202012Validator


class ExpectationDisposition(str, Enum):
    MATCHED = "matched"
    UNEXPECTED_COMPATIBLE = "unexpected_compatible"
    INCOMPATIBLE = "incompatible"
    UNCERTAIN = "uncertain"


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _local_schema(value: object) -> None:
    if isinstance(value, dict):
        if any(key in value for key in ("$ref", "$dynamicRef")):
            raise ValueError("expectation schemas must already be resolved")
        for item in value.values():
            _local_schema(item)
    elif isinstance(value, list):
        for item in value:
            _local_schema(item)


def resolved_schema_json(schema_json: str) -> str:
    """Validate and freeze a self-contained schema without reference IO."""
    from .record_operations_records import parse_json
    schema = parse_json(schema_json)
    _local_schema(schema)
    Draft202012Validator.check_schema(schema)
    return _canonical(schema)


@dataclass(frozen=True)
class ObservationExpectation:
    """An exact expected observation, bound before the action it describes."""

    expectation_id: str
    operation_id: str
    input_digest: str
    output_contract_ref: str
    schema_json: str
    semantic_questions: tuple[str, ...] = ()
    version: str = "1.0.0"

    def __post_init__(self):
        for name in ("expectation_id", "operation_id", "output_contract_ref"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(name + " must be non-empty text")
        if not re.fullmatch(r"[0-9a-f]{64}", self.input_digest):
            raise ValueError("input_digest must bind exact input bytes")
        if self.version != "1.0.0":
            raise ValueError("unsupported observation expectation version")
        object.__setattr__(self, "schema_json", resolved_schema_json(self.schema_json))
        questions = tuple(self.semantic_questions)
        if any(not isinstance(x, str) or not x.strip() for x in questions):
            raise ValueError("semantic questions must be non-empty text")
        object.__setattr__(self, "semantic_questions", questions)

    @property
    def content_digest(self) -> str:
        return _digest(_canonical(self.__dict__))


@dataclass(frozen=True)
class ObservationBinding:
    """Observed data detached from its producer and exact action/input binding."""

    operation_id: str
    input_digest: str
    value_json: str
    available: bool = True

    def __post_init__(self):
        if not isinstance(self.operation_id, str) or not self.operation_id.strip():
            raise ValueError("an observation needs its exact operation identity")
        if not re.fullmatch(r"[0-9a-f]{64}", self.input_digest):
            raise ValueError("an observation needs its exact input digest")
        if type(self.available) is not bool:
            raise ValueError("observation availability must be explicit")
        from .record_operations_records import parse_json
        object.__setattr__(self, "value_json", _canonical(parse_json(self.value_json)))

    @property
    def content_digest(self) -> str:
        return _digest(self.value_json)


@dataclass(frozen=True)
class ExpectationAssessment:
    """Compatibility evidence, never acceptance, effect, or repair authority."""

    expectation_digest: str
    observation_digest: str
    disposition: ExpectationDisposition
    contract_compatible: bool | None
    handoff_ready: bool
    findings: tuple[str, ...]
    unresolved_questions: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"record_type": "observation_expectation_assessment/v1",
                "expectation_digest": self.expectation_digest,
                "observation_digest": self.observation_digest,
                "disposition": self.disposition.value,
                "contract_compatible": self.contract_compatible,
                "handoff_ready": self.handoff_ready,
                "findings": list(self.findings),
                "unresolved_questions": list(self.unresolved_questions),
                "task_accepted": False, "effect_authorized": False}


def assess_observation(expectation: ObservationExpectation,
                       observation: ObservationBinding) -> ExpectationAssessment:
    """Check exact bindings and structure before permitting a dependent handoff.

    Additional fields explicitly allowed by a schema are retained as a
    compatible surprise. Semantic questions require a reasoning decision and
    remain unresolved here. No diagnostic contains the observed body.
    """
    if not isinstance(expectation, ObservationExpectation) or not isinstance(observation, ObservationBinding):
        raise TypeError("typed expectation and observation are required")

    def result(disposition, compatible, ready, findings=(), questions=()):
        return ExpectationAssessment(expectation.content_digest,
                                     observation.content_digest, disposition,
                                     compatible, ready, tuple(findings), tuple(questions))

    if (expectation.operation_id != observation.operation_id or
            expectation.input_digest != observation.input_digest):
        return result(ExpectationDisposition.INCOMPATIBLE, False, False,
                      ("operation_or_input_binding_changed",))
    if not observation.available:
        return result(ExpectationDisposition.UNCERTAIN, None, False,
                      ("observation_unavailable",))
    schema = json.loads(expectation.schema_json)
    value = json.loads(observation.value_json)
    errors = sorted(Draft202012Validator(schema).iter_errors(value),
                    key=lambda e: (str(list(e.absolute_path)), str(e.validator)))
    if errors:
        # Validator names and paths describe the failure without copying data,
        # credentials, or private model text into diagnostics.
        findings = tuple(str(error.validator) + ":" +
                         "/".join(str(p) for p in error.absolute_path)
                         for error in errors)
        return result(ExpectationDisposition.INCOMPATIBLE, False, False, findings)
    if expectation.semantic_questions:
        return result(ExpectationDisposition.UNCERTAIN, True, False,
                      ("semantic_expectations_require_review",),
                      expectation.semantic_questions)
    extra = (set(value) - set(schema.get("properties", {}))
             if isinstance(schema, dict) and isinstance(value, dict) and
             "properties" in schema else set())
    if extra:
        return result(ExpectationDisposition.UNEXPECTED_COMPATIBLE, True, True,
                      ("schema_permits_additional_fields:" + str(len(extra)),))
    return result(ExpectationDisposition.MATCHED, True, True)


def self_test() -> dict:
    """Positive, negative, stale, ambiguous, and non-authority controls."""
    from dataclasses import replace
    checks = []

    def check(name, value):
        checks.append({"test": name, "passed": bool(value)})

    expected = ObservationExpectation(
        "scan-expectation", "scan-1", "a" * 64, "directory_inventory/v1",
        _canonical({"type": "object", "required": ["files"],
                    "properties": {"files": {"type": "array", "minItems": 1,
                                             "items": {"type": "string"}}}}))
    actual = ObservationBinding("scan-1", "a" * 64, '{"files":["training.csv"]}')
    check("expected_observation_can_handoff", assess_observation(expected, actual).handoff_ready)
    check("empty_scan_cannot_feed_a_nonempty_input_contract", not assess_observation(
        expected, replace(actual, value_json='{"files":[]}')).handoff_ready)
    check("http_success_with_error_body_is_not_expected_data", assess_observation(
        expected, replace(actual, value_json='{"error":"unavailable"}')).disposition
          is ExpectationDisposition.INCOMPATIBLE)
    check("stale_input_requires_reorientation", not assess_observation(
        expected, replace(actual, input_digest="b" * 64)).handoff_ready)
    check("another_operation_cannot_supply_the_observation", not assess_observation(
        expected, replace(actual, operation_id="scan-2")).handoff_ready)
    check("missing_is_unknown_not_empty", assess_observation(
        expected, replace(actual, available=False)).contract_compatible is None)
    extra = assess_observation(expected, replace(actual, value_json='{"files":["a"],"extra":7}'))
    check("allowed_surprise_remains_usable_and_visible", extra.handoff_ready and
          extra.disposition is ExpectationDisposition.UNEXPECTED_COMPATIBLE)
    meaning = assess_observation(replace(expected, semantic_questions=(
        "Do the discovered resources support the next operation?",)), actual)
    check("shape_does_not_answer_semantic_questions", meaning.contract_compatible and
          not meaning.handoff_ready and bool(meaning.unresolved_questions))
    check("matching_grants_no_acceptance_or_effect", not extra.to_dict()["task_accepted"]
          and not extra.to_dict()["effect_authorized"])
    units = replace(expected, schema_json='{"type":"object","properties":{"units":{"const":"C"}},"required":["units"]}')
    check("wrong_units_block_the_next_step", not assess_observation(
        units, replace(actual, value_json='{"units":"F"}')).handoff_ready)
    refused = False
    try:
        replace(expected, schema_json='{"$ref":"https://example.invalid/schema"}')
    except ValueError:
        refused = True
    check("schema_validation_cannot_fetch_remote_content", refused)
    check("assessment_does_not_copy_observed_values", "training.csv" not in
          _canonical(assess_observation(expected, actual).to_dict()))
    return {"tests": checks, "passed": sum(x["passed"] for x in checks),
            "total": len(checks), "all_passed": all(x["passed"] for x in checks)}
