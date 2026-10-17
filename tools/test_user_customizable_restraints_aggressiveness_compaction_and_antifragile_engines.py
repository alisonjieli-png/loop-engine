"""Tests for User-Customizable Conditions, Restraints, Aggressiveness, Compaction & Anti-Fragile Typed Edges."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(_REPOSITORY_ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT / "tools"))
if str(_REPOSITORY_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT / "src"))

from user_customizable_restraints_aggressiveness_compaction_and_antifragile_engines import (  # noqa: E402
    AGGRESSIVENESS_PROFILES,
    COMPACTION_MODES,
    RESPONSE_STYLE_MODES,
    TYPED_EDGE_FAMILIES,
    AntiFragileEdgeRequest,
    EdgeCompatibilityAdapter,
    EdgeRegressionFixture,
    UserPolicyExecutionRequest,
    UserRestraintLogicSpec,
    evaluate_user_customizable_and_antifragile_benchmark,
    resolve_aggressiveness_profile,
    run_antifragile_self_improving_typed_edge_slot,
    run_user_policy_aggressiveness_compaction_style_slot,
    sha256_hex,
)


def _sample_restraint_spec() -> UserRestraintLogicSpec:
    return UserRestraintLogicSpec(
        when_predicates=(
            "when latency_budget_ms < 50 force L0_or_rust_engine",
            "when domain == 'finance' require decimal_fixed_point",
        ),
        require_conditions=(
            "require decimal fixed-point on currency columns",
            "require explicit verifier pass before file write",
        ),
        forbid_restraints=(
            "forbid modifying database migrations",
            "forbid dropping production tables",
            "forbid touching /home/username/loop-engine",
        ),
        pinned_invariants=("invariant_currency_decimal_fixed_point", "invariant_no_migration_edits"),
        task_capsule_sha256=sha256_hex("test-capsule-digest"),
    )


def _sample_source() -> str:
    return "\n".join(
        [
            '"""Sample module for compaction testing."""',
            "class LedgerEngine:",
            "    def compute_balance(self, cents: int) -> str:",
            '        """Compute fixed-point balance."""',
        ]
        + [f"        v_{i} = {i} + 1" for i in range(1, 60)]
        + ["        return str(cents)"]
    )


class UserCustomizablePolicyAndAntiFragileEdgeTests(unittest.TestCase):
    """Verify Slot Family 1, Slot Family 2, 32-scenario benchmark, and 4 known-wrong controls."""

    def test_five_calibrated_aggressiveness_profiles_and_continuous_interpolation(self) -> None:
        expected_anchors = {
            0.00: "ultra_conservative_surgical_patch_only",
            0.25: "guarded_incremental",
            0.50: "balanced_autonomous_standard",
            0.75: "proactive_multi_file_refactor_and_test_expansion",
            1.00: "maximal_overnight_autonomous_swarm",
        }
        for alpha, expected_name in expected_anchors.items():
            name, bounds = resolve_aggressiveness_profile(alpha)
            self.assertEqual(name, expected_name)
            self.assertEqual(bounds["max_files_touched"], AGGRESSIVENESS_PROFILES[expected_name]["max_files_touched"])

        interp_name, interp_bounds = resolve_aggressiveness_profile(0.35)
        self.assertEqual(interp_name, "guarded_incremental")
        self.assertGreaterEqual(interp_bounds["max_files_touched"], 3)

    def test_four_tier_compaction_modes_and_pinned_restraint_retention(self) -> None:
        spec = _sample_restraint_spec()
        src = _sample_source()
        reductions: dict[str, float] = {}
        for mode in COMPACTION_MODES:
            req = UserPolicyExecutionRequest(
                request_id=f"test_comp_{mode}",
                restraint_spec=spec,
                alpha_agg=0.50,
                compaction_mode=mode,
                response_style="surgical_diff_and_receipt_only",
                proposed_action={"target": "src/ledger.py", "verb": "edit", "latency_budget_ms": 20.0},
                source_code_text=src,
                draft_response_text="Updated ledger calculation.",
            )
            res = run_user_policy_aggressiveness_compaction_style_slot(req)
            self.assertTrue(res.ok)
            self.assertEqual(res.pinned_restraint_retention_ratio, 1.0)
            self.assertIn(spec.task_capsule_sha256, res.compacted_context_text)
            self.assertEqual(res.effective_execution_bounds.get("forced_routing_tier"), "L0_or_rust_engine")
            reductions[mode] = res.token_reduction_ratio

        self.assertEqual(reductions["C0_lossless_full_source"], 0.0)
        self.assertGreater(reductions["C1_ast_symbol_and_docstring_skeleton"], 0.70)
        self.assertGreater(reductions["C2_contract_card_and_active_span_only"], 0.90)
        self.assertGreater(reductions["C3_ultra_dense_64tok_pinned_digest"], 0.96)

    def test_all_six_response_style_modes_and_slot1_engine_failover(self) -> None:
        spec = _sample_restraint_spec()
        src = _sample_source()
        for style in RESPONSE_STYLE_MODES:
            req = UserPolicyExecutionRequest(
                request_id=f"test_style_{style}",
                restraint_spec=spec,
                alpha_agg=0.25,
                compaction_mode="C1_ast_symbol_and_docstring_skeleton",
                response_style=style,
                proposed_action={"target": "src/app.py", "verb": "patch"},
                source_code_text=src,
                draft_response_text="Benchmarked and verified component.",
                simulate_primary_engine_deferral=(style == "machine_json_contract_only"),
            )
            res = run_user_policy_aggressiveness_compaction_style_slot(req)
            self.assertTrue(res.ok)
            self.assertTrue(bool(res.formatted_response))
            if style == "machine_json_contract_only":
                self.assertEqual(res.selected_engine, "conservative_contract_card_policy_fallback_engine")
                self.assertEqual(len(res.attempted_engines), 2)

    def test_eight_typed_compatibility_edge_families_and_antifragile_caching(self) -> None:
        shim_registry: dict[str, EdgeCompatibilityAdapter] = {}
        fixture_registry: list[EdgeRegressionFixture] = []

        for idx, edge_family in enumerate(TYPED_EDGE_FAMILIES):
            req = AntiFragileEdgeRequest(
                request_id=f"edge_test_{idx}",
                edge_family=edge_family,
                source_schema="contract/v1",
                target_schema="contract/v2",
                inbound_payload={
                    "legacy_id": f"ent_{idx}",
                    "amount_cents": 5000,
                    "length_mm": 1500.0,
                    "function": {"name": "invoke_edge", "parameters": {"mode": "fast"}},
                    "batch_items": ["x", "y"],
                    "columns": {"c1": [10, 20], "c2": [30, 40]},
                    "py_floats": [0.5, 1.5],
                    "cloud_lease_token": "tok_abc",
                    "soap_body_xml": "<Envelope><Body>Hello</Body></Envelope>",
                },
                required_target_fields=(
                    "entity_id",
                    "amount_usd_decimal",
                    "length_m",
                    "tool_name",
                    "stream_chunks",
                    "typed_rows",
                    "f64_slice_descriptor",
                    "loopback_endpoint_grant",
                    "rest_utf8_json",
                ),
                stressor_type="schema_v1_to_v2_field_rename_shock",
                simulate_primary_engine_deferral=(idx == 7),
            )
            first = run_antifragile_self_improving_typed_edge_slot(req, shim_registry, fixture_registry)
            self.assertTrue(first.ok)
            self.assertTrue(first.shock_encountered)
            self.assertTrue(first.synthesized_new_shim)
            self.assertFalse(first.cache_hit)
            self.assertIsNotNone(first.adapter_shim)
            self.assertIsNotNone(first.regression_fixture)
            self.assertEqual(first.adapted_payload["entity_id"], f"ent_{idx}")
            self.assertEqual(first.adapted_payload["amount_usd_decimal"], "50.00")
            self.assertEqual(first.adapted_payload["length_m"], 1.5)

            second = run_antifragile_self_improving_typed_edge_slot(req, shim_registry, fixture_registry)
            self.assertTrue(second.ok)
            self.assertTrue(second.cache_hit)
            self.assertFalse(second.synthesized_new_shim)
            self.assertLess(second.latency_ms, first.latency_ms)

        self.assertEqual(len(shim_registry), 8)
        self.assertEqual(len(fixture_registry), 8)

    def test_four_known_wrong_controls_refused_before_effects(self) -> None:
        spec = _sample_restraint_spec()
        src = _sample_source()

        # (a) alpha_agg = 1.0 attempting to override user forbid restraint
        res_forbid = run_user_policy_aggressiveness_compaction_style_slot(
            UserPolicyExecutionRequest(
                request_id="kw_a",
                restraint_spec=spec,
                alpha_agg=1.00,
                compaction_mode="C1_ast_symbol_and_docstring_skeleton",
                response_style="surgical_diff_and_receipt_only",
                proposed_action={"target": "db/migrations/0001_init.sql", "verb": "edit"},
                source_code_text=src,
                draft_response_text="Edited migration.",
            )
        )
        self.assertFalse(res_forbid.ok)
        self.assertIsNotNone(res_forbid.refusal)
        assert res_forbid.refusal is not None
        self.assertEqual(res_forbid.refusal.code, "user_forbid_restraint_override_refused")
        self.assertFalse(res_forbid.envelope_trace.engine_dispatched)

        # (b) Context compaction dropping pinned user restraint or TaskCapsule digest
        res_comp_drop = run_user_policy_aggressiveness_compaction_style_slot(
            UserPolicyExecutionRequest(
                request_id="kw_b",
                restraint_spec=spec,
                alpha_agg=0.50,
                compaction_mode="C3_ultra_dense_64tok_pinned_digest",
                response_style="surgical_diff_and_receipt_only",
                proposed_action={"target": "src/ok.py", "verb": "edit"},
                source_code_text=src,
                draft_response_text="Compacted.",
                simulate_drop_pinned_restraint=True,
            )
        )
        self.assertFalse(res_comp_drop.ok)
        assert res_comp_drop.refusal is not None
        self.assertEqual(res_comp_drop.refusal.code, "compaction_dropped_pinned_restraint_refused")
        self.assertFalse(res_comp_drop.envelope_trace.engine_dispatched)

        # (c) Response style ending with questions under concise_decisions_and_benchmarks_no_questions
        res_questions = run_user_policy_aggressiveness_compaction_style_slot(
            UserPolicyExecutionRequest(
                request_id="kw_c",
                restraint_spec=spec,
                alpha_agg=0.50,
                compaction_mode="C1_ast_symbol_and_docstring_skeleton",
                response_style="concise_decisions_and_benchmarks_no_questions",
                proposed_action={"target": "src/ok.py", "verb": "edit"},
                source_code_text=src,
                draft_response_text="Completed analysis. Should I proceed with option 1 or option 2?",
            )
        )
        self.assertFalse(res_questions.ok)
        assert res_questions.refusal is not None
        self.assertEqual(res_questions.refusal.code, "response_style_trailing_questions_refused")
        self.assertFalse(res_questions.envelope_trace.engine_dispatched)

        # (d) Anti-fragile edge shim silently dropping required fields or fabricating data
        res_shim_drop = run_antifragile_self_improving_typed_edge_slot(
            AntiFragileEdgeRequest(
                request_id="kw_d",
                edge_family="json_schema_v1_v2_evolution_edge",
                source_schema="contract/v1",
                target_schema="contract/v2",
                inbound_payload={"legacy_id": "99"},
                required_target_fields=("entity_id",),
                stressor_type="schema_v1_to_v2_field_rename_shock",
                simulate_silent_field_drop_or_fabrication=True,
            ),
            {},
            [],
        )
        self.assertFalse(res_shim_drop.ok)
        assert res_shim_drop.refusal is not None
        self.assertEqual(res_shim_drop.refusal.code, "antifragile_shim_silent_field_drop_or_fabrication_refused")
        self.assertFalse(res_shim_drop.envelope_trace.engine_dispatched)

    def test_full_32_scenario_benchmark_metrics(self) -> None:
        report = evaluate_user_customizable_and_antifragile_benchmark()
        self.assertEqual(report["total_scenarios"], 32)
        self.assertEqual(report["total_shock_scenarios"], 24)

        base = report["rigid_fragile_unconfigurable_pipeline_baseline"]
        baltor = report["baltor_customizable_and_antifragile_edge_suite"]
        self.assertEqual(base["user_restraint_violation_rate_pct"], 34.4)
        self.assertEqual(baltor["user_restraint_violation_rate_pct"], 0.0)
        self.assertEqual(base["shock_recovery_rate_pct"], 0.0)
        self.assertEqual(baltor["shock_recovery_rate_pct"], 100.0)
        self.assertEqual(baltor["permanently_learned_edge_shims"], 24)
        self.assertEqual(baltor["permanent_regression_fixtures_generated"], 24)
        self.assertTrue(all(report["known_wrong_controls"].values()))


if __name__ == "__main__":
    unittest.main()
