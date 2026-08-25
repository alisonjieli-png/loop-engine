# The four intelligence layers

The Intelligence Library gives every loop one searchable view across four
persistent layers. Every search result names the layer that served it.

## Layer map

| Layer | What belongs here | Category groups |
|---|---|---|
| Context Intelligence | Context that can guide work without executing it. | question, method, heuristic, checklist, warning, constraint, persona, example, prompt pattern, output contract, decision schema, evaluation, rubric, source note, failure pattern, other |
| Code Intelligence | Software cards and executable capabilities. | function, file, module, package, repository, template repository, service, dataset-backed system, large framework, worker system, tool, plugin, workflow, notebook, other |
| Previous Run & Solution Intelligence | Saved run history and reusable solution information. | run, solution, decision, failure, repair, measurement, comparison, other |
| User Intelligence | Scoped guidance supplied by a person. | advice, correction, context, source suggestion, package suggestion, priority change, constraint, instruction, approval, veto, other |

The `other` category is deliberate. An item stays visible when its category is
not yet known. The catalog does not invent a precise classification.

## Shared classification

Each item can use the `classification/v1` fields:

```text
layer
item_type
category_group
category
subcategory
domain
scope
lifecycle
source
tags
```

The catalog also lists missing required fields. This makes incomplete
classification measurable instead of hiding it.

Context Intelligence also has a composable hierarchy for roles, work, thinking
styles, response shapes, operating conditions, and evidence. Read
[Context Intelligence ontology](CONTEXT-HIERARCHY.md).

Code Intelligence has reusable templates for small functions, PyPI packages,
GitHub and GitLab repositories, repository templates, tools, skills, notebooks,
workflows, and large systems. Read
[Code Intelligence templates](CODE-INTELLIGENCE-TEMPLATES.md).

Previous Run and Solution Intelligence has its own storage, retrieval,
applicability, and evidence boundaries. Read
[Previous Run and Solution Intelligence](PREVIOUS-RUN-AND-SOLUTION-INTELLIGENCE.md).

User Intelligence has explicit scope, strength, timing, precedence, conflict,
and response rules. Read [User Intelligence](USER-INTELLIGENCE.md).

## Current built-in population

The active population is computed from the package registries. The review
population adds the 1,000-record seed pack, generated candidates, candidate
Loop Templates, and experimental ask strategies.

Candidate records use the `experimental` tier. They are excluded from normal
retrieval. A caller must set `include_candidates=True` to inspect them during
review. Staging a candidate does not make it active.

The Code records are conservative module references. They are not a claim that
every module is an independently registered executable capability.

Previous Run & Solution Intelligence is populated from saved Chronicle runs.
User Intelligence is populated from saved user guidance. Both can be empty on
a fresh installation. The current catalog does not yet load saved
`SolutionLibrary` assets into the third layer.

Run the installed example to see the current counts and missing classifications
instead of relying on a copied number:

```bash
loop-engine --example intelligence-layers
```

## One search across all four layers

`query_intelligence()` sends one need through a search loop. Results include
the source layer, common classification, search score, and a body-free
`LoopRef`.
Filters can narrow the query by fields such as category group, domain, scope,
thinking style, project type, task type, or lifecycle.

The Retrieval Engine provides one interface with lexical, vector, and hybrid
modes. Current selectable built-in backends are `store`, `fts5`, and `lancedb`
for lexical search, plus `hash` and `model2vec` for vector search. This is a
fixed backend set today, not an external retrieval plugin registry.

The human-facing layer key is `context_intelligence`, with the short alias
`context`. The stable wire token remains `string_intelligence` so saved runs,
seed IDs, and existing clients do not break.

See [search the intelligence layers](../../../examples/09_search_the_intelligence_layers/)
for a runnable example.

## Search results are loops

The normal flow is:

```text
search loop
  -> ranked LoopRefs without item bodies
  -> select one reference
  -> materialization loop verifies and loads that item
  -> optional Code execution or explicit model reframe loop
  -> return to the parent loop
```

Context, Code, Previous Run & Solution, and User Intelligence all use this
flow. Read [Intelligence is returned through loops](INTELLIGENCE-AS-LOOPS.md)
for the contracts and examples.

## Runtime Memory is separate

Runtime Memory is the temporary note board for the current run. It is not a
fifth intelligence layer. Notes do not automatically become persistent
intelligence. A later, explicit curation step is required.
