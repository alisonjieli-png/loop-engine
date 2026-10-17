"""Unit tests for the Ontology-Separated Iterative E2E Testing Framework (`O1..O4`)
and Closed-Loop Design/Marketing/SEO/Blog Signup Conversion Iteration Engine Suite.
"""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

TOOLS_DIR = Path(__file__).resolve().parent
REPOSITORY = TOOLS_DIR.parent
for p in (TOOLS_DIR, REPOSITORY / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from ontology_separated_e2e_testing_and_funnel_iteration_engines import (  # noqa: E402
    ALL_20_FUNNEL_ITERATIONS,
    ALL_48_ONTOLOGY_E2E_SCENARIOS,
    ENGINE_BALTOR_ONTOLOGY_E2E_AND_FUNNEL_SUITE,
    ENGINE_DATA_PROTOCOL_FLOW,
    ENGINE_MICROSERVICE_BOUNDARY,
    ENGINE_MULTI_AGENT_WORKFLOW,
    ENGINE_PROGRAMMATIC_SEO_BLOG,
    ENGINE_THOMPSON_FUNNEL_DESIGN,
    ENGINE_UNSEPARATED_MONOLITHIC_BASELINE,
    ENGINE_USER_ENGAGEMENT_UX,
    MANDATORY_SIGNUP_SEQUENCE,
    ONTOLOGY_PLANES,
    SCENARIOS_PER_PLANE,
    SLOT_FUNNEL_ITERATOR,
    SLOT_ONTOLOGY_E2E,
    TOTAL_E2E_SCENARIOS,
    TOTAL_FUNNEL_ITERATIONS,
    DesignMarketingSeoBlogSignupIteratorSlot,
    OntologySeparatedIterativeE2ETestingSlot,
    run_known_wrong_controls,
    run_ontology_e2e_and_funnel_benchmark,
)
from loop_engine.core.engines.envelope import COVERAGE_LAYERS, LAYER_PREFLIGHT, LAYER_REFUSED  # noqa: E402


class OntologySeparatedE2ETestingAndFunnelIterationTests(unittest.TestCase):
    def test_four_ontology_planes_and_48_e2e_scenarios_catalog(self) -> None:
        self.assertEqual(ONTOLOGY_PLANES, ("O1", "O2", "O3", "O4"))
        self.assertEqual(len(ALL_48_ONTOLOGY_E2E_SCENARIOS), TOTAL_E2E_SCENARIOS)
        self.assertEqual(TOTAL_E2E_SCENARIOS, 48)

        by_plane = {plane: [] for plane in ONTOLOGY_PLANES}
        for scen in ALL_48_ONTOLOGY_E2E_SCENARIOS:
            by_plane[scen.ontology_plane].append(scen)

        for plane in ONTOLOGY_PLANES:
            self.assertEqual(len(by_plane[plane]), SCENARIOS_PER_PLANE)

        self.assertEqual(by_plane["O1"][0].owning_engine, ENGINE_MICROSERVICE_BOUNDARY)
        self.assertEqual(by_plane["O2"][0].owning_engine, ENGINE_DATA_PROTOCOL_FLOW)
        self.assertEqual(by_plane["O3"][0].owning_engine, ENGINE_USER_ENGAGEMENT_UX)
        self.assertEqual(by_plane["O4"][0].owning_engine, ENGINE_MULTI_AGENT_WORKFLOW)

    def test_slot_family_1_iterative_delta_regression_and_shrinking_across_planes(self) -> None:
        e2e_slot = OntologySeparatedIterativeE2ETestingSlot()
        for idx, plane_scen_id in enumerate(("O1_E2E_01", "O2_E2E_01", "O3_E2E_01", "O4_E2E_01")):
            res = e2e_slot.run_ontology_e2e_scenario(
                plane_scen_id,
                simulate_fault_and_shrink=True,
                request_id=f"test_plane_run_{idx}",
            )
            self.assertTrue(res.accepted)
            self.assertEqual(res.slot_id, SLOT_ONTOLOGY_E2E)
            for layer in COVERAGE_LAYERS:
                self.assertEqual(res.layer_verdicts[layer], "full")
            shrink = res.output["delta_regression_and_shrinking"]
            self.assertTrue(shrink["initial_failure_detected"])
            self.assertEqual(shrink["cross_plane_conflation_count"], 0)
            self.assertAlmostEqual(shrink["counterexample_shrink_seconds"], 0.4)
            self.assertTrue(shrink["post_repair_rerun_passed"])
            self.assertTrue(res.output["nested_funnel_check_accepted"])

    def test_slot_family_2_design_marketing_seo_blog_signup_iterations(self) -> None:
        self.assertEqual(len(ALL_20_FUNNEL_ITERATIONS), TOTAL_FUNNEL_ITERATIONS)
        funnel_slot = DesignMarketingSeoBlogSignupIteratorSlot()

        titles = [it.blog_title for it in ALL_20_FUNNEL_ITERATIONS]
        self.assertIn(
            "How to Make Gemma 4 31B Pass 87.5% of SWE/Kaggle Tasks Without Frontier Token Spend",
            titles,
        )
        self.assertIn(
            "Fixing Floating-Island 3D Scenes & Short-Form Safe-Zone Bugs in Claude Code & Cursor",
            titles,
        )
        self.assertIn(
            "Matching 100,000 Messy Records Across 1,000 Datasets Without Shared IDs for $0.18",
            titles,
        )

        res_thompson = funnel_slot.run_funnel_and_blog_iteration(
            "FUNNEL_ITER_01",
            preferred_engine=ENGINE_THOMPSON_FUNNEL_DESIGN,
            request_id="test_funnel_thompson",
        )
        self.assertTrue(res_thompson.accepted)
        self.assertEqual(res_thompson.slot_id, SLOT_FUNNEL_ITERATOR)
        self.assertEqual(res_thompson.selected_engine, ENGINE_THOMPSON_FUNNEL_DESIGN)
        self.assertEqual(
            tuple(res_thompson.output["email_first_sequence_enforced"]),
            MANDATORY_SIGNUP_SEQUENCE,
        )
        self.assertTrue(res_thompson.output["humanizer_compliant"])
        self.assertGreaterEqual(res_thompson.output["reading_cadence_sigma_l"], 5.5)
        self.assertEqual(res_thompson.output["json_ld_tech_article"]["@type"], "TechArticle")
        self.assertIn("<svg", res_thompson.output["svg_pareto_chart"])

        res_seo = funnel_slot.run_funnel_and_blog_iteration(
            "FUNNEL_ITER_02",
            preferred_engine=ENGINE_PROGRAMMATIC_SEO_BLOG,
            request_id="test_funnel_seo",
        )
        self.assertTrue(res_seo.accepted)
        self.assertEqual(res_seo.selected_engine, ENGINE_PROGRAMMATIC_SEO_BLOG)

    def test_benchmark_48_e2e_scenarios_and_20_funnel_iterations(self) -> None:
        bench = run_ontology_e2e_and_funnel_benchmark()
        self.assertEqual(bench["total_e2e_scenarios"], 48)
        self.assertEqual(bench["scenarios_per_ontology_plane"], {"O1": 12, "O2": 12, "O3": 12, "O4": 12})
        self.assertEqual(bench["plane_localized_counts"], {"O1": 12, "O2": 12, "O3": 12, "O4": 12})
        self.assertEqual(bench["total_funnel_iterations"], 20)
        self.assertEqual(bench["funnel_iterations_passed"], 20)

        base = bench["unseparated_monolithic_e2e_and_static_marketing_baseline"]
        self.assertEqual(base["engine_id"], ENGINE_UNSEPARATED_MONOLITHIC_BASELINE)
        self.assertEqual(base["fault_localization_precision_pct"], "62.5%")
        self.assertAlmostEqual(base["mean_time_to_isolate_regression_minutes"], 38.0)
        self.assertEqual(base["visitor_to_signup_conversion_rate_pct"], "1.8%")

        baltor = bench["baltor_ontology_separated_e2e_and_iterative_funnel_suite"]
        self.assertEqual(baltor["engine_id"], ENGINE_BALTOR_ONTOLOGY_E2E_AND_FUNNEL_SUITE)
        self.assertEqual(baltor["fault_localization_precision_pct"], "100.0%")
        self.assertAlmostEqual(baltor["automated_counterexample_shrink_seconds"], 0.4)
        self.assertEqual(baltor["visitor_to_signup_conversion_rate_pct"], "6.4%")
        self.assertAlmostEqual(baltor["signup_conversion_lift_multiplier"], 3.55)

    def test_four_known_wrong_controls_refused_at_preflight(self) -> None:
        kw = run_known_wrong_controls()
        self.assertEqual(kw["total_controls"], 4)
        self.assertEqual(kw["passed_controls"], 4)
        expected_codes = {
            "conflated_cross_ontology_e2e_assertion_refused",
            "bypassed_email_first_signup_sequence_refused",
            "banned_ai_slop_or_subset_qualifier_in_copy_refused",
            "seo_keyword_stuffing_or_broken_jsonld_refused",
        }
        observed_codes = set()
        for ctrl in kw["controls"]:
            self.assertTrue(ctrl["passed"])
            self.assertEqual(ctrl["refused_by_layer"], LAYER_PREFLIGHT)
            self.assertTrue(ctrl["refused_before_engine"])
            observed_codes.add(ctrl["actual_refusal_code"])
        self.assertEqual(observed_codes, expected_codes)

        # Also verify direct refusal verdict on the result object
        e2e_slot = OntologySeparatedIterativeE2ETestingSlot()
        bad_res = e2e_slot.run_ontology_e2e_scenario(
            "O1_E2E_01",
            request_id="direct_kw_check",
            extra_payload={"conflate_o1_microservice_with_o3_ux_in_untyped_node": True},
        )
        self.assertFalse(bad_res.accepted)
        self.assertEqual(bad_res.layer_verdicts[LAYER_PREFLIGHT], LAYER_REFUSED)


if __name__ == "__main__":
    unittest.main()
