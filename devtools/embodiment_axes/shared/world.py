"""The shared world, the task, and an oracle that is independent of every arm.

The comparison needs a task that one call cannot finish, because every earlier
measurement in this project stalled on the same problem: the tasks were small
enough that a single node solved them, so the architecture under test never
had a chance to matter.

So the facts live behind a tool. An arm cannot see a shard until it reads it,
and the answer needs every shard. Horizon is the number of shards, and it is
a dial.

The oracle computes the answer from the world's own data structures without
using anything an arm produced, and no arm may import it. That independence
is deliberate: the last time a population was checked by references that
shared assumptions with it, the check could not see three contradictions.
"""
from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Shard:
    """One unit of the world. An arm sees this only by reading it."""

    shard_id: str
    entries: tuple  # ((account, side, amount), ...)

    def rendered(self) -> str:
        """What the tool returns. This is the byte cost of one observation."""
        rows = [f"{account},{side},{amount}" for account, side, amount in self.entries]
        return f"shard {self.shard_id}\naccount,side,amount\n" + "\n".join(rows)


@dataclass
class World:
    """A deterministic set of shards behind a read tool, plus read accounting."""

    shards: tuple
    reads: list = field(default_factory=list)

    @classmethod
    def build(cls, shard_count: int, seed: int = 1, entries_per_shard: int = 6):
        rng = random.Random(seed)
        accounts = ("cash", "revenue", "payable", "equity", "expense")
        shards = []
        # The identifier is as wide as the population needs. A fixed width
        # silently truncates past its limit, and a reader matching that width
        # then resolves two different shards to one identifier.
        width = max(3, len(str(max(shard_count - 1, 0))))
        for index in range(shard_count):
            entries = tuple(
                (rng.choice(accounts), rng.choice(("DR", "CR")),
                 rng.randint(1, 999))
                for _ in range(entries_per_shard))
            shards.append(Shard(f"s{index:0{width}d}", entries))
        return cls(tuple(shards))

    @property
    def shard_ids(self) -> tuple:
        return tuple(shard.shard_id for shard in self.shards)

    def read_shard(self, shard_id: str) -> str:
        """The one tool. Every call is recorded, so re-reads are visible."""
        self.reads.append(shard_id)
        for shard in self.shards:
            if shard.shard_id == shard_id:
                return shard.rendered()
        return f"shard {shard_id} does not exist"

    def all_shards_rendered(self) -> str:
        """Every shard at once. Only the monolith arm is allowed to use this."""
        for shard in self.shards:
            self.reads.append(shard.shard_id)
        return "\n\n".join(shard.rendered() for shard in self.shards)


TASK_TEXT = (
    "Reconcile a ledger split across {count} shards. Read every shard with "
    "the read tool, then report one JSON object with three keys: "
    '"net" is the sum over all entries of the amount when side is DR minus '
    'the amount when side is CR; "unbalanced" is the number of distinct '
    "accounts whose own net is not zero; and "
    '"largest" is the shard id whose own net has the largest absolute value, '
    "breaking a tie by the smaller shard id. Read shards one at a time and "
    "keep a running total; you cannot see a shard you have not read."
)


def task_text(world: World) -> str:
    return TASK_TEXT.format(count=len(world.shards))


def oracle(world: World) -> dict:
    """The truth, computed from the world itself, never from an arm's work."""
    net = 0
    per_account: dict = {}
    per_shard: dict = {}
    for shard in world.shards:
        shard_net = 0
        for account, side, amount in shard.entries:
            signed = amount if side == "DR" else -amount
            net += signed
            shard_net += signed
            per_account[account] = per_account.get(account, 0) + signed
        per_shard[shard.shard_id] = shard_net
    largest = min(
        per_shard, key=lambda name: (-abs(per_shard[name]), name))
    return {"net": net,
            "unbalanced": sum(1 for value in per_account.values() if value != 0),
            "largest": largest}


def grade(world: World, answer) -> dict:
    """Score one arm's answer against the oracle. Shape errors are failures."""
    truth = oracle(world)
    if not isinstance(answer, dict):
        return {"solved": False, "reason": "answer was not an object",
                "expected": truth, "got": str(answer)[:120]}
    missing = [key for key in truth if key not in answer]
    if missing:
        return {"solved": False, "reason": f"missing keys {missing}",
                "expected": truth, "got": {k: answer.get(k) for k in truth}}
    wrong = {key: (truth[key], answer[key])
             for key in truth if answer[key] != truth[key]}
    return {"solved": not wrong,
            "reason": "" if not wrong else f"wrong values {sorted(wrong)}",
            "expected": truth,
            "got": {key: answer.get(key) for key in truth}}


def world_digest(world: World) -> str:
    body = json.dumps([[s.shard_id, list(s.entries)] for s in world.shards],
                      sort_keys=True)
    return hashlib.sha256(body.encode()).hexdigest()[:16]


def self_check() -> None:
    """The world and its oracle agree with a second, slower computation."""
    world = World.build(5, seed=7)
    truth = oracle(world)
    net = sum((amount if side == "DR" else -amount)
              for shard in world.shards for _, side, amount in shard.entries)
    assert truth["net"] == net, "oracle net disagrees with a direct sum"
    assert truth["largest"] in world.shard_ids
    assert 0 <= truth["unbalanced"] <= 5
    # reading is what makes a shard visible, and re-reads are counted
    fresh = World.build(3, seed=7)
    assert fresh.reads == []
    fresh.read_shard("s000")
    fresh.read_shard("s000")
    assert fresh.reads == ["s000", "s000"], "re-reads must be visible"
    assert "does not exist" in fresh.read_shard("nope")
    print("world self-check: ok")


if __name__ == "__main__":
    self_check()
