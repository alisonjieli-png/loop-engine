"""Explain ranking evidence and bounded reuse experiments; no upstream code copying."""
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
PATTERNS={
'AgriciDaniel/claude-seo':('Specialized website analysis, rendering and drift-monitoring procedures are advertised.','Separate SEO findings, page observation and network acquisition into bounded typed operations. Test redirects and changing DNS in controlled fixtures before accepting any source safety claim.'),
'affaan-m/ECC':('Modular roles, reusable procedures and lifecycle hooks.','Explore an exact package-to-native-profile adapter; verify one selected role and hook before considering a larger pack. Keep producer and reviewer authority separate.'),
'czlonkowski/n8n-skills':('Workflow construction knowledge paired with an MCP connector.','Wrap workflow validation and reusable step lookup as typed operations; compare a checked deterministic workflow with generating it afresh.'),
'nowork-studio/notfair-plugin':('Marketing/analytics integrations presented through one authentication surface.','Prototype a credential-reference broker for read-only report retrieval. Keep campaign writes and spending under distinct effect authority.'),
'TencentCloudBase/CloudBase-AI-Toolkit':('A provider-specific bundle spanning storage, identity, data and functions.','Represent provider requirements in a passive compatibility profile; adapt one bounded data operation behind a replaceable engine rather than importing the entire stack.'),
'cloudflare/skills':('Platform guidance and a protocol connector shipped together.','Pair scoped documentation retrieval with one declared deployment-preflight operation; keep knowledge access separate from deployment authority.'),
'sangrokjung/claude-forge':('Maker/checker roles, lifecycle hooks and continuation behavior are advertised.','Compare exact producer-exclusion and bounded-resume policies with Baltor records. Require request ceilings and preserved unknown outcomes before adopting retry behavior.'),
'suboss87/FDEOps':('Role-specific engineering tasks with local customer context.','Build task-oriented context selection with explicit customer/project scope, correction precedence and retention limits; test that one project cannot retrieve another’s notes.'),
'Galaxy-Dawn/claude-scholar':('Research, experiment and writing procedures combined with project knowledge.','Design a research packet containing source references, uncertainty, experiment inputs and acceptance criteria; compare citation preservation after context compression.'),
'OthmanAdi/planning-with-files':('Persistent planning files and selective context injection are declared.','Compare a typed task-state snapshot with a compact working brief. Keep Markdown content as data and refuse to infer executable authority from it.'),
'squirrelscan/squirrelscan':('Website checks cover several review dimensions.','Wrap one deterministic website-check result schema and prioritize findings by impact. Measure false positives on known-good and intentionally broken pages.'),
'gemini-cli-extensions/data-agent-kit-starter-pack':('A specialist data-engineering knowledge pack for one cloud ecosystem.','Build task packages for bounded SQL/data operations, with provider dependencies explicit; first qualify equivalent local fixtures before hosted execution.'),
'minipuft/claude-prompts-mcp':('Versioned templates, workflow chains and gates are exposed through a protocol.','Adapt prompt/template retrieval and result validation through existing typed edges. Version the template and criteria independently; do not introduce another operational runtime.'),
'Nimbleway/agent-skills':('Search, extraction templates and cited research are advertised.','Separate source acquisition from extraction and claim review. Preserve URL, timestamp, content digest and schema refusal before reusing extracted records.'),
'CloudAI-X/claude-workflow-v2':('Specialized project roles and workflow hooks are grouped in a plugin.','Map the role descriptions onto existing Loop profiles; qualify the smallest useful planner/executor/reviewer composition instead of adding parallel runtime classes.'),
'youdotcom-oss/agent-skills':('Search/research integrations include several authentication/payment mechanisms.','Add explicit connector capability, credential-reference and cost constraints to a research request. Test unavailable endpoints without inventing fallback authority.'),
'drobins25/craft':('A write gate and retained project decisions are described.','Compare planned-change, reviewed-change and applied-change records against exact working-tree digests. Test stale plans and failed review before any materializer write.'),
'product-on-purpose/pm-skills':('Product-lifecycle procedures and specialist review roles are advertised.','Create original decision packets for discovery, prioritization and launch readiness, each with evidence requirements and a small independently checked example.'),
'ww-w-ai/bkit-claude-code':('Checking generated code against design specifications is advertised.','Wrap design-to-implementation comparison with structured findings and explicit unknowns; evaluate it against both missed requirements and harmless implementation differences.'),
'Shopify/Shopify-AI-Toolkit':('Domain development tools explicitly describe telemetry in manifest prose.','Treat telemetry destinations and opt-out behavior as declared effects to verify in code. Benchmark a local validation operation with outbound access disabled.'),
'ChromeDevTools/chrome-devtools-mcp':('Browser debugging, automation and performance analysis are declared.','Qualify browser availability and observation first, then a bounded action adapter. Return explicit capability failures rather than silently substituting an unsupported browser path.'),
'markifact/markifact-mcp':('Marketing account analysis and gated campaign operations are advertised.','Separate read-only diagnosis from write-capable campaign actions; enforce budget and approval on the action boundary, not only in instructions.'),
'cathrynlavery/diagram-design':('Many diagram types and exported visual assets are advertised.','Introduce a diagram specification with explicit semantic nodes/relationships, then compare interchangeable renderers against a meaning-preservation check.'),
'nyldn/claude-octopus':('Cross-platform setup and quality-gate fixes appear in release metadata.','Build a small compatibility fixture matrix for line endings, paths and web assets; keep compatibility evidence tied to the exact client/profile version.'),
'unclejobs-ai/second-claude-code':('An iterative gather/draft/check workflow with multiple extension types is advertised.','Compare one bounded research-and-verification loop with the existing Practitioner profiles; retain failed drafts and independent checker decisions.'),
'scaccogatto/okf-skills':('Portable knowledge bundles, validation and protocol serving are described.','Test a passive knowledge-package schema and deterministic link/reference validation before considering a graph or retrieval backend.'),
}

def escape(text):return str(text).replace('|','\\|').replace('\n',' ')
def main():
 rows=[json.loads(line) for line in (HERE/'plugins-ranked.jsonl').read_text().splitlines()]
 stats=json.loads((HERE/'plugins-population.json').read_text())
 missing=[r['repository'] for r in rows[:20] if r['repository'] not in PATTERNS]
 if missing:raise ValueError('Top20 require explicit human synthesis: '+repr(missing))
 observations='; '.join(f'{key}: {value}' for key,value in sorted(stats['evidence_levels'].items()))
 table='\n'.join('| '+str(r['rank'])+' · ['+escape(r['name'])+']('+r['source_url']+') | '+escape(PATTERNS[r['repository']][0])+' | '+escape(PATTERNS[r['repository']][1])+' |' for r in rows[:20])
 text=f'''# Plugin research priorities — September 23, 2026

The [ranked JSONL](plugins-ranked.jsonl) contains **1,000 research leads**, grouped
as logical plugin packages for this study. This is an order for further
inspection, not a global quality ranking, compatibility certification, license
clearance, or a set of approved Baltor library items. No upstream code was
executed, imported or installed.

## Evidence and comparison population

The source is Tezan Sahu’s [AgentPluginZoo](https://github.com/tezansahu/agentpluginzoo),
pinned at [`{discovery_revision()}`](https://github.com/tezansahu/agentpluginzoo/tree/{discovery_revision()}).
Every cached source was checked against its recorded SHA-256 before CSV parsing.

| Observed export / result | Count |
| --- | ---: |
| Artifact rows in the actual export | {stats['artifact_rows']:,} |
| A_plugin rows used for this lane | {stats['plugin_rows']:,} |
| B_skill rows, excluded from this lane | {stats['strata']['B_skill']:,} |
| C_mcp rows, excluded from this lane | {stats['strata']['C_mcp']:,} |
| Repository metadata rows | {stats['repo_rows']:,} |
| Separate conformance-table rows | {stats['conformance_rows']:,} |
| A_plugin IDs joined to conformance | {stats['plugin_artifact_ids_joined_to_conformance']:,} |
| Conservative groups after initial identity deduplication | {stats['logical_groups']:,} |
| Groups with a reported fetched plugin manifest | {stats['eligible_logical_groups']:,} |
| Ranked repositories / owners | {stats['distinct_ranked_repositories']:,} / {stats['distinct_ranked_owners']:,} |
| Primary manifest paths attempted across both campaigns | {stats['primary_manifest_attempts']:,} |
| Verified current manifest-byte reads across both API campaigns | {stats['primary_manifest_verified_byte_reads']:,} |
| Anonymous exact-byte public-access checks / confirmations | {stats['anonymous_public_source_checks']:,} / {stats['anonymous_public_source_confirmations']:,} |
| Plugin licenses independently cleared | 0 |

Selected-record evidence: **{observations}**. All records remain
`qualification_status: unreviewed`, `compatibility_status: unverified` and
`license_verified: false`. Reported license strings are search signals, not
permission to copy an entire package.

The separate conformance table and project headline cover 68,072 rows, whereas
the pinned artifact CSV exposes 31,915 plugin rows. Those populations are not
interchangeable. Every A_plugin row used here joined by exact artifact ID;
headline rates were not applied to an invented 68,072-item discovery population.
The [population/evidence record](plugins-population.json) gives all source digests,
counts, scoring details and actual request totals.

## What primary inspection establishes

For a selected location, the bounded GitHub reader resolves a full repository
commit and reads the manifest at that exact commit/path. The returned file type,
path, decoded byte count and Git blob hash must agree. Exact manifest bytes are
then stored in a content-addressed quarantine **outside the repository** and
bound by SHA-256. Missing/inaccessible paths and unsupported responses remain
explicit observations; they are not converted into compatibility evidence.

Before new manifest metadata enters the ranked export, a separate credential-free GET must return exactly the same bytes from the pinned raw GitHub URL. A status flag alone is insufficient: URL, status and both content digests must agree. An unconfirmed source falls back to the public corpus record, with new private-uncertain metadata and commit information omitted. This establishes anonymous access to those bytes at observation time; it does not assert permanent repository visibility.

A strict JSON object observation is only format evidence. Referenced skills,
hooks, commands, protocol servers, dependencies, credentials, side effects,
entrypoint discovery and actual task performance were not qualified. Even a
manifest that follows the [published Agent Plugins 1.0.0 specification](https://agent-plugins.org/specification)
does not establish that a particular client loads or safely runs its components.
Vendor-specific native packages can also be useful without targeting that format.

Metadata projections are bounded, reject duplicate JSON names/nonfinite values
and invalid Unicode, and preserve any truncation indicator. Full bodies remain
in quarantine; they are never treated as instructions to this research process.

## Identity and duplicate handling

The initial grouping uses repository plus a normalized logical bundle path,
removing a final dot-prefixed client `*-plugin` directory, and joins identical
same-repository reported manifest fingerprints. The collector’s
[implementation](https://github.com/tezansahu/agentpluginzoo/blob/{discovery_revision()}/collector/store.py)
shows that `content_hash` is the first **24** hexadecimal characters of SHA-256
of manifest text. It is not a whole-package digest and is not a semantic hash.

The final selection also avoids counting the same repository/current manifest
SHA-256 or the same repository/observed manifest name twice. Related source
locations remain linked in each record or the primary-observation ledger. This
is conservative grouping: two intentionally distinct same-name variants can be
merged, while semantically copied code in different repositories can remain.
No comparison of every package asset or global semantic deduplication is claimed.

## Ranking recipe

The reproducible recipe is `plugin_research_priority/v3`. Scores order research
work; they are not calibrated probabilities or quality ratings.

| Component | Points / rule |
| --- | --- |
| Purpose keyword heuristic | 8 + 4 per matched topic, capped at 24; repository name, package path and available manifest metadata |
| Reported component/format evidence | 5 + 2 per reported component kind + 2 for a root manifest + 2 for reported schema agreement, capped at 16 |
| Primary manifest observation | 8 for a strict JSON object; 3 for verified bytes with another JSON shape; 0 otherwise |
| Reported maintenance | 15 within 30 days, 12 within 90, 8 within 180, 4 within 365, 1 otherwise; archived repositories receive 0 |
| Reported license | 10 for the listed permissive SPDX families, 5 for another reported license, 0 for unknown |
| Repository popularity | `min(10, 2 × log10(stars + 1))` |
| Diversity | `10/(1 + prior repository selections) + 5/(1 + prior owner selections)` |
| Example/template locations | −8 for an explicit example/test/fixture/template path component |
| Observed missing source | −12 for a 404 or unavailable repository head |

No repository contributes more than eight entries and no owner more than twenty.
Actual maxima are {stats['maximum_items_one_repository']} and {stats['maximum_items_one_owner']}.
Short keywords have boundaries so, for example, “git” does not classify “digital”
as code development; owner names cannot create a task topic. Every record
contains the score components, whose decimal sum equals its priority score.

The first acquisition order used a simpler metadata heuristic before descriptions
were available. That order is preserved in `plugins-initial-discovery-order.json`.
Final ranking corrects short-token/owner-name artifacts and uses the new primary
observations. This creates an inspection-selection bias; it is stated rather
than presented as an unbiased ecosystem sample.

## Biases and limits

The corpus uses marker-based GitHub search, marketplace expansion and repository
seeds. {stats['unexhausted_source_routes']} of {stats['source_ledger_rows']} source-ledger
routes are not marked exhausted. Search ceilings and repository-tree truncation
can hide items. Public GitHub, English terminology, visible extension layouts,
well-described projects and the source’s discovery routes are overrepresented.
Private/internal projects and unindexed clients are underrepresented.

Repository stars and push dates apply to the repository, not necessarily the
individual plugin. A push can be unrelated to maintenance of the selected bundle.
A root license label may not cover every bundled file. Manifest descriptions are
author claims and keyword-rich descriptions can receive a higher relevance score.
The list does not prove recent releases, ongoing support, commercial suitability,
security, performance, native compatibility or cross-client portability.

## Twenty bounded build/reuse inspirations

The middle column summarizes **manifest-level observations**, not independently
tested implementations. The final column is a proposed Baltor experiment; it is
not copied code or an automatic adoption decision. Each link points to the exact
observed manifest revision.

| Research rank / source | Declared pattern to inspect | Proposed original experiment |
| --- | --- | --- |
{table}

All experiments should reuse existing owners for context selection, model
routing, native layout, harness execution and service retrieval. A plugin wrapper
is an engine candidate behind a typed/versioned edge, not a new operational
runtime or authority source. The runtime classification remains:

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
    ├── Run mode: deterministic, hybrid, or non-deterministic
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition and exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when permitted
    └── Run History records
```

## Reproduce and refresh

`plugins_rank_research.py` verifies the pinned discovery sources and performs the
initial bounded reads through existing `GhCliReader`, `RequestBudget`,
`RequestLog` and `Quarantine` implementations at Loop Engine revision `231f51bb`.
`plugins_continue_primary.py` is a separately authorized continuation with its
own 1,200-request ceiling, a remaining-allowance reserve of 500 and at most 30
seconds of quota waiting. The initial 1,160-request campaign and its output were
preserved before continuation. `plugins_verify_public.py` adds a separate maximum of 1,100 anonymous HTTPS reads, at most 30 seconds of rate-limit waiting, to establish current public access without sending credentials. API and anonymous request totals are reported separately. No upstream lifecycle script or model call ran.

`plugins_build_ranked.py` produces the final JSONL and evidence counts from those
snapshots; `test_plugins_research.py` checks identity/score/evidence behavior.
`plugins-initial-*` records preserve the earlier partial-primary result. A new
research refresh should use a new cache/report namespace and declared budgets;
it must not overwrite this historical evidence or silently turn findings into
catalogue approvals. Unknowns stay unknown until the relevant check succeeds.

The sixteen [original-package paraphrase queries](original-component-paraphrase-queries.json)
were supplied before viewing retrieval results. They are an authored small test
set, not a representative customer benchmark.

## Attribution

AgentPluginZoo’s data/derived tables are published under
[CC BY 4.0](https://github.com/tezansahu/agentpluginzoo/blob/{discovery_revision()}/LICENSE-DATA)
by Tezan Sahu. This ranking adapts those tables by filtering the plugin stratum,
grouping identities, adding current source observations and applying a new
research-priority recipe. The source does not endorse this ranking. Its data
license does not relicense the underlying plugins. Code in the study repository
has a separate license; no upstream implementation was copied into Baltor.
'''
 with (HERE/'plugins-notes.md').open('x') as stream:stream.write(text)
 print({'top20_patterns':20,'notes_written':True})

def discovery_revision():return '83259b7499efc86756b3913ee7d3000a6a668893'
if __name__=='__main__':main()
