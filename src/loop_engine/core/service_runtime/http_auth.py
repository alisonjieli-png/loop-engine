"""Authentication adapters for the hosted intelligence request boundary.

Host-issued keys resolve through durable runtime records. External tokens are
verified against an explicit issuer, audience, algorithm set and key endpoint;
their subject is mapped by the runtime, never by a caller-supplied tenant claim.
This module issues no passwords, sessions or OAuth authorization codes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import ipaddress
import json
import math
import threading
import time
from urllib.parse import urlsplit

AUTHENTICATION_RECORD_TYPE = "service_http_authentication/v1"
HOST_KEY_AUTHENTICATION = "host_key"
EXTERNAL_JWT_AUTHENTICATION = "external_jwt"
BROWSER_IDENTITY_AUTHENTICATION = "browser_identity"
AUTHENTICATION_MODES = (HOST_KEY_AUTHENTICATION, EXTERNAL_JWT_AUTHENTICATION)


class HttpAuthenticationError(ValueError):
    """The request establishes no current authenticated service principal."""

    def __init__(self, code="unauthorized"):
        super().__init__(code)
        self.code = code


def is_loopback_url(value):
    parsed = urlsplit(value)
    if parsed.hostname == "localhost":
        return True
    try:
        return ipaddress.ip_address(parsed.hostname or "").is_loopback
    except ValueError:
        return False


def validate_public_url(value, *, permit_loopback=False):
    parsed = urlsplit(value)
    if (not parsed.hostname or parsed.username or parsed.password or parsed.fragment
            or parsed.query or parsed.scheme not in ("https", "http")
            or (parsed.scheme != "https" and not (permit_loopback and is_loopback_url(value)))):
        raise ValueError("service URLs require HTTPS or explicitly permitted loopback HTTP")
    return value.rstrip("/")


@dataclass(frozen=True)
class ServiceHttpAuthentication:
    """Versioned host authentication settings, not credentials or tenant grants."""

    modes: tuple[str, ...] = (HOST_KEY_AUTHENTICATION,)
    issuer: str = ""
    jwks_url: str = ""
    audience: str = ""
    algorithms: tuple[str, ...] = ("RS256",)
    required_scopes: tuple[str, ...] = ()
    key_cache_seconds: int = 60
    maximum_key_set_bytes: int = 262_144
    request_timeout_seconds: float = 5.0
    leeway_seconds: float = 0.0
    minimum_key_refresh_seconds: float = 10.0
    allow_loopback_issuer: bool = False
    record_type: str = AUTHENTICATION_RECORD_TYPE

    def __post_init__(self):
        if self.record_type != AUTHENTICATION_RECORD_TYPE:
            raise ValueError("unsupported HTTP authentication contract")
        modes = tuple(self.modes)
        if (not modes or len(set(modes)) != len(modes)
                or set(modes) - set(AUTHENTICATION_MODES)):
            raise ValueError("authentication requires explicit supported modes")
        if type(self.allow_loopback_issuer) is not bool:
            raise ValueError("loopback issuer allowance must be an explicit Boolean")
        algorithms = tuple(self.algorithms)
        if not algorithms or set(algorithms) - {"RS256", "ES256"}:
            raise ValueError("external authentication supports explicit asymmetric algorithms only")
        scopes = tuple(self.required_scopes)
        if any(not isinstance(scope, str) or not scope or any(character.isspace() for character in scope)
               for scope in scopes):
            raise ValueError("required token scopes must be exact nonempty names")
        if type(self.key_cache_seconds) is not int or not 1 <= self.key_cache_seconds <= 300:
            raise ValueError("key cache lifetime must be between one and 300 seconds")
        if type(self.maximum_key_set_bytes) is not int or not 1 <= self.maximum_key_set_bytes <= 2_000_000:
            raise ValueError("key-set response allowance must be explicit and bounded")
        for name, low, high in (("request_timeout_seconds", 0, 30), ("leeway_seconds", 0, 30)):
            number = getattr(self, name)
            if (type(number) not in (int, float) or not math.isfinite(number)
                    or number < low or number > high
                    or (name == "request_timeout_seconds" and number == 0)):
                raise ValueError("authentication timeout or clock allowance is invalid")
        pause = self.minimum_key_refresh_seconds
        if type(pause) not in (int, float) or not math.isfinite(pause) or not 1 <= pause <= 300:
            raise ValueError("the pause between key-set reads must be between one and 300 seconds")
        if EXTERNAL_JWT_AUTHENTICATION in modes:
            validate_public_url(self.issuer, permit_loopback=self.allow_loopback_issuer)
            validate_public_url(self.jwks_url, permit_loopback=self.allow_loopback_issuer)
            if not isinstance(self.audience, str) or not self.audience.strip():
                raise ValueError("external tokens require an exact configured audience")
        elif self.issuer or self.jwks_url or self.audience:
            raise ValueError("issuer settings require the external token authentication mode")
        object.__setattr__(self, "modes", modes)
        object.__setattr__(self, "algorithms", algorithms)
        object.__setattr__(self, "required_scopes", scopes)

    def to_dict(self):
        return {"record_type": self.record_type, "modes": list(self.modes),
                "issuer": self.issuer or None, "audience": self.audience or None,
                "algorithms": list(self.algorithms) if EXTERNAL_JWT_AUTHENTICATION in self.modes else [],
                "required_scopes": list(self.required_scopes),
                "key_cache_seconds": self.key_cache_seconds,
                "maximum_key_set_bytes": self.maximum_key_set_bytes,
                "issues_tokens": False, "external_provider_qualified": False}


@dataclass(frozen=True)
class AuthenticatedHttpRequest:
    """Ephemeral verified request identity; never serialize the credential."""

    principal: object = field(repr=False)
    credential: str = field(repr=False)
    mode: str
    expires_at: float | None = None
    token_scopes: tuple[str, ...] = ()
    #: The provider facts a browser session was admitted with, or None. Only
    #: the browser identity adapter sets it; a staff role is read from it.
    identity: object = field(default=None, repr=False, compare=False)

    @property
    def effective_scopes(self):
        held = set(self.principal.scopes)
        if self.mode in (EXTERNAL_JWT_AUTHENTICATION, BROWSER_IDENTITY_AUTHENTICATION):
            held.intersection_update(self.token_scopes)
        return tuple(sorted(held))


class ServiceHttpAuthenticator:
    """Resolve durable keys or verify an external token using PyJWT."""

    def __init__(self, runtime, configuration: ServiceHttpAuthentication, *, browser_identity=None):
        if not isinstance(configuration, ServiceHttpAuthentication):
            raise TypeError("typed HTTP authentication settings are required")
        self.runtime = runtime
        self.configuration = configuration
        if browser_identity is not None and (getattr(browser_identity, 'protocol_version', None) != 'browser_identity/v1'
                                             or getattr(browser_identity, 'runtime', None) is not runtime):
            raise TypeError('browser identity must bind the same runtime and supported protocol')
        self.browser_identity = browser_identity
        self._keys = None
        if EXTERNAL_JWT_AUTHENTICATION in configuration.modes:
            from jwt import PyJWKClient
            class BoundedJwkClient(PyJWKClient):
                # An unknown key identifier or a bad signature asks for a fresh
                # key set. Without a pause, any anonymous caller could make the
                # service contact the identity provider once per request and
                # hold a worker for the whole provider timeout.
                refresh_lock, last_attempt, last_value = threading.Lock(), None, None
                clock = staticmethod(time.monotonic)

                def fetch_data(self):
                    if not self.refresh_lock.acquire(blocking=False):
                        return self._known_keys()
                    try:
                        now = self.clock()
                        if (self.last_attempt is not None
                                and now - self.last_attempt < configuration.minimum_key_refresh_seconds):
                            return self._known_keys()
                        self.last_attempt = now
                        self.last_value = self._read_key_set()
                        return self.last_value
                    finally:
                        self.refresh_lock.release()

                def _known_keys(self):
                    if self.last_value is None:
                        raise HttpAuthenticationError("identity_key_set_unavailable")
                    return self.last_value

                def _read_key_set(self):
                    import httpx
                    chunks, size = [], 0
                    try:
                        with httpx.Client(timeout=configuration.request_timeout_seconds,
                                          follow_redirects=False, trust_env=False) as client:
                            with client.stream("GET", configuration.jwks_url) as response:
                                if 300 <= response.status_code < 400:
                                    raise HttpAuthenticationError()
                                response.raise_for_status()
                                for chunk in response.iter_bytes():
                                    size += len(chunk)
                                    if size > configuration.maximum_key_set_bytes:
                                        raise HttpAuthenticationError()
                                    chunks.append(chunk)
                    except httpx.HTTPError:
                        raise HttpAuthenticationError("identity_key_set_unavailable") from None
                    def unique(pairs):
                        value = {}
                        for key, item in pairs:
                            if key in value:
                                raise HttpAuthenticationError()
                            value[key] = item
                        return value
                    value = json.loads(b"".join(chunks), object_pairs_hook=unique)
                    if not isinstance(value, dict) or not isinstance(value.get("keys"), list):
                        raise HttpAuthenticationError()
                    if self.jwk_set_cache is not None:
                        self.jwk_set_cache.put(value)
                    return value
            self._keys = BoundedJwkClient(configuration.jwks_url, cache_keys=False,
                lifespan=configuration.key_cache_seconds, timeout=configuration.request_timeout_seconds)

    def _credential(self, authorization, purpose):
        if purpose not in ("service", "website"):
            raise HttpAuthenticationError()
        if (not isinstance(authorization, str) or len(authorization) > 16_384
                or not authorization.startswith("Bearer ") or authorization.count(" ") != 1):
            raise HttpAuthenticationError()
        credential = authorization[7:]
        if not credential or any(character.isspace() for character in credential):
            raise HttpAuthenticationError()
        return credential

    def consults_another_service(self, *, purpose="service"):
        """Whether resolving a credential this way needs a read at another service.

        A host-issued key is resolved from this service's own records. A
        browser session or an external token is confirmed by the identity
        provider, a machine this service does not control and cannot hurry.
        The caller uses this answer to decide which part of its own capacity
        the work may take, before it commits any.
        """
        return ((purpose == "website" and self.browser_identity is not None)
                or EXTERNAL_JWT_AUTHENTICATION in self.configuration.modes)

    def host_key(self, authorization, *, purpose="service"):
        """Resolve a host-issued key from local records, or return None.

        Returning None means only that this credential is not a host key. It
        is not a refusal, because another mode may still confirm it. This
        call reaches no other service, so its cost is this machine's alone.
        """
        credential = self._credential(authorization, purpose)
        if HOST_KEY_AUTHENTICATION not in self.configuration.modes:
            return None
        try:
            principal = self.runtime.authenticate_key(credential)
        except Exception:
            principal = None
        if principal is None:
            return None
        return AuthenticatedHttpRequest(principal, credential, HOST_KEY_AUTHENTICATION)

    def remote_credential(self, authorization, *, purpose="service"):
        """Confirm a credential that only another service can confirm."""
        credential = self._credential(authorization, purpose)
        if purpose == "website" and self.browser_identity is not None:
            return self.browser_identity.authenticate(credential)
        if EXTERNAL_JWT_AUTHENTICATION not in self.configuration.modes:
            raise HttpAuthenticationError()
        return self._external_token(credential)

    def authenticate(self, authorization, *, purpose="service"):
        held = self.host_key(authorization, purpose=purpose)
        return held if held is not None else self.remote_credential(authorization, purpose=purpose)

    def verified_external_claims(self, credential):
        """Verify the configured token profile before any durable subject lookup.

        Used by an explicitly installed account adapter for first registration.
        This does not create a principal, account, scope grant or subscription.
        """
        import jwt
        config = self.configuration
        try:
            header = jwt.get_unverified_header(credential)
            if (header.get("alg") not in config.algorithms or header.get("crit")
                    or not isinstance(header.get("kid"), str) or not 0 < len(header["kid"]) <= 128):
                raise HttpAuthenticationError()
            key = self._keys.get_signing_key_from_jwt(credential)
            options = {"require": ["iss", "aud", "sub", "exp"], "verify_signature": True}
            try:
                claims = jwt.decode(credential, key.key, algorithms=list(config.algorithms),
                    issuer=config.issuer, audience=config.audience, leeway=config.leeway_seconds, options=options)
            except jwt.InvalidSignatureError:
                # A provider may rotate a key while retaining its identifier.
                # Refresh only from the configured endpoint, never a token URL.
                keys = self._keys.get_signing_keys(refresh=True)
                key = next(item for item in keys if item.key_id == header["kid"])
                claims = jwt.decode(credential, key.key, algorithms=list(config.algorithms),
                    issuer=config.issuer, audience=config.audience, leeway=config.leeway_seconds, options=options)
            if (not isinstance(claims["sub"], str) or not claims["sub"].strip()
                    or type(claims["exp"]) not in (int, float)
                    or not math.isfinite(claims["exp"])):
                raise HttpAuthenticationError()
            scope = claims.get("scope", "")
            if not isinstance(scope, str) or not set(config.required_scopes) <= set(scope.split()):
                raise HttpAuthenticationError("insufficient_scope")
            return claims
        except HttpAuthenticationError:
            raise
        except Exception:
            raise HttpAuthenticationError() from None

    def _external_token(self, credential):
        claims = self.verified_external_claims(credential)
        try:
            principal = self.runtime.authenticate_subject(self.configuration.issuer, claims["sub"])
        except Exception:
            raise HttpAuthenticationError() from None
        return AuthenticatedHttpRequest(principal, credential, EXTERNAL_JWT_AUTHENTICATION,
                                        float(claims["exp"]), tuple(claims.get("scope", "").split()))

    def revalidate(self, request: AuthenticatedHttpRequest):
        if request.expires_at is not None and request.expires_at <= time.time():
            raise HttpAuthenticationError()
        fresh = self.authenticate("Bearer " + request.credential,
                                  purpose="website" if request.mode == BROWSER_IDENTITY_AUTHENTICATION else "service")
        if fresh.principal.tenant_id != request.principal.tenant_id or fresh.mode != request.mode:
            raise HttpAuthenticationError()
        return fresh

    @staticmethod
    def credential_digest(request):
        return hashlib.sha256(request.credential.encode("utf-8")).hexdigest()
