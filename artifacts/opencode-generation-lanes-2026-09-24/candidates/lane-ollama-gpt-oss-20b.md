---
name: text-standardization-data-cleaning
description: Standardize textual data for consistent logs and communications in logistics relationship management.
license: MIT
---

## Trigger
When a text document containing communications with customers is received for processing.

## Typed input
```text
Raw string, possibly with inconsistent indentation or whitespace.
```

## Typed output
```text
Normalized string with tabs replaced by spaces, excess whitespace trimmed, and consistent line breaks preserved.
```

## Effects
- Normalizes whitespace, removing leading and trailing spaces.
- Replaces all tab characters with the appropriate number of spaces (4 spaces per tab).
- Ensures consistent indentation levels.
- Eliminates any inconsistent spacing within lines.

## Stop condition
Processing ceases after the text has been fully normalised or if the input is empty.

## Known‑wrong case it must catch
A tab‑indented document is normalized as if the tabs were spaces.

## Acceptance check
Verify that the output string contains no `\t` characters and that any indentation appears as a multiple of four spaces.