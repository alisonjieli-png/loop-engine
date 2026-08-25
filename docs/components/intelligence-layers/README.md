# The four intelligence layers

The Intelligence Library gives every loop one searchable view across four
persistent layers. Every search result names the layer that served it.

## Intelligence uses query and retrieval relationships

The four layers classify stored intelligence. The Intelligence role classifies
the work a Loop performs with that intelligence. These are different axes.

```text
Starting Practitioner
└── queries an Intelligence Query Loop
    ├── role profile: intelligence.search
    └── retrieves Intelligence Item Loops
        ├── intelligence.materialize
        ├── intelligence.code.invoke
        ├── intelligence.runtime_history_solution.replay
        └── intelligence.user_feedback.interpret
```

The public operation selectors resolve to registered profiles:

- `intelligence.search` searches selected layers and returns references.
- `intelligence.materialize` verifies and loads one selected reference.
- `intelligence.code.invoke` invokes selected Code Intelligence.
- `intelligence.runtime_history_solution.replay` replays selected Runtime History.
- `intelligence.user_feedback.interpret` interprets selected User Feedback.

Short selectors such as `intelligence.invoke` resolve to these exact registered
profiles. Saved definitions record the exact profile ID and version, not the
short selector.

An independent intelligence task may use a Starting Intelligence Loop. In the
ordinary Practitioner flow, the Practitioner queries an Intelligence Query
Loop. That Query Loop retrieves Intelligence Item Loops and returns typed
references or material. Query and retrieval do not change role, profile, or
selected mode into a spawning relationship.

## Layer map

| Layer | What belongs here | Category groups |
|---|---|---|
| Context Intelligence | Context that can guide work without executing it. | question, method, heuristic, checklist, warning, constraint, persona, example, prompt pattern, output contract, decision schema, evaluation, rubric, source note, failure pattern, other |
| Code Intelligence | Software cards and executable capabilities. | function, file, module, package, repository, template repository, service, dataset-backed system, large framework, worker system, tool, plugin, workflow, notebook, other |
| Runtime History and Solution Intelligence | Saved run history and reusable solution information. | run, solution, decision, failure, repair, measurement, comparison, other |
| User Feedback Intelligence | Scoped guidance supplied by a person. | advice, correction, context, source suggestion, package suggestion, priority change, constraint, instruction, approval, veto, other |

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

Runtime History and Solution Intelligence has its own storage, retrieval,
applicability, and evidence boundaries. Read
[Runtime History and Solution Intelligence](RUNTIME-HISTORY-AND-SOLUTION-INTELLIGENCE.md).

User Feedback Intelligence has explicit scope, strength, timing, precedence, conflict,
and response rules. Read [User Feedback Intelligence](USER-FEEDBACK-INTELLIGENCE.md).

## Current built-in population

The active population is computed from the package registries. The review
population adds the 1,000-record seed pack, generated candidates, candidate
Loop Templates, and experimental ask strategies.

Candidate records use the `experimental` tier. They are excluded from normal
retrieval. A caller must set `include_candidates=True` to inspect them during
review. Staging a candidate does not make it active.

The Code records are conservative module references. They are not a claim that
every module is an independently registered executable capability.

Runtime History and Solution Intelligence is populated from saved Run History records.
User Feedback Intelligence is populated from saved user guidance. Both can be empty on
a fresh installation. The current catalog does not yet load saved
`SolutionLibrary` assets into the third layer.

Run the installed example to see the current counts and missing classifications
instead of relying on a copied number:

```bash
loop-engine --example intelligence-layers
```

## One search across all four layers

`query_intelligence()` sends one need through an `intelligence.search` Loop.
Results include
the source layer, common classification, search score, and a body-free
`LoopRef`.
Filters can narrow the query by fields such as category group, domain, scope,
thinking style, project type, task type, or lifecycle.

The Retrieval Engine provides one interface with lexical, vector, and hybrid
modes. Current selectable built-in backends are `store`, `fts5`, and `lancedb`
for lexical search, plus `hash` and `model2vec` for vector search. This is a
fixed backend set today, not an external retrieval plugin registry.

See [search the intelligence layers](../../../examples/09_search_the_intelligence_layers/)
for a runnable example.

## Search results are loops

The normal flow is:

```text
Intelligence search Loop
  -> Practitioner queries an Intelligence Query Loop
  -> Query Loop returns ranked LoopRefs without item bodies
  -> Query Loop retrieves the selected Intelligence Item Loop
  -> materialization verifies and loads that item
  -> optional Code invocation or explicit model reframe Loop
  -> typed reference or material returns to the Practitioner
```

Context Intelligence, Code Intelligence, Runtime History and Solution
Intelligence, and User Feedback Intelligence all use this flow. Read
[Intelligence is returned through loops](INTELLIGENCE-AS-LOOPS.md) for the
contracts and examples.

## Runtime Memory is separate

Runtime Memory is the temporary note board for the current run. It is not a
fifth intelligence layer. Notes do not automatically become persistent
intelligence. A later, explicit curation step is required.
