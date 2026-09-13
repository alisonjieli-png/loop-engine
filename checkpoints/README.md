# Development checkpoints

Dated, versioned snapshots of the entire system state. Each checkpoint
captures the architecture, tests, conformance, and evidence at one
moment so any later session can reconstruct exactly what existed.

These are historical records, not current status or instructions to rerun a
campaign. Preserve their recorded revisions and failed checks. The current
session entry point is [START-HERE.md](../docs/context/START-HERE.md).

## Layout

```text
checkpoints/
├── README.md
└── <date>-<slug>/
    ├── SNAPSHOT.md          human-readable system summary
    ├── state.json           machine-readable state
    ├── tree.txt             full repository tree
    ├── test-report.json     self-test results
    ├── conformance.json     conformance gate results
    └── git-state.txt        branch, commit, and dirty state
```

## Checkpoint helper

`tools/make_checkpoint.py` writes the layout above. Inspection on September
13, 2026 found that it expected the old self-test output shape, combined
command output without preserving return codes, allowed an existing target
directory, and listed a `conformance.json` file that it did not write. Its
tracked-file listing was not a complete snapshot of a dirty workspace, and
its slug was not path-confined.

The helper was repaired and tested the same day. It now parses the JSON
self-test summary from standard output and records a parse failure with the
return code and output tails instead of a placeholder; keeps the return
code, output, and launch error of every command it runs; refuses an existing
target directory and a slug that is not confined to the checkpoints
directory before any suite runs; writes `conformance.json` from the manifest
the conformance run produced during this run and refuses an older manifest;
and lists untracked files in `untracked.txt` next to the tracked listing.
Refusals exit with code 2, a failed suite with code 1, and a passing run
with code 0. `--dry-run` prints the plan without running or writing.
`tools/test_make_checkpoint.py` covers these behaviors. Read the module
docstring for the flags.

This repair does not change historical checkpoint files. Generated
structured records must use DuckDB or an established managed writer. The
helper preserves command return codes, exact source identities, failed
attempts, exclusive output creation, and path confinement. It does not
create another Run History store.

Existing committed checkpoints remain evidence. Creating a new checkpoint
does not authorize committing or publishing it.
