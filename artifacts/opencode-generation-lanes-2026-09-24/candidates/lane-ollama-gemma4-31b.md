---
name: text-standardization-data-cleaning
description: Use when normalizing text data from logistics relationship management records to ensure consistent formatting and eliminate whitespace irregularities.
license: MIT
---

# Trigger
The user provides raw text records concerning business relationships with logistics personnel that contain inconsistent whitespace, indentation, or non-standard characters.

# Input
- `text`: Raw string containing logistics personnel relationship notes.

# Output
- `text`: Standardized string with normalized whitespace and consistent character encoding.

# Effects
- Converts all non-standard whitespace characters to single spaces.
- Trims leading and trailing whitespace from each line.
- Ensures consistent UTF-8 encoding.

# Stop Condition
The text is processed such that no two consecutive whitespace characters remain and all line-start/end whitespace is removed.

# Known-Wrong Case
The method must not treat tab-indented documents as if the tabs were spaces; tabs must be explicitly handled or preserved according to the standardization rule rather than implicitly converted to spaces.

# Acceptance Check
Verify that a record containing mixed tabs and spaces is processed without losing structural intent while removing redundant trailing whitespace.
