"""Staff tools for accounts, credits, activity, the catalogue view and service health.

Kind: internal service mechanics; the functions `staff_tools.StaffTools`
calls for one tool each. It adds no runtime type, no store and no graph vertex.

```text
Tools in this module, and the permission each needs
├── accounts_search    accounts.search for rows with addresses, accounts.counts for counts only
├── account_get        accounts.read
├── account_action     the permission of its operation: accounts.grant_free_monthly,
│                      accounts.revoke_free_monthly, accounts.disable or accounts.enable
├── credits_grant      credits.grant
├── credits_revoke     credits.revoke
├── activity_search    activity.read for events, activity.counts for counts only
├── data_search        catalogue.read
└── service_health     service.diagnostics
```

Addresses live with the identity provider, never in the service store, so a
tool that shows one reads the provider's user list for that call.
"""
from __future__ import annotations

from datetime import datetime, timezone
import uuid

from . import credits as credit_module
from . import free_monthly
from .account_policy import (ACCOUNT_COUNTS, ACCOUNTS_READ, ACCOUNTS_SEARCH, ACTION_PERMISSIONS, ACTIVITY_COUNTS,
                             ACTIVITY_READ, CATALOGUE_READ, CREDITS_GRANT, CREDITS_REVOKE, SERVICE_DIAGNOSTICS)
from .free_monthly import PLAN_STATES
from .http import ServiceHttpError
from .records import ServiceRuntimeError
from .runtime import BILLING_POLICY, BODIES, ENTITLEMENT, KEY, METADATA, SUBJECT, USAGE
from .staff_tools import Plan, StaffTool, forbid_unless

ACCOUNTS_PAGE_VERSION, ACCOUNT_COUNTS_VERSION = "service_staff_account_page/v1", "service_staff_account_counts/v1"
ACCOUNT_VERSION, CATALOGUE_PAGE_VERSION = "service_staff_account/v1", "service_staff_catalogue_page/v1"
HEALTH_VERSION = "service_staff_health/v1"
LARGEST_PAGE, DEFAULT_PAGE, RECENT_SECONDS = 100, 25, 30 * 86400
PAGE = {"page_size": {"type": "integer", "minimum": 1, "maximum": LARGEST_PAGE},
        "cursor": {"type": "integer", "minimum": 0}}
TENANT = {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$"}
MOMENT = {"type": "string", "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}(T[0-9]{2}:[0-9]{2}:[0-9]{2}Z?)?$"}
REASON = {"type": "string", "minLength": 3, "maxLength": 200}


def moment(value):
    """Seconds since the epoch for a provider time or a caller's date, in UTC, or None."""
    if not isinstance(value, str) or len(value) < 10:
        return None
    try:
        text = value[:19] if len(value) >= 19 else value[:10] + "T00:00:00"
        return int(datetime.strptime(text, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).timestamp())
    except ValueError:
        return None


def identity_users(tools):
    """Every provider user, or None when this host reads no identity details."""
    administration = tools.administration
    if administration.origins is None or administration._identity_secret is None:
        return None
    return administration.origins.administration.all_users(administration._identity_secret())


def joined_accounts(tools, users=None):
    """Every account a person signs in to, joined with its provider user, its credits and its founding place."""
    administration, runtime = tools.administration, tools.runtime
    users = identity_users(tools) if users is None else users
    now = runtime._now()
    with runtime._catalog.store() as store:
        service = administration._accounts(store)
        credit = {row["payload"].get("tenant_id"): credit_module.summary(row["payload"], now)["remaining"]
                  for row in runtime._catalog.rows_all(store, credit_module.LEDGER)
                  if row["payload"].get("record_type") == credit_module.LEDGER_VERSION}
    holders = set(free_monthly.founding_holders(runtime))
    by_subject = {user.user_id: user for user in users or ()}
    rows = []
    for subject, held in service.items():
        user = by_subject.get(subject)
        rows.append({"tenant_id": held["tenant_id"], "provider_user_id": subject,
                     "email": user.email if user is not None else "",
                     "created_at": user.created_at if user is not None else "",
                     "email_confirmed": bool(user.email_confirmed_at) if user is not None else None,
                     "last_sign_in_at": user.last_sign_in_at if user is not None else "",
                     "enabled": held["enabled"], "plan_state": held["plan_state"],
                     "plan_valid_until": held["plan_valid_until"], "founding": held["tenant_id"] in holders,
                     "last_item_at": held["last_item_at"], "credits_remaining": credit.get(held["tenant_id"], 0)})
    rows.sort(key=lambda row: (row["created_at"] or "", row["tenant_id"]), reverse=True)
    return rows, users is not None


def _matches(row, fields):
    text = fields.get("text", "").strip().lower()
    if text and not any(text in str(row[name]).lower() for name in ("email", "tenant_id", "provider_user_id")):
        return False
    for name in ("plan_state", "founding", "enabled"):
        if name in fields and row[name] != fields[name]:
            return False
    created = moment(row["created_at"])
    after, before = moment(fields.get("created_after")), moment(fields.get("created_before"))
    if (after is not None or before is not None) and created is None:
        return False
    return (after is None or created >= after) and (before is None or created < before)


def page(rows, fields):
    size, start = fields.get("page_size", DEFAULT_PAGE), fields.get("cursor", 0)
    return rows[start:start + size], (start + size if start + size < len(rows) else None)


def accounts_search(tools, actor, fields):
    """Accounts by address text, plan, founding place, state and creation time; counts only for analytics."""
    rows_allowed = actor.may(ACCOUNTS_SEARCH)
    if not rows_allowed and fields.get("text"):
        # A count of accounts matching one address would say whether it has an account.
        raise ServiceHttpError("address_search_forbidden", 403)
    rows, details = joined_accounts(tools)
    kept = [row for row in rows if _matches(row, fields)]
    counts = {"total": len(kept), "plans": {name: sum(row["plan_state"] == name for row in kept) for name in PLAN_STATES},
              "founding": sum(row["founding"] for row in kept), "switched_off": sum(not row["enabled"] for row in kept),
              "with_credits": sum(row["credits_remaining"] > 0 for row in kept)}
    if not rows_allowed:
        return {"record_type": ACCOUNT_COUNTS_VERSION, **counts}
    shown, following = page(kept, fields)
    return {"record_type": ACCOUNTS_PAGE_VERSION, "accounts": shown, "next_cursor": following,
            "identity_details_available": details, **counts}


def _keys(runtime, store, tenant_id):
    shown = []
    for row in runtime._catalog.rows(store, KEY, tenant_id):
        value = runtime._payload(row, KEY)
        shown.append({"key_id": value.get("key_id", ""), "label": value.get("label", ""),
                      "scopes": list(value.get("scopes", ())), "expires_at": value.get("expires_at"),
                      "enabled": value.get("enabled") is True,
                      "customer_managed": value.get("management_profile") is not None})
    return sorted(shown, key=lambda item: item["key_id"])


def account_get(tools, actor, fields):
    """One account in full: plan, entitlements, key metadata, usage totals and last activity."""
    runtime, tenant_id = tools.runtime, fields["tenant_id"]
    now = runtime._now()
    with runtime._catalog.store() as store:
        tenant_row, tenant = tools.administration._target(store, tenant_id)
        entitlement_row = runtime._catalog.read(store, ENTITLEMENT, tenant_id)
        policy_row = runtime._catalog.read(store, BILLING_POLICY, "stripe")
        state = free_monthly.plan_state(runtime, tenant, entitlement_row, policy_row)
        value = runtime._payload(entitlement_row, ENTITLEMENT) if entitlement_row is not None else {}
        effective = (runtime._entitlement(entitlement_row, policy_row) if tenant.get("body_access_revoked") is False
                     else METADATA)
        _ledger_row, ledger = credit_module.read_ledger(runtime, store, tenant_id)
        usage = [runtime._payload(row, USAGE) for row in runtime._catalog.rows(store, USAGE, tenant_id)]
        subjects = [runtime._payload(row, SUBJECT) for row in runtime._catalog.rows(store, SUBJECT, tenant_id)]
        keys = _keys(runtime, store, tenant_id)
    credit = credit_module.summary(ledger, now)
    users = identity_users(tools)
    person = next((user for user in users or () for subject in subjects if user.user_id == subject.get("subject")),
                  None)
    totals = {}
    for row in usage:
        totals[row.get("unit", "")] = totals.get(row.get("unit", ""), 0) + row.get("quantity", 0)
    last = max((row.get("at", 0) for row in usage), default=None)
    return {"record_type": ACCOUNT_VERSION, "tenant_id": tenant_id, "enabled": tenant.get("enabled") is True,
            "provider_user_ids": sorted(subject.get("subject", "") for subject in subjects),
            "email": person.email if person is not None else "",
            "created_at": person.created_at if person is not None else "",
            "email_confirmed": bool(person.email_confirmed_at) if person is not None else None,
            "plan": {"state": state, "source": value.get("source", ""), "grant_kind": value.get("grant_kind", ""),
                     "valid_until": value.get("valid_until") if state != "none" else None,
                     "founding": tenant_id in set(free_monthly.founding_holders(runtime))},
            "entitlements": {"plan": effective, "body_access_revoked": tenant.get("body_access_revoked") is not False,
                             "downloads_through_credits": effective != BODIES and credit["remaining"] > 0,
                             "credits": credit},
            "keys": keys,
            "usage": {"records": len(usage), "totals": totals, "credit_downloads": sum(
                1 for row in usage if row.get("credit_grant_id")),
                "in_the_last_30_days": sum(1 for row in usage if row.get("at", 0) > now - RECENT_SECONDS)},
            "last_activity": {"download_at": last, "sign_in_at": person.last_sign_in_at if person is not None else "",
                              "tenant_record_version": tenant_row["record_version"]},
            "identity_details_available": users is not None}


def _protect_staff_accounts(tools, store, tenant_id):
    """A staff tool never switches off a staff member's own account; the host file decides who is staff."""
    policy, runtime = tools.administration.policy, tools.runtime
    subjects = [runtime._payload(row, SUBJECT).get("subject") for row in runtime._catalog.rows(store, SUBJECT, tenant_id)]
    if any(member.provider_user_id in subjects for member in policy.staff if member.provider_user_id):
        raise ServiceHttpError("staff_account_protected", 403)
    if any(member.email for member in policy.staff):
        users = identity_users(tools)
        if users is None:
            raise ServiceHttpError("staff_account_check_unavailable", 503)
        emails = {user.email for user in users if user.user_id in subjects}
        if any(member.email in emails for member in policy.staff if member.email):
            raise ServiceHttpError("staff_account_protected", 403)


def _action_rows(tools, store, actor, fields, now):
    runtime, operation, tenant_id = tools.runtime, fields["operation"], fields["tenant_id"]
    tenant_row, tenant = tools.administration._target(store, tenant_id)
    if operation == "grant_free_monthly":
        return free_monthly.grant_rows(runtime, store, tenant_id, now, actor.actor_ref)
    if operation == "revoke_free_monthly":
        return free_monthly.revoke_rows(runtime, store, tenant_id, now, actor.actor_ref)
    wanted = operation == "enable"
    if (tenant.get("enabled") is True) == wanted:
        raise ServiceRuntimeError("account_state_unchanged")
    if not wanted:
        _protect_staff_accounts(tools, store, tenant_id)
    changed = {**tenant_row, "record_version": uuid.uuid4().hex, "payload": {
        **tenant, "enabled": wanted, "enabled_changed_at": now, "enabled_changed_by": actor.actor_ref}}
    return (changed,), (runtime._catalog.guard(tenant_row),), {"enabled": wanted}


def account_action_plan(tools, actor, fields):
    forbid_unless(actor, ACTION_PERMISSIONS[fields["operation"]])
    runtime = tools.runtime
    now = int(runtime._now())
    with runtime._catalog.store() as store:
        _rows, guards, detail = _action_rows(tools, store, actor, fields, now)
        tenant = tools.administration._target(store, fields["tenant_id"])[1]
        state = free_monthly.plan_state(runtime, tenant, runtime._catalog.read(store, ENTITLEMENT, fields["tenant_id"]),
                                        runtime._catalog.read(store, BILLING_POLICY, "stripe"))
    return Plan({"operation": fields["operation"], "tenant_id": fields["tenant_id"],
                 "before": {"plan_state": state, "enabled": tenant.get("enabled") is True},
                 "change": {key: value for key, value in detail.items() if key != "valid_until"}},
                guards, fields["tenant_id"], fields["tenant_id"])


def account_action_apply(tools, actor, fields, context):
    runtime = tools.runtime
    with runtime._catalog.store(write=True) as store:
        rows, guards, detail = _action_rows(tools, store, actor, fields, int(runtime._now()))
        return context.commit(store, rows, guards, {"operation": fields["operation"], "tenant_id": fields["tenant_id"],
                                                    "committed": True, **detail})


def _credit_grant(tools, fields):
    now = int(tools.runtime._now())
    expires = fields.get("expires_at", now + fields.get("valid_days", 30) * 86400)
    return credit_module.CreditGrant(fields["tenant_id"], fields["downloads"], expires, fields["reason"])


def credits_grant_plan(tools, actor, fields):
    runtime = tools.runtime
    grant = _credit_grant(tools, fields)
    with runtime._catalog.store() as store:
        tools.administration._target(store, grant.tenant_id)
        _rows, guards, detail = credit_module.grant_rows(runtime, store, grant, actor.actor_ref, int(runtime._now()))
        _row, ledger = credit_module.read_ledger(runtime, store, grant.tenant_id)
    held = credit_module.summary(ledger, runtime._now())["remaining"]
    return Plan({"tenant_id": grant.tenant_id, "downloads": grant.downloads, "expires_at": grant.expires_at,
                 "reason": grant.reason, "remaining_before": held, "remaining_after": held + grant.downloads,
                 "purchase": False, "overage_billing": False},
                guards, grant.tenant_id, grant.tenant_id, context=grant)


def credits_grant_apply(tools, actor, fields, context):
    runtime = tools.runtime
    with runtime._catalog.store(write=True) as store:
        tools.administration._target(store, fields["tenant_id"])
        rows, guards, detail = credit_module.grant_rows(runtime, store, context.plan.context, actor.actor_ref,
                                                        int(runtime._now()))
        return context.commit(store, rows, guards, {"tenant_id": fields["tenant_id"], "committed": True, **detail})


def credits_revoke_plan(tools, actor, fields):
    runtime = tools.runtime
    with runtime._catalog.store() as store:
        tools.administration._target(store, fields["tenant_id"])
        _rows, guards, detail = credit_module.revoke_rows(runtime, store, fields["tenant_id"], fields["grant_id"],
                                                          fields["reason"], actor.actor_ref, int(runtime._now()))
    return Plan({"tenant_id": fields["tenant_id"], **detail}, guards, fields["tenant_id"], fields["grant_id"])


def credits_revoke_apply(tools, actor, fields, context):
    runtime = tools.runtime
    with runtime._catalog.store(write=True) as store:
        tools.administration._target(store, fields["tenant_id"])
        rows, guards, detail = credit_module.revoke_rows(runtime, store, fields["tenant_id"], fields["grant_id"],
                                                         fields["reason"], actor.actor_ref, int(runtime._now()))
        return context.commit(store, rows, guards, {"tenant_id": fields["tenant_id"], "committed": True, **detail})


def activity_search(tools, actor, fields):
    from .activity import KINDS, ActivityQuery, search
    query = ActivityQuery(tuple(fields.get("kinds") or KINDS), fields.get("tenant_id"), fields.get("code"),
                          moment(fields.get("since")), moment(fields.get("until")), fields.get("page_size", 50),
                          fields.get("cursor", 0), not actor.may(ACTIVITY_READ))
    return search(tools.runtime, query, issuer=tools.administration.issuer, journal=tools.application.failure_journal)


def data_search(tools, actor, fields):
    """The served catalogue in the staff view: every item, not one account's grants, with usage for each item."""
    runtime = tools.runtime
    view = tools.application.provisioning.current_view()
    words = [word for word in fields.get("text", "").lower().split() if word]
    now = runtime._now()
    usage = {}
    with runtime._catalog.store() as store:
        for row in runtime._catalog.rows_all(store, USAGE):
            value = row["payload"]
            held = usage.setdefault(value.get("item_identity", ""), {"downloads": 0, "in_the_last_30_days": 0,
                                                                      "accounts": set(), "last_at": 0})
            held["downloads"] += 1
            held["in_the_last_30_days"] += 1 if value.get("at", 0) > now - RECENT_SECONDS else 0
            held["accounts"].add(value.get("tenant_id", ""))
            held["last_at"] = max(held["last_at"], value.get("at", 0))
    approved = view.approved_bindings()
    withdrawn = {identity for identity, _digest in view.withdrawn}
    rows = []
    for identity, item in sorted(view.catalogue.items.items()):
        haystack = " ".join((identity, item.kind, item.purpose, item.source_layer, item.family)).lower()
        if (any(word not in haystack for word in words) or fields.get("kind", item.kind) != item.kind
                or fields.get("source_layer", item.source_layer) != item.source_layer):
            continue
        held = usage.get(identity, {"downloads": 0, "in_the_last_30_days": 0, "accounts": set(), "last_at": 0})
        rows.append({"identity": identity, "kind": item.kind, "purpose": item.purpose, "digest": item.digest,
                     "size_bytes": item.size_bytes, "license": item.license_name, "family": item.family,
                     "source_layer": item.source_layer, "approved": identity in approved,
                     "withdrawn": identity in withdrawn,
                     "usage": {"downloads": held["downloads"], "in_the_last_30_days": held["in_the_last_30_days"],
                               "accounts": len(held["accounts"]), "last_download_at": held["last_at"] or None}})
    if fields.get("order") == "downloads":
        rows.sort(key=lambda row: (-row["usage"]["downloads"], row["identity"]))
    shown, following = page(rows, fields)
    return {"record_type": CATALOGUE_PAGE_VERSION, "items": shown, "total": len(rows), "next_cursor": following,
            "catalogue_release": view.release_id or None, "source": view.source}


def service_health(tools, actor, fields):
    """The measured health record, the newest refusal codes and the staff tools' own state."""
    from .staff_keys import ACTIVE, KEY as STAFF_KEY, key_state
    from .account_messages import mail_day
    diagnostics = tools.application._staff_diagnostics()
    now = tools.runtime._now()
    with tools.runtime._catalog.store() as store:
        active = sum(1 for row in tools.runtime._catalog.rows_all(store, STAFF_KEY)
                     if key_state(row["payload"], now) == ACTIVE)
        used = mail_day(tools.runtime, store, now)[1]["sent"]
    return {"record_type": HEALTH_VERSION, **{key: value for key, value in diagnostics.items() if key != "record_type"},
            "staff_tools": {"active_staff_keys": active, "staff_messages_today": used,
                            "staff_message_daily_cap": tools.settings.mail_daily_cap,
                            "catalogue_publishing": tools.catalogue is not None and tools.catalogue.publishing}}


TOOLS = (
    StaffTool("accounts_search", "Search accounts by address text, plan state, founding place, switched-off "
              "state and creation time, one page at a time. The analytics role receives counts only.",
              {"text": {"type": "string", "maxLength": 254}, "plan_state": {"enum": list(PLAN_STATES)},
               "founding": {"type": "boolean"}, "enabled": {"type": "boolean"}, "created_after": MOMENT,
               "created_before": MOMENT, **PAGE}, (ACCOUNTS_SEARCH, ACCOUNT_COUNTS), accounts_search,
              provider_reads=True),
    StaffTool("account_get", "One account: plan, entitlements, download credits, key metadata, usage totals and "
              "last activity.", {"tenant_id": TENANT}, (ACCOUNTS_READ,), account_get, required=("tenant_id",),
              provider_reads=True),
    StaffTool("account_action", "Grant or revoke free monthly Baltor Pro, or switch an account off or on. "
              "Plan first, then apply with the plan digest.",
              {"operation": {"enum": list(ACTION_PERMISSIONS)}, "tenant_id": TENANT},
              tuple(ACTION_PERMISSIONS.values()), account_action_plan, account_action_apply,
              required=("operation", "tenant_id"), provider_reads=True),
    StaffTool("credits_grant", "Grant download credits to one account: a number of downloads with an expiry and a "
              "reason. No purchase and no overage billing. Plan first, then apply with the plan digest.",
              {"tenant_id": TENANT, "downloads": {"type": "integer", "minimum": 1, "maximum": 100_000},
               "valid_days": {"type": "integer", "minimum": 1, "maximum": 366},
               "expires_at": {"type": "integer", "minimum": 1}, "reason": REASON},
              (CREDITS_GRANT,), credits_grant_plan, credits_grant_apply,
              required=("tenant_id", "downloads", "reason")),
    StaffTool("credits_revoke", "Revoke one grant of download credits; its unused downloads end. Plan first, then "
              "apply with the plan digest.",
              {"tenant_id": TENANT, "grant_id": {"type": "string", "pattern": "^[0-9a-f]{32}$"}, "reason": REASON},
              (CREDITS_REVOKE,), credits_revoke_plan, credits_revoke_apply,
              required=("tenant_id", "grant_id", "reason")),
    StaffTool("activity_search", "Administration events, staff tool calls, sign-ups and activations, downloads and "
              "refusals by code, filtered by account, kind and time. The analytics role receives counts only.",
              {"kinds": {"type": "array", "items": {"enum": ["staff_tool", "administration", "sign_up", "activation",
                                                              "download", "refusal"]}, "maxItems": 6},
               "tenant_id": TENANT, "code": {"type": "string", "maxLength": 128}, "since": MOMENT, "until": MOMENT,
               "page_size": {"type": "integer", "minimum": 1, "maximum": 200}, "cursor": {"type": "integer",
                                                                                         "minimum": 0}},
              (ACTIVITY_READ, ACTIVITY_COUNTS), activity_search),
    StaffTool("data_search", "Search the served catalogue in the staff view, every item with its approval, "
              "withdrawal and usage.",
              {"text": {"type": "string", "maxLength": 200}, "kind": {"type": "string", "maxLength": 64},
               "source_layer": {"type": "string", "maxLength": 64}, "order": {"enum": ["identity", "downloads"]},
               **PAGE}, (CATALOGUE_READ,), data_search),
    StaffTool("service_health", "The measured health record, the newest refusal codes, active staff keys and the "
              "staff message allowance used today.", {}, (SERVICE_DIAGNOSTICS,), service_health),
)
