# Wave 5 generation specification

Kind: generation rules for 75 original harness candidate packages, written by the
wave 5 scout on September 23, 2026. Pinned repository revision:
`a1fc74321912cb9e7d0af7dc5d0ecee24c7081f4` (`origin/main`). The roadmap
(`docs/roadmap/roadmap.yaml`, steps S-6.40, S-6.44, S-6.53 and S-6.54) stays the
only task authority. Nothing in this folder is approved, staged in the service or
published. Every package is a candidate for the repository's independent review
panel: at least three approving reviewers from three model families, none from
the producer's family, and no rejection.

```text
library-wave-5/
├── SPEC.md                 this specification
├── GAP-MATRIX.md           what exists, by family, kind, file class, domain and harness
├── existing-identities.txt every served, candidate and planned identity (3,498)
├── assignments.json        the 15 assignments and their 75 packages
├── check_package.py        the shared executable pre-check every generator runs
├── scout/                  inventory script, inputs, duplicate corpus, checker tests
├── reports/                batch reports written by check-all (created on first run)
└── packages/               the only place generators write
    └── <assignment_id>/<identity>/
```

## 1. Read these before writing

| What | Where (read only) | What it fixes for this wave |
|---|---|---|
| Authoring rules for candidates | `git show origin/main:artifacts/first-party-harness-candidates-2026-09-22/GENERATION-GUIDE.md` | One package is one task method; review note contents; known-wrong case; closest existing item. |
| Earlier waves | `artifacts/first-party-harness-candidates-2026-09-22*/README.md` and `manifest.json` | 80 text skills in data, project and software groups. |
| Mixed-format pilots | `artifacts/harness-intelligence-format-pilot-2026-09-22/` and `-wave-2/` | Step templates with `{{PLACEHOLDERS}}`, skills with tested scripts, a local protocol server that failed in a clean home because it needed a third-party package. |
| Package file contract | `src/loop_engine/core/service_runtime/catalogue_packages.py` | `catalogue_package/v1`: file path, digest, size, media type and role; 13 roles; 64 files; path rules. |
| Proposal contract, newest | `/home/username/.le-codex-build/integration/tools/PREPARE-HARNESS-CANDIDATES.md` and `native_harness_candidates.py` (not yet on `main`) | `harness_candidate_batch_proposals/v2`: complete native packages; output `starter_catalogue_candidate_items/v3`. |
| Native review profile | `/home/username/.le-codex-build/integration/tools/candidate_review/native_prechecks.py` | What the first native profile accepts now and what it holds. See section 13. |
| Pre-checks and criteria | `tools/candidate_review/README.md`, `prechecks/`, `resources/criteria.json`, `resources/REVIEWER-INSTRUCTIONS.md` | Six pre-check kinds, reviewer lenses, the effects rule. |
| Item records | `examples/29_intelligence_service/starter-catalogue/` and `src/loop_engine/core/harness_intelligence.py` | `harness_intelligence_item/v1`; kinds `reusable_code`, `skill`, `tool`, `instruction_file`; families `loop_native`, `harness`, `open_knowledge`. |
| Codex examples | `/home/username/.le-codex-review-20260923/artifacts/focused-step-packet-2026-09-23/` and `harness-plugin-context-2026-09-23/` | A tested step packet (`node_context.md`, `task.json`, contracts, checklist) and a Claude Code plugin whose startup hook ran natively. |
| Placement research | `/home/username/loop-engine/docs/research/HARNESS-FILE-STANDARDS-FLEXIBILITY-2026-09-23.md`, `docs/architecture/HARNESS-WORKING-DIRECTORY-COMPILER-2026-09-23.md`, `/home/username/.le-codex-build/integration/docs/research/HARNESS-PACKAGES-CLAUDE-AND-EDITORS-2026-09-23.md` and `HARNESS-PACKAGES-OPEN-HARNESSES-2026-09-23.md` | Native paths per harness and which ones were observed. See section 6. |
| Measured lesson | `git show origin/main:case-studies/data-cleanup-with-and-without-baltor/REPORT-2026-09-22.md` | Material cost 45 to 446 percent more prompt tokens per step, one prose item made a cheap model worse, and a local 7B model wrote tool calls as text in all 37 steps. |

## 2. Hard rules

1. Write only under `packages/<assignment_id>/<identity>/` in this folder. Never
   modify `/home/username/loop-engine`, `/home/username/loop-engine-main`,
   `/home/username/.le-codex-build/*`, `/home/username/.le-integration/*` or any
   git worktree. Read `main` with `git -C /home/username/loop-engine show origin/main:<path>`.
2. Every file is original text and code written by you, licensed MIT like the
   repository. Never copy text or code from an outside project, including the
   3,251 staged outside candidates. Outside material may only inspire an original
   rewrite. Do not paste documentation passages; describe behavior in your own words.
3. No network use in any package file: no sockets, no HTTP clients, no `curl`,
   `wget`, `pip install`, `git clone`, `git push` or URL fetch in a script, a shell
   block, a hook command or a server command. No remote protocol transport.
4. No secrets or key values anywhere. Name environment variables only. Test data
   that must look like a secret is assembled at run time from fragments so that no
   file at rest matches a secret pattern, and the review note says so.
5. No destructive commands and no model calls from package code. Scripts declare
   their effects in their first docstring line and in `declared_effects`.
6. Nothing is approved here. Do not write the words approved, qualified or
   admitted about your own package. The producer family is `anthropic`.
7. Plain English for second-language readers. No em dash or en dash, no hype, no
   invented facts, no benchmark or benefit claims. Say "unverified" when a harness
   behavior was not observed or documented in a cited file.

## 3. What one package is

A package is one logical method with one identity. The same method rendered for
five harnesses is one package with five variants, not five packages. Tests,
examples and review notes are not extra packages.

Every model-facing entry file must let a fresh harness, run by a small or cheap
model, act without guessing. It states:

- the **first action**, as one concrete command or read;
- the **steps**, numbered, one action each;
- the **checks** and when the step is **done**;
- when to **stop and report** instead of improvising.

Keep the always-loaded text small. The cleanup study above measured the cost of
long material and found no benefit; move every deterministic rule into a tested
script and keep the prose to what the model must decide.

## 4. Folder layout for one package (exact)

```text
packages/<assignment_id>/<identity>/
├── package.json           wave5_candidate_package/v1 (section 5)
├── payload/               the exact delivery bytes; root of the catalogue package
│   ├── ...                harness-neutral files at package-relative paths
│   ├── variants/<harness>/...  files whose bytes must differ for one harness
│   └── LICENSE            byte copy of the repository LICENSE (sha256 663e093e...a46ea)
└── review/
    ├── REVIEW-NOTE.md     producer note (section 10); never delivered
    └── precheck-<UTC>.json  written by check_package.py; keep every one, including failures
```

Nothing else may exist at the package top level. No symbolic links, empty files,
`__pycache__`, `.pyc`, `.log`, `.key`, `.pem`, `.sqlite` or `.db` files. Every
payload file has mode `0644` on disk. Scripts are always started through
`python3`, so no file needs the executable bit.

## 5. package.json

`package.json` wraps exactly one proposal row of the newest proposal contract and
adds a `wave5` block for what that contract does not carry. Write it by hand with
`digest`, `size_bytes` and `package_digest` set to `null`, then run the fill
command, which computes them from the bytes.

```json
{
  "record_type": "wave5_candidate_package/v1",
  "proposal": {
    "id": "parse_dates_by_declared_formats",
    "title": "Parse dates by declared formats",
    "purpose": "Convert a date column to ISO 8601 using only an ordered list of declared formats, and hold every value that no format parses or that two formats read differently, such as 03/04/2025.",
    "sources": ["src/loop_engine/core/service_runtime/catalogue_packages.py"],
    "layer": "code",
    "family": "native_skill_with_scripts",
    "search_tags": ["parse dates", "ambiguous day and month", "iso 8601 dates", "date cleanup"],
    "tags": {"language": ["en"], "domain": ["data cleaning"], "role": ["data analyst"]},
    "symbols": ["main"],
    "declared_effects": ["reads_fs", "spawns_process"],
    "kind": "skill",
    "styles": ["claude_code", "codex", "gemini", "opencode", "pi"],
    "dependencies": ["python>=3.10 standard library only"],
    "producer": {"producer_identity": "Claude Code wave 5 generator a01_data_cleanup_executors",
                 "family": "anthropic", "method_identity": "claude_code_wave5_native_authoring/v1"},
    "files": [
      {"path": "SKILL.md", "digest": null, "size_bytes": null, "media_type": "text/markdown", "role": "skill_definition"}
    ]
  },
  "wave5": {
    "assignment_id": "a01_data_cleanup_executors",
    "file_class": "skill_with_scripts_and_tests",
    "use_cases": ["data_cleanup_without_an_expensive_model"],
    "harness_targets": ["claude_code", "codex", "opencode", "pi", "gemini_cli"],
    "unverified_targets": {},
    "not_placed": {},
    "native_name": "parse-dates-by-declared-formats",
    "version": "0.1.0",
    "entrypoints": {"claude_code": "SKILL.md", "codex": "SKILL.md", "opencode": "SKILL.md", "pi": "SKILL.md", "gemini_cli": "SKILL.md"},
    "placements": {"claude_code": {"SKILL.md": {"destination": ".claude/skills/parse-dates-by-declared-formats/SKILL.md", "operation": "copy_exact_bytes"}}},
    "file_extensions": {"SKILL.md": {"mode": "0644", "license": "MIT", "pickup": "native_discovery", "tested_by": []}},
    "render_placeholders": {},
    "tests": {"command": ["python3", "-I", "-B", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"], "minimum_python": "3.10"},
    "hooks": [],
    "servers": [],
    "first_action": "Run scripts/parse_dates.py on the column with the declared formats and read its JSON summary.",
    "done_when": ["Every value is parsed or listed in the hold report."],
    "stop_and_report_when": ["A declared format list is empty or the input is not UTF-8."],
    "source_revision": "a1fc74321912cb9e7d0af7dc5d0ecee24c7081f4",
    "source_digests": {"src/loop_engine/core/service_runtime/catalogue_packages.py": "05203ed9b332c9098aceef9b880f2335dd11c6dd722beaf070cb739b9fd62d77"},
    "package_digest": null,
    "review_note": "review/REVIEW-NOTE.md",
    "state": "candidate_only",
    "approval_state": "none"
  }
}
```

The example shows one file; a real package lists every payload file in
`proposal.files`, `wave5.file_extensions` and each harness's `placements`.

### 5.1 Field rules

| Field | Rule |
|---|---|
| `proposal.id` | Identity words: lower-case letters, digits and single underscores, at most 64 characters, pattern `[a-z][a-z0-9]*(?:_[a-z0-9]+)*`. Equals the package folder name. Not in `existing-identities.txt`. |
| `proposal.title` | One line, at most 160 characters. It is the first heading of the main entry file. |
| `proposal.purpose` | One line, at most 1,024 characters (aim for 300 or fewer). Also the `description` of a `SKILL.md`. Names the task and when it applies. |
| `proposal.sources` | First entry is always `src/loop_engine/core/service_runtime/catalogue_packages.py` (the package format followed). Add up to 19 related repository files at the pinned revision. Never `LICENSE`. |
| `proposal.layer`, `family`, `kind` | Fixed per file class (table 5.2). |
| `proposal.search_tags` | 1 to 20 distinct phrases a customer would type, each at most 160 characters. |
| `proposal.tags` | Only the dimensions `role`, `domain`, `geography`, `language`, `data_sensitivity`, `authentication`; never `lifecycle` (the preparer adds `candidate`). `language` is `["en"]`. |
| `proposal.declared_effects` | Drawn from `pure`, `reads_fs`, `writes_fs`, `reads_secret`, `spawns_process`; never `network` in this wave. Declare every effect a step tells the reader to perform on their own machine, and `spawns_process` whenever any file has an executable role or the text holds a shell block. A method that only transforms given values declares nothing. |
| `proposal.styles` | The review-profile names of the targets: `claude_code`, `codex`, `opencode`, `pi`, and `gemini` for `gemini_cli`. Targets outside that set (`cursor`, `copilot`, `goose`, `kimi_cli`, `cline`) add no style. |
| `proposal.dependencies` | Python code needs an entry matching `^python(?:3)?(?:[>=~!].*)?$`, for example `python>=3.10 standard library only`. No third-party package. |
| `proposal.files` | Exactly `path`, `digest`, `size_bytes`, `media_type`, `role` per file, as `catalogue_package/v1` defines them. |
| `wave5.harness_targets` | At least two distinct names from `claude_code`, `codex`, `opencode`, `pi`, `gemini_cli`, `cursor`, `copilot`, `goose`, `kimi_cli`, `cline`, and at least two of them placed. |
| `wave5.unverified_targets`, `not_placed` | Harness name to a reason of at least 20 characters. `not_placed` is for a target the class cannot reach there (for example Goose protocol configuration, which is global only). |
| `wave5.placements` | For each placed target, every payload file except other harnesses' variants maps to `{"destination", "operation"}` or to `null` when it is deliberately not placed for that harness (for example `CLAUDE.md` for Codex). Operations: `copy_exact_bytes`, `merge_json_object`, `merge_toml_table`, `compose_instruction_section`, `plugin_directory_binding`. |
| `wave5.file_extensions` | Every payload file: `mode` `"0644"`, `license` `"MIT"`, `pickup` (`native_discovery`, `composed_instruction`, `explicit_invocation`, `registered_event`, `launch_binding`, `referenced_resource`, `licence_notice`) and `tested_by` (payload test paths). |
| `wave5.render_placeholders` | Only task packets and root instruction fragments. Each `{{UPPER_SNAKE}}` marker used in the payload, with a description of what the host fills in. Examples hold no markers. |
| `wave5.tests` | For any package with Python code: exactly the command shown above and `minimum_python` `"3.10"`. Otherwise `null`. |
| `wave5.hooks`, `wave5.servers` | Run specifications (section 8.3 and 8.4). Empty lists otherwise. |
| `wave5.version` | `0.1.0` for a first draft; it equals `metadata.version` in a `SKILL.md`. |

### 5.2 Fixed values per file class

| `wave5.file_class` | `kind` | `layer` | `family` |
|---|---|---|---|
| `skill_with_scripts_and_tests` | `skill` | `code` | `native_skill_with_scripts` |
| `verifier_package` | `skill` | `code` | `native_verifier` |
| `hook_with_script` | `tool` | `code` | `native_hook` |
| `subagent_definition` | `instruction_file` | `context` | `native_subagent` |
| `command_file` | `instruction_file` | `context` | `native_command` |
| `protocol_server_config_local` | `tool` | `code` | `native_protocol_server` |
| `rules_file` | `instruction_file` | `context` | `native_rules_file` |
| `task_packet` | `instruction_file` | `context` | `native_task_packet` |
| `plugin_bundle` | `tool` | `code` | `native_plugin` |
| `settings_fragment` | `tool` | `context` | `native_settings_fragment` |
| `root_instruction_fragment` | `instruction_file` | `context` | `native_instruction_fragment` |

### 5.3 Where this wave extends existing record versions, and why

The newest existing record versions are followed; nothing new is invented inside
them. The wave-local wrapper `wave5_candidate_package/v1` exists because the
strict readers refuse unknown fields, so extensions cannot live in the proposal row.

1. **Proposal row.** `proposal` is exactly one `harness_candidate_batch_proposals/v2`
   row (Codex integration worktree, not yet on `main`) without `content_base64`;
   `check_package.py emit-proposals` adds the base64 content and the batch fields.
2. **Per-harness placement.** Neither the v2 proposal nor `catalogue_package/v1`
   names a destination per harness. The compiler's `native_client_layout_profile/v2`
   is a research draft. `wave5.placements` records the producer's intended
   destination and operation so a reviewer can probe native discovery; it is not
   an authoritative profile.
3. **File mode.** `catalogue_package/v1` has no mode and the body store keeps
   none. All payload files are `0644`, every script is started through `python3`,
   and the mode is recorded in `wave5.file_extensions`.
4. **Per-file licence and pickup.** The proposal carries one batch licence. The
   Codex plugin inventory recorded a licence and pickup per file; this wave keeps
   both per file in `wave5.file_extensions`.
5. **Style names.** Recipe styles name Gemini `gemini_cli`; the first native review
   profile names it `gemini`. `wave5.harness_targets` uses the recipe names and
   `proposal.styles` the review names.
6. **Kind for settings.** No `kind` value names configuration. Settings fragments
   use `tool`, as the pilot connection and the staged registry connections did.
   A new kind value is a record version change for the integrator, not this wave.
7. **Test files.** `FILE_ROLES` has no test role. Tests use `skill_script` in skill
   and verifier packages and `executable_tool` elsewhere.
8. **Run specifications.** `wave5.tests`, `wave5.hooks` and `wave5.servers` let the
   checker execute scripts, hook samples and protocol handshakes. No existing
   record carries them.
9. **Placement operations.** The compiler draft names only exact-byte copying.
   Merging settings files and composing instruction sections are proposed
   operations, named here so conflicts can be reviewed.

## 6. Placement map (research state, not a qualified profile)

One harness is rendered per step. Files that no harness discovers natively go
under `.baltor/`, the folder the public step demonstration already shows
(`.baltor/step.lock.json`):

- support files of a package: `.baltor/<native-name>/...`
- the current step's packet files: `.baltor/step/...`
- state written by hooks: `.baltor/state/<native-name>/...`

Basis: **O** observed on this machine in a recorded probe; **D** documented in a
cited research file; **U** unverified, record it in `unverified_targets`.

| Class | claude_code | codex | opencode | pi | gemini_cli | cursor | copilot | goose | kimi_cli | cline |
|---|---|---|---|---|---|---|---|---|---|---|
| Skill folder | `.claude/skills/<n>/` O | `.agents/skills/<n>/` O | `.opencode/skills/<n>/` O | `.pi/skills/<n>/` O | `.gemini/skills/<n>/` D | `.cursor/skills/<n>/` D | `.github/skills/<n>/` D | none | U | `.cline/skills/<n>/` D |
| Root instruction | `CLAUDE.md` O, its `@AGENTS.md` import D | `AGENTS.md` O | `AGENTS.md` O | `AGENTS.md` O | `GEMINI.md` D | `AGENTS.md` D | `AGENTS.md` D | `AGENTS.md` D | `AGENTS.md` U | `AGENTS.md` D |
| Hook registration | `.claude/settings.json` `hooks` D (plugin hook O) | U | U | none | extension `hooks/hooks.json` D | `.cursor/hooks.json` D | `.github/hooks/<n>.json` D (cloud) | none | U | U |
| Subagent | `.claude/agents/<n>.md` D | none | `.opencode/agent/<n>.md` U | none | `.gemini/agents/<n>.md` U (preview) | U | `.github/agents/<n>.agent.md` U | none | U | none |
| Command or prompt | `.claude/commands/<n>.md` D | none | `.opencode/command/<n>.md` U | none | `.gemini/commands/<n>.toml` D | `.cursor/commands/<n>.md` U | `.github/prompts/<n>.prompt.md` U | none | U | U |
| Protocol server config | `.mcp.json` D (syntax checked) | `.codex/config.toml` `[mcp_servers.<id>]` D (trusted project) | `opencode.json` `mcp` O | none in 0.73.1 | `.gemini/settings.json` `mcpServers` D | `.cursor/mcp.json` U | `.vscode/mcp.json` U | global only | U | U |
| Rules file | `.claude/rules/<n>.md` with `paths` D | none | none | none | none | `.cursor/rules/<n>.mdc` D | `.github/instructions/<n>.instructions.md` with `applyTo` D | none | none | `.clinerules/<n>.md` with `paths` D |
| Settings | `.claude/settings.json` `permissions` D | `.codex/config.toml` keys U for project scope | `opencode.json` `permission` D | none | `.gemini/settings.json` D (key names vary by version, U) | U | none | global only | U | none |
| Plugin | folder bound with `claude --plugin-dir` O | U | JavaScript plugins only, none here | none | extension folder D, local activation U | `.cursor-plugin/plugin.json` D | Agent Plugins 1.0 root `plugin.json` D | none | none | none |

Operations: skills, agents, commands, rules and copies use `copy_exact_bytes`;
`.claude/settings.json`, `.cursor/hooks.json`, `.mcp.json`, `opencode.json`,
`.gemini/settings.json` and `.cursor/mcp.json` use `merge_json_object`;
`.codex/config.toml` uses `merge_toml_table`; `AGENTS.md` sections use
`compose_instruction_section`; plugin folders use `plugin_directory_binding`.
Hook and server commands name the interpreter as `python3 -I -B`; the review note
states that the host must bind a trusted interpreter, because an earlier
independent review showed that a `python3` found first on `PATH` can be replaced.

Do not run harness binaries to test placement. Record the basis you relied on;
the integrator runs native discovery probes later.

## 7. Payload layout, roles and entry shape per file class

Word ranges count words that contain a letter or digit, front matter excluded.
Every Markdown entry starts with `# <Title>` and uses these exact `##` headings.

### 7.1 Skill with scripts and tests; verifier package

```text
payload/
├── SKILL.md                 skill_definition  text/markdown     entry, 120 to 450 words
├── scripts/<name>.py        skill_script      text/x-python     one to three files
├── tests/test_<name>.py     skill_script      text/x-python     at least one per script
├── references/checklist.md  skill_reference   text/markdown     required for verifier_package
├── references/<topic>.md    skill_reference   text/markdown     optional, read on demand
├── examples/<name>.json     skill_asset       application/json  optional, small, synthetic
└── LICENSE                  other             text/plain
```

`SKILL.md` front matter uses only `name`, `description`, `license`,
`compatibility` and `metadata`. The first native profile refuses `allowed-tools`.

```yaml
---
name: "parse-dates-by-declared-formats"
description: "<the proposal purpose, exactly>"
license: MIT
compatibility: "Python 3.10 or later, standard library only."
metadata:
  version: "0.1.0"
---
```

Body headings: `## When to use it`, `## First action`, `## Steps`, `## Checks`,
`## Done when`, `## Stop and report when`, `## Known-wrong example`. A verifier's
script exits 0 for pass, 1 for fail and 2 for refused input, and prints one JSON
object; `references/checklist.md` lists the checks code cannot do. Place the whole
folder under each harness's skill folder with `copy_exact_bytes`.

### 7.2 Hook with script

```text
payload/
├── AGENTS.md                               instruction_file  companion, 40 to 180 words
├── hooks/<name>.py                         hook              one JSON event on stdin, --harness NAME
├── tests/test_<name>.py                    executable_tool
├── examples/<harness>-<event>-<case>.json  other             at least one allowed and one refused sample per harness
├── variants/claude_code/settings.json      configuration     only {"hooks": {...}} -> .claude/settings.json, merge_json_object
├── variants/cursor/hooks.json              configuration     -> .cursor/hooks.json, merge_json_object
├── variants/copilot/<native-name>.json     configuration     -> .github/hooks/<native-name>.json, copy_exact_bytes
└── LICENSE
```

Companion headings: `## What is active`, `## If something is refused`. The script
goes to `.baltor/<native-name>/hooks/<name>.py`. The Claude Code command is
`python3 -I -B "$CLAUDE_PROJECT_DIR/.baltor/<native-name>/hooks/<name>.py" --harness claude_code`.
For Claude Code, a refusal before a tool call prints
`{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "..."}}`
and a blocked finish prints `{"decision": "block", "reason": "..."}`; cite the
Claude Code hook reference in the review note. For Cursor and Copilot, use only
event and field names you can cite from the research files in section 1;
otherwise list the harness in `unverified_targets`. Guards fail closed (malformed
input is refused with a fixed reason); loggers fail open (exit 0 and a diagnostic
on standard error). Read at most 1 MiB of input, finish within 10 seconds, never
echo file contents, never read transcript files, and write state only under
`.baltor/state/<native-name>/` (declare `writes_fs`).

### 7.3 Subagent definition

```text
payload/
├── variants/claude_code/<native-name>.md      subagent_definition  -> .claude/agents/<native-name>.md
├── variants/opencode/<native-name>.md         subagent_definition  -> .opencode/agent/<native-name>.md (U)
├── variants/copilot/<native-name>.agent.md    subagent_definition  -> .github/agents/<native-name>.agent.md (U)
└── LICENSE                                    -> .baltor/<native-name>/LICENSE
```

Each file has its harness's front matter and the same body, 80 to 350 words, with
`## Job`, `## Inputs`, `## Steps`, `## Return format`, `## Refuse when`. Give
read-only helpers only reading tools, and writers only the narrowest writing tool.
The return format is a fixed short JSON or Markdown shape the caller can check.

### 7.4 Command or prompt file

```text
payload/
├── variants/claude_code/<native-name>.md         command  -> .claude/commands/<native-name>.md
├── variants/gemini_cli/<native-name>.toml        command  application/toml -> .gemini/commands/<native-name>.toml
├── variants/opencode/<native-name>.md            command  -> .opencode/command/<native-name>.md (U)
├── variants/copilot/<native-name>.prompt.md      command  -> .github/prompts/<native-name>.prompt.md (U)
├── variants/cursor/<native-name>.md              command  -> .cursor/commands/<native-name>.md (U)
└── LICENSE
```

Body 60 to 350 words with `## Purpose`, `## First action`, `## Steps`, `## Output`,
`## Stop and report when`. A Gemini TOML file holds `description` and a `prompt`
string that contains the same headings. A command works without arguments by
reading the known step files under `.baltor/step/`; optional arguments use each
harness's documented marker.

### 7.5 Protocol server configuration with a tiny local server

```text
payload/
├── AGENTS.md                              instruction_file  companion, 40 to 180 words
├── server/<identity>.py                   executable_tool   single file, standard library, stdio
├── tests/test_<identity>.py               executable_tool   scripted client
├── contracts/<tool>.input.schema.json     configuration     application/schema+json, one per tool
├── examples/<tool>-arguments.json         other             sample call arguments
├── variants/claude_code/.mcp.json         protocol_server_configuration  -> .mcp.json
├── variants/codex/config.toml             protocol_server_configuration  application/toml -> .codex/config.toml
├── variants/opencode/opencode.json        protocol_server_configuration  -> opencode.json
├── variants/gemini_cli/settings.json      protocol_server_configuration  -> .gemini/settings.json
├── variants/cursor/mcp.json               protocol_server_configuration  -> .cursor/mcp.json
└── LICENSE
```

The server file goes to `.baltor/<native-name>/server/<identity>.py`; each config
names the server key `<identity>` and starts `python3` with
`["-I", "-B", ".baltor/<native-name>/server/<identity>.py", "--root", "."]`.
Record in the review note that the relative path assumes the harness starts the
server in the workspace root. Protocol requirements:

- newline-delimited JSON-RPC 2.0 on standard input and output; diagnostics only on
  standard error; exit when input closes;
- `initialize` answers `protocolVersion` equal to the client's value when it is one
  of `2025-11-25`, `2025-06-18` or `2025-03-26`, otherwise `2025-11-25`, with
  `capabilities.tools` and `serverInfo`; never claim `2026-07-28`;
- `notifications/initialized` gets no answer; `ping` answers `{}`;
- `tools/list` returns each tool's `name`, `description` and `inputSchema`, equal to
  its contract file (a test asserts equality);
- `tools/call` returns `content` with one text item holding compact JSON, plus
  `structuredContent`, and `isError: true` for a tool-level refusal;
- unknown method `-32601`, invalid parameters `-32602`, unreadable JSON `-32700`;
- every file path is resolved under `--root` without following a symbolic link out
  of it; input lines and outputs are bounded (1 MiB in, 256 KiB out).

### 7.6 Rules file

```text
payload/
├── variants/cursor/<native-name>.mdc                  instruction_file  -> .cursor/rules/<native-name>.mdc
├── variants/copilot/<native-name>.instructions.md     instruction_file  -> .github/instructions/<native-name>.instructions.md
├── variants/cline/<native-name>.md                    instruction_file  -> .clinerules/<native-name>.md
├── variants/claude_code/<native-name>.md              instruction_file  -> .claude/rules/<native-name>.md
└── LICENSE                                            -> .baltor/<native-name>/LICENSE
```

Front matter: Cursor uses plain `key: value` lines `description`, `globs` (comma
separated, unquoted) and `alwaysApply: false`; Copilot uses `applyTo`; Cline and
Claude Code use a `paths` list. The body is identical across variants, 40 to 250
words, with `## Rule`, `## Applies to`, `## Instead`, `## Stop and report when`.

### 7.7 Task packet for one focused step

```text
payload/
├── AGENTS.md                    instruction_file  entry with {{PLACEHOLDERS}}, 150 to 450 words
├── CLAUDE.md                    instruction_file  exactly "@AGENTS.md" and a newline (claude_code target)
├── GEMINI.md                    instruction_file  byte copy of AGENTS.md (gemini_cli target)
├── references/node_context.md   skill_reference   -> .baltor/step/node_context.md
├── references/checklist.md      skill_reference   -> .baltor/step/checklist.md
├── contracts/task.json          other             node_assignment/v3 -> .baltor/step/task.json
├── contracts/input.schema.json  configuration     -> .baltor/step/contracts/input.schema.json
├── contracts/output.schema.json configuration     -> .baltor/step/contracts/output.schema.json
├── examples/input.json          other             filled synthetic input, no markers
├── examples/output.json         other             the expected output for that input
└── LICENSE
```

`AGENTS.md` headings: `## Assignment`, `## First action`, `## Steps`, `## Done when`,
`## Stop and report when`, `## Files`, `## Authority`. The Authority section says
the file grants no authority and names the effects the host must supply.
`node_context.md` headings: `## Objective`, `## Relevant context`, `## Current state`,
`## Contracts and input`, `## Acceptance`. `checklist.md` headings: `## Before work`,
`## Before handoff`, each a list of `- [ ]` items. `task.json` has exactly the
`node_assignment/v3` fields of `src/loop_engine/core/node_provisioning.py`:
`record_type`, `node_id`, `kind` (`reason` or `build`), `objective`,
`output_contract_refs`, `dependency_ids`, `required_capabilities`, `effects`,
`harness_style`, `model_calls_authorized` (a JSON boolean) and `mode`
(`deterministic`, `hybrid` or `non_deterministic`). Markers look like
`{{TICKET_PATH}}`; the host must render every marker before launch and refuse a
file that still holds one (the pilot's `unrendered_step_input` rule). Schemas use
draft 2020-12 and local references only. Map `CLAUDE.md` and `GEMINI.md` to `null`
for harnesses that do not read them.

### 7.8 Plugin bundle

A plugin wires at least two component classes besides its manifest. Its
components must not restate a method assigned to another wave 5 package. Each
plugin package has its own pair of harness targets in `assignments.json`, and both
are placed: the second is a native variant (a Cursor plugin, a Gemini CLI
extension or a portable Agent Plugins manifest), not a copy of the first.

```text
payload/
├── variants/claude_code/.claude-plugin/plugin.json   plugin_manifest
├── variants/claude_code/hooks/hooks.json             configuration     uses ${CLAUDE_PLUGIN_ROOT}
├── variants/claude_code/scripts/<name>.py            hook, executable_tool or skill_script
├── variants/claude_code/commands/<name>.md           command
├── variants/claude_code/agents/<name>.md             subagent_definition
├── variants/claude_code/skills/<name>/SKILL.md       skill_definition
├── tests/test_<name>.py                              executable_tool
├── examples/<name>.json                              other
└── LICENSE
```

Place the plugin folder at `.baltor/plugins/<native-name>/` with
`plugin_directory_binding`; the Claude Code activation is
`claude --plugin-dir .baltor/plugins/<native-name>` (observed for 2.1.280). A
Gemini CLI extension uses `variants/gemini_cli/gemini-extension.json`, its context
file and `commands/*.toml`. An Agent Plugins 1.0 package keeps its portable root
`plugin.json`, `skills/<name>/SKILL.md` and `mcp.json` at the payload root. Record
each harness's activation step and its verification basis.

### 7.9 Settings or permission fragment

```text
payload/
├── AGENTS.md                              instruction_file  companion, 40 to 180 words
├── variants/claude_code/settings.json     configuration  -> .claude/settings.json, merge_json_object
├── variants/codex/config.toml             configuration  application/toml -> .codex/config.toml, merge_toml_table
├── variants/opencode/opencode.json        configuration  -> opencode.json, merge_json_object
├── variants/gemini_cli/settings.json      configuration  -> .gemini/settings.json, merge_json_object
├── tests/test_<identity>.py               executable_tool  parses every variant and asserts the policy
└── LICENSE
```

One package is one policy. Where a harness cannot express the policy, put it in
`not_placed` with the reason. The test must fail on a known-wrong variant, for
example one that allows the network or a write outside the declared folders. Do
not name credential file paths literally in deny lists (the safety pre-check
refuses them); use patterns such as `**/.env*`, `**/*.pem` and `**/*.key`.

### 7.10 Root instruction fragment

```text
payload/
├── AGENTS.md    instruction_file  80 to 350 words: ## Applies when, ## Rules, ## If a rule blocks the work
├── CLAUDE.md    exactly "@AGENTS.md" and a newline (claude_code target)
├── GEMINI.md    byte copy of AGENTS.md (gemini_cli target)
└── LICENSE      -> .baltor/<native-name>/LICENSE
```

`AGENTS.md` is a composable section: `compose_instruction_section` into the
step's `AGENTS.md`. Rules are numbered, one instruction each. A fill-in fragment
declares its markers in `render_placeholders`.

## 8. Code rules

### 8.1 Scripts

- Python 3.10 or later, standard library only, one file per script where
  possible. With `-I` the script folder is not on the import path; load a helper
  by its exact adjacent path with `importlib.util` if one is needed.
- Input from named paths or standard input; output one JSON object on standard
  output; exit 0 success, 1 check failed, 2 refused input. Bound every input
  (default 64 MiB for data files, 1 MiB for events) and refuse, never truncate.
- No `eval`, `exec`, `compile`, `__import__` or `importlib.import_module`; no
  sockets, HTTP, `subprocess` in product scripts unless the method needs it
  (tests may use `subprocess` with `sys.executable`).
- Resolve paths under a declared root, refuse `..`, absolute paths outside the
  root and symbolic links that leave it.
- Avoid the words in section 9.4 in comments and strings too.

### 8.2 Tests

- `tests/test_*.py`, standard `unittest`, run from the payload root with
  `python3 -I -B -m unittest discover -s tests -p 'test_*.py' -v`.
- Locate scripts from the test file: `Path(__file__).resolve().parent.parent / "scripts" / "<name>.py"`,
  and run them with `subprocess.run([sys.executable, "-I", "-B", str(path)], ...)`.
- Each script has a positive case and the package's known-wrong case. Name every
  script file in at least one test file.
- Tests must not write outside a `tempfile.TemporaryDirectory()`; prefer data on
  standard input. Any file write in a test counts as `writes_fs` for the package.
- Tests pass under Python 3.14 and 3.10 in a sandbox with no network and a
  read-only package folder unless `writes_fs` is declared.

### 8.3 Hook run specification (`wave5.hooks`)

```json
{"harness": "claude_code", "event": "PreToolUse", "script": "hooks/guard_shell.py",
 "arguments": ["--harness", "claude_code"], "environment": {"CLAUDE_PROJECT_DIR": "{WORKSPACE}"},
 "samples": [{"input": "examples/claude_code-pretooluse-allowed.json", "expect_exit": 0,
              "expect_stdout_json": true, "expect_stdout_contains": []},
             {"input": "examples/claude_code-pretooluse-refused.json", "expect_exit": 0,
              "expect_stdout_json": true, "expect_stdout_contains": ["\"permissionDecision\": \"deny\""]}]}
```

`{WORKSPACE}` becomes the sandbox copy of the payload.

### 8.4 Server run specification (`wave5.servers`)

```json
{"name": "csv_profile_server", "script": "server/csv_profile_server.py", "arguments": ["--root", "examples"],
 "tools": ["profile_csv"], "protocol_versions": ["2025-11-25", "2025-06-18"],
 "sample_call": {"tool": "profile_csv", "arguments": {"path": "people.csv"}, "expect_is_error": false}}
```

`--root` in a run specification is resolved inside the sandbox copy of the payload.
A sample call may exercise a refusal (`"expect_is_error": true`) when its data
cannot ship as text; for example, the SQLite server's tests build their database
in a temporary directory (declare `writes_fs`) and its sample call names a missing file.
Server packages may ship small synthetic CSV samples under `examples/` with media
type `text/csv`; the checker warns because the first native review profile holds
CSV bytes, and server packages are held by that profile in any case.

## 9. Writing rules

### 9.1 Words and size

| Limit | Target | Hard |
|---|---|---|
| Files in one payload | 32 | 64 |
| One file | 64 KiB | 256 KiB |
| One payload | 512 KiB | 2 MiB |
| Identity and native name | | 64 characters |
| Title / purpose | | 160 / 1,024 characters (purpose target 300) |
| Entry files | the ranges in section 7 | same |

### 9.2 Naming

- Identity: `snake_case` words as in 5.1. Native name: the identity with every
  `_` replaced by `-`. A skill folder, a subagent file, a command file, a rules
  file and a plugin name all use the native name. The Agent Skills version lives
  in `metadata.version`, never in the name.
- Protocol server keys and hook state folders use the identity.
- Payload file names: lower case, digits, `_` for Python files, `-` elsewhere.

### 9.3 Style

Plain English, short sentences, direct instructions to the model. Examples use
synthetic data only; never a real person, company, ticket system record or
dataset. No em dash, en dash or horizontal bar. No HTML comments. No text that
tells the reader to ignore earlier instructions or to approve anything.

### 9.4 Words refused in payload files

The checker refuses these in every payload file (the starter format rules): loop
or loops, practitioner, role profile, runtime classification, solution canvas,
code node, spawn and its forms, starting solution, run history, runtime memory
or history, context, code, solution or feedback intelligence, intelligence items,
queries or layers, child or children, grandchild, stop condition, receipt,
chronicle, and "what next". Say "subprocess", "repeat", "each item", "when to stop".

## 10. Review note (`review/REVIEW-NOTE.md`)

At least 250 words, never delivered, never a claim of approval. It contains the
sentence `Candidate only. Not approved, staged, served or published.` and these
headings: `## Method`, `## Authoring basis and sources`, `## Inputs and outputs`,
`## Effects`, `## Closest existing items`, `## Positive example`,
`## Known-wrong example`, `## Harness placement and verification state`,
`## Customer requests`, `## Limits`. Name the closest existing items (start from
`closest_existing` in `assignments.json` and search `scout/existing-inventory.tsv`),
state the behavioral difference, list two or three requests in a customer's own
words, list every unverified harness behavior, and record any check that failed
before it passed.

## 11. Order of work for one generator

1. Read your assignment in `assignments.json`: its file class, targets, the five
   identities, titles and purposes, and each package's `closest_existing`.
2. For each package, search `scout/existing-inventory.tsv` and the bodies named
   there; confirm the behavioral difference before writing anything.
3. Write the payload files for the class (section 7), then the review note.
4. Write `package.json` with `null` digests, sizes and package digest; run `fill`.
5. Run `check`; read every refusal and warning; repair; run `fill` and `check`
   again. Keep every report. Do not weaken a test to make it pass.
6. When all five pass, run `check-all --assignment <assignment_id>`.
7. Report what passed, what stayed refused and why, and every unverified harness
   behavior. Commit nothing and copy nothing into the repository.

## 12. Pre-checks every generator must run

Set `WAVE=/tmp/claude-1000/-home-username-loop-engine/4d86b429-7c1c-493e-b03d-37b529827fe7/scratchpad/grow/library-wave-5`
and `PKG=$WAVE/packages/<assignment_id>/<identity>`.

```bash
python3 $WAVE/check_package.py fill  $PKG     # digests, sizes and the package digest
python3 $WAVE/check_package.py check $PKG     # every check below; writes review/precheck-<UTC>.json
```

A package is ready when its newest report has `"passed_for_wave_gate": true` for
the current `package_digest`. `--skip-runs` never passes the gate. Keep every
failing report beside its successor. After all packages of an assignment pass:

```bash
python3 $WAVE/check_package.py check-all --assignment <assignment_id>   # your five packages and the plan
python3 $WAVE/check_package.py check-all     # the whole wave, run by the integrator
```

| Check | What refuses the package | Equivalent command |
|---|---|---|
| `layout` | Missing files, extra top-level entries, symbolic links, empty or cache files | `find $PKG -type l -o -empty` |
| `manifest_schema` | Field set, class values, styles, effects, producer, pinned sources | `git -C /home/username/loop-engine show a1fc7432:<source> \| sha256sum` |
| `identity` | Pattern, length, folder name, collision with `existing-identities.txt` | `grep -Fx <identity> $WAVE/existing-identities.txt` |
| `inventory` | Undeclared or changed bytes, unsafe paths, sizes, media and role, mode 0644, LICENSE bytes, package digest | `sha256sum`, `stat -c %a` |
| `text_hygiene` | Not UTF-8, carriage returns, byte order mark, control or invisible characters, missing final newline | |
| `vocabulary` | Words of section 9.4, em and en dashes | |
| `safety_static` | HTML comment, instruction override, pipe to shell, destructive command, credential paths | rules of `tools/candidate_review/prechecks/safety_rules.py` |
| `secrets` | The repository secret patterns plus the panel's extra shapes, in every file of the package | |
| `parse` | JSON (duplicate keys and `NaN` refused), TOML, YAML and front matter, JSON Schema 2020-12 with local references, Python syntax | `python3 -c 'import json,sys; [json.load(open(f)) for f in sys.argv[1:]]' FILES`; `python3 -c 'import tomllib,sys; [tomllib.load(open(f,"rb")) for f in sys.argv[1:]]' FILES`; `python3 -c 'import yaml,sys; [yaml.safe_load(open(f)) for f in sys.argv[1:]]' FILES` |
| `entry_shape` | Headings and word ranges of section 7, `SKILL.md` front matter, `CLAUDE.md` and `GEMINI.md` rules, `task.json` fields, placeholders | |
| `placements` | Unplaced files, unsafe or colliding destinations, fewer than two placed targets | |
| `effects` | An effect found in code or a shell block that is not declared; imports outside the standard library; dynamic code | |
| `network_static` | Network imports, network commands in shell blocks and command values, remote transports | `grep -rnE 'socket\|urllib\|http\.client\|requests\|httpx\|curl \|wget ' $PKG/payload` |
| `agent_skills_validator` | Either Agent Skills validator refusing a `SKILL.md` folder copied under its native name | `/home/username/.le-ci-tmp/research/compilers/validator/.venv-pypi/bin/agentskills validate DIR` and `/home/username/.le-ci-tmp/research/compilers/validator/.venv-official/bin/skills-ref validate DIR` |
| `duplicates` | Five-word shingle similarity of 0.8 or more with 225 existing bodies or another wave 5 package (0.5 or more is a warning) | |
| `review_note` | Section 10 | |
| `tests_run` | Any failing or missing test, under Python 3.14 and 3.10, in Bubblewrap with no network and a read-only package unless `writes_fs` | `bwrap --ro-bind /usr /usr --symlink usr/lib /lib --symlink usr/lib64 /lib64 --symlink usr/bin /bin --proc /proc --dev /dev --tmpfs /tmp --ro-bind PAYLOAD_COPY /work --chdir /work --unshare-net --unshare-pid --unshare-ipc --unshare-uts --die-with-parent --clearenv --setenv PATH /usr/bin:/bin --setenv HOME /tmp /usr/bin/python3 -I -B -m unittest discover -s tests -p 'test_*.py' -v` |
| `hooks_run` | A hook sample with another exit status or output, run in a temporary sandbox copy with its sample on standard input | the same `bwrap` prefix with `--bind PAYLOAD_COPY /work` and `/usr/bin/python3 -I -B hooks/<name>.py --harness claude_code < examples/<sample>.json` |
| `servers_run` | A failed `initialize`, `tools/list`, `tools/call` or unknown-method error through standard input and output | the same `bwrap` prefix with the server command |

The checker's own controls: `python3 $WAVE/scout/test_check_package.py` (19 cases)
and `python3 $WAVE/scout/test_packet_fixture.py` (2 cases); each known-wrong case
must be refused by its named check, and all 21 passed at scout time. The checker reads contracts from
`/home/username/loop-engine-main/src` and falls back to literal copies of the
`origin/main` values.

## 13. What the first native review profile does with each class

The Codex native review profile (`native_prechecks.py`, format rules version 2)
accepts root `AGENTS.md`, `CLAUDE.md` and `GEMINI.md`, a root `SKILL.md`, Python
with executable roles, supporting files under `examples/`, `verification/`,
`references/`, `assets/` and `contracts/`, JSON Schema contracts, strict JSON data
and the licence notice. It holds hooks, commands, subagents, plugin manifests,
protocol server configurations, activation folders such as `.claude/` or
`variants/.../settings.json`, and styles outside `codex`, `claude`, `claude_code`,
`opencode`, `pi` and `gemini`.

| Reviewable by the first native profile | Held until a versioned profile extension |
|---|---|
| a01, a02, a03 skills; a12, a15 verifiers; a09, a10 task packets; a14 fragments | a04 hooks; a05 subagents; a06 commands; a07 protocol servers; a08 rules; a11 plugins; a13 settings |

Held packages are still generated, fully checked here and kept as candidates.
They are the material for the profile extension that roadmap step S-6.44 needs.

## 14. Duplicates and boundaries between assignments

- `existing-identities.txt` holds 3,498 identities: 43 served, 80 starter
  candidates, 89 first-party wave and pilot candidates, 13 Codex candidates not
  yet merged, 20 planned Codex methods, 2 example packets and 3,251 staged
  outside candidates. `scout/existing-inventory.tsv` adds titles, classes and domains.
- These wave 5 pairs must stay behaviorally distinct; each review note says how:
  `build_group_stratified_folds` builds folds, `verify_fold_group_separation`
  checks any fold file; `ticket_reproduction_packet` creates a failing test, the
  pilot `repair_one_failing_test` repairs an existing one; `write_step_handoff`
  writes one step's handoff, `morning_report_packet` compiles a night and
  `verify_morning_report_claims` checks one; `raw_data_stays_read_only` is a rule,
  `cleaning_apply_packet` is a step and `verify_cleaned_copy_change_log` is a
  check; `honest_test_changes` prevents and `detect_weakened_test_assertions`
  detects; `repository_scout` answers questions by reading, `map_repository_layout`
  prints a map and neither ranks files for a ticket.
- A plugin's components restate no other wave 5 package.

## 15. After generation (not the generator's job)

The integrator runs `check-all`, then
`python3 $WAVE/check_package.py emit-proposals --output NEW_FILE` to write one
`harness_candidate_batch_proposals/v2` document. Its `source_revision` must equal
the checkout's `HEAD` for the Codex preparer, so a moved `main` needs a successor
document pinned to the new revision. Preparation, staging, the native review
profile, the family-quorum panel and the host release remain separate steps
under the repository's existing contracts. None of them is implied by a pass here.

## 16. The 15 assignments

Full titles, purposes and closest existing items are in `assignments.json`.

| Id | File class | Domain | Harness targets | Packages |
|---|---|---|---|---|
| a01_data_cleanup_executors | skill with scripts and tests | data cleaning | claude_code, codex, opencode, pi, gemini_cli | parse_dates_by_declared_formats, parse_numbers_by_declared_separators, map_categories_by_reviewed_table, standardize_missing_value_tokens, flag_outliers_by_median_deviation |
| a02_competition_modeling_tools | skill with scripts and tests | data science | claude_code, codex, opencode, pi, gemini_cli | build_group_stratified_folds, build_time_ordered_splits, audit_train_test_drift, target_encode_out_of_fold, rank_experiments_by_fold_scores |
| a03_ticket_work_tools | skill with scripts and tests | software change | claude_code, codex, opencode, pi, gemini_cli | extract_ticket_acceptance_criteria, map_repository_layout, extract_test_failures, select_tests_for_changed_files, detect_text_written_tool_calls |
| a04_unattended_guard_hooks | hook with script | harness operations | claude_code, cursor, copilot | guard_shell_command_allowlist, guard_workspace_file_writes, require_tests_before_stop, log_tool_activity, cap_tool_call_budget |
| a05_focused_subagents | subagent definition | harness operations | claude_code, opencode, copilot | repository_scout, test_run_summarizer, data_sample_inspector, leakage_reviewer, changelog_writer |
| a06_step_ritual_commands | command file | harness operations | claude_code, gemini_cli, opencode, copilot, cursor | write_step_handoff, plan_night_queue, record_blocker, night_preflight, pick_next_experiment |
| a07_local_data_tool_servers | protocol server config with local server | data cleaning | claude_code, codex, opencode, gemini_cli, cursor | csv_profile_server, csv_row_sampler_server, sqlite_readonly_server, json_schema_check_server, pattern_tester_server |
| a08_path_scoped_rules | rules file | repository conventions | cursor, copilot, cline, claude_code | generated_files_stay_unedited, raw_data_stays_read_only, reproducible_competition_notebooks, honest_test_changes, applied_migrations_stay_unchanged |
| a09_ticket_step_packets | task packet | software change | codex, claude_code, opencode, pi, gemini_cli, goose | ticket_triage_packet, ticket_reproduction_packet, ticket_fix_verification_packet, interrupted_step_resume_packet, morning_report_packet |
| a10_data_and_competition_step_packets | task packet | data and competition | codex, claude_code, opencode, pi, gemini_cli, kimi_cli | cleaning_plan_packet, cleaning_apply_packet, competition_brief_packet, baseline_training_packet, submission_assembly_packet |
| a11_session_plugins | plugin bundle | session kits | claude_code, gemini_cli, cursor, copilot | overnight_ticket_plugin, data_cleanup_plugin, competition_plugin, step_status_plugin, portable_step_packet_plugin (each with its own pair of targets) |
| a12_ticket_result_verifiers | verifier package | software change | claude_code, codex, opencode, pi, gemini_cli | verify_fail_then_pass_evidence, check_diff_allowed_paths, detect_weakened_test_assertions, verify_criteria_have_evidence, verify_morning_report_claims |
| a13_unattended_permission_settings | settings fragment | security | claude_code, codex, opencode, gemini_cli | read_only_investigation_settings, workspace_write_no_network_settings, test_commands_only_settings, data_step_scoped_write_settings, deny_env_file_reads_settings |
| a14_root_instruction_fragments | root instruction fragment | harness operations | codex, claude_code, gemini_cli, goose, opencode, pi, kimi_cli | unattended_run_rules, project_commands_fragment, small_working_context_rules, unattended_git_rules, focused_step_packet_rules |
| a15_data_and_competition_verifiers | verifier package | data and competition | claude_code, codex, opencode, pi, gemini_cli | check_csv_column_contract, verify_cleaned_copy_change_log, verify_fold_group_separation, recompute_claimed_cv_score, validate_submission_file |

Kimi CLI and Goose placements are unverified or global only; list them in
`unverified_targets` or `not_placed` with the reason, and keep at least two other
targets placed.
