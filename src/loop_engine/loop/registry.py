"""Registry — add a new "select the next action?" regime with one call.

The framing calls for open-ended extensibility: deterministic rules, embeddings,
small models, hybrids, tests, research, councils, blind takes, persona-salted
takes, and "super custom or super special dimensions for our very unique ones
that don't fit into a nice hierarchical ontology."  This registry is how a new
regime is added — ``register_regime(name, category, fn, ...)`` — without editing
the loop.  A novel regime whose category is not one of the known
``RESOLVER_CATEGORIES`` is allowed (it lands as a custom dimension) and flagged
as such, so the ontology stays open rather than closed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..loop.resolvers import (NextActionResolver, NextActionResolveFn, RESOLVER_CATEGORIES,
                        DEFAULT_CATEGORY_LEVEL)


@dataclass
class ResolverRegistry:
    """A named, ordered set of next-action decision resolvers."""
    _by_name: dict = field(default_factory=dict)

    def register(self, resolver: NextActionResolver, *,
                 replace: bool = False) -> NextActionResolver:
        if resolver.name in self._by_name and not replace:
            raise ValueError(
                f"a resolver named {resolver.name!r} is already registered; "
                f"pass replace=True to override it")
        self._by_name[resolver.name] = resolver
        return resolver

    def register_regime(self, name: str, category: str, fn: NextActionResolveFn, *,
                        level: int | None = None, cost: float = 0.0,
                        model_calls: int = 0, replace: bool = False
                        ) -> NextActionResolver:
        """The one-call way to add a new next-action decision regime.  A category outside
        the known set is accepted as a custom dimension (its default level is 4,
        a single-model-ish tier, unless ``level`` is given)."""
        if not category:
            raise ValueError("a regime needs a non-empty category")
        return self.register(
            NextActionResolver(name=name, category=category, fn=fn, level=level,
                               cost=cost, model_calls=model_calls),
            replace=replace)

    def unregister(self, name: str) -> None:
        self._by_name.pop(name, None)

    def get(self, name: str) -> NextActionResolver | None:
        return self._by_name.get(name)

    def resolvers(self, *, categories=None, max_level: int | None = None
                  ) -> list[NextActionResolver]:
        """Registered resolvers, optionally filtered by category and cost tier,
        returned cheapest-first (the order the loop will try them)."""
        out = list(self._by_name.values())
        if categories is not None:
            allowed = set(categories)
            out = [r for r in out if r.category in allowed]
        if max_level is not None:
            out = [r for r in out if r.resolved_level() <= max_level]
        out.sort(key=lambda r: (r.resolved_level(), r.cost, r.name))
        return out

    def categories(self) -> dict:
        """Which categories are registered, and which are CUSTOM (not in the
        known taxonomy) — so novel regimes are visible, never hidden."""
        seen: dict[str, list[str]] = {}
        for r in self._by_name.values():
            seen.setdefault(r.category, []).append(r.name)
        return {"known": {c: seen[c] for c in seen if c in RESOLVER_CATEGORIES},
                "custom": {c: seen[c] for c in seen
                           if c not in RESOLVER_CATEGORIES},
                "total_resolvers": len(self._by_name)}


# A default shared registry plus module-level conveniences, so the common case
# is a single import and one call.
DEFAULT_REGISTRY = ResolverRegistry()


def register_regime(name: str, category: str, fn: NextActionResolveFn, **kwargs
                    ) -> NextActionResolver:
    return DEFAULT_REGISTRY.register_regime(name, category, fn, **kwargs)


def register(resolver: NextActionResolver, *, replace: bool = False
             ) -> NextActionResolver:
    return DEFAULT_REGISTRY.register(resolver, replace=replace)


def registered_resolvers(**kwargs) -> list[NextActionResolver]:
    return DEFAULT_REGISTRY.resolvers(**kwargs)
