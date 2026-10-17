"""Tests for the Taedri-Provenance Semantic Invariants and 6-Tier Cheapest-Effective-Tool Ladder Suite."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

REPOSITORY = Path(__file__).resolve().parents[1]
if str(REPOSITORY / "src") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "src"))
if str(REPOSITORY / "tools") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "tools"))

from loop_engine import (  # noqa: E402
    DelegationSpec,
    EffectApprovalService,
    HarnessRunRequest,
    HarnessRunResult,
    LoopContract,
    LoopProfileRef,
)
from loop_engine.core.engines.envelope import (  # noqa: E402
    LAYER_ACCEPTED,
    LAYER_PREFLIGHT,
    LAYER_REFUSED,
    LAYER_TRACKING,
    RECONCILE_BEFORE_RETRY,
)
from taedri_invariants_and_cheapest_tool_ladder_engines import (  # noqa: E402
    BASELINE_ALWAYS_FRONTIER,
    BASELINE_UNVERIFIED_CHEAP,
    CLASS_CLASSIFIER,
    CLASS_CONTRACT_CODING,
    CLASS_FRONTIER_SYNTHESIS,
    CLASS_MATH_AST,
    CLASS_RETRIEVAL_LSH,
    CLASS_TIMESERIES_TABULAR,
    EIGHT_RESULT_STATES,
    ENGINE_EFFECT_AND_PROFILE,
    ENGINE_RESULT_STATE_MACHINE,
    ENGINE_TASK_CAPSULE,
    ENGINE_TIER0_DETERMINISTIC,
    ENGINE_TIER1_SIMD_LSH,
    ENGINE_TIER2_SYSTEM_ONE,
    ENGINE_TIER3_TIMESERIES_TABULAR,
    ENGINE_TIER4_CHEAP_CODING,
    ENGINE_TIER5_FRONTIER,
    RECONCILIATION_CONFIRMED_ABSENT,
    RECONCILIATION_UNKNOWN,
    SCOPE_CANDIDATE_ONLY,
    STATE_ACCEPTED,
    STATE_ARTIFACT_VALID,
    STATE_ATTEMPTED,
    STATE_INVALIDATED,
    STATE_PAIRED,
    STATE_PROMOTED,
    STATE_SCORE_VALID,
    STATE_SELECTED,
    STRATEGY_BALTOR_6TIER,
    TIER_L0,
    TIER_L1,
    TIER_L2,
    TIER_L3,
    TIER_L4,
    TIER_L5,
    CheapestEffectiveToolLadderOrchestrator,
    ClosedLoopTelemetryUtilityAdjuster,
    LadderTaskRequest,
    RuntimeMemory,
    TaedriSemanticInvariantsSlot,
    build_24_benchmark_tasks,
    run_head_to_head_benchmark,
    self_test,
)


class TaedriSemanticInvariantsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.slot = TaedriSemanticInvariantsSlot()

    def test_immutable_task_capsule_binds_loop_contract_delegation_and_harness_request(self) -> None:
        out = self.slot.build_immutable_task_capsule(
            capsule_id="cap-test-01",
            source_repository="loop-engine",
            source_revision="b3001c15",
            spdx_license="Apache-2.0",
            allowed_file_paths=("src/loop_engine/loop/loop_contract.py",),
            holdout_leakage_paths=("benchmarks/holdout/secret_test.json",),
            input_schema="task_capsule_in/v1",
            output_schema="task_capsule_out/v1",
            evaluator_digest="sha256:eval1234",
            max_tokens=2048,
            max_cost_usd=0.02,
            max_memory_mb=256,
            ambiguity_resolution_rules=("prefer_tier0_exact", "refuse_unverified_promotion"),
        )
        self.assertTrue(out.succeeded)
        self.assertEqual(out.engine_id, ENGINE_TASK_CAPSULE)
        self.assertTrue(out.envelope_trace.engine_dispatched)
        self.assertIsNotNone(out.capsule)
        assert out.capsule is not None
        self.assertEqual(len(out.capsule.capsule_sha256), 64)
        self.assertIsInstance(out.capsule.loop_contract, LoopContract)
        self.assertIsInstance(out.capsule.delegation_spec, DelegationSpec)
        self.assertIsInstance(out.capsule.harness_request, HarnessRunRequest)

    def test_known_wrong_holdout_leakage_in_task_capsule_is_refused(self) -> None:
        out = self.slot.build_immutable_task_capsule(
            capsule_id="cap-leak-01",
            source_repository="loop-engine",
            source_revision="b3001c15",
            spdx_license="Apache-2.0",
            allowed_file_paths=("benchmarks/holdout/secret_test.json",),
            holdout_leakage_paths=("benchmarks/holdout/secret_test.json",),
            input_schema="task_capsule_in/v1",
            output_schema="task_capsule_out/v1",
            evaluator_digest="sha256:eval1234",
            max_tokens=2048,
            max_cost_usd=0.02,
            max_memory_mb=256,
            ambiguity_resolution_rules=("prefer_tier0_exact",),
        )
        self.assertFalse(out.succeeded)
        self.assertEqual(out.envelope_trace.refused_by, LAYER_PREFLIGHT)
        self.assertIsNotNone(out.refusal)
        assert out.refusal is not None
        self.assertEqual(out.refusal.code, "holdout_leakage_boundary_intact")

    def test_eight_stage_result_state_machine_monotonic_progression_and_known_wrong_refusals(self) -> None:
        self.assertEqual(len(EIGHT_RESULT_STATES), 8)
        chain = (
            (STATE_ATTEMPTED, STATE_ARTIFACT_VALID),
            (STATE_ARTIFACT_VALID, STATE_SCORE_VALID),
            (STATE_SCORE_VALID, STATE_ACCEPTED),
            (STATE_ACCEPTED, STATE_PAIRED),
            (STATE_PAIRED, STATE_SELECTED),
            (STATE_SELECTED, STATE_PROMOTED),
        )
        for prior, target in chain:
            out = self.slot.transition_result_state(
                candidate_id="cand-01",
                prior_state=prior,
                target_state=target,
                artifact_digest="sha256:art01",
                evaluator_score=0.95,
                independent_verifier_passed=True,
                paired_baseline_id="baseline-01",
                selection_rank=1,
            )
            self.assertTrue(out.succeeded, f"Failed valid transition {prior} -> {target}")
            assert out.state_transition is not None
            self.assertIsInstance(out.state_transition.harness_result, HarnessRunResult)
            self.assertEqual(out.state_transition.harness_result.output["result_state"], target)

        # Known-wrong control: refuse promoting an artifact_valid candidate that failed score_valid/accepted
        bad_skip = self.slot.transition_result_state(
            candidate_id="cand-bad-skip",
            prior_state=STATE_ARTIFACT_VALID,
            target_state=STATE_PROMOTED,
            artifact_digest="sha256:art02",
            evaluator_score=0.50,
            independent_verifier_passed=False,
        )
        self.assertFalse(bad_skip.succeeded)
        self.assertEqual(bad_skip.envelope_trace.refused_by, LAYER_PREFLIGHT)
        assert bad_skip.refusal is not None
        self.assertEqual(bad_skip.refusal.code, "non_monotonic_or_skipped_state_transition")

        # Known-wrong control: refuse acceptance when score is below threshold or verifier failed
        bad_accept = self.slot.transition_result_state(
            candidate_id="cand-bad-accept",
            prior_state=STATE_SCORE_VALID,
            target_state=STATE_ACCEPTED,
            artifact_digest="sha256:art03",
            evaluator_score=0.91,
            independent_verifier_passed=False,
        )
        self.assertFalse(bad_accept.succeeded)
        assert bad_accept.refusal is not None
        self.assertEqual(
            bad_accept.refusal.code,
            "acceptance_requires_passing_score_and_independent_verifier",
        )

    def test_idempotent_effect_and_profile_binding_and_known_wrong_controls(self) -> None:
        valid = self.slot.bind_idempotent_effect_and_profile(
            effect_attempt_id="eff-valid-01",
            retry_idempotency_key="idem-001",
            is_retry=True,
            reconciliation_state=RECONCILIATION_CONFIRMED_ABSENT,
            worker_id="practitioner.worker.a",
            independent_verifier_id="practitioner.verifier.b",
            environment_digest="sha256:env123",
            declared_effects=("workspace_write",),
            runtime_memory=RuntimeMemory(
                memory_id="mem-01",
                loop_id="loop-01",
                scope="turn_local",
                curation_status=SCOPE_CANDIDATE_ONLY,
                claims_promotion=False,
            ),
        )
        self.assertTrue(valid.succeeded)
        self.assertEqual(valid.engine_id, ENGINE_EFFECT_AND_PROFILE)
        assert valid.effect_profile_binding is not None
        self.assertIsInstance(valid.effect_profile_binding.worker_profile, LoopProfileRef)
        self.assertIsInstance(self.slot.approval_service, EffectApprovalService)
        self.assertTrue(valid.effect_profile_binding.approval_service_bound)

        # Known-wrong control 1: Retry without prior outcome reconciliation
        bad_retry = self.slot.bind_idempotent_effect_and_profile(
            effect_attempt_id="eff-bad-retry",
            retry_idempotency_key="idem-002",
            is_retry=True,
            reconciliation_state=RECONCILIATION_UNKNOWN,
            worker_id="practitioner.worker.a",
            independent_verifier_id="practitioner.verifier.b",
            environment_digest="sha256:env123",
            declared_effects=("workspace_write",),
            runtime_memory=RuntimeMemory(memory_id="mem-02", loop_id="loop-01", scope="turn_local"),
        )
        self.assertFalse(bad_retry.succeeded)
        assert bad_retry.refusal is not None
        self.assertEqual(bad_retry.envelope_trace.refused_by, LAYER_TRACKING)
        self.assertEqual(bad_retry.refusal.retry, RECONCILE_BEFORE_RETRY)

        # Known-wrong control 2: worker_id == independent_verifier_id
        bad_verifier = self.slot.bind_idempotent_effect_and_profile(
            effect_attempt_id="eff-bad-verifier",
            retry_idempotency_key="idem-003",
            is_retry=False,
            reconciliation_state=RECONCILIATION_CONFIRMED_ABSENT,
            worker_id="practitioner.same",
            independent_verifier_id="practitioner.same",
            environment_digest="sha256:env123",
            declared_effects=(),
            runtime_memory=RuntimeMemory(memory_id="mem-03", loop_id="loop-01", scope="turn_local"),
        )
        self.assertFalse(bad_verifier.succeeded)
        assert bad_verifier.refusal is not None
        self.assertEqual(bad_verifier.refusal.code, "worker_cannot_be_own_independent_verifier")

        # Known-wrong control 3: RuntimeMemory claiming direct promotion
        bad_mem = self.slot.bind_idempotent_effect_and_profile(
            effect_attempt_id="eff-bad-mem",
            retry_idempotency_key="idem-004",
            is_retry=False,
            reconciliation_state=RECONCILIATION_CONFIRMED_ABSENT,
            worker_id="practitioner.worker.a",
            independent_verifier_id="practitioner.verifier.b",
            environment_digest="sha256:env123",
            declared_effects=(),
            runtime_memory=RuntimeMemory(
                memory_id="mem-04",
                loop_id="loop-01",
                scope="turn_local",
                curation_status=STATE_PROMOTED,
                claims_promotion=True,
            ),
        )
        self.assertFalse(bad_mem.succeeded)
        assert bad_mem.refusal is not None
        self.assertEqual(bad_mem.refusal.code, "runtime_memory_must_remain_scoped_candidate_only")


class CheapestEffectiveToolLadderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.orchestrator = CheapestEffectiveToolLadderOrchestrator()

    def test_all_six_tiers_route_to_cheapest_effective_engine(self) -> None:
        cases = (
            (CLASS_MATH_AST, TIER_L0, ENGINE_TIER0_DETERMINISTIC, 0.00000, 0),
            (CLASS_RETRIEVAL_LSH, TIER_L1, ENGINE_TIER1_SIMD_LSH, 0.00000, 0),
            (CLASS_CLASSIFIER, TIER_L2, ENGINE_TIER2_SYSTEM_ONE, 0.00002, 16),
            (CLASS_TIMESERIES_TABULAR, TIER_L3, ENGINE_TIER3_TIMESERIES_TABULAR, 0.00008, 32),
            (CLASS_CONTRACT_CODING, TIER_L4, ENGINE_TIER4_CHEAP_CODING, 0.00045, 140),
            (CLASS_FRONTIER_SYNTHESIS, TIER_L5, ENGINE_TIER5_FRONTIER, 0.01200, 1850),
        )
        for idx, (t_class, expected_tier, expected_engine, expected_cost, expected_tok) in enumerate(cases):
            out = self.orchestrator.execute(
                LadderTaskRequest(
                    task_id=f"tier-route-{idx}",
                    task_class=t_class,
                    prompt_or_expression="glsl sdf shader query",
                    payload={"operation": "math_eval", "a": 6, "b": 7},
                )
            )
            self.assertTrue(out.succeeded, t_class)
            self.assertEqual(out.selected_tier, expected_tier)
            self.assertEqual(out.selected_engine, expected_engine)
            self.assertAlmostEqual(out.total_cost_usd, expected_cost, places=6)
            self.assertEqual(out.total_tokens, expected_tok)

    def test_automatic_fallback_escalation_and_telemetry_utility_adjuster(self) -> None:
        telemetry = ClosedLoopTelemetryUtilityAdjuster()
        orch = CheapestEffectiveToolLadderOrchestrator(telemetry=telemetry)
        initial_gate_l4 = telemetry.effective_confidence_gate(TIER_L4)
        u_l0 = telemetry.expected_utility(TIER_L0, CLASS_MATH_AST)
        u_l5 = telemetry.expected_utility(TIER_L5, CLASS_MATH_AST)
        self.assertGreater(u_l0, u_l5)

        # Simulate L4 verifier failure due to high epistemic uncertainty -> escalates to L5
        escalated = orch.execute(
            LadderTaskRequest(
                task_id="esc-l4-to-l5",
                task_class=CLASS_CONTRACT_CODING,
                prompt_or_expression="Synthesize complex concurrent adapter",
                payload={"function_name": "concurrent_step"},
                epistemic_uncertainty=0.50,
            )
        )
        self.assertTrue(escalated.succeeded)
        self.assertEqual(escalated.selected_tier, TIER_L5)
        self.assertEqual(len(escalated.attempts), 2)
        self.assertFalse(escalated.attempts[0].verifier_passed)
        self.assertTrue(escalated.attempts[1].verifier_passed)
        # L4 failed trial tightens L4 confidence gate
        self.assertGreater(telemetry.effective_confidence_gate(TIER_L4), initial_gate_l4)

    def test_known_wrong_refuses_tier5_frontier_spend_when_tier0_solves(self) -> None:
        refused = self.orchestrator.execute(
            LadderTaskRequest(
                task_id="bad-frontier-spend",
                task_class=CLASS_MATH_AST,
                prompt_or_expression="Convert 5 km to meters",
                payload={"operation": "unit_convert_km_to_m", "km": 5.0},
                force_direct_tier=TIER_L5,
            )
        )
        self.assertFalse(refused.succeeded)
        self.assertEqual(refused.envelope_trace.refused_by, LAYER_PREFLIGHT)
        assert refused.refusal is not None
        self.assertEqual(
            refused.refusal.code,
            "refuse_unnecessary_frontier_spend_when_tier0_solves",
        )

    def test_24_task_head_to_head_benchmark_and_self_test(self) -> None:
        tasks = build_24_benchmark_tasks()
        self.assertEqual(len(tasks), 24)
        bench = run_head_to_head_benchmark()
        strategies = bench["strategies"]
        frontier = strategies[BASELINE_ALWAYS_FRONTIER]
        cheap = strategies[BASELINE_UNVERIFIED_CHEAP]
        ladder = strategies[STRATEGY_BALTOR_6TIER]

        self.assertEqual(ladder["verified_pass_count"], 24)
        self.assertEqual(ladder["verified_pass_rate"], 1.0)
        self.assertLess(ladder["total_cost_usd"], frontier["total_cost_usd"] * 0.20)
        self.assertLess(ladder["total_tokens"], frontier["total_tokens"] * 0.20)
        self.assertGreater(ladder["verified_pass_rate"], cheap["verified_pass_rate"])

        st = self_test()
        self.assertEqual(st["status"], "passed")


if __name__ == "__main__":
    unittest.main()
