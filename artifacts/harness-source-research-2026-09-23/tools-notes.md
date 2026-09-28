# Tools research list: 1,000 MCP integration leads

September 23, 2026. This is a ranked research population, not an approved catalogue.
The unit in every row is `tool_provider/mcp_server_package`. Individual callable
tool schemas were not discovered. No server was started, package installed,
provider action invoked or intelligence item approved.

## Files

- [tools-ranked.jsonl](tools-ranked.jsonl): exactly 1,000 ranked integration records.
- [tools-population.json](tools-population.json): source digests, population counts,
  exclusions, selection breadth and final output digest.
- [tools-package-metadata.json](tools-package-metadata.json): 120 public package
  metadata checks, with source URLs, response digests and match outcomes.
- [tools-build-opportunities.json](tools-build-opportunities.json): 20 specific
  adapter experiments, linked to records in the selected population.
- [build_tools_research.py](build_tools_research.py) and
  [test_tools_research.py](test_tools_research.py): reproducible selection and
  eight offline controls.
- [Tools source coverage](TOOLS-SOURCE-COVERAGE-2026-09-23.md): CLI/library primary
  sources, method-versus-provider counting, 32 additional method leads and a
  qualification plan. These supplements are not added to the 1,000-server count.

## Observed population

| Observation | Count |
| --- | ---: |
| Registry response pages with verified snapshot digests | 353 |
| Registry rows and unique server names | 35,293 |
| Registry-reported active / deprecated names | 34,923 / 370 |
| Additional exact installation-surface aliases collapsed | 31 |
| Eligible distinct installation declarations after filters | 34,892 |
| Selected integration leads | 1,000 |
| Publisher namespaces represented | 816 |
| npm/PyPI metadata GETs / matching responses / 404s | 120 / 119 / 1 |
| Selected rows with unknown licence declaration | 887 |
| Source-code licence verification / callable-tool discoveries | 0 / 0 |
| Executed servers / approved packages | 0 / 0 |

The snapshots come from the official registry's `version=latest` pagination.
The continuation record reports completion. This is one traversal over time,
not a transactional snapshot of the changing registry. Name conflicts are
excluded rather than resolved by guessing; none occurred in this population.
“Active” is the registry's status, not an independent service-health observation.

All selected rows have distinct names and stable name-derived research IDs.
Installation deduplication uses the declared repository and complete normalized
package/remote surfaces, dropping prose-only fields. It does not collapse an
entire monorepo or all servers using the same host. Equivalent methods, repackaged
implementations with different surfaces and semantic duplicates may remain.
Therefore these are 1,000 distinct integration declarations, not 1,000 proven
distinct functions.

## Ranking is explicit and reproducible

The priority score is a sum with a 100-point ceiling:

| Component | Maximum | What it measures |
| --- | ---: | --- |
| Descriptor completeness | 20 | Description detail, title, version and website fields |
| Declared task relevance | 20 | Keyword matches to Baltor's task families and operation verbs |
| Dependency clarity | 20 | Package, exact-looking version, described variables and package metadata match |
| Declared runtime surface | 15 | Recognized declared transport/package ecosystem and a launch surface |
| Primary surface evidence | 25 | Repository/website/install/remote declarations plus matching package metadata |

An explicit `[TEST]`, `[DEMO]` or `[STAGING]` description prefix deducts up to 20
points. An ordinary testing utility is not penalized for the word “test.” Ties
use the exact server name. A cap of 20 selected records per publisher namespace
keeps one prolific publisher from filling the list. The selected score range is
75–100.

These are editorial research-priority signals. A score of 100 does not indicate
100% safety, reliability or task success. Descriptions can overclaim and keyword
matching can reward broad descriptions. Source fields do not verify publisher
ownership, actual callable operations or product quality. The package-metadata
checks were selected from the initial ranking, capped at four checks per
publisher, so enriched rows had more opportunity to score evidence points. This
is intentional research triage, not an unbiased comparison experiment.

`dependency_clarity` describes launch metadata, not a resolved dependency graph.
`declared_runtime_surface` does not establish that a runtime is installed or
compatible with the user's machine. The snapshot's package versions are retained
in `reported_version`; `upstream_revision` and `upstream_blob_sha` stay null.
An exact version string is not an immutable source or binary pin.

## Package metadata checks

The existing Loop Engine bounded HTTPS transport fetched only public versioned
npm/PyPI metadata. It sent no credentials, followed no redirects and ran no
downloaded code. The run allowed 150 physical requests including retries, 120
selected package checks, 10 seconds per request, 4 MiB per response and at most
20 seconds total provider-requested pause. It made 120 requests and downloaded
764,181 bytes; no retry was needed.

Name/version equality was checked against the registry declaration, using
PyPI's name normalization where applicable. The 119 matching responses establish
metadata agreement only. The one 404 remains recorded. Reported licence text is
retained when present and bounded; every `license_verified` remains false.
Neither a public package endpoint nor a package metadata licence field proves
rights to redistribute all source, dependencies, assets or data.

Raw bodies remain in the existing content-addressed quarantine outside the
repository at `/home/username/.le-codex-research-cache/four-catalogues-20260923`.
The parent session's initial and continuation indexes plus the recorded SHA-256
digests bind each source page. `source_path` is a JSON location within that page,
for example `servers/5/server`. Re-running the local builder reads those exact
bytes and refuses a digest mismatch or incomplete registry traversal. Its
acquisition mode refuses overwriting the existing metadata-run summary.

## Twenty concrete opportunities

The JSON opportunity file contains source record IDs, proposed contracts and
negative controls. The proposals below are inferred experiments from published
descriptions, not verified upstream tool interfaces. They are deliberately
narrower than enabling every advertised capability of a server.

| Opportunity | Proposed first useful result |
| --- | --- |
| Google search retrieval | Bounded URLs and provenance with locale/query receipts |
| YouTube transcript retrieval | Timestamped segments tied to video and language |
| Docsmint hybrid retrieval | Context blocks tied to an explicit tenant/workspace |
| Slack thread reads | Bounded authorized message evidence for one task |
| Zoteus citation retrieval | Exact library-item/page evidence for research claims |
| Neurostack note retrieval | A budgeted context pack from a selected vault |
| ContextStream code retrieval | Code references tied to the checked-out revision |
| LogsLoom diagnostics | Redacted, bounded log evidence with truncation receipts |
| Trawlia page extraction | Extracted page content with URL/acquisition provenance |
| GitHits code discovery | Reuse candidates with revision and rights evidence pending |
| Local notes | A link-repair proposal that does not write automatically |
| Airtable schema inspection | Field definitions under explicit base/table authority |
| Outline document retrieval | Access-aware text and source-version receipts |
| Obsidian search comparison | Same-query lexical/semantic/graph retrieval measurements |
| Litescope schema comparison | Reported differences without applying migrations |
| Apple Calendar availability | Time-zone-aware free intervals without making bookings |
| Watchgoose job evidence | Missing/fresh heartbeat evidence for selected projects |
| PostgreSQL read-only profile | Bounded results with tested write/effect refusals |
| Preprint section retrieval | Attributed sections tied to a paper's exact version |
| npm dependency preflight | Runtime/package metadata checks without installation |

For immediate original authoring, use the separate source-coverage report's
deterministic method proposals. For wrappers, first pin source, inspect schemas,
establish explicit effect/authentication scope and write fixtures. A discovery
row is not permission to launch its advertised command or connect to customer
accounts. Runtime selection should compare qualified engines behind the same
typed edge; server names and description tags do not create execution authority.

## Checks and preserved failures

Eight offline controls cover inactive/nonlatest exclusion, conflicting latest
versions, exact duplicates and installation aliases, distinct monorepo packages,
unknown-licence handling, metadata-versus-callable evidence, score bounds and
explicit nonproduction labels. All pass in `tools-controls-final.txt`.

The initial missing-module attempt is retained in
`tools-controls-before-implementation.txt`. A later named control demonstrated
that an explicit `[TEST]` registration could receive a higher relevance score;
`tools-controls-test-label-before-repair.txt` preserves the failure. The bounded
prefix penalty repaired it. The prior population and output remain as
`tools-population-initial.json` and `tools-ranked-initial.jsonl`.

The ranked research output does not alter the six frozen original systems
packages, current served catalogue, release state or Claude's deployment work.
