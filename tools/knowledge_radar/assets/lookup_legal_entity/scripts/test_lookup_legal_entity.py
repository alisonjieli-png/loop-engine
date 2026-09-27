#!/usr/bin/env python3
"""Network-free check of lookup_legal_entity against verification/cases.json.

Run it from the package folder:

    python3 scripts/test_lookup_legal_entity.py

A request case calls the command line entry main() with a fake fetch that serves
the case's fixtures from verification/ in order and records every request the
tool makes, so the test never uses the network. A redirect case checks the
same-host redirect rule and a size_limit case checks the 2 MB read limit.

A known-wrong case carries a deliberately wrong expectation and passes only
when the tool succeeds and its output does not match that expectation. Every
successful output is checked against contracts/output.schema.json, and a case
that states request_matches_input_schema is checked against
contracts/input.schema.json, so the contract and the tool's own request checks
cannot drift apart unnoticed.

The test prints one JSON line {"passed": n, "failed": m, "known_wrong_rejected": k}
and exits 0 only when every case passed.
"""
from __future__ import annotations

import io
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
SCRIPTS = Path(__file__).resolve().parent
PACKAGE = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

import lookup_legal_entity as tool  # noqa: E402  (the module is found through the path set above)

CASES_RECORD = "knowledge_radar_tool_cases/v1"
FIXTURE_RECORD = "knowledge_radar_fixture/v1"
MISSING = object()


def read_json(relative: str):
    return json.loads((PACKAGE / relative).read_text(encoding="utf-8"))


INPUT_SCHEMA = read_json("contracts/input.schema.json")
OUTPUT_SCHEMA = read_json("contracts/output.schema.json")

# A small JSON Schema checker for the keywords the contracts use. An unknown
# keyword stops the test, so a contract can never pass by being misread.
KEYWORDS = {"type", "enum", "const", "properties", "required", "additionalProperties", "patternProperties",
            "items", "minItems", "maxItems", "uniqueItems", "minLength", "maxLength", "pattern", "minimum",
            "maximum", "exclusiveMinimum", "oneOf", "anyOf", "$ref"}
ANNOTATIONS = {"$schema", "$id", "$comment", "$defs", "title", "description", "default", "examples", "format"}


def is_type(value, name: str) -> bool:
    if name == "integer":
        return type(value) is int or (type(value) is float and value.is_integer())
    if name == "number":
        return type(value) in (int, float)
    kinds = {"null": type(None), "boolean": bool, "string": str, "array": list, "object": dict}
    return type(value) is kinds[name]


def same(first, second) -> bool:
    return json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def schema_problems(value, schema, root, path="$") -> list:
    if schema is True:
        return []
    if schema is False:
        return [f"{path} is not allowed"]
    unknown = set(schema) - KEYWORDS - ANNOTATIONS
    if unknown:
        raise ValueError(f"the test schema checker does not know {sorted(unknown)}")
    problems = []
    if "$ref" in schema:
        target = root
        for part in schema["$ref"].removeprefix("#/").split("/"):
            target = target[part]
        problems += schema_problems(value, target, root, path)
    if "type" in schema:
        names = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(is_type(value, name) for name in names):
            return problems + [f"{path} is not of type {names}"]
    if "const" in schema and not same(value, schema["const"]):
        problems.append(f"{path} is not the constant value")
    if "enum" in schema and not any(same(value, option) for option in schema["enum"]):
        problems.append(f"{path} is not an allowed value")
    if type(value) is str:
        if len(value) < schema.get("minLength", 0) or len(value) > schema.get("maxLength", len(value)):
            problems.append(f"{path} has a length outside the allowed range")
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            problems.append(f"{path} does not match its pattern")
    if is_type(value, "number") and type(value) is not bool:
        if value < schema.get("minimum", value) or value > schema.get("maximum", value):
            problems.append(f"{path} is outside the allowed range")
        if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
            problems.append(f"{path} is not above its exclusive minimum")
    if type(value) is list:
        if len(value) < schema.get("minItems", 0) or len(value) > schema.get("maxItems", len(value)):
            problems.append(f"{path} has a number of items outside the allowed range")
        if schema.get("uniqueItems") and len({json.dumps(item, sort_keys=True) for item in value}) != len(value):
            problems.append(f"{path} repeats an item")
        if "items" in schema:
            for index, item in enumerate(value):
                problems += schema_problems(item, schema["items"], root, f"{path}[{index}]")
    if type(value) is dict:
        problems += [f"{path} lacks {key}" for key in schema.get("required", []) if key not in value]
        for key, item in value.items():
            matched = key in schema.get("properties", {})
            if matched:
                problems += schema_problems(item, schema["properties"][key], root, f"{path}.{key}")
            for pattern, subschema in schema.get("patternProperties", {}).items():
                if re.search(pattern, key):
                    matched = True
                    problems += schema_problems(item, subschema, root, f"{path}.{key}")
            if not matched and "additionalProperties" in schema:
                problems += schema_problems(item, schema["additionalProperties"], root, f"{path}.{key}")
    if "anyOf" in schema and all(schema_problems(value, option, root, path) for option in schema["anyOf"]):
        problems.append(f"{path} matches none of anyOf")
    if "oneOf" in schema:
        matches = sum(1 for option in schema["oneOf"] if not schema_problems(value, option, root, path))
        if matches != 1:
            problems.append(f"{path} matches {matches} branches of oneOf, not exactly one")
    return problems


def load_fixture(name: str) -> dict:
    if re.fullmatch(r"fixture-[a-z0-9-]+\.json", name) is None:
        raise ValueError(f"{name} is not a fixture file name")
    record = read_json(f"verification/{name}")
    if (record.get("record_type") != FIXTURE_RECORD or type(record.get("status")) is not int
            or type(record.get("body_text")) is not str):
        raise ValueError(f"{name} is not a {FIXTURE_RECORD} record")
    return record


NETWORK_ERRORS = {"timeout": TimeoutError("the fake network timed out"),
                  "connection_refused": ConnectionRefusedError("the fake network refused the connection")}


class FakeFetch:
    """Serves the case's fixtures in order and records every request the tool makes.

    With a fetch_error the fake network fails the way a real one can, before any answer.
    """

    def __init__(self, fixtures: list, error=None) -> None:
        self.answers = list(fixtures)
        self.requests = []
        self.error = error

    def __call__(self, url: str, body, headers: dict) -> tuple:
        self.requests.append({"url": url, "body": None if body is None else json.loads(body.decode("utf-8"))})
        if self.error is not None:
            raise NETWORK_ERRORS[self.error]
        if not self.answers:
            raise LookupError("the tool asked for more answers than the case provides")
        answer = self.answers.pop(0)
        return answer["status"], answer["body_text"].encode("utf-8")


def fixed_time(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def call_tool(case: dict) -> tuple:
    fake = FakeFetch([load_fixture(name) for name in case.get("fixtures", [])], case.get("fetch_error"))
    moment = fixed_time(case["now"])
    stdin = io.StringIO("")
    arguments = case.get("arguments")
    if arguments is None:
        text = json.dumps(case["request"])
        if case.get("via_stdin"):
            arguments, stdin = ["-"], io.StringIO(text)
        else:
            arguments = [text]
    stdout = io.StringIO()
    exit_code = tool.main(arguments, fetch=fake, now=lambda: moment, stdin=stdin, stdout=stdout)
    lines = stdout.getvalue().splitlines()
    if len(lines) != 1:
        raise AssertionError(f"the tool printed {len(lines)} lines instead of one JSON line")
    return exit_code, json.loads(lines[0]), fake


def expectation_mismatches(expected: dict, exit_code: int, output: dict) -> list:
    if expected["outcome"] == "error":
        mismatches = []
        if exit_code != expected["exit_code"]:
            mismatches.append(f"exit code {exit_code} instead of {expected['exit_code']}")
        if (set(output) != {"record_type", "code", "message"} or output["record_type"] != tool.ERROR_RECORD
                or output["code"] != expected["code"] or not output["message"]):
            mismatches.append(f"printed {output} instead of the error record {expected['code']}")
        return mismatches
    if exit_code != 0:
        return [f"exit code {exit_code} instead of 0: {output}"]
    if "result" in expected:
        return [] if output == expected["result"] else [f"printed {output} instead of {expected['result']}"]
    return [f"{key} is {output.get(key, 'missing')!r} instead of {value!r}"
            for key, value in expected["fields"].items() if output.get(key, MISSING) != value]


def check_request_case(case: dict) -> tuple:
    """Returns (problems, known wrong rejected)."""
    exit_code, output, fake = call_tool(case)
    problems = []
    if exit_code == 0:
        problems += [f"output contract: {problem}" for problem in schema_problems(output, OUTPUT_SCHEMA, OUTPUT_SCHEMA)]
    if "request_matches_input_schema" in case:
        accepted = not schema_problems(case["request"], INPUT_SCHEMA, INPUT_SCHEMA)
        if accepted != case["request_matches_input_schema"]:
            problems.append(f"the input contract {'accepts' if accepted else 'refuses'} the request")
    if "fetch_calls" in case and len(fake.requests) != case["fetch_calls"]:
        problems.append(f"the tool made {len(fake.requests)} requests instead of {case['fetch_calls']}")
    if "expected_requests" in case and fake.requests != case["expected_requests"]:
        problems.append(f"the tool requested {fake.requests} instead of {case['expected_requests']}")
    mismatches = expectation_mismatches(case["expected"], exit_code, output)
    if not case.get("known_wrong"):
        return problems + mismatches, False
    if exit_code != 0 or not mismatches:
        return problems + ["the tool output matched the deliberately wrong expectation or did not succeed"], False
    return problems, not problems


def check_redirect_case(case: dict) -> list:
    request = urllib.request.Request(case["from"])
    try:
        followed = tool.SameHostRedirects().redirect_request(request, io.BytesIO(b""), 302, "Found", {}, case["to"])
    except tool.ToolError as error:
        return expectation_mismatches(case["expected"], error.exit_code, error.to_record())
    if case["expected"]["outcome"] != "followed" or getattr(followed, "full_url", None) != case["to"]:
        return [f"the redirect to {case['to']} was followed"]
    return []


def check_size_case(case: dict) -> list:
    try:
        body = tool.bounded_read(io.BytesIO(b"x" * case["bytes"]))
    except tool.ToolError as error:
        return expectation_mismatches(case["expected"], error.exit_code, error.to_record())
    if case["expected"]["outcome"] != "read" or len(body) != case["bytes"]:
        return [f"an answer of {case['bytes']} bytes was read"]
    return []


def coverage_problems(cases: list) -> list:
    """The negative cases this package must keep; removing one fails the test."""
    problems = []
    if not any(case.get("known_wrong") for case in cases):
        problems.append("no known-wrong case")
    if not any(case.get("fixtures") and case["expected"].get("exit_code") == 3 for case in cases):
        problems.append("no malformed upstream answer that must end with exit code 3")
    if not any(case.get("fetch_calls") == 0 and case["expected"].get("exit_code") == 2 for case in cases):
        problems.append("no invalid request refused before any fetch")
    if not any(case.get("fetch_error") and case["expected"].get("code") == "source_unreachable" for case in cases):
        problems.append("no network failure that must end with source_unreachable")
    if not any(case["expected"].get("code") == "invalid_lei" and case.get("fetch_calls") == 0
               and case.get("request_matches_input_schema") is True for case in cases):
        problems.append("no LEI with a bad check digit refused before any fetch")
    if not any(case["expected"].get("outcome") == "result" and case["expected"].get("result", {}).get("count") == 0
               for case in cases):
        problems.append("no LEI that GLEIF does not hold")
    if not any(case["expected"].get("code") == "redirect_refused" for case in cases):
        problems.append("no redirect to another host refused")
    return problems


def main() -> int:
    document = read_json("verification/cases.json")
    if document.get("record_type") != CASES_RECORD or type(document.get("cases")) is not list:
        print(f"verification/cases.json is not a {CASES_RECORD} record", file=sys.stderr)
        print(json.dumps({"passed": 0, "failed": 1, "known_wrong_rejected": 0}))
        return 1
    passed = failed = rejected = 0
    for case in document["cases"]:
        wrong_rejected = False
        try:
            kind = case.get("kind", "request")
            if kind == "request":
                problems, wrong_rejected = check_request_case(case)
            elif kind == "redirect":
                problems = check_redirect_case(case)
            elif kind == "size_limit":
                problems = check_size_case(case)
            else:
                problems = [f"unknown case kind {kind}"]
        except Exception as error:  # a case that cannot run is a failed case, never a skipped one
            problems = [f"the case could not run: {type(error).__name__}: {error}"]
        if problems:
            failed += 1
            print(f"FAIL {case.get('name')}: {'; '.join(problems)}", file=sys.stderr)
        else:
            passed += 1
            rejected += 1 if wrong_rejected else 0
    for problem in coverage_problems(document["cases"]):
        failed += 1
        print(f"FAIL coverage: {problem}", file=sys.stderr)
    print(json.dumps({"passed": passed, "failed": failed, "known_wrong_rejected": rejected}))
    return 0 if failed == 0 and passed > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
