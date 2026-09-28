"""The durable usage meter: one measured unit for each account, item version and calendar month.

Kind: internal service mechanics over the existing usage record (`service_usage/v1`). It adds no runtime type, no
store and no graph vertex. `ServiceRuntime.record_usage` and `ServiceRuntime.usage_for` delegate here, so the counting
rule, the retry of a busy store and the usage answer live in one module.

```text
One metered read of an item version
├── the unit's identity: account, item identity, body digest and calendar month (UTC)
├── already held this month
│   └── acknowledged by that record; nothing is written
└── not held yet
    ├── written once, under a guard that the record does not exist
    ├── another read wrote it first
    │   └── found on the next attempt and acknowledged by it
    ├── the store stayed busy
    │   └── tried again with growing pauses for METER_WRITE_SECONDS, then usage_store_busy
    └── the store answered neither way
        └── an acknowledgment whose commitment is unknown
```

The owner's price decision names one downloaded item as the measured unit, and there is no overage billing, so a
calendar month is the billing period of every plan source alike. A customer run on September 27, 2026 recorded 26
metered reads of 5 distinct items, and 5 of 8 downloads made during five concurrent runs on one account answered an
unknown commitment; this module counts each item version once a month and answers a busy store precisely.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import time

from ..provisioning_server import ProvisioningMeterAcknowledgment, ProvisioningMeterRequest
from .records import ServiceCommitUnknown, ServiceRuntimeError, digest, usage_items
from .runtime import BODIES, PROVISIONING_READ_SCOPE, SCHEMAS, USAGE, USAGE_READ_SCOPE
from .storage import STORE_BUSY_CODE

USAGE_UNIT_RULE = "one_per_item_version_per_calendar_month_utc"
USAGE_PERIOD_FORMAT = "%Y-%m"
#: How long the meter keeps trying a write that the store refused as busy before it answers `usage_store_busy`:
#: nothing was counted and nothing is delivered, and the customer may retry at once. It stays well inside the request
#: deadline, so concurrent downloads on one account succeed or get that precise answer, never an unknown commitment.
METER_WRITE_SECONDS = 12.0
METER_RETRY_FIRST_DELAY_SECONDS, METER_RETRY_LONGEST_DELAY_SECONDS = 0.05, 0.5
USAGE_STORE_BUSY_CODE = "usage_store_busy"
#: A write whose guard changed is tried again this many times: the unit another read just recorded is then found, or
#: the account's changed records are checked again from the start.
METER_CHANGED_GUARD_ATTEMPTS = 3


def usage_period(moment):
    """The calendar month, in UTC, that a metered read at `moment` counts in, as `YYYY-MM`."""
    return datetime.fromtimestamp(moment, timezone.utc).strftime(USAGE_PERIOD_FORMAT)


def usage_unit(request, period):
    """The logical identity and the exact content of one metered unit: account, item version, unit and month."""
    unit = {"tenant_id": request.tenant_id, "unit": request.unit, "quantity": request.quantity,
            "item_identity": request.binding.identity, "body_digest": request.binding.body_digest, "period": period}
    return (request.tenant_id, "item_version_month", request.binding.identity, request.binding.body_digest,
            period), digest(unit)


def record_usage(runtime, request, principal, guards=()):
    """Record one metered unit, or acknowledge the unit this item version already holds this month."""
    if not isinstance(request, ProvisioningMeterRequest):
        raise ServiceRuntimeError("invalid_usage_request")
    deadline = time.monotonic() + METER_WRITE_SECONDS
    delay, changed = METER_RETRY_FIRST_DELAY_SECONDS, 0
    while True:
        try:
            return _record_once(runtime, request, principal, guards)
        except ServiceCommitUnknown:
            return ProvisioningMeterAcknowledgment(request, None)
        except ServiceRuntimeError as error:
            if error.code == "concurrent_update" and changed < METER_CHANGED_GUARD_ATTEMPTS - 1:
                # Another read of the same unit committed between this read and this write, or an account record
                # changed: the next attempt finds that unit or checks the account again from the start.
                changed += 1
                continue
            if error.code != STORE_BUSY_CODE:
                raise
            # The store wrote nothing. Try again while the meter's time lasts, then say so precisely.
            if time.monotonic() + delay >= deadline:
                raise ServiceRuntimeError(USAGE_STORE_BUSY_CODE,
                                          "the usage store stayed busy; nothing was counted; retry") from None
        time.sleep(delay)
        delay = min(delay * 2, METER_RETRY_LONGEST_DELAY_SECONDS)


def _record_once(runtime, request, principal, guards):
    catalog = runtime._catalog
    with catalog.store(write=True) as store:
        current, auth_guards = runtime._revalidate(store, principal)
        if (current.tenant_id != request.tenant_id or current.entitlement != BODIES
                or PROVISIONING_READ_SCOPE not in current.scopes):
            raise ServiceRuntimeError("body_forbidden")
        now = runtime._now()
        period = usage_period(now)
        logical, unit_digest = usage_unit(request, period)
        held = catalog.read(store, USAGE, logical)
        if held is not None:
            if runtime._payload(held, USAGE).get("unit_digest") != unit_digest:
                raise ServiceRuntimeError("usage_identity_conflict")
            return ProvisioningMeterAcknowledgment(request, True, held["record_id"], "durable")
        row = catalog.record(USAGE, logical, {"record_type": SCHEMAS[USAGE],
            "tenant_id": request.tenant_id, "request_id_digest": digest(request.request_id),
            "request_digest": digest(asdict(request)), "unit_digest": unit_digest, "unit_rule": USAGE_UNIT_RULE,
            "period": period, "unit": request.unit, "quantity": request.quantity,
            "item_identity": request.binding.identity, "body_digest": request.binding.body_digest,
            "at": now}, tenant_id=request.tenant_id)
        catalog.commit(store, (row,), (*auth_guards, *guards, catalog.guard(None, row["record_id"])))
        return ProvisioningMeterAcknowledgment(request, True, row["record_id"], "durable")


def usage_for(runtime, principal):
    """One account's usage: its units, their totals, each item's units and latest unit, and this month's count."""
    catalog = runtime._catalog
    with catalog.store() as store:
        current, _ = runtime._revalidate(store, principal)
        if USAGE_READ_SCOPE not in current.scopes:
            raise ServiceRuntimeError("scope_required")
        rows = catalog.rows(store, USAGE, current.tenant_id)
        totals, reads = {}, {}
        period, this_period = usage_period(runtime._now()), 0
        for value in (runtime._payload(row, USAGE) for row in rows):
            totals[value["unit"]] = totals.get(value["unit"], 0) + value["quantity"]
            reads.setdefault(value["item_identity"], []).append(value["at"])
            # A record written before the monthly unit carries no period; its moment names its month.
            if value.get("period", usage_period(value["at"])) == period:
                this_period += 1
        return {"record_type": "durable_tenant_usage/v1", "tenant_id": current.tenant_id, "records": len(rows),
                "totals": totals, "durability": "durable", "items": usage_items(reads),
                "unit_rule": USAGE_UNIT_RULE, "current_period": period, "current_period_records": this_period}
