"""Backend-neutral intelligence access: one catalog, many store adapters.

The catalog resolves the same logical records whether they are materialized
as package JSONL, DuckDB tables, SQLite rows, a server database, a portable
bundle, or a remote service. A store adapter declares its real capabilities
in a handshake before it is used; unsupported operations fail explicitly.

This package adds no runtime. Querying, materializing, synchronizing,
exporting, and importing perform work through ordinary Intelligence-role
or Solution-role Loops. The access layer is a capability used by Loops,
not a second executor.
"""
from __future__ import annotations

from importlib import import_module as _import_module

_PUBLIC = {
    "StoreCapabilities": ("capabilities", "StoreCapabilities"),
    "StoreHandshake": ("handshake", "StoreHandshake"),
    "StoreHandshakeError": ("handshake", "StoreHandshakeError"),
    "IntelligenceQuery": ("query", "IntelligenceQuery"),
    "QueryError": ("query", "QueryError"),
    "CatalogStore": ("protocol", "CatalogStore"),
    "StoreError": ("protocol", "StoreError"),
    "UnsupportedOperationError": ("protocol", "UnsupportedOperationError"),
    "CompositeCatalog": ("composite", "CompositeCatalog"),
    "AdapterRegistry": ("registry", "AdapterRegistry"),
    "PackageJsonlStore": ("stores.package_jsonl", "PackageJsonlStore"),
    "DuckDBFileQueryEngine": ("stores.duckdb_files", "DuckDBFileQueryEngine"),
    "DuckDBRecordStore": ("stores.duckdb_store", "DuckDBRecordStore"),
    "SQLiteRecordStore": ("stores.sqlite_store", "SQLiteRecordStore"),
    "EphemeralRecordStore": ("stores.in_memory", "EphemeralRecordStore"),
    "run_store_conformance": ("conformance", "run_store_conformance"),
}

__all__ = tuple(_PUBLIC)


def __getattr__(name: str):
    """Load a documented public name only when it is requested."""
    target = _PUBLIC.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module, attribute = target
    return getattr(_import_module(f"{__name__}.{module}"), attribute)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_PUBLIC))
