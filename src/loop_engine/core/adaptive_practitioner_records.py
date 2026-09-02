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
import json
import os
import time
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Callable, Protocol, TYPE_CHECKING

from ..code_nodes.solution_model_port import (
    ModelExecution, ModelInvocationRequest, SolutionModelError)
from ..loop.kernel_runtime import current_kernel_owner
from ..templates.model import TaskFeedback
from .context_artifacts import ContextArtifactManager
from .context_budget import ContextBudgetPolicy, bound_state_view
from .context_pack_manifest import build_context_pack_manifest
from .generated_project import (
    execute_generated_project)
from .option_selection import (SELECTION_KEYS, SELECTION_REPORT_CONTRACT,
                              SelectionTally, admitted_selection)
from .llm_work_packet import (
    LLMContextBlock, LLMWorkPacket, WorkDirective)
from .adaptive_practitioner_prompting import (
    AdaptivePromptAssemblyRequest, assemble_work_packet,
    serialize_work_packet)
from .model_response_admission import (
    ModelResponseAdmissionRequest, ModelResponseRepairStalled,
    admit_model_response_as_loop)
from .practitioner_context import (
    PractitionerContextPortfolio)
from .reusable_capability_harvest import ReuseObservationPort
from .adaptive_practitioner_validation import _short_strings, _short_text
from .web_fetch import (
    fetch_web_resource)
from .web_search import (
    search_web)

if TYPE_CHECKING:
    from .action_fence import ActionFenceLedger

ADAPTIVE_PRACTITIONER_RECORD_TYPE = "adaptive_practitioner_run/v1"
ADAPTIVE_CAPABILITIES = (
    {
        "capability_ref": "core.source.inspect",
        "purpose": (
            "Inspect supplied local source manifests and selected text bodies "
            "before deciding how to solve or repair the task."),
        "arguments": {
            "paths": "optional exact relative source paths",
            "query": "optional lexical query for source selection",
            "include_contents": "false for manifest only, true for bodies",
        },
        "required_permissions": ["source_read"],
        "effects": ["reads_fs"],
    },
    {
        "capability_ref": "core.workspace.read",
        "purpose": (
            "Read back a file this run produced, with interpreter line "
            "numbers, so generated code can be repaired from what it "
            "actually says rather than from memory of what was intended. "
            "Reads only inside this run's workspace; supplied input files "
            "stay with core.source.inspect."),
        "arguments": {
            "path": ("optional workspace-relative path; omit it to list "
                     "every file this run has produced"),
            "first_line": "optional 1-based line to start from",
        },
        "required_permissions": ["workspace_write"],
        "effects": ["reads_fs"],
    },
    {
        "capability_ref": "core.web.search",
        "purpose": (
            "Search public web sources and return ranked candidates. Search "
            "results are not evidence until a selected URL is fetched."),
        "arguments": {
            "query": "one search query",
            "purpose": "why candidate sources are needed",
            "maximum_results": "optional positive integer owner limit",
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
    {
        "capability_ref": "core.source.profile",
        "purpose": (
            "Profile selected text sources deterministically: line counts, "
            "column structure for CSV and JSON shapes, key fields, and "
            "sample rows, without sending any content to a model."),
        "arguments": {
            "paths": "optional exact relative source paths; omit to profile "
                     "every supplied source",
            "maximum_sample_bytes": "optional positive integer owner limit",
        },
        "required_permissions": ["source_read"],
        "effects": ["reads_fs"],
    },
    {
        "capability_ref": "core.environment.describe",
        "purpose": (
            "Describe the current runtime environment deterministically: "
            "available execution capabilities, sandbox availability, "
            "configured providers without secrets, and task authority "
            "grants. Effect-free discovery for orientation."),
        "arguments": {},
        "required_permissions": [],
        "effects": [],
    },
    {
        "capability_ref": "core.intelligence.search",
        "purpose": (
            "Search the four persistent intelligence layers and prior Run "
            "History summaries through the existing retrieval projections. "
            "Results are references and candidates, never authority."),
        "arguments": {
            "query": "one retrieval query",
            "kinds": "optional list of record kinds to filter",
        },
        "required_permissions": [],
        "effects": [],
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
# Transport failure classes that may be retried at the governed model-step
# boundary. Permanent classes (authentication, payment, invalid request,
# rate limit policy, model not found) are never retried on the same route.
# gateway_timeout means a proxy cut a long generation; a retry may hit the
# same wall, so the step boundary also lowers its requested ceiling once
# before the final attempt.
#: Codes worth another physical attempt. Each names a property of THIS
#: attempt rather than of the request: a connection that dropped, a limit
#: that clears with time, a sampled response that carried no answer outside
#: its private reasoning. A deterministic refusal — a bad request, an unknown
#: model, an identity mismatch — is deliberately absent, because an identical
#: second call earns an identical refusal and spends a call to learn nothing.
#:
#: ``output_validation_failed`` belongs here for a reason worth stating: the
#: provider finished normally, declared `stop`, and stayed under its output
#: ceiling, yet returned only reasoning. Nothing about the request was wrong
#: and nothing in the run's state had changed, so the next sample is likely
#: to answer — but the code was fatal, and one unlucky sample ended entire
#: runs at their first step. Format repair does not cover this: repair feeds
#: a malformed answer back, and here no answer arrived to repair.
_RETRYABLE_TRANSPORT_ERRORS = frozenset({
    "network_unreachable", "provider_unavailable", "timeout",
    "gateway_timeout", "rate_limited", "output_validation_failed"})

#: Codes whose wait is governed by a limit clearing rather than a connection
#: settling. The transport backoff of one and two seconds returns straight
#: into the same refusal for these. Fifteen seconds a step is a starting
#: point chosen to be longer than the transport wait, not a measured
#: constant, and the retry events record what it actually cost.
_SLOW_BACKOFF_ERRORS = frozenset({"rate_limited"})
_SLOW_BACKOFF_SECONDS = 15
_MAXIMUM_TRANSPORT_ATTEMPTS = 3
#: Format-repair calls per model step before the step fails honestly. Each
#: attempt is a real model call whose output already failed admission;
#: unbounded repair against novel invalid output is churn, not progress.
_MAXIMUM_FORMAT_ATTEMPTS = 4
class AdaptivePractitionerError(ValueError):
    """The adaptive Practitioner could not satisfy a typed runtime contract."""
@dataclass(frozen=True)
class DeterministicAttemptTrace:
    """Complete explicit exact-reuse attempt preserved for later reasoning."""

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
                f"ambiguity state {self.state!r} is not admitted; the "
                f"admitted states are {list(AMBIGUITY_STATES)}")
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
        # Derived from the record's own fields: a restated copy of
        # this list drifts the moment a field is added.
        required = {item.name for item in fields(cls)}
        if set(value) != required:
            raise AdaptivePractitionerError(
                _field_mismatch(value, required, "TaskOrientationResult"))
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
                _short_text(item.get("subject"), "ambiguity subject"),
                str(item.get("state")),
                _short_text(item.get("reason"), "ambiguity reason"))
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
                        "proposed_next_action"),
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
            # Name the rejected value and the admitted set. A closed
            # vocabulary refused without stating itself leaves the model to
            # guess again, and a live run spent seven passes proposing
            # semantic step ids here because the packet's question portfolio
            # names those far more prominently than this schema does.
            raise AdaptivePractitionerError(
                f"next action kind {self.action_kind!r} is not admitted; the "
                f"admitted kinds are {list(NEXT_ACTION_KINDS)}. Semantic step "
                "ids such as those in the question portfolio are not action "
                "kinds")
        if not 0 <= self.confidence <= 1:
            raise AdaptivePractitionerError(
                "NextActionDecision confidence must be from zero through one")

    @classmethod
    def from_mapping(cls, value: object) -> "NextActionDecision":
        if not isinstance(value, dict):
            raise AdaptivePractitionerError(
                "NextActionDecision must be one object")
        # Derived from the record's own fields: a restated copy of
        # this list drifts the moment a field is added.
        required = {item.name for item in fields(cls)}
        if set(value) != required:
            raise AdaptivePractitionerError(
                _field_mismatch(value, required, "NextActionDecision"))
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
            _short_text(value["scheduling"], "scheduling"),
            _short_text(value["verification"], "verification"),
            _short_text(value["return_destination"],
                        "return_destination"),
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
    """One task plus mode, authority, and optional pass settings."""

    task: str
    mode: str = "non_deterministic"
    runs_dir: str = ""
    max_passes: "int | None" = None
    interaction_mode: str = "ask_when_material"
    allow_network_reads: bool = True
    allow_workspace_writes: bool = True
    allow_sandbox_commands: bool = True
    source_kind: str = "text"
    source_refs: tuple[str, ...] = ()
    feedback: tuple[TaskFeedback, ...] = ()
    workspace_root: str = ""
    allow_source_materialization_to_model: bool = False
    granularity_profile: str = "governed_semantic"
    persist_run_history: bool = True
    quiet_model_io: bool = False
    allow_local_execution: bool = False
    context_budget: ContextBudgetPolicy = field(
        default_factory=ContextBudgetPolicy)
    prior_region_evidence: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.prior_region_evidence, dict):
            raise AdaptivePractitionerError(
                "prior_region_evidence must be a mapping")
        try:
            json.dumps(self.prior_region_evidence, sort_keys=True)
        except (TypeError, ValueError) as exc:
            raise AdaptivePractitionerError(
                "prior_region_evidence must be JSON serializable") from exc
        if not self.task.strip():
            raise AdaptivePractitionerError("adaptive Practitioner needs a task")
        if self.mode not in ("deterministic", "hybrid", "non_deterministic"):
            raise AdaptivePractitionerError(
                "adaptive Practitioner mode is not registered")
        if (self.max_passes is not None
                and (not isinstance(self.max_passes, int)
                     or isinstance(self.max_passes, bool)
                     or self.max_passes < 1)):
            raise AdaptivePractitionerError(
                "max_passes must be positive when provided")
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
        if not isinstance(self.persist_run_history, bool):
            raise AdaptivePractitionerError(
                "persist_run_history must be a boolean")
        if not isinstance(self.allow_local_execution, bool):
            raise AdaptivePractitionerError(
                "allow_local_execution must be a boolean")
        if not isinstance(self.context_budget, ContextBudgetPolicy):
            raise AdaptivePractitionerError(
                "context_budget must be a ContextBudgetPolicy")
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
    reuse_observation_port: "ReuseObservationPort | None" = field(
        default=None, repr=False, compare=False)
    extension_snapshot: dict = field(default_factory=dict)

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
        if (self.reuse_observation_port is not None
                and not isinstance(
                    self.reuse_observation_port, ReuseObservationPort)):
            raise AdaptivePractitionerError(
                "reuse_observation_port has the wrong contract")
        if (not isinstance(self.extension_snapshot, dict)
                or (self.extension_snapshot
                and self.extension_snapshot.get("record_type")
                != "extension_snapshot/v1")):
            raise AdaptivePractitionerError(
                "extension_snapshot has an invalid contract")
@dataclass(frozen=True)
class ModelStepRequest:
    """One question-portfolio step and exact safe problem state."""

    step_id: str
    objective: str
    state: dict
    output_contract: str



#: How much of one diagnostic's payload travels on the progress stream. A
#: diagnostic that says nothing is the defect this bounds against; a
#: diagnostic that prints a whole artifact is the one it bounds.
_DIAGNOSTIC_DETAIL_BYTES = 1200


def _bounded_detail(payload: dict) -> str:
    """Render one screened diagnostic payload as bounded text.

    Serialized rather than nested so a writer that carries only scalar fields
    still delivers it, and truncated with its own marker so a reader can tell
    a short detail from a cut one.
    """
    try:
        text = json.dumps(payload, sort_keys=True, default=str)
    except (TypeError, ValueError):
        text = str(payload)
    if len(text) <= _DIAGNOSTIC_DETAIL_BYTES:
        return text
    return text[:_DIAGNOSTIC_DETAIL_BYTES] + "...[detail truncated]"


def _field_mismatch(value: dict, required: set, record_name: str) -> str:
    """Say which fields made a record inadmissible, not merely that some did.

    A refusal reading "fields do not match version 1" tells a reader that
    something is wrong and nothing about what. The unexpected and missing
    names are the whole content of the finding, and the model reading it on
    the repair attempt needs them more than anyone.
    """
    unexpected = sorted(set(value) - required)
    missing = sorted(required - set(value))
    parts = []
    if unexpected:
        parts.append(f"unexpected {unexpected}")
    if missing:
        parts.append(f"missing {missing}")
    return (f"{record_name} fields do not match version 1: "
            + "; ".join(parts) if parts else
            f"{record_name} fields do not match version 1")


def _new_action_fence():
    """One repeated-action fence per run.

    Imported when a run starts, so this record module keeps no
    import-time dependency on the supervision runtime.
    """
    from .action_fence import ActionFenceLedger
    return ActionFenceLedger()

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
    source_inspections: list[dict] = field(default_factory=list)
    #: The saved model-led reading of what each supplied file is, keyed to the
    #: manifest it was read from. Written once per distinct manifest by
    #: core.source_role_orientation and stated on every later call.
    source_roles: dict | None = None
    project_attempts: list[dict] = field(default_factory=list)
    verification_records: list[dict] = field(default_factory=list)
    context_snapshots: list[dict] = field(default_factory=list)
    #: What this run drew on from the portfolio it was offered, counted
    #: per option and saved with the result. Evidence for judging the
    #: portfolio, never a gate on what a later call may be offered.
    selection_tally: SelectionTally = field(default_factory=SelectionTally)
    selected_intelligence_refs: list[str] = field(default_factory=list)
    selected_memory_refs: list[str] = field(default_factory=list)
    progress_snapshots: list[tuple] = field(default_factory=list)
    unchanged_progress_snapshots: int = 0
    supervision_findings: list[dict] = field(default_factory=list)
    recovery_directives: list[dict] = field(default_factory=list)
    active_recovery_directive: dict | None = None
    recovery_rounds: int = 0
    generated_file_checkpoints: dict[str, dict] = field(default_factory=dict)
    #: Repeated-action fence. A supervision law, not an optional feature:
    #: every run has one, so no call site guards for its absence.
    action_fence: "ActionFenceLedger" = field(
        default_factory=lambda: _new_action_fence(), repr=False,
        compare=False)
    route_health: dict = field(default_factory=lambda: {})
    route_health_ledger: "object | None" = field(
        default=None, repr=False, compare=False)
    progress_sequence: int = 0
    active_pass_number: int = 0
    started_monotonic: float = field(
        default_factory=time.monotonic, repr=False, compare=False)

    def _runtime_facts_view(self) -> dict:
        """Exact runtime-owned facts, or an explicit absence record."""
        try:
            from .practitioner_runtime_facts import runtime_facts
            return runtime_facts(self)
        except Exception:
            return {
                "record_type": "practitioner_runtime_facts/v1",
                "authority": "runtime", "unavailable": True,
                "reason": "facts projection failed; ask the runtime "
                          "before guessing paths or permissions",
            }

    def available_capabilities(self) -> tuple[dict, ...]:
        """Return only capabilities usable under this run's current authority."""
        available = []
        for item in ADAPTIVE_CAPABILITIES:
            ref = item["capability_ref"]
            usable = (
                bool(self.request.source_refs)
                and self.request.allow_source_materialization_to_model
                if ref == "core.source.inspect" else
                self.request.allow_network_reads
                if ref == "core.web.get" else
                self.request.allow_network_reads
                and bool(os.environ.get("OLLAMA_API_KEY", "").strip())
                if ref == "core.web.search" else
                self.request.allow_workspace_writes
                and self.request.allow_sandbox_commands
                if ref == "core.generated_project" else
                # Available whenever the run may write a workspace, because
                # a run that can produce a file must be able to read it back.
                # Withholding this is what left a live run repairing code it
                # could not see for twenty passes.
                self.request.allow_workspace_writes
                if ref == "core.workspace.read" else False)
            if usable:
                available.append(item)
        return tuple(available)

    def publish(self, event_type: str, **fields) -> None:
        self.progress_sequence += 1
        owner = current_kernel_owner()
        loop_count = 0
        if owner is not None:
            loop_count = len({
                str(item.get("loop_id")) for item in owner.ledger.events
                if item.get("event") == "init" and item.get("loop_id")})
        model_calls = (self.model_session.calls_used
                       if self.model_session is not None else 0)
        event = {
            "event_type": event_type,
            "run_id": self.run_id,
            "progress_sequence": self.progress_sequence,
            "pass_number": self.active_pass_number,
            "loop_count": loop_count,
            "model_calls_completed": model_calls,
            "model_call_number": (
                model_calls + 1 if event_type == "model.step.started" else 0),
            "source_inspections_completed": len(self.source_inspections),
            "project_attempts_completed": len(self.project_attempts),
            "elapsed_seconds": round(
                time.monotonic() - self.started_monotonic, 3),
            **fields,
        }
        if self.dependencies.progress is not None:
            self.dependencies.progress(event)

    def checkpoint_generated_file(
            self, checkpoint_key: str, path: str, content: str,
            contract_digest: str) -> dict:
        """Keep one exact generated file reusable within the active run."""
        payload = self.artifacts.capture(
            content, media_type="text/plain",
            artifact_kind="generated_project_file_checkpoint")
        record = {
            "checkpoint_key": checkpoint_key, "path": path,
            "content": content, "content_digest": payload.raw.digest,
            "contract_digest": contract_digest,
            "artifact_ref": payload.raw.to_dict(),
            "byte_count": payload.raw.byte_count,
        }
        self.generated_file_checkpoints[checkpoint_key] = record
        return {key: value for key, value in record.items()
                if key != "content"}

    def generated_file_checkpoint_summaries(self) -> list[dict]:
        """Return checkpoint identity without exposing file bodies."""
        return [{key: value for key, value in item.items()
                 if key != "content"}
                for item in self.generated_file_checkpoints.values()]

    def diagnostic(self, code: str, payload: dict) -> None:  # noqa: D401
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
        # The payload travels as one named field as well as spread. A
        # progress writer with a field allowlist keeps what it recognizes and
        # silently drops the rest, so a diagnostic whose detail is spread
        # across ad-hoc keys arrives naming a problem and saying nothing about
        # it. One field survives any allowlist that carries it.
        self.publish("practitioner.diagnostic", diagnostic_code=code,
                     diagnostic_detail=_bounded_detail(safe), **safe)

    def _record_generation_outcome(
            self, request: ModelStepRequest, *, error_code: str) -> None:
        """Fold one observed model-step outcome into route health.

        Route identity comes from the session's last gateway result; without
        it (fixture sessions, deterministic ports) nothing is recorded and
        the ledger stays empty, which is honest.
        """
        if self.route_health_ledger is None:
            return
        results = getattr(self.model_session, "results", None) \
            if self.model_session is not None else None
        if not results:
            return
        last = results[-1]
        route_name = str(getattr(last, "route", "") or "")
        provider = str(getattr(last, "provider", "") or "")
        model = str(getattr(last, "model", "") or "")
        output_tokens = getattr(last, "output_tokens", None)
        if not route_name or not model:
            return
        from .route_health import GenerationOutcome
        try:
            self.route_health_ledger.record_outcome(GenerationOutcome(
                route_name=route_name, provider=provider, model=model,
                error_code=error_code,
                output_tokens=(
                    int(output_tokens)
                    if isinstance(output_tokens, int) else None),
                elapsed_seconds=(
                    float(getattr(last, "elapsed_seconds", 0) or 0) or None),
                requested_output_ceiling=getattr(
                    last, "maximum_output_tokens", None)))
        except Exception:
            self.publish(
                "practitioner.diagnostic",
                diagnostic_code="route_health_record_skipped")

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
        persona_candidates = self.portfolio.persona_candidates(request.step_id)
        guidance_candidates = self.portfolio.guidance_candidates(
            request.step_id)
        question_candidates = self.portfolio.question_candidates(
            request.step_id)
        from ..loop.intelligence_loops import serve_context_intelligence
        selected_context = serve_context_intelligence(
            f"adaptive-context-{request.step_id}", lambda: {
                "base_role": self.portfolio.persona.to_dict(),
                "persona_candidates": list(persona_candidates),
                "guidance_candidates": list(guidance_candidates),
                "question_candidates": list(question_candidates),
                "active_step_hint": step_context.to_dict(),
                "selection_authority": "model",
            }, parent=owner, profile_id="intelligence.context.serve")
        context_value = selected_context["value"]
        prior_events = []
        for event in owner.ledger.events:
            if event.get("custom_kind") == "llm_work_packet_assembled":
                break
            prior_events.append({
                key: value
                for key, value in event.items() if key != "ts"
                and not any(marker in key.lower() for marker in (
                    "secret", "token", "authorization", "prompt", "content"))})
        capability_descriptors = self.available_capabilities()
        from ..templates.library import TemplateLibrary
        template_candidates = [{
            "template_id": item.template_id,
            "version": item.version,
            "name": item.name,
            "description": item.description,
            "task_type": item.task_type,
            "output_kind": item.output_kind,
            "required_variables": list(item.required_variables),
            "advisory_only": True,
        } for item in TemplateLibrary().search(self.request.task)]
        extension_candidates = {
            "capabilities": list(
                self.dependencies.extension_snapshot.get(
                    "capabilities", ())),
            "intelligence_refs": list(
                self.dependencies.extension_snapshot.get(
                    "intelligence_entries", ())),
            "skills": list(
                self.dependencies.extension_snapshot.get("skills", ())),
            "plugins": list(
                self.dependencies.extension_snapshot.get("plugins", ())),
            "snapshot_digest": str(
                self.dependencies.extension_snapshot.get(
                    "content_digest", "")),
        }
        # The typed state view is bounded exactly once, here, where it enters
        # the model channel. Trimmed or deduplicated text stays in Run History
        # artifacts; every change is recorded against the owner Loop.
        bounded_state, state_trims = bound_state_view(
            request.state, self.request.context_budget)
        if state_trims:
            budget_policy = self.request.context_budget
            removed_bytes = sum(item.removed_bytes for item in state_trims)
            owner.ledger.record(
                loop_id=owner.loop_id, event="custom",
                custom_kind="context_budget_applied",
                procedure_step=request.step_id,
                policy_id=budget_policy.policy_id,
                policy_version=budget_policy.version,
                trim_count=len(state_trims), bytes_removed=removed_bytes,
                trims=tuple(item.to_dict() for item in state_trims[:40]))
            self.publish(
                "practitioner.context_budget_applied", step=request.step_id,
                trim_count=len(state_trims), bytes_removed=removed_bytes)
        runtime_facts_view = self._runtime_facts_view()
        blocks = (
            LLMContextBlock.create(
                "persona", "persona_context", self.portfolio.persona.version,
                self.portfolio.persona.persona_id,
                "base role and optional model-selected perspectives", 0,
                {"base_role": context_value["base_role"],
                 "candidates": context_value["persona_candidates"],
                 "selection_authority": "model"}),
            LLMContextBlock.create(
                f"guidance.{request.step_id}", "context_intelligence",
                self.portfolio.version, self.portfolio.portfolio_id,
                "optional guidance with step affinity metadata", 1,
                {"selection_authority": "model",
                 "candidates": context_value["guidance_candidates"]}),
            LLMContextBlock.create(
                f"questions.{request.step_id}", "question_portfolio",
                self.portfolio.version, self.portfolio.portfolio_id,
                "optional question sets with an active-step hint", 2,
                {"selection_authority": "model",
                 "active_step_hint": context_value["active_step_hint"],
                 "candidates": context_value["question_candidates"]}),
            LLMContextBlock.create(
                "deterministic_attempt", "attempt_trace", "1.0.0",
                "adaptive_practitioner",
                "exact-attempt result or explicit LLM-first skip", 3,
                self.deterministic_attempt.to_dict()),
            LLMContextBlock.create(
                "current_state", "task_context", "1.0.0",
                "active Practitioner run", "latest accepted state", 4,
                {"task_state": bounded_state,
                 "source_kind": self.request.source_kind,
                 "source_refs": list(self.request.source_refs),
                 "task_feedback": [
                     item.to_dict() for item in self.request.feedback],
                 "interaction_mode": self.request.interaction_mode,
                 "run_mode": self.request.mode}),
            LLMContextBlock.create(
                "runtime_facts", "runtime_facts", "1.0.0",
                "practitioner runtime", "exact facts the runtime states", 5,
                runtime_facts_view),
            LLMContextBlock.create(
                "template_candidates", "procedure_candidates", "1.0.0",
                "core template library", "optional reusable patterns", 6,
                {"binding_authority": "none",
                 "candidates": template_candidates}),
            LLMContextBlock.create(
                "capability_descriptors", "capability_snapshot", "1.0.0",
                "core capability registry", "available execution paths", 7,
                {"active": list(capability_descriptors),
                 "added_file_candidates": extension_candidates}),
            LLMContextBlock.create(
                "deterministic_event_history", "attempt_event_history", "1.0.0",
                "canonical Loop event log", "complete prior event history", 8,
                prior_events),
        )
        if self.request.prior_region_evidence:
            # Advisory evidence from earlier runs in this task region: the
            # region statistics, the shortcut decision, and the tuning
            # decision. The model may use it; it selects nothing by itself.
            blocks = blocks + (LLMContextBlock.create(
                "prior_region_evidence", "region_evidence", "1.0.0",
                "saved Run History projections",
                "advisory evidence from earlier runs in this task region", 9,
                {"selection_authority": "model", "advisory": True,
                 **self.request.prior_region_evidence}),)
        requested_state_version = int(request.state.get("state_version", -1))
        eligible_orientation_versions = [
            version for version in self.orientation_by_version
            if version <= requested_state_version]
        orientation = (
            self.orientation_by_version[max(eligible_orientation_versions)]
            if eligible_orientation_versions else None)
        permissions = tuple(name for name, allowed in (
                ("source_read",
                 self.request.allow_source_materialization_to_model
                 and bool(self.request.source_refs)),
                ("network_read", self.request.allow_network_reads),
                ("workspace_write", self.request.allow_workspace_writes),
                ("sandbox_command", self.request.allow_sandbox_commands),
                ("local_host_execution", self.request.allow_local_execution))
                if allowed)
        maximum_calls = self.model_session.authority.max_model_calls
        remaining_calls = (None if maximum_calls is None else max(
            0, maximum_calls - self.model_session.calls_used))
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
                "base_role": context_value["base_role"],
                "persona_candidates": context_value["persona_candidates"],
                "selection_authority": "model",
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
                "current_state": bounded_state,
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
            context_intelligence=tuple(
                context_value["guidance_candidates"]),
            question_portfolio={
                "selection_authority": "model",
                "active_step_hint": context_value["active_step_hint"],
                "candidates": context_value["question_candidates"]},
            capability_context={
                "available_capabilities": list(capability_descriptors),
                "added_file_candidates": extension_candidates,
                # Facts the runtime holds exactly: the admitted source
                # manifest, the workspace, the isolation, the permissions in
                # force, and every refused call so far. They render with the
                # capability limits because that is what they bound.
                "runtime_facts": runtime_facts_view,
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
                "format": "json", "additional_text_allowed": False,
                # Asked of every step, answered beside the step's own schema,
                # and removed before that schema is validated. The portfolio
                # can only be judged on use, and use is only visible if the
                # caller says what it used.
                "selection_report": SELECTION_REPORT_CONTRACT},
            policy_context={
                "interaction_mode": self.request.interaction_mode,
                "permissions": list(permissions),
                "model_cannot_grant_authority": True},
            token_budget={"model_calls_remaining": remaining_calls},
            source_refs=tuple(self.request.source_refs), context_blocks=blocks)
        offered_options = {
            "used_perspectives": [
                str(item.get("persona_id") or "")
                for item in packet.persona_context["persona_candidates"]],
            "used_question_refs": [
                str(item.get("step_id") or "")
                for item in packet.question_portfolio["candidates"]],
            "used_guidance_refs": [
                str(item.get("record_id") or "")
                for item in packet.context_intelligence],
        }
        self.selection_tally.note_offered(request.step_id)
        packet_artifact = self.artifacts.store.put(
            serialize_work_packet(packet, owner),
            media_type="application/json", encoding="utf-8",
            artifact_kind="llm_work_packet")
        value = None
        format_attempt = 1
        invalid_digests = set()
        format_failure_code = ""
        rejected_output_digest = ""
        while value is None:
            if format_attempt > _MAXIMUM_FORMAT_ATTEMPTS:
                self.publish(
                    "model.step.repair_exhausted", step=request.step_id,
                    format_attempt=format_attempt - 1,
                    failure_code=format_failure_code,
                    response_digest=rejected_output_digest)
                raise ModelResponseRepairStalled(
                    f"model step {request.step_id} produced "
                    f"{format_attempt - 1} invalid outputs; format repair is "
                    f"bounded at {_MAXIMUM_FORMAT_ATTEMPTS} attempts")
            profile = self.portfolio.assembly_profile(
                bool(request.state.get("failures")) or format_attempt > 1)
            assembled = assemble_work_packet(
                AdaptivePromptAssemblyRequest(
                    packet, profile.profile_id, profile.layout_policy,
                    format_repair=format_attempt > 1,
                    format_failure_code=format_failure_code,
                    rejected_output_digest=rejected_output_digest,
                    granularity_profile=self.request.granularity_profile), owner)
            snapshot = assembled.snapshot.to_dict()
            budget = self.request.context_budget
            if (budget.packet_estimated_tokens_max is not None
                    and snapshot["estimated_tokens"]
                    > budget.packet_estimated_tokens_max):
                self.publish(
                    "model.step.context_budget_exceeded",
                    step=request.step_id,
                    estimated_tokens=snapshot["estimated_tokens"],
                    packet_estimated_tokens_max=
                        budget.packet_estimated_tokens_max,
                    prompt_digest=snapshot["prompt_digest"])
                raise SolutionModelError(
                    f"context_budget_exceeded: the assembled packet for step "
                    f"{request.step_id} is estimated at "
                    f"{snapshot['estimated_tokens']} tokens, above the "
                    f"operator ceiling of {budget.packet_estimated_tokens_max}",
                    error_code="context_budget_exceeded")
            # One manifest per assembled packet: what the model could see,
            # what was compacted or excluded and why, and whether the
            # estimate fits the operator ceiling. The exact route window is
            # decided by the gateway, whose preflight refusal is separate.
            manifest = build_context_pack_manifest(
                run_id=self.run_id, loop_id=owner.loop_id,
                step_id=request.step_id, packet=packet, snapshot=snapshot,
                trims=state_trims, policy=budget)
            manifest_artifact = self.artifacts.store.put(
                json.dumps(manifest.to_dict(), sort_keys=True,
                           separators=(",", ":")).encode("utf-8"),
                media_type="application/json", encoding="utf-8",
                artifact_kind="context_pack_manifest")
            owner.ledger.record(
                loop_id=owner.loop_id, event="custom",
                custom_kind="context_pack_compiled",
                procedure_step=request.step_id,
                format_attempt=format_attempt,
                context_pack_artifact_ref=manifest_artifact.object_key,
                **manifest.summary())
            self.context_snapshots.append({
                "step": request.step_id, "objective": request.objective,
                "packet_id": packet.packet_id,
                "packet_digest": packet.content_digest,
                "packet_artifact_ref": packet_artifact.to_dict(),
                "context_pack": manifest.summary(),
                "context_pack_artifact_ref": manifest_artifact.to_dict(),
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
            for transport_attempt in range(1, _MAXIMUM_TRANSPORT_ATTEMPTS + 1):
                trace_event = {
                    "step": request.step_id,
                    "objective": request.objective[:160],
                    "format_attempt": format_attempt,
                    "transport_attempt": transport_attempt,
                    "prompt_digest": snapshot["prompt_digest"],
                    "prompt_bytes": len(assembled.prompt),
                    "output_schema_digest": hashlib.sha256(
                        request.output_contract.encode("utf-8")).hexdigest(),
                }
                if not self.request.quiet_model_io:
                    trace_event["prompt_text"] = assembled.prompt
                self.publish("model.step.started", **trace_event)
                if self.route_health_ledger is None:
                    from .route_health import RouteHealthLedger
                    self.route_health_ledger = RouteHealthLedger()
                try:
                    text = self.model_session.invoke(
                        ModelInvocationRequest(
                            assembled.prompt,
                            temperature=assembled.temperature), owner)
                    self._record_generation_outcome(request, error_code="")
                    break
                except SolutionModelError as exc:
                    error_code = exc.error_code or "model_gateway_failed"
                    self._record_generation_outcome(
                        request, error_code=error_code)
                    self.publish(
                        "model.step.transport_failed", step=request.step_id,
                        format_attempt=format_attempt,
                        transport_attempt=transport_attempt,
                        error_code=error_code,
                        prompt_digest=snapshot["prompt_digest"])
                    retryable = error_code in _RETRYABLE_TRANSPORT_ERRORS
                    final_attempt = (
                        transport_attempt >= _MAXIMUM_TRANSPORT_ATTEMPTS)
                    if not retryable or final_attempt:
                        raise
                    if error_code == "gateway_timeout" \
                            and self.route_health_ledger is not None:
                        for preference in (
                                self.route_health_ledger
                                .advise_route_preferences()):
                            if (preference.get("prefer_failover")
                                    and preference.get(
                                        "gateway_timeout_walls")):
                                self.publish(
                                    "practitioner.diagnostic",
                                    diagnostic_code=(
                                        "route_ceiling_wall_detected"),
                                    route_name=preference.get("route_name"),
                                    prefer_failover=True,
                                    reason=preference.get("reason"))
                                break
                    # Governed backoff: 1s, then 2s, or a longer wait when
                    # the thing being waited on is a limit rather than a
                    # connection. Every retry passes through
                    # model_session.invoke again, so every physical request
                    # stays visible and counted in the run record.
                    if error_code in _SLOW_BACKOFF_ERRORS:
                        time.sleep(_SLOW_BACKOFF_SECONDS * transport_attempt)
                    else:
                        time.sleep(2 ** (transport_attempt - 1))
            contract_digest = hashlib.sha256(
                request.output_contract.encode("utf-8")).hexdigest()
            if not self.request.quiet_model_io:
                self.publish(
                    "model.step.raw_output", step=request.step_id,
                    format_attempt=format_attempt,
                    output_digest=hashlib.sha256(
                        text.encode("utf-8")).hexdigest(),
                    output_text=text)
            admitted = admit_model_response_as_loop(
                ModelResponseAdmissionRequest(
                    text, "inline:" + contract_digest, contract_digest),
                parent=owner)
            value = admitted.value
            if isinstance(value, dict):
                # Read before the step's typed validator does, and removed so
                # that validator never has to know these keys exist.
                reported = {key: value.pop(key) for key in SELECTION_KEYS
                            if key in value}
                if reported:
                    selection = admitted_selection(reported, offered_options)
                    self.selection_tally.note(request.step_id, selection)
                    if selection:
                        self.publish(
                            "practitioner.options.selected",
                            step=request.step_id, **{
                                key: item for key, item in selection.items()
                                if key != "named_but_not_offered"})
                    outside = selection.get("named_but_not_offered")
                    if outside:
                        self.diagnostic("option_named_but_not_offered", {
                            "step": request.step_id, "named": outside})
            if value is not None:
                _preview = json.dumps(
                    value, default=str, sort_keys=True)
                completed_event = {
                    "step": request.step_id,
                    "format_attempt": format_attempt,
                    "transport_attempt": transport_attempt,
                    "output_digest": admitted.raw_digest,
                    "admitted_strategy": admitted.strategy,
                    "output_bytes": len(_preview),
                }
                completed_event["output_preview"] = (
                    _preview if not self.request.quiet_model_io
                    else _preview[:480])
                self.publish(
                    "model.step.completed", **completed_event)
                if admitted.strategy != "strict_json":
                    self.publish(
                        "model.step.output_repaired", step=request.step_id,
                        format_attempt=format_attempt,
                        parse_strategy=admitted.strategy,
                        response_digest=admitted.raw_digest,
                        admission_loop_id=admitted.loop_id)
                break
            self.publish(
                "model.step.output_invalid", step=request.step_id,
                format_attempt=format_attempt,
                failure_code=admitted.failure_code,
                parse_strategy=admitted.strategy,
                response_digest=admitted.raw_digest,
                admission_loop_id=admitted.loop_id)
            if admitted.raw_digest in invalid_digests:
                self.publish(
                    "model.step.repair_stalled", step=request.step_id,
                    format_attempt=format_attempt,
                    failure_code="repeated_invalid_output",
                    response_digest=admitted.raw_digest,
                    admission_loop_id=admitted.loop_id)
                raise ModelResponseRepairStalled(
                    f"model step {request.step_id} repeated the same invalid "
                    "JSON output without progress")
            invalid_digests.add(admitted.raw_digest)
            format_failure_code = admitted.failure_code
            rejected_output_digest = admitted.raw_digest
            format_attempt += 1
        return value
