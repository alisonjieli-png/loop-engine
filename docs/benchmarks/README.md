# Benchmark registry

Published harness results use a separate evidence catalog:

- [`published-harness-evidence.json`](published-harness-evidence.json) stores
  only source-backed published results.
- [`published-harness-evidence.schema.json`](published-harness-evidence.schema.json)
  requires benchmark, model, population, tools, score, date, source, and evidence
  qualifier fields.

The published-evidence catalog does not run a harness. It keeps model-only
results separate from harness measurements. Each admitted value links to the
source that reported it.

The registry contains 144 candidate tracks across ten families. A track may be
one benchmark, one official subset, or one task inside a benchmark suite. This
count is not 143 independent publications.

No registry entry has been promoted from `cataloged_not_run`, and every entry
still has `eligible_for_comparison: false`. Two separately frozen full-system
smoke populations have now run: three OpenML-CC18 tasks and four DS-1000
tasks. Their status does not silently promote the broader registry entries.
See the [case studies](../../case-studies/) and the
[historical first-portfolio review](FIRST-LOOP-ENGINE-PORTFOLIO-SOURCE-REVIEW.md).
The registry remains a research queue, not a scoreboard.

Files:

- [`benchmark-registry.yaml`](benchmark-registry.yaml) is the machine-readable
  catalog.
- [`benchmark-registry.schema.json`](benchmark-registry.schema.json) defines
  the required fields and allowed values after YAML anchors are resolved.

## What one entry records

Each entry names the task, modality, official source, evaluator, access terms,
network and cost needs, contamination risk, current status, and next gate.
Shared YAML templates keep repeated suite metadata consistent. A YAML parser
expands each template into a complete record.

License text in the registry is a triage note. It is not legal approval. Some
suites wrap datasets that retain separate licenses. LegalBench states this
explicitly for its tasks, and BEIR makes the same distinction for its source
datasets.

## Promotion stages

### Catalog

An official source exists. Nothing has been downloaded or scored.

### Source review

Freeze these items before implementation:

- benchmark release, commit, dataset split, and exact task IDs;
- input file digests and any container image digests;
- official evaluator version, metric direction, and tie handling;
- license, redistribution limits, account terms, and safety controls;
- expected storage, network access, model calls, compute, and money;
- known contamination, leakage, broken-task, and judge-model risks.

A benchmark that cannot meet these requirements stays in source review.

### Local smoke

Run a small declared subset. Prove that the adapter reads the frozen inputs,
the output contract rejects malformed answers, and the official evaluator can
score a known answer. A passing smoke run proves integration only. It does not
establish task performance.

### Frozen evaluation

Declare the task population before the run. Keep every attempted task,
including failures, timeouts, refusals, and infrastructure errors. Save the
exact settings, dependency versions, model route, token use, elapsed time, and
evaluator output for each task.

### Comparison ready

A comparison becomes eligible only when every arm uses the same frozen task
population and the same independent evaluator. If one arm cannot attempt a
task, that task remains in the denominator and receives its declared failure
treatment.

## Comparison rules

Freeze the inputs first. A task ID is not enough when the upstream dataset can
change. Record the release or commit and digest the downloaded files.

Freeze the oracle separately. The system under test must not choose its own
grader, edit expected answers, or change thresholds after seeing results.
Model-graded tasks require a pinned judge model, prompt, sampling settings, and
failure policy.

Compare paired tasks. Deterministic, hybrid, and non-deterministic arms must
attempt the same task IDs. Provider-pinned and fallback-enabled arms are
different arms because they answer different questions.

Do not average unlike raw metrics. Accuracy, nDCG, ANLS, resolved rate, F1,
and Kaggle competition metrics have different meanings. Report each track in
its native metric, then report family-level counts such as tasks attempted,
tasks accepted by their own oracle, model calls, wall time, and cost.

Keep selection visible. If a 100-track campaign selects tracks from this
registry, save the selection rule and every exclusion before execution. Do not
choose the final population after seeing scores.

Treat contamination as a field, not a footnote. Public static prompts usually
have high contamination risk. A private test set lowers answer leakage risk,
but it does not remove training overlap in source data or task format.

## Suggested first campaign

Start with a small, low-cost slice. Pick one locally executable track from each
family whose terms and evaluator have passed source review. Freeze the selected
run mode before outcomes. The current first campaign uses non-deterministic
Practitioner work with deterministic retrieval, execution, validation, and
grading spawned Loops. That is a campaign choice, not a universal benchmark rule.

The first broad campaign should measure coverage and failure modes. It should
not claim that Loop Engine is better than a specialized model or another
harness. Such a claim needs a named baseline, the same frozen population, the
same evaluator, and complete cost accounting.

## Primary sources used for the catalog

The catalog uses official project pages, repositories, dataset cards, and
competition pages. Key suite sources include:

- [AgentBench](https://github.com/THUDM/AgentBench),
  [GAIA](https://huggingface.co/datasets/gaia-benchmark/GAIA),
  [BFCL](https://gorilla.cs.berkeley.edu/leaderboard), and
  [tau-bench](https://taubench.com/) for agent and tool tasks.
- [BEIR](https://github.com/beir-cellar/beir) for retrieval tracks.
- [LongBench](https://github.com/THUDM/LongBench) for 21 long-context tasks.
- [LegalBench](https://github.com/HazyResearch/legalbench) for legal tasks and
  task-specific license metadata.
- [Harvey Legal Agent Benchmark](https://github.com/harveyai/harvey-labs/tree/v1.0)
  for long-horizon legal work products, matter files, and all-pass rubrics.
- [SWE-bench](https://github.com/princeton-nlp/SWE-bench),
  [LiveCodeBench](https://github.com/LiveCodeBench/LiveCodeBench), and
  [DS-1000](https://github.com/xlang-ai/DS-1000) for coding and data science.
- [Spider](https://github.com/taoyds/spider),
  [BIRD](https://bird-bench.github.io/), and
  [TableBench](https://github.com/TableBench/TableBench) for SQL and table
  work.
- [DocVQA](https://www.docvqa.org/datasets),
  [FUNSD](https://github.com/crcresearch/FUNSD), and
  [CORD](https://github.com/clovaai/cord) for document work.
- [HELM Safety](https://crfm.stanford.edu/2024/11/08/helm-safety.html),
  [HarmBench](https://github.com/centerforaisafety/HarmBench), and
  [AgentHarm](https://github.com/UKGovernmentBEIS/inspect_evals/tree/main/src/inspect_evals/agentharm)
  for safety evaluation.
- [MMMU](https://github.com/MMMU-Benchmark/MMMU) and
  [MM-Vet](https://github.com/yuweihao/MM-Vet) for multimodal reasoning.
- [MLE-bench](https://openai.com/index/mle-bench/) and official
  [Kaggle competitions](https://www.kaggle.com/competitions) for machine
  learning agents and private-test competitions.

The `source_url` on each registry entry is the source to review for that track.
Search summaries and third-party benchmark lists are not sources of record.
