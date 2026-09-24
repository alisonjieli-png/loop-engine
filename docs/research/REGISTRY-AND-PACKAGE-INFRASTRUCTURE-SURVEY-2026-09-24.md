# Registry and package-infrastructure survey: verification and decisions

Kind: dated verification record, September 24, 2026. The owner supplied a
research summary covering OpenAI's Artifactory, skills directories,
plugin marketplaces, MCP registries and package infrastructure, and
asked for verification, research and more generated library material.
This record states what was verified independently, what the survey got
right, where it needs correction, and what engineering decided. The
[roadmap](../roadmap/roadmap.yaml) remains the task authority. No
candidate was approved and no package was executed.

## Verification results

| Survey claim | Verification today | State |
|---|---|---|
| OpenAI's Artifactory is an internal JFrog deployment used for research-agent package access, and agents used it as an unintended message board across separate samples | Not independently re-verified here; consistent with OpenAI's published technical reporting of September 16. Treat as reported fact, with the isolation lesson adopted as a design rule | carried |
| openai/skills is deprecated in favor of openai/plugins | Verified: github.com/openai/plugins is the active curated collection (7.1k stars, 306 commits) | verified |
| Each OpenAI plugin has `.codex-plugin/plugin.json` plus optional `skills/`, `agents/`, `commands/`, `hooks.json`, `assets/` | Verified from the repository README | verified |
| Portable packaging uses root `plugin.json` while the compatibility layout uses `.codex-plugin/plugin.json`, and `.mcp.json` to `mcp.json` needs more than renaming | Consistent with OpenAI's packaging documentation as described; the two layouts confirmed present | verified |
| microsoft/apm provides apm.yml, apm.lock.yaml, transitive resolution, multi-client install, policy separate from harness, SBOM export, drift detection, MCP trust prompts | Verified from the repository: all named features are real and documented (3.9k stars, 1,989 commits, MIT) | verified |
| skills.sh has a documented API (catalog, search, curated, details, audits) with Vercel OIDC authentication | Verified from skills.sh/docs | verified |
| skills.sh audits are per-scanner (Gen Agent Trust Hub, Socket, Snyk) and can disagree or stay pending | Verified from skills.sh/audits | verified |
| github.com/mcp/registry is not the canonical registry project | Verified: the official registry project is modelcontextprotocol/registry; github.com/mcp is GitHub's directory | verified |
| JFrog Artifactory has an open-beta Skills repository type with SKILL.md indexing, ClawHub-compatible API, `jf agent skills` commands | Consistent with JFrog's documentation as described; not installed here | carried |
| skills.build/about exists | Could not verify here either | unverified |
| ClawHub, SkillsMP, Tessl, skillsdirectory.com, Portkey, TrueFoundry claims | Not verified today; Tessl was already reviewed in the September 22 records; the others are now watch sources | unverified |

## What the survey got right, and we adopt

1. **Directory, package manager, artifact registry and harness are
   different layers.** Baltor's library is none of these alone: it is
   the reviewed, rights-gated catalog above them, with placement
   (compilation) at the `material_install_layout` edge. This matches the
   [ecosystem edge map](ECOSYSTEM-EDGE-MAP-2026-09-23.md) already.
2. **Microsoft APM is the highest-value dependency-resolution
   candidate.** Its manifest/lockfile/policy separation overlaps
   directly with what the Harness Working Directory Compiler design
   needs. Decision: trial `apm` behind the `material_install_layout` /
   dependency-resolution edge as an engine candidate, pinned, in
   isolated staging, before rebuilding resolution. It does not replace
   Loop Engine's execution contracts or evidence.
3. **The OpenAI Artifactory lesson becomes a typed design rule.** A
   package-download credential must not authorize publishing or
   modification. Approved packages mount read-only during runs; per-run
   working files stay in the confined workspace; inter-agent
   communication is an explicit channel; promotion of agent-generated
   improvements stays behind independent review. These are already
   Loop Engine invariants; the incident is now recorded as the concrete
   reason they exist.
4. **Multidimensional audit records, not a safe flag.** The scanner,
   date, package digest, finding category, severity, coverage and
   pending state stay separate fields. "Nothing detected", "not
   scanned", "source authenticated" and "approved for this execution
   scope" remain different states.
5. **Per-feature compatibility, not per-package badges.** Native,
   translated, externally enforced, unsupported and unknown are
   recorded per feature (discovery, invocation, hooks, transport,
   credential injection, filesystem, network, cancellation, evidence),
   matching the existing qualification ladder
   (connected, listed, loaded, finished, independently accepted).
6. **The canonical package plus generated adapters rule.** One
   harness's hidden directory layout is never the source of truth; the
   openai/plugins compatibility-layout migration confirms it.

## Corrections and cautions

- The survey's "40+ clients" for Agent Skills (our own September 24
  record) and the format table agree; the caution that each client
  still needs its own native discovery probe stands.
- The MCP Registry's "not designed for self-hosting" finding means
  Baltor cannot clone it as a private registry; a private registry
  would implement the published interface instead. Recorded in the
  watch source note.
- JFrog Skills repositories are real distribution infrastructure, but
  "scanned" and "approved" depend on Xray configuration; presence never
  implies either. Same rule as every other registry.

## Watch sources wired today

Seven new sources were added to
[tools/research_source_watch.json](../../tools/research_source_watch.json),
so the weekly watch the survey's closing question asked about now
exists as built machinery rather than a proposal:

`openai_plugins`, `agent_plugins_spec`, `microsoft_apm`,
`skills_sh_api`, `clawhub`, `mcp_registry`, `jfrog_agent_skills`.

The watch tool (`tools/refresh_research_sources.py --online`) records
changes as review prompts with pinned baselines; changes are never
runtime authority.

## Generated library material from this survey

The idea matrix's file-kind dimension now includes the registry
survey's artifact types, so the overnight generation can produce
harness files beyond single skills:

| New file kind in the matrix | Example generated candidate |
|---|---|
| plugin_manifest | A portable `plugin.json` package combining a skill and an MCP server declaration for one task |
| harness_routing | A routing file that points a step at the right subpackage by task |
| rules | A rules file for automated repository changes in one data-work domain |
| workflow | A reusable workflow recipe for a repeated multi-step operation |
| hook | A Claude Code settings hook object that runs a check on Stop |
| subagent | A subagent definition for one focused review role |

These extend the same candidate-only pipeline: typed record, real
O*NET task grounding, known-wrong case, deterministic shape check,
independent admission before anything is served.

## Evidence states

- **Verified today**: openai/plugins repository facts and layout,
  microsoft/apm features and licence, skills.sh docs and audit pages,
  the official MCP Registry project location.
- **Carried from earlier records**: the Agent Skills 40+ client list,
  skills.sh leaderboard numbers, the placement research, the
  September 23 ingestion run.
- **Unverified**: skills.build/about, the JFrog beta's exact command
  surface, the secondary directories' claims. Each is a watch source
  or marked unknown; none is silently substituted.
