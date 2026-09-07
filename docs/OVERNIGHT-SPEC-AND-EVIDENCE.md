# The overnight solver: specification, and everything tried

One document, two jobs. The first half says what the system is meant to do
and why each decision is the way it is. The second half is the experimental
record: what was measured to work, what was measured **not** to work, and
every bug found by running the thing rather than reading it.

It is written to be built from. Someone starting with an empty directory
should be able to implement this; someone integrating
[loop-engine](https://github.com/alisonjieli-png/loop-engine) should be able
to see exactly which seam to use.

Everything with a number attached was measured on 2026-09-06 against
`ollama-cloud/gemma4:31b` — a small model, unattended. Claims without numbers
are design intent and are marked as such.

---

## Part 1 — What it is meant to do

### The product in one paragraph

At 5pm, without being asked, the system reads the day's coding-agent
transcripts and finds work the engineer left unfinished. It plans each
candidate, attempts it overnight in an isolated git worktree, and verifies
its own work by running **the project's own gate** — the test, lint or build
command the engineer already relies on. In the morning there is a report:
what was attempted, what actually passes, what it could not do, and a branch
per attempt. It never commits, pushes, merges, or touches the engineer's
checkout.

### The one property everything rests on

**The verification oracle is free.**

Every overnight system has to answer "how do I know I fixed it?" Most have
to construct an answer, and a system that grades its own homework is worth
nothing. This one does not construct anything: a candidate comes from a
command the engineer ran that **exited non-zero**. That command is the
acceptance test — already written, already trusted by the person who will
read the report, and binary.

The night's job is to make it exit zero. There is no ambiguity about success
and no opportunity to redefine it.

Consequences that follow from this and are not separate decisions:

- Intake ranks **gate** commands above everything else. Not "how often did
  this fail" but "would anyone care that it did".
- A candidate with no executable gate can be analysed but **cannot be
  verified**, and the run says so rather than implying otherwise.
- A metric-improvement task ("make the model better") has **no free oracle**.
  See *Where this does not reach* below.

### What it must never do

| never | because |
|---|---|
| commit, push, or merge | the morning reviewer decides, not the night |
| touch the engineer's checkout | a killed run must leave everything where it was |
| claim a result it did not observe | a false green is worse than a red; it destroys the only thing being sold |
| ask a question overnight | nobody is awake; `permission: ask` is a hang, not a safeguard |
| delete a failed attempt | a branch with a real error in it beats silence at 7am |
| invent work | "nothing unresolved was observed" is a real and correct report |

### The architecture, and the one seam that matters

Every cognitive step reaches the model through exactly one call:

```python
services.model_session.invoke(ModelInvocationRequest(...), owner)
```

`orient`, `plan`, `implement`, `verify` all funnel through it. Supplying a
different object for `model_session` redirects every step at once with no
change to the practitioner, the prompt builder, or verification. The
interface is four members: `invoke`, `results`, `calls_used`, `authority`.

That is the whole integration story. Two implementations exist:

- `ModelExecutionSession` — in-process, calls a provider gateway directly.
- `OpenCodeStepSession` — spawns one **OS process per cognitive step**
  (`opencode run --format json`), so the step arrives carrying its own
  tools, skills and context.

Choosing between them is configuration. This is also the answer to "should
each loop node be its own process?" — for model steps, both options exist
behind one seam.

### Composed instances: core plus per-step

An instance is a **directory**, not a set of flags. Only a directory can
carry per-step tool permissions, and it leaves an artifact a human can read
after the run.

```
.opencode/
  agent/step-<id>.md        # step layer: prompt, tools, permissions
  skill/<name>/SKILL.md     # core skills + any this step or task added
  instance-manifest.json    # what this instance was, and where each file came from
```

**Core layer** — identical on every step of every run. Its digest is computed
over every file's path and bytes and recorded in every manifest. Core drift
is therefore *detectable*, not promised: if the core can be edited per step
without anyone noticing, it is not an invariant, it is a default.

**Step layer** — chosen at instantiation from an engine-owned catalogue. A
step file that would overwrite a core file is refused, not merged.

**Trust direction** — the model *requests*, the engine *grants*. A model that
could compose its own instance could grant itself tools. Skills are selected
from **task text**, never from model output.

### Permissions are the substance

| step | tools | edit | bash |
|---|---|---|---|
| `inventory`, `requirements`, `orient`, `plan` | read, grep, glob, list | deny | deny |
| `implement` | + write, edit, bash, patch | allow | allow |
| `verify` | read, bash, grep, glob, list | **deny** | allow |
| `observe` (engine-supplied output) | read, grep, glob, list | deny | **deny** |

`verify` cannot edit because a verifier that can edit can make a failing
check pass. `orient` cannot write because a step that edits has a way to
appear to make progress without producing the orientation it was asked for.

**Read-only means all of `bash, edit, write, patch, task`.** This is not
tidiness; it was paid for. See *The read-only bypass* below.

### The step repertoire

18 steps, 30 skills. Beyond the base four:

`reproduce`, `narrow-scope`, `hypothesise`, `check-assumption`, `falsify`,
`decide`, `measure`, `recompute`, `source-ledger`, `claim-audit`,
`schedule-derive`, `review-adversarially`, `summarise-for-human`, `cleanup`,
plus `inventory` and `requirements`.

Skills are admitted by **word-boundary** matching on the task text, each with
a stated use, capped so a task that admits many drops a stable set. Every
carried skill costs prompt budget on every call the instance makes; thin is a
feature.

### Budget the night, not the call

There are no fixed step timeouts. The night is stated once in hours (default
12) and each step is granted a share of what **remains**:

```
orient may take 90 min: 12.0h of a 12h night remains, 8 step(s) expected
verify may take 15 min: 2.0h of a 12h night remains, 8 step(s) expected
```

Grants shrink as the night runs down, so a slow tail cannot overrun morning,
and every grant is a sentence someone can disagree with. `timeout=900` is
not.

---

## Part 2 — What was measured

### Things that work, with numbers

| what | evidence |
|---|---|
| a composed step runs and returns schema-conforming JSON | `orient` 8.6s / 17,722 in / 261 out; `plan` 6.0s / 4,339 in |
| steps use their tools | `orient` reported *"no existing `test_*.py` files were found"* — it globbed before answering |
| the full loop solves and verifies | `orient → plan → implement → verify` produced `stats.py`, gate `4 passed`, **first attempt** |
| the overnight pipeline end to end | seeded gate `python3 -m pytest -q`: `1 failed, 1 passed` → **`2 passed`**, verified, engineer's checkout untouched |
| the fix is minimal and correct | `if hi == lo: return [0.0] * len(values)` |
| intake finds real work | on real transcripts: biome failures in `apps/web/components/dashboard/*.tsx`, `useOptionalChain` in `apps/web/lib/api/guards.ts` |
| inventory reports found, not assumed | in a workspace whose gate is a Makefile target referenced by `[tool.custom].verify_command`, it returned all three real commands **with the file and key each came from**, and reported the absent build command as absent |
| engine-side admission | requested `time-travel` refused **while naming the available set**; a skill requested with no stated use dropped |
| a real ML task | drift dataset: **0.9574** vs 0.7210 baseline |

### Things measured NOT to work — the more useful half

**Wording does not change behaviour. Structure does.** This is the single
most repeated finding and it cost the most to learn.

- A required capability (`core.source.inspect`) was stated **in the tool
  description, in capitals** — *"USE THIS FIRST"* — the refusal named the
  exact fix, and the real paths were already delivered in the prompt. It was
  still hit **9 times across runs**.
- Situational capability triggers expressed as prompt framing left usage at
  **2 of 9** capabilities. No change at all.
- The same idea expressed as **instance content** (a `reproduce-before-fix`
  skill) moved reproduce-first behaviour from **0/3 to 2/3** on identical
  tasks (0/4 vs 3/4 including an earlier trial). Not statistically conclusive
  at that n — reported as direction, not proof.

**Model-authored content is uniformly soft.** 7 authoring agents produced 49
items; 49 independent critics reviewed them. **Every single item came back
`revise`.** None survived as first draft.

**Bundling verdict + explanation + repair did not reproduce as a cause**
(5/5 accept both ways). Recorded because it was a plausible theory that was
wrong.

### The read-only bypass — three rounds

Each round I believed the previous one was safe, and said so.

| round | denial | adversarial result |
|---|---|---|
| 1 | `edit: deny` | model ran `sed -i 's/return 1/return 2/'` — **file changed** |
| 2 | `+ bash: deny` | *"used a general agent task to execute `sed -i`"* — **file changed** |
| 3 | all of `bash, edit, write, patch, task` | told to use any means including delegation: **byte-identical** |

`task` spawns a subagent that inherits the **default** agent, not the composed
layer, handing back every tool the layer removed. The step's own prompt had
been asserting *"you cannot edit or write files"* while holding a shell.

Backstop: `WorkspaceGuard` hashes the workspace and rolls back anything a
read-only step moved. Detection is engine-side; it does not ask the model
whether it behaved.

### Bugs found by running it, not reading it

| bug | how it presented | fix |
|---|---|---|
| **self-disabling dirty check** | refused to run because the tree was dirty; the only dirt was `__pycache__` **created by running the gate**, so it disabled itself after its own first run | check tracked modifications only — untracked files survive a branch switch untouched |
| **killed run moved the checkout** | an 880s timeout killed the run; `finally: git checkout -` never ran, leaving the repo on an overnight branch | **git worktrees** — the engineer's checkout is never touched at all, which also makes their uncommitted work a non-issue |
| **no diagnostics on kill** | the killed run produced **0 bytes** of output | `\| tail -30` buffers until exit; per-step timing now printed and flushed |
| **arbitrary timeouts** | 880s wrapper killed a run with 11 hours of night left | night budget; grants derived from remaining time |
| **flaky complexity oracle** | *"10x input cost 30.6x time"* on a correct linear implementation at load average 18; passed 13/13 alone | `time.process_time()` not wall clock — verified 13/13 three times at load **31.7** |
| **fenced JSON discarded** | a complete correct orientation inside ` ```json ` scored as producing no object | recover it; fencing survives being told not to |
| **substring triggers** | `"error"` matched inside **`ValueError`**, pulling a debugging skill into a from-scratch creation task | word-boundary matching |
| **truncated filename** | report said the verified fix touched `alc.py` | parse porcelain properly; handles renames and quoted paths |
| **833-line diff** | `json.dump(sort_keys=True)` on a 3-line policy change | `tools/policy_edit.py`: typed CRUD, byte-identical round trip |
| **thinking budget** | 9,853 chars of thinking vs 8,018 of content | `think: false` on structured calls |
| **62 MB per step, and the real cause of the "timeout"** | a task ran **18+ minutes unfinished**; the observation step was composed with bash enabled, so OpenCode npm-installed `@opencode-ai/plugin` into the instance directory | wire the engine-observed variant, which needs no shell. Same task: **39 seconds, verified** — `orient` 17.7s, `implement` 20.6s, gate 1.0s |
| **orphaned worktrees** | a killed run left a 62 MB worktree; nothing removed it. 22 GB/year at one a night, on a disk with 66 GB free | prune worktrees older than 3 days, and their branches |
| **the cron runner was 8 commits stale** | its venv lacked 5 modules; a 5pm fire would have run code from before worktrees, the budget, state, or the ladder | launcher does `git fetch` + `reset --hard` and reinstalls before every run; a mirror, not a workspace |
| **result projection missing stage identity** | every OpenCode step logged `stage_evidence_degraded` ×2 (48 in 24 steps); the recorder compares `semantic_call_id`/`owner_loop_id` on result and attempts, and the session set neither | stamp both, derived as the gateway does |
| **CPU-time oracle fooled by swap** | passed at load 31.7, failed "21.5×" at load 48 with swap at 37/39 GB — page-fault handling is charged as system CPU | user CPU only via `getrusage`; 13/13 ×3 while swapping |
| **built but not wired, three times** | the engine-observed observation variant and structured state both existed unused while the slow, unsafe paths ran | wired; the lesson is that building a safer variant is half the work |

### State between steps

Each step gets P (its procedure), S (structured state) and O (the latest
real observation), and returns a patch. The reasoning that produced the
patch is discarded. Measured over 40 steps: an accumulating transcript grows
**29.6x**, bounded state **1.3x** — **5.8x fewer cumulative characters**,
widening with every step. See `docs/step-state-transport.md`.

Two measured limits on the argv transport, **both now fixed**:

- **128 KB** per argv element (`MAX_ARG_STRLEN`). A real `orient` prompt was
  17,722 tokens ~ 70 KB, already 55% of the wall.
- `/proc/<pid>/cmdline` is mode **444**. Verified: prompt content was
  readable by any local user via `ps`.

The prompt now goes in a mode-600 file passed with `--file`, and argv
carries one constant sentence. An 84,000-byte prompt puts **53 bytes** in
argv, and `ps` shows the same harmless line for every step of every run.
Verified live end to end.

### Hybrid, multi-path — measured

Three independent paths, three models, each in its own worktree, gate-verified,
engine-selected:

```
3 path(s): p1=gemma4:31b, p2=kimi-k3, p3=glm-5.3
[p1] -> verified  (98s,  1 file, 3 lines)
[p2] -> verified  (135s, 1 file, 2 lines)
[p3] -> verified  (141s, 1 file, 3 lines)
chose p2: 3 of 3 paths passed the gate; one file changed
```

Selection never reads a path's self-report: rung from the gate, then fewest
files, then fewest lines. A path that passed by editing only tests loses to
one that fixed source, whatever their diff sizes. All branches are kept.

Two bugs it took a live run to find: `git worktree add` **races** when two
paths create worktrees at the same instant (the second failed with
`failed to read .git/worktrees/<first>/commondir`) — creation is now
serialised, solving stays parallel; and a same-day rerun on the same repo
reused branch names and every path silently failed to start — the stamp now
includes the start time, and a path that cannot start says so immediately.

### The provisioning architecture — measured

The alternative to static skill selection: a read-only provisioning step
between cognitive steps decides the **next step**, its **skills**, and its
**context files**; the engine admits the request. Live, with the full
repertoire available:

```
provision -> reproduce (plan said orient), skills=['quote-command-output']
reproduce  10.8s
provision -> implement, skills=['fix-the-cause-not-the-symptom'],
             context=['config.py', 'settings.json', 'test_config.py']
implement  15.6s
-> verified  (44s, 1 file, 6 lines)
```

It **overrode the plan to reproduce first** — the move the earlier A/B showed
a small model does not make unprompted — and asked for exactly the three
relevant files. With only the four base steps available it asked for
`reproduce` and was refused by name; that refusal is how the gap between the
18-step catalog and the run's actual catalogue was found.

### Test-neutralising, and the fix that held first try

Given a test it could not make pass by changing code, the model changed the
test — once correcting a wrong expectation, once **mocking `urlopen`** so an
integration test tested nothing. The gate went green both times. OpenCode
permissions accept `{glob: verb}`, so `implement` now ships
`edit: {"**/tests/**": "deny", "**/test_*": "deny", ..., "*": "allow"}`.
Adversarially: source edit allowed, test edit denied, **`write` of a new
test file denied**, model reported it honestly. The identical mock-the-test
task then landed on `blocked_named` in 47s: *"the test requires a running
inventory service at INVENTORY_SERVICE_URL..."* — the answer an engineer
clears in thirty seconds.

### The real Practitioner, every step in OpenCode

`ModelExecution.session_factory` is one optional field. Set, it redirects
`run_adaptive_practitioner` — the engine's own loop. `loop-engine task build
--step-executor opencode --step-model ollama-cloud/gemma4:31b` with a
24-call ceiling ran **24 of 24 model steps as OpenCode processes** (`orient,
decide_next, how, act, route, verify` and repeats); Run History 1508 events,
chain intact; one step's prompt file was **52,126 bytes at mode 0600** —
40% of the argv wall, carried by file.

**It did not reach a verified terminal.** `Final route: none`, with
`project_candidate_invalid` ×3: the Practitioner's `act` step generates a
whole project candidate and the engine refused three of them — the same
refusal the direct gateway path hit on day one. The executor changed;
that bottleneck did not. The overnight chain (§8.2) verifies real gates in
40–140 s because it runs the project's own command against a real repo
instead of asking the model to author a project from nothing. Both facts
belong in the report: the seam works, and it is not a shortcut past the
Practitioner's hardest step.

The engine first recorded `stage_evidence_degraded` **×48** — two per step —
because the OpenCode result carried neither the stage identities
(`semantic_call_id`, `owner_loop_id`) nor the digests
(`prompt_digest`, `request_digest`, per-attempt `provider_request_digest`)
that the Practitioner's stage recorder verifies. Stamping the identities cut
it to **4** (one per step); stamping the digests, each a real digest of bytes
this session saw or sent, cut it to **0**. The stage evidence for an OpenCode
step is now indistinguishable to the recorder from a gateway step's.

### Cost

Per-instance overhead is **~7,854 input tokens** for a trivial prompt — the
instance ships its own system prompt and tool definitions. That is the price
of the tools being there. It makes composed instances a poor fit for cheap
high-frequency steps and a good fit for steps that must look around.

---

## Part 3 — Where this does not reach

**Ranked by readiness, for the roles that would use it.**

1. **Analytics / data-pipeline engineers — closest.** Their work has gates:
   `dbt test`, `sqlfluff`, `great_expectations`, `pandera`, `airflow dags
   test`, `alembic check`, `sqlmesh plan`. This is software engineering with
   a test command, and the free oracle holds exactly. Intake recognises 15
   such commands.
2. **AI/ML engineers doing engineering** — a broken training script, a
   dependency conflict, a failing pipeline. Gates exist. Same story.
3. **Data scientists doing modelling — furthest, and it is not close.**
   "Improve macro-F1" has **no free oracle**. Verifying it needs a holdout, a
   baseline, a metric and split discipline, and the engine would have to
   construct the very thing it is being graded against. A model that
   constructs its own oracle will fit the eval split or pick a favourable
   metric. Skills exist (`eval-split-quarantine`, `metric-denominator`,
   `sample-size-floor`, `measured-vs-inferred`) but a skill is guidance, and
   this document's central finding is that guidance does not constrain.
   **This is unsolved and should be treated as unsolved.**

**Also open:**

- No searchable index of symbols, call paths, entry points or versions.
  `.codegraph` is absent.
- `skill_state_context.py` — 722 lines implementing SKILL.state-style bounded
  execution state — carries `SKILL_STATE_PRODUCT_RENDERER_INTEGRATED = False`
  and reaches no prompt.
- Research verification generally: a research claim has no test suite.
- Never run unattended for a real night on real work.

---

## Part 4 — Building this

### From scratch

The minimum viable version, in dependency order:

1. **Intake.** Read agent transcripts. Extract `tool_use`/`tool_result` pairs
   where a command failed and was never later seen succeeding. Rank gate
   commands above everything. Never read assistant prose — it asserts
   outcomes it did not verify. Drop timeouts and one-off non-gate failures.
2. **Gameplan.** For each candidate, state before any model call: the gate,
   what acceptance means, and whether it is verifiable at all. Written first
   and kept, so the morning report shows intent beside outcome. A plan
   produced after the attempt is shaped by how the attempt went.
3. **Worktree isolation.** `git worktree add -b <branch> <dir> HEAD`. Never
   the engineer's checkout.
4. **Composed steps.** A directory per step with an agent file (prompt,
   tools, permissions) and skills. Deny **all** write-capable tools on
   read-only steps. Never `ask`.
5. **Gate before and after.** Exit code decides. Never ask a step whether it
   succeeded.
6. **Failure changes the step, not the wording.** Compose an observation step
   with no write tools and engine-supplied command output.
7. **Night budget.** Hours in, grants out.
8. **Morning report.** Verified / attempted / skipped / nothing-found, each
   with the real gate output.

### Integrating loop-engine

The integration point is one object. Implement four members:

```python
class YourSession:
    authority: Any        # .max_model_calls
    results: list         # append one ModelGatewayResult per call
    calls_used: int       # physical calls charged
    def invoke(self, request, parent_loop) -> str: ...
```

Assign it to `AdaptiveRunServices.model_session`. Every cognitive step is
redirected; nothing else changes. `core/opencode_step_session.py` is a
working reference implementation, including budget enforcement before a
process starts, event parsing, fenced-JSON recovery, and projecting each turn
into a `ModelGatewayResult` so accounting and run history see it normally.

What loop-engine gives you that is genuinely hard to rebuild: the conformance
layer (21 detectors, 33 zero-tolerance gates), Docker sandboxing with
digest-pinned images, typed run history, and ~2,900 in-module checks.

What it does not give you: intake, worktree isolation, the night budget, or
composed per-step instances. Those are the files listed below.

### The files

| file | role |
|---|---|
| `core/opencode_step_session.py` | model_session backed by headless OpenCode |
| `core/opencode_step_composition.py` | layer machinery, validation, digests |
| `core/opencode_step_layers.py` | the concrete steps and skills |
| `core/step_content.json` + `.py` | 14 generated steps, 27 skills, validated on load |
| `core/opencode_step_guard.py` | workspace guard, engine-side observation |
| `core/night_budget.py` | hours in, grants out |
| `tools/session_intake.py` | find the day's unfinished work |
| `tools/overnight.py` | the 5pm run |
| `tools/opencode_loop.py` | the composed loop, end to end |
| `tools/policy_edit.py` | typed CRUD for policy JSON |
| `tools/refusal_census.py` | rank refusals by what actually fires |

---

## Part 5 — How to judge a rebuild

If Kimi 3.0 or GLM 5.3 build this, these are the questions that separate a
working system from a demo. Every one of them caught a real defect here.

1. Compose a read-only step, tell it to edit a file **using any means
   including delegating to a subagent**, and hash the file. If it changed,
   the permission model is decorative.
2. Run the gate, then run the system again. If creating `__pycache__` makes
   it refuse to work, it disables itself after its own first run.
3. Kill it mid-run. Is the engineer's checkout on the same branch, with the
   same contents? Did it write any diagnostics before dying?
4. Give it a failing test whose **expectation** is wrong, not the code. Does
   it "fix" the working function?
5. Give it a task where nothing is broken. Does it report that, or invent
   work?
6. Ask what verifies a claim of success. If the answer is the model's own
   report, the verdict is worthless.
7. Time a scaling-sensitive check on a loaded machine. A verdict that changes
   with what else is running is not a verdict.
8. Return correct JSON inside a ` ```json ` fence. Is it accepted?
