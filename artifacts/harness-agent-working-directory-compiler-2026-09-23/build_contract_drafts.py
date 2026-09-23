"""Build research-only schema candidates and synthetic fixtures; never runtime input."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMPONENT = "Harness Working Directory Compiler"
PROFILE = "native_client_layout_profile/v2"
PLAN = "native_material_install_preview/v2"
DRAFT = "research_only_not_runtime_admitted"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def digest(value):
    return sha256(canonical(value)).hexdigest()


def obj(properties, required=None, **extra):
    return {"type": "object", "properties": properties,
            "required": list(properties) if required is None else required,
            "additionalProperties": False, **extra}


def array(items, minimum=0, maximum=64, unique=False):
    return {"type": "array", "items": items, "minItems": minimum, "maxItems": maximum,
            **({"uniqueItems": True} if unique else {})}


TEXT = {"type": "string", "minLength": 1, "maxLength": 256}
ID = {"type": "string", "pattern": r"^[a-z][a-z0-9_.-]{0,127}$"}
SHA = {"type": "string", "pattern": "^[a-f0-9]{64}$"}
SEGMENT = {"type": "string", "minLength": 1, "maxLength": 100,
           "pattern": r"^(?!\.{1,2}$)(?!\.git$)[A-Za-z0-9._@+-]+$"}
PATH = {"type": "string", "maxLength": 400,
        "pattern": r"^(?!.*(?:^|/)\.{1,2}(?:/|$))(?!.*(?:^|/)\.git(?:/|$))[A-Za-z0-9._@+-]+(?:/[A-Za-z0-9._@+-]+)*$"}
REF = obj({"ref": TEXT, "digest": SHA})
NULLREF = {"oneOf": [{"type": "null"}, REF]}
NULLSHA = {"oneOf": [{"type": "null"}, SHA]}
EFFECT = {"enum": ["pure", "reads_fs", "writes_fs", "reads_secret", "network", "spawns_process"]}
EFFECTS = array(EFFECT, maximum=6, unique=True)
ROLES = ["instruction_file", "skill_definition", "skill_script", "skill_reference", "skill_asset",
         "subagent_definition", "command", "hook", "protocol_server_configuration", "plugin_manifest",
         "executable_tool", "configuration", "other"]
ROLE = {"enum": ROLES}
CLIENT = obj({"client_kind": ID, "interface": {"enum": ["cli", "editor", "api"]},
              "exact_version": TEXT, "operating_system": ID, "architecture": ID,
              "executable_digest": SHA, "effective_configuration_digest": SHA})
ACTIVATION = {"enum": ["initial_discovery", "on_demand", "explicit_activation", "explicit_read"]}
EVIDENCE_KINDS = ["documentation", "path_constructor", "native_discovery", "native_activation", "accepted_task"]


def schema(title, properties, **extra):
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": title,
            "$comment": "Research candidate only. JSON Schema validates shape, not native support, provenance, review or authority.",
            **obj(properties, **extra)}


profile_schema = schema(COMPONENT + " — ClientLayoutProfile v2 draft", {
    "record_type": {"const": PROFILE}, "component": {"const": COMPONENT}, "draft_status": {"const": DRAFT},
    "profile_id": ID, "profile_revision": TEXT, "client_binding": CLIENT,
    "compiler_contract_versions": array({"const": PLAN}, 1, 1, True),
    "locations": array(obj({"served_kind": {"enum": ["instruction_file", "skill", "tool", "reusable_code"]},
                             "file_role": ROLE, "directory_segments": array(SEGMENT, maximum=8),
                             "append_native_name": {"type": "boolean"},
                             "file_path_policy": {"enum": ["preserve_package_relative_path", "fixed_file_name"]},
                             "file_name": {"oneOf": [{"type": "null"}, SEGMENT]},
                             "rendering_operation": ID,
                             "scope": {"enum": ["attempt_project", "isolated_user_configuration"]},
                             "activation": ACTIVATION,
                             "precedence_rule": REF,
                             "trust_requirement": {"enum": ["isolated_untrusted", "explicit_project_trust", "host_managed_approval"]},
                             "native_probe_recipe": NULLREF},
                            allOf=[{"if": {"properties": {"file_path_policy": {"const": "fixed_file_name"}}},
                                    "then": {"properties": {"file_name": SEGMENT}},
                                    "else": {"properties": {"file_name": {"type": "null"}}}}]), 1, 64),
    "unplaced_roles": array(obj({"role": ROLE, "reason": TEXT})),
    "evidence": array(obj({"evidence_id": ID, "kind": {"enum": EVIDENCE_KINDS},
                            "artifact": REF, "observed_client_binding": {"oneOf": [{"type": "null"}, CLIENT]},
                            "observed_at": {"type": "string", "format": "date-time"}})),
    "evidence_claim": obj({"stage": {"enum": ["paths_constructed", "material_listed", "material_activated", "accepted_task"]},
                            "evidence_ids": array(ID, 1, 32, True)}),
    "independent_qualification": NULLREF,
    "unsupported_role_policy": {"const": "refuse"},
})

expected_existing = obj({"state": {"enum": ["absent", "managed_exact"]}, "digest": NULLSHA},
    allOf=[{"if": {"properties": {"state": {"const": "absent"}}},
            "then": {"properties": {"digest": {"type": "null"}}},
            "else": {"properties": {"digest": SHA}}}])
file_schema = obj({"package_identity": ID, "package_digest": SHA, "source_path": PATH,
                   "source_digest": SHA, "file_role": ROLE, "target_path": PATH,
                   "rendering_operation": ID, "rendered_digest": SHA,
                   "size_bytes": {"type": "integer", "minimum": 0, "maximum": 8388608},
                   "activation": ACTIVATION, "expected_existing": expected_existing})
bindings_schema = obj({key: SHA for key in ["profile_digest", "assignment_digest", "selection_digest",
                      "authority_digest", "workspace_state_digest", "engine_descriptor_digest",
                      "engine_installation_digest", "host_policy_digest"]})
plan_schema = schema(COMPONENT + " — native material installation preview v2 draft", {
    "record_type": {"const": PLAN}, "component": {"const": COMPONENT}, "draft_status": {"const": DRAFT},
    "plan_id": ID, "status": {"enum": ["compiled", "refused"]},
    "bindings": bindings_schema, "client_binding": CLIENT,
    "engine": obj({"slot_id": {"const": "material_install_layout"}, "engine_ref": TEXT}),
    "files": array(file_schema, maximum=64),
    "required_capabilities": array(ID, maximum=64, unique=True),
    "resolved_capabilities": array(obj({"capability_id": ID,
                                       "outcome": {"enum": ["supported", "unsupported_optional", "refused"]},
                                       "evidence": REF}), maximum=64),
    "required_effects": obj({"installation": EFFECTS, "worker": EFFECTS}),
    "runtime_handshake": obj({"state": {"enum": ["not_performed", "matched", "refused"]},
                               "selected_profile_record_type": {"const": PROFILE},
                               "selected_plan_record_type": {"const": PLAN},
                               "observation": NULLREF}),
    "launch_eligibility": {"enum": ["not_assessed", "eligible", "refused"]},
    "reasons": array(ID, maximum=32, unique=True),
    "writes_performed": {"const": False}, "authority_granted": {"const": False},
}, allOf=[
    {"if": {"properties": {"status": {"const": "refused"}}},
     "then": {"properties": {"files": {"maxItems": 0}, "reasons": {"minItems": 1},
                              "launch_eligibility": {"const": "refused"}}},
     "else": {"properties": {"files": {"minItems": 1}, "reasons": {"maxItems": 0}}}},
    {"if": {"properties": {"launch_eligibility": {"const": "eligible"}}},
     "then": {"properties": {"status": {"const": "compiled"},
                              "runtime_handshake": {"properties": {"state": {"const": "matched"},
                                                                     "observation": REF}}}}},
])


def h(label):
    return sha256(label.encode()).hexdigest()


def ref(label):
    return {"ref": "fixture:" + label, "digest": h(label)}


client = {"client_kind": "synthetic_cli", "interface": "cli", "exact_version": "fixture-1.0.0",
          "operating_system": "linux", "architecture": "x86_64", "executable_digest": h("fixture binary"),
          "effective_configuration_digest": h("fixture isolated config")}
profile = {"record_type": PROFILE, "component": COMPONENT, "draft_status": DRAFT,
           "profile_id": "fixture_layout", "profile_revision": "fixture-1", "client_binding": client,
           "compiler_contract_versions": [PLAN],
           "locations": [{"served_kind": "skill", "file_role": "skill_definition", "directory_segments": [".fixture", "skills"],
                          "append_native_name": True, "file_path_policy": "preserve_package_relative_path", "file_name": None,
                          "rendering_operation": "copy_exact_bytes", "scope": "attempt_project",
                          "activation": "on_demand", "precedence_rule": ref("fixture precedence"),
                          "trust_requirement": "isolated_untrusted", "native_probe_recipe": None}],
           "unplaced_roles": [{"role": role, "reason": "fixture does not support this role"} for role in ROLES if role != "skill_definition"],
           "evidence": [{"evidence_id": "path_construction", "kind": "path_constructor", "artifact": ref("fixture path construction"),
                         "observed_client_binding": None, "observed_at": "2026-09-23T18:00:00Z"}],
           "evidence_claim": {"stage": "paths_constructed", "evidence_ids": ["path_construction"]},
           "independent_qualification": None, "unsupported_role_policy": "refuse"}
plan = {"record_type": PLAN, "component": COMPONENT, "draft_status": DRAFT, "plan_id": "fixture_plan", "status": "compiled",
        "bindings": {key: h(key) for key in bindings_schema["properties"]}, "client_binding": client,
        "engine": {"slot_id": "material_install_layout", "engine_ref": "fixture.compiler@1.0.0"},
        "files": [{"package_identity": "fixture_skill", "package_digest": h("fixture canonical package"),
                   "source_path": "SKILL.md", "source_digest": h("fixture body"), "file_role": "skill_definition",
                   "target_path": ".fixture/skills/fixture-skill/SKILL.md", "rendering_operation": "copy_exact_bytes",
                   "rendered_digest": h("fixture body"), "size_bytes": 12, "activation": "on_demand",
                   "expected_existing": {"state": "absent", "digest": None}}],
        "required_capabilities": ["skill.discovery"],
        "resolved_capabilities": [{"capability_id": "skill.discovery", "outcome": "supported", "evidence": ref("synthetic capability assumption")}],
        "required_effects": {"installation": ["writes_fs"], "worker": ["reads_fs"]},
        "runtime_handshake": {"state": "not_performed", "selected_profile_record_type": PROFILE,
                              "selected_plan_record_type": PLAN, "observation": None},
        "launch_eligibility": "not_assessed", "reasons": [], "writes_performed": False, "authority_granted": False}
plan["bindings"]["profile_digest"] = digest(profile)
context = {"profile": deepcopy(profile), "expected_bindings": deepcopy(plan["bindings"]),
           "engine_supported_operations": ["copy_exact_bytes"],
           "authorized_effects": {"installation": ["writes_fs"], "worker": ["reads_fs"]},
           "actual_client_binding": deepcopy(client), "host_policy_future_starts_allowed": False,
           "host_independent_qualification_verified": False,
           "required_capabilities": ["skill.discovery"],
           "notice": "Synthetic test assumptions only; never native or admission evidence"}

cases = []


def add(name, schema_name, record, context_value, expected_schema, expected_semantic, note):
    cases.append({"name": name, "schema": schema_name, "record": deepcopy(record), "context": deepcopy(context_value),
                  "expected_schema_valid": expected_schema, "expected_semantic_errors": expected_semantic, "note": note})


add("01-candidate-profile-valid", "profile", profile, {}, True, [], "Path construction is honestly only path construction.")
add("02-preview-plan-valid", "plan", plan, context, True, [], "Candidate plan is inspectable; no launch assessment or effects occurred.")
refused = deepcopy(plan); refused.update(status="refused", files=[], launch_eligibility="refused", reasons=["client_version_mismatch"])
refused["runtime_handshake"]["state"] = "refused"
add("03-refused-plan-valid", "plan", refused, context, True, [], "A correctly typed refusal is valid output, not successful compilation.")
wrong = deepcopy(profile); wrong["locations"][0]["directory_segments"] = ["..", "escape"]
add("04-profile-traversal-invalid", "profile", wrong, {}, False, [], "Parent path segment refuses before effects.")
wrong = deepcopy(profile); wrong["record_type"] = "native_client_layout_profile/v1"
add("05-old-profile-version-invalid", "profile", wrong, {}, False, [], "Do not reinterpret v1 as v2.")
wrong = deepcopy(profile); wrong["evidence_claim"]["stage"] = "material_listed"
add("06-constructor-is-not-discovery", "profile", wrong, {}, True, ["evidence_stage_not_supported"], "A path constructor cannot qualify native discovery.")
wrong = deepcopy(plan); wrong["files"][0]["rendering_operation"] = "future_hook_interpreter"
add("07-new-semantics-need-engine", "plan", wrong, context, True, ["engine_semantics_unsupported"], "A new profile operation does not install executable semantics.")


def launch_case():
    p, c = deepcopy(plan), deepcopy(context)
    # Host checks are assumed only to isolate a fixture's single wrong condition.
    # These booleans are never asserted as actual evidence or persisted approval.
    c["host_policy_future_starts_allowed"] = True
    c["host_independent_qualification_verified"] = True
    p["launch_eligibility"] = "eligible"
    p["runtime_handshake"].update(state="matched", observation=ref("synthetic runtime observation"))
    return p, c


wrong, ctx = launch_case(); ctx["actual_client_binding"]["exact_version"] = "fixture-2.0.0"
add("08-runtime-version-mismatch", "plan", wrong, ctx, True, ["client_binding_mismatch"], "Scheduled source watch cannot replace exact launch binding.")
wrong, ctx = launch_case(); ctx["host_policy_future_starts_allowed"] = False
add("09-known-bad-binding-disabled", "plan", wrong, ctx, True, ["binding_disabled"], "Preserve history but stop new launches on a confirmed incompatible binding.")
wrong = deepcopy(plan); second = deepcopy(wrong["files"][0]); second["package_identity"] = "other_fixture"; second["source_digest"] = h("different source"); second["rendered_digest"] = h("different source"); wrong["files"].append(second)
add("10-two-packages-one-target", "plan", wrong, context, True, ["path_collision"], "Different package identity must not silently overwrite same target.")
wrong = deepcopy(plan); wrong["required_effects"]["worker"].append("network")
add("11-worker-authority-escalation", "plan", wrong, context, True, ["authority_exceeded"], "Installation permission does not grant worker networking.")
wrong = deepcopy(plan); wrong["resolved_capabilities"] = []
add("12-required-capability-omitted", "plan", wrong, context, True, ["required_capability_unavailable"], "An absent mandatory capability cannot become an optional omission.")


def save(relative, value):
    target = ROOT / relative
    if target.exists():
        raise SystemExit(f"Refuse replacing existing research artifact: {target.name}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    save("native-client-layout-profile-v2.schema.json", profile_schema)
    save("native-material-install-preview-v2.schema.json", plan_schema)
    for case in cases:
        save("fixtures/" + case["name"] + ".json", case)
    save("fixture-index.json", {"record_type": "working_directory_compiler_research_fixtures/v1", "component": COMPONENT,
                               "draft_status": DRAFT, "cases": [{"path": "fixtures/" + c["name"] + ".json",
                               "sha256": sha256((ROOT / ("fixtures/" + c["name"] + ".json")).read_bytes()).hexdigest()} for c in cases]})
