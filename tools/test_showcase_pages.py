"""The demonstration page and the case studies say only what this release and the saved evidence say.

Kind: development check over packaged files. It reads the served page source, reruns every search the
demonstration shows through the same host loader and retrieval route the service uses (as
`tools/test_homepage_demonstration.py` does for the homepage), reads the native skill locations of
`tools/install_selected_material.py`, and reads the evidence files each case study names. Nothing here
reaches the network; the searches run on loopback over a temporary database.

The demonstration at `/demo` breaks one data cleanup task into five steps. Each step shows a search, the
references it returned, a download of the one it chose and the folder where the harness reads it. The
search and the download are recorded from this release's library and say so; the folder is an example and
says so. Each rule below refuses one way the page could stop being true, and each has known-wrong pages
beside it that the rule must report:

- every shown reference is what a real search of this release's library returns for that step's query, in
  the same place, with the same kind, licence, size and digest, and the download names the chosen one;
- the search and the download carry the recorded label and the folder the example label, and no label
  carries a retired status word;
- each folder places the downloaded skill under its native name, and the folder roots the page script
  offers for Claude Code, Codex, OpenCode and Pi are the ones the placement tool uses;
- no step chooses an item that a recorded measurement found harmful;
- every number a case study shows appears in the evidence files the case study names, and each named
  evidence file exists.
"""
from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_homepage_demonstration import (  # noqa: E402
    ASSETS, LABEL_WORDS, PAGE, RETIRED_STATUS, read_marked, recorded_harm, release_search, released_items, shown_size,
)
from install_selected_material import CLIENT_LAYOUT_PROFILES, native_name  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ASSETS / "public-pages.js"
#: The harnesses whose folders the page shows, each by its placement profile.
HARNESSES = ("claude-code", "codex", "opencode", "pi")
#: The harness whose folder the page shows before its script runs.
DEFAULT_HARNESS = "claude-code"
#: The fewest steps the task is broken into, and the references each step shows.
STEP_COUNT, SHOWN_RESULTS = 5, 2
#: A number as a reader sees it: digits, with the dots, commas and colons inside it.
NUMBER = re.compile(r"\d+(?:[.,:]\d+)*")
CASE_STUDY_VIEW = re.compile(r'^\s{4}<section data-view="(case-studies-[a-z0-9-]+)"[^>]*\bdata-evidence="([^"]+)"', re.M)
VIEW_LINE = re.compile(r'^\s{4}<section data-view="', re.M)


@dataclass
class Step:
    """One step of the demonstration as the page shows it."""

    name: str
    query: str
    results: list
    download: str
    labels: dict
    skill_root: str
    skill_name: str


def read_steps(page):
    """The steps of the demonstration, read from the served page source."""
    found = read_marked(page, "data-task-demo")

    def nearest(element, name):
        return next((attrs[name] for attrs in reversed(element["ancestors"]) if name in attrs), None)

    steps = []
    for article in sorted((item for item in found if "data-task-step" in item["attrs"]),
                          key=lambda item: page.find('data-task-step="' + item["attrs"]["data-task-step"] + '"')):
        name = article["attrs"]["data-task-step"]
        inside = [item for item in found if nearest(item, "data-task-step") == name]
        text = lambda attribute: next((" ".join(item["text"].split()) for item in inside if attribute in item["attrs"]), "")
        results = []
        ordered = [item for item in inside if "data-demo-item" in item["attrs"]]
        # The reader records an element when it closes; the page order is the order of the identities in the step's markup.
        markup = page[page.find('data-task-step="' + name + '"'):]
        ordered.sort(key=lambda item: markup.find('data-demo-item="' + item["attrs"]["data-demo-item"] + '"'))
        for item in ordered:
            identity = item["attrs"]["data-demo-item"]
            facts = {fact["attrs"]["data-fact"]: " ".join(fact["text"].split()) for fact in inside
                     if "data-fact" in fact["attrs"] and nearest(fact, "data-demo-item") == identity}
            results.append({"identity": identity, "chosen": "is-chosen" in item["attrs"].get("class", "").split(), **facts})
        labels = {}
        for item in inside:
            if "data-task-label" in item["attrs"]:
                stage = nearest(item, "data-task-stage") or ""
                labels[stage] = (item["attrs"]["data-task-label"], " ".join(item["text"].split()))
        stages = {item["attrs"]["data-task-stage"]: item["attrs"].get("data-task-evidence", "") for item in inside
                  if "data-task-stage" in item["attrs"]}
        head = labels.get("", ("", ""))
        steps.append(Step(name, text("data-task-query"), results,
                          next((item["attrs"]["data-demo-download"] for item in inside if "data-demo-download" in item["attrs"]), ""),
                          {stage: (evidence, labels.get(stage, head)) for stage, evidence in stages.items()},
                          text("data-task-skill-root"), text("data-task-skill-name")))
    return steps


def search_problems(steps, searches):
    """Each step shows what a real search of this release's library returns, in order, and downloads the chosen one."""
    problems = [] if len(steps) >= STEP_COUNT else [f"the demonstration shows {len(steps)} steps"]
    for step in steps:
        hits = searches.get(step.query, [])
        if len(step.results) != SHOWN_RESULTS:
            problems.append(f"{step.name}: the step shows {len(step.results)} references")
        for place, (item, hit) in enumerate(zip(step.results, hits), start=1):
            where = f"{step.name}, reference {place}"
            if item["identity"] != hit["identity"]:
                problems.append(f"{where}: the page shows {item['identity']} and the search returns {hit['identity']}")
                continue
            for fact, expected in (("kind", hit["kind"]), ("licence", hit["license"]), ("size", shown_size(hit["size_bytes"]))):
                if item.get(fact) != expected:
                    problems.append(f"{where}: the page shows {fact} {item.get(fact)!r} and this release has {expected!r}")
            shown = item.get("digest", "")
            if not re.fullmatch(r"[0-9a-f]{8,64}", shown) or not hit["sha256"].startswith(shown):
                problems.append(f"{where}: the page shows sha256 {shown or '(nothing)'} and this release has {hit['sha256']}")
        if len(hits) < len(step.results):
            problems.append(f"{step.name}: the search returned {len(hits)} references")
        chosen = [item["identity"] for item in step.results if item["chosen"]]
        if chosen != [step.download] or not step.results or step.results[0]["identity"] != step.download:
            problems.append(f"{step.name}: the step downloads {step.download or '(nothing)'} and marks {chosen} as chosen")
    return problems


def label_problems(steps):
    """The search and the download say they are recorded; the folder says it is an example layout."""
    wanted = {"search": "recorded", "download": "recorded", "folder": "illustration"}
    problems = []
    for step in steps:
        for stage, evidence in wanted.items():
            declared, (label, words) = step.labels.get(stage, ("", ("", "")))
            if declared != evidence or label != evidence or LABEL_WORDS[evidence] not in words or RETIRED_STATUS.search(words):
                problems.append(f"{step.name}: the {stage} part says {words or '(nothing)'!r} and must say {LABEL_WORDS[evidence]!r}")
    return problems


def script_roots(source):
    """The folder roots the page script offers, by harness."""
    found = re.search(r"const SKILL_ROOTS = (\{[^}]*\});", source)
    return json.loads(found.group(1)) if found else {}


def placement_problems(steps, roots):
    """Each folder places the downloaded skill under its native name, at the roots the placement tool uses."""
    problems = []
    expected = {kind: "/".join(CLIENT_LAYOUT_PROFILES[kind].location_for("skill").directory_segments) + "/" for kind in HARNESSES}
    if roots != expected:
        problems.append(f"the page script offers the roots {roots} and the placement tool uses {expected}")
    for step in steps:
        if step.skill_root != expected[DEFAULT_HARNESS]:
            problems.append(f"{step.name}: the folder shows the root {step.skill_root!r} before the script runs")
        if not step.download or step.skill_name != native_name(step.download):
            problems.append(f"{step.name}: the folder places {step.skill_name!r} and the step downloads {step.download!r}")
    return problems


def harm_problems(steps, harmful):
    """No step chooses an item that a recorded measurement found harmful."""
    return [f"{step.name}: chooses {step.download}, which a recorded measurement found harmful: {'; '.join(harmful[step.download])}"
            for step in steps if step.download in harmful]


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def visible_text(markup):
    reader = _Text()
    reader.feed(markup)
    return " ".join(" ".join(reader.parts).split())


def case_studies(page):
    """Each case study view: its name, the evidence files it names and its text."""
    studies = []
    for found in CASE_STUDY_VIEW.finditer(page):
        following = VIEW_LINE.search(page, found.end())
        markup = page[found.start():following.start() if following else len(page)]
        studies.append((found.group(1), found.group(2).split(), visible_text(markup)))
    return studies


def plain_numbers(text):
    """The numbers of a text, with the commas that group thousands taken out."""
    return re.sub(r"(?<=\d),(?=\d{3}\b)", "", text)


def number_problems(name, text, evidence):
    """Every number the page shows is a number of one of its evidence files.

    Numbers are compared whole, so 11 is not found inside 011 or 2011. A page may shorten a time or a
    version at one of its own separators: 13:03 is the evidence's 13:03:54.
    """
    held = set(NUMBER.findall(plain_numbers(evidence)))
    found = lambda number: number in held or any(value.startswith(number + mark) for value in held for mark in ":.")
    return [f"{name}: shows {number}, which none of its evidence files holds"
            for number in dict.fromkeys(NUMBER.findall(plain_numbers(text))) if not found(number)]


def evidence_of(paths):
    missing = [path for path in paths if not (ROOT / path).is_file() or not (ROOT / path).read_text(encoding="utf-8").strip()]
    return missing, "\n".join((ROOT / path).read_text(encoding="utf-8") for path in paths if path not in missing)


class DemonstrationPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = PAGE.read_text(encoding="utf-8")
        cls.steps = read_steps(cls.page)
        cls.searches = {step.query: release_search(step.query) for step in cls.steps if step.query}
        cls.items, _count = released_items()

    def test_each_step_shows_what_this_release_library_returns(self):
        self.assertEqual(search_problems(self.steps, self.searches), [])
        self.assertGreaterEqual(len(self.steps), STEP_COUNT)
        first = self.steps[0]
        # KNOWN_WRONG: a digest changed by one character, two references swapped, and a download of the second reference.
        digest = first.results[0]["digest"]
        changed = [Step(first.name, first.query, [{**first.results[0], "digest": digest[:-1] + ("0" if digest[-1] != "0" else "1")},
                                                  first.results[1]], first.download, first.labels, first.skill_root, first.skill_name)]
        swapped = [Step(first.name, first.query, list(reversed(first.results)), first.download, first.labels, first.skill_root, first.skill_name)]
        other = [Step(first.name, first.query, first.results, first.results[1]["identity"], first.labels, first.skill_root, first.skill_name)]
        for wrong in (changed, swapped, other):
            self.assertTrue(search_problems(wrong + self.steps[1:], self.searches))
        # PLANTED: a digest changed in the page source itself, the way a stale page would serve it.
        planted = self.page.replace('data-fact="digest">' + digest + "<", 'data-fact="digest">' + digest[:-1] + ("0" if digest[-1] != "0" else "1") + "<", 1)
        self.assertNotEqual(planted, self.page)
        self.assertTrue(search_problems(read_steps(planted), self.searches))

    def test_each_part_says_whether_it_is_recorded_or_an_example(self):
        self.assertEqual(label_problems(self.steps), [])
        # PLANTED: a folder called recorded, and a folder label that carries a retired status word.
        called = self.page.replace('data-task-label="illustration">Example layout<', 'data-task-label="recorded">Recorded from this release\'s library<', 1)
        building = self.page.replace('data-task-label="illustration">Example layout<', 'data-task-label="illustration">Example layout, being built<', 1)
        for planted in (called, building):
            self.assertNotEqual(planted, self.page)
            self.assertEqual(len(label_problems(read_steps(planted))), 1)

    def test_each_folder_uses_the_placement_tool_roots_and_names(self):
        roots = script_roots(SCRIPT.read_text(encoding="utf-8"))
        self.assertEqual(placement_problems(self.steps, roots), [])
        # KNOWN_WRONG: a root the placement tool does not use, and a folder named for another item.
        self.assertEqual(len(placement_problems(self.steps, {**roots, "codex": ".codex/skills/"})), 1)
        first = self.steps[0]
        renamed = [Step(first.name, first.query, first.results, first.download, first.labels, first.skill_root,
                        native_name(first.results[1]["identity"]))]
        self.assertEqual(len(placement_problems(renamed, roots)), 1)

    def test_no_step_chooses_an_item_a_measurement_found_harmful(self):
        harmful = recorded_harm()
        self.assertTrue(harmful)
        self.assertEqual(harm_problems(self.steps, harmful), [])
        # KNOWN_WRONG: a step that downloads the item the data cleanup study found harmful.
        first = self.steps[0]
        chose = [Step(first.name, first.query, first.results, sorted(harmful)[0], first.labels, first.skill_root, first.skill_name)]
        self.assertEqual(len(harm_problems(chose, harmful)), 1)


class CaseStudyPages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.studies = case_studies(PAGE.read_text(encoding="utf-8"))

    def test_there_are_three_case_studies_each_naming_its_evidence(self):
        self.assertEqual([name for name, _paths, _text in self.studies],
                         ["case-studies-data-cleanup", "case-studies-pi-and-gemma-4", "case-studies-sign-up-protection"])
        for name, paths, _text in self.studies:
            with self.subTest(study=name):
                self.assertEqual(evidence_of(paths)[0], [])
        # KNOWN_WRONG: an evidence file that does not exist.
        self.assertEqual(evidence_of(["case-studies/no-such-report.md"])[0], ["case-studies/no-such-report.md"])

    def test_every_number_on_a_case_study_is_in_its_evidence(self):
        for name, paths, text in self.studies:
            with self.subTest(study=name):
                self.assertEqual(number_problems(name, text, evidence_of(paths)[1]), [])
        name, paths, text = self.studies[0]
        evidence = evidence_of(paths)[1]
        # KNOWN_WRONG: an invented improvement, a changed score and a number from another study.
        for planted in ("With the item, accuracy rose 97.3 percent.", text.replace("0.842", "0.924", 1) if "0.842" in text else "0.924",
                        "The check passed at 13:03 UTC."):
            with self.subTest(planted=planted[:40]):
                self.assertTrue(number_problems(name, text + " " + planted, evidence))


if __name__ == "__main__":
    unittest.main()
