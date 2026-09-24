# Interrupted step resume: step background

## Objective

Finish the work of step {{INTERRUPTED_STEP_ID}} without repeating it, and without building on a workspace that changed after its handoff was written.

## Relevant context

- Unattended steps stop for ordinary reasons: a time limit, a closed session, a rate limit or a crash. A stopped harness cannot write its own handoff, so the host wrote it right after the stop, from facts it can check: the commit, every path that differed from that commit with its digest, and the first action and done conditions copied from its own rendered copy of the step's instructions. The handoff lists no claims; the changed files show what was done.
- A handoff is true only for the workspace it describes. When a file changed after it was written, continuing could overwrite work that someone else did, or build on a state that nobody checked. That is why the check runs first and any difference ends the step.
- The check also compares the handoff, the instructions copy and the interrupted step's packet files with the digests the host recorded. It refuses an action that quotes no command or path of the interrupted instructions, or quotes one they do not show. It cannot judge whether an action is wise; judge that against the instructions.
- What the host saw when the step stopped: {{INTERRUPTION_NOTE}}

## Current state

The workspace is as the interruption left it. The host placed the interrupted step's files in `.baltor/step/` again, and its outputs so far are in `.baltor/step-output/`. The handoff and the instructions copy are in `.baltor/resume/`. Nothing has run in this step yet.

## Contracts and input

- Input: `.baltor/resume/input.json`, described by `.baltor/resume/contracts/input.schema.json`. Read it; never edit it.
- Handoff: one `night_step_handoff/v1` object, described by `.baltor/resume/contracts/handoff.schema.json`.
- Output: `.baltor/resume-output/record.json`, one `interrupted_step_resume_record/v1` object described by `.baltor/resume/contracts/output.schema.json`.
- Evidence: one `interrupted_step_drift_check/v1` file per check, in the `evidence_dir` of the input.

## Acceptance

- The drift check ran before any other action, and its evidence file exists.
- After drift or not_resumable, nothing outside `.baltor/resume-output/` changed.
- After a match, the work started from the recorded first action, kept the changed files, and ran only commands the interrupted instructions show.
- No file in `.baltor/resume/` or `.baltor/step/` changed, and the record names every file that the continued work wrote.
