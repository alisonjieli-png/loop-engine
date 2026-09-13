# OpenCode instance composition and native session limits

This is an optional host execution adapter, not another Loop run mode.
It composes a native OpenCode instance from a core layer and a selected
step layer. The registered default catalogue is extensible; its four
example steps do not limit the product's step profiles.

The September 13 integration review found that the native session did not
honor the complete gateway request. Read the current limits below before
using the historical experiments later in this page. The
[complete behavioral explanation](../ASTRA.md#complete-behavioral-explanation)
defines the discrete cognitive or act step Loop node; this adapter implements
only part of that design.

```text
Operational runtime type
└── Loop
    ├── Operational relationship
    │   ├── Starting
    │   ├── Spawned by
    │   ├── Queried by
    │   ├── Retrieved by
    │   └── Connected from
    ├── Role
    │   ├── Practitioner
    │   ├── Intelligence
    │   └── Solution
    ├── Versioned role profile
    ├── Purpose and domain categories
    ├── Run mode
    │   ├── deterministic
    │   ├── hybrid
    │   └── non-deterministic, with model-led semantic work
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition
    ├── Exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the selected mode permits a model
    └── Run History records
```

## Shared interface and request compatibility

Every adaptive step reaches the model through exactly one seam:

```python
services.model_session.invoke(ModelInvocationRequest(...), owner)
```

`orient`, `plan`, `implement` and `verify` all funnel through it. Supplying a
different object for `model_session` selects an alternative implementation.
Matching method names does not establish request compatibility.
The interface includes `invoke`, `results`,
`calls_used`, `accounting_uncertain`, `authority`; `start_session` refuses a
factory-made session that lacks any of the first four, by name.

## The two modules

| module | role |
|---|---|
| `core.opencode_step_session` | a `model_session` whose every step is one headless OpenCode run |
| `core.opencode_step_composition` | builds the `.opencode` tree each instance is given |

### Session

`OpenCodeStepSession` accepts a prompt, a matching model identity, and a
bound structural response expectation. It checks that expectation and an
explicit validator before returning a successful result. It refuses system
instructions, temperature, a different model, output allocation, response
normalization policies, harness selection, and evaluator references before
execution. Those fields need a reviewed native binding. In particular, the
default temperature on `ModelInvocationRequest` is an explicit setting,
so the current native session is not a complete replacement for
`ModelExecutionSession`. Use the canonical gateway for that contract.

The session checks available authority before starting and charges every
reported model turn afterward. OpenCode controls the number of internal
turns, so this path detects an overrun after execution; it cannot guarantee
a strict pre-dispatch call or token ceiling. Missing usage remains unknown.
Transport failure leaves an uncertain result and prevents another run
under a finite ceiling. Native process failure cannot become success merely
because partial output contains text.

Token counts come from `step_finish`, with cache reads folded into input and
reasoning into output: the numbers the provider actually bills, not the raw
fixture fields.

`transport` is injectable, so the whole path (budget, parsing, projection,
refusal) is exercised offline against recorded fixtures with no process, no
network and no provider call.

### Composition

The instance is a directory, not a set of flags. OpenCode discovers agents,
skills, commands and plugins from a `.opencode` tree, and only a directory
can carry per-step *tool permissions*, which have no command-line form. It
also leaves an artifact a human can read after the run.

```text
.opencode/
  agent/step-<id>.md          <- the step layer: prompt, tools, permissions
  skill/<name>/SKILL.md       <- core skills, plus any the step adds
  instance-manifest.json      <- what this instance was, and where it came from
```

**Core layer**: the supplied `CoreLayer` pins its files by path and bytes.
The example runner reuses one core layer across its steps. This is a
campaign choice, not a requirement that every assignment or experiment
use identical instructions. Another qualified core layer can be supplied
explicitly. The manifest records the selected digest, and composition
refuses bytes that no longer match it.

**Step layer**: chosen at instantiation from an engine-owned catalogue keyed
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

The `verify` example denies the native edit tool but permits a shell.
A shell can still change files. `WorkspaceGuard` detects selected workspace
changes and can restore them; it does not contain effects outside that
workspace. The read-only examples disable known write-capable tools,
including shell execution and delegation.

`permission: ask` is refused outright for unattended steps: a prompt nobody
is awake to answer is a hang, not a safeguard.

## What this does NOT do

`OpenCodeProcessAdapter` in `opencode_harness_adapter` still refuses to
execute, and this does not lift that. Its judgement is about *unattended host
execution of arbitrary generated code*, and it stands.

What runs here is narrower, and is stated rather than left to be inferred:

- the process starts only when a caller passes an explicit profile;
- the environment is an allowlist built from nothing: a credential the
  profile did not name cannot travel by having been present in this process;
- `--pure` disables external plugins;
- `--dir` selects the working directory; it does not confine file access.

That is **a host process with a scrubbed environment**, a weaker boundary
than the engine's Docker profile (`--read-only --cap-drop ALL --network
none`). Native tools may perform effects before any final text is checked.
Use it only with explicitly trusted host execution. The environment allowlist
still includes `HOME`, and is not credential-file isolation.
`requires_trusted_workspace` is a declaration, not an operating-system
sandbox. The quarantined adapter remains unavailable for untrusted work.

Composition refuses path traversal, symlinked instance roots, file aliases,
reserved manifest replacement, and context writes into `.opencode` before
materialization. Validated native controls are read-only. YAML scalars are
quoted, and permission patterns retain their declared order because OpenCode
uses the last matching rule. See the official
[agent configuration](https://opencode.ai/docs/agents/#permissions).

## Historical native session experiments

The original record reported 10 and 12 offline checks and two live cognitive
steps through composed instances against
`ollama-cloud/gemma4:31b`. Those runs predate the current request refusals and
do not qualify every gateway dimension, strict budgets, or native isolation:

| step | wall time | input tokens | output tokens |
|---|---|---|---|
| `orient` | 8.6 s | 17,722 | 261 |
| `plan` | 6.0 s | 4,339 | 159 |

Both returned schema-conforming objects. `orient` reported *"no existing
`test_*.py` files were found"*: it used its read-only glob tool before
answering, which is the whole point: the instance arrived carrying tools and
used them, while `edit` and `bash` stayed denied.

### Two things the live run taught

**Fenced JSON must be recovered, not refused.** The first live step returned
a complete, correct orientation wrapped in a ```` ```json ```` fence. The
event parser accepts only a text part that parses as JSON on its own, so a
good answer was read as prose and the step scored as producing no object.
`_unfenced_json` now recovers it. Fencing is not a model defect to prompt
away: it is the most common way models emit JSON and it survives an
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
never in model output: a model that could trigger its own skills could
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

A skill declaring no triggers is refused outright: it would either always
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
changed between attempts: only the words did. A step that repeats is not a
step that adapts.

### Live result

Set up so the obvious reading is wrong: `clamp()` is **correct**, and the
test asserts `clamp(15, 1, 10) == 11` when the answer is 10. An
unconstrained repair step would plausibly "fix" `clamp.py` and break working
code.

The observation step:

| | |
|---|---|
| command run | `python3 -m pytest test_clamp.py`, the real one |
| output | quoted verbatim, including `assert 10 == 11` |
| contradiction named | *"The test expected clamp(15, 1, 10) to return 11, but the function returned 10"* |
| files changed | **none** |
| fix proposed | **none** |

It surfaced exactly the evidence needed to conclude the test is wrong,
without acting on the wrong reading. The denial held under a real failure,
and separately under an adversarial prompt that ordered an edit twice
("do it immediately"). The target file was byte-identical afterwards.

The skill also tells the step not to propose a fix, because a fix proposed
in the same breath as an observation tends to bend the observation toward
the fix. It complied.

## Inventory and requirements: what do I have, what do I need

Two steps that run before the work, and one engine-side function that
answers them.

`inventory_step_layer(library, catalogue)` establishes what is actually
present. It is read-only: an inventory step that could also act would stop
being an inventory step at the first opportunity to make progress. Its
prompt names the skills and steps this runtime can admit, so the inventory
is of real capabilities rather than imagined ones.

The instruction that carries the weight is *report the commands you FOUND,
quoted from the file you found them in; do not report a command you assume
is conventional*. A run that believes it has a test command it does not have
will report a pass it never ran.

`requirements_step_layer(library)` asks what **this** task needs, from a
**closed vocabulary stated in the prompt**. Requesting outside the list is
refused, and each request must say what it would be used for: a request
with no stated use is dropped, because asking for everything available
costs prompt budget on every later call and says nothing about the task.

### The model requests; the engine grants

`admit_requests(requests, library)` is the whole safety property. A step
that could add its own skills could add the one that says edit permission is
fine. So requests are answered on the engine side against the registered
catalogue, and `provisioned_step_layer` folds the grants into the next step.
A step's own fixed skills still win a name collision.

Refusals name the legal set. That rule was already written in this codebase
(*a closed vocabulary refused without stating itself leaves the next
attempt to guess again*) and had been applied exactly once.

### Why this step exists at all

Measured across a day of runs: the model used **2 of 9** available
capabilities, and rewording the prompt to advertise the others changed
nothing. Naming the inventory as its own step, with its own output contract
and its own denied tools, is the structural version of that fix.

### Live result: inventory and requirements

A workspace with deliberately unconventional commands, so a *found* answer
is distinguishable from an *assumed* one: the real gate lives in a Makefile
and is pointed at by `[tool.custom].verify_command` in `pyproject.toml`.

| field | returned |
|---|---|
| `commands_found` | `python3 -m pytest -q --tb=short tests/`, `python3 -m ruff check src/`, `make check` |
| `where_each_command_came_from` | attributed each to the file and key it came from |
| `absent` | `build command`, reported missing rather than invented |

It did not answer "pytest" by convention. The requirements step then
requested one skill with a specific stated use, and the engine granted it
with nothing refused or dropped.
