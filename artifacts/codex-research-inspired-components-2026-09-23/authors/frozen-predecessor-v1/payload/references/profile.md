# Bounded Markdown wikilink scanner profile

Profile: `bounded_markdown_wikilinks/v1`. Operation:
`audit_wikilink_resolution`. All comparison and output rules below are part of
the method contract. This is a lexical audit over supplied Markdown note text,
not an implementation of the full Obsidian or CommonMark renderers.

## Inputs and identity

Supply a source path, its text and at most 256 unique Markdown-note paths. The
source must occur in that inventory. Paths use forward slashes, end with `.md`
and have nonempty relative segments. Absolute, empty, dot/parent segments,
backslashes, ASCII controls, colon, hash, vertical bar and brackets are invalid.
Each segment must equal its stripped form. Unicode is compared literally; case,
percent-encoding and Unicode normalization are not changed. The inventory is
supplied evidence, not a claim about files present on any filesystem.

The strict JSON framing caps bytes and depth, rejects duplicate keys/nonfinite
numbers/unknown fields and requires valid UTF-8 and Unicode scalar values.
An optional `expected_sha256` binds the exact UTF-8 text. A mismatch refuses the
request before scanning. Input and output schemas describe the record shape;
path/source relationships and the additional rules here also apply.

## Scanned subset

The scanner walks original text without changing offsets. Line boundaries are
LF; CRLF is accepted for block delimiter lines. It skips these regions:

- A first line exactly `---` begins frontmatter; an exact `---` or `...` line
  ends it. An unclosed frontmatter section refuses the request.
- At line start, up to three spaces followed by at least three backticks or
  tildes begins a fence. A backtick opener's remainder cannot contain backticks.
  Closing fences use the same character, at least the opening run length and
  only trailing whitespace. An unclosed fence skips through the end of text.
- A line beginning with four spaces or a tab is skipped as an indented line.
  Continuation/block-container semantics are not inferred.
- HTML comments (`<!--` through `-->`) and Obsidian comments (`%%` through `%%`)
  are skipped when encountered outside code. Unclosed comments skip to EOF.
- Unescaped inline backticks skip through the next exact-length backtick run on
  that same line. Unmatched runs are literal. Multiline code spans are not parsed.

Quoted/list-nested fences, raw HTML blocks and a full Markdown AST are outside
the profile. Consequently every report carries `complete_markdown_audit: false`;
there is no blanket claim that all actual document links have been checked.

## Link spans and targets

Visible unescaped `[[` starts a link. An odd immediately preceding backslash run
escapes the opener; an even run does not. The next `]]` on that line ends the
link. A missing close or nested opening is an `unsupported` observation; its span
runs to the first same-line close, or to the line end when none exists. It is
consumed once, so a nested opener is not also reported as a valid independent
link. An unescaped `!` immediately before the opener marks a note embed. The
reported span includes brackets and excludes the optional exclamation mark.

`start` and `end` are zero-based, half-open Unicode-codepoint offsets into the
original text. `line` and `column` are one-based. `raw` is the inner source text.
An optional single pipe introduces a nonempty display label. The first hash
introduces a nonempty fragment, preserved verbatim. Multiple pipes, backslashes,
brackets or newlines inside a link are unsupported. There is no fuzzy correction.

A blank target with a fragment names the source note. Otherwise an optional
`.md` suffix is removed for comparison. Targets containing a slash compare to
the complete inventory path from the vault root. Bare targets compare to the
basename of every note. Zero matches are `missing`; one is `resolved`; multiple
are `ambiguous`, with sorted paths. No current-folder preference is guessed.
Dot-containing note names remain literal names. Attachment discovery and
verification are outside this Markdown-note-only inventory contract.

The fragment is `not_checked` whenever present, including heading and block
references; otherwise it is `absent`. The display label never contributes to
resolution. The tool makes no changes and returns no executable edit plan.
The output `target` preserves the supplied spelling, including an optional
`.md` suffix; the internal comparison key is not substituted into the report.

## Examples of decisive controls

`[[Plan]]` with `a/Plan.md` and `b/Plan.md` is ambiguous. `[[a/Plan]]` selects
only `a/Plan.md`, regardless of the source folder. `[[#Missing heading]]`
resolves the current note while leaving the fragment unchecked. An emoji before
a link adds one codepoint to its offset, not its UTF-8 byte length.

## Source basis and reuse

[Obsidian's internal-link documentation](https://obsidian.md/help/links) describes
the syntax that motivated this subset. Its folder links begin at the vault root,
and note links can carry display labels and heading/block references. The
[formatting documentation](https://obsidian.md/help/Editing+and+formatting/Basic+formatting+syntax)
describes code delimiters and comments. Sources consulted September 23, 2026.
No external implementation or documentation body was copied.

The implementation is original and uses Python's standard library. Strict JSON
framing reuses first-party Loop Engine candidate framing under the repository
MIT notice. A future fully compatible parser can be a separate qualified engine
behind a versioned edge; it must not silently reinterpret this profile.
