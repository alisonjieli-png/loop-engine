"""Staff administration of accounts: an overview, the account list and four account actions.

Kind: internal service mechanics used by the governed HTTP operations of the
administration routes. It adds no runtime type, no store and no graph vertex.

```text
Staff administration
├── Who is staff: a signed-in browser session of an account the service
│   honours, whose provider identity or address the host's staff list names
├── GET  /api/v1/admin/overview   the caller's role, its permissions, and the
│   counts and diagnostics that role may read
├── GET  /api/v1/admin/accounts   every account with its address, creation,
│   confirmation, plan and last use (superadmin)
└── POST /api/v1/admin/accounts   one action (superadmin)
    ├── grant_free_monthly, revoke_free_monthly, disable, enable
    ├── one request identity: a repeat returns the first result, and a
    │   changed request under the same identity is refused
    ├── the session must be current and not signed out when the write commits
    └── the account change and its audit record commit together
```

A host service key never holds a staff role, and nothing in a request can
name one. The permissions of each role are the table in `account_policy.py`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import uuid

from .account_policy import (ACCOUNT_COUNTS, ACCOUNTS_LIST, ACTION_PERMISSIONS, SERVICE_DIAGNOSTICS,
                             USAGE_COUNTS, ServiceAccountPolicy, permissions_for)
from . import free_monthly
from .free_monthly import PLAN_STATES
from .records import ServiceRuntimeError, digest, identifier
from .runtime import BILLING_POLICY, ENTITLEMENT, SESSION_REVOCATION, SUBJECT, TENANT, USAGE

REQUEST_VERSION = "service_account_administration_request/v1"
RESULT_VERSION = "service_account_administration_result/v1"
OVERVIEW_VERSION = "service_staff_overview/v1"
LISTING_VERSION = "service_account_listing/v1"
AUDIT, AUDIT_VERSION = "service_account_administration_event", "service_account_administration_event/v1"
OPERATIONS = tuple(ACTION_PERMISSIONS)
DISPLAY_LIMIT = 2000
RECENT_SECONDS = 30 * 86400


@dataclass(frozen=True)
class AccountAdministrationRequest:
    """One superadmin action on one account, under one request identity."""

    operation: str
    request_id: str
    tenant_id: str
    record_type: str = REQUEST_VERSION

    def __post_init__(self):
        if self.record_type != REQUEST_VERSION or self.operation not in OPERATIONS:
            raise ServiceRuntimeError("invalid_account_administration_request")
        identifier(self.request_id, "request identity")
        identifier(self.tenant_id, "account identity")

    @classmethod
    def from_dict(cls, value):
        if (not isinstance(value, dict) or set(value) != {"record_type", "operation", "request_id", "tenant_id"}
                or value.get("record_type") != REQUEST_VERSION):
            raise ServiceRuntimeError("invalid_account_administration_request")
        try:
            return cls(**value)
        except TypeError:
            raise ServiceRuntimeError("invalid_account_administration_request") from None

    def identity(self):
        return digest({"record_type": self.record_type, "operation": self.operation,
                       "request_id": self.request_id, "tenant_id": self.tenant_id})


@dataclass(frozen=True)
class StaffSession:
    """Verified facts about one staff request, built by the transport after a fresh check."""

    principal: object = field(repr=False)
    subject: str
    role: str
    credential_digest: str = field(repr=False)
    expires_at: float
    #: The verified address of the staff member, which a sign-up link message names.
    email: str = field(default="", repr=False)


class AccountAdministration:
    """Staff reads and superadmin actions over the existing catalogue records."""

    def __init__(self, runtime, policy, issuer, *, origins=None, identity_secret=None):
        if not isinstance(policy, ServiceAccountPolicy) or not isinstance(issuer, str) or not issuer:
            raise ServiceRuntimeError("invalid_account_policy")
        if identity_secret is not None and not callable(identity_secret):
            raise ServiceRuntimeError("invalid_account_policy")
        self.runtime, self.policy, self.issuer = runtime, policy, issuer
        self.origins, self._identity_secret = origins, identity_secret

    def role_of(self, authentication):
        """The staff role of one authenticated request, or empty text.

        Only a browser session carries a verified identity. A service key, a
        protocol token or anything a request says names no role.
        """
        from .http_auth import BROWSER_IDENTITY_AUTHENTICATION
        identity = getattr(authentication, "identity", None)
        if getattr(authentication, "mode", None) != BROWSER_IDENTITY_AUTHENTICATION or identity is None:
            return ""
        return self.policy.role_for(identity.subject, identity.email)

    def staff_session(self, authentication, credential_digest):
        role = self.role_of(authentication)
        if not role:
            raise ServiceRuntimeError("staff_role_required")
        return StaffSession(authentication.principal, authentication.identity.subject, role, credential_digest,
                            float(authentication.expires_at), authentication.identity.email)

    def _current_session(self, store, staff):
        """Recheck the staff member's account, the sign-out record and the expiry inside one read."""
        if not isinstance(staff, StaffSession) or not staff.role:
            raise ServiceRuntimeError("staff_role_required")
        current, guards = self.runtime._revalidate(store, staff.principal)
        catalog = self.runtime._catalog
        if catalog.read(store, SESSION_REVOCATION, staff.credential_digest) is not None:
            raise ServiceRuntimeError("unauthorized")
        if staff.expires_at <= self.runtime._now():
            raise ServiceRuntimeError("unauthorized")
        return current, (*guards, catalog.guard(None, catalog.identity(SESSION_REVOCATION, staff.credential_digest)))

    @staticmethod
    def _require(staff, permission):
        if permission not in permissions_for(staff.role):
            raise ServiceRuntimeError("account_administration_forbidden")

    def _accounts(self, store):
        """Every account a person signs in to, with its plan, from the service records."""
        catalog, runtime = self.runtime._catalog, self.runtime
        policy_row = catalog.read(store, BILLING_POLICY, "stripe")
        last_item = {}
        for row in catalog.rows_all(store, USAGE):
            value = row["payload"]
            tenant_id, moment = value.get("tenant_id", ""), value.get("at")
            if type(moment) in (int, float) and moment > last_item.get(tenant_id, 0):
                last_item[tenant_id] = moment
        accounts = {}
        for row in catalog.rows_all(store, SUBJECT):
            subject = runtime._payload(row, SUBJECT)
            if subject.get("issuer") != self.issuer:
                continue
            tenant_id = subject.get("tenant_id", "")
            tenant_row = catalog.read(store, TENANT, tenant_id)
            if tenant_row is None:
                continue
            tenant = runtime._payload(tenant_row, TENANT)
            entitlement_row = catalog.read(store, ENTITLEMENT, tenant_id)
            state = free_monthly.plan_state(runtime, tenant, entitlement_row, policy_row)
            until = (runtime._payload(entitlement_row, ENTITLEMENT).get("valid_until")
                     if entitlement_row is not None and state != "none" else None)
            accounts[subject.get("subject", "")] = {
                "tenant_id": tenant_id, "enabled": tenant.get("enabled") is True,
                "sign_in_enabled": subject.get("enabled") is True, "plan_state": state,
                "plan_valid_until": until, "last_item_at": last_item.get(tenant_id)}
        return accounts

    def overview(self, staff, *, diagnostics=None):
        """The caller's role and what that role may read: counts for analytics, diagnostics for developers."""
        with self.runtime._catalog.store() as store:
            self._current_session(store, staff)
            permissions = permissions_for(staff.role)
            result = {"record_type": OVERVIEW_VERSION, "role": staff.role, "permissions": sorted(permissions)}
            if ACCOUNT_COUNTS in permissions:
                accounts = self._accounts(store)
                result["account_counts"] = {
                    "accounts": len(accounts), "switched_off": sum(not row["enabled"] for row in accounts.values()),
                    "plans": {name: sum(row["plan_state"] == name for row in accounts.values()) for name in PLAN_STATES},
                    "founding_holders": len(free_monthly.founding_holders(self.runtime)),
                    "founding_limit": self.policy.founding_free_monthly_accounts}
            if USAGE_COUNTS in permissions:
                rows = self.runtime._catalog.rows_all(store, USAGE)
                since = self.runtime._now() - RECENT_SECONDS
                result["usage_counts"] = {
                    "downloads": len(rows),
                    "downloads_in_the_last_30_days": sum(1 for row in rows if (row["payload"].get("at") or 0) > since),
                    "accounts_with_a_download_in_the_last_30_days": len({
                        row["payload"].get("tenant_id") for row in rows if (row["payload"].get("at") or 0) > since})}
        if SERVICE_DIAGNOSTICS in permissions and diagnostics is not None:
            result["diagnostics"] = diagnostics()
        return result

    def accounts(self, staff):
        """Every account, joined from the identity provider and the service records (superadmin)."""
        self._require(staff, ACCOUNTS_LIST)
        from .staff_sign_up_links import links_by_subject
        with self.runtime._catalog.store() as store:
            self._current_session(store, staff)
            service = self._accounts(store)
            holders = set(free_monthly.founding_holders(self.runtime))
            links = links_by_subject(self.runtime, store, self.issuer)
        users, details = [], False
        if self.origins is not None and self._identity_secret is not None:
            users, details = self.origins.administration.all_users(self._identity_secret()), True
        rows, seen = [], set()
        for user in users:
            seen.add(user.user_id)
            held = service.get(user.user_id, {})
            rows.append({"provider_user_id": user.user_id, "email": user.email, "created_at": user.created_at,
                         "email_confirmed": bool(user.email_confirmed_at),
                         "email_confirmed_at": user.email_confirmed_at, "last_sign_in_at": user.last_sign_in_at,
                         "created_by_this_service": self.origins.honoured(user),
                         "founding": held.get("tenant_id") in holders, "sign_up_link": links.get(user.user_id),
                         **self._service_fields(held)})
        for subject, held in service.items():
            if subject not in seen:
                rows.append({"provider_user_id": subject, "email": "", "created_at": "", "email_confirmed": None,
                             "email_confirmed_at": "", "last_sign_in_at": "", "created_by_this_service": None,
                             "founding": held["tenant_id"] in holders, "sign_up_link": links.get(subject),
                             **self._service_fields(held)})
        rows.sort(key=lambda row: (row["created_at"] or "", row["provider_user_id"]), reverse=True)
        return {"record_type": LISTING_VERSION, "accounts": rows[:DISPLAY_LIMIT], "total": len(rows),
                "display_limit": DISPLAY_LIMIT, "identity_details_available": details,
                "founding_limit": self.policy.founding_free_monthly_accounts, "founding_holders": len(holders),
                "operations": list(OPERATIONS)}

    @staticmethod
    def _service_fields(held):
        return {"tenant_id": held.get("tenant_id", ""), "enabled": held.get("enabled"),
                "plan_state": held.get("plan_state", "none"), "plan_valid_until": held.get("plan_valid_until"),
                "last_item_at": held.get("last_item_at")}

    def _target(self, store, tenant_id):
        """Only an account a person signs in to can be changed here, never a host tenant."""
        if not any(self.runtime._payload(row, SUBJECT).get("issuer") == self.issuer
                   for row in self.runtime._catalog.rows(store, SUBJECT, tenant_id)):
            raise ServiceRuntimeError("account_not_found")
        return self.runtime._tenant(store, tenant_id)

    def _effect(self, store, staff, current, request, now):
        runtime = self.runtime
        tenant_row, tenant = self._target(store, request.tenant_id)
        actor = "staff:" + staff.subject
        if request.operation == "grant_free_monthly":
            return free_monthly.grant_rows(runtime, store, request.tenant_id, now, actor)
        if request.operation == "revoke_free_monthly":
            return free_monthly.revoke_rows(runtime, store, request.tenant_id, now, actor)
        wanted = request.operation == "enable"
        if not wanted and request.tenant_id == current.tenant_id:
            raise ServiceRuntimeError("staff_cannot_switch_off_own_account")
        if (tenant.get("enabled") is True) == wanted:
            raise ServiceRuntimeError("account_state_unchanged")
        changed = {**tenant_row, "record_version": uuid.uuid4().hex,
                   "payload": {**tenant, "enabled": wanted, "enabled_changed_at": now,
                               "enabled_changed_by": actor}}
        return (changed,), (runtime._catalog.guard(tenant_row),), {"enabled": wanted}

    def apply(self, staff, request):
        """Apply one action and its audit record together, or replay the first result of its identity."""
        if not isinstance(request, AccountAdministrationRequest):
            raise ServiceRuntimeError("invalid_account_administration_request")
        self._require(staff, ACTION_PERMISSIONS[request.operation])
        catalog = self.runtime._catalog
        with catalog.store(write=True) as store:
            current, guards = self._current_session(store, staff)
            key = (self.issuer, staff.subject, request.request_id)
            held = catalog.read(store, AUDIT, key)
            if held is not None:
                if held["payload"].get("record_type") != AUDIT_VERSION:
                    raise ServiceRuntimeError("unsupported_or_corrupt_record")
                if held["payload"].get("request_digest") != request.identity():
                    raise ServiceRuntimeError("account_administration_request_identity_conflict")
                return {**held["payload"]["result"], "replayed": True}
            now = int(self.runtime._now())
            rows, action_guards, detail = self._effect(store, staff, current, request, now)
            result = {"record_type": RESULT_VERSION, "committed": True, "operation": request.operation,
                      "tenant_id": request.tenant_id, "request_id": request.request_id, **detail}
            event = catalog.record(AUDIT, key, {
                "record_type": AUDIT_VERSION, "actor_subject": staff.subject, "actor_role": staff.role,
                "actor_tenant_id": current.tenant_id, "operation": request.operation,
                "tenant_id": request.tenant_id, "request_digest": request.identity(), "result": result,
                "at": now}, tenant_id=request.tenant_id)
            unique = {}
            for guard in (*guards, *action_guards, catalog.guard(None, event["record_id"])):
                if guard.record_id in unique and unique[guard.record_id] != guard:
                    raise ServiceRuntimeError("concurrent_update")
                unique[guard.record_id] = guard
            # The time check runs again right before the write: a session that
            # expired while the action was prepared changes nothing.
            if staff.expires_at <= self.runtime._now():
                raise ServiceRuntimeError("unauthorized")
            catalog.commit(store, (*rows, event), tuple(unique.values()))
        return {**result, "replayed": False}

    def audit_events(self):
        """Every recorded staff action, newest first."""
        catalog = self.runtime._catalog
        with catalog.store() as store:
            rows = [row["payload"] for row in catalog.rows_all(store, AUDIT)
                    if row["payload"].get("record_type") == AUDIT_VERSION]
        return sorted(rows, key=lambda row: -row.get("at", 0))

