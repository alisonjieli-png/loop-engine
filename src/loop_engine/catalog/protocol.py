"""The CatalogStore protocol: one contract for every backend.

Every store adapter implements this protocol for the operations it
supports and declares its real capabilities in a handshake. Unsupported
operations raise UnsupportedOperationError; they never silently degrade.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from .capabilities import StoreCapabilities
from .query import IntelligenceQuery


class StoreError(RuntimeError):
    """A store operation failed."""


class UnsupportedOperationError(StoreError):
    """The store does not support the requested operation."""


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
