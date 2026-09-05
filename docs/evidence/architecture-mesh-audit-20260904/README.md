# Architecture mesh audit evidence

This bundle supports the
[architecture and corpus audit](../../verification/ARCHITECTURE-MESH-CORPUS-AUDIT-2026-09-04.md).
It describes the dirty checkout at HEAD
`22ee44052b027ba96ce50c37e4cc6a659e1b91c8` on 2026-09-04.

These files are audit outputs, not intelligence candidates, runtime profiles,
promotion decisions, or evidence of a successful live model run. No embedded
historical instruction is current authority.

## Inventory and reading coverage

| Artifact | Meaning |
|---|---|
| [summary.json](summary.json) | Frozen input counts, revision, times, exclusions, and manifest hashes |
| [files.jsonl](files.jsonl) | Every in-scope input file, digest, size, text/AST scan, and structural markers |
| [commits.jsonl](commits.jsonl) | All 158 local commit objects, reachability, metadata, paths, and automated patch scans |
| [excluded.jsonl](excluded.jsonl) | Explicitly excluded directories and other exclusions |
| [markdown-semantic-coverage.json](markdown-semantic-coverage.json) | Full-text reading coverage of all 280 input Markdown files, with exact source hashes |
| [external-prompts.json](external-prompts.json) | Four explicitly registered external prompt files, hashes, headings, and automated inspection |
| [external-guidance-coverage.json](external-guidance-coverage.json) | Full semantic coverage of all four external files, including exact repeated-text and base-plus-diff mappings |
| [registered-conversation-sources.json](registered-conversation-sources.json) | Eight registered sessions with 116 user-text parts, plus three exact registered fragments, counted and hashed without their bodies |
| [source recheck](source-recheck-before-report-index-edits.json) | All 1,502 original input files unchanged before report-index edits |
| [environment](environment-at-publication.json) | Branch, HEAD, worktrees, dirty paths, and process names/working directories; no process arguments or environment values |
| [bundle-manifest.json](bundle-manifest.json) | Hashes of published evidence artifacts; excludes its own hash |

Full automated inspection does not mean full semantic reading. The Python
inventory parsed structure but did not independently verify every function.
The commit inventory read full patches automatically; selected changes
received detailed review. Binary assets were hashed, not viewed.

The 116 session user-text parts contain 3,813,127 bytes and 143,564 lines.
The three separately selected fragments contain 58,334 bytes and 2,270 lines;
these are selected occurrences, not a deduplicated novelty count.
They were selected only through the repository's reconciliation register.
Their enumeration does not establish full semantic review of conversations.
Private reasoning, tool bodies, unrelated chats, and raw user text are not
exported in this bundle.

## Findings and source reviews

| Artifact | Scope |
|---|---|
| [Commit-history review](commit-history-audit.md) | Historical changes, superseded claims, selected diffs, and coverage limits |
| [Reachable commit list](commit-inventory-reachable.json) | The 131 commits reachable from current local refs |
| [Additional commit list](commit-inventory-additional.json) | The 27 additional reflog-only or unreachable local commit objects |
| [Guidance and component review](guidance-component-audit.md) | Prompt, reference, component, and glossary findings |
| [Outside-docs Markdown review](other-markdown-audit.md) | All 109 Markdown files outside `docs/` |
| [Remaining docs review](remaining-docs-audit.md) | The other 111 documents assigned for full reading |
| [External guidance review](external-guidance-audit.md) | Four registered historical master prompts, authority conflicts, and proposed architectures |
| [Lineage and integration review](lineage-subject-audit.md) | Exact scope of the reproduced subject-binding and integration defects |

Review notes preserve their original temporary source paths. The corresponding
portable artifacts are linked here. Original per-file citations refer to the
input snapshot, before the small audit pointers were added to documentation.

## Reproduced defects

The [probe](lineage-subject-probe.py) calls the real verification producer
with an injected response. It then attempts to credit result A using the
genuine evaluation of result B. The boundary accepts that mismatch in the
inspected checkout. It also demonstrates retention of rejected artifacts and
an unchecked result index.

Run from the repository root with the exact inspected dirty source present:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 docs/evidence/architecture-mesh-audit-20260904/lineage-subject-probe.py
```

The [observed output](lineage-subject-probe-result.json) is a defect
reproduction, not a passing product proof. It makes zero provider calls.
Its use of repository-private test helpers means a later code fix may change
or refuse the probe; preserve this saved result as historical evidence.

The [model ladder probe](model-ladder-probe.py) demonstrates that one known
success plus eleven unknown outcomes sets `ModelLadder.proven` to true.
Its [observed output](model-ladder-probe-result.json) establishes a bootstrap
sample-sufficiency weakness, not a live routing or model-quality result.

[Delivery validation](delivery-validation.json) records rerun probes, source
preservation checks, artifact parsing, local links, and Markdown lint.

## Fresh diagnostic checks

[Conformance](conformance.json) passed 27 zero-tolerance gates over 405
files and validated 69 registered operational boundaries.
[Repository assurance](assurance.json) returned
`PASS_WITH_DOCUMENTED_WARNINGS`, with zero hard findings and 225 API-shape
warnings. That warning policy scanned 411 files and 3,295 callables.

The [check driver](checks.py) shows the exact APIs used. It was run with the
repository source and `devtools/src` on `PYTHONPATH`. Its original output
directory is deliberately retained in the archived script. `run_conformance`
regenerates the package conformance report; that file matched the input
snapshot afterward. These checks do not execute the full self-test suite.

The [inventory driver](inventory.py) preserves selection and scan rules.
It is an audit utility, not a new Loop Engine service. It reads all local
commit objects, including abandoned snapshots, without checking out or
executing historical code.
