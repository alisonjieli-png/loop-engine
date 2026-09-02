"""Immutable built-in loop profile definitions.

This module owns profile data and local shape validation. Runtime binding,
inheritance resolution, whole-tree validation, and version handshakes live in
``loop_profile_ontology``. Keeping the catalog separate makes profile growth a
data change instead of growth in runtime behavior.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .loop_role import LOOP_RELATIONSHIP_KINDS
from .recursive_loop import EXIT_CONDITIONS, LOGICAL_KINDS, MODES
from .loop_control import normalize_exit_condition


PROFILE_ONTOLOGY_VERSION = "1.0.0"
PROFILE_FAMILIES = ("universal", "practitioner", "intelligence", "solution")
PROFILE_STATES = ("abstract", "registered", "candidate")
THINKING_POWER_POLICIES = ("forbidden", "required_for_model_modes")
MODEL_MODES = ("hybrid", "non_deterministic")
ROOT_PROFILE_ID = "loop"
TOP_BRANCH_IDS = ("practitioner", "intelligence", "solution")
INTELLIGENCE_BRANCH_IDS = (
    "intelligence.context",
    "intelligence.code",
    "intelligence.runtime_history_solution",
    "intelligence.user_feedback",
)
ROLE_PROFILE_ALIASES = (
    ("researcher", "practitioner.research"),
    ("solver", "practitioner.solver"),
    ("verifier", "practitioner.verifier"),
    ("practitioner.researcher", "practitioner.research"),
    ("intelligence.search", "intelligence.search"),
    ("intelligence.materialize", "intelligence.materialize"),
    ("intelligence.invoke", "intelligence.code.invoke"),
    ("intelligence.replay", "intelligence.runtime_history_solution.replay"),
    ("intelligence.interpret", "intelligence.user_feedback.interpret"),
    ("solution.component", "solution.atomic_component"),
    ("solution.validator", "solution.validator"),
    ("solution.router", "solution.router_fallback"),
    ("solution.fallback", "solution.router_fallback"),
    ("solution.ensemble", "solution.ensemble"),
)

_PROFILE_ID = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*$")
_SEMVER = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")


class LoopProfileError(ValueError):
    """A profile, binding, or compatibility request failed closed."""


def _version_tuple(value: str) -> tuple[int, int, int]:
    match = _SEMVER.fullmatch(value)
    if match is None:
        raise LoopProfileError(
            f"profile version {value!r} must use MAJOR.MINOR.PATCH")
    return tuple(int(part) for part in match.groups())


def _normalized_strings(name: str, values) -> tuple[str, ...]:
    normalized = tuple(values)
    if any(not isinstance(value, str) or not value.strip()
           for value in normalized):
        raise LoopProfileError(f"{name} must contain non-empty strings")
    if len(normalized) != len(set(normalized)):
        raise LoopProfileError(f"{name} cannot contain duplicates")
    return normalized


@dataclass(frozen=True)
class LoopProfileRef:
    """An exact reference to one profile version."""

    profile_id: str
    version: str = PROFILE_ONTOLOGY_VERSION

    def __post_init__(self) -> None:
        if not _PROFILE_ID.fullmatch(self.profile_id):
            raise LoopProfileError(
                "profile_id must use lowercase dotted names")
        _version_tuple(self.version)

    @property
    def key(self) -> tuple[str, str]:
        return self.profile_id, self.version


def resolve_profile_alias(
        name: str, version: str = PROFILE_ONTOLOGY_VERSION) -> LoopProfileRef:
    """Resolve a short role alias to an exact position-neutral profile."""
    if not isinstance(name, str) or not name.strip():
        raise LoopProfileError("a profile name or alias must be non-empty")
    profile_id = dict(ROLE_PROFILE_ALIASES).get(name, name)
    return LoopProfileRef(profile_id, version)


@dataclass(frozen=True)
class LoopProfileSpec:
    """One immutable profile definition in the catalog."""

    profile_id: str
    title: str
    family: str
    purpose: str
    version: str = PROFILE_ONTOLOGY_VERSION
    parent: "LoopProfileRef | None" = None
    state: str = "registered"
    step_template_id: str = ""
    exit_condition: str = ""
    allowed_logical_kinds: tuple[str, ...] = LOGICAL_KINDS
    allowed_modes: tuple[str, ...] = MODES
    required_fields: tuple[str, ...] = ()
    required_capabilities: tuple[str, ...] = ()
    thinking_power_policy: str = "required_for_model_modes"
    def __post_init__(self) -> None:
        if self.exit_condition:
            object.__setattr__(
                self, "exit_condition", normalize_exit_condition(
                    self.exit_condition))
        LoopProfileRef(self.profile_id, self.version)
        if not self.title.strip() or not self.purpose.strip():
            raise LoopProfileError("a profile needs a title and purpose")
        if self.family not in PROFILE_FAMILIES:
            raise LoopProfileError(
                f"family {self.family!r} must be one of {PROFILE_FAMILIES}")
        if self.state not in PROFILE_STATES:
            raise LoopProfileError(
                f"state {self.state!r} must be one of {PROFILE_STATES}")
        modes = _normalized_strings("allowed_modes", self.allowed_modes)
        logical_kinds = _normalized_strings(
            "allowed_logical_kinds", self.allowed_logical_kinds)
        fields = _normalized_strings("required_fields", self.required_fields)
        capabilities = _normalized_strings(
            "required_capabilities", self.required_capabilities)
        object.__setattr__(self, "allowed_modes", modes)
        object.__setattr__(self, "allowed_logical_kinds", logical_kinds)
        object.__setattr__(self, "required_fields", fields)
        object.__setattr__(self, "required_capabilities", capabilities)
        if not modes:
            raise LoopProfileError("allowed_modes cannot be empty")
        if not logical_kinds:
            raise LoopProfileError("allowed_logical_kinds cannot be empty")
        if any(mode not in MODES for mode in modes):
            raise LoopProfileError(f"allowed_modes must use {MODES}")
        if any(kind not in LOGICAL_KINDS for kind in logical_kinds):
            raise LoopProfileError(
                f"allowed_logical_kinds must use {LOGICAL_KINDS}")
        if self.thinking_power_policy not in THINKING_POWER_POLICIES:
            raise LoopProfileError(
                "thinking_power_policy must be forbidden or "
                "required_for_model_modes")
        if (not any(mode in MODEL_MODES for mode in modes)
                and self.thinking_power_policy != "forbidden"):
            raise LoopProfileError(
                "a deterministic-only profile must forbid LLM thinking power")
        if self.state != "abstract" and not self.step_template_id:
            raise LoopProfileError(
                "a runnable profile needs a step_template_id")
        if (self.state != "abstract"
                and self.exit_condition not in EXIT_CONDITIONS):
            raise LoopProfileError(
                f"a runnable profile needs an exit_condition in "
                f"{EXIT_CONDITIONS}")

    @property
    def ref(self) -> LoopProfileRef:
        return LoopProfileRef(self.profile_id, self.version)


def _spec(profile_id: str, title: str, family: str, purpose: str, *,
          parent: str | None = None, state: str = "registered",
          template: str = "", exit_condition: str = "",
          kinds: tuple[str, ...] = LOGICAL_KINDS,
          modes: tuple[str, ...] = MODES,
          fields: tuple[str, ...] = (), capabilities: tuple[str, ...] = (),
          thinking: str = "required_for_model_modes") -> LoopProfileSpec:
    return LoopProfileSpec(
        profile_id=profile_id, title=title, family=family, purpose=purpose,
        parent=LoopProfileRef(parent) if parent else None, state=state,
        step_template_id=template, exit_condition=exit_condition,
        allowed_logical_kinds=kinds, allowed_modes=modes,
        required_fields=fields, required_capabilities=capabilities,
        thinking_power_policy=thinking)


LOOP_PROFILE_ONTOLOGY = (
    _spec(
        "loop", "Loop", "universal",
        "Defines the shared identity used by every runnable loop.",
        state="abstract",
        fields=("loop_contract", "loop_condition", "exit_condition",
                "step_profile", "mode_policy")),
    _spec(
        "practitioner", "Practitioner", "practitioner",
        "Uses loops to understand, build, test, and improve work.",
        parent="loop", state="abstract",
        capabilities=("loop_spawn", "run_history_write")),
    _spec(
        "intelligence", "Intelligence", "intelligence",
        "Serves or transforms one item from an intelligence layer.",
        parent="loop", state="abstract",
        capabilities=("intelligence_reference",)),
    _spec(
        "solution", "Solution", "solution",
        "Runs one part of a finished Solution Canvas.",
        parent="loop", state="abstract", kinds=("execution",),
        capabilities=("solution_canvas",)),

    # Practitioner profiles. Self-improvement remains a Practitioner task.
    _spec(
        "practitioner.reference_nine_step", "Reference nine-step Practitioner",
        "practitioner", "Runs the reference Practitioner step sequence.",
        parent="practitioner", template="reference_nine_step",
        exit_condition="steps_complete", kinds=("execution", "task_semantic")),
    _spec(
        "practitioner.compact_five_step", "Compact five-step Practitioner",
        "practitioner", "Runs a short load, choose, act, check, commit cycle.",
        parent="practitioner", template="compact_five_beat",
        exit_condition="steps_complete", kinds=("execution", "task_semantic")),
    _spec(
        "practitioner.research", "Research Practitioner", "practitioner",
        "Finds source-bound information and checks it before use.",
        parent="practitioner", template="research_intensive",
        exit_condition="steps_complete", kinds=("task_semantic",),
        fields=("research_question", "source_policy"),
        capabilities=("retrieval_search", "source_validation")),
    _spec(
        "practitioner.solver", "Solver Practitioner", "practitioner",
        "Builds, tests, diagnoses, and repairs a proposed solution.",
        parent="practitioner", template="build_test_repair",
        exit_condition="steps_complete", kinds=("task_semantic",),
        fields=("acceptance_test",),
        capabilities=("solution_build", "independent_verification")),
    _spec(
        "practitioner.verifier", "Verifier Practitioner", "practitioner",
        "Tries to reject a claim before accepting it.",
        parent="practitioner", template="adversarial_review",
        exit_condition="steps_complete", kinds=("execution", "task_semantic"),
        fields=("claim_set", "acceptance_rule"),
        capabilities=("independent_verification",)),
    _spec(
        "practitioner.self_improvement", "Self-improvement task",
        "practitioner",
        "Reviews bounded history and stages candidates for separate review.",
        parent="practitioner", template="continuous_improvement",
        exit_condition="steps_complete", kinds=("search_improvement",),
        fields=("history_population", "candidate_policy"),
        capabilities=("run_history_read", "intelligence_search",
                      "candidate_stage")),
    _spec(
        "practitioner.code_execution", "Code execution Practitioner",
        "practitioner", "Runs one bounded code operation and returns its result.",
        parent="practitioner", template="atomic_code_only",
        exit_condition="accepted_success", kinds=("execution",),
        modes=("deterministic",), fields=("operation_ref",),
        capabilities=("code_execution",), thinking="forbidden"),
    _spec(
        "practitioner.checklist", "Checklist Practitioner", "practitioner",
        "Inspects typed facts against ordered deterministic checks and "
        "escalates only when a blocking item fails.",
        parent="practitioner", template="gated_checklist",
        exit_condition="steps_complete", kinds=("execution",),
        modes=("deterministic",), fields=("checklist_items", "state_ref"),
        capabilities=("loop_spawn",), thinking="forbidden"),

    # Cross-layer Intelligence operations. Layer-specific profiles remain
    # below the four Intelligence branches.
    _spec(
        "intelligence.search", "Search Intelligence", "intelligence",
        "Searches selected intelligence layers and returns typed references.",
        parent="intelligence", template="compact_five_beat",
        exit_condition="accepted_success", kinds=("execution",),
        modes=("deterministic",), fields=("query", "layers"),
        capabilities=("intelligence_search",), thinking="forbidden"),
    _spec(
        "intelligence.materialize", "Materialize Intelligence",
        "intelligence",
        "Verifies and loads one selected intelligence reference.",
        parent="intelligence", template="atomic_code_only",
        exit_condition="accepted_success", kinds=("execution",),
        modes=("deterministic",),
        fields=("intelligence_ref", "expected_digest"),
        capabilities=("intelligence_materialize", "digest_verify"),
        thinking="forbidden"),

    # Intelligence branches and item-serving profiles.
    _spec(
        "intelligence.context", "Context Intelligence", "intelligence",
        "Serves questions, methods, examples, formats, and source notes.",
        parent="intelligence", state="abstract",
        fields=("context_record_ref",)),
    _spec(
        "intelligence.context.serve", "Serve Context Intelligence",
        "intelligence", "Returns one selected context item through a loop.",
        parent="intelligence.context", template="atomic_code_only",
        exit_condition="accepted_success", kinds=("execution",),
        modes=("deterministic",), capabilities=("context_store_read",),
        thinking="forbidden"),
    _spec(
        "intelligence.context.search", "Search Context Intelligence",
        "intelligence", "Searches context records and returns loop references.",
        parent="intelligence.context", template="compact_five_beat",
        exit_condition="accepted_success", kinds=("execution",),
        modes=("deterministic",), fields=("query",),
        capabilities=("context_search",), thinking="forbidden"),
    _spec(
        "intelligence.context.frame", "Frame Context Intelligence",
        "intelligence",
        "Frames selected context for a task without changing the stored item.",
        parent="intelligence.context", template="compact_five_beat",
        exit_condition="accepted_success", kinds=("execution",),
        fields=("task_context",), capabilities=("context_framing",)),

    _spec(
        "intelligence.code", "Code Intelligence", "intelligence",
        "Serves executable capabilities and large external code references.",
        parent="intelligence", state="abstract",
        fields=("code_asset_ref", "code_contract")),
    _spec(
        "intelligence.code.resolve", "Resolve Code Intelligence",
        "intelligence",
        "Resolves a code reference and checks its typed capability handshake.",
        parent="intelligence.code", template="compact_five_beat",
        exit_condition="accepted_success", kinds=("execution",),
        modes=("deterministic",),
        capabilities=("code_reference_resolver",), thinking="forbidden"),
    _spec(
        "intelligence.code.invoke", "Invoke Code Intelligence",
        "intelligence", "Runs one selected code capability through a loop.",
        parent="intelligence.code", template="atomic_code_only",
        exit_condition="accepted_success", kinds=("execution",),
        modes=("deterministic",), fields=("operation_ref",),
        capabilities=("code_execution",), thinking="forbidden"),
    _spec(
        "intelligence.code.package", "Load code package or repository",
        "intelligence",
        "Loads a selected package or repository by reference and entry point.",
        parent="intelligence.code", template="compact_five_beat",
        exit_condition="accepted_success", kinds=("execution",),
        modes=("deterministic",),
        fields=("artifact_manifest", "entry_point"),
        capabilities=("artifact_loader",), thinking="forbidden"),

    _spec(
        "intelligence.runtime_history_solution",
        "Runtime History and Solution Intelligence", "intelligence",
        "Serves saved runs, decisions, failures, measurements, and solutions.",
        parent="intelligence", state="abstract", fields=("history_ref",)),
    _spec(
        "intelligence.runtime_history_solution.search", "Search prior work",
        "intelligence", "Searches saved runs and solutions for relevant work.",
        parent="intelligence.runtime_history_solution",
        template="compact_five_beat", exit_condition="accepted_success",
        kinds=("execution",), modes=("deterministic",), fields=("query",),
        capabilities=("run_history_search", "solution_search"),
        thinking="forbidden"),
    _spec(
        "intelligence.runtime_history_solution.replay", "Replay prior work",
        "intelligence", "Rebuilds a saved run from its event log.",
        parent="intelligence.runtime_history_solution",
        template="compact_five_beat", exit_condition="accepted_success",
        kinds=("execution",), modes=("deterministic",),
        capabilities=("run_history_replay",), thinking="forbidden"),
    _spec(
        "intelligence.runtime_history_solution.compare", "Compare prior work",
        "intelligence",
        "Compares prior results under one stated evaluator and population.",
        parent="intelligence.runtime_history_solution",
        template="adversarial_review", exit_condition="steps_complete",
        kinds=("execution",), fields=("comparison_contract",),
        capabilities=("result_comparison",)),

    _spec(
        "intelligence.user_feedback", "User Feedback Intelligence", "intelligence",
        "Serves scoped user guidance, corrections, priorities, and vetoes.",
        parent="intelligence", state="abstract", fields=("guidance_ref",)),
    _spec(
        "intelligence.user_feedback.serve", "Serve User Feedback Intelligence", "intelligence",
        "Returns active user guidance through a loop.",
        parent="intelligence.user_feedback", template="atomic_code_only",
        exit_condition="accepted_success", kinds=("execution",),
        modes=("deterministic",), capabilities=("guidance_store_read",),
        thinking="forbidden"),
    _spec(
        "intelligence.user_feedback.scope", "Scope User Feedback Intelligence", "intelligence",
        "Filters guidance by user, task, component, and time scope.",
        parent="intelligence.user_feedback", template="compact_five_beat",
        exit_condition="accepted_success", kinds=("execution",),
        modes=("deterministic",), fields=("guidance_scope",),
        capabilities=("guidance_scope_filter",), thinking="forbidden"),
    _spec(
        "intelligence.user_feedback.interpret", "Interpret User Feedback Intelligence",
        "intelligence",
        "Frames active guidance for the current task without changing it.",
        parent="intelligence.user_feedback", template="compact_five_beat",
        exit_condition="accepted_success", kinds=("execution",), fields=("task_context",),
        capabilities=("guidance_interpretation",)),

    # Solution profiles. These describe what runs for new input.
    _spec(
        "solution.atomic_component", "Atomic solution component", "solution",
        "Runs one typed deterministic operation in a Solution Canvas.",
        parent="solution", template="atomic_code_only", exit_condition="accepted_success",
        kinds=("execution",), modes=("deterministic", "hybrid", "non_deterministic"),
        fields=("operation_ref",), capabilities=("component_execution",),
        thinking="required_for_model_modes"),
    _spec(
        "solution.pipeline", "Solution pipeline", "solution",
        "Runs an ordered composition of type-compatible solution loops.",
        parent="solution", template="compact_five_beat",
        exit_condition="steps_complete", kinds=("execution",),
        modes=("deterministic", "hybrid", "non_deterministic"),
        fields=("ordered_components",),
        capabilities=("typed_connection_check", "pipeline_execution"),
        thinking="required_for_model_modes"),
    _spec(
        "solution.router_fallback", "Solution router and fallback", "solution",
        "Selects a route and runs an ordered fallback when a route fails.",
        parent="solution", template="compact_five_beat",
        exit_condition="accepted_success", kinds=("execution",),
        modes=("deterministic", "hybrid", "non_deterministic"),
        fields=("route_table", "fallback_order"),
        capabilities=("route_selection", "fallback_execution"),
        thinking="required_for_model_modes"),
    _spec(
        "solution.ensemble", "Solution ensemble", "solution",
        "Combines several solution outputs under one declared rule.",
        parent="solution", template="compact_five_beat",
        exit_condition="accepted_success", kinds=("execution",),
        modes=("deterministic", "hybrid", "non_deterministic"),
        fields=("member_loops", "combination_rule"),
        capabilities=("ensemble_combine",), thinking="required_for_model_modes"),
    _spec(
        "solution.validator", "Solution validator", "solution",
        "Checks a solution output against a typed acceptance rule.",
        parent="solution", template="adversarial_review",
        exit_condition="steps_complete", kinds=("execution",),
        modes=("deterministic", "hybrid", "non_deterministic"), fields=("acceptance_rule",),
        capabilities=("independent_verification",), thinking="required_for_model_modes"),
)


def profile_catalog(profiles=LOOP_PROFILE_ONTOLOGY) -> tuple[dict, ...]:
    """Return serializable, body-free profile metadata."""
    aliases = dict(ROLE_PROFILE_ALIASES)
    return tuple({
        "profile_id": profile.profile_id,
        "version": profile.version,
        "title": profile.title,
        "family": profile.family,
        "purpose": profile.purpose,
        "parent": (profile.parent.profile_id if profile.parent else ""),
        "parent_version": (profile.parent.version if profile.parent else ""),
        "state": profile.state,
        "step_template_id": profile.step_template_id,
        "exit_condition": profile.exit_condition,
        "allowed_logical_kinds": list(profile.allowed_logical_kinds),
        "allowed_modes": list(profile.allowed_modes),
        "required_fields": list(profile.required_fields),
        "required_capabilities": list(profile.required_capabilities),
        "thinking_power_policy": profile.thinking_power_policy,
        "supported_relationship_kinds": (
            list(LOOP_RELATIONSHIP_KINDS)
            if profile.family in TOP_BRANCH_IDS else []),
        "aliases": [name for name, target in aliases.items()
                    if target == profile.profile_id],
    } for profile in profiles)
