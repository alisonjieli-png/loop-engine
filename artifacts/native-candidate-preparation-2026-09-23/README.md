# Original native package preparation and staging

Status: implemented operator-tool extension, pending root integration and full
repository checks. No items are approved or served. Worktree base is
`9c57c9a4c813578bffa504108ef9d785b308bb86`.

## Reuse and changes

The [existing preparer](../../tools/prepare_harness_candidates.py) now accepts
explicit version-two proposals holding complete native file trees. It reuses
the original source-revision, licence, tag, identity and bounded-batch checks.
The [small native extension](../../tools/native_harness_candidates.py) uses the
existing `CataloguePackage` contract for file paths, roles, sizes and digests.
The [existing staging tool](../../tools/stage_intelligence_candidates.py) verifies
those trees and writes only candidate records through `CatalogWriteBatch` and
`SQLiteRecordStore`. There is no new storage engine or executable runtime.

Each producer declares identity, model family and versioned method identity.
Rights and grounding remain explicit pending-review declarations. Dependencies
and effects travel with the package. An executable file role requires the
existing process-effect declaration. Native instruction files, plugin paths,
tools, Python scripts, JSON contracts and binary assets survive byte-for-byte.
No filename or declaration grants permission to execute anything.

The new version-three item/specification records deliberately fail old readers.
The independently assigned review adapter must read every file and bind verdicts
to its canonical package digest. Reviewing the manifest alone is insufficient.
See the [input and staging guide](../../tools/PREPARE-HARNESS-CANDIDATES.md).

## Concrete existing-package fixture

[Input](plugin-fixture-proposals.json) repackages the already authored Claude Code
plugin, including its command, agent, hook, Python tools, contracts and licence.
The [source binding](fixture-source-binding.json) pins the original inventory.

- One existing logical package, 13 payload files, 13 distinct payload digests.
- Zero `SKILL.md` files.
- Zero new logical-package count credit from this repackaging.
- Zero model calls, approvals, native installations or hosted releases.

The [prepared folder](prepared-plugin-fixture/items.json) holds one canonical
package document and the exact native tree. The [staging report](plugin-staging-report.json)
records an acknowledged atomic write, one candidate visible to review search,
and zero hits in normal search. The SQLite database is an isolated test artifact,
not the production service. No native tool or hook was executed in this lane.

## Checks and failures retained

| Record | Result |
| --- | --- |
| [Before implementation](tests-before-implementation.txt) | New complete-tree success checks failed against the old single-body preparer. |
| [Initial implementation](tests-after-initial-implementation.txt) | 20 checks passed, including eight reused original checks. |
| [Before contract repairs](tests-before-contract-repair.txt) | Three checks failed for producer method, strict JSON and the documented script import path. |
| [After contract repairs](tests-after-contract-repair.txt) | 23 checks passed. |
| [Before CLI binding repairs](tests-before-cli-binding-repair.txt) | Relative repository path and duplicate exception-class identity failed. |
| [After CLI binding repairs](tests-after-cli-binding-repair.txt) | 24 checks passed: 16 native checks and eight reused original checks. |
| [Owning lanes](tests-owning-lanes.txt) | 39 checks passed across native preparation, existing candidate staging and ingestion boundaries. |
| [Removed guards](removed-guards-final.json) | Six passing baselines and six detected removals: payload digest, process effects, package duplicates, full inventory, canonical document and closed effects. |

The [guard runner](check_removed_guards.py) uses disposable module copies and
refuses an existing report path. It never edits the production implementation.
The repository's complete integration checks remain the root session's gate.

## Limits

This is a preparation and candidate-staging mechanism. It does not establish
semantic originality, rights of every input, complete dependency resolution,
native loading or usefulness. Exact duplicate package identities are refused
within a batch, while semantic duplicates require independent analysis. Complete
trees remain with the prepared artifact folder; the catalogue contains their
references and metadata. Concurrent hostile filesystem changes and native
execution confinement are not qualified by these offline tests.
