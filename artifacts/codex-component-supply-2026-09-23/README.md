# Sixteen original Harness Working Directory Packages

Status: **16 candidate packages, 128 payload files, 113 distinct file hashes,
395,981 payload bytes, zero approvals and zero hosted items.** These counts
exclude authoring copies, canonical package documents, metadata and old attempts.

The owner assigned further deployments and application updates to Claude Code.
Codex authored this new supply in the shared project directory, using the
committed preparation/staging contracts at `231f51bb`. No additional Tactical/Hermes or other model API jobs were launched for this
batch. Authoring came from the current Codex session and its subagents. The pending Hermes endpoint
qualification remains separate.

## Prepared material

Use [prepared-v2/items.json](prepared-v2/items.json) and
[prepared-v2/packages/](prepared-v2/packages/) for exact-byte independent
admission and future integration. Preparation and engineering QA do not approve
or publish material. The authored directory contains auxiliary author evidence
under `authors/`; it is excluded from the explicit sixteen-package inventory.

Each package contains:

- `AGENTS.md` with purpose, first steps, invocation and limitations.
- A standalone Python tool using standard input and output.
- Two JSON Schema contracts, two JSON example files and verification cases.
- The repository MIT notice.

There are 16 Python tools, 80 JSON files, 16 instruction Markdown files and
16 licence files. There are no `SKILL.md` files in this cohort. Each tool can
be invoked directly by a host that supplies the required execution authority;
native harness loading remains unqualified. Compose package usage instructions
with the current task rather than overwriting that task.

## Package methods

| Identity | Purpose |
| --- | --- |
| `apply_flat_record_changes` | Check all expected-before states against one flat record, then return either every requested change or the untouched record with conflicts. |
| `apply_nonoverlapping_text_edits` | Apply a bounded batch of edits against the original string using Unicode-codepoint positions, optionally checking its exact UTF-8 SHA-256 first. |
| `assign_digest_shards` | Assign supplied IDs to a fixed shard count using the entire SHA-256 digest of each exact UTF-8 ID modulo the shard count. |
| `audit_half_open_interval_overlaps` | Find overlapping interval pairs, maximum simultaneous occupancy and union length while treating adjacency and empty intervals correctly. |
| `compare_file_inventories` | Compare two explicit file inventories by exact relative path and supplied SHA-256, size and executable metadata. Report changes without reading files or guessing renames. |
| `compute_weighted_quantiles` | Resolve weighted empirical-CDF quantiles with positive integer weights and exact decimal-string values; avoid interpolation and binary-float threshold drift. |
| `detect_portable_path_collisions` | Report exact, Unicode-normalization/casefold and parent-file path collisions under one explicitly named abstract comparison model. |
| `evaluate_capability_requirements` | Compare required and optional capabilities with supplied resolution and evidence levels without granting execution authority. |
| `paired_sign_test` | Compare candidate b against baseline a on paired bounded decimal measurements, with explicit ties, missing values and exact two-sided probability. |
| `profile_csv_structure` | Inspect an in-memory CSV extract before downstream transformation; report row-width distribution, baseline-column completeness, exact header issues and physical lines without opening a task file. |
| `reconcile_keyed_tables` | Pair two flat-record tables by typed keys, refuse duplicate identities, and report changed fields and unmatched row indices without a Cartesian join. |
| `reconcile_multiset_rows` | Compare two small flat-record collections while preserving duplicate multiplicity, field presence and JSON scalar type distinctions. |
| `render_focused_task_context` | Render a bounded task brief with explicit first steps, acceptance criteria and digest-bound structured state. |
| `resolve_selected_dependency_closure` | Find the transitive closure of selected exact package IDs and report cycles; refuse a missing reachable dependency without choosing versions or downloading material. |
| `select_context_blocks` | Preserve mandatory context and dependencies, then greedily admit optional blocks by explicit priority within supplied costs. |
| `validate_event_precedence` | Check strictly-before constraints against one supplied event-ID sequence, reporting missing IDs and order violations without inferring causality or using timestamps. |

## Engineering and retrieval evidence

- [Independent engineering QA](verification/independent-semantic-qa/INDEPENDENT-ENGINEERING-QA-2026-09-23.md): 190 cases pass across all sixteen packages; exact prepared file hashes match the independently checked trees. Two independently wrong algorithms are rejected.
- Two raw-number parser defects were reproduced and repaired: floating-point rounding/underflow could admit fractional costs as integers, and an extreme exponent on an exact zero caused an unnecessary refusal. Failed files and reports remain beside their successors.
- The CSV header precondition was clarified and rechecked without changing its algorithm.
- [Staging report](staging-report-v2.json): sixteen records committed to an isolated candidate catalogue through the existing atomic store boundary. Ordinary serving excludes all sixteen.
- [Independent query paraphrases](verification/retrieval-paraphrases-v1.json): 15 of 16 expected packages rank first and all 16 appear in the first three. The event-order query ranks second.
- Retrieval remains imperfect: two of four unrelated probes return weak matches. This is evidence for the existing relevance-floor work, not a claim that a small lexical index generalizes. No query or test called a model.

The source directory comparer and CSV profiler overlap earlier inspection
topics, but add executable transformations/measurements documented in the author
handoffs. This does not establish global semantic novelty.

## Search locally for review

The database is outside the repository at
`/home/username/.le-codex-research-cache/component-supply-20260923/candidates.db`.
It uses the existing catalogue contract. The following read-only wrapper uses
the existing Intelligence search boundary and explicitly includes candidates:

```bash
/home/username/.le-wave2/mcp-revision/.venv-mcp2/bin/python \
  artifacts/codex-component-supply-2026-09-23/review_search.py \
  --query "Fit background into a budget while retaining required context"
```

[staging-export-v2.json](staging-export-v2.json) preserves the staged records
without requiring access to that local database. Search results are references;
selected package bodies stay separately bound to exact digests.

## Admission and handoff

Claude can review the prepared bytes, reproduce the independent checks and
run the existing exact-byte admission workflow. Remaining gates include licence
scope, native profile/loading evidence, independent admission and relevant real
task acceptance. None may be inferred from file count, a successful subprocess
or this authoring report. The functional engine wrapping research and release
22 handoff are separate from this candidate batch.

The initial assembler used unregistered generic asset/reference role labels.
The factory refused it before materialization. The successor uses the current
explicit `other` role for standalone examples, cases and licence files. See
[the retained refusal](verification/preparation-refusal-v1.json). No production
contract was weakened or extended for this batch.
