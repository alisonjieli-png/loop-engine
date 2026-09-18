"""Offline checks for route separation between the producer and the independent verifier.

A fixture provider behind two named routes lets a producer call use one route
and the verifier the other. The checks make no live-model claim: they prove
the local contract that a declared separation is enforced at the gateway,
recorded on the report, refused at acceptance when it was required and not
achieved, and reported honestly when it was not declared.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch


def _two_route_execution(answers, *, max_model_calls):
    """The fixture provider behind two named routes, so a producer and a verifier can differ."""
    from .independent_verification_checks import (
        FixtureModelExecutionRequest, ModelExecution, fixture_model_execution)
    from .model_gateway import ModelGateway, ModelGatewayConfig
    from .model_routes import ModelRoute, RoutePolicy
    single = fixture_model_execution(FixtureModelExecutionRequest(
        answers=tuple(json.dumps(item) for item in answers), max_model_calls=max_model_calls))
    provider = next(iter(single.gateway.providers.values()))
    routes = tuple(ModelRoute(name, "fixture", "fixture-model", "local", purposes=("counted_generation",))
                   for name in ("fixture.producer", "fixture.verifier"))
    gateway = ModelGateway(providers=(provider,), routes=routes,
                           policy=RoutePolicy(allow_local_counted_generation=True))
    config = ModelGatewayConfig(route_names=tuple(route.name for route in routes),
                                allowed_localities=("local",), allow_failover=True,
                                max_route_attempts=2)
    return ModelExecution(gateway, config, max_model_calls=max_model_calls)


def run_route_separation_checks(check):
    from . import independent_verification as verification
    from .independent_verification_checks import (
        _GOOD_SOURCE, ModelInvocationRequest, _proposal, _refused, _sandbox_observation,
        _services, _subject)
    approved = {"valid": True, "criterion_refs": ["criterion:0"],
                "issues": [], "notes": "Offline oracle review fixture."}

    def executor(request, context):
        return _sandbox_observation(request, "12\n")

    with tempfile.TemporaryDirectory(prefix="loop-independent-routes-") as folder:
        services, owner = _services(Path(folder))
        services.model_session = _two_route_execution(
            ("producer answer", _proposal(), approved), max_model_calls=3).start_session()
        services.request.independent_verification_policy = (
            verification.IndependentVerificationPolicy(separate_route=True))
        services.model_session.invoke(ModelInvocationRequest("the producer's own call"), owner)
        good = _subject(services, source=_GOOD_SOURCE)
        with patch.object(verification, "execute_generated_project", executor):
            passed = verification.run_independent_verification(good, services, owner)
        separation = passed.get("route_separation") or {}
        verifier_results = services.model_session.results[1:]
        check("a_separated_verifier_confirms_on_a_route_the_producer_did_not_use",
              passed["status"] == "passed" and separation.get("achieved") is True
              and separation.get("required") is True
              and separation.get("producer_routes") == ["fixture.producer"]
              and separation.get("verifier_routes") == ["fixture.verifier"]
              and all(result.route == "fixture.verifier" for result in verifier_results)
              and passed["independence"] == verification.INDEPENDENCE_SEPARATE_ROUTE
              and services.model_session.calls_used == 3,
              json.dumps(separation))
        check("a_separated_pass_validates_and_a_report_claiming_separation_it_lacks_is_refused",
              not _refused(lambda: verification.validate_independent_verification(
                  passed, good, services, owner))
              and _refused(lambda: verification.require_route_separation(
                  {"route_separation": {**separation, "achieved": False}}))
              and not _refused(lambda: verification.require_route_separation(
                  {"route_separation": {**separation, "required": False, "achieved": False}}))
              and not _refused(lambda: verification.require_route_separation(passed)))
    with tempfile.TemporaryDirectory(prefix="loop-independent-shared-") as folder:
        services, owner = _services(Path(folder))
        services.model_session = _two_route_execution(
            ("producer answer", _proposal(), approved), max_model_calls=3).start_session()
        services.model_session.invoke(ModelInvocationRequest("the producer's own call"), owner)
        good = _subject(services, source=_GOOD_SOURCE)
        with patch.object(verification, "execute_generated_project", executor):
            shared = verification.run_independent_verification(good, services, owner)
        separation = shared.get("route_separation") or {}
        check("an_unseparated_verifier_reports_the_shared_route_honestly",
              shared["status"] == "passed" and separation.get("required") is False
              and separation.get("achieved") is False
              and separation.get("producer_routes") == ["fixture.producer"]
              and separation.get("verifier_routes") == ["fixture.producer"]
              and shared["independence"] == verification.INDEPENDENCE_SHARED_ROUTE
              and not _refused(lambda: verification.validate_independent_verification(
                  shared, good, services, owner)),
              json.dumps(separation))
    with tempfile.TemporaryDirectory(prefix="loop-independent-one-route-") as folder:
        services, owner = _services(Path(folder), ("producer answer", _proposal(), approved))
        services.request.independent_verification_policy = (
            verification.IndependentVerificationPolicy(separate_route=True))
        services.model_session.invoke(ModelInvocationRequest("the producer's only route"), owner)
        good = _subject(services, source=_GOOD_SOURCE)
        with patch.object(verification, "execute_generated_project", executor):
            unavailable = verification.run_independent_verification(good, services, owner)
        separation = unavailable.get("route_separation") or {}
        check("a_run_whose_only_route_is_the_producers_records_unavailable_not_a_quiet_reuse",
              unavailable["status"] == "unavailable"
              and "no_eligible_route" in unavailable["notes"]
              and separation.get("required") is True and separation.get("achieved") is True
              and separation.get("verifier_routes") == []
              and unavailable["independence"] == verification.INDEPENDENCE_SHARED_ROUTE
              and services.model_session.calls_used == 1
              and services.model_session.accounting_uncertain is False
              and _refused(lambda: verification.validate_independent_verification(
                  unavailable, good, services, owner)),
              unavailable["notes"][:160])
        default_policy = verification.IndependentVerificationPolicy()
        check("route_separation_is_off_unless_the_policy_declares_it",
              default_policy.separate_route is False
              and default_policy.to_dict()["separate_route"] is False
              and _refused(lambda: verification.IndependentVerificationPolicy(separate_route="yes")))
