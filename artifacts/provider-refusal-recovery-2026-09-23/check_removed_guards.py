"""Fixed in-memory identity/recovery regressions; no provider or source-file effects."""
import hashlib
import inspect
import io
import json
import textwrap
import unittest

from devtools.embodiment_lab.tests.test_task_database_trial_offline import (
    RefusalPageTrialChecks,
)
from loop_engine.core import (
    external_harness,
    external_harness_accounting,
    harness_semantic,
)
from tools import test_provider_refusal_recovery as checks

controls = [
    (external_harness.HarnessModelCall, '__post_init__', external_harness,
     'or self.ok is not False', '',
     'unknown_model_cannot_claim_success', checks.ProviderRefusalRecoveryChecks,
     'test_unknown_model_requires_failed_typed_canonical_observation'),
    (external_harness_accounting, '_validate_gateway_references', external_harness_accounting,
     'or binding["record_type"] != "model_request_binding/v1"', '',
     'requested_binding_version_is_required', checks.ProviderRefusalRecoveryChecks,
     'test_unknown_observation_cannot_guess_or_forge_requested_binding'),
    (external_harness, 'run_external_harness', external_harness,
     'canonical_requested[call.gateway_loop_id]', '(request.provider_id, request.model_id, call.route_id)',
     'requested_authority_cannot_be_invented', checks.ProviderRefusalRecoveryChecks,
     'test_failed_unknown_call_is_still_checked_against_requested_model_authority'),
    (harness_semantic.HarnessSemanticBinding, '_invoke_one', harness_semantic,
     "model=(physical[-1].model if physical else '')", 'model=latest.model or primary.model',
     'semantic_failure_cannot_invent_reported_model', RefusalPageTrialChecks,
     'test_a_page_in_the_providers_place_keeps_its_typed_code_and_its_call_count'),
]
rows = []
for owner, name, module, before, after, label, suite_type, method in controls:
    original = getattr(owner, name)
    source = textwrap.dedent(inspect.getsource(original))
    if before not in source:
        raise SystemExit('missing fixed mutation target: ' + label)
    namespace = dict(module.__dict__)
    exec(compile(source.replace(before, after), '<fixed-refusal-mutant>', 'exec'), namespace)  # noqa: S102 - fixed offline fault controls
    setattr(owner, name, namespace[name])
    alias = getattr(checks, name, None)
    if alias is original:
        setattr(checks, name, namespace[name])
    stream = io.StringIO()
    try:
        result = unittest.TextTestRunner(stream=stream).run(unittest.TestSuite([suite_type(method)]))
        rows.append({'mutation': label, 'detected': not result.wasSuccessful(), 'named_check': method,
                     'source_function_sha256': hashlib.sha256(source.encode()).hexdigest(), 'output': stream.getvalue()})
    finally:
        setattr(owner, name, original)
        if alias is original:
            setattr(checks, name, alias)
report = {'all_detected': all(row['detected'] for row in rows), 'controls': rows, 'provider_calls': 0}
print(json.dumps(report, indent=2))
raise SystemExit(0 if report['all_detected'] else 1)
