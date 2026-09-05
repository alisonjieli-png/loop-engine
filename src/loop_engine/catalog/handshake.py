"""Store handshake: explicit capability negotiation before any use.

A handshake compares what a consumer needs with what a store adapter
declares. The verdict distinguishes read, write, execute, import, export,
and migration compatibility. Unknown compatibility fails closed.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

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
        if self.selected.get("operations", {}).get(operation) is not True:
            return False
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
    if not isinstance(capabilities, StoreCapabilities):
        raise StoreHandshakeError("negotiation requires StoreCapabilities")
    declared = capabilities.compatibility_verdict
    if declared not in ("compatible", "compatible_read_only", "compatible_export_only"):
        return StoreHandshake(
            adapter_id=capabilities.adapter_id,
            verdict=declared if declared in VERDICTS else "unknown",
            reasons=("store compatibility is not established for use",))
    allowed = {name: value is True for name, value in capabilities.operations.items()}
    if declared == "compatible_read_only":
        allowed = {name: value and name in ("get", "query", "stream", "export")
                   for name, value in allowed.items()}
    elif declared == "compatible_export_only":
        allowed = {name: value and name == "export" for name, value in allowed.items()}
    selected = {"authority": capabilities.authority, "operations": allowed}
    reasons: list[str] = []
    for operation in required_operations:
        if not allowed.get(operation):
            reasons.append(f"operation {operation!r} is not supported")
    for feature in required_query_features:
        if capabilities.query_capabilities.get(feature) is not True:
            reasons.append(f"query feature {feature!r} is not supported")
    if write_requested and not allowed.get("write"):
        reasons.append("write was requested but the store is read-only")
    if reasons:
        return StoreHandshake(
            adapter_id=capabilities.adapter_id, verdict="incompatible",
            reasons=tuple(reasons))
    if declared == "compatible_export_only":
        return StoreHandshake(capabilities.adapter_id, declared, selected=selected)
    if not allowed.get("write") and write_requested is False:
        return StoreHandshake(
            adapter_id=capabilities.adapter_id,
            verdict="compatible_read_only",
            selected=selected,
            reasons=("store is read-only; read operations are permitted",))
    return StoreHandshake(
        adapter_id=capabilities.adapter_id, verdict="compatible",
        selected=selected)


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
    check("compatible_does_not_permit_undeclared_operations",
          not full.permits("execute") and not full.permits("invented"))
    from dataclasses import replace
    for declared in ("unknown", "incompatible", "refused_by_policy",
                     "compatible_with_migration", "compatible_with_degradation",
                     "invented"):
        unresolved = negotiate(replace(writable, compatibility_verdict=declared))
        check("unresolved_compatibility_fails_closed:" + declared,
              not unresolved.permits("query") and not unresolved.permits("write"))
    restricted = replace(writable, compatibility_verdict="compatible_read_only")
    check("declared_read_only_cannot_be_upgraded",
          negotiate(restricted).permits("query")
          and not negotiate(restricted).permits("write")
          and negotiate(restricted, write_requested=True).verdict == "incompatible")
    only_export = negotiate(replace(writable, compatibility_verdict="compatible_export_only"))
    check("declared_export_only_stays_restricted",
          only_export.permits("export") and not only_export.permits("query"))
    ambiguous = negotiate(replace(writable, operations={"query": "true", "write": "false"}))
    check("truthy_strings_do_not_grant_operations",
          not ambiguous.permits("query") and not ambiguous.permits("write"))
    return {"tests": results}
