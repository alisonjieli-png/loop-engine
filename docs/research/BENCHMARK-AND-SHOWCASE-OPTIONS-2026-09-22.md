# Benchmarks and demonstrations worth showing

Kind: dated primary-source benchmark research and proposed demonstration
design. Reviewed September 22, 2026. The [roadmap](../roadmap/roadmap.yaml)
remains the task authority, especially S-6.37, S-6.47, S-6.56 and D-23.
This record does not qualify a benchmark, authorize a model call, accept
competition rules, submit a result or publish a claim. External task and
dataset rights require review before use or redistribution.

## Current evidence before selecting a showcase

The [benchmark registry](../benchmarks/benchmark-registry.yaml) catalogs
144 tracks and marks none comparison-ready. Its `as_of` is August 25, 2026;
several external benchmarks changed after that date. The
[published harness review](PUBLISHED-HARNESS-BENCHMARKS.md) is a dated
Artificial Analysis version 1.4 snapshot, not a current result for version
1.5. The saved Loop Engine studies have no matched published external
harness comparison.

Existing examples and reports answer narrower questions:

| Local evidence | What it presently proves | Limit for a public demonstration |
|---|---|---|
| [Overnight local run example](../../examples/30_overnight_local_run/README.md) | Offline setup, resource and budget arithmetic, fixture transport, saved Run History and playback. | It makes zero physical model calls and opens no socket. It is not an observed unattended night with a local model. |
| [Exported-ticket pilot](../../examples/25_host_runtime/EXPORTED-TICKET-PILOT.md) | A local ticket fixture and checked output path. | It has no Jira connection, overnight schedule, customer repository push or customer workflow. |
| [Kaggle competition example](../../examples/05_kaggle_competition/README.md) | A narrow top-level comma-separated-value competition workflow with local validation. | It does not prove an arbitrary competition from task through official submission and score. Credentials, dataset terms and submission are separate effects. |
| [DS-1000 four-task record](../../case-studies/ds1000-four-task-recorded-output-correction.md) | A read-only recheck during this review ran `benchmarks/ds1000/verify.py` successfully: 288 of 288 checks. The original 2 of 4 extraction score was invalidated; a recorded-output correction passed the four tasks without a new model call. | This is a bounded public four-task smoke, not unseen-task generalization or a Baltor-versus-other-harness result. Preserve the failed first grading with the corrected result. |
| [OpenML three-task case study](../../case-studies/openml-cc18-three-task-run.md) | A historical report of three completed tasks. | A read-only recheck during this review ran `benchmarks/openml_cc18/verify.py` and failed with `RunHistoryIntegrityError: saved event log does not match its manifest or digest chain`. Do not present it as currently reverified until the source, verifier and evidence are reconciled. |

No new model, competition submission, customer account or paid service was
used for these local checks. The failing OpenML check is a finding for the
existing benchmark owner, not a reason to erase the historical report.

## The evidence ladder

```text
Operational runtime type
└── Loop
    ├── Operational relationship
    │   ├── Starting
    │   ├── Spawned by
    │   ├── Queried by
    │   ├── Retrieved by
    │   └── Connected from
    ├── Role
    │   ├── Practitioner
    │   ├── Intelligence
    │   └── Solution
    ├── Versioned role profile
    ├── Purpose and domain categories
    ├── Run mode
    │   ├── deterministic
    │   ├── hybrid
    │   └── non-deterministic, with model-led semantic work
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition
    ├── Exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the selected mode permits a model
    └── Run History records
```

A search evaluator can show relevance and abstention. A native-client
exercise can show a digest-bound file was loaded. A task evaluator can show
accepted work. A full-system Loop Engine benchmark additionally needs the
Starting Practitioner, reviewed Intelligence, bounded Spawned Loops,
candidate comparison, executed Solution Canvas, independent evaluator and
verified Run History described in [the repository instructions](../../AGENTS.md).
These levels must remain separate. A provider probe, installed file,
retrieval score or four-task smoke cannot stand in for a full-system
benchmark. A public competitor comparison needs the same task population,
model, harness settings where controlled, budget and evaluator for every arm.

## External populations to source-review

The denominators below belong to the **linked versions**. They are not
combined into one score. Access terms, upstream repository licences,
evaluator versions, data leakage and physical run cost must be checked
again at admission.

| Candidate and exact population | Main evaluator and relevant claim | First use and limit |
|---|---|---|
| [SkillRet](https://github.com/ThakiCloud/SKILLRET), current test split: 4,392 queries, 6,006 skill bodies and 7,187 labels | Ranking relevance and completeness at ten. | Search engine and no-result floor only. The paper used an older split; the collected skill bodies have their own source rights. |
| [Agent Retrieval Bench](https://github.com/eyuansu62/agent-retrieval-bench) | 427 workflow-specific retrieval samples across 25 repositories, including natural no-gold and wrong-repository controls. | Search and abstention, not accepted code changes. Pin evaluator and per-repository licences. |
| [SkillsBench v1.1](https://github.com/benchflow-ai/skillsbench/releases/tag/v1.1), 87 tasks | Task-specific deterministic verifiers with no-skill and curated-skill modes. | Best first external skill-value population after native load is qualified. The older [84-task study](https://www.skillsbench.ai/skillsbench.pdf) is a different population; it reports positive average curated-skill effects but negative transfer on some tasks and an average loss for self-generated skills. |
| [DeepSWE v1.1](https://github.com/datacurve-ai/deep-swe), 113 tasks | A patch is graded with repository tests in a separate pristine environment. | Unfamiliar multi-file coding after source/test leakage controls. It does not by itself prove all Loop Engine intelligence layers. |
| [Terminal-Bench 4.0](https://github.com/harbor-framework/terminal-bench/releases/tag/v4.0.0), 66 tasks | All task tests must pass under its pinned runner. | Broad terminal tasks, with substantial compute. Do not compare its score to the 89-task version 2.1. |
| [SWE-bench Pro V2](https://huggingface.co/datasets/ScaleAI/SWE-bench_Pro), 642 default tasks including a 51-task hard subset | Sanitized repository image and fail-to-pass and pass-to-pass checks. | Later corroboration after an independent validity audit. The original 731-task population remains separately accessible as `v1`; V2 became default on September 22. Source repositories retain their licences. |
| [SWE Atlas Codebase QnA](https://labs.scale.com/leaderboard/sweatlas-qna), 124 tasks | Judge rubric requires every criterion and refuses code changes. | Research and code understanding. Pin judge version, prompt, sampling and cost. |
| [SWE Atlas Test Writing](https://labs.scale.com/leaderboard/sweatlas-tw), 90 tasks | Test manifest, baseline-pass and mutant-fail checks, plus mandatory rubrics. | A close test of Loop Engine's test-first direction; judge and hidden-test access remain controls. |
| [SWE Atlas Refactoring](https://labs.scale.com/leaderboard/sweatlas-refactoring), 70 tasks | No regressions or missing tests, plus mandatory rubric. | Multi-file cleanup after checking evaluator quality and source leakage. |
| [WebArena-Verified](https://github.com/ServiceNow/webarena-verified), 812 tasks including a 258-task hard subset | Network-trace and structural state evaluators over self-hosted websites. | Browser and external-effect qualification; reset site state and accounts between trials. |
| [OSWorld 2.1](https://github.com/xlang-ai/OSWorld-V2), 108 long-horizon workflows | Execution-based computer-use evaluators. | Fresh-step state transfer and recovery under matched virtual machines; gated assets and high setup cost. |
| [Model Context Protocol Atlas](https://labs.scale.com/leaderboard/mcp_atlas), 500 public and 500 private tasks | Multi-server tool use with a model judge. | Tool selection and recovery. The judge, retry behavior and call budget changed in April 2026; older paper numbers are a different protocol. |
| [HiL-Bench](https://labs.scale.com/leaderboard/hil), 200 public and 100 held-out tasks with 1,131 blockers | Asking precision and recall are separate from task Pass@3. | TypeSafe Jev or other decision-method evaluation for when to clarify; question spam and inherited SWE-bench Pro task issues are controls. |
| [DataAgentBench](https://github.com/ucbepic/DataAgentBench), 54 queries across 12 datasets and four databases | Query-specific validators and repeated trials. | Data and cross-database tasks after sealing gold files and qualifying database setup and rights. |
| [MLE-bench](https://github.com/openai/mle-bench), 75 full competitions including the 22-competition Lite subset | Prepared held-out splits and competition-specific graders. | Later long-horizon data science capstone. Competition data have their own terms; new leaderboard submissions were paused in April 2026. |
| [AgentDojo](https://papers.nips.cc/paper_files/paper/2024/file/97091a5177d8dc64b1da8bf3e1f6fb54-Paper-Datasets_and_Benchmarks_Track.pdf), 97 benign user tasks, 27 attack goals and 629 security pairs | Benign utility and unauthorized attack success. | A separate prompt-injection and effect-authority gate, with useful work and rejected effects reported together. |

Benchmark versions are moving targets. [Artificial Analysis version 1.5](https://artificialanalysis.ai/methodology/coding-agents-benchmarking)
uses 113 DeepSWE tasks, 66 Terminal-Bench 4.0 tasks and 124 SWE Atlas
questions, 303 tasks in all; the older repository review describes version
1.4 with 326. [OpenAI's SWE-bench Verified review](https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/)
warns against using that suite as a frontier headline. Its
[SWE-bench Pro audit](https://openai.com/index/separating-signal-from-noise-coding-evaluations/)
estimated roughly 30 percent material problems in the original public
population; Scale's V2 repairs are newly published, not yet independently
settled. [Terminal-Bench version 2.1](https://github.com/harbor-framework/terminal-bench-docs/blob/main/content/blog/terminal-bench-2-1.mdx)
repaired 28 of 89 tasks. Freeze an exact package, task list, images and
evaluator before a number goes on a Baltor page.

## A sequence of comparisons with honest labels

The first study should start with the customer-relevant material path, then
broaden. Each row has a different denominator and conclusion:

| Study | Frozen arms and measure | What it can claim after a pass |
|---|---|---|
| Search floor | Pin SkillRet's current split. Compare lexical, vector, hybrid and a no-result policy on the same queries. Report ranking, no-result errors, latency and index cost. | Only search quality on that split. It cannot establish native loading or useful work. |
| Native material-use pilot | Before results, select a small, balanced subset from SkillsBench v1.1 and publish the selection rule. Repeat each selected task with one pinned harness/model/permission set under no item, raw skill source, approved Baltor item, and exact task-skill oracle arms. | A scoped effect of selected material on independently checked tasks. A proposed sixteen-task, three-repeat pilot is **not** an official 87-task score and needs a declared model budget. |
| Fresh-harness comparison | On the same tasks and selected material, compare a continuing session, a fresh context in the same process, and a cold process with the exact manifest. Count startup, handoff omissions and cache costs. | Evidence about context and process choices, not a general theorem that every task should be split. |
| Complete SkillsBench and coding campaign | After the canonical graph-to-harness path is qualified, run all pinned 87 SkillsBench tasks and a preregistered coding population such as DeepSWE v1.1, each with identical task and evaluator conditions across eligible arms. | Population-specific native and, only when the full required path is exercised, full-system Loop Engine results. |
| Long-horizon and authority campaign | Add a bounded MLE-bench or OpenML task, HiL-Bench clarification, and AgentDojo refusal, with rights and provider authority separately settled. | Distinct long-horizon, decision and safety findings. Do not average them into a single general capability number. |

For a complete Loop Engine claim, follow the full chain in the repository
instructions and [case-study admission rule](../../case-studies/README.md).
Keep each task in the predeclared denominator, including failures and
excluded attempts. Report model and harness versions, physical calls,
provider-reported input, output and cache usage or unknowns, task acceptance,
false acceptance, elapsed time, cost state, artifacts, permissions and the
evaluator. A smaller token count on a failed task is not an optimization.
Public benchmark success alone does not prove success on a new customer's
unseen task; add newly frozen customer-owned tasks with consent and a
separate holdout.

## Five concrete showcase packages

| Proposed exhibit | Input and deliverable | Independent check and risk |
|---|---|---|
| **A selected skill reached a harness, V1** | A frozen small set of code or data tasks in isolated project snapshots. Show the exact approved item, native client version, file digest, changed artifact and Run History. | Same harness/model and task in no-item, raw-source and Baltor arms. A client-reported load and task verifier are separate facts. Include irrelevant, stale, conflicting and unavailable material; model calls require the exact owner authority. |
| **Clean a dataset and reuse its transform, first S-6.37 exhibit** | Source-review one slice of [Clean Me If You Can](https://github.com/D2IP-TUB/Clean-Me-If-You-Can): dirty postal addresses to a corrected table, reusable transform and change log. Keep the clean answers with the evaluator. | Grade cell precision and recall, full-row matches, unchanged clean values, schema preservation and a held-out slice with no per-row model rewrite. Its ground truth has Open Database License terms; freeze actual bytes and row count because its published counts differ between sections. Include ambiguous addresses. |
| **Tickets worked overnight on a local model, V2** | Frozen exported issues and repository snapshots, then consenting customer tickets. Deliver reviewable changes, protected-file check, morning report, saved Run History and interruption recovery. | A real pinned local model on the same machine and budget in native and Baltor arms. Prove no hidden hosted fallback. Test a fixable issue, already-green issue, missing information, forbidden effect, failed verifier, outage and resume. The current [overnight example](../../examples/30_overnight_local_run/README.md) is an offline setup check, not this exhibit. |
| **Competition from task to submission, V2** | One selected competition with frozen terms, data, score direction, code, model artifact and valid submission file. The existing [TrafficFlowBench native plan](../benchmarks/TRAFFICFLOWBENCH-NATIVE-OPENCODE-PLAN.md) is a later capstone. | Local grading is diagnostic. An official [Kaggle submission](https://www.kaggle.com/docs/competitions) and score require separate account, rule and exact external-effect authority. Test identifier order, leakage, file format and deadlines; report public and private scores separately when available. |
| **Research and reusable code across domains, V3** | A pinned [AstaBench](https://github.com/allenai/asta-bench) research or data split and a separate source-reviewed [GitTaskBench](https://github.com/QuantaAlpha/GitTaskBench) code-reuse track. Deliver cited evidence or executable output with source and dependency identities. | Compare absent, raw and selected material using official and independent checks. Gated benchmark data, search or judge keys, public-task contamination and source licences make these later tracks. |

The first data-cleanup showcase is attractive because its output can be
checked without trusting the producing model's narrative, and the second
run can show whether reusable code actually avoided rewriting. That is a
design rationale, not an observed Baltor win. A full Kaggle submission or
overnight local-model solve needs the respective external and model
authority; a dry run must keep its narrower label.

## Public evidence viewer

The demonstration page should first answer: what was attempted, on which
frozen task population, and what passed. A full-width paired comparison
then shows the same task under each arm, with an expandable step record:

```text
Task and independent acceptance
  -> material offered
  -> selected and fetched by exact digest
  -> native client reported the item
  -> item loaded into the model turn
  -> item used in the work
  -> output independently verified or rejected
  -> physical calls, tokens, time, cost and failure details
```

The page must render `unknown` when a stage was not observed. It should not
turn a download into use, a model answer into acceptance, or missing usage
into zero cost. Give failures and excluded tasks the same prominence as
successes. Show machine, model and harness versions, permission and data
boundaries, evaluator, population denominator and limitations above any
headline figure. Link exact run and release evidence. Private customer
inputs remain local unless that customer authorizes an export. The prior
homepage's right-hand illustrative workflow was a poor fit for this depth;
the detailed record belongs on its own demonstration page.

S-6.37 and S-6.56 already own the subdomain and role-page work. The first
build handoff is one evidence-packet contract and one honestly labeled
material-use or data-cleanup run, followed by a live viewer check. A page
without the saved record must withhold its result claim. This research
created no demonstration result.
