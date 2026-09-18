"""Walk a grid over one node's parameters, score every cell, and accept only an honest gain.

The node is the text conformance resolver. Its parameters are the apply
threshold and two catalog confidences. The grid is declared, every cell is
counted as represented, applicable, proposed, dispatched, and evaluated,
the frozen suite is split by case digest into a training side and a held
out side, and a cell replaces the baseline only when it gains on training
cases without losing a held-out case.

Run:
    python3 examples/27_optimize_a_node_grid/run.py

No network, no external service, no model calls.
"""
from __future__ import annotations

import json
from pathlib import Path

from loop_engine import LoopLedger
from loop_engine.code_nodes.service_endpoints import solver_from_spec as _solver_from_spec
from loop_engine.core.configuration_optimizer import AcceptancePolicy, ParameterAxis, ParameterSpace, optimize
from loop_engine.core.evaluation_suite import EvaluationSuite, evaluate_suite
from loop_engine.core.node_grid import GridLedger, NodeGrid, NodeParameter, cell_id
from loop_engine.loop.encapsulate import as_practitioner_loop

HERE = Path(__file__).resolve().parent / "inputs"


def load() -> tuple[EvaluationSuite, dict, dict]:
    suite = EvaluationSuite.from_dict(json.loads((HERE / "suite.json").read_text("utf-8")))
    solver = json.loads((HERE / "solver.json").read_text("utf-8"))
    space = json.loads((HERE / "space.json").read_text("utf-8"))
    return suite, solver, space


def walk(_inputs=None) -> dict:
    suite, solver_spec, space_record = load()
    baseline_solver, baseline_id = _solver_from_spec(solver_spec)
    baseline = evaluate_suite(suite, baseline_solver, solver_id=baseline_id)
    grid = NodeGrid("conform.name", tuple(
        NodeParameter(item["name"], "choice", tuple(item["values"])) for item in space_record["axes"]))
    ledger = GridLedger(grid)
    space = ParameterSpace(tuple(ParameterAxis(item["name"], tuple(item["values"])) for item in space_record["axes"]))
    train, holdout = suite.split(space_record["holdout_fraction"], salt=space_record["salt"])

    stages: dict = {}

    def evaluate(cell, part, solver_id):
        if cell != space.baseline and stages.get(cell_id(cell)) is None:
            stages[cell_id(cell)] = ledger.advance(cell, "proposed")
            stages[cell_id(cell)] = ledger.advance(cell, "dispatched")
        solver, _ = _solver_from_spec(solver_spec, cell)
        report = evaluate_suite(part, solver, solver_id=solver_id)
        if cell != space.baseline and part.population_digest == holdout.population_digest:
            ledger.advance(cell, "evaluated")
        return report

    result = optimize(space, train, holdout, evaluate, strategy=space_record["strategy"],
                      policy=AcceptancePolicy(**space_record.get("acceptance", {})))
    for stage in ("proposed", "dispatched", "evaluated"):
        ledger.advance(space.baseline, stage)
    if result.accepted:
        ledger.advance(result.best_cell, "verified")
    return {"baseline": baseline.to_dict(), "result": result.to_dict(), "grid": grid.to_dict(),
            "counts": ledger.counts(), "train_cases": len(train.cases), "holdout_cases": len(holdout.cases)}


def main() -> int:
    ledger = LoopLedger()
    outcome = as_practitioner_loop("optimize the conformance node grid", walk, ledger=ledger)
    value = outcome["value"]
    baseline, result, counts = value["baseline"], value["result"], value["counts"]
    print("OPTIMIZE A NODE GRID")
    print(f"loop: {outcome['loop_id']}  ledger events: {len(ledger.events)}")
    print()
    print("BASELINE ON THE FULL SUITE")
    print(f"  solver {baseline['solver_id']}: passed {baseline['passed']} of {baseline['denominator']}")
    for item in baseline["failures"]:
        print(f"    failed {item['case_id']}: observed {item['observed']!r}")
    print()
    print("GRID")
    print(f"  node {value['grid']['node_id']}  represented {value['grid']['represented']}  "
          f"train cases {value['train_cases']}  holdout cases {value['holdout_cases']}")
    print("SEARCH")
    print(f"  strategy {result['strategy']}  represented {result['represented']}  dispatched {result['dispatched']}  "
          f"evaluated {result['evaluated']}  exhaustive {result['exhaustive']}")
    for item in result["comparisons"]:
        cell = json.dumps(item["cell"], sort_keys=True)
        print(f"    {cell}: train net {item.get('train_net')}  holdout net {item.get('holdout_net')}  "
              f"qualifies {item.get('qualifies')}")
    print("DECISION")
    print(f"  accepted {result['accepted']}  best cell {json.dumps(result['best_cell'], sort_keys=True)}")
    print(f"  {result['reason']}")
    print("STAGE COUNTS")
    print("  " + "  ".join(f"{stage} {counts[stage]}" for stage in
                          ("represented", "applicable", "proposed", "dispatched", "evaluated", "verified", "promoted")))
    print(f"  exhaustive coverage {counts['exhaustive_coverage']}  (promotion needs an independent review, not this run)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
