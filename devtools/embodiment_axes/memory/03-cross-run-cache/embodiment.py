"""Memory 3: remember the answer, and serve it whenever the task matches.

The cheapest possible memory and the most dangerous. A second run over the
same world costs nothing at all, because the answer is returned without a
single call. Whatever was written is what gets served.

Its failure mode is not subtle and is worth measuring rather than describing:
anything that can write to the cache decides what later runs believe. There is
no reviewer, no provenance requirement and no re-derivation.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))

from world import world_digest


class Store:
    kind = "cache"

    def __init__(self, root=None):
        self.root = Path(root) if root else None
        self.answers: dict = {}
        self.states: dict = {}

    def _key(self, world):
        return world_digest(world)

    def recall(self, world):
        return self.answers.get(self._key(world))

    def checkpoint(self, world):
        return self.states.get(self._key(world))

    def commit(self, world, outcome, accepted):
        answer = outcome.get("answer")
        if isinstance(answer, dict):
            self.answers[self._key(world)] = json.loads(json.dumps(answer))
        state = outcome.get("state")
        if isinstance(state, dict) and state:
            self.states[self._key(world)] = {
                "state": json.loads(json.dumps(state)),
                "cursor": int(outcome.get("cursor") or 0)}
        return "cached"

    def offer(self, world, record, by="unknown"):
        """No review, no provenance check. Whoever writes last is believed."""
        self.answers[self._key(world)] = json.loads(json.dumps(record))
        return f"accepted from {by}"


ARM = {"name": "cross_run_cache", "keeps": "the final answer, keyed by task",
       "Store": Store}


def self_check() -> None:
    from world import World
    store = Store()
    world = World.build(4, seed=1)
    assert store.recall(world) is None
    store.commit(world, {"answer": {"net": 3}}, accepted=False)
    assert store.recall(world) == {"net": 3}
    assert "accepted" in store.offer(world, {"net": -999}, by="anyone")
    assert store.recall(world) == {"net": -999}, (
        "the point of this arm is that an unreviewed write wins")
    print("memory/cross_run_cache self-check: ok")


if __name__ == "__main__":
    self_check()
