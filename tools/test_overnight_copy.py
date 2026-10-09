"""Focused regression controls for overnight copy, not proof of model outcomes.

These checks preserve usable local tools and distinguish an illustrative
timeline from accepted work. The claim patterns cover the removed assertions
and close regressions; they are not a general semantic truth evaluator.
"""
import json
from pathlib import Path
import re
import unittest

from test_homepage_demonstration import read_marked
from test_offering_copy import FUTURE_MARKETING, marketing_views, overnight_tools_problems

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "src/loop_engine/core/service_runtime"
PAGE = RUNTIME / "web_assets/index.html"
CLAIMS = {
    "promised_overnight_outcome": re.compile(
        r"\bsolve(?:s|d)?\s+(?:complex\s+)?problems?\s+overnight\b"
        r"|\b(?:guaranteed|guarantees?)\s+(?:accepted\s+)?(?:results?|outcomes?|success|completion)\b"
        r"|\byou(?:'ll| will)\s+(?:wake up|return)\s+to\s+(?:a\s+)?(?:finished|accepted|completed)\s+(?:task|work|result)", re.I),
    "automatic_acceptance": re.compile(
        r"\bindependent checks?\s+(?:will\s+)?accepts?\s+(?:each|every)\s+result\b"
        r"|\b(?:each|every)\s+result\s+is\s+automatically\s+(?:accepted|approved)\b"
        r"|\bautomatically\s+(?:accepts?|approves?)\s+(?:each|every|all)\s+(?:result|output)", re.I),
    "automatic_library_for_every_step": re.compile(
        r"\b(?:each|every)\s+step\s+(?:automatically\s+)?(?:asks?|queries?)\s+the\s+library\b"
        r"|\b(?:each|every)\s+step\s+automatically\s+(?:retrieves?|loads?|fetches?)\s+[^.]{0,80}\blibrary\b"
        r"|\bautomatically\s+(?:retrieves?|loads?|fetches?)\s+[^.]{0,80}\blibrary\b[^.]{0,80}\b(?:each|every)\s+step\b", re.I),
}


def claim_problems(text):
    compact = " ".join(text.split()).replace("’", "'")
    return [name for name, pattern in CLAIMS.items() if pattern.search(compact)]


def overnight_page_problems(page):
    problems = []
    # The shared reader joins adjacent text nodes. Insert tag-boundary spacing
    # so a heading followed immediately by a paragraph remains separate copy.
    rows = read_marked(re.sub(r">(?=<)", "> ", page))
    for row in rows:
        attributes = row["attrs"]
        if (attributes.get("data-use-case") == "overnight"
                or attributes.get("data-demo-card") == "overnight"
                or attributes.get("data-view") == "overnight"):
            problems.extend(claim_problems(row["text"]))
            if FUTURE_MARKETING.search(row["text"]):
                problems.append("future_feature_copy")
    examples = [row for row in rows if "data-overnight-example" in row["attrs"]]
    if len(examples) != 1:
        problems.append("one_explicitly_classified_example_required")
    else:
        example = examples[0]
        if example["attrs"]["data-overnight-example"] != "illustrative":
            problems.append("unproved_recorded_example")
        text = " ".join(example["text"].split())
        for fact in ("Example morning report", "Illustrative workflow", "not a recorded run", "outcomes are examples"):
            if fact not in text:
                problems.append("missing_example_scope:" + fact)
    return problems


class OvernightCopyTests(unittest.TestCase):
    def test_current_overnight_surfaces_distinguish_tools_examples_and_outcomes(self):
        self.assertEqual(overnight_page_problems(PAGE.read_text()), [])

    def test_actual_pages_reject_reintroduced_outcome_acceptance_or_retrieval_claims(self):
        page = PAGE.read_text()
        for claim in ("Solve complex problems overnight.", "An independent check accepts each result.",
                      "Every step asks the library for its files.", "Guaranteed accepted outcomes."):
            with self.subTest(claim=claim):
                wrong = page.replace('<div class="content-intro" data-band="overnight-intro">',
                                      '<p data-view="overnight">' + claim + '</p><div class="content-intro" data-band="overnight-intro">', 1)
                self.assertTrue(overnight_page_problems(wrong))

    def test_known_wrong_claims_are_refused_and_manual_review_remains_allowed(self):
        for category, statements in {
            "promised_overnight_outcome": ("Solve complex problems overnight", "Guaranteed results",
                                            "You will wake up to a finished task"),
            "automatic_acceptance": ("An independent check accepts each result before the next step",
                                      "Every result is automatically accepted", "Automatically approves every output"),
            "automatic_library_for_every_step": ("Every step asks the library for files",
                                                  "Each step automatically retrieves files from the library",
                                                  "Automatically fetches library files for every step"),
        }.items():
            for text in statements:
                with self.subTest(text=text):self.assertIn(category, claim_problems(text))
        for text in ("Review the artifacts before accepting results.", "Choose the files your task needs.",
                     "The queue holds interrupted attempts for review.", "Illustrative workflow, not a recorded run."):
            self.assertEqual(claim_problems(text), [])

    def test_example_labels_cannot_disappear_or_claim_a_recorded_run(self):
        page = PAGE.read_text()
        for old, replacement in (("Example morning report", "What you come back to"),
                                 ("Illustrative workflow", "Workflow"),
                                 ("not a recorded run", "a recorded run"),
                                 ('data-overnight-example="illustrative"', 'data-overnight-example="recorded"')):
            with self.subTest(old=old):
                self.assertTrue(old in page, old)
                self.assertTrue(overnight_page_problems(page.replace(old, replacement, 1)))

    def test_the_usable_preview_controls_prices_and_setup_paths_remain(self):
        page = PAGE.read_text()
        view = marketing_views(page)["overnight"]
        for fact in ("own model access", "call", "time", "checkpoints", "morning report", "$29 a month",
                     "machine that runs the job", "The local harness is free"):
            self.assertIn(fact, view)
        for row in read_marked(page):
            if "data-overnight-tools" in row["attrs"]:
                self.assertEqual(row["attrs"]["data-overnight-tools"], "local")
                self.assertEqual(overnight_tools_problems(row["text"]), [])
        for path in ('href="/overnight"', 'href="/get-started"', 'href="/setup#start-connect"',
                     'href="https://github.com/alisonjieli-png/loop-engine/blob/main/tools/OVERNIGHT-QUEUE.md"'):
            self.assertIn(path, page)

    def test_overnight_metadata_does_not_restore_the_outcome_promise(self):
        site = json.loads((RUNTIME / "web_site_map.json").read_text())
        entry = next(row for row in site["pages"] if row["address"] == "/overnight")
        self.assertEqual(claim_problems(entry["title"] + ". " + entry["description"]), [])
        self.assertIn("local", entry["description"].lower())
        self.assertIn("checkpoint", entry["description"].lower())
        self.assertIn("report", entry["description"].lower())


if __name__ == "__main__":
    unittest.main()
