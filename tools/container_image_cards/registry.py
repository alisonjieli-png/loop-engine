"""Read container images from an OCI distribution registry without pulling a layer: tags by HEAD, documents by digest.

```text
RegistryReader (one run folder; read_tag, read_document and head_document are its fixed edge)
├── engines (RegistryProfile), chosen by the caller in declared order
│   ├── docker_hub: registry-1.docker.io; anonymous bearer tokens from auth.docker.io. A tag is resolved by HEAD
│   │   and every document is read by its digest through the blob endpoint (an image index and a manifest are
│   │   content-addressed blobs there as well); measured on October 9, 2026, neither changes the anonymous pull
│   │   allowance (ratelimit-remaining 100;w=3600 before and after). A manifest the blob endpoint does not serve
│   │   is read from the manifest endpoint, which counts as a pull, only while the allowance stays above a reserve
│   └── ecr_public: public.ecr.aws, the mirror docker/library/<name> of the Docker Official Images, which serves
│       the same digests (alpine:latest's index was byte for byte the same on October 9, 2026)
├── every document is checked against the digest it was asked for (SHA-256) and cached under that digest, so a
│   later run reads it from disk; a tag answer is never cached across runs
├── tokens: requested from the realm the registry's challenge names, only on a declared host; held in memory only,
│   never written or logged, and sent as an unredirected header, so a content delivery host never receives one
├── redirects: a blob answer may redirect to a content delivery host; only a declared HTTPS host is followed
├── pace and ceiling: at least a pause between two requests and at most the run's ceiling (RequestBudget)
└── log: container_registry_request/v1, one line per request (method, host, path, status, bytes, the digest of
    the body, time, the registry's allowance headers); no header that could carry a credential is kept
```
"""
from __future__ import annotations

import hashlib
import json
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from loop_engine.core.library_ingestion.https_transport import HTTPS_SCHEME
from loop_engine.core.library_ingestion.record_rules import now_utc
from loop_engine.core.library_ingestion.request_log import PauseExceedsBound, RequestBudget, RequestCeilingReached

REQUEST_RECORD = "container_registry_request/v1"
#: The media types of the documents a card reads.
(OCI_INDEX, DOCKER_LIST, OCI_MANIFEST, DOCKER_MANIFEST, OCI_CONFIG, DOCKER_CONFIG) = MEDIA_TYPES = (
    "application/vnd.oci.image.index.v1+json", "application/vnd.docker.distribution.manifest.list.v2+json",
    "application/vnd.oci.image.manifest.v1+json", "application/vnd.docker.distribution.manifest.v2+json",
    "application/vnd.oci.image.config.v1+json", "application/vnd.docker.container.image.v1+json")
INDEX_TYPES, MANIFEST_TYPES, CONFIG_TYPES = (OCI_INDEX, DOCKER_LIST), (OCI_MANIFEST, DOCKER_MANIFEST), (
    OCI_CONFIG, DOCKER_CONFIG)
#: What a manifest request accepts: an index or a list first, then one image's manifest.
MANIFEST_ACCEPT = ", ".join(INDEX_TYPES + MANIFEST_TYPES)
#: The digests a card pins: SHA-256 only, as every registry this line reads writes them.
DIGEST_PATTERN = re.compile(r"sha256:([0-9a-f]{64})")
DIGEST_ALGORITHM = "sha256:"
#: The registry's own headers: the digest of what a manifest request names, and the anonymous pull allowance.
DIGEST_HEADER, LIMIT_HEADER, REMAINING_HEADER = "Docker-Content-Digest", "ratelimit-limit", "ratelimit-remaining"
LOCATION_HEADER, CHALLENGE_HEADER, RETRY_HEADER = "Location", "WWW-Authenticate", "Retry-After"
CONTENT_TYPE_HEADER, LENGTH_HEADER = "Content-Type", "Content-Length"
#: A challenge names the token realm and the service; a token answer carries the token under one of two names.
BEARER, REALM, SERVICE = "Bearer", "realm", "service"
TOKEN_FIELDS, EXPIRY_FIELD = ("token", "access_token"), "expires_in"
#: How long before its stated expiry a token is replaced, and the life of a token whose answer states none.
TOKEN_MARGIN_SECONDS, TOKEN_DEFAULT_SECONDS = 30, 60
HEAD, GET = "HEAD", "GET"
#: The largest document read: the distribution specification bounds a manifest at 4 MiB; a config may be larger.
MAXIMUM_DOCUMENT_BYTES = 8 * 1024 * 1024
MAXIMUM_TOKEN_BYTES = 64 * 1024
#: The statuses an answer may have, and how many times a server error or a rate limit is tried again.
OK, NOT_FOUND, UNAUTHORIZED, TOO_MANY = 200, 404, 401, 429
SERVER_ERRORS = range(500, 600)
RETRIES = 2
RETRY_PAUSE_SECONDS = 5.0
#: The redirects one blob read may follow.
MAXIMUM_REDIRECTS = 3
#: The reasons a read fails, from one closed vocabulary (the line's refusal reasons).
(REGISTRY_UNREADABLE, TAG_NOT_FOUND, DOCUMENT_NOT_FOUND, DIGEST_MISMATCH, DOCUMENT_TOO_LARGE, REDIRECT_UNDECLARED,
 UNAUTHORIZED_REASON, RATE_LIMITED, DIGEST_UNSUPPORTED) = READ_FAILURES = (
    "registry_unreadable", "tag_not_found", "document_not_found", "document_digest_mismatch", "document_too_large",
    "registry_redirect_undeclared", "registry_unauthorized", "registry_rate_limited", "digest_unsupported")
USER_AGENT = "Baltor-container-image-cards/1.0 (+baltor.ai; read-only manifests and configs, no layers)"


class RegistryError(RuntimeError):
    """A registry read that did not give the document or answer asked for, with a reason of READ_FAILURES."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason, self.detail = reason, detail


@dataclass(frozen=True)
class RegistryProfile:
    """One registry engine: where it answers, which hosts its tokens and redirects may use, and how it names a
    repository of the Docker Official Images."""

    name: str
    host: str
    token_hosts: tuple
    redirect_hosts: tuple
    namespace: str  # library on Docker Hub, docker/library on the ECR Public mirror
    #: Whether its manifest endpoint counts a GET against an anonymous pull allowance.
    counts_manifest_reads: bool
    #: Whether a document is read through the blob endpoint first (an index and a manifest are blobs there too).
    documents_through_blobs: bool

    def repository(self, name: str) -> str:
        return f"{self.namespace}/{name}"

    def hosts(self) -> tuple:
        return (self.host,) + tuple(self.token_hosts) + tuple(self.redirect_hosts)


DOCKER_HUB = RegistryProfile(
    name="docker_hub", host="registry-1.docker.io", token_hosts=("auth.docker.io",),
    redirect_hosts=("production.cloudfront.docker.com", "production.cloudflare.docker.com"), namespace="library",
    counts_manifest_reads=True, documents_through_blobs=True)
ECR_PUBLIC = RegistryProfile(
    name="ecr_public", host="public.ecr.aws", token_hosts=("public.ecr.aws",),
    redirect_hosts=("d2glxqk2uabbnd.cloudfront.net",), namespace="docker/library", counts_manifest_reads=False,
    documents_through_blobs=False)
PROFILES = {profile.name: profile for profile in (DOCKER_HUB, ECR_PUBLIC)}
#: The registry and namespace every card names its image by (the canonical name docker pull resolves).
CANONICAL_REGISTRY, CANONICAL_NAMESPACE = "docker.io", "library"


def https(host: str, path: str, query: "dict | None" = None) -> str:
    """An HTTPS address on a host; every address the reader sends a request to is built here."""
    return urllib.parse.urlunsplit((HTTPS_SCHEME, host, "/" + path.lstrip("/"),
                                    urllib.parse.urlencode(query or {}), ""))


def digest_hex(digest: str) -> str:
    """The hexadecimal part of a sha256 digest; raises RegistryError for anything else."""
    match = DIGEST_PATTERN.fullmatch(str(digest))
    if not match:
        raise RegistryError(DIGEST_UNSUPPORTED, str(digest)[:80])
    return match.group(1)


def challenge(value: str) -> dict:
    """The parameters of a Bearer challenge: realm, service (and scope when one is named)."""
    scheme, _, rest = str(value or "").partition(" ")
    if scheme != BEARER:
        return {}
    return {key: item for key, item in re.findall(r'([A-Za-z_]+)="([^"]*)"', rest)}


def allowance(headers) -> dict:
    """The pull allowance the registry reports, as it states it ("100;w=3600"), or nothing."""
    found = {}
    for name, key in ((LIMIT_HEADER, "limit"), (REMAINING_HEADER, "remaining")):
        value = headers.get(name) if headers is not None else None
        if value:
            found[key] = str(value)[:40]
    return found


def remaining_pulls(answer: dict) -> "int | None":
    """The count of an allowance answer's remaining pulls ("97;w=3600" is 97), or None when it states none."""
    match = re.match(r"\s*(\d+)", str(answer.get("remaining", "")))
    return int(match.group(1)) if match else None


@dataclass(frozen=True)
class Answer:
    """One HTTP exchange as the transport saw it: the status, the headers kept, the body and where it ended."""

    status: "int | None"
    headers: dict
    body: bytes
    final_host: str = ""
    error: str = ""


class _DeclaredRedirects(urllib.request.HTTPRedirectHandler):
    """Follow a redirect only to an HTTPS address on a declared host."""

    max_redirections = MAXIMUM_REDIRECTS

    def __init__(self, hosts) -> None:
        super().__init__()
        self.hosts = frozenset(hosts)

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parts = urllib.parse.urlsplit(newurl)
        if parts.scheme != HTTPS_SCHEME or parts.hostname not in self.hosts:
            raise urllib.error.HTTPError(newurl, code, f"{REDIRECT_UNDECLARED} {parts.hostname}", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


#: The response headers an exchange keeps; nothing that could carry a credential.
KEPT_HEADERS = (DIGEST_HEADER, LIMIT_HEADER, REMAINING_HEADER, CHALLENGE_HEADER, RETRY_HEADER, CONTENT_TYPE_HEADER,
                LENGTH_HEADER)


def urllib_transport(hosts, timeout_seconds: float = 60.0):
    """The default transport: one request through urllib, redirects only to declared hosts, at most maximum bytes."""
    opener = urllib.request.build_opener(_DeclaredRedirects(hosts))

    def send(method: str, url: str, headers: dict, credential: "str | None", maximum_bytes: int) -> Answer:
        request = urllib.request.Request(url, method=method, headers=headers)
        if credential is not None:
            # An unredirected header stays with this request: a redirect to a content delivery host never gets it.
            request.add_unredirected_header("Authorization", f"{BEARER} {credential}")
        try:
            with opener.open(request, timeout=timeout_seconds) as answer:
                body = b"" if method == HEAD else answer.read(maximum_bytes + 1)
                kept = {name: answer.headers.get(name) for name in KEPT_HEADERS if answer.headers.get(name)}
                return Answer(answer.status, kept, body, urllib.parse.urlsplit(answer.geturl()).hostname or "")
        except urllib.error.HTTPError as failure:
            kept = {name: failure.headers.get(name) for name in KEPT_HEADERS
                    if failure.headers is not None and failure.headers.get(name)}
            reason = REDIRECT_UNDECLARED if REDIRECT_UNDECLARED in str(failure.msg) else ""
            try:
                failure.close()
            except OSError:
                pass
            return Answer(failure.code, kept, b"", "", reason)
        except (urllib.error.URLError, OSError, ValueError) as failure:
            return Answer(None, {}, b"", "", type(failure).__name__)

    return send


@dataclass(frozen=True)
class TagAnswer:
    """What a HEAD of a tag said: the digest it resolves to, its media type and size, and the pull allowance."""

    repository: str
    tag: str
    digest: str
    media_type: str
    size: int
    retrieved_at: str
    allowance: dict


@dataclass(frozen=True)
class Document:
    """One document read by its digest: the exact bytes, where they were read and whether the cache gave them."""

    digest: str
    data: bytes
    url: str
    retrieved_at: str
    cached: bool

    @property
    def size(self) -> int:
        return len(self.data)

    def json(self):
        return json.loads(self.data)


@dataclass
class RegistryReader:
    """Every registry read of one run: paced, bounded, logged, and checked against the digests it asks for."""

    profile: RegistryProfile
    folder: Path
    budget: RequestBudget
    pause_seconds: float = 0.25
    cache_folder: "Path | None" = None
    user_agent: str = USER_AGENT
    transport: object = None
    #: The pull allowance a counted manifest read must leave behind.
    reserve_pulls: int = 20
    sleep: object = time.sleep
    clock: object = time.monotonic
    wall_clock: object = time.time
    requests: int = 0
    cache_hits: int = 0
    counted_reads: int = 0
    last_allowance: dict = field(default_factory=dict)
    _tokens: dict = field(default_factory=dict)
    _last: "float | None" = None

    def __post_init__(self) -> None:
        # Several workers may share one reader: the pace, the counters, the budget and the log are kept under one
        # lock, so the pause holds between any two requests of the run, whichever worker sends them.
        self._lock = threading.Lock()
        self.folder = Path(self.folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.cache_folder = Path(self.cache_folder) if self.cache_folder else self.folder / "documents"
        self.log_path = self.folder / "requests-registry.jsonl"
        if self.transport is None:
            self.transport = urllib_transport(self.profile.hosts())

    # -- requests ---------------------------------------------------------------------------------------------------
    def _pace(self) -> None:
        """Wait until at least the pause has passed since the last request started (called under the lock)."""
        now = self.clock()
        if self._last is not None and now - self._last < self.pause_seconds:
            self.sleep(self.pause_seconds - (now - self._last))
        self._last = self.clock()

    def _log(self, method: str, url: str, answer: Answer, elapsed: float, *, keep_digest: bool = True) -> None:
        parts = urllib.parse.urlsplit(url)
        row = {"record_type": REQUEST_RECORD, "sequence": self.requests, "method": method, "host": parts.hostname,
               "path": parts.path[:300], "status": answer.status, "bytes": len(answer.body),
               "body_sha256": hashlib.sha256(answer.body).hexdigest() if keep_digest and answer.body else None,
               "final_host": answer.final_host or None, "elapsed_ms": round(elapsed * 1000, 1),
               "allowance": allowance(answer.headers) or None, "error": answer.error or None}
        with self.log_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, sort_keys=True) + "\n")

    def _send(self, method: str, url: str, headers: dict, credential: "str | None", maximum_bytes: int, *,
              keep_digest: bool = True) -> Answer:
        with self._lock:
            self.budget.admit()
            self._pace()
            self.requests += 1
        started = self.clock()
        answer = self.transport(method, url, dict(headers, **{"User-Agent": self.user_agent}), credential,
                                maximum_bytes)
        with self._lock:
            self._log(method, url, answer, self.clock() - started, keep_digest=keep_digest)
            found = allowance(answer.headers)
            if found:
                self.last_allowance = found
        return answer

    def _token(self, parameters: dict, scope: str) -> "str | None":
        realm = parameters.get(REALM, "")
        parts = urllib.parse.urlsplit(realm)
        if parts.scheme != HTTPS_SCHEME or parts.hostname not in self.profile.token_hosts:
            raise RegistryError(UNAUTHORIZED_REASON, f"a token realm on an undeclared host: {parts.hostname}")
        key = (realm, parameters.get(SERVICE, ""), scope)
        held = self._tokens.get(key)
        if held and held[1] > self.wall_clock():
            return held[0]
        query = {"scope": scope}
        if parameters.get(SERVICE):
            query["service"] = parameters[SERVICE]
        url = https(parts.hostname, parts.path, query)
        answer = self._send(GET, url, {}, None, MAXIMUM_TOKEN_BYTES, keep_digest=False)
        if answer.status != OK:
            raise RegistryError(UNAUTHORIZED_REASON, f"the token realm answered {answer.status}")
        try:
            document = json.loads(answer.body)
        except ValueError:
            raise RegistryError(UNAUTHORIZED_REASON, "the token answer is not JSON") from None
        token = next((document.get(name) for name in TOKEN_FIELDS if document.get(name)), None)
        if not isinstance(token, str):
            raise RegistryError(UNAUTHORIZED_REASON, "the token answer names no token")
        lifetime = document.get(EXPIRY_FIELD) if isinstance(document.get(EXPIRY_FIELD), int) else TOKEN_DEFAULT_SECONDS
        self._tokens[key] = (token, self.wall_clock() + max(0, lifetime - TOKEN_MARGIN_SECONDS))
        return token

    def _scope(self, repository: str) -> str:
        return f"repository:{repository}:pull"

    def _request(self, method: str, path: str, repository: str, headers: dict, maximum_bytes: int) -> Answer:
        """One request to the registry, with a token when it asks for one, retried after a server error or a stated
        rate limit; raises RegistryError for a transport failure that persists."""
        url = https(self.profile.host, path)
        scope = self._scope(repository)
        credential = next((value[0] for key, value in self._tokens.items()
                           if key[2] == scope and value[1] > self.wall_clock()), None)
        attempts, challenged = 0, False
        while True:
            answer = self._send(method, url, headers, credential, maximum_bytes)
            if answer.error == REDIRECT_UNDECLARED:
                raise RegistryError(REDIRECT_UNDECLARED, path)
            if answer.status == UNAUTHORIZED and not challenged:
                # The first challenge (no token yet, or one that expired early) is answered with a fresh token.
                challenged = True
                parameters = challenge(answer.headers.get(CHALLENGE_HEADER, ""))
                if not parameters:
                    raise RegistryError(UNAUTHORIZED_REASON, f"{path}: no bearer challenge")
                self._tokens = {key: value for key, value in self._tokens.items() if key[2] != scope}
                credential = self._token(parameters, scope)
                continue
            if answer.status == UNAUTHORIZED:
                raise RegistryError(UNAUTHORIZED_REASON, path)
            retryable = answer.status is None or answer.status in SERVER_ERRORS or answer.status == TOO_MANY
            if retryable and attempts < RETRIES:
                attempts += 1
                wait = RETRY_PAUSE_SECONDS * attempts
                stated = answer.headers.get(RETRY_HEADER)
                if answer.status == TOO_MANY and stated and str(stated).isdigit():
                    wait = float(stated) + 1.0
                try:
                    with self._lock:
                        self.budget.pause(wait, f"{self.profile.host} answered {answer.status or answer.error}")
                except PauseExceedsBound as error:
                    raise RegistryError(RATE_LIMITED if answer.status == TOO_MANY else REGISTRY_UNREADABLE,
                                        str(error)) from None
                continue
            if answer.status == TOO_MANY:
                raise RegistryError(RATE_LIMITED, path)
            if answer.status is None or answer.status in SERVER_ERRORS:
                raise RegistryError(REGISTRY_UNREADABLE, f"{path}: {answer.status or answer.error}")
            return answer

    # -- the fixed edge ---------------------------------------------------------------------------------------------
    def read_tag(self, name: str, tag: str) -> TagAnswer:
        """The digest a tag resolves to now, by HEAD (no body read, no pull counted)."""
        repository = self.profile.repository(name)
        answer = self._request(HEAD, f"v2/{repository}/manifests/{tag}", repository, {"Accept": MANIFEST_ACCEPT}, 0)
        if answer.status == NOT_FOUND:
            raise RegistryError(TAG_NOT_FOUND, f"{repository}:{tag}")
        if answer.status != OK:
            raise RegistryError(REGISTRY_UNREADABLE, f"{repository}:{tag} answered {answer.status}")
        digest = str(answer.headers.get(DIGEST_HEADER, ""))
        digest_hex(digest)
        size = answer.headers.get(LENGTH_HEADER)
        return TagAnswer(repository, tag, digest, str(answer.headers.get(CONTENT_TYPE_HEADER, "")).split(";")[0],
                         int(size) if str(size or "").isdigit() else 0, now_utc(), allowance(answer.headers))

    def _cache_path(self, digest: str) -> Path:
        value = digest_hex(digest)
        return self.cache_folder / "sha256" / value[:2] / value

    def _cached(self, digest: str) -> "Document | None":
        path = self._cache_path(digest)
        meta = path.with_suffix(".json")
        if not path.is_file() or not meta.is_file():
            return None
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != digest_hex(digest):
            return None
        record = json.loads(meta.read_text(encoding="utf-8"))
        with self._lock:
            self.cache_hits += 1
        return Document(digest, data, record["url"], record["retrieved_at"], True)

    def _keep(self, digest: str, data: bytes, url: str) -> Document:
        path = self._cache_path(digest)
        path.parent.mkdir(parents=True, exist_ok=True)
        retrieved = now_utc()
        partial = path.with_suffix(f".partial-{threading.get_ident()}")
        partial.write_bytes(data)
        partial.replace(path)
        path.with_suffix(".json").write_text(json.dumps({"url": url, "retrieved_at": retrieved}, sort_keys=True),
                                             encoding="utf-8")
        return Document(digest, data, url, retrieved, False)

    def read_document(self, name: str, digest: str, *, manifest: bool, maximum_bytes: int = MAXIMUM_DOCUMENT_BYTES
                      ) -> Document:
        """The exact bytes of one document (an index, a manifest or a config) by its digest, from the cache when an
        earlier read kept them; raises RegistryError."""
        found = self._cached(digest)
        if found is not None:
            return found
        repository = self.profile.repository(name)
        use_blobs = self.profile.documents_through_blobs or not manifest
        path = f"v2/{repository}/{'blobs' if use_blobs else 'manifests'}/{digest}"
        answer = self._request(GET, path, repository, {} if use_blobs else {"Accept": MANIFEST_ACCEPT}, maximum_bytes)
        if answer.status == NOT_FOUND and use_blobs and manifest:
            # The blob endpoint does not serve this manifest: the manifest endpoint does, and may count a pull.
            if self.profile.counts_manifest_reads:
                remaining = remaining_pulls(self.last_allowance)
                if remaining is not None and remaining <= self.reserve_pulls:
                    raise RegistryError(RATE_LIMITED, f"{remaining} pulls left, a reserve of {self.reserve_pulls}")
                with self._lock:
                    self.counted_reads += 1
            path = f"v2/{repository}/manifests/{digest}"
            answer = self._request(GET, path, repository, {"Accept": MANIFEST_ACCEPT}, maximum_bytes)
        if answer.status == NOT_FOUND:
            raise RegistryError(DOCUMENT_NOT_FOUND, f"{repository}@{digest}")
        if answer.status != OK:
            raise RegistryError(REGISTRY_UNREADABLE, f"{repository}@{digest} answered {answer.status}")
        if len(answer.body) > maximum_bytes:
            raise RegistryError(DOCUMENT_TOO_LARGE, f"{repository}@{digest}")
        if hashlib.sha256(answer.body).hexdigest() != digest_hex(digest):
            raise RegistryError(DIGEST_MISMATCH, f"{repository}@{digest}")
        return self._keep(digest, answer.body, https(self.profile.host, path))

    def head_document(self, name: str, digest: str, *, manifest: bool) -> dict:
        """Whether the registry still serves a document by its digest (HEAD, no body, no pull counted): the status,
        the digest and size it states."""
        repository = self.profile.repository(name)
        path = f"v2/{repository}/{'manifests' if manifest else 'blobs'}/{digest}"
        answer = self._request(HEAD, path, repository, {"Accept": MANIFEST_ACCEPT} if manifest else {}, 0)
        size = answer.headers.get(LENGTH_HEADER)
        return {"status": answer.status, "digest": answer.headers.get(DIGEST_HEADER),
                "size": int(size) if str(size or "").isdigit() else None}

    def summary(self) -> dict:
        return {"engine": self.profile.name, "host": self.profile.host, "requests": self.requests,
                "cache_hits": self.cache_hits, "counted_manifest_reads": self.counted_reads,
                "last_allowance": dict(self.last_allowance), "paused_seconds": round(self.budget.paused_seconds, 1)}


def canonical_reference(name: str, digest: str) -> str:
    """The reference a card runs: docker.io/library/<name>@<digest>."""
    digest_hex(digest)
    return f"{CANONICAL_REGISTRY}/{CANONICAL_NAMESPACE}/{name}@{digest}"


__all__ = ["RegistryProfile", "RegistryReader", "RegistryError", "TagAnswer", "Document", "Answer", "DOCKER_HUB",
           "ECR_PUBLIC", "PROFILES", "urllib_transport", "challenge", "allowance", "remaining_pulls", "digest_hex",
           "canonical_reference", "RequestBudget", "RequestCeilingReached", "INDEX_TYPES", "MANIFEST_TYPES",
           "CONFIG_TYPES", "READ_FAILURES", "USER_AGENT", "MANIFEST_ACCEPT"]
