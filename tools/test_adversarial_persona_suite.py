"""Tests for tools/adversarial_persona_suite.py.

Verifies the 18-persona adversarial, strange-user, and executive emulation suite,
the four swappable defense and normalization engines with automatic fallback
chains over the 7-layer component envelope, and the eight known-wrong controls.
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import adversarial_persona_suite as suite  # noqa: E402
from loop_engine.core.engines.envelope import (  # noqa: E402
    COVERAGE_LAYERS,
    EnvelopeRefusal,
    EnvelopeTrace,
)


class AdversarialPersonaSuiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = suite.run_full_suite()
        cls.by_id = {spec.persona_id: spec for spec in suite.PERSONA_SPECS}

    def test_eighteen_personas_cover_all_three_categories_and_seven_envelope_layers(self):
        self.assertEqual(len(suite.PERSONA_SPECS), 18)
        bad_ids = [p.persona_id for p in suite.PERSONA_SPECS if p.category == suite.CATEGORY_BAD]
        strange_ids = [p.persona_id for p in suite.PERSONA_SPECS if p.category == suite.CATEGORY_STRANGE]
        exec_ids = [p.persona_id for p in suite.PERSONA_SPECS if p.category == suite.CATEGORY_EXECUTIVE]
        self.assertEqual(bad_ids, [f"P-BAD-0{i}" for i in range(1, 7)])
        self.assertEqual(strange_ids, [f"P-STRANGE-0{i}" for i in range(1, 7)])
        self.assertEqual(exec_ids, [f"P-EXEC-0{i}" for i in range(1, 7)])
        primary_layers = {p.primary_layer for p in suite.PERSONA_SPECS}
        self.assertEqual(primary_layers, set(COVERAGE_LAYERS))

    def test_exact_strict_guard_blocks_all_malicious_but_refuses_strange_users(self):
        bench = self.report["benchmarks"][suite.ENGINE_EXACT_STRICT]
        self.assertEqual(bench["bad_blocked"], 6)
        self.assertEqual(bench["malicious_block_rate"], 1.0)
        self.assertEqual(bench["strange_recovered"], 0)
        self.assertEqual(bench["strange_recovery_rate"], 0.0)
        self.assertEqual(bench["executive_passed"], 6)
        self.assertEqual(bench["false_positives"], 6)
        self.assertEqual(bench["total_passed"], 12)

    def test_normalized_tolerant_guard_recovers_five_of_six_strange_users_except_traceback(self):
        bench = self.report["benchmarks"][suite.ENGINE_NORMALIZED_TOLERANT]
        self.assertEqual(bench["bad_blocked"], 6)
        self.assertEqual(bench["strange_recovered"], 5)
        self.assertEqual(bench["executive_passed"], 6)
        self.assertEqual(bench["false_positives"], 1)
        self.assertEqual(bench["total_passed"], 17)
        by_persona = {r["persona_id"]: r for r in bench["results"]}
        self.assertFalse(by_persona["P-STRANGE-03"]["passed_expectation"])
        self.assertEqual(by_persona["P-STRANGE-03"]["code"], "noisy_traceback_or_polyglot_query")

    def test_lsh_fuzzy_traceback_normalizer_recovers_polyglot_80_line_traceback(self):
        bench = self.report["benchmarks"][suite.ENGINE_LSH_FUZZY]
        self.assertEqual(bench["bad_blocked"], 6)
        self.assertEqual(bench["strange_recovered"], 2)
        self.assertEqual(bench["executive_passed"], 6)
        self.assertEqual(bench["total_passed"], 14)
        by_persona = {r["persona_id"]: r for r in bench["results"]}
        self.assertTrue(by_persona["P-STRANGE-01"]["passed_expectation"])
        self.assertTrue(by_persona["P-STRANGE-03"]["passed_expectation"])
        self.assertEqual(by_persona["P-STRANGE-03"]["matched_component_id"], "godot_procedural_uv_shader_v1")

    def test_cascade_envelope_guard_passes_all_eighteen_personas_with_zero_false_positives(self):
        self.assertTrue(self.report["passed"])
        bench = self.report["benchmarks"][suite.ENGINE_CASCADE_ENVELOPE]
        self.assertEqual(bench["total_passed"], 18)
        self.assertEqual(bench["bad_blocked"], 6)
        self.assertEqual(bench["malicious_block_rate"], 1.0)
        self.assertEqual(bench["strange_recovered"], 6)
        self.assertEqual(bench["strange_recovery_rate"], 1.0)
        self.assertEqual(bench["executive_passed"], 6)
        self.assertEqual(bench["executive_pass_rate"], 1.0)
        self.assertEqual(bench["false_positives"], 0)
        self.assertEqual(bench["false_positive_rate"], 0.0)

    def test_cascade_fallback_chain_stops_at_first_engine_for_malicious_requests(self):
        bench = self.report["benchmarks"][suite.ENGINE_CASCADE_ENVELOPE]
        for row in bench["results"]:
            if row["category"] == suite.CATEGORY_BAD:
                self.assertEqual(
                    row["fallback_chain_used"],
                    [suite.ENGINE_EXACT_STRICT],
                    f"{row['persona_id']} must be refused immediately without falling back",
                )

    def test_cascade_fallback_chain_escalates_for_strange_requests_within_shared_allowance(self):
        bench = self.report["benchmarks"][suite.ENGINE_CASCADE_ENVELOPE]
        by_persona = {r["persona_id"]: r for r in bench["results"]}
        self.assertEqual(
            by_persona["P-STRANGE-01"]["fallback_chain_used"],
            [suite.ENGINE_EXACT_STRICT, suite.ENGINE_NORMALIZED_TOLERANT],
        )
        self.assertEqual(
            by_persona["P-STRANGE-03"]["fallback_chain_used"],
            [suite.ENGINE_EXACT_STRICT, suite.ENGINE_NORMALIZED_TOLERANT, suite.ENGINE_LSH_FUZZY],
        )
        self.assertEqual(
            by_persona["P-STRANGE-06"]["fallback_chain_used"],
            [suite.ENGINE_EXACT_STRICT, suite.ENGINE_NORMALIZED_TOLERANT],
        )
        self.assertEqual(by_persona["P-STRANGE-06"]["handshake_verdict"], "compatible_with_degradation")

    def test_every_refusal_and_trace_satisfies_envelope_record_contracts(self):
        for engine in suite.DEFENSE_ENGINES:
            for spec in suite.PERSONA_SPECS:
                res = suite.evaluate_persona(spec, engine)
                self.assertIsInstance(res.trace, EnvelopeTrace)
                trace_dict = res.trace.to_dict()
                self.assertEqual(trace_dict["record_type"], "envelope_trace/v1")
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
                f"Known-wrong control {item['control']} did not detect guard removal: {item}",
            )
            self.assertTrue(item["malicious_leaked_when_removed"])


if __name__ == "__main__":
    unittest.main()
