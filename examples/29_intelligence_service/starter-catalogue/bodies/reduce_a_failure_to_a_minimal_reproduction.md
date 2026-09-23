# Reduce a failure to a minimal reproduction

Cut a failing case down to the smallest input and the shortest program that still fails, so the cause has nowhere left to hide.

## When to use it

Use it when a failure appears in a large system, a large input file or a long sequence of actions, and reading the code has not found the cause.

## Steps

1. Get one reliable failing case. Write down the exact command, input and observed output.
2. Save the failing input somewhere safe, unchanged.
3. Remove half of the input. Run again. If it still fails, keep the smaller half. If it passes, keep the other half.
4. Repeat until removing anything at all makes the failure disappear.
5. Do the same with the program: remove settings, remove modules, replace services with fixed values, until only the failing path remains.
6. After each removal, confirm that the failure text is still the same failure and not a new one.
7. Write the smallest case as a standalone script or test with no external setup.
8. Confirm that the minimal case fails on a clean machine and passes when the suspected cause is changed.

## Checks

- The minimal case fails every time it is run.
- Removing any remaining part makes it pass.
- The failure text matches the original report.
- The minimal case runs without the original data set, network access or private credentials.

## Known-wrong example

A developer reports that a report generator fails on a file of two hundred thousand rows and sends the whole file. The file holds customer names and addresses, so it cannot be shared with the library author. Nobody reduces it. The defect is a single row where a quoted field contains a line break. Three rounds of halving would have produced a two row file with no personal data in it, which anyone could read and fix in minutes.

## What to record

- The original case and the minimal case, both runnable.
- The number of reduction rounds and what was removed.
- Any private data that was removed and replaced with invented values.

## Source

- `src/loop_engine/core/task_materials.py`: this repository unpacks supplied material into one working folder, identifies inputs by their content rather than their names, and keeps the original supplied files separate from what was derived from them.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision a0ca182.
