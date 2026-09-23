# Model-conditioned harness intelligence research

Kind: dated primary-source research and proposed materialization design.
Reviewed September 22, 2026. The owner proposed simplifying, condensing,
rewording or otherwise optimizing harness intelligence for the model that
will run a step. This is a useful configuration dimension to test, not a
claim that shorter text improves every model. The
[dimension inventory](../architecture/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md),
[intelligence rules](../../AGENTS.md), and [roadmap](../roadmap/roadmap.yaml)
remain authoritative. No derivative was generated, approved or served in
this review.

## Complete runtime classification

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

The logical intelligence item belongs to its existing persistent layer and
family. A model-specific rendering is a passive, versioned derivative body,
not another layer, family, Loop role or operational runtime type. An
Intelligence Loop can search, select and materialize it for a governed step.
The source's review does not automatically approve rewritten derivative
bytes.

## Why the idea is plausible but conditional

[Model-Adaptive Prompt Optimization](https://aclanthology.org/2023.findings-emnlp.215/)
reports that effective wording depends on the target model in its tested
tasks. [RECOMP](https://arxiv.org/abs/2310.04408) and
[LLMLingua-2](https://arxiv.org/abs/2403.12968) report useful prompt or
retrieval compression under their own populations. Conversely,
[information-preservation research](https://aclanthology.org/2025.findings-emnlp.949/)
shows why retaining apparent semantic similarity is not the same as
retaining task-critical information. These are published research results,
not Baltor measurements. [Tessl](https://docs.tessl.io/reference) already
offers model-specific evaluation and skill optimization; model adaptation
alone is not a novelty claim.

One small local model may need an ordered procedure, explicit constraints
and a worked example. Another model may follow a short checklist better.
A third may need exact source excerpts to avoid confident invention. The
objective is accepted work under the customer's quality, latency, spending
and permission constraints, not minimum words or tokens. A variant that
reduces input tokens but increases retries, cache misses or false acceptance
is worse for that task.

## Current boundary and proposed derivative record

[HarnessIntelligenceItem](../../src/loop_engine/core/harness_intelligence.py)
already names body identity, digest, source layer, family and exposure.
[ProvisioningServer](../../src/loop_engine/core/provisioning_server.py)
applies tenant/item qualification and body integrity. The
[context budget](../../src/loop_engine/core/context_budget.py) and
[context manifest](../../src/loop_engine/core/context_pack_manifest.py)
record fitting and what entered a model call. They do not presently define a
catalogue of independently qualified model-specific derivative bodies.
Their character-based token estimate is not the exact provider tokenizer
count or monetary cost. The current
[configuration dimensions](../architecture/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md)
already include context allocation, ordering, compression, model route,
skill choice, cache and fallback, so use those owning boundaries.

A proposed `model_conditioned_intelligence_variant/v1` passive record needs:

| Field group | Exact content and refusal |
|---|---|
| Parent identity | One logical approved source item, exact body digest, provenance, licence state, source revision and family. Unknown or withdrawn parent refuses. |
| Derivative identity | New body digest and size, renderer engine/version/configuration, producer, transformation kind and exact output artifact. A rewritten body cannot reuse the parent's approval digest. |
| Transformation | Exact formatting, selected original spans, simplified wording, condensed wording, reworded wording, expanded examples or translation. A changed executable script is a new Code Intelligence asset with its own effects and tests, not a text-only variant. |
| Target scope | Provider, exact resolved model revision or weight digest where known, tokenizer and chat-template identity, native harness version/layout, task region, language and tested context-budget interval. An opaque model alias gives a weaker qualification, not an invented exact revision. |
| Protected obligations | Numbers, limits, negations, safety requirements, permissions, commands, paths, schemas, dependencies, exceptions, citations and required files that must survive. The obligation inventory itself requires independent review. |
| Review and outcome | Candidate/approved/withdrawn status, independent exact-byte reviewer, task population, evaluator, failures, cost accounting and invalidation triggers. A model-generated derivative stays candidate until a different governed process approves it. |

The derivative may be stored once and rendered into several harness-native
packages. A physical file, model rendering and logical intelligence item
have different counts. For illustration, 100,000 logical methods with ten
model or harness renderings each make one million files but still only
100,000 source methods, with each derivative requiring its own qualification
or an explicitly proven carry rule. Generating a full cross-product would
create review burden without evidence of demand; begin with model/task cells
that customers actually use.

## Three different ways to change material

| Materialization choice | Authority and review consequence |
|---|---|
| Select approved source spans or sections | Preserve exact authored bytes and source coordinates. The selection policy and omitted obligations still need evaluation; an extractive view can lose a decisive exception. Keep full source available by authorized reference. |
| Compile a deterministic format from tagged approved sections | A fixed renderer can change order, headings or native layout with reproducible bytes. Its compatibility and semantic-retention checks are part of qualification; do not treat generated output as the approved parent automatically. |
| Generate new simplified, condensed or reworded text | Each output is a new candidate with rights, provenance, exact digest and independent review. A just-in-time model summary used inside one authorized run is provisional run material, not approved public catalogue intelligence. |

[Agent Skills](https://agentskills.io/specification) load the full `SKILL.md`
body on activation while references and other files can be loaded later.
Moving critical clauses from the body into a reference changes what the
model initially sees. A rendered variant must pass native format and file
size checks and record which bytes the native harness actually loaded.
Keep the text content variant separate from the provider's chat message
serialization: [Hugging Face chat templates](https://huggingface.co/docs/transformers/chat_templating_writing)
and [Ollama Modelfiles](https://docs.ollama.com/modelfile) show that exact
model templates can alter framing and tokenization even when the skill text
is unchanged.

## Select a model and material together

Choosing a model can depend on context size, but the eligible material
variant depends on the model. Resolve that pair under one typed decision:

1. Start with the step's input/output contract, authority, task category and
   quality floor. Search **logical** approved items and return small
   references, not every derivative body.
2. Form a bounded shortlist of eligible model routes and material variants.
   Hard-filter parent approval, derivative approval, tenant grant, rights,
   model revision, native layout, context capacity, recipients and spending.
3. Rank only eligible route/variant pairs using declared initial order and
   saved accepted-task evidence. Pin the selected pair and exact context
   manifest before a physical model call.
4. If a model route fails or changes, re-evaluate derivative eligibility,
   tokenizer/context fit, cache state and remaining authority. Do not carry
   a variant to another route because its friendly model name looks alike.
5. If no qualified derivative exists, use the approved canonical source if
   it fits. Otherwise select permitted original references, split the step
   under the existing Loop rules or return an explicit unavailable result.
   Never silently truncate a required safety or permission clause.

For a multi-model strategy, each physical member may receive a separately
eligible variant of the same source item, with its own manifest and digest.
The shared cumulative allowance still counts generation, comparison,
repair, judge and losing-candidate calls. A model-specific rewrite cannot
grant another model, network recipient, tool or effect.

Caching can reverse an apparent saving. A shorter variant whose prefix
changes each run may cost more than a longer stable prefix. The
[Anthropic prompt-caching guide](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
ties reuse to matching content; the exact provider's cache behavior must be
measured. Include variant generation and review cost, cold and warm model
calls, provider-reported input/output/cache usage, complete latency and
accepted work. Missing usage or local electricity cost stays unknown.

## Experiment and known-wrong cases

Freeze task population, source versions, model routes, harness versions,
budgets, permitted effects and independent evaluator before selecting a
variant. For each target model compare: no item, raw source, approved
canonical item, extractive view, condensed view, simplified wording,
reworded wording and expanded example. Test at least one small local model
and one larger model separately; do not transfer a winner across them by
assumption. Vary additions as well as removals. Report accepted tasks,
false acceptance, refusal, repair, tokens, cache reads/writes, cost state,
latency and excluded runs. [SkillsBench](https://arxiv.org/abs/2602.12670)
and [skill-retrieval research](https://arxiv.org/abs/2604.04323) reinforce
that skill usefulness depends on task fit and retrieval; their results are
not direct evidence for these Baltor variants.

Named negative checks must detect:

- A shortened variant drops `no network`, a spending ceiling, approval
  condition, path, schema field, source citation or exception.
- A rewording reverses a negation or turns an example into an instruction.
- A native package passes text lint but breaks a relative reference or its
  harness's size limit.
- A changed model alias, weight digest, tokenizer or chat template retains
  an old variant qualification.
- A fallback route reuses another model's variant without revalidation.
- A candidate derivative inherits parent approval or tenant access, or its
  rendered files inflate the count of distinct approved methods.
- An item reduces prompt tokens but lowers held-out task acceptance,
  increases retries or loses cache benefit, yet is ranked as cheaper.

S-6.40 can produce source-grounded derivative **candidates**; S-6.45 owns
admission and native-package checks; S-6.32 owns logical search; S-6.52
owns retrieval-engine comparisons; S-6.60 owns model-call strategy; D-05
owns durable exact bodies; D-07 to D-09 own benefit evidence. Claude Code
should decide whether a derivative selector fits an existing materialization
edge or needs a new engine behind it. The first implementation slice should
be an exact source-span or deterministic-format candidate with a check that
removing one protected obligation makes it fail, before model-generated
rewording or million-file rendering.
