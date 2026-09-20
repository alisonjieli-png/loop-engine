# Detect malformed values by the dominant character pattern

Find the values in a column whose character pattern differs from the pattern that most values share. When no pattern dominates, say so and flag nothing.

## When to use it

Use it on columns that should follow one format: dates, postal codes, product codes, invoice numbers, identifiers.

## Steps

1. Trim each value and reduce it to a collapsed character pattern. An upper case letter becomes `A`, a lower case letter `a`, a digit `9` and a character outside ASCII `U`. Other characters stay. Repeats collapse, so `2026-09-18` becomes `9+-9+-9+`.
2. Count the patterns and take the most common one as the dominant pattern.
3. Compute its share of all values. When the share is below the dominant share threshold, report that there is no dominant pattern and flag nothing. The default threshold is 0.6. It must be above 0 and at most 1.
4. Otherwise flag every value whose pattern differs from the dominant pattern.
5. Give each flagged value a confidence: the dominant share minus the share of the pattern of that value.
6. Give each flagged value the reason `pattern_differs_from_dominant` with the dominant pattern.

## Checks

- In the column `2026-09-18`, `2026-09-19`, `2026-10-01`, `18/09/2026`, `2026-11-30`, the dominant pattern is `9+-9+-9+` with a share of 0.8. Only `18/09/2026` is flagged, with confidence 0.6.
- An empty column reports no dominant pattern.
- The collapsed pattern ignores how long each run is. `18-09-2026` has the same pattern as `2026-09-18` and is not flagged. Compare the exact pattern when run length matters.

## Known-wrong example

A checker always flags every value that differs from the most common pattern. In a free text column the most common pattern covers 5 percent of the values, so the checker flags the other 95 percent. The share threshold prevents this. Below the threshold the correct answer is that the column has no dominant pattern.

## What to record

- The total, the dominant pattern, its share and the threshold.
- Each flagged value with its position, its pattern, its confidence and its reason.
- The statement that there is no dominant pattern, when that is the result.

## Source

- `src/loop_engine/code_nodes/field_recovery.py`: `detect_malformed`.
- `src/loop_engine/code_nodes/text_conformance_operations.py`: `induce_pattern`.

Licence: MIT. Compiled from revision 381efec. The two modules depend only on each other and on the Python standard library.
