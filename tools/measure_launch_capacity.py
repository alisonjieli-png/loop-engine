"""Bounded, read-only launch capacity probe of public pages and public API reads.

tools/measure_service_latency.py times serial requests and generates no load on purpose. Before a launch the
question is different: how many concurrent visitors' requests the public routes serve, and where latency and
errors begin. This probe answers that within fixed bounds:

- GET only, on public paths that a signed-out visitor's browser requests anyway; no credential, cookie,
  body upload, download of a component body, model call or provider write.
- Concurrency steps up through --levels (default 1, 4, 8, 16), each for --seconds, and stops at the first level
  whose error share exceeds --stop-error-share or whose p95 exceeds --stop-p95-ms. A hard --maximum-requests
  bounds the whole run, and requests are spread over the configured paths in a fixed rotation.
- Every request is counted, failures included; percentiles use nearest rank over successful requests only and
  say so. The report states the vantage point: one workstation and one network path, so it measures this path's
  view of the service and its per-client limits, not global capacity.

Usage: python3 tools/measure_launch_capacity.py --origin https://baltor.ai --output REPORT.json \
         --authorize-read-only-load [--levels 1,4,8,16] [--seconds 15] [--path /api/v1/health ...]
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
import http.client
import json
import math
from pathlib import Path
import threading
import time
from urllib.parse import urlsplit

RECORD_TYPE = "launch_capacity_report/v1"
DEFAULT_PATHS = ("/", "/pricing", "/api/v1/capabilities", "/api/v1/health", "/api/v1/public-good")
USER_AGENT = "BaltorLaunchCapacityProbe/1 (+read-only; operator run)"
MAXIMUM_BODY_BYTES = 4 * 1024 * 1024


def validated_origin(value: str) -> tuple[str, int]:
    parsed = urlsplit(value)
    if (parsed.scheme not in ("https", "http") or not parsed.hostname or parsed.username or parsed.password
            or parsed.path or parsed.query or parsed.fragment):
        raise ValueError("An exact origin without a path, query or credentials is required")
    if parsed.scheme == "http" and parsed.hostname not in ("127.0.0.1", "localhost"):
        raise ValueError("Plain HTTP is accepted only for a local test server")
    return parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80)


def percentile(values: list[float], fraction: float) -> float | None:
    return round(sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)], 1) if values else None


class Probe:
    def __init__(self, origin: str, paths: tuple[str, ...], timeout: float = 20.0):
        self.origin = origin.rstrip("/")
        self.scheme = urlsplit(origin).scheme
        self.host, self.port = validated_origin(self.origin)
        for path in paths:
            if not path.startswith("/") or "://" in path or any(ch in path for ch in "\r\n "):
                raise ValueError("A path must be an absolute path on the origin")
        self.paths, self.timeout = paths, timeout
        self.local = threading.local()

    def _connection(self):
        connection = getattr(self.local, "connection", None)
        if connection is None:
            factory = http.client.HTTPSConnection if self.scheme == "https" else http.client.HTTPConnection
            connection = factory(self.host, self.port, timeout=self.timeout)
            self.local.connection = connection
        return connection

    def close(self):
        connection = getattr(self.local, "connection", None)
        if connection is not None:
            connection.close()
            self.local.connection = None

    def get(self, path: str) -> dict:
        started = time.perf_counter()
        try:
            connection = self._connection()
            connection.request("GET", path, headers={"User-Agent": USER_AGENT, "Accept": "*/*",
                                                     "Accept-Encoding": "gzip"})
            response = connection.getresponse()
            body = response.read(MAXIMUM_BODY_BYTES + 1)
            elapsed = (time.perf_counter() - started) * 1000
            if response.getheader("Connection", "").lower() == "close":
                connection.close()
                self.local.connection = None
            return {"path": path, "status": response.status, "ms": round(elapsed, 1), "bytes": len(body),
                    "error": None, "ok": 200 <= response.status < 400}
        except (OSError, http.client.HTTPException) as error:
            try:
                self.local.connection.close()
            except Exception:  # noqa: BLE001
                pass
            self.local.connection = None
            return {"path": path, "status": None, "ms": round((time.perf_counter() - started) * 1000, 1),
                    "bytes": 0, "error": type(error).__name__, "ok": False}


def run_level(probe: Probe, concurrency: int, seconds: float, budget: int, offset: int) -> list[dict]:
    """Keep `concurrency` workers busy for `seconds`, never sending more than `budget` requests."""
    results, lock = [], threading.Lock()
    counter = {"sent": 0}
    deadline = time.monotonic() + seconds

    def worker():
        try:
            while time.monotonic() < deadline:
                with lock:
                    if counter["sent"] >= budget:
                        return
                    index = offset + counter["sent"]
                    counter["sent"] += 1
                result = probe.get(probe.paths[index % len(probe.paths)])
                with lock:
                    results.append(result)
        finally:
            probe.close()

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        for _ in range(concurrency):
            pool.submit(worker)
    return results


def summarize(results: list[dict], seconds: float) -> dict:
    ok = [row["ms"] for row in results if row["ok"]]
    statuses: dict[str, int] = {}
    for row in results:
        key = str(row["status"]) if row["status"] is not None else "error:" + str(row["error"])
        statuses[key] = statuses.get(key, 0) + 1
    by_path = {}
    for path in sorted({row["path"] for row in results}):
        rows = [row for row in results if row["path"] == path]
        good = [row["ms"] for row in rows if row["ok"]]
        by_path[path] = {"requests": len(rows), "ok": len(good), "p50_ms": percentile(good, .5),
                         "p95_ms": percentile(good, .95)}
    return {"requests": len(results), "ok": len(ok), "error_share": round(1 - len(ok) / len(results), 4)
            if results else None, "throughput_per_second": round(len(results) / seconds, 2),
            "p50_ms": percentile(ok, .5), "p95_ms": percentile(ok, .95), "p99_ms": percentile(ok, .99),
            "max_ms": round(max(ok), 1) if ok else None, "statuses": statuses, "by_path": by_path}


def measure(probe: Probe, levels: list[int], seconds: float, maximum_requests: int, stop_error_share: float,
            stop_p95_ms: float) -> dict:
    report = {"record_type": RECORD_TYPE, "origin": probe.origin, "paths": list(probe.paths),
              "started_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
              "vantage_point": "one operator workstation and network path",
              "method": "GET only; keep-alive connection per worker; fixed path rotation",
              "percentile_method": "nearest_rank_successful_requests_only",
              "bounds": {"levels": levels, "seconds_per_level": seconds, "maximum_requests": maximum_requests,
                         "stop_error_share": stop_error_share, "stop_p95_ms": stop_p95_ms},
              "levels": [], "stopped_early": False, "stop_reason": None}
    sent = 0
    for concurrency in levels:
        budget = maximum_requests - sent
        if budget <= 0:
            report.update(stopped_early=True, stop_reason="maximum_requests_reached")
            break
        started = time.monotonic()
        results = run_level(probe, concurrency, seconds, budget, sent)
        elapsed = max(time.monotonic() - started, 1e-6)
        sent += len(results)
        summary = {"concurrency": concurrency, "seconds": round(elapsed, 2), **summarize(results, elapsed)}
        report["levels"].append(summary)
        if summary["error_share"] is not None and summary["error_share"] > stop_error_share:
            report.update(stopped_early=True, stop_reason=f"error_share_above_{stop_error_share}")
            break
        if summary["p95_ms"] is not None and summary["p95_ms"] > stop_p95_ms:
            report.update(stopped_early=True, stop_reason=f"p95_above_{stop_p95_ms}_ms")
            break
    report["requests_sent"] = sent
    report["finished_at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--origin", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--path", action="append", help="Public path to include; repeat. Default: " +
                        ", ".join(DEFAULT_PATHS))
    parser.add_argument("--levels", default="1,4,8,16")
    parser.add_argument("--seconds", type=float, default=15.0)
    parser.add_argument("--maximum-requests", type=int, default=2500)
    parser.add_argument("--stop-error-share", type=float, default=0.05)
    parser.add_argument("--stop-p95-ms", type=float, default=3000.0)
    parser.add_argument("--authorize-read-only-load", action="store_true")
    options = parser.parse_args(argv)
    levels = [int(value) for value in options.levels.split(",") if value.strip()]
    if not levels or any(not 1 <= level <= 32 for level in levels) or levels != sorted(levels):
        parser.error("levels are ascending integers from 1 to 32")
    if not 1 <= options.seconds <= 60 or not 1 <= options.maximum_requests <= 10000:
        parser.error("each level lasts 1 to 60 seconds and a run sends at most 10,000 requests")
    if options.output.exists():
        parser.error("the report path exists; reports are never overwritten")
    try:
        probe = Probe(options.origin, tuple(options.path or DEFAULT_PATHS))
    except ValueError as error:
        parser.error(str(error))
    if not options.authorize_read_only_load:
        print(json.dumps({"dry_run": True, "origin": probe.origin, "paths": list(probe.paths), "levels": levels,
                          "seconds_per_level": options.seconds, "maximum_requests": options.maximum_requests}))
        return 0
    report = measure(probe, levels, options.seconds, options.maximum_requests, options.stop_error_share,
                     options.stop_p95_ms)
    with options.output.open("x") as stream:
        json.dump(report, stream, indent=1)
        stream.write("\n")
    print(json.dumps({level["concurrency"]: {k: level[k] for k in ("throughput_per_second", "p50_ms", "p95_ms",
                                                                  "error_share")} for level in report["levels"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
