"""Cumulative limits, exact receipts and cross-shard novelty of the case campaign adapter."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import tempfile
import signal
import time
import unittest
from unittest.mock import patch

from tools.test_constraint_case_factory import parent_run, LICENSE, REVISION
from supply_lines import api_contract_run as atomic
from supply_lines import case_campaign as campaign
from supply_lines import constraint_case_runtime as runtime


class CampaignTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        one, two = self.root / "one", self.root / "two"
        one.mkdir(); two.mkdir()
        first, _ = parent_run(one)
        second, _ = parent_run(two)
        self.args = SimpleNamespace(parent_run=[first, second], run_folder=self.root / "campaign", shard_size=1,
            maximum_contracts=2, maximum_cases=1000, maximum_candidate_bytes=64 * 1024 * 1024,
            maximum_invocations=10, maximum_campaign_seconds=600, minimum_free_gigabytes=0.001,
            batch_size=1, maximum_seconds=60, max_batches=1, exclude_case_jobs=None, authorize_output_writes=True)

    def run_campaign(self, args=None):
        return campaign.run(args or self.args, revision=REVISION, licence_text=LICENSE, generator_digest="a" * 64)

    def test_preview_has_no_output_and_exposes_full_source_count(self):
        self.args.authorize_output_writes = False
        result = self.run_campaign()
        self.assertFalse(result["written"])
        self.assertEqual(result["plan"]["source_contracts"], 2)
        self.assertEqual(len(result["plan"]["shards"]), 2)
        self.assertFalse(self.args.run_folder.exists())

    def test_restart_keeps_limits_and_excludes_previous_shard_jobs(self):
        first = self.run_campaign()
        self.assertFalse(first["complete"])
        self.assertEqual(first["completed_shards"], 1)
        self.assertGreater(first["new_case_jobs"], 0)
        second = self.run_campaign()
        self.assertTrue(second["complete"])
        self.assertEqual(second["completed_shards"], 2)
        self.assertEqual(first["new_case_jobs"], second["new_case_jobs"])
        self.assertEqual(second["invocations"], 2)
        again = self.run_campaign()
        self.assertEqual(again["invocations_this_call"], 0)
        self.assertEqual(again["new_case_jobs"], first["new_case_jobs"])

    def test_increased_ceiling_and_changed_source_refuse_resume(self):
        self.run_campaign()
        larger = SimpleNamespace(**{**vars(self.args), "maximum_cases": 1001})
        with self.assertRaisesRegex(ValueError, "resume_plan_changed"):
            self.run_campaign(larger)
        smaller = SimpleNamespace(**{**vars(self.args), "parent_run": self.args.parent_run[:1]})
        with self.assertRaisesRegex(ValueError, "resume_plan_changed"):
            self.run_campaign(smaller)

    def test_receipt_mutation_is_not_a_completed_batch(self):
        self.run_campaign()
        path = self.args.run_folder / "receipts/00000001.json"
        record = campaign.read_record(path)
        record["case_jobs"] += 100
        path.write_bytes(runtime.encode(record))
        with self.assertRaisesRegex(ValueError, "receipt_changed"):
            self.run_campaign()

    def test_unanswered_dispatch_is_not_automatically_replayed(self):
        self.run_campaign()
        journal = self.args.run_folder / "campaign-events.jsonl"
        first = campaign.events(journal)[0]
        journal.write_bytes(runtime.encode(first).replace(b"\n", b"") + b"\n")
        with patch.object(campaign.cases, "run_as_loop") as execute:
            with self.assertRaisesRegex(ValueError, "unanswered_dispatch"):
                self.run_campaign()
        execute.assert_not_called()

    def test_native_failure_holds_campaign_without_retry(self):
        with patch.object(campaign.cases, "run_as_loop", side_effect=ValueError("fixture")) as execute:
            first = self.run_campaign()
            second = self.run_campaign()
        self.assertEqual(execute.call_count, 1)
        self.assertEqual(first["stopped_by"], "held_child")
        self.assertEqual(second["stopped_by"], "held_child")

    def test_deadline_and_free_disk_floor_stop_before_dispatch(self):
        with patch.object(campaign.shutil, "disk_usage", return_value=SimpleNamespace(free=0)):
            report = self.run_campaign()
        self.assertEqual(report["stopped_by"], "free_space_floor")
        self.assertEqual(report["invocations"], 0)
        with patch.object(campaign.time, "time", return_value=10 ** 12):
            report = self.run_campaign()
        self.assertEqual(report["stopped_by"], "campaign_deadline")

    def test_deadline_cannot_be_changed_alone(self):
        self.run_campaign()
        path = self.args.run_folder / "campaign.json"
        record = campaign.read_record(path)
        record["deadline_epoch"] += 100
        path.write_bytes(runtime.encode(record))
        with self.assertRaisesRegex(ValueError, "deadline_binding_changed"):
            self.run_campaign()

    def test_snapshot_cache_rechecks_changed_bytes(self):
        self.run_campaign()
        root = self.args.run_folder
        rows = campaign.events(root / "campaign-events.jsonl")
        plan = campaign.read_record(root / "campaign.json")["plan"]
        cache = {}
        with patch.object(campaign.exclusions, "read", wraps=campaign.exclusions.read) as reader:
            campaign.state(root, rows, plan, cache)
            campaign.state(root, rows, plan, cache)
            self.assertEqual(reader.call_count, 1)
            path = root / "exclusions/000000.json"
            record = campaign.read_record(path)
            record["job_ids"].pop()
            path.write_bytes(runtime.encode(record))
            with self.assertRaisesRegex(ValueError, "snapshot_changed"):
                campaign.state(root, rows, plan, cache)
            self.assertEqual(reader.call_count, 2)

    def test_native_case_ceiling_holds_without_bypassing_it(self):
        self.args.maximum_cases = 1
        report = self.run_campaign()
        self.assertEqual(report["stopped_by"], "held_child")
        self.assertLessEqual(report["new_case_jobs"], 1)
        self.assertEqual(self.run_campaign()["invocations_this_call"], 0)

    def test_cli_exposes_existing_owner_not_arbitrary_commands(self):
        from tools.build_library_supply import parser
        args = parser().parse_args(["constraint-campaign", "--parent-run", "/source", "--run-folder", "/output",
            "--maximum-contracts", "100", "--maximum-cases", "1000", "--maximum-candidate-bytes", "1000000",
            "--maximum-invocations", "50", "--maximum-campaign-seconds", "600"])
        self.assertFalse(args.authorize_output_writes)
        self.assertEqual(args.max_batches, 1)

    def test_batch_deadline_interrupts_and_restores_the_process_timer(self):
        original = signal.getsignal(signal.SIGALRM)
        with self.assertRaises(TimeoutError):
            with campaign.batch_deadline(0.02):
                time.sleep(0.1)
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL), (0.0, 0.0))
        self.assertEqual(signal.getsignal(signal.SIGALRM), original)

    def test_an_existing_timer_is_not_replaced(self):
        signal.setitimer(signal.ITIMER_REAL, 100)
        try:
            with self.assertRaisesRegex(ValueError, "timer_already_owned"):
                with campaign.batch_deadline(1):
                    self.fail("The existing timer was replaced")
            self.assertGreater(signal.getitimer(signal.ITIMER_REAL)[0], 1)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)

    def test_unknown_fields_in_the_last_event_are_refused(self):
        self.run_campaign()
        journal = self.args.run_folder / "campaign-events.jsonl"
        rows = campaign.events(journal)
        rows[-1]["unexpected"] = True
        journal.write_bytes(b"".join(runtime.encode(row).replace(b"\n", b"") + b"\n" for row in rows))
        with self.assertRaisesRegex(ValueError, "event_fields"):
            self.run_campaign()

    def test_wrong_population_receipt_refuses_even_with_matching_digest(self):
        self.run_campaign()
        root = self.args.run_folder
        path = root / "receipts/00000001.json"
        report = campaign.read_record(path)
        report["source_contracts"] += 1
        path.write_bytes(runtime.encode(report))
        rows = campaign.events(root / "campaign-events.jsonl")
        rows[1]["report_sha256"] = runtime.fingerprint(report)
        plan = campaign.read_record(root / "campaign.json")["plan"]
        with self.assertRaisesRegex(ValueError, "population_invalid"):
            campaign.state(root, rows[:2], plan)


if __name__ == "__main__":
    unittest.main()
