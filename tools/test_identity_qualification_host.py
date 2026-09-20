"""Operator bridge tests never contact a provider or modify hosted state."""
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import identity_qualification_host as host


class QualificationHostTests(unittest.TestCase):
    def setUp(self):
        self.request = dict(application="fixture-app", origin="https://app.example", issuer="https://fixture.supabase.co/auth/v1",
            run_id="a" * 32, subjects=["00000000-0000-4000-8000-000000000001", "00000000-0000-4000-8000-000000000002"],
            operation="prepare", expected_sources={"src/loop_engine/core/service_runtime/" + name: "b" * 64 for name in
                ("access.py", "records.py", "runtime.py", "storage.py", "provisioning.py", "http.py", "http_auth.py", "browser_identity.py")})

    def test_invalid_target_cannot_start_an_operator_command(self):
        for field, value in (("application", "other; command"), ("origin", "http://untrusted.example"),
                             ("origin", "https://user@app.example"), ("origin", "https://app.example/path"),
                             ("subjects", []), ("subjects", ["bad", "worse"]), ("operation", "delete-all"),
                             ("run_id", "../escape"), ("expected_sources", {})):
            with self.subTest(field=field, value=value), patch.object(host.subprocess, "run") as run:
                with self.assertRaises(ValueError): host.operate(**{**self.request, field: value})
                run.assert_not_called()

    def test_source_and_target_are_bound_before_any_tenant_write(self):
        captured = []
        def run(command, **kwargs):
            captured.append((command, kwargs)); return subprocess.CompletedProcess(command, 0, json.dumps({"operation":"prepare"}), "")
        with patch.dict(host.os.environ, {"SUPABASE_SECRET_KEY":"fixture-private", "SUPABASE_PUBLISHABLE_KEY":"fixture-public"}), patch.object(host.subprocess, "run", side_effect=run):
            host.operate(**self.request)
        command, kwargs = captured[0]
        code = command[-1]
        self.assertLess(code.index('unqualified deployed source'), code.index('ensure_subject_tenant'))
        self.assertIn('unbound origin', code); self.assertIn('different identity project', code)
        self.assertIn('public admission must stay closed', code)
        self.assertNotIn("SUPABASE_SECRET_KEY", kwargs["env"])
        self.assertNotIn("SUPABASE_PUBLISHABLE_KEY", kwargs["env"])
        self.assertNotIn("fixture-private", repr(command))

    def test_failed_operator_command_is_not_automatically_repeated(self):
        with patch.object(host.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, "", "private diagnostic")) as run:
            with self.assertRaisesRegex(RuntimeError, "reconcile_before_retry"): host.operate(**self.request)
        self.assertEqual(run.call_count, 1)

    def test_wrong_acknowledgment_does_not_claim_success(self):
        with patch.object(host.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, '{"operation":"unrelated"}', "")):
            with self.assertRaisesRegex(RuntimeError, "acknowledgment_invalid"): host.operate(**self.request)


if __name__ == "__main__":
    unittest.main()
