import unittest
import json
import sys
import io
from .agents.skills.select-traceable-context-evidence.scripts.select_evidence import select_evidence

class TestSelectTraceableEvidence(unittest.TestCase):
    def test_successful_selection(self):
        request = {
            "byte_budget": 50,
            "required_ids": ["r1"],
            "registry": {"s1": {"v1": {"bounds": {"start": 0, "end": 100}}}},
            "evidence_pool": [
                {"id": "r1", "source_id": "s1", "revision": "v1", "priority": 10, "content": "High prio", "span": {"start": 0, "end": 9}},
                {"id": "r2", "source_id": "s1", "revision": "v1", "priority": 1, "content": "Low prio", "span": {"start": 10, "end": 19}}
            ]
        }
        result = select_evidence(request)
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["selected_records"]), 2)

    def test_budget_refusal(self):
        request = {
            "byte_budget": 5,
            "required_ids": ["r1"],
            "registry": {"s1": {"v1": {"bounds": {"start": 0, "end": 100}}}},
            "evidence_pool": [{"id": "r1", "source_id": "s1", "revision": "v1", "priority": 1, "content": "Too long", "span": {"start": 0, "end": 8}}]
        }
        result = select_evidence(request)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["error_code"], "BUDGET_EXCEEDED_BY_REQUIRED")

    def test_contradiction_unresolved(self):
        request = {
            "byte_budget": 100,
            "contradiction_groups": [["r1", "r2"]],
            "registry": {"s1": {"v1": {"bounds": {"start": 0, "end": 100}}}},
            "evidence_pool": [
                {"id": "r1", "source_id": "s1", "revision": "v1", "priority": 10, "content": "Side A", "span": {"start": 0, "end": 6}},
                {"id": "r2", "source_id": "s1", "revision": "v1", "priority": 1, "content": "Side B", "span": {"start": 10, "end": 16}}
            ]
        }
        # If we only select r1 (e.g. by making r2 too heavy or r1 required)
        request["required_ids"] = ["r1"]
        request["byte_budget"] = 10 # r2 is 6 bytes, but let's say we only want r1
        # Actually, r2 is 6 bytes. Let's make budget 7.
        request["byte_budget"] = 7
        
        result = select_evidence(request)
        self.assertEqual(result["status"], "success")
        self.assertIn("r2", result["unresolved_contradictions"])

    def test_invalid_type_boolean(self):
        request = {
            "byte_budget": 100,
            "registry": {"s1": {"v1": {"bounds": {"start": 0, "end": 100}}}},
            "evidence_pool": [{"id": "r1", "source_id": "s1", "revision": "v1", "priority": True, "content": "val", "span": {"start": 0, "end": 1}}]
        }
        result = select_evidence(request)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["error_code"], "INVALID_TYPE_BOOLEAN_AS_INT")

if __name__ == "__main__":
    unittest.main()
