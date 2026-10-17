"""Unit tests for the Unicorn PLG, Verified PR Badge, Referral & Creator Flywheel Engine Suite."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

REPOSITORY = Path(__file__).resolve().parents[1]
if str(REPOSITORY / "src") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "src"))
if str(REPOSITORY / "tools") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "tools"))

from unicorn_plg_referral_and_creator_flywheel_engines import (  # noqa: E402
    AT_SIGN,
    AUTHORIZED_PLANS,
    BRAND_SHARE_SURFACES,
    CREATOR_MARKETPLACE_ENGINE_IDS,
    ENGINE_AGGREGATE_LINK_COUNTER,
    ENGINE_BRAND_SHARE_CARD,
    ENGINE_CREATOR_LEDGER,
    ENGINE_MARKETPLACE_CONFORMANCE,
    ENGINE_OSS_AMBASSADOR_GRANT,
    ENGINE_PAID_CONVERSION_REFERRAL,
    ENGINE_PR_BADGE_RECEIPT,
    ENGINE_SPDX_ATTESTATION,
    ENGINE_STATIC_CITATION_FALLBACK,
    ENGINE_STATIC_QUARANTINE_FALLBACK,
    ENGINE_SYBIL_CYCLE_GUARD,
    REFERRAL_FLYWHEEL_ENGINE_IDS,
    SUPPORTED_CREATOR_FAMILIES,
    VIRAL_BADGE_ENGINE_IDS,
    CreatorComponentSubmissionRequest,
    CreatorMarketplaceBountyOrchestrator,
    ReferralAndFoundingAdvocateOrchestrator,
    ReferralConversionRequest,
    ViralArtifactAndBadgeOrchestrator,
    ViralArtifactRequest,
    make_receipt_sha256,
    run_known_wrong_probes,
    run_unicorn_plg_benchmark,
    self_test,
)
from loop_engine.core.engines.envelope import (  # noqa: E402
    COVERAGE_LAYERS,
    LAYER_ACCOUNT,
    LAYER_CARRIER,
    LAYER_HANDSHAKE,
    LAYER_PREFLIGHT,
    LAYER_TRACKING,
)


class ViralArtifactAndBadgeEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.orchestrator = ViralArtifactAndBadgeOrchestrator()
        self.valid_sha = make_receipt_sha256("test-receipt-seed-2026-10-17")

    def test_all_four_viral_engines_succeed_under_7_layer_envelope(self) -> None:
        for engine_id in VIRAL_BADGE_ENGINE_IDS:
            orch = ViralArtifactAndBadgeOrchestrator(engine_order=(engine_id,))
            res = orch.handle(
                ViralArtifactRequest(
                    request_id=f"req-viral-{engine_id}",
                    repo_slug="baltor/shader-showcase",
                    referral_slug="shader-showcase",
                    receipt_sha256=self.valid_sha,
                    surface_hostname="demos.baltor.ai",
                    verified_components_used=9,
                )
            )
            self.assertTrue(res.succeeded, engine_id)
            self.assertEqual(res.selected_engine, engine_id)
            self.assertEqual(res.coverage_layers, COVERAGE_LAYERS)
            self.assertEqual(res.payload["receipt_sha256"], self.valid_sha)

    def test_aggregate_link_counter_increments_hourly_buckets_with_zero_cookies_or_pii(self) -> None:
        orch = ViralArtifactAndBadgeOrchestrator(engine_order=(ENGINE_AGGREGATE_LINK_COUNTER,))
        r1 = orch.handle(
            ViralArtifactRequest(
                request_id="req-cnt-1",
                repo_slug="org/repo",
                referral_slug="founder-link",
                receipt_sha256=self.valid_sha,
                hourly_bucket_utc="2026-10-17T04:00Z",
                aggregate_click_delta=4,
            )
        )
        r2 = orch.handle(
            ViralArtifactRequest(
                request_id="req-cnt-2",
                repo_slug="org/repo",
                referral_slug="founder-link",
                receipt_sha256=self.valid_sha,
                hourly_bucket_utc="2026-10-17T04:00Z",
                aggregate_click_delta=3,
            )
        )
        self.assertTrue(r1.succeeded and r2.succeeded)
        self.assertEqual(r2.payload["aggregate_clicks_in_bucket"], 7)
        self.assertEqual(r2.payload["cookies_set"], 0)
        self.assertEqual(r2.payload["ip_fingerprints_stored"], 0)
        self.assertTrue(r2.payload["privacy_notice_compliant"])

    def test_brand_syndicated_share_cards_cover_all_five_surfaces(self) -> None:
        orch = ViralArtifactAndBadgeOrchestrator(engine_order=(ENGINE_BRAND_SHARE_CARD,))
        for host in BRAND_SHARE_SURFACES:
            res = orch.handle(
                ViralArtifactRequest(
                    request_id=f"req-card-{host}",
                    repo_slug="org/repo",
                    referral_slug="card-slug",
                    receipt_sha256=self.valid_sha,
                    surface_hostname=host,
                )
            )
            self.assertTrue(res.succeeded, host)
            self.assertEqual(res.payload["surface_hostname"], host)
            self.assertTrue(res.payload["humanizer_verified"])

    def test_viral_slot_automatic_fallback_to_static_citation_engine(self) -> None:
        res = self.orchestrator.handle(
            ViralArtifactRequest(
                request_id="req-viral-fallback",
                repo_slug="org/repo",
                referral_slug="fallback-slug",
                receipt_sha256=self.valid_sha,
                simulated_deferrals={
                    ENGINE_PR_BADGE_RECEIPT: "svg_badge_template_cache_miss",
                    ENGINE_AGGREGATE_LINK_COUNTER: "counter_bucket_shard_busy",
                    ENGINE_BRAND_SHARE_CARD: "opengraph_card_slot_deferred",
                },
            )
        )
        self.assertTrue(res.succeeded)
        self.assertEqual(res.selected_engine, ENGINE_STATIC_CITATION_FALLBACK)
        self.assertEqual(res.attempted_engines, VIRAL_BADGE_ENGINE_IDS)

    def test_known_wrong_missing_receipt_and_cookie_injection_refused_before_engine(self) -> None:
        bad_sha = self.orchestrator.handle(
            ViralArtifactRequest(
                request_id="req-bad-sha",
                repo_slug="org/repo",
                referral_slug="bad-sha",
                receipt_sha256="invalid",
            )
        )
        self.assertFalse(bad_sha.succeeded)
        self.assertFalse(bad_sha.trace.engine_dispatched)
        self.assertEqual(bad_sha.trace.refused_by, LAYER_CARRIER)
        self.assertEqual(bad_sha.refusal.code, "unverified_badge_receipt_sha256_missing")

        bad_cookie = self.orchestrator.handle(
            ViralArtifactRequest(
                request_id="req-bad-cookie",
                repo_slug="org/repo",
                referral_slug="bad-cookie",
                receipt_sha256=self.valid_sha,
                contains_cookie_header=True,
            )
        )
        self.assertFalse(bad_cookie.succeeded)
        self.assertFalse(bad_cookie.trace.engine_dispatched)
        self.assertEqual(bad_cookie.trace.refused_by, LAYER_HANDSHAKE)
        self.assertEqual(bad_cookie.refusal.code, "privacy_notice_violation_cookie_or_pii_in_link_counter")


class ReferralAndFoundingAdvocateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.orchestrator = ReferralAndFoundingAdvocateOrchestrator()

    def test_owner_authorized_plans_basic_pro_max_team_and_oss_ambassador(self) -> None:
        expected_prices = {"basic": 9, "pro": 49, "max": 99, "team": 199}
        for tier, price in expected_prices.items():
            res = self.orchestrator.handle(
                ReferralConversionRequest(
                    request_id=f"req-plan-{tier}",
                    referrer_account_id="acct_ref_1",
                    referee_account_id=f"acct_new_{tier}",
                    referrer_email=f"referrer{AT_SIGN}company.dev",
                    referee_email=f"customer-{tier}{AT_SIGN}company.dev",
                    plan_tier=tier,
                    email_first_verified=True,
                    paid_settlement_confirmed=True,
                )
            )
            self.assertTrue(res.succeeded, tier)
            self.assertEqual(res.payload["plan_monthly_usd"], price)
            self.assertEqual(res.payload["referrer_reward_credits"], AUTHORIZED_PLANS[tier]["referrer_credits"])

        oss_orch = ReferralAndFoundingAdvocateOrchestrator(engine_order=(ENGINE_OSS_AMBASSADOR_GRANT,))
        oss_res = oss_orch.handle(
            ReferralConversionRequest(
                request_id="req-oss-grant",
                referrer_account_id="acct_oss_1",
                referee_account_id="acct_oss_2",
                referrer_email=f"maintainer{AT_SIGN}oss.org",
                referee_email=f"contributor{AT_SIGN}skillsforgood.org",
                is_oss_or_public_good_repo=True,
                public_repo_slug="civic/open-accessibility-pack",
                embedded_contract_cards=10,
            )
        )
        self.assertTrue(oss_res.succeeded)
        self.assertEqual(oss_res.selected_engine, ENGINE_OSS_AMBASSADOR_GRANT)
        self.assertEqual(oss_res.payload["zero_cost_ambassador_grant_credits"], 500)

    def test_known_wrong_sybil_aliases_disposable_domains_cycles_and_unverified_emails_blocked(self) -> None:
        # Plus-alias and dot-normalized self-referral
        sybil = self.orchestrator.handle(
            ReferralConversionRequest(
                request_id="req-sybil",
                referrer_account_id="acct_1",
                referee_account_id="acct_2",
                referrer_email=f"dev.user+ref1{AT_SIGN}example.org",
                referee_email=f"devuser+ref2{AT_SIGN}example.org",
            )
        )
        self.assertFalse(sybil.succeeded)
        self.assertFalse(sybil.trace.engine_dispatched)
        self.assertEqual(sybil.trace.refused_by, LAYER_ACCOUNT)
        self.assertEqual(sybil.refusal.code, "sybil_normalized_email_self_referral_detected")

        # Disposable email domain
        disposable = self.orchestrator.handle(
            ReferralConversionRequest(
                request_id="req-disposable",
                referrer_account_id="acct_1",
                referee_account_id="acct_2",
                referrer_email=f"real{AT_SIGN}example.org",
                referee_email=f"burner{AT_SIGN}mailinator.com",
            )
        )
        self.assertFalse(disposable.succeeded)
        self.assertEqual(disposable.trace.refused_by, LAYER_HANDSHAKE)
        self.assertEqual(disposable.refusal.code, "disposable_email_domain_refused")

        # Circular referral ring A -> B -> C -> A
        cycle = self.orchestrator.handle(
            ReferralConversionRequest(
                request_id="req-cycle",
                referrer_account_id="acct_C",
                referee_account_id="acct_A",
                referrer_email=f"c{AT_SIGN}example.org",
                referee_email=f"a{AT_SIGN}example.org",
                existing_referral_edges=(("acct_A", "acct_B"), ("acct_B", "acct_C")),
            )
        )
        self.assertFalse(cycle.succeeded)
        self.assertEqual(cycle.trace.refused_by, LAYER_TRACKING)
        self.assertEqual(cycle.refusal.code, "referral_graph_cycle_ring_detected")

        # Unconfirmed email-first flow
        unverified = self.orchestrator.handle(
            ReferralConversionRequest(
                request_id="req-unverified",
                referrer_account_id="acct_1",
                referee_account_id="acct_2",
                referrer_email=f"a{AT_SIGN}example.org",
                referee_email=f"b{AT_SIGN}example.org",
                email_first_verified=False,
            )
        )
        self.assertFalse(unverified.succeeded)
        self.assertEqual(unverified.trace.refused_by, LAYER_ACCOUNT)
        self.assertEqual(unverified.refusal.code, "referral_payout_requires_email_first_verification")


class CreatorMarketplaceBountyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.orchestrator = CreatorMarketplaceBountyOrchestrator()
        self.sig = make_receipt_sha256("creator-component-signature")

    def test_all_component_families_and_marketplace_engines_succeed(self) -> None:
        for family in SUPPORTED_CREATOR_FAMILIES:
            res = self.orchestrator.handle(
                CreatorComponentSubmissionRequest(
                    request_id=f"req-fam-{family}",
                    component_id=f"cmp_{family.lower().replace('/', '_')}",
                    component_family=family,
                    producer_id="creator_alice",
                    reviewer_id="reviewer_bob",
                    spdx_license="MIT",
                    signature_sha256=self.sig,
                    verified_harness_invocations=100,
                    reuse_saves_model_calls=50,
                )
            )
            self.assertTrue(res.succeeded, family)
            self.assertEqual(res.payload["weighted_attribution_units"], 350)
            self.assertEqual(res.payload["creator_bounty_credits"], 87.5)

        for engine_id in CREATOR_MARKETPLACE_ENGINE_IDS:
            orch = CreatorMarketplaceBountyOrchestrator(engine_order=(engine_id,))
            res = orch.handle(
                CreatorComponentSubmissionRequest(
                    request_id=f"req-eng-{engine_id}",
                    component_id="cmp_shader_01",
                    component_family="WGSL/GLSL",
                    producer_id="creator_alice",
                    reviewer_id="reviewer_bob",
                    spdx_license="Apache-2.0",
                    signature_sha256=self.sig,
                )
            )
            self.assertTrue(res.succeeded, engine_id)
            self.assertEqual(res.selected_engine, engine_id)

    def test_known_wrong_self_approval_and_unapproved_spdx_refused_before_engine(self) -> None:
        self_approved = self.orchestrator.handle(
            CreatorComponentSubmissionRequest(
                request_id="req-self-approve",
                component_id="cmp_self",
                component_family="Python",
                producer_id="same_person",
                reviewer_id="same_person",
                spdx_license="MIT",
                signature_sha256=self.sig,
            )
        )
        self.assertFalse(self_approved.succeeded)
        self.assertFalse(self_approved.trace.engine_dispatched)
        self.assertEqual(self_approved.trace.refused_by, LAYER_HANDSHAKE)
        self.assertEqual(self_approved.refusal.code, "creator_submission_self_approval_forbidden")

        bad_spdx = self.orchestrator.handle(
            CreatorComponentSubmissionRequest(
                request_id="req-bad-spdx",
                component_id="cmp_closed",
                component_family="Blender",
                producer_id="creator_1",
                reviewer_id="reviewer_2",
                spdx_license="Proprietary-All-Rights-Reserved",
                signature_sha256=self.sig,
            )
        )
        self.assertFalse(bad_spdx.succeeded)
        self.assertFalse(bad_spdx.trace.engine_dispatched)
        self.assertEqual(bad_spdx.trace.refused_by, LAYER_PREFLIGHT)
        self.assertEqual(bad_spdx.refusal.code, "creator_submission_spdx_or_conformance_rejected")


class BenchmarkAndKnownWrongSuiteTests(unittest.TestCase):
    def test_benchmark_and_all_seven_known_wrong_probes(self) -> None:
        bench = run_unicorn_plg_benchmark()
        self.assertEqual(len(bench["viral_badge_engines"]), 4)
        self.assertEqual(len(bench["referral_flywheel_engines"]), 3)
        self.assertEqual(len(bench["creator_marketplace_engines"]), 4)
        probes = run_known_wrong_probes()
        self.assertEqual(len(probes), 7)
        for probe in probes:
            self.assertFalse(probe["succeeded"], probe["probe_name"])
            self.assertTrue(probe["blocked_before_engine_dispatch"], probe["probe_name"])
        summary = self_test()
        self.assertEqual(summary["status"], "passed")
        self.assertEqual(summary["known_wrong_probes_blocked"], 7)
        self.assertGreater(summary["autonomous_k_factor"], 1.0)


if __name__ == "__main__":
    unittest.main()
