#!/usr/bin/env python3
"""A slot queue for the daily library job: back to back while stock and serving capacity last, restarted on a failed calibration.

Kind: operator scheduling tool, compatible with the private daily job. It does not edit that job. It reads
the measured stage times of a ``factory_report/v1`` record, plans a queue of slots, and in ``run`` mode
starts the unchanged daily job for each slot in turn with ``EXPORT_TARGET`` set. Everything it decides is
written to its own journal, and ``--dry-run`` prints the plan and the exact commands without starting
anything.

    PYTHONPATH=src:tools python tools/factory_schedule.py plan --report REPORT.json --stock 47796 \\
        --served 7900 --serving-capacity 10000 --slots 6
    PYTHONPATH=src:tools python tools/factory_schedule.py run --report REPORT.json --stock 47796 \\
        --served 7900 --serving-capacity 10000 --slots 6 \\
        --daily-job /home/username/baltor-private/tools/daily_library_release.sh --library /home/username/baltor-library \\
        --repository /home/username/.le-library-job --run-folder /home/username/.le-library/import-2026-09-24/run-1 \\
        --journal /path/to/schedule-journal.jsonl --dry-run

The rules, each answering a measured loss in the factory report of September 26, 2026:

* **Back to back.** A clean slot takes about 105 minutes from start to counts (the stage means of the
  three recent slots, restarts left out), and the fixed cadence starts one every six hours, so the
  reviewer is busy 15.0 percent of the cadence. The queue starts the next slot a
  margin after the previous one really finished (the plan's times are predictions), so one review is in
  progress at a time by construction. Queued slots are named by date, hour and minute, so none takes the
  folder of a cron slot, which is named by date and hour. A
  generation call on the same server took 5.7 seconds alone and 23.0 seconds beside a review batch, so two
  reviews side by side would gain nothing. Overlapping the next slot's export and prechecks with the
  previous review is left out on purpose: the next slot's combine would then depend on predicted timings
  to include the previous slot's reviewed folder, and a late write would publish a catalogue without it.
* **Stop at the stock and at the serving capacity.** The export target of each slot is the remaining
  stock, capped by ``--target-max``; a remainder under one review batch waits. The queue
  also stops before the served count would pass ``--serving-capacity``, the package count the live host
  was measured to hold; the serving measurement of September 26 recommends a 3 GB volume before 10,000
  packages and 4 GB of memory before 50,000. ``run`` refuses to start without a declared capacity, adds
  the approvals each finished slot wrote in its counts, shrinks or stops the next slot from that actual
  total, and stops when a finished, published slot wrote no counts.
* **Bounded re-runs, then a person.** Two of the four slots of September 26 stopped at ``the reviewer is
  not qualified today`` and were restarted by hand within two minutes, after the first calibration files
  were moved into ``attempt-1`` (the job resumes a calibration ledger it finds, which asks a different
  question from the batch of twelve). The queue does the same move, never a deletion, and starts the job
  again after a wait, at most ``--calibration-attempts`` times. A calibration stop is recognised only when
  the verdict is the journal's last note, because the job writes it and exits. Any other failure stops the
  queue with its reason and the job's last journal note recorded, because every other stop that day was a
  code or contract fault a person had to repair, or a publish whose outcome was unknown (the 16 UTC slot's
  upload timed out, and the job's own re-run then failed because the upload does not overwrite). The
  queue never repeats an external effect.
* **No second writer.** A daily job the queue did not start (the six-hourly cron line) stops the queue
  before it starts a slot, because two jobs would export and publish over each other. Without
  ``--publish`` the job writes no counts, so ``run`` refuses a queue of more than one unpublished slot.
  The hourly oracle review on the same server skips fixed hours after each cron slot; while the queue
  runs, those hours no longer match its review windows, which the decision record lists as a host setting.

Nothing here approves an item or calls a model: the daily job does its own calibration and review through
the panel and its ledger.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

PLAN_RECORD = "factory_schedule_plan/v1"
EVENT_RECORD = "factory_schedule_event/v1"
RUN_RECORD = "factory_schedule_run/v1"
DEFAULT_BATCH = 12
DEFAULT_TARGET_MAX = 2000
DEFAULT_MARGIN_MINUTES = 3.0
DEFAULT_CALIBRATION_ATTEMPTS = 3
DEFAULT_CALIBRATION_WAIT_SECONDS = 120.0
DEFAULT_MEASURED_EXPORT = 2000
NOT_QUALIFIED = "not qualified"
DAILY_JOB_NAME = "daily_library_release.sh"
#: The daily job's stages in its order, and which of them grow with the number of exported items.
STAGES = ("export", "prechecks", "calibrate", "review", "write", "combine", "bundle", "publish", "check", "counts")
PER_ITEM_STAGES = ("prechecks", "review", "write")
#: The files a calibration writes; a re-run moves them into ``attempt-N`` exactly as the hand restart did.
CALIBRATION_FILES = ("calibration.json", "calibration.log", "calibration-ledger.jsonl", "calibration-retry.json",
                     "calibration-retry.log", "calibration-retry-ledger.jsonl")


class ScheduleError(ValueError):
    """A plan or run request that cannot be honoured."""


def _parse(stamp: str) -> datetime:
    return datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone(timezone.utc)


def _iso(when: datetime) -> str:
    return when.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def measured_from_report(report: dict) -> dict:
    """The stage minutes and rates a plan needs, from a factory_report/v1 record."""
    if report.get("record_type") != "factory_report/v1":
        raise ScheduleError("the report is not a factory_report/v1 record")
    stages = report["stage_minutes_mean"]
    recent = [slot for slot in report["slots"] if slot["slot"] in set(report["recent_slots"])]
    exported = [slot["counts"]["exported"] for slot in recent if slot["counts"].get("exported")]
    passed = [slot["counts"]["passed_prechecks"] / slot["counts"]["exported"] for slot in recent
              if slot["counts"].get("exported") and slot["counts"].get("passed_prechecks") is not None]
    return {"stage_minutes": {name: float(stages.get(name) or 0.0) for name in STAGES},
            "measured_export": int(sum(exported) / len(exported)) if exported else DEFAULT_MEASURED_EXPORT,
            "precheck_pass_rate": sum(passed) / len(passed) if passed else 1.0,
            "yield_per_exported": report["projection"]["yield_per_exported"] or 0.0}


def slot_minutes(measured: dict, target: int) -> dict:
    """The predicted minutes of each stage for an export of ``target`` items: per-item stages scale with it."""
    scale = target / float(measured["measured_export"])
    return {name: measured["stage_minutes"][name] * (scale if name in PER_ITEM_STAGES else 1.0) for name in STAGES}


def slot_name(when: datetime, taken: set) -> str:
    """The queue's slot name for a start time: the date, hour and minute. The cron line names its slots by the date
    and hour alone, so a queued slot never takes the folder a later cron slot would use."""
    name = when.strftime("%Y-%m-%d-%H-%M")
    if name in taken:
        raise ScheduleError(f"slot name {name} is taken")
    return name


def plan(*, measured: dict, stock: int, slots: int, start: datetime, served: int, serving_capacity: int | None,
         batch: int = DEFAULT_BATCH, target_max: int = DEFAULT_TARGET_MAX,
         margin_minutes: float = DEFAULT_MARGIN_MINUTES, existing: set = frozenset()) -> dict:
    """The queue: each slot's name, start, export target and predicted stages; each slot starts after the last finished."""
    if measured["measured_export"] < 1 or measured["stage_minutes"]["review"] <= 0:
        raise ScheduleError("the measured review minutes and export size must be positive")
    if batch < 1 or target_max < batch:
        raise ScheduleError("target_max must hold at least one batch")
    if stock < 0 or slots < 0 or served < 0:
        raise ScheduleError("stock, slots and served are counts")
    if serving_capacity is not None and serving_capacity < 1:
        raise ScheduleError("serving_capacity is a positive package count")
    rows, taken, left, when, serving = [], set(existing), stock, start, served
    stopped_by = "slots"
    for _index in range(slots):
        # The job reviews what passes the prechecks in batches of ``batch``; an export smaller than one batch
        # is not worth a slot's fixed stages.
        target = min(target_max, left)
        if target < batch:
            stopped_by = "stock"
            break
        approved = int(target * measured["yield_per_exported"])
        if serving_capacity is not None and serving + approved > serving_capacity:
            # Shrink the export to what the capacity still admits; stop when not even one batch fits.
            room = serving_capacity - serving
            target = min(target, int(room / measured["yield_per_exported"])) if room > 0 else 0
            if target < batch:
                stopped_by = "serving_capacity"
                break
            approved = int(target * measured["yield_per_exported"])
        name = slot_name(when, taken)
        taken.add(name)
        minutes = slot_minutes(measured, target)
        review_start = when + timedelta(minutes=minutes["export"] + minutes["prechecks"] + minutes["calibrate"])
        review_end = review_start + timedelta(minutes=minutes["review"])
        finish = when + timedelta(minutes=sum(minutes.values()))
        serving += approved
        rows.append({"slot": name, "start_at": _iso(when), "export_target": target,
                     "predicted_reviewed": int(target * measured["precheck_pass_rate"]),
                     "predicted_approved": approved, "predicted_review_start": _iso(review_start),
                     "predicted_review_end": _iso(review_end), "predicted_finish": _iso(finish),
                     "predicted_served_after": serving, "stock_left_after": left - target})
        left -= target
        when = finish + timedelta(minutes=margin_minutes)
    hours = ((_parse(rows[-1]["predicted_finish"]) - start).total_seconds() / 3600.0) if rows else 0.0
    approved = sum(row["predicted_approved"] for row in rows)
    return {"record_type": PLAN_RECORD, "planned_at": _iso(start), "measured": measured, "stock": stock,
            "served": served, "serving_capacity": serving_capacity, "batch": batch, "target_max": target_max,
            "margin_minutes": margin_minutes, "slots": rows, "stopped_by": stopped_by,
            "predicted_approved": approved, "predicted_hours": round(hours, 2),
            "predicted_approved_per_day": round(approved / hours * 24.0, 1) if hours else None,
            "stock_left": left}


def render_plan(record: dict) -> str:
    lines = ["| Slot | Start | Export target | Review window | Finish | Approved (predicted) | Served after | Stock left |",
             "|---|---|---|---|---|---|---|---|"]
    for row in record["slots"]:
        lines.append(f"| {row['slot']} | {row['start_at']} | {row['export_target']} | {row['predicted_review_start']} "
                     f"to {row['predicted_review_end']} | {row['predicted_finish']} | {row['predicted_approved']} | "
                     f"{row['predicted_served_after']} | {row['stock_left_after']} |")
    lines.append(f"\nPredicted: {record['predicted_approved']} approved in {record['predicted_hours']} hours "
                 f"({record['predicted_approved_per_day']} a day); {record['stock_left']} of the stock left; "
                 f"the queue ends at the {record['stopped_by'].replace('_', ' ')}.")
    return "\n".join(lines)


def _event(journal: Path | None, **fields) -> dict:
    event = {"record_type": EVENT_RECORD, "at": _iso(datetime.now(timezone.utc)), **fields}
    if journal is not None:
        journal.parent.mkdir(parents=True, exist_ok=True)
        with journal.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
    print(json.dumps(event, sort_keys=True), flush=True)
    return event


def _journal(library: Path, slot: str) -> list:
    journal = library / "daily" / slot / "journal.jsonl"
    if not journal.is_file():
        return []
    return [json.loads(line) for line in journal.read_text(encoding="utf-8").splitlines() if line.strip()]


def last_journal_note(library: Path, slot: str) -> dict | None:
    """The slot's last journal note, shortened, so a stop names what the job itself said."""
    notes = _journal(library, slot)
    if not notes:
        return None
    return {"stage": notes[-1].get("stage"), "at": notes[-1].get("at"), "note": " ".join(notes[-1].get("note", "").split())[:240]}


def stopped_at_calibration(library: Path, slot: str) -> bool:
    """Whether the slot's run ended at a calibration that did not qualify the reviewer: the journal's last note is
    that verdict and no calibration done marker exists. The job writes the verdict and exits at once, so an earlier
    verdict followed by a different failure is that failure, not a calibration stop."""
    notes = _journal(library, slot)
    return (bool(notes) and notes[-1].get("stage") == "calibrate" and NOT_QUALIFIED in notes[-1].get("note", "")
            and not (library / "daily" / slot / "calibrate.done").is_file())


def move_calibration_aside(library: Path, slot: str) -> dict:
    """Move the slot's calibration files into the next free ``attempt-N`` folder; nothing is deleted."""
    work = library / "daily" / slot
    number = 1
    while (work / f"attempt-{number}").exists():
        number += 1
    target = work / f"attempt-{number}"
    moved = []
    for name in CALIBRATION_FILES:
        source = work / name
        if source.is_file():
            target.mkdir(exist_ok=True)
            source.rename(target / name)
            moved.append(name)
    return {"folder": target.name if moved else None, "moved": moved}


def running_daily_jobs(proc: Path = Path("/proc")) -> list:
    """Every running daily job as (process id, slot), read from the process table without effects."""
    found = []
    for entry in proc.iterdir() if proc.is_dir() else ():
        if not entry.name.isdigit():
            continue
        try:
            argv = (entry / "cmdline").read_bytes().split(b"\0")
        except OSError:
            continue
        words = [part.decode("utf-8", "replace") for part in argv if part]
        for index, word in enumerate(words):
            if word.endswith(DAILY_JOB_NAME) and index + 1 < len(words):
                found.append((int(entry.name), words[index + 1]))
                break
    return found


def approved_in_slot(library: Path, slot: str) -> int | None:
    """The approvals the finished slot recorded in its counts, or None when it wrote none."""
    counts = library / "daily" / slot / "counts.json"
    if not counts.is_file():
        return None
    value = json.loads(counts.read_text(encoding="utf-8")).get("approved")
    return int(value) if isinstance(value, int) else None


def job_command(daily_job: Path, slot: str, publish: bool) -> list:
    command = ["bash", str(daily_job), slot]
    if publish:
        command.append("--publish")
    return command


def run(record: dict, *, daily_job: Path, library: Path, journal: Path | None, dry_run: bool, publish: bool,
        calibration_attempts: int = DEFAULT_CALIBRATION_ATTEMPTS,
        calibration_wait_seconds: float = DEFAULT_CALIBRATION_WAIT_SECONDS, sleeper=time.sleep,
        clock=lambda: datetime.now(timezone.utc), runner=subprocess.run, environment=None,
        job_settings: dict | None = None, foreign_jobs=running_daily_jobs) -> dict:
    """Start the daily job for each planned slot in turn; re-run a calibration stop; stop on anything else."""
    if calibration_attempts < 1:
        raise ScheduleError("calibration_attempts is at least one")
    if record.get("serving_capacity") is None and not dry_run:
        raise ScheduleError("run needs a plan with a declared serving capacity")
    if not publish and len(record["slots"]) > 1:
        # Without --publish the job stops after the bundle and writes no counts, so the queue could not count what
        # the next slot's combine would carry; one slot at a time is the honest bound.
        raise ScheduleError("without --publish the daily job writes no counts; run one slot at a time")
    outcome = {"record_type": RUN_RECORD, "dry_run": dry_run, "slots": [], "stopped": None}
    served, capacity = record.get("served", 0), record.get("serving_capacity")
    rate = record["measured"]["yield_per_exported"]
    for index, row in enumerate(record["slots"]):
        command = job_command(daily_job, row["slot"], publish)
        target = row["export_target"]
        if dry_run:
            _event(journal, event="would_start", slot=row["slot"], at_planned=row["start_at"],
                   command=" ".join(command), export_target=target, settings=sorted((job_settings or {}).items()))
            outcome["slots"].append({"slot": row["slot"], "result": "dry_run", "command": command})
            continue
        # The room is re-read from the counts the finished slots wrote, not from the plan's prediction.
        if capacity is not None and served + int(target * rate) > capacity:
            target = int(max(0, capacity - served) / rate) if rate > 0 else 0
            if target < record.get("batch", 1):
                _event(journal, event="queue_stopped", slot=row["slot"], reason="serving_capacity", served=served)
                outcome["stopped"] = {"slot": row["slot"], "reason": "serving_capacity",
                                      "needs": "a person: extend the host before the next slot"}
                break
            _event(journal, event="export_target_reduced", slot=row["slot"], planned=row["export_target"],
                   export_target=target, served=served)
        env = dict(environment if environment is not None else os.environ)
        env.update(job_settings or {})
        env["EXPORT_TARGET"] = str(target)
        # The first slot waits for its planned start; each later one starts a margin after the last one ended.
        wait = ((_parse(row["start_at"]) - clock()).total_seconds() if index == 0
                else record.get("margin_minutes", DEFAULT_MARGIN_MINUTES) * 60.0)
        if wait > 0:
            _event(journal, event="waiting", slot=row["slot"], seconds=round(wait, 1))
            sleeper(wait)
        others = foreign_jobs()
        if others:
            reason = "another_daily_job_is_running"
            _event(journal, event="queue_stopped", slot=row["slot"], reason=reason,
                   jobs=[{"pid": pid, "slot": slot} for pid, slot in others])
            outcome["stopped"] = {"slot": row["slot"], "reason": reason,
                                  "needs": "a person: pause the cron line of the daily job while the queue runs"}
            break
        attempts, result = 0, None
        while True:  # the single bound is the calibration check below; every other exit breaks at once
            attempts += 1
            _event(journal, event="start", slot=row["slot"], attempt=attempts, export_target=target,
                   planned_start=row["start_at"], command=" ".join(command))
            completed = runner(command, env=env)
            code = completed.returncode
            if code == 0:
                result = "finished"
                break
            if stopped_at_calibration(library, row["slot"]):
                _event(journal, event="calibration_stop", slot=row["slot"], attempt=attempts, exit_code=code)
                if attempts < calibration_attempts:
                    moved = move_calibration_aside(library, row["slot"])
                    _event(journal, event="calibration_moved_aside", slot=row["slot"], **moved)
                    sleeper(calibration_wait_seconds)
                    continue
                result = "gave_up_after_calibration_stops"
                break
            result = f"failed_exit_{code}"
            break
        approved = approved_in_slot(library, row["slot"]) if result == "finished" else None
        _event(journal, event="slot_end", slot=row["slot"], result=result, attempts=attempts, approved=approved)
        outcome["slots"].append({"slot": row["slot"], "result": result, "attempts": attempts, "approved": approved})
        if result != "finished":
            # Every other stop is left to a person, including a publish whose outcome is unknown: the queue never
            # repeats an external effect, and the job's own re-run of such a publish failed on September 26
            # because the upload does not overwrite.
            last = last_journal_note(library, row["slot"])
            outcome["stopped"] = {"slot": row["slot"], "reason": result, "last_note": last,
                                  "needs": "a person: the queue stops on a failure it cannot resolve by a re-run"}
            _event(journal, event="queue_stopped", slot=row["slot"], reason=result, last_note=last)
            break
        if approved is None and not publish:
            # Without --publish the job ends at the bundle and writes no counts by design; nothing was served, and
            # the rule above allows only this one slot.
            continue
        if approved is None:
            # Without counts the served total is unknown, so the capacity gate cannot be honoured: stop.
            last = last_journal_note(library, row["slot"])
            outcome["stopped"] = {"slot": row["slot"], "reason": "counts_missing_after_finish", "last_note": last,
                                  "needs": "a person: read the slot's journal before the queue continues"}
            _event(journal, event="queue_stopped", slot=row["slot"], reason="counts_missing_after_finish",
                   last_note=last)
            break
        served += approved
    outcome["served_after"] = served
    return outcome


def _existing(library: Path | None) -> set:
    if library is None or not (library / "daily").is_dir():
        return set()
    return {folder.name for folder in (library / "daily").iterdir() if folder.is_dir()}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "run"):
        command = commands.add_parser(name)
        command.add_argument("--report", type=Path, required=True,
                             help="A factory_report/v1 record with the measured stage times.")
        command.add_argument("--stock", type=int, required=True, help="Eligible candidates no export has drawn.")
        command.add_argument("--served", type=int, required=True, help="Packages served now.")
        command.add_argument("--serving-capacity", type=int, default=None,
                             help="Packages the live host was measured to hold; run refuses without it.")
        command.add_argument("--slots", type=int, default=4)
        command.add_argument("--start", default=None, help="ISO time of the first slot; the default is now.")
        command.add_argument("--batch", type=int, default=DEFAULT_BATCH)
        command.add_argument("--target-max", type=int, default=DEFAULT_TARGET_MAX)
        command.add_argument("--margin-minutes", type=float, default=DEFAULT_MARGIN_MINUTES)
        command.add_argument("--library", type=Path, default=None, help="The library root; its daily folder names are taken.")
        command.add_argument("--output", type=Path, default=None, help="Where to write the plan record.")
        if name == "run":
            command.add_argument("--daily-job", type=Path, required=True)
            command.add_argument("--repository", default=None, help="REPOSITORY for the job, as the cron line sets it.")
            command.add_argument("--run-folder", default=None, help="RUN_FOLDER for the job, as the cron line sets it.")
            command.add_argument("--journal", type=Path, default=None)
            command.add_argument("--dry-run", action="store_true")
            command.add_argument("--no-publish", action="store_true")
            command.add_argument("--calibration-attempts", type=int, default=DEFAULT_CALIBRATION_ATTEMPTS)
            command.add_argument("--calibration-wait-seconds", type=float, default=DEFAULT_CALIBRATION_WAIT_SECONDS)
    options = parser.parse_args(argv)
    try:
        measured = measured_from_report(json.loads(Path(options.report).read_text(encoding="utf-8")))
        start = _parse(options.start) if options.start else datetime.now(timezone.utc)
        record = plan(measured=measured, stock=options.stock, slots=options.slots, start=start, served=options.served,
                      serving_capacity=options.serving_capacity, batch=options.batch, target_max=options.target_max,
                      margin_minutes=options.margin_minutes, existing=_existing(options.library))
        if options.output:
            options.output.parent.mkdir(parents=True, exist_ok=True)
            options.output.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(render_plan(record))
        if options.command == "run":
            if options.library is None:
                raise ScheduleError("run needs --library")
            settings = {key: value for key, value in (("REPOSITORY", options.repository),
                                                      ("RUN_FOLDER", options.run_folder)) if value}
            outcome = run(record, daily_job=options.daily_job, library=options.library, journal=options.journal,
                          dry_run=options.dry_run, publish=not options.no_publish,
                          calibration_attempts=options.calibration_attempts,
                          calibration_wait_seconds=options.calibration_wait_seconds, job_settings=settings)
            print(json.dumps(outcome, sort_keys=True))
            return 0 if outcome["stopped"] is None else 1
    except ScheduleError as error:
        print(json.dumps({"record_type": PLAN_RECORD, "refused": True, "message": str(error)}))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
