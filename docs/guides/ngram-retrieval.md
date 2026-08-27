# Statistical n-gram retrieval

Loop Engine can build an exact character and word n-gram materialization for
bounded lexical retrieval. The materialization adds typo tolerance, phrase
evidence, and term statistics. It does not replace the Retrieval Engine or add
an intelligence layer.

## Architecture fit

The operational object is still a Loop. The index definition, index, scores,
and benchmark judgments are passive typed objects.

```text
Operational runtime type
└── Loop
    ├── Relationship: Starting, Spawned by, Queried by, Retrieved by, or Connected from
    ├── Role: Practitioner, Intelligence, or Solution
    ├── Versioned role profile
    ├── Purpose and domain categories
    ├── Run mode: deterministic, hybrid, or non-deterministic
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition and exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the selected mode permits a model
    └── Run History records
```

The n-gram branch stays inside Intelligence Search and Retrieval:

```text
Intelligence Search and Retrieval
└── External statistical materialization
    ├── NgramSpaceDefinition
    │   └── passive versioned identity and content digest
    ├── NgramIndex
    │   ├── exact character postings
    │   ├── exact word postings
    │   └── exact TF, DF, CF, and IDF statistics
    ├── NgramQueryResult
    │   ├── body-free ranked references
    │   ├── exact scope filter
    │   └── score contribution details
    └── Governed operations
        ├── Practitioner Loop builds the materialization
        └── Intelligence Loop queries the materialization
```

`NgramSpaceDefinition`, `NgramIndex`, and `NgramQueryResult` are not executable
graph vertices. `build_index_as_loop()` and `query_as_loop()` use the canonical
Loop wrapper when build or query work needs its own governed identity.

## Pinned space identity

An n-gram result is meaningful only inside one exact term space. The default
space pins:

- Unicode normalization: `NFKC`.
- Case normalization: `casefold`.
- Tokenizer: `unicode_alnum_v1`.
- Identifier splitting: `camel_snake_hyphen_v1`.
- Punctuation handling: replace punctuation with spaces.
- Character boundaries: per-token `^` and `$` markers.
- Character range: 3 through 5.
- Word range: 1 through 2.
- Posting key encoding: exact UTF-8 strings.
- Digest algorithm: SHA-256 with no seed.
- Weighting: sublinear TF-IDF cosine.
- Approximation: none.

The complete definition produces a SHA-256 `definition_digest`. A change to a
term-identity setting produces a different space reference and requires a new
index.

The hash setting protects definition, document, and index identity. The exact
postings do not use hash buckets, so unrelated terms cannot collide through a
feature-hashing shortcut.

## Exact statistics

For every character or word n-gram, the index can report:

- Query term frequency, or TF.
- Document frequency, or DF.
- Collection frequency, or CF.
- Smoothed inverse document frequency, or IDF.

Scoped queries calculate DF, CF, and IDF from eligible documents only. An
inaccessible scope therefore cannot change an accessible ranking or disclose
its document frequency through the result.

Every current result states:

```json
{
  "result_precision": "exact",
  "approximation": null
}
```

Approximate search raises `NotImplementedError`. Loop Engine does not label an
untested sketch or approximate index as exact.

## Explainable fusion

The default fusion policy combines four independent channels:

```text
Candidate score
├── exact character n-gram cosine
├── exact word n-gram cosine
├── supplied lexical score, when present
└── supplied semantic score, when present
```

Supplied lexical and semantic scores can come from the existing Retrieval
Engine or another reviewed adapter. The n-gram module does not call those
adapters itself. It validates document identities, removes disallowed scopes,
normalizes each supplied channel, and records the raw score, effective weight,
and weighted contribution for every hit.

The fusion policy is versioned and digest-pinned. It exposes contributions
instead of returning one unexplained score.

## Use the exact index

```python
from loop_engine.core.ngram_retrieval import (
    NgramDocument,
    build_index_as_loop,
    query_as_loop,
)

documents = (
    NgramDocument(
        "address-normalization",
        "Normalize customer addresses and preserve apartment units",
        "tenant:alpha",
        source_ref="catalog:address-normalization",
    ),
    NgramDocument(
        "schema-validation",
        "Validate Schema.org JSON-LD and SHACL constraints",
        "tenant:alpha",
        source_ref="catalog:schema-validation",
    ),
)

built = build_index_as_loop(documents)
searched = query_as_loop(
    built["index"],
    "normalise customer addrsses",
    allowed_scopes=("tenant:alpha",),
    top_k=2,
)

print(searched["loop_id"])
print(searched["result_record"]["hits"])
```

The build runs as a deterministic Practitioner Loop. The query runs as a
deterministic Intelligence Loop with the `intelligence.search` profile. Both
paths make zero model calls.

The returned hits contain document identity, scope, score details, and matching
grams. They do not contain document bodies. Materializing a selected source is
a separate Intelligence operation.

## Evidence boundary

N-grams and frequency distributions are retrieval evidence. They are not
verified claims, permissions, or active Learned intelligence. A frequent term
can still be wrong, irrelevant, stale, or outside the permitted scope.

This implementation is also separate from Qwen or another model's internal
learned n-gram embedding tables. Loop Engine builds an external, exact lexical
index over supplied cards. It does not reproduce, inspect, or make claims about
a model's learned parameters.

Run the frozen development and holdout benchmark:

```bash
PYTHONPATH=src python3 -m loop_engine.core.ngram_retrieval \
  benchmarks/ngram-retrieval/frozen-judgments-v1.json
```

See the [benchmark README](../../benchmarks/ngram-retrieval/README.md) for the
population, metrics, and current limitations.
