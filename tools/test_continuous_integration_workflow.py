"""Exercise the shell guards inside the continuous integration workflow.

Each guard is read from `.github/workflows/ci.yml` and run with bash, so the
test executes the same text the runner executes. The external commands that
would reach a search index, a renderer, or a server are replaced by small
programs with a chosen exit status, which is the behaviour under test.

The defects these tests hold closed are guards that report success without
having reached a conclusion: a search tool that could not search, an extraction
that produced nothing to render, and a readiness wait that ran out without
saying so.
"""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/ci.yml"

#: The jobs whose checks read the history the starter catalogue is anchored to. Until September 26, 2026 one suite job
#: named `test` ran every check; since then (roadmap S-6.200) these five jobs share that work, and each runs such checks.
HISTORY_JOBS = ("unit-tests", "runtime-checks", "self-test", "conformance", "component-guides")
#: The jobs that run once on every supported Python version, each version to its end.
MATRIX_JOBS = ("unit-tests", "runtime-checks")
PYTHON_VERSIONS = ["3.10", "3.11", "3.12"]

DIAGRAM_SOURCES = (
    "docs/components/self-improvement/README.md",
    "docs/components/intelligence-layers/INTELLIGENCE-AS-LOOPS.md",
    "docs/components/core-architecture/BRAVE-SEARCH-PLUGIN.md",
    "docs/components/core-architecture/MODEL-GATEWAY.md",
    "docs/components/loop-object/LOOP-PROFILE-ONTOLOGY.md",
)


def step_script(step_id):
    document = yaml.load(WORKFLOW.read_text(), Loader=yaml.BaseLoader)
    for job in document["jobs"].values():
        for row in job.get("steps", []):
            if row.get("id") == step_id:
                return row["run"]
    raise AssertionError(f"the workflow has no step with id {step_id!r}")


def embedded_python(step_id, mentioning):
    """The one `PY ... PY` program inside a step that names this text.

    The step around it installs a wheel and builds a virtual environment, which
    these checks do not repeat. The program is the part that decides, so it is
    taken out and decided on its own.
    """
    lines = step_script(step_id).splitlines()
    programs, current = [], None
    for line in lines:
        if current is None:
            if line.strip().endswith("<<'PY'"):
                current = []
            continue
        if line.strip() == "PY":
            programs.append("\n".join(current))
            current = None
            continue
        current.append(line)
    found = [program for program in programs if mentioning in program]
    if len(found) != 1:
        raise AssertionError(
            f"step {step_id!r} holds {len(found)} embedded programs naming {mentioning!r}, expected one")
    return textwrap.dedent(found[0])


class WorkflowGuardTestCase(unittest.TestCase):
    """Shared scaffolding: a temporary tree and a directory of stub commands."""

    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.workdir = Path(holder.name)
        self.stubs = self.workdir / "stubs"
        self.stubs.mkdir()
        self.runner_temp = self.workdir / "runner-temp"
        self.runner_temp.mkdir()

    def add_stub(self, name, body):
        path = self.stubs / name
        path.write_text(f"#!/usr/bin/env bash\n{body}\n")
        path.chmod(0o755)

    def run_script(self, script, cwd=None, environment=None, timeout=60):
        env = {
            "PATH": f"{self.stubs}:{os.environ['PATH']}",
            "RUNNER_TEMP": str(self.runner_temp),
            "HOME": str(self.workdir),
        }
        env.update(environment or {})
        # The runner's default shell for a run block, so -e is in force.
        return subprocess.run(["bash", "-e", "-o", "pipefail", "-c", script],
                              cwd=str(cwd or self.workdir), env=env,
                              capture_output=True, text=True, timeout=timeout)


class RetiredLanguageGuardTests(WorkflowGuardTestCase):
    """ripgrep answers 0 for a match, 1 for none, and 2 for a failed search."""

    @classmethod
    def setUpClass(cls):
        cls.guard = step_script("retired-language")

    def with_search_status(self, status):
        self.add_stub("rg", f'if [ "$1" = "--version" ]; then\n'
                            f'  echo "ripgrep 0.0.0 (test stub)"\n'
                            f'  exit 0\n'
                            f'fi\n'
                            f'exit {status}')

    def test_a_search_that_found_nothing_passes(self):
        self.with_search_status(1)
        finished = self.run_script(self.guard)
        self.assertEqual(finished.returncode, 0, finished.stdout + finished.stderr)

    def test_a_search_that_matched_fails_and_names_the_replacement_words(self):
        self.with_search_status(0)
        finished = self.run_script(self.guard)
        self.assertNotEqual(finished.returncode, 0)
        self.assertIn("Retired public language found", finished.stdout)

    def test_a_search_that_could_not_run_fails_instead_of_passing(self):
        self.with_search_status(2)
        finished = self.run_script(self.guard)
        self.assertNotEqual(finished.returncode, 0, finished.stdout)
        self.assertIn("ripgrep could not complete", finished.stdout)

    def test_the_failed_search_arm_is_the_reason_that_case_is_refused(self):
        lines = self.guard.splitlines()
        marker = next(index for index, line in enumerate(lines)
                      if "ripgrep could not complete" in line)
        # Restore the earlier behaviour: a failed search counted as "nothing
        # found". The guard must stop refusing the case once that arm is gone.
        mutant = "\n".join(lines[:marker] + ["              *) return 0 ;;"]
                           + lines[marker + 2:])
        self.with_search_status(2)
        self.assertNotEqual(self.run_script(self.guard).returncode, 0)
        self.assertEqual(self.run_script(mutant).returncode, 0)


class ArchitectureDiagramGuardTests(WorkflowGuardTestCase):
    """An extraction that produced nothing must not look like a rendered check."""

    @classmethod
    def setUpClass(cls):
        cls.guard = step_script("architecture-diagrams")

    def setUp(self):
        super().setUp()
        self.add_stub("npx", "exit 0")
        self.tree = self.workdir / "tree"
        for name in DIAGRAM_SOURCES:
            target = self.tree / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        (self.tree / ".github").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / ".github/puppeteer-config.json",
                        self.tree / ".github/puppeteer-config.json")

    def test_the_current_documents_all_yield_a_diagram(self):
        finished = self.run_script(self.guard, cwd=self.tree)
        self.assertEqual(finished.returncode, 0, finished.stdout + finished.stderr)
        for name in ("self-improvement", "intelligence-loops", "brave-plugin",
                     "model-gateway", "loop-profiles"):
            with self.subTest(diagram=name):
                self.assertTrue((self.runner_temp / f"{name}.mmd").stat().st_size)

    def test_a_document_whose_diagram_is_gone_fails_the_step(self):
        spoiled = self.tree / DIAGRAM_SOURCES[0]
        spoiled.write_text(spoiled.read_text().replace("```mermaid", "```text", 1))
        finished = self.run_script(self.guard, cwd=self.tree)
        self.assertNotEqual(finished.returncode, 0, finished.stdout)
        self.assertIn("No mermaid diagram was extracted", finished.stdout)

    def test_the_empty_extraction_check_is_the_reason_that_case_is_refused(self):
        self.assertIn('if [ ! -s "${RUNNER_TEMP}/${name}.mmd" ]; then', self.guard)
        lines = self.guard.splitlines()
        opening = next(index for index, line in enumerate(lines)
                       if '! -s "${RUNNER_TEMP}/${name}.mmd"' in line)
        closing = next(index for index in range(opening, len(lines))
                       if lines[index].strip() == "fi")
        mutant = "\n".join(lines[:opening] + lines[closing + 1:])
        spoiled = self.tree / DIAGRAM_SOURCES[0]
        spoiled.write_text(spoiled.read_text().replace("```mermaid", "```text", 1))
        self.assertNotEqual(self.run_script(self.guard, cwd=self.tree).returncode, 0)
        self.assertEqual(self.run_script(mutant, cwd=self.tree).returncode, 0)


class StudioReadinessGuardTests(WorkflowGuardTestCase):
    """A readiness wait that runs out must say so rather than carry on."""

    @classmethod
    def setUpClass(cls):
        cls.step = next(
            row["run"] for row in
            yaml.load(WORKFLOW.read_text(), Loader=yaml.BaseLoader)
            ["jobs"]["docs"]["steps"]
            if row.get("name") == "Verify interactive architecture and video")

    def readiness_fragment(self):
        lines = self.step.splitlines()
        start = next(index for index, line in enumerate(lines)
                     if line.strip() == "STUDIO_READY=no")
        end = next(index for index in range(start, len(lines))
                   if "node showcase/tests/studio-visual-audit.mjs" in lines[index])
        fragment = "\n".join(lines[start:end])
        self.assertIn("exit 1", fragment)
        return fragment

    # A background process that holds the captured pipes open would outlive
    # bash and hide the result, so each stand-in writes nowhere and is stopped.
    LIVE_SERVER = ("sleep 30 >/dev/null 2>&1 & STUDIO_PID=$!\n"
                   "trap 'kill $STUDIO_PID 2>/dev/null || true' EXIT\n")
    STOPPED_SERVER = ("sleep 0 >/dev/null 2>&1 & STUDIO_PID=$!\n"
                      "wait $STUDIO_PID\n")

    def setUp(self):
        super().setUp()
        self.add_stub("curl", "exit 7")
        (self.runner_temp / "studio-server.log").write_text(
            "the recorded reason the server stopped\n")

    def short_wait(self):
        return self.readiness_fragment().replace("$(seq 1 120)", "$(seq 1 2)")

    def test_a_server_that_stopped_is_reported_with_its_log(self):
        finished = self.run_script(self.STOPPED_SERVER + self.short_wait(),
                                   timeout=30)
        self.assertNotEqual(finished.returncode, 0)
        self.assertIn("stopped before it answered", finished.stdout)
        self.assertIn("the recorded reason the server stopped", finished.stdout)

    def test_running_out_of_time_fails_and_prints_the_log(self):
        finished = self.run_script(self.LIVE_SERVER + self.short_wait(), timeout=30)
        self.assertNotEqual(finished.returncode, 0)
        self.assertIn("did not answer", finished.stdout)
        self.assertIn("the recorded reason the server stopped", finished.stdout)

    def test_the_readiness_flag_is_the_reason_the_timeout_is_refused(self):
        fragment = self.short_wait()
        lines = fragment.splitlines()
        cut = next(index for index, line in enumerate(lines)
                   if 'if [ "$STUDIO_READY" != "yes" ]; then' in line)
        # Restore the earlier behaviour: the wait ran out and the step carried
        # on to the browser check as though the server had answered.
        mutant = "\n".join(lines[:cut])
        self.assertNotEqual(
            self.run_script(self.LIVE_SERVER + fragment, timeout=30).returncode, 0)
        self.assertEqual(
            self.run_script(self.LIVE_SERVER + mutant, timeout=30).returncode, 0)


def history_depth_problems(document, job_name):
    """Why one job cannot read the history its checks need, or an empty list."""
    checkouts = [row for row in document["jobs"][job_name].get("steps", [])
                 if str(row.get("uses", "")).startswith("actions/checkout@")]
    if not checkouts:
        return [f"the {job_name} job checks out nothing"]
    problems = []
    for index, row in enumerate(checkouts):
        depth = row.get("with", {}).get("fetch-depth")
        if depth != "0":
            problems.append(
                f"checkout {index} of the {job_name} job fetches depth {depth!r}, so a commit that is not "
                f"the head of the branch cannot be read")
    return problems


class WorkflowShapeTests(unittest.TestCase):
    def test_no_job_or_step_is_allowed_to_fail_quietly(self):
        document = yaml.load(WORKFLOW.read_text(), Loader=yaml.BaseLoader)
        text = WORKFLOW.read_text()
        self.assertNotIn("continue-on-error", text)
        # Every job with a matrix is named, so a new matrix job cannot slip past the rule below.
        with_matrix = sorted(name for name, job in document["jobs"].items() if "strategy" in job)
        self.assertEqual(with_matrix, sorted(MATRIX_JOBS))
        for name in MATRIX_JOBS:
            with self.subTest(job=name):
                strategy = document["jobs"][name]["strategy"]
                self.assertEqual(strategy["matrix"]["python-version"], PYTHON_VERSIONS)
                self.assertEqual(strategy["fail-fast"], "false")

    def test_an_installation_that_carries_no_studio_check_is_refused(self):
        """The known-wrong case: a report of nothing, which all_passed calls a pass.

        Every self-test in this repository computes all_passed as passed equal
        to total, so a report that collected no check at all answers True. The
        step exists to prove that a default installation carries working Studio
        checks, and it read only that field, so an installation that packaged
        none of them would have been reported as proof that it had them.
        """
        program = embedded_python("default-install", "studio_server")
        with tempfile.TemporaryDirectory() as directory:
            stub = Path(directory)
            (stub / "loop_engine" / "core").mkdir(parents=True)
            (stub / "loop_engine" / "__init__.py").write_text("", encoding="utf-8")
            (stub / "loop_engine" / "core" / "__init__.py").write_text("", encoding="utf-8")
            server = stub / "loop_engine" / "core" / "studio_server.py"
            program_file = stub / "step.py"
            program_file.write_text(program, encoding="utf-8")

            def decide(report):
                server.write_text(f"def self_test():\n    return {report!r}\n", encoding="utf-8")
                return subprocess.run([sys.executable, str(program_file)], cwd=str(stub),
                                      env={**os.environ, "PYTHONPATH": str(stub)},
                                      capture_output=True, text=True, timeout=60)

            honest = decide({"passed": 12, "total": 12, "all_passed": True})
            self.assertEqual(honest.returncode, 0, honest.stderr)
            self.assertIn("installed Studio checks: 12/12", honest.stdout)

            empty = decide({"passed": 0, "total": 0, "all_passed": True})
            self.assertNotEqual(empty.returncode, 0)
            self.assertIn("AssertionError", empty.stderr)

            lying = decide({"passed": 3, "total": 12, "all_passed": True})
            self.assertNotEqual(lying.returncode, 0)
            self.assertIn("AssertionError", lying.stderr)

            failing = decide({"passed": 11, "total": 12, "all_passed": False})
            self.assertNotEqual(failing.returncode, 0)
            self.assertIn("AssertionError", failing.stderr)

    def test_each_job_that_reads_the_history_checks_it_out(self):
        """The known-wrong case: the default depth-one checkout, which broke the suite on main.

        The starter catalogue names one revision and pins the bytes of every
        cited source at it. tools/test_starter_catalogue.py reads those files at
        that revision. With the default checkout the runner holds one commit, so
        the read succeeded only while the anchor was still the head of main and
        failed on the next push. Depth is a property of the workflow, not of the
        test, so it is held here.
        """
        document = yaml.load(WORKFLOW.read_text(), Loader=yaml.BaseLoader)
        for name in HISTORY_JOBS:
            with self.subTest(job=name):
                self.assertEqual(history_depth_problems(document, name), [])

        for name in HISTORY_JOBS:
            shallow = yaml.load(WORKFLOW.read_text(), Loader=yaml.BaseLoader)
            for row in shallow["jobs"][name]["steps"]:
                if str(row.get("uses", "")).startswith("actions/checkout@"):
                    row.pop("with", None)
            with self.subTest(shallow=name):
                found = history_depth_problems(shallow, name)
                self.assertEqual(len(found), 1)
                self.assertIn("cannot be read", found[0])


if __name__ == "__main__":
    unittest.main()
