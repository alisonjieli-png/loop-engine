"""Replay one isolated constraint case from digest-bound local JSON resources.

Standard-library replay uses the shipped schema checker. Generation also uses
jsonschema as an independent oracle; --independent repeats that check only
when the caller already has jsonschema installed. No reference is fetched.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import re

if __package__:
    from . import schema_check
else:
    import schema_check

CASE_TYPE = "api_constraint_case/v1"
GROUP_TYPE = "api_constraint_group/v1"
GROUP_FILE = "constraint-group.json"
MAX_BYTES = 256 * 1024
MAX_CASE_BYTES = 16 * 1024
MAX_DEPTH = 40
MAX_NODES = 20_000
MAX_FILES = 64  # This generator's grouping policy, not a platform-wide file-count claim.
HEX = re.compile(r"[0-9a-f]{64}\Z")
CASE_FIELDS = {"record_type", "job_id", "parent_semantic_sha256", "schema", "baseline", "edit", "expected", "constraint_value"}
GROUP_FIELDS = {"record_type", "parent", "schema", "baselines", "cases", "case_job_set_sha256", "producer_family"}
PARENT_FIELDS = {"record_id", "package_digest", "schema_sha256", "semantic_sha256"}
ANNOTATIONS = {"title", "description", "default", "example", "examples", "$comment", "deprecated", "readOnly",
               "writeOnly", "externalDocs", "discriminator", "xml"}
SCHEMA_MAPS = {"properties", "patternProperties", "$defs", "definitions", "dependentSchemas"}


def encode(value):
    return (json.dumps(value, sort_keys=True, indent=1, ensure_ascii=False, allow_nan=False) + "\n").encode()


def sha(value):
    return hashlib.sha256(value).hexdigest()


def fingerprint(value):
    return sha(encode(value))


def _shape(value, fields, code):
    if type(value) is not dict or set(value) != fields:
        raise ValueError(code)


def _bounded(value):
    remaining, active = [MAX_NODES], set()

    def walk(node, depth=0):
        remaining[0] -= 1
        if depth > MAX_DEPTH or remaining[0] < 0:
            raise ValueError("case_json_structure_bound")
        if type(node) in (dict, list):
            if id(node) in active:
                raise ValueError("case_json_cycle")
            active.add(id(node))
            if isinstance(node, dict) and any(not isinstance(key, str) for key in node):
                raise ValueError("case_json_key_invalid")
            for child in node.values() if isinstance(node, dict) else node:
                walk(child, depth + 1)
            active.remove(id(node))
        elif type(node) not in (str, int, float, bool, type(None)):
            raise ValueError("case_json_value_invalid")
        elif isinstance(node, float) and not math.isfinite(node):
            raise ValueError("case_json_number_invalid")
        elif type(node) is int and node.bit_length() > 1024:
            raise ValueError("case_json_number_bound")
    walk(value)


def decode(raw, maximum=MAX_BYTES):
    if type(raw) is not bytes or len(raw) > maximum:
        raise ValueError("case_json_byte_bound")
    def pairs(rows):
        result = {}
        for key, value in rows:
            if key in result:
                raise ValueError("case_json_duplicate_key")
            result[key] = value
        return result
    def nonfinite(_value):
        raise ValueError("case_json_number_invalid")
    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)
    except (UnicodeError, RecursionError):
        raise ValueError("case_json_unreadable") from None
    _bounded(value)
    return value


def semantic_digest(schema):
    """Same assertion identity as the atom edge, independent of labels and ordering."""
    def walk(node, named=False):
        if isinstance(node, dict):
            output = {}
            for key, value in sorted(node.items()):
                if not named and (key in ANNOTATIONS or key == "$schema" or key.startswith("x-")):
                    continue
                value = walk(value, key in SCHEMA_MAPS)
                if not named and key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
                    value = sorted(value, key=encode)
                    if key != "oneOf":
                        value = list({encode(item): item for item in value}.values())
                output[key] = value
            return output
        if isinstance(node, list):
            return [walk(item) for item in node]
        return node
    _bounded(schema)
    return fingerprint(walk(schema))


def path_tokens(value):
    if type(value) is not list or len(value) > MAX_DEPTH or any(
            not (type(part) is int and part >= 0 or type(part) is str and len(part) <= 1024)
            for part in value):
        raise ValueError("case_path_invalid")
    return value


def at(value, path):
    current = value
    for part in path_tokens(path):
        if isinstance(current, dict) and type(part) is str and part in current:
            current = current[part]
        elif isinstance(current, list) and type(part) is int and part < len(current):
            current = current[part]
        else:
            raise ValueError("case_path_missing")
    return current


def edit(baseline, operation):
    if not isinstance(operation, dict) or operation.get("op") not in ("replace", "remove", "add"):
        raise ValueError("case_edit_invalid")
    expected = {"op", "path"} if operation["op"] == "remove" else {"op", "path", "value"}
    _shape(operation, expected, "case_edit_fields")
    path = path_tokens(operation["path"])
    _bounded(baseline)
    _bounded(operation)
    result = deepcopy(baseline)
    if not path:
        if operation["op"] != "replace":
            raise ValueError("case_root_edit_invalid")
        result = deepcopy(operation["value"])
    else:
        parent, key = at(result, path[:-1]), path[-1]
        if isinstance(parent, dict) and type(key) is str:
            exists = key in parent
        elif isinstance(parent, list) and type(key) is int:
            exists = key < len(parent)
        else:
            raise ValueError("case_edit_target_invalid")
        if operation["op"] == "add":
            if not isinstance(parent, dict) or exists:
                raise ValueError("case_add_requires_new_member")
            parent[key] = deepcopy(operation["value"])
        else:
            if not exists:
                raise ValueError("case_edit_target_missing")
            if operation["op"] == "remove":
                del parent[key]
            else:
                parent[key] = deepcopy(operation["value"])
    if encode(result) == encode(baseline) or len(encode(result)) > MAX_CASE_BYTES:
        raise ValueError("case_edit_unchanged_or_oversized")
    return result


def ref(value):
    _shape(value, {"path", "sha256"}, "case_resource_ref_invalid")
    path, digest = value["path"], value["sha256"]
    if (not isinstance(path, str) or not path or path.startswith("/") or "\\" in path
            or len(path) > 200 or len(path.split("/")) > 8
            or any(part in ("", ".", "..") or part.startswith(".")
                   or re.fullmatch(r"[A-Za-z0-9_@+.-]{1,100}", part) is None for part in path.split("/"))
            or not isinstance(digest, str) or HEX.fullmatch(digest) is None):
        raise ValueError("case_resource_ref_invalid")
    return value


def resource(payloads, reference):
    ref(reference)
    raw = payloads.get(reference["path"])
    if type(raw) is not bytes or sha(raw) != reference["sha256"]:
        raise ValueError("case_resource_digest_mismatch")
    return decode(raw)


def read_case(value):
    _shape(value, CASE_FIELDS, "constraint_case_fields")
    if value["record_type"] != CASE_TYPE or not HEX.fullmatch(str(value["job_id"])):
        raise ValueError("constraint_case_version_or_identity")
    ref(value["schema"])
    ref(value["baseline"])
    expected = value["expected"]
    _shape(expected, {"validator", "schema_path", "instance_path", "shipped_path", "shipped_message"}, "case_expected_fields")
    path_tokens(expected["schema_path"])
    path_tokens(expected["instance_path"])
    if any(type(expected[name]) is not str or not expected[name] for name in ("validator", "shipped_path", "shipped_message")):
        raise ValueError("case_expected_invalid")
    identity = fingerprint([value["parent_semantic_sha256"], expected["schema_path"], value["constraint_value"]])
    if identity != value["job_id"]:
        raise ValueError("case_job_identity_mismatch")
    return value


def validate_schema(schema):
    _bounded(schema)
    def visit(node):
        if isinstance(node, dict):
            if any(key in node for key in ("$ref", "$recursiveRef", "$dynamicRef")):
                raise ValueError("case_schema_requires_resolved_references")
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)
    visit(schema)


def replay(value, payloads, *, independent=False):
    case = read_case(value)
    schema, baseline = resource(payloads, case["schema"]), resource(payloads, case["baseline"])
    validate_schema(schema)
    if semantic_digest(schema) != case["parent_semantic_sha256"]:
        raise ValueError("case_parent_semantics_mismatch")
    expected = case["expected"]
    if encode(at(schema, expected["schema_path"])) != encode(case["constraint_value"]) and expected["validator"] != "required":
        raise ValueError("case_constraint_value_mismatch")
    if expected["validator"] == "required" and case["constraint_value"] not in at(schema, expected["schema_path"]):
        raise ValueError("case_constraint_value_mismatch")
    if not expected["schema_path"] or expected["schema_path"][-1] != expected["validator"]:
        raise ValueError("case_validator_path_mismatch")
    operation = case["edit"]
    if not isinstance(operation, dict):
        raise ValueError("case_edit_invalid")
    path = path_tokens(operation.get("path"))
    target = expected["instance_path"]
    if expected["validator"] == "required":
        aligned = operation.get("op") == "remove" and path == target + [case["constraint_value"]]
    elif expected["validator"] == "additionalProperties":
        aligned = operation.get("op") == "add" and len(path) == len(target) + 1 and path[:-1] == target
    else:
        aligned = operation.get("op") == "replace" and path == target
    if not aligned:
        raise ValueError("case_edit_not_at_expected_target")
    if schema_check.errors(baseline, schema):
        raise ValueError("case_baseline_not_valid")
    changed = edit(baseline, case["edit"])
    actual = schema_check.errors(changed, schema)
    if actual != [expected["shipped_path"] + ": " + expected["shipped_message"]]:
        raise ValueError("case_shipped_error_mismatch")
    if independent:
        from jsonschema import Draft202012Validator
        validator = Draft202012Validator(schema)
        if not validator.is_valid(baseline):
            raise ValueError("case_independent_baseline_not_valid")
        errors = list(validator.iter_errors(changed))
        if (len(errors) != 1 or errors[0].validator != expected["validator"]
                or list(errors[0].absolute_schema_path) != expected["schema_path"]
                or list(errors[0].absolute_path) != expected["instance_path"]):
            raise ValueError("case_independent_error_mismatch")
    return {"record_type": "api_constraint_replay/v1", "job_id": case["job_id"], "baseline_valid": True,
            "isolated_violation": True, "independent_oracle_checked": independent, "network_calls": 0}


def read_group(payloads, *, independent=False, replay_cases=False):
    group = decode(payloads[GROUP_FILE])
    _shape(group, GROUP_FIELDS, "constraint_group_fields")
    _shape(group["parent"], PARENT_FIELDS, "constraint_parent_fields")
    if (group["record_type"] != GROUP_TYPE or not isinstance(group["producer_family"], str)
            or re.fullmatch(r"[a-z][a-z0-9_.-]{0,63}", group["producer_family"]) is None):
        raise ValueError("constraint_group_version_or_producer")
    schema = resource(payloads, group["schema"])
    parent = group["parent"]
    if (group["schema"]["sha256"] != parent["schema_sha256"] or semantic_digest(schema) != parent["semantic_sha256"]
            or HEX.fullmatch(str(parent["package_digest"])) is None or not isinstance(parent["record_id"], str)):
        raise ValueError("constraint_parent_binding")
    jobs, paths = [], set()
    if not isinstance(group["baselines"], list) or not 1 <= len(group["baselines"]) <= MAX_FILES:
        raise ValueError("constraint_group_baselines")
    baseline_refs = {ref(value)["sha256"]: value for value in group["baselines"]}
    if len(baseline_refs) != len(group["baselines"]) or not isinstance(group["cases"], list) or not group["cases"]:
        raise ValueError("constraint_group_population")
    for entry in group["cases"]:
        _shape(entry, {"job_id", "path", "sha256"}, "constraint_case_entry")
        case = read_case(resource(payloads, {key: entry[key] for key in ("path", "sha256")}))
        if (entry["path"] != "cases/" + case["job_id"] + ".json" or entry["job_id"] != case["job_id"]
                or case["schema"] != group["schema"] or case["parent_semantic_sha256"] != parent["semantic_sha256"]
                or baseline_refs.get(case["baseline"]["sha256"]) != case["baseline"]):
            raise ValueError("constraint_case_group_binding")
        resource(payloads, case["baseline"])
        if replay_cases:
            replay(case, payloads, independent=independent)
        jobs.append(case["job_id"])
        paths.add(entry["path"])
    if len(jobs) != len(set(jobs)) or len(paths) != len(jobs):
        raise ValueError("constraint_group_duplicate_case")
    if paths != {path for path in payloads if path.startswith("cases/")}:
        raise ValueError("constraint_group_unlisted_case")
    if len(payloads) > MAX_FILES:
        raise ValueError("constraint_group_file_bound")
    if group["case_job_set_sha256"] != fingerprint(sorted(jobs)):
        raise ValueError("constraint_group_job_set_mismatch")
    return group


def group_key(group):
    return fingerprint({"parent": group["parent"], "case_jobs": sorted(row["job_id"] for row in group["cases"])})


def load_folder(folder):
    folder = Path(folder).absolute()
    if folder.resolve() != folder or not folder.is_dir():
        raise ValueError("case_folder_not_regular")
    def read(relative):
        path = folder / relative
        if path.resolve() != path or not path.is_file() or path.stat().st_size > MAX_BYTES:
            raise ValueError("case_resource_not_regular_or_bounded")
        return path.read_bytes()
    payloads = {GROUP_FILE: read(GROUP_FILE)}
    group = decode(payloads[GROUP_FILE])
    _shape(group, GROUP_FIELDS, "constraint_group_fields")
    references = [group["schema"], *group["baselines"],
                  *({key: row[key] for key in ("path", "sha256")} for row in group["cases"])]
    if len(references) + 1 > MAX_FILES:
        raise ValueError("case_group_file_bound")
    for reference in references:
        relative = ref(reference)["path"]
        payloads[relative] = read(relative)
    return payloads


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("folder", type=Path)
    parser.add_argument("--independent", action="store_true")
    options = parser.parse_args()
    files = load_folder(options.folder)
    group = read_group(files)
    results = [replay(resource(files, {key: row[key] for key in ("path", "sha256")}), files, independent=options.independent)
               for row in group["cases"]]
    print(json.dumps({"record_type": "api_constraint_group_replay/v1", "cases_passed": len(results),
                      "independent_oracle_checked": options.independent, "network_calls": 0}))
