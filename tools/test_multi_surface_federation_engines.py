"""Tests for the Multi-Surface Startup Federation & Shared Backend Engine Suite.

Covers all 22 startup surface areas across four families, all shared backend planes,
the 7-layer envelope handshakes and preflight self-repairs, known-wrong cross-surface
security controls (session cookies, staff tools, account mutation, external IdP CSP,
section root mismatch, stale release digest, missing staff grant, missing HSTS/no-store),
all four swappable backend dispatch engines, and the cascade failover chain.
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
    COVERAGE_LAYERS,
    LAYER_ACCOUNT,
    LAYER_ANSWERED,
    LAYER_CARRIER,
    LAYER_HANDSHAKE,
    LAYER_PREFLIGHT,
    LAYER_TRACKING,
)
from loop_engine.core.engines.envelope_preflight import (  # noqa: E402
    VERDICT_READY,
    VERDICT_REFUSED,
    VERDICT_REPAIRED,
)
from loop_engine.core.engines.envelope_tracking import (  # noqa: E402
    RESYNC_IN_SYNC,
    RESYNC_NOW,
)
from multi_surface_federation_engines import (  # noqa: E402
    DEFAULT_RELEASE_DIGEST,
    ENGINE_EDGE_MANIFEST,
    ENGINE_HYBRID_SWR,
    ENGINE_ORIGIN_GATEWAY,
    ENGINE_STATIC_FAILOVER,
    FAMILY_COMMERCIAL_CORE,
    FAMILY_LIBRARY_SHOWCASE,
    FAMILY_PUBLIC_GOOD_PROTOCOL,
    FAMILY_STANDALONE_BRAND,
    FEDERATION_ENGINE_IDS,
    PLANE_AFK_APPROVAL_GATE,
    PLANE_BRIEFS_EVIDENCE,
    PLANE_CATALOGUE_PROJECTION,
    PLANE_FEED_DIGEST,
    PLANE_IDENTITY_ENTITLEMENT,
    PLANE_SYSTEMS_VIEW,
    PLANE_TELEMETRY_ROLLUP,
    SHARED_BACKEND_PLANES,
    STALE_RELEASE_DIGEST,
    SURFACE_TOPOLOGY_REGISTRY,
    CrossSurfaceFederationRequest,
    EdgeManifestFederationEngine,
    HybridStaleWhileRevalidateEngine,
    MultiSurfaceFederationOrchestrator,
    OriginScopedGatewayEngine,
    StaticBundleFailoverEngine,
    run_head_to_head_benchmark,
    self_test,
    verify_site_map_and_brand_alignment,
)


class SurfaceTopologyRegistryTests(unittest.TestCase):
    def test_all_twenty_two_startup_surfaces_are_registered_by_family(self) -> None:
        self.assertEqual(len(SURFACE_TOPOLOGY_REGISTRY), 22)
        expected_commercial = {"baltor.ai", "baltor.dev", "systems.baltor.ai"}
        expected_brands = {
            "agentfeeds.si",
            "agentfoundry.si",
            "agentstudios.si",
            "agentafk.si",
            "agentbriefs.si",
        }
        expected_showcase = {
            "deterministicskills.baltor.ai",
            "tools.baltor.ai",
            "cornercases.baltor.ai",
            "docs.baltor.ai",
            "gallery.baltor.ai",
        }
        expected_public_good = {
            "skillsforgood.org",
            "theloopengine.org",
            "loopengine.io",
            "loopengine.dev",
            "agenticengineering.org",
            "openknowledgeformat.org",
            "openintelligenceprotocol.org",
            "openpractitionerprotocol.org",
            "opensolutionprotocol.org",
        }
        by_family = {
            family: {s.hostname for s in SURFACE_TOPOLOGY_REGISTRY.values() if s.family == family}
            for family in (
                FAMILY_COMMERCIAL_CORE,
                FAMILY_STANDALONE_BRAND,
                FAMILY_LIBRARY_SHOWCASE,
                FAMILY_PUBLIC_GOOD_PROTOCOL,
            )
        }
        self.assertEqual(by_family[FAMILY_COMMERCIAL_CORE], expected_commercial)
        self.assertEqual(by_family[FAMILY_STANDALONE_BRAND], expected_brands)
        self.assertEqual(by_family[FAMILY_LIBRARY_SHOWCASE], expected_showcase)
        self.assertEqual(by_family[FAMILY_PUBLIC_GOOD_PROTOCOL], expected_public_good)

    def test_canonical_section_hostnames_align_with_web_site_map(self) -> None:
        alignment = verify_site_map_and_brand_alignment()
        self.assertTrue(alignment["aligned"], alignment["mismatches"])
        self.assertEqual(
            set(alignment["checked_sections"]),
            {"deterministicskills.baltor.ai", "tools.baltor.ai", "cornercases.baltor.ai"},
        )

    def test_all_shared_backend_planes_are_versioned(self) -> None:
        self.assertEqual(len(SHARED_BACKEND_PLANES), 7)
        for plane in SHARED_BACKEND_PLANES:
            self.assertTrue(plane.endswith("/v1"), plane)


class SevenLayerCrossSurfaceHandshakeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.orchestrator = MultiSurfaceFederationOrchestrator()

    def test_known_wrong_carrier_layer_refuses_unregistered_surface_and_bad_plane(self) -> None:
        unknown_host = self.orchestrator.handle(
            CrossSurfaceFederationRequest(
                request_id="req-carrier-unknown-host",
                surface_hostname="unregistered.example.org",
                plane_schema=PLANE_CATALOGUE_PROJECTION,
            )
        )
        self.assertFalse(unknown_host.succeeded)
        self.assertFalse(unknown_host.trace.engine_dispatched)
        self.assertEqual(unknown_host.trace.refused_by, LAYER_CARRIER)
        self.assertEqual(unknown_host.refusal.code, "unregistered_surface_hostname")

        bad_plane = self.orchestrator.handle(
            CrossSurfaceFederationRequest(
                request_id="req-carrier-bad-plane",
                surface_hostname="baltor.ai",
                plane_schema="unknown_plane/v99",
            )
        )
        self.assertFalse(bad_plane.succeeded)
        self.assertFalse(bad_plane.trace.engine_dispatched)
        self.assertEqual(bad_plane.trace.refused_by, LAYER_CARRIER)
        self.assertEqual(bad_plane.refusal.code, "unsupported_shared_plane_schema")

    def test_known_wrong_public_brand_and_protocol_surfaces_refuse_cookies_staff_mutations_and_idp_csp(self) -> None:
        cases = (
            (
                "agentfeeds.si",
                PLANE_FEED_DIGEST,
                {"has_session_cookie": True},
                "cross_surface_session_cookie_forbidden",
            ),
            (
                "agentfoundry.si",
                PLANE_CATALOGUE_PROJECTION,
                {"invokes_staff_tool": True},
                "cross_surface_staff_tool_forbidden",
            ),
            (
                "agentstudios.si",
                PLANE_CATALOGUE_PROJECTION,
                {"mutates_account_state": True},
                "cross_surface_account_mutation_forbidden",
            ),
            (
                "agentafk.si",
                PLANE_AFK_APPROVAL_GATE,
                {"includes_external_idp_csp": True},
                "cross_surface_external_idp_csp_forbidden",
            ),
            (
                "skillsforgood.org",
                PLANE_CATALOGUE_PROJECTION,
                {"has_session_cookie": True},
                "cross_surface_session_cookie_forbidden",
            ),
            (
                "openknowledgeformat.org",
                PLANE_SYSTEMS_VIEW,
                {},
                "plane_not_admitted_for_surface",
            ),
        )
        for idx, (hostname, plane, overrides, expected_code) in enumerate(cases):
            resp = self.orchestrator.handle(
                CrossSurfaceFederationRequest(
                    request_id=f"req-hs-wrong-{idx}",
                    surface_hostname=hostname,
                    plane_schema=plane,
                    **overrides,
                )
            )
            self.assertFalse(resp.succeeded, hostname)
            self.assertFalse(resp.trace.engine_dispatched, hostname)
            self.assertEqual(resp.trace.refused_by, LAYER_HANDSHAKE, hostname)
            self.assertEqual(resp.refusal.code, expected_code, hostname)

    def test_section_canonical_hostnames_enforce_section_root_and_release_digest_parity(self) -> None:
        wrong_root = self.orchestrator.handle(
            CrossSurfaceFederationRequest(
                request_id="req-section-wrong-root",
                surface_hostname="deterministicskills.baltor.ai",
                plane_schema=PLANE_CATALOGUE_PROJECTION,
                section_root="/tools",
            )
        )
        self.assertFalse(wrong_root.succeeded)
        self.assertEqual(wrong_root.trace.refused_by, LAYER_PREFLIGHT)
        self.assertEqual(wrong_root.refusal.code, "section_root_binding_mismatch")

        stale_unrepaired = self.orchestrator.handle(
            CrossSurfaceFederationRequest(
                request_id="req-section-stale-digest",
                surface_hostname="cornercases.baltor.ai",
                plane_schema=PLANE_CATALOGUE_PROJECTION,
                section_root="/corner-cases",
                release_digest=STALE_RELEASE_DIGEST,
                served_release_digest=DEFAULT_RELEASE_DIGEST,
                allow_release_resync=False,
            )
        )
        self.assertFalse(stale_unrepaired.succeeded)
        self.assertEqual(stale_unrepaired.trace.refused_by, LAYER_PREFLIGHT)
        self.assertEqual(stale_unrepaired.refusal.code, "served_release_digest_mismatch")
        self.assertEqual(stale_unrepaired.resync_state, RESYNC_NOW)

        stale_repaired = self.orchestrator.handle(
            CrossSurfaceFederationRequest(
                request_id="req-section-repaired-digest",
                surface_hostname="cornercases.baltor.ai",
                plane_schema=PLANE_CATALOGUE_PROJECTION,
                section_root="/corner-cases",
                release_digest=STALE_RELEASE_DIGEST,
                served_release_digest=DEFAULT_RELEASE_DIGEST,
                allow_release_resync=True,
            )
        )
        self.assertTrue(stale_repaired.succeeded)
        self.assertEqual(stale_repaired.preflight_report.verdict, VERDICT_REPAIRED)
        self.assertEqual(stale_repaired.payload["release_digest"], DEFAULT_RELEASE_DIGEST)

    def test_staff_surface_systems_baltor_ai_enforces_staff_grant_hsts_and_zero_cache(self) -> None:
        no_grant = self.orchestrator.handle(
            CrossSurfaceFederationRequest(
                request_id="req-systems-no-grant",
                surface_hostname="systems.baltor.ai",
                plane_schema=PLANE_SYSTEMS_VIEW,
                staff_grant=False,
            )
        )
        self.assertFalse(no_grant.succeeded)
        self.assertEqual(no_grant.trace.refused_by, LAYER_ACCOUNT)
        self.assertEqual(no_grant.refusal.code, "staff_grant_required")

        no_hsts = self.orchestrator.handle(
            CrossSurfaceFederationRequest(
                request_id="req-systems-no-hsts",
                surface_hostname="systems.baltor.ai",
                plane_schema=PLANE_SYSTEMS_VIEW,
                staff_grant=True,
                hsts_enabled=False,
            )
        )
        self.assertFalse(no_hsts.succeeded)
        self.assertEqual(no_hsts.trace.refused_by, LAYER_PREFLIGHT)
        self.assertEqual(no_hsts.refusal.code, "staff_surface_security_headers_missing")

        bad_cache = self.orchestrator.handle(
            CrossSurfaceFederationRequest(
                request_id="req-systems-bad-cache",
                surface_hostname="systems.baltor.ai",
                plane_schema=PLANE_SYSTEMS_VIEW,
                staff_grant=True,
                hsts_enabled=True,
                cache_control="max-age=60",
            )
        )
        self.assertFalse(bad_cache.succeeded)
        self.assertEqual(bad_cache.trace.refused_by, LAYER_PREFLIGHT)
        self.assertEqual(bad_cache.refusal.code, "staff_surface_security_headers_missing")

        valid_staff = self.orchestrator.handle(
            CrossSurfaceFederationRequest(
                request_id="req-systems-valid",
                surface_hostname="systems.baltor.ai",
                plane_schema=PLANE_SYSTEMS_VIEW,
                staff_grant=True,
                hsts_enabled=True,
                cache_control="no-store",
            )
        )
        self.assertTrue(valid_staff.succeeded)
        self.assertEqual(valid_staff.payload["record_type"], PLANE_SYSTEMS_VIEW)
        self.assertEqual(valid_staff.preflight_report.verdict, VERDICT_READY)
        self.assertEqual(valid_staff.resync_state, RESYNC_IN_SYNC)

    def test_tracking_layer_answers_from_first_result_on_idempotent_replay(self) -> None:
        req = CrossSurfaceFederationRequest(
            request_id="req-replay-agentbriefs-01",
            surface_hostname="agentbriefs.si",
            plane_schema=PLANE_BRIEFS_EVIDENCE,
        )
        first = self.orchestrator.handle(req)
        self.assertTrue(first.succeeded)
        self.assertTrue(first.trace.engine_dispatched)

        second = self.orchestrator.handle(req)
        self.assertTrue(second.succeeded)
        self.assertFalse(second.trace.engine_dispatched)
        self.assertEqual(second.trace.steps[-1], (LAYER_TRACKING, LAYER_ANSWERED))
        self.assertEqual(second.payload["projection_sha256"], first.payload["projection_sha256"])


class SwappableEnginesAndCascadeFailoverTests(unittest.TestCase):
    def test_cascade_fallback_across_all_four_engines_reaches_static_failover_with_shared_allowance(self) -> None:
        orchestrator = MultiSurfaceFederationOrchestrator(
            edge_engine=EdgeManifestFederationEngine(degraded=True),
            swr_engine=HybridStaleWhileRevalidateEngine(
                origin_failures=5,
                circuit_failure_threshold=3,
                cold_surfaces=frozenset({"agentfoundry.si"}),
            ),
            origin_engine=OriginScopedGatewayEngine(
                simulated_concurrent_writers=12,
                lock_saturation_threshold=8,
            ),
            static_engine=StaticBundleFailoverEngine(),
        )
        resp = orchestrator.handle(
            CrossSurfaceFederationRequest(
                request_id="req-full-cascade-agentfoundry",
                surface_hostname="agentfoundry.si",
                plane_schema=PLANE_CATALOGUE_PROJECTION,
            )
        )
        self.assertTrue(resp.succeeded)
        self.assertEqual(resp.selected_engine, ENGINE_STATIC_FAILOVER)
        self.assertEqual(resp.attempted_engines, FEDERATION_ENGINE_IDS)
        self.assertEqual(resp.frame.depth, 4)
        self.assertEqual(resp.frame.allowance.remaining, 0)
        self.assertEqual(resp.payload["delivery_tier"], "static_deterministic_failover")

    def test_hybrid_swr_engine_queues_background_revalidation_and_trips_circuit_breaker(self) -> None:
        swr = HybridStaleWhileRevalidateEngine(origin_failures=2, circuit_failure_threshold=3)
        orchestrator = MultiSurfaceFederationOrchestrator(
            edge_engine=EdgeManifestFederationEngine(degraded=True),
            swr_engine=swr,
        )
        resp = orchestrator.handle(
            CrossSurfaceFederationRequest(
                request_id="req-swr-hit",
                surface_hostname="agentfeeds.si",
                plane_schema=PLANE_FEED_DIGEST,
            )
        )
        self.assertTrue(resp.succeeded)
        self.assertEqual(resp.selected_engine, ENGINE_HYBRID_SWR)
        self.assertEqual(swr.revalidation_queue_depth, 1)
        self.assertFalse(swr.circuit_breaker_open)
        swr.record_origin_failure()
        self.assertTrue(swr.circuit_breaker_open)

    def test_origin_gateway_enforces_per_surface_rate_budget_and_fails_over_cleanly(self) -> None:
        origin = OriginScopedGatewayEngine(simulated_concurrent_writers=1, rate_budget_override=1)
        orchestrator = MultiSurfaceFederationOrchestrator(
            origin_engine=origin,
            static_engine=StaticBundleFailoverEngine(),
            engine_order=(ENGINE_ORIGIN_GATEWAY, ENGINE_STATIC_FAILOVER),
        )
        first = orchestrator.handle(
            CrossSurfaceFederationRequest(
                request_id="req-rate-1",
                surface_hostname="theloopengine.org",
                plane_schema=PLANE_TELEMETRY_ROLLUP,
            )
        )
        self.assertTrue(first.succeeded)
        self.assertEqual(first.selected_engine, ENGINE_ORIGIN_GATEWAY)

        second = orchestrator.handle(
            CrossSurfaceFederationRequest(
                request_id="req-rate-2",
                surface_hostname="theloopengine.org",
                plane_schema=PLANE_TELEMETRY_ROLLUP,
            )
        )
        self.assertTrue(second.succeeded)
        self.assertEqual(second.selected_engine, ENGINE_STATIC_FAILOVER)
        self.assertEqual(second.attempted_engines, (ENGINE_ORIGIN_GATEWAY, ENGINE_STATIC_FAILOVER))

    def test_head_to_head_benchmark_and_self_test_pass(self) -> None:
        result = self_test()
        self.assertTrue(result["passed"], result["checks"])
        bench = run_head_to_head_benchmark()
        self.assertEqual(bench["surface_count"], 22)
        self.assertEqual(len(bench["engine_benchmarks"]), 4)
        self.assertEqual(bench["cascade_failover"]["succeeded"], 22)
        self.assertTrue(bench["security_probes"]["all_blocked_before_engine"])
        self.assertEqual(len(bench["envelope_layers"]), len(COVERAGE_LAYERS))


if __name__ == "__main__":
    unittest.main()
