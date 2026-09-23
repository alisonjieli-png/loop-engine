# Handoff: overnight batch with a cheap model, September 23, 2026

Kind: work in progress handoff for one line of work. It records what was
done in the detached worktree `/home/username/.le-integration/overnight`,
based on `main` at `243a8811`, what is left, every check and every external
effect. The owner asked the session to stop here and hand over. No model run
was started after that request.

## The task

Run Baltor's first overnight-style proof with a cheap model, as the owner
asked on September 23, 2026: bring your own endpoint and key, use Ollama
Cloud and a model such as Gemma 4, build on the
[data cleanup study](../../case-studies/data-cleanup-with-and-without-baltor/README.md),
freeze the design before any counted call, run an unattended batch that
resumes after an interruption, and write a dated report. Authority: model
calls through Ollama Cloud with the key already in the environment, within
the owner's subscription, at most 600 requests, every call recorded. No push,
deployment or branch.

## What is done

- Model chosen: `gemma4:31b`, the only Gemma 4 model that Ollama Cloud lists.
  A three-request probe through the Pi harness showed structured tool calls
  (`bash`, then `write`), the answer file written, usage on every request.
- Study folder written and frozen:
  [case-studies/overnight-cheap-model-with-and-without-baltor/](../../case-studies/overnight-cheap-model-with-and-without-baltor/README.md).
  The [design](../../case-studies/overnight-cheap-model-with-and-without-baltor/DESIGN.md)
  is frozen by `design-freeze.json` (67 files). `design.json` SHA-256:
  `9d711a2d895869a1870efdfcd0289ec4db578d02e40a0fb2d984a6978c16bc80`.
  `design-freeze.json` SHA-256:
  `9129c9a648931a9d062f277417c9408abc24e79db6e9b7f6058c21c593a42b06`.
- Population: 311 rows in six families (phones 62, emails 57, addresses 48,
  duplicates 59 records, names 53, websites 32). The phones, emails and
  duplicates prompts are the same bytes as in the data cleanup study.
- Material: the seven approved items that the catalogue's own search fixtures
  name for the six step queries, copied byte for byte into `material/` with
  their approval rows.
- Item method reference with no model: the repository operation behind each
  item, run on every row, scores 0.5366 to 0.8438 and passes no family. Its
  per-row labels show where each item's own method gives the truth.
- Unattended runner: leases, crash recovery that stops a left-over harness
  and records the interrupted attempt, a supervisor (`runner/overnight.sh`)
  that restarts the runner, and a declared drill that kills the runner once
  during step `r1-addresses-gemma-none`.
- Proxy: forwards to `https://ollama.com/v1` with the key read from
  `OLLAMA_API_KEY` at send time; the key is never written anywhere.
- Frozen analysis `runner/summarize.py` with the claim rules and tests.
- 120 owned entries in `devtools/hardcoding-allowlist.yaml` for literals of
  the frozen study code and data, in the same form as the data cleanup study.

## Every model call so far

Three physical model requests, all in the probe of 13:13:00 to 13:13:04 UTC
(09:13 United States Eastern time), all counted in
`trials/requests.jsonl`. Request and response bodies are in
`probe/probe-bodies.tar.gz`.

| Sequence | Model | Outcome | Finish | Tool call | Prompt tokens | Completion tokens | Cached prompt tokens | Milliseconds | Provider request id |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `gemma4:31b` | HTTP 200, ok | tool_calls | bash | 1,362 | 24 | 0 | 803 | `25715da1-b578-4ef9-ac4a-3e0b92a9038d` |
| 2 | `gemma4:31b` | HTTP 200, ok | tool_calls | write | 1,395 | 27 | 1,344 | 786 | `0f081581-5474-4cf2-8c5a-ac25305d26b7` |
| 3 | `gemma4:31b` | HTTP 200, ok | stop | none | 1,437 | 6 | 1,376 | 537 | `2f3c8c1e-0113-4ed3-9353-88bbed20eabc` |

Totals: 3 of the 600 allowed requests, 4,194 prompt tokens, 57 completion
tokens, 2,720 of them cached. Cost: covered by the existing subscription and
not metered for each request.

## Other external effects

- Six metadata requests to Ollama Cloud, not model calls and not counted:
  `GET /api/tags`, `GET /v1/models`, and `POST /api/show` four times (once for
  `gemma4:31b`, then for `gemma4:31b`, `nemotron-3-nano:30b` and
  `gpt-oss:20b`). The saved result is `probe/ollama-model-metadata.json`.
- One web page read: the Wikipedia article on fictitious telephone numbers,
  to confirm the ranges used in the population.
- Files outside the repository, all under `/home/username/.le-ci-tmp/`:
  `overnight-study/run-1` (probe run folder and bodies),
  `overnight-study/capture`, `overnight-probe`, `overnight-tests`,
  `overnight-mutants` and `overnight-gates`.
- One detached worktree, `/home/username/.le-integration/overnight`. No
  branch was created. Nothing was pushed, deployed or published.

## Checks run and their results

| Check | Result |
|---|---|
| `python population/generate_population.py --check` | pass |
| `PYTHONPATH=src python case-studies/overnight-cheap-model-with-and-without-baltor/runner/item_reference.py --check` | pass |
| scorer tests (`scorer/test_score_step.py`) | 26 of 26 pass |
| proxy tests (`runner/test_meter.py`) | 10 of 10 pass |
| runner tests (`runner/test_runner.py`), including an end-to-end drill with the real Pi harness against a scripted provider | 15 of 15 pass |
| `python runner/freeze.py --check --catalogue` | pass; the catalogue still approves all seven items at the frozen digests |
| capture check with no model (`run_trials.py capture`) | pass: the item text reaches the system prompt only in the material arm; no text from the owner's instruction files |
| mutants of the new guards, on a throwaway copy | 11 of 11 fail their named check |
| `pyflakes` on the study code | clean |
| `markdownlint-cli2@0.23.2` on the changed Markdown files | 0 issues |
| retired-language searches of the CI workflow on the new files | no match |
| hardcoding audit with `--fail-on-new high` | exit 0 after the 120 entries (high findings 632, the baseline count) |
| `python -m loop_engine --conformance` | all gates pass |
| tools tests (`PYTHONPATH=src:tools python -m unittest discover -s tools -p 'test_*.py'`) | 848 run, 5 fail, all in `test_check_harness_fresh_instances.py`; the same 5 fail on a clean export of `main` at `ca739e13` on this workstation, so they predate this work |
| Vale and the lychee link check | not run: neither is installed here; relative links of the changed files were checked with a script |

## Known failures and findings

1. The data cleanup study's own `runner/freeze.py --check` fails on `main`:
   the catalogue re-anchored the five item bodies it froze, a change of the
   last line only. This study copies the item bytes instead. The earlier
   study's record was not edited.
2. Found and fixed before the freeze: the runner's first liveness check
   counted a killed but uncollected process as still running, which would
   have stopped the batch after a crash. The check now reads the process
   state, and a test and a mutant cover it.
3. Pi exits with code 0 after a provider error; the runner decides a step's
   status from the proxy ledger, not from the exit code.
4. The three probe ledger lines carry the provider address; the frozen proxy
   no longer repeats it, so the main run adds no such audit findings.
5. The probe ran with the runner and proxy as they were before the freeze;
   the probe record keeps their digests.

## What is left, in order

Run from `case-studies/overnight-cheap-model-with-and-without-baltor/` in the
worktree, with `OLLAMA_API_KEY` in the environment.

1. Pilot, two steps, excluded from results:
   `python3 runner/run_trials.py pilot --run-folder /home/username/.le-ci-tmp/overnight-study/run-1`.
   Only plumbing may change after it, recorded in `amendments.json` with
   digests before and after; `python3 runner/freeze.py --check` must pass.
2. Commit the pilot records.
3. Unattended batch, 36 steps plus the drill's repeat, in the background:
   `runner/overnight.sh /home/username/.le-ci-tmp/overnight-study/run-1`.
   Expect the runner to kill itself once during `r1-addresses-gemma-none`
   and the supervisor to restart it after 30 seconds.
4. Copy `main.log`, `supervisor.log` and `drill-fired.json` from the run
   folder into `trials/run-logs/`. Check that no body holds the key, then
   archive the bodies as `trials/request-bodies.tar.gz`.
5. `python3 runner/summarize.py` and
   `python3 runner/use_signals.py --bodies /home/username/.le-ci-tmp/overnight-study/run-1/bodies`.
6. Scan the recorded tool calls for paths outside each step folder and for
   any read of a truth file, as section 8 of the design requires.
7. Write the dated report beside the design, with exact denominators, every
   failure, tokens and requests, elapsed time and the claim decision, and
   update the study README status.
8. Run the gates again (study tests, freeze check, Markdown lint, hardcoding
   audit, conformance, tools tests, records index) and commit.

## Safe to merge

The commit adds a frozen, tested design and no result. Every check of the
table above passes except the five tools tests that fail the same way on
clean `main` here. Vale and the link check ran only in CI form, not locally.
