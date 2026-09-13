# Durable reactive activation

Status: `mechanism_implemented`. Runtime type: `Loop`.

Canonical SQLite scheduling, fencing, worker execution and persisted Run History.

Pure deterministic activations only; external-effect resume needs additional qualification.

This folder is an independent launch surface. It shares task contracts, evaluator and canonical runtime with the other embodiments so comparisons remain meaningful. Its state and run artifacts live only in the output directory you select.

Run from the repository root:

```bash
python3 embodiments/durable_reactive/run.py run --study /absolute/study --out /absolute/new-run --seconds 60 --concurrency 2
```

The current backend uses real deterministic computations and real process/worker placement. It does not simulate a successful model call or claim OpenCode compatibility.

See [the comparison index](../README.md), [architecture contract](../ARCHITECTURE.md), and [research and build plans](../../artifacts/review-2026-09-07/README.md).
