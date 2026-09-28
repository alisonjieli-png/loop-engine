# Independent wikilink component QA: initial frozen package

Scope: original `audit_wikilink_resolution`, declared
`bounded_markdown_wikilinks/v1`. This review tests its lexical contract, not full
Obsidian or CommonMark equivalence. The producer and reviewer are separate Codex
processes in the same OpenAI family; this is engineering QA, not the independent
model-family admission quorum.

## Evidence

- Nine payload files were frozen in `authors/frozen-manifest.json` before testing.
- Executable SHA-256:
  `4d7549e59c4fa658c6e499c82bd8ab1acb8956e596a0f5b87e790e1ec5e3e433`.
- Profile SHA-256:
  `07bcc3423bd901cc079d5382fc833bc3dc9af57a220a24dfae709ed31926d48a`.
- 61 independent cases were written from the contract and schemas before reading
  implementation source. All 61 passed in
  [wikilink-independent-execution-1.json](wikilink-independent-execution-1.json).
- The full payload tree was unchanged during execution. Every successful output
  was checked against the schema, source digest, codepoint span/line/column
  invariants, exact candidate paths and status counts.

The corpus covers duplicate basenames without folder preference; vault-root paths;
literal Unicode/case/percent/dotted-name identity; optional `.md`; unchecked
fragments; escaped openers/embed markers; fence run lengths; inline/comment
precedence; CRLF delimiters; invalid input framing; stale source digests; 256-link
and output-byte boundaries.

Candidate bytes ran only through the existing qualified `sandbox.run_bytes`
helper, using the canonical `library_ingestion.processes.run_command` owner.
Bubblewrap unshared the network and exposed no host home. CPU was limited to two
seconds, address space to 256 MiB, wall time to four seconds per case, and each
output capture to 131,073 bytes. Package output was independently required to stay
within its declared 131,072-byte ceiling. No provider/model call occurred.

## Confirmed finding

Static follow-up found `.rstrip("\r")` removing all trailing carriage returns
before testing frontmatter markers. The declared profile admits exact delimiter
lines, accepting CRLF line endings. Repeated CRs are not a single CRLF ending.

Both cases in
[wikilink-independent-crlf-execution-1.json](wikilink-independent-crlf-execution-1.json)
failed against the same unchanged payload:

1. `---\r\r\n[[Shown]]` was incorrectly treated as an unclosed frontmatter block;
   the first line is not an exact opener, so the visible link should be reported.
2. `---\nkey: value\n---\r\r\n[[Shown]]` incorrectly accepted a malformed closer;
   it should refuse with `unclosed_frontmatter`.

The author confirmed this mismatch and is preparing a preserved successor.
Additional independent controls cover lone CR at EOF and an exact closer at EOF,
so repairing repeated CRs must not introduce another line-ending interpretation.
The finding is a boundary defect in the declared subset; it does not require a
broader Markdown parser.

## Static scope observations

The implementation uses standard-library JSON/string/regex/hash operations and
stdio. It does not perform task-file I/O, network requests, subprocess invocation,
credential access or note edits. Input bytes, text length, inventory size, links,
nesting and encoded output are explicitly bounded. Code and comments are scanned
without normalizing the source string. Missing/ambiguous/unsupported states and
unchecked fragments remain visible. No other algorithm/effect defect was found
in this bounded review; this is not an exhaustive proof.

Status: **successor required for the confirmed delimiter defect**. No package
approval, serving, installation, or native harness loading was performed.
