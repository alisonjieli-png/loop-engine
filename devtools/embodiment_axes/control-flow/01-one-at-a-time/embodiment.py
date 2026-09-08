"""Control flow 1: one unit of work per call, in a fixed order.

The loop holds a cursor, reads the shard the cursor names, and sends one
observation per call. The order is decided by code, so the prompt never has to
carry a list of what is left.

This is the baseline for the family and the shape the transport family found
cheapest per prompt. Its cost is that the call count equals the horizon.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))

from port import Port
from step_loop import solve


def run(world, port: Port, max_steps: int = 4000) -> dict:
    return solve(world, port, max_steps=max_steps)


ARM = {"name": "one_at_a_time", "decides_next": "a code-held cursor",
       "calls_per_unit": "one", "run": run}


def self_check() -> None:
    from world import World, grade
    world = World.build(12, seed=9)
    port = Port(backend="fixture")
    outcome = run(world, port)
    assert grade(world, outcome["answer"])["solved"], outcome
    assert port.call_count == 13, port.call_count
    print(f"one_at_a_time self-check: ok ({port.call_count} calls for 12)")


if __name__ == "__main__":
    self_check()
