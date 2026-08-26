"""Permission-limited services available to one Loop.

Core Architecture has three public service groups. Internal execution
mechanics remain in one separate object so they cannot be mistaken for peer
architecture systems or executable graph vertices.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class LoopRuntimeContextError(ValueError):
    """A Loop requested a service or permission its context does not grant."""


def _names(label: str, values) -> tuple[str, ...]:
    normalized = tuple(values)
    if any(not isinstance(value, str) or not value.strip()
           for value in normalized):
        raise LoopRuntimeContextError(
            f"{label} must contain non-empty strings")
    if len(normalized) != len(set(normalized)):
        raise LoopRuntimeContextError(f"{label} cannot contain duplicates")
    return tuple(sorted(normalized))


@dataclass(frozen=True)
class IntelligenceSearchRetrievalPort:
    """Typed access to intelligence search, selection, and materialization."""

    port_id: str
    adapter: Any = field(repr=False, compare=False)
    capabilities: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.port_id, str) or not self.port_id.strip():
            raise LoopRuntimeContextError(
                "an Intelligence Search and Retrieval port needs an ID")
        if self.adapter is None:
            raise LoopRuntimeContextError(
                "an Intelligence Search and Retrieval port needs an adapter")
        object.__setattr__(
            self, "capabilities", _names("capabilities", self.capabilities))

    def restricted_to(self, capabilities) -> "IntelligenceSearchRetrievalPort | None":
        selected = tuple(
            item for item in self.capabilities if item in set(capabilities))
        if not selected:
            return None
        return IntelligenceSearchRetrievalPort(
            self.port_id, self.adapter, selected)


@dataclass(frozen=True)
class WebResearchPort:
    """Typed access to approved network research and source acquisition."""

    port_id: str
    adapter: Any = field(repr=False, compare=False)
    capabilities: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.port_id, str) or not self.port_id.strip():
            raise LoopRuntimeContextError("a Web Research port needs an ID")
        if self.adapter is None:
            raise LoopRuntimeContextError(
                "a Web Research port needs an adapter")
        object.__setattr__(
            self, "capabilities", _names("capabilities", self.capabilities))

    def restricted_to(self, capabilities) -> "WebResearchPort | None":
        selected = tuple(
            item for item in self.capabilities if item in set(capabilities))
        if not selected:
            return None
        return WebResearchPort(self.port_id, self.adapter, selected)


@dataclass(frozen=True)
class CustomPluginsPort:
    """Typed access to explicitly registered custom plugin adapters."""

    port_id: str
    adapter: Any = field(repr=False, compare=False)
    capabilities: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.port_id, str) or not self.port_id.strip():
            raise LoopRuntimeContextError("a Custom Plugins port needs an ID")
        if self.adapter is None:
            raise LoopRuntimeContextError(
                "a Custom Plugins port needs an adapter")
        object.__setattr__(
            self, "capabilities", _names("capabilities", self.capabilities))

    def restricted_to(self, capabilities) -> "CustomPluginsPort | None":
        selected = tuple(
            item for item in self.capabilities if item in set(capabilities))
        if not selected:
            return None
        return CustomPluginsPort(self.port_id, self.adapter, selected)


@dataclass(frozen=True)
class InternalRuntimeBinding:
    """One internal mechanic, kept below the public architecture boundary."""

    binding_id: str
    service: Any = field(repr=False, compare=False)
    capabilities: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.binding_id, str) or not self.binding_id.strip():
            raise LoopRuntimeContextError("an internal binding needs an ID")
        if self.service is None:
            raise LoopRuntimeContextError("an internal binding needs a service")
        object.__setattr__(
            self, "capabilities", _names("capabilities", self.capabilities))

    def restricted_to(self, capabilities) -> "InternalRuntimeBinding | None":
        selected = tuple(
            item for item in self.capabilities if item in set(capabilities))
        if not selected:
            return None
        return InternalRuntimeBinding(self.binding_id, self.service, selected)


@dataclass(frozen=True)
class InternalRuntimeMechanics:
    """Execution-only services, permissions, and installed mode executors."""

    bindings: tuple[InternalRuntimeBinding, ...] = ()
    permissions: tuple[str, ...] = ()
    executor_modes: tuple[str, ...] = ("deterministic",)
    compatibility_composition: bool = False

    def __post_init__(self) -> None:
        bindings = tuple(self.bindings)
        if any(not isinstance(item, InternalRuntimeBinding)
               for item in bindings):
            raise LoopRuntimeContextError(
                "bindings must contain InternalRuntimeBinding objects")
        binding_ids = [item.binding_id for item in bindings]
        if len(binding_ids) != len(set(binding_ids)):
            raise LoopRuntimeContextError(
                "internal binding IDs cannot be duplicated")
        object.__setattr__(self, "bindings", bindings)
        object.__setattr__(
            self, "permissions", _names("permissions", self.permissions))
        modes = _names("executor_modes", self.executor_modes)
        allowed = {"deterministic", "hybrid", "non_deterministic"}
        if any(mode not in allowed for mode in modes):
            raise LoopRuntimeContextError(
                "executor_modes must use deterministic, hybrid, or "
                "non_deterministic")
        object.__setattr__(self, "executor_modes", modes)

    @property
    def capabilities(self) -> frozenset[str]:
        return frozenset(
            capability for binding in self.bindings
            for capability in binding.capabilities)


@dataclass(frozen=True)
class LoopRuntimeContext:
    """The complete, explicit service context carried by one Loop.

    The first three fields are the only public Core Architecture ports.
    Everything else belongs to the grouped internal mechanics object.
    """

    intelligence_search_retrieval: IntelligenceSearchRetrievalPort | None = None
    web_research: WebResearchPort | None = None
    custom_plugins: CustomPluginsPort | None = None
    internal: InternalRuntimeMechanics = field(
        default_factory=InternalRuntimeMechanics)

    def __post_init__(self) -> None:
        expected = (
            (self.intelligence_search_retrieval,
             IntelligenceSearchRetrievalPort,
             "intelligence_search_retrieval"),
            (self.web_research, WebResearchPort, "web_research"),
            (self.custom_plugins, CustomPluginsPort, "custom_plugins"),
        )
        for value, kind, name in expected:
            if value is not None and not isinstance(value, kind):
                raise LoopRuntimeContextError(
                    f"{name} must use its typed port object")
        if not isinstance(self.internal, InternalRuntimeMechanics):
            raise LoopRuntimeContextError(
                "internal must be an InternalRuntimeMechanics object")

    @property
    def available_capabilities(self) -> frozenset[str]:
        public = (
            self.intelligence_search_retrieval,
            self.web_research,
            self.custom_plugins,
        )
        return frozenset(self.internal.capabilities).union(*(
            frozenset(port.capabilities) if port is not None else frozenset()
            for port in public))

    def public_core(self) -> dict[str, object | None]:
        """Return exactly the three public service groups."""
        return {
            "intelligence_search_retrieval":
                self.intelligence_search_retrieval,
            "web_research": self.web_research,
            "custom_plugins": self.custom_plugins,
        }

    def require(self, *, capabilities=(), permissions=(), executor_modes=()
                ) -> None:
        """Fail before work when this context cannot satisfy a definition."""
        missing_capabilities = sorted(
            set(capabilities) - self.available_capabilities)
        missing_permissions = sorted(
            set(permissions) - set(self.internal.permissions))
        missing_executors = sorted(
            set(executor_modes) - set(self.internal.executor_modes))
        failures = []
        if missing_capabilities:
            failures.append(
                f"missing capabilities {missing_capabilities}")
        if missing_permissions:
            failures.append(f"missing permissions {missing_permissions}")
        if missing_executors:
            failures.append(f"missing mode executors {missing_executors}")
        if failures:
            raise LoopRuntimeContextError("; ".join(failures))

    def derive(self, *, capabilities=(), permissions=(), executor_modes=()
               ) -> "LoopRuntimeContext":
        """Return a least-authority context for another Loop.

        The requested sets must already be available. Derivation never adds a
        service, permission, or executor.
        """
        requested_capabilities = _names("capabilities", capabilities)
        requested_permissions = _names("permissions", permissions)
        requested_executors = _names("executor_modes", executor_modes)
        self.require(
            capabilities=requested_capabilities,
            permissions=requested_permissions,
            executor_modes=requested_executors)
        internal_bindings = tuple(
            selected for selected in (
                binding.restricted_to(requested_capabilities)
                for binding in self.internal.bindings)
            if selected is not None)
        return LoopRuntimeContext(
            intelligence_search_retrieval=(
                self.intelligence_search_retrieval.restricted_to(
                    requested_capabilities)
                if self.intelligence_search_retrieval is not None else None),
            web_research=(
                self.web_research.restricted_to(requested_capabilities)
                if self.web_research is not None else None),
            custom_plugins=(
                self.custom_plugins.restricted_to(requested_capabilities)
                if self.custom_plugins is not None else None),
            internal=InternalRuntimeMechanics(
                bindings=internal_bindings,
                permissions=requested_permissions,
                executor_modes=requested_executors or ("deterministic",),
                compatibility_composition=(
                    self.internal.compatibility_composition)),
        )

    @classmethod
    def compatibility(cls, *, capabilities=(), permissions=(),
                      executor_modes=("deterministic",)) -> "LoopRuntimeContext":
        """Narrow bridge for established constructor calls.

        New code must pass real ports and bindings through ``LoopStartRequest``.
        The compatibility marker makes remaining migration use observable.
        """
        capability_names = _names("capabilities", capabilities)
        binding = ()
        if capability_names:
            binding = (InternalRuntimeBinding(
                "established_loop_constructor", object(), capability_names),)
        return cls(internal=InternalRuntimeMechanics(
            bindings=binding,
            permissions=_names("permissions", permissions),
            executor_modes=_names("executor_modes", executor_modes),
            compatibility_composition=True))

