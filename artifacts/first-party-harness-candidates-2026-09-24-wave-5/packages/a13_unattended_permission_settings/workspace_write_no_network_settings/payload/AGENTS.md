# Workspace write without network settings

## What is active

You may create and edit files inside the workspace and run tests. The shell commands you may run are `python3 -m pytest`, `python3 -m unittest`, `git status` and `git diff`, each on its own, without `>`, `2>&1`, `|` or `&&`; the harness shows their output anyway. Do not change `.git`, `.claude`, `.codex`, `.gemini`, `.opencode`, `.baltor` or `opencode.json`. There is no network: install nothing and do not push. Nothing asks for approval: a refused action fails at once.

First action: run `python3 -m pytest -q`, or `python3 -m unittest` when the project has no pytest, and note the result before you change a file.

## If something is refused

1. If the command had `>`, `2>&1`, `|` or `&&`, run it once more without that part.
2. Never look for another way to write outside the workspace, use the network or hand work to another agent.
3. If a test needs the network or a missing package, note the test and its error.
4. Run `python3 -I -B .baltor/workspace-write-no-network-settings/scripts/check_workspace_write_no_network_settings.py` to see what is allowed, then report what was blocked.
