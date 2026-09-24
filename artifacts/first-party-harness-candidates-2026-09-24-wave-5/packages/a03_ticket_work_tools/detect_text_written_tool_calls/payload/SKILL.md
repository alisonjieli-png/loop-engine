---
name: "detect-text-written-tool-calls"
description: "Scan a saved harness session log for assistant turns that describe a tool call in plain text without making a structured call, the failure that stalls small local models, and report the rate."
license: MIT
compatibility: "Python 3.10 or later, standard library only."
metadata:
  version: "0.1.0"
---
# Detect tool calls written as plain text

Some models, often small local ones, answer with text such as `{"name": "write", "arguments": {...}}` instead of making a real tool call. The harness reads that text as a final answer, and the step ends with nothing done. This skill measures how often that happened in one session log.

## When to use it

Use it after a step that ended without its output. Use it before an unattended run, on the log of one short probe step that had to call a tool.

## First action

Run the script on the log that the host or the task names. Give the folder that holds the log as `--root`. `SKILL_FOLDER` is the folder that holds this file. If you do not know its path, run `ls -d .*/skills/detect-text-written-tool-calls` and use the folder it prints.

```bash
python3 -I -B SKILL_FOLDER/scripts/detect_text_tool_calls.py LOG_FILE --root LOG_FOLDER --expect-calls
```

The accepted log shapes are in `references/log-formats.md`. A small sample log is `examples/generic-session.json`, and its result is `examples/scan-output.json`.

## Steps

1. Read `status`, `rate`, `assistant_turns`, `turns_with_structured_calls` and `last_turn_flagged`.
2. If `notes` says that no tool names were known, run the command again with `--tool NAME` for each tool the harness offered, for example `--tool read --tool write --tool bash`.
3. For each item in `flagged`, note `kind`, `tool` and `known_tool`. The output quotes no text from the log.
4. Decide: `structured_calls_work` means the model made real tool calls in this harness. Any other status means it did not, for this log.
5. Write the status, the rate, the turn counts and your decision in the step notes.

## Checks

- Exit status: 0 means the rate is at or below `--max-rate` (default 0); 1 means calls written as text, or no structured call at all with `--expect-calls`; 2 means the input was refused.
- `format` names the log shape that was read. If it is wrong, run again with `--format NAME`.
- Do not open the log yourself. It can be large and private.

## Done when

Your notes hold the status, the rate, the turn counts and the decision to continue or to stop.

## Stop and report when

- `status` is `text_calls_detected` or `no_structured_calls`. Do not start more unattended steps with this model and harness. Report the counts.
- The script exits with status 2, for example because no assistant turn was found. Report the `reason`.
- No log was named. Do not search private folders for one.

## Known-wrong example

A local model answered every step with a tool call written as JSON text. Each reply was counted as a finished step, but no output file existed. On such a log the script reports `rate` 1.0 and `last_turn_flagged` true.
