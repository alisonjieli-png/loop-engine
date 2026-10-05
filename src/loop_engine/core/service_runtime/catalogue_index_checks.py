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
    groups = [_edge_and_exactness_checks, _overlay_checks, _service_path_checks, _integrity_checks]
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
