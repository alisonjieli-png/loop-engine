# Compare supplied file inventories

Candidate harness intelligence. Native loading and usefulness are not qualified.

## Task

Compare two explicit file inventories by exact relative path and supplied SHA-256, size and executable metadata. Report changes without reading files or guessing renames.

## First steps

1. Read `contracts/input.schema.json` and the semantic rules below.
2. Construct one bounded JSON request from supplied data.
3. With host permission to start the interpreter, run `python3 tools/compare_file_inventories.py` and supply the request on standard input.
4. Check the exit code and `contracts/output.schema.json`; compare the result with the task's acceptance conditions.

The command returns one JSON line: exit 0 for a result, exit 2 for a refusal.
The input is at most 65536 UTF-8 bytes and 16 container levels. JSON duplicate
keys, nonfinite numbers, invalid Unicode scalars and unknown fields refuse.
Numeric literals are at most 128 characters; integral forms such as 1.0 and
1e0 are accepted without binary-float rounding. Booleans are not integers.
The output limit is 131072 UTF-8 bytes including its trailing newline; an
oversized result returns `output_limit_exceeded`. Schemas describe shape and
field bounds; wire limits and cross-field conditions are additional rules.

## Method and limits

Each side has at most 256 entries and distinct exact paths. Relative POSIX-style paths have no leading/trailing slash, empty segment, dot/dot-dot segment, backslash or control character; maximum 256 Unicode codepoints. Paths are compared case-sensitively without normalization. Output lists are sorted by Unicode codepoint order; changed fields use digest, size_bytes, executable order. Identical digests at different paths remain removal/addition, never a guessed rename. Supplied digests and metadata are not checked against physical files. Parent/file feasibility is not decided here.

## Authority and dependencies

Python 3.10 or newer, standard library only. The method reads supplied standard
input and writes standard output. It performs no task-file access, network
request, subprocess launch, environment lookup or dynamic import. The host's
interpreter launch is a separate `spawns_process` effect. Paths and labels are
data; no result grants execution, installation, publication or access authority.
No current workspace, package catalogue or live filesystem state is inferred.

## Verification

Use the synthetic example and `verification/cases.json`. Structural success
is separate from semantic usefulness and independent review. This candidate
is original Codex/OpenAI-family material under the repository MIT notice;
no third-party content is claimed licensed by that notice.
