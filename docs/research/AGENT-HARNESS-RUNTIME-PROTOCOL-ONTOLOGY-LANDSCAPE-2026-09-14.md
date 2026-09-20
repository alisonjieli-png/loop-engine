# Agent harnesses, runtimes, protocols, ontologies, and verification

Status: research record, September 14, 2026. Nothing in this record is
implemented in Loop Engine unless a sentence says so. Every build item is a
proposal until an implementation and its discriminating test exist.

Note added on September 20, 2026. The text below is unchanged. It describes
Model Context Protocol revision `2026-07-28` and proposes an adapter profile
for it. That proposal is not implemented. The Loop Engine service accepts
exactly `2025-11-25` and refuses `2026-07-28`. The current fact is stated
once, in
[current deployment](../architecture/MVP-CLIENT-SERVER.md#current-deployment).

## How this record was produced

The owner shared a research synthesis that described a converging stack of
model, harness, typed execution graph, semantic ontology, provenance ledger,
and evaluation, and asked for more research, tools, ideas, and best practices.

Six research passes checked every item the synthesis named against its
canonical source on September 14, 2026, and extended each area:

1. harness engineering and harness search,
2. agent graph runtimes, workflow engines, and durable execution,
3. portable agent specifications, protocols, identity, and supply chain,
4. ontology engineering, knowledge representation, and provenance,
5. emerging agent ontologies, skill libraries, tool graphs, and graph memory,
6. verification, observability, evaluation, and test oracle quality.

A seventh, read-only pass mapped the proposals onto this repository. Web
search allowances ran out during several passes, so later checks fetched
primary pages directly: arXiv, GitHub release data, package registries,
standards bodies, and vendor documentation. A few pages refused automated
fetches; the tables say so where it matters.

Status words used below:

- **Verified**: the canonical source confirmed the claim.
- **Partly verified**: the core claim holds, and the table names the
  correction.
- **Not found**: no source could be located.

## Summary

- **The synthesis is broadly right.** The field is converging on the stack it
  describes, and no single project combines all of it.
- **Several details needed correction.** Examples: Google Agent Development
  Kit 2.0 supersedes its sequential, parallel, and loop agents with
  graph-based workflows; the Model Context Protocol revision of July 28, 2026
  removed sessions and the initialize handshake; Skan's own pages disagree on
  the entities of its Agentic Ontology of Work; AGENT-O measures how
  completely papers report agent systems, not agent quality; Arize Phoenix
  uses Elastic License 2.0, which is source-available rather than open source;
  and Agentproof was evaluated on 18 workflows its authors built.
- **Loop Engine already holds much of the stack.** It has typed graph
  definitions, graph validation, a hash-chained Run History, managed record
  revisions, Code Intelligence admission, a skill registry, a Model Context
  Protocol client, OpenTelemetry export, and conformance checks driven by its
  terminology and architecture files.
- **The largest gaps are structural.** There is no portable graph export, no
  static policy verifier for Loop graphs, and no projection of the ontology
  or Run History into standard vocabularies. Contract fields are split
  across several types. The Model Context Protocol adapter speaks an older
  revision. Agent2Agent, Open Agent Specification, and OASF support is
  absent. There is no replay divergence check, and the benchmark records
  lack cost, human intervention, regression, and later-task improvement.
- **The defensible direction is not another agent framework.** Keep the Loop
  records authoritative, generate every semantic and provenance graph from
  them, verify graphs before execution, and treat every external format as a
  boundary that yields a candidate or a refusal.
- **Evaluation remains the keystone.** The verification research found that
  model-written checks tend to follow implemented behavior rather than
  intended behavior, that agents take shortcuts on impossible tests, and that
  mutation analysis is a sound gate against weakened checks. That evidence
  shapes the failed-check review in the
  [persistent general solving decision record](../architecture/ADR-PERSISTENT-GENERAL-SOLVING-AND-CONTRACT-FAILURE-REVIEW.md).

## The three-graph design, refined

The synthesis proposed a semantic graph, an execution graph, and a run and
provenance graph. The research supports that shape with one condition: each
graph is generated from an existing authority, never kept as a second store.

```text
Loop Engine knowledge
├── Semantic graph: generated projection, never a second authority
│   ├── Authority: terminology.yaml, architecture.yaml, typed Python contracts
│   ├── Projections: SKOS terms, SHACL shapes, JSON-LD context, SSSOM mappings
│   └── Checks: regeneration drift, lint rules, optional offline reasoning
├── Execution graph: the existing typed runtime
│   ├── Authority: LoopDefinition, LoopGraphDefinition, typed ports
│   ├── Projections: P-Plan plans and steps, portable specification export
│   └── Checks: port compatibility, exit reachability, policy paths
└── Run and provenance graph: an export of Run History
    ├── Authority: RunHistory hash chain and semantic records
    ├── Projections: PROV-O bundle per run, Workflow Run RO-Crate, spans
    └── Checks: SHACL shapes, independence query, digest agreement
```

Four refinements follow from the research:

1. **Generate, do not duplicate.** A separately edited graph would become a
   parallel source of truth, which the repository rules forbid.
2. **Keep authority in typed code.** Budgets, permissions, and approvals stay
   in fail-closed typed checks. Exports to PROV-O or ODRL serve audit, and an
   export is never imported back as a permission.
3. **Use stable standards at load-bearing boundaries.** RDF 1.2 and SHACL 1.2
   are not yet Recommendations, so load-bearing exports use RDF 1.1 patterns
   and qualified PROV terms, and newer features stay experimental.
4. **Treat every external description as a candidate.** Agent Cards, server
   metadata, OASF records, Agent Specification flows, and skill folders pass
   Loop Engine admission before they can influence execution.

## Verification of the named items

### Harness engineering

| Item | Status | What holds, and what changed |
|---|---|---|
| OpenAI, "Harness engineering: leveraging Codex in an agent-first world" (February 11, 2026) | Verified from three consistent secondary copies; the primary page refused automated fetches | A short AGENTS.md points into versioned repository documents, layered dependency rules are enforced by linters whose messages explain the fix, each worktree exposes the running application and its logs, and recurring agents open small cleanup changes. "Machine-legible architecture" is a paraphrase; the post speaks of legibility and mechanical enforcement. |
| Google, "The Anatomy of Harness Engineering" (September 9, 2026) | Verified | Behavioral evaluations assert on intermediate steps such as tool calls and file changes instead of final string equality, run in batches, and guard against regressions when prompts or models change. |
| "Code as Agent Harness" (arXiv 2605.18747) | Verified with a correction | A survey organized around code as interface, harness mechanisms, and multi-agent scaling. It reports no system or measurement of its own. |
| "Agentic Harness Engineering" (arXiv 2604.25850) | Verified | The model stays fixed while revertible harness edits live in version control. Each edit carries a prediction checked against which tasks flip. With GPT-5.4, the Terminal-Bench 2 pass rate rose from 69.7% to 77.0% over ten iterations. |
| OpenHands Software Agent SDK (arXiv 2511.03690; openhands-sdk 1.47.0) | Verified | Four packages (sdk, tools, workspace, agent-server), one workspace interface for local and remote execution, event-sourced state, and security analysis. |

### Agent graph runtimes

| Item | Status | What holds, and what changed |
|---|---|---|
| LangGraph (Python 1.2.11) | Verified | Checkpointers support human approval, time travel, and fault tolerance. A resumed node restarts from its beginning, so effects before an interrupt must be idempotent, and replay from a checkpoint re-runs later nodes, including model calls. |
| Microsoft Agent Framework (Python 1.18.0) | Verified | Both AutoGen and Semantic Kernel name it as successor; AutoGen is in maintenance mode. Typed executors are validated at build time, and checkpoints fall at superstep boundaries. |
| LlamaIndex Workflows (2.23.3) | Partly verified | Typed event steps with loops and branches. "Durable" means resuming a serialized context, and resume is at least once, so step effects must be safe to repeat. |
| Google Agent Development Kit (Python 2.9.0) | Partly verified | Sequential, parallel, and loop agents exist, but version 2.0 supersedes them with graph-based and dynamic workflows. |
| Pydantic Graph (2.43.0) | Partly verified | Nodes are typed and edges come from return types. It is a separate package with no persistence module; durable execution in Pydantic AI runs through Temporal, DBOS, Prefect, Restate, or AWS Lambda. |
| OpenAI Agents SDK (Python 0.22.2) | Verified, still before 1.0 | A runner loop bounded by `max_turns`, handoffs, guardrails, sessions, tracing, and tool approval with a serialized run state that another process can resume. Durable execution comes from Temporal or DBOS integrations. |
| CrewAI Flows (1.15.21) | Verified | Start, listen, and router decorators; persisted state with resume or fork; human feedback pauses. |

### Portable specifications and protocols

| Item | Status | What holds, and what changed |
|---|---|---|
| Oracle Open Agent Specification (26.3.1) | Verified | Declarative JSON or YAML agents and flows with JSON Schema ports, component references, and adapters for LangGraph, AutoGen, CrewAI, WayFlow, Microsoft Agent Framework, and OpenAI Agents SDK. It holds no executable code. |
| OASF (v1.1.0) | Partly verified | Records annotated with skill and domain taxonomies and extended by modules. No documented core "relationships" concept was found, and two names are in use. |
| AGNTCY | Verified, with additions | A Linux Foundation project with a federated directory, encrypted messaging, identity, the SHADI hardened runtime, and observability and evaluation. |
| Agent2Agent (1.0.1) | Verified | Agent Cards, tasks, messages, artifacts, and extensions; signed cards; a required version header with typed refusals; no registry interface. It joined the Agentic AI Foundation on August 17, 2026. |
| Model Context Protocol (revision 2026-07-28) | Verified; the local adapter needs an update | The current revision removed sessions and the initialize handshake, added multi round-trip requests, moved tasks into an extension, and deprecated Roots, Sampling, and Logging. Loop Engine's adapter speaks revision 2025-11-25. |
| Agent Skills | Verified | An open specification since December 18, 2025, with progressive disclosure. It has no signature, dependency, or version field. |

### Ontology engineering

| Item | Status | What holds, and what changed |
|---|---|---|
| RDF 1.2 | Verified | Concepts and Semantics are Candidate Recommendations (April 7, 2026), not Recommendations. |
| OWL 2 | Verified | A 2012 Recommendation with an open-world assumption. Classification in OWL 2 DL is N2EXPTIME-complete in the worst case; the EL and RL profiles are PTIME-complete. |
| SHACL | Verified | A 2017 Recommendation. The SHACL 1.2 documents are Working Drafts, and the rules draft now appears as SPARQL 1.2 RL. |
| PROV-O and PROV-DM | Verified | 2013 Recommendations. Plan contents are out of scope, so P-Plan or EP-Plan is needed for step structure. |
| Protégé and WebProtégé | Verified | Desktop 5.6.9 (March 2026). WebProtégé was last tagged in 2020 and remains a hosted service. |
| Ontology Development Kit and ROBOT | Verified | ODK v1.6.1 and ROBOT v1.9.10 provide release workflows, reports with failure thresholds, query-based verification, diffs, and profile validation. |
| LinkML | Verified | linkml 1.11.1 generates JSON Schema, SHACL, OWL, Python dataclasses, Pydantic, SQL, and more from one schema. Its SHACL generator is beta. |
| OBO Foundry | Verified | 267 registry entries on September 14, 2026, with principles for stable identifiers, versioning, and term stability. |
| BioPortal | Partly verified | The live page refused automated fetches; counts come from its 2025 paper. |

### Emerging agent ontologies and skill graphs

| Item | Status | What holds, and what changed |
|---|---|---|
| Skan Agentic Ontology of Work | Partly verified | Launched February 10, 2026. The whitepaper page lists nine entities, the product page twelve, and the press release a third set. No schema file, repository, or evaluation was found. |
| AGENT-O (arXiv 2608.28345) | Verified, with a scope correction | An OWL 2 and SHACL "semantic Agent Card" that scored how completely 279 papers report agent systems. Its authors say it does not assess agent quality or deployment readiness. |
| Ontology-to-tools compilation (arXiv 2602.03439) | Verified | OWL definitions compiled into Model Context Protocol tools that check classes, datatypes, units, and cardinality, with micro-F1 0.826 on 30 chemistry papers. One ontology, one domain, and no schema change test. |
| SciToolAgent-Evo (arXiv 2607.28692) | Verified | A skill library, an experience pool, and an ontology-annotated tool graph. A tool joins after one successful use with no separate test, and nothing is ever removed. |
| Graph-of-Skills (arXiv 2604.05333) | Verified | Retrieves bounded skill bundles by dependency. Headline figures changed between paper versions, and all results come from the authors. |
| Microsoft GraphRAG (3.1.2) | Partly verified | Its evaluated strength is corpus-wide summarization, not general retrieval, and its README describes the project as largely in maintenance mode. |
| Neo4j GraphRAG for Python (1.19.0) | Verified | A library with retrievers and schema-guided graph construction, without a published evaluation. |

### Verification and observability

| Item | Status | What holds, and what changed |
|---|---|---|
| Agentproof (arXiv 2603.20356) | Partly verified | Extracts one graph model from LangGraph, CrewAI, AutoGen, and Google Agent Development Kit, runs six structural checks, checks safety temporal policies by a graph and automaton product search, and runs the same monitors on traces. It was tested on 18 workflows its authors built, and human approval steps are found by name heuristics. |
| OpenInference | Verified | Vendor-led tracing conventions beside OpenTelemetry with ten span kinds, separate from the official generative AI conventions. |
| Arize Phoenix (20.11.0) | Partly verified | Tracing, evaluation, datasets, and experiments. Elastic License 2.0 is source-available, not an approved open source license. |
| Langfuse Agent Graphs | Partly verified | Aggregated and expanded graph views exist. No aggregate tool-call analysis was found, and trace-level evaluators are deprecated in version 4. |

## What Loop Engine already has

| Proposal in the synthesis | Closest existing implementation | Status | Gap |
|---|---|---|---|
| Universal graph representation | `LoopGraphDefinition` and `LoopDefinition` in `code_nodes/solution_graph.py` and `loop/loop_definition.py`, compiled by `compile_solution` and `build_solution_graph` | Implemented and tested for Solution Loops | Graph validation refuses non-Solution vertices, and output is limited to Mermaid, JSON, and text views. No export or import of portable specifications. |
| Static graph verification | `validate_loop_graph` (unbound inputs, cycles, outputs), `validate_loop_connection` (effect ceiling, modes), conformance gates | Partial | No exit reachability from every vertex, no dead-end check, no effect-path approval check, no temporal policies or witness traces. |
| Ontology-to-Loop compilation | `terminology.yaml`, `architecture.yaml`, the semantic data dictionary, `ontology/catalog.py`, and the Loop profile catalog | Enforced, not compiled | The ontology drives conformance and generated pages but generates no Loops, tools, validators, or standard projections. |
| Event-sourced run graph | `RunHistory` with hash chain and `consumed_refs` and `produced_refs`; `RecordOperationService` with revision links | Implemented and tested | No PROV mapping and no fork interface; replay means playback, not re-execution. |
| Harness benchmark | Embodiment lab campaigns, `ConfigurationSpace`, `trial_evidence_report`, DuckDB experiment records | Partial | Cost is always unknown, and human intervention, regression, and later-task improvement are not recorded. |
| Trusted skill and capability graph | `CodeAssetAdmissionRecord` (producer cannot be sole verifier), `SkillRegistry.admit`, reusable capability gates | Partial | Dependencies are a flat tuple; there are no edges between skills or tools and no signatures. |
| Memory and reference kinds | `LoopValueRef`, `MemoryRef`, `ContextArtifactRef`, `InformationScope`, run note board | Partial | No single list of reference kinds, no stream reference, no dedicated secret reference type. |
| Loop definition fields | `LoopDefinition`, `LoopContract`, `LoopConfig`, `SemanticLoopContractDraft` | Split across types | Preconditions, postconditions, evidence, and risk exist only on the semantic draft; budget and escalation are untyped facts; approval, retry, and memory references are not definition fields. |
| Telemetry conventions | `run_history_to_spans` in `core/otel_export.py` with allowlisted attributes | Partial | Only model spans borrow a generative AI name; no agent or tool span names, no trace context propagation. |
| Boundary formats | `McpRegistry` (client, four transports), `SkillRegistry` (progressive loading), plugin bundles | Partial | Model Context Protocol revision 2025-11-25 only; no Agent2Agent, Open Agent Specification, or OASF support; AGENTS.md is guidance, not parsed. |

## What to build, in order

The order puts the owner's September 14 direction first: evaluation that can
be trusted and persistence within declared authority. Each item names the
owning boundary and a test that shows whether it helps.

### First: trustworthy evaluation and persistence

1. **Failed-check review waterfall.** Owner: independent verification with
   Spawned verifier Loops. Stages, cheapest first:
   - freeze the failure record with digests of subject, check, and image;
   - rerun in a fresh pinned sandbox to separate flaky checks and
     environment defects;
   - qualify the check against a reference solution, trivial outputs, and
     mutants of the subject;
   - recompute the expected value blind, before seeing the check's value;
   - test specification fit through a declared comparison ladder;
   - probe ambiguity through independent interpretations;
   - adjudicate by rule, with abstention when evidence is insufficient.

   A revised check must cover the same criteria or more, kill every mutant
   the old check killed, still reject trivial outputs and known-wrong
   candidates, pass the reference, and stay stable over reruns. The producer
   sees checks read-only and has a typed "check conflicts with the task"
   exit. Test: on a seeded set containing a wrong expectation, an
   over-strict comparison, a flaky probe, an environment defect, and a real
   code defect, the real defect is never classified as a check defect.
2. **Typed independence and evaluation mode.** Owner: independent
   verification records. Replace the fixed independence string with fields
   for route, provider, and model family of producer, check author, and
   reviewer, and record each check's evaluation mode. Test: a policy that
   requires a different model family is refused when every role shares one
   route.
3. **Persistence fixes.** Owners: solve request adaptation, the Practitioner
   kernel, recovery, and routing. Carry a supervision policy on
   `SolveRequest`; route every format repair stall, including orientation and
   verification, to recovery; send the recovery panel's route through the
   action vector guard; give the independent verifier JSON repair; resume
   interrupted campaign cells without a restart collision. Test: a fixture
   whose first repairs fail but whose reframed request succeeds reaches the
   accepted result, and a fixture with an exhausted declared budget ends
   with `BUDGET_EXHAUSTED` and no extra call.

### Second: durable execution and graph checks

1. **Static Loop graph verifier.** Owner: Solution Canvas compilation and
   conformance. Check exit reachability from every vertex, dead ends,
   unbounded cycles, and effect paths without an approval gate; express
   safety policies in a small temporal language and return witness paths;
   run the same policies as monitors over Run History. Test: a canvas with an
   unreachable exit is refused before compilation, and a policy violation
   yields a witness path.
2. **Replay divergence check.** Owner: Run History and playback. Re-execute
   with recorded model and tool results, compare each new request with the
   recorded event, and record a typed divergence at the first mismatch. Test:
   an unchanged replay makes zero physical calls; inserting one step stops at
   the first differing sequence number.
3. **Pin runs to the compiled canvas digest.** Owner: Solution Canvas and Run
   History. Resume refuses a different digest unless a typed patch record
   names the change. Test: resuming a changed canvas is refused and names
   both digests.
4. **Effect idempotency and uncertain commits.** Owner: effect approval.
   Every external effect carries a scoped key and a parameter digest, moves
   through requested, dispatched, confirmed, and uncertain states, and cannot
   be retried while uncertain. Test: a process killed between dispatch and
   confirmation reconciles first, and the fake mailbox holds one message.
5. **One retry owner across nested harness layers.** Owner: budget and the
   outer Loop. Test: with an always-failing provider, physical calls equal
   the owning layer's limit, not the product of both layers' limits.
6. **Declared cancellation and approval waits.** Owner: Spawned Loops and
   effect approval. Each spawn declares cancel, abandon, or terminate; an
   approval wait binds its token to the effect digest and never re-runs the
   steps before it. Test: a token for a different digest is refused, and a
   correct approval sends once.
7. **One Loop contract.** Owner: `LoopDefinition`. Make preconditions,
   postconditions, required evidence, risk, retry, escalation, approval
   requirements, and memory references typed definition fields. Test: a
   definition with an effect and no approval requirement fails validation.

### Third: boundaries and semantics

1. **Model Context Protocol revision 2026-07-28.** Owner: the adapter. Add
   the stateless profile with discovery, per-request metadata, and multi
   round-trip requests, keeping 2025-11-25 as an ordered fallback, and map
   input requests to typed clarification or approval. Test: each profile
   succeeds only against a server of its own revision, and an input request
   on an effectful tool is never answered automatically.
2. **Agent2Agent adapter.** Owner: a Loop that holds the budget and
   acceptance. Import Agent Cards as capability candidates with verified
   signatures and an exact version. Test: a remote task reported complete
   whose artifact fails the owning Loop's evaluator is recorded as observed
   but not accepted.
3. **Attested Code Intelligence and skills.** Owner: Code Intelligence
   activation. Export in-toto statements over the existing asset digests,
   sign them with Sigstore or OpenSSF Model Signing, and require verified
   signatures for skill admission. Test: one changed byte in a signed skill
   script blocks admission, and a verification attestation signed by the
   producer's own identity fails activation.
4. **Standard projections of the ontology and Run History.** Owner: semantic
   conformance and Run History export. Generate SKOS terms with deprecation
   and replacement from `terminology.yaml`, SHACL shapes for exported
   records, a JSON-LD context for the ontology index, SSSOM mappings to PROV
   and P-Plan, and a PROV-O bundle per run with a query that flags
   verification that is not independent. Test: removing a term without a
   deprecation entry fails, and removing one generation link from an export
   yields exactly one shape violation.
5. **OpenTelemetry generative AI alignment.** Owner: `core/otel_export.py`.
   Emit agent, tool, workflow, and plan span names, propagate trace context,
   and record the convention version. Test: a model call without provider
   usage exports no token attribute rather than zero.
6. **Portable workflow import as candidates.** Owner: Solution Canvas. Import
   Open Agent Specification and Arazzo flows as candidate canvases with named
   missing fields for budget, exit condition, and authority, and export
   projections that list dropped fields. Test: a cyclic flow without an exit
   condition yields a candidate with a named missing field, never an
   executable canvas.

### Fourth: harness evaluation and self-improvement

1. **Behavioral assertions over Run History.** Owner: evaluation records.
   Assert tool invocations, file writes, verification before completion, and
   typed clarifications, separately from output checks. Test: on trajectories
   that claim completion without running tests, action assertions catch what
   output checks miss.
2. **A control arm and consistency metrics.** Owner: the harness adapter and
   campaign reports. Register a bash-only, linear-history harness as a
   control for every comparison, and report pass over k repeated trials next
   to single-attempt success. Test: any richer harness profile that does not
   beat the control with the same model, tasks, and budget is flagged.
3. **Honest search reporting.** Owner: configuration search. Record tuning,
   validation, and held-out scores for the submitted configuration, keep a
   Pareto portfolio with per-task selection and abstention, and require every
   staged harness change to predict which tasks it will flip. Test: replaying
   existing campaign records shows whether reports based on the best
   validation score overstate improvement.
4. **Skill and tool library hygiene.** Owner: Code Intelligence and Context
   Intelligence. Admit an item only after tests its builder never saw,
   measure each skill with paired runs and keep negative results, report
   harmful near-duplicate exposure beside recall, retrieve bounded bundles by
   dependency closure, requalify after dependency changes, keep validity
   windows instead of deleting facts, keep raw trajectories beside distilled
   skills, and screen imported skills before granting any effect. Test: a
   candidate that passes its own tests but fails a hidden suite is refused,
   and removing the requirement lets it through.
5. **Sandbox backends as typed policy.** Owner: the sandbox and effect policy.
   Declare the isolation backend (Landlock or nsjail confinement, gVisor, or a
   Firecracker virtual machine), keep network access off by default, and
   revalidate at invocation. Test: traversal, symbolic link escape, data
   exfiltration, and fork bomb fixtures are refused under each declared
   backend, and a mismatch between declared and observed backend fails
   conformance.

## Best practices, each with a test

### Harness and context

1. Keep project knowledge in versioned repository documents behind a short
   instruction map. Test: a task that depends on a rule stored only outside
   the repository fails until the rule moves in. (OpenAI)
2. Enforce architecture mechanically, with failure messages written as
   repair instructions. Test: attempts before a passing build fall. (OpenAI)
3. Assert on intermediate actions, not only final text. Test: a planted
   regression that final-text comparison misses is caught. (Google)
4. Load context by identifier, compact history, and move large outputs to
   files. Test: the same verified outcomes with fewer input tokens.
   (Anthropic; LangChain)
5. Keep a stable prefix, append-only context, deterministic serialization,
   and visible errors. Test: more provider-reported cached tokens and fewer
   repeated mistakes. (Manus)
6. Design tools from held-out evaluation transcripts, with truncated
   responses and errors that say how to recover. Test: fewer tool errors per
   held-out task. (Anthropic)
7. Keep the evaluator and permissions outside any loop that edits the
   harness, and accept only changes that do not regress on tuning or
   held-out tasks. Test: the evolving process cannot write evaluator files.
   (Weng)
8. Locate the faulty component from traces before repairing it. Test:
   targeted repairs beat broad rewrites on the same failures. (HarnessFix)
9. Requalify results when the scaffold changes, and read logs as well as
   scores. Test: a fixed task panel rerun after an adapter change shows
   whether earlier results transfer. (METR; HAL)

### Durable execution

1. Keep orchestration deterministic and put every nondeterministic operation,
   including model calls, behind a recorded step. Test: replaying one history
   twice with a moved clock and no network gives the same commands and no new
   calls. (Temporal; Azure Durable Task; Hatchet)
2. Fail loudly when replayed code diverges. Test: reordering one step
   produces a typed divergence naming the first differing event. (Temporal;
   Azure; Mastra)
3. Give every external effect a scoped idempotency key, and refuse a reused
   key with different parameters. Test: the same key and body give one
   effect; a changed body is refused. (AWS Builders' Library; Step
   Functions; Trigger.dev)
4. Pin running instances to the definition version they started with, and
   remove an old path only when no instance uses it. Test: an old instance
   follows the old path after a new deployment. (Temporal; DBOS; Dapr)
5. Declare cancellation behavior for each spawned unit of work, and keep
   graceful cancellation separate from forced termination. Test: each policy
   produces its declared final state. (Temporal; Azure; Restate)
6. Write retries as ordered rules by error class, and keep retry separate
   from repair and replanning. Test: a fixed error sequence produces the
   declared waits and then the fallback route. (Step Functions)
7. Model compensation as idempotent steps that run only for committed
   effects. Test: after a failure at the third step, compensations for the
   first two run once each. (Sagas paper; Azure pattern; Camunda)
8. Bound loops and history growth explicitly. Test: an unbounded cycle is
   refused before execution. (Temporal; Step Functions; Agent Development
   Kit; CWL)

### Protocols and supply chain

1. Send an exact protocol version and refuse mismatches with a typed error.
   Test: an unknown version produces a refusal and no effect. (Model Context
   Protocol; Agent2Agent)
2. Treat self-described capabilities and tool annotations as untrusted hints.
   Test: a tool labeled read-only that writes still requires approval.
   (Model Context Protocol)
3. Validate structured tool results against the declared output schema.
   Test: a result missing a required field is a typed contract failure.
   (Model Context Protocol)
4. Bind each approval to the exact effect and consume it once. Test: one
   changed argument byte after approval causes refusal. (Model Context
   Protocol; RFC 9396; AP2)
5. Accept only tokens issued for the resource, never pass tokens through,
   and validate the issuer. Test: a token for another audience is refused.
   (Model Context Protocol; RFC 8707; RFC 9207)
6. Sign and attest skills and code before activation, and verify again when
   loading. Test: changing one byte after signing makes loading fail.
   (OpenSSF Model Signing; in-toto)
7. Keep publication in a registry separate from approval. Test: a new
   registry entry leaves activation state at candidate. (Model Context
   Protocol Registry)

### Ontology and provenance

1. Keep stable identifiers, deprecate instead of deleting, and name a
   replacement. Test: a released identifier that disappears without
   deprecation fails continuous integration. (OBO Foundry; ROBOT)
2. Attach a diff to every release of a vocabulary. Test: a release without a
   diff fails. (ROBOT diff)
3. Validate closed shapes at boundaries with SHACL rather than relying on
   OWL, which assumes an open world. Test: a record with an undeclared
   property fails a closed shape. (SHACL; OWL 2 Primer)
4. Record provenance and a digest for every derived artifact. Test: removing
   one generation link yields exactly one shape violation. (PROV-O; DCAT 3;
   FAIR)
5. Link plans to executions. Test: every step activity corresponds to a step
   of the plan named in its association. (P-Plan; Provenance Run Crate)
6. Keep language-model-extracted terms as candidates grounded in existing
   identifiers until independent review. Test: nothing becomes active without
   a review record. (SPIRES; SSSOM)

### Verification and oracles

1. Record how independent each verdict is, including model family. Test:
   compare false acceptance for same-family and cross-family reviewers on
   seeded wrong solutions. (self-preference and model similarity studies)
2. Recompute expected values before seeing the check's value. Test: seeded
   wrong expectations are detected more often with the blind step. (No Free
   Labels; JudgeBench)
3. Qualify every check against a reference solution and trivial outputs
   before use. Test: an empty-output agent scores zero. (Agentic Benchmark
   Checklist)
4. Never let a check revision kill fewer mutants than before. Test: a
   revision that drops a discriminating case is refused. (Just and colleagues;
   Meta ACH; mutation testing at Google)
5. Rerun failures in a fresh pinned environment before blaming code or
   checks. Test: a nondeterministic probe is classified as flaky. (iDFlakies;
   flaky test survey)
6. Make checks read-only to the producer and offer an explicit "impossible
   check" exit. Test: on a conflicting check, edit attempts are refused and
   recorded. (ImpossibleBench)
7. Keep tamper monitors out of any optimization reward. Test: monitor output
   is absent from reward inputs. (chain-of-thought monitoring study)
8. Let judges abstain and escalate, and swap answer order for pairwise
   judgments. Test: agreement on non-abstained items meets the declared
   target, and the flip rate under order swap is reported. (Trust or
   Escalate; position bias studies)
9. Detect ambiguity from disagreement among independent candidates before
   blaming the code. Test: an ambiguous task produces a clarification and an
   unambiguous control does not. (ClarifyGPT; TiCoder; CodeT)
10. Report consistency over repeated trials. Test: pass over k trials is
    reported next to single-attempt success. (tau-bench)

### Skills, tools, and memory

1. Admit a tool or skill only after tests its builder never saw. Test:
   builder-visible and hidden pass rates are recorded separately. (ToolMaker;
   SkillsBench)
2. Measure each skill with paired runs and keep negative results. Test: a
   skill that hurts one task family is kept ineligible for that family.
   (SkillsBench; SkillFlow)
3. Report harmful near-duplicate exposure beside retrieval recall. Test:
   seeded near-duplicate pairs with swapped preconditions. (Right Family,
   Wrong Skill)
4. Retrieve bounded bundles by dependency closure. Test: a prerequisite that
   shares no words with the query is included only by closure. (Graph-of-Skills;
   Tool Graph Retriever)
5. Invalidate facts instead of deleting them. Test: a query scoped to an
   earlier time returns the old fact. (Graphiti)
6. Keep raw trajectories beside distilled skills. Test: compare both on
   held-out tasks with the library frozen. (SkillEvolBench)
7. Screen imported skills before granting any effect. Test: seeded
   exfiltrating skills never gain authority. (Agent Skills in the Wild)

## Additions by area

These lists name the most useful additions found. Each was checked against a
primary source on September 14, 2026.

### Harness engineering, context, and harness search

- **Guidance:** Anthropic on effective context engineering, long-running
  harnesses, writing tools for agents, and dynamic workflows; Manus on
  context engineering; LangChain, "The Anatomy of an Agent Harness"; Lilian
  Weng, "Harness Engineering for Self-Improvement".
- **Studies of real harnesses:** a source-code study of eleven coding
  harnesses (arXiv 2609.00006) that found none uses a general agent framework
  or vector retrieval for code; SWE-agent's agent-computer interface; the
  mini-SWE-agent control arm.
- **Harnesses:** Aider, OpenCode, Codex CLI, Claude Code and the Claude Agent
  SDK, goose, Cline, and Pi. Pi deliberately has no built-in permission
  system, so isolation must come from outside it.
- **Search over agents and harnesses:** ADAS, AFlow, MaAS, Darwin Gödel
  Machine, AlphaEvolve, OpenEvolve, ShinkaEvolve, GEPA, DSPy optimizers,
  TextGrad, Trace, Meta-Harness, HARBOR, WHALE, HarnessOpt-Bench (the
  submitted candidate usually scores below the best validation score), and
  HarnessFix.
- **Sandboxes:** E2B (one Firecracker virtual machine per sandbox), Modal
  sandboxes (gVisor), gVisor, Firecracker, Kata Containers, microsandbox,
  nsjail, and Landlock. Daytona's public repository was frozen in June 2026.
- **Memory:** MemGPT and Letta, Mem0 (benchmark results disputed by Zep),
  Zep and Graphiti (validity intervals), and A-MEM.
- **Measurement:** the Berkeley Function Calling Leaderboard, tau-bench and
  pass over k, ToolMaze (recovery drops about 37% when a tool failure is
  hidden), XGrammar constrained decoding, METR time horizons (scaffold
  changes moved measured capability), Terminal-Bench 2.0 and Harbor, HAL
  (logs revealed shortcuts that scores hid), and DeepSWE.

### Runtimes, workflow engines, and durable execution

- **Durable execution:** Temporal, Restate, DBOS Transact, Inngest, Hatchet,
  Trigger.dev, AWS Step Functions, Azure Durable Functions and Durable Task
  SDKs, Cadence, and Dapr Workflow.
- **Data and machine learning orchestration:** Dagster, Prefect, Flyte,
  Kubeflow Pipelines, Metaflow, Apache Hamilton, Apache Burr, ZenML with
  Kitaru replay policies, and Apache Airflow human-in-the-loop operators.
- **Agent frameworks:** Mastra (time travel refuses a changed definition),
  Haystack 3.0, the Semantic Kernel Process Framework (experimental), AutoGen
  Core (maintenance mode), AG2 1.0, CAMEL, MetaGPT, Agno 3.0, smolagents,
  Strands Agents, BeeAI Framework, Letta, Dify, n8n, Flowise (archived),
  Langflow, Rivet, Julep 3 release candidate, and iii (formerly Motia).
- **Formal and semi-formal models:** statecharts, SCXML, and XState; BPMN
  2.0.2 with Camunda 8; Petri nets and workflow nets; the Open Workflow
  Specification; Common Workflow Language 1.3 loops; WDL 1.3; Nextflow typed
  workflows; and Snakemake checkpoints.
- **Dataflow:** Timely Dataflow, Differential Dataflow, and Apache Beam.
- **Program-like model languages:** DSPy, LMQL (inactive), Guidance, the
  SGLang frontend, and BAML.

### Specifications, protocols, identity, and supply chain

- **Messaging and interfaces:** the Agent Communication Protocol (merged into
  Agent2Agent), Agent Network Protocol, AG-UI, A2UI, MCP Apps, the Agent
  Client Protocol and its registry, the LangChain Agent Protocol, the Agent
  Payments Protocol, and agentgateway.
- **Discovery conventions:** AGENTS.md, llms.txt, NLWeb, and agents.json
  (apparently inactive).
- **Interface and workflow descriptions:** OpenAPI 3.2, Arazzo 1.1, AsyncAPI
  3.1, JSON Schema 2020-12, JSON-LD 1.1, the schema.org Action vocabulary, the
  Web of Things Thing Description, the Open Workflow Specification, and
  CloudEvents.
- **Identity and delegated authority:** Verifiable Credentials 2.0,
  Decentralized Identifiers 1.1, the OAuth 2.1 draft, RFC 8693 token exchange,
  RFC 9396 rich authorization requests, RFC 9728 protected resource metadata,
  IETF agent delegation drafts, the WIMSE and Web Bot Auth working groups,
  SPIFFE and SPIRE, and the NIST AI Agent Standards Initiative.
- **Supply chain and provenance:** in-toto attestations, SLSA 1.2, Sigstore
  (Cosign 3 and Rekor 2), OpenSSF Model Signing, SPDX 3.0 AI and Dataset
  profiles, CycloneDX 1.7, OCI artifacts with referrers, CNCF ModelPack,
  Model Cards, Data Cards, Croissant, and the SCITT architecture (RFC 9943).
- **Registries and governance:** the Model Context Protocol Registry
  (preview), the AGNTCY directory, the Agent Client Protocol registry, and
  the Agentic AI Foundation, which now hosts the Model Context Protocol,
  goose, AGENTS.md, agentgateway, and Agent2Agent.

### Ontology engineering and knowledge representation

- **Upper and mid-level ontologies:** Basic Formal Ontology 2020 (ISO/IEC
  21838-2), DOLCE (ISO/IEC 21838-3), gUFO, Common Core Ontologies 2.2, and the
  Information Artifact Ontology.
- **Vocabularies:** SKOS, DCAT 3, Dublin Core, schema.org, ODRL 2.2 for
  policies, OWL-Time, SOSA and SSN, and ORG.
- **Plan and run provenance:** P-Plan, OPMW, EP-Plan, Workflow Run RO-Crate
  0.6, RO-Crate 1.2 and 1.3, WorkflowHub, OpenLineage, PROV-AQ, and PROV-AGENT.
- **Experiment ontologies:** ML-Schema, MEX, OntoDM, EXPO, and Croissant.
- **Shapes and mappings:** ShEx and SSSOM.
- **Stores, engines, and reasoners:** Apache Jena, RDF4J 6.0 (RDF 1.2),
  Oxigraph, RDFLib, pySHACL, Owlready2, HermiT, ELK, Konclude, GraphDB,
  Stardog, Virtuoso, TerminusDB, TypeDB, Datomic, XTDB, Soufflé, Logica,
  DuckDB with DuckPGQ, LadybugDB (Kùzu was archived in October 2025), and
  Neo4j.
- **Tooling with language models:** OntoGPT and SPIRES, the Ontology Access
  Kit, the LLMs4OL challenge, and DeepOnto.
- **Release and review tooling:** ROBOT diff, OWL API, the OBO Dashboard, and
  the LinkML linter.
- **Lighter typed schemas:** JSON Schema for boundary validation, Protocol
  Buffers for wire contracts, Pydantic for in-process validation, CUE for
  configuration, Dhall for non-Turing-complete configuration, TypeSpec for
  interface design, and Smithy for service models. OWL is the better choice
  only when entailment itself is the product.

### Skill libraries, tool graphs, and graph memory

- **Skill and tool making:** Voyager, ExpeL, Synapse, Agent Workflow Memory,
  Agent Skill Induction, SkillWeaver, CREATOR, Large Language Models as Tool
  Makers, CRAFT, ToolMaker (tests unavailable during creation), Alita,
  test-time tool evolution, and production tool compilation.
- **Skill evaluation:** SkillsBench (curated skills raised pass rates from
  33.9% to 50.5%, 13 of 87 tasks got worse, and self-generated skills scored
  below no skills), SkillFlow, SkillEvolBench (raw trajectories often beat
  distilled skills), SkillsVote, Agent Skills in the Wild (26.1% of 31,132
  marketplace skills had a vulnerability), SkillGenBench, SkillJuror,
  MIND-Skill, and Group of Skills.
- **Tool retrieval:** ToolLLM and ToolBench, AnyTool, Gorilla, ToolNet,
  ToolRet, Tool Graph Retriever, RAG-MCP (selection accuracy rose from 13.62%
  to 43.13%), MCP-Zero, and Right Family, Wrong Skill (a harmful sibling
  lands in the top three 34.6% to 37.2% of the time).
- **Graph memory and retrieval:** Graphiti and Zep, Mem0, Cognee, HippoRAG 2,
  LightRAG, KAG on OpenSPG, LazyGraphRAG, StructRAG, a systematic comparison
  of retrieval and graph retrieval (vector retrieval wins on detailed
  single-hop questions, graphs on multi-hop and temporal ones), and
  GraphRAG-Bench.
- **Planning and grounding:** LLM+P, Plansformer, work on planning abilities
  and world models, LLM-Modulo, OG-RAG, OaK, CodexGraph, and RepoGraph.
- **Experience and failure memory:** Reflexion, Agent KB, ReasoningBank,
  Agentic Context Engineering (context collapse), a memory management study
  showing that stored errors spread, MAST (14 failure modes with high human
  agreement), and a failure taxonomy with root-cause feedback.

### Verification, evaluation, and oracle quality

- **Telemetry:** OpenTelemetry generative AI conventions (agent spans still
  at Development status), OpenLLMetry, Weave, Braintrust, LangSmith with
  agentevals, Helicone, AgentOps, Laminar, and MLflow Tracing.
- **Formal and runtime verification:** TLA+ with TLC and Apalache, trace
  validation against TLA+, Alloy 6, the P language with PObserve, nuXmv,
  SPIN, UPPAAL, Kani, Dafny, the VERINA and CLEVER Lean benchmarks, DejaVu
  and reelay monitors, shielding, AgentSpec, ShieldAgent, ProbGuard, and
  VeriPlan.
- **Guardrails and policy:** Invariant Guardrails, NeMo Guardrails,
  Guardrails AI, LlamaFirewall, Progent, CaMeL, Open Policy Agent, Cedar, and
  FIDES.
- **Evaluation harnesses:** Inspect, HELM, OpenAI Evals, promptfoo, DeepEval,
  and Ragas.
- **Benchmarks:** tau-bench and tau2-bench, SWE-bench Verified and Pro,
  Terminal-Bench, GAIA, OSWorld and OSWorld-Verified, WebArena, AppWorld,
  MLE-bench, PaperBench, RE-Bench, METR time horizons, BrowseComp, Humanity's
  Last Exam and its published critique, and ARC-AGI-2 and ARC-AGI-3.
- **Benchmark critiques:** the Agentic Benchmark Checklist (an empty-response
  agent scored 38% on one task set), SWE-Bench+, UTBoost, PatchDiff, and "The
  SWE-Bench Illusion".
- **Judges and verifiers:** the MT-Bench judge study, position bias, CALM,
  JudgeBench, self-preference, model similarity bias, Agent-as-a-Judge,
  process supervision, ProcessBench, generative verifiers, limits of
  self-correction and self-verification, Trust or Escalate, No Free Labels,
  and variation in verification.
- **Test oracle quality:** mutmut, Cosmic Ray, PIT, StrykerJS, Hypothesis,
  Daikon, the test oracle problem survey, metamorphic testing, MR-Scout,
  mutants and real faults (73% of 357 real faults coupled to mutants),
  mutation testing at Google, Meta ACH, MuTAP, LLMorpheus, equivalent mutant
  detection, property-based test generation, nl2postcond, SpecGen, the flaky
  test survey, iDFlakies, FlakyFix, the risk that model oracles mirror the
  implementation, neural oracle false positives, TOGLL, actual or expected
  behavior (model assertion accuracy fell on buggy code), TaRGET, UTFix, test
  smells in generated tests, TestGenEval, SWT-Bench, TDD-Bench Verified and
  Otter, CodeT, HardTests, SAGA, ClarifyGPT, TiCoder, SpecRover,
  ImpossibleBench, METR's reward hacking report, chain-of-thought monitoring,
  and emergent misalignment from reward hacking.
- **Gap found:** no benchmark or tool was found whose main purpose is to
  decide whether an agent-written check or the code is wrong. That gap is
  the one the failed-check review waterfall addresses.

## Selected sources

- OpenAI harness engineering: <https://openai.com/index/harness-engineering/>
- Google harness evaluation: <https://developers.googleblog.com/the-anatomy-of-harness-engineering-how-to-evaluate-iterate-and-guard-ai-coding-agents/>
- Agentic Harness Engineering: <https://arxiv.org/abs/2604.25850>
- OpenHands Software Agent SDK: <https://arxiv.org/abs/2511.03690>
- Meta-Harness: <https://arxiv.org/abs/2603.28052>
- HarnessOpt-Bench: <https://arxiv.org/abs/2608.06301>
- LangGraph: <https://github.com/langchain-ai/langgraph>
- Microsoft Agent Framework: <https://github.com/microsoft/agent-framework>
- Temporal workflow determinism: <https://docs.temporal.io/workflow-definition>
- Open Agent Specification: <https://oracle.github.io/agent-spec/>
- Agent2Agent specification: <https://a2a-protocol.org/latest/specification/>
- Model Context Protocol 2026-07-28: <https://modelcontextprotocol.io/specification/2026-07-28>
- Agent Skills specification: <https://agentskills.io/specification>
- PROV-O: <https://www.w3.org/TR/prov-o/>
- SHACL: <https://www.w3.org/TR/shacl/>
- P-Plan: <https://vocab.linkeddata.es/p-plan/>
- Workflow Run RO-Crate: <https://www.researchobject.org/workflow-run-crate/>
- LinkML: <https://linkml.io/>
- AGENT-O: <https://arxiv.org/abs/2608.28345>
- Ontology-to-tools compilation: <https://arxiv.org/abs/2602.03439>
- SkillsBench: <https://arxiv.org/abs/2602.12670>
- Right Family, Wrong Skill: <https://arxiv.org/abs/2606.10388>
- Agentproof: <https://arxiv.org/abs/2603.20356>
- ImpossibleBench: <https://arxiv.org/abs/2510.20270>
- Actual or expected behaviour: <https://arxiv.org/abs/2410.21136>
- Meta ACH mutation-guided test generation: <https://arxiv.org/abs/2501.12862>
- Agentic Benchmark Checklist: <https://arxiv.org/abs/2507.02825>
- Trust or Escalate: <https://arxiv.org/abs/2407.18370>

## Limits

- Web search allowances ran out in several passes, so later checks relied on
  direct page fetches, and some recent work may be missing.
- A few primary pages refused automated fetches, including OpenAI's harness
  engineering post, and those rows rely on consistent secondary copies.
- Version numbers and dates were read on September 14, 2026 and will age.
- Reported results come from each source's own evaluation unless a row says
  otherwise. Several were vendor or author evaluations, and some are
  disputed.
- Line-level observations of Loop Engine came from a read-only map of the
  working tree at the time of the review; nothing was run for this record.
- Related records: the
  [September 14 review](../verification/CLAUDE-OPUS-5-REVIEW-2026-09-14.md),
  the [intake research](SELF-RESOLVING-INTAKE-SANDBOXES-AND-SHARING-2026-09-14.md),
  the [proposed invariants](../architecture/CONSTITUTION.md#proposed-invariants-from-owner-direction),
  and the
  [configuration dimensions](../architecture/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md).
