# Overnight solving on local models

Leave a hard problem running while you sleep, on weights you own, and read
the result over breakfast. This guide answers five questions in order:

1. What machine do I need, and what fits on it?
2. Which local model do I run, and how do I connect it?
3. How do I hand a problem over before I go to bed?
4. What is waiting for me in the morning?
5. What is kept between nights, and how much disk does it take?

Everything below uses commands and contracts that are in this repository
today. The section [What was run for this guide](#what-was-run-for-this-guide)
says plainly which parts were executed on 21 September 2026 and which were
not. No speed, cost or quality figure is claimed for any model anywhere in
this guide, because none was measured.

The runnable companion is
[examples/30_overnight_local_run](../../examples/30_overnight_local_run/).
It performs the whole setup with no provider key and no socket, and the
tables in this guide are its output rather than prose.

## 1. What machine do I need

Two numbers decide whether a model loads, and both are arithmetic:

```text
weights = parameters x bytes per weight        (the quantisation decides this)
cache   = 2 x layers x kv heads x head dim x context tokens x element bytes
total   = weights + cache + the reserve you declare for the runtime
```

The factor of two in the cache is the key half and the value half. The
reserve is the inference runtime's own working space. State it, and raise it
when a load fails close to the line. It is a declared reserve, not a measured
figure.

### Bytes per weight, from the block layout

A quantisation is a block layout, so its cost per weight is division, not
opinion. `q4_0` packs 32 four bit integers (16 bytes) and one 16 bit scale
(2 bytes) into 18 bytes, which is 4.5 bits or 0.5625 bytes a weight.

| Quantisation | Weights a block | Bytes a block | Bytes a weight |
|---|---|---|---|
| `f32` | 1 | 4 | 4 |
| `f16`, `bf16` | 1 | 2 | 2 |
| `q8_0` | 32 | 34 | 1.0625 |
| `q5_1` | 32 | 24 | 0.75 |
| `q5_0` | 32 | 22 | 0.6875 |
| `q4_1` | 32 | 20 | 0.625 |
| `q4_0` | 32 | 18 | 0.5625 |

The K quantisations (`q4_K_M`, `q5_K_M`, `q6_K` and their relatives) use a
different layout per tensor, so they have no single bytes per weight. Do not
multiply. Read the size of the weights file on disk and use that instead.
The calculator in the example refuses a K quantisation by name and says so,
because a guess here is a night that dies at two in the morning with an out
of memory error.

### The four inputs the cache needs

Read them from the model's own configuration file, never from memory:

| Input | Where it comes from |
|---|---|
| layers | `num_hidden_layers` |
| key and value heads | `num_key_value_heads` |
| head dimension | `head_dim`, or `hidden_size` divided by `num_attention_heads` |
| element bytes | 2 for a 16 bit cache, 1 for an 8 bit cache, which is a runtime setting |

Use `num_key_value_heads`, not `num_attention_heads`. Grouped query attention
makes the cache several times smaller than the attention head count suggests,
and substituting the wrong one overstates the cache badly enough to change
every answer below.

### Three machine tiers

These rows are the example's output. The machine figures are the definition
of each tier, so replace them with your own machine's numbers and run it
again. The model shapes are inputs stated in the source: 8 key and value
heads and a head dimension of 128 for each row, with the layer count rising
with the size. Read your own model's configuration before trusting a row for
a model you have not loaded.

The context column is at 8192 tokens. "longest context" is the longest the
model reaches at the better of the two placements.

#### Laptop, 16 GiB unified memory

One pool, shared with the operating system and the display. About two thirds
of it is what a model may take. Here, 11 GiB usable with a 1.5 GiB reserve.

| Model | Weights | Cache | Total | Placement | Longest context |
|---|---|---|---|---|---|
| 8B at `q4_0` | 4.19 GiB | 1.00 GiB | 6.69 GiB | video | 32768 resident |
| 14B at `q4_0` | 7.33 GiB | 1.50 GiB | 10.33 GiB | video | 11828 resident |
| 32B at `q4_0` | 16.76 GiB | 2.00 GiB | 20.26 GiB | refused | does not load |
| 70B at `q4_0` | 36.67 GiB | 2.50 GiB | 40.67 GiB | refused | does not load |

What it is good at: an 8B model at a full 32k context, all night, with the
lid shut and the machine on mains power.

What it is slow at: anything at 14B, because the model fits but the context
does not. Cutting the context to about 11k is what makes it resident, and a
shorter context means more passes over the same material.

What it cannot do: 32B and above. There is no quantisation that rescues it,
because the weights alone exceed the pool.

#### Workstation, one 24 GiB graphics card

23 GiB usable on the card, 64 GiB of system memory behind it, 1.5 GiB
reserve.

| Model | Weights | Cache | Total | Placement | Longest context |
|---|---|---|---|---|---|
| 8B at `q4_0` | 4.19 GiB | 1.00 GiB | 6.69 GiB | video | 32768 resident |
| 14B at `q4_0` | 7.33 GiB | 1.50 GiB | 10.33 GiB | video | 32768 resident |
| 32B at `q4_0` | 16.76 GiB | 2.00 GiB | 20.26 GiB | video | 19399 resident |
| 70B at `q4_0` | 36.67 GiB | 2.50 GiB | 40.67 GiB | split | 32768 split |

What it is good at: 8B and 14B at a full context with room to spare, and 32B
resident once the context is held near 19k.

What it is slow at: 70B. It loads, because system memory takes what the card
cannot, but the part that is not resident is read across the system bus on
every token. This guide claims no rate for that, and neither should you until
you have timed your own machine.

What it cannot do: hold 32B at a full 32k context on the card. Either shorten
the context, or move to an 8 bit cache and redo the arithmetic.

#### Server, 128 GiB system memory and 8 GiB video memory

120 GiB usable system memory, 7 GiB usable on the card, 2 GiB reserve. This
is the shape of a retired server or a workstation whose card was chosen for
display rather than for inference.

| Model | Weights | Cache | Total | Placement | Longest context |
|---|---|---|---|---|---|
| 8B at `q4_0` | 4.19 GiB | 1.00 GiB | 7.19 GiB | split | 6627 resident |
| 14B at `q4_0` | 7.33 GiB | 1.50 GiB | 10.83 GiB | split | 32768 split |
| 32B at `q4_0` | 16.76 GiB | 2.00 GiB | 20.76 GiB | split | 32768 split |
| 70B at `q4_0` | 36.67 GiB | 2.50 GiB | 41.17 GiB | split | 32768 split |

What it is good at: loading large models that the other two tiers refuse.
Nothing here fails to load.

What it is slow at: all of it, structurally. Almost nothing stays on the
card, so most of each token crosses the bus. The one exception is an 8B model
held under about 6.6k of context, which becomes resident.

What it cannot do: it has no hard refusal in this table, which is exactly why
this tier needs a wall clock limit more than the others. A night is finite
even when memory is not.

### Redo it for a model this guide did not list

```bash
python3 examples/30_overnight_local_run/run.py --json
```

Or call the calculator directly and put your own machine in:

```python
import sys
sys.path.insert(0, "examples/30_overnight_local_run")
from local_fit import GIB, LocalModel, MachineTier, fit, largest_context

machine = MachineTier(
    name="my laptop", usable_video_bytes=11 * GIB,
    usable_system_bytes=11 * GIB, runtime_reserve_bytes=1.5 * GIB)

model = LocalModel(
    name="the model I actually downloaded",
    layers=48, key_value_heads=8, head_dimension=128,
    weights_file_bytes=9_100_000_000,     # ls -l the weights file
    maximum_context_tokens=32768)

print(fit(machine, model, 8192))
print(largest_context(machine, model, placement="video"))
```

Pass `parameters` with a uniform `quantisation` when you have one, or
`weights_file_bytes` when you do not. Passing both is refused, and so is
passing neither, because a silently defaulted weights figure is the one
mistake this calculator exists to prevent.

## 2. Which local model, and how to connect it

### The providers this repository already supports

Loop Engine reaches a model through `ModelGateway` and a named `ModelRoute`.
A local server is not a special case in the code: it is a `kind: custom`
provider with a URL. Two wire formats are supported, `openai` and `ollama`,
so any server that speaks either one is a provider here without a code
change. That covers Ollama on its native path, and vLLM, LM Studio,
llama.cpp's server, text generation web user interface and LiteLLM on the
OpenAI compatible path.

Read [custom endpoints](custom-endpoints.md) for every field, and
[providers and keys](providers-and-keys.md) for the built in cloud providers.
Do not invent a provider name or a setting: the fields are validated and a
misspelled one is refused rather than ignored.

### Install the server and pull the weights

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve                       # listens on http://127.0.0.1:11434
ollama pull qwen3:8b
ollama list
```

Confirm the server answers before Loop Engine is involved at all:

```bash
curl -s http://127.0.0.1:11434/api/tags | head -c 400
```

A model listing is not readiness. It says the weights are on disk, not that
generation succeeds. The next two steps are what establish that.

### Declare the provider in a settings file

The settings file records a credential reference, never a key. A local server
that wants no key declares `auth_scheme: none` and no `credential_env` at
all.

```yaml
# ~/night/loop-engine.yaml
version: 1

models:
  default_thinking_power: medium
  # A local route is refused for counted generation by default, because a
  # benchmark's token counts must be reproducible on another machine. Your
  # own overnight run is not a benchmark, so permit it deliberately here.
  allow_local_counted_generation: true
  providers:
    - id: local_ollama
      kind: custom
      endpoint: http://127.0.0.1:11434
      model: qwen3:8b
      wire: ollama
      locality: local
      auth_scheme: none
      think: model
      maximum_output_tokens: 32768
      maximum_output_source: local server configuration read on 2026-09-21
      context_window: 32768
      purposes: [counted_generation, decide_label]
  tiers:
    medium:
      routes: [custom.local_ollama]
      timeout_seconds: 1800
      max_attempts: null

history:
  runs_dir: ~/.loop-engine/runs
  save_run_history: true
```

Four fields deserve a sentence each.

`maximum_output_tokens` and `maximum_output_source` are declared together or
not at all. Loop Engine requests the exact declared maximum and lets the
model stop on its own. It never invents a smaller ceiling, and a model with
no source backed maximum is refused with `unknown_model_output_limit` rather
than run at a guess.

`think` controls whether a reasoning model thinks before it answers on the
Ollama wire. The default sends `think: false`, because a reasoning model can
spend the whole output ceiling thinking and return nothing. A model that
cannot run without thinking refuses that with HTTP 400, which is classified
as `invalid_request` and stops the route. Declare `think: model` for such a
model, as the file above does.

`timeout_seconds` on the tier is the per attempt ceiling. Thirty minutes is
generous on purpose: a local model on a split placement is not a cloud model,
and a timeout tuned for a hosted route turns a slow answer into a failure.

`allow_local_counted_generation` is the switch most likely to be missed. Left
at its default, a local route is refused for counted generation and the
refusal names this flag. The example screens for it before the night starts,
so the refusal arrives at the keyboard rather than after you have gone to
bed.

### Check it before you trust it overnight

```bash
loop-engine settings check --settings-file ~/night/loop-engine.yaml
loop-engine models inventory --settings-file ~/night/loop-engine.yaml
loop-engine doctor
```

`settings check` validates the file and contacts nothing. `models inventory`
prints the route table and contacts nothing; your route appears as
`custom.local_ollama: local_ollama / qwen3:8b (local)`. `doctor` checks the
installation and makes zero provider calls.

Then make one real call, and read what comes back:

```bash
loop-engine solve \
  --text "Reply with the single word ready." \
  --settings-file ~/night/loop-engine.yaml \
  --compile-provider local_ollama \
  --authorize-model-calls \
  --max-model-calls 1 \
  --runs-dir ~/night/runs
```

A run that reaches `COMPLETED_VERIFIED` or returns a model answer has proved
the route. A run that ends `PROVIDER_UNAVAILABLE` has not, and the reason is
in the saved events. Do not start a night on an unproved route.

### Two protections worth knowing

A custom provider cannot shadow a built in one. Naming yours `mistral` is
refused, because a record naming a provider has to mean that provider.

Your configuration decides who is called. Configuring only your own server
means only your own server is contacted. This was a real defect once, where a
self hosted configuration quietly billed a different provider.

## 3. Handing over the problem before bed

### Write the night down first

An overnight run is a run nobody watches, so everything a person would
normally decide at the keyboard has to be written down in advance: what the
run may do, what it may spend, how long it waits for a server that went
quiet, and which endings are allowed to finish it.

The last one is where unattended runs usually go wrong. A run that ends after
three tries has not finished the work, it has finished counting. The accepted
endings come from the
[persistent general solving decision record](../architecture/ADR-PERSISTENT-GENERAL-SOLVING-AND-CONTRACT-FAILURE-REVIEW.md),
and there are five:

| Ending | Terminal codes the run returns |
|---|---|
| An accepted result that passed verification | `COMPLETED_VERIFIED` |
| Declared authority spent | `BUDGET_EXHAUSTED`, `DEADLINE_EXHAUSTED`, `NO_PROGRESS`, `COMPLETED_PARTIAL`, `VERIFICATION_FAILED`, `REPAIR_UNAVAILABLE`, `ABSTAINED` |
| A question only the owner can answer | `BLOCKED_MATERIAL_INPUT`, `AUTHORITY_REQUIRED`, `CAPABILITY_GAP` |
| An operator cancellation | `CANCELLED` |
| A provider outage, recorded so the run resumes | `PROVIDER_UNAVAILABLE` |

Every terminal code the solve runtime can return belongs to exactly one of
these five, and the example checks that it still does. A fixed attempt count
is not on the list, and `overnight_plan.OvernightPlan` refuses a plan that
declares one, along with a retry limit, a first failure, a score threshold
and a model that grades its own work.

### Declare the authority

Nothing is permitted by default. An unattended run that may call a model must
also declare its call ceiling, because nobody is awake to stop it.

```bash
loop-engine solve \
  --file ~/night/task.txt \
  --settings-file ~/night/loop-engine.yaml \
  --compile-provider local_ollama \
  --authorize-model-calls \
  --max-model-calls 400 \
  --unattended \
  --workspace ~/night/workspace \
  --verifier ~/night/verify.sh \
  --supervision-policy ~/night/supervision.json \
  --runs-dir ~/.loop-engine/runs \
  --quiet-model-io
```

| Flag | What it declares |
|---|---|
| `--authorize-model-calls` | governed model calls are permitted at all |
| `--max-model-calls 400` | the physical call ceiling for the whole run |
| `--unattended` | do not pause for a material answer; abstain rather than guess |
| `--workspace` | an empty or new directory; every generated file is confined to it |
| `--verifier` | a script run mid solve as an observation, never as acceptance |
| `--supervision-policy` | the declared non progress and unaccepted pass limits |
| `--quiet-model-io` | event summaries instead of the full prompt and output trace |

Three more are off by default and should stay off unless the task needs them:
`--allow-sandbox-commands` for generated code, `--allow-local-execution` for
running it as a host process when Docker is absent, which the run record
labels as the weaker isolation, and `--allow-model-failover` for moving to
another authorized route after a retryable failure. On one local route there
is nothing to fail over to, so leave it off.

`--unattended` matters more than it looks. Without it, a run that meets a
material question waits for an answer, and at three in the morning that is a
run that is not running.

### Declare how long it persists without progress

```json
{
  "identical_failures_before_stop": 3,
  "non_progress_passes_before_escalation": 4,
  "unaccepted_passes_before_stop": 16,
  "non_accepted_iterations_before_stop": 60,
  "budget_phase_thresholds": [0.35, 0.12]
}
```

This is not an attempt count. The escalation ladder is `soft_reset`,
`cold_restart`, `stop_unprofitable`: the run changes its approach before it
gives up, and only the last rung ends anything.
`identical_failures_before_stop` counts the same failure repeating, which is
the signal that the approach is wrong rather than the attempt unlucky.

`budget_phase_thresholds` is the setting that makes a long night behave. With
35 percent of the model call authority left the run conserves, which demotes
exploration to consolidating the work it already has. With 12 percent left it
presents its best available result for verification instead of generating
anything new. A night without these thresholds spends its whole allowance
exploring and then has nothing left to verify with.

### What happens when the server stops answering

Silence has kinds, and the kind decides the action. The gateway classifies
every provider refusal into a closed vocabulary, and
`provider_failure_classes.decide` turns the codes into one decision:

| What happened | Codes | Decision |
|---|---|---|
| The server is restarting | `provider_unavailable` | wait for recovery |
| The host is unreachable | `network_unreachable`, `timeout` | wait for recovery |
| A hosted allowance is spent | `usage_limit_reached`, `rate_limited` | wait for the allowance |
| The model name is wrong | `model_not_found` | stop the route |
| The key is wrong, after an outage | `timeout`, `authentication_failed` | stop the route |
| The prompt exceeds the context | `context_window_exceeded` | fail this unit of work |

Two rows carry the whole design. A wrong credential is never an outage, even
when an outage code arrived alongside it, because a worker that treats a bad
credential as an outage re running the same unit without bound is exactly how
an unattended night burns itself out. And a wait is always bounded: pass an
attempt ceiling, and a wait already retried that many times fails the unit of
work instead of waiting again. No ending is ever reached by counting
attempts, and no wait is ever unbounded.

Inside one step, a refusal that states its own wait through `Retry-After` is
honoured up to a 60 second ceiling. A longer stated wait is recorded and cut
at the ceiling, because a wait the length of a weekly allowance belongs to a
worker that schedules nights, not to one step of one run.

### Checkpointing, and what resume honestly means

`loop-engine solve` installs a signal handler before the first model call.
`SIGTERM`, `SIGINT` and `SIGHUP` write `checkpoint.json` into the run's own
directory, and the run writes one again when it completes.

Read this limit before you rely on it. Those are the only two moments the
current source writes a checkpoint. `SIGKILL` cannot be caught by design, and
an out of memory kill, a power loss or a closed lid that suspends the machine
arrives as no signal at all, so a night ended that way leaves no checkpoint.
The comment at the top of `core/run_checkpoint.py` refers to a periodic write
that covers this case; the current source does not perform one, and the
absence was confirmed on 21 September 2026 by reading every call site of
`RunCheckpoint.write`. Plan around it: keep the machine on mains power, stop
it suspending, and prefer `SIGTERM` over pulling the plug.

The checkpoint says so itself:

```json
{
  "record_type": "run_checkpoint/v1",
  "run_id": "adaptive-37f5e77a2993f3421daa7376",
  "workspace_base": "/home/you/night/workspace",
  "attempts": [],
  "attempt_digests": {},
  "ranking": {},
  "ranking_is_current": false,
  "model_calls": 0,
  "reason": "run completed",
  "note": "Reasoning state is not resumable: provider state was never captured. This records the work that survived."
}
```

Read that note carefully, because it is the honest answer to "how do I resume
it". Loop Engine does not replay a partially completed model loop. Provider
state was never captured, and pretending otherwise would be worse than
stopping. What the checkpoint preserves is what survives an interruption and
is worth having in the morning: which attempts exist on disk, which one the
others agree with, and where to find it.

A checkpoint also records a digest per attempt directory. Reading it back
recomputes them, so a checkpoint describing yesterday's tree comes back
marked `stale` with the changed paths named, rather than handing you a
ranking of files that have since moved.

Resuming, then, is starting a new run that is given the preserved work:

```python
from loop_engine.core.run_checkpoint import read_checkpoint

checkpoint = read_checkpoint("~/.loop-engine/runs/<run_id>")
if checkpoint.get("stale"):
    print("the tree moved since the checkpoint:", checkpoint["changed_paths"])
print(checkpoint.get("retained"), checkpoint.get("attempts"))
```

Point the new run's task at the retained attempt and say what it already
established. That is a resumption that is true, rather than a claim of
continuity the engine cannot support.

### Budget the night, not the call

`NightBudget` states the whole night once, in hours, and grants each step a
share of what remains. Two things follow, and both matter more than any
particular number. Grants shrink as the night runs down, so a slow tail
cannot overrun morning. And every grant arrives with its reason, which is a
sentence you can disagree with:

```text
orient may take 90 min: 12.0h of a 12h night remains, 8 step(s) expected
verify may take 7 min: 1.0h of a 12h night remains, 8 step(s) expected
```

No step is granted less than 90 seconds, because below about a minute a model
call cannot finish at all and a smaller grant only guarantees a failure while
burning the call. No step is granted more than half of what remains, because
a run with nothing left cannot report what it observed.

### Start it and walk away

```bash
nohup loop-engine solve ... > ~/night/night.log 2>&1 &
```

Stop the machine sleeping first. A laptop that suspends at two in the morning
is a night that produced nothing, and the checkpoint cannot help because the
process never received a signal.

## 4. What the morning looks like

### Where the night went

Run History lives under `~/.loop-engine/runs/<run_id>` by default, or
wherever `--runs-dir` pointed. Each run directory holds `events.jsonl`, the
append only event log with a hash chain over it, `outcome.json`,
`adaptive-result.json`, `manifest.json`, and `checkpoint.json` when one was
written. Generated files live in a sibling `<run_id>-artifacts` directory.

Start with the list:

```bash
loop-engine runs --runs-dir ~/.loop-engine/runs
```

```text
1 saved run(s):
  adaptive-37f5e77a2993f3421daa7376: CAPABILITY_GAP, 0 artifact(s)
```

### Read what it tried

```bash
loop-engine report @last --runs-dir ~/.loop-engine/runs
```

```text
LOOP REPORT: adaptive-37f5e77a2993f3421daa7376
  1 loops, 30 events, max depth 0
  0 model calls, 0 tokens
  chain verified: yes
  product terminal: CAPABILITY_GAP
  verification: not passed
```

The header is the part to read first. `chain verified` says the saved event
log has not been altered since the run wrote it. `product terminal` is the
ending, from the table in section 3. `model calls` and `tokens` are what was
actually spent, and an unknown count stays unknown rather than becoming zero.

`--format markdown`, `--format html` and `--format json` render the same run,
and `--out PATH` writes it to a file.

### Play it back

```bash
loop-engine studio --runs-dir ~/.loop-engine/runs --port 0
```

Studio reads the saved history and does not re run the work. Playback shows
each Loop entering, its relationship, its steps, its mode, and each spawn:

```text
[loop1] INIT depth=0 custom/standard: goal: repair the failing import check
[loop1] RELATIONSHIP Starting
[loop1] orient (deterministic) conf=0.8: orient: complete
[loop2] INIT depth=1 custom/standard: goal: confirm the failure on a clean tree
[loop2] RELATIONSHIP Spawned by: loop1
[loop1] SPAWN -> loop2: confirm the failure on a clean tree
```

### Tell a verified result from a provisional one

This is the distinction the whole morning turns on, and it is carried by the
terminal code, not by the prose in the summary.

`COMPLETED_VERIFIED` is the only ending that means the requested outcome was
produced and passed its verification. A `SolveOutcome` may not even carry
`solved=True` without it.

`COMPLETED_PARTIAL` means the run did the best available work and says
explicitly that the requested outcome was not verified. The record carries
`requested_outcome_verified: false`, and the runtime refuses to build the
package without it. Analysis, bounded assumptions, scenario branches,
estimates with their basis, an adapted analogous solution and a list of
missing inputs are all real morning value, and none of them is the result you
asked for.

Everything else is an ending without a result, and the code says which of the
five it was.

### Grade the night by what you received

A binary verified or not verified verdict throws away most of the value.
`loop_engine.core.overnight_outcome` grades a night on what a reviewer
receives, best first:

| Rung | What it means for you |
|---|---|
| `verified` | the project's own gate exits zero on a branch; review and merge |
| `negative_result` | the premise was wrong; this prevented work rather than doing it |
| `verified_by_test_change` | the gate passes, but every changed file is a test |
| `cause_localised` | still red, but with a reproduction and a named cause in named files |
| `blocked_named` | one specific missing thing, usually seconds to clear |
| `narrowed` | reproduced but not explained |
| `no_progress` | nothing usable, said plainly |
| `already_green` | the recorded failure no longer reproduces at all |
| `skipped` | the run declined to start, with its reason |

`verified_by_test_change` is separated deliberately. Anything that can edit a
test can make any gate green, and a run once corrected a wrong `== 11` to
`== 10` and reported a plain pass. The expectation genuinely was wrong, and
the report still gave no hint that the suite rather than the code had moved.

Classification reads the structured state and the gate's exit code. It never
asks a step how well it did, because a run that graded itself would grade
itself generously.

### A night on this repository's own unfinished work

If the problem you want solved is a check that failed during the day, the
repository already has an intake and a runner for exactly that:

```bash
python3 tools/overnight.py --dry-run
python3 tools/session_intake.py
```

See [the 5 PM run](../overnight-run.md) for what it counts as a candidate,
what it never does, and the flag behind every widening. Its verification
oracle is free, because a candidate is a command an engineer already ran that
exited non zero, and that command is the acceptance test.

## 5. System memory and the intelligence layers

### Four layers, and one thing that is not a layer

The four persistent intelligence layers are Context Intelligence, Code
Intelligence, Runtime History and Solution Intelligence, and User Feedback
Intelligence. They persist across runs and across restarts, and they are
searched, selected and materialized through Loop operations.

Runtime Memory is not a fifth layer. It is the temporary note board for one
run: `WorkingMemoryState` is process state with compartments, priorities and
eviction, and it holds no path and opens no file. When the process ends it is
gone, and nothing on disk survives it.

The two are connected by one deliberate step. A note taken during a run does
not become persistent intelligence by being useful, being retrieved, scoring
well or being believed. An explicit curation step promotes it, and an
independent process approves it, because a producer never approves its own
work.

```text
Runtime Memory (one run, in process, lost on exit)
  -> explicit curation into a candidate
    -> independent review
      -> a persistent intelligence layer (survives every restart)
```

### What survives a restart, and where it lives

| What | Where | Survives a restart |
|---|---|---|
| Runtime Memory for one run | process memory only | no |
| Run History, event log and hash chain | `~/.loop-engine/runs/<run_id>/` | yes |
| Generated files from a run | `~/.loop-engine/runs/<run_id>-artifacts/` | yes |
| The interruption checkpoint | `<run_id>/checkpoint.json` | yes |
| Learned and candidate intelligence | `~/.loop-engine/intelligence/` | yes |
| Memory candidates awaiting review | `~/.loop-engine/memory/candidates.jsonl` | yes |
| Live provider evidence | `~/.loop-engine/evidence/` | yes |

`LOOP_ENGINE_RUNS_DIR` and `LOOP_ENGINE_LEARNED_ROOT` move the first two
somewhere with more space, and `history.runs_dir` in the settings file does
the same for Run History.

### How much disk this actually takes

These are measurements from one development machine on 21 September 2026, not
a rate. State your own denominator before you plan around them.

| Measured | Figure |
|---|---|
| The example's own deterministic run | 27 KiB of Run History for 26 events, about 1 KiB an event |
| 30 saved runs accumulated on this machine | 124 MiB in total, Run History and artifact directories together |
| The largest single run in that set | 9.3 MiB of Run History plus 63 MiB of artifacts |
| A typical small deterministic run in that set | tens of kilobytes |
| Runtime Memory, all of it | 0 bytes, because it is never stored |

The shape to plan around is that Run History grows with events, and events
grow with model calls. A deterministic run costs kilobytes. A model led night
costs megabytes of event log, and the artifact directory beside it can be far
larger than the history when the run generates files or unpacks material.
Ten gigabytes is a comfortable allowance for a machine running a night a day
for a few months, and the number to watch is the artifact directories rather
than the event logs.

Two operational notes from this machine. A full disk silently truncates
generated manifests, so a night that ends with a strange conformance failure
is worth checking `df` against first. And a temporary directory under a
quota is a night that dies at an unpredictable point, so set `TMPDIR` to a
path in your own home directory rather than leaving it on a small system
partition.

## 6. Recommended setups

Each row is a starting point that follows from the arithmetic in section 1,
not a measured recommendation.

| Machine | Model and context | Night settings |
|---|---|---|
| Laptop, 16 GiB unified | 8B at `q4_0`, 32k context, resident | `--max-model-calls 200`, 8 hour night, `timeout_seconds: 900`, mains power, sleep disabled |
| Laptop, 16 GiB unified, harder problem | 14B at `q4_0`, context held near 11k | the same, and expect more passes over shorter material |
| Workstation, 24 GiB card | 14B at `q4_0` at a full context for breadth, or 32B near 19k for depth | `--max-model-calls 400`, 12 hour night, `timeout_seconds: 1800` |
| Workstation, 24 GiB card, largest model | 70B at `q4_0`, split placement | `--max-model-calls 150`, 12 hour night, `timeout_seconds: 3600`, and fewer expected steps so each grant is larger |
| Server, 128 GiB memory, 8 GiB card | 32B at `q4_0` at a full context | `--max-model-calls 150`, 12 hour night, `timeout_seconds: 3600`, `budget_phase_thresholds` set so verification is reached |

Common to all of them: `--unattended`, a `--workspace` that is empty at the
start, a `--verifier` that exits non zero on the failure you care about, a
supervision policy with `budget_phase_thresholds`, and one proved route with
failover off.

## What was run for this guide

Run on 21 September 2026 in this repository, on Python 3.10.20:

- `python3 examples/30_overnight_local_run/run.py`, which passed 45 of 45
  checks and exited zero. Every table in section 1 is its output.
- `loop-engine settings check` and `loop-engine models inventory` against the
  settings file in section 2. The route appeared as
  `custom.local_ollama: local_ollama / qwen3:8b (local)`.
- `loop-engine doctor`, which reported a valid configuration and zero
  provider calls.
- `loop-engine solve` with `--unattended`, `--workspace`, `--runs-dir`,
  `--supervision-policy` and `--settings-file`, in deterministic mode with no
  model authority. It saved a Run History and wrote `checkpoint.json`. The
  checkpoint shown in section 3 is that file.
- `loop-engine runs` and `loop-engine report @last`. The output quoted in
  section 4 is theirs.
- The supervision policy file in section 3, loaded through
  `SupervisionPolicy.from_dict` and printed back.
- The disk figures in section 5, measured with `du` against
  `~/.loop-engine/runs` on the development machine.

Not run, and therefore not claimed:

- No local inference server was installed, started or contacted. The Ollama
  commands in section 2 are the documented installation path and were not
  executed here.
- No model was loaded, so no row in section 1 was confirmed against a real
  load, and no speed, cost or quality figure appears anywhere in this guide.
- No overnight run was performed end to end with a model. The plan contract,
  the budget, the failure decisions and the morning path were exercised
  individually by the example, which is not the same as a night.
- The example's model call in section 2 answers the real endpoint adapter
  from a fixture transport, the way this repository's own custom endpoint
  checks do. It proves the wire format, the requested output ceiling, the
  token accounting and the refusal classification. It proves nothing about a
  physical server.

## Related reading

- [Custom endpoints](custom-endpoints.md) for every endpoint field
- [Providers and keys](providers-and-keys.md) for the built in providers
- [The 5 PM run](../overnight-run.md) for the repository's own night runner
- [Model gateway and provider configuration](../components/core-architecture/MODEL-GATEWAY.md)
- [Persistent general solving](../architecture/ADR-PERSISTENT-GENERAL-SOLVING-AND-CONTRACT-FAILURE-REVIEW.md)
- [Intelligence layers](../components/intelligence-layers/README.md)
- [Settings](settings.md) for the complete settings file
