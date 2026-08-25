# Five-problem campaign

The campaign CLI runs the same five problem cases across deterministic,
hybrid, and non-deterministic modes. Provider comparison arms pin one provider.
Every arm uses the same frozen input and evaluator for its problem.

## Built-in problems

| Case | Goal |
|---|---|
| Support queue | Choose the next support incident and explain why. |
| Customer import | Decide how to import customer rows safely. |
| Invoice reconciliation | Reconcile invoices and choose the safe payment action. |
| Deployment decision | Decide whether to continue or roll back a deployment. |
| Delivery estimate | Estimate delivery time and state a customer-safe promise. |

These are local control-plane problems. They test loop construction, cross-mode
spawning, provider routing, deterministic verification, Chronicle storage,
reporting, and playback before a larger Kaggle run.

## Plan the matrix

```bash
loop-engine campaign plan
```

The default matrix has 35 arms:

- 5 deterministic arms, one per problem
- 15 hybrid arms, five problems by three providers
- 15 non-deterministic arms, five problems by three providers

Deterministic work is not repeated under three provider labels.

## Run the deterministic stage

```bash
loop-engine campaign run \
  --modes deterministic \
  --runs-dir "$HOME/.loop-engine/pilot/runs" \
  --watch
```

This stage makes no model calls. It saves one Chronicle per problem.

## Run a provider-pinned pilot

Model arms refuse to start without an explicit authorization flag and a
physical-call ceiling.

```bash
loop-engine campaign run \
  --cases support_queue \
  --modes hybrid,non_deterministic \
  --providers ollama_cloud,mistral \
  --thinking-power medium \
  --authorize-model-calls \
  --max-model-calls 4 \
  --max-total-tokens 4000 \
  --runs-dir "$HOME/.loop-engine/pilot/runs" \
  --watch
```

This bounded pilot makes four provider-pinned calls. Set the required provider
keys before the run. A provider arm does not fail
over to another provider. That keeps the provider comparison readable.

Expand to all five problems and three providers only after the pilot passes.
The full model matrix requires a ceiling of at least 30 physical calls.

`--thinking-power` selects `small`, `medium`, `high`, `max`, or
`specialized` for every model arm in this campaign. The default comes from the
user settings file. Provider comparisons do not enable model-tier escalation.
Read [Runtime settings and model tiers](settings.md).

## View reports and playback

```bash
loop-engine --runs --runs-dir "$HOME/.loop-engine/pilot/runs"
loop-engine --report --runs-dir "$HOME/.loop-engine/pilot/runs"
loop-engine --studio --port 8765 \
  --runs-dir "$HOME/.loop-engine/pilot/runs"
```

Open `http://127.0.0.1:8765/app` for the loop tree and saved-event playback.
`--watch` provides live console events while the campaign runs. Browser-based
live campaign streaming is separate work; the current browser live view is the
fixed local demonstration.

## Result accounting

Each arm records:

```text
case and arm identity
mode and pinned provider
accepted or failed evaluator result
selected model and route
physical provider calls
input and output tokens when reported
whether token accounting is complete
error state
saved Chronicle run ID
```

Mode labels do not substitute for provider events. Physical model calls come
from `ModelGateway` attempts.

## Kaggle remains a separate effect

The campaign runner does not accept competition rules, download Kaggle data,
or submit a file. Use the repository's Kaggle example to test acquisition and
local solving. Add submission only with its explicit `--submit` flag.

```bash
python3 examples/05_kaggle_competition/run.py --help
```

A Kaggle case should enter the campaign only after its data, output format,
metric, local evaluator, and rule status are frozen. Download, local execution,
and submission should remain separate recorded effects.
