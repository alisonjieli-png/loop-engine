# Harness intelligence is a file package, not a Markdown-only library

Kind: dated format and admission research, September 22, 2026 local time.
The owner clarified that harness intelligence includes **any file or
package designed to enter a harness working environment and be discovered,
loaded or invoked by that harness**. A Markdown skill is one case. The
[native placement research](NATIVE-HARNESS-INTELLIGENCE-PLACEMENT-2026-09-22.md)
maps supported locations by client and version; the
[roadmap](../roadmap/roadmap.yaml) remains the task authority. This report
proposes qualification checks, not a new runtime or a claim that an
arbitrary file is automatically consumed.

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

The four intelligence layers still own material by meaning. Harness
intelligence is a **family**, built to follow an external harness. A
body owned by Code Intelligence has the Loop-native family. A harness
package may reference that verified code through its canonical source
identity, or hold a separately reviewed, original harness-local rendering;
it must not create a second active copy of the same body in another
family. A `.py` suffix creates neither an intelligence layer nor effect
authority. Installing, searching, selecting and invoking material
remain work owned by classified Loops and their adapters.

## What the harness can actually pick up

For each item, distinguish six separate facts: file present in the step
environment; native client discovers its path; client loads its content
or exposes its tool; the model or tool uses it; the task result is
independently verified; and the package improves a matched task outcome.
The last fact requires comparison, not a successful format check. A file
with no native discovery or explicit reference is just a workspace file.

| File or package class | Native pickup example | Review and effect distinction |
|---|---|---|
| Root or scoped instructions | `AGENTS.md` for Codex, OpenCode and Pi; `CLAUDE.md` for Claude Code; `GEMINI.md` for Gemini CLI; `.github/copilot-instructions.md` for supported Copilot surfaces | Usually loaded automatically at a particular scope. Review context size, inheritance, instruction conflicts, source and tenant scope. Prose does not grant permission. |
| Optional instruction fallback | `CODEX.md` is **not a Codex default**: official Codex configuration has `project_doc_fallback_filenames = []` by default. A qualified per-step configuration could list it as a fallback when no higher-priority instruction exists at that directory level. An `AGENTS.md` pointer only asks the model to read the file; it is not automatic native ingestion. | Record the exact configuration and native-load observation; do not count the filename alone as a working entry point. |
| Agent Skill package | `SKILL.md`, optional `scripts/`, `references/`, `assets/` at the client's native skill path | Name and description may be discovered first; body and resources load on activation. Review every bundled file, dependency and relative path. A format validator does not approve code or factual claims. |
| Agent or command profile | Client-specific agent definition, prompt or command file, such as a Claude subagent or an OpenCode agent | This can change prompts, tool exposure or operation mode. A Markdown extension here may be more powerful than a passive reference; qualify the client's actual activation rule. |
| Local tool or reusable code | Python, JavaScript, shell, SQL or a package placed under a selected skill or a registered tool adapter | Mere presence does not make it a callable tool. Record typed input/output, dependencies, effects, sandbox, tests and independent verification before invocation. Run code only under separately declared authority. |
| Protocol server connection | Codex `config.toml`, Claude `.mcp.json`, OpenCode `opencode.json`, or a qualified plugin declaration | A config may start a process or reach a remote endpoint. Validate syntax, trust, server identity, tool list, credential reference, network and effect policy. No raw key in the file. Pi 0.73.1 needs an extension for protocol support. |
| Client policy, provider route or lifecycle hook | Client settings, permissions, sandbox policy, provider/model routes, startup hooks or prompt overrides | These can change tools, effects, costs or context before the first task step. Require typed owner authority, versioned client settings, no embedded credentials, startup-source inspection and effect tests. They are not merely passive connection metadata. |
| Plugin or executable extension | Codex plugin manifest and explicit install, Claude plugin package, OpenCode project plugin, Pi TypeScript extension, Gemini CLI extension | Higher risk: code can run at startup or tool boundaries. Review entire package, dependencies, signatures or digests, lifecycle and effect limits. Native discovery is not necessarily activation. |
| Reference and task data | JSON, YAML, CSV, PDF, images, schemas, source documents, prompts or binaries in a scoped materials folder | Not automatically an instruction. Keep provenance, format, licence, sensitivity and size; materialize or read only after selection and permission checks. |

The [Agent Skills specification](https://agentskills.io/specification)
defines native skill folders and optional scripts, references and assets.
The [Codex instruction guide](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
and [configuration sample](https://learn.chatgpt.com/docs/config-file/config-sample)
support the `AGENTS.md` default and optional fallback distinction.
[Claude Code](https://code.claude.com/docs/en/memory),
[OpenCode](https://opencode.ai/docs/rules/),
[Pi](https://github.com/earendil-works/pi/blob/v0.73.1/packages/coding-agent/docs/skills.md),
[Gemini CLI](https://geminicli.com/docs/cli/gemini-md/) and
[GitHub Copilot](https://docs.github.com/en/copilot/reference/custom-instructions-support)
document different instruction paths. Official
[Codex plugin](https://developers.openai.com/plugins/build/plugins),
[Pi extension](https://pi.dev/docs/latest/extensions) and
[OpenCode tool](https://dev.opencode.ai/docs/tools/) documentation shows
why executable packages need a stronger gate than a text reference.
These sources describe current or named versions; Loop Engine must test
the exact installed client before listing support.

## One package record, several independent dimensions

The proposed candidate contract should record the following separately,
using existing catalogue and artifact boundaries rather than a parallel
runtime store:

```text
Harness intelligence candidate
├── Source identity, exact revision, rights, attribution and bytes
├── Logical method or capability identity, distinct from rendered files
├── Format and file inventory with digest, size and dependency per file
├── Meaningful layer and harness-intelligence family
├── Task, occupation, project and company-archetype search facets
├── Supported client/version layout profiles and activation conditions
├── Typed input/output, effects, credential and network requirements
├── Independent review decision for the exact package bytes
├── Native discovery, load, use and task-verification evidence
└── Release, withdrawal and model-specific derivative relationship
```

Do not infer executable authority from a filename, a skill description,
a tag, a model vote or a successful search result. A single logical
method may have client-specific layouts and model-specific renderings;
those are qualified variants, not extra unique methods for a 10,000-item
count. A multi-file skill is one package with several individually hashed
files. Only selected approved packages enter a fresh step; the rest stay
server-side searchable.

## Tests that differ by file class

| Known-wrong control | Required result |
|---|---|
| Place `CODEX.md` alone under a default Codex configuration | Do not claim native instruction loading; use `AGENTS.md` or prove an explicit fallback configuration. |
| Put a selected skill in a wrong client directory or behind a symlink escape | Native-listing or path-confinement check fails before the run. |
| Change a bundled script, reference asset or manifest after review | Exact-package approval no longer matches; refuse activation. |
| Give a tool script a wrong input type, duplicate key, path traversal or partial output | Positive and known-wrong execution checks reject it in a bounded sandbox. |
| Put a real credential, broad environment variable or unapproved endpoint into a connection file | Refuse before a server starts; a scoped broker reference is a different contract. |
| Add a startup hook, provider route or permission setting that broadens the step's typed authority | Refuse before client initialization, even when the settings file is syntactically valid. |
| Make a plugin executable but leave its licence, dependency or trust state unknown | It stays a candidate; native auto-discovery must not become approval. |
| Search a text reference for a write task, or return an ungranted item | Eligibility or grant filtering refuses the result before body materialization. |
| Withdraw the final item from an account but leave a stale config or grant | Release and direct-read checks refuse the old package, including after rollback. |

The first three [candidate batches](../verification/OCCUPATION-LINKED-HARNESS-CANDIDATE-BATCH-QA-2026-09-22.md)
cover 68 text-only Agent Skills. The owner's clarification expands the
next isolated pilot to native context files, deterministic tool code and
protocol configuration. Each must prove its pickup path and, for code or
connections, its bounded behavior before independent admission. Do not
publish a heterogeneous file count from extension names or rendered
copies; report logical packages, physical files, approved versions,
native-loaded versions and verified task effects separately.
