---
name: text-standardization-data-cleaning
description: Standardizes and cleans raw text records that document a logistics customer's key personnel involved in, or directly relevant to, a logistics activity — contact rosters, role lists, relationship notes, and activity logs. Use when such text needs whitespace/tab normalization and line cleanup (data_cleaning) before it is merged, imported, searched, or reviewed; not a substitute for actually managing the customer relationship.
license: MIT
---

# text-standardization-data-cleaning

Harness method for the `data_cleaning` use case: input datatype `text`, operation `standardization`.

## Trigger

Run when a `data_cleaning` pass is requested on text supporting logistics account-relationship management — e.g., a tab-indented key-personnel roster, whitespace-mangled meeting notes, or correspondence excerpts listing the customer's key personnel and their relevance to a logistics activity — and the text must be made structurally consistent before further processing.

## Typed input

- `records: text` — UTF-8 string; the document(s) to standardize.
- `tab_policy: text` (optional) — one of `preserve` (default) or `expand:<n>` where `<n>` is a positive integer column width. When absent, behave as `preserve`.

## Typed output

- `clean: text` — the standardized UTF-8 string.
- `report: text` — newline-delimited list of transformations applied (e.g., `tab_expanded:12`, `trailing_ws_trimmed:3`) plus `flagged:` lines for ambiguities left unresolved.

## Effects

Applies to text only, within a single invocation:

1. Normalizes line endings to `\n`.
2. Trims trailing whitespace on each line; collapses runs of spaces within a line to one.
3. Handles tabs strictly per `tab_policy`: `preserve` leaves every `\t` byte-identical; `expand:<n>` replaces each tab with spaces up to the next multiple of `<n>`. It never replaces a tab with a single space.
4. Collapses 3+ consecutive blank lines to one; preserves single blank-line structure.
5. Records every transformation in `report`; flags mixed tab/space indentation of unknown width instead of guessing.

It cannot and does not by itself maintain or develop business relationships, contact any personnel, verify their roles, or interpret logistics activities — it only standardizes the text records that document them.

## Stop condition

Stop when (a) re-applying the method to `clean` returns a byte-identical string (idempotence) and (b) every tab is either preserved or expanded exactly per the declared `tab_policy`. Do not continue if indentation mixes tabs and spaces and no `tab_policy` is supplied — stop and emit `flagged:mixed_indentation_unknown_width`.

## Known-wrong case (must catch)

A tab-indented document is normalized as if the tabs were spaces — e.g., `KEY\tPERSONNEL` becomes `KEY PERSONNEL`, or an indented roster line `\t\tALICE` collapses to ` ALICE`, destroying indentation depth and column alignment. This method must reject any transformation that substitutes a tab with a single space: under `preserve` the tab survives verbatim; under `expand:<n>` it becomes exactly the spaces required to reach the next `<n>` column boundary.

## Acceptance check

Given input `"Key Personnel\tRole\n\tAlice\tLogistics Manager\n\tBob\tDock Supervisor"`:

1. With `tab_policy: preserve`, `clean` must be byte-identical to the input (every `\t` intact); the check fails if any tab became a single space.
2. With `tab_policy: expand:4`, each tab must expand deterministically to the next multiple-of-4 column, row structure and field order preserved, and re-running the method must produce no further change (idempotence).
3. `report` must list every tab transformation performed and be non-empty whenever any change was made.