"""Show every verification arm the same wrong answers and score what it caught.

One clean control and four injected faults, identical across arms. The score
is the fraction of faults refused; the false positive is whether the control
was refused; the price is how many extra reads the check cost.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "shared"))
sys.path.insert(0, str(HERE))

import faults as fault_module
from port import DEFAULT_CONTEXT_LIMIT, Port
from step_loop import solve
from world import World, grade

DEFAULTS = {"horizons": [16], "seed": 11,
            "context_limit": DEFAULT_CONTEXT_LIMIT, "max_steps": 4000}


def run_family(arms, spec) -> list:
    options = {**DEFAULTS, **(spec or {})}
    rows = []
    for horizon in options["horizons"]:
        # Produce each run once, then show the same outcome to every arm, so
        # no arm is judged on a different run than another.
        produced = {}
        for name in fault_module.FAULTS:
            world = World.build(horizon, seed=options["seed"])
            port = Port(context_limit=options["context_limit"],
                        evaluator=fault_module.evaluator(name))
            outcome = solve(world, port, max_steps=options["max_steps"])
            produced[name] = (world, outcome,
                              grade(world, outcome.get("answer"))["solved"])
        for arm in arms:
            body = arm["module"].ARM
            caught, missed, reads = [], [], 0
            false_positive = False
            for name, (world, outcome, was_correct) in produced.items():
                result = body["verify"](world, outcome)
                reads += result.get("reads", 0)
                if name == "none":
                    false_positive = not result["accepted"]
                    continue
                (caught if not result["accepted"] else missed).append(name)
            rows.append({
                "family": "verification", "id": arm["id"], "arm": body["name"],
                "horizon": horizon, "checks": body["checks"],
                "faults_shown": len(fault_module.INJECTED),
                "caught": sorted(caught), "missed": sorted(missed),
                "caught_count": len(caught),
                "false_positive": false_positive,
                "verifier_reads": reads,
            })
    return rows


def summarise(rows) -> list:
    lines = []
    for row in rows:
        lines.append(
            f"  {row['arm']:24s} caught {row['caught_count']}/"
            f"{row['faults_shown']}  reads={row['verifier_reads']:4d}  "
            f"false_positive={'yes' if row['false_positive'] else 'no'}"
            + (f"  missed: {', '.join(row['missed'])}" if row["missed"] else ""))
    return lines
