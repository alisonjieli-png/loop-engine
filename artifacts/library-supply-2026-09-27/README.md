# Library supply lines, September 27, 2026

Counts only: no third-party text, no package body and no local path. The
record that reads them is
[the library supply research record](../../docs/research/LIBRARY-SUPPLY-LINES-2026-09-27.md).

| File | What it holds |
|---|---|
| `run-summaries.json` | `library_supply_run_summaries/v1`: for each supply line's last run, the candidates stored, the refusals by reason, the forms, licences and effects, the store write counts and the requests made; for the API line, each specification's repository, commit, SHA-256, licence and counts; for the verbatim code round of the licensed import, each repository's commit and module count. |
| `supply-report.json` | `library_supply_report/v1`, written by `tools/build_library_supply.py report`: the served release `daily-2026-09-27-16` by family and form, the import store's supply not yet exported (imported and generated), the approval share of seven daily slots, the needs per milestone and the slot-by-slot projection in two scenarios. |

The packages themselves, every fetched fact and every request log stay in
the run folders outside the repository, under
`/home/username/baltor-library/supply/<line>/2026-09-27/`, and the candidates
in the import store.
