# Loop Engine Kaggle notebooks

Single-cell Kaggle notebooks. Paste one file into one notebook cell and run
it. Each cell is fully self-contained: it downloads Loop Engine `main`,
installs it, checks the providers, solves the sample competition task, and
saves the artifacts. The same cells run outside Kaggle through the local
harness described below, so every fix can be tested before it is pasted.

## Choosing a notebook

| Notebook | Providers | Best for | Kaggle secrets required |
|---|---|---|---|
| [01 quickstart](01_quickstart_ollama.py) | Ollama Cloud only | First run, smallest surface, fastest to debug | `ollama_kaggle_key` |
| [02 tacticalengineering only](02_tacticalengineering_only.py) | Your private tacticalengineering gateway | Long runs on your own GPU box, wall-clock deadline, deepest logging | `tacticalhat_kaggle_key` |
| [03 three-provider failover](03_three_provider_failover.py) | Ollama Cloud, tacticalengineering, Mistral | Maximum resilience: the run continues when any one provider fails | `ollama_kaggle_key`, `mistral_kaggle_key`, `tacticalhat_kaggle_key` |

All three solve the same task: a reproducible baseline for the competition
files attached to the notebook (Playground Series S6E9 by default). Change
`LOOP_ENGINE_KAGGLE_COMPETITION` or the configuration block and the task
text to solve a different competition.

## What every notebook does

Competition data: the cells make no assumption about where the data sits or
what the files are called. Each hands the whole attached input root to the
solve, prints what is in it, and stops at the solve stage when nothing is
attached. The Practitioner requests the source manifest, reads the exact
admitted paths the runtime states, and works out from the observed schemas
which files hold training rows, which hold rows to predict, and which defines
the submission contract. That means a cell runs against any competition or
dataset you attach, whatever its slug, layout, or file names. Set
`LOOP_ENGINE_KAGGLE_DATASET_DIR` if you want to narrow the root yourself.

Notebook settings on Kaggle: Internet must be on (each cell downloads the
Loop Engine `main` archive from GitHub and calls the provider API), no
accelerator is required, and the provider key is read from a Kaggle secret
named in the cell header. Generated code runs as a host process with
`--allow-local-execution` because Kaggle notebooks have no Docker.

```text
one cell
├── reads Kaggle secrets (never printed, never written to files)
├── removes the previous checkout and stale workspaces (Run History is kept)
├── downloads and pip-installs current main
├── doctor + configure (offline, zero provider calls)
├── preflight: one authorized probe per provider, recorded AFTER it runs
├── solves with exact prompt and model-output tracing on stderr
├── copies verified artifacts to a stable solutions directory
└── writes a stage record saying what it did and where it stopped
```

## Output locations

All three notebooks write under the Kaggle working directory using the same
two roots, `loop-engine-logs/` and `loop-engine-solutions/`.

| Path | Contents | 01 | 02 | 03 |
|---|---|---|---|---|
| `loop-engine-solutions/attempt-<stamp>/` | solution.py, submission.csv, metrics.json, report.md, verification.json | yes | yes | yes |
| `loop-engine-solutions/BEST.txt`, `index.json` | pointer to the best attempt and an artifact index | | yes | |
| `loop-engine-logs/stage-<stamp>.json` | what the cell did: install mode, doctor/configure exit codes, preflight result, terminal code | yes | yes | yes |
| `loop-engine-logs/preflight/preflight-<stamp>.json` | provider API check record with one `ok` flag and exit code per provider | yes | yes | yes |
| `loop-engine-logs/solve/solve-stdout-<stamp>.json` | the final solve record (`.jsonl` in 02) | yes | yes | yes |
| `loop-engine-logs/solve/solve-stderr-<stamp>.log` | the full stderr trace with exact model IO | | yes | |
| `loop-engine-logs/run-history/` | Loop Engine Run History (replay, reports, studio); never deleted by the cells | yes | yes | yes |
| `loop-engine-logs/summary/` | `summary-<stamp>.md` (02) or `final-report-<stamp>.md` (03), one page per attempt | | yes | yes |
| `loop-engine-logs/master/master-<stamp>.log` | chronological master log | | yes | |
| `loop-engine-providers.yaml` | the settings file the solve reads (no key values) | | yes | yes |
| `loop-engine-<competition>-task.md` | the task text given to the solve | yes | yes | yes |

Inspect any run after the cell finishes:

```bash
loop-engine report <run-id> --runs-dir /kaggle/working/loop-engine-logs/run-history
loop-engine studio --port 0 --runs-dir /kaggle/working/loop-engine-logs/run-history
```

## Running the cells outside Kaggle

Every path and name a cell uses sits in one configuration block at the top
of the file. On Kaggle the defaults apply unchanged. Elsewhere these
variables redirect the cell:

| Variable | Default | Meaning |
|---|---|---|
| `LOOP_ENGINE_KAGGLE_WORKING` | `/kaggle/working` | output root |
| `LOOP_ENGINE_KAGGLE_INPUT` | `/kaggle/input` | dataset root; the competition lives at `<input>/competitions/<competition>` |
| `LOOP_ENGINE_KAGGLE_TEMP` | `/kaggle/temp` | scratch space for the downloaded archive |
| `LOOP_ENGINE_KAGGLE_COMPETITION` | `playground-series-s6e9` | competition slug |
| `LOOP_ENGINE_SOURCE_DIR` | unset | when set, this checkout is installed instead of downloading `main.zip`; the checkout is never deleted |
| `LOOP_ENGINE_KAGGLE_STAGE` | `solve` | `offline` stops after doctor/configure, `preflight` stops after the provider probes, `solve` is the full run |
| `LOOP_ENGINE_TACTICAL_BASE_URL` | `https://ai.tacticalengineering.net:6969/v1/chat/completions` | the private endpoint (02, 03); the `/v1` base or the full URL |
| `LOOP_ENGINE_TACTICAL_MODEL` | `gemma-4-coding-abliterated` | model id on that endpoint (02, 03) |
| `LOOP_ENGINE_KAGGLE_DEADLINE_SECONDS` | `18000` (5 hours) | wall-clock budget of the solve phase in notebook 02; the harness shortens it to test the deadline path |

Secrets are read from `kaggle_secrets` first. When that module is missing or
the secret is not attached, the cell falls back to an environment variable
with the secret's upper-cased name (`OLLAMA_KAGGLE_KEY`,
`MISTRAL_KAGGLE_KEY`, `TACTICALHAT_KAGGLE_KEY`) and then to the provider's
standard variable (`OLLAMA_API_KEY`, `MISTRAL_API_KEY`, `TACTICAL_API_KEY`).
Key values only ever enter the environment of the child processes; they are
never printed and never written to a file.

A notebook pushed through the Kaggle API (`kaggle kernels push`) does not
inherit secret access. Kaggle grants a secret to a notebook in the editor,
under *Add-ons -> Secrets*, and a version created by the API starts without
that grant, so the cell reports the secret as unavailable and stops. Open the
notebook once in the editor and attach the secrets it names, or set the
matching environment variable in the first cell. This is a Kaggle behaviour,
not something the cell can work around.

With `LOOP_ENGINE_SOURCE_DIR` set the cell runs `pip install --editable` on
that checkout when pip is available in the interpreter. In a pip-less
virtual environment (for example one created by `uv`) it runs the CLI from
the checkout's `src` tree through `PYTHONPATH` instead and records
`install_mode: pythonpath` in the stage record.

### Local test harness

The harness writes a tiny synthetic competition. `--competition-kind binary`
(the default) has a 0/1 target, `regression` a continuous target, and
`multiclass` a three-label string target, so the same cell can be exercised
against three submission contracts without a Kaggle download.

`check_cells.py` builds a temporary Kaggle-shaped root
(`<tmp>/working-<cell>`, `<tmp>/input/competitions/<competition>/` with a
deterministic 200-row synthetic binary-classification dataset: an id column,
six numeric columns, a `target`), sets the variables above with
`LOOP_ENGINE_SOURCE_DIR` pointing at this checkout, runs the chosen cell as
a subprocess, and checks what the stage must leave behind:

```bash
source .venv/bin/activate
python kaggle/check_cells.py --cell 01 --stage offline   # default stage
python kaggle/check_cells.py --cell all --stage offline  # no key, no network
python kaggle/check_cells.py --cell 02 --stage preflight # needs TACTICALHAT_KAGGLE_KEY or TACTICAL_API_KEY
python kaggle/check_cells.py --cell 03 --stage solve --verbose --keep
```

To exercise notebook 02's deadline path locally, shorten the budget and
point the endpoint at a slow server you control, for example
`LOOP_ENGINE_KAGGLE_DEADLINE_SECONDS=20`; the summary then records the
stop level that was needed.

| Stage | Checks |
|---|---|
| `offline` | cell exit 0; stage record says `offline`; `doctor` and `configure` exit 0; the doctor banner appeared |
| `preflight` | the above, plus a preflight record with a boolean `ok` per provider and at least one provider ok |
| `solve` | the above, plus an `outcome.json` under `run-history/` or a typed terminal code in the solve record |

The offline stage removes every provider variable from the child's
environment, so it needs no key and makes no network call. The preflight and
solve stages refuse with exit code 2 when the keys the chosen cell needs are
missing; nothing is fabricated. `--keep` keeps the temporary root (a failing
run always keeps it), `--verbose` streams the cell output, `--root DIR`
places the temporary root under `DIR`.

## Provider notes

- **Ollama Cloud**: probed through the built-in `models probe` with one
  authorized call. Model output ceilings are seeded from provider
  observations, so no per-notebook declarations are needed.
- **Mistral**: small (8,192) and large (16,384) output ceilings are seeded
  from Mistral platform documentation. Both routes enter failover
  automatically.
- **tacticalengineering** (notebooks 02 and 03): a **private endpoint**
  operated by the notebook owner, reached as a direct-origin
  OpenAI-compatible API on port 6969. The hostname is DNS-only and serves a
  Cloudflare Origin CA certificate, so the endpoint declares
  `tls_verification: skip` (the typed equivalent of `curl -k`, scoped to
  exactly this endpoint) and `stream: auto` (retries with SSE streaming if a
  proxy ever cuts a long generation). `tls_verification: ca_file` together
  with `tls_ca_file: <path to the Cloudflare Origin CA root>` is now
  supported and is the preferred setting whenever that root file is
  available on the notebook. The declared output ceiling is the gemma-4
  published 32,768 tokens; it is declared, not measured by these notebooks.
  Requests identify themselves honestly (`Loop-Engine-Kaggle` for the solve,
  `Loop-Engine-Kaggle-Preflight` for the raw probe); no browser User-Agent is
  spoofed. `--compile-provider tacticalengineering` names the provider id
  declared in the settings file, and its `credential_env`
  (`TACTICAL_API_KEY`) is the variable the key travels through.

## Honest behavior to expect

- The solve ends in `COMPLETED_VERIFIED` with artifacts, or in a typed
  honest terminal (`CAPABILITY_GAP`, `PROVIDER_UNAVAILABLE`,
  `VERIFICATION_FAILED`, `CANCELLED`, or a non-progress stop with the exact
  reason).
- Kaggle has no Docker, so every `loop-engine solve` in these cells passes
  `--allow-local-execution`: generated code runs as a host process with the
  preinstalled packages and the run record labels the weaker isolation.
  Without the flag the runtime refuses host execution. `--allow-source-to-model`
  stays on so the dataset text may enter the model context.
- Dependency-install network commands are refused by design and recorded as
  typed failures.
- The non-progress escalation ladder bounds stuck runs: soft reset, then
  cold restart with failure memory, then an honest stop.
- Notebook 02 additionally enforces a wall-clock deadline (default 5 hours).
  At the deadline it sends `SIGINT` to the solve, which the CLI turns into an
  honest `CANCELLED` outcome with its Run History written, waits up to 180
  seconds, and only then escalates to `terminate()` and finally `kill()`.
  The summary and the artifact index record which level was needed.
- Preflight probes never abort a cell before their result is recorded. Each
  provider's `ok` is decided from the probe's exit code after it ran, the
  preflight record is always written, notebook 03 continues when at least
  one provider answered, and notebooks 01 and 02 stop with a clear message
  when their single provider did not.
- No token ceiling is set by default. `--context-budget-tokens` is available
  as an operator ceiling for the estimated input of one model call if you
  want one; the cells do not set it.

## Limitations

- The tacticalengineering endpoint is a private server; its preflight may
  fail if the origin is down or its configuration changes. Notebook 03
  continues on the remaining providers when one fails preflight; notebooks
  01 and 02 stop before spending the time budget.
- The local harness proves the cell logic (configuration, install, doctor,
  configure, preflight recording, stage stops). Stages `preflight` and
  `solve` still need live provider keys and network access; nothing in the
  harness stands in for a provider.
- Loop Engine is 0.1.0 alpha software: the notebooks prove the product
  circuit, not guaranteed competition accuracy.
