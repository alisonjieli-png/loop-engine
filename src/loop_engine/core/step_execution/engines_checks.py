"""Offline checks for the step executor slot: its engines, the envelope and the custom Loop engine.

Each check names its known-wrong case and passes only when that case is
refused; each removed-guard control deletes one guard and passes only when
its check would then fail. The base checks start no process: the in-process
Loop engine and in-process fixture engines serve the edge. sandbox_checks()
starts real sandboxed processes (the fixture harness, the custom Loop harness
process and, where installed at its pinned version, Pi) and is kept out of the
base self-test, like the harness process qualification; the repository tool
tools/register_step_harness.py and its tests run it.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import tempfile
from unittest.mock import patch

from . import engines as step_engines
from . import envelope as step_envelope
from ..configuration_capabilities import digest
from ..engines.host_records import EngineInstallation, EngineSlotConfiguration
from ..engines.records import EngineQualification, EngineRecordError, EvidenceReference, QualificationScope
from ..engines.selection_records import EngineSelectionPolicy
from ..configuration_preferences import MetaPreferencePolicy
from ..engines.slots import load_engine_slot_catalog
from ..external_harness import HarnessAdapterInfo
from ..external_harness_contract import ADAPTER_CONTRACT_VERSION, STEP_EDGE
from ..harness_execution_contracts import HarnessExecutionCapabilities
from .envelope import StepExecutionHost, execute_step
from .harness_manifest_checks import step_request
from .launch_checks import launch_checks
from .loop_runtime import LoopRuntimeStepEngine, run_step_in_loop
from .procedures import LIVE_PROCEDURES, PARKED_PROCEDURES, ProcedureRefused, procedure_for
from .qualification import qualify_engine
from .records import (
    COMPLETED, CompatibilityEntry, ExecutorIdentity, ExecutorProfile, StepAccounting, StepInput, StepOutput,
    StepOutputPort, StepRequirements, StepRunResult, StepServices)

NOW = datetime(2026, 9, 24, 12, tzinfo=timezone.utc)
FIXTURE_DIGEST = digest("fixture process")


def _slot():
    return next(item for item in load_engine_slot_catalog().slots if item.slot_id == "step_executor")


class FixtureStepEngine:
    """An in-process fixture engine that claims whatever its constructor says; for checks only."""

    def __init__(self, harness_id, kind, isolation, modes=("hybrid", "non_deterministic"), *, claims=None,
                 answer="fixture answer"):
        self.harness_id, self.kind, self.isolation, self.modes = harness_id, kind, isolation, modes
        self.claims, self.answer, self.calls = dict(claims or {}), answer, 0

    def info(self):
        return HarnessAdapterInfo(self.harness_id, "1.0.0", "fixture", "1.0.0", ("typed_request",), (), True, "",
                                  HarnessExecutionCapabilities(("typed_request",), (), self.isolation),
                                  ADAPTER_CONTRACT_VERSION, self.kind, (STEP_EDGE,))

    def executor_profile(self):
        placement = "in_process" if self.isolation == "none" else "fresh_process"
        return ExecutorProfile(self.kind, self.isolation, placement, "supported", self.modes, ("typed_request",),
                               ("model_calls", "wall_time"), (), "loopback_model_endpoint",
                               "openai_chat_completions", "none", ("pure",) if placement == "in_process"
                               else ("spawns_process",),
                               (CompatibilityEntry("instruction_file", "agents_md/1", "1.0.0", "fixture/1",
                                                   "step_folder", "automatic", "native"),))

    def run_step(self, request, services):
        self.calls += 1
        port = request.output_ports[0]
        claimed = ExecutorIdentity("claimed.engine@9.9.9", digest("x"), digest("y"), "", "", True)
        return StepRunResult(request.request_id, request.digest, COMPLETED, "", "",
                             (StepOutput(port.name, port.media_type, self.answer),), (), (), "none",
                             StepAccounting(1, 3, 2, None), (), self.claims, claimed, (), 0.001, None)


def _installation(engine, kind=None):
    settings = (step_engines.loop_settings() if (kind or engine.info().engine_kind) == "in_process_runner"
                else {"record_type": "fixture_settings/v1"})
    return EngineInstallation(engine.info().harness_id, engine.info().harness_id, kind or engine.info().engine_kind,
                              True, settings, None, None)


def _qualification(engine, installation, rung="step_finished"):
    descriptor = step_engines.project_descriptor(engine, installation, as_of=NOW)
    return EngineQualification("step_executor", descriptor.engine_ref, descriptor.content_digest,
                               installation.installation_digest, QualificationScope(STEP_EDGE, None, ()),
                               "local_contract", rung, (EvidenceReference("artifacts/fixture.json", digest("e")),),
                               "independent-reviewer@fixture", "approved", "2026-09-24T00:00:00Z",
                               "2026-10-24T00:00:00Z")


def host(*engines, initial=None, fallbacks=(), work_root="/nonexistent", qualified=True):
    installations = tuple(_installation(item) for item in engines)
    names = tuple(item.installation_id for item in installations)
    policy = EngineSelectionPolicy(
        "step_executor", "1.0.0", "default", tuple(initial or names[:1]), tuple(fallbacks), not fallbacks,
        ("engine_reported_failure",) if fallbacks else (), MetaPreferencePolicy(("declared-order",)), None,
        {"loop": ("pin", "exclude", "prefer"), "harness": ("prefer",)}, None, (), False)
    configuration = EngineSlotConfiguration("step_executor", "1.0.0", installations, {"default": policy},
                                            "declared", digest("host"))
    qualifications = {item.installation_id: _qualification(engine, item)
                      for engine, item in zip(engines, installations)} if qualified else {}
    return StepExecutionHost(_slot(), configuration, dict(zip(names, engines)), qualifications,
                             StepServices(work_root))


def _owner():
    from ...loop.recursive_loop import Loop, LoopConfig
    return Loop("own one step", LoopConfig(framework="custom", custom_steps=("act",),
                                            allowable_modes=("deterministic",), preferred_modes=("deterministic",),
                                            delegated_modes=("deterministic", "hybrid", "non_deterministic")))


def deterministic_request(procedure="contract.match@1", **changes):
    base = step_request(
        mode="deterministic", authorize_model_calls=False, procedure_ref=procedure,
        owning_profile_ref="practitioner.code_execution@1.0.0",
        procedure_parameters={"mode": "canonical"},
        inputs=(StepInput("expected", "application/json", '{"total": 3}'),
                StepInput("observed", "application/json", '{"total":3}')),
        output_ports=(StepOutputPort("match", "application/json", True),),
        requirements=StepRequirements(delegation_required=False))
    return replace(base, **changes)


def _refused(action, code=None) -> bool:
    try:
        action()
    except EngineRecordError as exc:
        return code is None or exc.code == code
    except Exception:
        return False
    return False


def the_loop_runtime_runs_a_step_as_a_canonical_loop() -> bool:
    """Known wrong: a step the Loop engine answers without running the five-step Loop; an
    unknown or parked procedure run anyway; a model-led step run in process."""
    owner = _owner()
    result = run_step_in_loop(deterministic_request(), parent=owner)
    steps = [event.get("step") for event in owner.ledger.events if event.get("event") == "run_step"]
    matched = json.loads(result.outputs[0].text)
    unknown = run_step_in_loop(deterministic_request("text.invented@1"))
    parked = run_step_in_loop(deterministic_request("solution.solve@1"))
    return (result.status == "completed" and matched["matched"] is True
            and steps == ["load", "choose", "act", "check", "commit"]
            and dict(result.native_identities)["step_profile"] == "practitioner.compact_five_step"
            and (unknown.status, unknown.error_code) == ("refused", "procedure_unknown")
            and (parked.status, parked.error_code) == ("refused", "procedure_parked")
            and run_step_in_loop(step_request()).status == "refused")


def a_parked_procedure_is_refused_until_its_suite_returns() -> bool:
    """Known wrong: a parked capability callable from the live runtime; a live procedure
    whose checks the self-test does not collect."""
    from ..._self_test import self_test as _unused  # noqa: F401  (the suite list is read below)
    source = (Path(__file__).resolve().parents[2] / "_self_test.py").read_text(encoding="utf-8")
    try:
        procedure_for(PARKED_PROCEDURES[0].reference)
        return False
    except ProcedureRefused as exc:
        parked = exc.code == "procedure_parked"
    return parked and all(f'"{item.suite}"' in source for item in LIVE_PROCEDURES)


def a_delegation_claim_cannot_be_met_by_an_in_process_engine() -> bool:
    """Known wrong (design 13.13): a step requiring delegation offered only an in-process
    runner registered under a harness-looking name that even claims a sandbox; the status
    must be unavailable and no engine may be called."""
    impostor = FixtureStepEngine("opencode_local", "in_process_runner", "os_sandbox",
                                 claims={"process_identity": FIXTURE_DIGEST, "sandbox_profile_digest": FIXTURE_DIGEST})
    execution = execute_step(step_request(), host(impostor), parent=_owner(), as_of=NOW)
    refusals = {item.code for entry in execution.decisions[0].eligibility for item in entry.refusals}
    return (execution.result.status == "unavailable" and impostor.calls == 0 and not execution.attempts
            and "engine_kind_not_allowed" in refusals)


def delegated_is_computed_by_the_envelope() -> bool:
    """Known wrong: an engine that writes delegated true into its own result; a delegating
    kind with no process identity counted as delegation."""
    claims = {"process_identity": FIXTURE_DIGEST, "sandbox_profile_digest": FIXTURE_DIGEST}
    confined = FixtureStepEngine("fixture.confined", "native_protocol_harness", "os_sandbox", claims=claims)
    unconfined = FixtureStepEngine("fixture.unidentified", "native_protocol_harness", "os_sandbox")
    good = execute_step(step_request(), host(confined), parent=_owner(), as_of=NOW).result
    bad = execute_step(step_request(), host(unconfined), parent=_owner(), as_of=NOW).result
    return (good.executor.delegated is True and good.executor.engine_ref == "fixture.confined@1.0.0"
            and bad.status == "completed" and bad.executor.delegated is False)


def a_harness_without_a_proven_fresh_instance_is_ineligible_for_one_harness_per_step() -> bool:
    """Known wrong: an engine whose fresh start was only declared, or proven at a rung that
    shows no loaded material, selected for a step that requires one harness per step."""
    claims = {"process_identity": FIXTURE_DIGEST, "sandbox_profile_digest": FIXTURE_DIGEST}
    engine = FixtureStepEngine("fixture.fresh", "native_protocol_harness", "os_sandbox", claims=claims)
    fresh = replace(step_request(), requirements=StepRequirements(fresh_instance_required=True))
    unqualified = execute_step(fresh, host(engine, qualified=False), parent=_owner(), as_of=NOW)
    low = host(engine)
    installation = low.configuration.installed[0]
    connected = replace(low, qualifications={installation.installation_id: _qualification(
        engine, installation, rung="connected")})
    low_rung = execute_step(fresh, connected, parent=_owner(), as_of=NOW)
    proven = execute_step(fresh, host(engine), parent=_owner(), as_of=NOW)
    return (unqualified.result.status == "unavailable" and low_rung.result.status == "unavailable"
            and proven.result.status == "completed")


def a_semantic_step_without_a_bound_step_executor_is_refused() -> bool:
    """Known wrong: a model-led step with no eligible engine run by some in-process path."""
    loop_only = host(LoopRuntimeStepEngine())
    execution = execute_step(step_request(), loop_only, parent=_owner(), as_of=NOW)
    return (execution.result.status == "unavailable" and execution.result.failure_kind == "engine_unavailable"
            and not execution.attempts)


def a_step_runs_on_the_loop_runtime_or_an_outside_harness_with_no_caller_change() -> bool:
    """Known wrong: the caller must name the engine, or the two runs return different keys.
    The same call serves a deterministic step on Baltor's Loop runtime and a model-led
    step on an outside harness; only the host's slot configuration differs."""
    claims = {"process_identity": FIXTURE_DIGEST, "sandbox_profile_digest": FIXTURE_DIGEST}
    outside = FixtureStepEngine("fixture.outside", "native_protocol_harness", "os_sandbox", claims=claims)
    both = host(LoopRuntimeStepEngine(), outside, initial=("baltor_loop.in_process", "fixture.outside"))
    ours = execute_step(deterministic_request(), both, parent=_owner(), as_of=NOW)
    theirs = execute_step(step_request(), both, parent=_owner(), as_of=NOW)
    return (ours.result.status == theirs.result.status == "completed"
            and ours.result.executor.engine_ref == "baltor_loop.in_process@1.0.0"
            and theirs.result.executor.engine_ref == "fixture.outside@1.0.0"
            and set(ours.result.to_dict()) == set(theirs.result.to_dict())
            and ours.result.executor.delegated is False and theirs.result.executor.delegated is True)


def a_fallback_carries_the_step_to_the_next_declared_engine() -> bool:
    """Known wrong: a failed first engine that ends the step although the policy names a
    fallback, or a fallback that reruns the engine that failed."""
    claims = {"process_identity": FIXTURE_DIGEST, "sandbox_profile_digest": FIXTURE_DIGEST}

    class Failing(FixtureStepEngine):
        def run_step(self, request, services):
            self.calls += 1
            return StepRunResult(request.request_id, request.digest, "failed", "engine_reported_failure",
                                 "fixture_failure", (), (), (), "none", StepAccounting(1, 1, 1, None), (),
                                 self.claims, None, (), None, None)
    first = Failing("fixture.first", "native_protocol_harness", "os_sandbox", claims=claims)
    second = FixtureStepEngine("fixture.second", "native_protocol_harness", "os_sandbox", claims=claims)
    execution = execute_step(step_request(), host(first, second, initial=("fixture.first",),
                                                  fallbacks=("fixture.second",)), parent=_owner(), as_of=NOW)
    return (execution.result.status == "completed" and first.calls == 1 and second.calls == 1
            and [item.phase for item in execution.decisions] == ["initial", "fallback"]
            and execution.decisions[1].consumed.model_calls == 1)


def the_in_process_loop_engine_qualifies_on_its_fixture_step() -> bool:
    """Known wrong: a Loop engine qualification that never ran the step, or that approves a
    step whose output it did not read."""
    engine = LoopRuntimeStepEngine()
    with tempfile.TemporaryDirectory(prefix="le-qualify-") as root:
        qualification, record = qualify_engine(engine, _installation(engine), work_root=Path(root), as_of=NOW)
    return (qualification.decision == "approved" and qualification.ladder_rung == "step_finished"
            and record["output_read"] is True and record["model_calls_to_a_real_model"] == 0)


def native_loading_is_never_inferred_from_a_bridge_a_session_or_an_exit() -> bool:
    """Known wrong (roadmap S-6.31): a harness recorded at the rung material loaded because it
    exited cleanly with an answer, although no model request carried the step's markers."""
    engine = FixtureStepEngine("fixture.silent", "native_protocol_harness", "os_sandbox")
    with tempfile.TemporaryDirectory(prefix="le-qualify-") as root:
        qualification, record = qualify_engine(engine, _installation(engine), work_root=Path(root), as_of=NOW)
    return qualification.decision == "rejected" and qualification.ladder_rung == "connected" and not any(
        record["markers_found"].values())


CHECKS = (
    ("the_loop_runtime_runs_a_step_as_a_canonical_loop", the_loop_runtime_runs_a_step_as_a_canonical_loop, ()),
    ("a_parked_procedure_is_refused_until_its_suite_returns", a_parked_procedure_is_refused_until_its_suite_returns,
     ()),
    ("a_delegation_claim_cannot_be_met_by_an_in_process_engine",
     a_delegation_claim_cannot_be_met_by_an_in_process_engine,
     (("removed_delegation_kind_rule_is_detected", ((step_envelope, "DELEGATION_GROUP", "no_such_group"),)),)),
    ("delegated_is_computed_by_the_envelope_and_names_a_separate_confined_process",
     delegated_is_computed_by_the_envelope,
     (("removed_delegation_computation_is_detected", ((step_envelope, "delegated", lambda *a, **k: True),)),)),
    ("a_harness_without_a_proven_fresh_instance_is_ineligible_for_one_harness_per_step",
     a_harness_without_a_proven_fresh_instance_is_ineligible_for_one_harness_per_step,
     (("removed_fresh_instance_proof_is_detected",
       ((step_engines, "proves_fresh_instance", lambda *a, **k: True),)),)),
    ("a_semantic_step_without_a_bound_step_executor_is_refused",
     a_semantic_step_without_a_bound_step_executor_is_refused, ()),
    ("a_step_runs_on_the_loop_runtime_or_an_outside_harness_with_no_caller_change",
     a_step_runs_on_the_loop_runtime_or_an_outside_harness_with_no_caller_change, ()),
    ("a_fallback_carries_the_step_to_the_next_declared_engine", a_fallback_carries_the_step_to_the_next_declared_engine,
     ()),
    ("the_in_process_loop_engine_qualifies_on_its_fixture_step",
     the_in_process_loop_engine_qualifies_on_its_fixture_step, ()),
    ("native_loading_is_never_inferred_from_a_bridge_a_session_or_an_exit",
     native_loading_is_never_inferred_from_a_bridge_a_session_or_an_exit, ()),
)


def run_checks() -> dict:
    tests = []
    for name, scenario, controls in CHECKS:
        tests.append({"name": name, "passed": _observe(scenario)})
        for control, removed in controls:
            patches = [patch.object(module, guard, replacement) for module, guard, replacement in removed]
            for item in patches:
                item.start()
            try:
                tests.append({"name": control, "passed": _observe(scenario) is False})
            finally:
                for item in patches:
                    item.stop()
    tests += launch_checks()
    return {"tests": tests, "passed": sum(item["passed"] for item in tests), "total": len(tests),
            "all_passed": all(item["passed"] for item in tests)}


def _observe(scenario) -> bool:
    try:
        return bool(scenario())
    except Exception:
        return False


def self_test() -> dict:
    return run_checks()
