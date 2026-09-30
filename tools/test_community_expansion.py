"""The daily source-to-package boundary: real factory, fixture model, no network."""
from __future__ import annotations

import copy
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from knowledge_radar.community_store import CommunityStore
from knowledge_radar.expansion import ExpansionRequest, SOURCES, choose_context, method_signature, read_policy, run, search_existing
from loop_engine.catalog.stores.sqlite_store import SQLiteRecordStore

ROOT = Path(__file__).resolve().parents[1]


def opportunity():
    return {"title": "Validate a finite numeric column", "purpose": "Reject non-finite values before aggregating a numeric column.",
            "mechanism": "Parse numeric values and reject NaN and infinity before summing.",
            "input_contract": "A JSON array of finite numbers, excluding booleans.",
            "output_contract": "A finite numeric total or an explicit invalid-value error.",
            "acceptance": ["The sum of [1,2] is 3.", "An empty array totals zero."],
            "known_wrong": ["NaN must raise an error rather than propagate."], "delivery_format": "python_tool",
            "source_urls": [], "reuse_search_terms": ["finite numeric column validation"],
            "why_distinct": "The operation explicitly distinguishes booleans and non-finite values from valid numbers."}


def production():
    return {"declared_effects": ["reads_fs", "spawns_process"], "dependencies": [], "files": [
        {"path": "AGENTS.md", "role": "instruction_file", "media_type": "text/markdown", "content":
         "# Validate a numeric column\nUse scripts/finite.py to sum a list of finite numbers. Python 3.10 or newer, standard library only. Reject booleans, NaN and infinity. No network or file writes. Run tests/test_finite.py in a permitted sandbox. These candidate tests have not been executed by the producer.\n"},
        {"path": "scripts/finite.py", "role": "executable_tool", "media_type": "text/x-python", "content":
         "import math\ndef total(values):\n    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in values):\n        raise ValueError('invalid numeric input')\n    return sum(values)\n"},
        {"path": "contracts/input.schema.json", "role": "configuration", "media_type": "application/json", "content": '{"type":"array","items":{"type":"number"}}'},
        {"path": "contracts/output.schema.json", "role": "configuration", "media_type": "application/json", "content": '{"type":"number"}'},
        {"path": "tests/test_finite.py", "role": "skill_script", "media_type": "text/x-python", "content":
         "import unittest\nfrom scripts.finite import total\nclass Tests(unittest.TestCase):\n    def test_sum(self):\n        self.assertEqual(total([1, 2]), 3)\n    def test_nan(self):\n        with self.assertRaises(ValueError):\n            total([float('nan')])\n"},
    ]}


class FixtureTurn:
    def __init__(self):
        self.calls = []

    def __call__(self, stage, payload):
        self.calls.append((stage, copy.deepcopy(payload)))
        answer = opportunity() if stage == "opportunity" else production() if stage == "production" else {
            "decision": "build", "reason": "A bounded original validator can be prepared without copying a source.",
            "questions": [{"question": question, "answer": "Needs independent validation; this is a scoped implementation proposal.",
                           "evidence_state": "inference"} for question in payload["questions"][:5]], "opportunity": opportunity()}
        return {"status": "complete", "reason": "", "answer": answer, "physical_model_calls": 1, "reported_tokens": 100}


class ExpansionChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        cls.repository = cls.root / "repository"
        cls.repository.mkdir()
        for relative in (*SOURCES, "LICENSE"):
            target = cls.repository / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)
        for command in (("init", "-q"), ("config", "user.name", "Fixture"),
                        ("config", "user.email", "fixture@example.invalid"), ("add", "."), ("commit", "-qm", "fixture")):
            subprocess.run(["git", "-C", str(cls.repository), *command], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def setUp(self):
        self.library = self.root / self.id().rsplit(".", 1)[-1]
        self.request = ExpansionRequest(self.repository, self.library, 2, True, True)
        self.store = CommunityStore(self.library, writes_allowed=True)
        self.add_work("one")

    def add_work(self, name):
        self.store.put("community.brief." + name, "research_brief", "fixture", "needs_research", {
            "record_type": "community_component_work_order/v1", "source_url": "https://example.org/" + name,
            "source_digest": "0" * 64, "linked_sources": [], "tools_mentioned": ["Python"],
            "candidate_component_work": ["A numeric column validator for data quality"], "publication_approved": False})

    def execute(self, turn):
        return run(self.request, turn=turn, fixture_run=True, fixture_day="2026-09-30")

    def test_three_turns_produce_a_real_native_package_and_no_approval(self):
        turn = FixtureTurn()
        result = self.execute(turn)
        self.assertEqual([row[0] for row in turn.calls], ["opportunity", "interrogation", "production"])
        self.assertEqual(result["candidate_packages"], 1, result)
        self.assertEqual(result["physical_model_calls_observed"], 3)
        self.assertEqual(result["approved_packages"], 0)
        package = result["outcomes"][0]["package"]
        items = json.loads((Path(package["catalogue"]) / "items.json").read_text())
        self.assertEqual(len(items["items"]), 1)
        self.assertFalse(package["execution_tested"])
        self.assertGreaterEqual(package["files"], 6)

    def test_repeated_tick_never_repeats_completed_model_work(self):
        turn = FixtureTurn()
        self.execute(turn)
        again = self.execute(turn)
        self.assertEqual(again["candidate_packages"], 0)
        self.assertEqual(len(turn.calls), 3)

    def test_titles_and_formats_do_not_inflate_method_identity(self):
        first = opportunity()
        changed = {**first, "title": "For a different industry", "delivery_format": "typescript_tool"}
        self.assertEqual(method_signature(first), method_signature(changed))
        self.assertNotEqual(method_signature(first), method_signature({**first, "output_contract": "A count, not a sum."}))

    def test_relevant_signals_win_over_an_unrelated_unused_industry(self):
        policy = read_policy(self.repository)
        selected = choose_context({"candidate_component_work": [], "tools_mentioned": ["Blender"],
                                   "signal_hints": ["geometry_and_rigging", "gameplay"]}, policy, {"scene_geometry": 99})
        self.assertEqual(selected["id"], "scene_geometry")

    def test_source_title_preserves_a_specific_transit_workflow(self):
        policy = read_policy(self.repository)
        selected = choose_context({"source_title": "A GTFS station quiz using railway map route geometry",
                                   "candidate_component_work": [], "tools_mentioned": [],
                                   "signal_hints": ["workflow_detail"]}, policy, {})
        self.assertEqual(selected["id"], "transit_story")

    def test_same_method_from_two_sources_is_prepared_once(self):
        self.add_work("two")
        result = self.execute(FixtureTurn())
        self.assertEqual(result["candidate_packages"], 1, result)
        self.assertEqual(result["outcomes"][1]["status"], "duplicate_method")

    def test_critique_can_choose_reuse_without_production(self):
        original = FixtureTurn()
        def turn(stage, payload):
            result = original(stage, payload)
            if stage == "interrogation":
                result["answer"]["decision"] = "reuse"
            return result
        result = self.execute(turn)
        self.assertEqual(result["candidate_packages"], 0)
        self.assertEqual(len(original.calls), 2)
        self.assertEqual(result["outcomes"][0]["status"], "reuse")

    def test_unknown_call_outcome_blocks_further_dispatches(self):
        def turn(_stage, _payload):
            raise TimeoutError()
        result = self.execute(turn)
        self.assertEqual(result["status"], "accounting_blocked")
        self.add_work("another")
        successor = FixtureTurn()
        self.execute(successor)
        self.assertEqual(successor.calls, [])

    def test_unfinished_reserved_dispatch_is_not_ignored_on_resume(self):
        self.store.put("community.expansion.budget.2026-09-30", "harness_budget", "expansion", "recorded", {
            "dispatches": 1, "reported_tokens": 0, "work_started": 1, "contexts": {}, "blocked": False,
            "pending_dispatch": "some-interrupted-work", "limits": {"maximum_work_per_day": 32,
                "maximum_model_dispatches_per_day": 96, "reported_token_stop_after": 2000000}})
        turn = FixtureTurn()
        self.assertEqual(self.execute(turn)["status"], "accounting_blocked")
        self.assertEqual(turn.calls, [])

    def test_invented_citation_is_refused(self):
        original = FixtureTurn()
        def turn(stage, payload):
            result = original(stage, payload)
            result["answer"]["source_urls"] = ["https://invented.example.org/proof"]
            return result
        result = self.execute(turn)
        self.assertEqual(result["candidate_packages"], 0)
        self.assertEqual(len(original.calls), 1)

    def test_unsafe_generated_paths_are_not_written(self):
        original = FixtureTurn()
        def turn(stage, payload):
            result = original(stage, payload)
            if stage == "production":
                result["answer"]["files"][1]["path"] = "../../outside.py"
            return result
        result = self.execute(turn)
        self.assertEqual(result["candidate_packages"], 0)
        self.assertFalse((self.library / "outside.py").exists())

    def test_missing_output_contract_cannot_become_a_prepared_candidate(self):
        original = FixtureTurn()
        def turn(stage, payload):
            result = original(stage, payload)
            if stage == "production":
                result["answer"]["files"] = [row for row in result["answer"]["files"]
                                             if row["path"] != "contracts/output.schema.json"]
            return result
        self.assertEqual(self.execute(turn)["candidate_packages"], 0)

    def test_invalid_json_schema_cannot_become_a_prepared_candidate(self):
        original = FixtureTurn()
        def turn(stage, payload):
            result = original(stage, payload)
            if stage == "production":
                result["answer"]["files"][2]["content"] = '{"type":"invented-type"}'
            return result
        self.assertEqual(self.execute(turn)["candidate_packages"], 0)

    def test_finished_work_needs_no_provider_or_credential_on_a_later_tick(self):
        from unittest import mock
        self.execute(FixtureTurn())
        with mock.patch("knowledge_radar.expansion_model.ExpansionTurn",
                        side_effect=AssertionError("an empty queue needs no provider")):
            result = run(self.request, fixture_run=True, fixture_day="2026-09-30")
        self.assertEqual(result["physical_model_calls_observed"], 0)

    def test_dry_run_and_unmarked_fake_engine_cannot_dispatch(self):
        empty = self.root / "dry-run-has-no-state"
        result = run(ExpansionRequest(self.repository, empty))
        self.assertEqual(result["status"], "plan")
        self.assertFalse(empty.exists())
        with self.assertRaises(ValueError):
            run(self.request, turn=FixtureTurn())

    def test_read_only_reuse_search_reports_candidates_and_capped_coverage(self):
        root = self.root / "reuse-fixture"
        root.mkdir()
        store = SQLiteRecordStore(str(root / "records.db"))
        for index in range(3):
            store.put({"record_id": "fixture" + str(index), "record_version": "1", "intelligence_layer": "",
                       "source_collection": "learned", "artifact_kind": "intelligence_record", "lifecycle": "candidate",
                       "namespace": "library.supply", "attributes": {"title": "Finite numeric validator"},
                       "payload": {"description": "Reject invalid numbers"}})
        store.close()
        result = search_existing(root, ["numeric validator"], maximum_scan=2)
        self.assertFalse(result["coverage_complete"])
        self.assertEqual(len(result["hits"]), 2)
        self.assertEqual(result["hits"][0]["state"], "candidate_not_approval")


if __name__ == "__main__":
    unittest.main()
