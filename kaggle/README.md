# Loop Engine Kaggle notebooks

Single-cell Kaggle notebooks. Paste one file into one notebook cell and run
it. Each cell is fully self-contained: it downloads Loop Engine `main`,
installs it, checks the providers, solves the sample competition task, and
saves the artifacts.

## Choosing a notebook

| Notebook | Providers | Best for | Kaggle secrets required |
|---|---|---|---|
| [01 quickstart](01_quickstart_ollama.py) | Ollama Cloud only | First run, smallest surface, fastest to debug | `ollama_kaggle_key` |
| [02 tacticalengineering only](02_tacticalengineering_only.py) | Your self-hosted TensorRT gateway | Long runs on your own GPU box, wall-clock deadline, deepest logging | `tacticalhat_kaggle_key` |
| [03 three-provider failover](03_three_provider_failover.py) | Ollama Cloud, tacticalengineering, Mistral | Maximum resilience: the run continues when any one provider fails | `ollama_kaggle_key`, `mistral_kaggle_key`, `tacticalhat_kaggle_key` |

All three solve the same task: a reproducible baseline for the Playground
Series S6E9 competition files attached to the notebook. Change
`DATASET_DIR` and the task text to solve a different competition.

## What every notebook does

```text
one cell
├── reads Kaggle secrets (never printed, never written to files)
├── removes previous checkouts and run debris (disk never fills)
├── downloads and pip-installs current main
├── doctor + configure (offline, zero provider calls)
├── preflight: one authorized probe per provider, typed records
├── solves with exact prompt and model-output tracing on stderr
└── copies verified artifacts to a stable solutions directory
```

## Output locations

| Path | Contents |
|---|---|
| `loop-engine-solutions/attempt-<stamp>/` | solution.py, submission.csv, metrics.json, report.md, verification.json |
| `loop-engine-logs/preflight/` | provider API check records |
| `loop-engine-logs/solve/` | final solve records and stderr traces |
| `loop-engine-logs/run-history/` | Loop Engine Run History (replay, reports, studio) |

Inspect any run after the cell finishes:

```bash
loop-engine report <run-id> --runs-dir /kaggle/working/loop-engine-logs/run-history
loop-engine studio --port 0 --runs-dir /kaggle/working/loop-engine-logs/run-history
```

## Provider notes

- **Ollama Cloud**: probed through the built-in `models probe` with one
  authorized call. Model output ceilings are seeded from provider
  observations, so no per-notebook declarations are needed.
- **Mistral**: small (8,192) and large (16,384) output ceilings are seeded
  from Mistral platform documentation. Both routes enter failover
  automatically.
- **tacticalengineering** (notebooks 02 and 03): the direct-origin
  OpenAI-compatible API on port 6969. The hostname is DNS-only and serves a
  Cloudflare Origin CA certificate, so the endpoint declares
  `tls_verification: skip` (the typed equivalent of `curl -k`, scoped to
  exactly this endpoint) and `stream: auto` (retries with SSE streaming if a
  proxy ever cuts a long generation). The declared output ceiling is the
  gemma-4 published 32,768, verified live with a full-generation probe.

## Honest behavior to expect

- The solve ends in `COMPLETED_VERIFIED` with artifacts, or in a typed
  honest terminal (`CAPABILITY_GAP`, `PROVIDER_UNAVAILABLE`,
  `VERIFICATION_FAILED`, or a non-progress stop with the exact reason).
- Kaggle has no Docker, so generated code runs in the restricted local
  backend with the preinstalled packages. Dependency-install network
  commands are refused by design and recorded as typed failures.
- The non-progress escalation ladder bounds stuck runs: soft reset, then
  cold restart with failure memory, then an honest stop.
- Notebook 02 additionally enforces a wall-clock deadline (default 5 hours)
  and stops honestly at the limit, saving everything completed so far.

## Limitations

- The tacticalengineering endpoint is a private server; its preflight may
  fail if the origin is down or its configuration changes. Notebook 03
  continues on the remaining providers when one fails preflight; notebook 02
  stops before spending the time budget.
- Loop Engine is 0.1.0 alpha software: the notebooks prove the product
  circuit, not guaranteed competition accuracy.
