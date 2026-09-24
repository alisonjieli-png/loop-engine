import unittest
import json
import io
import sys
from tools.check_tabular_transformation_invariants import solve

class TestInvariants(unittest.TestCase):
    def run_tool(self, payload: dict) -> dict:
        # Mock stdin
        sys.stdin = io.StringIO(json.dumps(payload))
        # We need to re-run the logic because solve() reads from sys.stdin
        # In a real test we might use subprocess, but here we call the function
        # Note: solve() in the tool reads sys.stdin once.
        return solve()

    def test_success_case(self):
        payload = {
            "before": [{"id": "a", "v": 1, "p": "keep"}],
            "after": [{"id": "a", "v": 2, "p": "keep"}],
            "contract": {
                "id_field": "id",
                "preserved_fields": ["p"],
                "allowed_changes": ["v"],
                "integer_totals": ["v"]
            }
        }
        res = self.run_tool(payload)
        self.assertEqual(res["status"], "success")

    def test_id_mismatch(self):
        payload = {
            "before": [{"id": "a"}],
            "after": [{"id": "b"}],
            "contract": {"id_field": "id"}
        }
        res = self.run_tool(payload)
        self.assertEqual(res["status"], "refused")
        self.assertEqual(res["code"], "ID_SET_MISMATCH")

    def test_preserved_violation(self):
        payload = {
            "before": [{"id": "a", "f": 1}],
            "after": [{"id": "a", "f": 2}],
            "contract": {"id_field": "id", "preserved_fields": ["f"]}
        }
        res = self.run_tool(payload)
        self.assertEqual(res["status"], "refused")
        self.assertEqual(res["code"], "INVARIANT_VIOLATION")
        self.assertEqual(res["violations"][0]["field"], "f")

    def test_integer_sum_violation(self):
        payload = {
            "before": [{"id": "a", "s": 10}, {"id": "b", "s": 10}],
            "after": [{"id": "a", "s": 10}, {"id": "b", "s": 11}],
            "contract": {"id_field": "id", "integer_totals": ["s"]}
        }
        res = self.run_tool(payload)
        self.assertEqual(res["status"], "refused")
        self.assertEqual(res["code"], "TOTAL_MISMATCH")

    def test_boolean_as_integer(self):
        payload = {
            "before": [{"id": "a", "s": True}],
            "after": [{"id": "a", "s": 1}],
            "contract": {"id_field": "id", "integer_totals": ["s"]}
        }
        res = self.run_tool(payload)
        self.assertEqual(res["status"], "refused")
        self.assertEqual(res["code"], "NON_INTEGER_TOTAL")

    def test_duplicate_id(self):
        payload = {
            "before": [{"id": "a"}, {"id": "a"}],
            "after": [{"id": "a"}],
            "contract": {"id_field": "id"}
        }
        res = self.run_tool(payload)
        self.assertEqual(res["status"], "refused")
        self.assertEqual(res["code"], "DUPLICATE_ID")

if __name__ == "__main__":
    unittest.main()
