# OpenCode instances as loop-node cognitive steps

An optional execution mode: each Practitioner cognitive step runs inside its
own OpenCode instance, composed from a fixed core layer and a per-step layer
chosen when the instance is created. Nothing in the default path changes. A
run that does not ask for this is byte-for-byte the run it was before.

## Why this was cheap to add

Every adaptive step reaches the model through exactly one seam:

```python
services.model_session.invoke(ModelInvocationRequest(...), owner)
```

`orient`, `plan`, `implement` and `verify` all funnel through it. Supplying a
different object for `model_session` therefore redirects every cognitive step
at once, with no change to the practitioner, the prompt builder, or the
verification path. The interface is four members: `invoke`, `results`,
`calls_used`, `authority`.

## The two modules

| module | role |
|---|---|
| `core.opencode_step_session` | a `model_session` whose every step is one headless OpenCode run |
| `core.opencode_step_composition` | builds the `.opencode` tree each instance is given |

### Session

`OpenCodeStepSession` mirrors `ModelExecutionSession`. It enforces
`authority.max_model_calls` *before* starting a process, reuses the existing
`parse_opencode_events` to normalise `opencode run --format json`, and
projects each turn into a `ModelGatewayResult` so accounting, stage grading
and Run History see an OpenCode step exactly as they see a gateway step.

Token counts come from `step_finish`, with cache reads folded into input and
reasoning into output — the numbers the provider actually bills, not the raw
fixture fields.

`transport` is injectable, so the whole path — budget, parsing, projection,
refusal — is exercised offline against recorded fixtures with no process, no
network and no provider call.

### Composition

The instance is a directory, not a set of flags. OpenCode discovers agents,
skills, commands and plugins from a `.opencode` tree, and only a directory
can carry per-step *tool permissions*, which have no command-line form. It
also leaves an artifact a human can read after the run.

```
.opencode/
  agent/step-<id>.md          <- the step layer: prompt, tools, permissions
  skill/<name>/SKILL.md       <- core skills, plus any the step adds
  instance-manifest.json      <- what this instance was, and where it came from
```

**Core layer** — identical on every step of every run. `CoreLayer.digest`
is computed over every core file's path and bytes and recorded into every
instance manifest. A core that drifts between steps is *detectable*, not
merely promised: if it can be edited per step without anyone noticing, it is
not an invariant, it is a default.

**Step layer** — chosen at instantiation from an engine-owned catalogue keyed
by step id. A step file that would overwrite a core file is refused rather
than silently winning.

**Trust direction.** A model never names a file to write into the instance. A
model that could compose its own instance could grant itself tools and lift
its own permissions. Selection is engine authority; the model's influence is
the task text that selection reads.

### The default catalogue

Permissions are the substance here, not decoration:

| step | tools | edit | bash |
|---|---|---|---|
| `orient` | read, grep, glob, list | deny | deny |
| `plan` | read, grep, glob, list | deny | deny |
| `implement` | read, write, edit, bash, grep, glob, list | allow | allow |
| `verify` | read, bash, grep, glob, list | **deny** | allow |

`verify` can run commands but cannot edit: a verifier that can edit can make
a failing check pass. `orient` cannot write: a step that edits has a way to
appear to make progress without producing the orientation it was asked for.

`permission: ask` is refused outright for unattended steps — a prompt nobody
is awake to answer is a hang, not a safeguard.

## What this does NOT do

`OpenCodeProcessAdapter` in `opencode_harness_adapter` still refuses to
execute, and this does not lift that. Its judgement is about *unattended host
execution of arbitrary generated code*, and it stands.

What runs here is narrower, and is stated rather than left to be inferred:

- the process starts only when a caller passes an explicit profile;
- the environment is an allowlist built from nothing — a credential the
  profile did not name cannot travel by having been present in this process;
- `--pure` disables external plugins;
- `--dir` confines the working directory.

That is **a host process with a scrubbed environment**, a weaker boundary
than the engine's Docker profile (`--read-only --cap-drop ALL --network
none`). It is appropriate for driving a cognitive step, whose product is text
this engine then validates. It is **not** a substitute for the sandbox that
executes generated code. `requires_trusted_workspace` defaults to True to
keep that distinction legible at the call site.

## Status: working end to end, live

Both modules are registered in the suite and pass offline (10 + 12 checks).
Two live cognitive steps ran through composed instances against
`ollama-cloud/gemma4:31b`:

| step | wall time | input tokens | output tokens |
|---|---|---|---|
| `orient` | 8.6 s | 17,722 | 261 |
| `plan` | 6.0 s | 4,339 | 159 |

Both returned schema-conforming objects. `orient` reported *"no existing
`test_*.py` files were found"* — it used its read-only glob tool before
answering, which is the whole point: the instance arrived carrying tools and
used them, while `edit` and `bash` stayed denied.

### Two things the live run taught

**Fenced JSON must be recovered, not refused.** The first live step returned
a complete, correct orientation wrapped in a ```` ```json ```` fence. The
event parser accepts only a text part that parses as JSON on its own, so a
good answer was read as prose and the step scored as producing no object.
`_unfenced_json` now recovers it. Fencing is not a model defect to prompt
away — it is the most common way models emit JSON and it survives an
explicit instruction not to do it. Recovering costs one string operation;
refusing costs the step, and the repair attempt is just as likely to come
back fenced.

**Per-step overhead is real and should be budgeted.** A trivial one-line
prompt cost 7,854 input tokens through OpenCode, because the instance ships
its own system prompt and tool definitions. That is the price of the tools
being there. It makes OpenCode instances a poor fit for cheap, high-frequency
steps and a good fit for steps that genuinely need to look around.

### Running it on this machine

The local `opencode.db` fails its own schema migration
(`SQLiteError: no such column: replacement_seq`), so a default `opencode run`
exits 1 before emitting any event. **Nothing was deleted to work around
this**: pointing `XDG_DATA_HOME` at a fresh directory gives OpenCode a clean
database and leaves the existing one untouched. Credentials come from
`OLLAMA_API_KEY` in the environment, so no credential file is copied.

```bash
XDG_DATA_HOME=/path/to/fresh-dir OLLAMA_API_KEY=... opencode run --format json --pure -m ollama-cloud/gemma4:31b "..."
```

Both names must be listed in the profile's `additional_environment`, since
the environment is allowlisted from nothing. See
`docs/opencode-local-db-fault.md` for the 303 GB database behind that fault.

## Dynamic selection at instantiation

The catalogue gives each step its fixed layer. `SkillLibrary` adds the
variable half: optional skills admitted by terms found **in the task text**,
never in model output — a model that could trigger its own skills could
grant itself tools.

```python
layer, provenance = dynamic_step_layer(catalogue.select("plan"), task, library)
```

Selection is deterministic (same task and step → same set, ordered by name
before truncation) and the matched trigger is recorded per skill, so *"why
was this skill here"* has an answer after the run rather than a guess. The
base layer's own skills always win a name collision: a step's fixed skills
are part of what that step **is**, and a task-triggered skill that could
displace one would make the step's identity depend on wording.

A skill declaring no triggers is refused outright — it would either always
load or never load, and saying which is the point.

| task | admitted |
|---|---|
| *"failing test … raises a traceback"* | `reproduce-before-fix` |
| *"gantt chart from the dependency list"* | `schedule-arithmetic` |
| *"macro-F1 on the drift dataset csv"* | `dataset-discipline` |
| *"rename a variable"* | *(none)* |

### Measured effect

Controlled A/B on `orient`, same model (`ollama-cloud/gemma4:31b`), same
three bug-report tasks, differing only in whether `reproduce-before-fix` was
admitted. Scored on whether the step committed to reproducing the failure
before changing code:

| arm | reproduce-first |
|---|---|
| without skill | **0 / 3** |
| with skill | **2 / 3** |

With the earlier single trial included, 0/4 versus 3/4. At this n the result
is **not statistically conclusive** (Fisher's exact ≈ 0.14) and is reported
as a direction, not a proof. What makes it worth recording is the contrast
with a previous negative result in this codebase: situational capability
triggers expressed as *prompt framing* did not change capability usage at
all (still 2 of 9 capabilities used). The same idea expressed as *instance
content* moved behaviour on the first attempt.

That is the general lesson this whole session keeps returning to, from the
`core.source.inspect` refusal onward: **structure changes what a small model
does; wording mostly does not.**

## Forced observation after a failure

`observation_step_layer(failed_step_id, failure_text)` composes the step a
run is pushed into after something fails. Edit and write are **absent**, so
the only available move is to look.

This is a separate step, not a retry, and the distinction is the point.
Retrying gives the model the same tools and the same framing that produced
the failure, plus an error string. Measured in this codebase: one refusal
was hit **nine times across runs**, because nothing in the loop's shape
changed between attempts — only the words did. A step that repeats is not a
step that adapts.

### Live result

Set up so the obvious reading is wrong: `clamp()` is **correct**, and the
test asserts `clamp(15, 1, 10) == 11` when the answer is 10. An
unconstrained repair step would plausibly "fix" `clamp.py` and break working
code.

The observation step:

| | |
|---|---|
| command run | `python3 -m pytest test_clamp.py` — the real one |
| output | quoted verbatim, including `assert 10 == 11` |
| contradiction named | *"The test expected clamp(15, 1, 10) to return 11, but the function returned 10"* |
| files changed | **none** |
| fix proposed | **none** |

It surfaced exactly the evidence needed to conclude the test is wrong,
without acting on the wrong reading. The denial held under a real failure,
and separately under an adversarial prompt that ordered an edit twice
("do it immediately") — the target file was byte-identical afterwards.

The skill also tells the step not to propose a fix, because a fix proposed
in the same breath as an observation tends to bend the observation toward
the fix. It complied.
