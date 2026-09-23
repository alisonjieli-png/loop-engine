"""The CatalogStore protocol: one contract for every backend.

Every store adapter implements this protocol for the operations it
supports and declares its real capabilities in a handshake. Unsupported
operations raise UnsupportedOperationError; they never silently degrade.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Protocol, runtime_checkable

from .capabilities import StoreCapabilities
from .query import IntelligenceQuery


class StoreError(RuntimeError):
    """A store operation failed."""


class UnsupportedOperationError(StoreError):
    """The store does not support the requested operation."""


class PreconditionFailed(StoreError):
    """The authoritative store refused an expected version or absence check."""


ATOMIC_BATCH_VERSION = "catalog_atomic_write_batch/v1"
#: A batch that removes records is its own record version. An adapter that
#: declared only the first version refuses it, so no adapter can apply the
#: writes of a removal batch and quietly skip its removals.
ATOMIC_REMOVAL_BATCH_VERSION = "catalog_atomic_write_batch/v2"
ATOMIC_BATCH_OPERATION = "atomic_write_batch"
#: The optional operation a store declares when it applies removal batches.
ATOMIC_REMOVAL_OPERATION = "atomic_record_removal"
BATCH_ACKNOWLEDGMENT_VERSION = "catalog_batch_acknowledgment/v1"


@dataclass(frozen=True)
class CatalogRecordPrecondition:
    """An exact read-set version or absence requirement, including read-only guards."""

    record_id: str
    record_version: str | None = None
    must_not_exist: bool = False

    def __post_init__(self):
        if not isinstance(self.record_id, str) or not self.record_id.strip():
            raise StoreError("a batch precondition needs a record identity")
        if type(self.must_not_exist) is not bool:
            raise StoreError("absence must be an exact Boolean")
        if self.must_not_exist:
            if self.record_version is not None:
                raise StoreError("absence and version preconditions are mutually exclusive")
        elif not isinstance(self.record_version, str) or not self.record_version:
            raise StoreError("a present-record precondition needs an exact version")


@dataclass(frozen=True)
class CatalogWriteBatch:
    """Immutable checked writes and exact removals at one existing store, with no SQL or callbacks.

    A removal names one record identity, and the same batch must hold an exact
    version precondition for it, so a record is removed only at the version the
    caller read. A missing record, or one at another version, fails that
    precondition and the whole batch is refused. A record is never written and
    removed in one batch. A batch that removes anything is
    `catalog_atomic_write_batch/v2`; a batch that only writes stays
    `catalog_atomic_write_batch/v1`.
    """

    record_documents: tuple[str, ...]
    preconditions: tuple[CatalogRecordPrecondition, ...]
    removals: tuple[str, ...] = ()
    record_type: str = ATOMIC_BATCH_VERSION

    def __post_init__(self):
        object.__setattr__(self, "record_documents", tuple(self.record_documents))
        object.__setattr__(self, "preconditions", tuple(self.preconditions))
        object.__setattr__(self, "removals", tuple(self.removals))
        if self.record_type != (ATOMIC_REMOVAL_BATCH_VERSION if self.removals else ATOMIC_BATCH_VERSION):
            raise StoreError("unsupported atomic batch contract")
        if not (self.record_documents or self.removals) or not all(
                isinstance(row, CatalogRecordPrecondition) for row in self.preconditions):
            raise StoreError("a batch requires typed writes or removals and typed preconditions")
        expected = {row.record_id: row for row in self.preconditions}
        if len(expected) != len(self.preconditions):
            raise StoreError("batch precondition identities must be unique")
        ids = []
        for text in self.record_documents:
            try:
                row = json.loads(text)
                normalized = json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False)
            except (TypeError, ValueError) as exc:
                raise StoreError("batch records require finite canonical JSON") from exc
            if not isinstance(row, dict) or text != normalized:
                raise StoreError("batch records require canonical JSON objects")
            identity, version = row.get("record_id"), row.get("record_version")
            if not isinstance(identity, str) or not identity or not isinstance(version, str) or not version:
                raise StoreError("batch records require exact identity and new version")
            if identity not in expected:
                raise StoreError("every batch write needs a precondition")
            if expected[identity].record_version == version:
                raise StoreError("a batch update must advance its exact version token")
            ids.append(identity)
        if len(set(ids)) != len(ids):
            raise StoreError("batch write identities must be unique")
        for identity in self.removals:
            if not isinstance(identity, str) or not identity.strip():
                raise StoreError("a removal needs a record identity")
            if identity not in expected or expected[identity].must_not_exist:
                raise StoreError("every removal needs an exact version precondition")
        if len(set(self.removals)) != len(self.removals):
            raise StoreError("batch removal identities must be unique")
        if set(self.removals) & set(ids):
            raise StoreError("a record cannot be written and removed in one batch")

    @classmethod
    def from_records(cls, records, preconditions, removals=()):
        """Build a batch; the record version follows from whether it removes anything."""
        try:
            encoded = tuple(json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False)
                            for row in records)
        except (TypeError, ValueError) as exc:
            raise StoreError("batch records require finite JSON") from exc
        removals = tuple(removals)
        return cls(encoded, tuple(preconditions), removals,
                   ATOMIC_REMOVAL_BATCH_VERSION if removals else ATOMIC_BATCH_VERSION)

    @property
    def records(self):
        return tuple(json.loads(text) for text in self.record_documents)

    @property
    def digest(self):
        """One digest over the version, the writes, the removals and the read set.

        An acknowledgment names this digest, so an acknowledgment for a batch
        that removes anything else, or writes anything else, is not one for
        this batch.
        """
        value = {"record_type": self.record_type, "records": self.records, "removals": list(self.removals),
                 "preconditions": [(row.record_id, row.record_version, row.must_not_exist)
                                   for row in self.preconditions]}
        return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                        allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class CatalogBatchAcknowledgment:
    """Exact acknowledgment; missing or unknown commitment is never success."""

    batch_digest: str
    committed: bool | None
    record_type: str = BATCH_ACKNOWLEDGMENT_VERSION

    def __post_init__(self):
        if (not isinstance(self.batch_digest, str) or len(self.batch_digest) != 64
                or any(ch not in "0123456789abcdef" for ch in self.batch_digest)
                or (self.committed is not None and type(self.committed) is not bool)
                or self.record_type != BATCH_ACKNOWLEDGMENT_VERSION):
            raise StoreError("invalid atomic batch acknowledgment")


@runtime_checkable
class AtomicCatalogStore(Protocol):
    """Optional negotiated extension, not required of read-only or older adapters.

    A store that also applies removal batches declares the optional operation
    `atomic_record_removal` and the batch version
    `catalog_atomic_write_batch/v2` in its transactions. A store that declares
    neither is refused a removal batch before any effect.
    """

    def apply_batch(self, request: CatalogWriteBatch) -> CatalogBatchAcknowledgment: ...


def require_atomic_batch(store) -> None:
    """Negotiate exact optional semantics before a domain attempts a write."""
    from .handshake import negotiate
    capabilities = store.capabilities()
    decision = negotiate(capabilities, required_operations=("get", "write", ATOMIC_BATCH_OPERATION),
                         write_requested=True)
    if (not decision.permits(ATOMIC_BATCH_OPERATION) or capabilities.authority != "authoritative"
            or capabilities.transactions.get("atomic_batch_version") != ATOMIC_BATCH_VERSION
            or capabilities.transactions.get("atomic_read_set") is not True
            or not callable(getattr(store, "apply_batch", None))):
        raise UnsupportedOperationError("exact authoritative atomic batch contract is unavailable")


def require_atomic_removal(store) -> None:
    """Negotiate the removal extension before a batch that removes anything is built or sent.

    The store must meet the whole atomic batch contract and declare both the
    removal operation and the exact removal batch version. Anything less is
    refused here with `UnsupportedOperationError`, before any effect, so no
    caller can mistake an adapter that ignores removals for one that removed
    nothing.
    """
    require_atomic_batch(store)
    from .handshake import negotiate
    capabilities = store.capabilities()
    decision = negotiate(capabilities, required_operations=(
        "get", "write", ATOMIC_BATCH_OPERATION, ATOMIC_REMOVAL_OPERATION), write_requested=True)
    if (not decision.permits(ATOMIC_REMOVAL_OPERATION)
            or capabilities.transactions.get("atomic_removal_batch_version") != ATOMIC_REMOVAL_BATCH_VERSION):
        raise UnsupportedOperationError("exact authoritative atomic removal contract is unavailable")


@runtime_checkable
class CatalogStore(Protocol):
    """Backend-neutral record store contract."""

    def capabilities(self) -> StoreCapabilities: ...

    def get(self, record_id: str, version: str | None = None) -> dict | None:
        ...

    def query(self, query: IntelligenceQuery) -> list[dict]: ...

    def stream(self, query: IntelligenceQuery):
        ...

    def put(self, record: dict, *, precondition: dict | None = None) -> dict:
        ...

    def export(self, selection: dict | None = None) -> dict: ...

    def import_bundle(self, bundle: dict) -> dict: ...

    def health(self) -> dict: ...

    def close(self) -> None: ...


def require_operation(store: CatalogStore, operation: str) -> None:
    """Refuse an operation the store did not declare."""
    if not store.capabilities().supports(operation):
        raise UnsupportedOperationError(
            f"store {store.capabilities().adapter_id!r} does not support "
            f"operation {operation!r}")


def self_test() -> dict:
    """Prove the protocol refuses undeclared operations and ambiguous removals."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    def refuses(action, error=StoreError):
        try:
            action()
        except error:
            return True
        return False

    import tempfile
    import os
    from dataclasses import replace
    from .stores.package_jsonl import PackageJsonlStore
    from .stores.sqlite_store import SQLiteRecordStore
    with tempfile.TemporaryDirectory() as tmp:
        shard = os.path.join(tmp, "part-00000.jsonl")
        with open(shard, "w", encoding="utf-8") as handle:
            handle.write('{"record_id": "r1"}\n')
        store = PackageJsonlStore((shard,))
        require_operation(store, "query")
        check("declared_operation_is_permitted", True)
        try:
            require_operation(store, "write")
            check("undeclared_operation_is_refused", False)
        except UnsupportedOperationError:
            check("undeclared_operation_is_refused", True)
        sqlite = SQLiteRecordStore(os.path.join(tmp, "catalog.sqlite"))
        declared = sqlite.capabilities()

        def declaring(**changes):
            answer = replace(declared, **changes)
            return type("DeclaredStore", (), {"capabilities": lambda self: answer,
                                              "apply_batch": lambda self, request: None})()
        writes_only = declaring(operations={**declared.operations, ATOMIC_REMOVAL_OPERATION: False})
        other_version = declaring(transactions={**declared.transactions,
                                                "atomic_removal_batch_version": "catalog_atomic_write_batch/v3"})
        require_atomic_removal(sqlite)
        check("a_store_must_declare_removal_and_its_exact_version_before_any_removal",
              refuses(lambda: require_atomic_removal(store), UnsupportedOperationError)
              and refuses(lambda: require_atomic_removal(writes_only), UnsupportedOperationError)
              and refuses(lambda: require_atomic_removal(other_version), UnsupportedOperationError)
              and not refuses(lambda: require_atomic_batch(writes_only), UnsupportedOperationError))
        sqlite.close()
    held, also = CatalogRecordPrecondition("held", "1"), CatalogRecordPrecondition("also", "1")
    created = CatalogRecordPrecondition("new", must_not_exist=True)
    write = {"record_id": "new", "record_version": "1"}
    check("a_batch_that_removes_carries_its_own_version",
          CatalogWriteBatch.from_records((), (held,), ("held",)).record_type == ATOMIC_REMOVAL_BATCH_VERSION
          and CatalogWriteBatch.from_records((write,), (created,)).record_type == ATOMIC_BATCH_VERSION
          and refuses(lambda: CatalogWriteBatch((), (held,), ("held",), ATOMIC_BATCH_VERSION))
          and refuses(lambda: CatalogWriteBatch((json.dumps(write, sort_keys=True, separators=(",", ":")),),
                                                (created,), (), ATOMIC_REMOVAL_BATCH_VERSION)))
    check("a_removal_needs_an_exact_version_precondition",
          refuses(lambda: CatalogWriteBatch.from_records((), (), ("held",)))
          and refuses(lambda: CatalogWriteBatch.from_records(
              (), (CatalogRecordPrecondition("held", must_not_exist=True),), ("held",))))
    check("a_record_is_never_written_and_removed_in_one_batch",
          refuses(lambda: CatalogWriteBatch.from_records(
              ({"record_id": "held", "record_version": "2"},), (held,), ("held",))))
    check("an_empty_batch_and_a_repeated_removal_are_refused",
          refuses(lambda: CatalogWriteBatch.from_records((), ()))
          and refuses(lambda: CatalogWriteBatch.from_records((), (held,), ("held", "held")))
          and refuses(lambda: CatalogWriteBatch.from_records((), (held,), ("",))))
    mine = CatalogWriteBatch.from_records((), (held, also), ("held",))
    check("the_batch_digest_covers_the_removals",
          mine.digest != CatalogWriteBatch.from_records((), (held, also), ("also",)).digest
          and mine.digest == CatalogWriteBatch.from_records((), (held, also), ("held",)).digest)
    return {"tests": results}
