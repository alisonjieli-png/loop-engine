"""Requirements traceability: link requirements to design elements and tests, and find the gaps.

Builds the traceability matrix from the links that design elements (satisfies) and tests (verifies) declare. Each
requirement gets its design elements, its tests and a test status: passed when at least one linked test passed and
none failed, failed when any linked test failed, not_run when tests exist but none ran, untested when no test links
to it. Gaps are requirements without design, without tests or without a passing test, and design elements or tests
that link to nothing. A pure function of its JSON input; the command line reads standard input and writes standard
output.
"""
from __future__ import annotations

from kit_schema import KitRefusal, check, run_cli

REFUSALS = {
    "input_invalid": "the input does not match the input schema",
    "input_not_json": "standard input is not a JSON document",
    "duplicate_id": "an id is used twice across requirements, design elements and tests",
    "unknown_requirement": "a design element or test links to a requirement that is not listed",
}
_LINKS = {"type": "array", "items": {"type": "string"}, "maxItems": 500}
INPUT_SCHEMA = {
    "type": "object", "required": ["requirements", "tests"], "additionalProperties": False,
    "properties": {
        "requirements": {"type": "array", "minItems": 1, "maxItems": 20000, "description":
                         "requirements with an id and an optional priority (must, should, could)",
                         "items": {"type": "object", "required": ["id"], "additionalProperties": False,
                                   "properties": {"id": {"type": "string", "minLength": 1},
                                                  "text": {"type": "string"},
                                                  "priority": {"enum": ["must", "should", "could"]}}}},
        "design_elements": {"type": "array", "maxItems": 20000, "description":
                            "design elements and the requirement ids each satisfies",
                            "items": {"type": "object", "required": ["id", "satisfies"], "additionalProperties": False,
                                      "properties": {"id": {"type": "string", "minLength": 1},
                                                     "satisfies": _LINKS}}},
        "tests": {"type": "array", "maxItems": 50000, "description":
                  "tests, the requirement ids each verifies and the latest result (pass, fail, not_run)",
                  "items": {"type": "object", "required": ["id", "verifies"], "additionalProperties": False,
                            "properties": {"id": {"type": "string", "minLength": 1}, "verifies": _LINKS,
                                           "status": {"enum": ["pass", "fail", "not_run"]}}}},
    },
}
OUTPUT_SCHEMA = {
    "type": "object", "required": ["matrix", "gaps", "coverage"],
    "properties": {
        "matrix": {"type": "array", "description": "one row per requirement in input order",
                   "items": {"type": "object", "required": ["requirement", "design_elements", "tests", "test_status"],
                             "properties": {"requirement": {"type": "string"},
                                            "design_elements": {"type": "array", "items": {"type": "string"}},
                                            "tests": {"type": "array", "items": {"type": "string"}},
                                            "test_status": {"enum": ["passed", "failed", "not_run", "untested"]}}}},
        "gaps": {"type": "object", "description": "lists of ids for each kind of gap"},
        "coverage": {"type": "object", "description": "counts and shares of requirements with design, tests and a pass"},
    },
}


def test_status(statuses: list) -> str:
    if not statuses:
        return "untested"
    if "fail" in statuses:
        return "failed"
    if "pass" in statuses:
        return "passed"
    return "not_run"


def run(payload: dict) -> dict:
    check(payload, INPUT_SCHEMA)
    requirements = payload["requirements"]
    design, tests = payload.get("design_elements", []), payload["tests"]
    ids = [row["id"] for row in requirements + design + tests]
    if len(set(ids)) != len(ids):
        repeated = sorted({identity for identity in ids if ids.count(identity) > 1})
        raise KitRefusal("duplicate_id", ", ".join(repeated[:10]))
    known = {row["id"] for row in requirements}
    linked_design = {identity: [] for identity in known}
    linked_tests = {identity: [] for identity in known}
    for element in design:
        for identity in element["satisfies"]:
            if identity not in known:
                raise KitRefusal("unknown_requirement", f"{element['id']} satisfies {identity}")
            if element["id"] not in linked_design[identity]:
                linked_design[identity].append(element["id"])
    statuses = {identity: [] for identity in known}
    for test in tests:
        for identity in test["verifies"]:
            if identity not in known:
                raise KitRefusal("unknown_requirement", f"{test['id']} verifies {identity}")
            if test["id"] not in linked_tests[identity]:
                linked_tests[identity].append(test["id"])
                statuses[identity].append(test.get("status", "not_run"))
    matrix = []
    for row in requirements:
        identity = row["id"]
        matrix.append({"requirement": identity, "design_elements": linked_design[identity],
                       "tests": linked_tests[identity], "test_status": test_status(statuses[identity])})
    by_status = {row["requirement"]: row["test_status"] for row in matrix}
    must = [row["id"] for row in requirements if row.get("priority") == "must"]
    gaps = {
        "without_design": [row["id"] for row in requirements if not linked_design[row["id"]]] if design else [],
        "without_tests": [row["id"] for row in requirements if not linked_tests[row["id"]]],
        "failing": [row["id"] for row in requirements if by_status[row["id"]] == "failed"],
        "must_without_a_pass": [identity for identity in must if by_status[identity] != "passed"],
        "design_linked_to_nothing": [element["id"] for element in design if not element["satisfies"]],
        "tests_linked_to_nothing": [test["id"] for test in tests if not test["verifies"]],
    }
    count = len(requirements)
    with_design = sum(1 for row in matrix if row["design_elements"])
    with_tests = sum(1 for row in matrix if row["tests"])
    passed = sum(1 for row in matrix if row["test_status"] == "passed")
    coverage = {"requirements": count, "with_design": with_design, "with_tests": with_tests, "passed": passed,
                "design_share": round(with_design / count, 4), "test_share": round(with_tests / count, 4),
                "pass_share": round(passed / count, 4), "design_checked": bool(design)}
    return {"matrix": matrix, "gaps": gaps, "coverage": coverage}


def main(argv=None, stdin=None, stdout=None) -> int:
    return run_cli(run, argv, stdin, stdout)


if __name__ == "__main__":
    raise SystemExit(main())
