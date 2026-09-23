"""The one-step demonstration on the homepage shows this release's library, and every file it shows is what it says.

The homepage walks through one step of a task in five stages. Two stages are recorded: the search and
the download. Their item names, kinds, licences, sizes and digests must be what a real search of this
release's packaged library returns, run here through the same host loader and the same retrieval route
the service uses. A catalogue release rewrites each body and so each digest, and the page then fails
here until it shows the new values; the failure names them. The other three stages illustrate the
per-step design that is being built. The digests the illustrated step folder lists must be the digests
of the files it shows, and its check table must be what the script it shows returns for the checks
written in the downloaded skill. Each rule has a known-wrong page beside it that the rule must report.

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
PAGE = ROOT / "src" / "loop_engine" / "core" / "service_runtime" / "web_assets" / "index.html"
RELEASE = ROOT / "examples" / "29_intelligence_service" / "starter-catalogue" / "host-release"
STAGES = (("split", "illustration"), ("search", "recorded"), ("download", "recorded"),
          ("folder", "illustration"), ("check", "illustration"))
LABEL_WORDS = {"recorded": "Recorded from this release's library", "illustration": "Illustration"}
#: The fewest hexadecimal characters a shown digest may have. Eight is what the search list shows.
SHORTEST_DIGEST = 8
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class _DemonstrationReader(HTMLParser):
    """Collect every element of the demonstration that carries a data attribute, with its text and its ancestors."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.open, self.found = [], []

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            return
        self.open.append({"tag": tag, "attrs": dict(attrs), "text": []})

    def handle_endtag(self, tag):
        for index in range(len(self.open) - 1, -1, -1):
            if self.open[index]["tag"] == tag:
                closed, ancestors = self.open[index], self.open[:index]
                del self.open[index:]
                inside = any("data-step-demo" in item["attrs"] for item in ancestors + [closed])
                if inside and any(name.startswith("data-") for name in closed["attrs"]):
                    self.found.append({"tag": tag, "attrs": closed["attrs"], "text": "".join(closed["text"]),
                                       "ancestors": [item["attrs"] for item in ancestors]})
                return

    def handle_data(self, data):
        for item in self.open:
            item["text"].append(data)


def read_demonstration(page):
    """The parts of the demonstration as plain values, read from the served page source."""
    reader = _DemonstrationReader()
    reader.feed(page)
    # The reader records an element when it closes, after its children. Sorting by the place where each
    # element opened restores page order. The place is found through the element's own marker, which is
    # unique on the page.
    found = reader.found

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
    labels = {nearest(item, "data-demo-stage") or "": (item["attrs"]["data-demo-label"], " ".join(item["text"].split()))
              for item in found if "data-demo-label" in item["attrs"]}
    items = [{"identity": item["attrs"]["data-demo-item"], **facts("data-demo-item", item["attrs"]["data-demo-item"])}
             for item in in_order("data-demo-item")]
    download = next((item["attrs"]["data-demo-download"] for item in found if "data-demo-download" in item["attrs"]), "")
    downloaded = {item["attrs"]["data-fact"]: " ".join(item["text"].split()) for item in found
                  if "data-fact" in item["attrs"] and nearest(item, "data-demo-stage") == "download"
                  and nearest(item, "data-demo-item") is None}
    query = next((item["text"].strip() for item in found if "data-demo-query" in item["attrs"]), "")
    excerpt = next((item["text"] for item in found if "data-demo-excerpt" in item["attrs"]), "")
    bodies = {item["attrs"]["data-demo-body"]: item["text"] for item in found if "data-demo-body" in item["attrs"]}
    paths = {item["attrs"]["data-demo-path"]: facts("data-demo-path", item["attrs"]["data-demo-path"]).get("digest", "")
             for item in in_order("data-demo-path")}
    lock_text = next((item["text"] for item in found if "data-demo-lock" in item["attrs"]), "")
    try:
        lock = json.loads(lock_text)
    except ValueError:
        lock = None
    checks = [{cell["attrs"]["data-cell"]: cell["text"].strip() for cell in found
               if "data-cell" in cell["attrs"] and nearest(cell, "data-demo-check") == row["attrs"]["data-demo-check"]}
              for row in in_order("data-demo-check")]
    return {"stages": stages, "labels": labels, "items": items, "download": download, "downloaded": downloaded,
            "query": query, "excerpt": excerpt, "bodies": bodies, "paths": paths, "lock": lock, "checks": checks}


def released_items():
    manifest = json.loads((RELEASE / "manifest.json").read_text(encoding="utf-8"))
    return {row["reference"]["identity"]: {**row["reference"], "body_path": row["body_path"]} for row in manifest["items"]}


def shown_size(size_bytes):
    """The size as the page writes it: kilobytes of one thousand bytes, to one decimal place."""
    return f"{size_bytes / 1000:.1f} KB"


def digest_problem(place, shown, expected):
    """A shown digest is a lower-case prefix, at least eight characters long, of the expected one."""
    if not re.fullmatch(r"[0-9a-f]{%d,64}" % SHORTEST_DIGEST, shown or "") or not expected.startswith(shown):
        return f"{place}: the page shows sha256 {shown or '(nothing)'}, and this release has {expected}"
    return ""


def search_problems(demonstration, hits):
    """Each shown reference must be the reply of a real search of this release's library, in order."""
    shown = demonstration["items"]
    problems = [] if shown else ["the search stage shows no reference"]
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
    identity, shown = demonstration["download"], demonstration["downloaded"]
    first = demonstration["items"][0]["identity"] if demonstration["items"] else ""
    if identity not in items:
        return [f"the download stage names {identity or '(nothing)'}, which this release's library does not hold"]
    item, problems = items[identity], []
    if identity != first:
        problems.append(f"the download stage names {identity}, and the search chose {first or '(nothing)'} first")
    if shown.get("size") != shown_size(item["size_bytes"]):
        problems.append(f"download: the page shows {shown.get('size')!r}, and this release has {shown_size(item['size_bytes'])!r}")
    problems.append(digest_problem("download", shown.get("digest", ""), item["digest"]))
    body = (RELEASE / item["body_path"]).read_bytes()
    if hashlib.sha256(body).hexdigest() != item["digest"]:
        problems.append(f"download: the packaged body of {identity} does not have the digest its reference names")
    text = body.decode("utf-8")
    lines = [line for line in demonstration["excerpt"].splitlines() if line.strip()]
    if not lines or not all(line in text.splitlines() for line in lines):
        problems.append(f"download: the lines the page quotes are not lines of the packaged body of {identity}")
    return [problem for problem in problems if problem]


def lock_problems(demonstration, items):
    """Every placed file is listed, with the digest of the bytes the page shows or of the library item it came from."""
    lock, bodies, paths = demonstration["lock"], demonstration["bodies"], demonstration["paths"]
    if not isinstance(lock, dict) or not isinstance(lock.get("files"), list) or not lock["files"]:
        return ["the step folder shows no readable lock file"]
    problems, listed = [], {}
    for entry in lock["files"]:
        path = entry.get("path", "")
        listed[path] = entry
        if "item" in entry:
            item = items.get(entry["item"])
            if item is None:
                problems.append(f"lock: {path} names {entry['item']}, which this release's library does not hold")
            elif entry.get("body_sha256") != item["digest"]:
                problems.append(f"lock: {path} lists body_sha256 {entry.get('body_sha256')}, and this release has {item['digest']}")
        elif path not in bodies:
            problems.append(f"lock: {path} is listed, and the page does not show its bytes")
        elif entry.get("sha256") != hashlib.sha256(bodies[path].encode("utf-8")).hexdigest():
            problems.append(f"lock: {path} lists sha256 {entry.get('sha256')}, and the bytes shown have "
                            f"{hashlib.sha256(bodies[path].encode('utf-8')).hexdigest()}")
    placed = {path for path, digest in paths.items() if digest}
    for path in sorted(placed ^ set(listed)):
        problems.append(f"lock: {path} is " + ("in the folder with a digest and not in the lock" if path in placed else "in the lock and not in the folder"))
    for path in sorted(placed & set(listed)):
        entry = listed[path]
        full = entry.get("sha256") or entry.get("body_sha256") or ""
        problems.append(digest_problem("folder row " + path, paths[path], full))
    return [problem for problem in problems if problem]


def folder_problems(demonstration):
    paths = [path for path in demonstration["paths"] if not path.endswith("/")]
    other = [path for path in paths if Path(path).suffix.lower() != ".md"]
    return [] if other else ["the step folder shows only Markdown files; harness material is any file a harness reads"]


def check_table_problems(demonstration, items):
    """The check table is what the shown script returns for the checks written in the downloaded skill."""
    rows, script = demonstration["checks"], demonstration["bodies"].get(".agents/skills/normalize-phone-numbers/scripts/normalize_phones.py", "")
    if not rows or not script:
        return ["the check stage shows no check rows, or the folder shows no script"]
    namespace = {"__name__": "shown_script"}
    exec(compile(script, "normalize_phones.py", "exec"), namespace)  # the page's own script, read from this repository
    skill = (RELEASE / items[demonstration["download"]]["body_path"]).read_text(encoding="utf-8") if demonstration["download"] in items else ""
    written = skill.split("## Checks", 1)[1].split("\n## ", 1)[0] if "## Checks" in skill else ""
    problems = []
    for row in rows:
        output, why = namespace["normalize"](row.get("input", ""))
        if (output, why) != (row.get("output"), row.get("why")):
            problems.append(f"check {row.get('input')!r}: the page shows {row.get('output')!r} ({row.get('why')}), "
                            f"and the shown script returns {output!r} ({why})")
        if "`" + row.get("input", "") + "`" not in written or "`" + row.get("output", "") + "`" not in written:
            problems.append(f"check {row.get('input')!r}: this case is not one of the checks written in the downloaded skill")
    return problems


def label_problems(demonstration):
    problems = []
    if [tuple(pair) for pair in demonstration["stages"]] != list(STAGES):
        problems.append(f"the stages are {demonstration['stages']}, and the page must show {list(STAGES)}")
    for stage, evidence in STAGES:
        label, text = demonstration["labels"].get(stage, ("", ""))
        if label != evidence or LABEL_WORDS[evidence] not in text:
            problems.append(f"the {stage} stage must say {LABEL_WORDS[evidence]!r}; it says {text or '(nothing)'!r}")
    return problems


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


class HomepageDemonstrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = PAGE.read_text(encoding="utf-8")
        cls.demonstration = read_demonstration(cls.page)
        cls.items = released_items()
        cls.hits = release_search(cls.demonstration["query"]) if cls.demonstration["query"] else []

    def test_each_stage_says_whether_it_is_recorded_or_an_illustration(self):
        self.assertEqual(label_problems(self.demonstration), [])
        unlabelled = _changed(self.demonstration, lambda copy: copy["labels"].pop("folder"))
        relabelled = _changed(self.demonstration, lambda copy: copy["labels"].update(split=["recorded", LABEL_WORDS["recorded"]]))
        self.assertEqual(len(label_problems(unlabelled)), 1, "KNOWN_WRONG: a stage without its label is reported")
        self.assertEqual(len(label_problems(relabelled)), 1, "KNOWN_WRONG: an illustration called recorded is reported")

    def test_the_search_shows_what_this_release_library_returns(self):
        self.assertEqual(self.demonstration["query"], "format phone numbers with country code")
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
        planted = self.page.replace('data-fact="digest">' + first + "<",
                                    'data-fact="digest">' + first[:-1] + ("0" if first[-1] != "0" else "1") + "<", 1)
        self.assertNotEqual(planted, self.page)
        self.assertEqual(len(search_problems(read_demonstration(planted), self.hits)), 1)

    def test_the_download_is_this_release_file_with_its_digest(self):
        self.assertEqual(download_problems(self.demonstration, self.items), [])
        wrong = _changed(self.demonstration, lambda copy: copy["downloaded"].update(digest="0" * 16))
        invented = _changed(self.demonstration, lambda copy: copy.update(excerpt="# A heading the skill never had\n"))
        self.assertEqual(len(download_problems(wrong, self.items)), 1, "KNOWN_WRONG: a digest this release does not serve")
        self.assertEqual(len(download_problems(invented, self.items)), 1, "KNOWN_WRONG: a quoted line the file does not hold")

    def test_every_placed_file_is_listed_with_the_digest_of_its_bytes(self):
        self.assertEqual(lock_problems(self.demonstration, self.items), [])
        changed_body = _changed(self.demonstration, lambda copy: copy["bodies"].update(
            {"AGENTS.md": copy["bodies"]["AGENTS.md"] + "Also rewrite the address column.\n"}))
        stale_skill = _changed(self.demonstration, lambda copy: [entry.update(body_sha256="0" * 64)
                                                                  for entry in copy["lock"]["files"] if "item" in entry])
        dropped = _changed(self.demonstration, lambda copy: copy["lock"]["files"].pop())
        self.assertEqual(len(lock_problems(changed_body, self.items)), 1, "KNOWN_WRONG: a file edited after its digest")
        # A skill digest from another release disagrees with this release and with the digest its folder row shows.
        self.assertEqual(len(lock_problems(stale_skill, self.items)), 2, "KNOWN_WRONG: a skill digest from another release")
        self.assertGreaterEqual(len(lock_problems(dropped, self.items)), 1, "KNOWN_WRONG: a placed file left out of the lock")

    def test_the_folder_holds_files_that_are_not_markdown(self):
        self.assertEqual(folder_problems(self.demonstration), [])
        only_markdown = _changed(self.demonstration, lambda copy: copy.update(
            paths={path: digest for path, digest in copy["paths"].items() if path.endswith(".md")}))
        self.assertEqual(len(folder_problems(only_markdown)), 1, "KNOWN_WRONG: a folder of Markdown files only")

    def test_the_check_table_is_what_the_shown_script_returns_for_the_skill_checks(self):
        self.assertEqual(check_table_problems(self.demonstration, self.items), [])
        wrong_output = _changed(self.demonstration, lambda copy: copy["checks"][3].update(output="+15550100"))
        invented_case = _changed(self.demonstration, lambda copy: copy["checks"].append(
            {"input": "+1 800 555 0199", "output": "+18005550199", "why": "international prefix kept"}))
        self.assertGreaterEqual(len(check_table_problems(wrong_output, self.items)), 1, "KNOWN_WRONG: a result the script does not return")
        self.assertEqual(len(check_table_problems(invented_case, self.items)), 1, "KNOWN_WRONG: a case the skill never wrote")


if __name__ == "__main__":
    unittest.main()
