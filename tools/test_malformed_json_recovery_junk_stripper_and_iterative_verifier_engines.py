"""Unit and Conformance Tests for the Deterministic 7-Stage Malformed JSON Recovery & 3-Gate Iterative Output Verifier Suite."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
for _p in (_REPOSITORY_ROOT / "src", _REPOSITORY_ROOT / "tools"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from malformed_json_recovery_junk_stripper_and_iterative_verifier_engines import (  # noqa: E402
    IterativeOutputVerificationRequest,
    MalformedJSONRecoveryRequest,
    generate_combinatorial_json_recovery_remixes_and_agentfeeds_packs,
    run_ast_and_regex_fallback_harvester,
    run_iterative_output_verification_and_self_heal_slot,
    run_malformed_json_and_structured_output_recovery_slot,
    run_malformed_json_recovery_and_iterative_verifier_benchmark,
    run_seven_stage_pipeline,
    stage1_strip_invisible_and_control_junk,
    stage2_peel_reasoning_tags_and_chatter,
    stage3_scan_balanced_delimiter_island,
    stage4_strip_comments_and_trailing_commas,
    stage5_normalize_python_js_literals_and_keys,
    stage6_heal_unescaped_quotes_and_newlines,
    stage7_pushdown_automaton_truncated_closer,
)


class MalformedJSONRecoveryAndIterativeVerifierTests(unittest.TestCase):
    """Verify all 7 deterministic stages, fallback engine, 3-gate iterative verifier, 6 remixes, and 4 known-wrong controls."""

    def test_stage1_to_stage7_individual_and_combined_pipeline(self) -> None:
        raw = (
            "\ufeff\x1b[32m<think>Analyzing allocation weights</think>\n"
            "Here is the requested JSON:\n```json\n"
            "{\n  // comment line\n  status: \u2018verified\u2019, active: True, missing: None,\n"
            '  "note": "Called "inner_tool" on\nline 2",\n'
            '  "items": [{"id": 1, "title": "partial'
        )
        s1, junk_count = stage1_strip_invisible_and_control_junk(raw)
        self.assertGreaterEqual(junk_count, 3)
        s2, trace = stage2_peel_reasoning_tags_and_chatter(s1)
        self.assertIn("Analyzing allocation weights", trace)
        s3, was_trunc = stage3_scan_balanced_delimiter_island(s2)
        self.assertTrue(was_trunc)
        s4 = stage4_strip_comments_and_trailing_commas(s3)
        self.assertNotIn("// comment line", s4)
        s5 = stage5_normalize_python_js_literals_and_keys(s4)
        self.assertIn('"status": "verified"', s5)
        self.assertIn("true", s5)
        self.assertIn("null", s5)
        s6 = stage6_heal_unescaped_quotes_and_newlines(s5)
        self.assertIn('\\"inner_tool\\"', s6)
        s7, closures = stage7_pushdown_automaton_truncated_closer(s6)
        self.assertEqual(closures, ('"', "}", "]", "}"))

        full = run_seven_stage_pipeline(raw)
        self.assertEqual(full["parsed_object"]["status"], "verified")
        self.assertIs(full["parsed_object"]["active"], True)
        self.assertIsNone(full["parsed_object"]["missing"])
        self.assertEqual(full["parsed_object"]["items"][0]["title"], "partial")
        self.assertEqual(len(full["stages_executed"]), 7)

    def test_slot_family_1_primary_and_ast_regex_fallback_engine(self) -> None:
        res = run_malformed_json_and_structured_output_recovery_slot(
            MalformedJSONRecoveryRequest(
                request_id="test-slot1-primary",
                raw_llm_output="<reasoning>Step 1</reasoning>```json\n{status: 'ok', score: 0.95,}\n```",
                required_fields=("status", "score"),
            )
        )
        self.assertEqual(res.status, "ok")
        self.assertEqual(res.selected_engine, "seven_stage_deterministic_json_extractor_and_repair_engine")
        self.assertEqual(res.parsed_object["status"], "ok")
        self.assertEqual(res.extracted_reasoning_trace, "Step 1")
        self.assertEqual(res.extra_llm_tokens_spent, 0)
        self.assertLess(res.latency_ms, 0.18)

        # Fallback engine on non-JSON key=value mangled output
        fb_res = run_malformed_json_and_structured_output_recovery_slot(
            MalformedJSONRecoveryRequest(
                request_id="test-slot1-fallback",
                raw_llm_output="Result summary -> status = 'verified'; score = 0.91; id = 42",
                required_fields=("status", "score", "id"),
            )
        )
        self.assertEqual(fb_res.status, "ok")
        self.assertEqual(fb_res.selected_engine, "ast_and_regex_fallback_key_value_harvester_engine")
        self.assertEqual(fb_res.parsed_object["status"], "verified")
        self.assertEqual(fb_res.parsed_object["id"], 42)

        direct_ast = run_ast_and_regex_fallback_harvester("{'status': 'ok', 'value': 7}", ("status", "value"))
        self.assertEqual(direct_ast["parsed_object"]["value"], 7)

    def test_slot_family_2_three_gate_verifier_and_pinpoint_delta_repair(self) -> None:
        # Case A: Passes all 3 gates with 0 extra LLM calls after Stage 1-7 repair
        zero_call_res = run_iterative_output_verification_and_self_heal_slot(
            IterativeOutputVerificationRequest(
                request_id="test-slot2-zero-llm",
                raw_llm_output=(
                    "<think>Check weights</think>{status: 'verified', score: '0.93', "
                    "allocations: [{'id': 'a', 'weight': 0.4}, {'id': 'b', 'weight': 0.6}], "
                    "provenance_citation: 'sha256:abc123'}"
                ),
                expected_field_types={"score": "float"},
                required_fields=("status", "score", "allocations", "provenance_citation"),
                allowed_enums={"status": ("verified", "ok")},
                conservation_sum_target=("allocations.weight", 1.0),
                required_provenance_prefix="sha256:",
            )
        )
        self.assertEqual(zero_call_res.status, "ok")
        self.assertEqual(zero_call_res.extra_llm_calls_used, 0)
        self.assertTrue(zero_call_res.gate1_schema_and_type_passed)
        self.assertTrue(zero_call_res.gate2_conservation_invariant_passed)
        self.assertTrue(zero_call_res.gate3_provenance_citation_passed)
        self.assertEqual(zero_call_res.verified_object["score"], 0.93)

        # Case B: Semantic conservation drift repaired in 1 pinpoint delta turn (<= 65 tokens)
        delta_res = run_iterative_output_verification_and_self_heal_slot(
            IterativeOutputVerificationRequest(
                request_id="test-slot2-delta",
                raw_llm_output=(
                    '{"status": "verified", "score": 0.90, '
                    '"allocations": [{"id": "a", "weight": 0.7}, {"id": "b", "weight": 0.5}], '
                    '"provenance_citation": "sha256:def456"}'
                ),
                expected_field_types={"score": "float"},
                required_fields=("status", "score", "allocations", "provenance_citation"),
                allowed_enums={"status": ("verified", "ok")},
                conservation_sum_target=("allocations.weight", 1.0),
                required_provenance_prefix="sha256:",
                simulate_pinpoint_delta_callback=lambda _p, _obj: '{"allocations": [{"id": "a", "weight": 0.7}, {"id": "b", "weight": 0.3}]}',
            )
        )
        self.assertEqual(delta_res.status, "ok")
        self.assertEqual(delta_res.extra_llm_calls_used, 1)
        self.assertLessEqual(delta_res.pinpoint_delta_prompt_token_count, 65)
        self.assertIn("$.allocations[1].weight", delta_res.pinpoint_delta_prompts_generated[0])

    def test_combinatorial_remixes_agentfeeds_and_five_file_packs(self) -> None:
        bundle = generate_combinatorial_json_recovery_remixes_and_agentfeeds_packs()
        self.assertEqual(bundle["total_combinatorial_remixes"], 6)
        self.assertTrue(bundle["all_remixes_verified"])
        self.assertTrue(bundle["all_contract_cards_within_2048_bytes"])
        self.assertEqual(len(bundle["agentfeeds_si_items"]), 6)
        self.assertEqual(len(bundle["baltor_five_file_harness_packs"]), 6)
        for pack in bundle["baltor_five_file_harness_packs"]:
            self.assertLessEqual(pack["contract_card_bytes"], 2048)
            self.assertEqual(
                set(pack["files"].keys()),
                {"baltor_contract_card.json", "AGENTS.md", "RULES.md", "MEMORY.md", "verifier.py"},
            )

    def test_50_archetypes_benchmark_and_four_known_wrong_controls(self) -> None:
        report = run_malformed_json_recovery_and_iterative_verifier_benchmark()
        self.assertEqual(report["total_archetypes_evaluated"], 50)
        base = report["strict_json_loads_with_full_prompt_llm_retry_baseline"]
        suite = report["baltor_7stage_deterministic_json_repair_and_iterative_verifier_suite"]
        self.assertEqual(base["first_pass_parse_success_rate"], 0.14)
        self.assertEqual(suite["zero_llm_token_deterministic_recovery_rate"], 0.96)
        self.assertEqual(suite["final_verified_schema_and_invariant_pass_rate"], 1.0)
        self.assertLess(suite["mean_deterministic_repair_latency_ms"], 0.18)
        self.assertGreaterEqual(suite["retry_token_reduction_ratio"], 0.968)

        controls = report["known_wrong_controls"]
        self.assertEqual(len(controls), 4)
        for ctrl_name, ctrl_val in controls.items():
            self.assertTrue(ctrl_val["refused"], f"Control {ctrl_name} must be refused")
            self.assertEqual(ctrl_val["refused_by"], "preflight")


if __name__ == "__main__":
    unittest.main()
