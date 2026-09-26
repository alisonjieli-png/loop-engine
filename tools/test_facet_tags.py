"""The facet vocabulary is the pinned occupation grid plus declared lists, the slot is catalogued, and the facets
reach the signed-in table and the search hits but never the public pages (roadmap S-6.209).

Known-wrong cases: a title absent from the pinned grid and the seeds, an industry without its description line,
a facet name the schema would refuse, a public page module that names a facet, and a signed-in filter without
its select. The engine's own known-wrong cases and mutants are in core.library_ingestion.facet_tag_checks.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(HERE), str(ROOT / "src")]

from loop_engine.core.library_ingestion import engines, facet_tag_checks  # noqa: E402
from loop_engine.core.library_ingestion.facet_tags import (  # noqa: E402
    FACET_ATTRIBUTES, FACETS, JOB_TITLES, INDUSTRIES, FacetMaterial, RulesFacetTagger, facet_vocabulary)
from loop_engine.core.library_ingestion.selection import select_engines  # noqa: E402
from loop_engine.core.service_runtime import catalogue_attributes as attributes  # noqa: E402
from loop_engine.core.service_runtime.catalogue_schema import CatalogueAttributeSchema, attribute_name_refusal  # noqa: E402

GRID = ROOT / "artifacts/occupation-grid-research-2026-09-22"
DATA = ROOT / "src/loop_engine/data"
WEB = ROOT / "src/loop_engine/core/service_runtime/web_assets"
#: The public page modules: they read harness_kind and never a facet.
PUBLIC_PAGES = ("library_page.py", "web_pages.py", "web_chrome.py", "red_team_page.py", "public_links.py",
                "model_directory_pages.py")


def names_a_facet(source: str, facet: str) -> bool:
    """Whether code names a facet as an attribute key: the quoted name, as a page would read it from a row.
    Prose may use the plain word (the red team page counts severity levels), so a bare word is not a finding."""
    return re.search(rf"""["']{facet}["']""", source) is not None
FACET_SELECTS = {"job_titles": "browse-job-title", "industries": "browse-industry", "levels": "browse-level",
                 "languages": "browse-language", "geographies": "browse-geography"}
NODE = shutil.which("node")
#: Loads the page module without a page (it only defines window.BaltorCatalogueBrowser) and runs its facet
#: functions on the rows and choices it is given on standard input.
FACET_RULES_SCRIPT = r"""
const vm = require("node:vm"), fs = require("node:fs");
const given = JSON.parse(fs.readFileSync(0, "utf8")), context = {window: {}};
vm.createContext(context);
vm.runInContext(given.source, context);
const rules = context.window.BaltorCatalogueBrowser;
process.stdout.write(JSON.stringify({
  facets: rules.facets,
  choices: Object.fromEntries(given.names.map(name => [name, rules.facetChoices(given.rows, name)])),
  kept: given.choices.map(chosen => given.rows.filter(row => rules.keepsFacets(row, chosen)).map(row => row.identity))}));
"""
FACET_ROWS = [
    {"identity": "a", "attributes": {"job_titles": ["Lawyers"], "industries": ["legal"], "languages": ["english"]}},
    {"identity": "b", "attributes": {"industries": ["healthcare", "legal"], "languages": ["english"]}},
    {"identity": "c", "attributes": {"languages": ["spanish"]}},
    {"identity": "d", "attributes": {"industries": "legal"}},
    {"identity": "e"},
]
FACET_CHOICES = [[["industries", "legal"]], [["industries", "legal"], ["job_titles", "Lawyers"]],
                 [["industries", ""], ["job_titles", ""]], [["languages", "spanish"]]]


def run_facet_rules(source: str) -> dict:
    given = {"source": source, "rows": FACET_ROWS, "choices": FACET_CHOICES, "names": list(FACETS)}
    done = subprocess.run([NODE, "-e", FACET_RULES_SCRIPT], input=json.dumps(given), capture_output=True,
                          text=True, timeout=60, check=True)
    return json.loads(done.stdout)


def pinned_titles() -> dict:
    """Every title of the pinned grid with its code, from both dated inventories of the same source digest."""
    found = {}
    digests = set()
    for name in ("task-opportunities-expanded.json", "task-opportunities.json"):
        record = json.loads((GRID / name).read_text(encoding="utf-8"))
        digests.add(record["source"]["sha256"])
        for row in record["occupations"]:
            found.setdefault(row["occupation_title"], row["occupation_code"])
    assert len(digests) == 1, digests
    return found


class FacetVocabularyTest(unittest.TestCase):
    def test_every_job_title_comes_from_the_pinned_grid_or_the_packaged_seeds_with_its_code(self):
        grid = pinned_titles()
        seeds = {row["title"]: row["code"]
                 for row in yaml.safe_load((DATA / "occupation_seeds.yaml").read_text(encoding="utf-8"))["occupations"]}
        record = yaml.safe_load((DATA / "library_facets.yaml").read_text(encoding="utf-8"))
        entries = record["facets"][JOB_TITLES]["values"]
        for entry in entries:
            source = grid if entry["source"] == "grid" else seeds
            self.assertEqual(source.get(entry["value"]), entry["code"], entry)
        declared = {entry["value"] for entry in entries}
        self.assertEqual(declared & set(grid), set(grid), "every pinned grid title is declared")
        # A seed the grid already holds in the plural is served under the grid's title, not twice.
        folded = {title for title in seeds if title + "s" in grid}
        self.assertEqual(folded, {"Customer Service Representative", "Database Administrator"})
        self.assertEqual(set(seeds) - folded, declared - set(grid))
        self.assertNotIn("Dancers", declared)

    def test_the_industry_list_is_about_thirty_entries_each_with_a_description_line(self):
        record = yaml.safe_load((DATA / "library_facets.yaml").read_text(encoding="utf-8"))
        entries = record["facets"][INDUSTRIES]["values"]
        self.assertTrue(30 <= len(entries) <= 40, len(entries))
        for entry in entries:
            self.assertTrue(entry["description"].strip(), entry["value"])
            self.assertNotIn("\n", entry["description"])
            self.assertEqual(entry["value"], entry["value"].lower())

    def test_the_engine_checks_pass_with_their_mutants(self):
        result = facet_tag_checks.self_test()
        self.assertTrue(result["all_passed"], [test for test in result["tests"] if not test["passed"]])
        self.assertGreaterEqual(sum(test["test"].startswith("removed_") for test in result["tests"]), 4)


class FacetAttributeTest(unittest.TestCase):
    def test_the_facet_attributes_are_well_known_valid_and_never_reserved(self):
        for facet in FACETS:
            self.assertEqual(attribute_name_refusal(facet), "", facet)
        self.assertEqual(attributes.WELL_KNOWN_ATTRIBUTE_NAMES[-5:], FACETS)
        schema = CatalogueAttributeSchema.from_dict(attributes.declare({"record_type": "catalogue_attribute_schema/v1",
                                                                        "attributes": []}))
        values = schema.validate_values({"job_titles": ["Software Developers", "Lawyers"], "levels": ["lead"]})
        self.assertEqual(schema.filter_request({"job_titles": {"any_of": ["Lawyers"]}}),
                         (("job_titles", "any_of", ("Lawyers",)),))
        self.assertEqual(schema.shown_values(values), values)
        self.assertEqual([attribute["name"] for attribute in FACET_ATTRIBUTES], list(FACETS))

    def test_the_slot_is_catalogued_and_selects_the_rules_engine_without_authority(self):
        catalogue = yaml.safe_load((DATA / "engine_slots.yaml").read_text(encoding="utf-8"))
        [slot] = [slot for slot in catalogue["slots"] if slot["slot_id"] == "library_facet_tagging"]
        self.assertEqual(slot["engine_kinds"], ["facet_tagger"])
        self.assertEqual(slot["roadmap_steps"], ["S-6.209"])
        self.assertEqual(slot["conformance_suite"], "core.library_ingestion.facet_tag_checks")
        self.assertIn("library_facet_tagging", [slot.slot_id for slot in engines.SLOTS])
        decision, chosen = select_engines(engines.FACET_SLOT, engines.FACTORIES["library_facet_tagging"], {})
        self.assertEqual(decision["chosen"], ["facet_rules"])
        self.assertFalse(decision["authority_granted"])
        self.assertIs(chosen[0], RulesFacetTagger)
        rows = yaml.safe_load((DATA / "component_interactions.yaml").read_text(encoding="utf-8"))["interactions"]
        [row] = [row for row in rows if row["interaction_id"] == "core.interaction.library.tag_facets"]
        self.assertEqual((row["request_contract"], row["result_contract"]), ("facet_material/v1", "facet_tags/v1"))


class FacetSurfaceTest(unittest.TestCase):
    def test_the_signed_in_table_and_the_search_hits_carry_every_facet_and_the_public_pages_none(self):
        browser = (WEB / "catalogue-browser.js").read_text(encoding="utf-8")
        page = (WEB / "index.html").read_text(encoding="utf-8")
        service = (WEB / "service.js").read_text(encoding="utf-8")
        for facet, select in FACET_SELECTS.items():
            self.assertIn(f'"{facet}", "{select}"', browser, facet)
            self.assertRegex(page, rf'<select id="{select}"', select)
            self.assertIn(f'facet("{facet}")', service, facet)
        # Known-wrong: a page that reads a facet from a row is caught; the prose word alone is not a finding.
        self.assertTrue(names_a_facet('shown = row["attributes"]["industries"]', "industries"))
        self.assertTrue(names_a_facet("attributes.get('levels')", "levels"))
        self.assertFalse(names_a_facet("the harm would be on three levels", "levels"))
        for name in PUBLIC_PAGES:
            source = (ROOT / "src/loop_engine/core/service_runtime" / name).read_text(encoding="utf-8")
            for facet in FACETS:
                self.assertFalse(names_a_facet(source, facet), f"{name} names {facet}")

    @unittest.skipUnless(NODE, "node is not installed")
    def test_the_table_keeps_only_rows_that_carry_every_chosen_facet_value(self):
        browser = (WEB / "catalogue-browser.js").read_text(encoding="utf-8")
        result = run_facet_rules(browser)
        self.assertEqual([[name, select] for name, select, _label, _empty in result["facets"]],
                         [[name, FACET_SELECTS[name]] for name in FACETS])
        # The choices are the values the loaded rows carry, once each, sorted; a value that is not a list is none.
        self.assertEqual(result["choices"], {"job_titles": ["Lawyers"], "industries": ["healthcare", "legal"],
                                             "levels": [], "languages": ["english", "spanish"], "geographies": []})
        # Known-wrong: a row without the facet, or with a bare string for it, is not kept by a chosen value.
        self.assertEqual(result["kept"], [["a", "b"], ["a"], ["a", "b", "c", "d", "e"], ["c"]])
        # The table applies these functions: the filter and the select choices both go through them.
        self.assertIn("facetRules.keepsFacets(row, wanted)", browser)
        self.assertIn("facetRules.facetChoices(listed, name)", browser)
        # Removed guard: a module that keeps every row whatever is chosen fails the same comparison.
        rule = "!value || this.facetValues(row, name).includes(value)"
        self.assertEqual(browser.count(rule), 1)
        broken = run_facet_rules(browser.replace(rule, "true"))
        self.assertNotEqual(broken["kept"], result["kept"])
        self.assertEqual(broken["kept"][0], ["a", "b", "c", "d", "e"])

    def test_a_tagged_item_keeps_its_evidence_for_a_hand_check(self):
        tags = RulesFacetTagger().tag(FacetMaterial("skill", "skill", "payroll-audit",
                                                    "Reconcile payroll for accountants in Canada.", "", ()))
        self.assertEqual(tags.values["industries"][0], "accounting")
        self.assertEqual(tags.values["job_titles"], ("Accountants and Auditors",))
        self.assertEqual(tags.values["geographies"], ("Canada",))
        self.assertIn(("job_titles", "Accountants and Auditors", "name or purpose: accountants"), tags.evidence)
        self.assertGreaterEqual(len(facet_vocabulary().values["geographies"]), 80)


if __name__ == "__main__":
    unittest.main()
