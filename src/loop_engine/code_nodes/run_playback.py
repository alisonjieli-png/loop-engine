"""Run playback — replay a practitioner run and render it for humans.

Architectural role: Code Node system (reporting over ledgers + analyses).

Owns:
    - playback: a loop ledger -> an ordered, human-readable transcript
      (what happened, step by step, with modes, spawns, fallbacks, and
      terminal reasons — the "play back what the practitioner did" surface);
    - render_run_report: ONE canonical dict (ledger + run_analytics rollup +
      optional Solution Canvas) -> Mermaid loop-tree flowchart + HTML report
      with the du-style hotspot bars and token quantization.

Does not own:
    - the numbers (run_analytics.py computes them; this module renders);
    - the Solution Canvas graph (solution_compiler.render_canvas owns it;
      the run report EMBEDS it — the loop tree explains the build, the
      canvas explains the product).

Public entry points:
    - playback(events) -> list[str]
    - render_run_report(events, usage_log, trace, canvas=None,
                        title=...) -> {"canonical", "mermaid", "html"}

Side effects and authority: pure computation; the caller writes files.

Key invariants:
    - every view derives from the one canonical dict, never a UI-only truth;
    - unknowns render as "unknown", never as zero.

Verification: self_test() (folded into the package suite).
"""
from __future__ import annotations

import html as _html
import json

from .run_analytics import analyze_run, propose_edits


def playback(events) -> list:
    """The ordered transcript of a run — one line per meaningful event."""
    lines = []
    for e in events:
        ev, lid = e.get("event"), e.get("loop_id", "?")
        if ev == "init":
            lines.append(f"[{lid}] INIT depth={e.get('depth', 0)} "
                         f"{e.get('framework', '?')}/{e.get('power', '?')} — "
                         f"goal: {e.get('goal', '')[:80]}")
        elif ev == "spawn":
            lines.append(f"[{e.get('parent', '?')}] SPAWN -> {lid} — "
                         f"{e.get('goal', '')[:60]}")
        elif ev == "run_step":
            lines.append(f"[{lid}] {e.get('step', '?')} ({e.get('mode')}) "
                         f"conf={e.get('confidence')} — "
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


def _mermaid_tree(events, analysis) -> str:
    """The loop tree as a flowchart, pain-annotated."""
    lines = ["flowchart TD"]
    loops = analysis["loops"]
    for lid, row in loops.items():
        pain = next((h["pain"] for h in analysis["hotspots"]
                     if h["loop"] == lid), 0)
        label = (f"{lid}<br/>{row['steps']} steps · "
                 f"{row['semantic_calls']} calls · pain {pain}")
        lines.append(f'  {lid}["{label}"]')
    for e in events:
        if e.get("event") == "spawn":
            lines.append(f"  {e.get('parent')} --> {e.get('loop_id')}")
    return "\n".join(lines)


def render_run_report(events, usage_log=(), trace=None, *, canvas=None,
                      title: str = "Practitioner run") -> dict:
    """ONE canonical dict -> Mermaid + a self-contained HTML report."""
    analysis = analyze_run(events, usage_log, trace=trace)
    proposals = propose_edits(analysis)
    transcript = playback(events)
    mermaid = _mermaid_tree(events, analysis)
    canonical = {"record_type": "run_report/v1", "title": title,
                 "analysis": analysis, "proposals": proposals,
                 "transcript": transcript, "mermaid": mermaid,
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
        f'<li><b>{_html.escape(p["kind"])}</b> — '
        f'{_html.escape(p["proposal"])} <i>({_html.escape(p["evidence"])})'
        f'</i></li>' for p in proposals) or "<li>none</li>"
    lines = "\n".join(_html.escape(l) for l in transcript)
    body = f"""<h1>{_html.escape(title)}</h1>
<p class="k">{analysis['totals']['loops']} loops · {analysis['totals']['steps']}
steps · {analysis['totals']['semantic_calls']} semantic calls ·
{tok['prompt']}+{tok['eval']} provider tokens
({tok['calls_with_usage']} calls with usage)</p>
<h2>Troublesome loops (pain-ranked)</h2>{bars}
<h2>Loop tree</h2><pre class="mermaid">{_html.escape(mermaid)}</pre>
{'<h2>Solution canvas</h2><pre class="mermaid">' + _html.escape(canonical["canvas_mermaid"]) + '</pre>' if canonical["canvas_mermaid"] else ''}
<h2>Stuck signals</h2><ul>{stuck_rows}</ul>
<h2>Proposed edits (candidates — never self-applied)</h2><ul>{prop_rows}</ul>
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
                and f"{step}:child" not in context:
            return StepOutcome(output="need child", mode="deterministic",
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

    passed = sum(1 for r in results if r["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
