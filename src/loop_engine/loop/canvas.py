"""Canvases and the matrix of solutions — the substrate the practitioner builds on.

The owner's model (2026-08-22): the practitioner loop does not build into thin air,
it builds on a **canvas** — the place where nodes are placed and wired into something
executable.  Two kinds:

  * **solution canvas** — the actual answer to the problem being solved;
  * **exploration canvas** — where side work runs: note-taking, testing, side
    research, a sub-practitioner's own working area.  (The owner disliked
    "scratch"; this is the note-taking / testing / exploration canvas.)

A canvas is a graph, but because the system swarms and each step may have several
interchangeable ways to succeed, a canvas is better thought of as a **matrix of
solutions**: an ordered list of SLOTS, where each slot is one step of the solution
and holds a *preferred* node plus **type-compatible fallbacks**.  If the preferred
node for step 2 fails — the node is broken, the browser is blocked, the API is
down — execution waterfalls to the next node whose input/output contract matches,
so the whole solution does not collapse because one node did.  A slot fails only
when *every* compatible candidate fails.

This is what lets "research this website" survive a blocked browser, and lets an
AI/ML pipeline survive one estimator node erroring: the matrix carries the
alternatives, and execution picks the first that works.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

# The two canvas kinds the owner named.
CANVAS_KINDS = ("solution", "exploration")


@dataclass(frozen=True)
class TypeContract:
    """The typed input/output ports of a node — what makes a fallback a legal
    drop-in.  Two nodes are interchangeable for a slot when their contracts match
    (same input types and same output types), regardless of how they compute."""
    inputs: tuple = ()      # tuple of type names, e.g. ("DataFrame",)
    outputs: tuple = ()     # tuple of type names, e.g. ("Model",)

    def compatible_with(self, other: "TypeContract") -> bool:
        return self.inputs == other.inputs and self.outputs == other.outputs


@dataclass
class CanvasNode:
    """A node placed on a canvas: a typed contract plus how to run it."""
    name: str
    contract: TypeContract
    run: Callable[[Any], Any] | None = None   # (input) -> output; None = declared
    cost: float = 0.0
    provenance: str = ""                        # reuse | authored | mutated | tool
    handle: str = ""


@dataclass
class SolutionSlot:
    """One step of the matrix: a required contract and the ordered candidates that
    can fill it (preferred first, then type-compatible fallbacks = the waterfall)."""
    slot_id: str
    contract: TypeContract
    candidates: list = field(default_factory=list)   # ordered CanvasNodes

    def add_candidate(self, node: CanvasNode, *, prefer: bool = False) -> None:
        """Add a candidate.  It MUST be contract-compatible with the slot — an
        incompatible node cannot be a drop-in fallback and is refused."""
        if not node.contract.compatible_with(self.contract):
            raise ValueError(
                f"node {node.name!r} contract {node.contract} is not compatible "
                f"with slot {self.slot_id!r} contract {self.contract}")
        if prefer:
            self.candidates.insert(0, node)
        else:
            self.candidates.append(node)

    @property
    def preferred(self) -> "CanvasNode | None":
        return self.candidates[0] if self.candidates else None


@dataclass
class Canvas:
    """A canvas: an ordered matrix of solution slots, of one of the two kinds."""
    canvas_id: str
    kind: str = "solution"
    slots: list = field(default_factory=list)   # ordered SolutionSlots
    provenance: str = ""

    def __post_init__(self):
        if self.kind not in CANVAS_KINDS:
            raise ValueError(f"canvas kind must be one of {CANVAS_KINDS}")

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
    error: str = ""


@dataclass
class MatrixExecution:
    canvas_id: str
    ok: bool
    outcomes: list = field(default_factory=list)
    output: Any = None

    def waterfalls_used(self) -> int:
        """How many slots succeeded on a FALLBACK rather than the preferred node —
        the robustness the matrix bought."""
        return sum(1 for o in self.outcomes if o.ok and o.tried and
                   o.chosen != o.tried[0])


def execute_matrix(canvas: Canvas, initial_input: Any = None) -> MatrixExecution:
    """Execute a solution canvas as a matrix of solutions, waterfalling per slot.

    For each slot in order, try candidates preferred-first; the first that runs
    without raising fills the slot, and its output feeds the next slot.  A slot
    fails only if EVERY compatible candidate fails; that fails the execution but
    records exactly what was tried, so a caller can repair the slot."""
    outcomes: list[SlotOutcome] = []
    value = initial_input
    for slot in canvas.slots:
        oc = SlotOutcome(slot_id=slot.slot_id)
        filled = False
        for node in slot.candidates:
            oc.tried.append(node.name)
            if node.run is None:
                # a declared-but-not-runnable node cannot fill a slot at run time
                oc.error = f"{node.name} is declared, not runnable"
                continue
            try:
                value = node.run(value)
                oc.chosen, oc.ok, filled = node.name, True, True
                break
            except Exception as exc:                            # noqa: BLE001
                oc.error = f"{node.name}: {exc!r}"
                continue
        outcomes.append(oc)
        if not filled:
            return MatrixExecution(canvas.canvas_id, ok=False, outcomes=outcomes,
                                   output=None)
    return MatrixExecution(canvas.canvas_id, ok=True, outcomes=outcomes,
                           output=value)


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
    s1.add_candidate(CanvasNode("xgboost", df2model,
                                run=lambda x: "model:xgb", provenance="reuse"))
    s1.add_candidate(CanvasNode("lightgbm", df2model,
                                run=lambda x: "model:lgbm", provenance="reuse"))
    s2 = SolutionSlot("predict", model2pred)
    s2.add_candidate(CanvasNode("predict", model2pred,
                                run=lambda m: [1, 0, 1]))
    canvas.add_slot(s1); canvas.add_slot(s2)

    check("a_solution_canvas_holds_ordered_typed_slots",
          canvas.kind == "solution" and len(canvas.slots) == 2
          and canvas.is_executable(),
          "two type-connected slots (DataFrame->Model->Predictions) are executable")

    check("a_slot_carries_a_preferred_node_and_compatible_fallbacks",
          s1.preferred.name == "xgboost" and len(s1.candidates) == 2,
          "the fit slot prefers xgboost with lightgbm as a compatible fallback")

    # an incompatible fallback is refused
    refused = False
    try:
        s1.add_candidate(CanvasNode("bad", model2pred, run=lambda x: x))
    except ValueError:
        refused = True
    check("an_incompatible_fallback_is_refused",
          refused,
          "a node whose contract does not match the slot cannot be a drop-in")

    # execution waterfalls: preferred fails -> compatible fallback runs
    canvas2 = Canvas("c2", kind="solution")
    sf = SolutionSlot("fit", df2model)
    def boom(x):
        raise RuntimeError("xgboost node crashed")
    sf.add_candidate(CanvasNode("xgboost", df2model, run=boom))
    sf.add_candidate(CanvasNode("lightgbm", df2model, run=lambda x: "model:lgbm"))
    sp = SolutionSlot("predict", model2pred)
    sp.add_candidate(CanvasNode("predict", model2pred, run=lambda m: "preds"))
    canvas2.add_slot(sf); canvas2.add_slot(sp)
    ex = execute_matrix(canvas2, initial_input="df")
    check("execution_waterfalls_to_a_compatible_node_when_the_preferred_fails",
          ex.ok and ex.output == "preds" and ex.waterfalls_used() == 1
          and ex.outcomes[0].chosen == "lightgbm"
          and ex.outcomes[0].tried == ["xgboost", "lightgbm"],
          "step 2's preferred node crashed; the matrix fell back to the "
          "compatible lightgbm and the solution still completed")

    # a slot fails only if ALL candidates fail
    canvas3 = Canvas("c3", kind="solution")
    sbad = SolutionSlot("fit", df2model)
    sbad.add_candidate(CanvasNode("a", df2model, run=boom))
    sbad.add_candidate(CanvasNode("b", df2model, run=boom))
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
          "the widest step offers 2 interchangeable nodes")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "canvas_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
