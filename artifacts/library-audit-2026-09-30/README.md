# Library count reconciliation

Kind: measured inventory and publication audit, September 30, 2026.

The published catalogue contains **96,064 distinct files in 30,746 packages**.
It has 130,568 file placements; shared files appear in multiple packages and
are counted once in the distinct-file total. This follows the publication of
7,691 additional file digests and 2,935 packages during this review.

The local store contains substantially more material. Earlier updates mixed
package counts, file counts and readiness stages. These rows overlap and
must not be added together.

| Population | Packages or records | Distinct payload files | What it establishes |
| --- | ---: | ---: | --- |
| Current imported candidate packages | 80,973 packages | 240,548 | Material retained for review and use decisions. |
| Current generated candidate packages | 78,334 packages | 529,589 | Generated package payloads stored locally. |
| Union of those current candidate payloads | 159,307 packages | 769,812 | Distinct named blobs exist in the body store; this audit did not rehash every byte. |
| Generated packages passing the complete static qualification pass | 57,613 packages | 411,441 | The qualification record still matches each current package version and digest. Independent approval and execution checks remain separate. |
| Published catalogue before this update | 27,811 packages | 88,373 | The prior active release. |
| Published catalogue after this update | 30,746 packages | 96,064 | Approved packages offered by the running service, with complete file manifests. |

The database also has **259,874 records**. This includes 73,135 ideas,
5,402 source-state records, 22,029 superseded generated versions and one
withdrawn version. A database-record count cannot establish a file count.
The historical claim of over 250,000 ready files requires its exact source
before it can be classified; the audit does not reinterpret that claim as a
published total.

The separate artifact factory has another vocabulary. Its current ledger
contains 108,000 `staged_unlicensed` outcomes and 24,000 duplicates. An older
ledger records 379,324 staged unlicensed artifacts, 134,000 duplicates and
201 rejections. Those are different snapshots, not additive approved supply.
The factory explicitly says it does not review, approve, admit or publish.
Some retained artifacts are copies of local reports and private project
material; they must not be promoted wholesale.

## What held up publication

The daily combined catalogue omitted `component_form` from its attribute
schema because its job used an older tool revision. The current combiner
already declares that attribute. Rebuilding from the same reviewed material
preserved every prior package payload digest and allowed publication.

The generated review pass exposed two other problems. A function sample
rejected 21 of 58 components; an install-recipe sample rejected 6 of 48.
These batches need repairs. The data-table sample received no verdicts
because review requests exceeded the context window. Its planner constructed
variable-sized groups, then the panel regrouped the flattened requests at a
fixed maximum. That requires a request-planning repair, not an approval.

A separate review of previously unreviewed MCP and API-operation batches was
started during this audit. Its single-item calibration was incomplete, so it
stopped before admissible batch review. No new approval is claimed from that
attempt.

The deployment and catalogue release are distinct operations. Website release
54 completed successfully. The catalogue then moved atomically from
`b8058609…` to `f817b2b3…`. The observed serving-view swap took 337.673 seconds
on the existing one-CPU, 2 GB machine. This is a measured scaling issue for
the indexing and loading work.

## Evidence and limits

The audit read one SQLite snapshot of canonical candidate records, current
qualification records, the previous and next release inventories and the
factory ledgers. It found no missing named blob for the current candidate
payloads. Presence, static qualification, independent approval, native loading,
execution and successful customer outcomes are separate observations.

The private full audit has SHA-256
`b96cc9c46bea7ad2a5ee4fdc6602b972dbd0e08d46aa0c768bd2f9b9d026beae`.
Raw histories, candidate bodies and private project contents are not published
with this report. The [release 54 record](../architecture-audit-2026-09-19/pilot-release-54.json)
holds the live image and catalogue identities and the verification scope.
