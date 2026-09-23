# Agent Harness by wild: prior-art review, September 23, 2026

The owner asked for research on <https://github.com/madebywild/agent-harness>.
This record says what the project is, what a hands-on trial showed, how it maps
to Baltor's components, and what engineering decided. The source was read at
commit `2ecf44f` (tag `v2.1.0`), and the published npm package
`@madebywild/agent-harness-framework@2.1.0` was run in a scratch folder
outside this repository.

## What it is

Agent Harness is a TypeScript command line tool and library, MIT licensed, that
keeps one source for a project's agent configuration under `.harness/src/` and
writes each tool's native files from it. It covers four tools: OpenAI Codex,
Claude Code, GitHub Copilot and Cursor. It describes itself as "the Shadcn for
agent harnesses": shared material is pulled into a project as editable source,
not as a library import.

| Fact | Value |
|---|---|
| Packages | `@madebywild/agent-harness-manifest`, `-framework` (the command line tool) and `-tui`, released together; 8 releases, the latest `v2.1.0` |
| Runtime | Node.js 22 or newer, pnpm, Turborepo, Zod schemas |
| Activity | 14 stars, 5 contributors (two of them the Claude and Codex agents), 35 test files and a container-based end-to-end suite for git registries |
| Entities | prompt sections, skills, protocol server configurations, subagents, hooks, per-tool settings, commands |
| State | `manifest.json`, `manifest.lock.json` (hashes and registry provenance), `managed-index.json` (which generated files it owns) |

How the files land, as its documentation states and the trial confirmed:

| Entity | Codex | Claude Code | Copilot | Cursor |
|---|---|---|---|---|
| Prompt sections, joined in order | `AGENTS.md` | `CLAUDE.md` | `.github/copilot-instructions.md` | none |
| Skills, copied as folders | `.codex/skills/` | `.claude/skills/` | `.github/skills/` | `.cursor/skills/` |
| Protocol servers, merged | `.codex/config.toml` | `.mcp.json` | `.vscode/mcp.json` | `.cursor/mcp.json` |
| Subagents | `[agents.<id>]` in `.codex/config.toml` | `.claude/agents/<id>.md` | `.github/agents/<id>.agent.md` | `.cursor/agents/<id>.md` |
| Hooks | `.codex/config.toml` | `.claude/settings.json` | `.github/hooks/` | `.cursor/hooks.json` |

Other parts:

- **Registries** are git repositories with a strict root: `skills/<category>/<id>/SKILL.md`, `prompt-sections/<category>/<id>/SECTION.md` and `presets/<id>/`. Only skills and prompt sections are pulled one by one. Protocol servers, subagents, hooks, settings and commands arrive only inside presets.
- **Presets** are bootstrap bundles. A registry preset may `extends` another, inheriting its skills and prompt sections parent first.
- **Third-party skills** come from skills.sh. An import is blocked when the source has no published audit report or when an audit provider reports a failure, unless `--allow-unaudited` or `--allow-unsafe` is given.
- **U-Haul** imports an existing `CLAUDE.md`, `AGENTS.md`, `.mcp.json` and similar files into `.harness/src/`.
- **Placeholders**: `{{NAME}}` values are substituted from `.harness/.env`, `.env.harness` or the environment, and `{{behavior.<key>}}` from a behavior map.
- **Ownership**: a generated path that already exists unmanaged blocks `apply`.
- **Changes**: `plan` shows every change before `apply` writes it.
- **Schema versions** are explicit, with `doctor` and `migrate`.

Two documented limits matter for Baltor. Its architecture document states both:

- Cursor gets no prompt file. Prompt sections reach Codex, Claude Code and
  Copilot, and "cursor emits no prompt artifact".
- The lock hashes the source before substitution: "SHA256 fingerprints in the
  lock file are computed on the raw (pre-substitution) text". The lock
  therefore does not identify the bytes a tool actually reads, and cannot stand
  in for a digest of a delivered file.

## What the trial showed

Everything below was run with the published package in
`/home/username/.le-ci-tmp/research/ah-trial` and a second scratch folder. The
live Baltor service was not called.

1. **It works as described.**
   - The package installed 64 dependencies in 4 seconds.
   - `init`, enabling the four tools, and adding one prompt section, one skill, one protocol server configuration and one subagent all succeeded.
   - `apply` wrote 14 files.
   - A real Baltor library item, `split_address_lines_into_components`, placed as the skill arrived byte for byte the same in all four skill folders.
2. **Key references are not translated between tools.**
   - A server header written as `Bearer ${BALTOR_SERVICE_TOKEN}` was copied unchanged into all four connection files.
   - That form suits Claude Code. Cursor and VS Code expect `${env:NAME}`, and Codex expects `bearer_token_env_var` or `env_http_headers`. The Codex file it wrote would send the literal text.
   - Per-tool override files can switch an entity off for one tool, but they cannot reshape a protocol server's fields. Their `options` apply to subagents.
   - So one source file cannot connect all four tools to Baltor correctly.
3. **`{{NAME}}` substitution writes the secret into the generated files.**
   - With `BALTOR_SERVICE_TOKEN` set in `.harness/.env`, the value appeared in plain text in `.mcp.json`, `.vscode/mcp.json`, `.cursor/mcp.json` and `.codex/config.toml`.
   - Projects usually commit those files. This conflicts with Baltor's setup rule to keep the key out of files.
4. **U-Haul lost our main instruction file.**
   - The trial ran on a copy of this repository's `AGENTS.md` and `CLAUDE.md`. Here `CLAUDE.md` only imports `@AGENTS.md` and `@ASTRA.md`.
   - U-Haul detected two prompt sources. By its default precedence (Claude first), it kept `CLAUDE.md` and dropped `AGENTS.md`.
   - It deleted both original files and enabled only Claude.
   - The regenerated `CLAUDE.md` still imports `@AGENTS.md`, which no longer exists. The rulebook's text is nowhere under `.harness/`, and no backup was made.
   - In a repository where `AGENTS.md` is uncommitted, that text is gone. Codex would lose its instructions entirely.

## How it maps to Baltor

| Baltor component | Agent Harness part | Fit |
|---|---|---|
| Placing a package's files in each harness's own layout (roadmap S-6.44; `tools/install_selected_material.py`; `catalogue_packages.FILE_ROLES`) | The provider adapters and the per-tool path table | Close: the same problem, for four tools. Baltor also targets OpenCode and Pi, which Agent Harness does not cover |
| Harness intelligence served as packages of any file type | Skills, prompt sections, protocol servers, subagents, hooks, commands | Close in scope; Agent Harness has no per-file digest, review record or licence state |
| The reviewed, versioned library | Git registries pinned by branch or tag | Different: a git reference is not a content digest, and nothing records an independent approval |
| Independent review before approval | skills.sh audit gating | A useful model for imports; never a substitute for Baltor's review |
| The version policy (explicit versions, refuse newer, no silent downgrade) | `doctor`, `migrate`, `*_VERSION_NEWER_THAN_CLI` | Same principle, already ours |

## How it relates to the Loop Engine runtime

The runtime gives every step its own freshly started harness. That is the
discrete cognitive or act step Loop node: an independently governed instance
of the Loop runtime responsible for one clearly defined cognitive step or
action. It receives the context, instructions, skills, plugins, tools and
working files its assignment needs, and nothing else. Agent Harness has no
runtime. It is a file compiler, and it fits under the runtime at one point.

| Loop Engine concept | Agent Harness counterpart | How they relate |
|---|---|---|
| Materializing a step's working folder for the harness that runs it (the harness executor slot, roadmap package D-19) | `plan` and `apply` from `.harness/src/` into a tool's native files | One engine behind the materializing edge. The runtime still decides which material the step gets, its budget and its permissions; Agent Harness only writes the files |
| A versioned role profile or a step's configuration dimensions | Presets, `extends`, the behavior map | Presets bundle files; a profile also carries typed contracts, conditions, budget and authority. A preset can hold the files of a profile, never the profile itself |
| Spawned Loops, each in its own harness | Subagents inside one harness | Different things. A subagent runs inside the parent harness and shares its authority; a Spawned Loop has its own harness, contracts and Run History. Agent Harness subagents may be one kind of material a step receives, not a way to spawn work |
| Effect authority (file writes, commands, network, model calls, each typed and approved) | Hooks that run commands on tool events | A hook is an effect. A generated hook must pass the same typed authority as any other command before a step's harness starts; Agent Harness does not check that |
| Path-confined workspaces (no traversal, no symlink escape, no unsafe overwrite) | Relative-path checks on sources; `OUTPUT_COLLISION_UNMANAGED` on targets | Compatible. The materializer engine runs inside the step's confined folder, so its own checks add to ours |
| Run History records every effect | The lock and the managed-file index | The lock records source hashes and provenance. A Run History record of a materialization needs the digests of the written files as well, measured after `apply` |
| Engines behind fixed, typed, versioned edges, chosen by declared order and evidence | A second engine next to Baltor's own layout profiles | The edge stays Baltor's: package in, placed files and their digests out. Agent Harness is one engine, selected only where a workspace already uses it or where evidence shows it places files better |

## Decisions

Recorded under the owner's rule to search for existing work, and to adopt,
adapt or reject it with a reason.

1. **Adapt, as a distribution path.**
   - Publish a small public registry in Agent Harness format that holds only a Baltor preset. The preset carries the Baltor protocol connection and a free search skill.
   - It gives a per-tool override for each key reference: disable the generic server for Codex and supply a Codex settings file with `bearer_token_env_var`.
   - It never uses a `{{NAME}}` placeholder for the key.
   - The paid library stays behind the service; the registry holds no library content.
   - One command then connects an Agent Harness project: `npx harness preset apply baltor --registry baltor`.
   - Reason: low cost, and it reaches teams that already manage four tools from one source.
2. **Adapt, as an optional placement engine on the client.**
   - Behind the placement edge of S-6.44, add an engine that writes a selected Baltor package into `.harness/src/`, with Baltor provenance and digests, then runs `harness plan` and `harness apply`.
   - Baltor's own layout profiles stay the default engine.
   - The engine never runs `init --u-haul`, refuses to write a key through a placeholder, and runs only when the workspace already uses Agent Harness.
   - Reason: the owner's rule of swappable engines behind a fixed edge, and customers who already standardized on Agent Harness.
3. **Adopt the ideas, not the code:**
   - the per-tool table of where nested files are discovered (Claude Code reads all nested artifacts, Codex reads nested prompts, Copilot and Cursor only the root);
   - a lock with hashes and a managed-file index, with drift detection;
   - `plan` before `apply`;
   - a stop on unmanaged files at a target path;
   - per-tool override files;
   - preset inheritance order.
4. **Reject:**
   - running U-Haul on this repository;
   - `{{NAME}}` placeholders for any credential;
   - treating a git registry as approved intelligence, because it has no digest per file, no review record and no licence state.

## Findings to share upstream

These three findings are written so they can be filed on the project as they
stand. Nothing has been posted:

- U-Haul deletes a dropped prompt source without a backup. When `CLAUDE.md` imports `@AGENTS.md` (a common pattern), the kept file then points at a deleted file. Suggested fix: import imports, or back up every deleted file under `.harness/.backup/`.
- The same key reference is copied into every tool's connection file although the tools use different syntax (`${NAME}`, `${env:NAME}`, `bearer_token_env_var`). Suggested fix: a canonical environment reference that each adapter renders natively.
- `{{NAME}}` values are written in plain text into files that projects usually commit. Suggested fix: a secret-typed placeholder that renders as the tool's own environment reference.

## Next work

Roadmap step S-6.44 carries the two adapted engines above as next local work:
the Baltor preset registry and the optional Agent Harness placement engine,
each with a known-wrong check. The checks are: a connection file must not
contain a key value, a Codex connection must reference the key by variable
name, and a Baltor install must never delete an existing instruction file.
