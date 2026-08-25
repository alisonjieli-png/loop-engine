# DS-1000 four-task recorded-output correction

Status: `completed with corrected evaluation`

> **The first 2 of 4 score is invalidated and must not be cited as the
> benchmark result.** The evaluator adapter removed required leading
> whitespace. A zero-model-call correction of the exact recorded outputs passed
> all 4 tasks.

## Task and population

Loop Engine solved four public DS-1000 code-completion tasks from upstream
commit `b39aab71da6d23ef8d3cac59a7c5f834516ab334`. The population was frozen
before outcomes:

| Problem | Upstream library | Selected output |
|---:|---|---|
| 72 | Pandas | repair |
| 218 | Pandas | synthesis |
| 838 | Sklearn | synthesis |
| 896 | Sklearn | repair |

The independent evaluator was the pinned DS-1000 execution checker. A task
passed only when its upstream execution test and string test, when present,
passed inside the locked container. Higher execution accuracy is better.

## Full Loop Engine path

Each selected task started a Starting Practitioner in `non_deterministic` mode and
completed the registered nine-step profile:

```text
Starting Practitioner
|-- Context, Code, Previous Run, and User Feedback Intelligence searches
|-- candidate A model-led Practitioner
|-- candidate B model-led Practitioner
|-- synthesis model-led Practitioner
|-- compiled typed Solution Canvas
|-- isolated upstream evaluator
`-- one repair Practitioner after a completed evaluator failure
```

Every physical call used Ollama Cloud `deepseek-v4-flash:0731`, requested the
source-backed maximum output of 65,536 tokens, and had provider failover
disabled. The model never received upstream reference solutions, evaluator
bodies, or test code.

## Intelligence used

Before model decisions, the Starting Practitioner searched and materialized
all six admitted benchmark Code operations: source verification, task loading, safe code
extraction, isolated evaluation, upstream pass or fail interpretation, and
Canvas compilation and execution.

Every model-led spawned Loop then consumed a canonical seven-item portfolio
with one unique reference for each required family:

1. first principles;
2. alternatives and analogy;
3. missing information;
4. failure and adversarial review;
5. cost and resources;
6. verification and evaluation; and
7. output contract and format.

Each spawned Loop record binds the exact consumed references and digest.
Candidate A and candidate B used distinct portfolios. Active User Feedback Intelligence
and Runtime History and Solution Intelligence were present in every required model-led spawned
Loop.

## Solution Canvas and isolation

The selected code completion was compiled into a typed deterministic Solution
Canvas. Candidate code ran as a non-root user with no network, a read-only root
filesystem, all Linux capabilities dropped, no new privileges, and explicit
CPU, memory, process, file-descriptor, and temporary-filesystem bounds. The
runtime image was
`sha256:d29a0fedd17671510b759b15f276b73ee9ba813868653d8923c7365482ee328d`.

All four selected runs completed the required full path. Each saved Canvas plan,
evaluation result, report summary, and playback file is included in the tracked
[artifact package](../benchmarks/ds1000/artifacts/).

## Result and invalidation

The real provider run made 14 selected calls. An earlier interrupted diagnostic
made one excluded call, so the packet used 15 of its 16-call ceiling. The
selected calls reported 11,577 input tokens and 25,301 output tokens, or 36,878
total. Provider money cost is unknown because no source-backed price was
configured.

The first evaluation reported this table:

| Problem | First reported result | Why it changed |
|---:|---|---|
| 72 | fail | extractor removed indentation from repair output |
| 218 | pass | unchanged |
| 838 | pass | unchanged |
| 896 | fail | extractor removed indentation from repair output |

That 2 of 4 score, or 50 percent, is preserved for audit but invalidated. The
first `safe_extract_code` implementation called `strip()`. For problems 72 and
896, DS-1000 inserts the completion inside a function body, so removing leading
spaces changed valid recorded repair text into invalid Python.

The correction did not ask the model again. It replayed the exact saved provider
responses through a full deterministic nine-step Practitioner, preserved leading
whitespace, compiled the same Canvas shape, and ran the same locked upstream
evaluator. The selected raw-response hashes matched the correction inputs. All
four corrected tasks passed.

Plain verdict: the exact recorded model outputs passed this four-task public
smoke population after the deterministic extractor matched upstream whitespace
behavior. The invalidated 2 of 4 score is not a model result.

## Run History, playback, and offline verification

The tracked evidence contains four selected-run Run History chains and four
correction chains. All eight chains verify, as do every saved Canvas, compact
report, and playback path. The ignored detailed local results are not needed.

- [Compact verified result](../benchmarks/ds1000/verified-result.json)
- [Tracked artifact manifest](../benchmarks/ds1000/artifacts/manifest.json)
- [Selected-run summary](../benchmarks/ds1000/artifacts/selected-summary.json)
- [Correction summary](../benchmarks/ds1000/artifacts/correction-summary.json)
- [Per-task evidence](../benchmarks/ds1000/artifacts/task-evidence.json)
- [Eight compact Run History chains](../benchmarks/ds1000/artifacts/run-history-chains.json)
- [Problem 72 selected playback](../benchmarks/ds1000/artifacts/selected/playback/problem-72.txt)
- [Problem 72 correction playback](../benchmarks/ds1000/artifacts/correction/playback/problem-72.txt)

Run the independent verifier from a clean checkout:

```bash
python3 benchmarks/ds1000/verify.py
```

It uses only the Python standard library. It fits and trains nothing, executes
no candidate, and makes no provider or network call.

## Limits

This is a four-task public smoke population, not the complete DS-1000 suite.
Public prompts create high contamination risk. The result does not cover the
many AI, ML, experimentation, model-tuning, and data-engineering tasks outside
this slice. It compares no second model, provider, harness, or deterministic
baseline. It establishes full-path integration and these exact recorded-output
results, not a general success rate or cost advantage.
