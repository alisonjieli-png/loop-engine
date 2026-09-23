"""Grants that follow the active catalogue release, beside the existing snapshot grants.

An account's grants record now has two engines, told apart by its record
version. Version 1 is the existing snapshot: an exact list of item bindings
that changes only when an operator applies new grants. Version 2 follows the
active release: the account receives every approved item of the release being
served, minus the identities it explicitly denies, so a newly published item
reaches the account without `apply-grants`. Items that declare effects are
still withheld until the client declares them, exactly as for a snapshot,
because the effect filter runs after the grant.

A release older than this one reads version 1 only, so it refuses a version 2
record instead of honouring a record whose rules it does not know.
"""
from __future__ import annotations

from dataclasses import dataclass
import time

from ..provisioning_server import METERING_POLICIES, ProvisioningGrant
from .records import ServiceRuntimeError, identifier

FOLLOW_RELEASE_GRANTS_VERSION = "service_grants/v2"
FOLLOW_ACTIVE_RELEASE = "follow_active_release"
GRANT_ENGINE_RESULT_VERSION = "service_catalogue_grant_engine/v1"
MAXIMUM_DENIALS = 10_000


def release_following_payload(tenant_id, denials=(), *, body_allowed=True, metering=METERING_POLICIES[0]):
    """The version 2 grants record of one account."""
    denials = tuple(denials)
    if (len(denials) > MAXIMUM_DENIALS or len(set(denials)) != len(denials)
            or any(not isinstance(value, str) or not value for value in denials)):
        raise ServiceRuntimeError("invalid_disclosure_grant", "denials are distinct item identities")
    if type(body_allowed) is not bool or metering not in METERING_POLICIES:
        raise ServiceRuntimeError("invalid_disclosure_grant", "body and metering policies are explicit")
    return {"record_type": FOLLOW_RELEASE_GRANTS_VERSION, "tenant_id": tenant_id, "engine": FOLLOW_ACTIVE_RELEASE,
            "denials": sorted(denials), "body_allowed": body_allowed, "metering": metering}


@dataclass(frozen=True)
class ReleaseFollowingGrants:
    """The grants of one account under the release-following engine, resolved against one view."""

    tenant_id: str
    denials: frozenset
    body_allowed: bool = True
    metering: str = METERING_POLICIES[0]

    def materialize(self, view, candidates=None):
        """Return exact grants for the approved items of `view`, optionally only for `candidates`."""
        approved = view.approved_bindings()
        chosen = approved if candidates is None else {identity: approved[identity] for identity in candidates
                                                      if identity in approved}
        return tuple(ProvisioningGrant(self.tenant_id, binding, self.body_allowed, self.metering)
                     for identity, binding in chosen.items() if identity not in self.denials)

    def count(self, view):
        return sum(1 for identity in view.approved_bindings() if identity not in self.denials)


def release_following_grants(payload, tenant_id):
    """Read a version 2 grants record exactly, refusing any other shape."""
    if (not isinstance(payload, dict)
            or set(payload) != {"record_type", "tenant_id", "engine", "denials", "body_allowed", "metering"}
            or payload["record_type"] != FOLLOW_RELEASE_GRANTS_VERSION or payload["engine"] != FOLLOW_ACTIVE_RELEASE
            or payload["tenant_id"] != tenant_id or not isinstance(payload["denials"], list)):
        raise ServiceRuntimeError("invalid_disclosure_grant", "a release-following grants record has an exact shape")
    checked = release_following_payload(tenant_id, payload["denials"], body_allowed=payload["body_allowed"],
                                        metering=payload["metering"])
    return ReleaseFollowingGrants(tenant_id, frozenset(checked["denials"]), checked["body_allowed"], checked["metering"])


def follow_active_release(runtime, tenant_ids, *, denials=(), clock=time.time):
    """Move existing accounts to the release-following engine in one atomic batch.

    Each account keeps its identity, scopes and entitlement. Only its grants
    record is replaced, under a guard on the account and on the record it
    replaces. The catalogue state marker is written in the same batch, so an
    image that does not understand catalogue state refuses to start against
    this store.
    """
    from .catalogue_releases import STATE_KIND, STATE_LOGICAL, _marker_row, read_state
    from .runtime import GRANTS, TENANT
    tenants = tuple(dict.fromkeys(tenant_ids))
    if not tenants:
        raise ServiceRuntimeError("invalid_request", "name at least one account")
    for tenant in tenants:
        identifier(tenant, "tenant identity")
    catalog = runtime._catalog
    with catalog.store(write=True) as store:
        state_row, _state = read_state(catalog, store)
        records = [_marker_row(catalog, state_row, clock)]
        guards = [catalog.guard(state_row, catalog.identity(STATE_KIND, STATE_LOGICAL))]
        for tenant in tenants:
            tenant_row, _tenant = runtime._tenant(store, tenant)
            previous = catalog.read(store, GRANTS, tenant)
            records.append(catalog.record(GRANTS, tenant, release_following_payload(tenant, denials), tenant_id=tenant))
            guards += [catalog.guard(tenant_row), catalog.guard(previous, catalog.identity(GRANTS, tenant))]
        catalog.commit(store, tuple(records), tuple(guards))
    return {"record_type": GRANT_ENGINE_RESULT_VERSION, "engine": FOLLOW_ACTIVE_RELEASE, "tenants": list(tenants),
            "denials": len(tuple(denials)), "committed": True, "tenants_registered": 0}


def all_tenants(runtime):
    """Every registered account, for an operator who moves them all at once."""
    from .runtime import TENANT
    with runtime._catalog.store() as store:
        return sorted(runtime._payload(row, TENANT)["tenant_id"] for row in runtime._catalog.rows_all(store, TENANT))


def following_release(runtime, tenant_id):
    """The release-following grants of one account, or None when it holds a snapshot."""
    from .runtime import GRANTS
    with runtime._catalog.store() as store:
        row = runtime._catalog.read(store, GRANTS, tenant_id)
    if row is None or row["payload"].get("record_type") != FOLLOW_RELEASE_GRANTS_VERSION:
        return None
    return release_following_grants(row["payload"], tenant_id)
