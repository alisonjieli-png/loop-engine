# Messy dataset to Schema.org-aligned data product

Ingest a messy organizations dataset, profile it, propose a
Schema.org-aligned semantic model, clean and transform the data,
validate the result, and generate an evidence-backed data-quality
report.

Run:

```bash
python3 examples/21_schema_org_data_standardization/run.py
```

The default fixture is deliberately messy: duplicate entities, mixed
row grains, malformed addresses, several date formats, unknown
sentinel strings, inconsistent country codes, phones with extensions,
impossible coordinates, and nulls represented as N/A, -, unknown,
empty strings, and zero.

The example:

- profiles every column with evidence;
- infers the row grain;
- proposes typed cleaning operations with confidence and risk;
- applies reversible transformations with a transformation ledger;
- emits Schema.org-aligned JSON-LD;
- validates with SHACL shapes;
- measures before-and-after data quality;
- reports fixed, unresolved, and review-required issues.

No network, no external service, no model calls.
