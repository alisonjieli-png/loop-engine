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

import json

from .solution_canvas import (MODES, SolutionError, SolutionLoopSpec,
                              SolutionSpec, _run_solution_runtime, _spec_dict)
from .solution_graph import (GRAPH_RECORD_TYPE, LoopGraphDefinition,
                             LoopGraphError)

#: strategies executed here (they need extra callables); the rest run in
#: solution_canvas.run_solution.
EXTENDED_STRATEGIES = ("select_best", "gating_router")


def compile_solution(spec: SolutionSpec, registry: dict) -> dict:
    """Validate and resolve one authoritative Loop graph, without rewriting it."""
    report = spec.validate()
    violations = list(report["violations"])
    assert spec.graph is not None
    for operation in spec.graph.required_operation_refs():
        if not callable(registry.get(operation)):
            violations.append(
                f"operation {operation!r} does not resolve to one callable")

    if violations:
        return {"plan": None, "digest": "", "violations": violations}
    canonical = spec.graph.to_dict()
    return {"plan": canonical, "digest": spec.graph.content_digest,
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
            "not an authoritative loop_graph_definition/v1; compile first")
    try:
        graph = LoopGraphDefinition.from_dict(plan)
    except LoopGraphError as exc:
        raise SolutionError(str(exc)) from exc
    missing = [operation for operation in graph.required_operation_refs()
               if not callable(registry.get(operation))]
    if missing:
        raise SolutionError(f"compiled graph operations do not resolve {missing}")
    spec = SolutionSpec.from_graph(graph)
    return _run_solution_runtime(
        spec, registry, inputs, trace=trace, ledger=ledger, parent=parent,
        allow_extended=True, model_execution=model_execution)


def _spec_from_dict(d: dict) -> SolutionSpec:
    if d.get("record_type") == GRAPH_RECORD_TYPE:
        return SolutionSpec.from_graph(LoopGraphDefinition.from_dict(d))
    # Narrow reader for immutable solution_spec/v1-shaped records. New writes
    # emit only LoopGraphDefinition.
    return SolutionSpec(
        d["solution_id"], permitted_loop_modes=tuple(
            d.get("permitted_loop_modes", d.get("allowed_modes", MODES))),
        ensemble=d["ensemble"], weights=tuple(d.get("weights", ())),
        max_members=(None if d.get("max_members") is None
                     else int(d["max_members"])),
        loops=tuple(SolutionLoopSpec(n["loop_id"], n["operation"],
                                 mode=n.get("mode", "deterministic"),
                                 fallback_operations=tuple(
                                     n.get("fallback_operations", ())),
                                 params=dict(n.get("params", {})),
                                 input_role=n.get(
                                     "input_role", "solution.value/v1"),
                                 output_role=n.get(
                                     "output_role", "solution.value/v1"))
                    for n in d.get("loops", ())),
        members=tuple(_spec_from_dict(m) for m in d.get("members", ())))


def render_canvas(plan: dict) -> dict:
    """ONE canonical dict -> Mermaid + JSON views (never a UI-only truth)."""
    graph = LoopGraphDefinition.from_dict(plan)
    lines = ["flowchart TD", '  IN([inputs])']
    vertex_names = {}
    group_by_controller = {group.controller_vertex_id: group
                           for group in graph.groups}
    for index, vertex in enumerate(graph.vertices, 1):
        name = f"L{index}"
        vertex_names[vertex.vertex_id] = name
        group = group_by_controller.get(vertex.vertex_id)
        operation = (f": {vertex.operation_ref}" if vertex.operation_ref else
                     f": {group.combination}" if group is not None else "")
        lines.append(
            f'  {name}(("{vertex.vertex_id}{operation}<br/>'
            f'{vertex.selected_mode}"))')
    first_target = graph.input_ports[0].targets[0].vertex_id
    lines.append(f"  IN --> {vertex_names[first_target]}")
    for edge in graph.edges:
        lines.append(
            f"  {vertex_names[edge.source.vertex_id]} -->|"
            f"{edge.relationship}: {edge.source.port_role}| "
            f"{vertex_names[edge.target.vertex_id]}")
    lines.append("  OUT([output])")
    source = graph.output_ports[0].source.vertex_id
    lines.append(f"  {vertex_names[source]} --> OUT")
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
    spec_rt = _spec_from_dict(ok_rep["plan"])
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
    normalized_legacy = _spec_from_dict(legacy_spec)
    normalized_record = _spec_dict(normalized_legacy)
    check("legacy_allowed_modes_are_read_but_never_emitted",
          normalized_legacy.permitted_loop_modes == MODES
          and normalized_record["record_type"] == GRAPH_RECORD_TYPE
          and "permitted_vertex_modes" in normalized_record
          and "allowed_modes" not in normalized_record,
          "immutable Canvas v1 policy normalizes to permitted_loop_modes")

    passed = sum(1 for r in results if r["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
