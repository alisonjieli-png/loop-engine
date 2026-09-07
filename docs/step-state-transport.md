# Carrying state between steps: the mechanism, and every transport for it

Each cognitive step runs in its own process. Something has to carry what the
run knows from one step to the next. This documents the mechanism now
implemented, and every transport that mechanism could ride on, with the
measurements that decide between them.

## Part 1 — The mechanism (implemented)

`core/step_state.py`. Each step receives exactly three things:

| | |
|---|---|
| **P** | the immutable procedural specification — the step's own prompt |
| **S** | the current structured state, a flat typed record |
| **O** | the latest observation — real command output, not a summary |

and returns a **patch** to S. Once the patch is validated and applied, the
reasoning that produced it is discarded and never appears again. This
follows SKILL.state ([arXiv 2608.26263](https://arxiv.org/html/2608.26263)),
which reports a 16.2× cumulative-token reduction at a 100-step horizon. Only
the mechanism is reproduced here, not that figure.

### What it replaced

```python
carried = json.dumps(value)[:1200]     # the previous implementation
```

Growth was quadratic — every step re-read everything before it — and the cut
at 1200 bytes removed whichever fact happened to be serialized last,
silently, with no way for the next step to know something was gone.

### Measured, 40 steps, this repository

| step | accumulating transcript | bounded state |
|---:|---:|---:|
| 1 | 314 | 681 |
| 10 | 2,384 | 817 |
| 40 | 9,284 | 858 |

**Growth: 29.6× versus 1.3×. Cumulative characters: 191,960 versus 33,156 —
a 5.8× reduction at 40 steps**, widening with every further step. Bounded
state costs *more* at step 1 and less from about step 4 onward.

### Design decisions and why

**A patch, not a replacement.** A step returning the whole next state can
silently drop a field it did not think about, and the run cannot distinguish
"deleted deliberately" from "forgot to mention". Deletion must be spelled:
`null` removes a key, and is the only way to.

**A closed schema.** An unknown field is refused, not stored. A state that
accepts anything becomes a second transcript within a few steps and the
bound is gone.

**Immutable identity.** `task` and `gate_command` can never be patched. A
step that could rewrite either could redefine success into something already
achieved.

**Lists append and cap.** A step that observed one more file should not erase
the others by reporting only what it saw; the cap is what keeps append from
becoming accumulation.

**A rejected patch keeps the state.** Discarding everything because one step
returned a bad field would lose every earlier observation.

---

## Part 2 — Transports

The mechanism says *what* moves. This says *how*. Two measurements on this
machine decide most of it.

### Measurement 1 — the CLI transport has a hard ceiling, and we are near it

```
ARG_MAX                     2,097,152 bytes
max single argv element       130,945 bytes   (~128 KB, MAX_ARG_STRLEN)
```

A step prompt is passed as **one** argv element, so 128 KB is the wall. A
real `orient` prompt measured **17,722 input tokens ≈ 70 KB** — already over
half. This is not a theoretical limit; a larger workspace manifest or a
longer failure excerpt reaches it.

### Measurement 2 — argv is world-readable

```
/proc/<pid>/cmdline    -r--r--r--    (mode 444)
```

Verified: a marker string passed as a prompt was visible in `ps -eo cmd` and
readable from `/proc/<pid>/cmdline` by any local user. **Every step's full
prompt — proprietary source, customer data, credentials quoted inside an
error message — is exposed to every user on the machine.** On a shared build
host or a multi-tenant runner this is disqualifying on its own.

### The transports

| # | transport | size limit | durable | resumable | readable by others | cross-host |
|---|---|---|---|---|---|---|
| 1 | in-process (no transport) | RAM | no | no | no | no |
| 2 | **argv** (current) | **128 KB** | no | no | **yes** | no |
| 3 | environment variable | ~128 KB | no | no | **yes** (`/proc/pid/environ` for same user) | no |
| 4 | stdin pipe | none | no | no | no | no |
| 5 | **file + path pointer** | disk | yes | yes | file mode | shared FS only |
| 6 | content-addressed blob + digest | disk | yes | yes | file mode | with a shared store |
| 7 | **SQLite / DuckDB row + row id** | disk | yes | yes | file mode | no (single writer) |
| 8 | Postgres row + row id | disk | yes | yes | grants | yes |
| 9 | shared memory / mmap | RAM | no | no | perms | no |
| 10 | message queue | broker | yes | yes | ACLs | yes |
| 11 | HTTP state service | none | depends | yes | authz | yes |

#### 1. In-process

No serialization, no boundary. This is `ModelExecutionSession`. Fastest and
simplest; gives up isolation, per-step tool permissions, and crash
containment. Still the right choice when a step is cheap and the isolation
buys nothing.

#### 2. argv — no longer the default

Simple, synchronous, no extra dependency, and the natural fit for
`opencode run "<prompt>"`. Both measurements above are against it. Still
available via `prompt_via_file=False`, and in that mode a prompt larger than
the ceiling is now **refused by name** rather than failing the exec with an
opaque `E2BIG` from inside `subprocess`.

#### 3. Environment variable

Same ceiling, and `/proc/<pid>/environ` leaks to the same user. Its one real
use is passing a *pointer* — a path or a row id — never a payload. This is
already how `OLLAMA_API_KEY` reaches a step, through an explicit allowlist.

#### 4. stdin

Removes the size ceiling and the `ps` exposure for the cost of the child
having to read stdin — which `opencode run` does not do for its message.
Worth requesting upstream; it is the smallest change that fixes both
measured problems at once.

#### 5. File + path pointer — IMPLEMENTED, and now the default

Write the prompt to a mode-**600** file inside the composed instance
directory and pass `--file <path>`; argv carries only a constant sentence.

`OpenCodeStepProfile.prompt_via_file` defaults to `True`. Verified live: a
real `orient` step ran to a correct answer through this path.

| | argv transport | file transport |
|---|---|---|
| 84,000-byte prompt | exceeds the 128 KB element ceiling as prompts grow | **53 bytes** in argv |
| visible in `ps` | the entire prompt | one constant sentence, identical every step |
| file mode | n/a | `0600`, opened `O_CREAT` at 0600 so it is never briefly world-readable |

One detail that cost a debugging round: `--file` is an **array** flag, so a
trailing positional message is consumed as another filename and OpenCode
exits with `File not found: <the whole message>`. The message must come
immediately after `run`.

Cleanup is still owed — the prompt file lives in the instance directory,
which is per-step and disposable, but nothing prunes it explicitly. Same
class as the orphaned worktrees found here, where a killed run left 62 MB
behind and nothing removed it.

#### 6. Content-addressed blob + digest pointer

The file, keyed by `sha256(content)`. Identical state is stored once,
pointers are immutable, and a step's inputs are provably the bytes claimed
because the digest *is* the name. Fits this codebase, which already digests
core layers to make drift detectable. Best when many steps share large
context; adds a garbage-collection question.

#### 7. SQLite / DuckDB row + row id

**The variation asked about.** State becomes queryable: "which steps saw
this file", "how did the hypothesis change", "which runs were blocked on
credentials" become SQL rather than log-grepping. Transactional, so a
half-written state cannot be read. DuckDB additionally reads Parquet and CSV
in place, so a data-pipeline task's actual inputs sit beside the run state.

Costs: a dependency, a schema to migrate, and single-writer semantics —
SQLite serializes writers, so parallel steps queue. Fine for one run;
a constraint if steps fan out.

**Where this repo already does this and where it deliberately does not.**
Run records and intelligence belong in the record layer, and this repository
has one: `record_operations`, `duckdb_catalog`, `store_serve`,
`intelligence_registry`. Conformance *policy* deliberately stays a flat JSON
file read with `open()`, because the gate must run on a fresh checkout in CI
with no storage stack imported, and policy that needs infrastructure to read
is policy that can be unavailable. Step state is a **record**, not policy —
so it is on the right side of that line and belongs in the catalog.

#### 8. Postgres row + row id

Everything SQLite gives, plus concurrent writers and cross-host access —
which is what a hosted product needs. Costs a service to run and secure.
The step's identity becomes a row id, and the row is the audit trail.

#### 9. Shared memory / mmap

Fastest possible cross-process handoff, no serialization for a suitable
layout. Same host only, no durability, and lifetime management is easy to
get wrong. Justified only if state handoff is measured to be the bottleneck,
which here it is not: state renders to **858 characters** after 40 steps.

#### 10. Message queue

Decouples producer from consumer, gives durability and ordering, survives a
consumer restart, and lets steps run on different machines. Real operational
weight. Right when steps are genuinely distributed; overkill for a nightly
run on one laptop.

#### 11. HTTP state service

The hosted answer: any worker anywhere reads and writes through authz. Adds
a network dependency to every step, which for an unattended overnight run
means a new way to fail at 3am with nobody watching.

### What to use

1. **Now: transport 5, and it is what runs.** Both measured problems are
   closed. Nothing upstream was needed.
2. **Next, small:** make it content-addressed (transport 6) so identical
   state is stored once and a step's inputs are provably the bytes claimed —
   the same digest discipline the core layer already uses.
3. **For queryability:** transport 7, through the record layer that already
   exists. This is what makes "which runs were blocked on credentials" a
   query instead of a grep.
4. **For a hosted product:** transport 8 or 11, when there are workers rather
   than a laptop.

A useful property of the mechanism: **it is transport-independent.**
`StepState` serializes to JSON and `render_step_prompt` is the only place a
prompt is assembled. Changing transport is changing where those bytes are
put, not changing what steps receive.

## What is not solved

- **Cleanup.** Every durable transport accumulates. This system already
  learned that: a killed run left a 62 MB worktree and nothing removed it.
  Any file, blob, or row transport needs the same pruning that worktrees now
  have.
- **Fan-out.** Everything above assumes sequential steps. Parallel steps
  patching one state need a merge policy, and last-writer-wins silently
  discards work.
- **Secrets in state.** The schema is closed, but nothing stops a step
  putting a credential into `observed_failure` if a command printed one. A
  durable transport makes that persistent rather than transient — which is
  an argument for redaction before storage, not against durability.
