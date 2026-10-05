"""Read-only fact reading for the supply lines: declared public hosts, the gh login, a cache and a modest pace.

```text
FactReader (one run folder)
├── https: HttpsGetTransport of library ingestion, to the hosts the line declares; GET only, no
│   redirect, bounded bytes, every request admitted by a budget and logged
├── github REST: GhCliReader of library ingestion (its allow list: a repository, its licence, a
│   commit, a file at a commit)
├── github GraphQL: one fixed template here (repository facts with the latest release and each
│   asset's published digest), never a mutation, admitted by its own budget and logged
├── digest: a download streamed through SHA-256 and MD5 and never kept (bounded bytes, at most
│   MAXIMUM_REDIRECTS redirects, each to a declared HTTPS host), for a file a package pins but
│   does not carry; only its digest, size and final address are cached
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
import urllib.error
import urllib.parse
import urllib.request
from urllib.parse import parse_qsl, urlsplit

from loop_engine.core.library_ingestion.github_reader import (
    GITHUB_HOST, GhCliReader, ReadOnlyRequestRefused, parse_included_response)
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
#: The characters a request path keeps as they are when a listed address is encoded (RFC 3986 path characters and
#: the escape sign).
PATH_SAFE = "/%:@!$&'()*+,;=-._~"
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


#: The redirects one streamed download may follow, each to a declared HTTPS host: ambientCG's download address
#: answers with a redirect to its content delivery network.
MAXIMUM_REDIRECTS = 5
DIGEST_CHUNK_BYTES = 1024 * 1024
DIGEST_USER_AGENT = "loop-engine library-supply (read-only; digests pinned downloads)"


@dataclass(frozen=True)
class Digested:
    """What a streamed download was: its SHA-256, MD5 and size, and where the bytes came from after redirects.

    The bytes themselves are never kept. ``inspected`` is what the caller's inspection of the downloaded file
    returned before the file was removed (a zip archive's member list), cached with the digest."""

    url: str
    final_url: "str | None"
    status: "int | None"
    sha256: "str | None"
    md5: "str | None"
    size_bytes: "int | None"
    retrieved_at: str
    cached: bool
    inspected: object = None
    error: str = ""

    @property
    def ok(self) -> bool:
        return self.status == 200 and not self.error and self.sha256 is not None


class _DeclaredRedirects(urllib.request.HTTPRedirectHandler):
    """Follow a redirect only to an HTTPS address on a declared host, at most MAXIMUM_REDIRECTS times."""

    max_redirections = MAXIMUM_REDIRECTS

    def __init__(self, hosts) -> None:
        super().__init__()
        self.hosts = frozenset(hosts)

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parts = urlsplit(newurl)
        if parts.scheme != HTTPS_SCHEME or parts.hostname not in self.hosts:
            if fp is not None:
                fp.close()
            raise urllib.error.HTTPError(newurl, code, f"a redirect to an undeclared address ({parts.hostname})",
                                         headers, None)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


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
                 clock=time.monotonic, digest_cache=None) -> None:
        self.folder = Path(run_folder)
        self.cache = self.folder / "cache"
        self.cache.mkdir(parents=True, exist_ok=True)
        # Digests of pinned downloads may live in a folder shared by several runs: a file is downloaded again only
        # when its publisher's size or checksum changes, since the download is the expensive read.
        self.digest_cache = Path(digest_cache) if digest_cache else self.cache
        self.digest_log = self.folder / "requests-digest.jsonl"
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
        # A listed address may hold characters a request line cannot carry (a space in "v2.0 preview"): they are
        # percent-encoded; an address already encoded keeps its escapes.
        response = self.https.get(parts.hostname, urllib.parse.quote(parts.path or "/", safe=PATH_SAFE),
                                  dict(parse_qsl(parts.query)))
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

    # -- streamed digests -------------------------------------------------------------------------------------------
    def _open(self, request, timeout: float):
        """Open one streamed download; the redirect handler admits only declared HTTPS hosts."""
        return urllib.request.build_opener(_DeclaredRedirects(self.https.hosts)).open(request, timeout=timeout)

    def digest(self, url: str, *, published: "dict | None" = None, maximum_bytes: int = 256 * 1024 * 1024,
               inspect=None, use_cache: bool = True) -> Digested:
        """Stream one download through SHA-256 and MD5 without keeping it, and cache what it was.

        ``published`` (the publisher's size and checksum) is part of the cache key, so a file its publisher changed
        is read again. ``inspect(path)`` reads the downloaded file before it is removed and returns JSON-ready data
        that is cached with the digest (a zip archive's member list). Only HTTPS addresses on declared hosts are
        read, and at most ``maximum_bytes``. ``use_cache=False`` reads again when what ``inspect`` wrote from an
        earlier read is gone."""
        key = "digest:" + json.dumps([url, published or {}, bool(inspect)], sort_keys=True)
        digest_key = hashlib.sha256(key.encode("utf-8")).hexdigest()
        meta_path = self.digest_cache / digest_key[:2] / f"{digest_key}.digest.json"
        if use_cache and meta_path.is_file():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            self.cache_hits += 1
            return Digested(meta["url"], meta["final_url"], meta["status"], meta["sha256"], meta["md5"],
                            meta["size_bytes"], meta["retrieved_at"], True, meta.get("inspected"))
        parts = urlsplit(url)
        if parts.scheme != HTTPS_SCHEME or parts.hostname not in self.https.hosts:
            raise ValueError(f"not an HTTPS address on a declared host: {url[:120]}")
        self._pace()
        self.https.budget.admit()
        started, clock = now_utc(), time.monotonic()
        temporary = self.folder / "downloads" / f"{digest_key}.partial"
        temporary.parent.mkdir(parents=True, exist_ok=True)
        status = final = sha256 = md5 = size = inspected = None
        error = ""
        request = urllib.request.Request(urllib.parse.urlunsplit((parts.scheme, parts.netloc, urllib.parse.quote(
            parts.path or "/", safe=PATH_SAFE), parts.query, "")), method="GET",
            headers={"User-Agent": DIGEST_USER_AGENT, "Accept": "*/*"})
        try:
            with self._open(request, 120.0) as answer:
                status, final = answer.status, answer.geturl()
                hashes, count = (hashlib.sha256(), hashlib.md5(usedforsecurity=False)), 0
                with open(temporary, "wb") as stream:
                    while True:
                        chunk = answer.read(DIGEST_CHUNK_BYTES)
                        if not chunk:
                            break
                        count += len(chunk)
                        if count > maximum_bytes:
                            error = "response_too_large"
                            break
                        for value in hashes:
                            value.update(chunk)
                        stream.write(chunk)
            if not error and status == 200:
                sha256, md5, size = hashes[0].hexdigest(), hashes[1].hexdigest(), count
                if inspect is not None:
                    inspected = inspect(temporary)
        except urllib.error.HTTPError as failure:
            failure.close()
            status, error = failure.code, f"http_error {failure.code} {failure.msg}"[:200]
        except (urllib.error.URLError, OSError, ValueError) as failure:
            error = type(failure).__name__
        finally:
            temporary.unlink(missing_ok=True)
        retrieved = now_utc()
        row = {"url": url[:512], "final_url": (final or "")[:512], "status": status, "sha256": sha256,
               "size_bytes": size, "started_at": started, "elapsed_ms": round((time.monotonic() - clock) * 1000, 1),
               "error": error}
        with self.digest_log.open("a", encoding="utf-8") as log:
            log.write(json.dumps(row, sort_keys=True) + "\n")
        result = Digested(url, final, status, sha256, md5, size, retrieved, False, inspected, error)
        if result.ok:
            meta_path.parent.mkdir(parents=True, exist_ok=True)
            meta_path.write_text(json.dumps({"url": url, "final_url": final, "status": status, "sha256": sha256,
                                             "md5": md5, "size_bytes": size, "retrieved_at": retrieved,
                                             "inspected": inspected}, sort_keys=True), encoding="utf-8")
        return result

    def requests(self) -> dict:
        digests = []
        if self.digest_log.is_file():
            digests = [json.loads(line) for line in self.digest_log.read_text(encoding="utf-8").splitlines() if line]
        return {"network_requests": self.network_requests, "cache_hits": self.cache_hits,
                "https": self.https.log.summary(), "github_rest": self.rest.log.summary() if self.rest else None,
                "github_graphql": self.graphql_log.summary(),
                "digests": {"downloads": len(digests), "bytes": sum(row.get("size_bytes") or 0 for row in digests),
                            "failed": sum(1 for row in digests if row.get("error") or row.get("status") != 200)}}


def pinned_files(reader, repository: str, branch: str, paths) -> tuple:
    """({path: pinned file}, missing paths) of many files of one repository: the branch's head commit, its tree
    (one read), and each file's bytes at that commit, proven by the tree's git blob identity."""
    try:
        head = reader.github(f"repos/{repository}/commits/{branch}")
    except ReadOnlyRequestRefused as error:  # a branch name the read-only reader does not allow, such as one with /
        raise LookupError(f"{repository}: the branch {branch[:100]} is not a readable name") from error
    if head.status != 200:
        raise LookupError(f"{repository}: the branch {branch} has no readable head commit")
    commit = json.loads(head.body)["sha"]
    tree = reader.github(f"repos/{repository}/git/trees/{commit}?recursive=1")
    if tree.status != 200:
        raise LookupError(f"{repository}: no tree at {commit[:12]}")
    blobs = {entry["path"]: entry["sha"] for entry in json.loads(tree.body).get("tree", []) if entry.get("type") == "blob"}
    pinned, missing = {}, []
    for path in paths:
        if path not in blobs:
            missing.append(path)
            continue
        url = https_address(RAW_HOST, f"{repository}/{commit}/{path}")
        answer = reader.get(url)
        if answer.status != 200 or git_blob_identity(answer.body) != blobs[path]:
            missing.append(path)
            continue
        pinned[path] = {"repository": repository, "commit": commit, "path": path, "blob": blobs[path], "url": url,
                        "bytes": answer.body, "sha256": answer.sha256, "retrieved_at": answer.retrieved_at}
    return pinned, missing


#: The names of a repository's notice file, in the order they are looked for (Apache-2.0 section 4(d) asks that a
#: derivative work carry the attribution notices of the work's NOTICE file).
NOTICE_NAMES = ("NOTICE", "NOTICE.txt", "NOTICE.md")


def repository_notice(reader, repository: str, commit: str, spdx: str) -> "dict | None":
    """The notice file at a repository's root at an exact commit, its bytes proven by blob identity, or None.

    ``spdx`` is the licence of the repository at that commit, which the notice file is distributed under as
    one of the repository's files; the caller has already decided that licence."""
    for name in NOTICE_NAMES:
        try:
            found = reader.pinned_file(repository, commit, name)
        except LookupError:
            continue
        return {"repository": repository, "commit": found["commit"], "path": name, "bytes": found["bytes"],
                "sha256": found["sha256"], "retrieved_at": found["retrieved_at"], "spdx": spdx,
                "url": github_blob_address(repository, found["commit"], name)}
    return None
