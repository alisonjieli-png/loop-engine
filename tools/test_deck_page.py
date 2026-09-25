"""The deck at /deck: every number carries a source note and matches its record, and no retired or invitation word.

Kind: development check over packaged files. It reads the page that `web_pages.served_asset` serves at /deck, the
deck's script, the typed site map, the public wording rules (`tools/public_wording_rules.mjs`) and terminology.yaml. It starts no server, opens
no connection and needs no credential, so it runs with the other tools tests and under an empty environment.

The owner asked on September 24, 2026 for a deck at deck.baltor.ai whose content comes only from public facts backed
by saved evidence in the repository. Roadmap step S-6.36 asks for an adversarial fact check that catches a number,
comparison or customer claim without saved evidence. Each rule below refuses one way to break that:

- a number on a slide, written in digits or as a number word, that no fact element holds, or whose fact holds no
  single source note linking a record;
- a number that none of the records its fact names contains, a record that does not exist, a JSON pointer that
  does not resolve, and a record the visible source note does not link;
- a number in the title, the description or the text a shared link shows, where no source note can stand;
- a retired word, a word of an invitation-only service or a runtime word, in the page or in its script;
- a deck that the served address table, the site map or its hostname does not list, or whose shared-link picture
  is not the 1200 by 630 image it names.

Each rule has known-wrong decks beside it, built from a small fixture deck that passes every rule, and a mutant
control that removes the rule and requires its named check to fail. The browser suite reads the same number rule
from the rendered page in `tools/deck_checks.mjs`; a check below fails when the two copies of the rule differ.

    PYTHONPATH=src:tools python -m unittest tools/test_deck_page.py
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import struct
from typing import Callable
import unittest
from unittest import mock

import yaml

from loop_engine.core.service_runtime import web_pages
from loop_engine.core.service_runtime.web_site_map import load_site_map

ROOT = Path(__file__).resolve().parents[1]
DECK_ADDRESS, DECK_VIEW, DECK_HOSTNAME = "/deck", "deck", "deck.baltor.ai"
DECK_FILES = {"/deck": ("deck.html", "text/html"), "/assets/deck.css": ("deck.css", "text/css"),
              "/assets/deck.js": ("deck.js", "text/javascript"), "/assets/deck-card.png": ("deck-card.png", "image/png")}
CARD_ADDRESS, CARD_SIZE = "/assets/deck-card.png", (1200, 630)
CANONICAL = "https://baltor.ai/deck"
#: A visible source note links each record at this address, so a reader can open the record the number came from.
SOURCE_PREFIX = "https://github.com/alisonjieli-png/loop-engine/blob/main/"
#: The one file every page check imports its wording rules from (September 25, 2026).
WORDING_RULES = ROOT / "tools" / "public_wording_rules.mjs"
BROWSER_DECK_CHECKS = ROOT / "tools" / "deck_checks.mjs"
TERMINOLOGY = ROOT / "terminology.yaml"
#: A number: digits with the separators a written number uses. The same pattern is exported by tools/deck_checks.mjs.
NUMBER_PATTERN = r"(?<![A-Za-z0-9])\d+(?:[.,:]\d+)*"
#: Number words and their values; None where the word names no exact value. "one" is left out because it is also a
#: pronoun, so a claim that needs it is written with its numeral.
NUMBER_WORDS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
                "eleven": 11, "twelve": 12, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
                "seventy": 70, "eighty": 80, "ninety": 90, "hundred": 100, "hundreds": None, "thousand": 1000,
                "thousands": None, "million": 1_000_000, "millions": None, "billion": 1_000_000_000,
                "billions": None, "dozen": 12, "dozens": None, "half": 0.5, "twice": 2, "double": 2, "triple": 3}
NUMBER = re.compile(NUMBER_PATTERN + r"|\b(?:" + "|".join(NUMBER_WORDS) + r")\b", re.IGNORECASE)
#: The head texts a shared link or a search result shows. None of them can carry a source note.
HEAD_TEXTS = ('meta[name="description"]', 'meta[property="og:title"]', 'meta[property="og:description"]',
              'meta[property="og:image:alt"]', 'meta[name="twitter:title"]', 'meta[name="twitter:description"]')
#: The word rules of the public wording rules file, read from it so the deck and the browser checks never disagree.
SUITE_WORD_RULES = ("retiredAccessWords", "invitationWords", "publicVocabulary")
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class Element:
    """One element of a parsed page, with its text and its elements in order."""

    def __init__(self, tag, attrs, parent):
        self.tag, self.attrs, self.parent, self.children = tag, attrs, parent, []

    def walk(self):
        yield self
        for item in self.children:
            if isinstance(item, Element):
                yield from item.walk()

    def texts(self, skip=lambda element: False):
        """Every text of this element in order, leaving out whole elements that `skip` names."""
        for item in self.children:
            if isinstance(item, Element):
                if not skip(item):
                    yield from item.texts(skip)
            else:
                yield item

    def text(self, skip=lambda element: False):
        return " ".join(" ".join(self.texts(skip)).split())

    def classes(self):
        return set((self.attrs.get("class") or "").split())

    def ancestors(self):
        node = self.parent
        while node is not None:
            yield node
            node = node.parent


class _TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Element("#document", {}, None)
        self.open = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Element(tag, dict(attrs), self.open[-1])
        self.open[-1].children.append(node)
        if tag not in VOID:
            self.open.append(node)

    def handle_startendtag(self, tag, attrs):
        self.open[-1].children.append(Element(tag, dict(attrs), self.open[-1]))

    def handle_endtag(self, tag):
        for index in range(len(self.open) - 1, 0, -1):
            if self.open[index].tag == tag:
                del self.open[index:]
                return

    def handle_data(self, data):
        self.open[-1].children.append(data)


def parse(page: str) -> Element:
    builder = _TreeBuilder()
    builder.feed(page)
    builder.close()
    return builder.root


def is_note(element: Element) -> bool:
    return "deck-source" in element.classes()


def select_meta(document: Element, selector: str) -> str:
    """The content of the one meta element a simple attribute selector names, or an empty string."""
    name, value = re.fullmatch(r'meta\[(\w+(?::\w+)?)="([^"]+)"\]', selector).groups()
    return next((item.attrs.get("content") or "" for item in document.walk()
                 if item.tag == "meta" and item.attrs.get(name) == value), "")


@dataclass(frozen=True)
class Deck:
    """What a rule reads: the parsed page, the page script, the served files, the site map facts and the records."""

    document: Element
    script: str
    serve: Callable
    table: dict
    pages: dict
    hostnames: dict
    root: Path


def served_deck() -> Deck:
    """The deck this checkout serves, read through the service's own served address table and the typed site map."""
    site_map = load_site_map()

    def serve(address):
        answer = web_pages.served_asset(address, "GET", site_map.display_name)
        return None if answer is None else (answer[0], answer[1].split(";")[0])
    page = serve(DECK_ADDRESS)
    script = serve("/assets/deck.js")
    return Deck(parse(page[0].decode("utf-8") if page else ""), script[0].decode("utf-8") if script else "", serve,
                {address: value for address, value in web_pages.WEB_ASSETS.items()},
                {page.address: page.view for page in site_map.pages},
                {surface.hostname: surface.address for surface in site_map.hostnames}, ROOT)


# The rules. Each returns the problems it finds, as sentences a reader can act on.

def slides_of(document):
    return [item for item in document.walk() if "data-slide" in item.attrs]


def every_number_has_a_source_note(deck: Deck):
    problems = []
    for slide in slides_of(deck.document):
        def visit(element, fact):
            for item in element.children:
                if isinstance(item, Element):
                    if not is_note(item):
                        visit(item, item if "data-fact" in item.attrs else fact)
                    continue
                for found in NUMBER.finditer(item):
                    where = f"slide {slide.attrs.get('id', '?')}: {found.group(0)!r} in {' '.join(item.split())[:60]!r}"
                    notes = [node for node in fact.walk() if is_note(node)] if fact is not None else []
                    if fact is None:
                        problems.append(where + " stands in no data-fact element")
                    elif len(notes) != 1:
                        problems.append(where + f" has {len(notes)} source notes in its fact, not one")
                    elif not any(node.tag == "a" and node.attrs.get("href") for node in notes[0].walk()):
                        problems.append(where + " has a source note that links no record")
        visit(slide, slide if "data-fact" in slide.attrs else None)
    return problems


def _pointer(value, pointer):
    """The value a JSON pointer names (RFC 6901), or raise KeyError."""
    for part in pointer.split("/")[1:]:
        part = part.replace("~1", "/").replace("~0", "~")
        if isinstance(value, list):
            if not part.isdigit() or int(part) >= len(value):
                raise KeyError(part)
            value = value[int(part)]
        elif isinstance(value, dict) and part in value:
            value = value[part]
        else:
            raise KeyError(part)
    return value


def _value_of(token):
    word = token.lower()
    if word in NUMBER_WORDS:
        return NUMBER_WORDS[word]
    try:
        return float(token.replace(",", "")) if ":" not in token else None
    except ValueError:
        return None


def _in_text(token, text):
    """The token as a whole number in the text: not part of a longer number, in its written form or without commas."""
    if token.lower() in NUMBER_WORDS:
        return re.search(r"\b" + re.escape(token) + r"\b", text, re.IGNORECASE) is not None
    return any(re.search(r"(?<!\d)(?<!\d[.,])" + re.escape(form) + r"(?!\d)(?![.,]\d)", text)
               for form in {token, token.replace(",", "")})


def _matches(token, value):
    number = _value_of(token)
    if isinstance(value, bool) or value is None:
        return False
    if isinstance(value, (int, float)):
        return number is not None and float(value) == float(number)
    if isinstance(value, str):
        return _in_text(token, value)
    if isinstance(value, list):
        return number is not None and len(value) == number
    return False


def numbers_match_their_records(deck: Deck):
    problems = []
    for fact in (item for item in deck.document.walk() if "data-fact" in item.attrs):
        label = fact.text(is_note)[:48]
        bindings = (fact.attrs.get("data-evidence") or "").split()
        notes = [node for node in fact.walk() if is_note(node)]
        links = {node.attrs.get("href", "").split("#", 1)[0] for note in notes for node in note.walk() if node.tag == "a"}
        if not bindings:
            problems.append(f"fact {label!r} names no record in data-evidence")
        values = []
        for binding in bindings:
            path, _, pointer = binding.partition("#")
            record = (deck.root / path).resolve()
            if ".." in Path(path).parts or path.startswith("/") or not record.is_relative_to(deck.root.resolve()) or not record.is_file():
                problems.append(f"fact {label!r} names a record that does not exist: {path}")
                continue
            if SOURCE_PREFIX + path not in links:
                problems.append(f"fact {label!r} names {path}, and its source note does not link it")
            text = record.read_text("utf-8", errors="replace")
            if pointer:
                try:
                    values.append(("value", _pointer(json.loads(text), pointer)))
                except (KeyError, ValueError):
                    problems.append(f"fact {label!r} names {binding}, and that pointer does not resolve")
            else:
                values.append(("text", text))
        for found in NUMBER.finditer(fact.text(is_note)):
            token = found.group(0)
            if values and not any(_in_text(token, value) if kind == "text" else _matches(token, value) for kind, value in values):
                problems.append(f"fact {label!r}: {token!r} is in none of its records")
    return problems


def head_carries_no_number(deck: Deck):
    problems = []
    titles = [item.text() for item in deck.document.walk() if item.tag == "title"]
    for where, text in [("the title", title) for title in titles] + [(selector, select_meta(deck.document, selector)) for selector in HEAD_TEXTS]:
        found = NUMBER.search(text)
        if found:
            problems.append(f"{where} carries {found.group(0)!r}, and a number there can carry no source note")
    return problems


def suite_word_rules(source: str | None = None):
    """The public wording rules every page check imports, as compiled Python patterns.

    Until September 25, 2026 they were read from the browser suite, which then defined them; they moved to
    tools/public_wording_rules.mjs so no check keeps a copy of its own."""
    source = WORDING_RULES.read_text("utf-8") if source is None else source
    rules = {}
    for name in SUITE_WORD_RULES:
        found = re.search(r"^export const " + name + r"=/(.+)/([a-z]*);$", source, re.MULTILINE)
        if not found:
            raise ValueError(f"the public wording rules no longer define {name} as one regular expression on its own line")
        rules[name] = re.compile(found.group(1), re.IGNORECASE if "i" in found.group(2) else 0)
    return rules


def terminology_rules():
    """The words terminology.yaml refuses on the public pages: its retired words and its runtime words."""
    vocabulary = yaml.safe_load(TERMINOLOGY.read_text("utf-8"))["vocabulary"]
    return {name: re.compile(term["pattern"], 0 if term.get("case_sensitive") else re.IGNORECASE)
            for name, term in vocabulary.items()
            if isinstance(term, dict) and term.get("pattern") and "public_website_pages" in (term.get("must_not_appear") or ())}


def script_strings(source: str):
    """The strings a script can write into a page: its literals, without comments and lowercase names."""
    bare = re.sub(r"/\*[\s\S]*?\*/", " ", source)
    bare = re.sub(r"(^|[\s;{}()\[\],])//[^\n]*", r"\1", bare)
    found = re.findall(r'"((?:[^"\\\n]|\\.)*)"|\'((?:[^\'\\\n]|\\.)*)\'|`((?:[^`\\]|\\.)*)`', bare)
    return [next(part for part in parts if part is not None) for parts in found
            if not re.fullmatch(r"[a-z][a-z0-9]*(?:[-_.:/][a-z0-9]+)*", next(part for part in parts if part is not None) or "x")]


def reader_text(deck: Deck):
    """Everything a reader or a shared link shows: text, the head texts, labels and alternatives, and the script's words."""
    words = [deck.document.text(lambda element: element.tag in ("script", "style"))]
    words += [select_meta(deck.document, selector) for selector in HEAD_TEXTS]
    words += [item.attrs.get(name) or "" for item in deck.document.walk() for name in ("aria-label", "alt")]
    return "\n".join(words + script_strings(deck.script))


def no_retired_or_invitation_wording(deck: Deck, rules=None):
    rules = rules or {**suite_word_rules(), **terminology_rules()}
    text = reader_text(deck)
    return [f"the deck says {pattern.search(text).group(0)!r}, which the rule {name!r} refuses on a public page"
            for name, pattern in rules.items() if pattern.search(text)]


def deck_is_listed_and_served(deck: Deck):
    problems = []
    for address, (name, media) in DECK_FILES.items():
        if tuple(deck.table.get(address, ())) != (name, media):
            problems.append(f"the served address table does not serve {address} from {name} as {media}")
        answer = deck.serve(address)
        if answer is None or answer[1] != media:
            problems.append(f"{address} is not served as {media}")
    if deck.pages.get(DECK_ADDRESS) != DECK_VIEW:
        problems.append(f"the site map has no page {DECK_ADDRESS} shown by the view {DECK_VIEW!r}")
    if deck.hostnames.get(DECK_HOSTNAME) != DECK_ADDRESS:
        problems.append(f"the site map does not open {DECK_ADDRESS} at {DECK_HOSTNAME}")
    views = [item for item in deck.document.walk() if item.attrs.get("data-view") == DECK_VIEW]
    headings = [item for view in views for item in view.walk() if item.tag == "h1"
                and not any("hidden" in node.attrs for node in [item, *item.ancestors()])]
    if len(views) != 1 or len(headings) != 1:
        problems.append(f"the page has {len(views)} views named {DECK_VIEW!r} and {len(headings)} h1 headings in them, not one of each")
    canonical = next((item.attrs.get("href") for item in deck.document.walk() if item.tag == "link" and item.attrs.get("rel") == "canonical"), None)
    if canonical != CANONICAL:
        problems.append(f"the page names {canonical!r} as its canonical address, not {CANONICAL}")
    image = select_meta(deck.document, 'meta[property="og:image"]')
    if not image.startswith("https://") or not image.endswith(CARD_ADDRESS) or select_meta(deck.document, 'meta[name="twitter:card"]') != "summary_large_image":
        problems.append(f"the shared-link picture is {image!r}, not the absolute address of {CARD_ADDRESS} with a large card")
    card = deck.serve(CARD_ADDRESS)
    size = struct.unpack(">II", card[0][16:24]) if card and card[0][:8] == b"\x89PNG\r\n\x1a\n" else None
    if size != CARD_SIZE:
        problems.append(f"{CARD_ADDRESS} is {size}, not a PNG of {CARD_SIZE}")
    return problems


#: Every rule, by the name its checks report.
RULES = {
    "every_number_has_a_source_note": every_number_has_a_source_note,
    "numbers_match_their_records": numbers_match_their_records,
    "head_carries_no_number": head_carries_no_number,
    "no_retired_or_invitation_wording": no_retired_or_invitation_wording,
    "deck_is_listed_and_served": deck_is_listed_and_served,
}

# The fixture deck: a small deck that passes every rule, so that each known-wrong case changes one thing.
RELEASE = "artifacts/architecture-audit-2026-09-19/pilot-release-24.json"
REVIEWS = "examples/29_intelligence_service/starter-catalogue/reviews.json"
PNG_CARD = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + struct.pack(">II", *CARD_SIZE) + b"\x08\x02\x00\x00\x00"
FIXTURE_PAGE = (
    '<!doctype html><html lang="en"><head><title>Baltor | Deck</title>'
    '<meta name="description" content="A short deck on Baltor.">'
    '<link rel="canonical" href="https://baltor.ai/deck">'
    '<meta property="og:title" content="Baltor, the deck"><meta property="og:description" content="Every figure carries its source.">'
    '<meta property="og:image" content="https://baltor.ai/assets/deck-card.png"><meta name="twitter:card" content="summary_large_image">'
    '</head><body><main><section data-view="deck">'
    '<section data-slide id="cover"><h1>The right setup for every step.</h1><p class="lead">Reviewed material for each step.</p></section>'
    '<section data-slide id="live"><h2>Live today</h2>'
    f'<article data-fact data-evidence="{RELEASE}#/fly_release {REVIEWS}#/reviewers"><p class="stat">Release 24</p>'
    '<p>Each item approved by three reviewers.</p>'
    f'<p class="deck-source">Source: <a href="{SOURCE_PREFIX}{RELEASE}">the release record</a> and '
    f'<a href="{SOURCE_PREFIX}{REVIEWS}">reviews.json</a>, read on 2026-09-24</p></article>'
    '</section></section></main></body></html>')
FIXTURE_SCRIPT = 'const label = "Slide " + 1; element.className = "deck-overview-number";'


@dataclass(frozen=True)
class Fixture:
    """The parts of the fixture deck, each one replaceable by a known-wrong case."""

    page: str
    script: str
    files: dict
    table: dict
    pages: dict
    hostnames: dict

    def deck(self):
        files = {**self.files, DECK_ADDRESS: (self.page.encode("utf-8"), "text/html")}
        return Deck(parse(self.page), self.script, lambda address: files.get(address), self.table, self.pages, self.hostnames, ROOT)


def fixture():
    return Fixture(FIXTURE_PAGE, FIXTURE_SCRIPT,
                   {"/assets/deck.css": (b"", "text/css"), "/assets/deck.js": (FIXTURE_SCRIPT.encode(), "text/javascript"),
                    CARD_ADDRESS: (PNG_CARD, "image/png")},
                   dict(DECK_FILES),
                   {DECK_ADDRESS: DECK_VIEW}, {DECK_HOSTNAME: DECK_ADDRESS})


def _page(old, new):
    """A known-wrong case that changes one part of the fixture page."""
    def change(state):
        if old not in state.page:
            raise AssertionError(f"the fixture page has no {old!r}")
        return replace(state, page=state.page.replace(old, new, 1))
    return change


def _field(**changes):
    return lambda state: replace(state, **changes)


KNOWN_WRONG = {
    "every_number_has_a_source_note": (
        ("a number outside every fact", _page('<p class="lead">Reviewed material for each step.</p>', '<p class="lead">Used by 500 teams.</p>')),
        ("a number word outside every fact", _page('<p class="lead">Reviewed material for each step.</p>', '<p class="lead">Ten times cheaper.</p>')),
        ("a fact without its source note", _page(f'<p class="deck-source">Source: <a href="{SOURCE_PREFIX}{RELEASE}">', '<p class="other">Source: <a href="#">')),
        ("a source note that links nothing", _page(f'<a href="{SOURCE_PREFIX}{RELEASE}">the release record</a> and <a href="{SOURCE_PREFIX}{REVIEWS}">reviews.json</a>',
                                                   "the release record and reviews.json"))),
    "numbers_match_their_records": (
        ("a number its record does not hold", _page("Release 24", "Release 25")),
        ("a count its record does not hold", _page("approved by three reviewers", "approved by four reviewers")),
        ("a record that does not exist", _page(f"{RELEASE}#/fly_release", "artifacts/nowhere.json#/fly_release")),
        ("a pointer that does not resolve", _page(f"{RELEASE}#/fly_release", f"{RELEASE}#/release_that_is_not_there")),
        ("a record the source note does not link", _page(f'<a href="{SOURCE_PREFIX}{REVIEWS}">reviews.json</a>', "reviews.json")),
        ("a fact that names no record", _page(f'data-evidence="{RELEASE}#/fly_release {REVIEWS}#/reviewers"', 'data-evidence=""'))),
    "head_carries_no_number": (
        ("a number in the title", _page("<title>Baltor | Deck</title>", "<title>Baltor | 10x faster</title>")),
        ("a number in the description", _page('content="A short deck on Baltor."', 'content="Cut your token bill by 50 percent."')),
        ("a number word in the shared-link text", _page('content="Every figure carries its source."', 'content="Twice as fast as before."'))),
    "no_retired_or_invitation_wording": (
        ("a retired word", _page("<h2>Live today</h2>", "<h2>Join the private beta</h2>")),
        ("an invitation word", _page("<h2>Live today</h2>", "<h2>Request an invitation</h2>")),
        ("a phrase of an invitation-only service", _page("<h2>Live today</h2>", "<h2>Search is free while accounts open in small groups</h2>")),
        ("a runtime word", _page("<h2>Live today</h2>", "<h2>Built on Loop Engine</h2>")),
        ("a retired word in the script", _field(script=FIXTURE_SCRIPT + ' message("Join the waiting list");')),
        ("a retired word in a label", _page('<section data-slide id="cover">', '<section data-slide id="cover" aria-label="Early access">'))),
    "deck_is_listed_and_served": (
        ("the served address table drops the deck", _field(table={})),
        ("the site map drops the deck", _field(pages={})),
        ("the hostname opens another page", _field(hostnames={DECK_HOSTNAME: "/"})),
        ("two h1 headings", _page("<h2>Live today</h2>", "<h1>Live today</h1>")),
        ("another canonical address", _page('href="https://baltor.ai/deck"', 'href="https://baltor.ai/"')),
        ("a picture of the wrong size", lambda state: replace(state, files={**state.files, CARD_ADDRESS: (PNG_CARD[:16] + struct.pack(">II", 600, 600) + PNG_CARD[24:], "image/png")}))),
}


class DeckRules(unittest.TestCase):
    """Each rule reports its known-wrong decks, and the fixture deck passes every rule."""

    def test_the_fixture_deck_passes_every_rule(self):
        deck = fixture().deck()
        self.assertEqual({name: problems for name, rule in RULES.items() if (problems := rule(deck))}, {})

    def test_every_rule_has_known_wrong_cases(self):
        self.assertEqual(set(KNOWN_WRONG), set(RULES))
        self.assertTrue(all(len(cases) >= 3 for cases in KNOWN_WRONG.values()))

    def check_rule(self, name):
        for description, change in KNOWN_WRONG[name]:
            with self.subTest(case=description):
                self.assertTrue(RULES[name](change(fixture()).deck()), f"{name} did not report: {description}")

    def test_a_removed_rule_fails_its_named_check(self):
        """The mutant control: with one rule patched away, its own named check must fail once for each case."""
        for name, cases in KNOWN_WRONG.items():
            check = f"test_{name}_rejects_its_known_wrong_cases"
            with self.subTest(rule=name):
                intact = unittest.TestResult()
                DeckRules(check).run(intact)
                self.assertTrue(intact.wasSuccessful() and intact.testsRun == 1, f"{check} fails with its rule in place")
                with mock.patch.dict(RULES, {name: lambda deck: []}):
                    mutant = unittest.TestResult()
                    DeckRules(check).run(mutant)
                self.assertEqual(len(mutant.failures), len(cases), f"{check} survived the removal of {name}")
                self.assertEqual(mutant.errors, [])


for _name in RULES:
    setattr(DeckRules, f"test_{_name}_rejects_its_known_wrong_cases", lambda self, name=_name: self.check_rule(name))


class ServedDeck(unittest.TestCase):
    """The deck this checkout serves passes every rule, and the browser suite reads the same number rule."""

    @classmethod
    def setUpClass(cls):
        cls.deck = served_deck()

    def check_served(self, name):
        self.assertEqual(RULES[name](self.deck), [])

    def test_the_served_deck_has_slides_and_facts(self):
        slides = slides_of(self.deck.document)
        facts = [item for item in self.deck.document.walk() if "data-fact" in item.attrs]
        numbers = [found.group(0) for slide in slides for found in NUMBER.finditer(slide.text(is_note))]
        self.assertGreaterEqual(len(slides), 8)
        self.assertGreaterEqual(len(facts), 20)
        self.assertGreaterEqual(len(numbers), 40, "a deck whose numbers vanished would pass the number rules without proving anything")

    def test_the_browser_check_reads_the_same_number_rule(self):
        self.assertEqual(browser_number_rule(), (NUMBER_PATTERN, list(NUMBER_WORDS)))

    def test_the_rule_comparison_notices_a_changed_copy(self):
        source = BROWSER_DECK_CHECKS.read_text("utf-8")
        changed = source.replace('"twelve",', "", 1)
        self.assertNotEqual(changed, source)
        self.assertNotEqual(browser_number_rule(changed), (NUMBER_PATTERN, list(NUMBER_WORDS)))

    def test_the_word_rules_are_read_from_the_wording_rules_file_and_terminology(self):
        rules = {**suite_word_rules(), **terminology_rules()}
        for sentence in ("Join the private beta.", "Request an invitation", "Planned", "Search is free.", "Built on Loop Engine",
                         "Building with Loops", "early access"):
            with self.subTest(sentence=sentence):
                self.assertTrue(any(pattern.search(sentence) for pattern in rules.values()))
        with self.assertRaises(ValueError):
            suite_word_rules("export const retiredAccessWords = new RegExp('beta');")
        # A copy left in a page check is not the rule: only the exported definition counts.
        with self.assertRaises(ValueError):
            suite_word_rules("const retiredAccessWords=/beta/i;\nconst invitationWords=/invite/i;\nconst publicVocabulary=/Loop/i;")


def browser_number_rule(source: str | None = None):
    """The number pattern and the number words tools/deck_checks.mjs exports."""
    source = BROWSER_DECK_CHECKS.read_text("utf-8") if source is None else source
    pattern = re.search(r"^export const deckNumberPattern=String\.raw`([^`]+)`;$", source, re.MULTILINE)
    listed = re.search(r"^export const deckNumberWords=\[([^\]]+)\];$", source, re.MULTILINE | re.DOTALL)
    return (pattern.group(1) if pattern else None, re.findall(r'"([a-z]+)"', listed.group(1)) if listed else [])


for _name in RULES:
    setattr(ServedDeck, f"test_the_served_deck_{_name}", lambda self, name=_name: self.check_served(name))


if __name__ == "__main__":
    unittest.main()
