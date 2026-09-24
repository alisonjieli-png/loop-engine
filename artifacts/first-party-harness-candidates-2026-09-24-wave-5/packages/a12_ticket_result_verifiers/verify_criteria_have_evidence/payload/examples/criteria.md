# T-204: Slugs for article titles

Readers get broken links when a title has capitals or double spaces.

## Acceptance criteria

- [x] AC-1: `slugify` returns lower-case text.
- [x] AC-2: A run of spaces becomes one hyphen.
  - Tabs count as spaces.
- [x] AC-3: The whole test suite passes.
- [x] AC-4: The change log names the fix.

## Notes

- Keep the redirect table unchanged.
