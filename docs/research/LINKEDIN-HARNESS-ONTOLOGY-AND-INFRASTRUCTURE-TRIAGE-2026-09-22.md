# Harness, ontology, and infrastructure source triage

Kind: dated source review of the user's André Lindenberg activity excerpt
and additional public newsletter links. Reviewed September 22, 2026.
The [activity listing](https://www.linkedin.com/in/alindnbrg/recent-activity/all/)
returned a rate limit or login gate to the available fetchers. Thirty
distinct technical items were present in the user's pasted feed, and nine
additional older newsletters were publicly readable. Known individual post
URLs were readable, but this is **39 visible artifacts**, not an exhaustive
history of that profile. The social summaries are discovery leads. The
upstream repositories, specifications and papers linked below are the
technical sources; their speed, scale and task scores are usually author
claims, not reproduced Baltor results.

The [roadmap](../roadmap/roadmap.yaml) is the task authority. This review
does not install, fork, license, benchmark or qualify any candidate. It
extends the earlier [harness market comparison](FRONTIER-HARNESS-POSITIONING-AND-EXPERIMENTS-2026-09-22.md),
[knowledge-tool review](KNOWLEDGE-TOOLS-AND-RETRIEVAL-ENGINES-2026-09-22.md)
and [SoL-Pi study](SOL-PI-HARNESS-REVIEW-2026-09-19.md).

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

A container, micro virtual machine, WebAssembly cell, provider proxy,
worktree, graph index, proof checker and native harness remain mechanics or
adapters of a classified Loop. An upstream project's own use of “node” does
not add a Loop Engine runtime class.

## One harness per step has several independent compartments

The existing [dimension inventory](../architecture/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md)
already separates harness implementation, workspace, state, provider,
credentials, caching, resources and effects. A fresh harness process should
therefore not be mistaken for a fresh filesystem, model server or dependency
installation. A useful configuration record needs to state all of these:

```text
One Loop-owned focused step
├── Cognitive context: exact instructions, selected material, fresh transcript
├── Native harness: binary, version, fresh process and supported controls
├── Runtime image: pinned software and read-only dependency cache
├── Writable task view: scoped files, source, outputs and retention policy
├── Model endpoint: customer-owned route, model identity and capacity
├── Credential and tool bridge: host-held secrets, per-step grants and effects
├── Isolation substrate: process, container, WebAssembly or micro virtual machine
├── Resource envelope: calls, tokens, time, memory, disk and concurrency
└── Evidence: actual loading, calls, effects, evaluation and Run History
```

A prewarmed **clean runtime image** can save dependency and boot cost while
still starting a fresh harness process with no previous transcript, tenant
secret, writable task state or consumed authority. Forking a live agent or
restoring its process memory deliberately carries more state and must be a
separate, opt-in configuration with a different isolation claim. The current
[Bubblewrap harness path](../../src/loop_engine/core/harness_process.py)
already clears the inherited environment and brokers text model calls, but
native tools and observed loading by a qualified third-party harness are
unavailable. A local fixture has read a supplied instruction file. The
[Docker workspace backend](../../src/loop_engine/core/workspace_optional.py)
confines commands; it is not the native harness executor. The
[brokered container embodiment](../../embodiments/brokered_container/README.md)
remains planned. These current states cannot be described as a qualified
container-per-step native harness.

A [bounded local retention check](../verification/CONFINED-HARNESS-PRIVATE-LAUNCH-RETENTION-2026-09-22.md)
found that a successful confined run leaves its private `task.txt` and
`config.json` in a run directory after return. This may be intended for
task continuity, but its retention scope is not yet explicit. A fresh
process therefore does not prove private launch files were cleared. The
current Bubblewrap launcher also lacks a process memory or writable-disk
quota; the Docker command workspace's resource flags do not automatically
apply to harness processes.

## All thirty pasted activity items

Priority is a research order, not an adoption or qualification decision.
“Compare” means the smallest controlled test should be run only under the
existing owner and authority boundary. Direct original post URLs were
recoverable for 26 of the 30 pasted entries; links to the author's
[public newsletter](https://www.linkedin.com/pulse/laws-instead-diffs-andr%C3%A9-lindenberg-wxlmf)
and profile helped locate them. The four without a recovered original post
are still included from the user's supplied text.

| Priority | Upstream source from pasted item | Baltor use or limit |
|---|---|---|
| A | [codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp), [v0.11.0](https://github.com/DeusData/codebase-memory-mcp/releases/tag/v0.11.0) | Compare bounded code-graph indexing and exact-source queries with CodeGraph, Graphify, SCIP and `rg`. The kernel graph and 40 to 80 percent memory claims are upstream measurements; no approved Code Intelligence follows from an index. |
| A | [Foremerge](https://github.com/naw103/foremerge) | Compare early symbol-intent collision warnings with existing Git worktree practice. Its own limitations call conflicts advisory; the pasted 98-agent zero-miss figure lacks a published upstream benchmark. Do not make it a lock or second task authority. |
| A | [whip](https://github.com/context-labs/whip) | Candidate native harness executor. Test fresh process, exact files, model relay, tool approval, auto-loaded repository configurations and secret isolation. Live catalog discovery does not qualify a route. |
| A | [IWE](https://github.com/iwe-org/iwe) | Compare declared edit impact, schema refusal and orphan/dangling-link repair at the existing documentation and managed-record boundaries. Do not install a parallel note store. |
| A | [Operational Ontology](https://github.com/gura105/operational-ontology) | Adopt the invariant of named actions with typed preconditions, actor-scoped reads and audited refusals through existing effect and semantic execution contracts. No new Loop runtime is needed. |
| A | [Jev Ultrafast](https://github.com/browser-use/jev-ultrafast) | Bounded TypeSafe Jev browser-action candidate. Its 7.1-second result used one flight-search task with three repeats per arm and no booking. Test target freshness, denied effects and independent completion across sites. |
| A | [MemOS](https://github.com/MemTensor/MemOS) | Compare retrieval and experience-to-skill candidate generation. A successful trace cannot self-promote code or instructions into Baltor's active intelligence. |
| A | [Pipelock](https://github.com/luckyPipewrench/pipelock) | Candidate mediated egress and tool inspection under the existing effect boundary. Its Apache core is distinct from Elastic License 2.0 multi-agent identity and budgets; direct egress bypass must be tested. A signed boundary record proves that mediator's decision, not complete safety. |
| A | [Kubernetes Agent Sandbox](https://github.com/kubernetes-sigs/agent-sandbox) | Candidate later cluster substrate with Sandbox, Claim and WarmPool; configured RuntimeClass supplies isolation. Warm-start figures are author reported, and dynamic identity/network policy remain a qualification question. It is not needed for a local invited beta. |
| A | [Caura](https://github.com/caura-ai/caura) | Direct multi-agent memory competitor. Its [case study](https://caura.ai/use-cases/etoro-company-brain/) reports 291 distinct agent identifiers, more than 26,500 memories and 23-millisecond median **search**; full recall is slower in its [architecture account](https://caura.ai/blog/harness-engineering-deterministic-memory/). Compare corrected-fact ranking and full accepted tasks. |
| A | [Prime Agent](https://github.com/PrimeIntellect-ai/prime-agent) | Study live sibling-agent messaging and durable work as a coordination option under existing Loop relationships and Run History. Messaging is not an effect grant or process sandbox. |
| A | [SoL-Pi](https://github.com/NVlabs/SoL-Pi) | Already studied as an opt-in Pi extension. Compare its four mechanisms one at a time; the [paper](https://arxiv.org/html/2609.20519v1) reports lower cost with lower aggregate accepted score on some arms. |
| A | [Worktrunk](https://github.com/max-sixty/worktrunk) | Development worktree helper, not a customer harness. Its [copy-ignored behavior](https://worktrunk.dev/step/#copy-on-write) can copy ignored secrets; test cache reuse only with an explicit file allowlist in disposable repos. |
| A | [Microsoft tgrep](https://github.com/microsoft/tgrep) | Compare repeated exact text search in very large repositories with `rg`, including cold index build and updates. Its published gecko-dev speed comparison prebuilt the index; it is not semantic relevance. |
| B | [kimi-k3-in-c](https://github.com/FareedKhan-dev/kimi-k3-in-c) | Watch as a model endpoint candidate. The engine code is Apache-2.0 but the weights have a separate [model licence](https://huggingface.co/moonshotai/Kimi-K3/blob/main/LICENSE). Its 1.56-terabyte checkpoint remains disk streamed even with more random-access memory. The reported 8.24 decimal-gigabyte peak was measured under an 8-gibibyte control-group limit on a high-memory machine, not an 8-gigabyte laptop. One author-reported 26.5-second-per-token setting would take about 7.4 hours for 1,000 generated tokens before prefill; other settings differ. This does not prove useful overnight coding. |
| B | [Bend 2](https://github.com/bendlang/bend) | Optional formal verifier for code written in that language, distinct from [older Bend/HVM](https://github.com/HigherOrderCO/bend). A passing proof covers stated laws under its assumptions; weak specifications and `@unsafe` can still hide errors. Test a broken law, vacuous implementation and unsafe path before treating it as Code Intelligence evidence. |
| B | [OntoKG-EQ](https://arxiv.org/html/2609.08869) | Question-bounded graph with per-answer provenance. Its SQL baseline gives the same numerical analytics; the graph adds governance and traceability. Test exact source resolution and unsupported-question refusal before adding graph complexity. |
| B | [HelixDB](https://github.com/HelixDB/helix-db) | Candidate graph/vector/full-text storage engine for a measured retrieval bottleneck. Its current [licence](https://github.com/HelixDB/helix-db/blob/main/LICENSE) is Apache-2.0; an older search snapshot said otherwise. Test tenant filtering, transactional updates, p95, build cost and single-writer behavior against existing storage. |
| B | [EvoOntology](https://github.com/ruc-datalab/EvoOntology) | Compare candidate semantic-layer evolution on frozen data tasks. The BIRD 63.6 to 72.4 execution-accuracy figure is the authors' four-backbone subset, not a Baltor result. Generated semantics stay candidates. |
| B | [SLayer](https://github.com/MotleyAI/slayer) | Embedded reusable data metrics and generated queries. Its current README claims row-level security; this review did not qualify the exact access controls. Require wrong-join and unauthorized-field tests before customer data. |
| B | [Symbolic Separation paper](https://arxiv.org/abs/2609.17107) | Relationship-constrained agent answers in one supercomputer telemetry setting. Test graph-valid and intentionally false relations under identical inputs; do not transfer the paper's headline score to other domains. |
| B | [Oxigraph](https://github.com/oxigraph/oxigraph) | RDF and SPARQL library; compare only if a real interoperability task requires it. Canonical graph bytes prove representation identity, not factual truth. |
| B | [Cartography](https://github.com/cartography-cncf/cartography) | Cloud and identity metadata graph, potentially useful for customer-owned credential inventory. Its key graph represents metadata, not secret values; never ingest raw credentials into Baltor intelligence. |
| B | [SSTorytime](https://github.com/markburgess/SSTorytime) | Temporal story graph and separate protocol proxy. Watch against existing temporal-fact records; need a customer query that beats that simpler baseline. |
| B | [forkd](https://github.com/deeplethe/forkd) | Experimental Firecracker live-branch substrate requiring Linux/KVM and a modified dependency. Its 56-millisecond figure is a source-pause median, not complete new-harness startup. A live branch carries state; test a clean prewarmed image separately. |
| B | [LPG Modeler](https://github.com/Volland/lpg-modeler) | One graph model rendered to graph constraints, shapes and schema. Compare on a real governed relationship where generated targets reject the same bad edge; inspect licence/version before use. |
| B | [Ontology Atlas](https://github.com/wlsdks/ontology-atlas) | Git-versioned architecture map. Use as a derived developer view and compare impact answers against `architecture.yaml` and source; never make it a second authority. |
| B | [Ephemora Cell](https://github.com/MichaelS1011/ephemora-cell) | Wasmtime capability cell for narrow generated-tool execution. Author sub-millisecond calls and Docker cold starts are different workloads. Test function parity, denied filesystem/network, fuel, memory, cancellation and output before considering a workspace or plugin engine. |
| C | [Upscayl](https://github.com/upscayl/upscayl) | Local image upscaling may help a specific image task but has little direct relevance to harness selection, intelligence admission or the current launch path. Keep outside core architecture. |
| C | [Laws Instead of Diffs newsletter](https://www.linkedin.com/pulse/laws-instead-diffs-andr%C3%A9-lindenberg-wxlmf) | Editorial synthesis of Bend's proof idea and limits. Use the upstream Bend source for implementation decisions, not the newsletter's interpretation. |

## Additional sources from nine public newsletters

| Primary source | Reason to inspect; no qualification claim |
|---|---|
| [HarnessRouter](https://harnessrouter.ai/), [Community Edition](https://github.com/HarnessRouter/harnessrouter) and [Unified Harness Protocol](https://unifiedharnessprotocol.org/) | The closest newly found executor competitor. The Apache-2.0 self-hosted edition runs several harnesses behind one API, with separate operating-system users and workspaces per session inside one container. Hosted Cloud says one sandbox per **product task**. Neither establishes a fresh process per focused internal step. The draft 2026-09-12 protocol covers discovery, versioning, task lifecycle, plugins, sessions, files and streaming with 75 advertised conformance checks. Compare as a future external executor adapter and possible interoperability partner; the protocol's conformance suite does not supply Loop Engine authority or independent acceptance. |
| [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) and [Cordis](https://github.com/cordiverse/cordis) | Developer-preview everything-is-a-plugin harness with breaking changes expected. Inspect exact composition and lifecycle contracts before considering it as an engine; its plugin language does not override Loop Engine's single operational runtime. |
| [Google SAM](https://github.com/google/sam), [OpenConnector](https://github.com/oomol-lab/open-connector), [IBM ContextForge](https://github.com/IBM/mcp-context-forge) | Distributed identity and customer-side credential/tool gateway references for S-6.61. Google SAM's README says it is not an officially supported Google product. Compare step-scoped delegation, audience, revocation, direct/relay links and typed effect authority; do not install a second credentials source of truth. |
| [OpenViking](https://github.com/volcengine/OpenViking) and [HydraDB](https://github.com/hydra-db/hydradb) | Summary-first virtual knowledge filesystem and object-storage graph ideas. Both surfaced under AGPL-3.0 in this source review; use design ideas only until rights and a measured retrieval gap justify an engine. |
| [Utopia](https://github.com/deeplethe/utopia), [Procedural Graphs paper](https://arxiv.org/abs/2609.09153), [Semantica](https://github.com/semantica-agi/semantica) | Bitemporal correction, candidate procedure evolution and decision/provenance graph ideas. Map to current temporal facts, candidate-only self-improvement and Run History rather than another live memory or graph authority. |
| [Specula](https://arxiv.org/abs/2607.25333) and [SysMoBench](https://arxiv.org/abs/2509.23130) | Formal-specification and implementation-conformance evaluation. Test whether an attractive formal property actually matches executable code; a proof over a wrong specification must not approve a task. |
| [OrcaReplay](https://github.com/Continuum-AI-Corp/OrcaReplay) and [CCCC](https://github.com/ChesterRa/cccc) | Replay/forked call inspection and separate delivered/read/replied coordination facts. Compare with existing Run History and agent messaging before introducing another record system. |

The [Y Combinator launch page](https://www.ycombinator.com/launches/RpL-harnessrouter-bring-the-world-s-best-ai-agents-into-your-app-with-one-api)
is published under [Epsilla's company profile](https://www.ycombinator.com/companies/epsilla).
Describe that relationship precisely; it is not proof that HarnessRouter
entered a separate Y Combinator batch. HarnessRouter's own
[pricing page](https://harnessrouter.ai/pricing) separates agent-work
minutes, memory and model usage. Its zero-dollar tier lists 30 active
agent-work minutes; a customer-owned model key can still incur separate
provider charges.

## Public activity coverage register

These are the nine additional newsletter issues visible from the public
profile, beyond the 30 pasted feed items. Their summaries led to the
additional sources above; they do not make the blocked full activity list
complete.

| Issue date | Public newsletter |
|---|---|
| September 12 | [The Graph Doesn't Need RAM Anymore](https://www.linkedin.com/pulse/graph-doesnt-need-ram-anymore-andr%C3%A9-lindenberg-kqwde) |
| September 5 | [The Change of Mind Is Information](https://www.linkedin.com/pulse/change-mind-information-andr%C3%A9-lindenberg-uvcue) |
| August 29 | [Audit the Auditor](https://www.linkedin.com/pulse/audit-auditor-andr%C3%A9-lindenberg-odvfe) |
| August 22 | [From City Blocks to Agent Memory](https://www.linkedin.com/pulse/from-city-blocks-agent-memory-andr%C3%A9-lindenberg-8b5ie) |
| August 15 | [Everything Is a Plugin, Proven](https://www.linkedin.com/pulse/everything-plugin-proven-andr%C3%A9-lindenberg-gamle) |
| August 8 | [The Most Expensive Rung on the Ladder](https://www.linkedin.com/pulse/most-expensive-rung-ladder-andr%C3%A9-lindenberg-l2oqe) |
| August 1 | [The Half We Don't Budget For](https://www.linkedin.com/pulse/half-we-dont-budget-andr%C3%A9-lindenberg-pinxe) |
| July 25 | [From Loops to Graphs](https://www.linkedin.com/pulse/from-loops-graphs-andr%C3%A9-lindenberg-m8jae) |
| July 18 | [More Machines, Slower Model, Still Worth It](https://www.linkedin.com/pulse/more-machines-slower-model-still-worth-andr%C3%A9-lindenberg-isufe) |

The following original post links were recovered for 26 pasted entries.
The original post URLs for kimi-k3-in-c, codebase-memory-mcp, the symbolic
separation paper and Oxigraph were not recovered from the accessible
profile and newsletters; the user's pasted text remains the observation
for those four, with their upstream sources checked separately.

| Pasted item | Original public post |
|---|---|
| Upscayl | [post](https://www.linkedin.com/posts/alindnbrg_opensource-ai-foss-activity-7507923450863394817-sq2o) |
| Foremerge | [post](https://www.linkedin.com/posts/alindnbrg_aiagents-codingagents-agentinfrastructure-activity-7507875988534587392-lvy0) |
| whip | [post](https://www.linkedin.com/posts/alindnbrg_aiagents-codingagents-opensource-activity-7507723486065319936-hlkl) |
| IWE | [post](https://www.linkedin.com/posts/alindnbrg_agentmemory-knowledgegraphs-opensource-activity-7507538087498002435-F29L) |
| Operational Ontology | [post](https://www.linkedin.com/posts/alindnbrg_aiagents-ontology-mcp-activity-7507365873507201024-L3Dj) |
| Laws Instead of Diffs share | [post](https://www.linkedin.com/posts/alindnbrg_laws-instead-of-diffs-activity-7507200605527035904-9Kam) |
| Bend 2 | [post](https://www.linkedin.com/posts/alindnbrg_agentharness-codingagents-formalverification-activity-7507075563002687488-sdOm) |
| OntoKG-EQ | [post](https://www.linkedin.com/posts/alindnbrg_knowledgegraphs-ontologyengineering-shacl-activity-7506979785781243904--Ra8) |
| Jev Ultrafast | [post](https://www.linkedin.com/posts/alindnbrg_aiagents-browserautomation-agentengineering-activity-7506680606945239040-vnnZ) |
| HelixDB | [post](https://www.linkedin.com/posts/alindnbrg_graphdatabase-vectordatabase-rag-activity-7506614786382712832-srRz) |
| EvoOntology | [post](https://www.linkedin.com/posts/alindnbrg_aiagents-knowledgegraphs-ontology-activity-7506451164108976128-ezAz) |
| SLayer | [post](https://www.linkedin.com/posts/alindnbrg_semanticlayer-aiagents-dataengineering-activity-7506284217618673664-YQx-) |
| Cartography | [post](https://www.linkedin.com/posts/alindnbrg_aiagents-cloudsecurity-knowledgegraph-activity-7506033309257269248-9e0f) |
| SSTorytime | [post](https://www.linkedin.com/posts/alindnbrg_knowledgegraphs-graphdatabase-ontology-activity-7505948501722365952-G4Bz) |
| forkd | [post](https://www.linkedin.com/posts/alindnbrg_agentharness-codingagents-aiinfra-activity-7505921131686641664-uN03) |
| LPG Modeler | [post](https://www.linkedin.com/posts/alindnbrg_knowledgegraphs-ontology-graphdatabase-activity-7505759956714000384-BqSh) |
| tgrep | [post](https://www.linkedin.com/posts/alindnbrg_aiagents-developertools-codesearch-activity-7505731472545325057-vcYp) |
| MemOS | [post](https://www.linkedin.com/posts/alindnbrg_agentmemory-aiagents-mcp-activity-7505602882403041282-5UIA) |
| Pipelock | [post](https://www.linkedin.com/posts/alindnbrg_aiagents-mcp-agentsecurity-activity-7505527995026223104-rq5Y) |
| Kubernetes Agent Sandbox | [post](https://www.linkedin.com/posts/alindnbrg_kubernetes-aiagents-agentsandbox-activity-7505397228941774848-SIB7) |
| Ontology Atlas | [post](https://www.linkedin.com/posts/alindnbrg_aiagents-ontology-knowledgegraphs-activity-7505302005746307072-KG8n) |
| Caura | [post](https://www.linkedin.com/posts/alindnbrg_aiagents-agentmemory-mcp-activity-7505227128028889088-Hxx8) |
| Prime Agent | [post](https://www.linkedin.com/posts/alindnbrg_codingagents-multiagentsystems-agentorchestration-activity-7505023650471890944-3NPi) |
| Ephemora Cell | [post](https://www.linkedin.com/posts/alindnbrg_aiagents-mcp-wasm-activity-7504973494963658753-3vZt) |
| SoL-Pi | [post](https://www.linkedin.com/posts/alindnbrg_aiagents-agentengineering-codingagents-activity-7504862800700399617-4-8v) |
| Worktrunk | [post](https://www.linkedin.com/posts/alindnbrg_aiagents-developertools-aiengineering-activity-7504824816475217920-E7qu) |

## Comparison campaigns mapped to existing boundaries

1. **Executor and substrate, D-07-T04 and S-6.31.** Freeze one real task,
   model, permitted tools, selected material and independent evaluator.
   Compare the current confined process, a clean prewarmed dependency image,
   a container-per-step candidate and a micro virtual machine candidate
   only when each can execute the same harness. Track cold/warm p50 and p95,
   peak memory/disk, startup and cache cost, all physical model calls,
   cancellation and accepted work. Cross-step prompt, file, credential,
   socket and authority canaries are hard eligibility checks before ranking
   cost. A live forked process belongs in a separate state-continuity arm.
2. **Exact source and retrieval, S-6.32 and D-05.** Compare `rg`, tgrep,
   CodeGraph, codebase-memory-mcp and current lexical search on frozen
   source-navigation and no-answer questions, including index build/update
   cost, permission filters, exact source spans and false graph edges.
   Compare HelixDB only after a query need justifies graph/vector storage.
3. **Typed action and proof, existing effect/verification boundaries.** Use
   Operational Ontology preconditions, Bend laws and Specula's
   implementation check as test-design references. Include a wrong actor,
   changed state, missing rule, vacuous proof and uncertain external write.
   A formal proof or mediator decision never replaces independent task
   acceptance.
4. **Memory and generated procedure, S-6.40, S-6.41 and four intelligence layers.**
   Compare MemOS, Caura, IWE and EvoOntology on corrected facts,
   contradictory sources, source deletion, scope leakage and later-task
   reuse. Their generated skills stay candidate-only until a different
   process qualifies exact bytes.
5. **Developer workflow, not customer runtime.** Compare Foremerge and
   Worktrunk on disposable concurrent worktrees with true/false collision
   labels, setup time and disk use. Require an allowlist for shared caches;
   `copy-ignored` without one can copy repository secrets into sibling
   worktrees. Do not promote a helpful worktree tool into a new Loop type.

## Research procedure that can repeat

For each new post or release, keep the original URL and observation time;
resolve its upstream repository, paper and exact revision; check licence
for the code **and** any model weights or data; record the author-claimed
population and denominator; map the useful mechanism to an existing owner;
define a matched positive case and a known-wrong case; then mark it a
candidate, comparison result, qualified engine or rejected option. The
existing [source watcher](../../tools/refresh_research_sources.py) can
recheck public primary URLs, but LinkedIn's activity listing is not a
reliable unauthenticated feed in this environment. A future complete
profile audit would need an authorized export or a supplied list of post
URLs. Do not scrape private messages, infer a source's rights from a social
post, or automatically install material because its repository is popular.

Two versioned primary-source manifests make this part repeatable:
[execution sources](LINKEDIN-EXECUTION-SOURCE-WATCH-2026-09-22.json) and
[intelligence sources](LINKEDIN-INTELLIGENCE-SOURCE-WATCH-2026-09-22.json),
15 sources each. Offline validation and the first bounded online read of
each manifest returned zero failures. The saved
[execution observation](../../artifacts/research-source-watch/RESEARCH-SOURCE-WATCH-2026-09-23T001630.642317Z.json)
and [intelligence observation](../../artifacts/research-source-watch/RESEARCH-SOURCE-WATCH-2026-09-23T001641.991613Z.json)
record exact source revisions or page hashes, not adopted claims. A repeat
[execution observation](../../artifacts/research-source-watch/RESEARCH-SOURCE-WATCH-2026-09-23T001655.297486Z.json)
found ten unchanged revisions and five HTTP 403 failures. The five are
unknown, not unchanged; the read-only watcher preserves that failure for
resumption after its upstream request allowance clears. It does not check
licence changes or semantic source quality automatically.

Two corrections from the pasted summaries deserve retention. The
[Foremerge documentation](https://github.com/naw103/foremerge) does not
publish the cited 98-agent zero-miss benchmark. The
[RubyGems incident update](https://blog.rubygems.org/2026/09/11/update-may-spam-publishing-campaign.html)
does not establish that OpenAI agents created or published its malicious
packages or that key theft succeeded. Neither claim should enter a Baltor
comparison as observed fact.
