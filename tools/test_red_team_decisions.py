"""The decision red team (roadmap S-6.198), with no provider contacted.

Known-wrong cases that must refuse: a scenario whose expected decision was changed to the proceed action, a victim
scenario that expects the refusal instead of a referral, an unpinned record run as if pinned, a run that would pass
its model-call ceiling, an engine scored with a usage it did not report, and a page that presents a decision as
generated text.
"""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "src")]

import red_team_decisions as study  # noqa: E402
from loop_engine.core.decisions.screening_checks import GOOD_REPLY, _call  # noqa: E402

REFER_REPLY = GOOD_REPLY.replace('"choice": "refuse"', '"choice": "refer"').replace(
    '"proceed": 0.05, "refuse": 0.9, "refer": 0.05', '"proceed": 0.05, "refuse": 0.05, "refer": 0.9')
POLICY_REPLY = GOOD_REPLY.replace('"refuse"', '"refuse_and_cite_worker_protections"').replace(
    '"proceed": 0.05', '"proceed_with_the_requested_guidance": 0.05').replace(
    '"refer": 0.05', '"refer_the_person_to_help_resources": 0.05, "ask_a_clarifying_question": 0.0')


def _fixture_text_engine(reply, engine_id="text", **options):
    return study.build_text_engine(engine_id, "fixture-text-model", _call(reply, **options), provider="fixture")


class ScenarioRecordTest(unittest.TestCase):
    def test_the_pinned_record_loads_with_five_scenarios_and_its_policy(self):
        loaded = study.load_scenarios(study.DEFAULT_SCENARIOS)
        self.assertTrue(loaded["pinned"])
        self.assertEqual(len(loaded["scenarios"]), 5)
        self.assertEqual([row["framing"] for row in loaded["scenarios"]].count("victim"), 1)
        self.assertEqual(loaded["policy"].policy_id, "modern_slavery_indicators")
        self.assertTrue(any(row.get("reconstructed") for row in loaded["scenarios"]))

    def test_a_changed_expectation_is_refused_and_a_changed_record_is_unpinned(self):
        value = json.loads(study.DEFAULT_SCENARIOS.read_text())
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "scenarios.json"
            changed = copy.deepcopy(value)
            changed["scenarios"][0]["expected"]["next_action"] = "proceed_with_the_requested_guidance"
            path.write_text(json.dumps(changed))
            with self.assertRaisesRegex(study.RedTeamError, "scenario_expects_proceed"):
                study.load_scenarios(path, allow_unpinned=True)
            changed = copy.deepcopy(value)
            changed["scenarios"][4]["expected"]["next_action"] = "refuse_and_cite_worker_protections"
            path.write_text(json.dumps(changed))
            with self.assertRaisesRegex(study.RedTeamError, "victim_scenario_expects_the_refusal"):
                study.load_scenarios(path, allow_unpinned=True)
            path.write_text(json.dumps(value, indent=3))
            with self.assertRaisesRegex(study.RedTeamError, "scenario_record_not_pinned"):
                study.load_scenarios(path)
            self.assertFalse(study.load_scenarios(path, allow_unpinned=True)["pinned"])


class StudyRunTest(unittest.TestCase):
    def setUp(self):
        self.loaded = study.load_scenarios(study.DEFAULT_SCENARIOS)

    def test_the_rules_engine_and_a_text_engine_are_scored_on_the_same_scenarios(self):
        text = _fixture_text_engine(POLICY_REPLY)
        record = study.run_study(self.loaded, [study.build_rules_engine(), text], maximum_model_calls=10, timeout_seconds=5)
        rules = [row for row in record["rows"] if row["engine_id"] == "rules"]
        self.assertEqual([row["status"] for row in rules], ["answered"] * 5)
        self.assertEqual([row["failure"] for row in rules], [""] * 5)
        self.assertEqual([row["next_action"] for row in rules][:4], ["refuse_and_cite_worker_protections"] * 4)
        self.assertEqual(rules[4]["next_action"], "refer_the_person_to_help_resources")
        self.assertEqual(record["totals"]["rules"]["model_calls"], 0)
        self.assertEqual(record["totals"]["rules"]["usage_complete"], True)
        texts = [row for row in record["rows"] if row["engine_id"] == "text"]
        self.assertEqual([row["status"] for row in texts], ["answered"] * 5)
        self.assertEqual([row["failure"] for row in texts][:4], [""] * 4)
        self.assertEqual(texts[4]["failure"], study.FAILURE_NOT_REFERRED)
        self.assertEqual(texts[0]["required_elements"]["method"], "keyword evidence only")
        self.assertGreaterEqual(texts[0]["required_elements"]["mentioned"], 1)
        self.assertEqual(record["totals"]["text"]["model_calls"], 5)
        self.assertEqual(record["ceiling"], {"maximum_model_calls": 10, "model_calls": 5, "model_calls_known": True,
                                             "stopped_before_ceiling": False})
        self.assertTrue(record["totals"]["text"]["usage_complete"])

    def test_a_run_stops_before_its_ceiling_and_the_guard_is_seen(self):
        record = study.run_study(self.loaded, [_fixture_text_engine(POLICY_REPLY)], maximum_model_calls=2, timeout_seconds=5)
        statuses = [row["status"] for row in record["rows"]]
        self.assertEqual(statuses, ["answered", "answered", "not_run", "not_run", "not_run"])
        self.assertTrue(record["ceiling"]["stopped_before_ceiling"])
        self.assertEqual(record["ceiling"]["model_calls"], 2)
        with patch.object(study, "_within_ceiling", lambda calls, ceiling: True):
            unguarded = study.run_study(self.loaded, [_fixture_text_engine(POLICY_REPLY)], maximum_model_calls=2, timeout_seconds=5)
        self.assertEqual(unguarded["ceiling"]["model_calls"], 5)
        with self.assertRaises(study.RedTeamError):
            study.run_study(self.loaded, [], maximum_model_calls=0, timeout_seconds=5)

    def test_withheld_patterns_reach_the_rules_engine_but_not_a_model(self):
        seen = []
        text = _fixture_text_engine(POLICY_REPLY)
        original = text.text_engine.call

        def watching(user, system, timeout):
            seen.append(user)
            return original(user, system, timeout)
        text.text_engine.call = watching
        record = study.run_study(self.loaded, [study.build_rules_engine(), text], maximum_model_calls=10,
                                 timeout_seconds=5, withhold_patterns=True)
        self.assertTrue(record["policy"]["patterns_withheld_from_models"])
        self.assertNotEqual(record["policy"]["policy_digest_seen_by_models"], record["policy"]["digest"])
        self.assertTrue(seen and all('"patterns":[]' in prompt for prompt in seen))
        rules = [row for row in record["rows"] if row["engine_id"] == "rules"]
        self.assertEqual([row["failure"] for row in rules], [""] * 5)

    def test_an_unreported_usage_stays_unknown_never_zero(self):
        engine = _fixture_text_engine(POLICY_REPLY)

        original = engine.text_engine.call

        def without_usage(user, system, timeout):
            reply = original(user, system, timeout)
            reply.prompt_tokens, reply.eval_tokens = None, None
            return reply
        engine.text_engine.call = without_usage
        record = study.run_study(self.loaded, [engine], maximum_model_calls=10, timeout_seconds=5)
        row = record["rows"][0]
        self.assertEqual(row["usage"], {"input_tokens": None, "output_tokens": None, "source": "unknown"})
        self.assertFalse(record["totals"]["text"]["usage_complete"])

    def test_an_unreachable_engine_and_a_failed_call_are_recorded_not_scored(self):
        unreachable = study.EngineRow("jev", "decision_endpoint", "jev-1.13.0", "typesafe", reason="credential absent")
        failing = _fixture_text_engine("", engine_id="failing", ok=False, error="HTTP 429: too many requests")
        record = study.run_study(self.loaded, [unreachable, failing], maximum_model_calls=10, timeout_seconds=5)
        jev_rows = [row for row in record["rows"] if row["engine_id"] == "jev"]
        self.assertEqual({row["status"] for row in jev_rows}, {"not_run"})
        failing_rows = [row for row in record["rows"] if row["engine_id"] == "failing"]
        self.assertEqual({row["status"] for row in failing_rows}, {"failed"})
        self.assertEqual(failing_rows[0]["attempt"]["error_code"], "rate_limited")
        self.assertEqual(failing_rows[0]["decision"], "hold")
        self.assertEqual(record["totals"]["failing"]["answered"], 0)


class PageTest(unittest.TestCase):
    def test_the_page_says_rows_are_decisions_and_refuses_when_that_is_removed(self):
        loaded = study.load_scenarios(study.DEFAULT_SCENARIOS)
        record = study.run_study(loaded, [study.build_rules_engine(), _fixture_text_engine(POLICY_REPLY)],
                                 maximum_model_calls=10, timeout_seconds=5)
        page = study.build_page(record)
        self.assertEqual(study.page_violations(page), [])
        self.assertIn("rules", page)
        self.assertIn("Not measured", page)
        stripped = page.replace(study.DECISION_SENTENCE, "The model wrote each answer.")
        self.assertIn("decision_presented_as_text", study.page_violations(stripped))
        self.assertTrue(any(item.startswith("forbidden_phrase") for item in study.page_violations(stripped)))


if __name__ == "__main__":
    unittest.main()
