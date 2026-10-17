"""The library sites name only real library items, and their records refuse anything else.

Kind: development check over packaged files. It reads `web_assets/library-sites/hosts.json` and `items.json` through their
typed reader (`library_site_records`), the repository's publication record that confirmed the served release, the
repository's own creative originals sources and the gallery record. It opens no connection and needs no credential.
The build tool's own inputs stay outside the repository; `tools/build_library_sites.py --check` compares the written
record with them where they exist.

    PYTHONPATH=src:tools python -m unittest tools/test_library_sites.py
"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from loop_engine.core.service_runtime import library_site_records as records
from loop_engine.core.service_runtime.gallery_records import PUBLIC_TIERS

import build_library_sites as builder

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "src/loop_engine/core/service_runtime/web_assets"


def hosts_text():
    return (ASSETS / "library-sites" / records.HOSTS_FILE).read_text("utf-8")


def items_text():
    return (ASSETS / "library-sites" / records.ITEMS_FILE).read_text("utf-8")


def fresh():
    """A changeable copy of both packaged records."""
    return json.loads(hosts_text()), json.loads(items_text())


def parse(hosts, items):
    """Both records, read as the service reads them, after a known-wrong change."""
    hosts_record = records.parse_hosts(json.dumps(hosts))
    return records.parse_items(json.dumps(items), hosts_record)


class PackagedRecords(unittest.TestCase):
    def test_the_packaged_records_are_read_by_the_typed_reader(self):
        hosts, items = records.hosts_record(), records.items_record()
        self.assertEqual([host["id"] for host in hosts["hosts"]], ["deterministic-skills", "harness-tools", "corner-cases"])
        shown = {identity for host in hosts["hosts"] for category in host["categories"] for identity in category["items"]}
        self.assertEqual(shown, {item["identity"] for item in items["items"]})

    def test_the_item_record_is_bound_to_the_publication_that_confirmed_the_served_release(self):
        built = records.items_record()["built_from"]
        evidence = json.loads((ROOT / built["evidence"]).read_text("utf-8"))
        self.assertEqual(evidence["record_type"], "catalogue_publication_evidence/v1")
        self.assertEqual((built["release_id"], built["content_digest"], built["release_items"], built["confirmed_at"]),
                         (evidence["active_release"], evidence["content_digest"], evidence["items_after"],
                          evidence["confirmed_at"]))
        self.assertEqual(built["evidence"], builder.EVIDENCE)

    def test_every_creative_item_is_the_repository_source_it_names(self):
        creative = [item for item in records.items_record()["items"]
                    if item["identity"].startswith("library.supply.creative_originals.")]
        self.assertTrue(creative)
        for item in creative:
            with self.subTest(item=item["name"]):
                folder = ROOT / "tools/creative_originals" / item["family"] / "items" / item["name"]
                self.assertEqual((folder / "README.md").read_text("utf-8").splitlines()[0], "# " + item["title"])
                self.assertEqual(json.loads((folder / "item.json").read_text("utf-8"))["title"], item["title"])

    def test_gallery_links_name_the_same_public_item_at_the_same_version(self):
        gallery = {item["slug"]: item for item in json.loads((ASSETS / "gallery" / "gallery.json").read_text("utf-8"))["items"]}
        linked = [item for item in records.items_record()["items"] if item["gallery"]]
        self.assertTrue(linked)
        for item in linked:
            with self.subTest(item=item["slug"]):
                shown = gallery[item["gallery"]]
                self.assertIn(shown["tier"], PUBLIC_TIERS)
                self.assertEqual((shown["identity"], shown["version"]), (item["identity"], item["version"]))

    def test_the_deterministic_host_shows_only_tested_items_without_network_access(self):
        hosts, items = records.hosts_record(), records.items_by_identity()
        host = next(host for host in hosts["hosts"] if host["rule"].get("no_network"))
        for category in host["categories"]:
            for identity in category["items"]:
                with self.subTest(item=identity):
                    item = items[identity]
                    self.assertFalse({"network", "reads_secret"} & set(item["effects"]))
                    self.assertTrue(any(builder.TEST_FILE.search(path) for path, _size in item["files"]))

    def test_a_count_read_from_a_record_equals_that_record(self):
        hosts, items = records.hosts_record(), records.items_record()
        for host in hosts["hosts"]:
            for category in host["categories"]:
                rule = category["library_count"]
                if rule and "evidence" in rule:
                    value = json.loads((ROOT / rule["evidence"]).read_text("utf-8"))
                    for field in rule["fields"]:
                        value = value[field]
                    self.assertEqual(items["counts"][f"{host['id']}/{category['slug']}"], value)

    def test_the_hosts_own_copy_passes_the_wording_rules_and_the_house_punctuation(self):
        rules, hosts = builder.wording_rules(), records.hosts_record()
        copy = [value for host in hosts["hosts"] for value in (host["name"], host["headline"], host["lede"], host["why"])]
        copy += [value for host in hosts["hosts"] for category in host["categories"]
                 for value in (category["title"], category["description"], category["lede"], *category["watch_for"])]
        copy += list(hosts["titles"].values())
        for text in copy:
            with self.subTest(text=text[:60]):
                self.assertEqual(builder.refused_words(text, rules), [])
                # humanizer-context.md: no em or en dashes in Baltor's own copy, and no "reviewed" counting.
                self.assertNotRegex(text, "[–—]|\\breviewed\\b")

    def test_item_text_passes_the_public_wording_rules(self):
        rules = builder.wording_rules()
        for item in records.items_record()["items"]:
            text = " ".join([item["title"], item["summary"], *(value for pair in item["facts"] + item["cases"] + item["notes"]
                                                               for value in pair)])
            with self.subTest(item=item["identity"]):
                self.assertEqual(builder.refused_words(text, rules), [])


def _drop_one_shown(items):
    items["items"] = items["items"][1:]
    return items


KNOWN_WRONG = {
    "a category shows an item the catalogue data does not hold": lambda hosts, items: (hosts, _drop_one_shown(items)),
    "the item record holds an item no category shows": lambda hosts, items: (
        hosts, {**items, "items": items["items"] + [{**items["items"][0], "identity": "made_up_component",
                                                      "slug": "made-up-component"}]}),
    "a version that is not the one its identity names": lambda hosts, items: (
        hosts, {**items, "items": [{**item, "version": "0" * 64} if item["identity"].startswith("library.supply.") else item
                                   for item in items["items"]]}),
    "an item record built for another selection": lambda hosts, items: (
        {**hosts, "titles": {**hosts["titles"], next(iter(hosts["titles"])): "Another title"}}, items),
    "two items at one address": lambda hosts, items: (
        hosts, {**items, "items": [{**item, "slug": items["items"][0]["slug"]} for item in items["items"]]}),
    "a size that is not the files' total": lambda hosts, items: (
        hosts, {**items, "items": [{**items["items"][0], "bytes": items["items"][0]["bytes"] + 1}, *items["items"][1:]]}),
    "a description a search engine would cut short": lambda hosts, items: (_category_change(hosts, "description", "x" * 161), items),
    "a category of two items": lambda hosts, items: (_category_change(hosts, "items", hosts["hosts"][0]["categories"][0]["items"][:2]), items),
    "a host rule this reader does not know": lambda hosts, items: (
        {**hosts, "hosts": [{**hosts["hosts"][0], "rule": {"allow_anything": True}}, *hosts["hosts"][1:]]}, items),
    "a title for an item no category shows": lambda hosts, items: (
        {**hosts, "titles": {**hosts["titles"], "made_up_component": "A title"}}, items),
    "an unknown record version": lambda hosts, items: (hosts, {**items, "record_type": "website_library_site_items/v2"}),
}
#: The reader guards whose removal must let their known-wrong records through.
GUARDED = {"_membership": ("a category shows an item the catalogue data does not hold",
                           "the item record holds an item no category shows"),
           "_version": ("a version that is not the one its identity names",)}


def _category_change(hosts, field, value):
    first = hosts["hosts"][0]
    return {**hosts, "hosts": [{**first, "categories": [{**first["categories"][0], field: value},
                                                         *first["categories"][1:]]}, *hosts["hosts"][1:]]}


class KnownWrongRecords(unittest.TestCase):
    def test_the_packaged_records_pass(self):
        parse(*fresh())

    def test_the_reader_refuses_each_known_wrong_record(self):
        for description, change in KNOWN_WRONG.items():
            with self.subTest(case=description), self.assertRaises(records.LibrarySiteRecordError):
                parse(*change(*fresh()))

    def test_a_removed_reader_guard_lets_its_known_wrong_record_through(self):
        for guard, cases in GUARDED.items():
            for description in cases:
                with self.subTest(guard=guard, case=description), mock.patch.object(records, guard, lambda *given: None):
                    parse(*KNOWN_WRONG[description](*fresh()))


class BuildTool(unittest.TestCase):
    def test_the_wording_guard_refuses_retired_words_and_passes_plain_ones(self):
        rules = builder.wording_rules()
        for text in ("Join the beta today.", "Loop Engine runs this.", "Search is free.", "Coming soon"):
            with self.subTest(text=text):
                self.assertTrue(builder.refused_words(text, rules))
        self.assertEqual(builder.refused_words("Compare two samples with a kernel test.", rules), [])

    def test_a_release_folder_that_is_not_the_confirmed_release_is_refused(self):
        with tempfile.TemporaryDirectory(prefix="library-sites-build-") as folder:
            Path(folder, "bundle.json").write_text(json.dumps({"content_digest": "0" * 64, "release_items": 1}))
            with self.assertRaises(builder.BuildError):
                builder.binding(folder, {"one": "1" * 64})

    def test_a_local_copy_is_read_only_when_every_file_has_the_released_digest(self):
        with tempfile.TemporaryDirectory(prefix="library-sites-build-") as folder:
            package = Path(folder, "baltor_example")
            package.mkdir()
            Path(package, "SKILL.md").write_text("# Example\n")
            digest = builder._digest(package / "SKILL.md")
            record = {"package": {"files": [{"path": "SKILL.md", "digest": digest}]}}
            self.assertEqual(builder.verified_package("baltor_example", record, [folder]), package)
            record["package"]["files"][0]["digest"] = "0" * 64
            self.assertIsNone(builder.verified_package("baltor_example", record, [folder]))

    def test_titles_never_stop_in_the_middle_of_a_phrase(self):
        self.assertEqual(builder._title_from("Clean and repair email addresses: remove mailto and angle brackets"),
                         "Clean and repair email addresses")
        long = ("Calculate the share of seats held by women in declared parliamentary or local government bodies from seat "
                "counts, checking totals")
        self.assertFalse(builder._title_from(long).endswith((" or", " and", " in", " the")))


if __name__ == "__main__":
    unittest.main()
