# Five task shapes through one host interface

This probe asks Loop Engine to implement five functions through the same
inspect, replace, and run operations. The host controls the source file,
Docker execution, and independent comparisons. The task manifest supplies
the required behavior. No task name selects a branch in the core runtime.

| Task | Result | Fixed checks |
|---|---|---:|
| Duration utility | Integer seconds or `ValueError` | 10 |
| Sales aggregation | Grouped records with exact decimal totals | 32 |
| Dependency schedule | Earliest start and end times with validation | 19 |
| Schedule HTML | A complete escaped HTML document | 5 |
| Interval repair | Corrected existing source with unchanged caller input | 18 |

These are authored regression tasks. Some reproduce failures from earlier
Overnight integration attempts. They are not claimed to be unseen in model
training, and fixed feedback can guide repairs. The current 84 cases include
counterexamples discovered after earlier candidates passed smaller sets.
They are regression checks, not untouched holdouts. Nonfinite floats travel
through a fixed trusted constant codec with validated argument paths. Neither
the model nor a case can supply Python expressions to evaluate.

## Inspect the frozen plan

From a source checkout with the package installed:

```bash
python examples/25_host_runtime/generalization_probe.py
```

This prints the task population, effective prompts, evaluator identity,
source digests, provider route, and execution policy. It makes no model call
and writes no file.

Use repeated `--task` arguments for an explicit subset. A follow-up can name
`--parent-report` and `--selection-reason`; the report binds the prior file's
digest and preserves its recorded statuses. A failed or canceled attempt is
not replaced by a later successful one.

By default, a follow-up requires the exact previous task digest. When adding
independent counterexamples, supply `--allow-evaluator-revision` and an explicit
`--evaluation-revision-reason`. The binder permits changed evaluator fields
only when the full task semantics remain unchanged. It records both evaluator
digests, both case counts, and the reason.

`--reuse-parent-source` preserves prior work as a new run's unverified input.
It freezes a separate `seed-source.py` and provenance record before making the
working copy. Prior acceptance is never inherited. The previous source,
outcome, population, and task digests are checked; a changed binding refuses
before model dispatch.

## Run with a configured provider

The script uses `ollama_cloud / cloud.default / deepseek-v4-flash:0731` and the
exact known output-capacity record. It requires an available credential and
the pinned Python Docker image used by the host example. It does not download
an image or permit candidate network access.

Choose a work directory that does not exist:

```bash
python examples/25_host_runtime/generalization_probe.py \
  --work-dir /absolute/new/generalization-probe \
  --authorize-model-calls \
  --allow-source-to-model
```

The grant permits model calls and disclosure of the authored task, editable
implementation, and actual execution feedback. Expected answers and verifier
definitions stay with the host. The script adds no model-call, pass, or
total-token ceiling. Existing provider, context, sandbox, and runtime
supervision policies still apply.

Candidate code runs in a container with no network and a read-only workspace.
Only `solution.py` is editable through the host. Every replacement requires
the current source digest returned by `workspace_inspect`. The model does not
calculate a hash of new code for that field. A mismatch returns a known
no-write observation and fails verification. The host compares returned values
outside the candidate process and rechecks the source, task, and artifact identities
before confirming completion.

## Read the result

`population.json` freezes the selected tasks before execution. Each task
directory keeps its source, fixed task manifest, every execution observation,
and the public `SolveOutcome`. The HTML task also saves the returned document.
Incremental reports preserve completed and failed attempts if a later task
stops. `report.json` includes the original denominator, unstarted tasks,
model-call and token-accounting completeness, elapsed time, and unknown cost.
An interrupted provider call can leave unknown usage. Known subtotals are not
complete totals. Failure-only diagnostic notes explain the violated contract
without disclosing the host's expected answer; passing cases reveal no note.

A passing result covers the saved cases. It does not establish arbitrary Jira
ticket resolution, an unattended scheduler, general recursive planning,
cross-task learning, or a full-system benchmark. An Overnight adapter must
retain its own worktree policy, protected repository gates, privacy rules,
and human review of proposals. The [host API guide](../../docs/guides/embedding-loop-engine.md)
describes that ownership boundary.

## Check the host fixture without a provider

```bash
python -m unittest discover \
  -s examples/25_host_runtime -p test_generalization_probe.py
```

The tests use authored reference solutions and local fixture execution. They
test stale sources, protected paths, invalid observations, wrong outputs,
HTML injection and generator-shaped output, exact arithmetic beyond fixed
precision limits, evaluator revisions, unverified source reuse, and changed artifacts.
They do not count as live model or Docker integration evidence.

The [dated verification report](../../docs/verification/ADAPTIVE-HOST-GENERALIZATION-2026-09-06.md)
keeps the original failures, later invalidations, and repair outcomes separate.
