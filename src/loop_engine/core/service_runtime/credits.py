"""Download credits: a number of downloads a superadmin grants to one account, with an expiry and a reason.

Kind: internal service mechanics over the existing service store, used by the
governed staff tools that grant and revoke credits and by the metering of a
body read. It adds no runtime type, no store and no graph vertex.

The owner's direction of September 24, 2026 asked for "adding credits to
users". A credit here is one download of one item, the unit the service
already meters. It involves no purchase and no overage billing: nobody pays
for a credit, a credit is never converted to money, and an account that uses
its last credit is refused the next body read exactly as an account without a
plan is.

```text
One account's download credits, service_download_credits/v1
├── grants: each with a number of downloads, what remains, an expiry, a reason
│   and the staff member who granted it
├── a revoked grant keeps its record and its remaining count reads zero
└── metering beside the plan
    ├── an account whose plan grants bodies downloads under the plan and
    │   draws no credit
    ├── an account without such a plan downloads while it holds a usable
    │   credit; each metered read draws one, from the grant that expires first
    ├── the draw commits in the same batch as the usage record, against the
    │   exact version of the credit record, so two reads never share a credit
    └── a repeated request identity reuses its first usage record and draws
        nothing again
```

A host revocation of body access stops credits as it stops a plan, and a
switched-off account reads nothing. A release that predates this record does
not read it, so on that release a credit-only account is refused bodies: the
safe direction.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import uuid

from ..provisioning_server import ProvisioningMeterAcknowledgment, ProvisioningMeterRequest
from .activity import unique_guards
from .http import ServiceHttpError
from .records import ServiceCommitUnknown, ServiceRuntimeError, digest, text
from .runtime import BODIES, METADATA, PROVISIONING_READ_SCOPE, SCHEMAS, USAGE

LEDGER, LEDGER_VERSION = "service_download_credits", "service_download_credits/v1"
MOST_DOWNLOADS_IN_ONE_GRANT = 100_000
MOST_GRANTS_FOR_ONE_ACCOUNT = 200
SHORTEST_VALIDITY_SECONDS = 3600
LONGEST_VALIDITY_SECONDS = 366 * 86400
SHORTEST_REASON, LONGEST_REASON = 3, 200


def _ledger(row, tenant_id):
    if row is None:
        return {"record_type": LEDGER_VERSION, "tenant_id": tenant_id, "grants": [], "drawn": 0}
    value = row.get("payload")
    if (not isinstance(value, dict) or value.get("record_type") != LEDGER_VERSION
            or value.get("tenant_id") != tenant_id or not isinstance(value.get("grants"), list)):
        raise ServiceRuntimeError("unsupported_or_corrupt_record")
    return value


def read_ledger(runtime, store, tenant_id):
    """The credit record of one account and its row, or an empty record and None."""
    row = runtime._catalog.read(store, LEDGER, tenant_id)
    return row, _ledger(row, tenant_id)


def usable(ledger, now):
    """Grants a download may draw on now: not revoked, not expired, with a download left. First to expire first."""
    rows = [grant for grant in ledger["grants"] if grant.get("revoked_at") is None and grant.get("remaining", 0) > 0
            and type(grant.get("expires_at")) is int and grant["expires_at"] > now]
    return sorted(rows, key=lambda grant: (grant["expires_at"], grant["granted_at"], grant["grant_id"]))


def summary(ledger, now):
    """What an account holds now, for the staff view: remaining downloads and every grant's state."""
    held = usable(ledger, now)
    def state(grant):
        if grant.get("revoked_at") is not None:
            return "revoked"
        if grant["expires_at"] <= now:
            return "expired"
        return "used" if grant["remaining"] <= 0 else "usable"
    return {"remaining": sum(grant["remaining"] for grant in held),
            "next_expiry": held[0]["expires_at"] if held else None, "drawn": ledger.get("drawn", 0),
            "grants": [{"grant_id": grant["grant_id"], "downloads": grant["downloads"],
                        "remaining": grant["remaining"] if state(grant) == "usable" else 0,
                        "expires_at": grant["expires_at"], "reason": grant["reason"], "state": state(grant),
                        "granted_at": grant["granted_at"], "granted_by": grant["granted_by"]}
                       for grant in ledger["grants"]]}


@dataclass(frozen=True)
class CreditGrant:
    """One grant of download credits, as a staff tool plans it."""

    tenant_id: str
    downloads: int
    expires_at: int
    reason: str

    def __post_init__(self):
        if type(self.downloads) is not int or not 1 <= self.downloads <= MOST_DOWNLOADS_IN_ONE_GRANT:
            raise ServiceRuntimeError("invalid_credit_grant", "a grant is from 1 to 100000 downloads")
        if type(self.expires_at) is not int:
            raise ServiceRuntimeError("invalid_credit_grant", "a grant names its expiry as an epoch second")
        reason(self.reason)


def reason(value):
    text(value, "reason")
    if not SHORTEST_REASON <= len(value.strip()) <= LONGEST_REASON:
        raise ServiceRuntimeError("invalid_reason", "a reason has 3 to 200 characters")
    return value.strip()


def grant_rows(runtime, store, grant, actor_ref, now):
    """The rows and guards of one credit grant, and what it adds."""
    if not isinstance(grant, CreditGrant):
        raise ServiceRuntimeError("invalid_credit_grant")
    if not now + SHORTEST_VALIDITY_SECONDS <= grant.expires_at <= now + LONGEST_VALIDITY_SECONDS:
        raise ServiceRuntimeError("invalid_credit_expiry", "credits expire from one hour to 366 days from now")
    catalog = runtime._catalog
    tenant_row, _tenant = runtime._tenant(store, grant.tenant_id)
    row, ledger = read_ledger(runtime, store, grant.tenant_id)
    if len(ledger["grants"]) >= MOST_GRANTS_FOR_ONE_ACCOUNT:
        raise ServiceHttpError("credit_grant_limit_reached", 409)
    entry = {"grant_id": uuid.uuid4().hex, "downloads": grant.downloads, "remaining": grant.downloads,
             "expires_at": grant.expires_at, "reason": reason(grant.reason), "granted_by": actor_ref,
             "granted_at": int(now), "revoked_at": None, "revoked_by": "", "revoke_reason": ""}
    updated = catalog.record(LEDGER, grant.tenant_id, {**ledger, "grants": [*ledger["grants"], entry]},
                             tenant_id=grant.tenant_id)
    return ((updated,), (catalog.guard(row, updated["record_id"]), catalog.guard(tenant_row)),
            {"grant_id": entry["grant_id"], "downloads": grant.downloads, "expires_at": grant.expires_at})


def revoke_rows(runtime, store, tenant_id, grant_id, why, actor_ref, now):
    """The rows and guards that end one grant. Its unused downloads are gone; its record stays."""
    catalog = runtime._catalog
    row, ledger = read_ledger(runtime, store, tenant_id)
    matches = [grant for grant in ledger["grants"] if grant["grant_id"] == grant_id]
    if len(matches) != 1:
        raise ServiceHttpError("credit_grant_not_found", 404)
    if matches[0].get("revoked_at") is not None:
        raise ServiceHttpError("credit_grant_already_revoked", 409)
    forfeited = matches[0]["remaining"] if matches[0]["expires_at"] > now else 0
    grants = [{**grant, "revoked_at": int(now), "revoked_by": actor_ref, "revoke_reason": reason(why)}
              if grant["grant_id"] == grant_id else grant for grant in ledger["grants"]]
    updated = {**row, "record_version": uuid.uuid4().hex, "payload": {**ledger, "grants": grants}}
    return (updated,), (catalog.guard(row),), {"grant_id": grant_id, "downloads_forfeited": forfeited}


def _drawn_before(runtime, store, tenant_id, request_id):
    """True when this request identity already drew a credit, so a retry of it is honoured."""
    if not isinstance(request_id, str) or not request_id:
        return False
    held = runtime._catalog.read(store, USAGE, (tenant_id, request_id))
    return held is not None and bool(runtime._payload(held, USAGE).get("credit_grant_id"))


@dataclass(frozen=True)
class CreditBackedAccess:
    """Body access for one request that comes from download credits, not from a plan.

    The entitlement stays the same for the whole request, because the
    provisioning server checks the account again after the draw: the draw
    itself is the commit point, and it rechecks every credit condition.
    """

    runtime: object

    @staticmethod
    def entitlement(latest):
        return BODIES if latest.entitlement in (METADATA, BODIES) else latest.entitlement

    def meter(self, principal, grant_guard):
        return lambda request: record_credit_usage(self.runtime, request, principal, guards=(grant_guard,))


def credit_access(runtime, principal, operation, request_id=None):
    """Credit-backed access for one request, or None when the plan decides it or no credit applies."""
    if principal.entitlement == BODIES or PROVISIONING_READ_SCOPE not in principal.scopes:
        return None
    now = runtime._now()
    with runtime._catalog.store() as store:
        _tenant_row, tenant = runtime._tenant(store, principal.tenant_id)
        if tenant.get("enabled") is not True or tenant.get("body_access_revoked") is not False:
            return None
        _row, ledger = read_ledger(runtime, store, principal.tenant_id)
        if usable(ledger, now) or (operation == "read" and _drawn_before(runtime, store, principal.tenant_id,
                                                                       request_id)):
            return CreditBackedAccess(runtime)
    return None


def record_credit_usage(runtime, request, principal, *, guards=()):
    """Meter one body read that credits pay for: the usage record and the draw commit together."""
    if not isinstance(request, ProvisioningMeterRequest):
        raise ServiceRuntimeError("invalid_usage_request")
    catalog = runtime._catalog
    try:
        with catalog.store(write=True) as store:
            current, auth_guards = runtime._revalidate(store, principal)
            if current.tenant_id != request.tenant_id or PROVISIONING_READ_SCOPE not in current.scopes:
                raise ServiceRuntimeError("body_forbidden")
            tenant_row, tenant = runtime._tenant(store, current.tenant_id)
            if tenant.get("body_access_revoked") is not False:
                raise ServiceRuntimeError("body_forbidden")
            logical, expected = (request.tenant_id, request.request_id), digest(asdict(request))
            held = catalog.read(store, USAGE, logical)
            if held is not None:
                if runtime._payload(held, USAGE).get("request_digest") != expected:
                    raise ServiceRuntimeError("usage_identity_conflict")
                return ProvisioningMeterAcknowledgment(request, True, held["record_id"], "durable")
            now = runtime._now()
            row = {"record_type": SCHEMAS[USAGE], "tenant_id": request.tenant_id,
                   "request_id_digest": digest(request.request_id), "request_digest": expected, "unit": request.unit,
                   "quantity": request.quantity, "item_identity": request.binding.identity,
                   "body_digest": request.binding.body_digest, "at": now}
            rows, extra = [], []
            if current.entitlement != BODIES:
                # No plan covers this read now, so one credit pays for it.
                ledger_row, ledger = read_ledger(runtime, store, current.tenant_id)
                held_grants = usable(ledger, now)
                if not held_grants:
                    raise ServiceRuntimeError("download_credits_exhausted")
                chosen = held_grants[0]["grant_id"]
                grants = [{**grant, "remaining": grant["remaining"] - 1} if grant["grant_id"] == chosen else grant
                          for grant in ledger["grants"]]
                rows.append({**ledger_row, "record_version": uuid.uuid4().hex,
                             "payload": {**ledger, "grants": grants, "drawn": ledger.get("drawn", 0) + 1}})
                extra = [catalog.guard(ledger_row)]
                row["credit_grant_id"] = chosen
            usage = catalog.record(USAGE, logical, row, tenant_id=request.tenant_id)
            catalog.commit(store, (usage, *rows), unique_guards((*auth_guards, *guards, catalog.guard(tenant_row),
                                                                 *extra, catalog.guard(None, usage["record_id"]))))
            return ProvisioningMeterAcknowledgment(request, True, usage["record_id"], "durable")
    except ServiceCommitUnknown:
        return ProvisioningMeterAcknowledgment(request, None)
