# Event rates per 100,000 population

Turn counts of events into rates per 100,000 people (or another base), per group and period and pooled per period: the computation behind SDG indicators such as road traffic deaths (3.6.1), homicide victims (16.1.1), trafficking victims (16.2.2) and people affected by disasters (11.5.1).

## What it does

Each row holds a group (a city, a district, an age band), a period, a count of events and the population the count belongs to. The rate is count / population x per, with per 100,000 unless the input names another base; it stays exact until it is rounded to six decimals. Every period also gets its number of groups, total count, total population and pooled rate. Rows come back sorted by period, then group.

## Run it

As a library:

```python
from rate_per_100k import run
result = run(payload)  # payload: a dict shaped like the input schema
```

From a shell, with a JSON input document on standard input:

```bash
python3 rate_per_100k.py < input.json
```

The `input` object of `examples/known_good.json` is a working input. Exit status 0 prints the result; exit status 2 prints `{"refused": true, "reason": ..., "detail": ...}`.

## Input

- `rows` (array of object, required): one count of events for one group in one period, with its population
- `per` (number): the population base of the rate (default 100000)

## Output

- `per` (number, required)
- `rows` (array of object, required): each input row with its rate, by period then group
- `periods` (array of object, required): per period: groups, total count, total population, pooled rate

## Refusals

- `input_invalid`: the input does not match the input schema
- `input_not_json`: standard input is not a JSON document
- `population_not_positive`: a population is zero or negative
- `negative_count`: a count is negative
- `duplicate_group_period`: two rows name the same group and period

## Checks

`examples/known_good.json` and the 3 cases of `examples/known_answers.json` hold inputs with answers worked out by hand; `examples/known_wrong.json` holds an input the function refuses. `test_package.py` runs the known-good and known-wrong examples through the function and the command line, and every known answer through the function.

## Files

| File | Role |
| --- | --- |
| `README.md` | other |
| `rate_per_100k.py` | executable_tool |
| `examples/known_good.json` | other |
| `examples/known_wrong.json` | other |
| `examples/known_answers.json` | other |
| `kit_schema.py` | shared JSON Schema subset validator and command line runner |
| `test_package.py` | shared package tests |

## Source and SDG basis

The October 6, 2026 inventory of the owner's Kaggle download holds many incident tables of this shape (road collisions, shootings, overdose deaths, arrests, trafficking case records). Their licences are not established, so no row of them is copied; the examples are synthetic.

Dataset shape: incident counts with a population denominator: road deaths, homicides, overdose deaths, trafficking victims.

Proposed goals 3, 11, 16; targets 3.6, 11.5, 16.1, 16.2; indicators 3.6.1, 11.5.1, 16.1.1, 16.2.2. These indicators are counts per 100,000 population, and this function computes that step from counts and populations the caller supplies. The association is a proposal for reviewers, not a grant.

## Limits

The rate is crude: it is not age-standardized, and the population is taken as given for the whole period. The counts and population of a group have to describe the same area and time, which the function cannot check. Small populations give unstable rates and no interval is reported. Periods and groups sort as text.

This item is a candidate component. Generating it did not approve or qualify it.
