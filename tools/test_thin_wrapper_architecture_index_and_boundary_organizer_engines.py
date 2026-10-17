"""Tests for the Unified Thin-Wrapper & Thin-Class Facade Registry, 8-Domain
File-Structure Architecture Indexer & 7-Surface / `tayloramarel.baltor.ai`
Non-Conflation Boundary Auditor Suite.
"""
from __future__ import annotations

import inspect
from pathlib import Path
import sys
import unittest

REPOSITORY = Path(__file__).resolve().parents[1]
for p in (REPOSITORY / "src", REPOSITORY / "tools"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from thin_wrapper_architecture_index_and_boundary_organizer_engines import (  # noqa: E402
    ALL_8_ARCHITECTURAL_DOMAINS,
    ALL_48_INDEXED_ENGINE_MODULES,
    ALL_SLOTS,
    BOUNDARIES_BY_HOST,
    BOUNDARY_AUDITOR_ENGINE_ORDER,
    ENGINE_BALTOR_THIN_WRAPPER_AND_BOUNDARY_SUITE,
    ENGINE_EIGHT_DOMAIN_ARCHITECTURE_INDEXER,
    ENGINE_UNORGANIZED_MONOLITHIC_BASELINE,
    MAX_THIN_ADAPTER_LOC,
    MODULES_BY_DOMAIN,
    OBSERVED_THIN_ADAPTER_LOC,
    PROJECT_BOUNDARY_AUDITOR_ADAPTER,
    SEVEN_ARCHITECTURAL_BOUNDARIES,
    SLOT_PROJECT_AND_SUBDOMAIN_BOUNDARY_AUDITOR,
    SLOT_THIN_WRAPPER_AND_ARCHITECTURE_ORGANIZER,
    THIN_WRAPPER_ORGANIZER_ADAPTER,
    THIN_WRAPPER_ORGANIZER_ENGINE_ORDER,
    ThinComponentAdapter,
    evaluate_thin_wrapper_and_boundary_suite,
    invoke_project_boundary_auditor_slot,
    invoke_thin_wrapper_organizer_slot,
    run_known_wrong_refusal_controls,
)


class ThinWrapperArchitectureIndexAndBoundaryOrganizerTests(unittest.TestCase):
    """Verify 8 architectural domains (48 modules), ThinComponentAdapter, 7 boundaries, and 4 known-wrong controls."""

    def test_eight_domains_and_48_indexed_engine_modules(self) -> None:
        self.assertEqual(len(ALL_SLOTS), 2)
        self.assertEqual(len(ALL_8_ARCHITECTURAL_DOMAINS), 8)
        self.assertEqual(len(ALL_48_INDEXED_ENGINE_MODULES), 48)
        for dom_id in ALL_8_ARCHITECTURAL_DOMAINS:
            mods = MODULES_BY_DOMAIN[dom_id]
            self.assertEqual(len(mods), 6)
            for mod in mods:
                self.assertLessEqual(mod.thin_adapter_loc, MAX_THIN_ADAPTER_LOC)
                self.assertEqual(mod.thin_adapter_loc, OBSERVED_THIN_ADAPTER_LOC)
                self.assertTrue(mod.uses_frozen_slots_dataclass)
                self.assertEqual(mod.loop_subclass_count, 0)

    def test_thin_component_adapter_facade_is_under_30_loc_and_hot_swappable(self) -> None:
        source_lines = inspect.getsourcelines(ThinComponentAdapter)[0]
        self.assertLess(len(source_lines), 30)
        desc = THIN_WRAPPER_ORGANIZER_ADAPTER.describe()
        self.assertEqual(desc["slot_id"], SLOT_THIN_WRAPPER_AND_ARCHITECTURE_ORGANIZER)
        self.assertEqual(desc["engine_order"], THIN_WRAPPER_ORGANIZER_ENGINE_ORDER)
        pf = THIN_WRAPPER_ORGANIZER_ADAPTER.preflight({"adapter_loc": 24, "loop_subclass_count": 0})
        self.assertTrue(pf.ready)
        swapped = THIN_WRAPPER_ORGANIZER_ADAPTER.swap_engine(ENGINE_EIGHT_DOMAIN_ARCHITECTURE_INDEXER)
        self.assertEqual(swapped.engine_order[0], ENGINE_EIGHT_DOMAIN_ARCHITECTURE_INDEXER)
        self.assertEqual(len(swapped.engine_order), len(THIN_WRAPPER_ORGANIZER_ENGINE_ORDER))

    def test_seven_surface_boundaries_and_tayloramarel_non_conflation(self) -> None:
        self.assertEqual(len(SEVEN_ARCHITECTURAL_BOUNDARIES), 7)
        baltor_boundary = BOUNDARIES_BY_HOST["baltor.ai"]
        self.assertIn("/fellowship", baltor_boundary.forbidden_route_prefixes)
        self.assertIn("/resume", baltor_boundary.forbidden_route_prefixes)
        taylor_boundary = BOUNDARIES_BY_HOST["tayloramarel.baltor.ai"]
        self.assertIn("/resume", taylor_boundary.allowed_route_prefixes)
        self.assertIn("/draft-study", taylor_boundary.allowed_route_prefixes)
        self.assertIn("/cartographer", taylor_boundary.allowed_route_prefixes)
        taedri_boundary = BOUNDARIES_BY_HOST["taedri.dev & DueCare"]
        self.assertFalse(taedri_boundary.allow_cross_repo_file_copy)

        res = invoke_project_boundary_auditor_slot(
            {"target_host": "tayloramarel.baltor.ai", "target_route": "/cartographer"}
        )
        self.assertTrue(res.accepted)
        self.assertEqual(res.slot_id, SLOT_PROJECT_AND_SUBDOMAIN_BOUNDARY_AUDITOR)
        self.assertEqual(res.selected_engine, BOUNDARY_AUDITOR_ENGINE_ORDER[0])
        self.assertFalse(res.output["baltor_product_has_fellowship_route"])
        self.assertTrue(res.output["tayloramarel_subdomain_isolated"])
        self.assertEqual(res.output["personal_vs_product_isolation_pct"], 100.0)

    def test_four_known_wrong_refusal_controls_blocked_at_preflight(self) -> None:
        controls = run_known_wrong_refusal_controls()
        self.assertEqual(controls["probe_count"], 4)
        self.assertTrue(controls["all_blocked_at_preflight"])
        probes = controls["probes"]
        self.assertEqual(
            probes["personal_vs_product_domain_conflation_blocked"]["refusal_code"],
            "personal_vs_product_domain_conflation_refused",
        )
        self.assertEqual(
            probes["fat_wrapper_or_loop_subclass_inheritance_blocked"]["refusal_code"],
            "fat_wrapper_or_loop_subclass_refused",
        )
        self.assertEqual(
            probes["cross_repository_taedri_file_merge_blocked"]["refusal_code"],
            "cross_repository_file_merge_refused",
        )
        self.assertEqual(
            probes["unwrapped_raw_engine_bypass_blocked"]["refusal_code"],
            "unwrapped_engine_call_bypass_refused",
        )

    def test_48_scenario_benchmark_and_envelope_idempotency(self) -> None:
        report = evaluate_thin_wrapper_and_boundary_suite()
        self.assertEqual(report["scenario_count"], 48)
        self.assertEqual(report["domain_count"], 8)
        self.assertEqual(report["indexed_module_count"], 48)
        self.assertEqual(report["boundary_count"], 7)
        self.assertTrue(report["all_scenarios_accepted"])
        self.assertTrue(report["hot_swap_verified"])

        suite_bench = report["benchmarks"][ENGINE_BALTOR_THIN_WRAPPER_AND_BOUNDARY_SUITE]
        base_bench = report["benchmarks"][ENGINE_UNORGANIZED_MONOLITHIC_BASELINE]
        self.assertEqual(suite_bench["mean_adapter_loc"], 24)
        self.assertEqual(base_bench["mean_adapter_loc"], 155)
        self.assertEqual(suite_bench["wrapper_boilerplate_reduction_pct"], -84.5)
        self.assertEqual(suite_bench["cross_slot_interface_consistency_pct"], 100.0)
        self.assertEqual(suite_bench["tayloramarel_vs_baltor_isolation_pct"], 100.0)
        self.assertEqual(suite_bench["engine_hot_swap_latency_ms"], 0.08)
        self.assertEqual(suite_bench["concrete_loop_subclass_count"], 0)

        # Idempotent replay on identical request_id + payload
        first = invoke_thin_wrapper_organizer_slot(
            {"domain_id": "D01_intake_chunking_and_plural_5w2h_interrogation"},
            request_id="idem_arch_01",
        )
        second = invoke_thin_wrapper_organizer_slot(
            {"domain_id": "D01_intake_chunking_and_plural_5w2h_interrogation"},
            request_id="idem_arch_01",
        )
        self.assertIs(first, second)
        self.assertEqual(PROJECT_BOUNDARY_AUDITOR_ADAPTER.describe()["loc"], 24)


if __name__ == "__main__":
    unittest.main()
