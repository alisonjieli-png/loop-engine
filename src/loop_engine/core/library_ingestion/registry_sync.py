"""Registry snapshots compared over time: withdrawals and reconciliation.

A registry entry can be deprecated, deleted or replaced after it was read.
snapshot_index keeps, for each server name, the version, status and digest
of what one read saw. withdrawals compares an earlier snapshot with a later
one: a status that is no longer active, or a new version, returns the item
to review, and an entry missing from a complete later snapshot is withdrawn.
An incomplete snapshot (a stopped read, an outage) is never evidence of
absence, so it withdraws nothing on that ground. reconcile compares an
incremental read with a full one and names every difference.
"""
from __future__ import annotations

from .record_rules import bytes_digest, canonical_json

WITHDRAWAL_RECORD_TYPE = "library_registry_withdrawal/v1"
RECONCILIATION_RECORD_TYPE = "library_registry_reconciliation/v1"
OFFICIAL_META = "io.modelcontextprotocol.registry/official"
ACTIVE = "active"


def snapshot_index(entries) -> dict:
    """Server name to version, status and entry digest, for every readable entry."""
    index = {}
    for entry in entries:
        try:
            server = entry["server"]
            meta = entry["_meta"][OFFICIAL_META]
            index[str(server["name"])] = {"version": str(server["version"]), "status": str(meta["status"]),
                                          "digest": bytes_digest(canonical_json(entry).encode("utf-8"))}
        except (KeyError, TypeError):
            continue
    return index


def withdrawals(previous: dict, current: dict, *, current_complete: bool) -> list:
    """Items that must return to review, each with the reason the later snapshot gives."""
    rows = []
    for name in sorted(previous):
        before = previous[name]
        if before["status"] != ACTIVE:
            continue
        after = current.get(name)
        if after is None:
            if current_complete:
                rows.append({"record_type": WITHDRAWAL_RECORD_TYPE, "name": name,
                             "reason": "vanished_from_complete_snapshot",
                             "previous_version": before["version"], "current_version": None})
            continue
        if after["status"] != ACTIVE:
            rows.append({"record_type": WITHDRAWAL_RECORD_TYPE, "name": name, "reason": "status_changed",
                         "previous_version": before["version"], "current_version": after["version"],
                         "current_status": after["status"]})
        elif after["version"] != before["version"] or after["digest"] != before["digest"]:
            rows.append({"record_type": WITHDRAWAL_RECORD_TYPE, "name": name, "reason": "entry_changed",
                         "previous_version": before["version"], "current_version": after["version"]})
    return rows


def reconcile(incremental: dict, full: dict) -> dict:
    """Name every entry an incremental read missed, added or saw differently from a full read."""
    missing = sorted(set(full) - set(incremental))
    extra = sorted(set(incremental) - set(full))
    differing = sorted(name for name in set(full) & set(incremental) if full[name] != incremental[name])
    return {"record_type": RECONCILIATION_RECORD_TYPE, "missing_in_incremental": missing,
            "extra_in_incremental": extra, "differing": differing,
            "equal": not (missing or extra or differing)}
