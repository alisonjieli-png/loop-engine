"""Unit, conformance, benchmark, and adversarial known-wrong control tests for
`tools/trace_mined_agents_rules_memory_and_behavior_engines.py`.
"""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
for _path in (_REPOSITORY_ROOT / "src", _REPOSITORY_ROOT / "tools"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from trace_mined_agents_rules_memory_and_behavior_engines import (  # noqa: E402
    ActiveBehavioralEnforcerOrchestrator,
    BENCHMARK_24_SCENARIOS,
    CANONICAL_24_BEHAVIORAL_INVARIANTS,
    CORRECTION_DOMAINS,
    DOMAIN_ARCHETYPES_16,
    DraftInterceptRequest,
    ENFORCER_ENGINE_ORDER,
    ENGINE_ENFORCER_FALLBACK,
    ENGINE_MINER_FALLBACK,
    ENGINE_SYNTH_FALLBACK,
    MINER_ENGINE_ORDER,
    MultiHarnessAgentsRulesMemoryPackOrchestrator,
    PREFLIGHT_CHECK_IDS,
    SUPPORTED_HARNESSES_11,
    SYNTH_ENGINE_ORDER,
    TraceMiningRequest,
    TraceRepeatedCorrectionMinerOrchestrator,
    TraceTurnRecord,
    TriadPackSynthesisRequest,
    run_trace_mined_behavior_benchmark,
)


class TraceMinedAgentsRulesMemoryAndBehaviorTests(unittest.TestCase):
    """Verify the 3 slot families, 12 engines, 24 invariants, 176 packs, and known-wrong controls."""

    def test_slot1_trace_miner_crystallizes_24_invariants_across_6_domains_and_4_engines(self) -> None:
        miner = TraceRepeatedCorrectionMinerOrchestrator()
        turns = (
            TraceTurnRecord(
                turn_id="T-01",
                source_path="claude/history.jsonl",
                speaker="owner",
                text="Stop asking me to push, when you fix something you push!",
                domain_hint="D1_autonomy_and_git_authority",
                repetition_count=5,
                frustration_score=0.98,
                scrubbed_pii=True,
            ),
        )
        for engine_id in MINER_ENGINE_ORDER:
            res = miner.handle(
                TraceMiningRequest(
                    schema="trace_repeated_correction_miner_request/v1",
                    turns=turns,
                    min_repetition_count=2,
                    preferred_engine=engine_id,
                )
            )
            self.assertTrue(res.accepted)
            self.assertEqual(res.selected_engine, engine_id)
            self.assertFalse(res.fallback_used)
            self.assertEqual(len(res.invariants), 24)
            self.assertEqual(set(res.domain_counts.keys()), set(CORRECTION_DOMAINS))
            for count in res.domain_counts.values():
                self.assertEqual(count, 4)
            self.assertEqual(res.nested_frame_depth, 1)

        # Unknown engine falls back deterministically to ENGINE_MINER_FALLBACK
        fallback_res = miner.handle(
            TraceMiningRequest(
                schema="trace_repeated_correction_miner_request/v1",
                turns=turns,
                preferred_engine="unknown_experimental_miner",
            )
        )
        self.assertTrue(fallback_res.accepted)
        self.assertTrue(fallback_res.fallback_used)
        self.assertEqual(fallback_res.selected_engine, ENGINE_MINER_FALLBACK)

    def test_slot2_pack_synthesizer_generates_16_archetypes_by_11_harnesses(self) -> None:
        synth = MultiHarnessAgentsRulesMemoryPackOrchestrator()
        self.assertEqual(len(DOMAIN_ARCHETYPES_16), 16)
        self.assertEqual(len(SUPPORTED_HARNESSES_11), 11)

        for engine_id in SYNTH_ENGINE_ORDER:
            res = synth.handle(
                TriadPackSynthesisRequest(
                    schema="multi_harness_agents_rules_memory_pack_request/v1",
                    preferred_engine=engine_id,
                    per_turn_token_budget=900,
                )
            )
            self.assertTrue(res.accepted)
            self.assertEqual(res.selected_engine, engine_id)
            self.assertEqual(res.archetype_count, 16)
            self.assertEqual(res.harness_count, 11)
            self.assertEqual(len(res.packs), 176)
            self.assertLessEqual(res.max_pack_tokens, 900)
            sample = res.packs[0]
            self.assertIn("AGENTS.md", sample.agents_md_content)
            self.assertIn("RULES.md", sample.rules_md_content)
            self.assertIn("MEMORY.md", sample.memory_md_content)
            self.assertEqual(sample.enforced_check_ids, PREFLIGHT_CHECK_IDS)

        fallback_res = synth.handle(
            TriadPackSynthesisRequest(
                schema="multi_harness_agents_rules_memory_pack_request/v1",
                preferred_engine="nonexistent_synth_engine",
            )
        )
        self.assertTrue(fallback_res.accepted)
        self.assertTrue(fallback_res.fallback_used)
        self.assertEqual(fallback_res.selected_engine, ENGINE_SYNTH_FALLBACK)

    def test_slot3_active_behavioral_enforcer_auto_repairs_violations_across_4_engines(self) -> None:
        enforcer = ActiveBehavioralEnforcerOrchestrator()
        for engine_id in ENFORCER_ENGINE_ORDER:
            res = enforcer.handle(
                DraftInterceptRequest(
                    schema="active_behavioral_enforcer_request/v1",
                    scenario_id="TEST-VOID-AND-KEY",
                    domain_id="D2_3d_worlds_horizon_and_cad",
                    draft_output_text="You should rotate your API key immediately.",
                    draft_tool_payload={
                        "scene_type": "3d",
                        "has_horizon_sky_dome": False,
                        "ground_skirt_radius": 30,
                        "cad_part": True,
                        "z_min_mm": 1.8,
                        "clearance_mm": 0.05,
                        "full_file_rewrite": True,
                    },
                    auto_repair_enabled=True,
                    preferred_engine=engine_id,
                )
            )
            self.assertTrue(res.accepted)
            self.assertEqual(res.selected_engine, engine_id)
            self.assertTrue(res.was_auto_repaired)
            self.assertFalse(res.owner_re_correction_required)
            self.assertNotIn("rotate your API key", res.repaired_output_text)
            self.assertTrue(res.repaired_tool_payload["has_horizon_sky_dome"])
            self.assertGreaterEqual(res.repaired_tool_payload["ground_skirt_radius"], 400)
            self.assertEqual(res.repaired_tool_payload["z_min_mm"], 0.0)
            self.assertGreaterEqual(res.repaired_tool_payload["clearance_mm"], 0.20)
            self.assertFalse(res.repaired_tool_payload["full_file_rewrite"])
            self.assertTrue(res.repaired_tool_payload["surgical_ast_patch"])

        fallback_res = enforcer.handle(
            DraftInterceptRequest(
                schema="active_behavioral_enforcer_request/v1",
                scenario_id="TEST-FALLBACK",
                domain_id="D1_autonomy_and_git_authority",
                draft_output_text="Clean output.",
                draft_tool_payload={},
                preferred_engine="unknown_enforcer",
            )
        )
        self.assertTrue(fallback_res.accepted)
        self.assertTrue(fallback_res.fallback_used)
        self.assertEqual(fallback_res.selected_engine, ENGINE_ENFORCER_FALLBACK)

    def test_known_wrong_controls_refuse_unredacted_secrets_unverified_memory_bloated_tokens_and_strict_violations(self) -> None:
        miner = TraceRepeatedCorrectionMinerOrchestrator()
        synth = MultiHarnessAgentsRulesMemoryPackOrchestrator()
        enforcer = ActiveBehavioralEnforcerOrchestrator()

        # 1. Refuse raw unredacted secrets in trace mining
        bad_secret_res = miner.handle(
            TraceMiningRequest(
                schema="trace_repeated_correction_miner_request/v1",
                turns=(
                    TraceTurnRecord(
                        turn_id="T-BAD-SECRET",
                        source_path="claude/paste-cache",
                        speaker="owner",
                        text="Pasted UNREDACTED_CREDENTIAL_MARKER in raw trace.",
                        domain_hint="D1_autonomy_and_git_authority",
                        scrubbed_pii=False,
                    ),
                ),
            )
        )
        self.assertFalse(bad_secret_res.accepted)
        self.assertIsNotNone(bad_secret_res.refusal)
        self.assertEqual(bad_secret_res.refusal.code, "unredacted_secret_in_trace_turn")

        # 2. Refuse unverified RuntimeMemory direct promotion or self-verifying worker
        bad_mem_res = miner.handle(
            TraceMiningRequest(
                schema="trace_repeated_correction_miner_request/v1",
                turns=(),
                runtime_memory_candidate_only=False,
                worker_id="same_loop_01",
                independent_verifier_id="same_loop_01",
            )
        )
        self.assertFalse(bad_mem_res.accepted)
        self.assertIsNotNone(bad_mem_res.refusal)
        self.assertEqual(bad_mem_res.refusal.code, "unverified_runtime_memory_promotion_claim")

        # 3. Refuse bloated > 1,200-token per-turn rule injections
        bad_budget_res = synth.handle(
            TriadPackSynthesisRequest(
                schema="multi_harness_agents_rules_memory_pack_request/v1",
                per_turn_token_budget=2400,
            )
        )
        self.assertFalse(bad_budget_res.accepted)
        self.assertIsNotNone(bad_budget_res.refusal)
        self.assertEqual(bad_budget_res.refusal.code, "per_turn_token_budget_exceeded")

        # 4. Refuse un-repaired violation when auto_repair_enabled=False
        strict_refusal = enforcer.handle(
            DraftInterceptRequest(
                schema="active_behavioral_enforcer_request/v1",
                scenario_id="STRICT-01",
                domain_id="D2_3d_worlds_horizon_and_cad",
                draft_output_text="You should rotate your API key immediately.",
                draft_tool_payload={"scene_type": "3d", "has_horizon_sky_dome": False},
                auto_repair_enabled=False,
            )
        )
        self.assertFalse(strict_refusal.accepted)
        self.assertIsNotNone(strict_refusal.refusal)
        self.assertEqual(strict_refusal.refusal.code, "behavioral_invariant_violation_refused")
        self.assertIn("NO_KEY_ROTATION_NAGS", strict_refusal.triggered_check_ids)
        self.assertIn("NO_POSTAGE_STAMP_3D_VOID", strict_refusal.triggered_check_ids)

    def test_24_scenario_head_to_head_benchmark_eliminates_owner_re_corrections(self) -> None:
        self.assertEqual(len(CANONICAL_24_BEHAVIORAL_INVARIANTS), 24)
        self.assertEqual(len(BENCHMARK_24_SCENARIOS), 24)
        report = run_trace_mined_behavior_benchmark()
        self.assertEqual(report["invariants_crystallized"], 24)
        self.assertEqual(report["triad_packs_generated"], 176)
        strategies = {s["strategy_id"]: s for s in report["strategies"]}
        self.assertEqual(
            strategies["unsteered_default_llm_without_files"]["owner_re_correction_rate_pct"],
            79.2,
        )
        self.assertEqual(
            strategies["static_generic_agents_md_only"]["owner_re_correction_rate_pct"],
            37.5,
        )
        self.assertEqual(
            strategies["baltor_trace_mined_agents_rules_memory_triad"]["owner_re_correction_rate_pct"],
            0.0,
        )
        self.assertEqual(
            strategies["baltor_trace_mined_agents_rules_memory_triad"]["first_turn_compliance_rate_pct"],
            100.0,
        )


if __name__ == "__main__":
    unittest.main()
