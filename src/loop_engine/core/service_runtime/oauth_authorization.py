"""Durable MCP OAuth grants over existing service accounts and catalogue records.

Supabase remains the sign-in authority. The HTTP owner authenticates the browser,
checks Origin/CSRF, and calls an explicit consent decision. This module performs
no network request, creates no user, and changes no account entitlement. The
installed MCP SDK owns OAuth transport and PKCE verification; its token route
must also call validate_token_request because SDK 2.2.0 does not check resource
on code/refresh exchanges. Access, refresh and authorization codes persist only
as digests. Public PKCE clients are the only supported registration profile.
"""
from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass, field
import hashlib
import re
import secrets
from urllib.parse import urlsplit

from mcp.server.auth.provider import (
    AccessToken, AuthorizationCode, AuthorizationParams, AuthorizeError as _SdkAuthorizeError,
    RefreshToken, RegistrationError as _SdkRegistrationError, TokenError as _SdkTokenError, construct_redirect_uri,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

from . import account_origin
from .browser_identity import VerifiedIdentity
from .http_auth import AuthenticatedHttpRequest, BROWSER_IDENTITY_AUTHENTICATION
from .records import DEFAULT_SCOPES, ServicePrincipal, ServiceRuntimeError, digest
from .runtime import ServiceRuntime, SESSION_REVOCATION, SUBJECT


class _ExceptionTraceback:
    """Keep SDK 2.2.0's error fields frozen, but permit Python's exception machinery.

    contextlib/unittest on supported Python 3.11/3.12 assign traceback metadata.
    The SDK's frozen dataclass exceptions otherwise replace the real refusal
    with FrozenInstanceError. These subtypes still match every SDK handler.
    """
    def __setattr__(self, name, value):
        if name in ("__traceback__", "__context__", "__cause__", "__suppress_context__"):
            return BaseException.__setattr__(self, name, value)
        return super().__setattr__(name, value)


class AuthorizeError(_ExceptionTraceback, _SdkAuthorizeError):
    """SDK-compatible authorization refusal with normal Python traceback behavior."""


class RegistrationError(_ExceptionTraceback, _SdkRegistrationError):
    """SDK-compatible registration refusal with normal Python traceback behavior."""


class TokenError(_ExceptionTraceback, _SdkTokenError):
    """SDK-compatible token refusal with normal Python traceback behavior."""


OAUTH_ACCESS_MODE = "oauth_access_token"
POLICY_VERSION = "service_oauth_authorization_policy/v1"
CLIENT, REQUEST, CODE, GRANT, ACCESS, REFRESH, LIMITS = (
    "service_oauth_client", "service_oauth_request", "service_oauth_code", "service_oauth_grant",
    "service_oauth_access", "service_oauth_refresh", "service_oauth_limits",
)
FIELDS = {
    CLIENT: {"client", "enabled"},
    REQUEST: {"client_id", "params", "status", "expires_at"},
    CODE: {"client_id", "scopes", "expires_at", "subject", "tenant_id", "subject_ref", "code_challenge",
           "redirect_uri", "redirect_uri_provided_explicitly", "resource", "status"},
    GRANT: {"client_id", "scopes", "expires_at", "subject", "tenant_id", "subject_ref", "resource", "generation", "revoked"},
    ACCESS: {"client_id", "grant_id", "scopes", "expires_at", "resource", "subject", "generation"},
    REFRESH: {"client_id", "grant_id", "scopes", "expires_at", "resource", "subject", "generation"},
    LIMITS: {"records", "clients"},
}
TOKEN_PATTERN = re.compile(r"(?:boar|boac|boat|bort)_[A-Za-z0-9_-]{43}\Z")
CLIENT_PATTERN = re.compile(r"[A-Za-z0-9_.:-]{1,128}\Z")
OPENAI_CALLBACK_PREFIX = "https://chatgpt.com/connector/oauth/"
#: The redirect addresses of the hosted MCP clients this service accepts, each exactly as the client's own
#: documentation or source names it, read on October 9, 2026: (client, address, source). The source is an id in the
#: source tables of `docs/guides/chatgpt-app.md`, which give its address, the date it was read and the SHA-256 prefix
#: of the bytes read; tools/test_oauth_authorization.py holds every id to that table. A registration may name one of
#: these exactly; never a prefix of one, a path below one, another port or another host.
HOSTED_CLIENT_REDIRECTS = (
    ("ChatGPT, stable redirect with issuer identification",
     "https://chatgpt.com/connector_platform_oauth_redirect", "S5"),
    ("Claude on the web, Claude Desktop, Claude mobile and Cowork", "https://claude.ai/api/mcp/auth_callback", "S19"),
    ("Cursor on the web and Cursor Agents", "https://www.cursor.com/agents/mcp/oauth/callback", "S20"),
    ("VS Code, through its vscode.dev redirect page", "https://vscode.dev/redirect", "S21"),
    ("VS Code Insiders, registered beside vscode.dev by every VS Code registration",
     "https://insiders.vscode.dev/redirect", "S22"),
)
#: The hosts a native client listens on for its redirect (RFC 8252 sections 7.3 and 8.3).
LOOPBACK_HOSTS = ("localhost", "127.0.0.1", "::1")
#: The loopback paths a native client may redirect to on any port. "/" is the root path, written with or without its
#: slash: VS Code registers `http://127.0.0.1/` and `http://127.0.0.1:33418/` (its `fetchDynamicRegistration`,
#: source S22). "/callback" is Claude Code's, Codex's and Cursor's desktop app's, "/mcp/oauth/callback" OpenCode's.
NATIVE_LOOPBACK_PATHS = ("/", "/callback", "/oauth/callback", "/auth/callback", "/mcp/oauth/callback")
#: Loopback paths after which one server-specific callback identifier may follow: Codex appends one to
#: `/callback` when an authorization server does not advertise issuer identification (source S24).
NATIVE_LOOPBACK_CALLBACK_ID_PATHS = ("/callback",)
#: That identifier: the URL-safe Base64 of the first nine bytes of a SHA-256 without padding, so exactly twelve
#: characters (`callback_id_from_server_url` in Codex's codex-rs/rmcp-client/src/oauth_callback.rs, source S25).
CALLBACK_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{12}\Z")
#: A write that would pass a storage ceiling removes at most this many rows no request can use any more.
RECLAIM_LIMIT = 10_000
#: Looking for those rows reads every OAuth row of the policy, about 60 microseconds a row (1.2 seconds at 20,000).
#: After a look that leaves less than 1/64 of a ceiling free, writes that would pass a ceiling are refused without
#: another look for this many seconds per row it read, whole seconds only: a minute at 20,000 rows and none below 334.
#: So a store full of live rows spends about 2% of its time looking, not one look for every refused write.
RECLAIM_RETRY_SECONDS_PER_ROW = 0.003


def _url(value, *, loopback=False):
    if not isinstance(value, str) or len(value) > 2048 or any(ord(c) < 33 for c in value) or "\\" in value:
        raise ServiceRuntimeError("invalid_oauth_policy")
    try:
        parsed = urlsplit(value)
        parsed.port
    except ValueError:
        raise ServiceRuntimeError("invalid_oauth_policy") from None
    if (parsed.username is not None or parsed.password is not None or "#" in value or not parsed.hostname
            or (parsed.scheme != "https" and not (loopback and parsed.scheme == "http"
                and parsed.hostname in LOOPBACK_HOSTS))):
        raise ServiceRuntimeError("invalid_oauth_policy")
    return value


def _loopback_redirect(value):
    """The host and path of an `http` loopback redirect with a valid or absent port, no credentials, query or fragment,
    else None. The empty path is the root path."""
    if not isinstance(value, str) or len(value) > 2048 or any(ord(c) < 33 for c in value) or "\\" in value:
        return None
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return None
    if (parsed.scheme != "http" or parsed.hostname not in LOOPBACK_HOSTS or parsed.username is not None
            or parsed.password is not None or "?" in value or "#" in value or not (port is None or 1 <= port <= 65535)):
        return None
    return parsed.hostname, parsed.path or "/"


def same_redirect(requested, registered) -> bool:
    """True when a request's redirect address is the registered one: exactly, except that a loopback redirect may
    name any port when it is used, because a native client takes a free port from the system each time (RFC 8252
    section 7.3, "The authorization server MUST allow any port to be specified at the time of the request for
    loopback IP redirect URIs"; Claude's connector documentation asks the same of `localhost`, which Claude Code
    uses). Scheme, host and path still match exactly, so `localhost` never stands for `127.0.0.1`."""
    requested, registered = str(requested), str(registered)
    if requested == registered:
        return True
    loopback = _loopback_redirect(requested)
    return loopback is not None and loopback == _loopback_redirect(registered)


@dataclass(frozen=True)
class OAuthAuthorizationPolicy:
    issuer_url: str
    resource_url: str
    identity_issuer: str
    consent_url: str
    redirect_uris: tuple[str, ...] = ()
    redirect_uri_prefixes: tuple[str, ...] = ()
    native_loopback_paths: tuple[str, ...] = ()
    #: Loopback paths after which exactly one callback identifier (CALLBACK_ID_PATTERN) may follow.
    native_loopback_callback_id_paths: tuple[str, ...] = ()
    allowed_scopes: tuple[str, ...] = DEFAULT_SCOPES
    authorization_lifetime_seconds: int = 600
    code_lifetime_seconds: int = 120
    access_lifetime_seconds: int = 900
    refresh_lifetime_seconds: int = 604800
    max_clients: int = 128
    max_records: int = 20000
    allow_loopback_http: bool = False
    record_type: str = POLICY_VERSION

    def __post_init__(self):
        if self.record_type != POLICY_VERSION:
            raise ServiceRuntimeError("unsupported_oauth_policy_version")
        if type(self.allow_loopback_http) is not bool:
            raise ServiceRuntimeError("invalid_oauth_policy")
        for name in ("redirect_uris", "redirect_uri_prefixes", "native_loopback_paths",
                     "native_loopback_callback_id_paths", "allowed_scopes"):
            value = getattr(self, name)
            if not isinstance(value, (list, tuple)) or any(type(item) is not str for item in value):
                raise ServiceRuntimeError("invalid_oauth_policy")
            object.__setattr__(self, name, tuple(value))
        for value in (self.issuer_url, self.resource_url, self.identity_issuer, self.consent_url):
            _url(value, loopback=self.allow_loopback_http)
            if urlsplit(value).query:
                raise ServiceRuntimeError("invalid_oauth_policy")
        if urlsplit(self.consent_url).netloc != urlsplit(self.issuer_url).netloc:
            raise ServiceRuntimeError("invalid_oauth_policy")
        for value in self.redirect_uris:
            _url(value, loopback=True)
            # An authorization response adds its fields to the address's query; an exact address that brings a
            # query of its own could carry a second `iss` or `state`, so none may.
            if "?" in value:
                raise ServiceRuntimeError("invalid_oauth_redirect_policy")
        if set(self.redirect_uri_prefixes) - {OPENAI_CALLBACK_PREFIX}:
            raise ServiceRuntimeError("invalid_oauth_redirect_policy")
        if any(not re.fullmatch(r"/[A-Za-z0-9._~/-]*", path) or "//" in path
               or any(part in (".", "..") for part in path.split("/")) for path in self.native_loopback_paths):
            raise ServiceRuntimeError("invalid_oauth_redirect_policy")
        # A callback identifier follows a named path, never the root path and never a path that ends in a slash.
        if any(not re.fullmatch(r"(?:/[A-Za-z0-9._~-]+)+", path)
               or any(part in (".", "..") for part in path.split("/")) for path in self.native_loopback_callback_id_paths):
            raise ServiceRuntimeError("invalid_oauth_redirect_policy")
        if not self.redirect_uris and not self.redirect_uri_prefixes and not self.native_loopback_paths:
            raise ServiceRuntimeError("oauth_redirect_policy_required")
        for name in ("authorization_lifetime_seconds", "code_lifetime_seconds", "access_lifetime_seconds",
                     "refresh_lifetime_seconds", "max_clients", "max_records"):
            value = getattr(self, name)
            if type(value) is not int or value < 1:
                raise ServiceRuntimeError("invalid_oauth_policy")
        if (self.code_lifetime_seconds > self.authorization_lifetime_seconds
                or self.access_lifetime_seconds > self.refresh_lifetime_seconds or self.max_clients > self.max_records
                or not self.allowed_scopes or set(self.allowed_scopes) - set(DEFAULT_SCOPES)
                or len(set(self.allowed_scopes)) != len(self.allowed_scopes)):
            raise ServiceRuntimeError("invalid_oauth_policy")

    def permits_redirect(self, value):
        """True for an exact listed address, a listed prefix followed by one literal segment, or an `http` loopback
        address on a listed path (or a listed callback path and one callback identifier) on any port."""
        if not isinstance(value, str) or len(value) > 2048 or any(ord(c) < 33 for c in value) or "\\" in value:
            return False
        if value in self.redirect_uris:
            return True
        loopback = _loopback_redirect(value)
        if loopback is not None:
            path = loopback[1]
            if path in self.native_loopback_paths:
                return True
            base, _, identifier = path.rpartition("/")
            return base in self.native_loopback_callback_id_paths and CALLBACK_ID_PATTERN.fullmatch(identifier) is not None
        return any(value.startswith(prefix) and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value[len(prefix):])
                   for prefix in self.redirect_uri_prefixes)

    def to_dict(self):
        return asdict(self)


class RegisteredOAuthClient(OAuthClientInformationFull):
    """A stored client as the pinned SDK's authorization handler reads it, with `same_redirect` as its redirect rule.

    SDK 2.2.0 compares a requested redirect with the registered ones exactly, so a native client that registered
    `http://127.0.0.1/` and then listens on a port the system chose would be refused. Every other check is the SDK's.
    """

    def validate_redirect_uri(self, redirect_uri):
        if redirect_uri is not None and any(same_redirect(redirect_uri, uri) for uri in self.redirect_uris or ()):
            return redirect_uri
        return super().validate_redirect_uri(redirect_uri)


@dataclass(frozen=True)
class OAuthAccessContext:
    principal: ServicePrincipal = field(repr=False)
    scopes: tuple[str, ...]
    expires_at: int
    client_id: str
    subject: str
    resource: str
    grant_id: str = field(repr=False)
    #: The presentation of `/mcp` this delegation's client reads, from its registered redirects (see
    #: `chatgpt_app.profile_for_client`). Presentation only: the scopes above are the whole authority.
    client_profile: str = ""


class OAuthAuthorizationProvider:
    """SDK provider with atomic single-use codes, rotating grants and live account checks.

    max_records caps retained OAuth payload rows, excluding the one counter row,
    and max_clients the registered clients among them. A write that would pass
    a ceiling first removes the rows no request can use any more (_reclaim) and
    recounts the rows that stay; nothing else deletes a row or resets the counter.
    Storage/unknown-commit errors propagate; callers must not return credentials
    or repeat a write after such an error. All blocking store work uses threads.
    """

    def __init__(self, runtime: ServiceRuntime, policy: OAuthAuthorizationPolicy):
        if not isinstance(runtime, ServiceRuntime) or not isinstance(policy, OAuthAuthorizationPolicy):
            raise ServiceRuntimeError("invalid_oauth_policy")
        self.runtime, self.policy, self.catalog = runtime, policy, runtime._catalog
        self.policy_id = digest(["service_oauth/v1", policy.issuer_url, policy.resource_url, policy.identity_issuer])
        self._reclaim_after = 0  # Read and written only inside the counter's turn (_commit).

    def _now(self):
        return int(self.runtime._now())

    def _scopes(self, value):
        if (not isinstance(value, (list, tuple)) or not value or any(type(item) is not str for item in value)
                or len(set(value)) != len(value) or set(value) - set(self.policy.allowed_scopes)):
            raise TokenError("invalid_scope", "unsupported or empty scope set")
        return list(value)

    def _payload(self, row, kind):
        if row is None:
            return None
        value = row.get("payload")
        if (not isinstance(value, dict) or set(value) != FIELDS[kind] | {"record_type", "policy_id"}
                or value["record_type"] != kind + "/v1" or value["policy_id"] != self.policy_id):
            raise ServiceRuntimeError("oauth_record_invalid")
        return value

    def _record(self, kind, identity, value):
        return self.catalog.record(kind, identity, {"record_type": kind + "/v1", "policy_id": self.policy_id, **value})

    def _read(self, store, kind, identity):
        row = self.catalog.read(store, kind, identity)
        return row, self._payload(row, kind)

    def _commit(self, store, records, guards, *, new_records=0, new_clients=0):
        records, guards = list(records), list(guards)
        if not new_records:
            return self.catalog.commit(store, records, guards)
        # Every write that adds records changes the one counter row. The writes of this process take turns from
        # reading it to the commit, so concurrent authorizations and refreshes wait for one another instead of
        # refusing one another; the counter's version guard still refuses a write of another process.
        with self.catalog.serialized(LIMITS):
            prior, value = self._read(store, LIMITS, self.policy_id)
            value = value or {"records": 0, "clients": 0}
            if any(type(value[key]) is not int or value[key] < 0 for key in ("records", "clients")):
                raise ServiceRuntimeError("oauth_record_invalid")
            count, clients = value["records"] + new_records, value["clients"] + new_clients
            removals = ()
            if count > self.policy.max_records or clients > self.policy.max_clients:
                count, clients, removals, removal_guards = self._reclaim(store, records, guards, new_records, new_clients)
                guards.extend(removal_guards)
            counter = self._record(LIMITS, self.policy_id, {"records": count, "clients": clients})
            records.append(counter)
            guards.append(self.catalog.guard(prior, counter["record_id"]))
            return self.catalog.commit(store, records, guards, removals)

    def _reclaim(self, store, records, guards, new_records, new_clients):
        """Make room by removing in this write's batch the rows no request can use any more, as the write leaves them.

        Those are decided or expired requests, used or expired codes, revoked or expired grants, and tokens that
        expired or whose grant is gone, dead or at another generation, so a refresh frees the pair it replaces. Only
        when the client ceiling is passed, also clients with no live request, code or grant once their first
        authorization lifetime has passed. A row this provider cannot read is kept. The counts are taken from the
        stored rows, so the counter counts exactly what stays. Every removal carries the exact version it was read at.
        """
        now = self._now()
        if now < self._reclaim_after:
            raise ServiceRuntimeError("oauth_storage_limit")
        written = {row["record_id"]: row for row in records}
        stored = {kind: [row for row in self.catalog.rows(store, kind, "")
                         if isinstance(row.get("payload"), dict) and row["payload"].get("policy_id") == self.policy_id]
                  for kind in (CLIENT, REQUEST, CODE, GRANT, ACCESS, REFRESH)}
        values = {}
        for kind, rows in stored.items():
            current = {row["record_id"]: row for row in rows}
            current.update({identity: row for identity, row in written.items() if row["artifact_kind"] == kind})
            values[kind] = {}
            for identity, row in current.items():
                try:
                    values[kind][identity] = self._payload(row, kind)
                except ServiceRuntimeError:
                    values[kind][identity] = None
        def alive(kind, value):
            if kind == REQUEST:
                return value["status"] == "pending" and value["expires_at"] > now
            if kind == CODE:
                return value["status"] == "ready" and value["expires_at"] > now
            if kind == GRANT:
                return value["revoked"] is False and value["expires_at"] > now
            identity = self.catalog.identity(GRANT, value["grant_id"])
            grant = values[GRANT].get(identity)
            if identity in values[GRANT] and grant is None:
                return True
            return (value["expires_at"] > now and grant is not None and alive(GRANT, grant)
                    and grant["generation"] == value["generation"])
        dead = [row for kind in (REQUEST, CODE, GRANT, ACCESS, REFRESH) for row in stored[kind]
                if row["record_id"] not in written and values[kind][row["record_id"]] is not None
                and not alive(kind, values[kind][row["record_id"]])]
        clients = len(stored[CLIENT]) + new_clients
        if clients > self.policy.max_clients:
            used = {value["client_id"] for kind in (REQUEST, CODE, GRANT) for value in values[kind].values()
                    if value is not None and alive(kind, value)}
            for row in stored[CLIENT]:
                value = values[CLIENT][row["record_id"]]
                issued = value["client"].get("client_id_issued_at") if value is not None else None
                if (value is not None and row["record_id"] not in written and value["client"].get("client_id") not in used
                        and not (type(issued) is int and issued + self.policy.authorization_lifetime_seconds > now)):
                    dead.append(row)
        guarded = {guard.record_id: guard for guard in guards}
        removals, removal_guards = [], []
        for row in dead:
            if len(removals) == RECLAIM_LIMIT:
                break
            guard = guarded.get(row["record_id"])
            if guard is None:
                removal_guards.append(self.catalog.guard(row))
            elif guard.must_not_exist or guard.record_version != row["record_version"]:
                continue
            removals.append(row)
        count = sum(map(len, stored.values())) + new_records - len(removals)
        clients -= sum(row["artifact_kind"] == CLIENT for row in removals)
        if (count > self.policy.max_records - self.policy.max_records // 64
                or clients > self.policy.max_clients - self.policy.max_clients // 64):
            self._reclaim_after = now + int(sum(map(len, stored.values())) * RECLAIM_RETRY_SECONDS_PER_ROW)
        if count > self.policy.max_records or clients > self.policy.max_clients:
            raise ServiceRuntimeError("oauth_storage_limit")
        return count, clients, [row["record_id"] for row in removals], removal_guards

    def _client(self, store, client_id):
        if not isinstance(client_id, str) or not CLIENT_PATTERN.fullmatch(client_id):
            return None, None
        row, value = self._read(store, CLIENT, client_id)
        if value is None or value["enabled"] is not True:
            return None, None
        client = RegisteredOAuthClient.model_validate(value["client"])
        if (client.client_id != client_id or client.token_endpoint_auth_method != "none" or client.client_secret
                or not client.redirect_uris or not all(self.policy.permits_redirect(str(uri)) for uri in client.redirect_uris)):
            return None, None
        try:
            self._scopes((client.scope or "").split())
        except TokenError:
            return None, None
        return row, client

    async def get_client(self, client_id):
        def get():
            with self.catalog.store() as store:
                return self._client(store, client_id)[1]
        return await asyncio.to_thread(get)

    async def register_client(self, client_info):
        def register():
            if (not isinstance(client_info, OAuthClientInformationFull) or not client_info.client_id
                    or not CLIENT_PATTERN.fullmatch(client_info.client_id) or client_info.client_secret is not None
                    or client_info.token_endpoint_auth_method != "none"
                    or set(client_info.grant_types) != {"authorization_code", "refresh_token"}
                    or client_info.response_types != ["code"] or not client_info.redirect_uris
                    or len(client_info.redirect_uris) > 8 or not client_info.client_name or len(client_info.client_name) > 128
                    or any(ord(c) < 32 for c in client_info.client_name)):
                raise RegistrationError("invalid_client_metadata", "only named public authorization-code/refresh clients are supported")
            if not all(self.policy.permits_redirect(str(uri)) for uri in client_info.redirect_uris):
                raise RegistrationError("invalid_redirect_uri", "redirect is outside the host allowlist")
            try:
                scopes = self._scopes((client_info.scope or "").split())
            except TokenError:
                raise RegistrationError("invalid_client_metadata", "unsupported scopes") from None
            # Store the finite supported metadata only; no client secret or remote metadata fetch.
            client = OAuthClientInformationFull(client_id=client_info.client_id, client_name=client_info.client_name,
                redirect_uris=client_info.redirect_uris, token_endpoint_auth_method="none",
                grant_types=["authorization_code", "refresh_token"], response_types=["code"], scope=" ".join(scopes))
            with self.catalog.store(write=True) as store:
                prior, held = self._read(store, CLIENT, client.client_id)
                data = {"client": client.model_dump(mode="json"), "enabled": True}
                if held is not None:
                    # The time of issue is the first registration's; the same metadata again is the same client.
                    if {**held["client"], "client_id_issued_at": None} != data["client"] or held["enabled"] is not True:
                        raise RegistrationError("invalid_client_metadata", "client identity already exists")
                    return
                # The time of issue lets an unused client be removed at the client ceiling once its first
                # authorization lifetime has passed (_reclaim); a client stored without one counts as old.
                data["client"]["client_id_issued_at"] = self._now()
                row = self._record(CLIENT, client.client_id, data)
                self._commit(store, (row,), (self.catalog.guard(prior, row["record_id"]),), new_records=1, new_clients=1)
        return await asyncio.to_thread(register)

    async def authorize(self, client, params):
        def authorize():
            if not isinstance(params, AuthorizationParams) or params.resource != self.policy.resource_url:
                raise AuthorizeError("invalid_target", "resource must match this MCP server")
            if (not params.state or len(params.state) > 1024 or any(ord(c) < 32 for c in params.state)
                    or not re.fullmatch(r"[A-Za-z0-9_-]{43}", params.code_challenge)):
                raise AuthorizeError("invalid_request", "state and a valid S256 challenge are required")
            with self.catalog.store(write=True) as store:
                client_row, held = self._client(store, client.client_id)
                if held is None or not any(same_redirect(params.redirect_uri, uri) for uri in held.redirect_uris):
                    raise AuthorizeError("unauthorized_client", "client or redirect unavailable")
                try:
                    scopes = self._scopes(params.scopes if params.scopes is not None else held.scope.split())
                except TokenError:
                    raise AuthorizeError("invalid_scope", "unsupported scopes") from None
                if not set(scopes) <= set(held.scope.split()):
                    raise AuthorizeError("invalid_scope", "scope exceeds registered client")
                request_id = "boar_" + secrets.token_urlsafe(32)
                data = params.model_dump(mode="json")
                data["scopes"] = scopes
                row = self._record(REQUEST, self._hash(request_id), {"client_id": held.client_id, "params": data,
                    "status": "pending", "expires_at": self._now() + self.policy.authorization_lifetime_seconds})
                self._commit(store, (row,), (self.catalog.guard(client_row), self.catalog.guard(None, row["record_id"])), new_records=1)
            return construct_redirect_uri(self.policy.consent_url, authorization_id=request_id)
        return await asyncio.to_thread(authorize)

    @staticmethod
    def _hash(raw):
        if not isinstance(raw, str) or not TOKEN_PATTERN.fullmatch(raw):
            raise TokenError("invalid_grant", "invalid credential shape")
        return hashlib.sha256(raw.encode("ascii")).hexdigest()

    def _pending(self, store, request_id):
        row, value = self._read(store, REQUEST, self._hash(request_id))
        if value is None or value["status"] != "pending" or value["expires_at"] <= self._now():
            raise AuthorizeError("invalid_request", "authorization is expired or already decided")
        client_row, client = self._client(store, value["client_id"])
        if client is None:
            raise AuthorizeError("unauthorized_client", "client is unavailable")
        params = AuthorizationParams.model_validate(value["params"])
        if params.resource != self.policy.resource_url or not self.policy.permits_redirect(str(params.redirect_uri)):
            raise AuthorizeError("invalid_target", "authorization binding changed")
        return row, value, client_row, client, params

    async def inspect_consent(self, request_id):
        def inspect():
            with self.catalog.store() as store:
                _, value, _, client, params = self._pending(store, request_id)
                return {"record_type": "service_oauth_consent/v1", "authorization_id": request_id,
                    "client_id": client.client_id, "client_name": client.client_name,
                    "redirect_uri": str(params.redirect_uri), "scopes": params.scopes,
                    "resource": params.resource, "expires_at": value["expires_at"]}
        return await asyncio.to_thread(inspect)

    def _identity(self, store, value):
        subject_row = self.catalog.read_id(store, value["subject_ref"], kind=SUBJECT)
        if subject_row is None:
            raise TokenError("invalid_grant", "account is unavailable")
        subject = self.runtime._payload(subject_row, SUBJECT)
        if (subject.get("issuer") != self.policy.identity_issuer or subject.get("subject") != value["subject"]
                or subject.get("tenant_id") != value["tenant_id"]):
            raise TokenError("invalid_grant", "subject binding changed")
        try:
            principal, guards = self.runtime._principal(store, subject_row, SUBJECT)
        except ServiceRuntimeError as error:
            if error.code in ("unauthorized", "not_found", "tenant_disabled"):
                raise TokenError("invalid_grant", "account is unavailable") from None
            raise
        origin = self.catalog.read(store, account_origin.ORIGIN, (self.policy.identity_issuer, value["subject"]))
        payload = account_origin._origin_payload(origin) if origin is not None else {}
        if payload.get("issuer") != self.policy.identity_issuer or payload.get("subject") != value["subject"]:
            raise TokenError("invalid_grant", "account origin is unavailable")
        return principal, (*guards, self.catalog.guard(origin))

    def _browser(self, store, authentication):
        if (not isinstance(authentication, AuthenticatedHttpRequest) or authentication.mode != BROWSER_IDENTITY_AUTHENTICATION
                or not isinstance(authentication.identity, VerifiedIdentity) or authentication.expires_at is None
                or authentication.identity.origin not in account_origin.ORIGINS
                or authentication.expires_at <= self._now() or authentication.principal.authentication_kind != SUBJECT):
            raise AuthorizeError("access_denied", "a current verified browser identity is required")
        current, guards = self.runtime._revalidate(store, authentication.principal)
        value = {"subject": authentication.identity.subject, "tenant_id": current.tenant_id,
                 "subject_ref": current.authentication_record_id}
        principal, identity_guards = self._identity(store, value)
        hashed = hashlib.sha256(authentication.credential.encode()).hexdigest()
        revoked = self.catalog.read(store, SESSION_REVOCATION, hashed)
        if revoked is not None:
            raise AuthorizeError("access_denied", "browser session is revoked")
        return value, principal, (*guards, *identity_guards,
            self.catalog.guard(None, self.catalog.identity(SESSION_REVOCATION, hashed)))

    async def approve_consent(self, request_id, authentication):
        return await asyncio.to_thread(self._decide, request_id, authentication, True)

    async def deny_consent(self, request_id, authentication):
        return await asyncio.to_thread(self._decide, request_id, authentication, False)

    def _decide(self, request_id, authentication, approve):
        with self.catalog.store(write=True) as store:
            pending, value, client_row, client, params = self._pending(store, request_id)
            identity, principal, guards = self._browser(store, authentication)
            chosen = self._scopes(params.scopes)
            if approve and not set(chosen) <= set(principal.scopes) & set(authentication.effective_scopes):
                raise AuthorizeError("invalid_scope", "requested scopes exceed current account authority")
            updated = self._record(REQUEST, self._hash(request_id), {**{key: value[key] for key in FIELDS[REQUEST]},
                "status": "approved" if approve else "denied"})
            rows = [updated]
            all_guards = [self.catalog.guard(pending), self.catalog.guard(client_row), *guards]
            fields = {"state": params.state, "iss": self.policy.issuer_url}
            if approve:
                raw_code = "boac_" + secrets.token_urlsafe(32)
                code = self._record(CODE, self._hash(raw_code), {**identity, "client_id": client.client_id,
                    "scopes": chosen, "expires_at": self._now() + self.policy.code_lifetime_seconds,
                    "code_challenge": params.code_challenge, "redirect_uri": str(params.redirect_uri),
                    "redirect_uri_provided_explicitly": params.redirect_uri_provided_explicitly,
                    "resource": params.resource, "status": "ready"})
                rows.append(code)
                all_guards.append(self.catalog.guard(None, code["record_id"]))
                fields["code"] = raw_code
            else:
                fields["error"] = "access_denied"
            # Several account guards reference the same unchanged row; the store requires one guard per identity.
            all_guards = tuple({guard.record_id: guard for guard in all_guards}.values())
            self._commit(store, rows, all_guards, new_records=1 if approve else 0)
            return construct_redirect_uri(str(params.redirect_uri), **fields)

    def _code(self, raw, value):
        return AuthorizationCode(code=raw, **{key: value[key] for key in (
            "scopes", "expires_at", "client_id", "code_challenge", "redirect_uri", "redirect_uri_provided_explicitly", "resource", "subject")})

    async def load_authorization_code(self, client, raw):
        def load():
            try:
                hashed = self._hash(raw)
            except TokenError:
                return None
            with self.catalog.store() as store:
                _, value = self._read(store, CODE, hashed)
                if (value is None or value["status"] != "ready" or value["expires_at"] <= self._now()
                        or value["client_id"] != client.client_id or value["resource"] != self.policy.resource_url):
                    return None
                return self._code(raw, value)
        return await asyncio.to_thread(load)

    def _tokens(self, store, grant_id, grant, scopes):
        now = self._now()
        access, refresh = "boat_" + secrets.token_urlsafe(32), "bort_" + secrets.token_urlsafe(32)
        access_until = min(now + self.policy.access_lifetime_seconds, grant["expires_at"])
        shared = {"client_id": grant["client_id"], "grant_id": grant_id, "scopes": scopes,
                  "resource": self.policy.resource_url, "subject": grant["subject"], "generation": grant["generation"]}
        rows = [self._record(ACCESS, self._hash(access), {**shared, "expires_at": access_until}),
                self._record(REFRESH, self._hash(refresh), {**shared, "expires_at": grant["expires_at"]})]
        return rows, OAuthToken(access_token=access, token_type="Bearer", expires_in=access_until - now,
                               refresh_token=refresh, scope=" ".join(scopes))

    async def exchange_authorization_code(self, client, authorization_code):
        def exchange():
            with self.catalog.store(write=True) as store:
                row, value = self._read(store, CODE, self._hash(authorization_code.code))
                client_row, held = self._client(store, client.client_id)
                if (held is None or value is None or value["status"] != "ready" or value["expires_at"] <= self._now()
                        or value["client_id"] != held.client_id or self._code(authorization_code.code, value) != authorization_code):
                    raise TokenError("invalid_grant", "authorization code is unavailable")
                principal, guards = self._identity(store, value)
                chosen = self._scopes(value["scopes"])
                if value["resource"] != self.policy.resource_url or not set(chosen) <= set(principal.scopes):
                    raise TokenError("invalid_grant", "authorization is no longer permitted")
                grant_id = secrets.token_hex(24)
                grant = {key: value[key] for key in ("client_id", "scopes", "subject", "tenant_id", "subject_ref", "resource")}
                grant.update(expires_at=self._now() + self.policy.refresh_lifetime_seconds, generation=0, revoked=False)
                grant_row = self._record(GRANT, grant_id, grant)
                tokens, response = self._tokens(store, grant_id, grant, chosen)
                consumed = self._record(CODE, self._hash(authorization_code.code), {**{key: value[key] for key in FIELDS[CODE]}, "status": "consumed"})
                self._commit(store, [consumed, grant_row, *tokens], [self.catalog.guard(row), self.catalog.guard(client_row),
                    *guards, *[self.catalog.guard(None, item["record_id"]) for item in [grant_row, *tokens]]], new_records=3)
                return response
        return await asyncio.to_thread(exchange)

    def _token_record(self, store, kind, raw, client_id=None):
        try:
            hashed = self._hash(raw)
        except TokenError:
            return None
        row, token = self._read(store, kind, hashed)
        if (token is None or token["expires_at"] <= self._now() or token["resource"] != self.policy.resource_url
                or client_id is not None and token["client_id"] != client_id):
            return None
        grant_row, grant = self._read(store, GRANT, token["grant_id"])
        client_row, client = self._client(store, token["client_id"])
        if (grant is None or grant["revoked"] is not False or grant["expires_at"] <= self._now() or client is None
                or grant["generation"] != token["generation"] or grant["client_id"] != token["client_id"]
                or grant["resource"] != token["resource"] or grant["subject"] != token["subject"]
                or not set(token["scopes"]) <= set(grant["scopes"])):
            return None
        try:
            principal, guards = self._identity(store, grant)
        except TokenError:
            return None
        return row, token, grant_row, grant, client_row, principal, guards

    async def load_refresh_token(self, client, raw):
        def load():
            with self.catalog.store() as store:
                held = self._token_record(store, REFRESH, raw, client.client_id)
                if held is None:
                    return None
                token = held[1]
                return RefreshToken(token=raw, **{key: token[key] for key in ("client_id", "scopes", "expires_at", "resource", "subject")})
        return await asyncio.to_thread(load)

    async def exchange_refresh_token(self, client, refresh_token, scopes):
        def exchange():
            chosen = self._scopes(scopes)
            with self.catalog.store(write=True) as store:
                held = self._token_record(store, REFRESH, refresh_token.token, client.client_id)
                if held is None:
                    raise TokenError("invalid_grant", "refresh token is unavailable")
                row, token, grant_row, grant, client_row, principal, guards = held
                if not set(chosen) <= set(token["scopes"]) & set(principal.scopes):
                    raise TokenError("invalid_scope", "refresh cannot expand scope")
                grant = {**{key: grant[key] for key in FIELDS[GRANT]}, "scopes": chosen, "generation": grant["generation"] + 1}
                updated = self._record(GRANT, token["grant_id"], grant)
                tokens, response = self._tokens(store, token["grant_id"], grant, chosen)
                self._commit(store, [updated, *tokens], [self.catalog.guard(row), self.catalog.guard(grant_row),
                    self.catalog.guard(client_row), *guards, *[self.catalog.guard(None, item["record_id"]) for item in tokens]], new_records=2)
                return response
        return await asyncio.to_thread(exchange)

    def resolve_access(self, raw):
        """Resolve a token on an existing HTTP worker thread; no nested event loop."""
        if not isinstance(raw, str) or not raw.startswith("boat_") or not TOKEN_PATTERN.fullmatch(raw):
            return None
        with self.catalog.store() as store:
            held = self._token_record(store, ACCESS, raw)
            if held is None:
                return None
            _, token, _, _, _, principal, _ = held
            scopes = tuple(sorted(set(token["scopes"]) & set(principal.scopes) & set(self.policy.allowed_scopes)))
            if not scopes:
                return None
            _client_row, client = self._client(store, token["client_id"])
            from .chatgpt_app import profile_for_client
            return OAuthAccessContext(principal, scopes, token["expires_at"], token["client_id"], token["subject"],
                                      token["resource"], token["grant_id"],
                                      client_profile=profile_for_client(client.redirect_uris if client else ()))

    async def access_context(self, raw):
        return await asyncio.to_thread(self.resolve_access, raw)

    async def load_access_token(self, raw):
        context = await self.access_context(raw)
        if context is None:
            return None
        return AccessToken(token=raw, client_id=context.client_id, scopes=list(context.scopes),
            expires_at=context.expires_at, resource=context.resource, subject=context.subject,
            claims={"iss": self.policy.issuer_url})

    async def revoke_token(self, token):
        def revoke():
            kind = REFRESH if isinstance(token, RefreshToken) else ACCESS
            with self.catalog.store(write=True) as store:
                held = self._token_record(store, kind, token.token, token.client_id)
                if held is None:
                    return
                _, value, grant_row, grant, client_row, _, guards = held
                updated = self._record(GRANT, value["grant_id"], {**{key: grant[key] for key in FIELDS[GRANT]}, "revoked": True})
                self._commit(store, (updated,), (self.catalog.guard(grant_row), self.catalog.guard(client_row), *guards))
        return await asyncio.to_thread(revoke)

    async def exchange_identity_assertion(self, client, params):
        raise TokenError("unsupported_grant_type", "identity assertions are not enabled by this provider")

    def validate_token_request(self, form):
        """Call before the pinned SDK token handler; reads no store and performs no effect.

        The handler parses but ignores resource on code/refresh requests. FormData
        supplies getlist; plain dictionaries are supported for direct checks.
        """
        pairs = list(form.multi_items()) if hasattr(form, "multi_items") else list(form.items())
        names = [key for key, _ in pairs]
        if len(names) != len(set(names)) or len(names) > 8 or any(not isinstance(value, str) or len(value) > 4096 for _, value in pairs):
            raise TokenError("invalid_request", "duplicate or oversized form fields")
        data = dict(pairs)
        if data.get("resource") != self.policy.resource_url:
            raise TokenError("invalid_target", "resource must match this MCP server")
        grant = data.get("grant_type")
        if grant == "authorization_code":
            if not re.fullmatch(r"[A-Za-z0-9._~-]{43,128}", data.get("code_verifier", "")):
                raise TokenError("invalid_request", "invalid PKCE verifier")
        elif grant != "refresh_token":
            raise TokenError("unsupported_grant_type", "only code and refresh grants are supported")
