"""Resolving the exact provider output maximum bound to one harness request.

Split from ``external_harness`` at the module size cap. Capacity, the selected
allowance, and the total run authority are three different things, and this
module owns only the first: which provider maximum applies to this exact
provider, model, and route, and whether the request may use it.

A request that arrives with a limit is validated against its own identities. A
request without one is resolved through an installed resolver, and a resolver
that has nothing for this model is an explicit failure rather than an invented
smaller default.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Protocol, TYPE_CHECKING

from .harness_model_authority import (
    HarnessError, HarnessModelIdentity, ModelOutputLimit, _validate_allocation_capacity,
)

if TYPE_CHECKING:
    from .external_harness import HarnessRunRequest, HarnessServices


class ModelOutputResolver(Protocol):
    def resolve(self, request: HarnessRunRequest) -> "ModelOutputLimit | None": ...


@dataclass(frozen=True)
class StaticModelOutputResolver:
    """Resolve exact model maxima from reviewed capability records."""

    limits: tuple[ModelOutputLimit, ...]

    def resolve(self, request: HarnessRunRequest) -> "ModelOutputLimit | None":
        for limit in self.limits:
            provider_matches = limit.provider_id == request.provider_id
            model_matches = limit.model_id == request.model_id
            route_matches = (not limit.route_id
                             or limit.route_id in request.model_routes)
            if provider_matches and model_matches and route_matches:
                return limit
        return None


def _validate_output_limit_binding(
        request: HarnessRunRequest, limit: ModelOutputLimit) -> None:
    _validate_output_limit_binding_fields(
        request.provider_id, request.model_id, limit)
    if limit.route_id and limit.route_id not in request.model_routes:
        raise HarnessError(
            "model output maximum route does not match the request")
    if (limit.route_id and request.authorized_model_identities
            and HarnessModelIdentity(limit.provider_id, limit.model_id, limit.route_id)
            not in request.authorized_model_identities):
        raise HarnessError("model output capacity route is outside the authorized identities")
    if request.budget.output_allocation is not None:
        _validate_allocation_capacity(request.budget.output_allocation, limit)


def _validate_output_limit_binding_fields(
        provider_id: str, model_id: str, limit: ModelOutputLimit) -> None:
    if limit.provider_id != provider_id:
        raise HarnessError(
            "model output maximum provider does not match the request")
    if limit.model_id != model_id:
        raise HarnessError(
            "model output maximum model does not match the request")


def resolve_harness_output_limit(
        request: HarnessRunRequest,
        services: "HarnessServices | None" = None) -> HarnessRunRequest:
    """Resolve the exact provider maximum before creating the run identity."""
    if request.budget.output_limit is not None:
        _validate_output_limit_binding(request, request.budget.output_limit)
        return request
    from .external_harness import HarnessServices
    active = services or HarnessServices()
    resolver = active.model_output_resolver
    if resolver is None or not callable(getattr(resolver, "resolve", None)):
        raise HarnessError(
            "external harness needs a typed model output capability resolver")
    limit = resolver.resolve(request)
    if limit is None:
        raise HarnessError(
            "no exact provider output maximum matches this model and route")
    _validate_output_limit_binding(request, limit)
    return replace(
        request, budget=replace(request.budget, output_limit=limit))


def self_test() -> dict:
    """The binding refuses a limit that names another provider, model, or route."""
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    from .external_harness import HarnessRunRequest, HarnessServices
    from ..loop.loop_contract import LoopContract
    from .harness_model_authority import HarnessBudget

    limit = ModelOutputLimit(64, "custom_endpoint_declared", "offline fixture contract",
                             provider_id="fixture", model_id="fixture-model",
                             route_id="fixture.route")
    request = HarnessRunRequest(
        "limit-binding", "host_gateway", "answer",
        LoopContract("binding", "model_led", ("prompt/v1",), ("answer/v1",), ("pure",)),
        HarnessBudget(1), provider_id="fixture", model_id="fixture-model",
        model_routes=("fixture.route",), authorize_model_calls=True)

    def refuses(action):
        try:
            action()
        except HarnessError:
            return True
        except Exception:  # noqa: BLE001 - a crash is not a typed refusal
            return False
        return False

    resolved = resolve_harness_output_limit(
        request, HarnessServices(model_output_resolver=StaticModelOutputResolver((limit,))))
    check("an_installed_resolver_binds_the_exact_maximum_for_this_provider_and_route",
          resolved.budget.output_limit is limit
          and StaticModelOutputResolver((limit,)).resolve(
              replace(request, provider_id="other", model_id="fixture-model")) is None,
          str(resolved.budget.max_output_tokens))
    check("a_missing_resolver_and_a_limit_for_another_identity_are_refused_rather_than_guessed",
          refuses(lambda: resolve_harness_output_limit(request))
          and refuses(lambda: resolve_harness_output_limit(
              request, HarnessServices(model_output_resolver=StaticModelOutputResolver(()))))
          and refuses(lambda: _validate_output_limit_binding(
              request, replace(limit, provider_id="other")))
          and refuses(lambda: _validate_output_limit_binding(
              request, replace(limit, model_id="other")))
          and refuses(lambda: _validate_output_limit_binding(
              request, replace(limit, route_id="other.route"))))
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "harness_output_limit_binding_test/v1", "tests": tests,
            "passed": passed, "total": len(tests), "all_passed": passed == len(tests)}
