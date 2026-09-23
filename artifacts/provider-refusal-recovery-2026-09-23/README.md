# Provider refusal recovery evidence

No actual model/provider requests. Every response comes from an in-process fixture.

- `trial-state-before.json`, `trial-json-evidence-before.json`, `owning-case-before.txt`:
  reproduced HTML refusal becoming NO_PROGRESS and uncertain accounting.
- `focused-before.txt`: a failed call with unknown model could not be represented.
- `focused-first-repair.txt`: owning regression and initial boundary controls pass.
- `focused-authority-after.txt`, `focused-authority-final.txt`: new fixture initially
  lacked an artifact manager, then expected the inner provider code at the outer
  adapter normalization layer. These setup failures are preserved.
- `focused-authority-final-2.txt`, `focused-complete-final.txt`: corrected controls,
  including actual unapproved requested-model refusal and unknown semantic identity.
- `embodiment-after.txt`, `embodiment-frozen.txt`: all 106 owning tests pass.
- `owning-boundaries-after.json`: 211 focused component controls pass.
- `identity-and-recovery-final.txt`: 11 identity/recovery unit cases pass.
- `check_removed_guards.py`, `removed-guards.txt`: four fixed in-memory faults;
  trial progress events precede the final JSON fault-control report.
- `source-bindings.json`, Ruff delta reports: exact final source bytes and diagnostics.

Initial use of the review virtual environment failed import because DuckDB was absent.
The already-existing `/home/username/.le-wave2/mcp-revision/.venv-mcp2/bin/python`
used by the parent's failed CI then ran all checks. No installation occurred.
