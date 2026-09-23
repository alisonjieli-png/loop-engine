"""Read-only GitHub requests through the existing gh login, from an allow list.

The reader sends GET requests for exactly six kinds of resource: a git tree
at a full commit, a file's contents at a full commit, a repository licence
(at a full commit or at the default branch), a repository's public
description, the commit a branch points at (for curation only) and the rate
limit. Any other
request is refused before a process starts, so the broad scopes of the
login can never be used to change anything. The token never passes through
this module: gh reads it from its own store, and only the status, the
body and the allowance headers are read back. Every request is admitted by
the run's budget and recorded in the run's request log.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from .https_transport import unquote_part
from .processes import passthrough_environment, run_command
from .record_rules import now_utc
from .request_log import RequestBudget, RequestLog, RequestObservation

GITHUB_HOST = "api.github.com"
_OWNER = r"[A-Za-z0-9][A-Za-z0-9-]{0,38}"
_REPO = r"[A-Za-z0-9._-]{1,100}"
_COMMIT = r"[0-9a-f]{40}"
_ALLOWED = (
    re.compile(rf"repos/{_OWNER}/{_REPO}/git/trees/{_COMMIT}\?recursive=1\Z"),
    re.compile(rf"repos/{_OWNER}/{_REPO}/license\?ref={_COMMIT}\Z"),
    re.compile(rf"repos/{_OWNER}/{_REPO}/license\Z"),
    re.compile(rf"repos/{_OWNER}/{_REPO}\Z"),
    re.compile(rf"repos/{_OWNER}/{_REPO}/commits/[A-Za-z0-9._-]{{1,100}}\Z"),
    re.compile(rf"repos/{_OWNER}/{_REPO}/contents/[A-Za-z0-9._~%/+@=-]{{1,1024}}\?ref={_COMMIT}\Z"),
    re.compile(r"rate_limit\Z"),
)
_STATUS = re.compile(rb"HTTP/[0-9.]+ ([0-9]{3})")


class ReadOnlyRequestRefused(ValueError):
    """A GitHub request outside the read-only allow list; no process was started."""


@dataclass(frozen=True)
class GitHubResponse:
    status: "int | None"
    body: bytes
    allowance_remaining: "int | None" = None
    allowance_reset: "int | None" = None


def allowed_request(path: str) -> bool:
    """True only for a read of one of the six allowed resources, with no parent step."""
    if type(path) is not str or not any(pattern.match(path) for pattern in _ALLOWED):
        return False
    target = unquote_part(path.split("?", 1)[0])
    return ".." not in target.split("/") and "\x00" not in target


def parse_included_response(raw: bytes) -> GitHubResponse:
    """Split gh's status line and headers from the body; keep only status and allowance."""
    status_line, _, rest = raw.partition(b"\n")
    match = _STATUS.match(status_line.strip())
    headers, separator, body = rest.partition(b"\n\n")
    if not separator:
        headers, separator, body = rest.partition(b"\r\n\r\n")
    remaining = reset = None
    for line in headers.splitlines():
        name, _, value = line.decode("latin-1").partition(":")
        name = name.strip().lower()
        if name == "x-ratelimit-remaining" and value.strip().isdigit():
            remaining = int(value.strip())
        elif name == "x-ratelimit-reset" and value.strip().isdigit():
            reset = int(value.strip())
    return GitHubResponse(int(match.group(1)) if match else None, body if separator else b"",
                          remaining, reset)


class GhCliReader:
    """GET requests through gh api, admitted by a budget and recorded in a log."""

    transport = "gh_api"

    def __init__(self, budget: RequestBudget, log: RequestLog, *, timeout_seconds: float = 90.0,
                 maximum_bytes: int = 16 * 1024 * 1024, gh: str = "gh") -> None:
        self.budget, self.log = budget, log
        self.timeout_seconds, self.maximum_bytes, self.gh = timeout_seconds, maximum_bytes, gh

    def get(self, path: str) -> GitHubResponse:
        if not allowed_request(path):
            raise ReadOnlyRequestRefused(f"not an allowed read: {path[:120]}")
        response = self._send(path)
        if response.status in (403, 429) and response.allowance_remaining == 0:
            self.budget.respect_allowance(0, response.allowance_reset, "GitHub")
            response = self._send(path)
        return response

    def _send(self, path: str) -> GitHubResponse:
        self.budget.admit()
        started = now_utc()
        result = run_command((self.gh, "api", "--method", "GET", "--include", path),
                             timeout_seconds=self.timeout_seconds,
                             maximum_output_bytes=self.maximum_bytes,
                             environment=passthrough_environment())
        if result.exit_code is None or result.truncated or not result.stdout:
            self.log.record(RequestObservation(
                self.transport, GITHUB_HOST, path, None, None, started, result.elapsed_ms, "transport_error",
                error_class="timeout" if result.timed_out else
                "response_too_large" if result.truncated else "no_response"))
            return GitHubResponse(None, b"")
        response = parse_included_response(result.stdout)
        outcome = ("ok" if response.status == 200 else "not_found" if response.status == 404
                   else "rate_limited" if response.status in (403, 429)
                   and response.allowance_remaining == 0 else "http_error")
        self.log.record(RequestObservation(
            self.transport, GITHUB_HOST, path, response.status, response.body, started, result.elapsed_ms,
            outcome, allowance_remaining=response.allowance_remaining))
        if path != "rate_limit":
            self.budget.respect_allowance(response.allowance_remaining, response.allowance_reset, "GitHub")
        return response
