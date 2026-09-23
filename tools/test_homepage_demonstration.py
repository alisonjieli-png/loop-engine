"""The one-step demonstration on the homepage shows this release's library, and every fact it shows is what it says.

The homepage shows one step of a task in three parts. Two parts are recorded: the search and the download.
Their item names, kinds, licences, sizes and digests must be what a real search of this release's packaged
library returns, run here through the same host loader and the same retrieval route the service uses. A
catalogue release rewrites each body and so each digest, and the page then fails here until it shows the new
values; the failure names them. The download names the reference the search marked as chosen, and the packaged
bytes of that reference have the digest it names. The third part, a fresh harness that holds only the files of
the step, is being built and says so under a label of its own. Its folder places the downloaded skill and holds
files that are not Markdown, because harness material is any file a harness reads.

Two more facts on the homepage come from the same release: the count of items in the library is the number of
items in the packaged manifest, and the connection entry is the reviewed Claude Code recipe with the public
address written in. Each rule has a known-wrong page beside it that the rule must report.

The step the homepage shows chooses an item that no recorded measurement found harmful. The data cleanup study
of September 22, 2026 found that normalize_phone_numbers made a cheap model clearly worse on its population, and
the homepage featured that item until then. The study's own design and results records are read, so a later
study that finds another item harmful is covered without a change here.

Nothing here reaches the network. The service runs on loopback over a temporary database.
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
LABEL_WORDS = {"recorded": "Recorded from this release's library", "illustration": "Being built"}
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
        if label != evidence or LABEL_WORDS[evidence] not in text:
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
                               json={"record_type": "service_retrieval_request/v1", "query": query,
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


class HomepageDemonstrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = PAGE.read_text(encoding="utf-8")
        cls.demonstration = read_demonstration(cls.page)
        cls.items, cls.item_count = released_items()
        cls.recipes = json.loads(RECIPES.read_text(encoding="utf-8"))
        cls.hits = release_search(cls.demonstration["query"]) if cls.demonstration["query"] else []

    def test_each_part_says_whether_it_is_recorded_or_being_built(self):
        self.assertEqual(label_problems(self.demonstration), [])
        # KNOWN_WRONG: the folder without a label of its own falls under the recorded label of the head.
        unlabelled = _changed(self.demonstration, lambda copy: copy["labels"].pop("folder"))
        self.assertEqual(len(label_problems(unlabelled)), 1)
        # KNOWN_WRONG: a head that calls the recorded search and download "being built".
        relabelled = _changed(self.demonstration, lambda copy: copy["labels"].update({"": ["illustration", LABEL_WORDS["illustration"]]}))
        self.assertEqual(len(label_problems(relabelled)), 2)

    def test_the_search_shows_what_this_release_library_returns(self):
        self.assertEqual(self.demonstration["query"], "split address lines in a customer file")
        self.assertEqual(search_problems(self.demonstration, self.hits), [])
        # KNOWN_WRONG: one digest changed by one character, one size changed, and two places swapped.
        wrong_digest = _changed(self.demonstration, lambda copy: copy["items"][1].update(
            digest=copy["items"][1]["digest"][:-1] + ("0" if copy["items"][1]["digest"][-1] != "0" else "1")))
        wrong_size = _changed(self.demonstration, lambda copy: copy["items"][2].update(size="9.9 KB"))
        swapped = _changed(self.demonstration, lambda copy: copy["items"].reverse())
        self.assertEqual(len(search_problems(wrong_digest, self.hits)), 1)
        self.assertEqual(len(search_problems(wrong_size, self.hits)), 1)
        self.assertGreaterEqual(len(search_problems(swapped, self.hits)), 2)
        # PLANTED: one digest changed in the page source itself, the way a stale page would serve it.
        first = self.demonstration["items"][0]["digest"]
        planted = _planted(self.page, 'data-fact="digest">' + first + "<",
                           'data-fact="digest">' + first[:-1] + ("0" if first[-1] != "0" else "1") + "<")
        self.assertEqual(len(search_problems(read_demonstration(planted), self.hits)), 1)

    def test_the_download_is_the_chosen_reference_with_its_digest(self):
        self.assertEqual(download_problems(self.demonstration, self.items), [])
        second = self.demonstration["items"][1]["identity"]
        # KNOWN_WRONG: a download of another reference, of an item this release does not hold, and a moved choice.
        other = _changed(self.demonstration, lambda copy: copy.update(download=second))
        invented = _changed(self.demonstration, lambda copy: copy.update(download="invented_item_nobody_approved"))
        moved = _changed(self.demonstration, lambda copy: [item.update(chosen=item["identity"] == second) for item in copy["items"]])
        self.assertEqual(len(download_problems(other, self.items)), 1)
        self.assertEqual(len(download_problems(invented, self.items)), 1)
        self.assertEqual(len(download_problems(moved, self.items)), 1)

    def test_the_folder_places_the_download_and_holds_files_that_are_not_markdown(self):
        self.assertEqual(folder_problems(self.demonstration), [])
        # KNOWN_WRONG: a folder of Markdown files only, and a folder that places a skill the step did not download.
        only_markdown = _changed(self.demonstration, lambda copy: copy.update(paths=[path for path in copy["paths"] if path.endswith(".md")]))
        placed = self.demonstration["download"].replace("_", "-")
        another = next(identity for identity in sorted(self.items) if identity != self.demonstration["download"]).replace("_", "-")
        other_skill = _changed(self.demonstration, lambda copy: copy.update(
            paths=[path.replace(placed, another) for path in copy["paths"]]))
        self.assertEqual(len(folder_problems(only_markdown)), 1)
        self.assertEqual(len(folder_problems(other_skill)), 1)

    def test_the_step_chooses_no_item_a_recorded_measurement_found_harmful(self):
        harmful = recorded_harm()
        # The committed study records one clearly worse family, so a reader that finds nothing is itself broken.
        self.assertTrue(harmful)
        self.assertEqual(harmful_choice_problems(self.demonstration, harmful), [])
        # KNOWN_WRONG: the step chooses an item a recorded measurement found harmful, as the homepage did until September 23.
        chose_harm = _changed(self.demonstration, lambda copy: copy["items"][0].update(identity=sorted(harmful)[0], chosen=True))
        self.assertEqual(len(harmful_choice_problems(chose_harm, harmful)), 1)
        # KNOWN_WRONG: the reader is given a study whose material arm is clearly lower than the same model without it,
        # once in each order of the comparison; and a clearly lower arm of another model, which says nothing of the item.
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

    def test_the_connection_entry_is_the_reviewed_recipe_with_the_public_address(self):
        self.assertEqual(entry_problems(self.page, self.recipes), [])
        variable = self.recipes["credential_variable"]
        # PLANTED: another variable name, another address and another recipe, each written into the page source.
        for old, new in ((variable, "BALTOR_KEY"), (PUBLIC_ENDPOINT, "https://example.com/mcp"),
                         ('data-home-recipe="claude-code"', 'data-home-recipe="codex"')):
            with self.subTest(planted=new):
                self.assertEqual(len(entry_problems(_planted(self.page, old, new), self.recipes)), 1)


if __name__ == "__main__":
    unittest.main()
