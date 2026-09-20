"""Adversarial checks for the authoritative Solution Loop graph.

These checks prove that incomplete, hidden, cyclic, or tampered graph work is
refused before execution and that an Adapter is a real Loop vertex.
"""
from __future__ import annotations

from dataclasses import replace
import types

from ..loop.loop_definition import ConfigurationFacts, LoopDefinitionRef
from ..loop.canvas import SolutionLoopCandidate, TypeContract
from .solution_canvas import (SolutionError, SolutionLoopSpec, SolutionSpec,
                              run_solution)
from .solution_graph import (
    AdapterLoopRunRequest, LoopGraphEdge, LoopGraphEndpoint, LoopGraphError,
    LoopGraphInputPort, LoopGraphOutputPort,
    SolutionLoopDefinitionRequest,
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
        semantic_refused = "needs explicit model authority" in str(exc)
    check("semantic_mode_unavailable_is_refused_before_work",
          semantic_refused and not semantic_calls)

    from .solution_compiler import compile_solution, render_canvas, run_compiled
    arithmetic = {"first": lambda value, params: value + 1,
                  "second": lambda value, params: value * 10}
    first_id, second_id = spec.loops[0].vertex_id, spec.loops[1].vertex_id
    role = spec.loops[0].input_role
    connecting = next(edge for edge in graph.edges
                      if edge.source.vertex_id == first_id
                      and edge.target.vertex_id == second_id)
    independent = replace(graph,
        edges=tuple(edge for edge in graph.edges if edge is not connecting),
        input_ports=(replace(graph.input_ports[0], targets=(
            *graph.input_ports[0].targets, LoopGraphEndpoint(second_id, role))),))
    independent_plan = compile_solution(SolutionSpec.from_graph(independent), arithmetic)
    check("external_stage_binding_controls_the_executed_input",
          independent_plan["plan"] is not None
          and run_compiled(independent_plan["plan"], arithmetic, 2) == 20)

    ordered_calls = []
    ordered_registry = {
        "first": lambda value, params: ordered_calls.append("first") or value + 1,
        "second": lambda value, params: ordered_calls.append("second") or value * 10}
    reordered = replace(graph, groups=(replace(graph.groups[0],
                                               stages=tuple(reversed(graph.groups[0].stages))),))
    check("dependency_order_is_independent_of_stage_presentation_order",
          run_solution(SolutionSpec.from_graph(reordered), ordered_registry, 2) == 30
          and ordered_calls == ["first", "second"])

    early_output = replace(graph, output_ports=(replace(graph.output_ports[0],
        source=LoopGraphEndpoint(first_id, role)),))
    check("external_output_binding_selects_the_declared_producer",
          run_solution(SolutionSpec.from_graph(early_output), arithmetic, 2) == 3)

    named_inputs = replace(independent,
        input_ports=(graph.input_ports[0], LoopGraphInputPort("other", role,
            (LoopGraphEndpoint(second_id, role),))),
        output_ports=(graph.output_ports[0], LoopGraphOutputPort("early", role,
            LoopGraphEndpoint(first_id, role))))
    check("multiple_named_external_inputs_and_outputs_keep_distinct_values",
          run_solution(SolutionSpec.from_graph(named_inputs), arithmetic,
                       {"input": 2, "other": 7}) == {"output": 70, "early": 3})
    named_canvas = render_canvas(compile_solution(
        SolutionSpec.from_graph(named_inputs), arithmetic)["plan"])["mermaid"]
    check("canvas_displays_all_ports_and_each_loop_contract",
          "IN2 -->" in named_canvas and named_canvas.count(" --> OUT") == 2
          and all(label in named_canvas for label in (
              "input other", "output early", "solution.atomic_component@1.0.0",
              "inputs:", "outputs:", "continue:", "exit:")))
    invalid_input_calls = []
    invalid_input_registry = {key: (lambda value, params: invalid_input_calls.append(value))
                              for key in arithmetic}
    invalid_input_refused = False
    try:
        run_solution(SolutionSpec.from_graph(named_inputs), invalid_input_registry, {"input": 2})
    except SolutionError:
        invalid_input_refused = True
    check("missing_named_external_input_refuses_before_operation",
          invalid_input_refused and not invalid_input_calls)
    repeated_input = replace(graph, input_ports=(*graph.input_ports,
        LoopGraphInputPort("duplicate", role, graph.input_ports[0].targets)))
    check("two_external_inputs_cannot_bind_one_target_port",
          not repeated_input.validate().valid
          and any("bound more than once" in item for item in repeated_input.validate().violations))

    diamond_spec = SolutionSpec("diamond", loops=(
        SolutionLoopSpec("left", "left"), SolutionLoopSpec("right", "right"),
        SolutionLoopSpec("join", "join")))
    diamond = diamond_spec.graph
    controller, left, right, join = diamond.vertices

    def ports(vertex, inputs, outputs):
        definition = replace(vertex.definition, contract=replace(vertex.definition.contract,
            input_roles=inputs, output_roles=outputs))
        return replace(vertex, definition=definition, definition_ref=definition.ref)

    left = ports(left, (role,), ("left/v1",))
    right = ports(right, (role,), ("right/v1",))
    join = ports(join, ("left/v1", "right/v1"), (role,))
    diamond = replace(diamond, vertices=(controller, left, right, join), edges=(
        LoopGraphEdge("left-input", LoopGraphEndpoint(controller.vertex_id, role),
                      LoopGraphEndpoint(left.vertex_id, role)),
        LoopGraphEdge("right-input", LoopGraphEndpoint(controller.vertex_id, role),
                      LoopGraphEndpoint(right.vertex_id, role)),
        LoopGraphEdge("left-result", LoopGraphEndpoint(left.vertex_id, "left/v1"),
                      LoopGraphEndpoint(join.vertex_id, "left/v1")),
        LoopGraphEdge("right-result", LoopGraphEndpoint(right.vertex_id, "right/v1"),
                      LoopGraphEndpoint(join.vertex_id, "right/v1"))))
    diamond_registry = {"left": lambda value, params: value + 1,
                        "right": lambda value, params: value * 10,
                        "join": lambda value, params: value["left/v1"] + value["right/v1"]}
    check("branch_and_join_uses_each_declared_typed_input",
          diamond.validate().valid
          and run_solution(SolutionSpec.from_graph(diamond), diamond_registry, 2) == 23)

    fallback_spec = SolutionSpec("alternate-input", loops=(
        SolutionLoopSpec("attempt", "fail", fallback_operations=("second",)),))
    fallback_graph = fallback_spec.graph
    backup_id = fallback_spec.loops[0].fallback_vertex_ids[0]
    fallback_graph = replace(fallback_graph,
        edges=tuple(edge for edge in fallback_graph.edges if edge.target.vertex_id != backup_id),
        input_ports=(*fallback_graph.input_ports, LoopGraphInputPort("backup", role,
            (LoopGraphEndpoint(backup_id, role),))))

    def fail(value, params):
        raise ValueError("declared first attempt fails")

    check("fallback_attempt_uses_its_own_declared_input_binding",
          run_solution(SolutionSpec.from_graph(fallback_graph),
                       {"fail": fail, "second": arithmetic["second"]},
                       {"input": 2, "backup": 7}) == 70)

    ensemble = SolutionSpec("control-boundary", members=(spec, SolutionSpec("other-member",
        loops=(SolutionLoopSpec("other", "first"),))), ensemble="average")
    ensemble_graph = ensemble.graph
    outer = ensemble_graph.group(ensemble_graph.starting_group_id)
    member_a = ensemble_graph.group(outer.member_group_ids[0])
    member_b = ensemble_graph.group(outer.member_group_ids[1])
    bypass = replace(ensemble_graph, edges=tuple(
        replace(edge, source=LoopGraphEndpoint(member_a.stages[-1].result_vertex_id, role))
        if edge.target.vertex_id == member_b.controller_vertex_id else edge
        for edge in ensemble_graph.edges))
    check("unsupported_cross_group_control_bypass_is_explicitly_refused",
          not bypass.validate().valid and any("unsupported execution-control topology" in item
                                             for item in bypass.validate().violations))

    identity_calls = []
    identity_registry = {
        "first": lambda value, params: identity_calls.append(value) or value + 1,
        "second": arithmetic["second"]}
    exact_plan = compile_solution(spec, identity_registry)
    check("compilation_binds_identity_without_mutating_the_source_graph",
          exact_plan["digest"] != graph.content_digest
          and all("operation_identity" not in vertex.resolved_definition(None).configuration_facts.to_dict()
                  for vertex in graph.vertices))
    original_operation = identity_registry["first"]
    identity_registry["first"] = lambda value, params: value + 100
    changed_refused = False
    try:
        run_compiled(exact_plan["plan"], identity_registry, 2)
    except SolutionError as exc:
        changed_refused = "implementation changed" in str(exc)
    check("changed_operation_implementation_refuses_before_any_execution",
          changed_refused and not identity_calls)
    from .solution_graph import LoopGraphDefinition
    stale_spec = SolutionSpec.from_graph(LoopGraphDefinition.from_dict(exact_plan["plan"]))
    check("an_existing_compiled_binding_cannot_be_silently_rebound",
          compile_solution(stale_spec, identity_registry)["plan"] is None)
    changed_plan = compile_solution(spec, identity_registry)
    check("implementation_change_changes_the_compiled_graph_identity",
          changed_plan["plan"] is not None and changed_plan["digest"] != exact_plan["digest"])
    identity_registry["first"] = original_operation
    original_code = original_operation.__code__
    changed_code = (lambda value, params: identity_calls.append(value) or value + 200).__code__
    original_operation.__code__ = changed_code
    code_mutation_refused = False
    try:
        run_compiled(exact_plan["plan"], identity_registry, 2)
    except SolutionError as exc:
        code_mutation_refused = "implementation changed" in str(exc)
    finally:
        original_operation.__code__ = original_code
    check("in_place_callable_code_change_invalidates_the_binding", code_mutation_refused)

    portable_plan = compile_solution(spec, arithmetic)
    unsigned_refused = False
    try:
        run_compiled(graph.to_dict(), arithmetic, 2)
    except SolutionError as exc:
        unsigned_refused = "no compiled implementation identity" in str(exc)
    check("historical_unbound_graph_requires_explicit_compilation",
          unsigned_refused and run_compiled(portable_plan["plan"], arithmetic, 2) == 30)
    same_function = arithmetic["first"]
    exact_copy = types.FunctionType(same_function.__code__, same_function.__globals__,
                                   same_function.__name__, same_function.__defaults__,
                                   same_function.__closure__)
    exact_copy.__qualname__ = same_function.__qualname__
    check("equivalent_code_identity_is_accepted_without_object_identity_locking",
          run_compiled(portable_plan["plan"], {**arithmetic, "first": exact_copy}, 2) == 30)

    late_calls = []
    late_registry = {}

    def replace_later(value, params):
        late_registry["second"] = lambda current, ignored: late_calls.append(current) or 999
        return value + 1

    late_registry.update(first=replace_later, second=arithmetic["second"])
    late_plan = compile_solution(spec, late_registry)
    late_refused = False
    try:
        run_compiled(late_plan["plan"], late_registry, 2)
    except SolutionError as exc:
        late_refused = "implementation changed" in str(exc)
    check("implementation_is_rechecked_at_the_actual_invocation",
          late_refused and not late_calls)

    passed = sum(1 for item in results if item["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}


def self_test() -> dict:
    return solution_graph_self_test_checks()
