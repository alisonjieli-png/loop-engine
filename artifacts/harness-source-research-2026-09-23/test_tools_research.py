"""Offline controls for the research ranking, written before its implementation."""
import copy
import unittest

from build_tools_research import make_item, score, select_population


def observation(name="io.example/inspect", status="active", version="1.0.0"):
    return {"server": {"name": name, "version": version,
                       "description": "Inspect JSON database tables and validate records.",
                       "repository": {"url": "https://github.com/example/inspect"},
                       "packages": [{"registryType": "npm", "identifier": "inspect-mcp",
                                     "version": version, "transport": {"type": "stdio"}}]},
            "_meta": {"io.modelcontextprotocol.registry/official": {
                "status": status, "isLatest": True}},
            "_source": {"digest": "a" * 64, "path": "servers/0/server",
                        "url": "https://registry.modelcontextprotocol.io/v0.1/servers"}}


class RankingControls(unittest.TestCase):
    def test_deprecated_and_nonlatest_never_selected(self):
        stale = observation("io.example/stale")
        stale["_meta"]["io.modelcontextprotocol.registry/official"]["isLatest"] = False
        chosen, excluded = select_population([observation(), observation("io.example/old", "deprecated"), stale])
        self.assertEqual([x["server"]["name"] for x in chosen], ["io.example/inspect"])
        self.assertEqual(len(excluded), 2)

    def test_conflicting_latest_versions_are_not_guessed(self):
        chosen, excluded = select_population([observation(), observation(version="2.0.0")])
        self.assertEqual(chosen, [])
        self.assertEqual(excluded[0]["reason"], "conflicting_name_observations")

    def test_exact_duplicate_and_same_surface_alias_collapse(self):
        chosen, excluded = select_population([observation(), observation(), observation("io.example/alias")])
        self.assertEqual(len(chosen), 1)
        self.assertTrue(any(x["reason"] == "duplicate_installation_surface" for x in excluded))

    def test_different_package_in_monorepo_is_retained(self):
        other = observation("io.example/other")
        other["server"]["packages"][0]["identifier"] = "another-operation-mcp"
        chosen, _ = select_population([observation(), other])
        self.assertEqual(len(chosen), 2)

    def test_missing_license_is_not_defaulted_or_verified(self):
        item = make_item(observation(), 1, {})
        self.assertEqual(item["license_reported"], "unknown")
        self.assertFalse(item["license_verified"])
        self.assertEqual(item["tool_unit"], "tool_provider/mcp_server_package")
        self.assertEqual(item["qualification_status"], "unreviewed")
        self.assertEqual(item["compatibility_status"], "unverified")

    def test_declared_package_metadata_is_not_callable_evidence(self):
        checks = {"io.example/inspect": {"status": 200, "identity_matches": True,
                                         "license_reported": "MIT", "sha256": "b" * 64}}
        item = make_item(observation(), 1, checks)
        self.assertEqual(item["license_reported"], "MIT")
        self.assertFalse(item["license_verified"])
        self.assertIsNone(item["upstream_revision"])
        self.assertIsNone(item["upstream_blob_sha"])
        self.assertFalse(item["tools_list_observed"])

    def test_score_is_bounded_and_component_sum_is_exact(self):
        components, families = score(observation()["server"], {})
        self.assertGreaterEqual(sum(components.values()), 0)
        self.assertLessEqual(sum(components.values()), 100)
        self.assertIn("structured_data", families)

    def test_explicit_test_registration_cannot_equal_normal_priority(self):
        normal = observation()["server"]
        test = copy.deepcopy(normal)
        test["description"] = "[TEST] " + test["description"]
        self.assertLess(sum(score(test, {})[0].values()), sum(score(normal, {})[0].values()))


if __name__ == "__main__":
    unittest.main()
