# Context Intelligence hierarchy

Context Intelligence is reusable information that can guide a loop without
executing the work itself. It includes questions, methods, professional roles,
constraints, checks, examples, prompt parts, output shapes, and source-backed
domain context.

The internal compatibility token remains `string_intelligence`. Existing
Chronicles, content addresses, seed IDs, and API clients continue to use that
token. Human-facing surfaces use Context Intelligence.

## Composable axes

The hierarchy uses several axes instead of one large folder tree. A single
Context item can belong to one job role, one project type, one thinking style,
and one workflow stage at the same time.

| Axis | Examples |
|---|---|
| Context type | question, method, checklist, template, persona, evaluation, instruction, warning, constraint, consideration |
| Role context | role family, job title, seniority, responsibility, stakeholder |
| Work context | industry, domain, project type, task type, deliverable, workflow stage |
| Thinking style | first principles, analogy, outline to detail, inversion, gap analysis, adversarial review, comparison, prioritization, verification |
| Response shape | proposals, ranking, score, elimination, verdict, comparison, decomposition, list, free text |
| Operating context | geography, jurisdiction, timeframe, data regime, failure regime, constraints |
| Evidence context | source type, source references, claim status, freshness, provenance |
| Lifecycle | candidate, registered, implemented, committed, retired |

Do not materialize every possible combination. Store reusable parts and create
the needed combination for a task.

## Implemented `context_hierarchy/v1`

Every classified Context result can currently include:

```text
context_type
industry
domain
subdomain
topic
role_family
job_role
seniority
project_type
task_type
deliverable
workflow_stage
thinking_style
response_shape
geography
jurisdiction
time_horizon
source_policy
source_refs
claim_status
possible_code_target
scope
lifecycle
source
digest
tags
```

Missing values stay empty. The classifier does not invent a job, source, or
domain to make the record appear complete.

## Current reusable dimensions

The bundled generation banks currently include 54 job roles, 40 scientists,
25 authors and thinkers, 35 geographies, 20 timeframes, 40 situations, 27
thinking operators, 30 targets, 10 contrasts, 40 domains, 10 data regimes,
and 15 failure regimes.

The question engine provides reusable forms for best and worst approaches,
ranking, analogy, elimination, verification, novelty, comparison, premortem,
decomposition, missing items, first principles, outline to detail, top
improvements, top items to avoid, best practices, and assumption inversion.

These are seed dimensions, not a complete occupation or industry taxonomy.
Only a small set of jobs has deeply job-specific generated content today.

## Domain Context Packs

A reviewed Context Pack can bind the applicable roles, projects, tasks,
questions, methods, operating conditions, and sources for one profession,
industry, project family, or organization.

A domain seed remains a candidate pack until independent review accepts it.
Generation does not make a claim true, and retrieval does not make a candidate
active.
