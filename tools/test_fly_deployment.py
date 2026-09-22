"""Exercise the actual workflow permission gate without a provider or secret."""
from contextlib import redirect_stdout
import copy
import io
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
DEPLOY_STEP = "Publish and deploy the exact tested image"
GRANT_STEP = "Apply the packaged catalogue grants on the one Machine"
READINESS = 'jq -e "${SERVICE_READINESS_GATE}" >/dev/null'
#: The grant command reaches the one Machine through the Machines API exec
#: call, the way it was run by hand after release 12. The JSON form carries the
#: command's exit code and its exact standard output, with nothing of the
#: command line tool's own mixed in.
GRANT_CALL = 'flyctl machine exec "${machine}" "${GRANT_COMMAND}" --app "${FLY_APP}" --json'
GRANT_GATE = re.compile(r"""jq -e --arg manifest "\$\{PACKAGED_MANIFEST\}" '(.+?)' >/dev/null""")


def exec_output(**fields):
    """What `flyctl machine exec --json` prints for one finished command.

    The command line tool encodes the Machines API answer with an indent of
    four spaces and leaves out every empty field, so a command that exits with
    status zero has no exit code field at all.
    """
    return json.dumps({name: value for name, value in fields.items() if value}, indent=4) + "\n"


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


def grant_step_problems(workflow):
    """Every way the release's post-deploy grant step falls short, or nothing.

    A release that changes the catalogue offers nothing until the packaged
    grants are applied on the machine, so the step must exist, follow the
    deploy, run the exact command the container check qualified against the
    one started Machine, gate on what that command printed, and end with the
    shared readiness check. It must not open a remote shell: from a new runner
    each shell session adds a WireGuard peer to the organization that nothing
    removes afterwards.
    """
    steps = workflow["jobs"]["pilot"]["steps"]
    names = [row.get("name") for row in steps]
    if GRANT_STEP not in names:
        return ["the release has no step that applies the packaged grants after the deploy"]
    step = steps[names.index(GRANT_STEP)]
    problems = []
    if DEPLOY_STEP not in names or names.index(GRANT_STEP) < names.index(DEPLOY_STEP):
        problems.append("the grant step does not run after the deploy")
    if step.get("if") != "inputs.operation == 'deploy'":
        problems.append("the grant step is not limited to a deployment")
    environment = step.get("env", {})
    if environment.get("GRANT_COMMAND") != " ".join(container_check.POST_DEPLOY_GRANT_COMMAND):
        problems.append("the grant step does not run the command the container check qualified")
    if environment.get("PACKAGED_MANIFEST") != container_check.IMAGE_MANIFEST_PATH:
        problems.append("the grant step does not require the manifest packaged in the image")
    if environment.get("FLY_API_TOKEN") != "${{ secrets.FLY_API_TOKEN }}":
        problems.append("the grant step does not hold its own step-scoped Fly credential")
    run = step.get("run", "")
    required = ('set -euo pipefail', 'flyctl machine list --app "${FLY_APP}" --json',
                'length == 1 and .[0].state == "started"', GRANT_CALL,
                'service_host_grant_application/v1', READINESS)
    problems += [f"the grant step does not contain {text}" for text in required if text not in run]
    if "flyctl ssh" in run:
        problems.append("the grant step opens a remote shell, which adds a WireGuard peer on every run")
    if GRANT_GATE.search(run) is None:
        problems.append("the grant step does not gate on what the grant command printed")
    elif GRANT_CALL in run and run.rfind(READINESS) < run.find(GRANT_CALL):
        problems.append("the readiness check does not follow the grant command")
    return problems


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
        deploy = next(row["run"] for row in self.steps if row["name"] == DEPLOY_STEP)
        for required in ("--ha=false", "--strategy immediate", "--deploy-retries 0", "--no-public-ips", "@sha256:"):
            self.assertIn(required, deploy)
        self.assertNotIn("flyctl launch", str(self.workflow))
        self.assertIn(READINESS, deploy)
        self.assertIn(".result.ready == true", job["env"]["SERVICE_READINESS_GATE"])

    def test_the_deploy_health_gate_accepts_what_the_service_actually_serves(self):
        """Run the workflow's own filter over a health record the code produced.

        A gate written against a health record the service no longer serves
        fails every deployment after a successful release, and a gate that
        accepts anything passes a machine that can serve nobody. Both are
        caught here by running the exact filter from the workflow, first over a
        real ready record and then over the known-wrong case of one that is not
        ready. The deploy step and the grant step both end with that one gate.
        """
        if shutil.which("jq") is None:
            self.skipTest("jq is required to run the workflow's own health gate")
        gate = self.workflow["jobs"]["pilot"]["env"]["SERVICE_READINESS_GATE"]
        for name in (DEPLOY_STEP, GRANT_STEP):
            with self.subTest(step=name):
                self.assertIn(READINESS, next(row["run"] for row in self.steps if row["name"] == name))

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
        # Each known-wrong record below differs from the real ready record in
        # one statement, and each one is refused by a different part of the
        # gate. A record that names no required check would otherwise pass,
        # because every member of an empty list passes.
        first_required = next(index for index, row in enumerate(ready["checks"]) if row["required"])
        known_wrong = {
            "the retired health record": {**ready, "record_type": "service_health/v1"},
            "a process that is not alive": {**ready, "alive": False},
            "a record that says it is not ready": {**ready, "ready": False},
            "readiness that was not checked": {**ready, "readiness_checked": False},
            "a required check that failed": {**ready, "checks": [
                {**row, "passed": False} if index == first_required else row
                for index, row in enumerate(ready["checks"])]},
            "no required check": {**ready, "checks": [{**row, "required": False} for row in ready["checks"]]},
            "no check at all": {**ready, "checks": []},
        }
        for name, record in known_wrong.items():
            with self.subTest(known_wrong=name):
                self.assertNotEqual(run_gate(record), 0)

    def test_the_release_applies_the_packaged_grants_on_the_one_machine_after_the_deploy(self):
        """Fly release 12 offered nothing until the grants were applied by hand.

        The step now runs in the guarded workflow itself. Removing it, moving
        it before the deploy, changing its command or dropping its final
        readiness check fails here.
        """
        self.assertEqual(grant_step_problems(self.workflow), [])

    def test_a_workflow_without_a_complete_grant_step_is_refused(self):
        def changed(edit):
            workflow = copy.deepcopy(self.workflow)
            edit(workflow["jobs"]["pilot"]["steps"])
            return grant_step_problems(workflow)

        def step(steps):
            return next(row for row in steps if row.get("name") == GRANT_STEP)

        def remove(steps):
            steps.remove(step(steps))

        def before_the_deploy(steps):
            moved = step(steps)
            steps.remove(moved)
            steps.insert(0, moved)

        def configure_instead(steps):
            step(steps)["env"]["GRANT_COMMAND"] = "loop-engine service configure --config /data/host.json"

        def without_readiness(steps):
            step(steps)["run"] = step(steps)["run"].replace(READINESS, ">/dev/null")

        def without_the_output_gate(steps):
            step(steps)["run"] = GRANT_GATE.sub("cat >/dev/null", step(steps)["run"])

        def any_machine(steps):
            step(steps)["run"] = step(steps)["run"].replace('exec "${machine}" ', "exec ")

        def through_a_remote_shell(steps):
            step(steps)["run"] = step(steps)["run"].replace(
                GRANT_CALL, 'flyctl ssh console --app "${FLY_APP}" --machine "${machine}" --quiet '
                            '--command "${GRANT_COMMAND}"')

        def readiness_before_the_grant(steps):
            run = step(steps)["run"]
            readiness = next(line for line in run.splitlines() if READINESS in line)
            step(steps)["run"] = run.replace(readiness, "true").replace(
                "applied=", f"{readiness.strip()}\napplied=", 1)

        for mutant in (remove, before_the_deploy, configure_instead, without_readiness,
                       without_the_output_gate, any_machine, through_a_remote_shell,
                       readiness_before_the_grant):
            with self.subTest(mutant=mutant.__name__):
                self.assertNotEqual(changed(mutant), [])

    def test_the_grant_gate_accepts_what_apply_grants_prints_and_refuses_known_wrong_output(self):
        """Run the workflow's own gate over what the real command prints for the release manifest.

        The command is the service's own apply-grants entry point, run over a
        copy of the packaged manifest whose artifact root is the release folder
        in this repository. Its output reaches the gate the way the exec call
        returns it. Each known-wrong record differs from the real one in one
        field, and the gate must refuse every one of them, and every answer
        whose exit code is not zero.
        """
        if shutil.which("jq") is None:
            self.skipTest("jq is required to run the workflow's own grant gate")
        from loop_engine.core.service_runtime.http_entrypoint import configure_host, main as service_main
        run = next(row["run"] for row in self.steps if row["name"] == GRANT_STEP)
        gate = GRANT_GATE.search(run).group(1)
        packaged = json.loads((ROOT / container_check.CATALOGUE_MANIFEST).read_text("utf-8"))
        tenants = sorted({grant["tenant_id"] for row in packaged["items"] for grant in row["grants"]})
        with tempfile.TemporaryDirectory(prefix="fly-grant-gate-") as directory:
            root = Path(directory)
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({**packaged, "artifact_root": str(
                (ROOT / container_check.CATALOGUE_MANIFEST).parent)}), "utf-8")
            host = container_check.packaged_catalogue_host_configuration(tenants)
            host["runtime"]["database_path"] = str(root / "service.db")
            host["manifest_path"] = str(manifest)
            configuration = root / "host.json"
            configuration.write_text(json.dumps(host), "utf-8")
            configure_host(str(configuration))
            printed = io.StringIO()
            with redirect_stdout(printed):
                self.assertEqual(service_main(["apply-grants", "--config", str(configuration)]), 0)
        printed = printed.getvalue()
        record = json.loads(printed)

        def run_gate(text, manifest_path=str(manifest)):
            return subprocess.run(["jq", "-e", "--arg", "manifest", manifest_path, gate],
                                  input=text, capture_output=True, text=True, timeout=10).returncode

        self.assertEqual(record["granted_items_by_tenant"],
                         {name: sum(1 for row in packaged["items"]
                                    if any(grant["tenant_id"] == name for grant in row["grants"]))
                          for name in tenants})
        self.assertEqual(printed.count("\n"), 1, "the grant command prints one line")
        self.assertEqual(run_gate(exec_output(stdout=printed)), 0, "the gate refused what the grant command prints")
        self.assertEqual(run_gate(exec_output(exit_code=0, stdout=printed, stderr="a warning\n")), 0,
                         "the gate refused a stated exit code of zero or a warning on the error stream")
        known_wrong = {
            "a tenant registered": {**record, "tenants_registered": 1},
            "no tenant granted anything": {**record, "granted_items_by_tenant": {}},
            "a tenant granted nothing": {**record, "granted_items_by_tenant": {tenants[0]: 0}},
            "the grants as a list": {**record, "granted_items_by_tenant": [len(packaged["items"])]},
            "a count written as text": {**record, "granted_items_by_tenant": {
                name: str(count) for name, count in record["granted_items_by_tenant"].items()}},
            "another manifest": {**record, "manifest_path": "/data/manifest.json"},
            "another record": {**record, "record_type": "service_host_setup/v1"},
            "a remote account created": {**record, "remote_accounts_created": True},
        }
        for name, value in known_wrong.items():
            with self.subTest(known_wrong=name):
                self.assertNotEqual(run_gate(exec_output(stdout=json.dumps(value) + "\n")), 0)
        for name, text in (("nothing printed", exec_output()),
                           ("the record twice", exec_output(stdout=printed + printed)),
                           ("the record, then a failure", exec_output(exit_code=1, stdout=printed)),
                           ("a failure only", exec_output(exit_code=1, stderr="Traceback (most recent call last):\n")),
                           ("the record as plain text", printed),
                           ("an error of the command line tool", "Error: could not exec command on machine\n")):
            with self.subTest(known_wrong=name):
                self.assertNotEqual(run_gate(text), 0)

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

    def test_the_post_deploy_command_runs_the_grant_command_as_the_service_user(self):
        """Exactly the service's own apply-grants command, run as the user the image runs as."""
        command = container_check.POST_DEPLOY_GRANT_COMMAND
        self.assertEqual(command[command.index("loop-engine"):],
                         ("loop-engine", "service", "apply-grants", "--config", "/data/host.json"))
        self.assertEqual(command[:command.index("loop-engine")],
                         ("setpriv", f"--reuid={container_check.SERVICE_USER}",
                          f"--regid={container_check.SERVICE_USER}", "--clear-groups"))
        self.assertIn(f"USER {container_check.SERVICE_USER}:{container_check.SERVICE_USER}",
                      (ROOT / "Dockerfile.service").read_text("utf-8"))

    def test_the_grant_command_reads_the_same_however_the_exec_call_splits_it(self):
        """The exec call receives one line of text and splits it into words itself.

        A word holding a space, a quotation mark or shell syntax could be split
        or read differently on the Machine than in the container check, so the
        command holds none, and splitting the workflow's line on spaces gives
        back exactly the words the container check ran.
        """
        command = container_check.POST_DEPLOY_GRANT_COMMAND
        line = " ".join(command)
        self.assertEqual(tuple(line.split(" ")), command)
        for word in command:
            with self.subTest(word=word):
                self.assertRegex(word, r"^[A-Za-z0-9/=._-]+$")
        known_wrong = (*command[:-1], "/data/host file.json")
        self.assertNotEqual(tuple(" ".join(known_wrong).split(" ")), known_wrong)

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
