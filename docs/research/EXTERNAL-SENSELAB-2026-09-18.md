# External research: SenseLab and the memory layer it sells

Date: 2026-09-18. Requested by the owner, who asked for a closer look at
SenseLab after noting that it appears to be missing code reuse and tool
reuse. This record separates what SenseLab states about itself, what could
be verified from public sources on this date, how each part maps to a Loop
Engine boundary, and what Loop Engine should and should not borrow. It makes
no claim about SenseLab's measured performance and cites no benchmark.

## Sources read on 2026-09-18

- [The product site](https://www.sense-lab.ai/) (positioning, features,
  integrations, pricing, and customer claims).
- [The documentation](https://docs.sense-lab.ai/) (memory model, versioning,
  rooms, briefings, programming interface operations, self hosting).
- [The public repository](https://github.com/raia-live/amfs) (Apache 2.0
  license, Python, 76 stars, created 2026-03-31, last pushed 2026-09-18).
- The architecture diagram the owner supplied (an agent layer over a
  knowledge engine, a distribution layer, and a versioned timeline).

Every statement below that comes from these sources is a vendor statement
unless it says otherwise. The marketing claims of "87 percent less manual
work", "4 times faster execution", and "zero errors in workflows" are quoted
without endorsement; no method, population, or evaluator is published for
them.

## What SenseLab says it is

SenseLab positions itself as "continual learning for artificial intelligence
agents": a shared memory that agents read before they act and write after
they act, with the outcome of each action fed back into the confidence of
the entries that informed it. The vendor architecture has four parts.

```text
SenseLab as described by the vendor
├── Agent layer
│   ├── coding assistants and editors through the Model Context Protocol
│   ├── orchestration frameworks through a software development kit
│   └── custom agents through web endpoints and the same kit
├── Knowledge engine
│   ├── confidence scoring weighted by what worked in production
│   ├── hot, warm, and cold tiers
│   ├── hybrid search and dynamic surfacing
│   └── briefings compiled from ranked digests
├── Distribution layer
│   ├── cross-agent sharing and reading through rooms
│   ├── provenance tracking and conflict detection
│   └── a team-wide knowledge graph
└── Versioned timeline
    ├── copy-on-write versions with rollback
    ├── branches held until reviewed, then merged
    └── an audit log with decision traces and lineage for every entry
```

The documented memory model records, for each agent action, the task, what
was read, the action taken, and the outcome. Confidence then propagates
backward to the entries that were read. The programming interface exposes
identity, briefing, search, read, write, and outcome commit operations. A
slower loop over months turns the accumulated decision traces into
supervised fine tuning and preference optimization data and, in the hosted
plan, into tuned models. Self hosting offers filesystem, Postgres, and object
storage adapters. Pricing on this date was a free tier of one thousand
operations per month, a starter tier at 29 dollars per month for twenty five
thousand operations, and a professional tier at 149 dollars per month for
fifty thousand operations.

## What SenseLab does not describe

The owner's observation holds on the public material. The documentation
describes storing decisions and their outcomes. It does not describe:

- storing procedures, skills, or tool definitions, so an agent cannot
  retrieve a tool it wrote last week and run it again;
- storing code with an immutable source identity, license state, tests, and
  a digest, so nothing in the memory is executable intelligence;
- executing anything, verifying anything, or accepting a task, so the
  outcome it learns from is whatever the calling agent reports;
- typed contracts on what an entry means, so a briefing is prose, not a
  record a program can check;
- independent qualification of an entry before it becomes trusted, beyond
  the confidence score that its own outcomes produce;
- budgets, permissions, effects, or sandboxes, because the product stops at
  memory.

In Loop Engine terms, SenseLab covers part of Context Intelligence and part
of Runtime History and Solution Intelligence. It has no Code Intelligence,
no User Feedback Intelligence as a distinct layer, no execution, and no
independent verification. That is not a criticism of the product's scope;
it is the boundary the owner noticed.

## Mapping to Loop Engine boundaries

| SenseLab part | Nearest Loop Engine boundary | Status in Loop Engine on 2026-09-18 |
|---|---|---|
| Read before acting, write after acting | Context Intelligence serve and search Loops; Runtime History records | Implemented as typed references and run records; retrieval never promotes an entry. |
| Outcome confidence propagated to the entries read | `reuse_observation_port`, the reuse tiers, the decision outcome ledger | The ledger records decisions and outcomes; back propagation of an outcome to every entry a step read is not implemented. |
| Hot, warm, and cold tiers | Reuse tiers and cost routing | Documented as tiers by cost; not yet a retention policy on records. |
| Briefings compiled from ranked digests | Context compilation into the canonical semantic packet | Implemented as context blocks with digests; a compiled per-task briefing record is not a separate artifact. |
| Rooms shared by several agents | Task working folder and scoped views for Spawned Loops | The working folder exists; scoped views are not implemented. |
| Copy-on-write versions, branches held until review | Candidate-only intelligence, independent qualification, promotion | Implemented as statuses on records; there is no branch and merge operation on a memory store. |
| Decision traces and lineage | Stage and action lineage, `llm_work_packet_assembled`, model call records | Implemented; the new model call record keeps digests and counts per call. |
| Training data from decision traces | Learnable model call records and the training export planned in the audit backlog | Not implemented yet; the suggested output and contract identifiers landed on 2026-09-18 are the grouping keys it needs. |
| Compliance audit log | Run History, immutable revision artifacts, managed records | Implemented for runs and managed records. |
| Tuned models from the slow loop | Custom trained models under the model ontology | The ontology admits a custom trained model with a training record digest; no training pipeline exists. |

## What to borrow, and where it belongs

1. Outcome back propagation. When an independent verification passes or
   fails, the entries a step read should receive that outcome, not only the
   step. This belongs in the decision outcome ledger and the reuse
   observation port, keyed by the context block digests the packet already
   records. It must remain evidence about reuse, never a promotion.
2. A briefing record. The compiled context for one task should be a record
   with its own digest and the digests of what it compiled, so two runs can
   be compared by what they were told. This belongs beside the context pack
   manifest.
3. Branches held until review. Loop Engine already keeps candidates apart
   from active intelligence. What it lacks is the explicit merge decision
   record naming which reviewer accepted which candidate version. This
   belongs in the promotion path of each intelligence layer.
4. Retention tiers as policy. Hot, warm, and cold should be a declared
   policy on records with measured access, not a folder name.

What not to borrow: a memory that learns from the calling agent's own report
of success. Loop Engine's rule stays: an outcome that feeds learning comes
from an independent verification, a deterministic check, or the owner, and
never from the producer's own confidence.

## Where Loop Engine already goes further

- Code Intelligence: a tool written during a run stays a candidate until a
  different process qualifies it, then becomes executable intelligence with
  a source identity, contract, effects, tests, and a digest.
- Execution and verification: the engine runs the work in a path confined
  workspace or a declared sandbox and accepts it only through independent
  verification.
- Typed contracts: every record that feeds learning has a record type, a
  version, and a digest; every model step now names its response contract
  and may carry a suggested output shape.
- Authority: budgets, permissions, effects, and secrets are typed fields, so
  memory can never grant what the run was not given.

## Source inspection of raia-live/amfs at b9547b4 (2026-09-18)

The owner asked for the whole repository, not the product page. The
repository was cloned in full outside the checkout and read at commit
b9547b4 (539 commits, three contributors, created 2026-03-31, Apache 2.0).
Its 100 test files were not run. Everything below is what the code and the
repository's own documents say; the numbers are the vendor's measurements.

```text
raia-live/amfs packages
├── core: models, engine, evidence, labels, actions, outcome, reuse_value,
│   tiering, capture, authority, aggregates
├── cortex: briefing compiler, consolidator, trace miner, worker
├── patterns: detector
├── adapters: filesystem, postgres, s3, http
├── sdk-python, sdk-typescript, cli, http-server, mcp-server (40 tools)
├── integrations: autogen, crewai, langchain, langgraph, strands
└── benchmarks/continual_learning: preregistered arms, scenarios, analysis
```

### The evidence model is the part worth studying

`packages/core/src/amfs_core/evidence.py` replaced the fixed multipliers the
documentation still describes (times 1.03 on success, times 0.90 on
failure) with a recency-weighted Beta posterior:

```text
confidence = (PRIOR_STRENGTH * prior + E_s) / (PRIOR_STRENGTH + E_s + E_f)
w = severity(outcome) * causal_confidence / n_causal * (1 + |target - confidence|)
```

The evidence masses decay by 0.8 on every update so the last few outcomes
dominate. The last factor is a surprise term: a failure on an entry trusted
at 0.95 counts nearly twice as much as one on an entry at 0.5. Dividing by
the number of cited entries is a credit split: an outcome that cited eight
entries cannot hand each of them a full unit of evidence. A first failure on
an entry with at least three successes and no failure is weighed without
surprise, so one noisy failure leaves a long-validated rule contested at
about 0.62 instead of discrediting it; a second failure discredits it. A
regime shift is an event, not a permanent mark: at least three successes, a
recent failure inside a seven-day window, and an evidence label that is no
longer validated. `inherit_evidence` carries the evidence forward when a
rewritten entry restates the same claim and starts it untested when the
claim changed. A fail-then-succeed outcome record produces a contrast
lesson ("these entries led to a failed attempt; the task was resolved
without them") under a synthetic key prefix that training and evaluation
pipelines exclude.

`labels.py` separates the label an agent sees from the score: validated,
contested, or discredited, with a posterior rule (at least 0.7 over at least
two outcomes, or at least four wins with at most one loss) and a strict rule
kept for callers that need every outcome to have succeeded. The vendor's
own benchmark note says agents abandoned working rules after a single noisy
failure when the label was strict; that is the same failure the first-strike
rule addresses.

### Action priors: the newest mechanism

`actions.py` (merged the day of this reading) turns committed outcomes into
action-level priors: an action key is the tool name plus a short action
value; priors come from the twenty nearest past outcomes by task embedding
with cosine similarity of at least 0.75 and a daily decay of 0.9; the
recommendation is act on a validated rule or a winning action (posterior at
least 0.6 over at least two outcomes), explore an untried action assigned
per agent by a stable bucket so a fleet spreads its search, or escalate when
everything a caller could try has already failed. A regime shift skips the
winning priors whose wins predate the shift. The motivating case in the
docstring: a support fleet spent 24 attempts per class on the same two
failing actions and never tried the one that worked.

### Other mechanisms read in the code

- `capture.py`: one scanner for keys, connection strings, and customer
  data runs wherever a decision trace is built, after the vendor found the
  Model Context Protocol path storing raw text while its documentation
  promised redaction. This is the rule Loop Engine already keeps for
  events, reports, and traces.
- `reuse_value.py`: the reuse block a read returns leads with the counted
  fact (memories reused, times reused before) and labels the token figure
  an estimate; the vendor removed an instruction that told the model what
  to say first.
- `tiering.py`: a priority score of the form (alpha times importance plus
  beta times recency) times a frequency boost times time decay, from a
  paper the code calls HMO, drives hot, warm, and archive tiers.
- `authority.py`: one scorer answers who should be trusted first on a
  topic and produces the explaining sentence with the score.
- Cortex consolidation has two risk tiers: auto-safe changes (a belief
  superseded by a fact on the same key; zero-recall, zero-outcome pruning)
  and proposal-required merges (three or more agents converging above 0.9
  similarity; five or more experience entries all with outcomes), the second
  implemented in the closed package.
- Models: an entry carries outcome counts, evidence masses, prior
  confidence, discredit time, up to ten validators, recall count, tier,
  importance, time to live, embedding, artifact references, a memory type
  (fact, belief, experience), branch, content hash, integrity chain, and
  commit identifier. Outcome types are success, minor failure, failure,
  critical failure, clean deploy, regression, and two incident severities.
- The Model Context Protocol server exposes 40 tools, including
  `amfs_set_contract` (minimum confidence, required fields, and a time to
  live on writes under one path), `amfs_declare_capability` and
  `amfs_discover_agents`, `amfs_verify` (content hashes and integrity
  chains), `amfs_retrieve` with priors and candidate actions, and
  `amfs_export_training_data` in supervised fine tuning, direct preference
  optimization, and reward model formats, which needs the closed server.

### The benchmark is preregistered and its first result is negative

`benchmarks/continual_learning/HYPOTHESIS.md` (written 2026-09-16) compares
seven arms (none, pgvector, pgvector with reflection notes, Mem0, Zep,
SenseLab, SenseLab without outcome feedback) over six seeds, one agent and a
six-agent fleet, forty episodes, with scenarios for triage, diagnosis,
runbooks, drift, handoff, and realistic tasks. Its discipline matches Loop
Engine's: no episode repeats, the generic answer is wrong where the domain
has hidden quirks, and failure feedback is what the real system would say,
never the answer key. The vendor states that recall was found at parity with
a plain vector baseline and that the claim is convergence through
reconciling outcomes over the exact read set.

`IMPROVEMENTS.md` records the first regime-change run (97 changed-class
tasks per arm): a stale-pick rate of 13 to 16 percent for every memory arm
with no downward trend over eight exposures; SenseLab with and without
feedback indistinguishable on every metric; first-attempt success of 0.54
to 0.62 against 0.66 for no memory; 4.9 to 7.3 thousand tokens per episode
against 0.95 thousand for no memory; 25 seconds of wall time against 10 for
pgvector. The evidence model and the action priors above are the vendor's
response to that run. For Loop Engine the lesson is direct: retrieval that
is not selected by verified outcomes can cost five to seven times the tokens
and lower first-attempt success, so Context Intelligence must report a
stale-pick rate and tokens per episode per configuration, not only recall.

### What this changes in the mapping above

| AMFS mechanism | Loop Engine boundary | Decision |
|---|---|---|
| Surprise-weighted, credit-split Beta evidence with decay and first-strike tolerance | Reuse observation port and decision outcome ledger | Adopt as the evidence update for reuse observations, keyed by the context block digests the packet records; keep the lifecycle status (candidate, qualified, retired) separate from the evidence label (validated, contested, discredited). |
| Regime shift as a windowed event | Supervision policy and recovery | Adopt as a typed signal that a previously validated procedure stopped working; it feeds the failed-check review, it does not retire anything by itself. |
| Contrast lesson with a synthetic key excluded from training | Failed-check review records and the training export | Adopt: a fail-then-succeed run writes a derived record with a synthetic marker the export excludes. |
| Action priors with explore assigned per agent | Campaign cells and the recovery panel | Adopt the search-spreading rule for repeated trials: a cell that failed on the same route twice explores an untried registered route before repeating. |
| Memory contract on writes | Typed records | Already covered by record types, versions, and digests. |
| Capture sanitising in one place | Secret patterns in forbidden paths | Already covered for source and records; the training export must run the same scan on every exported string. |

### Comparable projects, verified on 2026-09-18

| Repository | Stars | License | Created | Last push | Relation to Loop Engine |
|---|---|---|---|---|---|
| raia-live/amfs | 76 | Apache 2.0 | 2026-03-31 | 2026-09-18 | Outcome-linked memory; no code, tool, or skill reuse; no execution or verification. |
| mem0ai/mem0 | 65,589 | Apache 2.0 | 2023-06-20 | 2026-09-18 | Fact extraction with add, update, delete operations; procedural memory in the Python package only. |
| getzep/graphiti | 30,985 | Apache 2.0 | 2024-08-08 | 2026-09-17 | Temporal knowledge graph with edge invalidation at write time. |
| topoteretes/cognee | 30,809 | Apache 2.0 | 2023-08-16 | 2026-09-18 | Memory platform with a graph; no outcome feedback. |
| letta-ai/letta | 24,786 | Apache 2.0 | 2023-10-11 | 2026-09-10 | Stateful agents with tiered memory inside the agent runtime. |
| MemTensor/MemOS | 11,454 | Apache 2.0 | 2025-07-06 | 2026-09-18 | Memory with a local skill plugin; skills are prompt guides, not executables. |
| getzep/zep | 4,919 | Apache 2.0 | 2023-04-29 | 2026-09-18 | Hosted memory over Graphiti. |
| langchain-ai/langmem | 1,671 | MIT | 2025-01-21 | 2026-09-09 | Memory utilities for one framework. |

None of these executes code, verifies a deliverable, or keeps a tool as a
qualified executable capability. The vendor's own comparison table claims
outcome back-propagation, causal explainability, and conflict detection as
unique to AMFS among them; that table was not verified against the other
repositories here beyond the metadata above.

## Competitive note for the owner

SenseLab sells the memory layer to agents that other vendors run. Loop
Engine's position is different: it owns the run, the execution, the
verification, and the four intelligence layers, and a memory product can be
one adapter behind Context Intelligence. If an acquisition or partnership
conversation arises, the relevant facts are that SenseLab's public
repository is small and Apache 2.0 licensed, its differentiators are outcome
weighted confidence and a git-like timeline over prose entries, and its
missing pieces are exactly the executable, verified, typed layers Loop Engine
already has. None of that is a statement about its revenue, customers, or
roadmap, which were not verifiable from public sources on this date.
