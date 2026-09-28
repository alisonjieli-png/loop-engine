# Detect abstract portable path collisions

Candidate harness intelligence. Native loading and usefulness are not qualified.

## Task

Report exact, Unicode-normalization/casefold and parent-file path collisions under one explicitly named abstract comparison model.

## First steps

1. Read `contracts/input.schema.json` and the semantic rules below.
2. Construct one bounded JSON request from supplied data.
3. With host permission to start the interpreter, run `python3 tools/detect_portable_path_collisions.py` and supply the request on standard input.
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

The model applies NFC, casefold, then NFC to each slash-separated segment. The returned Unicode database version is the runtime version; optional expected_unicode_version must match it. This is not NFKC, locale collation, NTFS/APFS/ext4 emulation, Windows reserved-name validation or a filesystem-security guarantee. Input paths are explicit files; a normalized path that prefixes another at a slash is a parent-file collision. Exact duplicates are accepted and reported by their original indices. Groups sort by normalized path; all ancestor/descendant pairs sort by (parent,child). More than 1024 parent-file pairs refuses as output_limit_exceeded. No directories, symlinks, permissions, case behavior or files on disk are inspected.

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
