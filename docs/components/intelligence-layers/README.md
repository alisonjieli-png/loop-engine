# The four intelligence layers

The Intelligence Library gives every loop one searchable view across four
persistent layers. Every search result names the layer that served it.

## Layer map

| Layer | What belongs here | Category groups |
|---|---|---|
| Context Intelligence | Context that can guide work without executing it. | question, method, checklist, template, persona, evaluation, context, instruction, warning, constraint, consideration, other |
| Code Intelligence | Implemented software references and executable capabilities. | transform, analyze, decide, retrieve, execute, validate, report, integrate, other |
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
[Context Intelligence hierarchy](CONTEXT-HIERARCHY.md).

## Current built-in population

At this revision, a clean active catalog contains 134 Context Intelligence
records and 37 Code Intelligence module references. The packaged review
catalog contains 1,337 Context records because it also includes the 1,000-record seed pack,
generated Foundry candidates, candidate Loop Templates, and experimental ask
strategies.

Candidate records use the `experimental` tier. They are excluded from normal
retrieval. A caller must set `include_candidates=True` to inspect them during
review. Staging a candidate does not make it active.

The Code records are conservative module references. They are not a claim that
every module is an independently registered executable capability.

Previous Run & Solution Intelligence is populated from saved Chronicle runs.
User Intelligence is populated from saved user guidance. Both can be empty on
a fresh installation. The current catalog does not yet load saved
`SolutionLibrary` assets into the third layer.

The current packaged records contain all required common classification
fields. Nine Context records and 29 Code module references still fall into the
broad `other` group. Run the installed example to see the current counts
instead of relying on a copied number:

```bash
loop-engine --example intelligence-layers
```

## One search across all four layers

`query_intelligence()` sends one need through the Retrieval Engine. Results
include the source layer, the common classification, and the search score.
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

## Runtime Memory is separate

Runtime Memory is the temporary note board for the current run. It is not a
fifth intelligence layer. Notes do not automatically become persistent
intelligence. A later, explicit curation step is required.
