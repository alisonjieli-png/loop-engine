"""Decomposition 2: cut the work into a fixed number of independent groups.

Each group gets its own accumulator and its own pass, and the partial results
are merged at the end. Nothing is shared while a group runs, so the groups
could execute anywhere, in any order, at the same time.

The call count goes up, not down: every group pays its own final call, so the
total is the units plus roughly one call per group. What comes down is the
longest chain, which is what wall-clock time actually follows when the groups
run at the same time. Those two columns are the trade, and they point in
opposite directions.

The other thing splitting buys is independent failure. One group failing costs
that group, not the run.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from merge import finalize, merge_all
from port import ContextWindowExceeded, Port, extract_json
from step_loop import STATE_KEYS, empty_state, render
from world import task_text

DEFAULT_GROUPS = 4


class _Group:
    """One independent slice of the world, with its own accumulator."""

    def __init__(self, world, shard_ids):
        self.world = world
        self.shard_ids = tuple(shard_ids)
        self.state = empty_state()
        self.observation = ""
        self.cursor = 0
        self.calls = 0
        self.failed = ""

    @property
    def done(self) -> bool:
        return self.cursor >= len(self.shard_ids)


def _step(group, port, label) -> bool:
    """One call for one group. Returns False when the group is finished."""
    next_shard = (group.shard_ids[group.cursor] if not group.done else "none")
    prompt = render(group.world, group.state, next_shard,
                    max(len(group.shard_ids) - group.cursor, 0),
                    group.observation)
    try:
        reply = port.ask(label, prompt)
    except ContextWindowExceeded as exc:
        group.failed = f"context_window_exceeded: {exc}"[:100]
        return False
    group.calls += 1
    decision = extract_json(reply) or {}
    patch = decision.get("carry")
    if isinstance(patch, dict):
        group.state = {key: patch.get(key, group.state[key])
                       for key in STATE_KEYS}
    if decision.get("action") == "read":
        shard_id = decision.get("shard")
        group.observation = group.world.read_shard(shard_id)
        if not group.done and shard_id == group.shard_ids[group.cursor]:
            group.cursor += 1
        return True
    return False


def run(world, port: Port, max_steps: int = 6000,
        groups: int = DEFAULT_GROUPS) -> dict:
    shard_ids = world.shard_ids
    count = max(1, min(groups, len(shard_ids) or 1))
    # Contiguous slices, so a group's identifiers stay adjacent and a reader
    # of the ledger can tell which slice a call belonged to. The remainder is
    # spread one unit at a time rather than absorbed by rounding the size up:
    # rounding up gave five or six groups when seven were asked for, and a
    # caller sizing a worker pool to the number it requested would have been
    # quietly wrong about how much parallelism it had.
    base, extra = divmod(len(shard_ids), count)
    slices, offset = [], 0
    for index in range(count):
        width = base + (1 if index < extra else 0)
        slices.append(shard_ids[offset:offset + width])
        offset += width
    slices = [chunk for chunk in slices if chunk] or [()]
    parts = [_Group(world, chunk) for chunk in slices]

    steps = 0
    for index, group in enumerate(parts):
        while steps < max_steps:
            steps += 1
            if not _step(group, port, f"g{index}.s{group.calls}"):
                break

    failed = [group for group in parts if group.failed]
    merged = merge_all([group.state for group in parts])
    answer = finalize(merged)
    longest = max((group.calls for group in parts), default=0)
    return {"answer": answer, "stopped": "answered" if not failed else "partial",
            "state": merged, "groups": len(parts), "candidates": 1,
            "longest_group_calls": longest,
            "failed_groups": len(failed),
            "detail": f"{len(parts)} groups, longest chain {longest} calls"
                      + (f", {len(failed)} failed" if failed else "")}


ARM = {"name": "fixed_split", "splits_into": "a fixed number of groups",
       "parallelism": "one group per worker", "run": run}


def self_check() -> None:
    from world import World, grade, oracle

    for groups in (1, 2, 4, 7):
        world = World.build(24, seed=2)
        port = Port(backend="fixture")
        outcome = run(world, port, groups=groups)
        assert grade(world, outcome["answer"])["solved"], (groups, outcome)
        assert outcome["groups"] == min(groups, 24), (groups, outcome)
        assert sorted(world.reads) == sorted(world.shard_ids), groups

    # more groups means more calls in total and a shorter longest chain
    one = Port(backend="fixture")
    run(World.build(24, seed=2), one, groups=1)
    many = Port(backend="fixture")
    wide = run(World.build(24, seed=2), many, groups=8)
    assert many.call_count > one.call_count, (many.call_count, one.call_count)
    assert wide["longest_group_calls"] < one.call_count
    # a group boundary must not change the answer
    assert finalize(merge_all([wide["state"]])) == oracle(
        World.build(24, seed=2))
    # the requested group count is delivered, not rounded away
    for groups in (3, 5, 7, 11):
        probe = run(World.build(24, seed=2), Port(backend="fixture"),
                    groups=groups)
        assert probe["groups"] == groups, (groups, probe["groups"])
    print(f"fixed_split self-check: ok ({one.call_count} calls in 1 group, "
          f"{many.call_count} in 8 with a {wide['longest_group_calls']}-call "
          f"longest chain)")


if __name__ == "__main__":
    self_check()
