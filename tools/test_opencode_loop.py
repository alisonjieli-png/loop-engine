"""Tests for tools/opencode_loop.py: the verify timeout is a flag, the verify
environment is an allowlist, and one SharedCallCeiling binds across steps.

No OpenCode binary is started: `run_step` is driven with the session class
replaced by one whose transport replays recorded events.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))

import opencode_loop  # noqa: E402
import overnight  # noqa: E402

SECRET = "OVERNIGHT_TEST_SECRET"


class VerifyChecks(unittest.TestCase):
    def setUp(self):
        self.workspace = Path(tempfile.mkdtemp(prefix="verify-"))

    def test_default_timeout_is_the_documented_600_seconds(self):
        self.assertEqual(opencode_loop.DEFAULT_STEP_TIMEOUT, 600.0)

    def test_step_timeout_is_reported_not_raised(self):
        ok, output = opencode_loop.verify("sleep 5", self.workspace, timeout=0.3)
        self.assertFalse(ok)
        self.assertIn("--step-timeout", output)

    def test_verify_environment_is_the_allowlist(self):
        with mock.patch.dict(os.environ, {SECRET: "leaks"}):
            ok, output = opencode_loop.verify(f"echo v=${SECRET}", self.workspace)
            _, admitted = opencode_loop.verify(
                f"echo v=${SECRET}", self.workspace,
                environment=overnight.gate_environment([SECRET]))
        self.assertTrue(ok)
        self.assertEqual(output, "v=")
        self.assertEqual(admitted, "v=leaks")


class RunStepCeilingChecks(unittest.TestCase):
    def test_one_ceiling_binds_across_composed_steps(self):
        from loop_engine.core.night_budget import NightBudget
        from loop_engine.core.opencode_harness_adapter import _FIXTURE_EVENTS
        from loop_engine.core.opencode_step_session import (
            OpenCodeStepError, OpenCodeStepSession)

        events = tuple(
            json.dumps({"type": "text", "timestamp": 3,
                        "sessionID": "ses_fixture",
                        "part": {"id": "prt_3", "type": "text",
                                 "text": json.dumps({"task_summary": "t"})}})
            if json.loads(line).get("type") == "text" else line
            for line in _FIXTURE_EVENTS)

        def replaying(**kwargs):
            return OpenCodeStepSession(
                transport=lambda _p, _m: (events, ""), **kwargs)

        workspace = Path(tempfile.mkdtemp(prefix="loop-step-"))
        catalogue = opencode_loop.default_catalogue()
        library = opencode_loop.default_skill_library()
        layer, _ = opencode_loop.dynamic_step_layer(
            catalogue.select("orient"), "orient on the task", library)
        budget = NightBudget(hours=1.0, expected_steps=4)
        ceiling = overnight.SharedCallCeiling(2, per_step=4)
        with mock.patch.object(opencode_loop, "OpenCodeStepSession", replaying):
            for _ in range(2):
                value, result = opencode_loop.run_step(
                    layer, workspace, "ollama-cloud/test",
                    opencode_loop.SCHEMAS["orient"], "task", budget, ceiling)
                self.assertEqual(value, {"task_summary": "t"})
                self.assertTrue(result.ok)
            self.assertEqual(ceiling.charged, 2)
            self.assertTrue(ceiling.exhausted)
            with self.assertRaises(OpenCodeStepError):
                opencode_loop.run_step(
                    layer, workspace, "ollama-cloud/test",
                    opencode_loop.SCHEMAS["orient"], "task", budget, ceiling)
        self.assertEqual(ceiling.charged, 2, "a refused step charges nothing")
        self.assertEqual([s["calls"] for s in ceiling.ledger], [1, 1, 0])


if __name__ == "__main__":
    unittest.main()
