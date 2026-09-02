"""Build a complete authoritative Loop graph from Solution projections.

This narrow migration layer turns established ``SolutionSpec`` callers into
explicit Loop vertices, typed edges, groups, and external ports.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..loop.loop_definition import ConfigurationFacts, LoopDefinition
from .solution_graph import (
    LoopGraphDefinition, LoopGraphEdge, LoopGraphEndpoint, LoopGraphGroup,
    LoopGraphInputPort, LoopGraphOutputPort, LoopGraphStage, LoopGraphVertexRecord,
    SolutionLoopDefinitionRequest, make_solution_loop_definition,
    vertex_from_definition,
)

if TYPE_CHECKING:
    from .solution_canvas import SolutionSpec

def _safe_id(value: str) -> str:
    import re
    cleaned = re.sub(r"[^A-Za-z0-9._:-]+", "_", value).strip("_")
    return cleaned or "loop"


def build_solution_graph(spec: SolutionSpec) -> LoopGraphDefinition:
    """Compile compatibility builders into one complete Loop graph."""
    vertices: list[LoopGraphVertexRecord] = []
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
                   delegated_modes: tuple | None = None,
                   definition: LoopDefinition | None = None) -> str:
        selected_definition = definition or make_solution_loop_definition(
            SolutionLoopDefinitionRequest(
                graph_id=spec.solution_id, vertex_id=vertex_id,
                profile_id=profile_id, input_roles=tuple(input_roles),
                output_roles=tuple(output_roles), selected_mode=mode,
                operation_ref=operation_ref,
                parameters=ConfigurationFacts.from_mapping(params),
                purpose=purpose,
                delegated_modes=tuple(delegated_modes
                                      if delegated_modes is not None else
                                      spec.permitted_loop_modes)))
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
            purpose="controller",
            delegated_modes=tuple(dict.fromkeys(
                ("deterministic", *current.permitted_loop_modes))),
            params={
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
                        purpose="fallback_router",
                        delegated_modes=tuple(dict.fromkeys(
                            ("deterministic", *current.permitted_loop_modes))))
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
        permitted_vertex_modes=tuple(dict.fromkeys(
            ("deterministic", *spec.permitted_loop_modes))),
        input_ports=(LoopGraphInputPort(
            "input", input_role,
            (LoopGraphEndpoint(starting.controller_vertex_id, input_role),)),),
        output_ports=(LoopGraphOutputPort(
            "output", output_role,
            LoopGraphEndpoint(output_vertex_id, output_role)),),
        vertices=tuple(vertices), edges=tuple(edges), groups=tuple(groups),
        starting_group_id=starting_group)
    return graph
