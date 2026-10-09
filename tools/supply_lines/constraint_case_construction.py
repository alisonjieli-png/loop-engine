"""One bounded, isolated invalid edit per declared schema constraint job.

Reuses all distinct valid parent baselines in deterministic digest order. It
adds no alternate fixture generator or dependency. A job is emitted at most
once, even if several baselines can expose its isolated failure.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from importlib.metadata import version

from jsonschema import Draft202012Validator

from . import constraint_case_runtime as runtime
from . import schema_check

MISSING = object()
SUPPORTED = frozenset({"type", "enum", "const", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum",
    "minLength", "maxLength", "pattern", "minItems", "maxItems", "uniqueItems", "required", "additionalProperties"})
UNSUPPORTED = frozenset({"multipleOf", "minProperties", "maxProperties", "dependentRequired", "dependentSchemas",
    "contains", "minContains", "maxContains", "propertyNames", "if", "then", "else", "not", "prefixItems", "allOf", "anyOf", "oneOf"})
PROBE_MEMBER = "__constraint_probe__"
DIAGNOSTICS_FIELD = "diagnostics"
ORACLE_VERSION = version("jsonschema")


def walk(schema, value, data_path=(), schema_path=()):
    if not isinstance(schema, dict):
        return
    for key, bound in schema.items():
        if key in UNSUPPORTED:
            yield {"unsupported": key, "schema_path": list(schema_path + (key,))}
        if key in SUPPORTED:
            values = bound if key == "required" else [bound]
            if key == "additionalProperties" and bound is not False:
                continue
            for constraint in values:
                yield {"keyword": key, "bound": constraint, "schema_path": list(schema_path + (key,)),
                       "data_path": list(data_path), "value": value}
    for name, child in schema.get("properties", {}).items():
        child_value = value.get(name, MISSING) if isinstance(value, dict) else MISSING
        yield from walk(child, child_value, data_path + (name,), schema_path + ("properties", name))
    if isinstance(schema.get("items"), dict):
        child_value = value[0] if isinstance(value, list) and value else MISSING
        yield from walk(schema["items"], child_value, data_path + (0,), schema_path + ("items",))
    for keyword in ("allOf", "anyOf", "oneOf"):
        for index, child in enumerate(schema.get(keyword, [])):
            yield from walk(child, value, data_path, schema_path + (keyword, index))


def edits(job):
    key, bound, value, path = job["keyword"], job["bound"], job["value"], job["data_path"]
    if value is MISSING:
        return []
    if key == "required":
        return [{"op": "remove", "path": path + [bound]}] if isinstance(value, dict) and bound in value else []
    if key == "additionalProperties":
        return [{"op": "add", "path": path + [PROBE_MEMBER], "value": None}] if isinstance(value, dict) and PROBE_MEMBER not in value else []
    values = []
    if key in ("type", "enum", "const", "pattern"):
        values = [None, True, 0, "", [], {}, "!"]
    elif key in ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum"):
        if type(value) in (int, float) and type(bound) in (int, float):
            values = [bound - 1 if key == "minimum" else bound + 1 if key == "maximum" else bound]
    elif key in ("minLength", "maxLength") and isinstance(value, str) and type(bound) is int and 0 <= bound <= 1024:
        length = bound - 1 if key == "minLength" else bound + 1
        values = ["x" * length] if length >= 0 else []
    elif key == "minItems" and isinstance(value, list) and type(bound) is int and bound > 0 and len(value) >= bound:
        values = [value[:bound - 1]]
    elif key == "maxItems" and isinstance(value, list) and value and type(bound) is int and 0 <= bound <= 64:
        values = [[deepcopy(value[0]) for _ in range(bound + 1)]]
    elif key == "uniqueItems" and bound is True and isinstance(value, list) and value:
        values = [[*deepcopy(value), deepcopy(value[0])]]
    return [{"op": "replace", "path": path, "value": candidate} for candidate in values
            if runtime.encode(candidate) != runtime.encode(value)]


def shipped_expected(job, schema):
    key, bound = job["keyword"], job["bound"]
    path = "$" + "".join(f"[{part}]" if isinstance(part, int) else "." + part for part in job["data_path"])
    if key == "additionalProperties":
        path += "." + PROBE_MEMBER
    messages = {"enum": "not one of the allowed values", "const": "not the constant value",
        "minimum": f"below the minimum {bound}", "maximum": f"above the maximum {bound}",
        "exclusiveMinimum": f"not above {bound}", "exclusiveMaximum": f"not below {bound}",
        "minLength": f"shorter than {bound}", "maxLength": f"longer than {bound}", "pattern": f"does not match {bound}",
        "minItems": f"fewer than {bound} items", "maxItems": f"more than {bound} items", "uniqueItems": "items are not unique",
        "required": f"lacks {bound}", "additionalProperties": "no value is allowed here"}
    if key == "type":
        kinds = [bound] if isinstance(bound, str) else bound
        messages[key] = "expected " + " or ".join(kinds)
    return path, messages[key]


def construct(schema_bytes, baseline_values):
    """(cases, shared baseline bodies, complete attempt accounting). Approves nothing."""
    schema = runtime.decode(schema_bytes)
    runtime.validate_schema(schema)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    valid, invalid = {}, 0
    for value in baseline_values:
        runtime._bounded(value)
        body = runtime.encode(value)
        if len(body) <= runtime.MAX_CASE_BYTES and validator.is_valid(value) and not schema_check.errors(value, schema):
            valid[runtime.sha(body)] = (value, body)
        else:
            invalid += 1
    if not valid:
        raise ValueError("constraint_parent_has_no_valid_baseline")
    schema_ref = {"path": "contract.schema.json", "sha256": runtime.sha(schema_bytes)}
    semantic = runtime.semantic_digest(schema)
    cases, findings, keywords, accepted, attempts = [], Counter(), Counter(), Counter(), 0
    diagnostics, jobs, unsupported, used_baselines = [], {}, set(), {}
    for baseline_digest in sorted(valid):
        baseline, body = valid[baseline_digest]
        baseline_ref = {"path": "baselines/" + baseline_digest + ".json", "sha256": baseline_digest}
        within_baseline = set()
        for job in walk(schema, baseline):
            if "unsupported" in job:
                identity = runtime.fingerprint(job)
                if identity not in unsupported:
                    findings["unsupported:" + job["unsupported"]] += 1
                    unsupported.add(identity)
                continue
            identity = runtime.fingerprint([semantic, job["schema_path"], job["bound"]])
            if identity in within_baseline:
                continue
            within_baseline.add(identity)
            jobs.setdefault(identity, []).append((job, baseline_ref, body))
    for identity, alternatives in jobs.items():
        keyword = alternatives[0][0]["keyword"]
        keywords[keyword] += 1
        emitted, available_value, had_probe = False, False, False
        for job, baseline_ref, body in alternatives:
            available_value = available_value or job["value"] is not MISSING
            options = edits(job)
            had_probe = had_probe or bool(options)
            path, message = shipped_expected(job, schema)
            expected = {"validator": keyword, "schema_path": job["schema_path"], "instance_path": job["data_path"],
                        "shipped_path": path, "shipped_message": message}
            for operation in options:
                attempts += 1
                case = {"record_type": runtime.CASE_TYPE, "job_id": identity, "parent_semantic_sha256": semantic,
                        "schema": schema_ref, "baseline": baseline_ref, "edit": operation,
                        "expected": expected, "constraint_value": job["bound"]}
                try:
                    if len(runtime.encode(case)) > runtime.MAX_CASE_BYTES:
                        raise ValueError("case_record_byte_bound")
                    runtime.replay(case, {schema_ref["path"]: schema_bytes, baseline_ref["path"]: body}, independent=True)
                except (ValueError, TypeError, LookupError, OverflowError, RecursionError):
                    continue
                cases.append(case)
                used_baselines[baseline_ref["path"]] = body
                accepted[keyword] += 1
                emitted = True
                break
            if emitted:
                break
        if not emitted:
            reason = ("no_isolated_agreed_target_failure" if had_probe else
                      "no_probe_candidate" if available_value else "missing_baseline_member")
            findings[reason] += 1
            diagnostics.append({"job_id": identity, "keyword": keyword, "schema_path": job["schema_path"], "reason": reason})
    return cases, used_baselines, {
        "supported_jobs": len(jobs), "jobs_by_keyword": dict(keywords), "accepted_cases": len(cases),
        "valid_baselines_considered": len(valid), "invalid_baselines_ignored": invalid,
        "distinct_baselines_used": len(used_baselines),
        "accepted_by_keyword": dict(accepted), "probe_attempts": attempts, "findings": dict(findings),
        DIAGNOSTICS_FIELD: diagnostics, "independent_oracle": "jsonschema.Draft202012Validator",
        "independent_oracle_version": ORACLE_VERSION,
        "shipped_checker_agreed": True, "approved": False}
