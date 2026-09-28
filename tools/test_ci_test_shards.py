"""Every tools test module runs in exactly one continuous integration shard, on every Python version.

Roadmap step S-6.200. tools/run_test_shard.py places the tools test modules in the shards that tools/ci_test_shards.json
names, at run time, from recorded timings; .github/workflows/ci.yml runs each shard as a job and tools/pre_push_check.sh
runs the same shards before a push. Each rule below refuses one way a test could stop running or a merge could
conflict again: a module placed in no shard or in two, a placement that changes with the order of discovery, a
manifest that lists modules again (the lists conflicted on every merge that added a test until September 27, 2026), a
shard the workflow never runs, a Python version the matrix dropped, and a workflow step the pre-push script neither
runs nor declines with a reason. Each rule has a known-wrong control.
"""
from __future__ import annotations

import copy
from pathlib import Path
import random
import re
import unittest

import yaml

from run_test_shard import MANIFEST, TOOLS, current_plan, discovered_test_modules, load_manifest, plan, recorded_seconds

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
PRE_PUSH = ROOT / "tools" / "pre_push_check.sh"
PYTHON_VERSIONS = ["3.10", "3.11", "3.12"]
#: The workflow job that runs the shards, and the runner call each shard job must make.
SHARD_JOB = "unit-tests"
RUNNER_CALL = "tools/run_test_shard.py --shard ${{ matrix.shard }}"
#: Jobs whose steps the pre-push script does not mirror: the manual live run and the artifact build.
UNMIRRORED_JOBS = {"live-ollama", "build"}
#: A line of the pre-push script: gate "local name" "CI step name" command..., skip "CI step name" "reason",
#: setup "CI step name" command..., or local "local name" "what it checks" command... A gate, a skip or a setup
#: ties the line to one step of the workflow; a local gate checks something continuous integration does not run.
SCRIPT_LINE = re.compile(r'^[ \t]*(gate|skip|setup|local) "([^"]+)"(?: "([^"]+)")?', re.MULTILINE)
#: The most the heaviest shard's estimate may exceed an even division before the placement counts as unbalanced.
BALANCE_SLACK = 1.15


def manifest_problems(manifest: dict) -> list:
    """What is wrong with the version 2 manifest, or nothing."""
    problems = []
    if "measured_seconds" in manifest or any(isinstance(value, (list, dict)) and key not in ("shards", "discovery")
                                             for key, value in manifest.items()):
        problems.append("the manifest holds per-shard numbers; they are computed at run time")
    shards = manifest.get("shards")
    if isinstance(shards, dict):
        problems.append("the manifest lists modules under shards; placement is computed at run time, and the lists "
                        "conflicted on every merge that added a test")
    elif not isinstance(shards, list) or not shards or len(set(shards)) != len(shards):
        problems.append("the manifest names its shards as a list of distinct names")
    if not sorted(ROOT.glob(str(manifest.get("timings") or "-"))):
        problems.append(f"no timing record matches {manifest.get('timings')!r}")
    return problems


def placement_problems(placed: dict, discovered: list) -> list:
    """What is wrong with a placement against the modules discovery finds, or nothing."""
    problems = []
    seen = {}
    for name, members in placed.items():
        for module in members:
            seen.setdefault(module, []).append(name)
    problems += [f"{module} is in no shard" for module in discovered if module not in seen]
    problems += [f"{module} is in more than one shard: {', '.join(names)}" for module, names in seen.items()
                 if len(names) > 1]
    problems += [f"{module} is placed but discovery does not find it" for module in seen if module not in discovered]
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
    """Every run step of the mirrored jobs is a gate, a setup line or a declined step of the script, every step the
    script names exists in the workflow, and every local gate says what it checks."""
    problems = []
    steps = workflow_run_steps(workflow)
    named = {}
    for kind, first, second in SCRIPT_LINE.findall(script):
        if kind == "local":
            if not second:
                problems.append(f"the local gate {first!r} does not say what it checks")
            continue
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


class ShardPlacementTests(unittest.TestCase):
    def setUp(self):
        self.manifest = load_manifest(MANIFEST)
        self.discovered = discovered_test_modules(TOOLS)
        self.seconds = recorded_seconds(self.manifest)
        self.workflow = WORKFLOW.read_text(encoding="utf-8")
        self.script = PRE_PUSH.read_text(encoding="utf-8")

    def test_the_manifest_names_shards_and_timings_and_lists_no_module(self):
        self.assertEqual(manifest_problems(self.manifest), [])

    def test_every_test_module_is_in_exactly_one_shard(self):
        self.assertIn("test_ci_test_shards", self.discovered)
        placed, _estimates, _weights = current_plan(self.manifest)
        self.assertEqual(placement_problems(placed, self.discovered), [])

    def test_the_placement_does_not_depend_on_the_order_of_discovery(self):
        expected = plan(self.discovered, self.manifest["shards"], self.seconds)
        shuffled = list(self.discovered)
        random.Random(20260927).shuffle(shuffled)
        self.assertEqual(plan(shuffled, self.manifest["shards"], self.seconds), expected)

    def test_a_new_module_is_placed_without_a_change_to_any_committed_file(self):
        before = MANIFEST.read_bytes()
        placed, _estimates, weights = plan(self.discovered + ["test_a_module_added_later"], self.manifest["shards"],
                                           self.seconds)
        self.assertEqual(placement_problems(placed, self.discovered + ["test_a_module_added_later"]), [])
        self.assertEqual(MANIFEST.read_bytes(), before)
        self.assertGreater(weights["test_a_module_added_later"], 0)

    def test_the_shards_are_balanced_on_the_recorded_times(self):
        _placed, estimates, weights = current_plan(self.manifest)
        even = sum(weights.values()) / len(estimates)
        self.assertLessEqual(max(estimates.values()), max(even * BALANCE_SLACK, max(weights.values())), estimates)

    def test_the_workflow_runs_every_shard_on_every_python_version(self):
        self.assertEqual(workflow_problems(self.workflow, list(self.manifest["shards"])), [])

    def test_the_pre_push_script_accounts_for_every_workflow_step(self):
        self.assertEqual(pre_push_problems(self.script, self.workflow), [])

    def test_the_pre_push_script_runs_the_shards_through_the_runner(self):
        self.assertIn("tools/run_test_shard.py --list", self.script)
        self.assertIn('tools/run_test_shard.py --shard "$shard"', self.script)

    def test_known_wrong_a_manifest_that_lists_modules_again_is_found(self):
        old = copy.deepcopy(self.manifest)
        old["shards"] = {name: [] for name in self.manifest["shards"]}
        old["measured_seconds"] = {name: 0.0 for name in self.manifest["shards"]}
        problems = manifest_problems(old)
        self.assertTrue(any("lists modules under shards" in p for p in problems), problems)
        self.assertTrue(any("per-shard numbers" in p for p in problems), problems)

    def test_known_wrong_a_module_in_no_shard_or_in_two_is_found(self):
        placed, _estimates, _weights = current_plan(self.manifest)
        names = list(placed)
        dropped = {name: [m for m in members if m != "test_ci_test_shards"] for name, members in placed.items()}
        self.assertIn("test_ci_test_shards is in no shard", placement_problems(dropped, self.discovered))
        doubled = {name: list(members) for name, members in placed.items()}
        for name in names[:2]:
            doubled[name] = sorted(set(doubled[name]) | {"test_ci_test_shards"})
        self.assertTrue(any("more than one shard" in p for p in placement_problems(doubled, self.discovered)))
        extra = {name: list(members) for name, members in placed.items()}
        extra[names[0]] = extra[names[0]] + ["test_absent_module"]
        self.assertTrue(any("discovery does not find it" in p for p in placement_problems(extra, self.discovered)))

    def test_known_wrong_a_shard_the_workflow_never_runs_is_found(self):
        names = list(self.manifest["shards"])
        self.assertTrue(workflow_problems(self.workflow, names + ["zz"]))

    def test_known_wrong_a_dropped_python_version_is_found(self):
        changed = self.workflow.replace('python-version: ["3.10", "3.11", "3.12"]\n        shard:',
                                        'python-version: ["3.11", "3.12"]\n        shard:', 1)
        self.assertNotEqual(changed, self.workflow)
        problems = workflow_problems(changed, list(self.manifest["shards"]))
        self.assertTrue(any("does not keep Python" in p for p in problems), problems)

    def test_known_wrong_a_shard_job_without_the_runner_is_found(self):
        changed = self.workflow.replace(RUNNER_CALL, "tools/run_test_shard.py --list", 1)
        self.assertNotEqual(changed, self.workflow)
        problems = workflow_problems(changed, list(self.manifest["shards"]))
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
