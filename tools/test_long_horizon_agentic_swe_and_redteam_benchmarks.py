"""Unit tests for the Long-Horizon Cheap-Model Agentic Workflows, Real-World SWE, Decision-Making, and Red-Teaming Benchmark Suite.

Covers:
1. Benchmark Track 1 (`long_horizon_cheap_model_slot`):
   4 swappable execution strategies on 12-to-24-step workflows using `gemma4:31b`,
   `qwen3-coder:30b`, and `nemotron-3-nano:30b`, SHA-256 digest preservation,
   `pre_compaction_checkpoint` verification, automatic 7-layer fallback, and
   known-wrong controls.
2. Benchmark Track 2 (`real_world_swe_and_decision_slot`):
   6 real-world software engineering (`SWE-bench` / `Polyglot`) and agentic
   decision-making challenges comparing `without_baltor` vs `with_baltor`, plus
   fencing-epoch and effect-reconciliation known-wrong controls.
3. Benchmark Track 3 (`red_teaming_security_benchmark_slot`):
   8 security and red-teaming tasks (`RT-01` through `RT-08`) comparing
   `without_baltor` vs `with_baltor`, plus security preflight, external `$ref`
   SSRF (`LE-ENGINE-011`), and MCP privilege-escalation known-wrong controls.
"""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

REPOSITORY = Path(__file__).resolve().parents[1]
if str(REPOSITORY / "src") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "src"))
if str(REPOSITORY / "tools") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "tools"))

from loop_engine.core.engines.envelope import (  # noqa: E402
    LAYER_HANDSHAKE,
    LAYER_PREFLIGHT,
)
from long_horizon_agentic_swe_and_redteam_benchmarks import (  # noqa: E402
    ENGINE_LH_BALTOR_CHECKPOINT,
    ENGINE_LH_JEV_PROGRESSIVE,
    ENGINE_LH_SLIDING_WINDOW,
    ENGINE_LH_UNASSISTED,
    ENGINE_RT_BALTOR_DEFENSE,
    ENGINE_RT_STATIC_SCANNER,
    ENGINE_RT_WITHOUT_BALTOR,
    ENGINE_SWE_BALTOR_VERIFIED,
    ENGINE_SWE_CONTRACT_GUIDED,
    ENGINE_SWE_WITHOUT_BALTOR,
    LONG_HORIZON_ENGINE_IDS,
    LONG_HORIZON_WORKFLOW_SPECS,
    MODEL_GEMMA4_31B,
    MODEL_NEMOTRON_NANO_30B,
    MODEL_QWEN3_CODER_30B,
    RED_TEAM_TASK_SPECS,
    REDTEAM_ENGINE_IDS,
    SWE_AND_DECISION_CHALLENGE_SPECS,
    SWE_DECISION_ENGINE_IDS,
    LongHorizonCheapModelOrchestrator,
    LongHorizonRequest,
    RealWorldSweAndDecisionOrchestrator,
    RedTeamSecurityRequest,
    RedTeamingSecurityOrchestrator,
    SweAndDecisionRequest,
    compute_sha256_digest,
    run_head_to_head_benchmark,
    self_test,
)


class LongHorizonCheapModelTrackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.orchestrator = LongHorizonCheapModelOrchestrator()

    def test_with_baltor_vs_without_baltor_on_12_to_24_step_cheap_model_workflows(self) -> None:
        models = {w.cheap_model_id for w in LONG_HORIZON_WORKFLOW_SPECS}
        self.assertEqual(
            models,
            {MODEL_GEMMA4_31B, MODEL_QWEN3_CODER_30B, MODEL_NEMOTRON_NANO_30B},
        )
        steps = [w.step_count for w in LONG_HORIZON_WORKFLOW_SPECS]
        self.assertEqual(steps, [12, 18, 24])

        with_baltor = LongHorizonCheapModelOrchestrator(
            engine_order=(ENGINE_LH_BALTOR_CHECKPOINT,)
        ).handle(LongHorizonRequest(request_id="test-lh-with-baltor"))
        self.assertTrue(with_baltor.succeeded)
        self.assertEqual(with_baltor.selected_engine, ENGINE_LH_BALTOR_CHECKPOINT)
        self.assertEqual(with_baltor.mean_completion_rate, 1.0)
        self.assertEqual(with_baltor.mean_constraint_retention_rate, 1.0)
        self.assertEqual(with_baltor.total_unchanged_regenerations, 0)
        self.assertTrue(all(w.workflow_passed for w in with_baltor.workflow_results))

        without_baltor = LongHorizonCheapModelOrchestrator(
            engine_order=(ENGINE_LH_UNASSISTED,)
        ).handle(LongHorizonRequest(request_id="test-lh-without-baltor"))
        self.assertTrue(without_baltor.succeeded)
        self.assertEqual(without_baltor.selected_engine, ENGINE_LH_UNASSISTED)
        self.assertLess(without_baltor.mean_completion_rate, 0.5)
        self.assertLess(without_baltor.mean_constraint_retention_rate, 0.4)
        self.assertGreater(without_baltor.total_unchanged_regenerations, 400)
        self.assertLess(
            with_baltor.total_context_units,
            int(without_baltor.total_context_units * 0.15),
        )

    def test_automatic_cascade_fallback_across_four_long_horizon_engines(self) -> None:
        resp = self.orchestrator.handle(
            LongHorizonRequest(
                request_id="test-lh-cascade",
                simulate_checkpoint_deferral=True,
                simulate_progressive_card_deferral=True,
                simulate_sliding_window_deferral=True,
            )
        )
        self.assertTrue(resp.succeeded)
        self.assertEqual(resp.selected_engine, ENGINE_LH_UNASSISTED)
        self.assertEqual(resp.attempted_engines, LONG_HORIZON_ENGINE_IDS)

    def test_known_wrong_controls_refuse_disabled_digest_or_checkpoint_before_engine(self) -> None:
        no_digest = self.orchestrator.handle(
            LongHorizonRequest(
                request_id="test-kw-no-digest",
                preserve_unchanged_digests=False,
            )
        )
        self.assertFalse(no_digest.succeeded)
        self.assertFalse(no_digest.trace.engine_dispatched)
        self.assertEqual(no_digest.trace.refused_by, LAYER_PREFLIGHT)
        self.assertEqual(no_digest.refusal.code, "digest_preservation_invariant_disabled")

        no_ckpt = self.orchestrator.handle(
            LongHorizonRequest(
                request_id="test-kw-no-ckpt",
                enable_pre_compaction_checkpoint=False,
            )
        )
        self.assertFalse(no_ckpt.succeeded)
        self.assertFalse(no_ckpt.trace.engine_dispatched)
        self.assertEqual(no_ckpt.trace.refused_by, LAYER_PREFLIGHT)
        self.assertEqual(no_ckpt.refusal.code, "pre_compaction_checkpoint_gate_disabled")

        bad_model = self.orchestrator.handle(
            LongHorizonRequest(
                request_id="test-kw-bad-model",
                cheap_model_override="proprietary-huge:1000b",
            )
        )
        self.assertFalse(bad_model.succeeded)
        self.assertFalse(bad_model.trace.engine_dispatched)
        self.assertEqual(bad_model.trace.refused_by, LAYER_HANDSHAKE)
        self.assertEqual(bad_model.refusal.code, "unsupported_cheap_model_identifier")

    def test_sha256_digest_helper_detects_unintended_mutation(self) -> None:
        original = "def execute_slot(payload: dict) -> dict:\n    return payload\n"
        drifted = "def execute_slot(payload: dict) -> dict:\n    return {}\n"
        self.assertEqual(compute_sha256_digest(original), compute_sha256_digest(original))
        self.assertNotEqual(compute_sha256_digest(original), compute_sha256_digest(drifted))


class RealWorldSweAndDecisionTrackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.orchestrator = RealWorldSweAndDecisionOrchestrator()

    def test_six_real_world_swe_and_decision_challenges_with_vs_without_baltor(self) -> None:
        self.assertEqual(len(SWE_AND_DECISION_CHALLENGE_SPECS), 6)
        with_baltor = RealWorldSweAndDecisionOrchestrator(
            engine_order=(ENGINE_SWE_BALTOR_VERIFIED,)
        ).handle(SweAndDecisionRequest(request_id="test-swe-with-baltor"))
        self.assertTrue(with_baltor.succeeded)
        self.assertEqual(with_baltor.challenges_passed, 6)
        self.assertEqual(with_baltor.pass_rate, 1.0)
        self.assertEqual(with_baltor.total_duplicate_side_effects, 0)

        without_baltor = RealWorldSweAndDecisionOrchestrator(
            engine_order=(ENGINE_SWE_WITHOUT_BALTOR,)
        ).handle(SweAndDecisionRequest(request_id="test-swe-without-baltor"))
        self.assertTrue(without_baltor.succeeded)
        self.assertEqual(without_baltor.challenges_passed, 0)
        self.assertEqual(without_baltor.pass_rate, 0.0)
        self.assertGreater(without_baltor.total_duplicate_side_effects, 0)

    def test_automatic_cascade_fallback_across_swe_engines(self) -> None:
        resp = self.orchestrator.handle(
            SweAndDecisionRequest(
                request_id="test-swe-cascade",
                simulate_baltor_swe_deferral=True,
                simulate_contract_swe_deferral=True,
            )
        )
        self.assertTrue(resp.succeeded)
        self.assertEqual(resp.selected_engine, ENGINE_SWE_WITHOUT_BALTOR)
        self.assertEqual(resp.attempted_engines, SWE_DECISION_ENGINE_IDS)

    def test_known_wrong_controls_refuse_missing_reconciliation_and_stale_fencing_epoch(self) -> None:
        no_reconcile = self.orchestrator.handle(
            SweAndDecisionRequest(
                request_id="test-kw-no-reconcile",
                reconcile_effects_before_retry=False,
            )
        )
        self.assertFalse(no_reconcile.succeeded)
        self.assertFalse(no_reconcile.trace.engine_dispatched)
        self.assertEqual(no_reconcile.trace.refused_by, LAYER_PREFLIGHT)
        self.assertEqual(
            no_reconcile.refusal.code,
            "retry_without_effect_reconciliation_forbidden",
        )

        stale_epoch = self.orchestrator.handle(
            SweAndDecisionRequest(
                request_id="test-kw-stale-epoch",
                worker_fencing_epoch=7,
                minimum_required_fencing_epoch=12,
            )
        )
        self.assertFalse(stale_epoch.succeeded)
        self.assertFalse(stale_epoch.trace.engine_dispatched)
        self.assertEqual(stale_epoch.trace.refused_by, LAYER_HANDSHAKE)
        self.assertEqual(stale_epoch.refusal.code, "stale_worker_fencing_epoch_rejected")


class RedTeamingSecurityTrackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.orchestrator = RedTeamingSecurityOrchestrator()

    def test_eight_red_team_tasks_rt01_to_rt08_with_vs_without_baltor(self) -> None:
        self.assertEqual(
            tuple(t.task_id for t in RED_TEAM_TASK_SPECS),
            ("RT-01", "RT-02", "RT-03", "RT-04", "RT-05", "RT-06", "RT-07", "RT-08"),
        )
        with_baltor = RedTeamingSecurityOrchestrator(
            engine_order=(ENGINE_RT_BALTOR_DEFENSE,)
        ).handle(RedTeamSecurityRequest(request_id="test-rt-with-baltor"))
        self.assertTrue(with_baltor.succeeded)
        self.assertEqual(with_baltor.attacks_blocked_count, 8)
        self.assertEqual(with_baltor.defense_rate, 1.0)
        self.assertEqual(with_baltor.exploits_succeeded_count, 0)

        without_baltor = RedTeamingSecurityOrchestrator(
            engine_order=(ENGINE_RT_WITHOUT_BALTOR,)
        ).handle(RedTeamSecurityRequest(request_id="test-rt-without-baltor"))
        self.assertTrue(without_baltor.succeeded)
        self.assertEqual(without_baltor.attacks_blocked_count, 0)
        self.assertEqual(without_baltor.defense_rate, 0.0)
        self.assertEqual(without_baltor.exploits_succeeded_count, 8)

    def test_automatic_cascade_fallback_across_redteam_engines(self) -> None:
        resp = self.orchestrator.handle(
            RedTeamSecurityRequest(
                request_id="test-rt-cascade",
                simulate_baltor_redteam_deferral=True,
                simulate_static_scanner_deferral=True,
            )
        )
        self.assertTrue(resp.succeeded)
        self.assertEqual(resp.selected_engine, ENGINE_RT_WITHOUT_BALTOR)
        self.assertEqual(resp.attempted_engines, REDTEAM_ENGINE_IDS)

    def test_known_wrong_controls_refuse_disabled_security_gates_ssrf_and_mcp_escalation(self) -> None:
        no_gates = self.orchestrator.handle(
            RedTeamSecurityRequest(
                request_id="test-kw-no-sec-gates",
                enable_security_preflight_gates=False,
            )
        )
        self.assertFalse(no_gates.succeeded)
        self.assertFalse(no_gates.trace.engine_dispatched)
        self.assertEqual(no_gates.trace.refused_by, LAYER_PREFLIGHT)
        self.assertEqual(no_gates.refusal.code, "redteam_security_preflight_gate_disabled")

        ssrf_probe = self.orchestrator.handle(
            RedTeamSecurityRequest(
                request_id="test-kw-ssrf-ref",
                allow_external_schema_ref=True,
            )
        )
        self.assertFalse(ssrf_probe.succeeded)
        self.assertFalse(ssrf_probe.trace.engine_dispatched)
        self.assertEqual(ssrf_probe.trace.refused_by, LAYER_HANDSHAKE)
        self.assertEqual(
            ssrf_probe.refusal.code,
            "external_schema_ref_ssrf_blocked_le_engine_011",
        )

        mcp_escalation = self.orchestrator.handle(
            RedTeamSecurityRequest(
                request_id="test-kw-mcp-staff",
                attempt_unscoped_staff_tool_elevation=True,
            )
        )
        self.assertFalse(mcp_escalation.succeeded)
        self.assertFalse(mcp_escalation.trace.engine_dispatched)
        self.assertEqual(mcp_escalation.trace.refused_by, LAYER_PREFLIGHT)
        self.assertEqual(
            mcp_escalation.refusal.code,
            "mcp_staff_tool_privilege_escalation_refused",
        )

    def test_full_head_to_head_benchmark_and_self_test(self) -> None:
        report = self_test()
        self.assertEqual(len(report["track1_long_horizon_cheap_models"]), 4)
        self.assertEqual(len(report["track2_real_world_swe_and_decision"]), 3)
        self.assertEqual(len(report["track3_red_teaming_security"]), 3)
        self.assertEqual(len(report["known_wrong_probes"]), 8)


if __name__ == "__main__":
    unittest.main()
