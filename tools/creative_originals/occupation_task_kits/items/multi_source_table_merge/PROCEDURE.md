# Procedure: Multi-source table merge with provenance and conflicts

Follow this procedure to do the activity with the helper `multi_source_table_merge.py`. The helper does the mechanical part. The agent gathers inputs, makes the decisions below and checks the result.

## Ask the user first

1. Which sources hold the data, and which one is trusted most for each field?
2. Which field or fields identify the same item across sources?
3. Are units, currencies and code lists the same in every source?
4. What difference between two numbers is acceptable?

## Steps

1. Profile each source with column_profile and check key formats match.
2. Write each source's mapping and unit multipliers.
3. Set priorities; use separate runs when field trust differs by field.
4. Run the helper; read conflicts and keys_in_one_source_only.
5. Resolve conflicts with the source owners or record the rule used.
6. Publish the merged table with its provenance columns.

## Decision points

### Which source wins

- system of record first: choose when one source is the official record
- most recent first: choose when sources are equal but updated at different times; order priorities by extract date
- per-field trust: choose when each source is best for different fields; run once per field group

Default when nothing settles it: system of record first

Evidence that settles it: data ownership and update frequency

### Numeric tolerance

- 0: choose when identifiers and money
- 0.01 to 0.05: choose when measurements with rounding

Default when nothing settles it: 0 for money, 0.01 for measurements

Evidence that settles it: the precision each source stores

## Quality checks

- Every mapped column exists in its source.
- Converted units are plausible (spot check three values by hand).
- Every merged value has a provenance entry.
- Conflicts were resolved or explained before publishing.

## Scenario variants

These are parameters of this one kit, not separate kits.

| Parameter | Values | Effect |
| --- | --- | --- |
| Speed | fast: key and few fields; thorough: all fields with tolerance tuned | same method |
| Tools | free: this helper, Python csv, SQLite; paid: ETL and data integration suites | same logic |
| Sources | two or many | priority order decides |

## Stop and ask, or hand to a person

- Fuzzy key matching: use duplicate_record_finder first.
- Writing back to the sources.
