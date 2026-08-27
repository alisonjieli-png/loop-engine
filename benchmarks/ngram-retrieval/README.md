# Exact n-gram retrieval benchmark

This frozen offline benchmark measures the exact statistical n-gram slice. It
uses no network access, provider, embedding model, or model call.

## Frozen population

The source-controlled fixture is
[`frozen-judgments-v1.json`](frozen-judgments-v1.json).

```text
Frozen population
├── 15 searchable cards
│   ├── 3 tenant-scoped address cards
│   └── 12 public capability cards
├── 10 retrieval queries
│   ├── 5 development queries
│   └── 5 holdout queries
└── 4 judged document pairs
    ├── 1 same-item pair
    └── 3 different-item pairs
```

The query population includes bounded typos, phrase evidence, exact scope
filters, and one fusion case with supplied lexical and semantic scores. The
tenant scope canary contains the same text in a disallowed scope. A scoped
query must exclude it before ranking.

The document-pair threshold is fixed in the fixture. Pair labels are fixture
judgments for measuring false merge and false split behavior. They are not
active intelligence or universal entity-resolution truth.

## Run it

```bash
PYTHONPATH=src python3 -m loop_engine.core.ngram_retrieval \
  benchmarks/ngram-retrieval/frozen-judgments-v1.json
```

Run only the benchmark through its canonical Practitioner Loop wrapper:

```python
from loop_engine.core.ngram_benchmark import run_frozen_benchmark_as_loop

run = run_frozen_benchmark_as_loop(
    "benchmarks/ngram-retrieval/frozen-judgments-v1.json"
)
print(run["loop_id"])
print(run["benchmark"]["splits"])
```

## Measures

The benchmark reports each query and macro averages for each split:

- Recall at k.
- Precision at k.
- Mean reciprocal rank, or MRR.
- Normalized discounted cumulative gain, or nDCG.
- Query mean, p50, and p95 latency.
- Build time.
- Serialized exact-index size.
- Unique term and posting counts.
- False merge and false split counts and rates.

Recall, precision, MRR, nDCG, rankings, counts, and index size are deterministic
for the fixture and implementation. Build and query timing are observations
from the current process. They vary by machine and system load.

## Current bounded evidence

The implementation run on 2026-08-27 evaluated all 10 queries. It produced the
following result on the frozen fixture with SHA-256 digest
`f253822397e30ee0db07cc50635d2565fb9ee7ce27388623985c30ab5e4ee9ff`:

| Split | Queries | Recall@3 | Precision@3 | MRR | nDCG@3 |
|---|---:|---:|---:|---:|---:|
| Development | 5 | 1.0000 | 0.4000 | 1.0000 | 0.9593 |
| Holdout | 5 | 1.0000 | 0.3333 | 1.0000 | 1.0000 |

The pair fixture recorded zero false merges and one false split. The false
split is retained as a measured limitation. It is not hidden by changing the
threshold after the run.

These scores describe this small synthetic population only. They do not prove
general retrieval quality, semantic understanding, entity-resolution quality,
or performance on a production catalog.

## Architectural boundary

This benchmark evaluates external character and word n-gram materialization.
It does not evaluate Qwen or another model's internal learned n-gram
embeddings. Frequency and overlap are ranking signals, not intelligence truth.

The benchmark operation uses the canonical Loop runtime. The fixture,
`NgramSpaceDefinition`, index, query results, metrics, and judgments remain
passive typed data.
