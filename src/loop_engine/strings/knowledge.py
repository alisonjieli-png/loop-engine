"""Knowledge — "what I presently know", as references and summaries.

The loop's input is everything the practitioner knows at this moment, but it does
NOT have to be full context: it is goal + graph summary + results so far + handles
to memory stores and folders + suggested blueprints + the still-open obligations,
plus a ``context_level`` that lets the same loop run blind or deeply informed and
an ``AskFrame`` of persona/prompt dimensions.  Detail is pulled from the
references only when a decision needs it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..strings.frame import AskFrame

# Named context levels, cheapest/blindest first.  A resolver may key off this to
# decide how much of the references to actually load.
CONTEXT_LEVELS = ("blind", "task_only", "graph_only", "memory_informed",
                  "research_grounded", "full_architect")


@dataclass
class Knowledge:
    goal: str = ""
    graph_summary: str = ""                       # nodes, inputs/outputs, state
    results: tuple[Any, ...] = ()                 # results of runs/tests so far
    memory_refs: tuple[str, ...] = ()             # handles: stores, folders, logs
    blueprints: tuple[str, ...] = ()              # suggested starting points
    open_obligations: tuple[str, ...] = ()        # what still needs deciding
    facts: dict = field(default_factory=dict)     # data/task profile the regimes read
    context_level: str = "memory_informed"
    frame: AskFrame = field(default_factory=AskFrame)

    def fact(self, name: str, default=None):
        """Read one profile fact (``has_model``, ``imbalanced``, ``text_cols``,
        ``split_verified``, ``near_perfect``, …).  Regimes branch on these."""
        return self.facts.get(name, default)

    def as_signals(self) -> dict:
        """A compact, hashable view for the governor / resolvers.  A stable id
        keyed on the material state keeps a decision replayable."""
        facts_key = tuple(sorted((k, repr(v)) for k, v in self.facts.items()))
        key = (self.goal, self.graph_summary, self.results,
               self.open_obligations, facts_key, self.context_level)
        from ..ontology.records import StableIdentityRequest, stable_content_id
        return {"id": stable_content_id(StableIdentityRequest(
                    "decision-signals", key, digest_length=16, separator=":")),
                "goal": self.goal, "graph_summary": self.graph_summary,
                "n_results": len(self.results),
                "open_obligations": list(self.open_obligations),
                "context_level": self.context_level}
