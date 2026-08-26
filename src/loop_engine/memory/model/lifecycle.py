"""Lifecycle primitives for the memory package.

MemoryLifecycle is defined in model.memory_type and re-exported here
so callers can import it from a named module rather than the shared
memory_type module.
"""
from __future__ import annotations

from .memory_type import MemoryLifecycle

__all__ = ("MemoryLifecycle",)
