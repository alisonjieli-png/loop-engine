---
name: text-standardization-data-cleaning
description: Use this skill to normalize and clean raw text data to ensure consistent formatting for downstream processing.
license: MIT
---

### trigger
When raw text inputs contain inconsistent whitespace, irregular character encodings, or non-standard formatting that disrupts data parsing.

### typed input
`text`

### typed output
`text`

### effects
- Normalizes all whitespace characters to a single space.
- Converts line endings to the standard `\n` format.
- Trims leading and trailing whitespace from the document.

### stop condition
The text has been processed such that all whitespace is standardized and no non-standard hidden characters remain.

### known-wrong case
A tab-indented document is normalized as if the tabs were spaces.

### acceptance check
Verify that a document containing a mix of `\t` (tabs) and spaces has all tabs converted to a single standardized space (or equivalent space-based indentation) rather than being treated as literal tab characters in a way that preserves the original width incorrectly.
