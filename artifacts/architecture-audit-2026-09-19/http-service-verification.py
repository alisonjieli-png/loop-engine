"""Real local transport acceptance and restored in-memory security mutants.

Only loopback servers and temporary durable stores are used. No source files
are changed by this runner and no provider, payment account or deployment is
contacted. Historical verification records remain separate.
"""
from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path
import tempfile
import textwrap
from unittest.mock import patch

from loop_engine.core.service_runtime import http, http_auth, http_checks, http_boundary_checks, http_entrypoint


def suite(function):
    checks = []
    def check(name, passed):
        checks.append({"test": name, "passed": bool(passed)})
    with tempfile.TemporaryDirectory(prefix="http-mutant-") as directory:
        root = Path(directory) / "case"
        if function.__module__ != http_boundary_checks.__name__:
            root.mkdir()
        function(check, root)
    return checks


def rewritten(function, module, before, after):
    source = textwrap.dedent(inspect.getsource(function))
    if source.count(before) != 1:
        raise RuntimeError("mutation target must occur once: " + before)
    namespace = dict(vars(module))
    exec(compile(source.replace(before, after), "<http-security-mutant>", "exec"), namespace)
    return namespace[function.__name__]


def main():
    baseline = http_checks.self_test()
    if not baseline["all_passed"]:
        print(json.dumps({"baseline": baseline, "passed": False}))
        return 1
    observations = []
    targets = (
        ("ignore_current_request_version", http.ServiceHttpApplication, "_validate_provisioning", http,
         'if payload.get("record_type") != PROVISIONING_REQUEST_VERSION:', 'if False:', http_checks._web_checks),
        ("ignore_token_audience", http_auth.ServiceHttpAuthenticator, "_external_token", http_auth,
         '"verify_signature": True', '"verify_signature": True, "verify_aud": False', http_checks._identity_checks),
        ("ignore_token_issuer", http_auth.ServiceHttpAuthenticator, "_external_token", http_auth,
         '"verify_signature": True', '"verify_signature": True, "verify_iss": False', http_checks._identity_checks),
        ("ignore_token_expiry", http_auth.ServiceHttpAuthenticator, "_external_token", http_auth,
         '"verify_signature": True', '"verify_signature": True, "verify_exp": False', http_checks._identity_checks),
        ("broaden_external_token_to_all_user_scopes", http_auth.AuthenticatedHttpRequest, "effective_scopes", http_auth,
         'held.intersection_update(self.token_scopes)', 'pass', http_checks._identity_checks),
        ("follow_unconfigured_key_endpoint_redirect", http_auth.ServiceHttpAuthenticator, "__init__", http_auth,
         'follow_redirects=False', 'follow_redirects=True', http_boundary_checks._key_endpoint),
        ("ignore_key_set_byte_limit", http_auth.ServiceHttpAuthenticator, "__init__", http_auth,
         'if size > configuration.maximum_key_set_bytes:', 'if False:', http_boundary_checks._key_endpoint),
        ("inline_a_body_requiring_separate_authorization", http.ServiceHttpApplication, "_invoke", http,
         'if manifest["size_bytes"] > self.configuration.maximum_inline_body_bytes:', 'if False:', http_checks._web_checks),
        ("call_hash_vectors_semantic_embeddings", http.ServiceHttpApplication, "capabilities", http,
         '"semantic_embedding_model_installed": False', '"semantic_embedding_model_installed": True', http_checks._web_checks),
        ("remove_Host_validation", http.ServiceHttpApplication, "create_app", http,
         'or request.headers["host"] not in config.allowed_hosts', 'or False', http_checks._web_checks),
        ("remove_Origin_validation", http.ServiceHttpApplication, "create_app", http,
         'or origin not in config.allowed_origins', 'or False', http_checks._web_checks),
        ("drop_selected_body_precondition", http.ServiceHttpApplication, "_invoke", http,
         'current = self.authenticator.revalidate(authentication)',
         'fields = {key: value for key, value in fields.items() if key != "expected_digest"}\n'
         '    current = self.authenticator.revalidate(authentication)', http_checks._web_checks),
        ("free_capacity_while_callback_is_still_running", http.ServiceHttpApplication, "_work", http,
         'future.add_done_callback(lambda _future: self._slots.release())', 'self._slots.release()', http_boundary_checks._limits),
        ("ignore_incoming_body_byte_limit", http.ServiceHttpApplication, "_body", http,
         'if size > self.configuration.maximum_request_bytes:', 'if False:', http_checks._web_checks),
        ("acknowledge_unreconciled_billing_as_HTTP_success", http.ServiceHttpApplication, "_web_route", http,
         'if output["result"]["status"] == "pending":', 'if False:', http_boundary_checks._billing),
        ("acknowledge_unknown_billing_commit_as_HTTP_success", http.ServiceHttpApplication, "_web_route", http,
         'if output["result"]["committed"] is not True:', 'if False:', http_boundary_checks._billing),
        ("admit_changed_host_artifact_bytes", http_entrypoint, "load_host_manifest", http_entrypoint,
         'if checksum.hexdigest() != item.digest:', 'if False:', http_boundary_checks._host_setup),
    )
    for checks in dict.fromkeys(target[-1] for target in targets):
        if not all(row["passed"] for row in suite(checks)):
            raise RuntimeError("unchanged isolated mutation fixture failed: " + checks.__name__)
    for name, owner, attribute, module, before, after, checks in targets:
        original = getattr(owner, attribute)
        function = original.fget if isinstance(original, property) else original
        replacement = rewritten(function, module, before, after)
        if isinstance(original, property):
            if isinstance(replacement, property):
                replacement = replacement.fget
            replacement = property(replacement)
        with patch.object(owner, attribute, replacement):
            try:
                failed = [row["test"] for row in suite(checks) if not row["passed"]]
                result = {"mutant": name, "detected": bool(failed), "failed_checks": failed}
            except Exception as error:
                result = {"mutant": name, "detected": True, "check_exception": type(error).__name__,
                          "detail": str(error)[:160]}
        observations.append(result)
    root = Path.cwd()
    paths = sorted((root / "src/loop_engine/core/service_runtime").glob("http*.py"))
    report = {"record_type": "remote_http_verification/v1", "provider_calls": 0,
              "external_network_calls": 0, "live_identity_provider_qualified": False,
              "live_payment_provider_qualified": False,
              "baseline": baseline, "mutants": observations,
              "source_sha256": {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths},
              "all_detected": all(row["detected"] for row in observations)}
    print(json.dumps(report, indent=2))
    return 0 if report["all_detected"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
