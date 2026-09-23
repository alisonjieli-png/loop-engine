"""Offline metadata-only probe for the hosted catalogue's present search shape.

No body files are generated, no catalogue is modified, and no service or model
is contacted. Run each search tier in its own process so RSS is comparable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import resource
import time


RECORD_TYPE = "host_attested_intelligence_manifest/v1"
ROOT = "/opt/baltor/catalogue"
PATH_KINDS = (
    ("skill", "skills/{identity}/SKILL.md"),
    ("tool", "tools/{identity}.py"),
    ("instruction_file", "instructions/{identity}/AGENTS.md"),
    ("instruction_file", "instructions/{identity}/CODEX.md"),
    ("tool", "agents/{identity}.yaml"),
    ("tool", "plugins/{identity}.json"),
    ("tool", "protocol/{identity}.json"),
)


def row(index: int) -> dict:
    identity = f"synthetic_task_{index:06d}"
    kind, path = PATH_KINDS[index % len(PATH_KINDS)]
    path = path.format(identity=identity)
    purpose = (f"Synthetic metadata for task{index:06d}: validate inputs, "
               "handle errors, and record acceptance for a harness step.")
    return {"reference": {
        "record_type": "harness_intelligence_item/v1",
        "identity": identity, "kind": kind, "purpose": purpose,
        # A deterministic placeholder for sizing only. No body exists.
        "digest": hashlib.sha256(identity.encode()).hexdigest(),
        "source_layer": "harness_local", "source_ref": f"synthetic-probe/{path}",
        "family": "harness", "size_bytes": 2048, "license": "MIT",
        "declared_effects": [], "styles": [],
        "tags": {"record_type": "intelligence_tags/v1", "lifecycle": ["candidate"],
                 "language": ["en"]},
        "exposure": "metadata_only", "availability": "remote", "body_included": False,
    }, "body_path": path, "approval_ref": f"synthetic-probe-only/{identity}",
        "grants": [{"tenant_id": "synthetic-tenant", "body_allowed": True,
                    "metering": "required"}]}


class Rows(list):
    """A JSON-encodable list that streams rows without retaining 100k objects."""

    def __init__(self, count: int, make=row):
        self.count = count
        self.make = make

    def __len__(self):
        return self.count

    def __iter__(self):
        return (self.make(index) for index in range(self.count))


class ByteCounter:
    def __init__(self):
        self.size = 0

    def write(self, value: str):
        self.size += len(value.encode("utf-8"))


def status_kib(field: str) -> int:
    with open("/proc/self/status", encoding="ascii") as handle:
        for line in handle:
            if line.startswith(field + ":"):
                return int(line.split()[1])
    raise RuntimeError(f"Linux {field} unavailable")


def rss_kib() -> int:
    return status_kib("VmRSS")


def manifest_size(count: int) -> dict:
    started = time.perf_counter()
    counter = ByteCounter()
    json.dump({"record_type": RECORD_TYPE, "artifact_root": ROOT,
               "items": Rows(count)}, counter, indent=2, ensure_ascii=False)
    counter.write("\n")
    return {"count": count, "manifest_bytes": counter.size,
            "manifest_seconds": round(time.perf_counter() - started, 4),
            "over_host_limit_bytes": max(0, counter.size - 2_000_000)}


def served_row(index: int) -> dict:
    return {**row(index)["reference"], "qualification_basis": "host_attested",
            "metering_policy": "required", "body_allowed": True}


def grant_row(index: int) -> dict:
    ref = row(index)["reference"]
    return {"tenant_id": "synthetic-tenant", "binding": {
        "identity": ref["identity"], "source_layer": ref["source_layer"],
        "source_ref": ref["source_ref"], "body_digest": ref["digest"],
        "descriptor_digest": hashlib.sha256(("descriptor/" + ref["identity"]).encode()).hexdigest(),
        "record_type": "provisioning_item_binding/v1"},
        "body_allowed": True, "metering": "required",
        "record_type": "provisioning_grant/v1"}


def payload_sizes(count: int) -> dict:
    listing = ByteCounter()
    json.dump({"record_type": "provisioning_list/v2", "tenant_id": "synthetic-tenant",
               "entitlement": "bodies", "items": Rows(count, served_row), "withheld": [],
               "metered": False}, listing, ensure_ascii=False, separators=(",", ":"))
    grants = ByteCounter()
    json.dump({"record_type": "service_grants/v1", "tenant_id": "synthetic-tenant",
               "grants": Rows(count, grant_row)}, grants, ensure_ascii=False,
              separators=(",", ":"), sort_keys=True)
    return {"count": count, "bare_list_result_bytes": listing.size,
            "over_http_response_limit_bytes": max(0, listing.size - 262_144),
            "single_tenant_grant_payload_bytes": grants.size}


def search_probe(count: int, engine: str, limit_mb: int) -> dict:
    if limit_mb:
        ceiling = limit_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (ceiling, ceiling))
    from loop_engine.core.retrieval import Retriever, SqliteFtsBackend
    from loop_engine.core.store_serve import StoreRecord

    started = time.perf_counter()
    records = []
    for index in range(count):
        ref = row(index)["reference"]
        identity = ref["identity"]
        records.append(StoreRecord(identity, "context", ref["purpose"],
            body={"description": ref["purpose"],
                  "keywords": [identity, ref["kind"], ref["source_layer"]]}))
    prepared = time.perf_counter()
    prepared_rss = rss_kib()
    backend = SqliteFtsBackend(records) if engine == "fts5_only" else Retriever(records)
    built = time.perf_counter()
    built_rss = rss_kib()
    query = f"task{count // 2:06d}"
    queried = time.perf_counter()
    result = backend.search(query, 10) if engine == "fts5_only" else backend.search(
        query, mode="lexical", top_n=10)
    finished = time.perf_counter()
    hits = result if engine == "fts5_only" else result["hits"]
    first_id = (hits[0][0] if engine == "fts5_only" else hits[0]["record_id"]) if hits else None
    return {"count": count, "engine": engine, "query": query,
            "record_build_seconds": round(prepared - started, 4),
            "index_build_seconds": round(built - prepared, 4),
            "query_seconds": round(finished - queried, 4),
            "rss_kib_after_records": prepared_rss, "rss_kib_after_index": built_rss,
            "rss_kib_after_query": rss_kib(),
            "peak_rss_kib": status_kib("VmHWM"),
            "hits": len(hits), "first_id": first_id,
            "expected_first_id": f"synthetic_task_{count // 2:06d}",
            "address_space_limit_mb": limit_mb}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("manifest", "payloads", "search"))
    parser.add_argument("--count", type=int, choices=(1000, 10000, 100000))
    parser.add_argument("--engine", choices=("fts5_only", "retriever"))
    parser.add_argument("--address-space-limit-mb", type=int, default=3072)
    args = parser.parse_args()
    if args.mode == "manifest":
        output = {"record_type": "synthetic_manifest_size_probe/v1",
                  "results": [manifest_size(count) for count in (1000, 10000, 100000)]}
    elif args.mode == "payloads":
        output = {"record_type": "synthetic_payload_size_probe/v1",
                  "results": [payload_sizes(count) for count in (1000, 10000, 100000)]}
    else:
        if args.count is None or args.engine is None:
            parser.error("search requires --count and --engine")
        output = {"record_type": "synthetic_search_probe/v1",
                  **search_probe(args.count, args.engine, args.address_space_limit_mb)}
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    main()
