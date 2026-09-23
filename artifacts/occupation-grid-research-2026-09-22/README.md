# Pinned occupation task opportunity research

Kind: dated source and ideation record, September 22, 2026. This is a
candidate opportunity inventory, not harness intelligence, a reviewed
skill, or a measure of customer demand.

The source is the
[O*NET® 31.0 Database](https://www.onetcenter.org/database.html) by the
U.S. Department of Labor, Employment and Training Administration, used
under [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/).
The [database licence](https://www.onetcenter.org/license_db.html) applies
to the specified downloadable files. Our inventory selects ten
occupations, joins task identifiers to detailed work activity identifiers,
and calculates counts. The U.S. Department of Labor has not approved,
endorsed, or tested this selection or any later candidate skill.

The exact source is
`https://www.onetcenter.org/dl_files/database/db_31_0_csv.zip`, downloaded
September 22, 2026 local time with SHA-256
`55033fc68b4c13ec23e7f74dc6378660f6e854e75d55d6e333ae0a761d3987cd`.
The ZIP stays in ignored `source/`; the
[derived inventory](task-opportunities.json) records the source URI,
licence, digest, source task text, selection and changes. The
[reproduction script](inspect_onet.py) refuses a different source digest.

## What the pinned source yields

The complete download contains 1,016 occupation rows, 18,838 task
statement rows and 24,087 task-to-detailed-work-activity links. Our
explicit ten-occupation selection contains 179 task rows and 136 distinct
detailed work activity identifiers; 36 of those activities occur in more
than one of the selected occupations. The same activity can motivate one
reusable method across roles, so multiplying task rows by company and
model labels would overcount methods. Task statements also include
physical, managerial and regulated work that may not fit a coding harness.

| Selected occupation | Task rows | Core task rows |
|---|---:|---:|
| Logisticians | 22 | 22 |
| Project Management Specialists | 20 | 20 |
| Management Analysts | 11 | 10 |
| Market Research Analysts and Marketing Specialists | 13 | 11 |
| Accountants and Auditors | 30 | 30 |
| Computer Systems Analysts | 22 | 18 |
| Software Developers | 17 | 11 |
| Data Scientists | 16 | 15 |
| Technical Writers | 15 | 8 |
| Customer Service Representatives | 13 | 7 |

This selection is deliberately broad and **not representative or weighted
by demand**. A row can be a source of a task hypothesis, but it does not
prove the procedure, rights, native format, customer value or independent
review of a generated package. The [first-party candidate guide](../first-party-harness-candidates-2026-09-22/GENERATION-GUIDE.md)
keeps those gates separate.

## Reproduce

```bash
mkdir -p artifacts/occupation-grid-research-2026-09-22/source
curl --fail --location --output \
  artifacts/occupation-grid-research-2026-09-22/source/db_31_0_csv.zip \
  https://www.onetcenter.org/dl_files/database/db_31_0_csv.zip
sha256sum artifacts/occupation-grid-research-2026-09-22/source/db_31_0_csv.zip
python3 artifacts/occupation-grid-research-2026-09-22/inspect_onet.py --check
python3 artifacts/occupation-grid-research-2026-09-22/test_inspect_onet.py
```

If the upstream ZIP changes, `--check` refuses it. Record a new source
version and new dated inventory instead of silently replacing this one.
O*NET task text is retained here only as licensed research input. A
customer-facing skill must be an original, separately reviewed method
with its own source, rights and exact-byte evidence.
