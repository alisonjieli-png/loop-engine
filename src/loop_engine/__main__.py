"""Command-line interface for Loop Engine.

    PYTHONPATH=. python3 -m loop_engine --self-test
    ... --categories     # print the resolver categories, levels, and move types
"""

from __future__ import annotations

import argparse
import json
import sys

from .loop.resolvers import RESOLVER_CATEGORIES, DEFAULT_CATEGORY_LEVEL
from .loop.moves import MOVE_TYPES
from ._self_test import self_test


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="loop-engine",
                                     description=__doc__.splitlines()[0])
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--categories", action="store_true",
                        help="print resolver categories, levels, and move types")
    parser.add_argument("--map", action="store_true",
                        help="print the nine-step kernel map: where every "
                        "capability lives")
    parser.add_argument("--live-demo", action="store_true",
                        help="watch a REAL PractitionerLoop run live: "
                        "localhost page with the step rail + console log "
                        "(deterministic stage-0 fixture, zero model calls)")
    parser.add_argument("--studio", action="store_true",
                        help="serve Loop Engine Studio (local, read-only, "
                        "Chronicle-backed) on --port")
    parser.add_argument("--port", type=int,
                        help="local port (Studio defaults to 8765; live demo "
                             "defaults to 8770)")
    parser.add_argument("--runs-dir",
                        help="shared Chronicle directory; defaults to "
                             "$LOOP_ENGINE_RUNS_DIR or ~/.loop-engine/runs")
    parser.add_argument("--conformance", action="store_true",
                        help="run the machine-enforced conformance scan + "
                        "zero-tolerance gates; writes "
                        "architecture_conformance.json; exits nonzero on any "
                        "violation")
    parser.add_argument("--report", metavar="RUN_ID", nargs="?", const="@last",
                        help="render a loop report for a saved run "
                             "(default: the most recent). Use --format and "
                             "--out to choose the rendering and destination.")
    parser.add_argument("--runs", action="store_true",
                        help="list the saved runs a report can be built from")
    parser.add_argument("--format", default="text",
                        choices=("text", "markdown", "html", "json"),
                        help="report rendering (default: text)")
    parser.add_argument("--out", metavar="PATH",
                        help="write the report to PATH instead of stdout")
    parser.add_argument("--setup", action="store_true",
                        help="guided walkthrough: checks the installation, "
                             "providers, your own server and knowledge, then "
                             "runs a real loop")
    parser.add_argument("--example",
                        choices=("support-queue", "intelligence-layers",
                                 "context-seed"),
                        help="run a useful example included with the package")
    # `loop-engine setup` reads better than a flag, so accept the bare word too
    if argv is None and len(sys.argv) > 1 and sys.argv[1] == "setup":
        sys.argv[1] = "--setup"
    args = parser.parse_args(argv)
    if args.setup:
        from .code_nodes.guided_setup import run_setup
        return 0 if run_setup().ready else 1
    if args.example:
        from .code_nodes.public_examples import run_example
        print(run_example(args.example))
        return 0
    if args.runs or args.report:
        import os
        from .static_architecture.chronicle import default_runs_dir
        from .code_nodes.loop_report import (report_from_run, render_text,
                                             render_markdown, render_html)
        runs_dir = default_runs_dir(args.runs_dir or "")
        saved = sorted(os.listdir(runs_dir)) if os.path.isdir(runs_dir) else []
        if args.runs:
            if not saved:
                print("No saved runs yet. Run a loop first — every run that "
                      "calls Chronicle.save() appears here.")
                return 0
            print(f"{len(saved)} saved run(s):")
            for r in saved:
                print(f"  {r}")
            return 0
        if not saved:
            print("No saved runs to report on yet.")
            return 1
        run_id = saved[-1] if args.report == "@last" else args.report
        if run_id not in saved:
            print(f"No saved run named {run_id!r}. Known runs: "
                  + ", ".join(saved[:8]) + ("…" if len(saved) > 8 else ""))
            return 1
        rep = report_from_run(runs_dir, run_id)
        body = {"text": render_text, "markdown": render_markdown,
                "html": render_html,
                "json": lambda r: json.dumps(r.as_dict(), indent=1)
                }[args.format](rep)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(body)
            print(f"wrote {args.format} report for {run_id} -> {args.out}")
        else:
            print(body)
        return 0
    if args.live_demo:
        from .code_nodes.live_run_demo import run_live_demo
        run_live_demo(port=args.port or 8770, pace_seconds=0.6,
                      serve_forever=True, runs_dir=args.runs_dir or "")
        return 0
    if args.studio:
        from .static_architecture.studio_server import serve
        serve(args.port or 8765, runs_dir=args.runs_dir or "")
        return 0
    if args.conformance:
        from .conformance_report import run_conformance
        report = run_conformance()
        print(report["human_summary"])
        return 0 if report["all_gates_pass"] else 1
    if args.map:
        from .architecture_map import render_map as render_architecture
        from .loop.step_registry import render_map
        print(render_architecture())
        print()
        print(render_map())
        return 0
    if args.categories:
        print(json.dumps({"resolver_categories": list(RESOLVER_CATEGORIES),
                          "default_levels": DEFAULT_CATEGORY_LEVEL,
                          "move_types": list(MOVE_TYPES)}, indent=1))
        return 0
    if args.self_test:
        report = self_test()
        print(json.dumps(report, indent=1))
        return 0 if report["all_passed"] else 1
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
