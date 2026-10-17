"""Tests for Universal 6-Sector Position, Military Rank/MOS, Civil Service, Government, Startup, Enterprise & Non-Profit Grid."""
from __future__ import annotations

import ast
import json
from pathlib import Path
import sys
import unittest

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(_REPOSITORY_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT / "src"))
if str(_REPOSITORY_ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT / "tools"))

from universal_role_grid_military_civil_gov_private_nonprofit_engines import (  # noqa: E402
    ALL_CIVIL_GOVERNMENT_GRADES,
    ALL_MILITARY_GRADES,
    ALL_SIX_SECTORS,
    BALTOR_ROLE_GRID_HARNESS,
    BASELINE_UNSPECIALIZED_ASSISTANT,
    CANONICAL_24_ROLE_BENCHMARK_TASKS,
    ENGINE_COMBINATORIAL_6_SECTOR_GRID,
    ENGINE_FIVE_FILE_ROLE_PACK,
    ENGINE_MOS_GS_ONET_CROSSWALK,
    MAX_CONTRACT_CARD_BYTES,
    MILITARY_DUTY_FAMILIES,
    OCCUPATION_GRID_ENGINE_IDS,
    ROLE_SYNTHESIZER_ENGINE_IDS,
    SECTOR_CIVIL_GOV,
    SECTOR_MILITARY,
    SECTOR_NONPROFIT_NGO,
    SECTOR_PRIVATE_ENTERPRISE,
    SECTOR_PUBLIC_UTILITIES,
    SECTOR_STARTUP,
    OccupationGridQueryRequest,
    RoleComponentSynthesizerRequest,
    build_sector_duty_families,
    compute_six_sector_grid_counts,
    execute_occupation_grid_slot,
    run_universal_role_grid_benchmark,
    synthesize_role_harness_pack,
)


class UniversalRoleGridTaxonomyTests(unittest.TestCase):
    """Verify Slot Family 1 (`universal_occupation_and_rank_grid_slot`) across all 6 sectors."""

    def test_six_sector_grid_indexes_54600_positions(self) -> None:
        counts = compute_six_sector_grid_counts()
        self.assertEqual(set(counts.keys()), set(ALL_SIX_SECTORS))
        self.assertEqual(counts[SECTOR_MILITARY], 9600)
        self.assertEqual(counts[SECTOR_CIVIL_GOV], 9000)
        self.assertEqual(counts[SECTOR_STARTUP], 9000)
        self.assertEqual(counts[SECTOR_PRIVATE_ENTERPRISE], 9000)
        self.assertEqual(counts[SECTOR_PUBLIC_UTILITIES], 9000)
        self.assertEqual(counts[SECTOR_NONPROFIT_NGO], 9000)
        self.assertEqual(sum(counts.values()), 54600)
        self.assertGreaterEqual(sum(counts.values()), 54000)

    def test_all_military_ranks_and_required_mos_ratings_present(self) -> None:
        self.assertEqual(len(ALL_MILITARY_GRADES), 24)
        for grade in ("E-1", "E-6", "E-9", "W-1", "W-5", "O-1", "O-4", "O-10"):
            self.assertIn(grade, ALL_MILITARY_GRADES)
        self.assertEqual(len(MILITARY_DUTY_FAMILIES), 20)
        titles = " | ".join(d.title for d in MILITARY_DUTY_FAMILIES)
        for required in (
            "17C/17A Cyber Operations",
            "35F/14N All-Source Intelligence Analyst",
            "92A/LSSR Automated Logistics & Supply Chain",
            "25B/25D Tactical C4ISR Communications",
            "15T/2A5X1 Aviation Maintenance & Readiness",
            "12B/CEC Combat & Civil Engineering",
            "68W/HM Field Medical & Triage",
            "51C Defense Contracting & Acquisition",
            "13J Fire Direction & Ballistics",
            "MST Coast Guard Maritime Safety & AIS",
        ):
            self.assertIn(required, titles)

    def test_civil_service_startup_enterprise_public_and_nonprofit_named_roles(self) -> None:
        for grade in ("GS-1", "GS-13", "GS-15", "SES", "State-Classified", "Municipal-Classified"):
            self.assertIn(grade, ALL_CIVIL_GOVERNMENT_GRADES)

        gov_titles = " | ".join(d.title for d in build_sector_duty_families(SECTOR_CIVIL_GOV))
        for role in (
            "911/EOC Emergency Dispatch Coordinator",
            "Municipal Permitting & Zoning Examiner",
            "Public Health Epidemiologist",
            "Federal FAR/DFARS Procurement Officer",
            "Treasury/Tax Revenue Auditor",
            "Environmental & Water Quality Inspector",
            "Court Clerk & Docket Archivist",
            "Transportation & Transit Scheduler",
        ):
            self.assertIn(role, gov_titles)

        startup_titles = " | ".join(d.title for d in build_sector_duty_families(SECTOR_STARTUP))
        for role in (
            "Solo Technical Founder",
            "Founding Full-Stack Engineer",
            "Forward-Deployed AI Engineer",
            "Growth/PLG Engineer",
            "Developer Relations Lead",
            "Product Designer",
            "Head of Revenue Operations",
            "Chief of Staff",
        ):
            self.assertIn(role, startup_titles)

        ent_titles = " | ".join(d.title for d in build_sector_duty_families(SECTOR_PRIVATE_ENTERPRISE))
        for role in (
            "Principal SRE / Platform Architect",
            "CISO / SecOps Analyst",
            "Quantitative Portfolio Analyst",
            "Supply Chain & ERP Demand Planner",
            "Manufacturing Six-Sigma QA Engineer",
            "Actuarial Risk Modeler",
            "Corporate Controller / FP&A",
            "Clinical Trial Biostatistician",
        ):
            self.assertIn(role, ent_titles)

        pub_titles = " | ".join(d.title for d in build_sector_duty_families(SECTOR_PUBLIC_UTILITIES))
        for role in (
            "SCADA Grid Reliability Operator",
            "Public School/University Curriculum & Assessment Lead",
            "Public Defender Casework Analyst",
            "National Lab Research Scientist",
        ):
            self.assertIn(role, pub_titles)

        ngo_titles = " | ".join(d.title for d in build_sector_duty_families(SECTOR_NONPROFIT_NGO))
        for role in (
            "Humanitarian Disaster Logistics Coordinator",
            "Foundation Grant & Impact Evaluator",
            "Food Bank Cold-Chain Optimizer",
            "Conservation GIS Analyst",
        ):
            self.assertIn(role, ngo_titles)

    def test_occupation_grid_slot_execution_and_fallback(self) -> None:
        resp = execute_occupation_grid_slot(
            OccupationGridQueryRequest(
                request_id="test-grid-mil",
                account_id="acct_test",
                sector_filter=SECTOR_MILITARY,
                grade_filter="E-6",
                duty_query="92A",
            )
        )
        self.assertTrue(resp.succeeded)
        self.assertEqual(resp.selected_engine_id, ENGINE_COMBINATORIAL_6_SECTOR_GRID)
        self.assertEqual(resp.total_indexed_positions, 54600)
        self.assertEqual(len(resp.matched_profiles), 1)
        self.assertIn("E-6 92A/LSSR", resp.matched_profiles[0].title)
        self.assertTrue(resp.envelope_trace.engine_dispatched)

        fallback_resp = execute_occupation_grid_slot(
            OccupationGridQueryRequest(
                request_id="test-grid-defer",
                account_id="acct_test",
                simulate_primary_deferral=True,
            )
        )
        self.assertTrue(fallback_resp.succeeded)
        self.assertEqual(fallback_resp.selected_engine_id, ENGINE_MOS_GS_ONET_CROSSWALK)
        self.assertEqual(
            fallback_resp.attempted_engines,
            (ENGINE_COMBINATORIAL_6_SECTOR_GRID, ENGINE_MOS_GS_ONET_CROSSWALK),
        )


class RoleHarnessComponentSynthesizerTests(unittest.TestCase):
    """Verify Slot Family 2 (`role_to_harness_component_synthesizer_slot`) 5-file bundle synthesis."""

    def test_synthesize_five_file_packs_for_flagship_positions(self) -> None:
        queries = (
            (SECTOR_MILITARY, "E-6", "92A/LSSR"),
            (SECTOR_CIVIL_GOV, "GS-13", "GOV-EPI"),
            (SECTOR_STARTUP, "Pre-Seed-Founding", "STU-FOU"),
            (SECTOR_NONPROFIT_NGO, "NGO-Field-Band-8", "NGO-CLD"),
        )
        for sector, grade, duty_code in queries:
            resp = synthesize_role_harness_pack(
                RoleComponentSynthesizerRequest(
                    request_id=f"test-pack-{duty_code}",
                    account_id="acct_test",
                    sector=sector,
                    grade_or_rank=grade,
                    duty_code=duty_code,
                )
            )
            self.assertTrue(resp.succeeded)
            self.assertIsNotNone(resp.pack)
            assert resp.pack is not None
            pack = resp.pack
            self.assertEqual(
                set(pack.files.keys()),
                {"baltor_contract_card.json", "AGENTS.md", "RULES.md", "MEMORY.md", "verifier.py"},
            )
            self.assertLess(pack.contract_card_bytes, MAX_CONTRACT_CARD_BYTES)
            card_obj = json.loads(pack.files["baltor_contract_card.json"])
            self.assertEqual(card_obj["sector"], sector)
            self.assertEqual(card_obj["grade_or_rank"], grade)

            # Parse and execute verifier.py deterministically
            verifier_src = pack.files["verifier.py"]
            ast.parse(verifier_src)
            ns: dict[str, object] = {}
            exec(compile(verifier_src, "<verifier>", "exec"), ns)  # noqa: S102
            verify_fn = ns["verify_role_invariant"]
            ok, msg = verify_fn({"classification_boundary_respected": True, "chain_of_command_signed": True, "observed_error": 0.0})  # type: ignore[operator]
            self.assertTrue(ok)
            self.assertEqual(msg, "verified")
            bad_ok, bad_msg = verify_fn({"classification_boundary_respected": False})  # type: ignore[operator]
            self.assertFalse(bad_ok)
            self.assertEqual(bad_msg, "classification_or_pii_boundary_violation")

    def test_all_synthesizer_engines_and_deferral_recovery(self) -> None:
        self.assertEqual(len(OCCUPATION_GRID_ENGINE_IDS), 4)
        self.assertEqual(len(ROLE_SYNTHESIZER_ENGINE_IDS), 4)
        for engine_id in ROLE_SYNTHESIZER_ENGINE_IDS:
            resp = synthesize_role_harness_pack(
                RoleComponentSynthesizerRequest(
                    request_id=f"test-eng-{engine_id}",
                    account_id="acct_test",
                    sector=SECTOR_PRIVATE_ENTERPRISE,
                    grade_or_rank="Enterprise-Band-L12",
                    duty_code="ENT-SRE",
                    preferred_engine_id=engine_id,
                )
            )
            self.assertTrue(resp.succeeded)
            self.assertEqual(resp.selected_engine_id, engine_id)

        defer_resp = synthesize_role_harness_pack(
            RoleComponentSynthesizerRequest(
                request_id="test-synth-defer",
                account_id="acct_test",
                sector=SECTOR_PUBLIC_UTILITIES,
                grade_or_rank="Public-Infra-Step-12",
                duty_code="PUB-SCA",
                preferred_engine_id=ENGINE_FIVE_FILE_ROLE_PACK,
                simulate_primary_deferral=True,
            )
        )
        self.assertTrue(defer_resp.succeeded)
        self.assertEqual(len(defer_resp.attempted_engines), 2)


class BenchmarkAndKnownWrongControlTests(unittest.TestCase):
    """Verify the 24-task 6-sector benchmark and all 4 known-wrong refusal controls."""

    def test_24_task_benchmark_and_known_wrong_controls(self) -> None:
        self.assertEqual(len(CANONICAL_24_ROLE_BENCHMARK_TASKS), 24)
        report = run_universal_role_grid_benchmark()
        self.assertEqual(report["total_indexed_positions"], 54600)

        comp = report["benchmark_comparison"]
        baseline = comp[BASELINE_UNSPECIALIZED_ASSISTANT]
        baltor = comp[BALTOR_ROLE_GRID_HARNESS]

        self.assertEqual(baseline["tasks_evaluated"], 24)
        self.assertEqual(baltor["tasks_evaluated"], 24)
        self.assertEqual(baltor["pass_rate_pct"], 100.0)
        self.assertEqual(baltor["compliance_violation_rate_pct"], 0.0)
        self.assertGreater(baltor["pass_rate_pct"], baseline["pass_rate_pct"])
        self.assertLess(baltor["compliance_violation_rate_pct"], baseline["compliance_violation_rate_pct"])
        self.assertGreater(baltor["time_saved_pct"], 80.0)

        controls = {c["control_id"]: c for c in report["known_wrong_controls"]}
        self.assertEqual(len(controls), 4)
        for cid, ctrl in controls.items():
            self.assertTrue(ctrl["refused"], f"Control {cid} must be refused")
            self.assertEqual(ctrl["refused_by_layer"], "preflight")
            self.assertEqual(ctrl["refusal_code"], cid)

    def test_carrier_and_handshake_refusals(self) -> None:
        bad_carrier = execute_occupation_grid_slot(
            OccupationGridQueryRequest(
                request_id="test-bad-carrier",
                account_id="acct_test",
                schema="invalid_schema/v0",
            )
        )
        self.assertFalse(bad_carrier.succeeded)
        self.assertEqual(bad_carrier.envelope_trace.refused_by, "carrier")

        bad_handshake = execute_occupation_grid_slot(
            OccupationGridQueryRequest(
                request_id="test-bad-sector",
                account_id="acct_test",
                sector_filter="nonexistent_sector",
            )
        )
        self.assertFalse(bad_handshake.succeeded)
        self.assertEqual(bad_handshake.envelope_trace.refused_by, "handshake")


if __name__ == "__main__":
    unittest.main()
