"""The decision red team page at /case-studies/decision-red-team renders from its packaged record and nothing else.

Roadmap steps S-6.201 and S-6.198. The page is rendered by src/loop_engine/core/service_runtime/red_team_page.py from
the record that tools/build_showcase_page.py writes from the recorded runs. Each rule below refuses one way the page
could stop being true, and each has a known-wrong control:

- the packaged record is read by the typed reader, was built from the pinned scenario record, and is what the
  generator writes from the recorded runs today (a stale record fails);
- a record whose scenario digest differs from the pinned one is refused, and the refusal depends on its guard;
- a proceed answer on a business-framed request without a recorded failure, and totals that disagree with the
  rows, are refused;
- the page keeps the sentence that every row is a typed decision, names the recorded counts, shows no size or digest,
  uses no retired or runtime word, and every number on it is a number of the record;
- the site map lists the page, its hostname opens it at the root, the examples page links it, and the served head,
  view and hostname rules of the surface checks hold with the page in the chain.

    PYTHONPATH=src:tools python -m unittest tools/test_red_team_page.py
"""
from __future__ import annotations

import copy
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import unittest
from unittest import mock

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(HERE), str(ROOT / "src")]

import build_showcase_page as generator  # noqa: E402
import red_team_decisions as study  # noqa: E402
from loop_engine.core.service_runtime import red_team_page as page  # noqa: E402
from loop_engine.core.service_runtime import web_pages, web_surface_checks  # noqa: E402
from loop_engine.core.service_runtime.web_site_map import load_site_map  # noqa: E402

RUNS = [ROOT / "artifacts/decision-red-team-2026-09-25/run-2.json", ROOT / "artifacts/decision-red-team-2026-09-25/run-3.json"]
INDEX = ROOT / "src/loop_engine/core/service_runtime/web_assets/index.html"
WORDING_RULES = ROOT / "tools/public_wording_rules.mjs"
TERMINOLOGY = ROOT / "terminology.yaml"
#: A number as a reader sees it, with the separators a written number uses; the deck check uses the same pattern.
NUMBER = re.compile(r"(?<![A-Za-z0-9])\d+(?:[.,:]\d+)*")
#: The numbers a record holds, read without the letter guard so that a time inside a recorded moment (the T of
#: 2026-09-25T22:35:03) is held as 22:35:03.
RECORD_NUMBER = re.compile(r"\d+(?:[.,:]\d+)*")
SIZE_OR_DIGEST = re.compile(r"\b\d[\d,]* bytes\b|\bdigest\b|[0-9a-f]{12,}", re.IGNORECASE)
#: The counts the case study states, which the page must name: 15 of 15 for the rules in both runs, 14 of 15 and 9 of 15
#: for Gemma 4, and one recorded failure.
STATED = ("15 of 15", "14 of 15", "9 of 15", "1 recorded failure", "did not refer a person seeking help", "was not measured")


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.skipped = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skipped += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skipped -= 1

    def handle_data(self, data):
        if not self.skipped:
            self.parts.append(data)


def view_words(body: bytes) -> str:
    """The words a reader sees in the page's own view, without the shared header and footer."""
    found = re.search(r'<section data-view="' + page.VIEW + r'"[\s\S]*?</section>', body.decode("utf-8"))
    reader = _Text()
    reader.feed(found.group(0) if found else "")
    return " ".join(" ".join(reader.parts).split())


def wording_rules() -> dict:
    """The retired and runtime words of the public pages: terminology.yaml and the shared browser rules."""
    rules = {}
    vocabulary = yaml.safe_load(TERMINOLOGY.read_text("utf-8"))["vocabulary"]
    for name, term in vocabulary.items():
        if isinstance(term, dict) and term.get("pattern") and "public_website_pages" in (term.get("must_not_appear") or ()):
            rules[name] = re.compile(term["pattern"], 0 if term.get("case_sensitive") else re.IGNORECASE)
    source = WORDING_RULES.read_text("utf-8")
    for name in ("internalTerms", "publicVocabulary", "retiredAccessWords", "invitationWords", "cardStatusWords"):
        found = re.search(r"^export const " + name + r"=/(.+)/([a-z]*);$", source, re.MULTILINE)
        rules[name] = re.compile(found.group(1), re.IGNORECASE if "i" in found.group(2) else 0)
    return rules


def fresh_record() -> dict:
    return generator.build_record([generator.load_run(path) for path in RUNS], study.load_scenarios(study.DEFAULT_SCENARIOS))


class PackagedRecord(unittest.TestCase):
    def test_the_packaged_record_is_pinned_and_is_what_the_generator_writes(self):
        record = page.load_page_record()
        self.assertEqual(record.value["scenarios_sha256"], page.PINNED_SCENARIOS_SHA256)
        self.assertEqual(page.PINNED_SCENARIOS_SHA256, study.SCENARIOS_SHA256)
        self.assertEqual([run["run_id"] for run in record.runs],
                         ["decision-red-team-20260925T223503Z", "decision-red-team-20260925T224153Z"])
        packaged = (ROOT / "src/loop_engine/core/service_runtime/web_assets" / page.RECORD_FOLDER / page.RECORD_FILE).read_text("utf-8")
        self.assertEqual(packaged, generator.record_text(fresh_record()), "the packaged record is stale; run tools/build_showcase_page.py")

    def test_a_record_built_from_another_scenario_record_is_refused_by_its_guard(self):
        value = copy.deepcopy(page.load_page_record().value)
        value["scenarios_sha256"] = "0" * 64
        with self.assertRaisesRegex(page.RedTeamPageError, "scenario_record_not_pinned"):
            page.page_record_from_value(value)
        # Mutant control: without the guard, the same record is read.
        with mock.patch.object(page, "_check_pinned", lambda record: None):
            self.assertEqual(page.page_record_from_value(value).value["scenarios_sha256"], "0" * 64)
        # The generator refuses a run whose scenario record is not the pinned one before the page reader sees it.
        run = json.loads(RUNS[1].read_text("utf-8"))
        run["scenarios"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(generator.ShowcaseError, "run_scenarios_not_pinned"):
            generator.load_run(self._written(run))

    def _written(self, value):
        import tempfile
        folder = Path(tempfile.mkdtemp(prefix="red-team-page-"))
        path = folder / "run.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_a_proceed_without_a_recorded_failure_and_disagreeing_totals_are_refused(self):
        value = copy.deepcopy(page.load_page_record().value)
        row = next(item for item in value["runs"][1]["rows"] if item["engine_id"] == "tactical" and item["status"] == "answered")
        row["engine_action"] = value["policy"]["proceed_action"]
        row["failure"] = ""
        with self.assertRaisesRegex(page.RedTeamPageError, "proceed_without_a_recorded_failure"):
            page.page_record_from_value(value)
        with mock.patch.object(page, "_check_failures", lambda record: None):
            page.page_record_from_value(value)
        value = copy.deepcopy(page.load_page_record().value)
        value["runs"][1]["totals"]["tactical"]["checks_passed"] = 15
        with self.assertRaisesRegex(page.RedTeamPageError, "totals_disagree_with_rows"):
            page.page_record_from_value(value)
        with mock.patch.object(page, "_check_totals", lambda record: None):
            page.page_record_from_value(value)
        value = copy.deepcopy(page.load_page_record().value)
        value["decision_sentence"] = "The model wrote each answer."
        with self.assertRaisesRegex(page.RedTeamPageError, "decision_presented_as_text"):
            page.page_record_from_value(value)
        value = copy.deepcopy(page.load_page_record().value)
        value["record_type"] = "decision_red_team_page/v2"
        with self.assertRaises(page.RedTeamPageError):
            page.page_record_from_value(value)


class RenderedPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.body, cls.media = page.rendered(page.ADDRESS, "GET", "Baltor")
        cls.words = view_words(cls.body)

    def test_the_page_renders_from_the_packaged_record_with_the_stated_counts(self):
        self.assertEqual(self.media, web_pages.HTML_MEDIA_TYPE)
        text = self.body.decode("utf-8")
        self.assertEqual(text.count("<h1"), 1)
        self.assertIn('<section data-view="' + page.VIEW + '"', text)
        self.assertIn(page.DECISION_SENTENCE, self.words)
        self.assertEqual(study.page_violations(text), [])
        for stated in STATED:
            self.assertIn(stated, self.words)
        self.assertIn("Jev", self.words)
        self.assertEqual(SIZE_OR_DIGEST.findall(self.words), [])
        self.assertIsNone(page.rendered("/case-studies/other", "GET", "Baltor"))
        self.assertIsNone(page.rendered(page.ADDRESS, "POST", "Baltor"))
        # Known-wrong: the study's own page rule refuses a page that presents a decision as generated text.
        self.assertIn("decision_presented_as_text", study.page_violations(text.replace(page.DECISION_SENTENCE, "The model wrote each answer.")))

    def test_the_page_uses_no_retired_or_runtime_word(self):
        rules = wording_rules()
        found = {name: rule.search(self.words).group(0) for name, rule in rules.items() if rule.search(self.words)}
        self.assertEqual(found, {})
        # Known-wrong: a runtime word and a retired word are found.
        self.assertTrue(any(rule.search(self.words + " Built on Loop Engine.") for rule in rules.values()))
        self.assertTrue(any(rule.search(self.words + " Join the private beta.") for rule in rules.values()))

    def test_every_number_on_the_page_is_a_number_of_the_record(self):
        held = set(RECORD_NUMBER.findall(json.dumps(page.load_page_record().value, ensure_ascii=False)))
        found = lambda number: number in held or any(value.startswith(number + mark) for value in held for mark in ":.")
        missing = [number for number in dict.fromkeys(NUMBER.findall(self.words)) if not found(number)]
        self.assertEqual(missing, [])
        # Known-wrong: an invented count.
        self.assertFalse(found("97.3"))

    def test_the_hostname_root_serves_the_page_and_the_surface_rules_hold(self):
        site_map = load_site_map()
        entry = site_map.page(page.ADDRESS)
        self.assertIsNotNone(entry)
        self.assertEqual((entry.view, entry.group, entry.indexed), (page.VIEW, "Use cases", True))
        self.assertIn((page.HOSTNAME, page.ADDRESS), [(surface.hostname, surface.address) for surface in site_map.hostnames])
        self.assertIsNone(web_pages.served_asset("/", "GET", "Baltor", page.HOSTNAME),
                          "the address table serves the homepage at the root of a hostname whose page is rendered")
        root, _media = page.rendered("/", "GET", "Baltor", page.HOSTNAME)
        own, _media = page.rendered(page.ADDRESS, "GET", "Baltor", page.HOSTNAME)
        self.assertEqual(root, own)
        self.assertIn(b'<meta name="baltor-root-address" content="' + page.ADDRESS.encode() + b'">', root)
        serve = web_surface_checks._served()
        self.assertEqual(web_surface_checks.head_problems(site_map, serve), [])
        self.assertEqual(web_surface_checks.view_problems(site_map, serve), [])
        self.assertEqual(web_surface_checks.hostname_problems(site_map, serve), [])
        # Known-wrong: a chain that answers the homepage at every root, as the address table did until September 26, 2026.
        homepage = lambda address, host: serve("/", None)
        self.assertTrue(web_surface_checks.hostname_problems(site_map, homepage))

    def test_the_examples_page_links_the_study_without_switching_views(self):
        index = INDEX.read_text("utf-8")
        links = re.findall(r'<a[^>]*href="' + re.escape(page.ADDRESS) + r'"[^>]*>', index)
        self.assertEqual(len(links), 1)
        self.assertNotIn("data-page", links[0], "the page is not a view of the one-page app, so its link must load it")
        self.assertIn("four real cases", index)


if __name__ == "__main__":
    unittest.main()
