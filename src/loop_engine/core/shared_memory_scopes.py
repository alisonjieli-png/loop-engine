"""Shared memory scopes: many Loops, one store, every write signed by its writer.

A scope names a namespace, its members, and who may read it. A write
inside a scope carries the writer's identity and the scope, is refused for
a non-member, and can be guarded by the version the writer last read, so
two concurrent writers cannot both win silently. Reads are filtered by
membership and visibility, and every returned record shows who wrote it
and when. The records are ordinary catalog records; there is no second
store and no second authority.
"""
from __future__ import annotations

import json
import re
from copy import deepcopy
from dataclasses import dataclass

from ..catalog.handshake import negotiate
from ..catalog.protocol import CatalogStore, PreconditionFailed, StoreError
from ..catalog.query import IntelligenceQuery

VISIBILITIES = ("members_only", "organization", "public")
SCOPE_RECORD_TYPE = "shared_memory_scope/v1"
WRITE_RECORD_TYPE = "shared_memory_write/v1"
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:@-]{0,127}$")


class SharedMemoryError(PermissionError):
    """A scope, membership, visibility, or write guard is violated."""


@dataclass(frozen=True)
class SharedMemoryScope:
    """One shared space: its namespace, members, and visibility."""

    scope_id: str
    namespace: str
    members: tuple[str, ...]
    visibility: str = VISIBILITIES[0]
    organization: str = ""

    def __post_init__(self):
        if not _IDENTIFIER.fullmatch(self.scope_id):
            raise SharedMemoryError("scope_id must be a short identifier")
        if not self.namespace.strip():
            raise SharedMemoryError("a scope needs a namespace")
        members = tuple(self.members)
        if not members or any(not _IDENTIFIER.fullmatch(item) for item in members):
            raise SharedMemoryError("a scope names at least one member identifier")
        if len(set(members)) != len(members):
            raise SharedMemoryError("members must be unique")
        if self.visibility not in VISIBILITIES:
            raise SharedMemoryError(f"visibility must be one of {VISIBILITIES}")
        if self.visibility == VISIBILITIES[1] and not self.organization.strip():
            raise SharedMemoryError("organization visibility names the organization")
        object.__setattr__(self, "members", members)

    def can_write(self, writer_id: str) -> bool:
        return writer_id in self.members

    def can_read(self, reader_id: str, reader_organization: str = "") -> bool:
        if reader_id in self.members or self.visibility == VISIBILITIES[2]:
            return True
        return self.visibility == VISIBILITIES[1] and bool(reader_organization) \
            and reader_organization == self.organization

    def to_dict(self) -> dict:
        return {"record_type": SCOPE_RECORD_TYPE, "scope_id": self.scope_id,
                "namespace": self.namespace, "members": list(self.members),
                "visibility": self.visibility, "organization": self.organization}


@dataclass(frozen=True)
class SharedWrite:
    """The outcome of one signed write."""

    scope_id: str
    writer_id: str
    record_id: str
    record_version: str
    written_at: str

    def to_dict(self) -> dict:
        return {"record_type": WRITE_RECORD_TYPE, "scope_id": self.scope_id,
                "writer_id": self.writer_id, "record_id": self.record_id,
                "record_version": self.record_version, "written_at": self.written_at}


class SharedMemory:
    """Signed writes and membership-filtered reads over one catalog store."""

    def __init__(self, store: CatalogStore):
        self.store = store

    def write(self, scope: SharedMemoryScope, writer_id: str, record: dict, *,
              written_at: str, expected_version: str | None = None) -> SharedWrite:
        """Store a record inside the scope with the writer's identity on it."""
        capabilities = self.store.capabilities()
        handshake = negotiate(capabilities, required_operations=("get", "write"), write_requested=True)
        if (not handshake.permits("write") or capabilities.authority != "authoritative"
                or capabilities.transactions.get("atomic_preconditions") is not True):
            raise SharedMemoryError("shared writes require atomic authoritative preconditions")
        if not scope.can_write(writer_id):
            raise SharedMemoryError(f"{writer_id!r} is not a member of scope {scope.scope_id!r}")
        record_id = record.get("record_id")
        version = record.get("record_version")
        if not isinstance(record_id, str) or not record_id or not isinstance(version, str) or not version:
            raise SharedMemoryError("a shared record needs record_id and record_version")
        if not written_at.strip():
            raise SharedMemoryError("a shared write needs its written_at time")
        stamped = deepcopy(record)
        stamped["namespace"] = scope.namespace
        attributes = dict(stamped.get("attributes") or {})
        attributes["scope_id"] = scope.scope_id
        attributes["writer_id"] = writer_id
        attributes["written_at"] = written_at
        stamped["attributes"] = attributes
        try:
            json.dumps(stamped, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise SharedMemoryError("a shared record must be strict JSON") from exc
        current = self.store.get(record_id)
        if expected_version is None and current is not None:
            raise SharedMemoryError(f"{record_id!r} exists; pass the version you last read")
        if expected_version is not None:
            if not isinstance(expected_version, str) or not expected_version:
                raise SharedMemoryError("expected_version must be a nonempty version")
            if current is None:
                raise SharedMemoryError(f"{record_id!r} does not exist; nothing to guard against")
            if ((current.get("attributes") or {}).get("scope_id") != scope.scope_id
                    or current.get("namespace") != scope.namespace):
                raise SharedMemoryError(f"{record_id!r} belongs to another scope")
            if version == expected_version:
                raise SharedMemoryError("a shared update must use a new record_version")
            if (re.fullmatch(r"\d+(?:\.\d+)*", version)
                    and re.fullmatch(r"\d+(?:\.\d+)*", expected_version)
                    and tuple(map(int, version.split("."))) <= tuple(map(int, expected_version.split(".")))):
                raise SharedMemoryError("a numeric shared record_version must advance")
        precondition = ({"exists": False} if expected_version is None
                        else {"record_version": expected_version})
        try:
            confirmation = self.store.put(stamped, precondition=precondition)
        except PreconditionFailed as exc:
            raise SharedMemoryError(f"{record_id!r} changed before the guarded write") from exc
        except StoreError as exc:
            raise SharedMemoryError(f"{record_id!r} write outcome is unknown") from exc
        if (not isinstance(confirmation, dict) or confirmation.get("stored") is not True
                or confirmation.get("record_id") != record_id):
            raise SharedMemoryError(f"{record_id!r} write outcome is unknown: invalid acknowledgment")
        try:
            actual = self.store.get(record_id)
        except StoreError as exc:
            raise SharedMemoryError(f"{record_id!r} write outcome is unknown: readback failed") from exc
        # Compare stored forms: a durable store returns a list where the
        # caller supplied a tuple, and that is not a changed record.
        def stored_form(value):
            return json.loads(json.dumps(value, sort_keys=True))
        if not isinstance(actual, dict) or any(stored_form(actual.get(key)) != stored_form(value)
                                                for key, value in stamped.items()):
            raise SharedMemoryError(f"{record_id!r} write outcome is unknown: readback changed")
        return SharedWrite(scope.scope_id, writer_id, record_id, version, written_at)

    def read(self, scope: SharedMemoryScope, reader_id: str, *, reader_organization: str = "",
             query: IntelligenceQuery | None = None) -> list[dict]:
        """Records of the scope the reader may see, each with its writer identity."""
        if not scope.can_read(reader_id, reader_organization):
            raise SharedMemoryError(f"{reader_id!r} may not read scope {scope.scope_id!r}")
        base = query or IntelligenceQuery()
        if base.namespaces and scope.namespace not in base.namespaces:
            raise SharedMemoryError("the query names a namespace outside the scope")
        scoped = IntelligenceQuery(layers=base.layers, source_collections=base.source_collections,
                                   artifact_kinds=base.artifact_kinds, lifecycle=base.lifecycle,
                                   namespaces=(scope.namespace,),
                                   attributes={**base.attributes, "scope_id": {"equals": scope.scope_id}},
                                   limit=base.limit, offset=base.offset)
        return [{"record_id": item["record_id"], "record_version": item.get("record_version", ""),
                 "writer_id": item["attributes"]["writer_id"],
                 "written_at": item["attributes"]["written_at"], "record": item}
                for item in self.store.query(scoped)]

    def writers(self, scope: SharedMemoryScope, reader_id: str) -> dict:
        """How many records each member wrote, visible only to a permitted reader."""
        counts: dict = {}
        for item in self.read(scope, reader_id):
            counts[item["writer_id"]] = counts.get(item["writer_id"], 0) + 1
        return dict(sorted(counts.items()))


def self_test() -> dict:
    """Membership gates writes and reads; every record names its writer; guards catch races."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    def refuses(action) -> bool:
        try:
            action()
        except SharedMemoryError:
            return True
        return False

    from ..catalog.stores.in_memory import EphemeralRecordStore
    memory = SharedMemory(EphemeralRecordStore())
    scope = SharedMemoryScope("project.alpha", "project:alpha", ("loop.planner", "loop.builder"))
    note = {"record_id": "alpha.note.1", "record_version": "1.0.0", "intelligence_layer": "context",
            "source_collection": "learned", "artifact_kind": "note", "lifecycle": "active",
            "attributes": {"topic": "schema"}, "payload": {"text": "the customer table has 12 columns"}}
    first = memory.write(scope, "loop.planner", note, written_at="2026-09-18T10:00:00Z")
    check("a_member_writes_and_the_record_carries_scope_writer_and_time",
          first.writer_id == "loop.planner" and first.scope_id == "project.alpha"
          and memory.store.get("alpha.note.1")["attributes"]["writer_id"] == "loop.planner"
          and memory.store.get("alpha.note.1")["namespace"] == "project:alpha"
          and memory.store.get("alpha.note.1")["attributes"]["written_at"] == "2026-09-18T10:00:00Z")
    check("a_non_member_cannot_write_and_an_unsigned_or_untimed_write_is_refused",
          refuses(lambda: memory.write(scope, "loop.stranger", {**note, "record_id": "alpha.note.2"},
                                       written_at="2026-09-18T10:00:00Z"))
          and refuses(lambda: memory.write(scope, "loop.builder", {"record_id": "x"},
                                           written_at="2026-09-18T10:00:00Z"))
          and refuses(lambda: memory.write(scope, "loop.builder", {**note, "record_id": "alpha.note.3"},
                                           written_at="")))
    second = memory.write(scope, "loop.builder", {**note, "record_version": "1.1.0",
                                                  "payload": {"text": "13 columns after migration"}},
                          written_at="2026-09-18T10:05:00Z", expected_version="1.0.0")
    check("the_other_member_revises_under_the_version_it_read",
          second.record_version == "1.1.0"
          and memory.store.get("alpha.note.1")["attributes"]["writer_id"] == "loop.builder")
    check("a_stale_concurrent_write_is_refused_by_name",
          refuses(lambda: memory.write(scope, "loop.planner", {**note, "record_version": "1.2.0"},
                                       written_at="2026-09-18T10:06:00Z", expected_version="1.0.0"))
          and refuses(lambda: memory.write(scope, "loop.planner", note, written_at="2026-09-18T10:06:00Z"))
          and refuses(lambda: memory.write(scope, "loop.planner", {**note, "record_id": "missing",
                                                                   "record_version": "2.0.0"},
                                           written_at="2026-09-18T10:06:00Z", expected_version="1.0.0")))
    seen = memory.read(scope, "loop.planner")
    check("a_member_reads_the_shared_record_with_its_writer_identity",
          [item["writer_id"] for item in seen] == ["loop.builder"]
          and seen[0]["record"]["payload"]["text"] == "13 columns after migration"
          and memory.writers(scope, "loop.builder") == {"loop.builder": 1})
    other_scope = SharedMemoryScope("project.beta", "project:beta", ("loop.other",))
    memory.write(other_scope, "loop.other", {**note, "record_id": "beta.note.1"},
                 written_at="2026-09-18T11:00:00Z")
    check("scopes_do_not_leak_into_each_other_and_a_stranger_cannot_read",
          [item["record_id"] for item in memory.read(scope, "loop.builder")] == ["alpha.note.1"]
          and refuses(lambda: memory.read(scope, "loop.stranger"))
          and refuses(lambda: memory.write(other_scope, "loop.other", {**note, "record_version": "1.2.0"},
                                           written_at="2026-09-18T11:01:00Z", expected_version="1.1.0"))
          and refuses(lambda: memory.read(scope, "loop.planner",
                                          query=IntelligenceQuery(namespaces=("project:beta",)))))
    organization_scope = SharedMemoryScope("org.wide", "org:example", ("loop.a",),
                                           visibility="organization", organization="example")
    public_scope = SharedMemoryScope("public.notes", "public", ("loop.a",), visibility="public")
    check("visibility_extends_reads_to_the_organization_or_everyone_but_never_writes",
          organization_scope.can_read("loop.z", "example") and not organization_scope.can_read("loop.z", "other")
          and public_scope.can_read("anyone") and not public_scope.can_write("anyone")
          and refuses(lambda: SharedMemoryScope("x", "ns", ("a",), visibility="organization"))
          and refuses(lambda: SharedMemoryScope("x", "ns", ("a", "a")))
          and refuses(lambda: SharedMemoryScope("x", "ns", ()))
          and refuses(lambda: SharedMemoryScope("x", "ns", ("a",), visibility="secret")))
    check("shared_updates_refuse_reused_and_lower_numeric_versions",
          refuses(lambda: memory.write(scope, "loop.builder", {**note, "record_version": "1.1.0"},
                                       written_at="now", expected_version="1.1.0"))
          and refuses(lambda: memory.write(scope, "loop.builder", note,
                                           written_at="now", expected_version="1.1.0"))
          and memory.store.get(note["record_id"])["record_version"] == "1.1.0")

    class LostAcknowledgment(EphemeralRecordStore):
        def put(self, record, *, precondition=None):
            super().put(record, precondition=precondition)
            return None

    uncertain = LostAcknowledgment()
    check("unacknowledged_shared_write_is_not_reported_successful",
          refuses(lambda: SharedMemory(uncertain).write(scope, "loop.builder", note, written_at="now"))
          and uncertain.get(note["record_id"]) is not None)

    class IgnoredWrite(EphemeralRecordStore):
        def put(self, record, *, precondition=None):
            return {"record_id": record["record_id"], "stored": True}

    check("shared_write_requires_matching_readback",
          refuses(lambda: SharedMemory(IgnoredWrite()).write(scope, "loop.builder", note, written_at="now")))

    class GuardRecorder(EphemeralRecordStore):
        def put(self, record, *, precondition=None):
            self.last_precondition = precondition
            return super().put(record, precondition=precondition)

    guarded = GuardRecorder()
    SharedMemory(guarded).write(scope, "loop.builder", note, written_at="now")
    check("shared_creation_uses_an_atomic_absence_guard", guarded.last_precondition == {"exists": False})

    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    class ConcurrentCreationStore(EphemeralRecordStore):
        def __init__(self):
            super().__init__()
            self.barrier = Barrier(2)

        def get(self, record_id, version=None):
            observed = super().get(record_id, version)
            if observed is None:
                self.barrier.wait(timeout=5)
            return observed

    concurrent = SharedMemory(ConcurrentCreationStore())

    def create(writer):
        try:
            concurrent.write(scope, writer, note, written_at="now")
            return True
        except SharedMemoryError:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        wins = list(pool.map(create, scope.members))
    check("concurrent_shared_creation_has_one_winner", sum(wins) == 1)
    # A durable store returns a list where the writer supplied a tuple. That
    # is the same record, so the write must be confirmed, not reported unknown.
    import tempfile
    from pathlib import Path
    from ..catalog.stores.sqlite_store import SQLiteRecordStore
    with tempfile.TemporaryDirectory() as folder:
        durable = SharedMemory(SQLiteRecordStore(str(Path(folder) / "shared.sqlite")))
        try:
            written = durable.write(scope, "loop.planner", {**note, "record_id": "alpha.note.pairs",
                "payload": {"pairs": (("a", 1), ("b", 2))}}, written_at="2026-09-18T10:00:00Z")
        except SharedMemoryError:
            written = None
        check("durable_shared_write_with_a_tuple_is_confirmed",
              written is not None and durable.store.get("alpha.note.pairs")["payload"] == {"pairs": [["a", 1], ["b", 2]]})
        durable.store.close()
    passed = sum(item["passed"] for item in results)
    return {"record_type": "shared_memory_scopes_test/v1", "tests": results, "passed": passed,
            "total": len(results), "all_passed": passed == len(results)}
