"""Store handshake: explicit capability negotiation before any use.

A handshake compares what a consumer needs with what a store adapter
declares. The verdict distinguishes read, write, execute, import, export,
and migration compatibility. Unknown compatibility fails closed.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict

from .capabilities import StoreCapabilities

#: Verdicts a handshake may return.
VERDICTS = (
    "compatible", "compatible_with_migration", "compatible_with_degradation",
    "compatible_read_only", "compatible_export_only", "incompatible",
    "unknown", "refused_by_policy",
)


class StoreHandshakeError(ValueError):
    """A handshake request or response is invalid."""


@dataclass(frozen=True)
class StoreHandshake:
    """One negotiated result between a consumer and a store adapter."""

    adapter_id: str
    verdict: str
    selected: dict = field(default_factory=dict)
    required_migrations: tuple[str, ...] = ()
    disabled_optional_features: tuple[str, ...] = ()
    degraded_behavior: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.verdict not in VERDICTS:
            raise StoreHandshakeError(f"verdict must be one of {VERDICTS}")

    def permits(self, operation: str) -> bool:
        """Whether this verdict allows one operation to proceed."""
        if self.verdict == "compatible":
            return True
        if self.verdict == "compatible_read_only":
            return operation in ("get", "query", "stream", "export")
        if self.verdict == "compatible_export_only":
            return operation == "export"
        return False

    def to_dict(self) -> dict:
        return asdict(self)


def negotiate(capabilities: StoreCapabilities, *,
              required_operations: tuple[str, ...] = (),
              required_query_features: tuple[str, ...] = (),
              write_requested: bool = False) -> StoreHandshake:
    """Negotiate one handshake from a store's declared capabilities.

    The verdict is computed, never guessed. Missing required operations or
    query features produce an explicit incompatible verdict with reasons.
    """
    reasons: list[str] = []
    disabled: list[str] = []
    for operation in required_operations:
        if not capabilities.supports(operation):
            reasons.append(f"operation {operation!r} is not supported")
    for feature in required_query_features:
        if not capabilities.query_capabilities.get(feature):
            reasons.append(f"query feature {feature!r} is not supported")
    if write_requested and not capabilities.supports("write"):
        reasons.append("write was requested but the store is read-only")
    if reasons:
        return StoreHandshake(
            adapter_id=capabilities.adapter_id, verdict="incompatible",
            reasons=tuple(reasons))
    if not capabilities.supports("write") and write_requested is False:
        return StoreHandshake(
            adapter_id=capabilities.adapter_id,
            verdict="compatible_read_only",
            selected={"authority": capabilities.authority},
            reasons=("store is read-only; read operations are permitted",))
    return StoreHandshake(
        adapter_id=capabilities.adapter_id, verdict="compatible",
        selected={"authority": capabilities.authority})


def self_test() -> dict:
    """Prove handshakes fail closed and never guess compatibility."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    read_only = StoreCapabilities(
        adapter_id="core.duckdb-files", adapter_version="1.0.0",
        adapter_kind="file_sql", engine="duckdb",
        operations={"get": True, "query": True, "stream": True,
                    "write": False, "export": True, "import": False},
        query_capabilities={"projection": True, "filter": True},
        authority="authoritative")
    ok = negotiate(read_only, required_operations=("query",))
    check("read_only_store_negotiates_read_verdict",
          ok.verdict == "compatible_read_only" and ok.permits("query")
          and not ok.permits("write"))
    refused = negotiate(read_only, required_operations=("write",))
    check("write_against_read_only_store_is_incompatible",
          refused.verdict == "incompatible"
          and "write" in " ".join(refused.reasons))
    missing = negotiate(
        read_only, required_query_features=("vector_search",))
    check("missing_query_feature_is_incompatible",
          missing.verdict == "incompatible"
          and any("vector_search" in r for r in missing.reasons))
    writable = StoreCapabilities(
        adapter_id="local.sqlite", adapter_version="1.0.0",
        adapter_kind="embedded_database", engine="sqlite",
        operations={"get": True, "query": True, "write": True,
                    "export": True, "import": True},
        query_capabilities={"projection": True, "filter": True},
        transactions={"supported": True},
        authority="authoritative")
    full = negotiate(writable, required_operations=("query", "write"),
                     write_requested=True)
    check("writable_store_negotiates_full_verdict",
          full.verdict == "compatible" and full.permits("write"))
    return {"tests": results}
