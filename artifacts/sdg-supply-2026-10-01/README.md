# SDG and small-component supply, October 1, 2026

Kind: measured candidate supply record. Nothing here is approved, admitted,
served or published. The owner's request and its limits are in
[owner decisions](../../docs/architecture/OWNER-DECISIONS.md#small-components-and-wider-public-good-supply-october-1-2026).

## What was produced

Every package came from the existing deterministic supply lines
([`tools/build_library_supply.py`](../../tools/build_library_supply.py)),
with no model call. Each source passed the line's own licence decision
(allowlist only), git blob identity and generated tests before it was kept.
All packages are `candidate` records in the import store's `library.supply`
namespace.

| Round | Line | Sources | Candidates | Refused by name |
|---|---|---:|---:|---:|
| 1 | openapi_operations | 8 SDG APIs | 473 | 77 |
| 1 | json_schemas (API components) | same 8 | 524 | 531 |
| 1 | data_tables | 540 SDG tables | 540 | 0 |
| 1 | function_extracts | 18 libraries | 1,217 | 2,123 |
| 1 | json_schemas (curated, new mode) | 11 standards, 71 repositories | 97 | 5 |
| 2 | openapi_operations | 67 | 6,236 | 298 |
| 2 | json_schemas (API components) | same 67 | 6,293 | 3,901 |
| 2 | function_extracts | 11 libraries | 78 | 262 |
| 3 | openapi_operations | 107 | 7,994 | 1,083 |
| 3 | json_schemas (API components) | same 107 | 7,607 | 5,697 |
| 2b | data_tables | 874 tables (thin SDGs, fixture banks) | 874 | 0 |

Measured afterwards from the store, over records whose provenance names the
generating revisions: **31,059 candidate packages and 184,087 distinct file
bodies** that no other supply candidate holds. Of those, 151,937 are
generated code, tests, schemas and READMEs, 905 are upstream files copied
byte for byte, and 31,245 are attribution and licence files. The north star
does not count the last group as useful files. The later 874-table batch
(revisions `fa346712` and `eafa4fe8`) added 874 packages and 5,366 new bodies
by the run's own store report, for about 31,933 packages and 189,453 bodies. None of this is a served
count; the catalogue's served-file measure is unchanged until review.

The packages name the original revisions `c625853a`, `872379b1`, `01fe31fd`,
`7d786592`, `0f36a2ba` and `9d38d128`. They were cherry-picked onto `main` as
`019f4564` to `c05c09f8` because the original branch sat on unpublished local
commits. `/home/username/baltor-library/supply/reports/` holds the original
commits as a git bundle and the revision map.

## Line repairs

- A form-encoded operation whose example body is a string stopped a whole
  openapi run. It is now refused as `operation_body_not_json`.
- A draft 3 `required: true` flag stopped a whole openapi run with a
  `TypeError`. It now names no required fields.
- Specifications declaring `CC BY 4.0`, `Apache2` or `MIT license` are read
  as those allowlisted licences.
- New curated mode for JSON Schemas outside SchemaStore, such as STAC, GBFS,
  Frictionless, Open SDG and the DPG nominee schema, with instances built
  from a schema's own keywords when it has no examples.

## SDG coverage and the next step

[`sdg-source-map.json`](sdg-source-map.json) proposes SDG goals for 1,638
sources. It feeds reviewers attaching `PublicGoodGrant` goals after
independent approval, and grants nothing by itself. SDG 5, 10, 14, 6 and 4
have the fewest sources and remain the thinnest goals.

Licence refusals that need an owner policy call, not code: OCDS core,
official IATI, 360Giving, OWID and the NOASSERTION repositories, plus Apache
LICENSE files with appended text (Airflow, Superset, Iceberg) that the text
matcher refuses.

The private microkit in `baltor-private/discrete-text-components-20261001-v01`
fits the native preparation path. Its 36 function cards pass the prechecks;
its shared core and four skills need a re-layout of first-party files, which
was left for the owner.
