"""The MCP setup candidate preserves producer identity, source dates and its no-connection boundary."""
import base64
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import unittest

import jsonschema

import build_mcp_setup_candidate as builder

ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / "tools/knowledge_radar/assets/plan_mcp_service_setup"
spec = importlib.util.spec_from_file_location("mcp_setup_planner_for_tests", ASSET / "scripts/plan_mcp_service_setup.py")
planner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(planner)


class McpSetupCandidateTests(unittest.TestCase):
    def test_geospatial_source_is_not_treated_as_an_mcp_service_table(self):
        table = json.loads((ROOT / "tools/resources/satellite-embedding-source-table.json").read_text())
        self.assertEqual(set(table["rows"][0]), set(table["columns"]))
        self.assertEqual(table["question_id"], "pipelines_geospatial")
        row = table["rows"][0]
        self.assertFalse(row["real_time"])
        self.assertFalse(row["official_mcp_endpoint_confirmed"])
        self.assertFalse(row["locally_reproduced"])
        self.assertEqual(row["origin"], "GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL")
        with self.assertRaises(planner.Invalid):
            planner.run({"record_type": planner.REQUEST, "on": "2026-10-08"}, table)

    def test_table_comes_from_existing_publisher_records_without_new_current_dates(self):
        table = builder.build_table()
        planner.check_table(table)
        self.assertEqual(table["as_of"], "2026-10-08")
        self.assertEqual(table["valid_until"], "2026-10-09")
        self.assertEqual(len(table["rows"]), 4)
        self.assertTrue(all(row["compatibility_basis"] == "publisher_declared" for row in table["rows"]))
        result = planner.run({"record_type": planner.REQUEST, "query": "logs", "on": "2026-10-08"}, table)
        self.assertEqual([row["key"] for row in result["candidates"]], ["cloudflare-observability"])
        self.assertFalse(result["connection_attempted"])

    def test_existing_native_proposal_carries_openai_authorship_not_default_radar_family(self):
        record, table = builder.proposals(ROOT, "a" * 40)
        self.assertEqual(record["record_type"], "harness_candidate_batch_proposals/v2")
        proposal = record["proposals"][0]
        self.assertEqual(proposal["id"], "radar_helper_plan_mcp_service_setup_v1")
        self.assertEqual(proposal["producer"]["family"], "openai")
        self.assertIn(builder.PUBLISHER_SOURCE, proposal["sources"])
        self.assertIn(builder.BUILDER_SOURCE, proposal["sources"])
        self.assertEqual(proposal["declared_effects"], ["reads_fs", "spawns_process"])
        files = {row["path"]: base64.b64decode(row["content_base64"]) for row in proposal["files"]}
        self.assertEqual(json.loads(files["references/mcp-services-table.json"]), table)
        self.assertEqual(files["LICENSE"], (ROOT / "LICENSE").read_bytes())
        self.assertNotIn("network", proposal["declared_effects"])

    def test_output_schema_accepts_observations_and_rejects_forged_effect_authority(self):
        schema = json.loads((ASSET / "contracts/output.schema.json").read_text())
        validate = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
        for request in ({"on": "2026-10-08"}, {"on": "2026-10-10"}, {"on": "2026-10-07"},
                        {"on": "2026-10-08", "query": "unlisted"}, {"on": "2026-10-08", "transport": "sse"}):
            result = planner.run({"record_type": planner.REQUEST, **request}, builder.build_table())
            validate.validate(result)
        result = planner.run({"record_type": planner.REQUEST, "on": "2026-10-08"}, builder.build_table())
        for field, value in (("connection_attempted", True), ("tool_calls_performed", 1),
                             ("effects_authorized", ["write"]), ("client_configuration_generated", True)):
            wrong = deepcopy(result); wrong[field] = value
            with self.assertRaises(jsonschema.ValidationError): validate.validate(wrong)


if __name__ == "__main__":
    unittest.main()
