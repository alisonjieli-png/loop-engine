"""Checks for tools/factory_schedule.py: the plan's bounds, one review at a time, the dry run, and bounded re-runs.

The known-wrong cases come first: a plan that would draw more than the stock, a plan that would serve
more packages than the host was measured to hold, a run that trusts the plan's predicted approvals over
the counts the slots wrote, two reviews at once, a queued slot that takes a cron slot's folder, a run
that would start a job in dry-run mode, a re-run that would resume the failed calibration's ledger, a
queue that keeps re-running a failed calibration without a bound, a queue that starts beside a daily
job it did not start, an older calibration verdict read as a new stop after a different failure, and a
queue of unpublished slots whose counts the job never writes.
Removing the bound in ``run`` fails ``test_calibration_re_runs_stop_at_the_bound``; removing the stock
rule in ``plan`` fails ``test_plan_never_draws_more_than_the_stock``; removing the capacity rule fails
``test_plan_stops_at_the_serving_capacity``; removing the move fails
``test_a_calibration_stop_is_re_run_after_moving_the_attempt_aside``; removing the foreign-job guard fails
``test_a_foreign_daily_job_stops_the_queue``; reading the last calibration note instead of the last note fails
``test_an_older_calibration_verdict_before_another_failure_is_not_re_run``; removing the publish rule fails
``test_a_queue_without_publish_runs_one_slot_at_a_time``.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import factory_schedule  # noqa: E402

#: The stage means of the September 26, 2026 factory report, rounded (slot 2026-09-26-10 alone is 98.6 minutes).
MEASURED = {"stage_minutes": {"export": 0.4, "prechecks": 15.4, "calibrate": 0.8, "review": 64.2, "write": 14.2,
                              "combine": 0.2, "bundle": 0.2, "publish": 3.1, "check": 0.0, "counts": 0.0},
            "measured_export": 2000, "precheck_pass_rate": 0.83, "yield_per_exported": 0.795}
START = datetime(2026, 9, 26, 13, 0, tzinfo=timezone.utc)

#: A stand-in daily job: fails at calibration the first FAILS times (writing the journal note and the calibration
#: ledger the real job writes, and refusing to start when an earlier attempt's ledger is still in place, which is
#: the resume hazard), then writes the done markers and exits 0. It records every invocation and its settings.
FAKE_JOB = textwrap.dedent("""\
    #!/usr/bin/env bash
    LIBRARY="$FAKE_LIBRARY"; SLOT="$1"; WORK="$LIBRARY/daily/$SLOT"; mkdir -p "$WORK"
    echo "$SLOT $EXPORT_TARGET $2 ${REPOSITORY:-none} ${RUN_FOLDER:-none}" >> "$LIBRARY/invocations.txt"
    if [ -f "$WORK/calibration-ledger.jsonl" ]; then
      echo '{"at":"2026-09-26T13:00:00Z","stage":"calibrate","note":"resumed an earlier ledger"}' >> "$WORK/journal.jsonl"
      exit 3
    fi
    COUNT=$(grep -c "^$SLOT " "$LIBRARY/invocations.txt")
    if [ "$COUNT" -le "$FAKE_FAILS" ]; then
      echo '{"record_type":"candidate_review_batch_call/v1"}' > "$WORK/calibration-ledger.jsonl"
      echo '{}' > "$WORK/calibration.json"
      echo '{"at":"2026-09-26T13:00:00Z","stage":"calibrate","note":"the reviewer is not qualified today; no real package is reviewed"}' >> "$WORK/journal.jsonl"
      exit 1
    fi
    if [ "$FAKE_OTHER_FAILURE" = "1" ]; then
      echo '{"at":"2026-09-26T13:00:00Z","stage":"review","note":"review failed: boom"}' >> "$WORK/journal.jsonl"
      exit 1
    fi
    if [ "$2" != "--publish" ]; then
      for s in export prechecks calibrate review write combine bundle; do touch "$WORK/$s.done"; done
      exit 0
    fi
    for s in export prechecks calibrate review write combine bundle publish check counts; do touch "$WORK/$s.done"; done
    echo "{\\"record_type\\":\\"daily_library_release_counts/v2\\",\\"approved\\":${FAKE_APPROVED:-1590}}" > "$WORK/counts.json"
    echo '{"at":"2026-09-26T13:00:00Z","stage":"counts","note":"done"}' >> "$WORK/journal.jsonl"
    exit 0
    """)


def _minutes_between(earlier: str, later: str) -> float:
    return (factory_schedule._parse(later) - factory_schedule._parse(earlier)).total_seconds() / 60.0


class PlanChecks(unittest.TestCase):
    def test_plan_never_draws_more_than_the_stock(self):
        record = factory_schedule.plan(measured=MEASURED, stock=5000, slots=10, start=START, served=0,
                                       serving_capacity=None)
        targets = [row["export_target"] for row in record["slots"]]
        self.assertEqual(targets, [2000, 2000, 1000])  # the queue ends with the stock, not the slot count
        self.assertEqual(record["stock_left"], 0)
        self.assertEqual(record["stopped_by"], "stock")
        small = factory_schedule.plan(measured=MEASURED, stock=2011, slots=10, start=START, served=0,
                                      serving_capacity=None)
        self.assertEqual([row["export_target"] for row in small["slots"]], [2000])  # 11 left is under one batch
        self.assertEqual(small["stock_left"], 11)

    def test_plan_stops_at_the_serving_capacity(self):
        record = factory_schedule.plan(measured=MEASURED, stock=100_000, slots=10, start=START, served=7900,
                                       serving_capacity=10_000)
        self.assertEqual(record["stopped_by"], "serving_capacity")
        self.assertLessEqual(record["slots"][-1]["predicted_served_after"], 10_000)
        self.assertEqual(record["slots"][0]["export_target"], 2000)  # 1590 approvals fit under 10,000
        self.assertEqual(record["slots"][1]["export_target"], 641)  # the rest of the room at the measured yield
        self.assertEqual(len(record["slots"]), 2)
        full = factory_schedule.plan(measured=MEASURED, stock=100_000, slots=10, start=START, served=10_000,
                                     serving_capacity=10_000)
        self.assertEqual(full["slots"], [])
        self.assertEqual(full["stopped_by"], "serving_capacity")

    def test_slots_run_back_to_back_with_one_review_at_a_time(self):
        record = factory_schedule.plan(measured=MEASURED, stock=100_000, slots=5, start=START, served=0,
                                       serving_capacity=None, margin_minutes=3.0)
        rows = record["slots"]
        self.assertEqual(len(rows), 5)
        for earlier, later in zip(rows, rows[1:]):
            self.assertAlmostEqual(_minutes_between(earlier["predicted_finish"], later["start_at"]), 3.0, places=6)
            self.assertGreater(_minutes_between(earlier["predicted_review_end"], later["predicted_review_start"]), 0.0)
        first = rows[0]
        self.assertEqual(first["predicted_reviewed"], 1660)
        self.assertEqual(first["predicted_approved"], 1590)
        self.assertAlmostEqual(_minutes_between(first["start_at"], first["predicted_finish"]), 98.5, places=0)
        # Back to back is about 14 slots a day against four on the six-hour cadence.
        self.assertGreater(record["predicted_approved_per_day"], 3 * 4 * 1590)

    def test_a_smaller_export_shortens_only_the_per_item_stages(self):
        minutes = factory_schedule.slot_minutes(MEASURED, 1000)
        self.assertAlmostEqual(minutes["review"], 32.1)
        self.assertAlmostEqual(minutes["prechecks"], 7.7)
        self.assertAlmostEqual(minutes["publish"], 3.1)

    def test_slot_names_never_take_a_cron_slot_folder(self):
        # The cron line names its slots YYYY-MM-DD-HH; a queued slot always carries its minute.
        record = factory_schedule.plan(measured=MEASURED, stock=100_000, slots=2, start=START, served=0,
                                       serving_capacity=None, existing={"2026-09-26-13"})
        self.assertEqual(record["slots"][0]["slot"], "2026-09-26-13-00")
        self.assertEqual(record["slots"][1]["slot"], "2026-09-26-14-41")
        with self.assertRaises(factory_schedule.ScheduleError):
            factory_schedule.plan(measured=MEASURED, stock=100_000, slots=1, start=START, served=0,
                                  serving_capacity=None, existing={"2026-09-26-13-00"})

    def test_known_wrong_measurements_are_refused(self):
        broken = {**MEASURED, "stage_minutes": {**MEASURED["stage_minutes"], "review": 0.0}}
        with self.assertRaises(factory_schedule.ScheduleError):
            factory_schedule.plan(measured=broken, stock=100, slots=1, start=START, served=0, serving_capacity=None)
        with self.assertRaises(factory_schedule.ScheduleError):
            factory_schedule.plan(measured=MEASURED, stock=100, slots=1, start=START, served=0, serving_capacity=None,
                                  target_max=6)
        with self.assertRaises(factory_schedule.ScheduleError):
            factory_schedule.plan(measured=MEASURED, stock=100, slots=1, start=START, served=0, serving_capacity=0)
        with self.assertRaises(factory_schedule.ScheduleError):
            factory_schedule.measured_from_report({"record_type": "something_else/v1"})

    def test_measured_values_come_from_a_factory_report(self):
        measured = factory_schedule.measured_from_report(_report())
        self.assertEqual(measured["stage_minutes"]["review"], 64.0)
        self.assertEqual(measured["measured_export"], 2000)
        self.assertEqual(measured["precheck_pass_rate"], 0.83)
        self.assertEqual(measured["yield_per_exported"], 0.795)


def _report() -> dict:
    return {"record_type": "factory_report/v1", "recent_slots": ["s1"],
            "stage_minutes_mean": {"export": 0.4, "prechecks": 15.0, "calibrate": 2.0, "review": 64.0, "write": 13.0,
                                   "combine": 0.1, "bundle": 0.1, "publish": 3.0, "check": 0.0, "counts": 0.0},
            "review_lane": {"seconds_per_item": 1.915}, "projection": {"yield_per_exported": 0.795},
            "slots": [{"slot": "s1", "review": {"startup_minutes": 12.1},
                       "counts": {"exported": 2000, "passed_prechecks": 1660}}]}


class RunChecks(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="factory-schedule-", dir=os.environ.get("TMPDIR")))
        self.library = self.root / "library"
        (self.library / "daily").mkdir(parents=True)
        self.job = self.root / "daily_job.sh"
        self.job.write_text(FAKE_JOB, encoding="utf-8")
        self.journal = self.root / "schedule-journal.jsonl"
        self.record = factory_schedule.plan(measured=MEASURED, stock=4000, slots=2, start=START, served=0,
                                            serving_capacity=25_000)

    def _env(self, fails: int, other_failure: bool = False, approved: int = 1590) -> dict:
        return {**os.environ, "FAKE_LIBRARY": str(self.library), "FAKE_FAILS": str(fails),
                "FAKE_OTHER_FAILURE": "1" if other_failure else "0", "FAKE_APPROVED": str(approved)}

    def _run(self, fails: int, *, attempts: int = 3, dry_run: bool = False, other_failure: bool = False,
             foreign=lambda: [], record=None, approved: int = 1590, publish: bool = True) -> dict:
        return factory_schedule.run(record or self.record, daily_job=self.job, library=self.library,
                                    journal=self.journal, dry_run=dry_run, publish=publish,
                                    calibration_attempts=attempts, calibration_wait_seconds=0.0,
                                    sleeper=lambda seconds: None, clock=lambda: START + timedelta(days=1),
                                    runner=subprocess.run, environment=self._env(fails, other_failure, approved),
                                    job_settings={"REPOSITORY": "/job/checkout", "RUN_FOLDER": "/run/folder"},
                                    foreign_jobs=foreign)

    def _invocations(self) -> list:
        path = self.library / "invocations.txt"
        return path.read_text(encoding="utf-8").splitlines() if path.is_file() else []

    def _events(self) -> list:
        return [json.loads(line)["event"] for line in self.journal.read_text(encoding="utf-8").splitlines()]

    def test_dry_run_starts_nothing_and_prints_the_commands(self):
        outcome = self._run(0, dry_run=True)
        self.assertEqual(self._invocations(), [])
        self.assertEqual([row["result"] for row in outcome["slots"]], ["dry_run", "dry_run"])
        events = [json.loads(line) for line in self.journal.read_text(encoding="utf-8").splitlines()]
        self.assertEqual([event["event"] for event in events], ["would_start", "would_start"])
        self.assertIn("--publish", events[0]["command"])

    def test_the_export_target_and_the_cron_settings_reach_the_job(self):
        outcome = self._run(0)
        self.assertEqual([row["result"] for row in outcome["slots"]], ["finished", "finished"])
        second = self.record["slots"][1]["slot"]
        self.assertEqual(self._invocations(), ["2026-09-26-13-00 2000 --publish /job/checkout /run/folder",
                                               f"{second} 2000 --publish /job/checkout /run/folder"])
        self.assertIsNone(outcome["stopped"])
        self.assertEqual(outcome["served_after"], 3180)

    def test_actual_counts_shrink_the_next_export(self):
        # More approvals than predicted leave less room: the third slot's export shrinks to what still fits.
        record = factory_schedule.plan(measured=MEASURED, stock=100_000, slots=3, start=START, served=0,
                                       serving_capacity=3400)
        self.assertEqual([row["export_target"] for row in record["slots"]], [2000, 2000, 276])
        outcome = self._run(0, record=record, approved=1650)
        self.assertIsNone(outcome["stopped"])
        self.assertEqual(self._invocations()[2].split()[1], "125")  # room 100 at the measured yield
        self.assertIn("export_target_reduced", self._events())

    def test_actual_counts_stop_the_queue_at_the_serving_capacity(self):
        record = factory_schedule.plan(measured=MEASURED, stock=100_000, slots=3, start=START, served=0,
                                       serving_capacity=3300)
        outcome = self._run(0, record=record, approved=1700)
        self.assertEqual(len(self._invocations()), 2)
        self.assertEqual(outcome["stopped"]["reason"], "serving_capacity")
        self.assertEqual(outcome["served_after"], 3400)

    def test_a_calibration_stop_is_re_run_after_moving_the_attempt_aside(self):
        outcome = self._run(1)
        self.assertEqual(outcome["slots"][0], {"slot": "2026-09-26-13-00", "result": "finished", "attempts": 2,
                                               "approved": 1590})
        work = self.library / "daily" / "2026-09-26-13-00"
        self.assertTrue((work / "attempt-1" / "calibration-ledger.jsonl").is_file())
        self.assertTrue((work / "attempt-1" / "calibration.json").is_file())
        self.assertFalse((work / "calibration-ledger.jsonl").exists())
        self.assertIn("calibration_moved_aside", self._events())

    def test_calibration_re_runs_stop_at_the_bound(self):
        # The fake job would qualify on its fifth attempt; a bound of three must give up first and stop the queue.
        outcome = self._run(4, attempts=3)
        self.assertEqual(outcome["slots"][0]["result"], "gave_up_after_calibration_stops")
        self.assertEqual(outcome["slots"][0]["attempts"], 3)
        self.assertEqual(len(self._invocations()), 3)
        self.assertEqual(outcome["stopped"]["slot"], "2026-09-26-13-00")
        self.assertEqual(len(outcome["slots"]), 1)  # the second slot is not started
        work = self.library / "daily" / "2026-09-26-13-00"
        self.assertEqual(sorted(p.name for p in work.glob("attempt-*")), ["attempt-1", "attempt-2"])

    def test_another_failure_stops_the_queue_without_a_re_run(self):
        outcome = self._run(0, other_failure=True)
        self.assertEqual(outcome["slots"][0]["result"], "failed_exit_1")
        self.assertEqual(len(self._invocations()), 1)
        self.assertEqual(outcome["stopped"]["reason"], "failed_exit_1")
        self.assertEqual(outcome["stopped"]["last_note"]["note"], "review failed: boom")

    def test_an_older_calibration_verdict_before_another_failure_is_not_re_run(self):
        # Known-wrong case: the first attempt stopped at calibration, the re-run failed in review, and the queue
        # read the older verdict as a new calibration stop and started the job a third time.
        outcome = self._run(1, other_failure=True)
        self.assertEqual(outcome["slots"][0]["result"], "failed_exit_1")
        self.assertEqual(outcome["slots"][0]["attempts"], 2)
        self.assertEqual(len(self._invocations()), 2)
        self.assertEqual(outcome["stopped"]["last_note"]["stage"], "review")

    def test_a_queue_without_publish_runs_one_slot_at_a_time(self):
        # Known-wrong case: without --publish the job writes no counts, so a second slot would combine an
        # unpublished folder the capacity count never saw.
        with self.assertRaises(factory_schedule.ScheduleError):
            self._run(0, publish=False)
        with self.assertRaises(factory_schedule.ScheduleError):
            self._run(0, publish=False, dry_run=True)
        self.assertEqual(self._invocations(), [])
        single = factory_schedule.plan(measured=MEASURED, stock=4000, slots=1, start=START, served=0,
                                       serving_capacity=25_000)
        outcome = self._run(0, publish=False, record=single)
        self.assertEqual(self._invocations(), ["2026-09-26-13-00 2000  /job/checkout /run/folder"])
        # Like the real job, the unpublished slot ends at the bundle without counts, which is not a stop.
        self.assertEqual(outcome["slots"][0], {"slot": "2026-09-26-13-00", "result": "finished", "attempts": 1,
                                               "approved": None})
        self.assertIsNone(outcome["stopped"])
        self.assertEqual(outcome["served_after"], 0)

    def test_a_foreign_daily_job_stops_the_queue(self):
        outcome = self._run(0, foreign=lambda: [(4167923, "2026-09-26-16")])
        self.assertEqual(self._invocations(), [])
        self.assertEqual(outcome["stopped"]["reason"], "another_daily_job_is_running")

    def test_a_zero_attempt_bound_and_a_missing_capacity_are_refused(self):
        with self.assertRaises(factory_schedule.ScheduleError):
            self._run(0, attempts=0)
        unbounded = factory_schedule.plan(measured=MEASURED, stock=4000, slots=1, start=START, served=0,
                                          serving_capacity=None)
        with self.assertRaises(factory_schedule.ScheduleError):
            self._run(0, record=unbounded)
        self.assertEqual(self._invocations(), [])

    def test_the_process_table_reader_finds_daily_jobs(self):
        proc = self.root / "proc"
        for pid, argv in ((10, [b"bash", b"/x/daily_library_release.sh", b"2026-09-26-16", b"--publish"]),
                          (11, [b"python", b"other.py"]), (12, [b"bash", b"/x/daily_library_release.sh"])):
            (proc / str(pid)).mkdir(parents=True)
            (proc / str(pid) / "cmdline").write_bytes(b"\0".join(argv) + b"\0")
        (proc / "self").mkdir()
        self.assertEqual(factory_schedule.running_daily_jobs(proc), [(10, "2026-09-26-16")])

    def test_main_plan_and_dry_run(self):
        report = self.root / "report.json"
        report.write_text(json.dumps(_report()), encoding="utf-8")
        out = self.root / "plan.json"
        code = factory_schedule.main(["plan", "--report", str(report), "--stock", "3000", "--served", "6398",
                                      "--slots", "4", "--start", "2026-09-26T13:00:00Z", "--output", str(out)])
        self.assertEqual(code, 0)
        record = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual([row["export_target"] for row in record["slots"]], [2000, 1000])
        code = factory_schedule.main(["run", "--report", str(report), "--stock", "3000", "--served", "6398",
                                      "--serving-capacity", "10000", "--slots", "1",
                                      "--start", "2026-09-26T13:00:00Z", "--daily-job", str(self.job),
                                      "--library", str(self.library), "--dry-run"])
        self.assertEqual(code, 0)
        self.assertEqual(self._invocations(), [])


if __name__ == "__main__":
    unittest.main()
