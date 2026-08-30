"""Loop reports: turn a run's ledger into something a person can read.

Architectural role: Code Node system (the reporting projection over a run).

A run emits a chain of events. That chain is complete and checkable, and it is
also unreadable: a few hundred JSON records with nesting expressed only through
spawning Loop IDs. This module answers the question a person has after a run
: *what did the loop do, what did it cost, and where did it spend its time?* :
in three renderings over the SAME projection:

    text      an indented tree for a terminal
    markdown  a report to paste into an issue or a pull request
    html      a self-contained page, no assets, no network

The rule that keeps a report honest, and the reason this module is small:

    A REPORT PROJECTS; IT NEVER RE-DERIVES.

    Every number here comes from the ledger the run actually emitted. Nothing
    is recomputed from a different source, nothing is estimated, and a value
    the ledger does not carry is shown as unknown rather than filled in. A
    report that quietly recalculates is a second source of truth, and the two
    drift.

Token counts are provider-reported and carry the provider that produced them,
because a count with no provider attached cannot be checked later.

Owns:
    - LoopReport: ownership tree, semantic relationship DAG, per-loop
      rollups, cost, and timings;
    - render_text / render_markdown / render_html;
    - report_from_ledger() / report_from_run(): the two entry points.

Does not own:
    - the ledger or its vocabulary (run_history, event_vocabulary), the runtime
      (recursive_loop), or the Studio server's live projections.

Key invariants:
    - every figure traces to a ledger event; nothing is estimated;
    - an empty run reports an empty run rather than a plausible-looking one;
    - model cost is attributed per provider, or reported as unknown;
    - semantic edges come from current relationship fields on canonical events;
    - invalid relationships remain visible without anonymous graph vertices;
    - the rendered HTML is self-contained (no external assets).

Verification: self_test(): tree shape from real nesting, cost attribution,
the empty-run path, unknown-vs-zero honesty, and HTML self-containment.
"""

from __future__ import annotations

import html as _html
import json
from dataclasses import dataclass, field

from ..core.run_history import to_canonical_events
from .run_analytics import LoopRelationshipDag, loop_relationship_dag

#: Events that open and close a loop, used to build the tree and the timings.
_OPEN = "init"
_TERMINAL_EVENTS = ("terminal", "loop.completed", "loop.failed")


@dataclass
class LoopReportRecord:
    """One loop in the tree, with what it did and what it cost."""
    loop_id: str
    goal: str = ""
    spawning_loop_id: str = ""
    depth: int = 0
    mode: str = ""
    steps: list = field(default_factory=list)
    events: int = 0
    model_calls: int = 0
    prompt_tokens: int = 0
    eval_tokens: int = 0
    providers: list = field(default_factory=list)
    started: "float | None" = None
    ended: "float | None" = None
    outcome: str = ""
    spawned_loops: list = field(default_factory=list)

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.eval_tokens

    @property
    def seconds(self) -> "float | None":
        """None: not 0.0: when the ledger carries no timestamps. A zero here
        would read as an instantaneous loop, which is a different claim."""
        if self.started is None or self.ended is None:
            return None
        return round(self.ended - self.started, 3)

    def as_dict(self) -> dict:
        return {"loop_id": self.loop_id, "goal": self.goal,
                "spawning_loop_id": self.spawning_loop_id,
                "depth": self.depth, "mode": self.mode,
                "steps": list(self.steps), "events": self.events,
                "model_calls": self.model_calls,
                "prompt_tokens": self.prompt_tokens,
                "eval_tokens": self.eval_tokens,
                "total_tokens": self.total_tokens,
                "providers": list(self.providers), "seconds": self.seconds,
                "outcome": self.outcome,
                "spawned_loops": [c.as_dict() for c in self.spawned_loops]}


@dataclass
class LoopReport:
    """The whole run, projected."""
    run_id: str = ""
    starting_loops: list = field(default_factory=list)
    by_id: dict = field(default_factory=dict)
    total_events: int = 0
    families: dict = field(default_factory=dict)
    chain_intact: "bool | None" = None
    product_outcome: dict = field(default_factory=dict)
    relationship_dag: LoopRelationshipDag = field(
        default_factory=LoopRelationshipDag)

    @property
    def loops(self) -> int:
        return len(self.by_id)

    @property
    def model_calls(self) -> int:
        return sum(n.model_calls for n in self.by_id.values())

    @property
    def total_tokens(self) -> int:
        return sum(n.total_tokens for n in self.by_id.values())

    def cost_by_provider(self) -> dict:
        out: dict = {}
        for n in self.by_id.values():
            for p in n.providers:
                out[p] = out.get(p, 0) + n.total_tokens
        return out

    def deepest(self) -> int:
        return max((n.depth for n in self.by_id.values()), default=0)

    def product_summary(self) -> dict:
        """Safe product facts bound to this run, or an explicit legacy gap."""
        if not self.product_outcome:
            return {"record_type": "solve_outcome_projection/v1",
                    "available": False, "terminal_code": "",
                    "solved": False, "summary": "", "failure_code": "",
                    "verification": {}, "artifacts": [], "workspace": "",
                    "limitations": [], "next_action": "",
                    "graph_digest": "", "selected_canvas": {}}
        outcome = self.product_outcome
        return {
            "record_type": "solve_outcome_projection/v1",
            "available": True,
            "terminal_code": str(outcome.get("terminal_code") or ""),
            "solved": bool(outcome.get("solved")),
            "summary": str(outcome.get("summary") or ""),
            "failure_code": str(outcome.get("failure_code") or ""),
            "verification": dict(outcome.get("verification") or {}),
            "artifacts": list(outcome.get("artifacts") or ()),
            "workspace": str(outcome.get("workspace") or ""),
            "limitations": list(outcome.get("limitations") or ()),
            "next_action": str(outcome.get("next_action") or ""),
            "graph_digest": str(outcome.get("graph_digest") or ""),
            "selected_canvas": dict(outcome.get("selected_canvas") or {}),
        }

    def summary(self) -> dict:
        return {"record_type": "loop_report/v1", "run_id": self.run_id,
                "loops": self.loops, "events": self.total_events,
                "max_depth": self.deepest(), "model_calls": self.model_calls,
                "total_tokens": self.total_tokens,
                "tokens_by_provider": self.cost_by_provider(),
                "event_families": dict(self.families),
                "chain_intact": self.chain_intact,
                "relationship_dag_complete": self.relationship_dag.complete,
                "relationship_edges": len(self.relationship_dag.edges),
                "relationship_diagnostics": len(
                    self.relationship_dag.diagnostics),
                "product": self.product_summary()}

    def as_dict(self) -> dict:
        return {**self.summary(),
                "tree": [loop.as_dict() for loop in self.starting_loops],
                "relationship_dag": self.relationship_dag.as_dict(),
                "relationship_mermaid": self.relationship_dag.mermaid()}


def report_from_ledger(events, *, run_id: str = "",
                       chain_intact: "bool | None" = None) -> LoopReport:
    """Project a ledger into a report. Nothing is recomputed from elsewhere."""
    from ..core.run_history import as_ledger_events
    events = as_ledger_events(events)
    rep = LoopReport(
        run_id=run_id, chain_intact=chain_intact,
        relationship_dag=loop_relationship_dag(events))
    rep.total_events = len(events)

    for e in events:
        lid = str(e.get("loop_id", "") or "")
        if not lid:
            continue
        node = rep.by_id.get(lid)
        if node is None:
            node = LoopReportRecord(loop_id=lid)
            rep.by_id[lid] = node
        node.events += 1
        kind = str(e.get("event", ""))
        ts = e.get("ts")

        if kind == _OPEN:
            node.goal = str(e.get("goal", "") or e.get("label", "") or "")
            spawning = str(e.get("spawning_loop_id", "") or "")
            if spawning:
                node.spawning_loop_id = spawning
            if isinstance(ts, (int, float)):
                node.started = float(ts)

        # THE RUNTIME OWNERSHIP EDGE. A returned Loop names the Loop that
        # spawned it independently of its semantic relationship kind.
        if kind == "spawned_return":
            spawned_id = str(e.get("spawned_loop_id", "") or "")
            if spawned_id:
                spawned = rep.by_id.get(spawned_id)
                if spawned is None:
                    spawned = LoopReportRecord(loop_id=spawned_id)
                    rep.by_id[spawned_id] = spawned
                spawned.spawning_loop_id = lid
        if kind == "spawn":
            spawning = str(e.get("spawning_loop_id", "") or "")
            if spawning:
                node.spawning_loop_id = spawning
            if e.get("goal") and not node.goal:
                node.goal = str(e.get("goal"))
        if kind in _TERMINAL_EVENTS:
            node.outcome = str(e.get("reason", "") or e.get("code", "")
                               or kind)
            if isinstance(ts, (int, float)):
                node.ended = float(ts)
        if isinstance(ts, (int, float)):
            if node.started is None:
                node.started = float(ts)
            node.ended = float(ts) if node.ended is None else max(
                node.ended, float(ts))

        if e.get("mode") and not node.mode:
            node.mode = str(e["mode"])
        step = e.get("step")
        if step and str(step) not in node.steps:
            node.steps.append(str(step))

        # model cost: provider-reported only, attributed to whoever answered
        if kind in ("model_led", "model_invocation", "model_invocation_failed"):
            node.model_calls += 1
            node.prompt_tokens += int(e.get("prompt_tokens", 0) or 0)
            node.eval_tokens += int(e.get("eval_tokens", 0) or 0)
            prov = str(e.get("provider", "") or "")
            if prov and prov not in node.providers:
                node.providers.append(prov)

    # canonical families, from the same closed vocabulary the ledger uses
    for c in to_canonical_events(events):
        fam = c["type"]
        rep.families[fam] = rep.families.get(fam, 0) + 1

    # Assemble runtime ownership. A missing spawning Loop makes the item a
    # starting display node so no Loop is silently dropped.
    for node in rep.by_id.values():
        spawning = (rep.by_id.get(node.spawning_loop_id)
                    if node.spawning_loop_id else None)
        if spawning is not None and spawning is not node:
            spawning.spawned_loops.append(node)
        else:
            rep.starting_loops.append(node)

    def _depth(n, d=0, seen=()):
        if n.loop_id in seen:                    # cycle guard: never recurse
            return
        n.depth = d
        for c in n.spawned_loops:
            _depth(c, d + 1, seen + (n.loop_id,))

    for r in rep.starting_loops:
        _depth(r)
    return rep


def report_from_run(root: str, run_id: str, *, ledger=None) -> LoopReport:
    """Project a SAVED run: the ``runs/<run_id>/`` layout on disk.

    The stored run is reached through the historical-intelligence loop rather
    than by opening saved run history directly: past runs are one of the four
    intelligence pillars, and a reader that bypasses the envelope is exactly
    the direct-resource-access the conformance gate refuses."""
    from ..core.run_history import load_saved_run_bundle
    from ..loop.intelligence_loops import serve_historical_intelligence
    bundle = serve_historical_intelligence(
        f"report:{run_id}", lambda: load_saved_run_bundle(root, run_id),
        ledger=ledger)["value"]
    rep = report_from_ledger(
        bundle.history.event_log, run_id=run_id,
        chain_intact=bundle.history.verify_chain()["intact"])
    rep.product_outcome = dict(bundle.outcome or {})
    return rep


def _cost_line(n: LoopReportRecord) -> str:
    if n.model_calls == 0:
        return "0 model calls"
    who = "/".join(n.providers) if n.providers else "provider unknown"
    return f"{n.model_calls} model call(s), {n.total_tokens} tokens ({who})"


def _ownership_tree_lines(rep: LoopReport, *, show_steps: bool = True
                          ) -> list[str]:
    lines = []

    def walk(node, prefix=""):
        secs = node.seconds
        timing = f" {secs}s" if secs is not None else ""
        head = f"{prefix}{node.loop_id}"
        if node.goal:
            head += f": {node.goal[:70]}"
        lines.append(head)
        lines.append(
            f"{prefix}    [{node.mode or 'mode unrecorded'}]{timing}, "
            f"{node.events} events, {_cost_line(node)}")
        if show_steps and node.steps:
            lines.append(
                f"{prefix}    steps: {' -> '.join(node.steps)}")
        for spawned in node.spawned_loops:
            walk(spawned, prefix + "    ")

    for starting in rep.starting_loops:
        walk(starting)
    return lines


def render_text(rep: LoopReport, *, show_steps: bool = True) -> str:
    """An indented tree for a terminal."""
    out = [f"LOOP REPORT: {rep.run_id or 'unsaved run'}",
           f"  {rep.loops} loops, {rep.total_events} events, "
           f"max depth {rep.deepest()}",
           f"  {rep.model_calls} model calls, {rep.total_tokens} tokens"]
    if rep.chain_intact is not None:
        out.append(f"  chain verified: {'yes' if rep.chain_intact else 'NO'}")
    product = rep.product_summary()
    if product["available"]:
        verified = bool(product["verification"].get("passed")
                        or product["verification"].get("verdict") == "accept")
        out += [f"  product terminal: {product['terminal_code']}",
                f"  verification: {'passed' if verified else 'not passed'}"]
        if product["summary"]:
            out.append(f"  result: {product['summary']}")
        if product["workspace"]:
            out.append(f"  workspace: {product['workspace']}")
        if product["artifacts"]:
            out.append("  artifacts:")
            out += [f"    {item.get('path', '')}"
                    for item in product["artifacts"]]
    else:
        out.append("  product outcome: not recorded (legacy run)")
    prov = rep.cost_by_provider()
    if prov:
        out.append("  by provider: "
                   + ", ".join(f"{k} {v}" for k, v in sorted(prov.items())))
    if not rep.by_id:
        out.append("  (this run recorded no loops)")
        return "\n".join(out)
    out.append("")

    out.extend(_ownership_tree_lines(rep, show_steps=show_steps))
    out += ["", *rep.relationship_dag.text_lines()]
    return "\n".join(out)


def render_markdown(rep: LoopReport) -> str:
    """A report to paste into an issue or a pull request."""
    out = [f"# Loop report: {rep.run_id or 'unsaved run'}", "",
           "| | |", "|---|---|",
           f"| Loops | {rep.loops} |",
           f"| Events | {rep.total_events} |",
           f"| Max depth | {rep.deepest()} |",
           f"| Model calls | {rep.model_calls} |",
           f"| Tokens (provider-reported) | {rep.total_tokens} |"]
    if rep.chain_intact is not None:
        out.append(f"| Chain verified | {'yes' if rep.chain_intact else 'NO'} |")
    product = rep.product_summary()
    if product["available"]:
        verified = bool(product["verification"].get("passed")
                        or product["verification"].get("verdict") == "accept")
        out += [f"| Product terminal | `{product['terminal_code']}` |",
                f"| Product verification | {'passed' if verified else 'not passed'} |",
                "", "## Product result", "",
                product["summary"] or "No product summary was recorded."]
        if product["workspace"]:
            out += ["", f"Workspace: `{product['workspace']}`"]
        if product["artifacts"]:
            out += ["", "### Artifacts", ""]
            out += [f"- `{item.get('path', '')}`"
                    for item in product["artifacts"]]
        if product["limitations"]:
            out += ["", "### Limitations", ""]
            out += [f"- {item}" for item in product["limitations"]]
    else:
        out += ["| Product outcome | not recorded (legacy run) |"]
    prov = rep.cost_by_provider()
    if prov:
        out += ["", "## Cost by provider", "",
                "| Provider | Tokens |", "|---|---:|"]
        out += [f"| {k} | {v} |" for k, v in sorted(prov.items())]
    if not rep.by_id:
        out += ["", "_This run recorded no loops._"]
        return "\n".join(out)

    out += ["", "## Loop ownership tree", "", "```"]
    out.append("\n".join(_ownership_tree_lines(rep)))
    out += ["```", "", "## Semantic relationship DAG", "", "```mermaid",
            rep.relationship_dag.mermaid(), "```"]
    if rep.relationship_dag.diagnostics:
        out += ["", "### Relationship diagnostics", "", "```"]
        out += rep.relationship_dag.text_lines()[1:]
        out += ["```"]
    out += ["", "## Event families", "",
            "| Family | Count |", "|---|---:|"]
    out += [f"| `{k}` | {v} |" for k, v in sorted(rep.families.items())]
    return "\n".join(out)


def render_html(rep: LoopReport) -> str:
    """A self-contained page: no external assets, no network."""
    def esc(s):
        return _html.escape(str(s))

    rows = []

    def walk(n, depth=0):
        secs = n.seconds
        rows.append(
            f'<li><div class="loop"><span class="id">{esc(n.loop_id)}</span>'
            f'<span class="goal">{esc(n.goal[:80])}</span>'
            f'<span class="mode m-{esc(n.mode or "unset")}">'
            f'{esc(n.mode or "mode unrecorded")}</span>'
            f'<span class="meta">{n.events} events'
            + (f' · {secs}s' if secs is not None else '')
            + (f' · {n.model_calls} calls, {n.total_tokens} tok'
               if n.model_calls else ' · no model')
            + '</span></div>')
        if n.spawned_loops:
            rows.append("<ul>")
            for c in n.spawned_loops:
                walk(c, depth + 1)
            rows.append("</ul>")
        rows.append("</li>")

    for r in rep.starting_loops:
        walk(r)
    tree = "<ul class='tree'>" + "".join(rows) + "</ul>" if rows else \
        "<p class='empty'>This run recorded no loops.</p>"
    fam = "".join(f"<tr><td><code>{esc(k)}</code></td><td>{v}</td></tr>"
                  for k, v in sorted(rep.families.items()))
    prov = "".join(f"<tr><td>{esc(k)}</td><td>{v}</td></tr>"
                   for k, v in sorted(rep.cost_by_provider().items()))
    relationship_text = "\n".join(rep.relationship_dag.text_lines())
    product = rep.product_summary()
    product_html = "<p class='empty'>Product outcome was not recorded for this legacy run.</p>"
    if product["available"]:
        verified = bool(product["verification"].get("passed")
                        or product["verification"].get("verdict") == "accept")
        artifact_items = "".join(
            f"<li><code>{esc(item.get('path', ''))}</code></li>"
            for item in product["artifacts"])
        product_html = (
            f"<div class='product'><b>{esc(product['terminal_code'])}</b>"
            f"<span>{esc(product['summary'])}</span>"
            f"<span>verification: {'passed' if verified else 'not passed'}</span>"
            + (f"<span>workspace: <code>{esc(product['workspace'])}</code></span>"
               if product["workspace"] else "")
            + (f"<ul>{artifact_items}</ul>" if artifact_items else "")
            + "</div>")
    chain = ("" if rep.chain_intact is None else
             f"<div class='stat'><b>{'yes' if rep.chain_intact else 'NO'}</b>"
             "<span>chain verified</span></div>")
    return f"""<!doctype html><meta charset="utf-8">
<title>Loop report: {esc(rep.run_id or 'run')}</title>
<style>
:root{{--bg:#fbfaf8;--fg:#1c1a17;--dim:#6b6660;--line:#e3ded6;--acc:#9a5b34}}
@media(prefers-color-scheme:dark){{:root{{--bg:#16151a;--fg:#ece9e4;
--dim:#9a948c;--line:#2e2b33;--acc:#d38a5c}}}}
*{{box-sizing:border-box}}
body{{margin:0;padding:2rem 1.25rem;background:var(--bg);color:var(--fg);
font:15px/1.55 ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif}}
.wrap{{max-width:60rem;margin:0 auto}}
h1{{font-size:1.5rem;margin:0 0 .25rem}}
.sub{{color:var(--dim);margin:0 0 1.5rem;font-size:.9rem}}
.stats{{display:flex;flex-wrap:wrap;gap:.75rem;margin-bottom:1.75rem}}
.stat{{border:1px solid var(--line);border-radius:8px;padding:.6rem .9rem;
min-width:7rem}}
.stat b{{display:block;font-size:1.35rem;font-variant-numeric:tabular-nums}}
.stat span{{color:var(--dim);font-size:.78rem;text-transform:uppercase;
letter-spacing:.04em}}
h2{{font-size:1rem;text-transform:uppercase;letter-spacing:.05em;
color:var(--dim);margin:2rem 0 .75rem}}
ul.tree,ul.tree ul{{list-style:none;margin:0;padding-left:1.1rem}}
ul.tree{{padding-left:0}}
ul.tree ul{{border-left:1px solid var(--line);margin-left:.4rem}}
.loop{{padding:.4rem 0;display:flex;gap:.6rem;flex-wrap:wrap;
align-items:baseline}}
.id{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.82rem;
color:var(--acc)}}
.goal{{font-weight:500}}
.mode{{font-size:.72rem;border:1px solid var(--line);border-radius:99px;
padding:.05rem .5rem;color:var(--dim)}}
.meta{{color:var(--dim);font-size:.8rem;font-variant-numeric:tabular-nums}}
table{{border-collapse:collapse;width:100%;max-width:28rem}}
td{{border-bottom:1px solid var(--line);padding:.35rem .5rem;font-size:.86rem}}
td:last-child{{text-align:right;font-variant-numeric:tabular-nums}}
.empty{{color:var(--dim)}}
.product{{border:1px solid var(--line);border-radius:8px;padding:.8rem 1rem}}
.product b,.product span{{display:block;margin:.15rem 0}}
.product ul{{margin:.5rem 0 0;padding-left:1.25rem}}
.product code{{overflow-wrap:anywhere}}
.foot{{margin-top:2.5rem;color:var(--dim);font-size:.78rem;
border-top:1px solid var(--line);padding-top:1rem}}
</style>
<div class="wrap">
<h1>Loop report</h1>
<p class="sub">{esc(rep.run_id or 'unsaved run')}</p>
<div class="stats">
<div class="stat"><b>{rep.loops}</b><span>loops</span></div>
<div class="stat"><b>{rep.total_events}</b><span>events</span></div>
<div class="stat"><b>{rep.deepest()}</b><span>max depth</span></div>
<div class="stat"><b>{rep.model_calls}</b><span>model calls</span></div>
<div class="stat"><b>{rep.total_tokens}</b><span>tokens</span></div>
{chain}
</div>
<h2>Product result</h2>{product_html}
<h2>Loop ownership tree</h2>{tree}
<h2>Semantic relationship DAG</h2><pre>{esc(relationship_text)}</pre>
{"<h2>Cost by provider</h2><table>" + prov + "</table>" if prov else ""}
<h2>Event families</h2><table>{fam}</table>
<p class="foot">Every figure is projected from the run's own ledger.
Token counts are provider-reported; a value the ledger does not carry is shown
as unknown rather than filled in.</p>
</div>"""


def write_report(rep: LoopReport, path: str, *, fmt: str = "") -> str:
    """Write a report, choosing the renderer from the file extension."""
    fmt = fmt or (path.rsplit(".", 1)[-1] if "." in path else "txt")
    body = {"html": render_html, "md": render_markdown,
            "markdown": render_markdown, "json": lambda r: json.dumps(
                r.as_dict(), indent=1)}.get(fmt, render_text)(rep)
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    return path


def self_test() -> dict:
    results = []

    def check(name, ok, note=""):
        results.append({"test": name, "passed": bool(ok), "detail": note})

    from ..loop.recursive_loop import LoopLedger

    # A real nested run: a starting Loop spawns two Loops, one of which makes
    # a model call. Built from the ledger's own vocabulary, not a mock.
    lg = LoopLedger()
    lg.record(loop_id="starting", event="init", goal="solve the task",
              relationship_kind="starting", ts=100.0)
    lg.record(loop_id="starting", event="iteration_started", step="orient",
              mode="deterministic", ts=100.5)
    lg.record(loop_id="kid1", event="init", goal="retrieve context",
              relationship_kind="spawned_by",
              spawned_by_loop_id="starting", ts=101.0)
    lg.record(loop_id="kid1", event="spawn",
              spawning_loop_id="starting", ts=101.0)
    lg.record(loop_id="kid1", event="terminal", reason="done", ts=101.5)
    lg.record(loop_id="kid2", event="init", goal="ask the model",
              relationship_kind="spawned_by",
              spawned_by_loop_id="starting", ts=102.0)
    lg.record(loop_id="kid2", event="spawn",
              spawning_loop_id="starting", ts=102.0)
    lg.record(loop_id="kid2", event="model_led", model="m", provider="mistral",
              prompt_tokens=60, eval_tokens=140, ts=102.5)
    lg.record(loop_id="kid2", event="terminal", reason="done", ts=103.0)
    lg.record(loop_id="starting", event="terminal", reason="done", ts=104.0)

    rep = report_from_ledger(lg.events, run_id="demo-run", chain_intact=True)

    # 1. THE TREE COMES FROM REAL NESTING, not from event order.
    check("the_tree_is_built_from_recorded_spawning",
          len(rep.starting_loops) == 1
          and rep.starting_loops[0].loop_id == "starting"
          and [item.loop_id
               for item in rep.starting_loops[0].spawned_loops]
              == ["kid1", "kid2"]
          and rep.deepest() == 1 and rep.loops == 3,
          "one starting Loop, two spawned Loops, depth 1")

    # 1b. Runtime ownership comes from spawn and return events independently
    # of the spawned Loop's semantic relationship.
    from ..loop.recursive_loop import Loop, LoopConfig, StepOutcome
    slg = LoopLedger()
    spawning_loop = Loop("spawning Loop",
                       LoopConfig(framework="custom", custom_steps=("act",),
                                  power="light"), ledger=slg)
    spawned_loop = spawning_loop.spawn("a real spawned Loop")
    while not spawned_loop.is_terminal:
        spawned_loop.run_next_iteration(
            handler=lambda loop, step, ctx: StepOutcome(
                output="done", mode="deterministic", confidence=0.9))
    spawned = report_from_ledger(slg.events)
    spawning_node = spawned.by_id.get(spawning_loop.loop_id)
    check("a_spawned_loop_nests_under_its_spawning_loop",
          spawning_node is not None
          and spawned_loop.loop_id in [
              item.loop_id for item in spawning_node.spawned_loops]
          and spawned.by_id[spawned_loop.loop_id].spawning_loop_id
              == spawning_loop.loop_id
          and spawned.deepest() >= 1,
          f"{spawned_loop.loop_id} nests under {spawning_loop.loop_id}")

    # 2. COST IS ATTRIBUTED TO WHOEVER ANSWERED. A token count with no provider
    # cannot be checked later, so the provider travels with the number.
    kid2 = rep.by_id["kid2"]
    check("model_cost_is_attributed_to_the_answering_provider",
          rep.model_calls == 1 and rep.total_tokens == 200
          and kid2.providers == ["mistral"]
          and rep.cost_by_provider() == {"mistral": 200}
          and rep.by_id["kid1"].model_calls == 0,
          "200 tokens, all attributed to mistral")

    # 3. TIMINGS come from recorded timestamps.
    check("timings_are_read_from_recorded_timestamps",
          rep.starting_loops[0].seconds == 4.0 and kid2.seconds == 1.0,
          "starting Loop spans its spawned Loops for 4.0s")

    # 4. UNKNOWN IS NOT ZERO. The live LoopLedger always stamps `ts`, so this
    # path is about a ledger from somewhere else: a replay, an import, an
    # older record: where the field is genuinely absent. Reporting 0.0 there
    # would read as an instantaneous loop, which is a different claim from
    # "this run did not record time".
    r2 = report_from_ledger([{"loop_id": "a", "event": "init",
                              "goal": "no timestamps"}])
    live = report_from_ledger(
        [dict(e) for e in (lambda l: (l.record(loop_id="b", event="init",
                                               goal="stamped"), l.events)[1])(
            LoopLedger())])
    check("a_missing_duration_is_unknown_rather_than_zero",
          r2.by_id["a"].seconds is None
          and r2.by_id["a"].as_dict()["seconds"] is None
          and live.by_id["b"].seconds == 0.0,
          "absent timestamps -> None; a stamped single-event loop -> 0.0")

    # 5. AN EMPTY RUN reports an empty run rather than a plausible-looking one.
    empty = report_from_ledger([])
    txt = render_text(empty)
    check("an_empty_run_is_reported_as_empty",
          empty.loops == 0 and empty.total_tokens == 0
          and "recorded no loops" in txt
          and "recorded no loops" in render_markdown(empty)
          and empty.deepest() == 0,
          "no invented structure")

    # 6. every renderer works and the HTML is SELF-CONTAINED: a report that
    # needs the network is not a report you can send someone.
    t, m, h = render_text(rep), render_markdown(rep), render_html(rep)
    check("all_three_renderings_carry_the_same_facts",
          "starting" in t and "mistral" in t
          and "| Model calls | 1 |" in m and "mistral" in m
          and "Loop report" in h and "mistral" in h
          and "200" in h,
          "text, markdown and html agree")
    check("the_html_report_is_self_contained",
          "<script" not in h.lower() and "http://" not in h
          and "https://" not in h and "<style>" in h
          and "prefers-color-scheme" in h,
          "no external assets, no network, both themes")

    relationship_events = (
        {"event": "init", "loop_id": "p", "goal": "practice",
         "role": "practitioner", "profile_id": "practitioner.solver",
         "relationship_kind": "starting"},
        {"event": "init", "loop_id": "s", "goal": "research",
         "role": "practitioner", "profile_id": "practitioner.research",
         "relationship_kind": "spawned_by", "spawned_by_loop_id": "p"},
        {"event": "init", "loop_id": "q", "goal": "query",
         "role": "intelligence", "profile_id": "intelligence.search",
         "relationship_kind": "queried_by", "queried_by_loop_id": "p"},
        {"event": "init", "loop_id": "i", "goal": "materialize",
         "role": "intelligence", "profile_id": "intelligence.materialize",
         "relationship_kind": "retrieved_by", "retrieved_by_loop_id": "q"},
        {"event": "init", "loop_id": "z", "goal": "solution",
         "role": "solution", "profile_id": "solution.pipeline",
         "relationship_kind": "connected_from",
         "connected_from_loop_ids": ("p", "i")},
    )
    relationship_report = report_from_ledger(relationship_events)
    relationship_dict = relationship_report.as_dict()
    relationship_text = render_text(relationship_report)
    relationship_markdown = render_markdown(relationship_report)
    relationship_html = render_html(relationship_report)
    check("semantic_DAG_renders_consistently_in_text_markdown_html_and_JSON",
          relationship_report.relationship_dag.complete
          and len(relationship_report.relationship_dag.edges) == 5
          and relationship_dict["relationship_dag"]["complete"] is True
          and "p -- Queried by --> q" in relationship_text
          and "```mermaid" in relationship_markdown
          and "Connected from" in relationship_markdown
          and "Semantic relationship DAG" in relationship_html
          and '["<br/>' not in relationship_dict["relationship_mermaid"])

    broken_report = report_from_ledger((
        {"event": "custom", "loop_id": ""},
        {"event": "init", "loop_id": "visible",
         "relationship_kind": "queried_by",
         "queried_by_loop_id": "missing"},
    ))
    broken_text = render_text(broken_report)
    check("missing_endpoints_are_visible_without_blank_vertices",
          broken_report.loops == 1
          and len(broken_report.relationship_dag.vertices) == 1
          and not broken_report.relationship_dag.complete
          and "relationship_endpoint_unknown" in broken_text
          and 'relationship_loop_0["visible' in
              broken_report.relationship_dag.mermaid()
          and '["<br/>' not in broken_report.relationship_dag.mermaid())

    # 7. ADVERSARIAL: a missing spawning Loop must not drop a Loop, and a
    # self-spawning reference must not hang the report.
    lg3 = LoopLedger()
    lg3.record(loop_id="orphan", event="init", goal="lost spawning Loop",
               relationship_kind="spawned_by",
               spawned_by_loop_id="never_existed")
    lg3.record(loop_id="orphan", event="spawn",
               spawning_loop_id="never_existed")
    lg3.record(loop_id="selfref", event="init", goal="self spawning Loop",
               relationship_kind="spawned_by",
               spawned_by_loop_id="selfref")
    lg3.record(loop_id="selfref", event="spawn",
               spawning_loop_id="selfref")
    r3 = report_from_ledger(lg3.events)
    check("orphans_and_self_parents_are_reported_not_dropped_or_hung",
          r3.loops == 2 and len(r3.starting_loops) == 2
          and {n.loop_id for n in r3.starting_loops}
              == {"orphan", "selfref"},
          "every loop appears exactly once")

    # 8. Persisted run history uses event_type/detail fields. The canonical
    # adapter must preserve the goal, model-call count, and tokens.
    import shutil
    import tempfile
    from ..core.run_history import RunHistory, bind_product_outcome
    saved_ledger = LoopLedger()
    saved_ledger.record(loop_id="saved", event="init", goal="saved work")
    saved_ledger.record(loop_id="saved", event="run_step", step="decide",
                        mode="hybrid", output="selected")
    saved_ledger.record(loop_id="saved", event="terminal", reason="done")
    saved_run_history = RunHistory.from_ledger(
        saved_ledger.events, run_id="saved-report",
        usage_log=[{"model": "test-model", "prompt_tokens": 10,
                    "eval_tokens": 20}])
    saved_run_history.commit()
    saved_root = tempfile.mkdtemp(prefix="loop_report_saved_")
    saved_run_history.save(saved_root)
    bind_product_outcome(saved_root, "saved-report", {
        "record_type": "solve_outcome/v3", "run_id": "saved-report",
        "terminal_code": "COMPLETED_VERIFIED",
        "status": "COMPLETED_VERIFIED", "solved": True,
        "summary": "Saved product.", "failure_code": "",
        "verification": {"passed": True},
        "artifacts": [{"path": "/tmp/result.txt"}],
        "workspace": "/tmp", "limitations": [], "selected_canvas": {},
    })
    saved_report = report_from_run(saved_root, "saved-report")
    check("saved_run_history_report_preserves_usage_and_goal",
          saved_report.model_calls == 1
          and saved_report.total_tokens == 30
          and saved_report.by_id["saved"].goal == "saved work"
          and saved_report.chain_intact is True
          and saved_report.product_summary()["terminal_code"]
              == "COMPLETED_VERIFIED"
          and "/tmp/result.txt" in render_text(saved_report)
          and "Saved product." in render_markdown(saved_report)
          and "COMPLETED_VERIFIED" in render_html(saved_report),
          "usage, goal, product terminal, artifact, and chain preserved")
    shutil.rmtree(saved_root, ignore_errors=True)

    passed = sum(1 for t in results if t["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
