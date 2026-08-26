# Runtime History and Solution Intelligence

Runtime History and Solution Intelligence helps a loop reuse what happened before.
It can describe a saved run, a decision, a failure, a repair, a measurement, a
comparison, or a reusable Solution.

A historical item is a prior. It is not proof that the same choice will work
for the current task. The current loop must still check applicability and
verify its result.

## What belongs in this layer

The shared classification schema recognizes these category groups:

| Category group | What it describes | Example |
|---|---|---|
| `run` | One saved execution and its Loop graph | A completed customer-import run |
| `solution` | A reusable Solution specification or compiled composition | A tabular-classification Solution Canvas |
| `decision` | A choice, its alternatives, and the reason for the choice | Use a deterministic validator before model review |
| `failure` | Work that failed or could not be verified | A provider timeout after all configured attempts |
| `repair` | A change that addressed a recorded failure | Normalize country codes before validation |
| `measurement` | An observed metric, cost, duration, or resource count | 2 model calls and 1,240 tokens for one run |
| `comparison` | Results from alternatives tested under a shared evaluation | Code-only baseline compared with a hybrid method |
| `other` | A visible item that does not yet have a reliable category | Imported legacy history awaiting classification |

The common fields are `layer`, `item_type`, `category_group`, `category`,
`subcategory`, `domain`, `scope`, `lifecycle`, `source`, and `tags`.

## Current storage

Loop Engine has two related storage paths today.

### Run History

`Run History` is the canonical event history for one run. It is append-only and
hash-chained. Its default location is:

```text
~/.loop-engine/runs/<run_id>/
  manifest.json
  events.jsonl
```

Set `LOOP_ENGINE_RUNS_DIR` or pass a directory to use another location.

The manifest stores the run identity, parent run, event count, head digest,
and committed state. The JSONL file stores the ordered events. Each event
contains its sequence number, previous digest, event digest, loop identity,
mode, status, and relevant usage fields.

Create and save a Run History from a loop ledger:

```python
from loop_engine import LoopLedger
from loop_engine.core.run_history import RunHistory

ledger = LoopLedger()
provider_usage = []

run_history = RunHistory.from_ledger(
    ledger.events,
    run_id="customer-import-2026-08-25",
    usage_log=provider_usage,
)
run_history.commit()
run_directory = run_history.save("./runs")

print(run_directory)
print(run_history.verify_chain())
```

`commit()` makes the in-memory history immutable. `save()` refuses to replace
an existing run directory.

### Solution Library

`SolutionLibrary` stores `SolutionAsset` records in a supplied Loop Engine
store. A Solution asset contains a task fingerprint, the Solution
specification record, the compiled Code digest, evaluation information,
runtime information, failure history, applicability, lineage, and maturity.

```python
from loop_engine.core.solution_library import (
    SolutionAsset,
    SolutionLibrary,
    task_fingerprint,
)
from loop_engine.core.store_serve import SolverStore

fingerprint = task_fingerprint(
    problem="classification",
    output_role="risk_label",
    metric="roc_auc",
    rows=85000,
    modality="tabular",
)

library = SolutionLibrary(SolverStore())
library.add(SolutionAsset(
    asset_id="risk-baseline-v1",
    spec_record_id="solution.risk-baseline-v1",
    fingerprint=fingerprint,
    compiled_digest="a" * 64,
    evaluation_evidence=("one local holdout evaluation",),
    runtime={"model_calls": 0},
    applicability="tabular binary classification with the same output role",
    maturity="candidate",
))

similar = library.find_similar(fingerprint, top_n=3)
assert all(item["prior_not_proof"] for item in similar)
```

The fingerprint separates modality, problem kind, output role, metric, and
scale band. The library keeps a regression Solution out of a classification
result. Exact fingerprint matches rank before broader family matches.

## Search history as loops

`build_intelligence_catalog()` scans saved Run History directories and creates
small searchable run-summary records. Each summary contains:

- `run_id`
- event count
- model-call count
- token count
- chain-integrity result
- lifecycle and classification fields

The search path does not load every event body. It runs a search loop and
returns ranked `LoopRef` objects.

```python
from loop_engine import LoopLedger
from loop_engine.loop.loop_capsule import LoopRef
from loop_engine.core.intelligence_layers import (
    build_intelligence_catalog,
    materialize_intelligence_ref,
    query_intelligence,
)

ledger = LoopLedger()
catalog = build_intelligence_catalog(runs_dir="./runs")

search = query_intelligence(
    "find a previous customer import with country-code failures",
    catalog,
    mode="lexical",
    top_n=5,
    ledger=ledger,
)

history_hits = [
    item for item in search["hits"]
    if item["layer"] == "runtime_history_solution_intelligence"
]

if history_hits:
    selected = LoopRef.from_dict(history_hits[0]["loop_ref"])
    loaded = materialize_intelligence_ref(
        selected,
        catalog,
        ledger=ledger,
    )
    summary = loaded["value"]
    print(summary["run_id"], summary["chain_intact"])
```

The steps are separate:

```text
search loop
  -> ranked LoopRefs without full event histories
  -> choose one reference
  -> historical access loop
  -> selected summary
```

The `LoopRef` carries identity, layer, supported modes, input and output
contracts, effects, maturity, version, score, locator, and digest. It does not
carry the full Run History.

## Load a full Run History through a historical loop

Materializing the unified catalog reference returns the small run summary.
Load the full event history only after selecting a run:

```python
from loop_engine.loop.intelligence_loops import (
    serve_historical_intelligence,
)
from loop_engine.core.run_history import RunHistory

selected_run_id = summary["run_id"]

served = serve_historical_intelligence(
    f"history:{selected_run_id}",
    lambda: RunHistory.load("./runs", selected_run_id),
    ledger=ledger,
)

selected_run_history = served["value"]
integrity = selected_run_history.verify_chain()
if not integrity["intact"]:
    raise ValueError("selected Run History failed its chain check")
```

This is a deterministic historical loop. Loading history does not call a
language model.

For a simpler store-backed history collection, use these exact APIs:

```python
from loop_engine.loop.intelligence_loops import (
    search_as_loop_refs,
    serve_record_as_loop,
)

references = search_as_loop_refs(
    history_store,
    "country-code repair",
    pillar="runtime_history_solution_intelligence",
    top_n=5,
    ledger=ledger,
)

selected_record = serve_record_as_loop(
    history_store,
    references[0].loop_ref.rsplit("/", 1)[-1],
    pillar="runtime_history_solution_intelligence",
    ledger=ledger,
)
```

## Lifecycle and evidence boundaries

Use this sequence for run history:

```text
live LoopLedger events
  -> Run History projection
  -> commit
  -> save under a new run identity
  -> search summary
  -> selected historical loop
  -> current-task verification
```

These rules apply:

1. Run History is append-only after `commit()`.
2. A broken hash chain shows that stored history changed. An intact chain does
   not prove that a result was correct.
3. Search rank is a retrieval signal. It is not an acceptance decision.
4. A previous Solution is a starting point. It must pass the current task's
   contracts and evaluation.
5. A candidate Solution does not become registered because it was retrieved
   or used.
6. Playback reads saved history. Recorded-output replay substitutes saved
   semantic outputs. Neither action is the same as a fresh live rerun.
7. A self-improvement Practitioner task verifies Run History chains before mining history.
   It stages improvement candidates only. It does not promote them.

For strict history intake in improvement work, use:

```python
from loop_engine.code_nodes.self_improvement_loop import (
    load_run_history,
)

population = load_run_history("./runs", limit=100, ledger=ledger)
print(population["runs"])
print(population["excluded"])
```

Unreadable runs, missing manifests, and broken chains appear in `excluded`.

## Exact API map

| API | Purpose |
|---|---|
| `RunHistory(run_id, parent_run_id="")` | Start one canonical event history |
| `RunHistory.append(event_type, **fields)` | Add one ordered event before commit |
| `RunHistory.from_ledger(events, run_id=..., usage_log=...)` | Project a runtime ledger into a Run History |
| `RunHistory.commit()` | Make the in-memory history immutable |
| `RunHistory.save(directory)` | Write one new run directory |
| `RunHistory.load(directory, run_id)` | Load one saved Run History |
| `RunHistory.verify_chain()` | Recompute the event chain and name broken positions |
| `RunHistory.to_otel_spans()` | Create an OpenTelemetry-shaped export view |
| `recorded_output_handler(run_history, base_handler, semantic_steps=...)` | Replay selected semantic outputs without new model calls |
| `build_intelligence_catalog(runs_dir=...)` | Build searchable Run History summary cards |
| `query_intelligence(...)` | Search all supplied intelligence layers in one loop |
| `materialize_intelligence_ref(ref, catalog, ...)` | Load one selected summary through a historical loop |
| `serve_historical_intelligence(name, content, ...)` | Serve selected historical data through one loop |
| `task_fingerprint(...)` | Build the Solution family search key |
| `SolutionAsset(...).to_record()` | Convert a Solution asset into a store record |
| `SolutionLibrary(store).add(asset)` | Add a Solution asset to its supplied store |
| `SolutionLibrary(store).find_similar(fingerprint)` | Return family-matched Solution priors |
| `load_run_history(...)` | Load and verify a bounded run population |

## Current limitations

- The unified catalog currently imports Run History summaries. It does not
  yet import `SolutionLibrary` assets into the same third-layer population.
- Built-in catalog history records currently use the `run` category. The
  other category groups are defined, but need their own record producers.
- A catalog summary exposes `chain_intact`, but general retrieval does not
  reject a false value. Check it before use, or use
  `load_run_history()` for strict improvement intake.
- A catalog `LoopRef` materializes the run summary, not `events.jsonl`. Full
  event loading is a separate historical loop.
- Run History storage is local file storage by default. The package does not
  automatically synchronize it with cloud or team storage.
- The hash chain detects changes. It does not validate a task result, model
  statement, metric, or external fact.
- `SolutionLibrary.find_similar()` uses its supplied store and a dedicated
  search path. It is not yet joined to `build_intelligence_catalog()`.

These limitations are integration work, not reasons to merge history into
another layer. The third layer already has a clear identity and loop boundary.
