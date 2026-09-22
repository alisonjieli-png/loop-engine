# Library scale and paid acquisition readiness

Kind: dated primary-source research and capacity proposal. Reviewed
September 22, 2026. The owner wants a working onboarding path, readiness
for paid advertisements, and more than 100,000 harness intelligence files.
This record defines what each count and gate would mean. It does not buy
advertising, acquire data, approve a file, publish a page or change a
customer's access. The [roadmap](../roadmap/roadmap.yaml) remains the task
authority for S-6.40, S-6.45, S-6.32, D-17, D-18 and D-23.

## Current counts and their limits

At the read-only local audit, the [starter review](../../examples/29_intelligence_service/starter-catalogue/REVIEW.md)
listed 123 candidate bodies. Three independent reviewers judged 49 of them:
43 were approved, six rejected and 74 remained unreviewed. The local host
release manifest included 43 entries. These are repository records, not a
fresh authenticated count of the running host, and the initial reviewed
items were curated. Their approval rate cannot be projected onto a large
outside-source feed. The [generated status](../roadmap/CONTINUATION-STATUS.md)
still marked all eight public paid-release gates unverified at this audit.

The new [offline candidate preparer](../../tools/prepare_harness_candidates.py)
accepts up to 5,000 authored proposals grounded in exact committed local
sources and writes only candidate bodies and current record shapes. The
[isolated staging command](../../tools/stage_intelligence_candidates.py)
accepts at most 50 records per run and does not yet provide durable
cross-population resumption. Even if 100,000 suitable proposals already
existed, this shape would need at least twenty preparation batches and
2,000 staging populations before review. It has no qualified external-source
provenance, native multi-file package or automatic publication path. The
synthetic thousand-item test demonstrates batching and schema compatibility,
not usefulness or rights to sell the outputs.

## One operational runtime and separate library facts

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

The proposed scheduled harvester, scanner, search index, skill package and
review record are mechanics or passive content owned by classified Loops. Their
existence does not change runtime authority. Every candidate retains its
own lifecycle. Search popularity, a scanner pass or a good run cannot make
it approved. A serving release reads only exact independently approved
bytes under the current licence and tenant grant.

Report these counts separately, with versions and exclusions:

| Count | Meaning and exclusion |
|---|---|
| Discovered sources | Repository, directory or publisher entries found. An entry can point at no redistributable body. |
| Fetched files | Exact source bytes obtained under the source's access rules. A failed, deleted, blocked or changed source remains recorded. |
| Distinct candidate files | Files after exact and near-duplicate review, with source and authored-body digests. Duplicates across registries are not new knowledge. |
| Rights-eligible candidates | Intended distribution is permitted by file-level evidence and notices. A public address or repository-level badge alone is insufficient. |
| Approved packages | An independent review covers exact bytes, declared effects, licence, dependencies, format and source identity. One package can contain several files. |
| Active served packages | Approved versions actually present under host family policy and customer grants. A withdrawn version leaves historical evidence but cannot be fetched as active. |
| Helpful packages | A supported native client loaded the version, used it on a named task and an independent check found a benefit against a proper baseline. Unknown and harmful effects remain visible. |

[Vercel's Skills command line tool](https://github.com/vercel-labs/skills/blob/main/README.md)
already searches, installs and temporarily uses skills across many agents.
[Mintlify Index](https://www.mintlify.com/search-index) advertises retrieval
over more than 200,000 libraries and interfaces, and
[Context7](https://context7.com/plans) has a free public-documentation tier.
File count and temporary loading alone therefore have strong substitutes.
[Vercel's directory terms](https://www.skills.sh/terms) say an indexed
third-party item is not owned or relicensed by the directory, and automated
checks do not guarantee safety. Its [unlisted packs](https://www.skills.sh/docs/packs)
are reachable by anyone with the address. Baltor's possible advantage is
exact authenticated entitlement, source and effect proof, and task utility,
but that remains an end-to-end hypothesis.

The [Agent Skills format](https://agentskills.io/specification) describes
roughly 100 startup metadata tokens per installed skill as a design guide.
Loading metadata for 100,000 skills into every harness would be roughly ten
million tokens before the task begins. This is illustrative arithmetic, not
a measured Baltor bill. It supports searching on the server, returning a few
typed references, and loading selected exact bodies for a focused step.
The format also permits `scripts/`, `references/` and `assets/`; a count of
Markdown bodies is not a count of validated multi-file packages.

## Measurable production and review capacity

Use conditional rates measured on a named source cohort, not a guessed
conversion factor:

| Symbol | Conditional fraction |
|---|---|
| `f` | Discovered entries fetched within the source rules. |
| `r` | Fetched entries with rights for the proposed use. |
| `u` | Rights-eligible entries distinct after exact and near-duplicate checks. |
| `n` | Distinct entries whose rendered native package passes format checks. |
| `s` | Native candidates passing safety and effect triage. |
| `a` | Triaged candidates independently approved on exact bytes. |
| `l` | Approved packages observed loaded in a supported client. |
| `h` | Loaded packages observed helpful on checked tasks. |

For `D` discovered entries, prepared candidates are
`C = D × f × r × u × n`; approved packages are
`A = C × s × a`; observed helpful packages are `H = A × l × h`.
Each rate is conditional on the preceding stage, so the formula does not
assume statistical independence. Report confidence intervals and rates by
source, file kind and task family. Solve backwards from a desired approved
count only after observing the rates. The title “100,000 files” must state
whether it targets candidates, approved packages, active packages or helpful
packages; these are different milestones.

Review capacity may dominate storage. If `Q` packages each need `j`
independent reviewer decisions taking a measured median `t` minutes, initial
review time is `Q × j × t / 60` reviewer hours, plus disputes and updates.
As an illustrative, **unmeasured** scenario, 100,000 packages with three
ten-minute decisions each need 50,000 reviewer hours. This is not a
forecast: a future independent process may be faster, but it must keep a
malicious-skill and known-wrong regression set that measures false approval.
A random sample detects population problems but cannot approve every
unsampled item. Clustered or copied attacks need source-stratified review.

A [2026 security study](https://arxiv.org/abs/2602.06547) examined 98,380
skills collected from two registries and behaviorally confirmed 157
malicious files. That is the study population, not a current directory size
or predicted Baltor attack rate. It supports a versioned adversarial set,
quarantine on source changes, exact digest review and prompt-injection,
script, dependency and effect checks. The
[official Model Context Protocol Registry](https://modelcontextprotocol.io/registry/about)
is a metadata directory that delegates code security checks. A registry
listing cannot satisfy independent item admission.

### Three staged scale checks

| Scale stage | Discriminating check, not a publication claim |
|---|---|
| 1,000 candidates | Every file has source and authored digests, rights state, candidate lifecycle and rendered format result. An identical rerun adds nothing; changed source bytes create a new review subject. Normal customer search exposes zero candidates. Report stratified reviewer defects. |
| 10,000 candidates | Durable cursor and readback resume interrupted batches without duplicating or guessing an unknown commit. Source deletion, licence change and takedown invalidate active versions. Held-out customer-like queries measure recall at three and false reference rate, including no-result needs. |
| 100,000 metadata cards | An index reused across requests meets declared p95 latency, memory, storage and concurrent tenant limits. Revocation during search withholds the result before disclosure. A near-duplicate flood cannot dominate top results. Report approved and helpful packages separately from the synthetic scale population. |

The current hosted [search adapter](../../src/loop_engine/core/service_runtime/http.py)
still builds a new `Retriever(records)` from the authorized listing for each
request. The typed prepared search and policy exist elsewhere, but the
[local 354-query comparison](../components/intelligence-layers/SEARCH-QUALITY.md)
does not prove the served route can search 100,000 items within a bound. It
also returned references for all ten unanswerable queries under the selected
default policy. At scale, reuse an index only under exact source, policy,
grant and family identities, with permission filtering and final
reauthorization. Measure rebuild, hot and cold search, no-result quality,
tenant changes and rollback before selecting another database.

## Source rights and continuing upkeep

Use official source inventories before scraping rendered pages. The
[Model Context Protocol Registry aggregator interface](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/registry-aggregators.mdx)
provides cursor, update and deletion signals; [GitHub's contents interface](https://docs.github.com/en/rest/repos/contents)
provides versioned repository paths with documented size limits. Record
origin, immutable commit, file path, raw and rendered digest, attribution,
dependency and notice for each candidate. [GitHub's licensing guide](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository)
explains that public code without a licence retains default copyright;
[robots rules](https://www.rfc-editor.org/rfc/rfc9309.html) control crawler
requests but do not grant rights to redistribute material. Unknown rights
must block verbatim paid delivery. A permissive source still needs its exact
terms and file-level exceptions checked.

The [O*NET 31.0 database](https://www.onetcenter.org/database.html) is one
structured occupation source under Creative Commons Attribution 4.0, with
credit, licence link and change notice. It can seed candidate task ideas.
One general skill repeated under 1,000 occupation labels remains one method;
different labels do not make 1,000 useful packages. Source updates, changed
dependencies, expired advice and customer feedback need a withdrawal and
re-review path. Count refresh backlog and time to withdraw alongside new
file output.

## When an advertisement has a useful destination

The customer funnel is **ad click → relevant landing page → invitation or
account → client key → search → exact download → native load → use →
independently verified result → repeat use → paid renewal**. The hosted
service directly observes offer and delivery; local loading, use and result
need a consenting client-side report. Record each stage separately, with
drop-off reasons and customer support time. Measure cost per attributable
paying customer and retained net contribution only after actual cohorts
exist. Clicks, signups and downloaded bytes are diagnostic signals, not
accepted work.

The current eight paid-release gates remain open in the
[generated status](../roadmap/CONTINUATION-STATUS.md). Before broad paid
acquisition, an outside person should be able to request an invitation or
register as offered, receive and revoke a key, connect a supported harness,
load useful material, understand the $29 allowance and model cost, receive
support, manage or cancel the subscription, and see a checked task example.
Every live hostname needs the release and recovery checks. The product
privacy, licence and data-retention statements must match the real flow.
An owner-authorized, tightly capped invitation experiment can be evaluated
earlier when its narrower beta path works; this record grants no ad spend.

[Google Ads destination policy](https://support.google.com/google-ads/answer/6008942)
expects a functional, useful and navigable destination with value. Its
[Search spam policy](https://developers.google.com/search/docs/essentials/spam-policies)
treats mass low-value generated pages as scaled-content abuse. Creating one
public page per unreviewed skill to acquire traffic would make a trust and
distribution problem. Role pages and demonstration subdomains under D-23
should point to saved, reproducible runs and working onboarding. Compare
channels by native loads, accepted tasks, repeated use and retained paid
customers, not by impression counts alone.

## Research handoff for Claude Code

S-6.40 owns discovery, bounded fetching, candidate production and source
upkeep. S-6.45 owns malicious-skill, rights and package checks. S-6.32 and
S-6.52 own the served relevance floor and engine tournament. D-17 owns
outside-user native loading. D-23 and S-6.37 own the paid-acquisition
destination and evidence pages. The next engineering decision is whether
100,000 means candidate files or independently approved, active packages;
the capacity test and review model follow from that answer. No new task list
is created by this report.
