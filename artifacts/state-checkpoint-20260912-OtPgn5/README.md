# Current-state checkpoint evidence

The [architecture and state report](../../docs/research/COGNITIVE-STEP-ARCHITECTURE-AND-STATE-2026-09-12.md)
is the readable checkpoint. This directory holds its local, derived evidence
projection. It does not create a product store, managed record collection, or
execution authority.

## Contents

| File | Purpose |
|---|---|
| [snapshot.py](snapshot.py) | Reads saved results and source identities; creates a fresh projection and refuses overwrite |
| [checkpoint.duckdb](checkpoint.duckdb) | Queryable metadata, dirty paths, source digests, 80 legacy cells, six cognitive-act cells, factor counts, and saved QA results |
| [checkpoint.json](checkpoint.json) | DuckDB-exported aggregate checkpoint with its observation time |
| [source-manifest.json](source-manifest.json) | DuckDB-exported identities for principal source documents and evidence files |
| [verify.py](verify.py) | Checks local citations, source stability, numerical claims, and report vocabulary without executing the engine |

All 472 production Python files matched the source used for the final checked
wheel. The saved installed suite reports 3,839/3,839 and 27/27 conformance
gates. The six cognitive-act task runs have 202 known physical calls, zero
sealed passes, nine recovery rounds, and zero reusable candidates. Three
model-call totals remain unknown. The legacy projection contains 80 saved
cells and eight task identities; the newer task increases the scoped distinct
task count to nine.

## Scope and reproducibility

The snapshot script reads source and saved evidence. It makes no model calls,
does not execute task or evaluator code, and does not rewrite canonical
histories. The six history-verification results are imported from the cited
recovery summary, whose builder verified their chains and learning artifacts.
This documentation pass did not rerun those campaigns or the full test suite.

The process observation examines argument tokens for the named campaign
markers but retains no arguments, environment values, credentials, or private
prompt bodies. It found no matching campaign process. This does not establish
ownership of other sessions or prove that the machine is idle.

The snapshot is intentionally fixed. Running `snapshot.py` again in this
directory refuses to overwrite it. A later checkpoint needs a new artifact
directory and an explicit source comparison. The generated database and JSON
remain local and are ignored by this directory's Git rules.

The separate documentation check creates `validation.duckdb` and
`validation.json`, including report digests. It also refuses overwrite. Its
checks are not additions to the runtime's 3,839-test denominator.

Read-only examples, after opening `checkpoint.duckdb` with DuckDB:

```sql
SELECT task, count(*) AS saved_cells
FROM legacy_cells GROUP BY task ORDER BY task;

SELECT study, harness_id, engine_terminal,
       model_calls, model_calls_known_subtotal, heldout_passed
FROM cognitive_cells ORDER BY study, harness_id;

SELECT * FROM runtime_sources WHERE NOT matches;

SELECT * FROM factor_counts ORDER BY factor;
```

Historical reports and their corrections remain in place. No reference
directory, source tree, or saved attempt was removed for this checkpoint.
