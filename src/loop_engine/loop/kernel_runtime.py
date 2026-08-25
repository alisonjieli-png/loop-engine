"""Canonical Loop envelope for Practitioner-kernel calculations.

The kernel pass calculator is a private deterministic control algorithm.  This
module is the operational boundary: it binds that calculation to one exact
Practitioner ``Loop``, one immutable definition, one runtime context, and one
shared event log.  Recursive work uses ``Loop.spawn`` and runs the resulting
Loop to a terminal state before returning a typed value.
"""
from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, replace
from typing import Any

from .kernel import (KERNEL_NODES, MAX_SPAWN_DEPTH, KernelRunRequest,
                     ProblemSpec, _calculate_kernel_passes)
from .loop_contract import LoopContract
from .loop_definition import LoopDefinition, LoopStartRequest
from .loop_role import (LoopRelationship, LoopRelationshipKind, LoopRole,
                        LoopRoleIdentity)
from .recursive_loop import (INTERNAL_MODE_NAMES, MODES, Loop, LoopConfig,
                             LoopLedger, StepOutcome)
from .runtime_context import (InternalRuntimeBinding, InternalRuntimeMechanics,
                              LoopRuntimeContext)


class KernelRuntimeError(RuntimeError):
    """Kernel work was requested without a valid canonical Loop owner."""


@dataclass(frozen=True)
class SpawnedKernelRun:
    """Typed result returned from one terminal Spawned Practitioner Loop."""

    loop_id: str
    definition_id: str
    definition_version: str
    definition_digest: str
    relationship: LoopRelationship
    terminal_code: str
    run: dict


_ACTIVE_KERNEL_OWNER: ContextVar[Loop | None] = ContextVar(
    "loop_engine_active_kernel_owner", default=None)


def current_kernel_owner() -> Loop | None:
    """Return the owner only while its private kernel calculation is active."""
    return _ACTIVE_KERNEL_OWNER.get()


def _validate_request(request: KernelRunRequest) -> None:
    if not isinstance(request, KernelRunRequest):
        raise KernelRuntimeError("run_kernel_passes needs a KernelRunRequest")
    if not isinstance(request.spec, ProblemSpec):
        raise KernelRuntimeError("KernelRunRequest.spec must be a ProblemSpec")
    if not isinstance(request.impls, dict):
        raise KernelRuntimeError("KernelRunRequest.impls must be a mapping")
    if request.selected_mode not in MODES:
        raise KernelRuntimeError(
            f"selected_mode must be one of {MODES}")
    if (request.max_passes is not None
            and (not isinstance(request.max_passes, int)
                 or isinstance(request.max_passes, bool)
                 or request.max_passes < 1)):
        raise KernelRuntimeError("max_passes must be positive when provided")
    if (request.event_dir is not None
            and (not isinstance(request.event_dir, str)
                 or not request.event_dir.strip())):
        raise KernelRuntimeError("event_dir must be a non-empty path")


def _supported_modes(selected_mode: str) -> tuple[str, ...]:
    if selected_mode == "deterministic":
        return ("deterministic",)
    return ("deterministic", selected_mode)


def _definition_for(request: KernelRunRequest) -> LoopDefinition:
    supported = _supported_modes(request.selected_mode)
    config = LoopConfig(
        framework="nine_step",
        logical_kind="task_semantic",
        allowable_modes=supported,
        preferred_modes=(request.selected_mode,) + tuple(
            mode for mode in supported if mode != request.selected_mode),
        delegated_modes=MODES,
        power="standard",
        llm_thinking_power=(
            "medium" if request.selected_mode != "deterministic" else ""),
        max_depth=MAX_SPAWN_DEPTH,
        loop_condition="steps_remain",
        exit_condition="steps_complete",
    )
    identity = LoopRoleIdentity(
        LoopRole.PRACTITIONER, "practitioner.reference_nine_step")
    contract = LoopContract(
        name="run Practitioner kernel passes",
        execution_mode=INTERNAL_MODE_NAMES[request.selected_mode],
        input_roles=("problem_spec",), output_roles=("kernel_run",),
        effects=("pure",), role="practitioner")
    return LoopDefinition.from_runtime(
        identity=identity, contract=contract, config=config,
        definition_id="practitioner.kernel_passes", version="1.0.0",
        installed_executor_modes=supported)


def _strict_context(definition: LoopDefinition) -> LoopRuntimeContext:
    bindings = tuple(
        InternalRuntimeBinding(
            f"kernel.{capability}", object(), (capability,))
        for capability in definition.required_capabilities)
    return LoopRuntimeContext(internal=InternalRuntimeMechanics(
        bindings=bindings,
        permissions=definition.permissions,
        executor_modes=definition.installed_executor_modes,
        compatibility_composition=False))


def _starting_loop(request: KernelRunRequest) -> Loop:
    definition = _definition_for(request)
    start = LoopStartRequest(
        goal=request.spec.objective,
        definition=definition,
        relationship=LoopRelationship.starting(),
        runtime_context=_strict_context(definition),
        event_log=LoopLedger())
    return Loop(start)


def _require_owner(request: KernelRunRequest) -> Loop:
    owner = request.owner_loop
    if owner is None:
        return _starting_loop(request)
    if not isinstance(owner, Loop):
        raise KernelRuntimeError("owner_loop must be the exact Loop instance")
    if owner.identity.role is not LoopRole.PRACTITIONER:
        raise KernelRuntimeError("kernel work needs a Practitioner Loop owner")
    if owner.goal != request.spec.objective:
        raise KernelRuntimeError(
            "owner Loop goal must equal the kernel ProblemSpec objective")
    if request.selected_mode not in owner.definition.supported_modes:
        raise KernelRuntimeError(
            f"owner Loop does not support {request.selected_mode!r}")
    if request.selected_mode not in owner.definition.installed_executor_modes:
        raise KernelRuntimeError(
            f"owner Loop has no {request.selected_mode!r} executor")
    if owner.is_terminal:
        raise KernelRuntimeError("a terminal Loop cannot own new kernel work")
    return owner


def _calculate_inside(owner: Loop, request: KernelRunRequest) -> dict:
    owner.ledger.record(
        loop_id=owner.loop_id, event="custom",
        custom_kind="kernel_input_bound",
        input_role="problem_spec", objective=request.spec.objective,
        budget_passes=request.spec.budget_passes)
    token = _ACTIVE_KERNEL_OWNER.set(owner)
    try:
        run = _calculate_kernel_passes(request)
    finally:
        _ACTIVE_KERNEL_OWNER.reset(token)
    owner.ledger.record(
        loop_id=owner.loop_id, event="custom",
        custom_kind="kernel_passes_completed",
        passes=run["passes"], final_route=run["final_route"],
        events_path=run["events_path"] or "")
    owner.ledger.record(
        loop_id=owner.loop_id, event="custom",
        custom_kind="kernel_output_bound",
        output_role="kernel_run", final_route=run["final_route"],
        passes=run["passes"])
    return run


def _run_owner(owner: Loop, request: KernelRunRequest) -> tuple[dict, Any]:
    state: dict[str, Any] = {"run": None}

    def handler(_loop: Loop, step: str, _context: dict) -> StepOutcome:
        if step == "act" and state["run"] is None:
            state["run"] = _calculate_inside(owner, request)
            output = state["run"]["final_route"] or "kernel:no_route"
            mode = request.selected_mode
        else:
            output = f"kernel:{step}:complete"
            mode = "deterministic"
        return StepOutcome(
            output=output, mode=mode, confidence=1.0)

    # Loop checks its step budget before it checks sequence exhaustion.  One
    # final control iteration is therefore needed to record the successful
    # ``done`` transition after the ninth completed step.
    result = owner.run(handler=handler, max_steps=len(KERNEL_NODES) + 1)
    if state["run"] is None:
        raise KernelRuntimeError("the owner Loop terminated before kernel work")
    if not owner.is_terminal:
        raise KernelRuntimeError("the owner Loop did not reach a terminal state")
    return state["run"], result


def execute_kernel_run(request: KernelRunRequest) -> dict:
    """Execute one request through an exact Starting or supplied owner Loop."""
    _validate_request(request)
    owner = _require_owner(request)
    active = current_kernel_owner()
    already_running = getattr(owner, "_it", None) is not None
    if already_running:
        if active is not None and active is not owner:
            raise KernelRuntimeError(
                "kernel work cannot cross from one active Loop owner to another")
        run = _calculate_inside(owner, request)
        loop_result = owner.result()
    else:
        run, loop_result = _run_owner(owner, request)
    run.update({
        "loop_id": owner.loop_id,
        "loop_definition_id": owner.definition_ref.definition_id,
        "loop_definition_version": owner.definition_ref.version,
        "loop_definition_digest": owner.definition_ref.content_digest,
        "loop_relationship": owner.relationship.to_dict(),
        "loop_terminal": owner.is_terminal,
        "loop_terminal_code": (
            loop_result.terminal_code if owner.is_terminal else ""),
    })
    return run


def run_spawned_kernel(spec: ProblemSpec, impls: dict, *,
                       selected_mode: str = "deterministic") -> SpawnedKernelRun:
    """Spawn, run, and type the result of one recursive Practitioner Loop."""
    parent = current_kernel_owner()
    if parent is None:
        raise KernelRuntimeError(
            "recursive kernel work requires an active Practitioner Loop owner")
    request = KernelRunRequest(
        spec=spec, impls=impls, selected_mode=selected_mode)
    definition = _definition_for(request)
    relationship = LoopRelationship.spawned_by(parent.loop_id)
    spawned = parent.spawn(
        spec.objective, definition=definition, relationship=relationship)
    run = execute_kernel_run(replace(request, owner_loop=spawned))
    result = spawned.result()
    if (spawned.ledger is not parent.ledger
            or relationship.kind is not LoopRelationshipKind.SPAWNED_BY
            or relationship.spawned_by_loop_id != parent.loop_id
            or not spawned.is_terminal):
        raise KernelRuntimeError(
            "Spawned Practitioner did not preserve ownership and closure")
    return SpawnedKernelRun(
        loop_id=spawned.loop_id,
        definition_id=spawned.definition_ref.definition_id,
        definition_version=spawned.definition_ref.version,
        definition_digest=spawned.definition_ref.content_digest,
        relationship=spawned.relationship,
        terminal_code=result.terminal_code,
        run=run)


def self_test() -> dict:
    """Adversarial checks for the kernel's one-runtime ownership boundary."""
    from .kernel import (PractitionerState, _calculate_kernel_pass,
                         default_impls, run_kernel_passes)

    tests: list[dict] = []

    def check(name: str, passed: bool, detail: str) -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    spec = ProblemSpec("kernel ownership test",
                       success_criteria=("understanding",))
    request = KernelRunRequest(spec, default_impls())
    owner = _starting_loop(request)
    run = run_kernel_passes(replace(request, owner_loop=owner))
    events = owner.ledger.events
    spawned = [event for event in events if event.get("event") == "spawn"]
    terminal_ids = {event["loop_id"] for event in events
                    if event.get("event") == "terminal"}

    check(
        "direct_kernel_run_creates_one_exact_starting_practitioner_loop",
        run["loop_id"] == owner.loop_id
        and run["loop_relationship"] == {"relationship_kind": "starting"}
        and run["loop_terminal"] and run["loop_terminal_code"] == "ACCEPTED"
        and owner.identity.profile_id == "practitioner.reference_nine_step"
        and owner.definition_ref.definition_id == "practitioner.kernel_passes",
        f"{owner.loop_id} {owner.relationship.to_dict()} "
        f"{owner.definition_ref.to_dict()}")

    exact_fields = (
        "loop_definition_id", "loop_definition_version",
        "loop_definition_digest", "profile_id", "profile_version",
        "loop_condition", "exit_condition")
    check(
        "every_recursive_kernel_run_has_exact_definition_and_spawned_edge",
        bool(spawned) and all(
            all(event.get(field) for field in exact_fields)
            and event.get("relationship_kind") == "spawned_by"
            and event.get("spawned_by_loop_id") == owner.loop_id
            for event in spawned),
        f"{len(spawned)} Spawned Loop edge(s) with complete definition fields")

    spawned_ids = {event["loop_id"] for event in spawned}
    check(
        "spawned_kernel_loops_share_the_event_log_and_reach_terminal_state",
        spawned_ids <= owner.ledger.loops()
        and spawned_ids <= terminal_ids
        and owner.audit_closure()["closed"],
        f"spawned={sorted(spawned_ids)} terminal={sorted(terminal_ids)}")

    returned = [result.result for record in run["records"]
                for result in record.results
                if isinstance(result.result, dict)
                and result.result.get("loop_id")]
    check(
        "recursive_kernel_result_is_typed_to_the_exact_terminal_loop",
        bool(returned) and all(
            item.get("loop_id") in spawned_ids
            and item.get("terminal_code") == "ACCEPTED"
            and isinstance(item.get("passes"), int)
            for item in returned),
        f"{len(returned)} typed recursive result(s)")

    bare_state = PractitionerState(spec=spec)
    bare_record, _ = _calculate_kernel_pass(bare_state, default_impls())
    check(
        "unit_pass_cannot_start_recursive_work_without_a_loop_owner",
        bool(bare_record.results)
        and all(result.errors for result in bare_record.results)
        and "active Practitioner Loop owner" in bare_record.results[0].errors[0],
        "the private unit calculator returns an explicit ownership error")

    active_request = KernelRunRequest(
        ProblemSpec("active owner test", success_criteria=("done",)),
        default_impls())
    active_owner = _starting_loop(active_request)
    captured: dict[str, Any] = {}

    def active_handler(loop: Loop, step: str, _context: dict) -> StepOutcome:
        if step == "act":
            captured.update(execute_kernel_run(replace(
                active_request, owner_loop=loop)))
        return StepOutcome(f"active:{step}", "deterministic", 1.0)

    active_owner.run(handler=active_handler, max_steps=len(KERNEL_NODES) + 1)
    check(
        "an_active_exact_owner_is_reused_without_a_second_starting_loop",
        captured.get("loop_id") == active_owner.loop_id
        and len([event for event in active_owner.ledger.events
                 if event.get("event") == "init"
                 and event.get("relationship_kind") == "starting"]) == 1
        and active_owner.is_terminal,
        f"kernel run remained owned by {active_owner.loop_id}")

    passed = sum(1 for test in tests if test["passed"])
    return {"record_type": "kernel_runtime_self_test", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
