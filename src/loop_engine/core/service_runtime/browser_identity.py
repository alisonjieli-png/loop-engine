"""Host-installed browser identity adapter over an existing identity provider.

Supabase owns passwords, email verification and session issuance. This adapter
verifies the exact browser-token audience and current provider user before
mapping the subject through the existing catalogue. Browser tokens are not
accepted by the Model Context Protocol resource-audience verifier.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import math
from urllib.parse import urlsplit

from .http_auth import (AuthenticatedHttpRequest, BROWSER_IDENTITY_AUTHENTICATION,
                        EXTERNAL_JWT_AUTHENTICATION, HttpAuthenticationError,
                        ServiceHttpAuthentication, ServiceHttpAuthenticator, validate_public_url)
from .records import (ACCESS_MANAGE_SCOPE, DEFAULT_SCOPES, SubjectTenantRegistration,
                      ServiceRuntimeError, identifier, scopes, text)


CONFIGURATION_RECORD_TYPE = "browser_identity_configuration/v1"
PROVIDER_PROFILE = "supabase_user/v1"


@dataclass(frozen=True)
class BrowserIdentityConfiguration:
    """Explicit provider and admission policy, not a user-controlled token profile."""

    project_url: str
    publishable_key_ref: str
    namespace_prefix: str
    allowed_scopes: tuple[str, ...] = DEFAULT_SCOPES
    registration_enabled: bool = False
    email_signup_enabled: bool = False
    allow_network: bool = False
    allow_loopback: bool = False
    timeout_seconds: float = 5.0
    maximum_response_bytes: int = 65_536
    record_type: str = CONFIGURATION_RECORD_TYPE
    provider_profile: str = PROVIDER_PROFILE

    def __post_init__(self):
        if self.record_type != CONFIGURATION_RECORD_TYPE or self.provider_profile != PROVIDER_PROFILE:
            raise ServiceRuntimeError("unsupported_browser_identity_profile")
        for name in ("registration_enabled", "email_signup_enabled", "allow_network", "allow_loopback"):
            if type(getattr(self, name)) is not bool:
                raise ServiceRuntimeError("invalid_browser_identity_configuration")
        origin = validate_public_url(self.project_url, permit_loopback=self.allow_loopback)
        if urlsplit(origin).path:
            raise ServiceRuntimeError("identity_project_origin_required")
        text(self.publishable_key_ref, "publishable key reference")
        identifier(self.namespace_prefix, "customer namespace prefix")
        if len(self.namespace_prefix) > 32:
            raise ServiceRuntimeError("invalid_customer_namespace_prefix")
        if self.email_signup_enabled and not self.registration_enabled:
            raise ServiceRuntimeError("email_signup_requires_account_admission")
        selected = scopes(self.allowed_scopes)
        if ACCESS_MANAGE_SCOPE in selected:
            raise ServiceRuntimeError("automatic_administration_forbidden")
        if (type(self.timeout_seconds) not in (int, float) or not math.isfinite(self.timeout_seconds)
                or not 0 < self.timeout_seconds <= 15 or type(self.maximum_response_bytes) is not int
                or not 1 <= self.maximum_response_bytes <= 262_144):
            raise ServiceRuntimeError("invalid_identity_request_limits")
        object.__setattr__(self, "project_url", origin)
        object.__setattr__(self, "allowed_scopes", selected)


@dataclass(frozen=True)
class IdentityUserRequest:
    """One bounded read at the configured identity origin; credentials stay private."""

    url: str
    timeout_seconds: float
    maximum_response_bytes: int
    access_token: str = field(repr=False)
    publishable_key: str = field(repr=False)


def expired_by_now(claims, now):
    """Whether a verified token's expiry has passed at `now`, the service runtime clock.

    The signature check reads the expiry before the provider call and the
    revocation read. A revocation is removed once its session has expired, so
    the expiry is read again after the revocation: a session whose revocation
    was removed while its request was being checked is past its expiry by then.
    """
    return claims["exp"] <= now


def revocation_expiry(expires_at):
    """The whole second a sign-out revocation is kept until: the token expiry, rounded up."""
    return math.ceil(expires_at)


def read_identity_user(request: IdentityUserRequest):
    import httpx
    import json
    try:
        with httpx.Client(follow_redirects=False, trust_env=False, timeout=request.timeout_seconds) as client:
            with client.stream("GET", request.url, headers={"Authorization": "Bearer " + request.access_token,
                    "apikey": request.publishable_key, "Accept": "application/json"}) as response:
                if response.status_code != 200:
                    raise HttpAuthenticationError("identity_user_unavailable" if response.status_code in (401, 403)
                                                  else "identity_provider_unavailable")
                chunks, size = [], 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > request.maximum_response_bytes:
                        raise HttpAuthenticationError("identity_response_too_large")
                    chunks.append(chunk)
        def unique(pairs):
            value = {}
            for key, item in pairs:
                if key in value:
                    raise HttpAuthenticationError("ambiguous_identity_response")
                value[key] = item
            return value
        return json.loads(b"".join(chunks), object_pairs_hook=unique)
    except HttpAuthenticationError:
        raise
    except Exception:
        raise HttpAuthenticationError("identity_provider_unavailable") from None


class BrowserIdentityAdapter:
    """Identity-provider implementation behind the browser_identity/v1 boundary."""

    protocol_version = "browser_identity/v1"

    def __init__(self, runtime, configuration: BrowserIdentityConfiguration, secret_resolver, *,
                 starter_bindings=(), transport=None):
        if not isinstance(configuration, BrowserIdentityConfiguration) or not callable(secret_resolver):
            raise TypeError("typed browser identity configuration and a host secret resolver are required")
        self.runtime, self.configuration = runtime, configuration
        self._secrets = secret_resolver
        self._transport = transport or read_identity_user
        self._starter_bindings = tuple(starter_bindings)
        self._verifier = ServiceHttpAuthenticator(runtime, ServiceHttpAuthentication(
            modes=(EXTERNAL_JWT_AUTHENTICATION,), issuer=configuration.project_url + "/auth/v1",
            jwks_url=configuration.project_url + "/auth/v1/.well-known/jwks.json", audience="authenticated",
            algorithms=("RS256", "ES256"), allow_loopback_issuer=configuration.allow_loopback))

    def _publishable_key(self):
        try:
            key = self._secrets(self.configuration.publishable_key_ref)
        except Exception:
            raise ServiceRuntimeError("identity_public_configuration_unavailable") from None
        if not isinstance(key, str) or not key.startswith("sb_publishable_") or any(character.isspace() for character in key):
            raise ServiceRuntimeError("publishable_key_required_not_server_secret")
        return key

    def public_configuration(self):
        return {"record_type": "browser_identity_public_configuration/v1",
                "provider_profile": self.configuration.provider_profile,
                "project_url": self.configuration.project_url, "publishable_key": self._publishable_key(),
                "registration_enabled": self.configuration.registration_enabled,
                "email_signup_enabled": self.configuration.email_signup_enabled,
                "passwords_owned_by": "configured_identity_provider", "session_persistence": "page_memory",
                "model_keys_requested": False}

    def _identity(self, credential):
        if not self.configuration.allow_network:
            raise HttpAuthenticationError("identity_network_authority_required")
        if (not isinstance(credential, str) or not 1 <= len(credential) <= 16_384
                or any(character.isspace() for character in credential)):
            raise HttpAuthenticationError()
        claims = self._verifier.verified_external_claims(credential)
        if claims.get("role") != "authenticated" or claims.get("is_anonymous") is not False:
            raise HttpAuthenticationError("verified_customer_identity_required")
        result = self._transport(IdentityUserRequest(self.configuration.project_url + "/auth/v1/user",
            self.configuration.timeout_seconds, self.configuration.maximum_response_bytes,
            credential, self._publishable_key()))
        if (not isinstance(result, dict) or result.get("id") != claims["sub"]
                or result.get("is_anonymous") is not False or result.get("role") != "authenticated"):
            raise HttpAuthenticationError("identity_subject_mismatch")
        # user_metadata.email_verified is user-editable and never consulted.
        confirmed = result.get("email_confirmed_at")
        try:
            stamp = datetime.fromisoformat(confirmed.replace("Z", "+00:00"))
            valid = stamp.tzinfo is not None and stamp <= datetime.now(timezone.utc)
        except (ValueError, TypeError, AttributeError):
            valid = False
        if not valid:
            raise HttpAuthenticationError("verified_email_required")
        if self.runtime.browser_session_revoked(hashlib.sha256(credential.encode()).hexdigest()):
            raise HttpAuthenticationError("browser_session_revoked")
        if expired_by_now(claims, self.runtime._now()):
            raise HttpAuthenticationError()
        return claims

    def activate(self, credential):
        if self.configuration.registration_enabled is not True:
            raise ServiceRuntimeError("account_registration_unavailable")
        claims = self._identity(credential)
        return self.runtime.ensure_subject_tenant(SubjectTenantRegistration(
            self._verifier.configuration.issuer, claims["sub"], self.configuration.namespace_prefix,
            self.configuration.allowed_scopes, self._starter_bindings))

    def authenticate(self, credential):
        claims = self._identity(credential)
        try:
            principal = self.runtime.authenticate_subject(self._verifier.configuration.issuer, claims["sub"])
        except Exception:
            raise HttpAuthenticationError("account_unavailable") from None
        return AuthenticatedHttpRequest(principal, credential, BROWSER_IDENTITY_AUTHENTICATION,
                                        float(claims["exp"]), self.configuration.allowed_scopes)

    def logout(self, request):
        """Refuse this browser session until the last moment its token could still be accepted.

        The revocation keeps the token expiry rounded up to a whole second, so
        a token whose expiry falls inside a second is refused until the end of
        that second, and the revocation is never removed before the token dies.
        """
        current = self.authenticate(request.credential)
        return self.runtime.revoke_browser_session(current.principal,
            hashlib.sha256(request.credential.encode()).hexdigest(), revocation_expiry(current.expires_at))
