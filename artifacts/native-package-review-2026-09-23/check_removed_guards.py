"""Exercise native review guards with fixed local mutations and no provider or payload execution."""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "src")]
from candidate_review import native, native_prechecks, prompt, review_record

spec = importlib.util.spec_from_file_location("integrity_mutation_helper", ROOT /
    "artifacts/candidate-review-integrity-2026-09-23/check_removed_guards.py")
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def run_case(name):
    stream = io.StringIO()
    suite = unittest.defaultTestLoader.loadTestsFromName("test_candidate_review_native." + name)
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    return {"passed": result.wasSuccessful(), "failures": len(result.failures), "errors": len(result.errors),
            "tests_run": result.testsRun, "output": stream.getvalue()}


def main():
    cases = [
        ("payload_digest", native, native.NativeCatalogue, "_verified_files",
         "if len(payload) != entry.size_bytes or sha256_hex(payload) != entry.digest:",
         "if len(payload) != entry.size_bytes:", "NativeReaderTest.test_same_size_changed_payload_digest_is_refused"),
        ("complete_inventory", native, native.NativeCatalogue, "_verified_files",
         "if found != expected:", "if False:", "NativeReaderTest.test_missing_changed_extra_and_linked_helper_refuse"),
        ("whole_file_prompt", prompt, prompt, "build_native_prompt", "for file in request.files:",
         "for file in ():", "NativeReaderTest.test_manifest_and_every_exact_file_reach_the_prompt_separately"),
        ("executable_effect", native_prechecks, native_prechecks.NativeEffectsRules, "findings",
         'if any(file.entry.role in EXECUTABLE for file in request.files) and "spawns_process" not in effects:',
         "if False:", "NativePrecheckTest.test_executable_requires_process_effect"),
        ("executable_role", native_prechecks, native_prechecks.NativeFormatRules, "findings",
         "if media in PYTHON_MEDIA and role not in EXECUTABLE:", "if False:",
         "NativePrecheckTest.test_python_cannot_hide_under_a_passive_role"),
        ("required_component", native_prechecks, native_prechecks.NativeFormatRules, "findings",
         "if role not in SUPPORTED_ROLES:", "if False:",
         "NativePrecheckTest.test_required_unsupported_component_is_not_silently_ignored"),
    ]
    results = []
    for name, module, owner, method, old, new, test in cases:
        baseline = run_case(test)
        mutation = helper.replacement(module, getattr(owner, method), old, new)
        with mock.patch.object(owner, method, mutation):
            control = run_case(test)
        results.append({"guard": name, "baseline": baseline, "removed_guard": control,
                        "detected": baseline["passed"] and control["failures"] > 0 and control["errors"] == 0})
    controls = [
        ("native_activation_placement", native_prechecks, "qualified_placement", lambda file: [],
         "NativePrecheckTest.test_native_activation_paths_cannot_be_disguised_as_passive_resources"),
        ("passive_resource_placement", native_prechecks, "qualified_placement", lambda file: [],
         "NativePrecheckTest.test_passive_json_is_limited_to_the_declared_resource_locations"),
        ("direct_payload_binding", native.NativePackageReviewRequest, "package_binding_findings", lambda self: [],
         "NativePrecheckTest.test_directly_replaced_payload_does_not_bypass_the_fixed_package_binding"),
        ("persisted_subject_binding", review_record, "_read_subject", lambda row: None,
         "NativeReviewPersistenceTest.test_changed_file_role_or_reported_identity_invalidates_persisted_review"),
        ("old_record_version", review_record, "PANEL_REVIEW_RECORD", "starter_catalogue_panel_review/v1",
         "NativeReviewPersistenceTest.test_old_review_records_cannot_be_resumed_or_admitted_by_current_reader"),
    ]
    for name, owner, attribute, mutation, test in controls:
        baseline = run_case(test)
        with mock.patch.object(owner, attribute, mutation):
            control = run_case(test)
        results.append({"guard": name, "baseline": baseline, "removed_guard": control,
                        "detected": baseline["passed"] and control["failures"] > 0 and control["errors"] == 0})
    now = datetime.now(timezone.utc)
    record = {"created_at": now.isoformat(), "provider_calls": 0, "payload_executions": 0,
              "sources": {str(Path(module.__file__).relative_to(ROOT)): hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
                          for module in (native, native_prechecks, prompt, review_record)},
              "results": results, "all_detected": all(row["detected"] for row in results)}
    target = Path(__file__).parent / ("removed-guards-" + now.strftime("%Y%m%dT%H%M%S%f") + ".json")
    target.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"report": str(target), "guards": len(results), "all_detected": record["all_detected"]}))
    return 0 if record["all_detected"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
