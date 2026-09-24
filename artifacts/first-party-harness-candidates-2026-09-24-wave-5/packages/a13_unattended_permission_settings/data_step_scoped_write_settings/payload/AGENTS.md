# Data step scoped write settings

## What is active

Read input from `data/raw/`. Write results only under `data/output/` and reports only under `reports/`. Raw data, source code and Python files are protected: edits there are refused, and so are paths that contain `..`, output redirection with `>`, web access and handing work to another agent. Shell commands are limited to `ls`, `wc`, `head` and scripts started as `python3 -I -B` from `.baltor/` or the harness skill folder. The settings cannot stop a script from writing where its arguments point, so give every script an output path under `data/output/` or `reports/`. Nothing asks for approval.

First action: list `data/raw/` and `data/output/`.

## If something is refused

1. Never write a changed copy back into `data/raw/`.
2. Do not retry the refused action or work around it.
3. Run `python3 -I -B .baltor/data-step-scoped-write-settings/scripts/check_data_step_scoped_write_settings.py` to see what is allowed, then stop and report the path or command you needed.
