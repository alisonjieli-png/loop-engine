"""Bind current durable service authority to the existing provisioning server.

Each request gets a short-lived internal credential, an exact durable grant
snapshot, current principal revalidation, and the existing qualification
resolver. No incoming token can install a body reader or disclosure policy.

The catalogue, resolver, body reader and search index come from one immutable
view. A request captures the view once and finishes on it, and only the host's
catalogue refresher installs a new view, with one assignment, so no request
ever mixes two catalogues.
"""
from __future__ import annotations

from dataclasses import replace
import hmac
import re
import secrets

from ..harness_intelligence import HarnessIntelligenceCatalogue
from ..provisioning_server import (
    METERING_POLICIES, ProvisioningAccessPolicy, ProvisioningQualificationResolver,
    ProvisioningRequest, ProvisioningServer, ProvisioningTenant, ProvisioningTenantResolver,
)
from ..service_api import key_digest
from .records import ServiceRuntimeError
from .runtime import (PROVISIONING_METADATA_SCOPE, PROVISIONING_READ_SCOPE, ServiceRuntime)


class DurableProvisioningBinding:
    """A host binding; runtime service records remain the sole tenant-grant authority."""

    def __init__(self, runtime: ServiceRuntime, catalogue: HarnessIntelligenceCatalogue,
                 qualification_resolver: ProvisioningQualificationResolver, body_reader, *, view=None):
        from .catalogue_serving import CatalogueView
        if (not isinstance(runtime, ServiceRuntime) or not isinstance(catalogue, HarnessIntelligenceCatalogue)
                or not isinstance(qualification_resolver, ProvisioningQualificationResolver)
                or (body_reader is not None and not callable(body_reader))):
            raise ServiceRuntimeError("invalid_provisioning_binding")
        if view is None:
            view = CatalogueView(catalogue, qualification_resolver, body_reader)
        elif (not isinstance(view, CatalogueView) or view.catalogue is not catalogue
              or view.qualification_resolver is not qualification_resolver or view.body_reader is not body_reader):
            raise ServiceRuntimeError("invalid_provisioning_binding")
        self.runtime = runtime
        self._view = view

    @property
    def catalogue(self):
        return self._view.catalogue

    @property
    def qualification_resolver(self):
        return self._view.qualification_resolver

    @property
    def body_reader(self):
        return self._view.body_reader

    @body_reader.setter
    def body_reader(self, reader):
        """Host-only replacement of the body reader, installed as a new view like any other change."""
        if reader is not None and not callable(reader):
            raise ServiceRuntimeError("invalid_provisioning_binding")
        self._view = replace(self._view, body_reader=reader, _lazy={})

    def current_view(self):
        """The view a request captures once and finishes on."""
        return self._view

    def install_view(self, view):
        """Host-only replacement of the served catalogue, as one assignment."""
        from .catalogue_serving import CatalogueView
        if not isinstance(view, CatalogueView) or view.body_reader is not None and not callable(view.body_reader):
            raise ServiceRuntimeError("invalid_provisioning_binding")
        self._view = view

    def invoke(self, raw_key: str, operation: str, **fields):
        return self.invoke_for_principal(self.runtime.authenticate_key(raw_key), operation, **fields)

    def invoke_for_principal(self, principal, operation: str, *, expected_digest=None, view=None, candidates=None,
                             **fields):
        view = view if view is not None else self._view
        if expected_digest is not None and (operation not in ("manifest", "read")
                or not isinstance(expected_digest, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_digest)):
            raise ServiceRuntimeError("invalid_selected_digest")
        if candidates is not None and operation != "list":
            raise ServiceRuntimeError("invalid_request", "only a listing can be narrowed to search candidates")
        current = self.runtime.revalidate(principal)
        required = PROVISIONING_READ_SCOPE if operation == "read" else PROVISIONING_METADATA_SCOPE
        if required not in current.scopes:
            raise ServiceRuntimeError("scope_required")
        grants, grant_guard = self.runtime.grant_snapshot(current)
        if not isinstance(grants, tuple):
            # A release-following account is resolved against the view this
            # request captured, never against a later one.
            grants = grants.materialize(view, candidates)
        catalogue = view.catalogue
        if candidates is not None:
            chosen = set(candidates)
            catalogue = HarnessIntelligenceCatalogue({identity: view.catalogue.items[identity] for identity in chosen
                                                      if identity in view.catalogue.items})
            grants = tuple(grant for grant in grants if grant.binding.identity in chosen)
        if operation in ("manifest", "read") and view.withdrawal_check is not None:
            item = view.catalogue.items.get(fields.get("identity"))
            if item is not None:
                view.withdrawal_check(item.identity, item.digest)
        if PROVISIONING_READ_SCOPE not in current.scopes:
            grants = tuple(replace(grant, body_allowed=False) for grant in grants)
        if self.runtime.config.writes_authorized is not True:
            grants = tuple(replace(grant, body_allowed=False) if grant.metering == METERING_POLICIES[0]
                           else grant for grant in grants)
        internal_key = secrets.token_urlsafe(32)
        held_digest = key_digest(internal_key)

        def resolve_tenant(supplied):
            if not isinstance(supplied, str) or not hmac.compare_digest(supplied, internal_key):
                raise ServiceRuntimeError("unauthorized")
            latest = self.runtime.revalidate(current)
            if required not in latest.scopes:
                raise ServiceRuntimeError("scope_required")
            _grants, observed = self.runtime.grant_snapshot(latest)
            if observed != grant_guard:
                raise ServiceRuntimeError("disclosure_grant_changed")
            return ProvisioningTenant(latest.tenant_id, held_digest, latest.entitlement)

        tenant = resolve_tenant(internal_key)
        def selected_qualification(binding):
            if expected_digest is not None and binding.body_digest != expected_digest:
                raise ServiceRuntimeError("selected_body_digest_mismatch")
            return view.qualification_resolver.resolve(binding)

        qualifier = ProvisioningQualificationResolver(
            view.qualification_resolver.resolver_id + ":selected", selected_qualification)
        policy = ProvisioningAccessPolicy(grants, qualifier)
        server = ProvisioningServer(catalogue, (tenant,), view.body_reader,
            lambda request: self.runtime.record_usage(request, current, guards=(grant_guard,)),
            access_policy=policy,
            tenant_resolver=ProvisioningTenantResolver("durable_service_tenant", resolve_tenant))
        return server.handle(ProvisioningRequest(operation, internal_key, **fields))
