# Graphify as an optional Code Intelligence producer

Graphify is useful to Loop Engine as a local descriptive source graph. It is
not a replacement for `Loop`, `LoopGraphDefinition`, the Code Intelligence
admission lifecycle, or the Reusable Capability Flywheel.

This evaluation inspected Graphify 0.9.53 at commit
`33362d969292b57eda82f3fbd9eb5f3f5bc9bbc2` on 2026-08-31. It also ran that
exact source revision against the current Loop Engine working tree.

## Decision

```text
Loop Engine graph use
├── Descriptive Code Intelligence graph
│   ├── source entities and relationships
│   ├── Graphify as one optional evidence producer
│   ├── exact source paths, locations, confidence, and graph digest
│   └── passive records that grant no execution authority
├── Executable Loop graph
│   ├── exact LoopDefinitionRef per executable vertex
│   ├── typed input and output ports
│   ├── deterministic, hybrid, or non-deterministic mode per Loop
│   └── permissions, effects, conditions, verification, and Run History
└── Bridge
    ├── normalize external graph evidence
    ├── resolve missing or implicit entities
    ├── verify source freshness
    ├── propose capability candidates
    └── admit and promote only through existing Code Intelligence authority
```

Use Graphify behind an optional, versioned adapter. Do not add Graphify or its
Tree-sitter language packages to the lightweight Loop Engine base install.
Do not copy Graphify's graph schema into Loop Engine as a second source of
truth.

## Verified upstream facts

The current package is `graphifyy` 0.9.53 and requires Python 3.10 or newer.
Its base dependencies include NetworkX, NumPy, RapidFuzz, Tree-sitter, and a
large set of language grammars. The package metadata declares Apache 2.0. The
repository also retains an MIT license for contributions made before the
relicensing. See the [official repository](https://github.com/Graphify-Labs/graphify),
[package metadata](https://github.com/Graphify-Labs/graphify/blob/v0.9.53/pyproject.toml),
and [NOTICE](https://github.com/Graphify-Labs/graphify/blob/v0.9.53/NOTICE).

The source architecture is:

```text
detect
  -> extract
  -> build
  -> cluster
  -> analysis helpers
  -> report
  -> export
```

Code extraction uses local Tree-sitter parsing. Documents and images can use a
configured semantic backend. Audio and video transcription can use local
faster-whisper. The exact privacy statement therefore depends on the selected
input class and backend. Code-only extraction is local. A mixed semantic pass
can send selected material to a configured provider. See the
[upstream README](https://github.com/Graphify-Labs/graphify/blob/v0.9.53/README.md)
and [security model](https://github.com/Graphify-Labs/graphify/blob/v0.9.53/SECURITY.md).

Graph edges carry `source`, `target`, `relation`, `confidence`, source file,
and source location. Upstream documents the confidence vocabulary as
`EXTRACTED`, `INFERRED`, and `AMBIGUOUS`. This is useful evidence metadata. It
does not prove runtime behavior.

The ordinary local query path is deterministic. It tokenizes the question,
removes filler terms, computes IDF weights, uses a trigram postings index when
selective, ranks candidate entities, chooses seeds, traverses with BFS or DFS,
and renders a token-budgeted subgraph. It does not require dense embeddings or
an LLM.

Reverse impact analysis traverses a declared relation set that includes calls,
indirect calls, references, imports, dynamic imports, inheritance,
implementation, use, embedding, and dependency relations. It carries the
traversed edge location so the result can cite a call or import site.

Query logging is off by default. It becomes active only through an explicit
environment setting. Graphify's work-memory reflection is stored in a separate
sidecar and does not mutate structural graph truth.

## Benchmark interpretation

Graphify reports 0.497 recall@10 on LOCOMO. LOCOMO is a conversational-memory
benchmark, not a repository coding benchmark. The same report gives 45.3
percent Graphify QA accuracy and 49.7 percent Supermemory QA accuracy. The
LongMemEval-S result is 76 percent QA accuracy for both Graphify and dense RAG.

The published code evaluation uses six ERPNext questions. It reports 82.0
percent key-fact coverage with Graphify and 70.8 percent with the grep/read
baseline, at about 140,000 tokens per agent query. This is promising pilot
evidence, not broad proof across languages or software tasks. See the
[official benchmark report](https://github.com/Graphify-Labs/graphify/blob/v0.9.53/BENCHMARKS.md).

The benchmark's primary memory configuration combines deterministic graph
expansion with a shared local BGE-m3 embedder. That number must not be presented
as the measured performance of every ordinary lexical plus graph query.

## Live Loop Engine evaluation

The first code-only run used no provider variables and disabled query logging.
It produced:

| Measurement | Observed value |
|---|---:|
| Code files detected | 575 |
| Explicit graph entities | 8,736 |
| Relationships | 24,973 |
| Graph size | 12,240,965 bytes |
| Cold elapsed time | 10.89 seconds |
| Peak memory | 406,296 KB |
| Unchanged retry files | 134 |
| Unchanged elapsed time | 3.42 seconds |

The 134 unchanged retry files were mostly JSON records classified as code but
producing no structural entities. The graph also included saved evidence and
benchmark outputs that are not source authority.

Loop Engine now ships a `.graphifyignore` that excludes generated evidence,
saved outputs, and JSON records already governed by schemas or catalogs. The
filtered run produced:

| Measurement | Observed value |
|---|---:|
| Code files detected | 401 |
| Explicit graph entities | 7,985 |
| Relationships | 24,164 |
| Source files represented | 401 |
| Cold elapsed time | 10.42 seconds |
| Peak memory | 404,012 KB |
| Unchanged changed-file count | 0 |
| Unchanged elapsed time | 1.17 seconds |
| Graph SHA-256 | `005a36f9a7b3ca2a62a50ed6e51f02cb95111f25412ce71a2a9e61c4f548f413` |

The filtered raw graph had 104 relationship endpoints with no explicit entity
record. These were external modules and unresolved references. NetworkX adds
them as implicit graph entities when loading the graph, so the query header
reported 8,089 entities. A Loop Engine adapter must label such entities as
external unresolved references. It must not present them as source-extracted
repository entities.

Exact explanation worked well. `ParameterDefinition` resolved to its source,
import, callers, deterministic validator, and rationale. Exact file impact for
`runtime_settings.py` found settings consumers and call sites. A qualified
method query failed until the exact displayed label
`.loop_config_with_record()` was used.

Free-form capability retrieval remained broad. A reusable-capability query
expanded to 827 entities. A parameter-resolution query with a call-only filter
expanded to 537 entities. Graphify should therefore support exact structural
orientation and bounded evidence expansion. It should not become the sole
semantic capability resolver.

## Integration requirements

An eventual adapter must record:

- Graphify package version and source commit.
- source repository commit and working-tree digest;
- `.graphifyignore` digest;
- graph artifact digest and schema shape;
- explicit and implicit entity counts;
- relation and confidence counts;
- source file and source location for each selected fact;
- query text digest, traversal mode, depth, filters, token budget, and
  truncation status;
- unresolved external endpoints;
- whether semantic extraction, transcription, networking, or an LLM was used;
- query-log policy;
- exact adapter and normalization versions.

Discovery remains effect-free. A graph update, MCP call, or CLI call executes
through a canonical Loop with typed file, network, model, and shell authority.
Graphify entities and relationships remain passive Code Intelligence evidence.

## Rejected integrations

- Do not make a Graphify entity an executable Loop.
- Do not add a fourth graph runtime.
- Do not make `graph.json` the admission or lifecycle authority.
- Do not let similarity or graph centrality bypass contract, effect,
  permission, lifecycle, provenance, or qualification checks.
- Do not import Graphify's learning sidecar as active Runtime History.
- Do not run semantic extraction merely because a provider key exists.
- Do not present LOCOMO or the six-question ERPNext pilot as Loop Engine task
  quality evidence.

## Next integration increment

Build an optional adapter at the existing Code Intelligence and MCP boundaries.
Start with exact symbol lookup, callers, callees, path, and affected-file
queries. Normalize missing endpoints and bind every result to source digests.
Evaluate the adapter on a frozen set of real Loop Engine change questions
against the existing deterministic orientation snapshot and manual source
truth. Promote no external graph fact merely because it was returned.
