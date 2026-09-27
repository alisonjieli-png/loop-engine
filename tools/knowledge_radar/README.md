# Knowledge radar

Kind: tool component and architecture contract, internal local zone. Roadmap
step S-6.214 (daily distillations) and the owner's knowledge radar direction
of September 27, 2026. The command is
[`tools/build_knowledge_radar.py`](../build_knowledge_radar.py). The research
record is
[`docs/research/KNOWLEDGE-RADAR-2026-09-27.md`](../../docs/research/KNOWLEDGE-RADAR-2026-09-27.md).

The radar answers recurring engineering questions once, for everyone, and
serves each answer as dated files a coding harness can load: a decision card
with ranked, source-linked evidence, a data file with its schema, a small
decision helper over that data, or a tool that fetches a fact too volatile
to store. Every answer names the day it was checked and the day it stops
being current. The radar approves nothing, serves nothing and publishes
nothing: its packages are candidates for the existing independent review and
catalogue release path.

## Runtime classification

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

A radar run is a Starting Practitioner task of the code execution profile
that an operator or a timer starts with the command above. It runs
deterministically and makes no model call. Its source engines, the brief
generator, the planner and the vetting checks are adapters and records the
run uses: none is a graph vertex, a role, a mode or a runtime type. Reads of
the network need the run's explicit grant and each engine's source contract.

## The owner's delivery rule, as typed fields

Each question in [`questions-v1.json`](questions-v1.json) declares its
research cost (engineer minutes and distinct sources), the volatility of its
facts, its delivery kinds and its refresh cadence. The reader refuses a
question whose delivery breaks the rule:

```text
delivery rule (records.rule_findings)
├── facts change faster than the refresh  -> a tool that fetches them; nothing stored may carry them
├── research above the threshold          -> a brief or a data file, done once for everyone
├── research at or below the threshold    -> no stored file; at most a tool
└── a helper or a tool                    -> names its asset; a helper reads a data file
```

The threshold is the owner's: more than five engineer minutes or more than
one website. A sensitive question (legal, security or financial) carries the
review requirement of two independent model families with a source on every
claim.

## Records

```text
knowledge_radar_question_registry/v1   the declared questions, the rule and the planner policy
knowledge_radar_question/v1            audience, constraints, baseline, acceptable evidence,
                                       intended output, research cost, volatility, delivery,
                                       refresh, sensitivity, questions to ask again, negative knowledge
knowledge_radar_source_contracts/v1    one ingestion contract per engine: access method, hosts,
                                       permitted uses, what is never used, attribution, terms,
                                       pacing, request ceiling, failure policy
knowledge_radar_observation/v1         one claim: key, common origin, title, link, facts, licence,
                                       event_at, source_published_at, observed_at, effective_from,
                                       effective_until, last_verified_at, review_after
knowledge_radar_source_check/v1        one binding's check outcome: checked with no relevant change,
                                       checked with a material change, partially checked, could not
                                       check, source disappeared or access changed
knowledge_radar_plan/v1                the questions a run selected (first run, overdue, changed
                                       source, demand, exploration) and a stable work identity each
knowledge_radar_brief/v1               the decision card and its evidence, or a notice that no
                                       currently validated recommendation exists
knowledge_radar_table/v1               a question's current claims as one typed table, with a schema
knowledge_radar_vetting/v1             six separate vetting dimensions per package
knowledge_radar_index/v1               every declared question with its honest answer state
```

A failed read is never recorded as "no change": the previous successful
check stays the baseline, its claims keep their old dates, and the brief
lists the failure under what is not established. Reading an old dated claim
again never renews it: its review date counts from the claim's own date.

## Engines behind one source edge

`knowledge_radar_source/v1` has seventeen Baltor-native engines. Local
engines read files: `collector_state` (the source discovery collector's
latest private exports, read only), `model_directory`,
`endpoint_directory`, `mcp_directory` (the directory data this repository
packages for its public pages) and `curated_seed` (official links a person
declared, unverified until a link check resolves them). Network engines
make bounded read-only requests through the library ingestion transport,
budget and request log: `github_search`, `github_advisories`,
`github_releases` and `owner_directory` through the gh login with the
radar's own read-only allow list, and `huggingface_models`,
`huggingface_new_models`, `arxiv_listing`, `openalex_works`,
`endoflife_calendar`, `federal_register`, `models_dev_catalogue` (models.dev,
MIT) and `litellm_prices` (the LiteLLM price map, MIT) over HTTPS GET. No
engine reads OpenRouter or Artificial Analysis by script: the contracts file
names both as hosts that are never read, a contract that names one is
refused, and both appear in briefs only as attributed links a customer
opens. The model directory's LMArena text scores (CC BY 4.0) are shown with
their credit, which every brief carries for each source that gave it claims.

Each source contract says whether the source's facts may be stored in a
served file (`republication`) and which upstream values its engine drops
(`excluded_upstreams`, `excluded_publishers`). A run refuses to start when a
question that stores an answer binds a live-lookup-only source, and the
directory engines drop every value the packaged directories took from
OpenRouter or that Artificial Analysis published. The reason is decision 7
of `docs/research/SHARED-RESEARCH-SERVICE-LANDSCAPE-2026-09-27.md`. Source prose that an answer carries
(descriptions, abstracts, release notes, advisory summaries) is kept only
as hashed eight-word runs, so the vetting stage can refuse a brief that
repeats it. A title that tries to steer a reader is excluded, never
rewritten.

## Hourly model watch

[`tools/watch_model_releases.py`](../watch_model_releases.py) checks the
bindings of the hourly question `models_new_releases` once: models.dev, the
newest Hugging Face repositories of major labs and the LiteLLM price map. It
sends back the validators of each source's last complete read, so an
unchanged source answers 304, which is the only "no change" that needs no
body. A failed read is "could not check" and changes nothing; a partial read
never counts a removal. On a material change it writes a change record under
`<library>/model-watch/<day>/` and marks every question that reads that
source; the daily planner answers those questions before they are due. It
never reads a model card and makes no model call.

```text
PYTHONPATH=src:tools python tools/watch_model_releases.py \
  --library /home/username/baltor-library/radar --authorize-network-reads --authorize-local-writes
```

## Stages of one day

```text
plan -> collect -> links -> diff -> brief -> package -> vet -> feed -> record
```

Each stage writes its files and a done marker in the day folder. A second
process for the same day answers `already_running`; a finished day answers
`already_complete` and writes nothing; an interrupted day resumes at the
first unfinished stage and never reads a stored source answer again. Only
the last stage writes the shared state under `<library>/state`: the last
successful check of each binding and four freshness times (last attempted
retrieval, last successful retrieval, last material change, last successful
evaluation).

## Deliverables in the existing package format

```text
brief (and data file)   skill package: SKILL.md, references/brief.json, references/provenance.json,
                        contracts/brief.schema.json, optional table and table schema, LICENSE
decision helper         tool package: the asset's files plus the day's table at its data path
tool                    tool package: the asset's files, with typed input and output contracts,
                        a known-wrong test and no stored value
```

Packages pass through the existing preparation factory
(`tools/prepare_harness_candidates.py`), which pins every cited repository
file to the committed revision. The assets live in [`assets/`](assets/).

## Vetting dimensions

`source_identity_checked`, `claim_supported_by_cited_evidence`,
`implementation_inspected` (the existing native prechecks),
`implementation_tested_or_reproduced` (the package's own tests in a
bubblewrap sandbox with no network, including a known-wrong case),
`compatibility_tested` and `publication_approved_for_scope`. The last two
are never done by this component.

## Command

```text
PYTHONPATH=src:tools python tools/build_knowledge_radar.py \
  --library /home/username/baltor-library/radar --as-of 2026-09-27 \
  --collector-state /home/username/baltor-private/source-discovery-2026-09-26/state \
  --authorize-network-reads --authorize-local-writes
```

Without `--authorize-local-writes` it prints the plan that a run would make
now, read from the library's state, with the reason for each selected
question, and writes nothing. `--only` limits a run
to named questions, `--skip-link-checks` and `--skip-sandbox-tests` leave
those dimensions not done, and `--stop-after` stops after a stage.
`--rerun` answers every planned question again, for example after a fix;
give it a new `--output` folder so the earlier attempt stays beside it. The
checks are [`tools/test_knowledge_radar.py`](../test_knowledge_radar.py),
[`tools/test_knowledge_radar_pipeline.py`](../test_knowledge_radar_pipeline.py),
[`tools/test_knowledge_radar_assets.py`](../test_knowledge_radar_assets.py)
and [`tools/test_knowledge_radar_model_watch.py`](../test_knowledge_radar_model_watch.py).

## What the first version implements

| Owner direction of September 27, 2026 | First version |
|---|---|
| Research cost, volatility, delivery and refresh per question, with the rule | Implemented: typed fields; the reader refuses a delivery that breaks the rule; known-wrong checks and a removed-guard control |
| Deliverable kinds | Implemented: skill packages with the brief and its metadata, typed tables with schemas, two decision helpers (`choose_model`, `check_support_window`) and four tools (`check_service_status`, `query_package_advisories`, `fetch_reference_rates`, `lookup_legal_entity`) |
| A wider question list | Implemented: 65 questions, 55 with a source and 10 declared gaps with reasons, including retrieval methods with the STAIR paper as a lead |
| Hourly checks for model releases | Implemented: the hourly question, the change-detecting watch with validators sent back over three openly licensed sources, and invalidation of the dependent questions; the schedule is proposed, not installed |
| First demonstration: small models for structured extraction | Implemented: the question `models_structured_extraction` and the `choose_model` helper 2.0.0 over openly licensed data; the measurement and release are the demonstration's own steps |
| Stored facts only from openly licensed sources | Implemented: no engine for OpenRouter or Artificial Analysis, a refused contract for any host that must not be read by script, the republication field and run guard, the directory engines' exclusions, and credits in every brief, each with a known-wrong check |
| Vetting before the context layer | Implemented: native prechecks, seed link checks, schema validation, copied-text refusal, sandbox tests with known-wrong cases, the stricter review requirement on sensitive questions. Independent review stays with the existing panel |
| Question registry and planner | Implemented |
| Check outcomes, time fields, "no currently validated recommendation" | Implemented and tested |
| Separate vetting dimensions | Implemented |
| Common origin and ingestion contracts | Implemented |
| Negative knowledge | Implemented in every brief |
| Cheapest model per thinking per task | The proxy helper is implemented; the measured frontier is design |
| Suggested sources | Wired: arXiv, OpenAlex, Hugging Face Hub, models.dev (through the model directory), GitHub releases, the official protocol server registry (through the collector and the directory), OSV and GLEIF (as tools), FederalRegister.gov. Not wired: eCFR, SEC EDGAR, SAM.gov, USAspending |
| Durable stages, journals, stable work identities, idempotent publication | Implemented; DBOS and Temporal remain candidate engines |
| Readiness demonstrations | Tested: resume, duplicate trigger, steering source, expired claim. Revocation uses the existing catalogue withdrawal path and is not exercised here |
| Repeat only invalidated work | The planner re-runs only overdue or changed questions and the run writes invalidation edges; running only the affected work from the edges is design |
| Reuse at five levels | Source answers, claims, implementations and scoped, expiring failure records are written; comparisons under an evaluation contract are design |
| Four freshness times | Kept per binding in the shared state. The hourly watch sends conditional requests; the daily run still reads each source in full |
| Honest answer states | Implemented in the index and feeds |
| Three data layers and request coalescing | The radar writes the public shared layer only; the work identity is implemented, attaching a second request to a running job is design |

## Design choices and their reasons

- The rule's threshold is five minutes or more than one source, from the owner's words.
- Briefs are skills, so a harness loads one when a step needs it instead of at every start. The skill
  name is stable per question, so a newer brief replaces an older one in a harness folder.
- A brief declares only `reads_fs`. It asks for no network, and it tells the harness to re-check a link
  only under the step's own network authority.
- The producer family is anthropic, because Claude wrote the generator and the assets, so reviewers come
  from another family.
- The hourly watch reads models.dev, Hugging Face and the LiteLLM price map. OpenRouter's terms forbid
  reading it by script, so no engine reads it.
- The cheapest model per unit of thinking stays a declared gap until it is measured: a listed price divided
  by a published index is neither allowed under the terms nor a measurement of thinking on a task.
- High confidence needs two independent source engines; one source gives at most medium.
- Seeds hold names and links only; the reader refuses a seed name that holds a number with a unit.
- Public-service files are not edited by this component; the routes are designed in the research record.

## Limits

- No model reads a source: briefs list, rank and date; they do not summarise.
- Link checks cover seed links; engine links come from each source's own answer.
- The planner reads local change times; network sources are re-read on their cadence.
- arXiv's edge refuses some automated reads with 406 at busy times; the engine waits and tries once more,
  then records "could not check".
- Serving, freshness in search, withdrawal of superseded briefs and a schedule are designed in the research record and not installed here.
