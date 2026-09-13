# Deep research: tool-use training lines, 2026-09-11 (round 2)

Follows TOOL-USE-TRAINING-LANDSCAPE-2026-09-11.md. Each line below is
carried to an experiment design with a falsifier. Author-reported
numbers throughout; nothing reproduced.

## A. GEPA on orient questions (cheapest, no weights, no endpoint upgrade)

GEPA (arXiv:2507.19457, ICLR 2026 Oral, `dspy.GEPA`): reflective prompt
evolution from full traces beats GRPO up to +19pp at 35x fewer rollouts;
cross-model transfer (+9% GPT-4.1-Mini from Qwen3-8B-optimized prompts).
Core trick: feedback function returns (score, feedback_text), not just a
scalar; Pareto frontier keeps complementary lessons.
Experiment: trainset = orient prompts (8 adapted tasks x arms);
metric = schema-valid orientation within 2 attempts (repairs counted);
feedback_text = rejection codes + digests from our ledger. Evolve the
14 orient questions; hold out 2 tasks. Falsifier: evolved set does not
cut repair rate vs baseline on held-out tasks.
Cost: orient attempts only (~2 calls each), runnable on tactical today.

## B. toolgrad-12b served locally (fixes the compliance burn directly)

The model exists: huggingface.co/zhongyi-zhou/toolgrad-12b (Gemma-3-12B
fine-tune for function calling, Apr 2026). 12B at Q4 is ~7-9 GB, which
fits this box's RTX 3060 (12 GB) via llama.cpp server. Wire as a
`local` custom provider (settings already support it; counted
generation on local needs the explicit policy flag, off by default).
Experiment: A/B the same cells (toolgrad-12b vs gemma-abliterated),
primary metric orient repair rate, secondary gate passes. Falsifier:
no repair-rate improvement (then the burn is prompt-side, not model).
Note: local serving sidesteps both the Ollama quota and tactical
outages entirely.

## C. SWE-smith synthesis on our own repos (grow 8 tasks toward 100s)

Pipeline (MIT, pip-installable, needs Docker which we have): procedural
AST edits + LM rewrites + PR mirrors + patch combination → validate
against existing tests (valid.py/eval.py/gather.py). Cost precedent:
$1,360 for 50k instances; issue text ~2.5c each (needs an LM key:
tactical endpoint qualifies). BugPilot (arXiv:2510.19898) shows agentic
bugs are harder than rule-based ones; start rule-based.
Experiment: pilot on loop-engine itself (Python, has suite): mint N
instances, keep those failing exactly the targeted tests, adapt each to
a task.txt/gate.sh/metric.json triple in our adapted format. Falsifier:
instances don't validate (tests don't break cleanly) or gates don't
discriminate (constant predictor passes).
Caution: synthetic bugs test repair skill, a different shape from our
Kaggle train-a-model tasks; track the mixture, don't merge blindly.

## D. Trajectory rewards from existing histories (zero new runs)

RLTR (EMNLP 2025): reward tool-use completeness of the action sequence,
not final answers (trains planning without verifiable data). ToolRL
(NeurIPS 2025): principled tool reward design, +17% base / +15% SFT.
Our ledger already records per-step admission, repair counts, usage,
and verification per attempt. Experiment: score all 24 campaign cells
on completeness (acted? artifacts? verified?) and test whether it ranks
arms differently from gate passes. Pure offline analysis; decides
whether trajectory rewards carry signal worth training on later.
Falsifier: completeness ranking == gate ranking (no added signal).

## E. R-Zero challenger/solver (watch, don't build)

Challenger proposes edge-of-capability tasks, Solver solves, co-evolve
(Qwen3-4B +6.49 math). Our verifier/producer split and alternatives
portfolio rhyme, but we lack the training loop to close it. Revisit
after A-D. No action now.

## Ranked order

A (days, tactical suffices) → B (needs half a day + disk; removes the
provider bottleneck structurally) → C (needs B or quota for issue
text at scale) → D (evenings, offline) → E (later).
