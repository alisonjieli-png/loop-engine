# Compare published harness benchmark evidence

Loop Engine compares results that another project has already published. It
does not rerun Deep Agents, Pydantic AI, OpenAI Agents, or Microsoft Agent
Framework through this catalog.

This research catalog is separate from the
[optional external harness adapters](../components/core-architecture/EXTERNAL-HARNESS-ADAPTERS.md).
The catalog reads published evidence. An adapter would execute a selected
package inside one bounded Loop. Neither one proves the other.

The catalog contains reviewed numeric results, graphical findings, and searches
that found no qualifying score. It currently has one exact cross-harness group
from Artificial Analysis Coding Agent Index v1.4.

Loop Engine results use a separate catalog:
[`loop-engine-benchmark-evidence.json`](../benchmarks/loop-engine-benchmark-evidence.json).
`match_loop_engine_to_published()` joins the two catalogs only when every
comparison key matches. The current report finds zero fair Loop
Engine-to-harness matches. It gives an exclusion reason for each saved Loop
Engine result instead of comparing unlike scores.

## Required facts

Every record must name these facts:

| Field | Meaning |
|---|---|
| Harness and version | The harness used in the published run |
| Benchmark and version | The exact benchmark release or dated revision |
| Model and version | The model used by the published run |
| Population | Named subset, item count, and selection rule |
| Tools | Tools available to the measured system |
| Evaluation protocol | Attempts, evaluator, aggregation, and scoring rule |
| External environment | The task environment held outside the harness |
| Score | Value, metric, unit, and direction |
| Evaluation date | Date attached to the result or source |
| Source | Official or primary URL and title |
| Evidence qualifier | Harness measured, model only, or unclear |
| Limitations | What the published result does not establish |

Model calls, input tokens, output tokens, and cost remain optional because many
published sources do not report them. Missing values remain unknown. They do not
become zero.

## Evidence qualifiers

`harness_measured` means the cited score was produced by the named harness.
The source must describe the harness configuration clearly enough to support
that attribution.

`model_only` means the source reports the underlying model without the named
harness. A model-only record cannot be used as evidence of harness quality. It
uses `harness_name: none`.

`unclear` means the source does not establish whether the measured system was
the model alone or a particular harness. It remains visible but cannot enter a
harness comparison.

## Exact comparison groups

Two records enter the same group only when all of these match:

- benchmark name and version;
- population name, count, and selection rule;
- model version and effort;
- evaluator, scoring rule, and external environment;
- score metric, unit, and direction.

A group becomes comparable only when it contains at least two source-reviewed
`harness_measured` records from different harnesses. Harness tools do not need
to match because tool access is part of the harness being compared. The catalog
records that difference instead of treating it as a fixed control. It does not
rank records from different models, populations, evaluators, or metrics.

Matching these fields does not prove every hidden configuration is equal. State
sampling settings, budgets, prompting, retries, and other known differences in
each record's limitations.

## Files

The machine-readable files are:

- [`published-harness-evidence.json`](../benchmarks/published-harness-evidence.json)
- [`published-harness-evidence.schema.json`](../benchmarks/published-harness-evidence.schema.json)

Load and audit the catalog in Python:

```python
from loop_engine.code_nodes.complex_task_benchmark import (
    default_loop_engine_catalog_path,
    default_published_catalog_path,
    load_native_evidence,
    load_published_evidence,
    match_loop_engine_to_published,
)

published = load_published_evidence(default_published_catalog_path())
native = load_native_evidence(default_loop_engine_catalog_path())
report = match_loop_engine_to_published(
    native,
    published,
)
print(report.to_dict())
```

The accounting output separates reviewed sources, harness measurements,
model-only records, unclear records, and comparable groups.

## Admission rule

Do not add a search result, social post paraphrase, or leaderboard screenshot
without a stable source page that states the required facts. Use
`source_unverified` while source review is incomplete. Such a record cannot
enter a comparison.

Do not translate an architecture feature into a benchmark result. Context
isolation, subagents, sandboxes, skills, and memory are capabilities. They are
not task scores.

## What this catalog establishes

A populated comparable group can show what the named sources reported under a
matching published setup. It does not prove that Loop Engine reproduced those
runs or that one harness will perform better on a new task.
