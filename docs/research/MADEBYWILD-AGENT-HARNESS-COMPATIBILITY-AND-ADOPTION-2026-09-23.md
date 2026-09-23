# Agent Harness: compatibility, design lessons and adoption for Baltor

Research checked September 23, 2026. Source inspected at
`madebywild/agent-harness` revision
`2ecf44f97ab6ffd76f5c1a58ac57b930e2ccfa17`, tagged `v2.1.0`.
The release was published September 1. This extends the
[first prior-art review](AGENT-HARNESS-MADEBYWILD-2026-09-23.md)
with implementation inspection, isolated renderer observations and native
Codex prompt construction. Roadmap S-6.44 remains the placement work authority;
S-6.40 and S-6.63 govern package supply and independent review.

## Decision

Use this project as concrete prior art for a configuration compiler and as a
candidate optional engine for customers who already use its workspace format.
Keep Baltor's direct materializer as the initial default. Qualify a small
export/import surface before maintaining a fork or calling upstream `apply`
inside a customer repository.

The strongest ideas to adopt are an explicit desired file set, ordered prompt
sections, capability-aware rendering, a preview of changes, source provenance,
customer ownership of downloaded source, and explicit registry refreshes.
The strongest reason for additional work is that rendering native-looking
files does not establish native loading, permission enforcement or task success.

The project is relevant even if Baltor never depends on its package. It provides
working examples and counterexamples for the materialization boundary we need.
It does not implement Baltor's task decomposition, fresh process per step,
budgeted execution, hosted retrieval, independent package admission or task
acceptance. These remain owned by the existing Loop Engine components.

## Evidence and limits

| Evidence | What was actually checked |
| --- | --- |
| Pinned repository source | Provider renderers, planner, ownership, behavior substitution, public exports, registry validation and hooks |
| Four renderer observations | Exact upstream TypeScript transpiled with TypeScript 5.9.3; synthetic canonical inputs rendered for Codex, Claude, Copilot and Cursor |
| Five additional renderer cases | Duplicate server conflict, strict unsupported hook, best-effort hook omission, settings override and Claude instruction path |
| Five native Codex cases | Installed `codex-cli 0.155.1`; empty control, both skill locations and two subagent configuration shapes; `debug prompt-input`, zero model calls |
| Separate architecture probes | [Ownership and compiler audit](MADEBYWILD-AGENT-HARNESS-ARCHITECTURE-AND-OWNERSHIP-2026-09-23.md) records its own controls and limitations |
| Earlier npm trial | Claude's first report records published package 2.1.0 producing fourteen files and an unsafe import result on a copy of repository instructions |

Our new probes did not run upstream initialization, migration, watch mode,
delegated authoring, lifecycle hooks, protocol servers or a model. The renderer
probe installed only pinned analysis dependencies in an isolated scratch folder
with package scripts disabled. Node's built-in TypeScript stripping was
unavailable in this build; the successful successor used TypeScript 5.9.3.
The [evidence folder](../../artifacts/madebywild-agent-harness-2026-09-23/README.md)
contains source hashes, inputs, outputs, scripts and reproduction instructions.
The renderer experiment was also repeated in a network-isolated, empty-environment
sandbox with a read-only host filesystem. Its provider outputs, control results
and source hashes matched exactly; the process had a 30-second timeout and
128 MB JavaScript heap ceiling.

## Where it belongs in Loop Engine

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

The default discrete cognitive or act step Loop node is an independently
governed instance of the canonical `Loop`, responsible for one focused cognitive
step or action. It receives the bounded assignment and selected information,
skills, tools and reusable code, then starts a fresh harness for that step.
The supervisor retains budgets, authority, termination and independent result
acceptance. A native subagent definition is material that a harness may consume;
it does not itself create a separately governed Loop or a separate workspace.

```text
Work owned by the classified Loop
├── Select an eligible package and complete dependencies
├── Resolve the exact harness, interface and runtime profile
├── Materialize through the existing placement boundary
│   ├── Direct native layout engine, initially preferred
│   └── Agent Harness export engine, proposed and qualified per profile
├── Verify the final files, configuration and available capabilities
├── Execute through the existing harness executor
└── Independently validate and record the result
```

| Existing owner | Useful extension inspired by this project |
| --- | --- |
| `tools/install_selected_material.py`, `ClientLayoutProfile` | Native file roles, interface/version-specific placement and discovery observations |
| `core.instance_instructions`, `InstructionSection`, `InstanceInstructionWriter` | Named ordered sections with source and transformation lineage |
| `core.service_runtime.catalogue_packages`, `CataloguePackage` | Exact complete file trees, including opaque binary bodies and executable dependencies |
| `core.harness_fresh_instances`, `FreshInstanceRecipe` | Tested launch profiles, controlled inherited state and native configuration generation |
| `core.node_provisioning`, existing `NodeAssignment` | The assignment and authorized capability selection before rendering |
| Existing review panel and catalogue releases | Exact-tree independent approval, withdrawal and customer eligibility |

These are extensions to existing boundaries. `ClientLayoutProfile` currently
lives in the installer tool, not in a new runtime module. The materializer must
not create a second package store, admission registry or task runtime.

## What the provider code really produces

| Material | Codex | Claude Code | Copilot | Cursor |
| --- | --- | --- | --- | --- |
| Ordered instruction sections | `AGENTS.md` | Root `CLAUDE.md` | `.github/copilot-instructions.md` | No renderer |
| Skill tree | `.codex/skills/<id>/` | `.claude/skills/<id>/` | `.github/skills/<id>/` | `.cursor/skills/<id>/` |
| Protocol connection | `.codex/config.toml`, `mcp_servers` | `.mcp.json`, `mcpServers` | `.vscode/mcp.json`, `servers` | `.cursor/mcp.json`, `mcpServers` |
| Native agent | Inline `agents.<id>` table | `.claude/agents/<id>.md` | `.github/agents/<id>.agent.md` | `.cursor/agents/<id>.md` |
| Hook | TOML hooks and optional notify | Settings hooks | `.github/hooks/harness.generated.json` | `.cursor/hooks.json` |
| Command | No renderer | `.claude/commands/<id>.md` | `.github/prompts/<id>.prompt.md` | No renderer |

This table describes this compiler revision, not universal support of the
products. Its fixed provider-name table does not identify CLI versus editor,
runtime release, operating system or policy. The actual root Claude output is
`CLAUDE.md`, despite the README's generated-output table saying `.claude/CLAUDE.md`.
[Pinned defaults](https://github.com/madebywild/agent-harness/blob/2ecf44f97ab6ffd76f5c1a58ac57b930e2ccfa17/packages/toolkit/src/provider-adapters/constants.ts).

### Codex skill placement works in the measured installed version

Both generated `.codex/skills/sample/SKILL.md` and the equivalent
`.agents/skills/sample/SKILL.md` exposed the controlled description in Codex
0.155.1 prompt construction. Neither exposed the full skill body initially.
All five native probe workspaces remained unchanged. Current official guidance
describes `.agents/skills` repository discovery; the measured alternative remains
version-specific evidence, not a reason to call the upstream path broken.
[Codex skills](https://learn.chatgpt.com/docs/build-skills).

The upstream Codex subagent renderer places `developer_instructions`, model and
other fields inline beneath `agents.<id>`. The official configuration reference
also describes a role's `config_file` pointing to another TOML layer. Our prompt
probe did not expose the reviewer marker for either shape, so it cannot determine
whether those subagent settings are honored. A native configuration/agent-listing
or controlled spawning test is still required; no model was called to settle it.
[Renderer](https://github.com/madebywild/agent-harness/blob/2ecf44f97ab6ffd76f5c1a58ac57b930e2ccfa17/packages/toolkit/src/provider-adapters/codex.ts),
[configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference).

### Copilot needs separate execution surfaces

The renderer writes VS Code configuration. GitHub's current CLI reference says
to migrate `.vscode/mcp.json` to `.mcp.json` for CLI use; the CLI also has user
configuration and explicit per-session configuration. A generic `copilot` label
would hide this difference. Qualify `copilot-vscode` and `copilot-cli` separately,
including schema, discovery, trust and authentication. The four-file renderer
test does not establish four working authenticated connections.
[Copilot command reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference).

### Missing output needs a typed compatibility result

Cursor has no prompt renderer in this project. That is a compiler limit;
Cursor itself documents `AGENTS.md` and project rules. Its lack of output should
produce an explicit unresolved required-capability result in Baltor. An empty
artifact list must not count as successfully delivering the task instructions.
[Cursor adapter](https://github.com/madebywild/agent-harness/blob/2ecf44f97ab6ffd76f5c1a58ac57b930e2ccfa17/packages/toolkit/src/provider-adapters/cursor.ts),
[Cursor rules](https://cursor.com/docs/rules).

### Monorepo location and activation are separate

The compiler routes package-scoped Claude material into the package, Codex
instructions into the package, and most other outputs to the root. Our renderer
probe confirmed the routing and preserved supplied section order. It also showed
Copilot's package section merging into the root instruction file. That can widen
instruction scope. The upstream monorepo guide itself says Claude protocol and
settings files are read when Claude starts in the directory. Baltor must bind
working directory and discovery mechanism to placement, and refuse a scope
change where a required rule was meant to apply only to one component.
[Monorepo guide](https://github.com/madebywild/agent-harness/blob/2ecf44f97ab6ffd76f5c1a58ac57b930e2ccfa17/docs/monorepo.md).

## Logic we should adopt and strengthen

| Upstream idea | Baltor improvement | Discriminating check |
| --- | --- | --- |
| Canonical entity followed by provider renderer | Treat each rendering as a compilation with an explicit capability/loss report | A required instruction or hook with no equivalent blocks launch |
| Ordered prompt sections | Preserve immutable sections and a source map from output ranges to section identities | Reordering policy and examples changes the digest and cannot reuse prior approval |
| Behavior map with allowed values and defaults | Use declared model/task variants for advisory wording, with evaluation evidence | Selecting concise wording cannot change output contracts or permissions |
| Provider capability table | Key capabilities by harness, interface, version, operating system and policy | Two surfaces of one product with different discovery cannot share a qualification |
| Desired file set and managed index | Bind a reviewed plan to expected existing bytes; refuse stale writes | A user edit between preview and apply causes a conflict |
| Settings merged into generated config | Validate the final merged configuration against step authority | A settings override replacing the selected server command is refused |
| Registry provenance and explicit refresh | Resolve commit plus path and content digests; keep local modifications distinct | A moved branch/tag or modified local file cannot silently inherit approval |
| Skills import audit | Retain the audit as input to Baltor's independent review | An upstream allow-unsafe flag cannot bypass Baltor admission |
| Reusable presets | Treat presets as versioned selection recipes with dependency closure | A parent preset cannot silently add a network-capable hook |
| Watch mode | Regenerate candidates only; publish a new checked bundle at a boundary | A file change cannot mutate an active attempt's approved inputs |

The successful conflict test is worth adopting: different definitions of the
same protocol server name cause an error. The same general rule should cover
tool names, instruction targets, native agent identifiers and package outputs.

The hook probe also gives a useful warning. A Copilot hook with an unsupported
matcher throws in strict mode. In `best_effort` mode, the same hook produces an
empty hook object. Baltor can permit omission of explicitly optional conveniences;
it must refuse omission of a mandatory permission or correctness check.
[Hook rendering](https://github.com/madebywild/agent-harness/blob/2ecf44f97ab6ffd76f5c1a58ac57b930e2ccfa17/packages/toolkit/src/provider-adapters/hooks.ts).

Our settings probe changed a generated Codex server command from
`/usr/bin/false` to `/usr/bin/true` through raw settings, without invoking either.
This is observed merge behavior. It demonstrates why checking only the original
package declaration is insufficient; the merged executable configuration is the
object that needs authorization and hashing.

## Context, executable tools and opaque assets

The upstream `RenderedArtifact` interface carries a string and a format limited
to Markdown, JSON or TOML. The skill renderer labels every non-JSON file as
Markdown, including a Python script. Its loader reads skill files as UTF-8 and
substitutes text. This is suitable for a substantial text-oriented subset, but
is not a qualified byte-preserving transport for arbitrary binaries.
[Artifact types](https://github.com/madebywild/agent-harness/blob/2ecf44f97ab6ffd76f5c1a58ac57b930e2ccfa17/packages/toolkit/src/types.ts),
[skill rendering](https://github.com/madebywild/agent-harness/blob/2ecf44f97ab6ffd76f5c1a58ac57b930e2ccfa17/packages/toolkit/src/provider-adapters/create-adapter.ts).

For Baltor, keep role, bytes, media type, activation and effects separate:

```text
Selected package payload
├── Information: instructions, references and bounded task state
├── Contracts: schemas, fixtures and independent acceptance rules
├── Executable resources: scripts, native binaries and WebAssembly modules
├── Activation: native tools, plugins, hooks and server declarations
└── Supporting assets: templates, data and locked dependencies
```

Only explicitly declared templates should be substituted. Opaque bodies pass
through unchanged. Scripts need interpreter/dependency bindings; native binaries
need operating system, architecture and application binary interface checks;
WebAssembly needs runtime and import-capability checks. Executable mode and
symbolic-link policy need their own fields. A `.py` suffix, a friendly tool name
or a plugin description cannot grant execution authority.

This is especially relevant to our million-file ambition. One method rendered
for four providers remains one logical package and several delivery variants.
Compile only selected packages and their dependencies into each attempt. Keep
the large searchable catalogue outside worker instruction discovery. Benchmark
retrieval, selection and materialization separately from the number of generated
paths. No million-item throughput claim follows from this project's design.

## Corrections to the first review and README

1. **The lock does record rendered output hashes.** `planner.ts` builds
   `outputs[].contentSha256` from each desired artifact's rendered content.
   Raw source hashes are another field. The earlier note's statement that the
   lock cannot identify rendered bytes is too broad. The remaining gap is
   independent post-write verification, semantic qualification and admission.
2. **An ownership entry is not an overwrite conflict guard.** The planner refuses
   unmanaged files, but a changed managed file is scheduled for replacement;
   stale managed paths are scheduled for deletion. Calling that drift refusal
   would misdescribe the code. See the separate ownership audit.
3. **Native agent configurations do not establish Loop isolation.** Filesystem,
   conversation, inherited policy, tools and budget must each be checked. Do not
   assume all subagents share one identical authority model across products.
4. **The README's `Planner` import is stale for this source.** Public `index.ts`
   exports `HarnessEngine` and a `plan()` function; it does not export `Planner`.
   Bind any wrapper to the actual package API and version.

[Pinned planner](https://github.com/madebywild/agent-harness/blob/2ecf44f97ab6ffd76f5c1a58ac57b930e2ccfa17/packages/toolkit/src/planner.ts),
[public exports](https://github.com/madebywild/agent-harness/blob/2ecf44f97ab6ffd76f5c1a58ac57b930e2ccfa17/packages/toolkit/src/index.ts).

## Reuse, fork and distribution choices

| Choice | Decision and reason |
| --- | --- |
| Design inspiration | Adopt now in existing owners: explicit plan, typed capability losses, source maps, conflict handling and customer-owned source |
| Public Baltor connection preset | Prototype with synthetic credentials, then qualify native connection paths independently; keep private catalogue bodies out of the public registry |
| Optional upstream workspace engine | Evaluate only in an isolated staging directory first; accept its output through Baltor's confined installer and final-config validator |
| Direct `apply` over an existing customer repository | Hold until ownership, drift, atomicity, deletion and symlink behavior satisfy the same installation contract |
| Fork of the whole project | Defer: it adds TypeScript/runtime/dependency maintenance and four-provider drift without addressing the full runtime mission |
| Small upstream contribution | Prepare reproducible reports for binary preservation, capability omissions, secret references and safe writes; posting still needs explicit authorization |

MIT licensing makes source reuse possible under its notice conditions. Preserve
the upstream license and exact revision for any copied code. Third-party registry
content has its own rights and approval state; the compiler's license does not
clear all content it can import.
[Project license](https://github.com/madebywild/agent-harness/blob/2ecf44f97ab6ffd76f5c1a58ac57b930e2ccfa17/LICENSE).

For customers, the strongest product idea is an inspectable installation:
select the harness surface, see files and effects, preview additions and
conflicts, install the selected package, and see separate discovery/use/results
evidence. Provide an explicit refresh and rollback path. Downloaded editable
source changes identity when the customer changes it; it cannot retain a badge
claiming approval of different bytes.

For the business, compatible exporters reduce setup friction. Paid value must
come from useful retrieval, reviewed methods, release management and measured
task outcomes. This repository supplies no evidence for a particular conversion
rate, price, market size or token-saving claim.

## Recommended experiment and continuation

Start with three controlled packages: instructions plus a skill; a deterministic
tool with a schema and fixtures; and a native hook/plugin package. Compare direct
placement with upstream rendering using the same exact package and installed
runtime. Test at least one successful path, one unsupported capability, one local
edit, one stale preview, one forbidden effect and one invalid output per profile.

Record native discovery, actual activation, executable availability, accepted
output, setup time and failure explanation separately. Models are unnecessary
for the first compilation/discovery phase. Model-dependent task use requires
declared authority and an independent evaluator. Select a default engine from
those results; do not infer performance from fewer source files.

For scale, add a frozen regression population and a scheduled documentation and
upstream-source comparison. Changed source creates a candidate compatibility
profile and reruns the same probes; it never updates an active profile or
customer workspace automatically. The first new dimensions to record are
interface, operating system, native feature omissions, text versus opaque bytes,
transformation lineage, activation timing and expected pre-existing content.
Map them to S-6.44 and the existing configuration/evidence machinery.

One adjacent live-code gap needs its own known-wrong check before expanding mixed
package serving: the current retrieval HTTP parser accepts query, mode, count
and filters but does not forward effect authority as the explicit provisioning
path does. A requested executable package may therefore be absent from search
even when an authorized explicit download is possible. This is a Baltor
integration gap, not a finding about Agent Harness.

Decision: finish a small, measured materialization comparison and connection
preset first. Carry the useful compiler ideas into Baltor's existing boundaries,
then expand file kinds and interfaces with native evidence.
