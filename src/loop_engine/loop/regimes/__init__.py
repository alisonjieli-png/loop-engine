"""Regime library — the growing set of ways to answer "select the next action".

This subpackage is where regimes accumulate.  The deterministic reflexes and the
test/optimization regimes register with one call (`register_library`); the
memory-recall and model-backed regimes are factories (they need a store or a
model client), re-exported here so a caller wires them in.  Adding a new regime
is: write a `(Knowledge) -> NextActionProposal | None` function, give it a category
and a cost, and append it to a SPECS list (or register it directly).
"""

from __future__ import annotations

from ...loop.registry import ResolverRegistry, DEFAULT_REGISTRY
from . import deterministic_reflexes, test_and_optimize
from .memory_recall import (make_recall_resolver, make_solved_route_replay,
                            make_analogy_transfer)
from .model_backed import (make_single_model_regime, make_council_regime,
                           make_research_regime)

# The deterministic, self-testable library that registers by default.
LIBRARY_SPECS = (list(deterministic_reflexes.SPECS)
                 + list(test_and_optimize.SPECS))


def register_library(registry: ResolverRegistry = DEFAULT_REGISTRY, *,
                     replace: bool = True) -> ResolverRegistry:
    """Register every deterministic reflex and test/optimization regime."""
    for name, category, fn, kwargs in LIBRARY_SPECS:
        registry.register_regime(name, category, fn, replace=replace, **kwargs)
    return registry


def catalog(registry: ResolverRegistry = DEFAULT_REGISTRY) -> dict:
    """What is registered, by category, with custom dimensions flagged."""
    return registry.categories()


__all__ = [
    "LIBRARY_SPECS", "register_library", "catalog",
    "make_recall_resolver", "make_solved_route_replay", "make_analogy_transfer",
    "make_single_model_regime", "make_council_regime", "make_research_regime",
]
