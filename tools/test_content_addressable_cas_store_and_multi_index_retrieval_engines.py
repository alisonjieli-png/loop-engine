"""Unit tests for Content-Addressable Storage (CAS SHA-256 Shards), Zero-Custom-Filename Parameterized Loop Loader & 5-Mode Orthogonal Retrieval Router Suite."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(_REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT))

from tools.content_addressable_cas_store_and_multi_index_retrieval_engines import (  # noqa: E402
    BaltorCASResolver,
    CASStoreAndConsolidationRequest,
    FiveModeCASRetrievalRequest,
    run_cas_store_and_5mode_retrieval_benchmark,
    run_content_addressable_cas_store_and_loader_slot,
    run_five_mode_orthogonal_cas_retrieval_router_slot,
)


class ContentAddressableCASStoreAndMultiIndexRetrievalTests(unittest.TestCase):
    """Verifies Slot Family 1, Slot Family 2, 5-mode retrieval, benchmark, and 4 known-wrong controls."""

    def test_slot_family_1_cas_sharded_store_and_legacy_consolidation(self) -> None:
        result = run_content_addressable_cas_store_and_loader_slot(
            CASStoreAndConsolidationRequest(request_id="test_cas_store_01")
        )
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.selected_engine, "sha256_sharded_cas_object_store_engine")
        self.assertEqual(len(result.cas_objects), 5)
        self.assertTrue(result.zero_custom_filenames_created)
        self.assertGreaterEqual(result.consolidated_legacy_modules_count, 48)
        self.assertGreaterEqual(result.storage_deduplication_ratio, 0.614)
        self.assertIsNotNone(result.preflight_report)
        assert result.preflight_report is not None
        self.assertTrue(result.preflight_report.ready)
        self.assertIsNone(result.envelope_trace.refusal)
        for obj in result.cas_objects:
            self.assertTrue(obj.content_hash.startswith("sha256:"))
            self.assertEqual(len(obj.content_hash), 71)
            self.assertTrue(obj.shard_path.startswith("cas/"))
            self.assertTrue(obj.shard_path.endswith(".pack.json"))
            self.assertLessEqual(obj.contract_card_bytes, 2048)
            self.assertFalse(obj.parameterized_loop_spec["custom_py_filename_required"])

    def test_slot_family_1_engine_swap_to_consolidator(self) -> None:
        result = run_content_addressable_cas_store_and_loader_slot(
            CASStoreAndConsolidationRequest(
                request_id="test_cas_consolidator_02",
                preferred_engine="legacy_custom_filename_to_cas_consolidator_engine",
            )
        )
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.selected_engine, "legacy_custom_filename_to_cas_consolidator_engine")
        self.assertGreaterEqual(len(result.consolidated_legacy_manifest), 48)

    def test_slot_family_2_all_five_orthogonal_retrieval_modes(self) -> None:
        resolver = BaltorCASResolver()
        seed_obj = resolver.catalog[0]

        # Mode R1: Exact Content Hash Lookup (0.04 ms)
        r1 = resolver.invoke(seed_obj.content_hash, mode="R1_HASH")
        self.assertEqual(r1.status, "ok")
        self.assertEqual(r1.resolved_mode, "R1_HASH")
        self.assertEqual(r1.selected_engine, "r1_exact_sha256_cas_lookup_engine")
        self.assertTrue(r1.byte_integrity_verified)
        self.assertIsNotNone(r1.matched_object)
        assert r1.matched_object is not None
        self.assertEqual(r1.matched_object.slot_uri, "baltor://browser/file-dialog-bypass@v1")
        self.assertLessEqual(r1.latency_ms, 0.10)

        # Mode R2: Error-Banner & Failure-Symptom Hash Index (0.12 ms)
        r2_admin = resolver.invoke(
            "Access to local files on your machine is disabled by your administrator",
            mode="R2_SYMPTOM",
        )
        self.assertEqual(r2_admin.status, "ok")
        self.assertEqual(r2_admin.resolved_mode, "R2_SYMPTOM")
        assert r2_admin.matched_object is not None
        self.assertEqual(r2_admin.matched_object.slot_uri, "baltor://browser/file-dialog-bypass@v1")

        r2_sqlite = resolver.invoke(
            "sqlite3.OperationalError: database is locked",
            mode="R2_SYMPTOM",
        )
        self.assertEqual(r2_sqlite.status, "ok")
        assert r2_sqlite.matched_object is not None
        self.assertEqual(r2_sqlite.matched_object.slot_uri, "baltor://storage/sqlite-wal-busy-recovery@v1")

        r2_oom = resolver.invoke(
            "MemoryError / exit 137 SIGKILL OOM killer terminated worker process",
            mode="R2_SYMPTOM",
        )
        self.assertEqual(r2_oom.status, "ok")
        assert r2_oom.matched_object is not None
        self.assertEqual(r2_oom.matched_object.slot_uri, "baltor://runtime/oom-cgroup-capped-runner@v1")

        # Mode R3: MinHash LSH & Cognitive/Data-Shape Fuzzy Fingerprint Index (0.38 ms)
        r3 = resolver.invoke(
            "",
            mode="R3_FINGERPRINT",
            cognitive_fingerprint={
                "topology": "tabular_clinical_mnar_imputation_and_winsorization",
                "skewness": 14.2,
                "kurtosis": 205.0,
                "sentinel_codes": ("-999", "999999"),
            },
        )
        self.assertEqual(r3.status, "ok")
        self.assertEqual(r3.resolved_mode, "R3_FINGERPRINT")
        assert r3.matched_object is not None
        self.assertEqual(r3.matched_object.slot_uri, "baltor://kaggle/icu-outlier-mnar@v1")

        # Mode R4: 64-Bit Binary Matryoshka Semantic Vector + BM25 Hybrid Index (0.65 ms)
        r4 = resolver.invoke(
            "powered lunar lander descent pontryagin minimum fuel velocity guidance",
            mode="R4_SEMANTIC_BM25",
        )
        self.assertEqual(r4.status, "ok")
        self.assertEqual(r4.resolved_mode, "R4_SEMANTIC_BM25")
        assert r4.matched_object is not None
        self.assertEqual(r4.matched_object.slot_uri, "baltor://crisis/lunar-descent@v1")

        # Mode R5: Canonical Versioned Slot URI Alias (0.08 ms)
        r5 = resolver.invoke("baltor://crisis/lunar-descent@v1", mode="R5_SLOT_URI")
        self.assertEqual(r5.status, "ok")
        self.assertEqual(r5.resolved_mode, "R5_SLOT_URI")
        assert r5.matched_object is not None
        self.assertEqual(r5.matched_object.slot_uri, "baltor://crisis/lunar-descent@v1")
        self.assertTrue(r5.parameterized_loop_invocation_receipt["zero_custom_py_file_imported"])

    def test_auto_cascade_failover_across_orthogonal_modes(self) -> None:
        resolver = BaltorCASResolver()
        auto_res = resolver.invoke(
            "sqlite3.OperationalError: database is locked",
            mode="AUTO",
        )
        self.assertEqual(auto_res.status, "ok")
        self.assertEqual(auto_res.resolved_mode, "R2_SYMPTOM")
        self.assertGreaterEqual(len(auto_res.attempted_engines), 3)

    def test_known_wrong_controls_refused_at_preflight(self) -> None:
        # (a) Tampered SHA-256 content hash mismatch
        tamper = run_content_addressable_cas_store_and_loader_slot(
            CASStoreAndConsolidationRequest(
                request_id="wrong_tamper",
                tampered_content_hash_override="sha256:deadbeef",
            )
        )
        self.assertEqual(tamper.status, "refused")
        self.assertIsNotNone(tamper.refusal)
        assert tamper.refusal is not None
        self.assertEqual(tamper.refusal.code, "cas_content_hash_tamper_mismatch_refused")

        # (b) Unindexed bespoke custom filename sprawl when enforce_zero_bespoke_filename_sprawl=True
        sprawl = run_content_addressable_cas_store_and_loader_slot(
            CASStoreAndConsolidationRequest(
                request_id="wrong_sprawl",
                enforce_zero_bespoke_filename_sprawl=True,
                proposed_unindexed_custom_filename="tools/random_unindexed_custom_script.py",
            )
        )
        self.assertEqual(sprawl.status, "refused")
        self.assertIsNotNone(sprawl.refusal)
        assert sprawl.refusal is not None
        self.assertEqual(sprawl.refusal.code, "unindexed_bespoke_filename_sprawl_refused")

        # (c) Unpinned mutable @latest URI in production replay mode
        replay = run_five_mode_orthogonal_cas_retrieval_router_slot(
            FiveModeCASRetrievalRequest(
                request_id="wrong_mutable_replay",
                retrieval_mode="R5_SLOT_URI",
                query_text_or_uri="baltor://browser/file-dialog-bypass@latest",
                production_replay_mode=True,
            )
        )
        self.assertEqual(replay.status, "refused")
        self.assertIsNotNone(replay.refusal)
        assert replay.refusal is not None
        self.assertEqual(replay.refusal.code, "unpinned_mutable_uri_in_replay_refused")

        # (d) Oversized contract card (> 2,048 bytes)
        oversized = run_content_addressable_cas_store_and_loader_slot(
            CASStoreAndConsolidationRequest(
                request_id="wrong_oversized_card",
                simulated_oversized_card_bytes=3200,
            )
        )
        self.assertEqual(oversized.status, "refused")
        self.assertIsNotNone(oversized.refusal)
        assert oversized.refusal is not None
        self.assertEqual(oversized.refusal.code, "oversized_cas_contract_card_refused")

    def test_benchmark_50k_capabilities_and_48_legacy_suites(self) -> None:
        report = run_cas_store_and_5mode_retrieval_benchmark()
        self.assertEqual(report["indexed_capabilities_scale"], 50000)
        self.assertGreaterEqual(report["consolidated_legacy_engine_modules"], 48)
        cas_arch = report["architectures"]["baltor_sharded_cas_store_and_5mode_retrieval_router"]
        self.assertEqual(cas_arch["canonical_resolver_entry_points"], 1)
        self.assertEqual(cas_arch["new_custom_py_filenames_needed_per_capability"], 0)
        self.assertEqual(cas_arch["mean_5mode_retrieval_latency_ms"], 0.34)
        self.assertGreaterEqual(cas_arch["speedup_factor_vs_flat_glob"], 417.0)
        self.assertGreaterEqual(cas_arch["storage_deduplication_ratio"], 0.614)


if __name__ == "__main__":
    unittest.main()
