# Review note: Check a CSV against a column contract

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a15_data_and_competition_verifiers, model family anthropic. This note is never delivered to a harness.

## Method

One verifier method. The script `scripts/check_column_contract.py` reads a UTF-8 CSV file and a JSON contract with `"record_type": "column_contract/v1"`, applies only the rules written in the contract, and prints one JSON verdict. The rules cover required and optional columns, extra columns, column order, the type of each column (`string`, `integer`, `decimal`, `boolean`, `date`, `datetime`), allowed values, inclusive ranges, text length, uniqueness of one column or of a group of columns, empty cells (`empty: never` and `max_empty_share`), and the number of rows. Every violation is counted in full and listed with its data row, file line and column, with at most three examples for each column and rule. Exit 0 is pass, 1 is fail, 2 is refused input. An unknown contract key or type is refused, so a typing error cannot switch a rule off silently. The checklist holds what code cannot judge, such as whether the contract was written before the table.

## Authoring basis and sources

Original text and code written for this wave, MIT like the repository. No outside text or code was copied. The package continues an interrupted earlier attempt of the same generator assignment, which wrote the script, the first tests and the documents and then stopped before its manifest and this note. That attempt is kept byte for byte in `packages/check_csv_column_contract/earlier-attempt-20260924T0102Z.tar.gz` and `prior-attempt-a15-20260923T2048Z.tar.gz`. This run reviewed every line, added seven tests, rewrote the known-wrong paragraph of `SKILL.md` so that it matches the shipped example, and wrote the manifest and this note.

Sources at the pinned revision `a1fc7432`:

- `src/loop_engine/core/service_runtime/catalogue_packages.py`: the package format this candidate follows.
- `examples/29_intelligence_service/starter-catalogue/bodies/write_a_data_contract_for_a_table_or_feed.md`: the prose method that tells a person what a contract should hold. This package executes such a contract.
- `src/loop_engine/core/observation_expectations.py`: the repository treats a match with a declared shape as a check on structure, never as acceptance of a task. The checklist and the Done when text keep that line.
- `case-studies/data-cleanup-with-and-without-baltor/REPORT-2026-09-22.md`: the study scored cleanup with an independent deterministic scorer and found that long prose material cost prompt tokens without a measured benefit. Here the rules live in a tested script and the entry text stays short.

## Inputs and outputs

Inputs: `--csv` and `--contract` below `--root` (default the current folder), or `--bundle` with the members `csv` and `contract` from a file or from standard input. Options: `--delimiter`, `--max-examples`, `--no-values` for private data, `--max-bytes` (default 64 MiB, refused above it, never truncated). Output: one JSON object with `status`, the CSV path and SHA-256 digest, `checks` with a count for every check the contract uses, `failed_checks`, `violations_by_column`, bounded `violations`, `contract_columns_not_checked` and `empty_cells`.

## Effects

`reads_fs`: the script reads the two named files and refuses `..`, paths that resolve outside `--root` (including through a symbolic link), non-regular files and oversized input. `spawns_process`: `SKILL.md` tells the reader to start `python3`, and the tests start the script with `subprocess`. The script writes nothing, starts no process, uses no network and reads no secret. The tests read the shipped examples, send the other tables on standard input and write no file.

## Closest existing items

- `write_a_data_contract_for_a_table_or_feed` (starter candidate, prose): writes a contract and checks nothing. This package checks a table against a machine-readable contract.
- `validate_input_at_the_boundary_and_refuse_early` (starter candidate, prose): a general rule to validate at the boundary. No executable part.
- `detect_malformed_values_by_dominant_pattern` (served, prose): infers the common shape of one column from the data. This package never infers a rule from the table it checks.
- `audit_csv_structure` (first-party pilot skill with scripts): checks CSV structure such as quoting, repeated headers and field counts, and by its own text infers no types and validates no meaning. This package applies declared column rules.
- `compare_primitive_object_contracts` (Codex candidate, not yet on `main`): finds when a new object contract would refuse a value that the old one admitted. It compares two contracts and reads no table.
- Wave 5 neighbours: `json_schema_check_server` (a07) checks JSON documents through a local protocol server, and the a01 executors change values. This package changes nothing and reads CSV. A search of `scout/existing-inventory.tsv` found no other executable column contract check.

## Positive example

The four rows of `CLEAN` in the tests pass `examples/column-contract.json` with every check at zero, including the optional `email` column with one empty cell and `NA` counted as empty in `monthly_spend`.

## Known-wrong example

`examples/known-wrong-bundle.json` holds the same contract and a table with `Germany` in `country`, `2024-7-30` in a `%Y-%m-%d` column, `1,200.50` in a decimal column, `C-0002` twice, `yes` in a boolean column, `0` below the minimum of `seats` and a leading space in `email`. The script fails with seven violations, each with its row and column. A model that looks at a few rows would miss most of them.

## Harness placement and verification state

The whole folder is copied with `copy_exact_bytes` to `.claude/skills/check-csv-column-contract/`, `.agents/skills/check-csv-column-contract/` (Codex), `.opencode/skills/check-csv-column-contract/`, `.pi/skills/check-csv-column-contract/` and `.gemini/skills/check-csv-column-contract/`. Basis: specification section 6 marks the first four skill folders observed on this machine and the Gemini CLI folder documented in `HARNESS-PACKAGES-CLAUDE-AND-EDITORS-2026-09-23.md`. No harness binary was run for this package. Unverified: whether each harness tells the model the folder path it needs for `SKILL_DIR`, and whether a harness asks for permission before `python3` runs from a skill folder. The command starts the first `python3` on `PATH`; a host that runs unattended should bind a trusted interpreter.

## Customer requests

- "Check that the cleaned customer file still follows our column rules before it goes to finance."
- "Which rows break the contract, and in which column?"
- "Validate this CSV against the JSON schema of its columns, every row, not a sample."

## Limits

The contract format is this package's own `column_contract/v1`; it is not JSON Schema and not any other product's format. Dates must be written exactly as the format writes them. A decimal with a thousands separator is refused as a type violation on purpose. Allowed values compare exact text, also in typed columns. A malformed CSV record gives exit 2 with the line, not a list of violations. Checks that failed before they passed: the first mutation pass ran 32 changes of the script against the earlier tests and 10 were not caught (length bounds, `unique_together` and its rule for empty parts, `row_count`, an absent optional column, a repeated header name, a misspelled top-level key, the size bound on a named file, and the start line of a record that spans two lines). Seven tests were added and each of the 32 changes now fails a named test. The suite holds 29 tests and passes under Python 3.14 and 3.10.
