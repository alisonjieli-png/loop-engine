"""Operator tool for the edge website (static_content_network engine): export, load and measure.

```text
cloudflare_site_edge.py
├── export   render this checkout's website with static_site_export: the identity origin of the page headers and
│            the served population are read from the live service's public answers, so the pages equal what the
│            live service would send for this release
├── load     write one export into a prototype Worker's KV namespace in signed loads (production deploys the export
│            as Workers static assets from continuous integration instead)
└── measure  every exported page through the edge and through the origin on kept-alive connections: status, bytes
             equal to the export, the edge's mark, and latency percentiles for both
```

Network reads and writes happen only with --authorize-network, and only to the addresses given.
"""
from __future__ import annotations

import argparse
import http.client
import json
from pathlib import Path
import re
import statistics
import sys
import time
import urllib.parse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from loop_engine.core.service_runtime import static_site_export as site  # noqa: E402
from loop_engine.core.service_runtime.catalogue_d1_index import USER_AGENT, RequestSigner  # noqa: E402

MEASUREMENT_RECORD_TYPE = "site_edge_measurement/v1"
_SUPABASE = re.compile(r"connect-src 'self' (https://[a-z0-9-]+\.supabase\.co)")


class Client:
    """One kept-alive HTTPS connection with a named user agent: a library's default one meets error 1010."""

    def __init__(self, origin):
        parsed = urllib.parse.urlsplit(origin)
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
                or parsed.path not in ("", "/") or parsed.query or parsed.fragment):
            raise ValueError("an exact HTTPS origin without credentials is required")
        self.host = parsed.hostname
        self.connection = http.client.HTTPSConnection(parsed.hostname, parsed.port or 443, timeout=60)

    def request(self, method, path, body=None, headers=None):
        sent = {"User-Agent": USER_AGENT, "Accept": "text/html,application/json;q=0.9,*/*;q=0.8", **(headers or {})}
        attempts = 2 if method in ("GET", "HEAD") else 1
        for attempt in range(attempts):
            began = time.perf_counter()
            try:
                self.connection.request(method, path, body=body, headers=sent)
                response = self.connection.getresponse()
                self.first_byte_ms = (time.perf_counter() - began) * 1000
                payload = response.read()
                return (response.status, {name.lower(): value for name, value in response.getheaders()}, payload,
                        (time.perf_counter() - began) * 1000)
            except (http.client.HTTPException, OSError):
                self.connection.close()
                if attempt + 1 == attempts:
                    raise


def live_values(origin):
    """The identity origin the live page headers name and the population the live service serves."""
    client = Client(origin)
    status, headers, _body, _ms = client.request("GET", "/pricing")
    if status != 200:
        raise ValueError("the origin page could not be read")
    match = _SUPABASE.search(headers.get("content-security-policy", ""))
    status, _headers, body, _ms = client.request("GET", "/api/v1/capabilities", headers={"Accept": "application/json"})
    if status != 200:
        raise ValueError("the origin capabilities could not be read")
    population = json.loads(body)["result"]["library"]["file_population"]
    if population.get("complete") is not True:
        raise ValueError("the export needs a complete served population")
    return (match.group(1) if match else ""), population


def export(out, *, origin, model_details):
    identity, population = live_values(origin)
    started = time.monotonic()
    exported = site.export_site(display_name="Baltor", identity_origin=identity, library_population=population,
                                include_model_details=model_details)
    site.write_export(exported, out)
    return {"record_type": "site_edge_export/v1", "export_id": exported.export_id,
            "addresses": len(exported.manifest["files"]), "files": len(exported.files),
            "bytes": sum(len(body) for body in exported.files.values()),
            "identity_origin_read": bool(identity), "packages": population.get("packages"),
            "seconds": round(time.monotonic() - started, 1)}


def read_export(folder):
    folder = Path(folder)
    manifest = json.loads((folder / "manifest.json").read_text())
    files = {path.name: path.read_bytes() for path in (folder / "files").iterdir()}
    return site.SiteExport(manifest, files)


def load(folder, worker, admin_key, *, batch_bytes=8_000_000):
    exported = read_export(folder)
    signer = RequestSigner.from_pem_file(admin_key)
    entries = site.kv_entries(exported)
    client, written, batch, size = Client(worker), 0, [], 0

    def send(group):
        payload = site.load_payload(exported.export_id, group)
        status, _headers, body, _ms = client.request(
            "POST", "/__edge/admin/files", payload,
            {"Authorization": signer.header("POST", "/__edge/admin/files", payload),
             "Content-Type": "application/octet-stream"})
        if status != 200:
            raise SystemExit(f"the load was refused with {status}: {body[:200]!r}")
        return json.loads(body)["written"]
    # The manifest goes last, so a reader never finds a manifest that names a file not yet written.
    manifest, files = entries[0], entries[1:]
    for entry in files + [manifest]:
        if batch and size + len(entry[1]) > batch_bytes:
            written += send(batch)
            batch, size = [], 0
        batch.append(entry)
        size += len(entry[1])
    if batch:
        written += send(batch)
    return {"record_type": "site_edge_load_report/v1", "export_id": exported.export_id, "written": written,
            "expected": len(entries)}


def _percentiles(values):
    ordered = sorted(values)
    if not ordered:
        return None
    pick = lambda share: round(ordered[max(0, min(len(ordered) - 1, int(round(share * (len(ordered) - 1)))))], 1)  # noqa: E731
    return {"p50": pick(0.5), "p95": pick(0.95), "mean": round(statistics.fmean(ordered), 1), "count": len(ordered)}


def measure(folder, worker, origin, *, rounds=3, pages_only=True):
    exported = read_export(folder)
    addresses = [address for address, entry in exported.manifest["files"].items()
                 if address != site.UNAVAILABLE_PAGE and (not pages_only or entry["media_type"].startswith("text/html"))]
    edge, source = Client(worker), Client(origin)
    edge.request("GET", "/__edge/status")
    source.request("GET", "/api/v1/health", headers={"Accept": "application/json"})
    edge_ms, origin_ms, mismatched, statuses, marks, origin_failures = [], [], [], {}, {}, []
    edge_first, origin_first = [], []
    for _round in range(rounds):
        for address in addresses:
            status, headers, body, elapsed = edge.request("GET", address)
            statuses[status] = statuses.get(status, 0) + 1
            marks[headers.get("x-baltor-edge", "").split(" ")[0]] = marks.get(headers.get("x-baltor-edge", "").split(" ")[0], 0) + 1
            edge_ms.append(elapsed)
            edge_first.append(edge.first_byte_ms)
            expected = exported.files[exported.manifest["files"][address]["sha256"]]
            if status != 200 or body != expected:
                mismatched.append(address)
            status, _headers, _body, elapsed = source.request("GET", address)
            if status != 200:
                origin_failures.append({"address": address, "status": status})
            origin_ms.append(elapsed)
            origin_first.append(source.first_byte_ms)
    return {"record_type": MEASUREMENT_RECORD_TYPE, "export_id": exported.export_id, "worker": worker,
            "origin": origin, "measured_at": int(time.time()), "rounds": rounds, "addresses": len(addresses),
            "edge_statuses": statuses, "edge_marks": marks, "edge_bodies_differing_from_the_export": sorted(set(mismatched)),
            "origin_failures": origin_failures[:20], "edge_ms": _percentiles(edge_ms), "origin_ms": _percentiles(origin_ms),
            "edge_first_byte_ms": _percentiles(edge_first), "origin_first_byte_ms": _percentiles(origin_first),
            "page_bytes": _percentiles([len(exported.files[exported.manifest["files"][a]["sha256"]]) for a in addresses])}


def outage(folder, worker, *, rounds=1):
    """Every exported page and three requests that need the origin, through an edge whose origin cannot answer."""
    exported = read_export(folder)
    addresses = [address for address, entry in exported.manifest["files"].items()
                 if address != site.UNAVAILABLE_PAGE and entry["media_type"].startswith("text/html")]
    edge, served, latencies = Client(worker), 0, []
    for _round in range(rounds):
        for address in addresses:
            status, _headers, body, elapsed = edge.request("GET", address)
            served += status == 200 and body == exported.files[exported.manifest["files"][address]["sha256"]]
            latencies.append(elapsed)
    answers = {}
    for path, accept in (("/api/v1/capabilities", "application/json"), ("/library", "text/html"),
                         ("/api/v1/health", "application/json")):
        status, headers, body, _ms = edge.request("GET", path, headers={"Accept": accept})
        answers[path] = {"status": status, "retry_after": headers.get("retry-after"),
                         "edge": headers.get("x-baltor-edge"),
                         "code": json.loads(body).get("error", {}).get("code") if accept == "application/json" and body else None}
    return {"record_type": "site_edge_outage_measurement/v1", "worker": worker, "pages": len(addresses) * rounds,
            "pages_served_exactly": served, "page_ms": _percentiles(latencies), "requests_needing_the_origin": answers}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    exporting = sub.add_parser("export")
    exporting.add_argument("--out", required=True)
    exporting.add_argument("--origin", required=True)
    exporting.add_argument("--without-model-details", action="store_true")
    loading = sub.add_parser("load")
    loading.add_argument("--export", required=True)
    loading.add_argument("--worker", required=True)
    loading.add_argument("--admin-key", required=True)
    measuring = sub.add_parser("measure")
    measuring.add_argument("--export", required=True)
    measuring.add_argument("--worker", required=True)
    measuring.add_argument("--origin", required=True)
    measuring.add_argument("--rounds", type=int, default=3)
    measuring.add_argument("--out", required=True)
    down = sub.add_parser("outage")
    down.add_argument("--export", required=True)
    down.add_argument("--worker", required=True)
    down.add_argument("--out", required=True)
    for command in (exporting, loading, measuring, down):
        command.add_argument("--authorize-network", action="store_true")
    args = parser.parse_args(argv)
    if not args.authorize_network:
        raise SystemExit("this command reads or writes over the network; pass --authorize-network")
    if args.command == "export":
        print(json.dumps(export(args.out, origin=args.origin, model_details=not args.without_model_details), indent=1))
    elif args.command == "load":
        print(json.dumps(load(args.export, args.worker, args.admin_key), indent=1))
    elif args.command == "measure":
        report = measure(args.export, args.worker, args.origin, rounds=args.rounds)
        Path(args.out).write_text(json.dumps(report, indent=1), "utf-8")
        print(json.dumps(report, indent=1))
    else:
        report = outage(args.export, args.worker)
        Path(args.out).write_text(json.dumps(report, indent=1), "utf-8")
        print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
