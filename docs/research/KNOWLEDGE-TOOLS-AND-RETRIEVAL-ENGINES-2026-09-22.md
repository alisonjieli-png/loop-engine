# Knowledge tools and retrieval engines for Baltor

Kind: dated primary-source and local read-only research. Reviewed September
22, 2026. The owner asked about Obsidian, retrieval-augmented generation,
embeddings, CodeGraph, Graphify and related code graphs. These tools have
different roles in development and in the customer service. This record
does not install a dependency, change a retrieval policy, send customer
data to a model, or qualify a new backend. The [roadmap](../roadmap/roadmap.yaml)
keeps work authority: D-05 for durable records, S-6.32 for served search
and relevance floor, S-6.52 for additional measured engines.

## Runtime boundary

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

A vault view, vector, code graph, ranker and search index are passive records
or mechanics. They do not become another executable graph vertex or grant
access. Search must first apply typed tenant and item eligibility, return
small body-free references, and materialize selected bytes only after a
fresh permission and digest check. A graph edge or similarity score cannot
approve an intelligence item. The [existing search and storage boundary](../components/core-architecture/SEARCH-AND-STORAGE.md)
and [Graphify evaluation](GRAPHIFY-CODE-INTELLIGENCE-EVALUATION.md) already
explain that distinction.

## Two jobs, different tool choices

| Tool or method | Development use in this repository | Candidate customer-service use and limit |
|---|---|---|
| [Obsidian](https://obsidian.md/help/data-storage) | A human can browse a local Markdown vault with links, graph view, properties and [Bases](https://obsidian.md/help/bases). Use the repository files as the view; the generated records index and `roadmap.yaml` remain authority. Its metadata cache can be rebuilt from files. | An optional export or local note-taking destination for a customer's own research workflow, only if users ask for it. Obsidian is not the service database, a qualification gate or a new intelligence layer. The application is free to use but [proprietary](https://obsidian.md/license); do not make it a base runtime dependency. |
| Installed [CodeGraph](https://github.com/colbymchenry/codegraph) | The connected `@colbymchenry/codegraph` version 1.6.0 has indexed this checkout. A local status read reported 1,220 files, 29,077 symbols, 114,153 edges and a 6.27-gigabyte database. It can orient a developer to symbols, callers and affected paths. Verify every important answer against source and tests. | An optional local code-structure evidence producer for customer-run harnesses, if source identity, update freshness, index cost, privacy and the native adapter pass. Its graph is a derived index, never Code Intelligence authority. Local telemetry was enabled at this audit; review its [upstream telemetry policy](https://github.com/colbymchenry/codegraph/blob/main/TELEMETRY.md) before a privacy claim. No setting was changed here. |
| [Graphify](https://github.com/Graphify-Labs/graphify) | The existing [version 0.9.53 pilot](GRAPHIFY-CODE-INTELLIGENCE-EVALUATION.md) found exact source and impact lookup useful but broad free-form expansion noisy. Keep it an optional descriptive graph. | Test exact symbols and bounded relationship expansion behind Code Intelligence. Current [query-log code](https://github.com/Graphify-Labs/graphify/blob/v8/graphify/querylog.py) makes logging opt-in, and the README environment table agrees, but its privacy paragraph still describes default logging. Verify the exact installed revision and configuration. Optional semantic extraction can send documents and images to a configured model, so requalify the data route before use. |
| [Semble](https://github.com/MinishLab/semble) and [SCIP](https://github.com/scip-code/scip) | Semble is an MIT local code search candidate combining code-aware chunks, lexical ranking and a local code embedding model. SCIP provides precise definitions and references where a language indexer exists. | Compare them with CodeGraph, Graphify and plain `rg` on frozen source-navigation questions. A source index is useful for code relationships; it does not by itself select qualified reusable code or execute it. Semble's published quality figures are author-reported. |
| SQLite full-text search and [LanceDB](https://lancedb.github.io/lancedb/) | Existing local backends for exact words and hybrid experiments; no new service is required for a small catalogue. | Retain the current low-infrastructure floor. Measure latency, permission filtering and relevance at 1,000, 10,000 and 100,000 metadata cards before changing deployment shape. |
| [pgvector](https://github.com/pgvector/pgvector), [Qdrant](https://github.com/qdrant/qdrant) and [Tantivy](https://github.com/quickwit-oss/tantivy) | Candidate backends when a particular storage or lexical bottleneck has been measured. | PostgreSQL plus pgvector may fit D-05 if PostgreSQL becomes the durable authority; its documentation says filtering after an approximate index scan can reduce filtered recall. Qdrant offers filtered dense and sparse search as a separate service. Tantivy is a lexical library, not a distributed service. Each enters only behind the fixed retrieval edge after the same held-out comparison. |
| [Microsoft GraphRAG](https://github.com/microsoft/graphrag) | A source of ideas for corpus-wide themes and multi-hop explanation; its [paper](https://arxiv.org/abs/2404.16130) tests different questions from exact item lookup. | Consider only when a customer task truly needs relationship synthesis across a large permitted corpus. Its repository warns indexing may be costly and is largely in maintenance mode. Generated graph claims need source citations and remain data; no graph summary grants authority. |
| [Haystack](https://github.com/deepset-ai/haystack) and [LlamaIndex](https://github.com/run-llama/llama_index) | Parser, indexing and evaluation components may be useful in isolated experiments. Haystack now documents progressive skill discovery in its framework. | Their full agent abstractions overlap Loop Engine's own runtime and source-of-truth rules. Reuse a bounded component or compare a native skill-discovery baseline, not a parallel orchestration ontology. |

“Graphcode” did not identify one exact package. The owner asked for **all**
of the related tools, so this record includes the installed CodeGraph, the
prior Graphify review and additional source-graph candidates.

## What the current search path actually supports

The living [search-quality report](../components/intelligence-layers/SEARCH-QUALITY.md)
records 354 local test queries over 123 catalogue candidates. The selected
purpose policy improved held-back ranking against the earlier served path,
yet still returned references for all ten unanswerable requests. Its
prepared-search implementation is not the served route. A read of
[`ServiceHttp._search`](../../src/loop_engine/core/service_runtime/http.py)
at this review still shows a `Retriever(records)` built from the authorized
listing on each request. The public [capabilities response](https://app.baltor.ai/api/v1/capabilities)
reports SQLite full-text search, a deterministic character-hash vector
backend and no installed semantic embedding model. These observations make
the relevance floor and reusable tenant-scoped index concrete work for
S-6.32 before a 100,000-item catalogue claim.

The [retrieval contract](../../src/loop_engine/core/retrieval.py) already
distinguishes embedding model, revision, dimensions, normalization and
distance in `EmbeddingSpace`; vectors from different spaces must not be
compared. One source-inspection question deserves a known-wrong check:
`Model2VecBackend` loads a model without an explicit immutable revision but
sets the space revision to the literal `hf-cache-pin`. Different downloaded
model bytes could then receive the same `space_id`. This was not reproduced
as a failing live index. Pin the exact model commit or artifact digest and
require a mismatch and rebuild when it changes before a persistent semantic
index is admitted. Embeddings derived from private material remain private
derived data; an external provider call needs explicit recipient and model
authority.

## A staged retrieval comparison

Use the same permitted item population, exact grant snapshot, held-out
queries and evaluator for every eligible engine. Separate query families:
exact identifier, paraphrased purpose, source-code call or dependency,
multi-hop relationship, historical change and genuinely unanswerable need.
Measure reference relevance, false matches, abstention, selected-body use,
downstream accepted work, index build/update cost, query latency, storage,
model usage and revocation behavior.

1. Compare the current served lexical path with the typed purpose policy and
   an explicit no-result floor. A high score threshold alone is not a
   solution if it also hides valid items.
2. Add one pinned local embedding engine and one lexical-vector hybrid arm.
   Exact names should still have a lexical route; paraphrases test whether
   vectors add value. Evaluate with the project's held-back queries and a
   separate customer-like holdout. The [SkillRet](https://github.com/ThakiCloud/SKILLRET)
   and [Agent Retrieval Bench](https://github.com/eyuansu62/agent-retrieval-bench)
   evaluators are candidate external checks for retrieval only.
3. On exact code questions, compare `rg`, CodeGraph, Graphify, Semble and SCIP
   where a supported indexer exists. Require the correct source location and
   verified callers or effects, and count false edges, update lag, disk size
   and total developer time. No graph centrality score becomes a code licence
   or test result.
4. Test a graph retrieval engine only on multi-hop or corpus-wide questions
   against lexical, hybrid and direct source reading. Record every generated
   statement's source and the cost of constructing and refreshing the graph.
5. Use 100,000 synthetic **metadata cards** for a storage and concurrency
   drill, not as useful approved intelligence. Measure cold rebuild, tenant
   filtering, p95 search latency, grants changed during a request, deletion,
   memory and disk. A revoked tenant must receive no reference even when a
   shared index remains warm.

[BEIR](https://github.com/beir-cellar/beir) and [MTEB](https://docs.mteb.org/)
can screen retrieval or embedding models on their own populations. They
cannot prove that a Baltor item reached a harness or helped it finish a
customer task. The service should admit an engine only after the existing
edge's version, permissions, body-free result and independent comparison
checks pass. This record proposes no new graph store or intelligence layer.
