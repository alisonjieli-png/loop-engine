"""Grants that follow the active catalogue release, beside the existing snapshot grants.

An account's grants record now has two engines, told apart by its record
version. Version 1 is the existing snapshot: an exact list of item bindings
that changes only when an operator applies new grants. Version 2 follows the
active release: the account receives every approved item of the release being
served, minus the identities it explicitly denies, so a newly published item
reaches the account without `apply-grants`. Items that declare effects are
still withheld until the client declares them, exactly as for a snapshot,
because the effect filter runs after the grant.

```text
Moving accounts between the two engines
├── follow_active_release            the named accounts follow, with the denials given
├── follow_accounts_already_granted  every account that already receives every item the
│                                    served view offers, and no other; an account that
│                                    follows already keeps its denials; named accounts
│                                    can be kept fixed, and a preview writes nothing
└── stop_following_release           one account returns to a version 1 snapshot of
                                     exactly what it receives from the served view now
```

A bulk move never widens what an account receives: following adds only what
is published later, so an account that holds less today is moved only by
naming it. A decision that reads the served view is refused when the catalogue
changed after that view was built.

A release older than this one reads version 1 only, so it refuses a version 2
record instead of honouring a record whose rules it does not know.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import time

from ..provisioning_server import METERING_POLICIES, ProvisioningGrant, ProvisioningItemBinding
from .records import ServiceRuntimeError, identifier

FOLLOW_RELEASE_GRANTS_VERSION = "service_grants/v2"
FOLLOW_ACTIVE_RELEASE = "follow_active_release"
#: The engine of a version 1 record, an exact list of grants.
SNAPSHOT_ENGINE = "snapshot"
GRANT_ENGINE_RESULT_VERSION = "service_catalogue_grant_engine/v1"
MAXIMUM_DENIALS = 10_000
#: How the accounts of one command were chosen.
NAMED_ACCOUNTS, ACCOUNTS_ALREADY_GRANTED = "named_accounts", "accounts_already_granted_every_item"
#: Why a bulk move left an account where it is.
ALREADY_FOLLOWING, NOT_GRANTED_EVERY_ITEM = "already_following", "not_granted_every_item"


def checked_denials(denials):
    """Distinct, nonempty item identities, at most `MAXIMUM_DENIALS` of them."""
    denials = tuple(denials)
    if (len(denials) > MAXIMUM_DENIALS or len(set(denials)) != len(denials)
            or any(not isinstance(value, str) or not value for value in denials)):
        raise ServiceRuntimeError("invalid_disclosure_grant", "denials are distinct item identities")
    return denials


def release_following_payload(tenant_id, denials=(), *, body_allowed=True, metering=METERING_POLICIES[0]):
    """The version 2 grants record of one account."""
    denials = checked_denials(denials)
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


def snapshot_payload(tenant_id, grants):
    """The version 1 grants record, the exact list `ServiceRuntime.set_grants` writes."""
    from .runtime import GRANTS, SCHEMAS
    return {"record_type": SCHEMAS[GRANTS], "tenant_id": tenant_id, "grants": [asdict(grant) for grant in grants]}


def snapshot_grants(payload, tenant_id):
    """Read a version 1 grants record as `ServiceRuntime.grant_snapshot` does, refusing another account's grants."""
    grants = tuple(ProvisioningGrant(**{**value, "binding": ProvisioningItemBinding(**value["binding"])})
                   for value in payload["grants"])
    if payload.get("tenant_id") != tenant_id or any(grant.tenant_id != tenant_id for grant in grants):
        raise ServiceRuntimeError("invalid_disclosure_grant")
    return grants


def require_served_state(state, view):
    """Refuse a grant decision taken on a view that was built before the catalogue last changed.

    Every publish, rollback, withdrawal and grant engine move writes the
    catalogue state marker with a new revision, and a view records the
    revision it was built from. A decision on an older view could snapshot
    items that are no longer served, or miss one that now is.
    """
    if (state["revision"] if state else 0) != view.state_revision:
        raise ServiceRuntimeError("catalogue_state_changed",
                                  "the catalogue changed after the served view was read; run the command again")


def left_out_reason(row, tenant_id, following, view):
    """Why a bulk move must leave this account where it is, or empty text when following adds nothing today.

    `row` is the account's grants record and `following` the grants it would
    follow with. The account moves only when its snapshot already holds every
    one of those grants, on the same body and metering terms. An account
    without a record, with an item missing, or with other body or metering
    terms is not granted every item. When the view offers the account
    nothing, holding everything proves nothing, so it stays where it is. An
    account that follows already would lose the denials it holds, which may
    name items that are not published yet.
    """
    if row is None:
        return NOT_GRANTED_EVERY_ITEM
    payload = row["payload"]
    if payload.get("record_type") == FOLLOW_RELEASE_GRANTS_VERSION:
        return ALREADY_FOLLOWING
    held, offered = set(snapshot_grants(payload, tenant_id)), set(following.materialize(view))
    return "" if offered and offered <= held else NOT_GRANTED_EVERY_ITEM


def _follow(runtime, store, state_row, accounts, denials, clock):
    """Write the version 2 records of `accounts`, each `(tenant, tenant row, grants row)`, and the marker, at once."""
    from .catalogue_releases import STATE_KIND, STATE_LOGICAL, _marker_row
    from .runtime import GRANTS
    catalog = runtime._catalog
    records = [_marker_row(catalog, state_row, clock)]
    guards = [catalog.guard(state_row, catalog.identity(STATE_KIND, STATE_LOGICAL))]
    for tenant, tenant_row, previous in accounts:
        records.append(catalog.record(GRANTS, tenant, release_following_payload(tenant, denials), tenant_id=tenant))
        guards += [catalog.guard(tenant_row), catalog.guard(previous, catalog.identity(GRANTS, tenant))]
    catalog.commit(store, tuple(records), tuple(guards))


def follow_active_release(runtime, tenant_ids, *, denials=(), clock=time.time):
    """Move the named accounts to the release-following engine in one atomic batch.

    Each account keeps its identity, scopes and entitlement. Only its grants
    record is replaced, under a guard on the account and on the record it
    replaces. The catalogue state marker is written in the same batch, so an
    image that does not understand catalogue state refuses to start against
    this store. Naming an account is the statement that it may receive every
    item published later; a following account named again takes the denials
    given now.
    """
    from .catalogue_releases import read_state
    from .runtime import GRANTS
    tenants = tuple(dict.fromkeys(tenant_ids))
    if not tenants:
        raise ServiceRuntimeError("invalid_request", "name at least one account")
    for tenant in tenants:
        identifier(tenant, "tenant identity")
    catalog = runtime._catalog
    with catalog.store(write=True) as store:
        state_row, _state = read_state(catalog, store)
        accounts = [(tenant, runtime._tenant(store, tenant)[0], catalog.read(store, GRANTS, tenant))
                    for tenant in tenants]
        _follow(runtime, store, state_row, accounts, denials, clock)
    return {"record_type": GRANT_ENGINE_RESULT_VERSION, "engine": FOLLOW_ACTIVE_RELEASE, "selection": NAMED_ACCOUNTS,
            "tenants": list(tenants), "denials": len(tuple(denials)), "committed": True, "tenants_registered": 0}


def follow_accounts_already_granted(runtime, view, *, denials=(), keep_fixed=(), preview=False, clock=time.time):
    """Move every account that already receives every item `view` offers, and leave every other one alone.

    This is `--all-tenants`. Following then adds only what is published later,
    so no account receives more today than it held. The decision is taken
    inside the write batch, against the view the host serves at the catalogue
    state it was built from, and the batch is guarded on the marker and on
    every record the decision moves, so a release, rollback or grant change
    committed meanwhile refuses it. The result names every account left alone
    and the reason.

    `keep_fixed` names accounts that must keep their fixed list, such as the
    diagnostic account that proves isolation; when the decision would move one
    of them, the whole command is refused and nothing is written. `preview`
    takes the same decision on a read-only store and writes nothing, so an
    operator reads exactly which accounts would move before any does.
    """
    from .catalogue_releases import read_state
    from .runtime import GRANTS, TENANT
    denials = checked_denials(denials)
    keep_fixed = tuple(dict.fromkeys(keep_fixed))
    for tenant in keep_fixed:
        identifier(tenant, "tenant identity")
    if type(preview) is not bool:
        raise ServiceRuntimeError("invalid_request", "preview is an explicit Boolean")
    catalog = runtime._catalog
    chosen, left_out = [], []
    with catalog.store(write=not preview) as store:
        state_row, state = read_state(catalog, store)
        require_served_state(state, view)
        for row in catalog.rows_all(store, TENANT):
            tenant = runtime._payload(row, TENANT)["tenant_id"]
            tenant_row, _tenant = runtime._tenant(store, tenant)
            previous = catalog.read(store, GRANTS, tenant)
            reason = left_out_reason(previous, tenant, ReleaseFollowingGrants(tenant, frozenset(denials)), view)
            if reason:
                left_out.append({"tenant_id": tenant, "reason": reason})
            else:
                chosen.append((tenant, tenant_row, previous))
        chosen.sort(key=lambda account: account[0])
        protected = sorted(tenant for tenant, _row, _previous in chosen if tenant in keep_fixed)
        if protected:
            raise ServiceRuntimeError("kept_account_would_move",
                                      "an account named with --keep-fixed holds every served item and would follow "
                                      "the release; nothing was written: " + ", ".join(protected))
        if chosen and not preview:
            _follow(runtime, store, state_row, chosen, denials, clock)
    return {"record_type": GRANT_ENGINE_RESULT_VERSION, "engine": FOLLOW_ACTIVE_RELEASE,
            "selection": ACCOUNTS_ALREADY_GRANTED, "tenants": [account[0] for account in chosen],
            "left_out": sorted(left_out, key=lambda row: row["tenant_id"]), "denials": len(denials),
            "kept_fixed": list(keep_fixed), "preview": preview,
            "release_id": view.release_id or None, "committed": bool(chosen) and not preview, "tenants_registered": 0}


def stop_following_release(runtime, tenant_id, view, *, clock=time.time):
    """Return one account from the release-following engine to a version 1 snapshot.

    The snapshot is exactly what the account receives from `view`, the view
    the host serves now: every approved item it does not deny, on the body and
    metering terms it follows with. An account that denies every current item
    keeps an empty list, and an item published later reaches it only when an
    operator grants it. The batch is guarded like `follow_active_release`, on
    the account, on the exact version 2 record it replaces and on the catalogue
    state marker, and it is refused when the catalogue changed after `view` was
    built or when the account does not follow the release.
    """
    from .catalogue_releases import STATE_KIND, STATE_LOGICAL, _marker_row, read_state
    from .runtime import GRANTS
    identifier(tenant_id, "tenant identity")
    catalog = runtime._catalog
    with catalog.store(write=True) as store:
        state_row, state = read_state(catalog, store)
        require_served_state(state, view)
        tenant_row, _tenant = runtime._tenant(store, tenant_id)
        previous = catalog.read(store, GRANTS, tenant_id)
        if previous is None or previous["payload"].get("record_type") != FOLLOW_RELEASE_GRANTS_VERSION:
            raise ServiceRuntimeError("account_not_following_release",
                                      "this account holds a fixed list of grants already")
        grants = release_following_grants(previous["payload"], tenant_id).materialize(view)
        snapshot = catalog.record(GRANTS, tenant_id, snapshot_payload(tenant_id, grants), tenant_id=tenant_id)
        catalog.commit(store, (snapshot, _marker_row(catalog, state_row, clock)),
                       (catalog.guard(tenant_row), catalog.guard(previous),
                        catalog.guard(state_row, catalog.identity(STATE_KIND, STATE_LOGICAL))))
    return {"record_type": GRANT_ENGINE_RESULT_VERSION, "engine": SNAPSHOT_ENGINE, "selection": NAMED_ACCOUNTS,
            "tenants": [tenant_id], "grants": len(grants), "release_id": view.release_id or None,
            "committed": True, "tenants_registered": 0}


def following_release(runtime, tenant_id):
    """The release-following grants of one account, or None when it holds a snapshot."""
    from .runtime import GRANTS
    with runtime._catalog.store() as store:
        row = runtime._catalog.read(store, GRANTS, tenant_id)
    if row is None or row["payload"].get("record_type") != FOLLOW_RELEASE_GRANTS_VERSION:
        return None
    return release_following_grants(row["payload"], tenant_id)
