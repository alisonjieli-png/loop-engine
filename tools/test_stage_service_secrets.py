"""Staging runtime credentials never shows a value and never stages an operator credential."""
from __future__ import annotations

import subprocess
import unittest
import unittest.mock

import stage_service_secrets as staging

DATA = {"api_keys": {
    "runtime-a": {"purpose": "secret-api", "environment": "RUNTIME_A"},
    "runtime-b": {"purpose": "transactional-email", "environment": "RUNTIME_B"},
    "same-name": {"purpose": "publishable-api", "environment": "RUNTIME_A"},
    "deploy": {"purpose": "organization-deploy", "environment": "DEPLOY_TOKEN"},
    "administrator": {"purpose": "service-access", "environment": "ADMIN_TOKEN"}},
    "oauth": {"management": {"environment": "MANAGEMENT_TOKEN"}}}
VALUES = {"runtime-a": "value-of-a-0123456789", "runtime-b": "value-of-b-0123456789"}


class Runner:
    def __init__(self, returncode=0, echo=False):
        self.calls, self.returncode, self.echo = [], returncode, echo

    def __call__(self, command, **options):
        self.calls.append((command, options))
        return subprocess.CompletedProcess(command, self.returncode, options["input"] if self.echo else "staged", "")


class StagingTests(unittest.TestCase):
    def test_values_travel_on_standard_input_and_only_names_are_reported(self):
        runner = Runner()
        pairs = staging.selected(["runtime-a", "runtime-b"], DATA)
        result = staging.stage("example-app", pairs, "deploy-token-0123456789", VALUES.__getitem__, run=runner)
        command, options = runner.calls[0]
        self.assertEqual(command, ["fly", "secrets", "import", "--app", "example-app", "--stage"])
        self.assertEqual(options["input"], "RUNTIME_A=value-of-a-0123456789\nRUNTIME_B=value-of-b-0123456789\n")
        self.assertEqual(result["staged_names"], ["RUNTIME_A", "RUNTIME_B"])
        for secret in (*VALUES.values(), "deploy-token-0123456789"):
            self.assertNotIn(secret, " ".join(command))
            self.assertNotIn(secret, repr(result))

    def test_a_child_that_echoes_its_input_cannot_leak_a_value(self):
        result = staging.stage("example-app", staging.selected(["runtime-a"], DATA), "deploy-token-0123456789",
                               VALUES.__getitem__, run=Runner(echo=True))
        self.assertNotIn("value-of-a", result["output"])
        self.assertIn("[credential suppressed]", result["output"])

    def test_operator_and_management_credentials_are_refused(self):
        for name in ("deploy", "administrator", "management", "unknown"):
            with self.assertRaises(staging.StagingError, msg=name):
                staging.selected([name], DATA)
        with self.assertRaises(staging.StagingError):
            staging.selected([], DATA)

    def test_two_credentials_cannot_share_one_environment_name(self):
        with self.assertRaises(staging.StagingError):
            staging.selected(["runtime-a", "same-name"], DATA)

    def test_a_value_with_a_line_break_is_refused_before_anything_is_sent(self):
        runner = Runner()
        with self.assertRaises(staging.StagingError):
            staging.stage("example-app", staging.selected(["runtime-a"], DATA), "deploy-token",
                          lambda _name: "first\nSECOND=injected", run=runner)
        self.assertEqual(runner.calls, [])

    def test_a_timeout_is_an_unknown_outcome_and_is_not_repeated(self):
        calls = []

        def slow(command, **options):
            calls.append(command)
            raise subprocess.TimeoutExpired(command, 1)
        with self.assertRaisesRegex(staging.StagingError, "outcome_unknown"):
            staging.stage("example-app", staging.selected(["runtime-a"], DATA), "deploy-token",
                          VALUES.__getitem__, run=slow)
        self.assertEqual(len(calls), 1)

    def test_nothing_is_sent_without_the_confirmation_flag(self):
        import io
        from contextlib import redirect_stdout
        from unittest import mock
        with mock.patch.object(staging.operator_credentials, "references", return_value=DATA), \
                mock.patch.object(staging, "stage") as stage, redirect_stdout(io.StringIO()) as shown:
            code = staging.main(["--app", "example-app", "--account", "example", "--ref", "runtime-a"])
        self.assertEqual(code, 0)
        stage.assert_not_called()
        self.assertIn('"dry_run": true', shown.getvalue())

    def test_removing_the_purpose_guard_is_detected(self):
        # Known-wrong control: without the purpose rule the deployment
        # credential itself would be staged into the service.
        with unittest.mock.patch.object(staging, "RUNTIME_PURPOSES", ("organization-deploy",)):
            self.assertEqual(staging.selected(["deploy"], DATA), {"DEPLOY_TOKEN": "deploy"})


if __name__ == "__main__":
    unittest.main()
