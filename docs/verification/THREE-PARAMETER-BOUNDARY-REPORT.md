# Three-parameter boundary report

## Outcome

The parameter-boundary checker and its mutation tests are verified working.
The repository-wide migration is not complete.

The immutable starting revision contains 179 unapproved findings. The shared
working tree contains 199. The 20 additional findings are in concurrent work
outside this slice. The two checker modules contain zero findings, and the
exception registry contains zero exceptions.

This distinction matters. Adding a checker does not make the existing source
tree conformant. No legacy or concurrent finding was hidden behind a broad
allowlist.

## Enforced contract

```text
Hand-written public or cross-module call boundary
├── Direct parameter count
│   ├── Maximum: three
│   └── Excluded names: self and cls
├── Contract-shape checks
│   ├── no *args escape hatch
│   ├── no **kwargs escape hatch
│   ├── no untyped or Any-valued option bag
│   ├── no mutable default
│   └── fewer than two direct boolean mode flags
├── Architecture check
│   └── no passive argument or schema container named as a Loop
└── Exact exception check
    ├── one file
    ├── one qualified symbol
    ├── one detector rule
    ├── external contract, reason, owner, and test
    ├── introduced version
    └── removal version or permanent justification
```

More than three related values belong in a cohesive typed request,
configuration, context, or service object. That object remains passive. A new
Loop is warranted only when the work itself needs independent governance,
authority, budget, scheduling, retry, verification, return behavior, or Run
History identity.

Generated dataclass and schema constructors are not hand-written AST
boundaries. A many-field record such as `WorkItemIR` is therefore not split
into arbitrary three-field records.

## Implementation

The implementation is split to keep each module within the 800-line source
limit:

- `src/loop_engine/parameter_boundary.py` contains the AST scanner, typed scan
  request, findings, exact exception validation, and repository scan result.
- `src/loop_engine/parameter_boundary_checks.py` contains the focused mutation
  fixtures and command wrapper.
- `docs/architecture/call-boundary-exceptions.yaml` is the exact exception
  registry. It currently has no entries.
- `artifacts/verification/parameter_boundary_results.jsonl` records the
  immutable baseline, current working-tree measurement, focused proof, and
  exact working-tree delta.

Public names, explicit `__all__` exports, public methods, public constructors,
Python protocol methods, and private module functions imported by another
first-party module are scanned. The checker parses source but does not import
or execute the files under review.

## Baseline and current measurement

The baseline was produced from `git archive` at the starting revision. This
kept the measurement independent of the dirty shared working tree.

| Measurement | Starting revision | Shared working tree |
|---|---:|---:|
| Revision | `6a26978c5e6cd2e3852818c4bb4b2dac23b0da76` | starting revision plus concurrent edits |
| Python files | 230 | 247 |
| Call boundaries | 1,731 | 1,890 |
| Parameter-count findings | 138 | 156 |
| `**kwargs` findings | 31 | 33 |
| `*args` findings | 4 | 4 |
| Boolean-flag findings | 6 | 6 |
| Total unapproved findings | 179 | 199 |
| Approved exceptions | 0 | 0 |

The working tree added 18 parameter-count findings and two `**kwargs`
findings. It resolved none of the baseline findings at measurement time.

### Exact working-tree delta

| File | Exact symbols | Findings |
|---|---|---:|
| `src/loop_engine/code_nodes/solution_model_port.py` | `ModelExecutionSession.invoke`, `ModelInvocationPort.__call__`, `fixture_model_execution` | 3 parameter count |
| `src/loop_engine/core/model_routing_intelligence.py` | `select_model_as_loop` | 1 parameter count |
| `src/loop_engine/core/model_routing_selector.py` | `ModelRouteBootstrapSelector.__init__`, `ModelRouteBootstrapSelector.from_gateway` | 2 parameter count |
| `src/loop_engine/core/ngram_retrieval.py` | `NgramIndex.query`, `NgramIndex.document_similarity`, `_operation_as_loop`, `build_index_as_loop`, `query_as_loop` | 5 parameter count, 1 `**kwargs` |
| `src/loop_engine/memory/storage/learning_cycle.py` | `CandidateJournal.stage`, `CandidateJournal.supersede`, `CandidateJournal.recall`, `CandidateJournal.observe_use` | 4 parameter count |
| `src/loop_engine/memory/storage/learning_records.py` | `run_loop_action`, `transitioned_record` | 1 parameter count, 1 `**kwargs` |
| `src/loop_engine/templates/compiler.py` | `compile_task_value`, `compile_task` | 2 parameter count |

These records were measured, not approved. The exact line, boundary kind, and
detail for every item are in
`artifacts/verification/parameter_boundary_results.jsonl`.

## Focused verification

The focused mutation suite passed 6 of 6 checks. It proved:

- all seven source detectors fire on planted defects;
- a generated many-field dataclass constructor is not reported;
- a typed single-request operation is not reported;
- one exact exception matches one file, symbol, and rule;
- wildcard and directory-wide exceptions fail;
- expired exceptions fail;
- the two new checker modules have zero unapproved findings.

Commands run:

```bash
python3 -m py_compile \
  src/loop_engine/parameter_boundary.py \
  src/loop_engine/parameter_boundary_checks.py

PYTHONPATH=src python3 -m loop_engine.parameter_boundary --self-test

PYTHONPATH=src python3 -m loop_engine.parameter_boundary \
  --root . \
  --source src/loop_engine/parameter_boundary.py \
  --source src/loop_engine/parameter_boundary_checks.py \
  --registry docs/architecture/call-boundary-exceptions.yaml \
  --focus src/loop_engine/parameter_boundary.py \
  --focus src/loop_engine/parameter_boundary_checks.py \
  --revision working-tree \
  --current-version 0.1.0
```

The focused scan indexed two files and five public call boundaries. It found
zero violations and exited successfully. The full repository self-test was not
run during this concurrent slice.

## Integration hooks

This slice does not edit shared integration modules. The owning integration
change should:

1. Add `parameter_boundary` to `_FOLDED_SUBMODULE_TESTS` in
   `src/loop_engine/_self_test.py`. Its `self_test()` uses only temporary
   deterministic fixtures.
2. Add a changed-file CI lane that invokes the checker with one `--source`
   argument per changed first-party Python file. This enforces zero new
   violations while the 179 baseline findings are migrated.
3. After migration, invoke one full scan across `src/loop_engine` and
   `devtools/src` from repository conformance and CI. A nonzero unapproved
   result must fail the gate.
4. Keep the exception registry source-controlled and require an exact review
   for every entry. Do not convert the measured baseline into exceptions.
5. Keep the scanner out of the public runtime API. It is a development
   conformance surface and does not create another runtime or graph authority.

## Limits

The scanner resolves ordinary first-party `from ... import ...` relationships.
It does not claim to resolve dynamic imports or private methods reached only
through runtime object dispatch. Public call boundaries are still covered.
CodeGraph was not initialized in this checkout, so this slice used the AST
source graph and records that limit explicitly.

Current checkpoint state: checker and focused enforcement are verified
working. Repository-wide conformance remains not yet proven because 199
unapproved findings remain in the shared tree.
