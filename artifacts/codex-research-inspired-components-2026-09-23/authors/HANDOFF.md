# Research-inspired wikilink audit candidate

One original candidate, nine physical payload files, zero approvals and zero
served packages. The payload directory is `../audit_wikilink_resolution`; this
`authors` directory contains authoring/evidence material and is not a package.

## Why this method

The tools research proposed local-note link repair and Obsidian retrieval
experiments. This candidate supplies the missing deterministic step: scan a
declared Markdown wikilink subset, resolve file targets against an explicit note
inventory, and report missing or ambiguous targets with original source spans.
It provides a bounded operation beyond the prior inventory-difference,
dependency-closure and table methods. Existing CataloguePackage/factory/review
components retain preparation and admission ownership.

The method does not connect to Obsidian, read a vault, edit notes or validate
heading/block anchors. Its profile states what it scans and always returns
`complete_markdown_audit: false`. Clear first steps, dependencies, examples,
schemas and limitations are included in the package's AGENTS.md and profile.

## Exact inputs for the parent factory

- Package ID: `audit_wikilink_resolution`.
- Metadata: `metadata.json`, keyed by that ID.
- Current exact payload manifest: `frozen-manifest-v2.json`.
- Historical predecessor: `frozen-manifest.json` and
  `frozen-predecessor-v1/payload`; do not prepare it as the current candidate.
- Producer: Codex, family `openai`.
- Method identity: `codex_original_research_inspired_components/v1`.
- Declared effect: interpreter launch (`spawns_process`). The method itself is
  supplied-data stdin/stdout computation with no task-file or external effects.
- Dependencies: Python 3.10+ standard library only.
- Rights: original method/fixtures and first-party framing under the repository
  MIT notice; no third-party implementation or documentation body copied.

## Author evidence

`wikilink-contract-before-code.md`, input/output schemas, examples and 37
acceptance cases were written before the executable existed. The record
`contracts-first.json` binds those initial bytes. Later, three explicit dot-target
controls demonstrated that appending `.md` before validating the raw target
misclassified `.`/`..` references as missing notes. Their failed sandbox results
are preserved in `sandbox-before-dot-repair.json`; the earlier fixture body is
`cases-before-dot-target-controls.json`.

The repair validates the raw target path before adding a suffix. That predecessor
passed 40 author cases and all seven named algorithm/guard mutations in
`sandbox-final-frozen.json`. The preceding passing run is retained separately.
Mutants cover ambiguity, vault-root paths, fenced examples, escape parity,
unverified fragments, Unicode offsets and stale source digests.

All candidate executions used the existing Bubblewrap verifier: separate network
namespace, empty environment, read-only exact mounts, no task workspace or
credentials, 2 CPU seconds, 256 MiB memory and 4 wall seconds. Every successful
and refusal output is checked against the output schema. Markdown local links
resolve. No model, provider, email, server-start or deployment action occurred.

An independent agent froze 61 semantic cases from the contract before inspecting
the implementation; all passed. Its subsequent source review found one exact-line
mismatch: stripping all trailing carriage returns accepted a repeated-CR
frontmatter delimiter. Four controls, including standalone CR at EOF, failed in
`sandbox-crlf-before-repair.json`. The successor removes only the single CR
immediately preceding an actual LF. No contract was loosened.

The current frozen tree passes 44 author cases and eight mutations in
`sandbox-crlf-successor.json`, including a mutation restoring the overly broad
strip. The whole predecessor and its reports remain preserved. Independent
successor QA passed all 66 cases: the original 61 plus five line-ending controls.
Its two runs observed unchanged payload trees matching manifest v2, and source
review found no unresolved scoped defect. The report is
`../verification/WIKILINK-INDEPENDENT-QA-SUCCESSOR-2026-09-23.md`; evidence is
`wikilink-independent-successor-2.json` and
`wikilink-independent-crlf-successor-2.json` in that verification directory.
That QA still does not constitute independent catalogue admission or
native-harness qualification.

## Integration boundary

Use the parent's existing native preparation lane and independent admission
process. The instructions file is a portable starting surface to qualify, not a
claim that every harness automatically loads the package. The current node's
task, permissions and source material must still be explicitly composed. No
application source, branch, commit, served manifest or deployment was changed.
