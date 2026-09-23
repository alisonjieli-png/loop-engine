"""Research fixture checks, not an installed compiler/qualification engine.

The host-policy facts in synthetic scenarios are test assumptions. This script
does not validate real review signatures, run a client, grant authority or apply
files. Shape validity and semantic fixture consistency are reported separately.
"""
from hashlib import sha256
from importlib.metadata import version
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parent


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def profile_errors(record):
    errors = []
    ids = [e["evidence_id"] for e in record["evidence"]]
    cited = record["evidence_claim"]["evidence_ids"]
    evidence = {e["evidence_id"]: e for e in record["evidence"]}
    if len(ids) != len(set(ids)) or any(e not in evidence for e in cited):
        errors.append("evidence_reference_invalid")
        return errors
    required = {"paths_constructed": {"path_constructor", "native_discovery", "native_activation", "accepted_task"},
                "material_listed": {"native_discovery"}, "material_activated": {"native_activation"},
                "accepted_task": {"accepted_task"}}[record["evidence_claim"]["stage"]]
    if not any(evidence[e]["kind"] in required for e in cited):
        errors.append("evidence_stage_not_supported")
    for e in cited:
        if evidence[e]["kind"] in {"native_discovery", "native_activation", "accepted_task"} and evidence[e]["observed_client_binding"] != record["client_binding"]:
            errors.append("native_evidence_binding_mismatch")
    location_keys = [(p["served_kind"], p["file_role"]) for p in record["locations"]]
    if len(location_keys) != len(set(location_keys)):
        errors.append("ambiguous_location")
    if {p["file_role"] for p in record["locations"]} & {r["role"] for r in record["unplaced_roles"]}:
        errors.append("contradictory_role_support")
    return sorted(set(errors))


def plan_errors(record, context):
    if record["status"] == "refused":
        # A report can faithfully describe a refusal. This does not test whether
        # the claimed refusal reason was actually observed by a runtime.
        return []
    errors = []
    profile = context["profile"]
    if record["bindings"]["profile_digest"] != digest(profile):
        errors.append("profile_binding_mismatch")
    if record["bindings"] != context["expected_bindings"]:
        errors.append("input_binding_mismatch")
    if record["client_binding"] != profile["client_binding"]:
        errors.append("client_binding_mismatch")
    supported_ops = set(context["engine_supported_operations"])
    if any(f["rendering_operation"] not in supported_ops for f in record["files"]):
        errors.append("engine_semantics_unsupported")
    paths = [f["target_path"] for f in record["files"]]
    if len(paths) != len(set(paths)):
        errors.append("path_collision")
    if any(f["rendering_operation"] == "copy_exact_bytes" and f["source_digest"] != f["rendered_digest"] for f in record["files"]):
        errors.append("copy_changed_bytes")
    for axis in ("installation", "worker"):
        if not set(record["required_effects"][axis]) <= set(context["authorized_effects"][axis]):
            errors.append("authority_exceeded")
        if "pure" in record["required_effects"][axis] and len(record["required_effects"][axis]) > 1:
            errors.append("pure_effect_conflict")
    required = set(context["required_capabilities"])
    if required != set(record["required_capabilities"]):
        errors.append("required_capability_binding_mismatch")
    resolved_ids = [c["capability_id"] for c in record["resolved_capabilities"]]
    if len(resolved_ids) != len(set(resolved_ids)):
        errors.append("capability_resolution_ambiguous")
    supported = {c["capability_id"] for c in record["resolved_capabilities"] if c["outcome"] == "supported"}
    if not required <= supported:
        errors.append("required_capability_unavailable")
    if record["launch_eligibility"] == "eligible":
        if record["client_binding"] != context["actual_client_binding"]:
            errors.append("client_binding_mismatch")
        if context["host_policy_future_starts_allowed"] is not True:
            errors.append("binding_disabled")
        if context["host_independent_qualification_verified"] is not True:
            errors.append("qualification_unavailable")
    return sorted(set(errors))


def main():
    names = {"profile": "native-client-layout-profile-v2.schema.json", "plan": "native-material-install-preview-v2.schema.json"}
    schemas = {key: json.loads((ROOT / name).read_text()) for key, name in names.items()}
    for schema in schemas.values():
        Draft202012Validator.check_schema(schema)
    validators = {key: Draft202012Validator(value, format_checker=FormatChecker()) for key, value in schemas.items()}
    rows = []
    index = json.loads((ROOT / "fixture-index.json").read_text())
    for entry in index["cases"]:
        raw = (ROOT / entry["path"]).read_bytes()
        if sha256(raw).hexdigest() != entry["sha256"]:
            raise SystemExit("Frozen fixture bytes changed: " + entry["path"])
        case = json.loads(raw)
        shape_errors = sorted(validators[case["schema"]].iter_errors(case["record"]), key=lambda e: str(list(e.path)))
        semantics = [] if shape_errors else (profile_errors(case["record"]) if case["schema"] == "profile" else plan_errors(case["record"], case["context"]))
        passed = ((not shape_errors) == case["expected_schema_valid"] and semantics == case["expected_semantic_errors"])
        rows.append({"fixture": entry["path"], "passed": passed, "schema_valid": not shape_errors,
                     "schema_errors": [{"path": list(e.path), "validator": e.validator} for e in shape_errors],
                     "semantic_errors": semantics, "establishes_native_qualification": False})
    report = {"record_type": "working_directory_compiler_draft_validation/v1", "component": "Harness Working Directory Compiler",
              "jsonschema_version": version("jsonschema"), "draft_only": True,
              "schemas": {name: sha256((ROOT / name).read_bytes()).hexdigest() for name in names.values()},
              "fixture_index_digest": sha256((ROOT / "fixture-index.json").read_bytes()).hexdigest(),
              "passed": all(row["passed"] for row in rows), "cases": rows,
              "limits": ["Schema and synthetic semantic checks only; no runtime registry or writer imports this validator",
                         "Host admission/qualification facts are synthetic test assumptions, not actual decisions",
                         "No native client, probe command, model, scheduling service or file installation ran"]}
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
