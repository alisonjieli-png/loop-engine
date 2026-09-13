# Adjacent lines: eval, constraints, test-time compute, 2026-09-11

Follows the tool-use landscape notes. Author-reported throughout;
nothing reproduced. Each section ends with the Loop Engine mapping.

## 1. Evaluating ML agents: MLE-bench, MLR-Bench

MLE-bench (OpenAI, ICLR 2025 Oral, arXiv:2410.07095, open code): 75
Kaggle competitions as agent tasks, human baselines from leaderboards.
Best setup (o1-preview + AIDE scaffold) reaches Kaggle bronze in 16.9%
of competitions. Design choices we should steal: medal thresholds as
the honest external yardstick (our floors are naive baselines: a
bronze-equivalent bar is stricter and comparable); preparation scripts
that re-split public train into train/test (exactly our gate.sh
holdout pattern, independently invented).
MLR-Bench (NeurIPS 2025): 201 open-ended ML-research tasks from
workshops with stepwise evaluation (MLR-Judge over 4 steps), the
precedent for scoring trajectories, not just final artifacts, which
supports research line D (trajectory rewards).
Mapping: re-score our 8 adapted tasks against medal-equivalent bars
where leaderboards exist; adopt stepwise judging for the repair-burn
analysis.

## 2. Constrained decoding and the constraint tax (directly our burn)

JSONSchemaBench (arXiv:2501.10868): Guidance has the highest open
compliance; Outlines times out on hard schemas (40s-10min on
minItems/enum/array features); constrained decoding also speeds
generation ~50% and lifts downstream task scores up to 4%.
WARNING from "The Constraint Tax" (2026, small models): hard schemas buy
validity but shift errors into wrong-valid-schema outputs. Calendar
tool-call analogue: 100% schema-valid both modes, but hard decoding
loses 43.5 points of executable accuracy; answer accuracy −8.7pp.
"Wrong answer, valid schema" is worse than a visible format failure.
Mapping: do NOT fix our orient-repair burn by constraining decoding at
the provider. Our repair loop preserves reasoning and fails loudly;
a grammar mask would convert visible failures into confident wrong
answers that pass admission. The right fix stays model-side
(tool-use-tuned model) or prompt-side (GEPA-evolved questions), with
format repair as the backstop. If constrained decoding is ever
trialed, measure executable/gate accuracy, never validity alone:
validity is the vanity metric here.

## 3. Test-time compute economics (why GEPA matters to us)

GEPA vs GRPO: +19pp at 35x fewer rollouts; MIPROv2 needs 2,270-6,926
rollouts per task family. Our campaign spent ~2,000 calls for 2 gate
passes: rollout-expensive, insight-cheap. The lesson: spend test-time
compute where feedback is richest (full traces + textual reflection),
not on identical-shape retries. Our proposed repetition guard (backlog
P0-1) is the degenerate version of this: stop paying for rollouts that
carry no new information. Metric to track going forward: gate passes
per 100 calls, split by novel-shape vs repeated-shape attempts.

## Ranked additions to the backlog

1. Medal-equivalent floors for adapted tasks where leaderboards exist.
2. Stepwise trajectory scoring (MLR-Bench-style) on existing run
   histories (feeds line D).
3. Explicit non-goal, recorded: provider-side constrained decoding as
   a fix for compliance burn (constraint tax). Revisit only with
   executable-accuracy measurement attached.
