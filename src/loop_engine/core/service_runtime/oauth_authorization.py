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
    AccessToken, AuthorizationCode, AuthorizationParams, AuthorizeError,
    RefreshToken, RegistrationError, TokenError, construct_redirect_uri,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

from . import account_origin
from .browser_identity import VerifiedIdentity
from .http_auth import AuthenticatedHttpRequest, BROWSER_IDENTITY_AUTHENTICATION
from .records import DEFAULT_SCOPES, ServicePrincipal, ServiceRuntimeError, digest
from .runtime import ServiceRuntime, SESSION_REVOCATION, SUBJECT

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
                and parsed.hostname in ("localhost", "127.0.0.1", "::1")))):
        raise ServiceRuntimeError("invalid_oauth_policy")
    return value


@dataclass(frozen=True)
class OAuthAuthorizationPolicy:
    issuer_url: str
    resource_url: str
    identity_issuer: str
    consent_url: str
    redirect_uris: tuple[str, ...] = ()
    redirect_uri_prefixes: tuple[str, ...] = ()
    native_loopback_paths: tuple[str, ...] = ()
    allowed_scopes: tuple[str, ...] = DEFAULT_SCOPES
    authorization_lifetime_seconds: int = 600
    code_lifetime_seconds: int = 120
    access_lifetime_seconds: int = 900
    refresh_lifetime_seconds: int = 604800
    max_clients: int = 128
    max_records: int = 20000
    record_type: str = POLICY_VERSION

    def __post_init__(self):
        if self.record_type != POLICY_VERSION:
            raise ServiceRuntimeError("unsupported_oauth_policy_version")
        for name in ("redirect_uris", "redirect_uri_prefixes", "native_loopback_paths", "allowed_scopes"):
            value = getattr(self, name)
            if not isinstance(value, (list, tuple)) or any(type(item) is not str for item in value):
                raise ServiceRuntimeError("invalid_oauth_policy")
            object.__setattr__(self, name, tuple(value))
        for value in (self.issuer_url, self.resource_url, self.identity_issuer, self.consent_url):
            _url(value)
            if urlsplit(value).query:
                raise ServiceRuntimeError("invalid_oauth_policy")
        if urlsplit(self.consent_url).netloc != urlsplit(self.issuer_url).netloc:
            raise ServiceRuntimeError("invalid_oauth_policy")
        for value in self.redirect_uris:
            _url(value, loopback=True)
        if set(self.redirect_uri_prefixes) - {OPENAI_CALLBACK_PREFIX}:
            raise ServiceRuntimeError("invalid_oauth_redirect_policy")
        if any(not re.fullmatch(r"/[A-Za-z0-9._~/-]*", path) or "//" in path
               or any(part in (".", "..") for part in path.split("/")) for path in self.native_loopback_paths):
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
        if not isinstance(value, str) or len(value) > 2048 or any(ord(c) < 33 for c in value) or "\\" in value:
            return False
        if value in self.redirect_uris:
            return True
        try:
            parsed = urlsplit(value)
            port = parsed.port
        except ValueError:
            return False
        if (parsed.scheme == "http" and parsed.hostname in ("localhost", "127.0.0.1", "::1")
                and parsed.username is None and parsed.password is None and "?" not in value and "#" not in value
                and parsed.path in self.native_loopback_paths and (port is None or 1 <= port <= 65535)):
            return True
        return any(value.startswith(prefix) and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value[len(prefix):])
                   for prefix in self.redirect_uri_prefixes)

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class OAuthAccessContext:
    principal: ServicePrincipal = field(repr=False)
    scopes: tuple[str, ...]
    expires_at: int
    client_id: str
    subject: str
    resource: str
    grant_id: str = field(repr=False)


class OAuthAuthorizationProvider:
    """SDK provider with atomic single-use codes, rotating grants and live account checks.

    max_records caps retained OAuth payload rows, excluding the one counter row.
    No expired rows are silently deleted and no quota counter is reset here.
    Storage/unknown-commit errors propagate; callers must not return credentials
    or repeat a write after such an error. All blocking store work uses threads.
    """

    def __init__(self, runtime: ServiceRuntime, policy: OAuthAuthorizationPolicy):
        if not isinstance(runtime, ServiceRuntime) or not isinstance(policy, OAuthAuthorizationPolicy):
            raise ServiceRuntimeError("invalid_oauth_policy")
        self.runtime, self.policy, self.catalog = runtime, policy, runtime._catalog
        self.policy_id = digest(["service_oauth/v1", policy.issuer_url, policy.resource_url, policy.identity_issuer])

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
        if new_records:
            prior, value = self._read(store, LIMITS, self.policy_id)
            value = value or {"records": 0, "clients": 0}
            if any(type(value[key]) is not int or value[key] < 0 for key in ("records", "clients")):
                raise ServiceRuntimeError("oauth_record_invalid")
            count, clients = value["records"] + new_records, value["clients"] + new_clients
            if count > self.policy.max_records or clients > self.policy.max_clients:
                raise ServiceRuntimeError("oauth_storage_limit")
            counter = self._record(LIMITS, self.policy_id, {"records": count, "clients": clients})
            records.append(counter)
            guards.append(self.catalog.guard(prior, counter["record_id"]))
        return self.catalog.commit(store, records, guards)

    def _client(self, store, client_id):
        if not isinstance(client_id, str) or not CLIENT_PATTERN.fullmatch(client_id):
            return None, None
        row, value = self._read(store, CLIENT, client_id)
        if value is None or value["enabled"] is not True:
            return None, None
        client = OAuthClientInformationFull.model_validate(value["client"])
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
                    if held["client"] != data["client"] or held["enabled"] is not True:
                        raise RegistrationError("invalid_client_metadata", "client identity already exists")
                    return
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
                if held is None or str(params.redirect_uri) not in [str(uri) for uri in held.redirect_uris]:
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
            return OAuthAccessContext(principal, scopes, token["expires_at"], token["client_id"], token["subject"],
                                      token["resource"], token["grant_id"])

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
