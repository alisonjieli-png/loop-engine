"""Typed model output capabilities and fail-closed resolution.

This module separates a provider-declared or provider-observed model limit from
an arbitrary caller limit.  Generation may start only when the selected model
and endpoint have a known maximum output size.  A missing capability stays
unknown.  It is never replaced with a convenient default.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


class UnknownModelOutputLimit(ValueError):
    """The selected provider, endpoint, and model have no known maximum."""


class ModelOutputLimitMismatch(ValueError):
    """A caller supplied a limit that is not the declared model maximum."""


@dataclass(frozen=True)
class ModelOutputCapability:
    """One source-backed maximum output declaration for one model route.

    ``maximum_output_tokens`` is the declared maximum. The string
    ``"unknown"`` declares an explicit unknown state: the server publishes
    no output maximum (many self-hosted gateways do not), so nothing is
    invented and the caller must supply an explicit working ceiling per
    invocation. The declaration is still source-backed: ``source`` names
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
        requested: "int | None", capability: ModelOutputCapability) -> int:
    """Return the exact declared maximum or an explicit caller ceiling.

    When the capability declares the maximum ``"unknown"`` (the server
    publishes no limit and no source-backed record exists), nothing is
    invented: the caller must supply an explicit working ceiling per
    invocation, exactly like a per-conversation output setting. A caller
    ceiling below any future declared maximum is still honest — it is an
    owner choice, not a fabricated model limit.
    """
    declared = capability.declared_maximum
    if declared is None:
        if requested is None:
            raise UnknownModelOutputLimit(
                "explicit working ceiling required: this model's maximum "
                "output is declared unknown (the server publishes no limit "
                "and no source-backed record exists); pass an explicit "
                "owner-chosen output ceiling")
        if (not isinstance(requested, int) or isinstance(requested, bool)
                or requested < 1):
            raise UnknownModelOutputLimit(
                "an unknown-maximum model needs a positive integer working "
                "ceiling")
        return int(requested)
    if requested is not None and int(requested) != declared:
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

    passed = sum(1 for test in results if test["passed"])
    return {"record_type": "model_capabilities_contract_test/v1",
            "scope": "offline_contract_only",
            "provider_integration_proven": False,
            "tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
