"""Tests and known-wrong controls for Pillar 5: Sub-2ms Capability Cache,
Real-Time Traceback Auto-Healer, and Detached-Worktree Multi-Agent Swarm Coordinator.
"""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
if str(HERE.parent / "src") not in sys.path:
    sys.path.insert(0, str(HERE.parent / "src"))

import unicorn_zero_latency_cache_healer_and_swarm_engines as pillar5  # noqa: E402
from loop_engine.core.engines.envelope import COVERAGE_LAYERS, LAYER_REFUSED  # noqa: E402


class UnicornZeroLatencyCacheHealerAndSwarmTests(unittest.TestCase):
    """Verify all 3 slot families, 7 envelope layers, and 4 known-wrong controls."""

    def test_slot1_two_tier_local_and_edge_capability_cache_and_release_invalidation(self) -> None:
        slot = pillar5.Sub2msCapabilityCacheSlot()

        # 1. Exact local Bloom + LRU hit in < 1 ms
        exact = slot.resolve(
            "sqlite operationalerror database is locked store busy wal timeout",
            request_id="test_exact_01",
        )
        self.assertTrue(exact.accepted)
        self.assertEqual(exact.selected_engine, pillar5.ENGINE_LOCAL_BLOOM_MATRYOSHKA)
        self.assertEqual(exact.output["hit_tier"], "local_exact_bloom_lru")
        self.assertLess(float(exact.output["measured_local_ms"]), 1.0)
        for layer in COVERAGE_LAYERS:
            self.assertEqual(exact.layer_verdicts[layer], "full")

        # 2. Near-exact 64-bit binary Matryoshka LSH hit in < 1 ms
        near = slot.resolve(
            "sqlite database locked operationalerror store busy wal",
            request_id="test_near_01",
        )
        self.assertTrue(near.accepted)
        self.assertEqual(near.selected_engine, pillar5.ENGINE_LOCAL_BLOOM_MATRYOSHKA)
        self.assertIn(
            near.output["hit_tier"],
            ("local_exact_bloom_lru", "local_matryoshka_lsh_near_hit"),
        )
        self.assertLess(float(near.output["measured_local_ms"]), 1.0)

        # 3. Advance release digest -> immediate invalidation of stale local LRU entries
        evicted = slot.advance_release_digest("sha256:rel_2026_10_17_v2")
        self.assertGreaterEqual(evicted, 4)

        # Next lookup seamlessly falls back to Cloudflare Edge KV (< 15 ms) and re-pins to v2
        revalidated = slot.resolve(
            "sqlite operationalerror database is locked store busy wal timeout",
            request_id="test_edge_swr_01",
        )
        self.assertTrue(revalidated.accepted)
        self.assertEqual(revalidated.selected_engine, pillar5.ENGINE_CLOUDFLARE_EDGE_SWR)
        self.assertEqual(revalidated.output["release_digest"], "sha256:rel_2026_10_17_v2")
        self.assertLess(float(revalidated.output["measured_local_ms"]), 15.0)

        # 4. Completely unseen capability falls back to Origin MCP Streamable HTTP
        origin = slot.resolve(
            "unseen webgpu SubgroupMatrixMultiply shader pipeline layout",
            request_id="test_origin_01",
        )
        self.assertTrue(origin.accepted)
        self.assertEqual(origin.selected_engine, pillar5.ENGINE_ORIGIN_MCP_HTTP)
        self.assertEqual(origin.output["hit_tier"], "origin_mcp_streamable_http")

    def test_slot2_realtime_traceback_healer_across_six_compiler_and_test_families(self) -> None:
        healer = pillar5.RealtimeTracebackHealerSlot()
        samples = (
            ("pytest", "pytest RuntimeError: Event loop is closed in async fixture teardown"),
            ("mypy", "mypy error: Incompatible return value type (got dict, expected Protocol)"),
            ("tsc", "tsc error TS2322: Type 'undefined' is not assignable to type 'EnvelopeCarrier'"),
            ("cargo check", "cargo check error[E0382]: borrow of moved value: `envelope_frame`"),
            ("blender --background", "blender AttributeError: 'NoneType' object has no attribute 'scene.camera'"),
            ("SQLite store_busy", "sqlite3.OperationalError: database is locked (store_busy)"),
        )
        for idx, (expected_family, stderr_text) in enumerate(samples):
            res = healer.heal(stderr_text, request_id=f"test_heal_{idx}")
            self.assertTrue(res.accepted)
            self.assertEqual(res.selected_engine, pillar5.ENGINE_BALTOR_TRACEBACK_LSH)
            self.assertEqual(res.output["tool_family"], expected_family)
            self.assertEqual(res.output["resolved_on_turn"], 1)
            self.assertLess(int(res.output["tokens_consumed"]), 450)
            self.assertGreater(int(res.output["tokens_saved"]), 14000)

    def test_slot3_detached_worktree_swarm_coordinator_across_product_tiers(self) -> None:
        coordinator = pillar5.DetachedWorktreeSwarmCoordinatorSlot()
        workers = (
            pillar5.SwarmWorkerTask(
                worker_id="wt_alpha",
                worktree_path="wt/alpha",
                detached_head=True,
                branch_name=None,
                owned_files=("src/loop_engine/alpha.py",),
                added_lines=("ALPHA_READY = True", "def run_alpha(): return 1"),
            ),
            pillar5.SwarmWorkerTask(
                worker_id="wt_beta",
                worktree_path="wt/beta",
                detached_head=True,
                branch_name=None,
                owned_files=("src/loop_engine/beta.py",),
                added_lines=("BETA_READY = True", "def run_beta(): return 2"),
            ),
        )
        merged_lines = (
            "ALPHA_READY = True",
            "def run_alpha(): return 1",
            "BETA_READY = True",
            "def run_beta(): return 2",
        )
        for tier in pillar5.SWARM_SUPPORTED_TIERS:
            res = coordinator.coordinate_swarm(
                f"goal_{tier}",
                workers,
                merged_lines,
                request_id=f"req_swarm_{tier}",
                tier=tier,
            )
            self.assertTrue(res.accepted)
            self.assertEqual(res.selected_engine, pillar5.ENGINE_DAG_WORKTREE_SWARM)
            self.assertTrue(res.output["all_detached_head"])
            self.assertEqual(res.output["feature_branches_created"], 0)
            self.assertEqual(res.output["line_preservation_ratio"], 1.0)

    def test_known_wrong_controls_block_all_four_failure_modes(self) -> None:
        cache_slot = pillar5.Sub2msCapabilityCacheSlot()
        healer_slot = pillar5.RealtimeTracebackHealerSlot()
        swarm_slot = pillar5.DetachedWorktreeSwarmCoordinatorSlot()

        # (a) Stale release_digest on cached contract card -> blocked by Layer 3 handshake
        stale = cache_slot.resolve(
            "sqlite operationalerror database is locked",
            request_id="kw_stale_01",
            injected_stale_card_digest="sha256:stale_digest_from_yesterday",
        )
        self.assertFalse(stale.accepted)
        self.assertIsNotNone(stale.refusal)
        self.assertEqual(stale.refusal.code, "stale_release_digest_rejected")
        self.assertEqual(stale.layer_verdicts["handshake"], LAYER_REFUSED)

        # (b) Overlapping file-ownership scopes between concurrent swarm worktrees -> blocked by Layer 6 preflight
        overlapping_workers = (
            pillar5.SwarmWorkerTask(
                worker_id="wt_1",
                worktree_path="wt/1",
                detached_head=True,
                branch_name=None,
                owned_files=("tools/shared_module.py",),
                added_lines=("X = 1",),
            ),
            pillar5.SwarmWorkerTask(
                worker_id="wt_2",
                worktree_path="wt/2",
                detached_head=True,
                branch_name=None,
                owned_files=("tools/shared_module.py",),
                added_lines=("Y = 2",),
            ),
        )
        overlap = swarm_slot.coordinate_swarm(
            "goal_overlap",
            overlapping_workers,
            ("X = 1", "Y = 2"),
            request_id="kw_overlap_01",
        )
        self.assertFalse(overlap.accepted)
        self.assertIsNotNone(overlap.refusal)
        self.assertEqual(overlap.refusal.code, "overlapping_file_ownership_rejected")
        self.assertEqual(overlap.layer_verdicts["preflight"], LAYER_REFUSED)

        # (c) Silent merge line drop -> blocked by Layer 6 preflight
        valid_workers = (
            pillar5.SwarmWorkerTask(
                worker_id="wt_1",
                worktree_path="wt/1",
                detached_head=True,
                branch_name=None,
                owned_files=("tools/mod_a.py",),
                added_lines=("KEEP_LINE = 1", "DROPPED_LINE = 2"),
            ),
        )
        dropped = swarm_slot.coordinate_swarm(
            "goal_drop",
            valid_workers,
            ("KEEP_LINE = 1",),
            request_id="kw_drop_01",
        )
        self.assertFalse(dropped.accepted)
        self.assertIsNotNone(dropped.refusal)
        self.assertEqual(dropped.refusal.code, "silent_merge_line_drop_rejected")
        self.assertEqual(dropped.layer_verdicts["preflight"], LAYER_REFUSED)

        # (d) Runaway retry loop exceeding turn/token ceiling -> blocked by Layer 1 frustration_avoidance
        runaway = healer_slot.heal(
            "pytest runtimeerror event loop is closed",
            request_id="kw_runaway_01",
            simulated_retry_turns=6,
            simulated_retry_tokens=18400,
        )
        self.assertFalse(runaway.accepted)
        self.assertIsNotNone(runaway.refusal)
        self.assertEqual(runaway.refusal.code, "runaway_retry_ceiling_rejected")
        self.assertEqual(runaway.layer_verdicts["frustration_avoidance"], LAYER_REFUSED)

    def test_end_to_end_benchmark_summary_verifies_all_controls(self) -> None:
        summary = pillar5.run_pillar5_unicorn_benchmarks()
        self.assertTrue(all(summary["known_wrong_controls"].values()))
        self.assertGreater(summary["slot_1_capability_cache"]["speedup_vs_origin_x"], 50.0)
        self.assertEqual(summary["slot_2_traceback_healer"]["unassisted_avg_retry_turns"], 5.33)
        self.assertEqual(summary["slot_2_traceback_healer"]["baltor_healed_turns"], 1.0)
        self.assertGreater(summary["slot_2_traceback_healer"]["token_reduction_pct"], 97.0)


if __name__ == "__main__":
    unittest.main()
