# Log tool activity for the morning report

## What is active

After each tool call, a hook appends one line to `.baltor/state/log-tool-activity/activity.jsonl`. A line holds the time, the tool, a short target and the outcome. For shell tools the target is only the program and up to two short words. For file tools it is the path. File contents and command output are never written.

The host reads this log to build the morning report. You do not need to write to it or read it.

## If something is refused

This hook never refuses a call. If you see one of its diagnostics, for example that the log is full:

1. Continue the step as planned.
2. Name the diagnostic in your handoff, so the host can check the report.
3. Do not edit, move or delete the log.
