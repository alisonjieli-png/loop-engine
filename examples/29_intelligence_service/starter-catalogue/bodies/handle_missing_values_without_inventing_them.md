# Handle missing values without inventing them

Keep the difference between a value that is zero, a value that is empty and a value nobody knows, all the way to the report.

## When to use it

Use it whenever you read data you did not produce: a form, a file, another service, a sensor, a model answer or an old table.

## Steps

1. Decide what missing means for each field, and whether the field can be missing at all.
2. Keep the distinct cases apart in your types: present with a value, present and empty, and absent. Do not map them onto one another.
3. Never use a normal value as a marker for absent. Zero, an empty text, a distant date and minus one are all real values somewhere.
4. When you fill a missing value, record that you filled it and with which rule, in a separate field.
5. Do not average, sum or compare a filled value as though it were observed, and say in the report how many values were filled.
6. Push the decision to the reader when the choice changes the answer. A total over rows with missing amounts needs a stated rule.
7. In a report, show the count of missing values beside the number, not instead of it.
8. Check the filling rule against a case where it is clearly wrong, and see what the report shows.

## Checks

- Absent, empty and zero are distinguishable at every step.
- No real value is used as a marker for absent.
- Every filled value is marked as filled, with its rule.
- Reports show the missing count beside the result.

## Known-wrong example

An import turns a missing price into zero, because the column is numeric. The monthly revenue report is correct in total but the average price for one category falls by half, and a pricing decision is made from it. Keeping absent apart from zero, and reporting eleven missing prices beside the average, would have stopped the decision.

## What to record

- The meaning of missing for each field.
- The filling rule used and how many values it filled.
- The numbers computed over filled values and the ones computed only over observed values.

## Source

- `src/loop_engine/core/model_gateway_accounting.py`: this repository keeps provider usage that was never reported as unknown rather than as zero, and separates real attempts from rows that describe work that did not happen.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision db18890.
