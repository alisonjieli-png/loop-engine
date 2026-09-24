# Ticket triage: step background

## Objective

Sort ticket {{TICKET_ID}} into go, hold or split before anyone changes code, so that tonight only work that can finish without a person is started.

## Relevant context

- A go starts a row of steps, each in a new harness that sees only its own files: one step writes a failing test, one makes the fix, one verifies it. They all build on your answer.
- A wrong go can spend a whole night on the wrong change. A wrong hold delays one ticket until morning. When the evidence is balanced, hold.
- A go must not drop part of the ticket in silence. A wanted result that no test or command can prove, such as "make the export faster" with no number, becomes an open question, and any open question makes the decision hold.
- A good first test is small: one behavior, one assertion about it, and it runs alone in seconds. Its command is a list of strings, the program first, because the next step runs it without a shell.
- A split is not worked tonight. A person or the host turns the parts into new tickets.
- Notes about this repository from the host: {{REPOSITORY_NOTES}}

## Current state

This is the first step for this ticket tonight. No file has been changed for it and no test has been run.

## Contracts and input

- Input: `.baltor/step/input.json`, described by `.baltor/step/contracts/input.schema.json`.
- Output: your final answer, one `ticket_triage_decision/v1` object described by `.baltor/step/contracts/output.schema.json`. Every key is present in every answer; unused lists are empty and `first_test` is null unless the decision is go.
- A schema match is not acceptance. The host or a person checks the decision before any code changes.

## Acceptance

- The decision is go, hold or split, and each reason names the ticket line or the file it rests on.
- Each sentence of the ticket that states a wanted result appears once: word for word in `acceptance`, or as a question in `open_questions`.
- A go has at least one acceptance statement, no open question, no need, at least one existing file to read, and a first test.
- A hold has at least one open question or at least one need.
- A split has at least two parts, each with its own acceptance statement, and no open question or need.
- No repository file changed during the step.
