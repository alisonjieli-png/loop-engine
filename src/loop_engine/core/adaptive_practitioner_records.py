"""Contracts and model context for the adaptive Practitioner.

The fixed code in this module owns only the universal work cycle, typed model
responses, capability dispatch, budgets, effects, verification, repair, and
Run History. It contains no task classifier, domain workflow, dataset name,
keyword route, or example solution.

Hybrid mode first asks exact deterministic resolvers. When none can satisfy
the task, or when a deterministic capability fails, the complete safe attempt
record is included in the next model decision. Non-deterministic mode begins
with model orientation. Both modes use the same question portfolio and Loop
runtime.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Protocol

from ..code_nodes.solution_model_port import (
    ModelExecution, ModelInvocationRequest, SolutionModelError)
from ..loop.kernel_runtime import current_kernel_owner
from ..templates.model import TaskFeedback
from .context_artifacts import ContextArtifactManager
from .generated_project import (
    execute_generated_project)
from .llm_work_packet import (
    LLMContextBlock, LLMWorkPacket, WorkDirective)
from .adaptive_practitioner_prompting import (
    AdaptivePromptAssemblyRequest, assemble_work_packet, parse_model_json,
    serialize_work_packet)
from .practitioner_context import (
    PractitionerContextPortfolio)
from .adaptive_practitioner_validation import _short_strings, _short_text
from .web_fetch import (
    fetch_web_resource)
from .web_search import (
    search_web)

ADAPTIVE_PRACTITIONER_RECORD_TYPE = "adaptive_practitioner_run/v1"
ADAPTIVE_CAPABILITIES = (
    {
        "capability_ref": "core.web.search",
        "purpose": (
            "Search public web sources and return ranked candidates. Search "
            "results are not evidence until a selected URL is fetched."),
        "arguments": {
            "query": "one bounded search query",
            "purpose": "why candidate sources are needed",
            "maximum_results": "optional integer from 1 through 10",
        },
        "required_permissions": ["network_read"],
        "effects": ["network_read"],
    },
    {
        "capability_ref": "core.web.get",
        "purpose": "Read one public HTTPS resource and retain its exact body.",
        "arguments": {
            "url": "public HTTPS URL",
            "purpose": "why this source is needed",
            "maximum_bytes": "optional positive integer",
        },
        "required_permissions": ["network_read"],
        "effects": ["network_read"],
    },
    {
        "capability_ref": "core.generated_project",
        "purpose": (
            "Create files, execute Python commands in a confined Docker "
            "workspace, run tests, and verify expected artifacts."),
        "arguments": {},
        "required_permissions": ["workspace_write", "sandbox_command"],
        "effects": ["writes_fs", "spawns_process"],
    },
)
NEXT_ACTION_KINDS = (
    "ASK_USER", "REQUEST_AUTHORITY", "RETRIEVE_INTELLIGENCE",
    "RECALL_MEMORY", "RESEARCH_SOURCE", "REUSE_CAPABILITY",
    "PARAMETERIZE_CAPABILITY", "MUTATE_CAPABILITY", "COMPOSE_SOLUTION",
    "PROPOSE_PROCEDURE", "BUILD_CAPABILITY", "GENERATE_CODE", "RUN_CODE",
    "RUN_TOOL", "SPAWN_LOOP", "RUN_PARALLEL", "JOIN_RESULTS", "VERIFY",
    "REPAIR", "INTEGRATE", "STAGE_LEARNING", "RETURN_RESULT", "ABSTAIN",
    "STOP")
AMBIGUITY_STATES = (
    "UNKNOWN", "AMBIGUOUS", "DELEGATED_CHOICE", "DEFAULTABLE_CHOICE",
    "DERIVED_VALUE", "RESEARCH_REQUIRED", "USER_CLARIFICATION_REQUIRED",
    "AUTHORITY_REQUIRED", "BLOCKED")
class AdaptivePractitionerError(ValueError):
    """The adaptive Practitioner could not satisfy a typed runtime contract."""
@dataclass(frozen=True)
class DeterministicAttemptTrace:
    """Complete exact-first attempt preserved for hybrid escalation."""

    original_input_digest: str
    literal_input: str
    status: str
    parsers_attempted: tuple[str, ...] = ()
    templates_considered: tuple[str, ...] = ()
    exact_values: tuple[tuple[str, object], ...] = ()
    capabilities_considered: tuple[str, ...] = ()
    rejected_matches: tuple[str, ...] = ()
    unresolved_requirements: tuple[str, ...] = ()
    ambiguities: tuple[str, ...] = ()
    decisions: tuple[str, ...] = ()
    outputs: tuple[tuple[str, object], ...] = ()
    errors: tuple[str, ...] = ()
    diagnostics: tuple[str, ...] = ()
    recommended_escalation: str = ""

    def __post_init__(self) -> None:
        if (len(self.original_input_digest) != 64 or any(
                character not in "0123456789abcdef"
                for character in self.original_input_digest)):
            raise AdaptivePractitionerError(
                "deterministic attempt input digest must be SHA-256")
        if not self.literal_input.strip() or not self.status.strip():
            raise AdaptivePractitionerError(
                "deterministic attempt needs literal input and status")

    def to_dict(self) -> dict:
        return {
            "record_type": "deterministic_attempt_trace/v1",
            "original_input_digest": self.original_input_digest,
            "literal_input": self.literal_input,
            "status": self.status,
            "parsers_attempted": list(self.parsers_attempted),
            "templates_considered": list(self.templates_considered),
            "exact_values": dict(self.exact_values),
            "capabilities_considered": list(self.capabilities_considered),
            "rejected_matches": list(self.rejected_matches),
            "unresolved_requirements": list(self.unresolved_requirements),
            "ambiguities": list(self.ambiguities),
            "decisions": list(self.decisions),
            "outputs": dict(self.outputs),
            "errors": list(self.errors),
            "diagnostics": list(self.diagnostics),
            "recommended_escalation": self.recommended_escalation,
        }
@dataclass(frozen=True)
class AmbiguityDisposition:
    """One unknown or choice classified without silently becoming false."""

    subject: str
    state: str
    reason: str

    def __post_init__(self) -> None:
        if self.state not in AMBIGUITY_STATES:
            raise AdaptivePractitionerError(
                "ambiguity disposition uses an unknown state")
        if not self.subject.strip() or not self.reason.strip():
            raise AdaptivePractitionerError(
                "ambiguity disposition needs subject and reason")

    def to_dict(self) -> dict:
        return {"subject": self.subject, "state": self.state,
                "reason": self.reason}
@dataclass(frozen=True)
class TaskOrientationResult:
    """Complete typed first semantic interpretation of the preserved task."""

    original_task_ref: str
    task_summary: str
    ultimate_goal: str
    immediate_goal: str
    current_state: str
    desired_state: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    operator_bundle: tuple[str, ...]
    response_contract: str
    decision_consumer: str
    explicit_constraints: tuple[str, ...]
    inferred_constraints: tuple[str, ...]
    non_goals: tuple[str, ...]
    knowns: tuple[str, ...]
    unknowns: tuple[str, ...]
    assumptions: tuple[str, ...]
    ambiguities: tuple[AmbiguityDisposition, ...]
    delegated_choices: tuple[str, ...]
    safe_defaults: tuple[str, ...]
    blocking_questions: tuple[str, ...]
    research_questions: tuple[str, ...]
    subproblems: tuple[str, ...]
    dependencies: tuple[str, ...]
    parallel_candidates: tuple[str, ...]
    candidate_profiles: tuple[str, ...]
    candidate_capabilities: tuple[str, ...]
    verification_obligations: tuple[str, ...]
    confidence_profile: tuple[tuple[str, float], ...]
    proposed_next_action: str

    @classmethod
    def from_mapping(cls, value: object) -> "TaskOrientationResult":
        if not isinstance(value, dict):
            raise AdaptivePractitionerError(
                "TaskOrientationResult must be one object")
        required = {
            "original_task_ref", "task_summary", "ultimate_goal",
            "immediate_goal", "current_state", "desired_state", "inputs",
            "outputs", "operator_bundle", "response_contract",
            "decision_consumer", "explicit_constraints",
            "inferred_constraints", "non_goals", "knowns", "unknowns",
            "assumptions", "ambiguities", "delegated_choices",
            "safe_defaults", "blocking_questions", "research_questions",
            "subproblems", "dependencies", "parallel_candidates",
            "candidate_profiles", "candidate_capabilities",
            "verification_obligations", "confidence_profile",
            "proposed_next_action"}
        if set(value) != required:
            raise AdaptivePractitionerError(
                "TaskOrientationResult fields do not match version 1")
        ambiguities = value.get("ambiguities")
        confidence = value.get("confidence_profile")
        if not isinstance(ambiguities, list) or not isinstance(confidence, dict):
            raise AdaptivePractitionerError(
                "orientation ambiguities and confidence profile are invalid")
        return cls(
            _short_text(value["original_task_ref"], "original_task_ref", 200),
            _short_text(value["task_summary"], "task_summary"),
            _short_text(value["ultimate_goal"], "ultimate_goal"),
            _short_text(value["immediate_goal"], "immediate_goal"),
            _short_text(value["current_state"], "current_state"),
            _short_text(value["desired_state"], "desired_state"),
            _short_strings(value["inputs"], "inputs"),
            _short_strings(value["outputs"], "outputs"),
            _short_strings(value["operator_bundle"], "operator_bundle"),
            _short_text(value["response_contract"], "response_contract"),
            _short_text(value["decision_consumer"], "decision_consumer"),
            _short_strings(value["explicit_constraints"],
                           "explicit_constraints"),
            _short_strings(value["inferred_constraints"],
                           "inferred_constraints"),
            _short_strings(value["non_goals"], "non_goals"),
            _short_strings(value["knowns"], "knowns"),
            _short_strings(value["unknowns"], "unknowns"),
            _short_strings(value["assumptions"], "assumptions"),
            tuple(AmbiguityDisposition(
                _short_text(item.get("subject"), "ambiguity subject", 300),
                str(item.get("state")),
                _short_text(item.get("reason"), "ambiguity reason", 500))
                for item in ambiguities if isinstance(item, dict)),
            _short_strings(value["delegated_choices"], "delegated_choices"),
            _short_strings(value["safe_defaults"], "safe_defaults"),
            _short_strings(value["blocking_questions"], "blocking_questions"),
            _short_strings(value["research_questions"], "research_questions"),
            _short_strings(value["subproblems"], "subproblems"),
            _short_strings(value["dependencies"], "dependencies"),
            _short_strings(value["parallel_candidates"], "parallel_candidates"),
            _short_strings(value["candidate_profiles"], "candidate_profiles"),
            _short_strings(value["candidate_capabilities"],
                           "candidate_capabilities"),
            _short_strings(value["verification_obligations"],
                           "verification_obligations"),
            tuple(sorted((str(key), float(item))
                         for key, item in confidence.items())),
            _short_text(value["proposed_next_action"],
                        "proposed_next_action", 500),
        )

    def to_dict(self) -> dict:
        value = asdict(self)
        value["record_type"] = "task_orientation_result/v1"
        value["ambiguities"] = [item.to_dict() for item in self.ambiguities]
        value["confidence_profile"] = dict(self.confidence_profile)
        for name in (
                "inputs", "outputs", "operator_bundle", "explicit_constraints",
                "inferred_constraints", "non_goals", "knowns", "unknowns",
                "assumptions", "delegated_choices", "safe_defaults",
                "blocking_questions", "research_questions", "subproblems",
                "dependencies", "parallel_candidates", "candidate_profiles",
                "candidate_capabilities", "verification_obligations"):
            value[name] = list(getattr(self, name))
        return value

@dataclass(frozen=True)
class NextActionDecision:
    """One typed action proposal validated before any execution."""

    action_kind: str
    goal: str
    reason: str
    inputs: tuple[tuple[str, object], ...]
    expected_output: str
    required_capabilities: tuple[str, ...]
    permissions: tuple[str, ...]
    budget: tuple[tuple[str, object], ...]
    dependencies: tuple[str, ...]
    scheduling: str
    verification: str
    return_destination: str
    confidence: float
    fallback: tuple[tuple[str, object], ...]

    def __post_init__(self) -> None:
        if self.action_kind not in NEXT_ACTION_KINDS:
            raise AdaptivePractitionerError("NextActionDecision kind is invalid")
        if not 0 <= self.confidence <= 1:
            raise AdaptivePractitionerError(
                "NextActionDecision confidence must be from zero through one")

    @classmethod
    def from_mapping(cls, value: object) -> "NextActionDecision":
        if not isinstance(value, dict):
            raise AdaptivePractitionerError(
                "NextActionDecision must be one object")
        required = {
            "action_kind", "goal", "reason", "inputs", "expected_output",
            "required_capabilities", "permissions", "budget", "dependencies",
            "scheduling", "verification", "return_destination", "confidence",
            "fallback"}
        if set(value) != required:
            raise AdaptivePractitionerError(
                "NextActionDecision fields do not match version 1")
        inputs = value.get("inputs")
        budget = value.get("budget")
        fallback = value.get("fallback")
        if not all(isinstance(item, dict)
                   for item in (inputs, budget, fallback)):
            raise AdaptivePractitionerError(
                "action inputs, budget, and fallback must be objects")
        return cls(
            str(value["action_kind"]),
            _short_text(value["goal"], "action goal"),
            _short_text(value["reason"], "action reason"),
            tuple(sorted(inputs.items())),
            _short_text(value["expected_output"], "expected_output"),
            _short_strings(value["required_capabilities"],
                           "required_capabilities"),
            _short_strings(value["permissions"], "permissions"),
            tuple(sorted(budget.items())),
            _short_strings(value["dependencies"], "dependencies"),
            _short_text(value["scheduling"], "scheduling", 200),
            _short_text(value["verification"], "verification", 500),
            _short_text(value["return_destination"],
                        "return_destination", 200),
            float(value["confidence"]), tuple(sorted(fallback.items())))

    def to_dict(self) -> dict:
        return {
            "record_type": "next_action_decision/v1",
            "action_kind": self.action_kind, "goal": self.goal,
            "reason": self.reason, "inputs": dict(self.inputs),
            "expected_output": self.expected_output,
            "required_capabilities": list(self.required_capabilities),
            "permissions": list(self.permissions), "budget": dict(self.budget),
            "dependencies": list(self.dependencies),
            "scheduling": self.scheduling, "verification": self.verification,
            "return_destination": self.return_destination,
            "confidence": self.confidence, "fallback": dict(self.fallback),
        }

class DeterministicTaskResolver(Protocol):
    """Exact reusable resolver considered before model escalation."""

    resolver_id: str

    def supports(self, task: str) -> bool: ...

    def execute(self, task: str) -> dict: ...

@dataclass(frozen=True)
class AdaptivePractitionerRequest:
    """One task plus mode, authority, and bounded pass settings."""

    task: str
    mode: str = "hybrid"
    runs_dir: str = ""
    max_passes: int = 24
    interaction_mode: str = "autonomous"
    allow_network_reads: bool = True
    allow_workspace_writes: bool = True
    allow_sandbox_commands: bool = True
    source_kind: str = "text"
    source_refs: tuple[str, ...] = ()
    feedback: tuple[TaskFeedback, ...] = ()
    workspace_root: str = ""
    allow_source_materialization_to_model: bool = False
    granularity_profile: str = "governed_semantic"

    def __post_init__(self) -> None:
        if not self.task.strip():
            raise AdaptivePractitionerError("adaptive Practitioner needs a task")
        if self.mode not in ("deterministic", "hybrid", "non_deterministic"):
            raise AdaptivePractitionerError(
                "adaptive Practitioner mode is not registered")
        if not 1 <= self.max_passes <= 32:
            raise AdaptivePractitionerError("max_passes must be from 1 through 32")
        if self.interaction_mode not in ("autonomous", "ask_when_material"):
            raise AdaptivePractitionerError("interaction mode is not registered")
        refs = tuple(self.source_refs)
        if any(not isinstance(item, str) or not item.strip() for item in refs):
            raise AdaptivePractitionerError("source refs must be non-empty text")
        object.__setattr__(self, "source_refs", refs)
        if not isinstance(self.workspace_root, str):
            raise AdaptivePractitionerError("workspace_root must be text")
        if self.granularity_profile not in (
                "governed_semantic", "strict_atomic"):
            raise AdaptivePractitionerError(
                "granularity_profile must be governed_semantic or strict_atomic")
        feedback = tuple(self.feedback)
        if (any(not isinstance(item, TaskFeedback) for item in feedback)
                or len({item.slot_ref for item in feedback}) != len(feedback)):
            raise AdaptivePractitionerError(
                "feedback must use unique typed TaskFeedback slots")
        object.__setattr__(self, "feedback", feedback)
@dataclass(frozen=True)
class AdaptivePractitionerDependencies:
    """Model authority and optional exact deterministic resolvers."""

    model_execution: "ModelExecution | None" = field(
        default=None, repr=False, compare=False)
    deterministic_resolvers: tuple[DeterministicTaskResolver, ...] = ()
    context_portfolio: "PractitionerContextPortfolio | None" = None
    project_executor: Callable = field(
        default=execute_generated_project, repr=False, compare=False)
    web_fetcher: Callable = field(
        default=fetch_web_resource, repr=False, compare=False)
    web_searcher: Callable = field(
        default=search_web, repr=False, compare=False)
    progress: "Callable[[dict], None] | None" = field(
        default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.model_execution is not None and not isinstance(
                self.model_execution, ModelExecution):
            raise AdaptivePractitionerError(
                "model_execution must use the canonical ModelExecution port")
        if any(not callable(getattr(item, "supports", None))
               or not callable(getattr(item, "execute", None))
               for item in self.deterministic_resolvers):
            raise AdaptivePractitionerError("deterministic resolvers must implement supports and execute")
        if self.context_portfolio is not None and not isinstance(
                self.context_portfolio, PractitionerContextPortfolio):
            raise AdaptivePractitionerError(
                "context_portfolio has the wrong contract")
        if (not callable(self.project_executor)
                or not callable(self.web_fetcher)
                or not callable(self.web_searcher)):
            raise AdaptivePractitionerError(
                "adaptive capability executors must be callable")
        if self.progress is not None and not callable(self.progress):
            raise AdaptivePractitionerError("progress must be callable")
@dataclass(frozen=True)
class ModelStepRequest:
    """One question-portfolio step and exact safe problem state."""

    step_id: str
    objective: str
    state: dict
    output_contract: str

@dataclass
class AdaptiveRunServices:
    """Mutable run-local services and evidence never persisted as authority."""

    request: AdaptivePractitionerRequest
    dependencies: AdaptivePractitionerDependencies
    run_id: str
    workspace_base: Path
    artifacts: ContextArtifactManager
    portfolio: PractitionerContextPortfolio
    model_session: object = None
    deterministic_attempt: "DeterministicAttemptTrace | None" = None
    action_details: dict[str, "NextActionDecision"] = field(default_factory=dict)
    action_history: list[dict] = field(default_factory=list)
    candidate_canvases: list[dict] = field(default_factory=list)
    plan_details: dict[str, dict] = field(default_factory=dict)
    orientation_by_version: dict[int, "TaskOrientationResult"] = field(
        default_factory=dict)
    web_search_results: list[dict] = field(default_factory=list)
    web_results: list[dict] = field(default_factory=list)
    project_attempts: list[dict] = field(default_factory=list)
    verification_records: list[dict] = field(default_factory=list)
    context_snapshots: list[dict] = field(default_factory=list)
    selected_intelligence_refs: list[str] = field(default_factory=list)
    selected_memory_refs: list[str] = field(default_factory=list)
    progress_snapshots: list[tuple] = field(default_factory=list)
    unchanged_progress_snapshots: int = 0
    supervision_findings: list[dict] = field(default_factory=list)
    recovery_directives: list[dict] = field(default_factory=list)
    active_recovery_directive: dict | None = None
    recovery_rounds: int = 0
    recovery_evidence_baseline: int = 0

    def available_capabilities(self) -> tuple[dict, ...]:
        """Return only capabilities usable under this run's current authority."""
        available = []
        for item in ADAPTIVE_CAPABILITIES:
            ref = item["capability_ref"]
            usable = (
                self.request.allow_network_reads
                if ref == "core.web.get" else
                self.request.allow_network_reads
                and bool(os.environ.get("OLLAMA_API_KEY", "").strip())
                if ref == "core.web.search" else
                self.request.allow_workspace_writes
                and self.request.allow_sandbox_commands
                if ref == "core.generated_project" else False)
            if usable:
                available.append(item)
        return tuple(available)

    def publish(self, event_type: str, **fields) -> None:
        event = {"event_type": event_type, "run_id": self.run_id, **fields}
        if self.dependencies.progress is not None:
            self.dependencies.progress(event)

    def diagnostic(self, code: str, payload: dict) -> None:
        """Record one bounded typed diagnostic in progress and Run History."""
        owner = current_kernel_owner()
        if owner is None or not code.strip() or not isinstance(payload, dict):
            raise AdaptivePractitionerError("adaptive diagnostic is invalid")
        safe = {str(key): value for key, value in payload.items()
                if key not in ("content", "prompt", "authorization", "secret")}
        owner.ledger.record(
            loop_id=owner.loop_id, event="custom",
            custom_kind="adaptive_diagnostic", diagnostic_code=code,
            diagnostic=safe)
        self.publish("practitioner.diagnostic", diagnostic_code=code, **safe)

    def model(self, request: ModelStepRequest) -> dict:
        if self.model_session is None:
            raise AdaptivePractitionerError(
                f"step {request.step_id} needs a model executor")
        owner = current_kernel_owner()
        if owner is None:
            raise AdaptivePractitionerError(
                "model step has no active Practitioner Loop owner")
        if self.deterministic_attempt is None:
            raise AdaptivePractitionerError(
                "semantic model work needs a deterministic attempt trace")
        step_context = self.portfolio.for_step(request.step_id)
        selected_persona = self.portfolio.persona_for_step(request.step_id)
        supporting = self.portfolio.supporting_personas_for_step(
            request.step_id)
        guidance = self.portfolio.guidance_for_step(request.step_id)
        from ..loop.intelligence_loops import serve_context_intelligence
        selected_context = serve_context_intelligence(
            f"adaptive-context-{request.step_id}", lambda: {
                "primary_persona": selected_persona.to_dict(),
                "supporting_personas": [item.to_dict() for item in supporting],
                "guidance": [item.to_dict() for item in guidance],
                "question_portfolio": step_context.to_dict(),
            }, parent=owner, profile_id="intelligence.context.serve")
        context_value = selected_context["value"]
        for item in guidance:
            if item.record_id not in self.selected_intelligence_refs:
                self.selected_intelligence_refs.append(item.record_id)
        prior_events = []
        for event in owner.ledger.events:
            if event.get("custom_kind") == "llm_work_packet_assembled":
                break
            prior_events.append({
                key: (value[:500] if isinstance(value, str) else value)
                for key, value in event.items() if key != "ts"
                and not any(marker in key.lower() for marker in (
                    "secret", "token", "authorization", "prompt", "content"))})
        capability_descriptors = self.available_capabilities()
        blocks = (
            LLMContextBlock.create(
                "persona", "persona_context", selected_persona.version,
                selected_persona.persona_id,
                "phase-selected Practitioner perspectives", 0,
                {"primary": selected_persona.to_dict(),
                 "supporting": [item.to_dict() for item in supporting]}),
            LLMContextBlock.create(
                f"guidance.{request.step_id}", "context_intelligence",
                self.portfolio.version, self.portfolio.portfolio_id,
                "guidance selected by step affinity", 1,
                [item.to_dict() for item in guidance]),
            LLMContextBlock.create(
                f"questions.{request.step_id}", "question_portfolio",
                self.portfolio.version, self.portfolio.portfolio_id,
                "questions for the active procedure step", 2,
                step_context.to_dict()),
            LLMContextBlock.create(
                "deterministic_attempt", "attempt_trace", "1.0.0",
                "adaptive_practitioner", "hybrid escalation evidence", 3,
                self.deterministic_attempt.to_dict()),
            LLMContextBlock.create(
                "current_state", "task_context", "1.0.0",
                "active Practitioner run", "latest accepted state", 4,
                {"task_state": request.state,
                 "source_kind": self.request.source_kind,
                 "source_refs": list(self.request.source_refs),
                 "task_feedback": [
                     item.to_dict() for item in self.request.feedback],
                 "interaction_mode": self.request.interaction_mode,
                 "run_mode": self.request.mode}),
            LLMContextBlock.create(
                "capability_descriptors", "capability_snapshot", "1.0.0",
                "core capability registry", "available execution paths", 5,
                list(capability_descriptors)),
            LLMContextBlock.create(
                "deterministic_event_history", "attempt_event_history", "1.0.0",
                "canonical Loop event log", "complete exact-first history", 6,
                prior_events),
        )
        requested_state_version = int(request.state.get("state_version", -1))
        eligible_orientation_versions = [
            version for version in self.orientation_by_version
            if version <= requested_state_version]
        orientation = (
            self.orientation_by_version[max(eligible_orientation_versions)]
            if eligible_orientation_versions else None)
        permissions = tuple(name for name, allowed in (
                ("network_read", self.request.allow_network_reads),
                ("workspace_write", self.request.allow_workspace_writes),
                ("sandbox_command", self.request.allow_sandbox_commands))
                if allowed)
        remaining_calls = max(
            0, self.model_session.authority.max_model_calls
            - self.model_session.calls_used)
        owner_init = next((item for item in owner.ledger.events
                           if item.get("event") == "init"
                           and item.get("loop_id") == owner.loop_id), {})
        root_init = next((item for item in owner.ledger.events
                          if item.get("event") == "init"
                          and item.get("depth") == 0), owner_init)
        directive = WorkDirective(
            request.step_id.upper(), request.objective, True,
            NEXT_ACTION_KINDS if request.step_id == "decide_next" else (),
            ("unrequested final solution", "unsupported permission",
             "completion claim without verified output",
             "additional prose outside the requested schema"),
            "the returned payload validates against the required schema",
            "the payload or its claimed authority fails validation",
            "inline:sha256:" + hashlib.sha256(
                request.output_contract.encode("utf-8")).hexdigest(),
            "return_to_owning_practitioner")
        packet = LLMWorkPacket(
            packet_id=(f"packet.{self.run_id.replace('-', '_')}."
                       f"{request.step_id}.attempt_"
                       f"{self.model_session.calls_used + 1}"),
            packet_version="1.0.0",
            purpose="resolve_one_semantic_step", phase=request.step_id,
            persona_context={
                "primary_persona": context_value["primary_persona"],
                "supporting_personas": context_value["supporting_personas"],
                "authority_limits": [
                    "may propose typed semantic output",
                    "may not execute tools or grant permission",
                    "may not decide terminal success"],
            },
            task_context={
                "original_input": self.request.task,
                "source_type": self.request.source_kind,
                "source_refs": list(self.request.source_refs),
                "normalized_interpretation": (
                    orientation.task_summary if orientation else None),
                "ultimate_goal": (
                    orientation.ultimate_goal if orientation
                    else self.request.task),
                "immediate_goal": (
                    orientation.immediate_goal if orientation
                    else request.objective),
                "current_state": request.state,
                "desired_state": (
                    orientation.desired_state if orientation else "unknown"),
                "expected_inputs": (
                    list(orientation.inputs) if orientation else []),
                "expected_outputs": (
                    list(orientation.outputs) if orientation else []),
                "acceptance_criteria": (
                    list(orientation.verification_obligations)
                    if orientation else []),
                "explicit_constraints": (
                    list(orientation.explicit_constraints)
                    if orientation else []),
                "inferred_constraints": (
                    list(orientation.inferred_constraints)
                    if orientation else []),
                "non_goals": (
                    list(orientation.non_goals) if orientation else []),
                "knowns": list(orientation.knowns) if orientation else [],
                "unknowns": list(orientation.unknowns) if orientation else [],
                "delegated_choices": (
                    list(orientation.delegated_choices)
                    if orientation else []),
                "feedback": [item.to_dict() for item in self.request.feedback],
                "provenance": "preserved user task plus accepted run state",
            },
            loop_context={
                "run_id": self.run_id, "loop_id": owner.loop_id,
                "root_loop_id": root_init.get("loop_id", owner.loop_id),
                "parent_loop_id": owner_init.get("spawning_loop_id", ""),
                "relationship": owner_init.get("relationship_kind", "starting"),
                "role": owner_init.get("role", "practitioner"),
                "profile": owner_init.get("profile_id", ""),
                "mode": self.request.mode,
                "current_step": request.step_id,
                "current_checkpoint": request.objective,
                "active_failures": list(request.state.get("failures") or ()),
                "artifacts": request.state.get("artifact_refs", {}),
                "permissions": list(permissions),
                "remaining_budget": {
                    "model_calls": remaining_calls,
                    "practitioner_passes": self.request.max_passes},
                "return_destination": "owning Practitioner",
                "terminal_contract": "verified task acceptance or typed blocker",
            },
            context_intelligence=tuple(context_value["guidance"]),
            question_portfolio=context_value["question_portfolio"],
            capability_context={
                "available_capabilities": list(capability_descriptors),
                "selected_intelligence_refs": list(
                    self.selected_intelligence_refs),
                "selected_memory_refs": list(self.selected_memory_refs),
            },
            attempt_history={
                "deterministic_attempt": self.deterministic_attempt.to_dict(),
                "current_failures": list(request.state.get("failures") or ()),
                "events": prior_events,
            },
            work_directive=directive,
            output_contract={
                "schema_ref": directive.return_schema_ref,
                "schema": request.output_contract,
                "format": "json", "additional_text_allowed": False},
            policy_context={
                "interaction_mode": self.request.interaction_mode,
                "permissions": list(permissions),
                "model_cannot_grant_authority": True},
            token_budget={"model_calls_remaining": remaining_calls},
            source_refs=tuple(self.request.source_refs), context_blocks=blocks)
        packet_artifact = self.artifacts.store.put(
            serialize_work_packet(packet, owner),
            media_type="application/json", encoding="utf-8",
            artifact_kind="llm_work_packet")
        value = None
        for format_attempt in (1, 2):
            profile = self.portfolio.assembly_profile(
                bool(request.state.get("failures")) or format_attempt == 2)
            assembled = assemble_work_packet(
                AdaptivePromptAssemblyRequest(
                    packet, profile.profile_id, profile.layout_policy,
                    format_repair=format_attempt == 2,
                    granularity_profile=self.request.granularity_profile), owner)
            snapshot = assembled.snapshot.to_dict()
            self.context_snapshots.append({
                "step": request.step_id, "objective": request.objective,
                "packet_id": packet.packet_id,
                "packet_digest": packet.content_digest,
                "packet_artifact_ref": packet_artifact.to_dict(),
                "intelligence_loop_id": selected_context["loop_id"],
                "assembly_loop_id": assembled.assembly_loop_id,
                "primitive_loop_ids": list(assembled.primitive_loop_ids),
                "prompt_assembly": snapshot,
                "blocks": [{key: value for key, value in item.to_dict().items()
                            if key != "content"} for item in blocks],
                "total_estimated_tokens": snapshot["estimated_tokens"],
            })
            owner.ledger.record(
                loop_id=owner.loop_id, event="custom",
                custom_kind="llm_work_packet_assembled",
                procedure_step=request.step_id,
                objective=request.objective[:160],
                packet_id=packet.packet_id,
                packet_digest=packet.content_digest,
                packet_artifact_ref=packet_artifact.object_key,
                context_block_ids=tuple(item.block_id for item in blocks),
                context_block_digests=tuple(item.digest for item in blocks),
                prompt_assembly_id=snapshot["assembly_id"],
                prompt_digest=snapshot["prompt_digest"],
                deterministic_attempt_status=self.deterministic_attempt.status,
                output_schema_digest=hashlib.sha256(
                    request.output_contract.encode("utf-8")).hexdigest())
            for transport_attempt in (1, 2):
                self.publish(
                    "model.step.started", step=request.step_id,
                    objective=request.objective[:160],
                    format_attempt=format_attempt,
                    transport_attempt=transport_attempt)
                try:
                    text = self.model_session.invoke(
                        ModelInvocationRequest(
                            assembled.prompt,
                            temperature=assembled.temperature), owner)
                    break
                except SolutionModelError:
                    self.publish(
                        "model.step.transport_failed", step=request.step_id,
                        format_attempt=format_attempt,
                        transport_attempt=transport_attempt)
                    if transport_attempt == 2:
                        raise
            value = parse_model_json(text, owner)
            if value is not None:
                break
            self.publish(
                "model.step.output_invalid", step=request.step_id,
                format_attempt=format_attempt)
        if value is None:
            raise AdaptivePractitionerError(
                f"model step {request.step_id} returned invalid JSON")
        self.publish("model.step.completed", step=request.step_id)
        return value
