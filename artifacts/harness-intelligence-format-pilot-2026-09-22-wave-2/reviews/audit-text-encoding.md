# Producer note: audit text encoding

State: candidate only. The author wrote the method, script and checks and cannot approve it. No independent review, customer distribution licence, native harness load, or real task outcome has been recorded.

## Exact delivery roles

- `SKILL.md`: activation description, command, limits and interpretation.
- `scripts/audit_text_encoding.py`: standard-library bounded byte and line analysis.
- `scripts/confined_input.py`: unchanged local confinement helper, reused from `artifacts/harness-intelligence-format-pilot-2026-09-22/tools/audit-csv-structure/scripts/confined_input.py`; the manifest records the exact digest.

The source is first-party generation and local code reuse, with no external text copied. Rights for customer distribution still need an explicit owner decision. The script requires Python 3.11 or later and POSIX no-follow file operations. It reads one regular input file, writes only a JSON response to standard output, and uses no network, credential or model.

Known-wrong controls include invalid UTF-8, mixed newline styles, NUL, oversized line, input symlink and attempted limit increase. A byte-order mark and trailing whitespace are reports, not failures. An independent reviewer should inspect interpretation of unusual Unicode separators, leading byte-order marks in the middle of a file, concurrent mutation and the caller's desired newline policy. A pass does not qualify the content or any later transformation.
