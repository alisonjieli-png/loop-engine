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
READINESS_SETTING = "SERVICE_READINESS_GATE"
READINESS = 'jq -e "${SERVICE_READINESS_GATE}" >/dev/null'
#: The grant command reaches the one Machine through the Machines API exec
#: call, the way it was run by hand after release 12. The JSON form carries the
#: command's exit code and its exact standard output, with nothing of the
#: command line tool's own mixed in.
GRANT_CALL = 'flyctl machine exec "${machine}" "${GRANT_COMMAND}" --app "${FLY_APP}" --json'
GRANT_GATE = re.compile(r"""jq -e --arg manifest "\$\{PACKAGED_MANIFEST\}" '(.+?)' >/dev/null""")
BILLING_STEP = "Apply the host billing policy on the one Machine"
BILLING_CALL = 'flyctl machine exec "${machine}" "${BILLING_POLICY_COMMAND}" --app "${FLY_APP}" --json'
#: The billing step reads three filters out of its script: the gate on what the
#: command printed, the filter that takes from that record what the host file
#: offers, and the gate on the live capabilities record.
BILLING_GATE = re.compile(r"""\| jq -e '(.+?)' >/dev/null""")
EXPECTED_FILTER = re.compile(r"""\| jq -e -c '(.+?)'\)""")
CAPABILITIES_GATE = re.compile(r"""jq -e --argjson expected "\$\{expected\}" '(.+?)' >/dev/null""")
CAPABILITIES_READ = '"https://${FLY_APP}.fly.dev/api/v1/capabilities"'


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
    if step.get("continue-on-error", "false") != "false":
        problems.append("a failed grant step would not stop the release")
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


def billing_step_problems(workflow):
    """Every way the release's post-deploy billing policy step falls short, or nothing.

    Fly release 13 served for a day with checkout and the portal unavailable,
    because the stored session policy held the digest an older release
    computed and nothing applied the policy again. The step must exist, follow
    the grant step, run the exact command the container check qualified on the
    one started Machine without --reset-paid-access, gate on what that command
    printed, require the live capabilities record to report checkout and the
    portal as the host file offers them, and end with the shared readiness
    check. It must not open a remote shell.
    """
    steps = workflow["jobs"]["pilot"]["steps"]
    names = [row.get("name") for row in steps]
    if BILLING_STEP not in names:
        return ["the release has no step that applies the host billing policy after the deploy"]
    step = steps[names.index(BILLING_STEP)]
    problems = []
    if DEPLOY_STEP not in names or GRANT_STEP not in names or not (
            names.index(DEPLOY_STEP) < names.index(GRANT_STEP) < names.index(BILLING_STEP)):
        problems.append("the billing policy step does not run after the deploy and the grant step")
    if step.get("if") != "inputs.operation == 'deploy'":
        problems.append("the billing policy step is not limited to a deployment")
    if step.get("continue-on-error", "false") != "false":
        problems.append("a failed billing policy step would not stop the release")
    environment, run = step.get("env", {}), step.get("run", "")
    if environment.get("BILLING_POLICY_COMMAND") != " ".join(container_check.POST_DEPLOY_BILLING_POLICY_COMMAND):
        problems.append("the billing policy step does not run the command the container check qualified")
    commands = "\n".join(line for line in run.splitlines() if not line.strip().startswith("#"))
    if "--reset-paid-access" in environment.get("BILLING_POLICY_COMMAND", "") + commands:
        problems.append("the release could end paid access without an operator deciding it")
    if environment.get("FLY_API_TOKEN") != "${{ secrets.FLY_API_TOKEN }}":
        problems.append("the billing policy step does not hold its own step-scoped Fly credential")
    required = ('set -euo pipefail', 'flyctl machine list --app "${FLY_APP}" --json',
                'length == 1 and .[0].state == "started"', BILLING_CALL,
                'service_billing_policy_application/v1', CAPABILITIES_READ, READINESS)
    problems += [f"the billing policy step does not contain {text}" for text in required if text not in run]
    if "flyctl ssh" in run:
        problems.append("the billing policy step opens a remote shell, which adds a WireGuard peer on every run")
    gate, expected, capabilities = BILLING_GATE.search(run), EXPECTED_FILTER.search(run), CAPABILITIES_GATE.search(run)
    if gate is None:
        problems.append("the billing policy step does not gate on what the command printed")
    if expected is None or capabilities is None:
        problems.append("the billing policy step does not compare the live capabilities with what the host file offers")
    if gate is not None and capabilities is not None and BILLING_CALL in run and READINESS in run:
        order = [run.find(BILLING_CALL), gate.start(), capabilities.start(), run.rfind(READINESS)]
        if order != sorted(order) or len(set(order)) != len(order):
            problems.append("the billing policy step does not read the command, then the capabilities, then readiness")
    return problems


def readiness_gate_problems(workflow):
    """Every way a release step could end without the one shared readiness gate deciding it, or nothing.

    The deploy step and the grant step both end with the gate that the job
    holds in SERVICE_READINESS_GATE. A step that sets that name again, in its
    own settings or in its script, runs a gate of its own under the shared
    name, and a step or a job that continues after an error lets a failed gate
    pass the release.
    """
    job = workflow["jobs"]["pilot"]
    problems = []
    if not job.get("env", {}).get(READINESS_SETTING):
        problems.append("the job holds no shared readiness gate")
    if job.get("continue-on-error", "false") != "false":
        problems.append("the job lets a failed step pass the release")
    for row in job["steps"]:
        name = row.get("name", "an unnamed step")
        run = row.get("run", "")
        if READINESS_SETTING in row.get("env", {}):
            problems.append(f"{name} replaces the shared readiness gate in its own settings")
        if READINESS_SETTING in run.replace(READINESS, ""):
            problems.append(f"{name} names the readiness gate outside the shared check")
        if READINESS in run and row.get("continue-on-error", "false") != "false":
            problems.append(f"{name} lets a failed readiness gate pass the release")
    return problems


def deploy_readiness_is_polled(workflow):
    """The deploy step reads the shared gate in a bounded retry loop, not once.

    A Machine that flyctl has just replaced is still starting when the command
    returns. Release 13 was deployed and healthy, yet its workflow failed because
    its only readiness read came a second after the restart. The read must sit
    inside a loop with a pause and a fixed number of attempts, and the step must
    fail when no attempt passed.
    """
    step = next(row for row in workflow["jobs"]["pilot"]["steps"]
                if row.get("name") == "Publish and deploy the exact tested image")
    run = step.get("run", "")
    loop = re.search(r"for attempt in \$\(seq 1 (\d+)\)", run)
    pause = re.search(r"\n\s*sleep (\d+)\s*\n", run)
    gate = run.find(READINESS)
    # At least a minute in total, so a Machine that is still starting has time to answer.
    return (loop is not None and pause is not None and gate > loop.start()
            and int(loop.group(1)) * int(pause.group(1)) >= 60 and int(loop.group(1)) >= 2
            and '[[ "${ready}" == true ]]' in run[gate:])


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
        for name in (DEPLOY_STEP, GRANT_STEP, BILLING_STEP):
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

        def continue_after_a_failure(steps):
            # A failed gate would no longer stop the release, so a release that
            # offers nothing would still end as a success.
            step(steps)["continue-on-error"] = "true"

        for mutant in (remove, before_the_deploy, configure_instead, without_readiness,
                       without_the_output_gate, any_machine, through_a_remote_shell,
                       readiness_before_the_grant, continue_after_a_failure):
            with self.subTest(mutant=mutant.__name__):
                self.assertNotEqual(changed(mutant), [])

    def test_every_release_step_ends_with_the_one_shared_readiness_gate(self):
        """The deploy step and the grant step decide readiness with the gate the job holds."""
        self.assertEqual(readiness_gate_problems(self.workflow), [])

    def test_a_step_that_replaces_or_ignores_the_shared_readiness_gate_is_refused(self):
        """Each known-wrong workflow ends a release step with something other than the shared gate.

        The gate is one setting of the job, so a step could set the same name
        again, in its own settings or in its script, and pass a record that the
        shared gate refuses. A step or a job that continues after an error lets
        a failed gate pass the release. The gate tests above run the job's
        setting, so none of these would be noticed there.
        """
        def changed(edit):
            workflow = copy.deepcopy(self.workflow)
            edit(workflow["jobs"]["pilot"])
            return readiness_gate_problems(workflow)

        def step(job, name):
            return next(row for row in job["steps"] if row.get("name") == name)

        def own_gate_in_the_settings(name):
            def edit(job):
                step(job, name).setdefault("env", {})["SERVICE_READINESS_GATE"] = "true"
            return edit

        def own_gate_in_the_script(name):
            def edit(job):
                row = step(job, name)
                row["run"] = row["run"].replace(
                    "set -euo pipefail", "set -euo pipefail\nSERVICE_READINESS_GATE=true", 1)
            return edit

        def continues_after_an_error(name):
            def edit(job):
                step(job, name)["continue-on-error"] = "true"
            return edit

        def no_shared_gate(job):
            del job["env"]["SERVICE_READINESS_GATE"]

        def the_job_continues_after_an_error(job):
            job["continue-on-error"] = "true"

        mutants = {"no shared gate": no_shared_gate,
                   "the job continues after an error": the_job_continues_after_an_error}
        for name in (DEPLOY_STEP, GRANT_STEP, BILLING_STEP):
            mutants[f"{name}: its own gate in its settings"] = own_gate_in_the_settings(name)
            mutants[f"{name}: its own gate in its script"] = own_gate_in_the_script(name)
            mutants[f"{name}: continues after an error"] = continues_after_an_error(name)
        for label, edit in mutants.items():
            with self.subTest(mutant=label):
                self.assertNotEqual(changed(edit), [])

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

    def test_the_release_applies_the_host_billing_policy_after_the_grants(self):
        """Fly release 13 kept checkout unavailable because nothing applied the billing policy again."""
        self.assertEqual(billing_step_problems(self.workflow), [])

    def test_a_workflow_without_a_complete_billing_policy_step_is_refused(self):
        def changed(edit):
            workflow = copy.deepcopy(self.workflow)
            edit(workflow["jobs"]["pilot"]["steps"])
            return billing_step_problems(workflow)

        def step(steps):
            return next(row for row in steps if row.get("name") == BILLING_STEP)

        def edit_run(function):
            def edit(steps):
                step(steps)["run"] = function(step(steps)["run"])
            return edit

        def remove(steps):
            steps.remove(step(steps))

        def moved_to(position):
            def edit(steps):
                moved = step(steps)
                steps.remove(moved)
                names = [row.get("name") for row in steps]
                steps.insert(names.index(GRANT_STEP) if position == "grant" else 0, moved)
            return edit

        def command(text):
            def edit(steps):
                step(steps)["env"]["BILLING_POLICY_COMMAND"] = text
            return edit

        def capabilities_before_the_command(run):
            lines = run.splitlines()
            start = next(index for index, line in enumerate(lines) if CAPABILITIES_READ in line)
            moved = lines[start:start + 2]
            del lines[start:start + 2]
            at = next(index for index, line in enumerate(lines) if line.strip().startswith("applied="))
            return "\n".join(lines[:at] + moved + lines[at:])

        def continue_after_a_failure(steps):
            step(steps)["continue-on-error"] = "true"

        mutants = {
            "removed": remove, "before the grant step": moved_to("grant"), "before the deploy": moved_to("start"),
            "configure instead": command("loop-engine service configure --config /data/host.json"),
            "ends paid access": command(" ".join(container_check.POST_DEPLOY_BILLING_POLICY_COMMAND)
                                        + " --reset-paid-access"),
            "without readiness": edit_run(lambda run: run.replace(READINESS, ">/dev/null")),
            "without the output gate": edit_run(lambda run: BILLING_GATE.sub("| cat >/dev/null", run)),
            "without the capabilities gate": edit_run(lambda run: CAPABILITIES_GATE.sub("cat >/dev/null", run)),
            "any machine": edit_run(lambda run: run.replace('exec "${machine}" ', "exec ")),
            "through a remote shell": edit_run(lambda run: run.replace(
                BILLING_CALL, 'flyctl ssh console --app "${FLY_APP}" --command "${BILLING_POLICY_COMMAND}"')),
            "capabilities read before the command": edit_run(capabilities_before_the_command),
            "continues after a failure": continue_after_a_failure}
        for name, mutant in mutants.items():
            with self.subTest(mutant=name):
                self.assertNotEqual(changed(mutant), [])

    def test_the_billing_gates_accept_what_the_service_answers_and_refuse_the_release_13_state(self):
        """Run the step's own three filters over what the real command prints and the real service serves.

        The service starts first and keeps running, as the deployed Machine
        does, with the session terms an older release stored. The command then
        runs as a separate call through the service entry point. Its record
        must pass the output gate, the filter must read from it what the host
        file offers, and the capabilities gate must refuse the capabilities the
        service served before the command and accept the ones it serves after.
        """
        if shutil.which("jq") is None:
            self.skipTest("jq is required to run the workflow's own billing gates")
        from loop_engine.core.service_runtime import billing_policy_checks as fixtures
        from loop_engine.core.service_runtime.http_entrypoint import main as service_main
        run = next(row["run"] for row in self.steps if row["name"] == BILLING_STEP)
        gate, offered = BILLING_GATE.search(run).group(1), EXPECTED_FILTER.search(run).group(1)
        capabilities_gate = CAPABILITIES_GATE.search(run).group(1)

        def jq(program, text, *arguments):
            return subprocess.run(["jq", "-e", *arguments, program], input=text, capture_output=True,
                                  text=True, timeout=10)

        def command(path):
            printed = io.StringIO()
            with redirect_stdout(printed):
                self.assertEqual(service_main(["apply-billing-policy", "--config", str(path)]), 0)
            return printed.getvalue()

        with tempfile.TemporaryDirectory(prefix="fly-billing-gate-") as directory:
            root = Path(directory)
            (root / "offered").mkdir()
            (root / "withheld").mkdir()
            path, running = fixtures.configured(root / "offered")
            fixtures.plant_older_terms(running)
            drifted = fixtures.served(running, "/api/v1/capabilities")
            printed = command(path)
            repaired = fixtures.served(running, "/api/v1/capabilities")
            withheld_path, withheld_service = fixtures.configured(root / "withheld", sessions={"allow_network": False})
            withheld_printed = command(withheld_path)
            withheld = fixtures.served(withheld_service, "/api/v1/capabilities")
            fixtures.rewrite(withheld_path, lambda host: host["billing"]["sessions"]["plans"].append(
                {"plan_ref": "team", "label": "Team", "price_id": "price_other"}))
            refused = io.StringIO()
            with redirect_stdout(refused):
                self.assertEqual(service_main(["apply-billing-policy", "--config", str(withheld_path)]), 1)
            refused = refused.getvalue()
        record = json.loads(printed)
        self.assertEqual(printed.count("\n"), 1, "the billing policy command prints one line")
        self.assertEqual(jq(gate, exec_output(stdout=printed)).returncode, 0, "the gate refused what the command prints")
        self.assertEqual(jq(gate, exec_output(exit_code=0, stdout=printed, stderr="a warning\n")).returncode, 0)
        known_wrong = {
            "a policy still not current": {**record, "every_installed_policy_current": False},
            "paid access ended": {**record, "paid_access_ended_for_accounts": 1},
            "a tenant registered": {**record, "tenants_registered": 1},
            "a remote account created": {**record, "remote_accounts_created": True},
            "a provider call": {**record, "provider_calls": 1},
            "another record": {**record, "record_type": "service_host_grant_application/v1"},
            "no statement of the offered checkout": {key: value for key, value in record.items()
                                                     if key != "checkout_expected"},
            "the offered checkout as text": {**record, "checkout_expected": "true"}}
        for name, value in known_wrong.items():
            with self.subTest(known_wrong=name):
                self.assertNotEqual(jq(gate, exec_output(stdout=json.dumps(value) + "\n")).returncode, 0)
        self.assertEqual(json.loads(refused)["code"], "session_price_not_in_billing_policy")
        for name, text in (("nothing printed", exec_output()),
                           ("the record twice", exec_output(stdout=printed + printed)),
                           ("the record, then a failure", exec_output(exit_code=1, stdout=printed)),
                           ("a refusal the command printed", exec_output(exit_code=1, stdout=refused)),
                           ("a refusal with a lost exit code", exec_output(stdout=refused)),
                           ("the record as plain text", printed),
                           ("an error of the command line tool", "Error: could not exec command on machine\n")):
            with self.subTest(known_wrong=name):
                self.assertNotEqual(jq(gate, text).returncode, 0)
        expected = jq(offered, exec_output(stdout=printed), "-c").stdout.strip()
        closed = jq(offered, exec_output(stdout=withheld_printed), "-c").stdout.strip()
        self.assertEqual((json.loads(expected), json.loads(closed)),
                         ({"checkout": True, "portal": True}, {"checkout": False, "portal": False}))

        def capabilities(served, wanted):
            return jq(capabilities_gate, json.dumps(served), "--argjson", "expected", wanted).returncode
        self.assertEqual(capabilities(repaired, expected), 0, "the gate refused the repaired service")
        self.assertNotEqual(capabilities(drifted, expected), 0, "the gate accepted the release 13 state")
        self.assertEqual(capabilities(withheld, closed), 0, "the gate refused a host that offers no checkout")
        self.assertNotEqual(capabilities(repaired, closed), 0, "the gate accepted checkout the host file withholds")
        other = {**repaired, "result": {**repaired["result"], "record_type": "service_capabilities/v2"}}
        self.assertNotEqual(capabilities(other, expected), 0, "the gate accepted another record version")

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
        """Exactly the service's own apply-grants and apply-billing-policy commands, run as the user the image runs as."""
        for name, command in (("apply-grants", container_check.POST_DEPLOY_GRANT_COMMAND),
                              ("apply-billing-policy", container_check.POST_DEPLOY_BILLING_POLICY_COMMAND)):
            with self.subTest(command=name):
                self.assertEqual(command[command.index("loop-engine"):],
                                 ("loop-engine", "service", name, "--config", "/data/host.json"))
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
        for command in (container_check.POST_DEPLOY_GRANT_COMMAND, container_check.POST_DEPLOY_BILLING_POLICY_COMMAND):
            line = " ".join(command)
            self.assertEqual(tuple(line.split(" ")), command)
            for word in command:
                with self.subTest(word=word):
                    self.assertRegex(word, r"^[A-Za-z0-9/=._-]+$")
        command = container_check.POST_DEPLOY_GRANT_COMMAND
        known_wrong = (*command[:-1], "/data/host file.json")
        self.assertNotEqual(tuple(" ".join(known_wrong).split(" ")), known_wrong)

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


    def test_the_deploy_step_polls_the_readiness_gate_until_a_deadline(self):
        self.assertTrue(deploy_readiness_is_polled(self.workflow))
        step = next(row for row in self.workflow["jobs"]["pilot"]["steps"]
                    if row.get("name") == "Publish and deploy the exact tested image")
        single = {**step, "run": step["run"].replace("for attempt in $(seq 1 ", "for attempt in $(seq 1 1) #")}
        once = copy.deepcopy(self.workflow)
        once["jobs"]["pilot"]["steps"] = [single if row is step else row for row in self.workflow["jobs"]["pilot"]["steps"]]
        self.assertFalse(deploy_readiness_is_polled(once), "a single read must be refused")
        unchecked = {**step, "run": step["run"].replace('[[ "${ready}" == true ]]', "true")}
        loose = copy.deepcopy(self.workflow)
        loose["jobs"]["pilot"]["steps"] = [unchecked if row is step else row for row in self.workflow["jobs"]["pilot"]["steps"]]
        self.assertFalse(deploy_readiness_is_polled(loose), "a loop whose failure is ignored must be refused")

if __name__ == "__main__":
    unittest.main()
