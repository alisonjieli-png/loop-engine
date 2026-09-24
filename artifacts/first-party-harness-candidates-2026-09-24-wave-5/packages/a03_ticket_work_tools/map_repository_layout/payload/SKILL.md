---
name: "map-repository-layout"
description: "Produce a bounded tree of a repository that marks source, test, configuration and generated folders with file counts, so a small model can choose where to look without opening every file."
license: MIT
compatibility: "Python 3.10 or later, standard library only."
metadata:
  version: "0.1.0"
---
# Map a repository layout compactly

Get a short map of the repository before you search or open files. The script counts every file into a category and prints a tree that fits in a fixed number of lines. It opens the folders with the most source and test files first.

## When to use it

Use it at the start of a step in a repository you have not seen, or when a search returns too many places to look.

## First action

Run the script at the workspace root. `SKILL_FOLDER` is the folder that holds this file. If you do not know its path, run `ls -d .*/skills/map-repository-layout` and use the folder it prints.

```bash
python3 -I -B SKILL_FOLDER/scripts/map_layout.py --root .
```

In a git repository you can map only tracked files: `git ls-files -z | python3 -I -B SKILL_FOLDER/scripts/map_layout.py --paths-from -`. The result has the shape of `examples/layout-output.json`.

## Steps

1. Read `status`. Continue only when it is `ok`.
2. Read `tree`. Each line gives a folder, its category and its file count; the counts in brackets show what else it holds.
3. Read `largest_source_folders` and `test_file_folders`. Choose at most two folders that match the words of your task.
4. When a line says `more folders here` and you need to see inside, run the script again with the `--focus` value that the line names.
5. Write the chosen folders and the reason for each in your step notes, then open files only there.

## Checks

- Exit status: 0 means source or test files were found, 1 means none were, 2 means the input was refused.
- No chosen folder is marked `generated`, and none appears in `skipped`.
- You do not open any path listed in `sensitive_files`.

## Done when

Your notes name the folders you will open, each with its category and a one-line reason.

## Stop and report when

- `status` is `no_source_found`. The root is probably wrong; report the `tree` lines.
- The script refuses because the folder holds more entries than allowed. Run it once more with `--focus` or with the tracked-file list.
- The only place that matches your task is inside a `generated` folder.

## Known-wrong example

A search for `def parse_price` finds `build/lib/shop/prices.py` first. Editing that file changes nothing, because the next build writes it again. The map marks `build/` as generated and not expanded, and names `src/shop` among the largest source folders.
