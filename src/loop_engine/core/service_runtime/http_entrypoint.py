"""Executable host-configured intelligence service, with no dynamic code loading.

Configuration names a durable store and exact host-reviewed artifact manifest.
Serving does not create tenants or restore revoked grants. Host setup and key
issuance are separate explicit commands; no cloud account is created here.
An item is registered only when the host licence policy accepts the exact
licence identifier that the item declares.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, fields as dataclass_fields
import hashlib
import json
import os
from pathlib import Path

from ..harness_intelligence import HarnessIntelligenceCatalogue
from ..practitioner_runtime.provisioning import _item
from ..provisioning_server import (
    ProvisioningGrant, ProvisioningItemBinding, ProvisioningQualification, ProvisioningQualificationResolver,
)
from .http import ServiceHttpApplication, ServiceHttpConfiguration, _parse_json
from .http_auth import ServiceHttpAuthentication
from .observability import ServiceObservabilityPolicy
from .provisioning import DurableProvisioningBinding
from .records import (
    BillingCustomerBindingRequest, ServiceRuntimeConfig, ServiceRuntimeError,
    SubjectBindingRequest, TenantKeyIssue, TenantRegistration,
)
from .request_limits import HEADER_SOURCE
from .runtime import ServiceRuntime

HOST_CONFIGURATION_VERSION = "service_http_host_configuration/v1"
#: Every command this entry point accepts. The public help for
#: `loop-engine service` names the same set, and a check compares the two,
#: because a command the help names and the parser refuses fails only on the
#: day an operator needs it.
SERVICE_COMMANDS = ("serve", "configure", "apply-grants", "issue-key", "smoke", "failures",
                    "apply-billing-policy", "remove-expired")
LOOPBACK_BINDINGS = ("127.0.0.1", "::1", "localhost")
MANIFEST_VERSION = "host_attested_intelligence_manifest/v1"
ENVIRONMENT_REFERENCE_PREFIX = "env:"
LICENSE_POLICY_VERSION = "service_host_license_policy/v1"
LICENSE_POLICY_KEY = "license_policy"
#: The family policy mirrors the licence policy. The main line is
#: harness-first by owner direction (September 21, 2026): the default serves
#: the harness family alone. A host that serves more lists those exact
#: families. Unknown families, look-alike names and unsupported record
#: versions are refused before the manifest is read.
FAMILY_POLICY_VERSION = "service_host_family_policy/v1"
FAMILY_POLICY_KEY = "intelligence_family_policy"
#: The conservative default accepts the harness family alone. Loop-native and
#: Open Knowledge Format material stay in the library and in the checkpoint;
#: serving them is a host decision that names them, never a silent default.
DEFAULT_ACCEPTED_FAMILIES = ("harness",)
FAMILY_NOT_ACCEPTED = "item_family_not_accepted"
#: The conservative default accepts only the licence of this repository's own
#: material. A host that serves anything else lists that exact identifier.
DEFAULT_ACCEPTED_LICENSES = ("MIT",)
#: Values that a producer writes when no licence is known, or when a licence
#: still waits for review. They name a state, not a licence, so an item that
#: carries one is refused and no host list can accept one.
UNKNOWN_LICENSE_MARKERS = ("unknown", "noassertion", "none")
REVIEW_LICENSE_MARKERS = ("pending_review", "needs_review")
LICENSE_MISSING = "item_license_missing"
LICENSE_UNKNOWN = "item_license_unknown"
LICENSE_NEEDS_REVIEW = "item_license_needs_review"
LICENSE_NOT_ACCEPTED = "item_license_not_accepted"
#: An operator message shows at most this many characters of one manifest or
#: host value, so a large manifest or a long host list cannot make it large.
#: An item identity gets more room, so that the operator can look the refused
#: item up. The identity rule of this service, records.identifier, allows 128
#: characters, and an identity of that length is shown in full between its two
#: quotation marks. A manifest may carry a longer item identity, because an
#: item identity is only required to be nonempty; such an identity is shown
#: from its start.
PREVIEW_CHARACTERS = 80
IDENTITY_PREVIEW_CHARACTERS = 130


def _license_state(license_name):
    """Name the refusal state of a value that is not a licence name, or return empty text.

    A state is recognised in any letter case, with spaces around it, and with a
    hyphen or a space in place of the underscore, because recognising more
    states can only refuse more. It never makes a name acceptable.
    """
    if not isinstance(license_name, str) or not license_name.strip():
        return LICENSE_MISSING
    marker = license_name.strip().casefold().replace("-", "_").replace(" ", "_")
    if marker in UNKNOWN_LICENSE_MARKERS:
        return LICENSE_UNKNOWN
    return LICENSE_NEEDS_REVIEW if marker in REVIEW_LICENSE_MARKERS else ""


def _preview(value, limit=PREVIEW_CHARACTERS):
    """Return a short form of a manifest or host value for an operator message.

    Every character outside printable ASCII is shown as an escape sequence, so
    a hidden character or a letter of another script cannot pass for a name
    that it only looks like.
    """
    shown = ascii(value)
    return shown if len(shown) <= limit else shown[:limit - 3] + "..."


@dataclass(frozen=True)
class HostLicensePolicy:
    """The exact licence identifiers that one host accepts for the items it serves.

    Acceptance is host policy. An identifier is compared as written, so a name
    in another letter case or with added spaces is a different, unlisted name.
    A supplied list replaces the default list; it does not extend it. Every
    listed identifier is written in printable ASCII characters, so the person
    who reviews the host file sees each character of each name that the host
    accepts. A control or zero width character, a direction override and a
    letter of another script are refused. An item may still declare such a
    name; no host list can hold it, so that item is never accepted.
    """

    accepted_licenses: tuple[str, ...] = DEFAULT_ACCEPTED_LICENSES
    record_type: str = LICENSE_POLICY_VERSION

    def __post_init__(self):
        if self.record_type != LICENSE_POLICY_VERSION:
            raise ServiceRuntimeError("unsupported_license_policy",
                f"this release reads the host licence policy record {LICENSE_POLICY_VERSION} only")
        names = self.accepted_licenses
        if (type(names) not in (tuple, list) or any(
                not isinstance(name, str) or name != name.strip() or not (name.isascii() and name.isprintable())
                or _license_state(name) for name in names) or len(set(names)) != len(names)):
            raise ServiceRuntimeError("invalid_license_policy",
                "accepted licences are exact, distinct identifiers written in printable ASCII characters; "
                "a missing, unknown or review state is not a licence")
        object.__setattr__(self, "accepted_licenses", tuple(names))

    def refusal(self, license_name):
        """Return the stable refusal code for one item's licence, or empty text when this host accepts it."""
        return _license_state(license_name) or ("" if license_name in self.accepted_licenses else LICENSE_NOT_ACCEPTED)


DEFAULT_LICENSE_POLICY = HostLicensePolicy()


@dataclass(frozen=True)
class HostFamilyPolicy:
    """The exact intelligence families that one host serves.

    Mirrors the licence policy. A family is compared exactly as written, in
    printable ASCII; an unknown, look-alike or duplicated name is refused, and
    a supplied list replaces the default rather than extending it. The record
    version is checked, so an older release refuses a host file it does not
    understand. This is the extensibility toggle: adding a family later is a
    host configuration change here, never a code change or a silent serve.
    """

    accepted_families: tuple[str, ...] = DEFAULT_ACCEPTED_FAMILIES
    record_type: str = FAMILY_POLICY_VERSION

    def __post_init__(self):
        if self.record_type != FAMILY_POLICY_VERSION:
            raise ServiceRuntimeError("unsupported_family_policy",
                f"this release reads the host family policy record {FAMILY_POLICY_VERSION} only")
        from ..harness_intelligence import FAMILIES as KNOWN_FAMILIES
        names = self.accepted_families
        # A family is spelled exactly as the vocabulary declares it. A name
        # that differs only in case is a look-alike of a known family, and a
        # name no layer serves is unknown; both are refused here, so a host
        # that meant to serve one of them names it exactly instead of silently
        # serving nothing.
        folded = {name.casefold(): name for name in KNOWN_FAMILIES}
        def suspect(name):
            return isinstance(name, str) and (name not in KNOWN_FAMILIES
                                              or name.casefold() in folded and folded[name.casefold()] != name)
        if (type(names) not in (tuple, list) or not names or any(
                not isinstance(name, str) or name != name.strip() or not name
                or not (name.isascii() and name.isprintable())
                for name in names) or len(set(names)) != len(names)
                or any(suspect(name) for name in names)):
            raise ServiceRuntimeError("invalid_family_policy",
                "accepted families are exact, distinct, nonempty identifiers written in printable ASCII "
                "characters, and each names a family the library knows, spelled exactly as declared")
        object.__setattr__(self, "accepted_families", tuple(names))

    def refusal(self, family):
        """Return the stable refusal code for one item's family, or empty text when this host serves it."""
        return "" if family in self.accepted_families else FAMILY_NOT_ACCEPTED


DEFAULT_FAMILY_POLICY = HostFamilyPolicy()


def host_family_policy(configuration):
    """Return the family policy that a host configuration declares, or the conservative default."""
    if FAMILY_POLICY_KEY not in configuration:
        return DEFAULT_FAMILY_POLICY
    settings = configuration[FAMILY_POLICY_KEY]
    if not isinstance(settings, dict) or set(settings) != {field.name for field in dataclass_fields(HostFamilyPolicy)}:
        raise ServiceRuntimeError("unsupported_family_policy",
            "a host family policy names its record version and its accepted families, and nothing else")
    return HostFamilyPolicy(**settings)


def host_license_policy(configuration):
    """Return the licence policy that a host configuration declares, or the conservative default."""
    if LICENSE_POLICY_KEY not in configuration:
        return DEFAULT_LICENSE_POLICY
    settings = configuration[LICENSE_POLICY_KEY]
    if not isinstance(settings, dict) or set(settings) != {field.name for field in dataclass_fields(HostLicensePolicy)}:
        raise ServiceRuntimeError("unsupported_license_policy",
            "a host licence policy names its record version and its accepted licences, and nothing else")
    return HostLicensePolicy(**settings)


def observability_policy(configuration):
    """Return the observability policy a host declares, or the recording default.

    The default records metadata about refused requests and no request body.
    A host that wants request bodies names that choice, so capturing a private
    payload is always a written decision and never an accident.
    """
    if "observability" not in configuration:
        return ServiceObservabilityPolicy()
    settings = configuration["observability"]
    if not isinstance(settings, dict) or set(settings) - {field.name for field in dataclass_fields(ServiceObservabilityPolicy)}:
        raise ServiceRuntimeError("unsupported_observability_policy",
            "a host observability policy names only the fields of the declared policy record")
    return ServiceObservabilityPolicy(**settings)


def retention_policy(configuration):
    """Return the retention schedule a host declares, or the ten-minute default.

    There is no way to switch the removal off: the published privacy notice
    promises it. A host names only how often the periodic task runs.
    """
    from .retention import ServiceRetentionPolicy
    if "retention" not in configuration:
        return ServiceRetentionPolicy()
    settings = configuration["retention"]
    if not isinstance(settings, dict) or set(settings) - {field.name for field in dataclass_fields(ServiceRetentionPolicy)}:
        raise ServiceRuntimeError("unsupported_retention_policy",
            "a host retention policy names only the fields of the declared policy record")
    return ServiceRetentionPolicy(**settings)


def _host_json(path, *, maximum_bytes=2_000_000):
    selected = Path(path)
    if not selected.is_absolute() or selected.resolve() != selected or not selected.is_file():
        raise ServiceRuntimeError("invalid_configuration", "host files must be absolute regular files without symbolic links")
    if selected.stat().st_size > maximum_bytes:
        raise ServiceRuntimeError("configuration_too_large")
    return _parse_json(selected.read_bytes())


def load_host_manifest(path, *, license_policy=DEFAULT_LICENSE_POLICY, family_policy=DEFAULT_FAMILY_POLICY):
    """Load exact host attestations; catalogue tags cannot approve a source.

    An item is registered only when the host family policy serves the exact
    family the item's source layer belongs to and the host licence policy
    accepts the exact licence identifier that the item declares. The family
    refusal is decided first, so non-harness material is refused before its
    body or licence is touched. The conservative default policies apply when
    the caller supplies none.
    """
    if not isinstance(license_policy, HostLicensePolicy):
        raise ServiceRuntimeError("invalid_license_policy", "a typed host licence policy is required")
    if not isinstance(family_policy, HostFamilyPolicy):
        raise ServiceRuntimeError("invalid_family_policy", "a typed host family policy is required")
    manifest = _host_json(path)
    if set(manifest) != {"record_type", "artifact_root", "items"} or manifest["record_type"] != MANIFEST_VERSION:
        raise ServiceRuntimeError("unsupported_manifest")
    root = Path(manifest["artifact_root"])
    if not root.is_absolute() or root.resolve() != root or not root.is_dir():
        raise ServiceRuntimeError("invalid_artifact_root")
    if not isinstance(manifest["items"], list):
        raise ServiceRuntimeError("invalid_manifest")
    catalogue, reviews, paths, grants = HarnessIntelligenceCatalogue(), {}, {}, {}
    for row in manifest["items"]:
        if not isinstance(row, dict) or set(row) != {"reference", "body_path", "approval_ref", "grants"}:
            raise ServiceRuntimeError("invalid_manifest_item")
        item = _item(row["reference"])
        # The family refusal is decided first and for every row, before the
        # licence or the body is read, so non-harness material is never
        # registered, granted, opened or offered by a host that has not
        # declared it. The message names the item's family and what the host
        # serves, and is built from short previews only.
        refused_family = family_policy.refusal(item.family)
        if refused_family:
            raise ServiceRuntimeError(refused_family, f"{refused_family}: item {_preview(item.identity, IDENTITY_PREVIEW_CHARACTERS)} "
                f"serves the family {_preview(item.family)} and this host serves "
                f"{_preview(list(family_policy.accepted_families))} (listed families: "
                f"{len(family_policy.accepted_families)})")
        # Licence acceptance is decided for every row, with or without
        # grants, so the body of a refused item is never opened and the item is
        # never registered, granted or offered as starter material. The message
        # is built from short previews only, so its length has a fixed limit.
        refused = license_policy.refusal(item.license_name)
        if refused:
            accepted = license_policy.accepted_licenses
            raise ServiceRuntimeError(refused, f"{refused}: item {_preview(item.identity, IDENTITY_PREVIEW_CHARACTERS)} "
                f"is refused before registration; it declares the licence {_preview(item.license_name)} "
                f"and this host accepts {_preview(list(accepted))} (listed identifiers: {len(accepted)})")
        if item.identity in paths:
            raise ServiceRuntimeError("duplicate_item_identity")
        relative = Path(row["body_path"])
        target = root / relative
        if (relative.is_absolute() or ".." in relative.parts or target.resolve() != target
                or root not in target.parents or not target.is_file()):
            raise ServiceRuntimeError("unsafe_artifact_path")
        if not isinstance(row["approval_ref"], str) or not row["approval_ref"].strip():
            raise ServiceRuntimeError("explicit_host_review_required")
        if not isinstance(row["grants"], list):
            raise ServiceRuntimeError("invalid_manifest_grants")
        if target.stat().st_size != item.size_bytes:
            raise ServiceRuntimeError("artifact_size_mismatch")
        checksum = hashlib.sha256()
        with target.open("rb") as stream:
            for chunk in iter(lambda: stream.read(65_536), b""):
                checksum.update(chunk)
        if checksum.hexdigest() != item.digest:
            raise ServiceRuntimeError("artifact_digest_mismatch")
        catalogue.register(item)
        binding = ProvisioningItemBinding.from_item(item)
        reviews[item.identity] = ProvisioningQualification(binding, "approved", "host_attested", row["approval_ref"])
        paths[item.identity] = target
        for grant in row["grants"]:
            if not isinstance(grant, dict) or set(grant) != {"tenant_id", "body_allowed", "metering"}:
                raise ServiceRuntimeError("invalid_manifest_grant")
            grants.setdefault(grant["tenant_id"], []).append(ProvisioningGrant(binding=binding, **grant))
    def resolve(binding):
        decision = reviews.get(binding.identity)
        return decision if decision is not None and decision.binding == binding else ProvisioningQualification(
            binding, "unknown", "host_attested")
    def read(item):
        target = paths[item.identity]
        if target.resolve() != target or root not in target.parents or not target.is_file():
            raise ServiceRuntimeError("artifact_path_changed")
        if target.stat().st_size != item.size_bytes:
            raise ServiceRuntimeError("artifact_size_mismatch")
        return target.read_text(encoding="utf-8")
    return catalogue, ProvisioningQualificationResolver("host_manifest_review/v1", resolve), read, grants


def environment_secret(reference):
    """Resolve only an explicitly configured environment reference, without logging it."""
    if (not isinstance(reference, str) or not reference.startswith(ENVIRONMENT_REFERENCE_PREFIX)
            or not reference[len(ENVIRONMENT_REFERENCE_PREFIX):]):
        raise ServiceRuntimeError("unsupported_secret_resolver")
    value = os.environ.get(reference[len(ENVIRONMENT_REFERENCE_PREFIX):])
    if not value:
        raise ServiceRuntimeError("configured_secret_unavailable")
    return value


def signup_matches_the_browser_identity(settings, browser_identity):
    """True when account creation is open wherever public sign-up email is open."""
    return not settings.signup_enabled or (browser_identity.configuration.registration_enabled
                                           and browser_identity.configuration.email_signup_enabled)


def load_host_application(path):
    configuration = _host_json(path)
    allowed = {"record_type", "runtime", "http", "authentication", "manifest_path", "tenants", "billing", "administration",
               "browser_identity", "client_access", "promotions", "account_email", "observability", "waitlist",
               "retention", LICENSE_POLICY_KEY, FAMILY_POLICY_KEY}
    if (configuration.get("record_type") != HOST_CONFIGURATION_VERSION or set(configuration) - allowed
            or not {"runtime", "http", "authentication", "manifest_path"} <= set(configuration)):
        raise ServiceRuntimeError("unsupported_host_configuration")
    license_policy = host_license_policy(configuration)
    family_policy = host_family_policy(configuration)
    runtime = ServiceRuntime(ServiceRuntimeConfig(**configuration["runtime"]))
    catalogue, resolver, body_reader, _grants = load_host_manifest(configuration["manifest_path"], license_policy=license_policy, family_policy=family_policy)
    binding = DurableProvisioningBinding(runtime, catalogue, resolver, body_reader)
    browser_identity = None
    if configuration.get("browser_identity"):
        from .browser_identity import BrowserIdentityAdapter, BrowserIdentityConfiguration
        settings = dict(configuration["browser_identity"])
        identities = settings.pop("starter_identities", [])
        if (not isinstance(identities, list) or len(identities) != len(set(identities))
                or any(identity not in catalogue.items for identity in identities)):
            raise ServiceRuntimeError("invalid_starter_identities")
        browser_identity = BrowserIdentityAdapter(runtime, BrowserIdentityConfiguration(**settings),
            environment_secret, starter_bindings=tuple(ProvisioningItemBinding.from_item(catalogue.items[identity]) for identity in identities))
    client_access = None
    if configuration.get("client_access"):
        from .access import ServiceAccessAdministration, ServiceClientAccessPolicy
        client_access = ServiceAccessAdministration(runtime, ServiceClientAccessPolicy(**configuration["client_access"]))
    promotions = None
    if configuration.get("promotions"):
        from .promotions import PromotionPolicy, PromotionRedemption
        promotions = PromotionRedemption(runtime, PromotionPolicy(**configuration["promotions"]))
    waitlist = None
    if configuration.get("waitlist"):
        from .waitlist import ServiceWaitlist, WaitlistPolicy
        # The flood guard keys its source digest with a host secret named by
        # an environment reference, resolved at use like every other secret.
        waitlist = ServiceWaitlist(runtime, WaitlistPolicy(**configuration["waitlist"]),
                                   secret_resolver=environment_secret)
    transport = ServiceHttpConfiguration(**configuration["http"])
    account_email = None
    if configuration.get("account_email"):
        from .account_email import AccountEmailAdapter, AccountEmailConfiguration
        settings = AccountEmailConfiguration.from_host(configuration["account_email"])
        # Sign-up and recovery finish at the browser identity routes, and both
        # must speak to the same identity project. Without that the confirmed
        # address could never be exchanged for an account of this service.
        if browser_identity is None:
            raise ServiceRuntimeError("account_email_requires_browser_identity")
        if settings.identity_origin != browser_identity.configuration.project_url:
            raise ServiceRuntimeError("account_email_identity_origin_mismatch")
        # Sign-up ends at `POST /api/v1/account/activate`, which refuses while
        # account creation is closed. Opening sign-up against a closed browser
        # identity would confirm an address at the identity provider and then
        # leave the person with no account of this service and no record, so
        # the host file is refused instead. Recovery is not refused here: a
        # person who already has an account may need a new password while
        # account creation stays closed, which is the private beta state.
        if not signup_matches_the_browser_identity(settings, browser_identity):
            raise ServiceRuntimeError("account_email_signup_needs_open_registration",
                "account_email.signup_enabled requires browser_identity.registration_enabled and "
                "browser_identity.email_signup_enabled, because sign-up finishes at account activation")
        account_email = AccountEmailAdapter(settings, environment_secret,
            public_base_url=transport.public_base_url, address_limits=transport.request_limits,
            display_name=transport.display_name)
    # The adapter is installed through the constructor, so that the declared
    # `account_email/v1` boundary is validated before the application exists.
    application = ServiceHttpApplication(runtime, binding, transport,
        ServiceHttpAuthentication(**configuration["authentication"]), browser_identity=browser_identity,
        client_access=client_access, promotions=promotions, account_email=account_email, waitlist=waitlist,
        observability=observability_policy(configuration), retention=retention_policy(configuration))
    if configuration.get("administration"):
        from .access import ServiceAccessAdministration, ServiceAccessPolicy
        application.access_administration = ServiceAccessAdministration(runtime, ServiceAccessPolicy(**configuration["administration"]))
    if configuration.get("billing"):
        from .billing import StripeEventProcessor
        from .billing_records import StripeWebhookConfig, StripeEntitlementPolicy, StripeProviderConfig
        settings = configuration["billing"]
        if set(settings) - {"webhook", "policy", "provider", "sessions"} or not {"webhook", "policy"} <= set(settings):
            raise ServiceRuntimeError("unsupported_billing_configuration")
        subscription_resolver = None
        if settings.get("provider"):
            from .stripe_provider import StripeSubscriptionReader
            subscription_resolver = StripeSubscriptionReader(
                StripeProviderConfig(**settings["provider"]), environment_secret).as_resolver()
        application.billing_processor = StripeEventProcessor(runtime, StripeWebhookConfig(**settings["webhook"]),
            StripeEntitlementPolicy(**settings["policy"]), environment_secret,
            subscription_resolver=subscription_resolver)
        if settings.get("sessions"):
            from .stripe_sessions import StripeSessionAdapter, StripeSessionConfiguration, StripeSessionPlan
            session_settings = dict(settings["sessions"])
            session_settings["plans"] = tuple(StripeSessionPlan(**row) for row in session_settings.get("plans", ()))
            application.billing_sessions = StripeSessionAdapter(runtime, StripeSessionConfiguration(**session_settings), environment_secret)
    return application, configuration


def configure_host(path):
    """Explicit one-time local tenant/grant setup, never a serving side effect."""
    application, configuration = load_host_application(path)
    tenants = configuration.get("tenants", [])
    if not isinstance(tenants, list):
        raise ServiceRuntimeError("invalid_tenant_configuration")
    for row in tenants:
        if not isinstance(row, dict) or set(row) - {"tenant_id", "namespace", "scopes", "subjects", "operator_entitlement", "billing_customer"}:
            raise ServiceRuntimeError("invalid_tenant_configuration")
        application.runtime.register_tenant(TenantRegistration(**{
            key: row[key] for key in ("tenant_id", "namespace", "scopes") if key in row}))
        for subject in row.get("subjects", []):
            if set(subject) != {"issuer", "subject"}:
                raise ServiceRuntimeError("invalid_subject_binding")
            application.runtime.bind_subject(SubjectBindingRequest(row["tenant_id"], **subject))
        if row.get("operator_entitlement"):
            application.runtime.set_operator_entitlement(row["tenant_id"], **row["operator_entitlement"])
        if row.get("billing_customer"):
            application.runtime.bind_billing_customer(BillingCustomerBindingRequest(row["tenant_id"], **row["billing_customer"]))
    _catalogue, _resolver, _reader, grants = load_host_manifest(
        configuration["manifest_path"], license_policy=host_license_policy(configuration),
        family_policy=host_family_policy(configuration))
    for tenant, selected in grants.items():
        application.runtime.set_grants(tenant, tuple(selected))
    if configuration.get("billing"):
        from .billing_records import StripeEntitlementPolicy
        application.runtime.configure_billing_policy(StripeEntitlementPolicy(**configuration["billing"]["policy"]))
        if application.billing_sessions is not None:
            application.billing_sessions.configure_policy()
    return {"record_type": "service_host_setup/v1", "tenants": [row["tenant_id"] for row in tenants],
            "configured_grant_sets": len(grants), "remote_accounts_created": False}


def apply_host_grants(path):
    """Explicit one-time application of the manifest's disclosure grants to existing tenants.

    A release that carries a new host manifest changes which items the host may
    disclose. Tenant registration is a separate, earlier setup step that this
    operation never repeats, so an existing deployment can take a new manifest
    without re-registering anything. Every tenant named in the grants must
    already exist, the grant set for that tenant is replaced by exactly what the
    manifest declares, and no tenant the manifest does not name is touched.
    """
    _application, configuration = load_host_application(path)
    runtime = ServiceRuntime(ServiceRuntimeConfig(**configuration["runtime"]))
    _catalogue, _resolver, _reader, grants = load_host_manifest(
        configuration["manifest_path"], license_policy=host_license_policy(configuration),
        family_policy=host_family_policy(configuration))
    applied = {tenant: runtime.set_grants(tenant, tuple(selected))["grants"]
               for tenant, selected in sorted(grants.items())}
    return {"record_type": "service_host_grant_application/v1", "manifest_path": configuration["manifest_path"],
            "granted_items_by_tenant": applied, "tenants_registered": 0, "remote_accounts_created": False}


def public_binding_refusal(host, behind_trusted_tls_proxy, request_limits):
    """Name why this binding may not serve the public, or return empty text.

    A service that anyone on the internet can reach must count refused
    sign-in attempts, and it can only count them when the host has said where
    the client address comes from. Behind a trusted proxy the socket peer is
    the proxy, so every caller in the world would share one count; that host
    names the exact header its own proxy writes on every request. A loopback
    binding serves only this machine, so it needs no such statement.

    This refusal exists because the setting has a safe-looking default. A host
    that says nothing gets no limit at all, and nothing else in a running
    service says so out loud. Being stopped at start with the exact repair is
    better than serving paying customers with the control switched off.
    """
    if host in LOOPBACK_BINDINGS:
        return ""
    if not behind_trusted_tls_proxy:
        return "non-loopback binding requires --behind-trusted-tls-proxy"
    if request_limits.client_address_source != HEADER_SOURCE:
        return ('a binding the public can reach must count refused sign-in attempts for each client '
                'address; add "request_limits": {"record_type": "service_request_limits/v1", '
                '"client_address_source": "header", "client_address_header": "<the exact header your '
                'trusted proxy writes on every request>"} to the "http" section of the host '
                'configuration, or bind to loopback for local work')
    return ""


def read_failures(path, *, limit=20, tenant=None, reference=None):
    """Read the durable failure journal of one host. This never writes.

    It builds the journal directly from the host configuration instead of
    starting the application, so an operator can read the records of a service
    that is refusing every request, or of one that is not running at all. The
    store is opened for reading only; no command here can change a record.
    """
    from .observability import ServiceFailureJournal
    from .http import DECLARED_ROUTES
    configuration = _host_json(path)
    if configuration.get("record_type") != HOST_CONFIGURATION_VERSION or "runtime" not in configuration:
        raise ServiceRuntimeError("unsupported_host_configuration")
    if reference is not None and tenant is not None:
        raise ServiceRuntimeError("invalid_request", "ask for one reference or for one tenant, not both")
    # The journal is opened with host writes withheld, so this command cannot
    # write even if a future change tried to. Reading needs no write authority.
    settings = {**configuration["runtime"], "writes_authorized": False}
    journal = ServiceFailureJournal(ServiceRuntimeConfig(**settings), DECLARED_ROUTES,
                                    policy=observability_policy(configuration))
    if reference is not None:
        return journal.detail(reference)
    return journal.recent(limit=limit, tenant_id=tenant)


def remove_expired_records(path):
    """Run every retention removal once, by hand, and return outcomes and counts only.

    Like `failures`, it reads only the runtime and waiting list blocks of the
    host configuration and starts no server, so it works while the service is
    down. It needs the host write authority the runtime block grants. It
    prints no digest, no record identity and no tenant.
    """
    from .retention import sweep_retention
    configuration = _host_json(path)
    if configuration.get("record_type") != HOST_CONFIGURATION_VERSION or "runtime" not in configuration:
        raise ServiceRuntimeError("unsupported_host_configuration")
    runtime = ServiceRuntime(ServiceRuntimeConfig(**configuration["runtime"]))
    waitlist = None
    if configuration.get("waitlist"):
        from .waitlist import ServiceWaitlist, WaitlistPolicy
        waitlist = ServiceWaitlist(runtime, WaitlistPolicy(**configuration["waitlist"]),
                                   secret_resolver=environment_secret)
    return sweep_retention(runtime, waitlist=waitlist)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Serve the versioned Loop Engine intelligence service.")
    parser.add_argument("command", choices=SERVICE_COMMANDS)
    parser.add_argument("--config", help="Absolute host configuration file; never supplied by a remote request.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--behind-trusted-tls-proxy", action="store_true")
    parser.add_argument("--tenant")
    parser.add_argument("--label", default="host-issued client key")
    parser.add_argument("--expires-at", type=int)
    parser.add_argument("--limit", type=int, default=20,
                        help="failures: how many of the newest records to show.")
    parser.add_argument("--reference",
                        help="failures: the request reference a customer read out of a refusal.")
    parser.add_argument("--reset-paid-access", action="store_true",
                        help="apply-billing-policy: apply a changed entitlement policy although accounts "
                             "with paid access under the held one lose it until their next subscription event.")
    from .records import SCOPES
    parser.add_argument("--scope", action="append", choices=SCOPES,
                        help="Repeat to narrow issued-key scopes; billing requires an explicit billing:manage grant.")
    arguments = parser.parse_args(argv)
    if arguments.command == "smoke":
        from .http_checks import self_test
        result = self_test()
        print(json.dumps(result, sort_keys=True))
        return 0 if result.get("all_passed") is True else 1
    if not arguments.config:
        parser.error("--config is required")
    if arguments.command == "configure":
        print(json.dumps(configure_host(arguments.config), sort_keys=True))
        return 0
    if arguments.command == "apply-grants":
        print(json.dumps(apply_host_grants(arguments.config), sort_keys=True))
        return 0
    if arguments.command == "apply-billing-policy":
        from .billing_policy import run_command
        return run_command(arguments.config, reset_paid_access=arguments.reset_paid_access)
    if arguments.command == "remove-expired":
        from .retention import COMPLETED
        report = remove_expired_records(arguments.config)
        print(json.dumps(report, sort_keys=True))
        return 0 if report["outcome"] == COMPLETED else 1
    if arguments.command == "failures":
        # A read-only operator view. It loads no manifest, starts no server and
        # opens no provider connection, so it answers while the service is down.
        print(json.dumps(read_failures(arguments.config, limit=arguments.limit,
                                       tenant=arguments.tenant, reference=arguments.reference),
                         sort_keys=True))
        return 0
    application, _configuration = load_host_application(arguments.config)
    if arguments.command == "issue-key":
        if not arguments.tenant:
            parser.error("--tenant is required for key issuance")
        fields = {"scopes": tuple(arguments.scope)} if arguments.scope is not None else {}
        issued = application.runtime.issue_key(TenantKeyIssue(arguments.tenant, arguments.label, arguments.expires_at, **fields))
        # This operator command displays the newly issued credential once.
        # The runtime persists only its digest; callers must not log stdout.
        print(json.dumps({"record_type": "issued_service_key/v1", **asdict(issued)}, sort_keys=True))
        return 0
    refusal = public_binding_refusal(arguments.host, arguments.behind_trusted_tls_proxy,
                                     application.configuration.request_limits)
    if refusal:
        parser.error(refusal)
    if not 1 <= arguments.port <= 65535:
        parser.error("--port must be between one and 65535")
    import uvicorn
    uvicorn.run(application.create_app(), host=arguments.host, port=arguments.port,
                proxy_headers=False, access_log=False,
                limit_concurrency=application.configuration.maximum_concurrent_operations * 4)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
