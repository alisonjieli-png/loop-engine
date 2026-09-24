# Checks the script cannot do

Answer each item with yes, no or unknown, and name the file you read. Put every no or unknown in your answer as an open point.

- [ ] The allowed patterns came from the task, not from the list of files the step happened to change.
- [ ] The diff covers the whole step: its base is the revision the step started from, and new files were checked with `--untracked`.
- [ ] Each `--permit` and `--ignore` value is named in the task, and every path in `ignored` was placed by the host, not written by the step.
- [ ] Every change inside the allowed paths belongs to the ticket. An allowed path does not make an unrelated edit right.
- [ ] No settings or environment file changed under a broad pattern such as `**`.
- [ ] Every warning, such as a file that became executable, has an explanation in your answer.
