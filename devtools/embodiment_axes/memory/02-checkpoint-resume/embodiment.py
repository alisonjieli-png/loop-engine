"""Memory 2: the accumulator survives a stop, and only the accumulator.

A run that hits a ceiling writes its carried state and its cursor. The next
run over the same world picks that up and continues. Nothing about an answer
is ever kept, so a later run cannot be handed a conclusion, only a position.

That is the safety property worth naming: the worst a corrupted checkpoint can
do is start the arithmetic from a wrong subtotal, which the verification family
catches. It cannot make a run skip its work and report someone else's answer.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))

from world import world_digest


class Store:
    kind = "checkpoint"

    def __init__(self, root=None):
        self.root = Path(root) if root else None
        self.states: dict = {}

    def _key(self, world):
        return world_digest(world)

    def recall(self, world):
        return None                      # answers are never kept

    def checkpoint(self, world):
        return self.states.get(self._key(world))

    def commit(self, world, outcome, accepted):
        # The position travels with the subtotal. Storing one without the
        # other is what makes a resumed run count the same work twice.
        state = outcome.get("state")
        if isinstance(state, dict) and state:
            self.states[self._key(world)] = {
                "state": json.loads(json.dumps(state)),
                "cursor": int(outcome.get("cursor") or 0)}
        return "checkpointed"

    def offer(self, world, record, by="unknown"):
        return "refused: this embodiment stores positions, not answers"


ARM = {"name": "checkpoint_resume", "keeps": "the accumulator and the cursor",
       "Store": Store}


def self_check() -> None:
    from world import World
    store = Store()
    world = World.build(4, seed=1)
    assert store.checkpoint(world) is None
    store.commit(world, {"state": {"net": 7}, "cursor": 3}, accepted=False)
    assert store.checkpoint(world) == {"state": {"net": 7}, "cursor": 3}, (
        "a checkpoint that drops the cursor is not a checkpoint")
    assert store.recall(world) is None, "an answer must never be recalled here"
    assert store.checkpoint(World.build(5, seed=1)) is None, "keyed by world"
    print("memory/checkpoint_resume self-check: ok")


if __name__ == "__main__":
    self_check()
