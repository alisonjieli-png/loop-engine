"""CLI projections for saved runs and reports.

Run History and product outcomes remain owned by their canonical stores. This
module only renders those verified records for terminal users.
"""
from __future__ import annotations

import html
import json


def run_history_command(args) -> int:
    """List saved runs or render one report in the requested format."""
    from .core.run_history import (
        RunHistoryIntegrityError, default_runs_dir,
        load_saved_run_bundle, saved_run_ids)
    from .code_nodes.loop_report import (
        report_from_run, render_html, render_markdown, render_text)

    runs_dir = default_runs_dir(args.runs_dir or "")
    saved = saved_run_ids(runs_dir)
    if args.runs:
        rows = []
        for run_id in saved:
            try:
                bundle = load_saved_run_bundle(runs_dir, run_id)
                outcome = bundle.outcome or {}
                rows.append({
                    "run_id": run_id, "valid": True,
                    "events": len(bundle.history.event_log),
                    "terminal_code": str(
                        outcome.get("terminal_code") or "legacy"),
                    "solved": bool(outcome.get("solved")),
                    "artifacts": len(outcome.get("artifacts") or ()),
                    "summary": str(outcome.get("summary") or ""),
                    "error": "",
                })
            except (OSError, ValueError, RunHistoryIntegrityError) as exc:
                rows.append({
                    "run_id": run_id, "valid": False, "events": 0,
                    "terminal_code": "RUN_INVALID", "solved": False,
                    "artifacts": 0, "summary": "Unreadable saved run",
                    "error": str(exc)[:240],
                })
        if args.format == "json":
            print(json.dumps({
                "record_type": "saved_runs/v1", "runs": rows,
                "invalid_runs": sum(not row["valid"] for row in rows),
                "runs_dir": runs_dir}, indent=1))
        elif args.format == "markdown":
            print("# Saved runs\n")
            print("| Run | Terminal | Artifacts | Valid |\n|---|---|---:|---|")
            for row in rows:
                print(f"| `{row['run_id']}` | `{row['terminal_code']}` | "
                      f"{row['artifacts']} | "
                      f"{'yes' if row['valid'] else 'NO'} |")
        elif args.format == "html":
            items = "".join(
                f"<li><code>{html.escape(row['run_id'])}</code>: "
                f"{html.escape(row['terminal_code'])}, "
                f"{row['artifacts']} artifact(s)</li>" for row in rows)
            print(f"<!doctype html><meta charset='utf-8'><title>Saved "
                  f"runs</title><h1>Saved runs</h1><ul>{items}</ul>")
        else:
            if not rows:
                print("No saved runs yet. Run solve to create one.")
            else:
                print(f"{len(rows)} saved run(s):")
                for row in rows:
                    suffix = (f"{row['terminal_code']}, "
                              f"{row['artifacts']} artifact(s)"
                              if row["valid"] else
                              f"RUN_INVALID: {row['error']}")
                    print(f"  {row['run_id']}: {suffix}")
        return 0

    if not saved:
        value = {"record_type": "loop_report_error/v1",
                 "error_code": "NO_SAVED_RUNS",
                 "error": "No saved runs to report on yet."}
        print(json.dumps(value, indent=1) if args.format == "json"
              else value["error"])
        return 1
    run_id = saved[-1] if args.report == "@last" else args.report
    if run_id not in saved:
        value = {"record_type": "loop_report_error/v1",
                 "error_code": "RUN_NOT_FOUND",
                 "error": f"No saved run named {run_id!r}.",
                 "known_runs": saved[:8]}
        print(json.dumps(value, indent=1) if args.format == "json"
              else value["error"] + " Known runs: "
              + ", ".join(value["known_runs"]))
        return 1
    try:
        report = report_from_run(runs_dir, run_id)
    except (OSError, ValueError, RunHistoryIntegrityError) as exc:
        value = {"record_type": "loop_report_error/v1",
                 "error_code": "RUN_HISTORY_INVALID",
                 "run_id": run_id, "error": str(exc)}
        print(json.dumps(value, indent=1) if args.format == "json"
              else f"Run {run_id} is invalid: {exc}")
        return 1
    body = {"text": render_text, "markdown": render_markdown,
            "html": render_html,
            "json": lambda value: json.dumps(value.as_dict(), indent=1)
            }[args.format](report)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as stream:
            stream.write(body)
        print(f"wrote {args.format} report for {run_id} -> {args.out}")
    else:
        print(body)
    return 0


__all__ = ("run_history_command",)
