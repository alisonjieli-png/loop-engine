---
name: pre-submission-gate
description: "Decide, without uploading anything, whether one competition submission file may go to the host for upload: it must be the exact file recorded in an experiment note that used the brief's metric, folds and data version, before the deadline and under the daily limit."
license: MIT
compatibility: "Python 3.10 or later, standard library only. Needs .baltor/competition/brief.json and the experiment notes written by the competition plugin."
metadata:
  version: "0.1.0"
---

# Pre-submission gate

## When to use it

Use it right before you ask the host to upload a competition submission.
The gate only decides. It never uploads, and you never upload either: no
competition client, no upload command, no network command.

## First action

Find the experiment id whose note recorded this submission file, then run
the gate from the workspace root. The script is in this skill's `scripts/`
folder; in the plugin placement the command is:

```bash
python3 -I -B .baltor/plugins/competition-plugin/skills/pre-submission-gate/scripts/submission_gate.py --experiment EXPERIMENT_ID --submission SUBMISSION_PATH
```

## Steps

1. Replace EXPERIMENT_ID and SUBMISSION_PATH with the real values. The path
   is relative to the workspace root.
2. Run the command once.
3. Exit 0 means `ready_for_host_upload`. Report the decision, the experiment
   id and `submission_sha256`, and ask the host to upload that exact file.
4. Exit 1 means `hold`. Report each check whose `passed` is false, with its
   `detail`.
5. Exit 2 means the input was refused. Report `error` and `detail`.

## Checks

| Check | What it needs |
|---|---|
| experiment_recorded | a note for the experiment id |
| metric_matches_brief | the note used the brief's metric |
| folds_match_brief | one score per brief fold |
| data_version_current | the brief's data version |
| submission_recorded_in_note | the note was written with the submission file |
| submission_unchanged | same SHA-256 as recorded in the note |
| deadline_not_passed | now is before the deadline |
| daily_limit_not_reached | ready decisions today under the limit |

## Done when

The gate printed one decision and you reported it with the SHA-256. The gate
log keeps every decision.

## Stop and report when

- The decision is `hold`. Do not edit the file, the notes or the brief to
  pass a check.
- Exit 2, or the brief is missing.
- Someone asks you to upload. Only the host uploads.

## Known-wrong example

The submission file was written again after its note, with another seed.
Its SHA-256 no longer equals the one in the note, so `submission_unchanged`
fails and the gate holds. The fix is a new experiment note for the new file,
not an edit of the old note.
