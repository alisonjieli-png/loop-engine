"""Offline durable service verification and in-memory behavioral mutants.

Real temporary SQLite databases and local signed webhook fixtures are used.
No Stripe account, network provider, purchase, deployment, or generated code
execution is authorized by this runner. Runtime source is never rewritten.
"""
from __future__ import annotations

import hashlib
import importlib
import inspect
import json
from pathlib import Path
import textwrap
from unittest.mock import patch

MODULES = (
    "loop_engine.core.service_runtime.runtime",
    "loop_engine.core.service_runtime.billing",
    "loop_engine.core.service_runtime.stripe_provider",
    "loop_engine.core.provisioning_server",
    "loop_engine.catalog.protocol",
    "loop_engine.catalog.stores.sqlite_store",
    "loop_engine.core.record_operations_checks",
)


def checks(module):
    try:
        rows = module.self_test()["tests"]
        return {"module": module.__name__, "checks": len(rows),
                "failed": [row.get("test", row.get("name", "unnamed")) for row in rows if row.get("passed") is not True],
                "not_tested": [row for row in rows if row.get("not_tested")]}
    except Exception as error:
        return {"module": module.__name__, "checks": None,
                "failed": [type(error).__name__ + ": " + str(error)], "not_tested": []}


def rewrite(function, old, new):
    source = textwrap.dedent(inspect.getsource(function))
    if source.count(old) != 1:
        raise RuntimeError("mutant target must be unique: " + old)
    scope = {}
    exec(compile(source.replace(old, new), "<durable-service-mutant>", "exec"), function.__globals__, scope)
    return scope[function.__name__]


def main():
    modules = [importlib.import_module(name) for name in MODULES]
    runtime, billing, provider, _server, protocol, sqlite = modules[:6]
    storage = importlib.import_module("loop_engine.core.service_runtime.storage")
    baseline = [checks(module) for module in modules]
    mutants = []

    def exercise(name, owner, attribute, replacement, module):
        with patch.object(owner, attribute, replacement):
            outcome = checks(module)
        mutants.append({"name": name, "detected": bool(outcome["failed"]), "failing_checks": outcome["failed"]})

    exercise("ignore_catalog_read_set", sqlite.SQLiteRecordStore, "apply_batch", rewrite(
        sqlite.SQLiteRecordStore.apply_batch,
        'if ((expected.must_not_exist and held is not None)',
        'if False and ((expected.must_not_exist and held is not None)'), runtime)
    exercise("omit_batch_rollback", sqlite.SQLiteRecordStore, "apply_batch", rewrite(
        sqlite.SQLiteRecordStore.apply_batch, 'self._con.rollback()', 'pass'), runtime)
    exercise("ignore_key_revocation", runtime.ServiceRuntime, "_principal", rewrite(
        runtime.ServiceRuntime._principal, 'if data.get("enabled") is not True:', 'if False:'), runtime)
    exercise("trust_unissued_or_stale_principal", runtime.ServiceRuntime, "_revalidate",
             lambda self, store, principal: (principal, ()), runtime)
    exercise("discard_usage_idempotency", runtime.ServiceRuntime, "record_usage", rewrite(
        runtime.ServiceRuntime.record_usage, 'if held is not None:', 'if False:'), runtime)
    exercise("ignore_unknown_commit_acknowledgment", storage.ServiceCatalogBinding, "commit", rewrite(
        storage.ServiceCatalogBinding.commit, 'or acknowledgment.committed is not True', 'or False'), runtime)
    exercise("accept_invalid_webhook_signature", billing.StripeEventProcessor, "_verified", rewrite(
        billing.StripeEventProcessor._verified, 'if not matched:', 'if False:'), billing)
    exercise("accept_expired_or_future_webhook_signature", billing.StripeEventProcessor, "_verified", rewrite(
        billing.StripeEventProcessor._verified,
        'if abs(self.runtime._now() - timestamp) > self.config.tolerance_seconds:', 'if False:'), billing)
    exercise("grant_active_but_unpaid_subscription", billing.StripeEventProcessor, "_decision", rewrite(
        billing.StripeEventProcessor._decision,
        'subscription.latest_invoice_paid is True', 'True'), billing)
    exercise("ignore_unknown_or_wrong_provider_snapshot", billing.StripeEventProcessor, "_decision", rewrite(
        billing.StripeEventProcessor._decision,
        'if (not isinstance(snapshot, StripeCustomerSubscriptionSnapshot)',
        'if False and (not isinstance(snapshot, StripeCustomerSubscriptionSnapshot)'), billing)
    exercise("ignore_provider_network_authority", provider.StripeSubscriptionReader, "resolve", rewrite(
        provider.StripeSubscriptionReader.resolve, 'if self.config.allow_network is not True:', 'if False:'), provider)
    paths = {Path(module.__file__) for module in modules}
    paths.update(Path(importlib.import_module(name).__file__) for name in (
        "loop_engine.core.service_runtime.records", "loop_engine.core.service_runtime.storage",
        "loop_engine.core.service_runtime.provisioning", "loop_engine.core.service_runtime.billing_records",
        "loop_engine.core.service_runtime.runtime_checks", "loop_engine.core.service_runtime.billing_checks"))
    result = {"record_type": "durable_service_verification/v1", "baseline": baseline, "mutants": mutants,
              "passed": not any(row["failed"] or row["not_tested"] for row in baseline)
              and all(row["detected"] for row in mutants),
              "source_sha256": {str(path.relative_to(Path.cwd())):
                                hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(paths)},
              "limitations": ["No live Stripe account or deployment tested.",
                              "SQLite embedded single-writer profile, not a clustered database claim.",
                              "Injected provider transport and signed fixtures establish local contracts, not provider qualification."]}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
