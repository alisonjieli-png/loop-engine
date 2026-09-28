# Audit wikilink note targets

Use this package when a step needs to find missing or ambiguous Markdown note
targets before proposing changes to a supplied knowledge-vault document.

## First steps

1. Read [the exact scanner profile](references/profile.md). Confirm that a
   Markdown-note-only lexical audit fits the task. This does not run Obsidian.
2. Have the caller supply the source note text, its exact relative path and the
   allowed note-path inventory. The tool does not discover or read files.
3. Build one JSON object matching [the input contract](contracts/input.schema.json).
   Use the UTF-8 source digest when the result will inform a later edit.
4. Within the harness's authorized process sandbox, run
   `python3 tools/audit_wikilink_resolution.py < examples/input.json` for the
   synthetic example, then supply the actual request through standard input.
5. Compare the example to [the expected result](examples/output.json). Inspect
   `missing`, `ambiguous` and `unsupported` entries before proposing repairs.

## Interpretation

The method reports exact candidate note paths and original Unicode-codepoint
spans. A bare name can be ambiguous even when a same-folder note exists. A slash
path begins at the supplied vault root. Identity is case-sensitive and does not
normalize Unicode. A display label is not a note alias. Heading and block
fragments are always marked `not_checked`; finding a note does not validate them.

`complete_markdown_audit` is always false. This bounded scanner covers the
published subset and must not be presented as a complete Obsidian/CommonMark
validator. Attachments, YAML aliases, raw HTML semantics, nested container fences
and multiline inline-code parsing need a separately qualified parser/profile.

## Runtime and limits

Requires Python 3.10 or later and only standard-library modules. Launching the
interpreter requires the harness's process permission. The method performs no
network request, task-file read/write, credential lookup or subprocess call.
It consumes one UTF-8 JSON document on stdin and returns one JSON line on stdout.
The contract caps input at 64 KiB, text at 32,768 codepoints, paths and links at
256 each, and output at 128 KiB including the newline. Exit 0 is a report, which
may contain unresolved links; exit 2 is a typed refusal. Errors are specified in
[the output contract](contracts/output.schema.json).

Nothing in a report grants permission to rename, create or modify a note. A
later editing step must independently check authority, source digest and intended
target. The package does not carry that step's task assignment automatically.

This is original candidate material. Sandbox checks and fixtures are evidence
for this exact method, not catalogue approval or native-harness qualification.
