# Contracts as harness intelligence: 1,000 research candidates

Date: September 23, 2026. Status: research and original package ideas. This work
creates no approved, served or natively loaded package. It changes no runtime,
deployment, credential, provider configuration or catalogue approval.

## What is ready

[contracts-ranked.jsonl](contracts-ranked.jsonl) contains **1,000 distinct
candidate logical identities**: 600 document/configuration schema families and
400 service API families. These are real catalogue entries selected for further
research. They are not 1,000 independently reviewed drop-in packages. Semantic
near-duplicate review and current upstream compatibility remain open.

[contracts-counts.json](contracts-counts.json) binds the inputs, script and output.
The first counts report and its counterexample remain beside the corrected report.
The initial acquisition used 920 budget admissions, producing 919 recorded HTTP
observations; one catalogue URL contained an unescaped space and failed before
the transport could log an HTTP observation. An explicit same-origin URL repair
then made one public request: the percent-encoded path returned HTTP 200 and a
parseable Swagger 2.0 document. The current totals are **921 admissions and 920
recorded HTTP observations**. The raw catalogue URL, predecessor row, and
normalization evidence remain preserved in [the repair report](contracts-url-repair-2.json).

| Selected population observation | Count |
|---|---:|
| Exact document bytes fetched and parsed as JSON | 891 |
| Fetch failure: four 404s and eighteen over the 1 MiB limit | 22 |
| Host or URL outside the qualified acquisition policy | 80 |
| Fetched but JSON parse refused | 6 |
| Unresolved malformed source URLs after explicit same-origin repair | 0 |
| Metadata-only replacement for an exact body alias | 1 |
| Verified redistribution licences | 0 |
| Approved / native-loaded packages | 0 / 0 |

Five parse refusals are YAML documents outside this JSON-only research reader;
they are not evidence that the upstream schemas are invalid. The sixth has a
duplicate JSON key. The run and its one-request URL successor fetched 898 HTTP-200 documents before
deduplication: 892 parsed, with one exact body alias removed from the selected count. It made
no remote-reference requests and called none of the APIs described by the files.

Raw bodies and request logs remain outside the repository at
`/home/username/.le-codex-research-cache/four-catalogues-20260923/contracts-20260923-1`.
The single corrected-URL response is in the adjacent
`contracts-url-repair-20260923-2` cache run.
The existing `HttpsGetTransport`, `RequestBudget`, `RequestLog` and `Quarantine`
implement the network and storage boundaries. Eight lanes each have a 150-request
ceiling; the total ceiling is 1,200. Each document is limited to 1 MiB, with a
12-second transport timeout. The acquisition was launched with an empty
environment except for a system executable path. No secrets were supplied.

## Verified input population

The existing cached catalogues were checked against their exact byte lengths and
SHA-256 before parsing. No duplicate catalogue download was made.

| Source | Observed population | Snapshot SHA-256 |
|---|---:|---|
| [SchemaStore catalogue](https://www.schemastore.org/api/json/catalog.json) | 1,474 entries; 1,473 unique primary URLs | `75edb7d0bab76c28a7e51dd4c0de1ba7b6a1202f99f11695d2109a79e8d16991` |
| [APIs.guru list](https://api.apis.guru/v2/list.json) | 2,529 API entries; 3,992 stored versions | `dfac835d2d1f13dfdb82723d72be1acf567df53c1b710bf6d68e28b795696e66` |

SchemaStore exposes 1,102 additional version links across 167 entries. They were
not counted as additional contracts. `package.json` and `package.yaml` share a
primary schema URL. APIs.guru's preferred metadata contains 886 `info.license`
objects and 1,643 without one. All preferred `updated` timestamps in this snapshot
are in 2016–2023. That does not prove an API is dead; it means this snapshot cannot
prove current endpoint compatibility. Azure, Google and AWS together account for
1,205 entries before consolidation and selection.

The metadata is imperfect. For example, the categories for `threatjammer.com`
are eight single characters spelling a category name. The collector records
unrecognized categories rather than silently repairing them into evidence.

## Keep the contract kinds separate

| Kind | What it describes | Useful harness package | What it does not prove |
|---|---|---|---|
| JSON Schema | Constraints and annotations for JSON instances | Pinned schema, fixtures, qualified validator invocation and task-specific guidance | Runtime behavior, authority, or endpoint availability |
| OpenAPI | HTTP operations, parameters, media types, responses and security descriptions | A selected operation family, exact source, serialization tests and a separately authorized adapter | Correct credentials, safe effects, or idempotency |
| MCP tool contract | Tool input schema and optional structured output schema within MCP messages | Input/output tests plus an adapter and negotiated client/server binding | Truth of tool annotations or arbitrary native harness activation |
| AsyncAPI | Application operations, channels, messages and protocol bindings | Event fixtures, correlation/ordering checks and an explicitly selected transport adapter | Exactly-once delivery or universal ordering |
| Arazzo | API call sequences with dependencies and success criteria | A bounded workflow description, stubbed fixtures and checked task outcomes | Permission to execute the described workflow |
| Baltor component contract | Versioned input/output, effects, budgets and lifecycle at an existing typed edge | Original fixtures and materialization adapters over the canonical record | A new runtime type or another source of authority |

OpenAPI 3.1 uses a JSON Schema 2020-12-based Schema Object; older OpenAPI 3.0
documents use different schema rules. Preserve the declared dialect and test the
chosen parser instead of relabelling old schemas as current. The snapshot contains
1,008 preferred Swagger 2.0 documents and only 35 preferred OpenAPI 3.1.0 documents.
The standards consulted are pinned examples, not a claim that 3.1.1 is the latest
OpenAPI release. [OpenAPI 3.1.1](https://spec.openapis.org/oas/v3.1.1.html#schema-object),
[OpenAPI 3.0.3](https://spec.openapis.org/oas/v3.0.3.html#schema-object).

MCP 2025-11-25 specifies JSON Schema inputs, optional output schemas and validation
of structured results. It also says tool annotations are untrusted unless supplied
by trusted servers. Package metadata must not turn a `readOnlyHint` or a schema
description into permission. [MCP tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools).

AsyncAPI 3.0.0 distinguishes implemented application operations from reusable
components. Arazzo 1.0.1 describes API workflows. Neither requires treating every
reusable component or step as a separately counted package.
[AsyncAPI 3.0.0](https://www.asyncapi.com/docs/reference/specification/v3.0.0),
[Arazzo 1.0.1](https://spec.openapis.org/arazzo/v1.0.1.html).

## Counting and ranking procedure

The frozen selection is a **research-priority sample**, not a global quality or
popularity ranking. No model scored it.

1. Verify source snapshot bytes and parse catalogue metadata.
2. Keep a SchemaStore version map as one family. Collapse identical primary URLs
   and explicitly identified schema version families. Draft variants of the JSON
   Schema meta-schema remain one family in this count.
3. Select APIs.guru's declared `preferred` version. Conservatively group entries
   sharing provider and normalized API title, retaining all catalogue IDs as
   evidence. This can merge genuinely different deployment or subservice surfaces;
   treat the selected document as a representative, not proof it covers every
   grouped surface. Separate them later only with a documented functional reason.
4. Score explicit metadata matches: direct agent/protocol work; developer
   build/test/configuration; data/observability; security/policy; general product
   configuration. API categories have a separately recorded score table. Source
   availability, filename associations and reported origin/licence metadata add
   small declared scores; old API metadata receives a penalty.
5. Select 600 schema families and 400 API families. Cap Azure, Google and AWS at 12
   API families each and other API providers at 20. These are sample diversity
   choices, not evidence that those providers are worse.
6. Fetch qualified exact document URLs only. The allowed hosts are
   `raw.githubusercontent.com`, `www.schemastore.org` and `api.apis.guru`.
   Userinfo, query-bearing sources, explicit ports, private/unqualified hosts,
   parent traversal and redirects are not accepted. Upstream origins, `$id` and
   `$ref` are recorded metadata, never secondary fetch instructions.
7. Remove exact parsed-body aliases from the selected count, then replace from the
   next eligible logical family. The one replacement in this run is explicitly
   metadata-only. Rank ties use a stable logical key.

The final sample has 36 direct agent/protocol schema candidates, 329 developer
schema candidates, 39 data schema candidates, 27 security/policy schemas and 169
general product/configuration schemas. The API portion includes 144 developer,
148 open-data, 52 text, 19 security, 19 analytics, eight machine-learning, six
search, two monitoring and two collaboration families. **Most of these are useful
to AI-assisted work; they are not AI-specific specifications.**

Every row has the common `harness_source_research_item/v1` fields requested for
the four research lists. `source_snapshot_digest` identifies the catalogue that
supplied the candidate; `body_snapshot_digest` separately identifies downloaded
document bytes. An unknown immutable revision or Git blob identity stays null.
Branch names are not fabricated commit IDs. `license_verified` stays false,
`qualification_status` stays `unreviewed`, and compatibility stays `unverified`.

## Rights and freshness qualification

SchemaStore's own repository reports Apache-2.0. Its catalogue also links to
hundreds of documents outside that repository. A repository licence must not be
assigned to every external URL. Check the exact document, provenance, applicable
notices and referenced dependency licences before redistributing a package.
[SchemaStore](https://www.schemastore.org/),
[repository licence](https://github.com/SchemaStore/schemastore/blob/master/LICENSE).

APIs.guru explicitly distinguishes definitions contributed by authors under CC0
from definitions acquired from public sources under its stated fair-use position.
Its repository badge is not a blanket licence grant for every upstream document.
Keep unqualified definitions as research references. `info.license` describes the
exposed API according to OpenAPI; it alone does not settle rights in each copied
file or linked asset. [APIs.guru licence explanation](https://github.com/APIs-guru/openapi-directory#licenses),
[OpenAPI License Object](https://spec.openapis.org/oas/v3.1.1.html#license-object).

Recommended evidence fields for a subsequent admission package are: immutable
source/revision and digest, exact licence evidence path/digest and scope,
attribution requirements, parser/dialect/version, complete dependency closure,
positive and negative examples, declared effects, native adapter profile,
verification report digest and independently reviewed package digest. A fresh
catalogue fetch updates discovery evidence; it must not automatically replace a
previously admitted package's bytes or approval.

## How to make a contract useful to one focused harness step

**Recommended package shape**, subject to the existing package/materializer edge:

```text
Harness Working Directory Package
├── AGENTS.md: task scope, invocation and refusal meaning
├── contracts/
│   ├── input.schema.json and output.schema.json, when original tool contracts
│   ├── upstream.schema.json or openapi.json, when redistribution is qualified
│   └── pinned dependency files with original URI bindings
├── tools/: an optional separately reviewed validator or adapter
├── examples/: useful positive examples
├── verification/: negative, boundary and serialization fixtures
└── LICENSE / NOTICE / provenance records as applicable
```

A passive schema does not automatically load into any harness. The materializer
must select an appropriate native instruction/skill/tool adapter, and native
loading must be observed separately. Scripts are optional: a schema plus examples
can be useful context, while execution requires a qualified validator and budget.
The current native review profile must explicitly admit each executable/config
role; installing a contract must never silently activate plugins or hooks.

Do not flatten reference graphs into one schema by naïve substitution. JSON Schema
identifiers are not necessarily download locations, and reference elimination can
change behavior. Preserve base URI, dialect and resource identity in a pinned
offline registry. The acquisition here counts references but does not claim that
it has validated or closed them. [JSON Schema 2020-12 Core, §§8–9 and appendix B.2](https://json-schema.org/draft/2020-12/json-schema-core).

## Qualification tests that distinguish useful packages from schema-shaped text

- **Dialect test:** run the intended validator against valid/invalid fixtures for
  the exact dialect; refusing an unsupported dialect is preferable to ignoring it.
- **Unknown-key test:** prove whether extra fields are accepted; do not assume
  `properties` alone closes an object.
- **Numeric test:** include `1`, `1.0`, `true`, near-integral decimals and extreme
  exponents. JSON Schema's integer meaning is mathematical, not Python's class.
- **Format test:** record whether `format` is annotation or assertion. Include a
  malformed date/email/URI that the advertised policy is supposed to reject.
- **Reference test:** a remote/local-file reference, cycle and conflicting `$id`
  cannot trigger network or arbitrary filesystem access in offline validation.
- **Serialization test:** request query arrays, path escaping, multipart and error
  status variants must agree with the selected OpenAPI dialect and adapter.
- **Effect test:** an API's read-like name or annotation cannot bypass runtime
  permissions; an ambiguous timeout must not become automatic mutation retry.
- **Whole-package test:** changing a helper, schema, example or licence file changes
  the package review subject; a missing dependency fails before invocation.
- **Semantic test:** a schema-valid request can still violate a domain precondition.
  Keep domain checks and refusal output in the tool contract and fixtures.
- **Native test:** offered, fetched, materialized, discovered, loaded, used and
  verified outcomes are recorded separately for the exact harness/version.

The numeric and format distinctions follow the validation specification.
[JSON Schema 2020-12 Validation, §§6–7](https://json-schema.org/draft/2020-12/json-schema-validation).
The JSON Schema project supplies a language-independent test suite, and Bowtie
compares validator implementations; reuse them when qualifying an engine rather
than claiming the seven collector checks constitute schema-validator conformance.
[JSON Schema Test Suite](https://github.com/json-schema-org/JSON-Schema-Test-Suite),
[Bowtie documentation, observed 2026.7.4](https://docs.bowtie.report/en/stable/).
SchemaStore recommends positive and negative schema fixtures and provides coverage
checks; catalogue membership does not establish that each schema has all of them.
[SchemaStore contributor guide](https://raw.githubusercontent.com/SchemaStore/schemastore/master/CONTRIBUTING.md).

## Twenty original build opportunities

These are concrete proposals for original packages or extensions at existing
boundaries. They are **not twenty newly authored packages**, and not instructions
to create duplicate canonical runtime records. First reuse the named owning
component; place new fixtures and reusable methods around its current contract.

| # | Proposed original package | Useful input → output and discriminating case | Owning boundary to reuse |
|---|---|---|---|
| 1 | Focused task brief checker | Task, prerequisites, success criteria and allowed first actions → missing/contradictory fields; reject a first action outside authority | `skill_state_context`, practitioner context |
| 2 | Context budget allocation checker | Required facts and byte/token estimates → a deterministic admitted subset with omissions; never drop required facts to meet budget silently | `context_budget`, context pack manifest |
| 3 | Working-directory placement preview | Exact package tree plus target profile → proposed paths/collisions; case-fold and symlink collisions refuse | Existing compiler/materializer proposal and `CataloguePackage` |
| 4 | Native loading evidence validator | Offered/fetched/loaded/used observations plus exact hashes → truthful stage summary; loaded without matching bytes refuses | Harness execution contracts and Run History |
| 5 | Package reference closure audit | Schema files and URI map → unresolved/conflicting bindings; remote URI must not trigger network | Catalogue package and validation engine |
| 6 | Schema dialect compatibility report | Declared dialect/vocabularies and validator capabilities → eligible/unsupported; required unknown vocabulary refuses | Existing engine compatibility handshake |
| 7 | Numeric contract agreement corpus | Schema numeric limits and tool results → representational mismatch cases; `1.0` versus `true` and near-integer strings | Candidate verification fixtures |
| 8 | API serialization fixture compiler | One pinned operation and example values → expected wire path/query/headers without sending; percent-encoding collisions differ | API adapter binding |
| 9 | Tool result envelope checker | Output schema, structured content and error flag → consistency findings; error text cannot become a successful result | MCP adapter and harness output boundary |
| 10 | Model identity receipt checker | Requested route, provider-reported identity and usage → exact/unknown/mismatch facts; never substitute requested model for reported model | ModelGateway accounting |
| 11 | Usage aggregation with unknowns | Attempts with optional usage fields → known subtotal plus unknown count; missing usage never becomes zero | Existing accounting records |
| 12 | Credential reference lint pack | Opaque credential lease metadata and target endpoint → scope/expiry/recipient findings; no raw secret in the package | `credential_leases` |
| 13 | Local endpoint topology brief | Harness placement and endpoint address → explicit host/container reachability assumptions; cloud `127.0.0.1` is not the user's machine | Provisioning and endpoint binding |
| 14 | Deadline propagation checker | Parent/child remaining deadlines and clock facts → violations; later child deadline cannot widen authority | Shared engine invocation context |
| 15 | Uncertain-effect reconciliation fixture | Attempt ID, acknowledgement and observed external state → known/unknown outcome; timeout alone cannot prove failure | Existing effect policy and service records |
| 16 | Retry-owner collision audit | Layer retry policies and attempt ceilings → multiplicative retry exposure; reject two owners for the same attempt | Engine adapter/retry boundary |
| 17 | Resume binding compatibility checker | Checkpoint profile/contract/package identities and proposed binding → resume/migration-required/refuse; changed stateful engine refuses silent resume | Run History and executor resume edge |
| 18 | Evidence-linked retrieval result checker | Query, result citations, material hashes and minimum relevance → missing/stale evidence; fluent summary without matching source refuses | Intelligence Search and Retrieval |
| 19 | Model-specific context variant comparator | Base package plus condensed/reworded variants and required facts → retained/omitted constraints; smaller text never means equivalent by itself | Package derivation and independent evaluation |
| 20 | Contract semantic-change report | Old/new pinned contract plus counterexample corpus → tested acceptance changes and unknowns; new optional field cannot conceal a narrowed enum | Versioned component contract and admission review |

The first practical batch should be 1, 3, 5, 8, 10 and 19: they directly improve
step setup, safe materialization, schema reuse, API adapters, truthful accounting
and model-specific intelligence. This ordering is an engineering recommendation,
not measured demand. The existing six data packages already demonstrate the
contract/tool/fixtures shape; reuse their bounded stdio and independent testing
approach rather than generating cosmetic occupation variants.

## Repeating the research

The collector and its seven offline boundary checks are saved beside this note.
For a new run, use a new cache run name and new artifact output directory:

```sh
env -i PATH=/usr/bin:/bin /usr/bin/python3 \
  artifacts/harness-source-research-2026-09-23/collect_contract_candidates.py \
  --fetch --run-name contracts-successor-YYYYMMDD \
  --output-dir artifacts/harness-source-research-YYYY-MM-DD/contracts-successor
```

The current collector deliberately consumes the two digest-bound September 23
catalogue snapshots. A future fresh discovery run must first acquire and verify
new snapshots through the existing source transport and update the input binding
deliberately. Do not present a rerank of old metadata as a fresh upstream survey.
The corrected collector excludes invalid raw navigation URLs from future selections
without guessing their destination. The Europeana record in this frozen list has
a separately fetched, explicit same-origin normalization record.
No scheduler, background poller or automatic publication was installed.

All external documentation cited here was consulted on September 23, 2026.
The source standards are pinned in their URLs; mutable repository documentation
is discovery evidence. The dated JSON catalogue hashes and acquired body hashes
provide the reproducible observation for this run.
