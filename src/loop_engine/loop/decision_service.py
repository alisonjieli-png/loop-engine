"""Internal next-action selection for the canonical Loop runtime.

This module does not define an operational runtime. ``DecisionService.step``
evaluates registered decision strategies, starts with the cheapest eligible
strategy, and returns a ``NextActionDecisionRecord``. The record identifies the
selected strategy, model usage, proposal, and any bounded spawned decisions.
Selection orders work to try. Verification still decides whether the work
succeeded.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from .escalation_governor import resolve_decision
from .decision_slates import Proposal, Slate
from ..strings.knowledge import Knowledge
from ..loop.moves import NextActionProposal, family_of
from ..loop.resolvers import NextActionResolver
from ..loop.registry import DEFAULT_REGISTRY, ResolverRegistry
from ..loop.decision_need import DecisionNeed

# The move kinds that mean "spawn a sub-loop" — the legacy flat name and its
# canonical family form.
_SPAWN_KINDS = frozenset({"spawn_subloop", "move.control.delegate"})


@dataclass
class NextActionDecisionRecord:
    resolved: bool
    resolver: str
    category: str
    level: int
    model_calls_made: int
    model_calls_avoided: int
    proposal: NextActionProposal | None
    spawned_loops: list["NextActionDecisionRecord"] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"record_type": "next_action_decision/v1", "resolved": self.resolved,
                "resolver": self.resolver, "category": self.category,
                "level": self.level,
                "model_calls_made": self.model_calls_made,
                "model_calls_avoided": self.model_calls_avoided,
                "proposal": self.proposal.to_dict() if self.proposal else None,
                "spawned_loops": [c.to_dict() for c in self.spawned_loops]}


@dataclass
class DecisionService:
    """Select one bounded next action inside a Practitioner Loop.

    The service may resolve with deterministic code or an authorized model
    strategy. A ``spawn_subloop`` proposal can request another Loop, but this
    service remains an internal decision strategy rather than a runtime.
    """
    confidence_bar: float = 0.7
    budget: float | None = None
    impact: float = 1.0
    exploration_rate: float = 0.0
    max_depth: int = 2
    registry: ResolverRegistry = field(default_factory=lambda: DEFAULT_REGISTRY)

    def step(self, knowledge: Knowledge, *,
             resolvers: Sequence[NextActionResolver] | None = None,
             categories=None, need: DecisionNeed | None = None,
             depth: int = 0) -> NextActionDecisionRecord:
        """Select one next action from the eligible strategies.

        An explicit resolver list takes precedence over the registry. A
        ``DecisionNeed`` limits proposals to admitted move families.
        """
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
                ans = NextActionProposal(
                    resolver=ans.resolver, category=ans.category,
                    moves=Slate("try", admitted), confidence=ans.confidence,
                    detail=ans.detail)

        resolved = ans is not None
        category = (by_name[gov.resolving_arm].category
                    if resolved and gov.resolving_arm in by_name else "")
        record = NextActionDecisionRecord(
            resolved=resolved,
            resolver=gov.resolving_arm if resolved else "",
            category=category,
            level=gov.resolving_level if resolved else -1,
            model_calls_made=gov.model_calls_made,
            model_calls_avoided=gov.model_calls_avoided, proposal=ans)

        if ans is not None and depth < self.max_depth:
            for m in ans.moves.items:
                if m.action_kind in _SPAWN_KINDS:
                    spawned = Knowledge(
                        goal=m.action_key, graph_summary=knowledge.graph_summary,
                        memory_refs=knowledge.memory_refs,
                        context_level=knowledge.context_level,
                        frame=knowledge.frame)
                    record.spawned_loops.append(
                        self.step(spawned, resolvers=resolvers,
                                  categories=categories, depth=depth + 1))
        return record


def ensemble_answers(answers: Sequence[NextActionProposal]) -> Slate:
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
