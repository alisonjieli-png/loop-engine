# SKILL.state research: state-centric execution and the cache question

Review date: 2026-09-01. This document records what a published paper claims,
what it does not report, and what that means for Loop Engine. Every claim below
is labeled observed, inferred, assumed, or unverified.

## Source

Sanket Badhe, Priyanka Tiwari (Google LLC), Jonghyun Chung (Google LLC /
Purdue University). "SKILL.state: Scalable Long-Horizon Agent Skills."
arXiv:2608.26263v2, revised 2026-08-28, accepted at EMNLP.
<https://arxiv.org/abs/2608.26263>

No code has been released as of this review date. Nothing in the paper has been
independently reproduced.

## What the paper reports (observed, from the paper's own tables)

SKILL.state replaces append-only conversation history with one structured,
mutable execution state. At each step the model receives exactly:

```text
A_t = (P, Sigma_t, O_t)
```

- P: the immutable skill specification
- Sigma_t: the current structured execution state
- O_t: the latest observation only

The model returns reasoning, a typed state patch, and one action. A
deterministic runtime validates the patch, merges it, executes the action, and
discards the reasoning permanently. Invalid patches roll back and retry; the
model cannot corrupt the state.

Reported results on their SkillExecBench warehouse environment
(Gemini-3-Flash, 5 seeds, mean plus or minus standard deviation):

| Horizon | ReAct score / total tokens | Stateful score / total tokens | SKILL.state score / total tokens |
|---:|---|---|---|
| 10 | 0.90 / 9,438 | 1.00 / 10,337 | 1.00 / 5,870 |
| 50 | 0.88 / 171,658 | 0.94 / 170,992 | 0.96 / 30,151 |
| 100 | 0.84 / 1,245,413 | 0.91 / 1,062,387 | 0.94 / 65,408 |
| 200 | 0.74 / 2,608,755 | 0.88 / 5,041,164 | 0.94 / 122,384 |

The often-cited comparison is T=100: 1,062,387 tokens (Stateful baseline) down
to 65,408 (SKILL.state), a 16.2x token reduction, with accuracy 0.94 against
0.91. Their complexity claim is O(1) prompt size and O(T) cumulative tokens,
against O(T^2) cumulative for append-only history.

Other reported results (observed, from the paper):

- Noise robustness at T=50 with 50 distractor events per turn: ReAct 0.53,
  SKILL.state 0.98.
- Silent external state change: history baselines took 5 to 8 turns to
  recover; SKILL.state took 0, because decisions read the current state and
  the corrective alert simply updates it.
- Budget-matched controls (all pinned to about 1,800 tokens at T=100):
  sliding window 0.18, LLMLingua compression 0.22, summary-capped 0.52,
  SKILL.state 0.94. Structure, not brevity, carries the accuracy.
- Public benchmarks: InterCode CTF pass@1 54.2 percent (best baseline 46.4)
  at 387k total tokens; tau-Bench Retail 58.3 percent at 3.47M tokens.

## The question the paper does not answer (the cache gap)

The word "cache" does not appear in the paper. This matters because
append-only history is the most cache-friendly prompt shape there is: step
t+1's prompt is step t's prompt plus a small suffix, so a provider can bill
almost the whole prefix at the cached rate. A rewritten state object has no
stable prefix beyond the fixed specification P, so most of each prompt is
billed fresh. The paper reports token counts, which is not the same as the
bill.

### Worked cost model (inferred; assumptions stated)

Assume a provider bills cached input at one tenth of fresh input, which is
close to current published rates on major providers. Assume ReAct achieves a
97.4 percent cache hit on its accumulated prefix (a real platform-reported
figure from an operator of long-horizon agent sessions; treated here as an
input assumption, not a paper result).

At T=100, Stateful baseline, about 1,062,387 cumulative tokens. Roughly
35,000 of those (new suffix per step, about 350 per step) would be fresh; the
rest billed at 0.1x:

```text
Stateful effective cost ~= 35,000 fresh + 1,027,387 cached x 0.1
                        ~= 137,700 effective fresh-equivalent tokens
```

SKILL.state, 65,408 cumulative tokens. The specification P is the same every
step and could be cached (assumed 500 tokens of the roughly 1,900-token
prompt); state and observation are rewritten each step:

```text
SKILL.state effective cost ~= 100 x (500 cached x 0.1 + 1,405 fresh)
                          ~= 145,500 effective fresh-equivalent tokens
```

Under these assumptions the 16x token gap collapses to roughly parity on
input cost per attempt. The exact crossover depends on |P|, |Sigma|, |O|, the
provider's cached-price ratio, and the real cache-hit ratio; the direction of
the conclusion is that token reduction alone does not settle the economics.

### What still favors SKILL.state even at cost parity (inferred)

- Cost per completed task: accuracy 0.94 against 0.91 means fewer retries.
  Expected attempts per success are 1/0.94 = 1.064 against 1/0.91 = 1.099,
  about a 3 percent cost advantage, and at T=200 against ReAct (0.74) the
  advantage is about 21 percent.
- Output tokens are never cached on any provider, and reasoning tokens are
  output. Both runtimes pay full price there; the paper does not report
  output-token splits.
- Prefill latency for a 36,000-token prompt is slower than a 1,900-token
  prompt even with cached billing, so wall-clock still favors the state
  runtime.
- The noise and state-recovery results (0.98 under heavy noise; zero-turn
  recovery) are quality effects with no cache offset; cache discounts do not
  compensate for wrong answers caused by poisoned history.

### What favors append-only runtimes (inferred)

- Very high cache-hit deployments (the 97.4 percent figure) narrow or close
  the input-cost gap at moderate horizons.
- Append-only needs no schema authoring. SKILL.state requires a state schema
  written once per domain, and its own limitations section names three
  failure settings: unknown schemas, late-recognized observations that were
  never committed to state, and trajectory-defined tasks (auditing,
  provenance) where history is the deliverable.
- Open-weight small models failed mostly on structured-output adherence
  (their Gemma-4-31B error taxonomy: 68 percent state-overwrite errors,
  20 percent type coercion, 12 percent JSON slips), so the runtime needs
  constrained decoding for weaker models.

## Who measures cost per completed task (observed state of the field)

Most agent benchmarks report token counts and success rates; few report
currency cost. The AgentBench, GAIA, and tau-Bench families report tokens or
turns. SWE-agent-style harnesses have reported dollars per resolved instance
because the task has a binary verifier, which makes cost-per-completed-task
well defined. The general practice this review recommends, and the gap it
found: any runtime that claims an economic win should publish effective cost
per completed task, computed from the provider's actual cached and fresh
prices and the measured cache-hit ratio, not raw token counts. Loop Engine's
own benchmark rules already require token-accounting completeness; currency
cost per completed task is the stricter form of that rule.

## What this means for Loop Engine

Loop Engine is already closer to the state-centric shape than to ReAct:

- Every model step receives a freshly assembled work packet built from typed
  blocks (constitution, persona, current state, bounded source views), not an
  appended transcript. The adaptive run record keeps context snapshots as
  evidence, but the next prompt is assembled from current state, not from
  the previous prompt plus a suffix.
- The semantic runtime already implements the trust half of SKILL.state's
  design: candidate output is validated by admission, committed by an
  independent verifier and effect controller, and intermediate reasoning is
  never granted authority.
- The non-progress escalation ladder already discards failed-approach detail
  into documented failures rather than letting obsolete reasoning poison the
  next pass.

Gaps SKILL.state makes explicit, as candidates for measurement rather than
immediate implementation:

1. Prompt-size boundedness: Loop Engine's packets were observed around 22,000
   to 26,000 input tokens per step in the 2026-09-01 Kaggle runs (observed in
   run records), not growing quadratically but not yet measured against a
   stated bound. A per-pass prompt-size metric would make boundedness a
   checked contract rather than an assumption.
2. Cost-per-completed-task reporting: Loop Engine records provider-reported
   input and output tokens per attempt and marks missing usage unknown. A
   settings-declared price table (fresh and cached rates) would let run
   reports state effective cost per attempt and per verified success. That
   adds a pricing authority, so it is a deliberate design change, not a
   patch.
3. State-sufficiency check: Loop Engine's step questions and orientation
   records already behave like a typed state. The open question is whether
   any late-recognized observation ever needs history the state never kept;
   the run record's context snapshots make this auditable.

## Decisions

1. Treat SKILL.state as directionally confirmed for accuracy, latency, and
   robustness under noise (paper-observed, unreproduced).
2. Treat its economics as unproven until measured under real cache pricing.
   Any adoption argument must compare effective cost per completed task,
   never token counts.
3. Do not adopt a state-rewrite runtime on token grounds alone. Loop
   Engine's packet architecture should stay, and its prompt-size
   boundedness should become a measured metric.
4. A candidate increment: per-pass prompt-size and cache-eligible-prefix
   metrics in run records, then a price-table authority for cost reports.
   Both follow the existing run-record and accounting rules; neither
   changes runtime authority.

## Limitations of this review

- The paper is recent, unreproduced, and has no released code; every number
  above is author-reported.
- The cache model is a worked estimate under stated assumptions, not a
  benchmark result. Real crossover points need measured cache-hit ratios
  and provider invoices.
- The 97.4 percent cache-hit ratio is an operator-reported figure used as
  an input assumption, not a verified measurement.
- Loop Engine prompt sizes cited here come from the 2026-09-01 Kaggle run
  records and are environment-specific.
