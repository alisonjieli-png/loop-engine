"""Legacy serialized ``loop_node`` record reader namespace.

# HARD ARCHITECTURE INVARIANT - DO NOT REMOVE OR WEAKEN:
#
# Loop is the sole concrete operational runtime and executable graph vertex.
# This package must never contain an executor,
# a role-specific subclass, or a mode-specific subclass.
"""
from __future__ import annotations

from ...ontology.loop_node import read_legacy_loop_node_record

__all__ = ("read_legacy_loop_node_record",)
