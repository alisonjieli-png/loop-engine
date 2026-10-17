"""Unit and conformance tests for the multi-domain With-Baltor vs. Without-Baltor Ollama benchmark suite."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time
import unittest

_REPO_ROOT = Path(__file__).resolve().parents[1]
for _p in (_REPO_ROOT / "src", _REPO_ROOT / "tools"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import multi_domain_ollama_benchmark as bench  # noqa: E402
from loop_engine.core.engines.envelope import PURE_EFFECT, root_frame  # noqa: E402


class MultiDomainOllamaBenchmarkTests(unittest.TestCase):
    """Verify the 7-layer ComponentEnvelope, 8 task verifiers, known-wrong controls, and offline replay."""

    def test_eight_tasks_cover_four_domains_two_per_domain(self) -> None:
        self.assertEqual(len(bench.TASKS), 8)
        counts: dict[str, int] = {}
        for task in bench.TASKS:
            dom = task["domain"]
            counts[dom] = counts.get(dom, 0) + 1
            self.assertIn(dom, bench.DOMAIN_METADATA)
            self.assertIn(task["task_id"], bench.TASK_VERIFIERS)
        self.assertEqual(
            counts,
            {
                bench.DOMAIN_KAGGLE: 2,
                bench.DOMAIN_GITHUB: 2,
                bench.DOMAIN_PUBLIC_GOOD: 2,
                bench.DOMAIN_DESIGN_MEDIA: 2,
            },
        )

    def test_nested_preturn_hook_retrieves_expected_cards_for_all_eight_tasks(self) -> None:
        frame = root_frame(bench.SLOT_ID)
        for task in bench.TASKS:
            without_info = bench.retrieve_baltor_card_for_task(frame, task, bench.ARM_WITHOUT_BALTOR)
            self.assertTrue(without_info["abstained"])
            self.assertEqual(without_info["injected_tokens"], 0)
            self.assertEqual(without_info["cards"], [])

            with_info = bench.retrieve_baltor_card_for_task(frame, task, bench.ARM_WITH_BALTOR)
            self.assertFalse(with_info["abstained"])
            self.assertGreater(with_info["injected_tokens"], 0)
            self.assertLessEqual(with_info["injected_tokens"], 360)
            self.assertEqual(len(with_info["cards"]), 1)
            self.assertEqual(with_info["cards"][0]["identity"], task["expected_card_identity"])
            self.assertEqual(with_info["nested_frame"]["depth"], 1)
            self.assertEqual(
                with_info["nested_frame"]["path"],
                [bench.SLOT_ID, bench.NESTED_PRETURN_SLOT_ID],
            )

    def test_known_wrong_controls_fail_all_eight_deterministic_verifiers(self) -> None:
        # 1. Leaky Kaggle Spaceship Titanic pipeline (modulo split + noisy CryoSleep spend)
        k01_wrong = bench.verify_k01_spaceship_titanic(
            bench.KNOWN_WRONG_CONTROLS["K-01_spaceship_titanic_group_pipeline"]
        )
        self.assertFalse(k01_wrong["passed"])
        self.assertFalse(k01_wrong["checks"]["group_leak_free"])
        self.assertFalse(k01_wrong["checks"]["cryosleep_zero_spend_invariant"])

        # 2. Leaky Kaggle Ames Housing pipeline (in-sample target encoding leakage)
        k02_wrong = bench.verify_k02_ames_housing(
            bench.KNOWN_WRONG_CONTROLS["K-02_ames_housing_rmsle_pipeline"]
        )
        self.assertFalse(k02_wrong["passed"])
        self.assertFalse(k02_wrong["checks"]["no_self_target_leakage"])

        # 3. Buggy cachetools TLRUCache (stores expired items & evicts valid LRU before expired)
        g01_wrong = bench.verify_g01_cachetools_tlru(
            bench.KNOWN_WRONG_CONTROLS["G-01_cachetools_tlru_cache"]
        )
        self.assertFalse(g01_wrong["passed"])
        self.assertFalse(g01_wrong["checks"]["out_of_order_expiration"])
        self.assertFalse(g01_wrong["checks"]["immediate_expired_insert"])
        self.assertFalse(g01_wrong["checks"]["expire_before_lru_eviction_at_maxsize"])

        # 4. Buggy python-dotenv parser (chained replace corrupts \\n and splits on '#' inside quotes)
        g02_wrong = bench.verify_g02_python_dotenv_parser(
            bench.KNOWN_WRONG_CONTROLS["G-02_python_dotenv_escape_parser"]
        )
        self.assertFalse(g02_wrong["passed"])
        self.assertFalse(g02_wrong["checks"]["single_pass_double_backslash_n"])

        # 5. Unsafe OSHA/NIOSH WBGT schedule (flat 30C cutoff, 10m rest, ignores unacclimatized halt)
        pg01_wrong = bench.verify_pg01_osha_niosh_wbgt(
            bench.KNOWN_WRONG_CONTROLS["PG-01_osha_niosh_heat_stress_wbgt"]
        )
        self.assertFalse(pg01_wrong["passed"])
        self.assertFalse(pg01_wrong["checks"]["niosh_log10_ral_al_threshold"])
        self.assertFalse(pg01_wrong["checks"]["unacclimatized_protection_invariant"])

        # 6. ADA-violating crisis shelter matcher (rejects service animals when accepts_pets=False)
        pg02_wrong = bench.verify_pg02_crisis_shelter_triage(
            bench.KNOWN_WRONG_CONTROLS["PG-02_crisis_shelter_accessible_triage"]
        )
        self.assertFalse(pg02_wrong["passed"])
        self.assertFalse(pg02_wrong["checks"]["ada_service_animal_exemption"])

        # 7. Keep-out-violating 1080x1920 vertical layout (places card at y=1650 in bottom 420px zone)
        dm01_wrong = bench.verify_dm01_vertical_motion_explainer(
            bench.KNOWN_WRONG_CONTROLS["DM-01_vertical_1080x1920_motion_explainer"]
        )
        self.assertFalse(dm01_wrong["passed"])
        self.assertFalse(dm01_wrong["checks"]["keepout_zones_respected"])
        self.assertFalse(dm01_wrong["checks"]["wcag_aaa_contrast"])
        self.assertFalse(dm01_wrong["checks"]["revision_survival_digest_invariant"])

        # 8. Non-conservative 2D collision + unbounded audio synth
        dm02_wrong = bench.verify_dm02_physics_karplus_strong(
            bench.KNOWN_WRONG_CONTROLS["DM-02_html5_physics_karplus_strong_synth"]
        )
        self.assertFalse(dm02_wrong["passed"])
        self.assertFalse(dm02_wrong["checks"]["kinetic_energy_and_momentum_conserved"])
        self.assertFalse(dm02_wrong["checks"]["audio_buffer_finite_and_bounded"])

    def test_envelope_layers_refuse_invalid_carrier_handshake_budget_and_secrets(self) -> None:
        env = bench.MultiDomainBenchmarkEnvelope()

        # Carrier refusal: wrong record_type
        r_carrier = env.run({"record_type": "wrong/v0"})
        self.assertEqual(r_carrier["record_type"], "envelope_refusal/v1")
        self.assertEqual(r_carrier["trace"]["refused_by"], "carrier")

        # Handshake refusal: live engine requested without network/model_call grants
        r_hs = env.run({
            "record_type": bench.REQUEST_RECORD_TYPE,
            "engine_id": bench.ENGINE_LIVE_OLLAMA,
            "granted_effects": ("reads_fs",),
        })
        self.assertEqual(r_hs["record_type"], "envelope_refusal/v1")
        self.assertEqual(r_hs["trace"]["refused_by"], "handshake")

        # Account refusal: max_physical_requests > 16
        r_acc = env.run({
            "record_type": bench.REQUEST_RECORD_TYPE,
            "engine_id": bench.ENGINE_SYNTHETIC_CONTROL,
            "granted_effects": (PURE_EFFECT,),
            "max_physical_requests": 17,
        })
        self.assertEqual(r_acc["record_type"], "envelope_refusal/v1")
        self.assertEqual(r_acc["trace"]["refused_by"], "account")

        # Preflight refusal: secret token in prompt_override
        r_pre = env.run({
            "record_type": bench.REQUEST_RECORD_TYPE,
            "engine_id": bench.ENGINE_SYNTHETIC_CONTROL,
            "granted_effects": (PURE_EFFECT,),
            "prompt_override": "Use Authorization: Bearer secret_token_1234567890",
        })
        self.assertEqual(r_pre["record_type"], "envelope_refusal/v1")
        self.assertEqual(r_pre["trace"]["refused_by"], "preflight")

    def test_tracking_journal_answers_duplicate_request_without_redispatch(self) -> None:
        env = bench.MultiDomainBenchmarkEnvelope()
        req = {
            "record_type": bench.REQUEST_RECORD_TYPE,
            "request_id": "req_idempotent_check",
            "engine_id": bench.ENGINE_SYNTHETIC_CONTROL,
            "granted_effects": (PURE_EFFECT,),
        }
        first = env.run(req)
        self.assertEqual(first["record_type"], bench.RESULT_RECORD_TYPE)
        self.assertFalse(first["answered_from_tracking_journal"])
        self.assertTrue(first["trace"]["engine_dispatched"])
        self.assertTrue(first["artifact"]["all_known_wrong_rejected"])

        second = env.run(req)
        self.assertEqual(second["record_type"], bench.RESULT_RECORD_TYPE)
        self.assertTrue(second["answered_from_tracking_journal"])
        self.assertFalse(second["trace"]["engine_dispatched"])

    def test_physical_request_meter_and_secret_scrubbing(self) -> None:
        meter = bench.PhysicalRequestMeter(maximum=16)
        for idx in range(16):
            seq = meter.acquire(f"task_{idx // 2}", "with_baltor", bench.PRIMARY_MODEL)
            self.assertEqual(seq, idx + 1)
        self.assertEqual(meter.remaining, 0)
        with self.assertRaises(RuntimeError):
            meter.acquire("task_overflow", "with_baltor", bench.PRIMARY_MODEL)

        fake_secret = "ollama_live_secret_key_998877665544"
        dirty_payload = {
            "header": f"Bearer {fake_secret}",
            "nested": [f"key={fake_secret}", "bsk_abcdef1234567890"],
        }
        scrubbed = bench.scrub_secrets(dirty_payload, fake_secret)
        bench.assert_no_secrets_in_record(scrubbed, fake_secret)
        with self.assertRaises(ValueError):
            bench.assert_no_secrets_in_record(dirty_payload, fake_secret)

    def test_deterministic_reference_replay_engine_verifies_saved_artifact_fast(self) -> None:
        self.assertTrue(
            bench.DEFAULT_ARTIFACT_PATH.exists(),
            f"Expected saved benchmark artifact at {bench.DEFAULT_ARTIFACT_PATH}",
        )
        env = bench.MultiDomainBenchmarkEnvelope()
        t0 = time.perf_counter()
        res = env.run({
            "record_type": bench.REQUEST_RECORD_TYPE,
            "request_id": "req_offline_replay_ci",
            "engine_id": bench.ENGINE_OFFLINE_REPLAY,
            "granted_effects": ("reads_fs",),
        })
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self.assertEqual(res["record_type"], bench.RESULT_RECORD_TYPE)
        artifact = res["artifact"]
        self.assertEqual(artifact["engine_id"], bench.ENGINE_OFFLINE_REPLAY)
        self.assertEqual(artifact["physical_requests_used"], 0)
        self.assertEqual(artifact["recorded_physical_requests"], 16)
        self.assertEqual(len(artifact["trials"]), 16)
        self.assertTrue(artifact["all_verdicts_reproduced"])
        self.assertLess(artifact["replay_elapsed_ms"], 50.0)
        self.assertLess(elapsed_ms, 200.0)

        # Ensure zero secrets in saved results.json
        raw_text = bench.DEFAULT_ARTIFACT_PATH.read_text(encoding="utf-8")
        parsed = json.loads(raw_text)
        bench.assert_no_secrets_in_record(parsed, bench.load_api_key())


if __name__ == "__main__":
    unittest.main()
