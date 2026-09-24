"""Removed-guard controls for the TLS trust contract and the provider binding.

Each control removes one guard in memory only, never on disk, and runs the
named checks. A control is detected when the checks pass on the real source
and fail with the guard removed. No provider is called: the TLS checks use a
local server with a throwaway authority, and the binding checks use fixture
transports.
"""
from __future__ import annotations

import hashlib
import inspect
import io
import json
import sys
import textwrap
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "tools")]

import tools.test_custom_endpoint_tls_trust as tls_checks
import tools.test_generate_original_native_provider_binding as binding_checks
from loop_engine.core import custom_endpoint as endpoint_module
from loop_engine.core import runtime_settings
from tools import generate_original_native_candidates as generation

TLS = "tools.test_custom_endpoint_tls_trust.CustomEndpointTLSTrustTest."
BOUND = "tools.test_generate_original_native_provider_binding.ProviderBindingTest."


def run(names):
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in names)
    result = unittest.TextTestRunner(stream=io.StringIO()).run(suite)
    return {"passed": result.wasSuccessful(), "run": result.testsRun,
            "failures": len(result.failures), "errors": len(result.errors)}


def endpoint_mutant(before, after, names):
    """Replace custom_endpoint in sys.modules with a mutated copy for the checks."""
    source = Path(endpoint_module.__file__).read_text(encoding="utf-8")
    if source.count(before) != 1:
        raise RuntimeError("a control must replace exactly one guard: " + before[:60])
    mutant = types.ModuleType(endpoint_module.__name__)
    mutant.__package__, mutant.__file__ = "loop_engine.core", endpoint_module.__file__
    exports = ("ce", "CustomEndpoint", "EndpointError", "make_adapter")
    saved = {name: getattr(tls_checks, name) for name in exports}
    sys.modules[endpoint_module.__name__] = mutant
    try:
        exec(compile(source.replace(before, after), endpoint_module.__file__, "exec"), mutant.__dict__)  # noqa: S102 - fixed in-memory controls
        for name in exports:
            setattr(tls_checks, name, mutant if name == "ce" else getattr(mutant, name))
        return run(names)
    finally:
        sys.modules[endpoint_module.__name__] = endpoint_module
        for name, value in saved.items():
            setattr(tls_checks, name, value)


def function_mutant(owner, name, before, after, names):
    """Replace one function or method with a mutated copy for the checks."""
    source = textwrap.dedent(inspect.getsource(getattr(owner, name)))
    if source.count(before) != 1:
        raise RuntimeError("a control must replace exactly one guard: " + before[:60])
    module = sys.modules[owner.__module__] if isinstance(owner, type) else owner
    namespace = dict(module.__dict__)
    exec(compile(source.replace(before, after), module.__file__, "exec"), namespace)  # noqa: S102 - fixed in-memory controls
    with patch.object(owner, name, namespace[name]):
        return run(names)


CONTROLS = [
    ("leaf_pin_not_compared", "endpoint",
     "if not hmac.compare_digest(hashlib.sha256(leaf).hexdigest(),\n                                       self._tls_pinned_sha256):",
     "if False:", [TLS + "test_wrong_pin_refuses_before_any_request"]),
    ("expected_server_name_ignored", "endpoint",
     "expected = self._tls_server_name or self._tunnel_host or self.host",
     "expected = self._tunnel_host or self.host", [TLS + "test_correct_name_anchor_and_pin_pass"]),
    ("hostname_check_disabled", "endpoint",
     "        context = ssl.create_default_context(cafile=ep.tls_ca_file or None)\n",
     "        context = ssl.create_default_context(cafile=ep.tls_ca_file or None)\n        context.check_hostname = False\n",
     [TLS + "test_wrong_server_name_refuses_before_any_request"]),
    ("declared_anchor_ignored", "endpoint",
     "context = ssl.create_default_context(cafile=ep.tls_ca_file or None)",
     "context = ssl.create_default_context()", [TLS + "test_missing_anchor_file_refuses_before_any_socket"]),
    ("https_only_declaration_removed", "endpoint",
     "if self.has_tls_trust_contract and not self.base_url.startswith(\n                \"https://\"):",
     "if False:", [TLS + "test_plain_http_declarations_are_refused"]),
    ("ca_file_consistency_removed", "endpoint",
     "if (self.tls_verification == \"ca_file\") != bool(\n                self.tls_ca_file.strip()):",
     "if False:", [TLS + "test_inconsistent_trust_declarations_are_refused"]),
    ("plain_http_transport_allowed", "endpoint",
     "_RedirectRefused(), _PlainHTTPRefused())", "_RedirectRefused())",
     [TLS + "test_plain_http_through_a_trusted_opener_sends_nothing"]),
    ("redirect_followed", "endpoint",
     "_RedirectRefused(), _PlainHTTPRefused())", "_PlainHTTPRefused())",
     [TLS + "test_redirect_is_not_followed_and_the_key_stays_with_the_verified_server"]),
    ("refusal_counted_as_physical_request", "endpoint",
     "physical_requests=physical_requests - 1)", "physical_requests=physical_requests)",
     [TLS + "test_wrong_pin_refuses_before_any_request"]),
    ("refusal_not_classified", "endpoint",
     "    if isinstance(error, TLSTrustRefused):\n        return error\n",
     "    return None\n", [TLS + "test_wrong_server_name_refuses_before_any_request"]),
    ("settings_drop_the_pin", (runtime_settings.ProviderSettings, "custom_endpoint"),
     "tls_pinned_sha256=self.tls_pinned_sha256,", "",
     [TLS + "test_endpoint_record_and_settings_carry_the_contract_but_never_the_key"]),
    ("binding_bytes_not_checked_at_revision", (generation, "committed_bytes"),
     "factory._checked_source(repository, revision, relative, expected)", "pass",
     [BOUND + "test_uncommitted_binding_refuses_even_when_its_digest_matches"]),
    ("credential_and_capacity_fields_admitted", (generation, "load_provider_binding"),
     "if type(provider) is not dict or any(key in provider for key in (\n            \"credential_env\", \"maximum_output_tokens\", \"maximum_output_source\")):",
     "if type(provider) is not dict:", [BOUND + "test_unverified_plain_or_credential_bearing_settings_refuse"]),
    ("unverified_or_plain_endpoint_admitted", (generation, "load_provider_binding"),
     " or not settings.endpoint.startswith(\"https://\") or settings.tls_verification == \"skip\"):", "):",
     [BOUND + "test_unverified_or_plain_endpoint_refuses_even_without_trust_options"]),
    ("model_not_bound", (generation, "load_provider_binding"),
     "if settings.model != model:", "if False:",
     [BOUND + "test_model_or_family_that_differs_from_the_binding_refuses_without_alias_normalization"]),
    ("family_not_bound", (generation, "load_provider_binding"),
     "if value[\"producer_family\"] != family:", "if False:",
     [BOUND + "test_model_or_family_that_differs_from_the_binding_refuses_without_alias_normalization"]),
    ("family_evidence_not_matched", (generation, "load_provider_binding"),
     "if {key: evidence.get(key) for key in identity} != identity or evidence.get(\"family\") != family:",
     "if False:", [BOUND + "test_family_evidence_for_another_model_or_family_refuses"]),
    ("capacity_not_matched", (generation, "load_provider_binding"),
     "if {key: capacity.get(key) for key in identity} != identity:", "if False:",
     [BOUND + "test_unknown_or_foreign_capacity_refuses_before_credential"]),
    ("unknown_capacity_reaches_the_credential", (generation, "load_provider_binding"),
     "if capability.declared_maximum is None:", "if False:",
     [BOUND + "test_unknown_or_foreign_capacity_refuses_before_credential"]),
    ("tls_refusal_does_not_stop_the_run", (generation, "STOP_ERROR_CODES"), None, None,
     [BOUND + "test_tls_trust_refusal_sends_nothing_and_stops_the_run"]),
    ("binding_not_bound_on_resume", (generation, "generate"),
     "\"provider_binding\": binding.summary() if binding is not None else None,", "\"provider_binding\": None,",
     [BOUND + "test_changed_binding_summary_refuses_resume_before_another_call"]),
]


def main():
    rows = []
    for identity, where, before, after, names in CONTROLS:
        baseline = run(names)
        if where == "endpoint":
            removed = endpoint_mutant(before, after, names)
        elif where[1] == "STOP_ERROR_CODES":
            with patch.object(generation, "STOP_ERROR_CODES",
                              tuple(code for code in generation.STOP_ERROR_CODES if code != "tls_trust_refused")):
                removed = run(names)
        else:
            removed = function_mutant(where[0], where[1], before, after, names)
        rows.append({"guard": identity, "checks": [name.rsplit(".", 1)[-1] for name in names],
                     "baseline": baseline, "removed": removed,
                     "detected": baseline["passed"] and not removed["passed"]})
    sources = [endpoint_module.__file__, runtime_settings.__file__, generation.__file__,
               tls_checks.__file__, binding_checks.__file__]
    report = {"record_type": "tactical_binding_removed_guards/v1", "provider_calls": 0,
              "at": datetime.now(timezone.utc).isoformat(),
              "source_sha256": {Path(path).name: hashlib.sha256(Path(path).read_bytes()).hexdigest()
                                for path in sources},
              "all_detected": all(row["detected"] for row in rows), "controls": len(rows), "results": rows}
    output = Path(__file__).with_name(
        "removed-guards-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + ".json")
    output.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"path": str(output), "all_detected": report["all_detected"], "controls": len(rows),
                      "missed": [row["guard"] for row in rows if not row["detected"]]}))
    return 0 if report["all_detected"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
