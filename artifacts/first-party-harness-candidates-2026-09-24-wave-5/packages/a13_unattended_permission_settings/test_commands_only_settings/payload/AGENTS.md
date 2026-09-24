# Test commands only settings

## What is active

This is a checking step. You may read, list and search files and run only these commands: `python3 -m unittest`, `python3 -m pytest`, `python3 -m pyflakes`, `ruff format --check` and `python3 -m black --check`. Every other command is refused, and so are file edits, output redirection with `>`, web access and handing work to another agent. Nothing asks for approval.

First action: run the test command named in your task, or `python3 -m pytest -q` when none is named.

Done when you have reported each command you ran, its exit status and the names of failing tests or files.

## If something is refused

1. Do not fix code or change tests in this step. Report the failure instead.
2. Do not try other commands. Run `python3 -I -B .baltor/test-commands-only-settings/scripts/check_test_commands_only_settings.py` to see the exact list.
3. If the project needs a command that is not listed, stop and report its name.
