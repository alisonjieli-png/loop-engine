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
import math
from dataclasses import dataclass, field

#: Compartments of one working-memory state.
COMPARTMENTS = (
    "task_envelope", "parent_shared", "private_scratch", "recalled",
    "intermediate", "decisions", "verification", "return_payload",
)

_SNAPSHOT_FIELDS = (
    "run_id", "loop_id", "parent_loop_id", "decision_cycle_id", "active_goal",
    "current_subgoal", "current_checkpoint",
)


def snapshot_json_value(value):
    """Detach finite JSON data without invoking hooks on opaque live objects.

    Tuples use their existing JSON array representation. Callers receive an
    owned data copy, not a live handle or a shared nested container.
    """
    active = set()

    def copy_data(item):
        kind = type(item)
        if item is None or kind in (bool, int):
            return item
        if kind is str:
            item.encode("utf-8")
            return item
        if kind is float:
            if not math.isfinite(item):
                raise ValueError("memory values must be finite JSON data")
            return item
        if kind not in (list, tuple, dict):
            raise ValueError("memory values must be finite JSON data, not live objects")
        if id(item) in active:
            raise ValueError("memory values cannot contain cycles")
        active.add(id(item))
        try:
            if kind is dict:
                if any(type(key) is not str for key in item):
                    raise ValueError("memory object keys must be strings")
                return {copy_data(key): copy_data(part) for key, part in item.items()}
            return [copy_data(part) for part in item]
        finally:
            active.remove(id(item))

    try:
        return copy_data(value)
    except (UnicodeError, RecursionError):
        raise ValueError("memory value cannot be represented as bounded UTF-8 JSON") from None


def _json_text(value) -> str:
    # Retain the v1 JSON wire layout for admissible data.
    return json.dumps(value, allow_nan=False)


def _snapshot_digest(payload: dict) -> str:
    return hashlib.sha256(json.dumps(
        payload, sort_keys=True, allow_nan=False).encode("utf-8")).hexdigest()


def _decoded_entry(text: str):
    if type(text) is not str:
        raise ValueError("snapshot entries must contain serialized JSON")

    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("snapshot JSON contains duplicate keys")
            result[key] = value
        return result

    try:
        return snapshot_json_value(json.loads(text, object_pairs_hook=unique_pairs))
    except (ValueError, TypeError, RecursionError):
        raise ValueError("snapshot entry is not finite JSON data") from None


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
        if (type(self.capacity_items) is not int or type(self.capacity_bytes) is not int
                or self.capacity_items < 1 or self.capacity_bytes < 1):
            raise ValueError("working memory capacity must be positive")
        if type(self.pinned_fields) not in (list, tuple):
            raise ValueError("pinned fields must be a sequence of field names")
        pinned = tuple(self.pinned_fields)
        if (any(type(key) is not str or not key for key in pinned)
                or len(set(pinned)) != len(pinned)):
            raise ValueError("pinned fields must be unique non-empty strings")
        object.__setattr__(self, "pinned_fields", pinned)
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
        if (not isinstance(self.policy, WorkingMemoryPolicy)
                or any(type(getattr(self, name)) is not str for name in _SNAPSHOT_FIELDS)
                or not self.run_id or not self.loop_id):
            raise ValueError("working memory needs run_id and loop_id")
        snapshot_json_value({name: getattr(self, name) for name in _SNAPSHOT_FIELDS})
        if (type(self._compartments) is not dict
                or any(type(key) is not str for key in self._compartments)
                or set(self._compartments) - set(COMPARTMENTS)):
            raise ValueError("working memory compartments are invalid")
        compartments = {name: self._compartments.get(name, {}) for name in COMPARTMENTS}
        if any(type(entries) is not dict for entries in compartments.values()):
            raise ValueError("working memory compartments must be mappings")
        compartments = snapshot_json_value(compartments)
        if any(not key for entries in compartments.values() for key in entries):
            raise ValueError("working memory entry keys must be non-empty")
        sizes = {(name, key): len(_json_text(value).encode("utf-8"))
                 for name, entries in compartments.items() for key, value in entries.items()}
        if len(sizes) > self.policy.capacity_items or sum(sizes.values()) > self.policy.capacity_bytes:
            raise ValueError("initial working memory exceeds capacity")
        self._compartments = compartments
        self._sizes = sizes
        self._order = list(sizes)
        self._priorities = {item: 0 for item in self._order}

    # -- access ---------------------------------------------------------
    def put(self, compartment: str, key: str, value, *,
            priority: int = 0, pinned: bool = False,
            parent_shared: bool = False) -> None:
        """Stage a detached entry and policy eviction before replacing state."""
        if compartment not in COMPARTMENTS:
            raise ValueError(f"unknown compartment {compartment!r}")
        if type(key) is not str or not key or type(priority) is not int:
            raise ValueError("working memory entry needs a string key and integer priority")
        if type(parent_shared) is not bool or type(pinned) is not bool:
            raise ValueError("working memory sharing and pinning flags must be boolean")
        if pinned and key not in self.policy.pinned_fields:
            raise ValueError("pinning requires the field in the working memory policy")
        target = "parent_shared" if parent_shared else compartment
        detached = snapshot_json_value(value)
        size = len(_json_text(detached).encode("utf-8"))
        if size > self.policy.capacity_bytes:
            raise ValueError("entry exceeds working-memory byte capacity")
        compartments = {name: dict(entries) for name, entries in self._compartments.items()}
        order, sizes, priorities = list(self._order), dict(self._sizes), dict(self._priorities)
        item = (target, key)
        if item in order:
            order.remove(item)
        compartments[target][key] = detached
        sizes[item], priorities[item] = size, priority
        order.append(item)
        evictions = []
        while len(order) > self.policy.capacity_items or sum(sizes.values()) > self.policy.capacity_bytes:
            eligible = [entry for entry in order if entry[1] not in self.policy.pinned_fields]
            if not eligible or self.policy.eviction_policy == "refuse":
                raise ValueError(
                    "working memory over capacity and nothing evictable")
            evicted = (eligible[0] if self.policy.eviction_policy == "least_recent"
                       else min(eligible, key=lambda entry: priorities.get(entry, 0)))
            compartments[evicted[0]].pop(evicted[1])
            order.remove(evicted)
            sizes.pop(evicted)
            priorities.pop(evicted, None)
            evictions.append({"compartment": evicted[0], "key": evicted[1],
                              "reason": self.policy.eviction_policy})
        self.__dict__.update(_compartments=compartments, _order=order, _sizes=sizes,
                             _priorities=priorities,
                             _eviction_history=[*self._eviction_history, *evictions])

    def get(self, compartment: str, key: str, default=None):
        if compartment not in COMPARTMENTS:
            raise ValueError(f"unknown compartment {compartment!r}")
        if key not in self._compartments[compartment]:
            return default
        return snapshot_json_value(self._compartments[compartment][key])

    def compartment(self, name: str) -> dict:
        if name not in COMPARTMENTS:
            raise ValueError(f"unknown compartment {name!r}")
        return snapshot_json_value(self._compartments[name])

    def items(self) -> tuple[tuple[str, str], ...]:
        return tuple(self._order)

    # -- capacity -------------------------------------------------------
    def _total_items(self) -> int:
        return sum(len(c) for c in self._compartments.values())

    def _total_bytes(self) -> int:
        return sum(self._sizes.values())

    # -- snapshots ------------------------------------------------------
    def snapshot(self) -> dict:
        """Deterministic serializable snapshot with digest."""
        if any(type(getattr(self, name)) is not str for name in _SNAPSHOT_FIELDS):
            raise ValueError("working memory snapshot metadata must be strings")
        payload = {
            **snapshot_json_value({name: getattr(self, name) for name in _SNAPSHOT_FIELDS}),
            "compartments": {
                name: {k: _json_text(v)
                       for k, v in self._compartments[name].items()}
                for name in COMPARTMENTS},
        }
        return {"schema": "working_memory_snapshot/v1",
                "digest": _snapshot_digest(payload), "payload": payload}

    def restore(self, snapshot: dict) -> None:
        """Validate the complete snapshot and receiver limits before replacement.

        Version 1 did not save eviction ordering, priorities, or history. Its
        reader reconstructs deterministic defaults and current byte counts;
        it never treats the supplied digest as an access-authority grant.
        """
        snapshot = snapshot_json_value(snapshot)
        if (type(snapshot) is not dict or set(snapshot) != {"schema", "digest", "payload"}
                or snapshot.get("schema") != "working_memory_snapshot/v1"):
            raise ValueError("incompatible working-memory snapshot schema")
        payload = snapshot["payload"]
        if (type(payload) is not dict or set(payload) != {*_SNAPSHOT_FIELDS, "compartments"}
                or any(type(payload[name]) is not str for name in _SNAPSHOT_FIELDS)):
            raise ValueError("working memory snapshot fields are invalid")
        if (type(snapshot["digest"]) is not str
                or _snapshot_digest(payload) != snapshot["digest"]):
            raise ValueError("working memory snapshot digest mismatch")
        if any(payload[name] != getattr(self, name)
               for name in ("run_id", "loop_id", "parent_loop_id")):
            raise ValueError(
                "working-memory snapshot does not match run, Loop, or spawning identity")
        encoded = payload["compartments"]
        if type(encoded) is not dict or set(encoded) != set(COMPARTMENTS):
            raise ValueError("working memory snapshot compartments are invalid")
        if any(type(entries) is not dict or any(not key for key in entries)
               for entries in encoded.values()):
            raise ValueError("working memory snapshot entries are invalid")
        compartments = {name: {key: _decoded_entry(text) for key, text in entries.items()}
                        for name, entries in encoded.items()}
        sizes = {(name, key): len(_json_text(value).encode("utf-8"))
                 for name, entries in compartments.items() for key, value in entries.items()}
        if len(sizes) > self.policy.capacity_items or sum(sizes.values()) > self.policy.capacity_bytes:
            raise ValueError("working memory snapshot exceeds receiver capacity")
        order = [(name, key) for name in COMPARTMENTS for key in compartments[name]]
        replacement = {name: payload[name] for name in _SNAPSHOT_FIELDS}
        replacement.update(_compartments=compartments, _sizes=sizes, _order=order,
                           _priorities={item: 0 for item in order},
                           _compaction_history=[], _eviction_history=[])
        self.__dict__.update(replacement)

    # -- receipts -------------------------------------------------------
    def history(self) -> dict:
        return {"compactions": snapshot_json_value(self._compaction_history),
                "evictions": snapshot_json_value(self._eviction_history),
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
    restored = WorkingMemoryState(run_id="run-1", loop_id="loop-a",
                                  parent_loop_id="loop-root")
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
    results.extend(_boundary_checks())
    return {"tests": results}


def _boundary_checks() -> list[dict]:
    """Regression checks for aliases and all-or-nothing snapshot restoration."""
    tests = []

    def check(name, passed):
        tests.append({"name": name, "passed": bool(passed), "note": ""})

    def refused(operation):
        try:
            operation()
        except ValueError:
            return True
        return False

    nested = {"items": [{"value": 1}]}
    memory = WorkingMemoryState("run-alias", "loop-a")
    memory.put("private_scratch", "nested", nested)
    expected = memory.snapshot()
    nested["items"][0]["value"] = 2
    memory.get("private_scratch", "nested")["items"][0]["value"] = 3
    memory.compartment("private_scratch")["nested"]["items"][0]["value"] = 4
    detached_snapshot = memory.snapshot()
    detached_snapshot["payload"]["compartments"]["private_scratch"]["nested"] = '"changed"'
    check("nested_input_get_compartment_and_snapshot_aliases_are_detached",
          memory.snapshot() == expected
          and memory.get("private_scratch", "nested") == {"items": [{"value": 1}]})
    initial = {"private_scratch": {"nested": {"items": [1]}}}
    initialized = WorkingMemoryState("run-initial", "loop-a", _compartments=initial)
    initial["private_scratch"]["nested"]["items"].append(2)
    check("constructor_data_is_detached_and_accounted",
          initialized.get("private_scratch", "nested") == {"items": [1]}
          and initialized.history()["bytes"] == len(json.dumps({"items": [1]}).encode()))

    hooks = []

    class OpaqueHandle:
        def __str__(self):
            hooks.append("str")
            return "opaque"

        def __deepcopy__(self, memo):
            hooks.append("deepcopy")
            return self

    cycle = []
    cycle.append(cycle)
    values = (OpaqueHandle(), {"nested": OpaqueHandle()}, float("nan"), float("inf"),
              {1: "non-string-key"}, cycle)
    before = memory.snapshot(), memory.history(), memory.items()
    check("unsupported_and_nonfinite_values_fail_without_object_hooks_or_state_change",
          all(refused(lambda value=value: memory.put("intermediate", "bad", value)) for value in values)
          and not hooks and before == (memory.snapshot(), memory.history(), memory.items()))

    target = WorkingMemoryState("run-restore", "loop-a", parent_loop_id="owner",
        policy=WorkingMemoryPolicy(capacity_items=2, capacity_bytes=64))
    target.put("private_scratch", "old", "old", priority=9)
    target.put("private_scratch", "keep", "keep", priority=4)
    target.put("private_scratch", "new", "new", priority=2)
    target.active_goal = "current goal"
    untouched = (target.snapshot(), target.history(), target.items(),
                 dict(target._sizes), dict(target._priorities))

    def unchanged():
        return untouched == (target.snapshot(), target.history(), target.items(),
                             dict(target._sizes), dict(target._priorities))

    original = target.snapshot()
    forged = snapshot_json_value(original)
    forged["payload"]["compartments"]["private_scratch"] = {
        "v": json.dumps("X" * 200), "extra": "2"}
    check("forged_snapshot_digest_is_refused_before_mutating_state_or_history",
          refused(lambda: target.restore(forged)) and unchanged())

    def rewritten(change):
        snapshot = snapshot_json_value(original)
        change(snapshot["payload"])
        snapshot["digest"] = _snapshot_digest(snapshot["payload"])
        return snapshot

    oversized = rewritten(lambda payload: payload["compartments"].update(
        private_scratch={"v": json.dumps("X" * 200)}))
    too_many = rewritten(lambda payload: payload["compartments"].update(
        private_scratch={"a": "1", "b": "2", "c": "3"}))
    check("correctly_digested_restore_overflow_is_rejected_not_trimmed",
          refused(lambda: target.restore(oversized)) and unchanged()
          and refused(lambda: target.restore(too_many)) and unchanged())
    identity_bad = [rewritten(lambda payload, name=name: payload.update({name: "forged"}))
                    for name in ("run_id", "loop_id", "parent_loop_id")]
    check("all_run_loop_and_spawning_identity_mismatches_are_refused",
          all(refused(lambda snapshot=snapshot: target.restore(snapshot)) and unchanged()
              for snapshot in identity_bad))
    invalid_entries = ("not-json", '{"duplicate":1,"duplicate":2}', "NaN")
    malformed = [rewritten(lambda payload, entry=entry: payload["compartments"].update(
        private_scratch={"bad": entry})) for entry in invalid_entries]
    malformed.append(rewritten(lambda payload: payload["compartments"].update(unknown={})))
    malformed.append(rewritten(lambda payload: payload.update(unknown="field")))
    check("malformed_snapshot_shapes_and_entries_preserve_existing_state",
          all(refused(lambda snapshot=snapshot: target.restore(snapshot)) and unchanged()
              for snapshot in malformed))

    source = WorkingMemoryState("run-restore", "loop-a", parent_loop_id="owner")
    source.put("task_envelope", "number", 1)
    source.put("private_scratch", "data", {"letter": "é", "values": [True, None]})
    valid = source.snapshot()
    target.restore(valid)
    expected_bytes = sum(len(json.dumps(value).encode("utf-8"))
                         for value in (1, {"letter": "é", "values": [True, None]}))
    valid["payload"]["compartments"]["private_scratch"]["data"] = '"changed"'
    check("valid_v1_restore_rebuilds_accounting_and_detaches_snapshot_data",
          target.snapshot() == source.snapshot() and target.history()["bytes"] == expected_bytes
          and target.history()["items"] == 2 and not target.history()["evictions"]
          and set(target._priorities.values()) == {0})
    legacy_payload = source.snapshot()["payload"]
    legacy_digest = hashlib.sha256(json.dumps(legacy_payload, sort_keys=True).encode()).hexdigest()
    check("valid_json_snapshot_v1_wire_digest_is_preserved",
          source.snapshot()["schema"] == "working_memory_snapshot/v1"
          and source.snapshot()["digest"] == legacy_digest)

    bounded = WorkingMemoryState("run-put", "loop-a", policy=WorkingMemoryPolicy(
        capacity_items=1, capacity_bytes=64, eviction_policy="refuse"))
    bounded.put("private_scratch", "original", {"items": [1]})
    original_state = bounded.snapshot(), bounded.history(), bounded.items()
    check("failed_put_is_atomic_under_refuse_eviction_policy",
          refused(lambda: bounded.put("private_scratch", "other", 2))
          and original_state == (bounded.snapshot(), bounded.history(), bounded.items()))
    priority = WorkingMemoryState("run-priority", "loop-a", policy=WorkingMemoryPolicy(
        capacity_items=2, eviction_policy="least_priority"))
    priority.put("private_scratch", "low", 1, priority=1)
    priority.put("private_scratch", "high", 2, priority=9)
    priority.put("private_scratch", "middle", 3, priority=5)
    copied_history = priority.history()
    copied_history["evictions"][0]["key"] = "forged"
    check("priority_eviction_is_preserved_and_history_returns_detached_metadata",
          priority.get("private_scratch", "low") is None
          and priority.get("private_scratch", "high") == 2
          and priority.history()["evictions"][0]["key"] == "low")
    return tests
