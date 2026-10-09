# Requirements traceability matrix and coverage gaps

Build a matrix linking requirements to design elements and tests, give each requirement a test status, and list requirements without design, tests or a pass, and links to nothing.

## What it does

Design elements declare the requirements they satisfy and tests the requirements they verify. The helper inverts those links into one row per requirement with its design elements, tests and a status: passed, failed, not_run or untested. Gaps list requirements without design, without tests, with a failing test, must requirements without a pass, and elements or tests that link to nothing. Coverage shares are computed over all requirements.

## Run it

As a library:

```python
from requirements_traceability import run
result = run(payload)  # payload: a dict shaped like the input schema
```

From a shell, with a JSON input document on standard input:

```bash
python3 requirements_traceability.py < input.json
```

The `input` object of `examples/known_good.json` is a working input. Exit status 0 prints the result; exit status 2 prints `{"refused": true, "reason": ..., "detail": ...}`.

## Input

- `requirements` (array of object, required): requirements with an id and an optional priority (must, should, could)
- `design_elements` (array of object): design elements and the requirement ids each satisfies
- `tests` (array of object, required): tests, the requirement ids each verifies and the latest result (pass, fail, not_run)

## Output

- `matrix` (array of object, required): one row per requirement in input order
- `gaps` (object, required): lists of ids for each kind of gap
- `coverage` (object, required): counts and shares of requirements with design, tests and a pass

## Refusals

- `input_invalid`: the input does not match the input schema
- `input_not_json`: standard input is not a JSON document
- `duplicate_id`: an id is used twice across requirements, design elements and tests
- `unknown_requirement`: a design element or test links to a requirement that is not listed

## Files

| File | Role |
| --- | --- |
| `README.md` | other |
| `requirements_traceability.py` | executable_tool |
| `PROCEDURE.md` | skill_reference |
| `TOOLS.md` | other |
| `ONET-ATTRIBUTION.md` | other |
| `examples/known_good.json` | other |
| `examples/known_wrong.json` | other |
| `kit_schema.py` | shared JSON Schema subset validator and command line runner |
| `test_package.py` | shared package tests |

## O*NET basis

O*NET data: the detailed work activities below link to 36 occupations through task statements. The kit serves the information part of these activities; choosing them is inference (see the DWA ranking rule in ONET-ATTRIBUTION.md).

| DWA | Title | Occupations | Rank |
| --- | --- | --- | --- |
| `4.A.4.a.2.h.7` | Collaborate with others to determine design specifications or details. | 16 | 51 |
| `4.A.2.a.4.e.5` | Analyze project data to determine specifications or requirements. | 10 | 150 |
| `4.A.2.a.4.e.3` | Evaluate designs or specifications to ensure quality. | 14 | 152 |

Occupations with the most of these activities: Computer Systems Analysts (`15-1211.00`); Telecommunications Engineering Specialists (`15-1241.01`); Software Developers (`15-1252.00`); Industrial Engineers (`17-2112.00`); Search Marketing Strategists (`13-1161.01`); Computer and Information Research Scientists (`15-1221.00`).

Example O*NET task statements linked to these activities:

- "Collaborate with system architects, software architects, design analysts, and others to understand business or industry requirements." (Database Architects, task `16113`)
- "Solicit, obtain, and integrate feedback from design and technical staff into original game design." (Video Game Designers, task `16201`)
- "Review and critique proposals, plans, or designs related to water or wastewater treatment systems." (Water/Wastewater Engineers, task `16325`)
- "Study and analyze information about alternative courses of action to determine which plan will offer the best outcomes." (Operations Research Analysts, task `7383`)

## Limits

A link is trusted as declared; the helper cannot tell whether a test really verifies the requirement. Status uses the latest result per test only. When no design elements are given, the without_design gap is left empty and design_checked is false.

This kit is a candidate component. Generating it did not approve or qualify it.
