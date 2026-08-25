"""4 — Reports: see what the loops actually did.

    python examples/04_reports.py

A run emits a verifiable chain of events. Complete, checkable — and unreadable
as raw JSON. This turns it into something a person can read, in three
renderings over the same projection:

    text      an indented tree for a terminal
    markdown  paste into an issue or a pull request
    html      a self-contained page, no assets, no network

Every figure comes from the ledger the run emitted. Nothing is recomputed from
another source, and a value the ledger does not carry shows as unknown rather
than being filled in with something plausible.

From the command line, over saved runs:

    loop-engine --runs                                  # what is available
    loop-engine --report                                # most recent, as text
    loop-engine --report <run_id> --format markdown
    loop-engine --report --format html --out report.html
"""

import os
import tempfile

from loop_engine import LoopLedger
from loop_engine.loop.recursive_loop import Loop, LoopConfig, StepOutcome
from loop_engine.code_nodes.loop_report import (report_from_ledger,
                                                render_text, render_markdown,
                                                render_html, write_report)


def a_nested_run():
    """A loop of loops — the structure a report exists to make visible."""
    ledger = LoopLedger()
    step = LoopConfig(framework="custom", custom_steps=("act",), power="light")
    root = Loop("prepare a quarterly plan", step, ledger=ledger)

    def run_to_completion(loop):
        while not loop.is_terminal:
            loop.run_next_iteration(
                handler=lambda l, s, c: StepOutcome(
                    output="done", mode="deterministic", confidence=0.9))

    for goal in ("gather last quarter's numbers", "draft the objectives"):
        child = run_to_completion(root.spawn(goal)) or None
    # a grandchild, so the tree has real depth
    child = root.spawn("review the draft")
    run_to_completion(child)
    run_to_completion(child.spawn("check one assumption"))
    return ledger


def main():
    ledger = a_nested_run()
    report = report_from_ledger(ledger.events, run_id="quarterly-plan")

    print("=" * 62)
    print("TEXT — for a terminal")
    print("=" * 62)
    print(render_text(report))
    print()

    print("=" * 62)
    print("MARKDOWN — for an issue or pull request (first lines)")
    print("=" * 62)
    print("\n".join(render_markdown(report).splitlines()[:12]))
    print("...")
    print()

    print("=" * 62)
    print("STRUCTURED — for a dashboard or a downstream check")
    print("=" * 62)
    s = report.summary()
    for k in ("loops", "events", "max_depth", "model_calls", "total_tokens"):
        print(f"  {k:<14}{s[k]}")
    print(f"  {'families':<14}{len(s['event_families'])} distinct")
    print()

    out = os.path.join(tempfile.gettempdir(), "loop-engine-report.html")
    write_report(report, out)
    size = os.path.getsize(out)
    html = render_html(report)
    print("=" * 62)
    print("HTML — self-contained, openable straight from disk")
    print("=" * 62)
    print(f"  wrote {out}  ({size:,} bytes)")
    print(f"  external requests: "
          f"{'none' if 'http' not in html else 'SOME — investigate'}")
    print(f"  adapts to dark mode: "
          f"{'yes' if 'prefers-color-scheme' in html else 'no'}")


if __name__ == "__main__":
    main()
