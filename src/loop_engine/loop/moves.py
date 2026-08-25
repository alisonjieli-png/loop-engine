"""Moves — what a next-action decision answer proposes to DO.

The point the framing insists on: an answer to "select the next action" is not only "add a
node."  It can be "run these tests first", "we don't know enough — gather more",
"go understand the current subgraph", "start an optimization plan", "spawn
sub-loops and ensemble them", or "stop".  A move is one such proposal; an answer
is a ranked slate of them, reusing the shared ``decision_slates`` vocabulary so
the loop speaks the same language as the planner and the council.
"""

from __future__ import annotations

from dataclasses import dataclass

from .decision_slates import Proposal, Slate

# A small, stable taxonomy of move FAMILIES with namespaced slugs, rather than
# one flat list that must anticipate every future move (the spec's §9).  A move
# kind is "move.<family>.<slug>", a novel one is "move.custom.<ns>.<slug>", and
# the legacy flat names below still work so nothing that predates the families
# breaks.
MOVE_FAMILIES = {
    "epistemic": ("inspect", "retrieve", "research", "ask", "profile", "test",
                  "verify", "reframe"),
    "constructive": ("instantiate", "configure", "add", "replace", "remove",
                     "transform", "implement", "repair"),
    "search": ("explore", "optimize", "mutate", "cross"),
    "experimental": ("ablate", "compare", "simulate", "stress"),
    "control": ("follow_plan", "branch", "delegate", "join", "merge",
                "ensemble", "promote", "rollback", "retry", "escalate", "defer"),
    "delivery": ("package", "submit", "report", "writeup", "demo", "release"),
    "terminal": ("complete", "abstain", "block", "exhaust_budget", "fail",
                 "cancel"),
}

# Legacy flat kinds, kept working, each mapped to its canonical family.slug so a
# caller can migrate at leisure and family_of() still answers.
LEGACY_MOVE_MAP = {
    "add_node": "constructive.add", "mutate": "search.mutate",
    "optimize": "search.optimize", "run_tests": "epistemic.test",
    "do_research": "epistemic.research", "gather_context": "epistemic.inspect",
    "understand_graph": "epistemic.inspect", "spawn_subloop": "control.delegate",
    "ensemble": "control.ensemble", "need_information": "epistemic.test",
    "stop": "terminal.complete", "abstain": "terminal.abstain",
}
# Back-compat export: the legacy flat names remain a valid vocabulary.
MOVE_TYPES = tuple(LEGACY_MOVE_MAP)

# Every fully-qualified namespaced kind the families define.
_NAMESPACED = frozenset(f"move.{fam}.{slug}"
                        for fam, slugs in MOVE_FAMILIES.items()
                        for slug in slugs)


def is_valid_move_kind(kind: str) -> bool:
    """A kind is valid if it is a legacy flat name, a known ``move.family.slug``,
    or a custom ``move.custom.<namespace>.<slug>`` (open extension)."""
    if kind in LEGACY_MOVE_MAP or kind in _NAMESPACED:
        return True
    parts = kind.split(".")
    return (len(parts) >= 4 and parts[0] == "move" and parts[1] == "custom"
            and all(parts))


def family_of(kind: str) -> str:
    """The family a move kind belongs to (``epistemic`` / ``constructive`` / … /
    ``custom``), for routing and reporting."""
    if kind in LEGACY_MOVE_MAP:
        return LEGACY_MOVE_MAP[kind].split(".")[0]
    parts = kind.split(".")
    if len(parts) >= 3 and parts[0] == "move":
        return parts[1]
    return "unknown"


def move(kind: str, key: str, *, mechanism: str = "", support: float = 0.0,
         confidence: float = 0.0, reasons: tuple[str, ...] = ()) -> Proposal:
    """One next-move proposal, validating its kind against the move families
    (legacy flat kinds still accepted)."""
    if not is_valid_move_kind(kind):
        raise ValueError(
            f"unknown move kind {kind!r}; expected a legacy flat kind "
            f"{MOVE_TYPES}, a move.<family>.<slug> from {sorted(MOVE_FAMILIES)}, "
            f"or a custom move.custom.<namespace>.<slug>")
    return Proposal(action_kind=kind, action_key=key, mechanism=mechanism,
                    support=support, confidence=confidence, reasons=reasons)


@dataclass
class NextActionProposal:
    """What a resolver proposes as next — a slate of moves, plus which resolver
    produced it and how confident it is."""
    resolver: str
    category: str
    moves: Slate
    confidence: float
    detail: str = ""

    def to_dict(self) -> dict:
        return {"record_type": "next_action_proposal/v1",
                "resolver": self.resolver, "category": self.category,
                "confidence": round(self.confidence, 4),
                "moves": self.moves.to_dict(), "detail": self.detail,
                "the_rule": ("an answer ORDERS what to try next — it may be run "
                             "tests / do research / add a node / spawn sub-loops "
                             "/ ensemble; the fold oracle decides what worked")}


def answer(resolver: str, category: str, moves, confidence: float,
           detail: str = "") -> NextActionProposal:
    """Build a next-action decision answer from a sequence of move proposals."""
    return NextActionProposal(resolver=resolver, category=category,
                            moves=Slate("try", list(moves)),
                            confidence=confidence, detail=detail)
