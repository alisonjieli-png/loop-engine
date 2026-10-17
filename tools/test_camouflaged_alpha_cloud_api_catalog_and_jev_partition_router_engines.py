"""Tests for Camouflaged Alpha Quantification, 401 Cloud API Catalog & Jev CPU Micro-Model Partition Router."""
from __future__ import annotations

import unittest

from tools.camouflaged_alpha_cloud_api_catalog_and_jev_partition_router_engines import (
    CAMOUFLAGED_ALPHA_ENVELOPE,
    JEV_PARTITION_ROUTER_ENVELOPE,
    RAPIDAPI_SEVEN_ENDPOINTS,
    build_searchable_cloud_api_catalog,
    execute_camouflaged_alpha_quantifier,
    execute_jev_partition_and_cloud_api_router,
)


class CamouflagedAlphaCloudApiAndJevRouterTests(unittest.TestCase):
    def test_envelopes_are_valid(self) -> None:
        self.assertEqual(
            CAMOUFLAGED_ALPHA_ENVELOPE.component,
            "camouflaged_alpha_and_international_law_hierarchy_slot",
        )
        self.assertEqual(
            JEV_PARTITION_ROUTER_ENVELOPE.component,
            "jev_probability_blocking_key_partition_router_slot",
        )

    def test_camouflaged_alpha_quantifier_overrides_surface_capture(self) -> None:
        res = execute_camouflaged_alpha_quantifier({"evaluate_all": True})
        self.assertEqual(res.status, "ok")
        self.assertEqual(res.value["cases_evaluated"], 4)
        self.assertGreater(res.value["mean_posterior_alpha_probability"], 0.90)
        for rec in res.value["records"]:
            self.assertTrue(rec["surface_capture_overridden"])
            self.assertLessEqual(rec["contract_card_bytes"], 2048)

    def test_camouflaged_alpha_known_wrong_refusals(self) -> None:
        ref1 = execute_camouflaged_alpha_quantifier(
            {"ignore_international_iom_agreements_for_local_law": True}
        )
        self.assertEqual(ref1.status, "refused")
        self.assertEqual(ref1.refusal.code, "local_statute_override_of_iom_treaty_refused")

        ref2 = execute_camouflaged_alpha_quantifier(
            {"accept_surface_sec_narrative_without_footnote_graph": True}
        )
        self.assertEqual(ref2.status, "refused")
        self.assertEqual(ref2.refusal.code, "unverified_surface_sec_narrative_capture_refused")

    def test_searchable_cloud_api_catalog_has_401_endpoints_and_7_rapidapi(self) -> None:
        catalog = build_searchable_cloud_api_catalog()
        self.assertEqual(len(catalog), 401)
        self.assertEqual(len(RAPIDAPI_SEVEN_ENDPOINTS), 7)
        for ep in RAPIDAPI_SEVEN_ENDPOINTS:
            self.assertEqual(
                ep.credential_keyring_ref,
                "loop-engine|rapidapi|social-media-video-downloaders",
            )

    def test_jev_caller_probabilities_90_5_5_reduces_search_space_4738x(self) -> None:
        res = execute_jev_partition_and_cloud_api_router(
            {
                "query_id": "jev_90_5_5",
                "query_text": "Download Facebook reel video via API",
                "caller_jev_probabilities": {
                    "cloud_api_only": 0.90,
                    "custom_scraper_util": 0.05,
                    "all_possible_solutions": 0.05,
                },
                "top_k": 20,
            }
        )
        self.assertEqual(res.status, "ok")
        route = res.value["route_result"]
        self.assertEqual(route["inference_tier_used"], "tier0_caller_explicit_jev_priors_and_blocking_key")
        self.assertEqual(route["candidate_records_scanned"], 401)
        self.assertGreaterEqual(route["search_space_reduction_factor"], 4738.0)
        self.assertFalse(route["escalated_to_complex_model"])

    def test_cpu_micro_model_predicts_jev_priors_under_1ms(self) -> None:
        res = execute_jev_partition_and_cloud_api_router(
            {"query_text": "Find RapidAPI or Mistral endpoint for video download"}
        )
        self.assertEqual(res.status, "ok")
        route = res.value["route_result"]
        self.assertEqual(route["inference_tier_used"], "tier1_cpu_int8_linear_micro_model")
        self.assertLess(route["inference_latency_ms"], 1.0)
        self.assertEqual(route["jev_probabilities"]["cloud_api_only"], 0.90)

    def test_jev_router_known_wrong_refusals(self) -> None:
        ref1 = execute_jev_partition_and_cloud_api_router({"hardcoded_secret_in_query": True})
        self.assertEqual(ref1.status, "refused")
        self.assertEqual(ref1.refusal.code, "hardcoded_api_credential_in_query_refused")

        ref2 = execute_jev_partition_and_cloud_api_router(
            {"caller_jev_probabilities": {"cloud_api_only": 1.5, "custom_scraper_util": -0.2}}
        )
        self.assertEqual(ref2.status, "refused")
        self.assertEqual(ref2.refusal.code, "invalid_jev_probability_simplex_refused")


if __name__ == "__main__":
    unittest.main()
