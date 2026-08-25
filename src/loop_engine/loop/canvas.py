"""Canvases and their matrix of passive Solution Loop candidates.

The owner's model (2026-08-22): the practitioner loop does not build into thin air,
it builds on a **canvas** that arranges typed Solution Loop candidates. Two kinds:

  * **solution canvas** — the actual answer to the problem being solved;
  * **exploration canvas** — where side work runs: note-taking, testing, side
    research, a sub-practitioner's own working area.  (The owner disliked
    "scratch"; this is the note-taking / testing / exploration canvas.)

A canvas is a graph-shaped plan, but its passive records are not graph vertices at
runtime. Execution creates one Starting Solution Loop and one role-correct Loop for
each attempted candidate. Ordered slots hold a preferred candidate plus typed
fallbacks. A normal pipeline member uses ``connected_from``. A fallback is a real
dynamic branch and uses ``spawned_by``. A slot fails only when every compatible
candidate Loop fails.

This is what lets "research this website" survive a blocked browser, and lets an
AI/ML pipeline survive one estimator operation erroring: the matrix carries the
alternatives, and execution picks the first that works.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .loop_definition import LoopDefinition
from .recursive_loop import MODES, Loop, LoopLedger
from ..code_nodes.solution_graph import make_solution_loop_definition

# The two canvas kinds the owner named.
CANVAS_KINDS = ("solution", "exploration")


@dataclass(frozen=True)
class TypeContract:
    """Typed input/output ports that make a fallback a legal drop-in.

    Two candidates are interchangeable for a slot when their contracts match
    (same input types and same output types), regardless of how they compute."""
    inputs: tuple = ()      # tuple of type names, e.g. ("DataFrame",)
    outputs: tuple = ()     # tuple of type names, e.g. ("Model",)

    def __post_init__(self) -> None:
        for field_name in ("inputs", "outputs"):
            values = tuple(getattr(self, field_name))
            if any(not isinstance(value, str) or not value.strip()
                   for value in values):
                raise ValueError(f"{field_name} must contain non-empty types")
            if len(values) != len(set(values)):
                raise ValueError(f"{field_name} cannot contain duplicates")
            object.__setattr__(self, field_name, values)
        if not self.outputs:
            raise ValueError("a candidate contract needs at least one output port")

    def compatible_with(self, other: "TypeContract") -> bool:
        return self.inputs == other.inputs and self.outputs == other.outputs


@dataclass
class SolutionLoopCandidate:
    """A passive candidate that references one complete Solution Loop."""
    name: str
    contract: TypeContract
    operation_ref: str
    definition: LoopDefinition
    implementation: Callable[[Any], Any] | None = field(
        default=None, repr=False, compare=False)
    cost: float = 0.0
    provenance: str = ""
    handle: str = ""
    mode: str = "deterministic"
    profile_id: str = "solution.atomic_component"

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("a solution candidate needs a name")
        if not isinstance(self.operation_ref, str) or not self.operation_ref.strip():
            raise ValueError("a solution candidate needs an operation_ref")
        if not isinstance(self.definition, LoopDefinition):
            raise ValueError(
                "a Canvas callable is not executable without a complete "
                "LoopDefinition; use SolutionLoopCandidate.from_callable")
        if self.mode not in MODES:
            raise ValueError(f"candidate mode must be one of {MODES}")
        if not self.profile_id.startswith("solution."):
            raise ValueError("a Canvas candidate needs a Solution role profile")
        definition = self.definition
        if definition.ref.content_digest != definition.content_digest:
            raise ValueError("candidate definition digest mismatch")
        if definition.identity.role.value != "solution":
            raise ValueError("a Canvas candidate needs a Solution Loop definition")
        if (definition.contract.input_roles != self.contract.inputs
                or definition.contract.output_roles != self.contract.outputs):
            raise ValueError("candidate ports conflict with its Loop definition")
        if definition.contract.runtime_mode != self.mode:
            raise ValueError("candidate mode conflicts with its Loop definition")
        if (definition.configuration_facts.to_dict().get("operation_ref")
                != self.operation_ref):
            raise ValueError(
                "candidate operation_ref is not bound inside its definition")

    @classmethod
    def from_callable(cls, name: str, contract: TypeContract,
                      implementation: Callable[[Any], Any], *,
                      operation_ref: str = "", cost: float = 0.0,
                      provenance: str = "", handle: str = "",
                      mode: str = "deterministic",
                      profile_id: str = "solution.atomic_component"
                      ) -> "SolutionLoopCandidate":
        """Make the callable selectable only after binding an exact Loop."""
        if not callable(implementation):
            raise ValueError("implementation must be callable")
        selected_ref = operation_ref or handle or name
        definition = make_solution_loop_definition(
            graph_id="canvas_candidate", vertex_id=name,
            profile_id=profile_id, input_roles=contract.inputs,
            output_roles=contract.outputs, selected_mode=mode,
            operation_ref=selected_ref, purpose="component")
        return cls(name, contract, selected_ref, definition, implementation,
                   cost, provenance, handle, mode, profile_id)


# Compatibility for older module-level imports. It is a passive candidate
# alias, never an operational graph type or a serialized runtime claim.
CanvasNode = SolutionLoopCandidate


@dataclass
class SolutionSlot:
    """One step of the matrix: a required contract and the ordered candidates that
    can fill it (preferred first, then type-compatible fallbacks = the waterfall)."""
    slot_id: str
    contract: TypeContract
    candidates: list = field(default_factory=list)

    def add_candidate(self, candidate: SolutionLoopCandidate, *,
                      prefer: bool = False) -> None:
        """Add a contract-compatible passive candidate to the slot."""
        if not isinstance(candidate, SolutionLoopCandidate):
            raise TypeError("a slot accepts SolutionLoopCandidate records")
        if not candidate.contract.compatible_with(self.contract):
            raise ValueError(
                f"candidate {candidate.name!r} contract {candidate.contract} "
                "is not compatible "
                f"with slot {self.slot_id!r} contract {self.contract}")
        if prefer:
            self.candidates.insert(0, candidate)
        else:
            self.candidates.append(candidate)

    @property
    def preferred(self) -> "SolutionLoopCandidate | None":
        return self.candidates[0] if self.candidates else None


@dataclass
class Canvas:
    """A canvas: an ordered matrix of solution slots, of one of the two kinds."""
    canvas_id: str
    kind: str = "solution"
    slots: list = field(default_factory=list)   # ordered SolutionSlots
    provenance: str = ""
    permitted_loop_modes: tuple[str, ...] = MODES

    def __post_init__(self):
        if self.kind not in CANVAS_KINDS:
            raise ValueError(f"canvas kind must be one of {CANVAS_KINDS}")
        self.permitted_loop_modes = tuple(self.permitted_loop_modes)
        if (not self.permitted_loop_modes
                or any(mode not in MODES for mode in self.permitted_loop_modes)):
            raise ValueError(f"permitted_loop_modes must use {MODES}")

    def add_slot(self, slot: SolutionSlot) -> None:
        self.slots.append(slot)

    def is_executable(self) -> bool:
        """Executable when every slot has at least one candidate AND adjacent
        slots type-connect (a slot's output feeds the next slot's input)."""
        if not self.slots or any(not s.candidates for s in self.slots):
            return False
        for a, b in zip(self.slots, self.slots[1:]):
            if a.contract.outputs != b.contract.inputs:
                return False
        return True

    def width(self) -> int:
        """The matrix width — how many alternative ways the widest step can go."""
        return max((len(s.candidates) for s in self.slots), default=0)


@dataclass
class SlotOutcome:
    slot_id: str
    chosen: str = ""
    ok: bool = False
    tried: list = field(default_factory=list)   # names attempted, in order
    attempted_loop_ids: list = field(default_factory=list)
    chosen_loop_id: str = ""
    error: str = ""


@dataclass
class MatrixExecution:
    canvas_id: str
    ok: bool
    outcomes: list = field(default_factory=list)
    output: Any = None
    starting_loop_id: str = ""
    events: list = field(default_factory=list)

    def waterfalls_used(self) -> int:
        """How many slots succeeded on a FALLBACK rather than the preferred node —
        the robustness the matrix bought."""
        return sum(1 for o in self.outcomes if o.ok and o.tried and
                   o.chosen != o.tried[0])


def execute_matrix(canvas: Canvas, initial_input: Any = None, *,
                   parent: "Loop | None" = None,
                   ledger: "LoopLedger | None" = None,
                   registry: "dict | None" = None) -> MatrixExecution:
    """Project selected candidates into one graph, then run that graph."""
    if not canvas.is_executable():
        return MatrixExecution(canvas.canvas_id, ok=False, output=None)
    disallowed = sorted({candidate.mode for slot in canvas.slots
                         for candidate in slot.candidates
                         if candidate.mode not in canvas.permitted_loop_modes})
    if disallowed:
        raise ValueError(
            f"Canvas policy does not permit candidate modes {disallowed}")
    selected_ledger = (parent.ledger if parent is not None
                       else ledger or LoopLedger())
    event_start = len(selected_ledger.events)
    from ..code_nodes.solution_canvas import (
        SolutionError, SolutionLoopSpec, SolutionSpec, run_solution)
    loops = []
    selected_registry = dict(registry or {})
    for slot in canvas.slots:
        primary, *fallbacks = slot.candidates
        loops.append(SolutionLoopSpec(
            slot.slot_id, primary.operation_ref, primary.mode,
            tuple(item.operation_ref for item in fallbacks), {},
            slot.contract.inputs[0], slot.contract.outputs[0],
            primary.definition,
            tuple(item.definition for item in fallbacks)))
        for candidate in slot.candidates:
            if candidate.implementation is not None:
                prior = selected_registry.get(candidate.operation_ref)
                if prior is not None and prior is not candidate.implementation:
                    raise ValueError(
                        f"operation {candidate.operation_ref!r} resolves to "
                        "different implementations")
                selected_registry[candidate.operation_ref] = (
                    lambda value, params, fn=candidate.implementation: fn(value))
    spec = SolutionSpec(
        canvas.canvas_id, permitted_loop_modes=canvas.permitted_loop_modes,
        loops=tuple(loops))
    trace: list[dict] = []
    error = ""
    output = None
    try:
        output = run_solution(
            spec, selected_registry, initial_input, trace=trace,
            ledger=selected_ledger, parent=parent)
        ok = True
    except SolutionError as exc:
        ok = False
        error = str(exc)
    outcomes = []
    for slot in canvas.slots:
        outcome = SlotOutcome(slot.slot_id, error=error)
        relevant = [item for item in trace
                    if item.get("solution_loop") == slot.slot_id
                    and item.get("operation")]
        outcome.tried = list(dict.fromkeys(
            item["operation"] for item in relevant))
        outcome.attempted_loop_ids = list(dict.fromkeys(
            item["component_loop_id"] for item in trace
            if item.get("component_loop_id")
            and (item.get("solution_loop") == slot.slot_id
                 or item.get("solution_loop", "").startswith(
                     f"{slot.slot_id}:"))))
        successful = next((item for item in reversed(relevant)
                           if not item.get("failed")), None)
        if successful is not None:
            outcome.chosen = successful["operation"]
            outcome.chosen_loop_id = successful.get("component_loop_id", "")
            outcome.ok = True
        outcomes.append(outcome)
    starting_id = next((item["runtime_loop_id"] for item in trace
                        if item.get("runtime_event") == "started"), "")
    return MatrixExecution(
        canvas.canvas_id, ok, outcomes, output, starting_id,
        list(selected_ledger.events[event_start:]))


# ---------------------------------------------------------------------------
# Self-test — deterministic, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    df2model = TypeContract(inputs=("DataFrame",), outputs=("Model",))
    model2pred = TypeContract(inputs=("Model",), outputs=("Predictions",))

    # a solution canvas with two typed slots
    canvas = Canvas("c1", kind="solution")
    s1 = SolutionSlot("fit", df2model)
    s1.add_candidate(SolutionLoopCandidate.from_callable(
        "xgboost", df2model, lambda x: "model:xgb", provenance="reuse"))
    s1.add_candidate(SolutionLoopCandidate.from_callable(
        "lightgbm", df2model, lambda x: "model:lgbm", provenance="reuse"))
    s2 = SolutionSlot("predict", model2pred)
    s2.add_candidate(SolutionLoopCandidate.from_callable(
        "predict", model2pred, lambda m: [1, 0, 1]))
    canvas.add_slot(s1); canvas.add_slot(s2)

    check("a_solution_canvas_holds_ordered_typed_slots",
          canvas.kind == "solution" and len(canvas.slots) == 2
          and canvas.is_executable(),
          "two type-connected slots (DataFrame->Model->Predictions) are executable")

    check("a_slot_carries_a_preferred_candidate_and_compatible_fallbacks",
          s1.preferred.name == "xgboost" and len(s1.candidates) == 2,
          "the fit slot prefers xgboost with lightgbm as a compatible fallback")

    # an incompatible fallback is refused
    refused = False
    try:
        s1.add_candidate(SolutionLoopCandidate.from_callable(
            "bad", model2pred, lambda x: x))
    except ValueError:
        refused = True
    check("an_incompatible_fallback_is_refused",
          refused,
          "a candidate whose contract does not match cannot be a drop-in")

    # execution waterfalls: preferred fails -> compatible fallback runs
    canvas2 = Canvas("c2", kind="solution")
    sf = SolutionSlot("fit", df2model)
    def boom(x):
        raise RuntimeError("xgboost node crashed")
    sf.add_candidate(SolutionLoopCandidate.from_callable(
        "xgboost", df2model, boom))
    sf.add_candidate(SolutionLoopCandidate.from_callable(
        "lightgbm", df2model, lambda x: "model:lgbm"))
    sp = SolutionSlot("predict", model2pred)
    sp.add_candidate(SolutionLoopCandidate.from_callable(
        "predict", model2pred, lambda m: "preds"))
    canvas2.add_slot(sf); canvas2.add_slot(sp)
    ex = execute_matrix(canvas2, initial_input="df")
    candidate_inits = [event for event in ex.events
                       if event.get("event") == "init"
                       and event.get("profile_id")
                       == "solution.atomic_component"]
    check("execution_waterfalls_to_a_compatible_loop_when_the_preferred_fails",
          ex.ok and ex.output == "preds" and ex.waterfalls_used() == 1
          and ex.outcomes[0].chosen == "lightgbm"
          and ex.outcomes[0].tried == ["xgboost", "lightgbm"]
          and len(candidate_inits) == 3
          and [event.get("relationship_kind") for event in candidate_inits]
              == ["spawned_by", "spawned_by", "connected_from"]
          and all(event.get("role") == "solution"
                  and event.get("loop_condition") == "steps_remain"
                  and event.get("exit_condition") == "accepted_success"
                  and event.get("input_roles") and event.get("output_roles")
                  for event in candidate_inits),
          "an explicit Router Loop spawns each ordered fallback attempt")

    # a slot fails only if ALL candidates fail
    canvas3 = Canvas("c3", kind="solution")
    sbad = SolutionSlot("fit", df2model)
    sbad.add_candidate(SolutionLoopCandidate.from_callable(
        "a", df2model, boom))
    sbad.add_candidate(SolutionLoopCandidate.from_callable(
        "b", df2model, boom))
    canvas3.add_slot(sbad)
    ex3 = execute_matrix(canvas3, initial_input="df")
    check("a_slot_fails_only_when_every_compatible_candidate_fails",
          not ex3.ok and ex3.outcomes[0].tried == ["a", "b"]
          and not ex3.outcomes[0].ok,
          "with both candidates crashing the slot fails, recording all attempts "
          "so the slot can be repaired")

    # exploration canvas is a distinct kind for side work
    expl = Canvas("scratch1", kind="exploration",
                  provenance="sub-practitioner research")
    check("an_exploration_canvas_is_a_distinct_kind_for_side_work",
          expl.kind == "exploration" and expl.kind != canvas.kind,
          "side research/testing runs on an exploration canvas, separate from the "
          "solution canvas")

    check("the_matrix_reports_its_width",
          canvas2.width() == 2,
          "the widest step offers 2 interchangeable candidates")

    disallowed_called = []
    blocked = Canvas("blocked", permitted_loop_modes=("deterministic",))
    blocked_slot = SolutionSlot("x", df2model)
    unavailable_refused = False
    try:
        blocked_slot.add_candidate(SolutionLoopCandidate.from_callable(
            "model-led", df2model,
            lambda value: disallowed_called.append(value),
            mode="non_deterministic"))
    except ValueError:
        unavailable_refused = True
    blocked.add_slot(blocked_slot)
    refused_mode = False
    try:
        if not unavailable_refused:
            execute_matrix(blocked, initial_input="df")
    except ValueError:
        refused_mode = True
    check("canvas_policy_refuses_a_disallowed_node_level_mode_before_execution",
          (unavailable_refused or refused_mode) and not disallowed_called,
          "Canvas policy restricts member modes; each member still owns its mode")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "canvas_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
