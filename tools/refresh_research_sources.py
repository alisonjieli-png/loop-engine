"""Validate a small primary-source watchlist and optionally check public changes.

Offline validation is the default. --online performs bounded, read-only HTTPS
requests. Every run creates a new report; no source claim is adopted from it.
"""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import re
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_TYPE = "research_source_watch_manifest/v1"
REPORT_TYPE = "research_source_watch_report/v1"
REPORT_PREFIX = "RESEARCH-SOURCE-WATCH-"
ID_PATTERN = re.compile(r"[a-z][a-z0-9_]{1,63}\Z")
ROADMAP_PATTERN = re.compile(r"S-\d+\.\d+\Z")
SHA_PATTERN = re.compile(r"[0-9a-f]{40}\Z")
HOST_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z")
REPO_PATH = re.compile(r"/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/?\Z")
MAX_MANIFEST_SOURCES = 50
MAX_ONLINE_SOURCES = 20
ALLOWED_PAGE_HOSTS = frozenset({"arxiv.org", "modelcontextprotocol.io",
                                 "agentplugins.io", "skills.sh",
                                 "jfrog.com"})


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _validate_url(value: Any, kind: str) -> None:
    if not isinstance(value, str) or len(value) > 500:
        raise ValueError("source URL must be a bounded HTTPS string")
    parsed = urlsplit(value)
    host = (parsed.hostname or "").lower()
    if (parsed.scheme != "https" or not host or parsed.username or parsed.password
            or parsed.port is not None or parsed.query or parsed.fragment
            or any(ord(char) > 127 for char in host)
            or len(host) > 253 or "." not in host
            or any(not HOST_LABEL.fullmatch(label) for label in host.split("."))
            or host.endswith((".local", ".internal", ".test", ".invalid"))):
        raise ValueError(f"unsupported source URL: {value}")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError(f"unsupported source URL: {value}")
    if kind == "github_repository":
        if host != "github.com" or not REPO_PATH.fullmatch(parsed.path):
            raise ValueError(f"unsupported GitHub repository URL: {value}")
        if any(part in (".", "..") for part in parsed.path.split("/")):
            raise ValueError(f"unsupported GitHub repository URL: {value}")
    elif kind == "web_page":
        # A bare domain such as https://agentplugins.io has no path; treat
        # the empty path as the site root, which still starts with "/".
        page_path = parsed.path or "/"
        if (host not in ALLOWED_PAGE_HOSTS or not page_path.startswith("/")
                or ".." in page_path.split("/")):
            raise ValueError(f"unsupported web page URL: {value}")
    else:
        raise ValueError(f"unsupported source kind: {kind}")


def validate_manifest(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, dict) or set(value) != {"record_type", "sources"}:
        raise ValueError("manifest fields are invalid")
    if value["record_type"] != MANIFEST_TYPE:
        raise ValueError("unsupported source watch manifest version")
    sources = value["sources"]
    if not isinstance(sources, list) or not 1 <= len(sources) <= MAX_MANIFEST_SOURCES:
        raise ValueError("manifest requires a bounded, nonempty source list")
    seen_ids: set[str] = set()
    seen_urls: set[str] = set()
    for row in sources:
        required = {"id", "name", "kind", "url", "roadmap_step", "license_state"}
        if not isinstance(row, dict) or not required <= set(row) or set(row) - required - {"baseline_revision", "note"}:
            raise ValueError("source fields are invalid")
        if "note" in row and (not isinstance(row["note"], str)
                              or not 1 <= len(row["note"].strip()) <= 1000):
            raise ValueError("source fields are invalid")
        if (not isinstance(row["id"], str) or not ID_PATTERN.fullmatch(row["id"])
                or not isinstance(row["name"], str) or not 1 <= len(row["name"].strip()) <= 160
                or not isinstance(row["roadmap_step"], str)
                or not ROADMAP_PATTERN.fullmatch(row["roadmap_step"])
                or not isinstance(row["license_state"], str)
                or not 1 <= len(row["license_state"].strip()) <= 160):
            raise ValueError("source identity, roadmap step or license state is invalid")
        _validate_url(row["url"], row["kind"])
        if row["id"] in seen_ids or row["url"] in seen_urls:
            raise ValueError("duplicate source ID or URL")
        seen_ids.add(row["id"])
        seen_urls.add(row["url"])
        if "baseline_revision" in row and (row["kind"] != "github_repository"
                                           or not isinstance(row["baseline_revision"], str)
                                           or not SHA_PATTERN.fullmatch(row["baseline_revision"])):
            raise ValueError("baseline revision must be an exact Git commit")
    return sources


def _request_url(source: dict[str, Any]) -> str:
    if source["kind"] == "web_page":
        return source["url"]
    path = urlsplit(source["url"]).path.strip("/")
    return f"https://api.github.com/repos/{path}/commits?per_page=1"


def _read_bounded(response: Any, max_bytes: int) -> bytes:
    body = response.read(max_bytes + 1)
    if len(body) > max_bytes:
        raise ValueError("response_too_large")
    return body


def _validator_header(value: Any) -> str | None:
    return value if isinstance(value, str) and len(value) <= 256 else None


def fetch_source(source: dict[str, Any], *, timeout_seconds: float,
                 max_bytes: int, opener: Any = None) -> dict[str, Any]:
    """Fetch a bounded public observation. Response bodies are never returned."""
    opener = opener or build_opener(ProxyHandler({}), _NoRedirect())
    request_url = _request_url(source)
    request = Request(request_url, headers={
        "User-Agent": "Loop-Engine-research-source-watch/1",
        "Accept": "application/vnd.github+json" if source["kind"] == "github_repository" else "text/html,*/*;q=0.1",
        "Accept-Encoding": "identity",
    }, method="GET")
    with opener.open(request, timeout=timeout_seconds) as response:
        body = _read_bounded(response, max_bytes)
        observed: dict[str, Any] = {
            "request_url": request_url,
            "etag": _validator_header(response.headers.get("ETag")),
            "last_modified": _validator_header(response.headers.get("Last-Modified")),
        }
        if source["kind"] == "github_repository":
            commits = json.loads(body)
            if (not isinstance(commits, list) or not commits
                    or not isinstance(commits[0], dict)
                    or not isinstance(commits[0].get("sha"), str)
                    or not SHA_PATTERN.fullmatch(commits[0]["sha"])):
                raise ValueError("invalid_repository_revision_response")
            observed["revision"] = commits[0]["sha"]
            observed["fingerprint"] = commits[0]["sha"]
        else:
            observed["content_sha256"] = hashlib.sha256(body).hexdigest()
            observed["fingerprint"] = observed["content_sha256"]
    return observed


def _failure(error: BaseException) -> dict[str, str]:
    if isinstance(error, HTTPError):
        return {"kind": "http_status", "detail": f"HTTP {error.code}"}
    if isinstance(error, (TimeoutError, socket.timeout)) or isinstance(getattr(error, "reason", None), TimeoutError):
        return {"kind": "timeout", "detail": "request timed out"}
    if isinstance(error, ValueError):
        return {"kind": "invalid_response", "detail": str(error)[:80]}
    if isinstance(error, URLError):
        return {"kind": "network_error", "detail": "network request failed"}
    return {"kind": "request_error", "detail": type(error).__name__}


def load_prior_observations(directory: Path) -> dict[tuple[str, str, str], tuple[str, str]]:
    """Find the latest successful observation for each unchanged source identity."""
    found: dict[tuple[str, str, str], tuple[str, str]] = {}
    for path in sorted(directory.glob(REPORT_PREFIX + "*.json"), reverse=True)[:1000]:
        try:
            report = json.loads(path.read_text("utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(report, dict) or report.get("record_type") != REPORT_TYPE:
            continue
        rows = report.get("sources")
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            observation = row.get("observed")
            if not isinstance(observation, dict) or not isinstance(observation.get("fingerprint"), str):
                continue
            key = (row.get("id"), row.get("kind"), row.get("url"))
            if all(isinstance(part, str) for part in key) and key not in found:
                found[key] = (observation["fingerprint"], path.name)
    return found


def run_watch(sources: list[dict[str, Any]], *, online: bool,
              prior: dict[tuple[str, str, str], tuple[str, str]] | None = None,
              timeout_seconds: float = 5.0, max_bytes: int = 512_000,
              max_online_sources: int = 12, opener: Any = None) -> dict[str, Any]:
    if not 0 < timeout_seconds <= 10 or not 1024 <= max_bytes <= 1_000_000:
        raise ValueError("online request limits are out of range")
    if not 1 <= max_online_sources <= MAX_ONLINE_SOURCES:
        raise ValueError("online source count limit is out of range")
    if online and len(sources) > max_online_sources:
        raise ValueError("online source list exceeds explicit request limit")
    prior = prior or {}
    rows = []
    for source in sources:
        row: dict[str, Any] = {key: source[key] for key in
                               ("id", "name", "kind", "url", "roadmap_step", "license_state")}
        row.update({"checked_at": _utc_now(), "retrieved_at": None, "change": "unknown",
                    "comparison_basis": None, "observed": None, "failure": None})
        if online:
            try:
                observation = fetch_source(source, timeout_seconds=timeout_seconds,
                                           max_bytes=max_bytes, opener=opener)
            except (HTTPError, URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as error:
                row["failure"] = _failure(error)
            else:
                row["retrieved_at"] = _utc_now()
                row["observed"] = observation
                key = (source["id"], source["kind"], source["url"])
                if key in prior:
                    baseline, basis = prior[key]
                    row["comparison_basis"] = basis
                elif source.get("baseline_revision"):
                    baseline, basis = source["baseline_revision"], "manifest baseline_revision"
                    row["comparison_basis"] = basis
                else:
                    baseline = None
                if baseline is not None:
                    row["change"] = "unchanged" if observation["fingerprint"] == baseline else "changed"
        rows.append(row)
    return {"record_type": REPORT_TYPE, "created_at": _utc_now(),
            "mode": "online" if online else "offline_validation",
            "limits": {"timeout_seconds": timeout_seconds, "max_bytes": max_bytes,
                       "max_online_sources": max_online_sources},
            "sources": rows,
            "interpretation": "Changes are review prompts, not source claims, candidate approval, or runtime authority."}


def write_new_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--manifest", type=Path, default=ROOT / "tools/research_source_watch.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts/research-source-watch")
    parser.add_argument("--output", type=Path, help="exact new report path; existing files are refused")
    parser.add_argument("--online", action="store_true", help="make bounded, read-only HTTPS checks")
    parser.add_argument("--timeout-seconds", type=float, default=5.0)
    parser.add_argument("--max-bytes", type=int, default=512_000)
    parser.add_argument("--max-online-sources", type=int, default=12)
    args = parser.parse_args(argv)
    try:
        raw = args.manifest.read_bytes()
        sources = validate_manifest(json.loads(raw))
        output = args.output or (args.output_dir / (REPORT_PREFIX + datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%S.%fZ") + ".json"))
        prior = load_prior_observations(output.parent) if args.online else {}
        report = run_watch(sources, online=args.online, prior=prior,
                           timeout_seconds=args.timeout_seconds,
                           max_bytes=args.max_bytes,
                           max_online_sources=args.max_online_sources)
        report["manifest_sha256"] = hashlib.sha256(raw).hexdigest()
        report["tool_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        write_new_report(output, report)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        parser._print_message(f"source watch failed: {error}\n", sys.stderr)
        return 2
    failures = sum(row["failure"] is not None for row in report["sources"])
    print(f"wrote {output} ({report['mode']}; {len(sources)} sources; {failures} failures)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
