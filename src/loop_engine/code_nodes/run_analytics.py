"""Run analytics — quantize what the practitioner actually did, find the pain.

Architectural role: Code Node system (behavioral analysis over ledgers).

Owns:
    - analyze_run: one loop ledger (+ provider usage log) -> per-loop and
      per-step rollups: iterations, semantic calls, tokens, wall seconds,
      fallbacks, deferrals, spawns — the du-style "which loops are most
      troublesome" numbers;
    - hotspots: the ranked worst offenders by tokens / calls / time /
      fallbacks;
    - stuck detection: repeated identical steps, fallback chains, budget
      stops, empty model outputs;
    - digestibility: model outputs that produced NO distilled keys or staged
      candidates (spend that never became reusable memory);
    - marginal-call analysis across paired records (cold vs warm, mode
      arms): did MORE calls actually buy quality?
    - propose_edits: per-hotspot improvement proposals in the housekeeping
      candidate vocabulary (staged only — never self-applied).

Does not own:
    - rendering (run_playback.py turns these numbers into transcripts,
      Mermaid, and HTML);
    - promotion (proposals are candidates through the one gate).

Public entry points:
    - analyze_run(events, usage_log=(), trace=None) -> dict
    - compare_run_records(pairs) -> dict     # marginal value of calls
    - propose_edits(analysis) -> list[dict]

Side effects and authority: pure computation over dicts; no I/O.

Key invariants:
    - a zero is a measurement only when the events could have shown nonzero;
      absent timestamps/usage yield "unknown", never fabricated numbers;
    - proposals cite the exact loop/step evidence that produced them.

Verification: self_test() (folded into the package suite).
"""
from __future__ import annotations

from collections import Counter, defaultdict

SEMANTIC_MODES = ("hybrid", "non_deterministic")


def analyze_run(events, usage_log=(), trace: "dict | None" = None) -> dict:
    """One canonical rollup of a loop ledger (the shared-tree history)."""
    from ..static_architecture.run_history import as_ledger_events
    events = as_ledger_events(events)
    per_loop: dict = defaultdict(lambda: {
        "steps": 0, "semantic_calls": 0, "fallbacks": 0, "deferrals": 0,
        "budget_stops": 0, "spawned": 0, "empty_outputs": 0,
        "wall_seconds": None, "first_ts": None, "last_ts": None,
        "step_counts": Counter(), "goal": "", "depth": 0})
    stored_usage = []
    for e in events:
        lid = e.get("loop_id")
        if lid is None:
            continue
        row = per_loop[lid]
        ts = e.get("ts")
        if ts is not None:
            row["first_ts"] = ts if row["first_ts"] is None \
                else min(row["first_ts"], ts)
            row["last_ts"] = ts if row["last_ts"] is None \
                else max(row["last_ts"], ts)
        ev = e.get("event")
        if ev == "init":
            row["goal"] = e.get("goal", "")
            row["depth"] = e.get("depth", 0)
        elif ev == "run_step":
            row["steps"] += 1
            row["step_counts"][e.get("step", "?")] += 1
            if e.get("mode") in SEMANTIC_MODES:
                row["semantic_calls"] += 1
            if not e.get("output"):
                row["empty_outputs"] += 1
        elif ev == "fallback":
            row["fallbacks"] += 1
        elif ev == "model_boundary_deferred":
            row["deferrals"] += 1
        elif ev == "budget_stop":
            row["budget_stops"] += 1
        elif ev == "spawn":
            spawning_loop_id = str(
                e.get("spawning_loop_id", "")
                or e.get("spawned_by_loop_id", "") or "?")
            per_loop[spawning_loop_id]["spawned"] += 1
        elif ev == "model_invocation":
            stored_usage.append({"prompt_tokens": e.get("prompt_tokens", 0),
                                 "eval_tokens": e.get("eval_tokens", 0)})
    for row in per_loop.values():
        if row["first_ts"] is not None and row["last_ts"] is not None:
            row["wall_seconds"] = round(row["last_ts"] - row["first_ts"], 3)
        row["step_counts"] = dict(row["step_counts"])

    tokens = {"prompt": 0, "eval": 0, "calls_with_usage": 0}
    for u in (usage_log or stored_usage):
        tokens["prompt"] += int(u.get("prompt_tokens", 0) or 0)
        tokens["eval"] += int(u.get("eval_tokens", 0) or 0)
        tokens["calls_with_usage"] += 1

    # stuck signals: a step resolved more than twice in one loop, any budget
    # stop, any fallback chain, any empty model output.
    stuck = []
    for lid, row in per_loop.items():
        for step, n in row["step_counts"].items():
            if n > 2:
                stuck.append({"loop": lid, "signal": "repeated_step",
                              "step": step, "count": n})
        if row["budget_stops"]:
            stuck.append({"loop": lid, "signal": "budget_stop"})
        if row["fallbacks"] >= 2:
            stuck.append({"loop": lid, "signal": "fallback_chain",
                          "count": row["fallbacks"]})
        if row["empty_outputs"]:
            stuck.append({"loop": lid, "signal": "empty_model_output",
                          "count": row["empty_outputs"]})

    # digestibility: semantic spend that produced no reusable memory.  From
    # the trace: a research answer whose decide step fell back to the default
    # key means the advice did not distill.
    digest = {"semantic_calls": sum(r["semantic_calls"]
                                    for r in per_loop.values()),
              "undigested": 0, "notes": []}
    if trace:
        keys = trace.get("proposed_keys") or []
        if digest["semantic_calls"] and keys == ["hist_gradient_boosting"]:
            digest["undigested"] += 1
            digest["notes"].append(
                "the model's research answer distilled to nothing beyond the "
                "default estimator — spend without reusable memory")

    # the du-style hotspot ranking: troublesomeness = weighted pain.
    def pain(row):
        return (row["semantic_calls"] * 3 + row["fallbacks"] * 2
                + row["deferrals"] * 2 + row["budget_stops"] * 3
                + row["empty_outputs"] * 2
                + (row["wall_seconds"] or 0) / 10)
    hotspots = sorted(
        ({"loop": lid, **row, "pain": round(pain(row), 3)}
         for lid, row in per_loop.items()),
        key=lambda r: r["pain"], reverse=True)

    return {"record_type": "run_analysis/v1",
            "loops": dict(per_loop), "hotspots": hotspots,
            "tokens": tokens, "stuck": stuck, "digestibility": digest,
            "totals": {"loops": len(per_loop),
                       "steps": sum(r["steps"] for r in per_loop.values()),
                       "semantic_calls": digest["semantic_calls"],
                       "fallbacks": sum(r["fallbacks"]
                                        for r in per_loop.values())}}


def compare_run_records(pairs) -> dict:
    """Marginal value of calls across labeled arms of the SAME task:
    pairs = [(label, {"calls": n, "score": s, "wall": w}), ...].
    Answers 'did more calls buy quality?' — honestly, one comparison per
    pair, never a generalized claim."""
    rows = sorted(((label, d) for label, d in pairs),
                  key=lambda t: t[1].get("calls", 0))
    findings = []
    for (la, a), (lb, b) in zip(rows, rows[1:]):
        dc = b.get("calls", 0) - a.get("calls", 0)
        ds = (b.get("score") or 0) - (a.get("score") or 0)
        findings.append({
            "from": la, "to": lb, "extra_calls": dc,
            "score_delta": round(ds, 6),
            "verdict": ("calls bought quality" if dc > 0 and ds > 0 else
                        "calls bought nothing measurable" if dc > 0 else
                        "no extra calls")})
    return {"record_type": "marginal_calls/v1", "arms": dict(rows),
            "findings": findings}


def propose_edits(analysis: dict) -> list:
    """Per-hotspot improvement proposals (staged candidates, cited)."""
    out = []
    for h in analysis["hotspots"]:
        if h["pain"] <= 0:
            continue
        if h["semantic_calls"]:
            out.append({"loop": h["loop"], "kind": "code_node",
                        "proposal": "serve this loop's semantic step from a "
                                    "code node or the advice store "
                                    f"({h['semantic_calls']} calls here)",
                        "evidence": f"loop {h['loop']} pain {h['pain']}"})
        if h["fallbacks"] or h["deferrals"]:
            out.append({"loop": h["loop"], "kind": "bias",
                        "proposal": "reorder the mode waterfall or add a "
                                    "precondition — this loop fell back "
                                    f"{h['fallbacks']}x, deferred "
                                    f"{h['deferrals']}x",
                        "evidence": f"loop {h['loop']}"})
        if h["budget_stops"]:
            out.append({"loop": h["loop"], "kind": "config",
                        "proposal": "raise power or cut steps: the budget "
                                    "stopped this loop before completion",
                        "evidence": f"loop {h['loop']}"})
    for s in analysis["stuck"]:
        if s["signal"] == "repeated_step":
            out.append({"loop": s["loop"], "kind": "logic_rule",
                        "proposal": f"step '{s['step']}' resolved "
                                    f"{s['count']}x — add a completion "
                                    "precondition or distill a rule",
                        "evidence": f"loop {s['loop']}"})
    return out


def self_test() -> dict:
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    from ..loop.recursive_loop import Loop, LoopConfig, StepOutcome, \
        default_handler

    # A real run with a semantic step, a fallback, and a spawned Loop.
    def handler(loop, step, context):
        if step == "research" and loop.depth == 0:
            if f"{step}:spawned" not in context:
                return StepOutcome(output="need spawned", mode="deterministic",
                                   spawn_goal="sub-research")
            return StepOutcome(output="advice", mode="hybrid", confidence=0.7)
        if step == "act" and "act" not in context:
            return StepOutcome(output="err", mode="deterministic", failed=True)
        return default_handler(loop, step, context)

    lp = Loop("analyze me", LoopConfig(framework="custom",
                                       custom_steps=("orient", "research",
                                                     "research", "research",
                                                     "act", "verify"),
                                       power="deep"))
    lp.run(handler=handler)
    usage = [{"prompt_tokens": 100, "eval_tokens": 400}]
    a = analyze_run(lp.ledger.events, usage,
                    trace={"proposed_keys": ["hist_gradient_boosting"]})

    # 1. the rollup quantizes calls, tokens, spawns, fallbacks, and wall time.
    root = a["loops"][lp.loop_id]
    check("rollup_quantizes_the_run",
          a["totals"]["semantic_calls"] >= 1
          and a["tokens"] == {"prompt": 100, "eval": 400,
                              "calls_with_usage": 1}
          and root["spawned"] == 1 and root["fallbacks"] >= 1
          and isinstance(root["wall_seconds"], float),
          f"root: {root['steps']} steps, {root['semantic_calls']} calls, "
          f"{root['wall_seconds']}s")

    # 2. hotspots rank by pain; the root (calls+fallbacks) outranks the
    # clean spawned Loop.
    check("hotspots_rank_troublesome_loops_first",
          a["hotspots"][0]["loop"] == lp.loop_id
          and a["hotspots"][0]["pain"] > a["hotspots"][-1]["pain"])

    # 3. stuck + digestibility signals fire on real shapes.
    check("stuck_and_digestibility_signals_fire",
          any(s["signal"] == "repeated_step" and s["step"] == "research"
              for s in a["stuck"])
          and a["digestibility"]["undigested"] == 1,
          "repeated research + advice that distilled to the default")

    # 4. proposals cite their evidence and stay in candidate vocabulary.
    props = propose_edits(a)
    check("proposals_are_cited_candidates",
          props and all(p.get("evidence") for p in props)
          and any(p["kind"] == "code_node" for p in props)
          and any(p["kind"] == "logic_rule" for p in props))

    # 5. marginal-call comparison answers 'did calls buy quality?' honestly.
    cmp = compare_run_records([
        ("deterministic", {"calls": 0, "score": 0.8294}),
        ("hybrid", {"calls": 1, "score": 0.8294}),
        ("model_led", {"calls": 1, "score": 0.8339})])
    verdicts = [f["verdict"] for f in cmp["findings"]]
    check("marginal_call_analysis_is_honest",
          "calls bought nothing measurable" in verdicts[0]
          and len(cmp["findings"]) == 2,
          f"{verdicts}")

    passed = sum(1 for r in results if r["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
