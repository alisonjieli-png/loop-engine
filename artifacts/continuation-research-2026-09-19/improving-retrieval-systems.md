# Improving retrieval systems that Loop Engine could wrap

Date: 2026-09-19. Status: bounded research and integration proposals.
Only primary project documentation, original repositories, and original
papers were used. Nothing was installed, trained, or run against a provider.

The best first experiments are DSPy with GEPA for offline optimization and
AutoRAG2 for feedback-driven document searching. Haystack or LlamaIndex can
supply individual missing components. Graphiti and LightRAG are conditional
choices for temporal or cross-document knowledge. Agent Lightning is a later
weight-training project, not a first-release retrieval dependency.

None of these sources establishes unlimited recursive self-improvement,
monotonic gains, or safe autonomous promotion on arbitrary customer data.
An adaptive loop, persistent memory, and a better held-out result are three
different claims.

## Classification and scope

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
    ├── Run mode: deterministic, hybrid, or non-deterministic
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition
    ├── Exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the selected mode permits a model
    └── Run History records
```

```text
Different meanings of retrieval improvement
├── Within-request correction
│   └── assess evidence, rewrite a query, retrieve again or abstain
├── Across-run prompt or pipeline optimization
│   └── propose configurations, evaluate them, retain a selected candidate
├── Incremental knowledge and memory updates
│   └── add facts, invalidate outdated facts or retain feedback
└── Weight training
    └── update a trainable model using supervised examples or rewards
```

Ten candidate entries follow. DSPy and GEPA are treated as one complementary
toolkit entry. The two foundational research methods are paired in the last
entry and are not represented as maintained production services. Project
maintenance and version statements are observations from current primary
pages, not support guarantees or a dependency lock.

The integration boundaries, risks, and discriminating tests below are our
proposals. They are not upstream claims or completed Loop Engine integrations.

## 1. DSPy with GEPA

Type: offline prompt and program optimization. GEPA proposes changes using
execution feedback and scores a population of candidates on validation data.
DSPy's current documentation exposes metric-call limits, candidate lineage,
and optional code-proposer hooks. The standalone project also supports
optimization of text artifacts beyond prompts. This does not update model
weights by itself.
[DSPy integration](https://github.com/stanfordnlp/dspy/blob/main/docs/docs/diving-deeper/gepa-in-depth.md),
[GEPA implementation](https://github.com/gepa-ai/gepa).

The original paper is `2507.19457v2`, revised February 14, 2026. It reports
task-specific comparisons, not general recursive improvement or a Loop Engine
benchmark. [Original paper](https://arxiv.org/abs/2507.19457v2).

Fit: a Practitioner self-improvement assignment proposes a query-rewrite
prompt, evidence grader, or ordering over already eligible retrieval choices.
Start with prompts and bounded configuration fields, not executable code edits.
Keep optimizer selection separate from independent acceptance.

Discriminating test: compare the unchanged retriever, a fixed manual prompt,
and the optimized candidate on untouched queries under the same total model
and time allowance. Include irrelevant documents and unanswerable questions.
An optimizer that improves its repeatedly inspected validation set but loses
on the untouched set has not passed.

## 2. AutoRAG2, the current librarian

Current assessment: the leading integrated agentic-retrieval trial candidate,
not an installed or qualified Loop Engine provider. A September 19 recheck
pins upstream revision `be20a32200dc5f5b130af01684939c66fc33fbc5`.
Its package is `@autorag/librarian` version `2.5.1`, requires Node.js 24 or
newer, and is MIT-licensed. Its public exports include `AutoRAGAgent`,
`SearchDocumentsResponse`, retrieval and memory modules, and `AutoRAGLite`.
[Pinned package](https://github.com/Marker-Inc-Korea/AutoRAG/blob/be20a32200dc5f5b130af01684939c66fc33fbc5/package.json),
[public exports](https://github.com/Marker-Inc-Korea/AutoRAG/blob/be20a32200dc5f5b130af01684939c66fc33fbc5/src/index.ts),
[license](https://github.com/Marker-Inc-Korea/AutoRAG/blob/be20a32200dc5f5b130af01684939c66fc33fbc5/LICENSE).

The documented calls `searchDocuments()` and `recordFeedbackByNumbers()`
provide a plausible adapter boundary. The agent's curated answer is not an
authoritative intelligence record. A Loop Engine adapter must retain exact
original-source identities and digests, isolate memory by permitted scope,
disable unapproved automatic installation and sharing, and account for model,
filesystem and indexing effects. It must reject an unsupported requested
retrieval mode instead of silently accepting an upstream degraded path.
The public wrapper must return typed references even if the underlying engine
also produces an answer. [Documented interface](https://github.com/Marker-Inc-Korea/AutoRAG#quick-start).

No Loop Engine adapter, tenant-isolation qualification, held-out improvement
measurement, or cost comparison has been completed for this candidate. The
current built-in Retriever still needs an external-provider registration
boundary before this becomes a supported selectable engine. The first trial
should compare an unchanged local baseline, the candidate with empty memory,
and the same candidate with frozen training-only memory on held-out tasks.
Add poisoned feedback, revoked sources, missing indexes and budget exhaustion
as refusal cases. GEPA remains a separate candidate for deferred optimization,
not a mandatory stage inside each retrieval.

Type: within-request agentic retrieval plus persistent feedback memory. The
current repository is a Pi-based librarian, not the original pipeline search
tool. Its model searches, reads sources, judges evidence, and returns typed
curation. It records retrieval memory and explicit useful/not-useful feedback.
The current package manifest identifies `@autorag/librarian` version `2.5.1`.
[Current repository](https://github.com/Marker-Inc-Korea/AutoRAG),
[Package manifest](https://github.com/Marker-Inc-Korea/AutoRAG/blob/main/package.json).

Fit: a customer-side, sandboxed query adapter with an exact input contract and
source-backed output. It is not effect-free discovery: direct file reading,
model calls, indexing, and memory writes need separate authority. The upstream
default can automatically install MinSync; disable that behavior and install
only an independently qualified pinned dependency during an authorized build.
The README's improvement claim is not independent evidence of generalization.

Discriminating test: let memory learn only from a training-query stream, then
freeze it. Compare frozen learned memory with empty memory on future held-out
queries and another document collection. Test poisoned feedback, changed
permissions, unavailable indexing, and malicious document instructions.
Require original-source identities rather than trusting curated prose alone.

## 3. Original AutoRAG under `legacy/`

Type: offline pipeline selection. This separate Python product evaluates
retrieval and generation module combinations using supplied evaluation data.
The current main README explicitly says it remains maintained for fixes,
dependencies, and package releases, while new feature work targets AutoRAG2.
Its license and distribution are also distinct from the new librarian.
[Legacy optimizer](https://github.com/Marker-Inc-Korea/AutoRAG/blob/main/legacy/README.md),
[Product distinction and maintenance policy](https://github.com/Marker-Inc-Korea/AutoRAG).

Fit: a comparison tool for chunking, retrieval, reranking, and generation
configurations. Treat the winning trial as a candidate manifest, not an
automatically deployable authority. Do not describe its pipeline optimizer
as a feature of `@autorag/librarian`.

Discriminating test: compare its selected pipeline against our baseline and
a small declared search over the same choices, with equal total evaluation
cost. Hold out document families as well as questions. Preserve every failed
configuration and avoid using generated evaluation answers as unquestioned
ground truth.

## 4. Haystack

Type: composable retrieval and within-request control, with evaluation
components. Its pipelines support branching and iterative correction;
evaluation can target retrieved documents or final answers. Those mechanisms
enable an improvement study but do not themselves create an across-run
learning policy. The maintainer announced Haystack 3.0 on July 20, 2026;
older version 2 examples must not silently define the selected contract.
[Pipelines](https://docs.haystack.deepset.ai/docs/pipelines),
[Evaluation](https://docs.haystack.deepset.ai/docs/evaluation),
[Version 3 announcement](https://haystack.deepset.ai/blog/haystack-3-release).

Fit: wrap a needed retriever, reranker, document converter, or evaluator.
Avoid introducing its entire orchestration layer merely to connect two
components already owned by Loop Engine.

Discriminating test: swap exactly one component while keeping corpus, source
filters, models, and answer generation fixed. Check document recall, citation
support, failure visibility, and cost. Then separately test whether a bounded
correction loop improves outcomes compared with the same component once.

## 5. LlamaIndex

Type: ingestion, retrieval, reranking, and workflow composition. The current
official example explicitly separates retrieval, model-based reranking, and
synthesis. These are reusable operations, not evidence that a deployed
retriever improves itself. Its open-source framework is distinct from the
managed LlamaParse platform. The older `QueryPipeline` documentation warns
of feature freeze and points to Workflows.
[Current workflow example](https://developers.llamaindex.ai/python/examples/workflow/rag/),
[Framework and managed-platform distinction](https://github.com/run-llama/llama_index),
[QueryPipeline warning](https://docs.llamaindex.ai/en/stable/module_guides/querying/pipeline/).

Fit: selected ingestion and retrieval adapters with source identities retained.
Do not require managed parsing or send private documents to it by default.

Discriminating test: compare direct retrieval with the selected reranker on
the same eligible candidate pool. Include a case where the best-looking
document belongs to another tenant, and a case where reranking discards the
only supporting source. Model-based relevance is not permission or truth.

## 6. LangGraph retrieval components

Type: within-request control and state. The official retrieval example grades
documents, generates an answer if they are relevant, or rewrites the question
and retrieves again. Persistent execution state or tracing does not by itself
optimize the retrieval policy across runs.
[Official retrieval-agent example](https://docs.langchain.com/oss/python/langgraph/agentic-rag).

Fit: borrow the control pattern or wrap a bounded external query operation.
Do not replace the canonical Loop or create a second first-party graph
runtime. If an external graph is wrapped, declare who owns retries, state,
deadlines, model accounting, cancellation, and acceptance. Optional hosted
tracing requires separate data-sharing authority.

Discriminating test: introduce persistently irrelevant evidence, a false
positive grader, and interrupted execution. Confirm termination within total
authority, no hidden replay of committed effects, and no final success solely
because the inner graph stopped.

## 7. LightRAG

Type: knowledge-graph and vector retrieval with incremental updates and
selective deletion. Its current repository describes dual-level retrieval,
document parsing and chunking choices, and rebuilding affected graph content
after deletion. Keeping an index current is not the same as learning a
better retrieval policy. Upstream quality and speed claims require our own
task-controlled comparison.
[Original project](https://github.com/HKUDS/LightRAG).

Fit: an optional derived index for questions that genuinely need
cross-document relationships. Keep original documents and exact digests
authoritative. Separate model-assisted ingestion from permitted query work.

Discriminating test: compare against the existing lexical/vector baseline on
both relational and simple lookup questions. Measure ingestion cost as well
as query cost. After deleting or replacing a source, test whether answers,
relationships, citations, and caches still reveal its information.

## 8. Graphiti

Type: incremental temporal knowledge and memory updates. Graphiti retains
episodes as provenance, temporal fact validity, and hybrid retrieval. Its
Model Context Protocol server includes both search and mutating episode or
maintenance operations. The open-source project requires surrounding
infrastructure; it is not the managed Zep product. These updates do not imply
model-weight training or independently verified policy improvement.
[Original project](https://github.com/getzep/graphiti).

Fit: a temporal derived index when changing facts and historical queries are
central requirements. Graph entities are passive knowledge, not operational
Loop vertices. Its ingestion and deletion tools need different permissions
from its search tools.

Discriminating test: feed dated, contradictory facts and ask both present and
historical questions. Compare it with a timestamp-filtered baseline. Test
tenant separation, source revocation, entity merging errors, and deletion
across every retained episode and derived representation. More remembered
facts are not automatically more correct answers.

## 9. Microsoft Agent Lightning

Type: model-weight training. Current main is a refactored version 1.0 with a
trainer, model-request gateway, and rollout controller. It trains with real
harness interaction and includes search-agent examples. Earlier prompt
optimization and `LightningStore` tutorials describe the pre-version-1.0
system, not proof of the current architecture.
[Current implementation](https://github.com/microsoft/agent-lightning).

The new report is `2608.17528v1`, submitted August 18, 2026. The repository
lists its announcement on August 19. This date distinction is retained rather
than silently converting a repository announcement into the paper date.
[Original report](https://arxiv.org/abs/2608.17528v1).

Fit: later training of a selected retrieval policy or trainable model through
an explicitly authorized research adapter. Requires model and data rights,
training compute, bounded rollouts, and careful trace handling. It does not
let an ordinary hosted-model credential authorize weight updates.

Discriminating test: compare a frozen initial checkpoint, a prompt-optimized
baseline, and the trained checkpoint on an untouched task population. Use the
same deployment harness. Evaluate reward hacking, source leakage, and
regressions alongside task quality and total training cost.

## 10. Self-RAG and Corrective Retrieval Augmented Generation

These are distinct research methods, not interchangeable product names.
Self-RAG trains a model to use retrieval and reflection tokens, then uses
those decisions during inference. The paper is `2310.11511v1`, submitted
October 17, 2023. It is not simply a generic self-critique prompt and is not
evidence of continuous online weight updates.
[Self-RAG paper](https://arxiv.org/abs/2310.11511v1),
[Original implementation](https://github.com/AkariAsai/self-rag).

Corrective Retrieval Augmented Generation evaluates retrieval quality and
selects corrective actions, including web search and evidence filtering.
The inspected paper is `2401.15884v3`, revised October 7, 2024. This primarily
informs within-request recovery; a correction is not independent acceptance.
[Corrective Retrieval Augmented Generation paper](https://arxiv.org/abs/2401.15884v3),
[Original implementation](https://github.com/HuskyInSalt/CRAG).

Fit: implement or wrap selected evidence-grading and correction operations.
Web fallback must use existing Web Research authority, not become an implicit
network grant after poor local retrieval.

Discriminating test: freeze deliberately good, misleading, empty, and
contradictory retrieval outputs. Check that correction improves grounded
answers or appropriate abstention, while a confident but wrong grader cannot
approve unsupported material. Test network-denied operation explicitly.

## Existing boundaries to extend

The current [Core Architecture contract](../../docs/components/core-architecture/README.md)
states that open external retrieval-backend registration is not shipped.
`Retriever` currently selects from explicit built-in backends. None of the
projects above is already a drop-in supported backend.

| Proposed integration | Existing owner | Required distinction |
|---|---|---|
| Initial bounded external query operation | `CapabilityDirectory`, `CapabilityHandshake`, and Custom Plugins | Discovery remains effect-free; invoking search that reads files or calls models requires exact authority. |
| Common search and selected references | `core.intelligence_layers`, `core.retrieval`, `loop.loop_capsule` | Eligibility precedes ranking; return small typed references and materialize only permitted selected bodies. |
| Feedback and outcome evidence | `core.user_feedback_intelligence`, `core.reuse_evidence`, existing Run History | A favorable reuse score can affect ranking, not promotion. Unverified likes are not verified outcomes. |
| Optimization proposals | Practitioner self-improvement profile, `core.recovery_learning`, `core.configuration_preferences` | Produce versioned candidates or ordering proposals; do not invent eligibility or permissions. |
| Code qualification and activation | `core.code_intelligence_assets` and independent review | Exact implementation, dependencies, license, effects, tests, source digests and independent evidence remain required. |
| Hosted distribution | `core.provisioning_server` and its authorization/qualification adapters | Serve approved assets and manifests. Do not turn the subscription service into arbitrary customer-code execution. |

Loop Engine already has bounded reuse-evidence ranking and selection among
admitted context-budget variants. These are useful starting mechanisms, not
proof that a general retrieval optimizer or all-layer promotion workflow is
finished. External memory should be an imported, scoped artifact, not a new
parallel authority over active intelligence.

## First-release shortlist and gates

1. **First optimizer trial: DSPy with GEPA.** Optimize a small declared prompt
   or configuration surface around the current retriever. Keep executable
   code mutation disabled initially. Compare against the unchanged baseline.
2. **First continual-memory wrapper trial: AutoRAG2.** Use a customer-side
   sandbox, read-only corpus views, explicit memory storage, disabled automatic
   installation, and fully counted model calls. Compare memory on versus off.
3. **Component shortlist: Haystack or LlamaIndex, selected by a verified gap.**
   Choose one needed converter, reranker, or evaluator. Do not introduce both
   full frameworks as mandatory dependencies.

Add Graphiti only for demonstrated temporal requirements, or LightRAG for
demonstrated cross-document relationship requirements. Legacy AutoRAG remains
a useful offline pipeline-search comparator. Keep Agent Lightning outside
the launch dependency set until trainable-model authority, data rights, and
compute budgets exist. The research correction methods can inform bounded
query recovery without installing their entire original training stacks.

Every trial needs a frozen corpus version and three distinct populations:
optimization examples, repeatedly inspected validation examples, and an
untouched final holdout. Group related documents and near-duplicate questions
before splitting. For continuous memory, freeze the learned memory before
final evaluation and include a later-time or changed-domain holdout. A reused
holdout becomes development data, not continuing independent evidence.

Predeclare the success rule. Measure relevant-source recall, ranking quality,
supported-answer accuracy, citation correctness, and appropriate abstention.
Also measure physical model calls, embedding and indexing work, total tokens,
elapsed time, cost completeness, and privacy failures. Quality and cost are
separate objectives; fewer calls are not universally better. Compare all
methods on the same query population and report every failed or excluded run.

Bound all physical work, including reflection, grading, query rewriting,
embedding, ingestion, and repair. An optimizer's metric-call counter is not
necessarily the number of physical model calls. Share cumulative authority
across parallel workers. If an adapter cannot account for or constrain its
internal calls, declare that configuration unsupported. A timeout does not
prove a callback was physically cancelled or a write was undone.

Keep corpus access and learning permissions separate. Use tenant-scoped
memory, approved egress, retained source provenance, and deletion tests.
Do not export customer prompts, feedback, or traces to hosted observability
or training services by default. Retrieved instructions and feedback can be
poisoned. They remain data, not permission to change the evaluator or system
policy.

Promote only through a different review process bound to the exact candidate
digest and frozen evaluation record. Preserve the prior active version and
a rollback path. Repeated model self-approval, success on its own synthetic
tests, and increasing memory size do not satisfy this gate.

## Evidence limits

The comparison verifies current documented mechanisms and important version
changes. It does not audit every upstream implementation, reproduce upstream
benchmarks, or claim that a wrapper is already qualified. Before execution,
pin an exact revision and dependency manifest, review its licenses and effect
surface, and test it through Loop Engine. Current main-branch links are
discovery evidence, not immutable admission identities.
