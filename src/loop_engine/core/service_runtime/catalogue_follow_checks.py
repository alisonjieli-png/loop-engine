"""Replay of the runbook step that lets new customer accounts follow the catalogue release.

The live host of September 24, 2026 had `new_accounts_follow_release` false and
the starter identities of its catalogue, so every new customer account was given
a fixed list of the items served that day and would never receive a later item.
The runbook section "Let new accounts follow the catalogue release" changes
that. This module replays it through the service entry point against a real
service store, with the accounts the live host holds: the owner, which follows
the release; the diagnostic accounts, which hold empty fixed lists; and customer
accounts created by sign-up with the starter list.

```text
Runbook
├── 1 and 2  one host file edit: new_accounts_follow_release true and no
│            starter identities, then a restart; the host reader refuses both
│            settings together
├── 3        catalogue-status: read which accounts --all-tenants would move
├── 4        follow-catalogue-release --all-tenants: only accounts that already
│            receive every served item move; the diagnostic accounts stay empty
└── 5        the next release reaches every customer and no diagnostic account
```
"""
from __future__ import annotations

import tempfile
from unittest.mock import patch

from .catalogue_serving_checks import (BILLING, FIRST_ITEMS, FIRST_RELEASE_FOLLOW_STEP, ISOLATED, LATER_ITEM, OWNER,
                                       RunbookHost)

#: The runbook's steps after the host file edit, as the entry point receives them after `--config`.
FOLLOW_PREVIEW_STEP = ("catalogue-status",)
FOLLOW_CUSTOMERS_STEP = ("follow-catalogue-release", "--all-tenants")
CUSTOMERS = ("customer-before-a", "customer-before-b")
LATER_CUSTOMER = "customer-after"
IDENTITY_BLOCK = {"project_url": "http://127.0.0.1:9", "publishable_key_ref": "env:BALTOR_RUNBOOK_PUBLISHABLE",
                  "namespace_prefix": "customer", "registration_enabled": True, "allow_loopback": True}


class FollowHost(RunbookHost):
    """The runbook host after its first release, with sign-up and the live starter list switched on."""

    def __init__(self, root):
        super().__init__(root)
        self.first_release(FIRST_RELEASE_FOLLOW_STEP)
        for tenant in (ISOLATED, BILLING):
            # The live repair left each diagnostic account with an empty fixed list.
            self.runtime.set_grants(tenant, ())
        self.configure_sign_up(follows=False, starters=sorted(FIRST_ITEMS))
        self.customers = {}
        for subject in CUSTOMERS:
            self.customers[subject] = self.sign_up(subject)

    def configure_sign_up(self, *, follows, starters):
        self.configuration["catalogue"]["new_accounts_follow_release"] = follows
        self.configuration["browser_identity"] = {**IDENTITY_BLOCK, "starter_identities": list(starters)}
        self.save()

    def application(self):
        from .http_entrypoint import load_host_application
        return load_host_application(str(self.host))[0]

    def sign_up(self, subject):
        """The account a verified sign-up gets from the application the host file starts, and a key for it."""
        from .records import TenantKeyIssue
        adapter = self.application().browser_identity
        tenant = self.runtime.ensure_subject_tenant(adapter.registration_for(subject))["tenant_id"]
        self.runtime.set_operator_entitlement(tenant, valid_until=self.keys_valid_until(),
                                              evidence_ref="local-check-not-payment")
        self.keys[subject] = self.runtime.issue_key(TenantKeyIssue(tenant, "runbook customer")).key
        return tenant

    @staticmethod
    def keys_valid_until():
        import time
        return int(time.time()) + 3600

    def grant_record(self, tenant):
        from .runtime import GRANTS
        with self.runtime._catalog.store() as store:
            row = self.runtime._catalog.read(store, GRANTS, tenant)
        return row["payload"] if row is not None else None

    def offered(self):
        application = self.application()
        return {name: sorted(row["identity"] for row in application.provisioning.invoke(key, "list")["items"])
                for name, key in self.keys.items()}


def _later_release(host):
    host.publish({**FIRST_ITEMS, LATER_ITEM[0]: LATER_ITEM[1]})
    return host.offered()


def _runbook(root, *, move=True):
    """The documented procedure; returns what each account is offered after a later release, and the answers."""
    host = FollowHost(tempfile.mkdtemp(dir=root))
    host.configure_sign_up(follows=True, starters=())
    later = host.sign_up(LATER_CUSTOMER)
    preview = host.run(*FOLLOW_PREVIEW_STEP)[1]
    moved = host.run(*FOLLOW_CUSTOMERS_STEP)[1] if move else None
    return host, {"preview": preview, "moved": moved, "later_tenant": later, "offered": _later_release(host)}


def run_checks(check, root):
    """The follow runbook, replayed, with its known-wrong cases and removed-guard controls."""
    try:
        _checks(check, root)
    except Exception:  # noqa: BLE001 - a group that stops part way is a failure with a name
        check("the_follow_runbook_checks_ran_to_completion", False)


def _checks(check, root):
    everything = sorted([*FIRST_ITEMS, LATER_ITEM[0]])
    host = FollowHost(tempfile.mkdtemp(dir=root))
    host.configure_sign_up(follows=True, starters=sorted(FIRST_ITEMS))
    refused = host.run("catalogue-status")
    try:
        host.application()
        loaded = "loaded"
    except Exception as error:  # noqa: BLE001 - the refusal code is the answer
        loaded = getattr(error, "code", type(error).__name__)
    check("a_host_file_that_both_follows_the_release_and_names_starter_identities_is_refused",
          loaded == "invalid_starter_identities" and refused[0] == 0)
    stale = FollowHost(tempfile.mkdtemp(dir=root))
    stale_offered = _later_release(stale)
    check("the_live_setting_leaves_every_customer_on_the_starter_list_forever",
          all(stale.grant_record(tenant)["record_type"] == "service_grants/v1" for tenant in stale.customers.values())
          and all(stale_offered[subject] == sorted(FIRST_ITEMS) for subject in CUSTOMERS))
    host, outcome = _runbook(root)
    customers = sorted(host.customers.values())
    preview = outcome["preview"]["follow_all_tenants_preview"] if isinstance(outcome["preview"], dict) else {}
    reasons = {row["tenant_id"]: row["reason"] for row in preview.get("left_out", ())}
    check("the_preview_names_exactly_the_customer_accounts_and_writes_nothing",
          preview.get("would_follow") == customers
          and reasons.get(ISOLATED) == "not_granted_every_item" and reasons.get(BILLING) == "not_granted_every_item"
          and reasons.get(OWNER) == "already_following" and reasons.get(outcome["later_tenant"]) == "already_following")
    check("the_move_follows_the_preview_and_the_diagnostic_accounts_keep_their_empty_lists",
          isinstance(outcome["moved"], dict) and outcome["moved"]["tenants"] == customers
          and all(host.grant_record(tenant) == {"record_type": "service_grants/v1", "tenant_id": tenant, "grants": []}
                  for tenant in (ISOLATED, BILLING)))
    offered = outcome["offered"]
    check("after_the_runbook_the_next_release_reaches_every_customer_and_no_diagnostic_account",
          all(offered[name] == everything for name in (*CUSTOMERS, LATER_CUSTOMER, OWNER))
          and offered[ISOLATED] == [] and offered[BILLING] == [])
    _host, skipped = _runbook(root, move=False)
    check("without_the_move_the_customers_that_signed_up_before_never_see_the_later_item",
          all(skipped["offered"][subject] == sorted(FIRST_ITEMS) for subject in CUSTOMERS)
          and skipped["offered"][LATER_CUSTOMER] == everything)
    from . import catalogue_grants
    with patch.object(catalogue_grants, "left_out_reason", lambda *arguments: ""):
        wrong_host, wrong = _runbook(root)
    wrong_preview = wrong["preview"]["follow_all_tenants_preview"] if isinstance(wrong["preview"], dict) else {}
    check("removed_every_item_rule_is_detected_by_the_preview_and_the_isolation_result",
          ISOLATED in wrong_preview.get("would_follow", ()) and wrong["offered"][ISOLATED] == everything)
    guarded = FollowHost(tempfile.mkdtemp(dir=root))
    runtime, view = _served(guarded)
    guarded.runtime.set_grants(ISOLATED, catalogue_grants.ReleaseFollowingGrants(ISOLATED, frozenset()).materialize(view))
    runtime, view = _served(guarded)
    try:
        catalogue_grants.follow_accounts_already_granted(runtime, view, keep_fixed=(ISOLATED,))
        kept = "moved"
    except Exception as error:  # noqa: BLE001 - the refusal code is the answer
        kept = getattr(error, "code", type(error).__name__)
    check("an_account_kept_fixed_that_would_move_refuses_the_whole_move_and_writes_nothing",
          kept == "kept_account_would_move"
          and guarded.grant_record(ISOLATED)["record_type"] == "service_grants/v1"
          and all(guarded.grant_record(tenant)["record_type"] == "service_grants/v1"
                  for tenant in guarded.customers.values()))


def _served(host):
    from .catalogue_commands import served_view
    return served_view(str(host.host))


__all__ = ["FOLLOW_CUSTOMERS_STEP", "FOLLOW_PREVIEW_STEP", "run_checks"]
