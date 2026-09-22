"""Exercise the actual workflow permission gate without a provider or secret."""
from pathlib import Path
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 is a supported development runtime.
    import tomli as tomllib

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_fly_service_container as container_check  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def image_default_command():
    """The command the service image runs when it is started without one."""
    for line in (ROOT / "Dockerfile.service").read_text("utf-8").splitlines():
        if line.startswith("CMD "):
            return json.loads(line[len("CMD "):])
    raise AssertionError("Dockerfile.service names no default command")


def refusal_of_the_image_command(host):
    """What the service's own start rule says about this host file under the image's command."""
    from loop_engine.core.service_runtime.http import ServiceHttpConfiguration
    from loop_engine.core.service_runtime.http_entrypoint import public_binding_refusal
    arguments = image_default_command()
    transport = ServiceHttpConfiguration(**host["http"])
    return public_binding_refusal(arguments[arguments.index("--host") + 1],
                                  "--behind-trusted-tls-proxy" in arguments, transport.request_limits)


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

    def test_the_container_check_expects_the_command_the_image_declares(self):
        self.assertEqual(container_check.DEFAULT_COMMAND, image_default_command())

    def test_every_host_file_the_container_check_writes_states_the_proxy_header(self):
        """The image's own command would refuse to serve either file without the statement.

        Each file names the Fly proxy's header, as the host file on the Fly
        volume does, and the service's own start rule accepts it for the
        image's default command. The known-wrong file is the same file with
        the statement removed, which is what the container check starts to
        prove that the image refuses it.
        """
        for name, host in (("default command", container_check.default_command_host_configuration()),
                           ("packaged catalogue", container_check.packaged_catalogue_host_configuration(
                               ["pilot-owner"]))):
            with self.subTest(host=name):
                self.assertEqual(host["http"]["request_limits"], container_check.FLY_REQUEST_LIMITS)
                self.assertEqual(refusal_of_the_image_command(host), "")
                wrong = container_check.without_client_address_source(host)
                self.assertNotIn("request_limits", wrong["http"])
                self.assertEqual({**wrong["http"], "request_limits": host["http"]["request_limits"]}, host["http"])
                self.assertIn("request_limits", refusal_of_the_image_command(wrong))

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
