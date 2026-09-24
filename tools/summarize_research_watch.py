"""Summarize one research source watch report as Markdown for an issue, or count its changes.

Reads a research_source_watch_report/v1 written by tools/refresh_research_sources.py.
A change is a prompt for the research team to read the source again; it is not a
source claim, an approval or runtime authority. Standard library only; no network.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPORT_TYPE = "research_source_watch_report/v1"


def load(path):
    report = json.loads(Path(path).read_text("utf-8"))
    if report.get("record_type") != REPORT_TYPE or not isinstance(report.get("sources"), list):
        raise SystemExit("not a research source watch report")
    return report


def changed(report):
    return [row for row in report["sources"] if row.get("change") == "changed"]


def failed(report):
    return [row for row in report["sources"] if row.get("failure")]


def markdown(report):
    lines = [f"Research watch of {report.get('created_at', 'unknown time')}: "
             f"{len(changed(report))} changed, {len(failed(report))} not reached, "
             f"{len(report['sources'])} watched.", "",
             "A change asks the research team to read the source again. It is not a claim, "
             "an approval or a change to what Baltor runs.", ""]
    if changed(report):
        lines += ["| Source | Kind | Observed | Roadmap step |", "|---|---|---|---|"]
        for row in changed(report):
            observed = row.get("observed") or {}
            seen = observed.get("revision") or observed.get("last_modified") or observed.get("fingerprint") or ""
            lines.append(f"| [{row.get('name', row.get('id'))}]({row.get('url', '')}) | {row.get('kind', '')} "
                         f"| {str(seen)[:40]} | {row.get('roadmap_step', '')} |")
        lines.append("")
    if failed(report):
        lines.append("Not reached: " + ", ".join(
            f"{row.get('id')} ({(row.get('failure') or {}).get('kind', 'unknown')})" for row in failed(report)) + ".")
    return "\n".join(lines) + "\n"


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        raise SystemExit("usage: summarize_research_watch.py REPORT [--changed-count]")
    report = load(argv[0])
    print(len(changed(report)) if "--changed-count" in argv[1:] else markdown(report), end="\n" if "--changed-count" in argv[1:] else "")
    return 0


if __name__ == "__main__":
    sys.exit(main())
