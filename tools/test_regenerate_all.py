"""Every generated view regenerates in order, reaches a fixed point, and a stale commit is caught before it is pushed.

tools/regenerate_all.py holds the one list of generated files that continuous integration compares with their
builders. These rules hold that list to the repository (every output exists, every check it names exists, every tool
with a check mode is a view or says why not), hold the runner to its promises on a small scratch registry (it reports
and can be a no-op, a check puts every output back, a builder whose inputs change after it ran is named, an
undeclared write and a failing builder are refused), and reproduce the failure of release train 2 of September 27,
2026: a commit that adds a release record after the status pages were built passes a working-tree check and fails
continuous integration; the pristine check, which regenerates an export of the commit, fails on it too.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import regenerate_all as tool  # noqa: E402

#: Tools with a check mode that are not views, each with the reason.
NOT_VIEWS = {"owner_requests_ledger.py": "checks the hand-kept ledger against the roadmap and writes no committed file",
             "regenerate_all.py": "the runner itself"}
GIT = ("git", "-c", "user.name=Regeneration test", "-c", "user.email=regeneration@example.invalid",
       "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false")


def git(repository: Path, *args) -> str:
    return subprocess.run([*GIT, "-C", str(repository), *args], capture_output=True, text=True, check=True).stdout


def commit_all(repository: Path, message: str) -> None:
    git(repository, "add", "-A")
    git(repository, "commit", "-q", "-m", message)


def view(name, outputs, code, reads=()):
    return tool.View(name, tuple(outputs), tuple(reads), ("{python}", "-c", code), "scratch registry")


class RegistryTests(unittest.TestCase):
    def test_no_view_reads_what_a_later_view_writes(self):
        self.assertEqual(tool.order_problems(tool.VIEWS), [])
        # KNOWN_WRONG: the conformance manifest, which reads everything, moved to the front.
        moved = (tool.VIEWS[-1],) + tool.VIEWS[:-1]
        self.assertTrue(any(problem.startswith("conformance-manifest reads") for problem in tool.order_problems(moved)))
        self.assertIn("two views are named status-pages", tool.order_problems(tool.VIEWS + (tool.VIEWS[-2],)))

    def test_every_output_is_in_this_checkout(self):
        for item in tool.VIEWS:
            for output in item.outputs:
                with self.subTest(output=output):
                    self.assertTrue(tool._files_under(ROOT, output), f"{item.name} names {output}, which is absent")

    def test_every_check_a_view_names_exists(self):
        for item in tool.VIEWS:
            head, _, names = item.ci_check.partition(":")
            with self.subTest(view=item.name):
                self.assertIn(head, ("tools tests", "self-test", "conformance gates"))
                for name in (word.strip(" ,") for word in names.split() if word.startswith("test_")):
                    self.assertTrue((ROOT / "tools" / f"{name.rstrip(',')}.py").is_file(), name)

    def test_the_outputs_listing_is_every_output_in_order(self):
        # tools/release_train.py takes the train's side of a conflict in exactly these paths.
        completed = subprocess.run([sys.executable, str(ROOT / "tools" / "regenerate_all.py"), "--outputs"],
                                   capture_output=True, text=True, check=True)
        self.assertEqual(completed.stdout.split("\n")[:-1], [output for item in tool.VIEWS for output in item.outputs])
        self.assertIn("docs/roadmap/CONTINUATION-STATUS.md", completed.stdout.split())

    def test_every_tool_with_a_check_mode_is_a_view_or_says_why_not(self):
        commands = {part for item in tool.VIEWS for part in item.command}
        with_check = sorted(path.name for path in (ROOT / "tools").glob("*.py") if not path.name.startswith("test_")
                            and 'add_argument("--check"' in path.read_text(encoding="utf-8"))
        self.assertTrue(with_check)
        missing = [name for name in with_check if f"tools/{name}" not in commands and name not in NOT_VIEWS]
        self.assertEqual(missing, [], "a tool with a check mode compares a committed file; add it to VIEWS")


class RunnerTests(unittest.TestCase):
    """The runner's promises on a small scratch registry in a scratch checkout."""

    def setUp(self):
        holder = tempfile.TemporaryDirectory(prefix="regenerate-")
        self.addCleanup(holder.cleanup)
        self.root = Path(holder.name)
        git(self.root, "init", "-q")
        (self.root / "in.txt").write_text("alpha\n")
        (self.root / "out").mkdir()
        (self.root / "out" / "upper.txt").write_text("ALPHA\n")
        commit_all(self.root, "start")
        self.upper = view("upper", ["out/upper.txt"], "import pathlib; pathlib.Path('out/upper.txt')"
                          ".write_text(pathlib.Path('in.txt').read_text().upper())", reads=["in.txt"])

    def run_registry(self, views, **options):
        return tool.regenerate(self.root, views=views, registry=views, log=lambda *args: None, **options)

    def test_a_current_view_is_a_no_op_and_a_stale_one_is_reported_and_written(self):
        self.assertEqual(self.run_registry((self.upper,))["changed"], [])
        (self.root / "in.txt").write_text("beta\n")
        result = self.run_registry((self.upper,))
        self.assertEqual(result["changed"], [("upper", "out/upper.txt", "changed")])
        self.assertEqual((self.root / "out" / "upper.txt").read_text(), "BETA\n")

    def test_the_check_mode_puts_every_output_back(self):
        (self.root / "in.txt").write_text("beta\n")
        folder = view("folder", ["out/"], "import pathlib, shutil; p = pathlib.Path('out'); "
                      "(p / 'upper.txt').unlink(); (p / 'new.txt').write_text('new')")
        result = self.run_registry((folder,), check=True, verify=False)
        self.assertEqual(sorted(change for _view, _path, change in result["changed"]), ["added", "removed"])
        self.assertEqual(sorted(path.name for path in (self.root / "out").iterdir()), ["upper.txt"])
        self.assertEqual((self.root / "out" / "upper.txt").read_text(), "ALPHA\n")

    def test_known_wrong_a_builder_whose_input_changes_after_it_ran_is_named(self):
        # "upper" reads in.txt without declaring it, and "rewrite" changes in.txt after it: the order check cannot see
        # the dependency, the second run does.
        hidden = view("upper", ["out/upper.txt"], self.upper.command[2])
        rewrite = view("rewrite", ["in.txt"], "import pathlib; pathlib.Path('in.txt').write_text('gamma\\n')")
        with self.assertRaises(tool.RegenerationError) as refused:
            self.run_registry((hidden, rewrite))
        self.assertIn("upper: a second run changed out/upper.txt", str(refused.exception))
        # Declared, the same dependency is refused before anything runs.
        with self.assertRaises(tool.RegenerationError) as ordered:
            self.run_registry((self.upper, rewrite))
        self.assertIn("upper reads in.txt, which rewrite writes after it", str(ordered.exception))

    def test_known_wrong_an_undeclared_write_is_refused(self):
        stray = view("stray", ["out/upper.txt"], "import pathlib; pathlib.Path('stray.txt').write_text('x')")
        with self.assertRaises(tool.RegenerationError) as refused:
            self.run_registry((stray,), verify=False)
        self.assertIn("stray.txt", str(refused.exception))

    def test_known_wrong_a_failing_builder_is_refused_with_its_output(self):
        broken = view("broken", ["out/upper.txt"], "import sys; print('the builder broke'); sys.exit(3)")
        with self.assertRaises(tool.RegenerationError) as refused:
            self.run_registry((broken,), verify=False)
        self.assertIn("exited 3", str(refused.exception))
        self.assertIn("the builder broke", str(refused.exception))


class ReleaseTrainTwoTests(unittest.TestCase):
    """Release train 2: status-pages.json was built before a later commit added a release record."""

    STATUS_PAGES = "src/loop_engine/core/service_runtime/web_assets/status-pages/status-pages.json"

    @classmethod
    def setUpClass(cls):
        holder = tempfile.TemporaryDirectory(prefix="train-two-")
        cls.addClassCleanup(holder.cleanup)
        cls.home = Path(holder.name)
        cls.repository = cls.home / "repository"
        cls.repository.mkdir()
        records = subprocess.run(["git", "-C", str(ROOT), "ls-files",
                                  "artifacts/architecture-audit-2026-09-19/pilot-release-*.json",
                                  "artifacts/community-release-*/README.md"],
                                 capture_output=True, text=True, check=True)
        # Only what the status pages builder reads, so the scratch checkout stays small (about 70 megabytes).
        paths = ["src", "tools", "docs/roadmap", "CHANGELOG.md", *records.stdout.split()]
        archive = subprocess.Popen(["git", "-C", str(ROOT), "archive", "--format=tar", "HEAD", "--", *paths],
                                   stdout=subprocess.PIPE)
        subprocess.run(["tar", "-x", "-C", str(cls.repository)], stdin=archive.stdout, check=True)
        archive.stdout.close()
        archive.wait()
        # The tree under test may not have committed this tool yet; the scratch checkout holds the current one.
        shutil.copy2(ROOT / "tools" / "regenerate_all.py", cls.repository / "tools" / "regenerate_all.py")
        git(cls.repository, "init", "-q")
        commit_all(cls.repository, "The tree with current status pages")

    def pristine(self):
        return tool.pristine_check(self.repository, only=("status-pages",), work_home=self.home / "work",
                                   log=lambda *args: None)

    def builder_check(self):
        path = os.pathsep.join([str(self.repository / "src"), str(self.repository / "tools")])
        return subprocess.run([sys.executable, "tools/build_public_status_pages.py", "--check"], cwd=self.repository,
                              env={**os.environ, "PYTHONPATH": path, "PYTHONDONTWRITEBYTECODE": "1"},
                              capture_output=True, text=True, check=False).returncode

    def test_a_later_record_commit_fails_the_pristine_check_even_when_the_working_tree_passes(self):
        self.assertEqual(self.pristine(), 0, "the scratch commit starts current")
        source = self.repository / "artifacts/architecture-audit-2026-09-19/pilot-release-40.json"
        record = json.loads(source.read_text("utf-8"))
        record.update(release=41, deployed_at="2026-09-27T21:00:00Z", recorded_at="2026-09-27T21:10:00+00:00")
        added = "The library page shows the count of packages served now."
        record["changes"] = [added] + list(record.get("changes") or [])
        source.with_name("pilot-release-41.json").write_text(json.dumps(record, indent=1) + "\n", "utf-8")
        commit_all(self.repository, "Record release 41")
        # The commit continuous integration would receive holds stale status pages.
        self.assertEqual(self.builder_check(), 1)
        self.assertEqual(self.pristine(), 1)
        # KNOWN_WRONG, train 2 itself: regenerated in the working tree and not committed, the local check passes,
        # while the commit that would be pushed is still stale and the pristine check still fails.
        subprocess.run([sys.executable, "tools/build_public_status_pages.py"], cwd=self.repository, check=True,
                       env={**os.environ, "PYTHONPATH": str(self.repository / "src"), "PYTHONDONTWRITEBYTECODE": "1"},
                       capture_output=True)
        self.assertEqual(self.builder_check(), 0)
        self.assertEqual(self.pristine(), 1)
        commit_all(self.repository, "Regenerate generated views")
        self.assertEqual(self.pristine(), 0)
        report = list((self.home / "work").glob("*/differences.txt"))
        self.assertTrue(any(self.STATUS_PAGES in path.read_text("utf-8") for path in report), report)


if __name__ == "__main__":
    unittest.main()
