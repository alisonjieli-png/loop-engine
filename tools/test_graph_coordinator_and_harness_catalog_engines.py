"""Tests for tools/graph_coordinator_and_harness_catalog_engines.py.

Verifies the One Loop runtime invariant (LE-RUNTIME-001), the four swappable
Loop graph communication coordinator engines with 7-layer cascade failover,
the 108-cell (9 harnesses by 12 component families) harness component catalog
matrix, the 12 end-to-end use-case executions, and the eight known-wrong controls.
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import graph_coordinator_and_harness_catalog_engines as suite  # noqa: E402
from loop_engine.core.engines.envelope import (  # noqa: E402
    COVERAGE_LAYERS,
    EnvelopeRefusal,
    EnvelopeTrace,
)


class GraphCoordinatorAndHarnessCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = suite.run_full_audit()

    def test_full_audit_passes_all_benchmarks_cells_use_cases_and_controls(self):
        self.assertTrue(self.report["passed"])
        self.assertEqual(self.report["envelope_layers"], list(COVERAGE_LAYERS))

    def test_four_coordinator_engines_and_cascade_failover_across_workloads(self):
        benches = self.report["coordinator_benchmarks"]
        self.assertEqual(benches[suite.COORD_TOPOLOGICAL_WAVE]["workloads_completed"], 1)
        self.assertEqual(benches[suite.COORD_PRIORITY_DEADLINE]["workloads_completed"], 2)
        self.assertEqual(benches[suite.COORD_ACTOR_MAILBOX]["workloads_completed"], 3)
        self.assertEqual(benches[suite.COORD_SEQUENTIAL_FALLBACK]["workloads_completed"], 4)
        cascade = benches[suite.COORD_CASCADE_ENVELOPE]
        self.assertEqual(cascade["workloads_completed"], 4)
        self.assertEqual(cascade["completion_rate"], 1.0)

        runs_by_id = {r["workload_id"]: r for r in cascade["runs"]}
        self.assertEqual(
            runs_by_id["W-DAG-01"]["fallback_chain_used"],
            [suite.COORD_TOPOLOGICAL_WAVE],
        )
        self.assertEqual(
            runs_by_id["W-WAVE-02"]["fallback_chain_used"],
            [suite.COORD_TOPOLOGICAL_WAVE, suite.COORD_PRIORITY_DEADLINE],
        )
        self.assertEqual(
            runs_by_id["W-DEADLINE-03"]["fallback_chain_used"],
            [
                suite.COORD_TOPOLOGICAL_WAVE,
                suite.COORD_PRIORITY_DEADLINE,
                suite.COORD_ACTOR_MAILBOX,
            ],
        )
        self.assertEqual(
            runs_by_id["W-MAILBOX-04"]["fallback_chain_used"],
            [
                suite.COORD_TOPOLOGICAL_WAVE,
                suite.COORD_PRIORITY_DEADLINE,
                suite.COORD_ACTOR_MAILBOX,
                suite.COORD_SEQUENTIAL_FALLBACK,
            ],
        )

    def test_all_108_harness_catalog_cells_and_mcp_transport_keys_are_verified(self):
        matrix = self.report["catalog_matrix"]
        self.assertEqual(matrix["harness_count"], 9)
        self.assertEqual(matrix["family_count"], 12)
        self.assertEqual(matrix["total_cells"], 108)
        self.assertEqual(matrix["verified_cells"], 108)

        expected_mcp_keys = {
            "windsurf": "serverUrl",
            "cline": "streamableHttp",
            "roo_code": "streamable-http",
            "claude_code": "http",
            "opencode": "remote",
            "codex": "http_transport",
            "cursor": "url",
            "pi": "mcp_endpoint",
            "goose_chatgpt_app": "sse_or_streamable_http",
        }
        for harness_id, expected_key in expected_mcp_keys.items():
            cell = suite.verify_harness_catalog_cell(harness_id, suite.FAM_MCP_CONFIGS)
            self.assertTrue(cell.verified)
            self.assertEqual(cell.mcp_transport_key, expected_key)
            self.assertFalse(cell.source_loaded_on_discovery)
            self.assertLess(cell.card_bytes, cell.source_bytes)

    def test_twelve_end_to_end_use_cases_verify_card_first_discovery_and_execution(self):
        use_cases = self.report["catalog_matrix"]["use_cases"]
        self.assertEqual(len(use_cases), 12)
        for uc in use_cases:
            self.assertTrue(uc["verified"], f"Use case failed: {uc}")
            self.assertGreater(uc["discovery_byte_savings_ratio"], 0.85)
            self.assertIn(uc["loop_role"], suite.ADMITTED_LOOP_ROLES)
            self.assertIn(uc["run_mode"], suite.ADMITTED_RUN_MODES)

    def test_every_trace_and_refusal_validates_against_envelope_contracts(self):
        workloads = suite.build_reference_workloads()
        for eng in suite.ALL_COORDINATOR_MODES:
            for wl in workloads:
                res = suite.execute_graph_workload(wl, eng)
                self.assertIsInstance(res.trace, EnvelopeTrace)
                self.assertEqual(res.trace.to_dict()["record_type"], "envelope_trace/v1")
                if res.refusal is not None:
                    self.assertIsInstance(res.refusal, EnvelopeRefusal)
                    rebuilt = EnvelopeRefusal.from_dict(res.refusal.to_dict())
                    self.assertEqual(rebuilt, res.refusal)

    def test_all_eight_known_wrong_controls_detect_removed_guards(self):
        controls = self.report["known_wrong_controls"]
        self.assertEqual(len(controls), 8)
        for item in controls:
            self.assertTrue(
                item["known_wrong_detected"],
                f"Known-wrong control {item['control']} failed: {item}",
            )
            self.assertTrue(item["leaked_when_removed"])


if __name__ == "__main__":
    unittest.main()
