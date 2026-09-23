# Harness file standards: the differences, and how to absorb them

Consolidation status: supplied design draft, with source bytes preserved in
[the supplied-note inventory](../../artifacts/harness-file-standards-supplied-2026-09-23/inventory.json).
The [profile and handshake review](HARNESS-AGENT-COMPILER-PROFILES-AND-HANDSHAKES-2026-09-23.md)
qualifies the claims below. Path construction is a local type exercise, not
native discovery or a completed compiler. Source-described capabilities and
observed capabilities must remain separate. The terminology and schema names
in the later review govern implementation; this draft is prior design input.

Kind: dated design and verified-standards record, September 23, 2026 local
time. It extends [the file-kinds and admission research](HARNESS-INTELLIGENCE-FILE-KINDS-AND-ADMISSION-2026-09-22.md),
[the placement research](NATIVE-HARNESS-INTELLIGENCE-PLACEMENT-2026-09-22.md),
and the agent-harness review; it does not replace their runtime classification
or their candidate-only state. Facts below were verified against the official
documentation and, where noted, the installed tool on this machine. Nothing
here publishes, grants or qualifies a file for a customer.

The [roadmap](../roadmap/roadmap.yaml) stays the task authority.

## The core problem

A harness is not one fixed layout. The same logical thing , "give this step its
instructions" or "install this skill" , is expressed differently in every tool,
and a library that assumes one shape will silently produce a directory that a
customer's harness never reads. The library must therefore describe material by
what it is, and resolve the per-harness shape at placement time from declared,
versioned profiles , never by guessing from a filename.

```text
One item, harness-flexible placement
├── a versioned capability record (what the material is, its family, kind,
│   digest, effects, licence, and the item identity)
└── resolved into a per-harness placement plan
    ├── the harness's profile record names the native path for that kind,
    │   the load rule, the precedence, and the trust requirement
    ├── the rendered files land exactly there, at exact digests
    └── a native probe confirms discovery before the step may claim loading
```

## The verified differences the design must absorb

These are the deltas that make a fixed layout break. Every row was confirmed
against the installed version shown, or the official documentation of it.

### 1. The instruction file: same concept, different name, discovery and precedence

| Harness (version) | Instruction file | Discovered where | Precedence |
|---|---|---|---|
| Codex 0.155.1 | `AGENTS.md`, or `AGENTS.override.md`, or a name listed in `project_doc_fallback_filenames` | Global `~/.codex/AGENTS.md` first, then each directory from the project root down to cwd (one candidate per directory) | Global first, then root-to-cwd, closer later; a fallback name is tried *only* when no `AGENTS.md`/`AGENTS.override.md` exists in that directory |
| Claude Code 2.1.280 | `CLAUDE.md`, `CLAUDE.local.md`; `.claude/rules/**/*.md` is a *separate* class; `AGENTS.md` only when no `CLAUDE.md` in the ancestry | Every directory from the working directory's ancestors down to cwd, plus user and managed scopes | Concatenated broadest-to-closest; `rules/` load as their own class with per-file `paths` gating |
| OpenCode 1.18.32 | `AGENTS.md` | Working directory root | Single root file |
| Gemini CLI 0.59.0 | `GEMINI.md` (name configurable via `context.fileName`, which may list several) | Global, workspace and parent directories, and just-in-time subdirectory files when tools touch them | All tiers concatenated, global first |
| Goose 1.50.0 | `.goosehints` and `AGENTS.md` (both loaded, both default) | Git root down to cwd, plus global config dirs | Both defaults concatenated; local wins over global on conflict |
| Aider 0.86.2 | None auto-loaded. `CONVENTIONS.md` is opt-in only | None | Loaded only by `read:` in `.aider.conf.yml` or `--read` |

Consequence for the design: a step's brief cannot be "the instruction file".
It is content the placement plan renders into whichever file the target
harness actually loads, at that harness's precedence slot. For Aider there is
no such native hook , the plan must use `.aider.conf.yml`'s `read:` key or
accept that instructions are opt-in there.

### 2. Skills: same shape, different root and precedence

All of these accept the open `SKILL.md` package shape (YAML frontmatter over a
Markdown body, with `scripts/` , `references/` , `assets/` subfolders read on
demand). The native root and the precedence differ:

| Harness | Project skill root | User skill root | Precedence note |
|---|---|---|---|
| Claude Code | `.claude/skills/<name>/SKILL.md` | `~/.claude/skills/` | User before project; plugins namespaced; a skill beats a same-named slash command |
| Codex 0.155.1 | `$cwd/.agents/skills/<name>/SKILL.md` (and parents to root) | `~/.agents/skills/` | User, system, plugin caches, then repository; no name merge |
| OpenCode | `.opencode/skills/<name>/SKILL.md` | isolated home | Root file + scoped home |
| Gemini CLI | `.gemini/skills/`, `.agents/skills/` | `~/.gemini/skills/`, `~/.agents/skills/` | Built-in < extension < user < workspace |
| Goose | plugins supply `~/.agents/plugins/*/skills/` | per-session `goose skills` | On demand |

A single packaged skill is harness-flexible: the library stores one approved
package and the placement plan copies it to the target harness's root for that
version, at exact digests. What is *not* portable is the assumption that a user
skill overrides a project skill, or vice versa; that is per-harness policy.

### 3. Tool / protocol configuration: where it lives and how it is trusted

| Harness | Configuration file | Tool / protocol declaration |
|---|---|---|
| Codex 0.155.1 | `~/.codex/config.toml`, plus trusted project `.codex/config.toml` (root-to-cwd, closest wins) | `[mcp_servers.<name>]` blocks; plugins via marketplaces |
| Claude Code 2.1.280 | managed > CLI > local `.claude/settings.local.json` > project `.claude/settings.json` > user `~/.claude/settings.json` | project `.mcp.json` prompts for approval; hooks merge across every level and managed hooks cannot be disabled |
| Gemini CLI 0.59.0 | `/etc` system, `~/.gemini/settings.json`, `<project>/.gemini/settings.json` | `mcpServers` merge across files; settings.json wins over an extension manifest on name conflict |
| Goose 1.50.0 | `/etc/goose/config.yaml`, `GOOSE_ADDITIONAL_CONFIG_FILES`, `~/.config/goose/config.yaml` (no per-project config) | `extensions:` in config.yaml; types builtin/platform/stdio/streamable_http |
| OpenCode 1.18.32 | `work/opencode.json` | protocol servers and settings in that file; executable plugins in `.opencode/plugins/` |
| Aider 0.86.2 | `.aider.conf.yml` (home < git root < cwd; `--config` overrides all) | no native protocol surface; models and read-only files via config |

The sharp edges for a customer step:

- Claude hooks **merge** across scopes and cannot be narrowed by a project ,
  so a hosted placement cannot promise "only my hooks". The placement record
  must name scope explicitly.
- Codex replaces its built-in instructions wholesale with
  `model_instructions_file`, and `instructions` is a reserved, inert key , a
  config written for one key name will not do what it looks like on another.
- Goose has **no** per-project config file; a project-level harness
  configuration for Goose is a hints/recipe concern, not a config.yaml.

### 4. The opt-in only classes (do not assume a discovery path)

- Codex custom slash commands do not exist as a drop-in directory; prompts are
  invoked through `$skill` mentions and `codex plugin` , a slash-command file
  in a step root is just a file.
- Aider never auto-reads a Markdown instruction.
- Goose recipes are resolved by name when asked, never auto-loaded.
- Gemini commands are TOML, project-over-user, namespaced by subdirectory.

## What this means for the library

- Describe material by kind and family, with a versioned digest, licence,
  declared effects and an item identity , the shape `harness_intelligence.py`
  already holds.
- Bind each item to a **harness profile record** at placement: the native
  path for each kind, the load rule, the precedence, the trust requirement
  and the observed version.
- The placement record maps item identity and digest to each rendered path
  and digest, and refuses an unsupported kind or version before any effect.
- Probe natively for discovery; never claim loading from a filename alone.

## Current state, future state, evolution vectors

- **Current:** the family/kind records and the four-layer open folders are
  on main; the candidate pilots and the madebywild prior-art review exist;
  the per-harness profiles above are research, not yet a typed registry.
- **Future:** a versioned `HarnessFileProfile record (harness_file_profile/v1)` per supported harness and
  version (instruction placement, skill placement, config placement, trust,
  probe), and a `PlacementPlan record (placement_plan/v1)` compiled per step from selected items and
  the chosen harness profile. This is the placement contract S-6.61/6.62/6.44
  ask for, and it absorbs the deltas above without a second runtime.
- **Evolution vectors:** (1) add the profile records as data under the
  catalogue, one per harness version, so a new harness or a version change is
  a new record, never a code change to the serving path; (2) extend the
  placement builder to resolve an item's kind through the profile rather than
  a hardcoded path; (3) add the native probes as admission checks so "file
  placed" is never read as "file loaded"; (4) keep every rule host-declared
  and versioned, so the flexibility lives in data, not in conditionals.
