# One long-lived worker session

Status: `mechanism_implemented`. Runtime type: `Loop`.

Startup is amortized; every packet still creates a fresh Loop and explicit state.

A process restart loses in-flight work; no provider caching benefit is claimed.

This folder is an independent launch surface. It shares task contracts, evaluator and canonical runtime with the other embodiments so comparisons remain meaningful. Its state and run artifacts live only in the output directory you select.

Run from the repository root:

```bash
python3 embodiments/long_lived_session/run.py run --study /absolute/study --out /absolute/new-run --seconds 60 --concurrency 2
```

The current backend uses real deterministic computations and real process/worker placement. It does not simulate a successful model call or claim OpenCode compatibility.

See [the comparison index](../README.md), [architecture contract](../ARCHITECTURE.md), and [research and build plans](../../artifacts/review-2026-09-07/README.md).
