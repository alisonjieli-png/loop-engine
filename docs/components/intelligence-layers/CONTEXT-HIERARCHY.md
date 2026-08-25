# Context Intelligence ontology

Context Intelligence is reusable information that can guide a loop without
executing the work itself. It includes questions, methods, role perspectives,
warnings, checklists, examples, source notes, prompt parts, and output
contracts.

The internal compatibility token is `string_intelligence`. Saved run records
and existing clients may still use that token. Public documentation uses
Context Intelligence.

## The main distinctions

These fields answer different questions. Do not combine them.

| Field | Question it answers | Example |
|---|---|---|
| Context type | What kind of item is this? | question |
| Question family | What is being asked? | missing items |
| Thinking method | How should the problem be examined? | first principles |
| Ask strategy | How should the request be assembled and sent? | direct next action |
| Response shape | What does the answer mean? | ranking |
| List structure | How are repeated items arranged? | top 10 |
| Ordering rule | How are items ordered? | highest value first |
| Serialization format | How is the answer encoded? | JSON |
| Evidence status | What support does the item have? | source backed |
| Lifecycle | Can normal retrieval use it? | candidate |
| Access level | Who may retrieve it? | project |
| Utility status | What happened when it was used? | changed a decision |

A ranking can be returned as JSON, Markdown, CSV, or plain text. Changing the
format does not change the meaning of the ranking.

## Metadata groups

The ontology is grouped so a reader can start with the fields needed for one
task. A Context record does not need every field.

| Group | Fields |
|---|---|
| Identity and governance | record ID, schema version, item version, digest, canonical label, aliases, language, lifecycle, access level, tenant, provenance |
| Artifact meaning | context type, semantic intent, definition, category path |
| Role | role family, job title, job aliases, seniority, responsibilities, stakeholders, decisions, deliverables |
| Work | industry, domain, subdomain, topic, project type, task type, workflow stage |
| Reasoning | speech act, question family, thinking methods, polarity, comparison mode, detail direction |
| Presentation | response shape, list structure, cardinality, ordering rule, serialization, schema, parser, validator, positive example, negative example |
| Operating context | geography, jurisdiction, time horizon, data regime, failure regime, risk, privacy, latency, budget |
| Epistemic state | claim status, evidence status, sources, source type, freshness, confidence, contradictions, abstention conditions |
| Applicability | applies when, contraindications, required inputs, compatibility, incompatibility |
| Retrieval | canonical label, aliases, key phrases, labels, tags, blocking keys, embedding space, lexical hash |
| History | retrieval, selection, outcome, failure, and lifecycle event references |

Job title, industry, domain, geography, and key phrases are open fields. Loop
Engine does not pretend that a package can ship a complete list of every job or
jurisdiction. The domain seed loop adds explicit values when a project needs
them.

Closed fields use one validated vocabulary. Friendly or older spellings are
normalized. For example, `md` becomes `markdown`, `adversarial` becomes
`adversarial_review`, and `core` becomes `registered`.

## One complete example

This record asks a security architect to rank ten authentication approaches.
Its meaning, list structure, and encoding are separate.

```json
{
  "record_id": "context.auth.rank.v1",
  "schema_version": "context_item/v1",
  "context_type": "question",
  "canonical_label": "Rank authentication approaches",
  "aliases": ["compare authentication methods"],
  "role_family": "software_systems",
  "job_title": "security architect",
  "domain": "identity and access management",
  "project_type": "service design",
  "task_type": "choose authentication method",
  "workflow_stage": "planning",
  "speech_act": "rank",
  "question_family": "ranking",
  "thinking_style": "comparison",
  "polarity": "balanced",
  "comparison_mode": "many_to_many",
  "response_shape": "ranking",
  "list_structure": "top_n",
  "cardinality": "exactly 10",
  "ordering_rule": "rank",
  "serialization_format": "json",
  "evidence_status": "source_backed",
  "lifecycle": "candidate",
  "access_level": "project",
  "applicability_status": "conditional",
  "key_phrases": [
    "authentication method",
    "account recovery",
    "phishing resistance"
  ],
  "blocking_keys": ["security", "authentication", "service_design"],
  "relationships": [
    {
      "relation": "validated_by",
      "target_id": "output.authentication_ranking.v1",
      "target_version": "1.0.0",
      "status": "asserted",
      "evidence_refs": [],
      "provenance": "project security review"
    }
  ]
}
```

The record is still a candidate. Detailed metadata does not promote it.

## Question construction

A useful question is assembled from reusable parts:

```text
question pattern
+ role lens
+ one or more thinking methods
+ context policy
+ evidence and uncertainty clauses
+ output contract
+ serialization renderer
+ task slot values
```

The built-in question families include direct questions, best and worst
approaches, first principles, analogy, decomposition, missing items, top
improvements, items to avoid, inversion, adversarial review, premortem,
falsification, evidence needed, comparison, pairwise choice, ranking,
elimination, prerequisites, uncertainty, calibration, causal reasoning,
counterfactuals, novel alternatives, stakeholder views, constraint review,
failure recovery, and cost compression.

Thinking methods are separate. A ranking question can use comparison,
first-principles reasoning, failure-first reasoning, or cost and value
analysis. That creates useful variation without inventing a new question type.

`ContextRecipe` stores references to these parts plus slot values and component
versions. It does not store every rendered combination. This lets the package
address millions of possible questions without adding millions of nearly
identical records.

## Formats and examples

The ontology includes a positive example and usage guidance for each built-in
format.

| Format | Use it for | Avoid it when |
|---|---|---|
| Plain text | A person will read one direct answer. | A program needs exact fields. |
| Markdown | Prose, headings, links, and code must coexist. | A strict machine schema is required. |
| JSON | One complete typed object crosses a boundary. | Records must be appended one at a time. |
| JSON Lines | Independent records are streamed or appended. | Records require one enclosing object. |
| YAML | A person edits nested configuration. | Parser portability or type ambiguity matters. |
| CSV | Rows share one flat column schema. | Values are nested. |
| TSV | Flat text contains many commas. | Fields contain tabs or nested values. |
| HTML | A browser renders the output. | Plain text or data is enough. |
| XML | An existing XML contract requires it. | No XML consumer exists. |
| Python literal | A trusted Python-only tool expects a literal. | The boundary crosses languages or trust domains. |
| Markdown table | A person compares a small fixed table. | Rows are numerous or code consumes them. |
| Mermaid | Labeled nodes and edges explain structure. | Exact numeric comparison is the main point. |

JSON example:

```json
{
  "items": [
    {"name": "passkey", "rank": 1},
    {"name": "one-time code", "rank": 2}
  ]
}
```

The same semantic ranking in Markdown:

```markdown
1. Passkey
2. One-time code
```

The `response_shape` remains `ranking` in both records. Only
`serialization_format` changes.

## Labels, phrases, tags, and search channels

Each retrieval field has one job:

| Field | Use |
|---|---|
| Canonical label | The stable human name. |
| Aliases | Other names people use for the same item. |
| Key phrases | Important multiword expressions, both curated and derived. |
| Labels | Readable cross-cutting descriptors such as `thinking:comparison`. |
| Tags | Low-cardinality filters such as domain, lifecycle, and format. |
| Blocking keys | Cheap exact filters used before a wider search. |
| Lexical hash | A stable similarity key for approximate lexical blocking. |
| Embedding space | The exact model, revision, dimensions, normalization, and distance for a vector. |

New namespaced metadata can be added inside a record. The Retrieval Engine
flattens safe descriptive fields, including nested metadata, into bounded
search text. It also keeps typed facets for hard filters. This allows new
search columns without changing the core storage schema for every experiment.

Vector results from different embedding spaces are never compared. A changed
model or dimension requires a new space and an explicit reindex.

## Relationships and history

Relationships are typed records. Supported relationships include `is_a`,
`part_of`, `variant_of`, `composed_of`, `requires`, `compatible_with`,
`incompatible_with`, `parsed_by`, `validated_by`, `evaluated_by`, `supports`,
`contradicts`, `fails_under`, and `negative_example_of`.

Mutable use counts do not belong inside the Context item. The system should
append separate events when an item is retrieved, selected, rendered, judged,
found harmful, promoted, demoted, quarantined, or retired. Utility can then be
calculated for the relevant role, domain, task, and project cohort. A global
average across unrelated work is not safe.

## Domain seeding

`run_context_seed()` builds a bounded, balanced candidate set across roles,
projects, tasks, and question patterns. The sampler is deterministic and
covers each feasible axis before repeating one. It does not use a model or the
network.

A separate research loop can find job families, primary sources, standards,
datasets, important organizations, and established software for a new domain.
Research output stays at candidate status until a separate review accepts it.

## Code locations

- Ontology and format contracts:
  `loop_engine.static_architecture.context_ontology`
- Classification:
  `loop_engine.static_architecture.context_classification`
- Catalog projection:
  `loop_engine.static_architecture.context_catalog`
- Question forms:
  `loop_engine.strings.question_engine`
- Balanced domain seeding:
  `loop_engine.code_nodes.context_seed`
