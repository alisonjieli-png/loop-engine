---
name: audit-measurement-units
description: Check measurement units and conversions before comparing or aggregating numeric data. Use when sources mix units or a report changes a value's unit.
---

# Audit measurement units

## When to use

Use this for a numeric field whose sources, target report, or transformation may use different units. Treat an unstated unit as unknown, not as the most common unit in the sample.

## Inputs

- Source fields with their stated units, meanings, and sample values.
- The target unit and the approved conversion reference, including its version or effective period when rates vary.
- The calculation to be checked and any declared rounding rule.

## Procedure

1. List each source field's physical quantity and unit. Separate a stored value from a display label that may be wrong.
2. Check dimensional compatibility and whether the requested operation makes sense for the quantity. A length cannot be added to a mass. A temperature scale with an offset needs its complete conversion rule, not a multiplier alone; converting readings does not make them additive.
3. For each compatible source unit, record the conversion rule and its provenance. Convert individual values to the target unit before a total or comparison is calculated.
4. Recalculate a small representative sample by hand. Include one value from every source unit and one boundary value such as zero.
5. Compare the recomputed result with the report and show any unresolved unit or conversion choice.

## Completion check

Return a table of source field, source unit, target unit, conversion reference, sample input, converted value, and status. Every value included in the reported calculation must have a compatible, known conversion. Report the calculation's resulting unit.

## Stop conditions

Stop before reporting a combined number if a unit, conversion rule, or effective period is missing, or if the quantities are incompatible. Request the missing definition and identify the affected rows. Do not change source data.
