"""Offline serving checks and in-memory known-wrong implementations.

No source file is rewritten by this runner. Bodies, resolvers and meters are
trusted local fixtures. No network, model, purchase or external effect occurs.
"""
from __future__ import annotations

import hashlib
import importlib
import inspect
import json
import textwrap
from pathlib import Path
from unittest.mock import patch

MODULES = (
    "loop_engine.core.provisioning_server",
    "loop_engine.core.harness_intelligence",
    "loop_engine.core.intelligence_tagging",
    "loop_engine.core.node_provisioning",
    "loop_engine.core.spawned_provisioning",
    "loop_engine.core.external_service_intelligence",
    "loop_engine.core.harness_intelligence_bridge",
    "loop_engine.core.service_api",
)


def run_checks(module):
    try:
        rows = module.self_test()["tests"]
        return {"module": module.__name__, "checks": len(rows),
                "failed": [row.get("name", row.get("test", "unnamed"))
                           for row in rows if row.get("passed") is not True],
                "not_tested": [row for row in rows if row.get("not_tested")]}
    except Exception as error:
        return {"module": module.__name__, "checks": None,
                "failed": [type(error).__name__ + ": " + str(error)], "not_tested": []}


def rewrite(function, old, new):
    source = textwrap.dedent(inspect.getsource(function))
    if source.count(old) != 1:
        raise RuntimeError("mutant target must be unique: " + old)
    namespace = {}
    exec(compile(source.replace(old, new), "<provisioning-mutant>", "exec"),
         function.__globals__, namespace)
    return namespace[function.__name__]


def main():
    modules = [importlib.import_module(name) for name in MODULES]
    baseline = [run_checks(module) for module in modules]
    serving = modules[0]
    mutants = []

    def exercise(name, owner, attribute, old, new):
        replacement = rewrite(getattr(owner, attribute), old, new)
        with patch.object(owner, attribute, replacement):
            result = run_checks(serving)
        mutants.append({"name": name, "detected": bool(result["failed"]),
                        "failing_checks": result["failed"]})

    exercise("ignore_tenant_identity_in_grant_lookup", serving.ProvisioningServer, "_approved",
             'policy._grant_index.get((tenant.tenant_id, binding.identity))',
             'next((entry for entry in policy.grants if entry.binding.identity == binding.identity), None)')
    exercise("omit_descriptor_identity_from_grants", serving.ProvisioningItemBinding, "from_item",
             '_hash(item.reference())', '"0" * 64')
    exercise("ignore_unapproved_qualification", serving.ProvisioningServer, "_approved",
             'or decision.binding != binding or decision.status != QUALIFICATION_APPROVED',
             'or decision.binding != binding')
    exercise("ignore_qualification_binding", serving.ProvisioningServer, "_approved",
             'or decision.binding != binding or decision.status != QUALIFICATION_APPROVED',
             'or decision.status != QUALIFICATION_APPROVED')
    exercise("ignore_subscription_and_body_grant", serving.ProvisioningServer, "_read",
             'if tenant.entitlement != ENTITLEMENTS[1] or grant.body_allowed is not True:',
             'if False:')
    exercise("disclose_global_catalogue_counts", serving.ProvisioningServer, "_discover",
             '"items_held": len(offered)', '"items_held": len(self.catalogue.items)')
    exercise("ignore_body_integrity", serving.ProvisioningServer, "_read",
             'if hashlib.sha256(encoded).hexdigest() != item.digest or len(encoded) != item.size_bytes:',
             'if False:')
    exercise("ignore_acknowledgment_exact_request", serving.ProvisioningServer, "_read",
             'or acknowledgment.request != meter_request', 'or False')
    exercise("accept_unknown_meter_commit", serving.ProvisioningServer, "_read",
             'or acknowledgment.committed is not True\n                or not acknowledgment.acknowledgment_ref.strip()',
             'or False')
    exercise("ignore_revocation_before_disclosure", serving.ProvisioningServer, "_recheck",
             'current, current_grant, current_decision = self._item(tenant, request)',
             'return\n    current, current_grant, current_decision = self._item(tenant, request)')
    exercise("ignore_reentrant_policy_revocation", serving.ProvisioningServer, "_approved",
             'or self.access_policy is not policy', 'or False')
    exercise("charge_exact_retries_again", serving.RecordedMeter, "__call__",
             'existing = self._acknowledgments.get(identity)', 'existing = None')
    exercise("reuse_charge_for_changed_effect", serving.RecordedMeter, "__call__",
             'if existing.request != request:', 'if False:')
    exercise("accept_unsupported_contract_version", serving, "_version",
             'if actual != expected:', 'if False:')
    paths = [Path(module.__file__) for module in modules]
    paths.append(Path(importlib.import_module("loop_engine.core.provisioning_server_checks").__file__))
    result = {"record_type": "provisioning_access_verification/v1", "baseline": baseline,
              "mutants": mutants,
              "passed": not any(row["failed"] or row["not_tested"] for row in baseline)
              and all(row["detected"] for row in mutants),
              "source_sha256": {str(path.relative_to(Path.cwd())):
                                hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(paths)}}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
