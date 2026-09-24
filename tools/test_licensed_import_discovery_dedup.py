"""Checks for discovery engines and duplicate resolution.

```text
Discovery
├── code search reads page one of every spec and band before page two of any, within its budget
├── an owner seed resolves only on a clear match; an ambiguous or missing name is recorded, not guessed
├── a ClawHub entry on GitHub becomes a lead; a hosted bundle is recorded as not on GitHub
├── the registry is read from its recorded time by cursor, and only latest entries become leads
└── a link that is not a repository (a topic page, an organization) is never a lead
Duplicates
├── one upstream file found in three repositories is one record whose provenance lists the others
├── an exact or near copy of a served item is not added
├── a copy of a restricted text from another owner is refused; the same owner's permissive copy stands
└── a September 23 staged row is superseded by the complete package, not duplicated
```

A removed-guard control shows that without the restricted rule the copy of a
restricted text would be kept. No network, process or model is used.
"""
from __future__ import annotations

import json
import unittest

import test_licensed_import_support as support

from licensed_import import dedup, discovery
from licensed_import.dedup import BATCH, DuplicateIndex, Subject


class _Https:
    def __init__(self, answers):
        self.answers, self.calls = answers, []

    def get(self, host, path, query=None):
        self.calls.append((host, path, dict(query or {})))
        status, body = self.answers.pop(0)
        return type("Answer", (), {"status": status, "body": json.dumps(body).encode()})()


class DiscoveryChecks(unittest.TestCase):
    def test_code_search_is_breadth_first_within_its_budget(self):
        declaration = {"code_search": [
            {"source_id": "code.a", "kind": "skill", "terms": ["filename:SKILL.md"], "size_bands": [[0, 10], [11, 20]],
             "pages": 10, "note": "a"},
            {"source_id": "code.b", "kind": "command", "terms": ["path:.claude/commands"], "size_bands": [[0, 10]],
             "pages": 10, "note": "b"}]}
        full = {"status": 200, "body": {"total_count": 5000, "items": [
            {"path": f"s{index}/SKILL.md", "sha": "a" * 40, "repository": {"full_name": f"o/r{index}", "fork": False}}
            for index in range(100)]}}
        api = support.FakeApi(searches={})
        api.code_search = lambda query, page: (api.calls.append((query, page)) or full)
        result = discovery.code_search(declaration, api, query_budget=4)
        self.assertEqual([page for _query, page in api.calls], [1, 1, 1, 2])
        self.assertEqual(result.requests, 4)
        self.assertEqual(result.cursor["code.a|0..10"], 2)
        self.assertEqual(len(result.leads), 400)

    def test_owner_seeds_resolve_only_on_a_clear_match(self):
        items = {"clear in:name": [{"full_name": "big/clear", "stargazers_count": 5000},
                                   {"full_name": "small/clear", "stargazers_count": 3}],
                 "tie in:name": [{"full_name": "a/tie", "stargazers_count": 400},
                                 {"full_name": "b/tie", "stargazers_count": 300}],
                 "none in:name": [{"full_name": "a/other", "stargazers_count": 9}]}
        api = support.FakeApi()
        api.repository_search = lambda query, page: {"status": 200, "body": {"items": items[query]}}
        declaration = {"owner_seeds": [
            {"source_id": "seed.clear", "seed": "clear", "names": ["clear"], "queries": ["clear in:name"], "note": "x"},
            {"source_id": "seed.tie", "seed": "tie", "names": ["tie"], "queries": ["tie in:name"], "note": "x"},
            {"source_id": "seed.none", "seed": "none", "names": ["none"], "queries": ["none in:name"], "note": "x"},
            {"source_id": "seed.declared", "seed": "d", "repository": "owner/declared", "note": "x"}]}
        result = discovery.resolve_owner_seeds(declaration, api)
        self.assertEqual(sorted(row["repository"] for row in result.leads), ["big/clear", "owner/declared"])
        states = {note["seed"]: note["state"] for note in result.notes}
        self.assertEqual(states, {"clear": "resolved", "tie": "ambiguous_seed_name", "none": "seed_name_not_found",
                                  "d": "declared"})
        tie = next(note for note in result.notes if note["seed"] == "tie")
        self.assertEqual([row["repository"] for row in tie["candidates"]], ["a/tie", "b/tie"])

    def test_clawhub_entries_on_github_become_leads_and_hosted_ones_are_recorded(self):
        feed = {"entries": [
            {"id": "@a/one", "install": {"candidates": [{"github": {"repo": "a/tools", "path": "skills/one",
                                                                    "commit": "b" * 40}}]}},
            {"id": "@a/two", "install": {"candidates": [{"sourceRef": "public-clawhub"}]}}]}
        declaration = {"feeds": [{"source_id": "clawhub.skills", "host": "clawhub.ai", "path": "/v1/feeds/skills",
                                  "note": "x"}]}
        result = discovery.clawhub_feeds(declaration, _Https([(200, feed)]))
        self.assertEqual([(row["repository"], row["path"]) for row in result.leads], [("a/tools", "skills/one")])
        self.assertEqual([row["reason"] for row in result.refusals], ["feed_entry_not_on_github"])

    def test_the_registry_is_read_since_its_recorded_time_by_cursor(self):
        page = lambda names, cursor: {"servers": [  # noqa: E731
            {"server": {"name": name, "version": "1.0.0", "repository": {"url": f"https://github.com/o/{name}"}},
             "_meta": {"io.modelcontextprotocol.registry/official": {"isLatest": name != "old"}}} for name in names],
            "metadata": {"nextCursor": cursor}}
        https = _Https([(200, page(["a", "old"], "c1")), (200, page(["b"], None))])
        declaration = {"registry": {"host": "registry.modelcontextprotocol.io", "updated_since": "2026-09-23T00:00:00Z",
                                    "page_size": 2, "maximum_entries": 100, "note": "x"}}
        result = discovery.registry_updates(declaration, https, request_budget=10)
        self.assertEqual([row["repository"] for row in result.leads], ["o/a", "o/b"])
        self.assertEqual(https.calls[0][2]["updated_since"], "2026-09-23T00:00:00Z")
        self.assertEqual(https.calls[1][2]["cursor"], "c1")
        self.assertTrue(result.cursor["complete"])

    def test_only_repository_links_become_leads(self):
        self.assertEqual(discovery.repository_name("git+https://github.com/Owner/Name.git"), "Owner/Name")
        for value in ("https://github.com/topics/claude", "https://github.com/orgs/acme", "not a link", "a/b/c/d e"):
            self.assertIsNone(discovery.repository_name(value), value)


def _index():
    return DuplicateIndex(support.builtin_near_engine(), threshold=0.85)


TEXT = support.skill("join-check").decode()


class DuplicateChecks(unittest.TestCase):
    def test_one_upstream_file_in_three_repositories_is_one_record(self):
        index = _index()
        for position, owner in enumerate(("first", "second", "third")):
            index.add(Subject(f"k{position}", BATCH, f"k{position}", (0, -position, owner, ""), TEXT,
                              blob="a" * 40, owner=owner))
        result = index.resolve()
        self.assertEqual(len(result.kept), 1)
        self.assertEqual(len(result.merged_into), 2)
        self.assertEqual({row["match"] for row in result.links}, {"git_blob"})

    def test_a_near_copy_of_an_exact_group_joins_the_whole_group(self):
        index = _index()
        long_text = " ".join(f"step{number} checks item{number % 37} before use" for number in range(120))
        edited = long_text.replace("step7 checks", "step7 verifies").replace("step90 checks", "step90 tests")
        index.add(Subject("served:x", dedup.SERVED, "x", (1, 0, "x", ""), edited))
        index.add(Subject("a", BATCH, "a", (0, 0, "a", ""), long_text, blob="b" * 40))
        index.add(Subject("b", BATCH, "b", (0, 1, "b", ""), long_text, blob="b" * 40))
        index.add(Subject("c", BATCH, "c", (0, 2, "c", ""), long_text.upper()))
        result = index.resolve()
        self.assertEqual(result.kept, [])
        self.assertEqual(result.merged_into, {"a": "x", "b": "x", "c": "x"})

    def test_a_copy_of_a_served_item_is_not_added(self):
        index = _index()
        index.add(Subject("served:x", dedup.SERVED, "x", (1, 0, "x", ""), TEXT))
        index.add(Subject("k", BATCH, "k", (0, 0, "o/r", ""), TEXT.replace("Compare", "compare") + "\n"))
        result = index.resolve()
        self.assertEqual(result.kept, [])
        self.assertEqual(result.merged_into, {"k": "x"})
        self.assertEqual(result.links[0]["corpus"], dedup.SERVED)

    def test_a_near_copy_is_found(self):
        index = _index()
        long_text = " ".join(f"step{number} checks item{number % 37} before use" for number in range(120))
        edited = long_text.replace("step7 checks", "step7 verifies").replace("step90 checks", "step90 tests")
        index.add(Subject("a", BATCH, "a", (0, 0, "a", ""), long_text))
        index.add(Subject("b", BATCH, "b", (0, 1, "b", ""), edited))
        result = index.resolve()
        self.assertEqual(result.kept, ["a"])
        self.assertEqual(result.links[0]["match"], "near_text")

    def test_a_restricted_text_refuses_other_owners_copies_but_not_its_own_owners(self):
        index = _index()
        index.add(Subject("restricted:r", BATCH, "restricted:r", (-1, 0, "r", ""), TEXT, restricted=True,
                          owner="vendor"))
        index.add(Subject("copy", BATCH, "copy", (0, 0, "collector/c", ""), TEXT, owner="collector"))
        index.add(Subject("own", BATCH, "own", (0, 1, "vendor/public", ""), TEXT, owner="vendor"))
        result = index.resolve()
        self.assertEqual(set(result.restricted_copies), {"copy"})
        self.assertEqual(result.kept, ["own"])

    def test_removed_guard_without_the_restricted_rule_the_copy_would_be_kept(self):
        index = _index()
        index.add(Subject("restricted:r", BATCH, "restricted:r", (-1, 0, "r", ""), TEXT, restricted=True, owner="v"))
        index.add(Subject("copy", BATCH, "copy", (0, 0, "c/c", ""), TEXT, owner="c"))
        guarded = index.resolve()
        mutant = _index()
        mutant.add(Subject("copy", BATCH, "copy", (0, 0, "c/c", ""), TEXT, owner="c"))
        self.assertEqual(guarded.kept, [])
        self.assertEqual(mutant.resolve().kept, ["copy"])

    def test_a_september_23_row_is_superseded_not_duplicated(self):
        index = _index()
        index.add(Subject("ls1:row", dedup.LS1, "library.outside.row", (2, 0, "row", ""), TEXT))
        index.add(Subject("k", BATCH, "k", (0, 0, "o/r", ""), TEXT))
        result = index.resolve()
        self.assertEqual(result.kept, ["k"])
        self.assertEqual(result.supersedes, {"k": ["library.outside.row"]})


if __name__ == "__main__":
    unittest.main()
