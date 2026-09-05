# Model architectures, contract composition, and a distributed Loop mesh

Research date: 2026-09-04, America/New_York. This is a bounded primary-source
review, not a claim to cover every proposed architecture. Published model
results below are author-reported and were not reproduced here. Repository
adaptations are proposals unless an implementation report establishes them.

Loop Engine can organize different forms of computation without choosing one
neural architecture as its foundation. The next practical test is whether the
existing solver can complete newly generated, hidden-label tasks through its
real model, execution, and verification boundaries. Connecting devices or
adding more models does not establish general intelligence.

## Keep the architectural levels separate

```text
Operational runtime type
└── Loop
    ├── Operational relationship
    │   ├── Starting
    │   ├── Spawned by
    │   ├── Queried by
    │   ├── Retrieved by
    │   └── Connected from
    ├── Role: Practitioner, Intelligence, or Solution
    ├── Versioned role profile
    ├── Purpose and domain categories
    ├── Mode: deterministic, hybrid, or non-deterministic
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition and exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when permitted
    └── Run History records
```

The four persistent intelligence layers remain Context Intelligence, Code
Intelligence, Runtime History and Solution Intelligence, and User Feedback
Intelligence. Runtime Memory is temporary. A model, embedding, skill file,
cache, transport, or container is not another intelligence layer or runtime.

```text
Independent implementation choices
├── Neural structure: attention, recurrence, state space, expert routing
├── Training objective: autoregressive, masked, diffusion, flow, reward
├── Inference and serving: search, sampling, KV storage, batching, precision
├── Loop program: responsibilities, contracts, graph, verification, effects
└── Deployment: local process, isolated worker, gateway, remote service
```

These axes can be combined. A diffusion language model can use a Transformer.
A hybrid attention/state-space model does not imply the repository's hybrid
Loop mode. A mixture-of-experts layer is not a team of independently governed
agents. An external recurrent Loop does not imply recurrent neural weights.

## Model families and the relevant tradeoffs

| Family or technique | What it changes | Useful role here | Main question before adoption |
|---|---|---|---|
| Encoder-decoder Transformer, BERT encoder, GPT-style causal decoder | Attention connectivity and training objective | Translation, representation, generation, or a semantic interpreter | Does the actual checkpoint support this contract and modality? Parallel training is not parallel autoregressive decoding. |
| Sparse mixture of experts | Activated feed-forward parameters per token | A provider realization | Are memory, routing, communication, and load imbalance included in cost? |
| FlashAttention and PagedAttention | Exact attention IO and serving-time KV allocation | Provider/runtime optimization | Is the gain prefill, decode, throughput, or latency under the actual concurrency? |
| Mamba and attention/state-space hybrids | Recurrent compressed state and selective access to sequence history | Long-stream or local model candidate | Which rare facts, ordering dependencies, and exact retrieval tasks are lost? |
| DDPM, flow matching, masked diffusion language models | Training and iterative generation procedure | Media generation or an alternative language interpreter | Does fewer sequential generation steps reduce measured cost at matched verified quality? |
| Learned world models with planning | Predictive latent dynamics and simulated search | Candidate experiment or plan generation | Can a wrong internal model produce a confidently unsafe plan? |
| Neural-symbolic systems | Learned proposals combined with exact domain reasoning | Bounded code, query, or proof responsibility | Is the formalization correct, and does the task fit the supported formal domain? |

The original Transformer, BERT, and GPT-3 papers describe different objectives
and connectivity. They do not support treating all LLM endpoints as equivalent
interpreters. In-context examples also do not constitute weight updates.
[Vaswani et al.](https://arxiv.org/html/1706.03762v7),
[Devlin et al.](https://arxiv.org/html/1810.04805v2),
[Brown et al.](https://arxiv.org/html/2005.14165v4).

Mixtral activates two of eight feed-forward experts per token while retaining
the larger parameter set. FlashAttention reduces attention memory traffic;
PagedAttention manages KV storage for serving. None proves a cheaper whole
Loop after retries, context construction, verification, and queueing.
[Mixtral](https://arxiv.org/html/2401.04088v1),
[FlashAttention](https://arxiv.org/html/2205.14135v2),
[PagedAttention](https://arxiv.org/html/2309.06180v1).

Mamba and Jamba warrant tests on state sufficiency, not just long input length.
Reported throughput depends on hardware, batch, precision, and workload.
Cross-run memory must remain explicit even if the chosen model has a recurrent
state. [Mamba](https://arxiv.org/html/2312.00752v2),
[Jamba](https://arxiv.org/html/2403.19887v2).

DDPM uses iterative denoising. Flow matching trains a vector field without
simulating its entire sampling trajectory during training; generation still
requires solving the resulting dynamics. LLaDA uses a masked diffusion
objective with a non-causal Transformer. Its language benchmark results do not
establish tool use or Loop integration.
[DDPM](https://arxiv.org/html/2006.11239v2),
[Flow Matching](https://arxiv.org/html/2210.02747v2),
[LLaDA](https://arxiv.org/html/2502.09992v3).

DreamerV3 reports broad task performance with shared hyperparameters, not one
trained agent that solves every task. MuZero combines learned latent dynamics
with search under specific environments and resources. AlphaGeometry combines
learned proposals with a symbolic engine in a restricted geometry domain.
Their useful common pattern is to test proposals against an appropriate
environment or verifier. A simulated observation must never become an actual
observation merely because planning used it.
[DreamerV3](https://www.nature.com/articles/s41586-025-08744-2),
[MuZero](https://arxiv.org/html/1911.08265v2),
[AlphaGeometry](https://www.nature.com/articles/s41586-023-06747-5).

## An LLM can organize code without seeing every implementation

LLMCompiler builds executable dependency plans from tool descriptions and
argument contracts. Synquid and TYGAR show how stronger types and restricted
synthesis can constrain composition. TYGAR's distinction between well-typed
and useful results is important: connecting compatible ports is not enough.
[LLMCompiler](https://arxiv.org/html/2312.04511v3),
[Synquid](https://cseweb.ucsd.edu/~npolikarpova/publications/pldi16.pdf),
[TYGAR](https://arxiv.org/pdf/1911.04091).

The planner should receive a small capability card: immutable identity,
version, purpose, typed ports, units and shapes, preconditions, postconditions,
effects, dependency/environment requirements, failure behavior, cost state,
and qualification. Summaries are hints; executable authority comes from the
exact registered asset. The planner may request source when a summary is
insufficient. Source hiding is an optimization, not a security proof.

Current mappings are `semantic_runtime_records`,
`reusable_capability_resolution`, and `solution_graph_validation`.
The resolver reloads authoritative capability details after retrieval.
Graph validation checks typed connections, but does not prove arbitrary
precondition implication, semantic equivalence, or effect noninterference.

PAL and Program of Thoughts delegate calculation to executable programs.
They leave problem interpretation and program correctness unresolved.
Recent answer-set-program distillation offers a useful narrow case, but its
symbolic inputs and restricted solver must not be mistaken for raw perception
or open-domain reasoning.
[PAL](https://proceedings.mlr.press/v202/gao23f.html),
[Program of Thoughts](https://arxiv.org/html/2211.12588v3),
[ASP distillation study](https://arxiv.org/html/2607.28086v1).

The proposed experiment compares full-source, contract-card, and progressively
hydrated planning on the same frozen component library. Include functions with
identical ordinary types but different behavior: sort, reverse, deduplicate;
degrees versus radians; pure reads versus state-changing reads. Reject a
composition if effects conflict, evidence is stale, or a postcondition is
missing. Measure compilation cost, execution success, false acceptance, and
source bytes exposed. Parallelize only when dependencies and effects permit.

## Response programs should optimize downstream loss

PICARD demonstrates constrained parsing for SQL. JSONSchemaBench distinguishes
claimed support from actual schema coverage. Grammar-aligned decoding examines
how token constraints can alter the intended conditional distribution. Format
validity and task correctness need separate measurements.
[PICARD](https://aclanthology.org/2021.emnlp-main.779.pdf),
[JSONSchemaBench](https://arxiv.org/html/2501.10868v3),
[Grammar-Aligned Decoding](https://arxiv.org/html/2405.21047v4).

Format restrictions can help one task and harm another. AdaCoder and LLMLingua
reduce supplied text in specific settings, but their compression and routing
costs, structural losses, and task assumptions matter here.
[Let Me Speak Freely](https://arxiv.org/html/2408.02442v3),
[AdaCoder](https://arxiv.org/html/2407.19410v1),
[LLMLingua](https://aclanthology.org/2023.emnlp-main.825.pdf).

Preserve a stable protocol and authority envelope. Allow task-specific fields,
extensions, contract proposals, and abstention inside it. The response should
retain its natural result beside any lossy consumer projection. Current
`template_negotiation` has these records, but its `usable` property alone does
not establish that all consumer requirements are satisfied or that a live
solver benefited from negotiation.

"99.99% of the information" needs an operational definition. Use missing
critical facts, downstream decision loss, false acceptance, and recovery cost.
It cannot be inferred from text similarity or schema validity. With zero
failures, a fixed IID Bernoulli experiment needs at least 29,956 trials for a
one-sided 95% upper bound at 0.0001. That calculation does not cover correlated
cases, adaptive template tuning, or unknown task distributions.

Compare minimal, fixed, and negotiated response programs on source-family
holdouts. Count formatting repairs and valid answers excluded by the schema.
Distill only after the smaller realization preserves the required outcomes,
including abstention and exceptions. A rigid output format is not itself a
proof that a smaller model will suffice.

## Information and computation have different units

The [earlier information review](LEARNING-FROM-VERIFIED-LOOP-OUTCOMES-2026-09-04.md)
defines proper predictive scores, information gain, and value of computation.
The distinctions also apply to distributed communication and response design.
Entropy reduction can accompany a wrong belief. A useful summary must preserve
information about a declared future decision, not every imaginable question.

A proposed allocation objective is to minimize total expected cost subject to
bounded task loss, false acceptance, latency, privacy, and effects. Cost must
include selection, retrieval, training, generation, failed attempts,
verification, coordination, and maintenance. Bits, dollars, elapsed time, and
task utility cannot be added without explicit conversion assumptions.

For repeated work, estimate a break-even count from measured construction cost
and per-use savings. Then test distribution drift and qualification cost.
N-grams, embeddings, classifiers, and cached procedures can supply candidates;
similarity alone cannot establish applicability. A strong-first strategy may
cost less overall when a weak early interpretation creates expensive rework.
These remain conditional hypotheses, not new deterministic routing rules.

## Distributed devices need more than registration

Deployment examples are test populations, not runtime branches. The core must
not select a smart-home, traffic, Kaggle, or industry workflow from a task name.
A user supplies the objective, available environment, deployment constraints,
and authority. A Practitioner interprets those inputs, queries intelligence,
proposes a graph, and verifies the selected realization against the actual
environment. Missing information or unsupported deployment remains an explicit
question or blocker.

Domain facts, standards guidance, examples, and procedures belong in Context
Intelligence. Reviewed protocol implementations, transformations, models, and
tools belong in Code Intelligence. Past results belong in Runtime History and
Solution Intelligence; user preferences and corrections belong in User
Feedback Intelligence. They keep provenance, scope, contracts, and lifecycle.
Source formats and industry names do not create additional layers.

An installed protocol adapter may implement protocol-specific mechanics. It
must not hide domain planning, tool selection, or authority behind a label.
Task-specific Loop definitions may be proposed as run-scoped graph data. They
are not developer-authored runtime classes or permanently installed industry
pipelines. A later reusable definition requires independent qualification.

The proposed problem, environment, deployment, and intelligence-pack manifests
must first be reconciled with existing authorities:

| Proposed responsibility | Existing boundary to extend | Still missing or unproven |
|---|---|---|
| Preserve and interpret a problem | `TaskIntake`, `CompiledTask`, `WorkItemIR`, `SemanticLoopContract` | One complete open-environment manifest and packless deployment proof |
| Discover environment and authority | `LoopRuntimeContext`, `OperatingProfile`, `ExtensionSnapshot`, capability catalog | General remote-endpoint discovery and reconciliation |
| Describe a reusable implementation | `CodeAssetSpec`, semantic realization and capability records | Qualified contract-only composition across unseen requirements |
| Choose deployment | `WorkspaceSpec`, backend declarations, logical graph definitions | One graph proven across Python, OCI and Wasm with explicit semantic differences |
| Package domain intelligence | Existing four intelligence layers, catalog and admission | Exact pack composition/qualification without another registry |

These names are a mapping, not proof that the new manifest examples are
implemented. Do not add parallel universal-manifest classes simply to match
a prompt's vocabulary. Source and task meaning are available to LLM reasoning;
the prohibition is a developer-authored domain switch that takes over that
reasoning.

The anti-specialization test population should include absent, wrong, and
obfuscated domain hints; equal labels with different effects; incompatible
packs; and a held-out user-defined environment. Renaming tests require a
consistent mapping of all relevant terms, contracts, and constraints.
Compare semantic obligations and permitted effects, not byte-identical graph
digests or one exact stochastic plan. Record core changes separately from
new manifests, intelligence resources, adapters, and tests. Zero core changes
for new scenarios is a target, not an established property of this checkout.

```text
Proposed deployment responsibilities, not additional runtime classes
├── Device or gateway
│   ├── Typed observations and approved local control
│   └── Local safety limits, freshness, and disconnected behavior
├── Loop worker
│   ├── Exact definitions, bounded execution, and Run History
│   └── Authenticated communication and effect-specific authority
└── Planning and improvement service
    ├── Candidate diagnosis, code, graphs, and model allocation
    └── Independent qualification, canary, versioning, and rollback
```

A small sensor need not run Python, a container, or an LLM. It can expose a
typed endpoint through a gateway. Do not call that endpoint a full Loop runtime
unless it actually implements the required contracts and evidence.

W3C Thing Descriptions describe properties, actions, events, data schemas, and
security mechanisms. They explicitly do not grant access authority. WIT worlds
describe component imports and exports, not arbitrary behavioral correctness.
Both can inform adapters without becoming new core authorities.
[WoT TD 1.1](https://www.w3.org/TR/wot-thing-description11/),
[WIT worlds](https://component-model.bytecodealliance.org/design/worlds.html).

SPIFFE supplies workload identities within trust domains, assuming adequate
workload isolation. Identity must be followed by effect authorization. MQTT
offers delivery guarantees, and CloudEvents defines interoperable event
metadata. Inference for this design: a messaging acknowledgment does not prove
that a physical action happened exactly once or succeeded.
[SPIFFE](https://spiffe.io/docs/latest/spiffe-about/spiffe-concepts/),
[MQTT 5](https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html),
[CloudEvents 1.0.2](https://github.com/cloudevents/spec/blob/v1.0.2/cloudevents/spec.md).

An effect request needs identity, schema/version, state revision, units,
freshness/deadline, namespace, authorization, idempotency key, and an observable
outcome. Independent retries must not duplicate actuation. A partition requires
an explicit local policy, not an assumption that global state remains current.

Containers require restricted privileges, mounts, resources, and network
policy. They do not provide hard real-time guarantees or complete isolation by
their mere presence. The repository already has Docker workspaces and local
leased reactive workers; that does not prove a secure decentralized device
mesh. [Kubernetes security checklist](https://kubernetes.io/docs/concepts/security/security-checklist/).

Keep traffic control and safety-critical actuation in qualified local control
systems. LLM-generated repairs remain candidates tested in simulation and
independently approved. No vehicle or home-device effect was authorized or
performed in this session.

## Adversarial research agenda

### Triads are optional computation strategies

Self-consistency and early multi-agent debate studies report gains on selected
reasoning tasks, but their main comparisons do not generally match total
inference cost. Later debate experiments show correct answers becoming wrong
after peer exchange. A recent budget-controlled multi-hop study favors simpler
systems in many settings, with limits in actual token matching, task scope,
and judging. None establishes a universal best panel size.
[Self-consistency](https://arxiv.org/html/2203.11171v4),
[Multiagent debate](https://arxiv.org/html/2305.14325v1),
[Debate failure modes](https://arxiv.org/html/2509.05396v2),
[Budget-controlled multi-hop study](https://arxiv.org/html/2604.02460v2).

Three peers voting, a proposer/critic/verifier arrangement, and replicated
state-machine consensus are different mechanisms. Raft coordinates an ordered
log for deterministic replicas under a specified failure model. It does not
make a model's agreed answer true. [Raft](https://raft.github.io/raft.pdf).

For three independent equal-accuracy binary voters, majority accuracy is
`3p^2 - 2p^3`; it exceeds individual accuracy only for `0.5 < p < 1`.
Perfectly correlated errors remove that gain. This is a conditional mathematical
example, not a measured LLM guarantee. Separate requests or provider names do
not establish independent errors.

Test monadic, fused-role, independent-sample, and functional-triad strategies
under the same total resource envelope. Preserve initial candidates and useful
dissent. Measure joint wrong answers, harmful revisions, verification results,
abstention, and complete cost. Do not store private reasoning. Majority may
propose a candidate; it cannot authorize an effect or promote a capability.
No triadic runtime or mandatory three-call default is installed by this note.

### Questions for executable experiments

1. Can a rare exact identifier survive recurrent state or aggressive context compression?
2. Does a summary omit a negation, unit, side effect, or data-licensing condition?
3. Can two individually valid components produce an invalid composition?
4. Does parallel scheduling duplicate effects or read stale state?
5. Does schema enforcement exclude a correct novel answer?
6. Can a schema-valid response omit evidence the consumer needs?
7. Does a teacher-derived shortcut fail on a new source, schema, or exception?
8. Does a cheap route still save money after escalation and verification?
9. Are expert or multi-agent errors correlated?
10. Can a learned world model exploit an inaccurate evaluator?
11. Can a poisoned capability summary gain execution authority?
12. Does reconnect/replay repeat a committed physical effect?
13. Can old observations survive expiry, clock skew, or unit conversion incorrectly?
14. Can revoked credentials or an old graph version continue to act?
15. Can one worker's workspace, prompt history, or cache contaminate another?
16. Does a container timeout leave unowned computation running?
17. Can an improvement proposer select its own favorable evaluator?
18. Are failed and excluded attempts included in reported cost and denominators?

The [source matrix](MODEL-ARCHITECTURES-COMPOSITION-SOURCE-MATRIX-2026-09-04.json)
records study assumptions, repository mappings, experiments, and falsifiers.
The [coverage index](ARCHITECTURE-COVERAGE-MATRIX-2026-09-04.json) distinguishes
selected-source review from unreviewed families. Its domain labels organize
research; they cannot select runtime behavior.
The research does not qualify a model route, device adapter, template, or
shortcut. New-task execution evidence belongs in a separate verification
report and campaign ledger.
