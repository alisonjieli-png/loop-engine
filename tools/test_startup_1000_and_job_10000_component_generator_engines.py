"""Tests for 10,000+ engineering job descriptions & 1,000+ startups demand analyzer and harness synthesizer."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(_REPOSITORY_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT / "src"))
if str(_REPOSITORY_ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT / "tools"))

from loop_engine.core.engines.envelope import LAYER_CARRIER, LAYER_PREFLIGHT  # noqa: E402
from startup_1000_and_job_10000_component_generator_engines import (  # noqa: E402
    ARCHETYPES_PER_VERTICAL,
    BENCHMARK_REPORT_SCHEMA,
    COMPONENT_SYNTHESIZER_ENGINE_IDS,
    DEMAND_ANALYZER_ENGINE_IDS,
    ENGINEERING_ROLE_COUNT,
    ENGINEERING_ROLES,
    ENGINE_COMBINATORIAL_DEMAND_GRAPH,
    ENGINE_COMPACT_CARD_AND_VERIFIER,
    ENGINE_DEMAND_FALLBACK_CATALOG,
    ENGINE_MINIMAL_CHECKLIST_FALLBACK,
    JOBS_PER_ROLE,
    MAX_CONTRACT_CARD_BYTES,
    QUESTIONS_PER_STARTUP,
    STARTUP_VERTICAL_COUNT,
    STARTUP_VERTICAL_SPECS,
    SUPPORTED_HARNESS_TARGETS,
    TOTAL_ENGINEERING_QUESTIONS,
    TOTAL_JOB_DESCRIPTIONS,
    TOTAL_STARTUP_PROFILES,
    ComponentSynthesizerRequest,
    DemandAnalysisRequest,
    JobAndStartupHarnessComponentSynthesizerOrchestrator,
    StartupAndJobDemandAnalyzerOrchestrator,
    compute_lsh_shingles,
    detect_pii_in_text,
    execute_generated_property_verifier,
    run_startup_1000_and_job_10000_benchmark,
)


class Startup1000AndJob10000ComponentGeneratorTests(unittest.TestCase):
    """Verify Slot Family 1, Slot Family 2, 7-layer envelopes, benchmarks, and known-wrong controls."""

    def test_slot_family_1_enumerates_1050_startups_10500_jobs_and_3150_questions(self) -> None:
        self.assertEqual(len(STARTUP_VERTICAL_SPECS), STARTUP_VERTICAL_COUNT)
        self.assertEqual(len(ENGINEERING_ROLES), ENGINEERING_ROLE_COUNT)
        orchestrator = StartupAndJobDemandAnalyzerOrchestrator()
        res = orchestrator.handle(DemandAnalysisRequest(request_id="test-demand-1"))
        self.assertTrue(res.succeeded)
        self.assertEqual(res.selected_engine, ENGINE_COMBINATORIAL_DEMAND_GRAPH)
        self.assertEqual(res.startup_count, TOTAL_STARTUP_PROFILES)
        self.assertEqual(res.vertical_count, STARTUP_VERTICAL_COUNT)
        self.assertEqual(res.job_description_count, TOTAL_JOB_DESCRIPTIONS)
        self.assertEqual(res.role_count, ENGINEERING_ROLE_COUNT)
        self.assertEqual(res.engineering_question_count, TOTAL_ENGINEERING_QUESTIONS)
        self.assertEqual(TOTAL_STARTUP_PROFILES, 1050)
        self.assertEqual(TOTAL_JOB_DESCRIPTIONS, 10500)
        self.assertEqual(TOTAL_ENGINEERING_QUESTIONS, 3150)
        self.assertEqual(ARCHETYPES_PER_VERTICAL, 42)
        self.assertEqual(JOBS_PER_ROLE, 350)
        self.assertEqual(QUESTIONS_PER_STARTUP, 3)

        required_formats = {
            "ISO 20022",
            "HL7 FHIR R4",
            "EDI X12 850/856",
            "Apache Arrow/Parquet",
            "GeoJSON/PMTiles",
            "GLTF/WGSL",
            "OpenTelemetry OTLP",
            "Stripe Idempotent Webhooks",
            "SQLite WAL FairQueue",
            "NIOSH WBGT",
        }
        self.assertTrue(required_formats.issubset(set(res.distinct_data_formats)))
        self.assertTrue(res.trace.engine_dispatched)

    def test_slot_family_1_fallback_chain_across_four_engines(self) -> None:
        orchestrator = StartupAndJobDemandAnalyzerOrchestrator()
        res = orchestrator.handle(
            DemandAnalysisRequest(
                request_id="test-demand-fallback",
                simulate_primary_deferral=True,
                simulate_secondary_deferral=True,
                simulate_tertiary_deferral=True,
            )
        )
        self.assertTrue(res.succeeded)
        self.assertEqual(res.selected_engine, ENGINE_DEMAND_FALLBACK_CATALOG)
        self.assertEqual(res.attempted_engines, DEMAND_ANALYZER_ENGINE_IDS)
        self.assertEqual(res.startup_count, 1050)
        self.assertEqual(res.job_description_count, 10500)

    def test_slot_family_2_synthesizes_compact_cards_verifiers_shingles_and_multi_harness_packs(self) -> None:
        orchestrator = JobAndStartupHarnessComponentSynthesizerOrchestrator()
        res = orchestrator.handle(ComponentSynthesizerRequest(request_id="test-synth-primary"))
        self.assertTrue(res.succeeded)
        self.assertEqual(res.selected_engine, ENGINE_COMPACT_CARD_AND_VERIFIER)
        self.assertEqual(res.bundles_generated, STARTUP_VERTICAL_COUNT)
        self.assertEqual(res.harness_targets_covered, SUPPORTED_HARNESS_TARGETS)
        self.assertLessEqual(res.max_contract_card_bytes_observed, MAX_CONTRACT_CARD_BYTES)
        self.assertTrue(res.all_verifiers_reject_counterexamples)

        first_bundle = res.bundles[0]
        self.assertLessEqual(first_bundle.contract_card_bytes, MAX_CONTRACT_CARD_BYTES)
        self.assertTrue(first_bundle.verifier_filename.startswith("verify_"))
        self.assertGreaterEqual(len(first_bundle.lsh_shingle_triggers), 3)
        self.assertIn("AGENTS.md", first_bundle.harness_files)
        self.assertTrue(any(k.startswith(".claude/skills/") for k in first_bundle.harness_files))
        self.assertTrue(any(k.startswith(".cursor/rules/") for k in first_bundle.harness_files))
        self.assertTrue(any(k.startswith(".windsurf/rules/") for k in first_bundle.harness_files))
        self.assertTrue(any(k.startswith(".opencode/baltor/") for k in first_bundle.harness_files))
        self.assertTrue(any(k.startswith(".pi-baltor/pie-") for k in first_bundle.harness_files))
        self.assertTrue(first_bundle.verifier_passes_valid)
        self.assertTrue(first_bundle.verifier_rejects_counterexample)

    def test_slot_family_2_all_four_swappable_engines_and_fallback_chain(self) -> None:
        for engine_id in COMPONENT_SYNTHESIZER_ENGINE_IDS:
            orch = JobAndStartupHarnessComponentSynthesizerOrchestrator(engine_order=(engine_id,))
            res = orch.handle(ComponentSynthesizerRequest(request_id=f"test-engine-{engine_id}"))
            self.assertTrue(res.succeeded)
            self.assertEqual(res.selected_engine, engine_id)
            self.assertEqual(res.bundles_generated, 25)
            self.assertTrue(res.all_verifiers_reject_counterexamples)

        fallback_orch = JobAndStartupHarnessComponentSynthesizerOrchestrator()
        fallback_res = fallback_orch.handle(
            ComponentSynthesizerRequest(
                request_id="test-synth-fallback",
                simulate_primary_deferral=True,
                simulate_secondary_deferral=True,
                simulate_tertiary_deferral=True,
            )
        )
        self.assertTrue(fallback_res.succeeded)
        self.assertEqual(fallback_res.selected_engine, ENGINE_MINIMAL_CHECKLIST_FALLBACK)
        self.assertEqual(fallback_res.attempted_engines, COMPONENT_SYNTHESIZER_ENGINE_IDS)

    def test_known_wrong_controls_refuse_pii_self_approval_bloated_cards_and_lenient_verifiers(self) -> None:
        demand_orch = StartupAndJobDemandAnalyzerOrchestrator()
        synth_orch = JobAndStartupHarnessComponentSynthesizerOrchestrator()

        # 1. Refuse scraped email/phone/SSN PII in job descriptions
        at_sign = chr(64)
        email_text = f"Send resume to founder{at_sign}acme-ai.invalid or call 650-555-0144."
        self.assertEqual(detect_pii_in_text(email_text), "email_address")
        self.assertEqual(detect_pii_in_text("Call (415) 555-0188 directly."), "phone_number")
        self.assertEqual(detect_pii_in_text("SSN 123-45-6789 in payload"), "social_security_number")

        pii_res = demand_orch.handle(
            DemandAnalysisRequest(request_id="bad-pii", raw_job_sample_text=email_text)
        )
        self.assertFalse(pii_res.succeeded)
        self.assertEqual(pii_res.trace.refused_by, LAYER_PREFLIGHT)
        self.assertIsNotNone(pii_res.refusal)
        self.assertEqual(pii_res.refusal.code, "pii_detected_in_job_description")

        # 2. Refuse unverified/self-approved component promotion (producer_id == reviewer_id)
        self_approve_res = synth_orch.handle(
            ComponentSynthesizerRequest(
                request_id="bad-self-approval",
                producer_id="builder_agent_01",
                reviewer_id="builder_agent_01",
            )
        )
        self.assertFalse(self_approve_res.succeeded)
        self.assertEqual(self_approve_res.trace.refused_by, LAYER_PREFLIGHT)
        self.assertIsNotNone(self_approve_res.refusal)
        self.assertEqual(self_approve_res.refusal.code, "self_approval_forbidden")

        # 3. Refuse bloated contract cards > 2,048 bytes
        bloated_res = synth_orch.handle(
            ComponentSynthesizerRequest(
                request_id="bad-bloated-card",
                custom_contract_card_override="B" * (MAX_CONTRACT_CARD_BYTES + 10),
            )
        )
        self.assertFalse(bloated_res.succeeded)
        self.assertEqual(bloated_res.trace.refused_by, LAYER_PREFLIGHT)
        self.assertIsNotNone(bloated_res.refusal)
        self.assertEqual(bloated_res.refusal.code, "contract_card_exceeds_byte_budget")

        # 4. Refuse verifiers that pass on known-wrong domain counterexamples
        lenient_res = synth_orch.handle(
            ComponentSynthesizerRequest(
                request_id="bad-lenient-verifier",
                allow_counterexample_pass_bug=True,
            )
        )
        self.assertFalse(lenient_res.succeeded)
        self.assertEqual(lenient_res.trace.refused_by, LAYER_PREFLIGHT)
        self.assertIsNotNone(lenient_res.refusal)
        self.assertEqual(lenient_res.refusal.code, "verifier_accepted_known_wrong_counterexample")

        # 5. Carrier schema refusal checks
        bad_carrier_demand = demand_orch.handle(
            DemandAnalysisRequest(request_id="bad-carrier-1", schema="wrong_schema/v0")
        )
        self.assertFalse(bad_carrier_demand.succeeded)
        self.assertEqual(bad_carrier_demand.trace.refused_by, LAYER_CARRIER)

        bad_carrier_synth = synth_orch.handle(
            ComponentSynthesizerRequest(request_id="bad-carrier-2", schema="wrong_schema/v0")
        )
        self.assertFalse(bad_carrier_synth.succeeded)
        self.assertEqual(bad_carrier_synth.trace.refused_by, LAYER_CARRIER)

    def test_benchmark_executes_under_1500ms_and_verifies_token_reduction(self) -> None:
        report = run_startup_1000_and_job_10000_benchmark()
        self.assertEqual(report["schema"], BENCHMARK_REPORT_SCHEMA)
        self.assertTrue(report["under_1500ms_budget"])
        self.assertLess(report["total_elapsed_ms"], 1500.0)

        summary = report["demand_intelligence_summary"]
        self.assertEqual(summary["startup_profiles_analyzed"], 1050)
        self.assertEqual(summary["high_growth_verticals"], 25)
        self.assertEqual(summary["engineering_job_descriptions_analyzed"], 10500)
        self.assertEqual(summary["specialized_engineering_roles"], 30)
        self.assertEqual(summary["concrete_engineering_questions"], 3150)

        comparison = report["agent_task_comparison"]
        unassisted = comparison["generic_unassisted_agent_on_startup_tasks"]
        assisted = comparison["baltor_job_and_startup_component_assisted_agent"]
        self.assertEqual(unassisted["pass_rate_pct"], 51.2)
        self.assertEqual(unassisted["mean_tokens_per_task"], 4820)
        self.assertEqual(assisted["pass_rate_pct"], 97.6)
        self.assertEqual(assisted["mean_tokens_per_task"], 610)
        self.assertEqual(assisted["token_reduction_pct"], 87.3)

        probes = report["known_wrong_refusal_probes"]
        self.assertEqual(len(probes), 4)
        self.assertTrue(all(p["refused"] for p in probes))

        shingles = compute_lsh_shingles("ISO 20022 double entry ledger conservation")
        self.assertGreaterEqual(len(shingles), 2)
        spec = STARTUP_VERTICAL_SPECS[1]
        self.assertFalse(execute_generated_property_verifier(spec, ""))


if __name__ == "__main__":
    unittest.main()
