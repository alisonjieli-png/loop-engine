"""Tests for the 1,000-Dataset No-Unique-ID Cross-Source Entity Resolution & Jev/LLM Hybrid Matcher Engine Suite."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
for _p in (_REPOSITORY_ROOT / "src", _REPOSITORY_ROOT / "tools"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from cross_dataset_no_id_fuzzy_deterministic_llm_hybrid_matcher_engines import (  # noqa: E402
    BAND_AUTO_LINK,
    BAND_CHEAP_LLM,
    BAND_JEV_SYSTEM1,
    CANDIDATE_BLOCKER_ENGINE_IDS,
    DATASET_ARCHETYPES,
    ENGINE_DETERMINISTIC_THRESHOLD_FALLBACK,
    ENGINE_FELLEGI_SUNTER_JEV_LLM_HYBRID,
    ENGINE_SPLINK_PHONETIC_CANOPY,
    HYBRID_RESOLVER_ENGINE_IDS,
    PATTERN_ADVISOR_ENGINE_IDS,
    SLOT_CANDIDATE_BLOCKER,
    SLOT_HYBRID_ENTITY_RESOLVER,
    SLOT_PATTERN_ADVISOR,
    TWELVE_HIGH_AMBIGUITY_DOMAINS,
    american_soundex,
    canonicalize_entity_name,
    canonicalize_phone_e164,
    canonicalize_usps_address,
    damerau_levenshtein_similarity,
    double_metaphone_key,
    jaro_winkler_similarity,
    minhash_lsh_bands,
    qgram_set,
    run_1000_dataset_entity_resolution_benchmark,
    run_cross_dataset_candidate_blocker,
    run_deterministic_then_llm_pattern_advisor,
    run_hybrid_jev_llm_entity_resolver,
)
from loop_engine.core.engines.envelope import ENVELOPE_LAYERS, root_frame  # noqa: E402
from loop_engine.core.engines.envelope_preflight import VERDICT_REPAIRED  # noqa: E402


class CrossDatasetNoIdHybridMatcherTests(unittest.TestCase):
    """Verify Slot Families 1-3, 12 domains, 100k-record benchmark, and 4 known-wrong controls."""

    def test_normalization_ocr_nicknames_corporate_usps_and_phone(self) -> None:
        self.assertEqual(len(DATASET_ARCHETYPES), 7)
        ocr_norm = canonicalize_entity_name("R0bert 5mith")
        bob_norm = canonicalize_entity_name("Smith, Bob")
        self.assertEqual(ocr_norm["canonical_name"], "robert smith")
        self.assertEqual(bob_norm["canonical_name"], "robert smith")
        self.assertEqual(ocr_norm["soundex_last"], bob_norm["soundex_last"])

        peggy_norm = canonicalize_entity_name("Peggy Smith")
        margaret_norm = canonicalize_entity_name("Margaret Smith")
        self.assertEqual(peggy_norm["canonical_name"], margaret_norm["canonical_name"])

        corp_a = canonicalize_entity_name("Acme Holdings LLC")
        corp_b = canonicalize_entity_name("ACME Hldgs, Inc.")
        self.assertEqual(corp_a["canonical_name"], "acme holdings")
        self.assertEqual(corp_b["canonical_name"], "acme holdings")
        self.assertTrue(corp_a["is_corporate"])
        self.assertTrue(corp_b["is_corporate"])

        addr_a = canonicalize_usps_address("1428 North Bryn Mawr Street Apt 4B", "16678-1428")
        addr_b = canonicalize_usps_address("1428 N BRYN MAWR ST #4B", "16678")
        addr_no_suite = canonicalize_usps_address("1428 N Bryn Mawr St", "16678")
        self.assertEqual(addr_a["full_address_key"], addr_b["full_address_key"])
        self.assertEqual(addr_a["base_canopy_key"], addr_no_suite["base_canopy_key"])

        tel_a = canonicalize_phone_e164("+1 (814) 555-0192")
        tel_b = canonicalize_phone_e164("814.555.0192 ext 4")
        tel_trans = canonicalize_phone_e164("814-555-0129")
        self.assertEqual(tel_a["last7"], "5550192")
        self.assertEqual(tel_a["last7"], tel_b["last7"])
        self.assertEqual(tel_a["sorted_last7"], tel_trans["sorted_last7"])

        self.assertGreater(jaro_winkler_similarity("jnoathan", "jonathan"), 0.92)
        self.assertGreater(damerau_levenshtein_similarity("jnoathan", "jonathan"), 0.85)
        self.assertEqual(american_soundex("Smith"), "S530")
        self.assertTrue(double_metaphone_key("Jonathan"))
        self.assertEqual(len(minhash_lsh_bands(qgram_set("robert smith 16678", 3))), 16)

    def test_slot_family_1_all_four_blocker_engines_and_self_repair(self) -> None:
        records = [
            {
                "record_id": "r1", "dataset_id": "ds_1",
                "cust_nm": "Robert Smith", "street_addr": "1428 North Bryn Mawr Street Apt 4B",
                "zip": "16678-1428", "contact_tel": "+1 (814) 555-0192", "dob": "1978-04-12",
            },
            {
                "record_id": "r2", "dataset_id": "ds_2",
                "cust_nm": "Smith, Bob", "street_addr": "1428 N BRYN MAWR ST #4B",
                "zip": "16678", "contact_tel": "814.555.0192 ext 4", "dob": "1978-04-12",
            },
            {
                "record_id": "r3", "dataset_id": "ds_3",
                "cust_nm": "Jnoathan Miller", "street_addr": "900 West Market Boulevard",
                "zip": "19103", "contact_tel": "215-555-0844", "dob": "1985-11-03",
            },
            {
                "record_id": "r4", "dataset_id": "ds_4",
                "cust_nm": "Jonathan Miller", "street_addr": "900 W Market Blvd",
                "zip": "19103-1100", "contact_tel": "(215) 555-0844", "dob": "1985-11-03",
            },
        ]
        for eng in CANDIDATE_BLOCKER_ENGINE_IDS:
            out = run_cross_dataset_candidate_blocker(
                records,
                engine_id=eng,
                unnormalized_schema_headers=True,
                enable_self_repair=True,
            )
            self.assertEqual(out["status"], "ok")
            self.assertEqual(out["slot_id"], SLOT_CANDIDATE_BLOCKER)
            self.assertEqual(out["envelope_layers"], ENVELOPE_LAYERS)
            self.assertEqual(out["preflight_report"]["verdict"], VERDICT_REPAIRED)
            pair_ids = {p["pair_id"] for p in out["candidate_pairs"]}
            self.assertIn("r1::r2", pair_ids)
            self.assertIn("r3::r4", pair_ids)

    def test_slot_family_2_hybrid_resolver_bands_transitive_mincut_and_crystallizer(self) -> None:
        # Include a transitive bridge trap: A ("Robert Smith" Sr, DOB 1952) and C ("Robert Smith" Jr, DOB 1978)
        # bridged by B ("Rob Smith", no DOB, shared address/phone)
        records = [
            {
                "record_id": "sr_1", "dataset_id": "ds_10",
                "name": "Robert Smith", "address": "1428 N Bryn Mawr St",
                "postal_code": "16678", "phone": "814-555-0192", "dob": "1952-01-10", "ssn_last4": "1111",
            },
            {
                "record_id": "bridge_2", "dataset_id": "ds_20",
                "name": "Rob Smith", "address": "1428 North Bryn Mawr Street",
                "postal_code": "16678", "phone": "814-555-0192", "dob": "", "ssn_last4": "",
            },
            {
                "record_id": "jr_3", "dataset_id": "ds_30",
                "name": "Bob Smith", "address": "1428 N Bryn Mawr St",
                "postal_code": "16678", "phone": "814-555-0192", "dob": "1978-04-12", "ssn_last4": "4821",
            },
            {
                "record_id": "household_wife", "dataset_id": "ds_40",
                "name": "Alice Smith", "address": "1428 N Bryn Mawr St",
                "postal_code": "16678", "phone": "814-555-0192", "dob": "1979-08-19", "ssn_last4": "7722",
            },
            {
                "record_id": "corp_parent", "dataset_id": "ds_50",
                "name": "Acme Holdings LLC", "address": "500 Industrial Pkwy",
                "postal_code": "15222", "phone": "412-555-0900", "ein": "25-1904411",
            },
            {
                "record_id": "corp_sub", "dataset_id": "ds_60",
                "name": "Acme Logistics Div LLC", "address": "500 Industrial Parkway",
                "postal_code": "15222", "phone": "412-555-0900", "ein": "25-1904411",
            },
        ]
        parent = root_frame("cross_dataset_pipeline_root")
        s1 = run_cross_dataset_candidate_blocker(records, parent_frame=parent)
        for eng in HYBRID_RESOLVER_ENGINE_IDS:
            s2 = run_hybrid_jev_llm_entity_resolver(s1, engine_id=eng, parent_frame=parent)
            self.assertEqual(s2["status"], "ok")
            self.assertEqual(s2["slot_id"], SLOT_HYBRID_ENTITY_RESOLVER)
            self.assertEqual(s2["envelope_frame"]["depth"], 1)
            # Verify sr_1 and jr_3 are NEVER in the same final cluster despite bridge_2!
            for cluster in s2["entity_clusters"]:
                self.assertFalse("sr_1" in cluster and "jr_3" in cluster)
                self.assertFalse("household_wife" in cluster and "jr_3" in cluster)

        full_hybrid = run_hybrid_jev_llm_entity_resolver(s1, engine_id=ENGINE_FELLEGI_SUNTER_JEV_LLM_HYBRID)
        self.assertGreaterEqual(full_hybrid["transitive_bridges_split"], 1)
        self.assertGreaterEqual(full_hybrid["band_counts"][BAND_AUTO_LINK], 1)
        self.assertTrue(
            full_hybrid["band_counts"][BAND_JEV_SYSTEM1] >= 1
            or full_hybrid["band_counts"][BAND_CHEAP_LLM] >= 1
        )
        for link in full_hybrid["resolved_links"]:
            if link["resolution_band"] == BAND_CHEAP_LLM:
                self.assertLess(link["contract_card_tokens"], 180)
        self.assertGreaterEqual(len(full_hybrid["self_learning_crystallized_rules"]), 1)

        # Verify fallback deterministic engine makes 0 Jev/LLM calls
        det_only = run_hybrid_jev_llm_entity_resolver(s1, engine_id=ENGINE_DETERMINISTIC_THRESHOLD_FALLBACK)
        self.assertEqual(det_only["jev_system1_calls"], 0)
        self.assertEqual(det_only["cheap_llm_calls"], 0)

    def test_slot_family_3_all_twelve_domains_and_four_advisor_engines(self) -> None:
        self.assertEqual(len(TWELVE_HIGH_AMBIGUITY_DOMAINS), 12)
        for domain in TWELVE_HIGH_AMBIGUITY_DOMAINS:
            res = run_deterministic_then_llm_pattern_advisor(
                domain=domain,
                dataset_record_count=100_000,
                dataset_count=1_000,
            )
            self.assertEqual(res["status"], "ok")
            self.assertEqual(res["slot_id"], SLOT_PATTERN_ADVISOR)
            self.assertIn("SELECT a.id, b.id FROM dataset_a", res["recommended_architecture"]["stage1_sql_snippet"])
            self.assertGreater(res["savings_receipt"]["pair_reduction_ratio"], 0.998)
            self.assertGreater(res["savings_receipt"]["cost_savings_percent"], 99.99)

        for eng in PATTERN_ADVISOR_ENGINE_IDS:
            res = run_deterministic_then_llm_pattern_advisor(engine_id=eng)
            self.assertEqual(res["status"], "ok")
            self.assertEqual(res["engine_id"], eng)

    def test_benchmark_1000_datasets_100k_records_and_four_known_wrong_controls(self) -> None:
        bench = run_1000_dataset_entity_resolution_benchmark()
        self.assertEqual(bench["dataset_count"], 1_000)
        self.assertEqual(bench["total_records"], 100_000)
        self.assertEqual(bench["raw_quadratic_pairs"], 4_999_950_000)
        naive = bench["systems"]["naive_all_pairs_llm_without_baltor"]
        fuzzy = bench["systems"]["pure_fuzzy_threshold_only_without_jev_llm"]
        hybrid = bench["systems"]["baltor_deterministic_blocking_plus_jev_llm_hybrid"]
        self.assertEqual(naive["estimated_cost_usd"], 74_985.00)
        self.assertEqual(fuzzy["f1_pct"], 71.4)
        self.assertEqual(hybrid["f1_pct"], 99.4)
        self.assertEqual(hybrid["pair_reduction_pct"], 99.94)
        self.assertEqual(hybrid["estimated_cost_usd"], 0.18)
        self.assertEqual(hybrid["false_transitive_bridges"], 0)

        # Known-wrong control (a): unblocked O(N^2) LLM calls on >500 rows refused
        refusal_a = run_cross_dataset_candidate_blocker(
            [{"record_id": "r1", "name": "Alice"}],
            total_records_override=1_200,
            bypass_stage1_deterministic_blocker=True,
        )
        self.assertEqual(refusal_a["status"], "refused")
        self.assertEqual(refusal_a["refusal"]["code"], "unblocked_quadratic_llm_refused")

        # Known-wrong control (b): conflicting hard anti-key merge refused
        valid_s1 = run_cross_dataset_candidate_blocker(
            [{"record_id": "r1", "name": "Alice"}, {"record_id": "r2", "name": "Alice"}],
        )
        refusal_b = run_hybrid_jev_llm_entity_resolver(
            valid_s1,
            force_conflicting_hard_antikey_merge=True,
        )
        self.assertEqual(refusal_b["status"], "refused")
        self.assertEqual(refusal_b["refusal"]["code"], "conflicting_hard_antikey_merge_refused")

        # Known-wrong control (c): self-learning unverified promotion refused (worker_id == verifier_id)
        refusal_c = run_hybrid_jev_llm_entity_resolver(
            valid_s1,
            promote_learned_rules=True,
            worker_loop_id="same_loop_id",
            verifier_loop_id="same_loop_id",
        )
        self.assertEqual(refusal_c["status"], "refused")
        self.assertEqual(refusal_c["refusal"]["code"], "self_learning_unverified_promotion_refused")

        # Known-wrong control (d): raw unredacted PII egress to unapproved external endpoint refused
        refusal_d = run_cross_dataset_candidate_blocker(
            [{"record_id": "r1", "name": "Alice"}],
            allow_unredacted_external_pii_egress=True,
        )
        self.assertEqual(refusal_d["status"], "refused")
        self.assertEqual(refusal_d["refusal"]["code"], "unredacted_pii_external_egress_refused")


if __name__ == "__main__":
    unittest.main()
