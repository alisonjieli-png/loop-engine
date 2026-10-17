"""Tests for the Master Launch Readiness, 9-Domain/Subdomain Surface Matrix,
12-Item MVP & Bug Resolution Checklist Verifier, 4-Tier Automated Backup/DR
Drill & 7-Channel Social/Marketing Go-Live Sequencer Engine Suite.
"""
from __future__ import annotations

import inspect
from pathlib import Path
import sys
import unittest

REPOSITORY = Path(__file__).resolve().parents[1]
for p in (REPOSITORY / "src", REPOSITORY / "tools"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from launch_readiness_disaster_recovery_and_surface_status_engines import (  # noqa: E402
    ALL_SLOTS,
    DISASTER_RECOVERY_ENGINE_ORDER,
    DISASTER_RECOVERY_LAUNCH_ADAPTER,
    ENGINE_AD_HOC_UNMONITORED_LAUNCH_BASELINE,
    ENGINE_BALTOR_MASTER_LAUNCH_AND_DR_CONTROL_TOWER,
    ENGINE_TWELVE_ITEM_MVP_BUG_CHECKLIST_VERIFIER,
    FOUR_TIER_DISASTER_RECOVERY_SPECS,
    FROZEN_BACKUP_BRANCH,
    FROZEN_BACKUP_REVISION,
    MAX_TARGET_DR_RTO_SECONDS,
    NINE_SURFACE_READINESS_MATRIX,
    OBSERVED_DR_RTO_SECONDS,
    PINNED_ROLLBACK_IMAGE_DIGEST,
    SEVEN_SOCIAL_MARKETING_CHANNELS,
    SLOT_DISASTER_RECOVERY_AND_LAUNCH_SEQUENCER,
    SLOT_SURFACE_STATUS_MVP_AND_BUG_CHECKLIST,
    SURFACE_CHECKLIST_ENGINE_ORDER,
    SURFACE_STATUS_CHECKLIST_ADAPTER,
    SURFACES_BY_DOMAIN,
    TWELVE_ITEM_MVP_AND_BUG_CHECKLIST,
    ThinComponentAdapter,
    evaluate_launch_readiness_and_disaster_recovery_suite,
    invoke_disaster_recovery_launch_sequencer_slot,
    invoke_surface_status_mvp_checklist_slot,
    run_known_wrong_refusal_controls,
)


class LaunchReadinessDisasterRecoveryAndSurfaceStatusTests(unittest.TestCase):
    """Verify 9 surfaces, 12 MVP/bug checklist items, 4 DR tiers, 7 marketing channels, and 4 known-wrong controls."""

    def test_nine_surfaces_and_twelve_mvp_bug_checklist_items(self) -> None:
        self.assertEqual(len(ALL_SLOTS), 2)
        self.assertEqual(len(NINE_SURFACE_READINESS_MATRIX), 9)
        expected_domains = (
            "baltor.ai",
            "proxy.baltor.ai",
            "browser.baltor.ai",
            "signals+<source>@baltor.ai",
            "agentfeeds.si",
            "agentfoundry.si",
            "agentbriefs.si",
            "paper.baltor.ai",
            "tayloramarel.baltor.ai",
        )
        for dom in expected_domains:
            self.assertIn(dom, SURFACES_BY_DOMAIN)
            self.assertEqual(SURFACES_BY_DOMAIN[dom].personal_vs_product_isolation_pct, 100.0)

        self.assertEqual(len(TWELVE_ITEM_MVP_AND_BUG_CHECKLIST), 12)
        for item in TWELVE_ITEM_MVP_AND_BUG_CHECKLIST:
            self.assertTrue(item.resolved_in_code)

        res = invoke_surface_status_mvp_checklist_slot({"domain_or_endpoint": "tayloramarel.baltor.ai"})
        self.assertTrue(res.accepted)
        self.assertEqual(res.slot_id, SLOT_SURFACE_STATUS_MVP_AND_BUG_CHECKLIST)
        self.assertEqual(res.selected_engine, SURFACE_CHECKLIST_ENGINE_ORDER[0])
        self.assertEqual(res.output["surface_count"], 9)
        self.assertEqual(res.output["mvp_and_bug_checklist_resolved"], 12)
        self.assertEqual(res.output["checklist_resolution_pct"], 100.0)
        self.assertTrue(res.output["zero_code_blockers_remaining"])

    def test_four_tier_disaster_recovery_and_seven_social_marketing_channels(self) -> None:
        source_lines = inspect.getsourcelines(ThinComponentAdapter)[0]
        self.assertLess(len(source_lines), 30)
        self.assertEqual(len(FOUR_TIER_DISASTER_RECOVERY_SPECS), 4)
        self.assertEqual(len(SEVEN_SOCIAL_MARKETING_CHANNELS), 7)
        for ch in SEVEN_SOCIAL_MARKETING_CHANNELS:
            self.assertTrue(ch.ready_for_launch_sequence)

        res = invoke_disaster_recovery_launch_sequencer_slot({"tier_id": "DR_TIER_1_git_dual_branch_and_bundles"})
        self.assertTrue(res.accepted)
        self.assertEqual(res.slot_id, SLOT_DISASTER_RECOVERY_AND_LAUNCH_SEQUENCER)
        self.assertEqual(res.selected_engine, DISASTER_RECOVERY_ENGINE_ORDER[0])
        self.assertEqual(res.output["allowed_branches"], ("main", FROZEN_BACKUP_BRANCH))
        self.assertEqual(res.output["frozen_backup_revision"], FROZEN_BACKUP_REVISION)
        self.assertEqual(res.output["pinned_rollback_image_digest"], PINNED_ROLLBACK_IMAGE_DIGEST)
        self.assertLess(res.output["simulated_dr_rto_seconds"], MAX_TARGET_DR_RTO_SECONDS)
        self.assertEqual(res.output["data_loss_rpo_commits"], 0)
        self.assertEqual(res.output["social_marketing_channels_ready"], 7)

        swapped = SURFACE_STATUS_CHECKLIST_ADAPTER.swap_engine(ENGINE_TWELVE_ITEM_MVP_BUG_CHECKLIST_VERIFIER)
        self.assertEqual(swapped.engine_order[0], ENGINE_TWELVE_ITEM_MVP_BUG_CHECKLIST_VERIFIER)
        self.assertEqual(DISASTER_RECOVERY_LAUNCH_ADAPTER.describe()["loc"], 24)

    def test_four_known_wrong_refusal_controls_blocked_at_preflight(self) -> None:
        controls = run_known_wrong_refusal_controls()
        self.assertEqual(controls["probe_count"], 4)
        self.assertTrue(controls["all_blocked_at_preflight"])
        probes = controls["probes"]
        self.assertEqual(
            probes["frozen_backup_branch_mutation_blocked"]["refusal_code"],
            "frozen_backup_branch_mutation_refused",
        )
        self.assertEqual(
            probes["missing_rollback_image_digest_blocked"]["refusal_code"],
            "missing_rollback_image_digest_refused",
        )
        self.assertEqual(
            probes["corrupted_backup_bundle_restore_blocked"]["refusal_code"],
            "corrupted_backup_bundle_restore_refused",
        )
        self.assertEqual(
            probes["personal_vs_product_host_isolation_failure_blocked"]["refusal_code"],
            "personal_vs_product_host_isolation_failed_refused",
        )

    def test_24_scenario_benchmark_and_envelope_idempotency(self) -> None:
        report = evaluate_launch_readiness_and_disaster_recovery_suite()
        self.assertEqual(report["scenario_count"], 24)
        self.assertEqual(report["surface_count"], 9)
        self.assertEqual(report["mvp_bug_checklist_count"], 12)
        self.assertEqual(report["mvp_bug_checklist_resolved_count"], 12)
        self.assertEqual(report["dr_tier_count"], 4)
        self.assertEqual(report["social_channel_count"], 7)
        self.assertTrue(report["all_scenarios_accepted"])
        self.assertTrue(report["hot_swap_verified"])

        suite_bench = report["benchmarks"][ENGINE_BALTOR_MASTER_LAUNCH_AND_DR_CONTROL_TOWER]
        base_bench = report["benchmarks"][ENGINE_AD_HOC_UNMONITORED_LAUNCH_BASELINE]
        self.assertEqual(suite_bench["launch_gate_and_checklist_coverage_pct"], 100.0)
        self.assertEqual(base_bench["launch_gate_and_checklist_coverage_pct"], 54.2)
        self.assertEqual(suite_bench["mean_disaster_recovery_rto_seconds"], OBSERVED_DR_RTO_SECONDS)
        self.assertEqual(suite_bench["mean_disaster_recovery_rto_display"], "28.5 sec")
        self.assertEqual(base_bench["mean_disaster_recovery_rto_display"], "45.0 min")
        self.assertEqual(suite_bench["data_loss_rpo_commits"], 0)
        self.assertEqual(suite_bench["branch_policy_compliance_pct"], 100.0)
        self.assertEqual(suite_bench["personal_vs_product_isolation_pct"], 100.0)

        first = invoke_surface_status_mvp_checklist_slot(
            {"domain_or_endpoint": "baltor.ai"},
            request_id="idem_launch_dr_01",
        )
        second = invoke_surface_status_mvp_checklist_slot(
            {"domain_or_endpoint": "baltor.ai"},
            request_id="idem_launch_dr_01",
        )
        self.assertIs(first, second)


if __name__ == "__main__":
    unittest.main()
