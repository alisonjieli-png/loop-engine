"""Checks of the 3D with-and-without runner that need no network, no model and no 3D libraries.

Each rule has a known-wrong control: the interval must not collapse to zero at zero successes, a run that would end
inside a daily slot must wait, the runner must not count itself as a busy process, a package path that leaves its
folder and a byte changed after staging must be refused, unknown token usage must stay unknown, and the two
conditions must differ by the Baltor note only.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "showcase_3d"))
import rerun  # noqa: E402
import tasks  # noqa: E402

SHARING = rerun.Sharing(("04:17", "10:17", "16:17", "22:17"), 90, 5, ("daily_library_release", "candidate_review"), 60)


def at(hour: int, minute: int, day: int = 28) -> datetime:
    return datetime(2026, 9, day, hour, minute, tzinfo=timezone.utc)


class Intervals(unittest.TestCase):
    def test_wilson_matches_published_values(self):
        low, high = rerun.wilson(2, 5)
        self.assertAlmostEqual(low, 0.1176, places=3)
        self.assertAlmostEqual(high, 0.7693, places=3)
        self.assertAlmostEqual(rerun.wilson(5, 5)[0], 0.5655, places=3)

    def test_zero_successes_do_not_collapse_to_zero(self):
        # Known-wrong control: the normal approximation gives 0 to 0 for 0 of 5.
        self.assertAlmostEqual(rerun.wilson(0, 5)[1], 0.4345, places=3)
        self.assertEqual(rerun.wilson(0, 0), (0.0, 1.0))

    def test_newcombe_difference(self):
        d, low, high = rerun.newcombe(5, 5, 0, 5)
        self.assertEqual(d, 1.0)
        self.assertAlmostEqual(low, 0.3855, places=3)
        self.assertAlmostEqual(high, 1.0, places=6)


class ModelServerSharing(unittest.TestCase):
    def test_a_run_that_would_reach_a_slot_waits(self):
        self.assertEqual(rerun.slot_conflict(at(3, 50), 1200, SHARING), "")
        # Known-wrong control: a check that ignores the run's own budget would start at 03:55 and run into 04:17.
        self.assertIn("04:17", rerun.slot_conflict(at(3, 55), 1200, SHARING))

    def test_inside_and_after_a_slot(self):
        self.assertIn("04:17", rerun.slot_conflict(at(4, 30), 1200, SHARING))
        self.assertEqual(rerun.slot_conflict(at(5, 48), 1200, SHARING), "")
        self.assertIn("22:17", rerun.slot_conflict(at(23, 30, 27), 1200, SHARING))
        self.assertEqual(rerun.slot_conflict(at(23, 50, 27), 1200, SHARING), "")

    def test_busy_processes_exclude_the_runner(self):
        listing = "\n".join(["123 bash /opt/daily_library_release.sh 2026-09-28-04 --publish",
                             "456 python tools/showcase_3d/rerun.py run --config c.json candidate_review",
                             "789 vim notes.md", "1000 python -m tools.candidate_review.panel"])
        found = rerun.busy_lines(listing, SHARING.busy_patterns, own_pids={1000})
        self.assertEqual([line.split()[0] for line in found], ["123"])


class Placement(unittest.TestCase):
    def test_paths_that_leave_the_folder_are_refused(self):
        for bad in ("../x.md", "/etc/passwd", "a/../b.md", "a\\b.md", ""):
            with self.assertRaises(ValueError, msg=bad):
                rerun.safe_relative(bad)
        self.assertEqual(str(rerun.safe_relative("references/a.md")), "references/a.md")

    def test_folder_name_comes_from_the_skill_when_valid(self):
        self.assertEqual(rerun.skill_folder_name("---\nname: cad\ndescription: x\n---\nbody", "import_skill_cad_1"), "cad")
        self.assertEqual(rerun.skill_folder_name("---\nname: CAD Skill\n---\n", "import_skill_cad_1"), "import-skill-cad-1")
        self.assertEqual(rerun.skill_folder_name("no frontmatter", "Odd__Name"), "odd-name")

    def staged(self, root: Path, files: dict) -> dict:
        receipt = {"identity": "import_skill_demo", "files": []}
        for path, text in files.items():
            target = root / "payload" / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)
            receipt["files"].append({"path": path, "digest": hashlib.sha256(text.encode()).hexdigest()})
        return receipt

    def test_a_package_is_placed_whole_and_checked(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            receipt = self.staged(root / "stage", {"SKILL.md": "---\nname: demo\n---\n", "references/r.md": "ref"})
            placed = rerun.place_staged(root / "stage", receipt, root / "project" / ".opencode" / "skills", set())
            self.assertEqual(placed["skill_folder"], ".opencode/skills/demo")
            self.assertEqual(sorted(f["path"] for f in placed["files"]),
                             [".opencode/skills/demo/SKILL.md", ".opencode/skills/demo/references/r.md"])

    def test_a_byte_changed_after_staging_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            receipt = self.staged(root / "stage", {"SKILL.md": "---\nname: demo\n---\n"})
            (root / "stage" / "payload" / "SKILL.md").write_text("---\nname: demo\n---\nchanged")
            with self.assertRaises(ValueError):
                rerun.place_staged(root / "stage", receipt, root / "project" / ".opencode" / "skills", set())


def processes_under(folder: Path) -> list[int]:
    found = []
    for entry in Path("/proc").iterdir():
        if entry.name.isdigit():
            try:
                if os.readlink(entry / "cwd").startswith(str(folder.resolve())):
                    found.append(int(entry.name))
            except OSError:
                pass
    return found


@unittest.skipUnless(shutil.which("setsid") and Path("/proc").is_dir(), "needs setsid and /proc")
class TimeBudget(unittest.TestCase):
    """A harness must not outlive its time budget, including commands it started in their own sessions."""

    command = "setsid sleep 120 & sleep 120"

    def test_the_budget_ends_every_process_of_the_run(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            started = time.time()
            exit_code, _, _, timed_out, _ = rerun.run_bounded(["bash", "-c", self.command], 2, dict(os.environ), root, root)
            self.assertTrue(timed_out)
            self.assertIsNone(exit_code)
            self.assertLess(time.time() - started, 40)
            time.sleep(0.5)
            self.assertEqual(processes_under(root), [])

    def test_a_group_kill_alone_leaves_a_process_behind(self):
        # Known-wrong control: without the sweep, the command in its own session survives the group kill.
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            process = subprocess.Popen(["bash", "-c", self.command], cwd=root, start_new_session=True)
            time.sleep(0.5)
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            time.sleep(0.5)
            survivors = processes_under(root)
            for pid in survivors:
                os.kill(pid, signal.SIGKILL)
            self.assertTrue(survivors)


class Records(unittest.TestCase):
    def test_unknown_usage_stays_unknown(self):
        known = [{"outcome": "ok", "prompt_tokens": 10, "completion_tokens": 2}]
        self.assertEqual(rerun.token_totals(known)["prompt_tokens"], 10)
        unknown = known + [{"outcome": "upstream_error", "prompt_tokens": None, "completion_tokens": None}]
        totals = rerun.token_totals(unknown)
        self.assertIsNone(totals["prompt_tokens"])
        self.assertEqual(totals["calls_with_unknown_usage"], 1)
        self.assertEqual(rerun.token_totals([{"outcome": "refused"}])["prompt_tokens"], 0)

    def test_the_schedule_pairs_both_conditions(self):
        config = {"runs_per_cell": 5, "seed": 7, "pairs_in_parallel": 2}
        schedule = rerun.plan(config, "rerun", None, None)
        runs = [run for batch in schedule["batches"] for pair in batch for run in pair["runs"]]
        self.assertEqual(len(runs), 50)
        self.assertEqual(len(set(runs)), 50)
        for batch in schedule["batches"]:
            for pair in batch:
                self.assertEqual([r.rsplit("-", 1)[-1] for r in pair["runs"]], ["without_baltor", "with_baltor"])
        self.assertEqual(schedule["digest"], rerun.plan(config, "rerun", None, None)["digest"])

    def test_conditions_differ_by_the_note_only(self):
        for task in tasks.TASKS:
            with_note, without = tasks.prompt_for(task, "with_baltor"), tasks.prompt_for(task, "without_baltor")
            self.assertEqual(with_note, tasks.BALTOR_NOTE + without)
        with self.assertRaises(ValueError):
            tasks.prompt_for("t1_gear", "with_baltor_protocol")

    def test_every_check_has_one_definition_and_digest(self):
        records = tasks.check_definition_records()
        keys = [(r["task"], r["check"]) for r in records]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertTrue(all(len(r["digest"]) == 64 for r in records))
        self.assertIn(("t1_gear", "tooth_thickness"), keys)
        json.dumps(records)


if __name__ == "__main__":
    unittest.main()
