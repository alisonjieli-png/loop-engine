"""Summarize research source changes and collection failures without conflating them.

Reads a research_source_watch_report/v1 written by tools/refresh_research_sources.py.
A change is a prompt for the research team to read the source again; it is not a
source claim, an approval or runtime authority. Standard library only; no network.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from refresh_research_sources import MAX_MANIFEST_SOURCES, REPORT_TYPE

MAX_REPORT_BYTES = 1_000_000


class ReportError(ValueError):
    """A report cannot establish the watch's outcome."""


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ReportError("duplicate_report_field")
        value[key] = item
    return value


def _invalid_constant(_value):
    raise ReportError("non_json_number")


def load(path):
    try:
        with Path(path).open("rb") as stream:
            body = stream.read(MAX_REPORT_BYTES + 1)
    except OSError:
        raise ReportError("watch_report_unreadable") from None
    if len(body) > MAX_REPORT_BYTES:
        raise ReportError("watch_report_oversized")
    try:
        report = json.loads(body, object_pairs_hook=_unique_object, parse_constant=_invalid_constant)
    except (ValueError, UnicodeDecodeError, RecursionError):
        raise ReportError("watch_report_invalid_json") from None
    if (not isinstance(report, dict) or report.get("record_type") != REPORT_TYPE
            or report.get("mode") not in ("online", "offline_validation")
            or not isinstance(report.get("created_at"), str) or not report["created_at"]
            or not isinstance(report.get("sources"), list)
            or not 1 <= len(report["sources"]) <= MAX_MANIFEST_SOURCES):
        raise ReportError("watch_report_shape_invalid")
    identities = set()
    for row in report["sources"]:
        if (not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"]
                or row["id"] in identities or row.get("change") not in ("changed", "unchanged", "unknown")
                or not {"observed", "failure"} <= set(row)):
            raise ReportError("watch_source_shape_invalid")
        identities.add(row["id"])
        observation, failure = row["observed"], row["failure"]
        if observation is not None and (not isinstance(observation, dict)
                or not isinstance(observation.get("fingerprint"), str) or not observation["fingerprint"]):
            raise ReportError("watch_observation_invalid")
        if failure is not None and (not isinstance(failure, dict)
                or not isinstance(failure.get("kind"), str) or not failure["kind"]):
            raise ReportError("watch_failure_invalid")
        if ((failure is not None and (observation is not None or row["change"] != "unknown"))
                or (row["change"] != "unknown" and observation is None)):
            raise ReportError("watch_source_outcome_conflict")
    return report


def changed(report):
    return [row for row in report["sources"] if row.get("change") == "changed"]


def failed(report):
    return [row for row in report["sources"] if row["failure"] is not None]


def unobserved(report):
    return [row for row in report["sources"] if row["observed"] is None and row["failure"] is None]


def error_count(report, watch_exit_code=None):
    """Count failed or missing observations; retain an otherwise unexplained command failure."""
    errors = len(failed(report)) + len(unobserved(report))
    return errors or int(watch_exit_code not in (None, 0))


def markdown(report, watch_exit_code=None):
    lines = [f"Research watch of {report.get('created_at', 'unknown time')}: "
             f"{len(changed(report))} changed, {len(failed(report))} failed checks, "
             f"{len(unobserved(report))} not observed, {len(report['sources'])} watched.", "",
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
        lines.append("Checks failed: " + ", ".join(
            f"{row.get('id')} ({(row.get('failure') or {}).get('kind', 'unknown')})" for row in failed(report)) + ".")
    if unobserved(report):
        lines.append("No observation recorded: " + ", ".join(row["id"] for row in unobserved(report)) + ".")
    if watch_exit_code not in (None, 0):
        lines.append(f"Watcher exit status: {watch_exit_code}. See research-watch.log for the command outcome.")
    if error_count(report, watch_exit_code):
        lines.append("Collection coverage is degraded. A failed check does not establish that its source changed or disappeared.")
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("report", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--changed-count", action="store_true")
    mode.add_argument("--error-count", action="store_true")
    parser.add_argument("--watch-exit-code", type=int, choices=range(256))
    parser.add_argument("--github-output", type=Path,
                        help="append changed/errors outputs, retaining an unreadable report as a monitoring error")
    args = parser.parse_args(argv)
    if args.github_output and (args.changed_count or args.error_count):
        parser.error("workflow outputs require the Markdown summary")
    try:
        report = load(args.report)
    except ReportError as error:
        if not args.github_output:
            if args.error_count:
                print(1)
                return 0
            parser.exit(2, f"Research watch report unavailable: {error}.\n")
        changes, errors = "unknown", 1
        text = (f"Research watch report unavailable ({error}).\n\n"
                "Change count is unknown; collection coverage was not established. "
                "See research-watch.log for the command outcome. This does not establish a source change.\n")
        if args.watch_exit_code is not None:
            text += f"Watcher exit status: {args.watch_exit_code}.\n"
    else:
        changes, errors = len(changed(report)), error_count(report, args.watch_exit_code)
        text = markdown(report, args.watch_exit_code)
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as stream:
            stream.write(f"changed={changes}\nerrors={errors}\n")
    print(changes if args.changed_count else errors if args.error_count else text,
          end="\n" if args.changed_count or args.error_count else "")
    return 0


if __name__ == "__main__":
    sys.exit(main())
