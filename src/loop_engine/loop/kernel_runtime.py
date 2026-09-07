"""Canonical Loop envelope for Practitioner-kernel calculations.

The kernel pass calculator is a private deterministic control algorithm.  This
module is the operational boundary: it binds that calculation to one exact
Practitioner ``Loop``, one immutable definition, one runtime context, and one
shared event log.  Recursive work uses ``Loop.spawn`` and runs the resulting
Loop to a terminal state before returning a typed value.
"""
from __future__ import annotations

from copy import deepcopy
from contextvars import ContextVar
from dataclasses import dataclass, replace
import hashlib
import json
from typing import Any, Callable

from .kernel import (KERNEL_NODES, MAX_SPAWN_DEPTH, KernelRunRequest,
                     ProblemSpec, _calculate_kernel_passes)
from .loop_contract import LoopContract, execution_mode_for_runtime_mode
from .loop_definition import LoopDefinition, LoopStartRequest
from .loop_role import (LoopRelationship, LoopRelationshipKind, LoopRole,
                        LoopRoleIdentity)
from .recursive_loop import MODES, Loop, LoopConfig, LoopLedger, StepOutcome
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
        execution_mode=execution_mode_for_runtime_mode(request.selected_mode),
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
        budget_passes=request.spec.budget_passes,
        pass_loop_placement="inside_owner_act_step")
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
            # The kernel pass loop runs entirely inside ``act``. Every other
            # step of the owner Loop is a structural boundary marker, never a
            # claim that the named kernel work happened at this position.
            output = f"kernel:{step}:structural_boundary"
            mode = "deterministic"
            return StepOutcome(output=output, mode=mode, confidence=1.0,
                               structural_boundary=True)
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
    run.update(_kernel_metadata(owner, loop_result))
    return run


def _kernel_metadata(owner: Loop, loop_result) -> dict:
    """Project owner identity and closure from the canonical Loop itself."""
    return {
        "loop_id": owner.loop_id,
        "loop_definition_id": owner.definition_ref.definition_id,
        "loop_definition_version": owner.definition_ref.version,
        "loop_definition_digest": owner.definition_ref.content_digest,
        "loop_relationship": owner.relationship.to_dict(),
        "loop_terminal": owner.is_terminal,
        "loop_terminal_code": (
            loop_result.terminal_code if owner.is_terminal else ""),
    }


def _prepare_spawned_kernel(
        owner: Loop, parent: Loop,
        prepare: Callable[[Loop], SpawnedKernelRun | None]) -> SpawnedKernelRun | None:
    """Validate a trusted preparation against the exact newly allocated owner.

    This checks identity and execution evidence. The installed preparation is
    responsible for the task's semantic verification; it is not model input
    or an execution sandbox for an untrusted callable.
    """
    original = {name: getattr(owner, name) for name in (
        "loop_id", "goal", "depth", "definition", "definition_ref", "identity",
        "relationship", "runtime_context", "config", "parent", "ledger")}
    original_ref = owner.definition_ref.to_dict()
    original_relationship = owner.relationship.to_dict()
    original_config = deepcopy(owner.config)
    parent_id, ledger = parent.loop_id, parent.ledger
    token = _ACTIVE_KERNEL_OWNER.set(owner)
    try:
        prepared = prepare(owner)
        stable_references = (
            "definition", "definition_ref", "identity", "relationship",
            "runtime_context", "config", "parent", "ledger")
        if (any(getattr(owner, name) is not original[name]
                for name in stable_references)
                or any(getattr(owner, name) != original[name]
                       for name in ("loop_id", "goal", "depth"))
                or owner.definition.ref.to_dict() != original_ref
                or owner.definition_ref.to_dict() != original_ref
                or owner.relationship.to_dict() != original_relationship
                or owner.config != original_config
                or parent.loop_id != parent_id or parent.ledger is not ledger):
            raise KernelRuntimeError("kernel preparation changed its bound owner")
        if prepared is None:
            if owner.is_terminal or getattr(owner, "_it", None) is not None:
                raise KernelRuntimeError(
                    "continuing preparation must leave its owner unstarted")
            return None
        if type(prepared) is not SpawnedKernelRun:
            raise KernelRuntimeError(
                "completed preparation must return SpawnedKernelRun")
        if not owner.is_terminal:
            raise KernelRuntimeError(
                "completed preparation requires its exact owner to be terminal")
        actual = owner.result()
        claims = {
            "loop_id": owner.loop_id,
            "definition_id": owner.definition_ref.definition_id,
            "definition_version": owner.definition_ref.version,
            "definition_digest": owner.definition_ref.content_digest,
            "relationship": owner.relationship,
            "terminal_code": actual.terminal_code,
        }
        if any(getattr(prepared, name) != value for name, value in claims.items()):
            raise KernelRuntimeError(
                "prepared result does not match its exact terminal Loop")
        metadata = _kernel_metadata(owner, actual)
        terminals = [event for event in ledger.events
                     if event.get("event") == "terminal"
                     and event.get("loop_id") == owner.loop_id]
        if (actual.terminal_code != "ACCEPTED" or len(terminals) != 1
                or terminals[0].get("reason") != actual.stopped
                or any(terminals[0].get(name) != metadata[name] for name in (
                    "loop_definition_id", "loop_definition_version",
                    "loop_definition_digest"))):
            raise KernelRuntimeError(
                "completed preparation requires recorded accepted owner closure")
        run = prepared.run
        if (type(run) is not dict or run.get("final_route") != "stop_success"
                or type(run.get("passes")) is not int or run["passes"] < 1
                or ("solved" in run and run["solved"] is not True)
                or run.get("failure_code") or run.get("failures")):
            raise KernelRuntimeError("prepared kernel projection is not completed")
        if any(name in run and run[name] != value for name, value in metadata.items()):
            raise KernelRuntimeError("prepared kernel projection has conflicting owner metadata")
        try:
            # Detach the returned value without changing Python types that
            # the exact resolver and its verification trace still preserve.
            run = deepcopy({**run, **metadata})
            encoded = json.dumps(
                run, sort_keys=True, separators=(",", ":"),
                allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise KernelRuntimeError(
                "prepared kernel projection must contain exact JSON values") from exc
        ledger.record(
            loop_id=owner.loop_id, event="custom",
            custom_kind="kernel_preparation_completed",
            output_role="kernel_run", final_route=run["final_route"],
            passes=run["passes"],
            projection_digest=hashlib.sha256(encoded.encode()).hexdigest())
        return SpawnedKernelRun(**claims, run=run)
    except (Exception, KeyboardInterrupt):
        # The preparation owns only this newly allocated Loop. Restore its
        # bound identity before recording rejection and closing it on failure.
        for name, value in original.items():
            setattr(owner, name, value)
        if owner.config != original_config:
            owner.config = original_config
        ledger.record(loop_id=original["loop_id"], event="custom",
                      custom_kind="kernel_preparation_rejected")
        owner.cancel("kernel_preparation_rejected")
        raise
    finally:
        _ACTIVE_KERNEL_OWNER.reset(token)


def run_spawned_kernel(spec: ProblemSpec, impls: dict, *,
                       selected_mode: str = "deterministic",
                       prepare: Callable[[Loop], SpawnedKernelRun | None] | None = None,
                       ) -> SpawnedKernelRun:
    """Spawn and run a canonical Practitioner, with optional trusted preparation.

    Preparation is installed by the caller. It may complete an exact qualified
    task through that same Loop, or leave it unstarted for the usual kernel.
    A model response cannot select or supply this callback.
    """
    parent = current_kernel_owner()
    if parent is None:
        raise KernelRuntimeError(
            "recursive kernel work requires an active Practitioner Loop owner")
    request = KernelRunRequest(
        spec=spec, impls=impls, selected_mode=selected_mode)
    _validate_request(request)
    if prepare is not None and not callable(prepare):
        raise KernelRuntimeError("kernel preparation must be callable")
    definition = _definition_for(request)
    relationship = LoopRelationship.spawned_by(parent.loop_id)
    spawned = parent.spawn(
        spec.objective, definition=definition, relationship=relationship)
    if prepare is not None:
        prepared = _prepare_spawned_kernel(spawned, parent, prepare)
        if prepared is not None:
            return prepared
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


def _preparation_checks() -> list[dict]:
    """Exercise trusted preparation through active canonical parent Loops."""
    from .kernel import ResultPacket, default_impls

    tests = []

    def close(owner):
        owner.run(handler=lambda _owner, step, _context: StepOutcome(
            "prepared:" + step, "deterministic", 1.0),
            max_steps=len(owner.steps()) + 1)

    def projection(owner):
        return SpawnedKernelRun(
            owner.loop_id, owner.definition_ref.definition_id,
            owner.definition_ref.version, owner.definition_ref.content_digest,
            owner.relationship, "ACCEPTED", {
                "final_route": "stop_success", "passes": 1,
                "facts": {"exact_value": 7}, "failures": []})

    def exercise(callback, mode="hybrid", *, parent_owner=None):
        captured = {"kernel_calls": 0}
        implementations = default_impls()
        original_orient = implementations["orient"]

        def orient(state):
            captured["kernel_calls"] += 1
            return original_orient(state)

        implementations["orient"] = orient

        def prepare(owner):
            captured["owner"] = owner
            captured["callback_owner_matches"] = current_kernel_owner() is owner
            return callback(owner)

        def act(_state, _plan):
            parent = current_kernel_owner()
            try:
                captured["result"] = run_spawned_kernel(
                    ProblemSpec("prepared subproblem", budget_passes=1, depth=1),
                    implementations, selected_mode=mode, prepare=prepare)
            except Exception as exc:
                captured["error"] = exc
            captured["parent_context_restored"] = current_kernel_owner() is parent
            return [ResultPacket("preparation fixture", result="observed")]

        parent_impls = default_impls()
        parent_impls["act"] = act
        execute_kernel_run(KernelRunRequest(
            ProblemSpec("preparation owner", budget_passes=1), parent_impls,
            max_passes=1, selected_mode=mode, owner_loop=parent_owner))
        return captured

    emitted = []

    def complete(owner):
        close(owner)
        value = projection(owner)
        emitted.append(value)
        return value

    for mode in MODES:
        result = exercise(complete, mode)
        typed = result.get("result")
        owner = result["owner"]
        passed = bool(
            typed and typed.loop_id == owner.loop_id
            and typed.terminal_code == owner.result().terminal_code == "ACCEPTED"
            and typed.run["loop_terminal"] is True
            and typed.run["loop_definition_digest"] == owner.definition_ref.content_digest
            and typed.run["loop_relationship"] == owner.relationship.to_dict()
            and result["kernel_calls"] == 0
            and result["callback_owner_matches"] and result["parent_context_restored"]
            and any(event.get("custom_kind") == "kernel_preparation_completed"
                    and event.get("projection_digest") for event in owner.ledger.events))
        emitted[-1].run["facts"]["exact_value"] = 99
        tests.append({"test": "prepared_exact_owner_completion_" + mode,
                      "passed": passed and typed.run["facts"]["exact_value"] == 7,
                      "detail": "real Loop closure with fixture work; zero provider calls"})

    continued = exercise(lambda _owner: None)
    tests.append({"test": "unresolved_preparation_continues_same_kernel_owner",
                  "passed": "error" not in continued
                  and continued["kernel_calls"] == 1
                  and continued["result"].loop_id == continued["owner"].loop_id
                  and continued["parent_context_restored"],
                  "detail": "None runs the supplied implementations"})

    def different_owner(owner):
        close(owner)
        other = _starting_loop(KernelRunRequest(ProblemSpec("different owner"), {}))
        close(other)
        return projection(other)

    def bad_metadata(owner):
        value = complete(owner)
        value.run["loop_id"] = "different-owner"
        return value

    def closed_without_result(owner):
        close(owner)
        return None

    def cancelled_completion(owner):
        owner.cancel("fixture cancellation")
        return projection(owner)

    def changed_identity(owner):
        owner.goal = "different goal"
        return None

    def changed_ledger(owner):
        owner.ledger = LoopLedger()
        return None

    def wrong_passes(owner):
        value = complete(owner)
        value.run["passes"] = True
        return value

    def wrong_definition(owner):
        return replace(complete(owner), definition_digest="0" * 64)

    def raised_preparation(_owner):
        raise RuntimeError("fixture preparation failure")

    for label, callback in (
            ("active_owner", projection), ("different_owner", different_owner),
            ("conflicting_metadata", bad_metadata),
            ("closed_none", closed_without_result),
            ("cancelled_completion", cancelled_completion),
            ("changed_identity", changed_identity), ("changed_ledger", changed_ledger),
            ("invalid_passes", wrong_passes), ("wrong_definition", wrong_definition),
            ("untyped_completion", lambda owner: (close(owner), {"solved": True})[1]),
            ("raised_preparation", raised_preparation)):
        result = exercise(callback)
        owner = result["owner"]
        completed_first = label in {
            "different_owner", "conflicting_metadata", "closed_none", "invalid_passes",
            "wrong_definition", "untyped_completion"}
        expected_terminal = "ACCEPTED" if completed_first else "CANCELED"
        tests.append({"test": "kernel_preparation_refuses_" + label,
                      "passed": "result" not in result and "error" in result
                      and result["kernel_calls"] == 0
                      and owner.result().terminal_code == expected_terminal
                      and len([event for event in owner.ledger.events
                               if event.get("event") == "terminal"
                               and event.get("loop_id") == owner.loop_id]) == 1
                      and result["parent_context_restored"]
                      and any(event.get("custom_kind") == "kernel_preparation_rejected"
                              for event in owner.ledger.events),
                      "detail": type(result.get("error")).__name__})

    from pathlib import Path
    from types import SimpleNamespace
    from ..core.adaptive_practitioner_records import (
        AdaptivePractitionerDependencies, AdaptivePractitionerRequest,
        AdaptiveRunServices)
    from ..core.adaptive_practitioner_scope import (
        delegated_task_text, prepare_exact_result, spawned_summary)

    original_value = {"verified": True, "value": ({"members": [1, 2]}, 3)}
    assignment = ProblemSpec("prepared subproblem", success_criteria=("retain exact value",))
    task_text = delegated_task_text(assignment)
    resolver_calls = []

    class ExactValueResolver:
        resolver_id = "fixture.exact_prepared_value"

        def supports(self, task):
            return task == task_text

        def execute(self, task):
            resolver_calls.append(task)
            return original_value

    services = AdaptiveRunServices(
        AdaptivePractitionerRequest(task_text, mode="hybrid"),
        AdaptivePractitionerDependencies(deterministic_resolvers=(ExactValueResolver(),)),
        "prepared-value-fixture", Path("."), None, None,
        model_session=SimpleNamespace(calls_used=0, accounting_uncertain=False))
    parent_owner = Loop("preparation owner", LoopConfig(
        allowable_modes=("deterministic", "hybrid"),
        preferred_modes=("hybrid", "deterministic"), delegated_modes=MODES,
        llm_thinking_power="medium"))
    exact = exercise(lambda owner: prepare_exact_result(services, owner),
                     parent_owner=parent_owner)
    prepared = exact.get("result")
    summary = (spawned_summary(prepared, services, spec=assignment, calls_before=0)
               if prepared is not None else {})
    exact_types = bool(
        summary.get("task_complete") is True and exact["kernel_calls"] == 0
        and resolver_calls == [task_text]
        and prepared.run["result"] == original_value
        and type(prepared.run["result"]["value"]) is tuple
        and summary["accepted_result"]["result"] == original_value
        and type(summary["accepted_result"]["result"]["value"]) is tuple)
    isolated = False
    if exact_types:
        summary["accepted_result"]["result"]["value"][0]["members"].append(99)
        summary_isolated = prepared.run["result"]["value"][0]["members"] == [1, 2]
        prepared.run["result"]["value"][0]["members"].append(88)
        isolated = (summary_isolated and original_value["value"][0]["members"] == [1, 2]
                    and dict(services.deterministic_attempt.outputs)["result"] == original_value)
    tests.append({"test": "prepared_exact_value_preserves_tuple_and_nested_alias_isolation",
                  "passed": exact_types and isolated,
                  "detail": "registered fixture resolver through spawned_summary; zero model calls"})
    return tests


def self_test() -> dict:
    """Adversarial checks for the kernel's one-runtime ownership boundary."""
    from .kernel import (PractitionerState, _calculate_kernel_pass,
                         default_impls, run_kernel_passes)

    tests: list[dict] = []

    def check(name: str, passed: bool, detail: str) -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    for mode in MODES:
        mode_request = KernelRunRequest(
            ProblemSpec("mode binding test", success_criteria=("done",)),
            default_impls(), max_passes=1, selected_mode=mode)
        mode_owner = _starting_loop(mode_request)
        mode_run = execute_kernel_run(replace(mode_request, owner_loop=mode_owner))
        check(
            "kernel_runtime_preserves_selected_mode_" + mode,
            mode_owner.contract.runtime_mode == mode
            and mode_owner.is_terminal
            and mode_run["loop_id"] == mode_owner.loop_id
            and any(event.get("event") == "run_step"
                    and event.get("loop_id") == mode_owner.loop_id
                    and event.get("step") == "act"
                    and event.get("mode") == mode
                    for event in mode_owner.ledger.events),
            "classified kernel fixture only; no provider invocation")
    rejected_mode = False
    try:
        execute_kernel_run(KernelRunRequest(
            ProblemSpec("invalid mode"), default_impls(), selected_mode="unknown"))
    except KernelRuntimeError:
        rejected_mode = True
    check("kernel_runtime_refuses_unknown_selected_mode", rejected_mode,
          "invalid modes are refused before definition or execution")

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

    honest_owner = _starting_loop(active_request)
    _run_owner(honest_owner, active_request)
    owner_outputs = [
        str(event.get("output", "")) for event in honest_owner.ledger.events
        if event.get("event") == "run_step"
        and event.get("loop_id") == honest_owner.loop_id]
    check(
        "owner_steps_outside_act_are_labelled_structural_not_complete",
        owner_outputs
        and not any(item.endswith(":complete") for item in owner_outputs)
        and sum(item.endswith(":structural_boundary")
                for item in owner_outputs) == len(KERNEL_NODES) - 1,
        f"{len(owner_outputs)} owner step outputs recorded")

    tests.extend(_preparation_checks())
    passed = sum(1 for test in tests if test["passed"])
    return {"record_type": "kernel_runtime_self_test", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
