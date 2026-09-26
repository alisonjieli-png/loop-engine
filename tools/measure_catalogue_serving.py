"""Measure how the service serves one real catalogue release bundle, and labelled synthetic doublings of it.

Kind: local measurement tool. It publishes a real release bundle into a
temporary service store and body folder with the service's own code, the way
`catalogue_release_checks.Fixture` does (`ServiceRuntimeConfig`,
`CatalogueOperatorContext`, `read_bundle`, `publish`, `store_view`), and
measures in separate processes what one Fly Machine would carry:

```text
Measured for each library size
├── index build     the time to build the served view and its one search index
├── peak memory     the resident high-water mark (resource and /proc) of the
│                   serving process, and the Python allocation peak (tracemalloc)
│                   from a second build in its own process
├── release swap    the time the refresher takes to verify and swap in a second
│                   release published by another process while the view is served
├── search latency  p50 and p95 over varied queries in the lexical and hybrid
│                   modes, through the same authorized search the service runs
├── listing latency the full authorized listing of a release-following account
└── store on disk   the service database and the body store
```

The first size is the real bundle as it is. Each further size doubles the
library with synthetic copies of the same items: each copy has a new
identity, a marker line appended to every file, so new digests, a purpose
that starts with "Synthetic copy", a synthetic approval reference and the
synthetic batch attribute. The record of every copy says so, and no copy is
ever served to anyone: every store lives under the root, which must be an
empty or absent folder outside this repository and outside the live
service's volume. The bundle folder is only read.

    PYTHONPATH=src python tools/measure_catalogue_serving.py \
        --bundle /home/username/baltor-bundles/daily-2026-09-26-10 \
        --root "$HOME/.le-ci-tmp/serving-measurement/run-1" --factors 1 2 4 \
        --output artifacts/serving-measurement-2026-09-26/measurement-6398-local-1.json

The tool takes no host file, no network address and no credential, so it
cannot touch the live service. The numbers describe this machine only: they
are a local measurement, not a production claim.

Four processes are used so that the serving process's memory is its own:
`prepare` writes any synthetic bundle and publishes the first release,
`trace` builds the view of that release under tracemalloc, `serve` builds
the same view without tracing and measures it, and `serve` starts
`publish-second` as a separate process when it measures the swap.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import platform
import random
import re
import resource
import statistics
import subprocess
import sys
import time
import tracemalloc

REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY / "src"))

RESULT_RECORD_TYPE = "catalogue_serving_measurement/v1"
LABEL = ("local measurement on one workstation of a real release bundle and labelled synthetic doublings of it; "
         "not a production claim")
#: The volume the live service mounts. The tool refuses to write under it.
LIVE_VOLUME = Path("/data")
#: The licences the live host file accepted on September 25, 2026.
LIVE_ACCEPTED_LICENSES = ("MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "CC0-1.0", "CC-BY-4.0")
PHASES = ("all", "prepare", "serve", "trace", "publish-second")
ALL_PHASE, PREPARE_PHASE, SERVE_PHASE, TRACE_PHASE, PUBLISH_SECOND_PHASE = PHASES
DEFAULT_FACTORS = (1, 2, 4)
DEFAULT_QUERIES = 50
DEFAULT_REPETITIONS = 5
DEFAULT_SEED = 20260926
#: The second release changes this many served items and adds this many synthetic ones.
SECOND_RELEASE_CHANGED, SECOND_RELEASE_NEW = 10, 100
MEASUREMENT_DATE = "2026-09-26"
SYNTHETIC_BATCH = "synthetic-serving-measurement-" + MEASUREMENT_DATE
SYNTHETIC_PURPOSE_PREFIX = "Synthetic copy"
TENANT = "measure"
_WORD = re.compile(r"[a-z][a-z0-9]{2,}")


class MeasurementRefused(Exception):
    """A named refusal: the tool did not write anything."""

    def __init__(self, code, detail=""):
        super().__init__(code if not detail else f"{code}: {detail}")
        self.code = code


def root_refusal(root, bundle):
    """Empty text when the root may hold stores and synthetic bundles, otherwise the refusal code.

    The root is never inside this repository, so no synthetic bundle or store
    can be committed by mistake; never on the live service's volume; never
    inside the bundle it reads; and never a folder that already holds files.
    """
    root, bundle = Path(root), Path(bundle)
    if root == REPOSITORY or REPOSITORY in root.parents:
        return "root_inside_repository"
    if root == LIVE_VOLUME or LIVE_VOLUME in root.parents:
        return "root_is_live_volume"
    if root == bundle or bundle in root.parents:
        return "root_inside_bundle"
    if root in bundle.parents:
        return "bundle_inside_root"
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        return "root_not_empty"
    return ""


def bundle_refusal(bundle):
    """Empty text when the bundle is an existing absolute bundle folder, otherwise the refusal code."""
    bundle = Path(bundle)
    if not bundle.is_absolute() or not bundle.is_dir() or not (bundle / "bundle.json").is_file() \
            or not (bundle / "items.jsonl").is_file():
        return "bundle_folder_invalid"
    return ""


def policies(accepted_licenses):
    from loop_engine.core.service_runtime.http_entrypoint import DEFAULT_FAMILY_POLICY, HostLicensePolicy
    return HostLicensePolicy(accepted_licenses=tuple(accepted_licenses)), DEFAULT_FAMILY_POLICY


def service(root):
    """The temporary service store and body folder under one root, as the service's own code opens them."""
    from loop_engine.core.service_runtime.catalogue_releases import CatalogueOperatorContext
    from loop_engine.core.service_runtime.catalogue_serving import CatalogueSourceSettings
    from loop_engine.core.service_runtime.records import ServiceRuntimeConfig
    from loop_engine.core.service_runtime.storage import ServiceCatalogBinding
    config = ServiceRuntimeConfig(str(root / "service.db"), writes_authorized=True)
    context = CatalogueOperatorContext(ServiceCatalogBinding(config), str(root / "bodies"))
    settings = CatalogueSourceSettings("store", str(root / "bodies"), refresh_seconds=5)
    return config, context, settings


def load_rows(bundle):
    """The bundle's item lines as they are written, in file order."""
    with open(Path(bundle) / "items.jsonl", "rb") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def marker(copy_index, *, changed=False):
    what = "changed bytes" if changed else f"synthetic copy {copy_index}"
    return f"\n<!-- {what} for the serving measurement of {MEASUREMENT_DATE}; not a library item -->\n".encode()


def rewritten_line(row, copy_index, read_bytes, *, keep_identity=False):
    """A labelled synthetic copy of one bundle line, or the same item with changed bytes.

    `read_bytes(digest, size)` returns the original bytes of one file. A copy
    takes a new identity, a marker line on every file and so new digests, a
    purpose that says it is synthetic, a synthetic source reference and
    approval reference, and the synthetic batch attribute when the schema
    declares one. A changed item keeps its identity, purpose and source and
    takes new bytes and a new approval. Returns the line and its payloads.
    """
    from loop_engine.core.service_runtime.catalogue_packages import (CataloguePackage, CataloguePackageFile,
                                                                     sha256_hex)
    suffix = marker(copy_index, changed=keep_identity)
    files, payloads = [], []
    for entry in row["package"]["files"]:
        data = read_bytes(entry["digest"], entry["size_bytes"]) + suffix
        files.append(CataloguePackageFile(entry["path"], sha256_hex(data), len(data), entry["media_type"],
                                          entry["role"]))
        payloads.append(data)
    package = CataloguePackage(tuple(files), row["package"]["body_form"])
    reference = dict(row["reference"])
    identity = reference["identity"] if keep_identity else f"{reference['identity']}_synthetic_{copy_index}"
    reference.update(identity=identity, digest=package.served_digest, size_bytes=package.served_size)
    attributes = dict(row["attributes"])
    if not keep_identity:
        reference.update(purpose=f"{SYNTHETIC_PURPOSE_PREFIX} {copy_index}: {reference['purpose']}",
                         source_ref=f"synthetic-copy-{copy_index}:{reference['source_ref']}")
        if "batch" in attributes:
            attributes["batch"] = SYNTHETIC_BATCH
    line = {"record_type": row["record_type"], "reference": reference, "package": package.to_dict(),
            "approval": {"tier": row["approval"]["tier"],
                         "approval_ref": f"synthetic-measurement-{MEASUREMENT_DATE}:{identity}",
                         "approved_digest": package.served_digest},
            "attributes": attributes}
    return line, payloads


def is_synthetic(line):
    return line["reference"]["purpose"].startswith(SYNTHETIC_PURPOSE_PREFIX + " ")


def build_queries(rows, count, seed):
    """`count` varied queries of one to five words taken from the purposes of the real items."""
    rng = random.Random(seed)
    queries = []
    while len(queries) < count:
        words = _WORD.findall(rows[rng.randrange(len(rows))]["reference"]["purpose"].lower())
        if not words:
            continue
        length = rng.randint(1, 5)
        start = rng.randrange(max(1, len(words) - length + 1))
        queries.append(" ".join(words[start:start + length]))
    return queries


def _size(path):
    files = [entry for entry in Path(path).rglob("*") if entry.is_file()]
    return {"bytes": sum(entry.stat().st_size for entry in files),
            "bytes_allocated": sum(entry.stat().st_blocks * 512 for entry in files), "files": len(files)}


def store_sizes(root):
    """The service database with its journal files, and the body store, as they lie on disk."""
    database = Path(root) / "service.db"
    parts = {suffix: (Path(str(database) + suffix).stat().st_size if Path(str(database) + suffix).exists() else 0)
             for suffix in ("", "-wal", "-shm", "-journal")}
    bodies = _size(Path(root) / "bodies")
    return {"service_database_bytes": sum(parts.values()), "service_database_parts": parts,
            "body_store_bytes": bodies["bytes"], "body_store_bytes_allocated": bodies["bytes_allocated"],
            "body_store_files": bodies["files"],
            "total_bytes": sum(parts.values()) + bodies["bytes"],
            "total_bytes_allocated": sum(parts.values()) + bodies["bytes_allocated"]}


def memory_now():
    """The resident high-water mark from `resource` and `/proc`, and the resident size now, in KiB."""
    usage = resource.getrusage(resource.RUSAGE_SELF)
    status = {}
    try:
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith(("VmRSS:", "VmHWM:")):
                status[line.split(":")[0]] = int(line.split()[1])
    except OSError:
        pass
    return {"peak_rss_kib_resource": usage.ru_maxrss, "peak_rss_kib_proc": status.get("VmHWM"),
            "current_rss_kib": status.get("VmRSS"), "load_average": load_average()}


def load_average():
    """The machine's one, five and fifteen minute load averages, so a contended run says so."""
    try:
        return [round(value, 2) for value in os.getloadavg()]
    except OSError:
        return None


def machine():
    info = {"processors": os.cpu_count(), "python": platform.python_version(), "platform": platform.platform(),
            "kernel": platform.release(), "cpu_model": None, "memory_total_kib": None,
            "load_average_at_end": load_average()}
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                info["cpu_model"] = line.split(":", 1)[1].strip()
                break
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                info["memory_total_kib"] = int(line.split()[1])
                break
    except OSError:
        pass
    return info


def percentile(ordered, fraction):
    """Nearest-rank percentile of an ascending list, without pretending an empty sample is zero."""
    return ordered[max(0, math.ceil(len(ordered) * fraction) - 1)]


def latencies(action, queries):
    """p50, p95, mean and maximum in milliseconds over `queries`, and how many returned anything."""
    values, hits = [], []
    for query in queries:
        started = time.perf_counter()
        hits.append(action(query))
        values.append((time.perf_counter() - started) * 1000)
    ordered = sorted(values)
    return {"samples": len(values), "p50_ms": round(statistics.median(values), 2),
            "p95_ms": round(percentile(ordered, 0.95), 2), "mean_ms": round(statistics.fmean(values), 2),
            "max_ms": round(ordered[-1], 2), "queries_with_hits": sum(1 for count in hits if count),
            "hits_total": sum(hits)}


def _write_second_bundle(root, rows, served, schema, factor, read_bytes):
    """An incremental second release: changed bytes for a few real items and a few more synthetic items."""
    from loop_engine.core.service_runtime.catalogue_bundle import write_bundle
    changed = [rewritten_line(row, factor, read_bytes, keep_identity=True) for row in rows[:SECOND_RELEASE_CHANGED]]
    added = [rewritten_line(row, factor, read_bytes) for row in rows[:SECOND_RELEASE_NEW]]
    replaced = {line["reference"]["identity"] for line, _payloads in changed}
    lines = [line for line, _payloads in changed + added] + [
        line for line in served if line["reference"]["identity"] not in replaced]
    write_bundle(root / "bundle-second", schema=schema, lines=lines,
                 payloads=[data for _line, payloads in changed + added for data in payloads],
                 notes=f"Second release of the serving measurement of {MEASUREMENT_DATE}: {len(changed)} items with "
                       f"changed bytes and {len(added)} synthetic additions; not a library release.")
    return {"items": len(lines), "changed": len(changed), "added": len(added)}


def prepare(bundle, root, factor, accepted_licenses):
    """Write the synthetic bundle of `factor` times the real items when `factor` is above one, then publish."""
    from loop_engine.core.service_runtime.catalogue_bundle import read_bundle, write_bundle
    from loop_engine.core.service_runtime.catalogue_grants import follow_active_release
    from loop_engine.core.service_runtime.catalogue_packages import VolumeBodyStore
    from loop_engine.core.service_runtime.catalogue_releases import publish
    from loop_engine.core.service_runtime.catalogue_schema import CatalogueAttributeSchema
    from loop_engine.core.service_runtime.records import TenantRegistration
    from loop_engine.core.service_runtime.runtime import ServiceRuntime
    license_policy, family_policy = policies(accepted_licenses)
    root.mkdir(parents=True, exist_ok=True)
    (root / "bodies").mkdir()
    header = json.loads((bundle / "bundle.json").read_text("utf-8"))
    schema = CatalogueAttributeSchema.from_dict(header["schema"])
    rows = load_rows(bundle)
    read_bytes = VolumeBodyStore(str(bundle / "blobs")).read
    seconds = {}
    if factor == 1:
        source, served = bundle, rows
    else:
        started = time.perf_counter()
        served = list(rows)
        for copy_index in range(1, factor):
            served.extend(rewritten_line(row, copy_index, read_bytes)[0] for row in rows)

        def payloads():
            for row in rows:
                for entry in row["package"]["files"]:
                    yield read_bytes(entry["digest"], entry["size_bytes"])
            for copy_index in range(1, factor):
                for row in rows:
                    yield from rewritten_line(row, copy_index, read_bytes)[1]
        source = root / f"bundle-{factor}x"
        write_bundle(source, schema=schema, lines=served, payloads=payloads(),
                     notes=f"Synthetic doubling of {header['items']} real items by {factor} for the serving "
                           f"measurement of {MEASUREMENT_DATE}; not a library release.")
        seconds["write_synthetic_bundle"] = round(time.perf_counter() - started, 2)
    started = time.perf_counter()
    loaded = read_bundle(source, license_policy=license_policy, family_policy=family_policy)
    seconds["read_bundle"] = round(time.perf_counter() - started, 2)
    config, context, _settings = service(root)
    runtime = ServiceRuntime(config)
    runtime.register_tenant(TenantRegistration(TENANT, "tenant:" + TENANT))
    runtime.set_operator_entitlement(TENANT, valid_until=int(time.time()) + 86_400,
                                     evidence_ref="local-measurement-not-payment")
    follow_active_release(runtime, [TENANT])
    started = time.perf_counter()
    first = publish(context, loaded)
    seconds["publish"] = round(time.perf_counter() - started, 2)
    second = _write_second_bundle(root, rows, served, schema, factor, read_bytes)
    return {"factor": factor, "items": len(served), "real_items": len(rows), "synthetic_items": len(served) - len(rows),
            "files": sum(len(line["package"]["files"]) for line in served),
            "multi_file_items": sum(1 for line in served if line["package"]["body_form"] == "package"),
            "bundle_source": "the real bundle, read in place" if factor == 1
            else f"a synthetic bundle under the root: the real items and {factor - 1} labelled copies of each",
            "seconds": seconds, "release_id": first["release_id"], "publish_state": first["state"],
            "bodies_written": first["bodies_written"], "second_bundle": second,
            "bundle_bytes_on_disk": _size(source)["bytes"] if factor > 1 else None, "store": store_sizes(root),
            "memory": memory_now()}


def publish_second(root, accepted_licenses):
    from loop_engine.core.service_runtime.catalogue_bundle import read_bundle
    from loop_engine.core.service_runtime.catalogue_releases import publish
    license_policy, family_policy = policies(accepted_licenses)
    _config, context, _settings = service(root)
    started = time.perf_counter()
    bundle = read_bundle(root / "bundle-second", license_policy=license_policy, family_policy=family_policy)
    result = publish(context, bundle)
    return {"seconds": round(time.perf_counter() - started, 2), "release_id": result["release_id"],
            "added": result["added"], "changed": result["changed"], "bodies_written": result["bodies_written"]}


def serve(root, accepted_licenses, queries, repetitions):
    """Build the served view in this process and measure it, as the service process would carry it."""
    from loop_engine.core.facets import EFFECTS
    from loop_engine.core.service_runtime.catalogue_search import authorized_hits
    from loop_engine.core.service_runtime.catalogue_serving import (CatalogueRefresher, next_view, state_token,
                                                                    store_view)
    from loop_engine.core.service_runtime.provisioning import DurableProvisioningBinding
    from loop_engine.core.service_runtime.records import TenantKeyIssue
    from loop_engine.core.service_runtime.runtime import ServiceRuntime
    license_policy, family_policy = policies(accepted_licenses)
    config, _context, settings = service(root)
    runtime = ServiceRuntime(config)
    memory_before = memory_now()
    started = time.perf_counter()
    view = store_view(config, settings, license_policy=license_policy, family_policy=family_policy)
    build_seconds = round(time.perf_counter() - started, 3)
    memory_after_build = memory_now()
    binding = DurableProvisioningBinding(runtime, view.catalogue, view.qualification_resolver, view.body_reader,
                                         view=view)
    # The key is issued here and used here; it is never printed or passed to another process.
    principal = runtime.authenticate_key(runtime.issue_key(TenantKeyIssue(TENANT, "serving measurement")).key)
    every_effect = tuple(EFFECTS)

    def listing(authority=every_effect):
        return binding.invoke_for_principal(principal, "list", community_items="included",
                                            authority_effects=authority)

    def search(mode, *, filters=None, authority=every_effect):
        def run(query):
            current = binding.current_view()

            def authorize(candidates):
                rows = binding.invoke_for_principal(principal, "list", view=current, candidates=candidates,
                                                    community_items="included", authority_effects=authority)["items"]
                return {row["identity"]: row for row in rows}
            fields = {"query": query, "mode": mode, "top_n": 10}
            if filters:
                fields["filters"] = filters
            hits, _rows = authorized_hits(current, fields, authorize)
            return len(hits)
        return run

    def timed_search(mode, **fields):
        action = search(mode, **fields)
        started = time.perf_counter()
        first_hits = action(queries[0])
        first_ms = round((time.perf_counter() - started) * 1000, 2)
        return {**latencies(action, queries), "first_query_ms": first_ms, "first_query_hits": first_hits}
    index = view.search_index()
    pages = index._connection.execute("PRAGMA page_count").fetchone()[0]
    page_size = index._connection.execute("PRAGMA page_size").fetchone()[0]
    results = {"view_build_seconds": build_seconds, "items_in_view": len(view.catalogue.items),
               "memory_before_build": memory_before, "memory_after_build": memory_after_build,
               "index": {**index.stats(), "full_text_bytes_in_memory": pages * page_size},
               "search_lexical": timed_search("lexical"), "search_hybrid": timed_search("hybrid"),
               "search_lexical_with_filter": timed_search("lexical", filters={"tier": {"equals": "community"}})
               if "tier" in index.stats()["filterable_attributes"] else None,
               "search_lexical_client_declares_no_effects": timed_search("lexical", authority=())}
    samples = []
    for _ in range(repetitions):
        started = time.perf_counter()
        listed = listing()
        samples.append((time.perf_counter() - started) * 1000)
    ordered = sorted(samples)
    results["listing"] = {"samples": len(samples), "p50_ms": round(statistics.median(samples), 2),
                          "p95_ms": round(percentile(ordered, 0.95), 2), "max_ms": round(ordered[-1], 2),
                          "items_offered": len(listed["items"]), "items_withheld": len(listed["withheld"]),
                          "response_bytes": len(json.dumps(listed, separators=(",", ":"))),
                          "items_offered_when_no_effect_is_declared": len(listing(())["items"])}
    results["memory_after_searches"] = memory_now()
    refresher = CatalogueRefresher(
        binding, build=lambda current, token: next_view(current, token, config, settings,
                                                        license_policy=license_policy, family_policy=family_policy),
        probe=lambda: state_token(config), interval_seconds=5)
    results["second_publish"] = _run([sys.executable, __file__, "--phase", PUBLISH_SECOND_PHASE, "--root", str(root),
                                      *_license_arguments(accepted_licenses)])
    started = time.perf_counter()
    swapped = refresher.check_once()
    results["hot_swap"] = {"seconds": round(time.perf_counter() - started, 3), "changed": swapped.get("changed"),
                           "failure": swapped.get("failure"),
                           "release_is_second": binding.current_view().release_id
                           == results["second_publish"]["release_id"],
                           "items_in_view": len(binding.current_view().catalogue.items),
                           "memory_after_swap": memory_now()}
    results["search_hybrid_after_swap"] = latencies(search("hybrid"), queries[:20])
    results["store_after_second_release"] = store_sizes(root)
    return results


def trace(root, accepted_licenses):
    """Build the view of the active release under tracemalloc, in a process of its own."""
    from loop_engine.core.service_runtime.catalogue_serving import store_view
    license_policy, family_policy = policies(accepted_licenses)
    config, _context, settings = service(root)
    tracemalloc.start()
    started = time.perf_counter()
    view = store_view(config, settings, license_policy=license_policy, family_policy=family_policy)
    seconds = round(time.perf_counter() - started, 3)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {"tracemalloc_peak_bytes": peak, "tracemalloc_bytes_after_build": current,
            "view_build_seconds_under_tracing": seconds, "items_in_view": len(view.catalogue.items),
            "memory": memory_now(),
            "note": "tracemalloc counts Python allocations only; the full-text table lives in SQLite outside it, "
                    "and tracing slows the build and raises this process's resident memory"}


def _license_arguments(accepted_licenses):
    return [argument for name in accepted_licenses for argument in ("--accept-license", name)]


def _run(arguments):
    completed = subprocess.run(arguments, capture_output=True, text=True)
    if completed.returncode != 0:
        raise MeasurementRefused("phase_failed", completed.stderr.strip()[-2000:])
    return json.loads(completed.stdout)


def measure(bundle, root, *, factors=DEFAULT_FACTORS, queries=DEFAULT_QUERIES, repetitions=DEFAULT_REPETITIONS,
            accepted_licenses=LIVE_ACCEPTED_LICENSES, seed=DEFAULT_SEED):
    """Run every phase for every factor and return the measurement record."""
    bundle, root = Path(bundle).resolve(), Path(root).resolve()
    refusal = bundle_refusal(bundle) or root_refusal(root, bundle)
    if refusal:
        raise MeasurementRefused(refusal)
    if any(type(factor) is not int or factor < 1 for factor in factors) or len(set(factors)) != len(factors):
        raise MeasurementRefused("factors_invalid", "each factor is a distinct whole number of one or more")
    root.mkdir(parents=True, exist_ok=True)
    header = json.loads((bundle / "bundle.json").read_text("utf-8"))
    rows = load_rows(bundle)
    query_list = build_queries(rows, queries, seed)
    (root / "queries.json").write_text(json.dumps(query_list), encoding="utf-8")
    licenses = _license_arguments(accepted_licenses)
    sizes = []
    for factor in factors:
        folder = root / f"size-{factor}x"
        run = [sys.executable, __file__, "--bundle", str(bundle), "--root", str(folder), "--factor", str(factor),
               "--queries-file", str(root / "queries.json"), "--repetitions", str(repetitions), *licenses]
        prepared = _run([*run, "--phase", PREPARE_PHASE])
        # The traced build comes first, so it builds the first release, before `serve` swaps in the second.
        traced = _run([*run, "--phase", TRACE_PHASE])
        served = _run([*run, "--phase", SERVE_PHASE])
        sizes.append({"factor": factor, "items": prepared["items"], "synthetic_items": prepared["synthetic_items"],
                      "prepare": prepared, "serve": served, "trace": traced})
    return {"record_type": RESULT_RECORD_TYPE, "label": LABEL,
            "measured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "bundle": {"folder": str(bundle), "items": header["items"], "items_digest": header["items_digest"],
                       "notes": header["notes"], "read_only": True},
            "accepted_licenses": list(accepted_licenses), "machine": machine(),
            "queries": {"count": len(query_list), "seed": seed, "words_from": "the purposes of the real items",
                        "top_n": 10, "list": query_list},
            "second_release": {"changed_items": SECOND_RELEASE_CHANGED, "added_synthetic_items": SECOND_RELEASE_NEW},
            "sizes": sizes}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--bundle", type=Path, help="The release bundle folder; it is only read.")
    parser.add_argument("--root", type=Path, required=True,
                        help="An empty or absent scratch folder outside the repository and outside /data.")
    parser.add_argument("--factors", type=int, nargs="+", default=list(DEFAULT_FACTORS),
                        help="Library sizes as multiples of the bundle: 1 is the real bundle, 2 doubles it.")
    parser.add_argument("--queries", type=int, default=DEFAULT_QUERIES)
    parser.add_argument("--repetitions", type=int, default=DEFAULT_REPETITIONS, help="Listing samples.")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--accept-license", action="append", dest="accepted_licenses",
                        help="A licence the measured host accepts; repeatable. Default: the live host's list.")
    parser.add_argument("--output", type=Path, help="Where to write the JSON record; it is also printed.")
    parser.add_argument("--phase", choices=PHASES, default=ALL_PHASE)
    parser.add_argument("--factor", type=int, default=1, help="prepare: the multiple this size folder holds.")
    parser.add_argument("--queries-file", type=Path, help="serve: the queries the orchestrator chose.")
    options = parser.parse_args(argv)
    accepted = tuple(options.accepted_licenses or LIVE_ACCEPTED_LICENSES)
    root = options.root.resolve()
    bundle = options.bundle.resolve() if options.bundle is not None else None
    if options.phase in (ALL_PHASE, PREPARE_PHASE):
        # Both phases that write refuse before writing; `measure` checks again for the whole run.
        if bundle is None:
            parser.error("--bundle names the release bundle folder to measure")
        refusal = bundle_refusal(bundle) or root_refusal(root, bundle)
        if refusal:
            parser.exit(2, f"refused: {refusal}\n")
    if options.phase != ALL_PHASE:
        if options.phase == PREPARE_PHASE:
            result = prepare(bundle, root, options.factor, accepted)
        elif options.phase == SERVE_PHASE:
            queries = json.loads(options.queries_file.read_text("utf-8"))
            result = serve(root, accepted, queries, options.repetitions)
        elif options.phase == TRACE_PHASE:
            result = trace(root, accepted)
        else:
            result = publish_second(root, accepted)
        print(json.dumps(result))
        return 0
    try:
        record = measure(bundle, root, factors=tuple(options.factors), queries=options.queries,
                         repetitions=options.repetitions, accepted_licenses=accepted, seed=options.seed)
    except MeasurementRefused as refused:
        parser.exit(2, f"refused: {refused}\n")
    rendered = json.dumps(record, indent=1)
    if options.output is not None:
        options.output.parent.mkdir(parents=True, exist_ok=True)
        options.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
