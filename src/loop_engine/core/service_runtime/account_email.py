"""Public sign-up and password recovery email for the hosted service.

Kind: internal service mechanics behind the `account_email/v1` boundary. It is
an adapter used by the HTTP transport, not a graph vertex and not a runtime
type. The identity provider owns users, passwords and one-time tokens. This
adapter asks that provider's administration interface to generate a
confirmation or a recovery link without sending any message, then sends the
service's own message through the configured mail provider. The message
carries a link to a page of this service, never the link that the identity
provider generated for itself.

Sign-up is email first. A sign-up request carries the address and nothing
else; a request that carries a password is refused. The provider's interface
needs a password to create a user, so this adapter generates a new random one
for every request, sends it in that one request and keeps it nowhere. Nobody
learns it. The person chooses their own password on the page the link opens,
before that page opens the account. On September 23, 2026 a probe of the
identity project showed that a second sign-up link for an address that has
not been confirmed keeps the first password, so a caller who could choose the
password could register an address first and keep a password its owner would
later confirm. The record is
`artifacts/architecture-audit-2026-09-19/identity-unconfirmed-signup-probe-1.json`.

Surface: `AccountEmailConfiguration` (the typed host block), `AccountEmailAdapter`
with `prepare`, `deliver` and `availability`, the two wire records
`IdentityLinkRequest` and `AccountMailRequest`, their default transports
`generate_identity_link` and `send_account_mail`, `generated_signup_password`,
and `ProviderAnswer`, which is what a transport returns. Both operations stay
closed until the host sets their Boolean and grants network authority.

The answer to a caller never says whether an address already has an account.
That holds for every definite answer the identity provider can give, not only
for the two this release expects, because a refusal that could be about the
address takes the same path as the expected one. The link, the token hash, the
generated password and every provider key stay out of records, messages,
reports and exception text. An open operation also needs a stated client
address source, so that one caller cannot send messages to addresses it
chooses without limit.
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields as dataclass_fields
import hashlib
import json
import math
import re
import secrets
import string
import time
from urllib.parse import quote, urlsplit

from .http import ServiceHttpError
from .http_auth import validate_public_url
from .records import ServiceRuntimeError, text
from .request_limits import (
    LIMIT_REACHED_CODE, REFUSAL_RECORD_TYPE, SOCKET_PEER_SOURCE, FailedAttemptLimiter, ServiceRequestLimits,
)

CONFIGURATION_RECORD_TYPE = "service_account_email_configuration/v1"
#: Version 2 carries the address alone. Version 1 carried a password chosen by
#: the caller and is refused: the website is the only caller, and before launch
#: no other caller has to be kept working.
SIGNUP_REQUEST_VERSION = "service_account_signup_request/v2"
SIGNUP_RESULT_VERSION = "service_account_signup_result/v1"
RECOVERY_REQUEST_VERSION = "service_account_recovery_request/v1"
RECOVERY_RESULT_VERSION = "service_account_recovery_result/v1"
#: The provider pair this release speaks to: the identity provider's
#: administration interface that generates a link without sending a message,
#: and the mail provider's send interface. A host that names another pair is
#: refused, because the field names below belong to these two interfaces.
PROVIDER_PROFILE = "supabase_generate_link_and_resend_send/v1"
SIGNUP_ACTION, RECOVERY_ACTION = "signup", "recovery"
ACTIONS = (SIGNUP_ACTION, RECOVERY_ACTION)
CONFIRMATION_SENT, RECOVERY_SENT = "confirmation_sent", "recovery_sent"
SIGNUP_PATH, RECOVERY_PATH = "/api/v1/account/signup", "/api/v1/account/recovery"
ACCOUNT_PATHS = (SIGNUP_PATH, RECOVERY_PATH)
#: The page of this service that the message links to. The website exchanges
#: the token hash there through the identity library and then activates.
CONFIRM_PAGE = "/auth/confirm"
GENERATE_LINK_PATH = "/auth/v1/admin/generate_link"
MAIL_SEND_PATH = "/emails"
ENVIRONMENT_REFERENCE = re.compile(r"env:[A-Za-z0-9_./:-]+")
#: The statuses at the identity provider's administration interface that are
#: about this service rather than about the address in the request: the server
#: key was refused, this service may not use the interface, or this service is
#: over the provider's own rate. They answer the same way for every address, so
#: turning them into a refusal tells a caller nothing about who is registered.
#: Every other definite refusal could be about the address, so it never reaches
#: the caller. This release reads no field of a refusal body. Nothing in this
#: repository establishes which field name this endpoint uses for its machine
#: readable code, and reading the wrong one would answer 503 for an address
#: that has an account and 202 for one that does not.
SERVICE_REFUSAL_STATUSES = (401, 403, 429)
#: The identity provider's server secret key. Requiring the exact prefix stops
#: a deployment that pastes the browser publishable key into the server slot.
IDENTITY_SECRET_PREFIX = "sb_secret_"
#: The mail provider's key prefix, for the same reason.
MAIL_SECRET_PREFIX = "re_"
#: A token hash travels in a query value. Only these characters are accepted,
#: so a value that would change the meaning of the link is refused instead of
#: being encoded and sent. The value is also percent encoded when the link is
#: built.
TOKEN_HASH = re.compile(r"[A-Za-z0-9_-]{1,256}")
LONGEST_EMAIL_ADDRESS, LONGEST_LOCAL_PART, LONGEST_DOMAIN = 254, 64, 253
DOMAIN_CHARACTERS = frozenset(string.ascii_letters + string.digits + "-")
LOCAL_CHARACTERS = frozenset(string.ascii_letters + string.digits + "!#$%&'*+/=?^_`{|}~.-")
#: The fields of a request each operation reads, and no others. Sign-up takes
#: no password: a caller who could choose one could register an address before
#: its owner does and keep a password the owner would later confirm.
REQUEST_FIELDS = {SIGNUP_ACTION: frozenset({"record_type", "email"}),
                  RECOVERY_ACTION: frozenset({"record_type", "email"})}
#: No password is longer than this, so that a password cannot be silently
#: shortened later by a hash function with a block limit. The identity
#: provider's own ceiling is the same number.
MAXIMUM_PASSWORD_BYTES = 72
SHORTEST_ALLOWED_MINIMUM_PASSWORD = 8
#: 51 random bytes encode to 68 ASCII characters, then four required character
#: groups bring the temporary secret to 72 bytes. This covers every host minimum
#: the configuration accepts without exceeding its maximum password byte count.
GENERATED_PASSWORD_BYTES = 51
#: One character from each group is added to the random part, so that the
#: password meets any character rule the identity project may set. A password
#: its policy refused would be answered like an ineligible address, and the
#: person would receive the notice message instead of a link.
GENERATED_PASSWORD_GROUPS = (string.ascii_lowercase, string.ascii_uppercase, string.digits, "-_")
SENDER_NAME_CHARACTERS = frozenset(string.ascii_letters + string.digits + " .-")


def _accepted(status_code):
    """True when a provider answered that it carried the request out."""
    return 200 <= status_code < 300


class AccountEmailError(ServiceHttpError):
    """A caller-safe refusal of one account email operation.

    It carries a stable code, a status, and for a request over its limit the
    typed refusal record and a `Retry-After` header. It never carries the
    address, the password, the link, the token hash, a provider key or any
    provider message.
    """


def _environment_reference(value, label):
    """Refuse anything but an exact environment reference for a provider secret."""
    if not isinstance(value, str) or ENVIRONMENT_REFERENCE.fullmatch(value) is None:
        raise ServiceRuntimeError("invalid_account_email_secret_reference",
                                  f"{label} must be an environment reference written as env:NAME")
    return value


def email_address(value):
    """Return the exact address this service will use, or refuse the value.

    The address is compared and sent in lower case, so that one address cannot
    be written in several ways to obtain several accounts or several
    allowances. Only printable ASCII is accepted: an address written with the
    letters of another script can look the same as one written with Latin
    letters, and this service has no way to tell the owners apart.
    """
    if not isinstance(value, str):
        raise AccountEmailError("invalid_email_address", 400)
    # Only the spaces a form adds around an address are removed. A line break
    # or a tab is refused rather than quietly dropped.
    address = value.strip(" ")
    if (not 3 <= len(address) <= LONGEST_EMAIL_ADDRESS or address.count("@") != 1
            or not address.isascii() or not address.isprintable()
            or any(character.isspace() for character in address)):
        raise AccountEmailError("invalid_email_address", 400)
    local, domain = address.split("@")
    labels = domain.split(".")
    if (not 1 <= len(local) <= LONGEST_LOCAL_PART or not 1 <= len(domain) <= LONGEST_DOMAIN or len(labels) < 2
            or local.startswith(".") or local.endswith(".") or ".." in local
            or any(character not in LOCAL_CHARACTERS for character in local)
            or any(not label or label.startswith("-") or label.endswith("-")
                   or any(character not in DOMAIN_CHARACTERS for character in label) for label in labels)):
        raise AccountEmailError("invalid_email_address", 400)
    return address.lower()


def generated_signup_password():
    """Return a new password that nobody chose and nobody will learn.

    The identity provider's interface needs a password to create a user. This
    one is made for one request and kept nowhere: not in a record, a message,
    an answer or a log. The person who owns the address chooses their own
    password on the page the link opens, before that page opens the account.
    Its 51 random bytes are written in the address-safe alphabet; one
    character from each group follows them. The resulting 72 ASCII bytes
    cover every minimum admitted by this configuration and its byte ceiling.
    """
    return (secrets.token_urlsafe(GENERATED_PASSWORD_BYTES)
            + "".join(secrets.choice(group) for group in GENERATED_PASSWORD_GROUPS))


def counted_email_key(address):
    """Name the counted email address without keeping the address itself.

    The table of attempts holds this digest, so a memory dump or a report of
    the table shows no address.
    """
    return hashlib.sha256(address.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AccountEmailConfiguration:
    """Host settings for public sign-up and password recovery email.

    Both operations are closed until the host sets their Boolean and grants
    network authority. The sender address, the identity origin and the mail
    origin are fixed here. No request can choose any of them, and this release
    carries no default origin for either provider: a host that wants this
    service to send a message names both, so that the deployment file shows
    every address this service can reach.
    """

    identity_origin: str
    identity_service_key_ref: str = field(repr=False)
    mail_origin: str
    mail_api_key_ref: str = field(repr=False)
    sender_address: str
    sender_name: str = ""
    signup_enabled: bool = False
    recovery_enabled: bool = False
    allow_network: bool = False
    allow_loopback: bool = False
    minimum_password_length: int = 12
    attempts_for_each_address: int = 10
    attempts_for_each_email: int = 3
    attempt_window_seconds: float = 3600.0
    tracked_addresses: int = 4096
    tracked_emails: int = 4096
    timeout_seconds: float = 10.0
    maximum_response_bytes: int = 65_536
    record_type: str = CONFIGURATION_RECORD_TYPE
    provider_profile: str = PROVIDER_PROFILE

    def __post_init__(self):
        if self.record_type != CONFIGURATION_RECORD_TYPE or self.provider_profile != PROVIDER_PROFILE:
            raise ServiceRuntimeError("unsupported_account_email_configuration",
                f"this release reads {CONFIGURATION_RECORD_TYPE} with the provider pair {PROVIDER_PROFILE}")
        for name in ("signup_enabled", "recovery_enabled", "allow_network", "allow_loopback"):
            if type(getattr(self, name)) is not bool:
                raise ServiceRuntimeError("invalid_account_email_authority",
                                          "sign-up, recovery, network and loopback authority are explicit Booleans")
        for name in ("identity_origin", "mail_origin"):
            origin = validate_public_url(getattr(self, name), permit_loopback=self.allow_loopback)
            if urlsplit(origin).path:
                raise ServiceRuntimeError("account_email_origin_required", f"{name} must be an origin without a path")
            object.__setattr__(self, name, origin)
        _environment_reference(self.identity_service_key_ref, "the identity provider server key reference")
        _environment_reference(self.mail_api_key_ref, "the mail provider key reference")
        object.__setattr__(self, "sender_address", email_address(self.sender_address))
        if (not isinstance(self.sender_name, str) or len(self.sender_name) > 64
                or any(character not in SENDER_NAME_CHARACTERS for character in self.sender_name)
                or self.sender_name != self.sender_name.strip()):
            raise ServiceRuntimeError("invalid_account_email_sender_name",
                "the sender name is short plain text; it never carries an address, a comma or a quotation mark")
        if (type(self.minimum_password_length) is not int
                or not SHORTEST_ALLOWED_MINIMUM_PASSWORD <= self.minimum_password_length <= MAXIMUM_PASSWORD_BYTES):
            raise ServiceRuntimeError("invalid_account_email_password_policy",
                f"the minimum password length is a whole number from {SHORTEST_ALLOWED_MINIMUM_PASSWORD} "
                f"to {MAXIMUM_PASSWORD_BYTES}")
        if (type(self.timeout_seconds) not in (int, float) or not math.isfinite(self.timeout_seconds)
                or not 0 < self.timeout_seconds <= 30 or type(self.maximum_response_bytes) is not int
                or not 1 <= self.maximum_response_bytes <= 262_144):
            raise ServiceRuntimeError("invalid_account_email_request_limits",
                                      "the provider deadline and the response allowance are bounded")
        # Building both records here refuses an impossible allowance while the
        # host file is read, before the service serves anything.
        self.email_attempt_limits()
        self.address_attempt_limits(ServiceRequestLimits())

    @classmethod
    def from_host(cls, value):
        """Accept the exact versioned mapping from a host file, and nothing else."""
        names = {item.name for item in dataclass_fields(cls)}
        if (not isinstance(value, dict) or set(value) - names
                or value.get("record_type") != CONFIGURATION_RECORD_TYPE):
            raise ServiceRuntimeError("unsupported_account_email_configuration",
                "an account email block names its record version and only the fields of that version")
        return cls(**value)

    def address_attempt_limits(self, stated):
        """Settings for the table that counts attempts from one client address.

        The table follows the address source that the host stated for the
        service. With no stated source every caller behind a proxy shares one
        key, so counting would refuse everyone at once; the table then stays
        inactive, exactly as the sign-in limit does.
        """
        return ServiceRequestLimits(client_address_source=stated.client_address_source,
            client_address_header=stated.client_address_header, ipv6_prefix_bits=stated.ipv6_prefix_bits,
            failures_allowed=self.attempts_for_each_address, window_seconds=self.attempt_window_seconds,
            maximum_tracked_addresses=self.tracked_addresses)

    def email_attempt_limits(self):
        """Settings for the table that counts attempts for one email address.

        An email address has none of the ambiguity of a client address, so this
        table is always active. Its key is the digest from `counted_email_key`,
        never a client address, and `address_key` is never called on it. The
        settings record names the socket peer only because that is how the
        shared limiter is switched on.
        """
        return ServiceRequestLimits(client_address_source=SOCKET_PEER_SOURCE,
            failures_allowed=self.attempts_for_each_email, window_seconds=self.attempt_window_seconds,
            maximum_tracked_addresses=self.tracked_emails)


@dataclass(frozen=True)
class ProviderAnswer:
    """What one provider request returned: its status and its parsed body."""

    status_code: int
    payload: dict

    def __post_init__(self):
        if type(self.status_code) is not int or not 100 <= self.status_code <= 599 or not isinstance(self.payload, dict):
            raise ServiceRuntimeError("invalid_provider_answer", "a provider answer is one status and one JSON object")


@dataclass(frozen=True)
class IdentityLinkRequest:
    """One bounded request to the identity provider's administration interface.

    A sign-up request carries the password from `generated_signup_password`;
    a recovery request carries none. The address and the password are kept
    out of the printed form, so that a log line, a traceback or a report of
    this record shows neither.
    """

    url: str
    action: str
    email: str = field(repr=False)
    password: str = field(repr=False)
    timeout_seconds: float
    maximum_response_bytes: int

    def __post_init__(self):
        if self.action not in ACTIONS or not self.url.endswith(GENERATE_LINK_PATH) or "?" in self.url or "#" in self.url:
            raise ServiceRuntimeError("unsupported_identity_link_request")
        if bool(self.password) != (self.action == SIGNUP_ACTION):
            raise ServiceRuntimeError("unsupported_identity_link_request",
                                      "a password belongs to sign-up only and sign-up always carries one")
        _bounded_request(self.timeout_seconds, self.maximum_response_bytes)


@dataclass(frozen=True)
class AccountMailRequest:
    """One bounded send through the mail provider. The body carries the link."""

    url: str
    sender: str
    recipient: str = field(repr=False)
    subject: str
    text_body: str = field(repr=False)
    timeout_seconds: float
    maximum_response_bytes: int

    def __post_init__(self):
        if not self.url.endswith(MAIL_SEND_PATH) or "?" in self.url or "#" in self.url:
            raise ServiceRuntimeError("unsupported_account_mail_request")
        for value, label in ((self.sender, "sender"), (self.recipient, "recipient"), (self.subject, "subject")):
            text(value, "the account message " + label)
        if (not isinstance(self.text_body, str) or not self.text_body.strip() or len(self.text_body) > 8192
                or any(ord(character) < 32 and character != "\n" for character in self.text_body)):
            raise ServiceRuntimeError("invalid_account_message",
                                      "the message is bounded text whose only control character is a line break")
        _bounded_request(self.timeout_seconds, self.maximum_response_bytes)


def _bounded_request(timeout_seconds, maximum_response_bytes):
    if (type(timeout_seconds) not in (int, float) or not math.isfinite(timeout_seconds) or timeout_seconds <= 0
            or type(maximum_response_bytes) is not int or maximum_response_bytes < 1):
        raise ServiceRuntimeError("invalid_account_email_request_limits")


def names_the_same_address(payload, address):
    """True when a provider answer is about the address that was asked for."""
    named = payload.get("email")
    return isinstance(named, str) and named.strip().lower() == address


def names_the_same_action(payload, action):
    """True when a provider answer is about the action that was asked for."""
    return payload.get("verification_type") == action


def may_open_without_a_stated_address_source(configuration, stated):
    """True when nothing is open, or the host stated where a client address comes from."""
    return stated.active or not (configuration.signup_enabled or configuration.recovery_enabled)


def _unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate provider field")
        value[key] = item
    return value


def within_the_deadline(deadline):
    """True while this service may still read the body of one provider answer."""
    return time.monotonic() <= deadline


def _answer(response, limit, unavailable, deadline):
    """Read one bounded provider answer, refusing a redirect, an oversized body and a slow one.

    `deadline` is the moment from `time.monotonic` after which this service
    stops reading. The client's own deadline applies to each read separately,
    so a provider that sends a few bytes before every read would hold this
    worker thread for as long as it kept sending. This total bound ends the
    body read instead, and the outcome stays unknown.
    """
    if 300 <= response.status_code < 400:
        raise AccountEmailError(unavailable, 503)
    chunks, size = [], 0
    for chunk in response.iter_bytes():
        size += len(chunk)
        if size > limit or not within_the_deadline(deadline):
            raise AccountEmailError(unavailable, 503)
        chunks.append(chunk)
    try:
        value = json.loads(b"".join(chunks) or b"{}", object_pairs_hook=_unique)
    except (ValueError, UnicodeError):
        raise AccountEmailError(unavailable, 503) from None
    if not isinstance(value, dict):
        raise AccountEmailError(unavailable, 503)
    return ProviderAnswer(response.status_code, value)


def _request(method, url, headers, body, request, unavailable):
    """Send exactly one request. Nothing here retries, and no proxy is inherited."""
    import httpx
    deadline = time.monotonic() + request.timeout_seconds
    try:
        with httpx.Client(timeout=request.timeout_seconds, follow_redirects=False, trust_env=False) as client:
            with client.stream(method, url, headers=headers, content=body) as response:
                if str(response.url) != url:
                    raise AccountEmailError(unavailable, 503)
                return _answer(response, request.maximum_response_bytes, unavailable, deadline)
    except AccountEmailError:
        raise
    except Exception:
        raise AccountEmailError(unavailable, 503) from None


def generate_identity_link(request: IdentityLinkRequest, secret: str):
    """Ask the identity provider for a link without letting it send a message."""
    if not isinstance(request, IdentityLinkRequest):
        raise ServiceRuntimeError("unsupported_identity_link_request")
    body = {"type": request.action, "email": request.email}
    if request.action == SIGNUP_ACTION:
        body["password"] = request.password
    # No `redirect_to` is sent. Engineering cannot change the provider's list
    # of permitted redirect addresses, and this journey never uses the
    # provider's own redirect: the message links to a page of this service.
    return _request("POST", request.url, {"apikey": secret, "Authorization": "Bearer " + secret,
        "Content-Type": "application/json", "Accept": "application/json"},
        json.dumps(body).encode("utf-8"), request, "identity_link_unavailable")


def send_account_mail(request: AccountMailRequest, secret: str):
    """Send exactly one message through the mail provider."""
    if not isinstance(request, AccountMailRequest):
        raise ServiceRuntimeError("unsupported_account_mail_request")
    body = {"from": request.sender, "to": [request.recipient], "subject": request.subject, "text": request.text_body}
    return _request("POST", request.url, {"Authorization": "Bearer " + secret,
        "Content-Type": "application/json", "Accept": "application/json"},
        json.dumps(body).encode("utf-8"), request, "account_mail_unavailable")


@dataclass(frozen=True)
class PreparedAccountRequest:
    """One validated and counted request, ready for the two provider requests.

    It holds no password. The one a sign-up needs is generated when the
    identity request is built, so that it exists for that request alone.
    """

    action: str
    email: str = field(repr=False)

    @property
    def operation(self):
        return "account_" + self.action

    @property
    def result(self):
        return ({"record_type": SIGNUP_RESULT_VERSION, "status": CONFIRMATION_SENT} if self.action == SIGNUP_ACTION
                else {"record_type": RECOVERY_RESULT_VERSION, "status": RECOVERY_SENT})


def confirmation_message(name, link):
    """The message for an address that can have a new account."""
    return ("Confirm your " + name + " account",
            "Someone asked to create a " + name + " account for this address.\n\n"
            "Open this link to confirm the address, choose your password and finish creating the account:\n"
            + link + "\n\n"
            "If you did not ask for an account, you can ignore this message. The account cannot be used "
            "until the address is confirmed and a password is chosen on that page.\n")


def already_registered_message(name, origin):
    """The message for an address that already has an account.

    It carries no link with a token, so a person who asks to create an account
    for an address that is not theirs learns nothing about it.
    """
    return ("About your " + name + " account",
            "Someone asked to create a " + name + " account for this address. This address already has an "
            "account, so no new account was created and no password was changed.\n\n"
            "If it was you, sign in here:\n" + origin + "/login\n\n"
            "If you do not remember the password, ask for a new one from the same page.\n")


def recovery_message(name, link):
    """The message for an address that has an account and asked for a new password."""
    return ("Set a new " + name + " password",
            "Someone asked to set a new password for this address at " + name + ".\n\n"
            "Open this link to choose a new password:\n" + link + "\n\n"
            "If you did not ask for this, you can ignore this message. The password has not changed.\n")


def no_account_message(name, origin):
    """The message for an address that asked for a new password and has no account."""
    return ("About your " + name + " password",
            "Someone asked to set a new password for this address at " + name + ". This address does not "
            "have an account, so nothing was changed.\n\n"
            "If you want an account, create one here:\n" + origin + "/signup\n")


class AccountEmailAdapter:
    """Sign-up and recovery email behind the `account_email/v1` boundary.

    `prepare` reads one request, refuses what it does not understand and counts
    the attempt. `deliver` makes exactly one request to the identity provider
    and exactly one request to the mail provider. Nothing is repeated after an
    uncertain answer, and the result record is the same whether or not the
    address already has an account.
    """

    protocol_version = "account_email/v1"

    def __init__(self, configuration, secret_resolver, *, public_base_url, address_limits, display_name,
                 identity_transport=None, mail_transport=None):
        if not isinstance(configuration, AccountEmailConfiguration) or not callable(secret_resolver):
            raise ServiceRuntimeError("invalid_account_email_adapter",
                                      "a typed account email configuration and a host secret resolver are required")
        if (identity_transport is not None and not callable(identity_transport)
                or mail_transport is not None and not callable(mail_transport)):
            raise ServiceRuntimeError("invalid_account_email_adapter", "an installed transport must be callable")
        origin = validate_public_url(public_base_url, permit_loopback=configuration.allow_loopback)
        if urlsplit(origin).path:
            raise ServiceRuntimeError("account_email_origin_required", "the public service base URL must be an origin")
        self.configuration, self.public_base_url = configuration, origin
        self.display_name = text(display_name, "the service display name")
        self._secrets = secret_resolver
        self._identity_transport = identity_transport or generate_identity_link
        self._mail_transport = mail_transport or send_account_mail
        self.transport_basis = ("injected_transport" if identity_transport is not None or mail_transport is not None
                                else "provider_https")
        stated = ServiceRequestLimits.from_host(address_limits)
        # An open operation with no stated client address source would leave
        # only the allowance for each email address, and one caller could then
        # send a message to as many different addresses as it liked, at the
        # expense and the sender reputation of this deployment. The sign-in
        # limit can stay inactive because the cost there is bounded guessing.
        if not may_open_without_a_stated_address_source(configuration, stated):
            raise ServiceRuntimeError("account_email_needs_a_stated_client_address_source",
                "sign-up and recovery send messages to addresses a caller chooses, so the host states "
                "client_address_source in its http.request_limits block before either Boolean is true")
        self.address_attempts = FailedAttemptLimiter(configuration.address_attempt_limits(stated))
        self.email_attempts = FailedAttemptLimiter(configuration.email_attempt_limits())

    @property
    def signup_available(self):
        return self.configuration.signup_enabled and self.configuration.allow_network

    @property
    def recovery_available(self):
        return self.configuration.recovery_enabled and self.configuration.allow_network

    def availability(self):
        """What the account identity route publishes about the two operations.

        Two Booleans say which operation is open. The minimum length is the
        shortest password the website's choose-a-password page accepts, read
        from the host file so that the page and the host agree.
        """
        return {"signup_available": self.signup_available, "recovery_available": self.recovery_available,
                "minimum_password_length": self.configuration.minimum_password_length}

    def _available(self, action):
        return self.signup_available if action == SIGNUP_ACTION else self.recovery_available

    def _require_available(self, action):
        if action not in ACTIONS:
            raise AccountEmailError("route_unavailable", 404)
        if not self._available(action):
            raise AccountEmailError("account_" + action + "_unavailable", 503)

    def prepare(self, action, request_fields, address_key):
        """Read one request and count the attempt, before any provider request.

        A request with any field the operation does not read is refused, a
        sign-up that carries a password among them, and so is the retired
        sign-up version 1, which carried one.
        """
        self._require_available(action)
        expected = SIGNUP_REQUEST_VERSION if action == SIGNUP_ACTION else RECOVERY_REQUEST_VERSION
        if (not isinstance(request_fields, dict) or set(request_fields) != REQUEST_FIELDS[action]
                or request_fields.get("record_type") != expected):
            raise AccountEmailError("invalid_account_" + action, 400)
        address = email_address(request_fields["email"])
        self._count(address_key, address)
        return PreparedAccountRequest(action, address)

    def _count(self, address_key, address):
        """Refuse an address or an email address over its allowance, then count this attempt.

        Every attempt is counted, accepted or refused, because the cost this
        limits is the message that an accepted attempt sends.
        """
        counted = ((self.address_attempts, text(address_key, "the counted client address")),
                   (self.email_attempts, counted_email_key(address)))
        for limiter, key in counted:
            waiting = limiter.retry_after(key)
            if waiting:
                raise AccountEmailError(LIMIT_REACHED_CODE, 429,
                    details={"record_type": REFUSAL_RECORD_TYPE, "retry_after_seconds": waiting},
                    headers={"Retry-After": str(waiting)})
        for limiter, key in counted:
            limiter.record_failure(key)

    def deliver(self, prepared):
        """Generate the link, then send exactly one message. Nothing is repeated."""
        if not isinstance(prepared, PreparedAccountRequest):
            raise ServiceRuntimeError("invalid_prepared_account_request")
        self._require_available(prepared.action)
        token_hash = self._token_hash(prepared)
        signup = prepared.action == SIGNUP_ACTION
        if token_hash:
            link = (self.public_base_url + CONFIRM_PAGE + "?token_hash=" + quote(token_hash, safe="")
                    + "&type=" + prepared.action)
            subject, body = (confirmation_message(self.display_name, link) if signup
                             else recovery_message(self.display_name, link))
        else:
            subject, body = (already_registered_message(self.display_name, self.public_base_url) if signup
                             else no_account_message(self.display_name, self.public_base_url))
        self._send(prepared.email, subject, body)
        return prepared.result

    def _ask(self, transport, request, secret, unavailable):
        """Make exactly one provider request. Any other failure is an unknown outcome.

        Nothing here repeats a request. A transport that fails in a way this
        release does not name still answers with the unknown outcome of its
        own step, never with an unhandled failure or a second request.
        """
        try:
            answer = transport(request, secret)
        except AccountEmailError:
            raise
        except Exception:
            raise AccountEmailError(unavailable, 503) from None
        if not isinstance(answer, ProviderAnswer):
            raise AccountEmailError(unavailable, 503)
        return answer

    def _token_hash(self, prepared):
        """The token hash of a generated link, or empty text when the address is not eligible.

        A definite refusal that could be about the address returns empty text,
        exactly as the expected not-eligible answer does, so that the caller
        reads the same status and the same bytes either way. Only a refusal of
        this service itself, which answers the same for every address, is
        turned into a refusal the caller can see.
        """
        configuration = self.configuration
        # The key is resolved first, so that a missing or wrong key stops the
        # request before a password is generated for it.
        secret = self._secret(configuration.identity_service_key_ref, IDENTITY_SECRET_PREFIX)
        # A sign-up password exists only inside the one request built here. It
        # is not kept on this adapter, returned, put in a message or logged.
        answer = self._ask(self._identity_transport,
            IdentityLinkRequest(configuration.identity_origin + GENERATE_LINK_PATH, prepared.action, prepared.email,
                                generated_signup_password() if prepared.action == SIGNUP_ACTION else "",
                                configuration.timeout_seconds, configuration.maximum_response_bytes),
            secret, "identity_link_unavailable")
        if 400 <= answer.status_code < 500:
            if answer.status_code in SERVICE_REFUSAL_STATUSES:
                raise AccountEmailError("identity_link_refused", 503)
            return ""
        if not _accepted(answer.status_code):
            raise AccountEmailError("identity_link_unavailable", 503)
        # The provider's own `action_link` is never read. The message carries a
        # link to this service, so that the whole journey stays on this domain.
        value = answer.payload.get("hashed_token")
        if not isinstance(value, str) or TOKEN_HASH.fullmatch(value) is None:
            raise AccountEmailError("identity_link_unusable", 503)
        # The link is bound to the address and to the action that were asked
        # for. Without this, an answer naming another address would be put in a
        # message to the requesting address, and whoever opened it could
        # confirm that other account and then set its password.
        if (not names_the_same_address(answer.payload, prepared.email)
                or not names_the_same_action(answer.payload, prepared.action)):
            raise AccountEmailError("identity_link_unusable", 503)
        return value

    def _send(self, recipient, subject, body):
        configuration = self.configuration
        sender = (configuration.sender_name + " <" + configuration.sender_address + ">"
                  if configuration.sender_name else configuration.sender_address)
        answer = self._ask(self._mail_transport,
            AccountMailRequest(configuration.mail_origin + MAIL_SEND_PATH, sender, recipient, subject, body,
                               configuration.timeout_seconds, configuration.maximum_response_bytes),
            self._secret(configuration.mail_api_key_ref, MAIL_SECRET_PREFIX), "account_mail_unavailable")
        if 400 <= answer.status_code < 500:
            raise AccountEmailError("account_mail_refused", 503)
        if not _accepted(answer.status_code):
            raise AccountEmailError("account_mail_unavailable", 503)

    def _secret(self, reference, prefix):
        """Resolve one provider key from its environment reference, without logging it."""
        try:
            value = self._secrets(reference)
        except Exception:
            raise AccountEmailError("account_email_secret_unavailable", 503) from None
        if (not isinstance(value, str) or not value.startswith(prefix)
                or any(character.isspace() for character in value)):
            raise AccountEmailError("account_email_secret_unusable", 503)
        return value
