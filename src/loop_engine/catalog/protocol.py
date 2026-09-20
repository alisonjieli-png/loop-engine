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
ATOMIC_BATCH_OPERATION = "atomic_write_batch"
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
    """Immutable checked writes at one existing store, with no SQL or callbacks."""

    record_documents: tuple[str, ...]
    preconditions: tuple[CatalogRecordPrecondition, ...]
    record_type: str = ATOMIC_BATCH_VERSION

    def __post_init__(self):
        if self.record_type != ATOMIC_BATCH_VERSION:
            raise StoreError("unsupported atomic batch contract")
        object.__setattr__(self, "record_documents", tuple(self.record_documents))
        object.__setattr__(self, "preconditions", tuple(self.preconditions))
        if not self.record_documents or not all(isinstance(row, CatalogRecordPrecondition)
                                               for row in self.preconditions):
            raise StoreError("a batch requires typed writes and preconditions")
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

    @classmethod
    def from_records(cls, records, preconditions):
        try:
            encoded = tuple(json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False)
                            for row in records)
        except (TypeError, ValueError) as exc:
            raise StoreError("batch records require finite JSON") from exc
        return cls(encoded, tuple(preconditions))

    @property
    def records(self):
        return tuple(json.loads(text) for text in self.record_documents)

    @property
    def digest(self):
        value = {"record_type": self.record_type, "records": self.records,
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
    """Optional negotiated extension, not required of read-only or older adapters."""

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
    """Prove the protocol refuses undeclared operations."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    import tempfile
    import os
    from .stores.package_jsonl import PackageJsonlStore
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
    return {"tests": results}
