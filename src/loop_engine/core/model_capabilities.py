"""Typed model output capabilities and fail-closed resolution.

This module separates a provider-declared or provider-observed model limit from
an arbitrary caller limit.  Generation may start only when the selected model
and endpoint have a known maximum output size.  A missing capability stays
unknown.  It is never replaced with a convenient default.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping


class UnknownModelOutputLimit(ValueError):
    """The selected provider, endpoint, and model have no known maximum."""


class ModelOutputLimitMismatch(ValueError):
    """A request differs from the declared maximum or explicit allocation."""


@dataclass(frozen=True)
class ModelOutputCapability:
    """One source-backed maximum output declaration for one model route.

    ``maximum_output_tokens`` is the declared maximum. The string
    ``"unknown"`` declares an explicit unknown state: the server publishes
    no output maximum (many self-hosted gateways do not), so execution waits
    for resolved capacity rather than inventing one. The declaration is still
    source-backed: ``source`` names
    where the unknown was established (for example a model catalog that
    publishes no limit field).
    """

    maximum_output_tokens: "int | str"
    source: str
    endpoint: str = ""
    observed_at: str = ""

    def __post_init__(self) -> None:
        if isinstance(self.maximum_output_tokens, str):
            if self.maximum_output_tokens != "unknown":
                raise ValueError(
                    "maximum_output_tokens must be a positive integer or the "
                    "exact string 'unknown'")
        elif (not isinstance(self.maximum_output_tokens, int)
                or isinstance(self.maximum_output_tokens, bool)
                or self.maximum_output_tokens < 1):
            raise ValueError("maximum_output_tokens must be positive")
        source = self.source.strip()
        if not source:
            raise ValueError("a model output capability needs a source")
        if len(source) > 300 or "\n" in source or "\r" in source:
            raise ValueError("capability source must be one short line")
        lowered = source.lower()
        if any(marker in lowered for marker in (
                "authorization:", "bearer ", "api_key=", "apikey=",
                "password=", "secret=")):
            raise ValueError("capability source must not contain credentials")
        if self.endpoint and not self.endpoint.startswith(("http://", "https://")):
            raise ValueError("capability endpoint must be an HTTP or HTTPS URL")

    @property
    def declared_maximum(self) -> "int | None":
        """The integer maximum, or None when explicitly unknown."""
        if isinstance(self.maximum_output_tokens, str):
            return None
        return int(self.maximum_output_tokens)

    @property
    def maximum_is_unknown(self) -> bool:
        return isinstance(self.maximum_output_tokens, str)

    def summary(self) -> dict:
        return {
            "maximum_output_tokens": self.maximum_output_tokens,
            "source": self.source,
            "endpoint": self.endpoint,
            "observed_at": self.observed_at,
        }


@dataclass(frozen=True)
class ModelOutputAllocation:
    """An explicit Loop decision selecting output within a known capacity.

    This passive record grants no model or spending authority. The gateway
    must bind its decision and exact provider, model, route and capability to
    the active request. A reason is a short public decision summary, not a
    private reasoning trace. There is no implicit allocation or small default.
    """

    capability: ModelOutputCapability
    provider_id: str
    model_id: str
    route_name: str
    requested_tokens: int
    decision_ref: str
    reason: str

    def __post_init__(self) -> None:
        if type(self.capability) is not ModelOutputCapability:
            raise ValueError("allocation requires an exact model output capability")
        if any(type(getattr(self.capability, name)) is not str
               for name in ("source", "endpoint", "observed_at")):
            raise ValueError("allocation capability metadata must be plain text")
        capability = replace(self.capability)
        maximum = capability.declared_maximum
        if maximum is None:
            raise UnknownModelOutputLimit(
                "a reasoned output allocation requires known provider capacity")
        if (type(capability.maximum_output_tokens) is not int
                or type(self.requested_tokens) is not int
                or not 1 <= self.requested_tokens <= maximum):
            raise ValueError("allocation must be a positive integer within provider capacity")
        for name in ("provider_id", "model_id", "route_name", "decision_ref", "reason"):
            value = getattr(self, name)
            maximum_length = 512 if name in ("model_id", "reason") else 256
            if (type(value) is not str or not value.strip()
                    or len(value) > maximum_length
                    or any(ord(character) < 32 or ord(character) == 127
                           for character in value)):
                raise ValueError("allocation needs bounded plain-text identity and decision provenance")
            if name != "reason" and any(character.isspace() for character in value):
                raise ValueError("allocation identities cannot contain whitespace")
            if any(marker in value.lower() for marker in (
                    "authorization:", "bearer ", "api_key=", "apikey=",
                    "password=", "secret=")):
                raise ValueError("allocation provenance must not contain credentials")
            try:
                value.encode("utf-8")
            except UnicodeError:
                raise ValueError("allocation provenance must be UTF-8 text") from None
        object.__setattr__(self, "capability", capability)

    @property
    def declared_maximum(self) -> int:
        return self.capability.declared_maximum

    @property
    def maximum_output_tokens(self) -> int:
        """Provider capacity, not the allocation selected by the Loop."""
        return self.capability.maximum_output_tokens

    @property
    def source(self) -> str:
        return self.capability.source

    @property
    def maximum_is_unknown(self) -> bool:
        return self.capability.maximum_is_unknown

    def summary(self) -> dict:
        return {
            "record_type": "model_output_allocation/v1",
            **self.capability.summary(),
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "route_name": self.route_name,
            "requested_tokens": self.requested_tokens,
            "decision_ref": self.decision_ref,
            "reason": self.reason,
        }


def resolve_output_capability(
        provider: str, model: str, endpoint: str,
        capabilities: Mapping[str, ModelOutputCapability]
        ) -> ModelOutputCapability:
    """Resolve the most specific capability or fail closed.

    Exact model identifiers win.  This lets an endpoint-specific observation
    override a family entry.  Family entries support provider suffixes such as
    ``:cloud`` only after exact resolution has failed.
    """
    exact = capabilities.get(model)
    if exact is not None and (not exact.endpoint or exact.endpoint == endpoint):
        return exact

    base = model.split("/")[-1].split(":")[0]
    candidates = []
    for name, capability in capabilities.items():
        if capability.endpoint and capability.endpoint != endpoint:
            continue
        # A suffixed identifier is an exact observation, not a family rule.
        # It must never leak onto a different version that shares the base.
        declared_leaf = name.split("/")[-1]
        if ":" in declared_leaf and name != model:
            continue
        declared_base = name.split("/")[-1].split(":")[0]
        if base == declared_base:
            candidates.append((len(name), capability))
    if candidates:
        return sorted(candidates, key=lambda item: item[0], reverse=True)[0][1]
    raise UnknownModelOutputLimit(
        "unknown_model_output_limit: no provider-declared or observed maximum "
        f"for provider={provider!r}, model={model!r}, endpoint={endpoint!r}")


def require_declared_maximum(
        requested: "int | None",
        capability: ModelOutputCapability | ModelOutputAllocation) -> int:
    """Return full capacity, or the selection in a typed Loop allocation.

    A ModelOutputAllocation is a distinct, explicit decision within a known
    capacity; a bare smaller integer does not create such a decision.

    Unknown capacity remains unavailable. A raw scalar cannot establish the
    provider's capacity or substitute for a typed reasoning/user allocation.
    """
    if type(capability) is ModelOutputAllocation:
        allocation = replace(capability)
        if (requested is not None and (type(requested) is not int
                                      or requested != allocation.requested_tokens)):
            raise ModelOutputLimitMismatch(
                "requested output differs from the explicit Loop allocation")
        return allocation.requested_tokens
    declared = capability.declared_maximum
    if declared is None:
        raise UnknownModelOutputLimit(
            "unknown_model_output_limit: source-backed output capacity is required")
    if requested is not None and (type(requested) is not int or requested != declared):
        raise ModelOutputLimitMismatch(
            f"requested output limit {requested} is not the declared model "
            f"maximum {declared}; Loop Engine does not invent or reduce model "
            "output ceilings")
    return declared


def self_test() -> dict:
    """Offline contract and refusal checks.  No provider is contacted."""
    results = []

    def check(name, ok, detail=""):
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    endpoint = "https://provider.example/v1/chat/completions"
    family = ModelOutputCapability(
        128000, "provider catalog", endpoint=endpoint)
    exact = ModelOutputCapability(
        65536, "provider HTTP 400 boundary", endpoint=endpoint,
        observed_at="2026-08-25")
    table = {"model-family": family, "model-family:0731": exact}
    resolved = resolve_output_capability(
        "provider", "model-family:0731", endpoint, table)
    check("an_exact_endpoint_observation_overrides_a_family_value",
          resolved.maximum_output_tokens == 65536)
    other_version = resolve_output_capability(
        "provider", "model-family:0815", endpoint, table)
    check("an_exact_observation_does_not_leak_to_another_version",
          other_version.maximum_output_tokens == 128000)

    unknown = False
    try:
        resolve_output_capability("provider", "unknown", endpoint, table)
    except UnknownModelOutputLimit:
        unknown = True
    check("an_unknown_maximum_refuses_instead_of_guessing", unknown)

    mismatch = False
    try:
        require_declared_maximum(512, exact)
    except ModelOutputLimitMismatch:
        mismatch = True
    check("a_lower_caller_cap_does_not_replace_the_declared_maximum", mismatch)
    check("an_unspecified_request_uses_the_declared_maximum",
          require_declared_maximum(None, exact) == 65536)

    def refused(operation):
        try:
            operation()
        except ValueError:
            return True
        return False

    allocation = ModelOutputAllocation(
        exact, "provider", "model-family:0731", "route.exact", 4096,
        "loop:output-decision", "The typed response needs this bounded output allocation.")
    check("explicit_loop_allocation_selects_within_known_capacity",
          require_declared_maximum(None, allocation) == 4096
          and require_declared_maximum(4096, allocation) == 4096)
    check("allocation_summary_keeps_capacity_and_selection_distinct",
          allocation.summary()["maximum_output_tokens"] == 65536
          and allocation.summary()["requested_tokens"] == 4096
          and allocation.declared_maximum == allocation.maximum_output_tokens == 65536
          and allocation.source == exact.source and not allocation.maximum_is_unknown)
    check("allocation_does_not_change_default_or_authorize_a_bare_lower_integer",
          require_declared_maximum(None, exact) == 65536
          and refused(lambda: require_declared_maximum(4096, exact)))
    check("allocation_requires_all_decision_fields_without_defaults",
          all(refused(lambda name=name: replace(allocation, **{name: ""}))
              for name in ("provider_id", "model_id", "route_name", "decision_ref", "reason")))
    check("allocation_rejects_nonpositive_out_of_capacity_and_noninteger_tokens",
          all(refused(lambda value=value: replace(allocation, requested_tokens=value))
              for value in (0, -1, 65537, True, False, 4096.0, float("nan"), float("inf"))))
    check("allocation_cannot_guess_an_unknown_capacity",
          refused(lambda: replace(allocation, capability=ModelOutputCapability(
              "unknown", "provider publishes no maximum"))))
    unknown_capability = ModelOutputCapability(
        "unknown", "provider publishes no maximum")
    check("unknown_capacity_cannot_be_replaced_by_an_arbitrary_owner_ceiling",
          refused(lambda: require_declared_maximum(2048, unknown_capability))
          and refused(lambda: require_declared_maximum(None, unknown_capability)))
    check("allocation_cannot_use_an_untyped_capacity_record",
          refused(lambda: replace(allocation, capability={"maximum_output_tokens": 65536})))
    check("wire_request_must_equal_the_explicit_allocation",
          all(refused(lambda value=value: require_declared_maximum(value, allocation))
              for value in (1, 4095, 4097, 65536, True, 4096.0, float("nan"))))
    check("full_capacity_remains_an_available_explicit_allocation",
          require_declared_maximum(None, replace(allocation, requested_tokens=65536)) == 65536)
    check("positive_structural_minimum_is_not_an_implicit_default",
          require_declared_maximum(None, replace(allocation, requested_tokens=1)) == 1
          and require_declared_maximum(None, exact) == 65536)
    changed_source = replace(exact, source="different provider observation")
    check("capability_source_and_capacity_remain_part_of_allocation_identity",
          allocation != replace(allocation, capability=changed_source)
          and refused(lambda: replace(allocation, capability=replace(
              exact, maximum_output_tokens=2048))))
    copied = allocation.summary()
    copied["requested_tokens"] = 1
    copied["source"] = "changed"
    check("allocation_copies_source_record_and_summary_cannot_mutate_it",
          allocation.capability is not exact and allocation.capability == exact
          and allocation.requested_tokens == 4096 and allocation.source == exact.source)
    check("allocation_provenance_refuses_controls_nontext_and_credential_shapes",
          all(refused(lambda name=name, value=value: replace(allocation, **{name: value}))
              for name, value in (("decision_ref", "two words"), ("reason", "a\nb"),
                                  ("reason", "api_key=PRIVATE"), ("provider_id", 1),
                                  ("reason", "\ud800"))))
    from dataclasses import FrozenInstanceError
    try:
        allocation.requested_tokens = 1
    except FrozenInstanceError:
        check("allocation_record_is_frozen", True)
    else:
        check("allocation_record_is_frozen", False)

    passed = sum(1 for test in results if test["passed"])
    return {"record_type": "model_capabilities_contract_test/v1",
            "scope": "offline_contract_only",
            "provider_integration_proven": False,
            "tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
