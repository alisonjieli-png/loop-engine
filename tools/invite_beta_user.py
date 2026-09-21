"""Prepare an invited Baltor beta account and show one password link.

The command asks the identity provider's administration interface to create a
confirmed user for the invited address, or finds the user that an earlier run
of this command created for that address. A found user that does not carry
the invitation mark gets no link, because someone else registered it and
chose its password. The command then asks the same interface to generate a
recovery link. The provider sends no email for either request. The link lets
the invited person set a password. It works once and it expires after the
period that is configured at the provider.

The administration credential arrives in the environment variable that
tools/operator_credentials.json names for the selected reference. Run this
command through tools/operator_credentials.py, so that the value never
appears in an argument, a file or the terminal. The credential is sent only
to the project that the reference is recorded for.

The link is written once to standard output and nowhere else. The report
holds a digest of the link, the user identity and the outcome. It never holds
the link, the credential or the address itself.

Nothing is repeated automatically. When a request may have reached the
provider and its answer is lost or unusable, the outcome is reported as
unknown. Inspect the provider before running the command again.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from enum import Enum
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import time
from urllib.parse import parse_qsl, urlsplit, urlunsplit

REPORT_RECORD_TYPE = "beta_invitation_report/v1"
MANIFEST_RECORD_TYPE = "operator_credential_references/v1"
DEFAULT_CREDENTIAL_REFERENCE = "supabase-secret"
IDENTITY_SERVICE = "supabase"
ADMINISTRATION_PURPOSE = "secret-api"
IDENTITY_HOST_SUFFIX = ".supabase.co"
SECURE_SCHEME = "https"
AUTHENTICATION_PATH = "/auth/v1"
USERS_PATH = AUTHENTICATION_PATH + "/admin/users"
LINK_PATH = AUTHENTICATION_PATH + "/admin/generate_link"
VERIFY_PATH = AUTHENTICATION_PATH + "/verify"
LINK_KIND = "recovery"
LINK_PARAMETERS = ("redirect_to", "token", "type")
CUSTOMER_ROLE = "authenticated"
EXISTING_ADDRESS_CODE = "email_exists"
INVITATION_MARKER = "baltor_invitation"
# The mark value is fixed apart from the report version, so that a later report
# version does not make this command refuse the users that it created earlier.
INVITATION_MARK_VALUE = "beta_invitation_report/v1"
SUPPORTED_INVITATION_MARKS = (INVITATION_MARK_VALUE,)
JSON_MEDIA_TYPE = "application/json"
PLAIN_ENCODING = "identity"
CREATED_STATUSES = (200, 201)
LINK_STATUS = 200
CREDENTIAL_REFUSED_STATUSES = (401, 403)
USER_NOT_FOUND_STATUS = 404
EXISTING_ADDRESS_STATUS = 422
EXIT_REFUSED_BEFORE_ANY_REQUEST = 2
MAXIMUM_ADDRESS_LENGTH = 2_048
MAXIMUM_INVITED_ADDRESS_LENGTH = 254
MAXIMUM_LOCAL_PART_LENGTH = 64
UNENCODED_BODY = "identity"
MINIMUM_LONG_SECRET_LENGTH = 16
LIMITATIONS = (
    "The link signs in as the invited person until it is used or expires. Only its digest is kept here.",
    "An administratively confirmed address is not proof that the person controls the mailbox.",
    "This report cannot show whether the person opened the link or set a password.",
)

_HOST_LABEL = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
_HOST_PATTERN = r"(?=[a-z0-9.-]{4,253}\Z)" + _HOST_LABEL + r"(?:\." + _HOST_LABEL + r")+"
_HOSTNAME = re.compile(_HOST_PATTERN)
_ADDRESS = re.compile(r"[a-z0-9_%+-]+(?:\.[a-z0-9_%+-]+)*@" + _HOST_PATTERN)
_PROJECT_REFERENCE = re.compile(r"[a-z]{20}")
_REDIRECT_PATH = re.compile(r"(?:/[A-Za-z0-9._~-]+)+")
_DOT_SEGMENTS = (".", "..")
_USER_IDENTITY = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
_LINK_SECRET = re.compile(r"[A-Za-z0-9_-]{20,256}")
_TIMESTAMP = re.compile(
    r"(\d{4})-(\d{2})-(\d{2})[Tt](\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,9}))?(?:([Zz])|([+-])(\d{2}):(\d{2}))")
_MANIFEST_FIELDS = ("environment", "value_pattern", "account")
_SENSITIVE_FIELDS = ("action_link", "email_otp", "hashed_token")
_REPORT_OPEN_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
_REPORT_MODE = 0o600


class InvitationOutcome(str, Enum):
    """What the operator may conclude when the command ends."""

    LINK_ISSUED = "link_issued"
    REFUSED = "refused"
    OUTCOME_UNKNOWN = "outcome_unknown"


class InvitationRefusal(str, Enum):
    """Refusals before any provider request. Nothing was created and no report exists."""

    PROJECT_REFERENCE = "project_reference_shape_refused"
    INVITED_ADDRESS = "invited_address_refused"
    SECURE_ORIGIN = "https_origin_required"
    HOST_SHAPE = "service_host_shape_refused"
    EXACT_ORIGIN = "exact_https_origin_required"
    REDIRECT_OUTSIDE_ORIGIN = "redirect_must_stay_inside_the_named_origin"
    REDIRECT_ADDRESS = "redirect_address_refused"
    CONFIRMATION = "explicit_confirmation_required_nothing_was_created"
    CREDENTIAL_MANIFEST = "credential_manifest_unavailable"
    CREDENTIAL_REFERENCE = "credential_reference_is_not_an_identity_administration_key"
    CREDENTIAL_PROJECT = "credential_is_recorded_for_another_project"
    CREDENTIAL_VALUE = "administration_credential_missing_or_malformed"
    REPORT_FOLDER = "report_folder_must_exist"
    REPORT_EXISTS = "report_path_must_not_exist"
    REPORT_PATH = "report_path_refused"
    LIMITS = "invalid_administration_limits"
    SECRET_IN_OUTPUT = "secret_in_output_refused"


class InvitationFailure(str, Enum):
    """Why a run that reached the provider did not end with a displayed link."""

    USER_CREATION_UNKNOWN = "user_creation_outcome_unknown_do_not_repeat"
    LINK_UNKNOWN = "link_outcome_unknown_do_not_repeat"
    PROVIDER_REDIRECT = "provider_redirect_refused"
    CREDENTIAL_REFUSED = "credential_refused_by_provider"
    USER_CREATION_REFUSED = "user_creation_refused_by_provider"
    USER_NOT_FOUND = "user_not_found_at_the_provider"
    LINK_REFUSED = "link_refused_by_provider"
    USER_NOT_CONFIRMED = "user_is_not_confirmed"
    USER_CANNOT_SIGN_IN = "user_cannot_sign_in_at_the_provider"
    IDENTITY_MISMATCH = "user_identity_mismatch"
    EXISTING_USER_NOT_INVITED = "existing_user_was_not_created_by_the_invitation_command"
    REDIRECT_REPLACED = "redirect_replaced_by_the_provider"
    LINK_SHAPE = "link_shape_refused"
    LINK_KIND_MISMATCH = "link_kind_mismatch"
    SECRET_IN_OUTPUT = "secret_in_output_refused"
    REPORT_NOT_WRITTEN = "report_not_written_link_withheld"
    UNEXPECTED_ERROR = "unexpected_error"


class InvitationDetail(str, Enum):
    """The cause behind a failure. An unexpected error names its exception type instead."""

    TIMEOUT = "timeout"
    CONNECTION_FAILED = "connection_failed"
    RESPONSE_TOO_LARGE = "response_too_large"
    RESPONSE_ENCODING = "response_encoding_refused"
    TRANSPORT_ERROR = "transport_error"
    TRANSPORT_CONTRACT = "transport_contract_violation"
    MALFORMED_RESPONSE = "malformed_response"
    UNEXPECTED_STATUS = "unexpected_status"
    OTHER_USER = "response_does_not_describe_the_invited_user"


REFUSALS = tuple(item.value for item in InvitationRefusal)
FAILURES = tuple(item.value for item in InvitationFailure)
DETAILS = tuple(item.value for item in InvitationDetail)
TRANSPORT_FAILURE_CODES = (InvitationDetail.TIMEOUT.value, InvitationDetail.CONNECTION_FAILED.value,
                           InvitationDetail.RESPONSE_TOO_LARGE.value, InvitationDetail.RESPONSE_ENCODING.value)
_EXIT_CODES = {InvitationOutcome.LINK_ISSUED: 0, InvitationOutcome.REFUSED: 1, InvitationOutcome.OUTCOME_UNKNOWN: 3}


class Refusal(Exception):
    """Refused before any provider request. It carries a code, never a value."""

    def __init__(self, reason):
        self.code = InvitationRefusal(reason).value
        super().__init__(self.code)


class TransportFailure(Exception):
    """The answer was lost, so the request may or may not have taken effect."""

    def __init__(self, code):
        if code not in TRANSPORT_FAILURE_CODES:
            raise ValueError("unsupported transport failure code")
        self.code = code
        super().__init__(code)


class _Stop(Exception):
    """Ends a run that reached the provider, with a typed outcome and failure."""

    def __init__(self, outcome, failure, detail=None):
        super().__init__(failure.value)
        self.outcome, self.failure, self.detail = outcome, failure, detail


@dataclass(frozen=True)
class AdministrationLimits:
    """Bounds for one administration request and for reading its answer."""

    timeout_seconds: float = 10.0
    maximum_response_bytes: int = 65_536
    maximum_link_length: int = 2_048
    maximum_clock_skew_seconds: int = 300

    def __post_init__(self):
        if (type(self.timeout_seconds) not in (int, float) or not math.isfinite(self.timeout_seconds)
                or not 0 < self.timeout_seconds <= 60
                or type(self.maximum_response_bytes) is not int or not 1 <= self.maximum_response_bytes <= 1_048_576
                or type(self.maximum_link_length) is not int or not 64 <= self.maximum_link_length <= 8_192
                or type(self.maximum_clock_skew_seconds) is not int
                or not 0 <= self.maximum_clock_skew_seconds <= 3_600):
            raise Refusal(InvitationRefusal.LIMITS)


@dataclass(frozen=True)
class InvitationRequest:
    """Validated operator input. Nothing here comes from a provider answer."""

    project_ref: str
    email: str
    service_origin: str
    redirect_to: str

    def __post_init__(self):
        _require_project_reference(self.project_ref)
        object.__setattr__(self, "email", _invited_address(self.email))
        _require_exact_origin(self.service_origin)
        _require_redirect_inside_origin(self.redirect_to, self.service_origin)

    @property
    def project_host(self):
        return self.project_ref + IDENTITY_HOST_SUFFIX

    @property
    def project_origin(self):
        return urlunsplit((SECURE_SCHEME, self.project_host, "", "", ""))

    @property
    def issuer(self):
        return self.project_origin + AUTHENTICATION_PATH

    @property
    def email_digest(self):
        return hashlib.sha256(self.email.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CredentialBinding:
    """Where the administration credential arrives and which project it is recorded for."""

    reference: str
    environment_name: str
    value_pattern: str
    project_ref: str


@dataclass(frozen=True)
class AdministrationRequest:
    """One bounded POST to the validated project origin. Private values stay out of repr."""

    url: str
    body: bytes = field(repr=False)
    timeout_seconds: float
    maximum_response_bytes: int
    credential: str = field(repr=False)


@dataclass(frozen=True)
class AdministrationResponse:
    """A status and a bounded body. The body can hold the link, so repr omits it."""

    status: int
    body: bytes = field(repr=False)


@dataclass(frozen=True)
class InvitationResult:
    """The typed result of one run. The link and other private values stay out of repr."""

    outcome: InvitationOutcome
    failure: "InvitationFailure | None"
    detail: "str | None"
    user_id: "str | None"
    user_created: "bool | None"
    link_generated: "bool | None"
    provider_requests: int
    provider_status: "int | None"
    invitation_mark_present: "bool | None" = None
    link: "str | None" = field(default=None, repr=False)
    sensitive_values: "tuple[str, ...]" = field(default=(), repr=False)


@dataclass
class _Progress:
    """What is known so far. It is kept apart so that a stop can still be reported."""

    requests: int = 0
    status: "int | None" = None
    user_id: "str | None" = None
    user_created: "bool | None" = None
    link_generated: "bool | None" = None
    mark_present: "bool | None" = None
    sensitive: list = field(default_factory=list)


# Guards before any request.

def _require_project_reference(value):
    if not isinstance(value, str) or not _PROJECT_REFERENCE.fullmatch(value):
        raise Refusal(InvitationRefusal.PROJECT_REFERENCE)


def _split(value, reason):
    if (not isinstance(value, str) or not value.isascii() or not 0 < len(value) <= MAXIMUM_ADDRESS_LENGTH
            or any(ord(character) <= 32 or ord(character) == 127 for character in value)):
        raise Refusal(reason)
    try:
        return urlsplit(value)
    except ValueError:
        raise Refusal(reason) from None


def _require_secure_scheme(parts):
    if parts.scheme != SECURE_SCHEME:
        raise Refusal(InvitationRefusal.SECURE_ORIGIN)


def _require_public_host_shape(host):
    """A public name with at least two labels. Addresses and single labels are refused."""
    if not isinstance(host, str) or not _HOSTNAME.fullmatch(host) or host.rsplit(".", 1)[-1].isdigit():
        raise Refusal(InvitationRefusal.HOST_SHAPE)


def _require_exact_origin(value):
    parts = _split(value, InvitationRefusal.EXACT_ORIGIN)
    _require_secure_scheme(parts)
    _require_public_host_shape(parts.hostname)
    if urlunsplit((parts.scheme, parts.hostname or "", "", "", "")) != value:
        raise Refusal(InvitationRefusal.EXACT_ORIGIN)


def _require_same_origin(parts, origin):
    if urlunsplit((parts.scheme, parts.netloc, "", "", "")) != origin:
        raise Refusal(InvitationRefusal.REDIRECT_OUTSIDE_ORIGIN)


def _require_redirect_inside_origin(value, origin):
    parts = _split(value, InvitationRefusal.REDIRECT_ADDRESS)
    _require_same_origin(parts, origin)
    if (not _REDIRECT_PATH.fullmatch(parts.path)
            or any(segment in _DOT_SEGMENTS for segment in parts.path.split("/"))
            or urlunsplit((parts.scheme, parts.netloc, parts.path, "", "")) != value):
        raise Refusal(InvitationRefusal.REDIRECT_ADDRESS)


def _invited_address(value):
    """The provider stores addresses in lower case, so the same form is used everywhere."""
    lowered = value.lower() if isinstance(value, str) and value.isascii() else ""
    local, _, domain = lowered.partition("@")
    if (not _ADDRESS.fullmatch(lowered) or len(lowered) > MAXIMUM_INVITED_ADDRESS_LENGTH
            or len(local) > MAXIMUM_LOCAL_PART_LENGTH
            or domain.rsplit(".", 1)[-1].isdigit()):
        raise Refusal(InvitationRefusal.INVITED_ADDRESS)
    return lowered


def _require_confirmation(acknowledged):
    if acknowledged is not True:
        raise Refusal(InvitationRefusal.CONFIRMATION)


def load_manifest():
    """The reference manifest that tools/operator_credentials.py also reads."""
    try:
        from operator_credentials import references
        return references()
    except Exception:
        raise Refusal(InvitationRefusal.CREDENTIAL_MANIFEST) from None


def _require_administration_reference(spec):
    if (not isinstance(spec, dict) or spec.get("service") != IDENTITY_SERVICE
            or spec.get("purpose") != ADMINISTRATION_PURPOSE
            or any(not isinstance(spec.get(name), str) or not spec.get(name) for name in _MANIFEST_FIELDS)):
        raise Refusal(InvitationRefusal.CREDENTIAL_REFERENCE)


def _require_supported_manifest(manifest):
    if not isinstance(manifest, dict) or manifest.get("record_type") != MANIFEST_RECORD_TYPE:
        raise Refusal(InvitationRefusal.CREDENTIAL_MANIFEST)


def credential_binding(reference, manifest):
    """Read the environment name, the value shape and the bound project from the manifest."""
    _require_supported_manifest(manifest)
    entries = manifest.get("api_keys") if isinstance(manifest, dict) else None
    spec = entries.get(reference) if isinstance(entries, dict) and isinstance(reference, str) else None
    _require_administration_reference(spec)
    return CredentialBinding(reference, spec["environment"], spec["value_pattern"], spec["account"])


def _require_credential_for_project(binding, request):
    if binding.project_ref != request.project_ref:
        raise Refusal(InvitationRefusal.CREDENTIAL_PROJECT)


def _require_credential_shape(value, binding):
    try:
        accepted = isinstance(value, str) and re.fullmatch(binding.value_pattern, value) is not None
    except re.error:
        accepted = False
    if not accepted:
        raise Refusal(InvitationRefusal.CREDENTIAL_VALUE)


def resolve_credential(binding, request, environment):
    """Take the credential from the named environment variable. It is never printed."""
    _require_credential_for_project(binding, request)
    value = environment.get(binding.environment_name)
    _require_credential_shape(value, binding)
    return value


def reserve_report(value):
    """Create the report file before any request, so that a run never overwrites evidence."""
    path = Path(value)
    try:
        folder = path.parent.resolve(strict=True)
    except (OSError, RuntimeError):
        raise Refusal(InvitationRefusal.REPORT_FOLDER) from None
    if not folder.is_dir() or path.name in ("", *_DOT_SEGMENTS):
        raise Refusal(InvitationRefusal.REPORT_FOLDER)
    target = folder / path.name
    try:
        descriptor = os.open(target, _REPORT_OPEN_FLAGS, _REPORT_MODE)
    except FileExistsError:
        raise Refusal(InvitationRefusal.REPORT_EXISTS) from None
    except OSError:
        raise Refusal(InvitationRefusal.REPORT_PATH) from None
    return target, os.fdopen(descriptor, "w", encoding="utf-8")


# The default transport.

def _client_options(request, http_transport):
    """Redirects are never followed and proxy settings in the environment are ignored."""
    return {"follow_redirects": False, "trust_env": False, "timeout": request.timeout_seconds,
            "transport": http_transport}


def _within_limit(size, request):
    return size <= request.maximum_response_bytes


def _deadline_passed(deadline):
    """One overall deadline for the whole answer. The library's own timeout restarts for each read."""
    return time.monotonic() > deadline


def _require_unencoded_body(encoding):
    """An encoded answer is refused before it is read, so no decoder can grow it beyond the bound."""
    if (encoding or UNENCODED_BODY).strip().lower() != UNENCODED_BODY:
        raise TransportFailure(InvitationDetail.RESPONSE_ENCODING.value)


def send_administration_request(request, *, http_transport=None):
    """Send one POST and read a bounded answer. A lost answer becomes a typed failure."""
    import httpx
    deadline = time.monotonic() + request.timeout_seconds
    headers = {"apikey": request.credential, "Authorization": "Bearer " + request.credential,
               "Accept": JSON_MEDIA_TYPE, "Accept-Encoding": UNENCODED_BODY, "Content-Type": JSON_MEDIA_TYPE}
    try:
        with httpx.Client(**_client_options(request, http_transport)) as client:
            with client.stream("POST", request.url, headers=headers, content=request.body) as response:
                _require_unencoded_body(response.headers.get("content-encoding"))
                chunks, size = [], 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if not _within_limit(size, request):
                        raise TransportFailure(InvitationDetail.RESPONSE_TOO_LARGE.value)
                    if _deadline_passed(deadline):
                        raise TransportFailure(InvitationDetail.TIMEOUT.value)
                    chunks.append(chunk)
                return AdministrationResponse(response.status_code, b"".join(chunks))
    except TransportFailure:
        raise
    except httpx.TimeoutException:
        raise TransportFailure(InvitationDetail.TIMEOUT.value) from None
    except httpx.HTTPError:
        raise TransportFailure(InvitationDetail.CONNECTION_FAILED.value) from None


# Reading answers.

def _unique_pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("a repeated key makes the answer ambiguous")
        value[key] = item
    return value


def _refuse_constant(name):
    raise ValueError("a number that is not finite is not supported")


def _json_object(body):
    value = json.loads(body.decode("utf-8"), object_pairs_hook=_unique_pairs, parse_constant=_refuse_constant)
    if not isinstance(value, dict):
        raise ValueError("an object is required")
    return value


def _answer(body, unknown):
    try:
        return _json_object(body)
    except (ValueError, RecursionError):
        raise _Stop(InvitationOutcome.OUTCOME_UNKNOWN, unknown, InvitationDetail.MALFORMED_RESPONSE.value) from None


def _provider_error_code(body):
    """The provider's typed error code, in either of its two published answer shapes."""
    try:
        payload = _json_object(body)
    except (ValueError, RecursionError):
        return None
    for name in ("error_code", "code"):
        if isinstance(payload.get(name), str):
            return payload[name]
    return None


def _timestamp(value):
    """Read an RFC 3339 time with a zone. Python 3.10 cannot read every provider form itself."""
    match = _TIMESTAMP.fullmatch(value) if isinstance(value, str) else None
    if match is None:
        return None
    year, month, day, hour, minute, second = (int(match.group(index)) for index in range(1, 7))
    fraction = (match.group(7) or "")[:6].ljust(6, "0")
    offset = timedelta(0)
    if match.group(8) is None:
        offset = timedelta(hours=int(match.group(10)), minutes=int(match.group(11)))
        if match.group(9) == "-":
            offset = -offset
    try:
        return datetime(year, month, day, hour, minute, second, int(fraction), tzinfo=timezone(offset))
    except ValueError:
        return None


def _utc_now():
    return datetime.now(timezone.utc)


# Guards after a request.

def _refuse_provider_redirect(status):
    """A redirect is never followed. The first request may still have taken effect."""
    if 300 <= status <= 399:
        raise _Stop(InvitationOutcome.OUTCOME_UNKNOWN, InvitationFailure.PROVIDER_REDIRECT)


def _require_transport_contract(response, unknown):
    """An injected transport must return the typed answer record, or the outcome is unknown."""
    if (not isinstance(response, AdministrationResponse) or type(response.status) is not int
            or not isinstance(response.body, bytes)):
        raise _Stop(InvitationOutcome.OUTCOME_UNKNOWN, unknown, InvitationDetail.TRANSPORT_CONTRACT.value)


def _require_definite_status(status, unknown):
    """Only a 4xx answer is a definite refusal. Any other unexpected status leaves the outcome unknown."""
    if not 400 <= status <= 499:
        raise _Stop(InvitationOutcome.OUTCOME_UNKNOWN, unknown, InvitationDetail.UNEXPECTED_STATUS.value)


def _require_bounded_body(body, limits, unknown):
    if len(body) > limits.maximum_response_bytes:
        raise _Stop(InvitationOutcome.OUTCOME_UNKNOWN, unknown, InvitationDetail.RESPONSE_TOO_LARGE.value)


def _require_link_at_project(parts, request):
    if parts.scheme != SECURE_SCHEME or parts.netloc != request.project_host:
        raise _Stop(InvitationOutcome.REFUSED, InvitationFailure.LINK_SHAPE)


def _require_link_kind(kind, payload):
    stated = payload.get("verification_type")
    if kind != LINK_KIND or (stated is not None and stated != LINK_KIND):
        raise _Stop(InvitationOutcome.REFUSED, InvitationFailure.LINK_KIND_MISMATCH)


def _require_same_identity(payload, request, progress):
    identity = payload.get("id")
    if (not isinstance(identity, str) or not _USER_IDENTITY.fullmatch(identity)
            or payload.get("email") != request.email
            or (progress.user_id is not None and identity != progress.user_id)):
        raise _Stop(InvitationOutcome.REFUSED, InvitationFailure.IDENTITY_MISMATCH)


def _invitation_mark_present(payload):
    """The mark lives in metadata that only the administration interface can write."""
    metadata = payload.get("app_metadata")
    mark = metadata.get(INVITATION_MARKER) if isinstance(metadata, dict) else None
    return isinstance(mark, str) and mark in SUPPORTED_INVITATION_MARKS


def _require_invited_user(progress):
    """A user that this run only found must carry the mark of an earlier run of this command.

    Whoever registered an unmarked account chose its password and may hold sessions and
    personal keys for it. A link for such an account would hand the invited person an
    account that someone else can still use.
    """
    if progress.user_created is not True and progress.mark_present is not True:
        raise _Stop(InvitationOutcome.REFUSED, InvitationFailure.EXISTING_USER_NOT_INVITED)


def _require_confirmed_user(payload, limits, now):
    confirmed = _timestamp(payload.get("email_confirmed_at"))
    if confirmed is None or confirmed > now + timedelta(seconds=limits.maximum_clock_skew_seconds):
        raise _Stop(InvitationOutcome.REFUSED, InvitationFailure.USER_NOT_CONFIRMED)


def _require_sign_in_allowed(payload, now):
    """The service accepts only an ordinary customer user that the provider has not disabled."""
    banned = payload.get("banned_until")
    until = _timestamp(banned)
    if (payload.get("is_anonymous") is not False or payload.get("role") != CUSTOMER_ROLE
            or payload.get("deleted_at") is not None
            or (banned is not None and (until is None or until > now))):
        raise _Stop(InvitationOutcome.REFUSED, InvitationFailure.USER_CANNOT_SIGN_IN)


def _require_redirect_kept(redirect, payload, request):
    """The provider replaces a redirect address that is not on its allow list."""
    stated = payload.get("redirect_to")
    if redirect != request.redirect_to or (stated is not None and stated != request.redirect_to):
        raise _Stop(InvitationOutcome.REFUSED, InvitationFailure.REDIRECT_REPLACED)


def _link_parts(link, request, limits):
    refused = _Stop(InvitationOutcome.REFUSED, InvitationFailure.LINK_SHAPE)
    if (not isinstance(link, str) or not link.isascii() or not 0 < len(link) <= limits.maximum_link_length
            or any(ord(character) <= 32 or ord(character) == 127 for character in link)):
        raise refused
    try:
        parts = urlsplit(link)
        pairs = parse_qsl(parts.query, keep_blank_values=True, strict_parsing=True)
    except ValueError:
        raise refused from None
    _require_link_at_project(parts, request)
    if (parts.path != VERIFY_PATH or parts.fragment
            or sorted(name for name, _ in pairs) != sorted(LINK_PARAMETERS)):
        raise refused
    query = dict(pairs)
    if not _LINK_SECRET.fullmatch(query["token"]):
        raise refused
    return query["token"], query["redirect_to"], query["type"]


# The run.

def _exchange(transport, url, fields, credential, limits, progress, unknown):
    """One request, never repeated. A lost or unusable answer leaves the outcome unknown."""
    body = json.dumps(fields, separators=(",", ":")).encode("utf-8")
    request = AdministrationRequest(url, body, limits.timeout_seconds, limits.maximum_response_bytes, credential)
    progress.requests += 1
    progress.status = None
    try:
        response = transport(request)
    except TransportFailure as failure:
        raise _Stop(InvitationOutcome.OUTCOME_UNKNOWN, unknown, failure.code) from None
    except Exception:
        raise _Stop(InvitationOutcome.OUTCOME_UNKNOWN, unknown, InvitationDetail.TRANSPORT_ERROR.value) from None
    _require_transport_contract(response, unknown)
    progress.status = response.status
    _refuse_provider_redirect(response.status)
    _require_bounded_body(response.body, limits, unknown)
    return response


def _create_or_find_user(request, credential, transport, limits, progress):
    unknown = InvitationFailure.USER_CREATION_UNKNOWN
    fields = {"email": request.email, "email_confirm": True, "app_metadata": {INVITATION_MARKER: INVITATION_MARK_VALUE}}
    response = _exchange(transport, request.project_origin + USERS_PATH, fields, credential, limits, progress, unknown)
    if response.status in CREATED_STATUSES:
        payload = _answer(response.body, unknown)
        described = payload["user"] if isinstance(payload.get("user"), dict) else payload
        identity = described.get("id")
        if (not isinstance(identity, str) or not _USER_IDENTITY.fullmatch(identity)
                or described.get("email") != request.email):
            raise _Stop(InvitationOutcome.OUTCOME_UNKNOWN, unknown, InvitationDetail.OTHER_USER.value)
        progress.user_id, progress.user_created = identity, True
        return
    _require_definite_status(response.status, unknown)
    progress.user_created = False
    if (response.status == EXISTING_ADDRESS_STATUS
            and _provider_error_code(response.body) == EXISTING_ADDRESS_CODE):
        return
    if response.status in CREDENTIAL_REFUSED_STATUSES:
        raise _Stop(InvitationOutcome.REFUSED, InvitationFailure.CREDENTIAL_REFUSED)
    raise _Stop(InvitationOutcome.REFUSED, InvitationFailure.USER_CREATION_REFUSED)


def _generate_link(request, credential, transport, limits, progress, now):
    unknown = InvitationFailure.LINK_UNKNOWN
    fields = {"type": LINK_KIND, "email": request.email, "redirect_to": request.redirect_to}
    response = _exchange(transport, request.project_origin + LINK_PATH, fields, credential, limits, progress, unknown)
    if response.status != LINK_STATUS:
        _require_definite_status(response.status, unknown)
        progress.link_generated = False
        if response.status in CREDENTIAL_REFUSED_STATUSES:
            raise _Stop(InvitationOutcome.REFUSED, InvitationFailure.CREDENTIAL_REFUSED)
        if response.status == USER_NOT_FOUND_STATUS:
            raise _Stop(InvitationOutcome.REFUSED, InvitationFailure.USER_NOT_FOUND)
        raise _Stop(InvitationOutcome.REFUSED, InvitationFailure.LINK_REFUSED)
    payload = _answer(response.body, unknown)
    # Each of these values can sign in as the user, so none may reach a report or a message.
    for name in _SENSITIVE_FIELDS:
        if isinstance(payload.get(name), str) and payload[name]:
            progress.sensitive.append(payload[name])
    link = payload.get("action_link")
    if isinstance(link, str) and link:
        progress.link_generated = True
    secret, redirect, kind = _link_parts(link, request, limits)
    progress.sensitive.append(secret)
    _require_link_kind(kind, payload)
    _require_same_identity(payload, request, progress)
    if isinstance(payload.get("id"), str) and _USER_IDENTITY.fullmatch(payload["id"]):
        progress.user_id = payload["id"]
    progress.mark_present = _invitation_mark_present(payload)
    _require_invited_user(progress)
    _require_confirmed_user(payload, limits, now)
    _require_sign_in_allowed(payload, now)
    _require_redirect_kept(redirect, payload, request)
    return link


def _outcome_after_defect(progress):
    """A defect after a request leaves the provider state unknown."""
    return InvitationOutcome.OUTCOME_UNKNOWN if progress.requests else InvitationOutcome.REFUSED


def issue_invitation(request, credential, transport, limits=None, now=None):
    """Create or find the confirmed user, then ask for one recovery link."""
    limits = AdministrationLimits() if limits is None else limits
    current = _utc_now if now is None else now
    progress, link = _Progress(), None
    try:
        _create_or_find_user(request, credential, transport, limits, progress)
        link = _generate_link(request, credential, transport, limits, progress, current())
        outcome, failure, detail = InvitationOutcome.LINK_ISSUED, None, None
    except _Stop as stop:
        outcome, failure, detail, link = stop.outcome, stop.failure, stop.detail, None
    except Exception as error:
        # No message is kept, because a message could hold a private value.
        outcome = _outcome_after_defect(progress)
        failure, detail, link = InvitationFailure.UNEXPECTED_ERROR, type(error).__name__, None
    return InvitationResult(outcome, failure, detail, progress.user_id, progress.user_created,
                            progress.link_generated, progress.requests, progress.status, progress.mark_present, link,
                            tuple(progress.sensitive))


# Output.

def build_report(request, result, observed_at):
    issued = result.outcome is InvitationOutcome.LINK_ISSUED and isinstance(result.link, str)
    return {
        "record_type": REPORT_RECORD_TYPE,
        "observed_at": observed_at.isoformat(timespec="seconds"),
        "project_url": request.project_origin,
        "identity_issuer": request.issuer,
        "redirect_to": request.redirect_to,
        "email_sha256": request.email_digest,
        "user_id": result.user_id,
        "user_created": result.user_created,
        "invitation_mark_present": result.invitation_mark_present,
        "link_kind": LINK_KIND,
        "link_generated": result.link_generated,
        "link_sha256": hashlib.sha256(result.link.encode("utf-8")).hexdigest() if issued else None,
        "outcome": result.outcome.value,
        "failure": result.failure.value if result.failure is not None else None,
        "detail": result.detail,
        "provider_status": result.provider_status,
        "provider_requests": result.provider_requests,
        "automatic_retries": 0,
        "email_requested": False,
        "limitations": list(LIMITATIONS),
    }


def _appears(value, text):
    """A long private value counts anywhere. A short code counts only as a whole value,
    so that a few digits inside a digest do not refuse an honest report."""
    if len(value) >= MINIMUM_LONG_SECRET_LENGTH:
        return value in text
    return re.search(r"(?<![0-9A-Za-z])" + re.escape(value) + r"(?![0-9A-Za-z])", text) is not None


def _require_no_secret(text, sensitive_values):
    if any(value and _appears(value, text) for value in sensitive_values):
        raise Refusal(InvitationRefusal.SECRET_IN_OUTPUT)


def encode_report(report, sensitive_values):
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    _require_no_secret(encoded, sensitive_values)
    return encoded


def _withheld(result, failure):
    """A link that cannot be recorded is not shown."""
    if result.outcome is not InvitationOutcome.LINK_ISSUED:
        return result
    return replace(result, outcome=InvitationOutcome.REFUSED, failure=failure, detail=None, link=None)


def _write_durably(stream, text):
    stream.write(text)
    stream.flush()
    os.fsync(stream.fileno())


def _report_is_durable(written):
    return written is True


def _record(stream, request, result, observed_at, sensitive):
    """Write the report, and return the result it describes and whether it is on disk."""
    recorded, encoded = result, None
    for candidate in (result, _withheld(result, InvitationFailure.SECRET_IN_OUTPUT)):
        try:
            recorded, encoded = candidate, encode_report(build_report(request, candidate, observed_at), sensitive)
            break
        except Refusal:
            recorded, encoded = candidate, None
    written = False
    if encoded is not None:
        try:
            _write_durably(stream, encoded)
            written = True
        except OSError:
            written = False
    return recorded, written


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], allow_abbrev=False)
    parser.add_argument("--project-ref", required=True, help="identity project reference, twenty lower case letters")
    parser.add_argument("--email", required=True, help="address of the invited person; it is used in lower case")
    parser.add_argument("--service-origin", required=True, help="exact HTTPS origin of the website, without a path")
    parser.add_argument("--redirect-to", required=True, help="return address inside that origin, without a query")
    parser.add_argument("--report", required=True, help="new report file in an existing folder")
    parser.add_argument("--credential-ref", default=DEFAULT_CREDENTIAL_REFERENCE,
                        help="reference name in tools/operator_credentials.json")
    parser.add_argument("--acknowledge-identity-account-effects", action="store_true",
                        help="confirm that a user may be created and that a sign-in link will be generated")
    return parser


def _select_transport(transport):
    """Only an absent transport selects the network. An injected one is used even when it is falsy."""
    return send_administration_request if transport is None else transport


def _sensitive_values(credential, result):
    return (credential, *result.sensitive_values)


def _safe_summary(summary, sensitive):
    try:
        _require_no_secret(summary, sensitive)
    except Refusal as refusal:
        return refusal.code
    return summary


def main(argv=None, *, environment=None, transport=None, manifest=None, now=None):
    arguments = build_parser().parse_args(argv)
    current = _utc_now if now is None else now
    try:
        request = InvitationRequest(arguments.project_ref, arguments.email, arguments.service_origin,
                                    arguments.redirect_to)
        limits = AdministrationLimits()
        _require_confirmation(arguments.acknowledge_identity_account_effects)
        binding = credential_binding(arguments.credential_ref, load_manifest() if manifest is None else manifest)
        credential = resolve_credential(binding, request, os.environ if environment is None else environment)
        target, stream = reserve_report(arguments.report)
    except Refusal as refusal:
        sys.stderr.write(refusal.code + "\n")
        return EXIT_REFUSED_BEFORE_ANY_REQUEST
    try:
        return _run(request, credential, _select_transport(transport), limits, current, target, stream)
    except Exception as error:
        # A defect here must not print a message that could hold a private value.
        sys.stderr.write(InvitationFailure.UNEXPECTED_ERROR.value + ":" + type(error).__name__ + "\n")
        return _EXIT_CODES[InvitationOutcome.OUTCOME_UNKNOWN]


def _run(request, credential, transport, limits, current, target, stream):
    """Everything after the report file exists: requests, then the report, then the link."""
    with stream:
        result = issue_invitation(request, credential, transport, limits, current)
        sensitive = _sensitive_values(credential, result)
        recorded, written = _record(stream, request, result, current(), sensitive)
    if not _report_is_durable(written):
        recorded = _withheld(recorded, InvitationFailure.REPORT_NOT_WRITTEN)
    shown = False
    if recorded.outcome is InvitationOutcome.LINK_ISSUED:
        try:
            sys.stdout.write(recorded.link + "\n")
            sys.stdout.flush()
            shown = True
        except OSError:
            shown = False
    summary = json.dumps({
        "outcome": recorded.outcome.value,
        "failure": recorded.failure.value if recorded.failure is not None else None,
        "detail": recorded.detail, "user_created": recorded.user_created,
        "invitation_mark_present": recorded.invitation_mark_present,
        "provider_requests": recorded.provider_requests, "link_displayed": shown,
        "report": str(target), "report_written": written}, sort_keys=True)
    sys.stderr.write(_safe_summary(summary, sensitive) + "\n")
    if recorded.outcome is InvitationOutcome.LINK_ISSUED and not shown:
        return _EXIT_CODES[InvitationOutcome.REFUSED]
    return _EXIT_CODES[recorded.outcome]


if __name__ == "__main__":
    raise SystemExit(main())
