#!/usr/bin/env python3
"""The factory report: what each stage of the daily library job costs per admitted package, and the projection.

Kind: local measurement tool over records that already exist. It reads the daily job's journals
(``daily/<slot>/journal.jsonl``), counts (``counts.json``), review and calibration ledgers, the export
reports of the review batches, the import store's candidate index, and the overnight generation batch's
status and journal, and writes one dated ``factory_report/v1`` record beside a plain Markdown table. It
makes no model call, contacts no network, and changes nothing it reads. Library bodies never enter the
report: only counts, times and digests of records.

    PYTHONPATH=src:tools python tools/factory_report.py --library /home/username/baltor-library \\
        --overnight-batch /path/to/batch --served 6398 --output /path/to/folder

What the numbers mean, stated once:

* A stage's minutes are the gap between the journal's ``done`` marker of the stage before it and its
  own. The export's minutes start when the job first ran for the slot: the birth time of the job's own
  temporary folder (``$HOME/.le-ci-tmp/daily-<slot>``, which the job creates before any stage), read
  with GNU ``stat``. Without it they start at the slot's scheduled minute when the slot name carries an
  hour (the cron line starts each slot at minute 17), and are unknown otherwise. The gap between the
  scheduled minute and the first run is recorded as a late start. When a stage wrote no ``done`` note (a
  person finished it by hand), the gap up to the next note spans several stages: it is recorded as an
  unattributed gap with the stages it covers, and none of those stages gets its minutes.
* A review lane is the installation that answered the calls, with the model family the ledger names, so
  the throughput of each lane and the family it would review for are read from the ledger, not assumed.
* A stage the job left once (a failure note or a not-qualified verdict) before its ``done`` note was
  restarted by a person, so its minutes hold the person's wait: the slot's row marks it, the waste counts
  it, and the stage means that plan a clean slot leave it out.
* A slot without ``counts.json`` that wrote its reviewed folder (it stopped at the publish) is written,
  not published: its approvals come from the writer's record and count toward the rates, because the
  next slot's combine carries every reviewed folder. Any other slot without counts is unfinished when it
  is the newest slot (it may still be running) and abandoned when a later slot exists; only an abandoned
  slot counts as lost.
* The review stage is split into startup (from the calibration marker to the first model call, when the
  panel rebuilds every request and reruns the prechecks), the calls themselves (the ledger's elapsed
  seconds, which is the reviewer's busy time), and the tail after the last call.
* The reviewer's utilization is its busy seconds over the slot's wall time, and over the cadence
  between slots, so an idle server is visible as a number.
* Cost per admitted package is given in the units that were measured: reviewer seconds, reported
  tokens, wall minutes, and the recorded monthly infrastructure allowance spread over a day's
  approvals. The Tactical server is the owner's own machine and reports no price, so its model cost is
  ``unmetered``, never zero.
* The stock is what the import store holds that no export has drawn, less what the export marks as not
  reviewable, and the draw curve simulates the job's own export policy (a target per export and a
  ceiling per repository) over the remaining candidates by repository, so the record shows how many
  full exports the stock supports before the ceiling shrinks each draw.
* The projection multiplies the mean approvals of the recent slots by the slots a day and stops at the
  stock, both at the eligible count and at what the export policy can draw. It also names the serving
  capacity the operator declares (the package count the live host was measured to hold) and the
  generated candidates that wait for a reviewer of another model family, whose yield is not measured
  and which therefore never enter the ceiling.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import statistics
import subprocess
import sys

RECORD_TYPE = "factory_report/v1"
STAGES = ("export", "prechecks", "calibrate", "review", "write", "combine", "bundle", "publish", "check", "counts")
BATCH_CALL = "candidate_review_batch_call/v1"
SINGLE_CALL = "candidate_review_call/v2"
ANSWERED = ("batch_answered", "verdict")
DEFAULT_MARKS = (10_000, 30_000, 100_000)
DEFAULT_CADENCE_HOURS = 6.0
DEFAULT_CRON_MINUTE = 17
DEFAULT_ALLOWANCE_USD_MONTH = 50.0
DEFAULT_EXPORT_TARGET = 2000
DEFAULT_PER_REPOSITORY = 15
DEFAULT_VOLUME_BYTES = 1_000_000_000
DEFAULT_TEMP_ROOT = Path.home() / ".le-ci-tmp"
DAYS_A_MONTH = 30.0
SIMULATION_HORIZON = 80
CALIBRATION_LEDGERS = ("calibration-ledger.jsonl", "calibration-retry-ledger.jsonl")
NOT_QUALIFIED = "not qualified"
#: The states of a slot as this report names them.
FINISHED, WRITTEN_NOT_PUBLISHED, UNFINISHED, ABANDONED = "finished", "written_not_published", "unfinished", "abandoned"
#: The overnight batch journal's event names this report reads.
DISPATCH, ATTEMPT_RESULT, OUTCOME, OUTAGE_WAIT, LANE_DEGRADED = (
    "dispatch", "attempt_result", "outcome", "outage_wait", "lane_degraded")
ATTEMPT_ENDS = frozenset({ATTEMPT_RESULT, OUTCOME})


class FactoryReportError(ValueError):
    """An input the report cannot read honestly."""


def _parse(stamp: str) -> datetime:
    return datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone(timezone.utc)


def _jsonl(path: Path) -> list:
    rows = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def _minutes(seconds) -> float | None:
    return None if seconds is None else round(seconds / 60.0, 2)


def _mean(values, digits=1):
    values = [value for value in values if value is not None]
    return round(statistics.mean(values), digits) if values else None


def slot_start(slot: str, cron_minute: int) -> datetime | None:
    """The scheduled start of a cron slot named ``YYYY-MM-DD-HH`` (at the cron minute) or of a queued slot named
    ``YYYY-MM-DD-HH-MM`` (at its own minute); None for a plain date."""
    parts = slot.split("-")
    if len(parts) in (4, 5) and all(part.isdigit() for part in parts):
        year, month, day, hour = (int(part) for part in parts[:4])
        minute = int(parts[4]) if len(parts) == 5 else cron_minute
        return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)
    return None


def job_started_at(temp_root: Path, slot: str) -> datetime | None:
    """When the daily job first ran for a slot: the birth time of the temporary folder it creates before any
    stage, read with GNU ``stat -c %W``; None when the folder, the tool or the file system cannot say."""
    folder = temp_root / f"daily-{slot}"
    if not folder.is_dir():
        return None
    try:
        completed = subprocess.run(["stat", "-c", "%W", str(folder)], capture_output=True, text=True, timeout=10,
                                   check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    text = completed.stdout.strip()
    if completed.returncode != 0 or not text.isdigit() or int(text) == 0:
        return None
    return datetime.fromtimestamp(int(text), tz=timezone.utc)


def _calls(rows: list) -> list:
    calls = [row for row in rows if row.get("record_type") in (BATCH_CALL, SINGLE_CALL)]
    calls.sort(key=lambda row: row["started_at"])
    return calls


def review_window(calls: list) -> tuple | None:
    """The first call's start and the last call's end: when the reviewer was in use."""
    if not calls:
        return None
    first = _parse(calls[0]["started_at"])
    last = max(_parse(row["started_at"]) + timedelta(seconds=float(row["elapsed_seconds"])) for row in calls)
    return first, last


def read_slot(folder: Path, *, cron_minute: int = DEFAULT_CRON_MINUTE, started_at: datetime | None = None) -> dict:
    """One slot of the daily job: its stage minutes, review split, calibration attempts, counts and waste."""
    slot = folder.name
    journal = _jsonl(folder / "journal.jsonl")
    done_at, notes = {}, []
    for event in journal:
        if event.get("note") == "done":
            done_at.setdefault(event["stage"], _parse(event["at"]))
        else:
            notes.append(event)
    scheduled = slot_start(slot, cron_minute)
    refused = None
    if started_at and journal and started_at > _parse(journal[0]["at"]):
        # The job writes its first note after its first run began, so a later folder time is not the first run.
        refused, started_at = started_at.isoformat(), None
    start = started_at or scheduled
    late_start = _minutes((started_at - scheduled).total_seconds()) if started_at and scheduled else None
    stage_minutes, unattributed, previous, missing = {}, [], start, []
    for stage in STAGES:
        finished = done_at.get(stage)
        if finished is None:
            stage_minutes[stage] = None
            missing.append(stage)
            continue
        if previous is not None and missing:
            # A stage before this one wrote no done note (a person finished it by hand, as on the first slot of
            # September 26), so the gap spans several stages and belongs to none of them.
            stage_minutes[stage] = None
            unattributed.append({"stages": missing + [stage], "minutes": _minutes((finished - previous).total_seconds())})
        else:
            stage_minutes[stage] = _minutes((finished - previous).total_seconds()) if previous else None
        previous, missing = finished, []
    end = done_at.get("counts") or previous
    wall_seconds = (end - start).total_seconds() if start and end else None

    calls = _calls(_jsonl(folder / "ledger.jsonl"))
    busy = sum(float(row["elapsed_seconds"]) for row in calls)
    lanes = {}
    for row in calls:
        # A lane is the installation that answered, with its model family, as the ledger names them; the family
        # is what the rule "a producer family never approves its own output" reads.
        lane = lanes.setdefault(row.get("installation_id") or "unknown", {
            "family": row.get("family") or "unknown", "calls": 0, "items": 0, "busy_seconds": 0.0, "unanswered_calls": 0})
        lane["calls"] += 1
        lane["items"] += len(row.get("members") or ()) or 1
        lane["busy_seconds"] = round(lane["busy_seconds"] + float(row["elapsed_seconds"]), 3)
        lane["unanswered_calls"] += 0 if row["outcome"] in ANSWERED else 1
    outcomes = Counter(row["outcome"] for row in calls)
    unanswered = [row for row in calls if row["outcome"] not in ANSWERED]
    tokens = sum(int(row.get("charged_tokens") or 0) for row in calls)
    window = review_window(calls)
    review = {"calls": len(calls), "busy_seconds": round(busy, 1), "outcomes": dict(outcomes),
              "charged_tokens": tokens,
              "calls_with_unknown_usage": sum(1 for row in calls if not (row.get("usage") or {}).get("input_tokens")),
              "unanswered_calls": len(unanswered),
              "unanswered_seconds": round(sum(float(row["elapsed_seconds"]) for row in unanswered), 1),
              "items_in_unanswered_calls": sum(len(row.get("members") or ()) or 1 for row in unanswered),
              "mean_call_seconds": _mean([float(row["elapsed_seconds"]) for row in calls]),
              "median_call_seconds": round(statistics.median(float(r["elapsed_seconds"]) for r in calls), 1) if calls else None,
              "max_call_seconds": round(max(float(row["elapsed_seconds"]) for row in calls), 1) if calls else None,
              "lanes": lanes,
              "startup_minutes": None, "tail_minutes": None, "first_call_at": None, "last_call_end_at": None}
    if window:
        first, last_end = window
        review["first_call_at"], review["last_call_end_at"] = first.isoformat(), last_end.isoformat()
        if "calibrate" in done_at:
            review["startup_minutes"] = _minutes((first - done_at["calibrate"]).total_seconds())
        if "review" in done_at:
            review["tail_minutes"] = _minutes((done_at["review"] - last_end).total_seconds())

    calibration_calls, moved_aside = [], []
    for name in CALIBRATION_LEDGERS:
        calibration_calls += _calls(_jsonl(folder / name))
    attempts = sorted(path for path in folder.glob("attempt-*") if path.is_dir())
    for attempt in attempts:
        for name in CALIBRATION_LEDGERS:
            moved_aside += _calls(_jsonl(attempt / name))
    calibration = {"calls": len(calibration_calls),
                   "busy_seconds": round(sum(float(row["elapsed_seconds"]) for row in calibration_calls), 1),
                   "retries": sum(1 for note in notes if note["stage"] == "calibrate" and "once more" in note["note"]),
                   "not_qualified_verdicts": sum(1 for note in notes if note["stage"] == "calibrate"
                                                 and "not qualified" in note["note"]),
                   "attempts_moved_aside": len(attempts), "moved_aside_calls": len(moved_aside),
                   "moved_aside_busy_seconds": round(sum(float(row["elapsed_seconds"]) for row in moved_aside), 1)}
    failures = [{"stage": note["stage"], "at": note["at"], "note": note["note"][:160]} for note in notes
                if "failed" in note["note"] and "status" not in note["note"]]
    # A stage the job left once (a failure or a not-qualified verdict) and a person restarted holds the person's
    # wait in its minutes, so it is kept out of the means that plan a clean slot.
    restarted = sorted({note["stage"] for note in notes if note.get("stage") in done_at
                        and _parse(note["at"]) <= done_at[note["stage"]]
                        and (("failed" in note["note"] and "status" not in note["note"]) or NOT_QUALIFIED in note["note"])},
                       key=STAGES.index)

    counts, status = _json(folder / "counts.json"), FINISHED
    if counts.get("approved") is None:
        counts, status = written_counts(folder, done_at), WRITTEN_NOT_PUBLISHED
        if counts is None:
            counts, status = {}, UNFINISHED
    approved = counts.get("approved")
    reviewer_busy = busy + calibration["busy_seconds"] + calibration["moved_aside_busy_seconds"]
    per_approved = {}
    if approved:
        per_approved = {"reviewer_seconds": round(reviewer_busy / approved, 2),
                        "charged_tokens": round(tokens / approved, 1),
                        "wall_minutes": round(wall_seconds / 60.0 / approved, 3) if wall_seconds else None}
    bundle = _json_line(folder / "bundle.log")
    stop = None
    if status != FINISHED:
        stop = {"last_stage": (journal or [{"stage": None}])[-1].get("stage"),
                "last_note": (journal or [{"note": ""}])[-1].get("note", "")[:160],
                "last_failure": failures[-1]["note"] if failures else None}
    return {"slot": slot, "status": status, "restarted_stages": restarted,
            "minutes_in_restarted_stages": round(sum(stage_minutes[stage] or 0.0 for stage in restarted), 2),
            "scheduled_start": scheduled.isoformat() if scheduled else None,
            "first_run_at": started_at.isoformat() if started_at else None, "first_run_refused": refused,
            "late_start_minutes": late_start,
            "finished_at": end.isoformat() if end else None, "wall_minutes": _minutes(wall_seconds),
            "stage_minutes": stage_minutes, "unattributed_gaps": unattributed, "review": review,
            "calibration": calibration,
            "reviewer_busy_seconds": round(reviewer_busy, 1),
            "reviewer_utilization_of_slot": round(reviewer_busy / wall_seconds, 3) if wall_seconds else None,
            "failed_stage_notes": failures, "stop": stop, "lost": None,
            "bundle": {key: bundle.get(key) for key in ("items", "files", "bytes")} if bundle else None,
            "counts": {key: counts.get(key) for key in (
                "record_type", "exported", "passed_prechecks", "reviewed", "review_calls", "approved", "rejected",
                "left_out", "published", "checked_live")}, "per_approved": per_approved}


def written_counts(folder: Path, done_at: dict) -> dict | None:
    """The counts of a slot that wrote its reviewed folder but stopped before its counts record (a failed publish):
    read from its prechecks, review and writer records, marked as not published. The next slot's combine carries
    every reviewed folder, so these approvals are produced, not lost. None when the slot did not reach the write."""
    writer = _json(folder.parent.parent / f"reviewed-{folder.name}" / "imported" / "writer-report.json")
    if "write" not in done_at or writer.get("approved") is None:
        return None
    prechecks, totals = _json(folder / "prechecks.json"), _json(folder / "review.json").get("totals") or {}
    items, refused = prechecks.get("items"), prechecks.get("refused")
    return {"record_type": "derived_from_the_writer_report", "exported": items,
            "passed_prechecks": items - refused if items is not None and refused is not None else None,
            "reviewed": totals.get("items"), "review_calls": totals.get("calls"), "approved": writer["approved"],
            "rejected": writer.get("rejected"), "left_out": len(writer.get("left_out") or ()), "published": False,
            "checked_live": False}


def _json_line(path: Path) -> dict:
    """The last JSON object in a log whose final line is one record; empty when there is none."""
    if not path.is_file():
        return {}
    for line in reversed(path.read_text(encoding="utf-8").splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except ValueError:
                return {}
    return {}


def _repository_of(item: dict) -> str:
    """The upstream repository an exported item came from, as ``owner/name``, from its source reference."""
    parts = ((item.get("reference") or {}).get("source_ref") or "").split("/")
    return "/".join(parts[1:3]) if len(parts) >= 3 else ""


def simulate_draws(pool: dict, *, target: int, per_repository: int, horizon: int) -> list:
    """Draws of the export policy over a pool of candidates by repository: at most ``per_repository`` from each
    repository per export and at most ``target`` in all, largest repositories first, until the pool or the horizon
    ends. The real export also keeps a kind mix and a rank; the ceiling is what shrinks the draw, so this is the
    upper bound of what the policy can draw."""
    if target < 1 or per_repository < 1:
        raise FactoryReportError("target and per_repository are positive counts")
    left = {name: int(count) for name, count in pool.items() if count > 0}
    draws = []
    for _export in range(horizon):
        got = 0
        for name in sorted(left, key=lambda name: (-left[name], name)):
            take = min(per_repository, left[name], target - got)
            if take <= 0:
                break
            left[name] -= take
            got += take
        left = {name: count for name, count in left.items() if count > 0}
        if got <= 0:
            break
        draws.append(got)
    return draws


def read_stock(library: Path, *, target: int = DEFAULT_EXPORT_TARGET, per_repository: int = DEFAULT_PER_REPOSITORY,
               horizon: int = SIMULATION_HORIZON) -> dict:
    """What the import store still holds, and the draw curve of the job's export policy over it.

    An export counts as drawn only when its folder holds ``export-report.json``, which is exactly the
    rule the daily job uses to exclude earlier exports; a folder whose export failed is drawn again.
    """
    review_batches = library / "review-batches"
    reports = sorted(review_batches.glob("*/export-report.json"), key=lambda path: path.stat().st_mtime)
    if not reports:
        return {"source": None, "eligible_remaining": None, "draw_curve": None}
    newest = _json(reports[-1])
    selection = newest.get("selection") or {}
    not_selected = selection.get("not_selected") or {}
    stored = selection.get("stored_candidates")
    in_reports = 0
    exported_by_repository = Counter()
    for report in reports:
        record = _json(report)
        in_reports += int(record.get("items") or 0)
        items = _json(report.parent / "items.json").get("items") or []
        for item in items:
            exported_by_repository[_repository_of(item)] += 1
    # The export tool's own count of what earlier exports drew is the authority on its exclusions; the sum over
    # the reports present is kept beside it as a cross-check.
    already = selection.get("already_exported")
    exported = int(already) + int(newest.get("items") or 0) if already is not None else in_reports
    unreviewable = int(not_selected.get("a_file_is_not_reviewable_text", 0)) + int(not_selected.get("a_file_is_above_the_review_bound", 0))
    remaining = None if stored is None else max(0, stored - exported - unreviewable)
    stock = {"source": str(reports[-1]), "written_at": newest.get("written_at"), "stored_candidates": stored,
             "exported_so_far": exported, "exported_in_reports_present": in_reports,
             "exports_drawn": len(reports), "not_reviewable": unreviewable,
             "held_by_repository_ceiling_in_last_export": not_selected.get("repository_ceiling_reached", 0),
             "per_repository": selection.get("per_repository"), "eligible_remaining": remaining,
             "policy": {"target": target, "per_repository": per_repository}, "draw_curve": None}
    indexes = sorted((library / "import-store").glob("candidate-index-*.jsonl"), key=lambda path: path.stat().st_mtime)
    if indexes and stored:
        by_repository = Counter()
        for row in _jsonl(indexes[-1]):
            by_repository[row.get("repository", "")] += 1
        reviewable_share = 1.0 - unreviewable / stored
        pool = {name: int(round(max(0, count - exported_by_repository.get(name, 0)) * reviewable_share))
                for name, count in by_repository.items()}
        draws = simulate_draws(pool, target=target, per_repository=per_repository, horizon=horizon)
        full = [draw for draw in draws if draw >= target]
        stock["draw_curve"] = {"index": str(indexes[-1]), "repositories": len(by_repository),
                               "repositories_with_stock": sum(1 for count in pool.values() if count > 0),
                               "reviewable_share_assumed": round(reviewable_share, 4), "draws": draws,
                               "full_exports_supported": len(full), "candidates_in_full_exports": sum(full),
                               "drawable_within_horizon": sum(draws), "horizon_exports": horizon,
                               "draw_after_full_exports": draws[len(full)] if len(draws) > len(full) else None}
    return stock


def read_generation_lanes(batch_folder: Path, review_windows: list = ()) -> dict:
    """Throughput of every generation lane in an overnight batch, and how a review beside it changed its calls."""
    status = _json(batch_folder / "status.json")
    lanes, open_dispatch = {}, {}
    for event in _jsonl(batch_folder / "journal.jsonl"):
        lane = event.get("lane_id")
        if not lane:
            continue
        row = lanes.setdefault(lane, {"dispatches": 0, "outcomes": Counter(), "attempts": [], "inside": [],
                                      "outside": [], "active_hours": set(), "outage_waits": 0,
                                      "outage_wait_seconds": 0.0, "degraded": 0})
        kind, when = event.get("event"), _parse(event["ts"]) if event.get("ts") else None
        if kind == DISPATCH:
            row["dispatches"] += 1
            open_dispatch[(lane, event.get("idea_id"))] = when
        elif kind in ATTEMPT_ENDS:
            started = open_dispatch.pop((lane, event.get("idea_id")), None)
            seconds = event.get("elapsed_seconds")
            if seconds is None and started is not None and when is not None:
                seconds = (when - started).total_seconds()
            if kind == OUTCOME:
                row["outcomes"][event["outcome"]] += 1
                row["active_hours"].add(when.strftime("%Y-%m-%dT%H"))
            if seconds is not None:
                row["attempts"].append(float(seconds))
                inside = any(first <= when <= last for first, last in review_windows)
                (row["inside"] if inside else row["outside"]).append(float(seconds))
        elif kind == OUTAGE_WAIT:
            row["outage_waits"] += 1
            row["outage_wait_seconds"] += float(event.get("seconds") or 0)
        elif kind == LANE_DEGRADED:
            row["degraded"] += 1
    result = {}
    for lane, row in lanes.items():
        written = row["outcomes"].get("candidate_written", 0)
        hours = len(row["active_hours"])
        result[lane] = {"dispatches": row["dispatches"], "outcomes": dict(row["outcomes"]), "candidates": written,
                        "active_hours": hours, "candidates_per_active_hour": round(written / hours, 1) if hours else None,
                        "mean_attempt_seconds": _mean(row["attempts"]),
                        "median_attempt_seconds": round(statistics.median(row["attempts"]), 1) if row["attempts"] else None,
                        "attempts_inside_review_windows": len(row["inside"]),
                        "mean_attempt_seconds_inside_review_windows": _mean(row["inside"]),
                        "attempts_outside_review_windows": len(row["outside"]),
                        "mean_attempt_seconds_outside_review_windows": _mean(row["outside"]),
                        "retries": max(0, row["dispatches"] - sum(row["outcomes"].values())),
                        "outage_waits": row["outage_waits"], "outage_wait_seconds": row["outage_wait_seconds"],
                        "degraded_events": row["degraded"]}
    return {"folder": str(batch_folder), "state": status.get("state"), "ideas_total": status.get("ideas_total"),
            "candidates": status.get("candidates"), "failed": status.get("failed"), "calls_used": status.get("calls_used"),
            "started_at": status.get("started_at"), "updated_at": status.get("updated_at"), "lanes": result}


def project(served: int, approved_per_slot: float, slots_per_day: float, yield_per_exported: float | None,
            stock: dict, marks, now: datetime, serving_capacity: int | None = None,
            generated_waiting: int | None = None, written: int = 0) -> dict:
    """Days and dates to each mark at the current rate, the ceilings the stock and the export policy allow,
    and the serving capacity the live host was measured to hold. The base is what is served plus what is
    approved and written but not yet published, because the next slot's combine carries those folders."""
    rate = approved_per_slot * slots_per_day
    base = served + written
    eligible = stock.get("eligible_remaining")
    curve = stock.get("draw_curve") or {}
    drawable = curve.get("drawable_within_horizon")
    approvable = None if eligible is None or yield_per_exported is None else int(eligible * yield_per_exported)
    approvable_by_policy = None if drawable is None or yield_per_exported is None else int(drawable * yield_per_exported)
    ceiling = None if approvable is None else base + approvable
    policy_ceiling = None if approvable_by_policy is None else base + approvable_by_policy
    rows = []
    for mark in marks:
        short = max(0, mark - base)
        days = None if rate <= 0 else round(short / rate, 1)
        row = {"mark": mark, "packages_short": short, "days_at_current_rate": days,
               "date_at_current_rate": (now + timedelta(days=days)).date().isoformat() if days is not None else None,
               "reachable_from_current_stock": None if ceiling is None else mark <= ceiling,
               "reachable_at_current_export_policy": None if policy_ceiling is None else mark <= policy_ceiling,
               "within_serving_capacity": None if serving_capacity is None else mark <= serving_capacity}
        if ceiling is not None and mark > ceiling and yield_per_exported:
            row["candidates_needed_beyond_stock"] = int((mark - ceiling) / yield_per_exported) + 1
        rows.append(row)
    return {"served_now": served, "written_not_published": written, "base": base,
            "approved_per_slot": round(approved_per_slot, 1), "slots_per_day": slots_per_day,
            "approved_per_day": round(rate, 1), "yield_per_exported": yield_per_exported,
            "eligible_remaining": eligible, "approvable_from_stock": approvable, "stock_ceiling": ceiling,
            "drawable_at_current_export_policy": drawable, "approvable_at_current_export_policy": approvable_by_policy,
            "export_policy_ceiling": policy_ceiling,
            "full_exports_supported": curve.get("full_exports_supported"),
            "days_until_stock_is_exhausted": None if approvable is None or rate <= 0 else round(approvable / rate, 1),
            "days_until_full_exports_end": None if curve.get("full_exports_supported") is None or slots_per_day <= 0
            else round(curve["full_exports_supported"] / slots_per_day, 1),
            "serving_capacity": serving_capacity,
            "days_until_serving_capacity": None if serving_capacity is None or rate <= 0
            else round(max(0, serving_capacity - base) / rate, 1),
            "generated_waiting_for_another_family": generated_waiting, "marks": rows}


def build_report(*, library: Path, overnight_batches: list, served: int, now: datetime, cadence_hours: float,
                 marks, allowance_usd_month: float, cron_minute: int = DEFAULT_CRON_MINUTE,
                 recent_slots: int = 3, export_target: int = DEFAULT_EXPORT_TARGET,
                 per_repository: int = DEFAULT_PER_REPOSITORY, volume_bytes: int = DEFAULT_VOLUME_BYTES,
                 serving_capacity: int | None = None, started=lambda slot: None) -> dict:
    daily = library / "daily"
    if not daily.is_dir():
        raise FactoryReportError(f"no daily folder under {library}")
    folders = [folder for folder in sorted(daily.iterdir()) if folder.is_dir()]
    slots = [read_slot(folder, cron_minute=cron_minute, started_at=started(folder.name)) for folder in folders]
    for slot in slots[:-1]:
        if slot["status"] == UNFINISHED:
            # A later slot started while this one had no counts: nobody finished it, so its approvals are lost.
            slot["status"] = ABANDONED
            slot["lost"] = {"last_stage": slot["stop"]["last_stage"],
                            "reason": slot["stop"]["last_failure"] or "no counts record and no failure note"}
    complete = [slot for slot in slots if slot["counts"].get("approved") is not None]
    recent = complete[-recent_slots:]
    if not recent:
        raise FactoryReportError("no slot with counts.json")
    approved = [slot["counts"]["approved"] for slot in recent]
    exported = [slot["counts"]["exported"] for slot in recent if slot["counts"].get("exported")]
    yield_per_exported = round(sum(approved) / sum(exported), 3) if exported else None
    slots_per_day = 24.0 / cadence_hours
    approved_per_slot = statistics.mean(approved)
    approved_per_day = approved_per_slot * slots_per_day
    busy = [slot["reviewer_busy_seconds"] for slot in recent]
    reviewed = [slot["counts"].get("reviewed") or 0 for slot in recent]
    # A slot that stopped before its counts has no end to measure a whole slot by.
    walls = [slot["wall_minutes"] for slot in recent if slot["status"] == FINISHED and slot["wall_minutes"]]
    review_lanes = {}
    for slot in recent:
        for installation, lane in slot["review"]["lanes"].items():
            total = review_lanes.setdefault(installation, {"family": lane["family"], "calls": 0, "items": 0,
                                                           "busy_seconds": 0.0, "unanswered_calls": 0})
            for key in ("calls", "items", "busy_seconds", "unanswered_calls"):
                total[key] = round(total[key] + lane[key], 3)
    for lane in review_lanes.values():
        lane["items_per_busy_hour"] = round(lane["items"] / (lane["busy_seconds"] / 3600.0), 1) if lane["busy_seconds"] else None
        lane["mean_call_seconds"] = round(lane["busy_seconds"] / lane["calls"], 1) if lane["calls"] else None
    review_lane = {"reviewer": ", ".join(sorted(review_lanes)) or None,
                   "items_per_busy_hour": round(sum(reviewed) / (sum(busy) / 3600.0), 1) if sum(busy) else None,
                   "approved_per_busy_hour": round(sum(approved) / (sum(busy) / 3600.0), 1) if sum(busy) else None,
                   "seconds_per_item": round(sum(busy) / sum(reviewed), 3) if sum(reviewed) else None,
                   "mean_call_seconds": _mean([slot["review"]["mean_call_seconds"] for slot in recent]),
                   "mean_busy_minutes_per_slot": round(statistics.mean(busy) / 60.0, 1),
                   "utilization_of_cadence": round(statistics.mean(busy) / (cadence_hours * 3600.0), 3),
                   "utilization_of_slot_wall": _mean([slot["reviewer_utilization_of_slot"] for slot in recent], 3)}
    stage_means = {stage: _mean([slot["stage_minutes"][stage] for slot in recent if stage not in slot["restarted_stages"]])
                   for stage in STAGES}
    tokens = sum(slot["review"]["charged_tokens"] for slot in recent)
    cost = {"stage_seconds_per_approved": {stage: None if stage_means[stage] is None
                                           else round(stage_means[stage] * 60.0 / approved_per_slot, 3)
                                           for stage in STAGES},
            "reviewer_seconds_per_approved": round(sum(busy) / sum(approved), 2),
            "charged_tokens_per_approved": round(tokens / sum(approved), 1),
            "wall_minutes_per_approved": round(statistics.mean(walls) / approved_per_slot, 3) if walls else None,
            "infrastructure_usd_per_approved_at_current_rate": round(
                (allowance_usd_month / DAYS_A_MONTH) / approved_per_day, 5) if approved_per_day else None,
            "model_cost_usd": "unmetered",
            "basis": "The Tactical reviewer is the owner's own server with no price record; the only recorded money "
                     f"is the {allowance_usd_month:.0f} dollar monthly infrastructure allowance, spread over "
                     "one day's approvals at the current rate."}
    lost = [{"slot": slot["slot"], **slot["lost"]} for slot in slots if slot["lost"]]
    # Waste is counted over every slot in the journals, not only the recent ones that set the rates.
    waste = {"slots_in_journals": len(slots),
             "unanswered_review_calls": sum(slot["review"]["unanswered_calls"] for slot in slots),
             "unanswered_review_seconds": round(sum(slot["review"]["unanswered_seconds"] for slot in slots), 1),
             "items_left_without_a_verdict": sum(slot["counts"].get("left_out") or 0 for slot in slots),
             "calibration_retries": sum(slot["calibration"]["retries"] for slot in slots),
             "calibration_not_qualified_verdicts": sum(slot["calibration"]["not_qualified_verdicts"] for slot in slots),
             "calibration_attempts_moved_aside": sum(slot["calibration"]["attempts_moved_aside"] for slot in slots),
             "moved_aside_calibration_seconds": round(sum(slot["calibration"]["moved_aside_busy_seconds"]
                                                          for slot in slots), 1),
             "failed_stage_notes": sum(len(slot["failed_stage_notes"]) for slot in slots),
             "slots_that_needed_a_restart": sum(1 for slot in slots if slot["failed_stage_notes"]
                                                or slot["calibration"]["not_qualified_verdicts"]),
             "late_start_minutes": round(sum(slot["late_start_minutes"] or 0.0 for slot in slots), 2),
             "minutes_without_a_stage_note": round(sum(gap["minutes"] or 0.0 for slot in slots
                                                       for gap in slot["unattributed_gaps"]), 2),
             "minutes_in_restarted_stages": round(sum(slot["minutes_in_restarted_stages"] for slot in slots), 2),
             "unfinished_slots": [slot["slot"] for slot in slots if slot["status"] == UNFINISHED],
             "written_not_published_slots": [slot["slot"] for slot in slots if slot["status"] == WRITTEN_NOT_PUBLISHED],
             "slots_lost": lost, "approvals_lost_with_them": int(len(lost) * approved_per_slot),
             "review_startup_minutes_per_slot": _mean([slot["review"]["startup_minutes"] for slot in recent])}
    stock = read_stock(library, target=export_target, per_repository=per_repository)
    windows = []
    for slot in slots:
        if slot["review"]["first_call_at"]:
            windows.append((_parse(slot["review"]["first_call_at"]), _parse(slot["review"]["last_call_end_at"])))
    generation = [read_generation_lanes(Path(folder), windows) for folder in overnight_batches]
    bundles = [slot["bundle"] for slot in complete if slot["bundle"] and slot["bundle"].get("bytes")]
    storage = None
    if bundles:
        newest = bundles[-1]
        per_package = newest["bytes"] / newest["items"]
        storage = {"bundle_items": newest["items"], "bundle_bytes": newest["bytes"],
                   "bytes_per_package": round(per_package), "volume_bytes": volume_bytes,
                   "packages_the_volume_holds_at_this_size": int(volume_bytes / per_package),
                   "bytes_at_mark": {str(mark): int(mark * per_package) for mark in marks},
                   "marks_beyond_the_volume": [mark for mark in marks if mark * per_package > volume_bytes]}
    waiting = sum(batch["candidates"] or 0 for batch in generation) if generation else None
    # ``served`` is the count of the last checked publish; the job writes counts only after its live check, so a
    # slot without counts is never inside it.
    written = sum(slot["counts"]["approved"] for slot in slots if slot["status"] == WRITTEN_NOT_PUBLISHED)
    projection = project(served, approved_per_slot, slots_per_day, yield_per_exported, stock, marks, now,
                         serving_capacity=serving_capacity, generated_waiting=waiting, written=written)
    # Back to back, a slot takes the sum of the clean stage means; the observed walls also hold every wait for a
    # person, which a queue that stops on a failure waits for too, so both are kept.
    clean_slot_minutes = sum(value for value in stage_means.values() if value)
    if clean_slot_minutes:
        projection["if_slots_ran_back_to_back"] = project(
            served, approved_per_slot, 24.0 * 60.0 / clean_slot_minutes, yield_per_exported, stock, marks, now,
            serving_capacity=serving_capacity, generated_waiting=waiting, written=written)
        projection["if_slots_ran_back_to_back"]["slot_minutes"] = round(clean_slot_minutes, 1)
    if walls:
        projection["if_slots_ran_back_to_back_with_the_observed_walls"] = project(
            served, approved_per_slot, 24.0 * 60.0 / statistics.mean(walls), yield_per_exported, stock, marks, now,
            serving_capacity=serving_capacity, generated_waiting=waiting, written=written)
        projection["if_slots_ran_back_to_back_with_the_observed_walls"]["slot_minutes"] = round(statistics.mean(walls), 1)
    return {"record_type": RECORD_TYPE, "written_at": now.isoformat(), "library": str(library),
            "cadence_hours": cadence_hours, "recent_slots": [slot["slot"] for slot in recent],
            "stage_minutes_mean": stage_means, "review_lane": review_lane, "review_lanes": review_lanes,
            "cost_per_admitted_package": cost,
            "waste": waste, "stock": stock, "generation_batches": generation, "storage": storage,
            "projection": projection, "slots": slots}


def render_table(report: dict) -> str:
    """The plain Markdown table a reader needs: stage minutes per slot, the lane, the cost, the stock, the projection."""
    lines = [f"# Factory report {report['written_at'][:10]}", "",
             "## Stage minutes per slot", "",
             "| Slot | " + " | ".join(STAGES) + " | Gaps without a stage note | Wall | Reviewer busy | Utilization "
             "| Approved |",
             "|---|" + "---|" * (len(STAGES) + 5)]
    for slot in report["slots"]:
        cells = [("unknown" if slot["stage_minutes"].get(stage) is None else str(slot["stage_minutes"][stage]))
                 + (" restarted" if stage in slot["restarted_stages"] else "") for stage in STAGES]
        gaps = "; ".join(f"{'+'.join(gap['stages'])} {gap['minutes']}" for gap in slot["unattributed_gaps"]) or "none"
        approved = slot["counts"].get("approved")
        if slot["status"] != FINISHED:
            last = (slot.get("stop") or {}).get("last_note") or ""
            approved = f"{'' if approved is None else approved} {slot['status']}: {' '.join(last.split())[:60]}".strip()
        lines.append(f"| {slot['slot']} | " + " | ".join(cells) + f" | {gaps} | {slot['wall_minutes']} | "
                     f"{round(slot['reviewer_busy_seconds'] / 60.0, 1)} | {slot['reviewer_utilization_of_slot']} | "
                     f"{approved} |")
    lines += ["", "## Review lanes of the recent slots", "",
              "| Installation | Family | Calls | Items | Busy seconds | Items per busy hour | Mean call seconds "
              "| Unanswered calls |", "|---|---|---|---|---|---|---|---|"]
    for installation, lane in sorted(report["review_lanes"].items()):
        lines.append(f"| {installation} | {lane['family']} | {lane['calls']} | {lane['items']} | {lane['busy_seconds']} | "
                     f"{lane['items_per_busy_hour']} | {lane['mean_call_seconds']} | {lane['unanswered_calls']} |")
    for title, table in (("Review lane", report["review_lane"]), ("Cost per admitted package",
                         {k: v for k, v in report["cost_per_admitted_package"].items() if k != "basis"}),
                         ("Waste", {k: v for k, v in report["waste"].items() if k != "slots_lost"})):
        lines += ["", f"## {title}", "", "| Measure | Value |", "|---|---|"]
        for key, value in table.items():
            shown = json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else value
            lines.append(f"| {key.replace('_', ' ')} | {shown} |")
    for row in report["waste"]["slots_lost"]:
        lines.append(f"| lost slot {row['slot']} | {row['last_stage']}: {' '.join(row['reason'].split())[:100]} |")
    stock = report["stock"]
    lines += ["", "## Stock", "", "| Measure | Value |", "|---|---|"]
    for key in ("stored_candidates", "exported_so_far", "exports_drawn", "not_reviewable", "eligible_remaining",
                "held_by_repository_ceiling_in_last_export"):
        lines.append(f"| {key.replace('_', ' ')} | {stock.get(key)} |")
    curve = stock.get("draw_curve")
    if curve:
        lines.append(f"| full exports the policy supports ({stock['policy']['target']} at {stock['policy']['per_repository']} "
                     f"per repository) | {curve['full_exports_supported']} ({curve['candidates_in_full_exports']} candidates) |")
        lines.append(f"| draw of the export after them | {curve['draw_after_full_exports']} |")
        lines.append(f"| drawable within {curve['horizon_exports']} exports | {curve['drawable_within_horizon']} |")
    for batch in report["generation_batches"]:
        lines += ["", f"## Generation lanes of {batch['folder']}", "",
                  "| Lane | Candidates | Per active hour | Mean attempt seconds | Beside a review | Alone | Retries | Outcomes |",
                  "|---|---|---|---|---|---|---|---|"]
        for lane_id, row in batch["lanes"].items():
            lines.append(f"| {lane_id} | {row['candidates']} | {row['candidates_per_active_hour']} | "
                         f"{row['mean_attempt_seconds']} | {row['mean_attempt_seconds_inside_review_windows']} "
                         f"({row['attempts_inside_review_windows']}) | {row['mean_attempt_seconds_outside_review_windows']} "
                         f"({row['attempts_outside_review_windows']}) | {row['retries']} | "
                         f"{json.dumps(row['outcomes'], sort_keys=True)} |")
    storage = report.get("storage")
    if storage:
        lines += ["", "## Storage", "", f"{storage['bytes_per_package']} bytes a package in the newest bundle "
                  f"({storage['bundle_items']} packages, {storage['bundle_bytes']} bytes); the volume of "
                  f"{storage['volume_bytes']} bytes holds {storage['packages_the_volume_holds_at_this_size']} packages "
                  f"at this size; marks beyond it: {storage['marks_beyond_the_volume']}."]
    projection = report["projection"]
    lines += ["", "## Projection at the current rate", "",
              f"Served now: {projection['served_now']}, and {projection['written_not_published']} approved and written "
              f"but not yet published. Approved per slot: {projection['approved_per_slot']}. "
              f"Slots a day: {projection['slots_per_day']}. Approved a day: {projection['approved_per_day']}. "
              f"Eligible remaining in the store: {projection['eligible_remaining']}. "
              f"Stock ceiling at the measured yield: {projection['stock_ceiling']}; at the current export policy: "
              f"{projection['export_policy_ceiling']}. Serving capacity declared: {projection['serving_capacity']} "
              f"(reached in {projection['days_until_serving_capacity']} days at this rate). Generated candidates "
              f"waiting for a reviewer of another family: {projection['generated_waiting_for_another_family']} "
              "(yield not measured, outside the ceiling).", "",
              "| Mark | Short | Days | Date | Reachable from the current stock | Reachable at the current export policy "
              "| Within the serving capacity |",
              "|---|---|---|---|---|---|---|"]
    for row in projection["marks"]:
        lines.append(f"| {row['mark']} | {row['packages_short']} | {row['days_at_current_rate']} | "
                     f"{row['date_at_current_rate']} | {row['reachable_from_current_stock']} | "
                     f"{row['reachable_at_current_export_policy']} | {row['within_serving_capacity']} |")
    for key, label in (("if_slots_ran_back_to_back", "the clean stage means"),
                       ("if_slots_ran_back_to_back_with_the_observed_walls", "the observed walls, restarts included")):
        back_to_back = projection.get(key)
        if back_to_back:
            lines += ["", f"If slots ran back to back at {back_to_back['slot_minutes']} minutes a slot ({label}, "
                          f"{back_to_back['slots_per_day']:.1f} a day): {back_to_back['approved_per_day']} approved a day, "
                          f"the stock exhausted in {back_to_back['days_until_stock_is_exhausted']} days."]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--library", type=Path, default=Path("/home/username/baltor-library"))
    parser.add_argument("--overnight-batch", type=Path, action="append", default=[],
                        help="A batch folder with status.json and journal.jsonl; may repeat.")
    parser.add_argument("--served", type=int, required=True,
                        help="Packages served now, from the last checked publish (a slot's counts record).")
    parser.add_argument("--now", default=None, help="ISO time; the default is now.")
    parser.add_argument("--cadence-hours", type=float, default=DEFAULT_CADENCE_HOURS)
    parser.add_argument("--cron-minute", type=int, default=DEFAULT_CRON_MINUTE)
    parser.add_argument("--marks", default=",".join(str(mark) for mark in DEFAULT_MARKS))
    parser.add_argument("--allowance-usd-month", type=float, default=DEFAULT_ALLOWANCE_USD_MONTH)
    parser.add_argument("--recent-slots", type=int, default=3)
    parser.add_argument("--export-target", type=int, default=DEFAULT_EXPORT_TARGET)
    parser.add_argument("--per-repository", type=int, default=DEFAULT_PER_REPOSITORY)
    parser.add_argument("--volume-bytes", type=int, default=DEFAULT_VOLUME_BYTES)
    parser.add_argument("--serving-capacity", type=int, default=None,
                        help="Packages the live host was measured to hold, from the serving measurement.")
    parser.add_argument("--job-temp-root", type=Path, default=DEFAULT_TEMP_ROOT,
                        help="Where the daily job creates daily-<slot>; its birth time is the slot's first run.")
    parser.add_argument("--output", type=Path, required=True, help="Folder for the dated record and table.")
    options = parser.parse_args(argv)
    now = _parse(options.now) if options.now else datetime.now(timezone.utc)
    marks = tuple(int(mark) for mark in options.marks.split(",") if mark)
    try:
        report = build_report(library=options.library, overnight_batches=options.overnight_batch, served=options.served,
                              now=now, cadence_hours=options.cadence_hours, marks=marks,
                              allowance_usd_month=options.allowance_usd_month, cron_minute=options.cron_minute,
                              recent_slots=options.recent_slots, export_target=options.export_target,
                              per_repository=options.per_repository, volume_bytes=options.volume_bytes,
                              serving_capacity=options.serving_capacity,
                              started=lambda slot: job_started_at(options.job_temp_root, slot))
    except FactoryReportError as error:
        print(json.dumps({"record_type": RECORD_TYPE, "refused": True, "message": str(error)}))
        return 1
    options.output.mkdir(parents=True, exist_ok=True)
    stem = f"factory-report-{now.strftime('%Y-%m-%dT%H%M%SZ')}"
    (options.output / f"{stem}.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    (options.output / f"{stem}.md").write_text(render_table(report), encoding="utf-8")
    print(json.dumps({"record_type": RECORD_TYPE, "json": str(options.output / f"{stem}.json"),
                      "table": str(options.output / f"{stem}.md"), "projection": report["projection"]["marks"],
                      "review_lane": report["review_lane"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
