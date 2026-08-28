"""Governed provider-backed web search for adaptive Practitioner work.

Search returns candidates, not evidence. The caller must select and fetch a
source before using it as evidence. The default adapter follows Ollama's
documented ``POST https://ollama.com/api/web_search`` contract and resolves
its credential from an environment-variable reference at the effect boundary.
"""
from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Callable

from ..loop.effect_approval import (
    ApprovalDecision, ApprovalRequest, EffectApprovalService, EffectClass,
    EffectSpec)
from ..loop.loop_contract import contract_for_code_loop
from ..loop.loop_role import LoopRelationship, LoopRole, LoopRoleIdentity
from ..loop.recursive_loop import LoopConfig, StepOutcome
from .runtime_observer import RuntimeObservationServices


OLLAMA_WEB_SEARCH_ENDPOINT = "https://ollama.com/api/web_search"


class WebSearchError(ValueError):
    """A web-search request, authority, or response violated its contract."""


@dataclass(frozen=True)
class WebSearchRequest:
    """One bounded query to a registered search provider."""

    query: str
    purpose: str
    maximum_results: int = 5

    def __post_init__(self) -> None:
        if not self.query.strip() or len(self.query) > 2_000:
            raise WebSearchError(
                "web search query must be 1 through 2,000 characters")
        if not self.purpose.strip() or len(self.purpose) > 1_000:
            raise WebSearchError(
                "web search purpose must be 1 through 1,000 characters")
        if not 1 <= self.maximum_results <= 10:
            raise WebSearchError("maximum_results must be from 1 through 10")


@dataclass(frozen=True)
class WebSearchAuthority:
    """Exact task-build authority and credential reference for one search."""

    actor_id: str
    allow_network_reads: bool
    credential_env: str = "OLLAMA_API_KEY"

    def __post_init__(self) -> None:
        if not self.actor_id.strip():
            raise WebSearchError("web search authority needs actor_id")
        if (not self.credential_env.isidentifier()
                or self.credential_env.upper() != self.credential_env):
            raise WebSearchError(
                "web search credential_env must be an uppercase identifier")


WebSearchTransport = Callable[[WebSearchRequest, str], dict]


@dataclass(frozen=True)
class WebSearchContext:
    """Active parent Loop and provider adapter for one search."""

    parent_loop: object
    transport: WebSearchTransport = field(
        default=lambda request, key: _ollama_transport(request, key),
        repr=False, compare=False)

    def __post_init__(self) -> None:
        if (self.parent_loop is None
                or not getattr(self.parent_loop, "loop_id", "")
                or getattr(self.parent_loop, "ledger", None) is None):
            raise WebSearchError("web search needs an active parent Loop")
        if not callable(self.transport):
            raise WebSearchError("web search transport must be callable")


def _effect(request: WebSearchRequest) -> EffectSpec:
    return EffectSpec(
        EffectClass.NETWORK_READ,
        "ollama_web_search",
        OLLAMA_WEB_SEARCH_ENDPOINT,
        tuple(sorted({
            "maximum_results": str(request.maximum_results),
            "purpose_digest": hashlib.sha256(
                request.purpose.encode("utf-8")).hexdigest(),
            "query_digest": hashlib.sha256(
                request.query.encode("utf-8")).hexdigest(),
        }.items())),
    )


def _approve(request, authority, parent) -> EffectApprovalService:
    if not authority.allow_network_reads:
        raise PermissionError("task-build authority does not permit web search")
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


def _ollama_transport(request: WebSearchRequest, api_key: str) -> dict:
    body = json.dumps({
        "query": request.query,
        "max_results": request.maximum_results,
    }, separators=(",", ":")).encode("utf-8")
    source = urllib.request.Request(
        OLLAMA_WEB_SEARCH_ENDPOINT,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "loop-engine/0.1 adaptive-practitioner",
        },
        method="POST")
    try:
        with urllib.request.urlopen(source, timeout=45.0) as response:
            raw = response.read(2 * 1024 * 1024 + 1)
    except urllib.error.HTTPError as exc:
        raise WebSearchError(
            f"Ollama web search returned HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise WebSearchError("Ollama web search was unavailable") from exc
    if len(raw) > 2 * 1024 * 1024:
        raise WebSearchError("web search response exceeded two MiB")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WebSearchError("web search response was not valid JSON") from exc
    return value


def _validated_results(value: object, maximum: int) -> tuple[dict, ...]:
    if not isinstance(value, dict) or set(value) != {"results"}:
        raise WebSearchError("web search response fields do not match version 1")
    candidates = value.get("results")
    if not isinstance(candidates, list) or len(candidates) > maximum:
        raise WebSearchError("web search returned an invalid result count")
    results = []
    for index, item in enumerate(candidates, 1):
        if not isinstance(item, dict):
            raise WebSearchError("web search result must be an object")
        title = str(item.get("title") or "").strip()
        url = str(item.get("url") or "").strip()
        raw_content = str(item.get("content") or "").strip()
        if (not title or len(title) > 1_000 or not url
                or len(url) > 4_000 or len(raw_content) > 256_000):
            raise WebSearchError("web search result fields are invalid")
        content = raw_content[:4_000]
        results.append({
            "rank": index,
            "title": title,
            "url": url,
            "content": content,
            "content_truncated": len(raw_content) > len(content),
            "evidence_state": "candidate_only",
        })
    return tuple(results)


def search_web(
        request: WebSearchRequest, authority: WebSearchAuthority,
        context: WebSearchContext) -> dict:
    """Search once in an Intelligence Loop and return unverified candidates."""
    parent = context.parent_loop
    _approve(request, authority, parent)
    api_key = os.environ.get(authority.credential_env, "")
    if not api_key:
        raise WebSearchError(
            f"web search credential is unavailable at env:{authority.credential_env}")
    contract = contract_for_code_loop(
        "web_search", input_roles=("web_search_request/v1",),
        output_roles=("web_search_result/v1",), effects=("network",),
        role="intelligence")
    config = LoopConfig(
        framework="custom", custom_steps=("search",),
        logical_kind="execution", replay_guarantee="evidence_equivalent",
        allowable_modes=("deterministic",),
        preferred_modes=("deterministic",),
        delegated_modes=("deterministic",), power="light",
        exit_condition="accepted_success")
    identity = LoopRoleIdentity(LoopRole.INTELLIGENCE, "intelligence.search")
    loop = parent.spawn(
        f"search public sources for {request.purpose}", config,
        contract=contract, identity=identity,
        relationship=LoopRelationship.queried_by(parent.loop_id))
    holder: dict[str, object] = {}

    def handler(active, _step, _state):
        try:
            results = _validated_results(
                context.transport(request, api_key), request.maximum_results)
            holder["value"] = {
                "record_type": "web_search_result/v1",
                "provider_id": "ollama_cloud",
                "credential_ref": f"env:{authority.credential_env}",
                "query": request.query,
                "query_digest": hashlib.sha256(
                    request.query.encode("utf-8")).hexdigest(),
                "purpose": request.purpose,
                "results": list(results),
                "result_count": len(results),
                "evidence_state": "candidate_only",
            }
            return StepOutcome("search:completed", "deterministic", 1.0)
        except Exception as exc:  # noqa: BLE001
            holder["error"] = exc
            active.ledger.record(
                loop_id=active.loop_id, event="failure.detected",
                failure_kind="web_search_failed",
                error_type=type(exc).__name__)
            return StepOutcome(
                "search:failed", "deterministic", 0.0, failed=True)

    result = loop.run(handler=handler, max_steps=1)
    if "error" in holder:
        error = holder["error"]
        if isinstance(error, (WebSearchError, PermissionError)):
            raise error
        raise WebSearchError(
            f"web search failed with {type(error).__name__}") from error
    if not result.accepted:
        raise WebSearchError("web search Loop did not reach accepted success")
    return holder["value"]  # type: ignore[return-value]


def self_test() -> dict:
    """Validate request limits and strict provider response handling."""
    tests = []
    for label, query, maximum in (
            ("empty_query", "", 5),
            ("zero_results", "sources", 0),
            ("too_many_results", "sources", 11)):
        refused = False
        try:
            WebSearchRequest(query, "contract test", maximum)
        except WebSearchError:
            refused = True
        tests.append({
            "test": f"web_search_refuses_{label}",
            "passed": refused,
            "detail": "invalid request refused before network",
        })
    strict = False
    try:
        _validated_results({"results": [], "extra": True}, 5)
    except WebSearchError:
        strict = True
    tests.append({
        "test": "web_search_response_contract_is_closed",
        "passed": strict,
        "detail": "unexpected response fields are rejected",
    })
    passed = sum(item["passed"] for item in tests)
    return {
        "record_type": "web_search_test/v1",
        "tests": tests,
        "passed": passed,
        "total": len(tests),
        "all_passed": passed == len(tests),
    }
