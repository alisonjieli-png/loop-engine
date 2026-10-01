"""Bounded OAuth transport using the pinned MCP SDK and existing account identity.

The SDK implements its standard handlers. This adapter enforces the selected
public-PKCE profile, resource checks missing from the SDK token handler, and
safe errors. It never logs request bodies or forwards a browser credential.
"""
from __future__ import annotations

import json
import math
import threading
import time
from collections import OrderedDict
from urllib.parse import parse_qsl, urlencode, urlsplit

from mcp.server.auth.handlers.authorize import AuthorizationHandler
from mcp.server.auth.handlers.register import RegistrationHandler
from mcp.server.auth.handlers.revoke import RevocationHandler
from mcp.server.auth.handlers.token import TokenHandler
from mcp.server.auth.middleware.client_auth import ClientAuthenticator
from mcp.server.auth.provider import AuthorizeError, RegistrationError, TokenError
from mcp.server.auth.routes import build_metadata
from mcp.server.auth.settings import ClientRegistrationOptions, RevocationOptions
from pydantic import AnyHttpUrl
from starlette.datastructures import FormData
from starlette.requests import Request
from starlette.responses import JSONResponse

from .records import ServiceRuntimeError

METADATA_PATH = "/.well-known/oauth-authorization-server"
AUTHORIZE_PATH = "/authorize"
TOKEN_PATH = "/token"
REGISTER_PATH = "/register"
REVOKE_PATH = "/revoke"
CONSENT_PATH = "/oauth/consent"
CONSENT_API_PATH = "/api/v1/oauth/consent"
OAUTH_ROUTES = {METADATA_PATH:("GET",), AUTHORIZE_PATH:("GET", "POST"), TOKEN_PATH:("POST",),
                REGISTER_PATH:("POST",), REVOKE_PATH:("POST",)}
CREDENTIAL_ROUTES = (AUTHORIZE_PATH, TOKEN_PATH, REGISTER_PATH, REVOKE_PATH, CONSENT_API_PATH)
MAXIMUM_OAUTH_REQUEST_BYTES = 16_384
OAUTH_WINDOW_SECONDS = 60
OAUTH_REQUESTS_PER_WINDOW, OAUTH_ADDRESS_REQUESTS_PER_WINDOW = 120, 30
OAUTH_REGISTRATIONS_PER_WINDOW, OAUTH_TRACKED_ADDRESSES = 10, 4096
OAUTH_ERRORS = frozenset(("invalid_request", "invalid_client", "invalid_grant", "unauthorized_client", "invalid_scope",
    "invalid_target", "unsupported_grant_type", "unsupported_response_type", "access_denied", "server_error",
    "temporarily_unavailable", "invalid_client_metadata", "invalid_redirect_uri"))


def default_provider(runtime, browser_identity, configuration):
    """Install only beside an existing HTTPS account service with declared write authority.

    Derived from existing host facts; no host-file migration, identity account,
    credential or policy record is created during startup. Other hosts may
    explicitly inject a qualified provider through the application constructor.
    """
    from .oauth_authorization import OPENAI_CALLBACK_PREFIX, OAuthAuthorizationPolicy, OAuthAuthorizationProvider
    if (browser_identity is None or runtime.config.writes_authorized is not True
            or urlsplit(configuration.public_base_url).scheme != "https"
            or urlsplit(browser_identity.configuration.project_url).scheme != "https"):
        return None
    origin = configuration.public_base_url
    policy = OAuthAuthorizationPolicy(origin, origin + "/mcp", browser_identity.configuration.project_url + "/auth/v1",
        origin + CONSENT_PATH, redirect_uris=("https://chatgpt.com/connector_platform_oauth_redirect",),
        redirect_uri_prefixes=(OPENAI_CALLBACK_PREFIX,),
        native_loopback_paths=("/callback", "/oauth/callback", "/auth/callback", "/mcp/oauth/callback"))
    return OAuthAuthorizationProvider(runtime, policy)


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate field")
        result[key] = value
    return result


def _constant(_value):
    raise ValueError("nonfinite number")


def refusal(error="invalid_request", status=400):
    return JSONResponse({"error":error if error in OAUTH_ERRORS else "server_error"}, status_code=status,
                        headers={"Cache-Control":"no-store", "Pragma":"no-cache"})


def _request(request, body):
    scope = dict(request.scope)
    scope["headers"] = [(key,value) for key,value in scope["headers"] if key != b"content-length"] + [
        (b"content-length", str(len(body)).encode())]
    sent = False
    async def receive():
        nonlocal sent
        if sent:
            return {"type":"http.disconnect"}
        sent = True
        return {"type":"http.request", "body":body, "more_body":False}
    return Request(scope, receive)


class OAuthHttp:
    def __init__(self, provider):
        self.provider = provider
        self.registration = ClientRegistrationOptions(enabled=True,
            valid_scopes=list(provider.policy.allowed_scopes), default_scopes=list(provider.policy.allowed_scopes))
        client = ClientAuthenticator(provider)
        self.handlers = {AUTHORIZE_PATH:AuthorizationHandler(provider), TOKEN_PATH:TokenHandler(provider, client),
            REGISTER_PATH:RegistrationHandler(provider, self.registration), REVOKE_PATH:RevocationHandler(provider, client)}
        self._attempts, self._attempt_lock = OrderedDict(), threading.Lock()

    def permit(self, path, address="", *, now=None):
        """Bound successful as well as failed anonymous authorization work, in this process.

        The host's existing address-source policy supplies the address key.
        Without one, only the explicit global ceilings apply. Nothing is logged.
        """
        if path == METADATA_PATH:
            return 0
        moment = time.monotonic() if now is None else now
        selected = [("all", OAUTH_REQUESTS_PER_WINDOW)]
        if path == REGISTER_PATH:
            selected.append(("registrations", OAUTH_REGISTRATIONS_PER_WINDOW))
        if address:
            selected.append(("address:" + address, OAUTH_ADDRESS_REQUESTS_PER_WINDOW))
        with self._attempt_lock:
            for key in list(self._attempts):
                self._attempts[key] = [stamp for stamp in self._attempts[key] if stamp > moment - OAUTH_WINDOW_SECONDS]
                if not self._attempts[key]:
                    del self._attempts[key]
            for key, limit in selected:
                held = self._attempts.get(key, [])
                if len(held) >= limit:
                    return max(1, math.ceil(held[0] + OAUTH_WINDOW_SECONDS - moment))
            if len(self._attempts) + sum(key not in self._attempts for key, _ in selected) > OAUTH_TRACKED_ADDRESSES + 2:
                return OAUTH_WINDOW_SECONDS
            for key, _ in selected:
                self._attempts.setdefault(key, []).append(moment)
        return 0

    def metadata(self):
        record = build_metadata(AnyHttpUrl(self.provider.policy.issuer_url),
            AnyHttpUrl(self.provider.policy.issuer_url + "/docs/searching-and-retrieving"),
            self.registration, RevocationOptions(enabled=True)).model_dump(mode="json", exclude_none=True)
        # AnyHttpUrl adds a trailing slash to an origin. RFC 8414 discovery
        # must publish exactly the issuer named by protected-resource metadata.
        record["issuer"] = self.provider.policy.issuer_url
        # SDK supports public clients but omits this method from its default metadata.
        record["token_endpoint_auth_methods_supported"] = ["none"]
        record["revocation_endpoint_auth_methods_supported"] = ["none"]
        # No CIMD, ID token/UserInfo or issuer-response claim is advertised.
        return record

    async def handle(self, request, body=b""):
        path = request.url.path
        if request.method not in OAUTH_ROUTES.get(path, ()):
            return refusal(status=405)
        if path == METADATA_PATH:
            return JSONResponse(self.metadata())
        if len(body) > MAXIMUM_OAUTH_REQUEST_BYTES or len(request.scope.get("query_string", b"")) > MAXIMUM_OAUTH_REQUEST_BYTES:
            return refusal(status=413)
        try:
            if request.method == "POST":
                media = request.headers.get("content-type", "").split(";",1)[0].strip().lower()
                if path == REGISTER_PATH:
                    if media != "application/json":
                        return refusal(status=415)
                    value = json.loads(body.decode("utf-8"), object_pairs_hook=_unique, parse_constant=_constant)
                    if not isinstance(value, dict) or "client_secret" in value:
                        return refusal("invalid_client_metadata")
                    value.setdefault("token_endpoint_auth_method", "none")
                    if value["token_endpoint_auth_method"] != "none":
                        return refusal("invalid_client_metadata")
                    value.setdefault("client_name", "MCP client")
                    value.setdefault("grant_types", ["authorization_code", "refresh_token"])
                    value.setdefault("response_types", ["code"])
                    body = json.dumps(value, allow_nan=False).encode("utf-8")
                else:
                    if media != "application/x-www-form-urlencoded":
                        return refusal(status=415)
                    pairs = parse_qsl(body.decode("utf-8"), keep_blank_values=True, strict_parsing=True,
                                      encoding="utf-8", errors="strict", max_num_fields=16)
                    _unique(pairs)
                    if path in (TOKEN_PATH, REVOKE_PATH) and (request.headers.getlist("authorization")
                            or dict(pairs).get("client_secret", "")):
                        return refusal("invalid_client", 401)
                    if path == TOKEN_PATH:
                        self.provider.validate_token_request(FormData(pairs))
                    elif path == REVOKE_PATH and "client_secret" not in dict(pairs):
                        # SDK 2.2.0's public-client revocation model incorrectly requires the optional field.
                        # Empty means no secret, never a client credential or a changed authentication mode.
                        body = urlencode([*pairs, ("client_secret", "")]).encode("utf-8")
            elif path == AUTHORIZE_PATH:
                _unique(list(request.query_params.multi_items()))
            result = await self.handlers[path].handle(_request(request, body))
            if result.status_code >= 400:
                # SDK validation messages may contain submitted values. Return the stable error only.
                try:
                    error = json.loads(result.body).get("error", "server_error")
                except (ValueError, AttributeError):
                    error = "server_error"
                return refusal(error, result.status_code)
            return result
        except (TokenError, AuthorizeError, RegistrationError) as error:
            return refusal(error.error)
        except ServiceRuntimeError:
            # In particular, an uncertain commit is not an invalid request and must never be replayed here.
            raise
        except (ValueError, UnicodeError, RecursionError):
            return refusal()
