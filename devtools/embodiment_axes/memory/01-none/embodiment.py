"""Memory 1: every run starts from nothing.

No state survives a run and no run learns from another. This is the control,
and it is the only arm that cannot be poisoned, because there is nothing to
poison. Its cost is that identical work is redone in full, every time.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))


class Store:
    kind = "none"

    def __init__(self, root=None):
        self.root = root

    def recall(self, world):
        return None

    def checkpoint(self, world):
        return None

    def commit(self, world, outcome, accepted):
        return None

    def offer(self, world, record, by="unknown"):
        """An outsider stages a claim. There is nowhere to put it."""
        return "refused: this embodiment keeps nothing"


ARM = {"name": "none", "keeps": "nothing", "Store": Store}


def self_check() -> None:
    store = Store()
    assert store.recall(None) is None and store.checkpoint(None) is None
    assert "refused" in store.offer(None, {"net": 1})
    print("memory/none self-check: ok")


if __name__ == "__main__":
    self_check()
