"""Prepare the Stripe test environment for Baltor with one repeatable command.

The command finds or creates four things in the Stripe test environment: the
product Baltor Pro, one recurring monthly price with a stable lookup key, one
billing portal configuration that allows cancelling and updating the payment
method, and one webhook endpoint for the given HTTPS address. The endpoint is
subscribed to exactly the event types that the service processes.

The API key arrives in the environment variable that
tools/operator_credentials.json names for the selected reference. Run this
command through tools/operator_credentials.py with the system Python, so that
the value never appears in an argument, a file or the terminal. A key that is
not a test key is refused before any request. Every object that Stripe
returns must also state that it is not in live mode.

This command imports nothing from loop_engine on purpose. It is an operator
command, so its provider origin, its paths and the environment names it
reports are fixed here and checked here. A change inside the service must not
be able to move where an operator sends the account's secret key.

Every read comes before the first write. Nothing is written without the
confirmation flag. A dry run only reads. Every write carries its own
idempotency key and is never repeated by this command. When a write may have
reached Stripe and its answer is lost or unusable, the outcome is reported as
unknown. Inspect the Stripe test dashboard before running the command again.

A run that stops before Stripe performed any write and a run that stops after
Stripe performed one are different outcomes with different exit codes. The
report counts both the writes that were sent and the writes that Stripe
answered with a success, so the operator can tell what now exists in the
account without guessing.

Stripe returns the signing secret of a webhook endpoint only when the
endpoint is created. The command stores that secret straight into the system
keyring under a named reference and never prints it. When the endpoint
already exists and the keyring does not hold its secret, the command stops.
It does not create a second endpoint for the same address. When a run creates
the endpoint and then cannot keep its secret, that secret is gone for good:
delete the new endpoint in the Stripe test dashboard and run the command
again. The report names the endpoint that has to be removed.

The report holds identifiers only. It is written to a path that must not
exist, so that a run never overwrites earlier evidence.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
import math
import os
from pathlib import Path
import re
import secrets
import sys
import time
from urllib.parse import urlencode, urlsplit, urlunsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import operator_credentials  # noqa: E402

REPORT_RECORD_TYPE = "stripe_sandbox_setup_report/v1"
PLAN_RECORD_TYPE = "stripe_sandbox_plan/v1"
MANIFEST_RECORD_TYPE = "operator_credential_references/v1"
HOST_BILLING_RECORD_NOTE = "service_http_host_configuration/v1 billing block"
DEFAULT_CREDENTIAL_REFERENCE = "stripe-test"
DEFAULT_WEBHOOK_SECRET_REFERENCE = "stripe-test-webhook-secret"
DEFAULT_WEBHOOK_URL = "https://app.baltor.ai/api/v1/billing/webhook"
PAYMENT_SERVICE = "stripe"
STRIPE_ORIGIN = "https://api.stripe.com"
SECURE_SCHEME = "https"
TEST_KEY_PREFIXES = ("sk_test_", "rk_test_")
WEBHOOK_SECRET_PREFIX = "whsec_"
# Stripe documents the prefix of a webhook signing secret and nothing else
# about its shape. "Receive Stripe events in your webhook endpoint" says "a
# signing secret beginning with whsec_ appears", and the create reference for
# /v1/webhook_endpoints shows the example value
# "whsec_wRNftLajMZNeslQOP6vEPm4iVx5NlZ6z". Neither page publishes the
# character set or the length, so this pattern accepts the base64 and
# base64url alphabets, which is wider than every published example. The same
# pattern is written into the keyring reference entry as value_pattern, and
# operator_credentials.store_api_reference validates the value against that
# entry before saving it, so the local check and the keyring apply one rule
# rather than two. Widen this pattern, not the store, if Stripe ever issues a
# secret outside it. Read docs/guides/billing-setup-and-pricing.md for what to
# do when a created endpoint's secret cannot be kept.
WEBHOOK_SECRET_VALUE_PATTERN = WEBHOOK_SECRET_PREFIX + r"[A-Za-z0-9+/=_-]{16,256}"
# tools/stage_service_secrets.py stages a saved credential only when its
# purpose is one of its runtime purposes, and "webhook-signing" is one of
# them. The exact endpoint address is recorded in the reference entry instead,
# because the keyring item is found by service, account and purpose alone.
WEBHOOK_SECRET_PURPOSE = "webhook-signing"
KEYRING_APPLICATION = "loop-engine"
KEYRING_LABEL_PREFIX = "Baltor operator / "
SERVICE_WEBHOOK_SECRET_ENVIRONMENT = "STRIPE_WEBHOOK_SECRET"
SERVICE_WEBHOOK_SECRET_REFERENCE = "env:" + SERVICE_WEBHOOK_SECRET_ENVIRONMENT
ENVIRONMENT_REFERENCE_PREFIX = "env:"
# The subscription reader of the service reads the period end on each
# subscription item, not on the subscription. Stripe moved that field onto the
# item in the release named after this date, so an older version cannot serve
# the reader.
EARLIEST_SUPPORTED_API_VERSION = "2025-03-31"
# The event types that the service processes. A check compares this tuple with
# loop_engine.core.service_runtime.billing_records.EVENT_TYPES.
SERVICE_EVENT_TYPES = ("customer.subscription.created", "customer.subscription.updated",
                       "customer.subscription.deleted", "invoice.paid", "invoice.payment_failed")

ACCOUNT_PATH = "/v1/account"
PRODUCTS_PATH = "/v1/products"
PRICES_PATH = "/v1/prices"
PORTAL_CONFIGURATIONS_PATH = "/v1/billing_portal/configurations"
WEBHOOK_ENDPOINTS_PATH = "/v1/webhook_endpoints"
COUPONS_PATH = "/v1/coupons"
PROMOTION_CODES_PATH = "/v1/promotion_codes"
GET_METHOD, POST_METHOD = "GET", "POST"
WRITE_PATHS = (PRODUCTS_PATH, PRICES_PATH, PORTAL_CONFIGURATIONS_PATH, WEBHOOK_ENDPOINTS_PATH,
               COUPONS_PATH, PROMOTION_CODES_PATH)
LIST_PATHS = (PRICES_PATH, PORTAL_CONFIGURATIONS_PATH, WEBHOOK_ENDPOINTS_PATH, PROMOTION_CODES_PATH)
ACCOUNT_OBJECT, PRODUCT_OBJECT, PRICE_OBJECT = "account", "product", "price"
PORTAL_OBJECT, ENDPOINT_OBJECT, LIST_OBJECT = "billing_portal.configuration", "webhook_endpoint", "list"
COUPON_OBJECT, PROMOTION_CODE_OBJECT = "coupon", "promotion_code"
COUPON_DURATIONS = ("once", "forever")
RECURRING_PRICE = "recurring"
ENDPOINT_ENABLED = "enabled"
CANCEL_AT_PERIOD_END = "at_period_end"
FORM_TRUE = "true"
FORM_MEDIA_TYPE = "application/x-www-form-urlencoded"
JSON_MEDIA_TYPE = "application/json"
OK_STATUS = 200
NOT_FOUND_STATUS = 404
CREDENTIAL_REFUSED_STATUSES = (401, 403)
# Stripe documents that these answers mean the write was not performed.
WRITE_NOT_PERFORMED_STATUSES = (400, 401, 402, 403, 404, 429)
PAGE_SIZE = 100
LOOKUP_PAGE_SIZE = 10
IDEMPOTENCY_KEY_PREFIX = "baltor-sandbox-setup-"
MINIMUM_LONG_SECRET_LENGTH = 16
EXIT_REFUSED_BEFORE_ANY_REQUEST = 2
LIMITATIONS = (
    "These checks cover the Stripe test environment only. A live account needs the owner's identity and bank verification.",
    "The report does not show that a checkout, a portal visit or a webhook delivery works. Run those journeys separately.",
    "The signing secret is in the workstation keyring only. The running service does not hold it until an operator sets it.",
    "A live portal configuration also needs a business profile with a privacy policy address and a terms of service address.",
    "One Stripe account holds one signing secret for the service. A second endpoint address needs the first one removed first.",
    "A run that created the endpoint and could not keep its signing secret leaves an endpoint to delete at Stripe before the next run.",
    "The report shows that the coupon and its promotion code exist. It does not show a checkout that applied the discount.",
)

_HOST_LABEL = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
_HOSTNAME = re.compile(r"(?=[a-z0-9.-]{4,253}\Z)" + _HOST_LABEL + r"(?:\." + _HOST_LABEL + r")+")
_URL_PATH = re.compile(r"(?:/[A-Za-z0-9._~-]+)+")
_DOT_SEGMENTS = (".", "..")
_TEST_KEY = re.compile(r"(?:sk|rk)_test_[A-Za-z0-9]{16,256}")
_WEBHOOK_SECRET = re.compile(WEBHOOK_SECRET_VALUE_PATTERN)
_ACCOUNT_IDENTITY = re.compile(r"acct_[A-Za-z0-9]{8,64}")
_OBJECT_IDENTITY = re.compile(r"[A-Za-z0-9_]{3,128}")
_API_VERSION = re.compile(r"(\d{4}-\d{2}-\d{2})(?:\.[a-z]{2,32})?")
_REFERENCE_NAME = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?")
_ENVIRONMENT_NAME = re.compile(r"[A-Z][A-Z0-9_]{1,63}")
_PRODUCT_READ_PATH = re.compile(re.escape(PRODUCTS_PATH) + r"/[A-Za-z0-9_]{3,128}")
_COUPON_READ_PATH = re.compile(re.escape(COUPONS_PATH) + r"/[A-Za-z0-9_]{3,128}")
# Stripe's promotion code reference documents the customer-facing code as
# upper and lower case letters and digits. It does not publish a rule for a
# separator, so this command creates a code without one. A code an operator
# made by hand in the dashboard is not created or changed here.
_PROMOTION_CODE = re.compile(r"[A-Z0-9]{3,64}")
_REPORT_OPEN_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
_REPORT_MODE = 0o600


class SetupOutcome(str, Enum):
    """What the operator may conclude when the command ends.

    STOPPED and STOPPED_AFTER_WRITES are separate on purpose. STOPPED means
    that Stripe performed no write in this run, so the account is as it was.
    STOPPED_AFTER_WRITES means that Stripe answered at least one write with a
    success before the run stopped, so objects now exist that the report
    names. The two have different exit codes.
    """

    READY = "ready"
    DRY_RUN = "dry_run_nothing_written"
    STOPPED = "stopped"
    STOPPED_AFTER_WRITES = "stopped_after_a_committed_write"
    OUTCOME_UNKNOWN = "outcome_unknown"


class SetupRefusal(str, Enum):
    """Refusals before any provider request. Nothing was read, written or reported."""

    MODE = "choose_exactly_one_of_dry_run_or_confirmed_writes"
    WEBHOOK_URL = "webhook_address_must_be_a_plain_https_address"
    API_VERSION = "api_version_shape_refused"
    API_VERSION_TOO_OLD = "api_version_is_older_than_the_subscription_reader_supports"
    CREDENTIAL_MANIFEST = "credential_manifest_unavailable"
    CREDENTIAL_REFERENCE = "credential_reference_is_not_a_stripe_test_key"
    LIVE_KEY = "only_a_stripe_test_key_is_accepted"
    SECRET_REFERENCE = "webhook_secret_reference_refused"
    KEYRING = "workstation_keyring_unavailable"
    KEYRING_AMBIGUOUS = "another_saved_secret_already_holds_this_keyring_place"
    REPORT_FOLDER = "report_folder_must_exist"
    REPORT_EXISTS = "report_path_must_not_exist"
    REPORT_PATH = "report_path_refused"
    LIMITS = "invalid_request_limits"
    PLAN = "unsupported_sandbox_plan"
    SECRET_IN_OUTPUT = "secret_in_output_refused"


class SetupFailure(str, Enum):
    """Why a run that reached Stripe did not end ready."""

    READ_FAILED = "read_failed_nothing_was_written_by_this_request"
    CREDENTIAL_REFUSED = "credential_refused_by_provider"
    PROVIDER_REDIRECT = "provider_redirect_refused"
    ACCOUNT_MISMATCH = "key_belongs_to_another_account"
    LIVE_MODE_OBJECT = "provider_object_is_in_live_mode"
    PRODUCT_MISMATCH = "existing_product_differs_from_the_plan"
    PRICE_MISMATCH = "existing_price_differs_from_the_plan"
    PRICE_AMBIGUOUS = "more_than_one_price_holds_the_lookup_key"
    PORTAL_MISMATCH = "existing_portal_configuration_differs_from_the_plan"
    PORTAL_AMBIGUOUS = "more_than_one_portal_configuration_holds_the_marker"
    ENDPOINT_MISMATCH = "existing_webhook_endpoint_differs_from_the_plan"
    ENDPOINT_AMBIGUOUS = "more_than_one_webhook_endpoint_has_this_address"
    COUPON_MISMATCH = "existing_coupon_differs_from_the_plan"
    PROMOTION_CODE_MISMATCH = "existing_promotion_code_differs_from_the_plan"
    PROMOTION_CODE_AMBIGUOUS = "more_than_one_promotion_code_holds_this_code"
    ENDPOINT_WITHOUT_SECRET = "webhook_endpoint_exists_but_its_signing_secret_is_not_in_the_keyring"
    SECRET_WITHOUT_ENDPOINT = "keyring_holds_a_signing_secret_but_no_endpoint_has_this_address"
    LIST_TOO_LONG = "list_is_longer_than_the_page_allowance"
    WRITE_REFUSED = "write_refused_by_provider"
    WRITE_UNKNOWN = "write_outcome_unknown_do_not_repeat"
    WRITE_ANSWER_MISMATCH = "created_object_differs_from_the_request"
    SECRET_MISSING = "created_endpoint_answer_held_no_usable_signing_secret"
    SECRET_NOT_STORED = "signing_secret_could_not_be_stored_in_the_keyring"
    SECRET_IN_OUTPUT = "secret_in_output_refused"
    UNEXPECTED_ERROR = "unexpected_error"


class SetupDetail(str, Enum):
    """The cause behind a failure. An unexpected error names its exception type instead."""

    TIMEOUT = "timeout"
    CONNECTION_FAILED = "connection_failed"
    RESPONSE_TOO_LARGE = "response_too_large"
    TRANSPORT_CONTRACT = "transport_contract_violation"
    MALFORMED_RESPONSE = "malformed_response"
    UNEXPECTED_STATUS = "unexpected_status"


class ObjectState(str, Enum):
    """What one run learned about one of the four objects."""

    EXISTING = "existing"
    CREATED = "created"
    MISSING = "missing"
    NOT_REACHED = "not_reached"


REFUSALS = tuple(item.value for item in SetupRefusal)
FAILURES = tuple(item.value for item in SetupFailure)
TRANSPORT_FAILURE_CODES = (SetupDetail.TIMEOUT.value, SetupDetail.CONNECTION_FAILED.value,
                           SetupDetail.RESPONSE_TOO_LARGE.value)
_EXIT_CODES = {SetupOutcome.READY: 0, SetupOutcome.DRY_RUN: 0, SetupOutcome.STOPPED: 1,
               SetupOutcome.OUTCOME_UNKNOWN: 3, SetupOutcome.STOPPED_AFTER_WRITES: 4}


class Refusal(Exception):
    """Refused before any provider request. It carries a code, never a value."""

    def __init__(self, reason):
        self.code = SetupRefusal(reason).value
        super().__init__(self.code)


class TransportFailure(Exception):
    """The answer was lost, so a write may or may not have taken effect."""

    def __init__(self, code):
        if code not in TRANSPORT_FAILURE_CODES:
            raise ValueError("unsupported transport failure code")
        self.code = code
        super().__init__(code)


class _Stop(Exception):
    """Ends a run that reached Stripe, with a typed outcome and failure."""

    def __init__(self, outcome, failure, detail=None):
        super().__init__(failure.value)
        self.outcome, self.failure, self.detail = outcome, failure, detail


@dataclass(frozen=True)
class SandboxPlan:
    """The exact objects that the command finds or creates. Amounts are in cents."""

    product_id: str = "baltor_pro"
    product_name: str = "Baltor Pro"
    price_lookup_key: str = "baltor_pro_monthly_usd"
    currency: str = "usd"
    unit_amount: int = 2_900
    interval: str = "month"
    interval_count: int = 1
    plan_ref: str = "pro-monthly"
    # The discount an invitation carries. The coupon is the discount itself;
    # the promotion code is the readable code the invited person types.
    coupon_id: str = "baltor_invitation"
    coupon_name: str = "Baltor invitation"
    coupon_percent_off: int = 40
    coupon_duration: str = "once"
    promotion_code: str = "BALTORFOUNDING40"
    marker_key: str = "baltor_setup"
    event_types: "tuple[str, ...]" = SERVICE_EVENT_TYPES
    record_type: str = PLAN_RECORD_TYPE

    def __post_init__(self):
        object.__setattr__(self, "event_types", tuple(self.event_types))
        names = (self.product_id, self.product_name, self.price_lookup_key, self.currency, self.interval,
                 self.plan_ref, self.marker_key, self.coupon_id, self.coupon_name, self.coupon_duration,
                 self.promotion_code, *self.event_types)
        if (self.record_type != PLAN_RECORD_TYPE or any(not isinstance(name, str) or not name for name in names)
                or not _OBJECT_IDENTITY.fullmatch(self.product_id)
                or not _OBJECT_IDENTITY.fullmatch(self.coupon_id)
                or not _PROMOTION_CODE.fullmatch(self.promotion_code)
                or self.coupon_duration not in COUPON_DURATIONS
                or type(self.coupon_percent_off) is not int or not 1 <= self.coupon_percent_off <= 100
                or type(self.unit_amount) is not int or self.unit_amount <= 0
                or type(self.interval_count) is not int or self.interval_count <= 0
                or not self.event_types or len(set(self.event_types)) != len(self.event_types)):
            raise Refusal(SetupRefusal.PLAN)

    @property
    def marker_value(self):
        return self.record_type


@dataclass(frozen=True)
class RequestLimits:
    """Bounds for one request, for reading its answer and for reading a list."""

    timeout_seconds: float = 15.0
    maximum_response_bytes: int = 2_000_000
    maximum_pages: int = 5

    def __post_init__(self):
        if (type(self.timeout_seconds) not in (int, float) or not math.isfinite(self.timeout_seconds)
                or not 0 < self.timeout_seconds <= 60
                or type(self.maximum_response_bytes) is not int or not 1 <= self.maximum_response_bytes <= 8_000_000
                or type(self.maximum_pages) is not int or not 1 <= self.maximum_pages <= 20):
            raise Refusal(SetupRefusal.LIMITS)


@dataclass(frozen=True)
class SetupRequest:
    """Validated operator input. Nothing here comes from a provider answer."""

    webhook_url: str
    api_version: str
    write: bool
    plan: SandboxPlan = field(default_factory=SandboxPlan)

    def __post_init__(self):
        _require_webhook_address(self.webhook_url)
        _require_supported_api_version(self.api_version)
        if type(self.write) is not bool or not isinstance(self.plan, SandboxPlan):
            raise Refusal(SetupRefusal.MODE)

    @property
    def service_origin(self):
        parts = urlsplit(self.webhook_url)
        return urlunsplit((parts.scheme, parts.netloc, "", "", ""))


@dataclass(frozen=True)
class CredentialBinding:
    """Where the test key arrives and which Stripe account it is recorded for."""

    reference: str
    environment_name: str
    account_id: str

    @property
    def service_api_key_reference(self):
        """The host configuration reads the same environment name that staging sets."""
        return ENVIRONMENT_REFERENCE_PREFIX + self.environment_name


@dataclass(frozen=True)
class SecretReference:
    """The named keyring reference for the signing secret of one endpoint address."""

    name: str
    attributes: "tuple[tuple[str, str], ...]"
    manifest: dict = field(repr=False, compare=False)

    @property
    def label(self):
        """The keyring label that tools/operator_credentials.py writes for this name."""
        return KEYRING_LABEL_PREFIX + self.name

    @property
    def search_attributes(self):
        return {"application": KEYRING_APPLICATION, **dict(self.attributes)}

    @property
    def manifest_entry(self):
        """The whole reference entry, ready to paste into the manifest file.

        It holds no secret value. The operator copies it into the api_keys
        map of tools/operator_credentials.json under the reference name, and
        tools/stage_service_secrets.py then finds the environment name and the
        purpose it needs. A partial copy of the keyring attributes alone is
        not enough, which is why the report carries this exact record.
        """
        return dict(self.manifest["api_keys"][self.name])


@dataclass(frozen=True)
class StripeRequest:
    """One bounded request to a fixed Stripe path. The key stays out of repr."""

    method: str
    path: str
    parameters: "tuple[tuple[str, str], ...]"
    api_version: str
    idempotency_key: str
    timeout_seconds: float
    maximum_response_bytes: int
    credential: str = field(repr=False)

    def __post_init__(self):
        parameters = tuple(tuple(pair) for pair in self.parameters)
        if any(len(pair) != 2 or any(not isinstance(value, str) for value in pair) for pair in parameters):
            raise ValueError("request parameters must be pairs of text")
        object.__setattr__(self, "parameters", parameters)
        read = (self.method == GET_METHOD and not self.idempotency_key
                and (self.path == ACCOUNT_PATH or self.path in LIST_PATHS
                     or _PRODUCT_READ_PATH.fullmatch(self.path) is not None
                     or _COUPON_READ_PATH.fullmatch(self.path) is not None))
        write = (self.method == POST_METHOD and self.path in WRITE_PATHS
                 and self.idempotency_key.startswith(IDEMPOTENCY_KEY_PREFIX)
                 and len(self.idempotency_key) > len(IDEMPOTENCY_KEY_PREFIX))
        if not (read or write):
            raise ValueError("unsupported Stripe operation")


@dataclass(frozen=True)
class StripeResponse:
    """A status and a bounded body. The body can hold the signing secret, so repr omits it."""

    status: int
    body: bytes = field(repr=False)


@dataclass
class ObjectReport:
    """Identifiers and the state of one object. It never holds a secret."""

    state: ObjectState = ObjectState.NOT_REACHED
    identity: "str | None" = None
    idempotency_key: "str | None" = None


@dataclass(frozen=True)
class SetupResult:
    """The typed result of one run. Private values stay out of repr."""

    outcome: SetupOutcome
    failure: "SetupFailure | None"
    detail: "str | None"
    account_id: "str | None"
    product: ObjectReport
    price: ObjectReport
    portal: ObjectReport
    endpoint: ObjectReport
    coupon: ObjectReport
    promotion_code: ObjectReport
    secret_in_keyring: bool
    provider_requests: int
    provider_writes: int
    committed_writes: int
    provider_status: "int | None"
    sensitive_values: "tuple[str, ...]" = field(default=(), repr=False)


@dataclass
class _Progress:
    """What is known so far. It is kept apart so that a stop can still be reported."""

    requests: int = 0
    writes: int = 0
    committed_writes: int = 0
    status: "int | None" = None
    account_id: "str | None" = None
    product: ObjectReport = field(default_factory=ObjectReport)
    price: ObjectReport = field(default_factory=ObjectReport)
    portal: ObjectReport = field(default_factory=ObjectReport)
    endpoint: ObjectReport = field(default_factory=ObjectReport)
    coupon: ObjectReport = field(default_factory=ObjectReport)
    promotion_code: ObjectReport = field(default_factory=ObjectReport)
    secret_in_keyring: bool = False
    sensitive: list = field(default_factory=list)


# Guards before any request.

def _require_one_mode(dry_run, confirmed):
    if (dry_run is True) == (confirmed is True):
        raise Refusal(SetupRefusal.MODE)


def _require_webhook_address(value):
    if (not isinstance(value, str) or not value.isascii() or not 0 < len(value) <= 2_048
            or any(ord(character) <= 32 or ord(character) == 127 for character in value)):
        raise Refusal(SetupRefusal.WEBHOOK_URL)
    try:
        parts = urlsplit(value)
        port = parts.port
    except ValueError:
        raise Refusal(SetupRefusal.WEBHOOK_URL) from None
    host = parts.hostname or ""
    if (parts.scheme != SECURE_SCHEME or port is not None or parts.username or parts.password
            or not _HOSTNAME.fullmatch(host) or host.rsplit(".", 1)[-1].isdigit()
            or not _URL_PATH.fullmatch(parts.path)
            or any(segment in _DOT_SEGMENTS for segment in parts.path.split("/"))
            or urlunsplit((parts.scheme, host, parts.path, "", "")) != value):
        raise Refusal(SetupRefusal.WEBHOOK_URL)


def _require_supported_api_version(value):
    match = _API_VERSION.fullmatch(value) if isinstance(value, str) else None
    if match is None:
        raise Refusal(SetupRefusal.API_VERSION)
    if match.group(1) < EARLIEST_SUPPORTED_API_VERSION:
        raise Refusal(SetupRefusal.API_VERSION_TOO_OLD)


def load_manifest():
    """The reference manifest that tools/operator_credentials.py also reads."""
    try:
        return operator_credentials.references()
    except Exception:
        raise Refusal(SetupRefusal.CREDENTIAL_MANIFEST) from None


def _require_supported_manifest(manifest):
    if (not isinstance(manifest, dict) or manifest.get("record_type") != MANIFEST_RECORD_TYPE
            or not isinstance(manifest.get("api_keys"), dict)):
        raise Refusal(SetupRefusal.CREDENTIAL_MANIFEST)


def _require_test_prefixes(spec):
    """The manifest itself must restrict the reference to test keys."""
    prefixes = spec.get("required_prefixes") if isinstance(spec, dict) else None
    if (not isinstance(prefixes, list) or not prefixes
            or any(prefix not in TEST_KEY_PREFIXES for prefix in prefixes)):
        raise Refusal(SetupRefusal.CREDENTIAL_REFERENCE)


def credential_binding(reference, manifest):
    """Read the environment name and the bound account from the manifest."""
    _require_supported_manifest(manifest)
    spec = manifest["api_keys"].get(reference) if isinstance(reference, str) else None
    if (not isinstance(spec, dict) or spec.get("service") != PAYMENT_SERVICE
            or not isinstance(spec.get("environment"), str)
            or not _ENVIRONMENT_NAME.fullmatch(spec["environment"])
            or not isinstance(spec.get("account"), str) or not _ACCOUNT_IDENTITY.fullmatch(spec["account"])):
        raise Refusal(SetupRefusal.CREDENTIAL_REFERENCE)
    _require_test_prefixes(spec)
    return CredentialBinding(reference, spec["environment"], spec["account"])


def _require_test_key(value):
    """A live key, a publishable key, a masked key and an empty value are all refused."""
    if not isinstance(value, str) or not value.startswith(TEST_KEY_PREFIXES) or not _TEST_KEY.fullmatch(value):
        raise Refusal(SetupRefusal.LIVE_KEY)


def resolve_credential(binding, environment):
    """Take the key from the named environment variable. It is never printed."""
    value = environment.get(binding.environment_name)
    _require_test_key(value)
    return value


class KeyringAmbiguous(Exception):
    """Another saved secret already occupies the place this reference would use."""


def secret_reference(name, binding, request, manifest):
    """The keyring reference for this endpoint address, as a manifest entry.

    The entry records the exact endpoint address. The keyring finds an item by
    service, account and purpose only, so one Stripe account holds one signing
    secret for the service. When the entry is already declared for another
    address, the run is refused instead of using the wrong secret.
    """
    if not isinstance(name, str) or not _REFERENCE_NAME.fullmatch(name) or name == binding.reference:
        raise Refusal(SetupRefusal.SECRET_REFERENCE)
    spec = {"service": PAYMENT_SERVICE, "account": binding.account_id, "purpose": WEBHOOK_SECRET_PURPOSE,
            "environment": SERVICE_WEBHOOK_SECRET_ENVIRONMENT, "required_prefixes": [WEBHOOK_SECRET_PREFIX],
            "value_pattern": WEBHOOK_SECRET_VALUE_PATTERN, "endpoint_url": request.webhook_url}
    declared = manifest["api_keys"].get(name)
    if declared is not None and declared != spec:
        raise Refusal(SetupRefusal.SECRET_REFERENCE)
    for other, held in manifest["api_keys"].items():
        if (other != name and isinstance(held, dict)
                and [held.get(key) for key in ("service", "account", "purpose")]
                == [spec[key] for key in ("service", "account", "purpose")]):
            raise Refusal(SetupRefusal.SECRET_REFERENCE)
    merged = {**manifest, "api_keys": {**manifest["api_keys"], name: spec}}
    attributes = tuple((key, spec[key]) for key in ("service", "account", "purpose"))
    return SecretReference(name, attributes, merged)


class KeyringSecretStore:
    """The system keyring, through the functions of tools/operator_credentials.py."""

    def holds(self, reference):
        saved = operator_credentials.collection()
        found = list(saved.search_items(reference.search_attributes))
        if len(found) > 1:
            raise KeyringAmbiguous(SetupRefusal.KEYRING_AMBIGUOUS.value)
        if found and found[0].get_label() != reference.label:
            # A secret saved under a different reference name would belong to
            # another endpoint address. Using it would sign for the wrong one.
            raise KeyringAmbiguous(SetupRefusal.KEYRING_AMBIGUOUS.value)
        return len(found) == 1

    def store(self, reference, value):
        operator_credentials.store_api_reference(reference.name, value, data=reference.manifest)


def keyring_holds(store, reference):
    """Ask the keyring once, before any request. A locked keyring refuses the run."""
    try:
        held = store.holds(reference)
    except KeyringAmbiguous:
        raise Refusal(SetupRefusal.KEYRING_AMBIGUOUS) from None
    except Exception:
        raise Refusal(SetupRefusal.KEYRING) from None
    if type(held) is not bool:
        raise Refusal(SetupRefusal.KEYRING)
    return held


def reserve_report(value):
    """Create the report file before any request, so that a run never overwrites evidence."""
    path = Path(value)
    try:
        folder = path.parent.resolve(strict=True)
    except (OSError, RuntimeError):
        raise Refusal(SetupRefusal.REPORT_FOLDER) from None
    if not folder.is_dir() or path.name in ("", *_DOT_SEGMENTS):
        raise Refusal(SetupRefusal.REPORT_FOLDER)
    target = folder / path.name
    try:
        descriptor = os.open(target, _REPORT_OPEN_FLAGS, _REPORT_MODE)
    except FileExistsError:
        raise Refusal(SetupRefusal.REPORT_EXISTS) from None
    except OSError:
        raise Refusal(SetupRefusal.REPORT_PATH) from None
    return target, os.fdopen(descriptor, "w", encoding="utf-8")


# The default transport.

def _client_options(request, http_transport):
    """Redirects are never followed and proxy settings in the environment are ignored."""
    return {"follow_redirects": False, "trust_env": False, "timeout": request.timeout_seconds,
            "transport": http_transport}


def _within_limit(size, request):
    return size <= request.maximum_response_bytes


def send_stripe_request(request, *, http_transport=None):
    """Send one request to the fixed Stripe origin and read a bounded answer."""
    import httpx
    if not isinstance(request, StripeRequest):
        raise ValueError("a validated Stripe request is required")
    deadline = time.monotonic() + request.timeout_seconds
    headers = {"Authorization": "Bearer " + request.credential, "Stripe-Version": request.api_version,
               "Accept": JSON_MEDIA_TYPE}
    options = {"headers": headers}
    if request.method == POST_METHOD:
        headers.update({"Idempotency-Key": request.idempotency_key, "Content-Type": FORM_MEDIA_TYPE})
        options["content"] = urlencode(request.parameters).encode()
    elif request.parameters:
        options["params"] = list(request.parameters)
    try:
        with httpx.Client(**_client_options(request, http_transport)) as client:
            with client.stream(request.method, STRIPE_ORIGIN + request.path, **options) as response:
                chunks, size = [], 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if not _within_limit(size, request):
                        raise TransportFailure(SetupDetail.RESPONSE_TOO_LARGE.value)
                    if time.monotonic() > deadline:
                        raise TransportFailure(SetupDetail.TIMEOUT.value)
                    chunks.append(chunk)
                return StripeResponse(response.status_code, b"".join(chunks))
    except TransportFailure:
        raise
    except httpx.TimeoutException:
        raise TransportFailure(SetupDetail.TIMEOUT.value) from None
    except httpx.HTTPError:
        raise TransportFailure(SetupDetail.CONNECTION_FAILED.value) from None


# Reading answers.

def _unique_pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("a repeated key makes the answer ambiguous")
        value[key] = item
    return value


def _refuse_constant(name):
    raise ValueError("unsupported JSON constant " + name)


def _json_object(body):
    value = json.loads(body.decode("utf-8"), object_pairs_hook=_unique_pairs, parse_constant=_refuse_constant)
    if not isinstance(value, dict):
        raise ValueError("the answer is not a JSON object")
    return value


def _require_bounded_body(response, limits):
    if len(response.body) > limits.maximum_response_bytes:
        raise TransportFailure(SetupDetail.RESPONSE_TOO_LARGE.value)


def _refuse_provider_redirect(status):
    return 300 <= status < 400


def new_idempotency_key():
    """A fresh key for each write. A repeated run must find objects by reading, not by replay."""
    return IDEMPOTENCY_KEY_PREFIX + secrets.token_hex(16)


def _require_write_allowed(request):
    if request.write is not True:
        raise RuntimeError("a dry run attempted a write")


def _require_test_mode_object(value):
    if value.get("livemode") is not False:
        raise _Stop(SetupOutcome.STOPPED, SetupFailure.LIVE_MODE_OBJECT)


def _require_same_account(account, binding):
    if account.get("object") != ACCOUNT_OBJECT or account.get("id") != binding.account_id:
        raise _Stop(SetupOutcome.STOPPED, SetupFailure.ACCOUNT_MISMATCH)


def _require_single(matches, failure):
    if len(matches) > 1:
        raise _Stop(SetupOutcome.STOPPED, failure)


def _identity(value):
    found = value.get("id")
    if not isinstance(found, str) or not _OBJECT_IDENTITY.fullmatch(found):
        raise ValueError("the answer holds no usable identity")
    return found


def _require_expected_product(product, plan):
    if (product.get("object") != PRODUCT_OBJECT or product.get("id") != plan.product_id
            or product.get("active") is not True or product.get("name") != plan.product_name):
        raise _Stop(SetupOutcome.STOPPED, SetupFailure.PRODUCT_MISMATCH)


def _require_expected_price(price, plan):
    recurring = price.get("recurring")
    if (price.get("object") != PRICE_OBJECT or price.get("active") is not True
            or price.get("type") != RECURRING_PRICE or price.get("currency") != plan.currency
            or price.get("unit_amount") != plan.unit_amount or type(price.get("unit_amount")) is not int
            or price.get("lookup_key") != plan.price_lookup_key or price.get("product") != plan.product_id
            or not isinstance(recurring, dict) or recurring.get("interval") != plan.interval
            or recurring.get("interval_count") != plan.interval_count
            or not _identity(price).startswith("price_")):
        raise _Stop(SetupOutcome.STOPPED, SetupFailure.PRICE_MISMATCH)


def _feature_enabled(configuration, name):
    features = configuration.get("features")
    feature = features.get(name) if isinstance(features, dict) else None
    return isinstance(feature, dict) and feature.get("enabled") is True


def _require_expected_portal(configuration, plan):
    if (configuration.get("object") != PORTAL_OBJECT or configuration.get("active") is not True
            or not _feature_enabled(configuration, "subscription_cancel")
            or not _feature_enabled(configuration, "payment_method_update")
            or not _identity(configuration).startswith("bpc_")):
        raise _Stop(SetupOutcome.STOPPED, SetupFailure.PORTAL_MISMATCH)


def _require_expected_endpoint(endpoint, request):
    events = endpoint.get("enabled_events")
    if (endpoint.get("object") != ENDPOINT_OBJECT or endpoint.get("url") != request.webhook_url
            or endpoint.get("status") != ENDPOINT_ENABLED or not isinstance(events, list)
            or sorted(events) != sorted(request.plan.event_types) or len(events) != len(request.plan.event_types)
            or endpoint.get("api_version") != request.api_version
            or not _identity(endpoint).startswith("we_")):
        raise _Stop(SetupOutcome.STOPPED, SetupFailure.ENDPOINT_MISMATCH)


def _require_expected_coupon(coupon, plan):
    if (coupon.get("object") != COUPON_OBJECT or coupon.get("id") != plan.coupon_id
            or coupon.get("valid") is not True or coupon.get("name") != plan.coupon_name
            or coupon.get("duration") != plan.coupon_duration
            or coupon.get("percent_off") != plan.coupon_percent_off
            or coupon.get("amount_off") is not None):
        raise _Stop(SetupOutcome.STOPPED, SetupFailure.COUPON_MISMATCH)


def _require_expected_promotion_code(promotion_code, plan):
    coupon = promotion_code.get("coupon")
    if (promotion_code.get("object") != PROMOTION_CODE_OBJECT or promotion_code.get("active") is not True
            or promotion_code.get("code") != plan.promotion_code
            or not isinstance(coupon, dict) or coupon.get("id") != plan.coupon_id
            or promotion_code.get("customer") is not None
            or not _identity(promotion_code).startswith("promo_")):
        raise _Stop(SetupOutcome.STOPPED, SetupFailure.PROMOTION_CODE_MISMATCH)


def _require_secret_matches_endpoint(endpoint_exists, secret_held):
    """The endpoint and its saved signing secret have to be present together.

    What keeps one address to one endpoint is the read before the writes: an
    endpoint that the read finds is never written again, whatever this rule
    does. This rule covers the two states that reading alone cannot repair.
    An endpoint whose signing secret is not in the keyring cannot be used,
    because Stripe shows that secret only when the endpoint is created;
    continuing would report a ready service that names a signing secret
    nobody holds, so every delivery would fail its signature check. A saved
    secret with no endpoint at the address is the mirror image of the same
    problem. Either way the run stops and the operator decides.
    """
    if endpoint_exists and not secret_held:
        raise _Stop(SetupOutcome.STOPPED, SetupFailure.ENDPOINT_WITHOUT_SECRET)
    if secret_held and not endpoint_exists:
        raise _Stop(SetupOutcome.STOPPED, SetupFailure.SECRET_WITHOUT_ENDPOINT)


class _Session:
    """The requests of one run. Reads may fail safely; a lost write is unknown."""

    def __init__(self, request, credential, transport, limits, progress, key_factory):
        self.request, self.limits, self.progress = request, limits, progress
        self._credential, self._transport, self._key_factory = credential, transport, key_factory

    def _exchange(self, method, path, parameters, idempotency_key, lost):
        wire = StripeRequest(method, path, tuple(parameters), self.request.api_version, idempotency_key,
                             self.limits.timeout_seconds, self.limits.maximum_response_bytes, self._credential)
        self.progress.requests += 1
        self.progress.writes += 1 if method == POST_METHOD else 0
        self.progress.status = None
        try:
            response = self._transport(wire)
        except TransportFailure as failure:
            raise _Stop(*lost, failure.code) from None
        if (not isinstance(response, StripeResponse) or type(response.status) is not int
                or not isinstance(response.body, bytes)):
            raise _Stop(*lost, SetupDetail.TRANSPORT_CONTRACT.value)
        try:
            _require_bounded_body(response, self.limits)
        except TransportFailure as failure:
            raise _Stop(*lost, failure.code) from None
        self.progress.status = response.status
        if _refuse_provider_redirect(response.status):
            raise _Stop(lost[0], SetupFailure.PROVIDER_REDIRECT)
        if response.status in CREDENTIAL_REFUSED_STATUSES:
            raise _Stop(SetupOutcome.STOPPED, SetupFailure.CREDENTIAL_REFUSED)
        return response

    def read(self, path, parameters=(), *, missing_allowed=False):
        lost = (SetupOutcome.STOPPED, SetupFailure.READ_FAILED)
        response = self._exchange(GET_METHOD, path, parameters, "", lost)
        if missing_allowed and response.status == NOT_FOUND_STATUS:
            return None
        if response.status != OK_STATUS:
            raise _Stop(*lost, SetupDetail.UNEXPECTED_STATUS.value)
        try:
            value = _json_object(response.body)
        except ValueError:
            raise _Stop(*lost, SetupDetail.MALFORMED_RESPONSE.value) from None
        return value

    def read_list(self, path, parameters):
        """Every page of a list, within the page allowance. Every row must be in test mode."""
        rows, cursor = [], ()
        for _page in range(self.limits.maximum_pages):
            page = self.read(path, (*parameters, *cursor))
            data = page.get("data")
            if (page.get("object") != LIST_OBJECT or not isinstance(data, list)
                    or type(page.get("has_more")) is not bool or any(not isinstance(row, dict) for row in data)):
                raise _Stop(SetupOutcome.STOPPED, SetupFailure.READ_FAILED, SetupDetail.MALFORMED_RESPONSE.value)
            for row in data:
                _require_test_mode_object(row)
            rows.extend(data)
            if not page["has_more"]:
                return rows
            try:
                cursor = (("starting_after", _identity(data[-1])),) if data else None
            except ValueError:
                cursor = None
            if cursor is None:
                raise _Stop(SetupOutcome.STOPPED, SetupFailure.READ_FAILED, SetupDetail.MALFORMED_RESPONSE.value)
        raise _Stop(SetupOutcome.STOPPED, SetupFailure.LIST_TOO_LONG)

    def write(self, path, parameters, entry):
        """One write, sent once. Only a clear refusal by Stripe counts as not performed."""
        _require_write_allowed(self.request)
        lost = (SetupOutcome.OUTCOME_UNKNOWN, SetupFailure.WRITE_UNKNOWN)
        entry.idempotency_key = self._key_factory()
        response = self._exchange(POST_METHOD, path, parameters, entry.idempotency_key, lost)
        if response.status in WRITE_NOT_PERFORMED_STATUSES:
            raise _Stop(SetupOutcome.STOPPED, SetupFailure.WRITE_REFUSED, SetupDetail.UNEXPECTED_STATUS.value)
        if response.status != OK_STATUS:
            raise _Stop(*lost, SetupDetail.UNEXPECTED_STATUS.value)
        # Stripe answered this write with a success, so the object exists from
        # here on, whatever the rest of the run does with the answer.
        self.progress.committed_writes += 1
        try:
            value = _json_object(response.body)
            entry.identity = _identity(value)
        except ValueError:
            raise _Stop(*lost, SetupDetail.MALFORMED_RESPONSE.value) from None
        entry.state = ObjectState.CREATED
        _require_test_mode_object(value)
        return value


def _product_parameters(plan):
    return (("id", plan.product_id), ("name", plan.product_name),
            ("metadata[" + plan.marker_key + "]", plan.marker_value))


def _price_parameters(plan):
    return (("product", plan.product_id), ("currency", plan.currency), ("unit_amount", str(plan.unit_amount)),
            ("recurring[interval]", plan.interval), ("recurring[interval_count]", str(plan.interval_count)),
            ("lookup_key", plan.price_lookup_key), ("metadata[" + plan.marker_key + "]", plan.marker_value))


def _portal_parameters(plan):
    return (("features[subscription_cancel][enabled]", FORM_TRUE),
            ("features[subscription_cancel][mode]", CANCEL_AT_PERIOD_END),
            ("features[payment_method_update][enabled]", FORM_TRUE),
            ("features[invoice_history][enabled]", FORM_TRUE),
            ("metadata[" + plan.marker_key + "]", plan.marker_value))


def _coupon_parameters(plan):
    return (("id", plan.coupon_id), ("name", plan.coupon_name), ("duration", plan.coupon_duration),
            ("percent_off", str(plan.coupon_percent_off)),
            ("metadata[" + plan.marker_key + "]", plan.marker_value))


def _promotion_code_parameters(plan):
    return (("coupon", plan.coupon_id), ("code", plan.promotion_code),
            ("metadata[" + plan.marker_key + "]", plan.marker_value))


def _endpoint_parameters(request):
    events = tuple(("enabled_events[" + str(index) + "]", name)
                   for index, name in enumerate(request.plan.event_types))
    return (("url", request.webhook_url), *events, ("api_version", request.api_version),
            ("metadata[" + request.plan.marker_key + "]", request.plan.marker_value))


def _as_mismatch(check, value, expected):
    """A created object that differs from the request is reported; it is not repeated."""
    try:
        check(value, expected)
    except (_Stop, ValueError):
        raise _Stop(SetupOutcome.STOPPED, SetupFailure.WRITE_ANSWER_MISMATCH) from None


def _observe(session, binding, secret_held):
    """Every read, before the first write. Returns what already exists."""
    request, progress, plan = session.request, session.progress, session.request.plan
    account = session.read(ACCOUNT_PATH)
    _require_same_account(account, binding)
    progress.account_id = binding.account_id

    product = session.read(PRODUCTS_PATH + "/" + plan.product_id, missing_allowed=True)
    if product is not None:
        _require_test_mode_object(product)
        _require_expected_product(product, plan)
        progress.product = ObjectReport(ObjectState.EXISTING, plan.product_id)
    else:
        progress.product = ObjectReport(ObjectState.MISSING)

    prices = session.read_list(PRICES_PATH, (("lookup_keys[0]", plan.price_lookup_key), ("active", FORM_TRUE),
                                             ("limit", str(LOOKUP_PAGE_SIZE))))
    _require_single(prices, SetupFailure.PRICE_AMBIGUOUS)
    progress.price = ObjectReport(ObjectState.MISSING)
    for price in prices:
        try:
            _require_expected_price(price, plan)
        except ValueError:
            raise _Stop(SetupOutcome.STOPPED, SetupFailure.PRICE_MISMATCH) from None
        progress.price = ObjectReport(ObjectState.EXISTING, price["id"])

    configurations = [row for row in session.read_list(
        PORTAL_CONFIGURATIONS_PATH, (("active", FORM_TRUE), ("limit", str(PAGE_SIZE))))
        if isinstance(row.get("metadata"), dict) and row["metadata"].get(plan.marker_key) == plan.marker_value]
    _require_single(configurations, SetupFailure.PORTAL_AMBIGUOUS)
    progress.portal = ObjectReport(ObjectState.MISSING)
    for configuration in configurations:
        try:
            _require_expected_portal(configuration, plan)
        except ValueError:
            raise _Stop(SetupOutcome.STOPPED, SetupFailure.PORTAL_MISMATCH) from None
        progress.portal = ObjectReport(ObjectState.EXISTING, configuration["id"])

    coupon = session.read(COUPONS_PATH + "/" + plan.coupon_id, missing_allowed=True)
    if coupon is not None:
        _require_test_mode_object(coupon)
        _require_expected_coupon(coupon, plan)
        progress.coupon = ObjectReport(ObjectState.EXISTING, plan.coupon_id)
    else:
        progress.coupon = ObjectReport(ObjectState.MISSING)

    promotion_codes = session.read_list(PROMOTION_CODES_PATH, (("code", plan.promotion_code),
                                                               ("limit", str(LOOKUP_PAGE_SIZE))))
    _require_single(promotion_codes, SetupFailure.PROMOTION_CODE_AMBIGUOUS)
    progress.promotion_code = ObjectReport(ObjectState.MISSING)
    for promotion_code in promotion_codes:
        _require_test_mode_object(promotion_code)
        _require_expected_promotion_code(promotion_code, plan)
        progress.promotion_code = ObjectReport(ObjectState.EXISTING, promotion_code["id"])

    endpoints = [row for row in session.read_list(WEBHOOK_ENDPOINTS_PATH, (("limit", str(PAGE_SIZE)),))
                 if row.get("url") == request.webhook_url]
    _require_single(endpoints, SetupFailure.ENDPOINT_AMBIGUOUS)
    progress.endpoint = ObjectReport(ObjectState.MISSING)
    for endpoint in endpoints:
        try:
            _require_expected_endpoint(endpoint, request)
        except ValueError:
            raise _Stop(SetupOutcome.STOPPED, SetupFailure.ENDPOINT_MISMATCH) from None
        progress.endpoint = ObjectReport(ObjectState.EXISTING, endpoint["id"])
    _require_secret_matches_endpoint(progress.endpoint.state is ObjectState.EXISTING, secret_held)


def _store_signing_secret(endpoint, reference, store, progress):
    """Move the secret from the answer into the keyring. It goes nowhere else.

    The shape check and the keyring apply the same rule: the pattern here is
    the value_pattern of the reference entry, and the keyring store validates
    the value against that entry before saving it. So checking first discards
    nothing that the store would have kept. When the value cannot be kept, the
    endpoint has already been created and its secret is gone, which the
    outcome, the report and the guide all say plainly.
    """
    secret = endpoint.get("secret")
    if isinstance(secret, str) and secret:
        progress.sensitive.append(secret)
    if not isinstance(secret, str) or not _WEBHOOK_SECRET.fullmatch(secret):
        raise _Stop(SetupOutcome.STOPPED, SetupFailure.SECRET_MISSING)
    try:
        store.store(reference, secret)
        held = store.holds(reference)
    except Exception as error:
        raise _Stop(SetupOutcome.STOPPED, SetupFailure.SECRET_NOT_STORED, type(error).__name__) from None
    if held is not True:
        raise _Stop(SetupOutcome.STOPPED, SetupFailure.SECRET_NOT_STORED)
    progress.secret_in_keyring = True


def _create_missing(session, reference, store):
    """The writes, in dependency order. Each one is sent once."""
    request, progress, plan = session.request, session.progress, session.request.plan
    if progress.product.state is ObjectState.MISSING:
        product = session.write(PRODUCTS_PATH, _product_parameters(plan), progress.product)
        _as_mismatch(_require_expected_product, product, plan)
    if progress.price.state is ObjectState.MISSING:
        price = session.write(PRICES_PATH, _price_parameters(plan), progress.price)
        _as_mismatch(_require_expected_price, price, plan)
    if progress.portal.state is ObjectState.MISSING:
        configuration = session.write(PORTAL_CONFIGURATIONS_PATH, _portal_parameters(plan), progress.portal)
        _as_mismatch(_require_expected_portal, configuration, plan)
    if progress.coupon.state is ObjectState.MISSING:
        coupon = session.write(COUPONS_PATH, _coupon_parameters(plan), progress.coupon)
        _as_mismatch(_require_expected_coupon, coupon, plan)
    if progress.promotion_code.state is ObjectState.MISSING:
        promotion_code = session.write(PROMOTION_CODES_PATH, _promotion_code_parameters(plan), progress.promotion_code)
        _as_mismatch(_require_expected_promotion_code, promotion_code, plan)
    if progress.endpoint.state is ObjectState.MISSING:
        endpoint = session.write(WEBHOOK_ENDPOINTS_PATH, _endpoint_parameters(request), progress.endpoint)
        # The secret is stored first. A later mismatch must not lose the only copy.
        _store_signing_secret(endpoint, reference, store, progress)
        _as_mismatch(_require_expected_endpoint, endpoint, request)


def set_up_sandbox(request, binding, credential, reference, *, transport, store, secret_held,
                   limits=None, key_factory=new_idempotency_key):
    """Read everything, then write what is missing. Always returns a typed result."""
    progress = _Progress(secret_in_keyring=secret_held, sensitive=[credential])
    outcome, failure, detail = SetupOutcome.READY, None, None
    try:
        session = _Session(request, credential, transport, limits or RequestLimits(), progress, key_factory)
        _observe(session, binding, secret_held)
        if request.write:
            _create_missing(session, reference, store)
        else:
            outcome = SetupOutcome.DRY_RUN
    except _Stop as stop:
        outcome, failure, detail = stop.outcome, stop.failure, stop.detail
    except Exception as error:
        # A defect after a write was sent leaves that write unknown. No message is kept.
        outcome = SetupOutcome.OUTCOME_UNKNOWN if progress.writes else SetupOutcome.STOPPED
        failure, detail = SetupFailure.UNEXPECTED_ERROR, type(error).__name__
    if outcome is SetupOutcome.STOPPED and progress.committed_writes:
        # Stripe performed at least one write before the run stopped, so the
        # account changed. That is a different outcome, and a different exit
        # code, from a run that stopped with the account untouched.
        outcome = SetupOutcome.STOPPED_AFTER_WRITES
    return SetupResult(outcome, failure, detail, progress.account_id, progress.product, progress.price,
                       progress.portal, progress.endpoint, progress.coupon, progress.promotion_code,
                       progress.secret_in_keyring, progress.requests, progress.writes, progress.committed_writes,
                       progress.status, tuple(progress.sensitive))


# Output.

def host_billing_block(request, result, binding):
    """The billing block of the host configuration, with environment references only.

    The success address and the cancel address of checkout are deliberately
    the same page. The return from Stripe grants nothing: paid access comes
    from the subscription event and the entitlement policy, never from the
    address the browser lands on. A separate cancel page would therefore be a
    presentation choice, and the deployed application serves one address for
    the signed-in view. The guide records the same reason.
    """
    common = {"account_id": result.account_id, "api_version": request.api_version, "livemode": False}
    api_key_ref = binding.service_api_key_reference
    origin = request.service_origin
    return {
        "webhook": {**common, "signing_secret_refs": [SERVICE_WEBHOOK_SECRET_REFERENCE]},
        "policy": {"allowed_price_ids": [result.price.identity]},
        "provider": {**common, "api_key_ref": api_key_ref, "allow_network": True},
        "sessions": {**common, "api_key_ref": api_key_ref,
                     "plans": [{"plan_ref": request.plan.plan_ref, "label": request.plan.product_name,
                                "price_id": result.price.identity}],
                     "checkout_success_url": origin + "/app", "checkout_cancel_url": origin + "/app",
                     "portal_return_url": origin + "/app", "portal_configuration_id": result.portal.identity,
                     "allow_network": True, "allow_session_creation": True,
                     "allow_promotion_codes": True},
    }


def _entry(report):
    return {"state": report.state.value, "id": report.identity, "idempotency_key": report.idempotency_key}


def build_report(request, result, reference, binding, observed_at):
    plan = request.plan
    ready = result.outcome is SetupOutcome.READY
    return {
        "record_type": REPORT_RECORD_TYPE,
        "observed_at": observed_at.isoformat(timespec="seconds"),
        "mode": "confirmed_writes" if request.write else "dry_run",
        "provider_origin": STRIPE_ORIGIN,
        "account_id": result.account_id,
        "livemode": False,
        "api_version": request.api_version,
        "plan": {"record_type": plan.record_type, "product_name": plan.product_name,
                 "price_lookup_key": plan.price_lookup_key, "currency": plan.currency,
                 "unit_amount": plan.unit_amount, "interval": plan.interval,
                 "interval_count": plan.interval_count, "coupon_id": plan.coupon_id,
                 "promotion_code": plan.promotion_code},
        "product": _entry(result.product),
        "price": _entry(result.price),
        "portal_configuration": _entry(result.portal),
        "coupon": {**_entry(result.coupon), "percent_off": plan.coupon_percent_off,
                   "duration": plan.coupon_duration},
        "promotion_code": {**_entry(result.promotion_code), "code": plan.promotion_code,
                           "carried_by": "an invitation sent to one reviewed waiting list entry"},
        "webhook_endpoint": {**_entry(result.endpoint), "url": request.webhook_url,
                             "enabled_events": list(plan.event_types)},
        "signing_secret": {"keyring_reference": reference.name, "in_keyring": result.secret_in_keyring,
                           "keyring_attributes": dict(reference.attributes),
                           "keyring_label": reference.label, "value_recorded": False,
                           "manifest_entry": reference.manifest_entry},
        "service_environment_names": {"api_key": binding.environment_name,
                                      "webhook_signing_secret": SERVICE_WEBHOOK_SECRET_ENVIRONMENT},
        "outcome": result.outcome.value,
        "failure": result.failure.value if result.failure is not None else None,
        "detail": result.detail,
        "provider_status": result.provider_status,
        "provider_requests": result.provider_requests,
        "provider_writes": result.provider_writes,
        "committed_provider_writes": result.committed_writes,
        "automatic_retries": 0,
        "host_billing_block": host_billing_block(request, result, binding) if ready else None,
        "host_billing_block_kind": HOST_BILLING_RECORD_NOTE,
        "limitations": list(LIMITATIONS),
    }


def _require_no_secret(text, sensitive_values):
    if any(isinstance(value, str) and len(value) >= MINIMUM_LONG_SECRET_LENGTH and value in text
           for value in sensitive_values):
        raise Refusal(SetupRefusal.SECRET_IN_OUTPUT)


def encode_report(report, sensitive_values):
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    _require_no_secret(encoded, sensitive_values)
    return encoded


def _utc_now():
    return datetime.now(timezone.utc)


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--webhook-url", default=DEFAULT_WEBHOOK_URL,
                        help="HTTPS address of the billing webhook, without a port, a query or a fragment")
    parser.add_argument("--api-version", required=True,
                        help="Stripe API version for requests and for events, the same value as in the host configuration")
    parser.add_argument("--report", required=True, help="new report file in an existing folder")
    parser.add_argument("--credential-ref", default=DEFAULT_CREDENTIAL_REFERENCE,
                        help="reference name of the test key in tools/operator_credentials.json")
    parser.add_argument("--webhook-secret-ref", default=DEFAULT_WEBHOOK_SECRET_REFERENCE,
                        help="keyring reference name for the signing secret of the endpoint")
    parser.add_argument("--dry-run", action="store_true", help="only read; report what a confirmed run would create")
    parser.add_argument("--confirm-test-mode-writes", action="store_true",
                        help="confirm that missing objects may be created in the Stripe test environment")
    return parser


def main(argv=None, *, environment=None, transport=None, manifest=None, store=None, now=None,
         key_factory=new_idempotency_key):
    arguments = build_parser().parse_args(argv)
    current = _utc_now if now is None else now
    try:
        _require_one_mode(arguments.dry_run, arguments.confirm_test_mode_writes)
        request = SetupRequest(arguments.webhook_url, arguments.api_version, arguments.confirm_test_mode_writes)
        limits = RequestLimits()
        held_manifest = load_manifest() if manifest is None else manifest
        binding = credential_binding(arguments.credential_ref, held_manifest)
        credential = resolve_credential(binding, os.environ if environment is None else environment)
        reference = secret_reference(arguments.webhook_secret_ref, binding, request, held_manifest)
        keyring = KeyringSecretStore() if store is None else store
        secret_held = keyring_holds(keyring, reference)
        target, stream = reserve_report(arguments.report)
    except Refusal as refusal:
        sys.stderr.write(refusal.code + "\n")
        return EXIT_REFUSED_BEFORE_ANY_REQUEST
    try:
        with stream:
            result = set_up_sandbox(request, binding, credential, reference, transport=transport or send_stripe_request,
                                    store=keyring, secret_held=secret_held, limits=limits, key_factory=key_factory)
            written = _record(stream, request, result, reference, binding, current())
        return _summarize(result, target, written)
    except Exception as error:
        # A defect here must not print a message that could hold a private value.
        sys.stderr.write(SetupFailure.UNEXPECTED_ERROR.value + ":" + type(error).__name__ + "\n")
        return _EXIT_CODES[SetupOutcome.OUTCOME_UNKNOWN]


def _record(stream, request, result, reference, binding, observed_at):
    """Write the report durably. A report that would hold a secret is not written."""
    try:
        encoded = encode_report(build_report(request, result, reference, binding, observed_at),
                                result.sensitive_values)
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())
        return True
    except (Refusal, OSError):
        return False


def _summarize(result, target, written):
    summary = json.dumps({
        "outcome": result.outcome.value, "failure": result.failure.value if result.failure is not None else None,
        "detail": result.detail, "product": result.product.state.value, "price": result.price.state.value,
        "portal_configuration": result.portal.state.value, "webhook_endpoint": result.endpoint.state.value,
        "signing_secret_in_keyring": result.secret_in_keyring, "secret_printed": False,
        "provider_requests": result.provider_requests, "provider_writes": result.provider_writes,
        "committed_provider_writes": result.committed_writes,
        "report": str(target), "report_written": written}, sort_keys=True)
    try:
        _require_no_secret(summary, result.sensitive_values)
    except Refusal as refusal:
        summary = refusal.code
    sys.stdout.write(summary + "\n")
    if not written and result.outcome in (SetupOutcome.READY, SetupOutcome.DRY_RUN):
        # A run whose report could not be written did not end ready. It still
        # has to say whether Stripe performed a write, so the exit code is the
        # one that matches the account, not the one that matches the report.
        return _EXIT_CODES[SetupOutcome.STOPPED_AFTER_WRITES if result.committed_writes
                           else SetupOutcome.STOPPED]
    return _EXIT_CODES[result.outcome]


if __name__ == "__main__":
    raise SystemExit(main())
