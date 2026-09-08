"""Memory 4: stage, review, promote, recall. Nothing promotes itself.

A record enters as a candidate carrying who produced it. It is served to a
later run only after a reviewer that did not produce it accepted it, and after
an authorizer promoted it. The producer cannot be the reviewer, so a run
cannot decide that its own conclusion is trustworthy.

The reviewer here is the independent recompute verifier from the verification
family, which is what makes this arm meaningfully different from the cache:
the gate is a second derivation, not a policy string.

Position is checkpointed too, so this arm is a superset of the resume arm. The
cost of that is exactly what you would expect and should be weighed: two
mechanisms, two failure modes, and a review pass before anything is believed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))

from world import world_digest

STAGED, PROMOTED, REJECTED = "staged", "promoted", "rejected"


class Store:
    kind = "governed"

    def __init__(self, root=None, reviewer=None):
        self.root = Path(root) if root else None
        #: callable(world, answer) -> (accepted, reason). Without one, nothing
        #: is ever promoted, which is the correct default for a governed store.
        self.reviewer = reviewer
        self.records: dict = {}
        self.states: dict = {}
        self.journal: list = []

    def _key(self, world):
        return world_digest(world)

    def recall(self, world):
        record = self.records.get(self._key(world))
        if record and record["status"] == PROMOTED:
            return record["answer"]
        return None

    def checkpoint(self, world):
        return self.states.get(self._key(world))

    def _stage(self, world, answer, by):
        key = self._key(world)
        record = {"answer": json.loads(json.dumps(answer)), "status": STAGED,
                  "produced_by": by, "reviewed_by": "", "reason": ""}
        self.records[key] = record
        self.journal.append((key, STAGED, by))
        return record

    def _review(self, world, record):
        """Promote only on an independent pass that the producer did not run."""
        if self.reviewer is None:
            # It stays a candidate. Not rejected, because nothing judged it;
            # not served, because only a promoted record is served. A store
            # with no reviewer therefore accumulates and never answers, which
            # is the right default for a design whose rule is that nothing
            # promotes itself.
            record["reason"] = "no reviewer configured"
            return record
        accepted, reason = self.reviewer(world, record["answer"])
        if accepted and record["produced_by"] == "reviewer":
            accepted, reason = False, "producer may not be its own reviewer"
        record["reviewed_by"] = "reviewer"
        record["reason"] = reason
        record["status"] = PROMOTED if accepted else REJECTED
        self.journal.append((self._key(world), record["status"], "reviewer"))
        return record

    def commit(self, world, outcome, accepted):
        state = outcome.get("state")
        if isinstance(state, dict) and state:
            self.states[self._key(world)] = {
                "state": json.loads(json.dumps(state)),
                "cursor": int(outcome.get("cursor") or 0)}
        answer = outcome.get("answer")
        if not isinstance(answer, dict):
            return "nothing to stage"
        record = self._stage(world, answer, by="run")
        self._review(world, record)
        return record["status"]

    def offer(self, world, record, by="unknown"):
        """An outsider may stage. Staging is not believing."""
        staged = self._stage(world, record, by=by)
        self._review(world, staged)
        return staged["status"]


ARM = {"name": "governed_journal",
       "keeps": "reviewed answers plus the accumulator", "Store": Store}


def self_check() -> None:
    from world import World, oracle

    def reviewer(world, answer):
        truth = oracle(world)
        wrong = [key for key in truth if answer.get(key) != truth[key]]
        return (not wrong), ("" if not wrong else f"disagrees on {wrong}")

    world = World.build(5, seed=1)
    truth = oracle(world)

    ungoverned = Store()
    assert ungoverned.commit(world, {"answer": dict(truth)}, True) == STAGED
    assert ungoverned.recall(world) is None, (
        "without a reviewer nothing may be served")
    assert [entry[1] for entry in ungoverned.journal] == [STAGED]

    store = Store(reviewer=reviewer)
    assert store.commit(world, {"answer": dict(truth), "state": {"net": 1},
                                "cursor": 2}, True) == PROMOTED
    assert store.recall(world) == truth
    assert store.checkpoint(world) == {"state": {"net": 1}, "cursor": 2}

    poisoned = Store(reviewer=reviewer)
    assert poisoned.offer(world, {"net": -999, "unbalanced": 0,
                                  "largest": "s000"}, by="outsider") == REJECTED
    assert poisoned.recall(world) is None, "a rejected record must not be served"
    assert poisoned.journal[-1][1] == REJECTED
    print("memory/governed_journal self-check: ok")


if __name__ == "__main__":
    self_check()
