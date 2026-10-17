"""Unit tests for the `index.baltor.ai` Cloudflare Static Public Site Directory
& `tayloramarel.baltor.ai` Cloudflare Edge Portal Builder, 3-Layer DNS/Route
Root-Cause Auditor & 10-Route Live Reachability Gate Engine Suite.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

REPOSITORY = Path(__file__).resolve().parents[1]
if str(REPOSITORY / "src") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "src"))
if str(REPOSITORY / "tools") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "tools"))

from index_baltor_site_directory_and_tayloramarel_cloudflare_edge_engines import (  # noqa: E402
    ALL_15_PUBLIC_SITE_DIRECTORY_ENTRIES,
    ALL_30_SUBDOMAIN_DEPLOYMENT_AND_REACHABILITY_SCENARIOS,
    CLOUDFLARE_LIVE_EDGE_BINDINGS,
    COVERAGE_LAYERS,
    ENGINE_BALTOR_CLOUDFLARE_EDGE_PORTAL_AND_INDEX_SUITE,
    ENGINE_CLOUDFLARE_WORKER_INDEX_BUNDLE_ASSEMBLER,
    ENGINE_LOCAL_ONLY_HTML_WITHOUT_CLOUDFLARE_DNS_BASELINE,
    ENGINE_TEN_ROUTE_HTTPS_HSTS_PARITY_AUDITOR,
    EXCLUDED_PRIVATE_OR_UNLAUNCHED_HOSTS,
    INDEX_BALTOR_DIRECTORY_ADAPTER,
    LAYER_PREFLIGHT,
    OTHER_AREAS_OF_INTEREST_BULLETS,
    OTHER_AREAS_OF_INTEREST_HEADING,
    SLOT_INDEX_BALTOR_PUBLIC_SITE_DIRECTORY,
    SLOT_TAYLORAMAREL_CLOUDFLARE_EDGE_AND_REACHABILITY_GUARD,
    SURFACE_GROUP_1_CORE_BALTOR,
    SURFACE_GROUP_2_ECOSYSTEM_DOMAINS,
    SURFACE_GROUP_3_PERSONAL_SHOWCASE,
    TAYLORAMAREL_CLOUDFLARE_EDGE_ADAPTER,
    evaluate_index_baltor_and_tayloramarel_cloudflare_edge_suite,
    invoke_index_baltor_public_site_directory_slot,
    invoke_tayloramarel_cloudflare_edge_guard_slot,
    run_known_wrong_refusal_controls,
)


class IndexBaltorSiteDirectoryAndTaylorAmarelCloudflareEdgeTests(unittest.TestCase):
    """Verify Slot Family 1 (`index.baltor.ai` 15-site static directory), Slot Family 2 (`tayloramarel.baltor.ai` Cloudflare Edge Portal & 3-layer diagnostics), 30 scenarios, and 4 known-wrong controls."""

    def test_slot_family_1_index_baltor_public_site_directory_15_sites_and_3_groups(self) -> None:
        res = invoke_index_baltor_public_site_directory_slot({"surface_filter": "all"})
        self.assertTrue(res.accepted)
        self.assertEqual(res.slot_id, SLOT_INDEX_BALTOR_PUBLIC_SITE_DIRECTORY)
        self.assertEqual(set(res.layer_verdicts.keys()), set(COVERAGE_LAYERS))
        self.assertTrue(INDEX_BALTOR_DIRECTORY_ADAPTER.verify_receipt(res))

        out = res.output
        self.assertEqual(out["directory_host"], "index.baltor.ai")
        self.assertEqual(out["total_public_sites"], 15)
        self.assertEqual(
            out["group_counts"],
            {
                "group_1_core_baltor_count": 9,
                "group_2_ecosystem_domains_count": 5,
                "group_3_personal_showcase_count": 1,
            },
        )
        self.assertEqual(out["private_hosts_leaked_count"], 0)
        self.assertTrue(out["zero_cookies_enforced"])
        self.assertTrue(out["hsts_enforced"])

        routes = out["compiled_routes"]
        self.assertEqual(set(routes.keys()), {"/", "/index.json", "/llms.txt"})
        parsed_json = json.loads(routes["/index.json"])
        self.assertEqual(parsed_json["total_public_sites"], 15)
        self.assertEqual(parsed_json["cloudflare_worker"], "baltor-public-site-index")
        self.assertEqual(parsed_json["proxied_dns_record_id"], "340adcb63f02544c950816ff3356cf3c")
        self.assertEqual(parsed_json["worker_route_id"], "1f6842d6b54448c6b489a8a12a945fe7")

        for private_host in EXCLUDED_PRIVATE_OR_UNLAUNCHED_HOSTS:
            self.assertNotIn(private_host, routes["/"])
            self.assertNotIn(private_host, routes["/llms.txt"])

        group2_hosts = {c["host"] for c in out["grouped_sites"][SURFACE_GROUP_2_ECOSYSTEM_DOMAINS]}
        self.assertEqual(
            group2_hosts,
            {
                "agentstudios.si",
                "getagentfoundry.si",
                "agentfeeds.si",
                "agentafk.si",
                "dontbeameatproxy.si",
            },
        )
        group3_hosts = {c["host"] for c in out["grouped_sites"][SURFACE_GROUP_3_PERSONAL_SHOWCASE]}
        self.assertEqual(group3_hosts, {"tayloramarel.baltor.ai"})

    def test_slot_family_2_tayloramarel_cloudflare_edge_and_10_routes(self) -> None:
        res = invoke_tayloramarel_cloudflare_edge_guard_slot({"host": "tayloramarel.baltor.ai"})
        self.assertTrue(res.accepted)
        self.assertEqual(res.slot_id, SLOT_TAYLORAMAREL_CLOUDFLARE_EDGE_AND_REACHABILITY_GUARD)
        self.assertTrue(TAYLORAMAREL_CLOUDFLARE_EDGE_ADAPTER.verify_receipt(res))

        out = res.output
        layers = out["three_layer_edge_verification"]
        self.assertEqual(
            layers["layer_1_proxied_dns_record"]["tayloramarel_dns_id"],
            CLOUDFLARE_LIVE_EDGE_BINDINGS["tayloramarel.baltor.ai"]["proxied_dns_record_id"],
        )
        self.assertEqual(
            layers["layer_2_worker_route_binding"]["tayloramarel_route_id"],
            CLOUDFLARE_LIVE_EDGE_BINDINGS["tayloramarel.baltor.ai"]["worker_route_id"],
        )
        self.assertEqual(
            layers["layer_3_worker_script_upload"]["tayloramarel_worker"],
            "tayloramarel-baltor-portal",
        )
        self.assertEqual(out["tayloramarel_routes_verified_count"], 7)
        self.assertEqual(out["index_baltor_routes_verified_count"], 3)
        self.assertEqual(out["total_edge_routes_verified_count"], 10)

        other_section = out["other_areas_of_interest_section"]
        self.assertEqual(other_section["heading"], OTHER_AREAS_OF_INTEREST_HEADING)
        self.assertEqual(other_section["bullet_count"], len(OTHER_AREAS_OF_INTEREST_BULLETS))
        self.assertTrue(other_section["rendered_in_html"])
        self.assertTrue(out["personal_vs_product_isolation_verified"])
        self.assertEqual(out["personal_product_conflation_rate_pct"], 0.0)

    def test_thin_component_adapter_contract_hot_swap_and_preflight(self) -> None:
        c1 = INDEX_BALTOR_DIRECTORY_ADAPTER.inspect_contract()
        c2 = TAYLORAMAREL_CLOUDFLARE_EDGE_ADAPTER.inspect_contract()
        self.assertLess(c1["loc"], 30)
        self.assertLess(c2["loc"], 30)

        swapped_i = INDEX_BALTOR_DIRECTORY_ADAPTER.swap_engine(
            ENGINE_CLOUDFLARE_WORKER_INDEX_BUNDLE_ASSEMBLER
        )
        self.assertEqual(
            swapped_i.engine_order[0],
            ENGINE_CLOUDFLARE_WORKER_INDEX_BUNDLE_ASSEMBLER,
        )
        swapped_t = TAYLORAMAREL_CLOUDFLARE_EDGE_ADAPTER.swap_engine(
            ENGINE_TEN_ROUTE_HTTPS_HSTS_PARITY_AUDITOR
        )
        self.assertEqual(
            swapped_t.engine_order[0],
            ENGINE_TEN_ROUTE_HTTPS_HSTS_PARITY_AUDITOR,
        )
        self.assertTrue(INDEX_BALTOR_DIRECTORY_ADAPTER.preflight({"surface_filter": "all"}).ready)
        self.assertTrue(
            TAYLORAMAREL_CLOUDFLARE_EDGE_ADAPTER.preflight({"host": "tayloramarel.baltor.ai"}).ready
        )

    def test_four_known_wrong_controls_blocked_at_preflight(self) -> None:
        controls = run_known_wrong_refusal_controls()
        self.assertEqual(controls["probe_count"], 4)
        self.assertTrue(controls["all_blocked_at_preflight"])
        expected_codes = {
            "missing_dns_or_worker_route_binding_blocked": "missing_dns_or_worker_route_binding_refused",
            "private_or_unlaunched_host_in_public_index_blocked": "private_or_unlaunched_host_in_public_index_refused",
            "personal_fellowship_product_conflation_blocked": "personal_fellowship_product_conflation_refused",
            "missing_hsts_or_tls_enforcement_blocked": "missing_hsts_or_tls_enforcement_refused",
        }
        for probe_id, expected_code in expected_codes.items():
            probe = controls["probes"][probe_id]
            self.assertFalse(probe["accepted"])
            self.assertEqual(probe["refused_by"], LAYER_PREFLIGHT)
            self.assertEqual(probe["refusal_code"], expected_code)
            self.assertTrue(probe["blocked_before_engine"])

    def test_full_30_scenario_benchmark_suite(self) -> None:
        self.assertEqual(len(ALL_15_PUBLIC_SITE_DIRECTORY_ENTRIES), 15)
        self.assertEqual(len(ALL_30_SUBDOMAIN_DEPLOYMENT_AND_REACHABILITY_SCENARIOS), 30)
        report = evaluate_index_baltor_and_tayloramarel_cloudflare_edge_suite()
        self.assertEqual(report["scenario_count"], 30)
        self.assertEqual(
            report["scenarios_per_group"],
            {
                SURFACE_GROUP_1_CORE_BALTOR: 13,
                SURFACE_GROUP_2_ECOSYSTEM_DOMAINS: 10,
                SURFACE_GROUP_3_PERSONAL_SHOWCASE: 7,
            },
        )
        self.assertEqual(report["public_ecosystem_sites_indexed_count"], 15)
        self.assertTrue(report["all_scenarios_accepted"])
        self.assertTrue(report["hot_swap_verified"])
        self.assertTrue(report["known_wrong_controls"]["all_blocked_at_preflight"])

        base = report["benchmarks"][ENGINE_LOCAL_ONLY_HTML_WITHOUT_CLOUDFLARE_DNS_BASELINE]
        suite = report["benchmarks"][ENGINE_BALTOR_CLOUDFLARE_EDGE_PORTAL_AND_INDEX_SUITE]
        self.assertEqual(base["tayloramarel_and_index_public_https_reachability_pct"], 0.0)
        self.assertEqual(suite["tayloramarel_and_index_public_https_reachability_pct"], 100.0)
        self.assertEqual(suite["verified_edge_routes_online_count"], 10)
        self.assertEqual(suite["public_ecosystem_sites_indexed_count"], 15)
        self.assertEqual(suite["hsts_tls_security_header_compliance_pct"], 100.0)
        self.assertEqual(suite["personal_product_conflation_rate_pct"], 0.0)


if __name__ == "__main__":
    unittest.main()
