"""Candidate staging cannot become promotion or a separate retrieval engine."""
from contextlib import closing
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from loop_engine.catalog.protocol import CatalogBatchAcknowledgment, PreconditionFailed
from loop_engine.catalog.stores.sqlite_store import SQLiteRecordStore
from tools.stage_intelligence_candidates import CandidateStageRequest, compile_candidates, review_search, stage_candidates


class CandidateStagingChecks(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / "source.md").write_text("Known source for a review-only test.")
        self.spec = {"record_type": "candidate_intelligence_specifications/v1", "specifications": [
            {"id": "review", "layer": "context", "family": "checklist", "title": "Review missing inputs",
             "tags": ["review", "inputs"], "text": "Check missing inputs before acting.", "sources": ["source.md"]}]}
        self.request = CandidateStageRequest(self.root, "test.candidates", True)

    def test_source_identity_changes_with_source_bytes(self):
        original = compile_candidates(self.spec, self.request)
        (self.root / "source.md").write_text("Changed source.")
        changed = compile_candidates(self.spec, self.request)
        self.assertNotEqual(original[0]["record_version"], changed[0]["record_version"])

    def test_search_metadata_changes_the_record_version_without_changing_body_identity(self):
        original = compile_candidates(self.spec, self.request)[0]
        changed = deepcopy(self.spec)
        changed["specifications"][0]["tags"].append("new search label")
        revised = compile_candidates(changed, self.request)[0]
        self.assertNotEqual(original["record_version"], revised["record_version"])
        self.assertEqual(original["attributes"]["content_sha256"], revised["attributes"]["content_sha256"])
        changed["specifications"][0]["layer"] = "code"
        moved = compile_candidates(changed, self.request)[0]
        self.assertNotEqual(revised["record_version"], moved["record_version"])

    def test_unknown_layers_lifecycle_injection_and_duplicate_identities_refuse(self):
        for key, value in (("layer", "fifth_layer"), ("lifecycle", "active"), ("id", "../../escape")):
            candidate = deepcopy(self.spec); candidate["specifications"][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                compile_candidates(candidate, self.request)
        candidate = deepcopy(self.spec); candidate["specifications"] *= 2
        with self.assertRaises(ValueError):
            compile_candidates(candidate, self.request)

    def test_traversal_and_symbolic_link_sources_refuse(self):
        (self.root / "linked.md").symlink_to(self.root / "source.md")
        for source in ("../outside.md", "linked.md", "/etc/passwd", ".secret"):
            candidate = deepcopy(self.spec); candidate["specifications"][0]["sources"] = [source]
            with self.subTest(source=source), self.assertRaises(ValueError):
                compile_candidates(candidate, self.request)

    def test_atomic_writes_reopen_and_duplicate_staging_refuses(self):
        records = compile_candidates(self.spec, self.request)
        database = self.root / "candidates.db"
        with closing(SQLiteRecordStore(str(database))) as store:
            result = stage_candidates(store, records, self.request)
            self.assertTrue(result.committed)
            with self.assertRaises(PreconditionFailed):
                stage_candidates(store, records, self.request)
        with closing(SQLiteRecordStore(str(database), read_only=True)) as store:
            self.assertEqual(store.get(records[0]["record_id"]), records[0])

    def test_no_authority_or_namespace_broadening(self):
        records = compile_candidates(self.spec, self.request)
        with closing(SQLiteRecordStore(str(self.root / "candidates.db"))) as store:
            with self.assertRaises(ValueError):
                stage_candidates(store, records, CandidateStageRequest(self.root, "test.candidates"))
            records[0]["namespace"] = "another.tenant"
            with self.assertRaises(ValueError):
                stage_candidates(store, records, self.request)

    def test_unknown_commit_not_a_success(self):
        records = compile_candidates(self.spec, self.request)
        with closing(SQLiteRecordStore(str(self.root / "candidates.db"))) as store:
            real = store.apply_batch
            def uncertain(batch):
                real(batch)
                return CatalogBatchAcknowledgment(batch.digest, None)
            store.apply_batch = uncertain
            with self.assertRaisesRegex(RuntimeError, "unknown"):
                stage_candidates(store, records, self.request)

    def test_normal_search_excludes_candidates_while_review_uses_canonical_query_loop(self):
        result = review_search(compile_candidates(self.spec, self.request))
        self.assertEqual(result["normal_search_hits"], 0)
        self.assertEqual(result["normal_search_excluded"], 1)
        self.assertTrue(result["probes"][0]["found_in_first_three"])
        self.assertEqual(result["probes"][0]["physical_model_calls"], 0)


if __name__ == "__main__":
    unittest.main()
