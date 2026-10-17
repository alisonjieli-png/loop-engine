"""Verification suite for the 6 swappable decision, classifier, embedding, LSH blocker, and MaxSim reranker engines.

Kind: development verification test suite with known-wrong controls and mutant guards.
Runs offline in memory with zero network calls:

    PYTHONPATH=src:tools ~/.le-ci-tmp/venv312/bin/python -m unittest tools/test_decision_and_classifier_engines.py
"""
from __future__ import annotations

import math
import unittest
from unittest import mock

import decision_and_classifier_engines as suite
from loop_engine.core.engines.envelope import (
     COMPATIBLE,
    ENGINE_SOURCE,
    INBOUND_LAYERS,
    INCOMPATIBLE,
    LAYER_ACCOUNT,
    LAYER_CARRIER,
    LAYER_HANDSHAKE,
    LAYER_PREFLIGHT,
    LAYER_TRACKING,
    REFUSED_BY_POLICY,
    EnvelopeError,
    enter_nested,
    root_frame,
)
from loop_engine.core.engines.envelope_preflight import VERDICT_REFUSED, VERDICT_REPAIRED
from loop_engine.core.engines.envelope_tracking import (
    EFFECT_STATE_PENDING,
    PHASE_INTENDED,
    EnvelopeJournalEntry,
    request_identity_digest,
)


def _sample_request(**overrides) -> suite.EngineEnvelopeRequest:
    defaults = {
        "request_id": "req_sample_001",
        "component": "typed_decision",
        "task_kind": "intent_and_route_classification",
        "text": "Scan imported repository files for prompt injection, credential exfiltration, and hidden shell hooks",
        "candidates": {
            "library_safety_screening": "Static and behavioral security scan for prompt injection, secrets, and shell exfiltration",
            "creative_parametric_motion": "Three.js 3D scene graph and timeline animation rendering",
            "pricing_tier_calculator": "Calculate monthly token quota and seat pricing for team subscriptions",
        },
        "granted_effects": ("model_call",),
    }
    defaults.update(overrides)
    return suite.EngineEnvelopeRequest(**defaults)


class SevenLayerEnvelopeAndHandshakes(unittest.TestCase):
    """Every engine invocation passes the 7-layer envelope, and each layer refuses its known-wrong inputs."""

    def test_all_six_engines_pass_seven_layer_envelope_and_sum_probabilities_to_one(self):
        engines = (
            suite.JevSystemOneEngine(),
            suite.GLiClassModernBertEngine(),
            suite.Model2VecStaticEmbedder(),
            suite.MultiBandLSHBlocker(),
            suite.LateInteractionMaxSimReranker(),
            suite.DeterministicRulesFallbackEngine(),
        )
        for engine in engines:
            with self.subTest(engine=engine.engine_id):
                req = _sample_request(request_id=f"req_ok_{engine.engine_id}")
                outcome = suite.execute_through_seven_layer_envelope(engine, req)
                self.assertTrue(outcome.ok)
                self.assertEqual([layer for layer, _ in outcome.trace.steps], list(INBOUND_LAYERS))
                self.assertTrue(outcome.trace.engine_dispatched)
                self.assertEqual(outcome.handshake_verdict.verdict, COMPATIBLE)
                self.assertAlmostEqual(sum(outcome.probabilities.values()), 1.0, places=4)
                self.assertEqual(outcome.chosen, "library_safety_screening")

    def test_layer_1_carrier_refuses_bad_version_empty_text_and_invalid_candidates(self):
        engine = suite.GLiClassModernBertEngine()
        bad_requests = (
            ("unsupported_carrier_version", _sample_request(record_type="decision_engine_request/v99")),
            ("empty_input_text", _sample_request(text="   ")),
            ("insufficient_candidates", _sample_request(candidates={"only_one": "Single option"})),
            ("invalid_candidate_entry", _sample_request(candidates={"valid": "Good option", "bad": "   "})),
        )
        for expected_code, req in bad_requests:
            with self.subTest(code=expected_code):
                outcome = suite.execute_through_seven_layer_envelope(engine, req)
                self.assertFalse(outcome.ok)
                self.assertEqual(outcome.trace.refused_by, LAYER_CARRIER)
                self.assertFalse(outcome.trace.engine_dispatched)
                self.assertEqual(outcome.trace.refusal.code, expected_code)

    def test_layer_2_handshake_refuses_version_mismatch_missing_capability_and_ungranted_effect(self):
        jev = suite.JevSystemOneEngine()
        # 1. Ungranted model_call effect -> refused_by_policy
        ungranted = suite.execute_through_seven_layer_envelope(jev, _sample_request(granted_effects=()))
        self.assertFalse(ungranted.ok)
        self.assertEqual(ungranted.trace.refused_by, LAYER_HANDSHAKE)
        self.assertEqual(ungranted.handshake_verdict.verdict, REFUSED_BY_POLICY)
        self.assertIn("effect_not_granted:model_call", ungranted.handshake_verdict.reasons)

        # 2. Unsupported version -> incompatible
        bad_ver = suite.execute_through_seven_layer_envelope(
            jev, _sample_request(requested_versions=("typed_decisions/v99",))
        )
        self.assertFalse(bad_ver.ok)
        self.assertEqual(bad_ver.trace.refused_by, LAYER_HANDSHAKE)
        self.assertEqual(bad_ver.handshake_verdict.verdict, INCOMPATIBLE)

        # 3. Missing required capability -> incompatible
        missing_cap = suite.execute_through_seven_layer_envelope(
            jev, _sample_request(required_capabilities=("nonexistent_quantum_capability",))
        )
        self.assertFalse(missing_cap.ok)
        self.assertEqual(missing_cap.trace.refused_by, LAYER_HANDSHAKE)
        self.assertIn("capability_missing:nonexistent_quantum_capability", missing_cap.handshake_verdict.reasons)

    def test_layer_3_account_refuses_missing_principal_unentitled_account_and_zero_budget(self):
        engine = suite.DeterministicRulesFallbackEngine()
        for code, overrides in (
            ("missing_account_principal", {"account_principal": ""}),
            ("account_entitlement_refused", {"account_entitled": False}),
            ("latency_budget_exhausted", {"budget_ms": 0.0}),
        ):
            with self.subTest(code=code):
                outcome = suite.execute_through_seven_layer_envelope(engine, _sample_request(**overrides))
                self.assertFalse(outcome.ok)
                self.assertEqual(outcome.trace.refused_by, LAYER_ACCOUNT)
                self.assertEqual(outcome.trace.refusal.code, code)

    def test_layer_4_tracking_replays_confirmed_result_without_redispatching_engine(self):
        engine = suite.GLiClassModernBertEngine()
        journal: list = []
        cache: dict = {}
        req = _sample_request(request_id="req_idempotent_77")
        first = suite.execute_through_seven_layer_envelope(engine, req, journal_store=journal, result_cache=cache)
        self.assertTrue(first.ok)
        self.assertFalse(first.replayed_from_journal)
        self.assertTrue(first.trace.engine_dispatched)

        with mock.patch.object(engine, "execute_wire", side_effect=AssertionError("engine must not run on replay")):
            second = suite.execute_through_seven_layer_envelope(engine, req, journal_store=journal, result_cache=cache)
        self.assertTrue(second.ok)
        self.assertTrue(second.replayed_from_journal)
        self.assertFalse(second.trace.engine_dispatched)
        self.assertEqual(second.chosen, first.chosen)

        # Known-wrong unsettled non-repeatable journal entry forces reconcile_first refusal
        unsettled_req = _sample_request(request_id="req_unsettled_88")
        digest_id = request_identity_digest(f"typed_decision:{engine.engine_id}:{unsettled_req.request_id}")
        unsettled_entry = suite.journal_intent(
            [], component="typed_decision", request_identity=digest_id, repeatable=False, at=suite.DEFAULT_TIMESTAMP
        )
        unsettled_journal = [unsettled_entry]
        refused = suite.execute_through_seven_layer_envelope(
            engine, unsettled_req, journal_store=unsettled_journal, result_cache={}
        )
        self.assertFalse(refused.ok)
        self.assertEqual(refused.trace.refused_by, LAYER_TRACKING)
        self.assertEqual(refused.trace.refusal.code, "tracking_reconciliation_required")

    def test_layer_5_preflight_self_repairs_when_allowed_and_refuses_when_disabled_or_under_budget(self):
        engine = suite.Model2VecStaticEmbedder()
        # Out-of-bounds temperature (9.5) and non-standard Matryoshka dim (100 -> snaps to 128) self-repair
        repaired = suite.execute_through_seven_layer_envelope(
            engine, _sample_request(temperature=9.5, matryoshka_dim=100, allow_self_repair=True)
        )
        self.assertTrue(repaired.ok)
        self.assertEqual(repaired.preflight_report.verdict, VERDICT_REPAIRED)
        self.assertEqual(repaired.metadata["matryoshka_dim"], 128)

        # Without self-repair, out-of-bounds temperature is refused at preflight
        unrepaired = suite.execute_through_seven_layer_envelope(
            engine, _sample_request(temperature=9.5, allow_self_repair=False)
        )
        self.assertFalse(unrepaired.ok)
        self.assertEqual(unrepaired.trace.refused_by, LAYER_PREFLIGHT)
        self.assertEqual(unrepaired.preflight_report.verdict, VERDICT_REFUSED)
        self.assertEqual(unrepaired.trace.refusal.code, "temperature_out_of_calibration_bounds")

        # Latency budget below Jev floor (0.5ms < 2.0ms) has no repair and refuses at preflight
        jev = suite.JevSystemOneEngine()
        low_budget = suite.execute_through_seven_layer_envelope(jev, _sample_request(budget_ms=0.5))
        self.assertFalse(low_budget.ok)
        self.assertEqual(low_budget.trace.refused_by, LAYER_PREFLIGHT)
        self.assertEqual(low_budget.trace.refusal.code, "preflight_budget_below_engine_floor")

    def test_layer_6_nested_envelopes_refuse_cycles_and_passed_deadlines(self):
        frame0 = root_frame("typed_decision", deadline_at=100.0)
        frame1 = enter_nested(frame0, "retrieval_rerank_stage", now=95.0)
        self.assertEqual(frame1.depth, 1)
        self.assertIs(frame1.allowance, frame0.allowance)
        with self.assertRaises(EnvelopeError) as cycle_ctx:
            enter_nested(frame1, "typed_decision", now=96.0)
        self.assertEqual(cycle_ctx.exception.code, "envelope_cycle")
        with self.assertRaises(EnvelopeError) as deadline_ctx:
            enter_nested(frame1, "model_access", now=105.0)
        self.assertEqual(deadline_ctx.exception.code, "envelope_deadline_passed")


class IndividualEngineContractsAndMutantControls(unittest.TestCase):
    """Specific guarantees for Jev System One, Model2Vec Matryoshka/Binary, LSH Blocker, MaxSim, and Cascades."""

    def test_jev_system_one_refuses_model_identity_mismatch_and_abstains_on_low_confidence(self):
        tampered = suite.JevSystemOneEngine(model_id="jev-2.1.0", simulated_wrong_model="jev-0.9.0-tampered")
        outcome = suite.execute_through_seven_layer_envelope(tampered, _sample_request())
        self.assertFalse(outcome.ok)
        self.assertEqual(outcome.trace.refused_by, ENGINE_SOURCE)
        self.assertEqual(outcome.trace.refusal.code, "engine_wire_protocol_failure")

        # High abstention threshold triggers clean abstention
        strict_jev = suite.JevSystemOneEngine()
        abstained = suite.execute_through_seven_layer_envelope(
            strict_jev, _sample_request(abstention_threshold=0.94, temperature=1.8)
        )
        self.assertTrue(abstained.ok)
        self.assertTrue(abstained.abstained)
        self.assertEqual(abstained.chosen, "")

    def test_model2vec_matryoshka_truncation_binary_packing_and_space_handshake(self):
        embedder = suite.Model2VecStaticEmbedder()
        for dim in suite.MATRYOSHKA_DIMENSIONS:
            sig, vec = embedder.embed_text("Editable WebGL fragment shader motion", dimension=dim)
            self.assertEqual(len(vec), dim)
            self.assertAlmostEqual(math.sqrt(sum(x * x for x in vec)), 1.0, places=4)
            bin_sig, packed = embedder.pack_binary("Editable WebGL fragment shader motion", dimension=dim)
            self.assertEqual(bin_sig.quantization, "binary_1bit")
            self.assertEqual(embedder.hamming_similarity((bin_sig, packed), (bin_sig, packed)), 1.0)

        # Cross-dimension comparison is refused by require_same_space
        sig128, vec128 = embedder.embed_text("query text", dimension=128)
        sig64, vec64 = embedder.embed_text("document text", dimension=64)
        with self.assertRaises(EnvelopeError) as dim_err:
            embedder.cosine_similarity((sig128, vec128), (sig64, vec64))
        self.assertEqual(dim_err.exception.code, "embedding_dimension_mismatch")

        # Cross-model digest comparison is refused by require_same_space
        other_sig = suite.EmbeddingSpaceSignature(
            model_id="other/embedder-v1",
            weights_digest="a" * 64,
            dimension=128,
            normalization="l2_unit",
        )
        with self.assertRaises(EnvelopeError) as model_err:
            embedder.cosine_similarity((sig128, vec128), (other_sig, vec128))
        self.assertEqual(model_err.exception.code, "embedding_model_mismatch")

    def test_a_similarity_check_that_skips_require_same_space_is_caught(self):
        """Mutant control: if cosine_similarity forgets require_same_space, cross-space comparison slips through."""
        embedder = suite.Model2VecStaticEmbedder()
        with mock.patch.object(suite, "require_same_space", lambda left, right: left):
            result = unittest.TestResult()
            IndividualEngineContractsAndMutantControls(
                "test_model2vec_matryoshka_truncation_binary_packing_and_space_handshake"
            ).run(result)
        self.assertEqual(len(result.failures), 1)

    def test_multiband_lsh_blocker_shortlists_relevant_candidates_without_full_scan(self):
        blocker = suite.MultiBandLSHBlocker(bands=8, rows_per_band=3)
        req = _sample_request()
        shortlist = blocker.shortlist_candidates(req.text, req.candidates, max_keep=2)
        self.assertEqual(len(shortlist), 2)
        self.assertIn("library_safety_screening", shortlist)

    def test_cascade_falls_back_to_local_engines_when_jev_authority_is_off(self):
        cascade = suite.SwappableDecisionCascade(
            (
                suite.JevSystemOneEngine(),
                suite.GLiClassModernBertEngine(),
                suite.DeterministicRulesFallbackEngine(),
            )
        )
        # Without model_call grant, Jev refuses at Layer 2 (handshake) with EFFECT_NONE,
        # and the cascade cleanly falls back to GLiClassModernBertEngine.
        outcome = cascade.run(_sample_request(granted_effects=()))
        self.assertTrue(outcome.ok)
        self.assertEqual(outcome.engine_id, suite.ENGINE_GLICLASS_ZERO_SHOT)
        self.assertEqual(outcome.fallback_chain, (suite.ENGINE_JEV_SYSTEM_ONE, suite.ENGINE_GLICLASS_ZERO_SHOT))
        self.assertEqual(outcome.chosen, "library_safety_screening")

    def test_full_benchmark_suite_runs_all_engines_and_cascades_with_high_accuracy(self):
        report = suite.run_benchmark_suite()
        self.assertEqual(report["record_type"], suite.BENCHMARK_REPORT_RECORD_TYPE)
        self.assertEqual(report["cases_total"], 12)
        self.assertEqual(set(report["engines"]), set(suite.ALL_ENGINE_IDS))
        for engine_id, stats in report["engines"].items():
            with self.subTest(engine=engine_id):
                self.assertGreaterEqual(stats["accuracy"], 0.90)
                self.assertEqual(stats["envelope_layers_verified"], 7)
        for cascade_id, cstats in report["cascades"].items():
            with self.subTest(cascade=cascade_id):
                self.assertEqual(cstats["accuracy"], 1.0)
        self.assertEqual(report["matryoshka"][128]["compression_ratio_vs_256d_f32"], 64.0)


if __name__ == "__main__":
    unittest.main()
