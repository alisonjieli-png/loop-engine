"""Tests for tools/baltor_optimized_harness_opencode_and_pi_engines.py.

Verifies the three slot families wrapped in the 7-layer ComponentEnvelope:
1. massively_optimized_baltor_harness_slot (4 engines)
2. opencode_and_pi_fork_adapter_slot (3 engines: opencode-baltor, pi-baltor / pie, vanilla)
3. custom_harness_compatibility_bridge_slot (4 universal protocol bridges)
Plus the 6-harness 20-turn benchmark matrix and 6 known-wrong controls.
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import baltor_optimized_harness_opencode_and_pi_engines as suite  # noqa: E402
from loop_engine.core.engines.envelope import (  # noqa: E402
    COVERAGE_LAYERS,
    EnvelopeRefusal,
    EnvelopeTrace,
)


class BaltorOptimizedHarnessOpenCodeAndPiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = suite.run_full_audit()

    def test_full_audit_passes_and_covers_all_seven_envelope_layers(self) -> None:
        self.assertTrue(self.report["passed"])
        self.assertEqual(self.report["envelope_layers"], list(COVERAGE_LAYERS))

    def test_slot_family_1_progressive_card_injection_and_zero_off_topic_bloat(self) -> None:
        on_topic = suite.run_progressive_zero_bloat_card_injection_engine(
            turn_prompt="Apply surgical AST patch and check function digest"
        )
        self.assertTrue(on_topic.accepted)
        self.assertLess(
            on_topic.payload["startup_schema_tokens"],
            suite.STARTUP_SCHEMA_TOKEN_CEILING,
        )
        self.assertEqual(len(on_topic.payload["mcp_startup_tools"]), 3)
        self.assertGreater(on_topic.payload["injected_tokens"], 0)
        self.assertLessEqual(
            on_topic.payload["injected_tokens"],
            2 * suite.CARD_INJECTION_TOKEN_CEILING,
        )

        off_topic = suite.run_progressive_zero_bloat_card_injection_engine(
            turn_prompt="Good morning, thanks for the update!"
        )
        self.assertTrue(off_topic.accepted)
        self.assertEqual(off_topic.payload["injected_tokens"], 0)
        self.assertTrue(off_topic.payload["off_topic_zero_injection"])

    def test_slot_family_1_ast_surgical_patch_preserves_untouched_symbol_digests(self) -> None:
        src = (
            "def untouched_helper(x: int) -> int:\n"
            "    return x + 42\n\n"
            "def target_fn(y: int) -> int:\n"
            "    return y * 2\n"
        )
        res = suite.run_ast_span_surgical_patch_engine(
            original_source=src,
            target_symbol="target_fn",
            replacement_symbol_source="def target_fn(y: int) -> int:\n    return y * 10\n",
        )
        self.assertTrue(res.accepted)
        self.assertEqual(res.payload["mutated_untouched_symbols"], [])
        self.assertEqual(res.payload["unchanged_preservation_rate"], 1.0)
        self.assertEqual(
            res.payload["before_digests"]["untouched_helper"],
            res.payload["after_digests"]["untouched_helper"],
        )
        self.assertNotEqual(
            res.payload["before_digests"]["target_fn"],
            res.payload["after_digests"]["target_fn"],
        )

    def test_slot_family_1_turn_one_auto_repair_and_pinned_invariant_compaction(self) -> None:
        repair_res = suite.run_turn_one_compiler_and_test_auto_repair_engine(
            candidate_code="def calc_margin(rev: float) -> float\n    return rev * 0.25\n",
            expected_symbol="calc_margin",
        )
        self.assertTrue(repair_res.accepted)
        self.assertTrue(repair_res.payload["auto_repaired_on_turn_one"])
        self.assertEqual(
            repair_res.payload["recovery_card_injected"],
            "card.compiler_turn_one_repair.v1",
        )

        capsule = suite.TaskCapsule(
            capsule_id="cap_test",
            goal_summary="Compact 34.6k tokens without losing invariants.",
            pinned_invariants=("INV-A", "INV-B", "INV-C"),
            protected_file_digests={"core.py": "abc123"},
            token_budget_ceiling=50000,
            usd_budget_ceiling=0.25,
        )
        comp_res = suite.run_pinned_invariant_compaction_memory_engine(
            raw_history_tokens=34600,
            capsule=capsule,
        )
        self.assertTrue(comp_res.accepted)
        self.assertLess(comp_res.payload["compacted_tokens"], suite.COMPACTION_TARGET_CEILING)
        self.assertEqual(comp_res.payload["retained_invariants"], ["INV-A", "INV-B", "INV-C"])
        self.assertEqual(comp_res.payload["missing_invariants"], [])

    def test_slot_family_2_opencode_baltor_and_pi_pie_baltor_forks(self) -> None:
        for model_id in suite.SUPPORTED_MODELS:
            oc_res = suite.run_opencode_baltor_fork_engine(
                turn_prompt="Configure opencode mcp fork",
                model_id=model_id,
                use_local_loopback=True,
            )
            self.assertTrue(oc_res.accepted)
            self.assertEqual(oc_res.payload["distribution"], "opencode-baltor")
            self.assertIn("baltor_preturn_hook", oc_res.payload["middleware"])
            panel = oc_res.payload["tui_side_panel"]
            self.assertIn("latest_selection_receipt", panel)
            self.assertGreater(panel["cumulative_saved_tokens"], 0)

        src = (
            "def keep_me() -> int:\n"
            "    return 1\n\n"
            "def edit_me() -> int:\n"
            "    return 2\n"
        )
        pi_res = suite.run_pi_pie_baltor_fork_engine(
            turn_prompt="Apply pi pie surgical ast patch",
            original_source=src,
            target_symbol="edit_me",
            replacement_symbol_source="def edit_me() -> int:\n    return 99\n",
            model_id="gemma4:31b",
        )
        self.assertTrue(pi_res.accepted)
        self.assertLess(pi_res.payload["system_prompt_tokens"], suite.PI_SYSTEM_PROMPT_TOKEN_CEILING)
        self.assertEqual(tuple(pi_res.payload["canonical_tools"]), suite.PI_CANONICAL_TOOLS)
        self.assertEqual(pi_res.payload["extra_tool_schema_tokens_added"], 0)
        self.assertTrue(pi_res.payload["ast_surgical_edit_verified"])

    def test_slot_family_3_four_universal_custom_harness_bridges(self) -> None:
        for eng in suite.CUSTOM_BRIDGE_ENGINES:
            res = suite.run_custom_harness_bridge(
                bridge_engine=eng,
                custom_harness_name=f"Harness_{eng}",
                turn_prompt="Apply ast surgical patch and opencode mcp",
            )
            self.assertTrue(res.accepted)
            self.assertIsInstance(res.trace, EnvelopeTrace)
            self.assertEqual(res.trace.to_dict()["record_type"], "envelope_trace/v1")
            self.assertFalse(res.payload["authorization_leaked"])
            if eng == suite.ENG_PAIRED_WEBSOCKET_LEASE_BRIDGE:
                self.assertIsNotNone(res.payload["websocket_lease_hmac"])

    def test_benchmark_profiles_and_all_six_known_wrong_controls(self) -> None:
        profiles = {p["profile_id"]: p for p in self.report["benchmark_profiles"]}
        self.assertEqual(len(profiles), 6)
        self.assertLess(
            profiles["opencode_baltor_fork"]["cumulative_20_turn_tokens"],
            profiles["vanilla_opencode"]["cumulative_20_turn_tokens"],
        )
        self.assertLess(
            profiles["pi_baltor_pie_fork"]["cumulative_20_turn_tokens"],
            profiles["vanilla_pi_pie"]["cumulative_20_turn_tokens"],
        )
        self.assertGreater(
            profiles["pi_baltor_pie_fork"]["pass_rate_gemma4_31b"],
            profiles["vanilla_pi_pie"]["pass_rate_gemma4_31b"],
        )
        self.assertGreater(
            profiles["native_massively_optimized_baltor_harness"]["pass_rate_gemma4_31b"],
            0.94,
        )

        controls = self.report["known_wrong_controls"]
        self.assertEqual(len(controls), 6)
        for ctrl in controls:
            self.assertTrue(ctrl["known_wrong_detected"], f"Control failed: {ctrl}")
            self.assertTrue(ctrl["leaked_when_removed"], f"Control did not leak when unguarded: {ctrl}")

        # Verify EnvelopeRefusal round-trip serialization on a refused control call
        refused = suite.run_custom_harness_bridge(
            bridge_engine=suite.ENG_MCP_STREAMABLE_HTTP_BRIDGE,
            custom_harness_name="BadVersionAgent",
            turn_prompt="ast patch",
            protocol_version="1999-01-01",
        )
        self.assertFalse(refused.accepted)
        self.assertIsInstance(refused.refusal, EnvelopeRefusal)
        self.assertEqual(
            EnvelopeRefusal.from_dict(refused.refusal.to_dict()),
            refused.refusal,
        )


if __name__ == "__main__":
    unittest.main()
