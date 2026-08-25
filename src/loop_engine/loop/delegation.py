"""Delegation — child SolverCells, join policies, and impasse guards (v3 §15,§19).

A next move may spawn child cells: five differently-informed graph designers, a
research subloop, an adversarial council.  Delegation carries a contract (scoped
goal, knowledge projection, budget, authority, and a **return contract**), and a
child never mutates the parent's state directly — it returns observations and
proposals the parent merges explicitly.  When several children run, a **join
policy** decides how their results combine.

Recursive deliberation must not run away, so two guards are first-class: a
**depth ceiling**, and a **request fingerprint** that detects an impasse — the
same question returning with no material state change — and recommends a
different lane, broader/narrower context, escalation, or stopping.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

JOIN_POLICIES = ("all", "any", "quorum", "best_evidence", "pareto",
                 "first_valid", "ensemble", "manual")


@dataclass(frozen=True)
class SubproblemSpec:
    """The contract handed to a child cell."""
    id: str
    parent_cell_id: str
    goal: str
    scope: str = ""
    knowledge_projection: str = "memory_informed"   # a context policy name
    budget: float | None = None
    authority: str = "propose_only"
    return_contract: tuple[str, ...] = ()
    join_policy: str = "all"
    max_depth: int = 4
    depth: int = 0

    def child_allowed(self) -> bool:
        return self.depth < self.max_depth


def check_depth(spec: SubproblemSpec) -> None:
    """Raise if delegating this child would exceed the recursion ceiling."""
    if not spec.child_allowed():
        raise RuntimeError(
            f"delegation depth {spec.depth} exceeds ceiling {spec.max_depth} "
            f"for child {spec.id!r}; refusing to spawn")


def join_children(results: Sequence[Mapping[str, Any]], policy: str = "all", *,
                  quorum: int = 2) -> dict:
    """Combine child results under a join policy.  Each result is a dict with at
    least ``valid: bool`` and optionally ``evidence`` (a score) and ``value``."""
    if policy not in JOIN_POLICIES:
        raise ValueError(f"unknown join policy {policy!r}; expected "
                         f"{JOIN_POLICIES}")
    valid = [r for r in results if r.get("valid")]
    kept: list = []
    reached = False
    note = ""

    if policy == "all":
        kept, reached = list(valid), len(valid) == len(results) and bool(results)
        note = "every child returned valid"
    elif policy in ("any", "first_valid"):
        kept = valid[:1]
        reached = bool(valid)
        note = "first valid child"
    elif policy == "quorum":
        reached = len(valid) >= quorum
        kept = valid if reached else []
        note = f"{len(valid)} of {quorum} required valid"
    elif policy == "best_evidence":
        kept = ([max(valid, key=lambda r: float(r.get("evidence", 0.0)))]
                if valid else [])
        reached = bool(valid)
        note = "child with the strongest evidence"
    elif policy == "pareto":
        # Keep children not evidence-dominated by another (1-D evidence here).
        best = max((float(r.get("evidence", 0.0)) for r in valid), default=0.0)
        kept = [r for r in valid if float(r.get("evidence", 0.0)) >= best]
        reached = bool(valid)
        note = "non-dominated children by evidence"
    elif policy == "ensemble":
        kept, reached = list(valid), len(valid) >= 2
        note = "all valid children, marked for ensembling"
    elif policy == "manual":
        kept, reached = list(valid), False
        note = "deferred to human adjudication"

    return {"record_type": "child_join/v1", "policy": policy,
            "children": len(results), "valid": len(valid), "kept": kept,
            "reached": reached, "note": note,
            "the_rule": ("children return evidence and proposals; the parent "
                         "merges explicitly and the fold oracle still decides")}


def request_fingerprint(goal: str, scope: str, state_digest: str,
                        unknowns: Sequence[str],
                        context_policy: str) -> str:
    """A stable fingerprint of a decision request, for impasse and duplicate
    detection (v3 §19): same goal + scope + state + unknowns + context."""
    payload = "|".join([goal, scope, state_digest,
                        ",".join(sorted(unknowns)), context_policy])
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


@dataclass
class ImpasseGuard:
    """Detects a decision that returns with no material state change and
    recommends a way out, so recursive deliberation cannot spin forever."""
    _seen: dict = field(default_factory=dict)   # fingerprint -> state_digest

    def register(self, fingerprint: str, state_digest: str) -> dict:
        prior = self._seen.get(fingerprint)
        self._seen[fingerprint] = state_digest
        if prior is not None and prior == state_digest:
            return {"impasse": True,
                    "recommendation": ("state did not change on the same "
                                       "request — switch to a different resolver "
                                       "lane, broaden or narrow context, "
                                       "escalate, or stop"),
                    "options": ("different_lane", "broaden_context",
                                "narrow_context", "escalate", "stop")}
        return {"impasse": False, "recommendation": "proceed"}


# ---------------------------------------------------------------------------
# Self-test — deterministic.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    kids = [{"id": "A", "valid": True, "evidence": 0.9, "value": "gA"},
            {"id": "B", "valid": True, "evidence": 0.4, "value": "gB"},
            {"id": "C", "valid": False, "evidence": 0.0}]

    j_all = join_children(kids, "all")
    j_quorum = join_children(kids, "quorum", quorum=2)
    j_best = join_children(kids, "best_evidence")
    check("join_policies_combine_children_correctly",
          j_all["reached"] is False            # not all valid (C invalid)
          and j_quorum["reached"] is True      # 2 valid >= quorum 2
          and j_best["kept"][0]["id"] == "A",  # strongest evidence
          "'all' fails because C is invalid; 'quorum' of 2 is reached by A and "
          "B; 'best_evidence' keeps A (0.9) — join policies combine children "
          "under an explicit rule")

    bad = False
    try:
        join_children(kids, "telepathy")
    except ValueError:
        bad = True
    check("an_unknown_join_policy_is_refused",
          bad, "an unknown join policy is refused")

    # Depth ceiling refuses a child past max_depth.
    deep = SubproblemSpec("s1", "cell.p", "sub goal", depth=4, max_depth=4)
    refused = False
    try:
        check_depth(deep)
    except RuntimeError:
        refused = True
    ok = SubproblemSpec("s2", "cell.p", "sub goal", depth=1, max_depth=4)
    check("the_depth_ceiling_refuses_runaway_recursion",
          refused and ok.child_allowed(),
          "a child at depth 4 with a ceiling of 4 is refused; a child at depth 1 "
          "is allowed — recursive deliberation cannot run away")

    # Impasse guard: same request + unchanged state -> impasse recommendation.
    guard = ImpasseGuard()
    fp = request_fingerprint("choose model", "graph", "statedigestX",
                             ["leakage?"], "memory_informed")
    first = guard.register(fp, "statedigestX")
    repeat = guard.register(fp, "statedigestX")
    progressed = guard.register(fp, "statedigestY")
    check("the_impasse_guard_detects_a_stuck_request",
          first["impasse"] is False and repeat["impasse"] is True
          and "different resolver lane" in repeat["recommendation"]
          and progressed["impasse"] is False,
          "the same request with an unchanged state digest is flagged as an "
          "impasse with a way out; once the state changes it proceeds again")

    # Determinism of the fingerprint.
    fp2 = request_fingerprint("choose model", "graph", "statedigestX",
                              ["leakage?"], "memory_informed")
    check("the_request_fingerprint_is_deterministic",
          fp == fp2,
          "the same request always fingerprints identically, so repeats are "
          "detectable and decisions are replayable")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "delegation_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
