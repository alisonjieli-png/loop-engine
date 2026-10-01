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
    ACCOUNT_GRANT_RECORD_TYPE, GRANT_RECORD_TYPE, METERING_POLICIES, ProvisioningAccessPolicy, ProvisioningError, ProvisioningMeterRefusal, ProvisioningQualificationResolver,
    ProvisioningRequest, ProvisioningServer, ProvisioningTenant, ProvisioningTenantResolver,
)
from ..service_api import key_digest
from .records import ServiceCommitUnknown, ServiceRuntimeError
from .runtime import (PROVISIONING_METADATA_SCOPE, PROVISIONING_READ_SCOPE, ServiceRuntime)

_AUTOMATIC_PUBLIC_GOOD_RESERVATION = object()


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
        from .public_good import PublicGoodAccess
        self._public_good = PublicGoodAccess(runtime)

    @property
    def public_good(self):
        """Keep this domain adapter bound when a host replaces the runtime."""
        if self._public_good.runtime is not self.runtime:
            from .public_good import PublicGoodAccess
            self._public_good = PublicGoodAccess(self.runtime)
        return self._public_good

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
                             public_good_reservation=_AUTOMATIC_PUBLIC_GOOD_RESERVATION, **fields):
        view = view if view is not None else self._view
        transport_reserved = public_good_reservation is not _AUTOMATIC_PUBLIC_GOOD_RESERVATION
        if not transport_reserved:
            public_good_reservation = None
        from .public_good import PublicGoodReservation
        if public_good_reservation is not None and not isinstance(public_good_reservation, PublicGoodReservation):
            raise ServiceRuntimeError("public_good_reservation_invalid")
        if expected_digest is not None and (operation not in ("manifest", "read")
                or not isinstance(expected_digest, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_digest)):
            raise ServiceRuntimeError("invalid_selected_digest")
        if candidates is not None and operation != "list":
            raise ServiceRuntimeError("invalid_request", "only a listing can be narrowed to search candidates")
        if public_good_reservation is not None and operation != "read":
            raise ServiceRuntimeError("public_good_reservation_invalid")
        current = self.runtime.revalidate(principal)
        required = PROVISIONING_READ_SCOPE if operation == "read" else PROVISIONING_METADATA_SCOPE
        if required not in current.scopes:
            raise ServiceRuntimeError("scope_required")
        grants, grant_guard = self.runtime.grant_snapshot(current)
        if not isinstance(grants, tuple):
            # A release-following account is resolved against the view this
            # request captured, never against a later one.
            grants = grants.materialize(view, candidates)
        if any(grant.record_type != GRANT_RECORD_TYPE for grant in grants):
            raise ServiceRuntimeError("public_good_requires_exact_policy")
        grants, public_good_token = self.public_good.overlay(current, view, grants, candidates=candidates)
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
                           or grant.record_type == ACCOUNT_GRANT_RECORD_TYPE
                           else grant for grant in grants)
        selected_public_good = next((grant for grant in grants if grant.record_type == ACCOUNT_GRANT_RECORD_TYPE
                                     and grant.binding.identity == fields.get("identity")), None)
        automatic_reservation = False
        if operation == "read" and selected_public_good is not None:
            if public_good_reservation is None:
                if transport_reserved:
                    # The transport chose ordinary access before a new free policy appeared.
                    # It must plan its full response budget again, never silently reserve less.
                    raise ServiceRuntimeError("public_good_authority_changed")
                item = view.catalogue.items[selected_public_good.binding.identity]
                public_good_reservation = self.public_good.reserve(current, view, item.identity,
                    expected_digest=expected_digest or item.digest, request_id=fields.get("request_id", ""),
                    response_bytes=item.size_bytes)
                automatic_reservation = True
            if public_good_reservation is None:
                raise ServiceRuntimeError("public_good_authority_changed")
            from .records import digest
            if (public_good_reservation.grant.binding != selected_public_good.binding
                    or public_good_reservation.request_id_digest != digest(fields.get("request_id", ""))):
                raise ServiceRuntimeError("public_good_reservation_invalid")
            self.public_good.revalidate(public_good_reservation, current, view)
        elif public_good_reservation is not None:
            raise ServiceRuntimeError("public_good_reservation_invalid")
        internal_key = secrets.token_urlsafe(32)
        held_digest = key_digest(internal_key)

        def resolve_tenant(supplied):
            if not isinstance(supplied, str) or not hmac.compare_digest(supplied, internal_key):
                raise ServiceRuntimeError("unauthorized")
            try:
                latest = self.runtime.revalidate(current)
                if required not in latest.scopes:
                    raise ServiceRuntimeError("scope_required")
                _grants, observed = self.runtime.grant_snapshot(latest)
                if observed != grant_guard:
                    raise ServiceRuntimeError("disclosure_grant_changed")
                refreshed = _grants if isinstance(_grants, tuple) else _grants.materialize(view, candidates)
                _effective, latest_public_good = self.public_good.overlay(latest, view, refreshed, candidates=candidates)
                if latest_public_good != public_good_token:
                    raise ServiceRuntimeError("public_good_authority_changed")
                if public_good_reservation is not None:
                    self.public_good.revalidate(public_good_reservation, latest, view)
            except ServiceRuntimeError as refusal:
                raise ProvisioningError("the durable tenant resolver refused this request", refusal.code) from None
            return ProvisioningTenant(latest.tenant_id, held_digest, latest.entitlement)

        tenant = resolve_tenant(internal_key)
        def selected_qualification(binding):
            if expected_digest is not None and binding.body_digest != expected_digest:
                raise ServiceRuntimeError("selected_body_digest_mismatch")
            return view.qualification_resolver.resolve(binding)

        qualifier = ProvisioningQualificationResolver(
            view.qualification_resolver.resolver_id + ":selected", selected_qualification)
        def measure(request):
            """Keep a definite refusal from the durable meter apart from an unknown commitment.

            The runtime states an unknown durable outcome in one typed way, `ServiceCommitUnknown`, and
            `record_usage` turns it into an acknowledgment whose commitment is unknown. Every other refusal it raises
            is definite: nothing was recorded. Those keep their own code, so the customer is told what happened and
            whether to retry, instead of being told that the outcome is unknown."""
            try:
                return self.runtime.record_usage(request, current, guards=(grant_guard,))
            except ServiceCommitUnknown:
                raise
            except ServiceRuntimeError as refusal:
                raise ProvisioningMeterRefusal("the durable meter refused this measured unit", refusal.code) from None

        policy = ProvisioningAccessPolicy(grants, qualifier)
        server = ProvisioningServer(catalogue, (tenant,), view.body_reader, measure,
            access_policy=policy,
            tenant_resolver=ProvisioningTenantResolver("durable_service_tenant", resolve_tenant))
        result = server.handle(ProvisioningRequest(operation, internal_key, **fields))
        if automatic_reservation:
            self.public_good.complete(public_good_reservation, current, view,
                                      response_bytes=len(result["body"].encode("utf-8")))
        return result
