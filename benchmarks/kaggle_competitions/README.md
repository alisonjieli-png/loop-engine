# Kaggle competitions: does the same engine generalize across shapes?

One competition tells you whether the engine can solve that competition.
Several tell you whether it generalizes, which is a different question and the
only one worth asking of a universal solver.

This benchmark runs the same unmodified Practitioner against several real
competitions and reports them side by side. The Practitioner is told nothing
about any of them beyond the task text and a read-only dataset directory. It
must discover the target, the identifier, the task type and the submission
contract from the files.

## The rubric is read independently

`contract.py` reads the same files and states what the answer was. It is a
grader, never an input. The rule it uses is the one the data supports: the
target is the column present in the training file and absent from the
prediction file, confirmed against the column the sample submission asks for.

That rule is not the obvious one, and the obvious one is wrong. In
`playground-series-s6e7` the target `health_condition` is the second of
fifteen training columns, and the last training column, `gender`, is a feature
that also appears in test. Anything taking the final column as the target
trains on a feature and can still emit a submission of exactly the right
shape.

The rubric also names contract traps it can establish from the files alone:

- a target that is not the last training column;
- blank values in the target column;
- training labels and submission values of different kinds;
- a sample submission holding a value the target never takes, which means the
  contract wants a score rather than a label.

Values are compared as values. A target of `0.0` and a sample of `0` are the
same label written twice, and reporting that as a trap would send a reader
looking for a defect that is not there.

## Discovery and execution are counted apart

`compare.py` reports what each run discovered separately from what it
produced. A run that identified the right target and failed to execute has
shown something different from one that ran cleanly on the wrong column, and
collapsing both into pass or fail destroys the distinction that matters most
when the question is generalization.

Every submission is described by its rows, its distinct-value count and its
range. A submission whose predictions never vary is reported as one.

## Running it

Download a competition with the Kaggle CLI, then solve it with a live route:

```bash
kaggle competitions download -c <competition> -p <data-dir>
unzip -q '<data-dir>/*.zip' -d <data-dir>

PYTHONPATH=src python3 -m loop_engine solve \
  --file <task-file> \
  --dataset <data-dir> \
  --workspace <workspace> \
  --runs-dir <runs> \
  --compile-provider ollama_cloud \
  --provider-key-env OLLAMA_API_KEY \
  --model-route cloud.default \
  --authorize-model-calls --allow-source-to-model --allow-local-execution \
  --max-passes 40 --format json
```

Then compare:

```bash
PYTHONPATH=src:benchmarks/kaggle_competitions python3 -c "
from compare import read_result, compare_competitions, render_table
results = [read_result(name, data_dir, run_root) for ...]
print(render_table(compare_competitions(results)))"
```

## What this does not establish

A submission produced and verified for schema, row count, column order and
identifier coverage is not a score. None of these submissions has been
submitted, so nothing here says how any of them ranks. Local
cross-validated figures are local.
