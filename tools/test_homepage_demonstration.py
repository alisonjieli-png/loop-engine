"""The homepage hero shows one step: a real search and download of this release, and the directory the step gets.

On September 26, 2026 the owner supplied a Claude Design project for the website and asked for it to be built: "we need to
aggressively implement the new design and get it deployed". Its homepage hero (site/Home.dc.html) is a terminal of three
panes: the search a harness sends, the download of the one reference it chose, and the folder the files are placed in. The
archive wrote those panes with placeholder commands (baltor.search, baltor.fetch) and made-up references. The hero here shows
the protocol tools a harness really calls on this service, intelligence_search and provisioning_read, with a search whose
references this check reruns against this release's library, in the same places with the same kind, licence, size and
digest, and a download of the reference the search marked as chosen whose packaged bytes match its digest. The search and the
download say "Real results from the library"; the folder stays an example layout with its built-to note, as below. A placeholder
command, a reference this release does not return in that place, a digest it does not hold, a download of another reference
and a folder that places another skill are each a known-wrong hero.

Until September 26 the hero showed no worked example. The owner: "instead of showing a simple example, we
should show the directory structure emphasize that it is built on demand efficiently, no manual searches, no manual
setup, etc. Then we can have 3 links to specific demos". The hero's figure is the working directory of one step: an
instruction file with only that step's context, the skill it needs, its protocol server settings and reused code,
under the label "Example layout"; the hero says the files are placed with no manual search and no manual setup, and
that the local engine is built to assemble such a directory for every step. Three demonstrations follow, each linking to a page that shows its run start to finish. A search, a
reference, a digest or a download anywhere in the hero is the known-wrong page. The one-step demonstration that stood
beside the hero until then, splitting the address lines of a customer file, is step 2 of the demonstration at /demo,
whose every search is rerun by tools/test_showcase_pages.py; its markup is archived in
artifacts/website-archive-2026-09-24. On September 27, 2026 the reused code file, lib/blocking_keys.py, was taken out of
the folder: the download it sat beside delivers one SKILL.md, and the folder shows only files the download delivers
beside the harness's own files.

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
    # The harness's own files of the folder (its instruction file, its skill folder and its connection settings) are not
    # placed from the download; they are kept apart from the placed paths.
    harness_files = [" ".join(item["text"].split()) for item in found if "data-hero-file" in item["attrs"]]
    return {"stages": stages, "labels": labels, "items": items, "download": download, "query": query, "paths": paths,
            "harness_files": harness_files}


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


def delivered_files(item):
    """The files a download of this release item places in its skill folder, or None for a shape this check does not read.

    Every item of the packaged release is a single-file skill: its one body is placed as the skill folder's SKILL.md."""
    if item.get("kind") == "skill" and Path(item.get("body_path", "")).suffix == ".md" and not item.get("files"):
        return {"SKILL.md"}
    return None


def folder_problems(demonstration, items):
    """The step folder places the downloaded skill and only the files its package delivers, and holds a file that is not Markdown.

    Until September 27, 2026 the folder also showed lib/blocking_keys.py beside the skill, a module the downloaded package
    does not deliver: every package of this release is a single SKILL.md."""
    paths, problems, identity = demonstration["paths"], [], demonstration["download"]
    if not any(Path(path.rstrip("/")).suffix.lower() not in (".md", "") for path in paths + demonstration["harness_files"]):
        problems.append("the step folder shows only Markdown files; harness material is any file a harness reads")
    placed = [Path(path).parent.name for path in paths if Path(path).name == "SKILL.md"]
    if placed != [identity.replace("_", "-")]:
        problems.append(f"the step folder places the skills {placed}, and the step downloaded {identity or '(nothing)'}")
    delivered = delivered_files(items[identity]) if identity in items else set()
    if delivered is None:
        return problems + [f"the files a download of {identity} places are not known to this check"]
    for path in paths:
        if Path(path).name != "SKILL.md" and not (Path(path).parent.name == identity.replace("_", "-")
                                                  and Path(path).name in delivered):
            problems.append(f"the step folder shows {path}, which the download of {identity} does not deliver")
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
#: The owner's hero of September 24, 2026 named reused code as a fourth part. On September 27, 2026 the code file was taken
#: out: the folder places the one reference the search chose, and no package of the packaged release delivers a code module.
HERO_PARTS = ("instructions", "skills", "tools")
#: The protocol tools the hero's terminal calls, in order: the search, then the read of the exact version it chose. The search
#: tool is listed by name in http.py and the read tool is a key of provisioning_mcp.TOOL_OPERATIONS; the tests read both.
HERO_TOOLS = ("intelligence_search", "provisioning_read")
HTTP_SOURCE = ROOT / "src" / "loop_engine" / "core" / "service_runtime" / "http.py"


def served_tool_names():
    """The names of the protocol tools this service lists to a harness."""
    from loop_engine.core.provisioning_mcp import TOOL_OPERATIONS
    listed = set(re.findall(r'types\.Tool\(name="([a-z_]+)"', HTTP_SOURCE.read_text(encoding="utf-8")))
    return listed | set(TOOL_OPERATIONS)
#: A sentence that assembles or builds something for each step. What works today stays apart from what is built but not
#: shipped: a person's agent searches and Baltor places the chosen files, while assembling a directory for every step is what
#: the local engine is built to do. Such a sentence must say "built to".
PER_STEP = re.compile(r"\b(?:assembl|build|built)\w*\b[^.!?]*\b(?:each|every|this|one)\s+(?:step|subtask)\b", re.IGNORECASE)
#: The three demonstrations under the hero, in order, with the page each one opens.
DEMONSTRATIONS = (("simple", "/demo"), ("overnight", "/overnight"), ("kaggle", "/demo/kaggle"))


def hero_markup(page):
    """The markup of the hero band of the homepage, from its opening tag to the next band."""
    found = re.search(r'<div class="home-band[^"]*" data-band="hero">(.*?)(?=\n\s*<div class="home-band)', page, re.S)
    return found.group(1) if found else ""


def hero_problems(page, served_tools=HERO_TOOLS):
    """The hero shows one step: its search and download as recorded parts and its working directory as an example.

    What this reads from the page source alone: the three parts in order with their labels, the tools the terminal calls, the four
    parts of the directory, its example label and built-to note, and the words about manual search and setup. That the search and
    the download are this release's own is `hero_result_problems`, which runs the search."""
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
    problems.extend(label_problems(read_demonstration(hero)))
    tools = tuple(re.findall(r'data-demo-tool="([^"]*)"', hero))
    if tools != HERO_TOOLS or any(tool not in served_tools for tool in tools):
        problems.append(f"the terminal calls {list(tools)}, and a harness calls {list(HERO_TOOLS)} on this service")
    return problems


def hero_result_problems(page, items, harmful):
    """The hero's search is a real search of this release, its download the chosen reference, its folder places that skill."""
    demonstration = read_demonstration(hero_markup(page))
    if not demonstration["query"]:
        return ["the hero terminal shows no search"]
    return (search_problems(demonstration, release_search(demonstration["query"])) + download_problems(demonstration, items)
            + folder_problems(demonstration, items) + harmful_choice_problems(demonstration, harmful))


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

    def test_the_hero_shows_one_step_with_its_parts_labels_and_tools(self):
        self.assertIn('types.Tool(name="intelligence_search"', HTTP_SOURCE.read_text(encoding="utf-8"))
        self.assertEqual(hero_problems(self.page, served_tool_names()), [])
        self.assertTrue(hero_markup(self.page))
        # KNOWN_WRONG: the archive's placeholder commands, and a tool this service does not list under the right name.
        planted = _planted(self.page, 'data-demo-tool="intelligence_search">intelligence_search<', 'data-demo-tool="baltor.search">baltor.search<')
        self.assertEqual(len(hero_problems(planted, served_tool_names())), 1)
        self.assertEqual(len(hero_problems(self.page, {"intelligence_search"})), 1)
        # KNOWN_WRONG: the one-step demonstration of September 23, as archived, planted as a second search beside the terminal.
        demonstration = self.archived.split("<!-- The Ask, get, place band")[0].split("-->", 2)[-1]
        self.assertIn("data-step-demo", demonstration)
        planted = _planted(self.page, '<figure class="hero-terminal"', demonstration + '<figure class="hero-terminal"')
        self.assertTrue(any(problem.startswith("the parts are") for problem in hero_problems(planted, served_tool_names())))
        # KNOWN_WRONG: the recorded label gone from the terminal, a directory without its protocol server settings, and a hero that
        # no longer says the files are placed without manual setup.
        # The terminal's label covers the search and the download, so its loss is reported for each of the two.
        self.assertEqual(len(hero_problems(_planted(self.page, ">Real results from the library<", ">Results<"), served_tool_names())), 2)
        self.assertEqual(len(hero_problems(_planted(self.page, '<span data-hero-part="tools"', "<span"), served_tool_names())), 1)
        self.assertEqual(len(hero_problems(_planted(self.page, "No manual search, no manual setup.", "No manual search."), served_tool_names())), 1)

    def test_the_hero_search_and_download_are_this_release_own(self):
        harmful = recorded_harm()
        self.assertEqual(hero_result_problems(self.page, self.items, harmful), [])
        # KNOWN_WRONG: a digest this release does not hold, the two references in the other order, a download of the reference the
        # search did not choose, and a folder that places another skill.
        first = re.search(r'data-demo-item="([a-z_]+)" class="is-chosen">.*?data-fact="digest">([0-9a-f]+)<', hero_markup(self.page), re.S)
        identity, digest = first.group(1), first.group(2)
        wrong_digest = digest[:-1] + ("0" if digest[-1] != "0" else "1")
        self.assertTrue(hero_result_problems(_planted(self.page, 'data-fact="digest">' + digest + "<", 'data-fact="digest">' + wrong_digest + "<"), self.items, harmful))
        shown = re.findall(r'data-demo-item="([a-z_]+)"', hero_markup(self.page))
        swapped = self.page.replace('data-demo-item="' + shown[0] + '"', "data-demo-item=\"PLACEHOLDER\"", 1).replace(
            'data-demo-item="' + shown[1] + '"', 'data-demo-item="' + shown[0] + '"', 1).replace("data-demo-item=\"PLACEHOLDER\"", 'data-demo-item="' + shown[1] + '"', 1)
        self.assertTrue(hero_result_problems(swapped, self.items, harmful))
        self.assertTrue(hero_result_problems(_planted(self.page, 'data-demo-download="' + identity + '"', 'data-demo-download="' + shown[1] + '"'), self.items, harmful))
        placed = identity.replace("_", "-")
        self.assertEqual(len(hero_result_problems(_planted(self.page, 'data-demo-path=".claude/skills/' + placed + '/SKILL.md"',
                                                             'data-demo-path=".claude/skills/' + shown[1].replace("_", "-") + '/SKILL.md"'), self.items, harmful)), 1)

    def test_the_folder_shows_only_files_the_download_delivers(self):
        harmful = recorded_harm()
        demonstration = read_demonstration(hero_markup(self.page))
        self.assertEqual(folder_problems(demonstration, self.items), [])
        self.assertEqual(delivered_files(self.items[demonstration["download"]]), {"SKILL.md"})
        self.assertIn(".mcp.json", demonstration["harness_files"])
        # KNOWN_WRONG: the folder as served until September 27, 2026, with a code module beside the skill that the downloaded
        # package does not deliver; and a second file planted inside the skill's own folder.
        before = _planted(self.page, '.mcp.json</span>\n└── .baltor/step.lock.json',
                          '.mcp.json</span>\n├── lib/\n│   └── <span data-hero-part="code" data-demo-path="lib/blocking_keys.py">'
                          'blocking_keys.py</span>\n└── .baltor/step.lock.json')
        problems = hero_result_problems(before, self.items, harmful)
        self.assertEqual(problems, ["the step folder shows lib/blocking_keys.py, which the download of "
                                    "find_duplicate_records_with_blocking_keys does not deliver"])
        self.assertTrue(any(problem.startswith("the hero directory shows the parts") for problem in hero_problems(before)))
        skill = ".claude/skills/find-duplicate-records-with-blocking-keys/"
        extra = _planted(self.page, 'SKILL.md</span>\n├── <span data-hero-part="tools"',
                         'SKILL.md</span>\n│       └── <span data-demo-path="' + skill + 'scripts/dedupe.py">dedupe.py</span>\n'
                         '├── <span data-hero-part="tools"')
        self.assertEqual(len(folder_problems(read_demonstration(hero_markup(extra)), self.items)), 1)

    def test_the_hero_keeps_assembly_for_each_step_to_built_to_wording(self):
        # KNOWN_WRONG, the owner's constraint of September 24, 2026: assembly for each step stated as what Baltor does today, as a
        # label beside the directory, as a sentence of the introduction, and as a note that no longer says the engine is built to.
        for planted in (_planted(self.page, '<p class="hero-directory-note"', '<p>Assembled for this step.</p><p class="hero-directory-note"'),
                        _planted(self.page, "No manual search, no manual setup.</p>",
                                 "No manual search, no manual setup. Baltor assembles one for every step.</p>"),
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
