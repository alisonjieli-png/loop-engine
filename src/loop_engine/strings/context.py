"""Context views — a bounded, deliberate projection of what a resolver sees.

The state may reference far more than any one resolver should receive (v3 §6): a
``ContextView`` is the scoped projection built for one resolver invocation, and
it states what was shown, what was deliberately hidden, and under which policy.
This is what makes blind and informed lanes a *deliberate, receipted choice*
rather than an accident — the same decision can be asked blind (goal and graph
interface only), memory-informed, research-informed, failure-only, anti-memory
(suppress popular priors), or sealed-evaluator-safe, and the synthesis can then
see which conclusions survive across context conditions.

Each view carries a manifest digest of what it included, so a decision is
replayable and an audit can see the blindness was intentional.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from ..strings.knowledge import Knowledge

# The knowledge fields a policy may include.
_ALL_FIELDS = ("goal", "graph_summary", "results", "memory_refs", "blueprints",
               "open_obligations", "facts", "frame")

# Context policies (v3 §5.1), each declaring which fields it exposes and any
# special flags.  Not the full twenty — the load-bearing ones the loop uses.
CONTEXT_POLICIES: dict[str, dict] = {
    "blind": {"include": ("goal", "graph_summary"),
              "note": "goal and graph interface only — no results or memory"},
    "goal_only": {"include": ("goal",), "note": "goal and output contract only"},
    "task_only": {"include": ("goal", "frame"),
                  "note": "the task, no history"},
    "graph_only": {"include": ("goal", "graph_summary", "open_obligations"),
                   "note": "graph summary without history"},
    "memory_blind": {"include": ("goal", "graph_summary", "results", "facts",
                                 "open_obligations"),
                     "note": "current state, no historical memory"},
    "memory_informed": {"include": _ALL_FIELDS,
                        "note": "similar cases and priors included"},
    "failure_only": {"include": ("goal", "graph_summary", "results"),
                     "flags": {"failures_only": True},
                     "note": "failure evidence without incumbent rationale"},
    "research_informed": {"include": ("goal", "graph_summary", "facts",
                                      "memory_refs"),
                          "flags": {"research_handles": True},
                          "note": "external research handles included"},
    "capability_blind": {"include": ("goal", "graph_summary", "facts",
                                     "open_obligations"),
                         "flags": {"hide_catalog": True},
                         "note": "ask what should exist without the registry"},
    "contradiction_focused": {"include": ("goal", "open_obligations"),
                              "flags": {"contradictions_only": True},
                              "note": "only incompatible evidence"},
    "anti_memory": {"include": ("goal", "graph_summary", "facts",
                                "open_obligations"),
                    "flags": {"suppress_priors": True},
                    "note": "suppress popular historical priors"},
    "sealed_evaluator_safe": {"include": _ALL_FIELDS,
                              "flags": {"exclude_sealed": True},
                              "note": "excludes protected evaluator/holdout data"},
    "counterfactual": {"include": _ALL_FIELDS,
                       "flags": {"flip_assumption": True},
                       "note": "assumes the incumbent hypothesis is wrong"},
    "fully_informed": {"include": _ALL_FIELDS,
                       "note": "broad architect view within limits"},
}

# Fact-key prefixes treated as sealed/holdout and excluded under the safe policy.
_SEALED_PREFIXES = ("sealed", "holdout", "answer_", "test_label")


@dataclass
class ContextView:
    policy: str
    included: dict = field(default_factory=dict)
    hidden: tuple[str, ...] = ()
    flags: dict = field(default_factory=dict)
    note: str = ""
    token_budget: int | None = None
    manifest_digest: str = ""

    def to_dict(self) -> dict:
        return {"record_type": "context_view/v1", "policy": self.policy,
                "included_fields": sorted(self.included),
                "hidden_fields": list(self.hidden), "flags": self.flags,
                "note": self.note, "token_budget": self.token_budget,
                "manifest_digest": self.manifest_digest,
                "the_rule": ("a context view states what it showed AND what it "
                             "deliberately hid — blindness is a receipted choice, "
                             "never an accident")}


def _summarize(field_name: str, value: Any) -> Any:
    """A compact, hashable projection of a field for the view."""
    if isinstance(value, dict):
        return {"keys": sorted(value)[:32], "n": len(value)}
    if isinstance(value, (list, tuple)):
        return {"n": len(value), "sample": [str(v) for v in list(value)[:6]]}
    return value


def build_view(knowledge: Knowledge, policy: str, *,
               token_budget: int | None = None) -> ContextView:
    """Project a Knowledge into a bounded ContextView under a named policy."""
    spec = CONTEXT_POLICIES.get(policy)
    if spec is None:
        raise ValueError(f"unknown context policy {policy!r}; expected one of "
                         f"{sorted(CONTEXT_POLICIES)}")
    include = set(spec["include"])
    flags = dict(spec.get("flags", {}))
    included: dict[str, Any] = {}

    field_values = {
        "goal": knowledge.goal, "graph_summary": knowledge.graph_summary,
        "results": knowledge.results, "memory_refs": knowledge.memory_refs,
        "blueprints": knowledge.blueprints,
        "open_obligations": knowledge.open_obligations,
        "facts": dict(knowledge.facts),
        "frame": knowledge.frame.as_dict()}

    for name in _ALL_FIELDS:
        if name not in include:
            continue
        value = field_values[name]
        # anti_memory suppresses memory even where the field is nominally in.
        if flags.get("suppress_priors") and name in ("memory_refs",
                                                     "blueprints"):
            continue
        # sealed-safe strips protected fact keys.
        if name == "facts" and flags.get("exclude_sealed"):
            value = {k: v for k, v in value.items()
                     if not any(k.lower().startswith(p)
                                for p in _SEALED_PREFIXES)}
        included[name] = _summarize(name, value)

    hidden = tuple(f for f in _ALL_FIELDS if f not in included)
    manifest = hashlib.sha256(
        json.dumps({"policy": policy, "included": {k: included[k]
                                                   for k in sorted(included)},
                    "flags": flags}, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]
    return ContextView(policy=policy, included=included, hidden=hidden,
                       flags=flags, note=spec.get("note", ""),
                       token_budget=token_budget, manifest_digest=manifest)


def build_lanes(knowledge: Knowledge, policies) -> list[ContextView]:
    """Build several context views over the same knowledge — one blind lane, one
    informed lane, etc. — so a decision can be asked across context conditions
    and the stable conclusions identified."""
    return [build_view(knowledge, p) for p in policies]


# ---------------------------------------------------------------------------
# Self-test — deterministic.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    k = Knowledge(goal="predict churn", graph_summary="tabular baseline",
                  results=(1, 2, 3), memory_refs=("solved-route-store",),
                  facts={"has_model": True, "sealed_holdout_score": 0.99,
                         "imbalanced": True})

    blind = build_view(k, "blind")
    check("a_blind_view_hides_memory_and_results",
          "goal" in blind.included and "graph_summary" in blind.included
          and "memory_refs" in blind.hidden and "results" in blind.hidden
          and "facts" in blind.hidden,
          "a blind view exposes only goal and graph interface; results, memory, "
          "and facts are recorded as deliberately hidden")

    informed = build_view(k, "memory_informed")
    check("a_memory_informed_view_includes_memory_and_results",
          "memory_refs" in informed.included and "results" in informed.included
          and "facts" in informed.included,
          "the memory-informed view exposes memory refs, results, and facts")

    anti = build_view(k, "anti_memory")
    check("anti_memory_suppresses_priors_even_when_present",
          "memory_refs" in anti.hidden and "facts" in anti.included,
          "anti-memory keeps facts but suppresses the memory-refs priors, so a "
          "lane can be run deliberately free of historical popularity")

    safe = build_view(k, "sealed_evaluator_safe")
    check("sealed_safe_strips_protected_holdout_facts",
          "sealed_holdout_score" not in safe.included["facts"]["keys"]
          and "has_model" in safe.included["facts"]["keys"],
          "the sealed-evaluator-safe view strips the sealed_holdout_score fact "
          "while keeping ordinary facts — protected evaluator data never leaks "
          "into a resolver's context")

    bad = False
    try:
        build_view(k, "telepathy")
    except ValueError:
        bad = True
    check("an_unknown_policy_is_refused",
          bad, "an unknown context policy is refused rather than silently "
          "returning everything")

    lanes = build_lanes(k, ("blind", "memory_informed", "failure_only"))
    b2 = build_view(k, "blind")
    check("lanes_build_and_views_are_deterministic",
          len(lanes) == 3 and lanes[0].manifest_digest == b2.manifest_digest,
          "several context lanes build over one knowledge, and the same policy "
          "always yields the identical manifest digest — replayable")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "context_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
