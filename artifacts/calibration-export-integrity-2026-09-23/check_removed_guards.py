"""Fixed in-memory calibration faults; no file mutation or provider calls."""
import hashlib
import inspect
import io
import json
import unittest

from candidate_review import calibration, calibration_record
from test_candidate_review_native_calibration import NativeCalibrationTest

controls = [
    (calibration, 'evaluate', 'set(result.availability) | set(result.ineligible)',
     '{identity for identity, probe in result.availability.items() if probe.available and identity not in result.ineligible}',
     'unmeasured_reviewers_disappear', 'test_unavailable_skipped_and_zero_call_installations_are_incomplete'),
    (calibration, 'installation_result', 'unanswered = sorted(set(expected) - set(answers))',
     'unanswered = sorted(set(wrong) - set(answers))',
     'missing_benign_answer_is_treated_as_complete', 'test_missing_benign_control_verdict_stays_incomplete'),
    (calibration_record, 'read_calibration', 'saved["items"] != [item.to_dict() for item in chosen.items]', 'False',
     'persisted_labels_replace_trusted_control_labels', 'test_export_refuses_control_labels_calls_and_summary_tampering'),
    (calibration_record, 'read_calibration', 'if digest(saved["installations"]) != digest(recomputed):', 'if False:',
     'saved_installation_summary_is_not_recomputed', 'test_export_refuses_control_labels_calls_and_summary_tampering'),
    (calibration_record, 'read_calibration',
     'if saved["excluded"] != excluded or {identity: row["reason"] for identity, row in ineligible_by_id.items()\n                                        if row["reason"] in EXCLUSIONS} != excluded:',
     'if False:', 'exclusion_projection_may_omit_failed_reviewer',
     'test_export_rederives_failed_status_when_both_exclusion_lists_are_deleted'),
    (calibration_record, 'read_calibration', 'if call["prompt_sha256"] != prompt.sha256:', 'if False:',
     'self_consistent_review_key_hides_changed_prompt',
     'test_recomputed_review_key_cannot_hide_a_changed_calibration_prompt'),
]
rows = []
for module, function, before, after, name, method in controls:
    original = getattr(module, function)
    source = inspect.getsource(original)
    if before not in source:
        raise SystemExit('missing mutation target: ' + name)
    namespace = dict(module.__dict__)
    exec(compile(source.replace(before, after), '<fixed-calibration-mutant>', 'exec'), namespace)  # noqa: S102 - fixed offline faults
    setattr(module, function, namespace[function])
    stream = io.StringIO()
    try:
        result = unittest.TextTestRunner(stream=stream).run(unittest.TestSuite([NativeCalibrationTest(method)]))
        rows.append({'mutation': name, 'detected': not result.wasSuccessful(), 'named_check': method,
                     'source_function_sha256': hashlib.sha256(source.encode()).hexdigest(), 'output': stream.getvalue()})
    finally:
        setattr(module, function, original)
report = {'all_detected': all(row['detected'] for row in rows), 'controls': rows, 'provider_calls': 0}
print(json.dumps(report, indent=2))
raise SystemExit(0 if report['all_detected'] else 1)
