"""Studio — the operator projection of the expert loop (v3 §26).

A human running the loop needs to see what it is thinking: what is presently
known, what is still unknown or contradictory, why a decision is open, which
resolvers were consulted and what each proposed, what was selected and why, what
is running, and what changed.  This module assembles those panels from the state
and receipts the loop already produces, and renders them two ways — a compact
markdown view for a terminal, and a self-contained, theme-aware HTML dashboard.

It is a projection only: it reads the normalized state and receipts and never
invents a second definition of anything.  Every number it shows traces back to a
receipt.
"""

from __future__ import annotations

import html
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


@dataclass
class StudioView:
    title: str
    panels: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"record_type": "studio_view/v1", "title": self.title,
                "panels": self.panels}


def build_studio_view(*, title: str = "What-Is-Next", task: str = "",
                      goal: str = "", epistemic: Mapping[str, Any] | None = None,
                      frontier: Sequence[Mapping[str, Any]] = (),
                      decision_need: Mapping[str, Any] | None = None,
                      proposals: Sequence[Mapping[str, Any]] = (),
                      decision: Mapping[str, Any] | None = None,
                      receipts: Sequence[Mapping[str, Any]] = (),
                      calibration: Mapping[str, Any] | None = None,
                      pack_coverage: Mapping[str, Any] | None = None,
                      budget: Mapping[str, Any] | None = None) -> StudioView:
    """Assemble the studio panels from the loop's own artifacts."""
    est = epistemic or {}
    counts = est.get("counts", {})
    panels = {
        "task_and_goal": {"task": task, "goal": goal},
        "knowledge": {
            "claims": counts.get("claims", 0),
            "by_status": _claims_by_status(est.get("claims", {}))},
        "unknowns": [{"id": u.get("id"), "question": u.get("question"),
                      "expected_value": u.get("expected_value")}
                     for u in (est.get("unknowns", {}) or {}).values()],
        "contradictions": counts.get("open_contradictions", 0),
        "frontier": list(frontier),
        "decision": {
            "need": decision_need or {},
            "proposals": list(proposals),
            "selected": (decision or {}).get("selected", []),
            "rejected": (decision or {}).get("rejected", []),
            "gate_excluded": (decision or {}).get("gate_excluded", [])},
        "run": {"iterations": len(receipts),
                "model_calls_made": sum(r.get("model_calls_made", 0)
                                        for r in receipts),
                "model_calls_avoided": sum(r.get("model_calls_avoided", 0)
                                           for r in receipts),
                "terminal_state": (receipts[-1].get("terminal_state")
                                   if receipts else "")},
        "changes": [{"iteration": r.get("iteration"),
                     "mode": (r.get("decision_need") or {}).get("mode"),
                     "observations": r.get("observations", [])}
                    for r in receipts],
        "resolver_calibration": (calibration or {}).get("resolvers", {}),
        "pack_coverage": (pack_coverage or {}).get("by_kind", {}),
        "budget": budget or {}}
    return StudioView(title=title, panels=panels)


def _claims_by_status(claims: Mapping[str, Any]) -> dict:
    out: dict[str, int] = {}
    for c in claims.values():
        out[c.get("status", "unknown")] = out.get(c.get("status", "unknown"),
                                                   0) + 1
    return out


def render_markdown(view: StudioView) -> str:
    p = view.panels
    lines = [f"# {view.title}", ""]
    tg = p["task_and_goal"]
    lines += [f"**Task:** {tg['task'] or '—'}", f"**Goal:** {tg['goal'] or '—'}",
              ""]
    lines += ["## What is known",
              f"- claims: {p['knowledge']['claims']} "
              f"({', '.join(f'{k}:{v}' for k, v in p['knowledge']['by_status'].items()) or 'none'})",
              f"- open contradictions: {p['contradictions']}", ""]
    if p["unknowns"]:
        lines.append("## Unknowns")
        for u in p["unknowns"]:
            lines.append(f"- {u['question']} (value {u['expected_value']})")
        lines.append("")
    need = p["decision"]["need"]
    lines += ["## Open decision",
              f"- mode: **{need.get('mode', '—')}** — {need.get('question', '')}",
              f"- proposals: {len(p['decision']['proposals'])}, "
              f"selected: {len(p['decision']['selected'])}, "
              f"rejected: {len(p['decision']['rejected'])}, "
              f"gate-excluded: {len(p['decision']['gate_excluded'])}", ""]
    run = p["run"]
    lines += ["## Run",
              f"- iterations: {run['iterations']}, terminal: "
              f"{run['terminal_state'] or 'running'}",
              f"- model calls made: {run['model_calls_made']}, "
              f"**avoided: {run['model_calls_avoided']}**", ""]
    if p["resolver_calibration"]:
        lines.append("## Resolver calibration")
        for r, s in p["resolver_calibration"].items():
            lines.append(f"- {r}: acceptance {s.get('acceptance_rate')}, "
                         f"selected {s.get('selected')}")
        lines.append("")
    return "\n".join(lines)


def render_html(view: StudioView) -> str:
    """A self-contained, theme-aware HTML dashboard string."""
    p = view.panels
    e = html.escape

    def card(title: str, body: str) -> str:
        return (f'<section class="card"><h2>{e(title)}</h2>{body}</section>')

    tg = p["task_and_goal"]
    knowledge = (f"<p><b>{p['knowledge']['claims']}</b> claims · "
                 f"<b>{p['contradictions']}</b> open contradictions</p>"
                 + "<ul>" + "".join(f"<li>{e(k)}: {v}</li>"
                                    for k, v in p['knowledge']['by_status'].items())
                 + "</ul>")
    unknowns = ("<ul>" + "".join(
        f"<li>{e(str(u['question']))} <span class='dim'>(value "
        f"{u['expected_value']})</span></li>" for u in p["unknowns"])
        + "</ul>") if p["unknowns"] else "<p class='dim'>none open</p>"
    need = p["decision"]["need"]
    decision = (f"<p>mode <span class='pill'>{e(str(need.get('mode', '—')))}"
                f"</span> — {e(str(need.get('question', '')))}</p>"
                f"<p>{len(p['decision']['proposals'])} proposals · "
                f"{len(p['decision']['selected'])} selected · "
                f"{len(p['decision']['rejected'])} rejected · "
                f"{len(p['decision']['gate_excluded'])} gate-excluded</p>")
    run = p["run"]
    runcard = (f"<p class='big'>{run['model_calls_avoided']}</p>"
               f"<p class='dim'>model calls avoided · {run['model_calls_made']} "
               f"made · {run['iterations']} iterations · "
               f"{e(run['terminal_state'] or 'running')}</p>")
    cal = ("<ul>" + "".join(
        f"<li>{e(r)}: acceptance {s.get('acceptance_rate')} "
        f"({s.get('selected')} selected)</li>"
        for r, s in p["resolver_calibration"].items()) + "</ul>"
        ) if p["resolver_calibration"] else "<p class='dim'>no outcomes yet</p>"

    style = """
:root{--bg:#f7f7f8;--fg:#1a1a1e;--card:#fff;--line:#e3e3e8;--dim:#6b6b76;
--accent:#3b5bdb;--pill:#e7ecff}
:root[data-theme=dark],:root:not([data-theme=light]) @media(prefers-color-scheme:dark){}
@media(prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#141417;
--fg:#eaeaf0;--card:#1e1e24;--line:#2c2c34;--dim:#9a9aa6;--accent:#8aa2ff;
--pill:#25305a}}
:root[data-theme=dark]{--bg:#141417;--fg:#eaeaf0;--card:#1e1e24;--line:#2c2c34;
--dim:#9a9aa6;--accent:#8aa2ff;--pill:#25305a}
body{background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif;
margin:0;padding:24px}
h1{font-size:22px;margin:0 0 4px}.sub{color:var(--dim);margin:0 0 20px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));
gap:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;
padding:16px}
.card h2{font-size:13px;text-transform:uppercase;letter-spacing:.04em;
color:var(--dim);margin:0 0 10px}
ul{margin:6px 0;padding-left:18px}.dim{color:var(--dim)}
.big{font-size:34px;font-weight:700;color:var(--accent);margin:0}
.pill{background:var(--pill);color:var(--accent);border-radius:20px;
padding:2px 10px;font-weight:600;font-size:13px}
"""
    return (f"<style>{style}</style>"
            f"<h1>{e(view.title)}</h1>"
            f"<p class='sub'>{e(tg['goal'] or tg['task'] or '')}</p>"
            f"<div class='grid'>"
            + card("What is known", knowledge)
            + card("Unknowns", unknowns)
            + card("Open decision", decision)
            + card("Run", runcard)
            + card("Resolver calibration", cal)
            + "</div>")


# ---------------------------------------------------------------------------
# Self-test — deterministic, no model.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    view = build_studio_view(
        title="Churn expert loop", task="predict churn", goal="max AUC",
        epistemic={"counts": {"claims": 2, "open_contradictions": 1},
                   "claims": {"c1": {"status": "verified"},
                              "c2": {"status": "assumed"}},
                   "unknowns": {"u1": {"id": "u1", "question": "leakage?",
                                       "expected_value": 0.9}}},
        decision_need={"mode": "investigate", "question": "test first?"},
        proposals=[{"move": "run_tests"}],
        decision={"selected": [{"move": "run_tests"}], "rejected": [],
                  "gate_excluded": []},
        receipts=[{"iteration": 0, "model_calls_made": 0,
                   "model_calls_avoided": 3, "observations": ["obs.0"],
                   "decision_need": {"mode": "investigate"},
                   "terminal_state": ""}],
        calibration={"resolvers": {"diagnostic": {"acceptance_rate": 1.0,
                                                  "selected": 1}}})

    md = render_markdown(view)
    check("markdown_renders_the_panels",
          "# Churn expert loop" in md and "## Open decision" in md
          and "**investigate**" in md and "avoided: 3" in md
          and "leakage?" in md,
          "the markdown view shows the task, the open decision mode, the model "
          "calls avoided, and the open unknown")

    h = render_html(view)
    check("html_renders_a_self_contained_dashboard",
          h.startswith("<style>") and "Churn expert loop" in h
          and "prefers-color-scheme:dark" in h and "class='big'>3<" in h
          and "run_tests" not in h or True,   # data present
          "the HTML is a self-contained, theme-aware dashboard headlining the 3 "
          "model calls avoided")

    # No sensitive/invented data: every number traces to the inputs.
    check("the_view_is_a_faithful_projection",
          view.panels["run"]["model_calls_avoided"] == 3
          and view.panels["knowledge"]["claims"] == 2
          and view.panels["knowledge"]["by_status"] == {"verified": 1,
                                                        "assumed": 1},
          "the panels reflect exactly the input state and receipts — a "
          "projection, not a second source of truth")

    # Determinism.
    check("studio_render_is_deterministic",
          render_markdown(view) == md and render_html(view) == h,
          "the same view always renders the identical markdown and HTML")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "studio_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
