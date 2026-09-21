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

Accepted generated code can enter the governed candidate, qualification,
promotion, projection, and future-use circuit. Read the
[Reusable Capability Flywheel](REUSABLE-CAPABILITY-FLYWHEEL.md).

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

### Known contradiction: two manifests disagree about the seed pack

Recorded on September 20, 2026. The data was not changed. Two manifests
describe the same 1,000-record seed pack, with the same content digest
`400229d47342e0593fb75d14e210ca04d47407411c8682e0f37c5acdc16e7b36`, and they
state different lifecycle states for it.

| File | What it states |
|---|---|
| `src/loop_engine/intelligence/context/core/records/part-00000.manifest.json` | The manifest of the pack. It says `"status": "candidate"`, `"promotion": "evidence_gate_only"` and `"automatic_preference": "forbidden"`. |
| `src/loop_engine/intelligence/context/core/manifest.yaml` | The catalogue manifest of the folder. It lists the same payload as `core.context.seed_corpus`, version `2.0.0`, with `lifecycle: registered`. |

Current behavior follows the manifest of the pack. `load_seed_pack()` in
`src/loop_engine/code_nodes/string_foundry.py` checks the digest and refuses
the pack when any record has a maturity other than `candidate`. The self-test
check `seed_pack_1000_records_20x50_all_candidate` protects that rule.
`seed_pack_store_records()` gives every record the `experimental` tier, so
normal retrieval excludes the pack. A caller sees it only with
`include_candidates=True`.

The catalogue record model in `src/loop_engine/ontology/records.py` orders the
lifecycle states as draft, candidate, validated, registered, preferred,
deprecated and retired. It treats only draft, candidate and validated as
candidate states. A `registered` entry therefore claims that an independent
approval happened. No approval record exists for the seed pack. Imported and
generated intelligence stays candidate-only until an independent process
approves it, so the catalogue manifest is the statement that is wrong.

The file that must be corrected is
`src/loop_engine/intelligence/context/core/manifest.yaml`. The `lifecycle` of
`core.context.seed_corpus` must say `candidate`. Two dependent files must
change in the same change:

- `src/loop_engine/ontology/index.json` is generated from the manifests and
  copies `registered` for this entry. A check fails when it is stale, so it
  must be regenerated.
- `src/loop_engine/intelligence/context/core/README.md` says that records in
  that folder must declare `registered` or a later state. The owner of that
  path must either amend the folder rule so that it admits a candidate pack
  whose bytes ship with the package, or move the catalogue entry to a folder
  whose contract admits candidates.

The pack data and the manifest of the pack do not need to change. This
document changes none of these files. Until the correction is made, do not
cite the catalogue manifest as evidence that the seed pack was approved, and
do not publish seed pack records to the hosted catalogue as approved material.

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

How a request is compared with what an item declares, and how well the
resulting order holds up against measured requests, is recorded in
[catalogue search quality](SEARCH-QUALITY.md). The matching mode is a typed
field of `core.harness_intelligence_search`, not a default buried in a call.

## Runtime Memory is separate

Runtime Memory is the temporary note board for the current run. It is not a
fifth intelligence layer. Notes do not automatically become persistent
intelligence. A later, explicit curation step is required.

## Expand intelligence coverage and use

The design should support more useful questions, methods, examples,
counterexamples, executable capabilities, prior outcomes, and human guidance
within these four layers. More stored material is not automatically better,
but reducing context is not the universal objective either. Compare what was
retrieved, loaded, applied, and useful on the actual assignment.

Read [flexible cognitive and action composition](../../architecture/FLEXIBLE-COGNITIVE-AND-ACTION-COMPOSITION.md)
and [configuration grid search](../../guides/configuration-grid-search-and-optimization.md)
for expansion, source combinations, prompt portfolios, and contribution tests.
