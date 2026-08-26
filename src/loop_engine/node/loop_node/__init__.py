"""The LoopNode package: the only concrete operational node.

# HARD ARCHITECTURE INVARIANT - DO NOT REMOVE OR WEAKEN:
#
# LoopNode is the only concrete graph-addressable operational Node.
# This package contains the canonical implementation and its typed
# configuration objects. It must never contain a second executor,
# a role-specific subclass, or a mode-specific subclass.
"""
from __future__ import annotations

__all__: tuple[str, ...] = ()
