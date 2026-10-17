"""Unit and conformance checks for the swappable pre-turn adoption trigger (`tools/baltor_preturn_hook.py`).

Includes positive retrieval cases across exact, paraphrased, and noisy/stack-trace
prompts, plus known-wrong controls for contract violations, secret scanning,
frustration cooldown, trivial/off-topic abstention, undeclared step effects,
and automatic fallback recovery.
"""
from __future__ import annotations

import unittest

import baltor_preturn_hook as hook


class BaltorPreturnHookChecks(unittest.TestCase):
    def _request(self, **overrides):
        base = {
            "record_type": hook.REQUEST_VERSION,
            "protocol_version": hook.PROTOCOL_V1,
            "client_profile": "claude-code",
            "prompt": (
                "In our Spaceship Titanic competition pipeline, audit the train and validation "
                "splits for target leakage and shared passenger_group overlap before fitting."
            ),
            "engine_id": hook.ENGINE_T7,
            "confidence_threshold": 0.38,
            "max_injected_tokens": 200,
        }
        base.update(overrides)
        return base

    def test_layer_1_and_2_refuse_unknown_fields_secrets_and_bad_handshakes(self):
        # Known-wrong control 1: wrong record_type
        bad_record = hook.run_preturn_envelope(self._request(record_type="adoption_trigger_request/v0"))
        self.assertEqual(bad_record["record_type"], hook.REFUSAL_VERSION)
        self.assertEqual(bad_record["error"]["code"], hook.REFUSAL_INVALID_RECORD)

        # Known-wrong control 2: unknown field injected into request
        unknown_field = hook.run_preturn_envelope(self._request(tenant_override="beta"))
        self.assertEqual(unknown_field["record_type"], hook.REFUSAL_VERSION)
        self.assertEqual(unknown_field["error"]["code"], hook.REFUSAL_UNKNOWN_FIELD)

        # Known-wrong control 3: secret token in prompt is refused before engine dispatch
        secret_prompt = hook.run_preturn_envelope(
            self._request(prompt="Audit data split leakage using token bsk_live_9876543210abcdef12345")
        )
        self.assertEqual(secret_prompt["record_type"], hook.REFUSAL_VERSION)
        self.assertEqual(secret_prompt["error"]["code"], hook.REFUSAL_SECRET_DETECTED)

        # Known-wrong control 4: unsupported protocol version and client profile
        bad_proto = hook.run_preturn_envelope(self._request(protocol_version="9.9"))
        self.assertEqual(bad_proto["error"]["code"], hook.REFUSAL_UNSUPPORTED_PROTOCOL)
        bad_profile = hook.run_preturn_envelope(self._request(client_profile="unknown-ide"))
        self.assertEqual(bad_profile["error"]["code"], hook.REFUSAL_UNSUPPORTED_PROFILE)

    def test_layer_3_and_4_deduplicate_seen_cards_and_enforce_token_and_effect_bounds(self):
        first = hook.run_preturn_envelope(self._request())
        self.assertFalse(first["abstained"])
        self.assertLessEqual(first["injected_tokens"], 200)
        top_id = first["cards"][0]["identity"]
        self.assertEqual(top_id, "audit_data_splits_for_errors_and_leakage")

        # Known-wrong / deduplication control: when all matching cards were already seen in session
        all_ids = tuple(entry.identity for entry in hook.DEFAULT_CAPABILITY_CATALOGUE)
        second = hook.run_preturn_envelope(self._request(seen_identities=all_ids))
        self.assertTrue(second["abstained"])
        self.assertEqual(second["abstention_code"], hook.ABSTAIN_ALL_SEEN)
        self.assertEqual(second["injected_tokens"], 0)

        # Known-wrong control: capability requiring 'network' effect is withheld when client only grants 'reads_fs'
        webhook_req = self._request(
            prompt="Dispatch outbound HTTP webhooks with HMAC-SHA256 signatures and exponential backoff.",
            granted_step_effects=("reads_fs",),
            confidence_threshold=0.30,
        )
        withheld = hook.run_preturn_envelope(webhook_req)
        for card in withheld.get("cards", ()):
            self.assertNotEqual(card["identity"], "live_network_webhook_dispatcher")

        granted = hook.run_preturn_envelope({**webhook_req, "granted_step_effects": ("reads_fs", "network")})
        self.assertFalse(granted["abstained"])
        self.assertEqual(granted["cards"][0]["identity"], "live_network_webhook_dispatcher")

    def test_layer_5_frustration_cooldown_abstains_on_opt_out_or_ignored_turns(self):
        # Known-wrong control: explicit user frustration phrase forces 0-token abstention
        opt_out = hook.run_preturn_envelope(
            self._request(prompt="Stop suggesting Baltor and just audit the data split leakage directly.")
        )
        self.assertTrue(opt_out["abstained"])
        self.assertEqual(opt_out["abstention_code"], hook.ABSTAIN_FRUSTRATION_COOLDOWN)
        self.assertEqual(opt_out["injected_tokens"], 0)

        # Known-wrong control: 2 consecutive ignored injections triggers cooldown
        ignored = hook.run_preturn_envelope(self._request(consecutive_ignored_injections=2))
        self.assertTrue(ignored["abstained"])
        self.assertEqual(ignored["abstention_code"], hook.ABSTAIN_FRUSTRATION_COOLDOWN)
        self.assertEqual(ignored["injected_tokens"], 0)

    def test_layer_6_self_troubleshooting_strips_noise_and_abstains_on_trivial_prompts(self):
        noisy_prompt = (
            "Can you help me recreate a class in Python from scratch for our Spaceship Titanic competition?\n"
            "Traceback (most recent call last):\n"
            "  File \"/app/src/cache/lru.py\", line 84, in get\n"
            "    KeyError: 'expired_session'\n"
            "We need a time-aware LRU cache with per-entry TTL expiration and an injectable monotonic clock."
        )
        cleaned = hook.preprocess_and_troubleshoot_prompt(noisy_prompt)
        self.assertFalse(cleaned["is_trivial_or_offtopic"])
        self.assertNotIn("spaceship", cleaned["cleaned_text"])
        self.assertNotIn("titanic", cleaned["cleaned_text"])
        self.assertNotIn("traceback", cleaned["cleaned_text"])
        self.assertIn("stripped_traceback_lines", cleaned["troubleshooting_steps"])
        self.assertIn("stripped_competition_or_project_titles", cleaned["troubleshooting_steps"])

        result = hook.run_preturn_envelope(self._request(prompt=noisy_prompt))
        self.assertFalse(result["abstained"])
        self.assertEqual(result["cards"][0]["identity"], "ttl_lru_cache_with_monotonic_clock")

        # Known-wrong controls: trivial one-line edit and off-topic prompt must abstain with 0 tokens
        for trivial in (
            "Rename variable foo to bar.",
            "Fix the typo in the README header.",
            "What is 2 + 2?",
            "Give me a sourdough bread recipe.",
        ):
            res = hook.run_preturn_envelope(self._request(prompt=trivial))
            self.assertTrue(res["abstained"], trivial)
            self.assertEqual(res["abstention_code"], hook.ABSTAIN_TRIVIAL_OR_OFFTOPIC)
            self.assertEqual(res["injected_tokens"], 0)

    def test_multi_band_minhash_and_simhash_lsh_matches_paraphrased_and_typo_prompts(self):
        for bands, rows in ((8, 16), (16, 8), (32, 4)):
            index = hook.MinHashLSHIndex(bands=bands, rows=rows)
            typo_hits = index.query("audt train test data splt for targt leakge and pasenger_group overlap")
            self.assertEqual(typo_hits[0]["identity"], "audit_data_splits_for_errors_and_leakage")
            self.assertGreater(typo_hits[0]["lsh_score"], 0.35)

    def test_four_probe_relaxation_chain_and_all_nine_engines_with_fault_fallback(self):
        paraphrased = (
            "Our classifier achieves 99% accuracy because only 1% of transactions are fraud; "
            "help us trade off false alarms against missed detections and calibrate probability thresholds."
        )
        for engine_id in hook.ENGINE_IDS:
            res = hook.run_preturn_envelope(self._request(prompt=paraphrased, engine_id=engine_id))
            self.assertEqual(res["record_type"], hook.RESULT_VERSION)
            if engine_id == hook.ENGINE_T0:
                self.assertTrue(res["abstained"])
            elif engine_id in (hook.ENGINE_T6, hook.ENGINE_T7, hook.ENGINE_T8):
                self.assertFalse(res["abstained"], engine_id)
                self.assertEqual(res["cards"][0]["identity"], "choose_metrics_by_task_type_and_industry")

        # Layer 7 fault drill: simulate fault in T7 and T6, verify automatic fallback to T5 succeeds
        fallback_res = hook.run_preturn_envelope(
            self._request(
                engine_id=hook.ENGINE_T7,
                simulated_faults=(hook.ENGINE_T7, hook.ENGINE_T6),
            )
        )
        self.assertFalse(fallback_res["abstained"])
        self.assertEqual(fallback_res["selected_engine"], hook.ENGINE_T5)
        self.assertEqual(len(fallback_res["fallback_events"]), 2)
        self.assertEqual(fallback_res["cards"][0]["identity"], "audit_data_splits_for_errors_and_leakage")


if __name__ == "__main__":
    unittest.main()
