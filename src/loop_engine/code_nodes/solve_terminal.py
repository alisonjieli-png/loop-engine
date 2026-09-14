"""Terminal classification and best-available solve resolution records.

Owns: the classification from a run's own failure and diagnostic codes to one
`SolveTerminalCode`, and the passive resolution package returned when the
original requested outcome cannot be verified in the current activation.

Belongs to: the solve runtime. Never: deciding whether the original requested
outcome succeeded. It reads that decision, preserves useful work, and keeps
observed, assumed, provisional, and missing material distinct.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum

from ..core.terminal_layer import deepest_layer_reached


class SolveTerminalCode(str, Enum):
    COMPLETED_VERIFIED = "COMPLETED_VERIFIED"
    COMPLETED_PARTIAL = "COMPLETED_PARTIAL"
    BLOCKED_MATERIAL_INPUT = "BLOCKED_MATERIAL_INPUT"
    AUTHORITY_REQUIRED = "AUTHORITY_REQUIRED"
    CAPABILITY_GAP = "CAPABILITY_GAP"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    REPAIR_UNAVAILABLE = "REPAIR_UNAVAILABLE"
    NO_PROGRESS = "NO_PROGRESS"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    DEADLINE_EXHAUSTED = "DEADLINE_EXHAUSTED"
    ABSTAINED = "ABSTAINED"
    CANCELLED = "CANCELLED"


RESOLUTION_FULFILLMENT_STATES = (
    "candidate_artifacts_available",
    "provisional_outputs_available",
    "analysis_and_plan_available",
    "constraint_report_only",
)

BEST_AVAILABLE_RESOLUTION_METHODS = (
    "analyze the available evidence and state what it supports",
    "map missing inputs, components, capabilities, and authority",
    "make explicit bounded assumptions and compare scenario branches",
    "produce a pro forma analysis from the available values",
    "use clearly labeled synthetic examples or data when they are useful",
    "give estimates or ranges with their basis and uncertainty",
    "adapt a similar or analogous solution and state where the analogy differs",
    "derive a first-principles approach from the task constraints",
    "prepare supplemental artifacts, templates, checks, and acquisition steps",
)

RESOLUTION_CONTRIBUTION_FIELDS = (
    "what_can_be_completed",
    "what_cannot_be_completed",
    "missing_inputs_or_components",
    "analysis",
    "assumptions",
    "scenario_analysis",
    "pro_forma_analysis",
    "synthetic_material",
    "estimates",
    "analogous_solutions",
    "first_principles_solutions",
    "supplemental_items",
    "next_actions",
)

RESOLUTION_METHOD_FIELDS = (
    ("available_evidence_analysis", ("what_can_be_completed", "analysis")),
    ("missing_piece_mapping", (
        "what_cannot_be_completed", "missing_inputs_or_components")),
    ("assumption_and_scenario_analysis", (
        "assumptions", "scenario_analysis")),
    ("pro_forma_analysis", ("pro_forma_analysis",)),
    ("synthetic_material", ("synthetic_material",)),
    ("bounded_estimation", ("estimates",)),
    ("analogous_solution", ("analogous_solutions",)),
    ("first_principles_solution", ("first_principles_solutions",)),
    ("supplemental_items", ("supplemental_items",)),
    ("next_action_plan", ("next_actions",)),
)
RESOLUTION_METHOD_IDS = tuple(item[0] for item in RESOLUTION_METHOD_FIELDS)
RESOLUTION_METHOD_DISPOSITIONS = (
    "completed", "not_applicable", "unavailable", "authority_required",
    "resource_exhausted")
RESOLUTION_REQUIRED_ACTION_KINDS = (
    "ASK_USER", "REQUEST_AUTHORITY", "RETURN_RESULT", "ABSTAIN", "STOP")

RESOLUTION_TRUTH_CONSTRAINTS = (
    "Label observed, derived, assumed, synthetic, estimated, and unverified "
    "material separately.",
    "Do not invent missing facts, permissions, independent verification, or "
    "completed external effects.",
    "Complete every safe reversible part of the work before reporting a "
    "remaining constraint.",
)


@dataclass(frozen=True)
class ResolutionCompletionPolicy:
    """Required best-available work before a task-level stop is published."""

    policy_id: str = "solve.best_available_resolution"
    version: str = "1.0.0"
    require_resolution_before_task_level_stop: bool = True
    require_every_method_assessed: bool = True
    require_completed_useful_work: bool = True
    methods: tuple[str, ...] = BEST_AVAILABLE_RESOLUTION_METHODS
    truth_constraints: tuple[str, ...] = RESOLUTION_TRUTH_CONSTRAINTS

    def to_dict(self) -> dict:
        return {
            "record_type": "resolution_completion_policy/v1",
            "policy_id": self.policy_id,
            "version": self.version,
            "require_resolution_before_task_level_stop":
                self.require_resolution_before_task_level_stop,
            "require_every_method_assessed": self.require_every_method_assessed,
            "require_completed_useful_work": self.require_completed_useful_work,
            "methods": list(self.methods),
            "method_ids": list(RESOLUTION_METHOD_IDS),
            "truth_constraints": list(self.truth_constraints),
        }


DEFAULT_RESOLUTION_COMPLETION_POLICY = ResolutionCompletionPolicy()


@dataclass(frozen=True)
class ResolutionMethodAssessment:
    """Disposition of one safe best-available-resolution method."""

    method_id: str
    disposition: str
    summary: str
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.method_id not in RESOLUTION_METHOD_IDS:
            raise ValueError("resolution method is not registered")
        if self.disposition not in RESOLUTION_METHOD_DISPOSITIONS:
            raise ValueError("resolution method disposition is not registered")
        if not isinstance(self.summary, str) or not self.summary.strip():
            raise ValueError("resolution method assessment needs a summary")
        refs = tuple(self.evidence_refs)
        if (len(refs) != len(set(refs))
                or any(not isinstance(item, str) or not item.strip()
                       for item in refs)):
            raise ValueError(
                "resolution method evidence refs must be unique non-empty text")
        object.__setattr__(self, "evidence_refs", refs)

    @classmethod
    def from_mapping(cls, value: object) -> "ResolutionMethodAssessment":
        if not isinstance(value, dict) or set(value) != {
                "method_id", "disposition", "summary", "evidence_refs"}:
            raise ValueError(
                "resolution method assessment fields do not match")
        refs = value.get("evidence_refs")
        if not isinstance(refs, list):
            raise ValueError("resolution method evidence_refs must be an array")
        return cls(
            str(value.get("method_id") or ""),
            str(value.get("disposition") or ""),
            str(value.get("summary") or ""), tuple(refs))

    def to_dict(self) -> dict:
        return {
            "record_type": "resolution_method_assessment/v1",
            "method_id": self.method_id,
            "disposition": self.disposition,
            "summary": self.summary,
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True)
class ProvisionalTaskOutput:
    """One model-authored output recovered before materialization or checking."""

    path: str
    content: str
    source_decision_id: str
    content_digest: str = ""

    def __post_init__(self) -> None:
        if not self.path.strip() or not self.content:
            raise ValueError("a provisional task output needs a path and content")
        expected = hashlib.sha256(self.content.encode("utf-8")).hexdigest()
        if self.content_digest and self.content_digest != expected:
            raise ValueError("provisional task output digest differs from its content")
        object.__setattr__(self, "content_digest", expected)

    def to_dict(self) -> dict:
        return {
            "record_type": "provisional_task_output/v1",
            "path": self.path,
            "content": self.content,
            "content_digest": self.content_digest,
            "source_decision_id": self.source_decision_id,
            "materialized": False,
            "verified": False,
        }


@dataclass(frozen=True)
class TaskResolutionPackage:
    """A complete useful response when the requested outcome is not verified."""

    requested_outcome: str
    fulfillment_status: str
    underlying_terminal: str
    method_assessments: tuple[ResolutionMethodAssessment, ...]
    completed_work: tuple[str, ...] = ()
    observed_evidence: tuple[str, ...] = ()
    model_analysis: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    cannot_complete: tuple[str, ...] = ()
    missing_inputs_or_components: tuple[str, ...] = ()
    missing_or_unverified: tuple[str, ...] = ()
    scenario_options: tuple[str, ...] = ()
    pro_forma_analysis: tuple[str, ...] = ()
    synthetic_material: tuple[str, ...] = ()
    estimates: tuple[str, ...] = ()
    analogous_solutions: tuple[str, ...] = ()
    first_principles_solutions: tuple[str, ...] = ()
    supplemental_items: tuple[str, ...] = ()
    alternative_approaches: tuple[str, ...] = ()
    provisional_outputs: tuple[ProvisionalTaskOutput, ...] = ()
    questions_for_improvement: tuple[str, ...] = ()
    next_actions: tuple[str, ...] = ()
    best_available_result: object = None
    policy: ResolutionCompletionPolicy = field(
        default_factory=ResolutionCompletionPolicy)

    def __post_init__(self) -> None:
        if not self.requested_outcome.strip():
            raise ValueError("task resolution needs the requested outcome")
        if self.fulfillment_status not in RESOLUTION_FULFILLMENT_STATES:
            raise ValueError("task resolution fulfillment status is invalid")
        if not self.underlying_terminal.strip():
            raise ValueError("task resolution needs its underlying terminal")
        if not isinstance(self.policy, ResolutionCompletionPolicy):
            raise TypeError("task resolution needs a typed completion policy")
        methods = tuple(self.method_assessments)
        if (len(methods) != len(RESOLUTION_METHOD_IDS)
                or {item.method_id for item in methods}
                != set(RESOLUTION_METHOD_IDS)):
            raise ValueError(
                "task resolution must assess every registered method exactly once")
        if (self.policy.require_completed_useful_work
                and not any(item.disposition == "completed" for item in methods)):
            raise ValueError(
                "task resolution needs at least one completed useful method")
        object.__setattr__(self, "method_assessments", methods)

    @property
    def response_complete(self) -> bool:
        return bool(
            len(self.method_assessments) == len(RESOLUTION_METHOD_IDS)
            and {item.method_id for item in self.method_assessments}
            == set(RESOLUTION_METHOD_IDS)
            and any(item.disposition == "completed"
                    for item in self.method_assessments))

    def report(self) -> str:
        """Render the structured resolution as a compact readable report."""
        lines = [
            "# Best available task resolution",
            "",
            f"Requested outcome: {self.requested_outcome}",
            f"Fulfillment status: {self.fulfillment_status}",
            f"Remaining constraint: {self.underlying_terminal}",
        ]

        def section(title: str, values: tuple[str, ...]) -> None:
            lines.extend(("", f"## {title}"))
            lines.extend((f"- {value}" for value in values)
                         if values else ("- None recorded.",))

        section("Completed work", self.completed_work)
        section("Observed evidence", self.observed_evidence)
        section("Analysis from the Practitioner", self.model_analysis)
        section("Assumptions", self.assumptions)
        section("What cannot be completed", self.cannot_complete)
        section("Missing inputs or components", self.missing_inputs_or_components)
        section("Missing or unverified", self.missing_or_unverified)
        section("Scenario and delegated choices", self.scenario_options)
        section("Pro forma analysis", self.pro_forma_analysis)
        section("Synthetic material", self.synthetic_material)
        section("Estimates", self.estimates)
        section("Analogous solutions", self.analogous_solutions)
        section("First-principles solutions", self.first_principles_solutions)
        section("Supplemental items", self.supplemental_items)
        section("Alternative approaches", self.alternative_approaches)
        section("Questions that could improve the result",
                self.questions_for_improvement)
        section("Next actions", self.next_actions)
        lines.extend(("", "## Resolution method coverage"))
        lines.extend(
            f"- {item.method_id}: {item.disposition}. {item.summary}"
            for item in self.method_assessments)
        section("Additional safe methods available", self.policy.methods)
        return "\n".join(lines) + "\n"

    def to_dict(self) -> dict:
        return {
            "record_type": "task_resolution_package/v1",
            "response_complete": self.response_complete,
            "resolution_status": (
                "COMPLETE" if self.response_complete else "INCOMPLETE"),
            "requested_outcome_verified": False,
            "requested_outcome_status": "UNVERIFIED",
            "requested_outcome": self.requested_outcome,
            "fulfillment_status": self.fulfillment_status,
            "underlying_terminal": self.underlying_terminal,
            "method_assessments": [
                item.to_dict() for item in self.method_assessments],
            "completed_work": list(self.completed_work),
            "observed_evidence": list(self.observed_evidence),
            "model_analysis": list(self.model_analysis),
            "assumptions": list(self.assumptions),
            "cannot_complete": list(self.cannot_complete),
            "missing_inputs_or_components":
                list(self.missing_inputs_or_components),
            "missing_or_unverified": list(self.missing_or_unverified),
            "scenario_options": list(self.scenario_options),
            "pro_forma_analysis": list(self.pro_forma_analysis),
            "synthetic_material": list(self.synthetic_material),
            "estimates": list(self.estimates),
            "analogous_solutions": list(self.analogous_solutions),
            "first_principles_solutions": list(
                self.first_principles_solutions),
            "supplemental_items": list(self.supplemental_items),
            "alternative_approaches": list(self.alternative_approaches),
            "provisional_outputs": [
                item.to_dict() for item in self.provisional_outputs],
            "questions_for_improvement": list(self.questions_for_improvement),
            "next_actions": list(self.next_actions),
            "best_available_result": self.best_available_result,
            "resolution_policy": self.policy.to_dict(),
            "report": self.report(),
        }


def _unique_text(values) -> tuple[str, ...]:
    output = []
    for value in values or ():
        if isinstance(value, str) and value.strip() and value.strip() not in output:
            output.append(value.strip())
    return tuple(output)


def _provisional_outputs(adaptive: dict) -> tuple[ProvisionalTaskOutput, ...]:
    """Recover the latest unmaterialized file body per proposed path."""
    by_path: dict[str, ProvisionalTaskOutput] = {}
    for decision in adaptive.get("action_decisions") or ():
        if not isinstance(decision, dict):
            continue
        inputs = decision.get("inputs")
        files = inputs.get("files") if isinstance(inputs, dict) else None
        if not isinstance(files, dict):
            continue
        for path, content in files.items():
            if (isinstance(path, str) and isinstance(content, str)
                    and path.strip() and content):
                by_path[path] = ProvisionalTaskOutput(
                    path, content, str(decision.get("decision_id") or ""))
    return tuple(by_path[path] for path in sorted(by_path))


def resolution_input_contract() -> dict:
    """Model-facing fields for a direct best-available resolution."""
    return {"resolution": {
        **{field_name: ["string"]
           for field_name in RESOLUTION_CONTRIBUTION_FIELDS},
        "constraint_code": sorted(_RESOLUTION_COMPLETABLE_TERMINALS),
        "method_assessments": [{
            "method_id": list(RESOLUTION_METHOD_IDS),
            "disposition": "completed|not_applicable|unavailable|authority_required|resource_exhausted",
            "summary": "why this disposition is correct",
            "evidence_refs": ["optional typed reference"],
        }],
    }}


def validate_resolution_input(inputs: object) -> dict:
    """Validate a direct RETURN_RESULT contribution before it is selected."""
    if not isinstance(inputs, dict) or set(inputs) != {"resolution"}:
        raise ValueError(
            "RETURN_RESULT without an existing result requires inputs with "
            "the exact field resolution")
    resolution = inputs.get("resolution")
    if not isinstance(resolution, dict):
        raise ValueError("inputs.resolution must be an object")
    expected = {
        *RESOLUTION_CONTRIBUTION_FIELDS, "constraint_code",
        "method_assessments"}
    if set(resolution) != expected:
        raise ValueError(
            "inputs.resolution fields must be exactly "
            + ",".join(RESOLUTION_CONTRIBUTION_FIELDS))
    normalized = {}
    for name in RESOLUTION_CONTRIBUTION_FIELDS:
        values = resolution[name]
        if (not isinstance(values, list)
                or any(not isinstance(item, str) or not item.strip()
                       for item in values)):
            raise ValueError(
                f"inputs.resolution.{name} must be an array of nonempty text")
        normalized[name] = list(values)
    constraint_code = resolution.get("constraint_code")
    if constraint_code not in _RESOLUTION_COMPLETABLE_TERMINALS:
        raise ValueError(
            "inputs.resolution.constraint_code must name a task-level constraint")
    normalized["constraint_code"] = constraint_code
    raw_assessments = resolution.get("method_assessments")
    if not isinstance(raw_assessments, list):
        raise ValueError("inputs.resolution.method_assessments must be an array")
    assessments = tuple(
        ResolutionMethodAssessment.from_mapping(item)
        for item in raw_assessments)
    if (len(assessments) != len(RESOLUTION_METHOD_IDS)
            or {item.method_id for item in assessments}
            != set(RESOLUTION_METHOD_IDS)):
        raise ValueError(
            "inputs.resolution must assess every registered method exactly once")
    fields_by_method = dict(RESOLUTION_METHOD_FIELDS)
    for assessment in assessments:
        has_content = any(
            normalized[name] for name in fields_by_method[assessment.method_id])
        if (assessment.disposition == "completed") is not has_content:
            raise ValueError(
                f"resolution method {assessment.method_id} disposition and "
                "contribution content disagree")
    if not any(item.disposition == "completed" for item in assessments):
        raise ValueError("inputs.resolution must complete at least one useful method")
    normalized["method_assessments"] = [{
        "method_id": item.method_id,
        "disposition": item.disposition,
        "summary": item.summary,
        "evidence_refs": list(item.evidence_refs),
    } for item in assessments]
    return normalized


def _resolution_contribution(adaptive: dict) -> dict:
    for decision in reversed(adaptive.get("action_decisions") or ()):
        if not isinstance(decision, dict):
            continue
        inputs = decision.get("inputs")
        resolution = inputs.get("resolution") if isinstance(inputs, dict) else None
        if isinstance(resolution, dict):
            return {
                **{name: resolution.get(name) or ()
                   for name in RESOLUTION_CONTRIBUTION_FIELDS},
                "constraint_code": str(
                    resolution.get("constraint_code") or ""),
                "method_assessments": resolution.get("method_assessments") or (),
            }
    return {}


def _default_method_disposition(terminal: str) -> str:
    if terminal == SolveTerminalCode.AUTHORITY_REQUIRED.value:
        return "authority_required"
    if terminal in (
            SolveTerminalCode.BUDGET_EXHAUSTED.value,
            SolveTerminalCode.DEADLINE_EXHAUSTED.value):
        return "resource_exhausted"
    return "unavailable"


def _assess_resolution_methods(
        contribution: dict, values_by_field: dict[str, tuple[str, ...]],
        terminal: str) -> tuple[ResolutionMethodAssessment, ...]:
    """Validate model coverage or derive honest operational dispositions."""
    raw = contribution.get("method_assessments") or ()
    if raw:
        assessments = tuple(
            ResolutionMethodAssessment.from_mapping(item) for item in raw)
        if (len(assessments) != len(RESOLUTION_METHOD_IDS)
                or {item.method_id for item in assessments}
                != set(RESOLUTION_METHOD_IDS)):
            raise ValueError(
                "resolution contribution must assess every method exactly once")
        by_method = dict(RESOLUTION_METHOD_FIELDS)
        for item in assessments:
            has_content = any(
                values_by_field.get(name) for name in by_method[item.method_id])
            if (item.disposition == "completed") is not bool(has_content):
                raise ValueError(
                    f"resolution method {item.method_id} does not match the "
                    "material preserved in the package")
        return assessments

    unavailable = _default_method_disposition(terminal)
    assessments = []
    for method_id, field_names in RESOLUTION_METHOD_FIELDS:
        completed_fields = tuple(
            name for name in field_names if values_by_field.get(name))
        if completed_fields:
            assessments.append(ResolutionMethodAssessment(
                method_id, "completed",
                "Completed material is preserved in "
                + ", ".join(completed_fields) + ".",
                tuple(f"resolution.{name}" for name in completed_fields)))
        else:
            assessments.append(ResolutionMethodAssessment(
                method_id, unavailable,
                f"No result for this method was available before {terminal}."))
    return tuple(assessments)


def _question_texts(questions) -> tuple[str, ...]:
    return _unique_text(
        item if isinstance(item, str)
        else item.get("question") if isinstance(item, dict)
        else getattr(item, "question", "") for item in questions or ())


def build_task_resolution_package(*, task: str, adaptive: dict, product: dict,
                                  underlying_terminal: str, questions=(),
                                  limitations=(), suggested_next: str = "",
                                  policy: ResolutionCompletionPolicy =
                                  DEFAULT_RESOLUTION_COMPLETION_POLICY,
                                  ) -> TaskResolutionPackage:
    """Preserve useful work and remaining constraints in one returned result."""
    orientations = [item for item in adaptive.get("orientations") or ()
                    if isinstance(item, dict)]
    orientation = orientations[-1] if orientations else {}
    project_attempts = [item for item in adaptive.get("project_attempts") or ()
                        if isinstance(item, dict)]
    artifacts = [item for item in product.get("artifacts") or ()
                 if isinstance(item, dict)]
    provisional = _provisional_outputs(adaptive)
    contribution = _resolution_contribution(adaptive)
    underlying_terminal = str(
        contribution.get("constraint_code") or underlying_terminal)

    observed = []
    completed = []
    for item in artifacts:
        path = str(item.get("path") or "unnamed artifact")
        digest = str(item.get("digest") or "digest unavailable")
        observed.append(f"Artifact {path}, digest {digest}.")
        completed.append(
            f"Produced candidate artifact {path}; recorded file checks "
            f"{'passed' if item.get('verified') else 'remain unconfirmed'}.")
    for inspection in adaptive.get("source_inspections") or ():
        if not isinstance(inspection, dict):
            continue
        for item in inspection.get("selected") or ():
            if not isinstance(item, dict):
                continue
            path = str(item.get("path") or "unnamed source")
            digest = str(item.get("digest") or "digest unavailable")
            observed.append(f"Inspected source {path}, digest {digest}.")
            completed.append(f"Inspected source {path}.")
    for item in adaptive.get("web_evidence") or ():
        if isinstance(item, dict):
            observed.append(
                "Fetched source " + str(item.get("final_url") or "unknown URL")
                + ", digest " + str(item.get("sha256") or "unavailable") + ".")
    for attempt in project_attempts:
        digest = str(attempt.get("manifest_digest") or "unavailable")
        passed = attempt.get("deterministic_checks_passed") is True
        observed.append(
            f"Project attempt {digest} deterministic checks "
            f"{'passed' if passed else 'did not pass'}.")
    for item in provisional:
        completed.append(
            f"Prepared provisional output {item.path}; it was not materialized or verified.")
    completed.extend(contribution.get("what_can_be_completed") or ())

    verification = [item for item in adaptive.get("verification") or ()
                    if isinstance(item, dict)]
    latest_verification = verification[-1] if verification else {}
    operational = [
        str(item.get("reason") or item.get("status") or "verification unavailable")
        for item in latest_verification.get("operational_failures") or ()
        if isinstance(item, dict)]
    failures = adaptive.get("failures") or ()
    if isinstance(failures, str):
        failures = (failures,)
    failure = adaptive.get("failure")

    alternatives = []
    for directive in adaptive.get("recovery_directives") or ():
        if not isinstance(directive, dict):
            continue
        alternatives.append(str(directive.get("directive") or ""))
        for proposal in directive.get("proposals") or ():
            if isinstance(proposal, dict):
                alternatives.append(str(proposal.get("directive") or ""))

    requested_outcome = str(
        orientation.get("ultimate_goal") or orientation.get("desired_state")
        or task).strip()
    analysis = _unique_text((
        orientation.get("task_summary"), orientation.get("current_state"),
        *(orientation.get("knowns") or ()),
        *(contribution.get("analysis") or ())))
    missing_components = _unique_text(
        contribution.get("missing_inputs_or_components") or ())
    missing = _unique_text((
        *(orientation.get("unknowns") or ()),
        *missing_components,
        *(latest_verification.get("remaining_gaps") or ()),
        *operational, *failures,
        *((failure,) if isinstance(failure, str) else ()),
        *limitations,
    ))
    scenarios = _unique_text((
        *(orientation.get("delegated_choices") or ()),
        *(orientation.get("safe_defaults") or ()),
        *(orientation.get("parallel_candidates") or ()),
        *(contribution.get("scenario_analysis") or ()),
    ))
    next_actions = _unique_text((
        orientation.get("proposed_next_action"),
        *(contribution.get("next_actions") or ()),
        alternatives[-1] if alternatives else "",
        suggested_next,
    ))
    completed_work = _unique_text(completed)
    observed_evidence = _unique_text(observed)
    assumptions = _unique_text((
        *(orientation.get("assumptions") or ()),
        *(contribution.get("assumptions") or ())))
    cannot_complete = _unique_text(
        contribution.get("what_cannot_be_completed") or ())
    pro_forma = _unique_text(contribution.get("pro_forma_analysis") or ())
    synthetic = _unique_text(contribution.get("synthetic_material") or ())
    estimates = _unique_text(contribution.get("estimates") or ())
    analogous = _unique_text(contribution.get("analogous_solutions") or ())
    first_principles = _unique_text(
        contribution.get("first_principles_solutions") or ())
    supplemental = _unique_text(contribution.get("supplemental_items") or ())
    method_values = {
        "what_can_be_completed": completed_work,
        "what_cannot_be_completed": cannot_complete,
        "missing_inputs_or_components": missing_components,
        "analysis": analysis,
        "assumptions": assumptions,
        "scenario_analysis": scenarios,
        "pro_forma_analysis": pro_forma,
        "synthetic_material": synthetic,
        "estimates": estimates,
        "analogous_solutions": analogous,
        "first_principles_solutions": first_principles,
        "supplemental_items": supplemental,
        "next_actions": next_actions,
    }
    method_assessments = _assess_resolution_methods(
        contribution, method_values, underlying_terminal)
    fulfillment = (
        "candidate_artifacts_available" if artifacts
        else "provisional_outputs_available" if provisional
        else "analysis_and_plan_available" if (
            analysis or scenarios or alternatives or contribution)
        else "constraint_report_only")
    return TaskResolutionPackage(
        requested_outcome=requested_outcome,
        fulfillment_status=fulfillment,
        underlying_terminal=underlying_terminal,
        method_assessments=method_assessments,
        completed_work=completed_work,
        observed_evidence=observed_evidence,
        model_analysis=analysis,
        assumptions=assumptions,
        cannot_complete=cannot_complete,
        missing_inputs_or_components=missing_components,
        missing_or_unverified=missing,
        scenario_options=scenarios,
        pro_forma_analysis=pro_forma,
        synthetic_material=synthetic,
        estimates=estimates,
        analogous_solutions=analogous,
        first_principles_solutions=first_principles,
        supplemental_items=supplemental,
        alternative_approaches=_unique_text(alternatives),
        provisional_outputs=provisional,
        questions_for_improvement=_question_texts(questions),
        next_actions=next_actions,
        best_available_result=product.get("result"),
        policy=policy,
    )


_RESOLUTION_COMPLETABLE_TERMINALS = frozenset({
    SolveTerminalCode.BLOCKED_MATERIAL_INPUT.value,
    SolveTerminalCode.AUTHORITY_REQUIRED.value,
    SolveTerminalCode.CAPABILITY_GAP.value,
    SolveTerminalCode.VERIFICATION_FAILED.value,
    SolveTerminalCode.REPAIR_UNAVAILABLE.value,
    SolveTerminalCode.NO_PROGRESS.value,
    SolveTerminalCode.BUDGET_EXHAUSTED.value,
    SolveTerminalCode.DEADLINE_EXHAUSTED.value,
    SolveTerminalCode.ABSTAINED.value,
})


def terminal_with_resolution(underlying_terminal: str) -> str:
    """Return completed partial for a useful task-level resolution package."""
    return (SolveTerminalCode.COMPLETED_PARTIAL.value
            if underlying_terminal in _RESOLUTION_COMPLETABLE_TERMINALS
            else underlying_terminal)


SOLVE_FAILURE_CODES = tuple(
    item.value for item in SolveTerminalCode
    if item is not SolveTerminalCode.COMPLETED_VERIFIED)


def failure_code_for(result: dict) -> str:
    code = str(result.get("failure_code") or "")
    if code in ("NO_VERIFIED_CAPABILITY", "EXECUTOR_UNAVAILABLE"):
        return SolveTerminalCode.CAPABILITY_GAP.value
    if code == "CANCELLED":
        return SolveTerminalCode.CANCELLED.value
    if code == "model_call_budget_exhausted":
        return SolveTerminalCode.BUDGET_EXHAUSTED.value
    if code in (
            "SolutionModelError", "MODEL_PROVIDER_UNAVAILABLE",
            "model_gateway_failed", "no_eligible_route",
            "provider_not_configured", "missing_credential",
            "authentication_failed", "payment_required", "model_not_found",
            "rate_limited", "usage_limit_reached", "provider_unavailable",
            "invalid_response_body", "timeout", "provider_failed"):
        return SolveTerminalCode.PROVIDER_UNAVAILABLE.value
    if code in ("PermissionError", "PERMISSION_DENIED"):
        return SolveTerminalCode.AUTHORITY_REQUIRED.value
    if code == "OUTPUT_CONTRACT_VIOLATION":
        return SolveTerminalCode.VERIFICATION_FAILED.value
    # A Python exception class name says which module raised, not which layer
    # failed. AdaptivePractitionerError was mapped straight to
    # VERIFICATION_FAILED, so a live run that produced two invalid
    # orientations and never verified anything still reported a verification
    # failure. Generic class names defer to the evidence below.
    if code in ("NO_PROGRESS", "stop_unprofitable"):
        return SolveTerminalCode.NO_PROGRESS.value
    # Only claim verification failed if the run reached verification. A run
    # whose provider never answered has a transport failure, and saying so
    # is the difference between one fix and a week of looking in the wrong
    # subsystem.
    reached = deepest_layer_reached(result)
    if reached == "transport":
        return SolveTerminalCode.PROVIDER_UNAVAILABLE.value
    if reached == "semantic":
        return SolveTerminalCode.NO_PROGRESS.value
    return SolveTerminalCode.VERIFICATION_FAILED.value


def self_test() -> dict:
    """Run static terminal and resolution checks from their fixture module."""
    from .solve_terminal_checks import run_checks
    return run_checks()
