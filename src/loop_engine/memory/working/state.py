"""Working memory: bounded, run-scoped, Loop-scoped cognitive state.

Working memory holds what one Loop currently needs to decide and act.
It is not persistent intelligence and it is not operational scheduler
state. It is snapshotable for checkpoints and isolated by default.

Compartments keep the state explicit: immutable task envelope,
parent-shared context, Loop-private scratch, recalled persistent
memory, intermediate products, decision and verification ledgers, and
the return-to-parent payload.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

#: Compartments of one working-memory state.
COMPARTMENTS = (
    "task_envelope", "parent_shared", "private_scratch", "recalled",
    "intermediate", "decisions", "verification", "return_payload",
)


@dataclass(frozen=True)
class WorkingMemoryPolicy:
    """Configuration bounds for one Loop's working memory."""

    capacity_items: int = 256
    capacity_bytes: int = 1_000_000
    pinned_fields: tuple[str, ...] = ()
    eviction_policy: str = "least_recent"
    compaction_enabled: bool = True
    allow_model_compaction: bool = False

    def __post_init__(self) -> None:
        if self.capacity_items < 1 or self.capacity_bytes < 1:
            raise ValueError("working memory capacity must be positive")
        if self.eviction_policy not in (
                "least_recent", "least_priority", "refuse"):
            raise ValueError(
                "eviction_policy must be least_recent, least_priority, "
                "or refuse")


@dataclass
class WorkingMemoryState:
    """Mutable bounded cognitive state for one Loop execution cycle."""

    run_id: str
    loop_id: str
    parent_loop_id: str = ""
    decision_cycle_id: str = ""
    active_goal: str = ""
    current_subgoal: str = ""
    current_checkpoint: str = ""
    policy: WorkingMemoryPolicy = field(
        default_factory=WorkingMemoryPolicy)
    _compartments: dict = field(default_factory=dict)
    _order: list = field(default_factory=list)
    _priorities: dict = field(default_factory=dict)
    _sizes: dict = field(default_factory=dict)
    _compaction_history: list = field(default_factory=list)
    _eviction_history: list = field(default_factory=list)

    def __post_init__(self) -> None:
        for name in COMPARTMENTS:
            self._compartments.setdefault(name, {})
        if not self.run_id or not self.loop_id:
            raise ValueError("working memory needs run_id and loop_id")

    # -- access ---------------------------------------------------------
    def put(self, compartment: str, key: str, value, *,
            priority: int = 0, pinned: bool = False,
            parent_shared: bool = False) -> None:
        """Write one entry, enforcing capacity and eviction."""
        if compartment not in COMPARTMENTS:
            raise ValueError(f"unknown compartment {compartment!r}")
        target = "parent_shared" if parent_shared else compartment
        size = len(json.dumps(value, default=str).encode("utf-8"))
        if size > self.policy.capacity_bytes:
            raise ValueError("entry exceeds working-memory byte capacity")
        existing = (compartment, key)
        if key in self._compartments[target]:
            self._sizes.pop((target, key), None)
            self._order.remove((target, key))
        self._compartments[target][key] = value
        self._priorities[(target, key)] = priority
        self._sizes[(target, key)] = size
        self._order.append((target, key))
        while self._total_items() > self.policy.capacity_items \
                or self._total_bytes() > self.policy.capacity_bytes:
            evicted = self._evict_one()
            if evicted is None:
                raise ValueError(
                    "working memory over capacity and nothing evictable")

    def get(self, compartment: str, key: str, default=None):
        if compartment not in COMPARTMENTS:
            raise ValueError(f"unknown compartment {compartment!r}")
        return self._compartments[compartment].get(key, default)

    def compartment(self, name: str) -> dict:
        if name not in COMPARTMENTS:
            raise ValueError(f"unknown compartment {name!r}")
        return dict(self._compartments[name])

    def items(self) -> tuple[tuple[str, str], ...]:
        return tuple(self._order)

    # -- capacity -------------------------------------------------------
    def _total_items(self) -> int:
        return sum(len(c) for c in self._compartments.values())

    def _total_bytes(self) -> int:
        return sum(self._sizes.values())

    def _evict_one(self) -> "tuple | None":
        # Pinned field names survive eviction regardless of compartment.
        candidates = [(c, k) for (c, k) in self._order
                      if k not in self.policy.pinned_fields]
        if not candidates:
            return None
        if self.policy.eviction_policy == "least_recent":
            target = candidates[0]
        elif self.policy.eviction_policy == "least_priority":
            target = min(candidates,
                         key=lambda ck: self._priorities.get(ck, 0))
        else:
            return None
        self._eviction_history.append({
            "compartment": target[0], "key": target[1],
            "reason": self.policy.eviction_policy})
        self._compartments[target[0]].pop(target[1])
        self._sizes.pop(target, None)
        self._order.remove(target)
        return target

    # -- snapshots ------------------------------------------------------
    def snapshot(self) -> dict:
        """Deterministic serializable snapshot with digest."""
        payload = {
            "run_id": self.run_id,
            "loop_id": self.loop_id,
            "parent_loop_id": self.parent_loop_id,
            "decision_cycle_id": self.decision_cycle_id,
            "active_goal": self.active_goal,
            "current_subgoal": self.current_subgoal,
            "current_checkpoint": self.current_checkpoint,
            "compartments": {
                name: {k: json.dumps(v, default=str)
                       for k, v in self._compartments[name].items()}
                for name in COMPARTMENTS},
        }
        serialized = json.dumps(payload, sort_keys=True)
        digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        return {"schema": "working_memory_snapshot/v1",
                "digest": digest, "payload": payload}

    def restore(self, snapshot: dict) -> None:
        """Restore from a compatible snapshot, refusing mismatches."""
        if snapshot.get("schema") != "working_memory_snapshot/v1":
            raise ValueError("incompatible working-memory snapshot schema")
        payload = snapshot["payload"]
        if payload.get("run_id") != self.run_id \
                or payload.get("loop_id") != self.loop_id:
            raise ValueError(
                "working-memory snapshot does not match run or Loop "
                "identity")
        self.parent_loop_id = payload.get("parent_loop_id", "")
        self.decision_cycle_id = payload.get("decision_cycle_id", "")
        self.active_goal = payload.get("active_goal", "")
        self.current_subgoal = payload.get("current_subgoal", "")
        self.current_checkpoint = payload.get("current_checkpoint", "")
        for name in COMPARTMENTS:
            self._compartments[name] = {
                k: json.loads(v)
                for k, v in payload.get("compartments", {}).get(name,
                                                                {}).items()}
        self._order = [(c, k) for c in COMPARTMENTS
                       for k in self._compartments[c]]

    # -- receipts -------------------------------------------------------
    def history(self) -> dict:
        return {"compactions": list(self._compaction_history),
                "evictions": list(self._eviction_history),
                "items": self._total_items(),
                "bytes": self._total_bytes()}


def self_test() -> dict:
    """Prove working memory is bounded, isolated, and snapshotable."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    state = WorkingMemoryState(run_id="run-1", loop_id="loop-a",
                               parent_loop_id="loop-root")
    state.put("private_scratch", "hypothesis", "use gradient boosting",
              priority=1)
    state.put("task_envelope", "goal", "predict churn")
    check("compartments_hold_values",
          state.get("private_scratch", "hypothesis")
          == "use gradient boosting"
          and state.get("task_envelope", "goal") == "predict churn")

    child = WorkingMemoryState(run_id="run-1", loop_id="loop-b",
                               parent_loop_id="loop-a")
    child.put("parent_shared", "constraint", "no network")
    check("sibling_isolation",
          child.get("private_scratch", "hypothesis") is None
          and state.get("parent_shared", "constraint") is None)

    snap = state.snapshot()
    restored = WorkingMemoryState(run_id="run-1", loop_id="loop-a")
    restored.restore(snap)
    check("snapshot_round_trip",
          restored.get("private_scratch", "hypothesis")
          == "use gradient boosting"
          and restored.snapshot()["digest"] == snap["digest"])

    try:
        restored.restore(dict(snap, payload=dict(
            snap["payload"], loop_id="other-loop")))
        check("incompatible_restore_is_refused", False)
    except ValueError:
        check("incompatible_restore_is_refused", True)

    bounded = WorkingMemoryState(
        run_id="run-1", loop_id="loop-c",
        policy=WorkingMemoryPolicy(capacity_items=2))
    bounded.put("private_scratch", "a", 1)
    bounded.put("private_scratch", "b", 2)
    bounded.put("private_scratch", "c", 3)
    check("capacity_evicts_oldest",
          bounded.get("private_scratch", "a") is None
          and bounded.get("private_scratch", "c") == 3
          and len(bounded.history()["evictions"]) == 1)

    pinned = WorkingMemoryState(
        run_id="run-1", loop_id="loop-d",
        policy=WorkingMemoryPolicy(capacity_items=2,
                                   pinned_fields=("goal",)))
    pinned.put("task_envelope", "goal", "irreplaceable")
    pinned.put("private_scratch", "x", 1)
    pinned.put("private_scratch", "y", 2)
    check("pinned_fields_survive_eviction",
          pinned.get("task_envelope", "goal") == "irreplaceable")

    try:
        tiny = WorkingMemoryState(
            run_id="run-1", loop_id="loop-e",
            policy=WorkingMemoryPolicy(capacity_bytes=10))
        tiny.put("private_scratch", "big", "x" * 100)
        check("oversized_entry_is_refused", False)
    except ValueError:
        check("oversized_entry_is_refused", True)
    return {"tests": results}
