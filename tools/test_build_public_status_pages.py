"""The changelog, feature list and open work pages follow their records, leave out what they must, and nothing links to them.

Kind: development check over packaged files and repository records. It starts no server, opens no connection and needs
no credential. Roadmap evidence: the owner's request of September 26, 2026 for public changelog, feature list and to-do
pages that no page links to.

Each rule has a known-wrong case beside it, and the mutant control removes one guard and requires its named check to
fail:

- regeneration is idempotent, and the committed record is current (the continuation status and records index checks
  run the same comparison, and a named check fails when either stops running this command);
- every changelog line is a cleaned line of its own release record, and every library release states the package count
  of its record;
- a roadmap step, a release line, a CHANGELOG.md line or a part of the capabilities record on the reviewed exclusion
  list never appears, and no page names the search backend;
- no page, header, footer, documentation index, sitemap.xml or packaged file links to the three addresses, and each
  page carries noindex;
- the pages pass the public wording rules and the extra words the task keeps off public pages.

Run:

    PYTHONPATH=src:tools python -m unittest tools/test_build_public_status_pages.py
"""
from __future__ import annotations

import copy
import json
import re
import sys
import tempfile
import unittest
from html import unescape
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_public_status_pages as tool  # noqa: E402
from loop_engine.core.service_runtime import status_pages, web_pages  # noqa: E402
from loop_engine.core.service_runtime.web_site_map import load_site_map  # noqa: E402

ROOT = tool.ROOT
DISPLAY_NAME = "Baltor"
_HREF = re.compile(r"""\b(?:href|src|action)\s*=\s*["']([^"']*)["']""", re.IGNORECASE)
_TAG = re.compile(r"<[^>]+>")


def page_text(body: str) -> str:
    """The words of a page's own view, as a reader sees them: without the markup, and with each character reference
    read back, so an escaped apostrophe in a leaked title still matches the title."""
    start = body.find("<section data-view=")
    end = body.find("</section>", start)
    return " ".join(unescape(_TAG.sub(" ", body[start:end])).split())


def rendered(value: dict, address: str) -> str:
    return status_pages.status_page(status_pages.page_record_from_value(value), address, load_site_map(), DISPLAY_NAME)


def changelog_problems(value: dict, root: Path = ROOT) -> list:
    """Every changelog line that is not a cleaned line of its own release record, and every library count that differs."""
    records = {}
    for path in root.glob(tool.RELEASE_RECORDS):
        record = json.loads(path.read_text("utf-8"))
        records[tool.release_number(record)] = record
    problems = []
    for release in value["changelog"]["releases"]:
        if release["kind"] == "library":
            source = next((path for path in root.glob(tool.LIBRARY_RELEASES)
                           if tool.library_release(path)["number"] == release["number"]), None)
            if source is None or tool.library_release(source)["lines"] != release["lines"]:
                problems.append(f"library release {release['number']}: {release['lines']} is not its record's count")
            continue
        record = records.get(release["number"])
        if record is None:
            problems.append(f"service release {release['number']}: no release record")
            continue
        stated = {tool.clean(item) for item in tool.raw_changes(record)}
        problems.extend(f"service release {release['number']}: {line!r} is in no line of its record"
                        for line in release["lines"] if line not in stated)
        seen = (record.get("observed_after_the_restart") or {}).get("customer_visible_change") or ""
        if release["seen_after_release"] and release["seen_after_release"] != tool.clean(seen):
            problems.append(f"service release {release['number']}: the change after the release is not its record's")
    return problems


def excluded_problems(value: dict, exclusions: dict) -> list:
    """Every excluded roadmap step or release line that a page still shows."""
    todo, changelog = rendered(value, "/todo"), rendered(value, "/changelog")
    titles = {step["id"]: step["title"] for step in tool.load_roadmap()["steps"]}
    problems = []
    for row in exclusions["todo_steps"]:
        if titles[row["step"]] in page_text(todo):
            problems.append(f"{row['step']} appears on /todo")
    for row in exclusions["changelog_lines"]:
        if row["line"] in page_text(changelog):
            problems.append(f"release {row['release']}: {row['line']!r} appears on /changelog")
    for row in exclusions["earlier_lines"]:
        if row["line"] in page_text(changelog):
            problems.append(f"changelog section {row['section']}: {row['line']!r} appears on /changelog")
    features = page_text(rendered(value, "/features"))
    for row in exclusions["capability_rows"]:
        if f" {tool.words(row['path'].split('.')[-1])} " in f" {features} ":
            problems.append(f"capability {row['path']} appears on /features")
    return problems


def names_the_search_backend(text: str) -> bool:
    """The browser suite's rule no_page_names_the_search_backend, over a page's words: its two phrases, and the backend
    names the capabilities builder writes, in code form or in plain words."""
    source = tool.HTTP_SOURCE.read_text("utf-8")
    names = re.findall(r'"(?:lexical|vector)_backend": "([a-z0-9_]+)"', source)
    return bool(re.search(r"vector method|embedding model installed", text, re.IGNORECASE)) or any(
        name in text or name.replace("_", " ") in text for name in names)


def links_to_the_three(documents) -> list:
    """Every link, script or form address in the given (name, text) pairs that opens one of the three pages."""
    problems = []
    for name, text in documents:
        for value in _HREF.findall(text):
            path = value.split("#", 1)[0].split("?", 1)[0]
            if path in status_pages.ADDRESSES:
                problems.append(f"{name} links to {path}")
    return problems


def wording_problems(text: str) -> list:
    patterns, phrases = tool.wording_rules()
    problems = [pattern.pattern for pattern in patterns if pattern.search(text)]
    problems += [phrase for phrase in phrases if phrase in text]
    problems += [name for name, pattern in tool.INTERNAL_MARKERS if name in ("runtime vocabulary", "refused word")
                 and pattern.search(text)]
    problems += ["dash"] if re.search("[—–]", text) else []
    return problems


class Generation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.value = tool.build()

    def test_regeneration_is_idempotent(self):
        self.assertEqual(tool.render(tool.build()), tool.render(self.value))
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "record.json"
            self.assertEqual(tool.main(["--output", str(output), "--check"]), 1)
            self.assertEqual(tool.main(["--output", str(output)]), 0)
            first = output.read_bytes()
            self.assertEqual(tool.main(["--output", str(output)]), 0)
            self.assertEqual(output.read_bytes(), first)
            self.assertEqual(tool.main(["--output", str(output), "--check"]), 0)
            output.write_text(first.decode("utf-8").replace("packages served", "packages shown", 1), "utf-8")
            self.assertEqual(tool.main(["--output", str(output), "--check"]), 1)

    def test_the_committed_record_is_current(self):
        self.assertEqual(tool.main(["--check"]), 0, "run python tools/build_public_status_pages.py and commit the record")

    def test_the_roadmap_and_records_commands_run_the_pages_command(self):
        """A session runs the continuation status generator after a roadmap edit and the records index builder after a
        dated record; both run this command with their own mode, so the pages have no second command to forget. A run
        that writes to another output, as their own tests do, leaves the packaged record alone."""
        import build_continuation_status
        import build_records_index
        calls = []
        with mock.patch.object(tool, "main", lambda argv=None: calls.append(list(argv or [])) or 7):
            stale = "regenerate docs/roadmap/CONTINUATION-STATUS.md and docs/RECORDS-INDEX.md first"
            self.assertEqual(build_continuation_status.main(["--check"]), 7, stale)
            self.assertEqual(build_records_index.main(["--check"]), 7, stale)
            with tempfile.TemporaryDirectory() as folder:
                self.assertEqual(build_continuation_status.main(["--output", str(Path(folder) / "status.md")]), 0)
                self.assertEqual(build_records_index.main(["--output", str(Path(folder) / "index.md")]), 0)
        self.assertEqual(calls, [["--check"], ["--check"]])

    def test_the_packaged_record_is_read_by_its_reader(self):
        record = status_pages.load_page_record()
        self.assertEqual(record.value["record_type"], status_pages.RECORD_TYPE)
        for wrong in ({**self.value, "record_type": "public_status_pages/v2"}, {**self.value, "extra": 1},
                      {**self.value, "todo": {**self.value["todo"], "listed": self.value["todo"]["listed"] + 1}}):
            with self.assertRaises(status_pages.StatusPageError):
                status_pages.page_record_from_value(wrong)
        reversed_value = copy.deepcopy(self.value)
        reversed_value["changelog"]["releases"].reverse()
        with self.assertRaises(status_pages.StatusPageError):
            status_pages.page_record_from_value(reversed_value)

    def test_every_changelog_line_matches_its_release_record(self):
        self.assertEqual(changelog_problems(self.value), [])
        releases = self.value["changelog"]["releases"]
        self.assertTrue(any(release["kind"] == "service" and release["lines"] for release in releases))
        self.assertTrue(any(release["kind"] == "library" for release in releases))
        # Known-wrong cases: an invented line, and a library count that is not its record's.
        wrong = copy.deepcopy(self.value)
        service = next(release for release in wrong["changelog"]["releases"] if release["kind"] == "service" and release["lines"])
        service["lines"].append("A feature nobody released.")
        library = next(release for release in wrong["changelog"]["releases"] if release["kind"] == "library")
        library["lines"] = ["7 packages served."]
        self.assertEqual(len(changelog_problems(wrong)), 2)

    def test_each_library_release_reads_the_count_and_time_its_record_states(self):
        # Known answers, read by a person from the fact tables of the dated Community release records, which never change:
        # release 1 states its time only in prose, release 6 names its count in a Served row and its time in a Release row.
        expected = {1: ("2026-09-25T16:38:00Z", 93), 2: ("2026-09-25T22:35:00Z", 316), 3: ("2026-09-25T23:22:00Z", 1629),
                    4: ("2026-09-26T00:58:00Z", 3276), 5: ("2026-09-26T06:18:00Z", 4812), 6: ("2026-09-26T11:55:00Z", 6398)}
        found = {release["number"]: release for release in self.value["changelog"]["releases"] if release["kind"] == "library"}
        for number, (at, packages) in expected.items():
            with self.subTest(release=number):
                self.assertEqual((found[number]["at"], found[number]["lines"]), (at, [f"{packages:,} packages served."]))
        with tempfile.TemporaryDirectory() as folder:
            record = Path(folder) / "community-release-9-2026-09-27" / "README.md"
            record.parent.mkdir()
            record.write_text("# A release\n\n| Fact | Value |\n|---|---|\n| Served | 12 packages |\n", "utf-8")
            with self.assertRaises(tool.BuildError):  # a record with a count and no time is refused, never guessed
                tool.library_release(record)

    def test_the_latest_release_record_is_on_the_changelog(self):
        numbers = [tool.release_number(json.loads(path.read_text("utf-8"))) for path in ROOT.glob(tool.RELEASE_RECORDS)]
        page = rendered(self.value, "/changelog")
        self.assertIn(f'data-release="service-release-{max(numbers)}"', page)
        for release in self.value["changelog"]["releases"]:
            self.assertIn(f'data-release="{release["kind"]}-release-{release["number"]}"', page)

    def test_an_excluded_step_or_line_never_appears(self):
        exclusions = tool.load_exclusions()
        self.assertTrue(exclusions["todo_steps"] and exclusions["changelog_lines"])
        self.assertEqual(excluded_problems(self.value, exclusions), [])

    def test_an_internal_line_is_left_out(self):
        site_map = json.loads(tool.SITE_MAP.read_text("utf-8"))
        public = tool.PublicText(site_map, json.loads(tool.LAYOUT_STANDARD.read_text("utf-8")))
        for line in ("Anchored to 9a483df.", "Moved to tools/red_team.py.", "The reads_fs default.",
                     "Reads service_provisioning_request/v2.", "Runs as a Loop.", "The runtime answers.",
                     "Deployed to baltor-pilot.fly.dev.", "Served at /admin/mcp.", "Costs $49 a month.",
                     "A planned page.", "Run 36243640251 passed.", "Links to /todo.", "A receipt for each call."):
            with self.subTest(line=line):
                self.assertTrue(public.problem(line), line)
        for line in ("The library page counts every kind of harness file.", "Served at /library and on docs.baltor.ai.",
                     "The plan is $29 a month."):
            with self.subTest(line=line):
                self.assertEqual(public.problem(line), "", line)
        self.assertEqual(tool.clean("the change (S-6.84) and (commits e0d965bd and c1071922)"), "The change and.")

    def test_the_exclusion_list_states_its_review_and_refuses_stale_entries(self):
        exclusions = tool.load_exclusions()
        self.assertIn("reviewed by a person or by an independent verifier", exclusions["review"])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "exclusions.json"
            path.write_text(json.dumps({**exclusions, "review": "Nobody reviews this."}), "utf-8")
            with self.assertRaises(tool.BuildError):
                tool.load_exclusions(path)
        site_map = json.loads(tool.SITE_MAP.read_text("utf-8"))
        public = tool.PublicText(site_map, json.loads(tool.LAYOUT_STANDARD.read_text("utf-8")))
        roadmap = tool.load_roadmap()
        with self.assertRaises(tool.BuildError):
            tool.todo(roadmap, {**exclusions, "todo_steps": [{"step": "S-9.99", "reason": "no such step"}]}, public)
        with self.assertRaises(tool.BuildError):
            tool.changelog(public, {**exclusions, "changelog_lines": [{"release": 37, "line": "Never written.",
                                                                        "reason": "no such line"}]})
        with self.assertRaises(tool.BuildError):
            tool.changelog(public, {**exclusions, "earlier_lines": [{"section": "Added", "line": "Never written.",
                                                                      "reason": "no such line"}]})
        with self.assertRaises(tool.BuildError):
            tool.features(site_map, json.loads(tool.LAYOUT_STANDARD.read_text("utf-8")), public,
                          {**exclusions, "capability_rows": [{"path": "retrieval.no_such_part", "reason": "no such part"}]})
        # A line a section holds is refused under another section's heading: the list names exact places.
        moved = [{**row, "section": "Fixed"} for row in exclusions["earlier_lines"][:1]]
        with self.assertRaises(tool.BuildError):
            tool.changelog(public, {**exclusions, "earlier_lines": moved})
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "exclusions.json"
            path.write_text(json.dumps({**exclusions, "reviews": [{"reviewer": "", "date": "2026-09-26", "entries": []}]}),
                            "utf-8")
            with self.assertRaises(tool.BuildError):  # a review that names no reviewer is refused
                tool.load_exclusions(path)
            path.write_text(json.dumps({**exclusions, "todo_steps": [{"step": "S-6.1", "reason": " "}]}), "utf-8")
            with self.assertRaises(tool.BuildError):  # an entry without its reason is refused
                tool.load_exclusions(path)

    def test_the_todo_lists_open_steps_only_with_plain_status_words(self):
        roadmap = tool.load_roadmap()
        done = {step["id"] for step in roadmap["steps"] if step["status"] in tool.DONE_STATUSES}
        listed = [step for group in self.value["todo"]["groups"] for step in group["steps"]]
        self.assertTrue(listed)
        self.assertFalse({step["step"] for step in listed} & done)
        self.assertEqual(len({step["step"] for step in listed}), len(listed))
        self.assertTrue({step["status"] for step in listed} <= set(tool.STATUS_WORDS.values()))
        self.assertEqual(self.value["todo"]["live"], sum(1 for step in roadmap["steps"] if step["status"] == "live_qualified"))
        page = rendered(self.value, "/todo")
        for field in ("next_local_work", "evidence"):
            for step in roadmap["steps"]:
                text = str(step.get(field) or "")
                if len(text) > 40 and step["status"] not in tool.DONE_STATUSES:
                    self.assertNotIn(text[:40], page)

    def test_the_features_come_from_their_records(self):
        features = self.value["features"]
        layout = json.loads(tool.LAYOUT_STANDARD.read_text("utf-8"))
        self.assertEqual(features["plan"], layout["price"]["phrase"])
        site_map = json.loads(tool.SITE_MAP.read_text("utf-8"))
        indexed = [page["address"] for page in site_map["pages"] if page["indexed"]]
        self.assertEqual([page["address"] for group in features["page_groups"] for page in group["pages"]],
                         [address for group in site_map["groups"] for address in indexed
                          if next(page for page in site_map["pages"] if page["address"] == address)["group"] == group])
        recipes = json.loads(tool.CLIENT_RECIPES.read_text("utf-8"))["recipes"]
        self.assertEqual(features["harnesses"], [recipe["name"] for recipe in recipes])
        rows = {(row["section"], row["feature"]): row for row in features["capabilities"]}
        self.assertEqual(rows[("Protocol", "Transport")]["value"], "streamable http")
        self.assertFalse(rows[("Website", "Registration available")]["fixed"])


class Discoverability(unittest.TestCase):
    """Nothing links to the three pages, each carries noindex, and none is in sitemap.xml."""

    def served(self):
        from test_website_site_map import served_site
        return served_site()

    def test_no_page_links_to_the_three_addresses(self):
        site = self.served()
        documents = [(page.address, (site.answer(page.address) or ("", ""))[0]) for page in site.site_map.pages]
        self.assertTrue(all(text for _name, text in documents))
        self.assertEqual(links_to_the_three(documents), [])
        header = set().union(*site.site_map.header_paths().values()) | site.site_map.footer_paths()
        self.assertFalse(header & set(status_pages.ADDRESSES))
        for address in status_pages.ADDRESSES:
            page = site.site_map.page(address)
            self.assertEqual((page.linked_from, page.indexed), ((), False))
            self.assertIn("no page linking to them", page.unlinked_reason)
        index = (ROOT / "src/loop_engine/core/service_runtime/web_assets/documentation-index.json").read_text("utf-8")
        packaged = [(str(path.relative_to(ROOT)), path.read_text("utf-8", errors="replace"))
                    for path in (ROOT / "src/loop_engine/core/service_runtime/web_assets").rglob("*")
                    if path.is_file() and path.suffix in (".html", ".js", ".json", ".md") and path.name != status_pages.RECORD_FILE]
        self.assertEqual(links_to_the_three(packaged), [])
        for address in status_pages.ADDRESSES:
            self.assertNotIn(f'"{address}"', index)
        # Known-wrong case: a page that links to one of them is reported.
        self.assertEqual(len(links_to_the_three([("/", '<a href="/todo#steps">Open work</a>')])), 1)

    def test_each_page_carries_noindex_and_stays_out_of_sitemap_xml(self):
        site_map = load_site_map()
        sitemap = web_pages.sitemap_xml(site_map).decode("utf-8")
        for address in status_pages.ADDRESSES:
            body, media = status_pages.rendered(address, "GET", DISPLAY_NAME)
            self.assertEqual(media, web_pages.HTML_MEDIA_TYPE)
            self.assertIn(b'<meta name="robots" content="noindex">', body)
            self.assertNotIn(site_map.canonical_origin + address + "<", sitemap)
        self.assertIsNone(status_pages.rendered("/todo", "POST", DISPLAY_NAME))
        self.assertIsNone(status_pages.rendered("/todos", "GET", DISPLAY_NAME))

    def test_the_pages_pass_the_public_wording_rules(self):
        for address in status_pages.ADDRESSES:
            body, _media = status_pages.rendered(address, "GET", DISPLAY_NAME)
            with self.subTest(address=address):
                self.assertEqual(wording_problems(page_text(body.decode("utf-8"))), [])
        self.assertTrue(wording_problems("A planned step of the runtime — with a receipt."))

    def test_no_page_names_the_search_backend(self):
        # The owner's rule for every page (roadmap S-6.39 and S-6.184), which the browser suite checks on the workspace.
        for address in status_pages.ADDRESSES:
            body, _media = status_pages.rendered(address, "GET", DISPLAY_NAME)
            with self.subTest(address=address):
                self.assertFalse(names_the_search_backend(page_text(body.decode("utf-8"))))
        # Known-wrong cases: the old workspace note, and a backend name in plain words.
        self.assertTrue(names_the_search_backend("Installed vector method: deterministic character hash."))
        self.assertTrue(names_the_search_backend("Retrieval Lexical backend sqlite fts5"))
        self.assertFalse(names_the_search_backend("Search returns references."))


class RemovedGuards(unittest.TestCase):
    """The mutant controls: with one guard removed, its named check fails."""

    def test_a_removed_guard_fails_its_named_check(self):
        exclusions = tool.load_exclusions()
        # Each part of the reviewed list, emptied on its own, lets one of its entries onto a page, and the named check
        # test_an_excluded_step_or_line_never_appears (through excluded_problems) reports exactly that part.
        # An excluded title with an apostrophe, escaped in the markup, is still found once its entry is removed.
        apostrophe = next(row for row in exclusions["todo_steps"] if "'" in tool.load_roadmap_titles()[row["step"]])
        with mock.patch.object(tool, "load_exclusions", lambda path=tool.EXCLUSIONS: {
                **exclusions, "todo_steps": [row for row in exclusions["todo_steps"] if row != apostrophe]}):
            self.assertEqual(excluded_problems(tool.build(), exclusions), [f"{apostrophe['step']} appears on /todo"])
        for part, marker in (("todo_steps", "appears on /todo"), ("changelog_lines", "release "),
                             ("earlier_lines", "changelog section "), ("capability_rows", "appears on /features")):
            with self.subTest(part=part), mock.patch.object(tool, "load_exclusions",
                                                            lambda path=tool.EXCLUSIONS, part=part: {**exclusions, part: []}):
                problems = excluded_problems(tool.build(), exclusions)
                self.assertTrue(problems, f"emptying {part} must show one of its entries")
                self.assertTrue(all(marker in problem for problem in problems), problems)
        with mock.patch.object(tool.PublicText, "problem", lambda self, line: ""):
            leaking = tool.build()
        self.assertTrue(wording_problems(" ".join(line for release in leaking["changelog"]["releases"]
                                                  for line in release["lines"])),
                        "removing the internal-term rules must let a refused word through")


if __name__ == "__main__":
    unittest.main()
