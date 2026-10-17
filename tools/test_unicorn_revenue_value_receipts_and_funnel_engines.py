"""Tests for Pillar 7: Multi-Tier Revenue Expansion, Automated Value Receipts, and 20-Surface Funnel Engines.

Covers:
1. Slot Family 1 (`multi_tier_monetization_and_upgrade_slot`):
   - Verification of the 7 owner-authorized revenue tiers (`basic`, `pro`, `founding`, `baltor_max`,
     `baltor_team`, `agentbriefs_single`, `agentbriefs_quarterly`).
   - Head-to-head comparison of `static_paywall_without_baltor` vs
     `usage_milestone_and_roi_triggered_upgrade_engine` and
     `sponsored_playground_and_referral_monetization_engine`.
   - Known-wrong controls: charging `Basic` before January 1, 2027 (`basic_tier_billing_forbidden_before_2027`)
     and missing paid-link disclosure on sponsored placements (`sponsored_brief_missing_paid_link_disclosure`).
2. Slot Family 2 (`automated_value_receipt_and_retention_slot`):
   - Audit-backed `BaltorValueReceipt` compilation (`tokens_saved_by_contract_cards`,
     `unchanged_files_preserved_from_regeneration`, `retry_loops_healed_on_turn_1`,
     `leakage_and_security_defects_blocked_by_preflight`, `estimated_compute_and_engineering_hours_saved`,
     `net_roi_multiple_vs_subscription_price`).
   - 1-click MCP self-healing repair command generation when an IDE update drops the local harness connection.
   - Known-wrong control: rejecting synthetic/unverified token savings not backed by meter spans
     (`unverified_synthetic_token_savings_in_value_receipt`).
3. Slot Family 3 (`multi_brand_organic_conversion_router_slot`):
   - Routing all 20 specialized brand and organic entry surfaces (`agentfeeds.si`, `agentstudios.si`,
     `agentafk.si`, `agentfoundry.si`, `agentbriefs.si`, `demos.baltor.ai`, `deterministicskills.baltor.ai`,
     `tools.baltor.ai`, `cornercases.baltor.ai`, `skillsforgood.org`, `baltor.ai`) into shared-account
     conversion flows while enforcing zero cross-domain cookies and positive copy.
   - Preflight self-repair of stale backend release digests and known-wrong refusal on cross-brand cookies.
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
    LAYER_CARRIER,
    LAYER_HANDSHAKE,
    LAYER_PREFLIGHT,
)
from unicorn_revenue_value_receipts_and_funnel_engines import (  # noqa: E402
    BASIC_FREE_THROUGH_DATE,
    ENGINE_CRYPTOGRAPHIC_VALUE_RECEIPT,
    ENGINE_ENTITLEMENT_HANDOFF_FUNNEL,
    ENGINE_INACTIVE_HARNESS_NUDGE,
    ENGINE_INTENT_QUALIFIED_FUNNEL,
    ENGINE_SPONSORED_AND_REFERRAL,
    ENGINE_STATIC_PAYWALL_BASELINE,
    ENGINE_USAGE_MILESTONE_ROI_UPGRADE,
    FOUNDING_MEMBER_MAX_SLOTS,
    OWNER_AUTHORIZED_REVENUE_LADDER,
    REQUIRED_SPONSORED_DISCLOSURE,
    TWENTY_SURFACE_FUNNEL_SPECS,
    AutomatedValueReceiptOrchestrator,
    MonetizationEvaluationRequest,
    MultiBrandFunnelRequest,
    MultiBrandOrganicConversionOrchestrator,
    MultiTierMonetizationOrchestrator,
    ValueReceiptRequest,
    run_unicorn_revenue_and_funnel_benchmark,
    self_test,
)


class MultiTierMonetizationSlotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.orchestrator = MultiTierMonetizationOrchestrator()

    def test_owner_authorized_revenue_ladder_tiers_and_invariants(self) -> None:
        self.assertEqual(
            set(OWNER_AUTHORIZED_REVENUE_LADDER.keys()),
            {
                "basic",
                "pro",
                "founding",
                "baltor_max",
                "baltor_team",
                "agentbriefs_single",
                "agentbriefs_quarterly",
            },
        )
        basic = OWNER_AUTHORIZED_REVENUE_LADDER["basic"]
        self.assertEqual(basic.monthly_price_usd, 9)
        self.assertEqual(basic.free_through_date, BASIC_FREE_THROUGH_DATE)

        founding = OWNER_AUTHORIZED_REVENUE_LADDER["founding"]
        self.assertEqual(founding.monthly_price_usd, 49)
        self.assertEqual(founding.slot_cap, FOUNDING_MEMBER_MAX_SLOTS)

        self.assertEqual(OWNER_AUTHORIZED_REVENUE_LADDER["baltor_max"].monthly_price_usd, 99)
        self.assertEqual(OWNER_AUTHORIZED_REVENUE_LADDER["baltor_team"].monthly_price_usd, 199)
        self.assertEqual(OWNER_AUTHORIZED_REVENUE_LADDER["baltor_team"].seat_allowance, 5)
        self.assertEqual(OWNER_AUTHORIZED_REVENUE_LADDER["agentbriefs_single"].monthly_price_usd, 299)
        self.assertEqual(OWNER_AUTHORIZED_REVENUE_LADDER["agentbriefs_quarterly"].monthly_price_usd, 799)

    def test_roi_triggered_upgrade_engine_outperforms_static_paywall_baseline(self) -> None:
        req = MonetizationEvaluationRequest(
            request_id="test-upgrade-pro",
            account_id="acct-dev-10",
            current_tier="basic",
            evaluation_date_iso="2027-01-15",
            charge_amount_usd=9,
            verified_tokens_saved=450_000,
            materialized_components_count=9,
            active_worktree_swarms=0,
            team_seats_requested=1,
            referral_qualified_signups=2,
        )
        roi_resp = self.orchestrator.handle(req)
        self.assertTrue(roi_resp.succeeded)
        self.assertEqual(roi_resp.selected_engine, ENGINE_USAGE_MILESTONE_ROI_UPGRADE)
        self.assertEqual(roi_resp.recommended_tier, "pro")
        self.assertTrue(roi_resp.upgrade_prompt_triggered)
        self.assertEqual(roi_resp.referral_credit_usd, 30)

        static_orch = MultiTierMonetizationOrchestrator(engine_order=(ENGINE_STATIC_PAYWALL_BASELINE,))
        static_resp = static_orch.handle(req)
        self.assertTrue(static_resp.succeeded)
        self.assertGreater(roi_resp.conversion_rate_estimate, static_resp.conversion_rate_estimate)
        self.assertLess(roi_resp.churn_risk_score, static_resp.churn_risk_score)

    def test_known_wrong_charging_basic_before_2027_is_refused_in_handshake(self) -> None:
        resp = self.orchestrator.handle(
            MonetizationEvaluationRequest(
                request_id="test-basic-early-charge",
                account_id="acct-basic-2026",
                current_tier="basic",
                evaluation_date_iso="2026-12-15",
                charge_amount_usd=9,
                verified_tokens_saved=100_000,
                materialized_components_count=2,
                active_worktree_swarms=0,
                team_seats_requested=1,
            )
        )
        self.assertFalse(resp.succeeded)
        self.assertFalse(resp.trace.engine_dispatched)
        self.assertEqual(resp.trace.refused_by, LAYER_HANDSHAKE)
        assert resp.refusal is not None
        self.assertEqual(resp.refusal.code, "basic_tier_billing_forbidden_before_2027")

    def test_known_wrong_sponsored_placement_without_paid_link_wording_is_refused_in_preflight(self) -> None:
        resp = self.orchestrator.handle(
            MonetizationEvaluationRequest(
                request_id="test-missing-disclosure",
                account_id="acct-sponsor-1",
                current_tier="pro",
                evaluation_date_iso="2026-10-17",
                charge_amount_usd=49,
                verified_tokens_saved=300_000,
                materialized_components_count=6,
                active_worktree_swarms=0,
                team_seats_requested=1,
                is_sponsored_placement=True,
                sponsored_disclosure_text="Partner spotlight without paid link disclosure",
            )
        )
        self.assertFalse(resp.succeeded)
        self.assertFalse(resp.trace.engine_dispatched)
        self.assertEqual(resp.trace.refused_by, LAYER_PREFLIGHT)
        assert resp.refusal is not None
        self.assertEqual(resp.refusal.code, "sponsored_brief_missing_paid_link_disclosure")

    def test_automatic_fallback_from_primary_to_sponsored_referral_engine(self) -> None:
        resp = self.orchestrator.handle(
            MonetizationEvaluationRequest(
                request_id="test-monetization-fallback",
                account_id="acct-max-1",
                current_tier="pro",
                evaluation_date_iso="2026-10-17",
                charge_amount_usd=49,
                verified_tokens_saved=900_000,
                materialized_components_count=20,
                active_worktree_swarms=3,
                team_seats_requested=1,
                is_sponsored_placement=True,
                sponsored_disclosure_text=REQUIRED_SPONSORED_DISCLOSURE,
                simulate_primary_deferral=True,
            )
        )
        self.assertTrue(resp.succeeded)
        self.assertEqual(resp.selected_engine, ENGINE_SPONSORED_AND_REFERRAL)
        self.assertEqual(
            resp.attempted_engines,
            (ENGINE_USAGE_MILESTONE_ROI_UPGRADE, ENGINE_SPONSORED_AND_REFERRAL),
        )
        self.assertEqual(resp.recommended_tier, "baltor_max")
        self.assertEqual(resp.frame.depth, 1)


class AutomatedValueReceiptSlotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.orchestrator = AutomatedValueReceiptOrchestrator()

    def test_compiles_cryptographic_value_receipt_and_1_click_mcp_repair_command(self) -> None:
        resp = self.orchestrator.handle(
            ValueReceiptRequest(
                request_id="test-vr-healed",
                account_id="acct-cursor-9",
                subscription_tier="baltor_max",
                subscription_price_usd=99,
                verified_meter_span_ids=("span-a1", "span-a2", "span-a3"),
                tokens_saved_by_contract_cards=1_200_000,
                unchanged_files_preserved_from_regeneration=32,
                retry_loops_healed_on_turn_1=14,
                leakage_and_security_defects_blocked_by_preflight=6,
                ide_harness_name="cursor",
                mcp_connection_dropped_after_ide_update=True,
            )
        )
        self.assertTrue(resp.succeeded)
        self.assertEqual(resp.selected_engine, ENGINE_CRYPTOGRAPHIC_VALUE_RECEIPT)
        self.assertTrue(resp.self_healing_nudge_dispatched)
        self.assertTrue(resp.silent_churn_prevented)
        assert resp.receipt is not None
        self.assertEqual(resp.receipt.tokens_saved_by_contract_cards, 1_200_000)
        self.assertGreater(resp.receipt.net_roi_multiple_vs_subscription_price, 10.0)
        self.assertEqual(
            resp.receipt.one_click_mcp_repair_command,
            "loop-engine mcp repair --harness cursor --verify-handshake",
        )

    def test_known_wrong_synthetic_token_savings_refused_in_preflight(self) -> None:
        resp = self.orchestrator.handle(
            ValueReceiptRequest(
                request_id="test-vr-synthetic-bad",
                account_id="acct-synthetic",
                subscription_tier="pro",
                subscription_price_usd=49,
                verified_meter_span_ids=("span-01",),
                tokens_saved_by_contract_cards=400_000,
                unchanged_files_preserved_from_regeneration=8,
                retry_loops_healed_on_turn_1=3,
                leakage_and_security_defects_blocked_by_preflight=1,
                unverified_synthetic_tokens_claimed=100_000,
            )
        )
        self.assertFalse(resp.succeeded)
        self.assertFalse(resp.trace.engine_dispatched)
        self.assertEqual(resp.trace.refused_by, LAYER_PREFLIGHT)
        assert resp.refusal is not None
        self.assertEqual(resp.refusal.code, "unverified_synthetic_token_savings_in_value_receipt")

    def test_automatic_fallback_to_inactive_harness_nudge_engine(self) -> None:
        resp = self.orchestrator.handle(
            ValueReceiptRequest(
                request_id="test-vr-fallback",
                account_id="acct-team-5",
                subscription_tier="baltor_team",
                subscription_price_usd=199,
                verified_meter_span_ids=("span-t1", "span-t2"),
                tokens_saved_by_contract_cards=2_400_000,
                unchanged_files_preserved_from_regeneration=60,
                retry_loops_healed_on_turn_1=22,
                leakage_and_security_defects_blocked_by_preflight=9,
                simulate_primary_deferral=True,
            )
        )
        self.assertTrue(resp.succeeded)
        self.assertEqual(resp.selected_engine, ENGINE_INACTIVE_HARNESS_NUDGE)
        self.assertEqual(
            resp.attempted_engines,
            (ENGINE_CRYPTOGRAPHIC_VALUE_RECEIPT, ENGINE_INACTIVE_HARNESS_NUDGE),
        )


class MultiBrandOrganicConversionRouterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.orchestrator = MultiBrandOrganicConversionOrchestrator()

    def test_routes_all_twenty_surfaces_with_zero_cross_domain_cookies_and_positive_copy(self) -> None:
        self.assertEqual(len(TWENTY_SURFACE_FUNNEL_SPECS), 20)
        distinct_hosts = {s.hostname for s in TWENTY_SURFACE_FUNNEL_SPECS}
        self.assertEqual(
            distinct_hosts,
            {
                "agentfeeds.si",
                "agentstudios.si",
                "agentafk.si",
                "agentfoundry.si",
                "agentbriefs.si",
                "demos.baltor.ai",
                "deterministicskills.baltor.ai",
                "tools.baltor.ai",
                "cornercases.baltor.ai",
                "skillsforgood.org",
                "baltor.ai",
            },
        )
        for spec in TWENTY_SURFACE_FUNNEL_SPECS:
            resp = self.orchestrator.handle(
                MultiBrandFunnelRequest(
                    request_id=f"test-route-{spec.surface_id}",
                    surface_id=spec.surface_id,
                )
            )
            self.assertTrue(resp.succeeded, spec.surface_id)
            self.assertEqual(resp.selected_engine, ENGINE_INTENT_QUALIFIED_FUNNEL)
            self.assertTrue(resp.zero_cross_domain_cookies_verified)
            self.assertTrue(resp.positive_humanizer_copy_verified)
            self.assertTrue(resp.paid_link_disclosure_verified)
            self.assertIn(spec.hostname, resp.entry_url)
            self.assertIn(f"tier={spec.recommended_tier}", resp.shared_account_checkout_url)

    def test_known_wrong_cross_brand_cookie_on_standalone_surface_is_refused_in_handshake(self) -> None:
        resp = self.orchestrator.handle(
            MultiBrandFunnelRequest(
                request_id="test-cookie-leak",
                surface_id="s19_skillsforgood_civic",
                carries_cross_brand_session_cookie=True,
            )
        )
        self.assertFalse(resp.succeeded)
        self.assertFalse(resp.trace.engine_dispatched)
        self.assertEqual(resp.trace.refused_by, LAYER_HANDSHAKE)
        assert resp.refusal is not None
        self.assertEqual(resp.refusal.code, "cross_brand_session_cookie_leakage_on_entry_surface")

    def test_preflight_self_repairs_stale_release_digest_and_refuses_when_disabled(self) -> None:
        repaired_resp = self.orchestrator.handle(
            MultiBrandFunnelRequest(
                request_id="test-digest-repair",
                surface_id="s03_agentstudios_3d",
                backend_release_digest="18f00a11",
                allow_digest_repair=True,
            )
        )
        self.assertTrue(repaired_resp.succeeded)
        self.assertTrue(repaired_resp.preflight_repaired)

        refused_resp = self.orchestrator.handle(
            MultiBrandFunnelRequest(
                request_id="test-digest-refuse",
                surface_id="s03_agentstudios_3d",
                backend_release_digest="18f00a11",
                allow_digest_repair=False,
            )
        )
        self.assertFalse(refused_resp.succeeded)
        self.assertFalse(refused_resp.trace.engine_dispatched)
        self.assertEqual(refused_resp.trace.refused_by, LAYER_PREFLIGHT)
        assert refused_resp.refusal is not None
        self.assertEqual(refused_resp.refusal.code, "stale_funnel_release_digest")

    def test_carrier_layer_refuses_unsupported_wire_schema_and_fallback_works(self) -> None:
        bad_schema_resp = self.orchestrator.handle(
            MultiBrandFunnelRequest(
                request_id="test-bad-schema",
                surface_id="s01_agentfeeds_live",
                schema="multi_brand_funnel_router_request/v99",
            )
        )
        self.assertFalse(bad_schema_resp.succeeded)
        self.assertEqual(bad_schema_resp.trace.refused_by, LAYER_CARRIER)

        fallback_resp = self.orchestrator.handle(
            MultiBrandFunnelRequest(
                request_id="test-funnel-fallback",
                surface_id="s09_agentbriefs_single",
                simulate_primary_deferral=True,
            )
        )
        self.assertTrue(fallback_resp.succeeded)
        self.assertEqual(fallback_resp.selected_engine, ENGINE_ENTITLEMENT_HANDOFF_FUNNEL)

    def test_end_to_end_benchmark_and_self_test_pass(self) -> None:
        result = self_test()
        self.assertTrue(result["passed"])
        report = run_unicorn_revenue_and_funnel_benchmark()
        self.assertTrue(report["known_wrong_probes"]["all_blocked_before_engine"])
        self.assertEqual(report["known_wrong_probes"]["total_probes"], 4)


if __name__ == "__main__":
    unittest.main()
