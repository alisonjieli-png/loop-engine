# Vision-alignment review, 2026-09-12

Historical review, superseded for current status by the later
[architecture checkpoint](COGNITIVE-STEP-ARCHITECTURE-AND-STATE-2026-09-12.md),
[complete terminology explanation](../context/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-HANDOFF-2026-09-12.md),
and [configuration dimension requirement](../architecture/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md).
The notes below retain the original review's conclusions for traceability.
They are not current implementation or model-quality claims. In particular,
the small perfect scores do not establish that stronger models are unnecessary,
and the broad absence claims about graph export, reuse, reward records, and
asynchronous output need the later source review. Do not use this page as a
continuation prompt or as authority to promote an experimental harness.

Thesis under review (owner): prompt engineering → iterative prompting →
loop/graph engineering → harness-per-cognitive-step (each minimal,
containerized, with exactly the context/tools/plugins it needs) →
fingerprinted steps with heuristic shortcuts → solution-canvas DAG
pipelines → deterministic/hybrid/non-deterministic + async multi-output
→ self-improvement/RL groundwork → AGI experimental framework.
Method: four parallel read-only surveys (sessions, runtime, intel/
memory/harness, docs/evidence) on 2026-09-12. Nothing modified.

## 1. Stage verdicts (what the repo proves at each stage)

- Prompt engineering: superseded by architecture; prompt skill now
  lives in versioned intelligence (43 forms, portfolios), not lore.
- Iterative prompting: the kernel IS this (13 nodes + recovery
  ladder), measured live, but execution collapses to 8 setup nodes
  \+ act-only (17,928 act vs 0 calibrate/commit/ladder across 62 runs).
- Loop/graph engineering: Loop-only runtime enforced (subclassing
  refused); harness boundary registered; T1 17/19; full-solve 14/17.
- Harness-per-step: PARTIAL. Per-CALL isolation is proven (1:1
  process-per-model-call, bwrap, relay, no credentials/tools).
  Per-STEP harnesses (orient/decide/act/verify each with own minimal
  context) exist only as lab embodiments, not the default path.
- Frontier models unnecessary: SUPPORTED with bounds. Two perfect
  gate scores on a small coding-tuned model; failures are
  compliance/repair-burn, not reasoning depth. Evidence covers
  single-script ML tasks only, not long-horizon engineering.
- Fingerprint shortcuts: HALF. Integrity digests everywhere; task +
  stage fingerprints exist; embedding/LSH reuse and memo/skip paths
  do not. Nothing is ever skipped on similarity today.
- Solution canvas DAGs: plan compiles (digests, mermaid), pipeline
  controllers fired 3x, wave executor tested 5/5 but never called by
  solves. No DAG export format. Closest miss to the thesis.
- Modes/async: modes covered in type system; multi-output typed but
  unexercised live; no generic async portfolio primitive.
- Self-improvement/RL: groundwork only. Histories, lineage, staged
  candidates with governed promote/reject (proven working this week);
  no reward schema, no training loop, no weight updates anywhere.

## 2. Session archaeology (all three harnesses)

- OpenCode: 21 sessions / 440 prompts. Mega-session 09-10→12
  (35.5M tokens) holds output-type, T1, tactical, review work.
- Claude: 4 transcripts (~47M). 09-03 Kaggle campaign (fingerprints,
  no-hardcode rule); Fable audits; 09-08 Codex/Astra handoff.
- Codex: 177 history lines, 71 rollouts 09-03→09-12 (Astra research,
  harness trials incl. Pi, embodiments, pushes).
- "Cloud Code": NO independent existence, no store, no sessions,
  only prose mentions. Treat as Claude Code unless shown otherwise.
- Checkpoints: one (2026-08-26). prompt dir warns against
  concatenating mandates (because it happens).

## 3. Stale guidance flags

START-HERE (09-08) claims "all gates pass" while its own table shows
a failing gate; EVERYTHING-LEARNED-09-08 superseded by 09-10/11
trials; GPT-6-READINESS title overstates a hard-disabled route;
26+49 dated files are the main staleness vector. Retired LoopNode/
plane mandates still sit in prompts/ (marked retired, keep the
marks, don't paste them).

## 4. Ranked gaps (what to build, in order)

1. Wave executor in the solve path (P0-0, specified): turns plans
   into executing graphs, the thesis's missing center.
2. Step-harness default path (lab embodiments exist; promote one):
   per-cognitive-step minimal context instead of per-call only.
3. Fingerprint reuse (exact-match memo first; LSH later): the
   shortcut half of fingerprinting.
4. Repetition guard + coverage rails (specified, partly built):
   stops the burn that eats every run's budget.
5. Reward schema on ledger trajectories (line D): the RL groundwork's
   missing piece; needs no training to start recording.
6. DAG export format for canvases (programmer handoff: K8s/pipeline).
7. Async multi-output portfolio primitive.
8. Fresh checkpoint (last: 08-26) + START-HERE refresh.
