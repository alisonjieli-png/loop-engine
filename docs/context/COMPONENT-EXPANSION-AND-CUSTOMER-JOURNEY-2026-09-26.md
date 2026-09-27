# Component expansion and the first customer journey

Kind: dated development handoff. The roadmap remains the task authority.
Evidence was collected late September 26 in United States Eastern time,
with some records dated September 27 in UTC.

## What is running

Fly release 38 serves the combined design from commit
`13caeb2039c28681e8c8793cfede80255e6f033a`. All ten hostnames passed their
post-deployment checks. The visitor check covered 54 pages and 348 links
with no reported problems. Catalogue checks passed nine of nine, and the
updated hosted protocol checker passed nineteen of nineteen. Exact source,
image and rollback identities are in the
[release record](../../artifacts/release-38-2026-09-27/README.md).

A new test customer signed up, received the confirmation email, chose a
password and signed in again. The normal product flow granted its current
founding offer. The customer then opened setup and account pages, loaded the
library, selected `find_duplicate_records_with_blocking_keys`, and downloaded
the exact version. There was one component download, no payment, no staff
grant, and no client-token creation. The
[public summary](../../artifacts/release-38-2026-09-27/customer-journey-summary.json)
omits account identifiers and credentials.

Aider 0.86.2 then loaded this actual customer-fetched file through its explicit
read-file mechanism. Its prompt contained the complete 2,722-byte, 44-line
body. A control left the same file on disk while removing that setting and
failed the loading check. No model or network call was needed for this
loading observation. The native record is private at
`/home/username/baltor-private/harness-native-qualification-20260927-v1/aider-customer-file-v1/evidence/summary.json`.

The fetched procedure was used with its named repository implementation on
six synthetic rows. It found the two expected pairs, reported a skipped block
when its ceiling was exceeded, and refused repeated identities. This is a
worked example. The implementation came from the development checkout; the
downloaded text did not bundle it. No unassisted comparison or autonomous
external-harness task result was measured.

Three test problems were corrected without repeating account creation:
the sandbox lacked its resolver path, the email checker omitted the current
`mail.baltor.ai` sender, and the first browsing script waited for a filter
before pressing Load the library. Failed reports remain beside their
successors. The resumable signup checker now retains private state before
effects and refuses to repeat uncertain account creation or confirmation.

## Expand source coverage across builder tasks

The owner's direction is to consider APIs, data cleanup, data centralization
and decentralization, and technical advances as component sources. The
library should support familiar work and emerging methods. The practical
unit is a useful task that a harness can perform or understand.

| Source | Potential component outputs | Check that distinguishes useful work |
|---|---|---|
| API specification | Operation reference, request contract, selected-operation adapter, response validator | A valid example succeeds and malformed or unauthorized inputs are refused |
| Data cleanup project | Profiling procedure, repair function, quarantine policy, regression fixture | Deliberately damaged data is detected and retained or repaired under a stated rule |
| Central data platform | Import recipe, schema migration, lineage mapping, reconciliation tool | Row identity, schema changes and reconciliation differences remain visible |
| Federated or decentralized system | Query plan, conflict-resolution procedure, replication checks | Conflicts, unavailable peers and consistency limits are reported |
| SaaS service | Capability guide, entitlement check, integration template, workflow | Documented access remains separate from an actual successful operation |
| New paper or technology | Evidence summary, reproduction plan, experiment fixture, engine candidate | The claimed result can be compared with a declared alternative on a frozen task |
| Historical project or session | Reusable function, failure-prevention procedure, context, persona, validator | The artifact is grounded in inspected source and passes a concrete counterexample |

One source may support several distinct capabilities. Several sources may
also contribute to one stronger component. Identity, role and persona files
describe behavior or context; they grant no permissions. A documented API
remains useful as a reference while its callable adapter is being qualified.

Use the existing source interrogation questions to determine who needs the
method, what it does, where it applies, when it fails, why it is preferable,
and how to check its result. Ask additional domain questions where useful.
Read selected source bodies before generating their implementation claims.
The full drive inventory is an index for selection, not evidence that every
file body has been understood.

## What this increment adds

The source scout now rotates through 40 data and technology queries, two per
run, under the existing twenty-request ceiling. The four daily runs cover
the configured rotation in five days when they complete. Registry pagination
continues from saved cursors instead of repeatedly fetching its first page.
The first new run completed with 290 extended-source observations. Code,
controls, configuration and installation evidence are in the
[source discovery package](../../artifacts/source-discovery-2026-09-26/README.md).

The data-workflow research lane prepared six original procedure packages from
16 opportunities across ten projects. It inspected 22 official documentation
URLs and pinned ten repository revisions and licence files. The existing
native preparation tool produced 42 payload files. These six packages remain
unapproved and unpublished. All six passed the deterministic prechecks and
were committed to an isolated candidate store. They are absent from normal
search there. Six title-derived review searches found the intended candidate
within the first three results; these are author-supplied probes, not a
retrieval benchmark. The delivery folder is
`/home/username/baltor-library/codex-lane/2026-09-27-data-workflow-6-v1`.
The packages declare Codex root instructions. Compiler placement and native
loading remain untested. Their private source ledger and prepared records
are under
`/home/username/baltor-private/component-domain-expansion-20260927/data-workflow-v1`.

The earlier lane holds 2,196 candidate components and 15,276 payload files.
Forty-seven earlier native packages were delivered for review. Adding this prepared
batch gives 2,202 candidate components and 15,318 payload files across these
two increments, with no new independent approvals or publications established
by this handoff. Discovery observations and layout variants are excluded.
The six draft packages still need semantic review and applicability checks.

## Decisions and remaining work

The 100,000 target counts distinct useful capabilities. A full edition, a
compact edition and several harness layouts belong to the same component.
Compact content must preserve its obligations, exceptions, inputs, outputs
and checks. The three compact pilot pairs have mechanical checks but no
semantic-equivalence or native-use qualification yet.

Use the existing generation, review and catalogue release paths. The source
collector is installed; continuous model interrogation and generation are
still separate work. Keep discovery throughput, inspected sources, generated
candidates, approved components, retrieved files, native loading and accepted
tasks separately measurable. Existing tasks S-6.81, S-6.207, S-6.213 and
S-6.214 own these changes and their next increments.

The expanded customer work belongs to S-6.56 and S-6.66: audience-specific
pages, beginner tutorials, setup and a checked first task. Begin enterprise
offers on `/enterprise`; a separate hostname can be added when its content
and customer route justify one. Private libraries, paid publisher libraries,
team controls and enterprise services need functioning contracts and journeys
before being offered as available features.

Prepare many creative candidates, then run bounded experiments with explicit
audiences and conversion denominators. Track signup, connection, first useful
result and paid retention. The owner's $100,000 monthly recurring revenue
in ninety days is a business target. No forecast or paid-ad spending follows
from it. Setup fees and one-time services do not count as monthly recurring
revenue.
