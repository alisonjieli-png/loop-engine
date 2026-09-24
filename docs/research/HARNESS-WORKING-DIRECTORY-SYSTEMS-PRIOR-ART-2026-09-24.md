# Harness working directory systems: prior-art addendum

Kind: dated research addendum, September 24, 2026. This extends the
[ecosystem edge map](ECOSYSTEM-EDGE-MAP-2026-09-23.md) and the
[agent-harness review](AGENT-HARNESS-MADEBYWILD-2026-09-23.md) with what
changed since September 23 and what a fresh survey of centralized
registries, file compilers and retrieval systems found. The
[roadmap](../roadmap/roadmap.yaml) remains the task authority. Nothing
here publishes, approves or qualifies material.

## What changed since the September 23 records

- **The Agent Skills format won the format war.** The official client
  showcase now lists 40+ clients that support the `SKILL.md` package
  shape, including Claude Code, Codex/ChatGPT, Cursor, GitHub Copilot,
  VS Code, Gemini CLI, OpenCode, Goose, Amp, OpenHands, Junie, Kiro,
  Droid, Roo Code, Factory, TRAE, Snowflake Cortex Code, Databricks
  Genie Code, Pulumi Neo, Hermes Agent and others. For Baltor this
  multiplies the value of one skill package: the same approved bytes
  land in every client's native skills root. The per-client roots
  still differ (verified in the placement research and the standards
  record), which is exactly what the layout profiles encode.
- **The skills.sh directory (Vercel) became a real centralized
  registry with third-party audits.** It now reports 1.5 million+
  tracked installs, a leaderboard ranked by anonymous install
  telemetry, pack bundling (`npx skills add owner/repo`), topic and
  agent pages, and combined security audits from three providers
  (Gen Agent Trust Hub, Socket, Snyk) shown per skill. Its audit
  states: Safe, Med Risk, Low Risk, Critical, Pending. The audits are
  a useful import gate model; they are not independent correctness
  review (they scan for malicious content, not method quality), and
  Baltor's own review process stays authoritative.

## The centralized systems landscape, one table

| System | What it centralizes | Retrieval | Placement / compile | Trust model | Fit behind Baltor's edges |
|---|---|---|---|---|---|
| [skills.sh](https://skills.sh) (Vercel, open source) | Skills from GitHub repos; install telemetry ranks them | Web search + `npx skills` CLI; per-agent pages | `skills add` writes the client's native skill roots directly | Third-party audits (Gen, Socket, Snyk); `--allow-unaudited`/`--allow-unsafe` escapes | A `library_ingestion_source` engine (candidate-only imports) and a demand-signal source; its audit gate informs, never replaces, Baltor review |
| [anthropics/skills](https://github.com/anthropics/skills) | Anthropic's official skill examples (178k stars) | GitHub browsing; Claude plugin marketplace | Claude Code plugin install | Publisher reputation; Apache 2.0 / source-available mixed | Ingestion source; its per-skill licences need the same file-level rights gate as any repo |
| MCP Registry (registry.modelcontextprotocol.io) | Protocol server packages (34,900 entries measured in the ingestion run) | Registry API | MCPB packs; client config merge | Publisher-declared; Smithery-hosted copies refused in run 2 | Already adopted behind `library_ingestion_source` (the September 23 ingestion staged 4,049 candidates from it) |
| agent-harness (madebywild) 2.1.0 | One `.harness/src/` source compiled to four clients' native files | In-project manifest | `plan`/`apply`; git-based registries; presets with `extends` | Lock file with pre-substitution hashes | A `material_install_layout` engine candidate, after the documented defects (key syntax untranslated, secrets in files, U-Haul deleting instruction files) are contained by the edge checks |
| rulesync 17.0.0 / Ruler | Cross-tool rule synchronization | Not centralized; per-project | Compile rules to each tool's config | Per-project | Same slot; not yet trialed here |
| Claude Code plugin marketplace | Plugins + skills as `claude-plugin` marketplace repos | Marketplace listing | `/plugin install` | Publisher | A distribution surface for Baltor presets, once generated per the client recipes |
| MCPB (Model Context Protocol Bundles) | Client-configuration bundles | Registry/hosted | Per-client bundle apply | Publisher | `custom_plugins_port` watch item |
| Harbor 0.23.0 | Not a registry: an evaluation harness that lists 12 harness integrations | Benchmark suites | Runs agents | Reproducible benchmarking | `response_evaluator` and `step_executor` coverage target, as the edge map records |

## What the landscape confirms about Baltor's design

1. **No existing system is a reviewed, versioned, rights-gated library
   served per-harness.** skills.sh ranks by install telemetry and scans
   for safety; the MCP registry lists publisher declarations;
   agent-harness compiles a project's own files. The gap Baltor
   occupies — independent review before approval, exact-byte identity,
   per-client native placement, offered/fetched/loaded/used as separate
   facts — remains unoccupied.
2. **Placement (compilation) is being commoditized; retrieval quality
   and trust are not.** Every compiler writes native files; none of
   them measures whether the material helped a task. Baltor's
   differentiation is the qualification ladder and the measured
   benefit evidence, not the file copying.
3. **The audit-gate import model is worth adopting as an engine.**
   skills.sh's three-audit gate, and agent-harness's use of it, match
   the candidate-gate design already built (`library_ingestion_source`
   blocks unaudited imports). The September 23 ingestion run already
   staged 4,049 candidates with provenance; skills.sh's audit states
   can become one more metadata field in that contract.
4. **Fresh demand data is public.** The skills.sh leaderboard (what
   developers actually install: frontend design, code review, domain
   modeling, debugging, Azure/Prisma/Supabase platform skills, Lark
   suite skills) is a free signal for prioritizing Baltor's own
   generation matrix, beside the O*NET task grid.

## Evidence states

- **Verified today**: skills.sh directory pages (leaderboard, audits,
  docs), the agentskills.io client showcase (40+ clients), the Agent
  Skills specification, anthropics/skills repository facts.
- **Carried from September 23 records**: agent-harness trial results,
  MCP Registry ingestion counts, placement research per-client roots,
  the standards table per-harness differences.
- **Not verified**: per-audit-provider methodology, the
  leaderboard's telemetry pipeline, whether every listed client
  actually implements the full specification (each still needs the
  native discovery probe before Baltor lists it as supported).