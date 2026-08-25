"""Memory-recall regimes — muscle memory, generalized to any store.

"This looks like one we've solved before" is a whole family of next-action decision
answers, and they all share one shape: consult a memory store keyed on the
current situation/signature, and if it recalls something strong enough, propose
it.  Rather than hard-wire one store, this module provides a **generic recall
adapter** so any backend plugs in behind the same contract — the archived-list
muscle memory (``list_intelligence``), a solved-route index (replay the exact
winning arrangement of a near-identical task), or an analogy store (transfer a
mechanism from a structurally similar task).

Each factory returns a ``(Knowledge) -> NextActionProposal | None`` resolver.  The
backend is injected, so these are testable with a stub and swappable for the real
stores without touching the loop.  The honesty rule holds: memory recall ORDERS a
move to try; the fold oracle still decides, and a blind lane always runs
alongside so recall never becomes destiny.
"""

from __future__ import annotations

from typing import Any, Callable

from ...strings.knowledge import Knowledge
from ...loop.moves import answer, move

# A recall function reads Knowledge and returns a list of (display, kind, key,
# strength) recalled moves, or an empty list to pass.
RecallFn = Callable[[Knowledge], list]


def make_recall_resolver(name: str, recall_fn: RecallFn, *,
                         category: str = "fingerprint_recall",
                         confidence: float = 0.85):
    """Wrap any recall backend as a memory regime.  ``recall_fn`` returns a list
    of dicts ``{"key", "kind", "display", "strength"}`` (strongest first) or an
    empty list."""
    def resolve(k: Knowledge):
        try:
            recalled = recall_fn(k) or []
        except Exception:                                       # noqa: BLE001
            return None
        if not recalled:
            return None
        moves = [move(r.get("kind", "add_node"), r["key"],
                      mechanism=f"recalled: {r.get('display', r['key'])} "
                      f"(strength {r.get('strength', 0)})",
                      support=float(r.get("strength", 0)), confidence=confidence)
                 for r in recalled[:3]]
        return answer(name, category, moves, confidence)
    return resolve


def make_solved_route_replay(name: str,
                             query_fn: Callable[[Any], "dict | None"], *,
                             min_similarity: float = 0.9):
    """Replay the exact winning arrangement of a near-identical solved task.

    ``query_fn(signature)`` returns ``{"route": [...steps...], "similarity": f}``
    or None.  Only replays when similarity clears ``min_similarity`` — a loose
    match is an analogy, not a replay, and is left to a softer regime.
    """
    def resolve(k: Knowledge):
        signature = k.fact("signature")
        if signature is None:
            return None
        try:
            hit = query_fn(signature)
        except Exception:                                       # noqa: BLE001
            return None
        if not hit or hit.get("similarity", 0.0) < min_similarity:
            return None
        route = hit.get("route") or []
        if not route:
            return None
        moves = [move("add_node", str(step),
                      mechanism=f"replay of a solved task "
                      f"(similarity {hit['similarity']:.2f})", confidence=0.9)
                 for step in route]
        return answer(name, "fingerprint_recall", moves, 0.9,
                      detail="solved_route_replay")
    return resolve


def make_analogy_transfer(name: str,
                          neighbours_fn: Callable[[Knowledge], list]):
    """Softer than replay: retrieve structurally similar tasks and propose their
    winning mechanisms as *priors to try*, flagged as analogy (they must still be
    verified against the current task).  ``neighbours_fn`` returns a list of
    ``{"method", "similarity"}``."""
    def resolve(k: Knowledge):
        try:
            neighbours = neighbours_fn(k) or []
        except Exception:                                       # noqa: BLE001
            return None
        if not neighbours:
            return None
        moves = [move("add_node", n["method"],
                      mechanism=f"analogy from a similar task "
                      f"(sim {n.get('similarity', 0):.2f}) — verify before trust",
                      support=float(n.get("similarity", 0)), confidence=0.6)
                 for n in neighbours[:3]]
        return answer(name, "embedding_similarity", moves, 0.6,
                      detail="analogy_transfer")
    return resolve
