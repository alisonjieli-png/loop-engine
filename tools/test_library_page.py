"""The public library page lists what a visitor may judge before paying, and nothing that would rebuild the library.

Roadmap step S-6.184. The page is rendered by src/loop_engine/core/service_runtime/library_page.py from one catalogue
view. Each rule below refuses one way to break the page: a Community item listed one by one, a second body printed, a
Verified item left out, a withdrawn item listed, a withdrawal shown without its note, a search backend named, or a
retired public word. Each rule has a known-wrong control.
"""
from __future__ import annotations

from pathlib import Path
import re
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
ROOT = Path(__file__).resolve().parents[1]

from loop_engine.core.harness_intelligence import HarnessIntelligenceCatalogue, HarnessIntelligenceDraft, item_from_body
from loop_engine.core.provisioning_server import (ProvisioningItemBinding, ProvisioningQualification,
                                                  ProvisioningQualificationResolver)
from loop_engine.core.service_runtime import library_page
from loop_engine.core.service_runtime.catalogue_serving import CatalogueView
from loop_engine.core.service_runtime.catalogue_tiers import TIER_MEANINGS

REVIEWS = "examples/29_intelligence_service/starter-catalogue/reviews.json#"
ITEMS = (
    ("check_for_existing_work_before_building", "skill", "Check for existing work before building", "verified",
     "SAMPLE BODY with <b>markup</b> that must be escaped"),
    ("find_duplicate_records_with_blocking_keys", "skill", "Find duplicate records with blocking keys", "verified",
     "FIND DUPLICATES BODY"),
    ("audio_aggregation_agentic_task", "skill", "Aggregate audio for an agentic task", "community", "COMMUNITY SKILL BODY"),
    ("write_the_step_brief", "instruction_file", "Write the brief for one step", "community", "COMMUNITY BRIEF BODY"),
)
CHANGES = {"added": [{"identity": "audio_aggregation_agentic_task", "item_version": "v", "note": ""}],
           "changed": [],
           "withdrawn": [{"identity": "normalize_phone_numbers", "item_version": "v",
                          "note": "Withdrawn after a measured drop.", "durable": True}]}
#: Words that would tell a reader how search works.
BACKEND_WORDS = re.compile(r"vector|embedding|character[ _-]?hash|lexical|full-text index", re.IGNORECASE)


def fixture_view(withdrawn=frozenset(), changes=None):
    catalogue, approvals, bodies = HarnessIntelligenceCatalogue(), {}, {}
    for identity, kind, purpose, tier, body in ITEMS:
        item = item_from_body(HarnessIntelligenceDraft(identity, kind, purpose, "harness_local", f"fixture:{identity}/v1",
                                                       "MIT"), body)
        catalogue.register(item)
        approvals[identity] = ProvisioningQualification(ProvisioningItemBinding.from_item(item), "approved", "host_attested",
                                                        REVIEWS + identity, tier)
        bodies[identity] = body
    resolver = ProvisioningQualificationResolver("library-fixture", lambda binding: approvals[binding.identity])
    return CatalogueView(catalogue, resolver, lambda item: bodies[item.identity], withdrawn=frozenset(withdrawn),
                         changes=dict(CHANGES if changes is None else changes))


def listed(html):
    return set(re.findall(r'data-library-item="([^"]+)"', html))


def printed_bodies(html):
    return re.findall(r'data-library-sample="([^"]+)"', html)


def visible_text(html):
    return re.sub(r"<[^>]+>", " ", re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", html))


def pyproject_repository():
    """The repository address pyproject.toml names, its one owner; read as text so every supported Python can."""
    found = re.search(r'^Repository = "([^"]+)"$', (ROOT / "pyproject.toml").read_text(encoding="utf-8"), re.MULTILINE)
    return found.group(1) if found else ""


def installed_as(*entries):
    """Render the page as if the installed distribution's metadata held exactly these project URL entries."""
    return mock.patch.object(library_page, "_project_urls", lambda: tuple(entries))


def page_problems(html, view):
    """Every rule the page breaks, for one view."""
    rows = library_page.library_rows(view)
    verified = {row.identity for row in rows if row.tier == "verified"}
    community = {row.identity for row in rows if row.tier == "community"}
    problems = []
    if listed(html) & community:
        problems.append("a Community item is listed one by one")
    if verified - listed(html):
        problems.append("a Verified item is left out")
    if len(printed_bodies(html)) > 1 or html.count("<pre") > 1:
        problems.append("more than one body is printed")
    for row in library_page.release_changes(view)["withdrawn"]:
        if row.get("note") and row["note"] not in html:
            problems.append("a withdrawal is shown without its note")
    if BACKEND_WORDS.search(visible_text(html)):
        problems.append("the page names how search works")
    return problems


class LibraryPageTests(unittest.TestCase):
    def setUp(self):
        self.view = fixture_view()
        self.html = library_page.library_body(self.view)

    def test_the_page_keeps_every_rule(self):
        self.assertEqual(page_problems(self.html, self.view), [])

    def test_counts_stand_in_for_the_community_items(self):
        self.assertIn("data-library-counts", self.html)
        self.assertIn("2 Community items", self.html)
        self.assertEqual(listed(self.html), {"check_for_existing_work_before_building",
                                             "find_duplicate_records_with_blocking_keys"})

    def test_one_item_is_printed_in_full_and_escaped(self):
        self.assertEqual(printed_bodies(self.html), ["check_for_existing_work_before_building"])
        self.assertIn("&lt;b&gt;markup&lt;/b&gt;", self.html)
        self.assertNotIn("<b>markup</b>", self.html)

    def test_the_labels_carry_the_published_meanings(self):
        for meaning in TIER_MEANINGS.values():
            self.assertIn(meaning.split(". ")[0], self.html)

    def test_a_review_record_in_the_repository_is_linked(self):
        repository = pyproject_repository()
        self.assertTrue(repository.startswith("https") and "/" in repository)
        with installed_as("Homepage, " + repository, "Repository, " + repository + "/"):
            html = library_page.library_body(self.view)
        self.assertIn(f'href="{repository}/blob/main/examples/29_intelligence_service/starter-catalogue/reviews.json"',
                      html)

    def test_the_repository_address_has_one_owner(self):
        repository = pyproject_repository()
        self.assertNotEqual(repository, "")
        self.assertNotIn(repository.split("://", 1)[-1], (ROOT / "src/loop_engine/core/service_runtime/library_page.py"
                                                           ).read_text(encoding="utf-8"))

    def test_known_wrong_no_named_https_repository_links_nothing(self):
        repository = pyproject_repository()
        for entries in ((), ("Homepage, " + repository,), ("Repository, " + repository.replace("https", "http", 1),),
                        ("Repository, not an address",)):
            with installed_as(*entries):
                html = library_page.library_body(self.view)
            self.assertNotIn("Review record</a>", html, entries)
            self.assertIn("Review record kept with the release", html, entries)

    def test_a_withdrawn_item_is_not_listed(self):
        item = self.view.catalogue.items["find_duplicate_records_with_blocking_keys"]
        view = fixture_view(withdrawn={(item.identity, item.digest)})
        html = library_page.library_body(view)
        self.assertNotIn("find_duplicate_records_with_blocking_keys", listed(html))
        self.assertEqual(page_problems(html, view), [])

    def test_the_whole_page_renders_from_an_empty_view(self):
        body, media_type = library_page.rendered(library_page.empty_view(), "/library", "GET", "Baltor", "baltor.ai")
        self.assertEqual(media_type, "text/html")
        self.assertIn(b"<h1", body)
        self.assertIsNone(library_page.rendered(library_page.empty_view(), "/library", "POST", "Baltor"))
        self.assertIsNone(library_page.rendered(library_page.empty_view(), "/libraries", "GET", "Baltor"))

    def test_a_row_without_a_page_of_its_own_does_not_look_like_a_link(self):
        rows = re.findall(r'<li class="md-row"[\s\S]*?</li>', self.html)
        self.assertEqual(len(rows), 2)
        self.assertEqual([row for row in rows if "md-row-link" in row or 'class="md-row-head"' not in row], [])
        css = (Path(__file__).resolve().parents[1] / "src/loop_engine/core/service_runtime/web_assets/model-directory.css"
               ).read_text(encoding="utf-8")
        self.assertRegex(css, r"\.md-row-head \.md-name\{[^}]*color:var\(--ink\)")

    def test_the_item_in_full_wraps_and_is_not_clipped(self):
        self.assertRegex(self.html, r'<pre class="md-code md-code-wrap" data-library-sample=')
        css = (Path(__file__).resolve().parents[1] / "src/loop_engine/core/service_runtime/web_assets/model-directory.css"
               ).read_text(encoding="utf-8")
        rule = re.search(r"\.md-code-wrap\{([^}]*)\}", css)
        self.assertIsNotNone(rule)
        self.assertIn("white-space:pre-wrap", rule.group(1))
        self.assertIn("max-height:none", rule.group(1))

    def test_counts_in_sentences_agree_with_their_nouns(self):
        self.assertIn("This release added 1 item and changed no items.", self.html)
        self.assertNotRegex(visible_text(self.html), r"\b1 items\b")

    def test_the_page_uses_no_retired_public_word(self):
        from test_deck_page import suite_word_rules
        text = visible_text(library_page.library_body(self.view))
        found = {name: rule.pattern for name, rule in suite_word_rules().items() if rule.search(text)}
        self.assertEqual(found, {})

    # Known-wrong controls: each rule must report the page it exists to refuse.
    def test_known_wrong_a_listed_community_item_is_found(self):
        row = next(row for row in library_page.library_rows(self.view) if row.tier == "community")
        html = self.html.replace("</ol>", library_page._verified_item(row) + "</ol>", 1)
        self.assertIn("a Community item is listed one by one", page_problems(html, self.view))

    def test_known_wrong_a_second_body_is_found(self):
        html = self.html + '<pre data-library-sample="find_duplicate_records_with_blocking_keys">FIND DUPLICATES</pre>'
        self.assertIn("more than one body is printed", page_problems(html, self.view))

    def test_known_wrong_a_missing_verified_item_is_found(self):
        html = re.sub(r'<li class="md-row" data-library-item="find_duplicate_records_with_blocking_keys"[\s\S]*?</li>', "",
                      self.html, count=1)
        self.assertIn("a Verified item is left out", page_problems(html, self.view))

    def test_known_wrong_a_withdrawal_without_its_note_is_found(self):
        html = self.html.replace("Withdrawn after a measured drop.", "")
        self.assertIn("a withdrawal is shown without its note", page_problems(html, self.view))

    def test_known_wrong_a_named_backend_is_found(self):
        html = self.html + "<p>Installed vector method: deterministic_character_hash.</p>"
        self.assertIn("the page names how search works", page_problems(html, self.view))


if __name__ == "__main__":
    unittest.main()
