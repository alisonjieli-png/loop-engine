"""Loop integration: memory presets running through ordinary Loops.

Memory operations that perform governed work execute through ordinary
Loops using existing roles and run modes. There is no Memory role and
no MemoryNode. These presets bind the four-memory subsystem to the
canonical Loop runtime.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..memory.model.memory_type import MemoryScope
from ..memory.working.state import WorkingMemoryPolicy


@dataclass(frozen=True)
class MemoryConfiguration:
    """Memory policies bound to one Loop definition or invocation."""

    working_policy: WorkingMemoryPolicy = field(
        default_factory=WorkingMemoryPolicy)
    scope: MemoryScope = MemoryScope.RUN
    recall_enabled: bool = True
    episode_capture: bool = False
    consolidation_enabled: bool = False
    write_policy: str = "candidate_only"

    def __post_init__(self) -> None:
        if self.write_policy not in ("candidate_only", "trusted_import",
                                     "none"):
            raise ValueError(
                "write_policy must be candidate_only, trusted_import, "
                "or none")


def recall_through_loop(query, store, *, parent=None,
                        ledger=None) -> dict:
    """Run a memory retrieval as a deterministic Intelligence Loop."""
    from ..loop.encapsulate import as_practitioner_loop

    def _run(_inputs=None) -> dict:
        receipt = store.query(query)
        return {"receipt": receipt.to_dict(),
                "selected": [r.to_dict() for r in receipt.selected]}

    return as_practitioner_loop("memory recall", _run, parent=parent,
                                ledger=ledger)


def self_test() -> dict:
    """Prove memory presets run through the canonical Loop runtime."""
    from ..memory.model.memory_type import (MemoryIdentity, MemoryType,
                                            MemoryLifecycle)
    from ..memory.semantic.record import SemanticMemoryRecord
    from ..memory.query.query import MemoryQuery
    from ..memory.storage.store import InMemoryMemoryStore

    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    record = SemanticMemoryRecord(
        identity=MemoryIdentity("mem.sem.1", "1.0.0", "f" * 64,
                                MemoryType.SEMANTIC),
        subject="repository", predicate="requires_python",
        object_value=">=3.10", claim_type="observed",
        lifecycle=MemoryLifecycle.ACTIVE)
    store = InMemoryMemoryStore([record])
    query = MemoryQuery(memory_types=("semantic",), text="python")
    result = recall_through_loop(query, store)
    check("memory_recall_runs_through_the_canonical_loop",
          result["loop_id"].startswith("loop")
          and result["value"]["selected"]
          and result["value"]["selected"][0]["record_id"] == "mem.sem.1")

    config = MemoryConfiguration()
    check("memory_configuration_validates",
          config.recall_enabled and config.episode_capture is False)
    try:
        MemoryConfiguration(write_policy="bogus")
        check("unknown_write_policy_is_refused", False)
    except ValueError:
        check("unknown_write_policy_is_refused", True)
    return {"tests": results}
