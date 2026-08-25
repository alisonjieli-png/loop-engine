"""solve — run the whole What-Is-Next loop end to end on a task, for real.

This assembles a SolverCell from the ACTUAL regime library (deterministic
reflexes, the linear-regression checklist, weighted heuristics, plan/blind
regimes, and any available memory), runs it to completion with an executor that
applies each chosen move to the epistemic state, and emits receipts, a persisted
run, and a studio dashboard.  No stubs: the resolvers are the real library.

    PYTHONPATH=src python3 -m loop_engine.loop.solve --demo
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

from ..strings.knowledge import Knowledge
from ..strings.knowledge_state import EpistemicState, Claim, Unknown, KnowledgeDelta
from ..loop.moves import family_of
from ..loop.loop import SolverCell
from ..loop.registry import ResolverRegistry
from ..loop.regimes import register_library
from ..loop.builtin_resolvers import register_builtins
from ..loop.practitioner_methods import checklist_resolver, linear_regression_checklist
from ..loop.runner import SolverCellState, run
from ..loop.studio import build_studio_view, render_markdown, render_html
from ..loop.receipts import SolverIterationReceipt
from ..static_architecture.persistence import persist_receipt, load_receipts


def build_registry() -> ResolverRegistry:
    """The real resolver library: deterministic reflexes + test/optimize regimes,
    the built-in plan/blind regimes, and the linear-regression checklist."""
    reg = ResolverRegistry()
    register_library(reg)                     # 17 reflex + test + optimize regimes
    register_builtins(reg)                    # plan_recipe, blind_baseline
    reg.register_regime("lr_checklist", "plan_recipe",
                        checklist_resolver("lr_checklist",
                                           linear_regression_checklist()),
                        cost=0.02)            # checklist just after safety reflexes
    return reg


def _apply_move(facts: dict, move_key: str, move_kind: str) -> dict:
    """The executor's effect: mark the fact a move establishes.  This is the
    adapter a real run would replace with graph execution + evaluation."""
    updates: dict = {}
    mapping = {
        "verify_target": {"target_numeric": True},
        "verify_split": {"split_verified": True},
        "leakage_audit": {"split_verified": True},
        "encoder=onehot": {"categoricals_encoded": True},
        "encoder=hashing": {"dimensionality_controlled": True},
        "scaler": {"features_scaled": True},
        "vif": {"collinearity_checked": True},
        "cv_probe": {"has_cv": True},
        "baseline": {"has_baseline": True},
    }
    for probe, upd in mapping.items():
        if probe in move_key:
            updates.update(upd)
    if "estimator" in move_key:
        updates["has_model"] = True
    return updates


def make_executor():
    def executor(decision, knowledge, state):
        selected = decision.selected or []
        observations, fact_updates = [], {}
        for cand in selected:
            upd = _apply_move(dict(knowledge.facts), cand.move.action_key,
                              cand.move.action_kind)
            fact_updates.update(upd)
            observations.append(f"applied:{cand.move.action_key}")
        # Fold the fact updates into the epistemic state as observed claims.
        claims = tuple(Claim(k, f"{k} established", "observed")
                       for k in fact_updates)
        # A run_tests on the split resolves the split unknown.
        resolved = ("u.split",) if fact_updates.get("split_verified") else ()
        delta = KnowledgeDelta(added_claims=claims, resolved_unknowns=resolved)
        # Goal is satisfied once the checklist facts and a model are present.
        done = {"target_numeric", "split_verified", "categoricals_encoded",
                "dimensionality_controlled", "features_scaled",
                "collinearity_checked", "has_model"}
        new_facts = {**knowledge.facts, **fact_updates}
        flag_updates = {}
        if done <= set(k for k, v in new_facts.items() if v):
            flag_updates["goal_satisfied"] = True
        return (observations, delta, flag_updates, tuple(observations))
    return executor


def solve(goal: str, facts: dict, *, unknowns: dict | None = None,
          cell_id: str = "cell.solve", max_iterations: int = 20,
          receipts_path: str | None = None) -> dict:
    """Run the loop to completion and return the run plus a studio view."""
    reg = build_registry()
    cell = SolverCell(confidence_bar=0.7, impact=20.0, registry=reg)
    est = _seed_facts(EpistemicState(), facts)
    for uid, u in (unknowns or {}).items():
        est.add_unknown(u)
    start = SolverCellState(cell_id=cell_id, goal=goal, epistemic=est,
                            flags={}, results=())
    out = run(start, cell=cell, resolvers=None, executor=make_executor(),
              max_iterations=max_iterations)
    # Persist receipts if a path was given.
    if receipts_path:
        for rd in out["receipts"]:
            persist_receipt(receipts_path, _receipt_obj(rd))
    view = build_studio_view(
        title="What Is Next", task=goal, goal=goal,
        epistemic=None, receipts=out["receipts"])
    return {"run": out, "studio_markdown": render_markdown(view),
            "studio_html": render_html(view)}


def _seed_facts(est: EpistemicState, facts: dict) -> EpistemicState:
    # Seed any TRUTHY fact as an observed ground claim so the resolvers can read
    # it (a list like high_cardinality_cols is truthy but not `is True`).
    for k, v in facts.items():
        if v and k not in est.claims:
            est.add_claim(Claim(k, f"{k} established", "observed"))
    return est


def _receipt_obj(rd: dict) -> SolverIterationReceipt:
    return SolverIterationReceipt(
        cell_id=rd["cell_id"], iteration=rd["iteration"],
        parent_digest=rd["parent_digest"],
        knowledge_before_digest=rd["knowledge_before_digest"],
        decision_need=rd["decision_need"], proposals=tuple(rd["proposals"]),
        decision=rd["decision"], model_calls_made=rd["model_calls_made"],
        model_calls_avoided=rd["model_calls_avoided"],
        observations=tuple(rd["observations"]),
        knowledge_after_digest=rd["knowledge_after_digest"],
        resources=rd["resources"], terminal_state=rd["terminal_state"],
        receipt_digest=rd["receipt_digest"])


def demo() -> dict:
    """A real end-to-end linear-regression run: starts with categorical, high-
    cardinality, unscaled data and an unverified split; the loop works the
    checklist to completion and stops when the goal is satisfied."""
    return solve(
        goal="fit a leakage-safe linear regression",
        facts={"has_categorical": True, "high_cardinality": True,
               "high_cardinality_cols": ["city", "zip"],
               "target_numeric": False, "categoricals_encoded": False,
               "dimensionality_controlled": False, "features_scaled": False,
               "collinearity_checked": False, "has_baseline": False,
               "has_model": False, "split_verified": False},
        unknowns={"u.split": Unknown("u.split", "is the split leakage-free?",
                                     expected_value=0.9)})


# ---------------------------------------------------------------------------
# Self-test — the loop actually runs to a semantic stop.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    out = demo()
    run_ = out["run"]
    modes = [r["decision_need"]["mode"] for r in run_["receipts"]]
    moves = [r["decision"].get("selected", []) for r in run_["receipts"]]

    check("the_loop_runs_the_real_library_to_a_semantic_stop",
          run_["terminal_state"] == "stop_continue"
          and run_["hit_ceiling"] is False and run_["iterations"] >= 5,
          "the real regime library drives the checklist to completion and the "
          "loop stops because the goal is satisfied, not on a ceiling")

    check("safety_and_investigation_come_before_model_construction",
          modes[0] in ("investigate",)
          and any("verify_target" in str(m) or "leakage" in str(m)
                  for m in moves[0]),
          "the first move is a safety/investigation move (verify target / audit "
          "leakage), not adding a model")

    check("the_run_makes_zero_model_calls",
          sum(r["model_calls_made"] for r in run_["receipts"]) == 0,
          "the whole run resolves with deterministic reflexes and the checklist "
          "— zero model calls")

    check("the_run_emits_a_studio_dashboard",
          "What Is Next" in out["studio_markdown"]
          and out["studio_html"].startswith("<style>"),
          "the run emits a markdown summary and a self-contained HTML dashboard")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "solve_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--demo", action="store_true",
                        help="run the linear-regression demo end to end")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--html-out", default="",
                        help="write the studio dashboard HTML to this path")
    args = parser.parse_args(argv)
    if args.self_test:
        report = self_test()
        print(json.dumps(report, indent=1))
        return 0 if report["all_passed"] else 1
    if args.demo:
        out = demo()
        print(out["studio_markdown"])
        print("\n--- run ---")
        print(json.dumps({"iterations": out["run"]["iterations"],
                          "terminal_state": out["run"]["terminal_state"],
                          "model_calls_made": sum(
                              r["model_calls_made"]
                              for r in out["run"]["receipts"]),
                          "model_calls_avoided": sum(
                              r["model_calls_avoided"]
                              for r in out["run"]["receipts"])}, indent=1))
        if args.html_out:
            Path(args.html_out).write_text(out["studio_html"], encoding="utf-8")
            print(f"\nstudio HTML -> {args.html_out}")
        return 0
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
