"""Mutant controls for tools/factory_report.py and tools/factory_schedule.py: remove each guard, run its named check.

Each mutant copies the two tools and their checks into a scratch folder, replaces one guard's line (the text
must occur exactly once), and runs the check named for it; the check must fail. The unmutated copies must
pass every named check. Scratch folders go under TMPDIR.

    TMPDIR=SCRATCH python artifacts/factory-economics-2026-09-26/factory_mutants.py
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

TREE = str(Path(__file__).resolve().parents[2] / "tools")
PY = sys.executable
MUTANTS = [
    ("factory_schedule.py", "                if attempts < calibration_attempts:\n", "                if True:\n",
     "test_factory_schedule.RunChecks.test_calibration_re_runs_stop_at_the_bound"),
    ("factory_schedule.py", "        target = min(target_max, left)\n", "        target = target_max\n",
     "test_factory_schedule.PlanChecks.test_plan_never_draws_more_than_the_stock"),
    ("factory_schedule.py", "        if serving_capacity is not None and serving + approved > serving_capacity:\n",
     "        if False:\n", "test_factory_schedule.PlanChecks.test_plan_stops_at_the_serving_capacity"),
    ("factory_schedule.py", "                    moved = move_calibration_aside(library, row[\"slot\"])\n",
     "                    moved = {\"folder\": None, \"moved\": []}\n",
     "test_factory_schedule.RunChecks.test_a_calibration_stop_is_re_run_after_moving_the_attempt_aside"),
    ("factory_schedule.py", "        others = foreign_jobs()\n", "        others = []\n",
     "test_factory_schedule.RunChecks.test_a_foreign_daily_job_stops_the_queue"),
    ("factory_schedule.py", "    if record.get(\"serving_capacity\") is None and not dry_run:\n", "    if False:\n",
     "test_factory_schedule.RunChecks.test_a_zero_attempt_bound_and_a_missing_capacity_are_refused"),
    ("factory_schedule.py", "        if capacity is not None and served + int(target * rate) > capacity:\n", "        if False:\n",
     "test_factory_schedule.RunChecks.test_actual_counts_stop_the_queue_at_the_serving_capacity"),
    ("factory_schedule.py", "        served += approved\n", "        pass\n",
     "test_factory_schedule.RunChecks.test_actual_counts_shrink_the_next_export"),
    ("factory_report.py", "    for slot in slots[:-1]:\n", "    for slot in slots:\n",
     "test_factory_report.FactoryReportChecks.test_an_unfinished_newest_slot_is_not_lost_but_an_abandoned_one_is"),
    ("factory_report.py", "    if started_at and journal and started_at > _parse(journal[0][\"at\"]):\n", "    if False:\n",
     "test_factory_report.FactoryReportChecks.test_the_first_run_replaces_the_schedule_and_records_a_late_start"),
    ("factory_report.py",
     "    reviewer_busy = busy + calibration[\"busy_seconds\"] + calibration[\"moved_aside_busy_seconds\"]\n",
     "    reviewer_busy = busy + calibration[\"busy_seconds\"]\n",
     "test_factory_report.FactoryReportChecks.test_calibration_attempts_moved_aside_count_as_reviewer_time"),
    ("factory_report.py", "        if previous is not None and missing:\n", "        if False:\n",
     "test_factory_report.FactoryReportChecks.test_a_gap_without_stage_notes_is_not_given_to_the_next_stage"),
    ("factory_report.py", "    review_lane = {\"reviewer\": \", \".join(sorted(review_lanes)) or None,\n",
     "    review_lane = {\"reviewer\": \"tactical.gemma-4-coding-abliterated\",\n",
     "test_factory_report.FactoryReportChecks.test_review_lanes_come_from_the_ledger"),
    ("factory_schedule.py",
     "    return (bool(notes) and notes[-1].get(\"stage\") == \"calibrate\" and NOT_QUALIFIED in notes[-1].get(\"note\", \"\")\n",
     "    return (bool(notes) and NOT_QUALIFIED in ([n for n in notes if n.get(\"stage\") == \"calibrate\"] or [{}])[-1].get(\"note\", \"\")\n",
     "test_factory_schedule.RunChecks.test_an_older_calibration_verdict_before_another_failure_is_not_re_run"),
    ("factory_schedule.py", "    if not publish and len(record[\"slots\"]) > 1:\n", "    if False:\n",
     "test_factory_schedule.RunChecks.test_a_queue_without_publish_runs_one_slot_at_a_time"),
    ("factory_report.py",
     "    stage_means = {stage: _mean([slot[\"stage_minutes\"][stage] for slot in recent if stage not in slot[\"restarted_stages\"]])\n",
     "    stage_means = {stage: _mean([slot[\"stage_minutes\"][stage] for slot in recent])\n",
     "test_factory_report.FactoryReportChecks.test_a_restarted_stage_is_kept_out_of_the_means"),
    ("factory_report.py", "        counts, status = written_counts(folder, done_at), WRITTEN_NOT_PUBLISHED\n",
     "        counts, status = None, WRITTEN_NOT_PUBLISHED\n",
     "test_factory_report.FactoryReportChecks.test_a_slot_stopped_at_the_publish_counts_its_written_approvals"),
    ("factory_report.py", "    base = served + written\n", "    base = served\n",
     "test_factory_report.FactoryReportChecks.test_a_slot_stopped_at_the_publish_counts_its_written_approvals"),
]


def main() -> int:
    scratch = os.environ.get("TMPDIR") or tempfile.gettempdir()
    failures = 0
    for index, (name, old, new, check) in enumerate(MUTANTS, 1):
        folder = tempfile.mkdtemp(prefix=f"mutant-{index}-", dir=scratch)
        for base in ("factory_report.py", "factory_schedule.py", "test_factory_report.py", "test_factory_schedule.py"):
            shutil.copy(os.path.join(TREE, base), os.path.join(folder, base))
        path = os.path.join(folder, name)
        text = open(path, encoding="utf-8").read()
        if text.count(old) != 1:
            print(f"mutant {index}: the guard text is not unique ({text.count(old)}) in {name}")
            failures += 1
            continue
        open(path, "w", encoding="utf-8").write(text.replace(old, new))
        completed = subprocess.run([PY, "-m", "unittest", check], cwd=folder, capture_output=True, text=True,
                                   timeout=120, env={**os.environ, "PYTHONPATH": folder})
        killed = completed.returncode != 0
        print(f"mutant {index} {name}: {'killed' if killed else 'SURVIVED'} by {check.split('.')[-1]}")
        failures += 0 if killed else 1
    # The unmutated copies must pass the same checks.
    folder = tempfile.mkdtemp(prefix="mutant-0-", dir=scratch)
    for base in ("factory_report.py", "factory_schedule.py", "test_factory_report.py", "test_factory_schedule.py"):
        shutil.copy(os.path.join(TREE, base), os.path.join(folder, base))
    completed = subprocess.run([PY, "-m", "unittest", *[m[3] for m in MUTANTS]], cwd=folder, capture_output=True,
                               text=True, timeout=300, env={**os.environ, "PYTHONPATH": folder})
    print("unmutated:", "pass" if completed.returncode == 0 else "FAIL", completed.stderr.strip().splitlines()[-1])
    return 1 if failures or completed.returncode else 0


if __name__ == "__main__":
    sys.exit(main())
