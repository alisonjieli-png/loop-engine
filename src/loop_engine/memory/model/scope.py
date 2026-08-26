"""Scope primitives for the memory package.

MemoryScope bounds who may see a persistent memory record. It is
defined in model.memory_type and re-exported here for a stable
import path.
"""
from __future__ import annotations

from .memory_type import MemoryScope

__all__ = ("MemoryScope",)
