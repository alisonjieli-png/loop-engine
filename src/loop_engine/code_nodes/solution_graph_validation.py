"""Validation implementation for serialized Loop graph definitions.

The split keeps graph data types small while applying exact definitions,
typed-port, DAG, mode, and execution-plan checks in one place.
"""
from __future__ import annotations

from ..loop.loop_definition import LoopDefinitionError


def validate_loop_graph(graph, registry=None):
    from .solution_graph import LoopGraphError, LoopGraphValidation
    from .solution_operation_identity import SolutionOperationIdentity
    violations: list[str] = []
    vertex_ids = [item.vertex_id for item in graph.vertices]
    edge_ids = [item.edge_id for item in graph.edges]
    group_ids = [item.group_id for item in graph.groups]
    for label, values in (("vertex", vertex_ids), ("edge", edge_ids),
                          ("group", group_ids),
                          ("external input", [port.name for port in graph.input_ports]),
                          ("external output", [port.name for port in graph.output_ports])):
        if len(values) != len(set(values)):
            violations.append(f"{label} IDs must be unique")
    by_vertex = {item.vertex_id: item for item in graph.vertices}
    by_group = {item.group_id: item for item in graph.groups}
    if graph.starting_group_id not in by_group:
        violations.append("starting_group_id does not name one group")

    definition_versions: dict[tuple[str, str], str] = {}
    for vertex in graph.vertices:
        try:
            definition = vertex.resolved_definition(registry)
        except (LoopGraphError, LoopDefinitionError) as exc:
            violations.append(str(exc))
            continue
        key = (definition.definition_id, definition.version)
        prior = definition_versions.get(key)
        if prior is not None and prior != definition.content_digest:
            violations.append(
                f"definition {key} has different digests inside one graph")
        definition_versions[key] = definition.content_digest
        if definition.identity.role.value != "solution":
            violations.append(
                f"vertex {vertex.vertex_id!r} is not a Solution Loop")
        if vertex.selected_mode not in definition.supported_modes:
            violations.append(
                f"vertex {vertex.vertex_id!r} selected mode "
                f"{vertex.selected_mode!r} is not supported by its exact "
                "Loop definition")
        if vertex.selected_mode not in definition.installed_executor_modes:
            violations.append(
                f"vertex {vertex.vertex_id!r} has no installed "
                f"{vertex.selected_mode!r} Solution executor")
        if definition.contract.runtime_mode != vertex.selected_mode:
            violations.append(
                f"vertex {vertex.vertex_id!r} selected mode conflicts with "
                "its Loop contract")
        if vertex.selected_mode not in graph.permitted_vertex_modes:
            violations.append(
                f"vertex {vertex.vertex_id!r} selected mode is outside the "
                "graph policy")
        facts = definition.configuration_facts.to_dict()
        if "operation_identity" in facts:
            try:
                implementation = SolutionOperationIdentity.from_dict(facts["operation_identity"])
                if implementation.operation_ref != vertex.operation_ref:
                    violations.append(f"vertex {vertex.vertex_id!r} implementation names another operation")
            except LoopGraphError as exc:
                violations.append(str(exc))
        if vertex.operation_ref and facts.get(
                "operation_ref") != vertex.operation_ref:
            violations.append(
                f"vertex {vertex.vertex_id!r} operation_ref is not bound "
                "inside its exact Loop definition")
        if facts.get("parameters", {}) != vertex.parameters.to_dict():
            violations.append(
                f"vertex {vertex.vertex_id!r} parameters are not bound "
                "inside its exact Loop definition")
        if vertex.purpose == "adapter" and not vertex.operation_ref:
            violations.append(
                f"Adapter Loop {vertex.vertex_id!r} has no operation")

    bound_inputs: set[tuple[str, str]] = set()
    for port in graph.input_ports:
        for target in port.targets:
            vertex = by_vertex.get(target.vertex_id)
            if vertex is None:
                violations.append(
                    f"external input {port.name!r} targets a missing vertex")
                continue
            try:
                definition = vertex.resolved_definition(registry)
            except (LoopGraphError, LoopDefinitionError):
                continue
            if port.role != target.port_role:
                violations.append(
                    f"external input {port.name!r} role does not match its "
                    "target endpoint")
            if target.port_role not in definition.contract.input_roles:
                violations.append(
                    f"external input {port.name!r} targets undeclared port "
                    f"{target.port_role!r}")
            target_key = (target.vertex_id, target.port_role)
            if target_key in bound_inputs:
                violations.append(f"input {target_key} is bound more than once")
            bound_inputs.add(target_key)

    adjacency = {item: set() for item in vertex_ids}
    indegree = {item: 0 for item in vertex_ids}
    for edge in graph.edges:
        source = by_vertex.get(edge.source.vertex_id)
        target = by_vertex.get(edge.target.vertex_id)
        if source is None or target is None:
            violations.append(f"edge {edge.edge_id!r} names a missing vertex")
            continue
        try:
            source_definition = source.resolved_definition(registry)
            target_definition = target.resolved_definition(registry)
        except (LoopGraphError, LoopDefinitionError):
            continue
        if edge.source.port_role not in source_definition.contract.output_roles:
            violations.append(
                f"edge {edge.edge_id!r} names missing source port "
                f"{edge.source.port_role!r}")
        if edge.target.port_role not in target_definition.contract.input_roles:
            violations.append(
                f"edge {edge.edge_id!r} names missing target port "
                f"{edge.target.port_role!r}")
        if edge.source.port_role != edge.target.port_role:
            violations.append(
                f"edge {edge.edge_id!r} changes port roles; insert an "
                "explicit Adapter Loop vertex")
        target_key = (edge.target.vertex_id, edge.target.port_role)
        if target_key in bound_inputs:
            violations.append(f"input {target_key} is bound more than once")
        bound_inputs.add(target_key)
        if edge.target.vertex_id not in adjacency[edge.source.vertex_id]:
            adjacency[edge.source.vertex_id].add(edge.target.vertex_id)
            indegree[edge.target.vertex_id] += 1

    for vertex in graph.vertices:
        try:
            definition = vertex.resolved_definition(registry)
        except (LoopGraphError, LoopDefinitionError):
            continue
        for role in definition.contract.input_roles:
            if (vertex.vertex_id, role) not in bound_inputs:
                violations.append(
                    f"vertex {vertex.vertex_id!r} input port {role!r} is "
                    "not bound")

    queue = [item for item, degree in indegree.items() if degree == 0]
    visited: list[str] = []
    while queue:
        current = queue.pop(0)
        visited.append(current)
        for target in sorted(adjacency[current]):
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    if len(visited) != len(vertex_ids):
        violations.append("Loop graph contains a cycle")

    for port in graph.output_ports:
        vertex = by_vertex.get(port.source.vertex_id)
        if vertex is None:
            violations.append(
                f"external output {port.name!r} names a missing vertex")
            continue
        try:
            definition = vertex.resolved_definition(registry)
        except (LoopGraphError, LoopDefinitionError):
            continue
        if port.role != port.source.port_role:
            violations.append(
                f"external output {port.name!r} role does not match source")
        if port.source.port_role not in definition.contract.output_roles:
            violations.append(
                f"external output {port.name!r} names an undeclared port")

    referenced_groups = {graph.starting_group_id}
    referenced_vertices: set[str] = set()
    for group in graph.groups:
        referenced_vertices.add(group.controller_vertex_id)
        referenced_groups.update(group.member_group_ids)
        for stage in group.stages:
            referenced_vertices.update(stage.attempt_vertex_ids)
            if stage.router_vertex_id:
                referenced_vertices.add(stage.router_vertex_id)
        if group.route_vertex_id:
            referenced_vertices.add(group.route_vertex_id)
        referenced_vertices.update(group.evaluator_vertex_ids)
    missing_groups = sorted(referenced_groups - set(group_ids))
    extra_vertices = sorted(set(vertex_ids) - referenced_vertices)
    missing_vertices = sorted(referenced_vertices - set(vertex_ids))
    if missing_groups:
        violations.append(f"execution groups are unresolved {missing_groups}")
    if extra_vertices:
        violations.append(
            f"vertices are outside the graph-owned execution plan "
            f"{extra_vertices}")
    if missing_vertices:
        violations.append(
            f"execution plan names missing vertices {missing_vertices}")
    if not violations:
        violations.extend(_execution_topology_violations(graph, by_vertex, by_group))
    return LoopGraphValidation(not violations, tuple(violations))


def _execution_topology_violations(graph, by_vertex, by_group):
    """Admit dependency graphs supported by the grouped execution protocol.

    Pipeline stages may branch, join, reorder, or use external inputs. Group
    records retain ownership of conditional fallbacks and ensemble members.
    Dataflow across those control boundaries must use their controller result.
    """
    violations = []
    ownership, stages, members_of, evaluator_member = {}, {}, {}, {}
    conditional_attempts = set()
    for group in graph.groups:
        own = [group.controller_vertex_id, *group.evaluator_vertex_ids]
        if group.route_vertex_id:
            own.append(group.route_vertex_id)
        stage_names = [stage.stage_id for stage in group.stages]
        if len(stage_names) != len(set(stage_names)):
            violations.append(f"group {group.group_id!r} repeats stage IDs")
        for stage in group.stages:
            own.extend(stage.attempt_vertex_ids)
            if stage.router_vertex_id:
                own.append(stage.router_vertex_id)
                conditional_attempts.update(stage.attempt_vertex_ids)
            for vertex_id in (*stage.attempt_vertex_ids,
                              *((stage.router_vertex_id,) if stage.router_vertex_id else ())):
                stages[vertex_id] = stage
        for vertex_id in own:
            if vertex_id in ownership:
                violations.append(f"vertex {vertex_id!r} has multiple execution owners")
            ownership[vertex_id] = group.group_id
        for member_id in group.member_group_ids:
            if member_id in members_of:
                violations.append(f"group {member_id!r} has multiple execution owners")
            members_of[member_id] = group.group_id
        for index, evaluator in enumerate(group.evaluator_vertex_ids):
            if index < len(group.member_group_ids):
                evaluator_member[evaluator] = by_group[group.member_group_ids[index]].controller_vertex_id
    for group_id in by_group:
        seen, current = set(), group_id
        while current in members_of:
            if current in seen:
                violations.append("execution group ownership contains a cycle")
                break
            seen.add(current)
            current = members_of[current]
        else:
            if current != graph.starting_group_id:
                violations.append(f"group {group_id!r} is outside the starting execution tree")
    for edge in graph.edges:
        source, target = edge.source.vertex_id, edge.target.vertex_id
        source_group = by_group[ownership[source]]
        target_group = by_group[ownership[target]]
        allowed = False
        if source_group.group_id == target_group.group_id:
            if source == source_group.controller_vertex_id:
                definition = by_vertex[source].resolved_definition(None)
                allowed = (edge.source.port_role in definition.contract.input_roles
                           and (target in stages or target == source_group.route_vertex_id))
            elif source in stages and target in stages:
                producer, consumer = stages[source], stages[target]
                allowed = ((producer is not consumer and source == producer.result_vertex_id)
                           or (producer is consumer and source == producer.router_vertex_id
                               and target in producer.attempt_vertex_ids))
        elif (source == source_group.controller_vertex_id
              and target == target_group.controller_vertex_id
              and target_group.group_id in source_group.member_group_ids):
            definition = by_vertex[source].resolved_definition(None)
            allowed = edge.source.port_role in definition.contract.input_roles
        elif evaluator_member.get(target) == source:
            allowed = True
        if not allowed:
            violations.append(f"edge {edge.edge_id!r} uses an unsupported execution-control topology")
    for port in graph.output_ports:
        if port.source.vertex_id in conditional_attempts:
            violations.append(f"output {port.name!r} must bind the selected fallback router result")
    for group in graph.groups:
        pending = {stage.stage_id: set() for stage in group.stages}
        for edge in graph.edges:
            source, target = edge.source.vertex_id, edge.target.vertex_id
            if (ownership[source] == group.group_id == ownership[target]
                    and source in stages and target in stages
                    and stages[source] is not stages[target]):
                pending[stages[target].stage_id].add(stages[source].stage_id)
        while pending:
            ready = {name for name, dependencies in pending.items() if not dependencies}
            if not ready:
                violations.append(f"group {group.group_id!r} has unsupported cyclic stage scheduling")
                break
            pending = {name: dependencies - ready for name, dependencies in pending.items()
                       if name not in ready}
    return violations
