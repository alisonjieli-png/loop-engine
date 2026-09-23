# From the current service to 100,000 harness intelligence packages

Kind: dated synthesis and engineering handoff, September 22, 2026 local time.
This is research and a proposed sequence, not a release plan or a second
source of task authority. The [roadmap](../roadmap/roadmap.yaml) governs work.
No item was admitted, model allowance spent, payment made or service changed
for this report.

## What exists, and what the target means

The current [repository rule](../../AGENTS.md) and roadmap S-6.40 count the
owner's 100,000 target as **distinct approved logical packages** in the active
release. Each package may contain one or more files a supported harness
actually reads or invokes. Count unique eligible source files separately.
An Agent Skill with its script and reference data is one package; copies for
Codex, Claude Code, OpenCode or different models are renderings of that same
package. The owner's wording of 100,000 harness files remains a separate
visible measure, and neither measure includes review notes, tests, source
snapshots, inactive versions or withdrawn items.

The [read-only live audit](../verification/SAAS-LIVE-READINESS-AND-CUSTOMER-JOURNEY-2026-09-22.md)
found eight public hostnames healthy on the same deployed site, but public
registration and sign-up email are off, checkout and portal are off, and no
invited customer has been observed downloading an approved item, placing it
in a native harness and finishing an independently checked step. The current
packaged host manifest contains **43 single Markdown skill bodies**.
[An exact file check](../verification/SAAS-LIVE-READINESS-AND-CUSTOMER-JOURNEY-2026-09-22.md#library-population-and-100000-file-boundary)
found no `SKILL.md` basename or Agent Skills frontmatter among them, so
their current skill metadata does not prove native Agent Skill pickup. Four
[original skill batches](../context/CODEX-SIDE-RESEARCH-HANDOFF-2026-09-22.md)
contain 80 more candidates. The
[first mixed-format pilot](../verification/MIXED-FORMAT-HARNESS-INTELLIGENCE-CANDIDATE-QA-2026-09-22.md)
contains six candidate packages with instructions, Python tools and a local
protocol connection; the
[second multi-file batch](../verification/SECOND-MIXED-FORMAT-CANDIDATE-BATCH-QA-2026-09-22.md)
adds three script-bearing skill candidates. None of those 89 has an
independent exact-byte admission decision or active customer grant.

The runtime classification remains:

    Operational runtime type
    └── Loop
        ├── Operational relationship
        │   ├── Starting
        │   ├── Spawned by
        │   ├── Queried by
        │   ├── Retrieved by
        │   └── Connected from
        ├── Role: Practitioner, Intelligence, or Solution
        ├── Versioned role profile and purpose categories
        ├── Run mode: deterministic, hybrid, or non-deterministic
        ├── Step profile; typed input and output; loop and exit conditions
        ├── Graph relationships; budget, permissions, and effect policy
        ├── Model settings when the mode permits a model
        └── Run History records

Generation, review, indexing, delivery and native placement remain mechanics
owned by classified Loops and existing component boundaries. Harness
intelligence is a family, not an additional intelligence layer.

## The measured scale gap

The [reproducible offline probe](../../artifacts/hundredk-serving-probe-2026-09-22/README.md)
used synthetic metadata with one primary file per row. It did not create
approved bodies or test a multi-file package. The results diagnose current
limits, not production throughput:

| At 100,000 synthetic rows | Measurement | Current limit or path |
|---|---:|---|
| Indented host manifest | 122,071,567 bytes | Host loader refuses over 2,000,000 bytes; this fixture first fails at 1,639 rows. |
| Bare unpaged list | 73,314,429 bytes | HTTP default response ceiling is 262,144 bytes; this fixture's bare list first fails at 358 rows. |
| One tenant's grant-array record | 47,257,224 bytes | Existing grant updates replace and reads rehydrate the whole array. |
| Fresh hosted Retriever build | 48.57 seconds, 2.10 GiB peak resident memory | Search builds SQLite full-text search and Python hash vectors per request; current request deadline is 30 seconds and Fly profile states 2 GB memory. |
| SQLite full-text search component alone | 1.80 seconds to build, 180 MiB peak; one exact-token query 0.0007 seconds | A persistent, release-bound index is promising, but one token does not measure relevance, concurrency or a customer path. |

The current builder makes one Markdown body per item, the reader decodes one
UTF-8 string, and download names it intelligence.txt. That path cannot
faithfully deliver arbitrary scripts, settings, images or whole skill
directories. Raising byte ceilings alone leaves the grant, index,
pagination, rights and native-placement failures. The current 100,000-row
search would also exceed the documented request deadline and memory before
service overhead. SQLite's own
[full-text search documentation](https://www.sqlite.org/fts5.html) supports
indexed content, ranked queries and consistency checks; a persisted index
should still be qualified against held-out task queries and tenant filters.
The [larger admission study](MILLION-SCALE-HARNESS-INTELLIGENCE-ADMISSION-2026-09-22.md)
also found that the current candidate preparer accepts at most 5,000
single-Markdown proposals per run and the local staging command accepts at
most 50 candidates into a fresh isolated database. Those are useful bounded
checks, not a resumable production package factory or a measured review
pipeline.
Body storage is another unmeasured capacity. As a sensitivity example,
100,000 packages averaging one 10-kibibyte payload would occupy about
0.95 gibibyte before indexes, historical versions, records or backups;
the [current service volume](../architecture/MVP-CLIENT-SERVER.md#current-deployment)
is one gigabyte. A multi-file corpus may be larger. Measure the actual
package-size distribution before choosing a volume or object store.

## One release and retrieval contract for every file kind

The existing S-6.40, S-6.44, S-6.45, S-6.62, S-6.32 and D-05 boundaries can
carry this sequence without a new parallel catalogue:

    Pinned task need or permitted exact source
    ├── Original method and distinctness check
    ├── Candidate package
    │   ├── Canonical member files and typed roles
    │   ├── Rights, provenance, effects and dependencies
    │   ├── Per-client placement and rendered digests
    │   └── Positive and known-wrong checks
    ├── Independent exact-tree admission
    ├── Immutable active release and withdrawal record
    ├── Persistent searchable projection and sparse tenant policy
    └── Selected exact package delivered to one clean step harness
        └── Placed, discovered, loaded, used and verified records

The package record needs a stable semantic identity, version, complete tree
digest, each member's relative path, MIME or format, byte length, SHA-256,
role, source and licence, dependency, effect requirement, selected client
layout and activation rule. A rendered variant names each canonical member
and its destination path. A changed file, even a script or asset, changes
the package tree and invalidates its approval. Review notes, tests and
records have explicit non-delivery roles. The
[candidate-only local repair](../verification/MIXED-FORMAT-HARNESS-INTELLIGENCE-CANDIDATE-QA-2026-09-22.md)
now rejects a review note or test file planted in a client variant; it does
not qualify the production contract.

At release time, store immutable exact bytes, write a versioned active
package index, then atomically move a guarded active-release pointer.
Index metadata once per release behind the existing hosted search engine
edge; do not rebuild the entire corpus per query. A sparse tenant policy
grants eligible approved items from the active release and records explicit
denials and revocations. Search filters eligibility before returning small
references. Direct reads recheck tenant, release, withdrawal, permissions
and every delivered digest. Enumerations need bounded pages and stable
cursors, and whole packages need typed streamed or bounded archive delivery
that preserves relative paths and avoids partial activation. A release
rollback must not revive withdrawn bytes. S-6.62 is already building parts of
this in a separate Claude Code worktree; compare these gates with that work
before implementation.

The 100,000-package index stays server-side. The
[complete behavioral explanation of a discrete cognitive or act step Loop node](../../ASTRA.md#complete-behavioral-explanation)
governs the assignment, its fresh harness, continuation and effects; file
selection is only one part of that behavior. For each focused step, the
Intelligence Query Loop returns small typed
references; the governing Loop selects only packages eligible for that
step's purpose, context budget, model, client version and typed effect
authority. The materializer puts their verified files at the qualified
native paths of a newly started harness. Large references load only when
selected. The [model-conditioned research](MODEL-CONDITIONED-HARNESS-INTELLIGENCE-2026-09-22.md)
allows a shorter or reworded rendering for a particular model only as a
versioned derivative of a reviewed source, with its own exact-byte checks;
it does not create another method or loosen permissions. Provider keys,
local endpoints and protocol connections pass through the
[scoped credential boundary](CUSTOMER-ENDPOINTS-AND-CREDENTIAL-DELEGATION-2026-09-22.md),
not through a source file copied into the step folder. The four-layer
history may suggest a later improvement, but a good run never approves
its own replacement package.

## Supply is a measured process

The [supply study](HUNDRED-THOUSAND-HARNESS-INTELLIGENCE-SUPPLY-2026-09-22.md)
uses original task methods first, then exact-rights outside sources where
permitted. The pinned O*NET task grid offers 18,838 task statements across
1,016 occupations, but those statements are neither 18,838 unique digital
methods nor customer requests. A role, company, locale, harness or model
label is a search or rendering facet unless method, effects or acceptance
really differ. Code, skills, root instructions, agents, configuration,
plugins and selected assets all count as file kinds; file count does not
establish useful task coverage.

At an **assumed** 50% independent approval rate and 80% deterministic
precheck pass rate, 100,000 approved packages require roughly 250,000
drafts, 200,000 review-eligible candidates and 600,000 per-item decisions
from a three-reviewer panel, before retries, withdrawals and human
escalation. Qualified batch reviews might use fewer physical model calls;
that throughput and its error rate remain unmeasured.
Those rates have not been measured. At 1,000 reviewed candidates per day,
the review phase alone would take about 200 days. A 1,000-candidate
stratified pilot must measure distinct yield, source rights, package-file
mix, reviewer error by risk class, native pickup, search recall/no-answer
and physical provider throughput before a scale schedule or spend claim.
The current 89 candidates cannot justify a date for 100,000.

## Launch sequence through existing roadmap gates

| Stage | Customer-visible result | Required evidence and owning work |
|---|---|---|
| First release, invited private beta | An invited developer signs in, creates a personal key, finds one reviewed package, downloads it, places it into a fresh supported harness and receives an independently accepted step result. The user can see usage and revoke access. | D-17-T03/T04, D-18-T01/T03, S-6.44 and S-6.35. Run the full hosted website, catalogue, service and protocol checks on every live hostname after a committed, checked deployment. Preserve release and rollback digests. |
| Second release, usable paid service and first 10,000 packages | A visitor can understand what Baltor supplies, request or create access, subscribe through a proven checkout-to-webhook-to-entitlement path, manage the subscription, recover sign-in, export/delete data and receive support. The first 10,000 distinct approved packages are searchable and deliverable through bounded pages, a relevance floor and a clear no-answer result. | S-6.16, S-6.21, S-6.32, S-6.33, S-6.38, S-6.39, S-6.40, S-6.62 and D-05. Owner-approved terms and an account journey are still needed. Do not treat session creation as a completed charge or subscription. |
| Third release, 100,000 approved packages and broad acquisition readiness | Customers can search, retrieve and natively place selected multi-file packages across supported clients without a service redeploy for each batch. They can see release changes and withdrawal. The public package and file counts come from the active release, not drafts or variants. | S-6.40, S-6.45, S-6.62, S-6.63, S-6.44 and S-6.52. Test a real active-release count, two tenants, package bytes, grants, revocation, rollback, held-out relevance, no-answer, cold and concurrent 95th and 99th percentile latency, memory and storage. The synthetic probe is only a failing baseline. |

For paid acquisition, the first useful conversion is a visitor who reaches
an accepted native step, not a landing-page visit or a catalogue count.
The [live visual review](../verification/LIVE-UI-UX-AND-ACQUISITION-REVIEW-2026-09-22.md)
found that at 390 by 844 pixels the 254-pixel header pushes the first hero
action below the first screen; the waitlist action leads to a notice and
requires another click before the form. The desktop example panel occupies
about two fifths of the hero but demonstrates retrieval rather than the
fresh, focused harness that distinguishes Baltor. S-6.33 already has a
redesign in progress. Its live acceptance should send a visitor directly to
one visible invitation form, show a primary action in the first phone
viewport, and label recorded retrieval separately from an illustrated
future step process.
The current competitor and economics review (kept in the owner's private research folder, outside this public repository)
finds that native skill installation, directories and documentation search
already offer strong substitutes. Baltor should test the combined value of
selection, independent review, exact native delivery and accepted work,
rather than treating the catalogue total as the main buyer promise. Use the
[persona and market research indexed here](../RECORDS-INDEX.md) to choose
one developer problem and one clear demonstration. Instrument
visit-to-invitation, invitation-to-account, account-to-key,
key-to-first-fetch, first-fetch-to-loaded-step, accepted-step and paid
retention separately. Run small, capped campaigns only after the invitation
and step journey work and the owner has an approved claim backed by saved
evidence. Report cost per accepted activated customer rather than cost per
click. This is a research recommendation, not spending authority.

## Immediate handoff to Claude Code

The current roadmap already has owners for the work. S-6.62 needs a named
100,000-package, two-tenant drill covering release activation, grants,
paged list, held-out search, complete package download, withdrawal and
rollback, plus cold/reused/concurrent resource measurements. S-6.40 needs
exact-tree admission across every supported file kind and a machine-derived
active package count alongside unique eligible file and rendering counts.
S-6.35's next action should reflect that the grant step ran in release 15:
the remaining gate is the full per-host suite and release record. The roadmap
also has older owner-approval and model-call notes that must be reconciled
with the newer AGENTS.md standing authority before the panel runs. Preserve
the current 43-item service and the failed attempts while those contracts
change. No claim of a fully functioning paid service or a 100,000-package
library is supported today.
