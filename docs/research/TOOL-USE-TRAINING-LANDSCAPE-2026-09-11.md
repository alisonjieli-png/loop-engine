# Tool-use training landscape, 2026-09-11

Research pass, no runtime changes. All results below are author-reported;
none was reproduced here. External numbers are cited with source and are
not claims about Loop Engine.

## 1. Answer-first data generation (ToolGrad)

Zhou et al., ACL 2026 Findings. Generate the verified tool chain first,
annotate the user query after (one LLM step): 99.8% pass rate, lower
cost, longer-horizon chains than query-first DFS.
Proposer → parallel Executors → Selector (the choice is the "textual
gradient") → Updater. Gemma-3-12B fine-tuned on 500 samples scores 83.1
on BFCL (vs gemini-2.5-pro 83.2, claude-4.5 Opus 82.8, gpt-5 74.4);
student beats its teacher (gemini-2.5-flash-lite); OOD transfer to
unseen tools. Repo needs no GPU.
Sources: blog, paper (arXiv:2508.04086), code (github.com/zhongyi-zhou/toolgrad).
Loop Engine mapping: our fixture-based qualification already uses the
answer-first inversion for *evaluation*; ToolGrad applies it to
*training*. A ToolGrad-class 12B model on tactical is the most direct
fix for our orient-repair burn.

## 2. Textual optimization without weight updates (TextGrad → GEPA)

GEPA (Agrawal et al., ICLR 2026 Oral, arXiv:2507.19457, `dspy.GEPA`):
reflective prompt evolution over full execution traces beats GRPO by up
to 19pp using up to 35x fewer rollouts; prompts optimized on weak
Qwen3-8B transfer +9% to GPT-4.1-Mini untouched; works on closed models.
Key concept: Actionable Side Information (diagnostics, not just scores).
Loop Engine mapping: our per-step question sets, personas, and guidance
blocks are hand-authored text parameters with step-affinity metadata
(exactly GEPA's optimization surface). Our gates are ready-made metrics
and the campaign runner already produces rollouts. Concrete experiment:
evolve orient questions against gate-pass rate on the 8 adapted tasks.

## 3. Agentic RL with verifiable rewards

Survey (500+ works, arXiv:2509.02547, TMLR 01/2026): field shifting from
imitation to outcome-driven optimization; RLVR theory (Mroueh;
Wen et al., ICLR 2026) shows verifiable rewards amplify success
probability and incentivize correct intermediate reasoning, not just
sampling efficiency.
RLTR (EMNLP 2025 industry): reward *tool-use completeness* of the
action sequence instead of final-answer correctness (trains planning
without verifiable final answers).
ToolRL (NeurIPS 2025 poster): principled reward design for tool
selection/application; +17% over base, +15% over SFT, better
generalization.
Loop Engine mapping: gate.sh files ARE verifiable rewards today (8
tasks). RLTR's completeness reward maps onto our per-step admission +
repair signals: we already score action sequences, not just outcomes.
A future fine-tune could reward the trajectory our ledger already
records.

## 4. Self-evolving data (R-Zero, Absolute Zero, SWE-smith)

R-Zero (ICLR 2026): Challenger proposes tasks at the Solver's edge,
Solver solves, both co-evolve with GRPO from zero labels; Qwen3-4B
+6.49 math / +7.54 general; works as mid-training amplifier.
SWE-smith (NeurIPS 2025 spotlight): synthesize bugs into real repos to
mint 100s-1000s of tasks per codebase; 50k instances over 128 repos;
SWE-agent-LM-32B reaches 40.2% SWE-bench Verified, open SOTA.
Loop Engine mapping: our 8 adapted + 318 raw Kaggle tasks are the seed
corpus SWE-smith-style synthesis could multiply; our verifier/producer
split and alternatives portfolio already resemble Challenger/Solver;
the self-improvement task (staged candidates, independent review) is
the governed version of the same loop.

## Ranked next steps for Loop Engine

1. GEPA-style evolution of orient/step questions against gate pass rate
   (no weight training, closed-model compatible, uses existing gates).
2. ToolGrad-12B-class model on tactical (external proposal; fixes the
   compliance burn directly).
3. SWE-smith-style synthesis to grow 8 gated tasks toward 100s.
4. Trajectory-level rewards (RLTR-style) from ledger admission signals
   when a fine-tune is on the table.

## Limitations of this note

No paper above was reproduced; benchmark numbers (BFCL, SWE-bench,
AIME) measure narrow capabilities, not open-task success; RL and
self-evolution results assume verifiable rewards we hold for 8 tasks
only. Treat every number as directional.
