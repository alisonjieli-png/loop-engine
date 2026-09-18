# Adversarial validation and audit plan for every matrix feature

Date: 2026-09-18. Owner direction: for each feature in the comparison
matrix, add to the plan an adversarial validation and an audit of every
aspect. This record lists, for each of the twenty columns, the claim the
Loop Engine row makes, the boundary that carries it, the checks that exist,
the attacks a skeptic would run to refute the claim, the audit questions a
reviewer answers, and the roadmap step that owns the work. A feature keeps
its Y only while the attacks fail and the audit answers hold. Roadmap step
S-1.12 runs this plan; each attack that is not yet automated is listed as
open.

Method for every feature: state the claim in one sentence; name the
authoritative module; run the existing checks and mutants; run each attack
and record whether it was refuted, confirmed, or not runnable offline;
answer the audit questions with evidence paths; record the result in the
roadmap status log with the commit.

## Memory

| Feature | Claim | Boundary | Attacks a skeptic runs | Audit questions | Owner |
|---|---|---|---|---|---|
| Persistent memory | Records survive across sessions in a store with identity and version. | `catalog/` adapters, `memory/storage` | Write, close the process, reopen, read: identical digest. Corrupt one row: the read refuses rather than guesses. Two processes write one identity: the precondition refuses the loser. | Which adapter is authoritative in each deployment shape? Where does a record's digest get checked on read? | S-2.10 |
| Graph or temporal facts | A fact holds over an interval; as-of queries never return a successor before its start. | `core/temporal_facts` | Assert overlapping facts on a functional predicate: refused. Query one second before a supersession: the old object. Supersede twice: refused. Namespace crossing: empty. | Is the interval boundary inclusive at the start and exclusive at the end everywhere? Does any path delete a fact? | S-1.1 (published), S-1.12 |
| Outcome changes retrieval | A verified outcome changes what a reused record is worth. | `core/reuse_evidence` | Feed a failure without a verified outcome: no change. Feed the same outcome twice: not double counted. Cite ten records: credit split. | Where is the evidence read during retrieval today? (Not yet: the label is computed, not consulted by the Retriever.) | S-1.12 open item |
| Memory versioning | Every previous version is kept; rollback is a new version that names its origin. | `catalog/versioning` | Revise with a stale expected version: refused. Roll back to a version that never existed: refused. Query active records: no revision appears. | Does any adapter overwrite a revision row? Is the revision digest equal to the content digest of the original? | S-1.2 (published) |
| Multi-agent shared memory | Writes are signed by a member; reads are filtered by membership and visibility. | `core/shared_memory_scopes` | Write as a non-member: refused. Read a members-only scope as a stranger: refused. Two members write the same identity with the same expected version: one loses by name. Query another scope's namespace through a scope: refused. | Is the writer identity taken from the caller's authenticated identity or from a parameter? (Parameter today; the service surface must bind it to the tenant.) | S-1.3 (published), S-4.2 |

## Procedures

| Feature | Claim | Boundary | Attacks | Audit questions | Owner |
|---|---|---|---|---|---|
| Procedures as instructions | Question forms, strategies, and packs are typed records a model reads at run time. | `strings/question_engine`, `strings/ask_strategies` | Render a form with a missing slot: refused. Change a form's template: its digest changes and a recorded run still names the old digest. | Are the forms addressable through the catalog contract or only through code? (Code today; S-2.10 moves them.) | S-2.10 |
| Executable code reuse | Qualified capabilities and registered resolvers run without a model interpreting them. | `core/reusable_capability_*`, `core/adaptive_practitioner_deterministic` | Register a resolver that returns without `verified` true: the fast path records a failed verification, never a completion. Register a resolver that raises: the trace names the exception and escalates. | Is live reuse measured? (No live measurement yet.) | S-3.2 |
| Executes code or tools | Generated projects run in a confined workspace or sandbox under declared effects. | `core/workspace_backends`, `core/generated_project` | Path traversal in a generated file: refused before any write. A command not declared: refused. A raw-host fallback after a sandbox failure: never. | Which sandbox is used in each deployment shape and how is its digest recorded? | S-4.1 |
| Standalone solution export | The exported package runs in an interpreter that cannot import the engine. | `code_nodes/solution_export` | Plant an `import loop_engine` in an exported file: export refuses; a tampered file after export fails the manifest check; remove the interpreter isolation flags: the leaked import check must fail (mutant killed). | Does the exported entry point read anything outside its package and its declared inputs? | S-0.5 (published) |

## Assurance

| Feature | Claim | Boundary | Attacks | Audit questions | Owner |
|---|---|---|---|---|---|
| Independent verification | A separate process judges the outcome; the producer's report is not the verdict. | `core/independent_verification` | Make the producer emit a passing report with no artifact: verification fails. Reuse a retained probe on a changed subject: the failed-check review must classify it. | Can the same model route that produced the work also verify it? (Yes today; confirmation on a different route is open.) | S-3.3 |
| Evaluation product | A frozen population, deterministic graders, exact denominators. | `core/evaluation_suite` | Solver raises: counted as errored, never as a pass (mutant killed). Compare two reports over different populations: refused. Change a case after the report: digests differ. | Are model-judged graders offered? (No; deliberate.) | S-1.4 |
| Per-implementation cost records | Every capability call writes one cost record; unknown counts stay unknown. | `core/operation_cost_capture`, `CapabilityDirectory` | Call through a directory without a ledger: no record, no crash. Report zero tokens without a provider count: refused by the record type. Remove the capture: the directory check fails (mutant killed). | Are model gateway calls captured as well as directory calls? (Directory yes; the gateway path is open.) | S-1.5 (published), S-1.12 open item |

## Selection

| Feature | Claim | Boundary | Attacks | Audit questions | Owner |
|---|---|---|---|---|---|
| Model routing | Routes are chosen per request by declared purposes, tiers, and health. | `core/model_routes`, `core/model_gateway` | Request a purpose no route declares: refused. Disable failover and make a route fail: no cross-provider call. | Is the chosen route recorded on every call record with its profile? | S-1.12 open item |
| Model versus non-model choice | A decision record names the candidates, the evidence, and the choice. | `core/implementation_choice` | Give the cheapest candidate a low verified rate: passed over (mutant killed). Mark every candidate unavailable: refused. | Is the decision consulted by a live solve before a model call? (Written by conformance escalations; not yet consulted by the Practitioner route.) | S-1.6 (published), S-2.1 wiring |
| Harness or prompt optimization | A cell is accepted only when it gains on train and does not lose on holdout. | `core/configuration_optimizer` | Memorize the training cases: refused (mutant killed). Sample and claim exhaustive: refused (mutant killed). | Are prompt elements and response style axes yet? (No; S-2.7.) | S-1.7, S-2.7 |
| Trains or exports specialists | A specialist is trained on a run-level split and measured on held-out runs. | `core/specialist_training` | Leak a run across the split: refused (mutant killed). Claim verification from a specialist answer: never (mutant killed). | Is any specialist qualified? (None; all candidates.) | S-1.8 (published), S-2.5 |

## Business

| Feature | Claim | Boundary | Attacks | Audit questions | Owner |
|---|---|---|---|---|---|
| Open source core | The engine is MIT licensed. | `LICENSE`, `pyproject.toml` | Import a dependency with an incompatible license into the core: the packaging review refuses. | Are optional extras' licenses declared (LGPL dependencies named)? | S-1.10 |
| Self-hosted option | The image and manifests run on the customer's cluster. | `Dockerfile`, example 28 | Remove resource limits from a manifest: example 28 fails. Bake a secret shape into the image: refused. | Has the image been built and its digest recorded? (Not yet.) | S-4.1 |
| Hosted cloud | Not claimed. | `core/service_api` | Call without a key: 401 before any work (mutant killed). Use an endpoint the tenant lacks: 403 (mutant killed). | Is an endpoint operated? (No.) | S-4.4 blocked |
| Public pricing | Not claimed. | packaging guide | A tier that meters outcomes: fails review. | Has the owner set a price? (No.) | S-4.5 blocked |

## Open items this plan adds to the roadmap

- Reuse evidence is computed but not consulted by the Retriever at
  retrieval time (Outcome changes retrieval).
- Cost capture covers directory calls; model gateway calls still need the
  same record (Per-implementation cost records).
- The implementation decision is written by conformance escalations but
  not consulted by the Practitioner's route step (Model versus non-model
  choice).
- The shared memory writer identity is a parameter; the service surface
  must bind it to the authenticated tenant.
- Verification on a different model route from the producer is not
  implemented (Independent verification).

Each becomes an attack that currently succeeds and is recorded as open
under S-1.12 until its boundary changes.
