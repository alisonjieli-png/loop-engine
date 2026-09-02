"""The authoritative, immutable graph for executable Solution Loops.

Every executable vertex is one versioned ``LoopDefinition``.  Edges only
describe typed value flow and operational relationships.  They never contain
callables, adapters, scripts, or other hidden work.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any, Iterable

from ..loop.loop_contract import LoopContract
from ..loop.loop_definition import (ConfigurationFacts, LoopDefinition,
                                    LoopDefinitionRef)
from ..loop.loop_profile_catalog import LoopProfileRef
from ..loop.loop_profile_ontology import resolve_profile


GRAPH_RECORD_TYPE = "loop_graph_definition/v1"
GRAPH_EDGE_RELATIONSHIPS = ("connected_from", "spawned_by")
GRAPH_COMBINATIONS = (
    "single", "average", "vote", "weighted_average", "ordered_fallback",
    "select_best", "gating_router",
)
GRAPH_VERTEX_PURPOSES = (
    "controller", "component", "adapter", "fallback_router",
    "route_selector", "validator",
)
_SEMVER = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,255}$")
_MODE_TO_EXECUTION = {
    "deterministic": "code_only",
    "hybrid": "hybrid",
    "non_deterministic": "model_led",
}
_HIDDEN_WORK_KEYS = frozenset({
    "adapter", "adapter_ref", "adapter_loop_ref", "callable", "code",
    "command", "executor", "function", "operation", "operation_ref",
    "script", "tool",
})


class LoopGraphError(ValueError):
    """A Loop graph is malformed, unresolved, changed, or not executable."""


def _identifier(label: str, value: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise LoopGraphError(
            f"{label} must use letters, numbers, dot, underscore, colon, or "
            "hyphen")
    return value


def _names(label: str, values: Iterable[str], *, allow_empty=False
           ) -> tuple[str, ...]:
    result = tuple(values)
    if any(not isinstance(value, str) or not value.strip() for value in result):
        raise LoopGraphError(f"{label} must contain non-empty strings")
    if len(result) != len(set(result)):
        raise LoopGraphError(f"{label} cannot contain duplicates")
    if not allow_empty and not result:
        raise LoopGraphError(f"{label} cannot be empty")
    return result


def _definition_segment(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9_]+", "_", value.lower()).strip("_") or "loop"
    return cleaned if cleaned[0].isalpha() else f"v_{cleaned}"


@dataclass(frozen=True)
class LoopGraphEndpoint:
    """One exact port on one Loop vertex."""

    vertex_id: str
    port_role: str

    def __post_init__(self) -> None:
        _identifier("vertex_id", self.vertex_id)
        if not isinstance(self.port_role, str) or not self.port_role.strip():
            raise LoopGraphError("a graph endpoint needs a port role")

    def to_dict(self) -> dict[str, str]:
        return {"vertex_id": self.vertex_id, "port_role": self.port_role}

    @classmethod
    def from_dict(cls, value: dict) -> "LoopGraphEndpoint":
        if not isinstance(value, dict) or set(value) != {
                "vertex_id", "port_role"}:
            raise LoopGraphError("LoopGraphEndpoint has an invalid shape")
        return cls(**value)


@dataclass(frozen=True)
class LoopGraphInputPort:
    """One external typed input, optionally fanned out to several Loops."""

    name: str
    role: str
    targets: tuple[LoopGraphEndpoint, ...]

    def __post_init__(self) -> None:
        _identifier("input port name", self.name)
        if not isinstance(self.role, str) or not self.role.strip():
            raise LoopGraphError("an external input needs a role")
        targets = tuple(self.targets)
        if not targets or any(not isinstance(item, LoopGraphEndpoint)
                              for item in targets):
            raise LoopGraphError(
                "an external input needs LoopGraphEndpoint targets")
        if len(targets) != len(set(targets)):
            raise LoopGraphError("external input targets cannot repeat")
        object.__setattr__(self, "targets", targets)

    def to_dict(self) -> dict:
        return {"name": self.name, "role": self.role,
                "targets": [item.to_dict() for item in self.targets]}

    @classmethod
    def from_dict(cls, value: dict) -> "LoopGraphInputPort":
        if not isinstance(value, dict) or set(value) != {
                "name", "role", "targets"}:
            raise LoopGraphError("LoopGraphInputPort has an invalid shape")
        return cls(value["name"], value["role"], tuple(
            LoopGraphEndpoint.from_dict(item) for item in value["targets"]))


@dataclass(frozen=True)
class LoopGraphOutputPort:
    """One external typed output produced by one exact Loop port."""

    name: str
    role: str
    source: LoopGraphEndpoint

    def __post_init__(self) -> None:
        _identifier("output port name", self.name)
        if not isinstance(self.role, str) or not self.role.strip():
            raise LoopGraphError("an external output needs a role")
        if not isinstance(self.source, LoopGraphEndpoint):
            raise LoopGraphError("an external output needs one endpoint")

    def to_dict(self) -> dict:
        return {"name": self.name, "role": self.role,
                "source": self.source.to_dict()}

    @classmethod
    def from_dict(cls, value: dict) -> "LoopGraphOutputPort":
        if not isinstance(value, dict) or set(value) != {
                "name", "role", "source"}:
            raise LoopGraphError("LoopGraphOutputPort has an invalid shape")
        return cls(value["name"], value["role"],
                   LoopGraphEndpoint.from_dict(value["source"]))


@dataclass(frozen=True)
class LoopDefinitionRegistry:
    """Exact resolver for graph vertices that carry a definition reference."""

    definitions: tuple[LoopDefinition, ...] = ()

    def __post_init__(self) -> None:
        definitions = tuple(self.definitions)
        if any(not isinstance(item, LoopDefinition) for item in definitions):
            raise LoopGraphError(
                "a definition registry accepts LoopDefinition objects")
        seen: dict[tuple[str, str], str] = {}
        for definition in definitions:
            key = (definition.definition_id, definition.version)
            previous = seen.get(key)
            if previous is not None and previous != definition.content_digest:
                raise LoopGraphError(
                    f"definition {key} has two different content digests")
            seen[key] = definition.content_digest
        object.__setattr__(self, "definitions", definitions)

    def resolve(self, ref: LoopDefinitionRef) -> LoopDefinition:
        if not isinstance(ref, LoopDefinitionRef):
            raise LoopGraphError("definition lookup needs a LoopDefinitionRef")
        exact = [item for item in self.definitions if item.ref == ref]
        if len(exact) != 1:
            raise LoopGraphError(
                f"definition {ref.definition_id}@{ref.version} with digest "
                f"{ref.content_digest} is not resolved exactly once")
        return exact[0]


@dataclass(frozen=True)
class LoopGraphVertexRecord:
    """One executable graph vertex, always an exact versioned Loop."""

    vertex_id: str
    definition_ref: LoopDefinitionRef
    definition: LoopDefinition | None
    selected_mode: str
    purpose: str
    operation_ref: str = ""
    parameters: ConfigurationFacts = field(default_factory=ConfigurationFacts)

    def __post_init__(self) -> None:
        _identifier("vertex_id", self.vertex_id)
        if not isinstance(self.definition_ref, LoopDefinitionRef):
            raise LoopGraphError(
                "a graph vertex needs an exact LoopDefinitionRef")
        if self.definition is not None and not isinstance(
                self.definition, LoopDefinition):
            raise LoopGraphError(
                "a graph vertex definition must be LoopDefinition or None")
        if self.selected_mode not in _MODE_TO_EXECUTION:
            raise LoopGraphError(
                f"selected_mode must be one of {tuple(_MODE_TO_EXECUTION)}")
        if self.purpose not in GRAPH_VERTEX_PURPOSES:
            raise LoopGraphError(
                f"purpose must be one of {GRAPH_VERTEX_PURPOSES}")
        if not isinstance(self.operation_ref, str):
            raise LoopGraphError("operation_ref must be a string")
        if (self.purpose in {"component", "adapter", "route_selector",
                             "validator"}
                and not self.operation_ref.strip()):
            raise LoopGraphError(
                f"{self.purpose} vertex {self.vertex_id!r} needs operation_ref")
        if not isinstance(self.parameters, ConfigurationFacts):
            raise LoopGraphError("parameters must use ConfigurationFacts")

    def resolved_definition(self, registry: LoopDefinitionRegistry | None
                            ) -> LoopDefinition:
        definition = self.definition
        if definition is None:
            if registry is None:
                raise LoopGraphError(
                    f"vertex {self.vertex_id!r} has an unresolved definition")
            definition = registry.resolve(self.definition_ref)
        if definition.ref != self.definition_ref:
            raise LoopGraphError(
                f"vertex {self.vertex_id!r} definition digest does not match "
                "its exact reference")
        return definition

    def to_dict(self) -> dict:
        return {
            "vertex_id": self.vertex_id,
            "definition_ref": self.definition_ref.to_dict(),
            "definition": (
                self.definition.to_dict() if self.definition is not None
                else None),
            "selected_mode": self.selected_mode,
            "purpose": self.purpose,
            "operation_ref": self.operation_ref,
            "parameters": self.parameters.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: dict) -> "LoopGraphVertexRecord":
        required = {
            "vertex_id", "definition_ref", "definition", "selected_mode",
            "purpose", "operation_ref", "parameters",
        }
        if not isinstance(value, dict) or set(value) != required:
            raise LoopGraphError("LoopGraphVertexRecord has an invalid shape")
        definition = value["definition"]
        return cls(
            vertex_id=value["vertex_id"],
            definition_ref=LoopDefinitionRef.from_dict(
                value["definition_ref"]),
            definition=(LoopDefinition.from_dict(definition)
                        if definition is not None else None),
            selected_mode=value["selected_mode"], purpose=value["purpose"],
            operation_ref=value["operation_ref"],
            parameters=ConfigurationFacts.from_mapping(value["parameters"]),
        )


@dataclass(frozen=True)
class LoopGraphEdge:
    """Typed data and relationship metadata; never an execution surface."""

    edge_id: str
    source: LoopGraphEndpoint
    target: LoopGraphEndpoint
    relationship: str = "connected_from"
    order: int = 0
    metadata: ConfigurationFacts = field(default_factory=ConfigurationFacts)

    def __post_init__(self) -> None:
        _identifier("edge_id", self.edge_id)
        if not isinstance(self.source, LoopGraphEndpoint) or not isinstance(
                self.target, LoopGraphEndpoint):
            raise LoopGraphError("an edge needs source and target endpoints")
        if self.relationship not in GRAPH_EDGE_RELATIONSHIPS:
            raise LoopGraphError(
                f"edge relationship must be one of {GRAPH_EDGE_RELATIONSHIPS}")
        if not isinstance(self.order, int) or self.order < 0:
            raise LoopGraphError("edge order must be a non-negative integer")
        if not isinstance(self.metadata, ConfigurationFacts):
            raise LoopGraphError("edge metadata must use ConfigurationFacts")
        hidden = sorted(set(self.metadata.to_dict()) & _HIDDEN_WORK_KEYS)
        if hidden:
            raise LoopGraphError(
                f"edge {self.edge_id!r} contains hidden work keys {hidden}; "
                "make that work an explicit Loop vertex")

    def to_dict(self) -> dict:
        return {
            "edge_id": self.edge_id, "source": self.source.to_dict(),
            "target": self.target.to_dict(),
            "relationship": self.relationship, "order": self.order,
            "metadata": self.metadata.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: dict) -> "LoopGraphEdge":
        required = {"edge_id", "source", "target", "relationship", "order",
                    "metadata"}
        if not isinstance(value, dict) or set(value) != required:
            raise LoopGraphError(
                "LoopGraphEdge has an invalid shape; an Adapter must be an "
                "explicit LoopGraphVertexRecord, never an edge field")
        return cls(
            edge_id=value["edge_id"],
            source=LoopGraphEndpoint.from_dict(value["source"]),
            target=LoopGraphEndpoint.from_dict(value["target"]),
            relationship=value["relationship"], order=value["order"],
            metadata=ConfigurationFacts.from_mapping(value["metadata"]),
        )


@dataclass(frozen=True)
class LoopGraphStage:
    """Graph-owned execution grouping for one primary and its fallbacks."""

    stage_id: str
    attempt_vertex_ids: tuple[str, ...]
    router_vertex_id: str = ""

    def __post_init__(self) -> None:
        _identifier("stage_id", self.stage_id)
        attempts = _names("attempt_vertex_ids", self.attempt_vertex_ids)
        for item in attempts:
            _identifier("attempt vertex ID", item)
        if self.router_vertex_id:
            _identifier("router_vertex_id", self.router_vertex_id)
        if len(attempts) > 1 and not self.router_vertex_id:
            raise LoopGraphError(
                "a stage with fallbacks needs an explicit Router Loop vertex")
        object.__setattr__(self, "attempt_vertex_ids", attempts)

    @property
    def result_vertex_id(self) -> str:
        return self.router_vertex_id or self.attempt_vertex_ids[0]

    def to_dict(self) -> dict:
        return {"stage_id": self.stage_id,
                "attempt_vertex_ids": list(self.attempt_vertex_ids),
                "router_vertex_id": self.router_vertex_id}

    @classmethod
    def from_dict(cls, value: dict) -> "LoopGraphStage":
        if not isinstance(value, dict) or set(value) != {
                "stage_id", "attempt_vertex_ids", "router_vertex_id"}:
            raise LoopGraphError("LoopGraphStage has an invalid shape")
        return cls(value["stage_id"], tuple(value["attempt_vertex_ids"]),
                   value["router_vertex_id"])


@dataclass(frozen=True)
class LoopGraphGroup:
    """One pipeline or ensemble controlled by an explicit Solution Loop."""

    group_id: str
    controller_vertex_id: str
    stages: tuple[LoopGraphStage, ...] = ()
    member_group_ids: tuple[str, ...] = ()
    combination: str = "single"
    weights: tuple[float, ...] = ()
    route_vertex_id: str = ""
    evaluator_vertex_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _identifier("group_id", self.group_id)
        _identifier("controller_vertex_id", self.controller_vertex_id)
        stages = tuple(self.stages)
        if any(not isinstance(item, LoopGraphStage) for item in stages):
            raise LoopGraphError("group stages must contain LoopGraphStage")
        members = _names(
            "member_group_ids", self.member_group_ids, allow_empty=True)
        evaluators = _names(
            "evaluator_vertex_ids", self.evaluator_vertex_ids,
            allow_empty=True)
        if bool(stages) == bool(members):
            raise LoopGraphError(
                "a graph group must contain stages or member groups, not both")
        if self.route_vertex_id:
            _identifier("route_vertex_id", self.route_vertex_id)
        if self.combination not in GRAPH_COMBINATIONS:
            raise LoopGraphError(
                f"combination must be one of {GRAPH_COMBINATIONS}")
        if stages and self.combination != "single":
            raise LoopGraphError("a pipeline stage group uses combination single")
        if members and self.combination != "single" and len(members) < 2:
            raise LoopGraphError(
                f"combination {self.combination!r} needs at least two members")
        if (self.combination == "weighted_average"
                and len(self.weights) != len(members)):
            raise LoopGraphError(
                "weighted_average needs one weight per member group")
        if self.combination == "gating_router" and not self.route_vertex_id:
            raise LoopGraphError("gating_router needs an explicit Router Loop")
        if (self.combination == "select_best"
                and len(evaluators) != len(members)):
            raise LoopGraphError(
                "select_best needs one explicit Validator Loop per member")
        object.__setattr__(self, "stages", stages)
        object.__setattr__(self, "member_group_ids", members)
        object.__setattr__(self, "weights", tuple(self.weights))
        object.__setattr__(self, "evaluator_vertex_ids", evaluators)

    def to_dict(self) -> dict:
        return {
            "group_id": self.group_id,
            "controller_vertex_id": self.controller_vertex_id,
            "stages": [item.to_dict() for item in self.stages],
            "member_group_ids": list(self.member_group_ids),
            "combination": self.combination,
            "weights": list(self.weights),
            "route_vertex_id": self.route_vertex_id,
            "evaluator_vertex_ids": list(self.evaluator_vertex_ids),
        }

    @classmethod
    def from_dict(cls, value: dict) -> "LoopGraphGroup":
        required = {
            "group_id", "controller_vertex_id", "stages",
            "member_group_ids", "combination", "weights", "route_vertex_id",
            "evaluator_vertex_ids",
        }
        if not isinstance(value, dict) or set(value) != required:
            raise LoopGraphError("LoopGraphGroup has an invalid shape")
        return cls(
            value["group_id"], value["controller_vertex_id"],
            tuple(LoopGraphStage.from_dict(item) for item in value["stages"]),
            tuple(value["member_group_ids"]), value["combination"],
            tuple(value["weights"]), value["route_vertex_id"],
            tuple(value["evaluator_vertex_ids"]),
        )


@dataclass(frozen=True)
class LoopGraphValidation:
    valid: bool
    violations: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"valid": self.valid, "violations": list(self.violations)}


@dataclass(frozen=True)
class LoopGraphDefinition:
    """One digest-bound source of truth for a complete executable Loop DAG."""

    graph_id: str
    version: str
    permitted_vertex_modes: tuple[str, ...]
    input_ports: tuple[LoopGraphInputPort, ...]
    output_ports: tuple[LoopGraphOutputPort, ...]
    vertices: tuple[LoopGraphVertexRecord, ...]
    edges: tuple[LoopGraphEdge, ...]
    groups: tuple[LoopGraphGroup, ...]
    starting_group_id: str

    def __post_init__(self) -> None:
        _identifier("graph_id", self.graph_id)
        if not isinstance(self.version, str) or not _SEMVER.fullmatch(
                self.version):
            raise LoopGraphError("graph version must use MAJOR.MINOR.PATCH")
        modes = _names("permitted_vertex_modes", self.permitted_vertex_modes)
        if any(mode not in _MODE_TO_EXECUTION for mode in modes):
            raise LoopGraphError(
                f"permitted vertex modes must use {tuple(_MODE_TO_EXECUTION)}")
        typed_fields = (
            ("input_ports", LoopGraphInputPort),
            ("output_ports", LoopGraphOutputPort),
            ("vertices", LoopGraphVertexRecord), ("edges", LoopGraphEdge),
            ("groups", LoopGraphGroup),
        )
        for name, expected in typed_fields:
            values = tuple(getattr(self, name))
            if not values or any(not isinstance(item, expected)
                                 for item in values):
                raise LoopGraphError(f"{name} must contain {expected.__name__}")
            object.__setattr__(self, name, values)
        object.__setattr__(self, "permitted_vertex_modes", modes)
        _identifier("starting_group_id", self.starting_group_id)

    def vertex(self, vertex_id: str) -> LoopGraphVertexRecord:
        matches = [item for item in self.vertices
                   if item.vertex_id == vertex_id]
        if len(matches) != 1:
            raise LoopGraphError(
                f"vertex {vertex_id!r} does not resolve exactly once")
        return matches[0]

    def group(self, group_id: str) -> LoopGraphGroup:
        matches = [item for item in self.groups if item.group_id == group_id]
        if len(matches) != 1:
            raise LoopGraphError(
                f"group {group_id!r} does not resolve exactly once")
        return matches[0]

    def resolved_definition(self, vertex_id: str,
                            registry: LoopDefinitionRegistry | None = None
                            ) -> LoopDefinition:
        return self.vertex(vertex_id).resolved_definition(registry)

    def validate(self, registry: LoopDefinitionRegistry | None = None
                 ) -> LoopGraphValidation:
        from .solution_graph_validation import validate_loop_graph
        return validate_loop_graph(self, registry)
    def assert_executable(self, registry: LoopDefinitionRegistry | None = None
                          ) -> None:
        report = self.validate(registry)
        if not report.valid:
            raise LoopGraphError("; ".join(report.violations))

    def _canonical_body(self) -> dict:
        return {
            "record_type": GRAPH_RECORD_TYPE,
            "graph_id": self.graph_id, "version": self.version,
            "permitted_vertex_modes": list(self.permitted_vertex_modes),
            "input_ports": [item.to_dict() for item in self.input_ports],
            "output_ports": [item.to_dict() for item in self.output_ports],
            "vertices": [item.to_dict() for item in self.vertices],
            "edges": [item.to_dict() for item in self.edges],
            "groups": [item.to_dict() for item in self.groups],
            "starting_group_id": self.starting_group_id,
        }

    @property
    def canonical_json(self) -> str:
        return json.dumps(self._canonical_body(), sort_keys=True,
                          separators=(",", ":"), ensure_ascii=False)

    @property
    def content_digest(self) -> str:
        return hashlib.sha256(self.canonical_json.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict:
        value = self._canonical_body()
        value["content_digest"] = self.content_digest
        return value

    @classmethod
    def from_dict(cls, value: dict, *,
                  registry: LoopDefinitionRegistry | None = None
                  ) -> "LoopGraphDefinition":
        required = {
            "record_type", "graph_id", "version", "permitted_vertex_modes",
            "input_ports", "output_ports", "vertices", "edges", "groups",
            "starting_group_id", "content_digest",
        }
        if not isinstance(value, dict) or set(value) != required:
            raise LoopGraphError("LoopGraphDefinition has an invalid shape")
        if value["record_type"] != GRAPH_RECORD_TYPE:
            raise LoopGraphError("unsupported Loop graph record type")
        graph = cls(
            value["graph_id"], value["version"],
            tuple(value["permitted_vertex_modes"]),
            tuple(LoopGraphInputPort.from_dict(item)
                  for item in value["input_ports"]),
            tuple(LoopGraphOutputPort.from_dict(item)
                  for item in value["output_ports"]),
            tuple(LoopGraphVertexRecord.from_dict(item)
                  for item in value["vertices"]),
            tuple(LoopGraphEdge.from_dict(item) for item in value["edges"]),
            tuple(LoopGraphGroup.from_dict(item) for item in value["groups"]),
            value["starting_group_id"],
        )
        if value["content_digest"] != graph.content_digest:
            raise LoopGraphError(
                "Loop graph content digest does not match its content")
        graph.assert_executable(registry)
        return graph

    def required_operation_refs(self) -> tuple[str, ...]:
        return tuple(sorted({item.operation_ref for item in self.vertices
                             if item.operation_ref}))


@dataclass(frozen=True)
class SolutionLoopDefinitionRequest:
    """One typed request for generating one exact Solution Loop definition."""

    graph_id: str
    vertex_id: str
    profile_id: str
    input_roles: tuple[str, ...]
    output_roles: tuple[str, ...]
    selected_mode: str = "deterministic"
    operation_ref: str = ""
    parameters: ConfigurationFacts = field(default_factory=ConfigurationFacts)
    purpose: str = "component"
    delegated_modes: tuple[str, ...] = ("deterministic",)
    version: str = "1.0.0"

    def __post_init__(self) -> None:
        object.__setattr__(self, "input_roles", tuple(self.input_roles))
        object.__setattr__(self, "output_roles", tuple(self.output_roles))
        object.__setattr__(self, "delegated_modes", tuple(self.delegated_modes))
        if not isinstance(self.parameters, ConfigurationFacts):
            raise LoopGraphError("definition parameters need ConfigurationFacts")


def make_solution_loop_definition(
        request: SolutionLoopDefinitionRequest) -> LoopDefinition:
    """Build one exact definition for a generated Solution graph vertex.

    Every leaf declares all three modes like every Loop.  Hybrid and
    non_deterministic leaves execute through the governed model-invocation
    port at run time; a run without explicit model authority refuses in
    preflight before any operation callable.
    """
    if not isinstance(request, SolutionLoopDefinitionRequest):
        raise LoopGraphError(
            "make_solution_loop_definition needs its typed request object")
    graph_id, vertex_id = request.graph_id, request.vertex_id
    profile_id, selected_mode = request.profile_id, request.selected_mode
    operation_ref, purpose = request.operation_ref, request.purpose
    parameters = request.parameters.to_dict()
    delegated_modes, version = request.delegated_modes, request.version
    resolved = resolve_profile(LoopProfileRef(profile_id))
    profile_modes = tuple(resolved.allowed_modes)
    # The spec's permitted-mode policy restricts what this definition
    # supports: profile allows, the graph policy decides. A deterministic-
    # only spec yields deterministic-only definitions even though the
    # profile itself also allows model modes.
    supported_modes = tuple(
        mode for mode in profile_modes if mode in delegated_modes)
    definition_mode = (selected_mode if selected_mode in supported_modes
                       else "deterministic")
    execution_mode = _MODE_TO_EXECUTION[definition_mode]
    inputs = tuple(request.input_roles)
    outputs = tuple(dict.fromkeys(request.output_roles))
    custom_step = "verify_survivors" if purpose == "validator" else "act"
    execution_delegated_modes = tuple(dict.fromkeys((
        *delegated_modes,
        *(("deterministic", "non_deterministic")
          if selected_mode in ("hybrid", "non_deterministic") else ()),
    )))
    facts = {
        "framework": "custom", "logical_kind": "execution",
        "replay_guarantee": "event_equivalent",
        "allowable_modes": list(supported_modes),
        "preferred_modes": [definition_mode],
        "delegated_modes": list(execution_delegated_modes),
        "power": "light", "llm_thinking_power": "",
        "custom_steps": [custom_step], "max_depth": 32,
        "loop_condition": "steps_remain",
        "exit_condition": "accepted_success",
        "success_confidence_min": 0.5,
        "graph_id": graph_id, "vertex_id": vertex_id, "purpose": purpose,
        "operation_ref": operation_ref,
        "parameters": dict(parameters or {}),
    }
    definition_id = ".".join((
        "solution", "graph", _definition_segment(graph_id),
        _definition_segment(vertex_id)))
    return LoopDefinition(
        definition_id=definition_id, version=version,
        role_profile_id=profile_id,
        role_profile_version=resolved.spec.version,
        contract=LoopContract(
            name=f"{graph_id}:{vertex_id}", execution_mode=execution_mode,
            input_roles=inputs, output_roles=outputs, effects=("pure",),
            role="solution"),
        configuration_facts=ConfigurationFacts.from_mapping(facts),
        supported_modes=supported_modes,
        installed_executor_modes=supported_modes,
        step_profile=resolved.step_template_id,
        loop_condition="steps_remain", exit_condition="accepted_success",
        effects=("pure",), required_capabilities=resolved.required_capabilities,
    )


def vertex_from_definition(
        vertex_id: str, definition: LoopDefinition, *, selected_mode: str,
        purpose: str, operation_ref: str = "", parameters: dict | None = None
        ) -> LoopGraphVertexRecord:
    """Bind a complete Loop definition and its exact reference once."""
    return LoopGraphVertexRecord(
        vertex_id, definition.ref, definition, selected_mode, purpose,
        operation_ref, ConfigurationFacts.from_mapping(parameters))


@dataclass(frozen=True)
class AdapterLoopRunRequest:
    """All inputs for executing one explicit Adapter Loop vertex."""

    graph_id: str
    adapter_vertex: LoopGraphVertexRecord
    value: Any
    registry: dict = field(repr=False, compare=False)
    parent: Any = field(default=None, repr=False, compare=False)
    event_log: Any = field(default=None, repr=False, compare=False)
    trace: list | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        _identifier("graph_id", self.graph_id)
        if (not isinstance(self.adapter_vertex, LoopGraphVertexRecord)
                or self.adapter_vertex.purpose != "adapter"):
            raise LoopGraphError(
                "adapter_vertex must be an explicit Adapter Loop vertex")
        if not isinstance(self.registry, dict):
            raise LoopGraphError("adapter registry must be a mapping")


def run_adapter_loop(request: AdapterLoopRunRequest):
    """Execute a typed conversion through its exact Adapter Loop definition."""
    if not isinstance(request, AdapterLoopRunRequest):
        raise LoopGraphError("run_adapter_loop needs AdapterLoopRunRequest")
    adapter = request.adapter_vertex
    definition = adapter.resolved_definition(None)
    if (len(definition.contract.input_roles) != 1
            or len(definition.contract.output_roles) != 1):
        raise LoopGraphError(
            "the current Adapter runner needs one input and one output role")
    input_role = definition.contract.input_roles[0]
    output_role = definition.contract.output_roles[0]
    controller_id = "adapter.controller"
    controller_definition = make_solution_loop_definition(
        SolutionLoopDefinitionRequest(
            request.graph_id, controller_id, "solution.pipeline",
            (input_role,), tuple(dict.fromkeys((input_role, output_role))),
            delegated_modes=(adapter.selected_mode,)))
    controller = vertex_from_definition(
        controller_id, controller_definition, selected_mode="deterministic",
        purpose="controller")
    edge = LoopGraphEdge(
        "adapter.connection", LoopGraphEndpoint(controller_id, input_role),
        LoopGraphEndpoint(adapter.vertex_id, input_role))
    group = LoopGraphGroup(
        "adapter.group", controller_id,
        (LoopGraphStage("adapter.stage", (adapter.vertex_id,)),))
    graph = LoopGraphDefinition(
        request.graph_id, "1.0.0", (adapter.selected_mode,),
        (LoopGraphInputPort(
            "input", input_role,
            (LoopGraphEndpoint(controller_id, input_role),)),),
        (LoopGraphOutputPort(
            "output", output_role,
            LoopGraphEndpoint(adapter.vertex_id, output_role)),),
        (controller, adapter), (edge,), (group,), group.group_id)
    graph.assert_executable()
    from .solution_canvas import SolutionSpec, run_solution
    return run_solution(
        SolutionSpec.from_graph(graph), request.registry, request.value,
        trace=request.trace, ledger=request.event_log, parent=request.parent)


def self_test() -> dict:
    from .solution_graph_checks import solution_graph_self_test_checks
    return solution_graph_self_test_checks()
