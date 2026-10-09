# Section enrollment allocator with prerequisites and waitlists

Seat students in course sections by priority group and registration time, honouring capacity, prerequisites, one section per course and time-block clashes, with ordered waitlists.

## What it does

Requests are processed by priority group, then registration time, then input order. Each request takes its first choice with a seat that the student is eligible for; when every eligible choice is full the student joins the first eligible full section's waitlist. Reasons are recorded for missing prerequisites, time clashes and a second section of a course already held.

## Run it

As a library:

```python
from section_enrollment_allocator import run
result = run(payload)  # payload: a dict shaped like the input schema
```

From a shell, with a JSON input document on standard input:

```bash
python3 section_enrollment_allocator.py < input.json
```

The `input` object of `examples/known_good.json` is a working input. Exit status 0 prints the result; exit status 2 prints `{"refused": true, "reason": ..., "detail": ...}`.

## Input

- `sections` (array of object, required): sections with a course, a seat capacity, an optional time block and course prerequisites
- `students` (array of object, required): students with a priority group, a registration time and completed courses
- `requests` (array of object, required): one seat request per course: the student and section choices in preference order

## Output

- `enrollments` (array of object, required): seated requests in processing order, with the choice rank
- `waitlists` (object, required): section id to waitlisted student ids in order
- `not_enrolled` (array of object, required): requests without a seat, with the reason
- `section_fill` (array of object, required): capacity, enrolled and waitlisted per section

## Refusals

- `input_invalid`: the input does not match the input schema
- `input_not_json`: standard input is not a JSON document
- `duplicate_id`: two sections, students or requests share an id
- `unknown_section`: a request names a section that is not listed
- `unknown_student`: a request names a student who is not listed
- `invalid_date_time`: a registration time is not an ISO 8601 date and time (a time without an offset is read as UTC)

## Files

| File | Role |
| --- | --- |
| `README.md` | other |
| `section_enrollment_allocator.py` | executable_tool |
| `PROCEDURE.md` | skill_reference |
| `TOOLS.md` | other |
| `ONET-ATTRIBUTION.md` | other |
| `examples/known_good.json` | other |
| `examples/known_wrong.json` | other |
| `kit_schema.py` | shared JSON Schema subset validator and command line runner |
| `test_package.py` | shared package tests |

## O*NET basis

O*NET data: the detailed work activities below link to 55 occupations through task statements. The kit serves the information part of these activities; choosing them is inference (see the DWA ranking rule in ONET-ATTRIBUTION.md).

| DWA | Title | Occupations | Rank |
| --- | --- | --- | --- |
| `4.A.4.c.1.a.5` | Perform student enrollment or registration activities. | 37 | 50 |
| `4.A.3.b.6.h.12` | Maintain student records. | 53 | 13 |

Occupations with the most of these activities: Mathematical Science Teachers, Postsecondary (`25-1022.00`); Architecture Teachers, Postsecondary (`25-1031.00`); Engineering Teachers, Postsecondary (`25-1032.00`); Agricultural Sciences Teachers, Postsecondary (`25-1041.00`); Biological Science Teachers, Postsecondary (`25-1042.00`); Forestry and Conservation Science Teachers, Postsecondary (`25-1043.00`).

Example O*NET task statements linked to these activities:

- "Maintain student records, including special education reports, confidential records, records of services provided, and behavioral data." (School Psychologists, task `5455`)
- "Maintain accurate and complete student records as required by laws, district policies, or administrative regulations." (Special Education Teachers, Preschool, task `19093`)
- "Maintain accurate and complete student records as required by laws, district policies, or administrative regulations." (Special Education Teachers, Elementary School, task `22374`)
- "Maintain student attendance records, grades, and other required records." (Foreign Language and Literature Teachers, Postsecondary, task `6337`)

## Limits

Prerequisites are completed course ids only; grades, co-requisites and instructor permission are not modelled. A time block is a label; overlap between different labels is not detected. Waitlists are not promoted automatically when seats free up: rerun with updated capacity. A registration time without an offset is read as UTC.

This kit is a candidate component. Generating it did not approve or qualify it.
