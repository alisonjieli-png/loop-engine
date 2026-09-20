"""Port values, dependency scheduling, and identity projections for Solution execution.

These are internal mechanics used by canonical Solution Loops. They do not
create another runtime, event history, or source of graph authority.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..loop.loop_role import LoopRelationship, LoopRole
from ..loop.recursive_loop import Loop
from .solution_graph import LoopGraphDefinition
from .solution_model_port import preflight_model_execution


class SolutionError(ValueError):
    """A solution spec that cannot be honestly executed as declared."""


@dataclass
class _SolutionGraphValues:
    """Run-local values and observed producers for the declared graph ports."""

    graph: LoopGraphDefinition
    inputs: object
    values: dict = field(default_factory=dict)
    runtime_ids: dict = field(default_factory=dict)
    external: dict = field(default_factory=dict)

    def __post_init__(self):
        ports = self.graph.input_ports
        if len(ports) == 1:
            supplied = {ports[0].name: self.inputs}
        elif (not isinstance(self.inputs, dict)
              or set(self.inputs) != {port.name for port in ports}):
            raise SolutionError("multiple graph inputs require their exact port-name mapping")
        else:
            supplied = self.inputs
        self.external = {
            (target.vertex_id, target.port_role): supplied[port.name]
            for port in ports for target in port.targets}

    def incoming(self, vertex_id):
        return tuple(edge for edge in self.graph.edges
                     if edge.target.vertex_id == vertex_id)

    def available(self, vertex_id, *, internal_sources=()):
        definition = self.graph.resolved_definition(vertex_id)
        for role in definition.contract.input_roles:
            if (vertex_id, role) in self.external:
                continue
            matches = [edge for edge in self.incoming(vertex_id)
                       if edge.target.port_role == role]
            if len(matches) != 1:
                return False
            source = matches[0].source
            if (source.vertex_id not in internal_sources
                    and (source.vertex_id, source.port_role) not in self.values):
                return False
        return True

    def input_for(self, vertex_id):
        definition = self.graph.resolved_definition(vertex_id)
        values = {}
        for role in definition.contract.input_roles:
            key = (vertex_id, role)
            if key in self.external:
                values[role] = self.external[key]
                continue
            matches = [edge for edge in self.incoming(vertex_id)
                       if edge.target.port_role == role]
            if len(matches) != 1:
                raise SolutionError(f"graph input {key!r} does not have one binding")
            source = matches[0].source
            source_key = (source.vertex_id, source.port_role)
            if source_key not in self.values:
                raise SolutionError(f"graph input {key!r} has no completed source {source_key!r}")
            values[role] = self.values[source_key]
        from ..loop.delegation_runtime import LoopPortValue
        for role, value in values.items():
            if isinstance(value, LoopPortValue):
                if value.role != role:
                    raise SolutionError(f"input value role {value.role!r} does not match {role!r}")
                values[role] = value.value
        return next(iter(values.values())) if len(values) == 1 else values

    def input_bindings(self, vertex_id):
        external = [{"target_role": target.port_role, "external_port": port.name}
                    for port in self.graph.input_ports for target in port.targets
                    if target.vertex_id == vertex_id]
        edges = [{"target_role": edge.target.port_role,
                  "source_vertex_id": edge.source.vertex_id,
                  "source_role": edge.source.port_role,
                  "source_loop_id": self.runtime_ids.get(edge.source.vertex_id, "")}
                 for edge in self.incoming(vertex_id)]
        return tuple(external + edges)

    def connected_relationship(self, vertex_id):
        sources = tuple(dict.fromkeys(
            self.runtime_ids[edge.source.vertex_id]
            for edge in self.incoming(vertex_id)
            if edge.source.vertex_id in self.runtime_ids))
        return (LoopRelationship.connected_from(sources) if sources
                else LoopRelationship.starting())

    def begin_controller(self, vertex_id, value, loop_id):
        definition = self.graph.resolved_definition(vertex_id)
        roles = definition.contract.input_roles
        incoming = {roles[0]: value} if len(roles) == 1 else value
        if not isinstance(incoming, dict) or set(incoming) != set(roles):
            raise SolutionError("controller inputs do not match its declared ports")
        self.runtime_ids[vertex_id] = loop_id
        for role, item in incoming.items():
            if role in definition.contract.output_roles:
                self.values[(vertex_id, role)] = item

    def publish(self, vertex_id, value, loop_id, *, controller=False):
        roles = self.graph.resolved_definition(vertex_id).contract.output_roles
        if controller or len(roles) == 1:
            published = {roles[-1]: value}
        elif isinstance(value, dict) and set(value) == set(roles):
            published = value
        else:
            raise SolutionError("multiple operation outputs require their exact role mapping")
        self.runtime_ids[vertex_id] = loop_id
        self.values.update({(vertex_id, role): item for role, item in published.items()})

    def public_output(self):
        values = {}
        for port in self.graph.output_ports:
            key = (port.source.vertex_id, port.source.port_role)
            if key not in self.values:
                raise SolutionError(f"declared graph output {port.name!r} is unavailable")
            values[port.name] = self.values[key]
        return next(iter(values.values())) if len(values) == 1 else values


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


def _model_execution_preflight(spec, model_execution) -> list[str]:
    """Fail-closed preflight for model-mode leaves, before any callable.

    A Solution leaf declares deterministic, hybrid, or non_deterministic like
    every Loop. Model modes are legitimate declarations: they execute only
    under the run's explicit, budgeted ``ModelExecution`` authority. A run
    that declares model-mode leaves without that authority refuses here,
    before any operation callable.
    """
    return preflight_model_execution(spec, model_execution)


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


def _run_pipeline(spec, registry, *, owner, trace, max_depth, model_execution,
                  graph_values):
    """Schedule ready stages; grouping controls alternatives, edges bind values."""
    from .solution_canvas import _run_solution_node

    group = spec.graph.group(spec.group_id)
    pending = list(zip(group.stages, spec.loops))
    completed = {}
    while pending:
        ready = next((index for index, (stage, _node) in enumerate(pending)
                      if all(graph_values.available(vertex_id,
                          internal_sources=((stage.router_vertex_id,)
                                            if stage.router_vertex_id else ()))
                          for vertex_id in (*stage.attempt_vertex_ids,
                              *((stage.router_vertex_id,) if stage.router_vertex_id else ())))), None)
        if ready is None:
            raise SolutionError("graph stages have unavailable or unsupported dependency bindings")
        stage, node = pending.pop(ready)
        completed[stage.stage_id] = _run_solution_node(
            node, None, owner=owner, solution_id=spec.solution_id,
            registry=registry, trace=trace, max_depth=max_depth,
            connected_from_loop_ids=(owner.loop_id,), model_execution=model_execution,
            graph_values=graph_values)
    return completed[group.stages[-1].stage_id]["value"]
