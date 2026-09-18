# Competitive landscape and monetization: memory, learning, and optimization layers for agents

Date: 2026-09-18, extended the same day with the feature matrix and again after commits fcca293 and 67d5d8f changed the Loop Engine row. Requested by
the owner after the SenseLab reading: compare the companies and projects adjacent to Loop Engine, contrast them with Loop
Engine's boundaries, and learn from how they charge. Every price, quota, and
claim below was read from the vendor's own public page or its public
repository on this date and is quoted as the vendor states it. Nothing was
purchased or benchmarked. Two companies from the owner's notes, Overmind and
Lemma, could not be reached at any resolvable domain today and are listed
as unverified.

## The landscape in one tree

```text
Layers adjacent to Loop Engine
├── Memory and context for agents
│   ├── Mem0, Zep and Graphiti, Supermemory, Cognee, Honcho, MemOS, Hindsight
│   └── SenseLab (memory plus outcome-linked confidence and training export)
├── Harness and prompt optimization, research workbenches
│   ├── Synth (local workshop plus managed research)
│   ├── Tellurio and Afnio (auto-tuned harnesses, hosted experiment tracking)
│   └── Overmind and Lemma (described in the owner's notes; unverified today)
├── Evaluation, simulation, and tracing
│   └── LangWatch
├── Right-sized computation
│   ├── Not Diamond (model routing)
│   ├── TypeSafe Jev (typed decisions, text only)
│   ├── PrismML Bonsai (compressed open-weight models)
│   └── Osmosis and Adaptive ML (post-training of specialized models)
├── Services-led enterprise deployment
│   └── Distyl
└── Precedents
    ├── Adaptive ML acquired by Datadog (announced June 2026)
    └── TensorZero archived on GitHub (2026-06-11)
```

Loop Engine sits across these layers rather than inside one: it owns the
run, the four intelligence layers, code and tool reuse as qualified
executable capability, independent verification, the model ontology, and
the records that say which implementation of an operation was cheapest.
None of the companies below owns all of that; several own one layer far more
deeply than Loop Engine does today.

## Feature matrix

The owner asked for binary cells rather than sentences, and for the claim
that most of these vendors have memory but not code reuse to be verified.
Each cell is Y (documented), N (not documented or documented as absent),
P (partial, see the cell notes), or ? (unverified today). Every non-obvious
cell names the page or fact it rests on. Letta was added to the chart.

The matrix is six tables, one per band, with seventy-six columns; the bands and the columns added after the first reading were introduced later on 2026-09-18, and a vendor cell in an added column is marked unverified unless an earlier note supported it.

The matrix is six tables, one per band, with seventy-six columns. The intelligence layers band and the columns added after the first reading were introduced later on 2026-09-18, and twenty more columns on the same day after the owner asked for more fields; a vendor cell in an added column is marked unverified unless an earlier note supported it, and the generator refuses a Loop Engine cell without an evidence note. Each table is followed by vendor counts.

### Intelligence layers

| Company | Context Intelligence served as records | Temporal validity on facts | Seeded generation by role or domain | Code Intelligence with contracts | Candidate to qualified admission | Runtime History with cost and verification | Training data from records | User Feedback applied at run time | Search returns typed references before bodies | Reuse evidence with credit split and regime shift | Suggested output shapes on model calls |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| Loop Engine (this repository) | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y |
| Mem0 | Y | ? | ? | N | ? | ? | P | Y | ? | ? | ? |
| Zep and Graphiti | Y | Y | ? | N | ? | ? | ? | ? | ? | ? | ? |
| Supermemory | Y | Y | ? | N | ? | ? | ? | Y | ? | ? | ? |
| Cognee | Y | P | ? | N | ? | ? | ? | ? | ? | ? | ? |
| Honcho (Plastic Labs) | Y | ? | ? | N | ? | ? | ? | ? | ? | ? | ? |
| MemOS (MemTensor) | Y | ? | ? | N | ? | P | ? | P | ? | ? | ? |
| Hindsight (Vectorize) | Y | ? | ? | N | ? | ? | ? | ? | ? | ? | ? |
| SenseLab (AMFS) | Y | ? | ? | N | ? | Y | Y | ? | ? | ? | ? |
| Letta | Y | N | ? | P | ? | ? | ? | ? | ? | ? | ? |
| Synth | P | ? | ? | P | ? | Y | Y | ? | ? | ? | ? |
| Tellurio and Afnio | ? | ? | ? | N | ? | ? | ? | ? | ? | ? | ? |
| LangWatch | ? | ? | ? | N | ? | Y | Y | ? | ? | ? | ? |
| Not Diamond | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| TypeSafe (Jev) | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| PrismML (Bonsai) | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| Osmosis (Gulp AI) | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| Adaptive ML (acquired by Datadog) | ? | ? | ? | ? | ? | ? | ? | P | ? | ? | ? |
| Distyl | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| TensorZero (archived) | N | ? | ? | N | ? | Y | ? | ? | ? | ? | ? |
| Overmind, Lemma | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? |

Vendor counts for intelligence layers (Loop Engine and the unverified pair excluded):

| Feature | Y | P | N | ? |
|---|:-:|:-:|:-:|:-:|
| Context Intelligence served as records | 9 | 1 | 1 | 8 |
| Temporal validity on facts | 2 | 1 | 1 | 15 |
| Seeded generation by role or domain | 0 | 0 | 0 | 19 |
| Code Intelligence with contracts | 0 | 2 | 11 | 6 |
| Candidate to qualified admission | 0 | 0 | 0 | 19 |
| Runtime History with cost and verification | 4 | 1 | 0 | 14 |
| Training data from records | 3 | 1 | 0 | 15 |
| User Feedback applied at run time | 2 | 2 | 0 | 15 |
| Search returns typed references before bodies | 0 | 0 | 0 | 19 |
| Reuse evidence with credit split and regime shift | 0 | 0 | 0 | 19 |
| Suggested output shapes on model calls | 0 | 0 | 0 | 19 |

### Memory

| Company | Persistent memory | Graph or temporal facts | Outcome changes retrieval | Memory versioning | Multi-agent shared memory | Working memory with eviction | Episodic memory | Semantic claims with contradictions | Procedural memory | One store contract, many adapters | Namespaces and tenancy | One task working folder | Runtime Memory scoped to one run |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| Loop Engine (this repository) | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | P | Y |
| Mem0 | Y | Y | N | N | Y | ? | ? | ? | Y | ? | ? | ? | ? |
| Zep and Graphiti | Y | Y | N | N | P | ? | ? | ? | ? | ? | P | ? | ? |
| Supermemory | Y | Y | P | N | P | ? | ? | ? | ? | ? | Y | ? | ? |
| Cognee | Y | Y | ? | N | P | ? | ? | ? | ? | ? | ? | ? | ? |
| Honcho (Plastic Labs) | Y | Y | N | N | Y | ? | ? | ? | ? | ? | ? | ? | ? |
| MemOS (MemTensor) | Y | Y | P | N | Y | ? | ? | ? | Y | ? | ? | ? | ? |
| Hindsight (Vectorize) | Y | Y | N | N | Y | ? | ? | ? | ? | ? | ? | ? | ? |
| SenseLab (AMFS) | Y | Y | Y | Y | Y | ? | ? | ? | ? | ? | ? | ? | ? |
| Letta | Y | N | N | Y | P | ? | ? | ? | ? | ? | ? | ? | ? |
| Synth | N | N | N | N | N | ? | ? | ? | ? | ? | ? | ? | ? |
| Tellurio and Afnio | N | N | N | N | N | ? | ? | ? | ? | ? | ? | ? | ? |
| LangWatch | N | N | N | N | N | ? | ? | ? | ? | ? | ? | ? | ? |
| Not Diamond | N | N | N | N | N | ? | ? | ? | ? | ? | ? | ? | ? |
| TypeSafe (Jev) | N | N | N | N | N | ? | ? | ? | ? | ? | ? | ? | ? |
| PrismML (Bonsai) | N | N | N | N | N | ? | ? | ? | ? | ? | ? | ? | ? |
| Osmosis (Gulp AI) | N | N | N | N | N | ? | ? | ? | ? | ? | ? | ? | ? |
| Adaptive ML (acquired by Datadog) | N | N | N | N | N | ? | ? | ? | ? | ? | ? | ? | ? |
| Distyl | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| TensorZero (archived) | N | N | N | N | N | ? | ? | ? | ? | ? | ? | ? | ? |
| Overmind, Lemma | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? |

Vendor counts for memory (Loop Engine and the unverified pair excluded):

| Feature | Y | P | N | ? |
|---|:-:|:-:|:-:|:-:|
| Persistent memory | 9 | 0 | 9 | 1 |
| Graph or temporal facts | 8 | 0 | 10 | 1 |
| Outcome changes retrieval | 1 | 2 | 14 | 2 |
| Memory versioning | 2 | 0 | 16 | 1 |
| Multi-agent shared memory | 5 | 4 | 9 | 1 |
| Working memory with eviction | 0 | 0 | 0 | 19 |
| Episodic memory | 0 | 0 | 0 | 19 |
| Semantic claims with contradictions | 0 | 0 | 0 | 19 |
| Procedural memory | 2 | 0 | 0 | 17 |
| One store contract, many adapters | 0 | 0 | 0 | 19 |
| Namespaces and tenancy | 1 | 1 | 0 | 17 |
| One task working folder | 0 | 0 | 0 | 19 |
| Runtime Memory scoped to one run | 0 | 0 | 0 | 19 |

### Procedures

| Company | Procedures as instructions | Executable code reuse | Executes code or tools | Sandbox with declared effects | Standalone solution export | Container and Job export | Model Context Protocol tools | Native harness adapters | Plugin and skill admission | Fast path before the first model call | Best-available resolution package | Question forms multiplied deterministically | Pre-packaged detection and correction families | Resource supervision of harness instances |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| Loop Engine (this repository) | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | P |
| Mem0 | Y | N | N | ? | N | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| Zep and Graphiti | N | N | N | ? | N | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| Supermemory | N | N | N | ? | N | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| Cognee | N | N | N | ? | N | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| Honcho (Plastic Labs) | N | N | N | ? | N | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| MemOS (MemTensor) | Y | N | P | ? | N | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| Hindsight (Vectorize) | N | N | N | ? | N | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| SenseLab (AMFS) | N | N | N | ? | N | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| Letta | Y | P | Y | Y | N | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| Synth | N | P | Y | Y | Y | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| Tellurio and Afnio | N | N | Y | ? | N | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| LangWatch | N | N | P | ? | N | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| Not Diamond | N | N | N | ? | N | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| TypeSafe (Jev) | N | N | N | ? | N | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| PrismML (Bonsai) | N | N | N | ? | N | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| Osmosis (Gulp AI) | N | N | N | ? | N | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| Adaptive ML (acquired by Datadog) | N | N | N | ? | N | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| Distyl | ? | ? | Y | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| TensorZero (archived) | N | N | N | ? | N | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| Overmind, Lemma | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? |

Vendor counts for procedures (Loop Engine and the unverified pair excluded):

| Feature | Y | P | N | ? |
|---|:-:|:-:|:-:|:-:|
| Procedures as instructions | 3 | 0 | 15 | 1 |
| Executable code reuse | 0 | 2 | 16 | 1 |
| Executes code or tools | 4 | 2 | 13 | 0 |
| Sandbox with declared effects | 2 | 0 | 0 | 17 |
| Standalone solution export | 1 | 0 | 17 | 1 |
| Container and Job export | 0 | 0 | 0 | 19 |
| Model Context Protocol tools | 0 | 0 | 0 | 19 |
| Native harness adapters | 0 | 0 | 0 | 19 |
| Plugin and skill admission | 0 | 0 | 0 | 19 |
| Fast path before the first model call | 0 | 0 | 0 | 19 |
| Best-available resolution package | 0 | 0 | 0 | 19 |
| Question forms multiplied deterministically | 0 | 0 | 0 | 19 |
| Pre-packaged detection and correction families | 0 | 0 | 0 | 19 |
| Resource supervision of harness instances | 0 | 0 | 0 | 19 |

### Assurance

| Company | Independent verification | Failed-check review | Evaluation or simulation product | Registered deterministic graders | Per-implementation cost records | Adversarial checks and mutants in the repository | Conformance gates on every commit | Secret-free records by contract | Action vectors on every step | Budget-phase supervision | Contract matching modes declared | Verification on a different model route |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| Loop Engine (this repository) | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y |
| Mem0 | N | ? | P | ? | N | ? | ? | ? | ? | ? | ? | ? |
| Zep and Graphiti | N | ? | N | ? | N | ? | ? | ? | ? | ? | ? | ? |
| Supermemory | N | ? | N | ? | N | ? | ? | ? | ? | ? | ? | ? |
| Cognee | N | ? | N | ? | N | ? | ? | ? | ? | ? | ? | ? |
| Honcho (Plastic Labs) | N | ? | N | ? | N | ? | ? | ? | ? | ? | ? | ? |
| MemOS (MemTensor) | N | ? | N | ? | N | ? | ? | ? | ? | ? | ? | ? |
| Hindsight (Vectorize) | N | ? | N | ? | N | ? | ? | ? | ? | ? | ? | ? |
| SenseLab (AMFS) | N | ? | P | ? | N | ? | ? | ? | ? | ? | ? | ? |
| Letta | N | ? | N | ? | N | ? | ? | ? | ? | ? | ? | ? |
| Synth | Y | ? | Y | Y | N | ? | ? | ? | ? | ? | ? | ? |
| Tellurio and Afnio | N | ? | Y | ? | N | ? | ? | ? | ? | ? | ? | ? |
| LangWatch | P | ? | Y | Y | N | ? | ? | ? | ? | ? | ? | ? |
| Not Diamond | N | ? | N | ? | N | ? | ? | ? | ? | ? | ? | ? |
| TypeSafe (Jev) | N | ? | N | ? | N | ? | ? | ? | ? | ? | ? | ? |
| PrismML (Bonsai) | N | ? | N | ? | N | ? | ? | ? | ? | ? | ? | ? |
| Osmosis (Gulp AI) | N | ? | P | ? | N | ? | ? | ? | ? | ? | ? | ? |
| Adaptive ML (acquired by Datadog) | P | ? | Y | Y | N | ? | ? | ? | ? | ? | ? | ? |
| Distyl | P | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| TensorZero (archived) | N | ? | Y | ? | N | ? | ? | ? | ? | ? | ? | ? |
| Overmind, Lemma | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? |

Vendor counts for assurance (Loop Engine and the unverified pair excluded):

| Feature | Y | P | N | ? |
|---|:-:|:-:|:-:|:-:|
| Independent verification | 1 | 3 | 15 | 0 |
| Failed-check review | 0 | 0 | 0 | 19 |
| Evaluation or simulation product | 5 | 3 | 10 | 1 |
| Registered deterministic graders | 3 | 0 | 0 | 16 |
| Per-implementation cost records | 0 | 0 | 18 | 1 |
| Adversarial checks and mutants in the repository | 0 | 0 | 0 | 19 |
| Conformance gates on every commit | 0 | 0 | 0 | 19 |
| Secret-free records by contract | 0 | 0 | 0 | 19 |
| Action vectors on every step | 0 | 0 | 0 | 19 |
| Budget-phase supervision | 0 | 0 | 0 | 19 |
| Contract matching modes declared | 0 | 0 | 0 | 19 |
| Verification on a different model route | 0 | 0 | 0 | 19 |

### Selection

| Company | Model routing | Model versus non-model choice | Harness or prompt optimization | Exhaustive grid with honest coverage | Explorative or evolutionary search | Noise injection robustness | Train gain and holdout loss acceptance | Trains or exports specialists | Heuristic adoption policy | Typed-decision model route | Step efficiency review | Meta-selection of selectors | Model ontology with placement rule | Convergence report with honest stability |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| Loop Engine (this repository) | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | P | Y | Y |
| Mem0 | N | N | N | ? | ? | ? | ? | N | ? | ? | ? | ? | ? | ? |
| Zep and Graphiti | N | N | N | ? | ? | ? | ? | N | ? | ? | ? | ? | ? | ? |
| Supermemory | N | N | N | ? | ? | ? | ? | N | ? | ? | ? | ? | ? | ? |
| Cognee | N | N | N | ? | ? | ? | ? | N | ? | ? | ? | ? | ? | ? |
| Honcho (Plastic Labs) | N | N | N | ? | ? | ? | ? | N | ? | ? | ? | ? | ? | ? |
| MemOS (MemTensor) | N | N | N | ? | ? | ? | ? | N | ? | ? | ? | ? | ? | ? |
| Hindsight (Vectorize) | N | N | N | ? | ? | ? | ? | N | ? | ? | ? | ? | ? | ? |
| SenseLab (AMFS) | N | N | N | ? | ? | ? | ? | Y | ? | ? | ? | ? | ? | ? |
| Letta | N | N | P | ? | ? | ? | ? | N | ? | ? | ? | ? | ? | ? |
| Synth | N | N | Y | ? | Y | ? | ? | Y | ? | ? | ? | ? | ? | ? |
| Tellurio and Afnio | N | N | Y | ? | ? | ? | ? | N | ? | ? | ? | ? | ? | ? |
| LangWatch | N | N | Y | ? | P | ? | ? | Y | ? | ? | ? | ? | ? | ? |
| Not Diamond | Y | N | ? | ? | ? | ? | ? | N | ? | ? | ? | ? | ? | ? |
| TypeSafe (Jev) | N | N | N | ? | ? | ? | ? | N | ? | Y | ? | ? | ? | ? |
| PrismML (Bonsai) | N | N | N | ? | ? | ? | ? | N | ? | ? | ? | ? | ? | ? |
| Osmosis (Gulp AI) | N | N | N | ? | ? | ? | ? | Y | ? | ? | ? | ? | ? | ? |
| Adaptive ML (acquired by Datadog) | N | N | N | ? | ? | ? | ? | Y | ? | ? | ? | ? | ? | ? |
| Distyl | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| TensorZero (archived) | Y | N | Y | ? | ? | ? | ? | Y | ? | ? | ? | ? | ? | ? |
| Overmind, Lemma | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? |

Vendor counts for selection (Loop Engine and the unverified pair excluded):

| Feature | Y | P | N | ? |
|---|:-:|:-:|:-:|:-:|
| Model routing | 2 | 0 | 16 | 1 |
| Model versus non-model choice | 0 | 0 | 18 | 1 |
| Harness or prompt optimization | 4 | 1 | 12 | 2 |
| Exhaustive grid with honest coverage | 0 | 0 | 0 | 19 |
| Explorative or evolutionary search | 1 | 1 | 0 | 17 |
| Noise injection robustness | 0 | 0 | 0 | 19 |
| Train gain and holdout loss acceptance | 0 | 0 | 0 | 19 |
| Trains or exports specialists | 6 | 0 | 12 | 1 |
| Heuristic adoption policy | 0 | 0 | 0 | 19 |
| Typed-decision model route | 1 | 0 | 0 | 18 |
| Step efficiency review | 0 | 0 | 0 | 19 |
| Meta-selection of selectors | 0 | 0 | 0 | 19 |
| Model ontology with placement rule | 0 | 0 | 0 | 19 |
| Convergence report with honest stability | 0 | 0 | 0 | 19 |

### Business

| Company | Open source core | Self-hosted option | Hosted cloud | Public pricing | Metered units documented | Never-metered list | Tenant keys stored as digests | Container image published | Packaging tiers documented | Machine-readable roadmap | Verified competitor comparison | Base image pinned by digest |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| Loop Engine (this repository) | Y | Y | N | N | Y | Y | Y | Y | Y | Y | Y | Y |
| Mem0 | Y | Y | Y | Y | Y | ? | ? | ? | ? | ? | ? | ? |
| Zep and Graphiti | Y | Y | Y | Y | Y | ? | ? | ? | ? | ? | ? | ? |
| Supermemory | Y | Y | Y | Y | Y | ? | ? | ? | ? | ? | ? | ? |
| Cognee | Y | Y | Y | Y | Y | ? | ? | ? | ? | ? | ? | ? |
| Honcho (Plastic Labs) | Y | Y | Y | Y | Y | ? | ? | ? | ? | ? | ? | ? |
| MemOS (MemTensor) | Y | Y | Y | Y | Y | ? | ? | ? | ? | ? | ? | ? |
| Hindsight (Vectorize) | Y | Y | Y | Y | Y | ? | ? | ? | ? | ? | ? | ? |
| SenseLab (AMFS) | Y | Y | Y | Y | Y | Y | ? | ? | ? | ? | ? | ? |
| Letta | Y | Y | Y | Y | Y | ? | ? | ? | ? | ? | ? | ? |
| Synth | Y | Y | Y | P | ? | ? | ? | ? | ? | ? | ? | ? |
| Tellurio and Afnio | P | ? | Y | Y | Y | ? | ? | ? | ? | ? | ? | ? |
| LangWatch | Y | Y | Y | Y | Y | ? | ? | ? | ? | ? | ? | ? |
| Not Diamond | N | N | Y | Y | Y | ? | ? | ? | ? | ? | ? | ? |
| TypeSafe (Jev) | N | N | Y | Y | Y | ? | ? | ? | ? | ? | ? | ? |
| PrismML (Bonsai) | Y | Y | N | N | ? | ? | ? | ? | ? | ? | ? | ? |
| Osmosis (Gulp AI) | N | N | Y | N | ? | ? | ? | ? | ? | ? | ? | ? |
| Adaptive ML (acquired by Datadog) | N | N | Y | N | ? | ? | ? | ? | ? | ? | ? | ? |
| Distyl | N | ? | Y | N | ? | ? | ? | ? | ? | ? | ? | ? |
| TensorZero (archived) | Y | Y | N | N | ? | ? | ? | ? | ? | ? | ? | ? |
| Overmind, Lemma | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? |

Vendor counts for business (Loop Engine and the unverified pair excluded):

| Feature | Y | P | N | ? |
|---|:-:|:-:|:-:|:-:|
| Open source core | 13 | 1 | 5 | 0 |
| Self-hosted option | 13 | 0 | 4 | 2 |
| Hosted cloud | 17 | 0 | 2 | 0 |
| Public pricing | 13 | 1 | 5 | 0 |
| Metered units documented | 13 | 0 | 0 | 6 |
| Never-metered list | 1 | 0 | 0 | 18 |
| Tenant keys stored as digests | 0 | 0 | 0 | 19 |
| Container image published | 0 | 0 | 0 | 19 |
| Packaging tiers documented | 0 | 0 | 0 | 19 |
| Machine-readable roadmap | 0 | 0 | 0 | 19 |
| Verified competitor comparison | 0 | 0 | 0 | 19 |
| Base image pinned by digest | 0 | 0 | 0 | 19 |

### Column definitions

- Context Intelligence served as records: Facts, instructions, personas, and forms kept and served with an identity.
- Temporal validity on facts: A fact carries the interval over which it held, and queries respect it.
- Seeded generation by role or domain: Questions, facts, and code seeds generated from occupations or domains and staged as candidates.
- Code Intelligence with contracts: Executable capabilities kept with identity, typed contract, tests, and digest, invoked without a model.
- Candidate to qualified admission: New capabilities stay candidates until an independent process qualifies them.
- Runtime History with cost and verification: What ran, what it cost, and what was independently verified, kept for later runs.
- Training data from records: Datasets or exports derived from recorded runs, with splits and exclusions.
- User Feedback applied at run time: What people said or decided is kept and consulted by later runs.
- Persistent memory: Keeps facts or entries across sessions.
- Graph or temporal facts: Relationships between entries, or validity times on facts.
- Outcome changes retrieval: A task outcome changes what is retrieved or how much it is trusted.
- Memory versioning: Branch, merge, or roll back the memory itself.
- Multi-agent shared memory: Several agents read and write one governed store.
- Working memory with eviction: A bounded run-time store with capacity, pinning, and recorded eviction.
- Episodic memory: What happened in a run: goal, acceptance, failure classes.
- Semantic claims with contradictions: Claims with subject, predicate, object, confidence, and contradiction handling.
- Procedural memory: Reusable procedures kept with purpose and applicability.
- One store contract, many adapters: The same read and write contract over in-memory, file, embedded database, and server database backends.
- Namespaces and tenancy: Records separated by namespace or tenant with access rules.
- Procedures as instructions: Stores step-by-step procedures or skills that a model reads at run time.
- Executable code reuse: Stores code, tools, or resolvers that later run without a model interpreting them.
- Executes code or tools: Runs code or tools itself, in a workspace or sandbox.
- Sandbox with declared effects: Execution confined to a declared sandbox with effect approval, resource limits, and no raw-host fallback.
- Standalone solution export: Emits a runnable package that works without the platform.
- Container and Job export: The exported solution ships with a container recipe and a cluster job manifest.
- Model Context Protocol tools: External tools reached through the protocol as adapters with a handshake.
- Native harness adapters: Other coding harnesses run a step under the platform's authority.
- Plugin and skill admission: Plugins and skills are discovered, admitted, and versioned before use.
- Independent verification: A separate process checks the task outcome; the producer's report is not the verdict.
- Failed-check review: A failed check is classified and confirmed before the work or the check changes.
- Evaluation or simulation product: Evaluators, scenarios, or simulations offered as a feature.
- Registered deterministic graders: Named graders with exact denominators, an error never counted as a pass.
- Per-implementation cost records: Records what each implementation of an operation cost and which was cheapest.
- Adversarial checks and mutants in the repository: Each check is shown to fail when its behavior is removed.
- Conformance gates on every commit: Architecture, hardcoding, documentation, and self-test gates run on an exported tree.
- Secret-free records by contract: Learning, metering, and cost records carry digests and sizes, never bodies or keys.
- Model routing: Chooses among models per request.
- Model versus non-model choice: Decides whether a model call is needed at all, by cost and evidence.
- Harness or prompt optimization: Automatically tunes prompts, context, or harness settings.
- Exhaustive grid with honest coverage: A finite declared grid enumerated fully, with sampling never reported as exhaustive.
- Explorative or evolutionary search: Seeded sampling, evolutionary, or novelty strategies over a configuration space.
- Noise injection robustness: A candidate must hold its gain on a perturbed suite.
- Train gain and holdout loss acceptance: A candidate replaces the baseline only with a training gain and no held-out loss.
- Trains or exports specialists: Fine-tunes a model or exports training data from records.
- Heuristic adoption policy: A declared run count gates any learned heuristic beyond an exact atomic fingerprint.
- Typed-decision model route: A model that returns typed decisions with confidence serves behind the same call boundary.
- Open source core: The engine is published under an open license.
- Self-hosted option: Runs on the customer's machines.
- Hosted cloud: A hosted service is sold.
- Public pricing: Prices are published.
- Metered units documented: The units a customer pays for are named.
- Never-metered list: What a customer never pays for is named.
- Tenant keys stored as digests: Service keys are kept only as digests and checked before any work.
- Container image published: A built, digest-pinned image is published for deployment.
- Search returns typed references before bodies: Intelligence search returns small typed references; a body is loaded only after selection and permission checks.
- Reuse evidence with credit split and regime shift: A verified outcome updates a posterior for every cited record, credit is split across citations, and a regime shift is recorded as an event.
- Suggested output shapes on model calls: A call names the answer shape it wants, for example a ranked list with a confidence, and records deviation without raising.
- One task working folder: Supplied files, unpacked archives, downloads, and generated work live in one folder that persists across attempts.
- Runtime Memory scoped to one run: A temporary run-scoped memory kept separate from the four persistent layers.
- Fast path before the first model call: Registered exact resolvers run before any model call; a verified fast path finishes with zero model calls.
- Best-available resolution package: A task that cannot be verified still ends with analysis, labeled assumptions, provisional files, and next actions.
- Question forms multiplied deterministically: Stored ways of asking are multiplied by persona and policy into a combination space without a model.
- Action vectors on every step: Each selected action declares its intended direction and expected delta and is assessed on observable process, output, and continuation.
- Budget-phase supervision: Declared thresholds of remaining call authority demote exploration to consolidation and present the best result for verification.
- Contract matching modes declared: Every contract names how it is matched: exact, canonical text, purpose, semantic with blocking keys, or judged.
- Verification on a different model route: The independent verifier confirms on a route different from the producer's.
- Step efficiency review: A step asks whether its inputs or outputs are too big and ranks alternatives with a cheap judge.
- Meta-selection of selectors: Selector methods and their settings are configuration choices with initial and fallback priorities.
- Model ontology with placement rule: Every route and tool declares model kind, placement, size class, and provenance; a tool never loads a large model in process.
- Convergence report with honest stability: Seeded rounds report separate counts and claim stability only when the best cell repeats or the enumeration was exhaustive.
- Packaging tiers documented: Community, self-hosted, and hosted tiers with what each includes and what stays free.
- Machine-readable roadmap: A roadmap a loop can walk, with verification, adversarial check, evidence, and status per step.
- Verified competitor comparison: A dated comparison read from vendors' own pages with an evidence note per cell.
- Base image pinned by digest: The worker image pins its base image by digest and the built image digest is recorded.
- Pre-packaged detection and correction families: Typed detection and correction operations with a confidence per decision, catalogs, blocking keys, and an escalation band for review.
- Resource supervision of harness instances: The machine or cluster is measured, instances are admitted within a derived ceiling, stalled ones are cleared, memory-heavy ones are paused and resumed, and capacity is added within a budget.

### Cell notes

- Loop Engine (this repository): Context Intelligence served as records: catalog adapters, the string bank, packaged data files; served through intelligence_layers and retrieval; Temporal validity on facts: core/temporal_facts: validity intervals, supersession, as-of queries (commit 67d5d8f); Seeded generation by role or domain: core/seeded_generation: occupation tables read through a declared column mapping (O*NET and ESCO layouts as data), six packaged occupations generate 327 candidate questions, facts, and code seeds staged through the store contract; nothing leaves candidate state (batch 11); Code Intelligence with contracts: capability directory surfaces, reusable capability records, registered resolvers, the text conformance family; Candidate to qualified admission: the reusable capability flywheel: opportunity, assessment, candidate, generalization, admission; Runtime History with cost and verification: run history, operation cost records, independent verification reports, solutions space; Training data from records: learnable call records with a run-level split; dataset versions in the training data store (commit b1fbcdc); User Feedback applied at run time: the advice store, typed task feedback slots, approvals, reviewed candidates; Graph or temporal facts: core/temporal_facts: typed triples with validity intervals, supersession, as-of, neighbors, paths (commit 67d5d8f); Outcome changes retrieval: reuse evidence with a bounded ranking term in core/retrieval: a validated record overtakes one adjacent rank, a discredited record sinks last, nothing is removed (batch 10); Memory versioning: catalog/versioning: immutable revisions, history, diff, rollback in the same store (commit 67d5d8f); Multi-agent shared memory: core/shared_memory_scopes: signed writes, membership and visibility filtered reads, stale-write refusal (commit 67d5d8f); the hosted memory endpoints bind the writer to the authenticated tenant (batch 10); Working memory with eviction: memory/working: compartments, capacity, pinning, eviction and compaction history; Episodic memory: memory/episodic records with run identity, acceptance, and failure classes; Semantic claims with contradictions: memory/semantic and strings/knowledge_state: claims, unknowns, contradictions; Procedural memory: memory/procedural, question forms, ask strategies; One store contract, many adapters: catalog/protocol with in-memory, packaged JSONL, SQLite, DuckDB, and composite adapters; server adapter planned (S-2.11); Namespaces and tenancy: catalog namespaces, shared memory scopes, service tenants; Executable code reuse: qualified reusable capabilities and registered resolvers; live reuse not yet measured; Executes code or tools: generated projects run in a confined workspace or sandbox; Sandbox with declared effects: workspace backends with Docker resource limits and effect approval; no raw-host fallback; Standalone solution export: code_nodes/solution_export: package with tests and a manifest, verified in an interpreter that cannot import loop_engine (commit fcca293); Container and Job export: the export writes a Dockerfile and a Kubernetes Job; example 28 validates the worker manifests; Model Context Protocol tools: core/mcp_adapter and core/mcp_sdk_transport as adapters used by Loops; Native harness adapters: OpenCode, Codex, Pi, and other registered recipes run a step under the owning Loop; Plugin and skill admission: extension discovery, skill admission, plugin handshakes; nothing runs from file presence; Failed-check review: core/independent_failure_review: classification with quoted evidence and a second confirmation call; Evaluation or simulation product: core/evaluation_suite and loop-engine evaluate: frozen suites, exact denominators, case-level comparison; no simulation product (commit f8a2ec1); Registered deterministic graders: exact, canonical text, JSON equality, numeric tolerance, set overlap, regular expression; Per-implementation cost records: core/operation_cost_capture wired into every capability directory call and every model gateway invocation; cheapest verified implementation query (commit b1fbcdc, batch 10); Adversarial checks and mutants in the repository: every batch ships a mutant script; a surviving mutant blocks the commit; Conformance gates on every commit: conformance, hardcoding delta, documentation lint, self-test, and an example battery on an exported tree; Secret-free records by contract: learning records, metering records, and cost records carry digests and counts; secret-shaped text is refused; Model versus non-model choice: core/implementation_choice: a decision record per operation from ledger evidence or the declared fallback order (commit b1fbcdc); the fast path records the decision it made on every deterministic attempt (batch 10); Harness or prompt optimization: core/configuration_optimizer and loop-engine optimize; offline graders only (commit f8a2ec1); Exhaustive grid with honest coverage: exact enumeration with the exhaustive flag set only when every cell was evaluated; node grid stage counts; Explorative or evolutionary search: seeded stratified sampling; the campaign vocabulary names beam, successive halving, evolutionary, and novelty strategies (represented, not qualified); Noise injection robustness: core/configuration_optimizer optimize_with_noise: a cell must hold its gain under whitespace, case, typographic quote, and extra token perturbations of the held-out suite; converge reports honest stability (batch 10); Train gain and holdout loss acceptance: AcceptancePolicy: minimum train gain and maximum holdout loss; a memorizing cell is refused; Trains or exports specialists: core/specialist_training: naive Bayes specialist from recorded rows with a run-level split, exported as JSON weights, candidate resolver; no fine-tuning; Heuristic adoption policy: core/heuristic_adoption: one million runs by default; an exact atomic fingerprint is the only exception; Typed-decision model route: core/typed_decision: the typed_decision.choice contract, admission that refuses wrong candidate sets or rows that do not sum to one, a route refused without a judgment profile, an in-process specialist judge and an endpoint judge over an injected transport, a suite with exact denominators; typed action decisions over an indexed element table under typed_decision.action (batch 16); no live provider route yet; Hosted cloud: service software and container recipes exist; no public hosted endpoint is operated; Public pricing: packaging tiers drafted; no prices published; Metered units documented: verified completions, avoided model calls, optimize hours, judgment depth; Never-metered list: outcome and verification records, reading own history, exports, refusals; Tenant keys stored as digests: core/service_api: SHA-256 digests compared in constant time before any work; Container image published: ghcr.io/alisonjieli-png/loop-engine@sha256:5e97636b (public package; tags main and sha-855ab32) published by the workflow on commit 855ab32, pulled back by digest and doctor run in the workflow and from the development host (batch 12); Open source core: MIT; Persistent memory: catalog adapters (in-memory, packaged JSONL, SQLite, DuckDB, composite) keep records with identity and digest across sessions; Procedures as instructions: question forms, ask strategies, packs, and skill folders admitted before use; a model reads them at run time; Independent verification: core/independent_verification: a separate process with its own probes and criterion judgments; the producer's report is never the verdict; route separation from the producer when the policy declares it; Model routing: core/model_routes: named routes with declared purposes, provider handshakes, and a policy gate on every call; Self-hosted option: pip install from the repository, the Dockerfile, and the Kubernetes manifests of example 28; Search returns typed references before bodies: core/intelligence_layers and core/retrieval return references first and materialize a body after selection; example 09; Reuse evidence with credit split and regime shift: core/reuse_evidence: surprise weighted credit split posterior and a regime shift event; consulted by retrieval since batch 10; Suggested output shapes on model calls: core/suggested_output and core/response_contracts: seven registered contracts; deviation is recorded on the call record, never raised; One task working folder: materials folder with unpacked archives and selected binary inputs implemented; downloads kept as files and scoped views for Spawned Loops are not (Constitution LE-SOLVE-005 proposed); Runtime Memory scoped to one run: core/runtime_memory RunNoteBoard: temporary, scoped to one run, registered as a boundary; Fast path before the first model call: allow_fast_path_resolution: registered resolvers run before the first model call, a verified fast path ends with zero calls, an incomplete trace stays as repair evidence, and the decision is recorded (batch 10); Best-available resolution package: task_resolution_package/v1 on COMPLETED_PARTIAL: evidence, labeled assumptions, provisional bodies, missing material, questions, next actions; Question forms multiplied deterministically: strings/question_engine: forms with slots, multiply, combination_space; forms served as store records; Action vectors on every step: action_intent_vector/v1, action_vector_assessment/v1, outcome_vector/v2 with unknown kept distinct from false; the route guard; Budget-phase supervision: supervision policy thresholds in core/adaptive_practitioner_routing; demotion recorded; no live rerun has qualified it; Contract matching modes declared: core/contract_matching owns the five modes; strict on solution ports, flexible in the solutioning space; review of the remaining exact comparisons open; Verification on a different model route: IndependentVerificationPolicy.separate_route: every verifier call excludes the routes the producer used through the gateway's excluded_routes, the report records route_separation/v1, and a run whose only route is the producer's ends unavailable with the reason on record; off unless declared (batch 12); Step efficiency review: core/step_efficiency_review with a deterministic size judge and recorded judge kind (commit b1fbcdc); a record a step can write, not yet a step the Practitioner performs live; Meta-selection of selectors: in-memory preference setter and advisory interface; autonomous selector portfolios proposed (configuration preferences guide); Model ontology with placement rule: core/model_ontology ModelProfile and validate_tool_model_use; core/model_call_contract refuses non-text kinds by name; Convergence report with honest stability: core/configuration_optimizer converge: convergence_report/v1 (batch 10); Packaging tiers documented: docs/guides/packaging-tiers-and-hosted-service.md; Machine-readable roadmap: docs/roadmap/roadmap.yaml: R-01 to R-36, steps with verify, adversarial, evidence, status, and a dated status log; Verified competitor comparison: this record; nineteen companies read from their own pages on 2026-09-18; Base image pinned by digest: Dockerfile pins python:3.12-slim by digest; local build sha256:08ed84d3 runs doctor with exit 0 (batch 11); Pre-packaged detection and correction families: text conformance (seven operations, five catalog layers, escalation requests), duplicate detection (names, addresses, emails, phones; five blocking keys; weakest-signal confidence; clusters; dedupe proposal; possible pairs as typed decisions), email recovery from declared tables under the same bands, malformed field detection by dominant pattern margin, database copy to a new target with applied corrections and the dedupe proposal, never in place, and address component extraction from declared patterns with optional usaddress and libpostal adapters (batches 6, 13, and 14); Resource supervision of harness instances: core/local_resources: measured snapshot, instance ledger with an append-only event log, admission within a ceiling derived from the machine, stall detection, pause under memory pressure and resume on recovery through a controller that signals only owned handles (batch 17); cloud capacity within a client budget and administrator surfaces are proposed (S-4.8, S-4.9).
- Mem0: Context Intelligence served as records: memories and procedural memory as entries; Training data from records: Memory Export exports memories, not training sets; User Feedback applied at run time: Feedback Mechanism captures user signals; Graph or temporal facts: Graph Memory page; Outcome changes retrieval: Feedback Mechanism captures user signals, not outcome confidence; Multi-agent shared memory: Team Task Agent cookbook; Procedures as instructions: Memory Types: procedural_memory; Procedural memory: Memory Types: procedural_memory; Evaluation or simulation product: Memory Evaluation benchmarks memory quality, not task outcomes; Trains or exports specialists: Memory Export exports memories, not training sets; Metered units documented: add and retrieval requests; Open source core: Apache 2.0, 65,589 stars.
- Zep and Graphiti: Temporal validity on facts: Fact Invalidation stores when a fact became invalid; Graph or temporal facts: Fact Invalidation stores when a fact became invalid; Multi-agent shared memory: per-user graphs; shared provenance not documented; Namespaces and tenancy: per-user graphs; Metered units documented: credits; Open source core: Graphiti Apache 2.0, 30,986 stars.
- Supermemory: Context Intelligence served as records: memories with relationships and temporal truth; Temporal validity on facts: Graph memory: relationships, temporal truth, forgetting; User Feedback applied at run time: Review Inferred Memories: approve or decline; Graph or temporal facts: Graph memory: relationships, temporal truth, forgetting; Outcome changes retrieval: Review Inferred Memories: approve or decline, not task outcomes; Multi-agent shared memory: multi-tenancy and container tags; provenance not documented; Namespaces and tenancy: multi-tenancy and container tags; Metered units documented: ingested tokens; Open source core: MIT, 30,159 stars.
- Cognee: Temporal validity on facts: bi-temporal facts in the enterprise tier; Graph or temporal facts: induced ontologies; bi-temporal facts in the enterprise tier; Executable code reuse: indexes code as a data source; does not run or reuse it; Outcome changes retrieval: feedback-informed retrieval claimed by the vendor; not found in the documentation index; Metered units documented: tokens plus workspaces; Open source core: Apache 2.0, 30,809 stars.
- Honcho (Plastic Labs): Graph or temporal facts: Peer Representations and Directional Representations; Outcome changes retrieval: search filters change queries, not trust from outcomes; Multi-agent shared memory: multi-peer memory with an Evidence page for reasoning origins; Metered units documented: ingestion tokens and reasoning queries by depth; Open source core: AGPL-3.0, 7,244 stars; Public pricing: ingestion $2 per million tokens; reasoning $0.001 to $0.50 per query.
- MemOS (MemTensor): Runtime History with cost and verification: Tool Calling records tool decisions and results; User Feedback applied at run time: feedback exists; no verification; Graph or temporal facts: Neo4j and PolarDB graph modules; Outcome changes retrieval: feedback exists; no verification; Multi-agent shared memory: Group Chat; Procedures as instructions: Self-Evolving: distills reusable structured methods; Procedural memory: Self-Evolving: distills reusable structured methods; Executable code reuse: a distilled skill is rendered into the prompt as an invocation guide; Executes code or tools: Tool Calling records tool decisions and results; the agent runs them; Metered units documented: adds, searches, and tokens; Open source core: Apache 2.0, 11,455 stars.
- Hindsight (Vectorize): Graph or temporal facts: entities, relationships, graph search; Multi-agent shared memory: shared memory banks; Executable code reuse: its tools are retain, recall, reflect over memory, not reusable task code; Metered units documented: retain and recall per million tokens; reflect per call; Open source core: MIT, 23,894 stars.
- SenseLab (AMFS): Runtime History with cost and verification: outcomes reconcile the read set; the evidence posterior; Training data from records: training export and Managed Models, paid; Outcome changes retrieval: evidence posterior in evidence.py; action priors; Memory versioning: branches, merge, rollback in the paid edition; Multi-agent shared memory: rooms in the paid edition; Evaluation or simulation product: a preregistered benchmark harness in the repository; not a product; Trains or exports specialists: training export and Managed Models, paid; Metered units documented: operations: reads 1, writes 2; Never-metered list: outcomes are free; Open source core: Apache 2.0 core, 76 stars.
- Letta: Code Intelligence with contracts: skills may carry scripts; the model chooses to invoke them; Memory versioning: git-versioned memory filesystem; Multi-agent shared memory: team organizations and agent sharing; Procedures as instructions: Skills: folders of instructions, scripts, and assets; Executable code reuse: skills may carry scripts and Mods are trusted local code, but the model chooses to invoke them; Executes code or tools: cloud sandboxes and tool execution billed per second; Sandbox with declared effects: cloud sandboxes billed per second of tool execution; Harness or prompt optimization: harness customization by hand, not automatic; Metered units documented: per agent per month plus seconds of tool execution; Open source core: Apache 2.0, 24,786 stars.
- Synth: Context Intelligence served as records: projects bind repos and reusable knowledge; Code Intelligence with contracts: no capability library; Runtime History with cost and verification: immutable traces with verifiers and rubrics; Training data from records: supervised fine-tuning from the workshop; Executable code reuse: projects bind repos and reusable knowledge; no capability library; Executes code or tools: container pools; Sandbox with declared effects: container pools; Standalone solution export: Repo Review and PR returns a pull request; Independent verification: Evaluation Standards: verifiers, rubrics, rewards over immutable traces; Registered deterministic graders: verifiers and rubrics over immutable traces; Harness or prompt optimization: GEPA and GELO optimizers; Explorative or evolutionary search: GEPA is an evolutionary prompt optimizer; Trains or exports specialists: supervised fine-tuning from the workshop; Open source core: software development kit MIT, 82 stars; Public pricing: $10 workshop allowance; no price list.
- Tellurio and Afnio: Executes code or tools: the software development kit runs the workflow it optimizes; Harness or prompt optimization: auto-tunes harness and prompts; Open source core: claimed open source; repository not found today; Metered units documented: users and optimize hours; Public pricing: $50 per user; $1 per optimize hour.
- LangWatch: Runtime History with cost and verification: traces of tool calls and workflow nodes with evaluators; Training data from records: Finetuning Agents with GRPO guide; Executes code or tools: tracks tool calls; workflow nodes; Independent verification: evaluators and scenario tests; not independent of the configuration; Registered deterministic graders: evaluators and scenario tests; Harness or prompt optimization: Automatic Prompt Optimization; DSPy with scenarios as the metric; Explorative or evolutionary search: DSPy optimizers; Trains or exports specialists: Finetuning Agents with GRPO guide; Metered units documented: seats plus events; Open source core: Apache 2.0 open core, 4,814 stars.
- Not Diamond: Model routing: $0.05 per million tokens routed; Harness or prompt optimization: prompt optimization mentioned by the vendor; not verified today; Metered units documented: tokens routed; Open source core: Python software development kit archived 2025-12-11.
- TypeSafe (Jev): Typed-decision model route: Jev returns typed decisions with probabilities and confidence; Metered units documented: input tokens; output free; Public pricing: $0.042 per million input tokens, output free; text only; no open weights.
- PrismML (Bonsai): Open source core: Apache 2.0 weights on the model hub; Self-hosted option: runs on a laptop with its runtime.
- Osmosis (Gulp AI): Evaluation or simulation product: evaluation integration for retraining cycles; Trains or exports specialists: forward-deployed reinforcement learning post-training.
- Adaptive ML (acquired by Datadog): User Feedback applied at run time: custom judges configured by the customer; Independent verification: custom judges and A/B testing, configured by the customer; Registered deterministic graders: custom judges; Trains or exports specialists: ADAPT, EVALUATE, SERVE.
- Distyl: Executes code or tools: composable routines with policy-aware execution; Independent verification: built-in auditability claimed; Hosted cloud: services-led deployments; the platform page was not reachable today.
- TensorZero (archived): Runtime History with cost and verification: a gateway that stores inference data for optimization; Model routing: gateway; Open source core: Apache 2.0, archived 2026-06-11; no longer maintained.
- Overmind, Lemma: Persistent memory: sites unreachable at any resolvable domain today.

## Comparison chart

Stars and licenses are from the GitHub programming interface on 2026-09-18.
"Open core" means an open source engine with paid hosted or governance
features.

| Company | What it sells | Open source | Pricing and packaging (vendor's numbers) | Metering unit | Buyer | Overlap with a Loop Engine boundary | What Loop Engine has that it lacks | What it has that Loop Engine lacks |
|---|---|---|---|---|---|---|---|---|
| Mem0 | Persistent memory for agents; graph memory; memory consolidation | Apache 2.0, 65,589 stars | Hobby free (10,000 adds and 1,000 retrievals per month); Starter $19 per month (50,000 adds, 5,000 retrievals); Pro $249 per month (500,000 adds, 50,000 retrievals, graph memory, consolidation); Enterprise custom with on-premises, audit logs, single sign-on | Add and retrieval requests per month | Solo builders to production teams | Context Intelligence retrieval; procedural memory in its Python package | Execution, verification, code reuse, typed contracts, cost records | Scale, integrations, a consolidation process, and a large community |
| Zep and Graphiti | Temporal knowledge graph memory with provenance and evolving facts | Graphiti Apache 2.0, 30,986 stars | Free 10,000 credits per month; Flex $125 per month (50,000 credits, then $25 per 10,000); Flex Plus $375 per month (200,000 credits, then $75 per 40,000); Enterprise custom with bring your own key and bring your own cloud | Credits | Startups to large enterprises | Context Intelligence with time validity; the freshness rule Loop Engine records on facts | Execution, verification, the solutions space | Edge invalidation at write time, a mature graph store, rate-limited tiers |
| Supermemory | Model-independent memory and context engine, connectors, self-hosting | MIT, 30,159 stars | Free ($5 credits per month); Pro $19 per month ($20 credits); Max $100 per month ($130 credits); Scale $399 per month ($600 credits, self-hosted option, compliance reports); Enterprise custom; its own token unit at $5 to $10 per million for memory and $1 to $2 per million for retrieval, plus $5 per million search queries and $100 per million operations at Scale | Ingested tokens, queries, operations | Individual developers to enterprises | Context Intelligence; the "retain a reference, load on demand" rule | Verification, code reuse, model ontology | Connectors, a startup program, compliance packaging, a forward-deployed engineer at the top tier |
| Cognee | Memory platform with graph relationships, ontologies, citations | Apache 2.0, 30,809 stars | Free (1 million tokens); Standard $1.00 per million tokens processed plus $5 per additional workspace; Enterprise bring your own cloud, custom; open source self-hosted free | Tokens processed, workspaces | Individuals to large organizations | Ontology and evidence graph; citations resemble Loop Engine's evidence references | Execution, verification, cost-based implementation choice | Source connectors, code indexing, bi-temporal conflict resolution in the paid tier |
| Honcho (Plastic Labs) | Reasoning-based memory of people, agents, and projects; "continual learning for stateful agents" | AGPL-3.0, 7,244 stars | Ingestion $2.00 per million tokens; unlimited context calls; reasoning tiers from $0.001 to $0.50 per query; startups get $1,000 in credits and twelve months of subsidized pricing | Ingested tokens and priced reasoning queries | Companion, tutor, support, and coding agent builders | User Feedback Intelligence and per-user representations | Independent verification, executable capability | A per-query reasoning ladder that prices depth of thought explicitly |
| MemOS (MemTensor) | Memory operating system with a local edition and a cloud | Apache 2.0, 11,455 stars | Cloud Free (50,000 adds, 20,000 searches, 3 million input and 1 million output tokens); Starter $19 per month (600,000 adds, 200,000 searches), shown as currently free; Pro $286 per month (80 million adds, 30 million searches), shown as currently free; Enterprise custom; MemOS Lite runs fully local | Adds, searches, tokens, storage | Students and proofs of concept to scaling teams | Skills as prompt guides overlap with Code Intelligence, but they are instructions, not executables | Qualified executable tools, verification | A behavior-scoring plugin and a large user base in its ecosystem |
| Hindsight (Vectorize) | Agent memory with retain, recall, and reflect operations | MIT, 23,894 stars, created 2025-10-30 | Self-hosted free; cloud pay as you go: retain $10.00 per million tokens, recall $0.75 per million, reflect $0.05 per call, storage $0.25 per million tokens per month after 30 days; Enterprise custom with bring your own cloud and uptime commitments | Tokens per operation kind, calls | Developers of agents and coding assistants | Context Intelligence; the reflect step resembles Loop Engine's derived records | Verification, code reuse, cost records | Per-operation pricing that separates storing, retrieving, and synthesizing |
| SenseLab (AMFS) | Outcome-linked memory, decision traces, confidence, training export, managed tool-call models | Apache 2.0 core, 76 stars | Free $0 (1,000 operations); Starter $29 per month (25,000); Pro $149 per month (50,000); Teams $449 per month (300,000); overage packs of 10,000 operations at $25, $20, or $15 by plan; reads cost 1 operation, writes 2, outcome commits 0; Managed Models $199 per month per account, serving at $1.00 input and $5.00 output per million tokens (a pro variant at $1.25 and $8.00), 10 million training tokens per month included then $10 per million; the pricing page shows 1 seat on Free while the billing document shows 2 | Operations, seats, keys, training and serving tokens | Individuals, small teams, businesses | The reuse evidence rule Loop Engine adopted on 2026-09-18; training export; briefings | Execution, verification, code and tool reuse, typed contracts, implementation choice | Branching, merge, pull requests, access control, signed traces, a dashboard, and hosted fine-tuning, all paid-only |
| Synth | Local research workbench (macOS) and managed research in the cloud; optimizers and containers as open source | Software development kit MIT, 82 stars | Workshop free with a permanent $10 allowance for account-backed work; local models, data, and execution need no account; cloud research billed separately; no public price list | Account-backed usage, provider costs pass through | Researchers and research engineers | The solutioning space: experiments, traces, candidates, comparison | Independent verification as a gate, the solutions space, code reuse across tasks | A polished local workbench and "experiments per minute" as the product promise |
| Tellurio and Afnio | Open source workflow optimization and a hosted experiment tracker | Site names github.com/Tellurio-AI/afnio; not found through the GitHub programming interface today (a tutorials repository exists) | Studio Free $0 per user (1 seat, 20 private runs and 3 private optimize hours per month); Pro $50 per user per month (5 seats, 80 private runs, 20 optimize hours, $1 per additional hour); Enterprise custom | Seats, runs, optimize hours | Individuals to enterprise agent teams | Harness and prompt optimization; explicit operation inputs and outputs resemble Loop Engine's typed ports | Verification, model ontology, reuse of executables | Optimize time as a metered unit |
| LangWatch | Evaluations, simulations, scenarios, tracing for agents | Apache 2.0, 4,814 stars | Developer free (50,000 events per month, 14 days of data, 2 users); Growth €29 per core seat per month with 200,000 events included then €5 per 100,000 and €3 per gigabyte beyond 30 days; Enterprise custom, self-hosted or on premises | Events, seats, storage | Individual developers to regulated teams | Independent evaluation and campaign reporting | Execution ownership, reuse, model ontology | Simulation-based testing and marketplace billing |
| Not Diamond | Predicts which model to use per prompt | Python software development kit archived 2025-12-11, 91 stars | Pay as you go at $0.05 per million tokens routed, positioned as cheaper than the cheapest model; Enterprise custom with organization analytics and single sign-on | Tokens routed | Developers and enterprise teams | Model routing inside the model ontology | Routing to no model call at all, verification, reuse | A fee anchored below the savings it claims (20 to 40 percent) |
| TypeSafe (Jev) | Typed decisions with probabilities instead of text; text only | No open weights (none on the model hub) | $42 per billion input tokens ($0.042 per million), output free; version jev-1.13.0 behind aliases jev-latest and jev-preview; 64,000 token context; rate limits adjust dynamically | Input tokens | Enterprises automating decisions | The judgment model kind in the model ontology; a candidate hybrid contract sensor | The ability to decide a model is unnecessary; verification | A calibrated-probability product and 12.2 times cheaper batching of many questions in one call |
| PrismML (Bonsai) | Ternary and 1-bit compressed open-weight models and a runtime | Apache 2.0 weights on the model hub (Ternary-Bonsai-27B: 650,692 downloads; Bonsai 2 27B: 405,609) | No public pricing; models free to download; a consumer application | None published | Device and laptop deployments | Local generative routes under the model ontology | Everything above the model | The models themselves and a runtime that makes them run |
| Osmosis (Gulp AI) | Forward-deployed reinforcement learning post-training for task-specific models | No public repository found | No public pricing; hands-on deployments; retraining "as little as every hour" | Not published | Enterprises needing extraction, tool-use, and code models | The "train our own model" branch of the engineering-lab questions | Deciding whether to train at all from cost records | Training infrastructure and reward engineering as a service |
| Adaptive ML | Post-training, evaluation, and serving of specialized models | Not applicable | Acquired by Datadog; the vendor site links a June 2026 announcement; named enterprise customers | Not published | Enterprises | Same branch as Osmosis | Same as Osmosis | An exit to an observability vendor |
| Distyl | Services-led deployment of agentic systems with a platform of composable routines and auditability | Not applicable | No public pricing; investors named on the site; "1B+ decisions processed annually"; "50+ enterprise deployments" | Engagements, decisions processed | Fortune 500 and institutions | The lab-of-engineers operating model | A product | Revenue from deployment work rather than software |
| TensorZero | Was a gateway, observability, evaluation, and optimization platform | Apache 2.0, 11,720 stars, archived 2026-06-11 | "No longer maintained" per its site | None | None now | Gateway and evaluation | Nothing to add | A warning: an open gateway without a moat did not survive |
| Overmind, Lemma | Described in the owner's notes as trace-driven optimization with specialist training, and trace auditing with failure grouping | Unverified | Unverified; the .ai domains reached today belong to other companies or are parked | Unverified | Unverified | Would overlap the failed-check review and the engineering loop | Unverified | Unverified |

## What the chart says about Loop Engine's position

Every memory vendor sells retrieval, provenance, and confidence over prose
entries. None executes code, verifies a deliverable, or keeps a tool as a
qualified executable capability, and none records which implementation of
an operation was cheapest. That is the gap the owner named on September 18,
and it is now a typed boundary in Loop Engine (the model ontology, the
operation cost records, the solutions space). The optimization vendors
(Synth, Tellurio, and the unverified pair) sell the solutioning space
without the solutions space: experiments and tuned harnesses, but no plural,
verified, reusable solutions per task.

The strongest evidence for the position is a competitor's own record. The
AMFS repository's preregistered benchmark found every memory arm worse than
no memory on first-attempt success at five to seven times the tokens until
outcomes reconciled the exact read set (see the
[SenseLab record](EXTERNAL-SENSELAB-2026-09-18.md)). Loop Engine's thesis is
that reuse must be selected by verified outcomes and cost, not by
similarity, and that the cheapest adequate implementation is often not a
model call. No vendor above sells that decision.

## How they charge, and what each unit rewards

| Pattern | Who uses it | What the unit rewards | Fit with Loop Engine's thesis |
|---|---|---|---|
| Operations per month with paid overage packs | SenseLab (reads 1, writes 2, outcomes free) | More reads and writes; outcomes deliberately free so learning signal keeps flowing | Poor as a primary unit: Loop Engine exists to make fewer calls. The free outcome commit is worth copying for verification records. |
| Tokens ingested or processed | Supermemory, Cognee, Hindsight, Honcho ingestion | Heavier ingestion | Poor: it rewards loading more context, the opposite of the minimal-sufficient-context rule. |
| Per operation kind at different rates | Hindsight (retain $10, recall $0.75, reflect $0.05) | Separates storing, retrieving, and synthesizing | Good model for Loop Engine's operation cost records: price what costs, not what is convenient to count. |
| Per query by depth of reasoning | Honcho ($0.001 to $0.50 per query) | Paying more for more deliberation | Directly matches the engineering-lab question "how much reasoning does this step need"; a natural unit for the judgment and verification services. |
| Credits with rollover and rate limits | Zep | Predictable spend, rate-limited tiers | Neutral; useful for a hosted judgment service. |
| Per seat plus usage | LangWatch (€29 per core seat), Tellurio ($50 per user), Letta Teams ($20 per seat) | Team adoption, collaboration | Good for the Studio and campaign dashboards; seats do not distort engine behavior. |
| Per agent per month plus tool execution time | Letta ($0.10 per active agent, $0.00015 per second of tool execution) | Long-lived agents and compute time | Interesting for Spawned Loops and sandbox execution: charge the compute a run actually used. |
| Optimize hours | Tellurio ($1 per additional hour) | Time spent searching configurations | Matches campaign runs; the honest unit for the engineering loop. |
| Routing fee below the savings | Not Diamond ($0.05 per million tokens routed, claimed 20 to 40 percent savings) | Fee anchored to avoided cost | The best analog for the implementation selector: charge a fraction of the model calls the reuse and cost records avoided, which is measurable from the records. |
| Managed specialist models as subscription plus serving | SenseLab ($199 per month, $1 and $5 per million tokens, eligibility thresholds) | Training only when data suffices; recurring serving | Direct precedent for the "train our own model" branch; the eligibility thresholds (100 to 200 decisions, at least 3 tools, at least 60 percent success) are a product mechanism, not only a guide. |
| Open core with governance in the paid tier | SenseLab (branches, access control, signed traces, dashboard), Supermemory (compliance at Scale), Mem0 (on premises, audit logs) | Free engine, paid collaboration and control | The natural split for Loop Engine: runtime, contracts, and records open; hosted verification, shared solutions spaces across teams, managed specialists, and dashboards paid. |
| Free local, paid cloud compute | Synth ($10 allowance), MemOS Lite, Hindsight self-hosted | Adoption on the developer's machine | Loop Engine already runs locally; the paid path is the shared and hosted layers. |
| Services-led deployment | Distyl, Osmosis, Supermemory's forward-deployed engineer | Revenue from engagements | The lab-of-engineers model can be sold as forward-deployed research on a customer's task families, with the records as the deliverable. |
| Exit | Adaptive ML to Datadog (June 2026) | Observability vendors buying the learning layer | The acquisition case the owner raised is real; the buyer wanted production signals feeding specialized models, which Loop Engine's records are designed to produce. |
| Abandonment | TensorZero (archived) | None | An open gateway without a differentiated moat did not survive; the moat must be the verified records and the reuse they enable. |

Price anchors from the market on this date: entry tiers at $19 to $29 per
month, team tiers at $125 to $449 per month, seats at $20 to $50 per user
per month, and usage from $0.042 per million tokens (a typed decision) to
$10 per million tokens (storing memory).

## Lessons Loop Engine should take

1. Meter what the thesis improves. A unit that grows when the engine works
   well is verified completions per task family, or model calls avoided by
   qualified reuse; both are already computable from the operation cost
   records and the learning records. A unit that grows when the engine
   works badly (reads, tokens ingested, calls) contradicts the product.
2. Keep outcomes free. SenseLab makes outcome commits cost nothing because
   the learning loop starves without them. Loop Engine's independent
   verification records should never be metered.
3. Price deliberation depth, not volume, for hosted judgment. Honcho's
   per-query ladder and TypeSafe's flat input rate show buyers accept a
   price for a bounded judgment; the engineering-lab question "is a model
   necessary here" is the product, and the answer "no" should be cheapest.
4. Put governance, not the engine, behind the paywall. Every open-core
   vendor draws the line at branching, access control, signing, dashboards,
   and hosting. For Loop Engine the equivalents are shared solutions spaces
   across teams, hosted verification, managed specialists, and the Studio.
5. Gate training on evidence thresholds and sell it as a subscription plus
   serving. SenseLab's numbers are a usable starting shape; Loop Engine's
   `TrainingExportPolicy` already excludes unverified and synthetic rows,
   which is the stricter version of the same rule.
6. Charge the engineering loop by the hour and the selector by avoided
   cost. Tellurio's optimize hours and Not Diamond's routing fee are the two
   units that match what Loop Engine actually does.
7. Do not compete on memory. The memory market is crowded, priced to the
   floor, and its own benchmark shows memory without outcome-grounded
   selection can hurt. Compete on the decision of which machinery performs
   each operation, and on the verified records that make that decision
   defensible.

## Caveats

- Vendor pages change; every number carries the date at the top.
- Star counts measure attention, not revenue or quality.
- SenseLab's pricing page and billing document disagree on Free seats (1
  versus 2); the discrepancy is recorded, not resolved.
- Not Diamond's Python software development kit is archived while its
  product page remains live; the product's status was not verified beyond
  the page.
- Overmind and Lemma are recorded from the owner's notes only.
- No claim here about a company's revenue, customers, or roadmap goes
  beyond what its public page states.
