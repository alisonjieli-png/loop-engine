"""Check the worker's fixed mount, explicit authority and fresh run allocation."""
from contextlib import redirect_stderr
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("worker_launcher", ROOT / "containers/worker/run-task.py")
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)


class WorkerLauncherTests(unittest.TestCase):
    def arguments(self, task, *extra):
        return ["--task", str(task), "--provider", "fixture-provider", "--model", "fixture-model",
                "--max-model-calls", "7", *extra]

    def launch(self, root, args):
        with mock.patch.object(worker, "WORK_ROOT", root / "work"), \
                mock.patch.object(worker, "HARNESS_ROOT", root / "temporary"), \
                mock.patch.object(worker.os, "execvpe") as execute:
            worker.main(args)
            return execute.call_args.args[1]

    def fixture(self, root):
        (root / "work").mkdir()
        (root / "temporary").mkdir()
        task = root / "work/task.md"
        task.write_text("One bounded task")
        return task

    def test_each_launch_has_a_fresh_workspace_history_and_harness(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            task = self.fixture(root)
            commands = [self.launch(root, self.arguments(task)) for _ in range(2)]
            for flag in ("--workspace", "--runs-dir", "--harness-work-dir"):
                paths = [Path(command[command.index(flag) + 1]) for command in commands]
                self.assertNotEqual(*paths)
                self.assertTrue(all(path.is_dir() for path in paths))
            command = commands[0]
            self.assertEqual(command[:2], ["loop-engine", "solve"])
            self.assertEqual(command[command.index("--compile-provider") + 1], "fixture-provider")
            self.assertEqual(command[command.index("--max-model-calls") + 1], "7")
            self.assertNotIn("--allow-local-execution", command)
            self.assertEqual(command[command.index("--embodiment") + 1], "baltor")

    def test_native_choice_and_project_command_authority_are_explicit(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            task = self.fixture(root)
            command = self.launch(root, self.arguments(task, "--harness", "opencode", "--authorize-project-commands"))
            self.assertIn("--allow-local-execution", command)
            self.assertEqual(command[command.index("--embodiment-config") + 1], "/opt/baltor/opencode-harness.json")
            direct = self.launch(root, self.arguments(task, "--harness", "gateway"))
            self.assertNotIn("--embodiment", direct)

    def test_bad_allocations_unknown_harness_and_unmounted_task_refuse_before_execution(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            task = self.fixture(root)
            outside = root / "outside.md"
            outside.write_text("Must remain outside")
            alias = root / "work/alias.md"
            alias.symlink_to(task)
            invalid = [self.arguments(outside), self.arguments(alias), self.arguments(task, "--harness", "implicit"),
                       self.arguments(task, "--max-model-calls", "0"), self.arguments(task, "--max-passes", "-1")]
            for args in invalid:
                with self.subTest(args=args), self.assertRaises(SystemExit), redirect_stderr(io.StringIO()):
                    self.launch(root, args)
            self.assertFalse((root / "work/baltor-runs").exists())

    def test_run_directory_symlink_refuses_before_execution(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            task = self.fixture(root)
            (root / "work/baltor-runs").symlink_to(root / "temporary", target_is_directory=True)
            with self.assertRaises(SystemExit), redirect_stderr(io.StringIO()):
                self.launch(root, self.arguments(task))
            self.assertEqual(list((root / "temporary").iterdir()), [])

    def test_container_support_is_not_imported_by_the_product(self):
        for path in (ROOT / "src/loop_engine").rglob("*.py"):
            self.assertNotIn("from containers", path.read_text(), str(path))
            self.assertNotIn("import containers", path.read_text(), str(path))


if __name__ == "__main__":
    unittest.main()
