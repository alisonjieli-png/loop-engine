# Deaths and disappearances during migration by year and region

Total the people who died or went missing in the process of migration from incident records with dead and missing counts, per year and region, per year and overall, with unreported counts kept visible: the count behind SDG indicator 10.7.3.

## What it does

Each row is one incident with its id, year, region, number of dead and number of missing. A null count adds zero and is counted as unreported, so a total never hides a gap. Per (year, region), per year and in total, the function gives incidents, dead, missing, dead and missing together, and the incidents whose dead or missing count was not reported. Years sort as numbers and regions by name.

## Run it

As a library:

```python
from migration_deaths_and_missing import run
result = run(payload)  # payload: a dict shaped like the input schema
```

From a shell, with a JSON input document on standard input:

```bash
python3 migration_deaths_and_missing.py < input.json
```

The `input` object of `examples/known_good.json` is a working input. Exit status 0 prints the result; exit status 2 prints `{"refused": true, "reason": ..., "detail": ...}`.

## Input

- `rows` (array of object, required): one incident: its id, year, region and counts of dead and missing people

## Output

- `by_year_region` (array of object, required): totals per year and region, by year then region
- `by_year` (array of object, required): totals per year
- `total` (object, required)

## Refusals

- `input_invalid`: the input does not match the input schema
- `input_not_json`: standard input is not a JSON document
- `negative_count`: a dead or missing count is negative
- `duplicate_incident`: two rows share an incident id

## Checks

`examples/known_good.json` and the 3 cases of `examples/known_answers.json` hold inputs with answers worked out by hand; `examples/known_wrong.json` holds an input the function refuses. `test_package.py` runs the known-good and known-wrong examples through the function and the command line, and every known answer through the function.

## Files

| File | Role |
| --- | --- |
| `README.md` | other |
| `migration_deaths_and_missing.py` | executable_tool |
| `examples/known_good.json` | other |
| `examples/known_wrong.json` | other |
| `examples/known_answers.json` | other |
| `kit_schema.py` | shared JSON Schema subset validator and command line runner |
| `test_package.py` | shared package tests |

## Source and SDG basis

The October 6, 2026 inventory of the owner's Kaggle download holds a copy of the IOM Missing Migrants Project's incident table in this shape. Its licence is not established, so no row of it is copied; the examples are synthetic.

Dataset shape: migration incident records with dead and missing counts, as the IOM Missing Migrants Project publishes.

Proposed goals 10; targets 10.7; indicators 10.7.3. Indicator 10.7.3 counts people who died or disappeared in the process of migration towards an international destination. The association is a proposal for reviewers, not a grant.

## Limits

The totals are as complete as the incident records: incidents never recorded, and bodies never found or identified, are absent. An unreported count adds zero and is counted separately rather than estimated. Regions and years are taken as given; the function does not assign incidents to routes.

This item is a candidate component. Generating it did not approve or qualify it.
