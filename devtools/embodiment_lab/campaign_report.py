"""One campaign as a self-contained page: what ran, what it proved, what it
cost, and what it has not touched yet.

The report reads the campaign's exported records (``campaign.json``,
``status.json``, ``population-index.json``, each cell's ``status.json`` and
``outcome.json``) and each cell's projection when it can be read; a cell the
running worker holds the writer lock on is shown as in progress, never
guessed. It renders no external asset and runs nothing. It counts model
calls and provider-reported tokens from the outcome each cell exported;
those are the cell's own accounting, not an independent measurement.
"""
from __future__ import annotations

import argparse
import html
import json
from datetime import datetime, timezone
from pathlib import Path

from loop_engine.core.run_history import MODEL_INVOCATION_EVENT, RunHistory
from loop_engine.core.run_history_paths import saved_run_ids
from loop_engine.generation.space import INTEGER_RANGE, ConfigurationSpace, GenerationError, parse_json

from .trial_evidence import REQUIRED_LINKS, campaign_evidence_summary

REPORT_RECORD_TYPE = "campaign_report/v1"


def _load(path):
    path = Path(path)
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text())
    except ValueError:
        return {}


def _tokens(outcome) -> dict:
    """Provider-reported tokens the outcome carries, summed over its usage
    entries, with the entries that carried no counts kept as a number."""
    prompt = completion = 0
    unknown = 0
    for entry in outcome.get("model_usage") or ():
        if not isinstance(entry, dict):
            continue
        p = entry.get("prompt_tokens", entry.get("input_tokens"))
        c = entry.get("eval_tokens", entry.get("completion_tokens", entry.get("output_tokens")))
        if isinstance(p, int) and isinstance(c, int):
            prompt += p
            completion += c
        else:
            unknown += 1
    return {"prompt_tokens": prompt, "completion_tokens": completion,
            "total_tokens": prompt + completion, "entries_without_counts": unknown}


def access_probes(root) -> list:
    """Every saved access-probe history under the campaign root, with its
    physical model calls counted from its own events. Probe calls are the
    worker's readiness checks, kept apart from task executions so neither
    denominator absorbs the other."""
    store = Path(root) / "provider-access"
    probes = []
    if not store.is_dir():
        return probes
    try:
        run_ids = saved_run_ids(str(store))
    except Exception:
        run_ids = sorted(p.name for p in store.iterdir() if p.is_dir())
    for run_id in run_ids:
        try:
            history = RunHistory.load(str(store), run_id)
            calls = sum(1 for event in history.event_log if event.event_type == MODEL_INVOCATION_EVENT)
            probes.append({"run_id": run_id, "model_calls": calls,
                           "intact": bool(history.verify_chain().get("intact")), "readable": True})
        except Exception as exc:  # a broken probe history is reported, never guessed
            probes.append({"run_id": run_id, "model_calls": None, "intact": False,
                           "readable": False, "error_type": type(exc).__name__})
    return probes


def campaign_grid(space_record, cells) -> dict:
    """Every visited cell placed in the campaign's declared configuration
    grid: its index in the space, its coordinate on each axis, and the
    counts by axis level, so the fabric of the search (which
    configurations ran, for which families, with what outcome) is one
    record. A cell whose configuration is not an address of the declared
    space is listed as unindexed, never placed by guess."""
    if not isinstance(space_record, dict) or "axes" not in space_record:
        return {"declared": False, "cardinality": 0, "axes": [], "placed": [], "unindexed": 0,
                "by_level": {}}
    try:
        space = ConfigurationSpace.from_dict(space_record)
    except (GenerationError, TypeError, ValueError, KeyError) as exc:
        return {"declared": False, "cardinality": 0, "axes": [], "placed": [], "unindexed": len(cells),
                "by_level": {}, "error_type": type(exc).__name__}
    axes = []
    for axis in space.axes:
        if axis.value_kind == INTEGER_RANGE:
            levels = [str(v) for v in range(axis.minimum, axis.maximum + 1)]
        else:
            levels = [str(parse_json(value)) for value in axis.encoded_values]
        axes.append({"dimension_id": axis.dimension_id, "levels": levels})
    placed, unindexed = [], 0
    by_level = {axis["dimension_id"]: {level: {"cells": 0, "finished": 0, "failed": 0}
                                      for level in axis["levels"]} for axis in axes}
    for cell in cells:
        configuration = cell.get("configuration")
        try:
            index = space.index_of(configuration)
        except (GenerationError, TypeError, ValueError, KeyError):
            unindexed += 1
            continue
        coordinates = []
        remainder = index
        for axis, declared in zip(reversed(space.axes), reversed(axes)):
            offset = remainder % axis.cardinality
            remainder //= axis.cardinality
            coordinates.append(declared["levels"][offset])
        coordinates.reverse()
        for declared, level in zip(axes, coordinates):
            counts = by_level[declared["dimension_id"]][level]
            counts["cells"] += 1
            if cell.get("status") == "finished":
                counts["finished"] += 1
            elif cell.get("status") == "failed":
                counts["failed"] += 1
        placed.append({"index": index, "coordinates": coordinates, "task_id": cell.get("task_id"),
                       "family": cell.get("family"), "status": cell.get("status"),
                       "engine_terminal": cell.get("engine_terminal")})
    return {"declared": True, "cardinality": space.cardinality, "space_id": space.space_id,
            "axes": axes, "placed": placed, "unindexed": unindexed, "by_level": by_level}


def campaign_report(root) -> dict:
    """The campaign's records, cells, accounting, and coverage as one plain
    record; every number names the file it came from by its section."""
    root = Path(root)
    campaign = _load(root / "campaign.json")
    status = _load(root / "status.json")
    population = _load(root / "population-index.json")
    tasks = [row for row in (population.get("tasks") or []) if isinstance(row, dict)]
    family_of = {row.get("id"): row.get("job_family", "") for row in tasks}
    families = {}
    for row in tasks:
        family = row.get("job_family", "")
        families.setdefault(family, {"tasks": 0, "visited": 0, "finished": 0, "failed": 0})
        families[family]["tasks"] += 1
    evidence = campaign_evidence_summary(root)
    cells = []
    visited = set()
    totals = {"model_calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0,
              "elapsed_seconds": 0.0, "cells_with_unknown_calls": 0}
    for report in evidence["reports"]:
        cell = Path(report["cell"])
        outcome = _load(cell / "outcome.json")
        tokens = _tokens(outcome)
        task_id = report.get("task_id") or ""
        family = family_of.get(task_id, "")
        calls = report.get("physical_model_calls")
        if calls is None:
            calls = report.get("claimed_model_calls")
        if isinstance(calls, int):
            totals["model_calls"] += calls
        else:
            totals["cells_with_unknown_calls"] += 1
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            totals[key] += tokens[key]
        elapsed = outcome.get("elapsed_seconds")
        if isinstance(elapsed, (int, float)):
            totals["elapsed_seconds"] += float(elapsed)
        if task_id:
            visited.add(task_id)
            if family in families:
                families[family]["visited"] += 1
                if report.get("status") == "finished":
                    families[family]["finished"] += 1
                elif report.get("status") == "failed":
                    families[family]["failed"] += 1
        exported = _load(cell / "status.json")
        cells.append({
            "task_id": task_id, "family": family, "occurrence": cell.name,
            "configuration": exported.get("configuration"),
            "status": report.get("status"), "engine_terminal": report.get("engine_terminal"),
            "projection_readable": report.get("projection_readable", True),
            "model_calls": calls, "accounting_complete": report.get("accounting_complete"),
            "tokens": tokens, "elapsed_seconds": elapsed,
            "artifacts": report["links"].get("delivered_artifacts", 0),
            "step_checkpoints": report["links"].get("step_history", 0),
            "complete": report.get("complete"), "gaps": report.get("gaps", []),
            "disagreements": report.get("disagreements", {}),
        })
    probes = access_probes(root)
    totals["probe_calls"] = sum(p["model_calls"] for p in probes if isinstance(p["model_calls"], int))
    totals["probes"] = len(probes)
    totals["probes_unreadable"] = sum(1 for p in probes if not p["readable"])
    by_gap = {name: evidence["gaps"].get(name, 0) for name in REQUIRED_LINKS}
    return {
        "record_type": REPORT_RECORD_TYPE, "root": str(root),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "campaign": {key: campaign.get(key) for key in (
            "campaign_id", "task_count", "raw_configurations_per_task", "raw_task_configuration_cells",
            "valid_task_configuration_cells", "configuration_space_digest", "engine_digest",
            "selected_route_name", "not_before_utc", "provider_failover", "search_policy",
            "optimizer_policy", "harnesses", "created_at", "status")},
        "worker": {key: status.get(key) for key in (
            "status", "worker_pid", "updated_at", "not_before_utc", "provider", "cursor",
            "next_probe_seconds", "next_task")},
        "provider_observation": status.get("provider_observation") or {},
        "population": {"tasks": len(tasks), "families": families,
                       "public_population_digest": population.get("public_population_digest")},
        "coverage": {"tasks_visited": len(visited), "tasks_total": len(tasks),
                     "cells": len(cells),
                     "finished": evidence["finished"], "failed": evidence["failed"],
                     "in_progress": sum(1 for c in cells if c["status"] not in ("finished", "failed")),
                     "projection_locked": evidence.get("projection_locked", 0)},
        "evidence": {"complete": evidence["complete"], "trials": evidence["trials"],
                     "with_disagreements": evidence.get("with_disagreements", 0),
                     "gaps": by_gap, "required_links": list(REQUIRED_LINKS)},
        "accounting": totals,
        "access_probes": probes,
        "grid": campaign_grid(campaign.get("configuration_space"), cells),
        "cells": cells,
    }


def _esc(value) -> str:
    return html.escape("" if value is None else str(value))


def _bar(count: int, total: int, label: str) -> str:
    width = 0 if not total else round(100 * count / total)
    return (f'<div class="bar" title="{_esc(label)}"><span style="width:{width}%"></span>'
            f'<b>{_esc(label)}</b> {count} of {total}</div>')


def _fabric_svg(report: dict) -> str:
    """The grid as one drawing: configuration index across, job family
    down, one mark per visited cell coloured by status, drawn to the
    space's own cardinality so an untouched column is visibly empty."""
    grid = report["grid"]
    families = sorted(report["population"]["families"]) or sorted({p["family"] for p in grid["placed"]})
    if not grid["declared"] or not families:
        return "<p class='muted'>The campaign declares no configuration space, so there is no grid to draw.</p>"
    columns, rows = max(grid["cardinality"], 1), len(families)
    cell_w, cell_h, left, top = 3, 14, 150, 18
    width, height = left + columns * cell_w + 10, top + rows * cell_h + 10
    marks = []
    for item in grid["placed"]:
        if item["family"] not in families:
            continue
        y = top + families.index(item["family"]) * cell_h
        colour = {"finished": "var(--ok)", "failed": "var(--bad)"}.get(item["status"], "var(--warn)")
        marks.append(f'<rect x="{left + item["index"] * cell_w}" y="{y + 1}" width="{cell_w}" height="{cell_h - 2}" '
                     f'fill="{colour}"><title>{_esc(item["task_id"])} at {item["index"]}: {_esc(item["status"])} '
                     f'{_esc(item["engine_terminal"] or "")} ({_esc(", ".join(item["coordinates"]))})</title></rect>')
    labels = "".join(f'<text x="{left - 6}" y="{top + i * cell_h + cell_h - 3}" text-anchor="end" font-size="10" fill="var(--ink)">{_esc(name or "unnamed")}</text>'
                     for i, name in enumerate(families))
    ticks = "".join(f'<text x="{left + i * cell_w}" y="{top - 5}" font-size="9" fill="var(--muted)">{i}</text>'
                    for i in range(0, columns, max(1, columns // 8)))
    return (f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" '
            f'aria-label="campaign grid: {columns} configurations by {rows} families">'
            f'<rect x="{left}" y="{top}" width="{columns * cell_w}" height="{rows * cell_h}" fill="var(--code)"/>'
            f'{labels}{ticks}{"".join(marks)}</svg>')


def render_campaign_html(report: dict) -> str:
    """A self-contained page: no external asset, no script, no network."""
    camp, worker, cov, ev, acc = (report["campaign"], report["worker"], report["coverage"],
                                  report["evidence"], report["accounting"])
    facts = [
        ("campaign", camp.get("campaign_id")), ("worker status", worker.get("status")),
        ("tasks", camp.get("task_count")), ("configurations per task", camp.get("raw_configurations_per_task")),
        ("valid cells", camp.get("valid_task_configuration_cells")),
        ("route", camp.get("selected_route_name")), ("provider", worker.get("provider")),
        ("not before", worker.get("not_before_utc") or camp.get("not_before_utc")),
        ("engine digest", (camp.get("engine_digest") or "")[:16]),
        ("space digest", (camp.get("configuration_space_digest") or "")[:16]),
        ("updated", worker.get("updated_at")), ("generated", report["generated_at"]),
    ]
    facts_html = "".join(f"<div><dt>{_esc(k)}</dt><dd>{_esc(v)}</dd></div>" for k, v in facts)
    bars = [_bar(cov["tasks_visited"], cov["tasks_total"], "tasks visited"),
            _bar(cov["finished"], max(cov["cells"], 1), "cells finished"),
            _bar(cov["failed"], max(cov["cells"], 1), "cells failed"),
            _bar(ev["complete"], max(ev["trials"], 1), "cells with complete evidence")]
    gap_rows = "".join(f"<tr><td>{_esc(name)}</td><td class='num'>{ev['gaps'][name]}</td></tr>"
                       for name in ev["required_links"])
    family_rows = "".join(
        f"<tr><td>{_esc(name or 'unnamed')}</td><td class='num'>{row['tasks']}</td>"
        f"<td class='num'>{row['visited']}</td><td class='num'>{row['finished']}</td>"
        f"<td class='num'>{row['failed']}</td></tr>"
        for name, row in sorted(report["population"]["families"].items()))
    cell_rows = "".join(
        f"<tr><td>{_esc(c['task_id'])}</td><td>{_esc(c['family'])}</td><td>{_esc(c['occurrence'])}</td>"
        f"<td><span class='chip {_esc(c['status'])}'>{_esc(c['status'])}</span>"
        + ("" if c["projection_readable"] else " <span class='chip locked'>projection locked</span>")
        + f"</td><td>{_esc(c['engine_terminal'])}</td>"
        f"<td class='num'>{_esc(c['model_calls'])}</td><td class='num'>{c['tokens']['prompt_tokens']}</td>"
        f"<td class='num'>{c['tokens']['completion_tokens']}</td><td class='num'>{c['step_checkpoints']}</td>"
        f"<td class='num'>{c['artifacts']}</td><td>{'complete' if c['complete'] else _esc(', '.join(c['gaps']))}</td>"
        f"<td>{_esc(', '.join(c['disagreements']) or '')}</td></tr>"
        for c in report["cells"])
    observation = report.get("provider_observation") or {}
    observation_html = ("<p class='muted'>No provider observation exported yet.</p>" if not observation else
                        "<dl class='facts'>" + "".join(
                            f"<div><dt>{_esc(k)}</dt><dd>{_esc(v)}</dd></div>"
                            for k, v in observation.items() if not isinstance(v, (dict, list))) + "</dl>")
    unknown = acc["cells_with_unknown_calls"]
    grid = report["grid"]
    fabric = _fabric_svg(report)
    grid_summary = (f"{len(grid['placed'])} cells placed in a space of {grid['cardinality']} configurations "
                    f"({' × '.join(a['dimension_id'] + '[' + str(len(a['levels'])) + ']' for a in grid['axes'])}); "
                    f"{grid['unindexed']} cells carry a configuration outside the declared space."
                    if grid["declared"] else "No configuration space is declared for this campaign.")
    level_rows = "".join(
        f"<tr><td>{_esc(axis)}</td><td>{_esc(level)}</td><td class='num'>{counts['cells']}</td>"
        f"<td class='num'>{counts['finished']}</td><td class='num'>{counts['failed']}</td></tr>"
        for axis, levels in grid["by_level"].items() for level, counts in levels.items())
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Campaign {_esc(camp.get('campaign_id') or Path(report['root']).name)}</title>
<style>
:root {{ --bg:#f6f7f8; --surface:#fff; --ink:#1c2430; --muted:#5d6874; --line:#d9dee4; --accent:#155e75;
        --ok:#2c6b44; --ok-bg:#e4f2e8; --bad:#9e2b2b; --bad-bg:#fae8e8; --warn:#7f5300; --warn-bg:#fbf1dc; --code:#e9edf1; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#101418; --surface:#171c22; --ink:#e5e9ee; --muted:#9aa5b1; --line:#2b333c;
        --accent:#6cc3d5; --ok:#86cd9e; --ok-bg:#15271b; --bad:#f09090; --bad-bg:#33191b; --warn:#e6b85e; --warn-bg:#2f2713; --code:#1e252d; }} }}
* {{ box-sizing:border-box }} body {{ margin:0; background:var(--bg); color:var(--ink); font:15px/1.5 system-ui, sans-serif }}
main {{ max-width:1200px; margin:0 auto; padding:1.5rem 1.25rem 4rem; display:grid; gap:1.75rem }}
h1 {{ font-size:1.6rem; margin:0 }} h2 {{ font-size:1.15rem; margin:0 0 .6rem }} p {{ max-width:70ch }} .muted {{ color:var(--muted) }}
dl.facts {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:.6rem 1.2rem; margin:0 }}
dl.facts div {{ border-top:2px solid var(--line); padding-top:.3rem }} dt {{ font-size:.72rem; letter-spacing:.06em; text-transform:uppercase; color:var(--muted) }}
dd {{ margin:.1rem 0 0; font-family:ui-monospace,monospace; font-size:.9rem; overflow-wrap:anywhere }}
.bars {{ display:grid; gap:.5rem; max-width:52rem }} .bar {{ position:relative; background:var(--code); border-radius:4px; padding:.35rem .6rem; overflow:hidden }}
.bar span {{ position:absolute; inset:0 auto 0 0; background:var(--accent); opacity:.22 }} .bar b {{ font-weight:600 }}
.wrap {{ overflow-x:auto; border:1px solid var(--line); border-radius:6px; background:var(--surface) }}
table {{ border-collapse:collapse; width:100%; font-size:.9rem }} th,td {{ text-align:left; padding:.45rem .6rem; border-bottom:1px solid var(--line); vertical-align:top }}
th {{ background:var(--code); font-size:.8rem; position:sticky; top:0 }} td.num {{ text-align:right; font-variant-numeric:tabular-nums }}
.chip {{ font-family:ui-monospace,monospace; font-size:.72rem; padding:.1rem .4rem; border-radius:3px; background:var(--code) }}
.chip.finished {{ color:var(--ok); background:var(--ok-bg) }} .chip.failed {{ color:var(--bad); background:var(--bad-bg) }} .chip.locked {{ color:var(--warn); background:var(--warn-bg) }}
</style></head><body><main>
<header><div class="muted" style="font-size:.78rem;letter-spacing:.08em;text-transform:uppercase">Loop Engine task-database campaign</div>
<h1>{_esc(camp.get('campaign_id') or Path(report['root']).name)}</h1>
<p>What ran, what it proved link by link, what it cost in model calls and provider-reported tokens, and which of the population's tasks it has not touched. Every count comes from the records the runner exported; a cell the running worker holds locked is shown as in progress, never guessed.</p></header>
<section><dl class="facts">{facts_html}</dl></section>
<section><h2>Coverage and evidence</h2><div class="bars">{''.join(bars)}</div>
<p class="muted">{cov['cells']} cells written, {cov['in_progress']} in progress, {cov['projection_locked']} with a locked projection, {ev['with_disagreements']} where the recorded counts and the re-verified counts disagree.</p></section>
<section><h2>Accounting</h2><dl class="facts">
<div><dt>model calls</dt><dd>{acc['model_calls']}{' (+' + str(unknown) + ' cells unknown)' if unknown else ''}</dd></div>
<div><dt>prompt tokens</dt><dd>{acc['prompt_tokens']}</dd></div><div><dt>completion tokens</dt><dd>{acc['completion_tokens']}</dd></div>
<div><dt>total tokens</dt><dd>{acc['total_tokens']}</dd></div><div><dt>elapsed seconds</dt><dd>{round(acc['elapsed_seconds'], 1)}</dd></div>
<div><dt>access probe calls</dt><dd>{acc['probe_calls']} in {acc['probes']} probes{' (' + str(acc['probes_unreadable']) + ' unreadable)' if acc['probes_unreadable'] else ''}</dd></div></dl>
<p class="muted">Task model calls are each cell's physical count from its Run History where the history could be read, else the outcome's claim; tokens are the provider-reported usage the outcome carries. Access probe calls are the worker's readiness checks, counted from their own saved histories and kept apart from task calls.</p></section>
<section><h2>Provider observation</h2>{observation_html}</section>
<section><h2>Grid</h2><p class="muted">{grid_summary}</p><div class="wrap" style="padding:.5rem">{fabric}</div>
<div class="wrap"><table><thead><tr><th>axis</th><th>level</th><th class="num">cells</th><th class="num">finished</th><th class="num">failed</th></tr></thead><tbody>{level_rows}</tbody></table></div></section>
<section><h2>Evidence gaps by link</h2><div class="wrap"><table><thead><tr><th>link</th><th class="num">cells missing it</th></tr></thead><tbody>{gap_rows}</tbody></table></div></section>
<section><h2>Population by job family</h2><div class="wrap"><table><thead><tr><th>family</th><th class="num">tasks</th><th class="num">visited</th><th class="num">finished</th><th class="num">failed</th></tr></thead><tbody>{family_rows}</tbody></table></div></section>
<section><h2>Cells</h2><div class="wrap"><table><thead><tr><th>task</th><th>family</th><th>occurrence</th><th>status</th><th>terminal</th><th class="num">calls</th><th class="num">prompt</th><th class="num">completion</th><th class="num">checkpoints</th><th class="num">artifacts</th><th>evidence</th><th>disagreements</th></tr></thead><tbody>{cell_rows or '<tr><td colspan="12" class="muted">No cell has been written yet.</td></tr>'}</tbody></table></div></section>
</main></body></html>
"""


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Render one campaign root as a self-contained page.")
    parser.add_argument("root")
    parser.add_argument("--html", help="write the page here")
    parser.add_argument("--json", help="write the plain report here")
    args = parser.parse_args(argv)
    report = campaign_report(args.root)
    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=1, sort_keys=True))
    if args.html:
        Path(args.html).write_text(render_campaign_html(report))
    if not args.html and not args.json:
        print(json.dumps({key: report[key] for key in ("coverage", "evidence", "accounting", "worker")},
                         indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
