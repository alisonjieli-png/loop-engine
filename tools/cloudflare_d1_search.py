"""Operator tool for engine (d) of the catalogue search index slot: export, load and measure a D1 edge index.

```text
cloudflare_d1_search.py
├── keys     make an Ed25519 key pair for signing requests; the private key stays in a 0600 file, the public
│            key entry is printed for the Worker's KEYS binding (no secret ever leaves this machine)
├── export   read a catalogue bundle the way the service reads it (licence and family policy included), keep the
│            whole release or a deterministic sample, and write index.sql, build.json, entries.json and the 512
│            vector columns, with the account profile of the Worker's retrieval route
├── vectors  upload the vector columns to a deployed Worker in signed admin requests (one KV write a column)
└── measure  run the judged requests of examples/30_search_quality against the Worker and against the in-memory
             engine over the same entries: exact pool and answer comparison, judged recall, latency percentiles,
             and the rows D1 reports reading
```

The D1 import itself is the provider's import API (init, upload to the address it returns, ingest, poll) and the
Worker upload is the scripts API; docs/architecture/CLOUDFLARE-HOSTING-2026-10-05.md lists the calls. This tool
makes network requests only to the Worker origin it is given, and only with `--authorize-network`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
for folder in (ROOT / "src", ROOT / "examples" / "30_search_quality"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

from loop_engine.core.service_runtime import catalogue_d1_index as d1  # noqa: E402

#: The licences the live host accepts (`/data/host.json` license_policy, October 5, 2026).
LIVE_LICENSES = ("MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "CC0-1.0", "CC-BY-4.0",
                 "MIT AND BSD-2-Clause", "Apache-2.0 AND MIT", "BSD-2-Clause AND MIT", "BSD-3-Clause AND MIT",
                 "CC-BY-4.0 AND MIT", "CC0-1.0 AND MIT", "ISC AND MIT", "MIT AND Apache-2.0", "MIT AND BSD-3-Clause",
                 "MIT AND BSD-3-Clause AND Apache-2.0", "MIT AND CC-BY-4.0", "MIT AND CC0-1.0", "MIT AND ISC")
MEASUREMENT_RECORD_TYPE = "catalogue_d1_index_measurement/v1"


def make_keys(folder):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    os.chmod(folder, 0o700)
    entries = []
    for name, scopes in (("search", ["search"]), ("admin", ["admin"])):
        path = folder / f"edge-{name}-ed25519.pem"
        if path.exists():
            raise SystemExit(f"{path} exists; keys are never overwritten")
        key = Ed25519PrivateKey.generate()
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()))
        entries.append(d1.public_key_entry(d1.RequestSigner(key).public_key_raw, scopes))
    return entries


def read_live_bundle(folder):
    from loop_engine.core.service_runtime.catalogue_bundle import read_bundle
    from loop_engine.core.service_runtime.http_entrypoint import HostFamilyPolicy, HostLicensePolicy
    return read_bundle(Path(folder).resolve(), license_policy=HostLicensePolicy(LIVE_LICENSES),
                       family_policy=HostFamilyPolicy(), verify_blobs=False)


def sample_positions(bundle, size, keep):
    """Every identity in `keep` plus the identities with the lowest SHA-256 until `size`: the same every run."""
    identities = [item.identity for item in bundle.items]
    if size is None or size >= len(identities):
        return set(identities)
    chosen = {identity for identity in identities if identity in keep}
    ranked = sorted((hashlib.sha256(identity.encode()).hexdigest(), identity) for identity in identities
                    if identity not in chosen)
    chosen.update(identity for _digest, identity in ranked[:max(0, size - len(chosen))])
    return chosen


def judged_identities():
    judgements = json.loads((ROOT / "examples/30_search_quality/relevance-judgements.json").read_text())
    return {identity for row in judgements["judgements"] for identity in row.get("relevant", [])}


def export(bundle_folder, out, *, sample=None, release_id=None, content_digest=None):
    from dataclasses import replace
    bundle = read_live_bundle(bundle_folder)
    keep = sample_positions(bundle, sample, judged_identities())
    chosen = replace(bundle, items=tuple(item for item in bundle.items if item.identity in keep))
    entries, hits = d1.entries_from_bundle(chosen)
    reconciliation = Path(bundle_folder) / "reconciliation.json"
    stated = json.loads(reconciliation.read_text()) if reconciliation.exists() else {}
    release = release_id or stated.get("result_release") or "unpublished"
    digest = content_digest or stated.get("result_content_digest") or "0" * 64
    if sample is not None and len(entries) < len(bundle.items):
        release = f"{release}+sample{len(entries)}"
    profile = d1.edge_search_profile(release_id=release)
    started = time.monotonic()
    exported = d1.export_index(entries, chosen.schema, release_id=release, content_digest=digest, hits=hits,
                               profile=profile)
    out = Path(out)
    (out / "vectors").mkdir(parents=True, exist_ok=True)
    (out / "index.sql").write_text(exported.sql(), "utf-8")
    (out / "build.json").write_text(json.dumps(exported.build, indent=1, sort_keys=True), "utf-8")
    (out / "entries.json").write_text(json.dumps({"identities": [entry.identity for entry in entries]}), "utf-8")
    for dimension, column in enumerate(exported.columns):
        (out / "vectors" / f"{dimension:03d}.f32").write_bytes(column)
    summary = {"record_type": "catalogue_d1_index_export/v1", "build_id": exported.build_id,
               "release_id": release, "entries": len(entries), "of_bundle_items": len(bundle.items),
               "statements": len(exported.statements), "sql_bytes": len(exported.sql().encode()),
               "largest_statement_bytes": max(len(s.encode()) for s in exported.statements),
               "vector_bytes": sum(len(column) for column in exported.columns),
               "estimated_rows_written": len(entries) * 2 + len(exported.statements),
               "tiers": {tier: sum(1 for entry in entries if entry.tier == tier) for tier in ("verified", "community")},
               "seconds": round(time.monotonic() - started, 1)}
    (out / "export.json").write_text(json.dumps(summary, indent=1), "utf-8")
    return summary


def load_export(folder):
    """The export written by `export`, rebuilt from its own files for upload and measurement."""
    folder = Path(folder)
    build = json.loads((folder / "build.json").read_text())
    columns = tuple((folder / "vectors" / f"{dimension:03d}.f32").read_bytes() for dimension in range(d1.VECTOR_DIMENSIONS))
    if d1.vectors_digest(d1.column_digests(columns)) != build["vectors_digest"]:
        raise SystemExit("the vector columns differ from the build record")
    return d1.D1IndexExport(build, (), columns)


def upload_vectors(folder, worker, admin_key, *, batch=32):
    import urllib.request
    exported = load_export(folder)
    signer = d1.RequestSigner.from_pem_file(admin_key)
    written = []
    for start in range(0, d1.VECTOR_DIMENSIONS, batch):
        payload = d1.vector_upload_payload(exported, range(start, min(start + batch, d1.VECTOR_DIMENSIONS)))
        request = urllib.request.Request(worker.rstrip("/") + "/v1/admin/vectors", data=payload, method="POST",
                                         headers={"Authorization": signer.header("POST", "/v1/admin/vectors", payload),
                                                  "Content-Type": "application/octet-stream",
                                                  "User-Agent": d1.USER_AGENT})
        with urllib.request.urlopen(request, timeout=120) as response:
            written += json.loads(response.read())["written"]
    return {"record_type": "catalogue_d1_vector_upload_report/v1", "build_id": exported.build_id,
            "written": len(written), "complete": sorted(written) == list(range(d1.VECTOR_DIMENSIONS))}


def _percentile(values, share):
    ordered = sorted(values)
    if not ordered:
        return None
    index = max(0, min(len(ordered) - 1, int(round(share * (len(ordered) - 1)))))
    return round(ordered[index], 1)


def _metrics(ranked, judged):
    """Mean reciprocal rank and hits in the first ten over the answerable requests, as examples/30 scores them."""
    reciprocal, hits, answerable = 0.0, 0, 0
    for relevant, order in zip(judged, ranked):
        if not relevant:
            continue
        answerable += 1
        rank = next((position for position, identity in enumerate(order, 1) if identity in relevant), 0)
        reciprocal += 1.0 / rank if rank else 0.0
        hits += 1 if rank else 0
    return {"answerable": answerable, "mrr": round(reciprocal / answerable, 4) if answerable else None,
            "hit_at_10": round(hits / answerable, 4) if answerable else None}


def measure(folder, bundle_folder, worker, search_key, *, modes=("lexical", "hybrid"), limit=None, repeat=1,
            query_stride=1):
    """Judged requests through the Worker's retrieval route and through the in-memory engine, same entries.

    The in-memory side runs `catalogue_search.authorized_hits` with the authorization the Worker's account profile
    applies to a request that states no effects and no tiers: every item of the release, community included.
    Both sides answer the same top ten, so an exact engine shows no differing answer and equal judged metrics.
    """
    import http.client
    import urllib.parse
    from dataclasses import replace
    from loop_engine.core.service_runtime.catalogue_search import ReleaseSearchIndex, authorized_hits
    build = json.loads((Path(folder) / "build.json").read_text())
    origin = urllib.parse.urlsplit(worker)
    connection = http.client.HTTPSConnection(origin.hostname, origin.port or 443, timeout=60)

    def send(method, path, body=b""):
        """One request on the kept-alive connection: (status, body, server timing, rows read, milliseconds)."""
        headers = {"User-Agent": d1.USER_AGENT, "Accept": "application/json"}
        if path != "/v1/ping":
            headers["Authorization"] = signer.header(method, path, body)
        if body:
            headers["Content-Type"] = "application/json"
        began = time.perf_counter()
        for attempt in range(2):
            try:
                connection.request(method, path, body=body or None, headers=headers)
                response = connection.getresponse()
                answer = response.read()
                break
            except (http.client.HTTPException, OSError):
                connection.close()
                if attempt:
                    raise
                began = time.perf_counter()
        elapsed = (time.perf_counter() - began) * 1000
        return (response.status, answer, response.getheader("Server-Timing", ""),
                int(response.getheader("X-Baltor-Rows-Read", "0") or 0), elapsed)
    identities = set(json.loads((Path(folder) / "entries.json").read_text())["identities"])
    bundle = read_live_bundle(bundle_folder)
    chosen = replace(bundle, items=tuple(item for item in bundle.items if item.identity in identities))
    entries, _hits = d1.entries_from_bundle(chosen)
    started = time.monotonic()
    memory = ReleaseSearchIndex(entries, chosen.schema)
    build_seconds = time.monotonic() - started
    tiers = {entry.identity: entry.tier for entry in entries}

    class View:
        schema = chosen.schema

        @staticmethod
        def search_index():
            return memory

    def everything(candidates):
        return {identity: {"library_tier": tiers[identity]} for identity in candidates}
    data = json.loads((ROOT / "examples/30_search_quality/relevance-judgements.json").read_text())
    rows = data["judgements"][::query_stride][:limit]
    signer = d1.RequestSigner.from_pem_file(search_key)
    send("GET", "/v1/ping")
    pings = [send("GET", "/v1/ping")[4] for _ping in range(20)]
    report = {"record_type": MEASUREMENT_RECORD_TYPE, "build_id": build["build_id"], "release_id": build["release_id"],
              "entries": build["entries"], "worker": worker, "measured_at": int(time.time()), "repeat": repeat,
              "queries": len(rows), "query_stride": query_stride,
              "in_memory_build_seconds": round(build_seconds, 2),
              "network_round_trip_ms": {"p50": _percentile(pings, 0.5), "p95": _percentile(pings, 0.95),
                                        "route": "GET /v1/ping on one kept-alive TLS connection"},
              "modes": {}}
    for mode in modes:
        local_ms, edge_ms, server_ms, d1_ms, kv_ms, rows_read = [], [], [], [], [], []
        differing, failures, edge_orders, local_orders, kept = [], [], [], [], []
        for row in rows:
            fields = {"query": row["query"], "mode": mode, "top_n": 10}
            local = None
            for _attempt in range(repeat):
                began = time.perf_counter()
                local, _allowed = authorized_hits(View, dict(fields), everything)
                local_ms.append((time.perf_counter() - began) * 1000)
            payload = json.dumps({"record_type": "service_retrieval_request/v2", **fields}).encode()
            answer = None
            for _attempt in range(repeat):
                try:
                    status, body, timing, read_rows, elapsed = send("POST", "/api/v1/retrieval", payload)
                except (http.client.HTTPException, OSError) as error:
                    failures.append({"query": row["query"], "status": None, "code": type(error).__name__})
                    answer = None
                    break
                if status != 200:
                    try:
                        code = json.loads(body).get("error", {}).get("code")
                    except ValueError:
                        code = body[:120].decode("utf-8", "replace")
                    failures.append({"query": row["query"], "status": status, "code": code})
                    answer = None
                    break
                edge_ms.append(elapsed)
                parts = {}
                for part in timing.split(","):
                    if "dur=" in part:
                        parts[part.split(";")[0].strip()] = float(part.split("dur=")[1].split(";")[0])
                server_ms.append(parts.get("total", 0.0))
                d1_ms.append(parts.get("d1", 0.0))
                kv_ms.append(parts.get("kv", 0.0))
                rows_read.append(read_rows)
                answer = json.loads(body)
            if answer is None:
                continue
            edge_order = [(hit["reference"]["identity"], hit["score"], hit["modes"])
                          for hit in answer["result"]["hits"]]
            local_order = [(identity, score, list(modes)) for identity, score, modes in local]
            if edge_order != local_order:
                differing.append(row["query"])
            edge_orders.append([identity for identity, _score, _modes in edge_order])
            local_orders.append([identity for identity, _score, _modes in local_order])
            kept.append(row)
        judged = [frozenset(row.get("relevant", [])) for row in kept]
        report["modes"][mode] = {
            "requests": len(edge_ms), "failures": failures, "differing_answers": differing,
            "in_memory_ms": {"p50": _percentile(local_ms, 0.5), "p95": _percentile(local_ms, 0.95)},
            "edge_round_trip_ms": {"p50": _percentile(edge_ms, 0.5), "p95": _percentile(edge_ms, 0.95)},
            "edge_worker_ms": {"p50": _percentile(server_ms, 0.5), "p95": _percentile(server_ms, 0.95)},
            "edge_d1_ms": {"p50": _percentile(d1_ms, 0.5), "p95": _percentile(d1_ms, 0.95)},
            "edge_kv_ms": {"p50": _percentile(kv_ms, 0.5), "p95": _percentile(kv_ms, 0.95)},
            "rows_read": {"p50": _percentile(rows_read, 0.5), "p95": _percentile(rows_read, 0.95),
                          "total": sum(rows_read)},
            "judged_edge": _metrics(edge_orders, judged), "judged_in_memory": _metrics(local_orders, judged)}
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    keys = sub.add_parser("keys")
    keys.add_argument("--folder", required=True)
    exporting = sub.add_parser("export")
    exporting.add_argument("--bundle", required=True)
    exporting.add_argument("--out", required=True)
    exporting.add_argument("--sample", type=int)
    vectors = sub.add_parser("vectors")
    vectors.add_argument("--export", required=True)
    vectors.add_argument("--worker", required=True)
    vectors.add_argument("--admin-key", required=True)
    vectors.add_argument("--authorize-network", action="store_true")
    measuring = sub.add_parser("measure")
    measuring.add_argument("--export", required=True)
    measuring.add_argument("--bundle", required=True)
    measuring.add_argument("--worker", required=True)
    measuring.add_argument("--search-key", required=True)
    measuring.add_argument("--modes", default="lexical,hybrid")
    measuring.add_argument("--limit", type=int)
    measuring.add_argument("--stride", type=int, default=1)
    measuring.add_argument("--repeat", type=int, default=1)
    measuring.add_argument("--out", required=True)
    measuring.add_argument("--authorize-network", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "keys":
        print(json.dumps(make_keys(args.folder), indent=1))
    elif args.command == "export":
        print(json.dumps(export(args.bundle, args.out, sample=args.sample), indent=1))
    elif args.command == "vectors":
        if not args.authorize_network:
            raise SystemExit("uploading writes to the Worker's KV namespace; pass --authorize-network")
        print(json.dumps(upload_vectors(args.export, args.worker, args.admin_key), indent=1))
    else:
        if not args.authorize_network:
            raise SystemExit("measuring sends requests to the Worker; pass --authorize-network")
        report = measure(args.export, args.bundle, args.worker, args.search_key, modes=tuple(args.modes.split(",")),
                         limit=args.limit, repeat=args.repeat, query_stride=args.stride)
        Path(args.out).write_text(json.dumps(report, indent=1), "utf-8")
        print(json.dumps({mode: {key: value for key, value in result.items() if key != "differing_answers"}
                          for mode, result in report["modes"].items()}, indent=1))


if __name__ == "__main__":
    main()
