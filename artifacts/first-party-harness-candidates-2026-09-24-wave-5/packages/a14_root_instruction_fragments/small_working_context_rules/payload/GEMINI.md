# Small working context rules

## Applies when

A small or low-cost model runs this step. Everything you open or print stays in your context until the step ends.

## Rules

1. Start from the paths your assignment names. Open no other file until a search shows you need it.
2. Run shell commands and write files only when your assignment's effects allow it: an entry ending in `_process` allows commands, and `writes_fs` allows writing. Otherwise use only your read and search tools.
3. Search before you read: your search tool, or `grep -rn -m 20 "TEXT" FOLDER | head -n 40`. Then open the file at the line found.
4. Check a file's size before you open it: `wc -l -c FILE` or your tools.
5. Read a file over 300 lines or 20,000 bytes in slices of at most 120 lines: your read tool's offset and limit, or `sed -n '200,319p' FILE`. For very long lines, use `head -c 4000 FILE`.
6. Never print a whole folder tree, lock file, generated or minified file or data file; read its first 20 lines (`head -n 20 FILE`). For a log, read the last 40 lines (`tail -n 40 FILE`) and the error lines (`grep -n -m 20 -E "FAIL|ERROR|Error" FILE`).
7. When you may run commands and write files, run any command that may print more than 40 lines through the helper, which saves the output and prints a short summary: `python3 -I -B .baltor/small-working-context-rules/scripts/run_and_summarize.py -- COMMAND`.
8. Do not read unchanged lines twice. When you may write files, keep facts you need later, with file and line, in `.baltor/state/small-working-context-rules/notes.md`.
9. When you may write files, put a result longer than 40 lines in a file and report its path and at most three summary lines, except the final answer whose form your assignment names.

## If a rule blocks the work

If understanding the step needs more than 10 files or 2,000 lines, stop and report that the step is too large. Name the files and a way to split it. Do not read everything instead.
