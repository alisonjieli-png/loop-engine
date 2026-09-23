"""Re-apply and verify the host's two billing policies after a release.

The host file names two policies. The billing entitlement policy says which
provider prices grant paid access. The billing session policy says what
checkout and the customer portal offer. Each is stored once with a digest, and
every checkout, portal session and payment notification compares the stored
digest with the one the running release computes from the host file.

Host setup, `loop-engine service configure`, installs both once and cannot run
again, because it also registers tenants. Release 13 computed a different
session digest from an unchanged host file, so checkout and the portal were
unavailable with nothing to repair them, and the health record did not say so.
This module holds the repair and the check:

- `apply_host_billing_policy` re-applies both policies from the host file
  through the existing writers. It reads each held record version first and
  names it as the exact expected revision, and it reports the digests it held
  and wrote.
- `billing_policy_refusal` names why the stored policies do not serve the
  running configuration. The health record and the command both read it.

Neither reaches the payment provider, registers anything or prints a secret.
This module holds internal runtime mechanics; the transport Loop that already
owns the request owns these records.
"""
from __future__ import annotations

from dataclasses import asdict
import json

from .billing_effects import SESSION_POLICY_IDENTITY, SESSION_POLICY_KIND, SESSION_POLICY_VERSION
from .records import ServiceRuntimeError, digest
from .runtime import BILLING_POLICY, SCHEMAS

APPLICATION_VERSION = "service_billing_policy_application/v1"
#: A changed entitlement policy ends the paid access recorded under the held
#: one. Each such entitlement names the digest it was decided under, and a
#: different stored digest reads it as no access until the account's next
#: subscription notification decides it again. The command refuses that change
#: while any account holds paid access, unless the operator says so; the
#: release workflow never says so.
PAID_ACCESS_REFUSAL = "billing_policy_change_ends_paid_access"
REFUSAL_VERSION = "service_billing_policy_refusal/v1"
#: The refusals of this command that an operator must be able to read. The
#: `loop-engine service` wrapper reports every other refusal by one generic
#: code, so these are printed here, as a record of their own, with exit
#: status one. Each is a stable code from this source and carries no value of
#: the host file.
APPLICATION_REFUSALS = ("session_price_not_in_billing_policy", PAID_ACCESS_REFUSAL,
                        "billing_policy_revision_required", "session_policy_revision_required")


def _held_billing_policy(runtime):
    """The stored entitlement policy's record version and digest, or None. This reads."""
    with runtime._catalog.store() as store:
        row = runtime._catalog.read(store, BILLING_POLICY, "stripe")
    if row is None:
        return None
    return {"record_version": row["record_version"],
            "policy_digest": runtime._payload(row, BILLING_POLICY)["policy_digest"]}


def _other_session_policy_versions(runtime):
    """The versions of stored session policies this release does not read, left for a rollback."""
    own = runtime._catalog.identity(SESSION_POLICY_KIND, SESSION_POLICY_IDENTITY)
    with runtime._catalog.store() as store:
        rows = runtime._catalog.rows_all(store, SESSION_POLICY_KIND)
    return sorted({str(row["payload"].get("record_type")) for row in rows if row["record_id"] != own})


def billing_policy_refusal(application):
    """Name why the stored billing policies do not serve the running configuration, or return empty text.

    This reads; it never writes. Three facts must hold. The stored entitlement
    policy is the one the host file names, or every payment notification is
    refused with `billing_policy_mismatch`. The stored session policy is the one
    the running configuration computes. The session policy was stored against
    the entitlement policy stored now. The last two are the exact comparison
    every checkout and portal session makes, so this answer and the session
    routes cannot disagree. Only a code is returned, never a digest.
    """
    sessions, processor = application.billing_sessions, application.billing_processor
    if processor is not None:
        held = _held_billing_policy(application.runtime)
        if held is None:
            return "billing_policy_not_installed"
        if held["policy_digest"] != digest(asdict(processor.policy)):
            return "billing_policy_changed"
    if sessions is not None:
        try:
            sessions.effects.policy_available(sessions.policy_digest)
        except ServiceRuntimeError as error:
            return error.code
    return ""


def _session_prices_outside(policy, sessions):
    """The session prices the entitlement policy does not name. Checked before anything is written."""
    return sorted({plan.price_id for plan in sessions.configuration.plans} - set(policy.allowed_price_ids))


def _accounts_with_paid_access(runtime):
    """How many accounts hold paid access now, under the held entitlement policy. This reads."""
    return runtime.access_source_report()["counts"]["revenue_bearing"]


def _session_report(held, written, billing_digest, runtime):
    return {"record_type": SESSION_POLICY_VERSION,
            "held_record_version": held["record_version"] if held else None,
            "held_policy_digest": held["policy_digest"] if held else None,
            "held_billing_policy_digest": held["billing_policy_digest"] if held else None,
            "record_version": written["record_version"], "policy_digest": written["policy_digest"],
            "billing_policy_digest": billing_digest,
            "changed": held is None or written["record_version"] != held["record_version"],
            "other_record_versions": _other_session_policy_versions(runtime)}


def apply_billing_policy(application, configuration, *, reset_paid_access=False):
    """Re-apply both billing policies of one loaded host file through the existing writers.

    Each held record version is read first and named as the exact expected
    revision, so a writer that changed a record in between is refused rather
    than overwritten. A host file whose session prices are not all in its own
    entitlement policy is refused before anything is written. A second run
    finds both policies current and changes nothing.
    """
    if type(reset_paid_access) is not bool:
        raise ServiceRuntimeError("invalid_request", "the paid access choice is an explicit Boolean")
    settings = configuration.get("billing") or {}
    sessions = application.billing_sessions
    report = {"record_type": APPLICATION_VERSION, "billing_installed": bool(settings),
              "sessions_installed": sessions is not None, "tenants_registered": 0,
              "remote_accounts_created": False, "provider_calls": 0}
    if not settings:
        return {**report, "billing_policy": None, "session_policy": None, "changed": False,
                "every_installed_policy_current": True, "refusal": "",
                "paid_access_ended_for_accounts": 0, "checkout_expected": False, "portal_expected": False}
    from .billing_records import StripeEntitlementPolicy
    runtime = application.runtime
    policy = StripeEntitlementPolicy(**settings["policy"])
    if sessions is not None and _session_prices_outside(policy, sessions):
        raise ServiceRuntimeError("session_price_not_in_billing_policy")
    held = _held_billing_policy(runtime)
    ended = 0
    if held is not None and held["policy_digest"] != digest(asdict(policy)):
        ended = _accounts_with_paid_access(runtime)
        if ended and not reset_paid_access:
            raise ServiceRuntimeError(PAID_ACCESS_REFUSAL, f"{ended} accounts hold paid access under the held "
                                      "billing policy and would lose it until their next subscription event")
    applied = runtime.configure_billing_policy(policy, expected_version=held["record_version"] if held else None)
    billing = {"record_type": SCHEMAS[BILLING_POLICY],
               "held_record_version": held["record_version"] if held else None,
               "held_policy_digest": held["policy_digest"] if held else None,
               "record_version": applied["record_version"], "policy_digest": applied["policy_digest"],
               "changed": held is None or applied["record_version"] != held["record_version"]}
    session = None
    if sessions is not None:
        held_session = sessions.effects.held_policy()
        written = sessions.configure_policy(
            expected_version=held_session["record_version"] if held_session else None)
        session = _session_report(held_session, written, applied["policy_digest"], runtime)
    refusal = billing_policy_refusal(application)
    offered = sessions.host_offers() if sessions is not None else {"checkout": False, "portal": False}
    return {**report, "billing_policy": billing, "session_policy": session,
            "changed": billing["changed"] or bool(session and session["changed"]),
            "every_installed_policy_current": not refusal, "refusal": refusal,
            "paid_access_ended_for_accounts": ended,
            "checkout_expected": offered["checkout"], "portal_expected": offered["portal"]}


def apply_host_billing_policy(path, *, reset_paid_access=False):
    """Load one host file and re-apply its billing policies."""
    from .http_entrypoint import load_host_application
    application, configuration = load_host_application(path)
    return apply_billing_policy(application, configuration, reset_paid_access=reset_paid_access)


def run_command(path, *, reset_paid_access=False):
    """The `apply-billing-policy` command: print one record and return the exit status.

    Status zero means every installed policy is current. A refusal this command
    declares prints a `service_billing_policy_refusal/v1` record with its code
    and returns one; any other failure is raised to the wrapper as before.
    """
    try:
        applied = apply_host_billing_policy(path, reset_paid_access=reset_paid_access)
    except ServiceRuntimeError as error:
        if error.code not in APPLICATION_REFUSALS:
            raise
        print(json.dumps({"record_type": REFUSAL_VERSION, "code": error.code}, sort_keys=True))
        return 1
    print(json.dumps(applied, sort_keys=True))
    return 0 if applied["every_installed_policy_current"] else 1
