"""Section enrollment allocator: seat students in sections by priority, capacity, prerequisites and time clashes.

Requests are processed by the student's priority group (1 first), then registration time, then input order. Each
request takes the first choice that has a free seat, whose course prerequisites the student has completed, and
whose time block does not clash with a section the student already holds. When every eligible choice is full the
student joins the waitlist of the first eligible full choice. A pure function of its JSON input; the command line
reads standard input and writes standard output.
"""
from __future__ import annotations

import datetime

from kit_schema import KitRefusal, check, parse_date_time, run_cli

REFUSALS = {
    "input_invalid": "the input does not match the input schema",
    "input_not_json": "standard input is not a JSON document",
    "duplicate_id": "two sections, students or requests share an id",
    "unknown_section": "a request names a section that is not listed",
    "unknown_student": "a request names a student who is not listed",
    "invalid_date_time": "a registration time is not an ISO 8601 date and time (a time without an offset is read as UTC)",
}
INPUT_SCHEMA = {
    "type": "object", "required": ["sections", "students", "requests"], "additionalProperties": False,
    "properties": {
        "sections": {"type": "array", "minItems": 1, "maxItems": 2000, "description":
                     "sections with a course, a seat capacity, an optional time block and course prerequisites",
                     "items": {"type": "object", "required": ["id", "course", "capacity"], "additionalProperties": False,
                               "properties": {"id": {"type": "string", "minLength": 1},
                                              "course": {"type": "string", "minLength": 1},
                                              "capacity": {"type": "integer", "minimum": 0, "maximum": 5000},
                                              "time_block": {"type": "string"},
                                              "prerequisites": {"type": "array", "items": {"type": "string"}}}}},
        "students": {"type": "array", "minItems": 1, "maxItems": 50000, "description":
                     "students with a priority group, a registration time and completed courses",
                     "items": {"type": "object", "required": ["id", "priority_group", "registered_at"],
                               "additionalProperties": False,
                               "properties": {"id": {"type": "string", "minLength": 1},
                                              "priority_group": {"type": "integer", "minimum": 1, "maximum": 20},
                                              "registered_at": {"type": "string"},
                                              "completed": {"type": "array", "items": {"type": "string"}}}}},
        "requests": {"type": "array", "minItems": 1, "maxItems": 100000, "description":
                     "one seat request per course: the student and section choices in preference order",
                     "items": {"type": "object", "required": ["id", "student", "choices"], "additionalProperties": False,
                               "properties": {"id": {"type": "string", "minLength": 1},
                                              "student": {"type": "string"},
                                              "choices": {"type": "array", "minItems": 1, "maxItems": 10,
                                                          "items": {"type": "string"}}}}},
    },
}
OUTPUT_SCHEMA = {
    "type": "object", "required": ["enrollments", "waitlists", "not_enrolled", "section_fill"],
    "properties": {
        "enrollments": {"type": "array", "description": "seated requests in processing order, with the choice rank",
                        "items": {"type": "object", "required": ["request", "student", "section", "choice_rank"],
                                  "properties": {"request": {"type": "string"}, "student": {"type": "string"},
                                                 "section": {"type": "string"},
                                                 "choice_rank": {"type": "integer"}}}},
        "waitlists": {"type": "object", "description": "section id to waitlisted student ids in order"},
        "not_enrolled": {"type": "array", "description": "requests without a seat, with the reason",
                         "items": {"type": "object", "required": ["request", "student", "reason"],
                                   "properties": {"request": {"type": "string"}, "student": {"type": "string"},
                                                  "reason": {"enum": ["waitlisted", "missing_prerequisite",
                                                                      "time_clash", "already_in_course"]}}}},
        "section_fill": {"type": "array", "description": "capacity, enrolled and waitlisted per section",
                         "items": {"type": "object", "required": ["section", "capacity", "enrolled", "waitlisted"],
                                   "properties": {"section": {"type": "string"}, "capacity": {"type": "integer"},
                                                  "enrolled": {"type": "integer"},
                                                  "waitlisted": {"type": "integer"}}}},
    },
}


def choice_problem(section: dict, student: dict, held: list, sections: dict) -> str:
    """Why ``student`` cannot take ``section`` apart from seats, or an empty string."""
    if any(sections[other]["course"] == section["course"] for other in held):
        return "already_in_course"
    if any(course not in student.get("completed", []) for course in section.get("prerequisites", [])):
        return "missing_prerequisite"
    block = section.get("time_block")
    if block and any(sections[other].get("time_block") == block for other in held):
        return "time_clash"
    return ""


def run(payload: dict) -> dict:
    check(payload, INPUT_SCHEMA)
    for name in ("sections", "students", "requests"):
        ids = [row["id"] for row in payload[name]]
        if len(set(ids)) != len(ids):
            raise KitRefusal("duplicate_id", f"repeated id in {name}")
    sections = {row["id"]: row for row in payload["sections"]}
    students = {row["id"]: row for row in payload["students"]}
    order = []
    for index, request in enumerate(payload["requests"]):
        if request["student"] not in students:
            raise KitRefusal("unknown_student", request["student"])
        unknown = [choice for choice in request["choices"] if choice not in sections]
        if unknown:
            raise KitRefusal("unknown_section", unknown[0])
        student = students[request["student"]]
        moment = parse_date_time(student["registered_at"])
        if moment is None:
            raise KitRefusal("invalid_date_time", student["id"])
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=datetime.timezone.utc)
        order.append(((student["priority_group"], moment.timestamp(), index), request))
    order.sort(key=lambda row: row[0])
    seats = {section_id: section["capacity"] for section_id, section in sections.items()}
    held = {student_id: [] for student_id in students}
    waitlists = {section_id: [] for section_id in sections}
    enrollments, not_enrolled = [], []
    for _key, request in order:
        student = students[request["student"]]
        problems, full = [], None
        placed = False
        for rank, section_id in enumerate(request["choices"], 1):
            problem = choice_problem(sections[section_id], student, held[student["id"]], sections)
            if problem:
                problems.append(problem)
                continue
            if seats[section_id] > 0:
                seats[section_id] -= 1
                held[student["id"]].append(section_id)
                enrollments.append({"request": request["id"], "student": student["id"], "section": section_id,
                                    "choice_rank": rank})
                placed = True
                break
            if full is None:
                full = section_id
        if placed:
            continue
        if full is not None:
            waitlists[full].append(student["id"])
            not_enrolled.append({"request": request["id"], "student": student["id"], "reason": "waitlisted"})
        else:
            not_enrolled.append({"request": request["id"], "student": student["id"], "reason": problems[0]})
    fill = [{"section": section_id, "capacity": section["capacity"],
             "enrolled": section["capacity"] - seats[section_id], "waitlisted": len(waitlists[section_id])}
            for section_id, section in sections.items()]
    return {"enrollments": enrollments, "waitlists": {key: value for key, value in waitlists.items() if value},
            "not_enrolled": not_enrolled, "section_fill": fill}


def main(argv=None, stdin=None, stdout=None) -> int:
    return run_cli(run, argv, stdin, stdout)


if __name__ == "__main__":
    raise SystemExit(main())
