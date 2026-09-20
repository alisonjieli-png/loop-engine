"""Solution compiler + Solution Canvas renderer (§16/§15 of the companion).

Architectural role: Solution system (a Code Node over Solution Strings).

Owns:
    - compile_solution: SolutionSpec String -> frozen, content-addressed
      SolutionPlan (every operation resolved, mode closure verified, hidden
      model calls rejected, fallbacks checked) -> an executable composite;
    - select_best / gating_router composition execution (the strategies that
      need an evaluator or router callable, beyond solution_canvas's
      average/vote/weighted/ordered_fallback);
    - render_canvas: ONE canonical serialized graph dict -> Mermaid and
      JSON views (the Solution Canvas explains the PRODUCT; the loop tree
      explains the build — never conflated).

Does not own:
    - SolutionSpec semantics/validation (solution_canvas.py owns the spec);
    - promotion (a compiled plan is a candidate until admitted through the
      one lifecycle gate).

Public entry points:
    - compile_solution(spec, registry) -> {"plan", "digest", "violations"}
    - run_compiled(plan, registry, inputs, evaluator/router) -> value
    - render_canvas(plan) -> {"canonical", "mermaid", "json"}

Side effects and authority: pure computation; no filesystem, no network.

Key invariants:
    - a spec with violations does NOT compile (fail closed, report attached);
    - the plan digest binds the exact resolved composition;
    - a code_only plan cannot contain a hybrid/model_led loop (mode closure);
    - select_best needs an evaluator; gating_router needs a router — absence
      is a compile-time violation, never a runtime surprise.

Verification: self_test() (folded into the package suite).
"""
from __future__ import annotations

from dataclasses import replace
import functools
import hashlib
import html
import json
import marshal
import sys
import types

from ..loop.loop_definition import ConfigurationFacts

from .solution_canvas import (MODES, SolutionError, SolutionLoopSpec,
                              SolutionSpec, _run_solution_runtime)
from .solution_graph import (GRAPH_RECORD_TYPE, LoopGraphDefinition,
                             LoopGraphError)
from .solution_operation_identity import PROCESS_BOUND, PORTABLE_CODE, SolutionOperationIdentity

#: strategies executed here (they need extra callables); the rest run in
#: solution_canvas.run_solution.
EXTENDED_STRATEGIES = ("select_best", "gating_router")


def operation_identity(operation_ref: str, operation) -> SolutionOperationIdentity:
    """Fingerprint code and referenced bindings without invoking the operation.

    Mutable opaque state retains object identity and is explicitly process
    bound. It remains trusted host state, not a claim of immutable semantics
    or independent Code Intelligence qualification.
    """
    if not callable(operation):
        raise SolutionError(f"operation {operation_ref!r} does not resolve to one callable")
    process_bound = False
    active = set()

    def code_bytes(code):
        constants = tuple(code_bytes(item) if isinstance(item, types.CodeType) else item
                          for item in code.co_consts)
        return marshal.dumps(code.replace(co_filename="", co_firstlineno=0,
                                          co_consts=constants))

    def material(value):
        nonlocal process_bound
        if value is None or type(value) in (str, bool, int, float, bytes):
            return (type(value).__name__, marshal.dumps(value).hex())
        if type(value) is tuple:
            return ("tuple", tuple(material(item) for item in value))
        if type(value) is frozenset:
            return ("frozenset", tuple(sorted(material(item) for item in value)))
        if id(value) in active:
            return ("recursive_binding", type(value).__module__, type(value).__qualname__)
        active.add(id(value))
        try:
            if isinstance(value, types.FunctionType):
                closure = []
                for cell in value.__closure__ or ():
                    try:
                        closure.append(material(cell.cell_contents))
                    except ValueError:
                        closure.append(("empty_cell",))
                globals_used = tuple((name, material(value.__globals__[name]))
                    for name in sorted(set(value.__code__.co_names))
                    if name in value.__globals__)
                return ("function", value.__module__, value.__qualname__,
                        hashlib.sha256(code_bytes(value.__code__)).hexdigest(),
                        material(value.__defaults__),
                        tuple((key, material(item)) for key, item in sorted(
                            (value.__kwdefaults__ or {}).items())),
                        tuple(closure), globals_used)
            if isinstance(value, types.MethodType):
                return ("bound_method", material(value.__func__), material(value.__self__))
            if isinstance(value, functools.partial):
                return ("partial", material(value.func), material(value.args),
                        tuple((key, material(item)) for key, item in sorted(
                            (value.keywords or {}).items())))
            if isinstance(value, types.ModuleType):
                namespace = vars(value)
                return ("module", namespace.get("__name__"),
                        material(namespace.get("__version__")))
            if isinstance(value, (types.BuiltinFunctionType, types.BuiltinMethodType)):
                return ("builtin", value.__module__, value.__qualname__)
            process_bound = True
            return ("host_state", type(value).__module__, type(value).__qualname__, id(value))
        finally:
            active.remove(id(value))

    runtime = f"{sys.implementation.name}:{sys.implementation.cache_tag}:{sys.version_info[:3]}"
    body = material(operation)
    if not isinstance(operation, (types.FunctionType, types.MethodType,
                                  types.BuiltinFunctionType, types.BuiltinMethodType,
                                  functools.partial)):
        body = (body, material(type(operation).__call__))
    digest = hashlib.sha256(json.dumps((runtime, body), sort_keys=True,
        separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    return SolutionOperationIdentity(operation_ref, digest, runtime,
                                     PROCESS_BOUND if process_bound else PORTABLE_CODE)


def bind_solution_operations(graph: LoopGraphDefinition, registry: dict) -> LoopGraphDefinition:
    """Bind each operation inside its exact Loop definition before execution."""
    identities = {name: operation_identity(name, registry.get(name))
                  for name in graph.required_operation_refs()}
    vertices = []
    for vertex in graph.vertices:
        if not vertex.operation_ref:
            vertices.append(vertex)
            continue
        definition = vertex.resolved_definition(None)
        facts = definition.configuration_facts.to_dict()
        current = identities[vertex.operation_ref]
        if "operation_identity" in facts:
            prior = SolutionOperationIdentity.from_dict(facts["operation_identity"])
            if prior != current:
                raise SolutionError(f"operation {vertex.operation_ref!r} implementation changed")
        facts["operation_identity"] = current.to_dict()
        bound = replace(definition, configuration_facts=ConfigurationFacts.from_mapping(facts))
        vertices.append(replace(vertex, definition=bound, definition_ref=bound.ref))
    return replace(graph, vertices=tuple(vertices))


def validate_operation_binding(definition, operation_ref, operation) -> None:
    facts = definition.configuration_facts.to_dict()
    if "operation_identity" not in facts:
        raise SolutionError(f"operation {operation_ref!r} has no compiled implementation identity")
    expected = SolutionOperationIdentity.from_dict(facts["operation_identity"])
    if expected != operation_identity(operation_ref, operation):
        raise SolutionError(f"operation {operation_ref!r} implementation changed")


def compile_solution(spec: SolutionSpec, registry: dict) -> dict:
    """Validate a graph and bind exact trusted operation implementations."""
    report = spec.validate()
    violations = list(report["violations"])
    assert spec.graph is not None
    for operation in spec.graph.required_operation_refs():
        if not callable(registry.get(operation)):
            violations.append(
                f"operation {operation!r} does not resolve to one callable")

    if violations:
        return {"plan": None, "digest": "", "violations": violations}
    try:
        bound = bind_solution_operations(spec.graph, registry)
    except (SolutionError, LoopGraphError) as exc:
        return {"plan": None, "digest": "", "violations": [str(exc)]}
    canonical = bound.to_dict()
    return {"plan": canonical, "digest": bound.content_digest,
            "violations": []}


def run_compiled(plan: dict, registry: dict, inputs, *,
                 trace: "list | None" = None, ledger=None, parent=None,
                 model_execution=None):
    """Execute a compiled plan through one role-correct Solution tree.

    Extended evaluator and router callables run as Spawned Solution loops
    under the compiled solution envelope. Member solutions share that
    envelope's ledger instead of becoming unrelated starting loops.
    """
    if not plan or plan.get("record_type") != GRAPH_RECORD_TYPE:
        raise SolutionError(
            f"not an authoritative {GRAPH_RECORD_TYPE}; compile the current graph first")
    try:
        graph = LoopGraphDefinition.from_dict(plan)
    except LoopGraphError as exc:
        raise SolutionError(str(exc)) from exc
    missing = [operation for operation in graph.required_operation_refs()
               if not callable(registry.get(operation))]
    if missing:
        raise SolutionError(f"compiled graph operations do not resolve {missing}")
    for vertex in graph.vertices:
        if vertex.operation_ref:
            validate_operation_binding(vertex.resolved_definition(None),
                                       vertex.operation_ref, registry.get(vertex.operation_ref))
    spec = SolutionSpec.from_graph(graph)
    return _run_solution_runtime(
        spec, registry, inputs, trace=trace, ledger=ledger, parent=parent,
        allow_extended=True, model_execution=model_execution)


def render_canvas(plan: dict) -> dict:
    """ONE canonical dict -> Mermaid + JSON views (never a UI-only truth)."""
    graph = LoopGraphDefinition.from_dict(plan)
    lines = ["flowchart TD"]
    for index, port in enumerate(graph.input_ports, 1):
        name = "IN" if len(graph.input_ports) == 1 else f"IN{index}"
        label = html.escape(f"input {port.name}: {port.role}")
        lines.append(f"  {name}([{json.dumps(label)}])")
    vertex_names = {}
    group_by_controller = {group.controller_vertex_id: group
                           for group in graph.groups}
    for index, vertex in enumerate(graph.vertices, 1):
        name = f"L{index}"
        vertex_names[vertex.vertex_id] = name
        group = group_by_controller.get(vertex.vertex_id)
        operation = (f": {vertex.operation_ref}" if vertex.operation_ref else
                     f": {group.combination}" if group is not None else "")
        definition = vertex.resolved_definition(None)
        label = "<br/>".join(html.escape(value) for value in (
            f"{vertex.vertex_id}{operation}",
            f"Loop: {definition.identity.role.value}",
            f"{definition.role_profile_id}@{definition.role_profile_version}",
            f"mode: {vertex.selected_mode}",
            f"inputs: {', '.join(definition.contract.input_roles) or 'none'}",
            f"outputs: {', '.join(definition.contract.output_roles)}",
            f"continue: {definition.loop_condition}",
            f"exit: {definition.exit_condition}"))
        lines.append(
            f"  {name}(({json.dumps(label)}))")
    for index, port in enumerate(graph.input_ports, 1):
        name = "IN" if len(graph.input_ports) == 1 else f"IN{index}"
        for target in port.targets:
            lines.append(f"  {name} --> {vertex_names[target.vertex_id]}")
    for edge in graph.edges:
        lines.append(
            f"  {vertex_names[edge.source.vertex_id]} -->|"
            f"{edge.relationship}: {edge.source.port_role}| "
            f"{vertex_names[edge.target.vertex_id]}")
    for index, port in enumerate(graph.output_ports, 1):
        name = "OUT" if len(graph.output_ports) == 1 else f"OUT{index}"
        label = html.escape(f"output {port.name}: {port.role}")
        lines.append(f"  {name}([{json.dumps(label)}])")
        lines.append(f"  {vertex_names[port.source.vertex_id]} --> {name}")
    mermaid = "\n".join(lines)
    return {"canonical": plan, "mermaid": mermaid,
            "json": json.dumps(plan, indent=1, default=str)}


def self_test() -> dict:
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    reg = {
        "clean": lambda x, p: [v for v in x if v is not None],
        "mean": lambda x, p: sum(x) / len(x),
        "median": lambda x, p: sorted(x)[len(x) // 2],
        "maxv": lambda x, p: max(x),
        "evaluator": lambda out: -abs(out - 2.5),   # closest to 2.5 wins
        "router": lambda inputs: "m_small" if len(inputs) < 10 else "m_big",
    }
    data = [1, None, 2, 3, None, 4]
    m1 = SolutionSpec("m_mean", loops=(SolutionLoopSpec("a", "clean"),
                                       SolutionLoopSpec("b", "mean")))
    m2 = SolutionSpec("m_median", loops=(SolutionLoopSpec("a", "clean"),
                                         SolutionLoopSpec("b", "median")))

    # 1. an unresolvable spec does NOT compile; the report says why.
    bad = SolutionSpec("ghost", loops=(SolutionLoopSpec("a", "no_such_op"),))
    rep = compile_solution(bad, reg)
    check("unresolvable_spec_does_not_compile",
          rep["plan"] is None
          and "does not resolve" in rep["violations"][0])

    # 2. select_best compiles only with an evaluator, runs, and records the
    # selection (the strategy the canvas module doesn't own).
    sb = SolutionSpec("pick", members=(m1, m2), ensemble="select_best")
    no_eval = compile_solution(sb, {k: v for k, v in reg.items()
                                    if k != "evaluator"})
    ok_rep = compile_solution(sb, reg)
    tr = []
    from ..loop.recursive_loop import LoopLedger
    compiled_ledger = LoopLedger()
    out = run_compiled(ok_rep["plan"], reg, data, trace=tr,
                       ledger=compiled_ledger)
    compiled_inits = [e for e in compiled_ledger.events
                      if e.get("event") == "init"]
    evaluator_calls = [e for e in compiled_ledger.events
                       if e.get("event") == "tool_invocation_started"
                       and e.get("operation") == "evaluator"]
    init_by_id = {e["loop_id"]: e for e in compiled_inits}
    check("select_best_compiles_runs_and_records",
          no_eval["plan"] is None and ok_rep["plan"] is not None
          and out == 2.5    # mean=2.5 beats median=3 for 'closest to 2.5'
          and any(t.get("selected") == "m_mean" for t in tr)
          and compiled_inits[0].get("relationship_kind") == "starting"
          and compiled_inits[0].get("profile_id") == "solution.ensemble"
          and len(evaluator_calls) == 2
          and all(init_by_id[e["loop_id"]].get("role") == "solution"
                  and init_by_id[e["loop_id"]].get("profile_id")
                      == "solution.validator"
                  and init_by_id[e["loop_id"]].get("relationship_kind")
                      == "connected_from"
                  and init_by_id[e["loop_id"]].get(
                      "connected_from_loop_ids")
                      in ([compiled_inits[1]["loop_id"]],
                          [compiled_inits[4]["loop_id"]])
                  for e in evaluator_calls),
          f"selected mean ({out}); evaluator calls are validator spawned_loops")

    # 3. gating_router routes by input; an unknown target is inspectable.
    gr = SolutionSpec("route", members=(
        SolutionSpec("m_small", loops=(SolutionLoopSpec("a", "clean"),
                                       SolutionLoopSpec("b", "mean"))),
        SolutionSpec("m_big", loops=(SolutionLoopSpec("a", "clean"),
                                     SolutionLoopSpec("b", "maxv")))),
        ensemble="gating_router")
    plan = compile_solution(gr, reg)["plan"]
    router_ledger = LoopLedger()
    small = run_compiled(plan, reg, data, ledger=router_ledger)
    big = run_compiled(plan, reg, list(range(20)))
    router_inits = {e["loop_id"]: e for e in router_ledger.events
                    if e.get("event") == "init"}
    router_call = next(e for e in router_ledger.events
                       if e.get("event") == "tool_invocation_started"
                       and e.get("operation") == "router")
    router_starting = next(e for e in router_inits.values()
                           if e.get("relationship_kind") == "starting")
    check("gating_router_routes_by_input",
          small == 2.5 and big == 19
          and router_starting.get("profile_id")
              == "solution.router_fallback"
          and router_inits[router_call["loop_id"]].get("role") == "solution"
          and router_inits[router_call["loop_id"]].get("relationship_kind")
              == "connected_from"
          and router_inits[router_call["loop_id"]].get(
              "connected_from_loop_ids") == [router_starting["loop_id"]],
          "router callable is connected from its Starting Solution")

    # 4. the plan digest binds the exact composition (a changed member ->
    # a different digest).
    d1 = compile_solution(sb, reg)["digest"]
    sb2 = SolutionSpec("pick", members=(m1,
                                        SolutionSpec("m_median2",
                                                     loops=m2.loops)),
                       ensemble="select_best")
    d2 = compile_solution(sb2, reg)["digest"]
    check("plan_digest_binds_exact_composition",
          len(d1) == 64 and d1 != d2)

    # 5. the canvas renders Mermaid + JSON from ONE canonical dict.
    canvas = render_canvas(ok_rep["plan"])
    check("canvas_renders_from_one_canonical_truth",
          canvas["mermaid"].startswith("flowchart TD")
          and "m_mean" in canvas["mermaid"]
          and "select_best" in canvas["mermaid"]
          and json.loads(canvas["json"])["content_digest"] == d1)

    # 6. a loop graph is drawn in the same order in which it executes.
    seq = SolutionSpec("sequence", loops=(
        SolutionLoopSpec("clean", "clean"),
        SolutionLoopSpec("summarize", "mean"),
    ))
    seq_plan = compile_solution(seq, reg)["plan"]
    seq_mermaid = render_canvas(seq_plan)["mermaid"]
    seq_edges = [line.strip() for line in seq_mermaid.splitlines()
                 if "-->" in line]
    check("canvas_draws_solution_loops_in_execution_order",
          len(seq_edges) == 4 and seq_edges[0] == "IN --> L1"
          and seq_edges[-1].endswith("--> OUT"),
          str(seq_edges))

    # 7. round trip: plan -> spec -> identical re-compiled digest.
    spec_rt = SolutionSpec.from_graph(LoopGraphDefinition.from_dict(ok_rep["plan"]))
    check("plan_spec_round_trip_is_stable",
          compile_solution(spec_rt, reg)["digest"] == d1)

    legacy_spec = {
        "solution_id": "legacy", "allowed_modes": list(MODES),
        "ensemble": "single", "weights": [], "max_members": 5,
        "loops": [{"loop_id": "one", "operation": "clean",
                   "mode": "deterministic", "fallback_operations": [],
                   "params": {}, "input_role": "solution.value/v1",
                   "output_role": "solution.value/v1"}],
        "members": [],
    }
    obsolete = dict(ok_rep["plan"], record_type="loop_graph_definition/v1")
    refused = 0
    for record in (legacy_spec, obsolete):
        try:
            LoopGraphDefinition.from_dict(record)
        except LoopGraphError:
            refused += 1
    check("unsupported_solution_records_are_refused_without_upgrade", refused == 2)

    passed = sum(1 for r in results if r["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
