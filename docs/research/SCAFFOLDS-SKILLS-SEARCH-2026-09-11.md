# Research round 3: scaffolds, skills, search, 2026-09-11

Follows the tool-use landscape and adjacent-lines notes. Author-reported
throughout; nothing reproduced. Loop Engine mapping per section.

## 1. The scaffold taxonomy (our embodiment catalogue, independently validated)

"Inside the Scaffold" (arXiv:2604.03515): source-code taxonomy of 10+
production coding agents (OpenCode, Gemini CLI, Codex CLI, OpenHands,
Agentless, mini-swe-agent, Prometheus...). Key findings: architectures
resist discrete classification. Control ranges from fixed pipelines to
MCTS, tools from 0 to 37, context compaction has seven distinct
strategies. Also: Agentless/DARS argue fixed pipelines can match
agentic scaffolds on SWE-bench.
Mapping: our 19 embodiments are an instance of exactly this spectrum
(we measure it instead of classifying it). Their pipeline-vs-agent
axis matches our control-flow axis (chooser vs batch). Their seven
compaction strategies map onto our context-transport arms. Nothing to
change; independent confirmation of the catalogue approach. Crossref
for future docs.

## 2. AIDE: the winning scaffold for our exact task class (steal these three pieces)

AIDE (arXiv:2502.13138, MIT, WecoAI/aideml): tree search over Python
scripts; DRAFT/DEBUG/IMPROVE operators; won MLE-bench (8.7% medals vs
OpenHands 4.4%, MLAB 0.8%); 4x more medals than the best linear agent.
Three transferable mechanics:

- Summarization operator Σ(T): each node's prompt carries ONLY
  metrics + hyperparameters + debug hints, never full logs. Our
  axes finding (bounded_state beats full_history 10x) reproduces
  this at small scale.
- Static data preview: rows/columns/splits injected into every
  coding prompt (cheap, and it replaces repeated EDA). Directly
  applicable: bake a data preview block into our ML-task prompts.
- Search policy is a hard-coded rule (draft/debug/improve), not a
  model decision: the intelligence sits in operators + tree, not in
  orchestration. Our kernel already separates these; the lesson is
  to keep step routing cheap and deterministic.
META's follow-up (NeurIPS 2025, arXiv:2507.02554): AIDE's OPERATORS,
not its search, are the bottleneck. Fancier search (MCTS,
evolutionary, crossover) didn't help; better operators did. Also:
MLE-bench slides note pass@8 clears 30% for o1-preview. Attempt
diversity is worth real medal percentage.
Mapping: highest-value port is the data-preview prompt block (hours,
prompt-side, works on any model); second is treating our alternatives
portfolio as AIDE-style draft/debug/improve nodes with per-node
summaries rather than pass-level history.

## 3. Skill libraries (our governed memory, with fresh cautions)

2026 surveys (arXiv:2607.10113 lifecycle taxonomy; arXiv:2605.07358
comprehensive): the field converged on our model: skills as stored,
retrievable, refined procedural artifacts with a lifecycle
(create/memory/manage/evaluate/refine); SKILL.md conventions and
registries are now standard; Anthropic ships a public skills repo.
Voyager remains the root (3.3x items, 15.3x tech tree).
Caution from "Demystifying Agent Skills" (arXiv:2608.14036): skill
benefits are real but bounded; growing libraries become confusable
(RQ4), portability across frameworks is partial, and benchmarks
mostly measure final success only. "Systematic Study of Model-Generated
Skills" (arXiv:2605.23899) flags selection/interference as unsolved
at scale.
Mapping: our semantic memory already implements the governed version
(candidate staging, independent approval, demotion). The warnings map
to features we have or need: retrieval precision measurement (have
per-run), interference at library scale (measure when ours grows),
cross-framework portability (unproven: test before claiming). No
runtime change; recorded as design constraints for the memory work.

## 4. Cross-links and updated rankings

The experiment ranking from round 2 gains one entry and one promotion:

- NEW: data-preview prompt block from AIDE (cheap, model-agnostic,
  targets our failure mode of agents never looking at the data before
  the budget dies, the same root cause the startup questions attack).
- PROMOTED: stepwise trajectory scoring (round 1, line D). META's
  operators-are-the-bottleneck finding says operator-level signals
  matter more than search-level ones; score operators, not passes.
Constraint-tax non-goal (round 1) unchanged: no provider-side
constrained decoding.
