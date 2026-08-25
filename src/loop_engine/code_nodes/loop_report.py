"""Loop reports: turn a run's ledger into something a person can read.

Architectural role: Code Node system (the reporting projection over a run).

A run emits a chain of events. That chain is complete and checkable, and it is
also unreadable: a few hundred JSON records with nesting expressed only through
parent ids. This module answers the question a person actually has after a run
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
    - LoopReport: the projection (tree, per-loop rollups, cost, timings);
    - render_text / render_markdown / render_html;
    - report_from_ledger() / report_from_run(): the two entry points.

Does not own:
    - the ledger or its vocabulary (chronicle, event_vocabulary), the runtime
      (recursive_loop), or the Studio server's live projections.

Key invariants:
    - every figure traces to a ledger event; nothing is estimated;
    - an empty run reports an empty run rather than a plausible-looking one;
    - model cost is attributed per provider, or reported as unknown;
    - the rendered HTML is self-contained (no external assets).

Verification: self_test(): tree shape from real nesting, cost attribution,
the empty-run path, unknown-vs-zero honesty, and HTML self-containment.
"""

from __future__ import annotations

import html as _html
import json
from dataclasses import dataclass, field

from ..static_architecture.chronicle import to_canonical_events

#: Events that open and close a loop, used to build the tree and the timings.
_OPEN = "init"
_TERMINAL_EVENTS = ("terminal", "loop.completed", "loop.failed")


@dataclass
class LoopNode:
    """One loop in the tree, with what it did and what it cost."""
    loop_id: str
    goal: str = ""
    parent: str = ""
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
    children: list = field(default_factory=list)

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
                "parent": self.parent, "depth": self.depth, "mode": self.mode,
                "steps": list(self.steps), "events": self.events,
                "model_calls": self.model_calls,
                "prompt_tokens": self.prompt_tokens,
                "eval_tokens": self.eval_tokens,
                "total_tokens": self.total_tokens,
                "providers": list(self.providers), "seconds": self.seconds,
                "outcome": self.outcome,
                "children": [c.as_dict() for c in self.children]}


@dataclass
class LoopReport:
    """The whole run, projected."""
    run_id: str = ""
    roots: list = field(default_factory=list)
    by_id: dict = field(default_factory=dict)
    total_events: int = 0
    families: dict = field(default_factory=dict)
    chain_intact: "bool | None" = None

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

    def summary(self) -> dict:
        return {"record_type": "loop_report/v1", "run_id": self.run_id,
                "loops": self.loops, "events": self.total_events,
                "max_depth": self.deepest(), "model_calls": self.model_calls,
                "total_tokens": self.total_tokens,
                "tokens_by_provider": self.cost_by_provider(),
                "event_families": dict(self.families),
                "chain_intact": self.chain_intact}

    def as_dict(self) -> dict:
        return {**self.summary(), "tree": [r.as_dict() for r in self.roots]}


def report_from_ledger(events, *, run_id: str = "",
                       chain_intact: "bool | None" = None) -> LoopReport:
    """Project a ledger into a report. Nothing is recomputed from elsewhere."""
    from ..static_architecture.chronicle import as_ledger_events
    events = as_ledger_events(events)
    rep = LoopReport(run_id=run_id, chain_intact=chain_intact)
    rep.total_events = len(events)

    for e in events:
        lid = str(e.get("loop_id", "") or "")
        if not lid:
            continue
        node = rep.by_id.get(lid)
        if node is None:
            node = LoopNode(loop_id=lid)
            rep.by_id[lid] = node
        node.events += 1
        kind = str(e.get("event", ""))
        ts = e.get("ts")

        if kind == _OPEN:
            node.goal = str(e.get("goal", "") or e.get("label", "") or "")
            parent = str(e.get("parent", "") or e.get("parent_loop_id", "")
                         or "")
            if parent:
                node.parent = parent
            if isinstance(ts, (int, float)):
                node.started = float(ts)

        # THE REAL PARENT EDGE. A spawned child does not announce its parent on
        # its own `init`; the PARENT records `child_return` under its own
        # loop_id naming the child. Reading only `init` produced a flat list of
        # loops for a run that was genuinely nested: which hid the one
        # structure the report exists to show.
        if kind == "child_return":
            kid = str(e.get("child", "") or "")
            if kid:
                child = rep.by_id.get(kid)
                if child is None:
                    child = LoopNode(loop_id=kid)
                    rep.by_id[kid] = child
                child.parent = lid
        if kind == "spawn":
            parent = str(e.get("parent", "") or "")
            if parent:
                node.parent = parent
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
            if kind != "model_invocation_failed":
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

    # assemble the tree; a parent that never appears is treated as a root so
    # no loop is silently dropped from the report
    for node in rep.by_id.values():
        parent = rep.by_id.get(node.parent) if node.parent else None
        if parent is not None and parent is not node:
            parent.children.append(node)
        else:
            rep.roots.append(node)

    def _depth(n, d=0, seen=()):
        if n.loop_id in seen:                    # cycle guard: never recurse
            return
        n.depth = d
        for c in n.children:
            _depth(c, d + 1, seen + (n.loop_id,))

    for r in rep.roots:
        _depth(r)
    return rep


def report_from_run(root: str, run_id: str, *, ledger=None) -> LoopReport:
    """Project a SAVED run: the ``runs/<run_id>/`` layout on disk.

    The stored run is reached through the historical-intelligence loop rather
    than by opening the Chronicle directly: past runs are one of the four
    intelligence pillars, and a reader that bypasses the envelope is exactly
    the direct-resource-access the conformance gate refuses."""
    from ..static_architecture.chronicle import Chronicle
    from ..loop.intelligence_loops import serve_historical_intelligence
    ch = serve_historical_intelligence(
        f"report:{run_id}", lambda: Chronicle.load(root, run_id),
        ledger=ledger)["value"]
    return report_from_ledger(ch.events, run_id=run_id,
                              chain_intact=ch.verify_chain()["intact"])


def _cost_line(n: LoopNode) -> str:
    if n.model_calls == 0:
        return "0 model calls"
    who = "/".join(n.providers) if n.providers else "provider unknown"
    return f"{n.model_calls} model call(s), {n.total_tokens} tokens ({who})"


def render_text(rep: LoopReport, *, show_steps: bool = True) -> str:
    """An indented tree for a terminal."""
    out = [f"LOOP REPORT: {rep.run_id or 'unsaved run'}",
           f"  {rep.loops} loops, {rep.total_events} events, "
           f"max depth {rep.deepest()}",
           f"  {rep.model_calls} model calls, {rep.total_tokens} tokens"]
    if rep.chain_intact is not None:
        out.append(f"  chain verified: {'yes' if rep.chain_intact else 'NO'}")
    prov = rep.cost_by_provider()
    if prov:
        out.append("  by provider: "
                   + ", ".join(f"{k} {v}" for k, v in sorted(prov.items())))
    if not rep.by_id:
        out.append("  (this run recorded no loops)")
        return "\n".join(out)
    out.append("")

    def walk(n, prefix=""):
        secs = n.seconds
        timing = f" {secs}s" if secs is not None else ""
        head = f"{prefix}{n.loop_id}"
        if n.goal:
            head += f": {n.goal[:70]}"
        out.append(head)
        detail = f"{prefix}    [{n.mode or 'mode unrecorded'}]{timing}, " \
                 f"{n.events} events, {_cost_line(n)}"
        out.append(detail)
        if show_steps and n.steps:
            out.append(f"{prefix}    steps: {' -> '.join(n.steps)}")
        for c in n.children:
            walk(c, prefix + "    ")

    for r in rep.roots:
        walk(r)
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
    prov = rep.cost_by_provider()
    if prov:
        out += ["", "## Cost by provider", "",
                "| Provider | Tokens |", "|---|---:|"]
        out += [f"| {k} | {v} |" for k, v in sorted(prov.items())]
    if not rep.by_id:
        out += ["", "_This run recorded no loops._"]
        return "\n".join(out)

    out += ["", "## Loop tree", "", "```"]
    out.append(render_text(rep).split("\n\n", 1)[-1])
    out += ["```", "", "## Event families", "",
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
        if n.children:
            rows.append("<ul>")
            for c in n.children:
                walk(c, depth + 1)
            rows.append("</ul>")
        rows.append("</li>")

    for r in rep.roots:
        walk(r)
    tree = "<ul class='tree'>" + "".join(rows) + "</ul>" if rows else \
        "<p class='empty'>This run recorded no loops.</p>"
    fam = "".join(f"<tr><td><code>{esc(k)}</code></td><td>{v}</td></tr>"
                  for k, v in sorted(rep.families.items()))
    prov = "".join(f"<tr><td>{esc(k)}</td><td>{v}</td></tr>"
                   for k, v in sorted(rep.cost_by_provider().items()))
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
<h2>Loop tree</h2>{tree}
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

    # A real nested run: a parent that spawns two children, one of which makes
    # a model call. Built from the ledger's own vocabulary, not a mock.
    lg = LoopLedger()
    lg.record(loop_id="root", event="init", goal="solve the task", ts=100.0)
    lg.record(loop_id="root", event="iteration_started", step="orient",
              mode="deterministic", ts=100.5)
    lg.record(loop_id="kid1", event="init", goal="retrieve context",
              parent="root", ts=101.0)
    lg.record(loop_id="kid1", event="terminal", reason="done", ts=101.5)
    lg.record(loop_id="kid2", event="init", goal="ask the model",
              parent="root", ts=102.0)
    lg.record(loop_id="kid2", event="model_led", model="m", provider="mistral",
              prompt_tokens=60, eval_tokens=140, ts=102.5)
    lg.record(loop_id="kid2", event="terminal", reason="done", ts=103.0)
    lg.record(loop_id="root", event="terminal", reason="done", ts=104.0)

    rep = report_from_ledger(lg.events, run_id="demo-run", chain_intact=True)

    # 1. THE TREE COMES FROM REAL NESTING, not from event order.
    check("the_tree_is_built_from_recorded_parentage",
          len(rep.roots) == 1 and rep.roots[0].loop_id == "root"
          and [c.loop_id for c in rep.roots[0].children] == ["kid1", "kid2"]
          and rep.deepest() == 1 and rep.loops == 3,
          "one root, two children, depth 1")

    # 1b. A SPAWNED child announces no parent on its own `init`: the PARENT
    # records `child_return` naming it. Reading only `init` rendered a genuinely
    # nested run as a flat list, hiding the one structure this report exists to
    # show, so the real runtime edge is exercised here against live spawn().
    from ..loop.recursive_loop import Loop, LoopConfig, StepOutcome
    slg = LoopLedger()
    parent_loop = Loop("parent that spawns",
                       LoopConfig(framework="custom", custom_steps=("act",),
                                  power="light"), ledger=slg)
    kid = parent_loop.spawn("a real spawned child")
    while not kid.is_terminal:
        kid.run_next_iteration(
            handler=lambda loop, step, ctx: StepOutcome(
                output="done", mode="deterministic", confidence=0.9))
    spawned = report_from_ledger(slg.events)
    parent_node = spawned.by_id.get(parent_loop.loop_id)
    check("a_spawned_child_nests_under_the_parent_that_recorded_it",
          parent_node is not None
          and kid.loop_id in [c.loop_id for c in parent_node.children]
          and spawned.by_id[kid.loop_id].parent == parent_loop.loop_id
          and spawned.deepest() >= 1,
          f"{kid.loop_id} nests under {parent_loop.loop_id} via child_return")

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
          rep.roots[0].seconds == 4.0 and kid2.seconds == 1.0,
          "root 4.0s spanning its children")

    # 4. UNKNOWN IS NOT ZERO. The live LoopLedger always stamps `ts`, so this
    # path is about a ledger from somewhere else: a replay, an import, an
    # older receipt: where the field is genuinely absent. Reporting 0.0 there
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
          "root" in t and "mistral" in t
          and "| Model calls | 1 |" in m and "mistral" in m
          and "Loop report" in h and "mistral" in h
          and "200" in h,
          "text, markdown and html agree")
    check("the_html_report_is_self_contained",
          "<script" not in h.lower() and "http://" not in h
          and "https://" not in h and "<style>" in h
          and "prefers-color-scheme" in h,
          "no external assets, no network, both themes")

    # 7. ADVERSARIAL: an event naming a parent that never opened must not drop
    # the loop from the report, and a self-parented loop must not hang it.
    lg3 = LoopLedger()
    lg3.record(loop_id="orphan", event="init", goal="lost parent",
               parent="never_existed")
    lg3.record(loop_id="selfref", event="init", goal="self parent",
               parent="selfref")
    r3 = report_from_ledger(lg3.events)
    check("orphans_and_self_parents_are_reported_not_dropped_or_hung",
          r3.loops == 2 and len(r3.roots) == 2
          and {n.loop_id for n in r3.roots} == {"orphan", "selfref"},
          "every loop appears exactly once")

    # 8. A persisted Chronicle uses event_type/detail fields. The canonical
    # adapter must preserve the goal, model-call count, and tokens.
    import shutil
    import tempfile
    from ..static_architecture.chronicle import Chronicle
    saved_ledger = LoopLedger()
    saved_ledger.record(loop_id="saved", event="init", goal="saved work")
    saved_ledger.record(loop_id="saved", event="run_step", step="decide",
                        mode="hybrid", output="selected")
    saved_ledger.record(loop_id="saved", event="terminal", reason="done")
    saved_chronicle = Chronicle.from_ledger(
        saved_ledger.events, run_id="saved-report",
        usage_log=[{"model": "test-model", "prompt_tokens": 10,
                    "eval_tokens": 20}])
    saved_chronicle.commit()
    saved_root = tempfile.mkdtemp(prefix="loop_report_saved_")
    saved_chronicle.save(saved_root)
    saved_report = report_from_run(saved_root, "saved-report")
    check("saved_chronicle_report_preserves_usage_and_goal",
          saved_report.model_calls == 1
          and saved_report.total_tokens == 30
          and saved_report.by_id["saved"].goal == "saved work"
          and saved_report.chain_intact is True,
          "1 call, 30 tokens, goal and chain preserved")
    shutil.rmtree(saved_root, ignore_errors=True)

    passed = sum(1 for t in results if t["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
