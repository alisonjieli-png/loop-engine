# Intelligence portfolios for non-deterministic Loops

An intelligence portfolio gives one model-led Practitioner Loop a small,
traceable cross-section of what Loop Engine already knows. Selection uses the
existing four-layer Retriever and returns typed `LoopRef` objects before any
body is loaded. It does not create prompts, call a model, enable candidate
Context records, or set a model-output token limit.

The bound is semantic: exactly one unique active reference from each required
lens family. It is unrelated to provider output size.

| Lens family | What it contributes |
|---|---|
| `first_principles` | Invariants, mechanisms, assumptions, decomposition |
| `alternatives_analogy` | Alternatives, analogy, counterfactuals, diversity |
| `missing_information` | Gaps, prerequisites, uncertainty, information gain |
| `failure_adversarial` | Failure modes, premortems, falsification, risks |
| `cost_resource` | Cost, budget, minimum complexity, resource discipline |
| `verification_evaluation` | Evidence, metrics, validation, evaluation |
| `output_contract_format` | Output schemas, response shapes, serialization |

## Map and materialize

```python
from loop_engine import (
    PortfolioRequest,
    PortfolioSelectionServices,
    PortfolioMaterializationServices,
    select_intelligence_portfolio,
    materialize_portfolio_for_loop,
)
from loop_engine.core.intelligence_layers import (
    build_intelligence_catalog,
)

catalog = build_intelligence_catalog()
request = PortfolioRequest(
    task="compare a complete benchmark solution",
    consuming_loop_id="candidate.ds1000.1",
    benchmark_id="ds1000",
    mode="non_deterministic",
)
portfolio = select_intelligence_portfolio(
    request,
    PortfolioSelectionServices(layer_records=catalog),
)
materialized = materialize_portfolio_for_loop(
    portfolio,
    PortfolioMaterializationServices(layer_records=catalog),
)

# The typed Loop boundary receives exactly what this Loop consumed.
context_policy = materialized.consumption.context_policy()

# Add these fields only when the real model event is recorded.
model_event_fields = materialized.consumption.run_history_fields()
```

Each query trace records its retrieval loop, returned population, selected
rank, comparable top cohort, empty layers, and zero model calls. Selection is
stable for one consuming Loop identity. Different Loop identities rotate among
equally qualified ontology matches, giving multiple model-led Loops different
phrasing and context without weakening the seven-family coverage contract.

Runtime History and Solution Intelligence and User Feedback Intelligence are not fabricated
when their stores are empty. Both appear as `empty_visible` in layer coverage
and in every lens query's `empty_layers` field.

## Benchmark Code Intelligence

`BenchmarkCodeRegistration` accepts only a `CodeAssetSpec` whose lifecycle is
`registered`, whose `admission_ref` is present, and whose declared entrypoints
are each bound exactly once to a callable. `BenchmarkCodePack` exposes only the
records registered for the requested benchmark and marks their intended lens
families on their body-free search cards.

The portfolio's `non_deterministic` rule governs the model-led Loop. A
registered deterministic Code component remains eligible for retrieval,
materialization, and execution. The focused self-test uses such a component to
normalize scores through a real callable entrypoint with zero model calls.

## Fold and export

`fold_loop_intelligence_consumption()` keeps the exact reference list under
each consuming Loop identity and separately reports unique references and
lens-family use.
`export_intelligence_portfolios()` exports the mapped portfolios plus that
folded consumption record. Retrieved payload bodies are intentionally absent
from the export.

Run the focused verification with:

```bash
PYTHONPATH=src python3 -c \
  'from loop_engine.core.intelligence_portfolio import self_test; print(self_test())'
```

The check uses the packaged active Context catalog and an actual record from
the packaged candidate bank to test the exclusion boundary. Its only added
Code pack is a small real-callable, admission-bound component used to verify
the Code path itself.
