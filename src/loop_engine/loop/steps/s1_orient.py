"""STEP 1 — Reconstruct the latest accepted problem state and assemble context.

CONTRACT   PractitionerState  ->  Situation
REQUIRED   yes (you always orient)
WAYS       cached state · retrieval · deterministic reconstruction
EXTEND     provide an `orient` impl returning a Situation; register context
           sources as searchable resources in the store.

Rebuild accepted state from immutable snapshots — never a chat transcript.
Separate facts / claims / assumptions / failures.  Record what was included,
excluded, summarized, stale, or masked.
"""
from ...loop.kernel import Situation, default_orient
from ...static_architecture.store_serve import SolverStore, core_seed
from ...strings.context import CONTEXT_POLICIES, build_view

__all__ = ["Situation", "default_orient", "SolverStore", "core_seed",
           "CONTEXT_POLICIES", "build_view"]
