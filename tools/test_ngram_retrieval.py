"""Judged document-pair similarity checks existence and scope before identity.

The module's own contract checks are collected only on the parked checkpoint
branch (forbidden_paths.json suite_collection_exceptions), so this owning
check runs on main.
"""
import unittest

from loop_engine.core.ngram_retrieval import (
    DocumentSimilarityRequest, NgramDocument, NgramIndex, NgramRetrievalError)


class DocumentSimilarity(unittest.TestCase):
    def setUp(self):
        self.index = NgramIndex((
            NgramDocument("a.one", "normalize customer addresses", "tenant:a"),
            NgramDocument("a.two", "normalize customer address lines", "tenant:a"),
            NgramDocument("b.one", "validate schema records", "tenant:b")))

    def similarity(self, left, right, scopes=None):
        return self.index.document_similarity(DocumentSimilarityRequest(left, right, allowed_scopes=scopes))

    def test_identity_is_refused_for_unknown_or_out_of_scope_documents(self):
        # Known-wrong control: equal IDs returned 1.0 before either check, so a
        # document that does not exist, one outside the caller's scopes and an
        # invalid scope list all scored as a perfect match.
        for left, right, scopes in (("missing", "missing", None), ("b.one", "b.one", ("tenant:a",)),
                                    ("a.one", "a.one", ("",)), ("a.one", "a.one", ())):
            with self.subTest(left=left, scopes=scopes):
                with self.assertRaises(NgramRetrievalError):
                    self.similarity(left, right, scopes)

    def test_identity_in_scope_is_a_perfect_match_and_pairs_keep_their_checks(self):
        self.assertEqual(self.similarity("a.one", "a.one", ("tenant:a",)), 1.0)
        self.assertEqual(self.similarity("b.one", "b.one"), 1.0)
        self.assertLess(self.similarity("a.one", "a.two", ("tenant:a",)), 1.0)
        for left, right, scopes in (("a.one", "missing", None), ("a.one", "b.one", ("tenant:a",))):
            with self.subTest(left=left, right=right):
                with self.assertRaises(NgramRetrievalError):
                    self.similarity(left, right, scopes)


if __name__ == "__main__":
    unittest.main()
