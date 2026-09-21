# The overnight command on a local model, September 21, 2026

Kind: dated evidence record. It reports what happened on one machine on one
afternoon, including the attempts that did not work. It is not a benchmark,
and no number here is a rate that another machine will reproduce. Read
[the records index](../RECORDS-INDEX.md) for the route to other evidence.

## What was built

One command, `loop-engine overnight`, with four operations: `check`,
`start`, `resume` and `report`. The preflight is
`src/loop_engine/core/local_model_readiness.py`. The declared authority and
the residency policy are in
`src/loop_engine/code_nodes/overnight_authority.py`. The record that
survives an interruption is
`src/loop_engine/code_nodes/overnight_journal.py`. The loop itself is
`src/loop_engine/code_nodes/overnight_night.py`, and the command is
`src/loop_engine/overnight_cli.py`.

The narrative guide for overnight work on local models is being written on
the branch `wave3/overnight-local` and is not on this branch, so it is named
here rather than linked. A link to a file that is not on the branch fails
the documentation link check.

## The machine, and the state it was in

| Part | Value |
|---|---|
| Video memory | NVIDIA GeForce RTX 3060, 12288 MiB |
| Model | `qwen2.5-coder:7b`, 7.6 billion parameters, Q4_K_M |
| Server | a local server on `http://127.0.0.1:11434`, version 0.32.6 |
| Context the server reports | 32768 |
| Context the night asked for | 8192 |

Two facts about the state matter for every timing below, and both were
observed rather than assumed.

The card was not free. `nvidia-smi` reported 10808 MiB of the 12288 MiB in
use and 1096 MiB free, because two earlier server processes were still
holding 6434 MiB and 3006 MiB. The server therefore loaded the model with
part of it outside video memory: `/api/ps` reported `size_vram` of
3017539583 bytes for a model whose file is 4683087561 bytes.

The machine was busy. Other work on the same machine was running the
repository's own conformance and self-test suites throughout, and the load
average was between 69 and 76 for the whole period. Every elapsed time
below was measured under that load.

## What was run

Three nights on the same small real problem, plus one interruption
exercise. The problem: a `chunk(items, size)` function that drops the final
partial piece and returns nothing when the size is larger than the list.
The gate is a script that checks five cases and exits non-zero. Before the
first night the gate failed two of its five cases, so the starting state was
known wrong.

### The preflight, against the real server

Five questions, all answered by the server or declared by the operator.
Every refusal path was exercised against the real server:

| Declared | What the check said | Exit |
|---|---|---|
| `--video-memory-mib 12288` | ready; 5682 MiB needed of 12288 declared, 6606 MiB left, longest context that fits 32768 | 0 |
| `--video-memory-mib 1096`, the memory actually free | refused: 5682 MiB needed and 1096 MiB declared; the weights alone do not fit | 2 |
| no `--video-memory-mib` | refused: the memory a model may occupy was not declared and this check cannot read the card | 2 |
| `--base-url http://127.0.0.1:1` | refused: no local model server answered at that address | 2 |
| `--model not-a-model:1b` | refused: the server answers but does not hold it, and it named the six it does hold | 2 |

The key and value cache arithmetic uses the layer count, key and value head
count and embedding length the server reports through `/api/show`, so
nothing was guessed. The check refuses rather than substituting a default
when the server reports no context length.

### The residency instruction reached the server

The night declares how long the server keeps the weights loaded and sends
it. After a call with the residency set to 1800 seconds, `/api/ps` reported
`expires_at` about thirty minutes ahead. After the night declared 8192
context tokens, `/api/ps` reported `context_length` 8192 for the loaded
model, where it had reported 4096 before. Both instructions are declared
fields on the endpoint record, not defaults.

### One call through the adapter, before any night

The engine's own `make_adapter` over a `CustomEndpoint` with wire `ollama`,
locality `local` and authentication `none`, over a real socket. The endpoint
record reported `has_key` false. The server reported 55 prompt tokens and 17
output tokens, and the call took 98.04 seconds with the weights not yet
loaded at that context length.

## What each night did

### Attempt one: the run blamed the server for its own deadline

Declared authority: 0.5 hours, 14 model calls, the working folder as the
only readable and writable folder, the gate script, residency for the whole
night, and no output allowance, so each call asked for the full declared
capacity of 32768 tokens.

The first step answered in 90.4 seconds; the server reported 208 prompt
tokens and 29 output tokens. The second step ran past the 342 second grant
the night gave it and the adapter reported `TimeoutError: timed out`. The
run read that as the server going away, waited, probed, and ended the night
as `PROVIDER_UNAVAILABLE` after 522.6 seconds and three physical calls,
while the server was answering the whole time.

That is a defect in the run, not in the server. Our own deadline expiring is
a budget event that belongs to the run. It is now separated:
`classify_call_failure` returns `deadline`, `outage` or `refusal`, a
deadline becomes `narrow_the_request`, and the check
`a_step_over_its_time_grant_narrows_rather_than_blaming_the_server` fails
if a timeout is treated as an outage again.

The same attempt showed two smaller defects. A step that answered with a
well formed but empty object left the round looking like a step that had
worked; an empty object is now recorded as a step that gained nothing. The
morning report said no gate was declared when one was declared and had
never run; it now distinguishes the two.

### Attempt two: the gateway refused the reduced output ceiling

With `--max-output-tokens 600` passed as a bare number, every call was
refused by the engine's own model capability contract:
`requested output limit 600 is not the declared model maximum 32768; Loop
Engine does not invent or reduce model output ceilings`. That is the
contract working as written.

The night behaved correctly around it. Each refusal became
`narrow_the_request`, the run carried on, and it ended on `BUDGET_EXHAUSTED`
after exactly the 14 declared calls. It did not end on an attempt count.

It also showed a weakness: it asked fourteen times in fourteen different
words for something no wording could change. One refusal repeated at every
step of a whole round is now a `CAPABILITY_GAP`, which is the ending
"question only a person can answer", and the refusal is quoted in the
report. Two different refusals still do not end the night, and a check
covers both cases.

The allowance now travels as a typed `ModelOutputAllocation`, with the
capacity read from the server, the route named, and the reason recorded.
Without `--max-output-tokens` the full declared capacity is requested, as
the model gateway requires.

### Attempt three

Declared authority: 0.5 hours, 14 model calls, `--max-output-tokens 700` as
a typed allocation, the same folders and the same gate.

The numbers from this attempt are recorded in the section below, together
with what the night did about each failure.

## What was observed, and what was not

Observed on this machine, in a real run against a real server:

- The preflight answers in under a second and refuses with a plain sentence
  in each of the four ways a night can be impossible.
- The declared residency and the declared context length reach the server
  and change what it loads.
- The authority is enforced at the moment of use. Attempt three's first step
  asked to read `/home/username/projects/chunk_list.py`, a path it invented,
  and the night refused it and wrote the refusal to the journal.
- Every model call is written to the journal before it happens and again
  after, so a process killed in between leaves a record that says the
  outcome is unknown.
- Token counts come from the server or stay unknown. Attempt one recorded
  208 prompt tokens, 29 output tokens and one call with no usage reported,
  which is the call that timed out.

Not observed, and not claimed:

- No night reached a verified result on this machine. The gate that decides
  success never passed during these attempts.
- No speed, cost or quality figure is claimed for this model. The elapsed
  times above were measured while the machine was running several other
  suites and while the model was partly outside video memory, so they
  describe this afternoon and nothing else.
- A full night of eight or twelve hours was not run. The longest declared
  authority used here was half an hour.
- The morning report, the journal and the resume path were exercised, but no
  run was left unattended overnight.
