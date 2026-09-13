"""Contract, wiring, isolation, failure and persistence qualification for the lab."""

from __future__ import annotations

import ast
import asyncio
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from embodiment_lab.__main__ import run_experiment
from embodiment_lab.catalog import IMPLEMENTED, select
from embodiment_lab.contracts import RunPolicy, TaskCase, WorkPacket, digest
from embodiment_lab.process_adapter import WorkerProcess
from embodiment_lab.runtime import check_candidate, execute
from embodiment_lab.serving import view
from embodiment_lab.storage import ResultRecorder, confined_root
from embodiment_lab.study import generate, load, qualify

from loop_engine.core.reactive_output_store import SQLiteReactiveOutputStore
from loop_engine.core.reactive_scheduler import SQLiteReactiveScheduler
from loop_engine.loop.reactive_contracts import PortfolioView
from loop_engine.loop.reactive_outputs import OutputQuery

REPO = Path(__file__).resolve().parents[3]


class LabTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="loop-embodiments-test-")
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def packet(self, name="test", values=(1, -2, 8)):
        return WorkPacket(name, TaskCase(name, "sum", values))

    def test_contracts_refuse_unknown_boolean_and_oversized_values(self):
        for operation, values in (
            ("typo", (1,)),
            ("sum", (True,)),
            ("sum", (0,) * 4097),
        ):
            with self.assertRaises(ValueError):
                TaskCase("case", operation, values)
        for seconds, workers in ((float("nan"), 1), (1, 0), (1, True), (0, 1)):
            with self.assertRaises(ValueError):
                RunPolicy(seconds, workers)

    def test_packet_digest_and_exact_schema_are_enforced(self):
        value = self.packet().to_dict()
        self.assertEqual(WorkPacket.from_dict(value), self.packet())
        value["task"]["values"].append(4)
        with self.assertRaises(ValueError):
            WorkPacket.from_dict(value)
        value = self.packet().to_dict()
        value["authority"] = "all"
        with self.assertRaises(ValueError):
            WorkPacket.from_dict(value)

    def test_independent_oracle_rejects_wrong_value_and_wrong_request(self):
        packet = self.packet()
        result = execute(packet)
        self.assertTrue(check_candidate(packet, result)["accepted"])
        wrong = dict(result, value=42, value_digest=digest(42))
        self.assertEqual(check_candidate(packet, wrong)["reason"], "oracle_mismatch")
        self.assertFalse(check_candidate(self.packet("other"), result)["accepted"])
        self.assertNotEqual(
            check_candidate(packet, result)["verifier_loop_id"], result["loop_id"]
        )

    def test_study_controls_and_resource_drift(self):
        generate(self.root / "study", 12, 7)
        cases = load(self.root / "study")
        self.assertEqual(len(cases), 12)
        self.assertTrue(qualify(cases)["passed"])
        with self.assertRaises(FileExistsError):
            generate(self.root / "study", 12, 7)
        file = self.root / "study/case-00000/task.json"
        value = json.loads(file.read_text())
        value["values"].append(1)
        file.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, "drift"):
            load(self.root / "study")

    def test_symlink_and_traversal_refused(self):
        (self.root / "real").mkdir()
        (self.root / "alias").symlink_to(self.root / "real", target_is_directory=True)
        with self.assertRaises(ValueError):
            confined_root(self.root / "alias/sub", create=True)
        with self.assertRaises(ValueError):
            TaskCase("../escape", "sum", ())
        generate(self.root / "study", 1, 7)
        file = self.root / "study/manifest.json"
        manifest = json.loads(file.read_text())
        manifest["cases"][0]["path"] = "../outside.json"
        file.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "escape"):
            load(self.root / "study")

    def test_real_process_payload_delivery_and_session_state_separation(self):
        async def exercise():
            worker = await WorkerProcess(self.root / "worker").start()
            try:
                a, b = self.packet("first", (100,)), self.packet("second", (-3,))
                ra = await worker.request(a, 10)
                rb = await worker.request(b, 10)
                self.assertEqual(ra["pid"], rb["pid"])
                self.assertNotEqual(ra["pid"], os.getpid())
                self.assertNotEqual(ra["loop_id"], rb["loop_id"])
                self.assertEqual(rb["value"], -3)
                self.assertEqual(rb["packet_digest"], digest(b.to_dict()))
                self.assertNotIn("100", json.dumps(rb["value"]))
            finally:
                process = worker.process
                await worker.close()
                self.assertIsNotNone(process.returncode)

        asyncio.run(exercise())

    def test_all_implementations_produce_verified_outputs_and_history(self):
        generate(self.root / "study", 3, 11)
        results = {}
        for implementation in IMPLEMENTED:
            with self.subTest(variant=implementation.name):
                result = run_experiment(
                    implementation.name,
                    self.root / "study",
                    self.root / implementation.name,
                    RunPolicy(40, 2),
                )
                results[implementation.name] = result
                self.assertTrue(result["passed"], result)
                self.assertEqual(result["verified_tasks"], 3)
                self.assertEqual(result["model_calls"], 0)
                self.assertTrue(
                    list((self.root / implementation.name / "history").iterdir())
                )
        self.assertEqual(len(results["native"]["distinct_worker_pids"]), 1)
        self.assertEqual(len(results["fresh_process"]["distinct_worker_pids"]), 3)
        self.assertEqual(len(results["long_lived_session"]["distinct_worker_pids"]), 1)
        self.assertEqual(len(results["pooled_sessions"]["distinct_worker_pids"]), 2)
        self.assertEqual(results["parallel_portfolio"]["candidate_attempts"], 6)
        self.assertTrue(
            all(
                r["history_disposition"] == "persisted"
                for r in results["durable_reactive"]["rows"]
            )
        )

    def test_failed_attempts_remain_in_the_denominator(self):
        generate(self.root / "study", 3, 2)
        with patch(
            "embodiment_lab.embodiments.native.execute",
            side_effect=RuntimeError("fixture failure"),
        ):
            result = run_experiment(
                "native", self.root / "study", self.root / "out", RunPolicy()
            )
        self.assertFalse(result["passed"])
        self.assertEqual(result["tasks"], 3)
        self.assertEqual(result["failed_candidates"], 3)
        self.assertEqual(result["candidate_attempts"], 3)
        self.assertIsNone(result["model_calls"])

    def test_invalid_candidate_never_replaces_verified_portfolio(self):
        recorder = ResultRecorder(self.root)
        task = TaskCase("case", "sum", (1, 2, 3))
        first = WorkPacket("first", task)
        recorder.record(first, execute(first))
        second = WorkPacket("second", task)
        wrong = execute(second)
        wrong.update(value=999, value_digest=digest(999))
        self.assertFalse(recorder.record(second, wrong)["accepted"])
        recorder.close()
        reopened = SQLiteReactiveOutputStore(str(self.root / "portfolio.sqlite"))
        try:
            view = reopened.query(
                OutputQuery("lab", digest(task.to_dict()), PortfolioView.VERIFIED_TOP_K)
            )
            self.assertEqual(view.snapshot.portfolio_version, 1)
            self.assertEqual(view.entries[0].candidate_ref, "first")
        finally:
            reopened.close()

    def test_durable_activation_and_history_survive_database_reopen(self):
        generate(self.root / "study", 1, 19)
        result = run_experiment(
            "durable_reactive", self.root / "study", self.root / "run", RunPolicy()
        )
        self.assertTrue(result["passed"], result)
        scheduler = SQLiteReactiveScheduler(str(self.root / "run/activations.sqlite"))
        try:
            activation = scheduler.get_activation(result["rows"][0]["activation_id"])
            self.assertIsNotNone(activation.history_ref)
            self.assertEqual(activation.history_disposition.value, "persisted")
            self.assertTrue(
                (
                    self.root
                    / "run/reactive-history"
                    / activation.history_ref.run_id
                    / "manifest.json"
                ).is_file()
            )
            self.assertEqual(scheduler.recover_expired("2099-01-01T00:00:00Z"), ())
        finally:
            scheduler.close()

    def test_catalog_folders_and_planned_refusals(self):
        catalog = json.loads((REPO / "embodiments/catalog.json").read_text())
        self.assertIsNone(catalog["default_embodiment"])
        for item in catalog["embodiments"]:
            directory = REPO / "embodiments" / item["folder"]
            self.assertEqual(
                json.loads((directory / "manifest.json").read_text()), item
            )
            self.assertTrue((directory / "README.md").is_file())
            if item["status"] == "planned":
                process = subprocess.run(
                    [sys.executable, str(directory / "run.py")],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
                self.assertEqual(process.returncode, 2)
                self.assertEqual(json.loads(process.stdout)["status"], "unavailable")
            else:
                self.assertEqual(select(item["id"]).folder, item["folder"])

    def test_serving_best_random_and_as_of_never_reexecutes_a_producer(self):
        recorder = ResultRecorder(self.root)
        task = TaskCase("case", "sum", (1, 2, 3))
        for name in ("a", "b"):
            packet = WorkPacket(name, task)
            recorder.record(packet, execute(packet))
        recorder.close()
        with patch(
            "embodiment_lab.runtime.compute",
            side_effect=AssertionError("producer must not run"),
        ):
            latest = view(self.root, task, {"view": "all_verified"})
            first = view(self.root, task, {"view": "all_verified", "version": 1})
            random_a = view(self.root, task, {"view": "random", "seed": 5})
            random_b = view(self.root, task, {"view": "random", "seed": 5})
        self.assertEqual(len(latest["values"]), 2)
        self.assertEqual(len(first["values"]), 1)
        self.assertEqual(random_a, random_b)
        self.assertFalse(latest["producer_reactivated"])

    def test_cancellation_closes_a_real_worker(self):
        async def exercise():
            worker = await WorkerProcess(self.root / "cancel-worker").start()
            process = worker.process
            entered = asyncio.Event()

            async def blocked_read():
                entered.set()
                await asyncio.Future()

            with patch.object(process.stdout, "readline", side_effect=blocked_read):
                task = asyncio.create_task(worker.request(self.packet(), 10))
                await entered.wait()
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task
            self.assertIsNone(worker.process)
            self.assertIsNotNone(process.returncode)

        asyncio.run(exercise())

    def test_no_product_imports_of_experiments_or_cross_variant_imports(self):
        forbidden = {"embodiments", "embodiment_lab", "devtools"}
        for file in (REPO / "src/loop_engine").rglob("*.py"):
            for node in ast.walk(ast.parse(file.read_text())):
                if isinstance(node, ast.Import):
                    self.assertFalse(
                        {a.name.split(".")[0] for a in node.names} & forbidden,
                        str(file),
                    )
                elif (
                    isinstance(node, ast.ImportFrom) and node.level == 0 and node.module
                ):
                    self.assertNotIn(node.module.split(".")[0], forbidden, str(file))
        for file in (REPO / "devtools/embodiment_lab/embodiments").rglob("*.py"):
            for node in ast.walk(ast.parse(file.read_text())):
                if isinstance(node, ast.ClassDef):
                    self.assertFalse(node.name.endswith("Node"), str(file))
                if isinstance(node, ast.ImportFrom):
                    self.assertNotIn("embodiments", node.module or "", str(file))


if __name__ == "__main__":
    unittest.main()
