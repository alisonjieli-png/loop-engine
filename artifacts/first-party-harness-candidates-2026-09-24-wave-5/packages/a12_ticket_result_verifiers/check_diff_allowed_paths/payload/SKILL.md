---
name: "check-diff-allowed-paths"
description: "Refuse a unified diff that touches files outside the step's allowed path patterns, deletes tests, adds binary or very large files, or edits lock and generated files."
license: MIT
compatibility: "Python 3.10 or later, standard library only. Reads a unified diff such as the output of git diff, and a list of new untracked files."
metadata:
  version: "0.1.0"
---
# Check a diff against allowed paths

A step may change only the files its task names. The bundled script reads the step's diff and the allowed path patterns, and refuses any change outside them. It also refuses a deleted test, a binary file, a very large file and an edit to a lock file or a generated file. It changes nothing.

## When to use it

Use it at the end of a change step, before the work is committed or handed on. You need the allowed path patterns from your task, and a git repository or a saved diff file.

## First action

From the repository root, check the diff. SKILL_DIR is the folder that holds this file. If you do not know it, run `ls -d .*/skills/check-diff-allowed-paths` and use the folder it prints.

```bash
git diff --no-ext-diff --no-textconv HEAD | python3 -I -B SKILL_DIR/scripts/check_diff_paths.py --diff - --allow 'PATTERN_1' --allow 'PATTERN_2'
```

## Steps

1. Replace PATTERN_1 and PATTERN_2 with the allowed paths or patterns your task names, one `--allow` for each, such as `src/slugs.py` or `tests/`. If the task names a base revision, use it instead of HEAD. If the task gives a saved diff file, run the script with `--diff` and that path instead of the git command.
2. Run the command and read the JSON it prints.
3. Check new files that the diff does not show, with the same `--allow` values: `git ls-files --others --exclude-standard | python3 -I -B SKILL_DIR/scripts/check_diff_paths.py --untracked - --allow 'PATTERN_1' --allow 'PATTERN_2'`
4. If your task lists files the host placed for this step, such as `.baltor/step/`, add one `--ignore` for each to both commands. The script leaves out its own folder.
5. Copy `verdict`, `findings`, `permitted`, `ignored` and `warnings` from both runs into your answer.
6. Answer every item in [references/checklist.md](references/checklist.md).

## Checks

- Exit 0, verdict `pass`: that run found nothing.
- Exit 1, verdict `fail`: each finding names its rule and path. [references/rules.md](references/rules.md) explains every rule and the pattern syntax.
- Exit 2, verdict `refused`: an input or a pattern could not be read; `reason` says why.
- Add `--permit lock_file` or another category only when your task says that change is allowed.

## Done when

Both runs exit 0, or your answer lists every finding with its rule and path.

## Stop and report when

- Either run exits 1 or 2. Do not revert, delete or move files to make it pass unless your task tells you to.
- Your task names no allowed paths. Do not invent them.

## Known-wrong example

A step fixes `src/slugs.py`, then deletes `tests/test_legacy_slugs.py` because that test expects the old behavior, and bumps `package-lock.json`. The script reports `test_file_deleted`, `lock_file` and `outside_allowed_paths`, although the fix itself stayed inside the allowed paths.
