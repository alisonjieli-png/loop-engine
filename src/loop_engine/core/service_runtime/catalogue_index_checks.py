"""The conformance kit of the catalogue search index slot (catalogue_index_engines), run against every engine.

Every engine the image offers answers the same edge, so the kit runs the same
cases against each, on real temporary service stores, body folders and index
folders; no network, model or provider is used. The judged queries of
`examples/30_search_quality` are run against every engine by
`tools/test_catalogue_index_engines.py`, which reads repository files this
installed package does not carry.

```text
Kit
├── edge           each engine is a CatalogueSearchIndexEngine and states its size and stats
├── exactness      the disk engine's pools equal the in-memory engine's on a fresh build, for lexical and hybrid
│                  queries, with and without filters, at several pool sizes; float32 accumulation and a
│                  shortened term list are known-wrong engines the kit must catch
├── service path   the same served hits, summary, file population and served count through the provisioning
│                  authority, for a version 2 release, an internal-attribute filter refused on both
├── withdrawal     an item withdrawn after the index was built is never returned and never read
├── requests       manifest, read, list, discover, the library rows and the Public Good file projection answer
│                  as on the in-memory view; a manifest or read parses only the record it names and a walk over
│                  the library parses each record once a walk (controls: every grant materialized, the library copied)
├── coordination   one build at a time under an index root, a lost index built again, and the indexes of releases
│                  no longer kept removed while the active release's, and during a grace its predecessor's, stay
├── http           the loopback serving checks over a real socket with the host on the disk engine (when the
│                  serving packages are installed): search, filters, downloads by path, a hot swap, a request
│                  that finishes on the view it started with
├── commands       catalogue-formats, publish-catalogue of a version 2 bundle and index-catalogue through the
│                  service entry point, a host start on the disk view, and a swap that renders the new view's
│                  library page before installing it
├── overlay        a later release served as base + delta never returns a removed or replaced record, and its
│                  vector pools equal a fresh build's
├── selection      an engine the host names is refused at start when it cannot run, never replaced
├── integrity      an index file changed after its build is refused when verified; an unfinished build is unread
└── prototype      engine (c), when lancedb is installed: the edge, filters exact against the baseline
```
"""
from __future__ import annotations

import json
from pathlib import Path
import random
import tempfile
from unittest.mock import patch

from .records import ServiceRuntimeError

STARTER_SCHEMA = {"record_type": "catalogue_attribute_schema/v1", "attributes": [
    {"name": "cited_source", "type": "keyword", "filterable": True, "shown": True},
    {"name": "origin_layer", "type": "choice", "choices": ["context_intelligence", "code_intelligence"],
     "filterable": True, "shown": True},
    {"name": "catalogued_on", "type": "date", "filterable": True, "shown": True},
    {"name": "domain", "type": "keyword_list", "searchable": True, "filterable": True, "shown": True},
    {"name": "batch", "type": "keyword", "visibility": "internal"}]}
WORDS = ("audit training data split leakage review nurse intake question chart deploy release safety test "
         "schema migration index search vector cache latency budget report summary customer record duplicate "
         "match casing name address invoice payment refund ledger").split()


def refused(action, code=None):
    try:
        action()
    except ServiceRuntimeError as error:
        return code is None or error.code == code
    except Exception:  # noqa: BLE001 - a crash is not a typed refusal
        return False
    return False


def _schema():
    from .catalogue_schema import CatalogueAttributeSchema
    return CatalogueAttributeSchema.from_dict(STARTER_SCHEMA)


def _entries(count, seed=7, schema=None, version=1, start=0):
    from .catalogue_search import IndexEntry
    schema = schema or _schema()
    rng = random.Random(seed * 31 + version)
    rows = []
    for index in range(start, start + count):
        values = schema.validate_values({
            "cited_source": f"src/module_{rng.randint(0, 9)}.py",
            "origin_layer": rng.choice(["context_intelligence", "code_intelligence"]),
            "catalogued_on": f"2026-09-{rng.randint(1, 28):02d}",
            "domain": sorted(set(rng.sample(WORDS, rng.randint(1, 3)))), "batch": "check"})
        text = (f"skill_{index:05d} skill harness_local version {version} "
                + " ".join(rng.choice(WORDS) for _ in range(rng.randint(4, 24))) + " " + schema.search_text(values))
        rows.append(IndexEntry(f"skill_{index:05d}", text, values))
    return rows


def _queries(seed=11, count=60):
    rng = random.Random(seed)
    return ([" ".join(rng.choice(WORDS) for _ in range(rng.randint(1, 5))) for _ in range(count)]
            + ["", "zzzz qqqq", "skill_00042", "audits deployments reviewing"])


FILTERS = (None, [("origin_layer", "any_of", ("code_intelligence",))],
           [("catalogued_on", "range", ("2026-09-05", "2026-09-12"))],
           [("domain", "any_of", ("audit", "nurse")), ("cited_source", "any_of", ("src/module_1.py",
                                                                                  "src/module_2.py"))])


def _pools(index, queries, pools=(1, 20, 80)):
    rows = []
    for query in queries:
        for conditions in FILTERS:
            for mode in ("lexical", "hybrid"):
                for pool in pools:
                    eligible = index.eligible(conditions) if conditions else None
                    rows.append(index.rank(query, mode=mode, pool=pool, eligible=eligible))
    return rows


def _edge_and_exactness_checks(check, root):
    from . import catalogue_disk_index
    from .catalogue_disk_index import DiskIndex, DiskSearchIndex, build_disk_index
    from .catalogue_index_engines import CatalogueSearchIndexEngine, index_size
    from .catalogue_search import ReleaseSearchIndex
    schema, entries = _schema(), _entries(1500)
    baseline = ReleaseSearchIndex(entries, schema)
    disk = DiskSearchIndex(DiskIndex(build_disk_index(Path(root) / "exact", entries, schema), verify_files=True),
                           schema)
    check("every_engine_speaks_the_catalogue_search_index_edge",
          all(isinstance(index, CatalogueSearchIndexEngine) for index in (baseline, disk))
          and index_size(baseline) == index_size(disk) == len(entries)
          and disk.stats()["stored_on_disk"] is True)
    queries = _queries()
    expected = _pools(baseline, queries)
    check("the_disk_engine_ranks_exactly_as_the_in_memory_engine_on_a_fresh_build",
          _pools(disk, queries) == expected)
    original = catalogue_disk_index.DiskIndex.vector_top

    def float32_vector_top(self, weights, pool, keep_mask, floor):
        numpy = self.numpy
        scores = numpy.zeros(self.size, dtype=numpy.float32)
        for dimension, weight in weights:
            scores += self.columns[dimension] * numpy.float32(weight)
        accepted = scores > floor
        if keep_mask is not None:
            accepted &= keep_mask
        rows = [(float(scores[position]), int(position)) for position in numpy.flatnonzero(accepted)]
        return sorted(rows, key=lambda row: (-row[0], row[1]))[:pool + 1]
    with patch.object(catalogue_disk_index.DiskIndex, "vector_top", float32_vector_top):
        check("a_disk_engine_that_adds_scores_in_float32_is_detected", _pools(disk, queries) != expected)
    with patch.object(catalogue_disk_index, "LEXICAL_TERMS", 2):
        check("a_disk_engine_that_shortens_the_query_is_detected", _pools(disk, queries) != expected)
    check("the_float32_control_left_the_engine_unchanged",
          catalogue_disk_index.DiskIndex.vector_top is original and _pools(disk, queries[:5]) == _pools(
              baseline, queries[:5]))


def _overlay_checks(check, root):
    from .catalogue_disk_index import DiskIndex, DiskSearchIndex, build_disk_index
    schema = _schema()
    base_entries = _entries(1200)
    removed = {f"skill_{index:05d}" for index in range(0, 1200, 37)}
    changed = {f"skill_{index:05d}" for index in range(5, 1200, 53)} - removed
    replacements = {entry.identity: entry for entry in _entries(1200, version=2) if entry.identity in changed}
    added = _entries(60, version=3, start=5000)
    served = sorted([replacements.get(entry.identity, entry) for entry in base_entries if entry.identity not in removed]
                    + added, key=lambda entry: entry.identity)
    delta_entries = sorted(list(replacements.values()) + added, key=lambda entry: entry.identity)
    base = DiskIndex(build_disk_index(Path(root) / "overlay-base", base_entries, schema))
    fresh = DiskSearchIndex(DiskIndex(build_disk_index(Path(root) / "overlay-fresh", served, schema)), schema)
    delta = DiskIndex(build_disk_index(Path(root) / "overlay-delta", delta_entries, schema))
    gone = base.positions_of(sorted(removed | changed))
    overlay = DiskSearchIndex(base, schema, removed=frozenset(gone.values()), delta=delta)
    queries = _queries(13, 40)
    stale, vectors_equal, total = False, True, 0
    for query in queries:
        for conditions in FILTERS:
            pools, _ = overlay.rank(query, mode="hybrid", pool=40,
                                    eligible=overlay.eligible(conditions) if conditions else None)
            reference, _ = fresh.rank(query, mode="hybrid", pool=40,
                                      eligible=fresh.eligible(conditions) if conditions else None)
            total += 1
            stale = stale or any(identity in removed for identity, _score in pools["lexical"] + pools["vector"])
            vectors_equal = vectors_equal and pools["vector"] == reference["vector"]
    check("an_overlay_never_returns_a_removed_item", not stale and overlay.size == fresh.size)
    check("an_overlay_scores_vectors_exactly_as_a_fresh_build", vectors_equal and total)
    replaced = [identity for identity in sorted(changed)
                if overlay.rank(identity, mode="lexical", pool=3)[0]["lexical"][:1]
                and overlay.rank(identity, mode="lexical", pool=3)[0]["lexical"][0][0] == identity]
    check("an_overlay_serves_the_replacing_version_of_a_changed_item", len(replaced) == len(changed))
    with patch.object(DiskSearchIndex, "_keep", lambda self, part_mask, removed_mask: (
            None if part_mask is None else (lambda position: bool(part_mask[position])))):
        leaking = DiskSearchIndex(base, schema, removed=frozenset(gone.values()), delta=delta)
        found = any(identity in removed for query in queries
                    for identity, _ in leaking.rank(query, mode="lexical", pool=40)[0]["lexical"])
        check("removed_overlay_mask_is_detected", found)


def _service_path_checks(check, root):
    from .catalogue_disk_view import DiskCatalogueView
    from .catalogue_releases import withdraw
    from .catalogue_search import authorized_hits
    from .catalogue_segment_checks import SegmentFixture
    from .catalogue_serving import CatalogueSourceSettings, next_view, state_token, store_view
    from .provisioning import DurableProvisioningBinding
    case = SegmentFixture(root)
    base = case.base
    lines = [base.line(f"skill_{index:03d}", f"Skill {index} about " + " ".join(WORDS[(index * k) % len(WORDS)]
                                                                         for k in (1, 3, 7)),
                       attributes={"domain": [WORDS[index % len(WORDS)]],
                                   "origin_layer": ["context_intelligence", "code_intelligence"][index % 2]})
             for index in range(90)]
    case.publish(lines)
    (Path(root) / "index").mkdir()
    disk_settings = CatalogueSourceSettings("store", str(Path(root) / "bodies"),
                                            record_type="service_catalogue_source/v2",
                                            search_engine="sqlite_disk_index", index_root=str(Path(root) / "index"))

    def build(settings):
        return store_view(base.config, settings, license_policy=base.license_policy, family_policy=base.family_policy)
    memory, disk = build(base.settings), build(disk_settings)

    def hits(view, query, mode, filters=None):
        binding = DurableProvisioningBinding(base.runtime, view.catalogue, view.qualification_resolver,
                                             view.body_reader, view=view)
        principal = base.runtime.authenticate_key(base.key.key)

        def authorize(candidates):
            listing = binding.invoke_for_principal(principal, "list", view=view, candidates=candidates)
            return {row["identity"]: row for row in listing["items"]}
        fields = {"query": query, "mode": mode, "top_n": 5, **({"filters": filters} if filters else {})}
        return authorized_hits(view, fields, authorize)[0]
    requests = [(query, mode, filters) for query in ("audit data", "nurse intake question", "deploy release safety",
                                                    "skill 12", "chart")
                for mode in ("lexical", "hybrid")
                for filters in (None, {"origin_layer": {"equals": "code_intelligence"}},
                                {"domain": {"any_of": ["audit", "nurse"]}})]
    check("the_disk_view_serves_the_same_hits_through_the_provisioning_authority",
          isinstance(disk, DiskCatalogueView)
          and all(hits(memory, *request) == hits(disk, *request) for request in requests))
    check("the_disk_view_reports_the_same_summary_population_and_served_count",
          {**memory.summary(), "built_at": 0} == {**disk.summary(), "built_at": 0}
          and memory.file_population() == disk.file_population()
          and memory.served_package_count() == disk.served_package_count() == len(lines))
    check("a_filter_on_an_internal_attribute_is_refused_by_every_engine",
          all(refused(lambda view=view: hits(view, "audit", "lexical", {"batch": {"equals": "x"}}),
                      "search_filter_not_allowed") for view in (memory, disk)))
    withdraw(base.context, identity="skill_012", note_text="withdrawn by the check")
    token = state_token(base.config)
    after = next_view(disk, token, base.config, disk_settings, license_policy=base.license_policy,
                      family_policy=base.family_policy)
    check("an_item_withdrawn_after_the_index_was_built_is_never_returned_or_read",
          "skill_012" not in after.catalogue.items and after.served_package_count() == len(lines) - 1
          and all(identity != "skill_012" for identity, _score, _modes in hits(after, "Skill 12 about", "lexical"))
          and refused(lambda: disk.read_package_entries("skill_012", disk.package_of("skill_012").files),
                      "item_withdrawn"))
    from . import catalogue_disk_view
    with patch.object(catalogue_disk_view.DiskItemSource, "with_left_out", lambda self, more: self):
        leaking = next_view(disk, token, base.config, disk_settings, license_policy=base.license_policy,
                            family_policy=base.family_policy)
        check("removed_withdrawal_rule_of_the_disk_view_is_detected", "skill_012" in leaking.catalogue.items)


def _request_path_checks(check, root):
    """Manifest, read, list, discover, the library rows and the Public Good file projection on the disk view.

    Each answers as the in-memory view does. A manifest or read parses only the record it names, and a walk over
    the whole library parses each record once; the known-wrong controls materialize every grant for a manifest and
    copy the library before checking it, and the kit must see both."""
    from . import catalogue_disk_view
    from . import provisioning as provisioning_module
    from .catalogue_disk_view import DiskCatalogueView
    from .catalogue_segment_checks import SegmentFixture
    from .catalogue_serving import CatalogueSourceSettings, store_view
    from .library_page import library_rows
    from .provisioning import DurableProvisioningBinding
    from .public_good_files import collection
    case = SegmentFixture(root)
    base = case.base
    names = [f"skill_{index:03d}" for index in range(120)]
    case.publish(case.lines(names, text=lambda name: f"Skill {name} about "
                                                       + " ".join(WORDS[(len(name) * k + int(name[-3:])) % len(WORDS)]
                                                                  for k in (1, 3, 7))))
    (Path(root) / "index").mkdir()
    disk_settings = CatalogueSourceSettings("store", str(Path(root) / "bodies"),
                                            record_type="service_catalogue_source/v2",
                                            search_engine="sqlite_disk_index", index_root=str(Path(root) / "index"))

    def build(settings):
        return store_view(base.config, settings, license_policy=base.license_policy, family_policy=base.family_policy)

    def binding_of(view):
        return DurableProvisioningBinding(base.runtime, view.catalogue, view.qualification_resolver,
                                          view.body_reader, view=view)

    def plain(answer):
        return {key: value for key, value in answer.items() if not key.startswith("meter")}

    def answers(view, label):
        binding = binding_of(view)
        return {"manifest": plain(binding.invoke(base.key.key, "manifest", identity="skill_042")),
                "read": plain(binding.invoke(base.key.key, "read", identity="skill_042",
                                             request_id=f"index-kit-read-{label}")),
                "list": plain(binding.invoke(base.key.key, "list")),
                "discover": plain(binding.invoke(base.key.key, "discover"))}
    memory, disk = build(base.settings), build(disk_settings)
    check("the_disk_view_answers_manifest_read_list_and_discover_as_the_in_memory_view",
          isinstance(disk, DiskCatalogueView) and answers(memory, "memory") == answers(disk, "disk")
          and len(answers(disk, "again")["list"]["items"]) == len(names))
    check("the_disk_view_gives_the_library_page_the_same_rows", library_rows(memory) == library_rows(disk)
          and len(library_rows(disk)) == len(names))
    check("the_public_good_file_projection_reads_a_disk_view",
          collection(disk, binding_of(disk).public_good.snapshot(disk))
          == collection(memory, binding_of(memory).public_good.snapshot(memory)))
    entries = disk.package_of("skill_042").files
    check("the_disk_view_delivers_the_same_package_files",
          [data for data, _entry in disk.read_package_entries("skill_042", entries)]
          == [data for data, _entry in memory.read_package_entries("skill_042", memory.package_of("skill_042").files)]
          and len(entries) >= 1)
    # A served view parses a package on its first use; one that names other bytes than its item is refused then.
    _position, stored_version, stored = disk.disk.base.records(["skill_042"])["skill_042"]
    record = json.loads(stored)
    altered = json.loads(stored)
    altered["package"]["files"][0]["digest"] = "0" * 64
    check("a_stored_package_that_disagrees_with_its_item_is_refused_on_first_use",
          catalogue_disk_view._disk_item(record, stored_version, None, None, None).package.files
          and refused(lambda: catalogue_disk_view._disk_item(altered, stored_version, None, None, None).package,
                      "catalogue_release_digest_mismatch"))

    def parsed_by(operation, **fields):
        view = build(disk_settings)  # opens the built index with an empty record cache
        start = view.disk.records_parsed
        binding_of(view).invoke(base.key.key, operation, **fields)
        return view.disk.records_parsed - start
    narrowed = parsed_by("manifest", identity="skill_042")
    narrowed_read = parsed_by("read", identity="skill_042", request_id="index-kit-parsed-read")
    check("a_manifest_or_read_on_the_disk_view_parses_only_the_record_it_names",
          1 <= narrowed <= 2 and 1 <= narrowed_read <= 2)
    with patch.object(provisioning_module, "grant_scope", lambda operation, fields, candidates: candidates):
        everything = parsed_by("manifest", identity="skill_042")
    check("a_manifest_that_materializes_every_grant_is_detected", everything >= len(names))
    # A cache smaller than the library, as a large library's always is, with batches that fit in it.
    with patch.object(catalogue_disk_view, "RECORD_CACHE", 32), patch.object(catalogue_disk_view, "BULK_BATCH", 16):
        walked = parsed_by("list")
        with patch.object(catalogue_disk_view.DiskMapping, "walks_without_copy", False):
            copied = parsed_by("list")
    # One walk materializes the account's grants and one checks each item; each parses every record once.
    check("a_list_on_the_disk_view_parses_each_record_once_for_each_walk", walked == 2 * len(names))
    check("a_list_that_copies_the_library_before_checking_it_is_detected", copied > 2 * len(names))


#: What the loopback HTTP group needs, as core.service_runtime.http_checks does; without them it is not run.
HTTP_MODULES = ("httpx", "starlette", "uvicorn", "mcp")


def _http_checks(check, root):
    """catalogue_serving_checks' loopback HTTP checks again, with the fixture's host on the disk engine: search,
    filters, downloads by path with digests and one charge, a release swapped in while the service runs, and a
    request finishing on the view it started with, over a real socket."""
    from . import catalogue_serving_checks
    from .catalogue_release_checks import Fixture
    from .catalogue_serving import CatalogueSourceSettings
    original = Fixture.__init__

    def on_the_disk_engine(self, folder):
        original(self, folder)
        index_root = Path(folder) / "index"
        index_root.mkdir(exist_ok=True)
        self.settings = CatalogueSourceSettings("store", str(self.root / "bodies"),
                                                record_type="service_catalogue_source/v2",
                                                search_engine="sqlite_disk_index", index_root=str(index_root))
    engines = []

    def named(name, passed):
        check(f"{name}_on_the_disk_engine", passed)
    with patch.object(Fixture, "__init__", on_the_disk_engine):
        original_view = Fixture.view

        def view(self):
            served = original_view(self)
            engines.append(type(served).__name__)
            return served
        with patch.object(Fixture, "view", view):
            catalogue_serving_checks._serving_checks(named, root)
    check("the_http_checks_ran_on_disk_views", bool(engines) and set(engines) == {"DiskCatalogueView"})


def _build_coordination_checks(check, root):
    """One build at a time under an index root, a lost index built again, and old indexes removed."""
    from contextlib import nullcontext
    import shutil
    import time
    from . import catalogue_disk_view
    from .catalogue_disk_view import INDEXES_FOLDER, RELEASES_FOLDER, build_lock, ensure_release_index, prune_indexes
    from .catalogue_segment_checks import SegmentFixture
    from .catalogue_serving import CatalogueSourceSettings
    case = SegmentFixture(root)
    base = case.base
    index_root = Path(root) / "index"
    index_root.mkdir()
    settings = CatalogueSourceSettings("store", str(Path(root) / "bodies"), record_type="service_catalogue_source/v2",
                                       search_engine="sqlite_disk_index", index_root=str(index_root))
    now = [time.time()]

    def ensure(wait=True):
        return ensure_release_index(base.config, settings, license_policy=base.license_policy,
                                    family_policy=base.family_policy, wait=wait, clock=lambda: now[0])

    def folders():
        return sorted(path.name for path in (index_root / INDEXES_FOLDER).iterdir() if not path.name.startswith("."))

    def descriptors():
        return sorted(path.stem for path in (index_root / RELEASES_FOLDER).glob("*.json"))
    names = [f"skill_{index:03d}" for index in range(20)]
    case.publish(case.lines(names))
    with build_lock(index_root):
        waiting = refused(lambda: ensure(wait=False), "search_index_building")
        with patch.object(catalogue_disk_view, "build_lock", lambda root, wait=True: nullcontext()):
            unguarded = not refused(lambda: ensure(wait=False))
    check("a_refresher_never_builds_an_index_another_process_is_building", waiting)
    check("removed_build_lock_is_detected", unguarded)
    releases = []
    for number in range(4):
        now[0] += 2 * catalogue_disk_view.SERVING_GRACE_SECONDS
        if number:
            case.publish(case.lines(names, text=lambda name, number=number: f"Skill {name}, edition {number}."))
        header, descriptor, _state = ensure()
        releases.append((header.release_id, descriptor["base"]))
    check("indexes_of_releases_no_longer_kept_are_removed",
          folders() == sorted(name for _release, name in releases[-2:])
          and descriptors() == sorted(release for release, _name in releases[-2:]))
    shutil.rmtree(index_root / INDEXES_FOLDER / releases[-1][1])
    now[0] += 30
    _header, rebuilt, _state = ensure()
    check("a_release_whose_index_folder_was_lost_is_built_again",
          rebuilt["base"] != releases[-1][1] and (index_root / INDEXES_FOLDER / rebuilt["base"] / "BUILT.json").is_file())
    # A release built a minute after the last one: the service may still serve the release before that, so its
    # index stays until the grace period has passed.
    now[0] += 60
    case.publish(case.lines(names, text=lambda name: f"Skill {name}, edition five."))
    newest, _descriptor, _state = ensure()
    check("the_release_the_service_may_still_serve_keeps_its_index_for_the_grace_period",
          len(folders()) == 3 and releases[-2][1] in folders() and rebuilt["base"] in folders())
    later = lambda: now[0] + 10 ** 6  # noqa: E731 - a clock long past every grace period
    kept = prune_indexes(index_root, active_release=releases[-1][0], keep=1, clock=later)
    check("the_active_release_index_is_never_removed",
          rebuilt["base"] in folders() and rebuilt["base"] not in kept["removed_indexes"]
          and releases[-2][1] in kept["removed_indexes"])
    gone = prune_indexes(index_root, active_release=newest.release_id, keep=1, clock=later)
    check("without_the_active_release_rule_its_index_is_removed", rebuilt["base"] in gone["removed_indexes"])


def _selection_checks(check):
    from . import catalogue_index_engines
    from .catalogue_index_engines import DISK_ENGINE, IN_MEMORY_ENGINE, OBJECT_STORE_ENGINE, describe, select_engine
    from .catalogue_serving import CatalogueSourceSettings
    check("the_baseline_engine_is_always_selectable", select_engine(IN_MEMORY_ENGINE).engine_id == IN_MEMORY_ENGINE)
    check("the_slot_describes_its_engines_in_declared_order",
          [row["engine_id"] for row in describe()] == [IN_MEMORY_ENGINE, DISK_ENGINE, OBJECT_STORE_ENGINE])
    unavailable = catalogue_index_engines.CatalogueIndexEngine(
        DISK_ENGINE, "1.0.0", "disk_index", "disk", True, availability=lambda: {"available": False,
                                                                                "reason": "numpy_not_installed"})
    with patch.dict(catalogue_index_engines.ENGINES, {DISK_ENGINE: unavailable}):
        check("an_engine_that_cannot_run_here_is_refused_at_start_and_never_replaced",
              refused(lambda: select_engine(DISK_ENGINE), "search_engine_unavailable"))
    check("an_unknown_or_planned_engine_is_refused",
          refused(lambda: select_engine("faster_engine"), "search_engine_unavailable")
          and refused(lambda: select_engine(OBJECT_STORE_ENGINE), "search_engine_unavailable"))
    check("a_version_1_catalogue_section_names_no_engine",
          refused(lambda: CatalogueSourceSettings("store", "/data/bodies", search_engine=DISK_ENGINE,
                                                  index_root="/data/index"), "unsupported_catalogue_source"))
    check("the_disk_engine_needs_the_store_source_and_an_index_root",
          refused(lambda: CatalogueSourceSettings("store", "/data/bodies", record_type="service_catalogue_source/v2",
                                                  search_engine=DISK_ENGINE), "unsupported_catalogue_source"))


def _command_checks(check, root):
    """The formats, publish and index commands through the service entry point, and a host start on the disk view."""
    import io
    from contextlib import redirect_stdout
    from .catalogue_disk_view import DiskCatalogueView
    from .catalogue_release_checks import bundle_line
    from .catalogue_segment_checks import SegmentFixture
    from .http_entrypoint import load_host_application, main
    case = SegmentFixture(root)
    base = case.base
    image = Path(root) / "image"
    (image / "bodies").mkdir(parents=True)
    (image / "bodies" / "packaged.md").write_bytes(b"# Packaged item\n")
    reference = bundle_line("packaged_item", [("SKILL.md", b"# Packaged item\n", "text/markdown",
                                                "skill_definition")])["reference"]
    (image / "manifest.json").write_text(json.dumps({
        "record_type": "host_attested_intelligence_manifest/v1", "artifact_root": str(image),
        "items": [{"reference": reference, "body_path": "bodies/packaged.md", "approval_ref": "review:packaged",
                   "grants": []}]}))
    (Path(root) / "index").mkdir()
    section = {"record_type": "service_catalogue_source/v2", "source": "store",
               "body_store_root": str(Path(root) / "bodies"), "refresh_seconds": 5,
               "search_engine": "sqlite_disk_index", "index_root": str(Path(root) / "index")}
    configuration = {"record_type": "service_http_host_configuration/v1",
                     "runtime": {"database_path": base.config.database_path, "writes_authorized": True},
                     "http": {"public_base_url": "http://127.0.0.1:8080", "allowed_hosts": ["127.0.0.1:8080"],
                              "allow_loopback_http": True},
                     "authentication": {}, "manifest_path": str(image / "manifest.json"), "catalogue": section}
    host = Path(root) / "host.json"
    host.write_text(json.dumps(configuration))

    def command(*arguments, config=host):
        printed = io.StringIO()
        try:
            with redirect_stdout(printed):
                status_code = main([*arguments, "--config", str(config)])
            return status_code, json.loads(printed.getvalue())
        except Exception as error:  # noqa: BLE001 - a refusal is an answer here
            return None, getattr(error, "code", str(error))
    formats = command("catalogue-formats")
    check("catalogue_formats_answers_through_the_service_entry_point",
          formats[0] == 0 and "catalogue_release_bundle/v2" in formats[1]["bundle_record_types"])
    folder = case.write(case.lines([f"skill_{index:03d}" for index in range(30)]))
    from .catalogue_packages import sha256_hex
    digest = sha256_hex((folder / "bundle.json").read_bytes())
    published = command("publish-catalogue", "--bundle", str(folder), "--expected-bundle-digest", digest)
    first = command("index-catalogue")
    again = command("index-catalogue")
    check("publish_catalogue_reads_a_version_2_bundle_and_index_catalogue_builds_once",
          published[0] == 0 and published[1]["release_record_type"] == "catalogue_release/v2"
          and first[0] == 0 and first[1]["release_id"] == published[1]["release_id"]
          and again[1]["base"] == first[1]["base"])
    application, _configuration = load_host_application(str(host))
    view = application.provisioning.current_view()
    check("a_host_that_selects_the_disk_engine_starts_on_the_disk_view",
          isinstance(view, DiskCatalogueView) and view.release_id == published[1]["release_id"]
          and len(view.catalogue.items) == 30)
    from . import library_page
    from .catalogue_serving import catalogue_settings, refresher_for
    from .http_entrypoint import host_family_policy, host_license_policy
    case.publish(case.lines([f"skill_{index:03d}" for index in range(31)]))
    refresher = refresher_for(application, catalogue_settings(configuration),
                              license_policy=host_license_policy(configuration),
                              family_policy=host_family_policy(configuration))
    swapped = refresher.check_once()
    current = application.provisioning.current_view()
    check("a_swap_renders_the_library_page_of_the_new_view_before_installing_it",
          swapped.get("changed") is True and len(current.catalogue.items) == 31
          and (library_page._view_key(current), application.configuration.display_name) in library_page._PAGES)
    case.publish(case.lines([f"skill_{index:03d}" for index in range(32)]))
    with patch.object(application, "warm_catalogue_pages", None):
        refresher.check_once()
    later = application.provisioning.current_view()
    check("removed_page_warming_is_detected",
          len(later.catalogue.items) == 32
          and (library_page._view_key(later), application.configuration.display_name) not in library_page._PAGES)
    plain = Path(root) / "host-v1.json"
    plain.write_text(json.dumps({**configuration, "catalogue": {
        "record_type": "service_catalogue_source/v1", "source": "store",
        "body_store_root": str(Path(root) / "bodies"), "refresh_seconds": 5}}))
    check("index_catalogue_is_refused_for_a_host_that_keeps_the_in_memory_engine",
          command("index-catalogue", config=plain) == (None, "invalid_request"))


def _lance_checks(check, root):
    """The engine (c) prototype on the same edge: filters exact against the baseline, the edge's shape kept."""
    from .catalogue_index_engines import CatalogueSearchIndexEngine, index_size
    from .catalogue_lance_index import LanceSearchIndex, build_lance_index
    from .catalogue_search import ReleaseSearchIndex
    schema, entries = _schema(), _entries(600)
    baseline = ReleaseSearchIndex(entries, schema)
    lance = LanceSearchIndex(build_lance_index(Path(root) / "lance", entries, schema), schema)
    check("the_lance_prototype_speaks_the_catalogue_search_index_edge",
          isinstance(lance, CatalogueSearchIndexEngine) and index_size(lance) == len(entries))
    exact = True
    for conditions in FILTERS[1:]:
        wanted = {baseline.identities[position] for position in baseline.eligible(conditions)}
        rows = lance.table.search().where(lance.eligible(conditions)).select(["identity"]).limit(len(entries))
        exact = exact and wanted == {row["identity"] for row in rows.to_list()}
    check("the_lance_prototype_filters_select_exactly_the_baseline_items", exact)
    found = lance.rank("skill_00042", mode="lexical", pool=3)[0]["lexical"]
    check("the_lance_prototype_finds_an_item_by_its_identity", bool(found) and found[0][0] == "skill_00042")


def _integrity_checks(check, root):
    from .catalogue_disk_index import DiskIndex, build_disk_index
    schema = _schema()
    folder = build_disk_index(Path(root) / "integrity", _entries(50), schema)
    vectors = folder / "vectors.f32"
    data = bytearray(vectors.read_bytes())
    data[-1] ^= 0xFF
    vectors.chmod(0o644)
    vectors.write_bytes(bytes(data))
    check("a_disk_index_file_changed_after_its_build_is_refused_when_verified",
          refused(lambda: DiskIndex(folder, verify_files=True), "search_index_unavailable"))
    (folder / "BUILT.json").unlink()
    check("an_unfinished_disk_index_is_never_read", refused(lambda: DiskIndex(folder), "search_index_unavailable"))


def run_checks(check=None):
    tests = []
    if check is None:
        def check(name, passed):
            tests.append({"test": name, "passed": bool(passed),
                          "detail": "real temporary stores, body folders and index folders; no provider"})
    from .catalogue_disk_index import availability
    if not availability()["available"]:
        return {"record_type": "catalogue_index_checks/v1", "tests": [], "passed": 0, "total": 0,
                "all_passed": True, "not_tested": availability()["reason"]}
    _selection_checks(check)
    from .catalogue_lance_index import availability as lance_availability
    groups = [_edge_and_exactness_checks, _overlay_checks, _service_path_checks, _request_path_checks,
              _build_coordination_checks, _command_checks, _integrity_checks]
    import importlib.util
    if all(importlib.util.find_spec(name) is not None for name in HTTP_MODULES):
        groups.append(_http_checks)
    if lance_availability()["available"]:
        groups.append(_lance_checks)
    for group in groups:
        with tempfile.TemporaryDirectory(prefix="catalogue-index-checks-") as directory:
            try:
                group(check, directory)
            except Exception:  # noqa: BLE001 - a group that stops part way is a failure with a name
                check(f"the_{group.__name__.strip('_')}_ran_to_completion", False)
    return {"record_type": "catalogue_index_checks/v1", "tests": tests,
            "passed": sum(row["passed"] for row in tests), "total": len(tests),
            "all_passed": all(row["passed"] for row in tests)}


def self_test():
    return run_checks()
