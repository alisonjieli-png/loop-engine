"""Checks for tools/factory_report.py on a small synthetic library: stage minutes, the review split, waste and the projection."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import factory_report  # noqa: E402


def _write_jsonl(path: Path, rows: list) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _call(started_at: str, elapsed: float, outcome: str = "batch_answered", members: int = 12, tokens: int = 60000,
          installation: str = "tactical.reviewer-a", family: str = "google") -> dict:
    return {"record_type": "candidate_review_batch_call/v1", "started_at": started_at, "elapsed_seconds": elapsed,
            "outcome": outcome, "members": [{"position": i} for i in range(members)], "charged_tokens": tokens,
            "usage": {"input_tokens": tokens - 1000, "output_tokens": 1000}, "installation_id": installation,
            "family": family}


def _shift(rows: list, hours: int) -> list:
    """The fixture's times are written for the 10 UTC slot; a slot of another hour runs the same stages at its hour."""
    shifted = []
    for row in rows:
        row = dict(row)
        for key in ("at", "started_at"):
            if key in row:
                when = datetime.fromisoformat(row[key].replace("Z", "+00:00")) + timedelta(hours=hours)
                row[key] = when.strftime("%Y-%m-%dT%H:%M:%SZ")
        shifted.append(row)
    return shifted


def make_slot(daily: Path, name: str, *, approved: int = 1500, exported: int = 2000, passed: int = 1660,
              with_failure: bool = False, published_by_hand: bool = False, restarted_export: bool = False,
              stop_at_publish: bool = False) -> Path:
    folder = daily / name
    folder.mkdir(parents=True)
    parts = name.split("-")
    hours = int(parts[3]) - 10 if len(parts) >= 4 and parts[3].isdigit() else 0
    journal = [{"at": "2026-09-26T10:18:00Z", "stage": "export", "note": "export failed: boom"}] if restarted_export else []
    journal += [{"at": "2026-09-26T10:27:00Z", "stage": "export", "note": "done"},
                {"at": "2026-09-26T10:42:00Z", "stage": "prechecks", "note": "done"}]
    if with_failure:
        journal += [{"at": "2026-09-26T10:43:00Z", "stage": "calibrate", "note": "incomplete batch answer; asking the whole batch once more"},
                    {"at": "2026-09-26T10:43:30Z", "stage": "calibrate", "note": "the reviewer is not qualified today; no real package is reviewed"}]
    journal += [{"at": "2026-09-26T10:44:00Z", "stage": "calibrate", "note": "done"},
                {"at": "2026-09-26T11:40:00Z", "stage": "review", "note": "done"},
                {"at": "2026-09-26T11:52:00Z", "stage": "write", "note": "done"},
                {"at": "2026-09-26T11:52:10Z", "stage": "combine", "note": "done"},
                {"at": "2026-09-26T11:52:20Z", "stage": "bundle", "note": "done"}]
    if stop_at_publish:
        journal += [{"at": "2026-09-26T11:53:00Z", "stage": "publish", "note": "publish failed: Fly command timed out"}]
    elif published_by_hand:
        # The first slot of September 26: the publish failed, a person published and checked by hand without a
        # done note, and the job then wrote its counts.
        journal += [{"at": "2026-09-26T11:53:00Z", "stage": "publish", "note": "publish failed: boom"},
                    {"at": "2026-09-26T11:58:20Z", "stage": "counts", "note": "done"}]
    else:
        journal += [{"at": "2026-09-26T11:55:20Z", "stage": "publish", "note": "done"},
                    {"at": "2026-09-26T11:55:22Z", "stage": "check", "note": "done"},
                    {"at": "2026-09-26T11:55:22Z", "stage": "counts", "note": "done"}]
    _write_jsonl(folder / "journal.jsonl", _shift(journal, hours))
    calls = [_call("2026-09-26T10:56:00Z", 20.0), _call("2026-09-26T10:56:20Z", 30.0),
             _call("2026-09-26T10:56:50Z", 2.5, outcome="model_identity_mismatch")]
    _write_jsonl(folder / "ledger.jsonl", [{"record_type": "candidate_review_run/v2"}] + _shift(calls, hours))
    _write_jsonl(folder / "calibration-ledger.jsonl", _shift([_call("2026-09-26T10:43:10Z", 18.0, members=12)], hours))
    if stop_at_publish:
        # The job stopped at the publish: no counts, but the prechecks, review and writer records exist.
        (folder / "prechecks.json").write_text(json.dumps({"items": exported, "refused": exported - passed}),
                                               encoding="utf-8")
        (folder / "review.json").write_text(json.dumps({"totals": {"items": passed, "calls": 3}}), encoding="utf-8")
        reviewed = daily.parent / f"reviewed-{name}" / "imported"
        reviewed.mkdir(parents=True)
        (reviewed / "writer-report.json").write_text(json.dumps({
            "approved": approved, "rejected": 40, "left_out": ["x"] * 12}), encoding="utf-8")
        return folder
    (folder / "counts.json").write_text(json.dumps({
        "record_type": "daily_library_release_counts/v1", "day": name, "exported": exported, "passed_prechecks": passed,
        "reviewed": passed, "review_calls": 3, "approved": approved, "rejected": 40, "left_out": 12,
        "published": True, "checked_live": True}), encoding="utf-8")
    return folder


def make_export_report(batches: Path, name: str) -> None:
    folder = batches / name
    folder.mkdir(parents=True)
    (folder / "export-report.json").write_text(json.dumps({
        "record_type": "licensed_import_review_export/v1", "items": 2000, "written_at": "2026-09-26T10:17:23Z",
        "selection": {"already_exported": 6000, "stored_candidates": 58787, "per_repository": 15,
                      "not_selected": {"a_file_is_above_the_review_bound": 20, "a_file_is_not_reviewable_text": 2605,
                                       "repository_ceiling_reached": 13369}}}), encoding="utf-8")


class FactoryReportChecks(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="factory-report-", dir=os.environ.get("TMPDIR")))
        self.library = self.root / "library"
        make_slot(self.library / "daily", "2026-09-26-10")
        make_slot(self.library / "daily", "2026-09-26-04", with_failure=True)
        make_export_report(self.library / "review-batches", "2026-09-26-10")
        self.now = datetime(2026, 9, 26, 13, 0, tzinfo=timezone.utc)

    def test_stage_minutes_come_from_the_journal_markers(self):
        slot = factory_report.read_slot(self.library / "daily" / "2026-09-26-10")
        self.assertEqual(slot["stage_minutes"]["export"], 10.0)  # 10:17 scheduled start to 10:27
        self.assertEqual(slot["stage_minutes"]["prechecks"], 15.0)
        self.assertEqual(slot["stage_minutes"]["review"], 56.0)
        self.assertEqual(slot["stage_minutes"]["write"], 12.0)
        self.assertEqual(slot["wall_minutes"], 98.37)

    def test_review_split_and_waste(self):
        slot = factory_report.read_slot(self.library / "daily" / "2026-09-26-10")
        review = slot["review"]
        self.assertEqual(review["calls"], 3)
        self.assertEqual(review["busy_seconds"], 52.5)
        self.assertEqual(review["startup_minutes"], 12.0)  # calibrate done 10:44, first call 10:56
        self.assertEqual(review["unanswered_calls"], 1)
        self.assertEqual(review["items_in_unanswered_calls"], 12)
        self.assertEqual(slot["reviewer_busy_seconds"], 70.5)  # review calls plus the calibration call
        self.assertEqual(slot["per_approved"]["charged_tokens"], 120.0)

    def test_calibration_retries_and_restarts_are_counted(self):
        slot = factory_report.read_slot(self.library / "daily" / "2026-09-26-04")
        self.assertEqual(slot["calibration"]["retries"], 1)
        self.assertEqual(slot["calibration"]["not_qualified_verdicts"], 1)
        report = factory_report.build_report(library=self.library, overnight_batches=[], served=6398, now=self.now,
                                             cadence_hours=6.0, marks=(10_000,), allowance_usd_month=50.0)
        self.assertEqual(report["waste"]["slots_that_needed_a_restart"], 1)
        self.assertEqual(report["waste"]["calibration_retries"], 1)

    def test_projection_stops_at_the_stock(self):
        report = factory_report.build_report(library=self.library, overnight_batches=[], served=6398, now=self.now,
                                             cadence_hours=6.0, marks=(10_000, 100_000), allowance_usd_month=50.0)
        projection = report["projection"]
        self.assertEqual(projection["approved_per_day"], 6000.0)
        self.assertEqual(projection["yield_per_exported"], 0.75)
        self.assertEqual(report["stock"]["eligible_remaining"], 58787 - 8000 - 2625)
        marks = {row["mark"]: row for row in projection["marks"]}
        self.assertTrue(marks[10_000]["reachable_from_current_stock"])
        self.assertEqual(marks[10_000]["date_at_current_rate"], "2026-09-27")  # 0.6 days after 13:00
        self.assertFalse(marks[100_000]["reachable_from_current_stock"])
        self.assertGreater(marks[100_000]["candidates_needed_beyond_stock"], 0)
        self.assertEqual(report["cost_per_admitted_package"]["model_cost_usd"], "unmetered")
        self.assertEqual(report["review_lane"]["utilization_of_cadence"], round(70.5 / (6 * 3600), 3))

    def test_an_unfinished_newest_slot_is_not_lost_but_an_abandoned_one_is(self):
        # Known-wrong case: the slot that is still running was reported as lost with its approvals.
        running = self.library / "daily" / "2026-09-26-16"
        running.mkdir(parents=True)
        _write_jsonl(running / "journal.jsonl", [
            {"at": "2026-09-26T16:17:25Z", "stage": "export", "note": "export failed: boom"},
            {"at": "2026-09-26T16:29:21Z", "stage": "export", "note": "done"}])
        report = factory_report.build_report(library=self.library, overnight_batches=[], served=6398, now=self.now,
                                             cadence_hours=6.0, marks=(10_000,), allowance_usd_month=50.0)
        self.assertEqual(report["waste"]["slots_lost"], [])
        self.assertEqual(report["waste"]["approvals_lost_with_them"], 0)
        self.assertEqual(report["waste"]["unfinished_slots"], ["2026-09-26-16"])
        later = self.library / "daily" / "2026-09-26-22"
        later.mkdir(parents=True)
        report = factory_report.build_report(library=self.library, overnight_batches=[], served=6398, now=self.now,
                                             cadence_hours=6.0, marks=(10_000,), allowance_usd_month=50.0)
        self.assertEqual([row["slot"] for row in report["waste"]["slots_lost"]], ["2026-09-26-16"])
        self.assertEqual(report["waste"]["unfinished_slots"], ["2026-09-26-22"])

    def test_the_first_run_replaces_the_schedule_and_records_a_late_start(self):
        # Known-wrong case: a folder time later than the slot's first journal event is not its first run, and
        # would give a negative export time; it is refused and the schedule is used instead.
        too_late = datetime(2026, 9, 26, 10, 38, 23, tzinfo=timezone.utc)
        slot = factory_report.read_slot(self.library / "daily" / "2026-09-26-10", started_at=too_late)
        self.assertEqual(slot["first_run_refused"], too_late.isoformat())
        self.assertIsNone(slot["late_start_minutes"])
        self.assertEqual(slot["stage_minutes"]["export"], 10.0)
        report = factory_report.build_report(
            library=self.library, overnight_batches=[], served=6398, now=self.now, cadence_hours=6.0, marks=(10_000,),
            allowance_usd_month=50.0,
            started=lambda name: datetime(2026, 9, 26, 10, 17, 1, tzinfo=timezone.utc) if name == "2026-09-26-10" else None)
        ten = [row for row in report["slots"] if row["slot"] == "2026-09-26-10"][0]
        self.assertEqual(ten["stage_minutes"]["export"], 9.98)
        self.assertEqual(ten["late_start_minutes"], 0.02)

    def test_calibration_attempts_moved_aside_count_as_reviewer_time(self):
        folder = self.library / "daily" / "2026-09-26-04"
        (folder / "attempt-1").mkdir()
        _write_jsonl(folder / "attempt-1" / "calibration-ledger.jsonl", [_call("2026-09-26T10:42:10Z", 15.0)])
        slot = factory_report.read_slot(folder)
        self.assertEqual(slot["calibration"]["attempts_moved_aside"], 1)
        self.assertEqual(slot["calibration"]["moved_aside_busy_seconds"], 15.0)
        self.assertEqual(slot["reviewer_busy_seconds"], 85.5)

    def test_the_projection_names_the_serving_capacity(self):
        report = factory_report.build_report(library=self.library, overnight_batches=[], served=6398, now=self.now,
                                             cadence_hours=6.0, marks=(10_000, 30_000), allowance_usd_month=50.0,
                                             serving_capacity=25_000)
        projection = report["projection"]
        self.assertEqual(projection["serving_capacity"], 25_000)
        self.assertEqual(projection["days_until_serving_capacity"], round((25_000 - 6398) / 6000.0, 1))
        marks = {row["mark"]: row for row in projection["marks"]}
        self.assertTrue(marks[10_000]["within_serving_capacity"])
        self.assertFalse(marks[30_000]["within_serving_capacity"])
        self.assertEqual(report["cost_per_admitted_package"]["stage_seconds_per_approved"]["review"],
                         round(56.0 * 60.0 / 1500, 3))

    def test_a_gap_without_stage_notes_is_not_given_to_the_next_stage(self):
        # Known-wrong case: the counts stage was given the minutes a person spent publishing and checking by hand.
        make_slot(self.library / "daily", "2026-09-26", published_by_hand=True)
        slot = factory_report.read_slot(self.library / "daily" / "2026-09-26")
        self.assertIsNone(slot["stage_minutes"]["publish"])
        self.assertIsNone(slot["stage_minutes"]["check"])
        self.assertIsNone(slot["stage_minutes"]["counts"])
        self.assertEqual(slot["unattributed_gaps"], [{"stages": ["publish", "check", "counts"], "minutes": 6.0}])
        self.assertEqual(slot["stage_minutes"]["bundle"], 0.17)
        report = factory_report.build_report(library=self.library, overnight_batches=[], served=6398, now=self.now,
                                             cadence_hours=6.0, marks=(10_000,), allowance_usd_month=50.0)
        self.assertEqual(report["stage_minutes_mean"]["counts"], 0.0)  # the two slots with notes, not 6.0 minutes
        self.assertEqual(report["waste"]["minutes_without_a_stage_note"], 6.0)
        self.assertIn("publish+check+counts 6.0", factory_report.render_table(report))

    def test_a_restarted_stage_is_kept_out_of_the_means(self):
        # Known-wrong case: the minutes a person spent repairing a failed export entered the mean that plans a
        # clean slot.
        folder = make_slot(self.library / "daily", "2026-09-26-16", restarted_export=True)
        journal = (folder / "journal.jsonl").read_text(encoding="utf-8").replace("16:27:00", "16:40:00")
        (folder / "journal.jsonl").write_text(journal, encoding="utf-8")
        slot = factory_report.read_slot(folder)
        self.assertEqual(slot["restarted_stages"], ["export"])
        self.assertEqual(slot["stage_minutes"]["export"], 23.0)
        self.assertEqual(slot["minutes_in_restarted_stages"], 23.0)
        report = factory_report.build_report(library=self.library, overnight_batches=[], served=6398, now=self.now,
                                             cadence_hours=6.0, marks=(10_000,), allowance_usd_month=50.0)
        self.assertEqual(report["recent_slots"], ["2026-09-26-04", "2026-09-26-10", "2026-09-26-16"])
        self.assertEqual(report["stage_minutes_mean"]["export"], 10.0)  # not 14.3 with the repair inside
        clean = sum(value for value in report["stage_minutes_mean"].values() if value)
        back_to_back = report["projection"]["if_slots_ran_back_to_back"]
        self.assertEqual(back_to_back["slot_minutes"], round(clean, 1))
        self.assertAlmostEqual(back_to_back["slots_per_day"], 24.0 * 60.0 / clean)
        self.assertGreater(report["projection"]["if_slots_ran_back_to_back_with_the_observed_walls"]["slot_minutes"],
                           back_to_back["slot_minutes"])  # the observed walls hold the restart
        self.assertEqual(report["waste"]["minutes_in_restarted_stages"], 25.0)  # 23.0 export, 2.0 calibration at 04
        self.assertIn("23.0 restarted", factory_report.render_table(report))

    def test_a_slot_stopped_at_the_publish_counts_its_written_approvals(self):
        # Known-wrong case: a slot whose publish failed after its reviewed folder was written was left out of the
        # rates and reported lost once a later slot started, though the next slot's combine carries its folder.
        make_slot(self.library / "daily", "2026-09-26-16", approved=1408, passed=1529, stop_at_publish=True)
        (self.library / "daily" / "2026-09-26-22").mkdir(parents=True)
        report = factory_report.build_report(library=self.library, overnight_batches=[], served=6398, now=self.now,
                                             cadence_hours=6.0, marks=(10_000,), allowance_usd_month=50.0)
        sixteen = [row for row in report["slots"] if row["slot"] == "2026-09-26-16"][0]
        self.assertEqual(sixteen["status"], "written_not_published")
        self.assertEqual(sixteen["counts"]["approved"], 1408)
        self.assertEqual(sixteen["counts"]["reviewed"], 1529)
        self.assertFalse(sixteen["counts"]["published"])
        self.assertEqual(sixteen["stop"]["last_stage"], "publish")
        self.assertEqual(report["waste"]["slots_lost"], [])
        self.assertEqual(report["waste"]["written_not_published_slots"], ["2026-09-26-16"])
        self.assertEqual(report["waste"]["unfinished_slots"], ["2026-09-26-22"])
        self.assertEqual(report["projection"]["yield_per_exported"], round((1500 + 1500 + 1408) / 6000, 3))
        self.assertIn("1408 written_not_published: publish failed", factory_report.render_table(report))
        # The written approvals are part of the base: the marks are nearer by 1,408, not as far as the live count.
        self.assertEqual(report["projection"]["written_not_published"], 1408)
        marks = {row["mark"]: row for row in report["projection"]["marks"]}
        self.assertEqual(marks[10_000]["packages_short"], 10_000 - 6398 - 1408)

    def test_review_lanes_come_from_the_ledger(self):
        # Known-wrong case: a fixed reviewer name; the lane and its family are what the ledger says answered.
        folder = self.library / "daily" / "2026-09-26-10"
        with (folder / "ledger.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(_call("2026-09-26T10:57:00Z", 10.0, members=6, installation="codex.reviewer-b",
                                          family="openai")) + "\n")
        report = factory_report.build_report(library=self.library, overnight_batches=[], served=6398, now=self.now,
                                             cadence_hours=6.0, marks=(10_000,), allowance_usd_month=50.0)
        lanes = report["review_lanes"]
        self.assertEqual(sorted(lanes), ["codex.reviewer-b", "tactical.reviewer-a"])
        self.assertEqual(lanes["codex.reviewer-b"], {"family": "openai", "calls": 1, "items": 6, "busy_seconds": 10.0,
                                                     "unanswered_calls": 0, "items_per_busy_hour": 2160.0,
                                                     "mean_call_seconds": 10.0})
        self.assertEqual(lanes["tactical.reviewer-a"]["calls"], 6)  # three calls in each of the two slots
        self.assertEqual(lanes["tactical.reviewer-a"]["unanswered_calls"], 2)
        self.assertEqual(report["review_lane"]["reviewer"], "codex.reviewer-b, tactical.reviewer-a")

    def test_cron_and_queued_slot_names_give_their_scheduled_start(self):
        self.assertEqual(factory_report.slot_start("2026-09-26-16", 17), datetime(2026, 9, 26, 16, 17, tzinfo=timezone.utc))
        self.assertEqual(factory_report.slot_start("2026-09-26-18-30", 17), datetime(2026, 9, 26, 18, 30, tzinfo=timezone.utc))
        self.assertIsNone(factory_report.slot_start("2026-09-26", 17))
        self.assertIsNone(factory_report.slot_start("2026-09-26-16.failed-export-1", 17))

    def test_a_library_without_counts_is_refused(self):
        empty = self.root / "empty"
        (empty / "daily" / "2026-09-27-04").mkdir(parents=True)
        with self.assertRaises(factory_report.FactoryReportError):
            factory_report.build_report(library=empty, overnight_batches=[], served=0, now=self.now, cadence_hours=6.0,
                                        marks=(10_000,), allowance_usd_month=50.0)

    def test_generation_lane_throughput_from_the_batch_journal(self):
        batch = self.root / "batch"
        batch.mkdir()
        (batch / "status.json").write_text(json.dumps({"state": "complete", "ideas_total": 3, "candidates": 2,
                                                       "failed": 1, "calls_used": 4}), encoding="utf-8")
        _write_jsonl(batch / "journal.jsonl", [
            {"event": "dispatch", "idea_id": "a", "lane_id": "lane-x", "ts": "2026-09-26T01:00:00Z"},
            {"event": "outcome", "idea_id": "a", "lane_id": "lane-x", "outcome": "candidate_written", "ts": "2026-09-26T01:00:06Z"},
            {"event": "dispatch", "idea_id": "b", "lane_id": "lane-x", "ts": "2026-09-26T01:00:07Z"},
            {"event": "outage_wait", "idea_id": "b", "lane_id": "lane-x", "seconds": 60, "ts": "2026-09-26T01:00:10Z"},
            {"event": "dispatch", "idea_id": "b", "lane_id": "lane-x", "ts": "2026-09-26T01:01:10Z"},
            {"event": "outcome", "idea_id": "b", "lane_id": "lane-x", "outcome": "candidate_written", "ts": "2026-09-26T01:01:16Z"},
            {"event": "dispatch", "idea_id": "c", "lane_id": "lane-x", "ts": "2026-09-26T02:00:00Z"},
            {"event": "outcome", "idea_id": "c", "lane_id": "lane-x", "outcome": "failed_candidate_shape", "ts": "2026-09-26T02:00:04Z"}])
        lanes = factory_report.read_generation_lanes(batch)["lanes"]
        self.assertEqual(lanes["lane-x"]["candidates"], 2)
        self.assertEqual(lanes["lane-x"]["retries"], 1)
        self.assertEqual(lanes["lane-x"]["outage_waits"], 1)
        self.assertEqual(lanes["lane-x"]["candidates_per_active_hour"], 1.0)
        self.assertEqual(lanes["lane-x"]["median_attempt_seconds"], 6.0)

    def test_main_writes_the_dated_record_and_table(self):
        out = self.root / "out"
        code = factory_report.main(["--library", str(self.library), "--served", "6398", "--now", "2026-09-26T13:00:00Z",
                                    "--job-temp-root", str(self.root / "no-temporary-folders"), "--output", str(out)])
        self.assertEqual(code, 0)
        record = json.loads((out / "factory-report-2026-09-26T130000Z.json").read_text(encoding="utf-8"))
        self.assertEqual(record["record_type"], "factory_report/v1")
        table = (out / "factory-report-2026-09-26T130000Z.md").read_text(encoding="utf-8")
        self.assertIn("| 2026-09-26-10 |", table)
        self.assertIn("Reachable from the current stock", table)


if __name__ == "__main__":
    unittest.main()
