# Quarterly retrieval landscape review

Kind: bounded research-task prompt. Scheduling state: not scheduled.

Requested cadence: quarterly. Suggested time: 09:00 America/New_York on
January 1, April 1, July 1, and October 1. The next suggested run is
2026-10-01. This time is a proposal, not a confirmed scheduled task.

This session has no scheduling tool. The prompt can be used in the Scheduled
view of the ChatGPT desktop app with the Loop Engine project, preferably in
an isolated worktree. A local-project task needs the machine and app running.
The web alternative needs accessible uploaded or connected project context;
it cannot directly read this local folder.
[Official scheduled-task guidance](https://learn.chatgpt.com/docs/automations).

Suggested recurrence rule:

```text
RRULE:FREQ=YEARLY;BYMONTH=1,4,7,10;BYMONTHDAY=1;BYHOUR=9;BYMINUTE=0;BYSECOND=0
Timezone: America/New_York
```

## Saved task prompt

Review the current agentic and continuously improving retrieval landscape
for Loop Engine. Read the project's current short instructions and latest
architecture/status documents first. Use dated historical reports only as
baselines, not current authority.

Research primary project repositories, release notes, license files, official
documentation, and original papers. Compare the current versions of simple
lookup, PostgreSQL text and vector search, Elasticsearch/OpenSearch, LightRAG,
HippoRAG, Graphiti, AutoRAG, DSPy/GEPA, relevant evaluation tools, and newly
credible alternatives. Do not assume a project still has the product or
license described in an older review.

Distinguish these capabilities:

- retrieval correction within one request;
- persistent feedback or retrieval-policy learning across requests;
- incremental knowledge or graph ingestion;
- offline prompt, ranking, and pipeline optimization;
- actual model-weight training.

For each material change, record the exact source, date, release or revision,
license and dependency limitations, deployment requirements, supported
interfaces, privacy implications, cost drivers, and evidence quality. Separate
vendor claims, paper results, local observations, and unknowns. Missing
documentation is not proof of absence. Incompatible benchmarks are not a
head-to-head comparison.

Assess fit behind Loop Engine's existing retrieval, artifact, model, harness,
storage, and evaluation boundaries. Preserve the canonical Loop runtime,
current contract versions, runtime compatibility negotiation, explicit effects
and budgets, tenant isolation, and independent promotion. Do not recommend
replacing the runtime with another orchestration framework without a verified
gap and a concrete benefit. Include a simple implementation as a baseline.

Propose only a small ranked set of experiments. Name the expected benefit,
frozen comparison population, success and failure criteria, cost/latency
measurements, adversarial tests, privacy conditions, and rollback path. Treat
noise injection and exploration as experiments, not proof of a global optimum.
The proposer cannot approve its own candidate.

Return a concise summary of what changed, what matters to the first release
or current product, what should be kept, what should be tested, and what should
be deferred. Draft a dated research report and proposed roadmap updates when
the selected environment permits local report writing. Preserve prior reports.
If no material change is supported, say so with the inspected scope.

Do not install dependencies, call paid providers, launch training, create cloud
resources, access private customer traces, modify runtime code, adopt a new
backend, commit, publish, contact organizations, or change production settings.
Those actions need separate authority. Report missing access instead of
inventing results or silently changing the task.
