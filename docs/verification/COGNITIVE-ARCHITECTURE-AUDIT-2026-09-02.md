# Cognitive architecture audit, 2026-09-02

Written against the supplemental steering prompt's required output. It reports
what the live repository has, what two live runs on the same competition
showed, what was implemented in response, and what remains hypothesis.

The short version: the recent failure was **not** caused by a cycle that was
too short. It was caused by an operator that did not exist and a runtime with
no way to say so. Adding steps would have produced more passes of the same
correct conclusion.

## A. What the recent failures actually showed

Two runs, same competition, same three files, same engine, different model.

| | 14:22 run | 15:08 run |
|---|---|---|
| Run id | `adaptive-7b7fd04e0e75bc3785e30abb` | `adaptive-c143ca11dc3e0c5625aa7590` |
| Model | `deepseek-v4-flash:0731` | `gemma-4-coding-abliterated` |
| Outcome | `COMPLETED_VERIFIED` | exit 1, no submission |

### The failing run, by layer

- **Failure layer.** Capability catalog, not reasoning and not the cycle.
- **Failure class.** A required operation had no operator.
- **Observed cause.** The model wrote `src/pipeline.py` with an unterminated
  string literal at line 131. The runtime reported the `SyntaxError` exactly.
  The model concluded at once that it should read the file, find the line and
  fix it, which is correct. `core.source.inspect` refused: "source inspection
  requested unknown paths ['src/pipeline.py']". `core.generated_project`
  refused a `cat`: "generated commands must execute reviewed files, not inline
  code" and "must use the registered Python executable". Neither refusal is
  wrong; one guards the input boundary and the other the execution boundary.
  Between them nothing could observe the run's own output.
- **Contributing cause.** No channel existed for "the operation I need does
  not exist". The run could only repeat.
- **What remains unknown.** Whether the same model would have completed the
  task with the read-back operator available. It was never given one.
- **Recovery attempted.** The ladder ran correctly: every refusal was recorded
  on the action fence with its exact cause, `core.generated_project` was
  fenced after five failures, the model identified the right workaround by
  pass 11, soft reset fired at pass 16 and cold restart at pass 19.
- **Result.** Twenty passes carrying the same sentence, then exit 1.
- **Architectural implication.** The recovery ladder cannot recover from a
  missing operator, and the record could not distinguish "this model reasons
  badly" from "this catalog has a hole". That distinction is the one a system
  intending to improve most needs, and nothing was recording it.

### A second finding, from the packet rather than the run

Measured on real rendered packets: **7,423 of 39,075 bytes were byte-identical
repeats**, 19.0% of every model call on every step. Thirteen canonical blocks
were mapped onto ten packet fields, so `[PERSONA]` and `[PERSPECTIVES]`
carried the same 5,120 bytes, and the directive appeared three times. This is
the §1.4 hypothesis confirmed by measurement rather than argument.

## B. Current cycle architecture

Counted from the live sources, not from documentation.

| | count | where it lives |
|---|---|---|
| Kernel nodes | 13 (6 required, 7 optional) | `loop.kernel.KERNEL_NODES` |
| Action kinds | 24 | `NEXT_ACTION_KINDS` |
| Capabilities | 8 | `ADAPTIVE_CAPABILITIES` |
| Routes | 9 | `MODEL_ROUTE_VALUES` |
| Question step sets | 16 | practitioner portfolio |
| Perspectives | 43 | practitioner portfolio |
| Guidance records | 30 | practitioner portfolio |

- **Fixed cycles.** One. `_calculate_kernel_pass` runs the 13 nodes in a fixed
  acyclic order; six are required and seven may be skipped per pass through
  `state.facts["_skip_nodes"]`.
- **Configurable profiles.** None existed before this increment.
- **Transitions.** Nine routes. The full algebra a Loop network would need is
  28; see §C.
- **State objects.** Orientations, action decisions, verification records,
  failures, recovery directives, and a `FrontierSnapshot` — but the frontier
  is a **read-only projection rebuilt from the finished result**, not a living
  structure the model updates during the run.
- **Logical steps versus physical calls.** Not separated. One model-calling
  node is one physical call; the seven optional nodes make no model calls at
  all, which matters for §E.
- **Context path.** `assemble_work_packet` renders 13 blocks per call, with a
  context pack manifest and measured budgets.
- **Recovery path.** Typed rejections, an action fence keyed on capability
  plus canonical arguments, a diagnose/propose/adjudicate panel, then soft
  reset, reframe, cold restart.
- **Learning path.** Run History, region statistics, and as of today an
  option-selection tally per run.

## C. Proposed cognitive grammar, and what was implemented

`core.cognitive_grammar` was added. It names, and never gates.

- **Operator catalog — implemented.** 45 operators, *derived on call* from the
  kernel nodes, action kinds and capabilities. It is not a second list,
  because a second list drifts and the drift is silent. This is the same rule
  that `_CORE_STEP_IDS` now follows after it was found restating the kernel's
  node list by hand.
- **Cycle profiles — implemented as vocabulary, not as a default.** Five named
  versioned profiles (`full`, `compact_action`, `experiment`, `repair`,
  `orientation`), each a skip set over optional nodes only. A profile naming a
  required node is refused by name. Only `full` is in use; see §E for why the
  rest are not yet worth adopting.
- **Transition algebra — mapped, mostly not realized.** All 28 transitions are
  named with their state. **18 are realized** and each names its mechanism.
  **13 are not**, each with the reason: `GOTO` and `REVISIT` (a pass is
  acyclic), `BACKTRACK` and `ROLLBACK` (no named checkpoint the model may
  choose, no compensating transition), `RESUME` (history replays a finished
  run, it does not resume a stopped one), `RECONTEXTUALIZE` (a model cannot
  ask for recompilation and retry the same operator), `DEESCALATE`,
  `TOURNAMENT`, `VOTE`, `ENSEMBLE`, `RETURN_INCUMBENT`, `TERMINATE_BRANCH`,
  `REPLAN`. Naming a transition realizes nothing, and the map says so.
- **Operator gap channel — implemented.** A caller may report `operator_gap`
  with what it `needed`, what it `tried`, and what the runtime `said`. It is
  admitted, marked with whether it names an operator that already exists (a
  caller that missed a present operator is a finding about the prompt, not the
  catalog), counted apart from a missing portfolio option, and carried into
  saved history. This is precisely the record the failing run could not make.
- **Situation snapshot, living frontier, graph mutation proposal — not
  implemented.** Hypothesis only. The existing frontier projection is not a
  substitute and should not be described as one.

## D. Experiment performed

One ablation from §21.3: fixed cycle versus shorter profiles. Task, fixture
model, answers and packet content held constant; only the skip set varied.

| profile | nodes/pass | model calls | mean packet bytes |
|---|---|---|---|
| full | 13 | 4 | 51,354 |
| experiment | 11 | 4 | 51,392 |
| orientation | 10 | 4 | 51,402 |
| repair | 10 | 4 | 51,412 |
| compact_action | 9 | 4 | 51,424 |

Limitations, stated because they bound the conclusion: this is a fixture model
on a small task; every arm ends `NOT_YET_PROVEN`, so the experiment measures
cost and structure, not quality; and a single task cannot separate profiles
that would differ on harder work.

## E. What the comparison showed

**Removing four of thirteen nodes changed model calls not at all and packet
bytes by 0.1%.** The profile lever is close to inert in the current runtime,
and the reason is structural: all seven optional nodes are served by
deterministic defaults that make no model calls. Cost lives entirely in the
six model-calling nodes and in what each packet carries.

This is worth stating plainly because it contradicts the intuition the
steering prompt warns about. Adding or removing named steps is not where the
cost is. The 19% duplication finding and its removal changed every call on
every step; the profile change altered nothing measurable. Profiles remain
worth having as safe named vocabulary, and they are not a cost lever today.

## F. Simplest successful proof

The end-to-end path is proven by the 14:22 run, in `LIVE-KAGGLE-DIAGNOSTIC-
2026-09-02.md`: task, orientation naming all three files from their profiles
alone, bounded action, observation, verification failing on an independently
unconfirmable read-only guarantee, a design change adding a pre-run input
snapshot so verification could prove it, re-execution, `COMPLETED_VERIFIED`,
and a submission of 286,571 rows with 286,571 distinct values.

The grammar increment itself is proven at the unit level: 11 self-tests over
the catalog, the profiles, the transition map and the gap channel, plus one
guard that a missing operator is recorded apart from a missing option.

## G. Honest remaining limitations

**Proven.** The operator catalog derives from live sources and cannot drift.
Profiles cannot skip required nodes. The gap channel admits, separates and
persists a reported missing operator. The 19% packet duplication is removed
and cannot return. `core.workspace.read` closes the specific hole the failing
run hit, verified against a reproduction of that exact file.

**Partially proven.** Cycle profiles are safe and inert; whether any of them
helps on a harder task is untested. Option selection is recorded and
aggregated, but no run has yet accumulated enough reports for
`option_evidence()` to say anything — it reports fewer than three reporting
runs as thin evidence, and every region is currently below that.

**Implemented but untested live.** The gap channel has never been exercised by
a real model. Nothing yet asks a model to report a gap in prompt text beyond
the output-contract entry, so a live run may simply not use it.

**Failed.** The 15:08 run. Its cause is closed; whether that model can now
finish the task is unknown.

**Still conceptual.** Situation snapshots as a live state plane, a living
question and work frontier, graph mutation proposals, multi-solution
portfolios with tournaments and ensembles, and 13 of the 28 transitions.

**AGI-scale claims that remain unproven.** Every one in §23.12. Nothing here
tests distribution, addressing at scale, backpressure, permission attenuation
across spawned Loops, or protocol evolution. The repository runs one process.

**Next smallest experiment with the highest information value.** Ask a live
model, on the 15:08 task with `core.workspace.read` available, to solve it
again. That single run tests the closed gap, exercises the gap channel on a
real model, and produces the first option-selection tally from live work —
three unknowns for one run.
