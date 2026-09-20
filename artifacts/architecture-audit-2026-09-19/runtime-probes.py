"""Safe local probes for the runtime audit. No providers or external effects.

Run with PYTHONDONTWRITEBYTECODE=1 and PYTHONPATH=src. The probes only build
records, execute pure arithmetic, construct sandbox arguments, and wait for
30 milliseconds inside a local synchronous fixture. No native harness starts.
Finding flags describe observed audit failures, not passing product checks.
"""

from dataclasses import replace
import json
from pathlib import Path
import time
from types import SimpleNamespace

from loop_engine.code_nodes.solution_canvas import SolutionLoopSpec, SolutionSpec
from loop_engine.code_nodes.solution_compiler import compile_solution, run_compiled
from loop_engine.code_nodes.solution_graph import LoopGraphEndpoint
from loop_engine.core.harness_process import _sandbox
from loop_engine.core.model_gateway import ModelGateway, ModelGatewayConfig
from loop_engine.core.model_routes import ModelRoute, RoutePolicy, RouteRegistry
from loop_engine.loop.delegation_runtime import (
    DelegationBudget,
    DelegationConstraints,
    DelegationSpec,
    LoopPortValue,
    SpawnedTaskManager,
)
from loop_engine.loop.loop_contract import LoopContract
from loop_engine.loop.loop_definition import LoopStartRequest
from loop_engine.loop.loop_profile_catalog import LoopProfileRef
from loop_engine.loop.loop_role import LoopRelationship
from loop_engine.loop.recursive_loop import Loop, LoopConfig, LoopLedger
from loop_engine.loop.runtime_context import InternalRuntimeMechanics, LoopRuntimeContext
from loop_engine.loop.spawned_runtime_port import DeterministicSpawnedExecutor
from loop_engine.loop.supervision_policy import DEFAULT_SUPERVISION_POLICY


def parent_loop():
    return Loop("audit parent", LoopConfig(
        allowable_modes=("deterministic",),
        preferred_modes=("deterministic",),
        delegated_modes=("deterministic",),
    ))


def context_executor_narrowing():
    source = LoopRuntimeContext(internal=InternalRuntimeMechanics(
        executor_modes=("hybrid",)))
    derived = source.derive()
    return {
        "id": "runtime-probe-01",
        "finding": "derive_adds_undeclared_executor",
        "before": source.internal.executor_modes,
        "after": derived.internal.executor_modes,
        "finding_present": not set(derived.internal.executor_modes).issubset(
            source.internal.executor_modes),
    }


def spawn_configuration_preservation():
    parent = parent_loop()
    supervision = replace(DEFAULT_SUPERVISION_POLICY,
                          policy_id="audit.custom", identical_failures_before_stop=2)
    requested = LoopConfig(
        allowable_modes=("deterministic", "hybrid"),
        preferred_modes=("deterministic", "hybrid"),
        delegated_modes=("deterministic", "hybrid"),
        supervision=supervision, output_type="multiple", max_outputs=2,
    )
    spawned = parent.spawn("audit spawned", requested)
    return {
        "id": "runtime-probe-02",
        "finding": "mode_clamping_resets_unrelated_settings",
        "requested_supervision": requested.supervision.policy_id,
        "actual_supervision": spawned.config.supervision.policy_id,
        "requested_output": [requested.output_type, requested.max_outputs],
        "actual_output": [spawned.config.output_type, spawned.config.max_outputs],
        "finding_present": spawned.config.supervision != requested.supervision
        or spawned.config.output_type != requested.output_type
        or spawned.config.max_outputs != requested.max_outputs,
    }


def compatibility_authority():
    parent = parent_loop()
    definition = replace(parent.definition, definition_id="audit.extra_permission",
                         permissions=("audit_permission",))
    compatibility_refused = False
    try:
        spawned = parent.spawn("audit authority", definition=definition)
        spawned_permissions = spawned.runtime_context.internal.permissions
    except (ValueError, RuntimeError):
        compatibility_refused = True
        spawned_permissions = ()
    strict_context = replace(parent.runtime_context,
                             internal=replace(parent.runtime_context.internal,
                                              compatibility_composition=False))
    strict_parent = Loop(LoopStartRequest(
        "strict audit parent", parent.definition, LoopRelationship.starting(),
        strict_context, LoopLedger()))
    strict_refused = False
    try:
        strict_parent.spawn("strict audit authority", definition=definition)
    except ValueError:
        strict_refused = True
    except RuntimeError:
        strict_refused = True
    return {
        "id": "runtime-probe-03",
        "finding": "compatibility_spawn_mints_permission_names",
        "before": parent.runtime_context.internal.permissions,
        "after": spawned_permissions,
        "compatibility_context_refused": compatibility_refused,
        "strict_context_refused": strict_refused,
        "finding_present": not compatibility_refused
        and not set(spawned_permissions).issubset(
            parent.runtime_context.internal.permissions) and strict_refused,
        "scope": "typed context grant only; no operating-system effect attempted",
    }


def graph_fixture():
    spec = SolutionSpec("audit.pipeline", permitted_loop_modes=("deterministic",),
                        loops=(SolutionLoopSpec("first", "increment"),
                               SolutionLoopSpec("second", "times_ten")))
    registry = {"increment": lambda value, params: value + 1,
                "times_ten": lambda value, params: value * 10}
    return spec, registry


def registry_identity():
    spec, registry = graph_fixture()
    compiled = compile_solution(spec, registry)
    before = run_compiled(compiled["plan"], registry, 2)
    registry["increment"] = lambda value, params: value + 100
    replacement_refused = False
    try:
        after = run_compiled(compiled["plan"], registry, 2)
    except (ValueError, RuntimeError):
        replacement_refused = True
        after = None
    return {
        "id": "runtime-probe-04",
        "finding": "compiled_graph_does_not_bind_callable_implementation",
        "graph_digest": compiled["digest"],
        "before": before,
        "after_registry_replacement": after,
        "replacement_refused": replacement_refused,
        "finding_present": not replacement_refused and before != after,
        "scope": "caller-supplied trusted registry; no untrusted-code execution",
    }


def graph_dataflow():
    spec, registry = graph_fixture()
    graph = spec.graph
    first = spec.loops[0].vertex_id
    second = spec.loops[1].vertex_id
    matches = [edge for edge in graph.edges
               if edge.source.vertex_id == first and edge.target.vertex_id == second]
    if len(matches) != 1:
        raise RuntimeError("audit fixture has an unexpected graph shape")
    edge = matches[0]
    changed = replace(
        graph,
        edges=tuple(item for item in graph.edges if item is not edge),
        input_ports=(replace(
            graph.input_ports[0], targets=(*graph.input_ports[0].targets,
                LoopGraphEndpoint(second, edge.target.port_role))),
            *graph.input_ports[1:]),
    )
    validation = changed.validate()
    compiled = compile_solution(SolutionSpec.from_graph(changed), registry)
    observed = run_compiled(compiled["plan"], registry, 2) if compiled["plan"] else None
    return {
        "id": "runtime-probe-05",
        "finding": "group_execution_disagrees_with_declared_dataflow",
        "validation_passed": validation.valid,
        "violations": validation.violations,
        "declared_second_stage_input": "external input 2",
        "expected_under_declared_binding": 20,
        "observed": observed,
        "finding_present": validation.valid and observed != 20,
    }


def instruction_mount_visibility():
    from loop_engine.core.harness_process import HarnessProcessRequest

    if "instruction_material" in HarnessProcessRequest.__dataclass_fields__:
        return {
            "id": "runtime-probe-06",
            "finding": "instance_instruction_folder_not_mounted_in_native_process",
            "finding_present": None,
            "status": "baseline_fixture_superseded",
            "scope": "the new instruction-material contract requires its own actual binding checks; field presence does not prove loading",
        }
    step = Path("/tmp/loop-engine-audit/step-example")
    run = step / "harness-example"
    request = SimpleNamespace(spec=SimpleNamespace(read_only_paths=(), style="opencode"))
    arguments = _sandbox(request, run, step / "broker.sock")
    mounts = [(arguments[index + 1], arguments[index + 2])
              for index, value in enumerate(arguments)
              if value in ("--bind", "--ro-bind")]
    instruction = step / "AGENTS.md"
    visible = any(instruction == Path(source) or Path(source) in instruction.parents
                  for source, _ in mounts)
    return {
        "id": "runtime-probe-06",
        "finding": "instance_instruction_folder_not_mounted_in_native_process",
        "writer_path_from_call_chain": str(instruction),
        "native_work_mount": next(source for source, target in mounts if target == "/work"),
        "writer_path_visible_from_mounts": visible,
        "finding_present": not visible,
        "scope": "sandbox argument construction only; no file write or process launch",
    }


def default_failover_selection():
    gateway = object.__new__(ModelGateway)
    gateway.registry = RouteRegistry((
        ModelRoute("audit.a", "provider_a", "model_a", purposes=("generation",)),
        ModelRoute("audit.b", "provider_b", "model_b", purposes=("generation",)),
    ))
    gateway.policy = RoutePolicy()
    config = ModelGatewayConfig(purpose="generation", route_names=("audit.a", "audit.b"))
    selected = gateway._routes(config)
    refused_failover = gateway._routes(replace(config, allow_failover=False))
    return {
        "id": "runtime-probe-07",
        "finding": "cross_provider_failover_is_enabled_by_config_default",
        "default_allow_failover": config.allow_failover,
        "default_providers": [route.provider for route, _ in selected],
        "explicit_false_providers": [route.provider for route, _ in refused_failover],
        "finding_present": config.allow_failover and len(selected) == 2,
        "scope": "pure route selection; no provider registered or called",
    }


def synchronous_deadline():
    parent = parent_loop()
    spec = DelegationSpec(
        "normalize one customer row", LoopProfileRef("solution.atomic_component"),
        LoopContract("normalize-row", "code_only", input_roles=("raw_row/v1",),
                     output_roles=("clean_row/v1",)),
        inputs=(LoopPortValue("raw_row/v1", {"name": " Ada "}),),
        constraints=DelegationConstraints(
            available_fields=("operation_ref",),
            capability_refs=("solution_canvas", "component_execution")),
        budget=DelegationBudget(wall_time_seconds=0.005),
    )

    def delayed(request):
        time.sleep(0.03)
        return DeterministicSpawnedExecutor()(request)

    manager = SpawnedTaskManager(parent, executor=delayed)
    started = time.monotonic()
    identity = manager.start(spec)
    elapsed = time.monotonic() - started
    result = manager.status(identity).result
    return {
        "id": "runtime-probe-08",
        "finding": "synchronous_delegation_ignores_wall_time_budget",
        "declared_seconds": spec.budget.wall_time_seconds,
        "elapsed_seconds": elapsed,
        "status": result.status.value,
        "outputs": [{"role": item.role, "value": item.value} for item in result.outputs],
        "finding_present": elapsed > spec.budget.wall_time_seconds
        and result.status.value == "succeeded",
        "additional_observation": "default executor returns structural act:done, not normalized data",
    }


if __name__ == "__main__":
    observations = [probe() for probe in (
        context_executor_narrowing, spawn_configuration_preservation,
        compatibility_authority, registry_identity, graph_dataflow,
        instruction_mount_visibility, default_failover_selection, synchronous_deadline,
    )]
    print(json.dumps({"record_type": "runtime_audit_probes/v1",
                      "provider_calls": 0, "observations": observations}, indent=2))
