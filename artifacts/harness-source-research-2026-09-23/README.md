# Four ranked harness research lists and original package supply

Checked September 23, 2026. **4,000 research records are searchable locally:**
1,000 skills, 1,000 plugins, 1,000 contracts and 1,000 tool integrations.
Ranking means a documented priority for investigation within each collection.
It does not certify a global top 1,000 or approve material for customers.

## Start here

| Collection | Current evidence | List and explanation |
| --- | --- | --- |
| Skills | 1,000 named groups and distinct instruction hashes; exact source revisions and anonymous instruction reads; 81 repository addresses resolve to 80 canonical repositories | [Ranked skills](skills-ranked.jsonl), [methodology](skills-notes.md), [20 build/reuse opportunities](skills-build-opportunities.json), [independent integrity review](skills-independent-integrity-review-final.md) |
| Plugins | 1,000 logical leads across 989 repository addresses; pinned manifests with matching anonymous public bytes; 993 distinct manifest hashes | [Ranked plugins](plugins-ranked.jsonl), [methodology and 20 experiments](plugins-notes.md) |
| Contracts | 600 document/configuration schemas and 400 API contracts; 891 exact documents fetched and parsed; other gaps explicitly recorded | [Ranked contracts](contracts-ranked.jsonl), [methodology and 20 opportunities](contracts-notes.md) |
| Tools | 1,000 MCP integration declarations selected from 35,293 latest registry rows; 120 public package metadata checks, 119 matched | [Ranked integrations](tools-ranked.jsonl), [methodology](tools-notes.md), [20 build opportunities](tools-build-opportunities.json) |

The tools unit is a tool provider or server package. Individual callable tool
schemas were not discovered, so the list is not 1,000 verified callable tools.
An API description or document schema is a contract input; its presence does
not establish behavioral compatibility. Licence declarations remain unverified
across these research lists. Inspection depth and failures are visible per row.

## Search and retrieve research metadata

[Research index usage](RESEARCH-INDEX-USAGE.md) documents the commands. The index
uses the existing catalogue, atomic-write and Intelligence Search contracts.
It is a derived local view of the four JSONL files, stored outside the repository.
It creates no production catalogue, endpoint or runtime type.

```bash
/home/username/.le-wave2/mcp-revision/.venv-mcp2/bin/python \
  artifacts/harness-source-research-2026-09-23/research_index.py search \
  --category skill --query "code review" --limit 10
```

Use `--category plugin`, `contract` or `tool` to narrow the collection. Use
`--lookup RESEARCH_ID` to retrieve one exact metadata record. This operation
returns provenance and qualification state, never executes a source or silently
installs a package. Query scores are separate from research-priority scores.

The [build record](research-index-build-successor.json) reports all 4,000 exact
payloads read back after acknowledgment, 1,291 referenced source snapshots
verified, zero active records and zero default active-search results. Fifteen
controls pass, including source drift, identity/rank problems and forged
qualification state. Search is lexical and does not guarantee semantic recall.

## Original packages already built

Separate from the source research, Codex authored and prepared **17 original
candidate packages, 137 payload files, 121 distinct file hashes and 535,608
payload bytes**. The count excludes metadata, authoring copies and old attempts.
No external model API generation job, upstream server invocation, package
approval or new deployment was performed for this supply work. Authoring used
the current Codex session and its subagents.

- [Sixteen-package cohort](../codex-component-supply-2026-09-23/README.md): task
  context, capability evidence, context budgets, paired evaluation, CSV/table
  methods, dependency resolution, file inventories, event order and text edits.
- [Research-inspired wikilink package](../codex-research-inspired-components-2026-09-23/README.md):
  missing and ambiguous note targets, with source spans and an explicit bounded
  Markdown profile. It operates on supplied data and makes no full Obsidian
  compatibility claim.
- [Combined counts](../codex-component-supply-2026-09-23/combined-supply-counts-v1.json):
  190 independent checks for the first cohort plus 66 for wikilinks, 256 total.
  Failed numeric and delimiter attempts remain beside their repaired successors.

Each package includes executable code, instructions, input/output schemas,
examples and verification fixtures. They are staged through the existing
candidate contract and are available through the local review search helper.
They are not served by the live Baltor catalogue. Exact-byte admission, rights,
native loading and relevant task acceptance remain separate gates.

## Findings that change the build plan

1. **Package a complete method.** A skill description alone can omit required
   scripts, contracts, references and setup. Resolve the needed files and keep
   their exact identities together.
2. **Count native projections once.** The skills audit removed duplicate named
   projections while retaining their differing bytes as variants. Plugin
   grouping is also conservative and does not prove semantic uniqueness.
3. **Separate discovery from working compatibility.** A registry status or a
   valid manifest does not establish tool connectivity, native loading or a
   successful task. Qualification belongs to the exact execution profile.
4. **Carry rights uncertainty forward.** Repository and package metadata can
   omit narrower file licences. APIs.guru also has different provenance classes;
   the whole collection must not be described as uniformly CC0.
5. **Make contracts behavioral where needed.** Schemas help with shape. Ordering,
   idempotency, effects, units, state migration and acceptance need their own
   obligations and checks.
6. **Test actual bytes and parser boundaries.** Independent tests caught integer
   rounding/underflow, extreme zero exponents and a frontmatter delimiter error
   in the original supply. Syntax and happy-path examples were insufficient.
7. **Keep reference libraries separate from step context.** The 4,000-record
   research index is for discovery. A step receives selected material through
   the Harness Working Directory Compiler and its qualified native profile.
8. **Use source ideas through the existing component boundaries.** Reuse a
   library, wrap an external implementation or build an original bounded
   variation. Preserve source identity, qualification and selectable engines.
   The [functional engine wrapping research](https://github.com/alisonjieli-png/loop-engine/blob/231f51bb1facab517fbe915b08ea9ac85f913347/docs/research/FUNCTIONAL-ENGINE-WRAPPING-RESEARCH-AND-IMPROVEMENTS-2026-09-23.md)
   on current main gives the ownership model and proposed improvements.

The original cohort's sixteen independent task paraphrases retrieved every
expected package in the first three results, with fifteen ranked first.
Two of four unrelated queries still returned weak matches. The existing
relevance-floor work remains necessary; this small candidate result is not a
customer-task benchmark or an admission decision.

## Repeat procedure and source handling

The collection scripts reuse `GhCliReader`, `HttpsGetTransport`, `RequestBudget`,
`RequestLog` and `Quarantine` from Loop Engine at `231f51bb`. The lists, score
components, request records and source digests make the selection inspectable.
For a refresh, create a new dated run/output folder and preserve these records.
Do not overwrite a historical snapshot or silently reuse a changed source.

Raw third-party content stays outside this public repository under
`/home/username/.le-codex-research-cache/`. The shared JSONL files contain
research metadata and source references. No fetched source was executed or
installed. The official skills API returned 401; public page data was used
without bypassing authentication. The registry traversal reached the end of
pagination but is an observation over time, not a transactional snapshot.

Primary collection routes include the [public skills directory](https://www.skills.sh/),
[AgentPluginZoo data definitions](https://github.com/tezansahu/agentpluginzoo/blob/83259b7499efc86756b3913ee7d3000a6a668893/data/README.md),
[official MCP registry API](https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/api/official-registry-api.md),
[SchemaStore](https://www.schemastore.org/) and [APIs.guru](https://apis.guru/).
Every selected record carries its more specific source and inspection status.

## Claude handoff

Claude Code owns further application updates, merging and deployment. These
new research/supply folders are in the shared `/home/username/loop-engine`
checkout for review and integration. The checkout has concurrent dirty work and
must not be reset. The roadmap remains the task authority; these are dated
research and candidate-supply artifacts, not another task tracker.

The deployment handoff is
[CODEX-TO-CLAUDE-DEPLOYMENT-HANDOFF-2026-09-23.md](../../docs/context/CODEX-TO-CLAUDE-DEPLOYMENT-HANDOFF-2026-09-23.md).
The source lists and 137 original payload files do not change the live library's
43 approved items. Admission and release are deliberate later operations.
