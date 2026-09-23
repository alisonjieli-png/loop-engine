"""Check an explicit brief's structure and output-check coverage, from stdin only."""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location("brief_protocol", Path(__file__).with_name("protocol.py"))
_protocol = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_protocol)

IDENTIFIER = re.compile(r"[a-z][a-z0-9_-]{0,63}\Z")
FIELDS = {"record_type", "objective", "inputs", "outputs", "constraints",
          "out_of_scope", "acceptance_checks", "unresolved_questions",
          "requested_effects", "authority_reference"}
EFFECTS = {"read_selected_inputs", "write_declared_outputs", "shell", "network", "model"}


def valid_text(value, maximum=2000):
    return (isinstance(value, str) and bool(value.strip()) and len(value) <= maximum
            and not any(0xD800 <= ord(c) <= 0xDFFF or (ord(c) < 32 and c not in "\n\t\r")
                        for c in value))


def validate(value):
    issues = []

    def issue(code, field):
        issues.append({"code": code, "field": field})

    if not isinstance(value, dict):
        return [{"code": "object_required", "field": "$"}]
    if set(value) != FIELDS:
        issue("exact_fields_required", "$")
    if value.get("record_type") != "baltor_step_brief/v1":
        issue("unsupported_record_type", "record_type")
    for key in ("objective", "authority_reference"):
        if not valid_text(value.get(key), 2000 if key == "objective" else 256):
            issue("bounded_text_required", key)
    for key in ("inputs", "outputs"):
        items = value.get(key)
        if (not isinstance(items, list) or not 1 <= len(items) <= 32
                or any(not isinstance(x, str) or not IDENTIFIER.fullmatch(x) for x in items)):
            issue("identifier_list_required", key)
        elif len(set(items)) != len(items):
            issue("duplicate_identifier", key)
    for key in ("constraints", "out_of_scope", "unresolved_questions"):
        items = value.get(key)
        if (not isinstance(items, list) or not (0 if key == "unresolved_questions" else 1) <= len(items) <= 32
                or any(not valid_text(x) for x in items)):
            issue("bounded_text_list_required", key)
        elif len(set(items)) != len(items):
            issue("duplicate_text", key)
    effects = value.get("requested_effects")
    if (not isinstance(effects, list) or len(effects) > len(EFFECTS)
            or any(not isinstance(x, str) or x not in EFFECTS for x in effects)):
        issue("effect_list_required", "requested_effects")
    elif len(set(effects)) != len(effects):
        issue("duplicate_effect", "requested_effects")
    checks = value.get("acceptance_checks")
    outputs = value.get("outputs")
    valid_outputs = (isinstance(outputs, list)
                     and all(isinstance(x, str) and IDENTIFIER.fullmatch(x) for x in outputs))
    if not isinstance(checks, list) or not 1 <= len(checks) <= 32:
        issue("check_list_required", "acceptance_checks")
    else:
        names, covered = set(), set()
        for index, check in enumerate(checks):
            field = f"acceptance_checks[{index}]"
            if (not isinstance(check, dict) or set(check) != {"id", "output", "assertion"}
                    or not isinstance(check.get("id"), str) or not IDENTIFIER.fullmatch(check["id"])
                    or not isinstance(check.get("output"), str) or not IDENTIFIER.fullmatch(check["output"])
                    or not valid_text(check.get("assertion"))):
                issue("check_shape_required", field)
                continue
            if check["id"] in names:
                issue("duplicate_check_id", field)
            names.add(check["id"])
            if valid_outputs and check["output"] not in outputs:
                issue("unknown_output", field)
            covered.add(check["output"])
        if valid_outputs and not set(outputs).issubset(covered):
            issue("output_missing_check", "acceptance_checks")
    return issues


def main():
    digest = None
    value = None
    try:
        value, digest = _protocol.parse_input(sys.stdin.buffer)
        issues = validate(value)
    except _protocol.InvalidInput as exc:
        issues = [{"code": str(exc), "field": "$"}]
    valid = not issues
    _protocol.write_json({"record_type": "baltor_step_brief_check/v1",
                          "structure_valid": valid,
                          "input_sha256": digest,
                          "unresolved_question_count": len(value["unresolved_questions"]) if valid else None,
                          "issues": issues,
                          "scope": "structure_and_declared_output_check_coverage",
                          "authority_granted": False,
                          "semantic_review_required": True}, sys.stdout)
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
