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
from dataclasses import dataclass, field

from ..loop.kernel import KERNEL_NODES

MODES = ("deterministic", "hybrid", "non_deterministic")
# Precise internal names for the same three modes (user-facing stays simple):
# embeddings / trained models / seeded search are machine-run CODE, not strictly
# deterministic — the real distinction is whether a semantic LLM call happens.
INTERNAL_MODE_NAMES = {"deterministic": "code_only",
                       "hybrid": "code_with_model_assistance",
                       "non_deterministic": "model_led"}
FRAMEWORKS = ("nine_step", "five_step", "custom", "open")

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
    "every child has a parent and a declared return destination",
    "child modes never exceed the parent's delegation authority",
    "recursion depth and child count are bounded",
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


@dataclass
class LoopConfig:
    """Everything passed into a Loop at initialization.

    ``stop_condition`` is the loop's declared completion policy — the
    doctrine's first-class identity, not a hack on the iteration engine.
    ``run_to_completion`` is the default (the loop runs its sequence/budget);
    ``success_once`` stops after the first ACCEPTED-success iteration (the
    step's outcome not failed and its confidence meets the bar) — the
    degenerate, fully legal stop most Solution DAG loops use.  A loop that
    declares ``success_once`` may still make several ATTEMPTS across the mode
    waterfall; acceptance-vs-attempt is tracked separately in the result."""
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
    stop_condition: str = "run_to_completion"          # or "success_once"
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
        if self.stop_condition not in ("run_to_completion", "success_once"):
            raise ValueError("stop_condition must be run_to_completion or "
                             "success_once — an unknown stop is refused "
                             "fail-closed, a loop may not run without one")

    @property
    def settings(self) -> dict:
        return POWER_SETTINGS[self.power]


@dataclass
class LoopLedger:
    """The intelligent database of everything that happened — decisions, inputs,
    outputs, modes, spawns, infra calls.  Shared across a loop and its children so
    the whole recursive tree has one history."""
    events: list[dict] = field(default_factory=list)
    _counter: int = 0

    def next_id(self) -> str:
        self._counter += 1
        return f"loop{self._counter}"

    def record(self, **kw) -> None:
        import time
        self.events.append({"ts": time.time(), **kw})

    def tree(self) -> dict:
        """The loops-of-loops nesting, from the recorded parent links."""
        kids: dict = {}
        for e in self.events:
            if e.get("event") == "spawn":
                kids.setdefault(e["parent"], []).append(e["loop_id"])
        return kids

    def loops(self) -> set:
        return {e["loop_id"] for e in self.events if "loop_id" in e}


@dataclass
class StepOutcome:
    """What resolving one step produced.  ``spawn_goal`` triggers a child loop;
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
    stop_condition: str = "run_to_completion"

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
    """A deterministic step handler (no real model call — cloud-only policy): it
    picks the mode via the loop's waterfall and returns a synthetic result.  Real
    handlers delegate a step to the kernel / a code node / the LLM pipeline."""
    mode = loop.choose_mode(
        needs_judgement=step in ("decide_next", "assess_prepare", "choose",
                                 "decide"))
    return StepOutcome(output=f"{step}:done", mode=mode, confidence=0.8)


class Loop:
    """The fundamental object: initialize with a goal + config; it runs a shape of
    steps, each resolved in a mode chosen by the waterfall; it can SPAWN child
    loops (recursive initialization) whose results flow back."""

    def __init__(self, goal: str, config: "LoopConfig | None" = None, *,
                 parent: "Loop | None" = None, depth: int = 0,
                 ledger: "LoopLedger | None" = None,
                 contract: "object | None" = None):
        self.goal = goal
        self.config = config or LoopConfig()
        self.parent = parent
        self.depth = depth
        self.ledger = ledger or LoopLedger()
        self.loop_id = self.ledger.next_id()
        # The doctrine baseline rides the loop's identity.  ``contract`` (a
        # loop_contract.LoopContract, any object with name/execution_mode/
        # input_roles/output_roles) is the typed+mode declaration; when a
        # caller passes nothing, a default practitioner baseline is composed
        # from the goal so EVERY loop carries one — the doctrine is the
        # constructor, not a side-channel.  Typed in, never re-derived.
        if contract is None:
            from .loop_doctrine import baseline_for_practitioner
            contract = baseline_for_practitioner(
                goal, output_roles=(f"{goal[:24].replace(' ','_')}_out",))
        self.contract = contract
        m = getattr(contract, "terminal_mode",
                    getattr(contract, "execution_mode", ""))
        self.ledger.record(loop_id=self.loop_id, depth=depth, event="init",
                            goal=goal, framework=self.config.framework,
                            logical_kind=self.config.logical_kind,
                            replay_guarantee=self.config.replay_guarantee,
                            power=self.config.power,
                            llm_thinking_power=
                                self.config.llm_thinking_power,
                            stop_condition=self.config.stop_condition,
                            baseline_goal=getattr(contract, "goal", goal),
                            baseline_terminal_mode=m,
                            input_roles=tuple(getattr(contract, "input_roles", ())),
                            output_roles=tuple(getattr(contract, "output_roles", ())))
        # the first honest emitter for loop.started — the loop is live.
        self.ledger.record(loop_id=self.loop_id, depth=depth,
                           event="loop.started", goal=goal)

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

    # --- recursion: one loop initializes another ---------------------------

    def spawn(self, goal: str, config: "LoopConfig | None" = None, *,
              contract=None) -> "Loop":
        """Initialize a CHILD loop (e.g. a research loop) whose answer helps this
        loop proceed.  Depth-limited; recorded on the shared ledger.

        Mode is local to each loop. The parent's own ``allowable_modes`` do not
        determine the child's mode. A deterministic loop may start a
        non-deterministic loop, and the reverse is also valid.

        ``delegated_modes`` is the separate authority rail. A requested child
        config is clamped to the modes the parent may delegate. The child's own
        delegation authority is also clamped, so it cannot pass on authority
        that the parent did not grant. Power may differ; effort never grants
        new authority.
        """
        if self.depth + 1 > self.config.max_depth:
            raise LoopError(f"max recursion depth {self.config.max_depth} reached")
        clamped_from = ()
        delegated_clamped_from = ()
        if config is not None and config is not self.config:
            allowed = tuple(m for m in config.allowable_modes
                            if m in self.config.delegated_modes)
            if not allowed:
                raise LoopError(
                    "child modes "
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
                    stop_condition=config.stop_condition,
                    success_confidence_min=config.success_confidence_min)
        # the REQUEST is recorded before the child exists: a spawn that is
        # refused by the delegation clamp still leaves a trace of having been
        # asked for, which a spawn-only event cannot show.
        self.ledger.record(loop_id=self.loop_id, event="child_requested",
                           goal=str(goal)[:120], depth=self.depth + 1)
        child = Loop(goal, config or self.config, parent=self,
                     depth=self.depth + 1, ledger=self.ledger,
                     contract=contract)
        self.ledger.record(loop_id=child.loop_id, parent=self.loop_id,
                           depth=child.depth, event="spawn", goal=goal,
                           **({"modes_clamped_from": clamped_from,
                               "modes_clamped_to":
                                   tuple(child.config.allowable_modes)}
                              if clamped_from else {}),
                           **({"delegated_modes_clamped_from":
                                  delegated_clamped_from,
                               "delegated_modes_clamped_to":
                                  tuple(child.config.delegated_modes)}
                              if delegated_clamped_from else {}))
        return child

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
                "max_model_calls": st["max_model_calls"], "steps": rows}

    # --- initialization from a serialized Loop Specification String ---------

    @classmethod
    def initialize(cls, spec: dict, *, ledger: "LoopLedger | None" = None,
                   parent: "Loop | None" = None) -> "Loop":
        """Initialize a Loop from a serialized LoopSpec (a String).  Validated
        fail-closed: unknown top-level keys are refused; a child spec asking to
        INCREASE permissions is refused.  The spec digest is recorded so every
        run is traceable to the exact specification that configured it."""
        known = {"loop_id", "objective", "inputs", "output_expectation",
                 "loop_template", "resolution", "power", "strings", "models",
                 "children", "limits", "stopping"}
        unknown = set(spec) - known
        if unknown:
            raise LoopError(f"unknown LoopSpec keys {sorted(unknown)} refused "
                            "(fail closed — a typo must never silently no-op)")
        objective = spec.get("objective") or {}
        goal = (objective.get("text_or_ref") if isinstance(objective, dict)
                else str(objective)) or spec.get("loop_id", "")
        if not goal:
            raise LoopError("a LoopSpec needs an objective")
        children = spec.get("children") or {}
        if children.get("may_increase_permissions"):
            raise LoopError("children.may_increase_permissions=true is refused: "
                            "a child never has more permissions than its parent")
        resolution = spec.get("resolution") or {}
        _from_internal = {v: k for k, v in INTERNAL_MODE_NAMES.items()}

        def _modes(names, default):
            if not names:
                return default
            return tuple(_from_internal.get(m, m) for m in names)

        template = spec.get("loop_template") or {}
        limits = spec.get("limits") or {}
        cfg = LoopConfig(
            framework=template.get("framework", "nine_step"),
            logical_kind=template.get("logical_kind", "execution"),
            replay_guarantee=template.get("replay_guarantee",
                                          "event_equivalent"),
            allowable_modes=_modes(resolution.get("allowed_modes"), MODES),
            preferred_modes=_modes(resolution.get("preferred_waterfall"),
                                   ("deterministic", "hybrid",
                                    "non_deterministic")),
            delegated_modes=_modes(children.get("allowed_modes"), MODES),
            power=(spec.get("power") or {}).get("profile", "standard"),
            llm_thinking_power=(spec.get("models") or {}).get(
                "thinking_power", ""),
            custom_steps=tuple(template.get("steps", ())),
            max_depth=int(children.get("maximum_depth", 3)),
            stop_condition=(spec.get("stopping") or {}).get(
                "condition", "run_to_completion"),
            success_confidence_min=float((spec.get("stopping") or {}).get(
                "success_confidence_min", 0.5)))
        digest = hashlib.sha256(
            json.dumps(spec, sort_keys=True, default=str).encode()).hexdigest()
        if parent is not None:
            loop = parent.spawn(goal, cfg)
        else:
            loop = cls(goal, cfg, ledger=ledger)
        loop.spec = dict(spec)
        loop.spec_digest = digest
        if limits.get("maximum_iterations"):
            loop._max_steps_override = int(limits["maximum_iterations"])
        loop.ledger.record(loop_id=loop.loop_id, event="spec",
                           spec_digest=digest,
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
                          stop_condition=self.config.stop_condition)

    def enable_chronicle(self, run_id: str, *, root_dir: str,
                         usage_log: "list | None" = None) -> None:
        """Native Chronicle emission (§9.4): when enabled on a ROOT loop,
        its terminal transition projects the shared ledger into a canonical
        Chronicle and persists it under ``root_dir/<run_id>/`` — every run
        lands in the runs store automatically.  ``usage_log`` is the live
        list the handler appends provider usage to (captured by reference)."""
        if self.parent is not None:
            raise LoopError("enable_chronicle on the ROOT loop only — "
                            "children share the root's history")
        self._chronicle = {"run_id": run_id, "root_dir": root_dir,
                           "usage_log": usage_log if usage_log is not None
                           else []}

    def _terminate(self, it: dict, reason: str) -> None:
        """The ONE terminal transition: every stop is recorded on the ledger,
        so closure can be audited (no silent ends, no orphan ambiguity)."""
        it["stopped"] = reason
        self.ledger.record(loop_id=self.loop_id, event="terminal",
                            reason=reason, stop_condition=self.config.stop_condition,
                            accepted_successes=it.get("accepted_successes", 0),
                            attempts=it.get("attempts", 0))
        # A child that reached a terminal state RETURNS to its parent: the
        # return destination is recorded on the parent's own timeline, so
        # spawn and return are both visible (§8.2 — every child has a return
        # destination; the closure audit reads the terminal, the parent reads
        # this).
        if self.parent is not None:
            self.ledger.record(loop_id=self.parent.loop_id,
                               event="child_return", child=self.loop_id,
                               depth=self.depth, reason=reason,
                               steps_run=it.get("steps_run", 0))
        cfg = getattr(self, "_chronicle", None)
        if cfg is not None:
            from ..static_architecture.chronicle import Chronicle
            ch = Chronicle.from_ledger(self.ledger.events,
                                       run_id=cfg["run_id"],
                                       usage_log=cfg["usage_log"])
            ch.commit()
            ch.save(cfg["root_dir"])
            self.ledger.record(loop_id=self.loop_id,
                               event="custom",
                               chronicle_saved=cfg["run_id"])

    def audit_closure(self) -> dict:
        """§15.2 closure audit: every child this loop spawned must itself have
        reached a recorded terminal state.  A spawned-but-never-run child is an
        ORPHAN and fails the audit — inspectable, never silent."""
        spawned = [e["loop_id"] for e in self.ledger.events
                   if e.get("event") == "spawn"
                   and e.get("parent") == self.loop_id]
        terminal = {e["loop_id"] for e in self.ledger.events
                    if e.get("event") == "terminal"}
        orphans = [c for c in spawned if c not in terminal]
        return {"loop_id": self.loop_id, "children": spawned,
                "orphaned_children": orphans,
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
        return {"record_type": "loop_pause/v1", "loop_id": self.loop_id,
                "goal": self.goal, "depth": self.depth, "reason": reason,
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
                           "stop_condition": self.config.stop_condition,
                           "success_confidence_min":
                               self.config.success_confidence_min},
                "iteration_state": {k: (dict(v) if isinstance(v, dict)
                                        else list(v) if isinstance(v, list)
                                        else v)
                                    for k, v in it.items()},
                "spec_digest": getattr(self, "spec_digest", "")}

    @classmethod
    def resume(cls, token: dict, *,
               ledger: "LoopLedger | None" = None) -> "Loop":
        """Reconstruct a paused loop from its resume token and continue exactly
        where it stopped (durable resumption)."""
        if token.get("record_type") != "loop_pause/v1":
            raise LoopError("not a loop_pause/v1 resume token")
        c = token["config"]
        loop = cls(token["goal"],
                   LoopConfig(framework=c["framework"],
                              logical_kind=c.get("logical_kind", "execution"),
                              replay_guarantee=c.get("replay_guarantee",
                                                     "event_equivalent"),
                              allowable_modes=tuple(c["allowable_modes"]),
                              preferred_modes=tuple(c["preferred_modes"]),
                              delegated_modes=tuple(
                                  c.get("delegated_modes", MODES)),
                              power=c["power"],
                              llm_thinking_power=c.get(
                                  "llm_thinking_power", ""),
                              custom_steps=tuple(c["custom_steps"]),
                              max_depth=c["max_depth"],
                              stop_condition=c.get("stop_condition",
                                                   "run_to_completion"),
                              success_confidence_min=float(c.get(
                                  "success_confidence_min", 0.5))),
                   ledger=ledger)
        loop._it = {k: (dict(v) if isinstance(v, dict) else v)
                    for k, v in token["iteration_state"].items()}
        loop._it["seq"] = list(token["iteration_state"]["seq"])
        loop.ledger.record(loop_id=loop.loop_id, event="resume",
                           resumed_from=token["loop_id"],
                           at_step=loop._it["steps_run"])
        return loop

    def run_next_iteration(self, *, handler=None, chooser=None,
                           max_steps: "int | None" = None) -> dict:
        """Run exactly ONE bounded iteration; returns the LoopIterationRecord.
        At most one semantic model call happens per iteration (§12) — a
        semantic fallback is deferred to the NEXT iteration as a visible model
        boundary, never hidden inside this one."""
        handler = handler or default_handler
        it = self._ensure_execution(max_steps)
        st = self.config.settings
        rec = {"record_type": "loop_iteration/v1", "loop_id": self.loop_id,
               "iteration": it["steps_run"] + 1, "semantic_calls": 0,
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
            outcome = StepOutcome(output=f"{step}:recovered:{forced_mode}",
                                  mode=forced_mode, confidence=0.6)
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
                    # END OF THE STEP SEQUENCE. Under `run_to_completion` that
                    # is the goal and the loop is done. Under `success_once` it
                    # is NOT: the stop condition is "one iteration succeeded",
                    # so finishing the steps without an accepted success means
                    # going round again, not stopping.
                    #
                    # Terminating here regardless made `success_once` able to
                    # stop with ZERO successes — the opposite of what it says —
                    # and a retry-until-it-works loop silently ran exactly one
                    # attempt. Found by writing the example for it.
                    if (self.config.stop_condition == "success_once"
                            and it["accepted_successes"] < 1):
                        it["i"] = 0                  # another pass
                        self.ledger.record(
                            loop_id=self.loop_id, depth=self.depth,
                            event="iteration_started",
                            iteration=it["attempts"] + 1,
                            note="no accepted success yet; success_once "
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
                if (outcome.mode in ("hybrid", "non_deterministic")
                        and fb in ("hybrid", "non_deterministic")):
                    # §12: a semantic fallback is ANOTHER semantic call →
                    # defer it to the next iteration, visibly.
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
            child = self.spawn(outcome.spawn_goal)   # loops initialize loops
            cres = child.run(handler=handler, chooser=chooser)
            it["context"][f"{step}:child"] = cres.output
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
        # cleared the confidence bar.  ``success_once`` stops on the first.
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
        if (self.config.stop_condition == "success_once" and
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
          * an outcome with ``spawn_goal`` recursively initializes a CHILD loop,
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


# The canonical public name (§19): one universal recursive class, two spellings.
PractitionerLoop = Loop


def suggested_templates() -> list:
    """A few starting-point loop configs as searchable resources — the "nice
    middle ground" front lever plus framework presets."""
    from ..static_architecture.store_serve import StoreRecord
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
              "role": "loop_template"},
        tags=("loop_template", fw, power), tier="core")
            for name, fw, power, pref in presets]


# ---------------------------------------------------------------------------
# Self-test — deterministic, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name, ok, detail=""):
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    # 1. a Loop is a parameterized CLASS: initialize with a goal + config.
    lp = Loop("solve churn", LoopConfig(framework="nine_step", power="medium"))
    check("a_loop_is_an_initializable_parameterized_class",
          lp.goal == "solve churn" and lp.config.framework == "nine_step"
          and lp.loop_id.startswith("loop"),
          "core config passed in at init; a loop id is assigned")

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
    grandchild = research.spawn("research point-in-time features")
    deep_blocked = False
    try:
        grandchild.spawn("too deep")
    except LoopError:
        deep_blocked = True
    check("loops_recursively_initialize_loops",
          research.depth == 1 and grandchild.depth == 2 and deep_blocked
          and research.parent is root,
          "one loop spawns another whose answer helps it proceed; depth-limited")

    improve_root = Loop("review history", LoopConfig(
        allowable_modes=("deterministic",),
        preferred_modes=("deterministic",), max_depth=2,
        delegated_modes=("deterministic",),
        logical_kind="search_improvement",
        replay_guarantee="evidence_equivalent"))
    improve_child = improve_root.spawn("audit context", LoopConfig(
        framework="custom", custom_steps=("audit",),
        allowable_modes=("deterministic", "hybrid"),
        preferred_modes=("deterministic", "hybrid"), max_depth=2,
        logical_kind="search_improvement",
        replay_guarantee="evidence_equivalent"))
    check("spawn_clamp_preserves_improvement_identity_and_replay_policy",
          improve_child.config.allowable_modes == ("deterministic",)
          and improve_child.config.logical_kind == "search_improvement"
          and improve_child.config.replay_guarantee == "evidence_equivalent")

    det_parent = Loop("deterministic orchestration", LoopConfig(
        allowable_modes=("deterministic",),
        preferred_modes=("deterministic",), max_depth=2))
    model_child = det_parent.spawn("open-ended research", LoopConfig(
        framework="custom", custom_steps=("research",),
        allowable_modes=("non_deterministic",),
        preferred_modes=("non_deterministic",), max_depth=2))
    model_parent = Loop("model-led planning", LoopConfig(
        allowable_modes=("non_deterministic",),
        preferred_modes=("non_deterministic",), max_depth=2))
    code_child = model_parent.spawn("validate the proposal", LoopConfig(
        framework="custom", custom_steps=("validate",),
        allowable_modes=("deterministic",),
        preferred_modes=("deterministic",), max_depth=2))
    check("parent_and_child_modes_are_independent_under_delegation_policy",
          model_child.config.allowable_modes == ("non_deterministic",)
          and code_child.config.allowable_modes == ("deterministic",)
          and model_child.parent is det_parent and code_child.parent is model_parent,
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
    check("plan_requires_string_intelligence_per_step",
          plan["steps"]
          and all(r["required_intelligence"] == 5 for r in plan["steps"])
          and plan["max_model_calls"] == 40,
          "each step pulls at least N string prompts (from the power lever)")

    # 9. loop templates are searchable resources (the front-lever presets).
    from ..static_architecture.store_serve import SolverStore
    store = SolverStore(core_records=suggested_templates())
    hit = store.search("offline deterministic only loop", kind="strategy")
    check("loop_templates_are_searchable",
          hit["hits"] and any("looptmpl." in h["record_id"] for h in hit["hits"]),
          "starting-point loop configs flow through the one search DAG")

    # 10. a loop actually RUNS: nine steps execute deterministically end-to-end,
    # everything on the ledger.
    r1 = Loop("run it", LoopConfig(power="large")).run()
    check("a_loop_actually_runs_end_to_end",
          r1.steps_run == 9 and r1.stopped == "done"
          and r1.mode_counts.get("deterministic", 0) >= 6 and r1.output,
          f"{r1.steps_run} steps, modes {r1.mode_counts} (medium power caps at 6 "
          "iterations — the lever binds, so nine steps need 'large')")

    # 11. RECURSIVE EXECUTION: a research step spawns a child loop, RUNS it, and
    # uses its answer — loops initializing loops, live.
    def research_handler(loop, step, context):
        if step == "research" and loop.depth == 0 and f"{step}:child" not in context:
            return StepOutcome(output=f"{step}:needs-child", mode="deterministic",
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
          f"child spawned+ran; its answer fed the parent ({r2.spawned} spawned)")

    # 12. the MODE FALLBACK runs live: a failed deterministic step recovers on the
    # next mode in the waterfall, recorded.
    def flaky_handler(loop, step, context):
        if step == "act":
            return StepOutcome(output="act:error", mode="deterministic",
                               failed=True)
        return default_handler(loop, step, context)
    lp3 = Loop("flaky", LoopConfig(framework="custom",
                                   custom_steps=("orient", "act", "verify")))
    lp3.run(handler=flaky_handler)
    fell = [e for e in lp3.ledger.events if e.get("event") == "fallback"]
    check("mode_fallback_runs_live",
          fell and fell[0]["from_mode"] == "deterministic"
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
            "children": {"maximum_depth": 2}}
    lp15 = Loop.initialize(spec)
    bad_key = bad_perm = False
    try:
        Loop.initialize({"objective": {"text_or_ref": "x"}, "powerr": {}})
    except LoopError:
        bad_key = True
    try:
        Loop.initialize({"objective": {"text_or_ref": "x"},
                         "children": {"may_increase_permissions": True}})
    except LoopError:
        bad_perm = True
    check("initialize_from_serialized_loopspec_fail_closed",
          lp15.goal == "predict churn"
          and lp15.config.allowable_modes == ("deterministic", "hybrid")
          and lp15.config.custom_steps == ("orient", "research", "decide", "act")
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
          token["record_type"] == "loop_pause/v1"
          and r17.steps_run == 5 and r17.stopped == "done"
          and lp17b.config.logical_kind == "search_improvement"
          and lp17b.config.replay_guarantee == "evidence_equivalent"
          and lp17b.config.delegated_modes == ("deterministic", "hybrid")
          and any(e.get("event") == "resume" for e in lp17b.ledger.events),
          "2 steps before pause + 3 after resume = the same 5-step loop")

    # 18. §12: at most ONE semantic call per iteration — a semantic→semantic
    # fallback is DEFERRED to the next iteration as a visible model boundary.
    def semantic_flaky(loop, step, context):
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

    # 20. PractitionerLoop is the same canonical class (one runtime, §19).
    check("practitioner_loop_is_the_same_canonical_class",
          PractitionerLoop is Loop, "one universal recursive class")

    # 21. NATIVE CHRONICLE EMISSION: a root loop with enable_chronicle
    # persists its canonical history automatically at terminal; children
    # refuse (they share the root's history).
    import tempfile as _tf
    _croot = _tf.mkdtemp(prefix="chron_native_")
    lp21 = Loop("native emit", LoopConfig(framework="five_step",
                                          power="deep"))
    lp21.enable_chronicle("native-test-run", root_dir=_croot)
    child_refused = False
    try:
        lp21.spawn("child").enable_chronicle("nope", root_dir=_croot)
    except LoopError:
        child_refused = True
    lp21.run()
    from ..static_architecture.chronicle import Chronicle as _Ch
    back = _Ch.load(_croot, "native-test-run")
    check("root_loop_emits_its_chronicle_natively_at_terminal",
          back.verify_chain()["intact"] and len(back.events) >= 6
          and child_refused
          and any(e.get("chronicle_saved") == "native-test-run"
                  for e in lp21.ledger.events),
          "runs land in the runs store automatically; children refuse")

    # 22. ACCEPTED-SUCCESS != ATTEMPT (Universal Loop Standard §7).  A
    # ``success_once`` loop stops at the FIRST accepted success; the attempt
    # counter and accepted-success counter are distinct and recorded.
    def one_flaky_then_ok(loop, step, context):
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
                           stop_condition="success_once"))
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
                             stop_condition="success_once", power="light"))
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

    # adversarial: an unknown stop condition is refused fail-closed.
    bad = False
    try:
        LoopConfig(stop_condition="when_done_maybe")
    except ValueError:
        bad = True
    check("unknown_stop_condition_refused_fail_closed", bad)

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
          and init23.get("stop_condition") == "run_to_completion"
          and tuple(init23.get("output_roles", ())) == ("out",),
          "identity carries goal, typing, terminal mode, and stop condition")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "recursive_loop_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
