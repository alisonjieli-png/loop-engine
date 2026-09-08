"""Verification 3: recompute the answer from the world, ignoring the run.

The verifier reads every shard itself and does its own arithmetic on the raw
rows. It never looks at the carried state, the transcript, or anything the run
produced except the final answer it is judging. That independence is the whole
value: a mistake the run made cannot propagate into the check, because the
check shares no work with it.

It is also the expensive one. It costs a full second pass over the world, and
the family harness records those reads so the price is visible next to the
detection rate rather than argued about.

This is deliberately not the world's own oracle. It is a second implementation
of the same specification, written from the task text, so that a defect in one
arithmetic is not automatically present in the other.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))

ROW = re.compile(r"^([a-z]+),(DR|CR),(\d+)$", re.M)


def recompute(world) -> dict:
    """Read every shard and compute the answer from the rendered rows."""
    net = 0
    per_account: dict = {}
    best_shard, best_abs = "", -1
    for shard_id in world.shard_ids:
        rendered = world.read_shard(shard_id)
        shard_net = 0
        for account, side, amount in ROW.findall(rendered):
            signed = int(amount) if side == "DR" else -int(amount)
            net += signed
            shard_net += signed
            per_account[account] = per_account.get(account, 0) + signed
        if abs(shard_net) > best_abs or (abs(shard_net) == best_abs
                                         and shard_id < best_shard):
            best_abs, best_shard = abs(shard_net), shard_id
    return {"net": net,
            "unbalanced": sum(1 for value in per_account.values() if value != 0),
            "largest": best_shard}


def verify(world, outcome: dict) -> dict:
    answer = outcome.get("answer")
    if not isinstance(answer, dict):
        return {"accepted": False, "reason": "no answer object", "reads": 0}
    before = len(world.reads)
    truth = recompute(world)
    reads = len(world.reads) - before
    wrong = [key for key in truth if answer.get(key) != truth[key]]
    if wrong:
        return {"accepted": False,
                "reason": f"recomputed disagreement on {wrong}", "reads": reads}
    return {"accepted": True, "reason": "", "reads": reads}


ARM = {
    "name": "independent_recompute",
    "checks": "the answer against a second implementation reading the world "
              "again from scratch",
    "verify": verify,
}


def self_check() -> None:
    from world import World, oracle
    world = World.build(9, seed=8)
    truth = oracle(world)
    mine = recompute(World.build(9, seed=8))
    assert mine == truth, (mine, truth)
    assert verify(World.build(9, seed=8),
                  {"answer": dict(truth), "stopped": "answered"})["accepted"]
    off = dict(truth, net=truth["net"] + 1)
    result = verify(World.build(9, seed=8),
                    {"answer": off, "stopped": "answered"})
    assert not result["accepted"] and result["reads"] == 9, result
    print("independent_recompute self-check: ok")


if __name__ == "__main__":
    self_check()
