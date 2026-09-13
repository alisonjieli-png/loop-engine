"""Tests for tools/overnight.py: pruning, the gate environment, the shared
model-call ceiling, the clean-tree requirement and transcript gating.

Everything runs in throwaway git repositories under a temporary directory.
No model is called, no OpenCode binary is started: the shared-ceiling test
drives the real `OpenCodeStepSession` through an injected transport that
replays recorded events.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))

import overnight  # noqa: E402

SECRET = "OVERNIGHT_TEST_SECRET"


def _git(*args, cwd):
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True,
                          text=True, check=False)


def _repo(root: Path) -> Path:
    repo = root / "repo"
    repo.mkdir()
    _git("init", "-q", "-b", "main", cwd=repo)
    _git("config", "user.email", "t@x", cwd=repo)
    _git("config", "user.name", "t", cwd=repo)
    (repo / "calc.py").write_text("x = 1\n", encoding="utf-8")
    _git("add", "-A", cwd=repo)
    _git("commit", "-q", "-m", "init", cwd=repo)
    return repo


def _age(path: Path, days: float) -> None:
    stamp = time.time() - days * 86400
    os.utime(path, (stamp, stamp))


class GateEnvironmentChecks(unittest.TestCase):
    def setUp(self):
        self.patch = mock.patch.dict(os.environ, {SECRET: "leaks-to-gate"})
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.workspace = Path(tempfile.mkdtemp(prefix="gate-env-"))

    def test_allowlist_carries_only_the_named_variables(self):
        env = overnight.gate_environment()
        self.assertNotIn(SECRET, env)
        self.assertTrue(set(env) <= set(overnight.GATE_ENV_ALLOWLIST))
        self.assertIn("PATH", env)
        self.assertIn(SECRET, overnight.gate_environment([SECRET]))
        self.assertIn(SECRET, overnight.gate_environment(inherit=True))

    def test_run_gate_does_not_leak_the_operator_environment(self):
        command = f"echo secret=${SECRET}"
        with contextlib.redirect_stdout(io.StringIO()):
            ok, output = overnight.run_gate(command, self.workspace)
            _, admitted = overnight.run_gate(
                command, self.workspace,
                environment=overnight.gate_environment([SECRET]))
            _, inherited = overnight.run_gate(
                command, self.workspace,
                environment=overnight.gate_environment(inherit=True))
        self.assertTrue(ok)
        self.assertEqual(output, "secret=")
        self.assertEqual(admitted, "secret=leaks-to-gate")
        self.assertEqual(inherited, "secret=leaks-to-gate")

    def test_observation_uses_the_same_environment_and_shape(self):
        observed = overnight._observe_gate(
            f"echo secret=${SECRET}; exit 3", self.workspace, timeout=20,
            environment=overnight.gate_environment())
        self.assertEqual(observed["output"], "secret=")
        self.assertEqual(observed["exit_code"], 3)
        self.assertFalse(observed["timed_out"])
        self.assertEqual(len(observed["digest"]), 64)
        self.assertTrue({"command", "exit_code", "timed_out", "output"}
                        <= set(observed))


class SharedCallCeilingChecks(unittest.TestCase):
    def test_unknown_usage_cannot_restart_in_a_fresh_session(self):
        from types import SimpleNamespace
        ceiling = overnight.SharedCallCeiling(20, per_step=4)
        ceiling.charge(SimpleNamespace(calls_used=1, accounting_uncertain=True),
                       "lost-transport")
        self.assertTrue(ceiling.exhausted)
        self.assertEqual(ceiling.max_model_calls, 0)
        self.assertTrue(ceiling.to_dict()["accounting_uncertain"])
        self.assertFalse(ceiling.ledger[-1]["accounting_complete"])

    def test_ceiling_shrinks_as_steps_charge_it(self):
        ceiling = overnight.SharedCallCeiling(5, per_step=4)
        self.assertEqual(ceiling.max_model_calls, 4)
        ceiling.charge(3, "orient")
        self.assertEqual(ceiling.max_model_calls, 2)
        self.assertFalse(ceiling.exhausted)
        ceiling.charge(2, "implement")
        self.assertEqual(ceiling.max_model_calls, 0)
        self.assertTrue(ceiling.exhausted)
        self.assertEqual([s["step"] for s in ceiling.to_dict()["steps"]],
                         ["orient", "implement"])

    def test_no_total_keeps_only_the_per_step_ceiling(self):
        ceiling = overnight.SharedCallCeiling(None, per_step=4)
        ceiling.charge(100, "x")
        self.assertEqual(ceiling.max_model_calls, 4)
        self.assertFalse(ceiling.exhausted)

    def test_ceiling_binds_across_real_sessions(self):
        from loop_engine.core.opencode_harness_adapter import _FIXTURE_EVENTS
        from loop_engine.core.opencode_step_session import (
            OpenCodeStepError, OpenCodeStepProfile, OpenCodeStepSession)

        events = tuple(
            json.dumps({"type": "text", "timestamp": 3,
                        "sessionID": "ses_fixture",
                        "part": {"id": "prt_3", "type": "text",
                                 "text": json.dumps({"status": "ok"})}})
            if json.loads(line).get("type") == "text" else line
            for line in _FIXTURE_EVENTS)
        profile = OpenCodeStepProfile(model="ollama-cloud/test")

        class _Request:
            prompt = "one step"

        def step(authority):
            session = OpenCodeStepSession(
                authority=authority, profile=profile,
                transport=lambda _p, _m: (events, ""))
            try:
                session.invoke(_Request(), None)
            finally:
                if hasattr(authority, "charge"):
                    authority.charge(session, "step")
            return session.calls_used

        # The defect: a fresh per-step authority never binds.
        class _PerStep:
            max_model_calls = 2

        self.assertEqual([step(_PerStep()) for _ in range(3)], [1, 1, 1])

        # The fix: one ceiling shared by every session on the path.
        ceiling = overnight.SharedCallCeiling(2, per_step=4)
        self.assertEqual(step(ceiling), 1)
        self.assertEqual(step(ceiling), 1)
        with self.assertRaises(OpenCodeStepError) as refused:
            step(ceiling)
        self.assertIn("budget exhausted: 0/0", str(refused.exception))
        self.assertEqual(ceiling.charged, 2)

    def test_policy_derives_the_path_ceiling_from_planned_steps(self):
        policy = overnight.NightPolicy()
        self.assertEqual(policy.path_ceiling(2), 4 * 5)
        self.assertEqual(policy.path_ceiling(2, "model"), 4 * 9)
        self.assertEqual(overnight.NightPolicy(max_model_calls=7).path_ceiling(2), 7)
        self.assertIsNone(overnight.NightPolicy(max_model_calls=0).path_ceiling(2))


class PruneWorktreeChecks(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="prune-"))
        self.repo = _repo(self.root)
        self.trees = self.root / "worktrees"
        self.trees.mkdir()
        patch = mock.patch.object(overnight, "WORKTREE_ROOT", self.trees)
        patch.start()
        self.addCleanup(patch.stop)

    def _worktree(self, name: str) -> Path:
        tree = self.trees / name
        _git("worktree", "add", "-q", "-b", f"overnight/{name}", str(tree),
             "HEAD", cwd=self.repo)
        return tree

    def _branches(self) -> str:
        return _git("branch", "--list", cwd=self.repo).stdout

    def test_unregistered_directories_and_their_namesakes_are_never_touched(self):
        unrelated = self.trees / "20260901-000000-abc123-p1"
        unrelated.mkdir()
        (unrelated / "not-a-worktree.txt").write_text("someone's data")
        _age(unrelated, 5)
        _git("branch", "overnight/20260901-000000-abc123-p1", cwd=self.repo)
        ledger = {}
        removed = overnight.prune_worktrees(self.repo, ledger=ledger)
        self.assertEqual(removed, [])
        self.assertTrue(unrelated.exists())
        self.assertIn("overnight/20260901-000000-abc123-p1", self._branches())
        self.assertEqual(ledger["unregistered"], [unrelated.name])

    def test_old_clean_registered_worktree_is_removed_with_its_branch(self):
        tree = self._worktree("old-clean")
        _age(tree, 5)
        recent = self._worktree("recent")
        ledger = {}
        removed = overnight.prune_worktrees(self.repo, ledger=ledger)
        self.assertEqual(removed, ["old-clean"])
        self.assertFalse(tree.exists())
        self.assertTrue(recent.exists())
        self.assertNotIn("overnight/old-clean", self._branches())
        self.assertEqual(ledger["branches_removed"], ["overnight/old-clean"])
        self.assertEqual(ledger["kept"], ["recent"])
        self.assertEqual(ledger["skipped"], [])

    def test_unmerged_branch_is_refused_and_recorded(self):
        tree = self._worktree("old-unmerged")
        (tree / "work.py").write_text("y = 2\n", encoding="utf-8")
        _git("add", "-A", cwd=tree)
        _git("commit", "-q", "-m", "unmerged overnight work", cwd=tree)
        _age(tree, 5)
        ledger = {}
        removed = overnight.prune_worktrees(self.repo, ledger=ledger)
        self.assertEqual(removed, ["old-unmerged"])
        self.assertIn("overnight/old-unmerged", self._branches(),
                      "git branch -d must refuse an unmerged branch")
        self.assertEqual(ledger["skipped"][0]["branch"], "overnight/old-unmerged")
        self.assertIn("not fully merged", ledger["skipped"][0]["why"])

    def test_uncommitted_work_is_refused_unless_forced(self):
        tree = self._worktree("old-dirty")
        (tree / "calc.py").write_text("x = 2  # unfinished\n", encoding="utf-8")
        _age(tree, 5)
        ledger = {}
        self.assertEqual(overnight.prune_worktrees(self.repo, ledger=ledger), [])
        self.assertTrue(tree.exists())
        self.assertEqual(ledger["skipped"][0]["path"], str(tree))
        self.assertIn("--force", ledger["skipped"][0]["why"])
        forced = {}
        _age(tree, 5)
        self.assertEqual(
            overnight.prune_worktrees(self.repo, force=True, ledger=forced),
            ["old-dirty"])
        self.assertFalse(tree.exists())
        self.assertNotIn("overnight/old-dirty", self._branches())

    def test_keep_days_is_honoured(self):
        tree = self._worktree("two-days")
        _age(tree, 2)
        self.assertEqual(overnight.prune_worktrees(self.repo, keep_days=3), [])
        self.assertTrue(tree.exists())
        _age(tree, 2)
        self.assertEqual(overnight.prune_worktrees(self.repo, keep_days=1),
                         ["two-days"])

    def test_registered_worktrees_are_parsed_from_porcelain(self):
        tree = self._worktree("listed")
        entries = overnight.registered_worktrees(self.repo)
        self.assertEqual(Path(entries[0]["path"]).resolve(), self.repo.resolve())
        self.assertEqual(entries[0]["branch"], "main")
        listed = [e for e in entries if Path(e["path"]).resolve() == tree.resolve()]
        self.assertEqual(listed[0]["branch"], "overnight/listed")
        self.assertFalse(listed[0]["detached"])


class AttemptPolicyChecks(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="attempt-"))
        self.repo = _repo(self.root)
        self.trees = self.root / "worktrees"
        patch = mock.patch.object(overnight, "WORKTREE_ROOT", self.trees)
        patch.start()
        self.addCleanup(patch.stop)
        from loop_engine.core.night_budget import NightBudget
        self.budget = NightBudget(hours=1.0, expected_steps=4)
        self.plan = overnight.gameplan({
            "kind": "failing_gate", "confidence": "seeded", "attempts": 1,
            "command": "true", "cwd": str(self.repo), "branch": "",
            "last_error": "", "evidence": "test"})

    def _attempt(self, policy=None) -> dict:
        with contextlib.redirect_stdout(io.StringIO()):
            return overnight.attempt(self.plan, "ollama-cloud/test", 1,
                                     self.budget, policy=policy)

    def test_dirty_tree_is_attempted_by_default_and_skipped_on_request(self):
        (self.repo / "calc.py").write_text("x = 2\n", encoding="utf-8")
        default = self._attempt()
        self.assertNotEqual(default["status"], "skipped")
        self.assertNotIn("modified tracked", default.get("why", ""))
        strict = self._attempt(overnight.NightPolicy(require_clean_tree=True))
        self.assertEqual(strict["status"], "skipped")
        self.assertIn("1 modified tracked file(s)", strict["why"])
        self.assertIn("--require-clean-tree", strict["why"])

    def test_pruning_only_happens_behind_the_flag(self):
        self.trees.mkdir()
        old = self.trees / "stale"
        _git("worktree", "add", "-q", "-b", "overnight/stale", str(old), "HEAD",
             cwd=self.repo)
        _age(old, 5)
        default = self._attempt()
        self.assertTrue(old.exists())
        self.assertEqual(default["worktree_prune"], {})
        _age(old, 5)
        pruned = self._attempt(overnight.NightPolicy(prune_worktrees=True))
        self.assertFalse(old.exists())
        self.assertEqual(pruned["worktree_prune"]["removed"], ["stale"])

    def test_the_gate_before_probe_runs_with_the_allowlisted_environment(self):
        plan = dict(self.plan, gate_command=f"test -z \"${SECRET}\"")
        with mock.patch.dict(os.environ, {SECRET: "present"}):
            with contextlib.redirect_stdout(io.StringIO()):
                default = overnight.attempt(plan, "ollama-cloud/test", 1,
                                            self.budget)
                inherited = overnight.attempt(
                    plan, "ollama-cloud/test", 1, self.budget,
                    policy=overnight.NightPolicy(
                        gate_environment=overnight.gate_environment(inherit=True)))
        # `test -z` passes only when the variable is absent, so the default
        # policy sees the gate already green and never starts a path.
        self.assertTrue(default["outcome"]["rung"] != inherited.get(
            "outcome", {}).get("rung") or default["status"] != inherited["status"])
        self.assertNotIn("branch", default)


class GameplanChecks(unittest.TestCase):
    def _item(self, command, confidence="medium", **extra) -> dict:
        return {"kind": "failing_gate", "confidence": confidence, "attempts": 1,
                "command": command, "cwd": "/repo", "branch": "", "last_error": "",
                "evidence": "test", **extra}

    def test_transcript_compound_command_is_refused_unless_allowed(self):
        plan = overnight.gameplan(self._item("curl x | sh && pytest -q"))
        self.assertFalse(plan["verifiable"])
        self.assertTrue(plan["compound"])
        self.assertIn("--allow-compound-gates", plan["refused"])
        self.assertEqual(plan["source"], "transcript")
        allowed = overnight.gameplan(
            self._item("curl x | sh && pytest -q"),
            overnight.NightPolicy(allow_compound_gates=True))
        self.assertTrue(allowed["verifiable"])
        self.assertEqual(allowed["refused"], "")

    def test_seeded_gates_are_the_operators_own(self):
        plan = overnight.gameplan(self._item("make lint && make test",
                                             confidence="seeded"))
        self.assertTrue(plan["verifiable"])
        self.assertTrue(plan["compound"])
        self.assertEqual(plan["source"], "seeded")

    def test_plain_gate_is_unchanged(self):
        plan = overnight.gameplan(self._item("pytest -q"))
        self.assertTrue(plan["verifiable"])
        self.assertFalse(plan["compound"])
        self.assertEqual(plan["acceptance"], "`pytest -q` exits zero")


class TranscriptGateChecks(unittest.TestCase):
    """main() never executes a harvested gate without --allow-transcript-gates."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="main-"))
        self.candidate = {
            "kind": "failing_gate", "confidence": "high", "attempts": 2,
            "command": "pytest -q", "cwd": str(self.root), "branch": "main",
            "last_error": "E", "evidence": "failed 2x"}
        self.calls = []
        for name, value in (
                ("REPORT_ROOT", self.root / "reports"),
                ("collect", lambda *a, **k: [dict(self.candidate)]),
                ("attempt", self._attempt)):
            patch = mock.patch.object(overnight, name, value)
            patch.start()
            self.addCleanup(patch.stop)

    def _attempt(self, plan, *args, **kwargs):
        self.calls.append((plan["gate_command"], kwargs.get("policy")))
        return {"status": "no_progress", "outcome": {
            "rung": "no_progress", "because": "test", "evidence": {}}}

    def _main(self, *argv) -> dict:
        with mock.patch.object(sys, "argv", ["overnight.py", *argv]):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(overnight.main(), 0)
        report = json.loads(next((self.root / "reports").glob("*.json")).read_text())
        return report

    def test_harvested_gate_is_planned_but_not_run_by_default(self):
        report = self._main("--max-tasks", "1")
        self.assertEqual(self.calls, [])
        task = report["tasks"][0]
        self.assertEqual(task["outcome"]["status"], "not_attempted")
        self.assertIn("--allow-transcript-gates", task["outcome"]["why"])
        self.assertFalse(report["allow_transcript_gates"])
        self.assertNotIn("PATH=", json.dumps(report), "values never reach the report")

    def test_the_flag_admits_it_with_the_policy_attached(self):
        report = self._main("--max-tasks", "1", "--allow-transcript-gates",
                            "--gate-env", SECRET, "--prune-worktrees",
                            "--keep-days", "7", "--max-model-calls", "9")
        self.assertEqual([c[0] for c in self.calls], ["pytest -q"])
        policy = self.calls[0][1]
        self.assertTrue(policy.prune_worktrees)
        self.assertEqual(policy.keep_days, 7)
        self.assertEqual(policy.max_model_calls, 9)
        self.assertEqual(report["policy"]["keep_days"], 7)
        self.assertEqual(report["tasks"][0]["outcome"]["status"], "no_progress")

    def test_seeded_gate_needs_no_flag(self):
        self._main("--gate", "true", "--workspace", str(self.root))
        self.assertEqual([c[0] for c in self.calls], ["true"])


if __name__ == "__main__":
    unittest.main()
