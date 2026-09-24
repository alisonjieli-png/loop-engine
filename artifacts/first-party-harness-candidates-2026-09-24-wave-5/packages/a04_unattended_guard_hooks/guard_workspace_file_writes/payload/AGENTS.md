# Guard file writes to the workspace

## What is active

A hook checks every write, edit and delete made with the file tools before it happens. It follows symbolic links to the real file. It refuses a target that is:

- outside the workspace folder;
- inside `.git` or other version control folders;
- inside `.baltor`, `.claude`, `.cursor` or `.github/hooks`, except paths the step reopens;
- on a protected path listed in `.baltor/step/guard-workspace-file-writes.json`, such as instruction files and editor settings;
- a folder, a special file or a file with other hard links.

The hook does not see writes made by shell commands. Never use a shell command to change a file that this hook would refuse.

## If something is refused

1. Read the reason. It names the path and the rule it broke.
2. Write your result to a new file inside the workspace and outside protected paths.
3. Never try a link, a copy or a shell command to reach the same file.
4. If the task needs that exact file changed, stop and report the path and why.
