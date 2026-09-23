# Mixed-format harness intelligence candidate pilot

Kind: dated candidate-only verification, September 22, 2026 local time.
The owner clarified that harness intelligence is not limited to Markdown
skills. The [isolated format pilot](../../artifacts/harness-intelligence-format-pilot-2026-09-22/README.md)
contains **six logical candidates** and an
[exact-file manifest](../../artifacts/harness-intelligence-format-pilot-2026-09-22/manifest.json)
for **52 physical source, rendering and review files**. Its manifest
SHA-256 is
`12f41d188e0022a0ff16132f3ffce14f0378639d50e00cc53467291aef50f000`.
Many physical files are tests, notes or alternative client renderings,
not extra intelligence methods. The version-two candidate manifest assigns
file roles: 28 delivery paths, two canonical connection-source paths, four
review notes, five tests, seven receipts and six local support files. The 28
delivery paths include repeated client layouts; they are not 28 unique
capabilities or 28 approved files. The starting revision `0d1f883` does
not contain these uncommitted bytes.

## Six different logical candidates

| Candidate kind | Logical items | Physical behavior observed |
|---|---:|---|
| Native step instructions | 2 | Ten `AGENTS.md` and `CLAUDE.md` client-rendering files. Static layout/digest check passed; Codex 0.155.1 included unchanged copies in a fresh isolated no-model prompt input. No task placeholders were rendered and the other clients have no exact-byte native-load result. |
| Agent Skills with real Python tools | 3 | Each has `SKILL.md`, a deterministic script, a confined-input helper and tests. Forty focused tests pass. A separate reviewer reproduced initial serious path and number failures, then reran them against repaired bytes without a new candidate-retention blocker. Native harness invocation and customer benefit are unmeasured. |
| Local protocol connection and server | 1 | One read-only JSON-shape server with three alternative JSON or TOML client layouts. The Python protocol client negotiated `2025-11-25` and listed/called one tool without a model. OpenCode 1.x failed to connect with generic `python3` in a clean home; it connected in a successor trial only after a temporary pinned interpreter was provisioned and the command was changed. Codex and Claude native activation, Pi extension support, and `2026-07-28` are unqualified. |

The [logical catalogue](../../artifacts/harness-intelligence-format-pilot-2026-09-22/candidate-items.json)
keeps those six identities separate from their source files and
client-specific delivery variants. A [local metadata search](../../artifacts/harness-intelligence-format-pilot-2026-09-22/search_format_candidates.py)
checks the current file manifest and catalogue before returning paths,
digests and descriptive fields. A result filtered to Codex does not
return Claude `.mcp.json` or OpenCode `opencode.json` as files to install.
An unfiltered result requires a client variant selection. The catalogue
records `approval_state: none` and customer distribution licence pending.
The local search is not a customer endpoint or authorization boundary.

## Checks and saved failures

| Check | Observed result | What remains unproven |
|---|---|---|
| Context candidate checker | Two logical templates, ten native files, two local Claude imports and current digests pass | Actual rendered task, model use, and native loading in Claude, OpenCode or Pi. |
| [Codex context probes](../../artifacts/harness-intelligence-format-pilot-2026-09-22/context/README.md) | Initial nested-repository attempt did not show the marker; isolated fresh-root successor did. A separate `CODEX.md` control was absent under default settings and present after an explicit fallback setting. | `CODEX.md` is not the default instruction file, and prompt-input inclusion is not task use. |
| Python tool checks | 13 CSV, 16 JSON Lines and 11 digest-inventory tests pass, including repaired ancestor symlink, numeric precision, FIFO and entry-bound cases | Runtime authorization, bind-mount/hard-link provenance, concurrent snapshot consistency and independent customer task evaluation. |
| Local protocol server and config checks | Three server tests, four config tests and nine rendered-layout files pass. Saved failed and successor OpenCode connection receipts remain beside each other. | Provisioned customer runtime, Codex and Claude native binding, modern protocol revision and model use. |
| Heterogeneous manifest and search checks | Four manifest tests and nine local metadata-search tests pass; manifest validates 52 exact files, excludes generated caches, and refuses review notes, test receipts and files from another client's layout in a delivery variant. Both known-wrong mutants failed before repair. | Independent approval, rights, secret review beyond the bounded pilot, hosted search relevance and grants. |
| Ruff and Markdown lint | Candidate Python checks pass; 19 selected Markdown files show zero lint issues | Semantic correctness or security approval. |

The [connection review](../../artifacts/harness-intelligence-format-pilot-2026-09-22/connections/json-shape-stdio/REVIEW.md)
explains the dependency failure: the failed listing alone said
`Connection closed`; a same-source clean-home command separately
recorded `ModuleNotFoundError`. The successful trial's receipt records
Python and `mcp==1.29.0` versions, a modified interpreter command and
its config digest. It does **not** prove the canonical `python3`
configuration works after deployment. The old failed attempt and new
receipt were kept under different names.

## Admission and placement boundary

The [file-kind guide](../research/HARNESS-INTELLIGENCE-FILE-KINDS-AND-ADMISSION-2026-09-22.md)
and [placement report](../research/NATIVE-HARNESS-INTELLIGENCE-PLACEMENT-2026-09-22.md)
map each format to its native discovery and effect gate. A skill folder
with Python scripts is one multi-file candidate. A single connection
server rendered for three clients is one candidate with three layouts.
The active hosted catalogue still admits only independently reviewed
exact bytes under a customer licence and typed effect policy. None of
these six packages has that decision. The local result says what a
reviewer can inspect, not what a customer can fetch or run.

Claude Code should preserve the package boundary, all file digests,
dependency and runtime versions, client trust, relative paths and
source rights when adapting these candidates. In particular, existing
single-Markdown preparation cannot qualify the Python script or a
protocol configuration by reviewing `SKILL.md` alone. Offered, placed,
discovered, loaded, used and independently verified remain separate
facts. The [roadmap](../roadmap/roadmap.yaml) remains the only task
authority.
