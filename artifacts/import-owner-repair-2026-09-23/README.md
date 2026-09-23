# Import ownership and class adapter evidence

The integration checkout was only read. A detached checkout reproduced its tracked
working diff and untracked tool files; `integration-baseline.json` pins that snapshot.
`source-bindings.json` gives the exact eight-file delta for integration.

- `combined-before.txt`: parent's exact 69-test command, one exception identity error.
- `new-controls-before.txt`: initial import-order/class controls; the unavailable-source
  fixture initially failed at ProviderSpec validation and was corrected separately.
- `unavailable-source-control-before.txt`: valid adapter with unavailable source,
  failing at the intended reflection boundary before repair.
- `staging-import-control-before.txt`: both import orders expose duplicate staging class.
- `module-launch-control-before.txt`: `python -m` native refusal exposes duplicate
  preparation class and traceback before launcher repair.
- `combined-after-first-repair.txt`, `combined-final.txt`, `combined-frozen.txt`:
  intermediate green 72-test successors, preserved.
- `combined-final-module-launch.txt`: final combined 72-test run, including module CLI.
- `adjacent-after.txt`: 46 ingestion/native review tests pass.
- `outside-repository-cli.json`: five help commands and native review refusal.
- `check_removed_class_hash_guards.py`, `removed-class-hash-guards.json`: three
  fixed in-memory mutations; every removed guard fails a named owning test.
- `ruff-delta-first.json`, `ruff-delta-final.json`: introduced import formatting
  findings were repaired; final delta introduces no diagnostics.

No model or provider calls occurred. No package was approved or published.
