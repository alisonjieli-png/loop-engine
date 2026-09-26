"""Customer reports, staff flags and the withdrawal rule of the served library.

The "Approval of intelligence items" row of the AGENTS.md decision table
publishes an item after one screening review and lets feedback withdraw it
afterwards (roadmap S-6.199). This module holds that feedback edge. It writes
two kinds of durable record through the existing service store and nothing
else: the report itself, and the same `catalogue_withdrawal/v1` record that an
operator's withdrawal writes, so serving, releases and rollbacks honour a
report exactly as they honour every other withdrawal.

```text
Feedback on a served item
├── report   a signed-in customer who downloaded that item version names it, its
│   │        expected digest and a bounded reason
│   ├── Community item   withdrawn at once; the report queues the full review
│   └── Verified item    withdrawn on the second report from a different customer
├── flag     a staff member with the catalogue.flag permission; withdraws any tier at once
└── every report and flag keeps its record; a withdrawal keeps a fixed public
    note, and a withdrawn item version is served again only through a new
    review of new bytes
```

A report counts once for each customer account and item version: a second
report of the same version by the same account is the same record. An
anonymous caller holds no account and cannot report, and an account that never
downloaded the reported bytes is refused with `report_requires_download`. The
rule reads the library tier from the served view's own approval, never from
the request. The reason stays in the private report record: the public library
page shows only a fixed note, because a reason is unreviewed customer text.
"""
from __future__ import annotations

import re
import time

from ..provisioning_server import (COMMUNITY_TIER, LIBRARY_TIERS, QUALIFICATION_APPROVED, VERIFIED_TIER,
                                   ProvisioningItemBinding, ProvisioningQualification)
from .account_policy import STAFF_ROLES
from .catalogue_releases import (POINTER_KIND, POINTER_LOGICAL, POINTER_RECORD_TYPE, RELEASE_KIND, RELEASE_RECORD_TYPE,
                                 STATE_KIND, STATE_LOGICAL, WITHDRAWAL_KIND, WITHDRAWAL_RECORD_TYPE, _marker_row,
                                 _payload, read_state)
from .records import ServiceRuntimeError

REPORT_KIND = "service_catalogue_report"
REPORT_RECORD_TYPE = "catalogue_item_report/v1"
RESULT_RECORD_TYPE = "service_catalogue_report_result/v1"
QUEUE_RECORD_TYPE = "service_catalogue_review_queue/v1"
REPORT_OPERATION, FLAG_OPERATION = "report", "flag"
FEEDBACK_OPERATIONS = (REPORT_OPERATION, FLAG_OPERATION)
#: The protocol tool a harness calls to report an item it was served.
REPORT_TOOL = "provisioning_report"
MAXIMUM_REASON_CHARACTERS = 400
#: How many different customer accounts must report one Verified item version before it is withdrawn without a
#: staff flag, and how many report a Community one. A flag withdraws either tier at once.
VERIFIED_REPORTS_TO_WITHDRAW = 2
COMMUNITY_REPORTS_TO_WITHDRAW = 1
RECORDED, WITHDRAWN = "recorded", "withdrawn"
REVIEW_QUEUED = "queued"
REPORT_REQUIRES_DOWNLOAD = "report_requires_download"
_DIGEST = re.compile(r"[0-9a-f]{64}")


def _refuse(code, message):
    raise ServiceRuntimeError(code, message)


def reason_text(value):
    """A report's reason: bounded plain text without control characters, never empty."""
    if (not isinstance(value, str) or not value.strip() or len(value) > MAXIMUM_REASON_CHARACTERS
            or any(ord(character) < 32 and character not in "\n\t" for character in value)):
        _refuse("report_reason_invalid",
                f"a reason is 1 to {MAXIMUM_REASON_CHARACTERS} characters of plain text without control characters")
    return value


def served_item(view, identity, expected_digest):
    """The item the view serves under that identity and digest, and its library tier from the view's own approval."""
    if not isinstance(identity, str) or not identity:
        _refuse("invalid_request", "a report names an item identity")
    if not isinstance(expected_digest, str) or _DIGEST.fullmatch(expected_digest) is None:
        _refuse("invalid_selected_digest", "a report names the expected digest of the item it saw")
    item = view.catalogue.items.get(identity)
    if item is None:
        if any(key[0] == identity for key in view.withdrawn):
            _refuse("item_withdrawn", "this item version was withdrawn from the library")
        _refuse("item_unavailable", "the library serves no item with that identity")
    if item.digest != expected_digest:
        _refuse("selected_body_digest_mismatch", "the library serves other bytes than the report names")
    try:
        decision = view.qualification_resolver.resolve(ProvisioningItemBinding.from_item(item))
    except Exception:  # noqa: BLE001 - an item the resolver cannot decide is not reportable as served
        decision = None
    tier = getattr(decision, "library_tier", None) if isinstance(decision, ProvisioningQualification) else None
    if getattr(decision, "status", None) != QUALIFICATION_APPROVED or tier not in LIBRARY_TIERS:
        _refuse("item_unavailable", "the library serves that item without an approval this release can read")
    return item, tier


def withdrawal_due(tier, records):
    """True when the feedback records of one item version withdraw it under the rule of its tier."""
    if any(row.get("kind") == FLAG_OPERATION for row in records):
        return True
    reporters = {row.get("reporter_tenant_id") for row in records if row.get("kind") == REPORT_OPERATION}
    needed = VERIFIED_REPORTS_TO_WITHDRAW if tier == VERIFIED_TIER else COMMUNITY_REPORTS_TO_WITHDRAW
    return len(reporters) >= needed


def feedback_records(binding, store, identity, body_digest):
    """Every report and flag of one item version, oldest first. An unknown record version refuses."""
    rows = []
    for row in binding.rows_all(store, REPORT_KIND):
        payload = row["payload"]
        if payload.get("record_type") != REPORT_RECORD_TYPE:
            _refuse("catalogue_record_unsupported", f"a report record is not {REPORT_RECORD_TYPE}")
        if payload["identity"] == identity and payload["body_digest"] == body_digest:
            rows.append(payload)
    return sorted(rows, key=lambda payload: (payload["reported_at"], payload["reporter_tenant_id"], payload["kind"]))


def active_item_version(binding, store, identity):
    """The version digest the active release names for one identity, or empty text when no release is active."""
    _row, pointer = _payload(binding, store, POINTER_KIND, POINTER_LOGICAL, POINTER_RECORD_TYPE)
    if pointer is None:
        return ""
    _release_row, document = _payload(binding, store, RELEASE_KIND, pointer["release_id"], RELEASE_RECORD_TYPE)
    if document is None:
        return ""
    return dict(document["items"]).get(identity, "")


def downloaded(binding, store, tenant_id, identity, body_digest):
    """True when this account holds a usage record of exactly this item version.

    A customer report withdraws a Community item at once, so only an account
    that downloaded the reported bytes may file one. Without this rule any
    signed-in account could empty the Community tier one report at a time."""
    from .runtime import USAGE
    for row in binding.rows(store, USAGE, tenant_id):
        value = row.get("payload", {})
        if value.get("item_identity") == identity and value.get("body_digest") == body_digest:
            return True
    return False


def withdrawal_note(kind):
    """The public note of a withdrawal. It never repeats the words of a report or a flag.

    The library page is public and a reason is unreviewed free text, so the
    reason stays in the private report record that the review reads."""
    return ("Withdrawn after a staff flag; queued for review." if kind == FLAG_OPERATION
            else "Withdrawn after a customer report; queued for review.")


def record_feedback(binding, view, *, kind, identity, expected_digest, reason, tenant_id, role="", clock=time.time):
    """Record one report or flag and withdraw the item version when the rule of its tier says so.

    `binding` is the host's `ServiceCatalogBinding`; `view` is the catalogue the
    service serves now. The report, the withdrawal it causes and the catalogue
    state marker commit together in one atomic batch under a guard on the
    marker, so two reports racing on one item cannot both count as the first.
    """
    if kind not in FEEDBACK_OPERATIONS:
        _refuse("unsupported_operation", f"feedback is one of {FEEDBACK_OPERATIONS}")
    if not isinstance(tenant_id, str) or not tenant_id:
        _refuse("unauthorized", "a report comes from a signed-in account")
    if kind == FLAG_OPERATION and role not in STAFF_ROLES:
        _refuse("staff_role_required", "a flag comes from a staff member")
    reason = reason_text(reason)
    item, tier = served_item(view, identity, expected_digest)
    now = int(clock())
    logical = (identity, expected_digest, tenant_id, kind)
    with binding.store(write=True) as store:
        if kind == REPORT_OPERATION and not downloaded(binding, store, tenant_id, identity, expected_digest):
            _refuse(REPORT_REQUIRES_DOWNLOAD, "a report comes from an account that downloaded this item version")
        state_row, _state = read_state(binding, store)
        version = active_item_version(binding, store, identity)
        held = binding.read(store, REPORT_KIND, logical)
        records = feedback_records(binding, store, identity, expected_digest)
        payload = held["payload"] if held is not None else {
            "record_type": REPORT_RECORD_TYPE, "kind": kind, "identity": identity, "body_digest": expected_digest,
            "item_version": version, "library_tier": tier, "reason": reason, "reporter_tenant_id": tenant_id,
            "reporter_role": role if kind == FLAG_OPERATION else "", "reported_at": now,
            "review_state": REVIEW_QUEUED}
        if held is None:
            records.append(payload)
        withdrawn_row = binding.read(store, WITHDRAWAL_KIND, (identity, expected_digest))
        if withdrawn_row is not None and withdrawn_row["payload"].get("record_type") != WITHDRAWAL_RECORD_TYPE:
            _refuse("catalogue_record_unsupported", f"a withdrawal record is not {WITHDRAWAL_RECORD_TYPE}")
        due = withdrawal_due(tier, records)
        writes, guards = [], [binding.guard(state_row, binding.identity(STATE_KIND, STATE_LOGICAL))]
        if held is None:
            row = binding.record(REPORT_KIND, logical, payload, tenant_id=tenant_id)
            writes.append(row)
            guards.append(binding.guard(None, row["record_id"]))
        withdrawing = due and withdrawn_row is None
        if withdrawing:
            row = binding.record(WITHDRAWAL_KIND, (identity, expected_digest), {
                "record_type": WITHDRAWAL_RECORD_TYPE, "identity": identity, "body_digest": expected_digest,
                "item_version": version, "note": withdrawal_note(kind), "withdrawn_at": now,
                "release_id": ""})
            writes.append(row)
            guards.append(binding.guard(None, row["record_id"]))
            writes.append(_marker_row(binding, state_row, clock))
        if writes:
            binding.commit(store, tuple(writes), tuple(guards))
    reporters = {row["reporter_tenant_id"] for row in records if row["kind"] == REPORT_OPERATION}
    return {"record_type": RESULT_RECORD_TYPE, "operation": kind, "identity": identity,
            "body_digest": expected_digest, "library_tier": tier,
            "state": WITHDRAWN if (withdrawing or withdrawn_row is not None) else RECORDED,
            "withdrawn": bool(withdrawing or withdrawn_row is not None), "withdrawn_now": withdrawing,
            "reports": len(reporters), "flags": sum(1 for row in records if row["kind"] == FLAG_OPERATION),
            "reports_to_withdraw": (VERIFIED_REPORTS_TO_WITHDRAW if tier == VERIFIED_TIER
                                    else COMMUNITY_REPORTS_TO_WITHDRAW),
            "review_state": REVIEW_QUEUED, "recorded_before": held is not None}


def review_queue(binding):
    """Every reported or flagged item version with its counts, for the full review that follows publication."""
    grouped = {}
    with binding.store() as store:
        for row in binding.rows_all(store, REPORT_KIND):
            payload = row["payload"]
            if payload.get("record_type") != REPORT_RECORD_TYPE:
                _refuse("catalogue_record_unsupported", f"a report record is not {REPORT_RECORD_TYPE}")
            key = (payload["identity"], payload["body_digest"])
            entry = grouped.setdefault(key, {"identity": key[0], "body_digest": key[1],
                                             "item_version": payload["item_version"],
                                             "library_tier": payload["library_tier"], "reports": 0, "flags": 0,
                                             "reasons": [], "first_reported_at": payload["reported_at"],
                                             "withdrawn": False})
            entry["reports" if payload["kind"] == REPORT_OPERATION else "flags"] += 1
            entry["reasons"].append(payload["reason"])
            entry["first_reported_at"] = min(entry["first_reported_at"], payload["reported_at"])
        for key, entry in grouped.items():
            entry["withdrawn"] = binding.read(store, WITHDRAWAL_KIND, key) is not None
    queue = sorted(grouped.values(), key=lambda entry: (entry["first_reported_at"], entry["identity"]))
    return {"record_type": QUEUE_RECORD_TYPE, "queued": queue, "count": len(queue),
            "rule": {"community_reports_to_withdraw": COMMUNITY_REPORTS_TO_WITHDRAW,
                     "verified_reports_to_withdraw": VERIFIED_REPORTS_TO_WITHDRAW,
                     "staff_flag_withdraws": True, "tiers": list(LIBRARY_TIERS),
                     "community_tier": COMMUNITY_TIER, "verified_tier": VERIFIED_TIER}}
