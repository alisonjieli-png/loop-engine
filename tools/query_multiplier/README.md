# Query multiplier

Kind: tool component, internal local zone. Roadmap step S-6.214 (the knowledge
radar's research). Engine slots `research_query_planner` and
`research_query_executor` in
[`engine_slots.yaml`](../../src/loop_engine/data/engine_slots.yaml) (planned:
these reference engines run from `tools/` today). The command is
[`tools/run_query_multiplier.py`](../run_query_multiplier.py).

The owner, October 5, 2026: "This is a very easy thing to get to, millions, we
just setup a large set of dimensions for search and research like a long string
multiplication for queries like dorks with searching topics, times, geographies,
languages, etc, then we use the list of keywords multiply them together to get
an array of things."

The multiplier does that. A versioned library of dimensions (topics, file
formats, programming and natural languages, geographies, time windows, licences,
source qualifiers) is multiplied, per source, into a stream of distinct queries.
Each query is a probe in that source's own query language. The distinct items
the probes find become candidate source rows for the supply lines. Baltor's
counting rule stays: permutations are fine as queries and never as packages. A
candidate is a lead that its line must still read, decide the licence of and
check.

It starts from the reviewed October 1 planner (`tools/knowledge_radar/query_matrix.py`,
commit `bc29e8e1`) and reuses its normalisation, its sensitive-term screen, its
digest-bound plans and its rule for public GitHub results.

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

A pass is a Starting Practitioner task of the code execution profile that an
operator or the timer starts. It runs deterministically and calls no model (the
Ollama web search engine is a search service, not a model call). Its lanes are
bounded parallel reads inside that one task, not Loop vertices, schedulers or
runtime types. Network reads need the pass's explicit grant; local writes go only
under its private root.

```text
Functional components
├── research_query_planner      edge research_query_plan/v1 -> research_query/v1
│   ├── factorized_multiplier   planner.py (Baltor-native)
│   ├── matrix_pages            knowledge_radar/query_matrix.py (the October 1 planner)
│   └── queue_import            importers.py (earlier research queues as plans)
└── research_query_executor     edge research_query/v1 -> research_query_evidence/v1
    └── one engine per source   executors.py, through transport.py and its host policy
```

## Dimensions as data

[`data/dimensions-v1.json`](data/dimensions-v1.json) is a
`research_dimension_library/v1`. Each dimension names its kind, its source and
licence, the share of its null value and its values (inline, or read by a named
loader from a file pinned by SHA-256, so a changed table changes the plan digest
instead of silently changing queries). Each value has a stable id, a search
phrase, a weight and the attributes an executor renders.

| Dimension | Values | Source and licence |
|---|---|---|
| `sdg_goal`, `sdg_target` | 17, 169 | Goal and target numbers of UN resolution A/RES/71/313 with Baltor's own phrases ([`data/sdg-vocabulary-v1.json`](data/sdg-vocabulary-v1.json), MIT); the phrases are not the official text |
| `onet_occupation`, `onet_task` | 1,015, 15,357 | O*NET 31.0 Database (USDOL/ETA, CC BY 4.0), read from the local copy under the declared data root `onet`; a task phrase is the head noun group of the statement. USDOL/ETA has not approved, endorsed or tested this use |
| `industry` | 34 | The facet vocabulary of `library_facet_tagging` (`data/library_facets.yaml`) |
| `harness_kind`, `step_function` | 18, 10 | The catalogue's `HARNESS_KINDS` and `STEP_FUNCTIONS`, read from source; the loader refuses a phrase table out of sync with them |
| `creative_domain`, `algorithm` | 66, 203 | Baltor's vocabularies (MIT) |
| `file_format` | 79 | Baltor's vocabulary with per-source renderings: GitHub code qualifiers, data.europa.eu format ids, Hugging Face format tags, Openverse extensions, npm keywords |
| `programming_language` | 105 | Names as GitHub's linguist spells them (the `language:` value) |
| `natural_language`, `natural_language_endonym` | 186, 185 | Wikidata ISO 639-1 items with English and native labels (CC0-1.0, [`data/languages-wikidata-v1.json`](data/languages-wikidata-v1.json)) |
| `geography` | 284 | Wikidata UN M49 regions and ISO 3166-1 countries or areas (CC0-1.0, [`data/geography-wikidata-v1.json`](data/geography-wikidata-v1.json)); names are search terms, not jurisdiction or sovereignty claims |
| `time_window` | 76 | Quarters 2008 to 2026 |
| `licence` | 9 | The owner's allowlist, weighted by how common each licence is |
| `source_type` | 14 | The executors |
| qualifiers | 3 to 37 each | GitHub stars, match fields and code sizes; OpenAlex work types; Hugging Face tasks, libraries and modalities; Openverse categories; GBIF dataset types; data.europa.eu themes; arXiv categories |

The CC0 tables are rebuilt by `python -m query_multiplier.reference_tables
--authorize-network-reads` (three SPARQL reads); each records its query, endpoint,
retrieval time and response digest. The CLDR country inventory of October 1
stays private under its Unicode licence, as before.

A rule names a value attribute and the dimensions that must then be null: a 3D,
audio, image, font or CAD format never meets an SDG, O*NET or industry phrase;
a query names a language once; a harness file format skips geography.

## The planner

[`plans/default-v1.json`](plans/default-v1.json) declares 40 products. A product
is one executor, a weight and up to eight dimensions with their null shares and
optional value filters. The default plan's full virtual product is about 85
billion combinations.

Each dimension becomes a virtual list: every value repeated by its weight, the
null value repeated to its declared share, the length padded (with nulls, or with
skipped entries when null is not allowed) until all lengths in the product are
pairwise coprime. Query k takes, in every dimension d, entry
`(a_d * k + b_d) mod n_d`, with `a_d` near the golden ratio of `n_d` and coprime
to it. By the Chinese remainder theorem `k -> (k mod n_1, ..., k mod n_D)` is a
bijection of `[0, n_1 * ... * n_D)`, and the affine step keeps it one, so:

- no combination repeats before the whole product is spent;
- every value of every dimension comes round once in each `n_d` queries, and
  every pair of dimensions once in `n_i * n_j`: every slice is covered early,
  and no dimension exhausts the budget before the others move;
- the cursor is the single number k, saved after each attempt, so a killed pass
  resumes at the query that was in flight.

Values an executor cannot express (a licence it cannot filter by, a format with
no rendering for it, a region where it filters by country) never enter that
product, and the count is reported. A combination that breaks a rule, or renders
to an empty request, is examined and skipped with its reason. Null values stay:
a query with no geography is the global baseline that country queries are
compared with. The cursor binds the product, the library's dimension digests,
the executor and the planner's own code; a changed product starts its own
cursor, and the ledger still prevents repeats. A query executed inside its
refresh period (per source, 14 to 90 days) is skipped; once due it is planned
again and counted as a refresh.

Query identity is the SHA-256 of the executor and its exact rendered request, so
the same request reached from two products, two plans or an imported queue is one
query.

## Executors

| Executor | Host | Query language | Pace and ceiling |
|---|---|---|---|
| `github_repositories` | api.github.com via `gh` | quoted phrases, `license:`, `language:`, `pushed:`/`created:`, `stars:`, `in:`, `is:public archived:false` | 3 s (20 a minute of the shared 30); waits while core REST is under 1,500 or search is low |
| `github_code` | api.github.com via `gh` | `filename:`, `extension:`, `path:`, `language:`, `size:` with a keyword | 15 s (4 a minute of the shared 10) |
| `huggingface_models`, `huggingface_datasets` | huggingface.co | `search`, `filter=license:`, task, library, modality, format and language tags | 2 s each (anonymous window 500 per 5 minutes) |
| `openalex_works` | api.openalex.org | filters (SDG, type, licence, language, institution country, dates) at one credit; `title_and_abstract.search` at ten | 700 credits a day of the anonymous 1,000; holds under 150 left |
| `openverse_images`, `openverse_audio` | api.openverse.org | `q`, `license=cc0,by` only, category, extension | 70 a day each of the anonymous 200; holds under 40 left |
| `gbif_datasets` | api.gbif.org | `q`, `license`, `type`, `publishingCountry` | 3 s |
| `data_europa_datasets` | data.europa.eu | `q` with format, theme and country facets | 3 s |
| `datagov_datasets` | api.gsa.gov | the v4 catalogue with the documented `DEMO_KEY` (catalog.data.gov's CKAN interface answers 404) | 40 a day |
| `arxiv` | export.arxiv.org | `all:"phrase"`, `cat:`, `submittedDate:` | 3.5 s |
| `npm_search` | registry.npmjs.org | text and `keywords:` | 3 s |
| `ollama_web_search` | ollama.com | `POST /api/web_search` with the owner's existing key from the environment, 10 results (endpoint and fields checked against docs.ollama.com on October 5; no published quota, so the ceiling is Baltor's own) | 300 a day, declared within the existing subscription |
| `pypi_search` | pypi.org | none: PyPI has no search interface | unavailable, with that reason |

[`data/hosts-v1.json`](data/hosts-v1.json) refuses 18 hosts before any request,
each with its reason: google.com (and every subdomain, Scholar included), bing.com,
duckduckgo.com, Yahoo, Yandex and Baidu search, openrouter.ai and
artificialanalysis.ai, reddit.com, linkedin.com, x.com and twitter.com,
facebook.com and instagram.com, stackoverflow.com pages, and two piracy hosts.
A request goes only to its executor's one declared host. GitHub is read only
through `gh`, which holds the login; the Ollama key is read from the environment
at send time and never enters a request record, a stored response, the ledger or
a report.

A 429, or a 403 with no allowance left, holds the lane until the provider's reset.
A GitHub 403 with allowance left (its secondary rate limit) holds the lane for its
retry-after, or ten minutes; another source's 401 or 403 holds it for six hours.
A refusal before sending (a missing key, a refused host) stops the lane and leaves
its cursor in place, so no query is spent unsent. Follow-up pages are fetched only
for a query whose first page was at least half new. A GraphQL lane reads, fifty
repositories at a time, the licence GitHub detects for repositories that code
search and web search name without one.

## Evidence

```text
<root>/                       private, 0700, outside the repository (default ~/baltor-library/query-runs)
├── state/ledger.sqlite       cursors, queries, attempts, candidates, origins, usage, holds, imported plans
├── state/status.json         the live status of the current or last pass
└── <YYYY-MM-DD>/raw/<executor>/<qq>/<attempt>.json.gz   one stored response each
    <YYYY-MM-DD>/routed/<line or pool>.jsonl             one row per new candidate
    <YYYY-MM-DD>/run-<id>.json                           the pass report
```

An attempt moves intent, stored, folded. The intent exists before the request
leaves. The response (request without credential, status, rate-limit headers, the
body up to 4 MiB, its SHA-256) is written to a temporary file, flushed and renamed
before the ledger says stored. A query counts as executed only then, and only when
the answer is a 200 the executor could parse. A 403, a 429 or a timeout is stored
as evidence of a failed attempt and executes nothing. Folding reads the stored
file, never the network: a crash between storing and folding is repaired by
folding again, and a response file that reached the disk before the ledger did is
adopted at the next start. An intent with nothing stored is marked
`abandoned_unknown_outcome` and the query stays unexecuted.

Why a ledger and not managed records: one `RecordOperationService` write measured
37.7 ms against 0.08 ms for this ledger on October 5, and one pass writes tens of
thousands of rows. The bounded managed path of the knowledge radar stays for a few
queries a tick.

## Routing

Each result row becomes a candidate with one cross-source identity
(`github:owner/repo`, `github-file:owner/repo/path`, `hf-model:`, `hf-dataset:`,
`doi:` for papers and datasets, including arXiv as `doi:10.48550/arxiv.*`,
`openverse:`, `gbif-dataset:`, `europa:`, `datagov:`, `npm:`, `web:<address>`), so
one item found by two queries or two sources is one candidate with every origin
kept. The licence is kept exactly as reported with the field that reported it,
plus a lead: the SPDX identifier it names when it names exactly one, and whether
that is on the allowlist. A licence family without a version (OpenAlex `cc-by`) is
never read as CC-BY-4.0.

| Route | What goes there |
|---|---|
| `openapi_sources` | OpenAPI, Swagger or AsyncAPI files (proposed rows with repository, path and the commit seen), and repositories tagged as such (paths still needed) |
| `json_schema_sources` | JSON Schema files and repositories tagged as schemas |
| `data_tables` | CSV and TSV files in public repositories (`csv_records`, `tsv_records` rows), and portal datasets with tabular distributions (the line reads GitHub today, so these wait for a portal reader) |
| `function_sources` | Python libraries that say they carry doctests |
| `programs` | Command-line programs (the line still needs the Homebrew formula, release and effects check) |
| pools | `model_pool` and `dataset_pool` (the model and dataset recipe lines do not exist yet), `media_pool`, `paper_pool`, `package_pool`, `harness_file_pool`, `harness_repository_pool`, `python_library_pool`, `code_file_pool`, `repository_pool`, `web_lead_pool` |

A route is a proposal: every line decides the licence again from the licence text
at the pinned commit when it generates.

## Imported queues

`run_query_multiplier.py import` brings earlier research queues in as plans,
never as executions: the October 1 SDG discovery queue
(`planned-searches-final.jsonl`, 148,800 searches), the 1,440-card Public Good
query bank (Drive mirror v6; its eight cards answered by the outside ChatGPT run
are kept as that run's evidence, not as Baltor executions) and the 96,525-string
country and keyword matrix of the social-video workspace
(`~/social_videos/research/sdg-public-good-20261001-v01/generated-v01/queries.jsonl`).
Strings are normalised, kept once across queues with every origin, screened like
every query, and rotated round-robin over their SDG and country keys. On October 5
the three queues gave 246,757 distinct strings over 4,643 keys, with no normalised
duplicate between them. These are web-search strings (`site:` and `filetype:`
operators), so only the web search engine executes them, as one more product within
its daily ceiling of 300: at that rate the queues take about 820 days, and they
stay plans until a larger web search allowance exists.

## Commands

```sh
PYTHONPATH=src:tools python tools/run_query_multiplier.py plan --show 3
PYTHONPATH=src:tools python tools/run_query_multiplier.py run --root ~/baltor-library/query-runs \
  --minutes 40 --authorize-network-reads --authorize-local-writes
PYTHONPATH=src:tools python tools/run_query_multiplier.py import --root ~/baltor-library/query-runs \
  --sdg-planned-searches FILE --public-good-bank FILE --authorize-local-writes
PYTHONPATH=src:tools python tools/run_query_multiplier.py report --root ~/baltor-library/query-runs --with-plan
```

`plan` sends and writes nothing. `run` needs both grants. `--only EXECUTOR`
limits a pass to named lanes. A file `<root>/state/stop` ends a running pass after
its current requests; `<root>/state/pause` makes scheduled passes exit at once.

## Schedule

`python tools/query_multiplier/install_schedule.py --revision <commit>` pins that
commit's `src` and `tools` under `~/baltor-scheduled/query-multiplier-<commit12>/`
(read-only; the radar's schedule pins `~/baltor-scheduled/radar-<commit>` the same
way) and writes the user units `baltor-query-multiplier.service` (oneshot,
`MemoryMax=4G`, `CPUQuota=50%`, idle I/O, running `scheduled-run.sh` of the pinned
checkout) and `baltor-query-multiplier.timer` (hourly at minute 7, 40-minute
passes). Add `--enable` only after one complete manual pass of that pinned
checkout. The pass's live status is `<root>/state/status.json`; `ExecStopPost`
writes systemd's own verdict to `<root>/state/last-unit-result.json` and appends
it to `unit-history.jsonl`, so a pass killed by a timeout or the memory cap still
leaves a record.

## The October 1 review, finding by finding

| Finding | Where it stands |
|---|---|
| QR-01 to QR-07 (aliases, plan membership, private results, sensitive terms, engine binding, parser-change holds, saved refusals) | Resolved in `bc29e8e1`; the multiplier reuses the same screen, digests and public-result rule |
| An orphaned attempt intent was left to an operator | `query_runs.reconcile_interrupted` closes it as `abandoned_before_dispatch` and requeues its work; the multiplier marks its own orphans `abandoned_unknown_outcome` and adopts any response that reached the disk |
| An interrupted origin fold was left to an operator | The next writing tick folds the saved result without a second read; the multiplier folds from the stored response file |
| The queued lookup and hold windows are capped at 1,000 records | Kept for the bounded managed path; the multiplier's ledger has no such window |
| Language facets were English names only | `natural_language_endonym` carries 185 native names from Wikidata (CC0) |
| Country conjunctions might miss global code; yield never measured | Every product keeps a null geography share, so global baseline queries run beside country ones, and each pass reports yield per executor and its decay |

## Limits

- Candidates are leads. Licences are as reported; the lines decide them.
- arXiv's interface reports no licence, and OpenAlex reports `cc-by` without a
  version, so neither counts as allowlisted until a line reads the licence.
- PyPI has no search interface. data.gov is reached only through its public
  demonstration key, 40 requests a day.
- Some products combine values that rarely meet (a niche licence with a niche
  language); their empty results are measured and lower the measured yield, not
  the plan's correctness. Weights move requests toward common licences and
  languages; a learning allocation over measured yield is not built yet.
- Shared allowances (GitHub search, OpenAlex and Openverse anonymous budgets)
  are also used by other agents; the lanes wait or hold instead of exceeding them.
