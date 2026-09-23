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
import re
import threading
from urllib.parse import urlsplit

from ...loop.encapsulate import as_loop
from ...loop.loop_role import LoopRole, LoopRoleIdentity
from ..provisioning_mcp import TOOL_OPERATIONS, _schema
from ..provisioning_server import OPERATIONS, ProvisioningError, ProvisioningItemBinding
from .http_auth import (
    HttpAuthenticationError, ServiceHttpAuthentication, ServiceHttpAuthenticator, validate_public_url,
    EXTERNAL_JWT_AUTHENTICATION,
)
from .observability import (
    CAPTURED_BODY_KEY, SCOPE_REFERENCE_KEY, ServiceFailureJournal, ServiceObservabilityPolicy,
    new_request_reference, readiness_deadline_report, readiness_report,
)
from .records import ACCESS_MANAGE_SCOPE, BILLING_MANAGE_SCOPE, ServiceCommitUnknown, ServiceRuntimeError
from .refusals import guidance as _refusal_guidance
from .request_limits import LIMIT_REACHED_CODE, FailedAttemptLimiter, ServiceRequestLimits
from .retention import RetentionSchedule, ServiceRetentionPolicy
from .waitlist import ServiceWaitlist, administer_waitlist, join_request
from .web_pages import HTML_MEDIA_TYPE, WEB_ASSETS, missing_address_page, served_asset

RESULT_VERSION = "service_http_result/v1"
ERROR_VERSION = "service_http_error/v1"
PROVISIONING_REQUEST_VERSION = "service_provisioning_request/v1"
RETRIEVAL_REQUEST_VERSION = "service_retrieval_request/v1"
#: Version 2 replaced the one pinned protocol version of version 1 with the
#: set of versions the host serves. A release that reads version 1 refuses
#: version 2, and this release refuses version 1, so neither can widen or
#: narrow what a host file meant.
HTTP_CONFIGURATION_RECORD_TYPE = "service_http_configuration/v2"
#: Model Context Protocol versions a client reaches through the `initialize`
#: handshake, oldest first. Each one is qualified by the protocol checks in
#: `http_checks.py`.
HANDSHAKE_PROTOCOL_VERSIONS = ("2025-11-25",)
#: Versions that carry the protocol version on every request instead of a
#: handshake, oldest first, qualified by the same checks.
PER_REQUEST_PROTOCOL_VERSIONS = ("2026-07-28",)
#: Every protocol version this release can serve, oldest first. A host serves
#: all of them unless its configuration names fewer.
QUALIFIED_PROTOCOL_VERSIONS = HANDSHAKE_PROTOCOL_VERSIONS + PER_REQUEST_PROTOCOL_VERSIONS
#: How long a client may reuse a tool list or a discovery answer, in
#: milliseconds. Both change only with a release or a host configuration
#: change, and both are answers to an authenticated caller, so a shared cache
#: must not hand them to anyone else.
PROTOCOL_CACHE_TTL_MS = 300_000
PROTOCOL_CACHE_SCOPE = "private"
#: The account email boundary this release serves. An installed adapter states
#: the version it speaks, and an adapter that speaks another one is refused
#: before the application serves either public account route.
ACCOUNT_EMAIL_PROTOCOL = "account_email/v1"
TENANT_CONCURRENCY_REFUSAL_VERSION = "service_tenant_concurrency_refusal/v1"
TENANT_CONCURRENCY_CODE = "tenant_concurrency_limit_reached"
EXTERNAL_PROVIDER_REFUSAL_VERSION = "service_external_provider_capacity_refusal/v1"
EXTERNAL_PROVIDER_CODE = "external_provider_capacity_reached"
#: The name of the share held by work that waits on another service. A tenant
#: identity may not contain a space, so no account can ever name this share.
EXTERNAL_PROVIDER_SHARE = "external provider"
NESTING_LIMIT_CODE = "nesting_limit_exceeded"
#: The deepest request or host file this service reads nests about five
#: containers. The reader refuses anything deeper before it parses, because the
#: parser opens one recursive call for each container and the interpreter's
#: recursion allowance belongs to the whole process, not to one request.
MAXIMUM_JSON_NESTING_DEPTH = 64
DISCOVER_OPERATION, LIST_OPERATION, MANIFEST_OPERATION, READ_OPERATION = OPERATIONS
BILLING_PLANS_PATH = "/api/v1/billing/plans"
BILLING_CHECKOUT_PATH = "/api/v1/billing/checkout"
BILLING_PORTAL_PATH = "/api/v1/billing/portal"
#: The one address added for promotion codes. An account posts a code to it and
#: receives the entitlement the code declares. There is no address that reads a
#: code back, because the service stores a digest and never the code itself.
PROMOTION_REDEMPTION_PATH = "/api/v1/account/promotion"
#: The public waiting list and its operator view. A visitor posts an address to
#: the first without signing in. An operator with the administration scope reads
#: the list and applies one decision at a time at the second.
WAITLIST_PATH, ADMIN_WAITLIST_PATH = "/api/v1/waitlist", "/api/v1/admin/waitlist"
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
    "/api/v1/account/signup": ("POST",),
    "/api/v1/account/recovery": ("POST",),
    PROMOTION_REDEMPTION_PATH: ("POST",),
    WAITLIST_PATH: ("POST",),
    "/api/v1/admin/access": ("GET", "POST"),
    ADMIN_WAITLIST_PATH: ("GET", "POST"),
    "/api/v1/session": ("GET",),
    "/api/v1/usage": ("GET",),
    "/api/v1/provisioning": ("POST",),
    "/api/v1/download": ("POST",),
    "/api/v1/retrieval": ("POST",),
    BILLING_PLANS_PATH: ("GET",),
    BILLING_CHECKOUT_PATH: ("POST",),
    BILLING_PORTAL_PATH: ("POST",),
}
#: The address the protocol transport answers, ahead of the interface router.
PROTOCOL_PATH = "/mcp"
#: Every address this service answers, named once and built from the tables
#: that decide what is served, so that it cannot drift from them. A failure
#: record keeps the path only when it is one of these; anything else is
#: recorded as the unmatched name, because a stranger chooses that text.
DECLARED_ROUTES = (*API_ROUTES, PROTOCOL_PATH, *WEB_ASSETS)
#: The addresses whose request body is itself a credential: sign-up carries the
#: password of a new account, and promotion redemption carries a code that
#: grants paid access to whoever holds it. Their bodies never reach a failure
#: record, whatever the host chose to capture, because no recording choice may
#: record a credential. The refusal itself is still recorded.
CREDENTIAL_BODY_ROUTES = ("/api/v1/account/signup", PROMOTION_REDEMPTION_PATH)


class ServiceHttpError(ValueError):
    """A bounded versioned transport refusal with no private exception text; no other failure adds details or headers.

    A refusal of the protocol endpoint itself carries `protocol_error`, the
    JSON-RPC error response a protocol client reads, and is answered in that
    shape instead of the service's own record.
    """

    def __init__(self, code, status=400, *, details=None, headers=None, protocol_error=None):
        super().__init__(code)
        self.code, self.status = code, status
        self.details, self.headers = details, headers
        self.protocol_error = protocol_error


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
    protocol_versions: tuple[str, ...] = QUALIFIED_PROTOCOL_VERSIONS
    record_type: str = HTTP_CONFIGURATION_RECORD_TYPE

    def __post_init__(self):
        if (not isinstance(self.display_name, str) or not self.display_name.strip()
                or len(self.display_name) > 80 or any(ord(ch) < 32 for ch in self.display_name)):
            raise ValueError("service display name must be bounded printable text")
        if self.record_type != HTTP_CONFIGURATION_RECORD_TYPE:
            raise ValueError("unsupported HTTP service profile")
        versions = self.protocol_versions
        if (not isinstance(versions, (tuple, list)) or not versions or len(set(map(str, versions))) != len(versions)
                or any(not isinstance(value, str) or value not in QUALIFIED_PROTOCOL_VERSIONS for value in versions)):
            raise ValueError("protocol versions must be distinct versions this release qualified")
        # The release order, not the host file's order, so no order in a host
        # file can carry a meaning of its own.
        object.__setattr__(self, "protocol_versions",
                           tuple(value for value in QUALIFIED_PROTOCOL_VERSIONS if value in versions))
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

    @property
    def maximum_concurrent_operations_for_each_tenant(self):
        """How many workers one share may hold at once: half the pool, at least one.

        A worker stays reserved until its operation finishes, so a share that
        could hold every worker could refuse every other share. Half the pool
        leaves room for a second share at any moment. A pool of one cannot be
        shared, and the share is then the pool.

        One account is a share. All work that waits on another service is one
        further share, so a slow or flooded identity or payment provider can
        never hold the workers that this service's own records need.
        """
        return max(1, self.maximum_concurrent_operations // 2)

    @property
    def handshake_protocol_versions(self):
        """The served versions a client reaches with `initialize`, oldest first."""
        return tuple(value for value in self.protocol_versions if value in HANDSHAKE_PROTOCOL_VERSIONS)

    @property
    def per_request_protocol_versions(self):
        """The served versions a client names on every request instead, oldest first."""
        return tuple(value for value in self.protocol_versions if value in PER_REQUEST_PROTOCOL_VERSIONS)


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


#: The protocol's own error codes, defined by the 2026-07-28 revision.
HEADER_MISMATCH_ERROR = -32020
UNSUPPORTED_PROTOCOL_VERSION_ERROR = -32022
PROTOCOL_VERSION_HEADER = "mcp-protocol-version"
#: The shape of a protocol version a refusal may name back to the client. A
#: header outside it is refused as malformed and is not repeated.
_VERSION_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")


def _protocol_error(protocol_code, message, request_id, data=None):
    """The protocol's own error response for one refused request."""
    error = {"code": protocol_code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": request_id, "error": error}


def select_protocol_binding(configuration, payload, header_values):
    """The protocol version one request to `/mcp` is served at, or a refusal before any effect.

    Returns `(version, message)`: the version handed to the protocol library
    and the message it serves. The message differs from the request only when
    an `initialize` asked for a version this service does not serve.

    An `initialize` always selects the handshake, whatever header it carries,
    as the 2026-07-28 revision requires of a server that serves both kinds of
    version. When the requested version is not served, the 2025-11-25
    lifecycle requires an answer that names one that is, normally the newest,
    and the client decides whether to continue. The service selects that
    version itself, because the protocol library would also accept older
    versions this release has not qualified. A requested version that is not
    text is passed on unchanged, so the library refuses it as malformed.

    Every other request names its version in `MCP-Protocol-Version`, and that
    version selects the binding. A version the service does not serve is
    answered with the 2026-07-28 error that lists the versions it does serve,
    newest first, so that a client can choose one and retry.
    """
    identity = payload.get("id")
    request_id = identity if isinstance(identity, (str, int)) and not isinstance(identity, bool) else None
    supported = list(reversed(configuration.protocol_versions))
    if len(header_values) > 1:
        raise ServiceHttpError("protocol_version_header_repeated", protocol_error=_protocol_error(
            HEADER_MISMATCH_ERROR, "The MCP-Protocol-Version header appears more than once", request_id))
    if payload.get("method") == "initialize":
        handshake = configuration.handshake_protocol_versions
        params = payload.get("params")
        requested = params.get("protocolVersion") if isinstance(params, dict) else None
        if not handshake:
            data = {"supported": supported}
            if isinstance(requested, str) and _VERSION_TOKEN.fullmatch(requested):
                data["requested"] = requested
            raise ServiceHttpError("unsupported_protocol_version", protocol_error=_protocol_error(
                UNSUPPORTED_PROTOCOL_VERSION_ERROR, "Unsupported protocol version", request_id, data))
        if not isinstance(requested, str) or requested in handshake:
            return (requested if requested in handshake else handshake[-1]), payload
        return handshake[-1], {**payload, "params": {**params, "protocolVersion": handshake[-1]}}
    if not header_values:
        raise ServiceHttpError("protocol_version_header_missing", protocol_error=_protocol_error(
            HEADER_MISMATCH_ERROR, "The MCP-Protocol-Version header is required", request_id))
    version = header_values[0]
    if not _VERSION_TOKEN.fullmatch(version):
        raise ServiceHttpError("protocol_version_header_malformed", protocol_error=_protocol_error(
            HEADER_MISMATCH_ERROR, "The MCP-Protocol-Version header is not a protocol version", request_id))
    if version not in configuration.protocol_versions:
        raise ServiceHttpError("unsupported_protocol_version", protocol_error=_protocol_error(
            UNSUPPORTED_PROTOCOL_VERSION_ERROR, "Unsupported protocol version", request_id,
            {"supported": supported, "requested": version}))
    return version, payload


def _json_nesting_depth(body, limit):
    """Deepest container nesting in raw JSON bytes, stopping once over the limit.

    The reader must know the depth before it parses. The parser opens one
    recursive call for each container it enters, and the interpreter's
    recursion allowance is shared by everything running in this process, so a
    body deep enough to exhaust it is an internal fault rather than a bounded
    refusal. A bracket inside a quoted string is text, not a container, so the
    scan tracks strings and their escapes.
    """
    if isinstance(body, str):
        body = body.encode("utf-8", "surrogatepass")
    depth = highest = 0
    inside = escaped = False
    for byte in body:
        if escaped:
            escaped = False
        elif inside:
            if byte == 0x5C:
                escaped = True
            elif byte == 0x22:
                inside = False
        elif byte == 0x22:
            inside = True
        elif byte in (0x7B, 0x5B):
            depth += 1
            if depth > highest:
                highest = depth
                if highest > limit:
                    return highest
        elif byte in (0x7D, 0x5D):
            depth -= 1
    return highest


def selected_origin(sent_origins):
    """The one origin a request names, or None when it names none or several.

    A request that names more than one origin names none. Reading the first of
    them would let a caller pair an allowed origin with another one and still
    be answered with the allowed origin's sharing headers, on the refusal as
    well as on a result.
    """
    return sent_origins[0] if len(sent_origins) == 1 else None


def _parse_json(body, *, maximum_depth=MAXIMUM_JSON_NESTING_DEPTH):
    if _json_nesting_depth(body, maximum_depth) > maximum_depth:
        raise ServiceHttpError(NESTING_LIMIT_CODE)
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
    except RecursionError:
        # The depth scan above is the guard. This second refusal keeps a
        # parser that recurses on some other shape from becoming a fault.
        raise ServiceHttpError(NESTING_LIMIT_CODE) from None
    if not isinstance(value, dict):
        raise ServiceHttpError("object_required")
    return value


def _error_record(code, status, details=None, request_reference=None):
    """Build the one refusal shape. The reference names this exact request.

    The customer reads the reference back to an operator, who searches for it.
    It carries no information about the credential, the caller or the body; it
    is a name issued from the operating system random source.
    """
    # The code stays exactly what it was, because a client matches on it. The
    # two sentences beside it are for whoever has to act: a person reading the
    # website, and an agent that has to choose a next step without one. They
    # are chosen from the code and the status alone, so no part of the request
    # can be reflected back in a refusal.
    message, next_action = _refusal_guidance(code, status)
    result = {"record_type": ERROR_VERSION,
              "error": {"code": code, "message": message, "next_action": next_action},
              "effect_commitment": "not_asserted", "automatic_retry": False}
    if request_reference is not None:
        result["request_reference"] = request_reference
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
    # A success answer is not a refusal. The transport's success statuses
    # appear in the route as a default and as accepted delivery answers, so
    # reading every numeric literal in the module would name wording for
    # statuses no refusal ever carries.
    success_defaults = {int(value) for value in re.findall(
        r"request\.method,\s*(\d{3})", source)}
    success_defaults.update(int(value) for value in re.findall(
        r"\)\)\),\s*(\d{3})", source))
    return ({int(value) for value in [*raised, *chosen, "400"]}
            - success_defaults)


def http_provisioning_schema(operation):
    schema = _schema(operation)
    if operation in (MANIFEST_OPERATION, READ_OPERATION):
        schema["properties"]["expected_digest"] = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
    if operation == READ_OPERATION:
        schema["required"] = ["identity", "request_id"]
        # One file of a multi-file package, fetched through the download
        # address after the item's own read is authorized and metered.
        schema["properties"]["path"] = {"type": "string", "minLength": 1, "maxLength": 200}
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
                "scope_escalation_refused", "access_writes_not_authorized", "browser_session_required",
                "waitlist_administration_forbidden", "waitlist_writes_not_authorized"):
        return 403, code
    if code in ("access_request_identity_conflict", "access_token_limit_reached", "concurrent_update",
                "access_token_history_limit_reached", "access_token_already_revoked",
                "promotion_request_identity_conflict", "promotion_code_already_redeemed_by_this_account",
                "paid_subscription_active",
                "session_request_identity_conflict", "session_selection_changed", "session_policy_changed",
                "waitlist_address_already_listed", "waitlist_address_has_account",
                "waitlist_transition_refused", "waitlist_decision_identity_conflict"):
        return 409, code
    # Accepted requests to join the waiting list, counted for one declared
    # source. It is a wait like the failed-attempt limit, not a bad request.
    if code == "waitlist_source_flooded":
        return 429, code
    # Every refusal that depends on the offered code itself answers with one
    # status and one word, so a guess cannot tell an unknown code from a real
    # one that has run out.
    if code in ("promotion_code_unusable", "promotion_redemption_forbidden"):
        return 403, code
    if code == "promotion_redemption_requires_an_account":
        return 401, code
    if code == "promotion_redemption_unavailable":
        return 503, code
    if code in ("item_unavailable", "managed_access_token_not_found", "waitlist_entry_not_found",
                "item_withdrawn", "package_file_not_found", "package_files_unavailable"):
        return 404, code
    if code in ("meter_commit_unknown", "commit_unknown", "session_operation_in_progress",
                "session_reconciliation_window_exhausted", "session_network_authority_required",
                "billing_customer_not_bound", "session_record_unavailable",
                "waitlist_unavailable", "waitlist_account_directory_unavailable",
                "waitlist_source_secret_unavailable", "waitlist_source_secret_unusable"):
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
    waitlist: object | None = field(default=None, repr=False)
    observability: ServiceObservabilityPolicy = ServiceObservabilityPolicy()
    retention: ServiceRetentionPolicy = ServiceRetentionPolicy()
    #: The host's catalogue refresher, started with the application and
    #: stopped with it. None serves the catalogue loaded at start unchanged.
    catalogue_refresher: object | None = field(default=None, repr=False)

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
        if self.waitlist is not None and (not isinstance(self.waitlist, ServiceWaitlist)
                                          or self.waitlist.runtime is not self.runtime):
            raise ValueError("the waiting list must bind the same durable runtime authority")
        if not isinstance(self.observability, ServiceObservabilityPolicy):
            raise TypeError("a typed observability policy is required")
        if not isinstance(self.retention, ServiceRetentionPolicy):
            raise TypeError("a typed retention policy is required")
        # The one periodic removal of records whose promised time has passed.
        # The lifespan starts it and cancels it; health reads its last outcome.
        self.retention_schedule = RetentionSchedule(self.runtime, self.retention, waitlist=self.waitlist)
        self._workers = ThreadPoolExecutor(max_workers=self.configuration.maximum_concurrent_operations,
                                           thread_name_prefix="intelligence-service")
        self._slots = threading.BoundedSemaphore(self.configuration.maximum_concurrent_operations)
        # Workers each share holds right now: one entry for each account with
        # an operation running, and one for all work waiting on another
        # service. An entry exists only while that share holds a worker, so
        # the table cannot grow past the pool. It belongs to one service
        # process, like the failed-attempt table.
        self._share_operations = {}
        self._share_lock = threading.Lock()
        self.request_limiter = FailedAttemptLimiter(self.configuration.request_limits)
        # The durable record of refused requests, in the same service store.
        self.failure_journal = ServiceFailureJournal(self.runtime.config, DECLARED_ROUTES,
                                                     policy=self.observability)

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
                            "promotion_redemption_endpoint": PROMOTION_REDEMPTION_PATH,
                            "waitlist_available": self.waitlist is not None},
                "protocol": {"transport": "streamable_http",
                             "versions": list(self.configuration.protocol_versions),
                             "handshake_versions": list(self.configuration.handshake_protocol_versions),
                             "per_request_versions": list(self.configuration.per_request_protocol_versions),
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
                              "scope": "authorized_catalogue_metadata", "returns_bodies": False,
                              "index": "one_reusable_index_for_each_catalogue_view",
                              "filters": "declared_filterable_public_attributes"},
                "delivery": {"inline_body_bytes": self.configuration.maximum_inline_body_bytes,
                             "download_bytes": self.configuration.maximum_download_bytes,
                             "download_endpoint": "/api/v1/download", "requires_reauthorization": True,
                             "body_format": "utf8_text", "package_files": "download_by_path"},
                "limits": {"request_bytes": self.configuration.maximum_request_bytes,
                           "response_bytes": self.configuration.maximum_response_bytes,
                           "search_results": self.configuration.maximum_search_results,
                           "concurrent_operations": self.configuration.maximum_concurrent_operations,
                           "concurrent_operations_for_each_account":
                               self.configuration.maximum_concurrent_operations_for_each_tenant,
                           "concurrent_operations_waiting_on_another_service":
                               self.configuration.maximum_concurrent_operations_for_each_tenant,
                           "request_nesting_depth": MAXIMUM_JSON_NESTING_DEPTH,
                           "failed_attempts_per_address": self.configuration.request_limits.published()},
                "billing": {"webhook": self.billing_processor is not None,
                            "checkout": session_options.get("checkout_available", False),
                            "portal": session_options.get("portal_available", False),
                            "discount_code": session_options.get("discount_code_accepted", False),
                            "plans_endpoint": BILLING_PLANS_PATH},
                "cancellation": "bounded_response_wait; running callbacks may finish; no automatic replay"}

    def _address_key(self, request):
        """Name the address whose source the host declared, or no address when it declared none."""
        name = self.configuration.request_limits.client_address_header
        return self.request_limiter.address_key(request.client.host if request.client else None,
                                                request.headers.getlist(name) if name else ())

    @asynccontextmanager
    async def _limited(self, request):
        """Refuse an address over its failed-attempt limit before any work; count only a refused attempt.

        It yields the counted address key, so that a route with its own allowance counts the same caller.
        """
        key = self._address_key(request)
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
            context = await self._authenticate_request(request)
        # The tenant of a signed-in request, kept so that a later refusal names
        # the account an operator must look at. The credential is not kept.
        request.scope["service_failure_tenant"] = context.principal.tenant_id
        return context

    @staticmethod
    def _share_refusal(name, ceiling):
        if name == EXTERNAL_PROVIDER_SHARE:
            # Not the caller's own allowance and not their fault, so it is a
            # capacity state of this service and is not a refused attempt.
            return ServiceHttpError(EXTERNAL_PROVIDER_CODE, 503, headers={"Retry-After": "1"},
                details={"record_type": EXTERNAL_PROVIDER_REFUSAL_VERSION,
                         "concurrent_operations_for_each_share": ceiling, "retry_after_seconds": 1})
        return ServiceHttpError(TENANT_CONCURRENCY_CODE, 429, headers={"Retry-After": "1"},
            details={"record_type": TENANT_CONCURRENCY_REFUSAL_VERSION,
                     "concurrent_operations_for_each_tenant": ceiling, "retry_after_seconds": 1})

    def _reserve(self, shares):
        """Hold one worker in each named share of the pool; refuse over any share.

        Returns the callable that gives the held workers back. Calling it twice
        gives back one set, so a refusal on the way in cannot free a worker
        that a different operation is holding. Nothing is taken unless every
        named share has room, so a refusal leaves no share short.
        """
        names = tuple(dict.fromkeys(name for name in shares if name))
        if not names:
            return lambda: None
        ceiling = self.configuration.maximum_concurrent_operations_for_each_tenant
        with self._share_lock:
            for name in names:
                if self._share_operations.get(name, 0) >= ceiling:
                    raise self._share_refusal(name, ceiling)
            for name in names:
                self._share_operations[name] = self._share_operations.get(name, 0) + 1
        given_back = []
        def release():
            with self._share_lock:
                if given_back:
                    return
                given_back.append(True)
                for name in names:
                    remaining = self._share_operations.get(name, 1) - 1
                    if remaining > 0:
                        self._share_operations[name] = remaining
                    else:
                        self._share_operations.pop(name, None)
        return release

    def _tenant_work(self, context, function):
        """Run one authenticated operation inside its own account's share."""
        return self._work(function, shares=(context.principal.tenant_id,))

    async def _authenticate_request(self, request):
        """Resolve one credential: this service's own records first, then a provider read.

        A host-issued key is resolved from local records in microseconds. A
        browser session or an external token needs a read at the identity
        provider, which waits on a machine this service does not control. The
        two are separate work with separate shares of the worker pool, so
        callers waiting on a slow or flooded identity provider can never hold
        the workers that a host key needs. Where no mode consults another
        service, one attempt remains one piece of work.
        """
        purpose = "website" if request.url.path.startswith("/api/") else "service"
        if len(request.headers.getlist("authorization")) != 1:
            raise HttpAuthenticationError()
        authorization = request.headers["authorization"]
        if not self.authenticator.consults_another_service(purpose=purpose):
            return await self._work(lambda: self.authenticator.authenticate(authorization, purpose=purpose))
        held = await self._work(lambda: self.authenticator.host_key(authorization, purpose=purpose))
        if held is not None:
            return held
        return await self._work(lambda: self.authenticator.remote_credential(authorization, purpose=purpose),
                                shares=(EXTERNAL_PROVIDER_SHARE,))

    async def _readiness(self):
        """Measure every dependency now, off the bounded customer worker pool.

        Readiness runs on the default executor so that a busy service still
        answers the question truthfully instead of reporting itself unready
        merely because every customer slot is in use. A dependency that does
        not answer inside the request deadline is a dependency that failed.
        """
        def measure():
            from .billing_policy import billing_policy_refusal
            billed = self.billing_sessions is not None or self.billing_processor is not None
            return readiness_report(config=self.runtime.config, provisioning=self.provisioning,
                authentication_modes=self.authentication.modes, policy=self.observability,
                browser_identity_installed=self.browser_identity is not None,
                billing_sessions_installed=self.billing_sessions is not None,
                billing_webhook_installed=self.billing_processor is not None,
                billing_policy=(lambda: billing_policy_refusal(self)) if billed else None,
                retention=self.retention_schedule.readiness_check())
        waiting = asyncio.get_running_loop().run_in_executor(None, measure)
        try:
            return await asyncio.wait_for(asyncio.shield(waiting), self.configuration.request_timeout_seconds)
        except asyncio.TimeoutError:
            waiting.add_done_callback(lambda done: done.exception() if not done.cancelled() else None)
            return readiness_deadline_report(self.observability)

    async def _record_failure(self, scope, request, code, status):
        """Write one metadata failure record without letting it raise.

        This runs on the default executor, not on the bounded service pool, so
        recording a refusal can never consume a slot a customer needs.
        """
        reference = scope.get(SCOPE_REFERENCE_KEY)
        if reference is None:
            return {"recorded": False, "reason": "no_request_reference"}
        # Everything is inside the guard, including reading the route and the
        # method off the request. The customer is already being refused, and
        # nothing done to record that may turn their typed refusal into a
        # different failure.
        try:
            journal = self.failure_journal
            fields = {"route": journal.route_of(request.url.path),
                      "method": journal.method_of(request.method),
                      "refusal_code": code, "status": status,
                      "tenant_id": scope.get("service_failure_tenant", ""),
                      "request_body": scope.get(CAPTURED_BODY_KEY)}
            return await asyncio.get_running_loop().run_in_executor(
                None, lambda: journal.record(reference, **fields))
        except Exception:
            return {"recorded": False, "reason": "failure_not_recorded"}

    async def _work(self, function, *, shares=()):
        release_shares = self._reserve(shares)
        if not self._slots.acquire(blocking=False):
            release_shares()
            raise ServiceHttpError("service_busy", 503)
        try:
            future = self._workers.submit(function)
        except Exception:
            self._slots.release()
            release_shares()
            raise
        def finished(_future):
            self._slots.release()
            release_shares()
        future.add_done_callback(finished)
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
        if "path" in fields:
            raise ServiceHttpError("package_file_requires_download")
        view = self.provisioning.current_view()
        if operation == READ_OPERATION:
            manifest = self.provisioning.invoke_for_principal(current.principal, MANIFEST_OPERATION, view=view,
                **{key: value for key, value in fields.items() if key != "request_id"})
            if manifest["size_bytes"] > self.configuration.maximum_inline_body_bytes:
                raise ServiceHttpError("download_required", 413)
        result = self.provisioning.invoke_for_principal(current.principal, operation, view=view, **fields)
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
        from dataclasses import asdict
        from ..harness_intelligence import HarnessIntelligenceItem
        from ..intelligence_tagging import TagSet
        from .catalogue_search import authorized_hits

        current = self.authenticator.revalidate(authentication)
        self._require_scope(current, "provisioning:metadata")
        _grants, grant_guard = self.runtime.grant_snapshot(current.principal)
        # One view for the whole request: the index that ranks, the listing
        # that authorizes and the references returned all come from it.
        view = self.provisioning.current_view()

        def authorize(candidates):
            listing = self.provisioning.invoke_for_principal(current.principal, LIST_OPERATION, view=view,
                                                             candidates=candidates)
            return {row["identity"]: row for row in listing["items"]}
        ranked, rows = authorized_hits(view, fields, authorize)
        hits = []
        for identity, score, modes in ranked:
            row = rows[identity]
            item = HarnessIntelligenceItem(
                identity=row["identity"], kind=row["kind"], purpose=row["purpose"], digest=row["digest"],
                source_layer=row["source_layer"], source_ref=row["source_ref"], size_bytes=row["size_bytes"],
                license_name=row["license"], declared_effects=tuple(row["declared_effects"]),
                styles=tuple(row["styles"]), default_exposure=row["exposure"], availability=row["availability"],
                tags=TagSet({key: value for key, value in row["tags"].items() if key != "record_type"}))
            hits.append({"reference": asdict(ProvisioningItemBinding.from_item(item)),
                         "purpose": row["purpose"], "kind": row["kind"], "size_bytes": row["size_bytes"],
                         "license": row["license"], "declared_effects": row["declared_effects"],
                         "harness_styles": row["styles"],
                         "score": score, "modes": modes,
                         "qualification_basis": row["qualification_basis"],
                         "body_allowed": row["body_allowed"] and "provisioning:read" in current.effective_scopes,
                         "attributes": view.shown_attributes(identity),
                         "package": view.package_summary(identity)})
        self._verify_search_snapshot(authentication, current, grant_guard)
        return {"record_type": "service_retrieval_result/v1", "hits": hits,
                "mode": fields.get("mode", "lexical"), "bodies_loaded": False,
                "backend": self.capabilities()["retrieval"],
                "catalogue_release": view.release_id or None,
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
        if set(payload) - ({"record_type", "query", "mode", "top_n", "filters"} if versioned
                           else {"query", "mode", "top_n", "filters"}):
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
        if "filters" in payload and not isinstance(payload["filters"], dict):
            raise ServiceHttpError("search_filter_invalid")
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
        """The protocol library's server, bound to exactly the versions this host serves.

        The library speaks more versions than this release has qualified, so
        the transport selects the version of every request before the library
        sees it. The library must still speak each version the host serves;
        a missing one refuses the whole application before it answers anyone.
        """
        import mcp.types as types
        from mcp.server.caching import CacheHint
        from mcp.server.lowlevel import Server
        from mcp.types.version import HANDSHAKE_PROTOCOL_VERSIONS as LIBRARY_HANDSHAKE
        from mcp.types.version import MODERN_PROTOCOL_VERSIONS as LIBRARY_PER_REQUEST
        from jsonschema import validate, ValidationError
        configuration = self.configuration
        unserved = ([value for value in configuration.handshake_protocol_versions if value not in LIBRARY_HANDSHAKE]
                    + [value for value in configuration.per_request_protocol_versions
                       if value not in LIBRARY_PER_REQUEST])
        if unserved:
            raise ValueError("the installed protocol library does not serve " + ", ".join(unserved))

        async def list_tools(ctx, _params):
            self.authenticator.revalidate(ctx.request.scope["service_authentication"])
            tools = [types.Tool(name=name, description="Authorized intelligence " + operation,
                inputSchema=http_provisioning_schema(operation), annotations=types.ToolAnnotations(
                    readOnlyHint=operation != READ_OPERATION, destructiveHint=False, idempotentHint=True))
                for name, operation in TOOL_OPERATIONS.items()]
            tools.append(types.Tool(name="intelligence_search", description="Search authorized metadata only",
                inputSchema={"type": "object", "required": ["query"], "additionalProperties": False,
                    "properties": {"query": {"type": "string"}, "mode": {"enum": ["lexical", "hybrid"]},
                                   "top_n": {"type": "integer", "minimum": 1},
                                   "filters": {"type": "object"}}}))
            return types.ListToolsResult(tools=tools)

        async def call_tool(ctx, params):
            # The library passes the arguments as sent; this transport has
            # always read an absent argument object as an empty one.
            name, arguments = params.name, params.arguments or {}
            scope = ctx.request.scope
            try:
                context = scope["service_authentication"]
                if name == "intelligence_search":
                    fields = self._validate_search(arguments, versioned=False)
                    output = await self._tenant_work(context, lambda: invoke_http_retrieval_as_loop(lambda: self._search(context, fields)))
                else:
                    operation = TOOL_OPERATIONS.get(name)
                    if operation is None:
                        raise ServiceHttpError("unsupported_operation")
                    validate(arguments, http_provisioning_schema(operation))
                    if operation == READ_OPERATION and not arguments.get("request_id"):
                        raise ServiceHttpError("request_identity_required")
                    output = await self._tenant_work(context, lambda: invoke_http_service_as_loop(operation,
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
            # A protocol tool refusal is a failed request too, and the harness
            # that made it sees the same reference the operator searches for.
            # The record goes through the same guarded writer as every other
            # refusal, so recording it can never turn into a different failure.
            await self._record_failure(scope, ctx.request, code, status)
            reference = scope.get(SCOPE_REFERENCE_KEY)
            refused = _error_record(code, status, None, reference.value if reference is not None else None)
            return types.CallToolResult(content=[types.TextContent(type="text", text=_json_bytes(refused).decode())],
                                        structuredContent=refused, isError=True)

        hint = CacheHint(ttl_ms=PROTOCOL_CACHE_TTL_MS, scope=PROTOCOL_CACHE_SCOPE)
        sdk = Server("loop-engine-intelligence", version="1.0.0", on_list_tools=list_tools, on_call_tool=call_tool,
                     cache_hints={"tools/list": hint, "server/discover": hint})

        async def discover(ctx, _params):
            # The library's own answer lists every version it can speak. This
            # one lists what this host serves, newest first, in both kinds, as
            # the specification's example of a server that serves both does.
            self.authenticator.revalidate(ctx.request.scope["service_authentication"])
            return types.DiscoverResult(supported_versions=list(reversed(configuration.protocol_versions)),
                                        capabilities=sdk.get_capabilities(protocol_version=ctx.protocol_version))
        sdk.add_request_handler("server/discover", types.RequestParams, discover)
        # The library records every protocol message as a trace span by
        # default. The service has no telemetry setting for protocol traffic,
        # and telemetry needs an explicit one, so it records none.
        sdk.middleware = []
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
            schedule = self.retention_schedule
            schedule.start()
            try:
                async with manager.run(), self._catalogue_refresh():
                    yield
            finally:
                await schedule.stop()
            self._workers.shutdown(wait=False, cancel_futures=False)

        async def transport(scope, receive, send):
            request = Request(scope, receive)
            # Every request is named before any work, so a refusal raised at the
            # very first check still carries an identity the operator can find.
            reference = new_request_reference()
            scope[SCOPE_REFERENCE_KEY] = reference
            sent_origins = request.headers.getlist("origin")
            origin = selected_origin(sent_origins)
            cors = ({"Access-Control-Allow-Origin": origin, "Vary": "Origin",
                     "Access-Control-Expose-Headers": "X-Content-SHA256, X-Loop-Engine-Record-Type"}
                    if origin is not None and origin in config.allowed_origins else {})
            try:
                if (len(request.headers.getlist("host")) != 1
                        or request.headers["host"] not in config.allowed_hosts):
                    raise ServiceHttpError("invalid_host", 421)
                if sent_origins and (origin is None or origin not in config.allowed_origins):
                    raise ServiceHttpError("invalid_origin", 403)
                if request.method == "OPTIONS":
                    if origin not in config.allowed_origins:
                        raise ServiceHttpError("invalid_origin", 403)
                    response = Response(status_code=204, headers={**cors,
                        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                        "Access-Control-Allow-Headers": "Authorization, Content-Type, MCP-Protocol-Version, Stripe-Signature"})
                elif request.url.path == PROTOCOL_PATH:
                    context = await self._authenticated(request)
                    if request.method != "POST":
                        # One POST endpoint in both kinds of version: this
                        # service keeps no session, so there is no stream to
                        # open with GET and no session to end with DELETE.
                        raise ServiceHttpError("protocol_method_not_allowed", 405, headers={"Allow": "POST"})
                    body = await self._body(request)
                    payload = _parse_json(body) if body else {}
                    if not isinstance(payload, dict):
                        raise ServiceHttpError("object_required")
                    # The version is chosen here, before the protocol library
                    # or any effect, and the library is told the choice in the
                    # header it routes on. Every later request is checked
                    # against the served versions the same way.
                    selected, served = select_protocol_binding(
                        config, payload, request.headers.getlist(PROTOCOL_VERSION_HEADER))
                    if served is not payload:
                        body = _json_bytes(served)
                    scope["headers"] = [(name, value) for name, value in scope["headers"]
                                        if name not in (PROTOCOL_VERSION_HEADER.encode(), b"content-length")] + [
                        (PROTOCOL_VERSION_HEADER.encode(), selected.encode("ascii")),
                        (b"content-length", str(len(body)).encode("ascii"))]
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
                # The record is committed before the customer is told its name,
                # so a reference in a refusal is one an operator can search for.
                await self._record_failure(scope, request, code, status)
                # A reader who arrived in a browser needs a sentence and a way
                # back. A record shape is the right answer to a program and the
                # wrong answer to a person. The page names no address and
                # repeats nothing from the request, so nothing can be reflected
                # into it.
                if isinstance(error, ServiceHttpError) and error.protocol_error is not None:
                    # A protocol client reads the protocol's own error shape.
                    # Its code and its list of versions are what a client uses
                    # to choose a version it shares with this service.
                    response = JSONResponse(error.protocol_error, status_code=status, headers=cors)
                elif status == 404 and "text/html" in request.headers.get("accept", ""):
                    response = Response(
                        missing_address_page(config.display_name),
                        status_code=404, media_type=HTML_MEDIA_TYPE,
                        headers={**cors, **self._page_headers()})
                else:
                    response = JSONResponse(_error_record(code, status, details, reference.value),
                                            status_code=status, headers={**cors, **(added or {})})
                if status == 401:
                    response.headers["WWW-Authenticate"] = ("Bearer resource_metadata=\""
                        + config.public_base_url + "/.well-known/oauth-protected-resource/mcp\""
                        if EXTERNAL_JWT_AUTHENTICATION in self.authentication.modes else "Bearer")
            response.headers["Cache-Control"] = "no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
            await response(scope, receive, send)
        return Starlette(routes=[Mount("/", app=transport)], lifespan=lifespan)

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
        body = b"".join(chunks)
        # This is the one place every JSON body of this service passes through.
        # The body is kept for a later failure record only when the host has
        # chosen to capture request bodies. Under the default choice nothing is
        # kept, so there is nothing a failure record could disclose. A header is
        # never kept here, so the credential cannot reach a record this way, and
        # a body that is itself a credential is never kept under any choice.
        if self.observability.captures_request_body and request.url.path not in CREDENTIAL_BODY_ROUTES:
            request.scope[CAPTURED_BODY_KEY] = body
        return body

    @asynccontextmanager
    async def _catalogue_refresh(self):
        """Run the host's catalogue refresher for the life of the application, then stop it."""
        refresher = self.catalogue_refresher
        task = asyncio.create_task(refresher.run()) if refresher is not None else None
        try:
            yield
        finally:
            if task is not None:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)

    def _page_headers(self):
        """The headers every served page carries, refusals included."""
        identity_origin = " " + self.browser_identity.configuration.project_url if self.browser_identity else ""
        return {"Content-Security-Policy": "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'"
                + identity_origin + "; base-uri 'none'; frame-ancestors 'none'; form-action 'none'",
                "Referrer-Policy": "no-referrer", "X-Frame-Options": "DENY",
                "Permissions-Policy": "camera=(), microphone=(), geolocation=()"}

    async def _web_route(self, request, Response, JSONResponse):
        path, method, status_code = request.url.path, request.method, 200
        asset = served_asset(path, method, self.configuration.display_name)
        if asset is not None:
            body, media_type = asset
            return Response(body, media_type=media_type, headers=self._page_headers())
        # Decide whether this service serves the address before asking who is
        # calling. An unknown address that is authenticated first answers 401
        # unauthorized, which sends the reader looking for a credential fault
        # that does not exist, and hides a wrong address from the person who
        # published it. A known address reached with the wrong method is the
        # same missing-page answer, so only the exact method reaches a
        # provider or an effect.
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
            # Alive and ready are different answers. Alive says this process is
            # running. Ready says every required dependency answered just now.
            # A machine that is not ready answers 503, so the load balancer in
            # front of it stops sending customers to it.
            output = await self._readiness()
            status_code = 200 if output["ready"] else 503
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
                # Account activation reads the identity provider, so it draws
                # on the share held by work that waits on another service.
                output = await self._work(lambda: invoke_http_service_as_loop("account_activation",
                    lambda: self.browser_identity.activate(request.headers["authorization"][7:])),
                    shares=(EXTERNAL_PROVIDER_SHARE,))
        elif path in ("/api/v1/account/signup", "/api/v1/account/recovery") and method == "POST":
            if self.account_email is None:
                raise ServiceHttpError("account_email_unavailable", 404)
            async with self._limited(request) as address:
                prepared = self.account_email.prepare(path.rsplit("/", 1)[-1], _parse_json(await self._body(request)), address)
                output, status_code = await self._work(lambda: invoke_http_service_as_loop(prepared.operation,
                    lambda: self.account_email.deliver(prepared))), 202
        elif path == WAITLIST_PATH and method == "POST":
            # No sign-in: the address is the request. A refused request counts
            # as a refused attempt from one client address, and the list itself
            # counts accepted entries for each declared source. With no declared
            # source the limiter names no address, and the list records that no
            # count was taken.
            async with self._limited(request) as address:
                joining = join_request(self.waitlist, _parse_json(await self._body(request)), address)
                output = await self._work(lambda: invoke_http_service_as_loop("waitlist_join",
                    lambda: self.waitlist.join(joining)))
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
                output = await self._tenant_work(context, lambda: invoke_http_service_as_loop("account_logout",
                    lambda: self.browser_identity.logout(context)))
            elif path == "/api/v1/usage" and method == "GET":
                output = await self._tenant_work(context, lambda: invoke_http_service_as_loop("usage",
                    lambda: self._usage(context)))
            elif path == "/api/v1/account/access" and method in ("GET", "POST"):
                if request.query_params:
                    raise ServiceHttpError("unknown_request_field")
                fields = _parse_json(await self._body(request)) if method == "POST" else None
                output = await self._tenant_work(context, lambda: invoke_http_service_as_loop("client_access",
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
                output = await self._tenant_work(context, lambda: invoke_http_service_as_loop("access_administration", administer))
            elif path == ADMIN_WAITLIST_PATH and method in ("GET", "POST"):
                self._require_scope(context, ACCESS_MANAGE_SCOPE)
                decided = _parse_json(await self._body(request)) if method == "POST" else None
                output = await self._tenant_work(context, lambda: invoke_http_service_as_loop(
                    "waitlist_administration",
                    lambda: administer_waitlist(self.waitlist, self.authenticator.revalidate(context), decided)))
            elif path == BILLING_PLANS_PATH and method == "GET":
                output = await self._tenant_work(context, lambda: invoke_http_service_as_loop("billing_plans",
                    lambda: self._session_options(context)))
            elif path in (BILLING_CHECKOUT_PATH, BILLING_PORTAL_PATH) and method == "POST":
                from .stripe_sessions import BillingSessionRequest, CHECKOUT_OPERATION, PORTAL_OPERATION
                operation = CHECKOUT_OPERATION if path == BILLING_CHECKOUT_PATH else PORTAL_OPERATION
                payload = BillingSessionRequest.from_dict(_parse_json(await self._body(request)), operation)
                # Creating a session calls the payment provider and waits for
                # it, so it draws on the same share as every other provider wait.
                output = await self._work(lambda: invoke_http_service_as_loop(operation,
                    lambda: self._create_billing_session(context, payload)),
                    shares=(context.principal.tenant_id, EXTERNAL_PROVIDER_SHARE))
            elif path in ("/api/v1/provisioning", "/api/v1/download") and method == "POST":
                operation, fields = self._validate_provisioning(_parse_json(await self._body(request)))
                if path.endswith("download"):
                    if operation != READ_OPERATION:
                        raise ServiceHttpError("download_requires_read")
                    selected_path = fields.pop("path", None)
                    def download():
                        current = self.authenticator.revalidate(context)
                        self._require_scope(current, "provisioning:read")
                        view = self.provisioning.current_view()
                        manifest = self.provisioning.invoke_for_principal(current.principal, MANIFEST_OPERATION,
                            view=view, **{key: value for key, value in fields.items() if key != "request_id"})
                        if manifest["size_bytes"] > self.configuration.maximum_download_bytes:
                            raise ServiceHttpError("download_limit_exceeded", 413)
                        value = self.provisioning.invoke_for_principal(current.principal, READ_OPERATION,
                                                                        view=view, **fields)
                        self.authenticator.revalidate(context)
                        if len(value["body"].encode("utf-8")) > self.configuration.maximum_download_bytes:
                            raise ServiceHttpError("download_limit_exceeded", 413)
                        if selected_path is not None:
                            # The item's own read was authorized and metered
                            # above; one file of its package is then read from
                            # the same view and checked against its digest.
                            payload, entry = view.read_package_file(value["identity"], selected_path)
                            if len(payload) > self.configuration.maximum_download_bytes:
                                raise ServiceHttpError("download_limit_exceeded", 413)
                            return {**value, "body": None, "file": payload, "digest": entry.digest}
                        return value
                    output = await self._tenant_work(context, lambda: invoke_http_service_as_loop("download", download))
                    value = output["result"]
                    return Response(value["file"] if value.get("file") is not None else value["body"].encode("utf-8"),
                        media_type="application/octet-stream",
                        headers={"X-Loop-Engine-Record-Type": "service_download/v1",
                                 "X-Content-SHA256": value["digest"],
                                 "Content-Disposition": 'attachment; filename="intelligence.txt"'})
                output = await self._tenant_work(context, lambda: invoke_http_service_as_loop(operation,
                    lambda: self._invoke(context, operation, fields)))
            elif path == "/api/v1/retrieval" and method == "POST":
                fields = self._validate_search(_parse_json(await self._body(request)))
                output = await self._tenant_work(context, lambda: invoke_http_retrieval_as_loop(lambda: self._search(context, fields)))
            else:
                raise ServiceHttpError("route_unavailable", 404)
        if output.get("record_type") != RESULT_VERSION:
            output = {"record_type": RESULT_VERSION, "operation": path.rsplit("/", 1)[-1], "result": output}
        encoded = _json_bytes(output)
        if len(encoded) > self.configuration.maximum_response_bytes:
            raise ServiceHttpError("response_limit_exceeded", 413)
        return Response(encoded, media_type="application/json", status_code=status_code)
