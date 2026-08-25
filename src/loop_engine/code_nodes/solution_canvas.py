"""Solution builders and execution over one authoritative Loop graph."""
from __future__ import annotations

from dataclasses import InitVar, dataclass, field

from ..loop.loop_definition import (LoopDefinition, LoopStartRequest)
from ..loop.loop_role import (LoopRelationship, LoopRelationshipKind,
                              LoopRole)
from ..loop.runtime_context import LoopRuntimeContext
from ..loop.recursive_loop import (MODES, Loop, LoopError, LoopLedger,
                                   StepOutcome)
from .solution_graph import (
    GRAPH_COMBINATIONS, LoopGraphDefinition, LoopGraphEdge, LoopGraphEndpoint,
    LoopGraphGroup, LoopGraphInputPort, LoopGraphOutputPort, LoopGraphStage,
    LoopGraphVertex, LoopGraphError, make_solution_loop_definition,
    vertex_from_definition,
)

#: how a composite combines its member solutions.  select_best and
#: gating_router are EXTENDED strategies: they validate here but execute in
#: solution_compiler.run_compiled (they need an evaluator/router callable,
#: enforced at compile time).
ENSEMBLE_METHODS = GRAPH_COMBINATIONS
_EXTENDED = ("select_best", "gating_router")


class SolutionError(ValueError):
    """A solution spec that cannot be honestly executed as declared."""


@dataclass
class SolutionLoopSpec:
    """Compatibility builder for one graph stage of Solution Loop vertices."""
    loop_id: str
    operation: str
    mode: str = "deterministic"
    fallback_operations: tuple = ()
    params: dict = field(default_factory=dict)
    input_role: str = "solution.value/v1"
    output_role: str = "solution.value/v1"
    definition: LoopDefinition | None = None
    fallback_definitions: tuple[LoopDefinition, ...] = ()
    vertex_id: str = field(default="", repr=False)
    fallback_vertex_ids: tuple[str, ...] = field(default=(), repr=False)
    router_vertex_id: str = field(default="", repr=False)
    router_definition: LoopDefinition | None = field(default=None, repr=False)

    def __post_init__(self):
        if self.mode not in MODES:
            raise SolutionError(f"loop {self.loop_id}: mode {self.mode!r} "
                                f"not in {MODES}")
        if not isinstance(self.loop_id, str) or not self.loop_id.strip():
            raise SolutionError("a solution loop needs a non-empty loop_id")
        if not isinstance(self.operation, str) or not self.operation.strip():
            raise SolutionError(
                f"loop {self.loop_id}: operation must be non-empty")
        if (not isinstance(self.input_role, str) or not self.input_role.strip()
                or not isinstance(self.output_role, str)
                or not self.output_role.strip()):
            raise SolutionError(
                f"loop {self.loop_id}: input_role and output_role must be "
                "non-empty typed port names")
        self.fallback_operations = tuple(self.fallback_operations)
        self.fallback_definitions = tuple(self.fallback_definitions)
        if (self.fallback_definitions
                and len(self.fallback_definitions)
                != len(self.fallback_operations)):
            raise SolutionError(
                "fallback_definitions must match fallback_operations")


@dataclass
class SolutionSpec:
    """A narrow builder and projection over ``LoopGraphDefinition``."""
    solution_id: str
    permitted_loop_modes: tuple = MODES
    loops: tuple = ()
    members: tuple = ()
    ensemble: str = "single"
    weights: tuple = ()
    max_members: int = 5
    graph: LoopGraphDefinition | None = field(default=None, repr=False)
    group_id: str = field(default="", repr=False)
    allowed_modes: InitVar["tuple | None"] = None

    def __post_init__(self, allowed_modes) -> None:
        """Accept the old constructor keyword without emitting the old field."""
        if allowed_modes is not None:
            legacy = tuple(allowed_modes)
            if (tuple(self.permitted_loop_modes) != MODES
                    and tuple(self.permitted_loop_modes) != legacy):
                raise SolutionError(
                    "cannot mix permitted_loop_modes with a different legacy "
                    "allowed_modes value")
            self.permitted_loop_modes = legacy
        self.permitted_loop_modes = tuple(self.permitted_loop_modes)
        self.loops = tuple(self.loops)
        self.members = tuple(self.members)
        self.weights = tuple(self.weights)
        if self.graph is None:
            try:
                self.graph = _build_solution_graph(self)
            except (LoopGraphError, ValueError) as exc:
                raise SolutionError(str(exc)) from exc
            self.group_id = self.graph.starting_group_id
            _apply_graph_projection(self)
        else:
            if not isinstance(self.graph, LoopGraphDefinition):
                raise SolutionError("graph must be a LoopGraphDefinition")
            self.group_id = self.group_id or self.graph.starting_group_id
            _apply_graph_projection(self)

    @classmethod
    def from_graph(cls, graph: LoopGraphDefinition, *, group_id: str = ""
                   ) -> "SolutionSpec":
        return cls(graph.graph_id, graph=graph,
                   group_id=group_id or graph.starting_group_id)

    def validate(self) -> dict:
        """Fail-closed validation; the report IS the result."""
        assert self.graph is not None
        v = list(self.graph.validate().violations)
        if len(self.members) > self.max_members:
            v.append(f"{len(self.members)} members exceeds the "
                     f"max_members bound {self.max_members}")
        if self.ensemble == "weighted_average" and \
                len(self.weights) != len(self.members):
            v.append("weighted_average needs one weight per member")
        if self.ensemble != "single" and len(self.members) < 2:
            v.append(f"ensemble {self.ensemble!r} needs >=2 members")
        return {"valid": not v, "violations": list(dict.fromkeys(v))}

    def to_record(self):
        """The searchable String record (facets ride the card)."""
        from ..static_architecture.store_serve import StoreRecord
        from ..static_architecture.facets import string_facets
        return StoreRecord(
            f"solution.{self.solution_id}", "strategy",
            f"Solution spec: {self.solution_id} ({self.ensemble}; modes "
            f"{'/'.join(self.permitted_loop_modes)})",
            body={"role": "solution_graph", "graph": _spec_dict(self),
                  "facets": string_facets(category="solution_spec",
                                          subcategory=self.ensemble)},
            tags=("solution_spec", self.ensemble)
                 + tuple(self.permitted_loop_modes))


def _spec_dict(s: SolutionSpec) -> dict:
    assert s.graph is not None
    return s.graph.to_dict()


def _safe_id(value: str) -> str:
    import re
    cleaned = re.sub(r"[^A-Za-z0-9._:-]+", "_", value).strip("_")
    return cleaned or "loop"


def _build_solution_graph(spec: SolutionSpec) -> LoopGraphDefinition:
    """Compile compatibility builders into one complete Loop graph."""
    vertices: list[LoopGraphVertex] = []
    edges: list[LoopGraphEdge] = []
    groups: list[LoopGraphGroup] = []
    edge_counter = 0

    def add_edge(source_id: str, source_role: str, target_id: str,
                 target_role: str, relationship: str, order: int = 0) -> None:
        nonlocal edge_counter
        edge_counter += 1
        edges.append(LoopGraphEdge(
            f"edge:{edge_counter}",
            LoopGraphEndpoint(source_id, source_role),
            LoopGraphEndpoint(target_id, target_role), relationship, order))

    def add_vertex(vertex_id: str, *, profile_id: str, input_roles: tuple,
                   output_roles: tuple, mode: str = "deterministic",
                   purpose: str = "component", operation_ref: str = "",
                   params: dict | None = None,
                   definition: LoopDefinition | None = None) -> str:
        selected_definition = definition or make_solution_loop_definition(
            graph_id=spec.solution_id, vertex_id=vertex_id,
            profile_id=profile_id, input_roles=input_roles,
            output_roles=output_roles, selected_mode=mode,
            operation_ref=operation_ref, parameters=params, purpose=purpose,
            delegated_modes=spec.permitted_loop_modes)
        vertices.append(vertex_from_definition(
            vertex_id, selected_definition, selected_mode=mode,
            purpose=purpose, operation_ref=operation_ref,
            parameters=params))
        return vertex_id

    def outer_roles(current: SolutionSpec) -> tuple[str, str]:
        if current.loops:
            return current.loops[0].input_role, current.loops[-1].output_role
        if current.members:
            return outer_roles(current.members[0])
        return "solution.value/v1", "solution.value/v1"

    def add_group(current: SolutionSpec, prefix: str, *,
                  parent_controller: str = "",
                  parent_dispatch_role: str = "", member_order: int = 0
                  ) -> str:
        group_id = f"{prefix}.group"
        controller_id = f"{prefix}.controller"
        input_role, output_role = outer_roles(current)
        controller_profile = (
            "solution.pipeline" if current.loops else
            "solution.router_fallback" if current.ensemble in (
                "ordered_fallback", "gating_router") else
            "solution.ensemble")
        add_vertex(
            controller_id, profile_id=controller_profile,
            input_roles=(input_role,),
            output_roles=tuple(dict.fromkeys((input_role, output_role))),
            purpose="controller", params={
                "logical_solution_id": current.solution_id,
                "max_members": current.max_members,
            })
        if parent_controller:
            add_edge(parent_controller, parent_dispatch_role, controller_id,
                     input_role, "spawned_by", member_order)

        stages: list[LoopGraphStage] = []
        member_ids: list[str] = []
        route_vertex_id = ""
        evaluator_ids: list[str] = []
        if current.loops:
            source_id, source_role = controller_id, input_role
            for stage_index, loop_spec in enumerate(current.loops):
                stage_base = f"{prefix}.stage{stage_index + 1}"
                attempt_ids: list[str] = []
                operations = (loop_spec.operation,) + tuple(
                    loop_spec.fallback_operations)
                fallback_definitions = tuple(loop_spec.fallback_definitions)
                definitions = ((loop_spec.definition,)
                               + fallback_definitions
                               + (None,) * (len(loop_spec.fallback_operations)
                                           - len(fallback_definitions)))
                router_id = ""
                if len(operations) > 1:
                    router_id = f"{stage_base}.router"
                    add_vertex(
                        router_id, profile_id="solution.router_fallback",
                        input_roles=(loop_spec.input_role,),
                        output_roles=tuple(dict.fromkeys((
                            loop_spec.input_role, loop_spec.output_role))),
                        purpose="fallback_router")
                    add_edge(source_id, source_role, router_id,
                             loop_spec.input_role, "connected_from")
                    source_id, source_role = router_id, loop_spec.input_role
                for attempt_index, (operation, definition) in enumerate(
                        zip(operations, definitions)):
                    vertex_id = (f"{stage_base}.attempt{attempt_index + 1}"
                                 if len(operations) > 1 else
                                 f"{stage_base}.component")
                    add_vertex(
                        vertex_id, profile_id="solution.atomic_component",
                        input_roles=(loop_spec.input_role,),
                        output_roles=(loop_spec.output_role,),
                        mode=loop_spec.mode, purpose="component",
                        operation_ref=operation, params=loop_spec.params,
                        definition=definition)
                    add_edge(source_id, source_role, vertex_id,
                             loop_spec.input_role,
                             "spawned_by" if router_id else "connected_from",
                             attempt_index)
                    attempt_ids.append(vertex_id)
                stage = LoopGraphStage(
                    _safe_id(loop_spec.loop_id), tuple(attempt_ids), router_id)
                stages.append(stage)
                source_id, source_role = stage.result_vertex_id, loop_spec.output_role
        else:
            for member_index, member in enumerate(current.members):
                member_prefix = (f"{prefix}.member{member_index + 1}_"
                                 f"{_safe_id(member.solution_id)}")
                member_ids.append(add_group(
                    member, member_prefix, parent_controller=controller_id,
                    parent_dispatch_role=input_role,
                    member_order=member_index))
            if current.ensemble == "gating_router":
                route_vertex_id = f"{prefix}.route_selector"
                add_vertex(
                    route_vertex_id, profile_id="solution.router_fallback",
                    input_roles=(input_role,),
                    output_roles=("solution.member_id/v1",),
                    purpose="route_selector", operation_ref="router")
                add_edge(controller_id, input_role, route_vertex_id,
                         input_role, "connected_from")
            if current.ensemble == "select_best":
                for member_index, group_id_value in enumerate(member_ids):
                    member_group = next(
                        item for item in groups if item.group_id == group_id_value)
                    member_controller = member_group.controller_vertex_id
                    member_definition = next(
                        item.definition for item in vertices
                        if item.vertex_id == member_controller)
                    assert member_definition is not None
                    member_output = member_definition.contract.output_roles[-1]
                    evaluator_id = f"{prefix}.evaluator{member_index + 1}"
                    add_vertex(
                        evaluator_id, profile_id="solution.validator",
                        input_roles=(member_output,),
                        output_roles=("solution.evaluation_score/v1",),
                        purpose="validator", operation_ref="evaluator")
                    add_edge(member_controller, member_output, evaluator_id,
                             member_output, "connected_from", member_index)
                    evaluator_ids.append(evaluator_id)
        groups.append(LoopGraphGroup(
            group_id, controller_id, tuple(stages), tuple(member_ids),
            current.ensemble, tuple(current.weights), route_vertex_id,
            tuple(evaluator_ids)))
        return group_id

    starting_group = add_group(spec, "solution")
    starting = next(item for item in groups
                    if item.group_id == starting_group)
    starting_definition = next(
        item.definition for item in vertices
        if item.vertex_id == starting.controller_vertex_id)
    assert starting_definition is not None
    input_role = starting_definition.contract.input_roles[0]
    output_role = starting_definition.contract.output_roles[-1]
    output_vertex_id = (starting.stages[-1].result_vertex_id
                        if starting.stages
                        else starting.controller_vertex_id)
    graph = LoopGraphDefinition(
        graph_id=spec.solution_id, version="1.0.0",
        permitted_vertex_modes=tuple(spec.permitted_loop_modes),
        input_ports=(LoopGraphInputPort(
            "input", input_role,
            (LoopGraphEndpoint(starting.controller_vertex_id, input_role),)),),
        output_ports=(LoopGraphOutputPort(
            "output", output_role,
            LoopGraphEndpoint(output_vertex_id, output_role)),),
        vertices=tuple(vertices), edges=tuple(edges), groups=tuple(groups),
        starting_group_id=starting_group)
    return graph


def _project_group(graph: LoopGraphDefinition, group_id: str) -> dict:
    group = graph.group(group_id)
    controller = graph.vertex(group.controller_vertex_id)
    loops = []
    for stage in group.stages:
        attempts = [graph.vertex(item) for item in stage.attempt_vertex_ids]
        primary = attempts[0]
        definition = primary.resolved_definition(None)
        loops.append(SolutionLoopSpec(
            stage.stage_id, primary.operation_ref, primary.selected_mode,
            tuple(item.operation_ref for item in attempts[1:]),
            primary.parameters.to_dict(), definition.contract.input_roles[0],
            definition.contract.output_roles[-1], definition,
            tuple(item.resolved_definition(None) for item in attempts[1:]),
            primary.vertex_id,
            tuple(item.vertex_id for item in attempts[1:]),
            stage.router_vertex_id,
            (graph.resolved_definition(stage.router_vertex_id)
             if stage.router_vertex_id else None)))
    members = tuple(
        SolutionSpec.from_graph(graph, group_id=item)
        for item in group.member_group_ids)
    return {"solution_id": controller.parameters.to_dict().get(
                "logical_solution_id", group.group_id),
            "max_members": controller.parameters.to_dict().get(
                "max_members", 5), "loops": tuple(loops),
            "members": members, "ensemble": group.combination,
            "weights": group.weights}


def _apply_graph_projection(spec: SolutionSpec) -> None:
    assert spec.graph is not None
    projected = _project_group(spec.graph, spec.group_id)
    spec.solution_id = (spec.graph.graph_id if spec.group_id
                        == spec.graph.starting_group_id
                        else projected["solution_id"])
    spec.permitted_loop_modes = spec.graph.permitted_vertex_modes
    spec.loops = projected["loops"]
    spec.members = projected["members"]
    spec.ensemble = projected["ensemble"]
    spec.weights = projected["weights"]
    spec.max_members = projected["max_members"]


def _spec_roles(spec: SolutionSpec) -> tuple[str, str]:
    group = spec.graph.group(spec.group_id) if spec.graph else None
    if group is None:
        return "solution.value/v1", "solution.value/v1"
    definition = spec.graph.resolved_definition(group.controller_vertex_id)
    return (definition.contract.input_roles[0],
            definition.contract.output_roles[-1])


def _runtime_depth(spec: SolutionSpec) -> int:
    """Maximum descendant depth below this spec's own Solution envelope."""
    if spec.loops:
        return max((2 if loop.fallback_operations else 1
                    for loop in spec.loops), default=0)
    return 1 + max((_runtime_depth(member) for member in spec.members),
                   default=0)


def _adapter_violations(spec: SolutionSpec, path: str = "") -> list[str]:
    """Report execution-adapter coverage separately from declaration shape."""
    here = f"{path}/{spec.solution_id}" if path else spec.solution_id
    violations = [
        f"{here}/{loop.loop_id}: the in-process Canvas adapter supports "
        f"deterministic execution only; declared mode {loop.mode!r} needs a "
        "separate execution adapter"
        for loop in spec.loops if loop.mode != "deterministic"
    ]
    for member in spec.members:
        violations.extend(_adapter_violations(member, here))
    return violations


def _runtime_identity(loop: Loop) -> dict:
    identity = loop.identity
    relationship = loop.relationship
    if identity is None or identity.role != LoopRole.SOLUTION:
        raise SolutionError(
            f"runtime loop {loop.loop_id} is not bound to the Solution role")
    return {
        "runtime_loop_id": loop.loop_id,
        **identity.to_dict(), **relationship.to_dict(),
    }


def _new_solution_loop(*, definition: LoopDefinition, goal: str,
                       ledger: LoopLedger,
                       parent: "Loop | None", max_depth: int,
                       solution_id: str, logical_loop_id: str,
                       relationship: LoopRelationship, trace: list) -> Loop:
    profile_id = definition.role_profile_id
    try:
        if parent is not None and parent.depth + 1 > max_depth:
            raise LoopError(f"max Loop depth {max_depth} reached")
        if parent is not None and relationship.kind is \
                LoopRelationshipKind.SPAWNED_BY:
            loop = parent.spawn(goal, definition=definition,
                                relationship=relationship)
        else:
            if parent is None:
                context = LoopRuntimeContext.compatibility(
                    capabilities=definition.required_capabilities,
                    permissions=definition.permissions,
                    executor_modes=definition.installed_executor_modes)
                depth = 0
            elif parent.runtime_context.internal.compatibility_composition:
                context = LoopRuntimeContext.compatibility(
                    capabilities=definition.required_capabilities,
                    permissions=definition.permissions,
                    executor_modes=definition.installed_executor_modes)
                depth = parent.depth + 1
            else:
                context = parent.runtime_context.derive(
                    capabilities=definition.required_capabilities,
                    permissions=definition.permissions,
                    executor_modes=definition.installed_executor_modes)
                depth = parent.depth + 1
            request = LoopStartRequest(
                goal, definition, relationship, context, ledger)
            loop = Loop(request, parent=parent, depth=depth)
    except (LoopError, ValueError) as exc:
        raise SolutionError(
            f"cannot initialize {profile_id} for {logical_loop_id!r}: "
            f"{exc}") from exc
    identity = _runtime_identity(loop)
    loop.ledger.record(
        loop_id=loop.loop_id, event="solution.loop.started",
        solution=solution_id, logical_loop_id=logical_loop_id,
        mode=definition.contract.runtime_mode,
        **{k: v for k, v in identity.items()
                                 if k != "runtime_loop_id"})
    trace.append({"runtime_event": "started", "solution": solution_id,
                  "logical_loop_id": logical_loop_id,
                  "mode": definition.contract.runtime_mode, **identity})
    return loop


def _complete_solution_loop(loop: Loop, *, solution_id: str,
                            logical_loop_id: str, status: str,
                            trace: list) -> None:
    if not loop.is_terminal:
        loop.cancel(f"{logical_loop_id} did not reach a terminal transition")
    result = loop.result()
    identity = _runtime_identity(loop)
    loop.ledger.record(
        loop_id=loop.loop_id, event="solution.loop.completed",
        solution=solution_id, logical_loop_id=logical_loop_id,
        status=status, terminal_reason=result.stopped,
        actual_modes=tuple(result.mode_counts),
        **{k: v for k, v in identity.items() if k != "runtime_loop_id"})
    trace.append({"runtime_event": "completed", "solution": solution_id,
                  "logical_loop_id": logical_loop_id, "status": status,
                  "terminal_reason": result.stopped,
                  "actual_modes": tuple(result.mode_counts), **identity})


def _run_envelope(loop: Loop, *, solution_id: str, logical_loop_id: str,
                  action_step: str, body, trace: list):
    """Run one body through the already-bound canonical Loop runtime."""
    holder: dict = {}

    def handler(active: Loop, step: str, context: dict) -> StepOutcome:
        if step != action_step:
            confidence = (0.0 if active.config.exit_condition == "accepted_success"
                          else 0.9)
            return StepOutcome(output=f"{step}:ready", mode="deterministic",
                               confidence=confidence)
        try:
            holder["value"] = body(active)
            return StepOutcome(output=f"{step}:done", mode="deterministic",
                               confidence=0.95)
        except Exception as exc:  # noqa: BLE001 - terminate before surfacing
            holder["error"] = exc
            active.cancel(f"{logical_loop_id}: {type(exc).__name__}")
            return StepOutcome(output=f"{step}:failed:{type(exc).__name__}",
                               mode="deterministic", confidence=0.0,
                               failed=True)

    try:
        loop.run(handler=handler, max_steps=len(loop.steps()) + 1)
    except Exception as exc:  # noqa: BLE001 - closure is mandatory
        if not loop.is_terminal:
            loop.cancel(f"{logical_loop_id}: runtime failure")
        _complete_solution_loop(
            loop, solution_id=solution_id,
            logical_loop_id=logical_loop_id, status="failed", trace=trace)
        raise SolutionError(
            f"solution loop {logical_loop_id}: runtime failed") from exc
    if "error" in holder:
        _complete_solution_loop(
            loop, solution_id=solution_id,
            logical_loop_id=logical_loop_id, status="failed", trace=trace)
        error = holder["error"]
        if isinstance(error, SolutionError):
            raise error
        raise SolutionError(
            f"solution loop {logical_loop_id}: "
            f"{type(error).__name__}: {error}") from error
    loop.ledger.record(loop_id=loop.loop_id, event="solution_finalized",
                       solution=solution_id,
                       logical_loop_id=logical_loop_id)
    _complete_solution_loop(
        loop, solution_id=solution_id,
        logical_loop_id=logical_loop_id, status="done", trace=trace)
    return holder.get("value")


def _run_atomic_operation(*, owner: Loop, solution_id: str,
                          logical_loop_id: str, operation: str, value,
                          params: dict, input_role: str, output_role: str,
                          definition: LoopDefinition,
                          registry: dict, trace: list, max_depth: int,
                          pass_params: bool = True,
                          relationship: "LoopRelationship | None" = None
                          ) -> dict:
    relationship = relationship or LoopRelationship.connected_from(
        (owner.loop_id,))
    loop = _new_solution_loop(
        definition=definition,
        goal=f"run {operation} for solution {solution_id}",
        ledger=owner.ledger, parent=owner, max_depth=max_depth,
        solution_id=solution_id, logical_loop_id=logical_loop_id,
        relationship=relationship, trace=trace)

    def invoke(active: Loop):
        from ..loop.delegation_runtime import LoopPortValue
        callable_ = registry.get(operation)
        if not callable(callable_):
            trace.append({"solution_loop": logical_loop_id,
                          "missing_operation": operation,
                          **_runtime_identity(active)})
            raise SolutionError(
                f"solution loop {logical_loop_id}: operation {operation!r} "
                "does not resolve to a callable")
        identity = _runtime_identity(active)
        actual_input = value
        if isinstance(value, LoopPortValue):
            if value.role != input_role:
                raise SolutionError(
                    f"solution loop {logical_loop_id}: input value role "
                    f"{value.role!r} does not match {input_role!r}")
            actual_input = value.value
        active.ledger.record(
            loop_id=active.loop_id, event="tool_invocation_started",
            surface="solution_registry", operation=operation,
            solution=solution_id, logical_loop_id=logical_loop_id)
        try:
            output = (callable_(actual_input, dict(params)) if pass_params
                      else callable_(actual_input))
        except Exception as exc:  # noqa: BLE001 - evidence before propagation
            active.ledger.record(
                loop_id=active.loop_id, event="tool_invocation_failed",
                surface="solution_registry", operation=operation,
                solution=solution_id, logical_loop_id=logical_loop_id,
                error_type=type(exc).__name__)
            raise
        active.ledger.record(
            loop_id=active.loop_id, event="tool_invocation_completed",
            surface="solution_registry", operation=operation,
            solution=solution_id, logical_loop_id=logical_loop_id)
        if isinstance(output, LoopPortValue):
            if output.role != output_role:
                raise SolutionError(
                    f"solution loop {logical_loop_id}: output value role "
                    f"{output.role!r} does not match {output_role!r}")
            output = output.value
        trace.append({"solution_loop": logical_loop_id,
                      "operation": operation,
                      "mode": definition.contract.runtime_mode,
                      "component_loop_id": active.loop_id,
                      "input_role": input_role, "output_role": output_role,
                      "input_type": type(actual_input).__name__,
                      "output_type": type(output).__name__, **identity})
        return output

    output = _run_envelope(
        loop, solution_id=solution_id, logical_loop_id=logical_loop_id,
        action_step=("verify_survivors" if definition.role_profile_id
                     == "solution.validator"
                     else "act"),
        body=invoke, trace=trace)
    return {"value": output, "loop_id": loop.loop_id,
            "identity": _runtime_identity(loop)}


def _run_solution_node(node: SolutionLoopSpec, value, *, owner: Loop,
                       solution_id: str, registry: dict, trace: list,
                       max_depth: int, connected_from_loop_ids: tuple[str, ...]
                       ) -> dict:
    operations = (node.operation,) + tuple(node.fallback_operations)
    definitions = (node.definition,) + tuple(node.fallback_definitions)
    if any(definition is None for definition in definitions):
        raise SolutionError(
            f"solution stage {node.loop_id!r} has an unresolved definition")
    if not node.fallback_operations:
        assert node.definition is not None
        return _run_atomic_operation(
            owner=owner, solution_id=solution_id,
            logical_loop_id=node.loop_id, operation=node.operation,
            value=value, params=node.params, input_role=node.input_role,
            output_role=node.output_role, definition=node.definition,
            registry=registry, trace=trace,
            max_depth=max_depth,
            relationship=LoopRelationship.connected_from(
                connected_from_loop_ids))

    if node.router_definition is None:
        raise SolutionError(
            f"fallback stage {node.loop_id!r} has no explicit Router Loop")
    router = _new_solution_loop(
        definition=node.router_definition,
        goal=f"route fallbacks for {node.loop_id}",
        ledger=owner.ledger, parent=owner, max_depth=max_depth,
        solution_id=solution_id, logical_loop_id=f"{node.loop_id}:fallback",
        relationship=LoopRelationship.spawned_by(owner.loop_id), trace=trace)

    def route(active: Loop):
        errors = []
        for index, (operation, definition) in enumerate(zip(
                operations, definitions)):
            assert definition is not None
            attempt_id = f"{node.loop_id}:{operation}:{index}"
            try:
                attempt = _run_atomic_operation(
                    owner=active, solution_id=solution_id,
                    logical_loop_id=attempt_id, operation=operation,
                    value=value, params=node.params,
                    input_role=node.input_role,
                    output_role=node.output_role, definition=definition,
                    registry=registry,
                    trace=trace, max_depth=max_depth,
                    relationship=LoopRelationship.spawned_by(active.loop_id))
            except SolutionError as exc:
                errors.append(f"{operation}: {exc}")
                trace.append({"solution_loop": node.loop_id,
                              "operation": operation, "failed": str(exc),
                              "attempt_index": index,
                              **_runtime_identity(active)})
                continue
            trace.append({"solution_loop": node.loop_id,
                          "operation": operation,
                          "component_loop_id": attempt["loop_id"],
                          "router_loop_id": active.loop_id,
                          "used_fallback": index > 0,
                          "served_by": index, "mode": "deterministic",
                          "input_role": node.input_role,
                          "output_role": node.output_role,
                          **_runtime_identity(active)})
            return attempt["value"]
        raise SolutionError(
            f"solution loop {node.loop_id}: every declared operation failed: "
            f"{errors}")

    output = _run_envelope(
        router, solution_id=solution_id,
        logical_loop_id=f"{node.loop_id}:fallback", action_step="act",
        body=route, trace=trace)
    return {"value": output, "loop_id": router.loop_id,
            "identity": _runtime_identity(router)}


def _run_members(spec: SolutionSpec, registry: dict, inputs, *, owner: Loop,
                 trace: list, max_depth: int, allow_extended: bool):
    assert spec.graph is not None
    group = spec.graph.group(spec.group_id)
    if spec.ensemble in _EXTENDED and not allow_extended:
        raise SolutionError(
            f"{spec.ensemble} is an extended strategy; compile the spec and "
            "execute via solution_compiler.run_compiled")

    if spec.ensemble == "gating_router":
        route_vertex = spec.graph.vertex(group.route_vertex_id)
        route_definition = route_vertex.resolved_definition(None)
        routed = _run_atomic_operation(
            owner=owner, solution_id=spec.solution_id,
            logical_loop_id=f"{spec.solution_id}:router",
            operation="router", value=inputs, params={},
            input_role=_spec_roles(spec)[0],
            output_role="solution.member_id/v1",
            definition=route_definition, registry=registry,
            trace=trace, max_depth=max_depth, pass_params=False,
            relationship=LoopRelationship.connected_from((owner.loop_id,)))
        target = routed["value"]
        for member in spec.members:
            if member.solution_id == target:
                trace.append({"solution": spec.solution_id,
                              "routed_to": target,
                              **_runtime_identity(owner)})
                executed = _execute_spec(
                    member, registry, inputs, parent=owner, trace=trace,
                    max_depth=max_depth, allow_extended=allow_extended,
                    relationship=LoopRelationship.spawned_by(owner.loop_id))
                return executed["value"]
        raise SolutionError(
            f"router chose {target!r} but no member has that id")

    outputs, errors = [], []
    for index, member in enumerate(spec.members):
        try:
            executed = _execute_spec(
                member, registry, inputs, parent=owner, trace=trace,
                max_depth=max_depth, allow_extended=allow_extended,
                relationship=LoopRelationship.spawned_by(owner.loop_id))
        except SolutionError as exc:
            errors.append(f"{member.solution_id}: {exc}")
            trace.append({"solution": spec.solution_id,
                          "member_failed": member.solution_id,
                          "error": str(exc), **_runtime_identity(owner)})
            continue
        outputs.append((index, member, executed))
        if spec.ensemble == "ordered_fallback":
            trace.append({"solution": spec.solution_id,
                          "served_by": member.solution_id,
                          **_runtime_identity(owner)})
            return executed["value"]
    if not outputs:
        raise SolutionError(f"every member failed: {errors}")
    if spec.ensemble == "select_best":
        scored = []
        for index, member, executed in outputs:
            output = executed["value"]
            evaluator_vertex = spec.graph.vertex(
                group.evaluator_vertex_ids[index])
            evaluated = _run_atomic_operation(
                owner=owner, solution_id=spec.solution_id,
                logical_loop_id=f"{member.solution_id}:evaluate",
                operation="evaluator", value=output, params={},
                input_role=_spec_roles(member)[1],
                output_role="solution.evaluation_score/v1",
                definition=evaluator_vertex.resolved_definition(None),
                registry=registry, trace=trace, max_depth=max_depth,
                pass_params=False,
                relationship=LoopRelationship.connected_from(
                    (executed["loop_id"],)))
            scored.append((evaluated["value"], member.solution_id, output))
            trace.append({"solution": spec.solution_id,
                          "member": member.solution_id,
                          "score": evaluated["value"],
                          **_runtime_identity(owner)})
        best = max(scored)
        trace.append({"solution": spec.solution_id, "selected": best[1],
                      **_runtime_identity(owner)})
        return best[2]
    values = [executed["value"] for _, _, executed in outputs]
    if spec.ensemble == "average":
        return sum(values) / len(values)
    if spec.ensemble == "weighted_average":
        weighted = [(spec.weights[index], executed["value"])
                    for index, _, executed in outputs]
        return (sum(weight * output for weight, output in weighted)
                / sum(weight for weight, _ in weighted))
    if spec.ensemble == "vote":
        return max(set(values), key=values.count)
    return values[0]


def _execute_spec(spec: SolutionSpec, registry: dict, inputs, *,
                  parent: "Loop | None", trace: list, max_depth: int,
                  allow_extended: bool, relationship: LoopRelationship):
    assert spec.graph is not None
    group = spec.graph.group(spec.group_id)
    controller_definition = spec.graph.resolved_definition(
        group.controller_vertex_id)
    loop = _new_solution_loop(
        definition=controller_definition,
        goal=f"execute solution {spec.solution_id}",
        ledger=(parent.ledger if parent is not None else trace._ledger
                if hasattr(trace, "_ledger") else LoopLedger()),
        parent=parent, max_depth=max_depth, solution_id=spec.solution_id,
        logical_loop_id=spec.solution_id, relationship=relationship,
        trace=trace)

    def execute(active: Loop):
        if spec.members:
            return _run_members(
                spec, registry, inputs, owner=active, trace=trace,
                max_depth=max_depth, allow_extended=allow_extended)
        value = inputs
        upstream = (active.loop_id,)
        for node in spec.loops:
            executed = _run_solution_node(
                node, value, owner=active, solution_id=spec.solution_id,
                registry=registry, trace=trace, max_depth=max_depth,
                connected_from_loop_ids=upstream)
            value = executed["value"]
            upstream = (executed["loop_id"],)
        return value

    output = _run_envelope(
        loop, solution_id=spec.solution_id,
        logical_loop_id=spec.solution_id, action_step="act",
        body=execute, trace=trace)
    return {"value": output, "loop_id": loop.loop_id,
            "identity": _runtime_identity(loop)}


def _run_solution_runtime(spec: SolutionSpec, registry: dict, inputs, *,
                          trace: "list | None" = None,
                          ledger: "LoopLedger | None" = None,
                          parent: "Loop | None" = None,
                          allow_extended: bool = False):
    report = spec.validate()
    if not report["valid"]:
        raise SolutionError("; ".join(report["violations"]))
    adapter_violations = _adapter_violations(spec)
    if adapter_violations:
        raise SolutionError("; ".join(adapter_violations))
    if parent is not None and ledger is not None and ledger is not parent.ledger:
        raise SolutionError(
            "parent and ledger do not share one timeline; Canvas execution "
            "refuses to split its history")
    selected_ledger = parent.ledger if parent is not None else (
        ledger if ledger is not None else LoopLedger())
    required_depth = ((parent.depth + 1 if parent is not None else 0)
                      + _runtime_depth(spec))
    if parent is not None and parent.config.max_depth < required_depth:
        raise SolutionError(
            f"solution {spec.solution_id!r} needs absolute Loop depth "
            f"{required_depth}, but parent {parent.loop_id} allows only "
            f"{parent.config.max_depth}; explicit Solution nesting will not "
            "be flattened")
    max_depth = (parent.config.max_depth if parent is not None
                 else max(3, required_depth))
    tr = trace if trace is not None else []

    # A plain list cannot carry the selected ledger. Pass it explicitly into
    # the starting initializer, then recurse only through spawning ledgers.
    assert spec.graph is not None
    group = spec.graph.group(spec.group_id)
    controller_definition = spec.graph.resolved_definition(
        group.controller_vertex_id)
    starting_relationship = (LoopRelationship.spawned_by(parent.loop_id)
                             if parent is not None
                             else LoopRelationship.starting())
    starting = _new_solution_loop(
        definition=controller_definition,
        goal=f"execute solution {spec.solution_id}",
        ledger=selected_ledger, parent=parent, max_depth=max_depth,
        solution_id=spec.solution_id, logical_loop_id=spec.solution_id,
        relationship=starting_relationship, trace=tr)

    def execute(active: Loop):
        if spec.members:
            return _run_members(
                spec, registry, inputs, owner=active, trace=tr,
                max_depth=max_depth, allow_extended=allow_extended)
        value = inputs
        upstream = (active.loop_id,)
        for node in spec.loops:
            executed = _run_solution_node(
                node, value, owner=active, solution_id=spec.solution_id,
                registry=registry, trace=tr, max_depth=max_depth,
                connected_from_loop_ids=upstream)
            value = executed["value"]
            upstream = (executed["loop_id"],)
        return value

    return _run_envelope(
        starting, solution_id=spec.solution_id,
        logical_loop_id=spec.solution_id, action_step="act",
        body=execute, trace=tr)


def run_solution(spec: SolutionSpec, registry: dict, inputs,
                 *, trace: "list | None" = None, ledger=None,
                 parent: "Loop | None" = None):
    """Run one Canvas through role-correct Solution ``Loop`` envelopes.

    Standalone execution creates a Starting Solution envelope. With ``parent``
    it creates a Spawned Solution envelope under that exact spawning Loop.
    Member solutions, components, routers, fallback attempts, and validators
    are Spawned Solution loops on the same ledger. The in-process adapter is
    deterministic-only;
    unsupported leaf modes fail in preflight before any operation callable.
    """
    return _run_solution_runtime(
        spec, registry, inputs, trace=trace, ledger=ledger, parent=parent)


def self_test() -> dict:
    """Run the focused checks from the mapped companion module."""
    from .solution_canvas_checks import solution_canvas_self_test_checks
    return solution_canvas_self_test_checks()
