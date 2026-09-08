"""Decomposition 1: do not decompose. One pass over everything.

The baseline. One state, one cursor, one order, and every unit folded into the
same accumulator. There is no merge because there is nothing to merge, and no
group can fail independently because there are no groups.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))

from port import Port
from step_loop import solve


def run(world, port: Port, max_steps: int = 6000) -> dict:
    outcome = solve(world, port, max_steps=max_steps)
    return {**outcome, "groups": 1, "candidates": 1,
            "longest_group_calls": port.call_count}


ARM = {"name": "single_pass", "splits_into": "nothing",
       "parallelism": "none", "run": run}


def self_check() -> None:
    from world import World, grade
    world = World.build(24, seed=2)
    port = Port(backend="fixture")
    outcome = run(world, port)
    assert grade(world, outcome["answer"])["solved"], outcome
    assert outcome["groups"] == 1
    print(f"single_pass self-check: ok ({port.call_count} calls)")


if __name__ == "__main__":
    self_check()
