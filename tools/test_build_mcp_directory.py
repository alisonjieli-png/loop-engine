"""The directory build refuses each known-wrong listing, keeps paid links out of the order and resumes a stopped sync.

Kind: development check. It needs no network and no credential: the sources are small fixtures and the registry
is a fake transport that answers from a list of pages. Each rule has known-wrong cases beside it, and each named rule
has a mutant control that patches the rule away and requires the check to fail:

- a duplicate listing (two registry names with the same packages, endpoint and repository) is one row with an alias;
- a deprecated or deleted server is left out, also when an incremental read reports the change;
- a listing without a place to get it (no package, no endpoint, no repository) is left out;
- ordering, filtering and inclusion never read a commercial field: every field is changed and the rows stay the
  same in the same order, and a mutant that ranks by the commercial kind is caught;
- the shared commercial relationship reader refuses each known-wrong record, and the packaged directory ships every
  row with the relationship none;
- a stopped registry read resumes from its saved cursor, and a later read asks only for what changed.

    PYTHONPATH=src:tools python -m unittest tools/test_build_mcp_directory.py
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import build_mcp_directory as tool  # noqa: E402
from loop_engine.core.library_ingestion.https_transport import HttpsResponse  # noqa: E402
from loop_engine.core.service_runtime import commercial_relationship as commercial  # noqa: E402
from mcp_directory import build, page, records, sources, state as directory_state  # noqa: E402
from mcp_directory.records import Exclusion  # noqa: E402

RULES = build.CategoryRules.from_file(tool.CATEGORY_RULES)
META = "io.modelcontextprotocol.registry/official"


def entry(name, *, status="active", packages=None, remotes=None, repository=None, description="Query a Postgres database",
          website=None, title=None, updated="2026-09-20T00:00:00Z", latest=True):
    server = {"name": name, "description": description, "version": "1.0.0"}
    if packages is not None:
        server["packages"] = packages
    if remotes is not None:
        server["remotes"] = remotes
    if repository is not None:
        server["repository"] = {"url": repository, "source": "github"}
    if website:
        server["websiteUrl"] = website
    if title:
        server["title"] = title
    return {"server": server, "_meta": {META: {"status": status, "isLatest": latest, "updatedAt": updated,
                                               "publishedAt": updated}}}


def npm(identifier, arguments=None):
    package = {"registryType": "npm", "identifier": identifier, "version": "1.0.0", "transport": {"type": "stdio"}}
    if arguments:
        package["packageArguments"] = arguments
    return package


FIXTURE = [
    entry("io.github.alice/postgres-tool", packages=[npm("pg-tool")], repository="https://github.com/alice/pg-tool"),
    entry("com.example/notes", remotes=[{"type": "streamable-http", "url": "https://mcp.example.com/mcp"}],
          description="Notes and reminders for your team", website="https://example.com/mcp"),
    entry("io.github.bob/weather", packages=[npm("weather-now")], repository="https://github.com/bob/weather",
          description="Weather forecast for a city"),
    entry("io.github.carol/stripe-helper", remotes=[{"type": "sse", "url": "https://stripe-helper.carol.dev/sse",
                                                     "headers": [{"name": "Authorization", "isSecret": True}]}],
          repository="https://github.com/stripe/agent-toolkit", description="Payments and invoices"),
    entry("io.github.dave/files", packages=[npm("files-mcp")], description="Read local files"),
]


def listings_of(entries):
    found = [sources.registry_listing(item) for item in entries]
    return [item for item in found if not isinstance(item, Exclusion)], [item for item in found if isinstance(item, Exclusion)]


def build_rows(entries, relationships=None):
    listings, _refused = listings_of(entries)
    offerings, _excluded = tool.build_offerings(listings, RULES, relationships or {}, {})
    return offerings


class KnownWrongListings(unittest.TestCase):
    """A duplicate listing, a deprecated server and a listing without a location, each refused by name."""

    def duplicate_problems(self, rows):
        names = [item.identity for item in rows]
        problems = []
        if "io.github.erin/pg-tool-copy" in names:
            problems.append("the duplicate listing is its own row")
        merged = next((item for item in rows if item.identity == "io.github.alice/postgres-tool"), None)
        if merged is None or "io.github.erin/pg-tool-copy" not in merged.aliases:
            problems.append("the duplicate name is not kept as an alias of the one row")
        return problems

    def test_a_duplicate_listing_is_one_row_with_an_alias(self):
        duplicate = entry("io.github.erin/pg-tool-copy", packages=[npm("pg-tool")], repository="https://github.com/alice/pg-tool")
        self.assertEqual(self.duplicate_problems(build_rows(FIXTURE + [duplicate])), [])

    def test_one_package_started_with_different_arguments_stays_several_servers(self):
        first = entry("io.github.kit/alpha", packages=[npm("kit", [{"type": "positional", "value": "alpha"}])],
                      repository="https://github.com/kit/kit")
        second = entry("io.github.kit/beta", packages=[npm("kit", [{"type": "positional", "value": "beta"}])],
                       repository="https://github.com/kit/kit")
        self.assertEqual(sorted(item.identity for item in build_rows([first, second])), ["io.github.kit/alpha", "io.github.kit/beta"])

    def test_removing_the_surface_rule_lets_the_duplicate_through(self):
        duplicate = entry("io.github.erin/pg-tool-copy", packages=[npm("pg-tool")], repository="https://github.com/alice/pg-tool")
        with mock.patch.object(build, "_surface", lambda listing: listing.key):
            self.assertTrue(self.duplicate_problems(build_rows(FIXTURE + [duplicate])))

    def test_a_deprecated_or_deleted_server_is_left_out(self):
        for status in ("deprecated", "deleted"):
            with self.subTest(status=status):
                listings, refused = listings_of(FIXTURE + [entry("io.github.old/server", status=status, packages=[npm("old-server")])])
                self.assertEqual([(item.key, item.rule) for item in refused], [("io.github.old/server", "not_active")])
                self.assertNotIn("io.github.old/server", [item.identity for item in build_rows(FIXTURE + [
                    entry("io.github.old/server", status=status, packages=[npm("old-server")])])])

    def test_removing_the_status_rule_lets_the_deprecated_server_through(self):
        with mock.patch.object(sources, "ACTIVE", "deprecated"):
            listings, _refused = listings_of([entry("io.github.old/server", status="deprecated", packages=[npm("old-server")])])
        self.assertEqual([item.key for item in listings], ["io.github.old/server"])

    def test_a_listing_without_a_location_is_left_out(self):
        bare = entry("io.github.ghost/nothing", description="A server with nowhere to get it")
        listings, refused = listings_of([bare])
        self.assertEqual(listings, [])
        self.assertEqual([(item.key, item.rule) for item in refused], [("io.github.ghost/nothing", "no_location")])
        unusable = entry("io.github.ghost/local", remotes=[{"type": "streamable-http", "url": "http://localhost:3000/mcp"}])
        self.assertEqual(listings_of([unusable])[1][0].rule, "no_location")
        docker = sources.docker_listing({"name": "empty", "type": "server", "about": {"title": "Empty"}}, "0" * 40)
        self.assertEqual(docker.rule, "no_location")

    def test_removing_the_location_rule_lets_the_bare_listing_through(self):
        bare = entry("io.github.ghost/nothing", description="A server with nowhere to get it")
        listing = replace(sources.server_listing("registry", {**bare["server"], "repository": {"url": "https://github.com/ghost/x"}},
                                                 bare["_meta"][META]), repository="")
        self.assertIsInstance(build.offering_of([listing], RULES), Exclusion)
        with mock.patch.object(build, "Exclusion", lambda *args: None):
            self.assertIsNone(build.offering_of([listing], RULES))

    def test_the_checked_packaged_files_hold_no_row_without_a_location(self):
        self.assertEqual(tool.check_packaged(), [])


class Addresses(unittest.TestCase):
    def test_only_public_https_addresses_are_kept_without_their_scheme(self):
        self.assertEqual(records.without_scheme("https://mcp.example.com/mcp/"), "mcp.example.com/mcp/")
        for refused in ("http://example.com", "https://user:pw@example.com", "https://localhost/mcp", "https://10.0.0.8/mcp",
                        "https://printer.local/mcp", "ftp://example.com", "https://example", "not an address"):
            with self.subTest(address=refused):
                self.assertEqual(records.without_scheme(refused), "")

    def test_the_lister_is_matched_with_the_code_owner_by_the_written_rule(self):
        self.assertEqual(sources.listing_origin("io.github.alice", "github.com/alice/tool", []), records.ORIGIN_MAKER)
        self.assertEqual(sources.listing_origin("io.github.carol", "github.com/stripe/agent-toolkit", []), records.ORIGIN_OTHER)
        self.assertEqual(sources.listing_origin("com.notion", "", ["mcp.notion.com"]), records.ORIGIN_MAKER)
        self.assertEqual(sources.listing_origin("ai.smithery", "github.com/222wcnm/bili", ["server.smithery.ai"]), records.ORIGIN_OTHER)
        self.assertEqual(sources.listing_origin("com.example", "", ["elsewhere.org"]), records.ORIGIN_UNKNOWN)


class Categories(unittest.TestCase):
    def test_keywords_match_whole_words_and_the_first_category_wins_a_tie(self):
        self.assertEqual(RULES.classify("postgres-tool", "Query a Postgres database"), "databases")
        self.assertEqual(RULES.classify("helper", "settings panel"), "other")
        self.assertEqual(RULES.classify("x", "CI/CD pipelines"), "developer-tools")
        record = {"record_type": build.CATEGORY_RULES_RECORD_TYPE, "fallback": {"id": "other", "label": "Other"},
                  "categories": [{"id": "a", "label": "A", "keywords": ["shared"]}, {"id": "b", "label": "B", "keywords": ["shared"]}]}
        self.assertEqual(build.CategoryRules(record).classify("shared", ""), "a")

    def test_a_rule_file_with_a_repeated_category_or_no_keywords_is_refused(self):
        for categories in ([{"id": "a", "label": "A", "keywords": ["x"]}, {"id": "a", "label": "A", "keywords": ["y"]}],
                           [{"id": "a", "label": "A", "keywords": []}]):
            with self.subTest(categories=categories), self.assertRaises(ValueError):
                build.CategoryRules({"record_type": build.CATEGORY_RULES_RECORD_TYPE, "fallback": {"id": "other", "label": "Other"},
                                     "categories": categories})


def editorial_view(offerings):
    """What a reader sees of the order, membership and filters, without any commercial field."""
    order = [item.identity for item in build.default_order(offerings)]
    by_category = {}
    for item in offerings:
        by_category.setdefault(item.category, set()).add(item.identity)
    encoded, _parts = build.encode(offerings, RULES, {"generated_at": "2026-09-24T00:00:00Z", "checked": {}})
    editorial_columns = [column for column in build.COLUMNS if column != "commercial"]
    return order, by_category, editorial_columns, [entry["rows"] for entry in encoded["categories"]]


def commercial_invariance_problems(entries, order_function=None):
    """Change every commercial field of every row in several rotations; the rows and their order must not move."""
    base = build_rows(entries)
    baseline = editorial_view(base)
    variants = commercial.invariance_variants("example.org")
    problems = []
    for shift in range(len(variants)):
        changed = [replace(item, commercial_relationship=variants[(index + shift) % len(variants)]) for index, item in enumerate(base)]
        order = [item.identity for item in (order_function or build.default_order)(changed)]
        view = editorial_view(changed)
        if order != baseline[0] or view[0] != baseline[0]:
            problems.append(f"rotation {shift} changes the order")
        if view[1] != baseline[1] or view[3] != baseline[3]:
            problems.append(f"rotation {shift} changes the rows in a category")
    return problems


class CommercialFieldsNeverRank(unittest.TestCase):
    """Ranking, ordering, filtering and inclusion read no commercial field; a mutant that does is caught."""

    def test_changing_every_commercial_field_keeps_the_rows_and_their_order(self):
        self.assertEqual(commercial_invariance_problems(FIXTURE), [])

    def test_a_ranking_that_reads_the_commercial_kind_is_caught(self):
        original = build.sort_key

        def paid_first(item):
            return (0 if item.commercial_relationship.kind == commercial.SPONSORED else 1, *original(item))
        with mock.patch.object(build, "sort_key", paid_first):
            self.assertTrue(commercial_invariance_problems(FIXTURE))

    def test_an_inclusion_rule_that_reads_the_commercial_status_is_caught(self):
        def paid_only(offerings):
            return build.default_order([item for item in offerings if item.commercial_relationship.status != commercial.ACTIVE])
        self.assertTrue(commercial_invariance_problems(FIXTURE, order_function=paid_only))

    def test_the_encoded_row_keeps_the_relationship_in_its_own_column(self):
        rows = build_rows(FIXTURE, {"io.github.bob/weather": commercial.invariance_variants("example.org")[2]})
        manifest, parts = build.encode(rows, RULES, {"generated_at": "2026-09-24T00:00:00Z", "checked": {}})
        weather = next(row for part in parts for row in part["rows"] if row[0] == "io.github.bob/weather")
        position = manifest["columns"].index("commercial")
        self.assertEqual(commercial.from_record(manifest["commercial_relationships"][weather[position]]),
                         commercial.invariance_variants("example.org")[2])
        self.assertEqual(manifest["commercial_relationships"][0], commercial.to_record(commercial.NONE))


class CommercialRelationshipRecord(unittest.TestCase):
    """The shared schema reads exactly its eight fields and refuses each known-wrong record."""

    def test_the_reader_refuses_each_known_wrong_record(self):
        good = commercial.to_record(commercial.invariance_variants("example.org")[2])
        wrong = {
            "an unknown field": {**good, "rank_boost": "1"},
            "a missing field": {key: value for key, value in good.items() if key != "reviewed_at"},
            "none with a programme": {**commercial.to_record(commercial.NONE), "program_name": "x"},
            "an unknown kind": {**good, "kind": "partner"},
            "an affiliate link without its label": {**good, "disclosure_label": ""},
            "a label that hides the kind": {**good, "disclosure_label": "Recommended"},
            "the retired label Affiliate link": {**good, "disclosure_label": "Affiliate link"},
            "an ad labelled Sponsored": {**commercial.to_record(commercial.invariance_variants("example.org")[6]), "disclosure_label": "Sponsored"},
            "an own service link with something added": {**commercial.to_record(commercial.invariance_variants("example.org")[8]),
                                                         "outbound_link": "https://owned.example.org/product?ref=baltor"},
            "a plain http link": {**good, "outbound_link": "http://go.example.org/x"},
            "user information in the link": {**good, "outbound_link": "https://user@go.example.org/x"},
            "active without a review date": {**good, "reviewed_at": ""},
            "a relationship with status none": {**good, "status": "none"},
        }
        for description, record in wrong.items():
            with self.subTest(case=description), self.assertRaises(commercial.CommercialRelationshipError):
                commercial.from_record(record)
        self.assertEqual(commercial.from_record(good).kind, commercial.AFFILIATE)

    def test_only_an_active_paid_link_or_own_service_shows_a_labelled_row_link(self):
        variants = commercial.invariance_variants("example.org")
        visible = [commercial.link_attributes(item) for item in variants if commercial.link_attributes(item)]
        paid = [item for item in visible if item["rel"] == "sponsored noopener"]
        self.assertEqual(len(paid), 2)
        self.assertTrue(all(item["label"] == "Paid link" and item["plain_address"].endswith("/product") for item in paid))
        owned = [item for item in visible if item["rel"] == "noopener"]
        self.assertEqual([item["label"] for item in owned], ["Baltor's own service"])
        self.assertEqual(owned[0]["href"], owned[0]["plain_address"])
        self.assertEqual(sum(1 for item in variants if item.is_sponsored_placement), 1)
        self.assertEqual(commercial.DISCLOSURE_LABELS[commercial.SPONSORED], "Ad")
        self.assertEqual((commercial.AD_BAND_HEADING, commercial.MAXIMUM_ADS), ("Ads", 3))

    def test_the_paid_link_sentence_shows_exactly_while_a_paid_link_is_active(self):
        variants = commercial.invariance_variants("example.org")
        self.assertFalse(commercial.shows_paid_link_notice([commercial.NONE]))
        self.assertFalse(commercial.shows_paid_link_notice([item for item in variants if not item.shows_commercial_link]))
        self.assertTrue(commercial.shows_paid_link_notice([commercial.NONE, variants[2]]))
        self.assertTrue(commercial.PAID_LINK_NOTICE.startswith("Links marked Paid link are ads"))

    def test_a_paid_link_goes_only_on_a_row_its_publisher_listed(self):
        paid = commercial.invariance_variants("example.org")[2]
        self.assertEqual(sources.listing_origin("io.github.carol", "github.com/stripe/agent-toolkit", []), records.ORIGIN_OTHER)
        with self.assertRaises(build.CommercialPlacementError):
            build_rows(FIXTURE, {"io.github.carol/stripe-helper": paid})
        with self.assertRaises(build.CommercialPlacementError):
            build_rows(FIXTURE, {"io.github.nobody/missing": paid})
        self.assertEqual(len(build_rows(FIXTURE, {"io.github.bob/weather": paid})), len(FIXTURE))

    def test_removing_the_placement_rule_lets_a_paid_link_onto_a_community_row(self):
        paid = commercial.invariance_variants("example.org")[2]
        with mock.patch.object(build, "ORIGIN_MAKER", records.ORIGIN_OTHER):
            rows = build_rows(FIXTURE, {"io.github.carol/stripe-helper": paid})
        self.assertEqual(next(item for item in rows if item.identity == "io.github.carol/stripe-helper").commercial_relationship, paid)

    def test_the_packaged_directory_ships_every_row_with_no_relationship(self):
        """Joining a programme is the owner's step; until the owner approves one, every row ships with none."""
        manifest = json.loads((tool.DATA_FOLDER / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["commercial_relationships"], [commercial.to_record(commercial.NONE)])
        record = json.loads(tool.COMMERCIAL_FILE.read_text(encoding="utf-8"))
        self.assertEqual(record["rows"], [])


class Pages:
    """A fake registry: each request answers the next page of a list, or a failure."""

    def __init__(self, pages):
        self.pages, self.queries = list(pages), []
        self.budget = type("Budget", (), {"used": 0})()

    def get(self, host, path, query=None):
        self.queries.append(dict(query or {}))
        status, body = self.pages.pop(0)
        return HttpsResponse(status, json.dumps(body).encode("utf-8") if body is not None else b"")


class IncrementalSync(unittest.TestCase):
    def test_a_stopped_read_resumes_from_its_cursor_and_a_later_read_asks_only_for_changes(self):
        with tempfile.TemporaryDirectory(prefix="directory-state-") as folder:
            state = directory_state.DirectoryState(Path(folder))
            first = {"servers": [FIXTURE[0]], "metadata": {"nextCursor": "io.github.alice/postgres-tool:1.0.0"}}
            second = {"servers": [FIXTURE[1]], "metadata": {}}
            pages = Pages([(200, first), (503, None)])
            result = directory_state.sync_registry(state, pages, now="2026-09-24T10:00:00Z")
            self.assertFalse(result["complete"])
            self.assertEqual(directory_state.DirectoryState(Path(folder)).sync["run"]["cursor"], "io.github.alice/postgres-tool:1.0.0")
            resumed = directory_state.DirectoryState(Path(folder))
            pages = Pages([(200, second)])
            result = directory_state.sync_registry(resumed, pages, now="2026-09-24T10:05:00Z")
            self.assertTrue(result["complete"])
            self.assertEqual(pages.queries[0]["cursor"], "io.github.alice/postgres-tool:1.0.0")
            self.assertEqual(sorted(resumed.entries), ["com.example/notes", "io.github.alice/postgres-tool"])
            self.assertEqual(resumed.sync["watermark"], "2026-09-24T10:00:00Z")
            deprecated = entry("com.example/notes", status="deprecated", updated="2026-09-25T00:00:00Z")
            later = directory_state.DirectoryState(Path(folder))
            pages = Pages([(200, {"servers": [deprecated], "metadata": {}})])
            directory_state.sync_registry(later, pages, now="2026-09-25T10:00:00Z")
            self.assertEqual(pages.queries[0]["updated_since"], "2026-09-24T09:00:00Z")
            self.assertNotIn("cursor", pages.queries[0])
            listings, refused = listings_of(later.entries.values())
            self.assertEqual([item.key for item in refused], ["com.example/notes"])

    def test_a_seed_page_that_does_not_hold_its_recorded_bytes_is_refused(self):
        with tempfile.TemporaryDirectory(prefix="directory-seed-") as folder:
            page_file = Path(folder) / "page.json"
            page_file.write_text(json.dumps({"servers": [FIXTURE[0]], "metadata": {}}), encoding="utf-8")
            acquisition = Path(folder) / "acquisition.json"
            acquisition.write_text(json.dumps({"sources": [{"name": "p0", "host": sources.REGISTRY_HOST, "path": sources.REGISTRY_LIST_PATH,
                                                            "sha256": "0" * 64, "quarantine_file": str(page_file)}]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                directory_state.seed_from_research(directory_state.DirectoryState(Path(folder) / "state"), [acquisition], [])


class ServedPage(unittest.TestCase):
    def test_every_generated_region_is_present_once_and_a_missing_one_is_refused(self):
        html = tool.PAGE.read_text(encoding="utf-8")
        for name in ("header", "footer", "facts", "chips", "rows", "structured-data"):
            with self.subTest(region=name):
                self.assertTrue(page.region(html, name).strip())
        with self.assertRaises(ValueError):
            page.replace_region(html.replace("<!-- generated:rows -->", ""), "rows", "")

    def test_the_first_rows_follow_the_default_order_and_mark_third_party_text(self):
        html = tool.PAGE.read_text(encoding="utf-8")
        rows = page.region(html, "rows")
        self.assertEqual(rows.count('<div class="directory-row" role="listitem"'), page.FIRST_ROWS)
        self.assertEqual(rows.count('class="row-description" data-listing-text'), page.FIRST_ROWS)
        structured = page.region(html, "structured-data")
        value = json.loads(structured.split(">", 1)[1].rsplit("</script>", 1)[0])
        self.assertEqual({item["@type"] for item in value["@graph"]}, {"CollectionPage", "Dataset"})


class HeldBack(unittest.TestCase):
    def test_a_row_with_a_credential_shaped_field_is_held_back(self):
        rows = build_rows(FIXTURE + [entry("io.github.leak/tool", packages=[npm("leak-tool")],
                                           description="Use sk-" + "a" * 24 + " to connect")])
        self.assertEqual(tool.secret_shaped(rows), ["io.github.leak/tool"])


if __name__ == "__main__":
    unittest.main()
