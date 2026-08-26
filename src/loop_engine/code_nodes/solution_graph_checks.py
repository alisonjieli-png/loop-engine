"""Adversarial checks for the authoritative Solution Loop graph.

These checks prove that incomplete, hidden, cyclic, or tampered graph work is
refused before execution and that an Adapter is a real Loop vertex.
"""
from __future__ import annotations

from dataclasses import replace

from ..loop.loop_definition import ConfigurationFacts, LoopDefinitionRef
from ..loop.canvas import SolutionLoopCandidate, TypeContract
from .solution_canvas import (SolutionError, SolutionLoopSpec, SolutionSpec,
                              run_solution)
from .solution_graph import (
    AdapterLoopRunRequest, LoopGraphEdge, LoopGraphEndpoint, LoopGraphError,
    LoopGraphVertexRecord, SolutionLoopDefinitionRequest,
    make_solution_loop_definition, run_adapter_loop, vertex_from_definition,
)


def solution_graph_self_test_checks() -> dict:
    results = []

    def check(name, passed, note=""):
        results.append({"name": name, "passed": bool(passed), "note": note})

    spec = SolutionSpec(
        "adversarial.graph", loops=(
            SolutionLoopSpec("first", "first"),
            SolutionLoopSpec("second", "second")))
    graph = spec.graph
    assert graph is not None

    fake_refused = False
    try:
        replace(graph, vertices=("not-a-loop",))
    except LoopGraphError:
        fake_refused = True
    check("fake_string_vertex_is_refused", fake_refused)

    unresolved_vertex = replace(graph.vertices[1], definition=None)
    unresolved = replace(
        graph, vertices=(graph.vertices[0], unresolved_vertex,
                         *graph.vertices[2:]))
    check("unresolved_definition_is_not_executable",
          not unresolved.validate().valid
          and any("unresolved definition" in item
                  for item in unresolved.validate().violations))

    mismatch_vertex = replace(
        graph.vertices[1], definition_ref=LoopDefinitionRef(
            graph.vertices[1].definition_ref.definition_id,
            graph.vertices[1].definition_ref.version, "0" * 64))
    mismatch = replace(
        graph, vertices=(graph.vertices[0], mismatch_vertex,
                         *graph.vertices[2:]))
    check("definition_digest_mismatch_is_refused",
          not mismatch.validate().valid
          and any("digest does not match" in item
                  for item in mismatch.validate().violations))

    hidden_adapter_refused = False
    try:
        LoopGraphEdge(
            "hidden-adapter", graph.edges[0].source, graph.edges[0].target,
            metadata=ConfigurationFacts.from_mapping(
                {"adapter_ref": "convert-in-secret"}))
    except LoopGraphError:
        hidden_adapter_refused = True
    check("edge_attached_adapter_is_refused", hidden_adapter_refused,
          "an Adapter must be an explicit Loop vertex")

    adapter_definition = make_solution_loop_definition(
        SolutionLoopDefinitionRequest(
            "adapter.test", "string_to_integer", "solution.atomic_component",
            ("text/v1",), ("integer/v1",), operation_ref="parse_integer",
            purpose="adapter"))
    adapter_vertex = vertex_from_definition(
        "string_to_integer", adapter_definition,
        selected_mode="deterministic", purpose="adapter",
        operation_ref="parse_integer")
    adapted = run_adapter_loop(AdapterLoopRunRequest(
        "adapter.test", adapter_vertex, "42",
        {"parse_integer": lambda value, params: int(value)}))
    check("the_adapter_executes_as_a_loop_not_an_edge_function",
          adapted == 42)

    last = graph.vertices[-1]
    first = graph.vertices[0]
    role = last.definition.contract.output_roles[-1]  # type: ignore[union-attr]
    cyclic_edge = LoopGraphEdge(
        "cycle", LoopGraphEndpoint(last.vertex_id, role),
        LoopGraphEndpoint(first.vertex_id, role))
    cyclic = replace(graph, edges=graph.edges + (cyclic_edge,))
    check("cycle_is_refused",
          any("cycle" in item for item in cyclic.validate().violations))

    missing_port_edge = replace(
        graph.edges[0], source=LoopGraphEndpoint(
            graph.edges[0].source.vertex_id, "missing.port/v1"))
    missing_port = replace(
        graph, edges=(missing_port_edge, *graph.edges[1:]))
    check("missing_port_is_refused",
          any("missing source port" in item
              for item in missing_port.validate().violations))

    original = graph.vertices[0].definition
    changed = graph.vertices[1].definition
    assert original is not None and changed is not None
    changed = replace(
        changed, definition_id=original.definition_id,
        version=original.version)
    duplicate_vertex = replace(
        graph.vertices[1], definition=changed, definition_ref=changed.ref)
    duplicate = replace(
        graph, vertices=(graph.vertices[0], duplicate_vertex,
                         *graph.vertices[2:]))
    check("same_definition_version_with_different_digest_is_refused",
          any("different digests" in item
              for item in duplicate.validate().violations))

    bare_callable_refused = False
    contract = TypeContract(("input/v1",), ("output/v1",))
    try:
        SolutionLoopCandidate(
            "bare", contract, "bare", None, lambda value: value)  # type: ignore[arg-type]
    except ValueError:
        bare_callable_refused = True
    check("canvas_bare_callable_is_refused", bare_callable_refused)

    semantic_calls = []
    semantic = SolutionSpec(
        "semantic.unavailable", loops=(SolutionLoopSpec(
            "semantic", "semantic", mode="hybrid"),))
    semantic_refused = False
    try:
        run_solution(
            semantic,
            {"semantic": lambda value, params: semantic_calls.append(value)},
            "input")
    except SolutionError as exc:
        semantic_refused = "no installed 'hybrid' Solution executor" in str(exc)
    check("semantic_mode_unavailable_is_refused_before_work",
          semantic_refused and not semantic_calls)

    passed = sum(1 for item in results if item["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}


def self_test() -> dict:
    return solution_graph_self_test_checks()
