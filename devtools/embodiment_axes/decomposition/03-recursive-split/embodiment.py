"""Decomposition 3: keep splitting until a piece is small enough, then merge.

The group count is not chosen. A piece larger than a threshold is halved and
each half is handled the same way, so the shape of the tree follows the size
of the work. That is the difference from the fixed split: one number that
means something about the work, instead of one number that means something
about the machine.

The merge has to be associative for this to be safe at all, because partial
results are combined pairwise up the tree rather than once at the end. That
property is checked in `merge.py`, not assumed here.

What it costs is a call per leaf beyond the units themselves, the same way the
fixed split does, plus the tree being deeper than a flat split for the same
leaf count.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from merge import empty, finalize, merge
from port import ContextWindowExceeded, Port, extract_json
from step_loop import STATE_KEYS, render

#: A piece at or under this many units is worked directly rather than split.
DEFAULT_LEAF_SIZE = 8
#: A guard, so a bad threshold cannot build an unbounded tree.
MAX_DEPTH = 16


def _work_leaf(world, port, shard_ids, label, max_steps) -> tuple:
    """Fold one leaf's units into its own accumulator. Returns (state, calls)."""
    state = {"net": 0, "accounts": {}, "best_shard": "", "best_abs": -1}
    observation = ""
    cursor = 0
    calls = 0
    while calls < max_steps:
        next_shard = shard_ids[cursor] if cursor < len(shard_ids) else "none"
        prompt = render(world, state, next_shard,
                        max(len(shard_ids) - cursor, 0), observation)
        try:
            reply = port.ask(f"{label}.{calls}", prompt)
        except ContextWindowExceeded:
            return state, calls, "context_window_exceeded"
        calls += 1
        decision = extract_json(reply) or {}
        patch = decision.get("carry")
        if isinstance(patch, dict):
            state = {key: patch.get(key, state[key]) for key in STATE_KEYS}
        if decision.get("action") == "read":
            shard_id = decision.get("shard")
            observation = world.read_shard(shard_id)
            if cursor < len(shard_ids) and shard_id == shard_ids[cursor]:
                cursor += 1
            continue
        return state, calls, ""
    return state, calls, "step_ceiling"


def _split(world, port, shard_ids, label, leaf_size, depth, budget) -> dict:
    if len(shard_ids) <= leaf_size or depth >= MAX_DEPTH:
        state, calls, error = _work_leaf(world, port, shard_ids, label,
                                         budget["left"])
        budget["left"] -= calls
        budget["leaves"] += 1
        budget["longest"] = max(budget["longest"], calls)
        budget["depth"] = max(budget["depth"], depth)
        if error:
            budget["errors"].append(f"{label}: {error}")
        return state
    middle = len(shard_ids) // 2
    left = _split(world, port, shard_ids[:middle], label + "L", leaf_size,
                  depth + 1, budget)
    right = _split(world, port, shard_ids[middle:], label + "R", leaf_size,
                   depth + 1, budget)
    return merge(left, right)


def run(world, port: Port, max_steps: int = 6000,
        leaf_size: int = DEFAULT_LEAF_SIZE) -> dict:
    budget = {"left": max_steps, "leaves": 0, "longest": 0, "depth": 0,
              "errors": []}
    state = _split(world, port, world.shard_ids, "n", max(1, leaf_size), 0,
                   budget)
    return {"answer": finalize(state), "state": state,
            "stopped": "answered" if not budget["errors"] else "partial",
            "groups": budget["leaves"], "candidates": 1,
            "longest_group_calls": budget["longest"],
            "tree_depth": budget["depth"],
            "detail": f"{budget['leaves']} leaves at depth "
                      f"{budget['depth']}, longest chain "
                      f"{budget['longest']} calls"}


ARM = {"name": "recursive_split",
       "splits_into": "halves, until a piece is under a threshold",
       "parallelism": "one leaf per worker", "run": run}


def self_check() -> None:
    from world import World, grade

    for leaf_size in (1, 3, 8, 64):
        world = World.build(24, seed=2)
        outcome = run(world, Port(backend="fixture"), leaf_size=leaf_size)
        assert grade(world, outcome["answer"])["solved"], (leaf_size, outcome)
        assert sorted(world.reads) == sorted(world.shard_ids), leaf_size

    # a smaller leaf makes a deeper tree with more, shorter chains
    small = run(World.build(24, seed=2), Port(backend="fixture"), leaf_size=2)
    large = run(World.build(24, seed=2), Port(backend="fixture"), leaf_size=24)
    assert small["groups"] > large["groups"], (small["groups"],
                                               large["groups"])
    assert small["tree_depth"] > large["tree_depth"]
    assert small["longest_group_calls"] < large["longest_group_calls"]
    assert large["groups"] == 1, "a threshold above the work must not split"

    # the depth guard holds even at a threshold that asks for an endless tree
    guarded = run(World.build(24, seed=2), Port(backend="fixture"),
                  leaf_size=0)
    assert grade(World.build(24, seed=2), guarded["answer"])["solved"]
    assert guarded["tree_depth"] <= 16, guarded["tree_depth"]
    print(f"recursive_split self-check: ok "
          f"({small['groups']} leaves at depth {small['tree_depth']} for "
          f"leaf_size 2, {large['groups']} for 24)")


if __name__ == "__main__":
    self_check()
