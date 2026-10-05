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
| 4 | openapi_operations | 185 public sector, health, science, energy | 21,908 | 2,993 |
| 4 | json_schemas (API components) | same 185 | 17,856 | 15,176 |
| 4 | mcp_registry | registry refresh | 2,917 | 36,520 |
| 5C | openapi_operations | 154 telecom, industrial, mobility, finance, logistics | 5,170 | 771 |
| 5C | json_schemas (API components) | same 154 | 8,184 | 12,303 |
| 5D | openapi_operations | 288 broad sweep | 21,165 | 1,834 |
| 5D | json_schemas (API components) | same 288 | 15,913 | 8,390 |

Measured from the store on October 5, over `candidate` records whose
provenance names one of the generating revisions listed below:
**125,046 candidate packages** (62,946 openapi_operations, 56,474
json_schemas, 2,917 mcp_registry, 1,414 data_tables, 1,295
function_extracts) holding **628,800 distinct task-bearing file bodies, of
which 627,782 no earlier supply candidate holds**. 626,965 of them are
generated code, tests, schemas and READMEs and the rest are upstream files
copied byte for byte. Attribution and licence files are excluded, as the
north star does not count them. Earlier rows superseded by a later run are
not counted. None of this is a served count; the catalogue's served-file
measure is unchanged until review.

The rounds' generating revisions are `c625853a`, `872379b1`, `01fe31fd`,
`7d786592`, `0f36a2ba`, `9d38d128`, `eafa4fe8`, `ccb269c8`, `0e5ecb50`,
`5f94ab71` and `3ff8d79d`.

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
- A branch name the read-only reader refuses, such as one containing `/`,
  stopped a whole run. It is now an unreadable source.
- The October 4 registry refresh ran out of its 4,000 licence lookups,
  still reported the registry complete and withdrew 5,176 candidates.
  `b99e5cd3` and `05091539` now count unread and rate-limited licence
  lookups as undecided, so such a pass withdraws nothing. A restoration pass
  with a larger lookup allowance is running; its candidates are not in the
  counts above.
- New curated mode for JSON Schemas outside SchemaStore, such as STAC, GBFS,
  Frictionless, Open SDG and the DPG nominee schema, with instances built
  from a schema's own keywords when it has no examples.

## SDG coverage and the next step

[`sdg-source-map.json`](sdg-source-map.json) proposes SDG goals for 2,391
sources. It feeds reviewers attaching `PublicGoodGrant` goals after
independent approval, and grants nothing by itself. SDG 5, 6, 1, 10 and 14
have the fewest sources and remain the thinnest goals.

Licence refusals that need an owner policy call, not code: OCDS core,
official IATI, 360Giving, OWID and the NOASSERTION repositories, plus Apache
LICENSE files with appended text (Airflow, Superset, Iceberg) that the text
matcher refuses.

The private microkit in `baltor-private/discrete-text-components-20261001-v01`
fits the native preparation path. Its 36 function cards pass the prechecks;
its shared core and four skills need a re-layout of first-party files, which
was left for the owner.
