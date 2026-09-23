# Producer note: audit ZIP package

State: candidate only. The author wrote the method, script and checks and cannot approve it. No independent review, customer distribution licence, native harness load, or real task outcome has been recorded.

## Exact delivery roles

- `SKILL.md`: activation description, command, limits and interpretation.
- `scripts/audit_zip_package.py`: standard-library central-directory screen with bounded archive and expansion claims.
- `scripts/confined_input.py`: unchanged local confinement helper, reused from `artifacts/harness-intelligence-format-pilot-2026-09-22/tools/audit-csv-structure/scripts/confined_input.py`; the manifest records the exact digest.

The source is first-party generation and local code reuse, with no external text copied. Rights for customer distribution still need an explicit owner decision. The script requires Python 3.11 or later and POSIX no-follow file operations. It reads one regular archive file, extracts nothing, writes only a JSON response to standard output, and uses no network, credential or model.

Known-wrong controls include traversal, duplicate and portable-equivalent names, nested reserved Windows names and colon streams, trailing dots and spaces, symbolic links, unsupported Unix special files and privileged modes, declared expansion, deep paths, a high entry-signature count, a file used as a parent directory, an invalid archive, an input symlink and attempted limit increase. The large-entry test runs under a 96 mebibyte address-space cap, and the deep-path test has a five-second deadline. A valid one-entry ZIP with more than 5,000 matching byte sequences in its member payload must return an unknown-screening refusal, not a finding that the archive is unsafe or has too many entries. The script does not decompress entries, verify their checksums or establish that a passing archive is safe to execute. An independent reviewer should inspect ZIP parser edge cases, extraction behavior under the intended later extractor, archive metadata consistency and the resource ceiling in a sandbox.
