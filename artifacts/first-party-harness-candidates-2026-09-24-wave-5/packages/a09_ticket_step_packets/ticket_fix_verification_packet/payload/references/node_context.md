# Ticket fix verification: step background

## Objective

Decide from evidence whether the fix for ticket {{TICKET_ID}} is ready for a person to review, and prepare the summary and commit message that person will read.

## Relevant context

- The fix step `{{FIX_STEP_ID}}` may report a success that its files do not support. Judge the files and the test runs, not its words.
- Step `{{REPRODUCTION_STEP_ID}}` wrote the reproduction test and saw it fail. Its digest is in `input.json`. If the fix changed that test, the fix may have weakened it, so the check fails even when the tests pass.
- The full test run starts only after every earlier check passed, so a broken fix does not spend the night on a long run.
- The diff file leaves out the files the host placed, such as a composed `AGENTS.md`, so read that file instead of the whole tree. Files that git ignores are not in it and not checked. If `diff_error` is not null or `diff_truncated` is true, read the files in `changed_paths` themselves.
- Nothing is committed during the night. A person or the host commits after review, with your proposed message or without it.

## Current state

The working tree holds the reproduction test and the fix, uncommitted, on top of base revision {{BASE_REVISION}}. No verification has run for this fix yet, and `.baltor/step-output/` is empty.

## Contracts and input

- Input: `.baltor/step/input.json`, described by `.baltor/step/contracts/input.schema.json`. Read it; never edit it. Every evidence file records its digest.
- Output: `.baltor/step-output/output.json`, one `ticket_fix_verification_record/v1` object described by `.baltor/step/contracts/output.schema.json`. For `blocked`, `blocker` holds the reason; otherwise it is null.
- Evidence: one `ticket_fix_verification_run/v1` file and one diff file per checks run, in the `evidence_dir` of the input.

## Acceptance

- `ready_for_review` only when every check passed and `concerns` is empty.
- Every failed check and every concern appears in the summary and in `output.json`.
- A commit message exists only for `ready_for_review` and passed the message check.
- No file outside `.baltor/step-output/` changed during this step, and nothing was staged or committed.
