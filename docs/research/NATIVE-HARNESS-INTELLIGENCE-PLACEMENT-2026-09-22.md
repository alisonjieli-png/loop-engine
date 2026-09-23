# Where selected intelligence belongs in each fresh harness

Kind: dated placement research and proposed checks. Prepared September 22,
2026 from the [native instance experiment](HARNESS-INDEPENDENT-INSTANCES-2026-09-22.md),
the installed clients and their official documentation. The
[roadmap](../roadmap/roadmap.yaml) remains the task authority, especially
S-6.44, S-6.42, S-6.61 and S-6.62. This report proposes a layout contract;
it does not qualify every file kind or publish the new candidate batch.

## Answer

Yes. **Each selected file kind has a preferred native destination for the
exact harness and version used by that step.** A fresh working directory is
only one part of the boundary. A client may read parent instructions, a
user's home directory, bundled skills, project configuration or executable
plugins outside that directory. Putting every intelligence file at the
work root would leave some undiscovered and could load other files that
were never selected.

The step should receive a small compiled placement plan. It chooses one
approved version of each selected item, its native path and its private
configuration scope. The source library stays searchable centrally; only
selected material is copied into the freshly started harness. The file's
position does not grant model, tool, network, file-write or spending
authority.

## Complete runtime classification

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

The native harness is an adapter used by the owning Loop. Its workspace,
configuration home, placement plan and discovery observations are internal
mechanics, not new executable graph vertices or intelligence layers.

## Two roots and five placement classes

The proposed shape separates the task files from the client's private
configuration. It is a placement example, not a new required top-level
repository folder or a claim that every harness supports every kind.

```text
One step's isolated instance
├── work/                         own task root and working directory
│   ├── native instruction file   small step brief at the client's expected path
│   ├── native skill directory    only selected approved packages
│   ├── materials/                authorized task inputs, not automatic instructions
│   └── outputs/                  permitted task results, separate from skills
├── home/                         fresh home; no inherited user skills or rules
├── config/                       isolated client configuration and tool references
└── host-owned placement record   outside the model-writable task view
```

| Material | Preferred place and reason |
|---|---|
| Step instructions | Compile a small `AGENTS.md` or `CLAUDE.md` into the task root. It contains the assignment and selected references, not the full library or prior transcript. Nested instruction files should appear only if the client needs their scoped behavior. |
| Agent Skills package | Copy the exact reviewed `SKILL.md` and its approved relative resources into the client's native project skill directory. Keep bundled scripts and references relative to that package. Do not install all 10,000 packages or copy one skill into several compatibility directories. |
| General reference or task data | Keep in a scoped materials folder or behind an authorized retrieval reference. Do not place arbitrary source documents where the client treats them as instructions. Fetch a large body only after selection. |
| Protocol server and provider configuration | Put versioned declarations in the client's supported project or isolated configuration location. A declaration cannot carry raw secrets; use the step-scoped credential broker and exact effect authority. Some clients need explicit trust or connection approval. |
| Plugins and executable code | Use the client's explicit installation or extension mechanism only after dependency, rights, sandbox, effect and load checks. A plugin is not activated merely because a folder exists. Outputs and writable task files stay out of skill or plugin source directories. |

## Observed client layouts

These paths are for the tested versions or source-backed client behavior,
not a universal portable layout. The
[September 22 instance experiment](HARNESS-INDEPENDENT-INSTANCES-2026-09-22.md)
observed instruction, skill and protocol configuration loading without a
model call. It did not establish that a model used each item or completed a
customer task.

| Client | Step instruction | Selected project skill | Configuration or executable integration |
|---|---|---|---|
| Codex 0.155.1 | `work/AGENTS.md` | `work/.agents/skills/<name>/SKILL.md` | Isolated `CODEX_HOME/config.toml`, or trusted `work/.codex/config.toml`, for Model Context Protocol servers. Plugins need their own installation and enablement flow. |
| Claude Code 2.1.280 | `work/CLAUDE.md`; for a shared brief, `CLAUDE.md` may contain `@AGENTS.md` | `work/.claude/skills/<name>/SKILL.md` | Project `.mcp.json` and `.claude/settings.json` or an isolated configuration directory. A plugin needs explicit loading or installation. |
| OpenCode, tested at 1.18.32 | `work/AGENTS.md` | `work/.opencode/skills/<name>/SKILL.md` | `work/opencode.json` for protocol servers and settings; `.opencode/plugins/` for executable plugins, with isolated home and configuration paths. |
| Pi 0.73.1 | `work/AGENTS.md` | `work/.pi/skills/<name>/SKILL.md` | Isolated `PI_CODING_AGENT_DIR`; `.pi/extensions/` is executable. This installed version has no native Model Context Protocol support. |

A [separate no-model Codex probe](../../artifacts/harness-intelligence-format-pilot-2026-09-22/context/CODEX-MD-CONFIGURED-FALLBACK-2026-09-22.json)
confirmed that Codex 0.155.1 ignored `CODEX.md` under the default empty
fallback list, then included it in prompt input when an isolated
configuration explicitly listed `CODEX.md` as a fallback. This makes
`CODEX.md` a qualified **configured alternative**, not the default root
instruction location.

The official [Codex instruction](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
and [skill](https://learn.chatgpt.com/docs/build-skills) guides,
[Claude instruction](https://code.claude.com/docs/en/memory),
[skill](https://code.claude.com/docs/en/skills), and
[protocol server](https://code.claude.com/docs/en/mcp) guides,
[OpenCode rules](https://opencode.ai/docs/rules/),
[skills](https://opencode.ai/docs/skills/), and
[configuration](https://opencode.ai/docs/config/) guides, and
[Pi 0.73.1 skill documentation](https://github.com/earendil-works/pi/blob/v0.73.1/packages/coding-agent/docs/skills.md)
support those path choices. The exact installed version still needs a
native-load probe because layout and trust behavior can change.

## Isolation is a separate test from layout

The native instance experiment found that setting only a client's
documented configuration variable could still admit a user skill from
`$HOME/.agents/skills`. OpenCode could also read the user's Claude
material. Claude Code and Pi could read ancestor instruction files.
Use a clean home and a task directory beneath a controlled root; isolate
client configuration and inspect every startup source. Codex's bundled
skills and client-specific built-ins need their own documented setting or
recorded presence. Do not assume a project file overrides every global
file, and do not create a symlink from the step into an unreviewed shared
skill directory.

A proposed `native_client_layout_profile/v1` can bind the client identity
and observed version, ancestor and global discovery rules, per-kind
relative destination, render transform, filename limits, trust and
activation requirements, collision policy, isolated home settings, and a
native discovery probe. An instance placement record then binds each
selected approved item identity and digest to every rendered path and
digest. Refuse an unsupported kind or client version before effects.
Keep the placement record outside the model-writable workspace.

## Checks before saying a step loaded the right files

The existing [native material guide](../guides/native-client-material-loading.md)
and [OpenCode installer](../../tools/install_selected_material.py) already
show one bounded implementation; do not build a second runtime to test
this proposal. Extend its owning edge and checks by client profile.

| Known-wrong setup | Required refusal or observation |
|---|---|
| Place a correct skill in the wrong client directory, or change its frontmatter name | The native discovery probe fails to list it; the step cannot claim it loaded. |
| Put an unselected skill or instruction in an ancestor, real home or compatibility directory | The isolation probe detects the extra source and refuses the run. |
| Two selected packages claim the same native name or destination | Resolve under an explicit policy before writing, or refuse; never silently overwrite. |
| A relative resource escapes through `..` or a symlink | Path confinement refuses materialization before launch. |
| A package's body or resource differs from its approved digest | Refuse the package and any claim that the prior approval covers it. |
| Project configuration is untrusted, a protocol server is unexpected, or a plugin has not been activated | Report the missing native binding; a file on disk is not a loaded capability. |
| A skill is listed but the model never reads or uses it | Record listed and loaded separately from used and independently verified. |

The initial choice is one selected package at its native project path,
with fresh home and configuration scopes. Fallback may choose another
qualified client layout or a permitted harness instance, but must keep
the same item identity, authority and task acceptance rule. A fallback
cannot silently add broader tools, inherited context or credentials.
