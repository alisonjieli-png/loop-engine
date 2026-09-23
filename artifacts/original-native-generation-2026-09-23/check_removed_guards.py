"""Offline removed-guard checks. Never changes source or invokes a provider."""
import hashlib
import inspect
import io
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
from tools import generate_original_native_candidates as generation


def run(name):
    output = io.StringIO()
    tests = unittest.defaultTestLoader.loadTestsFromName(
        "tools.test_generate_original_native_candidates.GenerationTest." + name)
    result = unittest.TextTestRunner(stream=output).run(tests)
    return {"passed": result.wasSuccessful(), "failures": len(result.failures), "errors": len(result.errors),
            "output": generation.redacted(output.getvalue())}


def main():
    controls = [
        ("plan_binding", "load_plan", "if digest(raw) != expected_digest:", "if False:",
         "test_authority_source_plan_and_budget_binding_refuse_before_call"),
        ("call_ceiling", "generate", "if used_calls >= request.call_ceiling:", "if False:",
         "test_call_ceiling_stops_without_generating_another_method"),
        ("model_identity", "generate", "if result.ok and (result.model != request.model or result.provider != spec.provider_id or reported_model != request.model):", "if False:",
         "test_nonmatching_model_never_generates_package"),
        ("strict_bound_source", "generate", "if request.token_ceiling is not None and token_bound_resolver is None:", "if False:",
         "test_strict_total_requires_resolver_before_dispatch"),
        ("resume_binding", "generate", "if strict_json(read_file(meta, MAX_PLAN_BYTES)) != config:", "if False:",
         "test_changed_resume_budget_and_timeout_refuse"),
        ("complete_file_tree", "parse_draft", "if found != set(planned):", "if False:",
         "test_missing_or_extra_path_and_wrapper_are_preserved_failures"),
        ("duplicate_package", "generate", "if any(row[\"data\"][\"package_digest\"] == package_digest for row in successful.values()):", "if False:",
         "test_identical_payloads_under_new_method_name_do_not_inflate_count"),
        ("prepared_metadata_binding", "verify_success", "if prepared_tree_digest(prepared) != data[\"prepared_tree_sha256\"]:", "if False:",
         "test_changed_prepared_metadata_or_specification_refuses_resume"),
        ("rejected_attempt_identity", "generate", '"reported_model": redacted(reported_model)', '"reported_model": ""',
         "test_rejected_physical_attempt_identity_is_retained_without_requested_fallback"),
        ("direct_engine_binding", "implementation_digests",
         'paths = (Path(__file__), Path(native.__file__), Path(factory.__file__),\n             Path(inspect.getfile(ModelGateway)), Path(inspect.getfile(adapter)))',
         'paths = (Path(__file__), Path(native.__file__), Path(factory.__file__))',
         "test_direct_gateway_and_adapter_implementations_are_bound_on_resume"),
    ]
    results = []
    for name, function, old, replacement, test in controls:
        baseline = run(test)
        source = inspect.getsource(getattr(generation, function))
        if source.count(old) != 1:
            raise RuntimeError("control must replace exactly one guard")
        namespace = dict(generation.__dict__)
        exec(compile(source.replace(old, replacement), "<fixed-local-control>", "exec"), namespace)  # noqa: S102
        with patch.object(generation, function, namespace[function]):
            removed = run(test)
        results.append({"guard": name, "baseline": baseline, "removed": removed,
                        "detected": baseline["passed"] and removed["failures"] > 0 and removed["errors"] == 0})
    report = {"record_type": "original_native_generation_removed_guards/v1", "provider_calls": 0,
              "source_sha256": hashlib.sha256(Path(generation.__file__).read_bytes()).hexdigest(),
              "all_detected": all(r["detected"] for r in results), "results": results}
    output = Path(__file__).with_name("removed-guards-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + ".json")
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"path": str(output), "all_detected": report["all_detected"], "controls": len(results)}))
    return 0 if report["all_detected"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
