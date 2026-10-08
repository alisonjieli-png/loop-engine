"""Offline positive, malformed, stale, and known-wrong controls. No service is contacted."""
from copy import deepcopy
import io
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan_mcp_service_setup as planner


def fixture():
    row = {"key": "service-a", "title": "Example logs service", "url": "https://mcp.example.com/mcp",
           "documentation": "https://example.com/docs/mcp", "publisher": "example.com", "transport": "streamable-http",
           "authentication": "unknown", "capabilities": "logs analytics", "compatibility_basis": "publisher_declared",
           "transport_conflict": False, "source_updated_at": "2026-07-28", "last_verified_at": "2026-10-08", "review_after": "2026-10-15"}
    return {"record_type": "knowledge_radar_table/v1", "question_id": "mcp_service_setup", "as_of": "2026-10-08",
            "valid_until": "2026-10-15", "columns": sorted(planner.ROW_FIELDS), "rows": [row]}


class PlannerChecks(unittest.TestCase):
    def request(self, **changes):
        return {"record_type": planner.REQUEST, "on": "2026-10-08", **changes}

    def test_matching_source_is_not_a_connection_or_verified_tool(self):
        result = planner.run(self.request(query="logs", publisher="example.com"), fixture())
        self.assertEqual(result["state"], "source_candidates")
        self.assertEqual(result["candidates"][0]["authentication"], "unknown")
        self.assertEqual(result["candidates"][0]["setup_state"], "not_connected_not_tested")
        self.assertFalse(result["connection_attempted"])
        self.assertFalse(result["client_configuration_generated"])
        self.assertEqual(result["tool_calls_performed"], 0)
        self.assertEqual(result["effects_authorized"], [])

    def test_dates_keep_stale_and_future_tables_out_of_current_results(self):
        for on, state in (("2026-10-16", "table_expired"), ("2026-10-07", "table_not_yet_current")):
            result = planner.run(self.request(on=on), fixture())
            self.assertEqual(result["state"], state)
            self.assertEqual(result["candidates"], [])

    def test_row_review_due_and_transport_conflicts_are_visible_holds(self):
        for key, value, reason in (("transport_conflict", True, "transport_conflict"),
                                   ("transport", "sse", "transport_not_matched"),
                                   ("review_after", "2026-10-08", "source_review_due")):
            table = fixture(); table["rows"][0][key] = value
            result = planner.run(self.request(on="2026-10-09"), table)
            self.assertEqual(result["state"], "source_recheck_required")
            self.assertEqual(result["withheld"][0]["reason"], reason)
            self.assertEqual(result["candidates"], [])

    def test_similar_name_does_not_bypass_requested_publisher(self):
        self.assertEqual(planner.run(self.request(publisher="different.com"), fixture())["state"], "no_matching_source")
        self.assertEqual(planner.run(self.request(query="unlisted capability"), fixture())["state"], "no_matching_source")

    def test_limits_versions_unknown_fields_and_credentials_are_refused(self):
        for changes in ({"record_type": "mcp_setup_plan_request/v2"}, {"count": True}, {"count": 21},
                        {"on": "2026-02-31"}, {"transport": "auto"}, {"connect": True},
                        {"api_key": "not-a-real-credential"}, {"query": "x" * 161}):
            with self.assertRaises(planner.Invalid):
                planner.run(self.request(**changes), fixture())

    def test_unknown_request_version_refuses_before_the_table_is_read(self):
        with mock.patch.object(planner, "TABLE") as table, mock.patch("sys.stdout", new_callable=io.StringIO) as output:
            status = planner.main(['{"record_type":"mcp_setup_plan_request/v2"}'])
        self.assertEqual(status, 2)
        table.resolve.assert_not_called()
        table.open.assert_not_called()
        self.assertEqual(json.loads(output.getvalue()), {"record_type": planner.ERROR, "code": "invalid_request"})

    def test_unsafe_locations_and_forged_qualification_do_not_become_candidates(self):
        for url in ("http://example.com/mcp", "https://user:pass@example.com/mcp", "https://127.0.0.1/mcp",
                    "https://localhost.localdomain/mcp", "https://mcp..example.com/mcp", "https://-example.com/mcp",
                    "https://example.com/{tenant}/mcp",
                    "https://example.com/mcp?key=value", "https://example.com/mcp#extra"):
            table = fixture(); table["rows"][0]["url"] = url
            with self.assertRaises(planner.Invalid):
                planner.run(self.request(), table)
        table = fixture(); table["rows"][0]["compatibility_basis"] = "tested"
        with self.assertRaises(planner.Invalid):
            planner.run(self.request(), table)

    def test_duplicate_rows_columns_types_and_json_keys_refuse(self):
        for change in ("duplicates", "columns", "auth"):
            table = fixture()
            if change == "duplicates": table["rows"] *= 2
            if change == "columns": table["columns"] = [{}]
            if change == "auth": table["rows"][0]["authentication"] = []
            with self.assertRaises(planner.Invalid):
                planner.run(self.request(), table)
        for raw in (b'{"a":1,"a":2}', b'{"value":NaN}', b" " * (planner.MAXIMUM_BYTES + 1)):
            with self.assertRaises(planner.Invalid): planner.parse_json(raw)

    def test_output_bound_is_enforced_and_order_is_deterministic(self):
        table = fixture()
        second = deepcopy(table["rows"][0]); second.update(key="service-b", title="A first service")
        table["rows"].append(second)
        result = planner.run(self.request(count=1), table)
        self.assertEqual([row["key"] for row in result["candidates"]], ["service-b"])
        self.assertEqual(result, planner.run(self.request(count=1), table))

    def test_known_wrong_claims_are_not_accepted_as_success(self):
        result = planner.run(self.request(), fixture())
        good = lambda value: not value["connection_attempted"] and value["effects_authorized"] == []
        self.assertTrue(good(result))
        wrong = deepcopy(result); wrong["connection_attempted"] = True
        self.assertFalse(good(wrong))
        wrong = deepcopy(result); wrong["effects_authorized"] = ["network_write"]
        self.assertFalse(good(wrong))


if __name__ == "__main__":
    result = unittest.TextTestRunner(stream=sys.stderr, verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(PlannerChecks))
    print(json.dumps({"passed": result.testsRun - len(result.failures) - len(result.errors),
                      "failed": len(result.failures) + len(result.errors), "known_wrong_rejected": 2}))
    raise SystemExit(not result.wasSuccessful())
