"""Tests for the unattended runner: the plan, the material, recovery and the drill.

Run from this folder:

    python -m unittest test_runner -v

No test calls a model. The end-to-end test starts the real Pi harness against
a scripted provider on a local port and is skipped when Pi is not installed.
"""
from __future__ import annotations

import csv
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
sys.path.insert(0, str(HERE))

import run_trials  # noqa: E402

DESIGN = json.loads((STUDY / "design.json").read_text(encoding="utf-8"))
TEST_TMP = os.environ.get("STUDY_TEST_TMP") or None


def temporary_folder(test):
    folder = tempfile.TemporaryDirectory(dir=TEST_TMP)
    test.addCleanup(folder.cleanup)
    return Path(folder.name)


class PlanTests(unittest.TestCase):
    def test_every_round_holds_every_family_and_arm_once(self):
        plan = run_trials.main_plan(DESIGN)
        cells = len(DESIGN["families"]) * len(DESIGN["arms"])
        self.assertEqual(len(plan), DESIGN["repetitions"] * cells)
        for repetition in range(1, DESIGN["repetitions"] + 1):
            round_cells = {(s["family"], s["arm"]) for s in plan if s["repetition"] == repetition}
            self.assertEqual(len(round_cells), cells)
        self.assertEqual(len({spec["trial_id"] for spec in plan}), len(plan))

    def test_the_drill_names_an_early_step_of_the_first_round(self):
        plan = [spec["trial_id"] for spec in run_trials.main_plan(DESIGN)]
        position = plan.index(DESIGN["interruption_drill"]["trial_id"])
        self.assertLess(position, len(DESIGN["families"]) * len(DESIGN["arms"]))
        self.assertGreater(position, 0)

    def test_the_worst_case_plan_fits_under_the_ceiling(self):
        steps = len(run_trials.main_plan(DESIGN)) + len(DESIGN["pilot"]["trials"]) + 1
        worst = steps * DESIGN["step_request_cap"] + DESIGN["probe"]["step_request_cap"]
        self.assertLessEqual(worst, DESIGN["request_ceiling"])


class MaterialTests(unittest.TestCase):
    def test_every_family_has_approved_material_with_its_first_line_as_marker(self):
        for family in DESIGN["families"]:
            text, items, markers = run_trials.material_for(DESIGN, family)
            self.assertEqual(len(items), len(DESIGN["material"][family]))
            self.assertTrue(all(marker.startswith("# ") for marker in markers))
            for marker in markers:
                self.assertIn(marker, text)

    def test_a_changed_byte_in_the_material_is_refused(self):
        folder = temporary_folder(self)
        shutil.copytree(run_trials.MATERIAL, folder / "material")
        body = folder / "material" / "normalize_website_addresses.md"
        body.write_bytes(body.read_bytes().replace(b"lower case", b"lower-case", 1))
        with mock.patch.object(run_trials, "MATERIAL", folder / "material"):
            with self.assertRaises(SystemExit):
                run_trials.material_for(DESIGN, "websites")


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.root = temporary_folder(self)
        self.trials = self.root / "trials"
        self.run_folder = self.root / "run"
        (self.run_folder / "leases").mkdir(parents=True)
        (self.run_folder / "steps").mkdir(parents=True)
        patcher = mock.patch.object(run_trials, "TRIALS", self.trials)
        patcher.start()
        self.addCleanup(patcher.stop)

    def write_ledger(self, trial_id, sequences):
        self.trials.mkdir(parents=True, exist_ok=True)
        with open(self.trials / "requests.jsonl", "a", encoding="utf-8") as handle:
            for sequence in sequences:
                handle.write(json.dumps({"event": "sent", "sequence": sequence,
                                         "trial_id": trial_id}) + "\n")
            handle.write(json.dumps({"event": "completed", "sequence": sequences[0],
                                     "trial_id": trial_id, "outcome": "ok",
                                     "usage": {"prompt_tokens": 10, "completion_tokens": 2}})
                         + "\n")

    def lease(self, pid, start_time, trial_id="r1-websites-gemma-none", attempt=1):
        root = self.run_folder / "steps" / f"{trial_id}-a{attempt}"
        (root / "work").mkdir(parents=True)
        value = {"trial_id": trial_id, "attempt": attempt, "phase": "main", "repetition": 1,
                 "family": "websites", "arm": "gemma-none", "model": "gemma4:31b",
                 "material_mode": "none", "material_items": [], "material_sha256": None,
                 "prompt_sha256": "x", "root": str(root), "start_sequence": 4,
                 "started_at": "2026-09-23T00:00:00+00:00", "runner_pid": 1,
                 "harness_pid": pid, "harness_start_time": start_time}
        run_trials.write_json_atomic(run_trials.lease_path(self.run_folder, trial_id, attempt),
                                     value)
        return value

    def test_a_left_over_harness_is_stopped_before_the_attempt_is_recorded(self):
        process = subprocess.Popen(["sleep", "300"], start_new_session=True)
        self.addCleanup(lambda: process.poll() is None and process.kill())
        self.lease(process.pid, run_trials.process_start_time(process.pid))
        self.write_ledger("r1-websites-gemma-none", [5, 6])
        recovered = run_trials.recover_interrupted(self.run_folder, DESIGN,
                                                   self.trials / "requests.jsonl", lambda _: None)
        self.assertEqual(recovered, ["r1-websites-gemma-none.a1"])
        process.wait(timeout=5)
        self.assertFalse(run_trials.group_alive(process.pid))
        record = json.loads((self.trials / "records" / "r1-websites-gemma-none.a1.json").read_text())
        self.assertEqual(record["status"], "interrupted")
        self.assertFalse(record["counts_in_results"])
        self.assertEqual(record["requests"]["physical"], 2)
        self.assertEqual(record["requests"]["sent_without_completion"], 1)
        self.assertIn(record["interruption"]["harness_stopped"],
                      ("ended_after_sigterm", "ended_after_sigkill"))
        self.assertEqual(list((self.run_folder / "leases").glob("*.json")), [])
        self.assertEqual(run_trials.next_attempt("r1-websites-gemma-none", self.run_folder), 2)

    def test_a_reused_process_number_is_never_signalled(self):
        self.lease(os.getpid(), "0")
        self.write_ledger("r1-websites-gemma-none", [5])
        run_trials.recover_interrupted(self.run_folder, DESIGN, self.trials / "requests.jsonl",
                                       lambda _: None)
        record = json.loads((self.trials / "records" / "r1-websites-gemma-none.a1.json").read_text())
        self.assertEqual(record["interruption"]["harness_stopped"],
                         "process_number_reused_by_another_process")

    def test_an_interrupted_attempt_does_not_count_and_the_step_runs_again(self):
        self.lease(None, None)
        self.write_ledger("r1-websites-gemma-none", [5])
        run_trials.recover_interrupted(self.run_folder, DESIGN, self.trials / "requests.jsonl",
                                       lambda _: None)
        records = run_trials.finished_trials()["r1-websites-gemma-none"]
        self.assertFalse(any(run_trials.counts(record) for record in records))


class SummarizeTests(unittest.TestCase):
    """The frozen analysis applies the claim rules to known cases."""

    def setUp(self):
        import summarize
        self.summarize = summarize

    def decide(self, better=(), worse=(), baseline_means=None):
        comparisons = {"gemma-agents against gemma-none": {
            family: ("first_clearly_higher" if family in better else
                     "second_clearly_higher" if family in worse else "not_separated")
            for family in DESIGN["families"]}}
        means = baseline_means or {family: 0.99 for family in DESIGN["families"]}
        table = [{"family": family, "arm": "gemma-none", "primary_mean": mean, "passed": 3,
                  "steps": 3} for family, mean in means.items()]
        return self.summarize.claim_decisions(DESIGN, comparisons, table)

    def test_three_clear_gains_and_no_loss_is_help(self):
        decision = self.decide(better=("phones", "emails", "names"))
        self.assertEqual(decision["overall"], "material_helps_across_families")

    def test_two_clear_gains_are_not_enough(self):
        decision = self.decide(better=("phones", "emails"))
        self.assertEqual(decision["overall"], "clear_in_some_families_only")

    def test_one_clear_loss_turns_gains_into_mixed(self):
        decision = self.decide(better=("phones", "emails", "names"), worse=("websites",))
        self.assertEqual(decision["overall"], "mixed")

    def test_three_clear_losses_and_no_gain_is_harm(self):
        decision = self.decide(worse=("phones", "emails", "names"))
        self.assertEqual(decision["overall"], "material_hurts_across_families")

    def test_hardness_needs_three_families_where_the_baseline_fails_part(self):
        hard = {family: 0.99 for family in DESIGN["families"]}
        hard.update(phones=0.90, emails=0.94)
        self.assertEqual(self.decide(baseline_means=hard)["hardness"], "not_hard_enough")
        hard.update(names=0.80)
        self.assertEqual(self.decide(baseline_means=hard)["hardness"], "hard_enough")

    def test_the_frozen_verdict_needs_every_repetition_above_every_other(self):
        self.assertEqual(self.summarize.verdict([0.9, 0.95, 0.92], [0.8, 0.85, 0.89]),
                         "first_clearly_higher")
        self.assertEqual(self.summarize.verdict([0.9, 0.95, 0.88], [0.8, 0.85, 0.89]),
                         "not_separated")
        self.assertEqual(self.summarize.verdict([0.9, 0.9, 0.9], [0.9, 0.9, 0.9]), "not_separated")


# ---------------------------------------------------------------------------
# End to end: the real Pi harness, a scripted provider, the drill and the supervisor


class ScriptedProvider:
    """Writes the perfect output on a step's first request and says DONE after a pause."""

    def __init__(self, output_text, pause_seconds=3.0):
        self.requests = 0
        self.authorization = set()
        provider = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.0"

            def log_message(self, *args):
                return

            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(length))
                provider.requests += 1
                provider.authorization.add(self.headers.get("Authorization"))
                first = not any(message.get("role") == "tool" for message in body["messages"])
                if not first:
                    time.sleep(pause_seconds)
                try:
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.end_headers()
                    if first:
                        delta = {"role": "assistant", "tool_calls": [{
                            "index": 0, "id": "call1", "type": "function",
                            "function": {"name": "write", "arguments": json.dumps(
                                {"path": "output.csv", "content": output_text})}}]}
                        finish = "tool_calls"
                    else:
                        delta, finish = {"role": "assistant", "content": "DONE"}, "stop"
                    for chunk in ({"choices": [{"index": 0, "delta": delta}]},
                                  {"choices": [{"index": 0, "delta": {}, "finish_reason": finish}]},
                                  {"choices": [], "usage": {"prompt_tokens": 50,
                                                            "completion_tokens": 5,
                                                            "total_tokens": 55}}):
                        self.wfile.write(b"data: " + json.dumps(chunk).encode() + b"\n\n")
                    self.wfile.write(b"data: [DONE]\n\n")
                except OSError:
                    pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()


def perfect_output(family):
    truth = json.loads((STUDY / "population" / family / "truth.json").read_text(encoding="utf-8"))
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(truth["output_columns"])
    for row in truth["rows"]:
        writer.writerow((row["id"], row["expected"], row["review"]))
    return buffer.getvalue()


@unittest.skipUnless(Path(DESIGN["harness"]["executable"]).exists(), "Pi is not installed")
class DrillEndToEndTests(unittest.TestCase):
    def test_the_supervisor_resumes_after_the_drill_and_finishes_the_plan(self):
        root = temporary_folder(self)
        provider = ScriptedProvider(perfect_output("websites"))
        self.addCleanup(provider.stop)
        design = json.loads(json.dumps(DESIGN))
        design.update(families=["websites"], repetitions=1, request_ceiling=20,
                      arms={"gemma-none": DESIGN["arms"]["gemma-none"]})
        design["provider"]["endpoint"] = {"scheme": "http", "host": "127.0.0.1",
                                          "port": provider.port, "base_path": "/v1",
                                          "key_variable": "STUDY_TEST_PROVIDER_KEY"}
        design["interruption_drill"] = {"trial_id": "r1-websites-gemma-none",
                                        "after_completed_requests": 1}
        design_path = root / "design.json"
        design_path.write_text(json.dumps(design), encoding="utf-8")
        trials, run_folder = root / "trials", root / "run"
        env = dict(os.environ, STUDY_TEST_PROVIDER_KEY="scripted-key-4417",
                   OVERNIGHT_RESTART_WAIT_SECONDS="1")
        completed = subprocess.run(
            ["bash", str(HERE / "overnight.sh"), str(run_folder), "--design", str(design_path),
             "--trials-folder", str(trials)],
            env=env, capture_output=True, text=True, timeout=240)
        self.assertEqual(completed.returncode, 0, completed.stdout[-2000:] + completed.stderr[-2000:])
        records = {path.stem: json.loads(path.read_text())
                   for path in (trials / "records").glob("*.json")}
        self.assertEqual(sorted(records), ["r1-websites-gemma-none.a1", "r1-websites-gemma-none.a2"])
        first, second = records["r1-websites-gemma-none.a1"], records["r1-websites-gemma-none.a2"]
        self.assertEqual(first["status"], "interrupted")
        self.assertFalse(first["counts_in_results"])
        self.assertGreaterEqual(first["requests"]["physical"], 1)
        self.assertEqual(second["status"], "completed")
        self.assertTrue(second["counts_in_results"])
        self.assertEqual(second["score"]["primary"], 1.0)
        self.assertTrue((run_folder / "drill-fired.json").is_file())
        supervisor = (run_folder / "supervisor.log").read_text()
        self.assertIn("runner ended with code 137", supervisor)
        self.assertIn("runner ended with code 0; supervisor stops", supervisor)
        ledger = [json.loads(line) for line in (trials / "requests.jsonl").read_text().splitlines()]
        sent = sum(row["event"] == "sent" for row in ledger)
        self.assertEqual(sent, first["requests"]["physical"] + second["requests"]["physical"])
        self.assertEqual(provider.authorization, {"Bearer scripted-key-4417"})
        self.assertNotIn("scripted-key-4417", (trials / "requests.jsonl").read_text())
        self.assertEqual(list((run_folder / "leases").glob("*.json")), [])


if __name__ == "__main__":
    unittest.main()
