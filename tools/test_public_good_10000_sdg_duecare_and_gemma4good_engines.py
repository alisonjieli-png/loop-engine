"""Tests and known-wrong controls for the 10,000+ Public Good Harness Component Files,
DueCare & Kaggle Gemma-4-Good Micro/Meso/Macro Synthesizer, All 17 UN SDGs +
12 Public-Benefit Initiatives & 3,480+ Public Good Feeds/Datasets/Sources Engine Suite.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
if str(HERE.parent / "src") not in sys.path:
    sys.path.insert(0, str(HERE.parent / "src"))

import public_good_10000_sdg_duecare_and_gemma4good_engines as pg10k  # noqa: E402
from loop_engine.core.engines.envelope import COVERAGE_LAYERS, LAYER_REFUSED  # noqa: E402


class PublicGood10000SdgDuecareAndGemma4GoodTests(unittest.TestCase):
    """Verify the 14,500-spec (72,500-file) Public Good factory, 17.6M combinatorial space,
    3,480 feeds/datasets/sources registry, 30-task benchmark, and 4 known-wrong controls.
    """

    def test_29_domains_169_sdg_targets_14500_specs_72500_files_and_17_6m_bijective_space(self) -> None:
        space = pg10k.enumerate_combinatorial_public_good_space()
        self.assertEqual(space["domains_count"], 29)
        self.assertEqual(space["un_sdg_domains_count"], 17)
        self.assertEqual(space["specialized_initiatives_count"], 12)
        self.assertEqual(space["official_sdg_targets_count"], 169)
        self.assertEqual(len(pg10k.OFFICIAL_169_SDG_TARGETS), 169)
        self.assertEqual(space["granularity_tiers_count"], 3)
        self.assertEqual(space["regional_profiles_count"], 120)
        self.assertEqual(space["data_modalities_count"], 10)
        self.assertEqual(space["total_addressable_blueprints"], 17643600)
        self.assertEqual(space["immediate_catalogued_specs"], 14500)
        self.assertEqual(space["immediate_harness_component_files"], 72500)
        self.assertEqual(space["total_public_good_feeds_and_sources"], 3480)

        # Verify bijective index mapping at boundaries and interior points
        first_idx = pg10k.compute_public_good_blueprint_index(0, 0, 0, 0, 0)
        last_idx = pg10k.compute_public_good_blueprint_index(28, 168, 2, 119, 9)
        self.assertEqual(first_idx, 0)
        self.assertEqual(last_idx, 17643599)

        for sample_idx in (0, 1, 424242, 8821800, 17643599):
            coords = pg10k.invert_public_good_blueprint_index(sample_idx)
            recomputed = pg10k.compute_public_good_blueprint_index(
                int(coords["domain_idx"]),
                int(coords["target_idx"]),
                int(coords["tier_idx"]),
                int(coords["region_idx"]),
                int(coords["modality_idx"]),
            )
            self.assertEqual(recomputed, sample_idx)

        # Verify fast enumeration of 14,500 specs / 72,500 files completes in < 0.5s
        catalog = pg10k.enumerate_14500_public_good_component_specs()
        self.assertEqual(catalog["total_domains"], 29)
        self.assertEqual(catalog["total_component_specs"], 14500)
        self.assertEqual(catalog["total_distinct_harness_files"], 72500)
        self.assertTrue(catalog["completed_under_half_second"])

    def test_slot1_micro_meso_macro_factory_across_swappable_engines_and_verifier_execution(self) -> None:
        factory = pg10k.PublicGoodMicroMesoMacroFactorySlot()
        for idx, engine_id in enumerate(pg10k.FACTORY_ENGINE_ORDER):
            tier = pg10k.GRANULARITY_TIERS[idx % len(pg10k.GRANULARITY_TIERS)]
            dom = pg10k.ALL_PUBLIC_BENEFIT_DOMAINS[idx]
            res = factory.synthesize_component_pack(
                dom.domain_id,
                granularity_tier=tier,
                spec_offset=idx,
                request_id=f"test_factory_eng_{idx}",
                preferred_engine=engine_id,
            )
            self.assertTrue(res.accepted)
            self.assertEqual(res.selected_engine, engine_id)
            for layer in COVERAGE_LAYERS:
                self.assertEqual(res.layer_verdicts[layer], "full")

            self.assertTrue(res.output["contract_card_within_2048_bytes"])
            self.assertLessEqual(int(res.output["contract_card_bytes"]), 2048)
            self.assertTrue(res.output["micro_card_within_1024_bytes"])
            self.assertLessEqual(int(res.output["micro_card_bytes"]), 1024)

            files = res.output["files"]
            verifier_name = str(res.output["verifier_filename"])
            self.assertIn(verifier_name, files)
            self.assertIn("SKILL.md", files)
            self.assertIn("AGENTS.md", files)
            self.assertIn("RULES.md", files)
            self.assertIn("MEMORY.md", files)
            self.assertIn("baltor_contract_card.json", files)
            self.assertIn("baltor_micro_card.json", files)

            card = json.loads(files["baltor_contract_card.json"])
            self.assertEqual(card["domain_id"], dom.domain_id)
            self.assertEqual(card["local_model_id"], "gemma4:e4b")

            # Execute generated verifier in an isolated namespace
            ns: dict[str, object] = {}
            exec(files[verifier_name], ns)  # noqa: S102
            verify_fn = ns["verify_public_good_record"]
            self.assertTrue(
                callable(verify_fn)
                and verify_fn(
                    {
                        "domain_id": dom.domain_id,
                        "public_benefit_reason": dom.default_public_benefit_reason,
                        "duecare_split_leakage_detected": False,
                        "duecare_redistribution_rights_ok": True,
                        "claims_un_affiliation": False,
                    }
                )
            )
            self.assertFalse(
                callable(verify_fn)
                and verify_fn(
                    {
                        "domain_id": dom.domain_id,
                        "public_benefit_reason": dom.default_public_benefit_reason,
                        "duecare_split_leakage_detected": True,
                        "duecare_redistribution_rights_ok": True,
                        "claims_un_affiliation": False,
                    }
                )
            )

    def test_slot2_3480_public_good_feeds_datasets_and_sources_across_all_29_domains(self) -> None:
        feeds_slot = pg10k.PublicGoodFeedsDatasetsAndSourcesSlot()
        for idx, engine_id in enumerate(pg10k.FEEDS_ENGINE_ORDER):
            res = feeds_slot.materialize_feeds_catalog(
                "ALL",
                request_id=f"test_feeds_eng_{idx}",
                preferred_engine=engine_id,
            )
            self.assertTrue(res.accepted)
            self.assertEqual(res.selected_engine, engine_id)
            self.assertEqual(res.output["domains_covered"], 29)
            self.assertEqual(res.output["feeds_per_domain"], 120)
            self.assertEqual(res.output["total_feeds_generated"], 3480)
            self.assertTrue(res.output["all_feeds_pass_duecare_rights_filter"])
            self.assertEqual(len(res.output["duecare_datasets_linked"]), 6)
            self.assertEqual(len(res.output["gemma4good_tracks_linked"]), 4)
            for layer in COVERAGE_LAYERS:
                self.assertEqual(res.layer_verdicts[layer], "full")

    def test_benchmark_baltor_100_percent_vs_unassisted_llm_46_7_percent(self) -> None:
        bench = pg10k.run_public_good_10k_benchmark()
        self.assertEqual(bench["total_benchmark_tasks"], 30)

        scale = bench["catalog_scale_verified"]
        self.assertEqual(scale["immediate_component_specs"], 14500)
        self.assertEqual(scale["immediate_distinct_harness_files"], 72500)
        self.assertEqual(scale["public_good_feeds_and_sources"], 3480)
        self.assertEqual(scale["combinatorial_addressable_blueprints"], 17643600)

        without_b = bench["without_baltor_baseline"]
        self.assertEqual(without_b["engine_id"], pg10k.ENGINE_UNASSISTED_LLM_BASELINE)
        self.assertEqual(without_b["tasks_passed"], 14)
        self.assertAlmostEqual(float(without_b["pass_rate"]), 0.4667)
        self.assertEqual(without_b["pass_rate_pct"], "46.7%")
        self.assertGreater(int(without_b["duecare_split_leakage_missed"]), 0)
        self.assertGreater(int(without_b["redistribution_rights_violations"]), 0)

        with_b = bench["with_baltor_public_good_suite"]
        self.assertEqual(with_b["engine_id"], pg10k.ENGINE_BALTOR_10K_PUBLIC_GOOD_SUITE)
        self.assertEqual(with_b["tasks_passed"], 30)
        self.assertAlmostEqual(float(with_b["pass_rate"]), 1.0)
        self.assertEqual(with_b["pass_rate_pct"], "100.0%")
        self.assertEqual(with_b["duecare_split_leakage_missed"], 0)
        self.assertEqual(with_b["redistribution_rights_violations"], 0)
        self.assertEqual(with_b["hallucinated_sdg_indicator_codes"], 0)
        self.assertTrue(with_b["all_cards_within_2048_bytes"])

    def test_four_known_wrong_controls_refuse_before_engine_dispatch(self) -> None:
        kw = pg10k.run_known_wrong_controls()
        self.assertEqual(kw["total_controls"], 4)
        self.assertEqual(kw["passed_controls"], 4)
        for ctrl in kw["controls"]:
            self.assertTrue(ctrl["passed"], msg=f"Failed control: {ctrl}")
            self.assertTrue(ctrl["refused_before_engine"])

        factory = pg10k.PublicGoodMicroMesoMacroFactorySlot()
        res_un = factory.synthesize_component_pack(
            "SDG-01",
            request_id="direct_kw_un",
            extra_payload={"claim_un_endorsement_or_affiliation": True},
        )
        self.assertFalse(res_un.accepted)
        self.assertIsNotNone(res_un.refusal)
        self.assertEqual(res_un.refusal.code, "un_affiliation_or_endorsement_claim_refused")
        self.assertEqual(res_un.layer_verdicts["preflight"], LAYER_REFUSED)


if __name__ == "__main__":
    unittest.main()
