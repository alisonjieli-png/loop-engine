# Step context

## Objective

Report the newest release in `CHANGELOG.md`: its version, its date and how
many changes it lists.

## Relevant context

Each release starts with a line such as `## 2.4.1 (2026-09-18)`. The changes
of a release are the list lines below it, up to the next release line. The
newest release is the first one in the file.

## First action

Call `read_step_file` for `checklist.md`, then read `CHANGELOG.md` with your
own file tool.

## Current state

No result exists yet.

## Contracts and input

The result matches `contracts/output.schema.json`: `version`,
`release_date` and `change_count`.

## Acceptance

The three values match the first release section of `CHANGELOG.md`.
