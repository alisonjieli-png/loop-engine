"""Run playback: replay a practitioner run and render it for humans.

Architectural role: Code Node system (reporting over ledgers + analyses).

Owns:
    - playback: a loop ledger -> an ordered, human-readable transcript
      (what happened, step by step, with modes, spawns, fallbacks, and
      terminal reasons: the "play back what the practitioner did" surface);
    - render_run_report: ONE canonical dict (ledger + run_analytics rollup +
      semantic relationship DAG + optional Solution Canvas) -> ownership and
      relationship Mermaid flowcharts + HTML report with the du-style hotspot
      bars and token quantization.

Does not own:
    - the numbers (run_analytics.py computes them; this module renders);
    - the Solution Canvas graph (solution_compiler.render_canvas owns it;
      the run report EMBEDS it: the loop tree explains the build, the
      canvas explains the product).

Public entry points:
    - playback(events) -> list[str]
    - render_run_report(events, usage_log, trace, canvas=None,
                        title=...) -> {"canonical", "mermaid", "html"}

Side effects and authority: pure computation; the caller writes files.

Key invariants:
    - every view derives from the one canonical dict, never a UI-only truth;
    - empty Loop IDs never become transcript lines or Mermaid vertices;
    - unknowns render as "unknown", never as zero.

Verification: self_test() (folded into the package suite).
"""
from __future__ import annotations

import html as _html
import json

from .run_analytics import (
    analyze_run, loop_relationship_dag, propose_edits)


_RELATIONSHIP_LABELS = {
    "starting": "Starting",
    "spawned_by": "Spawned by",
    "queried_by": "Queried by",
    "retrieved_by": "Retrieved by",
    "connected_from": "Connected from",
}


def _relationship_line(event: dict, loop_id: str) -> str:
    kind = str(event.get("relationship_kind", "") or "")
    if kind not in _RELATIONSHIP_LABELS:
        return ""
    endpoints = {
        "starting": (),
        "spawned_by": (event.get("spawned_by_loop_id", ""),),
        "queried_by": (event.get("queried_by_loop_id", ""),),
        "retrieved_by": (event.get("retrieved_by_loop_id", ""),),
        "connected_from": tuple(event.get("connected_from_loop_ids", ()) or ()),
    }[kind]
    related = ", ".join(str(value) for value in endpoints if value)
    suffix = f": {related}" if related else ""
    return f"[{loop_id}] RELATIONSHIP {_RELATIONSHIP_LABELS[kind]}{suffix}"


def playback(events) -> list:
    """The ordered transcript of a run: one line per meaningful event."""
    from ..core.run_history import as_ledger_events
    events = as_ledger_events(events)
    lines = []
    for e in events:
        ev = e.get("event")
        lid = str(e.get("loop_id", "") or "").strip()
        if not lid:
            continue
        if ev == "init":
            lines.append(f"[{lid}] INIT depth={e.get('depth', 0)} "
                         f"{e.get('framework', '?')}/{e.get('power', '?')}: "
                         f"goal: {e.get('goal', '')[:80]}")
            relationship = _relationship_line(e, lid)
            if relationship:
                lines.append(relationship)
        elif ev == "spawn":
            spawning_loop_id = str(
                e.get("spawning_loop_id", "")
                or e.get("spawned_by_loop_id", "") or "?")
            lines.append(f"[{spawning_loop_id}] SPAWN -> {lid}: "
                         f"{e.get('goal', '')[:60]}")
        elif ev == "run_step":
            lines.append(f"[{lid}] {e.get('step', '?')} ({e.get('mode')}) "
                         f"conf={e.get('confidence')}: "
                         f"{str(e.get('output', ''))[:70]}")
        elif ev == "fallback":
            lines.append(f"[{lid}] FALLBACK {e.get('step')}: "
                         f"{e.get('from_mode')} -> {e.get('to_mode')}")
        elif ev == "model_boundary_deferred":
            lines.append(f"[{lid}] MODEL BOUNDARY deferred at "
                         f"{e.get('step')}: retry next iteration")
        elif ev == "budget_stop":
            lines.append(f"[{lid}] BUDGET STOP after "
                         f"{e.get('model_calls')} model calls")
        elif ev == "terminal":
            lines.append(f"[{lid}] TERMINAL: {e.get('reason')}")
        elif ev == "cancel":
            lines.append(f"[{lid}] CANCELLED: {e.get('reason')}")
        elif ev == "spec":
            lines.append(f"[{lid}] SPEC digest {e.get('spec_digest', '')[:12]}…")
    return lines


def product_playback_lines(outcome: "dict | None") -> list[str]:
    """Render the saved product result without reinterpreting its claims."""
    if not outcome:
        return ["[run] PRODUCT OUTCOME NOT RECORDED (legacy run)"]
    verification = dict(outcome.get("verification") or {})
    verified = bool(verification.get("passed")
                    or verification.get("verdict") == "accept")
    lines = [
        f"[run] PRODUCT TERMINAL: {outcome.get('terminal_code', '')}",
        f"[run] PRODUCT VERIFICATION: "
        f"{'passed' if verified else 'not passed'}",
    ]
    if outcome.get("summary"):
        lines.append(f"[run] RESULT: {outcome['summary']}")
    if outcome.get("workspace"):
        lines.append(f"[run] WORKSPACE: {outcome['workspace']}")
    lines.extend(
        f"[run] ARTIFACT: {item.get('path', '')}"
        for item in outcome.get("artifacts", ()))
    lines.extend(
        f"[run] LIMITATION: {item}"
        for item in outcome.get("limitations", ()))
    return lines


def playback_saved_run(root: str, run_id: str) -> list[str]:
    """Play back one verified saved-run bundle without rerunning its work."""
    from ..core.run_history import load_saved_run_bundle
    bundle = load_saved_run_bundle(root, run_id)
    return [*playback(bundle.history.event_log),
            *product_playback_lines(bundle.outcome)]


def _mermaid_tree(events, analysis) -> str:
    """The loop tree as a flowchart, pain-annotated."""
    lines = ["flowchart TD"]
    loops = {str(loop_id): row for loop_id, row in analysis["loops"].items()
             if str(loop_id).strip()}
    identifiers = {loop_id: f"ownership_loop_{index}"
                   for index, loop_id in enumerate(sorted(loops))}
    for lid in sorted(loops):
        row = loops[lid]
        pain = next((h["pain"] for h in analysis["hotspots"]
                     if h["loop"] == lid), 0)
        label = (f"{_html.escape(lid)}<br/>{row['steps']} steps · "
                 f"{row['semantic_calls']} calls · pain {pain}")
        lines.append(f'  {identifiers[lid]}["{label}"]')
    for e in events:
        if e.get("event") == "spawn":
            spawning_loop_id = str(
                e.get("spawning_loop_id", "")
                or e.get("spawned_by_loop_id", "") or "").strip()
            spawned_loop_id = str(e.get("loop_id", "") or "").strip()
            if (spawning_loop_id in identifiers
                    and spawned_loop_id in identifiers
                    and spawning_loop_id != spawned_loop_id):
                lines.append(
                    f"  {identifiers[spawning_loop_id]} --> "
                    f"{identifiers[spawned_loop_id]}")
    return "\n".join(lines)


def render_run_report(events, usage_log=(), trace=None, *, canvas=None,
                      title: str = "Practitioner run") -> dict:
    """ONE canonical dict -> Mermaid + a self-contained HTML report."""
    from ..core.run_history import as_ledger_events
    events = as_ledger_events(events)
    analysis = analyze_run(events, usage_log, trace=trace)
    proposals = propose_edits(analysis)
    transcript = playback(events)
    mermaid = _mermaid_tree(events, analysis)
    relationships = loop_relationship_dag(events)
    canonical = {"record_type": "run_report/v1", "title": title,
                 "analysis": analysis, "proposals": proposals,
                 "transcript": transcript, "mermaid": mermaid,
                 "relationship_dag": relationships.as_dict(),
                 "relationship_mermaid": relationships.mermaid(),
                 "canvas_mermaid": (canvas or {}).get("mermaid", "")}

    tok = analysis["tokens"]
    max_pain = max((h["pain"] for h in analysis["hotspots"]), default=1) or 1
    bars = "\n".join(
        f'<div class="bar"><span class="lbl">{_html.escape(str(h["loop"]))}'
        f' · {h["steps"]} steps · {h["semantic_calls"]} calls</span>'
        f'<div class="fill" style="width:{max(2, int(100 * h["pain"] / max_pain))}%">'
        f'{h["pain"]}</div></div>'
        for h in analysis["hotspots"][:12])
    stuck_rows = "".join(f"<li>{_html.escape(json.dumps(s))}</li>"
                         for s in analysis["stuck"]) or "<li>none</li>"
    prop_rows = "".join(
        f'<li><b>{_html.escape(p["kind"])}</b>: '
        f'{_html.escape(p["proposal"])} <i>({_html.escape(p["evidence"])})'
        f'</i></li>' for p in proposals) or "<li>none</li>"
    lines = "\n".join(_html.escape(l) for l in transcript)
    body = f"""<h1>{_html.escape(title)}</h1>
<p class="k">{analysis['totals']['loops']} loops · {analysis['totals']['steps']}
steps · {analysis['totals']['semantic_calls']} semantic calls ·
{tok['prompt']}+{tok['eval']} provider tokens
({tok['calls_with_usage']} calls with usage)</p>
<h2>Troublesome loops (pain-ranked)</h2>{bars}
<h2>Loop ownership tree</h2><pre class="mermaid">{_html.escape(mermaid)}</pre>
<h2>Semantic relationship DAG</h2><pre class="mermaid">{_html.escape(canonical["relationship_mermaid"])}</pre>
{'<h2>Solution canvas</h2><pre class="mermaid">' + _html.escape(canonical["canvas_mermaid"]) + '</pre>' if canonical["canvas_mermaid"] else ''}
<h2>Stuck signals</h2><ul>{stuck_rows}</ul>
<h2>Proposed edits (candidates: never self-applied)</h2><ul>{prop_rows}</ul>
<h2>Transcript</h2><pre class="tx">{lines}</pre>"""
    canonical["html"] = body
    return canonical


def self_test() -> dict:
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    from ..loop.recursive_loop import Loop, LoopConfig, StepOutcome, \
        default_handler

    def handler(loop, step, context):
        if step == "research" and loop.depth == 0 \
                and f"{step}:spawned" not in context:
            return StepOutcome(output="need spawned", mode="deterministic",
                               spawn_goal="sub-research")
        if step == "decide":
            return StepOutcome(output="picked", mode="hybrid", confidence=0.7)
        return default_handler(loop, step, context)

    lp = Loop("playback me", LoopConfig(framework="custom",
                                        custom_steps=("orient", "research",
                                                      "decide", "act"),
                                        power="deep"))
    lp.run(handler=handler)
    usage = [{"prompt_tokens": 50, "eval_tokens": 200}]

    # 1. the transcript replays init, spawn, steps, and terminal in order.
    tx = playback(lp.ledger.events)
    check("transcript_replays_the_run_in_order",
          tx[0].startswith(f"[{lp.loop_id}] INIT")
          and any("SPAWN ->" in l for l in tx)
          and any("(hybrid)" in l for l in tx)
          and any("TERMINAL: done" in l for l in tx),
          f"{len(tx)} transcript lines")

    # 2. the report derives every view from ONE canonical dict: mermaid tree
    # with pain annotations, hotspot bars, tokens, proposals, transcript.
    rep = render_run_report(lp.ledger.events, usage, title="test run")
    check("report_renders_from_one_canonical_truth",
          rep["mermaid"].startswith("flowchart TD")
          and "pain" in rep["mermaid"]
          and "50+200 provider tokens" in rep["html"]
          and "Troublesome loops" in rep["html"]
          and rep["analysis"]["totals"]["loops"] == 2
          and rep["transcript"] == tx)

    # 3. the canvas embeds when supplied (build vs product, side by side).
    from .solution_canvas import SolutionLoopSpec, SolutionSpec
    from .solution_compiler import compile_solution, render_canvas
    reg = {"clean": lambda x, p: x, "mean": lambda x, p: 1.0}
    plan = compile_solution(
        SolutionSpec("s", loops=(SolutionLoopSpec("a", "clean"),
                                 SolutionLoopSpec("b", "mean"))), reg)["plan"]
    rep2 = render_run_report(lp.ledger.events, usage,
                             canvas=render_canvas(plan))
    check("solution_canvas_embeds_beside_the_loop_tree",
          "Solution canvas" in rep2["html"]
          and "flowchart TD" in rep2["canvas_mermaid"])

    # 4. Loaded saved-run events use a different storage envelope. Playback
    # and analytics must use the shared adapter rather than render an empty run.
    import tempfile
    from ..core.run_history import RunHistory, bind_product_outcome
    ch = RunHistory.from_ledger(lp.ledger.events, run_id="playback-saved",
                               usage_log=usage)
    ch.commit()
    saved_tx = playback(ch.event_log)
    saved_report = render_run_report(ch.event_log, title="saved playback")
    check("persisted_run_history_plays_without_reexecution",
          saved_tx and any("INIT" in line for line in saved_tx)
          and any("TERMINAL" in line for line in saved_tx)
          and saved_report["analysis"]["totals"]["loops"] >= 2
          and saved_report["analysis"]["tokens"]["prompt"] == 50,
          "stored events produced transcript, tree, and provider usage")
    with tempfile.TemporaryDirectory() as saved_root:
        ch.save(saved_root)
        bind_product_outcome(saved_root, "playback-saved", {
            "record_type": "solve_outcome/v3", "run_id": "playback-saved",
            "terminal_code": "COMPLETED_VERIFIED",
            "status": "COMPLETED_VERIFIED", "solved": True,
            "summary": "Playback product.", "failure_code": "",
            "verification": {"passed": True},
            "artifacts": [{"path": "/tmp/result.txt"}],
            "workspace": "/tmp", "limitations": [],
            "selected_canvas": {},
        })
        product_tx = playback_saved_run(saved_root, "playback-saved")
    check("saved_playback_ends_with_the_product_terminal_and_artifacts",
          any("PRODUCT TERMINAL: COMPLETED_VERIFIED" in line
              for line in product_tx)
          and product_tx[-1] == "[run] ARTIFACT: /tmp/result.txt")

    relationship_events = (
        {"event": "init", "loop_id": "p", "goal": "practice",
         "role": "practitioner", "profile_id": "practitioner.solver",
         "relationship_kind": "starting"},
        {"event": "init", "loop_id": "s", "goal": "spawned work",
         "relationship_kind": "spawned_by", "spawned_by_loop_id": "p"},
        {"event": "spawn", "loop_id": "s", "spawning_loop_id": "p",
         "relationship_kind": "spawned_by", "spawned_by_loop_id": "p"},
        {"event": "init", "loop_id": "q", "goal": "query",
         "relationship_kind": "queried_by", "queried_by_loop_id": "p"},
        {"event": "init", "loop_id": "i", "goal": "item",
         "relationship_kind": "retrieved_by", "retrieved_by_loop_id": "q"},
        {"event": "init", "loop_id": "adapter", "goal": "adapt",
         "relationship_kind": "starting"},
        {"event": "init", "loop_id": "z", "goal": "solution",
         "relationship_kind": "connected_from",
         "connected_from_loop_ids": ("p", "adapter")},
        {"event": "custom", "loop_id": ""},
    )
    adapted_history = RunHistory.from_ledger(
        relationship_events, run_id="relationship-playback")
    relationship_report = render_run_report(adapted_history.event_log)
    relationship_transcript = relationship_report["transcript"]
    check("playback_and_report_cover_all_five_relationships_after_adapter",
          relationship_report["relationship_dag"]["complete"] is True
          and len(relationship_report["relationship_dag"]["vertices"]) == 6
          and len(relationship_report["relationship_dag"]["edges"]) == 5
          and all(any(label in line for line in relationship_transcript)
                  for label in ("Starting", "Spawned by", "Queried by",
                                "Retrieved by", "Connected from"))
          and "Semantic relationship DAG" in relationship_report["html"]
          and '["<br/>' not in relationship_report["mermaid"]
          and '["<br/>' not in relationship_report["relationship_mermaid"])

    broken = render_run_report((
        {"event": "custom", "loop_id": ""},
        {"event": "init", "loop_id": "visible",
         "relationship_kind": "retrieved_by",
         "retrieved_by_loop_id": "absent"},
    ))
    check("playback_omits_blank_ids_and_reports_missing_relationship_endpoints",
          all("[]" not in line and "[?]" not in line
              for line in broken["transcript"])
          and len(broken["relationship_dag"]["vertices"]) == 1
          and broken["relationship_dag"]["complete"] is False
          and broken["relationship_dag"]["diagnostics"][0]["code"]
              == "relationship_endpoint_unknown"
          and "absent[" not in broken["relationship_mermaid"])

    passed = sum(1 for r in results if r["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
