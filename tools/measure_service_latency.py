"""Bounded read-only timing from this workstation to an explicitly named service.

No body downloads, provider calls, credential printing or load generation.
The report retains every sample, including failures and connection setup.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import http.client
import json
import math
from pathlib import Path
import ssl
import time
from urllib.parse import urlsplit


@dataclass(frozen=True)
class MeasurementProfile:
    name: str
    path: str
    authenticated: bool = False
    body: dict | None = None


def validated_origin(value: str) -> str:
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
            or parsed.port not in (None, 443) or parsed.path or parsed.query or parsed.fragment
            or value != "https://" + parsed.netloc):
        raise ValueError("An exact HTTPS origin without a path or credentials is required")
    return parsed.hostname


def percentile(values: list[float], fraction: float) -> float | None:
    """Nearest-rank percentile, without pretending an empty sample is zero."""
    return sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)] if values else None


def summarize(samples: list[dict]) -> dict:
    good = [row["total_ms"] for row in samples if row["ok"]]
    warm = [row["total_ms"] for row in samples if row["ok"] and not row["new_connection"]]
    return {"attempted": len(samples), "successful": len(good),
            "failed": len(samples) - len(good), "successful_p50_ms": percentile(good, .50),
            "successful_p95_ms": percentile(good, .95), "successful_max_ms": max(good) if good else None,
            "reused_connection_successful_p50_ms": percentile(warm, .50),
            "reused_connection_successful_p95_ms": percentile(warm, .95)}


def measure(host: str, profile: MeasurementProfile, count: int, interval: float, token: str | None) -> list[dict]:
    rows, connection = [], None
    for index in range(count):
        is_new = connection is None
        if is_new:
            connection = http.client.HTTPSConnection(host, timeout=20, context=ssl.create_default_context())
        headers = {"Accept": "application/json" if profile.path.startswith("/api/") else "*/*"}
        if profile.authenticated:
            if not token:
                raise ValueError("Missing declared credential")
            headers["Authorization"] = "Bearer " + token
        body = json.dumps(profile.body).encode() if profile.body is not None else None
        if body is not None:
            headers["Content-Type"] = "application/json"
        row = {"sample": index + 1, "new_connection": is_new, "ok": False, "status": None,
               "header_ms": None, "total_ms": None, "response_bytes": None, "error": None}
        started = time.perf_counter()
        try:
            connection.request("POST" if body is not None else "GET", profile.path, body, headers)
            response = connection.getresponse()
            row["header_ms"] = round((time.perf_counter() - started) * 1000, 3)
            data = response.read(512_001)
            row["total_ms"] = round((time.perf_counter() - started) * 1000, 3)
            row["status"], row["response_bytes"] = response.status, len(data)
            row["ok"] = response.status == 200 and len(data) <= 512_000
            if len(data) > 512_000:
                row["error"] = "response_size_exceeded"
            elif response.status != 200:
                row["error"] = "http_status"
            elif profile.path.startswith("/api/"):
                result = json.loads(data)["result"]
                if profile.path.endswith("retrieval"):
                    row["returned_references"] = len(result["hits"])
                    row["bodies_loaded"] = result["bodies_loaded"]
                    row["ok"] = result["bodies_loaded"] is False
                elif profile.path.endswith("provisioning"):
                    row["permitted_items"] = len(result["items"])
            if response.will_close or not row["ok"]:
                connection.close(); connection = None
        except Exception as error:
            row["ok"] = False
            row["total_ms"] = round((time.perf_counter() - started) * 1000, 3)
            row["error"] = type(error).__name__  # Never save remote bodies or exception details.
            connection.close(); connection = None
        rows.append(row)
        if index + 1 < count:
            time.sleep(interval)
    if connection is not None:
        connection.close()
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--account", help="Optional named system-keyring service-access credential")
    parser.add_argument("--query", default="review inputs")
    parser.add_argument("--samples", type=int, default=12)
    parser.add_argument("--interval", type=float, default=.25)
    parser.add_argument("--authorize-read-only-measurement", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        host = validated_origin(args.origin)
    except ValueError as error:
        parser.error(str(error))
    if (not args.authorize_read_only_measurement or not 3 <= args.samples <= 20
            or not math.isfinite(args.interval) or not .2 <= args.interval <= 2
            or not 1 <= len(args.query) <= 4096 or args.output.exists()):
        parser.error("Explicit read-only authority, 3..20 samples, .2..2 second interval and a new report are required")
    profiles = [MeasurementProfile("homepage", "/"), MeasurementProfile("javascript", "/assets/service.js"),
                MeasurementProfile("health", "/api/v1/health"), MeasurementProfile("capabilities", "/api/v1/capabilities")]
    token = None
    if args.account:
        import secretstorage
        collection = secretstorage.get_default_collection(secretstorage.dbus_init())
        items = list(collection.search_items({"application": "loop-engine", "service": host,
                                             "account": args.account, "purpose": "service-access"}))
        if len(items) != 1:
            raise RuntimeError("Named service credential unavailable")
        token = items[0].get_secret().decode()
        profiles.append(MeasurementProfile("permitted_catalogue", "/api/v1/provisioning", True,
                                          {"record_type": "service_provisioning_request/v1", "operation": "list"}))
        for mode in ("lexical", "hybrid"):
            profiles.append(MeasurementProfile(mode + "_retrieval", "/api/v1/retrieval", True,
                            {"record_type": "service_retrieval_request/v1", "query": args.query, "mode": mode, "top_n": 10}))
    report = {"record_type": "service_latency_report/v1", "observed_at": datetime.now(timezone.utc).isoformat(),
              "origin": args.origin, "vantage_point": "development_workstation", "authenticated": token is not None,
              "samples_per_profile": args.samples, "serial_concurrency": 1, "interval_seconds": args.interval,
              "maximum_requests": args.samples * len(profiles), "automatic_retries": 0,
              "query_sha256": hashlib.sha256(args.query.encode()).hexdigest(), "query_characters": len(args.query),
              "percentile_method": "nearest_rank_successful_samples_only",
              "limits": ["Network round trip and client processing, not isolated server execution time",
                         "New connections include name lookup and TLS setup; reused connections are reported separately",
                         "Small diagnostic catalogue; not a capacity, availability, geographic or competitor benchmark",
                         "No body downloads, model calls or external mutations"], "profiles": []}
    for profile in profiles:
        samples = measure(host, profile, args.samples, args.interval, token)
        result = {"name": profile.name, "path": profile.path, "samples": samples, "summary": summarize(samples)}
        report["profiles"].append(result)
        print(json.dumps({"profile": profile.name, **result["summary"]}), flush=True)
    report["all_requests_succeeded"] = all(row["summary"]["failed"] == 0 for row in report["profiles"])
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2); stream.write("\n")
    return 0 if report["all_requests_succeeded"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
