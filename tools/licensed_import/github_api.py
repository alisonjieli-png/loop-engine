"""Read-only GitHub requests through the existing gh login: search and two GraphQL reads.

The library ingestion component's reader (`GhCliReader`) already covers the
REST reads this import needs as a fallback: a tree at a commit, a file's
contents at a commit and a repository licence. This module adds three
reads it does not have, each from a fixed shape:

```text
Read-only GitHub requests of the licensed import
├── code search: search/code, a query of allowlisted qualifiers, 100 results a page, pages 1 to 10
├── repository search: search/repositories, a query of allowlisted qualifiers, sorted by stars
└── GraphQL, from two templates only
    ├── repository metadata for up to 100 repositories: head commit, licence, fork, archive, size
    └── the text of up to 100 blobs of one repository, by object identity
```

A GraphQL request is sent only for a `ReadQuery` built by one of the two
templates; any other text, and any text that names a mutation or a
subscription, is refused before a process starts. Each kind of request has
its own budget, because GitHub gives each its own allowance (code search
ten a minute, search thirty a minute, GraphQL and REST five thousand an
hour). Every request is recorded in the run's request log with its outcome
and the provider's remaining allowance; no header other than the allowance
and no token is kept.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass

from loop_engine.core.library_ingestion.github_reader import GITHUB_HOST, parse_included_response
from loop_engine.core.library_ingestion.record_rules import now_utc
from loop_engine.core.library_ingestion.request_log import RequestBudget, RequestLog, RequestObservation

from .processes import gh_environment, run

OWNER = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}\Z")
NAME = re.compile(r"[A-Za-z0-9._-]{1,100}\Z")
OID = re.compile(r"[0-9a-f]{40}\Z")
#: Qualifiers a code search may use, and those a repository search may use.
CODE_QUALIFIERS = frozenset({"filename", "path", "extension", "size", "language", "in", "fork", "repo", "user", "org"})
REPOSITORY_QUALIFIERS = frozenset({"topic", "created", "pushed", "stars", "language", "fork", "archived", "is",
                                   "in", "size", "license", "user", "org"})
_QUERY_TERM = re.compile(r"(?:([a-z]+):)?([A-Za-z0-9_.*/@+<>=-]{1,120})\Z")
MAXIMUM_PAGE = 10
PAGE_SIZE = 100
MAXIMUM_BATCH = 100
CODE_SEARCH, SEARCH, GRAPHQL = "code_search", "search", "graphql"
_FORBIDDEN_OPERATIONS = re.compile(r"\b(?:mutation|subscription)\b", re.I)
_METADATA_FIELDS = ("nameWithOwner isFork isArchived isPrivate isEmpty stargazerCount diskUsage pushedAt "
                    "licenseInfo { spdxId } defaultBranchRef { name target { oid } } parent { nameWithOwner }")
_BLOB_FIELDS = "... on Blob { oid byteSize isBinary isTruncated text }"


class ReadRefused(ValueError):
    """A request outside the fixed read-only shapes; no process was started."""


@dataclass(frozen=True)
class ReadQuery:
    """GraphQL text built by one of this module's two templates, with the template's name."""

    text: str
    template: str


def search_query(terms, allowed=CODE_QUALIFIERS) -> str:
    """One search query from exact terms, each a plain word or an allowlisted qualifier."""
    words = []
    for term in terms:
        match = _QUERY_TERM.match(str(term))
        if match is None or (match.group(1) is not None and match.group(1) not in allowed):
            raise ReadRefused(f"not an allowed search term: {str(term)[:60]}")
        words.append(str(term))
    if not words or len(" ".join(words)) > 256:
        raise ReadRefused("a search query holds one to 256 characters of allowed terms")
    return " ".join(words)


def _owner_name(repository: str) -> tuple:
    owner, _, name = str(repository).partition("/")
    if not OWNER.match(owner) or not NAME.match(name) or name in (".", ".."):
        raise ReadRefused(f"not a repository name: {str(repository)[:80]}")
    return owner, name


def metadata_query(repositories) -> ReadQuery:
    """Head commit, licence, fork, archive state and size of up to 100 repositories in one read."""
    repositories = list(repositories)
    if not 1 <= len(repositories) <= MAXIMUM_BATCH:
        raise ReadRefused(f"a metadata read names 1 to {MAXIMUM_BATCH} repositories")
    parts = []
    for index, repository in enumerate(repositories):
        owner, name = _owner_name(repository)
        parts.append(f'r{index}: repository(owner: "{owner}", name: "{name}") {{ {_METADATA_FIELDS} }}')
    return ReadQuery("query { rateLimit { cost remaining resetAt } " + " ".join(parts) + " }", "repository_metadata")


def blob_query(repository: str, oids) -> ReadQuery:
    """The text of up to 100 blobs of one repository, by object identity."""
    owner, name = _owner_name(repository)
    oids = list(oids)
    if not 1 <= len(oids) <= MAXIMUM_BATCH or any(not OID.match(str(oid)) for oid in oids):
        raise ReadRefused(f"a blob read names 1 to {MAXIMUM_BATCH} full object identities")
    parts = " ".join(f'b{index}: object(oid: "{oid}") {{ {_BLOB_FIELDS} }}' for index, oid in enumerate(oids))
    return ReadQuery(f'query {{ rateLimit {{ cost remaining resetAt }} r: repository(owner: "{owner}", '
                     f'name: "{name}") {{ {parts} }} }}', "blob_text")


def _check_read_query(query) -> str:
    if not isinstance(query, ReadQuery) or query.template not in ("repository_metadata", "blob_text"):
        raise ReadRefused("GraphQL is read only through this module's templates")
    if not query.text.startswith("query {") or _FORBIDDEN_OPERATIONS.search(query.text):
        raise ReadRefused("a GraphQL read is a query and never a mutation or a subscription")
    return query.text


@dataclass
class ApiBudgets:
    """One budget per GitHub allowance, so one allowance running low never stops the others."""

    code_search: RequestBudget
    search: RequestBudget
    graphql: RequestBudget


class GitHubApi:
    """Search and GraphQL reads through gh, each admitted by its budget and recorded."""

    transport = "gh_api"

    def __init__(self, budgets: ApiBudgets, log: RequestLog, *, gh: str = "gh", timeout_seconds: float = 120.0,
                 maximum_bytes: int = 96 * 1024 * 1024, clock=time.time, sleep=time.sleep) -> None:
        self.budgets, self.log, self.gh = budgets, log, gh
        self.timeout_seconds, self.maximum_bytes = timeout_seconds, maximum_bytes
        self.clock, self.sleep = clock, sleep

    def code_search(self, query: str, page: int) -> dict:
        return self._search("search/code", query, page, CODE_QUALIFIERS, self.budgets.code_search, ())

    def repository_search(self, query: str, page: int) -> dict:
        return self._search("search/repositories", query, page, REPOSITORY_QUALIFIERS, self.budgets.search,
                            ("-f", "sort=stars", "-f", "order=desc"))

    def _search(self, endpoint, query, page, allowed, budget, extra) -> dict:
        search_query(query.split(" "), allowed)
        if type(page) is not int or not 1 <= page <= MAXIMUM_PAGE:
            raise ReadRefused(f"a search page is from 1 to {MAXIMUM_PAGE}")
        argv = (self.gh, "api", "--method", "GET", "--include", endpoint, "-f", f"q={query}",
                "-f", f"per_page={PAGE_SIZE}", "-f", f"page={page}", *extra)
        return self._send(argv, f"{endpoint}?q={query}&page={page}", budget)

    def graphql(self, query: ReadQuery) -> dict:
        text = _check_read_query(query)
        argv = (self.gh, "api", "--include", "graphql", "-f", f"query={text}")
        return self._send(argv, f"graphql:{query.template}", self.budgets.graphql)

    def _send(self, argv, target: str, budget: RequestBudget) -> dict:
        for _attempt in range(2):
            budget.admit()
            started = now_utc()
            result = run(argv, timeout_seconds=self.timeout_seconds, maximum_output_bytes=self.maximum_bytes,
                         environment=gh_environment())
            if result.exit_code is None or result.truncated or not result.stdout:
                self.log.record(RequestObservation(
                    self.transport, GITHUB_HOST, target, None, None, started, result.elapsed_ms, "transport_error",
                    error_class="timeout" if result.timed_out else
                    "response_too_large" if result.truncated else "no_response"))
                return {"status": None, "body": None}
            response = parse_included_response(result.stdout)
            limited = response.status in (403, 429)
            outcome = ("ok" if response.status == 200 else "rate_limited" if limited
                       else "not_found" if response.status == 404 else "http_error")
            self.log.record(RequestObservation(self.transport, GITHUB_HOST, target, response.status, response.body,
                                               started, result.elapsed_ms, outcome,
                                               allowance_remaining=response.allowance_remaining))
            if limited:
                # A primary allowance names its reset; a secondary limit asks for a minute.
                wait = (max(0.0, float(response.allowance_reset) - self.clock()) + 1.0
                        if response.allowance_remaining == 0 and response.allowance_reset else 61.0)
                budget.pause(wait, f"GitHub {target.split('?')[0]} asked to wait")
                continue
            budget.respect_allowance(response.allowance_remaining, response.allowance_reset, "GitHub")
            try:
                body = json.loads(response.body) if response.body else None
            except ValueError:
                body = None
            return {"status": response.status, "body": body}
        return {"status": 429, "body": None}
