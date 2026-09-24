# Formats and problem names

## Inputs the script reads

| Form | How items and evidence are found |
|---|---|
| `night_morning_report/v1` JSON | Each entry of `complete` is one claim. Its `claims` give the text and the evidence path, and its `handoff` is checked too. Entries of `blocked` and `unfinished` are listed as not claims. `counts` is compared with the lists. |
| Other JSON | A list of items, or an object with an `items`, `tickets`, `results`, `entries` or `tasks` list. Each item has an id, a `status` and an `evidence` list. |
| Markdown | A table with a status column and an evidence column. Paths are in backticks or links; `sha256:HEX` and `exit N` after a path belong to it. |

An evidence entry is a path, or an object with `path` and, when known, `sha256`, `exit_code`, `expect_exit` and `text`. `expect_exit` 0 says the run should pass; another number says it should fail, such as a run before the fix. A cited `exit_code` states the same.

Status words such as verified, done, fixed and complete claim completion. Words such as blocked, narrowed, unfinished and failed do not. `verified_by_test_change` claims completion but always needs reading.

## What counts as a passing run

A cited file shows a pass by itself when it is a JSON record with a passing verdict, `passed` true, all `checks` passed or exit code 0; a JUnit XML file without failures; or a test or build log whose summary line passes. A `ticket_reproduction_run/v1` record with the verdict `failing_test_recorded` shows a failure recorded on purpose. It supports a claim about the run before the fix, never a pass.

## Problems (verdict fail)

| Problem | Meaning |
|---|---|
| `no_evidence` | The item claims completion and cites nothing. |
| `evidence_missing`, `evidence_path_unsafe`, `evidence_path_missing` | The cited file is not there, lies outside the root, or no path is given. |
| `evidence_unreadable` | The file cannot be read, such as XML with declarations. |
| `digest_mismatch`, `digest_malformed`, `digest_not_cited` | The bytes differ from the cited SHA-256, the digest is not 64 hexadecimal characters, or `--require-digests` was given and no digest is cited. |
| `exit_code_contradicted` | The report cites one exit code and the file records or shows another result. |
| `exit_code_failed`, `expected_failure_not_shown` | The cited exit code or the file does not match the stated `expect_exit`. |
| `evidence_shows_failure` | The file shows a failure where a pass was stated, or where nothing else in the item shows a pass. |
| `no_passing_gate_evidence` | No cited file without a problem shows a passing run. |
| `handoff_missing`, `handoff_unreadable`, `handoff_status_differs` | The cited step handoff is gone, is not JSON, or does not say complete. |
| `count_mismatch` | A count in the report differs from its own entries. |

## Reasons to read (verdict review)

| Reason | Meaning |
|---|---|
| `evidence_shows_failure` | A file shows a failure and the report states no expectation. Read whether the claim describes that failure. |
| `changed_since_handoff` | A file the handoff lists has other bytes now, so the evidence was made for other bytes. |
| `handoff_not_checked` | The handoff is not a `night_step_handoff/v1` record. |
| `only_tests_changed` | The status is `verified_by_test_change`. Read the diff before calling it a fix. |
