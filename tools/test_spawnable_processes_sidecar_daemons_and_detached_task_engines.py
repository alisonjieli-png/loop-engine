"""Unit tests for the 12 Spawnable Subprocess Daemons, Ephemeral Sidecars & Detached Task Worker Orchestrator Engine Suite."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

REPOSITORY = Path(__file__).resolve().parents[1]
if str(REPOSITORY / "src") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "src"))
if str(REPOSITORY / "tools") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "tools"))

from spawnable_processes_sidecar_daemons_and_detached_task_engines import (  # noqa: E402
    ALL_12_SPAWNABLE_PROCESS_SPECS,
    ALL_24_SPAWNABLE_WORKFLOW_CASES,
    COVERAGE_LAYERS,
    ENGINE_BACKPRESSURE_IPC_BROKER,
    ENGINE_BALTOR_12_SPAWNABLE_SUPERVISOR,
    ENGINE_BLOCKING_IN_CONTEXT_BASELINE,
    ENGINE_CATALOG_ORCHESTRator,
    ENGINE_CGROUP_PGID_SUPERVISOR,
    ENGINE_DETACHED_DISPATCH_ROUTER,
    HOST_CGROUP_MEM_MAX_MB,
    LAYER_PREFLIGHT,
    LAYER_REFUSED,
    MAX_IPC_SUMMARY_BYTES_LIMIT,
    PROCESS_SPEC_BY_ID,
    PROCESS_SUPERVISOR_ENGINE_ORDER,
    SLOT_PROCESS_SUPERVISOR_REAPER,
    SLOT_SPAWNABLE_PROCESS_CATALOG,
    SPAWNABLE_CATALOG_ENGINE_ORDER,
    EnvelopeInvocationRequest,
    SpawnableProcessAndSidecarCatalogSlot,
    SpawnableProcessSupervisorAndReaperSlot,
    run_known_wrong_controls,
    run_spawnable_processes_benchmark,
)


class SpawnableProcessesAndSidecarEngineSuiteTests(unittest.TestCase):
    def test_twelve_spawnable_process_specifications_and_bounds(self) -> None:
        self.assertEqual(len(ALL_12_SPAWNABLE_PROCESS_SPECS), 12)
        expected_ids = (
            "P01_incremental_test_and_verifier_watcher_daemon",
            "P02_mmap_rust_matryoshka_and_lsh_index_sidecar",
            "P03_ast_symbol_digest_and_callgraph_guard_daemon",
            "P04_out_of_core_duckdb_and_dataset_profiler_worker",
            "P05_detached_counterexample_bisection_shrinker_worker",
            "P06_headless_3d_cad_and_200layer_media_render_worker",
            "P07_offpeak_overnight_cheap_local_model_refactor_daemon",
            "P08_ephemeral_bubblewrap_redteam_and_untrusted_code_sandbox",
            "P09_deterministic_webhook_and_microservice_replay_sidecar",
            "P10_two_way_portable_trend_and_directory_spider_worker",
            "P11_shadow_speculative_verifier_and_ab_gauntlet_runner",
            "P12_local_and_public_pii_anonymizer_spool_daemon",
        )
        self.assertEqual(tuple(s.process_id for s in ALL_12_SPAWNABLE_PROCESS_SPECS), expected_ids)
        for spec in ALL_12_SPAWNABLE_PROCESS_SPECS:
            self.assertGreater(spec.mem_max_mb, 0)
            self.assertLessEqual(spec.mem_max_mb, HOST_CGROUP_MEM_MAX_MB)
            self.assertGreater(spec.lease_ttl_seconds, 0)
            self.assertLessEqual(spec.max_ipc_summary_bytes, MAX_IPC_SUMMARY_BYTES_LIMIT)
            self.assertIn(spec.loop_role, ("Practitioner", "Intelligence", "Solution"))
            self.assertIn(spec.loop_mode, ("deterministic", "hybrid", "non-deterministic"))

        p01 = PROCESS_SPEC_BY_ID["P01_incremental_test_and_verifier_watcher_daemon"]
        self.assertLess(p01.max_receipt_tokens, 120)
        p02 = PROCESS_SPEC_BY_ID["P02_mmap_rust_matryoshka_and_lsh_index_sidecar"]
        self.assertLess(p02.ipc_roundtrip_latency_ms, 0.30)
        p04 = PROCESS_SPEC_BY_ID["P04_out_of_core_duckdb_and_dataset_profiler_worker"]
        self.assertLess(p04.max_receipt_tokens, 200)
        p07 = PROCESS_SPEC_BY_ID["P07_offpeak_overnight_cheap_local_model_refactor_daemon"]
        self.assertEqual(p07.detached_worktree_policy, "git_worktree_detached_head_only")

    def test_slot_family_1_catalog_7_layer_envelope_and_nested_supervision(self) -> None:
        slot = SpawnableProcessAndSidecarCatalogSlot()
        res = slot.spawn_and_execute_workflow("WF_07", request_id="test_wf_07")
        self.assertTrue(res.accepted)
        self.assertEqual(res.slot_id, SLOT_SPAWNABLE_PROCESS_CATALOG)
        self.assertEqual(res.selected_engine, ENGINE_CATALOG_ORCHESTRator)
        self.assertEqual(res.fallback_chain_tried, (ENGINE_CATALOG_ORCHESTRator,))
        self.assertEqual(set(res.layer_verdicts.keys()), set(COVERAGE_LAYERS))
        self.assertTrue(all(v == "full" for v in res.layer_verdicts.values()))
        self.assertEqual(res.output["process_id"], "P04_out_of_core_duckdb_and_dataset_profiler_worker")
        self.assertTrue(res.output["nested_supervisor_accepted"])
        sup_rcpt = res.output["supervision_receipt"]
        self.assertTrue(sup_rcpt["pgid_reaped_cleanly"])
        self.assertEqual(sup_rcpt["leaked_orphan_processes"], 0)
        self.assertTrue(sup_rcpt["ipc_within_2048_byte_cap"])

        res_alt = slot.spawn_and_execute_workflow(
            "WF_13",
            request_id="test_wf_13_router",
            preferred_engine=ENGINE_DETACHED_DISPATCH_ROUTER,
        )
        self.assertTrue(res_alt.accepted)
        self.assertEqual(res_alt.selected_engine, ENGINE_DETACHED_DISPATCH_ROUTER)
        self.assertEqual(res_alt.fallback_chain_tried, SPAWNABLE_CATALOG_ENGINE_ORDER)

    def test_slot_family_2_supervisor_reaper_and_backpressure_ipc_broker(self) -> None:
        sup = SpawnableProcessSupervisorAndReaperSlot()
        res = sup.supervise_and_reap_worker(
            "WF_11",
            request_id="test_sup_wf_11",
            preferred_engine=ENGINE_BACKPRESSURE_IPC_BROKER,
        )
        self.assertTrue(res.accepted)
        self.assertEqual(res.slot_id, SLOT_PROCESS_SUPERVISOR_REAPER)
        self.assertEqual(res.selected_engine, ENGINE_BACKPRESSURE_IPC_BROKER)
        self.assertEqual(res.fallback_chain_tried, PROCESS_SUPERVISOR_ENGINE_ORDER)
        self.assertEqual(res.output["mem_max_mb"], 3072)
        self.assertTrue(res.output["heartbeat_verified"])
        self.assertTrue(res.output["ipc_within_2048_byte_cap"])
        self.assertEqual(res.output["leaked_orphan_processes"], 0)
        self.assertEqual(res.output["raw_log_tokens_suppressed"], 2500)

    def test_envelope_idempotency_and_carrier_schema_guards(self) -> None:
        slot = SpawnableProcessAndSidecarCatalogSlot()
        r1 = slot.spawn_and_execute_workflow("WF_01", request_id="idem_spawn_01")
        r2 = slot.spawn_and_execute_workflow("WF_01", request_id="idem_spawn_01")
        self.assertEqual(r1.payload_digest, r2.payload_digest)
        self.assertTrue(r2.accepted)

        conflict = slot.spawn_and_execute_workflow("WF_02", request_id="idem_spawn_01")
        self.assertFalse(conflict.accepted)
        self.assertIsNotNone(conflict.refusal)
        assert conflict.refusal is not None
        self.assertEqual(conflict.refusal.code, "idempotency_payload_conflict")

        bad_schema_req = EnvelopeInvocationRequest(
            slot_id=SLOT_SPAWNABLE_PROCESS_CATALOG,
            request_id="bad_schema_spawn",
            payload={"workflow_id": "WF_01"},
            schema_version="unsupported.schema.v0",
        )
        bad_schema_res = slot.envelope.execute(bad_schema_req, slot._dispatch)
        self.assertFalse(bad_schema_res.accepted)
        assert bad_schema_res.refusal is not None
        self.assertEqual(bad_schema_res.refusal.code, "carrier_schema_invalid")

    def test_24_workflow_spawnable_processes_benchmark_metrics(self) -> None:
        self.assertEqual(len(ALL_24_SPAWNABLE_WORKFLOW_CASES), 24)
        bench = run_spawnable_processes_benchmark()
        self.assertEqual(bench["total_workflows"], 24)
        self.assertEqual(bench["total_spawnable_process_specs"], 12)
        self.assertEqual(bench["workflows_per_process_spec"], 2)
        self.assertTrue(bench["all_24_workflows_executed_through_7_layer_envelope"])

        baseline = bench["single_threaded_blocking_in_context_agent_baseline"]
        self.assertEqual(baseline["engine_id"], ENGINE_BLOCKING_IN_CONTEXT_BASELINE)
        self.assertEqual(baseline["total_foreground_turn_latency_ms"], 96000.0)
        self.assertEqual(baseline["mean_foreground_turn_latency_ms"], 4000.0)
        self.assertEqual(baseline["total_subprocess_context_tokens"], 38400)
        self.assertEqual(baseline["oom_or_zombie_leak_workflows"], 7)
        self.assertEqual(baseline["oom_or_zombie_leak_rate_pct"], "29.2%")

        supervised = bench["baltor_12_spawnable_process_and_sidecar_supervisor"]
        self.assertEqual(supervised["engine_id"], ENGINE_BALTOR_12_SPAWNABLE_SUPERVISOR)
        self.assertEqual(supervised["total_foreground_turn_latency_ms"], 10176.0)
        self.assertEqual(supervised["mean_foreground_turn_latency_ms"], 424.0)
        self.assertEqual(supervised["foreground_turn_latency_reduction_pct"], "89.4%")
        self.assertEqual(supervised["total_subprocess_context_tokens"], 840)
        self.assertEqual(supervised["context_bloat_reduction_pct"], "97.8%")
        self.assertEqual(supervised["oom_or_zombie_leak_workflows"], 0)
        self.assertEqual(supervised["oom_or_zombie_leak_rate_pct"], "0.0%")
        self.assertEqual(supervised["mem_max_enforcement_rate_pct"], "100.0%")
        self.assertEqual(supervised["pgid_clean_reap_rate_pct"], "100.0%")

    def test_four_known_wrong_preflight_refusal_controls(self) -> None:
        kw = run_known_wrong_controls()
        self.assertEqual(kw["total_controls"], 4)
        self.assertEqual(kw["passed_controls"], 4)
        expected_codes = {
            "unbounded_memory_or_ttl_spawn_refused",
            "raw_stdout_context_flood_refused",
            "named_branch_in_detached_worker_refused",
            "orphan_or_zombie_survival_after_lease_revocation_refused",
        }
        observed_codes = {c["actual_refusal_code"] for c in kw["controls"]}
        self.assertEqual(observed_codes, expected_codes)
        for ctrl in kw["controls"]:
            self.assertTrue(ctrl["passed"])
            self.assertEqual(ctrl["refused_by_layer"], LAYER_PREFLIGHT)
            self.assertTrue(ctrl["refused_before_engine"])


if __name__ == "__main__":
    unittest.main()
