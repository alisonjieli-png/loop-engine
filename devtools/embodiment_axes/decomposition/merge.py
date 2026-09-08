"""Merging two partial accumulators, which is what makes splitting possible.

A design that splits work has to put it back together, and the merge is where
splitting is won or lost. This one is associative and commutative, so groups
can finish in any order and nest to any depth and the answer does not change.
That property is the reason the recursive arm can exist at all.

The tie-break is the part that catches people. Two groups can each hold a unit
with the same absolute value, and the task says the smaller identifier wins,
so the merge cannot just take whichever arrived first.
"""
from __future__ import annotations


def empty() -> dict:
    return {"net": 0, "accounts": {}, "best_shard": "", "best_abs": -1}


def merge(left: dict, right: dict) -> dict:
    left = {**empty(), **(left or {})}
    right = {**empty(), **(right or {})}
    accounts = dict(left.get("accounts") or {})
    for name, value in (right.get("accounts") or {}).items():
        accounts[name] = accounts.get(name, 0) + value
    best_shard, best_abs = left["best_shard"], left["best_abs"]
    if (right["best_abs"] > best_abs
            or (right["best_abs"] == best_abs
                and right["best_shard"]
                and (not best_shard or right["best_shard"] < best_shard))):
        best_shard, best_abs = right["best_shard"], right["best_abs"]
    return {"net": left["net"] + right["net"], "accounts": accounts,
            "best_shard": best_shard, "best_abs": best_abs}


def merge_all(parts) -> dict:
    total = empty()
    for part in parts:
        total = merge(total, part)
    return total


def finalize(state: dict) -> dict:
    accounts = state.get("accounts") or {}
    return {"net": state.get("net", 0),
            "unbalanced": sum(1 for value in accounts.values() if value != 0),
            "largest": state.get("best_shard", "")}


def self_check() -> None:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))
    from port import empty_carry, fold_prompt
    from world import World, oracle

    world = World.build(24, seed=2)
    truth = oracle(world)

    # folding everything at once, and folding in groups then merging, agree
    whole = empty_carry()
    for shard in world.shards:
        whole = fold_prompt(shard.rendered(), whole)
    assert finalize(whole) == truth, (finalize(whole), truth)

    for groups in (2, 3, 5, 24):
        parts = []
        for index in range(groups):
            part = empty_carry()
            for shard in world.shards[index::groups]:
                part = fold_prompt(shard.rendered(), part)
            parts.append(part)
        merged = merge_all(parts)
        assert finalize(merged) == truth, (groups, finalize(merged), truth)

    # order does not matter, which is what lets groups finish whenever
    parts = [dict(part) for part in parts]
    assert finalize(merge_all(parts)) == finalize(merge_all(parts[::-1]))

    # the tie-break the task specifies, not whichever arrived first
    a = {"net": 0, "accounts": {}, "best_shard": "s009", "best_abs": 500}
    b = {"net": 0, "accounts": {}, "best_shard": "s002", "best_abs": 500}
    assert merge(a, b)["best_shard"] == "s002"
    assert merge(b, a)["best_shard"] == "s002"
    print("merge self-check: ok (associative, commutative, correct tie-break)")


if __name__ == "__main__":
    self_check()
