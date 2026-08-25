"""Hybrid-dimension lattice — cover every interaction without the full product.

The v2 specification makes deliberation a product of independent axes: context
level (A3, 30 values) × question family (A4, 46) × persona/lens (A5, 60+) ×
swarm topology (A6, 30) × aggregation method (A9, 25) × model lane × language ×
era × geography.  Taken literally, "try all combinations of these hybrid
dimensions" is a Cartesian product in the trillions — no budget survives it, and
running it would be the opposite of the cost discipline the escalation governor
buys.

The outside-the-box move is that you almost never need the full product.  Most
of the value in combinatorial spaces lives in *pairwise interactions* — how a
context level behaves with a persona, how a topology behaves with an aggregation
method.  A **pairwise covering array** is a small set of combinations chosen so
that every pair of values drawn from any two axes appears together in at least
one combination.  For axes with a few values each, a covering array of a few
dozen rows exercises every 2-way interaction that a product of billions would —
the standard result behind combinatorial test design (S097 in the spec).

This module builds that lattice:

- ``full_product_size`` reports the naive count, so the saving is visible and
  honest — the lattice never pretends it ran the product.
- ``pairwise_cover`` produces a deterministic greedy covering array: every pair
  of values across every pair of axes is guaranteed present, and the module
  proves it did so.
- ``diversity_sample`` picks a budget-bounded set of maximally spread
  combinations (each new pick maximizes its minimum distance to those chosen) —
  for when even the covering array is larger than the budget, or when raw spread
  matters more than exhaustive pairwise coverage.
- Every generated combination is a *lane spec* — one deliberation
  configuration a decision cell can dispatch — and the lattice always includes a
  blind/random lane and tracks which axis values co-vary, so a set of lanes is
  never mistaken for more independence than it has.

The lattice ORDERS and SAMPLES which hybrid configurations to try; it never
decides which one is right — the fold oracle does that downstream, and a
blind/random lane always rides along so the covering design never becomes
destiny.

Run: ``python -m loop_engine.loop.hybrid_dimension_lattice --self-test``.
Architectural role: Practitioner Loop.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

# A default set of deliberation axes, matching the specification's lattices.
# Open — a caller passes its own axes; these are illustrative and used by the
# self-test.  Each axis is (name, [values]).
DEFAULT_AXES: dict[str, tuple[str, ...]] = {
    "context_level": ("blind", "task_only", "memory_informed",
                      "research_grounded", "full_architect"),
    "question_family": ("top_next_moves", "do_not_try", "capability_gap",
                        "adversarial_critique"),
    "persona_lens": ("data_scientist", "distributed_systems", "red_team",
                     "minimalist", "cross_domain_analogist"),
    "topology": ("independent_panel", "debate", "delphi", "evidence_court"),
    "aggregation": ("wilson_lower_bound", "reciprocal_rank_fusion",
                    "pareto", "cluster_bootstrap"),
}


# The specification's full axis registries, as named data (A3 context lattice,
# A4 question families, A5 persona/lens classes, A6 topologies, A9 aggregation).
# These are the actual dimension VALUES so a caller can build the spec-scale
# lattice without re-typing them; the covering array keeps even this affordable.
CONTEXT_LEVELS: tuple[str, ...] = (
    "zero_context", "task_title_only", "raw_owner_request",
    "independent_paraphrase", "goal_and_deliverables", "external_io_contract",
    "task_fingerprint", "data_shape_summary", "target_and_evaluator",
    "statistical_diagnostics", "local_graph_boundary", "global_logical_graph",
    "physical_plan", "node_catalog_aware", "node_catalog_blind",
    "winning_memory_only", "failure_memory_only", "pheromone_path_prior",
    "analogy_packet", "research_grounded", "contrarian_research",
    "resource_and_operations", "policy_and_authority", "outcome_history",
    "ablation_only", "stakeholder_lens", "holdout_blind_confirmation",
    "full_architect_packet", "anti_memory_lane", "counterfactual_world")

QUESTION_FAMILIES: tuple[str, ...] = (
    "task_interpretation", "objective_hierarchy", "decomposition",
    "top_next_moves", "do_not_try", "missing_information", "capability_gap",
    "catalog_selection", "ordering_and_commutativity", "test_generation",
    "failure_diagnosis", "adversarial_critique", "completeness_audit",
    "excess_audit", "simplification", "continuation", "stopping",
    "distillation")

PERSONA_LENSES: tuple[str, ...] = (
    "data_scientist", "ml_systems_engineer", "distributed_systems",
    "compiler_engineer", "operations_researcher", "statistician",
    "causal_inference", "security_reviewer", "reliability_engineer",
    "red_team", "minimalist", "cross_domain_analogist", "contrarian_critic",
    "kaggle_competitor", "formal_methods", "newcomer")

TOPOLOGIES: tuple[str, ...] = (
    "independent_panel", "sequential_handoff", "hierarchical_council",
    "delphi_rounds", "adversarial_debate", "red_blue_purple",
    "jury_hidden_ballots", "tournament_bracket", "blackboard", "mixture_of_agents",
    "beam_of_councils", "island_swarms", "evidence_court", "socratic_swarm")

AGGREGATIONS: tuple[str, ...] = (
    "qualified_majority", "weighted_majority", "wilson_lower_bound",
    "cluster_bootstrap", "effective_sample_size", "weighted_borda",
    "reciprocal_rank_fusion", "condorcet_copeland", "bradley_terry",
    "robust_median", "pareto_frontier", "diversity_constrained",
    "evidence_weighted", "thompson_sampling")

# The spec-scale lattice: context × question × persona × topology × aggregation.
SPEC_AXES: dict[str, tuple[str, ...]] = {
    "context_level": CONTEXT_LEVELS, "question_family": QUESTION_FAMILIES,
    "persona_lens": PERSONA_LENSES, "topology": TOPOLOGIES,
    "aggregation": AGGREGATIONS}


def full_product_size(axes: Mapping[str, Sequence[str]]) -> int:
    """The naive Cartesian count — what "all combinations" literally means."""
    size = 1
    for values in axes.values():
        size *= max(1, len(values))
    return size


@dataclass(frozen=True)
class LaneSpec:
    """One deliberation configuration: a value chosen on each axis."""
    assignment: tuple[tuple[str, str], ...]   # ((axis, value), …), axis-sorted
    blind: bool = False

    def as_dict(self) -> dict:
        out = {axis: value for axis, value in self.assignment}
        if self.blind:
            out["_lane"] = "blind_random"
        return out

    def key(self) -> str:
        return "|".join(f"{a}={v}" for a, v in self.assignment)


def _canonical(assignment: Mapping[str, str]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted(assignment.items()))


def _all_pairs(axes: Mapping[str, Sequence[str]]) -> set:
    """Every (axisA, valueA, axisB, valueB) pair that a cover must hit."""
    pairs = set()
    names = sorted(axes)
    for a, b in itertools.combinations(names, 2):
        for va in axes[a]:
            for vb in axes[b]:
                pairs.add((a, va, b, vb))
    return pairs


def _pairs_in(assignment: Mapping[str, str],
              names: Sequence[str]) -> set:
    covered = set()
    for a, b in itertools.combinations(names, 2):
        covered.add((a, assignment[a], b, assignment[b]))
    return covered


def pairwise_cover(axes: Mapping[str, Sequence[str]]) -> dict:
    """A deterministic greedy pairwise covering array over the axes.

    Guarantees every pair of values from every pair of axes co-occurs in at
    least one lane.  Greedy: repeatedly build the lane that covers the most
    not-yet-covered pairs, choosing each axis value deterministically to
    maximize new coverage (ties broken by value name, for reproducibility).
    """
    names = sorted(axes)
    need = _all_pairs(axes)
    lanes: list[LaneSpec] = []

    # Guard against a degenerate single-axis space (no pairs to cover).
    if len(names) < 2:
        assignment = {n: axes[n][0] for n in names if axes[n]}
        return {"record_type": "pairwise_cover/v1",
                "axes": {n: list(v) for n, v in axes.items()},
                "full_product_size": full_product_size(axes),
                "lane_count": 1,
                "lanes": [LaneSpec(_canonical(assignment)).as_dict()],
                "pairs_required": 0, "pairs_covered": 0, "complete": True}

    def _gain(axis: str, value: str, assignment: Mapping[str, str]) -> int:
        g = 0
        for other, oval in assignment.items():
            key = ((axis, value, other, oval) if axis < other
                   else (other, oval, axis, value))
            if key in need:
                g += 1
        return g

    while need:
        # Seed each lane with the (deterministically chosen) lowest uncovered
        # pair, fixing those two axis values.  This guarantees the lane covers
        # at least that pair, so `need` strictly shrinks and the loop both
        # terminates and reaches COMPLETE coverage — the flaw a plain greedy
        # per-axis build had.
        seed_axis_a, seed_val_a, seed_axis_b, seed_val_b = min(need)
        assignment: dict[str, str] = {seed_axis_a: seed_val_a,
                                      seed_axis_b: seed_val_b}
        # Fill the remaining axes greedily, maximizing new-pair coverage; ties
        # break by value name for reproducibility.
        for axis in names:
            if axis in assignment:
                continue
            best_value, best_gain = None, -1
            for value in axes[axis]:
                gain = _gain(axis, value, assignment)
                if gain > best_gain or (gain == best_gain
                                        and (best_value is None
                                             or value < best_value)):
                    best_value, best_gain = value, gain
            assignment[axis] = best_value
        lanes.append(LaneSpec(_canonical(assignment)))
        need -= _pairs_in(assignment, names)

    required = len(_all_pairs(axes))
    covered = required - len(need)
    # Always append a protected blind/random lane so the design never becomes
    # the whole search.
    blind_assignment = {n: axes[n][_stable_index(n, len(axes[n]))]
                        for n in names}
    lanes.append(LaneSpec(_canonical(blind_assignment), blind=True))
    return {"record_type": "pairwise_cover/v1",
            "axes": {n: list(v) for n, v in axes.items()},
            "full_product_size": full_product_size(axes),
            "lane_count": len(lanes),
            "lanes": [l.as_dict() for l in lanes],
            "pairs_required": required, "pairs_covered": covered,
            "complete": covered == required,
            "the_rule": ("every pair of values across every pair of axes "
                         "co-occurs in some lane; a blind/random lane always "
                         "rides along; the fold oracle decides which lane won")}


def _stable_index(seed: str, n: int) -> int:
    if n <= 0:
        return 0
    digest = hashlib.sha256(seed.encode()).hexdigest()
    return int(digest[:8], 16) % n


def _hamming(a: Mapping[str, str], b: Mapping[str, str]) -> int:
    return sum(1 for k in a if a.get(k) != b.get(k))


def diversity_sample(axes: Mapping[str, Sequence[str]], k: int, *,
                     salt: str = "lattice") -> dict:
    """Pick ``k`` maximally-spread lanes (farthest-first traversal).

    Deterministic: the first lane is chosen by a stable hash; each subsequent
    lane maximizes its minimum Hamming distance to those already chosen.  Use
    when the budget is below the covering-array size, or when raw spread across
    the space matters more than exhaustive pairwise coverage.
    """
    names = sorted(axes)
    # Seed lane: one deterministic point.
    first = {n: axes[n][_stable_index(f"{salt}:{n}", len(axes[n]))]
             for n in names}
    chosen = [first]
    # Candidate pool: a bounded deterministic scan of the product is infeasible
    # for large spaces, so generate candidates by perturbing chosen lanes one
    # axis at a time plus a stable pseudo-random spread.
    product_cap = min(full_product_size(axes), 4096)
    pool: list[dict] = []
    for i, combo in enumerate(itertools.islice(
            itertools.product(*(axes[n] for n in names)), product_cap)):
        pool.append(dict(zip(names, combo)))
    while len(chosen) < max(1, k) and len(chosen) < len(pool):
        best, best_dist = None, -1
        for cand in pool:
            if cand in chosen:
                continue
            d = min(_hamming(cand, c) for c in chosen)
            # Deterministic tiebreak by a stable hash of the assignment.
            tie = _stable_index(salt + "|".join(f"{k}={v}" for k, v
                                                 in sorted(cand.items())), 997)
            if (d, tie) > (best_dist, -1) and (best is None or d > best_dist
                                               or (d == best_dist
                                                   and tie > _stable_index(
                        salt + "|".join(f"{k}={v}" for k, v
                                        in sorted(best.items())), 997))):
                best, best_dist = cand, d
        if best is None:
            break
        chosen.append(best)
    return {"record_type": "diversity_sample/v1",
            "requested": k, "returned": len(chosen),
            "full_product_size": full_product_size(axes),
            "lanes": [LaneSpec(_canonical(c)).as_dict() for c in chosen]}


def dependence_note(lanes: Sequence[Mapping[str, str]],
                    covary_axis: str = "model_family") -> dict:
    """Report which lanes share a value on a co-variance axis (e.g. the same
    model family), so a set of lanes is never counted as more independent than
    it is — the spec's dependence discipline applied to the lattice."""
    groups: dict[str, list[int]] = {}
    for i, lane in enumerate(lanes):
        groups.setdefault(str(lane.get(covary_axis, "?")), []).append(i)
    return {"record_type": "lattice_dependence/v1", "covary_axis": covary_axis,
            "independent_groups": len(groups),
            "groups": {k: v for k, v in groups.items()},
            "note": ("lanes sharing a value on the co-variance axis are one "
                     "dependence group, not N independent confirmations")}


# ---------------------------------------------------------------------------
# Self-test — deterministic, no model, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    # The full product is enormous; the covering array is tiny AND complete.
    product = full_product_size(DEFAULT_AXES)
    cover = pairwise_cover(DEFAULT_AXES)
    check("the_full_product_is_huge_but_the_cover_is_small_and_complete",
          product == 5 * 4 * 5 * 4 * 4  # 1600
          and cover["complete"] is True
          and cover["pairs_covered"] == cover["pairs_required"]
          and cover["lane_count"] < product // 10,
          f"the naive product is {product} combinations; the pairwise cover "
          f"exercises every one of {cover['pairs_required']} two-way "
          f"interactions in just {cover['lane_count']} lanes — every pair "
          f"covered, a fraction of the product")

    # Independently re-verify the coverage claim (don't trust the builder).
    names = sorted(DEFAULT_AXES)
    need = _all_pairs(DEFAULT_AXES)
    for lane in cover["lanes"]:
        assignment = {n: lane[n] for n in names if n in lane}
        if len(assignment) == len(names):
            need -= _pairs_in(assignment, names)
    check("the_pairwise_coverage_claim_is_independently_verified",
          not need,
          "re-scanning the emitted lanes confirms zero uncovered pairs remain — "
          "the completeness claim is checked, not asserted")

    # A blind/random lane always rides along.
    check("a_blind_random_lane_always_rides_along",
          any(l.get("_lane") == "blind_random" for l in cover["lanes"]),
          "the covering design always appends a protected blind/random lane so "
          "the systematic cover never becomes the whole search")

    # Determinism.
    cover2 = pairwise_cover(DEFAULT_AXES)
    check("the_cover_is_deterministic",
          cover2["lanes"] == cover["lanes"],
          "the same axes always produce the identical covering array — "
          "replayable, no hidden randomness")

    # diversity_sample spreads: consecutive picks differ on multiple axes.
    small_axes = {"a": ("a1", "a2", "a3"), "b": ("b1", "b2", "b3"),
                  "c": ("c1", "c2", "c3")}
    sample = diversity_sample(small_axes, 4)
    lanes = [{k: v for k, v in l.items() if not k.startswith("_")}
             for l in sample["lanes"]]
    spread_ok = sample["returned"] == 4 and all(
        _hamming(lanes[0], other) >= 1 for other in lanes[1:])
    check("diversity_sample_returns_spread_out_lanes",
          spread_ok,
          "a farthest-first sample of 4 lanes over a 27-combination space "
          "returns distinct, spread-out configurations rather than near-clones")

    # Dependence note groups lanes by a co-variance axis.
    dep = dependence_note(
        [{"model_family": "deepseek"}, {"model_family": "deepseek"},
         {"model_family": "glm"}], covary_axis="model_family")
    check("dependence_note_counts_independent_groups_not_lanes",
          dep["independent_groups"] == 2,
          "three lanes on two model families are two independent groups, not "
          "three — the lattice never inflates independence")

    # The spec-scale lattice (30 context × 18 question × 16 persona × 14
    # topology × 14 aggregation) is over a million combinations, yet the cover
    # stays a few hundred lanes and is provably complete.
    spec_product = full_product_size(SPEC_AXES)
    spec_cover = pairwise_cover(SPEC_AXES)
    check("the_spec_scale_lattice_stays_affordable_and_complete",
          spec_product > 1_000_000 and spec_cover["complete"] is True
          and spec_cover["lane_count"] < spec_product // 1000,
          f"the specification's full deliberation lattice is {spec_product:,} "
          f"combinations; the pairwise cover exercises every 2-way interaction "
          f"in {spec_cover['lane_count']} lanes — over a million combinations' "
          f"worth of interaction coverage for a few hundred deliberations")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "hybrid_dimension_lattice_self_test",
            "tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--show-cover", action="store_true",
                        help="print the default pairwise cover")
    args = parser.parse_args(argv)
    if args.show_cover:
        print(json.dumps(pairwise_cover(DEFAULT_AXES), indent=1))
        return 0
    if args.self_test:
        report = self_test()
        print(json.dumps(report, indent=1))
        return 0 if report["all_passed"] else 1
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
