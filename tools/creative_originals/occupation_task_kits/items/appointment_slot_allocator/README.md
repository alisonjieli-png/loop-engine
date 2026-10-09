# Appointment slot allocator for providers and rooms

Place appointment requests into providers' free time by priority, service, date window, duration, buffer and preferred provider, and report what could not be placed and why.

## What it does

Requests are taken by priority, then earliest allowed date, then input order. Each one goes to the earliest start on a step grid that fits inside an availability block of a provider offering the service, with the buffer clear of that provider's bookings. The preferred provider is used when it has any fitting slot in the window. Existing bookings block time. The result lists bookings, unplaced requests with a reason, and booked against available minutes per provider.

## Run it

As a library:

```python
from appointment_slot_allocator import run
result = run(payload)  # payload: a dict shaped like the input schema
```

From a shell, with a JSON input document on standard input:

```bash
python3 appointment_slot_allocator.py < input.json
```

The `input` object of `examples/known_good.json` is a working input. Exit status 0 prints the result; exit status 2 prints `{"refused": true, "reason": ..., "detail": ...}`.

## Input

- `providers` (array of object, required): people or rooms with availability blocks (date, start, end) and the services they offer
- `requests` (array of object, required): appointments to place: duration, optional service, priority, date window, preferred provider
- `existing_bookings` (array of object): bookings already made; they block time like new ones
- `slot_step_minutes` (integer): grid for candidate start times (default 15)
- `buffer_minutes` (integer): gap kept free before and after each booking (default 0)

## Output

- `bookings` (array of object, required): one row per placed request, in placement order
- `unplaced` (array of object, required): requests that could not be placed, with the reason
- `utilization` (array of object, required): available and booked minutes per provider, existing bookings included

## Refusals

- `input_invalid`: the input does not match the input schema
- `input_not_json`: standard input is not a JSON document
- `duplicate_id`: two providers or two requests share an id
- `invalid_date_or_time`: a date is not a real calendar date or a time is not HH:MM
- `empty_availability_block`: an availability block ends at or before its start
- `overlapping_availability`: one provider has two availability blocks that overlap on the same date
- `unknown_provider`: a request or an existing booking names a provider that is not listed
- `reversed_window`: a request's latest_date is before its earliest_date

## Files

| File | Role |
| --- | --- |
| `README.md` | other |
| `appointment_slot_allocator.py` | executable_tool |
| `PROCEDURE.md` | skill_reference |
| `TOOLS.md` | other |
| `ONET-ATTRIBUTION.md` | other |
| `examples/known_good.json` | other |
| `examples/known_wrong.json` | other |
| `kit_schema.py` | shared JSON Schema subset validator and command line runner |
| `test_package.py` | shared package tests |

## O*NET basis

O*NET data: the detailed work activities below link to 41 occupations through task statements. The kit serves the information part of these activities; choosing them is inference (see the DWA ranking rule in ONET-ATTRIBUTION.md).

| DWA | Title | Occupations | Rank |
| --- | --- | --- | --- |
| `4.A.2.b.5.c.1` | Schedule appointments. | 21 | 37 |
| `4.A.2.b.5.c.2` | Schedule patient procedures or appointments. | 23 | 119 |

Occupations with the most of these activities: Dental Hygienists (`29-1292.00`); Surgical Technologists (`29-2055.00`); Medical Records Specialists (`29-2072.00`); Spa Managers (`11-9179.02`); Tax Preparers (`13-2082.00`); Social Science Research Assistants (`19-4061.00`).

Example O*NET task statements linked to these activities:

- "Schedule surgical procedures for patients." (Surgical Technologists, task `24037`)
- "Operate telephone switchboard to answer, screen, or forward calls, providing information, taking messages, or scheduling appointments." (Receptionists and Information Clerks, task `744`)
- "Schedule client appointments." (Hairdressers, Hairstylists, and Cosmetologists, task `638`)
- "Perform clerical duties, such as scheduling exams or special procedures, keeping records, or archiving computerized images." (Diagnostic Medical Sonographers, task `448`)

## Limits

Greedy first fit: a later high-value request can be blocked by an earlier lower-priority one in the same priority band, and no request is moved once placed. Times are local wall-clock times without time zones or daylight saving changes. A provider serves one appointment at a time. Patient or client consent, reminders and cancellations are out of scope.

This kit is a candidate component. Generating it did not approve or qualify it.
