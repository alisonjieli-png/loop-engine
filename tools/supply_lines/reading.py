"""Read-only fact reading for the supply lines: declared public hosts, the gh login, a cache and a modest pace.

```text
FactReader (one run folder)
├── https: HttpsGetTransport of library ingestion, to the hosts the line declares; GET only, no
│   redirect, bounded bytes, every request admitted by a budget and logged
├── github REST: GhCliReader of library ingestion (its allow list: a repository, its licence, a
│   commit, a file at a commit)
├── github GraphQL: one fixed template here (repository facts with the latest release and each
│   asset's published digest), never a mutation, admitted by its own budget and logged
├── pace: at least a fixed pause between two network requests (a modest rate)
└── cache: every answer kept under the run folder by the digest of its address, so a stopped
    run starts again without reading anything twice
```

Nothing here writes outside the run folder, sends a credential to a public
host or prints a token: gh reads its own login.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
import urllib.parse
from urllib.parse import parse_qsl, urlsplit

from loop_engine.core.library_ingestion.github_reader import GITHUB_HOST, GhCliReader, parse_included_response
from loop_engine.core.library_ingestion.https_transport import HTTPS_SCHEME, HttpsGetTransport
from loop_engine.core.library_ingestion.record_rules import git_blob_identity, now_utc
from loop_engine.core.library_ingestion.request_log import RequestBudget, RequestLog, RequestObservation

from licensed_import.processes import gh_environment, run

_OWNER = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}\Z")
_NAME = re.compile(r"[A-Za-z0-9._-]{1,100}\Z")
_QUOTED = re.compile(r'"[^"\\]*"')
_FORBIDDEN = re.compile(r"\b(?:mutation|subscription)\b", re.I)
#: The one GraphQL template of the supply lines: repository facts with the latest release and its assets.
RELEASE_FIELDS = ("nameWithOwner isFork isArchived isPrivate stargazerCount licenseInfo { spdxId } "
                  "defaultBranchRef { name target { oid } } "
                  "latestRelease { tagName publishedAt tagCommit { oid } "
                  "releaseAssets(first: 100) { nodes { name size downloadUrl digest } } }")
MAXIMUM_BATCH = 25
#: The host that serves a GitHub file's exact bytes at a commit, and the host of GitHub's web pages.
RAW_HOST = "raw.githubusercontent.com"
GITHUB_WEB_HOST = "github.com"


def https_address(host: str, path: str) -> str:
    """An HTTPS address on a host: every address a supply line reads or records is built here."""
    return urllib.parse.urlunsplit((HTTPS_SCHEME, host, "/" + str(path).lstrip("/"), "", ""))


def github_blob_address(repository: str, revision: str, path: str) -> str:
    """The web address of one file of a GitHub repository at a revision, for attribution."""
    return https_address(GITHUB_WEB_HOST, f"{repository}/blob/{revision}/{path}")


def is_https(address) -> bool:
    return urllib.parse.urlsplit(str(address)).scheme == HTTPS_SCHEME


@dataclass(frozen=True)
class Fetched:
    url: str
    status: "int | None"
    body: bytes
    sha256: str
    retrieved_at: str
    cached: bool


def split_repository(repository: str) -> tuple:
    owner, _, name = str(repository).partition("/")
    if not _OWNER.match(owner) or not _NAME.match(name) or name in (".", ".."):
        raise ValueError(f"not a repository name: {str(repository)[:80]}")
    return owner, name


def repository_facts_query(repositories) -> str:
    """The fixed read: facts and the latest release of up to MAXIMUM_BATCH repositories."""
    repositories = list(repositories)
    if not 1 <= len(repositories) <= MAXIMUM_BATCH:
        raise ValueError(f"a release read names 1 to {MAXIMUM_BATCH} repositories")
    parts = []
    for index, repository in enumerate(repositories):
        owner, name = split_repository(repository)
        parts.append(f'r{index}: repository(owner: "{owner}", name: "{name}") {{ {RELEASE_FIELDS} }}')
    text = "query { rateLimit { cost remaining resetAt } " + " ".join(parts) + " }"
    unquoted = _QUOTED.sub('""', text)
    if _FORBIDDEN.search(unquoted) or '"' in _QUOTED.sub("", text):
        raise ValueError("a GraphQL read is a query and never a mutation or a subscription")
    return text


class FactReader:
    """Every read a supply line makes, paced, budgeted, logged and cached under one run folder."""

    def __init__(self, run_folder, hosts, *, maximum_requests: int = 5000, pause_seconds: float = 0.25,
                 maximum_bytes: int = 64 * 1024 * 1024, github: bool = True, sleep=time.sleep,
                 clock=time.monotonic) -> None:
        self.folder = Path(run_folder)
        self.cache = self.folder / "cache"
        self.cache.mkdir(parents=True, exist_ok=True)
        self.https = HttpsGetTransport(hosts, RequestBudget(maximum_requests, 1800.0),
                                       RequestLog(self.folder / "requests-https.jsonl"), timeout_seconds=90.0,
                                       maximum_bytes=maximum_bytes)
        self.rest = GhCliReader(RequestBudget(maximum_requests, 3700.0), RequestLog(self.folder / "requests-gh.jsonl"),
                                maximum_bytes=maximum_bytes) if github else None
        self.graphql_budget = RequestBudget(maximum_requests, 3700.0)
        self.graphql_log = RequestLog(self.folder / "requests-graphql.jsonl")
        self.pause_seconds, self.sleep, self.clock = pause_seconds, sleep, clock
        self._last = None
        self.network_requests = 0
        self.cache_hits = 0

    # -- the cache ------------------------------------------------------------------------------------------------
    def _paths(self, key: str) -> tuple:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.cache / digest[:2] / f"{digest}.body", self.cache / digest[:2] / f"{digest}.json"

    def _cached(self, key: str) -> "Fetched | None":
        body_path, meta_path = self._paths(key)
        if not meta_path.is_file() or not body_path.is_file():
            return None
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        body = body_path.read_bytes()
        if hashlib.sha256(body).hexdigest() != meta["sha256"]:
            return None
        self.cache_hits += 1
        return Fetched(meta["url"], meta["status"], body, meta["sha256"], meta["retrieved_at"], True)

    def _keep(self, key: str, url: str, status, body: bytes) -> Fetched:
        body_path, meta_path = self._paths(key)
        body_path.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(body).hexdigest()
        retrieved = now_utc()
        temporary = body_path.with_suffix(".partial")
        temporary.write_bytes(body)
        temporary.replace(body_path)
        meta_path.write_text(json.dumps({"url": url, "status": status, "sha256": digest, "retrieved_at": retrieved,
                                         "size_bytes": len(body)}, sort_keys=True), encoding="utf-8")
        return Fetched(url, status, body, digest, retrieved, False)

    def _pace(self) -> None:
        now = self.clock()
        if self._last is not None and now - self._last < self.pause_seconds:
            self.sleep(self.pause_seconds - (now - self._last))
        self._last = self.clock()
        self.network_requests += 1

    # -- reads ----------------------------------------------------------------------------------------------------
    def get(self, url: str, *, cache_errors: bool = False) -> Fetched:
        """A GET of a public HTTPS address on a declared host; a 200 answer (and, if asked, any answer) is cached."""
        found = self._cached(url)
        if found is not None:
            return found
        parts = urlsplit(url)
        if parts.scheme != HTTPS_SCHEME or not parts.hostname:
            raise ValueError(f"not an HTTPS address: {url[:120]}")
        self._pace()
        response = self.https.get(parts.hostname, parts.path or "/", dict(parse_qsl(parts.query)))
        if response.status == 200 or (cache_errors and response.status is not None):
            return self._keep(url, url, response.status, response.body)
        return Fetched(url, response.status, response.body, hashlib.sha256(response.body).hexdigest(), now_utc(), False)

    def github(self, path: str) -> Fetched:
        """A read-only GitHub REST read from the library ingestion allow list, cached when it answers."""
        key = https_address(GITHUB_HOST, path)
        found = self._cached(key)
        if found is not None:
            return found
        if self.rest is None:
            raise PermissionError("this reader has no GitHub access")
        self._pace()
        response = self.rest.get(path)
        if response.status in (200, 404):
            return self._keep(key, key, response.status, response.body)
        return Fetched(key, response.status, response.body, hashlib.sha256(response.body).hexdigest(), now_utc(), False)

    def repository_facts(self, repositories) -> dict:
        """Repository name (lower case) to its facts and latest release, read MAXIMUM_BATCH at a time."""
        wanted = sorted({repository for repository in repositories})
        facts = {}
        for start in range(0, len(wanted), MAXIMUM_BATCH):
            chunk = wanted[start:start + MAXIMUM_BATCH]
            key = "graphql:" + json.dumps(chunk)
            found = self._cached(key)
            if found is None:
                text = repository_facts_query(chunk)
                self._pace()
                self.graphql_budget.admit()
                started = now_utc()
                result = run(("gh", "api", "--include", "graphql", "-f", f"query={text}"), timeout_seconds=120.0,
                             maximum_output_bytes=32 * 1024 * 1024, environment=gh_environment())
                if result.exit_code is None or not result.stdout:
                    self.graphql_log.record(RequestObservation("gh_api", GITHUB_HOST, "graphql:repository_releases",
                                                               None, None, started, result.elapsed_ms,
                                                               "transport_error", error_class="no_response"))
                    continue
                response = parse_included_response(result.stdout)
                self.graphql_log.record(RequestObservation(
                    "gh_api", GITHUB_HOST, "graphql:repository_releases", response.status, response.body, started,
                    result.elapsed_ms, "ok" if response.status == 200 else "http_error",
                    allowance_remaining=response.allowance_remaining))
                if response.status != 200:
                    continue
                found = self._keep(key, key, 200, response.body)
            data = (json.loads(found.body).get("data") or {})
            for index, repository in enumerate(chunk):
                value = data.get(f"r{index}")
                facts[repository.lower()] = value
        return facts

    def licence_text(self, repository: str, commit: str) -> "tuple | None":
        """(path, bytes, GitHub's SPDX identifier) of a repository's licence file at a commit, or None."""
        answer = self.github(f"repos/{repository}/license?ref={commit}")
        if answer.status != 200:
            return None
        try:
            document = json.loads(answer.body)
            data = base64.b64decode(document.get("content", ""))
        except (ValueError, TypeError):
            return None
        return document.get("path"), data, ((document.get("license") or {}).get("spdx_id") or "NOASSERTION")

    def pinned_file(self, repository: str, branch: str, path: str) -> dict:
        """A GitHub file at its branch's head commit, its bytes proven by git blob identity; raises LookupError."""
        head = self.github(f"repos/{repository}/commits/{branch}")
        if head.status != 200:
            raise LookupError(f"{repository}: the branch {branch} has no readable head commit")
        commit = json.loads(head.body)["sha"]
        meta = self.github(f"repos/{repository}/contents/{urllib.parse.quote(path)}?ref={commit}")
        if meta.status != 200:
            raise LookupError(f"{repository}/{path}: no file at {commit[:12]}")
        blob = json.loads(meta.body).get("sha")
        url = https_address(RAW_HOST, f"{repository}/{commit}/{urllib.parse.quote(path)}")
        raw = self.get(url)
        if raw.status != 200 or git_blob_identity(raw.body) != blob:
            raise LookupError(f"{repository}/{path}: the bytes differ from the blob {blob}")
        return {"repository": repository, "commit": commit, "path": path, "blob": blob, "url": url,
                "bytes": raw.body, "sha256": raw.sha256, "retrieved_at": raw.retrieved_at}

    def requests(self) -> dict:
        return {"network_requests": self.network_requests, "cache_hits": self.cache_hits,
                "https": self.https.log.summary(), "github_rest": self.rest.log.summary() if self.rest else None,
                "github_graphql": self.graphql_log.summary()}
