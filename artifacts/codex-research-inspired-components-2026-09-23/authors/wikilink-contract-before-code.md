# Wikilink audit: decision and contract before implementation

Operation: `audit_wikilink_resolution`. Original producer: Codex, OpenAI family,
method identity `codex_original_research_inspired_components/v1`. Candidate only.

The current sixteen supplied-data components have no Markdown link scanner or
note-target resolver. The prior systems duplication review records eighty skills,
nine mixed packages and twelve native methods; their inventory, dependency and
graph methods do not implement this behavior. A focused search of those local
candidate populations found no `wikilink`, `wiki-link`, `dangling-link` or Obsidian
method. This is a gap in executable note-maintenance support, inspired by the
local-notes/Obsidian opportunities in the completed tools research.

Owner/reuse: the existing native package factory and CataloguePackage retain
preparation/admission ownership. No runtime, store or deployment changes. Reuse
the first-party strict JSON framing and sandbox verifier from the six systems
packages. Use Python standard-library string operations, regular expressions,
hashlib and JSON; no added library or server. Do not copy an external parser.

Primary [Obsidian links](https://obsidian.md/help/links) document wikilinks,
optional `.md`, vault-root folder paths, display labels and heading/block
fragments. [Formatting](https://obsidian.md/help/Editing+and+formatting/Basic+formatting+syntax)
documents code and comments. The method uses a declared smaller scanner profile.
It does not claim Obsidian runtime qualification or full Markdown parsing.

## Contract

Input is one strict bounded JSON object:

- `record_type`: `audit_wikilink_resolution_request/v1`.
- `syntax_profile`: `bounded_markdown_wikilinks/v1`.
- `source_path`: exact Markdown note path included in `note_paths`.
- `text`: supplied note text, at most 32,768 Unicode codepoints.
- `note_paths`: at most 256 unique relative POSIX note paths ending `.md`, each
  at most 256 codepoints; no empty/dot/parent path segments, backslash, ASCII
  control, colon, `#`, `|`, `[` or `]`. Each segment equals its stripped form.
- Optional `expected_sha256`: exact lowercase digest of UTF-8 text.

Wire framing reuses 64 KiB input, 128 KiB output, depth 16, duplicate-key and
nonfinite rejection, valid UTF-8/scalar strings and closed fields. No input
number fields exist. Unknown or incompatible profile refuses before scanning.

Mask frontmatter only when the first line is exactly `---`, until an exact
`---` or `...` line (unclosed refuses). Mask root-level fences with at most three
leading spaces, three or more matching backticks/tildes; an equal-or-longer
same-character closing fence has only trailing whitespace. Unclosed fences
mask through EOF. Mask each line starting four spaces or a tab, HTML comments,
Obsidian `%%` comments and paired exact-run backtick spans on the same line.
Unclosed comments mask through EOF; unmatched inline backticks stay literal.
This is a specified lexical profile, not full Markdown. Quoted/list-nested
fences, multiline inline spans, raw HTML blocks and escaped delimiters inside a
link are outside its claim. Report `complete_markdown_audit: false` always.

Find visible unescaped `[[...]]` pairs in order; content cannot cross a line.
Escape means an odd immediately preceding backslash run. Optional unescaped `!`
before `[[` marks a note embed. Source span includes brackets but excludes `!`.
At most 256 links; nested openings or missing same-line closing brackets produce
an `unsupported` entry. Never silently fix invalid syntax.

Split at one optional `|` display label, then first `#` fragment. Multiple pipes,
backslashes, bracket nesting, blank labels/fragments and invalid path syntax are
unsupported. A blank note target with a fragment means the source note. A path
with `/` addresses the vault root exactly; a bare target matches every supplied
note basename. One optional `.md` suffix is stripped before matching. Do not
casefold, normalize Unicode, percent-decode, use aliases or pick a preferred
folder. For zero/one/many candidate notes return missing/resolved/ambiguous.
The inventory contains Markdown notes only, so attachment verification is out
of scope. Names containing a dot before the optional `.md` remain literal note
names; do not infer media behavior from them.

Output includes record/profile/source/text digest, ordered links with original
codepoint spans, one-based line/column, raw inner content, target, nullable
fragment/display label, embed flag, status, sorted candidate note paths and
reason. Fragment status is `not_checked` when present, otherwise `absent`.
Counts report resolved/missing/ambiguous/unsupported separately. There is no
global “all links valid” or edit instruction. Error objects are exactly
`{"error":"CODE"}`, exit 2. Success exit 0. Output is a report, never authority.

## Known-wrong cases to detect

1. Choosing the first duplicate basename instead of returning ambiguity.
2. Treating a slash target as relative to the source directory.
3. Counting a link inside a fenced/inline code example or comment.
4. Treating an escaped bracket pair as active, or an even escape run as escaped.
5. Casefolding or Unicode-normalizing note identity without an explicit policy.
6. Verifying a heading merely because its note exists.
7. Offsets measured in UTF-8 bytes instead of original Unicode codepoints.
8. Parsing stale text after the optional expected digest no longer matches.
9. Accepting path traversal or unknown input fields.

The examples, schemas and acceptance cases are written before the executable.
Root owns eventual candidate preparation/indexing; independent review and client
loading remain separate from sandbox execution.
