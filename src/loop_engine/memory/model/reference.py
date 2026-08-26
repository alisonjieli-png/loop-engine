"""Reference primitives for the memory package.

MemoryRef is the typed reference to one exact persistent memory
record version. It is defined in model.memory_type and re-exported
here for a stable import path.
"""
from __future__ import annotations

from .memory_type import MemoryRef

__all__ = ("MemoryRef",)
