"""Task Blueprint — a prioritized, digestible opening-move sequence, as a resource.

Owner design question (2026-08-23): with ONE model call per loop, how do we stop
the practitioner from jumping straight to "how to solve it" on pass 1? A normal
model asked to select the next action may jump straight to a solution. This
blueprint performs atomic opening moves first: establish context, research,
outline, and add detail before building.

The elegant resolution — and the answer to "separate nodes vs one node":

  * Keep ONE decision node (one call per pass — elegant, auditable).
  * Make the ORDER a **resource**, not hardcoded nodes.  A ``TaskBlueprint`` is a
    named, prioritized, digestible sequence of OPENING MOVES that BIASES the
    single next-action Loop on early passes: pass 1 biases toward context, pass 2
    toward outline, and so on.  Same node, different bias per pass.

Because the sequence is a resource (stored, searchable, swappable, versioned,
learnable), different task families get different openings, and the system can
DISTILL a better opening sequence over time — exactly like any other resource.
This is more flexible than hardcoded nodes AND keeps the loop minimal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

# The kinds of opening move a task blueprint can prioritize.  Solving is LAST —
# the point is to do the atomic groundwork first.
OPENING_MOVE_KINDS = ("establish_context", "research", "outline",
                      "detail_outline", "gather_evidence", "build", "tune",
                      "verify", "deliver")

MATURITY = ("ephemeral", "candidate", "validated", "preferred")


@dataclass
class OpeningMove:
    """One prioritized, digestible step in a task blueprint."""
    kind: str
    summary: str                      # digestible one-line intent
    done_when: str = ""               # the cheap signal this move is complete
    optional: bool = False

    def __post_init__(self):
        if self.kind not in OPENING_MOVE_KINDS:
            raise ValueError(f"kind must be one of {OPENING_MOVE_KINDS}")


@dataclass
class TaskBlueprint:
    """A named, prioritized opening-move sequence — an infrastructure resource."""
    blueprint_id: str
    moves: list = field(default_factory=list)     # ordered OpeningMoves = priority
    applicability: str = "any task"
    maturity: str = "candidate"
    provenance: str = "hand_seed"

    def __post_init__(self):
        if self.maturity not in MATURITY:
            raise ValueError(f"maturity must be one of {MATURITY}")

    def next_move(self, completed_kinds: Sequence[str]) -> "OpeningMove | None":
        """The current opening move to bias toward: the first non-optional move
        whose kind is not yet completed.  Returns None when the opening sequence
        is exhausted (the loop then decides freely — build/solve territory)."""
        done = set(completed_kinds)
        for mv in self.moves:
            if mv.optional:
                continue
            if mv.kind not in done:
                return mv
        return None

    def is_exhausted(self, completed_kinds: Sequence[str]) -> bool:
        return self.next_move(completed_kinds) is None

    def digest_summary(self) -> str:
        """The digestible rendering fed into the prompt — the whole opening plan
        in a few lines so the model sees the groundwork, not just the next step."""
        return " -> ".join(f"{i+1}. {m.kind}: {m.summary}"
                           for i, m in enumerate(self.moves))

    def envelope(self):
        """As a searchable store record."""
        from ..static_architecture.store_serve import StoreRecord
        return StoreRecord(
            record_id=f"taskblueprint.{self.blueprint_id}", kind="strategy",
            title=f"opening sequence: {self.applicability}"[:80],
            body={"moves": [{"kind": m.kind, "summary": m.summary}
                            for m in self.moves],
                  "applicability": self.applicability,
                  "provenance": self.provenance},
            tags=("task_blueprint", "opening_sequence")
            + tuple(m.kind for m in self.moves),
            tier="core" if self.maturity in ("validated", "preferred")
            else "experimental")


def default_opening_sequence() -> TaskBlueprint:
    """The secret-sauce default: groundwork BEFORE solving.  Context and research
    first, then progressively-detailed outlines, THEN build/tune/verify.  This is
    what makes next-action selection use atomic opening moves instead of leaping to a
    solution."""
    return TaskBlueprint(
        blueprint_id="default.groundwork_first", maturity="preferred",
        provenance="hand_seed",
        moves=[
            OpeningMove("establish_context", "gather relevant context, packs, "
                        "and domain framing for THIS task",
                        done_when="a context view exists"),
            OpeningMove("research", "find relevant experts/questions/evidence; "
                        "generate them if the banks are empty",
                        done_when="decision support is sufficient",
                        optional=True),
            OpeningMove("outline", "produce a high-level outline of the whole "
                        "solution (broad coverage, not detail)",
                        done_when="a blueprint outline exists"),
            OpeningMove("detail_outline", "detail the active part of the outline "
                        "into atomic actions (only the near horizon)",
                        done_when="the active checkpoint is atomic"),
            OpeningMove("build", "execute the atomic actions into the solution",
                        done_when="a candidate solution exists"),
            OpeningMove("tune", "tune/optimize the candidate solution",
                        done_when="tuning budget spent or no gain",
                        optional=True),
            OpeningMove("verify", "independently verify the solution is real and "
                        "non-degenerate", done_when="an evaluation is accepted"),
        ])


def bias_next_from_blueprint(candidates: list, blueprint: TaskBlueprint,
                             completed_kinds: Sequence[str], *,
                             boost: float = 0.25):
    """Bias next-action candidates toward the blueprint's current opening
    move — WITHOUT adding a node.  A candidate whose action matches the current
    move gets an expected-value boost; if none matches, the current move is
    INJECTED as a high-value candidate.  Returns the (possibly augmented) list,
    re-sorted.  This is how one node follows a prioritized opening sequence."""
    mv = blueprint.next_move(completed_kinds)
    if mv is None:
        return candidates                       # groundwork done — decide freely
    matched = False
    for c in candidates:
        text = f"{getattr(c, 'action', '')} {getattr(c, 'kind', '')}".lower()
        if mv.kind in text or mv.kind.replace("_", " ") in text:
            c.expected_value = min(1.0, c.expected_value + boost)
            c.rationale = (getattr(c, "rationale", "")
                           + f" [opening move: {mv.kind}]")
            matched = True
    if not matched:
        from ..loop.kernel import CandidateAction
        candidates = list(candidates) + [CandidateAction(
            action=f"opening:{mv.kind}", kind="task",
            rationale=f"opening move (blueprint {blueprint.blueprint_id}): "
            f"{mv.summary}",
            expected_value=0.9, confidence=0.8, information_gain=0.7)]
    candidates.sort(key=lambda c: (-c.expected_value, -c.confidence))
    return candidates


# ---------------------------------------------------------------------------
# Self-test — deterministic, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    bp = default_opening_sequence()

    # 1. the default sequence does GROUNDWORK first — not solve.
    first = bp.next_move([])
    check("the_default_opening_move_is_context_not_solve",
          first.kind == "establish_context"
          and bp.moves[-1].kind == "verify"
          and [m.kind for m in bp.moves][:3]
          == ["establish_context", "research", "outline"],
          f"opens with {first.kind}, not 'build' — the secret sauce")

    # 2. next_move advances as moves complete, skipping optional ones.
    n1 = bp.next_move(["establish_context"])          # research is optional
    n2 = bp.next_move(["establish_context", "outline"])
    check("next_move_advances_and_skips_optional_moves",
          n1.kind == "outline" and n2.kind == "detail_outline",
          "optional 'research' is skipped; the sequence advances to outline")

    # 3. the sequence exhausts, and then the loop decides freely.
    all_done = ["establish_context", "outline", "detail_outline", "build",
                "verify"]
    check("the_opening_sequence_exhausts_then_frees_the_loop",
          bp.is_exhausted(all_done) and bp.next_move(all_done) is None,
          "after the opening moves, next-action selection is unbiased (build/solve)")

    # 4. ONE node, biased: a matching candidate is boosted; else the move is
    # injected — no new node added.
    from ..loop.kernel import CandidateAction
    cands = [CandidateAction("jump to build the model", kind="task",
                             expected_value=0.85, confidence=0.8)]
    biased = bias_next_from_blueprint(cands, bp, [])   # current move: context
    top = max(biased, key=lambda c: c.expected_value)
    check("one_node_is_biased_toward_the_opening_move_not_solving",
          top.action.startswith("opening:establish_context")
          and "jump to build" in cands[0].action,
          "with no context candidate, the context opening move is INJECTED and "
          "outranks 'jump to build' — same single node, biased order")

    # 5. a matching candidate is boosted rather than duplicated.
    cands2 = [CandidateAction("establish_context for the task", kind="task",
                              expected_value=0.6, confidence=0.7),
              CandidateAction("build the model", kind="task",
                              expected_value=0.7, confidence=0.7)]
    biased2 = bias_next_from_blueprint(cands2, bp, [])
    top2 = max(biased2, key=lambda c: c.expected_value)
    check("a_matching_candidate_is_boosted_not_duplicated",
          "establish_context" in top2.action and len(biased2) == 2
          and top2.expected_value > 0.6,
          "the existing context candidate is boosted above build; no injection")

    # 6. the blueprint is a SWAPPABLE, searchable resource.
    custom = TaskBlueprint("fast.build_first",
                           moves=[OpeningMove("build", "just build it"),
                                  OpeningMove("verify", "check it")],
                           applicability="trivial tasks")
    check("a_task_blueprint_is_a_swappable_resource",
          custom.next_move([]).kind == "build"
          and custom.envelope().record_id == "taskblueprint.fast.build_first",
          "a different task family can swap in a different opening sequence")

    # 7. searchable through the store DAG; digest is digestible.
    from ..static_architecture.store_serve import SolverStore
    store = SolverStore(core_records=[bp.envelope()])
    hit = store.search("opening sequence establish context outline",
                       kind="strategy")
    check("opening_sequences_are_findable_and_digestible",
          hit["hits"] and "establish_context" in bp.digest_summary()
          and "->" in bp.digest_summary(),
          "the loop finds an opening sequence by search; the whole plan renders "
          "in a few digestible lines for the prompt")

    # 8. closed vocabularies.
    bad = 0
    for fn in (lambda: OpeningMove("teleport", "s"),
               lambda: TaskBlueprint("x", maturity="legendary")):
        try:
            fn()
        except ValueError:
            bad += 1
    check("opening_move_kinds_and_maturity_are_closed", bad == 2,
          "the opening-move and maturity vocabularies are closed")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "task_blueprint_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
