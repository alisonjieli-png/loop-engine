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

import hashlib
import json

from .solution_canvas import (SolutionError, SolutionLoopSpec, SolutionSpec,
                              _spec_dict, run_solution)

#: strategies executed here (they need extra callables); the rest run in
#: solution_canvas.run_solution.
EXTENDED_STRATEGIES = ("select_best", "gating_router")


def compile_solution(spec: SolutionSpec, registry: dict) -> dict:
    """Validate + resolve + freeze.  The report IS the result — a plan is
    only present when there are zero violations."""
    report = spec.validate()
    violations = list(report["violations"])

    def _walk(s: SolutionSpec):
        for n in s.loops:
            ops = (n.operation,) + tuple(n.fallback_operations)
            if not any(op in registry for op in ops):
                violations.append(
                    f"loop {n.loop_id}: none of {ops} resolves in the "
                    "registry — an unresolvable plan must not compile")
        for m in s.members:
            _walk(m)
    _walk(spec)

    if spec.ensemble == "select_best" and "evaluator" not in registry:
        violations.append("select_best needs registry['evaluator'] "
                          "(member_output -> score)")
    if spec.ensemble == "gating_router" and "router" not in registry:
        violations.append("gating_router needs registry['router'] "
                          "(inputs -> member solution_id)")

    if violations:
        return {"plan": None, "digest": "", "violations": violations}
    canonical = _spec_dict(spec)
    canonical["resolved_operations"] = sorted(registry.keys())
    digest = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, default=str).encode()
    ).hexdigest()
    return {"plan": {"record_type": "solution_plan/v1",
                     "solution_id": spec.solution_id, "spec": canonical,
                     "digest": digest},
            "digest": digest, "violations": []}


def run_compiled(plan: dict, registry: dict, inputs, *,
                 trace: "list | None" = None):
    """Execute a compiled plan; extended strategies run here."""
    if not plan or plan.get("record_type") != "solution_plan/v1":
        raise SolutionError("not a compiled solution_plan/v1 — compile first")
    spec = _spec_from_dict(plan["spec"])
    tr = trace if trace is not None else []
    if spec.ensemble == "select_best":
        scored = []
        for m in spec.members:
            out = run_solution(m, registry, inputs, trace=tr)
            score = registry["evaluator"](out)
            scored.append((score, m.solution_id, out))
            tr.append({"solution": spec.solution_id, "member": m.solution_id,
                       "score": score})
        best = max(scored)
        tr.append({"solution": spec.solution_id, "selected": best[1]})
        return best[2]
    if spec.ensemble == "gating_router":
        target = registry["router"](inputs)
        for m in spec.members:
            if m.solution_id == target:
                tr.append({"solution": spec.solution_id, "routed_to": target})
                return run_solution(m, registry, inputs, trace=tr)
        raise SolutionError(f"router chose {target!r} but no member has "
                            "that id — inspectable, never silent")
    return run_solution(spec, registry, inputs, trace=tr)


def _spec_from_dict(d: dict) -> SolutionSpec:
    return SolutionSpec(
        d["solution_id"], allowed_modes=tuple(d["allowed_modes"]),
        ensemble=d["ensemble"], weights=tuple(d.get("weights", ())),
        loops=tuple(SolutionLoopSpec(n["loop_id"], n["operation"],
                                 mode=n.get("mode", "deterministic"),
                                 fallback_operations=tuple(
                                     n.get("fallback_operations", ())),
                                 params=dict(n.get("params", {})))
                    for n in d.get("loops", ())),
        members=tuple(_spec_from_dict(m) for m in d.get("members", ())))


def render_canvas(plan: dict) -> dict:
    """ONE canonical dict -> Mermaid + JSON views (never a UI-only truth)."""
    spec = plan["spec"]
    lines = ["flowchart TD", '  IN([inputs])']
    edges, counter = [], [0]

    def nid():
        counter[0] += 1
        return f"N{counter[0]}"

    def walk(s: dict, parent: str) -> str:
        me = nid()
        label = f"{s['solution_id']}<br/>{s['ensemble']} | " \
                f"{'/'.join(s['allowed_modes'])}"
        lines.append(f'  {me}["{label}"]')
        edges.append(f"  {parent} --> {me}")
        tail = me
        for n in s.get("loops", ()):
            k = nid()
            fb = ("|fb: " + ",".join(n["fallback_operations"]) + "|"
                  if n.get("fallback_operations") else "")
            lines.append(f'  {k}("{n["loop_id"]}: {n["operation"]} '
                         f'[{n.get("mode", "deterministic")}]{fb}")')
            edges.append(f"  {tail} --> {k}")
            tail = k
        member_tails = [walk(m, me) for m in s.get("members", ())]
        if member_tails:
            join = nid()
            lines.append(f'  {join}{{"{s["solution_id"]} result"}}')
            edges.extend(f"  {member_tail} --> {join}"
                         for member_tail in member_tails)
            tail = join
        return tail

    root = walk(spec, "IN")
    out = nid()
    lines.append(f"  {out}([output])")
    edges.append(f"  {root} --> {out}")
    mermaid = "\n".join(lines + edges)
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
          rep["plan"] is None and "none of" in rep["violations"][0])

    # 2. select_best compiles only with an evaluator, runs, and records the
    # selection (the strategy the canvas module doesn't own).
    sb = SolutionSpec("pick", members=(m1, m2), ensemble="select_best")
    no_eval = compile_solution(sb, {k: v for k, v in reg.items()
                                    if k != "evaluator"})
    ok_rep = compile_solution(sb, reg)
    tr = []
    out = run_compiled(ok_rep["plan"], reg, data, trace=tr)
    check("select_best_compiles_runs_and_records",
          no_eval["plan"] is None and ok_rep["plan"] is not None
          and out == 2.5    # mean=2.5 beats median=3 for 'closest to 2.5'
          and any(t.get("selected") == "m_mean" for t in tr),
          f"selected mean ({out}); evaluator required at compile time")

    # 3. gating_router routes by input; an unknown target is inspectable.
    gr = SolutionSpec("route", members=(
        SolutionSpec("m_small", loops=(SolutionLoopSpec("a", "clean"),
                                       SolutionLoopSpec("b", "mean"))),
        SolutionSpec("m_big", loops=(SolutionLoopSpec("a", "clean"),
                                     SolutionLoopSpec("b", "maxv")))),
        ensemble="gating_router")
    plan = compile_solution(gr, reg)["plan"]
    small = run_compiled(plan, reg, data)
    big = run_compiled(plan, reg, list(range(20)))
    check("gating_router_routes_by_input",
          small == 2.5 and big == 19,
          "6 rows -> m_small(mean); 20 rows -> m_big(max)")

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
          and json.loads(canvas["json"])["digest"] == d1)

    # 6. a loop graph is drawn in the same order in which it executes.
    seq = SolutionSpec("sequence", loops=(
        SolutionLoopSpec("clean", "clean"),
        SolutionLoopSpec("summarize", "mean"),
    ))
    seq_plan = compile_solution(seq, reg)["plan"]
    seq_mermaid = render_canvas(seq_plan)["mermaid"]
    seq_edges = [line.strip() for line in seq_mermaid.splitlines()
                 if " --> " in line]
    check("canvas_draws_solution_loops_in_execution_order",
          seq_edges == ["IN --> N1", "N1 --> N2", "N2 --> N3",
                        "N3 --> N4"],
          str(seq_edges))

    # 7. round trip: plan -> spec -> identical re-compiled digest.
    spec_rt = _spec_from_dict(ok_rep["plan"]["spec"])
    check("plan_spec_round_trip_is_stable",
          compile_solution(spec_rt, reg)["digest"] == d1)

    passed = sum(1 for r in results if r["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
