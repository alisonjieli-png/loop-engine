"""Store capability declarations: what a backend can actually do.

A store adapter reports its capabilities before any query runs. The catalog
planner uses this declaration to select pushdown operations and to refuse
operations the backend cannot perform. A capability is never guessed.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict

#: Authority roles a store may hold for a record collection.
AUTHORITY_ROLES = (
    "authoritative", "primary_replica", "read_only_replica", "mirror",
    "staging", "cache", "derived_projection", "archive",
)

#: Result formats an adapter may return.
RESULT_FORMATS = (
    "python_records", "arrow_table", "arrow_record_batch_reader", "jsonl",
    "parquet",
)


@dataclass(frozen=True)
class StoreCapabilities:
    """The exact operations and query features one store adapter supports."""

    adapter_id: str
    adapter_version: str
    adapter_kind: str
    engine: str = ""
    source_collections: tuple[str, ...] = ()
    operations: dict = field(default_factory=dict)
    query_capabilities: dict = field(default_factory=dict)
    pushdown: dict = field(default_factory=dict)
    transactions: dict = field(default_factory=dict)
    result_formats: tuple[str, ...] = ("python_records",)
    materializations: tuple[str, ...] = ()
    authority: str = "authoritative"
    compatibility_verdict: str = "compatible"

    def __post_init__(self) -> None:
        if self.authority not in AUTHORITY_ROLES:
            raise ValueError(f"authority must be one of {AUTHORITY_ROLES}")
        unknown = [f for f in self.result_formats if f not in RESULT_FORMATS]
        if unknown:
            raise ValueError(f"unknown result formats {unknown}")

    def supports(self, operation: str) -> bool:
        return bool(self.operations.get(operation))

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_mapping(cls, value: dict) -> "StoreCapabilities":
        return cls(**value)


def self_test() -> dict:
    """Prove capability declarations stay closed and honest."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    caps = StoreCapabilities(
        adapter_id="core.duckdb-files", adapter_version="1.0.0",
        adapter_kind="file_sql", engine="duckdb",
        source_collections=("core",),
        operations={"get": True, "query": True, "stream": True,
                    "write": False, "export": True, "import": False},
        query_capabilities={"projection": True, "filter": True,
                           "join": True, "aggregation": True,
                           "relationship_traversal": False,
                           "full_text_search": False,
                           "vector_search": False},
        pushdown={"projection": True, "filter": True, "limit": True,
                  "order": True},
        transactions={"supported": False, "snapshot_reads": True},
        result_formats=("python_records", "arrow_table"),
        materializations=("jsonl", "parquet"),
        authority="authoritative",
    )
    check("read_only_file_engine_declares_no_write",
          caps.supports("query") and not caps.supports("write"))
    check("capabilities_round_trip_through_mapping",
          StoreCapabilities.from_mapping(caps.to_dict()) == caps)
    try:
        StoreCapabilities(adapter_id="x", adapter_version="1.0.0",
                          adapter_kind="file_sql", authority="bogus")
        check("unknown_authority_is_refused", False)
    except ValueError:
        check("unknown_authority_is_refused", True)
    return {"tests": results}
