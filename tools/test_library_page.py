"""The public library page counts every kind of harness file and lists no item before sign-up.

Roadmap step S-6.208, after S-6.184. The page is rendered by src/loop_engine/core/service_runtime/library_page.py from
one catalogue view. Each rule below refuses one way to break the page: an item listed one by one, a second body
printed, a size or a digest shown, a withdrawn item counted, a withdrawal shown without its note, a count that folds
the harness kinds into the four served kinds, a search backend named, or a retired public word. Each rule has a
known-wrong control.
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
from loop_engine.core.service_runtime.catalogue_attributes import HARNESS_KINDS
from loop_engine.core.service_runtime.catalogue_schema import CatalogueAttributeSchema
from loop_engine.core.service_runtime.catalogue_serving import CatalogueView
from loop_engine.core.service_runtime.catalogue_tiers import TIER_MEANINGS

REVIEWS = "examples/29_intelligence_service/starter-catalogue/reviews.json#"
#: identity, served kind, purpose, tier, body, styles (the licensed import writes the harness kind first).
ITEMS = (
    ("check_for_existing_work_before_building", "skill", "Check for existing work before building", "verified",
     "SAMPLE BODY with <b>markup</b> that must be escaped", ("claude", "codex")),
    ("find_duplicate_records_with_blocking_keys", "skill", "Find duplicate records with blocking keys", "verified",
     "FIND DUPLICATES BODY", ()),
    ("audio_aggregation_agentic_task", "skill", "Aggregate audio for an agentic task", "community",
     "COMMUNITY SKILL BODY", ("skill", "agent_skill")),
    ("write_the_step_brief", "instruction_file", "Write the brief for one step", "community", "COMMUNITY BRIEF BODY",
     ("subagent", "plugin_agent")),
    ("import_hook_session_start", "tool", "Run a check when a session starts", "community", "HOOK BODY",
     ("hook", "plugin_hooks")),
)
CHANGES = {"added": [{"identity": "audio_aggregation_agentic_task", "item_version": "v", "note": ""}],
           "changed": [],
           "withdrawn": [{"identity": "normalize_phone_numbers", "item_version": "v",
                          "note": "Withdrawn after a measured drop.", "durable": True}]}
#: Words that would tell a reader how search works.
BACKEND_WORDS = re.compile(r"vector|embedding|character[ _-]?hash|lexical|full-text index", re.IGNORECASE)
SIZE_OR_DIGEST = re.compile(r"\b\d[\d,]* bytes\b|\bdigest\b|[0-9a-f]{12,}", re.IGNORECASE)


def fixture_view(withdrawn=frozenset(), changes=None, attributes=None):
    catalogue, approvals, bodies = HarnessIntelligenceCatalogue(), {}, {}
    for identity, kind, purpose, tier, body, styles in ITEMS:
        item = item_from_body(HarnessIntelligenceDraft(identity, kind, purpose, "harness_local", f"fixture:{identity}/v1",
                                                       "MIT", styles=styles), body)
        catalogue.register(item)
        approvals[identity] = ProvisioningQualification(ProvisioningItemBinding.from_item(item), "approved", "host_attested",
                                                        REVIEWS + identity, tier)
        bodies[identity] = body
    resolver = ProvisioningQualificationResolver("library-fixture", lambda binding: approvals[binding.identity])
    served = {}
    if attributes:
        served = {"schema": CatalogueAttributeSchema.from_dict({"record_type": "catalogue_attribute_schema/v1", "attributes": [
            {"name": "harness_kind", "type": "choice", "choices": list(HARNESS_KINDS), "filterable": True, "shown": True}]}),
            "attributes": dict(attributes)}
    return CatalogueView(catalogue, resolver, lambda item: bodies[item.identity], withdrawn=frozenset(withdrawn),
                         changes=dict(CHANGES if changes is None else changes), **served)


def listed(html):
    return set(re.findall(r'data-library-item="([^"]+)"', html))


def counted_kinds(html):
    return re.findall(r'<tr data-harness-kind="([^"]+)">', html)


def printed_bodies(html):
    return re.findall(r'data-library-sample="([^"]+)"', html)


def visible_text(html):
    return re.sub(r"<[^>]+>", " ", re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>|<pre[\s\S]*?</pre>", " ", html))


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
    problems = []
    if listed(html):
        problems.append("an item is listed one by one")
    if len(printed_bodies(html)) > 1 or html.count("<pre") > 1:
        problems.append("more than one body is printed")
    if SIZE_OR_DIGEST.search(visible_text(html)):
        problems.append("a size or a digest is shown")
    if set(counted_kinds(html)) != {row.harness_kind for row in rows}:
        problems.append("the counts do not name every harness kind the view serves")
    if {"tool", "instruction_file"} & set(counted_kinds(html)) and any(
            row.harness_kind not in ("tool", "instruction_file") for row in rows if row.kind in ("tool", "instruction_file")):
        problems.append("a count folds harness kinds into the served kinds")
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

    def test_the_counts_name_every_harness_kind_and_no_item_is_listed(self):
        self.assertIn("data-library-counts", self.html)
        self.assertEqual(counted_kinds(self.html), ["skill", "subagent", "hook"])
        self.assertEqual(listed(self.html), set())
        self.assertIn("5 files a coding agent can fetch today, of 3 kinds", self.html)
        self.assertIn("2 Verified and 3 Community", self.html)
        self.assertIn('href="/get-started"', self.html)
        self.assertIn('href="/app#browse-heading"', self.html)

    def test_a_served_harness_kind_attribute_wins_over_the_styles(self):
        view = fixture_view(attributes={"find_duplicate_records_with_blocking_keys": {"harness_kind": "rules"}})
        rows = {row.identity: row for row in library_page.library_rows(view)}
        self.assertEqual(rows["find_duplicate_records_with_blocking_keys"].harness_kind, "rules")
        self.assertEqual(rows["write_the_step_brief"].harness_kind, "subagent")
        self.assertEqual(rows["import_hook_session_start"].harness_kind, "hook")
        self.assertEqual(rows["check_for_existing_work_before_building"].harness_kind, "skill")
        self.assertEqual(page_problems(library_page.library_body(view), view), [])

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

    def test_a_withdrawn_item_is_not_counted(self):
        item = self.view.catalogue.items["import_hook_session_start"]
        view = fixture_view(withdrawn={(item.identity, item.digest)})
        html = library_page.library_body(view)
        self.assertNotIn("hook", counted_kinds(html))
        self.assertEqual(page_problems(html, view), [])

    def test_the_whole_page_renders_from_an_empty_view(self):
        body, media_type = library_page.rendered(library_page.empty_view(), "/library", "GET", "Baltor", "baltor.ai")
        self.assertEqual(media_type, "text/html")
        self.assertIn(b"<h1", body)
        self.assertIsNone(library_page.rendered(library_page.empty_view(), "/library", "POST", "Baltor"))
        self.assertIsNone(library_page.rendered(library_page.empty_view(), "/libraries", "GET", "Baltor"))

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
    def test_known_wrong_a_listed_item_is_found(self):
        html = self.html + '<li data-library-item="write_the_step_brief">Write the brief for one step</li>'
        self.assertIn("an item is listed one by one", page_problems(html, self.view))

    def test_known_wrong_a_second_body_is_found(self):
        html = self.html + '<pre data-library-sample="find_duplicate_records_with_blocking_keys">FIND DUPLICATES</pre>'
        self.assertIn("more than one body is printed", page_problems(html, self.view))

    def test_known_wrong_a_size_or_a_digest_is_found(self):
        self.assertIn("a size or a digest is shown", page_problems(self.html + "<p>1,204 bytes</p>", self.view))
        self.assertIn("a size or a digest is shown",
                      page_problems(self.html + "<p><code>0123456789abcdef</code></p>", self.view))

    def test_known_wrong_a_missing_or_folded_kind_is_found(self):
        html = re.sub(r'<tr data-harness-kind="hook">[\s\S]*?</tr>', "", self.html, count=1)
        self.assertIn("the counts do not name every harness kind the view serves", page_problems(html, self.view))
        folded = self.html.replace('data-harness-kind="hook"', 'data-harness-kind="tool"', 1)
        self.assertIn("a count folds harness kinds into the served kinds", page_problems(folded, self.view))

    def test_known_wrong_a_withdrawal_without_its_note_is_found(self):
        html = self.html.replace("Withdrawn after a measured drop.", "")
        self.assertIn("a withdrawal is shown without its note", page_problems(html, self.view))

    def test_known_wrong_a_named_backend_is_found(self):
        html = self.html + "<p>Installed vector method: deterministic_character_hash.</p>"
        self.assertIn("the page names how search works", page_problems(html, self.view))


if __name__ == "__main__":
    unittest.main()
