"""Every tools test module runs in exactly one continuous integration shard, on every Python version.

Roadmap step S-6.200. The manifest tools/ci_test_shards.json divides the tools test modules into shards that
.github/workflows/ci.yml runs as parallel jobs, and tools/pre_push_check.sh runs the same shards before a push.
Each rule below refuses one way a test could stop running: a module that no shard names, a module two shards
name (it would run twice and hide a flaky order), a shard the workflow never runs, a Python version the matrix
dropped, and a continuous integration step the pre-push script neither runs nor declines with a reason. Each
rule has a known-wrong control.
"""
from __future__ import annotations

from pathlib import Path
import re
import unittest

import yaml

from run_test_shard import MANIFEST, TOOLS, discovered_test_modules, load_manifest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
PRE_PUSH = ROOT / "tools" / "pre_push_check.sh"
PYTHON_VERSIONS = ["3.10", "3.11", "3.12"]
#: The workflow job that runs the shards, and the runner call each shard job must make.
SHARD_JOB = "unit-tests"
RUNNER_CALL = "tools/run_test_shard.py --shard ${{ matrix.shard }}"
#: Jobs whose steps the pre-push script does not mirror: the manual live run and the artifact build.
UNMIRRORED_JOBS = {"live-ollama", "build"}
#: A gate line of the pre-push script: gate "local name" "CI step name" command..., skip "CI step name" "reason",
#: or setup "CI step name" command... The CI step name ties every line to one step of the workflow.
SCRIPT_LINE = re.compile(r'^[ \t]*(gate|skip|setup) "([^"]+)"(?: "([^"]+)")?', re.MULTILINE)
REBALANCE = "python tools/balance_test_shards.py --add-missing --write"


def manifest_problems(manifest: dict, discovered: list) -> list:
    """What is wrong with the manifest against the modules discovery finds, or nothing."""
    problems = []
    shards = manifest.get("shards") or {}
    if not shards:
        return ["the manifest has no shards"]
    seen = {}
    for name, members in shards.items():
        for module in members:
            seen.setdefault(module, []).append(name)
    for module in discovered:
        if module not in seen:
            problems.append(f"{module} is in no shard; run {REBALANCE}")
    for module, names in seen.items():
        if len(names) > 1:
            problems.append(f"{module} is in more than one shard: {', '.join(names)}")
        if module not in discovered:
            problems.append(f"{module} is named by shard {names[0]} but discovery does not find it")
    for name, members in shards.items():
        if list(members) != sorted(members):
            problems.append(f"shard {name} is not sorted")
    return problems


def workflow_problems(text: str, shard_names: list) -> list:
    """What is wrong with the workflow against the manifest's shard names, or nothing."""
    problems = []
    data = yaml.safe_load(text)
    job = (data.get("jobs") or {}).get(SHARD_JOB)
    if not job:
        return [f"the workflow has no {SHARD_JOB} job"]
    matrix = ((job.get("strategy") or {}).get("matrix") or {})
    if sorted(str(item) for item in matrix.get("shard") or []) != sorted(shard_names):
        problems.append(f"the {SHARD_JOB} matrix does not list exactly the shards {', '.join(shard_names)}")
    if [str(item) for item in matrix.get("python-version") or []] != PYTHON_VERSIONS:
        problems.append(f"the {SHARD_JOB} matrix does not keep Python {', '.join(PYTHON_VERSIONS)}")
    if not any(RUNNER_CALL in str(step.get("run", "")) for step in job.get("steps") or []):
        problems.append(f"no {SHARD_JOB} step runs {RUNNER_CALL}")
    return problems


def workflow_run_steps(text: str) -> dict:
    """The names of the run steps and the named uses steps of every mirrored job: name to job."""
    data = yaml.safe_load(text)
    steps = {}
    for job_name, job in (data.get("jobs") or {}).items():
        if job_name in UNMIRRORED_JOBS:
            continue
        for step in job.get("steps") or []:
            if step.get("name") and ("run" in step or "uses" in step):
                steps[step["name"]] = job_name
    return steps


def pre_push_problems(script: str, workflow: str) -> list:
    """Every run step of the mirrored jobs is a gate, a setup line or a declined step of the script, and every
    step the script names exists in the workflow."""
    problems = []
    steps = workflow_run_steps(workflow)
    named = {}
    for kind, first, second in SCRIPT_LINE.findall(script):
        step = second if kind == "gate" else first
        named[step] = kind
        if kind == "skip" and not second:
            problems.append(f"the declined step {first!r} gives no reason")
    for step, job in steps.items():
        if step not in named:
            problems.append(f"the pre-push script neither runs nor declines the {job} step {step!r}")
    for step in named:
        if step not in steps:
            problems.append(f"the pre-push script names a step the workflow does not have: {step!r}")
    return problems


class ShardManifestTests(unittest.TestCase):
    def setUp(self):
        self.manifest = load_manifest(MANIFEST)
        self.discovered = discovered_test_modules(TOOLS)
        self.workflow = WORKFLOW.read_text(encoding="utf-8")
        self.script = PRE_PUSH.read_text(encoding="utf-8")

    def test_every_test_module_is_in_exactly_one_shard(self):
        self.assertIn("test_ci_test_shards", self.discovered)
        self.assertEqual(manifest_problems(self.manifest, self.discovered), [])

    def test_the_workflow_runs_every_shard_on_every_python_version(self):
        self.assertEqual(workflow_problems(self.workflow, sorted(self.manifest["shards"])), [])

    def test_the_pre_push_script_accounts_for_every_workflow_step(self):
        self.assertEqual(pre_push_problems(self.script, self.workflow), [])

    def test_the_pre_push_script_runs_the_shards_through_the_runner(self):
        self.assertIn("tools/run_test_shard.py --list", self.script)
        self.assertIn('tools/run_test_shard.py --shard "$shard"', self.script)

    def test_known_wrong_a_module_in_no_shard_is_found(self):
        changed = {"shards": {name: [m for m in members if m != "test_ci_test_shards"]
                              for name, members in self.manifest["shards"].items()}}
        problems = manifest_problems(changed, self.discovered)
        self.assertTrue(any(p.startswith("test_ci_test_shards is in no shard") for p in problems), problems)

    def test_known_wrong_a_module_in_two_shards_is_found(self):
        names = sorted(self.manifest["shards"])
        self.assertGreater(len(names), 1)
        changed = {"shards": {name: list(members) for name, members in self.manifest["shards"].items()}}
        changed["shards"][names[1]] = sorted(changed["shards"][names[1]] + ["test_ci_test_shards"])
        changed["shards"][names[0]] = sorted(set(changed["shards"][names[0]]) | {"test_ci_test_shards"})
        problems = manifest_problems(changed, self.discovered)
        self.assertTrue(any("more than one shard" in p for p in problems), problems)

    def test_known_wrong_a_module_discovery_does_not_find_is_found(self):
        changed = {"shards": {name: list(members) for name, members in self.manifest["shards"].items()}}
        first = sorted(changed["shards"])[0]
        changed["shards"][first] = sorted(changed["shards"][first] + ["test_absent_module"])
        problems = manifest_problems(changed, self.discovered)
        self.assertTrue(any("discovery does not find it" in p for p in problems), problems)

    def test_known_wrong_a_shard_the_workflow_never_runs_is_found(self):
        names = sorted(self.manifest["shards"])
        self.assertIn("a shard the workflow does not run", [
            "a shard the workflow does not run" if workflow_problems(self.workflow, names + ["zz"]) else "no problem"])

    def test_known_wrong_a_dropped_python_version_is_found(self):
        changed = self.workflow.replace('python-version: ["3.10", "3.11", "3.12"]\n        shard:',
                                        'python-version: ["3.11", "3.12"]\n        shard:', 1)
        self.assertNotEqual(changed, self.workflow)
        problems = workflow_problems(changed, sorted(self.manifest["shards"]))
        self.assertTrue(any("does not keep Python" in p for p in problems), problems)

    def test_known_wrong_a_shard_job_without_the_runner_is_found(self):
        changed = self.workflow.replace(RUNNER_CALL, "tools/run_test_shard.py --list", 1)
        self.assertNotEqual(changed, self.workflow)
        problems = workflow_problems(changed, sorted(self.manifest["shards"]))
        self.assertTrue(any("runs tools/run_test_shard.py" in p for p in problems), problems)

    def test_known_wrong_an_unaccounted_workflow_step_is_found(self):
        changed = self.script.replace('gate "self-test" "Self-test"', 'gate "self-test" "Renamed step"', 1)
        self.assertNotEqual(changed, self.script)
        problems = pre_push_problems(changed, self.workflow)
        self.assertTrue(any("'Self-test'" in p and "neither runs nor declines" in p for p in problems), problems)
        self.assertTrue(any("'Renamed step'" in p for p in problems), problems)

    def test_known_wrong_a_declined_step_without_a_reason_is_found(self):
        changed = re.sub(r'^skip "([^"]+)" "[^"]+"', r'skip "\1"', self.script, count=1, flags=re.MULTILINE)
        self.assertNotEqual(changed, self.script)
        problems = pre_push_problems(changed, self.workflow)
        self.assertTrue(any("gives no reason" in p for p in problems), problems)


if __name__ == "__main__":
    unittest.main()
