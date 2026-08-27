"""Compatibility reader for immutable serialized ``loop_node`` records.

Active code has no ``LoopNode`` concept. Historical records are migrated into
``LoopDefinitionRecord`` and new code never emits the legacy kind.
"""
from __future__ import annotations

from .loop_definition_record import (
    LoopDefinitionProjectionRequest,
    LoopDefinitionRecord,
)

def read_legacy_loop_node_record(value: dict) -> LoopDefinitionRecord:
    """Migrate one exact historical record into the canonical projection."""
    if value.get("kind") != "loop_node":
        raise ValueError("legacy reader requires kind='loop_node'")
    return LoopDefinitionRecord.from_mapping(value)

__all__ = (
    "LoopDefinitionProjectionRequest", "LoopDefinitionRecord",
    "read_legacy_loop_node_record",
)
