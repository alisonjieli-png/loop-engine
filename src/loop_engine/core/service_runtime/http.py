"""Remote web and Streamable HTTP adapters over the durable service domain.

The application delegates tenant, qualification, disclosure and usage decisions
to the existing Python authority. It owns bounded transport, exact protocol
selection, safe errors and separately authorized downloads, not another runtime.
"""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
import json
import math
import threading
from urllib.parse import urlsplit

from ...loop.encapsulate import as_loop
from ...loop.loop_role import LoopRole, LoopRoleIdentity
from ..provisioning_mcp import PROTOCOL_VERSION, TOOL_OPERATIONS, _schema
from ..provisioning_server import OPERATIONS, ProvisioningError, ProvisioningItemBinding
from .http_auth import (
    HttpAuthenticationError, ServiceHttpAuthentication, ServiceHttpAuthenticator, validate_public_url,
    EXTERNAL_JWT_AUTHENTICATION,
)
from .records import ACCESS_MANAGE_SCOPE, BILLING_MANAGE_SCOPE, ServiceCommitUnknown, ServiceRuntimeError
from .refusals import guidance as _refusal_guidance
from .request_limits import LIMIT_REACHED_CODE, FailedAttemptLimiter, ServiceRequestLimits

RESULT_VERSION = "service_http_result/v1"
ERROR_VERSION = "service_http_error/v1"
PROVISIONING_REQUEST_VERSION = "service_provisioning_request/v1"
RETRIEVAL_REQUEST_VERSION = "service_retrieval_request/v1"
HTTP_CONFIGURATION_RECORD_TYPE = "service_http_configuration/v1"
#: The account email boundary this release serves. An installed adapter states
#: the version it speaks, and an adapter that speaks another one is refused
#: before the application serves either public account route.
ACCOUNT_EMAIL_PROTOCOL = "account_email/v1"
DISCOVER_OPERATION, LIST_OPERATION, MANIFEST_OPERATION, READ_OPERATION = OPERATIONS
BILLING_PLANS_PATH = "/api/v1/billing/plans"
BILLING_CHECKOUT_PATH = "/api/v1/billing/checkout"
BILLING_PORTAL_PATH = "/api/v1/billing/portal"
#: The one address added for promotion codes. An account posts a code to it and
#: receives the entitlement the code declares. There is no address that reads a
#: code back, because the service stores a digest and never the code itself.
PROMOTION_REDEMPTION_PATH = "/api/v1/account/promotion"
HTML_MEDIA_TYPE = "text/html"
WEB_ASSETS = {
    "/": ("index.html", HTML_MEDIA_TYPE), "/app": ("index.html", HTML_MEDIA_TYPE),
    "/login": ("index.html", HTML_MEDIA_TYPE), "/signup": ("index.html", HTML_MEDIA_TYPE),
    "/account": ("index.html", HTML_MEDIA_TYPE),
    "/admin": ("index.html", HTML_MEDIA_TYPE),
    "/connect": ("index.html", HTML_MEDIA_TYPE),
    "/examples": ("index.html", HTML_MEDIA_TYPE),
    "/security": ("index.html", HTML_MEDIA_TYPE),
    "/auth/callback": ("index.html", HTML_MEDIA_TYPE), "/auth/confirm": ("index.html", HTML_MEDIA_TYPE),
    "/docs": ("index.html", HTML_MEDIA_TYPE), "/how-it-works": ("index.html", HTML_MEDIA_TYPE),
    "/pricing": ("index.html", HTML_MEDIA_TYPE),
    "/assets/client-recipes.json": ("client-recipes.json", "application/json"),
    "/assets/supabase-client.js": ("supabase-client.js", "text/javascript"),
    "/assets/service.css": ("service.css", "text/css"),
    "/assets/architecture.css": ("architecture.css", "text/css"),
    "/assets/client-access.js": ("client-access.js", "text/javascript"),
    "/assets/service.js": ("service.js", "text/javascript"),
    "/assets/architecture-story.js": ("architecture-story.js", "text/javascript"),
    # The licence terms of the packaged browser library travel with it.
    "/assets/third-party-notices.txt": ("THIRD-PARTY-NOTICES.md", "text/plain"),
}
# Every address the interface router answers, with the methods it answers for
# it. The router reads this before it asks who is calling, so that an address
# the service does not serve is a missing page rather than a credential
# problem. `/mcp` is answered earlier, by the protocol transport.
#
# A check compares this table with the branches in `_web_route`, because an
# address named in one and not the other is either unreachable or
# unauthenticated and neither is visible from anywhere else.
API_ROUTES = {
    "/.well-known/oauth-protected-resource": ("GET",),
    "/.well-known/oauth-protected-resource/mcp": ("GET",),
    "/api/v1/health": ("GET",),
    "/api/v1/capabilities": ("GET",),
    "/api/v1/billing/webhook": ("POST",),
    "/api/v1/account/identity": ("GET",),
    "/api/v1/account/activate": ("POST",),
    "/api/v1/account/logout": ("POST",),
    "/api/v1/account/access": ("GET", "POST"),
    "/api/v1/admin/access": ("GET", "POST"),
    "/api/v1/session": ("GET",),
    "/api/v1/usage": ("GET",),
    "/api/v1/provisioning": ("POST",),
    "/api/v1/download": ("POST",),
    "/api/v1/retrieval": ("POST",),
    BILLING_PLANS_PATH: ("GET",),
    BILLING_CHECKOUT_PATH: ("POST",),
    BILLING_PORTAL_PATH: ("POST",),
}
MISSING_ADDRESS_PAGE = """<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{name} | Address not found</title><link rel="stylesheet" href="/assets/service.css"></head>
<body><main id="main" class="reading" style="padding:4rem 4vw">
<p class="eyebrow">Address not found</p>
<h1>This service has no page at that address.</h1>
<p class="lede">The address in your browser is not one {name} serves. It may have been
mistyped, or it may be an older address that has since changed. Nothing is wrong with
your account or your key.</p>
<div class="actions"><a class="button primary" href="/">Go to the home page</a>
<a class="button quiet" href="/docs">Open the setup guide</a></div>
<p class="caption">If you followed a link from {name} to get here, the link is wrong and
we would like to know. Tell the person who runs this service which page you came from.</p>
</main></body></html>
"""


class ServiceHttpError(ValueError):
    """A bounded versioned transport refusal with no private exception text; no other failure adds details or headers."""

    def __init__(self, code, status=400, *, details=None, headers=None):
        super().__init__(code)
        self.code, self.status = code, status
        self.details, self.headers = details, headers


@dataclass(frozen=True)
class ServiceHttpConfiguration:
    """Exact host transport settings and resource ceilings."""

    public_base_url: str
    allowed_hosts: tuple[str, ...]
    allowed_origins: tuple[str, ...] = ()
    display_name: str = "Loop Engine"
    maximum_request_bytes: int = 65_536
    maximum_response_bytes: int = 262_144
    maximum_inline_body_bytes: int = 16_384
    maximum_download_bytes: int = 64 * 1024 * 1024
    maximum_search_results: int = 50
    maximum_concurrent_operations: int = 8
    request_timeout_seconds: float = 30.0
    allow_loopback_http: bool = False
    request_limits: ServiceRequestLimits = ServiceRequestLimits()
    protocol_version: str = PROTOCOL_VERSION
    record_type: str = HTTP_CONFIGURATION_RECORD_TYPE

    def __post_init__(self):
        if (not isinstance(self.display_name, str) or not self.display_name.strip()
                or len(self.display_name) > 80 or any(ord(ch) < 32 for ch in self.display_name)):
            raise ValueError("service display name must be bounded printable text")
        if self.record_type != HTTP_CONFIGURATION_RECORD_TYPE or self.protocol_version != PROTOCOL_VERSION:
            raise ValueError("unsupported HTTP service profile")
        if type(self.allow_loopback_http) is not bool:
            raise ValueError("loopback HTTP requires explicit Boolean configuration")
        base = validate_public_url(self.public_base_url, permit_loopback=self.allow_loopback_http)
        if urlsplit(base).path not in ("", "/"):
            raise ValueError("public service base URL must be an origin")
        hosts, origins = tuple(self.allowed_hosts), tuple(self.allowed_origins)
        if not hosts or any(not isinstance(host, str) or not host or "*" in host or "/" in host or any(ch.isspace() for ch in host) for host in hosts):
            raise ValueError("exact nonempty Host values are required")
        if urlsplit(base).netloc not in hosts:
            raise ValueError("the public origin must be an allowed Host")
        for origin in origins:
            validate_public_url(origin, permit_loopback=self.allow_loopback_http)
            if urlsplit(origin).path not in ("", "/") or origin.endswith("/"):
                raise ValueError("browser origins must be exact origins without paths")
        for name in ("maximum_request_bytes", "maximum_response_bytes", "maximum_inline_body_bytes",
                     "maximum_download_bytes", "maximum_search_results", "maximum_concurrent_operations"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError("HTTP resource limits must be positive integers")
        if self.maximum_inline_body_bytes > self.maximum_download_bytes:
            raise ValueError("inline body allowance cannot exceed download allowance")
        if (type(self.request_timeout_seconds) not in (int, float)
                or not math.isfinite(self.request_timeout_seconds) or self.request_timeout_seconds <= 0):
            raise ValueError("HTTP request deadline must be finite and positive")
        object.__setattr__(self, "request_limits", ServiceRequestLimits.from_host(self.request_limits))
        object.__setattr__(self, "public_base_url", base)
        object.__setattr__(self, "allowed_hosts", hosts)
        # The declared public service origin owns the packaged browser client.
        # Other origins still require an exact host configuration entry.
        object.__setattr__(self, "allowed_origins", tuple(dict.fromkeys((base.rstrip("/"), *origins))))


def speaks_the_account_email_boundary(adapter):
    """True when an installed account email adapter declares the boundary this release serves."""
    return getattr(adapter, "protocol_version", None) == ACCOUNT_EMAIL_PROTOCOL


def invoke_http_service_as_loop(operation, function):
    """Own one deterministic domain attempt with a canonical Practitioner."""
    return _loop_result(operation, function, LoopRole.PRACTITIONER, "practitioner.code_execution")


def invoke_http_retrieval_as_loop(function):
    """Own metadata retrieval with the registered Intelligence search profile."""
    return _loop_result("retrieval", function, LoopRole.INTELLIGENCE, "intelligence.search")


def _loop_result(operation, function, role, profile):
    result = as_loop("hosted intelligence " + operation, function,
                     identity=LoopRoleIdentity(role, profile))
    if result.get("error") is not None:
        raise result["error"]
    return {"record_type": RESULT_VERSION, "operation": operation, "result": result["value"],
            "execution": {"runtime_type": "Loop", "loop_id": result["loop_id"],
                          "profile": profile + "@1.0.0", "mode": "deterministic",
                          "model_calls": result["model_calls"],
                          "definition_digest": result["loop_definition_digest"]}}


def _json_bytes(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _parse_json(body):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate field")
            value[key] = item
        return value
    try:
        value = json.loads(body, object_pairs_hook=unique,
                           parse_constant=lambda _value: (_ for _ in ()).throw(ValueError("nonfinite value")))
    except (ValueError, UnicodeError):
        raise ServiceHttpError("invalid_json") from None
    if not isinstance(value, dict):
        raise ServiceHttpError("object_required")
    return value


def _error_record(code, status, details=None):
    # The code stays exactly what it was, because a client matches on it. The
    # two sentences beside it are for whoever has to act: a person reading the
    # website, and an agent that has to choose a next step without one. They
    # are chosen from the code and the status alone, so no part of the request
    # can be reflected back in a refusal.
    message, next_action = _refusal_guidance(code, status)
    result = {"record_type": ERROR_VERSION,
              "error": {"code": code, "message": message, "next_action": next_action},
              "effect_commitment": "not_asserted", "automatic_retry": False}
    if details is not None:
        result["error"]["details"] = details
        if details.get("record_type") == "billing_event_result/v1" and details.get("committed") is True and details.get("status") == "pending":
            result["effect_commitment"] = "durable_pending"
    return result


def _status_classes_in_use():
    """Every HTTP status this transport can put on a refusal.

    Read from this module's own source rather than kept as a second list, so
    that a status added to a raise or to `_status` has no wording only if the
    wording check says so.
    """
    import inspect
    import re
    source = inspect.getsource(inspect.getmodule(_status_classes_in_use))
    raised = re.findall(r"ServiceHttpError\([^)\n]*?,\s*(\d{3})", source)
    chosen = re.findall(r"return\s+(\d{3})(?:,|\s|$)", source) + re.findall(r"\s(\d{3})\s+if\s", source)
    return {int(value) for value in [*raised, *chosen, "400"]}


def http_provisioning_schema(operation):
    schema = _schema(operation)
    if operation in (MANIFEST_OPERATION, READ_OPERATION):
        schema["properties"]["expected_digest"] = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
    if operation == READ_OPERATION:
        schema["required"] = ["identity", "request_id"]
    return schema


def _status(error):
    code = getattr(error, "code", "operation_failed")
    if isinstance(error, ServiceHttpError):
        return error.status, code
    # Closed account creation is a state of the service, not a bad request. The identity codes stay ahead
    # of the authentication answer: the identity adapter raises them as an authentication failure, and an
    # unreachable provider is a service state, not a wrong password.
    if code in ("identity_provider_unavailable", "identity_key_set_unavailable",
                "account_registration_unavailable"):
        return 503, code
    if isinstance(error, HttpAuthenticationError) or code in ("unauthorized", "key_expired", "key_revoked",
            "tenant_disabled", "subject_unbound", "session_authorization_expired"):
        return 403 if code == "insufficient_scope" else 401, code
    if code in ("body_forbidden", "scope_denied", "entitlement_required", "forbidden", "scope_required",
                "disclosure_grant_changed", "access_administration_forbidden", "access_target_forbidden",
                "scope_escalation_refused", "access_writes_not_authorized", "browser_session_required"):
        return 403, code
    if code in ("access_request_identity_conflict", "access_token_limit_reached", "concurrent_update",
                "access_token_history_limit_reached", "access_token_already_revoked",
                "promotion_request_identity_conflict", "promotion_code_already_redeemed_by_this_account",
                "paid_subscription_active",
                "session_request_identity_conflict", "session_selection_changed", "session_policy_changed"):
        return 409, code
    # Every refusal that depends on the offered code itself answers with one
    # status and one word, so a guess cannot tell an unknown code from a real
    # one that has run out.
    if code in ("promotion_code_unusable", "promotion_redemption_forbidden"):
        return 403, code
    if code == "promotion_redemption_requires_an_account":
        return 401, code
    if code == "promotion_redemption_unavailable":
        return 503, code
    if code in ("item_unavailable", "managed_access_token_not_found"):
        return 404, code
    if code in ("meter_commit_unknown", "commit_unknown", "session_operation_in_progress",
                "session_reconciliation_window_exhausted", "session_network_authority_required",
                "billing_customer_not_bound", "session_record_unavailable"):
        return 503, code
    return 400 if isinstance(error, (ProvisioningError, ServiceRuntimeError)) else 500, code


@dataclass
class ServiceHttpApplication:
    """Portable transport facade; all persistent policy remains in its bindings."""

    runtime: object = field(repr=False)
    provisioning: object = field(repr=False)
    configuration: ServiceHttpConfiguration
    authentication: ServiceHttpAuthentication = field(default_factory=ServiceHttpAuthentication)
    billing_processor: object | None = field(default=None, repr=False)
    billing_sessions: object | None = field(default=None, repr=False)
    access_administration: object | None = field(default=None, repr=False)
    browser_identity: object | None = field(default=None, repr=False)
    client_access: object | None = field(default=None, repr=False)
    promotions: object | None = field(default=None, repr=False)
    account_email: object | None = field(default=None, repr=False)

    def __post_init__(self):
        from .runtime import ServiceRuntime
        from .provisioning import DurableProvisioningBinding
        if not isinstance(self.configuration, ServiceHttpConfiguration):
            raise TypeError("typed HTTP service configuration is required")
        if (not isinstance(self.runtime, ServiceRuntime) or not isinstance(self.provisioning, DurableProvisioningBinding)
                or self.provisioning.runtime is not self.runtime):
            raise TypeError("authentication and provisioning require the same durable runtime authority")
        if (EXTERNAL_JWT_AUTHENTICATION in self.authentication.modes
                and self.authentication.audience != self.configuration.public_base_url + "/mcp"):
            raise ValueError("token audience must match the advertised service resource URL")
        self.authenticator = ServiceHttpAuthenticator(self.runtime, self.authentication, browser_identity=self.browser_identity)
        if self.client_access is not None:
            from .access import ServiceAccessAdministration, ServiceClientAccessPolicy
            if (not isinstance(self.client_access, ServiceAccessAdministration)
                    or not isinstance(self.client_access.policy, ServiceClientAccessPolicy)
                    or self.client_access.runtime is not self.runtime or self.browser_identity is None):
                raise ValueError("customer access must bind the same runtime and a browser identity provider")
        if self.account_email is not None and not speaks_the_account_email_boundary(self.account_email):
            raise ValueError(f"an installed account email adapter must speak {ACCOUNT_EMAIL_PROTOCOL}")
        self._workers = ThreadPoolExecutor(max_workers=self.configuration.maximum_concurrent_operations,
                                           thread_name_prefix="intelligence-service")
        self._slots = threading.BoundedSemaphore(self.configuration.maximum_concurrent_operations)
        self.request_limiter = FailedAttemptLimiter(self.configuration.request_limits)

    def capabilities(self):
        from importlib.metadata import version
        session_options = self.billing_sessions.options() if self.billing_sessions is not None else {}
        return {"record_type": "service_capabilities/v1", "api_version": "v1",
                "website": {"display_name": self.configuration.display_name,
                            "registration_available": self.browser_identity is not None and self.browser_identity.configuration.email_signup_enabled,
                            "browser_identity_available": self.browser_identity is not None,
                            "access_profile": "operator_provisioned",
                            "access_administration_available": self.access_administration is not None,
                            "client_access_available": self.client_access is not None,
                            "promotion_redemption_available": self.promotions is not None,
                            "promotion_redemption_endpoint": PROMOTION_REDEMPTION_PATH},
                "protocol": {"transport": "streamable_http", "versions": [PROTOCOL_VERSION],
                             "sdk_version": version("mcp"), "session_state": "stateless",
                             "oauth_resource_metadata": EXTERNAL_JWT_AUTHENTICATION in self.authentication.modes,
                             "oauth_authorization_server_installed": False,
                             "external_authorization_flow_qualified": False},
                "authentication": self.authentication.to_dict(),
                "operation_scopes": {"metadata_and_search": "provisioning:metadata",
                                     "body_and_download": "provisioning:read", "usage": "usage:read",
                                     "billing_sessions": BILLING_MANAGE_SCOPE},
                "retrieval": {"modes": ["lexical", "hybrid"], "lexical_backend": "sqlite_fts5",
                              "vector_backend": "deterministic_character_hash",
                              "semantic_embedding_model_installed": False,
                              "scope": "authorized_catalogue_metadata", "returns_bodies": False},
                "delivery": {"inline_body_bytes": self.configuration.maximum_inline_body_bytes,
                             "download_bytes": self.configuration.maximum_download_bytes,
                             "download_endpoint": "/api/v1/download", "requires_reauthorization": True,
                             "body_format": "utf8_text"},
                "limits": {"request_bytes": self.configuration.maximum_request_bytes,
                           "response_bytes": self.configuration.maximum_response_bytes,
                           "search_results": self.configuration.maximum_search_results,
                           "concurrent_operations": self.configuration.maximum_concurrent_operations,
                           "failed_attempts_per_address": self.configuration.request_limits.published()},
                "billing": {"webhook": self.billing_processor is not None,
                            "checkout": session_options.get("checkout_available", False),
                            "portal": session_options.get("portal_available", False),
                            "plans_endpoint": BILLING_PLANS_PATH},
                "cancellation": "bounded_response_wait; running callbacks may finish; no automatic replay"}

    @asynccontextmanager
    async def _limited(self, request):
        """Refuse an address over its failed-attempt limit before any work; count only a refused attempt.

        It yields the counted address key, so that a route with its own allowance counts the same caller.
        """
        name = self.configuration.request_limits.client_address_header
        key = self.request_limiter.address_key(request.client.host if request.client else None,
                                               request.headers.getlist(name) if name else ())
        refusal = self.request_limiter.refusal(key)
        if refusal is not None:
            raise ServiceHttpError(LIMIT_REACHED_CODE, 429, details=refusal,
                                   headers={"Retry-After": str(refusal["retry_after_seconds"])})
        try:
            yield key
        except Exception as error:
            if 400 <= _status(error)[0] < 500:
                self.request_limiter.record_failure(key)
            raise

    async def _authenticated(self, request):
        """Sign in one request: no credential uses no worker slot, and a refused credential is counted."""
        if len(request.headers.getlist("authorization")) != 1:
            raise HttpAuthenticationError()
        async with self._limited(request):
            return await self._work(lambda: self._authenticate_request(request))

    async def _work(self, function):
        if not self._slots.acquire(blocking=False):
            raise ServiceHttpError("service_busy", 503)
        try:
            future = self._workers.submit(function)
        except Exception:
            self._slots.release()
            raise
        future.add_done_callback(lambda _future: self._slots.release())
        waiting = asyncio.wrap_future(future)
        try:
            return await asyncio.wait_for(asyncio.shield(waiting), self.configuration.request_timeout_seconds)
        except asyncio.TimeoutError:
            # The callback can still commit. Its reserved slot remains held
            # until completion, and the adapter never retries the operation.
            waiting.add_done_callback(lambda done: done.exception() if not done.cancelled() else None)
            raise ServiceHttpError("deadline_exceeded", 504) from None
        except asyncio.CancelledError:
            waiting.add_done_callback(lambda done: done.exception() if not done.cancelled() else None)
            raise

    def _invoke(self, authentication, operation, fields):
        current = self.authenticator.revalidate(authentication)
        self._require_scope(current, "provisioning:read" if operation == READ_OPERATION else "provisioning:metadata")
        if operation == READ_OPERATION:
            manifest = self.provisioning.invoke_for_principal(current.principal, MANIFEST_OPERATION,
                **{key: value for key, value in fields.items() if key != "request_id"})
            if manifest["size_bytes"] > self.configuration.maximum_inline_body_bytes:
                raise ServiceHttpError("download_required", 413)
        result = self.provisioning.invoke_for_principal(current.principal, operation, **fields)
        if "provisioning:read" not in current.effective_scopes:
            if operation == LIST_OPERATION:
                result = {**result, "items": [{**row, "body_allowed": False} for row in result["items"]]}
            elif operation == MANIFEST_OPERATION:
                result = {**result, "body_allowed": False}
            elif operation == DISCOVER_OPERATION:
                result = {**result, "bodies_available": False}
        self.authenticator.revalidate(authentication)
        return result

    def _search(self, authentication, fields):
        from ..retrieval import Retriever
        from ..store_serve import StoreRecord
        from ..harness_intelligence import HarnessIntelligenceItem
        from ..intelligence_tagging import TagSet

        current = self.authenticator.revalidate(authentication)
        self._require_scope(current, "provisioning:metadata")
        _grants, grant_guard = self.runtime.grant_snapshot(current.principal)
        listing = self.provisioning.invoke_for_principal(current.principal, LIST_OPERATION)
        rows = {row["identity"]: row for row in listing["items"]}
        records = [StoreRecord(identity, "context", row["purpose"],
                    body={"description": row["purpose"], "keywords": [identity, row["kind"], row["source_layer"]]})
                   for identity, row in rows.items()]
        result = Retriever(records).search(fields["query"], mode=fields.get("mode", "lexical"),
                                            top_n=fields.get("top_n", 10))
        hits = []
        for hit in result["hits"]:
            row = rows[hit["record_id"]]
            item = HarnessIntelligenceItem(
                identity=row["identity"], kind=row["kind"], purpose=row["purpose"], digest=row["digest"],
                source_layer=row["source_layer"], source_ref=row["source_ref"], size_bytes=row["size_bytes"],
                license_name=row["license"], declared_effects=tuple(row["declared_effects"]),
                styles=tuple(row["styles"]), default_exposure=row["exposure"], availability=row["availability"],
                tags=TagSet({key: value for key, value in row["tags"].items() if key != "record_type"}))
            from dataclasses import asdict
            hits.append({"reference": asdict(ProvisioningItemBinding.from_item(item)),
                         "purpose": row["purpose"], "kind": row["kind"], "size_bytes": row["size_bytes"],
                         "license": row["license"], "declared_effects": row["declared_effects"],
                         "harness_styles": row["styles"],
                         "score": hit["rrf"], "modes": hit["modes"],
                         "qualification_basis": row["qualification_basis"],
                         "body_allowed": row["body_allowed"] and "provisioning:read" in current.effective_scopes})
        self._verify_search_snapshot(authentication, current, grant_guard)
        return {"record_type": "service_retrieval_result/v1", "hits": hits,
                "mode": fields.get("mode", "lexical"), "bodies_loaded": False,
                "backend": self.capabilities()["retrieval"],
                "limitations": ["Hash vectors measure character similarity, not learned semantic understanding.",
                                "Distribution references do not grant local code execution or independent Code admission."]}

    def _verify_search_snapshot(self, authentication, initial, grant_guard):
        """Authorize the completed metadata response before releasing any result.

        A grant replacement, even one restoring the same values, invalidates
        the in-flight listing. Principal and token scope changes also refuse.
        This is a completion-time check, not a recall of bytes already sent.
        """
        latest = self.authenticator.revalidate(authentication)
        self._require_scope(latest, "provisioning:metadata")
        _grants, observed = self.runtime.grant_snapshot(latest.principal)
        if (observed != grant_guard or latest.principal != initial.principal
                or latest.effective_scopes != initial.effective_scopes):
            raise ServiceRuntimeError("disclosure_grant_changed")

    @staticmethod
    def _require_scope(authentication, scope):
        if scope not in authentication.effective_scopes:
            raise HttpAuthenticationError("insufficient_scope")

    def _usage(self, context):
        current = self.authenticator.revalidate(context)
        self._require_scope(current, "usage:read")
        return self.runtime.usage_for(current.principal)

    def _session_options(self, context):
        from .stripe_sessions import SESSION_OPTIONS_VERSION
        if self.billing_sessions is None:
            return {"record_type": SESSION_OPTIONS_VERSION, "policy_digest": None,
                    "checkout_available": False, "portal_available": False, "plans": [],
                    "unavailable_reason": "billing_sessions_not_installed"}
        current = self.authenticator.revalidate(context)
        value = self.billing_sessions.options(current.principal)
        if BILLING_MANAGE_SCOPE not in current.effective_scopes:
            value = {**value, "checkout_available": False, "portal_available": False,
                     "unavailable_reason": "billing_scope_required"}
        return value

    def _create_billing_session(self, context, request):
        from .stripe_sessions import BillingSessionError, SESSION_UNCERTAINTY_VERSION
        current = self.authenticator.revalidate(context)
        self._require_scope(current, BILLING_MANAGE_SCOPE)
        if self.billing_sessions is None:
            raise ServiceHttpError("billing_sessions_not_installed", 501)
        try:
            result = self.billing_sessions.create(current.principal, request, authorization_expires_at=current.expires_at)
        except BillingSessionError as error:
            raise ServiceHttpError(error.code, error.status, details=error.details) from None
        except ServiceCommitUnknown:
            raise ServiceHttpError("billing_session_record_unknown", 503, details={
                "record_type": SESSION_UNCERTAINTY_VERSION, "request_id": request.request_id,
                "retry_same_request": True, "creation_attempted": False}) from None
        self.authenticator.revalidate(context)
        return result

    def _client_access(self, context, fields):
        from .access import ServiceAccessRequest, ServiceAccessSession
        from .http_auth import BROWSER_IDENTITY_AUTHENTICATION
        current = self.authenticator.revalidate(context)
        if current.mode != BROWSER_IDENTITY_AUTHENTICATION:
            raise ServiceHttpError("browser_session_required", 403)
        if self.client_access is None:
            raise ServiceHttpError("client_access_unavailable", 503)
        session = ServiceAccessSession(current.principal.authentication_record_id,
            self.authenticator.credential_digest(current), current.expires_at, current.effective_scopes)
        if fields is None:
            return self.client_access.inspect(current.principal, session=session)
        request = ServiceAccessRequest.from_customer_dict(fields, current.principal.tenant_id)
        return self.client_access.apply(current.principal, request, session=session)

    def _redeem_promotion(self, context, request):
        """Revalidate the signed-in account, then redeem for that account only."""
        current = self.authenticator.revalidate(context)
        return self.promotions.redeem(current.principal, request)

    def _validate_search(self, payload, *, versioned=True):
        if not isinstance(payload, dict):
            raise ServiceHttpError("object_required")
        if set(payload) - ({"record_type", "query", "mode", "top_n"} if versioned else {"query", "mode", "top_n"}):
            raise ServiceHttpError("unknown_request_field")
        if versioned and payload.get("record_type") != RETRIEVAL_REQUEST_VERSION:
            raise ServiceHttpError("unsupported_version")
        if (not isinstance(payload.get("query"), str) or not payload["query"].strip()
                or len(payload["query"].encode()) > 4096):
            raise ServiceHttpError("invalid_query")
        if payload.get("mode", "lexical") not in ("lexical", "hybrid"):
            raise ServiceHttpError("unsupported_retrieval_mode")
        if (type(payload.get("top_n", 10)) is not int
                or not 1 <= payload.get("top_n", 10) <= self.configuration.maximum_search_results):
            raise ServiceHttpError("invalid_search_limit")
        return {key: value for key, value in payload.items() if key != "record_type"}

    def _validate_provisioning(self, payload):
        if payload.get("record_type") != PROVISIONING_REQUEST_VERSION:
            raise ServiceHttpError("unsupported_version")
        operation = payload.get("operation")
        if operation not in TOOL_OPERATIONS.values():
            raise ServiceHttpError("unsupported_operation")
        fields = {key: value for key, value in payload.items() if key not in ("record_type", "operation")}
        from jsonschema import validate, ValidationError
        try:
            validate(fields, http_provisioning_schema(operation))
        except ValidationError:
            raise ServiceHttpError("invalid_request") from None
        if operation == READ_OPERATION and not fields.get("request_id"):
            raise ServiceHttpError("request_identity_required")
        return operation, fields

    def _sdk_server(self):
        import mcp.types as types
        from mcp.server.lowlevel import Server
        from jsonschema import validate, ValidationError
        sdk = Server("loop-engine-intelligence", version="1.0.0")

        @sdk.list_tools()
        async def list_tools():
            context = sdk.request_context.request.scope["service_authentication"]
            self.authenticator.revalidate(context)
            tools = [types.Tool(name=name, description="Authorized intelligence " + operation,
                inputSchema=http_provisioning_schema(operation), annotations=types.ToolAnnotations(
                    readOnlyHint=operation != READ_OPERATION, destructiveHint=False, idempotentHint=True))
                for name, operation in TOOL_OPERATIONS.items()]
            tools.append(types.Tool(name="intelligence_search", description="Search authorized metadata only",
                inputSchema={"type": "object", "required": ["query"], "additionalProperties": False,
                    "properties": {"query": {"type": "string"}, "mode": {"enum": ["lexical", "hybrid"]},
                                   "top_n": {"type": "integer", "minimum": 1}}}))
            return tools

        @sdk.call_tool(validate_input=False)
        async def call_tool(name, arguments):
            try:
                context = sdk.request_context.request.scope["service_authentication"]
                if name == "intelligence_search":
                    fields = self._validate_search(arguments, versioned=False)
                    output = await self._work(lambda: invoke_http_retrieval_as_loop(lambda: self._search(context, fields)))
                else:
                    operation = TOOL_OPERATIONS.get(name)
                    if operation is None:
                        raise ServiceHttpError("unsupported_operation")
                    validate(arguments, http_provisioning_schema(operation))
                    if operation == READ_OPERATION and not arguments.get("request_id"):
                        raise ServiceHttpError("request_identity_required")
                    output = await self._work(lambda: invoke_http_service_as_loop(operation,
                        lambda: self._invoke(context, operation, arguments)))
                response = types.CallToolResult(content=[types.TextContent(type="text", text=_json_bytes(output).decode())],
                                                structuredContent=output, isError=False)
                if len(response.model_dump_json(by_alias=True).encode()) > self.configuration.maximum_response_bytes:
                    raise ServiceHttpError("response_limit_exceeded", 413)
                return response
            except ValidationError:
                status, code = 400, "invalid_request"
            except Exception as error:
                status, code = _status(error)
            refused = _error_record(code, status)
            return types.CallToolResult(content=[types.TextContent(type="text", text=_json_bytes(refused).decode())],
                                        structuredContent=refused, isError=True)
        return sdk

    def create_app(self):
        from starlette.applications import Starlette
        from starlette.requests import Request
        from starlette.responses import Response, JSONResponse
        from starlette.routing import Mount
        from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
        from mcp.server.transport_security import TransportSecuritySettings
        config = self.configuration
        manager = StreamableHTTPSessionManager(self._sdk_server(), stateless=True,
            security_settings=TransportSecuritySettings(allowed_hosts=list(config.allowed_hosts),
                                                       allowed_origins=list(config.allowed_origins)),
            max_request_body_size=config.maximum_request_bytes)

        @asynccontextmanager
        async def lifespan(_app):
            async with manager.run():
                yield
            self._workers.shutdown(wait=False, cancel_futures=False)

        async def transport(scope, receive, send):
            request = Request(scope, receive)
            origin = request.headers.get("origin")
            cors = ({"Access-Control-Allow-Origin": origin, "Vary": "Origin",
                     "Access-Control-Expose-Headers": "X-Content-SHA256, X-Loop-Engine-Record-Type"}
                    if origin in config.allowed_origins else {})
            try:
                if (len(request.headers.getlist("host")) != 1
                        or request.headers["host"] not in config.allowed_hosts):
                    raise ServiceHttpError("invalid_host", 421)
                if origin is not None and (len(request.headers.getlist("origin")) != 1
                                           or origin not in config.allowed_origins):
                    raise ServiceHttpError("invalid_origin", 403)
                if request.method == "OPTIONS":
                    if origin not in config.allowed_origins:
                        raise ServiceHttpError("invalid_origin", 403)
                    response = Response(status_code=204, headers={**cors,
                        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                        "Access-Control-Allow-Headers": "Authorization, Content-Type, MCP-Protocol-Version, Stripe-Signature"})
                elif request.url.path == "/mcp":
                    context = await self._authenticated(request)
                    body = await self._body(request) if request.method == "POST" else b""
                    payload = _parse_json(body) if body else {}
                    if payload.get("method") == "initialize":
                        if (payload.get("params") or {}).get("protocolVersion") != PROTOCOL_VERSION:
                            raise ServiceHttpError("unsupported_protocol_version")
                    elif request.headers.get("mcp-protocol-version") != PROTOCOL_VERSION:
                        raise ServiceHttpError("unsupported_protocol_version")
                    scope["service_authentication"] = context
                    delivered = False
                    async def replay():
                        nonlocal delivered
                        if not delivered:
                            delivered = True
                            return {"type": "http.request", "body": body, "more_body": False}
                        return await receive()
                    async def protocol_send(message):
                        if message["type"] == "http.response.start":
                            message = {**message, "headers": list(message.get("headers", ()))
                                       + [(key.lower().encode(), value.encode()) for key, value in {
                                           **cors, "Cache-Control": "no-store",
                                           "X-Content-Type-Options": "nosniff"}.items()]}
                        await send(message)
                    await manager.handle_request(scope, replay, protocol_send)
                    return
                else:
                    response = await self._web_route(request, Response, JSONResponse)
                    response.headers.update(cors)
            except Exception as error:
                status, code = _status(error)
                details, added = (error.details, error.headers) if isinstance(error, ServiceHttpError) else (None, None)
                # A reader who arrived in a browser needs a sentence and a way
                # back. A record shape is the right answer to a program and the
                # wrong answer to a person. The page names no address and
                # repeats nothing from the request, so nothing can be reflected
                # into it.
                if status == 404 and "text/html" in request.headers.get("accept", ""):
                    from html import escape
                    response = Response(
                        MISSING_ADDRESS_PAGE.format(name=escape(config.display_name)).encode("utf-8"),
                        status_code=404, media_type=HTML_MEDIA_TYPE,
                        headers={**cors, **self._page_headers()})
                else:
                    response = JSONResponse(_error_record(code, status, details), status_code=status,
                                            headers={**cors, **(added or {})})
                if status == 401:
                    response.headers["WWW-Authenticate"] = ("Bearer resource_metadata=\""
                        + config.public_base_url + "/.well-known/oauth-protected-resource/mcp\""
                        if EXTERNAL_JWT_AUTHENTICATION in self.authentication.modes else "Bearer")
            response.headers["Cache-Control"] = "no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
            await response(scope, receive, send)
        return Starlette(routes=[Mount("/", app=transport)], lifespan=lifespan)

    def _authenticate_request(self, request):
        if len(request.headers.getlist("authorization")) != 1:
            raise HttpAuthenticationError()
        return self.authenticator.authenticate(request.headers["authorization"],
            purpose="website" if request.url.path.startswith("/api/") else "service")

    async def _body(self, request):
        if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
            raise ServiceHttpError("unsupported_media_type", 415)
        chunks, size = [], 0
        async def collect():
            nonlocal size
            async for chunk in request.stream():
                size += len(chunk)
                if size > self.configuration.maximum_request_bytes:
                    raise ServiceHttpError("request_limit_exceeded", 413)
                chunks.append(chunk)
        try:
            await asyncio.wait_for(collect(), self.configuration.request_timeout_seconds)
        except asyncio.TimeoutError:
            raise ServiceHttpError("request_body_deadline", 408) from None
        return b"".join(chunks)

    def _page_headers(self):
        """The headers every served page carries, refusals included."""
        identity_origin = " " + self.browser_identity.configuration.project_url if self.browser_identity else ""
        return {"Content-Security-Policy": "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'"
                + identity_origin + "; base-uri 'none'; frame-ancestors 'none'; form-action 'none'",
                "Referrer-Policy": "no-referrer", "X-Frame-Options": "DENY",
                "Permissions-Policy": "camera=(), microphone=(), geolocation=()"}

    async def _web_route(self, request, Response, JSONResponse):
        path, method, status_code = request.url.path, request.method, 200
        if method == "GET" and path in WEB_ASSETS:
            from html import escape
            from importlib.resources import files
            name, media_type = WEB_ASSETS[path]
            body = files("loop_engine").joinpath("core", "service_runtime", "web_assets", name).read_bytes()
            if media_type == HTML_MEDIA_TYPE:
                body = body.replace(b"{{SERVICE_NAME}}", escape(self.configuration.display_name, quote=True).encode("utf-8"))
            return Response(body, media_type=media_type, headers=self._page_headers())
        # Decide whether this service serves the address before asking who is
        # calling. An unknown address that is authenticated first answers 401
        # unauthorized, which sends the reader looking for a credential fault
        # that does not exist, and hides a wrong address from the person who
        # published it.
        if method not in API_ROUTES.get(path, ()):
            raise ServiceHttpError("route_unavailable", 404)
        if path in ("/.well-known/oauth-protected-resource", "/.well-known/oauth-protected-resource/mcp") and method == "GET":
            if EXTERNAL_JWT_AUTHENTICATION not in self.authentication.modes:
                raise ServiceHttpError("external_authorization_not_configured", 404)
            from .records import SCOPES
            return JSONResponse({"resource": self.configuration.public_base_url + "/mcp",
                "authorization_servers": [self.authentication.issuer],
                "scopes_supported": sorted(set(SCOPES) | set(self.authentication.required_scopes)),
                "bearer_methods_supported": ["header"], "resource_name": "Loop Engine Intelligence"})
        if path == "/api/v1/health" and method == "GET":
            output = {"record_type": "service_health/v1", "healthy": True, "readiness_checked": False,
                      "deployed_provider_qualification": False}
        elif path == "/api/v1/billing/webhook" and method == "POST":
            if self.billing_processor is None:
                raise ServiceHttpError("billing_webhook_unavailable", 501)
            if len(request.headers.getlist("stripe-signature")) != 1:
                raise ServiceHttpError("billing_signature_required", 400)
            body = await self._body(request)
            output = await self._work(lambda: invoke_http_service_as_loop("billing_webhook",
                lambda: self.billing_processor.handle(body, request.headers["stripe-signature"]).to_dict()))
            if output["result"]["committed"] is not True:
                raise ServiceHttpError("billing_commit_unknown", 503, details=output["result"])
            if output["result"]["status"] == "pending":
                raise ServiceHttpError("billing_reconciliation_pending", 503, details=output["result"])
        elif path == "/api/v1/capabilities" and method == "GET":
            output = self.capabilities()
        elif path == "/api/v1/account/identity" and method == "GET":
            if self.browser_identity is None:
                raise ServiceHttpError("browser_identity_unavailable", 503)
            output = {**self.browser_identity.public_configuration(), **(self.account_email.availability()
                      if self.account_email else {"signup_available": False, "recovery_available": False}),
                      "redirect_url": self.configuration.public_base_url + "/auth/callback"}
        elif path == "/api/v1/account/activate" and method == "POST":
            if self.browser_identity is None:
                raise ServiceHttpError("browser_identity_unavailable", 503)
            async with self._limited(request):
                fields = _parse_json(await self._body(request))
                if fields != {"record_type": "service_account_activation_request/v1"}:
                    raise ServiceHttpError("invalid_account_activation")
                if (len(request.headers.getlist("authorization")) != 1
                        or not request.headers["authorization"].startswith("Bearer ")
                        or request.headers["authorization"].count(" ") != 1):
                    raise HttpAuthenticationError()
                output = await self._work(lambda: invoke_http_service_as_loop("account_activation",
                    lambda: self.browser_identity.activate(request.headers["authorization"][7:])))
        elif path in ("/api/v1/account/signup", "/api/v1/account/recovery") and method == "POST":
            if self.account_email is None:
                raise ServiceHttpError("account_email_unavailable", 404)
            async with self._limited(request) as address:
                prepared = self.account_email.prepare(path.rsplit("/", 1)[-1], _parse_json(await self._body(request)), address)
                output, status_code = await self._work(lambda: invoke_http_service_as_loop(prepared.operation,
                    lambda: self.account_email.deliver(prepared))), 202
        else:
            context = await self._authenticated(request)
            if path == "/api/v1/session" and method == "GET":
                output = {"record_type": "service_session/v1", "principal": context.principal.to_dict(),
                          "authentication_mode": context.mode, "token_expires_at": context.expires_at}
                output["principal"]["scopes"] = list(context.effective_scopes)
            elif path == "/api/v1/account/logout" and method == "POST":
                from .http_auth import BROWSER_IDENTITY_AUTHENTICATION
                fields = _parse_json(await self._body(request))
                if (self.browser_identity is None or context.mode != BROWSER_IDENTITY_AUTHENTICATION
                        or fields != {"record_type": "service_browser_logout_request/v1"}):
                    raise ServiceHttpError("browser_session_required", 403)
                output = await self._work(lambda: invoke_http_service_as_loop("account_logout",
                    lambda: self.browser_identity.logout(context)))
            elif path == "/api/v1/usage" and method == "GET":
                output = await self._work(lambda: invoke_http_service_as_loop("usage",
                    lambda: self._usage(context)))
            elif path == "/api/v1/account/access" and method in ("GET", "POST"):
                if request.query_params:
                    raise ServiceHttpError("unknown_request_field")
                fields = _parse_json(await self._body(request)) if method == "POST" else None
                output = await self._work(lambda: invoke_http_service_as_loop("client_access",
                    lambda: self._client_access(context, fields)))
            elif path == PROMOTION_REDEMPTION_PATH and method == "POST":
                from .promotions import PromotionRedemptionRequest
                if self.promotions is None:
                    raise ServiceHttpError("promotion_redemption_unavailable", 503)
                # Guessing a code is a refused attempt from one address, so the
                # existing failed-attempt limiter counts it and refuses the
                # address once it is over its allowance.
                async with self._limited(request):
                    payload = PromotionRedemptionRequest.from_dict(_parse_json(await self._body(request)))
                    output = await self._work(lambda: invoke_http_service_as_loop("promotion_redemption",
                        lambda: self._redeem_promotion(context, payload)))
            elif path == "/api/v1/admin/access" and method in ("GET", "POST"):
                from .access import ServiceAccessRequest
                self._require_scope(context, ACCESS_MANAGE_SCOPE)
                if self.access_administration is None:
                    raise ServiceHttpError("access_administration_unavailable", 503)
                request_data = ServiceAccessRequest.from_dict(_parse_json(await self._body(request))) if method == "POST" else None
                def administer():
                    current = self.authenticator.revalidate(context)
                    self._require_scope(current, ACCESS_MANAGE_SCOPE)
                    return (self.access_administration.inspect(current.principal) if request_data is None
                            else self.access_administration.apply(current.principal, request_data))
                output = await self._work(lambda: invoke_http_service_as_loop("access_administration", administer))
            elif path == BILLING_PLANS_PATH and method == "GET":
                output = await self._work(lambda: invoke_http_service_as_loop("billing_plans",
                    lambda: self._session_options(context)))
            elif path in (BILLING_CHECKOUT_PATH, BILLING_PORTAL_PATH) and method == "POST":
                from .stripe_sessions import BillingSessionRequest, CHECKOUT_OPERATION, PORTAL_OPERATION
                operation = CHECKOUT_OPERATION if path == BILLING_CHECKOUT_PATH else PORTAL_OPERATION
                payload = BillingSessionRequest.from_dict(_parse_json(await self._body(request)), operation)
                output = await self._work(lambda: invoke_http_service_as_loop(operation,
                    lambda: self._create_billing_session(context, payload)))
            elif path in ("/api/v1/provisioning", "/api/v1/download") and method == "POST":
                operation, fields = self._validate_provisioning(_parse_json(await self._body(request)))
                if path.endswith("download"):
                    if operation != READ_OPERATION:
                        raise ServiceHttpError("download_requires_read")
                    def download():
                        current = self.authenticator.revalidate(context)
                        self._require_scope(current, "provisioning:read")
                        manifest = self.provisioning.invoke_for_principal(current.principal, MANIFEST_OPERATION,
                            **{key: value for key, value in fields.items() if key != "request_id"})
                        if manifest["size_bytes"] > self.configuration.maximum_download_bytes:
                            raise ServiceHttpError("download_limit_exceeded", 413)
                        value = self.provisioning.invoke_for_principal(current.principal, READ_OPERATION, **fields)
                        self.authenticator.revalidate(context)
                        if len(value["body"].encode("utf-8")) > self.configuration.maximum_download_bytes:
                            raise ServiceHttpError("download_limit_exceeded", 413)
                        return value
                    output = await self._work(lambda: invoke_http_service_as_loop("download", download))
                    value = output["result"]
                    return Response(value["body"].encode("utf-8"), media_type="application/octet-stream",
                        headers={"X-Loop-Engine-Record-Type": "service_download/v1",
                                 "X-Content-SHA256": value["digest"],
                                 "Content-Disposition": 'attachment; filename="intelligence.txt"'})
                output = await self._work(lambda: invoke_http_service_as_loop(operation,
                    lambda: self._invoke(context, operation, fields)))
            elif path == "/api/v1/retrieval" and method == "POST":
                fields = self._validate_search(_parse_json(await self._body(request)))
                output = await self._work(lambda: invoke_http_retrieval_as_loop(lambda: self._search(context, fields)))
            else:
                raise ServiceHttpError("route_unavailable", 404)
        if output.get("record_type") != RESULT_VERSION:
            output = {"record_type": RESULT_VERSION, "operation": path.rsplit("/", 1)[-1], "result": output}
        encoded = _json_bytes(output)
        if len(encoded) > self.configuration.maximum_response_bytes:
            raise ServiceHttpError("response_limit_exceeded", 413)
        return Response(encoded, media_type="application/json", status_code=status_code)
