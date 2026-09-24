import unittest
import json
import sys
import io
from tools.build_permission_scoped_lexical_index import run_tool

class TestLexicalIndex(unittest.TestCase):
    def run_with_input(self, input_dict):
        input_str = json.dumps(input_dict)
        sys.stdin = io.StringIO(input_str)
        sys.stdout = io.StringIO()
        run_tool()
        output = sys.stdout.getvalue()
        return json.loads(output)

    def test_build_mode(self):
        req = {
            "mode": "build",
            "documents": [
                {"id": "1", "text": "hello", "tenant_id": "a", "source_hash": "h1"}
            ]
        }
        res = self.run_with_input(req)
        self.assertEqual(res["status"], "success")
        self.assertIn("corpus_digest", res["data"])

    def test_query_ranking(self):
        # doc_1: 2 distinct (apple, banana), 3 total
        # doc_2: 1 distinct (apple), 2 total
        # doc_3: 1 distinct (apple), 1 total
        req = {
            "mode": "query",
            "tenant_id": "t1",
            "query_terms": ["apple", "banana"],
            "documents": [
                {"id": "doc_1", "text": "apple banana apple", "tenant_id": "t1", "source_hash": "h1"},
                {"id": "doc_2", "text": "apple apple", "tenant_id": "t1", "source_hash": "h2"},
                {"id": "doc_3", "text": "apple", "tenant_id": "t1", "source_hash": "h3"},
                {"id": "doc_4", "text": "apple banana", "tenant_id": "t1", "source_hash": "h4"}
            ]
        }
        res = self.run_with_input(req)
        self.assertEqual(res["status"], "success")
        ids = [r["id"] for r in res["data"]["results"]]
        # doc_1 (2 dist, 3 tot) > doc_4 (2 dist, 2 tot) > doc_2 (1 dist, 2 tot) > doc_3 (1 dist, 1 tot)
        self.assertEqual(ids, ["doc_1", "doc_4", "doc_2", "doc_3"])

    def test_tenant_filtering(self):
        req = {
            "mode": "query",
            "tenant_id": "t1",
            "query_terms": ["apple"],
            "documents": [
                {"id": "d1", "text": "apple", "tenant_id": "t1", "source_hash": "h1"},
                {"id": "d2", "text": "apple", "tenant_id": "t2", "source_hash": "h2"}
            ]
        }
        res = self.run_with_input(req)
        self.assertEqual(len(res["data"]["results"]), 1)
        self.assertEqual(res["data"]["results"][0]["id"], "d1")

    def test_type_rejection(self):
        # Reject boolean where integer expected
        req = {
            "mode": "query",
            "min_distinct_matches": True,
            "documents": []
        }
        res = self.run_with_input(req)
        self.assertEqual(res["status"], "refused")
        self.assertEqual(res["code"], "type_mismatch")

    def test_duplicate_keys(self):
        # Manual construction of JSON with duplicate keys
        input_str = '{"mode": "build", "mode": "query", "documents": []}'
        sys.stdin = io.StringIO(input_str)
        sys.stdout = io.StringIO()
        run_tool()
        res = json.loads(sys.stdout.getvalue())
        self.assertEqual(res["status"], "refused")
        self.assertEqual(res["code"], "duplicate_keys")

if __name__ == "__main__":
    unittest.main()
