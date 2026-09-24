# Ticket fix verification step packet

This file is a step template for ticket {{TICKET_ID}}. The host fills every marker in double braces before launch. If one remains, stop and report `unrendered_step_input`.

## Assignment

Step `{{FIX_STEP_ID}}` changed the code to fix ticket {{TICKET_ID}}. Judge that fix by evidence, not by what the step said about it. Run the checks script, read the diff it saves, then write a change summary and, only when everything passed, a proposed commit message. You verify. You do not repair, and you never commit.

## First action

Run the checks script and read the JSON it prints:

```bash
python3 -I -B .baltor/ticket-fix-verification-packet/scripts/run_fix_checks.py --input .baltor/step/input.json
```

## Steps

1. Read each entry of `checks` and the evidence file named in `evidence_path`. A failed relevant or full run shows its output in `runs`.
2. Read the diff file named in `diff_path`. It holds the changes of the judged paths and nothing the host placed. Then read each file in `new_paths`.
3. Look for what the checks cannot see: a deleted, skipped or loosened test, a secret value, a change that the ticket did not ask for. Write each one in `concerns`.
4. Write the change summary to `summary_path` from `input.json`: one line per changed path saying what changed and why, then the verdict, the failed checks and the concerns.
5. Only when no check failed and `concerns` is empty, write the commit message to `commit_message_path`: a subject of at most 72 characters that names the ticket, a blank line, then two to five short lines. Follow `commit_message_style`. Then check it:

```bash
python3 -I -B .baltor/ticket-fix-verification-packet/scripts/run_fix_checks.py --input .baltor/step/input.json --check-commit-message
```

6. Write `.baltor/step-output/output.json` in the shape of `.baltor/step/contracts/output.schema.json`.

## Done when

The summary names every changed path, `output.json` matches its schema with `committed` false, and for `ready_for_review` the message check printed `"passed": true`.

## Stop and report when

- The checks script exits with code 2. Write verdict `blocked` and copy its reason into `blocker`.
- A check failed or you wrote a concern. Do not edit code or tests to change that. Write verdict `not_ready`.
- The diff shows a secret value. Name the file and line in the summary, not the value.

## Files

- `.baltor/step/`: the host's files: `input.json`, `node_context.md`, `checklist.md`, the contracts and a made-up example in `examples/`. Read them; never edit them.
- `.baltor/step-output/`: your summary, message and `output.json`, and one evidence file and one diff file per script run in `evidence/`. Keep them all.

## Authority

This file grants no authority. The host must supply read access to the repository, permission to run the checks script, which runs git and the two test commands, and write access only to `.baltor/step-output/`. Do not edit, stage, commit, push, reset or stash anything, and run no other command.
