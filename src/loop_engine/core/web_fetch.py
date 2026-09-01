"""Governed HTTPS GET capability for adaptive Practitioner work.

The model may choose a URL, but it cannot perform the request directly. This
module validates the URL, binds one exact network-read effect, executes GET in
an Intelligence Loop, stores the complete body as an immutable artifact, and
returns the selected text plus metadata to active context.

Redirect handling is explicit. The HTTP client refuses automatic redirects:
every hop target is resolved, then validated against the same public HTTPS
policy as the requested URL, before any connection is made to it. The result
records the full hop chain. Known limit: the hostname is re-resolved by the
transport at connect time, so a validated address is not pinned to the actual
connection.
"""
from __future__ import annotations

import hashlib
import ipaddress
import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from ..loop.effect_approval import (
    ApprovalDecision, ApprovalRequest, EffectApprovalService, EffectClass,
    EffectSpec)
from ..loop.loop_contract import contract_for_code_loop
from ..loop.loop_role import LoopRelationship, LoopRole, LoopRoleIdentity
from ..loop.recursive_loop import Loop, LoopConfig, StepOutcome
from .context_artifacts import ContextArtifactManager
from .runtime_observer import RuntimeObservationServices


class WebFetchError(ValueError):
    """A web-read request or response violated the capability contract."""


_MAXIMUM_REDIRECT_HOPS = 5
_REDIRECT_STATUS_CODES = (301, 302, 303, 307, 308)


class _RefusedRedirect(urllib.request.HTTPRedirectHandler):
    """Stop urllib from following redirects; each hop is validated instead."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass(frozen=True)
class WebFetchRequest:
    """One public HTTPS resource request with optional owner limits."""

    url: str
    purpose: str
    timeout_seconds: float = 30.0
    maximum_bytes: "int | None" = None

    def __post_init__(self) -> None:
        if not self.purpose.strip():
            raise WebFetchError("web fetch needs a purpose")
        if (self.timeout_seconds <= 0
                or (self.maximum_bytes is not None
                    and self.maximum_bytes < 1)):
            raise WebFetchError("web fetch limits are invalid")
        _validate_public_https(self.url)


@dataclass(frozen=True)
class WebFetchAuthority:
    """Exact task-build authority for public network reads."""

    actor_id: str
    allow_network_reads: bool

    def __post_init__(self) -> None:
        if not self.actor_id.strip():
            raise WebFetchError("web fetch authority needs actor_id")


@dataclass(frozen=True)
class WebFetchContext:
    """Active Practitioner and artifact service for one fetch."""

    parent_loop: object
    artifacts: ContextArtifactManager

    def __post_init__(self) -> None:
        if (self.parent_loop is None
                or not getattr(self.parent_loop, "loop_id", "")
                or getattr(self.parent_loop, "ledger", None) is None):
            raise WebFetchError("web fetch needs an active parent Loop")
        if not isinstance(self.artifacts, ContextArtifactManager):
            raise WebFetchError("web fetch needs ContextArtifactManager")


def _validate_public_https(url: str) -> urllib.parse.ParseResult:
    parsed = urllib.parse.urlparse(str(url))
    if parsed.scheme != "https" or not parsed.hostname or parsed.username:
        raise WebFetchError("web fetch accepts public HTTPS URLs only")
    if parsed.port not in (None, 443):
        raise WebFetchError("web fetch accepts the standard HTTPS port only")
    hostname = parsed.hostname.lower().rstrip(".")
    if hostname in ("localhost",) or hostname.endswith((".local", ".internal")):
        raise WebFetchError("web fetch refuses local or internal hosts")
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(
            hostname, 443, type=socket.SOCK_STREAM)}
    except socket.gaierror as exc:
        raise WebFetchError(f"web host cannot be resolved: {hostname}") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise WebFetchError("web fetch refuses non-public network addresses")
    return parsed


def _effect(request: WebFetchRequest) -> EffectSpec:
    return EffectSpec(
        EffectClass.NETWORK_READ,
        "https_get",
        request.url,
        tuple(sorted({
            "maximum_bytes": str(request.maximum_bytes),
            "purpose_digest": hashlib.sha256(
                request.purpose.encode("utf-8")).hexdigest(),
            "timeout_seconds": str(request.timeout_seconds),
        }.items())),
    )


def _open_without_redirects(url: str, timeout_seconds: float):
    """Open one exact URL. Redirects surface as HTTPError, never followed."""
    handler = urllib.request.build_opener(_RefusedRedirect)
    return handler.open(
        urllib.request.Request(
            url,
            headers={"User-Agent": "loop-engine/0.1 adaptive-practitioner"},
            method="GET"),
        timeout=timeout_seconds)


def _fetch_with_validated_hops(
        request: WebFetchRequest) -> tuple[object, str, list[str]]:
    """GET the requested URL, validating and following each redirect hop.

    Automatic redirects stay disabled. When the server answers with a
    redirect status, the hop target is resolved and checked against the
    public HTTPS policy before any connection is made to it. A redirect to
    a private or non-HTTPS destination is refused before contact.
    """
    visited: list[str] = [request.url]
    url = request.url
    timeout_budget = request.timeout_seconds
    for _hop in range(_MAXIMUM_REDIRECT_HOPS + 1):
        try:
            response = _open_without_redirects(url, timeout_budget)
        except urllib.error.HTTPError as exc:
            if exc.code not in _REDIRECT_STATUS_CODES:
                raise
            if _hop >= _MAXIMUM_REDIRECT_HOPS:
                raise WebFetchError(
                    "web fetch exceeded the maximum redirect hops") from exc
            location = exc.headers.get("Location")
            if not location:
                raise WebFetchError(
                    "web fetch redirect has no Location header") from exc
            target = urllib.parse.urljoin(url, location)
            _validate_public_https(target)
            visited.append(target)
            url = target
            continue
        return response, url, visited
    raise WebFetchError("web fetch exceeded the maximum redirect hops")


def _approve(request, authority, parent) -> EffectApprovalService:
    if not authority.allow_network_reads:
        raise PermissionError("task-build authority does not permit network reads")
    runtime = RuntimeObservationServices(parent=parent, ledger=parent.ledger)
    service = EffectApprovalService(runtime=runtime)
    approval = ApprovalRequest.create(
        parent.loop_id, _effect(request), request.purpose,
        requested_by="adaptive_practitioner")
    checkpoint = service.create(approval)
    service.resume(
        checkpoint.pending, checkpoint.resume_token,
        ApprovalDecision.approve(
            approval.request_id, authority.actor_id,
            reason="User invoked task build with approved external reads."))
    service.consume(approval.request_id, approval.effect)
    return service


def fetch_web_resource(
        request: WebFetchRequest, authority: WebFetchAuthority,
        context: WebFetchContext) -> dict:
    """Fetch one exact URL in an Intelligence Loop and retain full content."""
    parent = context.parent_loop
    _approve(request, authority, parent)
    contract = contract_for_code_loop(
        "web_fetch", input_roles=("web_fetch_request/v1",),
        output_roles=("web_fetch_result/v1",), effects=("network",),
        role="intelligence")
    config = LoopConfig(
        framework="custom", custom_steps=("fetch",),
        logical_kind="execution", replay_guarantee="evidence_equivalent",
        allowable_modes=("deterministic",),
        preferred_modes=("deterministic",),
        delegated_modes=("deterministic",), power="light",
        exit_condition="accepted_success")
    identity = LoopRoleIdentity(LoopRole.INTELLIGENCE, "intelligence.search")
    loop = parent.spawn(
        f"fetch public resource for {request.purpose}", config,
        contract=contract, identity=identity,
        relationship=LoopRelationship.queried_by(parent.loop_id))
    holder: dict[str, object] = {}

    def handler(active, _step, _state):
        try:
            response, final_url, hop_chain = _fetch_with_validated_hops(
                request)
            with response:
                declared = response.headers.get("Content-Length")
                if (request.maximum_bytes is not None and declared
                        and int(declared) > request.maximum_bytes):
                    raise WebFetchError("web resource exceeds maximum_bytes")
                body = (response.read() if request.maximum_bytes is None
                        else response.read(request.maximum_bytes + 1))
                if (request.maximum_bytes is not None
                        and len(body) > request.maximum_bytes):
                    raise WebFetchError("web resource exceeds maximum_bytes")
                media_type = response.headers.get_content_type()
                charset = response.headers.get_content_charset() or "utf-8"
            artifact = context.artifacts.store.put(
                body, media_type=media_type, encoding=charset,
                artifact_kind="web_source_snapshot")
            try:
                text = body.decode(charset, errors="replace")
            except LookupError:
                text = body.decode("utf-8", errors="replace")
            holder["value"] = {
                "record_type": "web_fetch_result/v1",
                "requested_url": request.url,
                "final_url": final_url,
                "redirect_hops": hop_chain,
                "media_type": media_type,
                "byte_count": len(body),
                "sha256": artifact.digest,
                "artifact_ref": artifact.to_dict(),
                "text": text,
                "text_truncated": False,
            }
            return StepOutcome("fetch:completed", "deterministic", 1.0)
        except Exception as exc:  # noqa: BLE001
            holder["error"] = exc
            active.ledger.record(
                loop_id=active.loop_id, event="failure.detected",
                failure_kind="web_fetch_failed", error_type=type(exc).__name__)
            return StepOutcome(
                "fetch:failed", "deterministic", 0.0, failed=True)

    result = loop.run(handler=handler, max_steps=1)
    if "error" in holder:
        error = holder["error"]
        if isinstance(error, WebFetchError):
            raise error
        raise WebFetchError(
            f"web fetch failed with {type(error).__name__}") from error
    if not result.accepted:
        raise WebFetchError("web fetch Loop did not reach accepted success")
    return holder["value"]  # type: ignore[return-value]


def self_test() -> dict:
    """Refuse unsafe destinations without contacting any network."""
    tests = []
    for label, url in (
            ("plain_http", "http://example.com/data"),
            ("localhost", "https://localhost/data"),
            ("private_ipv4", "https://127.0.0.1/data"),
            ("userinfo", "https://user@example.com/data")):
        refused = False
        try:
            WebFetchRequest(url, "test refusal")
        except WebFetchError:
            refused = True
        tests.append({
            "test": f"web_fetch_refuses_{label}",
            "passed": refused,
            "detail": url,
        })
    redirect_refused = False
    try:
        _validate_public_https("http://redirect.target/data")
    except WebFetchError:
        redirect_refused = True
    tests.append({
        "test": "web_fetch_refuses_http_redirect_target",
        "passed": redirect_refused,
        "detail": "a redirect Location downgrading to http is refused",
    })
    private_redirect_refused = False
    try:
        _validate_public_https("https://192.168.1.10/data")
    except WebFetchError:
        private_redirect_refused = True
    tests.append({
        "test": "web_fetch_refuses_private_redirect_target",
        "passed": private_redirect_refused,
        "detail": "a redirect Location naming a private network address is"
                  " refused before any connection",
    })
    relative = urllib.parse.urljoin(
        "https://example.com/a/b", "next/page")
    tests.append({
        "test": "web_fetch_resolves_relative_redirect_targets",
        "passed": relative == "https://example.com/a/next/page",
        "detail": relative,
    })
    import email.message
    import sys
    import unittest.mock

    _self = sys.modules[__name__]

    def _raise_redirect(url, target):
        headers = email.message.Message()
        headers["Location"] = target
        raise urllib.error.HTTPError(url, 302, "Found", headers, None)

    hop_exhaustion_refused = False
    hop_exhaustion_detail = ""
    with unittest.mock.patch.object(
            _self, "_open_without_redirects",
            side_effect=lambda url, timeout: _raise_redirect(
                url, "https://example.com/next")):
        try:
            _fetch_with_validated_hops(WebFetchRequest(
                "https://example.com/start", "test hop bound"))
        except WebFetchError as exc:
            hop_exhaustion_refused = "exceeded the maximum redirect" in str(
                exc)
            hop_exhaustion_detail = str(exc)
    tests.append({
        "test": "web_fetch_bounds_redirect_hops",
        "passed": hop_exhaustion_refused,
        "detail": hop_exhaustion_detail or "an endless redirect chain is"
                  " refused without contacting any network",
    })
    private_hop_refused = False
    private_hop_detail = ""
    with unittest.mock.patch.object(
            _self, "_open_without_redirects",
            side_effect=lambda url, timeout: _raise_redirect(
                url, "https://192.168.1.10/data")):
        try:
            _fetch_with_validated_hops(WebFetchRequest(
                "https://example.com/start", "test private hop"))
        except WebFetchError as exc:
            private_hop_refused = "non-public network" in str(exc)
            private_hop_detail = str(exc)
    tests.append({
        "test": "web_fetch_refuses_private_redirect_before_contact",
        "passed": private_hop_refused,
        "detail": private_hop_detail or "the hop target is validated before"
                  " any connection",
    })
    passed = sum(item["passed"] for item in tests)
    return {
        "record_type": "web_fetch_test/v1",
        "tests": tests,
        "passed": passed,
        "total": len(tests),
        "all_passed": passed == len(tests),
    }
