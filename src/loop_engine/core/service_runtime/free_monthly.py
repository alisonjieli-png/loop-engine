"""Free monthly Baltor Pro: the founding offer and the grants a superadmin makes.

Kind: internal service mechanics over the existing entitlement record. It adds
no runtime type, no store and no graph vertex. A free monthly grant is the
operator entitlement that `set_operator_entitlement` already writes, source
`explicit_host_grant`, with three more fields: `grant_kind`, `renews` and the
moment the grant was made. Every release that reads the entitlement record
honours it until `valid_until`, which is the end of the current month, and
this release renews it month by month until it is revoked. A release that
predates renewal therefore honours at most one month and never more.

```text
Free monthly Baltor Pro
├── founding_free_monthly: the first accounts that finish Baltor's sign-up
│   ├── the count comes from the host file, ten by default
│   ├── one counter record holds the accounts that hold the offer, and every
│   │   grant commits against its exact version, so two sign-ups at the last
│   │   place yield one holder
│   └── each account is considered once, and the answer is kept
├── free_monthly: granted by a superadmin to any account without paid access
├── renewal: a periodic task moves `valid_until` on by one calendar month when
│   it is three days away; a revocation that lands first wins
└── revocation: the next check of the account refuses bodies; a founding
    place becomes free again
```
"""
from __future__ import annotations

from datetime import datetime, timezone
import uuid

from .records import ServiceRuntimeError
from .retention import COMPLETED, FAILED, INCOMPLETE, RetentionSchedule, ServiceRetentionPolicy
from .runtime import (BILLING_POLICY, BODIES, ENTITLEMENT, HOST_GRANT_SOURCE, METADATA, SCHEMAS,
                      STRIPE_SNAPSHOT_SOURCE)

FREE_MONTHLY, FOUNDING_FREE_MONTHLY = "free_monthly", "founding_free_monthly"
GRANT_KINDS = (FREE_MONTHLY, FOUNDING_FREE_MONTHLY)
PAID, OTHER_COMPED, NO_PLAN = "paid", "other_comped", "none"
PLAN_STATES = (PAID, FREE_MONTHLY, FOUNDING_FREE_MONTHLY, OTHER_COMPED, NO_PLAN)
FOUNDING, FOUNDING_VERSION, FOUNDING_KEY = "service_founding_offer", "service_founding_offer/v1", "founding"
FOUNDING_ACCOUNT, FOUNDING_ACCOUNT_VERSION = "service_founding_offer_account", "service_founding_offer_account/v1"
GRANTED, LIMIT_REACHED, ACCESS_HELD, DEFERRED = "granted", "limit_reached", "access_already_held", "deferred"
RENEWAL_REPORT_VERSION = "service_free_monthly_renewal_report/v1"
#: A grant is renewed once its end is this close, so a renewal task that misses
#: a few runs still renews before the account notices.
RENEWAL_LEAD_SECONDS = 3 * 86400
RENEWAL_INTERVAL_SECONDS = 3600
RENEWAL_CHECK_NAME = "free_monthly_renewal_current"
CONSIDERATION_ROUNDS = 8


def next_month(moment):
    """The same moment one calendar month later, in UTC, on the last day when the month is shorter."""
    when = datetime.fromtimestamp(moment, timezone.utc)
    year, month = (when.year + 1, 1) if when.month == 12 else (when.year, when.month + 1)
    for day in (when.day, 30, 29, 28):
        try:
            return int(when.replace(year=year, month=month, day=day).timestamp())
        except ValueError:
            continue
    raise ServiceRuntimeError("invalid_period")


def free_monthly_payload(tenant_id, kind, now, granted_by, previous=None):
    """The entitlement record of one free monthly grant, ending one month from now."""
    if kind not in GRANT_KINDS:
        raise ServiceRuntimeError("invalid_free_monthly_grant")
    earlier = previous or {}
    return {"record_type": SCHEMAS[ENTITLEMENT], "tenant_id": tenant_id, "enabled": True, "entitlement": BODIES,
            "valid_until": next_month(now), "source": HOST_GRANT_SOURCE,
            "evidence_ref": kind + ":" + granted_by, "grant_kind": kind, "renews": "monthly",
            "granted_at": now, "granted_by": granted_by, "renewals": 0,
            "previous_source": earlier.get("source", ""), "previous_valid_until": earlier.get("valid_until")}


def free_monthly_kind(payload):
    """The kind of an enabled free monthly grant, or empty text. It says nothing about the current month."""
    if (isinstance(payload, dict) and payload.get("record_type") == SCHEMAS[ENTITLEMENT]
            and payload.get("source") == HOST_GRANT_SOURCE and payload.get("grant_kind") in GRANT_KINDS
            and payload.get("enabled") is True and payload.get("entitlement") == BODIES):
        return payload["grant_kind"]
    return ""


def plan_state(runtime, tenant, entitlement_row, policy_row):
    """One account's plan: paid, free monthly, founding free monthly, other comped access, or none.

    It reads the recorded source and kind with the runtime's own entitlement
    rule, and never infers money from an expiry or a name. Whether the account
    is switched on is reported beside it, not folded into it.
    """
    if (entitlement_row is None or tenant.get("body_access_revoked") is not False
            or runtime._entitlement(entitlement_row, policy_row) != BODIES):
        return NO_PLAN
    value = runtime._payload(entitlement_row, ENTITLEMENT)
    if value.get("source") == STRIPE_SNAPSHOT_SOURCE:
        return PAID
    return free_monthly_kind(value) or OTHER_COMPED


def _counter(row):
    if row is None:
        return {"record_type": FOUNDING_VERSION, "holders": [], "granted_total": 0}
    value = row.get("payload")
    if (not isinstance(value, dict) or value.get("record_type") != FOUNDING_VERSION
            or not isinstance(value.get("holders"), list)):
        raise ServiceRuntimeError("unsupported_or_corrupt_record")
    return value


def founding_holders(runtime):
    """The accounts that hold the founding offer now."""
    with runtime._catalog.store() as store:
        return list(_counter(runtime._catalog.read(store, FOUNDING, FOUNDING_KEY))["holders"])


def consider_founding_offer(runtime, tenant_id, limit):
    """Grant the founding offer to one new account while fewer than `limit` accounts hold it.

    The decision is kept for the account, so it is made once. The counter,
    the account's decision and its entitlement commit in one batch against the
    counter's exact version. A sign-up that loses a race reads the counter
    again and decides again, so the holders never exceed the limit. After
    repeated lost races the answer is `deferred` and nothing is kept; the next
    activation of the account decides.
    """
    if type(limit) is not int or limit < 0:
        raise ServiceRuntimeError("invalid_account_policy")
    catalog = runtime._catalog
    for _round in range(CONSIDERATION_ROUNDS):
        try:
            with catalog.store(write=True) as store:
                held = catalog.read(store, FOUNDING_ACCOUNT, tenant_id)
                if held is not None:
                    return held["payload"].get("decision", DEFERRED)
                tenant_row, tenant = runtime._tenant(store, tenant_id)
                counter_row = catalog.read(store, FOUNDING, FOUNDING_KEY)
                counter = _counter(counter_row)
                entitlement_row = catalog.read(store, ENTITLEMENT, tenant_id)
                policy_row = catalog.read(store, BILLING_POLICY, "stripe")
                now = int(runtime._now())
                holders = list(counter["holders"])
                decision = (ACCESS_HELD if plan_state(runtime, tenant, entitlement_row, policy_row) != NO_PLAN
                            else GRANTED if len(holders) < limit else LIMIT_REACHED)
                account = catalog.record(FOUNDING_ACCOUNT, tenant_id, {
                    "record_type": FOUNDING_ACCOUNT_VERSION, "tenant_id": tenant_id, "decision": decision,
                    "considered_at": now, "limit": limit, "holders_before": len(holders), "revoked_at": None},
                    tenant_id=tenant_id)
                rows = [account]
                guards = [catalog.guard(None, account["record_id"]),
                          catalog.guard(counter_row, catalog.identity(FOUNDING, FOUNDING_KEY))]
                if decision == GRANTED:
                    # Checked again against the count about to be written, so a
                    # wrong decision above still cannot commit a holder too many.
                    if tenant_id in holders or len(holders) + 1 > limit:
                        raise ServiceRuntimeError("concurrent_update")
                    rows.append(catalog.record(FOUNDING, FOUNDING_KEY, {
                        "record_type": FOUNDING_VERSION, "holders": [*holders, tenant_id],
                        "granted_total": counter.get("granted_total", 0) + 1}))
                    previous = runtime._payload(entitlement_row, ENTITLEMENT) if entitlement_row is not None else {}
                    entitlement = catalog.record(ENTITLEMENT, tenant_id, free_monthly_payload(
                        tenant_id, FOUNDING_FREE_MONTHLY, now, "founding_offer", previous), tenant_id=tenant_id)
                    rows.append(entitlement)
                    guards += [catalog.guard(entitlement_row, entitlement["record_id"]), catalog.guard(tenant_row)]
                catalog.commit(store, tuple(rows), tuple(guards))
                return decision
        except ServiceRuntimeError as error:
            if error.code != "concurrent_update":
                raise
    return DEFERRED


def grant_rows(runtime, store, tenant_id, now, granted_by):
    """The rows and guards of one superadmin grant of free monthly Baltor Pro."""
    catalog = runtime._catalog
    tenant_row, tenant = runtime._tenant(store, tenant_id)
    entitlement_row = catalog.read(store, ENTITLEMENT, tenant_id)
    state = plan_state(runtime, tenant, entitlement_row, catalog.read(store, BILLING_POLICY, "stripe"))
    if state == PAID:
        raise ServiceRuntimeError("paid_subscription_active")
    if state in GRANT_KINDS:
        raise ServiceRuntimeError("free_monthly_already_held")
    previous = runtime._payload(entitlement_row, ENTITLEMENT) if entitlement_row is not None else {}
    entitlement = catalog.record(ENTITLEMENT, tenant_id, free_monthly_payload(
        tenant_id, FREE_MONTHLY, now, granted_by, previous), tenant_id=tenant_id)
    # A host grant lifts an earlier host revocation of body access, exactly as
    # `set_operator_entitlement` does.
    updated_tenant = {**tenant_row, "record_version": uuid.uuid4().hex,
                      "payload": {**tenant, "body_access_revoked": False}}
    return ((entitlement, updated_tenant),
            (catalog.guard(entitlement_row, entitlement["record_id"]), catalog.guard(tenant_row)),
            {"grant_kind": FREE_MONTHLY, "valid_until": entitlement["payload"]["valid_until"]})


def revoke_rows(runtime, store, tenant_id, now, revoked_by):
    """The rows and guards that end one account's free monthly grant, founding or not."""
    catalog = runtime._catalog
    runtime._tenant(store, tenant_id)
    entitlement_row = catalog.read(store, ENTITLEMENT, tenant_id)
    value = runtime._payload(entitlement_row, ENTITLEMENT) if entitlement_row is not None else {}
    kind = free_monthly_kind(value)
    if not kind:
        raise ServiceRuntimeError("free_monthly_not_held")
    revoked = {**entitlement_row, "record_version": uuid.uuid4().hex, "payload": {
        **value, "enabled": False, "entitlement": METADATA, "valid_until": None,
        "revoked_at": now, "revoked_by": revoked_by}}
    rows, guards = [revoked], [catalog.guard(entitlement_row)]
    if kind == FOUNDING_FREE_MONTHLY:
        counter_row = catalog.read(store, FOUNDING, FOUNDING_KEY)
        counter = _counter(counter_row)
        rows.append(catalog.record(FOUNDING, FOUNDING_KEY, {
            **counter, "holders": [holder for holder in counter["holders"] if holder != tenant_id]}))
        guards.append(catalog.guard(counter_row, catalog.identity(FOUNDING, FOUNDING_KEY)))
        account_row = catalog.read(store, FOUNDING_ACCOUNT, tenant_id)
        if account_row is not None:
            rows.append({**account_row, "record_version": uuid.uuid4().hex,
                         "payload": {**account_row["payload"], "revoked_at": now}})
            guards.append(catalog.guard(account_row))
    return tuple(rows), tuple(guards), {"grant_kind": kind}


def _renewal_due(payload, now):
    return (bool(free_monthly_kind(payload)) and type(payload.get("valid_until")) is int
            and payload["valid_until"] - now <= RENEWAL_LEAD_SECONDS)


def renew_free_monthly(runtime):
    """Move every free monthly grant that ends within three days on by whole months.

    Each renewal commits against the exact version it read, so a revocation or
    a payment that lands first wins and the renewal is skipped. A report holds
    counts only.
    """
    catalog, now = runtime._catalog, int(runtime._now())
    with catalog.store() as reader:
        due = [row["record_id"] for row in catalog.rows_all(reader, ENTITLEMENT) if _renewal_due(row["payload"], now)]
    renewed = conflicts = 0
    if due:
        with catalog.store(write=True) as store:
            for identity in due:
                row = catalog.read_id(store, identity, kind=ENTITLEMENT)
                if row is None or not _renewal_due(row["payload"], now):
                    continue
                until = row["payload"]["valid_until"]
                while until <= now + RENEWAL_LEAD_SECONDS:
                    until = next_month(until)
                updated = {**row, "record_version": uuid.uuid4().hex, "payload": {
                    **row["payload"], "valid_until": until, "renewed_at": now,
                    "renewals": row["payload"].get("renewals", 0) + 1}}
                try:
                    catalog.commit(store, (updated,), (catalog.guard(row),))
                    renewed += 1
                except ServiceRuntimeError as error:
                    if error.code != "concurrent_update":
                        raise
                    conflicts += 1
    return {"record_type": RENEWAL_REPORT_VERSION, "outcome": INCOMPLETE if conflicts else COMPLETED,
            "renewed": renewed, "conflicts": conflicts, "due": len(due)}


class FreeMonthlyRenewalSchedule(RetentionSchedule):
    """The periodic renewal task of one service process, on the retention task's schedule machinery.

    It starts and stops with the application, runs soon after start and then
    every hour, and reports its last outcome as a health check that is never
    required.
    """

    def __init__(self, runtime, interval_seconds=RENEWAL_INTERVAL_SECONDS):
        super().__init__(runtime, ServiceRetentionPolicy(sweep_interval_seconds=interval_seconds),
                         sweep=lambda: renew_free_monthly(runtime))

    def _finished(self, report):
        self.finished_sweeps += 1
        outcome = report.get("outcome", FAILED) if isinstance(report, dict) else FAILED
        self.last_outcome = outcome
        self.last_code = "" if outcome == COMPLETED else (
            report.get("code") if isinstance(report, dict) and report.get("code")
            else "free_monthly_renewal_" + str(outcome))

    def readiness_check(self):
        from .observability import ReadinessCheck
        if not self.running:
            return ReadinessCheck(RENEWAL_CHECK_NAME, False, False, "free_monthly_renewal_not_running")
        if self.finished_sweeps == 0:
            return ReadinessCheck(RENEWAL_CHECK_NAME, False, False, "free_monthly_renewal_not_run_yet")
        passed = self.last_outcome == COMPLETED
        return ReadinessCheck(RENEWAL_CHECK_NAME, False, passed, "" if passed else self.last_code)
