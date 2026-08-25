"""Model-backed regime factories — councils, single model, research.

These are the ``llm_single`` / ``persona_salted`` / ``llm_council`` / ``research``
paths.  They are *factories*, not registered by default, because their cost and
their tokens are real: the caller injects a proposer (a function that actually
calls a model) and registers the regime with a live client.  Keeping them out of
the default registry is what makes most loop steps free — a model is reached only
when a caller has wired one in and the escalation governor decides it is worth
the cost.

Each factory renders the AskFrame preamble into the ask, so persona / system
prompt / salts flow to the model, and returns a ``(Knowledge) -> NextActionProposal``
resolver.  The council factory digests independent members by summing confidence
per distinct move across members (each member is one independent group), so a
lone loud member cannot carry a move — the same dependence-aware discipline the
planner uses, in miniature; a caller may pass a richer ``aggregate`` (e.g. the
Wilson-lower-bound planner) instead.
"""

from __future__ import annotations

from typing import Any, Callable

from ...strings.knowledge import Knowledge
from ...loop.moves import answer, move

# A proposer turns (knowledge, prompt_preamble) into a list of move dicts
# {"kind", "key", "confidence"}.  The caller's proposer is where the model call
# happens.
Proposer = Callable[[Knowledge, str], list]


def make_single_model_regime(name: str, proposer: Proposer, *,
                             category: str = "llm_single",
                             cost: float = 8.0, confidence: float = 0.75):
    """One model proposes the next move(s), framed by the AskFrame."""
    def resolve(k: Knowledge):
        preamble = k.frame.render_prompt_preamble()
        try:
            proposed = proposer(k, preamble) or []
        except Exception:                                       # noqa: BLE001
            return None
        if not proposed:
            return None
        moves = [move(p.get("kind", "add_node"), p["key"],
                      mechanism=p.get("mechanism", ""),
                      confidence=float(p.get("confidence", confidence)))
                 for p in proposed[:5]]
        conf = max((m.confidence for m in moves), default=confidence)
        return answer(name, category, moves, conf)
    # attach cost so register_regime can pass it through
    resolve._regime_cost = cost                                 # type: ignore
    return resolve


def _digest_members(members_moves: list) -> list:
    """Sum confidence per distinct move across independent members; return the
    strongest first.  Each member counts once for a move regardless of how many
    times it repeated it — one member is one independent endorsement."""
    agg: dict[tuple[str, str], dict] = {}
    for member in members_moves:
        seen = set()
        for p in member or []:
            key = (p.get("kind", "add_node"), p["key"])
            if key in seen:
                continue
            seen.add(key)
            row = agg.setdefault(key, {"support": 0.0, "conf": 0.0,
                                       "mechanism": p.get("mechanism", "")})
            row["support"] += 1
            row["conf"] = max(row["conf"], float(p.get("confidence", 0.5)))
    ordered = sorted(agg.items(), key=lambda kv: (-kv[1]["support"],
                                                  -kv[1]["conf"], kv[0]))
    return [{"kind": k[0], "key": k[1], "support": v["support"],
             "conf": v["conf"], "mechanism": v["mechanism"]}
            for k, v in ordered]


def make_council_regime(name: str, members: list, *,
                        cost: float = 40.0, min_members: int = 2,
                        aggregate: "Callable | None" = None):
    """A council of independent model members proposes; their answers are
    digested into one move slate.  ``members`` is a list of proposers.  A caller
    may pass ``aggregate`` (e.g. the Wilson-lower-bound planner) to replace the
    default confidence-summing digest."""
    def resolve(k: Knowledge):
        preamble = k.frame.render_prompt_preamble()
        members_moves = []
        for proposer in members:
            try:
                members_moves.append(proposer(k, preamble) or [])
            except Exception:                                   # noqa: BLE001
                members_moves.append([])
        answered = [m for m in members_moves if m]
        if len(answered) < min_members:
            return None
        digested = (aggregate(members_moves) if aggregate is not None
                    else _digest_members(members_moves))
        if not digested:
            return None
        n = max(1, len(members))
        moves = [move(d["kind"], d["key"], mechanism=d.get("mechanism", ""),
                      support=d.get("support", 0),
                      confidence=min(1.0, d.get("support", 1) / n))
                 for d in digested[:5]]
        conf = max((m.confidence for m in moves), default=0.5)
        return answer(name, "llm_council", moves, conf,
                      detail=f"{len(answered)} of {len(members)} members answered")
    resolve._regime_cost = cost                                 # type: ignore
    return resolve


def make_research_regime(name: str,
                         gap_fn: Callable[[Knowledge], "str | None"], *,
                         cost: float = 30.0):
    """research: when a capability gap is present, answer 'do_research' for it —
    the loop then routes that through research_to_capability (a nominated
    package/method is verified before it is usable)."""
    def resolve(k: Knowledge):
        gap = gap_fn(k)
        if not gap:
            return None
        return answer(name, "research", [
            move("do_research", f"capability_gap:{gap}",
                 mechanism="no registered capability satisfies this need — "
                 "research candidates, then verify them", confidence=0.7)], 0.7)
    resolve._regime_cost = cost                                 # type: ignore
    return resolve
