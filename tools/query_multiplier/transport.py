"""The multiplier's network edge: one request to the one host its executor declares, never to a forbidden host.

```text
send(executor, request)
├── refuse before anything leaves: undeclared host, forbidden host (data/hosts-v1.json, with reasons),
│   unavailable executor, missing key for a keyed engine
├── gh_api        `gh api --method GET --include <path>`: the gh login holds the GitHub credential, never this code
├── https_get     urllib GET, no redirect, bounded bytes and time, the executor's fixed public headers
└── https_post_key urllib POST of a JSON body; the bearer key is read from the environment at send time and
                   exists only in the outgoing header: it never enters the request record, the stored response,
                   the ledger or a report
```

The answer keeps the status, the provider's rate-limit headers (and Link, which carries a next-page cursor), the
body up to the declared bound and whether it was cut. No other header is kept.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlencode, urlunsplit

from loop_engine.core.library_ingestion.processes import passthrough_environment, run_command

POLICY = "research_query_host_policy/v1"
USER_AGENT = "loop-engine query-multiplier/1.0 (read-only research probes; https://github.com/alisonjieli-png/loop-engine)"
KEPT_HEADERS = ("x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-reset", "x-ratelimit-used",
                "x-ratelimit-resource", "ratelimit", "ratelimit-policy", "retry-after", "x-ratelimit-cost-usd",
                "x-ratelimit-credits-used", "x-ratelimit-remaining-usd", "x-ratelimit-available-anon_burst",
                "x-ratelimit-available-anon_sustained", "x-ratelimit-limit-anon_burst",
                "x-ratelimit-limit-anon_sustained", "link", "content-type")
MAXIMUM_BYTES = 4 * 1024 * 1024


class RequestRefused(ValueError):
    """Nothing was sent; the code says why."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class HostPolicy:
    forbidden: tuple  # (domain, reason)
    retired: tuple

    def refusal(self, host: str) -> "str | None":
        host = (host or "").lower().rstrip(".")
        for domain, reason in self.forbidden:
            if host == domain or host.endswith("." + domain):
                return reason
        for domain, reason in self.retired:
            if host == domain or host.endswith("." + domain):
                return reason
        return None


def load_policy(path: "Path | None" = None) -> HostPolicy:
    path = path or Path(__file__).resolve().parent / "data" / "hosts-v1.json"
    value = json.loads(Path(path).read_bytes())
    if value.get("record_type") != POLICY:
        raise ValueError("host_policy_version")
    return HostPolicy(tuple((row["domain"].lower(), row["reason"]) for row in value["forbidden"]),
                      tuple((row["domain"].lower(), row["reason"]) for row in value.get("retired", ())))


@dataclass
class Answer:
    status: "int | None"
    headers: dict
    body: bytes
    elapsed_ms: float
    truncated: bool = False
    error_class: str = ""
    sent: bool = True
    target: str = ""
    extra: dict = field(default_factory=dict)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _kept(headers) -> dict:
    out = {}
    for name in KEPT_HEADERS:
        value = headers.get(name) if headers is not None else None
        if isinstance(value, str) and value:
            out[name] = value[:600]
    return out


def encoded(params) -> str:
    return urlencode([(str(name), str(value)) for name, value in params]) if params else ""


def target_of(request: dict) -> str:
    query = encoded(request["params"])
    return urlunsplit(("https", request["host"], request["path"], query, ""))


class Transport:
    def __init__(self, policy: HostPolicy, *, gh: str = "gh", timeout_seconds: float = 60.0,
                 maximum_bytes: int = MAXIMUM_BYTES, environment=None, opener=None, runner=None):
        self.policy = policy
        self.gh = gh
        self.timeout_seconds = timeout_seconds
        self.maximum_bytes = maximum_bytes
        self.environment = os.environ if environment is None else environment
        self.opener = opener or urllib.request.build_opener(_NoRedirect)
        self.runner = runner or run_command

    def check(self, executor, request: dict) -> None:
        """Every refusal that happens before a request exists on the wire."""
        if not executor.available:
            raise RequestRefused("executor_unavailable")
        if request.get("host") != executor.host:
            raise RequestRefused("host_not_declared_by_executor")
        reason = self.policy.refusal(request["host"])
        if reason:
            raise RequestRefused("host_forbidden")
        if not request.get("path", "").startswith("/") or ".." in request["path"].split("/"):
            raise RequestRefused("path_not_absolute")
        if executor.access == "https_post_key" and not self.environment.get(executor.key_variable):
            raise RequestRefused("key_not_in_environment")

    def send(self, executor, request: dict) -> Answer:
        self.check(executor, request)
        if executor.access == "gh_api":
            return self._gh(request)
        if executor.access == "https_get":
            return self._http(executor, request, "GET", None, {})
        if executor.access == "https_post_key":
            key = self.environment.get(executor.key_variable, "")
            body = json.dumps(request["body"], sort_keys=True, separators=(",", ":")).encode()
            return self._http(executor, request, "POST", body, {"Authorization": "Bearer " + key,
                                                                "Content-Type": "application/json"})
        raise RequestRefused("access_method_unknown")

    def _http(self, executor, request, method, data, secret_headers) -> Answer:
        target = target_of(request)
        headers = {"User-Agent": USER_AGENT, "Accept": executor.accept, **executor.static_headers, **secret_headers}
        started = time.monotonic()
        status, body, kept, error_class = None, b"", {}, ""
        try:
            with self.opener.open(urllib.request.Request(target, data=data, method=method, headers=headers),
                                  timeout=self.timeout_seconds) as answer:
                status, kept = answer.status, _kept(answer.headers)
                body = answer.read(self.maximum_bytes + 1)
        except urllib.error.HTTPError as error:
            status, kept = error.code, _kept(error.headers)
            try:
                body = error.read(self.maximum_bytes + 1)
            except OSError:
                body = b""
        except (urllib.error.URLError, OSError, ValueError) as error:
            error_class = type(error).__name__
        finally:
            secret_headers.clear()
        truncated = len(body) > self.maximum_bytes
        return Answer(status, kept, body[:self.maximum_bytes], (time.monotonic() - started) * 1000, truncated,
                      error_class, True, target)

    def graphql_licences(self, repositories) -> Answer:
        """The detected licence of up to fifty repositories in one GraphQL read through the gh login."""
        if self.policy.refusal("api.github.com"):
            raise RequestRefused("host_forbidden")
        query = licence_query(repositories)
        started = time.monotonic()
        result = self.runner((self.gh, "api", "graphql", "--include", "-f", "query=" + query),
                             timeout_seconds=self.timeout_seconds, maximum_output_bytes=self.maximum_bytes + 65536,
                             environment=passthrough_environment())
        elapsed = (time.monotonic() - started) * 1000
        if result.exit_code is None or not result.stdout:
            return Answer(None, {}, b"", elapsed, result.truncated, "no_response", True, "https://api.github.com/graphql")
        status, headers, body = parse_gh_include(result.stdout)
        return Answer(status, headers, body[:self.maximum_bytes], elapsed, result.truncated, "", True,
                      "https://api.github.com/graphql")

    def _gh(self, request) -> Answer:
        query = encoded(request["params"])
        path = request["path"].lstrip("/") + ("?" + query if query else "")
        if not (path.startswith("search/repositories?") or path.startswith("search/code?")):
            raise RequestRefused("github_path_not_allowed")
        started = time.monotonic()
        result = self.runner((self.gh, "api", "--method", "GET", "--include", path), timeout_seconds=self.timeout_seconds,
                             maximum_output_bytes=self.maximum_bytes + 65536, environment=passthrough_environment())
        elapsed = (time.monotonic() - started) * 1000
        target = "https://api.github.com/" + path
        if result.exit_code is None or not result.stdout:
            return Answer(None, {}, b"", elapsed, result.truncated, "timeout" if result.timed_out else "no_response",
                          True, target)
        status, headers, body = parse_gh_include(result.stdout)
        truncated = result.truncated or len(body) > self.maximum_bytes
        return Answer(status, headers, body[:self.maximum_bytes], elapsed, truncated, "", True, target)


_OWNER = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})\Z")
_NAME = re.compile(r"[A-Za-z0-9._-]{1,100}\Z")
GRAPHQL_BATCH = 50


def licence_query(repositories) -> str:
    """One GraphQL read of the licence GitHub detects for each named repository; names are validated, never free text."""
    if not 1 <= len(repositories) <= GRAPHQL_BATCH:
        raise RequestRefused("licence_batch_bound")
    parts = []
    for index, full_name in enumerate(repositories):
        owner, _, name = full_name.partition("/")
        if not _OWNER.fullmatch(owner) or not _NAME.fullmatch(name):
            raise RequestRefused("repository_name_invalid")
        parts.append(f'r{index}: repository(owner: "{owner}", name: "{name}") '
                     "{ nameWithOwner isPrivate isArchived licenseInfo { spdxId } }")
    return "query { " + " ".join(parts) + " rateLimit { cost remaining resetAt } }"


def parse_gh_include(raw: bytes) -> tuple:
    """Split `gh api --include` output into status, the kept headers and the body."""
    status_line, _, rest = raw.partition(b"\n")
    parts = status_line.decode("latin-1").split()
    status = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
    head, separator, body = rest.partition(b"\r\n\r\n")
    if not separator:
        head, separator, body = rest.partition(b"\n\n")
    headers = {}
    for line in head.decode("latin-1").splitlines():
        name, _, value = line.partition(":")
        name = name.strip().lower()
        if name in KEPT_HEADERS:
            headers[name] = value.strip()[:600]
    return status, headers, body if separator else b""


def github_allowance() -> dict:
    """The gh login's allowance by bucket (core, search, code_search, graphql); the rate_limit read costs none."""
    result = run_command(("gh", "api", "rate_limit"), timeout_seconds=30.0, maximum_output_bytes=65536,
                         environment=passthrough_environment())
    try:
        resources = json.loads(result.stdout)["resources"]
    except (ValueError, KeyError, TypeError):
        return {}
    return {name: {"remaining": row.get("remaining"), "limit": row.get("limit"), "reset": row.get("reset")}
            for name, row in resources.items() if name in ("core", "search", "code_search", "graphql")}
