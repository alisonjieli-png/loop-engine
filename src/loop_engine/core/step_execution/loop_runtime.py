"""Baltor's own Loop runtime as a step executor engine: the custom Loop engine.

Owns run_step_in_loop, which runs one deterministic step as a canonical Loop
with the compact five-step profile (load the typed inputs, choose the declared
procedure, act, check the output against its port, commit it), and
LoopRuntimeStepEngine, the in_process_runner engine of the step_executor slot
that calls it in this process. The same function is the inner implementation
of the custom_loop_harness engine: core/step_execution/loop_harness_process.py
runs it in a separate, sandboxed process declared by the manifest
``baltor_loop.process``. A step therefore runs on Baltor's own runtime or on an
outside harness with no change to the caller; only the host's slot
configuration differs. Belongs to the step execution component (roadmap
S-6.30, S-6.31).
Does not own: selection, the envelope, a model call (a deterministic step
makes none) or acceptance. It is an engine, never a runtime type: the Loop it
runs is the one canonical Loop.
"""
from __future__ import annotations

import json
import time

from ..engines.records import EngineRecordError
from ..external_harness import HarnessAdapterInfo
from ..external_harness_contract import ADAPTER_CONTRACT_VERSION, STEP_EDGE
from ..harness_execution_contracts import HarnessExecutionCapabilities
from .procedures import JSON_MEDIA_TYPE, ProcedureRefused, procedure_for
from .records import (
    COMPLETED, DETERMINISTIC_MODE, FAILED, IN_PROCESS, NO_MODEL_CALLS, REFUSED, CompatibilityEntry, ExecutorProfile,
    StepOutput, StepRunResult)

ENGINE_ID = "baltor_loop.in_process"
ENGINE_VERSION = "1.0.0"
ENGINE_KIND = "in_process_runner"
#: The compact five-step profile the step Loop runs, one procedure call in act.
STEP_PROFILE = "practitioner.compact_five_step"


def _result(request, status, *, failure_kind="", error_code="", outputs=(), identities=None, seconds=None):
    return StepRunResult(request.request_id, request.digest, status, failure_kind, error_code, tuple(outputs), (),
                         (), "none", NO_MODEL_CALLS, (), identities or {}, None, (), seconds, None)


def run_step_in_loop(request, *, parent=None) -> StepRunResult:
    """Run one deterministic step as a canonical Loop and return its typed result.

    With a parent the step Loop is Spawned by it and shares its ledger; without
    one (a separate process) it is a Starting Loop with a ledger of its own."""
    from ...loop.loop_role import LoopRoleIdentity
    from ...loop.recursive_loop import Loop, LoopConfig, LoopLedger, StepOutcome
    started = time.monotonic()
    if request.mode != DETERMINISTIC_MODE or not request.procedure_ref:
        return _result(request, REFUSED, failure_kind="capability_requirement_unsatisfied",
                       error_code="loop_engine_runs_deterministic_procedures")
    try:
        procedure = procedure_for(request.procedure_ref)
    except ProcedureRefused as exc:
        return _result(request, REFUSED, failure_kind="capability_requirement_unsatisfied", error_code=exc.code)
    port = next((item for item in request.output_ports if item.required), request.output_ports[0])
    config = LoopConfig(framework="five_step", allowable_modes=("deterministic",),
                        preferred_modes=("deterministic",), delegated_modes=("deterministic",),
                        exit_condition="steps_complete")
    identity = LoopRoleIdentity("practitioner", STEP_PROFILE)
    goal = f"run step {request.step_name} with {procedure.reference}"
    loop = (parent.spawn(goal, config, identity=identity) if parent is not None
            else Loop(goal, config, ledger=LoopLedger(), identity=identity))
    state = {"inputs": {item.name: item.text for item in request.inputs}, "output": None, "error": ""}

    def handler(active, step, context):
        if state["error"]:
            return StepOutcome(output=step + ":skipped", mode="deterministic", confidence=0.0, failed=True)
        try:
            if step == "load":
                missing = [name for name in procedure.inputs if name not in state["inputs"]]
                if missing:
                    raise ProcedureRefused("procedure_input_missing", ",".join(missing))
            elif step == "act":
                state["output"] = procedure.function(state["inputs"], dict(request.procedure_parameters))
            elif step == "check":
                if not isinstance(state["output"], str):
                    raise ProcedureRefused("procedure_output_not_text", procedure.reference)
                if port.media_type == JSON_MEDIA_TYPE:
                    json.loads(state["output"])
        except ProcedureRefused as exc:
            state["error"] = exc.code
        except (ValueError, TypeError, RecursionError):
            state["error"] = "procedure_output_invalid"
        failed = bool(state["error"])
        return StepOutcome(output=f"{step}:{'failed' if failed else 'done'}", mode="deterministic",
                           confidence=0.0 if failed else 1.0, failed=failed)

    run = loop.run(handler=handler, max_steps=5)
    identities = {"loop_id": loop.loop_id, "terminal_code": run.terminal_code, "steps_run": run.steps_run,
                  "step_profile": STEP_PROFILE, "procedure": procedure.reference}
    seconds = round(time.monotonic() - started, 6)
    if state["error"] or state["output"] is None:
        failure = ("output_validation_failed" if state["error"].startswith("procedure_output")
                   else "engine_reported_failure")
        return _result(request, FAILED, failure_kind=failure, error_code=state["error"] or "procedure_no_output",
                       identities=identities, seconds=seconds)
    return _result(request, COMPLETED, outputs=(StepOutput(port.name, port.media_type, state["output"]),),
                   identities=identities, seconds=seconds)


class LoopRuntimeStepEngine:
    """The in_process_runner engine: the canonical Loop runs the step in this process.

    It never counts as delegation, holds no process isolation and makes no
    model call; a step that requires delegation cannot select it."""

    def __init__(self, *, version: str = ENGINE_VERSION):
        self._version = version

    def info(self) -> HarnessAdapterInfo:
        return HarnessAdapterInfo(
            ENGINE_ID, self._version, "loop-engine", self._version, ("typed_request", "deterministic_procedures"),
            ("deterministic steps only; model-led steps are delegated to a harness",), True, "",
            HarnessExecutionCapabilities(("typed_request", "deterministic_procedures"), (), "none"),
            ADAPTER_CONTRACT_VERSION, ENGINE_KIND, (STEP_EDGE,))

    def executor_profile(self) -> ExecutorProfile:
        """A new Loop for each step, with no shared context, state, grant or credential: a warm
        runtime whose fresh start for each step a qualification must still prove."""
        return ExecutorProfile(
            ENGINE_KIND, "none", IN_PROCESS, "supported",
            ("deterministic",), ("typed_request", "deterministic_procedures"), (), (), "none", "none", "none",
            ("pure",), (CompatibilityEntry("instruction_file", "step_instructions/1", ENGINE_VERSION,
                                           "baltor_loop/" + ENGINE_VERSION, "step_folder", "explicit", "embedded"),))

    def run_step(self, request, services) -> StepRunResult:
        parent = getattr(services, "attempt_loop", None)
        try:
            return run_step_in_loop(request, parent=parent)
        except EngineRecordError as exc:
            return _result(request, FAILED, failure_kind="engine_reported_failure", error_code=exc.code)


def self_test():
    """Run the step execution checks, which cover the Loop engine."""
    from .engines_checks import self_test as run_engine_checks
    return run_engine_checks()
