"""Named checks for the external harness adapter contract and the envelope clock.

Owns the checks of engine plan package X2. Registration refuses an adapter
whose contract version is missing or unknown, whose engine kind is outside the
step executor slot, or which serves none of the slot's edges. One engine
identifier names one implementation. The envelope's own clock, not the
engine's report, sets the attempt time. Each control removes one guard inside
the check and requires the named check to fail, so a deleted guard is noticed.
Uses local fixture adapters only: no package, process, provider or model call.
"""
from __future__ import annotations

import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from ..loop.loop_contract import LoopContract
from .external_harness import (
    HarnessAdapterInfo, HarnessBudget, HarnessError, HarnessModelCall, HarnessRegistry,
    HarnessRunRequest, HarnessRunResult, HarnessServices, ModelOutputLimit, run_external_harness,
)
from .harness_execution_contracts import HarnessExecutionCapabilities

#: The declaration every well-formed fixture carries unless a check omits a part.
_VERSION = "external_harness_adapter/v2"
_KIND = "agent_framework_kit"
_RESPONSE_EDGE = "harness_request_identity/v3"
_STEP_EDGE = "step_run_request/v1"
#: The closed engine kinds of the step executor slot, as the engine design
#: (section 13.5) lists them. A wider list in code must fail this check.
_SLOT_KINDS = (
    "agent_protocol_harness", "native_protocol_harness", "text_relay_harness",
    "custom_loop_harness", "remote_agent", "agent_framework_kit", "direct_model_step",
    "in_process_runner", "typed_decision_step", "structural")
_OMITTED = object()


class _Fixture:
    """A local adapter whose declaration each check sets. It starts no process."""

    def __init__(self, harness_id="contract_fixture", *, contract=_VERSION, kind=_KIND,
                 edges=(_RESPONSE_EDGE,), version="1.0.0", reported=None, sleep=0.0,
                 features=()):
        self.harness_id, self.version = harness_id, version
        self.contract, self.kind, self.edges = contract, kind, edges
        self.reported, self.sleep, self.calls = reported, sleep, 0
        self.features = features

    def info(self):
        declared = {name: value for name, value in (
            ("adapter_contract_version", self.contract), ("engine_kind", self.kind),
            ("supported_edge_contracts", self.edges)) if value is not _OMITTED}
        return HarnessAdapterInfo(
            self.harness_id, self.version, "not-imported", available=True,
            execution_capabilities=HarnessExecutionCapabilities(
                supported_features=self.features), **declared)

    def run(self, request, services):
        self.calls += 1
        time.sleep(self.sleep)
        return HarnessRunResult(
            request.request_id, request.harness_id, "completed", output={"answer": 1},
            model_calls=(HarnessModelCall(request.provider_id, request.model_id, True,
                                          input_tokens=1, output_tokens=1),),
            adapter_version=self.version, elapsed_seconds=self.reported)


class _SecondImplementation(_Fixture):
    """The same declaration as _Fixture from a different implementation."""


class _StepEngine(_Fixture):
    """Serves only the step edge: it has run_step and no run operation."""

    run = None

    def run_step(self, request, services):
        raise AssertionError("a registration check never runs a step")


def _outcome(action):
    """'accepted', the refusal codes, or the name of any other error raised."""
    from .external_harness_contract import HarnessAdapterRefused
    try:
        action()
    except HarnessAdapterRefused as refusal:
        return refusal.refusals
    except (HarnessError, ValueError, TypeError) as error:
        return type(error).__name__
    return "accepted"


def _register(*adapters, registry=None, replace=False):
    target = registry if registry is not None else HarnessRegistry()
    return _outcome(lambda: [target.register(item, replace=replace) for item in adapters])


def _contract_version_is_required():
    return (_register(_Fixture(contract=_OMITTED)) == ("adapter_contract_version_missing",)
            and _register(_Fixture(contract="external_harness_adapter/v1"))
            == ("adapter_contract_version_unsupported",)
            and _register(_Fixture(contract="external_harness_adapter/v3"))
            == ("adapter_contract_version_unsupported",)
            and _register(_Fixture()) == "accepted")


def _served_edge_is_required():
    return (_register(_Fixture(edges=("harness_request_identity/v2",)))
            == ("no_supported_edge_contract",)
            and _register(_Fixture(edges=("step_run_request/v2",))) == ("no_supported_edge_contract",)
            and _register(_Fixture(edges=_OMITTED)) == ("no_supported_edge_contract",)
            and _register(_Fixture(edges=(_STEP_EDGE,))) == ("edge_operation_missing:run_step",)
            # An operation that exists but cannot be called is missing too.
            and _register(_StepEngine(edges=(_RESPONSE_EDGE,))) == ("edge_operation_missing:run",)
            and _register(_StepEngine(edges=(_STEP_EDGE,))) == "accepted"
            and _register(_Fixture(edges=(_RESPONSE_EDGE, "harness_request_identity/v4")))
            == "accepted")


def _kind_is_inside_the_slot():
    from .external_harness_contract import STEP_EXECUTOR_ENGINE_KINDS
    every_kind = HarnessRegistry()
    return (_register(_Fixture(kind="server_database")) == ("engine_kind_not_in_slot",)
            and _register(_Fixture(kind=_OMITTED)) == ("engine_kind_missing",)
            and tuple(STEP_EXECUTOR_ENGINE_KINDS) == _SLOT_KINDS
            and all(_register(_Fixture("kind_" + kind, kind=kind), registry=every_kind)
                    == "accepted" for kind in _SLOT_KINDS))


def _one_identifier_one_implementation():
    from .harness_configuration import UnavailableHarnessAdapter
    from .opencode_harness_adapter import OpenCodeProcessAdapter
    parked = OpenCodeProcessAdapter()
    recipe = UnavailableHarnessAdapter(
        "opencode", "1.17.9", "fixture: the opencode recipe engine is not installed here")
    held = HarnessRegistry()
    both = _register(parked, recipe, registry=held)
    registry = HarnessRegistry((_Fixture("replaced"),))
    first = registry.registration_digest("replaced")
    same_again = _register(_Fixture("replaced"), registry=registry, replace=True)
    unchanged = registry.registration_digest("replaced") == first
    without_replace = _register(_Fixture("replaced", version="1.0.1"), registry=registry)
    new_version = _register(_Fixture("replaced", version="1.0.1"), registry=registry, replace=True)
    second = registry.registration_digest("replaced")
    new_code = _register(_SecondImplementation("replaced", version="1.0.1"),
                         registry=registry, replace=True)
    third = registry.registration_digest("replaced")
    # Only the declared capabilities change: still a new registration digest.
    new_capabilities = _register(_SecondImplementation(
        "replaced", version="1.0.1", features=("model_routes",)), registry=registry, replace=True)
    fourth = registry.registration_digest("replaced")
    # The new identifier is a harness name, so no model call may give it as its provider.
    harness_as_provider = _outcome(
        lambda: HarnessModelCall("opencode.raw_host", "fixture-model", True))
    return (parked.info().harness_id == "opencode.raw_host" and both == "accepted"
            and harness_as_provider == "HarnessError"
            and {item.harness_id for item in held.inventory()} == {"opencode", "opencode.raw_host"}
            and same_again == ("replacement_registration_digest_unchanged",) and unchanged
            and without_replace == ("engine_identifier_already_registered",)
            and new_version == "accepted" and new_code == "accepted"
            and new_capabilities == "accepted" and len({first, second, third, fourth}) == 4)


def _request(harness_id, **budget):
    limit = ModelOutputLimit(64, "custom_endpoint_declared", "offline contract fixture",
                             provider_id="fixture_provider", model_id="fixture-model")
    return HarnessRunRequest(
        "contract-" + harness_id, harness_id, "answer one fixture question",
        LoopContract("contract fixture", "model_led", input_roles=("question/v1",),
                     output_roles=("answer/v1",), effects=("pure",)),
        HarnessBudget(max_model_calls=1, output_limit=limit, **budget),
        provider_id="fixture_provider", model_id="fixture-model", authorize_model_calls=True)


def _timed(adapter, **budget):
    from ..loop.recursive_loop import LoopLedger
    from .context_artifacts import ContextArtifactManager, ContextArtifactStore, ContextArtifactStoreSpec
    ledger = LoopLedger()
    with tempfile.TemporaryDirectory(prefix="harness-contract-clock-") as root:
        services = HarnessServices(artifact_store=ContextArtifactManager(
            ContextArtifactStore(ContextArtifactStoreSpec(root))))
        result = run_external_harness(adapter, _request(adapter.harness_id, **budget),
                                      services=services, ledger=ledger)
    events = [row for row in ledger.events if isinstance(row.get("external_harness_result"), dict)]
    return result, events[0] if len(events) == 1 else {}


def _envelope_clock_rules():
    # The known-wrong case: the engine says 0.001 seconds while the envelope
    # watched it work for at least 0.05 seconds.
    fast, fast_event = _timed(_Fixture("clock_fixture", reported=0.001, sleep=0.05))
    slow, slow_event = _timed(_Fixture("clock_fixture", reported=5000.0))
    bounded, _ = _timed(_Fixture("clock_fixture", reported=0.001, sleep=0.05), max_seconds=0.02)
    return (fast.elapsed_seconds >= 0.05 and fast_event.get("engine_reported_seconds") == 0.001
            and fast_event["external_harness_result"]["elapsed_seconds"] == fast.elapsed_seconds
            and slow.elapsed_seconds < 60 and slow_event.get("engine_reported_seconds") == 5000.0
            and bounded.status == "budget_exhausted"
            and bounded.error_code == "time_budget_exhausted")


def _envelope_refuses_outside_the_contract():
    from ..loop.recursive_loop import LoopLedger
    undeclared, step_only = _Fixture("clock_fixture", contract=_OMITTED), _StepEngine(
        "clock_fixture", edges=(_STEP_EDGE,))
    ledgers = (LoopLedger(), LoopLedger())
    first = _outcome(lambda: run_external_harness(
        undeclared, _request("clock_fixture"), ledger=ledgers[0]))
    second = _outcome(lambda: run_external_harness(
        step_only, _request("clock_fixture"), ledger=ledgers[1]))
    return (first == ("adapter_contract_version_missing",) and undeclared.calls == 0
            and second == ("edge_not_declared:" + _RESPONSE_EDGE,)
            and not ledgers[0].events and not ledgers[1].events)


def _production_adapters_declare_the_contract():
    import sys
    from .external_harness_adapters import builtin_harness_adapters
    from .harness_configuration import UnavailableHarnessAdapter
    from .harness_process import HarnessProcessSpec
    from .harness_semantic import GatewayHarnessProcessAdapter
    from .opencode_harness_adapter import OpenCodeProcessAdapter
    with tempfile.TemporaryDirectory(prefix="harness-contract-process-") as root:
        software = Path(root) / "software"
        software.mkdir()
        process = GatewayHarnessProcessAdapter(HarnessProcessSpec(
            "process_fixture", "1.0.0", (sys.executable,), (str(software),), "aider"))
        adapters = (*builtin_harness_adapters(), process,
                    UnavailableHarnessAdapter("unavailable_fixture", "1.0.0", "fixture reason"),
                    OpenCodeProcessAdapter())
        expected = {**{item.harness_id: "agent_framework_kit" for item in adapters[:4]},
                    "process_fixture": "text_relay_harness",
                    "unavailable_fixture": "text_relay_harness",
                    "opencode.raw_host": "in_process_runner"}
        infos = [item.info() for item in adapters]
        registered = _register(*adapters)
    return (registered == "accepted" and len(infos) == len(expected)
            and all(info.adapter_contract_version == _VERSION
                    and info.supported_edge_contracts == (_RESPONSE_EDGE,)
                    and expected.get(info.harness_id) == info.engine_kind for info in infos))


def _binding_needs_the_response_edge():
    from .harness_semantic import HarnessSemanticBinding
    with tempfile.TemporaryDirectory(prefix="harness-contract-binding-") as root:
        work = str(Path(root).resolve() / "work")
        step_only = HarnessRegistry((_StepEngine("step_only", edges=(_STEP_EDGE,)),))
        both = HarnessRegistry((_Fixture("response_engine"),))
        refused = _outcome(lambda: HarnessSemanticBinding("step_only", step_only, work))
        bound = _outcome(lambda: HarnessSemanticBinding("response_engine", both, work))
    return refused == "ValueError" and bound == "accepted"


def _declarations_are_shaped():
    def built(**declared):
        return _outcome(lambda: HarnessAdapterInfo(
            "shape_fixture", "1.0.0", "not-imported", **{
                "adapter_contract_version": _VERSION, "engine_kind": _KIND,
                "supported_edge_contracts": (_RESPONSE_EDGE,), **declared}))
    edges = [_RESPONSE_EDGE]
    info = HarnessAdapterInfo("shape_fixture", "1.0.0", "not-imported",
                              adapter_contract_version=_VERSION, engine_kind=_KIND,
                              supported_edge_contracts=edges)
    edges.append("step_run_request/v1")
    return (all(built(**declared) == "HarnessError" for declared in (
                {"adapter_contract_version": "external_harness_adapter"},
                {"adapter_contract_version": "External Harness/v2"},
                {"adapter_contract_version": 2},
                {"engine_kind": "Text Relay"},
                {"supported_edge_contracts": _RESPONSE_EDGE},
                {"supported_edge_contracts": (_RESPONSE_EDGE, _RESPONSE_EDGE)},
                {"supported_edge_contracts": ("harness_request_identity",)}))
            and info.supported_edge_contracts == (_RESPONSE_EDGE,))


def run_checks() -> dict:
    """Run every named check and control; one raising check fails only itself."""
    tests = []

    def check(name, rule, detail=""):
        try:
            passed = bool(rule())
        except Exception as error:  # a check that raises is a failed check, never a crash
            passed, detail = False, f"{type(error).__name__}: {str(error)[:200]}"
        tests.append({"test": name, "passed": passed, "detail": detail})

    check("registration_refuses_an_unknown_or_missing_adapter_contract_version",
          _contract_version_is_required)

    def without_version_guard():
        from . import external_harness_contract
        with patch.object(external_harness_contract, "contract_version_refusal", lambda info: ""):
            return not _contract_version_is_required()
    check("removed_contract_version_refusal_is_detected", without_version_guard)
    check("registration_refuses_an_adapter_that_serves_no_supported_edge",
          _served_edge_is_required)
    check("an_adapter_cannot_declare_a_kind_outside_its_slot", _kind_is_inside_the_slot)
    check("one_engine_identifier_names_one_implementation", _one_identifier_one_implementation)
    check("engine_reported_time_never_replaces_the_envelope_clock", _envelope_clock_rules,
          "an engine that reports 0.001 seconds is measured by the envelope")

    def adapter_reported_time_wins(started, engine_reported):
        measured = round(time.monotonic() - started, 6)
        return (engine_reported if engine_reported is not None else measured), engine_reported

    def without_clock_rule():
        from . import external_harness
        with patch.object(external_harness, "measured_and_reported_seconds",
                          adapter_reported_time_wins):
            return not _envelope_clock_rules()
    check("removed_envelope_clock_rule_is_detected", without_clock_rule)
    check("the_envelope_refuses_an_adapter_outside_the_contract_before_any_loop",
          _envelope_refuses_outside_the_contract)
    check("every_production_adapter_declares_the_adapter_contract",
          _production_adapters_declare_the_contract)
    check("a_semantic_binding_refuses_an_engine_that_does_not_serve_the_model_response_edge",
          _binding_needs_the_response_edge)
    check("adapter_contract_declarations_are_shaped_before_registration",
          _declarations_are_shaped)
    passed = sum(item["passed"] for item in tests)
    return {"module": "core.external_harness_contract_checks", "tests": tests,
            "passed": passed, "total": len(tests), "all_passed": passed == len(tests)}
