"""Known-wrong cases for the weekly upstream source check (tools/check_upstream_sources.py).

No network is used: the repository host is a fake opener that records what was asked. The known-wrong cases are a
reference that is not an import, a read without the network authorization, a licence answer the host could not
detect (which must not count as a change), and a repository bound that is exceeded.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))

import check_upstream_sources as upstream  # noqa: E402

REVISION = "a" * 40
ITEMS = [
    {"identity": "alpha_skill", "source_ref": f"github.com/acme/tools/skills/alpha/SKILL.md@{REVISION}", "license": "MIT"},
    {"identity": "beta_skill", "source_ref": f"github.com/acme/tools/skills/beta/SKILL.md@{REVISION}", "license": "MIT"},
    {"identity": "gone_skill", "source_ref": f"github.com/vanished/repo/SKILL.md@{REVISION}", "license": "Apache-2.0"},
    {"identity": "original_skill", "source_ref": "fixture:original_skill", "license": "MIT"},
]


class FakeHost:
    """The repository host as the check sees it: one answer for each repository, and a log of every read."""

    def __init__(self, answers):
        self.answers, self.reads = answers, []

    def __call__(self, url):
        self.reads.append(url)
        name = url.split("/repos/", 1)[1].split("/security-advisories", 1)[0].split("?", 1)[0]
        if url.endswith("per_page=100"):
            return 200, json.dumps(self.answers.get(name, {}).get("advisories", [])).encode()
        answer = self.answers.get(name)
        if answer is None:
            return 404, b'{"message":"Not Found"}'
        return 200, json.dumps({"license": {"spdx_id": answer.get("licence", "")}, "archived": answer.get("archived", False)}).encode()


class SourceReferenceTests(unittest.TestCase):
    def test_an_imported_reference_names_its_repository_path_and_revision(self):
        self.assertEqual(upstream.parse_source_ref(ITEMS[0]["source_ref"]),
                         {"owner": "acme", "repository": "tools", "path": "skills/alpha/SKILL.md", "revision": REVISION})

    def test_known_wrong_a_reference_that_is_not_an_import_is_not_checked(self):
        self.assertIsNone(upstream.parse_source_ref("fixture:original_skill"))
        self.assertIsNone(upstream.parse_source_ref(f"github.com/acme/tools/SKILL.md@{'a' * 39}"))
        self.assertIsNone(upstream.parse_source_ref(None))
        self.assertEqual(sorted(upstream.group_by_repository(ITEMS)), ["acme/tools", "vanished/repo"])


class AssessmentTests(unittest.TestCase):
    def test_gone_changed_and_advisory_are_each_a_finding_that_names_every_item(self):
        rows = upstream.group_by_repository(ITEMS)["acme/tools"]
        gone = upstream.assess("acme/tools", rows, {"status": "gone", "http_status": 404})
        self.assertEqual([(row["code"], row["identities"]) for row in gone], [("repository_gone", ["alpha_skill", "beta_skill"])])
        changed = upstream.assess("acme/tools", rows, {"status": "present", "licence": "Apache-2.0", "archived": False, "advisories": 0})
        self.assertEqual([row["code"] for row in changed], ["licence_changed"])
        advisory = upstream.assess("acme/tools", rows, {"status": "present", "licence": "MIT", "archived": True, "advisories": 2})
        self.assertEqual([row["code"] for row in advisory], ["advisory_published", "repository_archived"])

    def test_known_wrong_an_unchanged_repository_and_an_undetected_licence_raise_no_finding(self):
        rows = upstream.group_by_repository(ITEMS)["acme/tools"]
        self.assertEqual(upstream.assess("acme/tools", rows, {"status": "present", "licence": "MIT", "archived": False, "advisories": 0}), [])
        self.assertEqual(upstream.assess("acme/tools", rows, {"status": "present", "licence": "NOASSERTION", "archived": False, "advisories": 0}), [])
        unknown = upstream.assess("acme/tools", rows, {"status": "error", "http_status": 503})
        self.assertEqual([row["code"] for row in unknown], ["upstream_unknown"])


class RunTests(unittest.TestCase):
    def test_one_read_per_repository_within_the_bound_and_a_record_of_every_finding(self):
        host = FakeHost({"acme/tools": {"licence": "Apache-2.0", "advisories": [{"ghsa_id": "GHSA-1"}]}})
        record = upstream.run(ITEMS, authorize_network_reads=True, opener=host, max_repositories=1)
        self.assertEqual(record["checked_repositories"], ["acme/tools"])
        self.assertEqual(record["skipped_repositories"], ["vanished/repo"])
        self.assertEqual(sorted(row["code"] for row in record["findings"]), ["advisory_published", "licence_changed"])
        self.assertEqual(len([url for url in host.reads if "security-advisories" not in url]), 1)
        everything = upstream.run(ITEMS, authorize_network_reads=True, opener=FakeHost({"acme/tools": {"licence": "MIT"}}))
        self.assertEqual([row["code"] for row in everything["findings"]], ["repository_gone"])
        with tempfile.TemporaryDirectory() as folder:
            path = upstream.write_record(folder, everything)
            self.assertEqual(json.loads(path.read_text())["record_type"], "upstream_source_check/v1")

    def test_known_wrong_nothing_is_read_without_the_network_authorization(self):
        host = FakeHost({})
        record = upstream.run(ITEMS, authorize_network_reads=False, opener=host)
        self.assertEqual((record["checked_repositories"], record["findings"], host.reads), ([], [], []))
        self.assertEqual(record["imported_items"], 3)
        with tempfile.TemporaryDirectory() as folder:
            items = Path(folder) / "items.json"
            items.write_text(json.dumps(ITEMS))
            with patch.object(upstream, "default_opener", host):
                with self.assertRaises(SystemExit):
                    upstream.main(["--items-file", str(items), "--output-folder", folder])
                self.assertEqual(host.reads, [])
                code = upstream.main(["--items-file", str(items), "--output-folder", folder, "--list-only"])
            self.assertEqual((code, host.reads), (0, []))
            self.assertEqual(len(list(Path(folder).glob("upstream-check-*.json"))), 1)


if __name__ == "__main__":
    unittest.main()
