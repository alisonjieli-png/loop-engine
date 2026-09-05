"""Passive exact-request token bounds for the existing model gateway.

This module owns no runtime, store, token estimator, provider call or budget
counter. An effect-free host resolver supplies a qualified upper bound for the
complete physical request. The gateway owns request construction and its
digest; the session owns atomic reservation and reconciliation.

A bound covers every provider-reported input and output token, including
framing, cached-input accounting and reasoning where the provider counts them.
Its provenance is a host assertion, not independent provider qualification.
Unknown bounds fail closed. The exact supported output maximum is never
reduced to fit a budget. Unbounded runs need not call this strict preflight.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Protocol

_ACCOUNTING_SCOPE = "all_provider_reported_input_and_output/v1"


class TokenBoundFailureCode(str, Enum):
    """Closed, content-free failures before a physical provider dispatch."""

    UNAVAILABLE = "token_bound_unavailable"
    INVALID = "token_bound_invalid"
    INSUFFICIENT = "token_budget_insufficient_preflight"


_FAILURE_MESSAGES = {
    TokenBoundFailureCode.UNAVAILABLE:
        "a qualified exact-request token bound is unavailable",
    TokenBoundFailureCode.INVALID:
        "the token-bound contract or its exact request binding is invalid",
    TokenBoundFailureCode.INSUFFICIENT:
        "the complete token reservation exceeds the remaining budget",
}


class TokenBoundError(ValueError):
    """Safe refusal with a stable code and no provider or prompt text."""

    def __init__(self, code: TokenBoundFailureCode | str):
        self.code = TokenBoundFailureCode(code).value
        super().__init__(_FAILURE_MESSAGES[TokenBoundFailureCode(self.code)])


def _bounded_identifier(value: object, maximum: int) -> None:
    if (type(value) is not str or not value or len(value) > maximum
            or any(character.isspace() or ord(character) < 32
                   or ord(character) == 127 for character in value)):
        raise TokenBoundError(TokenBoundFailureCode.INVALID)
    try:
        value.encode("utf-8")
    except UnicodeError:
        raise TokenBoundError(TokenBoundFailureCode.INVALID) from None


def _token_count(value: object, *, positive: bool = False) -> None:
    if type(value) is not int or value < (1 if positive else 0):
        raise TokenBoundError(TokenBoundFailureCode.INVALID)


def _identity(record) -> tuple[str, str, str, str]:
    _bounded_identifier(record.provider_id, 192)
    _bounded_identifier(record.model_id, 512)
    _bounded_identifier(record.route_name, 192)
    digest = record.provider_request_digest
    if (type(digest) is not str or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)):
        raise TokenBoundError(TokenBoundFailureCode.INVALID)
    return (record.provider_id, record.model_id, record.route_name, digest)


@dataclass(frozen=True)
class TokenBoundRequest:
    """Exact physical request presented to an effect-free host resolver.

    The gateway must derive provider_request_digest from its final physical
    packet and settings. This helper cannot certify an adapter's wire encoder
    or a caller-supplied digest. Prompt and system bodies are never summaries.
    """

    provider_id: str
    model_id: str
    route_name: str
    provider_request_digest: str
    prompt: str = field(repr=False)
    system: str = field(repr=False)
    maximum_output_tokens: int

    def __post_init__(self) -> None:
        _identity(self)
        _token_count(self.maximum_output_tokens, positive=True)
        if (type(self.prompt) is not str or not self.prompt.strip()
                or type(self.system) is not str):
            raise TokenBoundError(TokenBoundFailureCode.INVALID)
        try:
            self.prompt.encode("utf-8")
            self.system.encode("utf-8")
        except UnicodeError:
            raise TokenBoundError(TokenBoundFailureCode.INVALID) from None


@dataclass(frozen=True)
class ProviderTokenBound:
    """Host-qualified upper bounds, pinned to one exact physical request.

    Source fields must be non-secret references, never provider responses or
    private text. They are hashed in safe_summary, not exported verbatim.
    maximum_output_tokens is the exact approved wire allocation, including
    reasoning if charged as output. Without an explicit Loop allocation the
    gateway requests the full supported maximum. Capacity and allocation are
    separate facts; this helper binds the latter for accounting. Providers
    whose accounting cannot be bounded this way are unsupported for a strict
    total-token ceiling until a qualified counting contract is supplied.
    """

    provider_id: str
    model_id: str
    route_name: str
    provider_request_digest: str
    maximum_input_tokens: int
    maximum_output_tokens: int
    source_ref: str = field(repr=False)
    source_version: str = field(repr=False)
    accounting_scope: str = _ACCOUNTING_SCOPE
    record_type: str = "provider_token_bound/v1"

    def __post_init__(self) -> None:
        _identity(self)
        _token_count(self.maximum_input_tokens)
        _token_count(self.maximum_output_tokens, positive=True)
        _bounded_identifier(self.source_ref, 256)
        _bounded_identifier(self.source_version, 64)
        if any(marker in value.lower() for value in (
                self.source_ref, self.source_version) for marker in (
                    "authorization:", "api_key=", "apikey=", "access_token=",
                    "password=", "secret=", "bearer:")):
            raise TokenBoundError(TokenBoundFailureCode.INVALID)
        if (type(self.accounting_scope) is not str
                or self.accounting_scope != _ACCOUNTING_SCOPE
                or type(self.record_type) is not str
                or self.record_type != "provider_token_bound/v1"):
            raise TokenBoundError(TokenBoundFailureCode.INVALID)

    @property
    def maximum_total_tokens(self) -> int:
        return self.maximum_input_tokens + self.maximum_output_tokens

    def safe_summary(self) -> dict:
        provenance = json.dumps(
            [self.source_ref, self.source_version],
            ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        return {
            "record_type": self.record_type,
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "route_name": self.route_name,
            "provider_request_digest": self.provider_request_digest,
            "maximum_input_tokens": self.maximum_input_tokens,
            "maximum_output_tokens": self.maximum_output_tokens,
            "maximum_total_tokens": self.maximum_total_tokens,
            "accounting_scope": self.accounting_scope,
            "source_identity_digest": hashlib.sha256(provenance).hexdigest(),
            "qualification": "host_asserted_not_independently_proven_here",
        }


class ProviderTokenBoundResolver(Protocol):
    """Trusted, effect-free source of bounds; never a hidden provider call."""

    def resolve(self, request: TokenBoundRequest) -> ProviderTokenBound | None: ...


def prepare_token_reservation(
        request: TokenBoundRequest,
        resolver: ProviderTokenBoundResolver | None,
        remaining_tokens: int) -> ProviderTokenBound:
    """Validate a bound and budget fit, without reserving or spending tokens.

    The returned bound is input to the caller's atomic reservation operation,
    not a reservation confirmation or permission. Repeat for every physical route
    attempt; a previously accepted digest cannot authorize a changed packet.
    """
    if type(request) is not TokenBoundRequest:
        raise TokenBoundError(TokenBoundFailureCode.INVALID)
    request = replace(request)
    _token_count(remaining_tokens)
    expected_identity = _identity(request)
    expected_output = request.maximum_output_tokens
    if resolver is None:
        raise TokenBoundError(TokenBoundFailureCode.UNAVAILABLE)
    try:
        resolve = getattr(resolver, "resolve", None)
        if not callable(resolve):
            raise TokenBoundError(TokenBoundFailureCode.UNAVAILABLE)
        bound = resolve(request)
    except TokenBoundError as exc:
        code = (exc.code if type(exc.code) is str
                and exc.code in {item.value for item in TokenBoundFailureCode}
                else TokenBoundFailureCode.INVALID)
        raise TokenBoundError(code) from None
    except Exception:  # noqa: BLE001 - Host failure text must never be exported.
        raise TokenBoundError(TokenBoundFailureCode.INVALID) from None
    if bound is None:
        raise TokenBoundError(TokenBoundFailureCode.UNAVAILABLE)
    if type(bound) is not ProviderTokenBound:
        raise TokenBoundError(TokenBoundFailureCode.INVALID)
    bound = replace(bound)
    if (_identity(bound) != expected_identity
            or bound.maximum_output_tokens != expected_output):
        raise TokenBoundError(TokenBoundFailureCode.INVALID)
    if bound.maximum_total_tokens > remaining_tokens:
        raise TokenBoundError(TokenBoundFailureCode.INSUFFICIENT)
    return bound


def self_test() -> dict:
    """Check passive preflight only, with no provider, network or storage."""
    tests = []

    def check(name, passed):
        tests.append({"test": name, "passed": bool(passed)})

    def failure(operation, code):
        try:
            operation()
        except TokenBoundError as exc:
            return exc.code == code.value
        return False

    request = TokenBoundRequest(
        "fixture.provider", "fixture/model", "fixture.route", "a" * 64,
        "PRIVATE_PROMPT_MARKER", "PRIVATE_SYSTEM_MARKER", 10)
    bound = ProviderTokenBound(
        request.provider_id, request.model_id, request.route_name,
        request.provider_request_digest, 6, 10,
        "source:PRIVATE_SOURCE_MARKER", "1.0.0")

    class Resolver:
        def __init__(self, value):
            self.value = value
            self.requests = []

        def resolve(self, selected):
            self.requests.append(selected)
            return self.value

    resolver = Resolver(bound)
    exact = prepare_token_reservation(request, resolver, 16)
    check("exact_budget_fit_keeps_full_output_and_source_identity",
          exact == bound and exact.maximum_total_tokens == 16
          and exact.maximum_output_tokens == 10
          and resolver.requests == [request])
    check("spare_budget_does_not_change_the_bound",
          prepare_token_reservation(request, resolver, 100) == bound)
    check("one_token_short_refuses_without_lowering_output",
          failure(lambda: prepare_token_reservation(request, resolver, 15),
                  TokenBoundFailureCode.INSUFFICIENT)
          and bound.maximum_output_tokens == request.maximum_output_tokens == 10)
    check("zero_remaining_refuses_positive_output_reservation",
          failure(lambda: prepare_token_reservation(request, resolver, 0),
                  TokenBoundFailureCode.INSUFFICIENT))
    check("zero_input_is_admissible_when_the_host_can_bound_it",
          prepare_token_reservation(
              request, Resolver(replace(bound, maximum_input_tokens=0)),
              10).maximum_total_tokens == 10)
    for name, value in (("absent_resolver", None), ("missing_method", object()),
                        ("unknown_bound", Resolver(None))):
        check(name + "_fails_closed", failure(
            lambda value=value: prepare_token_reservation(request, value, 100),
            TokenBoundFailureCode.UNAVAILABLE))
    check("untyped_bound_fails_closed", failure(
        lambda: prepare_token_reservation(request, Resolver({"tokens": 16}), 100),
        TokenBoundFailureCode.INVALID))
    for name, changed in (("provider_id", "other"), ("model_id", "other"),
                          ("route_name", "other"),
                          ("provider_request_digest", "b" * 64),
                          ("maximum_output_tokens", 9),
                          ("maximum_output_tokens", 11)):
        check("bound_mismatch_" + name + "_" + str(changed)[:8], failure(
            lambda name=name, changed=changed: prepare_token_reservation(
                request, Resolver(replace(bound, **{name: changed})), 100),
            TokenBoundFailureCode.INVALID))
    check("changed_request_cannot_reuse_an_old_digest_bound", failure(
        lambda: prepare_token_reservation(replace(
            request, provider_request_digest="c" * 64, prompt="changed"),
            resolver, 100), TokenBoundFailureCode.INVALID))
    for field_name in ("maximum_input_tokens", "maximum_output_tokens"):
        check(field_name + "_rejects_boolean_negative_fractional_and_nonfinite",
              all(failure(lambda value=value, field_name=field_name:
                  replace(bound, **{field_name: value}),
                  TokenBoundFailureCode.INVALID)
                  for value in (True, False, -1, 1.5, float("nan"), float("inf"))))
    check("zero_output_maximum_is_invalid", failure(
        lambda: replace(bound, maximum_output_tokens=0),
        TokenBoundFailureCode.INVALID))
    before = len(resolver.requests)
    check("invalid_remaining_budget_is_refused_before_resolver",
          all(failure(lambda value=value: prepare_token_reservation(
              request, resolver, value), TokenBoundFailureCode.INVALID)
              for value in (None, True, False, -1, 1.5, float("nan"), float("inf")))
          and len(resolver.requests) == before)
    check("missing_or_unbounded_provenance_is_invalid",
          all(failure(lambda name=name, value=value:
              replace(bound, **{name: value}), TokenBoundFailureCode.INVALID)
              for name, value in (("source_ref", ""), ("source_version", ""),
                                  ("source_ref", "x" * 257),
                                  ("source_version", "x" * 65),
                                  ("source_ref", "free form text"),
                                  ("source_ref", "api_key=PRIVATE"),
                                  ("source_version", "secret=PRIVATE"))))
    check("unknown_accounting_scope_is_invalid", failure(
        lambda: replace(bound, accounting_scope="visible_output_only"),
        TokenBoundFailureCode.INVALID))
    check("unknown_record_version_is_invalid", failure(
        lambda: replace(bound, record_type="provider_token_bound/v2"),
        TokenBoundFailureCode.INVALID))
    check("malformed_identity_and_request_text_are_invalid",
          all(failure(lambda name=name, value=value:
              replace(request, **{name: value}), TokenBoundFailureCode.INVALID)
              for name, value in (("provider_id", ""), ("model_id", "bad model"),
                                  ("route_name", 1),
                                  ("provider_request_digest", "Z" * 64),
                                  ("prompt", ""), ("system", object()),
                                  ("prompt", "\ud800"),
                                  ("maximum_output_tokens", True))))

    class RaisingResolver:
        def resolve(self, selected):
            raise RuntimeError("PRIVATE_RESOLVER_ERROR_MARKER")

    try:
        prepare_token_reservation(request, RaisingResolver(), 100)
    except TokenBoundError as exc:
        check("resolver_errors_are_content_free_and_fail_closed",
              exc.code == TokenBoundFailureCode.INVALID.value
              and "PRIVATE_RESOLVER" not in str(exc)
              and exc.__suppress_context__)
    else:
        check("resolver_errors_are_content_free_and_fail_closed", False)

    class TypedRaisingResolver:
        def resolve(self, selected):
            error = TokenBoundError(TokenBoundFailureCode.UNAVAILABLE)
            error.args = ("PRIVATE_TYPED_RESOLVER_MARKER",)
            raise error

    try:
        prepare_token_reservation(request, TypedRaisingResolver(), 100)
    except TokenBoundError as exc:
        check("typed_resolver_failures_are_renormalized_without_private_text",
              exc.code == TokenBoundFailureCode.UNAVAILABLE.value
              and "PRIVATE_TYPED" not in str(exc) and exc.__suppress_context__)
    else:
        check("typed_resolver_failures_are_renormalized_without_private_text", False)
    summary = bound.safe_summary()
    summary["maximum_output_tokens"] = 1
    serialized = json.dumps(bound.safe_summary()) + repr(bound) + repr(request)
    check("safe_summary_and_repr_exclude_prompt_and_source_bodies",
          all(marker not in serialized for marker in (
              "PRIVATE_PROMPT_MARKER", "PRIVATE_SYSTEM_MARKER", "PRIVATE_SOURCE_MARKER")))
    check("summary_mutation_cannot_change_frozen_bound",
          bound.maximum_output_tokens == 10
          and bound.safe_summary()["maximum_output_tokens"] == 10)
    from dataclasses import FrozenInstanceError
    try:
        bound.maximum_input_tokens = 0
    except FrozenInstanceError:
        check("bound_is_frozen", True)
    else:
        check("bound_is_frozen", False)
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "model_token_preflight_self_test/v1", "tests": tests,
            "passed": passed, "total": len(tests), "all_passed": passed == len(tests),
            "provider_calls": 0}


__all__ = (
    "ProviderTokenBound", "ProviderTokenBoundResolver", "TokenBoundError",
    "TokenBoundFailureCode", "TokenBoundRequest", "prepare_token_reservation",
)
