# In-process native Loops

Status: `mechanism_implemented`. Runtime type: `Loop`.

Minimum placement overhead; no process isolation.

Trusted deterministic workloads only. Model-quality comparison remains a separate qualification.

This folder is an independent launch surface. It shares task contracts, evaluator and canonical runtime with the other embodiments so comparisons remain meaningful. Its state and run artifacts live only in the output directory you select.

Run from the repository root:

```bash
python3 embodiments/native/run.py run --study /absolute/study --out /absolute/new-run --seconds 60 --concurrency 2
```

The current backend uses real deterministic computations and real process/worker placement. It does not simulate a successful model call or claim OpenCode compatibility.

See [the comparison index](../README.md), [architecture contract](../ARCHITECTURE.md), and [research and build plans](../../artifacts/review-2026-09-07/README.md).
