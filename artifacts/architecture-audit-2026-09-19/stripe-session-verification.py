"""Restored in-memory mutants for the bounded billing session adapter.

All stores are temporary and all provider transports are explicitly injected.
The suite uses real loopback HTTP but never contacts Stripe or a remote issuer.
The output is source-bound evidence, not deployed payment qualification.
"""
from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path
import textwrap
from unittest.mock import patch

from loop_engine.core.service_runtime import billing_effects as effects
from loop_engine.core.service_runtime import http
from loop_engine.core.service_runtime import stripe_sessions as sessions
from loop_engine.core.service_runtime import stripe_session_checks as domain
from loop_engine.core.service_runtime import stripe_session_transport_checks as transport


def collect(function):
    records = []
    function(lambda name, passed: records.append({"test": name, "passed": bool(passed)}))
    return records


def rewritten(function, module, before, after):
    source = textwrap.dedent(inspect.getsource(function))
    if source.count(before) != 1:
        raise RuntimeError("mutation target must occur once: " + before)
    namespace = dict(vars(module))
    exec(compile(source.replace(before, after), "<billing-session-mutant>", "exec"), namespace)
    return namespace[function.__name__]


def main():
    baseline = sessions.self_test()
    if not baseline["all_passed"]:
        print(json.dumps({"baseline": baseline, "all_detected": False}, indent=2))
        return 1
    targets = (
        ("remove_explicit_network_and_session_authority", sessions.StripeSessionAdapter, "create", sessions,
         'if config.allow_network is not True or config.allow_session_creation is not True:', 'if False:', domain.run_domain_checks),
        ("substitute_a_different_server_price", sessions.StripeSessionAdapter, "create", sessions,
         '("line_items[0][price]", price_id)', '("line_items[0][price]", "price_other")', domain.run_domain_checks),
        ("ignore_provider_account_identity", sessions.StripeSessionAdapter, "create", sessions,
         'if account.get("id") != config.account_id:', 'if False:', domain.run_domain_checks),
        ("ignore_customer_live_mode", sessions.StripeSessionAdapter, "create", sessions,
         'observed_customer.get("livemode") is not config.livemode', 'False', domain.run_domain_checks),
        ("allow_inactive_price", sessions.StripeSessionAdapter, "create", sessions,
         'price.get("active") is not True', 'False', domain.run_domain_checks),
        ("accept_arbitrary_redirect_host", sessions.StripeSessionAdapter, "create", sessions,
         'location.hostname != expected_host', 'False', transport._response_checks),
        ("accept_expired_checkout_session", sessions.StripeSessionAdapter, "create", sessions,
         'response["expires_at"] <= time.time()', 'False', transport._response_checks),
        ("accept_changed_cancel_return_URL", sessions.StripeSessionAdapter, "create", sessions,
         'response.get("cancel_url") != config.checkout_cancel_url', 'False', transport._response_checks),
        ("accept_changed_portal_configuration", sessions.StripeSessionAdapter, "create", sessions,
         'response.get("configuration") != config.portal_configuration_id', 'False', transport._response_checks),
        ("drop_reserved_authority_read_set", effects.BillingSessionEffectStore, "authorize_dispatch", effects,
         'for guard in reservation.authority_guards:', 'for guard in ():', domain.run_domain_checks),
        ("allow_forged_reservation_guard_removal", effects.BillingSessionEffectStore, "_reserved", effects,
         'not hmac.compare_digest(reservation._proof, self._proof(reservation))', 'False', domain.run_domain_checks),
        ("ignore_changed_effect_under_same_request", effects.BillingSessionEffectStore, "begin", effects,
         'if state["spec_digest"] != spec.digest or state["spec"] != asdict(spec):', 'if False:', domain.run_domain_checks),
        ("create_a_fresh_provider_identity_on_retry", effects.BillingSessionEffectStore, "begin", effects,
         'state = dict(self._payload(previous, SESSION_EFFECT_VERSION))',
         'state = dict(self._payload(previous, SESSION_EFFECT_VERSION))\n'
         '            state["idempotency_key"] = "le-session-" + uuid.uuid4().hex', domain.run_domain_checks),
        ("ignore_provider_retention_window", effects.BillingSessionEffectStore, "begin", effects,
         'if now >= state["retry_before"]:', 'if False:', domain.run_domain_checks),
        ("accept_changed_confirmed_provider_identity", effects.BillingSessionEffectStore, "finish", effects,
         'if state["provider_session_id"] and state["provider_session_id"] != provider_session_id:', 'if False:', transport._response_checks),
        ("borrow_subject_billing_scope_from_narrow_token", http.ServiceHttpApplication, "_create_billing_session", http,
         'self._require_scope(current, BILLING_MANAGE_SCOPE)', 'pass', transport._token_checks),
        ("follow_Stripe_redirect", sessions, "_send", sessions,
         'follow_redirects=False', 'follow_redirects=True', transport._wire_checks),
        ("remove_Stripe_response_byte_limit", sessions, "_send", sessions,
         'if size > request.maximum_response_bytes:', 'if False:', transport._wire_checks),
    )
    for function in dict.fromkeys(row[-1] for row in targets):
        if not all(row["passed"] for row in collect(function)):
            raise RuntimeError("unmutated isolated suite failed: " + function.__name__)
    observations = []
    for name, owner, attribute, module, before, after, function in targets:
        changed = rewritten(getattr(owner, attribute), module, before, after)
        with patch.object(owner, attribute, changed):
            try:
                failed = [row["test"] for row in collect(function) if not row["passed"]]
                observation = {"mutant": name, "detected": bool(failed), "failed_checks": failed}
            except Exception as error:
                observation = {"mutant": name, "detected": False, "exception_type": type(error).__name__,
                               "detail": "fixture interruption is not counted as named-check detection"}
        observations.append(observation)
    root = Path.cwd()
    paths = [root / "src/loop_engine/core/service_runtime" / name for name in (
        "billing_effects.py", "stripe_sessions.py", "stripe_session_checks.py", "stripe_session_transport_checks.py",
        "http.py", "http_auth.py", "http_entrypoint.py")]
    output = {"record_type": "billing_session_verification/v1", "baseline": baseline,
              "mutants": observations, "all_detected": all(row["detected"] for row in observations),
              "external_network_calls": 0, "live_payment_provider_qualified": False,
              "limitations": ["injected provider records, not Stripe interoperability",
                              "loopback identity issuer, not a deployed OAuth authorization flow",
                              "response timeout cannot preempt an already running synchronous callback"],
              "source_sha256": {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}}
    print(json.dumps(output, indent=2))
    return 0 if output["all_detected"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
