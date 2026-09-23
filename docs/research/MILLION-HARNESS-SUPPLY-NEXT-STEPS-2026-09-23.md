# A measured path toward a million harness files

Kind: September 23, 2026 research and offline audit at detached revision
`abcad4f8`. This page maps findings to the existing
[roadmap](../roadmap/roadmap.yaml). It does not approve an item, change the
served catalogue, authorize an outside download, or promise a date for a
million files. The [audit tool and exact reports](../../artifacts/million-harness-supply-audit-2026-09-23/README.md)
are available for a later session to rerun after the current worktrees merge.

## Count the right things first

The owner's milestone in [S-6.40](../roadmap/roadmap.yaml) is 10,000 distinct
approved, active logical packages, followed by 100,000. The owner also wants
millions of useful harness files. One package may contain instructions, code,
references, assets and client configuration. Client layouts and model wording
are variants of a method until the method, effects or acceptance check differs.
The count of distinct, approved, installable files must therefore be reported
beside the package count, never used to inflate it.

```text
Supply denominators
├── Source opportunities and discovered references
├── Candidate logical packages and their physical payload paths
├── Exact distinct payload bodies and possible near-duplicate methods
├── Independently approved exact package versions
├── Active, authorized, searchable and fetchable versions
└── Native discovery, use and independently verified task benefit
```

The [offline report](../../artifacts/million-harness-supply-audit-2026-09-23/README.md#saved-observations)
verified every local candidate payload digest in its supported manifests. Its
counts describe repository records, not a live customer journey.

| Measure at `abcad4f8` | Observed | What it does not mean |
|---|---:|---|
| Local logical package records | 212 | Some remain only first-party drafts. |
| Starter catalogue records | 123 | Its 73 distinct cited source references are not 73 outside publishers. |
| Recorded approved starter versions, also in the packaged host manifest | 43 | The offline audit does not read the live release pointer or customer grants. The [saved catalogue release record](../architecture/CATALOGUE-RELEASES-AND-HOT-SWAP-2026-09-22.md#the-first-live-run-and-the-isolation-repair) last names 43 served items. |
| Starter items rejected or not reviewed in the current review record | 6 rejected; 74 not reviewed | An old or unmerged decision does not change these states. |
| Isolated first-party candidate packages | 80 single-file skills and 9 mixed-format packages | None is independently admitted. Native layout files are not proof of use. |
| Physical local payload paths across these 212 records | 240 | Some paths are alternative client renderings or copies. |
| Distinct exact payload SHA-256 digests | 225 | Byte distinctness does not establish method distinctness, rights or quality. |
| Client-specific layout variants in the first mixed-format batch | 23 variants, 55 file bindings | They are six logical packages, not 23 or 55 methods. |
| Current nonapproved review queue | 169 | Every queue row says `approval_ready: false`. |

The exact duplicate report shows one confined-input helper copied into six
candidate packages. Several other duplicates are alternative client copies of
one method. This is why the 240 path count cannot be the library headline.
The 43 packaged host bodies are one Markdown file each; their eligibility as
native installed and helpful material still needs separate client and task
evidence.

## New work that is real but not yet admitted

The unmerged outside ingestion run (saved at
`/home/username/.le-library/ls1/artifacts/library-ingestion-2026-09-23/run-report-2.json`,
SHA-256 `881fc9f2154b329c566d02ff0e36dedb42f3bd896f3dabffacbffeff35f32332`)
at revision `0f7ae1f` read 20 pinned repositories and the official Model
Context Protocol Registry. Its second run reported 4,790 discovered entries,
4,049 candidate references and 3,251 rows staged in an isolated database.
The staged set comprised 596 skills, 445 instruction files and 2,210 protocol
connection records. The run refused 511 skills that referred to bundled files
or modules it could not yet carry as complete packages. Its first run is a
predecessor, not another population to add. The audit's
`outside_ingestion_reports` field gives these references **zero approval and
zero native-file credit**. Source records, link-only registry entries and
isolated staging rows are not added to the 212 local package records.

The unmerged independent panel pilot (saved under
`/home/username/.le-library/ls2/artifacts/candidate-review-pilot-2026-09-22`)
put 30 starter items to reviewers. It recorded 30 rejections, no approvals,
14 items with opposing reviewer decisions, 91 item calls and 32 calibration
calls in the completed attempt. The completed run used about 33,600 reported
tokens per item. Its four calibration cases per reviewer cannot establish a
low false-approval rate across file kinds and risk classes. Running that panel
faster would not turn the current 30 items into approved supply. Its findings
on incomplete promises, source claims and effect declarations are candidate
repair inputs under S-6.63 and S-6.45.

A more serious review conflict is now reproducible. The
[morning status review](../verification/CLAUDE-AND-ROADMAP-STATUS-2026-09-23-MORNING.md)
preserves the original comparison. A historical starter
review version one, saved in Claude's `wf_2c5a17d0-bee-4` worktree,
has SHA-256 `043f92e36a4bde89b5d816c9dbcc31435a1a626c28f91f96c2c60c341497b9ef`.
The later panel record, saved in the `ls2` worktree,
has SHA-256 `22f3fb23c41d93cca99ec76c648e9e6d3cb24cf2d201c71aa56670d45f2dab31`.
They give opposite outcomes to 29 of the same items. For all 29, each
record's reviewed body still exists in its worktree and matches its recorded
digest; the two bodies match after replacing only the literal closing
catalogue revision line. The
[review-dispute report](../../artifacts/million-harness-supply-audit-2026-09-23/README.md#saved-observations)
places those 29 on an adjudication hold. It does not carry the old approval
across revisions or convert the newer rejection into an approval. Historical
approval records for 42 other nonapproved current items also stay outside the
current source of truth. None of the proposed additional approvals is ready
for a release until the contradictory criteria and item defects are resolved
against the exact current bytes.

## Serving changed, but a million is still unqualified

The earlier [million-scale review](MILLION-SCALE-HARNESS-INTELLIGENCE-ADMISSION-2026-09-22.md)
described a two-megabyte host manifest and a search index rebuilt per request.
The service now has a content-addressed body store, versioned catalogue
release records and an active pointer, a reusable view per release, sparse
release-following grants and a hot swap. The two-megabyte limit remains on the
small host or bundle header. The current bundle's item list is line-oriented,
with a 65,536-byte limit per item line and at most 200,000 items in one bundle.
This removes the old single-host-manifest ceiling, but does not qualify a
million-item release or one million simultaneous customer-visible results.

The saved [synthetic 100,000-item service measurement](../../artifacts/catalogue-release-scale-2026-09-22/scale-measurement-100000-local-1.json)
needed about 1.4 GiB resident memory to build one served view and about
2.0 GiB during a swap. It took 59.31 seconds to build the first view and
64.76 seconds to swap. The 40 lexical search samples had a 187.2 millisecond
95th percentile; the 40 hybrid samples had a 787 millisecond 95th
percentile. Bodies occupied about 592 MiB of allocated disk blocks. These
are synthetic local measurements on one workstation, not hosted capacity or
search-quality proof. One million items require another index and body-store
engine, bounded listing, tenant isolation, withdrawal checks and a measured
update path before a scale claim.

The new [audit scale probe](../../artifacts/million-harness-supply-audit-2026-09-23/README.md#saved-observations)
processed one million **metadata rows** across five disposable prospective
bundle files under a 768 MiB address-space limit. It took 19.898 seconds and
the worker process peaked at 43,532 KiB resident. The file digest was repeated
one million times, so it correctly reported one distinct file body and zero
active-release credit. This measures the temporary offline counting procedure
only. It has no package blobs, approvals, native harness tests or task results.

## Source strategy and admission work

The [official Model Context Protocol Registry](https://modelcontextprotocol.io/registry/about)
is metadata for publicly accessible servers, including execution commands,
environment variables and remote addresses. It is in preview and delegates
server-code security scanning to package registries and downstream curators.
Its [aggregator guide](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/registry-aggregators.mdx)
describes cursor pagination, update filters and changing server status. The
existing unmerged importer should own this lane. A registry row is a source
reference or a reviewed connection candidate, never an automatically enabled
server or a copied upstream code package. A deletion or rights change needs
an exact reconciled source snapshot before it changes availability.

The [Agent Skills specification](https://agentskills.io/specification) allows
`SKILL.md` with scripts, references and assets and describes progressive
loading. S-6.40 should upgrade the first-party and outside candidate paths to
preserve every bundled file, path, dependency and digest. A skill that needs a
script must not be admitted as a copied instruction file missing that script.
[GitHub's licensing guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository)
states that public visibility without a licence does not give permission to
reproduce or distribute source code. Source discovery and licence evidence
remain separate from customer distribution rights. First-party generation
from verified tasks and code, maintainer submissions with explicit rights,
and tenant-private material are distinct lanes. Company, occupation, project,
language, client and model dimensions are search facets until a different
method, effect or acceptance check justifies another package.

The first source-driven campaign should report, per lane, exact leads,
rights-eligible unique method proposals, format-complete package trees,
independent review decisions, adjudication holds, active release versions,
native discovery and verified task outcomes. The saved
[data-cleanup experiment](../roadmap/roadmap.yaml) under S-6.47 found an
approved item made one measured model's phone-number work worse. Approval and
helpfulness are separate measurements. A very large catalogue of unhelpful
files would fail the owner's objective.

## Existing roadmap owners and next evidence gates

| Roadmap boundary | Next evidence that changes the decision |
|---|---|
| S-6.40, supply and candidate factory | Merge or adapt the outside importer only after its 3,251 staged rows have complete multi-file handling, file-level rights and distinct-method clustering. Measure first-party task-to-useful-method yield on a stratified population. Do not add its rows to approved supply. |
| S-6.45, exact rights and safety | Freeze both malicious and benign controls by file kind. Preserve a bill of materials for code and plugins and fail on missing nested rights, dependencies, effects or secret scans. |
| S-6.63, independent panel | Adjudicate the 29 opposing outcomes, clarify effect language, repair candidate defects, and expand blinded calibration by risk class before review at scale. The producer never approves its own tree. |
| S-6.62 and D-05, releases and stores | Prove complete multi-file bundles, bounded index build and swap, withdrawal through rollback, tenant grants and source changes at 10,000, then 100,000, then larger populations. The synthetic million-row audit is not this gate. |
| S-6.32, search and S-6.44, native placement | Hold out real task and no-answer queries, apply a relevance floor and native client/version placement, then record offered, fetched, loaded, used and independently verified separately. |
| S-6.47, customer benefit | Compare a selected item with a no-item arm and a raw-source arm before calling it helpful or claiming lower cost. Preserve negative outcomes. |

The next public library size should come from one active release's exact
independent review records and authorization checks. It should give the
distinct package count and unique eligible file count side by side. This
offline audit can detect drift and review conflicts, but it cannot approve
content or measure what a customer's harness achieved.
