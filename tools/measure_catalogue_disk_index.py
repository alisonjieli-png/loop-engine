"""Measure the disk index engine (`sqlite_disk_index`) of the catalogue search index slot at a synthetic size.

Kind: local measurement tool. Nothing here contacts a network or provider, and
the numbers describe this machine only: a local measurement, not a production
claim.

The items are synthetic and carry no bodies. Each is an item version record of
the shape the service stores, with the purpose words drawn exactly as
`measure_catalogue_release_scale.py` draws them (from the starter catalogue's
purposes, 20 to 40 words), the same attributes (`cited_source` from 40 values,
`origin_layer`, `catalogued_on`, an internal `batch`), four in five single-file
skills and one in five packages of three or four files. File digests are
derived from the identity and path, not from bytes, so no body exists to read;
search, authorization and descriptors never read a body.

```text
Phases, each its own process so each one's memory is its own
├── build   generate the items as a stream and write one disk index; records seconds, peak memory, file sizes
├── serve   open the index, serve a disk view through the service's own authorization path, and time 40
│           queries in each mode: lexical, hybrid, lexical with a filter, hybrid with a filter
└── delta   publish-time work for a daily release of 100 new and 10 changed items on top of the index: build
            the delta index and the overlay, then time the same queries over the overlay
```

    PYTHONPATH=src python tools/measure_catalogue_disk_index.py --items 1000000 \
        --root "$HOME/.le-ci-tmp/scale-runs/disk-1m" --phase build

`--engine lance_object_store_index` builds and serves the engine (c) prototype (catalogue_lance_index) from the
same items instead; it has no item-descriptor view, so its serve phase times the index edge alone (rank and fusion,
no provisioning authorization), and the disk engine's serve phase reports the same index-only timings beside its
full-path ones for comparison.

`serve` and `delta` read the index the `build` phase left in the root. Memory is reported as the process's peak
resident set, its anonymous (heap) part and its file-backed part: the index files are memory-mapped or read
through SQLite's bounded page cache, so file-backed pages are the operating system's cache, which it reclaims
under pressure, not memory the process holds.
"""
from __future__ import annotations

import argparse
from collections import namedtuple
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import statistics
import sys
import time

REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY / "src"))
STARTER = REPOSITORY / "examples/29_intelligence_service/starter-catalogue"
RESULT_RECORD_TYPE = "catalogue_disk_index_measurement/v1"
QUERIES = 40
DELTA_NEW, DELTA_CHANGED = 100, 10
_Item = namedtuple("_Item", "identity kind source_layer purpose")


def _status():
    values = {}
    for line in Path("/proc/self/status").read_text().splitlines():
        key, _, rest = line.partition(":")
        if key in ("VmHWM", "VmRSS", "RssAnon", "RssFile", "RssShmem"):
            values[key] = int(rest.split()[0])
    return values


def _words():
    manifest = json.loads((STARTER / "host-release" / "manifest.json").read_text("utf-8"))
    return " ".join(row["reference"]["purpose"] for row in manifest["items"]).split()


def _schema():
    from loop_engine.core.service_runtime.catalogue_schema import CatalogueAttributeSchema
    return CatalogueAttributeSchema.from_dict(json.loads((STARTER / "attribute-schema.json").read_text()))


def _template_reference():
    from loop_engine.core.harness_intelligence import HarnessIntelligenceDraft, item_from_body
    draft = HarnessIntelligenceDraft("synthetic_template", "skill", "template purpose", "harness_local",
                                     "synthetic:template", "MIT", ())
    return item_from_body(draft, "x").reference()


def _items(start, stop, seed, schema, version=1):
    """Yield `(IndexEntry, item version, record text)` for synthetic items `start` to `stop - 1`.

    One random stream is seeded from `seed`, `start` and `version`, so a run is repeatable and a later version of
    an item gets other words. Words are drawn with replacement from the starter purposes, as the release scale
    tool draws them.
    """
    from loop_engine.core.service_runtime.catalogue_packages import CataloguePackage, CataloguePackageFile
    from loop_engine.core.service_runtime.catalogue_search import IndexEntry, entry_text
    words, template = _words(), _template_reference()
    sources = [f"src/loop_engine/synthetic/module_{index:02d}.py" for index in range(40)]
    rng = random.Random(seed * 1_000_003 + start * 7 + version)
    for index in range(start, stop):
        identity = f"synthetic_skill_{index:08d}"
        purpose = " ".join(rng.choices(words, k=rng.randint(20, 40)))
        size = max(600, int(rng.gauss(2800, 700)))
        shape = rng.random()
        paths = [("SKILL.md", size, "text/markdown", "skill_definition")]
        if shape < 0.20:
            paths = [("SKILL.md", int(size * 0.72), "text/markdown", "skill_definition"),
                     ("references/notes.md", size - int(size * 0.72), "text/markdown", "skill_reference"),
                     ("assets/example.json", 48, "application/json", "skill_asset")]
            if shape < 0.05:
                paths.append(("scripts/run.py", 40, "text/x-python", "skill_script"))
        files = tuple(CataloguePackageFile(path, hashlib.sha256(f"{identity}/{path}/{version}".encode()).hexdigest(),
                                           length, media, role) for path, length, media, role in paths)
        package = CataloguePackage(files, "file" if len(files) == 1 else "package")
        values = {"cited_source": rng.choice(sources),
                  "origin_layer": rng.choice(["context_intelligence", "code_intelligence"]),
                  "catalogued_on": f"2026-09-{rng.randint(1, 22):02d}", "batch": "synthetic"}
        reference = {**template, "identity": identity, "purpose": purpose, "digest": package.served_digest,
                     "size_bytes": package.served_size, "source_ref": f"synthetic:{identity}",
                     "declared_effects": ["spawns_process"] if shape < 0.05 else []}
        record = {"record_type": "catalogue_item_version/v1", "reference": reference, "package": package.to_dict(),
                  "approval_ref": f"synthetic-review:{identity}", "attributes": values}
        text = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        item = _Item(identity, "skill", "harness_local", purpose)
        entry = IndexEntry(identity, entry_text(item, schema.search_text(values)), values, "verified",
                           shape < 0.05)
        yield entry, hashlib.sha256(text.encode()).hexdigest(), text


GENERATION_CHUNK = 20_000


def _chunk(arguments):
    start, stop, seed = arguments
    return list(_items(start, stop, seed, _schema()))


def _generated(count, seed, workers):
    """Every synthetic item in order, generated in chunks by `workers` processes, at most two chunks ahead each."""
    chunks = [(start, min(count, start + GENERATION_CHUNK), seed) for start in range(0, count, GENERATION_CHUNK)]
    if workers <= 1:
        for chunk in chunks:
            yield from _chunk(chunk)
        return
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(max_workers=workers) as pool:
        pending = []
        for chunk in chunks:
            pending.append(pool.submit(_chunk, chunk))
            if len(pending) > 2 * workers:
                yield from pending.pop(0).result()
        for future in pending:
            yield from future.result()


def _size_of(folder):
    return {path.name: path.stat().st_size for path in sorted(Path(folder).iterdir()) if path.is_file()}


def _tree_size(folder):
    return {"total": sum(path.stat().st_size for path in Path(folder).rglob("*") if path.is_file())}


def build(count, root, seed, workers=1, engine="sqlite_disk_index"):
    schema = _schema()
    started = time.perf_counter()
    if engine == "lance_object_store_index":
        from loop_engine.core.service_runtime.catalogue_lance_index import build_lance_index
        folder = build_lance_index(root / "index-lance", (row[0] for row in _generated(count, seed, workers)), schema,
                                   release_id="synthetic")
        seconds = time.perf_counter() - started
        files = _tree_size(folder)
    else:
        from loop_engine.core.service_runtime.catalogue_disk_index import build_disk_index
        folder = build_disk_index(root / "index-base", _generated(count, seed, workers), schema, count=count,
                                  release_id="synthetic", note="synthetic measurement", workers=workers)
        seconds = time.perf_counter() - started
        files = _size_of(folder)
    return {"items": count, "engine": engine, "workers": workers, "build_seconds": round(seconds, 1),
            "items_per_second": round(count / seconds),
            "note": "the seconds include generating the synthetic items in the same pipeline",
            "process_memory_kib": _status(), "files_bytes": files, "index_bytes": sum(files.values()),
            "index_bytes_per_item": round(sum(files.values()) / max(1, count), 1)}


def _latencies(action, rounds):
    values = []
    for query in rounds:
        started = time.perf_counter()
        action(query)
        values.append((time.perf_counter() - started) * 1000)
    values.sort()
    return {"p50_ms": round(statistics.median(values), 1),
            "p95_ms": round(values[max(0, int(len(values) * 0.95) - 1)], 1),
            "max_ms": round(values[-1], 1), "samples": len(values)}


def _disk_view(root, base, delta=None, removed=()):
    from loop_engine.core.harness_intelligence import HarnessIntelligenceCatalogue
    from loop_engine.core.service_runtime.catalogue_disk_index import DiskSearchIndex
    from loop_engine.core.service_runtime.catalogue_disk_view import DiskCatalogueView, DiskItemSource, _view_over
    from loop_engine.core.service_runtime.catalogue_serving import STORE_SOURCE, _approved_resolver
    schema = _schema()
    removed_rows = base.records(list(removed))
    source = DiskItemSource(base, delta, frozenset(removed_rows), schema=schema)
    index = DiskSearchIndex(base, schema, removed=frozenset(row[0] for row in removed_rows.values()), delta=delta)
    template = DiskCatalogueView(HarnessIntelligenceCatalogue(), _approved_resolver("measure", {}), None,
                                 source=STORE_SOURCE, release_id="synthetic", schema=schema, index=index)
    return _view_over(source, template)


def _account(root):
    from loop_engine.core.service_runtime.catalogue_grants import follow_active_release
    from loop_engine.core.service_runtime.records import ServiceRuntimeConfig, TenantKeyIssue, TenantRegistration
    from loop_engine.core.service_runtime.runtime import ServiceRuntime
    config = ServiceRuntimeConfig(str(root / "service.db"), writes_authorized=True)
    runtime = ServiceRuntime(config)
    if not (root / "key.txt").exists():
        runtime.register_tenant(TenantRegistration("measure", "tenant:measure"))
        key = runtime.issue_key(TenantKeyIssue("measure", "local measurement"))
        follow_active_release(runtime, ["measure"])
        (root / "key.txt").write_text(key.key)
    return runtime, (root / "key.txt").read_text()


def _search_runs(view, runtime, key, seed):
    from loop_engine.core.service_runtime.catalogue_search import authorized_hits
    from loop_engine.core.service_runtime.provisioning import DurableProvisioningBinding
    binding = DurableProvisioningBinding(runtime, view.catalogue, view.qualification_resolver, view.body_reader,
                                         view=view)
    principal = runtime.authenticate_key(key)
    rng, words = random.Random(seed + 1), _words()
    queries = [" ".join(rng.choice(words) for _ in range(rng.randint(2, 5))) for _ in range(QUERIES)]

    def search(mode, filters=None):
        def run(query):
            def authorize(candidates):
                listing = binding.invoke_for_principal(principal, "list", view=view, candidates=candidates)
                return {row["identity"]: row for row in listing["items"]}
            fields = {"query": query, "mode": mode, "top_n": 10}
            if filters:
                fields["filters"] = filters
            hits, _rows = authorized_hits(view, fields, authorize)
            if not hits:
                raise RuntimeError(f"no hit for {query!r}")
        return run
    started = time.perf_counter()
    search("hybrid")(queries[0])
    first = round((time.perf_counter() - started) * 1000, 1)
    code_only = {"origin_layer": {"equals": "code_intelligence"}}
    one_source = {"cited_source": {"equals": "src/loop_engine/synthetic/module_07.py"}}
    return {"first_query_ms": first,
            "search_lexical": _latencies(search("lexical"), queries),
            "search_hybrid": _latencies(search("hybrid"), queries),
            "search_lexical_with_filter": _latencies(search("lexical", code_only), queries),
            "search_hybrid_with_filter": _latencies(search("hybrid", code_only), queries),
            "search_hybrid_with_selective_filter": _latencies(search("hybrid", one_source), queries)}


def _index_runs(index, seed):
    """The index edge alone: rank and fusion with every candidate allowed, no provisioning authorization."""
    from loop_engine.core.service_runtime.catalogue_search import fuse
    schema = _schema()
    rng, words = random.Random(seed + 1), _words()
    queries = [" ".join(rng.choice(words) for _ in range(rng.randint(2, 5))) for _ in range(QUERIES)]

    def search(mode, filters=None):
        conditions = schema.filter_request(filters) if filters else ()

        def run(query):
            eligible = index.eligible(conditions) if conditions else None
            pool = 10 * index.policy.candidate_pool_multiplier
            pools, _exhausted = index.rank(query, mode=mode, pool=pool, eligible=eligible)
            allowed = {identity: {} for rows in pools.values() for identity, _score in rows}
            return fuse(pools, allowed, index.policy, 10)
        return run
    code_only = {"origin_layer": {"equals": "code_intelligence"}}
    return {"index_lexical": _latencies(search("lexical"), queries),
            "index_hybrid": _latencies(search("hybrid"), queries),
            "index_hybrid_with_filter": _latencies(search("hybrid", code_only), queries)}


def serve_lance(root, seed):
    from loop_engine.core.service_runtime.catalogue_lance_index import LanceSearchIndex
    before = _status()
    started = time.perf_counter()
    index = LanceSearchIndex(root / "index-lance", _schema())
    opened = round(time.perf_counter() - started, 3)
    after_open = _status()
    started = time.perf_counter()
    search_one = _index_runs(index, seed)
    return {"engine": "lance_object_store_index", "open_seconds": opened, "process_memory_kib_before_open": before,
            "process_memory_kib_after_open": after_open, **search_one,
            "process_memory_kib_after_searches": _status(), "index_stats": index.stats(),
            "note": "index edge only: no item-descriptor view exists for this prototype"}


def serve(root, seed):
    from loop_engine.core.service_runtime.catalogue_disk_index import DiskIndex
    if (root / "index-lance").exists() and not (root / "index-base").exists():
        return serve_lance(root, seed)
    before = _status()
    runtime, key = _account(root)
    started = time.perf_counter()
    base = DiskIndex(root / "index-base")
    view = _disk_view(root, base)
    opened = round(time.perf_counter() - started, 3)
    after_open = _status()
    started = time.perf_counter()
    summary = view.summary()
    summary_seconds = round(time.perf_counter() - started, 3)
    runs = _search_runs(view, runtime, key, seed)
    runs.update(_index_runs(view.search_index(), seed))
    return {"open_seconds": opened, "summary_seconds": summary_seconds, "summary": summary,
            "process_memory_kib_before_open": before, "process_memory_kib_after_open": after_open,
            **runs, "process_memory_kib_after_searches": _status(),
            "index_stats": view.search_index().stats()}


def delta(root, count, seed):
    """The index-side work of a daily release on top of the base: 100 new and 10 changed items."""
    from loop_engine.core.service_runtime.catalogue_disk_index import DiskIndex, build_disk_index
    schema = _schema()
    base = DiskIndex(root / "index-base")
    changed = list(range(0, count, max(1, count // DELTA_CHANGED)))[:DELTA_CHANGED]
    rows = [next(_items(index, index + 1, seed, schema, version=2)) for index in changed]
    started = time.perf_counter()
    rows += list(_items(count, count + DELTA_NEW, seed, schema))
    rows.sort(key=lambda row: row[0].identity)
    generated = time.perf_counter() - started
    folder = root / f"index-delta-{int(time.time())}"
    started = time.perf_counter()
    build_disk_index(folder, rows, schema, count=len(rows), release_id="synthetic-2", note="synthetic delta")
    removed = [f"synthetic_skill_{index:08d}" for index in changed]
    built = time.perf_counter() - started
    started = time.perf_counter()
    view = _disk_view(root, base, DiskIndex(folder), removed)
    opened = time.perf_counter() - started
    runtime, key = _account(root)
    return {"delta_items": len(rows), "removed_from_base": len(removed), "delta_generate_seconds": round(generated, 2),
            "delta_build_seconds": round(built, 2),
            "overlay_open_seconds": round(opened, 3), "summary": view.summary(),
            **_search_runs(view, runtime, key, seed), "process_memory_kib": _status()}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--items", type=int, required=True)
    parser.add_argument("--root", type=Path, required=True, help="A scratch folder outside the repository.")
    parser.add_argument("--seed", type=int, default=20261005)
    parser.add_argument("--phase", choices=("build", "serve", "delta"), required=True)
    parser.add_argument("--label", default="", help="Recorded with the result, e.g. the memory cap of the run.")
    parser.add_argument("--workers", type=int, default=1, help="build: processes for generation and vectors.")
    parser.add_argument("--engine", default="sqlite_disk_index",
                        choices=("sqlite_disk_index", "lance_object_store_index"), help="build: the engine to build.")
    options = parser.parse_args(argv)
    root = options.root.resolve()
    if REPOSITORY in root.parents or root == REPOSITORY:
        parser.error("the root is a scratch folder outside the repository")
    root.mkdir(parents=True, exist_ok=True)
    phases = {"build": lambda: build(options.items, root, options.seed, options.workers, options.engine),
              "serve": lambda: serve(root, options.seed),
              "delta": lambda: delta(root, options.items, options.seed)}
    result = phases[options.phase]()
    print(json.dumps({"record_type": RESULT_RECORD_TYPE, "phase": options.phase, "items": options.items,
                      "label": options.label or "local measurement on one workstation, not a production claim",
                      "measured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                      "load_average_at_end": [round(value, 1) for value in os.getloadavg()],
                      "machine": {"processors": os.cpu_count(), "python": platform.python_version(),
                                  "platform": platform.platform(), "sqlite": __import__("sqlite3").sqlite_version},
                      "result": result}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
