# Resolution times of city service requests

Measure how long a city takes to close 311 service requests, per category and overall: requests, closed, still open, closed before opened, the median and 90th percentile hours to close and the share closed within a target, from ISO or US style timestamps.

## What it does

Each row is one request with its category, opened time and closed time (null while open). Per category and overall the function counts requests, closed and still open requests, and requests closed before they were opened (a data error, left out of the times and counted), then gives the median and the nearest-rank 90th percentile of hours to close and the share closed within the target (72 hours unless the input names another). It reads ISO 8601 timestamps (a date, or a date and time with optional seconds, fraction and offset; Z is UTC) and US style MM/DD/YYYY hh:mm[:ss] with an optional AM or PM; an offset is converted to UTC.

## Run it

As a library:

```python
from service_request_resolution_times import run
result = run(payload)  # payload: a dict shaped like the input schema
```

From a shell, with a JSON input document on standard input:

```bash
python3 service_request_resolution_times.py < input.json
```

The `input` object of `examples/known_good.json` is a working input. Exit status 0 prints the result; exit status 2 prints `{"refused": true, "reason": ..., "detail": ...}`.

## Input

- `rows` (array of object, required): one service request: its id, category, opened time and closed time or null
- `target_hours` (number): hours within which a request counts as closed on time (default 72)

## Output

- `target_hours` (number, required)
- `categories` (array of object, required): one summary per category, in category order
- `overall` (object, required)

## Refusals

- `input_invalid`: the input does not match the input schema
- `input_not_json`: standard input is not a JSON document
- `timestamp_unreadable`: a timestamp is neither ISO 8601 nor MM/DD/YYYY hh:mm:ss AM/PM
- `duplicate_id`: two requests share an id

## Checks

`examples/known_good.json` and the 4 cases of `examples/known_answers.json` hold inputs with answers worked out by hand; `examples/known_wrong.json` holds an input the function refuses. `test_package.py` runs the known-good and known-wrong examples through the function and the command line, and every known answer through the function.

## Files

| File | Role |
| --- | --- |
| `README.md` | other |
| `service_request_resolution_times.py` | executable_tool |
| `examples/known_good.json` | other |
| `examples/known_wrong.json` | other |
| `examples/known_answers.json` | other |
| `kit_schema.py` | shared JSON Schema subset validator and command line runner |
| `test_package.py` | shared package tests |

## Source and SDG basis

The October 6, 2026 inventory of the owner's Kaggle download holds 311 request tables from several cities in this shape (an id, a request type, created and closed timestamps). Their licences are not established, so no row of them is copied; the examples are synthetic.

Dataset shape: municipal 311 service request tables with opened and closed timestamps.

Proposed goals 11, 16; targets 11.6, 16.6. Resolution time informs how responsive city services are (target 16.6) for requests about waste and the urban environment (target 11.6); it is not indicator 16.6.2, which is a survey of satisfaction with public services. The association is a proposal for reviewers, not a grant.

## Limits

Timestamps without an offset are taken as written, so a table mixing local and UTC times needs one convention first; daylight saving changes are not applied. Requests closed before they were opened are counted and left out. Durations count calendar hours, not business hours. Resolution speed is not satisfaction: indicator 16.6.2 is a survey of people's experience.

This item is a candidate component. Generating it did not approve or qualify it.
