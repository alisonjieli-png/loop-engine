# Research round 4: debate, serving, verifiers, 2026-09-11

Follows the three earlier landscape notes. Author-reported throughout;
nothing reproduced. Each section ends with the Loop Engine mapping.

## 1. Multi-agent debate: mostly ensemble, with a real exception

- Debate-or-Vote (NeurIPS 2025, Wisconsin): debate induces a martingale
  over belief trajectories. Debate alone does not improve expected
  correctness; majority voting captures most gains. Confidence-guided
  debate (DOWN: debate only when uncertain, ~2.5 calls avg) matches full
  debate at a fraction of the cost and guards against cascading errors.
- Nature MI (Jul 2026, 260 configs x 3 model families x 6 benchmarks):
  single-agent baseline strength is the best predictor of whether
  coordination helps; a capability-saturation threshold exists beyond
  which more agents add overhead (spans +80.8% to −70.0% by domain).
- Counterpoint: Anthropic reports Opus 4 coordinating Sonnet subagents
  +90.2% on complex research tasks. Decomposition with asymmetric
  roles (strong orchestrator, cheap workers) works where symmetric
  debate does not.
Mapping: our portfolio arm is voting, not debate (consistent with the
evidence). Our practitioner/spawned (strong) + solution (cheap) split
matches the asymmetric pattern that works. Do not build symmetric
debate; do build confidence-gated escalation (DOWN-style: extra
agents only when uncertainty is high). This sharpens backlog P0-1:
the repetition guard should trigger on low-confidence recurrence,
not bare counts.

## 2. Local serving is fully specified (unblocks line B)

vLLM OpenAI-compatible server: chat API + `guided_json/regex/choice/
grammar` + `--tool-call-parser {hermes, llama3_json, mistral,
pythonic...}` + `--api-key`. toolgrad-12b (Gemma-3-12B) at Q4 fits
our 12 GB 3060. Two cautions from round-3 reading: (a) guided
decoding is the constrained-decoding path we recorded as a non-goal
for compliance: serve PLAIN first, compare, and only then trial
guided modes with executable-accuracy measurement; (b) Hermes-style
tool templates need the matching `--tool-call-parser`, else tool
calls come back as unstructured text and our admission layer will
(and should) refuse them.
Concrete bring-up: `vllm serve zhongyi-zhou/toolgrad-12b` (or GGUF
via llama.cpp server), OpenAI wire, model id pinned, then
`--verify-live-model` against a `local` custom provider entry before
any campaign cell touches it.

## 3. Process reward models (the verifier shelf)

- Math-Shepherd: auto-built step supervision (no humans);
  Mistral-7B 77.9→84.1 GSM8K via step-PPO, 89.1 with verification
  rerank. PRM beats ORM increasingly with task difficulty.
- AgentPRM (WWW 2026): promise (advances goal?) + progress
  (inter-step dependence) per agent step; 8x+ sample efficiency
  claims; GUI-Shepherd +7.7 online PPO / +5.1 as verifier.
- PRM survey loop: generate → train PRM → improve policy → new data.
Mapping: our independent verifier + admission checks are a
rules-based PRM already (per-step accept/reject with reasons). The
upgrade path is a learned reranker over candidate portfolios trained
on our ledger outcomes, but only after the trajectory-reward
analysis (round 1, line D) shows the signal exists. No new
instrumentation needed: the ledger already records what a PRM needs
(step, context digest, verdict, usage).

## Updated ranking deltas

- Backlog P0-1 (repetition guard) refined: gate on
  low-confidence recurrence (DOWN), not bare counts.
- Line B (local 12B) is now a recipe, not a proposal: vLLM flags,
  parser choices, and the guided-decoding caution are specified.
- No change: constraint-tax non-goal, GEPA-first ordering.
