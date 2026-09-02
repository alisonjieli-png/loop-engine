"""Publish one Kaggle run's outputs where a person and Kaggle both find them.

A run that produced a submission and a run that produced nothing looked
nearly the same in the notebook: the same wall of log lines, the submission
buried under an attempt directory named by timestamp, and nothing at
``/kaggle/working/submission.csv`` where Kaggle's own submit flow looks. This
module ends the run by putting each output where its reader is — the
competition file at the working root, a dated copy in ``submissions/``,
reports in HTML and Markdown, one JSON record for machines, and a short
console block that says what happened without scrolling.

It states measured facts and never a verdict. A submission is described by
its row count, its distinct-value count and its value range, because a run
in this repository's own history reported success on a file whose predictions
were a single constant. A file with one distinct value is published with that
said plainly rather than withheld or dressed up: the reader decides.

The root ``submission.csv`` is the only output that competes for one name, so
promotion to it is explicit and recorded. A submission from a verified run
replaces whatever is there; an unverified one is published under its own name
and only takes the root slot when nothing verified has claimed it.

Owns:
    - publish_run_outputs(): every artifact this module writes.
    - describe_submission(): the measured reading of one submission file.
    - render_terminal_block(): the console summary.

Does not own: the solve itself, the Run History it reads, or the notebook
cells that call this at the end of a run.
"""
from __future__ import annotations

import csv
import html
import json
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone

KAGGLE_REPORT_RECORD_TYPE = "kaggle_run_report/v1"
SUBMISSION_READING_RECORD_TYPE = "submission_reading/v1"

#: Rows read when measuring a submission. A submission is one column of
#: predictions, so this is about describing it honestly, not about loading it.
_MEASURE_ROW_CAP = 2_000_000


class KaggleReportError(ValueError):
    """A report request violated its typed contract."""


@dataclass
class KaggleReportRequest:
    """Everything the publisher needs, passed rather than discovered."""

    working_root: str
    run_stamp: str
    solved: bool
    #: Where everything except the competition file lives. The working root
    #: holds the one file a person needs and this holds the rest, so the
    #: directory a reader opens is not a haystack with the needle in it.
    engine_root: str = ""
    terminal_code: str = ""
    run_id: str = ""
    provider_label: str = ""
    model_label: str = ""
    model_calls: "int | None" = None
    loop_count: "int | None" = None
    elapsed_seconds: "float | None" = None
    deadline_hit: bool = False
    stop_level: str = ""
    task_text: str = ""
    artifacts: tuple = ()
    verification: dict = field(default_factory=dict)
    limitations: tuple = ()
    failures: tuple = ()
    source_roles: dict = field(default_factory=dict)
    option_selection: dict = field(default_factory=dict)
    log_paths: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not str(self.working_root or "").strip():
            raise KaggleReportError("working_root is required")
        if not str(self.run_stamp or "").strip():
            raise KaggleReportError("run_stamp is required")
        if not str(self.engine_root or "").strip():
            self.engine_root = os.path.join(self.working_root, "loop-engine")


def _float(value) -> "float | None":
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def describe_submission(path: str) -> dict:
    """Measure one submission file without judging it.

    Row count, columns, and for the prediction column how many distinct
    values it holds and what range they cover. The distinct count is the
    number that separates a real submission from a constant, which is why it
    is measured here rather than left for a reader to notice.
    """
    reading = {
        "record_type": SUBMISSION_READING_RECORD_TYPE,
        "path": path,
        "readable": False,
        "byte_count": None,
        "rows": None,
        "columns": [],
        "prediction_column": "",
        "distinct_predictions": None,
        "minimum": None,
        "maximum": None,
        "mean": None,
        "constant": None,
        "note": "",
    }
    if not path or not os.path.isfile(path):
        reading["note"] = "no submission file was produced"
        return reading
    reading["byte_count"] = os.path.getsize(path)
    try:
        with open(path, newline="", encoding="utf-8", errors="replace") as fh:
            rows = csv.reader(fh)
            header = next(rows, None)
            if not header:
                reading["note"] = "the file is empty"
                return reading
            reading["columns"] = list(header)
            column = len(header) - 1
            reading["prediction_column"] = header[column]
            seen, count = set(), 0
            total, low, high = 0.0, None, None
            numeric = 0
            for row in rows:
                if count >= _MEASURE_ROW_CAP or column >= len(row):
                    if column >= len(row):
                        continue
                    break
                value = row[column]
                seen.add(value)
                count += 1
                number = _float(value)
                if number is not None:
                    numeric += 1
                    total += number
                    low = number if low is None else min(low, number)
                    high = number if high is None else max(high, number)
            reading["readable"] = True
            reading["rows"] = count
            reading["distinct_predictions"] = len(seen)
            reading["constant"] = count > 0 and len(seen) == 1
            if numeric:
                reading["minimum"] = low
                reading["maximum"] = high
                reading["mean"] = round(total / numeric, 6)
            if reading["constant"]:
                reading["note"] = (
                    "every prediction is the same value; a submission that "
                    "does not vary carries no information about the rows")
            elif count == 0:
                reading["note"] = "the file has a header and no rows"
    except OSError as exc:
        reading["note"] = f"the file could not be read: {exc}"
    return reading


def _find_submission(artifacts, workspace: str) -> str:
    """The submission this run produced, from the record or the workspace."""
    for artifact in artifacts or ():
        path = str((artifact or {}).get("path") or "")
        if path.endswith("submission.csv") and os.path.isfile(path):
            return path
    newest, newest_time = "", -1.0
    for base, _dirs, names in os.walk(workspace or ""):
        for name in names:
            if name == "submission.csv":
                full = os.path.join(base, name)
                try:
                    stamp = os.path.getmtime(full)
                except OSError:
                    continue
                if stamp > newest_time:
                    newest, newest_time = full, stamp
    return newest


def _promotion(root_path: str, ledger_path: str, solved: bool) -> tuple:
    """Decide whether this run's submission takes the root filename.

    One name, several runs. A verified run always claims it. An unverified
    run claims it only while nothing verified has, so a later failed attempt
    cannot quietly replace a submission that passed.
    """
    previous = {}
    if os.path.isfile(ledger_path):
        try:
            with open(ledger_path, encoding="utf-8") as handle:
                previous = json.load(handle)
        except (OSError, json.JSONDecodeError):
            previous = {}
    held_by_verified = bool(previous.get("solved"))
    if solved:
        return True, ("this run verified; the root submission.csv now holds "
                      "its output")
    if not os.path.isfile(root_path):
        return True, ("nothing had claimed the root submission.csv; this "
                      "run's unverified output now holds it")
    if held_by_verified:
        return False, ("the root submission.csv holds output from a run that "
                       "verified (" + str(previous.get("run_stamp", ""))
                       + "); this unverified run did not replace it")
    return True, ("the root submission.csv held an earlier unverified "
                  "output; this run's replaces it")


def _report_rows(request: KaggleReportRequest, reading: dict) -> list:
    """The facts both reports render, in one order, computed once."""
    elapsed = request.elapsed_seconds
    return [
        ("Outcome", request.terminal_code or "UNKNOWN"),
        ("Verified", "yes" if request.solved else "no"),
        ("Provider", request.provider_label or "not recorded"),
        ("Model", request.model_label or "not recorded"),
        ("Model calls", request.model_calls),
        ("Loops", request.loop_count),
        ("Elapsed", (f"{elapsed:.0f}s ({elapsed / 60:.1f} min)"
                     if isinstance(elapsed, (int, float)) else None)),
        ("Deadline hit", "yes" if request.deadline_hit else "no"),
        ("Stop level", request.stop_level or "none, finished on its own"),
        ("Run id", request.run_id or "not recorded"),
    ]


def _submission_rows(reading: dict) -> list:
    return [
        ("File", reading.get("path") or "none produced"),
        ("Rows", reading.get("rows")),
        ("Bytes", reading.get("byte_count")),
        ("Columns", ", ".join(reading.get("columns") or []) or None),
        ("Distinct predictions", reading.get("distinct_predictions")),
        ("Range", (f"{reading['minimum']} to {reading['maximum']}"
                   if reading.get("minimum") is not None else None)),
        ("Mean", reading.get("mean")),
    ]


def _markdown(request: KaggleReportRequest, reading: dict,
              published: dict) -> str:
    def table(rows) -> list:
        out = ["| | |", "|---|---|"]
        for name, value in rows:
            if value is None or value == "":
                value = "not recorded"
            out.append(f"| {name} | {value} |")
        return out + [""]

    verdict = ("verified" if request.solved else
               "not verified" if reading.get("readable") else
               "no submission")
    lines = [f"# Kaggle run {request.run_stamp}", "",
             f"**{verdict}** — {request.terminal_code or 'UNKNOWN'}", ""]
    lines += ["## Run", ""] + table(_report_rows(request, reading))
    lines += ["## Submission", ""] + table(_submission_rows(reading))
    if reading.get("note"):
        lines += [f"> {reading['note']}", ""]
    if published.get("promoted"):
        lines += [f"The competition file is `{published['root_path']}`.", "",
                  f"{published['promotion_reason']}.", ""]
    elif published.get("root_path"):
        lines += [f"{published['promotion_reason']}.", ""]
    roles = (request.source_roles or {}).get("files") or []
    if roles:
        lines += ["## What the run made of each supplied file", ""]
        for item in roles:
            lines.append(f"- `{item.get('path')}` — {item.get('role')}")
        lines.append("")
    if request.failures:
        lines += ["## Failures the run recorded", ""]
        for item in list(request.failures)[:12]:
            lines.append(f"- {str(item)[:300]}")
        lines.append("")
    if request.limitations:
        lines += ["## Limitations the run stated", ""]
        for item in request.limitations:
            lines.append(f"- {str(item)[:300]}")
        lines.append("")
    tally = request.option_selection or {}
    if tally.get("reports"):
        lines += ["## What the run drew on", "",
                  f"Reported on {tally.get('reports')} of "
                  f"{tally.get('calls')} calls.", ""]
        for kind in ("perspectives", "guidance_refs"):
            for ref, count in sorted((tally.get(kind) or {}).items(),
                                     key=lambda item: -item[1])[:8]:
                lines.append(f"- {ref} ({count})")
        lines.append("")
    if request.log_paths:
        lines += ["## Files", ""]
        for name, path in sorted(request.log_paths.items()):
            lines.append(f"- {name}: `{path}`")
        lines.append("")
    return "\n".join(lines) + "\n"


_STYLE = """
:root { --ink:#16191d; --dim:#5a6472; --line:#e2e6ec; --bg:#ffffff;
        --panel:#f6f8fa; --good:#137a3f; --warn:#8a5a00; --bad:#a01b2b; }
@media (prefers-color-scheme: dark) {
  :root { --ink:#e7ebf0; --dim:#9aa5b4; --line:#2a3038; --bg:#14171b;
          --panel:#1b1f25; --good:#4cc38a; --warn:#e0a640; --bad:#f2707f; } }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--ink);
       font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",
       Roboto,Helvetica,Arial,sans-serif; }
.wrap { max-width:960px; margin:0 auto; padding:32px 20px 64px; }
h1 { font-size:24px; margin:0 0 4px; letter-spacing:-.01em; }
h2 { font-size:15px; text-transform:uppercase; letter-spacing:.07em;
     color:var(--dim); margin:34px 0 10px; font-weight:600; }
.sub { color:var(--dim); margin:0 0 22px; }
.badge { display:inline-block; padding:5px 12px; border-radius:999px;
         font-weight:650; font-size:13px; letter-spacing:.02em; }
.ok { background:rgba(19,122,63,.12); color:var(--good); }
.no { background:rgba(160,27,43,.12); color:var(--bad); }
.mid { background:rgba(138,90,0,.14); color:var(--warn); }
table { border-collapse:collapse; width:100%; font-size:14px; }
td { padding:8px 12px; border-bottom:1px solid var(--line);
     vertical-align:top; }
td.k { color:var(--dim); width:210px; white-space:nowrap; }
.panel { background:var(--panel); border:1px solid var(--line);
         border-radius:10px; padding:2px 16px; }
.note { border-left:3px solid var(--warn); padding:10px 14px; margin:14px 0;
        background:var(--panel); border-radius:0 8px 8px 0; }
code, .mono { font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
              font-size:13px; }
ul { margin:0; padding-left:20px; } li { margin:5px 0; }
.files li { color:var(--dim); } .files code { color:var(--ink); }
.foot { color:var(--dim); font-size:12px; margin-top:40px;
        border-top:1px solid var(--line); padding-top:14px; }
"""


def _html_table(rows) -> str:
    cells = []
    for name, value in rows:
        if value is None or value == "":
            value = '<span style="color:var(--dim)">not recorded</span>'
        else:
            value = html.escape(str(value))
        cells.append(f"<tr><td class='k'>{html.escape(str(name))}</td>"
                     f"<td class='mono'>{value}</td></tr>")
    return "<div class='panel'><table>" + "".join(cells) + "</table></div>"


def _html(request: KaggleReportRequest, reading: dict,
          published: dict) -> str:
    if request.solved:
        badge, label = "ok", "verified"
    elif reading.get("readable") and not reading.get("constant"):
        badge, label = "mid", "submission produced, not verified"
    else:
        badge, label = "no", "no usable submission"
    parts = [
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'>",
        f"<title>Kaggle run {html.escape(request.run_stamp)}</title>",
        f"<style>{_STYLE}</style></head><body><div class='wrap'>",
        f"<h1>Kaggle run {html.escape(request.run_stamp)}</h1>",
        f"<p class='sub'><span class='badge {badge}'>{label}</span> &nbsp; "
        f"{html.escape(request.terminal_code or 'UNKNOWN')}</p>",
        "<h2>Run</h2>", _html_table(_report_rows(request, reading)),
        "<h2>Submission</h2>", _html_table(_submission_rows(reading)),
    ]
    if reading.get("note"):
        parts.append(f"<div class='note'>{html.escape(reading['note'])}</div>")
    if published.get("promotion_reason"):
        parts.append(
            f"<div class='note'>{html.escape(published['promotion_reason'])}"
            "</div>")
    roles = (request.source_roles or {}).get("files") or []
    if roles:
        items = "".join(
            f"<li><code>{html.escape(str(item.get('path')))}</code> — "
            f"{html.escape(str(item.get('role')))}</li>" for item in roles)
        parts += ["<h2>What the run made of each supplied file</h2>",
                  f"<ul>{items}</ul>"]
    if request.failures:
        items = "".join(f"<li>{html.escape(str(item)[:400])}</li>"
                        for item in list(request.failures)[:12])
        parts += ["<h2>Failures the run recorded</h2>", f"<ul>{items}</ul>"]
    if request.limitations:
        items = "".join(f"<li>{html.escape(str(item)[:400])}</li>"
                        for item in request.limitations)
        parts += ["<h2>Limitations the run stated</h2>", f"<ul>{items}</ul>"]
    tally = request.option_selection or {}
    if tally.get("reports"):
        rows = []
        for kind, title in (("perspectives", "perspective"),
                            ("guidance_refs", "guidance")):
            for ref, count in sorted((tally.get(kind) or {}).items(),
                                     key=lambda item: -item[1])[:8]:
                rows.append((f"{title}: {ref}", count))
        parts += [f"<h2>What the run drew on "
                  f"({tally.get('reports')} of {tally.get('calls')} calls)"
                  f"</h2>", _html_table(rows)]
    if request.log_paths:
        items = "".join(
            f"<li>{html.escape(name)}: <code>{html.escape(str(path))}</code>"
            "</li>" for name, path in sorted(request.log_paths.items()))
        parts += ["<h2>Files</h2>", f"<ul class='files'>{items}</ul>"]
    parts += [
        "<p class='foot'>Every figure here is measured from the run's own "
        "output. A submission is described by its rows, distinct values and "
        "range rather than called good or bad.</p>",
        "</div></body></html>"]
    return "\n".join(parts)


def render_terminal_block(record: dict) -> str:
    """The console summary: what happened, where the file is, nothing else."""
    reading = record.get("submission") or {}
    published = record.get("published") or {}
    width = 68
    verdict = ("VERIFIED" if record.get("solved") else
               "NOT VERIFIED" if reading.get("readable") else
               "NO SUBMISSION")
    lines = ["", "=" * width,
             f"  {verdict}  ·  {record.get('terminal_code') or 'UNKNOWN'}",
             "=" * width]

    def row(name, value):
        if value is None or value == "":
            return
        lines.append(f"  {name:<22}{value}")

    elapsed = record.get("elapsed_seconds")
    row("model calls", record.get("model_calls"))
    row("elapsed", (f"{elapsed:.0f}s ({elapsed / 60:.1f} min)"
                    if isinstance(elapsed, (int, float)) else None))
    row("provider", record.get("provider_label"))
    row("model", record.get("model_label"))
    if reading.get("readable"):
        lines.append("  " + "-" * (width - 4))
        row("submission rows", f"{reading.get('rows'):,}"
            if isinstance(reading.get("rows"), int) else None)
        row("distinct values", f"{reading.get('distinct_predictions'):,}"
            if isinstance(reading.get("distinct_predictions"), int) else None)
        if reading.get("minimum") is not None:
            row("range", f"{reading['minimum']} to {reading['maximum']}"
                f"  (mean {reading.get('mean')})")
    if reading.get("note"):
        lines += ["  " + "-" * (width - 4), f"  ! {reading['note']}"]
    lines.append("  " + "-" * (width - 4))
    if published.get("promoted"):
        row("SUBMIT THIS FILE", published.get("root_path"))
    elif published.get("root_path"):
        row("root submission.csv", published.get("root_path"))
        lines.append(f"  ({published.get('promotion_reason')})")
    for name in ("submission_copy", "html_report", "markdown_report",
                 "json_record"):
        row(name.replace("_", " "), (record.get("outputs") or {}).get(name))
    lines += ["=" * width, ""]
    return "\n".join(lines)


def publish_run_outputs(request: KaggleReportRequest,
                        workspace: str = "") -> dict:
    """Write every end-of-run output and return the record describing them."""
    if not isinstance(request, KaggleReportRequest):
        raise KaggleReportError("publish_run_outputs needs its typed request")
    root = os.path.abspath(request.working_root)
    engine = os.path.abspath(request.engine_root)
    submissions = os.path.join(engine, "submissions")
    reports = os.path.join(engine, "logs", "reports")
    records = os.path.join(engine, "logs", "records")
    for directory in (submissions, reports, records):
        os.makedirs(directory, exist_ok=True)

    found = _find_submission(request.artifacts, workspace)
    reading = describe_submission(found)
    outputs: dict = {}
    published = {"promoted": False, "root_path": "", "promotion_reason": ""}

    if reading.get("readable"):
        dated = os.path.join(
            submissions, f"submission-{request.run_stamp}.csv")
        shutil.copy2(found, dated)
        outputs["submission_copy"] = dated
        root_path = os.path.join(root, "submission.csv")
        ledger = os.path.join(submissions, "root-submission.json")
        promote, reason = _promotion(root_path, ledger, request.solved)
        published["root_path"] = root_path
        published["promotion_reason"] = reason
        if promote:
            shutil.copy2(found, root_path)
            published["promoted"] = True
            with open(ledger, "w", encoding="utf-8") as handle:
                json.dump({"run_stamp": request.run_stamp,
                           "solved": request.solved,
                           "source": dated,
                           "reason": reason,
                           "rows": reading.get("rows"),
                           "distinct_predictions":
                               reading.get("distinct_predictions")},
                          handle, indent=2)
    else:
        published["promotion_reason"] = (
            "no submission was produced, so nothing was written to the root "
            "submission.csv")

    record = {
        "record_type": KAGGLE_REPORT_RECORD_TYPE,
        "run_stamp": request.run_stamp,
        "published_at_utc": datetime.now(timezone.utc).isoformat(),
        "solved": request.solved,
        "terminal_code": request.terminal_code,
        "run_id": request.run_id,
        "provider_label": request.provider_label,
        "model_label": request.model_label,
        "model_calls": request.model_calls,
        "loop_count": request.loop_count,
        "elapsed_seconds": request.elapsed_seconds,
        "deadline_hit": request.deadline_hit,
        "stop_level": request.stop_level,
        "submission": reading,
        "published": published,
        "verification": request.verification,
        "limitations": list(request.limitations),
        "failures": [str(item)[:500] for item in request.failures],
        "source_roles": request.source_roles,
        "option_selection": request.option_selection,
        "log_paths": request.log_paths,
        "outputs": outputs,
    }

    html_path = os.path.join(reports, f"report-{request.run_stamp}.html")
    with open(html_path, "w", encoding="utf-8") as handle:
        handle.write(_html(request, reading, published))
    outputs["html_report"] = html_path

    md_path = os.path.join(reports, f"report-{request.run_stamp}.md")
    with open(md_path, "w", encoding="utf-8") as handle:
        handle.write(_markdown(request, reading, published))
    outputs["markdown_report"] = md_path

    json_path = os.path.join(records, f"run-{request.run_stamp}.json")
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2, default=str)
    outputs["json_record"] = json_path

    latest = os.path.join(engine, "logs", "LATEST.json")
    with open(latest, "w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2, default=str)
    outputs["latest_record"] = latest
    record["outputs"] = outputs
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2, default=str)
    with open(latest, "w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2, default=str)
    return record


def self_test() -> dict:
    """Prove measurement, promotion, and that nothing is claimed unmeasured."""
    import tempfile

    tests = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    def write_submission(path: str, values) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["id", "target"])
            for index, value in enumerate(values):
                writer.writerow([index, value])

    with tempfile.TemporaryDirectory(prefix="loop-engine-kreport-") as root:
        space = os.path.join(root, "workspace")
        real = os.path.join(space, "attempt-1", "submission.csv")
        write_submission(real, [0.1, 0.9, 0.35, 0.62])

        reading = describe_submission(real)
        check("a_submission_is_measured_rather_than_judged",
              reading["rows"] == 4 and reading["distinct_predictions"] == 4
              and reading["constant"] is False
              and reading["minimum"] == 0.1 and reading["maximum"] == 0.9,
              str(reading))

        # The defect this repository has actually shipped: a submission whose
        # predictions never vary. It must be published and named, not hidden.
        flat = os.path.join(space, "flat", "submission.csv")
        write_submission(flat, [0.5] * 6)
        flat_reading = describe_submission(flat)
        check("a_constant_submission_is_named_as_one",
              flat_reading["constant"] is True
              and flat_reading["distinct_predictions"] == 1
              and "does not vary" in flat_reading["note"],
              flat_reading["note"])

        check("an_absent_submission_reads_as_absent_not_as_empty",
              describe_submission(os.path.join(root, "nope.csv"))["rows"]
              is None,
              "rows stays None rather than becoming zero")

        # An unverified run publishes and claims the root slot when free.
        first = publish_run_outputs(KaggleReportRequest(
            working_root=root, run_stamp="A", solved=False,
            terminal_code="NOT_YET_PROVEN"), workspace=space)
        root_file = os.path.join(root, "submission.csv")
        check("an_unverified_run_publishes_and_claims_a_free_root_slot",
              first["published"]["promoted"] is True
              and os.path.isfile(root_file)
              and os.path.isfile(os.path.join(
                  root, "loop-engine", "submissions", "submission-A.csv")),
              str(first["published"]))

        # A verified run always takes the root slot.
        verified_space = os.path.join(root, "workspace2")
        write_submission(
            os.path.join(verified_space, "submission.csv"), [0.2, 0.4, 0.6])
        second = publish_run_outputs(KaggleReportRequest(
            working_root=root, run_stamp="B", solved=True,
            terminal_code="COMPLETED_VERIFIED"), workspace=verified_space)
        check("a_verified_run_takes_the_root_slot",
              second["published"]["promoted"] is True
              and describe_submission(root_file)["rows"] == 3,
              str(second["published"]["promotion_reason"]))

        # And a later unverified run must not displace it.
        third = publish_run_outputs(KaggleReportRequest(
            working_root=root, run_stamp="C", solved=False,
            terminal_code="VERIFICATION_FAILED"), workspace=space)
        check("a_later_unverified_run_does_not_displace_a_verified_one",
              third["published"]["promoted"] is False
              and describe_submission(root_file)["rows"] == 3
              and os.path.isfile(os.path.join(
                  root, "loop-engine", "submissions", "submission-C.csv")),
              third["published"]["promotion_reason"])

        outputs = third["outputs"]
        check("every_report_shape_is_written",
              all(os.path.isfile(outputs[key]) for key in
                  ("html_report", "markdown_report", "json_record",
                   "latest_record", "submission_copy")),
              str(sorted(outputs)))

        with open(outputs["html_report"], encoding="utf-8") as handle:
            page = handle.read()
        check("the_html_report_is_self_contained",
              "<style>" in page and "http://" not in page
              and "https://" not in page and "<script" not in page,
              "no external resource and no script")

        with open(outputs["json_record"], encoding="utf-8") as handle:
            saved = json.load(handle)
        check("the_json_record_names_its_own_outputs",
              saved["record_type"] == KAGGLE_REPORT_RECORD_TYPE
              and saved["outputs"]["html_report"] == outputs["html_report"],
              "a reader can find every file from the record alone")

        block = render_terminal_block(third)
        check("the_console_block_says_where_the_file_is",
              "NOT VERIFIED" in block and "root submission.csv" in block,
              block.splitlines()[2] if len(block.splitlines()) > 2 else "")

        # A run with no submission writes reports and touches nothing else.
        empty_root = os.path.join(root, "empty")
        os.makedirs(empty_root, exist_ok=True)
        none = publish_run_outputs(KaggleReportRequest(
            working_root=empty_root, run_stamp="D", solved=False,
            terminal_code="BLOCKED"), workspace=os.path.join(root, "absent"))
        check("a_run_with_no_submission_writes_no_root_file",
              not os.path.isfile(os.path.join(empty_root, "submission.csv"))
              and "no submission was produced"
              in none["published"]["promotion_reason"]
              and os.path.isfile(none["outputs"]["html_report"]),
              none["published"]["promotion_reason"])

        # The working root is what a person opens and what Kaggle's submit
        # dialog lists. It holds the competition file and the one directory
        # everything else lives under, and nothing else this module writes.
        entries = sorted(os.listdir(root))
        check("the_working_root_holds_the_submission_and_one_directory",
              "submission.csv" in entries
              and "loop-engine" in entries
              and not [name for name in entries
                       if name.endswith((".json", ".md", ".html", ".log"))],
              str(entries))

        refused = False
        try:
            KaggleReportRequest(working_root="", run_stamp="E", solved=False)
        except KaggleReportError:
            refused = True
        check("an_invalid_request_fails_closed", refused)

    passed = sum(1 for item in tests if item["passed"])
    return {"record_type": "kaggle_report_test/v1",
            "tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
