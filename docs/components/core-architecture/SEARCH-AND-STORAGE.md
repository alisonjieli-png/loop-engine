# Search and storage choices

Loop Engine uses one Retrieval Engine interface and several replaceable
backends. The searchable unit is a small card. Large source files, packages,
repositories, datasets, and model files stay behind immutable references.

## Current search path

```text
need
  -> exact identity and typed filters
  -> optional blocking keys or locality-sensitive hash
  -> lexical and optional vector retrieval
  -> reciprocal-rank fusion
  -> eligibility filters
  -> ranked LoopRefs
  -> select one
  -> materialize and verify the selected body
```

The current package provides:

| Channel | Current implementation | Main use |
|---|---|---|
| In-memory lexical | Store term weighting | Small JSON Lines example catalogs. |
| Full-text lexical | SQLite FTS5 with BM25 | Default local search with no server. |
| Columnar full-text | LanceDB full-text search | Larger local indexes. |
| Deterministic vector | Token and character feature hashing | Typo and word-form tolerance without a learned model. |
| Learned local vector | model2vec | Semantic retrieval when the configured model is present. |
| Blocking | Typed facets, keywords, and blocking keys | Remove ineligible records before wider work. |
| Lexical locality | Stable 64-bit SimHash | Cheap approximate grouping and experiments. |

One GitHub install includes these adapters and their Python dependencies:

```bash
python -m pip install "https://github.com/alisonjieli-png/loop-engine/archive/refs/heads/main.zip"
```

Missing declared dependencies fail clearly. The Retrieval Engine does not
silently replace a selected backend with a different one.

## Flexible records

Each card has stable common fields and a namespaced metadata object. Search
text can include descriptions, summaries, templates, key phrases, labels,
keywords, public symbols, entry points, component names, asset kinds, source
kinds, domain fields, format examples, typed facets, and nested safe metadata.

Typed facets remain available for hard requirements and exclusions. New
experimental descriptors can be added in namespaced metadata without adding a
database column first. If a descriptor proves useful, it can later become a
typed common field.

Embeddings always carry an exact space identity: model, revision, dimensions,
normalization, and distance. Vectors from different spaces are refused rather
than compared.

## Large bodies and several storage locations

The search card stores:

```text
payload locator
SHA-256 digest
size
media type
storage type
contract and entry points
search metadata
```

The payload may live in a local file, package cache, Git repository, object
store, container registry, database, or service. The current resolver decides
how to load it. A digest-keyed cache avoids loading the same immutable body for
each subsystem card.

`load_knowledge()` has three content modes:

| Mode | Behavior |
|---|---|
| `inline` | Parse supported text files into searchable records. This remains the default. |
| `reference` | Stream a digest and store one compact external reference card. |
| `auto` | Inline files below the threshold and reference larger files. The default threshold is 8 MB. |

Size is checked before text decoding. Reference mode never sends the large body
through the text parser.

## Off-the-shelf engines reviewed

The practical choice is to keep SQLite FTS5 as the zero-service default and
use the existing LanceDB adapter for the next local scale tier. Add a service
backend only when measured load, concurrency, or tenant isolation requires it.

| Engine | Useful properties | Current decision |
|---|---|---|
| SQLite FTS5 | Built into Python's SQLite on supported builds, BM25 ranking, prefix indexes, and contentless or external-content indexes. | Current default lexical engine. Loop Engine keeps bodies outside search results. |
| LanceDB | Local, object-storage, and hosted connection modes; full-text, vector, hybrid, scalar filtering, and column projection. | Current optional large local backend. The Loop Engine adapter currently opens a local index. Cloud or object-store configuration needs a separate storage adapter and test. |
| DuckDB | Strong analytical queries over JSON, Parquet, and run history; an official full-text extension exists. | Current catalog and analysis option. Not the default online ranker. |
| DuckDB VSS | HNSW vector search inside DuckDB. | Not adopted for production. DuckDB documents the extension and persistent index support as experimental. |
| Qdrant | Dense and sparse named vectors, hybrid and multi-stage queries, JSON payload filters, local or service deployment. | Good future service plugin when multi-writer or tenant scale justifies a service. Not required now. |
| OpenSearch | Keyword and vector search, hybrid search pipelines, rank or score fusion, pre-filtering, post-filtering, and explanations. | Good future adapter for organizations that already operate an OpenSearch cluster. Too much infrastructure for the default package. |

Primary documentation:

- [SQLite FTS5](https://www.sqlite.org/fts5.html)
- [LanceDB Python interface and query modes](https://lancedb.github.io/lancedb/python/python/)
- [Lance local and object-storage reads](https://lancedb.github.io/lance/introduction/read_and_write.html)
- [DuckDB full-text search](https://duckdb.org/docs/stable/core_extensions/full_text_search)
- [DuckDB vector similarity search](https://duckdb.org/docs/lts/core_extensions/vss)
- [Qdrant hybrid queries](https://qdrant.tech/documentation/search/hybrid-queries/)
- [Qdrant payload filtering](https://qdrant.tech/documentation/search/filtering/)
- [OpenSearch hybrid search](https://docs.opensearch.org/latest/vector-search/ai-search/hybrid-search/index/)

## Adoption rule

A new backend must implement the same handshake and return the same body-free
`LoopRef` shape. Compare it on a frozen query set with the same records,
filters, expected matches, resource limits, and ranking measures. Keep the
losing results. A backend is not adopted because its feature list is longer.

This keeps the storage choice reversible. The intelligence layers and loop
contracts do not depend on one database product.
