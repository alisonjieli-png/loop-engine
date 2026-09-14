"""Typed assessment of one action's observable direction and outcome.

Owns the closed process, output, progress, and continuation vocabularies; the
versioned response fragment; validation; and conversion into signals for the
existing ``OutcomeVector``. It does not execute work, route a Practitioner,
inspect private model reasoning, grant authority, or accept a task.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass


def _short_text(value: object, label: str, maximum: int | None = None) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ActionVectorAssessmentError(f"{label} must be non-empty text")
    if maximum is not None and len(value) > maximum:
        raise ActionVectorAssessmentError(
            f"{label} must contain at most {maximum} characters")
    return value.strip()


def _short_strings(value: object, label: str) -> tuple[str, ...]:
    if (not isinstance(value, list)
            or any(not isinstance(item, str) or not item.strip()
                   for item in value)):
        raise ActionVectorAssessmentError(
            f"{label} must be an array of non-empty text")
    values = tuple(item.strip() for item in value)
    if len(values) != len(set(values)):
        raise ActionVectorAssessmentError(f"{label} must not repeat")
    return values


PROCESS_ALIGNMENT_CHECKS = (
    "task_goal_preserved",
    "declared_method_followed",
    "constraints_and_authority_respected",
    "evidence_assumptions_and_synthetic_material_separated",
    "expected_observation_checked",
    "alternatives_or_fallback_considered",
)
PROCESS_CHECK_STATUSES = ("passed", "failed", "unknown", "not_applicable")
OUTPUT_CHECK_STATUSES = ("satisfied", "unsatisfied", "unknown")
PROGRESS_STATUSES = ("advanced", "neutral", "regressed", "unknown")
CONTINUATION_STATUSES = (
    "continue", "adjust", "complete", "await_authority",
    "no_safe_action", "unknown")
# Named subsets of the closed vocabularies above, defined once so each
# decision below refers to its vocabulary instead of repeating its tokens.
CONTINUING_STATUSES = CONTINUATION_STATUSES[:2]
WORK_BOUND_CONTINUATION_STATUSES = (
    CONTINUATION_STATUSES[:2] + CONTINUATION_STATUSES[3:4])
STOPPING_CONTINUATION_STATUSES = CONTINUATION_STATUSES[2:5]
NON_ADVANCING_PROGRESS_STATUSES = PROGRESS_STATUSES[1:3]


class ActionVectorAssessmentError(ValueError):
    """An action-vector assessment violated its typed contract."""


@dataclass(frozen=True)
class ObservableProcessCheck:
    """One check of the visible work record, never private model reasoning."""

    check_id: str
    status: str
    finding: str

    def __post_init__(self) -> None:
        if self.check_id not in PROCESS_ALIGNMENT_CHECKS:
            raise ActionVectorAssessmentError(
                "process check identity is not registered")
        if self.status not in PROCESS_CHECK_STATUSES:
            raise ActionVectorAssessmentError(
                "process check status is not registered")
        _short_text(self.finding, "process check finding", 500)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class RequestedOutputCheck:
    """One preserved task criterion checked against this action result."""

    criterion_ref: str
    status: str
    finding: str

    def __post_init__(self) -> None:
        if not self.criterion_ref.strip():
            raise ActionVectorAssessmentError(
                "output check needs a criterion reference")
        if self.status not in OUTPUT_CHECK_STATUSES:
            raise ActionVectorAssessmentError(
                "output check status is not registered")
        _short_text(self.finding, "output check finding", 500)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ActionVectorAssessment:
    """Observable process, output, progress, and continuation for one action.

    This record supplies evidence to the existing ``OutcomeVector``. It does
    not store or request private reasoning and it cannot grant task acceptance,
    permission, or another action.
    """

    process_checks: tuple[ObservableProcessCheck, ...]
    expected_output_status: str
    expected_output_findings: tuple[str, ...]
    requested_output_checks: tuple[RequestedOutputCheck, ...]
    progress_status: str
    progress_evidence: tuple[str, ...]
    continuation_status: str
    remaining_work: tuple[str, ...]

    def __post_init__(self) -> None:
        if ({item.check_id for item in self.process_checks}
                != set(PROCESS_ALIGNMENT_CHECKS)
                or len(self.process_checks) != len(PROCESS_ALIGNMENT_CHECKS)):
            raise ActionVectorAssessmentError(
                "action vector needs every observable process check exactly once")
        if self.expected_output_status not in OUTPUT_CHECK_STATUSES:
            raise ActionVectorAssessmentError(
                "expected output status is not registered")
        if self.progress_status not in PROGRESS_STATUSES:
            raise ActionVectorAssessmentError(
                "progress status is not registered")
        if self.continuation_status not in CONTINUATION_STATUSES:
            raise ActionVectorAssessmentError(
                "continuation status is not registered")
        for name in ("expected_output_findings", "progress_evidence",
                     "remaining_work"):
            values = tuple(getattr(self, name))
            if (len(values) != len(set(values))
                    or any(not isinstance(item, str) or not item.strip()
                           for item in values)):
                raise ActionVectorAssessmentError(
                    f"{name} must contain unique non-empty text")
            object.__setattr__(self, name, values)
        if (self.continuation_status in WORK_BOUND_CONTINUATION_STATUSES
                and not self.remaining_work):
            raise ActionVectorAssessmentError(
                "a continuing or authority-bound vector needs remaining work")

    @classmethod
    def from_mapping(cls, value: object,
                     criterion_refs: tuple[str, ...]) -> "ActionVectorAssessment":
        if not isinstance(value, dict):
            raise ActionVectorAssessmentError("action_vector must be one object")
        required = {
            "process_checks", "expected_output_status",
            "expected_output_findings", "requested_output_checks",
            "progress_status", "progress_evidence", "continuation_status",
            "remaining_work"}
        if set(value) != required:
            raise ActionVectorAssessmentError(
                "action_vector fields do not match its versioned contract")
        process_values = value.get("process_checks")
        output_values = value.get("requested_output_checks")
        if not isinstance(process_values, list) or not isinstance(
                output_values, list):
            raise ActionVectorAssessmentError(
                "action vector checks must be arrays")
        process_checks = tuple(ObservableProcessCheck(
            _short_text(item.get("check_id"), "process check id"),
            str(item.get("status") or ""),
            _short_text(item.get("finding"), "process check finding", 500))
            for item in process_values if isinstance(item, dict))
        output_checks = tuple(RequestedOutputCheck(
            _short_text(item.get("criterion_ref"), "criterion_ref"),
            str(item.get("status") or ""),
            _short_text(item.get("finding"), "output check finding", 500))
            for item in output_values if isinstance(item, dict))
        if (len(output_checks) != len(criterion_refs)
                or {item.criterion_ref for item in output_checks}
                != set(criterion_refs)):
            raise ActionVectorAssessmentError(
                "action vector must assess every registered criterion exactly once")
        return cls(
            process_checks,
            str(value.get("expected_output_status") or ""),
            _short_strings(value.get("expected_output_findings") or [],
                           "expected_output_findings"),
            output_checks,
            str(value.get("progress_status") or ""),
            _short_strings(value.get("progress_evidence") or [],
                           "progress_evidence"),
            str(value.get("continuation_status") or ""),
            _short_strings(value.get("remaining_work") or [],
                           "remaining_work"))

    @property
    def observable_process_aligned(self) -> bool | None:
        statuses = {item.status for item in self.process_checks}
        if "failed" in statuses:
            return False
        if "unknown" in statuses:
            return None
        return True

    @property
    def expected_output_satisfied(self) -> bool | None:
        if self.expected_output_status == OUTPUT_CHECK_STATUSES[0]:
            return True
        if self.expected_output_status == OUTPUT_CHECK_STATUSES[1]:
            return False
        return None

    @property
    def requested_output_satisfied(self) -> bool | None:
        statuses = {item.status for item in self.requested_output_checks}
        if "unsatisfied" in statuses:
            return False
        if "unknown" in statuses:
            return None
        return True

    @property
    def material_progress(self) -> bool | None:
        if self.progress_status == PROGRESS_STATUSES[0]:
            return True
        if self.progress_status in NON_ADVANCING_PROGRESS_STATUSES:
            return False
        return None

    @property
    def continuation_available(self) -> bool | None:
        if self.continuation_status in CONTINUING_STATUSES:
            return True
        if self.continuation_status in STOPPING_CONTINUATION_STATUSES:
            return False
        return None

    def outcome_signals(self) -> dict:
        return {
            "observable_process_aligned": self.observable_process_aligned,
            "expected_output_satisfied": self.expected_output_satisfied,
            "requested_output_satisfied": self.requested_output_satisfied,
            "material_progress": self.material_progress,
            "continuation_available": self.continuation_available,
        }

    def to_dict(self) -> dict:
        return {
            "record_type": "action_vector_assessment/v1",
            "private_reasoning_evaluated": False,
            "process_checks": [item.to_dict() for item in self.process_checks],
            "expected_output_status": self.expected_output_status,
            "expected_output_findings": list(self.expected_output_findings),
            "requested_output_checks": [
                item.to_dict() for item in self.requested_output_checks],
            "progress_status": self.progress_status,
            "progress_evidence": list(self.progress_evidence),
            "continuation_status": self.continuation_status,
            "remaining_work": list(self.remaining_work),
            "outcome_signals": self.outcome_signals(),
            "task_accepted": False,
            "effect_authorized": False,
        }


def action_vector_schema(criterion_refs: tuple[str, ...]) -> dict:
    """Return the strict JSON Schema fragment for one assessment response."""
    refs = tuple(criterion_refs)
    if (not refs or len(refs) != len(set(refs))
            or any(not isinstance(item, str) or not item.strip()
                   for item in refs)):
        raise ActionVectorAssessmentError(
            "action vector schema needs unique criterion references")
    text = {"type": "string", "minLength": 1}
    return {
        "type": "object",
        "required": [
            "process_checks", "expected_output_status",
            "expected_output_findings", "requested_output_checks",
            "progress_status", "progress_evidence", "continuation_status",
            "remaining_work"],
        "properties": {
            "process_checks": {
                "type": "array", "minItems": len(PROCESS_ALIGNMENT_CHECKS),
                "maxItems": len(PROCESS_ALIGNMENT_CHECKS),
                "items": {
                    "type": "object",
                    "required": ["check_id", "status", "finding"],
                    "properties": {
                        "check_id": {"enum": list(PROCESS_ALIGNMENT_CHECKS)},
                        "status": {"enum": list(PROCESS_CHECK_STATUSES)},
                        "finding": text},
                    "additionalProperties": False}},
            "expected_output_status": {"enum": list(OUTPUT_CHECK_STATUSES)},
            "expected_output_findings": {
                "type": "array", "items": text},
            "requested_output_checks": {
                "type": "array", "minItems": len(refs),
                "maxItems": len(refs),
                "items": {
                    "type": "object",
                    "required": ["criterion_ref", "status", "finding"],
                    "properties": {
                        "criterion_ref": {"enum": list(refs)},
                        "status": {"enum": list(OUTPUT_CHECK_STATUSES)},
                        "finding": text},
                    "additionalProperties": False}},
            "progress_status": {"enum": list(PROGRESS_STATUSES)},
            "progress_evidence": {"type": "array", "items": text},
            "continuation_status": {"enum": list(CONTINUATION_STATUSES)},
            "remaining_work": {"type": "array", "items": text},
        },
        "additionalProperties": False,
    }


def self_test() -> dict:
    """Test valid, missing, contradictory, and continuation cases offline."""
    def mapping():
        return {
            "process_checks": [{
                "check_id": check_id, "status": "passed",
                "finding": "The visible record satisfies this check."}
                for check_id in PROCESS_ALIGNMENT_CHECKS],
            "expected_output_status": "satisfied",
            "expected_output_findings": ["The declared output is present."],
            "requested_output_checks": [{
                "criterion_ref": "criterion:0", "status": "satisfied",
                "finding": "The requested criterion is satisfied."}],
            "progress_status": "advanced",
            "progress_evidence": ["A verified artifact was added."],
            "continuation_status": "complete", "remaining_work": [],
        }

    valid = ActionVectorAssessment.from_mapping(mapping(), ("criterion:0",))

    def refuses(value, refs=("criterion:0",)):
        try:
            ActionVectorAssessment.from_mapping(value, refs)
        except (TypeError, ValueError):
            return True
        return False

    missing_process = mapping()
    missing_process["process_checks"].pop()
    continuing_without_work = mapping()
    continuing_without_work["continuation_status"] = "continue"
    wrong_criterion = mapping()
    wrong_criterion["requested_output_checks"][0][
        "criterion_ref"] = "criterion:other"
    failed_process = mapping()
    failed_process["process_checks"][0]["status"] = "failed"
    failed = ActionVectorAssessment.from_mapping(
        failed_process, ("criterion:0",))
    schema = action_vector_schema(("criterion:0",))
    tests = [{
        "test": "valid_assessment_separates_every_vector_axis",
        "passed": (valid.observable_process_aligned is True
                   and valid.expected_output_satisfied is True
                   and valid.requested_output_satisfied is True
                   and valid.material_progress is True
                   and valid.continuation_available is False),
    }, {
        "test": "private_reasoning_and_self_acceptance_are_never_claimed",
        "passed": (valid.to_dict()["private_reasoning_evaluated"] is False
                   and valid.to_dict()["task_accepted"] is False),
    }, {
        "test": "failed_observable_process_is_distinct_from_response_shape",
        "passed": failed.observable_process_aligned is False,
    }, {
        "test": "every_process_check_and_requested_criterion_is_required",
        "passed": refuses(missing_process) and refuses(wrong_criterion),
    }, {
        "test": "continuation_requires_named_remaining_work",
        "passed": refuses(continuing_without_work),
    }, {
        "test": "schema_uses_closed_axes_and_exact_cardinality",
        "passed": (
            schema["properties"]["process_checks"]["minItems"]
            == len(PROCESS_ALIGNMENT_CHECKS)
            and schema["properties"]["requested_output_checks"][
                "maxItems"] == 1
            and schema["additionalProperties"] is False),
    }]
    return {
        "record_type": "action_vector_assessment_test/v1",
        "tests": tests, "passed": sum(item["passed"] for item in tests),
        "total": len(tests),
        "all_passed": all(item["passed"] for item in tests),
    }


__all__ = (
    "ActionVectorAssessment", "ActionVectorAssessmentError",
    "CONTINUATION_STATUSES", "OUTPUT_CHECK_STATUSES",
    "PROCESS_ALIGNMENT_CHECKS", "PROCESS_CHECK_STATUSES",
    "PROGRESS_STATUSES", "action_vector_schema", "self_test")
