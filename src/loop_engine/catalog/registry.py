"""Adapter registry: swappable backends behind one protocol.

The registry lets deployments swap query engines and databases without
changing the catalog contract. An adapter registers its capabilities;
the catalog negotiates a handshake before use. DuckDB is the default
local engine, not the ontology and not the only backend.
"""
from __future__ import annotations

from .capabilities import StoreCapabilities
from .handshake import StoreHandshake, negotiate
from .protocol import CatalogStore, StoreError


class AdapterRegistry:
    """Named adapter registration with capability negotiation."""

    def __init__(self) -> None:
        self._adapters: dict[str, CatalogStore] = {}

    def register(self, adapter: CatalogStore, *, replace: bool = False
                 ) -> None:
        adapter_id = adapter.capabilities().adapter_id
        if adapter_id in self._adapters and not replace:
            raise StoreError(f"adapter {adapter_id!r} is already registered")
        self._adapters[adapter_id] = adapter

    def unregister(self, adapter_id: str) -> None:
        self._adapters.pop(adapter_id, None)

    def get(self, adapter_id: str) -> CatalogStore:
        adapter = self._adapters.get(adapter_id)
        if adapter is None:
            raise StoreError(f"adapter {adapter_id!r} is not registered")
        return adapter

    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._adapters))

    def capabilities(self) -> dict[str, StoreCapabilities]:
        return {adapter_id: adapter.capabilities()
                for adapter_id, adapter in self._adapters.items()}

    def negotiate(self, adapter_id: str, *,
                  required_operations: tuple[str, ...] = (),
                  required_query_features: tuple[str, ...] = (),
                  write_requested: bool = False) -> StoreHandshake:
        """Negotiate one handshake against a registered adapter."""
        adapter = self.get(adapter_id)
        return negotiate(
            adapter.capabilities(),
            required_operations=required_operations,
            required_query_features=required_query_features,
            write_requested=write_requested)

    def select(self, *, required_operations: tuple[str, ...] = (),
               required_query_features: tuple[str, ...] = (),
               write_requested: bool = False,
               preferred: tuple[str, ...] = ()) -> tuple[str, StoreHandshake]:
        """Select the first registered adapter that satisfies the request.

        Preferred adapters are tried first. The selection is explicit and
        receipted; an unsatisfiable request raises rather than silently
        degrading.
        """
        order = [a for a in preferred if a in self._adapters]
        order += [a for a in self._adapters if a not in order]
        for adapter_id in order:
            handshake = self.negotiate(
                adapter_id,
                required_operations=required_operations,
                required_query_features=required_query_features,
                write_requested=write_requested)
            if handshake.verdict in ("compatible", "compatible_read_only"):
                return adapter_id, handshake
        raise StoreError(
            "no registered adapter satisfies the request "
            f"(operations={required_operations}, "
            f"features={required_query_features}, "
            f"write={write_requested})")


def self_test() -> dict:
    """Prove adapters are swappable behind the same contract."""
    import tempfile
    import os

    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    from .stores.in_memory import EphemeralRecordStore
    from .stores.sqlite_store import SQLiteRecordStore

    registry = AdapterRegistry()
    registry.register(EphemeralRecordStore())
    with tempfile.TemporaryDirectory() as tmp:
        registry.register(SQLiteRecordStore(os.path.join(tmp, "c.sqlite")))
        check("registry_lists_registered_adapters",
              set(registry.ids()) == {"local.in-memory", "local.sqlite"})
        selected, handshake = registry.select(
            required_operations=("query", "write"), write_requested=True,
            preferred=("local.sqlite",))
        check("preferred_adapter_is_selected",
              selected == "local.sqlite"
              and handshake.verdict == "compatible")
        selected, handshake = registry.select(
            required_operations=("query",))
        check("read_only_adapter_satisfies_read_request",
              handshake.verdict in ("compatible", "compatible_read_only"))
        try:
            registry.select(required_query_features=("vector_search",))
            check("unsatisfiable_request_is_refused", False)
        except StoreError:
            check("unsatisfiable_request_is_refused", True)
        try:
            registry.register(EphemeralRecordStore())
            check("duplicate_registration_is_refused", False)
        except StoreError:
            check("duplicate_registration_is_refused", True)
        registry.unregister("local.sqlite")
        check("unregister_removes_adapter",
              "local.sqlite" not in registry.ids())
    return {"tests": results}
