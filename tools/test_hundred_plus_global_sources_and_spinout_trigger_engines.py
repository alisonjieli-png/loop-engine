"""Tests for the 108-Source Global Research, Competition, Red-Teaming, Dataset &
Signal Directory + Autonomous Spin-Out Trigger & Priority Router Engine Suite.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
import unittest

_REPO_ROOT = Path(__file__).resolve().parents[1]
for _p in (_REPO_ROOT / "tools", _REPO_ROOT / "src"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from hundred_plus_global_sources_and_spinout_trigger_engines import (  # noqa: E402
    ALL_SLOTS,
    ENGINE_CACHED_CATALOG_FALLBACK,
    ENGINE_SPINOUT_FALLBACK,
    FAMILIES_COUNT,
    FIVE_HARNESS_PACK_FILES,
    FOUR_SPINOUT_DELIVERABLES,
    GLOBAL_108_SOURCES_CATALOG,
    MAX_CONTRACT_CARD_BYTES,
    SOURCES_PER_FAMILY,
    TOTAL_GLOBAL_SOURCES,
    AutonomousSpinoutTriggerOrchestrator,
    GlobalSourcesHarvestRequest,
    HundredPlusGlobalSourcesOrchestrator,
    SpinoutTriggerRequest,
    compute_multi_factor_trigger_score,
    run_hundred_plus_global_sources_benchmark,
)


class HundredPlusGlobalSourcesAndSpinoutTriggerTests(unittest.TestCase):
    """Verify the 108 global intelligence sources, 4-deliverable spin-out router, and 4 known-wrong controls."""

    def test_catalog_covers_108_sources_across_12_families_of_9(self) -> None:
        self.assertEqual(len(ALL_SLOTS), 2)
        self.assertEqual(len(GLOBAL_108_SOURCES_CATALOG), TOTAL_GLOBAL_SOURCES)
        self.assertEqual(TOTAL_GLOBAL_SOURCES, 108)

        by_family: dict[str, list[str]] = {}
        for src in GLOBAL_108_SOURCES_CATALOG:
            by_family.setdefault(src.family_id, []).append(src.source_name)

        self.assertEqual(len(by_family), FAMILIES_COUNT)
        for fam_id, names in by_family.items():
            self.assertEqual(len(names), SOURCES_PER_FAMILY, f"Family {fam_id} must contain 9 sources")

        all_names = {s.source_name for s in GLOBAL_108_SOURCES_CATALOG}
        for expected in (
            "DrivenData",
            "Zindi Africa",
            "DEF CON AI Village / GRT",
            "MITRE ATLAS Adversarial Threat Matrix",
            "DARPA AIxCC Cyber Challenge",
            "PhysioNet / MIMIC Clinical Challenges",
            "SWE-bench Verified / Multimodal",
            "GIFT-Eval Time-Series",
            "RepoDir.com (3,452 curated repos)",
            "Tessl.io Skill Estate (skills.state)",
            "OpenReview (ICLR/NeurIPS/ICML)",
            "SAM.gov Federal Contract Opportunities",
            "GrabCAD Mechanical Engineering Library",
            "Hacker News (Algolia API)",
            "Overture Maps Foundation Places/Buildings",
            "Y Combinator Startup Directory (5,000+ companies)",
        ):
            self.assertIn(expected, all_names)

    def test_slot_family_1_harvester_and_fallback_engine(self) -> None:
        harvester = HundredPlusGlobalSourcesOrchestrator()
        res = harvester.handle(
            GlobalSourcesHarvestRequest(
                schema="hundred_plus_global_intelligence_sources_request/v1",
                preferred_engine="unknown_harvester_engine",
            )
        )
        self.assertTrue(res.accepted)
        self.assertTrue(res.fallback_used)
        self.assertEqual(res.selected_engine, ENGINE_CACHED_CATALOG_FALLBACK)
        self.assertEqual(res.total_sources_harvested, 108)
        self.assertEqual(len(res.families_covered), 12)
        self.assertEqual(res.redteam_sources_count, 9)
        self.assertEqual(res.nested_frame_depth, 1)

    def test_slot_family_2_multi_factor_trigger_and_four_deliverables(self) -> None:
        router = AutonomousSpinoutTriggerOrchestrator()
        res = router.handle(
            SpinoutTriggerRequest(
                schema="source_signal_to_spinout_trigger_request/v1",
                sources=GLOBAL_108_SOURCES_CATALOG,
                preferred_engine="unknown_router_engine",
                trigger_threshold=0.70,
            )
        )
        self.assertTrue(res.accepted)
        self.assertTrue(res.fallback_used)
        self.assertEqual(res.selected_engine, ENGINE_SPINOUT_FALLBACK)
        self.assertEqual(res.evaluated_source_count, 108)
        self.assertEqual(res.triggered_spinout_count, 108)
        self.assertLessEqual(res.max_contract_card_bytes, MAX_CONTRACT_CARD_BYTES)
        self.assertEqual(len(FOUR_SPINOUT_DELIVERABLES), 4)

        sample = res.deliverable_bundles[0]
        self.assertEqual(set(sample.harness_component_pack.keys()), set(FIVE_HARNESS_PACK_FILES))
        self.assertEqual(sample.live_feed_channel_spec["feed_domain"], "agentfeeds.si")
        self.assertIn("paper.baltor.ai", sample.research_brief_and_gauntlet_spec["publication_targets"])
        self.assertIn("agentbriefs.si", sample.research_brief_and_gauntlet_spec["publication_targets"])
        self.assertEqual(sample.micro_product_venture_blueprint["blueprint_style"], "DOT-120")
        self.assertTrue(sample.defensive_preflight_detector_wrapped)

        expected_score = compute_multi_factor_trigger_score(GLOBAL_108_SOURCES_CATALOG[0])
        self.assertEqual(sample.trigger_score, expected_score)

    def test_four_known_wrong_controls_refuse_at_preflight(self) -> None:
        harvester = HundredPlusGlobalSourcesOrchestrator()
        router = AutonomousSpinoutTriggerOrchestrator()

        # Control 1: Restricted/proprietary scraping without API compliance
        bad_src = replace(GLOBAL_108_SOURCES_CATALOG[0], api_terms_compliant=False)
        c1 = harvester.handle(
            GlobalSourcesHarvestRequest(
                schema="hundred_plus_global_intelligence_sources_request/v1",
                sources=(bad_src,),
            )
        )
        self.assertFalse(c1.accepted)
        self.assertIsNotNone(c1.refusal)
        assert c1.refusal is not None
        self.assertEqual(c1.refusal.code, "restricted_scraping_terms_refused")
        self.assertEqual(c1.layer_trace[-1], ("preflight", "refused"))

        # Control 2: Red-team attack payload spin-out without defensive Layer 3/6 preflight wrapper
        c2 = router.handle(
            SpinoutTriggerRequest(
                schema="source_signal_to_spinout_trigger_request/v1",
                sources=GLOBAL_108_SOURCES_CATALOG,
                wrap_redteam_payloads_in_defensive_detector=False,
            )
        )
        self.assertFalse(c2.accepted)
        self.assertIsNotNone(c2.refusal)
        assert c2.refusal is not None
        self.assertEqual(c2.refusal.code, "unwrapped_redteam_attack_payload_refused")
        self.assertEqual(c2.layer_trace[-1], ("preflight", "refused"))

        # Control 3: Duplicate spin-out project matching an existing LSH shingle signature
        existing_sig = GLOBAL_108_SOURCES_CATALOG[0].lsh_shingle_signature
        c3 = router.handle(
            SpinoutTriggerRequest(
                schema="source_signal_to_spinout_trigger_request/v1",
                sources=(GLOBAL_108_SOURCES_CATALOG[0],),
                existing_lsh_signatures=frozenset({existing_sig}),
            )
        )
        self.assertFalse(c3.accepted)
        self.assertIsNotNone(c3.refusal)
        assert c3.refusal is not None
        self.assertEqual(c3.refusal.code, "duplicate_lsh_spinout_signature_refused")
        self.assertEqual(c3.layer_trace[-1], ("preflight", "refused"))

        # Control 4: Self-approval (producer_id == reviewer_id)
        c4 = router.handle(
            SpinoutTriggerRequest(
                schema="source_signal_to_spinout_trigger_request/v1",
                sources=(GLOBAL_108_SOURCES_CATALOG[0],),
                producer_id="same_loop_01",
                reviewer_id="same_loop_01",
            )
        )
        self.assertFalse(c4.accepted)
        self.assertIsNotNone(c4.refusal)
        assert c4.refusal is not None
        self.assertEqual(c4.refusal.code, "self_approval_refused")
        self.assertEqual(c4.layer_trace[-1], ("preflight", "refused"))

    def test_head_to_head_benchmark_108_sources(self) -> None:
        report = run_hundred_plus_global_sources_benchmark()
        self.assertEqual(report["total_sources_monitored"], 108)
        self.assertEqual(report["families_covered_count"], 12)
        self.assertEqual(report["triggered_spinout_count"], 108)
        self.assertEqual(report["four_deliverables_synthesized_total"], 432)
        self.assertLessEqual(report["max_contract_card_bytes"], MAX_CONTRACT_CARD_BYTES)
        self.assertLess(report["combined_latency_ms"], 40.0)

        strategies = {s["strategy_id"]: s for s in report["strategies"]}
        manual = strategies["ad_hoc_manual_research_without_baltor"]
        baltor = strategies["baltor_108_source_autonomous_spinout_engine"]

        self.assertEqual(manual["sources_monitored"], 6)
        self.assertEqual(manual["cross_domain_blind_spot_detection_pct"], 14.2)
        self.assertEqual(baltor["sources_monitored"], 108)
        self.assertEqual(baltor["cross_domain_blind_spot_detection_pct"], 99.1)
        self.assertEqual(baltor["spinout_deliverables_per_trigger"], 4)


if __name__ == "__main__":
    unittest.main()
