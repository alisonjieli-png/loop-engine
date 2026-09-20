"""Executable host-configured intelligence service, with no dynamic code loading.

Configuration names a durable store and exact host-reviewed artifact manifest.
Serving does not create tenants or restore revoked grants. Host setup and key
issuance are separate explicit commands; no cloud account is created here.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
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
from .provisioning import DurableProvisioningBinding
from .records import (
    BillingCustomerBindingRequest, ServiceRuntimeConfig, ServiceRuntimeError,
    SubjectBindingRequest, TenantKeyIssue, TenantRegistration,
)
from .runtime import ServiceRuntime

HOST_CONFIGURATION_VERSION = "service_http_host_configuration/v1"
MANIFEST_VERSION = "host_attested_intelligence_manifest/v1"
ENVIRONMENT_REFERENCE_PREFIX = "env:"


def _host_json(path, *, maximum_bytes=2_000_000):
    selected = Path(path)
    if not selected.is_absolute() or selected.resolve() != selected or not selected.is_file():
        raise ServiceRuntimeError("invalid_configuration", "host files must be absolute regular files without symbolic links")
    if selected.stat().st_size > maximum_bytes:
        raise ServiceRuntimeError("configuration_too_large")
    return _parse_json(selected.read_bytes())


def load_host_manifest(path):
    """Load exact host attestations; catalogue tags cannot approve a source."""
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


def load_host_application(path):
    configuration = _host_json(path)
    allowed = {"record_type", "runtime", "http", "authentication", "manifest_path", "tenants", "billing", "administration", "browser_identity", "client_access"}
    if (configuration.get("record_type") != HOST_CONFIGURATION_VERSION or set(configuration) - allowed
            or not {"runtime", "http", "authentication", "manifest_path"} <= set(configuration)):
        raise ServiceRuntimeError("unsupported_host_configuration")
    runtime = ServiceRuntime(ServiceRuntimeConfig(**configuration["runtime"]))
    catalogue, resolver, body_reader, _grants = load_host_manifest(configuration["manifest_path"])
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
    application = ServiceHttpApplication(runtime, binding, ServiceHttpConfiguration(**configuration["http"]),
        ServiceHttpAuthentication(**configuration["authentication"]), browser_identity=browser_identity, client_access=client_access)
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
    _catalogue, _resolver, _reader, grants = load_host_manifest(configuration["manifest_path"])
    for tenant, selected in grants.items():
        application.runtime.set_grants(tenant, tuple(selected))
    if configuration.get("billing"):
        from .billing_records import StripeEntitlementPolicy
        application.runtime.configure_billing_policy(StripeEntitlementPolicy(**configuration["billing"]["policy"]))
        if application.billing_sessions is not None:
            application.billing_sessions.configure_policy()
    return {"record_type": "service_host_setup/v1", "tenants": [row["tenant_id"] for row in tenants],
            "configured_grant_sets": len(grants), "remote_accounts_created": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Serve the versioned Loop Engine intelligence service.")
    parser.add_argument("command", choices=("serve", "configure", "issue-key", "smoke"))
    parser.add_argument("--config", help="Absolute host configuration file; never supplied by a remote request.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--behind-trusted-tls-proxy", action="store_true")
    parser.add_argument("--tenant")
    parser.add_argument("--label", default="host-issued client key")
    parser.add_argument("--expires-at", type=int)
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
    if arguments.host not in ("127.0.0.1", "::1", "localhost") and not arguments.behind_trusted_tls_proxy:
        parser.error("non-loopback binding requires --behind-trusted-tls-proxy")
    if not 1 <= arguments.port <= 65535:
        parser.error("--port must be between one and 65535")
    import uvicorn
    uvicorn.run(application.create_app(), host=arguments.host, port=arguments.port,
                proxy_headers=False, access_log=False,
                limit_concurrency=application.configuration.maximum_concurrent_operations * 4)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
