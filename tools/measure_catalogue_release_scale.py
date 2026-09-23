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
PHASES = ("all", "prepare", "serve", "publish-second")
ALL_PHASES, PREPARE_PHASE, SERVE_PHASE, PUBLISH_SECOND_PHASE = PHASES
SECOND_RELEASE_NEW, SECOND_RELEASE_CHANGED = 100, 10


def _words():
    manifest = json.loads((STARTER / "host-release" / "manifest.json").read_text("utf-8"))
    return " ".join(row["reference"]["purpose"] for row in manifest["items"]).split()


def _peak_rss_kib():
    for line in Path("/proc/self/status").read_text().splitlines():
        if line.startswith("VmHWM:"):
            return int(line.split()[1])
    return None


def _item(index, rng, words, sources, version=1):
    """One synthetic bundle line and its file payloads."""
    from dataclasses import replace
    from loop_engine.core.harness_intelligence import HarnessIntelligenceDraft, item_from_body
    from loop_engine.core.service_runtime.catalogue_bundle import BUNDLE_ITEM_RECORD_TYPE
    from loop_engine.core.service_runtime.catalogue_packages import CataloguePackage, CataloguePackageFile, sha256_hex
    identity = f"synthetic_skill_{index:06d}"
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
            "approval": {"approval_ref": f"synthetic-review:{identity}", "approved_digest": package.served_digest},
            "attributes": {"cited_source": rng.choice(sources),
                           "origin_layer": rng.choice(["context_intelligence", "code_intelligence"]),
                           "catalogued_on": f"2026-09-{rng.randint(1, 22):02d}", "batch": "synthetic"}}
    return line, [data for _path, data, _media, _role in files]


def _size(path):
    return sum(entry.stat().st_size for entry in Path(path).rglob("*") if entry.is_file())


def _allocated(path):
    """Bytes the file system allocated, which a small file rounds up to one block."""
    return sum(entry.stat().st_blocks * 512 for entry in Path(path).rglob("*") if entry.is_file())


def _service(root):
    from loop_engine.core.service_runtime.catalogue_releases import CatalogueOperatorContext
    from loop_engine.core.service_runtime.catalogue_serving import CatalogueSourceSettings
    from loop_engine.core.service_runtime.records import ServiceRuntimeConfig
    from loop_engine.core.service_runtime.storage import ServiceCatalogBinding
    config = ServiceRuntimeConfig(str(root / "service.db"), writes_authorized=True)
    return config, CatalogueOperatorContext(ServiceCatalogBinding(config), str(root / "bodies")), \
        CatalogueSourceSettings("store", str(root / "bodies"), refresh_seconds=5)


def prepare(count, root, seed):
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
    started = time.perf_counter()
    digest = write_bundle(root / "bundle-1", schema=schema, lines=lines, payloads=payloads, notes="synthetic")
    written = time.perf_counter() - started
    started = time.perf_counter()
    bundle = read_bundle(root / "bundle-1", license_policy=DEFAULT_LICENSE_POLICY, family_policy=DEFAULT_FAMILY_POLICY)
    validated = time.perf_counter() - started
    config, context, _settings = _service(root)
    runtime = ServiceRuntime(config)
    runtime.register_tenant(TenantRegistration("measure", "tenant:measure"))
    key = runtime.issue_key(TenantKeyIssue("measure", "local measurement"))
    follow_active_release(runtime, ["measure"])
    started = time.perf_counter()
    first = publish(context, bundle)
    published = time.perf_counter() - started
    changed = [_item(index, rng, words, sources, version=2) for index in range(SECOND_RELEASE_CHANGED)]
    added = [_item(count + index, rng, words, sources) for index in range(SECOND_RELEASE_NEW)]
    second_lines = [line for line, _files in changed + added] + lines[SECOND_RELEASE_CHANGED:]
    write_bundle(root / "bundle-2", schema=schema, lines=second_lines,
                 payloads=[data for _line, files in changed + added for data in files], notes="second")
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
            "key": key.key, "first_release": first["release_id"]}


def publish_second(root):
    from loop_engine.core.service_runtime.catalogue_bundle import read_bundle
    from loop_engine.core.service_runtime.catalogue_releases import publish
    from loop_engine.core.service_runtime.http_entrypoint import DEFAULT_FAMILY_POLICY, DEFAULT_LICENSE_POLICY
    _config, context, _settings = _service(root)
    started = time.perf_counter()
    bundle = read_bundle(root / "bundle-2", license_policy=DEFAULT_LICENSE_POLICY, family_policy=DEFAULT_FAMILY_POLICY)
    result = publish(context, bundle)
    return {"seconds": round(time.perf_counter() - started, 2), "release_id": result["release_id"],
            "added": result["added"], "changed": result["changed"], "bodies_written": result["bodies_written"]}


def _latencies(action, rounds):
    values = []
    for query in rounds:
        started = time.perf_counter()
        action(query)
        values.append((time.perf_counter() - started) * 1000)
    values.sort()
    return {"p50_ms": round(statistics.median(values), 1),
            "p95_ms": round(values[max(0, int(len(values) * 0.95) - 1)], 1), "samples": len(values)}


def serve(root, key, seed):
    from loop_engine.core.service_runtime.catalogue_search import authorized_hits
    from loop_engine.core.service_runtime.catalogue_serving import (CatalogueRefresher, next_view, state_token,
                                                                    store_view)
    from loop_engine.core.service_runtime.http_entrypoint import DEFAULT_FAMILY_POLICY, DEFAULT_LICENSE_POLICY
    from loop_engine.core.service_runtime.provisioning import DurableProvisioningBinding
    from loop_engine.core.service_runtime.runtime import ServiceRuntime
    config, _context, settings = _service(root)
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
    fts_pages = index._connection.execute("PRAGMA page_count").fetchone()[0]
    fts_page_size = index._connection.execute("PRAGMA page_size").fetchone()[0]
    results = {"view_build_seconds": round(built, 2),
               "process_peak_rss_kib_before_build": before, "process_peak_rss_kib_after_build": after_build,
               "index": {**index.stats(), "full_text_bytes_in_memory": fts_pages * fts_page_size,
                         "stored_on_disk": False},
               "search_lexical": _latencies(search("lexical"), queries),
               "search_hybrid": _latencies(search("hybrid"), queries),
               "search_lexical_with_filter": _latencies(
                   search("lexical", {"origin_layer": {"equals": "code_intelligence"}}), queries)}
    full = time.perf_counter()
    listed = len(binding.invoke_for_principal(principal, "list")["items"])
    results["full_listing"] = {"items": listed, "seconds": round(time.perf_counter() - full, 2)}
    refresher = CatalogueRefresher(binding, build=lambda current, token: next_view(
        current, token, config, settings, license_policy=DEFAULT_LICENSE_POLICY, family_policy=DEFAULT_FAMILY_POLICY),
        probe=lambda: state_token(config), interval_seconds=5)
    second = subprocess.run([sys.executable, __file__, "--phase", PUBLISH_SECOND_PHASE, "--root", str(root)],
                            capture_output=True, text=True, check=True, env={**os.environ})
    results["second_publish"] = json.loads(second.stdout)
    started = time.perf_counter()
    swapped = refresher.check_once()
    results["hot_swap"] = {"seconds": round(time.perf_counter() - started, 2), "changed": swapped.get("changed"),
                           "failure": swapped.get("failure"),
                           "release_is_second": binding.current_view().release_id == results["second_publish"]["release_id"],
                           "process_peak_rss_kib_after_swap": _peak_rss_kib()}
    results["search_hybrid_after_swap"] = _latencies(search("hybrid"), queries[:20])
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--items", type=int, default=10_000)
    parser.add_argument("--root", type=Path, required=True, help="An empty scratch folder outside the repository.")
    parser.add_argument("--seed", type=int, default=20260922)
    parser.add_argument("--phase", choices=PHASES, default=ALL_PHASES)
    parser.add_argument("--key", help="serve: the measurement account's key, from prepare.")
    options = parser.parse_args(argv)
    root = options.root.resolve()
    phases = {PREPARE_PHASE: lambda: prepare(options.items, root, options.seed),
              PUBLISH_SECOND_PHASE: lambda: publish_second(root),
              SERVE_PHASE: lambda: serve(root, options.key, options.seed)}
    if options.phase in phases:
        print(json.dumps(phases[options.phase]()))
        return 0
    if root.exists() and any(root.iterdir()) or REPOSITORY in root.parents:
        parser.error("the root is an empty scratch folder outside the repository")
    root.mkdir(parents=True, exist_ok=True)
    run = [sys.executable, __file__, "--root", str(root), "--items", str(options.items), "--seed", str(options.seed)]
    prepared = json.loads(subprocess.run([*run, "--phase", PREPARE_PHASE], capture_output=True, text=True,
                                         check=True).stdout)
    served = json.loads(subprocess.run([*run, "--phase", SERVE_PHASE, "--key", prepared.pop("key")],
                                       capture_output=True, text=True, check=True).stdout)
    import platform
    print(json.dumps({"record_type": RESULT_RECORD_TYPE, "label": "local measurement on one workstation, not a "
                      "production claim", "measured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                      "machine": {"processors": os.cpu_count(), "python": platform.python_version(),
                                  "platform": platform.platform()},
                      "prepare": prepared, "serve": served}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
