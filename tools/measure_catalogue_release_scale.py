"""Measure catalogue releases at a synthetic library size on this workstation.

Kind: local measurement tool. It generates a synthetic release of N items with
bodies of the starter catalogue's average size (about 2.8 kilobytes), four in
five single-file skills and one in five multi-file packages, writes a bundle,
publishes it into a temporary service store and body folder with the service's
own code, and then, in a separate serving process, builds the served view,
measures search and a hot swap to a second release. Nothing here contacts a
network or provider, and the numbers describe this machine only: they are a
local measurement, not a production claim.

    PYTHONPATH=src python tools/measure_catalogue_release_scale.py --items 10000 --root /some/scratch/folder

Three processes are used so that the serving process's memory is not the
generator's: `prepare` generates and publishes the first release and writes an
incremental second bundle, `serve` builds the view and measures, and `serve`
starts `publish-second` as its own child when it measures the swap.

Since October 5, 2026 the serving process also records where its memory goes
(`component_memory`): the Python objects reachable from each part of the view
(catalogue, packages, attributes, bindings, approvals, item versions, the
index's identities and filter tables), the vector columns, the in-memory
full-text database, and what the resident set holds beyond them. Shared
objects are counted once, to the first part walked, in the order listed.

`--segmented` publishes the same library as version 2 releases
(catalogue_segments.py): the first bundle carries every segment, item line
and body; the second carries what the publish tool would upload, only the
segments, item lines and bodies the first release lacks, so its size is the
upload a daily release costs. `--engine sqlite_disk_index` serves the store
through the disk index engine and its disk view instead of the in-memory
engine; the swap to the second release is then an overlay when the base is
large enough.

The bundle reader refuses more than `MAXIMUM_BUNDLE_ITEMS` (200,000) items.
`--lift-bundle-limit` raises that bound inside the measurement's own
processes only, so today's serving code can be measured above it; the record
says so, and the service itself is unchanged.

With the disk engine, an `index` process builds the release's disk index
first, as `loop-engine service index-catalogue` does on a host, and reports its
time and memory; the serving process then opens that index. The serving
process also times what a customer's other requests cost (added October 5,
2026, after a manifest on a disk view was found to take 47 s): a manifest for
the release-following account at identities spread over the library, a
discover, the unpaged list and the library page's rows, each with the
process's memory afterwards.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import random
import statistics
import subprocess
import sys
import time

REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY / "src"))
STARTER = REPOSITORY / "examples/29_intelligence_service/starter-catalogue"
RESULT_RECORD_TYPE = "catalogue_release_scale_measurement/v1"
QUERIES = 40
PHASES = ("all", "prepare", "index", "serve", "publish-second")
ALL_PHASES, PREPARE_PHASE, INDEX_PHASE, SERVE_PHASE, PUBLISH_SECOND_PHASE = PHASES
#: Identities a manifest is timed for, spread over the library.
MANIFEST_SAMPLES = 20
SECOND_RELEASE_NEW, SECOND_RELEASE_CHANGED = 100, 10


def _words():
    manifest = json.loads((STARTER / "host-release" / "manifest.json").read_text("utf-8"))
    return " ".join(row["reference"]["purpose"] for row in manifest["items"]).split()


def _peak_rss_kib():
    for line in Path("/proc/self/status").read_text().splitlines():
        if line.startswith("VmHWM:"):
            return int(line.split()[1])
    return None


def _status_kib():
    values = {}
    for line in Path("/proc/self/status").read_text().splitlines():
        key, _, rest = line.partition(":")
        if key in ("VmHWM", "VmRSS", "RssAnon", "RssFile"):
            values[key] = int(rest.split()[0])
    return values


def _rss_kib():
    for line in Path("/proc/self/status").read_text().splitlines():
        if line.startswith("VmRSS:"):
            return int(line.split()[1])
    return None


def _lift_bundle_limit(items):
    """Raise the bundle reader's item bound inside this measurement process only, when asked."""
    from loop_engine.core.service_runtime import catalogue_bundle
    held = catalogue_bundle.MAXIMUM_BUNDLE_ITEMS
    catalogue_bundle.MAXIMUM_BUNDLE_ITEMS = max(held, items + SECOND_RELEASE_NEW)
    return held


def _deep_bytes(roots, seen):
    """Bytes of the Python objects reachable from `roots` that `seen` does not hold yet; adds them to `seen`.

    Types, modules, functions and code are not followed, so a walk stays inside the data it was given. A
    closure's cells are followed only when a caller passes them as roots.
    """
    import gc
    import types
    skip = (type, types.ModuleType, types.FunctionType, types.BuiltinFunctionType, types.MethodType,
            types.CodeType)
    total, stack = 0, list(roots)
    while stack:
        value = stack.pop()
        if id(value) in seen or isinstance(value, skip):
            continue
        seen.add(id(value))
        total += sys.getsizeof(value)
        stack.extend(gc.get_referents(value))
    return total


def _component_memory(view):
    """Where one served view's memory goes, part by part, with what the resident set holds beyond the parts."""
    index = view.search_index()
    resolve = view.qualification_resolver.resolve
    approvals = [cell.cell_contents for cell in (resolve.__closure__ or ()) if isinstance(cell.cell_contents, dict)]
    seen = set()
    vectors = sum(sys.getsizeof(column) for column in index._columns)
    seen.update(id(column) for column in index._columns)
    seen.add(id(index._columns))
    pages = index._connection.execute("PRAGMA page_count").fetchone()[0]
    page_size = index._connection.execute("PRAGMA page_size").fetchone()[0]
    parts = {"catalogue": [view.catalogue.items], "bindings": [view.bindings], "packages": [view.packages],
             "attributes": [view.attributes], "approvals": approvals, "item_versions": [view.item_versions],
             "index_identities": [index.identities], "index_filter_tables": [index._sets, index._ranges],
             "changes_and_notes": [view.changes, view.withdrawal_notes]}
    measured = {name: _deep_bytes(roots, seen) for name, roots in parts.items()}
    measured["vector_columns"] = vectors
    measured["full_text_database"] = pages * page_size
    rss = _rss_kib() * 1024
    return {"record_type": "catalogue_view_component_memory/v1", "items": len(view.catalogue.items),
            "bytes": measured, "bytes_per_item": {name: round(value / max(1, len(view.catalogue.items)), 1)
                                                  for name, value in measured.items()},
            "parts_total_bytes": sum(measured.values()), "process_rss_bytes": rss,
            "rss_beyond_parts_bytes": rss - sum(measured.values()),
            "note": "Python objects reachable from each part, shared objects counted once to the first part in this "
                    "order; vector columns are the 512 float32 arrays; the full-text database is SQLite's page "
                    "count times page size; the rest of the resident set is the interpreter, imported code, "
                    "allocator slack and memory freed by the build but not returned to the system"}


def _item(index, rng, words, sources, version=1, identity=None):
    """One synthetic bundle line and its file payloads."""
    from dataclasses import replace
    from loop_engine.core.harness_intelligence import HarnessIntelligenceDraft, item_from_body
    from loop_engine.core.service_runtime.catalogue_bundle import BUNDLE_ITEM_RECORD_TYPE
    from loop_engine.core.service_runtime.catalogue_packages import CataloguePackage, CataloguePackageFile, sha256_hex
    identity = identity or f"synthetic_skill_{index:06d}"
    purpose = " ".join(rng.choice(words) for _ in range(rng.randint(20, 40)))
    target = max(600, int(rng.gauss(2800, 700)))
    body = (f"# {identity}\n\nVersion {version}. {purpose}\n\n" + " ".join(
        rng.choice(words) for _ in range(target // 6))).encode()[:target] + b"\n"
    shape = rng.random()
    files = [("SKILL.md", body, "text/markdown", "skill_definition")]
    effects = ()
    if shape < 0.20:
        files = [("SKILL.md", body[: int(len(body) * 0.72)] + b"\n", "text/markdown", "skill_definition"),
                 ("references/notes.md", body[int(len(body) * 0.72):], "text/markdown", "skill_reference"),
                 ("assets/example.json", json.dumps({"example": identity, "version": version}).encode(),
                  "application/json", "skill_asset")]
        if shape < 0.05:
            files.append(("scripts/run.py", f"print({identity!r})\n".encode(), "text/x-python", "skill_script"))
            effects = ("spawns_process",)
    entries = tuple(CataloguePackageFile(path, sha256_hex(data), len(data), media, role)
                    for path, data, media, role in files)
    package = CataloguePackage(entries, "file" if len(entries) == 1 else "package")
    draft = HarnessIntelligenceDraft(identity, "skill", purpose, "harness_local", f"synthetic:{identity}", "MIT",
                                     effects)
    item = replace(item_from_body(draft, "x"), digest=package.served_digest, size_bytes=package.served_size)
    line = {"record_type": BUNDLE_ITEM_RECORD_TYPE, "reference": item.reference(), "package": package.to_dict(),
            "approval": {"tier": "verified", "approval_ref": f"synthetic-review:{identity}",
                         "approved_digest": package.served_digest},
            "attributes": {"cited_source": rng.choice(sources),
                           "origin_layer": rng.choice(["context_intelligence", "code_intelligence"]),
                           "catalogued_on": f"2026-09-{rng.randint(1, 22):02d}", "batch": "synthetic"}}
    return line, [data for _path, data, _media, _role in files]


def _size(path):
    return sum(entry.stat().st_size for entry in Path(path).rglob("*") if entry.is_file())


def _allocated(path):
    """Bytes the file system allocated, which a small file rounds up to one block."""
    return sum(entry.stat().st_blocks * 512 for entry in Path(path).rglob("*") if entry.is_file())


def _service(root, engine="in_memory_view_index"):
    from loop_engine.core.service_runtime.catalogue_releases import CatalogueOperatorContext
    from loop_engine.core.service_runtime.catalogue_serving import CatalogueSourceSettings
    from loop_engine.core.service_runtime.records import ServiceRuntimeConfig
    from loop_engine.core.service_runtime.storage import ServiceCatalogBinding
    config = ServiceRuntimeConfig(str(root / "service.db"), writes_authorized=True)
    if engine == "in_memory_view_index":
        settings = CatalogueSourceSettings("store", str(root / "bodies"), refresh_seconds=5)
    else:
        (root / "index").mkdir(exist_ok=True)
        settings = CatalogueSourceSettings("store", str(root / "bodies"), refresh_seconds=5,
                                           record_type="service_catalogue_source/v2", search_engine=engine,
                                           index_root=str(root / "index"))
    return config, CatalogueOperatorContext(ServiceCatalogBinding(config), str(root / "bodies")), settings


def _with_versions(lines):
    """Each bundle line with the item version digest the service will compute for it."""
    from loop_engine.core.service_runtime.catalogue_bundle import validate_item
    from loop_engine.core.service_runtime.catalogue_schema import CatalogueAttributeSchema
    from loop_engine.core.service_runtime.http_entrypoint import DEFAULT_FAMILY_POLICY, DEFAULT_LICENSE_POLICY
    schema = CatalogueAttributeSchema.from_dict(json.loads((STARTER / "attribute-schema.json").read_text()))
    return [(line, validate_item(line, schema, license_policy=DEFAULT_LICENSE_POLICY,
                                 family_policy=DEFAULT_FAMILY_POLICY).version) for line in lines]


def prepare(count, root, seed, lift=False, segmented=False, scattered=False):
    limit = _lift_bundle_limit(count) if lift else None
    from loop_engine.core.service_runtime.catalogue_bundle import read_bundle, write_bundle
    from loop_engine.core.service_runtime.catalogue_grants import follow_active_release
    from loop_engine.core.service_runtime.catalogue_releases import publish
    from loop_engine.core.service_runtime.catalogue_schema import CatalogueAttributeSchema
    from loop_engine.core.service_runtime.http_entrypoint import DEFAULT_FAMILY_POLICY, DEFAULT_LICENSE_POLICY
    from loop_engine.core.service_runtime.records import TenantKeyIssue, TenantRegistration
    from loop_engine.core.service_runtime.runtime import ServiceRuntime
    (root / "bodies").mkdir(parents=True)
    rng, words = random.Random(seed), _words()
    sources = [f"src/loop_engine/synthetic/module_{index:02d}.py" for index in range(40)]
    schema = CatalogueAttributeSchema.from_dict(json.loads((STARTER / "attribute-schema.json").read_text()))
    started = time.perf_counter()
    lines, payloads = [], []
    for index in range(count):
        line, files = _item(index, rng, words, sources)
        lines.append(line)
        payloads.extend(files)
    generated = time.perf_counter() - started
    from loop_engine.core.service_runtime import catalogue_segments
    started = time.perf_counter()
    if segmented:
        versioned = _with_versions(lines)
        digest = catalogue_segments.write_segmented_bundle(root / "bundle-1", schema=schema, items=versioned,
                                                           payloads=payloads, notes="synthetic")
    else:
        digest = write_bundle(root / "bundle-1", schema=schema, lines=lines, payloads=payloads, notes="synthetic")
    written = time.perf_counter() - started
    started = time.perf_counter()
    bundle = (catalogue_segments.read_segmented_bundle(root / "bundle-1", license_policy=DEFAULT_LICENSE_POLICY,
                                                       family_policy=DEFAULT_FAMILY_POLICY) if segmented else
              read_bundle(root / "bundle-1", license_policy=DEFAULT_LICENSE_POLICY, family_policy=DEFAULT_FAMILY_POLICY))
    validated = time.perf_counter() - started
    config, context, _settings = _service(root)
    runtime = ServiceRuntime(config)
    runtime.register_tenant(TenantRegistration("measure", "tenant:measure"))
    key = runtime.issue_key(TenantKeyIssue("measure", "local measurement"))
    follow_active_release(runtime, ["measure"])
    started = time.perf_counter()
    from loop_engine.core.service_runtime.catalogue_segment_publish import publish_segmented
    first = (publish_segmented(context, bundle) if segmented else publish(context, bundle))
    published = time.perf_counter() - started
    if scattered:
        # The changed items and the new identities are spread over the whole library, as a daily release's are,
        # so a segmented release rewrites one segment for each of them: the worst case for segments.
        changed_at = list(range(0, count, max(1, count // SECOND_RELEASE_CHANGED)))[:SECOND_RELEASE_CHANGED]
        added_after = list(range(0, count, max(1, count // SECOND_RELEASE_NEW)))[:SECOND_RELEASE_NEW]
        changed = [_item(index, rng, words, sources, version=2) for index in changed_at]
        added = [_item(count + index, rng, words, sources, identity=f"synthetic_skill_{after:06d}_added")
                 for index, after in enumerate(added_after)]
        kept = [line for index, line in enumerate(lines) if index not in set(changed_at)]
    else:
        changed = [_item(index, rng, words, sources, version=2) for index in range(SECOND_RELEASE_CHANGED)]
        added = [_item(count + index, rng, words, sources) for index in range(SECOND_RELEASE_NEW)]
        kept = lines[SECOND_RELEASE_CHANGED:]
    second_lines = [line for line, _files in changed + added] + kept
    second_payloads = [data for _line, files in changed + added for data in files]
    if segmented:
        # The second bundle carries exactly what the publish tool uploads: segments and item lines the first
        # release does not hold, and the new bodies.
        held_segments = {ref.digest for ref in bundle.segments}
        held_versions = {version for _line, version in versioned}
        second = _with_versions(second_lines)
        new_segments = {ref.digest for ref, _document in catalogue_segments.membership_segments(
            sorted((line["reference"]["identity"], version) for line, version in second), bundle.segmentation)}
        catalogue_segments.write_segmented_bundle(
            root / "bundle-2", schema=schema, items=second, payloads=second_payloads, notes="second",
            carry=catalogue_segments.Carried(
                segments=frozenset(new_segments - held_segments),
                items=frozenset(version for _line, version in second if version not in held_versions)))
    else:
        write_bundle(root / "bundle-2", schema=schema, lines=second_lines, payloads=second_payloads, notes="second")
    with context.binding.store() as store:
        from loop_engine.core.service_runtime.catalogue_releases import ITEM_KIND, RELEASE_KIND
        release_row = context.binding.read(store, RELEASE_KIND, first["release_id"])
        item_rows = context.binding.rows_all(store, ITEM_KIND)
    return {"items": count, "files": len(payloads), "body_bytes": sum(len(value) for value in payloads),
            "multi_file_items": sum(1 for line in lines if line["package"]["body_form"] == "package"),
            "seconds": {"generate": round(generated, 2), "write_bundle": round(written, 2),
                        "validate_bundle": round(validated, 2), "publish": round(published, 2)},
            "bundle_digest": digest, "bundle_bytes_on_disk": _size(root / "bundle-1"),
            "release_record_bytes": len(json.dumps(release_row["payload"], separators=(",", ":"))),
            "item_version_records_bytes": sum(len(json.dumps(row["payload"], separators=(",", ":")))
                                              for row in item_rows),
            "service_store_bytes_on_disk": sum(Path(str(config.database_path) + suffix).stat().st_size
                                               for suffix in ("", "-wal") if Path(str(config.database_path) + suffix).exists()),
            "body_store_bytes_on_disk": _size(root / "bodies"),
            "body_store_bytes_allocated": _allocated(root / "bodies"),
            "bundle_bytes_allocated": _allocated(root / "bundle-1"),
            "bundle_item_limit": limit, "bundle_item_limit_lifted_for_measurement": bool(lift),
            "segmented": segmented, "scattered_delta": scattered, "first_publish_result": {key: value for key, value in first.items()
                                                             if key not in ("release_id",)},
            "second_bundle_bytes_on_disk": _size(root / "bundle-2"),
            "key": key.key, "first_release": first["release_id"]}


def publish_second(root, count=0, lift=False):
    if lift:
        _lift_bundle_limit(count)
    from loop_engine.core.service_runtime.catalogue_releases import publish
    from loop_engine.core.service_runtime.catalogue_segment_publish import publish_segmented
    from loop_engine.core.service_runtime.catalogue_segments import SegmentedBundle, read_any_bundle
    from loop_engine.core.service_runtime.http_entrypoint import DEFAULT_FAMILY_POLICY, DEFAULT_LICENSE_POLICY
    _config, context, _settings = _service(root)
    started = time.perf_counter()
    bundle = read_any_bundle(root / "bundle-2", license_policy=DEFAULT_LICENSE_POLICY,
                             family_policy=DEFAULT_FAMILY_POLICY)
    result = (publish_segmented(context, bundle) if isinstance(bundle, SegmentedBundle) else publish(context, bundle))
    return {"seconds": round(time.perf_counter() - started, 2), "release_id": result["release_id"],
            "added": result["added"], "changed": result["changed"], "bodies_written": result["bodies_written"],
            **{key: result[key] for key in ("segments", "segments_written", "items_written") if key in result}}


def _latencies(action, rounds):
    values = []
    for query in rounds:
        started = time.perf_counter()
        action(query)
        values.append((time.perf_counter() - started) * 1000)
    values.sort()
    return {"p50_ms": round(statistics.median(values), 1),
            "p95_ms": round(values[max(0, int(len(values) * 0.95) - 1)], 1), "samples": len(values)}


def index(root, engine):
    """Build the disk index of the active release in this process, as index-catalogue does on a host."""
    from loop_engine.core.service_runtime.catalogue_disk_view import ensure_release_index
    from loop_engine.core.service_runtime.http_entrypoint import DEFAULT_FAMILY_POLICY, DEFAULT_LICENSE_POLICY
    config, _context, settings = _service(root, engine)
    before = _status_kib()
    started = time.perf_counter()
    header, descriptor, _state = ensure_release_index(config, settings, license_policy=DEFAULT_LICENSE_POLICY,
                                                      family_policy=DEFAULT_FAMILY_POLICY)
    seconds = time.perf_counter() - started
    folder = root / "index" / "indexes" / descriptor["base"]
    return {"seconds": round(seconds, 2), "release_id": header.release_id, "base": descriptor["base"],
            "index_bytes": sum(path.stat().st_size for path in folder.iterdir() if path.is_file()),
            "process_status_kib_before": before, "process_status_kib_after": _status_kib(),
            "note": "one process, one worker, reading every item record and body of the release, as index-catalogue"}


def serve(root, key, seed, count=0, lift=False, engine="in_memory_view_index"):
    from loop_engine.core.service_runtime.catalogue_search import authorized_hits
    from loop_engine.core.service_runtime.catalogue_serving import (CatalogueRefresher, next_view, state_token,
                                                                    store_view)
    from loop_engine.core.service_runtime.http_entrypoint import DEFAULT_FAMILY_POLICY, DEFAULT_LICENSE_POLICY
    from loop_engine.core.service_runtime.provisioning import DurableProvisioningBinding
    from loop_engine.core.service_runtime.runtime import ServiceRuntime
    config, _context, settings = _service(root, engine)
    runtime = ServiceRuntime(config)
    before = _peak_rss_kib()
    started = time.perf_counter()
    view = store_view(config, settings, license_policy=DEFAULT_LICENSE_POLICY, family_policy=DEFAULT_FAMILY_POLICY)
    built = time.perf_counter() - started
    after_build = _peak_rss_kib()
    binding = DurableProvisioningBinding(runtime, view.catalogue, view.qualification_resolver, view.body_reader,
                                         view=view)
    principal = runtime.authenticate_key(key)
    rng, words = random.Random(seed + 1), _words()
    queries = [" ".join(rng.choice(words) for _ in range(rng.randint(2, 5))) for _ in range(QUERIES)]

    def search(mode, filters=None):
        def run(query):
            current = binding.current_view()

            def authorize(candidates):
                listing = binding.invoke_for_principal(principal, "list", view=current, candidates=candidates)
                return {row["identity"]: row for row in listing["items"]}
            fields = {"query": query, "mode": mode, "top_n": 10}
            if filters:
                fields["filters"] = filters
            return authorized_hits(current, fields, authorize)
        return run
    index = view.search_index()
    if engine == "in_memory_view_index":
        fts_pages = index._connection.execute("PRAGMA page_count").fetchone()[0]
        fts_page_size = index._connection.execute("PRAGMA page_size").fetchone()[0]
        started = time.perf_counter()
        components = _component_memory(view)
        components["walk_seconds"] = round(time.perf_counter() - started, 2)
        index_stats = {**index.stats(), "full_text_bytes_in_memory": fts_pages * fts_page_size, "stored_on_disk": False}
    else:
        components = {"record_type": "catalogue_view_component_memory/v1", "engine": engine,
                      "note": "the disk view holds no per-item parts; see the process memory figures",
                      "process_status_kib": _status_kib()}
        index_stats = index.stats()
    results = {"engine": engine, "view_build_seconds": round(built, 2),
               "process_peak_rss_kib_before_build": before, "process_peak_rss_kib_after_build": after_build,
               "process_rss_kib_after_build": _rss_kib(), "component_memory": components,
               "index": index_stats,
               "search_lexical": _latencies(search("lexical"), queries),
               "search_hybrid": _latencies(search("hybrid"), queries),
               "search_lexical_with_filter": _latencies(
                   search("lexical", {"origin_layer": {"equals": "code_intelligence"}}), queries)}
    results["process_status_kib_after_searches"] = _status_kib()
    # A manifest is decided by the one grant of the identity it names; time it across the library.
    samples = [f"synthetic_skill_{position:06d}" for position in range(0, max(1, count),
                                                                        max(1, count // MANIFEST_SAMPLES))]
    results["manifest"] = _latencies(
        lambda identity: binding.invoke_for_principal(principal, "manifest", identity=identity), samples)
    started = time.perf_counter()
    held = binding.invoke_for_principal(principal, "discover")["items_held"]
    results["discover"] = {"items_held": held, "seconds": round(time.perf_counter() - started, 2),
                           "process_status_kib_after": _status_kib()}
    full = time.perf_counter()
    listed = len(binding.invoke_for_principal(principal, "list")["items"])
    results["full_listing"] = {"items": listed, "seconds": round(time.perf_counter() - full, 2),
                               "process_status_kib_after": _status_kib()}
    from loop_engine.core.service_runtime.library_page import library_rows
    started = time.perf_counter()
    rows = len(library_rows(binding.current_view()))
    results["library_page_rows"] = {"rows": rows, "seconds": round(time.perf_counter() - started, 2),
                                    "process_status_kib_after": _status_kib()}
    refresher = CatalogueRefresher(binding, build=lambda current, token: next_view(
        current, token, config, settings, license_policy=DEFAULT_LICENSE_POLICY, family_policy=DEFAULT_FAMILY_POLICY),
        probe=lambda: state_token(config), interval_seconds=5)
    second = subprocess.run([sys.executable, __file__, "--phase", PUBLISH_SECOND_PHASE, "--root", str(root),
                             "--items", str(count)] + (["--lift-bundle-limit"] if lift else []),
                            capture_output=True, text=True, check=True, env={**os.environ})
    results["second_publish"] = json.loads(second.stdout)
    started = time.perf_counter()
    swapped = refresher.check_once()
    results["hot_swap"] = {"seconds": round(time.perf_counter() - started, 2), "changed": swapped.get("changed"),
                           "failure": swapped.get("failure"),
                           "release_is_second": binding.current_view().release_id == results["second_publish"]["release_id"],
                           "process_peak_rss_kib_after_swap": _peak_rss_kib(), "process_rss_kib_after_swap": _rss_kib()}
    results["search_hybrid_after_swap"] = _latencies(search("hybrid"), queries[:20])
    results["process_status_kib_at_end"] = _status_kib()
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--items", type=int, default=10_000)
    parser.add_argument("--root", type=Path, required=True, help="An empty scratch folder outside the repository.")
    parser.add_argument("--seed", type=int, default=20260922)
    parser.add_argument("--phase", choices=PHASES, default=ALL_PHASES)
    parser.add_argument("--key", help="serve: the measurement account's key, from prepare.")
    parser.add_argument("--lift-bundle-limit", action="store_true",
                        help="Raise the bundle reader's 200,000-item bound inside the measurement processes only.")
    parser.add_argument("--segmented", action="store_true", help="Publish version 2 (segmented) releases.")
    parser.add_argument("--scattered-delta", action="store_true",
                        help="Spread the second release's changed and new items over the whole library.")
    parser.add_argument("--engine", default="in_memory_view_index",
                        choices=("in_memory_view_index", "sqlite_disk_index"), help="serve: the search index engine.")
    options = parser.parse_args(argv)
    root = options.root.resolve()
    lift = options.lift_bundle_limit
    phases = {PREPARE_PHASE: lambda: prepare(options.items, root, options.seed, lift, options.segmented,
                                             options.scattered_delta),
              PUBLISH_SECOND_PHASE: lambda: publish_second(root, options.items, lift),
              INDEX_PHASE: lambda: index(root, options.engine),
              SERVE_PHASE: lambda: serve(root, options.key, options.seed, options.items, lift, options.engine)}
    if options.phase in phases:
        print(json.dumps(phases[options.phase]()))
        return 0
    if root.exists() and any(root.iterdir()) or REPOSITORY in root.parents:
        parser.error("the root is an empty scratch folder outside the repository")
    root.mkdir(parents=True, exist_ok=True)
    run = [sys.executable, __file__, "--root", str(root), "--items", str(options.items), "--seed", str(options.seed)]
    run += ["--lift-bundle-limit"] if lift else []
    run += ["--segmented"] if options.segmented else []
    run += ["--scattered-delta"] if options.scattered_delta else []
    run += ["--engine", options.engine]
    prepared = json.loads(subprocess.run([*run, "--phase", PREPARE_PHASE], capture_output=True, text=True,
                                         check=True).stdout)
    indexed = (json.loads(subprocess.run([*run, "--phase", INDEX_PHASE], capture_output=True, text=True,
                                         check=True).stdout) if options.engine != "in_memory_view_index" else None)
    served = json.loads(subprocess.run([*run, "--phase", SERVE_PHASE, "--key", prepared.pop("key")],
                                       capture_output=True, text=True, check=True).stdout)
    import platform
    print(json.dumps({"record_type": RESULT_RECORD_TYPE, "label": "local measurement on one workstation, not a "
                      "production claim", "measured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                      "machine": {"processors": os.cpu_count(), "python": platform.python_version(),
                                  "platform": platform.platform()},
                      "options": {"segmented": options.segmented, "engine": options.engine,
                                  "scattered_delta": options.scattered_delta},
                      "load_average_at_end": [round(value, 1) for value in os.getloadavg()],
                      "prepare": prepared, "index_build": indexed, "serve": served}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
