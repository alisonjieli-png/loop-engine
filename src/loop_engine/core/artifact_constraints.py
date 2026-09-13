"""Check what an artifact MEANS, not merely that it parses.

Artifact verification today is three conjuncts: the file exists, its byte count
clears a threshold the framework pins to literally 1, and a format signature
parses.  Measured 2026-09-05 against the live validator: a schedule whose only
task ends four days before it starts, whose declared duration matches neither
endpoint, and which lists itself as its own dependency returns
``(True, "json_parse", "")`` -- fully verified.  So does the single byte ``0``,
and so does ``[]``.  For a spreadsheet or a CSV the check degrades to "is
nonempty".

That floor is fine for "did the model produce a file" and useless for "is the
plan coherent".  This module supplies the missing conjunct.

Why a certificate check rather than the metamorphic oracle in
``differential_verification``: schedule validity is a UNARY DECIDABLE PREDICATE
over a single output.  Building a schedule is NP-hard in general (resource
constrained project scheduling); checking one is near-linear.  Metamorphic
relations exist to verify functions whose correct output nobody can state --
that is the harder case, and reaching for it here would be the harder path, not
the smaller one.

The checks are ENGINE-OWNED and referenced by name.  A manifest may say
``constraint: "schedule/v1"``; it may never supply the predicate.  That is the
same principle as ``_refuse_pre_authored_artifacts``: a model that can define
its own pass criterion has not been checked, it has been asked to mark its own
paper -- which is exactly the failure measured on the ISO-8601 run, where the
model wrote correct code, wrote incorrect expected constants, and then condemned
the correct code.
"""
from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass(frozen=True)
class ConstraintResult:
    """Outcome of one engine-owned constraint check."""

    check_id: str
    satisfied: bool
    violations: tuple[str, ...] = ()
    checked: int = 0
    detail: str = ""

    def to_dict(self) -> dict:
        return {
            "record_type": "artifact_constraint_result/v1",
            "check_id": self.check_id,
            "satisfied": self.satisfied,
            "violations": list(self.violations),
            "checked": self.checked,
            "detail": self.detail,
        }


def _as_json(content: bytes):
    try:
        return json.loads(content.decode("utf-8")), ""
    except (UnicodeDecodeError, ValueError) as exc:
        return None, f"not readable JSON: {type(exc).__name__}"


def _schedule_rows(document):
    """Accept the shapes a model actually emits for a schedule."""
    if isinstance(document, dict):
        for key in ("tasks", "schedule", "items", "activities"):
            if isinstance(document.get(key), list):
                return document[key], ""
        # A mapping of id -> {start, end} is equally common.
        if document and all(isinstance(v, dict) for v in document.values()):
            return ([{"id": k, **v} for k, v in document.items()], "")
        return None, "no task collection found in object"
    if isinstance(document, list):
        return document, ""
    return None, "schedule must be an object or a list"


def check_schedule(content: bytes) -> ConstraintResult:
    """Every task ends after it starts, respects its dependencies, and no cycle.

    Deliberately tolerant about SHAPE and strict about MEANING: a model names
    fields differently every run, and refusing an artifact for calling a field
    ``finish`` instead of ``end`` would reject correct plans.  What it will not
    tolerate is a plan that cannot be executed.
    """
    check_id = "schedule/v1"
    document, error = _as_json(content)
    if error:
        return ConstraintResult(check_id, False, (error,), 0)
    rows, error = _schedule_rows(document)
    if error:
        return ConstraintResult(check_id, False, (error,), 0)
    if not rows:
        return ConstraintResult(
            check_id, False, ("schedule contains no tasks",), 0,
            "an empty plan is not a satisfied plan")

    violations: list[str] = []
    starts: dict = {}
    ends: dict = {}
    dependencies: dict = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            violations.append(f"task #{index} is not an object")
            continue
        identity = str(row.get("id") or row.get("name") or f"#{index}")
        if identity in starts:
            violations.append(f"duplicate task id {identity!r}")
        start = row.get("start", row.get("start_day", row.get("begin")))
        end = row.get("end", row.get("finish", row.get("end_day")))
        duration = row.get("duration", row.get("days"))
        starts[identity] = start
        ends[identity] = end
        depends = row.get("depends_on", row.get("deps", row.get("predecessors")))
        dependencies[identity] = list(depends) if isinstance(depends, list) else []
        if isinstance(start, (int, float)) and isinstance(end, (int, float)):
            if end < start:
                violations.append(
                    f"{identity}: ends ({end}) before it starts ({start})")
            if isinstance(duration, (int, float)) and end - start != duration:
                violations.append(
                    f"{identity}: end - start is {end - start} but duration "
                    f"is {duration}")
        if isinstance(start, (int, float)) and start < 0:
            violations.append(f"{identity}: negative start {start}")

    for identity, depends in dependencies.items():
        for other in depends:
            other = str(other)
            if other == identity:
                violations.append(f"{identity}: depends on itself")
                continue
            if other not in starts:
                violations.append(
                    f"{identity}: depends on unknown task {other!r}")
                continue
            if (isinstance(starts.get(identity), (int, float))
                    and isinstance(ends.get(other), (int, float))
                    and starts[identity] < ends[other]):
                violations.append(
                    f"{identity}: starts at {starts[identity]} before its "
                    f"dependency {other} ends at {ends[other]}")

    # Cycle detection over the declared graph, independent of the dates.
    colour: dict = {}

    def descend(node: str) -> bool:
        colour[node] = "open"
        for peer in dependencies.get(node, ()):  # noqa: B007
            peer = str(peer)
            if peer not in dependencies:
                continue
            if colour.get(peer) == "open":
                return True
            if colour.get(peer) is None and descend(peer):
                return True
        colour[node] = "closed"
        return False

    for identity in list(dependencies):
        if colour.get(identity) is None and descend(identity):
            violations.append(f"dependency cycle reaches {identity!r}")
            break

    unique = tuple(dict.fromkeys(violations))
    return ConstraintResult(
        check_id, not unique, unique, len(rows),
        "" if not unique else f"{len(unique)} constraint violation(s)")


def check_nonempty_json_collection(content: bytes) -> ConstraintResult:
    """Reject the degenerate documents the format check calls valid."""
    check_id = "json_collection/v1"
    document, error = _as_json(content)
    if error:
        return ConstraintResult(check_id, False, (error,), 0)
    if isinstance(document, list):
        count = len(document)
    elif isinstance(document, dict):
        count = len(document)
    else:
        return ConstraintResult(
            check_id, False,
            (f"expected an object or list, got {type(document).__name__}",), 0)
    if count == 0:
        return ConstraintResult(check_id, False, ("collection is empty",), 0)
    return ConstraintResult(check_id, True, (), count)


#: The closed set a manifest may name.  A model references a check; it never
#: supplies one.  Adding a check is a code change with a test, by design.
CONSTRAINT_CHECKS = {
    "schedule/v1": check_schedule,
    "json_collection/v1": check_nonempty_json_collection,
}

#: Which media types each check can actually read.  Without this a check can be
#: named on an artifact it cannot parse, and the result is a guaranteed
#: violation that looks like a real finding: measured 2026-09-05, a model
#: declared "schedule/v1" on its gantt.html and the JSON reader reported
#: "not readable JSON" as a constraint violation, which -- because
#: constraint_satisfied is a conjunct of `verified` -- would fail a correct
#: artifact.  A check applied to the wrong type is a category error and must be
#: refused where it is DECLARED, not reported as a finding where it is run.
CHECK_MEDIA_TYPES = {
    "schedule/v1": ("application/json",),
    "json_collection/v1": ("application/json",),
}


def check_accepts_media_type(check_id: str, media_type: str) -> bool:
    """True when this check can read that media type."""
    allowed = CHECK_MEDIA_TYPES.get(str(check_id))
    if allowed is None:
        return False
    return str(media_type).split(";")[0].strip().lower() in allowed


def checks_for_media_type(media_type: str) -> tuple[str, ...]:
    """The checks that could apply to an artifact of this type."""
    return tuple(sorted(
        name for name in CONSTRAINT_CHECKS
        if check_accepts_media_type(name, media_type)))


def available_checks() -> tuple[str, ...]:
    return tuple(sorted(CONSTRAINT_CHECKS))


def verify_constraint(check_id: str, content: bytes) -> ConstraintResult:
    """Run one named engine-owned check over artifact bytes."""
    check = CONSTRAINT_CHECKS.get(str(check_id))
    if check is None:
        return ConstraintResult(
            str(check_id), False,
            (f"unknown constraint check; available: "
             f"{list(available_checks())}",), 0)
    try:
        return check(content)
    except Exception as exc:                             # noqa: BLE001
        # A check that raises must fail closed, never pass by accident.
        return ConstraintResult(
            str(check_id), False,
            (f"check raised {type(exc).__name__}",), 0)


def self_test() -> dict:
    """Offline proof that meaning is checked, not just syntax."""
    results: list[dict] = []

    def check(name, ok, detail=""):
        results.append({"name": name, "passed": bool(ok), "detail": detail})

    good = json.dumps({"tasks": [
        {"id": "a", "start": 0, "end": 2, "duration": 2, "depends_on": []},
        {"id": "b", "start": 2, "end": 7, "duration": 5, "depends_on": ["a"]},
        {"id": "c", "start": 2, "end": 3, "duration": 1, "depends_on": ["a"]},
        {"id": "d", "start": 7, "end": 9, "duration": 2,
         "depends_on": ["b", "c"]}]}).encode()
    result = verify_constraint("schedule/v1", good)
    check("a_valid_diamond_schedule_passes", result.satisfied and result.checked == 4,
          str(result.violations))

    # The exact document the live format check called verified.
    inverted = json.dumps({"tasks": [
        {"id": "a", "start": 5, "end": 1, "duration": 99,
         "depends_on": ["a"]}]}).encode()
    result = verify_constraint("schedule/v1", inverted)
    joined = " ".join(result.violations)
    check("ends_before_it_starts_is_caught",
          not result.satisfied and "ends" in joined, joined)
    check("duration_contradiction_is_caught", "duration" in joined, joined)
    check("self_dependency_is_caught", "itself" in joined, joined)

    precedence = json.dumps({"tasks": [
        {"id": "a", "start": 0, "end": 5, "duration": 5, "depends_on": []},
        {"id": "b", "start": 2, "end": 4, "duration": 2,
         "depends_on": ["a"]}]}).encode()
    result = verify_constraint("schedule/v1", precedence)
    check("starting_before_a_dependency_finishes_is_caught",
          not result.satisfied
          and any("before its dependency" in v for v in result.violations),
          str(result.violations))

    cycle = json.dumps({"tasks": [
        {"id": "a", "start": 0, "end": 1, "duration": 1, "depends_on": ["b"]},
        {"id": "b", "start": 0, "end": 1, "duration": 1,
         "depends_on": ["a"]}]}).encode()
    result = verify_constraint("schedule/v1", cycle)
    check("a_dependency_cycle_is_caught",
          not result.satisfied
          and any("cycle" in v for v in result.violations),
          str(result.violations))

    unknown = json.dumps([{"id": "a", "start": 0, "end": 1, "duration": 1,
                           "depends_on": ["ghost"]}]).encode()
    result = verify_constraint("schedule/v1", unknown)
    check("an_unknown_dependency_is_caught",
          not result.satisfied
          and any("unknown task" in v for v in result.violations),
          str(result.violations))

    mapping = json.dumps({"a": {"start": 0, "end": 3},
                          "b": {"start": 3, "end": 4}}).encode()
    check("an_id_to_window_mapping_is_accepted",
          verify_constraint("schedule/v1", mapping).satisfied)

    check("the_degenerate_documents_are_rejected",
          not verify_constraint("schedule/v1", b"[]").satisfied
          and not verify_constraint("json_collection/v1", b"[]").satisfied
          and not verify_constraint("json_collection/v1", b"0").satisfied)

    check("unparseable_bytes_fail_closed",
          not verify_constraint("schedule/v1", b"\xff\xfe not json").satisfied)
    check("an_unknown_check_id_fails_closed",
          not verify_constraint("no_such_check", good).satisfied)
    check("a_check_declares_the_media_types_it_reads",
          check_accepts_media_type("schedule/v1", "application/json")
          and not check_accepts_media_type("schedule/v1", "text/html"))
    check("media_type_parameters_are_ignored",
          check_accepts_media_type("json_collection/v1",
                                   "application/json; charset=utf-8"))
    check("an_unknown_check_accepts_nothing",
          not check_accepts_media_type("no_such_check", "application/json"))
    check("checks_can_be_listed_for_a_type",
          checks_for_media_type("application/json")
          == ("json_collection/v1", "schedule/v1")
          and checks_for_media_type("text/html") == ())
    check("the_check_set_is_closed_and_named",
          available_checks() == ("json_collection/v1", "schedule/v1"),
          str(available_checks()))
    check("result_serializes",
          verify_constraint("schedule/v1", good).to_dict()["record_type"]
          == "artifact_constraint_result/v1")

    passed = sum(1 for r in results if r["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
