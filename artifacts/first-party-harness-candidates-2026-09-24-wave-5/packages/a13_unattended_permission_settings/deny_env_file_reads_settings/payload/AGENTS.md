# Deny environment file reads settings

## What is active

Environment files and key files are closed to this step. The harness refuses to read, search, print or edit any file whose name starts with `.env`, including `.env.example` and `.envrc`, and any file whose name ends in `.pem`, `.key`, `.p12` or `.pfx`. These settings only add refusals; your other step rules still decide everything else.

First action: go on with your task without opening these files. You do not need them to learn how the project is configured.

## If something is refused

1. Do not try another tool, command or path to reach the same file.
2. If the task needs a setting, write the name of the environment variable in your report and say where the step needs it. Never copy a key or a secret value into a file or an answer.
3. Keep working on the parts of the task that do not need it.
