"""The four-memory architecture: working, episodic, semantic, procedural.

A memory type answers: what kind of retained cognition is this?

- working: bounded, run-scoped state for one Loop's current cycle;
- episodic: a bounded, time-ordered experience with Run History provenance;
- semantic: generalized knowledge with evidence, validity, and scope;
- procedural: contracted, versioned, evidence-backed know-how.

Memory types are independent of Functional Intelligence Domains, which
answer why intelligence is useful. Memory records are data. Memory
operations that perform governed work execute through ordinary Loops.
There is no Memory role and no MemoryNode class.
"""
from __future__ import annotations

from importlib import import_module as _import_module

_PUBLIC = {
    "MEMORY_TYPES": ("model.memory_type", "MEMORY_TYPES"),
    "MemoryType": ("model.memory_type", "MemoryType"),
    "MemoryIdentity": ("model.identity", "MemoryIdentity"),
    "MemoryRef": ("model.reference", "MemoryRef"),
    "MemoryScope": ("model.scope", "MemoryScope"),
    "MemoryLifecycle": ("model.lifecycle", "MemoryLifecycle"),
    "EpisodicMemoryRecord": ("episodic.record", "EpisodicMemoryRecord"),
    "SemanticMemoryRecord": ("semantic.record", "SemanticMemoryRecord"),
    "ProceduralMemoryRecord": (
        "procedural.record", "ProceduralMemoryRecord"),
    "WorkingMemoryState": ("working.state", "WorkingMemoryState"),
    "MemoryQuery": ("query.query", "MemoryQuery"),
    "MemoryRetrievalReceipt": (
        "query.receipts", "MemoryRetrievalReceipt"),
    "InMemoryMemoryStore": ("storage.store", "InMemoryMemoryStore"),
}

__all__ = tuple(_PUBLIC)


def __getattr__(name: str):
    target = _PUBLIC.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module, attribute = target
    return getattr(_import_module(f"{__name__}.{module}"), attribute)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_PUBLIC))
