# Twenty-two embodiments on five axes: what the measurements say

Date: 2026-09-08. Every number below came from running the code in this
folder. No model was called; the reason is in the method section, and the live
runs that would answer the remaining questions are listed at the end.

## What this folder is

Five questions about how to build this system. Each one has a folder, each
folder holds every answer worth considering, and each answer states what it
gives you and what it costs you next to each other.

| Family | The question it answers | Answers |
|---|---|---:|
| context-transport | If a step runs somewhere else, how does information reach it? | 8 |
| execution-placement | Where does a step physically run? | 3 |
| verification | How does an answer get accepted? | 3 |
| memory | What does an earlier run contribute to a later one? | 4 |
| control-flow | Who picks the next unit of work, and how much per call? | 4 |

The claim that makes this a catalogue rather than a list: **these are
independent axes.** A design is one choice from each, and the choices compose.
Bounded state, in a container, verified by recomputation, remembering through
a governed journal, driven by an adaptive batch, is a sentence you can now say
and price. Nothing here forces a bundle.

## Method, and why it is shaped this way

**A task one call cannot finish.** Every earlier measurement in this project
stalled the same way: the tasks were small enough that a single call solved
them, so the architecture under test never mattered. Here the facts live
behind a read tool, a unit is invisible until it is read, the answer needs
every unit, and the number of units is a dial.

**Intelligence held constant.** The thing that reads a prompt is one pure
function that plays perfectly on whatever the prompt contains. It has no
memory between calls and never touches the world. So an arm that carries what
the step needs succeeds, and an arm that loses it fails or pays to recover it.
The comparison measures structure, and only structure.

**Independence where it is the thing under test.** The transport family varies
the loop, so each of its arms has its own loop, its own state handling and its
own rendering. The other three families vary something else, so they share one
loop on purpose: changing two things at once would confound them.

**One window for everyone.** A prompt over 16,000 bytes is refused with a
typed error rather than truncated, because a silent truncation would hide the
wall the experiment exists to find.

## Context transport

Peak prompt bytes, seed 11, 16,000-byte window.

| units | monolith | full_history | state_patch | horizon_state | pull_reference | bounded_state | summarised | hybrid |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 4 | 1,023 | 1,084 | 950 | 1,012 | 1,059 | 949 | 1,308 | 922 |
| 16 | 2,403 | 2,464 | 1,060 | 1,122 | 1,169 | 965 | 1,454 | 938 |
| 64 | 8,013 | 8,074 | 1,451 | 1,514 | 1,560 | 972 | 1,468 | 945 |
| 256 | failed | failed | 2,993 | 3,057 | 3,102 | 979 | 1,474 | 951 |
| 1024 | failed | failed | 10,165 | 10,229 | 10,275 | 986 | 1,487 | 957 |

**Constant context is a property of the schema, not of the architecture.**
This is still the finding worth acting on. The state arm was written to carry
a constant amount per step and does not: two of its fields are lists with one
entry per unit, so its prompt reaches ten kilobytes at 1,024 units. The
bounded arm carries the same information as five scalars, a mapping over a
closed vocabulary and a cursor, and moves 37 bytes across a 256-fold increase
in horizon. Same answers, one tenth the bytes.

So "we carry a compact state" cannot be checked by reading the description.
The thing to measure is whether any field is proportional to the horizon.

**The de-duplication list only has to name what is in the prompt.** The
summarised arm generalises that lesson. It keeps raw recent observations and
folds the rest into a summary, and its list of what has already been folded
covers only the entries still present, because an entry that is not in the
prompt cannot be folded twice. That keeps a transcript design flat: 1,308
bytes at four units and 1,487 at 1,024, with the budget rather than the
horizon setting the peak.

**Two arms have a wall and it is easy to predict.** The monolith grows about
117 bytes per unit, so its wall is roughly the window divided by 117: about
136 units at 16,000 bytes. The transcript arm grows at the same rate and
breaks in the same place, later in the run. Neither is a bad design. Both have
a horizon they cannot pass, and it is computable in advance.

**Labelling by horizon costs 60 to 65 bytes per prompt and cannot be shown to
buy anything here.** Against a perfect reader the horizon arm's correctness is
identical to the state arm's by construction, so this experiment prices the
labels and cannot value them. Only a live run answers it.

**Pull costs twice the calls and buys nothing at this task shape.** The pull
arm needed 2,050 calls where the push arms needed 1,025, and sent more bytes,
not fewer. A seed plus a served payload is larger than the payload alone. The
general rule: pulling wins only when a step needs a small fraction of what a
push would send. Here that fraction is one.

**The hybrid arm makes that a dial rather than a doctrine.** It pushes the
state while it fits a byte budget and fetches by name when it does not. Above
the state size it is a push arm, below it a pull arm, and it is the cheapest
arm at every horizon measured, by 28 bytes at 1,024 units, because it carries
no remaining count at all.

## Control flow, and the finding that changes the transport conclusion

At 1,024 units, all four arms correct:

| Arm | Calls | Total prompt bytes | Peak prompt |
|---|---:|---:|---:|
| one_at_a_time | 1,025 | 981,450 | 967 |
| model_chosen_next | 1,025 | 5,668,863 | 10,085 |
| fixed_batch, K=8 | 128 | 224,585 | 1,771 |
| adaptive_batch | 22 | 138,096 | 8,380 |

**Batching wins on both axes at once, which the transport family could not
see.** The transport comparison held one unit per call fixed, and concluded
that the cheapest design sends about 986 bytes per call. But 1,025 calls of
986 bytes is 680 kilobytes of task text and state re-sent for its own sake.
Folding 64 units per call pays that overhead 22 times instead of 1,025, and
the total falls seven-fold *and* the call count falls forty-seven-fold. There
is no trade between them at this scale; the trade is against peak prompt,
which rises to 8,380 bytes.

So the honest summary of both families together is: get the schema bounded
first, then batch as hard as the window allows. Either one alone leaves most
of the saving on the table.

**Adaptation removes the knob and the wall together.** The adaptive arm
doubles its batch while the last prompt used less than a target share of the
window, and halves it on a refusal, retrying the same units. It never has to
be told the window size, and a refusal is recoverable rather than fatal, which
no other arm here can say. At a half-window target it never overshot at all;
pushed to a 0.99 target it absorbed five refusals and still finished correctly.

**Letting the reply choose the next unit costs the same list twice over.** The
model-chosen arm sends the remaining units and its peak reaches 10,085 bytes
at 1,024 units, against 967 for a cursor. It is the same horizon-proportional
field the transport family found dominating the state arm, arriving through a
different door.

## Execution placement

Same loop, same transport, 13 calls each.

| Placement | Per call | What it contains |
|---|---:|---|
| in process | 0.10 ms | nothing |
| a fresh interpreter per step | 194 ms | process memory only; same filesystem, network and user |
| a container per step | 1,398 ms | no network, read-only mount, all capabilities dropped, memory and process limits |

Containment costs about 14,000 times a function call, per step. That is the
number, and it means placement is a per-step decision rather than a per-system
one: a run that takes one untrusted action and a hundred trusted ones should
not pay containment a hundred and one times.

The container arm refuses when no runtime is present rather than falling back.
A placement that downgrades in silence is worse than one that refuses, because
the containment claim stays in the documentation after it stops being true.

## Verification

Five injected faults and one clean control, identical for every arm.

| Policy | Caught | Extra reads | Rejected the clean run |
|---|---:|---:|---|
| self report | 0 of 5 | 0 | no |
| engine gate | 4 of 5 | 0 | no |
| independent recompute | 5 of 5 | 96 | no |

**The structural gate is much stronger than expected, and still has exactly
one blind spot.** It caught four faults for no extra reads, including two that
looked like they would need recomputation. The check that earned its place is
the cheapest one and the one most often skipped: does the answer agree with
the state the same run carried? An answer contradicting its own run is wrong
whatever it says.

What it cannot catch is a fault that agrees with itself at every level a rule
can check. When the total moved, the account breakdown absorbed the difference
and the count stayed consistent, every gate passed. That case needs a second
derivation, and a second derivation cost a full extra pass over the world.

This also corrected the experiment. The first arithmetic fault was written to
be the hard case and turned out to be the easy one, because it left the answer
disagreeing with its own breakdown. Both faults are kept: the weak one shows
what a gate catches, the strong one shows what only recomputation catches.

## Memory

Sixteen units, one cold run then a second run, plus a resume scenario and an
outsider staging a wrong answer.

| Design | Cold calls | Repeat calls | Resumes | Served the poison | Answered wrongly |
|---|---:|---:|---|---|---|
| none | 17 | 17 | no | no | no |
| checkpoint and resume | 17 | 1 | yes | no | no |
| cross-run cache | 17 | 0 | yes | **yes** | **yes** |
| governed journal | 17 | 0 | yes | no | no |

**The cache buys one call out of seventeen and pays for it with everything.**
That is the result worth carrying out of this folder. A checkpoint store keeps
positions and never keeps conclusions, so the worst a corrupted one can do is
start the arithmetic from a wrong subtotal, which recomputation catches. It
reached one call on a repeat because the position was already at the end and
the answer was re-derived rather than served. The cache reached zero by
serving a stored conclusion, and when an outsider stored one, the run returned
it as its own answer.

**The governed journal gets the cache's saving without the cache's exposure.**
A record enters as a candidate carrying who produced it, an independent
reviewer re-derives it, and only a promoted record is ever served. With no
reviewer configured it serves nothing at all, which is the correct default for
a design whose rule is that nothing promotes itself.

## Three defects the measurements found in this folder

Worth listing, because each was invisible to reading the code that contained
it.

**A checkpoint that dropped its position.** The resume store kept the running
subtotal and not the cursor it was a subtotal of. A resumed run then re-read
what the subtotal already contained and double counted it, and answered
confidently. The two now travel together in one signature, and there is a
check that resuming with the subtotal alone produces a wrong answer, so the
defect cannot be rewritten by accident.

**Compaction that dropped an observation before anything read it.** The
summarised arm discarded oldest-first by age. With a tail budget smaller than
one observation it discarded the observation that had just arrived. Dropping
is now conditional on the entry already being folded, and the budget is
advisory against that.

**A fault written to be hard that was easy.** Described above under
verification.

An earlier round of this work found a fourth: identifiers three digits wide
meant `s1000` matched the pattern written for `s100` at 1,024 units, and 3,000
of 4,000 reads were repeats. Identifier width now scales with the population.

## What this does not establish

The reader is perfect, so nothing here says whether a real model reasons well
with any of these structures. That is the largest open question and it is
deliberately out of scope for a run that costs nothing.

One task shape, one world generator, one window size. The task is
accumulate-over-everything, which is the shape most favourable to a compact
state and least favourable to pull. Bytes were counted, not provider tokens.
Placement was timed on one machine with a warm image.

The arms are correct implementations of their ideas, not tuned versions. A
better pull arm would cache what it pulled. That is another arm, not a
correction to this one.

## How to run it

```bash
python3 registry.py list                          # every embodiment
python3 registry.py check                         # manifests, imports, self-checks
python3 registry.py run                           # all five families
python3 registry.py run --family memory           # one family
python3 registry.py run --horizons 1024 --out deep.json
python3 registry.py catalog                       # regenerate CATALOG.md
```

`run_comparison.py` still works with its original flags and record type.

## What a live run would answer

Three questions, in the order they are worth paying for.

1. Does a real model keep a bounded state correctly over a long horizon, or
   corrupt the accumulator in a way a perfect reader never would? Run the
   bounded arm at a few horizons against the oracle.
2. Do horizon labels change answer quality at equal information? The state and
   horizon arms differ in presentation alone, so it is a clean test.
3. Does a model offered a fetch mechanism ask for what it needs, or ask for
   everything? The ledger log answers this directly, and the answer decides
   whether a pull design is worth building at all.

A useful first spend is question 2 at one horizon: it is the cheapest, and the
two arms are otherwise identical.

Those runs are cloud-proxied on this machine and therefore cost money, so they
should be asked for rather than assumed.
