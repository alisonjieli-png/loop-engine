"""Resolvers — the named ways to answer "select the next action".

The value of centring on the question is that the *ways to answer it* become a
clean, named taxonomy instead of ad-hoc code.  Each resolver is one path — a
deterministic rule, a followed recipe, muscle-memory recall, embedding
similarity, a small model, a hybrid, a test we must run first, research, one
model, a council, a blind take, a persona-salted take, or a custom special case —
and each declares its cost tier so the loop can try the cheapest first.

A resolver is turned into an escalation-governor arm by ``as_arm``, so the loop's
"cheapest category first" behaviour is exactly the governor's cost waterfall.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from .escalation_governor import Arm, Resolution
from .decision_slates import Slate
from ..strings.knowledge import Knowledge
from ..loop.moves import NextActionProposal, family_of

# The named categories of how to answer the question — the expert's paths.
RESOLVER_CATEGORIES = ("deterministic_rule", "plan_recipe", "fingerprint_recall",
                       "embedding_similarity", "small_model", "hybrid",
                       "test_driven", "research", "llm_single", "llm_council",
                       "blind", "persona_salted", "custom_special")

# The default cost tier for each category — cheapest paths first.  A resolver may
# override its level, but this is the waterfall: rules and memory before models,
# models before councils and research.
DEFAULT_CATEGORY_LEVEL = {
    "deterministic_rule": 0, "plan_recipe": 0, "fingerprint_recall": 1,
    "blind": 1, "embedding_similarity": 2, "small_model": 3, "hybrid": 3,
    "test_driven": 3, "persona_salted": 4, "llm_single": 4, "custom_special": 4,
    "llm_council": 6, "research": 7}
# Which categories actually spend model tokens (for the calls-avoided record).
MODEL_CATEGORIES = frozenset({"small_model", "hybrid", "persona_salted",
                              "llm_single", "llm_council", "research"})

# A resolver answers from Knowledge, or returns None to pass.
NextActionResolveFn = Callable[[Knowledge], "NextActionProposal | None"]


@dataclass(frozen=True)
class NextActionResolver:
    """One named way to answer 'select the next action'."""
    name: str
    category: str
    fn: NextActionResolveFn
    level: int | None = None          # default from category
    cost: float = 0.0
    model_calls: int = 0

    def resolved_level(self) -> int:
        return (self.level if self.level is not None
                else DEFAULT_CATEGORY_LEVEL.get(self.category, 4))

    def resolved_model_calls(self) -> int:
        return (self.model_calls if self.model_calls
                else (1 if self.category in MODEL_CATEGORIES else 0))

    def as_arm(self) -> Arm:
        """Wrap this resolver as an escalation-governor arm.  The Knowledge is
        passed through the governor's context under ``_knowledge``."""
        def resolve(signals: Mapping[str, Any],
                    ctx: Mapping[str, Any]) -> Resolution:
            knowledge = ctx.get("_knowledge")
            ans = self.fn(knowledge) if knowledge is not None else None
            if ans is None:
                return Resolution(False, abstained=True,
                                  detail=f"{self.name}: passed")
            # If a decision need is in scope, keep only the moves whose family it
            # admits.  A resolver whose moves are ALL inadmissible ABSTAINS, so
            # the governor continues to the next resolver instead of resolving to
            # an answer that the need would then empty.
            need = ctx.get("_need")
            if need is not None:
                admitted = [m for m in ans.moves.items
                            if need.admits_family(family_of(m.action_kind))]
                if not admitted:
                    return Resolution(
                        False, abstained=True,
                        detail=f"{self.name}: no move admitted by "
                        f"{getattr(need, 'mode', '?')} need")
                if len(admitted) != len(ans.moves.items):
                    ans = NextActionProposal(
                        resolver=ans.resolver, category=ans.category,
                        moves=Slate("try", admitted),
                        confidence=ans.confidence, detail=ans.detail)
            return Resolution(True, answer=ans, confidence=ans.confidence,
                              detail=f"{self.name}: {self.category}")
        return Arm(name=self.name, level=self.resolved_level(),
                   cost=self.cost, resolve=resolve,
                   model_calls=self.resolved_model_calls())
