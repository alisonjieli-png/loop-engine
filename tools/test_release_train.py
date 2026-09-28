"""A release train picks with -x, resolves only what a rule can resolve, regenerates last, and never pushes.

tools/release_train.py builds a train in a given worktree. These rules run it on scratch repositories, each with a
bare origin, a small generated view (out/upper.txt, the upper case of a.txt and b.txt) behind a fake
tools/regenerate_all.py, and a fake tools/pre_push_check.sh, and hold it to its promises: clean picks carry the -x
line and are followed by one "Regenerate generated views" commit; a conflict in a generated file takes the train's
side and is regenerated; two appends to the same YAML list are kept, the train's first; the shard manifest takes its
version 2 side; any other conflict stops the train and names the file; a failed gate is not ready; and no git command
the train runs is a push, while the origin stays where it was. Each known-wrong case is one the integrator met by
hand on September 27, 2026.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import release_train as train  # noqa: E402

SCRIPT = ROOT / "tools" / "release_train.py"
IDENTITY = {"GIT_AUTHOR_NAME": "Train test", "GIT_AUTHOR_EMAIL": "train@example.invalid",
            "GIT_COMMITTER_NAME": "Train test", "GIT_COMMITTER_EMAIL": "train@example.invalid",
            "GIT_CONFIG_NOSYSTEM": "1"}
FAKE_REGENERATE = '''\
"""A one-view registry: out/upper.txt is the upper case of a.txt followed by b.txt."""
import argparse, pathlib, subprocess, sys, tempfile

OUTPUTS = ["out/upper.txt"]


def build(root):
    text = (root / "a.txt").read_text() + (root / "b.txt").read_text()
    (root / "out").mkdir(exist_ok=True)
    (root / "out" / "upper.txt").write_text(text.upper())


parser = argparse.ArgumentParser()
parser.add_argument("--root", type=pathlib.Path, default=pathlib.Path("."))
parser.add_argument("--outputs", action="store_true")
parser.add_argument("--pristine", action="store_true")
parser.add_argument("--skip", default="")
arguments = parser.parse_args()
root = arguments.root.resolve()
if arguments.outputs:
    print("\\n".join(OUTPUTS))
    sys.exit(0)
if arguments.pristine:
    with tempfile.TemporaryDirectory() as folder:
        archive = subprocess.run(["git", "-C", str(root), "archive", "--format=tar", "HEAD"], capture_output=True,
                                 check=True)
        subprocess.run(["tar", "-x", "-C", folder], input=archive.stdout, check=True)
        export = pathlib.Path(folder)
        committed = (export / "out" / "upper.txt").read_text()
        build(export)
        sys.exit(0 if (export / "out" / "upper.txt").read_text() == committed else 1)
build(root)
'''
FAKE_GATES = '''\
#!/usr/bin/env bash
echo "Pre-push check of the scratch train"
echo "  pass      1s  scratch-gate"
code="${FAKE_GATES_EXIT:-0}"
if [ "$code" = 0 ]; then verdict="all 1 gates passed"; else verdict="1 of 1 gates FAILED"; fi
echo "RESULT: $verdict; NOT EQUIVALENT TO CI (0 skipped in this run, 1 only in continuous integration; listed above)"
exit "$code"
'''
ALLOWLIST = """\
version: 1
entries:
  - finding_id: f1
    path: src/a.py
  - finding_id: f2
    path: src/b.py
"""
MANIFEST_V1 = {"record_type": "tools_test_shard_manifest/v1", "shards": {"a": ["test_one"], "b": ["test_two"]},
               "measured_seconds": {"a": 1.0, "b": 1.0}}
MANIFEST_V2 = {"record_type": "tools_test_shard_manifest/v2", "version": 2, "shards": ["a", "b"],
               "timings": "artifacts/ci-speed-*/module-times-*.json"}
#: A git that records every command it is asked to run, then runs the real one.
GIT_RECORDER = '''\
#!/bin/sh
printf '%s\\n' "$*" >> "{log}"
exec "{git}" "$@"
'''


def dump(data) -> str:
    return json.dumps(data, indent=1) + "\n"


class TrainCase(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory(prefix="release-train-")
        self.addCleanup(holder.cleanup)
        self.home = Path(holder.name)
        self.environment = {**os.environ, **IDENTITY}
        self.origin = self.home / "origin.git"
        self.run_git(self.home, "init", "-q", "--bare", "-b", "main", str(self.origin))
        self.worktree = self.home / "train"
        self.run_git(self.home, "clone", "-q", str(self.origin), str(self.worktree))
        files = {"a.txt": "alpha\n", "b.txt": "beta\n", "out/upper.txt": "ALPHA\nBETA\n", "notes.txt": "one\n",
                 "devtools/allow.yaml": ALLOWLIST, "tools/ci_test_shards.json": dump(MANIFEST_V1),
                 "tools/regenerate_all.py": FAKE_REGENERATE, "tools/pre_push_check.sh": FAKE_GATES}
        self.base = self.commit(files, "The scratch base", parent=None)
        self.run_git(self.worktree, "push", "-q", "origin", f"{self.base}:refs/heads/main")
        self.run_git(self.worktree, "fetch", "-q", "origin")
        self.run_git(self.worktree, "checkout", "-q", "--detach", self.base)
        self.origin_main = self.origin_head()
        # Every git command of the train goes through a recorder, so a push would be seen.
        self.recorded = self.home / "git-commands.txt"
        recorder = self.home / "recorder"
        recorder.mkdir()
        real_git = subprocess.run(["sh", "-c", "command -v git"], capture_output=True, text=True, check=True)
        (recorder / "git").write_text(GIT_RECORDER.format(log=self.recorded, git=real_git.stdout.strip()))
        (recorder / "git").chmod(0o755)
        self.train_environment = {**self.environment, "PATH": f"{recorder}{os.pathsep}{os.environ['PATH']}"}
        self.train_environment.pop("PY", None)

    def run_git(self, where: Path, *args) -> str:
        return subprocess.run(["git", "-C", str(where), *args], capture_output=True, text=True, check=True,
                              env=self.environment).stdout

    def origin_head(self) -> str:
        return self.run_git(self.origin, "rev-parse", "refs/heads/main").strip()

    def commit(self, files: dict, message: str, parent) -> str:
        """A commit of these file contents on parent (None for a first commit); HEAD is left detached on it."""
        if parent:
            self.run_git(self.worktree, "checkout", "-q", "--detach", parent)
        for name, text in files.items():
            path = self.worktree / name
            if text is None:
                self.run_git(self.worktree, "rm", "-q", name)
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            self.run_git(self.worktree, "add", name)
        self.run_git(self.worktree, "commit", "-q", "-m", message)
        return self.run_git(self.worktree, "rev-parse", "HEAD").strip()

    def start_train_at(self, revision: str) -> None:
        self.run_git(self.worktree, "checkout", "-q", "--detach", revision)

    def run_train(self, *commits, gates_exit=None, extra=("--skip-gates",)):
        environment = dict(self.train_environment)
        if gates_exit is not None:
            environment["FAKE_GATES_EXIT"] = str(gates_exit)
        completed = subprocess.run([sys.executable, str(SCRIPT), "--worktree", str(self.worktree), *extra,
                                    "--trailer", "Co-Authored-By: Train test <train@example.invalid>", *commits],
                                   capture_output=True, text=True, env=environment, check=False, timeout=120)
        return completed.returncode, completed.stdout + completed.stderr

    def messages(self, count: int) -> list:
        return self.run_git(self.worktree, "log", f"-{count}", "--format=%B%x00").split("\0")[:count]

    def assertNeverPushed(self):
        commands = self.recorded.read_text().splitlines() if self.recorded.exists() else []
        self.assertTrue(commands, "the recorder saw no git command")
        pushes = [line for line in commands if " push" in f" {line}" and "push" in line.split()]
        self.assertEqual(pushes, [])
        self.assertEqual(self.origin_head(), self.origin_main)


class PickTests(TrainCase):
    def test_clean_picks_carry_the_x_line_and_one_regeneration_commit_follows(self):
        first = self.commit({"a.txt": "alpha two\n"}, "Change a", parent=self.base)
        second = self.commit({"notes.txt": "one\ntwo\n"}, "Change the notes", parent=self.base)
        self.start_train_at(self.base)
        status, output = self.run_train(first, second)
        self.assertEqual(status, 0, output)
        latest, picked_second, picked_first = self.messages(3)
        self.assertTrue(latest.strip().startswith(train.REGENERATE_SUBJECT), latest)
        self.assertIn("- out/upper.txt", latest)
        self.assertIn("Co-Authored-By: Train test <train@example.invalid>", latest)
        self.assertIn(f"(cherry picked from commit {second})", picked_second)
        self.assertIn(f"(cherry picked from commit {first})", picked_first)
        self.assertEqual((self.worktree / "out/upper.txt").read_text(), "ALPHA TWO\nBETA\n")
        self.assertIn(f"git -C {self.worktree} push origin HEAD:main", output)
        self.assertIn("gh variable set FLY_DEPLOY_ENABLED", output)
        self.assertIn("--body false", output)
        self.assertNeverPushed()

    def test_a_commit_already_on_the_train_is_skipped(self):
        first = self.commit({"notes.txt": "one\ntwo\n"}, "Change the notes", parent=self.base)
        self.start_train_at(first)
        status, output = self.run_train(first)
        self.assertEqual(status, 0, output)
        self.assertIn("already on the train", output)

    def test_known_wrong_a_generated_file_conflict_takes_the_train_side_and_is_regenerated(self):
        # Train 2's shape: both sides rebuilt the same generated file from different inputs.
        on_train = self.commit({"a.txt": "alpha train\n", "out/upper.txt": "ALPHA TRAIN\nBETA\n"}, "Train side",
                               parent=self.base)
        picked = self.commit({"b.txt": "beta picked\n", "out/upper.txt": "ALPHA\nBETA PICKED\n"}, "Picked side",
                             parent=self.base)
        self.start_train_at(on_train)
        status, output = self.run_train(picked)
        self.assertEqual(status, 0, output)
        self.assertIn("out/upper.txt: generated; took the train's side", output)
        self.assertEqual((self.worktree / "out/upper.txt").read_text(), "ALPHA TRAIN\nBETA PICKED\n")
        self.assertTrue(self.messages(1)[0].startswith(train.REGENERATE_SUBJECT))
        self.assertIn(f"(cherry picked from commit {picked})", self.messages(2)[1])
        self.assertNeverPushed()

    def test_known_wrong_any_other_conflict_stops_the_train_and_names_the_file(self):
        on_train = self.commit({"notes.txt": "one\ntrain\n"}, "Train notes", parent=self.base)
        picked = self.commit({"notes.txt": "one\npicked\n"}, "Picked notes", parent=self.base)
        later = self.commit({"a.txt": "alpha later\n"}, "A later change", parent=self.base)
        self.start_train_at(on_train)
        status, output = self.run_train(picked, later)
        self.assertEqual(status, 2, output)
        self.assertIn("STOPPED at", output)
        self.assertIn("notes.txt: not a generated file", output)
        self.assertIn(later, output, "the stop names the commits still to pick")
        self.assertTrue((self.worktree / ".git" / "CHERRY_PICK_HEAD").exists(), "the conflict is left in place")
        self.assertNotIn("push origin", output)
        self.assertNeverPushed()

    def test_known_wrong_two_appends_to_one_list_are_kept_in_order(self):
        on_train = self.commit({"devtools/allow.yaml": ALLOWLIST + "  - finding_id: f3\n    path: src/c.py\n"},
                               "Allow f3", parent=self.base)
        picked = self.commit({"devtools/allow.yaml": ALLOWLIST + "  - finding_id: f4\n    path: src/d.py\n"},
                             "Allow f4", parent=self.base)
        self.start_train_at(on_train)
        status, output = self.run_train(picked)
        self.assertEqual(status, 0, output)
        self.assertIn("devtools/allow.yaml: 1 list appends kept, the train's entries first", output)
        entries = yaml.safe_load((self.worktree / "devtools/allow.yaml").read_text())["entries"]
        self.assertEqual([entry["finding_id"] for entry in entries], ["f1", "f2", "f3", "f4"])

    def test_known_wrong_a_repeated_identifier_or_a_changed_entry_stops_the_train(self):
        on_train = self.commit({"devtools/allow.yaml": ALLOWLIST + "  - finding_id: f3\n    path: src/c.py\n"},
                               "Allow f3 here", parent=self.base)
        repeated = self.commit({"devtools/allow.yaml": ALLOWLIST + "  - finding_id: f3\n    path: src/other.py\n"},
                               "Allow f3 there", parent=self.base)
        self.start_train_at(on_train)
        status, output = self.run_train(repeated)
        self.assertEqual(status, 2, output)
        self.assertIn("an identifier repeats after the append: finding_id f3", output)
        self.run_git(self.worktree, "cherry-pick", "--abort")
        changed = self.commit({"devtools/allow.yaml": ALLOWLIST.replace("src/b.py", "src/b2.py")}, "Move f2",
                              parent=self.base)
        other = self.commit({"devtools/allow.yaml": ALLOWLIST.replace("src/b.py", "src/b3.py")}, "Move f2 again",
                            parent=self.base)
        self.start_train_at(changed)
        status, output = self.run_train(other)
        self.assertEqual(status, 2, output)
        self.assertIn("not an append", output)

    def test_the_shard_manifest_takes_its_version_2_side(self):
        on_train = self.commit({"tools/ci_test_shards.json": dump(MANIFEST_V2)}, "Place shards at run time",
                               parent=self.base)
        listed = dict(MANIFEST_V1, shards={"a": ["test_one", "test_three"], "b": ["test_two"]},
                      measured_seconds={"a": 2.0, "b": 1.0})
        picked = self.commit({"tools/ci_test_shards.json": dump(listed), "notes.txt": "one\nthree\n"},
                             "Add test_three", parent=self.base)
        self.start_train_at(on_train)
        status, output = self.run_train(picked)
        self.assertEqual(status, 0, output)
        self.assertIn("kept the train's version 2 manifest", output)
        self.assertEqual(json.loads((self.worktree / "tools/ci_test_shards.json").read_text()), MANIFEST_V2)
        self.assertEqual((self.worktree / "notes.txt").read_text(), "one\nthree\n")

    def test_known_wrong_both_sides_changing_a_version_2_manifest_stop(self):
        on_train = self.commit({"tools/ci_test_shards.json": dump(dict(MANIFEST_V2, shards=["a", "b", "c"]))},
                               "Three shards", parent=self.base)
        picked = self.commit({"tools/ci_test_shards.json": dump(dict(MANIFEST_V2, shards=["a", "b", "d"]))},
                             "Other three shards", parent=self.base)
        self.start_train_at(on_train)
        status, output = self.run_train(picked)
        self.assertEqual(status, 2, output)
        self.assertIn("both sides changed the shard manifest (versions 2 and 2)", output)


class GateTests(TrainCase):
    def test_the_gates_run_and_their_result_line_is_repeated(self):
        change = self.commit({"notes.txt": "one\ntwo\n"}, "Change the notes", parent=self.base)
        self.start_train_at(self.base)
        status, output = self.run_train(change, gates_exit=0, extra=())
        self.assertEqual(status, 0, output)
        self.assertIn("RESULT: all 1 gates passed; NOT EQUIVALENT TO CI", output)
        self.assertIn("READY", output)

    def test_known_wrong_a_failed_gate_is_not_ready_and_prints_no_push(self):
        change = self.commit({"notes.txt": "one\ntwo\n"}, "Change the notes", parent=self.base)
        self.start_train_at(self.base)
        status, output = self.run_train(change, gates_exit=1, extra=())
        self.assertEqual(status, 1, output)
        self.assertIn("NOT READY", output)
        self.assertNotIn("push origin", output)
        self.assertNeverPushed()

    def test_known_wrong_a_dirty_worktree_or_another_branch_is_refused(self):
        change = self.commit({"notes.txt": "one\ntwo\n"}, "Change the notes", parent=self.base)
        self.start_train_at(self.base)
        (self.worktree / "a.txt").write_text("edited by hand\n")
        status, output = self.run_train(change)
        self.assertEqual(status, 2, output)
        self.assertIn("uncommitted changes to tracked files", output)
        self.run_git(self.worktree, "checkout", "-q", "--", "a.txt")
        self.run_git(self.worktree, "checkout", "-q", "-b", "topic")
        status, output = self.run_train(change)
        self.assertEqual(status, 2, output)
        self.assertIn("has the branch topic checked out", output)


class ResolverTests(unittest.TestCase):
    """The list append resolver alone, on conflict text in the diff3 form."""

    @staticmethod
    def conflict(ours: str, theirs: str, base: str = "", after: str = "") -> str:
        return (ALLOWLIST + "<<<<<<< HEAD\n" + ours + "||||||| base\n" + base + "=======\n" + theirs
                + ">>>>>>> picked\n" + after)

    def test_a_pure_append_keeps_ours_then_theirs(self):
        text, count = train.resolve_list_appends(self.conflict("  - finding_id: f3\n", "  - finding_id: f4\n"))
        self.assertEqual(count, 1)
        self.assertTrue(text.endswith("  - finding_id: f3\n  - finding_id: f4\n"), text)

    def test_known_wrong_a_side_that_is_not_a_whole_entry_is_refused(self):
        with self.assertRaisesRegex(train.Unresolved, "does not start with a list entry"):
            train.resolve_list_appends(self.conflict("    path: src/c.py\n", "  - finding_id: f4\n"))
        with self.assertRaisesRegex(train.Unresolved, "outside its list entries"):
            train.resolve_list_appends(self.conflict("  - finding_id: f3\nversion: 2\n", "  - finding_id: f4\n"))

    def test_known_wrong_a_conflict_that_ends_inside_an_entry_is_refused(self):
        with self.assertRaisesRegex(train.Unresolved, "ends inside an entry"):
            train.resolve_list_appends(self.conflict("  - finding_id: f3\n", "  - finding_id: f4\n",
                                                     after="    path: src/shared.py\n"))

    def test_known_wrong_a_changed_line_is_not_an_append(self):
        with self.assertRaisesRegex(train.Unresolved, "not an append"):
            train.resolve_list_appends(self.conflict("  - finding_id: f3\n", "  - finding_id: f4\n",
                                                     base="  - finding_id: f0\n"))

    def test_only_new_repeats_count(self):
        before = yaml.safe_load(ALLOWLIST + "  - finding_id: f1\n    path: again.py\n")
        after = yaml.safe_load(ALLOWLIST + "  - finding_id: f1\n    path: again.py\n  - finding_id: f2\n")
        self.assertEqual(train.identifier_repeats(after) - train.identifier_repeats(before),
                         {(("entries",), "finding_id", "f2")})

    def test_the_train_itself_refuses_to_push(self):
        # No real git runs here. If the guard were removed, the call would reach this recorder, never a remote: on
        # September 27, 2026 a mutant of an earlier form of this test, without the guard, ran a real
        # `git push origin HEAD:main` from the development worktree and moved main.
        calls = []

        def recorder(command, **_options):
            calls.append(command)
            return subprocess.CompletedProcess(command, 0, "", "")

        with mock.patch.object(train.subprocess, "run", recorder):
            with self.assertRaises(AssertionError):
                train.git(Path("/nonexistent-train"), "push", "origin", "HEAD:main")
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
