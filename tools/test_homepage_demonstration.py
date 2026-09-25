"""The homepage hero shows the working directory one step gets, and the homepage's facts are this release's.

Since September 24, 2026 the hero shows no worked example. The owner: "instead of showing a simple example, we
should show the directory structure emphasize that it is built on demand efficiently, no manual searches, no manual
setup, etc. Then we can have 3 links to specific demos". The hero's figure is the working directory of one step: an
instruction file with only that step's context, the skill it needs, its protocol server settings and reused code,
under the label "Example layout"; the hero says the files are placed with no manual search and no manual setup, and
that the local engine is built to assemble such a directory for every step. Three demonstrations follow, each linking to a page that shows its run start to finish. A search, a
reference, a digest or a download anywhere in the hero is the known-wrong page. The one-step demonstration that stood
beside the hero until then, splitting the address lines of a customer file, is step 2 of the demonstration at /demo,
whose every search is rerun by tools/test_showcase_pages.py; its markup is archived in
artifacts/website-archive-2026-09-24.

This module also keeps what the demonstration pages share with it: the reader of marked page elements, a real search
of this release's packaged library through the host loader and the retrieval route the service uses, and the reader of
recorded measurements that refuses an item a study found harmful. The data cleanup study of September 22, 2026 found
that normalize_phone_numbers made a cheap model clearly worse on its population; the study's own design and results
records are read, so a later study that finds another item harmful is covered without a change here.

The count of items in the library on the homepage is the number of items in the packaged manifest. Each rule has a
known-wrong page beside it that the rule must report. Nothing here reaches the network. The service runs on loopback
over a temporary database.
"""
from __future__ import annotations

from dataclasses import asdict
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "src" / "loop_engine" / "core" / "service_runtime" / "web_assets"
PAGE = ASSETS / "index.html"
RECIPES = ASSETS / "client-recipes.json"
RELEASE = ROOT / "examples" / "29_intelligence_service" / "starter-catalogue" / "host-release"
#: Where measurements of library items are recorded, one folder for each study.
STUDIES = ROOT / "case-studies"
#: The results record whose design names, for each family, the items its material arms placed.
STUDY_RESULTS = "data_cleanup_results/v1"
STAGES = (("search", "recorded"), ("download", "recorded"), ("folder", "illustration"))
LABEL_WORDS = {"recorded": "Real results from the library", "illustration": "Example layout"}
#: The status words the owner removed from the homepage on September 23, 2026. No part of the demonstration says one.
RETIRED_STATUS = re.compile(r"being built|being prepared|\bplanned\b|available now|coming soon", re.IGNORECASE)
#: The address the served homepage writes into its connection entry. Once the page script has checked the
#: reviewed recipe record, it writes the entry again with the address of the service that serves the page.
PUBLIC_ENDPOINT = "https://baltor.ai/mcp"
ENDPOINT_PLACEHOLDER = "{{ENDPOINT}}"
#: The fewest hexadecimal characters a shown digest may have. Eight is what the search list shows.
SHORTEST_DIGEST = 8
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class _MarkedReader(HTMLParser):
    """Collect every element that carries a data attribute, with its text and its ancestors.

    With a scope, only elements inside an element that carries the scope attribute are collected.
    """

    def __init__(self, scope=None):
        super().__init__(convert_charrefs=True)
        self.scope, self.open, self.found = scope, [], []

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            return
        self.open.append({"tag": tag, "attrs": dict(attrs), "text": []})

    def handle_endtag(self, tag):
        for index in range(len(self.open) - 1, -1, -1):
            if self.open[index]["tag"] == tag:
                closed, ancestors = self.open[index], self.open[:index]
                del self.open[index:]
                inside = self.scope is None or any(self.scope in item["attrs"] for item in ancestors + [closed])
                if inside and any(name.startswith("data-") for name in closed["attrs"]):
                    self.found.append({"tag": tag, "attrs": closed["attrs"], "text": "".join(closed["text"]),
                                       "ancestors": [item["attrs"] for item in ancestors]})
                return

    def handle_data(self, data):
        for item in self.open:
            item["text"].append(data)


def read_marked(page, scope=None):
    reader = _MarkedReader(scope)
    reader.feed(page)
    return reader.found


def read_demonstration(page):
    """The parts of the demonstration as plain values, read from the served page source."""
    # The reader records an element when it closes, after its children. Sorting by the place where each
    # element opened restores page order. The place is found through the element's own marker, which is
    # unique on the page.
    found = read_marked(page, "data-step-demo")

    def nearest(element, name):
        """The value of the closest ancestor that carries the attribute, or None when none does."""
        return next((attrs[name] for attrs in reversed(element["ancestors"]) if name in attrs), None)

    def facts(owner_name, owner_value):
        return {item["attrs"]["data-fact"]: " ".join(item["text"].split()) for item in found
                if "data-fact" in item["attrs"] and nearest(item, owner_name) == owner_value}

    def in_order(name):
        marked = [item for item in found if name in item["attrs"]]
        return sorted(marked, key=lambda item: page.find(name + '="' + str(item["attrs"][name]) + '"'))

    stages = [(item["attrs"]["data-demo-stage"], item["attrs"].get("data-demo-evidence", "")) for item in in_order("data-demo-stage")]
    # A label outside every part is the label of the panel's head, which covers the parts without a label of their own.
    labels = {nearest(item, "data-demo-stage") or "": (item["attrs"]["data-demo-label"], " ".join(item["text"].split()))
              for item in found if "data-demo-label" in item["attrs"]}
    items = [{"identity": item["attrs"]["data-demo-item"], "chosen": "is-chosen" in item["attrs"].get("class", "").split(),
              **facts("data-demo-item", item["attrs"]["data-demo-item"])} for item in in_order("data-demo-item")]
    download = next((item["attrs"]["data-demo-download"] for item in found if "data-demo-download" in item["attrs"]), "")
    query = next((item["text"].strip() for item in found if "data-demo-query" in item["attrs"]), "")
    paths = [item["attrs"]["data-demo-path"] for item in in_order("data-demo-path")]
    return {"stages": stages, "labels": labels, "items": items, "download": download, "query": query, "paths": paths}


def released_items():
    """This release's items by identity, and the number of items its manifest holds."""
    manifest = json.loads((RELEASE / "manifest.json").read_text(encoding="utf-8"))
    return ({row["reference"]["identity"]: {**row["reference"], "body_path": row["body_path"]} for row in manifest["items"]},
            len(manifest["items"]))


def shown_size(size_bytes):
    """The size as the page writes it: kilobytes of one thousand bytes, to one decimal place."""
    return f"{size_bytes / 1000:.1f} KB"


def digest_problem(place, shown, expected):
    """A shown digest is a lower-case prefix, at least eight characters long, of the expected one."""
    if not re.fullmatch(r"[0-9a-f]{%d,64}" % SHORTEST_DIGEST, shown or "") or not expected.startswith(shown):
        return f"{place}: the page shows sha256 {shown or '(nothing)'}, and this release has {expected}"
    return ""


def label_problems(demonstration):
    problems = []
    if [tuple(pair) for pair in demonstration["stages"]] != list(STAGES):
        problems.append(f"the parts are {demonstration['stages']}, and the page must show {list(STAGES)}")
    head = demonstration["labels"].get("", ("", ""))
    for stage, evidence in STAGES:
        label, text = demonstration["labels"].get(stage, head)
        if label != evidence or LABEL_WORDS[evidence] not in text or RETIRED_STATUS.search(text):
            problems.append(f"the {stage} part must say {LABEL_WORDS[evidence]!r}; it says {text or '(nothing)'!r}")
    return problems


def search_problems(demonstration, hits):
    """Each shown reference must be the reply of a real search of this release's library, in order."""
    shown = demonstration["items"]
    problems = [] if shown else ["the search part shows no reference"]
    if len(hits) < len(shown):
        problems.append(f"the search returned {len(hits)} references and the page shows {len(shown)}")
    for place, (item, hit) in enumerate(zip(shown, hits), start=1):
        name = f"search result {place} ({item['identity']})"
        if item["identity"] != hit["identity"]:
            problems.append(f"{name}: this release's library returns {hit['identity']} in this place")
            continue
        for fact, expected in (("kind", hit["kind"]), ("licence", hit["license"]), ("size", shown_size(hit["size_bytes"]))):
            if item.get(fact) != expected:
                problems.append(f"{name}: the page shows {fact} {item.get(fact)!r}, and this release has {expected!r}")
        problems.append(digest_problem(name, item.get("digest", ""), hit["sha256"]))
    return [problem for problem in problems if problem]


def download_problems(demonstration, items):
    """The download names the one reference the search marked as chosen, and its packaged bytes match its digest."""
    identity, shown = demonstration["download"], demonstration["items"]
    if identity not in items:
        return [f"the download part names {identity or '(nothing)'}, which this release's library does not hold"]
    problems = []
    chosen = [item["identity"] for item in shown if item["chosen"]]
    if chosen != [identity]:
        problems.append(f"the download part names {identity}, and the search marks {chosen or 'nothing'} as chosen")
    body = (RELEASE / items[identity]["body_path"]).read_bytes()
    if hashlib.sha256(body).hexdigest() != items[identity]["digest"]:
        problems.append(f"download: the packaged body of {identity} does not have the digest its reference names")
    return problems


def folder_problems(demonstration):
    """The step folder places the downloaded skill, and holds a file that is not Markdown."""
    paths, problems = demonstration["paths"], []
    if not any(Path(path).suffix.lower() != ".md" for path in paths):
        problems.append("the step folder shows only Markdown files; harness material is any file a harness reads")
    placed = [Path(path).parent.name for path in paths if Path(path).name == "SKILL.md"]
    if placed != [demonstration["download"].replace("_", "-")]:
        problems.append(f"the step folder places the skills {placed}, and the step downloaded {demonstration['download'] or '(nothing)'}")
    return problems


def harmful_in(design, summary, study):
    """The items one study found harmful, each with the comparisons that found it.

    An item is harmful on a study's population when an arm that placed it scored clearly lower, under the study's frozen
    rule, than an arm of the same model that placed nothing. A comparison of two different models proves nothing about
    the item and is not read.
    """
    arms, found = {**design["arms"], **design.get("optional_arms", {})}, {}
    for comparison in summary["comparisons"]:
        first, second = arms.get(comparison["first"]), arms.get(comparison["second"])
        if not first or not second or first["model"] != second["model"]:
            continue
        lower, higher = {"first_clearly_higher": (second, first), "second_clearly_higher": (first, second)}.get(comparison["verdict"], (None, None))
        if lower is not None and lower["material"] != "none" and higher["material"] == "none":
            for identity in design["material"][comparison["family"]]:
                found.setdefault(identity, []).append(
                    f"{study}: {comparison['family']}, {comparison['first']} against {comparison['second']}, {comparison['verdict']}")
    return found


def recorded_harm():
    """Every item a recorded study found harmful, read from the design and results records under case-studies."""
    found = {}
    for path in sorted(STUDIES.glob("*/results/summary.json")):
        summary = json.loads(path.read_text(encoding="utf-8"))
        if summary.get("record_type") != STUDY_RESULTS:
            continue
        design = json.loads((path.parent.parent / "design.json").read_text(encoding="utf-8"))
        for identity, where in harmful_in(design, summary, path.parent.parent.name).items():
            found.setdefault(identity, []).extend(where)
    return found


def harmful_choice_problems(demonstration, harmful):
    """The demonstration may not choose an item that a recorded measurement found harmful."""
    return [f"the demonstration chooses {item['identity']}, which a recorded measurement found harmful: {'; '.join(harmful[item['identity']])}"
            for item in demonstration["items"] if item["chosen"] and item["identity"] in harmful]


def library_count_problems(page, item_count):
    shown = [" ".join(item["text"].split()) for item in read_marked(page) if "data-library-count" in item["attrs"]]
    if shown != [str(item_count)]:
        return [f"the homepage counts {shown or 'no'} items, and this release's manifest holds {item_count}"]
    return []


def with_endpoint(value, endpoint):
    if value == ENDPOINT_PLACEHOLDER:
        return endpoint
    if isinstance(value, dict):
        return {key: with_endpoint(item, endpoint) for key, item in value.items()}
    if isinstance(value, list):
        return [with_endpoint(item, endpoint) for item in value]
    return value


def entry_problems(page, record):
    """The homepage shows one connection entry: a reviewed recipe, as the page script writes it, with the public address."""
    entries = [(item["attrs"]["data-home-recipe"], item["text"]) for item in read_marked(page) if "data-home-recipe" in item["attrs"]]
    if len(entries) != 1:
        return [f"the homepage shows {len(entries)} connection entries, and it shows one"]
    identity, text = entries[0]
    recipe = next((recipe for recipe in record["recipes"] if recipe["id"] == identity), None)
    if recipe is None or recipe["format"] != "json":
        return [f"the homepage entry names {identity!r}, which is not a reviewed recipe written as JSON"]
    # The page script writes the entry with JSON.stringify(value, null, 2); this is the same text.
    expected = json.dumps(with_endpoint(recipe["configuration"], PUBLIC_ENDPOINT), indent=2, ensure_ascii=False)
    return [] if text == expected else [f"the homepage entry is not the reviewed {identity} recipe with the address {PUBLIC_ENDPOINT}"]


def release_search(query, top_n=10):
    """A real search of this release's packaged library, through the host loader and the retrieval route."""
    import httpx
    from loop_engine.core.service_runtime.http_entrypoint import configure_host, load_host_application
    from loop_engine.core.service_runtime.http_test_fixtures import running_http
    from loop_engine.core.service_runtime.records import TenantKeyIssue
    manifest = json.loads((RELEASE / "manifest.json").read_text(encoding="utf-8"))
    manifest["artifact_root"] = str(RELEASE.resolve())
    tenants = sorted({grant["tenant_id"] for row in manifest["items"] for grant in row["grants"]})
    with tempfile.TemporaryDirectory(prefix="homepage-demonstration-") as temporary:
        root = Path(temporary).resolve()
        (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        def build(configuration):
            (root / "service.json").write_text(json.dumps({
                "record_type": "service_http_host_configuration/v1",
                "runtime": {"database_path": str(root / "state.db"), "writes_authorized": True},
                "http": asdict(configuration), "authentication": {"modes": ["host_key"]},
                "manifest_path": str(root / "manifest.json"),
                "tenants": [{"tenant_id": tenant, "namespace": tenant, "operator_entitlement": {
                    "valid_until": int(time.time()) + 3600, "evidence_ref": "homepage-demonstration-check"}}
                    for tenant in tenants]}), encoding="utf-8")
            configure_host(str(root / "service.json"))
            return load_host_application(str(root / "service.json"))[0]

        with running_http(None, application_factory=build) as (base, application):
            key = application.runtime.issue_key(TenantKeyIssue(tenants[0], "homepage demonstration check")).key
            reply = httpx.post(base + "/api/v1/retrieval", trust_env=False, timeout=10,
                               headers={"Authorization": "Bearer " + key},
                               json={"record_type": "service_retrieval_request/v2", "query": query,
                                     "mode": "lexical", "top_n": top_n})
            reply.raise_for_status()
    return [{"identity": hit["reference"]["identity"], "kind": hit["kind"], "license": hit["license"],
             "size_bytes": hit["size_bytes"], "sha256": hit["reference"]["body_digest"]} for hit in reply.json()["result"]["hits"]]


def _changed(demonstration, change):
    copy = json.loads(json.dumps(demonstration))
    change(copy)
    return copy


def _planted(page, old, new):
    """The page source with one text replaced, the way a stale or edited page would serve it."""
    changed = page.replace(old, new, 1)
    assert changed != page, f"the planted text {old!r} is not on the page"
    return changed


#: The parts of one step's working directory the hero shows, in order.
HERO_PARTS = ("instructions", "skills", "tools", "code")
#: A sentence that assembles or builds something for each step. What works today stays apart from what is built but not
#: shipped: a person's agent searches and Baltor places the chosen files, while assembling a directory for every step is what
#: the local engine is built to do. Such a sentence must say "built to".
PER_STEP = re.compile(r"\b(?:assembl|build|built)\w*\b[^.!?]*\b(?:each|every|this|one)\s+(?:step|subtask)\b", re.IGNORECASE)
#: The three demonstrations under the hero, in order, with the page each one opens.
DEMONSTRATIONS = (("simple", "/demo"), ("overnight", "/overnight"), ("kaggle", "/demo/kaggle"))
#: What a worked example leaves in the hero: a demonstration panel, a search, its references, their facts or a download.
WORKED_EXAMPLE = ("data-step-demo", "data-demo-item", "data-demo-query", "data-demo-download", "data-demo-stage",
                  "data-task-demo", "data-fact=")
WORKED_EXAMPLE_WORDS = re.compile(r"\bsearch:|\bsha256\b|Bytes match the digest|Recorded from this release", re.IGNORECASE)


def hero_markup(page):
    """The markup of the hero band of the homepage, from its opening tag to the next band."""
    found = re.search(r'<div class="home-band[^"]*" data-band="hero">(.*?)(?=\n\s*<div class="home-band)', page, re.S)
    return found.group(1) if found else ""


def hero_problems(page):
    """The hero shows the working directory of one step, labelled as an example, and no worked example."""
    hero = hero_markup(page)
    if not hero:
        return ["the homepage has no hero band"]
    problems = []
    parts = re.findall(r'data-hero-part="([a-z]+)"', hero)
    if tuple(parts) != HERO_PARTS:
        problems.append(f"the hero directory shows the parts {parts}, and it shows {list(HERO_PARTS)}")
    label = re.search(r'data-hero-label="illustration">([^<]*)<', hero)
    if not label or label.group(1).strip() != LABEL_WORDS["illustration"] or RETIRED_STATUS.search(label.group(1)):
        problems.append("the hero directory is not labelled as an example layout")
    note = re.search(r"<p [^>]*data-hero-note[^>]*>([^<]*)</p>", hero)
    note = note.group(1) if note else ""
    words = " ".join(re.sub(r"<[^>]+>", " ", hero).split())
    if not re.search(r"no manual search", words, re.IGNORECASE) or not re.search(r"no manual setup", words, re.IGNORECASE):
        problems.append("the hero does not say the files are placed with no manual search and no manual setup")
    claims = [sentence for sentence in re.split(r"(?<=[.!?])\s+", words) if PER_STEP.search(sentence) and "built to" not in sentence.lower()]
    if claims or "built to" not in note.lower():
        problems.append(f"the hero states assembly for each step as a current capability: {claims}")
    if any(marker in hero for marker in WORKED_EXAMPLE) or WORKED_EXAMPLE_WORDS.search(re.sub(r"<[^>]+>", " ", hero)):
        problems.append("the hero shows a worked example again")
    return problems


def demonstration_problems(page, served):
    """The homepage links the three demonstrations in order, each to a page this service serves."""
    cards = re.findall(r'data-demo-card="([a-z]+)">.*?<a [^>]*href="([^"]+)"', page, re.S)
    problems = [] if tuple(cards) == DEMONSTRATIONS else [f"the homepage links the demonstrations {cards}, and it links {list(DEMONSTRATIONS)}"]
    return problems + [f"the {name} demonstration links {address}, which this service does not serve"
                       for name, address in cards if address not in served]


def opening_claim_problems(page):
    """Refuse an unconditional drift outcome in the homepage's design promise."""
    # The opening may hold an inline link, such as the one to how review works; its words are read without the tags.
    opening = re.search(r'<p class="hero-subhead">(.*?)</p>', page, re.S)
    if opening is None:
        return ["opening message missing or not readable"]
    guarantee = re.search(
        r"\bnothing\s+drifts\b|\bnever\s+drifts?\b|\beliminates?\s+(?:all\s+)?context\s+drift\b",
        re.sub(r"<[^>]+>", "", opening.group(1)), re.IGNORECASE)
    return ["opening promises unmeasured elimination of drift"] if guarantee else []


class HomepageOpeningClaimTest(unittest.TestCase):
    def test_opening_does_not_promise_that_context_never_drifts(self):
        self.assertEqual(opening_claim_problems(PAGE.read_text(encoding="utf-8")), [])
        # KNOWN_WRONG: the September 23 page promised "nothing drifts".
        for text in ("nothing drifts", "the context never drifts", "eliminates context drift"):
            with self.subTest(guarantee=text):
                self.assertEqual(len(opening_claim_problems(
                    '<p class="hero-subhead">' + text + '</p>')), 1)
        self.assertEqual(opening_claim_problems(
            '<p class="hero-subhead">The design aims to reduce context drift.</p>'), [])
        # KNOWN_WRONG: the promise written around an inline link is still read.
        self.assertEqual(len(opening_claim_problems('<p class="hero-subhead">The context <a href="/security">never</a> drifts.</p>')), 1)


class HomepageHeroTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from loop_engine.core.service_runtime.web_pages import WEB_ASSETS
        cls.page = PAGE.read_text(encoding="utf-8")
        cls.items, cls.item_count = released_items()
        cls.served = set(WEB_ASSETS)
        cls.archived = (ROOT / "artifacts" / "website-archive-2026-09-24" / "homepage-before-2026-09-24-hero.html").read_text(encoding="utf-8")

    def test_the_hero_shows_a_working_directory_and_no_worked_example(self):
        self.assertEqual(hero_problems(self.page), [])
        hero = hero_markup(self.page)
        # KNOWN_WRONG: the one-step demonstration of September 23, as archived, back beside the hero copy.
        demonstration = self.archived.split("<!-- The Ask, get, place band")[0].split("-->", 2)[-1]
        planted = _planted(self.page, '<figure class="hero-directory"', demonstration + '<figure class="hero-directory"')
        self.assertIn("the hero shows a worked example again", hero_problems(planted))
        # KNOWN_WRONG: a search and its digest written as words, a directory without its protocol server settings, and a
        # hero that no longer says the files are placed without manual setup.
        self.assertEqual(len(hero_problems(_planted(self.page, '<p class="hero-directory-note"', '<p>search: split address lines, sha256 53dc74e3</p><p class="hero-directory-note"'))), 1)
        self.assertEqual(len(hero_problems(_planted(self.page, '<span data-hero-part="tools">', "<span>"))), 1)
        self.assertEqual(len(hero_problems(_planted(self.page, "No manual search, no manual setup, nothing copied by hand.",
                                                    "No manual search, nothing copied by hand."))), 1)
        self.assertTrue(hero)

    def test_the_hero_keeps_assembly_for_each_step_to_built_to_wording(self):
        # KNOWN_WRONG, the owner's constraint of September 24, 2026: assembly for each step stated as what Baltor does today, as a
        # label beside the directory, as a sentence of the introduction, and as a note that no longer says the engine is built to.
        for planted in (_planted(self.page, '<p class="hero-directory-note"', '<p>Assembled for this step.</p><p class="hero-directory-note"'),
                        _planted(self.page, "No manual search, no manual setup, nothing copied by hand.</p>",
                                 "No manual search, no manual setup, nothing copied by hand. Baltor assembles one for every step.</p>"),
                        _planted(self.page, "The local engine is built to assemble a directory", "The local engine assembles a directory")):
            with self.subTest(planted=len(planted)):
                self.assertTrue(any("current capability" in problem for problem in hero_problems(planted)))

    def test_the_homepage_links_three_demonstrations_start_to_finish(self):
        self.assertEqual(demonstration_problems(self.page, self.served), [])
        # KNOWN_WRONG: a demonstration that opens a page this service does not serve, and a missing demonstration.
        unserved = demonstration_problems(_planted(self.page, 'href="/demo/kaggle" data-page="demo-kaggle"', 'href="/demo/kaggle-2026" data-page="demo-kaggle"'), self.served)
        self.assertIn("the kaggle demonstration links /demo/kaggle-2026, which this service does not serve", unserved)
        self.assertEqual(len(demonstration_problems(_planted(self.page, 'data-demo-card="overnight"', 'data-demo-card="retired"'), self.served)), 1)

    def test_the_study_reader_finds_the_harmful_item_and_nothing_else(self):
        harmful = recorded_harm()
        # The committed study records one clearly worse family, so a reader that finds nothing is itself broken.
        self.assertTrue(harmful)
        self.assertIn("normalize_phone_numbers", harmful)
        # KNOWN_WRONG: a study whose material arm is clearly lower than the same model without it, once in each order of the
        # comparison; and a clearly lower arm of another model, which says nothing of the item.
        design = {"arms": {"cheap-none": {"model": "cheap", "material": "none"}, "cheap-file": {"model": "cheap", "material": "agents_file"},
                           "large-none": {"model": "large", "material": "none"}},
                  "material": {"family": ["planted_item"]}}
        comparisons = [{"family": "family", "first": "cheap-file", "second": "cheap-none", "verdict": "second_clearly_higher"},
                       {"family": "family", "first": "cheap-none", "second": "cheap-file", "verdict": "first_clearly_higher"}]
        for comparison in comparisons:
            self.assertEqual(list(harmful_in(design, {"comparisons": [comparison]}, "planted")), ["planted_item"])
        self.assertEqual(harmful_in(design, {"comparisons": [{"family": "family", "first": "cheap-file", "second": "large-none",
                                                              "verdict": "second_clearly_higher"}]}, "planted"), {})
        self.assertEqual(harmful_in(design, {"comparisons": [{**comparisons[0], "verdict": "not_separated"}]}, "planted"), {})

    def test_the_library_count_is_this_release_manifest_count(self):
        self.assertEqual(library_count_problems(self.page, self.item_count), [])
        # PLANTED: a count this release does not hold, written into the page source.
        planted = _planted(self.page, "data-library-count>" + str(self.item_count) + "<", "data-library-count>" + str(self.item_count + 1) + "<")
        self.assertEqual(len(library_count_problems(planted, self.item_count)), 1)


if __name__ == "__main__":
    unittest.main()
