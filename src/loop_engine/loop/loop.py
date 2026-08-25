"""The loop — a Practitioner running "here is what I know; what is next?".

The Practitioner is the atomic worker.  One ``step`` asks the question once:
it turns the registered resolvers into escalation-governor arms, resolves at the
cheapest category that answers confidently enough, and returns a receipt showing
which resolver won and how many model calls were made vs avoided.  If the winning
answer proposes ``spawn_subloop`` moves, the Practitioner runs each as its own
what-is-next question (bounded by a depth ceiling) and attaches the child
receipts; ``ensemble_answers`` folds several answers into one, summing support
for moves they agree on.  Nothing here decides truth — an answer orders what to
try; the fold oracle decides what worked, and a blind/random resolver always
rides along so muscle memory never becomes destiny.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from .escalation_governor import resolve_decision
from .decision_slates import Proposal, Slate
from ..strings.knowledge import Knowledge
from ..loop.moves import WhatIsNextAnswer, family_of
from ..loop.resolvers import WhatIsNextResolver
from ..loop.registry import DEFAULT_REGISTRY, ResolverRegistry
from ..loop.decision_need import DecisionNeed

# The move kinds that mean "spawn a sub-loop" — the legacy flat name and its
# canonical family form.
_SPAWN_KINDS = frozenset({"spawn_subloop", "move.control.delegate"})


@dataclass
class StepReceipt:
    resolved: bool
    resolver: str
    category: str
    level: int
    model_calls_made: int
    model_calls_avoided: int
    answer: WhatIsNextAnswer | None
    children: list["StepReceipt"] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"record_type": "whats_next_step/v1", "resolved": self.resolved,
                "resolver": self.resolver, "category": self.category,
                "level": self.level,
                "model_calls_made": self.model_calls_made,
                "model_calls_avoided": self.model_calls_avoided,
                "answer": self.answer.to_dict() if self.answer else None,
                "children": [c.to_dict() for c in self.children]}


@dataclass
class SolverCell:
    """The smallest independently governed instance of the expert loop (v3 §2.1):
    given what is presently known, decide what is next.  It is implementation-
    independent — it may resolve with no model at all, or coordinate a council —
    and recursively composable (a resolved ``spawn_subloop`` move runs a child
    cell)."""
    confidence_bar: float = 0.7
    budget: float | None = None
    impact: float = 1.0
    exploration_rate: float = 0.0
    max_depth: int = 2
    registry: ResolverRegistry = field(default_factory=lambda: DEFAULT_REGISTRY)

    def step(self, knowledge: Knowledge, *,
             resolvers: Sequence[WhatIsNextResolver] | None = None,
             categories=None, need: DecisionNeed | None = None,
             depth: int = 0) -> StepReceipt:
        """Ask 'what is next' once.  If ``resolvers`` is given it is used
        verbatim; otherwise the cell's registry supplies them (optionally
        filtered to ``categories``).  If a ``DecisionNeed`` is given, the resolved
        answer's moves are constrained to the families the need admits — so you
        cannot answer 'add a node' to a stop decision."""
        pool = (list(resolvers) if resolvers is not None
                else self.registry.resolvers(categories=categories))
        arms = [r.as_arm() for r in pool]
        by_name = {r.name: r for r in pool}
        gov = resolve_decision(
            knowledge.as_signals(), arms, confidence_bar=self.confidence_bar,
            budget=self.budget, impact=self.impact,
            exploration_rate=self.exploration_rate,
            context={"_knowledge": knowledge, "_need": need})

        ans = gov.answer if gov.resolved else None
        # Constrain the answer to the families the decision need admits.  If the
        # winning answer proposes only inadmissible moves, it does not satisfy
        # this need.
        if ans is not None and need is not None:
            admitted = [m for m in ans.moves.items
                        if need.admits_family(family_of(m.action_kind))]
            if not admitted:
                ans = None
            elif len(admitted) != len(ans.moves.items):
                ans = WhatIsNextAnswer(
                    resolver=ans.resolver, category=ans.category,
                    moves=Slate("try", admitted), confidence=ans.confidence,
                    detail=ans.detail)

        resolved = ans is not None
        category = (by_name[gov.resolving_arm].category
                    if resolved and gov.resolving_arm in by_name else "")
        receipt = StepReceipt(
            resolved=resolved,
            resolver=gov.resolving_arm if resolved else "",
            category=category,
            level=gov.resolving_level if resolved else -1,
            model_calls_made=gov.model_calls_made,
            model_calls_avoided=gov.model_calls_avoided, answer=ans)

        if ans is not None and depth < self.max_depth:
            for m in ans.moves.items:
                if m.action_kind in _SPAWN_KINDS:
                    child = Knowledge(
                        goal=m.action_key, graph_summary=knowledge.graph_summary,
                        memory_refs=knowledge.memory_refs,
                        context_level=knowledge.context_level,
                        frame=knowledge.frame)
                    receipt.children.append(
                        self.step(child, resolvers=resolvers,
                                  categories=categories, depth=depth + 1))
        return receipt


# Transitional alias so any early caller of the working name keeps working.
Practitioner = SolverCell


def ensemble_answers(answers: Sequence[WhatIsNextAnswer]) -> Slate:
    """Fold several answers into one move slate, summing support for moves more
    than one answer proposed — the 'ensemble the ten solutions' step, kept
    honest: agreement raises order, never truth."""
    agg: dict[tuple[str, str], Proposal] = {}
    for a in answers:
        for m in a.moves.items:
            key = (m.action_kind, m.action_key)
            prior = agg.get(key)
            if prior is None:
                agg[key] = m
            else:
                agg[key] = Proposal(
                    action_kind=m.action_kind, action_key=m.action_key,
                    mechanism=m.mechanism or prior.mechanism,
                    support=prior.support + m.support,
                    confidence=max(prior.confidence, m.confidence),
                    reasons=tuple(dict.fromkeys(prior.reasons + m.reasons)))
    ordered = sorted(agg.values(), key=lambda p: (-p.support, p.action_key))
    return Slate("try", ordered)
