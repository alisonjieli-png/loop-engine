# Everything learned, 2026-09-08

One file, written to be handed to whoever picks this up next. It records what
was measured, what broke, what is still unknown, and where each thing lives.
Every number here came from running something on this machine on this date.
Where a claim is not measured, it says so.

Read [START-HERE.md](START-HERE.md) first if you have never seen this project.
Read [INVARIANTS-AND-TRAPS.md](INVARIANTS-AND-TRAPS.md) before changing
anything. This file is the third one: what the last round of work found out.

## 1. Verified state at the time of writing

| Check | How it was run | Result |
|---|---|---|
| Full engine self-test | `python -m loop_engine --self-test` | PASSED, 3412 of 3412 checks, 1392 seconds, 0 provider calls |
| Conformance gates | `run_conformance()` | all gates pass, 430 files scanned |
| Repository structure | `structure_report()` | 0 violations |
| Reachability from a solve | `reachability_report("solve_path")` | 240 of 430 modules |
| Reachability from the command line | `reachability_report("command_line")` | 290 of 430 modules |
| Embodiment catalogue | `registry.py check` | 30 embodiments, 7 families, all self-checks pass |

The self-test takes about 23 minutes. Budget for that before assuming it hung.

## 2. What was built: a catalogue of 30 embodiments on 7 axes

It lives in `devtools/embodiment_axes/`. It does not run the canonical
runtime, implements every design from scratch against one shared task, and
grants no authority. It exists so a design choice can be measured instead of
argued about.

| Axis | The question it answers | Arms |
|---|---|---:|
| `context-transport` | How does information reach a step that runs elsewhere | 8 |
| `control-flow` | Who picks the next unit of work, and how much per call | 4 |
| `decomposition` | How is the work divided before any of it starts | 4 |
| `execution-placement` | Where does a step physically run | 3 |
| `failure-handling` | What does the loop do when a step fails | 4 |
| `memory` | What does an earlier run contribute to a later one | 4 |
| `verification` | How does an answer get accepted | 3 |

```bash
cd devtools/embodiment_axes
python3 choose.py --units 5000 --workers 8 --untrusted-steps --stakes high
python3 registry.py check          # manifests, imports, self-checks, chooser rules
python3 registry.py run            # all seven families through their harnesses
python3 registry.py catalog        # regenerate CATALOG.md and every README
```

Discovery is by folder. Nothing is registered in a list, so the catalogue
cannot go stale against what is on disk. A manifest without non-empty `cons`
and `avoid_when` is refused by `check`, because an option with no stated cost
is an advertisement rather than a choice.

### Why the measurements can be trusted, and where they cannot

The thing that reads a prompt is a pure function that plays perfectly on
whatever the prompt contains. It has no memory between calls and never touches
the world. So an arm that carries what a step needs succeeds and an arm that
loses it fails, and the comparison measures structure rather than reasoning.

That is also the limit. **Nothing here says whether a real model reasons well
with any of these designs.** It is the largest open question and it is
deliberately outside a run that costs nothing. Bytes were counted, not
provider tokens. One task shape, one world generator, one window size.

## 3. The eight findings that change decisions

**Constant context is a property of the schema, not of the architecture.** The
state arm was written to carry a fixed amount per step and does not. Two of
its fields are lists with one entry per unit, so its prompt reaches 10,165
bytes at 1,024 units. The bounded arm carries the same information as five
scalars, a mapping over a closed vocabulary and a cursor, and moves 37 bytes
across a 256-fold increase in horizon. Same answers, one tenth the total
bytes. The lesson is procedural: you cannot check this by reading a design
description, and the thing to look for is any field proportional to the
horizon.

**Bounding the schema and batching are separate wins, and most designs take
only one.** The transport comparison held one unit per call fixed, so it could
not see this. At 1,024 units, one unit per call costs 1,025 calls and 981,450
bytes. Folding 64 units per call costs 22 calls and 138,096 bytes. Both
numbers fall, by 47 times and 7 times, because the task text and the state
stop being re-sent for their own sake. Get the schema bounded first, then
batch as hard as the window allows.

**A de-duplication list only has to name what is currently in the prompt.**
This is what lets a transcript design stay flat. An entry that has been folded
into a summary and dropped from the raw tail cannot be folded twice, because
it is not there to fold. The list is then bounded by the tail rather than by
the horizon, and the arm keeps raw recent detail without a growing prompt.

**An answer cache buys one call out of seventeen over a checkpoint store, and
pays for it with everything.** A checkpoint store keeps positions and never
keeps conclusions, so the worst a corrupted one can do is start from a wrong
subtotal, which recomputation catches. It reached 1 call on a repeat against a
17 call cold run. The cache reached 0 by serving a stored conclusion, and when
an outsider staged a wrong one, the run returned it as its own answer. The
governed journal reached 0 as well and refused the same record, because
nothing promotes itself.

**A threshold about the work beats a count about the machine.** Fixed and
recursive splitting both reached 4 times the parallelism at 24 units. At 256
the fixed split was still at 4 times, because someone had set the group count
to four, while the recursive split reached 32 times without anyone changing
anything. A group count states how many workers exist. A leaf threshold states
how big a piece should be, and only the second still means the same thing when
the input grows.

**Skipping a failed unit converts a visible failure into an invisible one.**
It is the only policy that finished a run containing an unfixable failure, and
the answer it returned did not match the truth. That is not a reason to reject
it, because partial results are the right answer for plenty of work. It is a
reason to pair it with independent recomputation. Together they give a
finished run and an honest refusal, where either alone gives one or the other.
This is the clearest case in the catalogue of two choices being safe only in
combination.

**Containment costs about 14,000 times a function call, per step.** That makes
placement a per-step decision rather than a per-system one. A run that takes
one untrusted action and a hundred trusted ones should not pay containment a
hundred and one times.

**A structural verification gate is stronger than expected and has exactly one
blind spot.** It caught four of five injected faults for no extra reads,
including two that looked like they would need recomputation. The check that
earned its place is the cheapest and the most often skipped: does the answer
agree with the state the same run carried. What it cannot catch is a fault
that agrees with itself at every level a rule can check, and that case needed
a full second pass over the world.

## 4. The measurements

Peak prompt bytes, seed 11, 16,000 byte window. `failed` means the arm was
refused by the window rather than truncated.

| units | monolith | full_history | state_patch | horizon_state | pull_reference | bounded_state | summarised | hybrid |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 4 | 1,023 | 1,084 | 950 | 1,012 | 1,059 | 949 | 1,308 | 922 |
| 256 | failed | failed | 2,993 | 3,057 | 3,102 | 979 | 1,474 | 951 |
| 1024 | failed | failed | 10,165 | 10,229 | 10,275 | 986 | 1,487 | 957 |

Total prompt bytes at 1,024 units, all arms that solved:

| Arm | Calls | Total bytes |
|---|---:|---:|
| hybrid_push_pull | 1,025 | 971,285 |
| bounded_state | 1,025 | 1,000,925 |
| summarised_history | 1,025 | 1,504,060 |
| state_patch | 1,025 | 10,409,501 |
| horizon_state | 1,025 | 10,475,013 |
| pull_reference | 2,050 | 10,880,374 |

Control flow at 1,024 units, all four correct:

| Arm | Calls | Total bytes | Peak prompt |
|---|---:|---:|---:|
| one_at_a_time | 1,025 | 981,450 | 967 |
| model_chosen_next | 1,025 | 5,668,863 | 10,085 |
| fixed_batch, K=8 | 128 | 224,585 | 1,771 |
| adaptive_batch | 22 | 138,096 | 8,380 |

Decomposition. Longest chain is serial depth, meaning what the run still costs
if every group has its own worker. It is a lower bound on wall time, not a
measurement of one.

| Design | Calls at 256 | Longest chain | Parallel factor |
|---|---:|---:|---:|
| single_pass | 257 | 257 | 1.0 |
| fixed_split, 4 groups | 260 | 65 | 4.0 |
| recursive_split, leaf 8 | 288 | 9 | 32.0 |
| portfolio, 3 candidates | 382 | 382 | 1.0 |

Placement, same loop, 13 calls each:

| Placement | Per call | What it contains |
|---|---:|---|
| in process | 0.10 ms | nothing |
| a fresh interpreter per step | 194 ms | process memory only, same filesystem, network and user |
| a container per step | 1,398 ms | no network, read-only mount, all capabilities dropped, memory and process limits |

These two are single-run wall-clock figures and they move. Across two runs the
subprocess figure ranged from 194 to 275 milliseconds and the container figure
from 1,398 to 1,413. The ratio is the durable part, not the digits: a process
boundary is roughly a thousand times a function call and a container is
roughly five times a process. The container was timed with a warm image.

Verification, five injected faults and one clean control:

| Policy | Caught | Extra reads | Rejected the clean run |
|---|---:|---:|---|
| self report | 0 of 5 | 0 | no |
| engine gate | 4 of 5 | 0 | no |
| independent recompute | 5 of 5 | 96 | no |

Memory, sixteen units, cold run then a second run, plus resume and an outsider
staging a wrong answer:

| Design | Cold calls | Repeat calls | Resumes | Served the poison | Answered wrongly |
|---|---:|---:|---|---|---|
| none | 17 | 17 | no | no | no |
| checkpoint and resume | 17 | 1 | yes | no | no |
| cross-run cache | 17 | 0 | yes | yes | yes |
| governed journal | 17 | 0 | yes | no | no |

Failure handling, five failure shapes, every arm given the same four attempt
budget so the policy is what varies:

| Policy | Recovered | Cost of the failure nothing fixes | Answered anyway |
|---|---:|---|---|
| stop on first | 0 of 4 | stopped after 4 calls | no |
| retry the same request | 3 of 4 | exhausted after 4 calls | no |
| retry then escalate | 4 of 4 | exhausted after 4 calls | no |
| skip and continue | 3 of 4 | 12 calls | yes, and wrongly |

## 5. Five defects that only running found

Each was invisible to reading the code that contained it. This is the argument
for the whole exercise, so they are listed rather than quietly fixed.

**A checkpoint that dropped its position.** The resume store kept the running
subtotal and not the cursor it was a subtotal of. A resumed run re-read what
the subtotal already contained, counted it twice, and answered confidently.
The two now travel in one signature, and there is a check asserting that
resuming with the subtotal alone produces a wrong answer, so the defect cannot
be reintroduced by accident.

**Compaction that dropped an observation before anything read it.** The
summarising arm discarded oldest-first by age. With a tail budget smaller than
one observation it discarded the observation that had just arrived. Dropping
is now conditional on the entry already being folded.

**A slicer that returned six groups when seven were asked for.** The fixed
split rounded the group size up. The answer was never wrong, which is why it
would have survived review, but a caller sizing a worker pool to the count it
requested would have been quietly wrong about how much parallelism it had.

**A fault written to be the hard case that was the easy one.** An arithmetic
error was injected by moving the total without moving the account breakdown.
The structural gate caught it immediately, because the answer then disagreed
with itself. A second fault now moves the total, the breakdown and the count
together, and that one only recomputation catches. Both are kept.

**Identifiers three digits wide.** From an earlier round. At 1,024 units the
identifier `s1000` matched a pattern written for `s100`, two units resolved to
one name, and 3,000 of 4,000 reads were repeats. Nothing about it is visible
below 1,000 units. Identifier width now scales with the population.

## 6. What this project's actual problem is

**It is wiring, not capability.** A solve reaches 240 of 430 modules. The
command line reaches 290. The gap is not dead code that should be deleted; it
is built capability that no live path calls.

The sharpest remaining case is memory. Of 32 modules with `memory` in the
path, 18 are unreachable from a solve:

```text
loop_engine.memory                    the package itself
loop_engine.memory.episodic
loop_engine.memory.semantic
loop_engine.memory.working
loop_engine.memory.storage
loop_engine.memory.lifecycle
loop_engine.memory.loop_integration
loop_engine.memory.procedural         and 2 modules beneath it
loop_engine.memory.query              and 1 module beneath it
loop_engine.memory.model              and 4 modules beneath it
loop_engine.catalog.stores.in_memory
```

Reproduce that list with `reachable_from("loop_engine.code_nodes.solve_runtime")`
in `src/loop_engine/reachability_report.py`, differenced against the shipped
module set. One leaf under `loop_engine.memory.query` is named for a term the
project has retired from public prose, so it is counted here rather than
spelled out, which is also why the list shows subtrees instead of every leaf.

So there is a full memory subsystem with episodic, semantic, procedural and
working layers that a solve never touches. Eight of ten reactive modules and
two of three OpenCode modules are also dark from a solve.

This has improved. An earlier count in this campaign was 129 of 406 modules
reached, with 1 of 20 memory modules. Wiring approved learned memory into the
solve path moved all five learning modules into reach. The same treatment
applied to the memory subtree is the highest-value work available, and
`reachability_report.py` measures whether it worked.

Use `REQUIRED_REACHABLE` in `src/loop_engine/reachability_report.py` to make a
module's reachability a gate rather than a hope. A module added there that
stops being reachable fails the check.

## 7. The node context transport question, answered

The question was how information should reach a loop node running as its own
process, and whether a database reference with an identifier beats sending the
content.

**A command line cannot carry the packet.** Measured mean packet size was
about 139 KB against a `MAX_ARG_STRLEN` ceiling of 131,072 bytes per element.
It also leaks: `/proc/<pid>/cmdline` is mode 444 and readable by any process
on the host, so anything on a command line is public to the machine.

**Passing a reference does not shrink context. The schema does.** This is the
finding that settles the design argument. The pull arm needed 2,050 calls
where the push arms needed 1,025, and sent more total bytes, not fewer,
because a seed plus a served payload is larger than the payload alone. The
rule the numbers support: pulling wins only when a step needs a small fraction
of what a push would send. When every step needs the whole accumulator, that
fraction is one and pull is strictly worse.

**The useful version is a budget, not a doctrine.** The hybrid arm pushes the
state while it fits a byte budget and fetches by name when it does not. Above
the state size it is a push design, below it a pull design, and it was the
cheapest arm at every horizon measured. Make it a dial and stop arguing.

Framed standard input remains the right transport for the packet itself, which
is what the OpenCode bridge under `examples/25_host_runtime/` already does.

## 8. Three embodiment catalogues exist on this machine

They are cut three different ways and are complementary. Knowing which is
which saves rediscovering all of it.

| Where | Organised by | What it is for |
|---|---|---|
| `~/overnight/embodiments/` | whole architecture, 17 folders with a race runner | racing complete approaches end to end against a project's own gate |
| `~/loop-engine/embodiments/` | execution mechanism, 12 folders | runnable launch surfaces for the canonical runtime |
| `~/loop-engine/devtools/embodiment_axes/` | orthogonal design axis, 30 folders | measuring which single choice is doing the work |

The third answers a question the first two cannot. When a race picks a winning
architecture, it does not say why that architecture won. The axis measurements
say the answer is usually the state schema and the batch size, because those
effects are 10 times and 47 times respectively and dwarf most differences
between named architectures.

Sizes for orientation: `~/overnight` has 1,015 tracked Python files,
`~/loop-engine` has 646, `~/vigil` has 54.

## 9. Operational lessons

**A second agent commits into this same checkout.** Stage explicit paths, never
`git add -A`. During this session another agent had uncommitted edits to
`README.md`, `architecture.yaml`, `devtools/README.md`,
`src/loop_engine/repository_conformance.py` and
`src/loop_engine/repository_structure.py`, plus untracked `embodiments/` and
`docs/architecture/ADR-EXPERIMENTAL-EMBODIMENTS.md`. Committing a new
top-level folder would have needed their unpushed approval line in
`APPROVED_TOP_LEVEL`, so the new work went under `devtools/`, which is already
approved. Check `git status` before choosing a location, not after.

**Never use a broad process pattern to kill anything.** A `pkill -f` on a
generic module name killed another session's run in an unrelated directory
earlier in this campaign. Run gates under a name nothing else matches. The
self-test here ran as `axes-gate-check` for exactly that reason.

**Parallel implementer agents hit a session rate limit.** Three died with HTTP
429 before writing any code. Sequential in-session work finished the same job.

**Local model endpoints on this machine are cloud proxies.** A run marked
`--backend local` still spends money. Ask before spending; assume nothing from
the word local.

**A check that passes locally can fail on every CI interpreter.** A
nesting-depth assertion passed here and failed on all three CI Pythons because
their decoder handled 1,500 levels. The fix was to probe for the depth the
interpreter actually refuses rather than assume one. Prefer measuring the
environment to asserting about it.

**Gate failures and their fixes, as a checklist.** Adding a module to
`src/loop_engine/` triggers these in this order:

1. `unclassified_files` fails. Add the module to `architecture_map.py`.
2. `architecture_map_freshness` fails. Regenerate `ARCHITECTURE-MAP.md` from
   `render_map()`.
3. `modules_whose_self_test_the_suite_never_runs` fails. Add it to
   `_FOLDED_SUBMODULE_TESTS`.
4. `subprocess_outside_declared_adapters` fails if you shell out. The
   reachability report was rewritten as a static import closure over the
   abstract syntax tree for this reason, and it is better for it.

**Documentation lint is real.** `.vale.ini` refuses em-dashes and en-dashes
everywhere, plus a list of retired terms and retired topology words in
`.vale/styles/LoopEngine/`. Write around them rather than adding exemptions.

## 10. An environment hazard that is not this project's

`/home/username/.local/lib/python3.14/site-packages/usercustomize.py`, created
2026-09-08 at 00:21, 1405 bytes, not written by this campaign. Python imports
`usercustomize` automatically in every process for this user, so it is not
scoped to one project.

It wraps `pandas.read_csv`. Any comma separated file carrying both a
`stock_status` and a `qty` column comes back as a subclassed frame whose
comparisons lie. Verified live on this date: with every `qty` equal to 900,
`bool((df['qty'] <= 50).all())` returned `True`. The companion status branch is
buggy and raises `AttributeError`, so half of it fails loudly while the other
half fails silently.

Any measurement or gate on this machine that validates such a file cannot be
trusted while that file exists. It was reported to the owner and left in place,
because it was not written by this campaign and removing another party's file
without asking is the wrong default.

## 11. What is not established

- Whether a real model reasons well with any of the measured designs. Every
  number above came from a perfect fixture reader.
- Whether labelling state by horizon helps. The labelled arm costs 60 to 65
  bytes more per prompt and is identical in correctness against a perfect
  reader by construction, so this harness can price the labels and cannot
  value them.
- Whether a model offered a fetch mechanism asks for what it needs or asks for
  everything. The ledger log answers it directly and the answer decides
  whether a pull design is worth building.
- Whether the container placement figure holds on a cold image. It was timed
  with a warm one.
- Whether the memory subtree is worth wiring or worth retiring. Reachability
  says it is dark. It does not say which way to resolve that.

The cheapest useful live run is the labelled against unlabelled state pair at
one horizon, because those two arms differ in presentation alone. It costs
money and should be asked for rather than assumed.

## 12. Where things are

| Path | What it holds |
|---|---|
| `devtools/embodiment_axes/CATALOG.md` | all 30 embodiments with both sides of each |
| `devtools/embodiment_axes/FINDINGS.md` | the measurements and what they mean |
| `devtools/embodiment_axes/choose.py` | situation in, one recommendation per axis out |
| `devtools/embodiment_axes/registry.py` | discover, check, run, regenerate |
| `docs/context/START-HERE.md` | the orientation page |
| `docs/context/INVARIANTS-AND-TRAPS.md` | what breaks if you change it |
| `docs/context/WAYS-OF-RUNNING.md` | every configuration that exists today |
| `docs/verification/CODE-REVIEW-2026-09-07.md` | 31 findings, 29 confirmed by execution |
| `docs/implementation/IMPROVEMENT-PLAN-2026-09-07.md` | what is specified and not yet built |
| `docs/research/NODE-CONTEXT-TRANSPORT-AND-LEDGER-REFERENCES-2026-09-07.md` | the long form of section 7 |
| `src/loop_engine/reachability_report.py` | which modules a live path can actually call |

## 13. If you only do one thing

Wire the memory subtree into the solve path the way learned memory was wired,
and add each module to `REQUIRED_REACHABLE` as it lands so it cannot go dark
again. That is 18 modules of built capability currently reachable by nothing,
and the measurement that proves it is one function call.
