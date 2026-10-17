"""Unit and known-wrong control tests for tools/proforma_simulator.py."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for entry in (REPO_ROOT / "src", REPO_ROOT / "tools"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from loop_engine.core.engines.envelope import (  # noqa: E402
    EFFECT_NONE,
    EFFECT_UNKNOWN,
    RECONCILE_BEFORE_RETRY,
    RETRY_AFTER_FIX,
)
from loop_engine.core.engines.envelope_tracking import (  # noqa: E402
    EFFECT_STATE_CONFIRMED,
    EFFECT_STATE_NONE,
    EnvelopeJournalEntry,
)
from proforma_simulator import (  # noqa: E402
    ARCH_FLY_ORIGIN_R2_EDGE_EXPORT,
    ARCH_FLY_VOLUME_ORIGIN,
    ARCH_WORKER_FIRST_R2_D1_CACHE,
    CATALOGUE_FILE_COUNTS,
    EMAIL_STACKS,
    EMAIL_VOLUMES,
    FAILURE_DROPPED_AFTER_WRITE,
    FAILURE_PROVIDER_UNAVAILABLE,
    FAILURE_QUOTA_EXCEEDED,
    GROWTH_SCENARIOS,
    HORIZON_DAYS_1_TO_7,
    HORIZON_MONTH_1,
    HORIZON_MONTH_3,
    HORIZON_MONTH_12,
    HORIZONS,
    HOSTING_ARCHITECTURES,
    MODEL_CURRENT_LAUNCH,
    MODEL_MULTI_TIER_EXPANSION,
    PRICING_MODELS,
    SCENARIO_AGGRESSIVE,
    SCENARIO_BASE,
    SCENARIO_CONSERVATIVE,
    STACK_AWS_SES_CF_WORKERS,
    STACK_POSTMARK_FASTMAIL,
    STACK_RESEND_FREE_CF_ROUTING,
    STACK_RESEND_PRO_CF_WORKERS_FASTMAIL,
    HorizonCohortMix,
    PricingCatalog,
    ProformaSimulationError,
    build_cohort_mix,
    build_full_proforma_report,
    evaluate_cohort_projection,
    evaluate_email_stack,
    evaluate_hosting_scale,
    self_test,
    simulate_email_failover_dispatch,
    simulate_email_stack_matrix,
    simulate_hosting_matrix,
    simulate_pricing_matrix,
)


class ProformaSimulatorTest(unittest.TestCase):
    """Verify pricing trajectories, email stacks, failover safety, and catalogue hosting models."""

    def test_builtin_self_test_passes(self) -> None:
        res = self_test()
        self.assertTrue(res["passed"])

    def test_pricing_matrix_dimensions_and_monotonic_growth(self) -> None:
        rows = simulate_pricing_matrix()
        self.assertEqual(len(rows), len(PRICING_MODELS) * len(GROWTH_SCENARIOS) * len(HORIZONS))

        by_key = {(r.pricing_model, r.growth_scenario, r.horizon): r for r in rows}
        for model in PRICING_MODELS:
            for scenario in GROWTH_SCENARIOS:
                mrr_values = [by_key[(model, scenario, h)].gross_mrr_usd for h in HORIZONS]
                self.assertEqual(mrr_values, sorted(mrr_values))

            # At every horizon, Aggressive >= Base >= Conservative
            for horizon in HORIZONS:
                cons = by_key[(model, SCENARIO_CONSERVATIVE, horizon)].gross_mrr_usd
                base = by_key[(model, SCENARIO_BASE, horizon)].gross_mrr_usd
                aggr = by_key[(model, SCENARIO_AGGRESSIVE, horizon)].gross_mrr_usd
                self.assertLessEqual(cons, base)
                self.assertLessEqual(base, aggr)

    def test_multi_tier_expansion_exceeds_current_launch_and_reaches_100k_mrr(self) -> None:
        rows = simulate_pricing_matrix()
        by_key = {(r.pricing_model, r.growth_scenario, r.horizon): r for r in rows}
        for scenario in GROWTH_SCENARIOS:
            for horizon in HORIZONS:
                launch = by_key[(MODEL_CURRENT_LAUNCH, scenario, horizon)]
                expansion = by_key[(MODEL_MULTI_TIER_EXPANSION, scenario, horizon)]
                self.assertGreater(expansion.gross_mrr_usd, launch.gross_mrr_usd)
                # Under current_launch, higher tiers without active checkout contribute $0
                self.assertEqual(launch.revenue_by_stream_usd["max_monthly"], 0.0)
                self.assertEqual(launch.revenue_by_stream_usd["team_monthly"], 0.0)
                self.assertEqual(launch.revenue_by_stream_usd["agentbriefs_standard"], 0.0)
                self.assertEqual(launch.revenue_by_stream_usd["agentbriefs_enterprise"], 0.0)
                self.assertEqual(launch.revenue_by_stream_usd["playground_sponsorships"], 0.0)

        # Aggressive Multi-Tier reaches >$100K MRR by Month 6, Base Multi-Tier by Month 12
        aggr_m6 = by_key[(MODEL_MULTI_TIER_EXPANSION, SCENARIO_AGGRESSIVE, "month_6")]
        self.assertGreaterEqual(aggr_m6.gross_mrr_usd, 100_000.0)
        base_m12 = by_key[(MODEL_MULTI_TIER_EXPANSION, SCENARIO_BASE, HORIZON_MONTH_12)]
        self.assertGreaterEqual(base_m12.gross_mrr_usd, 100_000.0)

    def test_basic_free_window_enforced_in_days_1_to_7_and_month_1(self) -> None:
        for model in PRICING_MODELS:
            for scenario in GROWTH_SCENARIOS:
                for free_h in (HORIZON_DAYS_1_TO_7, HORIZON_MONTH_1):
                    cohort = build_cohort_mix(model, scenario, free_h)
                    self.assertTrue(cohort.in_basic_free_window)
                    self.assertEqual(cohort.basic_paid_opt_in_accounts, 0)
                    proj = evaluate_cohort_projection(model, scenario, cohort)
                    self.assertEqual(proj.revenue_by_stream_usd["basic_feeds"], 0.0)
                paid_h_cohort = build_cohort_mix(model, scenario, HORIZON_MONTH_3)
                self.assertFalse(paid_h_cohort.in_basic_free_window)
                self.assertGreater(paid_h_cohort.basic_paid_opt_in_accounts, 0)

    def test_known_wrong_controls_refuse_invalid_pricing_and_cohorts(self) -> None:
        # Control 1: negative or zero price in PricingCatalog
        with self.assertRaises(ProformaSimulationError) as ctx:
            PricingCatalog(pro_monthly_usd=0.0)
        self.assertEqual(ctx.exception.code, "invalid_price")

        # Control 2: founding free Pro cap > 10 in PricingCatalog
        with self.assertRaises(ProformaSimulationError) as ctx:
            PricingCatalog(founding_free_pro_cap=15)
        self.assertEqual(ctx.exception.code, "invalid_founding_cap")

        # Control 3: charging Basic during the free window through Dec 31, 2026
        with self.assertRaises(ProformaSimulationError) as ctx:
            HorizonCohortMix(
                horizon=HORIZON_DAYS_1_TO_7,
                in_basic_free_window=True,
                founding_free_pro_accounts=10,
                public_good_free_accounts=10,
                basic_free_preview_accounts=20,
                basic_paid_opt_in_accounts=1,
                pro_monthly_accounts=5,
                pro_annual_accounts=0,
                max_monthly_accounts=0,
                team_monthly_accounts=0,
                agentbriefs_standard_accounts=0,
                agentbriefs_enterprise_accounts=0,
                playground_sponsors=0,
            )
        self.assertEqual(ctx.exception.code, "basic_charged_during_free_window")

        # Control 4: negative cohort count
        with self.assertRaises(ProformaSimulationError) as ctx:
            HorizonCohortMix(
                horizon=HORIZON_MONTH_3,
                in_basic_free_window=False,
                founding_free_pro_accounts=10,
                public_good_free_accounts=10,
                basic_free_preview_accounts=0,
                basic_paid_opt_in_accounts=10,
                pro_monthly_accounts=-1,
                pro_annual_accounts=0,
                max_monthly_accounts=0,
                team_monthly_accounts=0,
                agentbriefs_standard_accounts=0,
                agentbriefs_enterprise_accounts=0,
                playground_sponsors=0,
            )
        self.assertEqual(ctx.exception.code, "negative_cohort_count")

    def test_email_stack_comparisons_and_caps(self) -> None:
        points = simulate_email_stack_matrix()
        self.assertEqual(len(points), len(EMAIL_STACKS) * len(EMAIL_VOLUMES))
        by_key = {(p.stack_id, p.monthly_emails): p for p in points}

        # Stack A (Resend Free + CF Routing) is $0 and within quota at 100 and 1,000, but exceeds cap at 10k and 100k
        self.assertTrue(by_key[(STACK_RESEND_FREE_CF_ROUTING, 100)].within_plan_quota)
        self.assertTrue(by_key[(STACK_RESEND_FREE_CF_ROUTING, 1_000)].within_plan_quota)
        self.assertFalse(by_key[(STACK_RESEND_FREE_CF_ROUTING, 10_000)].within_plan_quota)
        self.assertFalse(by_key[(STACK_RESEND_FREE_CF_ROUTING, 100_000)].within_plan_quota)

        # Stack B (Resend Pro $20 + CF Workers + Fastmail $5) is $25 up to 50k, and $70 at 100k
        self.assertEqual(by_key[(STACK_RESEND_PRO_CF_WORKERS_FASTMAIL, 10_000)].monthly_cost_usd, 25.0)
        self.assertEqual(by_key[(STACK_RESEND_PRO_CF_WORKERS_FASTMAIL, 100_000)].monthly_cost_usd, 70.0)
        self.assertTrue(by_key[(STACK_RESEND_PRO_CF_WORKERS_FASTMAIL, 10_000)].supports_programmable_inbound_worker)
        self.assertTrue(by_key[(STACK_RESEND_PRO_CF_WORKERS_FASTMAIL, 10_000)].supports_oauth_or_jmap)

        # Stack C (AWS SES + CF Workers) is $0.01 at 100, $0.10 at 1,000, $1.00 at 10,000, $10.00 at 100,000
        self.assertAlmostEqual(by_key[(STACK_AWS_SES_CF_WORKERS, 1_000)].monthly_cost_usd, 0.10)
        self.assertAlmostEqual(by_key[(STACK_AWS_SES_CF_WORKERS, 100_000)].monthly_cost_usd, 10.00)

        # Stack D (Postmark + Fastmail) is $20 at 10k, and $20 + 90*1.80 = $182 at 100k
        self.assertEqual(by_key[(STACK_POSTMARK_FASTMAIL, 10_000)].monthly_cost_usd, 20.0)
        self.assertEqual(by_key[(STACK_POSTMARK_FASTMAIL, 100_000)].monthly_cost_usd, 182.0)

    def test_email_envelope_failover_and_reconciliation_guards(self) -> None:
        # 1. Pre-effect quota failure on primary -> automatic failover to secondary succeeds
        ok_failover = simulate_email_failover_dispatch(
            request_id="test-email-001",
            recipient="user@baltor.ai",
            provider_chain=("resend_free_api", "aws_ses_api"),
            injected_failures={"resend_free_api": FAILURE_QUOTA_EXCEEDED},
        )
        self.assertTrue(ok_failover["delivered"])
        self.assertEqual(ok_failover["selected_provider"], "aws_ses_api")
        self.assertEqual(len(ok_failover["attempts"]), 2)
        self.assertEqual(ok_failover["attempts"][0]["outcome"], "failed_over")
        self.assertEqual(ok_failover["attempts"][1]["outcome"], "delivered")

        # 2. Known-wrong control: invalid recipient refused in preflight before any provider call
        bad_recipient = simulate_email_failover_dispatch(
            request_id="test-email-002",
            recipient="not-an-email-address",
            provider_chain=("resend_pro_api", "aws_ses_api"),
        )
        self.assertFalse(bad_recipient["delivered"])
        self.assertEqual(bad_recipient["trace"]["refused_by"], "preflight")
        self.assertEqual(bad_recipient["refusal"]["code"], "invalid_recipient")
        self.assertEqual(bad_recipient["refusal"]["retry"], RETRY_AFTER_FIX)
        self.assertEqual(bad_recipient["attempts"], [])

        # 3. Known-wrong control: connection drop after payload write (EFFECT_UNKNOWN) halts failover
        dropped = simulate_email_failover_dispatch(
            request_id="test-email-003",
            recipient="user@baltor.ai",
            provider_chain=("resend_pro_api", "aws_ses_api", "fastmail_jmap_submission"),
            injected_failures={"resend_pro_api": FAILURE_DROPPED_AFTER_WRITE},
        )
        self.assertFalse(dropped["delivered"])
        self.assertEqual(len(dropped["attempts"]), 1)
        self.assertEqual(dropped["refusal"]["effect_commitment"], EFFECT_UNKNOWN)
        self.assertEqual(dropped["refusal"]["retry"], RECONCILE_BEFORE_RETRY)

        # 4. Repeating the same request before reconciliation is refused by the tracking layer
        journal_entries = tuple(EnvelopeJournalEntry.from_dict(item) for item in dropped["journal"])
        blocked_retry = simulate_email_failover_dispatch(
            request_id="test-email-003",
            recipient="user@baltor.ai",
            provider_chain=("resend_pro_api", "aws_ses_api"),
            existing_journal=journal_entries,
        )
        self.assertFalse(blocked_retry["delivered"])
        self.assertEqual(blocked_retry["trace"]["refused_by"], "tracking")
        self.assertEqual(blocked_retry["journal_decision"]["decision"], "reconcile_first")

        # 5. Reconciling as EFFECT_STATE_NONE allows clean dispatch on the next provider
        reconciled_retry = simulate_email_failover_dispatch(
            request_id="test-email-003",
            recipient="user@baltor.ai",
            provider_chain=("aws_ses_api",),
            existing_journal=journal_entries,
            reconcile_to_state=EFFECT_STATE_NONE,
        )
        self.assertTrue(reconciled_retry["delivered"])
        self.assertEqual(reconciled_retry["selected_provider"], "aws_ses_api")

        # 6. All providers unavailable -> refuses after exhausting chain
        all_down = simulate_email_failover_dispatch(
            request_id="test-email-004",
            recipient="user@baltor.ai",
            provider_chain=("resend_pro_api", "aws_ses_api"),
            injected_failures={
                "resend_pro_api": FAILURE_PROVIDER_UNAVAILABLE,
                "aws_ses_api": FAILURE_PROVIDER_UNAVAILABLE,
            },
        )
        self.assertFalse(all_down["delivered"])
        self.assertEqual(all_down["refusal"]["effect_commitment"], EFFECT_NONE)

    def test_hosting_scale_comparisons(self) -> None:
        points = simulate_hosting_matrix()
        self.assertEqual(len(points), len(HOSTING_ARCHITECTURES) * len(CATALOGUE_FILE_COUNTS))
        by_key = {(p.architecture_id, p.distinct_files): p for p in points}

        # At 1.90M files, all three architectures fit under $50/mo, with R2/Worker cheaper than pure Fly NVMe
        self.assertTrue(by_key[(ARCH_FLY_VOLUME_ORIGIN, 1_900_000)].within_50_usd_allowance)
        self.assertTrue(by_key[(ARCH_FLY_ORIGIN_R2_EDGE_EXPORT, 1_900_000)].within_50_usd_allowance)
        self.assertTrue(by_key[(ARCH_WORKER_FIRST_R2_D1_CACHE, 1_900_000)].within_50_usd_allowance)

        # At 5M and 10M files, direct Fly NVMe origin exceeds the $50/mo infrastructure allowance,
        # while Worker-first + R2 content-addressed storage stays under $50/mo even at 10M files!
        self.assertFalse(by_key[(ARCH_FLY_VOLUME_ORIGIN, 5_000_000)].within_50_usd_allowance)
        self.assertFalse(by_key[(ARCH_FLY_VOLUME_ORIGIN, 10_000_000)].within_50_usd_allowance)
        self.assertTrue(by_key[(ARCH_FLY_ORIGIN_R2_EDGE_EXPORT, 5_000_000)].within_50_usd_allowance)
        self.assertTrue(by_key[(ARCH_WORKER_FIRST_R2_D1_CACHE, 5_000_000)].within_50_usd_allowance)
        self.assertTrue(by_key[(ARCH_WORKER_FIRST_R2_D1_CACHE, 10_000_000)].within_50_usd_allowance)

        # Latency ordering: Worker-first < Fly + R2 Edge < Fly Volume Origin
        for count in CATALOGUE_FILE_COUNTS:
            w_lat = by_key[(ARCH_WORKER_FIRST_R2_D1_CACHE, count)].p95_read_latency_ms
            r2_lat = by_key[(ARCH_FLY_ORIGIN_R2_EDGE_EXPORT, count)].p95_read_latency_ms
            fly_lat = by_key[(ARCH_FLY_VOLUME_ORIGIN, count)].p95_read_latency_ms
            self.assertLess(w_lat, r2_lat)
            self.assertLess(r2_lat, fly_lat)

        # Known-wrong controls on hosting evaluator
        with self.assertRaises(ProformaSimulationError):
            evaluate_hosting_scale("unknown_arch", 1_900_000)
        with self.assertRaises(ProformaSimulationError):
            evaluate_hosting_scale(ARCH_FLY_ORIGIN_R2_EDGE_EXPORT, 0)
        with self.assertRaises(ProformaSimulationError):
            evaluate_email_stack("unknown_stack", 1_000)
        with self.assertRaises(ProformaSimulationError):
            evaluate_email_stack(STACK_RESEND_FREE_CF_ROUTING, 0)

    def test_full_report_serializes_deterministically(self) -> None:
        r1 = build_full_proforma_report()
        r2 = build_full_proforma_report()
        self.assertEqual(r1, r2)


if __name__ == "__main__":
    unittest.main()
