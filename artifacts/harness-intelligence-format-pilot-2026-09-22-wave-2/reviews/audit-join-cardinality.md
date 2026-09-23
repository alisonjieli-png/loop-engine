# Producer note: audit join cardinality

State: candidate only. The author of this package wrote the method, script and checks and cannot approve it. No independent review, customer distribution licence, native harness load, or real task outcome has been recorded.

## Exact delivery roles

- `SKILL.md`: search and activation description, command, limits and interpretation.
- `scripts/audit_join_cardinality.py`: standard-library computation of duplicate, blank, unmatched and projected join rows.
- `scripts/confined_input.py`: unchanged local confinement helper, reused from `artifacts/harness-intelligence-format-pilot-2026-09-22/tools/audit-csv-structure/scripts/confined_input.py`; the manifest records the exact digest.

The source is first-party generation and local code reuse, with no external text copied. Rights for customer distribution still need an explicit owner decision. The script requires Python 3.11 or later, POSIX no-follow file operations and a stable materials snapshot. It reads at most two regular files within the declared root, writes only a JSON response to standard output, and uses no network, credential or model.

Known-wrong controls include a many-to-many row explosion, blank keys on both sides, missing required match, duplicate header, ragged row, ancestor symlink and attempted limit increase. An independent reviewer should test exact bytes, Unicode header/key edge cases, concurrent mutation and how the caller chooses the join expectation. A pass establishes counts under those inputs; it does not establish business semantics or permission for a subsequent join.
