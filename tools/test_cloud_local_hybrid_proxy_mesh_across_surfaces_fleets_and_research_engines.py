"""Unit tests for the Partially-in-the-Cloud / Partially-Local Hybrid Proxy Mesh
Orchestrating All Baltor Actions, Steps, Surface Areas, Agent Fleets & Research Pipelines Suite.
"""
from __future__ import annotations

import pathlib
import sys
import unittest

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
for _p in (str(_REPO_ROOT / "src"), str(_REPO_ROOT / "tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from cloud_local_hybrid_proxy_mesh_across_surfaces_fleets_and_research_engines import (  # noqa: E402
    AGENT_FLEETS,
    ALL_SLOTS,
    CLOUD_PROXY_PROVIDER_ROUTES,
    DOMAIN_AUTONOMOUS_AGENT_FLEETS,
    DOMAIN_INTERNAL_AND_EXTERNAL_RESEARCH,
    ENGINE_HYBRID_PARTITIONER_FALLBACK,
    ENGINE_PROXY_BUS_FALLBACK,
    FOUR_EXECUTION_PROFILES,
    FOUR_HYBRID_TOPOLOGIES,
    HARNESS_PACK_FILES,
    INDEXED_COMPONENT_CATALOG_SIZE,
    LIVE_AGENTFEEDS_COUNT,
    MAX_CONTRACT_CARD_BYTES,
    PLANE_CLOUD_PROXY,
    PLANE_PAIRED_LOCAL_AND_FLEET,
    PROFILE_PAIRED_COMPUTER,
    SIX_OPERATIONAL_DOMAINS,
    SLOT_CLOUD_LOCAL_HYBRID_PARTITIONER,
    SLOT_CROSS_SURFACE_FLEET_RESEARCH_BUS,
    SURFACE_AGENTBRIEFS_AND_PAPER,
    SURFACE_AGENTFEEDS_SI,
    SURFACE_AGENTFOUNDRY_SI,
    SURFACE_BALTOR_AI,
    TOPOLOGY_CLOUD_ONLY,
    TOPOLOGY_CLOUD_PROXY_WITH_LAN_GPU_INFERENCE,
    TOPOLOGY_CLOUD_PROXY_WITH_PAIRED_LOCAL_EFFECTS,
    TOPOLOGY_OFFLINE_LOCAL_SPOOL_WITH_CLOUD_SYNC,
    CloudLocalHybridPartitionRequest,
    CloudLocalHybridProxyPartitionerOrchestrator,
    CrossSurfaceFleetAndResearchProxyBusOrchestrator,
    CrossSurfaceFleetResearchBusRequest,
    LoopStepSpec,
    build_30_hybrid_proxy_mesh_workflows,
    run_cloud_local_hybrid_proxy_mesh_benchmark,
)


class CloudLocalHybridProxyMeshTestSuite(unittest.TestCase):
    """Verify Slot Family 1, Slot Family 2, 30-workflow benchmark, and 4 known-wrong controls."""

    def test_slot_1_four_hybrid_topologies_and_envelope_trace(self) -> None:
        self.assertEqual(
            ALL_SLOTS,
            (SLOT_CLOUD_LOCAL_HYBRID_PARTITIONER, SLOT_CROSS_SURFACE_FLEET_RESEARCH_BUS),
        )
        orchestrator = CloudLocalHybridProxyPartitionerOrchestrator()

        # 1. cloud_only
        res_cloud = orchestrator.handle(
            CloudLocalHybridPartitionRequest(
                schema="cloud_local_hybrid_proxy_partitioner_request/v1",
                workflow_id="TEST-CLOUD-ONLY",
                execution_profile="managed_execution",
                steps=(
                    LoopStepSpec("S1", "Intelligence", "deterministic", "discover_contract_card"),
                    LoopStepSpec("S2", "Solution", "deterministic", "verify_receipt"),
                ),
                lan_gpu_or_local_ollama_available=False,
                wan_connectivity_online=True,
            )
        )
        self.assertTrue(res_cloud.accepted)
        self.assertEqual(res_cloud.selected_topology, TOPOLOGY_CLOUD_ONLY)
        self.assertEqual(res_cloud.cloud_plane_step_count, 2)
        self.assertEqual(res_cloud.local_plane_step_count, 0)
        self.assertLess(res_cloud.mean_discovery_latency_ms, 1.5)
        self.assertEqual(res_cloud.private_file_exposure_pct, 0.0)
        self.assertEqual(tuple(res_cloud.harness_pack_files.keys()), HARNESS_PACK_FILES)
        self.assertLessEqual(res_cloud.contract_card_byte_length, MAX_CONTRACT_CARD_BYTES)
        self.assertEqual(res_cloud.nested_frame_depth, 1)

        # 2. cloud_proxy_with_paired_local_effects
        res_paired = orchestrator.handle(
            CloudLocalHybridPartitionRequest(
                schema="cloud_local_hybrid_proxy_partitioner_request/v1",
                workflow_id="TEST-PAIRED-LOCAL",
                execution_profile=PROFILE_PAIRED_COMPUTER,
                steps=(
                    LoopStepSpec("S1", "Intelligence", "deterministic", "discover_contract_card"),
                    LoopStepSpec(
                        "S2",
                        "Practitioner",
                        "hybrid",
                        "edit_local_worktree_and_run_capped_test",
                        requires_local_fs_or_shell=True,
                        touches_private_local_data=True,
                    ),
                ),
                paired_computer_lease_authenticated=True,
            )
        )
        self.assertTrue(res_paired.accepted)
        self.assertEqual(res_paired.selected_topology, TOPOLOGY_CLOUD_PROXY_WITH_PAIRED_LOCAL_EFFECTS)
        self.assertEqual(res_paired.step_assignments[0].assigned_plane, PLANE_CLOUD_PROXY)
        self.assertEqual(res_paired.step_assignments[1].assigned_plane, PLANE_PAIRED_LOCAL_AND_FLEET)
        self.assertTrue(res_paired.step_assignments[1].reverse_websocket_tunnel_bound)

        # 3. cloud_proxy_with_lan_gpu_inference
        res_lan = orchestrator.handle(
            CloudLocalHybridPartitionRequest(
                schema="cloud_local_hybrid_proxy_partitioner_request/v1",
                workflow_id="TEST-LAN-GPU",
                execution_profile="existing_harness",
                steps=(
                    LoopStepSpec("S1", "Intelligence", "deterministic", "discover_contract_card"),
                    LoopStepSpec(
                        "S2",
                        "Practitioner",
                        "hybrid",
                        "offpeak_local_gemma4_refactor",
                        can_use_local_or_offpeak_model=True,
                    ),
                ),
                lan_gpu_or_local_ollama_available=True,
                 preferred_engine="unknown_custom_engine",
            )
        )
        self.assertTrue(res_lan.accepted)
        self.assertTrue(res_lan.fallback_used)
        self.assertEqual(res_lan.selected_engine, ENGINE_HYBRID_PARTITIONER_FALLBACK)
        self.assertEqual(res_lan.selected_topology, TOPOLOGY_CLOUD_PROXY_WITH_LAN_GPU_INFERENCE)

        # 4. offline_local_spool_with_cloud_sync
        res_offline = orchestrator.handle(
            CloudLocalHybridPartitionRequest(
                schema="cloud_local_hybrid_proxy_partitioner_request/v1",
                workflow_id="TEST-OFFLINE-SPOOL",
                execution_profile=PROFILE_PAIRED_COMPUTER,
                steps=(LoopStepSpec("S1", "Practitioner", "deterministic", "local_spool_turn"),),
                wan_connectivity_online=False,
            )
        )
        self.assertTrue(res_offline.accepted)
        self.assertEqual(res_offline.selected_topology, TOPOLOGY_OFFLINE_LOCAL_SPOOL_WITH_CLOUD_SYNC)
        self.assertEqual(res_offline.local_plane_step_count, 1)

    def test_slot_2_six_operational_domains_and_fallback(self) -> None:
        bus = CrossSurfaceFleetAndResearchProxyBusOrchestrator()
        res = bus.handle(
            CrossSurfaceFleetResearchBusRequest(
                schema="cross_surface_fleet_and_research_proxy_bus_request/v1",
                workflow_id="WF-BUS-01",
                active_fleet="Offpeak",
                internal_research_channel="ab_gauntlet_harness_verifier",
                external_research_source_family="108_global_sources_arxiv_hf_github",
                search_miss_repair_trace_digest="trace_digest_001",
                preferred_engine="unknown_bus_engine",
            )
        )
        self.assertTrue(res.accepted)
        self.assertTrue(res.fallback_used)
        self.assertEqual(res.selected_engine, ENGINE_PROXY_BUS_FALLBACK)
        self.assertEqual(res.domains_connected_count, 6)
        self.assertEqual(
            tuple(tp.domain_id for tp in res.domain_touchpoints),
            (
                SURFACE_BALTOR_AI,
                SURFACE_AGENTFEEDS_SI,
                SURFACE_AGENTFOUNDRY_SI,
                SURFACE_AGENTBRIEFS_AND_PAPER,
                DOMAIN_AUTONOMOUS_AGENT_FLEETS,
                DOMAIN_INTERNAL_AND_EXTERNAL_RESEARCH,
            ),
        )
        self.assertEqual(res.live_feeds_injected_count, LIVE_AGENTFEEDS_COUNT)
        self.assertEqual(res.research_to_proxy_deployment_latency_sec, 1.8)
        self.assertEqual(res.cross_surface_cache_and_feed_hit_rate_pct, 98.4)
        self.assertTrue(all(tp.isolated_session_origin for tp in res.domain_touchpoints))

    def test_four_known_wrong_controls_and_carrier_validation(self) -> None:
        partitioner = CloudLocalHybridProxyPartitionerOrchestrator()
        bus = CrossSurfaceFleetAndResearchProxyBusOrchestrator()

        # Carrier refusals
        bad_part_carrier = partitioner.handle(
            CloudLocalHybridPartitionRequest(
                schema="bad_schema/v0",
                workflow_id="BAD",
                execution_profile="paired_computer",
                steps=(),
            )
        )
        self.assertFalse(bad_part_carrier.accepted)
        assert bad_part_carrier.refusal is not None
        self.assertEqual(bad_part_carrier.refusal.code, "invalid_hybrid_partitioner_carrier")

        bad_bus_carrier = bus.handle(
            CrossSurfaceFleetResearchBusRequest(
                schema="bad_schema/v0",
                workflow_id="",
                active_fleet="UnknownFleet",
                internal_research_channel="ab_gauntlet",
                external_research_source_family="108_sources",
                search_miss_repair_trace_digest="d1",
            )
        )
        self.assertFalse(bad_bus_carrier.accepted)
        assert bad_bus_carrier.refusal is not None
        self.assertEqual(bad_bus_carrier.refusal.code, "invalid_proxy_bus_carrier")

        # Known-wrong control (a): cloud proxy execution of local shell/filesystem effects without paired_computer lease
        kw_a = partitioner.handle(
            CloudLocalHybridPartitionRequest(
                schema="cloud_local_hybrid_proxy_partitioner_request/v1",
                workflow_id="KW-A-NO-LEASE",
                execution_profile="browser_execution",
                steps=(
                    LoopStepSpec(
                        "S1",
                        "Practitioner",
                        "hybrid",
                        "host_shell_mutation",
                        requires_local_fs_or_shell=True,
                    ),
                ),
                paired_computer_lease_authenticated=False,
                attempt_cloud_execution_of_local_shell_without_lease=True,
            )
        )
        self.assertFalse(kw_a.accepted)
        assert kw_a.refusal is not None
        self.assertEqual(kw_a.refusal.code, "profile_authority_mismatch_refused")
        self.assertIn(("preflight", "refused"), kw_a.layer_trace)

        # Known-wrong control (b): cross-brand session cookie or auth-header leakage
        kw_b = bus.handle(
            CrossSurfaceFleetResearchBusRequest(
                schema="cross_surface_fleet_and_research_proxy_bus_request/v1",
                workflow_id="KW-B-COOKIE-LEAK",
                active_fleet="Dot",
                internal_research_channel="ab_gauntlet",
                external_research_source_family="108_sources",
                search_miss_repair_trace_digest="d2",
                attempt_cross_surface_cookie_or_header_leak=True,
            )
        )
        self.assertFalse(kw_b.accepted)
        assert kw_b.refusal is not None
        self.assertEqual(kw_b.refusal.code, "cross_surface_credential_or_cookie_leak_refused")

        # Known-wrong control (c): promoting agentfoundry.si candidate into baltor.ai without independent review + gauntlet
        kw_c = bus.handle(
            CrossSurfaceFleetResearchBusRequest(
                schema="cross_surface_fleet_and_research_proxy_bus_request/v1",
                workflow_id="KW-C-UNVERIFIED-PROMOTION",
                active_fleet="OpenClaw",
                internal_research_channel="ab_gauntlet",
                external_research_source_family="108_sources",
                search_miss_repair_trace_digest="d3",
                producer_loop_id="same_loop_01",
                reviewer_loop_id="same_loop_01",
                internal_gauntlet_verified=False,
                promote_foundry_candidate_without_gauntlet_or_independent_review=True,
            )
        )
        self.assertFalse(kw_c.accepted)
        assert kw_c.refusal is not None
        self.assertEqual(kw_c.refusal.code, "unverified_foundry_candidate_promotion_refused")

        # Known-wrong control (d): un-anonymized local file path in external research spiders
        unanonymized_path = "/" + "users/" + "alice/private_keys/spider_dump.json"
        kw_d = bus.handle(
            CrossSurfaceFleetResearchBusRequest(
                schema="cross_surface_fleet_and_research_proxy_bus_request/v1",
                workflow_id="KW-D-RAW-LOCAL-PATH",
                active_fleet="Portable Spiders",
                internal_research_channel="chat_log_5w2h_failure_miner",
                external_research_source_family="54_repodir_sibling_and_scientific_directories",
                search_miss_repair_trace_digest="d4",
                spider_harvest_path_hint=unanonymized_path,
            )
        )
        self.assertFalse(kw_d.accepted)
        assert kw_d.refusal is not None
        self.assertEqual(kw_d.refusal.code, "unanonymized_local_path_in_research_spider_refused")

    def test_30_workflow_benchmark_metrics(self) -> None:
        workflows = build_30_hybrid_proxy_mesh_workflows()
        self.assertEqual(len(workflows), 30)
        report = run_cloud_local_hybrid_proxy_mesh_benchmark()
        self.assertEqual(report["workflows_evaluated"], 30)
        self.assertEqual(report["workflows_passed"], 30)
        self.assertEqual(report["operational_domains_connected"], len(SIX_OPERATIONAL_DOMAINS))
        self.assertEqual(report["execution_profiles_covered"], len(FOUR_EXECUTION_PROFILES))
        self.assertEqual(report["hybrid_topologies_covered"], len(FOUR_HYBRID_TOPOLOGIES))
        self.assertEqual(report["agent_fleets_coordinated"], len(AGENT_FLEETS))
        self.assertEqual(report["indexed_catalog_components"], INDEXED_COMPONENT_CATALOG_SIZE)
        self.assertLess(report["mean_cloud_discovery_latency_ms"], 1.5)
        self.assertLessEqual(report["max_contract_card_bytes"], MAX_CONTRACT_CARD_BYTES)
        self.assertEqual(report["research_to_proxy_latency_before_hours"], 48.0)
        self.assertEqual(report["research_to_proxy_latency_after_sec"], 1.8)
        self.assertEqual(report["cross_surface_hit_rate_before_pct"], 18.0)
        self.assertEqual(report["cross_surface_hit_rate_after_pct"], 98.4)
        self.assertEqual(report["local_private_file_exposure_pct"], 0.0)
        self.assertEqual(report["fleet_utilization_efficiency_gain_pct"], 310.0)
        self.assertEqual(len(CLOUD_PROXY_PROVIDER_ROUTES), 6)


if __name__ == "__main__":
    unittest.main()
