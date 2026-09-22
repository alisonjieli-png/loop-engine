"""Exercise the actual workflow permission gate without a provider or secret."""
from pathlib import Path
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest

import yaml

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 is a supported development runtime.
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]


class FlyDeploymentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = yaml.load((ROOT / ".github/workflows/fly-pilot.yml").read_text(), Loader=yaml.BaseLoader)
        cls.steps = cls.workflow["jobs"]["pilot"]["steps"]
        cls.guard = next(row["run"] for row in cls.steps if row.get("id") == "authority")

    def run_guard(self, changes=None, script=None):
        env = {"PATH": os.environ["PATH"], "GITHUB_REF": "refs/heads/main", "OPERATION": "deploy",
               "APP_CONFIRMATION": "example-pilot", "FLY_ORG": "example", "FLY_APP": "example-pilot",
               "FLY_PRIMARY_REGION": "iad", "FLY_DEPLOY_ENABLED": "true", "FLY_SERVICE_CONFIGURED": "true",
               "FLY_APPROVED_MONTHLY_USD": "50", "FLY_DEPLOYMENT_APPROVAL_REF": "owner:fixture"}
        env.update(changes or {})
        return subprocess.run(["bash", "-euo", "pipefail", "-c", script or self.guard],
                              env=env, capture_output=True, timeout=5).returncode

    def test_explicit_complete_settings_pass(self):
        self.assertEqual(self.run_guard(), 0)

    def test_read_only_access_check_needs_no_spending_approval(self):
        self.assertEqual(self.run_guard({"OPERATION": "verify_access", "FLY_DEPLOY_ENABLED": "false",
            "FLY_APPROVED_MONTHLY_USD": "", "FLY_APP": "", "FLY_PRIMARY_REGION": ""}), 0)

    def test_incomplete_ambiguous_or_injected_settings_refuse(self):
        for change in ({"FLY_DEPLOY_ENABLED": "false"}, {"FLY_DEPLOY_ENABLED": "TRUE"},
            {"FLY_SERVICE_CONFIGURED": "false"}, {"FLY_APP": "--other-app"},
            {"FLY_APP": "example\n-pilot"}, {"FLY_PRIMARY_REGION": ""},
            {"APP_CONFIRMATION": "different"}, {"FLY_APPROVED_MONTHLY_USD": "0"},
            {"FLY_APPROVED_MONTHLY_USD": "NaN"}, {"FLY_DEPLOYMENT_APPROVAL_REF": ""},
            {"GITHUB_REF": "refs/pull/1/merge"}, {"FLY_ORG": ""}, {"OPERATION": "unknown"}):
            with self.subTest(change=change):
                self.assertNotEqual(self.run_guard(change), 0)

    def test_removed_guards_are_detected_by_their_counterexamples(self):
        mutants = (("${FLY_DEPLOY_ENABLED}", {"FLY_DEPLOY_ENABLED": "false"}),
                   ("${FLY_SERVICE_CONFIGURED}", {"FLY_SERVICE_CONFIGURED": "false"}),
                   ("${APP_CONFIRMATION}", {"APP_CONFIRMATION": "different"}),
                   ("${FLY_APPROVED_MONTHLY_USD}", {"FLY_APPROVED_MONTHLY_USD": "0"}),
                   ("${FLY_DEPLOYMENT_APPROVAL_REF}", {"FLY_DEPLOYMENT_APPROVAL_REF": ""}),
                   ("${GITHUB_REF}", {"GITHUB_REF": "refs/pull/1/merge"}))
        for marker, counterexample in mutants:
            with self.subTest(guard=marker):
                mutant = "\n".join(line for line in self.guard.splitlines() if marker not in line)
                self.assertNotEqual(self.run_guard(counterexample), 0)
                self.assertEqual(self.run_guard(counterexample, mutant), 0)

    def test_workflow_is_manual_and_secrets_are_step_scoped(self):
        self.assertEqual(set(self.workflow["on"]), {"workflow_dispatch"})
        self.assertEqual(self.workflow["on"]["workflow_dispatch"]["inputs"]["operation"]["default"], "verify_access")
        job = self.workflow["jobs"]["pilot"]
        self.assertEqual(job["environment"], "pilot")
        self.assertNotIn("FLY_API_TOKEN", job["env"])
        for row in self.steps:
            if "uses" in row:
                self.assertRegex(row["uses"], r"@[0-9a-f]{40}$")
            if "docker build" in row.get("run", ""):
                self.assertNotIn("FLY_API_TOKEN", row.get("env", {}))
                self.assertIn("tools/check_fly_service_container.py", row["run"])
        deploy = next(row["run"] for row in self.steps if row["name"] == "Publish and deploy the exact tested image")
        for required in ("--ha=false", "--strategy immediate", "--deploy-retries 0", "--no-public-ips", "@sha256:"):
            self.assertIn(required, deploy)
        self.assertNotIn("flyctl launch", str(self.workflow))
        self.assertIn(".result.ready == true", deploy)

    def test_the_deploy_health_gate_accepts_what_the_service_actually_serves(self):
        """Run the workflow's own filter over a health record the code produced.

        A gate written against a health record the service no longer serves
        fails every deployment after a successful release, and a gate that
        accepts anything passes a machine that can serve nobody. Both are
        caught here by running the exact filter from the workflow, first over a
        real ready record and then over the known-wrong case of one that is not
        ready.
        """
        if shutil.which("jq") is None:
            self.skipTest("jq is required to run the workflow's own health gate")
        deploy = next(row["run"] for row in self.steps if row["name"] == "Publish and deploy the exact tested image")
        expression = re.search(r"jq -e '(.+?)' >/dev/null", deploy)
        self.assertIsNotNone(expression, "the deploy step must gate the release on a readable jq expression")
        gate = expression.group(1)

        from loop_engine.core.service_runtime.http_test_fixtures import HttpDomainFixture
        from loop_engine.core.service_runtime.observability import readiness_report, ServiceObservabilityPolicy
        with tempfile.TemporaryDirectory(prefix="fly-health-gate-") as directory:
            fixture = HttpDomainFixture(Path(directory))
            def measure(policy):
                return readiness_report(config=fixture.runtime.config, provisioning=fixture.provisioning,
                    authentication_modes=("host_key",), policy=policy, browser_identity_installed=False,
                    billing_sessions_installed=False, billing_webhook_installed=False)
            ready = measure(ServiceObservabilityPolicy())
            # Known-wrong case: a volume with no room left to write. The
            # service answers, so a gate that only checked for an answer would
            # pass it. This one must refuse the release.
            unready = measure(ServiceObservabilityPolicy(minimum_free_bytes=2**40))

        def run_gate(record):
            served = json.dumps({"record_type": "service_operation_result/v1",
                                 "operation": "health", "result": record})
            return subprocess.run(["jq", "-e", gate], input=served, capture_output=True,
                                  text=True, timeout=10).returncode

        self.assertTrue(ready["ready"])
        self.assertEqual(run_gate(ready), 0, "the deploy gate rejected the health record the service serves")
        self.assertFalse(unready["ready"])
        self.assertNotEqual(run_gate(unready), 0, "the deploy gate accepted a service that is not ready")

    def test_every_container_health_probe_reads_only_fields_the_service_serves(self):
        """Read each health field the container check asserts from a real health record.

        The container check runs two probes against the image. After the
        September 22 merges one of them asserted the measured record and the
        other still asserted the field `healthy`, which only the retired
        `service_health/v1` record carried, so no release could satisfy both.
        Every field a probe reads must be a field of the record the code builds.
        """
        from loop_engine.core.service_runtime.http_test_fixtures import HttpDomainFixture
        from loop_engine.core.service_runtime.observability import readiness_report, ServiceObservabilityPolicy
        with tempfile.TemporaryDirectory(prefix="fly-health-probe-") as directory:
            fixture = HttpDomainFixture(Path(directory))
            served = readiness_report(config=fixture.runtime.config, provisioning=fixture.provisioning,
                authentication_modes=("host_key",), policy=ServiceObservabilityPolicy(),
                browser_identity_installed=False, billing_sessions_installed=False,
                billing_webhook_installed=False)
        source = (ROOT / "tools/check_fly_service_container.py").read_text(encoding="utf-8")
        read = set(re.findall(r"""health\[(['"])result\1\]\[(['"])(\w+)\2\]""", source))
        fields = {name for _open, _close, name in read}
        fields.update(name for _quote, name in re.findall(r"""health\[(['"])(\w+)\1\]""", source)
                      if name != "result")
        self.assertTrue(fields, "the container check must read the health record it probes")
        self.assertEqual(sorted(fields - set(served)), [],
                         "a container probe reads a health field the service does not serve")

    def test_service_profile_has_persistence_tls_and_a_real_server_command(self):
        profile = tomllib.loads((ROOT / "fly.toml").read_text())
        self.assertNotIn("app", profile)
        self.assertNotIn("primary_region", profile)
        self.assertTrue(profile["http_service"]["force_https"])
        self.assertEqual(profile["mounts"][0]["destination"], "/data")
        self.assertEqual(profile["http_service"]["checks"][0]["path"], "/api/v1/health")
        dockerfile = (ROOT / "Dockerfile.service").read_text()
        self.assertIn("USER 65534:65534", dockerfile)
        self.assertIn("'.[serving]'", dockerfile)
        self.assertIn('"service", "serve"', dockerfile)
        self.assertIn('"--behind-trusted-tls-proxy"', dockerfile)


if __name__ == "__main__":
    unittest.main()
