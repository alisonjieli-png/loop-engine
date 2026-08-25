# Intelligence Retrieval Plan - the swappable plug and the scale ladder

> Historical retrieval design record. The current release provides one
> Retrieval Engine with a fixed selectable set of built-in backends. It does
> not provide external retrieval plugin registration.

Status: historical design input.
Date: 2026-08-24. Owner question answered here: "is there truly an
off-the-shelf search/RAG/hybrid system we can encapsulate into a plug
and swap later - and how does this scale to billions?"

## 1. The short answer

**No single off-the-shelf system covers the whole portfolio, and that
is fine - the plug is ours, the engines are theirs.** Every serious
2026 system (LanceDB, Qdrant, txtai, Vespa, Milvus, OpenSearch,
turbopuffer) covers lexical + vector + hybrid + filters, several add
reranking; none ships typed contracts, structural code search, or the
compiler/test admission gate. So the durable asset is the CONTRACT in
`static_architecture/retrieval.py` - `backend_handshakes()`,
`EmbeddingSpace`, `require_same_space()`, and the constructor-name swap
form the plug. Engines are commodity backends behind it, adopted one tournament
at a time. This is executable today: five backends declare handshakes;
unknown names refuse; missing extras error explicitly.

## 2. The three laws (all enforced in code)

1. **Reference, not body.** The index holds cards: identity, typed
   edges, descriptions, tags, embeddings, and a FILE REFERENCE. Search
   returns a handle; loading the Code Intelligence body or run body is a separate,
   digest-verified materialization step (`store_serve` owns it). Every
   backend handshake carries `bodies_never_in_index: true`.
2. **Embedding-space identity.** A space = model + revision + dims +
   normalization + distance, content-addressed (`space_id`). Vectors
   from different spaces are never compared - `require_same_space`
   fails closed. This is what makes "embedding models get better over
   time" and "we may train our own" safe: a new model is a new space
   and an explicit reindex, never silent mixing. Matryoshka-truncation
   (progressively shorter prefixes of one embedding) is the recognized
   exception a future space may declare, because truncation avoids
   re-embedding ([production practice, 2026](https://tianpan.co/blog/2026-04-09-embedding-models-production-versioning-index-drift)).
3. **Evidence-gated adoption.** A backend joins the registry only by
   winning frozen-query tournaments on OUR data (evidence record:
   `evidence/retrieval-engine-tournament-20260823.json`, rounds 1-3).

## 3. The deployment floor and the scale ladder

Same contract at every rung; only the backend changes.

| Rung | Backend | Scale | Trigger to climb |
|---|---|---|---|
| 0 - files | JSONL loaded in memory (`store` idf / `hash`) | thousands | none needed - the zero-infrastructure floor every user gets from `pip install` |
| 1 - embedded | SQLite FTS5; **LanceDB** (`search` extra) | hundreds of thousands → tens of millions | **measured 2026-08-24 on this workstation, 250K real-grammar records: embed 6.1s (41K rec/s CPU), ingest 4.8s, FTS index 1.8s, IVF-PQ index 15.2s, disk 296MB; queries p50 = FTS 5ms · vector 5ms · hybrid 7ms · vector+blocking-key filter 13ms** (~1.2GB/M records ⇒ 10M ≈ 12GB, still one machine) |
| 2 - service | Qdrant (verified: the SAME client API runs embedded `:memory:` with no server - dev/prod continuity) or OpenSearch | hundreds of millions | corpus outgrows one machine, or multi-writer/multi-tenant needs |
| 3 - billions | Vespa (one engine: lexical + tensors + phased ONNX reranking in-pipeline), Milvus/DiskANN (on-disk ANN built for beyond-RAM corpora), or turbopuffer (object-storage-native; 2.5T documents in production at ~$0.30/M vectors/month) | billions → trillions | the SaaS library at full scale; also when storage cost dominates (object-storage tier is ~10× cheaper) |

**Blocking keys** are already the facet grammar: layer
(string/code/past-run), category, modality, maturity become hard
prefilters before any vector work - measured at rung 1 (the 13ms
filtered query) and native at every higher rung (payload filters /
structured fields).

## 4. Multi-representation records

One record, many searchable channels - never one concatenated blob:
raw text · human description · LLM-generated description · LLM tags ·
embedding of text · embedding of description · blocking keys · typed
edges. Each channel is a field the backend indexes separately; the
tournament decides which channels earn their storage (the
field-ablation rule). LLM-generated tags/descriptions are candidates
with provenance like any other generated String.

## 5. The LLM-assisted layer (opt-in stages, not a product)

Query rewriting, HyDE (embed a hypothetical answer instead of the
query), LLM rerankers (RankLLM-style), and GraphRAG-style relationship
expansion are stages a Loop may add. Each executable stage is a Loop with a mode
(the rewrite step is model-backed; the rerank may be a local
cross-encoder), budgeted and evidence recorded like any semantic call. None of
them is the retrieval core; all are measured against the no-assist
baseline before adoption. Local rerankers verified available for the
tournament queue: FlashRank (CPU), mxbai-rerank-large-v2 and
Qwen3-Reranker (Apache-2.0), behind the `rerankers` one-interface
package.

## 6. What was evaluated and where it landed

- **Adopted now:** LanceDB (lexical won round 2; native hybrid held
  where naive RRF degraded); FTS5 (zero-dep floor); model2vec (local
  embeddings, tournament round 1); embedded Qdrant verified as the
  rung-2 path.
- **Integrated all-in-one considered:** txtai - closest single system
  (sparse+dense+graph+SQL+RAG pipelines), but framework-shaped: its
  pipelines/orchestration overlap the Loop; if adopted it enters as a
  BACKEND behind our plug, never as the ontology.
- **Deferred until their rung:** Vespa, Milvus, OpenSearch, turbopuffer
  - rung 2-3 engines; integrating them today would be speculative
  infrastructure (the horizon rule: keep the seam, not the dependency).
- **Rejected as core:** LlamaIndex/LangChain/Haystack as foundation
  (parallel ontology); bm25s (no gain over FTS5, measured); hosted
  embedding APIs (Voyage/Codestral - the embeddings-are-LOCAL law).

## 7. Recompute

```bash
PYTHONPATH=. python3 -m loop_engine --self-test   # retrieval tests incl. handshakes + space law
# tournament + scale numbers: evidence/retrieval-engine-tournament-20260823.json
```
