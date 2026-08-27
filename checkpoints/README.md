# Development checkpoints

Dated, versioned snapshots of the entire system state. Each checkpoint
captures the architecture, tests, conformance, and evidence at one
moment so any later session can reconstruct exactly what existed.

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

## Create a checkpoint

```bash
python3 tools/make_checkpoint.py <slug>
```

The script captures everything automatically. Checkpoints are
committed; they are evidence, not generated debris.
