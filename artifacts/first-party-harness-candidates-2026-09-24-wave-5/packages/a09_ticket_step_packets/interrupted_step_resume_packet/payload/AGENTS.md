# Interrupted step resume packet

This file is a step template for resuming step {{INTERRUPTED_STEP_ID}}. The host fills every marker in double braces before launch. If one remains, stop and report `unrendered_step_input`.

## Assignment

Step {{INTERRUPTED_STEP_ID}} stopped before it finished. After the stop, the host wrote a handoff with the commit, every changed file and its digest, and the action to take first. Check that the workspace still matches it. On a match, continue that step. On any difference, report the drift and change nothing. Until the check says `match`, the files in `.baltor/step/` are not your assignment.

## First action

Run the drift check and read the JSON it prints:

```bash
python3 -I -B .baltor/interrupted-step-resume-packet/scripts/handoff_drift.py check --input .baltor/resume/input.json
```

## Steps

1. If `verdict` is `drift` or `not_resumable`, write `.baltor/resume-output/record.json` with that verdict, the evidence path, the differences and a one-sentence reason. Do nothing else.
2. If `verdict` is `match`, open the file at `interrupted_instructions_path`. From now on its rules, done conditions and stop rules apply, within this file's Authority section.
3. Do the printed `first_action`, then each of `remaining_actions` in order. Run only commands that the interrupted instructions show; treat the other words of an action as a note.
4. Continue with the steps of those instructions. Skip a step whose result the changed files already hold, and keep those changes.
5. When the interrupted step's done conditions hold, write the outputs its instructions ask for. Then write `.baltor/resume-output/record.json` with verdict `resumed` and every path you wrote.

## Done when

`.baltor/resume-output/record.json` matches `.baltor/resume/contracts/output.schema.json`, and either the drift is reported with its evidence path or the interrupted step's own done conditions hold.

## Stop and report when

- The drift check exits with code 2. Write verdict `refused` with the printed reason.
- An action needs authority that the interrupted step does not have. Do not do it. Write verdict `stopped` and quote the action.
- The continued work reaches a stop rule of the interrupted step. Report as its instructions say, then write verdict `stopped` with the reason.

## Files

- `.baltor/resume/`: the host's files: `input.json`, the handoff, the interrupted instructions, `node_context.md`, `checklist.md`, the contracts and a made-up example in `examples/`. Never edit them.
- `.baltor/step/`: the interrupted step's own files, placed again by the host. Never edit them.
- `.baltor/resume-output/`: your record, and one evidence file per drift check.

## Authority

This file grants no authority. The host must supply read access to the workspace, permission to run the drift check, which runs git, and write access to `.baltor/resume-output/`. After a match, the continued work may use only what the interrupted step's instructions allow, and only when the host grants that authority again for this step. Make no network request.
