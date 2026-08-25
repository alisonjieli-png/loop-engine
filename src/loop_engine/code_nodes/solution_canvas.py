"""The Solution Canvas — what a practitioner run PRODUCES, made first-class.

The owner's distinction (2026-08-23): the practitioner loop BUILDS a solution;
the SOLUTION ITSELF is a separate artifact with its own mode discipline —
deterministic (same answer every run), hybrid (code with declared model-assist
slots), or model-led — chosen by the USER'S setting, not by how the loop was
built.  A solution is a graph of loops; each LOOP carries its own mode and
fallback chain; and a solution can be a SOLUTION OF SOLUTIONS — one composite
whose members are averaged, voted, weighted, or ordered as fallbacks.

Nothing here changes the practitioner loop.  The loop's ``act``/``commit``
steps emit a ``SolutionSpec`` (a String — declarative, serializable,
searchable); ``run_solution`` (a code loop) executes it against a registry of
operation callables.  The same mode vocabulary as the loop is reused exactly
(deterministic | hybrid | non_deterministic) so one setting language covers
both how you SOLVE and what you SHIP.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from ..loop.encapsulate import as_component_loop
from ..loop.recursive_loop import MODES, LoopError, LoopLedger

#: how a composite combines its member solutions.  select_best and
#: gating_router are EXTENDED strategies: they validate here but execute in
#: solution_compiler.run_compiled (they need an evaluator/router callable,
#: enforced at compile time).
ENSEMBLE_METHODS = ("single", "average", "vote", "weighted_average",
                    "ordered_fallback", "select_best", "gating_router")
_EXTENDED = ("select_best", "gating_router")


class SolutionError(ValueError):
    """A solution spec that cannot be honestly executed as declared."""


@dataclass
class SolutionLoopSpec:
    """One LOOP in a solution graph: its own mode + its own fallback chain.

    The owner's node rule (2026-08-25): each loop is a node, and every
    operational node uses the same loop runtime.
    Most shipped components are deterministic and collapse to a single pass,
    but each is a real PractitionerLoop envelope — which is what gives it
    identity, evidence, failure attribution, and the fallback seam.
    """
    loop_id: str
    operation: str                      # registry key of the callable
    mode: str = "deterministic"
    fallback_operations: tuple = ()     # tried in order when the op fails
    params: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.mode not in MODES:
            raise SolutionError(f"loop {self.loop_id}: mode {self.mode!r} "
                                f"not in {MODES}")


@dataclass
class SolutionSpec:
    """The declarative solution String.

    ``allowed_modes`` is the USER'S shipping setting: a deterministic-only
    spec refuses any loop that would need a model, at validation time — the
    same permission grammar as the loop, applied to the artifact.
    ``members`` makes it a solution of solutions; ``ensemble`` says how they
    combine; ``weights`` applies to weighted_average (must match members).

    Nomenclature (the loop-node rule): this solution's graph is ``loops`` —
    every element is a ``SolutionLoopSpec``, a PractitionerLoop.  There is no
    node field, and no legacy alias; the canonical name is the only name.
    """
    solution_id: str
    allowed_modes: tuple = MODES
    loops: tuple = ()                   # this solution's own graph of loops
    members: tuple = ()                 # child SolutionSpecs (composite)
    ensemble: str = "single"
    weights: tuple = ()
    max_members: int = 5

    def validate(self) -> dict:
        """Fail-closed validation; the report IS the result."""
        v = []
        for m in self.allowed_modes:
            if m not in MODES:
                v.append(f"allowed mode {m!r} unknown")
        if self.ensemble not in ENSEMBLE_METHODS:
            v.append(f"ensemble {self.ensemble!r} not in {ENSEMBLE_METHODS}")
        if self.loops and self.members:
            v.append("a solution is EITHER a loop graph OR a composite of "
                     "members, never both (compose by nesting instead)")
        if not self.loops and not self.members:
            v.append("an empty solution ships nothing")
        if len(self.members) > self.max_members:
            v.append(f"{len(self.members)} members exceeds the "
                     f"max_members bound {self.max_members}")
        if self.ensemble == "weighted_average" and \
                len(self.weights) != len(self.members):
            v.append("weighted_average needs one weight per member")
        if self.ensemble != "single" and len(self.members) < 2:
            v.append(f"ensemble {self.ensemble!r} needs >=2 members")
        for n in self.loops:
            if n.mode not in self.allowed_modes:
                v.append(f"loop {n.loop_id} needs mode {n.mode} but the "
                         f"solution allows only {tuple(self.allowed_modes)} — "
                         "the shipping setting is a hard gate")
        for m in self.members:
            wider = [x for x in m.allowed_modes if x not in self.allowed_modes]
            if wider:
                v.append(f"member {m.solution_id} allows {wider} beyond the "
                         "parent — a member never has more mode permissions")
            v.extend(f"member {m.solution_id}: {e}"
                     for e in m.validate()["violations"])
        return {"valid": not v, "violations": v}

    def to_record(self):
        """The searchable String record (facets ride the card)."""
        from ..static_architecture.store_serve import StoreRecord
        from ..static_architecture.facets import string_facets
        return StoreRecord(
            f"solution.{self.solution_id}", "strategy",
            f"Solution spec: {self.solution_id} ({self.ensemble}; modes "
            f"{'/'.join(self.allowed_modes)})",
            body={"role": "solution_spec", "spec": _spec_dict(self),
                  "facets": string_facets(category="solution_spec",
                                          subcategory=self.ensemble)},
            tags=("solution_spec", self.ensemble) + tuple(self.allowed_modes))


def _spec_dict(s: SolutionSpec) -> dict:
    return {"solution_id": s.solution_id,
            "allowed_modes": list(s.allowed_modes),
            "ensemble": s.ensemble, "weights": list(s.weights),
            "loops": [{"loop_id": n.loop_id, "operation": n.operation,
                       "mode": n.mode,
                       "fallback_operations": list(n.fallback_operations),
                       "params": n.params} for n in s.loops],
            "members": [_spec_dict(m) for m in s.members]}


def _bind(fn, params: dict):
    """One registry callable (inputs, params) as the single-argument arm a
    component loop runs."""
    return lambda value: fn(value, params)


def run_solution(spec: SolutionSpec, registry: dict, inputs,
                 *, trace: "list | None" = None, ledger=None):
    """Execute a validated solution — every component AS A PRACTITIONER LOOP.

    Each registry callable takes (inputs, params) and returns a value, but it
    is never invoked directly: it becomes an arm of the component's own loop,
    so a failure walks that loop's ordered fallback chain (each attempt
    recorded) before raising inspectably.  A composite runs its members and
    combines by the ensemble policy; ``ordered_fallback`` returns the first
    member that completes.  Pass ``ledger`` to put the component loops on the
    run's own timeline; without one a private ledger still records them, so
    evidence exists whether or not the caller asked for it.
    """
    report = spec.validate()
    if not report["valid"]:
        raise SolutionError("; ".join(report["violations"]))
    tr = trace if trace is not None else []
    lg = ledger if ledger is not None else LoopLedger()

    if spec.members:
        if spec.ensemble in _EXTENDED:
            raise SolutionError(
                f"{spec.ensemble} is an extended strategy — compile the spec "
                "and execute via solution_compiler.run_compiled (it needs an "
                "evaluator/router the compiler verifies)")
        outs, errors = [], []
        for m in spec.members:
            try:
                outs.append(run_solution(m, registry, inputs, trace=tr,
                                         ledger=lg))
                if spec.ensemble == "ordered_fallback":
                    tr.append({"solution": spec.solution_id,
                               "served_by": m.solution_id})
                    return outs[-1]
            except SolutionError as e:
                errors.append(f"{m.solution_id}: {e}")
                tr.append({"solution": spec.solution_id,
                           "member_failed": m.solution_id, "error": str(e)})
        if not outs:
            raise SolutionError(f"every member failed: {errors}")
        if spec.ensemble == "average":
            return sum(outs) / len(outs)
        if spec.ensemble == "weighted_average":
            ws = list(spec.weights)[:len(outs)]
            return sum(o * w for o, w in zip(outs, ws)) / sum(ws)
        if spec.ensemble == "vote":
            return max(set(outs), key=outs.count)
        return outs[0]                                     # single

    value = inputs
    for n in spec.loops:
        ops = [op for op in (n.operation,) + tuple(n.fallback_operations)
               if registry.get(op) is not None]
        for op in (n.operation,) + tuple(n.fallback_operations):
            if registry.get(op) is None:
                tr.append({"solution_loop": n.loop_id,
                           "missing_operation": op})
        if not ops:
            raise SolutionError(
                f"solution loop {n.loop_id}: no operation in "
                f"{(n.operation,) + tuple(n.fallback_operations)} resolves")
        # THE LOOP-NODE RULE, on the live path: the component never calls a
        # registry callable directly — it runs as a PractitionerLoop whose
        # own ordered fallback chain is its arms.  One loop per component,
        # its evidence on the run's ledger, zero semantic calls.
        lg.record(loop_id=n.loop_id, event="solution.loop.started",
                  solution=spec.solution_id, operation=n.operation,
                  mode=n.mode)
        arms = [_bind(registry[op], n.params) for op in ops]
        try:
            run = as_component_loop(
                f"solution loop {n.loop_id} ({n.operation})", arms[0],
                fallbacks=tuple(arms[1:]), inputs=value, ledger=lg)
        except LoopError as e:
            tr.append({"solution_loop": n.loop_id, "every_arm_failed": True})
            lg.record(loop_id=n.loop_id, event="solution.loop.completed",
                      solution=spec.solution_id, status="failed")
            raise SolutionError(
                f"solution loop {n.loop_id}: no operation in "
                f"{tuple(ops)} succeeded") from e
        value = run["value"]
        for a in run["attempts"]:
            if "failed" in a:
                tr.append({"solution_loop": n.loop_id, "operation": ops[a["index"]],
                           "failed": a["failed"][:120]})
        tr.append({"solution_loop": n.loop_id, "operation": ops[run["served_by"]],
                   "mode": n.mode, "component_loop_id": run["loop_id"],
                   "used_fallback": run["used_fallback"]})
        lg.record(loop_id=n.loop_id, event="solution.loop.completed",
                  solution=spec.solution_id, status="done",
                  component_loop_id=run["loop_id"],
                  served_by=ops[run["served_by"]])
    lg.record(loop_id=spec.solution_id, event="solution_finalized",
              solution=spec.solution_id, loops=len(spec.loops))
    return value


def self_test() -> dict:
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    reg = {
        "clean": lambda x, p: [v for v in x if v is not None],
        "scale": lambda x, p: [v * p.get("factor", 1) for v in x],
        "mean": lambda x, p: sum(x) / len(x),
        "crash": lambda x, p: (_ for _ in ()).throw(RuntimeError("boom")),
        "median": lambda x, p: sorted(x)[len(x) // 2],
    }
    data = [1, None, 2, 3, None, 4]

    # 1. a deterministic solution ships: same answer every run (the user's
    # "same result every time" setting, honored end to end).
    det = SolutionSpec("pipeline_a", allowed_modes=("deterministic",),
                       loops=(SolutionLoopSpec("n1", "clean"),
                              SolutionLoopSpec("n2", "scale",
                                           params={"factor": 2}),
                              SolutionLoopSpec("n3", "mean")))
    r1, r2 = run_solution(det, reg, data), run_solution(det, reg, data)
    check("deterministic_solution_is_repeatable", r1 == r2 == 5.0,
          f"two runs, same answer: {r1}")

    # 2. the shipping setting is a HARD gate: a deterministic-only solution
    # refuses a model-led LOOP at validation, before anything runs.
    bad = SolutionSpec("no_llm", allowed_modes=("deterministic",),
                       loops=(SolutionLoopSpec("n1", "clean",
                                           mode="non_deterministic"),))
    rep = bad.validate()
    check("shipping_mode_setting_is_a_hard_gate",
          not rep["valid"] and "hard gate" in rep["violations"][0])

    # 3. per-NODE fallback chains: a crashing operation falls to its declared
    # fallback, recorded; nothing silent.
    tr = []
    fb = SolutionSpec("with_fallback",
                      loops=(SolutionLoopSpec("n1", "clean"),
                             SolutionLoopSpec("n2", "crash",
                                          fallback_operations=("median",))))
    out = run_solution(fb, reg, data, trace=tr)
    check("node_fallback_chain_runs_and_records",
          out == 3 and any("failed" in t for t in tr)
          and tr[-1]["operation"] == "median")

    # 4. a solution of solutions: average and weighted_average combine members.
    m1 = SolutionSpec("m1", loops=(SolutionLoopSpec("a", "clean"),
                                   SolutionLoopSpec("b", "mean")))
    m2 = SolutionSpec("m2", loops=(SolutionLoopSpec("a", "clean"),
                                   SolutionLoopSpec("b", "median")))
    avg = SolutionSpec("blend", members=(m1, m2), ensemble="average")
    wavg = SolutionSpec("wblend", members=(m1, m2),
                        ensemble="weighted_average", weights=(3, 1))
    check("solution_of_solutions_averages_and_weights",
          run_solution(avg, reg, data) == 2.75
          and run_solution(wavg, reg, data) == 2.625,
          "members mean=2.5 and median=3 combine as declared")

    # 5. ordered_fallback: the first member that completes serves; a broken
    # first member is recorded, not fatal.
    broken = SolutionSpec("broken", loops=(SolutionLoopSpec("a", "crash"),))
    of = SolutionSpec("resilient", members=(broken, m2),
                      ensemble="ordered_fallback")
    tr5 = []
    out5 = run_solution(of, reg, data, trace=tr5)
    check("ordered_fallback_serves_first_working_member",
          out5 == 3 and any(t.get("member_failed") == "broken" for t in tr5)
          and any(t.get("served_by") == "m2" for t in tr5))

    # 6. a member never has more mode permissions than its composite (the
    # loop's permission grammar, applied to the artifact).
    wide = SolutionSpec("wide", allowed_modes=MODES,
                        loops=(SolutionLoopSpec("a", "clean"),))
    parent = SolutionSpec("narrow", allowed_modes=("deterministic",),
                          members=(wide, m2), ensemble="average")
    repp = parent.validate()
    check("member_modes_never_exceed_the_composite",
          not repp["valid"] and any("never has more" in x
                                    for x in repp["violations"]))

    # 7. specs are searchable Strings (round-trip through the store, faceted).
    from ..static_architecture.store_serve import SolverStore
    store = SolverStore(core_records=[det.to_record(), avg.to_record()])
    hits = store.search("solution average blend ensemble")
    check("solution_specs_are_searchable_strings",
          hits["hits"] and hits["hits"][0]["record_id"] == "solution.blend"
          and hits["hits"][0]["facets"].get("category") == "solution_spec")

    # 8. member-count bound + JSON serializability (a spec is a String).
    over = SolutionSpec("crowd", members=tuple(
        SolutionSpec(f"s{i}", loops=(SolutionLoopSpec("a", "clean"),))
        for i in range(7)), ensemble="average", max_members=5)
    check("member_bound_and_serializable",
          not over.validate()["valid"]
          and json.loads(json.dumps(_spec_dict(avg)))["ensemble"] == "average")

    # 9. THE LOOP-NODE RULE ON THE LIVE PATH: executing a solution runs EVERY
    # component as a PractitionerLoop on the run's own ledger — one
    # solution.loop.started/completed pair per component, one real loop
    # envelope behind each, and zero semantic calls for a deterministic ship.
    from ..loop.recursive_loop import LoopLedger
    from ..static_architecture.chronicle import to_canonical_events
    lg = LoopLedger()
    tr: list = []
    two = SolutionSpec("two.step", loops=(SolutionLoopSpec("prep", "clean"),
                                          SolutionLoopSpec("score", "mean")))
    out = run_solution(two, reg, [1, None, 3], trace=tr, ledger=lg)
    fams = [c["type"] for c in to_canonical_events(lg.events)]
    started = [e for e in lg.events
               if e.get("event") == "solution.loop.started"]
    envelopes = {e["loop_id"] for e in lg.events if e.get("event") == "init"}
    check("every_solution_component_executes_as_a_practitioner_loop",
          out == 2.0 and len(started) == 2 and len(envelopes) == 2
          and fams.count("solution.loop.started") == 2
          and fams.count("solution.loop.completed") == 2
          and all(r.get("component_loop_id") in envelopes
                  for r in tr if "component_loop_id" in r)
          and not [e for e in lg.events
                   if e.get("mode") in ("hybrid", "non_deterministic")],
          f"2 components -> 2 loop envelopes {sorted(envelopes)}, "
          "0 semantic modes")

    # 10. ADVERSARIAL: no path reaches a registry callable outside a loop.
    # A component whose primary crashes must still be served INSIDE its own
    # envelope by its declared fallback (recorded), and a component whose
    # whole chain fails must raise SolutionError with the failure on the
    # ledger — never a silent value and never a bare call.
    lg2 = LoopLedger()
    tr2: list = []
    saved = SolutionSpec("recovers", loops=(
        SolutionLoopSpec("risky", "crash", fallback_operations=("clean",)),))
    got = run_solution(saved, reg, [1, None, 3], trace=tr2, ledger=lg2)
    served = [r for r in tr2 if r.get("used_fallback")]
    doomed = SolutionSpec("doomed", loops=(
        SolutionLoopSpec("risky", "crash", fallback_operations=("crash",)),))
    failed_closed = False
    lg3 = LoopLedger()
    try:
        run_solution(doomed, reg, [1], ledger=lg3)
    except SolutionError:
        failed_closed = True
    check("fallbacks_and_failures_stay_inside_the_loop_envelope",
          got == [1, 3] and len(served) == 1
          and any(e.get("event") == "init" for e in lg2.events)
          and failed_closed
          and any(e.get("event") == "solution.loop.completed"
                  and e.get("status") == "failed" for e in lg3.events),
          "crash -> fallback served in-envelope; exhausted chain fails closed")

    passed = sum(1 for r in results if r["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
