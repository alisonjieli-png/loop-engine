# Read-only investigation settings

## What is active

You may read, list and search files. Use the file read and search tools to look inside files. The shell commands you may run are `git status`, `git diff`, `git log`, `git show`, `ls`, `pwd` and `wc`, each on its own, without `>`, `2>&1`, `|` or `&&`. You cannot create, edit or delete files, use the network or hand work to another agent. No approval prompt will appear: a refused action fails at once.

First action: run `git status`. Give your findings in your final answer, because this step changes no file.

## If something is refused

1. If the command had `>`, `2>&1`, `|` or `&&`, run it once more without that part.
2. To read or search a file, use the read or search tool instead of a shell command.
3. Never look for another way to write, use the network or hand work to another agent.
4. If you are still blocked, run `python3 -I -B .baltor/read-only-investigation-settings/scripts/check_read_only_investigation_settings.py`, then stop and report the action you needed and why.
