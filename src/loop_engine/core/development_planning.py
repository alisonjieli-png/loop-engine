"""Typed software-development planning over existing Loop graph contracts.

Planning records are passive. Deterministic assurance and wave compilation are
capabilities owned by Practitioner Loops. They do not create a plan runtime,
task graph executor, or competing history.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from enum import Enum

from ..code_nodes.solution_graph import (
    LoopGraphDefinition, LoopGraphEdge, LoopGraphEndpoint, LoopGraphGroup,
    LoopGraphInputPort, LoopGraphOutputPort, LoopGraphStage,
    SolutionLoopDefinitionRequest, make_solution_loop_definition,
    vertex_from_definition,
)
from ..loop.loop_definition import ConfigurationFacts
from ..scheduling import ConcurrencyContract, decide_overlap


_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,191}$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")


class DevelopmentPlanError(ValueError):
    """A plan, task, handoff, assurance, or policy failed validation."""


class PlanningAuthority(str, Enum):
    INTERACTIVE_REQUIRED = "interactive_required"
    AUTONOMOUS_WITH_SAFE_DEFAULTS = "autonomous_with_safe_defaults"
    AUTONOMOUS_WITH_POST_PLAN_APPROVAL = "autonomous_with_post_plan_approval"
    AUTONOMOUS_LOW_RISK = "autonomous_low_risk"
    PARENT_LOOP_AUTHORIZED = "parent_loop_authorized"


class ClarificationDisposition(str, Enum):
    MUST_ANSWER = "must_answer"
    WILL_DEFAULT_IF_SILENT = "will_default_if_silent"
    DELEGATED_CHOICE = "delegated_choice"
    DERIVED_VALUE = "derived_value"
    RESEARCH_REQUIRED = "research_required"
    AUTHORITY_REQUIRED = "authority_required"
    NONMATERIAL = "nonmaterial"


class ResolutionDisposition(str, Enum):
    RESOLVED_NONEMPTY = "resolved_nonempty"
    RESOLVED_EMPTY = "resolved_empty"
    OPTIONAL_MISSING = "optional_missing"
    REQUIRED_MISSING = "required_missing"
    MALFORMED = "malformed"
    INCOMPATIBLE = "incompatible"
    UNAUTHORIZED = "unauthorized"
    FAILED = "failed"
    DRIFTED = "drifted"
    STALE = "stale"
    BLOCKED = "blocked"


class AssuranceVerdict(str, Enum):
    ACCEPT = "accept"
    REPAIR_PLAN = "repair_plan"
    BLOCKED = "blocked"


class TerminalPlanCode(str, Enum):
    COMPLETED_VERIFIED = "completed_verified"
    COMPLETED_PARTIAL = "completed_partial"
    TASKS_BLOCKED = "tasks_blocked"
    AUTHORITY_REQUIRED = "authority_required"
    CAPABILITY_GAP = "capability_gap"
    NO_PROGRESS = "no_progress"
    REPAIR_UNAVAILABLE = "repair_unavailable"
    BUDGET_EXHAUSTED = "budget_exhausted"
    DEADLINE_EXHAUSTED = "deadline_exhausted"
    CANCELLED = "cancelled"
    ABSTAINED = "abstained"


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, default=str)


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _id(label: str, value: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise DevelopmentPlanError(f"{label} is invalid")
    return value


def _names(label: str, values) -> tuple[str, ...]:
    result = tuple(values or ())
    if (any(not isinstance(value, str) or not value.strip() for value in result)
            or len(result) != len(set(result))):
        raise DevelopmentPlanError(
            f"{label} must contain unique non-empty strings")
    return result


@dataclass(frozen=True)
class ClarificationItem:
    subject: str
    disposition: ClarificationDisposition | str
    reason: str
    selected_value: str = ""
    default_value: str = ""

    def __post_init__(self) -> None:
        if not self.subject.strip() or not self.reason.strip():
            raise DevelopmentPlanError("clarification needs subject and reason")
        try:
            object.__setattr__(self, "disposition",
                               ClarificationDisposition(self.disposition))
        except ValueError as exc:
            raise DevelopmentPlanError("unknown clarification disposition") from exc
        if (self.disposition is ClarificationDisposition.WILL_DEFAULT_IF_SILENT
                and not self.default_value):
            raise DevelopmentPlanError("defaultable clarification needs a default")
        if self.disposition is ClarificationDisposition.DELEGATED_CHOICE \
                and not self.selected_value:
            raise DevelopmentPlanError("delegated choice needs a selected value")


@dataclass(frozen=True)
class RequirementVerificationContract:
    criterion_id: str
    criterion: str
    verification_operator: str
    expected_evidence: tuple[str, ...]
    failure_state: str
    independent_verification: bool

    def __post_init__(self) -> None:
        _id("criterion_id", self.criterion_id)
        if any(not value.strip() for value in (
                self.criterion, self.verification_operator, self.failure_state)):
            raise DevelopmentPlanError("verification contract is incomplete")
        evidence = _names("expected_evidence", self.expected_evidence)
        if not evidence:
            raise DevelopmentPlanError("criterion needs expected evidence")
        object.__setattr__(self, "expected_evidence", evidence)
        if not isinstance(self.independent_verification, bool):
            raise DevelopmentPlanError("independent_verification must be boolean")


@dataclass(frozen=True)
class TaskSliceDefinition:
    task_id: str
    objective: str
    input_refs: tuple[str, ...]
    output_contract_refs: tuple[str, ...]
    dependency_ids: tuple[str, ...]
    verifications: tuple[RequirementVerificationContract, ...]
    concurrency: ConcurrencyContract
    activation_path: tuple[str, ...]
    required_capabilities: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _id("task_id", self.task_id)
        if not self.objective.strip():
            raise DevelopmentPlanError("task slice needs an objective")
        for name in ("input_refs", "output_contract_refs", "dependency_ids",
                     "activation_path", "required_capabilities"):
            object.__setattr__(self, name, _names(name, getattr(self, name)))
        if not self.output_contract_refs or not self.activation_path:
            raise DevelopmentPlanError(
                "task slice needs output contracts and an activation path")
        checks = tuple(self.verifications)
        if not checks or any(not isinstance(item, RequirementVerificationContract)
                             for item in checks):
            raise DevelopmentPlanError("task slice needs verification contracts")
        if not isinstance(self.concurrency, ConcurrencyContract):
            raise DevelopmentPlanError("task slice needs ConcurrencyContract")
        object.__setattr__(self, "verifications", checks)


@dataclass(frozen=True)
class PlanDefinition:
    plan_id: str
    original_task_ref: str
    original_task_digest: str
    goal: str
    scope: tuple[str, ...]
    non_goals: tuple[str, ...]
    authority: PlanningAuthority | str
    clarifications: tuple[ClarificationItem, ...]
    task_slices: tuple[TaskSliceDefinition, ...]

    def __post_init__(self) -> None:
        _id("plan_id", self.plan_id)
        _id("original_task_ref", self.original_task_ref)
        if not _DIGEST.fullmatch(self.original_task_digest):
            raise DevelopmentPlanError("original task digest is invalid")
        if not self.goal.strip():
            raise DevelopmentPlanError("plan needs a goal")
        object.__setattr__(self, "scope", _names("scope", self.scope))
        object.__setattr__(self, "non_goals", _names("non_goals", self.non_goals))
        try:
            object.__setattr__(self, "authority", PlanningAuthority(self.authority))
        except ValueError as exc:
            raise DevelopmentPlanError("unknown planning authority") from exc
        clarifications = tuple(self.clarifications)
        tasks = tuple(self.task_slices)
        if any(not isinstance(item, ClarificationItem) for item in clarifications):
            raise DevelopmentPlanError("plan clarification is untyped")
        if (not tasks or any(not isinstance(item, TaskSliceDefinition)
                             for item in tasks)
                or len({item.task_id for item in tasks}) != len(tasks)):
            raise DevelopmentPlanError("plan needs unique typed task slices")
        object.__setattr__(self, "clarifications", clarifications)
        object.__setattr__(self, "task_slices", tasks)

    @property
    def content_digest(self) -> str:
        return _digest(asdict(self))


@dataclass(frozen=True)
class ConcurrencyDecisionRecord:
    left_task_id: str
    right_task_id: str
    verdict: str
    reasons: tuple[str, ...]
    selected_wave_relation: str


@dataclass(frozen=True)
class TaskExecutionPlan:
    plan_id: str
    plan_digest: str
    waves: tuple[tuple[str, ...], ...]
    decisions: tuple[ConcurrencyDecisionRecord, ...]
    blocked: tuple[str, ...]


@dataclass(frozen=True)
class TaskLoopBinding:
    """Task-conditioned execution binding used by the graph compiler."""

    task_id: str
    operation_ref: str
    selected_mode: str = "deterministic"
    profile_id: str = "solution.atomic_component"

    def __post_init__(self) -> None:
        _id("task_id", self.task_id)
        if not self.operation_ref.strip() or not self.profile_id.strip():
            raise DevelopmentPlanError(
                "task Loop binding needs an operation and profile")
        if self.selected_mode not in {
                "deterministic", "hybrid", "non_deterministic"}:
            raise DevelopmentPlanError("task Loop binding mode is invalid")


@dataclass(frozen=True)
class PlanAssuranceResult:
    plan_id: str
    reviewer_loop_id: str
    critical_findings: tuple[str, ...]
    important_findings: tuple[str, ...]
    minor_findings: tuple[str, ...]
    proposed_patches: tuple[str, ...]
    verdict: AssuranceVerdict | str

    def __post_init__(self) -> None:
        _id("plan_id", self.plan_id)
        _id("reviewer_loop_id", self.reviewer_loop_id)
        try:
            object.__setattr__(self, "verdict", AssuranceVerdict(self.verdict))
        except ValueError as exc:
            raise DevelopmentPlanError("unknown assurance verdict") from exc


@dataclass(frozen=True)
class WorkerAssignmentEnvelope:
    parent_loop_ref: str
    plan_ref: str
    task_slice_ref: str
    original_task_ref: str
    resolved_workspace_ref: str
    settings_snapshot_ref: str
    capability_snapshot_ref: str
    extension_snapshot_ref: str
    input_refs: tuple[str, ...]
    dependency_output_refs: tuple[str, ...]
    context_refs: tuple[str, ...]
    permissions: tuple[str, ...]
    write_scope: tuple[str, ...]
    effect_scope: tuple[str, ...]
    output_contract_refs: tuple[str, ...]
    verification_refs: tuple[str, ...]
    return_destination: str

    @property
    def content_digest(self) -> str:
        return _digest(asdict(self))


@dataclass(frozen=True)
class RetryPolicy:
    policy_id: str
    maximum_attempts: int
    allowed_failure_classes: tuple[str, ...]
    executable_delta_required: bool = True

    def __post_init__(self) -> None:
        _id("retry policy", self.policy_id)
        if (not isinstance(self.maximum_attempts, int)
                or isinstance(self.maximum_attempts, bool)
                or self.maximum_attempts < 1):
            raise DevelopmentPlanError("maximum attempts must be positive")
        if not self.executable_delta_required:
            raise DevelopmentPlanError("retry requires an executable delta")


def assure_plan(plan: PlanDefinition, reviewer_loop_id: str) -> PlanAssuranceResult:
    """Deterministically find structural gaps before semantic review."""
    tasks = {item.task_id: item for item in plan.task_slices}
    critical = []
    important = []
    for task in plan.task_slices:
        missing = sorted(set(task.dependency_ids) - set(tasks))
        if missing:
            critical.append(f"{task.task_id}: missing dependencies {missing}")
        if not task.activation_path:
            critical.append(f"{task.task_id}: no activation path")
        if not task.verifications:
            critical.append(f"{task.task_id}: no verification")
        if not task.input_refs:
            important.append(f"{task.task_id}: no explicit input refs")
    try:
        compile_execution_waves(plan)
    except DevelopmentPlanError as exc:
        critical.append(str(exc))
    verdict = AssuranceVerdict.REPAIR_PLAN if critical else AssuranceVerdict.ACCEPT
    return PlanAssuranceResult(plan.plan_id, reviewer_loop_id,
                               tuple(critical), tuple(important), (), (), verdict)


def compile_execution_waves(plan: PlanDefinition) -> TaskExecutionPlan:
    """Compile deterministic dependency and concurrency-safe task waves."""
    tasks = {item.task_id: item for item in plan.task_slices}
    for task in tasks.values():
        missing = set(task.dependency_ids) - set(tasks)
        if missing:
            raise DevelopmentPlanError(
                f"{task.task_id}: missing dependencies {sorted(missing)}")
    remaining = set(tasks)
    completed: set[str] = set()
    waves = []
    decisions = []
    while remaining:
        ready = sorted(task_id for task_id in remaining
                       if set(tasks[task_id].dependency_ids) <= completed)
        if not ready:
            raise DevelopmentPlanError("task dependency cycle or blocked graph")
        wave = []
        for task_id in ready:
            safe = True
            for selected in wave:
                decision = decide_overlap(tasks[task_id].concurrency,
                                          tasks[selected].concurrency)
                decisions.append(ConcurrencyDecisionRecord(
                    selected, task_id, decision.verdict, decision.reasons,
                    "same_wave" if decision.verdict == "safe" else "serialized"))
                if decision.verdict != "safe":
                    safe = False
                    break
            if safe:
                wave.append(task_id)
        if not wave:
            wave = [ready[0]]
        waves.append(tuple(wave))
        completed.update(wave)
        remaining.difference_update(wave)
    return TaskExecutionPlan(plan.plan_id, plan.content_digest, tuple(waves),
                             tuple(decisions), ())


def compile_plan_to_loop_graph(
        plan: PlanDefinition,
        bindings: tuple[TaskLoopBinding, ...]) -> LoopGraphDefinition:
    """Compile one accepted task plan into the canonical Loop graph.

    Planning remains Practitioner work. This compiler binds each executable
    task slice to one exact Solution Loop definition. Dependency edges, not
    list position or prose, determine the executable DAG.
    """
    if not isinstance(plan, PlanDefinition):
        raise DevelopmentPlanError("graph compilation needs PlanDefinition")
    execution = compile_execution_waves(plan)
    by_task = {item.task_id: item for item in plan.task_slices}
    by_binding = {item.task_id: item for item in bindings}
    if (len(by_binding) != len(bindings)
            or set(by_binding) != set(by_task)):
        raise DevelopmentPlanError(
            "every task must have exactly one task Loop binding")

    graph_id = f"plan:{plan.plan_id}"
    request_role = "development.plan.request/v1"
    result_roles = {
        task_id: f"development.task.{task_id}.result/v1"
        for task_id in by_task
    }
    wave_by_task = {
        task_id: index for index, wave in enumerate(execution.waves, start=1)
        for task_id in wave
    }

    controller_definition = make_solution_loop_definition(
        SolutionLoopDefinitionRequest(
            graph_id=graph_id, vertex_id="plan.controller",
            profile_id="solution.pipeline", input_roles=(request_role,),
            output_roles=(request_role,), selected_mode="deterministic",
            purpose="controller", delegated_modes=("deterministic",),
            parameters=ConfigurationFacts.from_mapping({
                "plan_id": plan.plan_id,
                "plan_digest": plan.content_digest,
                "execution_waves": [list(wave) for wave in execution.waves],
            })))
    vertices = [vertex_from_definition(
        "plan.controller", controller_definition,
        selected_mode="deterministic", purpose="controller",
        parameters={
            "plan_id": plan.plan_id,
            "plan_digest": plan.content_digest,
            "execution_waves": [list(wave) for wave in execution.waves],
        })]
    edges = []
    stages = []
    for task_id, task in by_task.items():
        binding = by_binding[task_id]
        input_roles = tuple(
            result_roles[dependency] for dependency in task.dependency_ids
        ) or (request_role,)
        parameters = {
            "plan_id": plan.plan_id,
            "plan_digest": plan.content_digest,
            "task_id": task.task_id,
            "objective": task.objective,
            "wave": wave_by_task[task_id],
            "activation_path": list(task.activation_path),
            "output_contract_refs": list(task.output_contract_refs),
            "required_capabilities": list(task.required_capabilities),
            "verification_criteria": [
                item.criterion_id for item in task.verifications],
        }
        definition = make_solution_loop_definition(
            SolutionLoopDefinitionRequest(
                graph_id=graph_id, vertex_id=task_id,
                profile_id=binding.profile_id, input_roles=input_roles,
                output_roles=(result_roles[task_id],),
                selected_mode=binding.selected_mode,
                purpose="component", operation_ref=binding.operation_ref,
                parameters=ConfigurationFacts.from_mapping(parameters),
                delegated_modes=(binding.selected_mode,)))
        vertices.append(vertex_from_definition(
            task_id, definition, selected_mode=binding.selected_mode,
            purpose="component", operation_ref=binding.operation_ref,
            parameters=parameters))
        stages.append(LoopGraphStage(f"stage:{task_id}", (task_id,)))
        if task.dependency_ids:
            for dependency in task.dependency_ids:
                role = result_roles[dependency]
                edges.append(LoopGraphEdge(
                    f"edge:{dependency}:{task_id}",
                    LoopGraphEndpoint(dependency, role),
                    LoopGraphEndpoint(task_id, role),
                    "connected_from", wave_by_task[task_id]))
        else:
            edges.append(LoopGraphEdge(
                f"edge:controller:{task_id}",
                LoopGraphEndpoint("plan.controller", request_role),
                LoopGraphEndpoint(task_id, request_role),
                "connected_from", wave_by_task[task_id]))

    depended_on = {
        dependency for task in plan.task_slices
        for dependency in task.dependency_ids
    }
    sinks = tuple(task_id for task_id in by_task if task_id not in depended_on)
    modes = tuple(dict.fromkeys((
        "deterministic", *(item.selected_mode for item in bindings))))
    graph = LoopGraphDefinition(
        graph_id=graph_id, version="1.0.0",
        permitted_vertex_modes=modes,
        input_ports=(LoopGraphInputPort(
            "plan-input", request_role,
            (LoopGraphEndpoint("plan.controller", request_role),)),),
        output_ports=tuple(LoopGraphOutputPort(
            f"output:{task_id}", result_roles[task_id],
            LoopGraphEndpoint(task_id, result_roles[task_id]))
            for task_id in sinks),
        vertices=tuple(vertices), edges=tuple(edges),
        groups=(LoopGraphGroup(
            "plan.execution", "plan.controller", tuple(stages)),),
        starting_group_id="plan.execution")
    graph.assert_executable()
    return graph


__all__ = (
    "AssuranceVerdict",
    "ClarificationDisposition",
    "ClarificationItem",
    "ConcurrencyDecisionRecord",
    "DevelopmentPlanError",
    "PlanAssuranceResult",
    "PlanDefinition",
    "PlanningAuthority",
    "RequirementVerificationContract",
    "ResolutionDisposition",
    "RetryPolicy",
    "TaskExecutionPlan",
    "TaskLoopBinding",
    "TaskSliceDefinition",
    "TerminalPlanCode",
    "WorkerAssignmentEnvelope",
    "assure_plan",
    "compile_execution_waves",
    "compile_plan_to_loop_graph",
)
