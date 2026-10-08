"""Run one explicitly authorized ephemeral search; print metadata, never result bodies or credentials.

Uses the existing operator keyring manifest and canonical capability Loop.
Without --authorize-network, validates and describes the selected engine only.
This tool creates no schedule, account, purchase or result file. Dispatch also
requires an explicit durable provider-account policy and accounting-write
grant. Its allowance is an operator ceiling, not an inferred provider quota.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tools"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from loop_engine import LoopLedger  # noqa: E402
from loop_engine.core.capability_directory import CapabilityDirectory  # noqa: E402
from loop_engine.core.library_ingestion.request_log import RequestBudget  # noqa: E402
from loop_engine.core.web_research_engines import (ENDPOINTS, WebResearchEngineConfig, WebResearchPolicy,  # noqa: E402
    WebResearchRequest, describe_web_research_engine, observation, register_web_research)
from loop_engine.core.web_research_quota import DurableSearchQuota, QuotaRefused, SearchQuotaPolicy  # noqa: E402
from loop_engine.loop.capability_loops import run_capability_ref_as_loop  # noqa: E402
import operator_credentials  # noqa: E402

PROVIDERS = {"brave": ("brave-search", "BRAVE_SEARCH_API_KEY"), "exa": ("exa", "EXA_API_KEY"),
             "tavily": ("tavily", "TAVILY_API_KEY")}


def selected_config(provider, reference, manifest):
    if (type(manifest) is not dict or manifest.get("record_type") != "operator_credential_references/v1"
            or type(manifest.get("api_keys")) is not dict):
        raise ValueError("unsupported_credential_manifest")
    item = manifest.get("api_keys", {}).get(reference)
    service, variable = PROVIDERS[provider]
    if (not isinstance(item, dict) or item.get("service") != service or item.get("environment") != variable
            or item.get("purpose") != "bounded-research-search"):
        raise ValueError("credential_provider_binding_mismatch")
    # Account identity comes from the operator's manifest, never the chosen
    # credential alias or any part of its secret value.
    return WebResearchEngineConfig(provider, provider + "-operator-probe", item.get("account"), reference)


class OperatorSecrets:
    def __init__(self, manifest):
        self.manifest = manifest

    def get(self, reference):
        return operator_credentials.resolve(reference, data=self.manifest)


def load_quota_policy(path):
    def unique(pairs):
        value = {}
        for name, item in pairs:
            if name in value:
                raise ValueError("quota_policy_duplicate_field")
            value[name] = item
        return value

    with path.open("rb") as handle:
        data = handle.read(65537)
    if len(data) > 65536:
        raise ValueError("quota_policy_too_large")
    return SearchQuotaPolicy.from_record(json.loads(data, object_pairs_hook=unique))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--provider", choices=tuple(ENDPOINTS), required=True)
    parser.add_argument("--credential-ref", required=True)
    parser.add_argument("--credentials", type=Path, default=ROOT / "tools/operator_credentials.json")
    parser.add_argument("--query", required=True, help="Public, non-confidential query text sent to the selected provider.")
    parser.add_argument("--purpose", default="Bounded provider contract validation")
    parser.add_argument("--maximum-results", type=int)
    parser.add_argument("--authorize-network", action="store_true")
    parser.add_argument("--quota-policy", type=Path, help="Explicit versioned provider-account allowance JSON.")
    parser.add_argument("--quota-state", type=Path, help="Absolute path to the shared private .sqlite accounting file.")
    parser.add_argument("--authorize-accounting-writes", action="store_true")
    options = parser.parse_args(argv)
    policy = None
    try:
        manifest = json.loads(options.credentials.read_text())
        config = selected_config(options.provider, options.credential_ref, manifest)
        request = WebResearchRequest(options.query, options.purpose, options.maximum_results)
        if not options.authorize_network:
            print(json.dumps({"record_type": "web_research_probe_plan/v1", "engine": describe_web_research_engine(config),
                              "requests_authorized": 0, "credentials_read": False, "results_retained": False}))
            return 0
        if not options.quota_policy or not options.quota_state or not options.authorize_accounting_writes:
            raise ValueError("durable_quota_configuration_required")
        accounting = DurableSearchQuota(options.quota_state, load_quota_policy(options.quota_policy),
                                        allow_writes=options.authorize_accounting_writes)
        policy = WebResearchPolicy(RequestBudget(1), {config.quota_identity: RequestBudget(1)},
                                   time.monotonic() + 35, durable=accounting)
        directory = CapabilityDirectory()
        register_web_research(directory, config=config, secret_provider=OperatorSecrets(manifest), policy=policy)
        ref = directory.search_core("search public web")[0]
        result = run_capability_ref_as_loop(directory, ref, "search", request=request,
            access_mode="approved_external_read", ledger=LoopLedger())
        metadata = observation(result["value"])
        accounting_view = None
        if accounting.state_path.exists():
            try:
                accounting_view = accounting.snapshot(config.quota_identity)
            except QuotaRefused as error:
                accounting_view = {"record_type": "web_research_quota_refusal/v1", "error_code": str(error)}
        print(json.dumps({**metadata, "loop_id": result["loop_id"], "run_requests_reserved": policy.total.used,
                          "request_ceiling": policy.total.maximum_requests,
                          "accounting": accounting_view}, sort_keys=True))
        return 0 if metadata["ok"] and not (accounting_view or {}).get("error_code") else 1
    except (ValueError, OSError, KeyError, RecursionError, operator_credentials.CredentialError):
        # Neither malformed files nor secret-store failures echo their input.
        print(json.dumps({"record_type": "web_research_probe_refusal/v1", "error_code": "probe_configuration_or_execution_refused",
                          "results_retained": False, "run_requests_reserved": policy.total.used if policy else 0,
                          "phase": "execution" if policy and policy.total.used else "before_dispatch",
                          "effect_commitment": "not_asserted", "automatic_retry": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
