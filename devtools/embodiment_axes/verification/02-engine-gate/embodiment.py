"""Verification 2: structural gates the engine can run without redoing work.

Every check here is cheap because it needs no second pass over the world. It
asks whether the answer has the shape the task promised, whether it refers to
things that exist, whether the run actually finished its reading, and whether
the answer agrees with the run's own carried state.

That last one matters and is often skipped: an answer that contradicts the
state the same run carried is wrong no matter what the state says.

What this cannot catch is an error that is consistent with itself all the way
down, which is exactly what an arithmetic slip in the accumulator looks like.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))

REQUIRED = ("net", "unbalanced", "largest")


def verify(world, outcome: dict) -> dict:
    answer = outcome.get("answer")
    if not isinstance(answer, dict):
        return {"accepted": False, "reason": "no answer object", "reads": 0}
    missing = [key for key in REQUIRED if key not in answer]
    if missing:
        return {"accepted": False, "reason": f"missing {missing}", "reads": 0}
    if not isinstance(answer.get("net"), int):
        return {"accepted": False, "reason": "net is not an integer", "reads": 0}
    if answer.get("largest") not in world.shard_ids:
        return {"accepted": False,
                "reason": f"largest {answer.get('largest')!r} is not a shard",
                "reads": 0}
    read = set(world.reads)
    unread = [name for name in world.shard_ids if name not in read]
    if unread:
        return {"accepted": False,
                "reason": f"{len(unread)} shards never read", "reads": 0}
    carry = answer.get("carry") or {}
    accounts = carry.get("accounts")
    if isinstance(accounts, dict):
        implied = sum(1 for value in accounts.values() if value != 0)
        if implied != answer.get("unbalanced"):
            return {"accepted": False,
                    "reason": "unbalanced disagrees with the carried accounts",
                    "reads": 0}
        if sum(accounts.values()) != answer.get("net"):
            return {"accepted": False,
                    "reason": "net disagrees with the carried accounts",
                    "reads": 0}
    return {"accepted": True, "reason": "", "reads": 0}


ARM = {
    "name": "engine_gate",
    "checks": "shape, referential validity, reading completeness, and "
              "agreement with the run's own carried state",
    "verify": verify,
}


def self_check() -> None:
    from world import World
    world = World.build(3, seed=2)
    for name in world.shard_ids:
        world.read_shard(name)
    good = {"net": 0, "unbalanced": 0, "largest": world.shard_ids[0],
            "carry": {"accounts": {"cash": 0}}}
    assert verify(world, {"answer": good, "stopped": "answered"})["accepted"]
    bad = dict(good, largest="s999999")
    assert not verify(world, {"answer": bad, "stopped": "answered"})["accepted"]
    short = World.build(3, seed=2)
    assert not verify(short, {"answer": good, "stopped": "answered"})["accepted"]
    skewed = {"net": 5, "unbalanced": 0, "largest": world.shard_ids[0],
              "carry": {"accounts": {"cash": 0}}}
    assert not verify(world, {"answer": skewed,
                              "stopped": "answered"})["accepted"]
    print("engine_gate self-check: ok")


if __name__ == "__main__":
    self_check()
