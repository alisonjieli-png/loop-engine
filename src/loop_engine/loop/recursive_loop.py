"""The Loop — the fundamental object.  Everything is a loop, run deterministically,
hybrid, or non-deterministically, and a loop can initialize another loop.

Owner vision (2026-08-23): move from "everything is a node" to "everything is a
LOOP".  A loop is a CLASS you initialize with its core configuration; one loop can
initialize (spawn) another loop that, say, does research and returns an answer the
parent uses to proceed — recursive initialization of loops, all tracked on a shared
ledger (decisions, inputs, outputs, modes, spawns, infra calls, confidence).  The
wedge is then just reusable Code Nodes + String intelligence flowing through a
universally flexible loop.

What you pass into a Loop at initialization:

  * ``framework`` — the shape: ``nine_step`` (the default), ``five_step``,
    ``custom`` (your own steps), or ``open`` (an engine picks the next step each
    iteration — maximum variety, not a fixed sequence).
  * ``allowable_modes`` — which of deterministic / hybrid / non_deterministic this
    loop MAY use; ``preferred_modes`` — the WATERFALL order (e.g. deterministic
    first, then hybrid, then non-deterministic), with fallback when a mode fails.
  * ``power`` — small / medium / large / max: a simple front lever that sets how
    much Context Intelligence it pulls, how often it iterates, and how many model
    calls it may make (advanced settings can override on the back end).

The three modes map to the per-node resolution paths (see [[decision_engine.py]]):
deterministic = code only, hybrid = code-first with model escalation/repair,
non_deterministic = model-led.  This module is the parameterized, recursive shell;
the kernel's nine-node run is the concrete executor for the ``nine_step`` framework.
"""

from __future__ import annotations

import hashlib
import json
import weakref
from dataclasses import dataclass, field

from ..loop.kernel import KERNEL_NODES
from .loop_definition import (LoopDefinition, LoopDefinitionError,
                              LoopDefinitionRef, LoopStartRequest)
from .loop_control import (EXIT_CONDITIONS, FRAMEWORKS, LOOP_CONDITIONS,
                           default_loop_condition, normalize_exit_condition)
from .loop_role import (LoopRelationship, LoopRelationshipKind, LoopRole,
                        LoopRoleIdentity)
from .runtime_context import LoopRuntimeContext

MODES = ("deterministic", "hybrid", "non_deterministic")
# Precise internal names for the same three modes (user-facing stays simple):
# embeddings / trained models / seeded search are machine-run CODE, not strictly
# deterministic — the real distinction is whether a semantic LLM call happens.
INTERNAL_MODE_NAMES = {"deterministic": "code_only",
                       "hybrid": "code_with_model_assistance",
                       "non_deterministic": "model_led"}

#: Constitution Article 11 — one protocol, three MEANINGS.  A shared protocol
#: does not erase the distinction, and collapsing them would put a search loop
#: and an execution loop under the same authority:
#:   execution        govern one runnable unit; may not alter a frozen plan
#:   task_semantic    repetition the problem itself requires
#:   search_improvement  propose and compare alternatives — and NEVER accept
#:                       its own candidate (the rule that most needs a name)
LOGICAL_KINDS = ("execution", "task_semantic", "search_improvement")

#: What a loop actually guarantees on replay.  A mode is a policy preset; it
#: is NOT a reproducibility claim, and a seed or a temperature of zero is not
#: a proof of determinism (reproducibility varies by library release,
#: platform and device).  A loop states the guarantee it can keep:
#:   exact                same commands AND identical outputs
#:   event_equivalent     the same controller state rebuilds from the events,
#:                        without re-executing effects
#:   evidence_equivalent  re-running lands inside declared tolerances
#:   non_replayable       explicitly declared; provenance still retained
REPLAY_GUARANTEES = ("exact", "event_equivalent", "evidence_equivalent",
                     "non_replayable")

#: Typed terminal codes.  Richer than a boolean, and richer than a reason
#: string: a consumer can branch on WHY a loop stopped without parsing prose.
TERMINAL_CODES = ("ACCEPTED", "INVALID_SPEC", "POLICY_DENIED", "BLOCKED",
                  "EXHAUSTED", "BUDGET_EXHAUSTED", "DEADLINE_EXCEEDED",
                  "CANCELED", "VERIFICATION_REJECTED", "EFFECT_FAILED",
                  "COMPENSATION_FAILED", "INTERNAL_PROTOCOL_ERROR")

#: the runtime's own stop reasons -> their typed code.  Kept as a closed map
#: so a new reason cannot appear without a code.
_REASON_TO_CODE = {"done": "ACCEPTED", "success_once": "ACCEPTED",
                   "budget": "BUDGET_EXHAUSTED", "cancelled": "CANCELED"}


def terminal_code(reason: str) -> str:
    """The typed terminal code for a stop reason; unknown reasons are an
    internal protocol error rather than a silent pass."""
    return _REASON_TO_CODE.get(reason, "INTERNAL_PROTOCOL_ERROR")

#: kinds forbidden from promoting/accepting their own output.  This is
#: Article 10's "no component approves its own candidate", stated where it is
#: easiest to violate.
SELF_PROMOTION_FORBIDDEN = ("search_improvement",)
POWER_LEVELS = ("light", "standard", "deep", "max")
_POWER_ALIASES = {"small": "light", "medium": "standard", "large": "deep"}
MODEL_THINKING_POWER_LEVELS = ("small", "medium", "high", "max",
                               "specialized")
_FIVE = ("load", "choose", "act", "check", "commit")

# The five core String roles EVERY loop must receive to stay grounded (coverage,
# not an arbitrary prompt count — extra intelligence is retrieved per task).
REQUIRED_STRING_ROLES = ("goal", "state", "work_item", "output_specification",
                         "capability_snapshot")

# The thin, non-negotiable rails around recursive flexibility.
RAILS = (
    "every loop has an input and a declared expected output",
    "every loop has a stop / abstention / budget-exhaustion condition",
    "every iteration is durably recorded",
    "every spawned has a parent and a declared return destination",
    "spawned modes never exceed the parent's delegation authority",
    "recursion depth and spawned count are bounded",
    "every capability search flows through the directory",
    "every semantic model call is visible and budgeted",
    "generated source stays a String until admitted as a Code Node",
    "improvement loops stage candidates, never promote themselves",
    "MAX power raises effort, never permissions",
    "secrets never enter prompt or memory Strings",
    "use a direct Code Node for known bounded work; a loop only when selection, "
    "uncertainty, adaptation, research, or recursive decomposition is needed",
)

# The simple front lever → concrete settings (monotonic).  "How much power?"
# Power raises EFFORT; it never raises permissions.
POWER_SETTINGS = {
    "light":    {"min_intelligence_per_step": 1, "max_iterations": 3,
                 "max_model_calls": 2, "string_pull": 5},
    "standard": {"min_intelligence_per_step": 3, "max_iterations": 6,
                 "max_model_calls": 8, "string_pull": 20},
    "deep":     {"min_intelligence_per_step": 5, "max_iterations": 15,
                 "max_model_calls": 40, "string_pull": 100},
    "max":      {"min_intelligence_per_step": 8, "max_iterations": 60,
                 "max_model_calls": 300, "string_pull": 1000},
}


class LoopError(RuntimeError):
    """A loop misconfiguration or a recursion-depth violation."""


class LoopExecutorUnavailableError(LoopError):
    """The selected Loop mode has no real installed executor."""


@dataclass
class LoopConfig:
    """Everything passed into a Loop at initialization.

    ``loop_condition`` says when another iteration may run. Fixed and custom
    shapes use ``steps_remain``; an open shape uses
    ``chooser_selects_work``. ``exit_condition`` says which successful exit
    the Loop seeks: ``steps_complete`` or ``accepted_success``. Budgets remain
    safety limits, never successful exits.

    """
    framework: str = "nine_step"
    logical_kind: str = "execution"
    replay_guarantee: str = "event_equivalent"
    allowable_modes: tuple[str, ...] = MODES
    preferred_modes: tuple[str, ...] = (
        "deterministic", "hybrid", "non_deterministic")
    delegated_modes: tuple[str, ...] = MODES
    power: str = "medium"
    llm_thinking_power: str = ""
    custom_steps: tuple[str, ...] = ()
    max_depth: int = 3
    loop_condition: str = ""
    exit_condition: str = ""
    success_confidence_min: float = 0.5
    def __post_init__(self):
        if self.framework not in FRAMEWORKS:
            raise ValueError(f"framework must be one of {FRAMEWORKS}")
        self.power = _POWER_ALIASES.get(self.power, self.power)
        if self.power not in POWER_LEVELS:
            raise ValueError(f"power must be one of {POWER_LEVELS} "
                             f"(aliases: {_POWER_ALIASES})")
        for m in (tuple(self.allowable_modes) + tuple(self.preferred_modes)
                  + tuple(self.delegated_modes)):
            if m not in MODES:
                raise ValueError(f"mode {m!r} must be one of {MODES}")
        uses_model = any(mode in self.allowable_modes
                         for mode in ("hybrid", "non_deterministic"))
        if uses_model and not self.llm_thinking_power:
            self.llm_thinking_power = "medium"
        if (self.llm_thinking_power
                and self.llm_thinking_power not in MODEL_THINKING_POWER_LEVELS):
            raise ValueError(
                "llm_thinking_power must be small, medium, high, max, or "
                "specialized")
        if not uses_model and self.llm_thinking_power:
            raise ValueError(
                "llm_thinking_power applies only to a loop that allows "
                "hybrid or non_deterministic mode")
        if self.framework == "custom" and not self.custom_steps:
            raise ValueError("a custom framework needs custom_steps")
        if self.replay_guarantee not in REPLAY_GUARANTEES:
            raise ValueError(
                f"replay_guarantee must be one of {REPLAY_GUARANTEES} — "
                "state the guarantee you can keep; a seed is not a proof of "
                "determinism")
        if self.logical_kind not in LOGICAL_KINDS:
            raise ValueError(
                f"logical_kind must be one of {LOGICAL_KINDS} — one protocol, "
                "three meanings; a loop that will not say which it is cannot "
                "be governed by the rule that applies to it")
        expected_loop_condition = default_loop_condition(self.framework)
        if not self.loop_condition:
            self.loop_condition = expected_loop_condition
        if self.loop_condition not in LOOP_CONDITIONS:
            raise ValueError(
                f"loop_condition must be one of {LOOP_CONDITIONS}")
        if self.loop_condition != expected_loop_condition:
            raise ValueError(
                f"framework {self.framework!r} requires loop_condition "
                f"{expected_loop_condition!r}")
        self.exit_condition = normalize_exit_condition(self.exit_condition)

    @property
    def settings(self) -> dict:
        return POWER_SETTINGS[self.power]


@dataclass
class LoopLedger:
    """The intelligent database of everything that happened — decisions, inputs,
    outputs, modes, spawns, infra calls.  Shared across a loop and its spawned_loops so
    the whole recursive tree has one history."""
    events: list[dict] = field(default_factory=list)
    _counter: int = 0
    _definition_refs: dict[str, dict[str, str]] = field(
        default_factory=dict, repr=False)

    def next_id(self) -> str:
        self._counter += 1
        return f"loop{self._counter}"

    def register_definition(self, loop_id: str,
                            definition_ref: LoopDefinitionRef) -> None:
        """Bind one Loop ID to one immutable definition before events exist."""
        if not isinstance(definition_ref, LoopDefinitionRef):
            raise LoopError("definition_ref must be a LoopDefinitionRef")
        fields = {
            "loop_definition_id": definition_ref.definition_id,
            "loop_definition_version": definition_ref.version,
            "loop_definition_digest": definition_ref.content_digest,
        }
        previous = self._definition_refs.get(loop_id)
        if previous is not None and previous != fields:
            raise LoopError(
                f"Loop {loop_id!r} is already bound to another definition")
        self._definition_refs[loop_id] = fields

    def record(self, **kw) -> None:
        import time
        loop_id = kw.get("loop_id")
        definition_fields = self._definition_refs.get(loop_id, {})
        for name, value in definition_fields.items():
            supplied = kw.get(name, value)
            if supplied != value:
                raise LoopError(
                    f"event definition field {name!r} conflicts with the "
                    f"definition registered for {loop_id!r}")
            kw[name] = value
        self.events.append({"ts": time.time(), **kw})

    def tree(self) -> dict:
        """The loops-of-loops nesting, from recorded spawning links."""
        kids: dict = {}
        for e in self.events:
            if e.get("event") == "spawn":
                kids.setdefault(e["spawning_loop_id"], []).append(e["loop_id"])
        return kids

    def loops(self) -> set:
        return {e["loop_id"] for e in self.events if "loop_id" in e}


@dataclass
class StepOutcome:
    """What resolving one step produced. ``spawn_goal`` triggers a spawned Loop;
    ``failed`` triggers a mode fallback. ``model_calls`` counts physical
    provider attempts, not semantic mode labels."""
    output: str
    mode: str = "deterministic"
    confidence: float = 0.8
    failed: bool = False
    spawn_goal: str = ""
    model_calls: int = 0


@dataclass
class LoopResult:
    loop_id: str
    output: str
    confidence: float
    steps_run: int
    mode_counts: dict[str, int]
    model_calls: int
    spawned: int
    stopped: str = ""                   # "" | budget | depth | done | success_once
    attempts: int = 0                   # bounded mode-specific attempts made
    accepted_successes: int = 0         # iterations that satisfied the completion check
    loop_condition: str = "steps_remain"
    exit_condition: str = "steps_complete"
    loop_definition_id: str = ""
    loop_definition_version: str = ""
    loop_definition_digest: str = ""

    @property
    def terminal_code(self) -> str:
        """The typed terminal code for this result.

        A consumer branches on this rather than parsing ``stopped`` prose or
        collapsing four different outcomes into a boolean.  ACCEPTED covers
        both "done" and the accepted-success stop; a budget stop and a
        cancellation are distinct codes, not shades of failure."""
        return terminal_code(self.stopped)

    @property
    def accepted(self) -> bool:
        """Did the loop REACH ITS OBJECTIVE?  Not "did it return" — the
        distinction Article 5 insists on."""
        return self.terminal_code == "ACCEPTED"


def default_handler(loop: "Loop", step: str, context: dict) -> StepOutcome:
    """Run only the explicit deterministic structural path.

    This helper can exercise control flow for offline checks. It is never a
    substitute for a semantic executor.
    """
    mode = ("deterministic"
            if "deterministic" in loop.config.allowable_modes
            else loop.choose_mode(needs_judgement=True))
    if mode in ("hybrid", "non_deterministic"):
        raise LoopExecutorUnavailableError(
            f"Loop {loop.loop_id} selected {mode!r} for step {step!r}, but "
            "the synthetic structural handler cannot perform semantic work")
    return StepOutcome(output=f"{step}:done", mode=mode, confidence=0.8)


def _default_registered_identity(config: LoopConfig) -> LoopRoleIdentity:
    """Return an exact runnable profile for the established constructor."""
    profile_id = (
        "practitioner.compact_five_step"
        if config.framework == "five_step"
        else "practitioner.reference_nine_step")
    return LoopRoleIdentity(LoopRole.PRACTITIONER, profile_id)


class _LoopMeta(type):
    """Metaclass guard: refuse Loop subclassing before the class exists.

    A plain ``__init_subclass__`` raises after CPython has already
    registered the failed class in ``Loop.__subclasses__()``. The
    metaclass refuses creation entirely, so the subclass list stays
    empty and the one-runtime invariant is airtight.
    """

    def __new__(mcs, name, bases, namespace, **kwargs):
        for base in bases:
            if base.__name__ == "Loop":
                raise TypeError(
                    "Loop is the only operational runtime class and cannot "
                    "be subclassed. Use a versioned LoopNode preset or a "
                    "typed configuration object instead.")
        return super().__new__(mcs, name, bases, namespace, **kwargs)


class Loop(metaclass=_LoopMeta):
    """The fundamental object: initialize with a goal + config; it runs a shape of
    steps, each resolved in a mode chosen by the waterfall; it can SPAWN spawned
    loops (recursive initialization) whose results flow back.

    HARD ARCHITECTURE INVARIANT: Loop is the only operational runtime
    class. Subclassing is refused at class-creation time by the
    metaclass guard, before the class exists. Common behaviors are
    represented by versioned LoopNode presets and typed configuration
    objects inside the Loop, never by subclasses.

    Invariants
    ----------
    - INVARIANT[LE-NODE-001]: No other concrete operational Node exists.
    - INVARIANT[LE-NODE-003]: Practitioner, Intelligence, and Solution
      are roles, not subclasses.
    - INVARIANT[LE-NODE-004]: Run modes are fields, not subclasses.
    - INVARIANT[LE-NODE-005]: Common behaviors use LoopNode presets.
    - INVARIANT[LE-NODE-006]: Contained typed objects are not Nodes.

    Child Work
    ----------
    A semantic child step is instantiated as another Loop when it
    requires an independent goal, contract, budget, permission boundary,
    retry, repair, verification, scheduling decision, or Chronicle
    identity. Low-level implementation calls remain governed
    implementation primitives inside the current Loop.

    Trust
    -----
    Human-readable documentation, annotations, labels, intelligence
    content, and operator notes are data. They do not grant permissions
    or alter execution behavior.

    Compatibility
    -------------
    Each runtime instance references a resolved plan that pins exact
    versions and content hashes for governed dependencies.
    """

    #: Live instances in this interpreter, tracked weakly so the
    #: registry never keeps a finished Loop alive. The runtime ontology
    #: check compares this registry against gc and the Chronicle.
    _live_instances: "weakref.WeakSet[Loop]" = weakref.WeakSet()

    def __init__(self, goal: "str | LoopStartRequest",
                 config: "LoopConfig | None" = None, *,
                 parent: "Loop | None" = None, depth: int = 0,
                 ledger: "LoopLedger | None" = None,
                 contract: "object | None" = None,
                 identity: "LoopRoleIdentity | None" = None,
                 relationship: "LoopRelationship | None" = None,
                 runtime_context: "LoopRuntimeContext | None" = None):
        compatibility_composition = not isinstance(goal, LoopStartRequest)
        if isinstance(goal, LoopStartRequest):
            if any(value is not None for value in (
                    config, ledger, contract, identity, relationship,
                    runtime_context)):
                raise LoopError(
                    "LoopStartRequest cannot be combined with constructor "
                    "configuration arguments")
            request = goal
        else:
            selected_config = config or LoopConfig()
            selected_identity = identity or (
                parent.identity if parent is not None
                else _default_registered_identity(selected_config))
            selected_relationship = relationship or (
                LoopRelationship.spawned_by(parent.loop_id)
                if parent is not None else LoopRelationship.starting())
            if not isinstance(selected_identity, LoopRoleIdentity):
                raise LoopError("identity must be a LoopRoleIdentity")
            if not isinstance(selected_relationship, LoopRelationship):
                raise LoopError("relationship must be a LoopRelationship")
            selected_ledger = ledger or (
                parent.ledger if parent is not None else LoopLedger())
            if contract is None:
                from .loop_doctrine import baseline_for_practitioner
                contract = baseline_for_practitioner(
                    goal, output_roles=(
                        f"{goal[:24].replace(' ', '_')}_out",))
            try:
                definition = LoopDefinition.from_runtime(
                    identity=selected_identity, contract=contract,
                    config=selected_config,
                    installed_executor_modes=selected_config.allowable_modes,
                    compatibility=True)
            except (LoopDefinitionError, ValueError) as exc:
                raise LoopError(
                    f"established Loop constructor could not compose a "
                    f"registered definition: {exc}") from exc
            selected_context = runtime_context or LoopRuntimeContext.compatibility(
                capabilities=definition.required_capabilities,
                permissions=definition.permissions,
                executor_modes=definition.installed_executor_modes)
            try:
                request = LoopStartRequest(
                    goal, definition, selected_relationship,
                    selected_context, selected_ledger)
            except LoopDefinitionError as exc:
                raise LoopError(str(exc)) from exc

        self.goal = request.goal
        Loop._live_instances.add(self)
        self.definition = request.definition
        self.definition_ref = request.definition.ref
        self.config = request.definition.to_loop_config()
        self.parent = parent
        self.identity = request.definition.identity
        self.relationship = request.relationship
        self.runtime_context = request.runtime_context
        self.depth = depth
        self.ledger = request.event_log
        self.loop_id = self.ledger.next_id()
        self.ledger.register_definition(self.loop_id, self.definition_ref)
        self.contract = request.definition.contract
        m = self.contract.execution_mode
        identity_fields = self.identity.to_dict()
        relationship_fields = self.relationship.to_dict()
        self.ledger.record(loop_id=self.loop_id, depth=depth, event="init",
                            goal=self.goal, framework=self.config.framework,
                            logical_kind=self.config.logical_kind,
                            replay_guarantee=self.config.replay_guarantee,
                            power=self.config.power,
                            llm_thinking_power=
                                self.config.llm_thinking_power,
                            loop_condition=self.config.loop_condition,
                            exit_condition=self.config.exit_condition,
                            baseline_goal=self.contract.name,
                            baseline_terminal_mode=m,
                            input_roles=self.contract.input_roles,
                            output_roles=self.contract.output_roles,
                            compatibility_composition=
                                compatibility_composition,
                            **identity_fields,
                            **relationship_fields)
        # the first honest emitter for loop.started — the loop is live.
        self.ledger.record(loop_id=self.loop_id, depth=depth,
                           event="loop.started", goal=self.goal,
                           loop_condition=self.config.loop_condition,
                           exit_condition=self.config.exit_condition)

    # --- the shape ---------------------------------------------------------

    def steps(self) -> tuple:
        f = self.config.framework
        if f == "nine_step":
            return KERNEL_NODES
        if f == "five_step":
            return _FIVE
        if f == "custom":
            return tuple(self.config.custom_steps)
        return ()                       # open: the engine picks each iteration

    # --- the mode waterfall ------------------------------------------------

    def choose_mode(self, *, deterministic_available: bool = True,
                    needs_judgement: bool = False) -> str:
        """Pick the mode for a step: the first PREFERRED mode that is ALLOWABLE and
        feasible.  Deterministic is skipped when no code path exists or the step
        needs open-ended judgement; a deterministic-only loop then does its best
        deterministically (or abstains)."""
        for m in self.config.preferred_modes:
            if m not in self.config.allowable_modes:
                continue
            if m == "deterministic" and (not deterministic_available
                                         or needs_judgement):
                continue
            return m
        allow = [m for m in self.config.preferred_modes
                 if m in self.config.allowable_modes]
        return allow[-1] if allow else "abstain"

    def fallback_mode(self, current: str) -> str:
        """The next mode in the waterfall when ``current`` fails (deterministic →
        hybrid → non_deterministic → abstain)."""
        seq = [m for m in self.config.preferred_modes
               if m in self.config.allowable_modes]
        if current in seq and seq.index(current) + 1 < len(seq):
            return seq[seq.index(current) + 1]
        return "abstain"

    def _require_allowed_outcome_mode(self, outcome: StepOutcome,
                                      step: str) -> None:
        """Refuse a handler that reports a mode this loop cannot use."""
        if outcome.mode not in self.config.allowable_modes:
            self.ledger.record(
                loop_id=self.loop_id, event="failure.detected",
                failure_kind="disallowed_step_mode", step=step,
                reported_mode=outcome.mode,
                allowable_modes=tuple(self.config.allowable_modes))
            raise LoopError(
                f"step {step!r} reported mode {outcome.mode!r}, but loop "
                f"{self.loop_id} allows only {tuple(self.config.allowable_modes)}")
        if outcome.mode not in self.definition.installed_executor_modes:
            self.ledger.record(
                loop_id=self.loop_id, event="failure.detected",
                failure_kind="mode_executor_unavailable", step=step,
                reported_mode=outcome.mode,
                installed_executor_modes=
                    self.definition.installed_executor_modes)
            raise LoopExecutorUnavailableError(
                f"step {step!r} needs mode {outcome.mode!r}, but Loop "
                f"{self.loop_id} has installed executors only for "
                f"{self.definition.installed_executor_modes}")

    # --- recursion: one loop initializes another ---------------------------

    def spawn(self, goal: str, config: "LoopConfig | None" = None, *,
              contract=None, definition: "LoopDefinition | None" = None,
              identity: "LoopRoleIdentity | None" = None,
              relationship: "LoopRelationship | None" = None) -> "Loop":
        """Initialize a spawned Loop whose answer helps this Loop proceed.
        Depth-limited and recorded on the shared ledger.

        Mode is local to each loop. The parent's own ``allowable_modes`` do not
        determine the spawned's mode. A deterministic loop may start a
        non-deterministic loop, and the reverse is also valid.

        ``delegated_modes`` is the separate authority rail. A requested spawned
        config is clamped to the modes the parent may delegate. The spawned's own
        delegation authority is also clamped, so it cannot pass on authority
        that the parent did not grant. Power may differ; effort never grants
        new authority.
        """
        if self.depth + 1 > self.config.max_depth:
            raise LoopError(f"max recursion depth {self.config.max_depth} reached")
        if definition is not None and any(
                value is not None for value in (config, contract, identity)):
            raise LoopError(
                "a spawned LoopDefinition cannot be combined with config, "
                "contract, or identity")
        clamped_from = ()
        delegated_clamped_from = ()
        if config is not None and config is not self.config:
            allowed = tuple(m for m in config.allowable_modes
                            if m in self.config.delegated_modes)
            if not allowed:
                raise LoopError(
                    "spawned modes "
                    f"{tuple(config.allowable_modes)} share nothing with the "
                    "parent's delegation authority "
                    f"{tuple(self.config.delegated_modes)}")
            delegated = tuple(m for m in config.delegated_modes
                              if m in self.config.delegated_modes)
            if set(allowed) != set(config.allowable_modes):
                clamped_from = tuple(config.allowable_modes)
            if set(delegated) != set(config.delegated_modes):
                delegated_clamped_from = tuple(config.delegated_modes)
            if clamped_from or delegated_clamped_from:
                config = LoopConfig(
                    framework=config.framework,
                    logical_kind=config.logical_kind,
                    replay_guarantee=config.replay_guarantee,
                    allowable_modes=allowed,
                    preferred_modes=tuple(m for m in config.preferred_modes
                                          if m in allowed) or allowed,
                    delegated_modes=delegated,
                    power=config.power,
                    llm_thinking_power=(
                        config.llm_thinking_power if any(
                            mode in allowed for mode in
                            ("hybrid", "non_deterministic")) else ""),
                    custom_steps=config.custom_steps,
                    max_depth=config.max_depth,
                    loop_condition=config.loop_condition,
                    exit_condition=config.exit_condition,
                    success_confidence_min=config.success_confidence_min)
        selected_relationship = relationship or LoopRelationship.spawned_by(
            self.loop_id)
        semantic_spawn = (
            selected_relationship.kind is LoopRelationshipKind.SPAWNED_BY)
        if (semantic_spawn
                and selected_relationship.spawned_by_loop_id != self.loop_id):
            raise LoopError(
                "spawned_by_loop_id must name the Loop that initializes it")
        if semantic_spawn:
            # The request exists before the new Loop. Other semantic edges are
            # represented by their own relationship and never emit spawn data.
            self.ledger.record(
                loop_id=self.loop_id, event="spawned_requested",
                goal=str(goal)[:120], depth=self.depth + 1)
        if definition is None:
            selected_identity = identity or self.identity
            selected_config = config or self.config
            if contract is None:
                from .loop_doctrine import baseline_for_practitioner
                contract = baseline_for_practitioner(
                    goal, output_roles=(
                        f"{goal[:24].replace(' ', '_')}_out",))
            try:
                definition = LoopDefinition.from_runtime(
                    identity=selected_identity, contract=contract,
                    config=selected_config,
                    installed_executor_modes=selected_config.allowable_modes,
                    compatibility=True)
            except (LoopDefinitionError, ValueError) as exc:
                raise LoopError(
                    f"spawned Loop could not compose a registered "
                    f"definition: {exc}") from exc
        elif not set(definition.supported_modes) <= set(
                self.config.delegated_modes):
            raise LoopError(
                f"spawned definition modes {definition.supported_modes} "
                "exceed this Loop's delegated_modes "
                f"{self.config.delegated_modes}")

        if self.runtime_context.internal.compatibility_composition:
            spawned_context = LoopRuntimeContext.compatibility(
                capabilities=definition.required_capabilities,
                permissions=definition.permissions,
                executor_modes=definition.installed_executor_modes)
        else:
            try:
                spawned_context = self.runtime_context.derive(
                    capabilities=definition.required_capabilities,
                    permissions=definition.permissions,
                    executor_modes=definition.installed_executor_modes)
            except ValueError as exc:
                raise LoopError(
                    f"spawning context cannot grant the requested Loop: "
                    f"{exc}") from exc
        try:
            start_request = LoopStartRequest(
                goal, definition, selected_relationship,
                spawned_context, self.ledger)
        except LoopDefinitionError as exc:
            raise LoopError(str(exc)) from exc
        spawned = Loop(start_request, parent=self, depth=self.depth + 1)
        if semantic_spawn:
            self.ledger.record(
                loop_id=spawned.loop_id,
                spawning_loop_id=self.loop_id,
                depth=spawned.depth, event="spawn", goal=goal,
                loop_condition=spawned.config.loop_condition,
                exit_condition=spawned.config.exit_condition,
                **spawned.identity.to_dict(),
                **spawned.relationship.to_dict(),
                **({"modes_clamped_from": clamped_from,
                    "modes_clamped_to":
                        tuple(spawned.config.allowable_modes)}
                   if clamped_from else {}),
                **({"delegated_modes_clamped_from": delegated_clamped_from,
                    "delegated_modes_clamped_to":
                        tuple(spawned.config.delegated_modes)}
                   if delegated_clamped_from else {}))
        return spawned

    # --- the structural plan ----------------------------------------------

    def plan(self, *, deterministic_available: bool = True) -> dict:
        """The step→mode plan this loop would run (the concrete executor for
        nine_step is the kernel).  Records each step + mode on the ledger and
        attaches the required string-intelligence pull per step (from power)."""
        st = self.config.settings
        rows = []
        for step in self.steps():
            mode = self.choose_mode(
                deterministic_available=deterministic_available,
                needs_judgement=step in ("decide_next", "assess_prepare",
                                         "choose"))
            rows.append({"step": step, "mode": mode,
                         "required_intelligence": st["min_intelligence_per_step"]})
            self.ledger.record(loop_id=self.loop_id, depth=self.depth,
                               event="step", step=step, mode=mode)
        return {"loop_id": self.loop_id, "framework": self.config.framework,
                "power": self.config.power, "open": self.config.framework == "open",
                "llm_thinking_power": self.config.llm_thinking_power,
                "loop_condition": self.config.loop_condition,
                "exit_condition": self.config.exit_condition,
                "loop_definition_id": self.definition_ref.definition_id,
                "loop_definition_version": self.definition_ref.version,
                "loop_definition_digest":
                    self.definition_ref.content_digest,
                "max_model_calls": st["max_model_calls"], "steps": rows}

    # --- initialization from a serialized Loop Specification String ---------

    @classmethod
    def initialize(cls, spec: dict, *, ledger: "LoopLedger | None" = None,
                   parent: "Loop | None" = None) -> "Loop":
        """Initialize a Loop from a serialized LoopSpec (a String).  Validated
        fail-closed: unknown top-level keys are refused; a spawned spec asking to
        INCREASE permissions is refused.  The spec digest is recorded so every
        run is traceable to the exact specification that configured it."""
        known = {"loop_id", "objective", "inputs", "output_expectation",
                 "loop_template", "resolution", "power", "strings", "models",
                 "spawned_loops", "limits", "conditions"}
        unknown = set(spec) - known
        if unknown:
            raise LoopError(f"unknown LoopSpec keys {sorted(unknown)} refused "
                            "(fail closed — a typo must never silently no-op)")
        objective = spec.get("objective") or {}
        goal = (objective.get("text_or_ref") if isinstance(objective, dict)
                else str(objective)) or spec.get("loop_id", "")
        if not goal:
            raise LoopError("a LoopSpec needs an objective")
        spawned_loops = spec.get("spawned_loops") or {}
        if spawned_loops.get("may_increase_permissions"):
            raise LoopError("spawned_loops.may_increase_permissions=true is refused: "
                            "a spawned Loop never has more permissions than "
                            "its spawning Loop")
        resolution = spec.get("resolution") or {}
        _from_internal = {v: k for k, v in INTERNAL_MODE_NAMES.items()}

        def _modes(names, default):
            if not names:
                return default
            return tuple(_from_internal.get(m, m) for m in names)

        template = spec.get("loop_template") or {}
        limits = spec.get("limits") or {}
        conditions = spec.get("conditions") or {}
        if not isinstance(conditions, dict):
            raise LoopError("conditions must be a mapping")
        unknown_conditions = set(conditions) - {
            "loop_condition", "exit_condition", "success_confidence_min"}
        if unknown_conditions:
            raise LoopError(
                f"unknown conditions keys {sorted(unknown_conditions)} refused")
        current_confidence = conditions.get("success_confidence_min")
        cfg = LoopConfig(
            framework=template.get("framework", "nine_step"),
            logical_kind=template.get("logical_kind", "execution"),
            replay_guarantee=template.get("replay_guarantee",
                                          "event_equivalent"),
            allowable_modes=_modes(resolution.get("allowed_modes"), MODES),
            preferred_modes=_modes(resolution.get("preferred_waterfall"),
                                   ("deterministic", "hybrid",
                                    "non_deterministic")),
            delegated_modes=_modes(spawned_loops.get("allowed_modes"), MODES),
            power=(spec.get("power") or {}).get("profile", "standard"),
            llm_thinking_power=(spec.get("models") or {}).get(
                "thinking_power", ""),
            custom_steps=tuple(template.get("steps", ())),
            max_depth=int(spawned_loops.get("maximum_depth", 3)),
            loop_condition=conditions.get("loop_condition", ""),
            exit_condition=conditions.get("exit_condition", ""),
            success_confidence_min=float(
                current_confidence if current_confidence is not None
                else 0.5))
        digest = hashlib.sha256(
            json.dumps(spec, sort_keys=True, default=str).encode()).hexdigest()
        if parent is not None:
            loop = parent.spawn(goal, cfg)
        else:
            loop = cls(goal, cfg, ledger=ledger)
        loop.spec = dict(spec)
        loop.spec["conditions"] = {
            "loop_condition": cfg.loop_condition,
            "exit_condition": cfg.exit_condition,
            "success_confidence_min": cfg.success_confidence_min,
        }
        loop.spec_digest = digest
        if limits.get("maximum_iterations"):
            loop._max_steps_override = int(limits["maximum_iterations"])
        loop.ledger.record(loop_id=loop.loop_id, event="spec",
                           spec_digest=digest,
                           loop_condition=cfg.loop_condition,
                           exit_condition=cfg.exit_condition,
                           required_string_roles=tuple(
                               (spec.get("strings") or {}).get(
                                   "required_roles", REQUIRED_STRING_ROLES)))
        return loop

    # --- actually RUN the loop (recursive execution) ------------------------
    #
    # ONE canonical execution path: run() drives run_next_iteration(); there is
    # no second executor.  The §12 invariant holds per iteration: at most ONE
    # semantic model call — a semantic→semantic fallback is DEFERRED to the
    # next iteration (recorded as a model boundary), never hidden in-iteration.

    def _ensure_execution(self, max_steps: "int | None") -> dict:
        if getattr(self, "_it", None) is None:
            st = self.config.settings
            limit = (max_steps if max_steps is not None
                     else getattr(self, "_max_steps_override", None)
                     or st["max_iterations"])
            self._it = {"context": {}, "mode_counts": {}, "model_calls": 0,
                        "spawned": 0, "steps_run": 0, "conf_sum": 0.0,
                        "last": "", "stopped": "", "seq": list(self.steps()),
                        "i": 0, "limit": limit, "pending": None,
                        "attempts": 0, "accepted_successes": 0}
        return self._it

    @property
    def is_terminal(self) -> bool:
        it = getattr(self, "_it", None)
        return bool(it and it["stopped"])

    def result(self) -> "LoopResult":
        """The result so far — partial until ``is_terminal`` (an honest partial
        return, never a fabricated completion)."""
        it = self._ensure_execution(None)
        return LoopResult(self.loop_id, it["last"],
                          round(it["conf_sum"] / max(1, it["steps_run"]), 3),
                          it["steps_run"], it["mode_counts"], it["model_calls"],
                          it["spawned"],
                          stopped=it["stopped"],
                          attempts=it["attempts"],
                          accepted_successes=it["accepted_successes"],
                          loop_condition=self.config.loop_condition,
                          exit_condition=self.config.exit_condition,
                          loop_definition_id=
                              self.definition_ref.definition_id,
                          loop_definition_version=
                              self.definition_ref.version,
                          loop_definition_digest=
                              self.definition_ref.content_digest)

    def enable_run_history(self, run_id: str, *, root_dir: str,
                         usage_log: "list | None" = None) -> None:
        """Native RunHistory emission (§9.4): when enabled on a starting Loop,
        its terminal transition projects the shared ledger into a canonical
        RunHistory and persists it under ``root_dir/<run_id>/`` — every run
        lands in the runs store automatically.  ``usage_log`` is the live
        list the handler appends provider usage to (captured by reference)."""
        if self.parent is not None:
            raise LoopError("enable_run_history on the starting Loop only — "
                            "spawned Loops share its history")
        self._run_history = {"run_id": run_id, "root_dir": root_dir,
                           "usage_log": usage_log if usage_log is not None
                           else []}

    def _terminate(self, it: dict, reason: str) -> None:
        """The ONE terminal transition: every stop is recorded on the ledger,
        so closure can be audited (no silent ends, no orphan ambiguity)."""
        it["stopped"] = reason
        self.ledger.record(loop_id=self.loop_id, event="terminal",
                            reason=reason,
                            loop_condition=self.config.loop_condition,
                            exit_condition=self.config.exit_condition,
                            accepted_successes=it.get("accepted_successes", 0),
                            attempts=it.get("attempts", 0))
        # A spawned that reached a terminal state RETURNS to its parent: the
        # return destination is recorded on the parent's own timeline, so
        # spawn and return are both visible (§8.2 — every spawned has a return
        # destination; the closure audit reads the terminal, the parent reads
        # this).
        if (self.parent is not None
                and self.relationship.kind is LoopRelationshipKind.SPAWNED_BY):
            self.ledger.record(loop_id=self.parent.loop_id,
                               event="spawned_return",
                               spawned_loop_id=self.loop_id,
                               depth=self.depth, reason=reason,
                               steps_run=it.get("steps_run", 0))
        cfg = getattr(self, "_run_history", None)
        if cfg is not None:
            from ..core.run_history import RunHistory
            ch = RunHistory.from_ledger(self.ledger.events,
                                       run_id=cfg["run_id"],
                                       usage_log=cfg["usage_log"])
            ch.commit()
            ch.save(cfg["root_dir"])
            self.ledger.record(loop_id=self.loop_id,
                               event="custom",
                               run_history_saved=cfg["run_id"])

    def audit_closure(self) -> dict:
        """§15.2 closure audit: every Loop this Loop spawned must itself have
        reached a recorded terminal state. A spawned-but-never-run Loop is an
        ORPHAN and fails the audit — inspectable, never silent."""
        spawned = [e["loop_id"] for e in self.ledger.events
                   if e.get("event") == "spawn"
                   and e.get("spawning_loop_id") == self.loop_id]
        terminal = {e["loop_id"] for e in self.ledger.events
                    if e.get("event") == "terminal"}
        orphans = [c for c in spawned if c not in terminal]
        return {"loop_id": self.loop_id, "spawned_loops": spawned,
                "orphaned_spawned_loops": orphans,
                "closed": self.is_terminal and not orphans}

    def cancel(self, reason: str = "cancelled") -> None:
        it = self._ensure_execution(None)
        self.ledger.record(loop_id=self.loop_id, event="cancel", reason=reason)
        self._terminate(it, "cancelled")

    def pause(self, reason: str = "") -> dict:
        """Pause between iterations and return a durable, JSON-serializable
        resume token (the LoopPause String)."""
        it = self._ensure_execution(None)
        self.ledger.record(loop_id=self.loop_id, event="pause", reason=reason)
        return {"record_type": "loop_pause/v2", "loop_id": self.loop_id,
                "goal": self.goal, "depth": self.depth, "reason": reason,
                "loop_definition_id": self.definition_ref.definition_id,
                "loop_definition_version": self.definition_ref.version,
                "loop_definition_digest":
                    self.definition_ref.content_digest,
                "loop_definition": self.definition.to_dict(),
                "relationship": self.relationship.to_dict(),
                "runtime_context": {
                    "available_capabilities": sorted(
                        self.runtime_context.available_capabilities),
                    "permissions": list(
                        self.runtime_context.internal.permissions),
                    "executor_modes": list(
                        self.runtime_context.internal.executor_modes),
                    "compatibility_composition":
                        self.runtime_context.internal.compatibility_composition,
                },
                "config": {"framework": self.config.framework,
                           "logical_kind": self.config.logical_kind,
                           "replay_guarantee": self.config.replay_guarantee,
                           "allowable_modes": list(self.config.allowable_modes),
                           "preferred_modes": list(self.config.preferred_modes),
                           "delegated_modes": list(self.config.delegated_modes),
                           "power": self.config.power,
                           "llm_thinking_power":
                               self.config.llm_thinking_power,
                           "custom_steps": list(self.config.custom_steps),
                           "max_depth": self.config.max_depth,
                           "loop_condition": self.config.loop_condition,
                           "exit_condition": self.config.exit_condition,
                           "success_confidence_min":
                               self.config.success_confidence_min},
                "iteration_state": {k: (dict(v) if isinstance(v, dict)
                                        else list(v) if isinstance(v, list)
                                        else v)
                                    for k, v in it.items()},
                "spec_digest": getattr(self, "spec_digest", "")}

    @classmethod
    def resume(cls, token: dict, *,
               ledger: "LoopLedger | None" = None,
               runtime_context: "LoopRuntimeContext | None" = None) -> "Loop":
        """Reconstruct a paused loop from its resume token and continue exactly
        where it stopped (durable resumption)."""
        version = token.get("record_type")
        if version != "loop_pause/v2":
            raise LoopError("not a supported loop_pause resume token")
        c = token["config"]
        current_keys = {
            "framework", "logical_kind", "replay_guarantee",
            "allowable_modes", "preferred_modes", "delegated_modes",
            "power", "llm_thinking_power", "custom_steps", "max_depth",
            "loop_condition", "exit_condition", "success_confidence_min",
        }
        unknown = set(c) - current_keys
        if unknown:
            raise LoopError(
                f"unknown pause config keys {sorted(unknown)} refused")
        if not c.get("loop_condition") or not c.get("exit_condition"):
            raise LoopError(
                "loop_pause/v2 requires loop_condition and exit_condition")
        definition_record = token.get("loop_definition")
        if not isinstance(definition_record, dict):
            raise LoopError("loop_pause/v2 requires a LoopDefinition")
        try:
            definition = LoopDefinition.from_dict(definition_record)
        except LoopDefinitionError as exc:
            raise LoopError(f"paused LoopDefinition is invalid: {exc}") from exc
        expected_config = definition.to_loop_config()
        supplied_config = LoopConfig(
            framework=c["framework"],
            logical_kind=c.get("logical_kind", "execution"),
            replay_guarantee=c.get("replay_guarantee", "event_equivalent"),
            allowable_modes=tuple(c["allowable_modes"]),
            preferred_modes=tuple(c["preferred_modes"]),
            delegated_modes=tuple(c.get("delegated_modes", MODES)),
            power=c["power"],
            llm_thinking_power=c.get("llm_thinking_power", ""),
            custom_steps=tuple(c["custom_steps"]),
            max_depth=c["max_depth"],
            loop_condition=c.get("loop_condition", ""),
            exit_condition=c.get("exit_condition", ""),
            success_confidence_min=float(c.get(
                "success_confidence_min", 0.5)))
        if supplied_config != expected_config:
            raise LoopError(
                "paused config conflicts with its immutable LoopDefinition")
        context_summary = token.get("runtime_context") or {}
        if runtime_context is None:
            if not context_summary.get("compatibility_composition"):
                raise LoopError(
                    "resuming a strict Loop requires its LoopRuntimeContext")
            runtime_context = LoopRuntimeContext.compatibility(
                capabilities=tuple(
                    context_summary.get("available_capabilities", ())),
                permissions=tuple(context_summary.get("permissions", ())),
                executor_modes=tuple(
                    context_summary.get("executor_modes", ())))
        relationship_record = token.get("relationship")
        try:
            selected_relationship = LoopRelationship.from_dict(
                relationship_record)
            request = LoopStartRequest(
                token["goal"], definition, selected_relationship,
                runtime_context, ledger or LoopLedger())
            loop = cls(request)
        except (ValueError, LoopDefinitionError) as exc:
            raise LoopError(f"cannot resume Loop: {exc}") from exc
        loop._it = {k: (dict(v) if isinstance(v, dict) else v)
                    for k, v in token["iteration_state"].items()}
        loop._it["seq"] = list(token["iteration_state"]["seq"])
        loop.ledger.record(loop_id=loop.loop_id, event="resume",
                           resumed_from=token["loop_id"],
                           at_step=loop._it["steps_run"],
                           loop_condition=loop.config.loop_condition,
                           exit_condition=loop.config.exit_condition)
        return loop

    def run_next_iteration(self, *, handler=None, chooser=None,
                           max_steps: "int | None" = None) -> dict:
        """Run exactly ONE bounded iteration; returns the LoopIterationRecord.
        At most one semantic model call happens per iteration (§12) — a
        semantic fallback is deferred to the NEXT iteration as a visible model
        boundary, never hidden inside this one."""
        uses_structural_handler = handler is None
        handler = handler or default_handler
        it = self._ensure_execution(max_steps)
        st = self.config.settings
        rec = {"record_type": "loop_iteration/v2", "loop_id": self.loop_id,
               "iteration": it["steps_run"] + 1, "semantic_calls": 0,
               "loop_condition": self.config.loop_condition,
               "exit_condition": self.config.exit_condition,
               "loop_definition_id": self.definition_ref.definition_id,
               "loop_definition_version": self.definition_ref.version,
               "loop_definition_digest":
                   self.definition_ref.content_digest,
               "terminal": False}
        if it["stopped"]:
            rec.update(terminal=True, note=f"already terminal: {it['stopped']}")
            return rec
        if it["steps_run"] >= it["limit"]:
            self._terminate(it, "budget")
            rec.update(terminal=True, note="iteration limit reached")
            return rec
        # --- pick the step (a deferred semantic fallback takes precedence) ---
        if it["pending"] is not None:
            step, forced_mode = it["pending"]
            it["pending"] = None
            if uses_structural_handler:
                raise LoopExecutorUnavailableError(
                    f"Loop {self.loop_id} needs a real {forced_mode} executor "
                    f"to retry step {step!r}")
            it["context"]["requested_mode"] = forced_mode
            try:
                outcome = handler(self, step, it["context"])
            finally:
                it["context"].pop("requested_mode", None)
            self._require_allowed_outcome_mode(outcome, step)
            self.ledger.record(loop_id=self.loop_id, event="fallback",
                              step=step, from_mode="deferred",
                              to_mode=forced_mode)
        else:
            if self.config.framework == "open":
                step = chooser(sorted(it["context"])) if chooser else None
                if step in (None, "finish"):
                    self._terminate(it, "done")
                    rec.update(terminal=True, note="chooser finished")
                    return rec
            else:
                if it["i"] >= len(it["seq"]):
                    # END OF THE STEP SEQUENCE. Under `steps_complete` that is
                    # the goal and the loop is done. Under `accepted_success` it
                    # is NOT: the exit condition is "one iteration succeeded",
                    # so finishing the steps without an accepted success means
                    # going round again, not stopping.
                    #
                    # Terminating here regardless made `success_once` able to
                    # stop with ZERO successes — the opposite of what it says —
                    # and a retry-until-it-works loop silently ran exactly one
                    # attempt. Found by writing the example for it.
                    if (self.config.exit_condition == "accepted_success"
                            and it["accepted_successes"] < 1):
                        it["i"] = 0                  # another pass
                        self.ledger.record(
                            loop_id=self.loop_id, depth=self.depth,
                            event="iteration_started",
                            iteration=it["attempts"] + 1,
                            note="no accepted success yet; accepted_success "
                                 "requires another attempt")
                    else:
                        self._terminate(it, "done")
                        rec.update(terminal=True, note="sequence complete")
                        return rec
                step, it["i"] = it["seq"][it["i"]], it["i"] + 1
            # the iteration START, before the handler runs: "what did this
            # loop attempt" and "what did it complete" are different
            # questions, and a completion-only event answers one of them.
            self.ledger.record(loop_id=self.loop_id, event="iteration_started",
                               step=step, iteration=it["steps_run"] + 1)
            outcome = handler(self, step, it["context"])
            self._require_allowed_outcome_mode(outcome, step)
            attempts = 0
            while outcome.failed and attempts < 3:  # the mode fallback, live
                fb = self.fallback_mode(outcome.mode)
                if fb == "abstain":
                    break
                if fb in ("hybrid", "non_deterministic"):
                    # A semantic retry needs a real executor. It never
                    # completes through a fabricated recovery outcome.
                    it["pending"] = (step, fb)
                    self.ledger.record(loop_id=self.loop_id,
                                       event="model_boundary_deferred",
                                       step=step, from_mode=outcome.mode,
                                       to_mode=fb)
                    rec.update(step=step, mode=outcome.mode,
                               deferred_fallback=fb)
                    it["steps_run"] += 1
                    return rec
                self.ledger.record(loop_id=self.loop_id, event="fallback",
                                   step=step, from_mode=outcome.mode,
                                   to_mode=fb)
                outcome = StepOutcome(output=f"{step}:recovered:{fb}", mode=fb,
                                      confidence=0.6)
                self._require_allowed_outcome_mode(outcome, step)
                attempts += 1
        if outcome.spawn_goal and self.depth + 1 <= self.config.max_depth:
            spawned = self.spawn(outcome.spawn_goal)   # loops initialize loops
            cres = spawned.run(handler=handler, chooser=chooser)
            it["context"][f"{step}:spawned"] = cres.output
            it["spawned"] += 1 + cres.spawned
            outcome = StepOutcome(output=f"{step}:used({cres.output})",
                                  mode=outcome.mode,
                                  confidence=min(outcome.confidence,
                                                 cres.confidence))
        physical_model_calls = max(0, int(outcome.model_calls))
        if physical_model_calls:
            if physical_model_calls > 1:
                raise LoopError(
                    "one loop iteration may report at most one physical "
                    "model call")
            it["model_calls"] += physical_model_calls
            rec["semantic_calls"] = physical_model_calls
            if it["model_calls"] > st["max_model_calls"]:
                self.ledger.record(loop_id=self.loop_id, event="budget_stop",
                                   model_calls=it["model_calls"])
                self._terminate(it, "budget")
                rec.update(terminal=True, note="model-call budget spent")
                return rec
        it["mode_counts"][outcome.mode] = (
            it["mode_counts"].get(outcome.mode, 0) + 1)
        it["context"][step] = outcome.output
        it["conf_sum"] += outcome.confidence
        it["last"] = outcome.output
        it["steps_run"] += 1
        # --- acceptance-vs-attempt (Universal Loop Standard §7): every step is
        # one attempt; an accepted success is an attempt that did NOT fail and
        # cleared the confidence bar. ``accepted_success`` exits on the first.
        it["attempts"] += 1
        accepted = (not outcome.failed
                    and outcome.confidence >= self.config.success_confidence_min)
        if accepted:
            it["accepted_successes"] += 1
        self.ledger.record(loop_id=self.loop_id, depth=self.depth,
                            event="run_step", step=step, mode=outcome.mode,
                            output=outcome.output,
                            confidence=outcome.confidence,
                            accepted=accepted,
                            attempts=it["attempts"],
                            accepted_successes=it["accepted_successes"])
        rec.update(step=step, mode=outcome.mode, output=outcome.output,
                   confidence=outcome.confidence, accepted=accepted)
        if (self.config.exit_condition == "accepted_success" and
                it["accepted_successes"] >= 1):
            self._terminate(it, "success_once")
            rec.update(terminal=True, note="first accepted success reached")
            return rec
        return rec

    def run(self, *, handler=None, chooser=None,
            max_steps: "int | None" = None) -> "LoopResult":
        """Run to completion — the same canonical path, iterated: each step is
        resolved by the ``handler`` (pluggable — the default is deterministic;
        real handlers delegate to the kernel, a code node, or the LLM
        pipeline).  Everything is tracked on the shared ledger:

          * a FAILED step falls back along the mode waterfall (deterministic →
            hybrid → non_deterministic → abstain), each attempt recorded; a
            semantic→semantic fallback is deferred to the next iteration (§12);
          * an outcome with ``spawn_goal`` recursively initializes a spawned Loop,
            runs it, and feeds its answer back into this loop's context;
          * hybrid / non-deterministic steps consume the POWER lever's model-call
            budget — the loop stops honestly when the budget is spent;
          * an ``open`` loop asks ``chooser(context_keys)`` for the next step each
            iteration until it returns "finish" (or the iteration cap)."""
        self._ensure_execution(max_steps)
        while not self.is_terminal:
            rec = self.run_next_iteration(handler=handler, chooser=chooser,
                                          max_steps=max_steps)
            if rec.get("terminal"):
                break
        return self.result()

    # canonical alias for the public mental model (§19)
    run_to_completion = run


def suggested_templates() -> list:
    """A few starting-point loop configs as searchable resources — the "nice
    middle ground" front lever plus framework presets."""
    from ..core.store_serve import StoreRecord
    presets = [
        ("balanced_nine", "nine_step", "medium",
         ("deterministic", "hybrid", "non_deterministic")),
        ("cheap_deterministic", "nine_step", "small", ("deterministic", "hybrid")),
        ("overnight_max", "open", "max",
         ("deterministic", "hybrid", "non_deterministic")),
        ("offline_only", "five_step", "small", ("deterministic",)),
    ]
    return [StoreRecord(
        record_id=f"looptmpl.{name}", kind="strategy",
        title=f"Loop template: {name} ({fw}, {power})",
        body={"framework": fw, "power": power, "preferred_modes": list(pref),
              "loop_condition": default_loop_condition(fw),
              "exit_condition": "steps_complete", "role": "loop_template"},
        tags=("loop_template", fw, power), tier="core")
            for name, fw, power, pref in presets]


# ---------------------------------------------------------------------------
# Self-test — deterministic, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name, ok, detail=""):
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    # 0. the one-runtime invariant is mechanically enforced: subclassing
    #    the canonical Loop class is refused at class-creation time.
    try:
        class _SneakyNode(Loop):                                # noqa: F841
            pass
        check("loop_cannot_be_subclassed", False)
    except TypeError:
        check("loop_cannot_be_subclassed", True)

    # 1. a Loop is a parameterized CLASS: initialize with a goal + config.
    lp = Loop("solve churn", LoopConfig(framework="nine_step", power="medium"))
    check("a_loop_is_an_initializable_parameterized_class",
          lp.goal == "solve churn" and lp.config.framework == "nine_step"
          and lp.loop_id.startswith("loop")
          and lp.relationship == LoopRelationship.starting()
          and lp.identity.role is LoopRole.PRACTITIONER
          and lp.identity.profile_id == "practitioner.reference_nine_step"
          and lp.definition_ref.content_digest,
          "every Loop receives separate role identity and relationship")

    relationship_shapes = [
        LoopRelationship.starting().to_dict(),
        LoopRelationship.spawned_by("loop-a").to_dict(),
        LoopRelationship.queried_by("loop-b").to_dict(),
        LoopRelationship.retrieved_by("loop-c").to_dict(),
        LoopRelationship.connected_from(("loop-d", "loop-e")).to_dict()]
    check("all_relationship_kinds_emit_only_their_matching_typed_fields",
          all(LoopRelationship.from_dict(value).to_dict() == value
              for value in relationship_shapes)
          and all("relationship_kind" in value for value in relationship_shapes))

    # 2. the framework sets the shape: nine / five / custom / open.
    nine = Loop("g", LoopConfig(framework="nine_step")).steps()
    five = Loop("g", LoopConfig(framework="five_step")).steps()
    cust = Loop("g", LoopConfig(framework="custom",
                                custom_steps=("orient", "research", "research",
                                              "decide", "build"))).steps()
    openn = Loop("g", LoopConfig(framework="open")).steps()
    check("the_framework_sets_the_loop_shape",
          nine == KERNEL_NODES and len(five) == 5
          and cust == ("orient", "research", "research", "decide", "build")
          and openn == (),
          "custom can reorder/repeat (orient→research→research→decide→build); "
          "open has no fixed sequence")

    # 3. the mode WATERFALL: deterministic-first; a deterministic-only loop never
    # goes non-deterministic.
    det_only = Loop("g", LoopConfig(allowable_modes=("deterministic",)))
    balanced = Loop("g", LoopConfig())
    check("mode_waterfall_respects_allowable_and_preferred",
          balanced.choose_mode() == "deterministic"
          and det_only.choose_mode(needs_judgement=True) == "deterministic"
          and balanced.choose_mode(deterministic_available=False) == "hybrid",
          "deterministic first; det-only stays deterministic; no code → hybrid")

    disallowed_mode = Loop(
        "mode guard",
        LoopConfig(framework="custom", custom_steps=("act",),
                   allowable_modes=("deterministic",),
                   preferred_modes=("deterministic",)))
    disallowed_refused = False
    try:
        disallowed_mode.run(handler=lambda loop, step, context: StepOutcome(
            output="mislabelled", mode="hybrid"))
    except LoopError:
        disallowed_refused = True
    check("handler_cannot_report_a_mode_the_loop_does_not_allow",
          disallowed_refused and any(
              event.get("failure_kind") == "disallowed_step_mode"
              for event in disallowed_mode.ledger.events),
          "reported modes are enforced, not trusted as labels")

    # 4. FALLBACK moves along the waterfall: deterministic → hybrid → non_det.
    check("mode_fallback_walks_the_waterfall",
          balanced.fallback_mode("deterministic") == "hybrid"
          and balanced.fallback_mode("hybrid") == "non_deterministic"
          and balanced.fallback_mode("non_deterministic") == "abstain",
          "when a mode fails, fall to the next allowable mode")

    # 5. RECURSION — a loop initializes another loop (loops of loops), tracked and
    # depth-limited.
    root = Loop("build a model", LoopConfig(max_depth=2))
    research = root.spawn("research the domain")
    nested_spawned_loop = research.spawn("research point-in-time features")
    deep_blocked = False
    try:
        nested_spawned_loop.spawn("too deep")
    except LoopError:
        deep_blocked = True
    check("loops_recursively_initialize_loops",
          research.depth == 1 and nested_spawned_loop.depth == 2 and deep_blocked
          and research.parent is root,
          "one loop spawns another whose answer helps it proceed; depth-limited")

    improve_root = Loop("review history", LoopConfig(
        allowable_modes=("deterministic",),
        preferred_modes=("deterministic",), max_depth=2,
        delegated_modes=("deterministic",),
        logical_kind="search_improvement",
        replay_guarantee="evidence_equivalent"))
    improve_spawned = improve_root.spawn("audit context", LoopConfig(
        framework="custom", custom_steps=("audit",),
        allowable_modes=("deterministic", "hybrid"),
        preferred_modes=("deterministic", "hybrid"), max_depth=2,
        logical_kind="search_improvement",
        replay_guarantee="evidence_equivalent"))
    check("spawn_clamp_preserves_improvement_identity_and_replay_policy",
          improve_spawned.config.allowable_modes == ("deterministic",)
          and improve_spawned.config.logical_kind == "search_improvement"
          and improve_spawned.config.replay_guarantee == "evidence_equivalent")

    det_parent = Loop("deterministic orchestration", LoopConfig(
        allowable_modes=("deterministic",),
        preferred_modes=("deterministic",), max_depth=2))
    model_spawned = det_parent.spawn("open-ended research", LoopConfig(
        framework="custom", custom_steps=("research",),
        allowable_modes=("non_deterministic",),
        preferred_modes=("non_deterministic",), max_depth=2))
    model_parent = Loop("model-led planning", LoopConfig(
        allowable_modes=("non_deterministic",),
        preferred_modes=("non_deterministic",), max_depth=2))
    code_spawned = model_parent.spawn("validate the proposal", LoopConfig(
        framework="custom", custom_steps=("validate",),
        allowable_modes=("deterministic",),
        preferred_modes=("deterministic",), max_depth=2))
    check("parent_and_spawned_modes_are_independent_under_delegation_policy",
          model_spawned.config.allowable_modes == ("non_deterministic",)
          and code_spawned.config.allowable_modes == ("deterministic",)
          and model_spawned.parent is det_parent and code_spawned.parent is model_parent,
          "deterministic starts model-led; model-led starts deterministic")

    # 6. POWER is a simple lever with monotonic concrete settings.
    s = {p: POWER_SETTINGS[p]["max_model_calls"] for p in POWER_LEVELS}
    i = {p: POWER_SETTINGS[p]["min_intelligence_per_step"] for p in POWER_LEVELS}
    check("power_lever_sets_monotonic_settings",
          s["light"] < s["standard"] < s["deep"] < s["max"]
          and i["light"] < i["standard"] < i["deep"] < i["max"],
          "light to max scales model calls and required Context Intelligence")

    invalid_thinking_power = False
    try:
        LoopConfig(
            allowable_modes=("deterministic",),
            llm_thinking_power="high")
    except ValueError:
        invalid_thinking_power = True
    model_config = LoopConfig(
        allowable_modes=("hybrid",), preferred_modes=("hybrid",),
        llm_thinking_power="specialized")
    check("model_thinking_power_applies_only_to_model_using_loops",
          invalid_thinking_power
          and LoopConfig().llm_thinking_power == "medium"
          and model_config.llm_thinking_power == "specialized",
          "deterministic-only refuses it; model-using loops default or declare it")

    # 6b. spec refinements: legacy power names alias; the three modes have
    # precise internal names; five core String roles + the rails are declared.
    check("spec_refinements_power_aliases_modes_roles_rails",
          LoopConfig(power="large").power == "deep"
          and LoopConfig(power="medium").power == "standard"
          and INTERNAL_MODE_NAMES["hybrid"] == "code_with_model_assistance"
          and len(REQUIRED_STRING_ROLES) == 5
          and "capability_snapshot" in REQUIRED_STRING_ROLES
          and len(RAILS) >= 10,
          "light/standard/deep/max (old names alias); code_only / "
          "code_with_model_assistance / model_led; 5 grounding roles; the rails")

    # 7. the LEDGER is the intelligent database — the whole recursive tree's
    # history (init, spawn, steps), with the nesting recoverable.
    tree = root.ledger.tree()
    check("the_ledger_tracks_the_whole_recursive_history",
          root.loop_id in tree and research.loop_id in tree[root.loop_id]
          and research.loop_id in tree and len(root.ledger.loops()) == 3,
          "spawns + steps recorded on one shared ledger; loops-of-loops tree")

    # 8. plan() attaches required Context Intelligence per step.
    plan = Loop("g", LoopConfig(power="large")).plan()
    check("plan_requires_context_intelligence_per_step",
          plan["steps"]
          and all(r["required_intelligence"] == 5 for r in plan["steps"])
          and plan["max_model_calls"] == 40,
          "each step pulls at least N string prompts (from the power lever)")

    # 9. loop templates are searchable resources (the front-lever presets).
    from ..core.store_serve import SolverStore
    store = SolverStore(core_records=suggested_templates())
    hit = store.search("offline deterministic only loop", kind="strategy")
    check("loop_templates_are_searchable",
          hit["hits"] and any("looptmpl." in h["record_id"] for h in hit["hits"]),
          "starting-point loop configs flow through the one search DAG")

    # 10. a loop actually RUNS: nine steps execute deterministically end-to-end,
    # everything on the ledger.
    r1 = Loop("run it", LoopConfig(power="large")).run()
    check("a_loop_actually_runs_end_to_end",
          r1.steps_run == 10 and r1.stopped == "done"
          and r1.mode_counts.get("deterministic", 0) >= 6 and r1.output,
          f"{r1.steps_run} steps, modes {r1.mode_counts} (medium power caps at 6 "
          "iterations — the lever binds, so ten steps need 'large')")

    # 11. RECURSIVE EXECUTION: a research step spawns and runs another Loop,
    # then uses the returned answer.
    def research_handler(loop, step, context):
        if step == "research" and loop.depth == 0 and f"{step}:spawned" not in context:
            return StepOutcome(output=f"{step}:needs-spawned", mode="deterministic",
                               spawn_goal="research the domain")
        return default_handler(loop, step, context)
    parent = Loop("build model",
                  LoopConfig(framework="custom",
                             custom_steps=("orient", "research", "decide",
                                           "build")))
    r2 = parent.run(handler=research_handler)
    check("loops_recursively_execute_loops",
          r2.spawned >= 1 and "used(" in " ".join(
              e.get("output", "") for e in parent.ledger.events
              if e.get("event") == "run_step" and e.get("loop_id") == parent.loop_id)
          and r2.steps_run == 4,
          f"spawned and ran a Loop; its answer returned ({r2.spawned} spawned)")

    # 12. the MODE FALLBACK runs live: a failed deterministic step recovers on the
    # next mode in the waterfall, recorded.
    def flaky_handler(loop, step, context):
        requested_mode = context.get("requested_mode")
        if step == "act" and requested_mode:
            return StepOutcome(
                output=f"act:recovered:{requested_mode}",
                mode=requested_mode, confidence=0.8)
        if step == "act":
            return StepOutcome(output="act:error", mode="deterministic",
                               failed=True)
        return default_handler(loop, step, context)
    lp3 = Loop("flaky", LoopConfig(framework="custom",
                                   custom_steps=("orient", "act", "verify")))
    lp3.run(handler=flaky_handler)
    fell = [e for e in lp3.ledger.events if e.get("event") == "fallback"]
    deferred_fallbacks = [
        e for e in lp3.ledger.events
        if e.get("event") == "model_boundary_deferred"]
    check("mode_fallback_runs_live",
          fell and deferred_fallbacks
          and deferred_fallbacks[0]["from_mode"] == "deterministic"
          and deferred_fallbacks[0]["to_mode"] == "hybrid"
          and fell[0]["to_mode"] == "hybrid"
          and any("recovered:hybrid" in e.get("output", "")
                  for e in lp3.ledger.events if e.get("event") == "run_step"),
          "deterministic failed → recovered on hybrid, on the ledger")

    # 13. the POWER budget stops a model-heavy loop honestly.
    heavy = Loop("model heavy",
                 LoopConfig(allowable_modes=("non_deterministic",),
                            preferred_modes=("non_deterministic",),
                            power="small"))
    r4 = heavy.run(handler=lambda loop, step, context: StepOutcome(
        output="model attempt", mode="non_deterministic", model_calls=1))
    check("power_budget_stops_a_model_heavy_loop",
          r4.stopped == "budget" and r4.model_calls == 3 and r4.steps_run <= 2,
          f"small power = 2 model calls; stopped at the 3rd ({r4.steps_run} steps)")

    # 14. an OPEN loop runs via a chooser until it says finish — no fixed order.
    def chooser(done):
        for s in ("research", "research2", "build", "finish"):
            if s not in done:
                return s
        return "finish"
    r5 = Loop("open run", LoopConfig(framework="open")).run(chooser=chooser)
    check("an_open_loop_runs_engine_chosen_steps",
          r5.steps_run == 3 and r5.stopped == "done",
          "research → research2 → build → finish, chosen live, no fixed sequence")

    # 15. Loop.initialize(spec): a serialized LoopSpec String configures the
    # loop; unknown keys and permission increases are refused fail-closed.
    spec = {"objective": {"text_or_ref": "predict churn"},
            "loop_template": {"framework": "custom",
                              "steps": ["orient", "research", "decide", "act"]},
            "resolution": {"allowed_modes": ["code_only", "hybrid"],
                           "preferred_waterfall": ["code_only", "hybrid"]},
            "power": {"profile": "standard"},
            "limits": {"maximum_iterations": 10},
            "conditions": {"loop_condition": "steps_remain",
                           "exit_condition": "steps_complete"},
            "spawned_loops": {"maximum_depth": 2}}
    lp15 = Loop.initialize(spec)
    bad_key = bad_perm = False
    try:
        Loop.initialize({"objective": {"text_or_ref": "x"}, "powerr": {}})
    except LoopError:
        bad_key = True
    try:
        Loop.initialize({"objective": {"text_or_ref": "x"},
                         "spawned_loops": {"may_increase_permissions": True}})
    except LoopError:
        bad_perm = True
    check("initialize_from_serialized_loopspec_fail_closed",
          lp15.goal == "predict churn"
          and lp15.config.allowable_modes == ("deterministic", "hybrid")
          and lp15.config.custom_steps == ("orient", "research", "decide", "act")
          and lp15.config.loop_condition == "steps_remain"
          and lp15.config.exit_condition == "steps_complete"
          and len(lp15.spec_digest) == 64 and bad_key and bad_perm,
          "internal mode names accepted; unknown keys refused; "
          "may_increase_permissions refused; spec digest recorded")

    # 16. bounded iteration: run_next_iteration + is_terminal + partial result.
    lp16 = Loop("iterate", LoopConfig(framework="five_step", power="large"))
    first = lp16.run_next_iteration()
    partial = lp16.result()
    while not lp16.is_terminal:
        lp16.run_next_iteration()
    final = lp16.result()
    check("bounded_iteration_with_partial_results",
          first["iteration"] == 1 and first["step"] == "load"
          and partial.steps_run == 1 and not partial.stopped
          and final.steps_run == 5 and final.stopped == "done"
          and lp16.is_terminal,
          "one iteration at a time; result() is honestly partial until terminal")

    # 17. pause → serializable token → resume continues exactly where it stopped.
    lp17 = Loop("pausable", LoopConfig(
        framework="five_step", power="large",
        delegated_modes=("deterministic", "hybrid"),
        logical_kind="search_improvement",
        replay_guarantee="evidence_equivalent"))
    lp17.run_next_iteration()
    lp17.run_next_iteration()
    token = json.loads(json.dumps(lp17.pause("checkpoint")))   # survives JSON
    lp17b = Loop.resume(token)
    while not lp17b.is_terminal:
        lp17b.run_next_iteration()
    r17 = lp17b.result()
    check("pause_resume_continues_exactly",
          token["record_type"] == "loop_pause/v2"
          and token["config"]["loop_condition"] == "steps_remain"
          and token["config"]["exit_condition"] == "steps_complete"
          and r17.steps_run == 5 and r17.stopped == "done"
          and lp17b.config.logical_kind == "search_improvement"
          and lp17b.config.replay_guarantee == "evidence_equivalent"
          and lp17b.config.delegated_modes == ("deterministic", "hybrid")
          and any(e.get("event") == "resume" for e in lp17b.ledger.events),
          "2 steps before pause + 3 after resume = the same 5-step loop")

    # 18. §12: at most ONE semantic call per iteration — a semantic→semantic
    # fallback is DEFERRED to the next iteration as a visible model boundary.
    def semantic_flaky(loop, step, context):
        if step == "act" and context.get("requested_mode"):
            return StepOutcome(
                output="act:model-recovered",
                mode=context["requested_mode"], model_calls=1)
        if step == "act" and "act" not in context:
            return StepOutcome(output="act:model-error", mode="hybrid",
                               failed=True, model_calls=1)
        return default_handler(loop, step, context)
    lp18 = Loop("one call per iteration",
                LoopConfig(framework="custom", custom_steps=("orient", "act"),
                           power="large"))
    recs = []
    while not lp18.is_terminal:
        recs.append(lp18.run_next_iteration(handler=semantic_flaky))
    deferred = [e for e in lp18.ledger.events
                if e.get("event") == "model_boundary_deferred"]
    check("one_semantic_call_per_iteration_deferral",
          deferred and deferred[0]["from_mode"] == "hybrid"
          and deferred[0]["to_mode"] == "non_deterministic"
          and all(r.get("semantic_calls", 0) <= 1 for r in recs)
          and any(r.get("deferred_fallback") for r in recs),
          "hybrid failed → non_deterministic retry happened in the NEXT "
          "iteration, recorded as a model boundary")

    # 19. cancellation is terminal and recorded.
    lp19 = Loop("cancel me", LoopConfig(framework="five_step"))
    lp19.run_next_iteration()
    lp19.cancel("operator stop")
    check("cancellation_is_terminal_and_recorded",
          lp19.is_terminal and lp19.result().stopped == "cancelled"
          and any(e.get("event") == "cancel" for e in lp19.ledger.events))

    # 20. Loop is the only runtime class.
    check("loop_is_the_only_runtime_class",
          Loop.__name__ == "Loop", "one universal Loop class")

    # 21. NATIVE RUN_HISTORY EMISSION: a Starting Loop with enable_run_history
    # persists its canonical history automatically at terminal; spawned_loops
    # refuse (they share the Starting Loop's history).
    import tempfile as _tf
    _croot = _tf.mkdtemp(prefix="run_history_native_")
    lp21 = Loop("native emit", LoopConfig(framework="five_step",
                                          power="deep"))
    lp21.enable_run_history("native-test-run", root_dir=_croot)
    spawned_refused = False
    try:
        lp21.spawn("spawned").enable_run_history("nope", root_dir=_croot)
    except LoopError:
        spawned_refused = True
    lp21.run()
    from ..core.run_history import RunHistory as _Ch
    back = _Ch.load(_croot, "native-test-run")
    check("starting_loop_emits_its_run_history_natively_at_terminal",
          back.verify_chain()["intact"] and len(back.event_log) >= 6
          and spawned_refused
          and any(e.get("run_history_saved") == "native-test-run"
                  for e in lp21.ledger.events),
          "runs land in the runs store automatically; spawned_loops refuse")

    # 22. ACCEPTED-SUCCESS != ATTEMPT (Universal Loop Standard §7).  A
    # ``success_once`` loop stops at the FIRST accepted success; the attempt
    # counter and accepted-success counter are distinct and recorded.
    def one_flaky_then_ok(loop, step, context):
        if step == "act" and context.get("requested_mode"):
            return StepOutcome(
                output="act:ok", mode=context["requested_mode"],
                confidence=0.9)
        if step == "act":
            if "act_tried" not in context:
                context["act_tried"] = True
                return StepOutcome(output="act:miss", mode="deterministic",
                                   failed=True, confidence=0.2)
            return StepOutcome(output="act:ok", mode="deterministic",
                               confidence=0.9)
        return StepOutcome(output=f"{step}:ok", mode="deterministic",
                           confidence=0.9)
    lp22 = Loop("stop at the first accepted success",
                LoopConfig(framework="custom",
                           custom_steps=("act", "verify", "commit"),
                           exit_condition="accepted_success"))
    r22 = lp22.run(handler=one_flaky_then_ok)
    check("success_once_stops_at_first_accepted_success",
          r22.stopped == "success_once" and r22.accepted_successes == 1
          and r22.attempts >= 1 and r22.steps_run <= 2
          and any(e.get("event") == "terminal"
                  and e.get("reason") == "success_once"
                  for e in lp22.ledger.events),
          f"stopped at success_once; attempts={r22.attempts} "
          f"accepted={r22.accepted_successes}")

    # `success_once` must not stop WITHOUT a success. Running out of steps is
    # the goal under run_to_completion; under success_once it means going round
    # again. Before this, a retry-until-it-works loop finished its one step,
    # terminated "done" with ZERO accepted successes, and reported success —
    # the exact opposite of the stop condition's name. Found by writing the
    # example for it.
    def _succeeds_on_nth(n):
        state = {"tries": 0}

        def handler(loop, step, context):
            state["tries"] += 1
            ok = state["tries"] >= n
            return StepOutcome(output="found" if ok else "timed out",
                               mode="deterministic",
                               confidence=1.0 if ok else 0.0, failed=not ok)
        lp = Loop("retry until it works",
                  LoopConfig(framework="custom", custom_steps=("attempt",),
                             allowable_modes=("deterministic",),
                             preferred_modes=("deterministic",),
                             exit_condition="accepted_success", power="light"))
        while not lp.is_terminal:
            lp.run_next_iteration(handler=handler)
        return state["tries"], lp.result()

    third_tries, third = _succeeds_on_nth(3)
    never_tries, never = _succeeds_on_nth(10 ** 6)
    first_tries, first = _succeeds_on_nth(1)
    check("success_once_retries_a_failed_pass_and_stays_bounded",
          third_tries == 3 and third.stopped == "success_once"
          and third.accepted_successes == 1
          and first_tries == 1 and first.stopped == "success_once"
          # and it cannot spin forever: with no success ever, the budget stops
          # it and names the real reason rather than claiming completion
          and never.stopped == "budget" and never.accepted_successes == 0
          and never_tries < 100,
          f"3rd-attempt success took {third_tries} attempts; a never-succeeding "
          f"loop stopped on budget after {never_tries}")

    # adversarial: an unknown current condition is refused fail-closed.
    bad = False
    try:
        LoopConfig(exit_condition="when_done_maybe")
    except ValueError:
        bad = True
    check("unknown_exit_condition_refused_fail_closed", bad)

    # 23. every loop carries a doctrine baseline composed from its goal —
    # the doctrine IS the constructor; the ledger records it.
    from .loop_contract import LoopContract as _C
    lp23 = Loop("typed", LoopConfig(framework="five_step"),
                contract=_C(name="typed", execution_mode="code_only",
                            input_roles=("in",), output_roles=("out",)))
    init23 = next(e for e in lp23.ledger.events if e.get("event") == "init")
    check("loop_carries_a_composed_baseline_on_record",
          init23.get("baseline_goal") == "typed"
          and init23.get("baseline_terminal_mode") == "code_only"
          and init23.get("loop_condition") == "steps_remain"
          and init23.get("exit_condition") == "steps_complete"
          and tuple(init23.get("output_roles", ())) == ("out",),
          "identity carries goal, typing, terminal mode, and both conditions")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "recursive_loop_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
