# Catalogue of embodiments

Every folder here is one way of building this system. They are not
drafts of each other and none is deprecated. Each one is a design
someone could reasonably choose, with what it gives you and what it
costs you stated next to each other, and measured where a
measurement is possible.

The organising claim is that these are independent axes. A design is
one choice from each family, and the choices compose: bounded state,
in a container, verified by recomputation, remembering through a
governed journal, driven by an adaptive batch. Nothing here forces a
bundle.

```bash
python3 registry.py list                  # everything, by family
python3 registry.py check                 # manifests, imports, self-checks
python3 registry.py run                   # every family through its harness
python3 registry.py run --family memory   # one family
python3 registry.py catalog               # regenerate this file
```

30 embodiments across 7 families.

## context-transport

**If a step runs somewhere else, how does the information it needs get there?**

Varies: what travels from one step to the next.  
Held constant: the world, the task, the reader of the prompt, the context window, and the grader.  
Decides: whether an embodiment has a horizon it cannot pass, and where that horizon is.  
Read first: the peak prompt column; an arm whose peak grows with the horizon has a wall, and the wall is computable before you hit it.

| # | Embodiment | In one line | Status |
|---|---|---|---|
| 01 | [`monolith`](context-transport/01-monolith/README.md) | Put the whole world in one prompt and take one answer. | measured |
| 02 | [`full_history`](context-transport/02-full-history/README.md) | Resend the entire transcript on every step. | measured |
| 03 | [`state_patch`](context-transport/03-state-patch/README.md) | Send the procedure, one closed state record, and the latest observation. | measured |
| 04 | [`horizon_state`](context-transport/04-horizon-state/README.md) | The same state fields, labelled long, medium and short horizon. | measured |
| 05 | [`pull_reference`](context-transport/05-pull-reference/README.md) | Send an identifier and a list of keys; the node fetches what it needs. | measured |
| 06 | [`bounded_state`](context-transport/06-bounded-state/README.md) | A state schema with no field proportional to the horizon. | measured |
| 07 | [`summarised_history`](context-transport/07-summarised-history/README.md) | Keep the transcript, but compact the oldest part once it crosses a threshold. | measured |
| 08 | [`hybrid_push_pull`](context-transport/08-hybrid-push-pull/README.md) | Push the bounded state every step, pull only what is missing. | measured |

### monolith

*Put the whole world in one prompt and take one answer.*

**Gives you**

- One call. No state, no protocol, no partial failure to reason about.
- Cheapest per unit of work below its horizon: 1,023 bytes at 4 shards, the second lowest of the eight arms.
- Nothing can be lost between steps because there are no steps.

**Costs you**

- Prompt grows about 117 bytes per shard, so a 16,000-byte window puts the wall near 136 shards. Measured: fine at 128, refused at 256.
- No intermediate result survives a failure. The run is all or nothing.
- Cannot use a tool result to decide what to read next.

**Pick it when** The whole input provably fits the window with room to spare.; The task is one shot and latency matters more than anything else.; You want a baseline the other arms have to beat.

**Avoid it when** Input size is unbounded or set by a user.; You need progress to survive a crash.

### full_history

*Resend the entire transcript on every step.*

**Gives you**

- Nothing is ever summarised, so nothing can be lost by summarising.
- The transcript is the audit log. What the model saw is exactly what you can read back.
- Simplest correct multi-step design; no schema to get wrong.

**Costs you**

- Same growth rate as the monolith and the same wall, just reached later in the run. Refused at step 123 of 256 shards.
- Total bytes are the worst of any arm that gets close: 749,460 at 1,024 shards while failing.
- Re-reads the same facts every step, so cost is quadratic in steps.

**Pick it when** Runs are short and bounded, under a few dozen steps.; Full replayability of model input matters more than cost.; You are debugging and want to see everything the model saw.

**Avoid it when** Step count is set by input size.; You are paying per token.

### state_patch

*Send the procedure, one closed state record, and the latest observation.*

**Gives you**

- Solves every horizon tried, up to 1,024 shards.
- The closed schema means a reply cannot widen what travels forward.
- History is not resent, so the per-step cost does not depend on how many steps came before.

**Costs you**

- Its state is not actually constant. Two fields are lists with one entry per shard, so the prompt goes from 950 bytes at 4 shards to 10,165 at 1,024. Ten times larger than the arm that fixed this.
- The word 'compact' in the design description was not true and reading the description would never have revealed it.
- One call per shard: 1,025 calls at 1,024 shards.

**Pick it when** You want the standard SKILL.state shape and horizons are moderate.; You need refusal of out-of-schema fields more than minimum bytes.

**Avoid it when** The horizon is large. Audit the schema first, then use bounded_state.

### horizon_state

*The same state fields, labelled long, medium and short horizon.*

**Gives you**

- Costs 60 to 65 bytes more per prompt than state_patch at every horizon tried, so the price of the labels is known and small.
- The three blocks give a human reader a place to look.
- Differs from state_patch in presentation only, so a live run prices the labels against nothing else.

**Costs you**

- Against a perfect reader its correctness is identical by construction, so this harness can price the labels and cannot value them.
- Inherits the horizon-proportional fields from state_patch, and the same 10 kilobyte prompt at 1,024 shards.

**Pick it when** A person reads the prompts and needs the structure.; You are running the live A/B against state_patch.

**Avoid it when** Bytes are the binding constraint and no one reads the prompts.

### pull_reference

*Send an identifier and a list of keys; the node fetches what it needs.*

**Gives you**

- The prompt seed is O(1) regardless of how large the stored context is.
- The pull log is a direct record of what the node believed it needed, which no push design produces.
- Access can be checked per key at serve time.

**Costs you**

- Two calls per step where a push arm needs one: 2,050 against 1,025 at 1,024 shards.
- Sends more total bytes, not fewer: 10,880,374 against 10,409,501. A seed plus a served payload is bigger than the payload alone.
- At 256 shards with a 400-step ceiling it ran out of steps and failed where the push arms solved.

**Pick it when** Each step needs a small and different slice of a large body.; You need per-key authorisation or an audit of what was requested.

**Avoid it when** Every step needs essentially the whole accumulator, as here. Then the fraction pulled is one and pull is strictly worse.

### bounded_state

*A state schema with no field proportional to the horizon.*

**Gives you**

- Peak prompt moves from 949 bytes at 4 shards to 986 at 1,024. That is 37 bytes across a 256-fold increase in horizon.
- One tenth the total bytes of state_patch at 1,024 shards: 1,000,925 against 10,409,501, for identical answers.
- No horizon in reach. Nothing in the record grows with the input.

**Costs you**

- Requires a closed vocabulary. The account mapping is bounded only because the accounts are known in advance.
- The cursor imposes an order, so it cannot express work that jumps around or runs out of order.
- Still one call per shard; it fixes bytes, not call count.

**Pick it when** The horizon is large or unbounded.; You can name a closed schema and prove no field grows with input.

**Avoid it when** You cannot bound the vocabulary. Then measure rather than assume.

### summarised_history

*Keep the transcript, but compact the oldest part once it crosses a threshold.*

**Gives you**

- Removes the transcript arm's wall without asking anyone to design a state schema.
- The recent window stays verbatim, which is where a reader usually looks.
- One knob. The threshold trades fidelity against bytes directly.

**Costs you**

- Summarising is where facts get silently dropped. Here the fold is arithmetic and lossless; with a model writing the summary it is not.
- Peak is set by the threshold, not by the task, so it wastes bytes at small horizons and only saves at large ones.
- Two representations of the same history exist at once.

**Pick it when** You have an existing transcript loop hitting a wall and cannot restructure it into a state schema.; The task genuinely needs recent raw detail.

**Avoid it when** The summary would be model-written and correctness is required. Measure what the fold loses before trusting it.

### hybrid_push_pull

*Push the bounded state every step, pull only what is missing.*

**Gives you**

- Keeps the bounded arm's flat prompt and adds the pull escape hatch.
- Measured slightly cheaper than the bounded arm at every horizon, 951 bytes against 979 at 256 shards, because it carries no remaining count.
- Pays the second call only on steps that use it, unlike pure pull which pays it always.
- The budget is a single dial between the two designs: above the state size it is a push arm, below it a pull arm, and the same code is both.

**Costs you**

- Two mechanisms to maintain and two ways for the same fact to arrive.
- On this task nothing is ever missing, so the pull path costs nothing and buys nothing. It needs a task with rare deep lookups to earn out.
- A node can pull what it was already pushed, so the ledger has to detect that or the design quietly degrades to pure pull.

**Pick it when** Most steps need the same small state and a few need something rare and large.; You want an audit trail of exceptional access without paying for it on every step.

**Avoid it when** Every step needs the same thing. Then push alone is simpler and cheaper.

## control-flow

**How does the loop decide what to do next, and how much per call?**

Varies: who picks the next unit of work and how many units one call carries.  
Held constant: the world, the reader, the window and the state schema.  
Decides: the call-count against prompt-size curve, and whether an arm can recover from a window refusal.  
Read first: calls against peak bytes; they trade directly and the adaptive arm finds the knee without being told the window.

| # | Embodiment | In one line | Status |
|---|---|---|---|
| 01 | [`one_at_a_time`](control-flow/01-one-at-a-time/README.md) | One unit of work per call, in an order code decides. | measured |
| 02 | [`model_chosen_next`](control-flow/02-model-chosen-next/README.md) | The reply picks the next unit from a list of what is left. | measured |
| 03 | [`fixed_batch`](control-flow/03-fixed-batch/README.md) | Fold a fixed number of units per call. | measured |
| 04 | [`adaptive_batch`](control-flow/04-adaptive-batch/README.md) | Grow the batch until the window pushes back, then hold. | measured |

### one_at_a_time

*One unit of work per call, in an order code decides.*

**Gives you**

- Smallest possible prompt per call.
- The order costs nothing to communicate, because it is never sent.
- A failure loses one unit of work.

**Costs you**

- Call count equals the horizon. This is the dominant cost at scale.
- The order is fixed, so it cannot react to what a unit contained.
- Per-call overhead is paid the maximum number of times.

**Pick it when** Per-call cost is low and prompt size is the constraint.; Units are independent and order does not matter.

**Avoid it when** Calls are the expensive thing. Batch instead.

### model_chosen_next

*The reply picks the next unit from a list of what is left.*

**Gives you**

- Order can react to what was just seen, which a cursor cannot.
- Natural fit when units are not interchangeable.
- The chosen order is itself a record of what the run thought mattered.

**Costs you**

- The remaining list has one entry per unit, so the prompt is proportional to the horizon and the arm inherits a wall.
- Nothing stops a repeat request, so the loop needs its own guard.
- Pays for flexibility on every call, including the calls that would have taken the cursor's answer anyway.

**Pick it when** Order genuinely depends on content.; The horizon is small enough that the list is cheap.

**Avoid it when** Units are interchangeable. Then this is a cursor with a bill attached.

### fixed_batch

*Fold a fixed number of units per call.*

**Gives you**

- Calls fall by a factor of K, which is the whole point.
- One knob, and its effect is exactly what you would predict.
- No extra mechanism over the cursor arm.

**Costs you**

- Somebody has to choose K, and the right K depends on the window, the observation size and the state size.
- A K that is too large is a refused prompt and a failed run, not a slow one.
- A K that is too small leaves most of the saving on the table.

**Pick it when** You know the window and the unit size and they are stable.

**Avoid it when** Unit sizes vary, or the window is not yours to know. Use the adaptive arm.

### adaptive_batch

*Grow the batch until the window pushes back, then hold.*

**Gives you**

- Collapsed 256 units into 10 calls with no knob set by anyone.
- A window refusal is recoverable rather than fatal. It is the only arm here with that property.
- At a half-window target it never overshot at all, so a careful target buys a run with zero refusals.
- Adapts to a window it was not told about, which is what makes it portable across models.

**Costs you**

- Peak prompt is deliberately near the target share, so it uses most of the window by design.
- A greedy target trades refusals for speed: at 0.99 it absorbed five refusals on a run that had none at 0.5.
- More moving parts than a fixed K, and the batch history is another thing to record and read.

**Pick it when** The window, the model or the unit size can change.; You want the call saving without owning the tuning.

**Avoid it when** You need a fixed, auditable prompt size per call.

## decomposition

**How is the work divided before any of it is done?**

Varies: what gets split, and what has to be put back together.  
Held constant: the world, the reader, the window and the state schema.  
Decides: what splitting costs in total calls and what it buys in serial depth, which move in opposite directions.  
Read first: calls and longest_chain_calls together; reading either one alone tells you whatever you already believed.

| # | Embodiment | In one line | Status |
|---|---|---|---|
| 01 | [`single_pass`](decomposition/01-single-pass/README.md) | Do not decompose. One pass over everything. | measured |
| 02 | [`fixed_split`](decomposition/02-fixed-split/README.md) | Cut the work into a fixed number of independent groups. | measured |
| 03 | [`recursive_split`](decomposition/03-recursive-split/README.md) | Keep halving until a piece is small enough, then merge back up. | measured |
| 04 | [`portfolio`](decomposition/04-portfolio/README.md) | Split by approach, not by work: run several, publish the first that verifies. | measured |

### single_pass

*Do not decompose. One pass over everything.*

**Gives you**

- Fewest total calls of any arm here, because nothing pays a per-group final call.
- No merge, so no chance of a merge being wrong.
- Nothing to size, nothing to tune, nothing to schedule.

**Costs you**

- Serial depth equals the work. Nothing can run at the same time as anything else.
- One failure is the whole run's failure; there are no independent domains.
- Cannot use more than one worker even when they are free.

**Pick it when** Work is small, or strictly ordered, or you have one worker.; You want the cheapest total and do not care about latency.

**Avoid it when** Latency matters and workers are available.

### fixed_split

*Cut the work into a fixed number of independent groups.*

**Gives you**

- Serial depth falls by roughly the group count, which is what wall time follows when groups run at once.
- Groups are independent, so one failing costs that group and not the run.
- The group count is a direct handle on how many workers get used.
- Contiguous slices keep a group's identifiers adjacent, so a ledger reader can tell which slice a call belonged to.

**Costs you**

- More total calls, not fewer: every group pays its own final call.
- The right group count depends on the machine, not on the work, so it has to be set by someone who knows the machine.
- Needs a merge that is associative and gets the task's tie-breaks right, which is a real piece of code that can be wrong.
- This folder shipped a slicer that returned six groups when seven were asked for, which would have silently mis-sized a worker pool.

**Pick it when** Units are independent and workers are available.; You know how many workers you have.

**Avoid it when** Units depend on each other, or the merge cannot be made associative.

### recursive_split

*Keep halving until a piece is small enough, then merge back up.*

**Gives you**

- The threshold is about the work, not about the machine, so the same setting travels between deployments.
- The tree shape follows the input size without anyone choosing a group count.
- A depth guard bounds the tree even at a threshold that asks for an unbounded one.

**Costs you**

- Combines pairwise up the tree, so the merge must be associative and not merely correct once at the end.
- Deeper than a flat split for the same number of leaves, and depth is coordination.
- Same per-leaf call overhead as the fixed split, plus a tree to reason about.

**Pick it when** Input size varies a lot between runs.; You want one threshold that means the same thing everywhere.

**Avoid it when** The merge is not associative. Then the tree is unsafe in a way a flat split is not.

### portfolio

*Split by approach, not by work: run several, publish the first that verifies.*

**Gives you**

- The only arm in the catalogue that survives one of its designs being wrong for the input. At 256 units two candidates hit their horizon and it still answered correctly.
- Refuses when no candidate verifies, rather than publishing the least bad one.
- Stops as soon as one is accepted, so the cheap candidate costs nothing extra when it works.
- Builds nothing of its own: the candidates and the checker are other folders in this catalogue, loaded as they are. It is the composability claim actually executing.

**Costs you**

- Pays for every candidate it runs before one verifies, and it cannot know in advance which that is.
- Needs a verifier good enough to tell the candidates apart. With a weak checker it publishes the first plausible answer rather than the first correct one.
- A portfolio of similar designs buys nothing but cost; the candidates have to fail differently to be worth running.
- Ordering the candidates is a real decision, because it decides what the common case costs.

**Pick it when** No single design covers the whole input range you see.; You have an independent checker and being wrong is expensive.

**Avoid it when** One design covers the range, or you cannot verify a result independently.

## execution-placement

**Where does a step physically run?**

Varies: the boundary a step body is executed behind.  
Held constant: the loop, the transport, the reader and the task; every arm runs the same bounded-state loop.  
Decides: what containment costs per step, in wall time, so the price is a number rather than an argument.  
Read first: seconds_per_call; the isolation column is what you are buying with it.

| # | Embodiment | In one line | Status |
|---|---|---|---|
| 01 | [`in_process`](execution-placement/01-in-process/README.md) | The step runs inside the calling process. | measured |
| 02 | [`subprocess_per_step`](execution-placement/02-subprocess-per-step/README.md) | Each step runs in a fresh interpreter, talking over pipes. | measured |
| 03 | [`container_per_step`](execution-placement/03-container-per-step/README.md) | Each step runs in a container with no network and no writes. | measured |

### in_process

*The step runs inside the calling process.*

**Gives you**

- Nothing to pay. The fastest possible placement.
- Simplest to debug: one stack, one process, one log.
- No serialisation, so a step can be handed any Python object.

**Costs you**

- No containment at all. A step that exits, exhausts memory or writes a file takes the host with it.
- A step can reach anything the host process can reach, including credentials in the environment.
- Hidden shared state makes a broken transport look like it works.

**Pick it when** The step body is your own trusted code.; You are measuring something else and want no noise.

**Avoid it when** The step body is generated, or comes from a model, or touches anything you would not run as yourself.

### subprocess_per_step

*Each step runs in a fresh interpreter, talking over pipes.*

**Gives you**

- A step cannot accumulate hidden state, so a transport defect shows up instead of being masked by shared memory.
- A crashing step is a non-zero exit code, not a dead run.
- Costs milliseconds, not the hundreds a container costs.

**Costs you**

- Same filesystem, same network, same user. This is a memory boundary and nothing more.
- Everything crossing it has to serialise.
- Spawn cost is paid on every step, so it multiplies by the horizon.

**Pick it when** You want the transport boundary to be real without paying for containment.; Steps are long enough that spawn cost disappears.

**Avoid it when** The step body is untrusted. This stops nothing it does to the filesystem or the network.

### container_per_step

*Each step runs in a container with no network and no writes.*

**Gives you**

- The only arm here that contains a hostile step: no network, no host filesystem, no capabilities, bounded memory and processes.
- Leaves nothing behind, so one step cannot set a trap for the next.
- Refuses when no runtime is present rather than falling back to a weaker placement, so the containment claim stays true.

**Costs you**

- Container start dominates everything else, by two to three orders of magnitude over a function call.
- Needs a runtime and an image, which is operational weight.
- Image pinning is a real obligation; a tag is not a pin.

**Pick it when** The step body is generated or untrusted.; A step may run commands, and you need it to fail closed.

**Avoid it when** Steps are short and numerous, and the body is your own code. Then the start cost is the whole run.

## failure-handling

**What does the loop do when a step fails?**

Varies: the recovery policy, and what it spends before giving up.  
Held constant: the loop, the transport, the world, and the five failure shapes every arm is shown.  
Decides: which failures each policy actually survives, and what a futile recovery costs.  
Read first: permanent_answered_wrongly; a policy that finishes a run it could not complete is the one that needs verification beside it.

| # | Embodiment | In one line | Status |
|---|---|---|---|
| 01 | [`stop_on_first`](failure-handling/01-stop-on-first/README.md) | The first failed step ends the run. | measured |
| 02 | [`retry_same`](failure-handling/02-retry-same/README.md) | Send the same request again, up to a budget. | measured |
| 03 | [`retry_with_escalation`](failure-handling/03-retry-with-escalation/README.md) | Retry plainly first; when that stops helping, change the request. | measured |
| 04 | [`skip_and_continue`](failure-handling/04-skip-and-continue/README.md) | Record the failure, skip the unit, finish the run. | measured |

### stop_on_first

*The first failed step ends the run.*

**Gives you**

- Spends nothing on a failure it cannot fix, which is the right answer when the failure is permanent.
- Never returns a partial result dressed as a complete one.
- Counts a reply that does not parse as a failure, so confident prose cannot pass as a completed step.
- Simplest possible policy; nothing to tune.

**Costs you**

- Loses the whole run to a failure that would have cleared on the next attempt, which is the most common kind.
- Wastes all the work already done, unless a checkpoint store is paired with it.
- Turns a rate limit into an outage.

**Pick it when** Failures are rare and meaningful, and a human is watching.; Partial results are worse than no result.

**Avoid it when** The transport or the provider is flaky, which is most of the time.

### retry_same

*Send the same request again, up to a budget.*

**Gives you**

- Handles the most common real failure: one that goes away.
- One number to set, and its meaning is obvious.
- No change to the request, so nothing about the run's semantics shifts when it retries.

**Costs you**

- Cannot fix a failure whose cause is the request itself. Against that shape it spends the entire budget learning nothing.
- Multiplies cost on exactly the runs that were already going badly.
- A budget large enough to ride out a real outage is a budget large enough to hide one.

**Pick it when** Failures are transient and independent.; A retry is cheap relative to losing the run.

**Avoid it when** The failure is deterministic in the request. Escalate instead.

### retry_with_escalation

*Retry plainly first; when that stops helping, change the request.*

**Gives you**

- The only policy here that recovers a failure caused by the request itself, which no amount of retrying can fix.
- Escalates only after plain retries fail, so a transient failure costs zero escalations.
- The ladder is a field, not a subclass, which is the same shape as this runtime's own escalation ladder.

**Costs you**

- More expensive than plain retry on every failure it does not fix, because it pays the plain budget and then the escalated one.
- Escalating changes the request, so the successful attempt is not the attempt that was specified. That has to be recorded or the run is not reproducible.
- Two budgets to set instead of one.

**Pick it when** Failures have more than one cause and some are request-shaped.; You can express a stronger version of the same request.

**Avoid it when** Every failure is transient. The ladder is then pure overhead.

### skip_and_continue

*Record the failure, skip the unit, finish the run.*

**Gives you**

- The only policy here that finishes a run containing a failure nothing could fix.
- Partial results are the right answer for plenty of work, and this is the only arm that can produce one.
- Returns the lost units as a field rather than a log line, so a caller can decide rather than discover.

**Costs you**

- Returns an answer that is quietly wrong. In the permanent-failure scenario it answered rather than stopping, and the answer did not match the truth.
- The wrongness is proportional to what was skipped and there is nothing in the answer itself that shows it.
- Needs a verifier beside it to be safe. Alone it converts a visible failure into an invisible one.

**Pick it when** Partial results have value and the caller can see what was lost.; You are pairing it with independent verification, which together give a finished run and an honest refusal.

**Avoid it when** Anything consumes the answer without reading the lost list.

## memory

**What does an earlier run contribute to a later one?**

Varies: what survives between runs and what has to happen before it is believed.  
Held constant: the loop, the transport and the world.  
Decides: the savings each design buys and the blast radius it opens.  
Read first: poison_served next to warm_calls; they move together, and that is the trade.

| # | Embodiment | In one line | Status |
|---|---|---|---|
| 01 | [`none`](memory/01-none/README.md) | Nothing survives a run. | measured |
| 02 | [`checkpoint_resume`](memory/02-checkpoint-resume/README.md) | The position survives a stop. Conclusions never do. | measured |
| 03 | [`cross_run_cache`](memory/03-cross-run-cache/README.md) | Remember the answer and serve it whenever the task matches. | measured |
| 04 | [`governed_journal`](memory/04-governed-journal/README.md) | Stage, review, promote, recall. Nothing promotes itself. | measured |

### none

*Nothing survives a run.*

**Gives you**

- Cannot be poisoned. There is nothing to write to.
- Every run is reproducible from its inputs alone.
- No storage, no keys, no eviction, no staleness.

**Costs you**

- Identical work is redone in full every time.
- A run that stops loses everything it had done.
- Nothing improves with experience.

**Pick it when** Runs are cheap, or inputs never repeat.; You need every run to be independently reproducible.

**Avoid it when** Runs are expensive and inputs repeat.

### checkpoint_resume

*The position survives a stop. Conclusions never do.*

**Gives you**

- A stopped run keeps its progress, which is the difference between a retry and a restart.
- Nearly all of the cache's saving without any of its exposure: a repeat cost 1 call against the cold run's 17, because the position is already at the end and the answer is re-derived from the state rather than served.
- The worst a corrupted checkpoint can do is start from a wrong subtotal, which recomputation catches. It cannot make a run report someone else's conclusion, and the poison scenario confirmed it.
- No review machinery needed, because nothing is ever believed.

**Costs you**

- One call short of the cache on a repeat, so it is not free where the cache is.
- Keyed on the task, so a changed input silently misses.
- A stale checkpoint against a changed world is a real hazard, and the position and the subtotal must be stored together or a resumed run counts the same work twice. This folder shipped that defect until a measurement found it.

**Pick it when** Runs are long and interruption is normal.; You want durability without opening a trust surface.

**Avoid it when** The same task repeats often and you want the savings.

### cross_run_cache

*Remember the answer and serve it whenever the task matches.*

**Gives you**

- The largest possible saving: a repeat costs zero calls.
- Trivial to implement and to reason about.
- Latency on a hit is a lookup.

**Costs you**

- Anything that can write decides what later runs believe. An outsider's record was served unchanged and the run returned it as its answer.
- The margin it buys over a checkpoint store is one call out of seventeen, and it pays for that margin with total exposure.
- No provenance, no review, no re-derivation.
- A wrong answer, once written, is served forever and looks authoritative because it is fast.

**Pick it when** The store is trusted end to end and answers are genuinely deterministic in the key.

**Avoid it when** Anything other than the run can write, or the key does not fully determine the answer.

### governed_journal

*Stage, review, promote, recall. Nothing promotes itself.*

**Gives you**

- Gets the repeat saving without the blast radius: an unreviewed record is staged and never served.
- The gate is a second derivation, not a policy string, so it catches what a policy string cannot.
- Refuses to serve anything at all when no reviewer is configured, which is the correct default.
- Superset of resume: it checkpoints too.

**Costs you**

- The most machinery of any arm here: two stores, a reviewer, a journal and a promotion rule.
- The saving only arrives after review, so the first run pays for both the work and the check.
- A wrong reviewer promotes wrong records, so the reviewer is now the thing that has to be right.

**Pick it when** You want runs to accumulate and more than one thing can write.; Being wrong is expensive enough to pay for a review.

**Avoid it when** Nothing repeats, or you cannot write an independent reviewer.

## verification

**How does an answer get accepted?**

Varies: what has to pass before a run is called finished.  
Held constant: the loop, the transport and the world; faults are injected identically into every arm.  
Decides: which wrong answers each policy actually stops, and what the strongest one costs.  
Read first: the missed column; a policy that misses the internally consistent fault is the common case in production.

| # | Embodiment | In one line | Status |
|---|---|---|---|
| 01 | [`self_report`](verification/01-self-report/README.md) | The run is done when it says it is done. | measured |
| 02 | [`engine_gate`](verification/02-engine-gate/README.md) | Structural gates that need no second pass over the world. | measured |
| 03 | [`independent_recompute`](verification/03-independent-recompute/README.md) | A second implementation reads the world again and recomputes. | measured |

### self_report

*The run is done when it says it is done.*

**Gives you**

- Free. No second pass, no second implementation.
- Never rejects a correct answer.
- It is what a system does by default, so measuring it prices doing nothing.

**Costs you**

- Caught nothing. All five injected faults were accepted.
- The confident wrong answer is exactly the case it cannot see.
- Gives an acceptance signal that carries no information.

**Pick it when** Wrong answers are cheap and visible downstream.; You are prototyping and know this is the baseline.

**Avoid it when** Anything acts on the answer without a human reading it.

### engine_gate

*Structural gates that need no second pass over the world.*

**Gives you**

- Costs no extra reads, so it is affordable on every run.
- Caught four of five faults, including two that a reader would expect to need recomputation: an answer that stopped early, and a total that disagreed with its own account breakdown.
- The agreement check is the cheap one people skip and it is the one that earns its place: an answer that contradicts its own run is wrong whatever it says.

**Costs you**

- Missed the one fault that agrees with itself at every level, where the total, the breakdown and the count were all moved together. No structural check can see that, by construction.
- Every gate is a rule someone wrote, so it only covers the failures that were imagined.
- Scores well enough against ordinary faults to give a false sense of coverage.

**Pick it when** You want a default that is strictly better than free.; Answers are structured and referential.

**Avoid it when** Correctness of the arithmetic is the thing at stake.

### independent_recompute

*A second implementation reads the world again and recomputes.*

**Gives you**

- Caught all five faults, including the internally consistent one that the structural gate cannot see.
- Shares no work with the run, so a defect cannot propagate into its own check.
- Rejected nothing on the clean control.

**Costs you**

- Costs a full second pass over the world, one read per unit, and the harness records exactly that.
- Needs a second implementation, which is real work and can itself be wrong.
- Only applies where the answer can be recomputed at all.

**Pick it when** Something acts on the answer automatically.; The answer is cheap to recompute relative to its cost being wrong.

**Avoid it when** Recomputation is as expensive as the original run and the answer is low stakes.

## Adding one

1. Make `<family>/<NN-name>/`, choosing the family whose question
   your idea answers differently. A new question is a new family,
   which needs its own `family.json` and `harness.py`.
2. Write `embodiment.py` with an `ARM` dict and a `self_check()`.
3. Write `manifest.json`. Both `cons` and `avoid_when` are required
   and must be non-empty. An option with no stated cost does not
   help anyone choose.
4. Run `python3 registry.py check`, then `catalog`.

Nothing has to be added to a list. Discovery is by folder, so the
catalogue cannot go stale against what is on disk.

Generated by `registry.py catalog`. Edit the manifests, not this file.
