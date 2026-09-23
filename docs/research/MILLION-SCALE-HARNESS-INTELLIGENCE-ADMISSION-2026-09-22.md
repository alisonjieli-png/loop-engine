# Million-scale harness intelligence admission research

Kind: dated primary-source research and adversarial scale proposal. Reviewed
September 22, 2026 against local main `9cdf99e` and the newer
[harness and library plan](HARNESS-AND-LIBRARY-PLAN-2026-09-22.md). The
[roadmap](../roadmap/roadmap.yaml) remains the only task authority, especially
S-6.40, S-6.45, S-6.32 and D-05. This report does not authorize source
scraping, model spending, redistribution, candidate approval or publication.

## Answer the million-file question precisely

A million discovered file references is plausible to **count**. A million
rights-eligible, distinct, safe, independently approved and helpful harness
packages is a different claim. Rendering one method as files for ten
harnesses creates ten deliverable variants, not ten independent methods.
Packing one skill with a script, a reference and an asset creates several
files, not several independent skills. Public library size should count
approved active exact packages; candidate, rendered-file and helpful counts
must be displayed separately.

The present [starter review](../../examples/29_intelligence_service/starter-catalogue/REVIEW.md)
has 123 candidate items, 49 reviewed, 43 approved, six rejected and 74
unreviewed. The local host manifest carries 43. The
[offline preparer](../../tools/prepare_harness_candidates.py) reads only
committed local MIT sources at current HEAD, accepts at most 5,000 authored
proposals and writes one Markdown body per proposal in 50-item populations.
The [isolated staging command](../../tools/stage_intelligence_candidates.py)
accepts at most 50 candidates into a new SQLite database and forces
`candidate`, `pending_review` and `execution_available=False`. The tested
1,000-item fixture shows bounded production and staging, not an outside
source feed, native loading or independent usefulness. The preparer is not
yet a complete `SKILL.md` renderer because it does not emit the
[required Agent Skills frontmatter and optional bundled files](https://agentskills.io/specification).
At current per-run ceilings, one million suitable proposals would require
at least 200 preparation batches and 20,000 fifty-record staging
populations before rights review or approval. The staging command creates
a new isolated database each run, not a resumable million-item feed.

## Keep runtime and intelligence classifications intact

```text
Operational runtime type
└── Loop
    ├── Operational relationship
    │   ├── Starting
    │   ├── Spawned by
    │   ├── Queried by
    │   ├── Retrieved by
    │   └── Connected from
    ├── Role
    │   ├── Practitioner
    │   ├── Intelligence
    │   └── Solution
    ├── Versioned role profile
    ├── Purpose and domain categories
    ├── Run mode
    │   ├── deterministic
    │   ├── hybrid
    │   └── non-deterministic, with model-led semantic work
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition
    ├── Exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the selected mode permits a model
    └── Run History records
```

The four persistent intelligence layers still own bodies by meaning.
Harness intelligence is the family of material shaped to drop into a native
harness. Markdown, skills, repositories, protocol server configurations,
embeddings and graph indexes are source or delivery formats, not extra
layers. Source connectors, queues, workers, storage indexes and reviewers are
mechanics under classified Loops. Self-generated material stays candidate
until an independent process approves exact bytes.

## Record each denominator

| Count | What it establishes and excludes |
|---|---|
| Discovered entries | A registry, publisher or repository exposed a reference. It may lead to no accessible body. |
| Fetched source files | Exact bytes were obtained under source rules and fixed to a fetch timestamp and digest. Fetching grants no redistribution rights. |
| Rights-eligible distinct candidates | The intended use has file-level rights evidence; exact and near-duplicate clusters have been inspected. A repository licence badge alone is insufficient. |
| Logical packages and rendered files | The first counts unique methods or tool packages; the second counts their native layouts and bundled files. A rendering cannot inflate the first. |
| Independently approved exact versions | A different governed process approved this digest, licence, effects, dependencies, format and review criteria. A source listing, scanner score, model confidence or good run is not approval. |
| Active served versions | Approved bytes remain under a current source right, host family policy and customer grant. Withdrawn versions stay historical but unavailable. |
| Helpful versions | A supported native client demonstrably loaded and used the version on a task and an independent evaluator found accepted work or a measured benefit against an appropriate baseline. Unknown and harmful outcomes remain visible. |

## Source supply with rights and update semantics

The [official Model Context Protocol Registry](https://modelcontextprotocol.io/registry/about)
is a useful metadata feed, with the [aggregator guide](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/registry-aggregators.mdx)
describing pagination, incremental updates and preview-data limitations. It
delegates server-code security scanning. Its
[`server.json` schema](https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/server-json/draft/server.schema.json)
can describe remote URLs, package commands, environment variables and
secret-valued inputs. A registry row must stay inert in search; copying its
command or endpoint into an active harness configuration would install a
capability without the required effect, credential, source and permission
checks. An entry's version and `updatedAt` do not pin a remote endpoint's
behavior. Preserve the fetched metadata digest and timestamp, and an exact
package artifact digest where supplied. Mark remote behavior unpinned until
an exact qualified binding exists.

[skills.sh terms](https://www.skills.sh/terms) identify upstream authors as
the content owners. [GitHub's licence guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository)
says public code without a licence retains default copyright. Package files
can carry different notices. The [npm crawler policy](https://docs.npmjs.com/policies/crawlers/)
permits certain registry inspection, while individual packages still carry
their own licences. These are discovery channels, not blanket grants to
copy content into a paid catalogue. The strongest supply path for valuable
public packages is an opt-in publisher submission or partnership with an
explicit distribution grant, canonical source, update channel and takedown
contact. Customer-private materials remain tenant scoped and do not become
public material through search, generation or feedback.

Do not treat model paraphrasing of a restricted source as automatic rights
clearance. Original authored procedures can use facts from rights-cleared
sources or independent expertise, with their own provenance and licence
review. A source deletion, licence change, explicit registry deletion or
reported malicious version blocks new delivery pending independent review.
An item missing from an incomplete cursor page, outage or reset is **not**
proof of deletion; require a complete reconciled source snapshot before
classifying absence. Keep prior bytes in historical evidence without serving
them as active.

## A scalable candidate pipeline behind existing edges

```text
S-6.40 source discovery
  -> source-specific cursor, rate budget and rights to fetch
  -> immutable raw source identity: origin, revision, path, digest, time
  -> exact deduplication plus near-duplicate candidate clusters
  -> typed candidate authoring and native package rendering
  -> format, dependency, licence, effect and safety triage
  -> independent exact-version approval or named refusal
  -> D-05 immutable body and authoritative catalogue record
  -> rebuildable, grant-filtered S-6.32 search projection
  -> final current-rights reauthorization at body fetch
  -> consented S-6.41 outcome observation, candidate improvement only
```

Use an idempotency identity such as `(source, revision, path, source_digest,
generator_version, output_kind)`. An unknown commit reconciles that exact
key and reads back bytes before retrying. A changed source digest creates a
new candidate, not an in-place rewrite of an approved version. Preserve
failed fetches, ambiguous rights and rejected outputs with reasons. A source
adapter can offer metadata links without importing a body, but a link
cannot imply safety or native installation permission.

An exact SHA-256 digest catches byte duplicates. A normalized comparison can
cluster boilerplate, and MinHash or locality-sensitive hashing can propose
near-duplicate groups; neither should silently merge semantically different
skills. Group by source family and task purpose before deciding that a
near-duplicate is redundant. Count one logical method separately from the
number of client-specific renderings. Use the official
[Agent Skills specification](https://agentskills.io/specification) and its
reference validator for real packages with `SKILL.md`, scripts, references
and assets, while retaining independent effects and execution checks.

Candidate generation can scale from several distinct sources without
inventing expertise: first-party code that already passed an exact check,
maintainer-submitted packages with distribution rights, customer-private
materials kept in their own tenant, and source-grounded original procedures
whose claims can be checked. A generator should propose one narrow job,
preconditions, input/output contract, denied effects, failure cases and
source identity per package. It should return “no candidate” when a source
adds no new verified procedure. Changes in wording, title, target client
or model create variants of one logical method; they are not new independent
knowledge. A public metadata federation can point to an upstream package
without storing its body, but a customer must still see its unqualified
status and approve any executable installation.

## Approval cannot be inferred from a batch sample

S-6.40's current acceptance says a worker adds reviewed, licensed items
continuously “without manual work,” while its verification requires every
item to remain a candidate until independent reviewers approve it. The
[newer implementation plan](HARNESS-AND-LIBRARY-PLAN-2026-09-22.md)
likewise describes per-item model review and a human batch spot audit. The
scalable interpretation needs an explicit, versioned **independent approval
policy**: which bounded low-risk classes an independently qualified
deterministic or model-assisted verifier may approve, and which rights,
scripts, effects or uncertain cases require human judgment. The generator,
reviewer and promotion authority remain separate. A sampled human audit
estimates reviewer defects and can withhold a batch; it cannot approve
unsampled exact bytes by itself.

Every candidate can receive automated deterministic checks. High-risk
scripts, tool configurations, external commands and credential access need
stronger inspection and sandbox tests. Factual instruction files need source
claim checks and task controls. Scanner output is triage. The
[MaliciousAgentSkillsBench artifact](https://github.com/protectskills/MaliciousAgentSkillsBench)
describes 157 behaviorally confirmed malicious skills nested inside 4,287
suspicious candidates inside a 98,380-skill snapshot. The remainder of that
snapshot is **not** a verified benign set. Build a separate clean benign
control population, measure false refusals as well as missed attacks by
source and attack class, and keep known-wrong controls that fail when a
guard is removed. A generated item can never approve itself.

At an **illustrative** three reviewers spending ten minutes on each item,
one million individual approvals would require 500,000 reviewer-hours,
before updates, disputes and re-review. Automated independent review may
reduce manual hours after its false approvals are measured; it does not
erase the approval obligation. Review throughput, defect rate and content
maintenance must be measured before assigning a business value to a million
files.

## Retrieval and storage at one million cards

The current served path builds a `Retriever(records)` from each authorized
listing per request; the [search quality record](../components/intelligence-layers/SEARCH-QUALITY.md)
measures relevance on 354 queries, not million-card capacity. A million
metadata cards need an index reused across requests and rebuilt from the
authoritative approved-version catalogue. Filter by tenant and grant before
ranking, then reauthorize the selected exact body immediately before fetch.
Measure no-result quality, near-duplicate top-result flooding, source
withdrawal and rights revocation under concurrent queries. Embeddings and
graphs are optional engines behind the same retrieval edge, chosen by held-out
quality and total index/build cost; neither becomes another intelligence
layer or an authority store.

For sizing illustration only, a million 10-kibibyte bodies occupy about
10.24 gigabytes before replication, indexes and backups. A million
384-dimensional float32 vectors occupy about 1.54 gigabytes before their
index and payload. The actual body-size distribution, embedding revision,
write churn, tenant count and access pattern must be measured. Do not put a
million bodies in Git or prefill every harness's context. Search returns
small references; materialize a body only after exact selection and grants.

## Four evidence stages

| Stage | What can be demonstrated without inflating the public library count |
|---|---|
| 1,000 real candidates | Every source and output has an exact digest, file-level rights state, native-format result, candidate lifecycle and duplicate cluster. Scanner tests include malicious and benign controls. Normal customer search exposes none of the unapproved population. |
| 10,000 real candidates | A durable source cursor resumes interrupted batches without duplicate or guessed commits. Upstream change, explicit deletion, licence change and takedown produce exact lifecycle transitions. Held-out search includes no-answer queries. |
| 100,000 metadata cards | An approved-only reusable index meets declared p95 latency, memory, storage and tenant-concurrency limits. Withdrawal during search prevents body disclosure. Build and update cost, recall at three, false-reference rate and duplicate flooding are reported together. |
| 1,000,000 metadata cards | A failure-injected ingestion, update, withdrawal and reindex stress campaign reports exact source/rights/candidate/approved/active/helpful denominators. Only the independently approved subset can be served; scale of cards is not a quality claim. |

These are proposed qualification stages, not achieved milestones or a launch
forecast. S-6.40 owns discovery and candidate production, S-6.45 owns
admission and rights, D-05 owns durable blobs/catalogue/projections, S-6.32
owns served relevance and S-6.41 owns consented outcome evidence. The next
review of S-6.40 should replace “reviewed items without manual work” with
the exact independent approval policy and its measured defect ceiling. The
source-population figures in the Claude plan should also be reproduced from
saved query, timestamp, response and inclusion rule before they are reused
as market or supply facts.
