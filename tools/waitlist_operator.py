"""Read the Baltor waiting list, invite one entry, or erase one entry.

The command talks to the deployed service over HTTPS with an operator service
token. It does three things and nothing else.

`--list` reads the waiting list and prints one line for each entry: the entry
reference to pass back, the state, the address and the note. Reading the list
performs no write and sends no email.

`--invite` invites exactly one entry, in this order:

```text
invite one entry
├── 0. check that checkout takes a discount code, and that a saved payment
│      account report says this exact code exists
├── 1. record the invitation in the service, with its discount code
├── 2. prepare the account at the identity provider and take its link
├── 3. send the invitation email through the mail provider
└── 4. record what happened to that email, sent or unknown
```

Step zero exists because the message tells a person to enter a code at
checkout. Two separate facts have to hold before that sentence is sent: the
service has to report that its checkout sessions take a discount code, and
`--discount-evidence` has to name the report that
`tools/setup_stripe_sandbox.py` wrote when it found or created that code in
the payment account. Either one missing refuses the run before anything is
recorded and before any message is prepared.

`--forget` erases one entry's address and note and moves it to the removed
state, so that a person who asks to be taken off the list is taken off it. It
sends no email and prepares no account. The entry keeps its decision history
and the one-way digest of the address; the address and the note are gone and
cannot be recovered. `--acknowledge-erasure` is required, because nothing
undoes it.

The order matters. The service records the invitation before any outside
effect, so an email that may have gone out is never sent twice by a second
run: the same request identity replays the first decision and writes nothing.
Step three is an external effect with no automatic repeat. When its answer is
lost, step four records the delivery as unknown and the operator inspects the
mail provider before deciding anything.

Three credentials arrive in the environment variables that
tools/operator_credentials.json names: the operator service token, the
identity administration key and the mail sending key. Run this command through
tools/operator_credentials.py, so that no value appears in an argument, a file
or the terminal. No credential, no sign-in link and no address is written to
the report. The report holds identifiers, digests, states and counts.

The discount code is the promotion code that tools/setup_stripe_sandbox.py
created in the payment account. This command does not create a discount, and
it cannot: a code the payment provider does not hold would be refused at
checkout, so the code is passed in with the report that shows it exists, and
recorded as sent. That report is evidence from the moment it was written. It
is not a reading of the payment account now, and this command holds no
payment credential with which to take one.

The report is written to a path that must not exist, so a run never overwrites
earlier evidence.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import uuid
from urllib.parse import urlsplit, urlunsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import invite_beta_user  # noqa: E402
import operator_credentials  # noqa: E402

REPORT_RECORD_TYPE = "waitlist_operator_report/v1"
DECISION_RECORD_TYPE = "service_waitlist_decision/v1"
LISTING_RECORD_TYPE = "service_waitlist_listing/v1"
RESULT_RECORD_TYPE = "service_waitlist_result/v1"
DEFAULT_SERVICE_REFERENCE = "baltor-admin"
DEFAULT_IDENTITY_REFERENCE = "supabase-secret"
DEFAULT_MAIL_REFERENCE = "resend-send"
MANIFEST_RECORD_TYPE = "operator_credential_references/v1"
CAPABILITIES_RECORD_TYPE = "service_capabilities/v1"
SETUP_REPORT_RECORD_TYPE = "stripe_sandbox_setup_report/v1"
SETUP_CONFIRMED_WRITES, SETUP_READY = "confirmed_writes", "ready"
PRESENT_OBJECT_STATES = ("existing", "created")
SERVICE_WAITLIST_PATH = "/api/v1/admin/waitlist"
SERVICE_CAPABILITIES_PATH = "/api/v1/capabilities"
SERVICE_PATHS = (SERVICE_WAITLIST_PATH, SERVICE_CAPABILITIES_PATH)
MAIL_ORIGIN = "https://api.resend.com"
MAIL_PATH = "/emails"
MAIL_SERVICE = "resend"
MAIL_PURPOSE = "transactional-email"
IDENTITY_SERVICE = "supabase"
SECURE_SCHEME = "https"
JSON_MEDIA_TYPE = "application/json"
GET_METHOD, POST_METHOD = "GET", "POST"
OK_STATUS = 200
CREDENTIAL_REFUSED_STATUSES = (401, 403)
WAITING, INVITED, REMOVED = "waiting", "invited", "removed"
INVITE_OPERATION, RECORD_DELIVERY_OPERATION = "invite", "record_delivery"
FORGET_OPERATION = "forget"
DELIVERY_SENT, DELIVERY_UNKNOWN = "sent", "unknown"
EXIT_REFUSED_BEFORE_ANY_REQUEST = 2
MINIMUM_LONG_SECRET_LENGTH = 16
LIMITATIONS = (
    "A sent email is what the mail provider accepted. It is not proof that the message arrived or was read.",
    "The discount code is recorded as sent. Whether checkout applies it is a separate check against the payment account.",
    "The saved payment account report is evidence that the code existed when that report was written, not at this moment.",
    "The report holds no address, no sign-in link and no credential. Read the list to see an address.",
    "An invitation that ends unknown has to be inspected at the mail provider before the operator decides anything.",
    "A removed entry keeps its decision history and the one-way digest of the address. The address and the note are gone.",
)

_HOST_LABEL = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
_HOST_PATTERN = r"(?=[a-z0-9.-]{4,253}\Z)" + _HOST_LABEL + r"(?:\." + _HOST_LABEL + r")+"
_HOSTNAME = re.compile(_HOST_PATTERN)
_ADDRESS = re.compile(r"[a-z0-9_%+-]+(?:\.[a-z0-9_%+-]+)*@" + _HOST_PATTERN)
_ENTRY_REFERENCE = re.compile(r"service:[0-9a-f]{64}")
_DISCOUNT_CODE = re.compile(r"[A-Z0-9]{3,64}")
_MESSAGE_IDENTITY = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}")
_REPORT_OPEN_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
_REPORT_MODE = 0o600


class OperatorOutcome(str, Enum):
    """What the operator may conclude when the command ends."""

    LISTED = "listed"
    INVITED = "invited_and_email_sent"
    FORGOTTEN = "removed_and_erased"
    REFUSED = "refused"
    OUTCOME_UNKNOWN = "outcome_unknown"


class OperatorRefusal(str, Enum):
    """Refused before any request. Nothing was read, recorded or sent."""

    MODE = "choose_exactly_one_of_list_invite_or_forget"
    SERVICE_ORIGIN = "exact_https_service_origin_required"
    ENTRY_REFERENCE = "entry_reference_shape_refused"
    ADDRESS = "invited_address_refused"
    DISCOUNT_CODE = "discount_code_shape_refused"
    DISCOUNT_EVIDENCE = "payment_account_report_does_not_show_this_code_exists"
    SENDER = "sender_address_refused"
    CREDENTIAL_MANIFEST = "credential_manifest_unavailable"
    CREDENTIAL_REFERENCE = "credential_reference_refused"
    CREDENTIAL_VALUE = "credential_missing_or_malformed"
    CONFIRMATION = "explicit_confirmation_required_nothing_was_sent"
    REPORT_FOLDER = "report_folder_must_exist"
    REPORT_EXISTS = "report_path_must_not_exist"
    REPORT_PATH = "report_path_refused"
    SECRET_IN_OUTPUT = "secret_in_output_refused"


class OperatorFailure(str, Enum):
    """Why a run that reached a provider did not end as asked."""

    SERVICE_UNAVAILABLE = "service_did_not_answer_the_waiting_list"
    SERVICE_REFUSED = "service_refused_the_operator_token"
    LISTING_MALFORMED = "waiting_list_answer_was_not_a_listing"
    ENTRY_NOT_WAITING = "entry_is_not_waiting_so_it_was_not_invited"
    DISCOUNT_NOT_ACCEPTED = "checkout_does_not_take_a_discount_code_so_nothing_was_recorded_or_sent"
    DECISION_REFUSED = "service_refused_the_invitation"
    REMOVAL_REFUSED = "service_refused_the_removal"
    REMOVAL_UNKNOWN = "removal_outcome_unknown_do_not_repeat_with_a_new_identity"
    DECISION_UNKNOWN = "invitation_outcome_unknown_do_not_repeat_with_a_new_identity"
    IDENTITY_REFUSED = "identity_provider_did_not_issue_a_sign_in_link"
    MAIL_REFUSED = "mail_provider_refused_the_message"
    MAIL_UNKNOWN = "mail_answer_lost_the_message_may_have_been_sent"
    DELIVERY_NOT_RECORDED = "email_was_sent_but_the_service_did_not_record_it"
    UNEXPECTED_ERROR = "unexpected_error"


REFUSALS = tuple(item.value for item in OperatorRefusal)
FAILURES = tuple(item.value for item in OperatorFailure)
_EXIT_CODES = {OperatorOutcome.LISTED: 0, OperatorOutcome.INVITED: 0, OperatorOutcome.FORGOTTEN: 0,
               OperatorOutcome.REFUSED: 1, OperatorOutcome.OUTCOME_UNKNOWN: 3}


class Refusal(Exception):
    """Refused before any request. It carries a code, never a value."""

    def __init__(self, reason):
        self.code = OperatorRefusal(reason).value
        super().__init__(self.code)


class TransportFailure(Exception):
    """The answer was lost, so an effect may or may not have taken place."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


class _Stop(Exception):
    """Ends a run that reached a provider, with a typed outcome and failure."""

    def __init__(self, outcome, failure, detail=None):
        super().__init__(failure.value)
        self.outcome, self.failure, self.detail = outcome, failure, detail


@dataclass(frozen=True)
class OperatorLimits:
    """Bounds for one request and for reading its answer."""

    timeout_seconds: float = 15.0
    maximum_response_bytes: int = 262_144
    maximum_listed_entries: int = 500

    def __post_init__(self):
        if (type(self.timeout_seconds) not in (int, float) or not 0 < self.timeout_seconds <= 60
                or type(self.maximum_response_bytes) is not int
                or not 1 <= self.maximum_response_bytes <= 4_194_304
                or type(self.maximum_listed_entries) is not int or not 1 <= self.maximum_listed_entries <= 5_000):
            raise Refusal(OperatorRefusal.CREDENTIAL_REFERENCE)


@dataclass(frozen=True)
class ServiceRequest:
    """One bounded request to the exact service origin. Private values stay out of repr."""

    method: str
    url: str
    body: "bytes | None" = field(repr=False, default=None)
    timeout_seconds: float = 15.0
    maximum_response_bytes: int = 262_144
    credential: str = field(repr=False, default="")

    def __post_init__(self):
        parts = urlsplit(self.url)
        # Only two addresses: the waiting list, and the public service profile
        # that says whether checkout takes a discount code. A write reaches the
        # waiting list alone, so a profile read can never become a decision.
        if (self.method not in (GET_METHOD, POST_METHOD) or parts.scheme != SECURE_SCHEME
                or not _HOSTNAME.fullmatch(parts.hostname or "") or parts.path not in SERVICE_PATHS
                or (self.method == POST_METHOD and parts.path != SERVICE_WAITLIST_PATH)
                or parts.query or parts.fragment or parts.username or parts.password):
            raise Refusal(OperatorRefusal.SERVICE_ORIGIN)


@dataclass(frozen=True)
class MailRequest:
    """One bounded request to the exact mail origin. The message body is not repeated in repr."""

    url: str
    body: bytes = field(repr=False)
    timeout_seconds: float = 15.0
    maximum_response_bytes: int = 65_536
    credential: str = field(repr=False, default="")

    def __post_init__(self):
        if self.url != MAIL_ORIGIN + MAIL_PATH:
            raise Refusal(OperatorRefusal.SERVICE_ORIGIN)


@dataclass(frozen=True)
class ProviderResponse:
    """A status and a bounded body. A body can hold a link, so repr omits it."""

    status: int
    body: bytes = field(repr=False)


@dataclass(frozen=True)
class InviteRequest:
    """Validated operator input for one invitation. Nothing here comes from an answer."""

    service_origin: str
    entry_ref: str
    email: str
    discount_code: str
    sender: str
    project_ref: str
    redirect_to: str
    request_id: str

    def __post_init__(self):
        _require_exact_origin(self.service_origin)
        if not _ENTRY_REFERENCE.fullmatch(self.entry_ref):
            raise Refusal(OperatorRefusal.ENTRY_REFERENCE)
        address = (self.email or "").strip().lower()
        if not _ADDRESS.fullmatch(address) or len(address) > 254:
            raise Refusal(OperatorRefusal.ADDRESS)
        object.__setattr__(self, "email", address)
        if not _DISCOUNT_CODE.fullmatch(self.discount_code or ""):
            raise Refusal(OperatorRefusal.DISCOUNT_CODE)
        sender = (self.sender or "").strip()
        if not _ADDRESS.fullmatch(sender.split("<")[-1].rstrip(">").strip().lower()):
            raise Refusal(OperatorRefusal.SENDER)
        if not _MESSAGE_IDENTITY.fullmatch(self.request_id or ""):
            raise Refusal(OperatorRefusal.ENTRY_REFERENCE)

    @property
    def waitlist_url(self):
        return self.service_origin + SERVICE_WAITLIST_PATH

    @property
    def email_digest(self):
        return hashlib.sha256(self.email.encode("utf-8")).hexdigest()

    @property
    def delivery_request_id(self):
        return self.request_id + ".delivery"


@dataclass(frozen=True)
class ForgetRequest:
    """Validated operator input for one removal. It needs no address and no code."""

    service_origin: str
    entry_ref: str
    request_id: str
    email: str = ""
    discount_code: "str | None" = None

    def __post_init__(self):
        _require_exact_origin(self.service_origin)
        if not _ENTRY_REFERENCE.fullmatch(self.entry_ref or ""):
            raise Refusal(OperatorRefusal.ENTRY_REFERENCE)
        if not _MESSAGE_IDENTITY.fullmatch(self.request_id or ""):
            raise Refusal(OperatorRefusal.ENTRY_REFERENCE)

    @property
    def waitlist_url(self):
        return self.service_origin + SERVICE_WAITLIST_PATH

    @property
    def email_digest(self):
        """A removal names no address, so the report has no address digest to hold."""
        return None


@dataclass
class _Progress:
    """What is known so far, so that a stop can still be reported."""

    service_requests: int = 0
    mail_requests: int = 0
    decision_recorded: bool = False
    link_issued: bool = False
    mail_accepted: bool = False
    delivery_recorded: "str | None" = None
    entry_state: "str | None" = None
    message_digest: "str | None" = None
    identity_user_id: "str | None" = None
    sensitive: list = field(default_factory=list)


@dataclass(frozen=True)
class OperatorResult:
    """The typed result of one run. Private values stay out of repr."""

    outcome: OperatorOutcome
    failure: "OperatorFailure | None" = None
    detail: "str | None" = None
    entries: tuple = ()
    entry_state: "str | None" = None
    decision_recorded: bool = False
    link_issued: bool = False
    mail_accepted: bool = False
    delivery_recorded: "str | None" = None
    message_digest: "str | None" = None
    identity_user_id: "str | None" = None
    service_requests: int = 0
    mail_requests: int = 0
    sensitive_values: tuple = field(default=(), repr=False)


# Guards before any request.

def _require_exact_origin(value):
    parts = urlsplit(value or "")
    if (parts.scheme != SECURE_SCHEME or not _HOSTNAME.fullmatch(parts.hostname or "")
            or parts.path or parts.query or parts.fragment or parts.username or parts.password
            or (value or "").endswith("/")):
        raise Refusal(OperatorRefusal.SERVICE_ORIGIN)
    return urlunsplit((SECURE_SCHEME, parts.netloc, "", "", ""))


def read_discount_evidence(path, code):
    """Read the saved payment account report that says this exact code exists.

    An invitation promises a discount, so the promise needs evidence from the
    account that would honour it. The report `tools/setup_stripe_sandbox.py`
    writes names the promotion code it found or created. A dry run, another
    code, a missing object or any other record refuses before any request.
    This command holds no payment credential and reads no payment account.
    """
    try:
        report = json.loads(Path(path or "").read_text(encoding="utf-8"))
    except Exception:
        raise Refusal(OperatorRefusal.DISCOUNT_EVIDENCE) from None
    promotion = report.get("promotion_code") if isinstance(report, dict) else None
    identity = promotion.get("id") if isinstance(promotion, dict) else None
    if (not isinstance(report, dict) or report.get("record_type") != SETUP_REPORT_RECORD_TYPE
            or report.get("mode") != SETUP_CONFIRMED_WRITES or report.get("outcome") != SETUP_READY
            or not isinstance(promotion, dict) or promotion.get("code") != code
            or promotion.get("state") not in PRESENT_OBJECT_STATES
            or not isinstance(identity, str) or not identity):
        raise Refusal(OperatorRefusal.DISCOUNT_EVIDENCE)
    return {"report": str(path), "promotion_code_id": identity, "state": promotion["state"],
            "payment_account_id": report.get("account_id"), "observed_at": report.get("observed_at")}


def load_manifest():
    try:
        manifest = operator_credentials.references()
    except Exception:
        raise Refusal(OperatorRefusal.CREDENTIAL_MANIFEST) from None
    if not isinstance(manifest, dict) or manifest.get("record_type") != MANIFEST_RECORD_TYPE:
        raise Refusal(OperatorRefusal.CREDENTIAL_MANIFEST)
    return manifest


def credential_environment(reference, manifest, *, service=None, purpose=None):
    """Name the environment variable a reference arrives in, and check what it is for."""
    entry = (manifest.get("api_keys") or {}).get(reference)
    if not isinstance(entry, dict):
        raise Refusal(OperatorRefusal.CREDENTIAL_REFERENCE)
    if (service is not None and entry.get("service") != service) or (
            purpose is not None and entry.get("purpose") != purpose):
        raise Refusal(OperatorRefusal.CREDENTIAL_REFERENCE)
    name = entry.get("environment")
    if not isinstance(name, str) or not name:
        raise Refusal(OperatorRefusal.CREDENTIAL_REFERENCE)
    return name


def resolve_credential(name, environment):
    value = (environment or {}).get(name)
    if not isinstance(value, str) or len(value) < MINIMUM_LONG_SECRET_LENGTH or value.strip() != value:
        raise Refusal(OperatorRefusal.CREDENTIAL_VALUE)
    return value


def reserve_report(value):
    """Open a new report file, so that a run never overwrites earlier evidence."""
    target = Path(value or "")
    if not target.name or target.is_symlink():
        raise Refusal(OperatorRefusal.REPORT_PATH)
    if not target.parent.is_dir():
        raise Refusal(OperatorRefusal.REPORT_FOLDER)
    try:
        handle = os.open(target, _REPORT_OPEN_FLAGS, _REPORT_MODE)
    except FileExistsError:
        raise Refusal(OperatorRefusal.REPORT_EXISTS) from None
    except OSError:
        raise Refusal(OperatorRefusal.REPORT_PATH) from None
    return target, os.fdopen(handle, "w", encoding="utf-8")


# Transport.

def send_service_request(request):
    """One bounded HTTPS request to the service. Redirects are refused, not followed."""
    return _send(request.method, request.url, request.body, request.credential,
                 request.timeout_seconds, request.maximum_response_bytes)


def send_mail_request(request):
    """One bounded HTTPS request to the mail provider. Redirects are refused, not followed."""
    return _send(POST_METHOD, request.url, request.body, request.credential,
                 request.timeout_seconds, request.maximum_response_bytes)


def _send(method, url, body, credential, timeout_seconds, maximum_response_bytes):
    import httpx
    headers = {"Authorization": "Bearer " + credential, "Accept": JSON_MEDIA_TYPE}
    if body is not None:
        headers["Content-Type"] = JSON_MEDIA_TYPE
    try:
        with httpx.Client(follow_redirects=False, trust_env=False, timeout=timeout_seconds) as client:
            with client.stream(method, url, headers=headers, content=body) as response:
                chunks, size = [], 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > maximum_response_bytes:
                        raise TransportFailure("response_too_large")
                    chunks.append(chunk)
                return ProviderResponse(response.status_code, b"".join(chunks))
    except TransportFailure:
        raise
    except Exception as error:
        raise TransportFailure("timeout" if "Timeout" in type(error).__name__ else "connection_failed") from None


def _json_object(body):
    try:
        value = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeError):
        raise ValueError("answer was not JSON") from None
    if not isinstance(value, dict):
        raise ValueError("answer was not an object")
    return value


def _result_of(response, lost):
    if response.status in CREDENTIAL_REFUSED_STATUSES:
        raise _Stop(OperatorOutcome.REFUSED, OperatorFailure.SERVICE_REFUSED)
    if response.status != OK_STATUS:
        raise _Stop(*lost, "status_" + str(response.status))
    try:
        value = _json_object(response.body)
    except ValueError:
        raise _Stop(*lost, "malformed_answer") from None
    result = value.get("result")
    if not isinstance(result, dict):
        raise _Stop(*lost, "malformed_answer")
    return result


# The two operations.

def read_waiting_list(origin, credential, limits, transport, progress):
    """Read the list. This performs no write and sends no email."""
    request = ServiceRequest(GET_METHOD, origin + SERVICE_WAITLIST_PATH, None,
                             limits.timeout_seconds, limits.maximum_response_bytes, credential)
    progress.service_requests += 1
    try:
        response = transport(request)
    except TransportFailure as failure:
        raise _Stop(OperatorOutcome.REFUSED, OperatorFailure.SERVICE_UNAVAILABLE, failure.code) from None
    listing = _result_of(response, (OperatorOutcome.REFUSED, OperatorFailure.SERVICE_UNAVAILABLE))
    entries = listing.get("entries")
    if listing.get("record_type") != LISTING_RECORD_TYPE or not isinstance(entries, list):
        raise _Stop(OperatorOutcome.REFUSED, OperatorFailure.LISTING_MALFORMED)
    if len(entries) > limits.maximum_listed_entries:
        raise _Stop(OperatorOutcome.REFUSED, OperatorFailure.LISTING_MALFORMED, "listing_too_long")
    return listing


def require_checkout_takes_a_code(origin, credential, limits, transport, progress):
    """Refuse the invitation unless checkout shows a place to type the code.

    The invitation tells a person to enter a code at checkout. A checkout
    session that was not created with discount codes enabled has no field for
    it, so the promise would fail at the first paid step. The service
    publishes that fact in its own profile record; this reads it and stops
    before the invitation is recorded and before any message is prepared.
    """
    request = ServiceRequest(GET_METHOD, origin + SERVICE_CAPABILITIES_PATH, None,
                             limits.timeout_seconds, limits.maximum_response_bytes, credential)
    progress.service_requests += 1
    try:
        response = transport(request)
    except TransportFailure as failure:
        raise _Stop(OperatorOutcome.REFUSED, OperatorFailure.SERVICE_UNAVAILABLE, failure.code) from None
    profile = _result_of(response, (OperatorOutcome.REFUSED, OperatorFailure.SERVICE_UNAVAILABLE))
    billing = profile.get("billing")
    if profile.get("record_type") != CAPABILITIES_RECORD_TYPE or not isinstance(billing, dict):
        raise _Stop(OperatorOutcome.REFUSED, OperatorFailure.SERVICE_UNAVAILABLE, "malformed_answer")
    if billing.get("discount_code") is not True:
        raise _Stop(OperatorOutcome.REFUSED, OperatorFailure.DISCOUNT_NOT_ACCEPTED)
    return True


def _decide(request, credential, limits, transport, progress, fields, lost):
    """Send one decision. A lost answer is unknown, and this command never repeats it."""
    body = json.dumps({"record_type": DECISION_RECORD_TYPE, **fields}, sort_keys=True).encode("utf-8")
    wire = ServiceRequest(POST_METHOD, request.waitlist_url, body,
                          limits.timeout_seconds, limits.maximum_response_bytes, credential)
    progress.service_requests += 1
    try:
        response = transport(wire)
    except TransportFailure as failure:
        raise _Stop(OperatorOutcome.OUTCOME_UNKNOWN, lost, failure.code) from None
    result = _result_of(response, (OperatorOutcome.OUTCOME_UNKNOWN, lost))
    if result.get("record_type") != RESULT_RECORD_TYPE or result.get("committed") is not True:
        raise _Stop(OperatorOutcome.OUTCOME_UNKNOWN, lost, "unconfirmed_answer")
    return result


def _message(request, link):
    """The invitation. It names the discount code and carries the sign-in link once."""
    lines = (
        "You asked for an invitation to Baltor.",
        "",
        "Baltor gives every step of a task the information, tools and reusable code",
        "that the step needs, under your own budget and permissions.",
        "",
        "Set your password with this link. It works once:",
        link,
        "",
        "Your invitation carries a discount. Enter this code at checkout:",
        request.discount_code,
        "",
        "If you did not ask for this, ignore this message and nothing happens.",
    )
    return {"from": request.sender, "to": [request.email],
            "subject": "Your Baltor invitation", "text": "\n".join(lines)}


def send_invitation_email(request, credential, limits, transport, progress, link):
    """Send one message. There is no automatic repeat, at any stage, for any reason."""
    wire = MailRequest(MAIL_ORIGIN + MAIL_PATH, json.dumps(_message(request, link)).encode("utf-8"),
                       limits.timeout_seconds, 65_536, credential)
    progress.mail_requests += 1
    try:
        response = transport(wire)
    except TransportFailure as failure:
        # The request left this machine. Whether the provider accepted it is
        # unknown, so the invitation is recorded as unknown and not repeated.
        raise _Stop(OperatorOutcome.OUTCOME_UNKNOWN, OperatorFailure.MAIL_UNKNOWN, failure.code) from None
    if response.status in CREDENTIAL_REFUSED_STATUSES or response.status not in (200, 201, 202):
        raise _Stop(OperatorOutcome.REFUSED, OperatorFailure.MAIL_REFUSED, "status_" + str(response.status))
    try:
        accepted = _json_object(response.body)
    except ValueError:
        raise _Stop(OperatorOutcome.OUTCOME_UNKNOWN, OperatorFailure.MAIL_UNKNOWN, "malformed_answer") from None
    identity = accepted.get("id")
    if not isinstance(identity, str) or not _MESSAGE_IDENTITY.fullmatch(identity):
        raise _Stop(OperatorOutcome.OUTCOME_UNKNOWN, OperatorFailure.MAIL_UNKNOWN, "no_message_identity")
    progress.mail_accepted = True
    progress.message_digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    return progress.message_digest


def invite_one_entry(request, credentials, limits, *, service_transport, mail_transport,
                     identity_transport=None, now=None):
    """Record the invitation, prepare the account, send the email, record the delivery."""
    progress = _Progress(sensitive=[credentials.service, credentials.identity, credentials.mail])
    outcome, failure, detail = OperatorOutcome.INVITED, None, None
    try:
        require_checkout_takes_a_code(request.service_origin, credentials.service, limits,
                                      service_transport, progress)
        recorded = _decide(request, credentials.service, limits, service_transport, progress,
                           {"operation": INVITE_OPERATION, "entry_ref": request.entry_ref,
                            "request_id": request.request_id, "discount_code": request.discount_code},
                           OperatorFailure.DECISION_UNKNOWN)
        entry = recorded.get("entry") if isinstance(recorded.get("entry"), dict) else {}
        progress.entry_state = recorded.get("state")
        if recorded.get("state") != INVITED:
            raise _Stop(OperatorOutcome.REFUSED, OperatorFailure.ENTRY_NOT_WAITING)
        if entry.get("email") != request.email:
            raise _Stop(OperatorOutcome.REFUSED, OperatorFailure.DECISION_REFUSED, "address_does_not_match_the_entry")
        progress.decision_recorded = True

        identity = invite_beta_user.issue_invitation(
            invite_beta_user.InvitationRequest(request.project_ref, request.email,
                                               request.service_origin, request.redirect_to),
            credentials.identity,
            invite_beta_user._select_transport(identity_transport),
            invite_beta_user.AdministrationLimits(),
            now or _utc_now)
        progress.sensitive.extend(value for value in identity.sensitive_values if isinstance(value, str))
        progress.identity_user_id = identity.user_id
        if identity.outcome is not invite_beta_user.InvitationOutcome.LINK_ISSUED or not identity.link:
            raise _Stop(OperatorOutcome.REFUSED if identity.outcome is invite_beta_user.InvitationOutcome.REFUSED
                        else OperatorOutcome.OUTCOME_UNKNOWN, OperatorFailure.IDENTITY_REFUSED,
                        identity.failure.value if identity.failure is not None else None)
        progress.link_issued = True

        digest = send_invitation_email(request, credentials.mail, limits, mail_transport, progress, identity.link)
        _record_delivery(request, credentials.service, limits, service_transport, progress, DELIVERY_SENT, digest)
    except _Stop as stop:
        outcome, failure, detail = stop.outcome, stop.failure, stop.detail
        if progress.mail_accepted and progress.delivery_recorded is None:
            failure = OperatorFailure.DELIVERY_NOT_RECORDED
        if stop.failure is OperatorFailure.MAIL_UNKNOWN and progress.decision_recorded:
            _record_unknown_delivery(request, credentials.service, limits, service_transport, progress)
    except Exception as error:
        outcome = OperatorOutcome.OUTCOME_UNKNOWN
        failure, detail = OperatorFailure.UNEXPECTED_ERROR, type(error).__name__
    return OperatorResult(outcome, failure, detail, (), progress.entry_state, progress.decision_recorded,
                          progress.link_issued, progress.mail_accepted, progress.delivery_recorded,
                          progress.message_digest, progress.identity_user_id, progress.service_requests,
                          progress.mail_requests, tuple(progress.sensitive))


def forget_one_entry(request, credentials, limits, *, service_transport):
    """Erase one entry's address and note. Nothing outside the service is touched.

    The service replaces the address and the note and moves the entry to the
    removed state. This command confirms that the answer shows both gone. A
    lost answer is unknown: the same request identity may be sent again, and
    the service replays its first decision instead of writing twice.
    """
    progress = _Progress(sensitive=[credentials.service])
    outcome, failure, detail = OperatorOutcome.FORGOTTEN, None, None
    try:
        result = _decide(request, credentials.service, limits, service_transport, progress,
                         {"operation": FORGET_OPERATION, "entry_ref": request.entry_ref,
                          "request_id": request.request_id}, OperatorFailure.REMOVAL_UNKNOWN)
        entry = result.get("entry") if isinstance(result.get("entry"), dict) else {}
        progress.entry_state = result.get("state")
        if result.get("state") != REMOVED or entry.get("email") or entry.get("note"):
            raise _Stop(OperatorOutcome.REFUSED, OperatorFailure.REMOVAL_REFUSED)
        progress.decision_recorded = True
    except _Stop as stop:
        outcome, failure, detail = stop.outcome, stop.failure, stop.detail
    except Exception as error:
        outcome = OperatorOutcome.OUTCOME_UNKNOWN
        failure, detail = OperatorFailure.UNEXPECTED_ERROR, type(error).__name__
    return OperatorResult(outcome, failure, detail, (), progress.entry_state, progress.decision_recorded,
                          service_requests=progress.service_requests,
                          sensitive_values=tuple(progress.sensitive))


def _record_delivery(request, credential, limits, transport, progress, delivery, message_digest):
    result = _decide(request, credential, limits, transport, progress,
                     {"operation": RECORD_DELIVERY_OPERATION, "entry_ref": request.entry_ref,
                      "request_id": request.delivery_request_id, "delivery": delivery,
                      "invitation_ref": message_digest or ""},
                     OperatorFailure.DELIVERY_NOT_RECORDED)
    progress.delivery_recorded = delivery
    progress.entry_state = result.get("state")


def _record_unknown_delivery(request, credential, limits, transport, progress):
    """A lost mail answer is recorded as unknown. A failure here changes nothing outside."""
    try:
        _record_delivery(request, credential, limits, transport, progress, DELIVERY_UNKNOWN, None)
    except _Stop:
        progress.delivery_recorded = None


# Output.

def _utc_now():
    return datetime.now(timezone.utc)


def listing_lines(listing):
    """One readable line for each entry. The operator reads addresses here, not in the report."""
    lines = []
    for entry in listing.get("entries", []):
        note = (entry.get("note") or "").replace("\n", " ")
        lines.append("\t".join((entry.get("entry_ref", ""), entry.get("state", ""),
                                entry.get("email", ""), note[:120])))
    return lines


def build_report(result, mode, observed_at, request=None, listing=None, discount_evidence=None):
    counts = (listing or {}).get("counts") if isinstance(listing, dict) else None
    return {
        "record_type": REPORT_RECORD_TYPE,
        "observed_at": observed_at.isoformat(timespec="seconds"),
        "mode": mode,
        "service_origin": request.service_origin if request is not None else None,
        "entry_ref": request.entry_ref if request is not None else None,
        "invited_address_digest": request.email_digest if request is not None else None,
        "discount_code": request.discount_code if request is not None else None,
        "discount_evidence": discount_evidence,
        "entry_state": result.entry_state,
        "waiting_list_counts": counts if isinstance(counts, dict) else None,
        "listed_entries": len(listing.get("entries", [])) if isinstance(listing, dict) else 0,
        "invitation_recorded": result.decision_recorded,
        "sign_in_link_issued": result.link_issued,
        "sign_in_link_recorded": False,
        "email_accepted_by_provider": result.mail_accepted,
        "email_message_digest": result.message_digest,
        "delivery_recorded": result.delivery_recorded,
        "identity_user_id": result.identity_user_id,
        "service_requests": result.service_requests,
        "mail_requests": result.mail_requests,
        "automatic_retries": 0,
        "outcome": result.outcome.value,
        "failure": result.failure.value if result.failure is not None else None,
        "detail": result.detail,
        "limitations": list(LIMITATIONS),
    }


def _require_no_secret(text, sensitive_values):
    if any(isinstance(value, str) and len(value) >= MINIMUM_LONG_SECRET_LENGTH and value in text
           for value in sensitive_values):
        raise Refusal(OperatorRefusal.SECRET_IN_OUTPUT)


def encode_report(report, sensitive_values):
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    _require_no_secret(encoded, sensitive_values)
    return encoded


@dataclass(frozen=True)
class Credentials:
    """The three values this command uses. They are never written anywhere."""

    service: str = field(repr=False, default="")
    identity: str = field(repr=False, default="")
    mail: str = field(repr=False, default="")


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], allow_abbrev=False)
    parser.add_argument("--service-origin", required=True, help="exact HTTPS origin of the service, without a path")
    parser.add_argument("--report", required=True, help="new report file in an existing folder")
    parser.add_argument("--list", action="store_true", help="read the waiting list and print it")
    parser.add_argument("--invite", default="", help="entry reference to invite, as the listing prints it")
    parser.add_argument("--forget", default="", help="entry reference whose address and note are erased")
    parser.add_argument("--email", default="", help="address of that entry, which must match what the service holds")
    parser.add_argument("--discount-code", default="", help="promotion code the payment account already holds")
    parser.add_argument("--discount-evidence", default="",
                        help="report from tools/setup_stripe_sandbox.py that names that code as present")
    parser.add_argument("--sender", default="", help="from address of the invitation, on a verified sending domain")
    parser.add_argument("--project-ref", default="", help="identity project reference, twenty lower case letters")
    parser.add_argument("--redirect-to", default="", help="return address inside the service origin")
    parser.add_argument("--service-ref", default=DEFAULT_SERVICE_REFERENCE, help="operator token reference")
    parser.add_argument("--identity-ref", default=DEFAULT_IDENTITY_REFERENCE, help="identity administration reference")
    parser.add_argument("--mail-ref", default=DEFAULT_MAIL_REFERENCE, help="mail sending credential reference")
    parser.add_argument("--acknowledge-invitation-effects", action="store_true",
                        help="confirm that an account may be prepared and that one email will be sent")
    parser.add_argument("--acknowledge-erasure", action="store_true",
                        help="confirm that the address and the note are erased and cannot be recovered")
    return parser


def main(argv=None, *, environment=None, manifest=None, service_transport=None, mail_transport=None,
         identity_transport=None, now=None):
    arguments = build_parser().parse_args(argv)
    current = _utc_now if now is None else now
    values = os.environ if environment is None else environment
    try:
        if sum((bool(arguments.list), bool(arguments.invite), bool(arguments.forget))) != 1:
            raise Refusal(OperatorRefusal.MODE)
        origin = _require_exact_origin(arguments.service_origin)
        held = load_manifest() if manifest is None else manifest
        limits = OperatorLimits()
        service = resolve_credential(credential_environment(arguments.service_ref, held), values)
        request, evidence = None, None
        if arguments.invite:
            if not arguments.acknowledge_invitation_effects:
                raise Refusal(OperatorRefusal.CONFIRMATION)
            request = InviteRequest(origin, arguments.invite, arguments.email, arguments.discount_code,
                                    arguments.sender, arguments.project_ref, arguments.redirect_to,
                                    uuid.uuid4().hex)
            evidence = read_discount_evidence(arguments.discount_evidence, request.discount_code)
            identity = resolve_credential(credential_environment(
                arguments.identity_ref, held, service=IDENTITY_SERVICE), values)
            mail = resolve_credential(credential_environment(
                arguments.mail_ref, held, service=MAIL_SERVICE, purpose=MAIL_PURPOSE), values)
        else:
            identity = mail = ""
            if arguments.forget:
                if not arguments.acknowledge_erasure:
                    raise Refusal(OperatorRefusal.CONFIRMATION)
                request = ForgetRequest(origin, arguments.forget, uuid.uuid4().hex)
        target, stream = reserve_report(arguments.report)
    except Refusal as refusal:
        sys.stderr.write(refusal.code + "\n")
        return EXIT_REFUSED_BEFORE_ANY_REQUEST
    credentials = Credentials(service, identity, mail)
    try:
        return _run(arguments, request, credentials, limits, origin, current, target, stream,
                    service_transport or send_service_request, mail_transport or send_mail_request,
                    identity_transport, evidence)
    except Exception as error:
        sys.stderr.write(OperatorFailure.UNEXPECTED_ERROR.value + ":" + type(error).__name__ + "\n")
        return _EXIT_CODES[OperatorOutcome.OUTCOME_UNKNOWN]


def _run(arguments, request, credentials, limits, origin, current, target, stream,
         service_transport, mail_transport, identity_transport, discount_evidence=None):
    """Everything after the report file exists: requests, then the report, then the lines."""
    listing, lines = None, []
    with stream:
        if isinstance(request, ForgetRequest):
            result = forget_one_entry(request, credentials, limits, service_transport=service_transport)
        elif request is None:
            progress = _Progress(sensitive=[credentials.service])
            try:
                listing = read_waiting_list(origin, credentials.service, limits, service_transport, progress)
                result = OperatorResult(OperatorOutcome.LISTED, service_requests=progress.service_requests,
                                        sensitive_values=tuple(progress.sensitive))
                lines = listing_lines(listing)
            except _Stop as stop:
                result = OperatorResult(stop.outcome, stop.failure, stop.detail,
                                        service_requests=progress.service_requests,
                                        sensitive_values=tuple(progress.sensitive))
        else:
            result = invite_one_entry(request, credentials, limits, service_transport=service_transport,
                                      mail_transport=mail_transport, identity_transport=identity_transport,
                                      now=current)
        mode = "forget" if isinstance(request, ForgetRequest) else "invite" if request is not None else "list"
        report = build_report(result, mode, current(), request, listing, discount_evidence)
        try:
            stream.write(encode_report(report, result.sensitive_values))
        except Refusal as refusal:
            sys.stderr.write(refusal.code + "\n")
            return EXIT_REFUSED_BEFORE_ANY_REQUEST
    for line in lines:
        sys.stdout.write(line + "\n")
    summary = {"outcome": result.outcome.value, "failure": report["failure"], "detail": report["detail"],
               "report": str(target), "listed_entries": report["listed_entries"], "mode": mode,
               "invitation_recorded": result.decision_recorded, "email_accepted_by_provider": result.mail_accepted,
               "delivery_recorded": result.delivery_recorded, "entry_state": result.entry_state}
    sys.stdout.write(json.dumps(summary, sort_keys=True) + "\n")
    return _EXIT_CODES[result.outcome]


if __name__ == "__main__":
    raise SystemExit(main())
