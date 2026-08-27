"""Template model: typed task templates and binding modes.

A template standardizes freeform text into typed variables. The
binding is open-set: exact, composite, partial, ambiguous, open, or
new-template-candidate. The original input is never replaced.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum

#: Binding modes a compiler may return.
BINDING_MODES = (
    "exact", "composite", "partial", "ambiguous", "open",
    "new_template_candidate",
)

#: Task types a template may declare.
TASK_TYPES = (
    "classification", "regression", "ranking", "prediction",
    "optimization", "recommendation", "monitoring", "transformation",
    "validation", "generation", "retrieval", "comparison", "migration",
    "audit", "unknown",
)

#: Output kinds a template may request.
OUTPUT_KINDS = (
    "label", "probability", "score", "ranked_list", "report", "artifact",
    "code", "config", "graph", "service", "decision", "unknown",
)

WORK_OPERATORS = (
    "retrieve", "search", "browse", "extract", "validate", "classify",
    "score", "rank", "estimate", "predict", "forecast", "detect",
    "cluster", "match", "resolve_entities", "recommend", "optimize",
    "plan", "diagnose", "explain", "infer_causally", "simulate",
    "generate", "summarize", "monitor", "decide", "learn", "transform",
    "unknown",
)

RESPONSE_TOPOLOGIES = (
    "boolean", "label", "score", "scalar", "probability", "interval",
    "distribution", "list", "ranked_list", "table", "matrix", "hierarchy",
    "graph", "timeline", "scenario_tree", "plan", "schedule", "policy",
    "action", "artifact", "alert", "abstention", "unknown",
)


class TemplateError(ValueError):
    """A template or binding violated its contract."""


class InteractionMode(str, Enum):
    """Whether unresolved material choices may request user input."""

    ASK_WHEN_MATERIAL = "ask_when_material"
    AUTONOMOUS = "autonomous"


class RequirementDispositionState(str, Enum):
    """How one required template value may be resolved after compilation."""

    PROVIDED = "provided"
    DELEGATED_CHOICE = "delegated_choice"
    NEEDS_CLARIFICATION = "needs_clarification"
    ABSTAIN_REQUIRED = "abstain_required"


@dataclass(frozen=True)
class TaskFeedback:
    """Optional invocation input for one registered task feedback slot."""

    slot_ref: str
    value: str

    def __post_init__(self) -> None:
        for name in ("slot_ref", "value"):
            item = getattr(self, name)
            if not isinstance(item, str) or not item.strip():
                raise TemplateError(f"{name} must be a non-empty string")

    def to_dict(self) -> dict:
        return {"slot_ref": self.slot_ref, "value": self.value}


@dataclass(frozen=True)
class RequirementDisposition:
    """One unresolved or supplied requirement with a typed next action."""

    requirement_id: str
    state: RequirementDispositionState
    reason_code: str
    constraint_refs: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()
    feedback_slot_ref: str = ""

    def __post_init__(self) -> None:
        for name in ("requirement_id", "reason_code"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise TemplateError(f"{name} must be a non-empty string")
        if not isinstance(self.feedback_slot_ref, str):
            raise TemplateError("feedback_slot_ref must be a string")
        state = self.state
        if not isinstance(state, RequirementDispositionState):
            try:
                state = RequirementDispositionState(state)
            except (TypeError, ValueError) as exc:
                raise TemplateError(
                    "requirement disposition state is not recognized") from exc
            object.__setattr__(self, "state", state)
        for name in ("constraint_refs", "depends_on"):
            values = tuple(getattr(self, name))
            if (any(not isinstance(value, str) or not value.strip()
                    for value in values)
                    or len(values) != len(set(values))):
                raise TemplateError(
                    f"{name} must contain unique non-empty references")
            object.__setattr__(self, name, values)

    def to_dict(self) -> dict:
        return {
            "requirement_id": self.requirement_id,
            "state": self.state.value,
            "reason_code": self.reason_code,
            "constraint_refs": list(self.constraint_refs),
            "depends_on": list(self.depends_on),
            "feedback_slot_ref": self.feedback_slot_ref,
        }


@dataclass(frozen=True)
class RequirementPolicy:
    """Template-owned rules for asking or accepting delegated choice."""

    requirement_id: str
    allow_delegated_choice: bool = False
    delegation_cues: tuple[str, ...] = ()
    clarification_cues: tuple[str, ...] = ()
    constraint_refs: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()
    feedback_slot_ref: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.requirement_id, str) \
                or not self.requirement_id.strip():
            raise TemplateError("requirement_id must be a non-empty string")
        if not isinstance(self.allow_delegated_choice, bool):
            raise TemplateError("allow_delegated_choice must be a boolean")
        if not isinstance(self.feedback_slot_ref, str):
            raise TemplateError("feedback_slot_ref must be a string")
        for name in (
                "delegation_cues", "clarification_cues", "constraint_refs",
                "depends_on"):
            values = tuple(getattr(self, name))
            if (any(not isinstance(value, str) or not value.strip()
                    for value in values)
                    or len(values) != len(set(values))):
                raise TemplateError(
                    f"{name} must contain unique non-empty strings")
            object.__setattr__(self, name, values)
        if self.allow_delegated_choice \
                and (not self.delegation_cues or not self.constraint_refs):
            raise TemplateError(
                "delegated choice needs cues and constraint references")
        if not self.allow_delegated_choice and self.delegation_cues:
            raise TemplateError(
                "delegation cues require allow_delegated_choice")

    def resolve(
            self, text: str, provided: bool,
            interaction_mode: InteractionMode = (
                InteractionMode.ASK_WHEN_MATERIAL)) -> RequirementDisposition:
        if not isinstance(interaction_mode, InteractionMode):
            try:
                interaction_mode = InteractionMode(interaction_mode)
            except (TypeError, ValueError) as exc:
                raise TemplateError("interaction mode is not recognized") from exc
        if provided:
            return RequirementDisposition(
                self.requirement_id,
                RequirementDispositionState.PROVIDED,
                "explicit_value",
                depends_on=self.depends_on,
                feedback_slot_ref=self.feedback_slot_ref)
        normalized = " ".join(text.casefold().split())
        clarification_required = any(
            cue.casefold() in normalized for cue in self.clarification_cues)
        delegated = (not clarification_required
                     and self.allow_delegated_choice
                     and (interaction_mode == InteractionMode.AUTONOMOUS
                          or any(cue.casefold() in normalized
                                 for cue in self.delegation_cues)))
        abstain = (not delegated
                   and interaction_mode == InteractionMode.AUTONOMOUS)
        return RequirementDisposition(
            self.requirement_id,
            (RequirementDispositionState.DELEGATED_CHOICE if delegated
             else RequirementDispositionState.ABSTAIN_REQUIRED if abstain
             else RequirementDispositionState.NEEDS_CLARIFICATION),
            ("user_delegated_choice" if delegated else
             "autonomous_run_cannot_resolve_safely" if abstain else
             "delegation_explicitly_withheld" if clarification_required else
             "required_value_missing"),
            constraint_refs=(self.constraint_refs if delegated else ()),
            depends_on=self.depends_on,
            feedback_slot_ref=self.feedback_slot_ref)

    def to_dict(self) -> dict:
        return {
            "requirement_id": self.requirement_id,
            "allow_delegated_choice": self.allow_delegated_choice,
            "delegation_cues": list(self.delegation_cues),
            "clarification_cues": list(self.clarification_cues),
            "constraint_refs": list(self.constraint_refs),
            "depends_on": list(self.depends_on),
            "feedback_slot_ref": self.feedback_slot_ref,
        }


@dataclass(frozen=True)
class SemanticCoordinates:
    """Question, Operator, Response, and Decision remain separate contracts."""

    question: str
    operator: str = "unknown"
    response_topology: str = "unknown"
    decision_consumer: str = "return_verified_result"

    def __post_init__(self) -> None:
        if not self.question.strip():
            raise TemplateError("semantic coordinates need a question")
        if self.operator not in WORK_OPERATORS:
            raise TemplateError(f"operator must be one of {WORK_OPERATORS}")
        if self.response_topology not in RESPONSE_TOPOLOGIES:
            raise TemplateError(
                f"response_topology must be one of {RESPONSE_TOPOLOGIES}")
        if not self.decision_consumer.strip():
            raise TemplateError("decision_consumer must be explicit")

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "operator": self.operator,
            "response_topology": self.response_topology,
            "decision_consumer": self.decision_consumer,
        }


@dataclass(frozen=True)
class WorkItemIR:
    """Small typed intermediate representation shared by every intake form."""

    work_item_id: str
    source_kind: str
    original_input: str
    normalized_interpretation: str
    coordinates: SemanticCoordinates
    source_refs: tuple[str, ...] = ()
    acceptance_criteria: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    known_facts: tuple[str, ...] = ()
    unknowns: tuple[str, ...] = ()
    requirement_dispositions: tuple[RequirementDisposition, ...] = ()
    tags: tuple[str, ...] = ()
    risk: str = "unknown"
    consequence: str = "unknown"
    privacy_scope: str = "project"
    provenance: str = ""

    def __post_init__(self) -> None:
        if not self.work_item_id or not self.source_kind:
            raise TemplateError("WorkItemIR needs identity and source_kind")
        if not self.original_input:
            raise TemplateError("WorkItemIR preserves a non-empty original_input")
        dispositions = tuple(self.requirement_dispositions)
        if any(not isinstance(value, RequirementDisposition)
               for value in dispositions):
            raise TemplateError(
                "requirement_dispositions must be typed records")
        requirement_ids = tuple(value.requirement_id for value in dispositions)
        if len(requirement_ids) != len(set(requirement_ids)):
            raise TemplateError("WorkItemIR requirement dispositions cannot repeat")
        object.__setattr__(self, "requirement_dispositions", dispositions)

    def to_dict(self) -> dict:
        return {
            "record_type": "work_item_ir/v1",
            "work_item_id": self.work_item_id,
            "source_kind": self.source_kind,
            "original_input": self.original_input,
            "normalized_interpretation": self.normalized_interpretation,
            "coordinates": self.coordinates.to_dict(),
            "source_refs": list(self.source_refs),
            "acceptance_criteria": list(self.acceptance_criteria),
            "constraints": list(self.constraints),
            "known_facts": list(self.known_facts),
            "unknowns": list(self.unknowns),
            "requirement_dispositions": [
                item.to_dict() for item in self.requirement_dispositions],
            "tags": list(self.tags),
            "risk": self.risk,
            "consequence": self.consequence,
            "privacy_scope": self.privacy_scope,
            "provenance": self.provenance,
        }


@dataclass(frozen=True)
class TaskTemplate:
    """One versioned task template with a JSON variable schema."""

    template_id: str
    version: str
    name: str
    description: str = ""
    task_type: str = "unknown"
    output_kind: str = "unknown"
    variables: dict = field(default_factory=dict)
    required_variables: tuple[str, ...] = ()
    optional_variables: tuple[str, ...] = ()
    requirement_policies: tuple[RequirementPolicy, ...] = ()
    file_refs: tuple[str, ...] = ()
    input_contract: str = ""
    output_contract: str = ""
    maturity: str = "registered"

    def __post_init__(self) -> None:
        if self.task_type not in TASK_TYPES:
            raise TemplateError(f"task_type must be one of {TASK_TYPES}")
        if self.output_kind not in OUTPUT_KINDS:
            raise TemplateError(f"output_kind must be one of {OUTPUT_KINDS}")
        if self.maturity not in ("registered", "candidate", "deprecated"):
            raise TemplateError(
                "maturity must be registered, candidate, or deprecated")
        for name in self.required_variables:
            if name not in self.variables:
                raise TemplateError(
                    f"required variable {name!r} missing from variables")
        policies = tuple(self.requirement_policies)
        if any(not isinstance(policy, RequirementPolicy) for policy in policies):
            raise TemplateError("requirement_policies must be typed policies")
        policy_ids = tuple(policy.requirement_id for policy in policies)
        if len(policy_ids) != len(set(policy_ids)):
            raise TemplateError("requirement policy IDs cannot repeat")
        if any(name not in self.required_variables for name in policy_ids):
            raise TemplateError(
                "requirement policies may target only required variables")
        object.__setattr__(self, "requirement_policies", policies)

    def content_digest(self) -> str:
        serialized = json.dumps({
            "template_id": self.template_id, "version": self.version,
            "name": self.name, "task_type": self.task_type,
            "output_kind": self.output_kind, "variables": self.variables,
            "required_variables": list(self.required_variables),
            "optional_variables": list(self.optional_variables),
            "requirement_policies": [
                policy.to_dict() for policy in self.requirement_policies],
            "file_refs": list(self.file_refs),
        }, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict:
        return {
            "template_id": self.template_id, "version": self.version,
            "name": self.name, "description": self.description,
            "task_type": self.task_type, "output_kind": self.output_kind,
            "variables": dict(self.variables),
            "required_variables": list(self.required_variables),
            "optional_variables": list(self.optional_variables),
            "requirement_policies": [
                policy.to_dict() for policy in self.requirement_policies],
            "file_refs": list(self.file_refs),
            "input_contract": self.input_contract,
            "output_contract": self.output_contract,
            "maturity": self.maturity,
        }


@dataclass(frozen=True)
class TemplateBinding:
    """One binding decision: which template, which mode, what remains."""

    template_id: str
    template_version: str
    binding_mode: str
    confidence: float = 1.0
    mapped_variables: dict = field(default_factory=dict)
    unmapped_requirements: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    ambiguities: tuple[str, ...] = ()
    rejected_bindings: tuple[str, ...] = ()
    rejection_reasons: tuple[str, ...] = ()
    requirement_dispositions: tuple[RequirementDisposition, ...] = ()

    def __post_init__(self) -> None:
        if self.binding_mode not in BINDING_MODES:
            raise TemplateError(
                f"binding_mode must be one of {BINDING_MODES}")
        if not 0.0 <= self.confidence <= 1.0:
            raise TemplateError("confidence must be in [0, 1]")
        dispositions = tuple(self.requirement_dispositions)
        if any(not isinstance(value, RequirementDisposition)
               for value in dispositions):
            raise TemplateError(
                "requirement_dispositions must be typed records")
        requirement_ids = tuple(value.requirement_id for value in dispositions)
        if len(requirement_ids) != len(set(requirement_ids)):
            raise TemplateError("requirement dispositions cannot repeat")
        if self.template_id and not set(self.unmapped_requirements).issubset(
                requirement_ids):
            raise TemplateError(
                "every unmapped template requirement needs a disposition")
        object.__setattr__(self, "requirement_dispositions", dispositions)

    @property
    def requires_clarification(self) -> bool:
        return any(
            item.state == RequirementDispositionState.NEEDS_CLARIFICATION
            for item in self.requirement_dispositions)

    @property
    def requires_abstention(self) -> bool:
        return any(
            item.state == RequirementDispositionState.ABSTAIN_REQUIRED
            for item in self.requirement_dispositions)

    @property
    def can_continue_without_user_input(self) -> bool:
        return not self.requires_clarification and not self.requires_abstention

    @property
    def delegated_requirements(self) -> tuple[str, ...]:
        return tuple(
            item.requirement_id for item in self.requirement_dispositions
            if item.state == RequirementDispositionState.DELEGATED_CHOICE)

    def to_dict(self) -> dict:
        return {
            "template_id": self.template_id,
            "template_version": self.template_version,
            "binding_mode": self.binding_mode,
            "confidence": self.confidence,
            "mapped_variables": dict(self.mapped_variables),
            "unmapped_requirements": list(self.unmapped_requirements),
            "assumptions": list(self.assumptions),
            "ambiguities": list(self.ambiguities),
            "rejected_bindings": list(self.rejected_bindings),
            "rejection_reasons": list(self.rejection_reasons),
            "requirement_dispositions": [
                item.to_dict() for item in self.requirement_dispositions],
            "requires_clarification": self.requires_clarification,
            "requires_abstention": self.requires_abstention,
            "can_continue_without_user_input": (
                self.can_continue_without_user_input),
            "delegated_requirements": list(self.delegated_requirements),
        }


@dataclass(frozen=True)
class CompiledTask:
    """The typed result of task compilation.

    The original input is preserved verbatim alongside the normalized
    interpretation so later review can detect task drift.
    """

    compiled_task_id: str
    original_input: str
    normalized_interpretation: str
    task_type: str = "unknown"
    output_kind: str = "unknown"
    binding: TemplateBinding | None = None
    variables: dict = field(default_factory=dict)
    file_refs: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    provenance: str = ""
    work_item: WorkItemIR | None = None

    def __post_init__(self) -> None:
        if self.task_type not in TASK_TYPES:
            raise TemplateError(f"task_type must be one of {TASK_TYPES}")
        if self.output_kind not in OUTPUT_KINDS:
            raise TemplateError(f"output_kind must be one of {OUTPUT_KINDS}")

    def to_dict(self) -> dict:
        return {
            "compiled_task_id": self.compiled_task_id,
            "original_input": self.original_input,
            "normalized_interpretation": self.normalized_interpretation,
            "task_type": self.task_type,
            "output_kind": self.output_kind,
            "binding": self.binding.to_dict() if self.binding else None,
            "variables": dict(self.variables),
            "file_refs": list(self.file_refs),
            "source_refs": list(self.source_refs),
            "provenance": self.provenance,
            "work_item": self.work_item.to_dict() if self.work_item else None,
        }


def self_test() -> dict:
    """Prove templates validate and bindings are typed."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    template = TaskTemplate(
        template_id="core.task.tabular_classification",
        version="1.0.0",
        name="Tabular classification",
        task_type="classification",
        output_kind="label",
        variables={"target_column": "string", "file_path": "string",
                   "metric": "string"},
        required_variables=("target_column", "file_path"),
        optional_variables=("metric",),
        file_refs=("data.csv",))
    check("template_validates_required_variables",
          template.content_digest() == template.content_digest()
          and template.required_variables == ("target_column", "file_path"))
    try:
        TaskTemplate(template_id="bad", version="1.0.0", name="bad",
                     task_type="classification", output_kind="label",
                     variables={}, required_variables=("missing",))
        check("missing_required_variable_is_refused", False)
    except TemplateError:
        check("missing_required_variable_is_refused", True)
    try:
        TaskTemplate(template_id="bad", version="1.0.0", name="bad",
                     task_type="bogus", output_kind="label")
        check("unknown_task_type_is_refused", False)
    except TemplateError:
        check("unknown_task_type_is_refused", True)

    binding = TemplateBinding(
        template_id="core.task.tabular_classification",
        template_version="1.0.0",
        binding_mode="partial",
        mapped_variables={"target_column": "churn"},
        unmapped_requirements=("file_path",),
        requirement_dispositions=(RequirementDisposition(
            "file_path", RequirementDispositionState.NEEDS_CLARIFICATION,
            "required_value_missing"),))
    check("partial_binding_records_unmapped_requirements",
          binding.binding_mode == "partial"
          and binding.unmapped_requirements == ("file_path",))
    policy = RequirementPolicy(
        "dataset_source", allow_delegated_choice=True,
        delegation_cues=("any public dataset",),
        clarification_cues=("do not use any public dataset",),
        constraint_refs=("source.public", "source.license_known"))
    delegated = policy.resolve("use any public dataset", provided=False)
    unresolved = policy.resolve("use the supplied dataset", provided=False)
    prohibited = policy.resolve(
        "do not use any public dataset", provided=False)
    autonomous = policy.resolve(
        "choose a suitable source", provided=False,
        interaction_mode=InteractionMode.AUTONOMOUS)
    check("requirement_policy_separates_delegation_from_clarification",
          delegated.state == RequirementDispositionState.DELEGATED_CHOICE
          and delegated.constraint_refs
          and unresolved.state
              == RequirementDispositionState.NEEDS_CLARIFICATION
          and prohibited.state
              == RequirementDispositionState.NEEDS_CLARIFICATION
          and prohibited.reason_code == "delegation_explicitly_withheld"
          and autonomous.state
              == RequirementDispositionState.DELEGATED_CHOICE)
    try:
        TemplateBinding(
            template_id="core.task.tabular_classification",
            template_version="1.0.0", binding_mode="partial",
            unmapped_requirements=("file_path",))
        check("unmapped_requirement_without_disposition_is_refused", False)
    except TemplateError:
        check("unmapped_requirement_without_disposition_is_refused", True)
    try:
        TemplateBinding(template_id="x", template_version="1.0.0",
                        binding_mode="bogus")
        check("unknown_binding_mode_is_refused", False)
    except TemplateError:
        check("unknown_binding_mode_is_refused", True)

    compiled = CompiledTask(
        compiled_task_id="task:1",
        original_input="predict churn from customers.csv",
        normalized_interpretation="predict churn from customers.csv",
        task_type="classification", output_kind="label",
        binding=binding)
    check("compiled_task_preserves_original_input",
          compiled.original_input == "predict churn from customers.csv"
          and compiled.to_dict()["binding"]["binding_mode"] == "partial")
    return {"tests": results}
