# How task packets and harness packages should interface

Kind: dated research, native observations and integration recommendations.
September 23, 2026. Source reviewed: `abcad4f8`. This extends the existing
[roadmap](../roadmap/roadmap.yaml), particularly S-6.40, S-6.42, S-6.43,
S-6.44 and S-6.61. It does not admit a package or deploy an adapter.

## Recommended direction

Keep one structured assignment and one identity for each reusable package.
Render them for the **exact harness, version and product surface**. A local
command-line process, editor extension, software development kit and remote
coding agent can load different material despite sharing a product name.

For a step started by the engine, send the essential assignment through the
native launch or session input. For a user entering a prepared directory,
provide a tested native instruction entrypoint. Both views must come from
the same host-validated assignment. Do not duplicate the entire task and its
inputs in several prompt channels as a universal policy.

Keep larger references, approved tools and dependencies in their native
package layout. `node_context.md` and `run-state.json` are useful views, but
arbitrary filenames have no universal discovery or memory behavior. Hooks
can add context where supported; they cannot be the only delivery mechanism
for an essential task requirement.

The current service already has `CataloguePackage`, typed file roles,
per-file digests and downloads by path. Reuse those components. The present
catalogue's one-file Markdown items and the installer's narrow native
coverage do not mean the service needs another package store.

Detailed supporting reports:

- [Standards and interfaces](HARNESS-PACKAGE-STANDARDS-AND-INTERFACES-2026-09-23.md)
- [Claude Code and editor surfaces](HARNESS-PACKAGES-CLAUDE-AND-EDITORS-2026-09-23.md)
- [Open harnesses and source revisions](HARNESS-PACKAGES-OPEN-HARNESSES-2026-09-23.md)
- [New local observations and reproducible probe](../../artifacts/harness-package-interoperability-2026-09-23/README.md)

## Which harnesses to qualify first

This ordering reflects our existing implementation and evidence. It is not a
model-quality ranking, market-share estimate or assertion of complete support.

| Qualification lane | Initial targets | Why start here | What still needs proof |
|---|---|---|---|
| Task assignment | Codex CLI 0.155.1 and Claude Code 2.1.280 | Codex has direct prompt-construction observations; Claude has native plugin discovery and an independently observed startup hook. | Full task packet consumption, exact selected dependencies, output checks and accepted work. |
| Hosted package installation | OpenCode, at an explicitly qualified installed version | The current selected-material installer already has an OpenCode profile. | Complete multi-file preservation, all required file roles, safe activation and the final native task. Its recorded installer versions and the 1.18.32 research binary are separate facts. |
| Local-model and overnight execution | Pi 0.73.1 initially, with a separate upgrade qualification | Existing process integration and now direct installed-loader observations. | Model/tool compatibility and actual task completion. Current upstream Pi has changed package identity and behavior; do not transfer old observations to the new version. |
| Next command-line adapters | Gemini CLI, Qwen Code and ZCode | Documented explicit launch and native package mechanisms; ZCode now has identifiable source to inspect. | Clean installation or pinned binary, isolation, cancellation, loading and output evidence. Source availability alone is not qualification. |
| Editor and remote surfaces | Cursor, Cline, Copilot CLI, Copilot cloud, OpenHands | Valuable native ecosystems and distribution paths. | A separate profile for each surface, workspace trust, tool permissions, remote filesystem reachability and native activation. |

ZCode being unqualified means Baltor has not yet demonstrated the required
behavior. It does not mean ZCode is incapable. Prefer an adapter or native
extension first. A fork should address a measured limitation that an adapter
cannot fix, with an explicit upstream maintenance cost and comparison.

## What is read first, and what is merely present

| Material | Usual activation | Consequence for our package |
|---|---|---|
| Explicit task text | Launch request or protocol turn | Put the objective, first actions, constraints, state identity and output obligations here for engine-controlled starts. |
| Native instruction file | Startup, directory discovery or a client-specific reload | Qualify precedence, ancestor scope, trust and the effective combined budget. |
| Skill metadata | Discovery before task work | A listed name and description do not establish that the procedure body was read. |
| Skill body and resources | Explicit invocation or model-selected activation; resources often load later | Preserve the whole folder and record activation and reads separately. |
| Python, shell or other tool code | Explicit tool registration or a permitted execution command | Dropping a source file into a directory does not make it a registered tool. |
| Hook | Registered event after native activation and trust | Events, blocking behavior, timeouts, merge rules and output schemas differ. |
| Plugin manifest | Explicit native binding, installation or package discovery | Successful manifest parsing can coexist with silently ignored unsupported components. |
| JSON contract | Explicit schema attachment or host validation | A schema file on disk does not enforce its requirements. |
| State snapshot | Explicit input or authorized read | The host owns its version and acceptance; a filename is not automatic cross-step memory. |

The [Agent Skills specification](https://agentskills.io/specification) provides
a useful common folder convention. It does not standardize every client's
activation, permission, duplicate-name or state behavior.

## Important differences in the current evidence

### Codex: an instruction file can be valid and still disappear

Official guidance describes one selected instruction file per directory,
override precedence and a combined project-instruction budget of 32 KiB by
default. It also distinguishes local skills from plugin distribution.
[Instruction discovery](https://learn.chatgpt.com/docs/agent-configuration/agents-md),
[skills](https://learn.chatgpt.com/docs/build-skills).

The new no-model probe observed these seven cases in Codex 0.155.1:

| Controlled setup | Observed prompt content |
|---|---|
| Existing focused packet in a clean root | Objective, first action, state identity and output contract all visible. |
| Add `AGENTS.override.md` | All four task markers absent; the override marker visible. |
| Replace instructions with `@node_context.md` and prose file pointers | All four task markers absent. Codex did not expand the import syntax. |
| A large ancestor instruction consumes the combined budget | Ancestor marker visible; all four step markers absent. |
| Remove the native entrypoint and supply the essentials as launch text | All four markers visible. |
| Set the actual instruction budget to 512 bytes | Objective visible; first action, state and output contract absent. |
| Install one controlled skill and a loose tool source file | Skill description visible; skill body and loose tool body absent. |

These are observations of prompt construction, not proof that a model followed
the task. The explicit-input case does not justify ignoring hostile inherited
instructions. Isolation and assignment delivery are separate requirements.

Installed schema generation also confirms separate thread configuration,
turn input and `outputSchema` fields. The public command-line interface accepts
standard input and an output schema. Use those native mechanisms instead of
asking the model to discover its task by searching arbitrary files. Private
task content belongs on standard input or the protocol transport, not command
arguments visible in a process listing.
[Native automation](https://learn.chatgpt.com/docs/non-interactive-mode),
[application server](https://learn.chatgpt.com/docs/app-server).

### Other clients: similarly named files have different semantics

- **Claude Code:** direct `AGENTS.md` support is version and configuration
  dependent. Explicit `CLAUDE.md` imports remain useful. The earlier candidate
  hook ran in a no-model startup, but that does not establish use of the full
  packet. Its skill `allowed-tools` field is not a tool-denial boundary.
- **OpenCode:** `@file` text is not an automatic instruction import. Current
  source also prioritizes instruction filenames across the worktree, which
  can make a parent `AGENTS.md` matter more than a nearer alternative name.
- **Pi:** installed 0.73.1 and current upstream are materially different.
  Existing loader evidence must keep the package and version attached.
- **Gemini CLI:** `GEMINI.md` or explicitly configured context filenames feed
  context; native skill activation has its own consent and loading behavior.
- **Copilot:** CLI, cloud and editor instructions are separate profiles.
  Custom subagents can omit repository instructions unless explicitly enabled.
- **Cursor:** a startup hook is not a blocking gate. A plugin may satisfy the
  portable format while native hook or variable behavior remains different.
- **Cline:** inspect the actual tool-approval configuration rather than
  assuming command-line automation starts with restrictive defaults.
- **Qwen and OpenHands:** portable package support does not make their native
  commands, hooks, agent definitions and extension namespaces interchangeable.

Each statement above is sourced and qualified in the linked client reports.
The required behavior belongs in a client profile and a discriminating test,
not in a global claim that every harness reads `AGENTS.md` identically.

## Standards to use, with their boundaries

| Standard or interface | Recommended use | Boundary to preserve |
|---|---|---|
| AGENTS.md | Portable starting convention for applicable clients | Client-specific discovery and precedence still apply. |
| Agent Skills | Reusable procedure plus supporting resources | Metadata, body loading and executable effects are separate. |
| Agent Plugins 1.0.0 | Portable identity, skills and protocol server configuration | Hooks, commands and agents require native extensions; 1.1.0 is a draft. |
| Model Context Protocol | Authenticated search, selected resources and tools | Returning a resource does not install or activate it locally. |
| Skills over Model Context Protocol | A qualified experimental skill delivery path | Current host support is partial and it is not a general plugin or task-state installer. |
| Agent Client Protocol | Session setup, explicit task text, capability-negotiated context and events | A fresh session is not automatically a fresh process or clean configuration scope. |
| Agent2Agent | Later remote task delegation and output artifacts | It is unnecessary for copying a local package and does not replace Loop ownership. |
| JSON Schema | Versioned structural contracts | Host semantic acceptance and effect policy remain independent. |

The [published Agent Plugins specification](https://agent-plugins.org/specification)
and [Skills over Model Context Protocol](https://modelcontextprotocol.io/extensions/skills/overview)
are useful reuse opportunities. The latter should be tested against our
existing download path with identical package bytes and tasks. Baltor already
serves the two deliberately qualified base protocol revisions described in
S-6.43; supporting that newer extension is separate work.

## Fit the design into the existing architecture

```text
Operational runtime type
└── Loop
    ├── Operational relationship
    │   ├── Starting
    │   ├── Spawned by
    │   ├── Queried by
    │   ├── Retrieved by
    │   └── Connected from
    ├── Role: Practitioner, Intelligence, or Solution
    ├── Versioned role profile
    ├── Purpose and domain categories
    ├── Run mode: deterministic, hybrid, or non-deterministic
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition
    ├── Exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the selected mode permits a model
    └── Run History records
```

The following preparation steps are owned by classified Loops. Their files,
adapters and records are internal mechanics, not new executable vertices.

```text
Host-validated assignment and selected approved package references
└── Existing provisioning and instruction boundaries
    ├── resolve exact client/version/surface and required capabilities
    ├── bind task, state version, authority and output acceptance
    ├── stage complete package trees and verify bytes before activation
    ├── render essential launch input and the required native files
    ├── check effective context, dependencies and native activation
    └── start the eligible executor
        ├── observe reads, tool calls, effects and output
        ├── validate structure and independently evaluate the result
        └── commit permitted state changes through the owning host
```

| Existing owner | Improvement to make there |
|---|---|
| `NodeAssignment` and `AssignmentBriefing` | Versioned first actions, relevant state and output obligations; avoid ad hoc fields silently appended to existing serialized versions. |
| Prompt resource bundles | One typed source for native-file and launch renderings, trust classes, required slots, omission rules and exact render digests. |
| `CataloguePackage` and body store | Preserve existing file roles, media types, limits and digests. Add only missing activation/dependency requirements through the current package contracts. |
| `ClientLayoutProfile` in the selected-material installer | Extend the existing profile registry for complete package roles and exact surfaces; no second installer registry. |
| Harness execution capabilities and adapter edge | Bind native invocation, process/session identity, output mode, cancellation and required behavior to a qualified version. |
| Trusted state and Run History | Keep input state immutable, updates candidate-only and version-bound; record actual exposure and effects separately from file presence. |
| Credential broker direction in S-6.61 | Bind step-scoped connection references. Keep raw credentials out of package bodies and task/state snapshots. |

The current package contract permits up to 64 files, 8 MiB per file and 32 MiB
per package, with confined paths and case-collision rejection. Do not bundle
an entire dependency tree by silently increasing those limits. Declare pinned
dependencies and qualify their preparation under a separate effect policy.
The existing native installer currently places skills for OpenCode; it does
not yet provide equivalent delivery for every declared catalogue file role.

## Improvements and tests that should guide implementation

1. **Check actual task exposure before launch.** Record objective, first
   actions, constraints, state binding and output requirements through native
   inspection when available. Required information that is omitted or truncated
   must produce a preparation failure. Without an inspection interface, mark
   exposure unknown and qualify a controlled task before advertising support.
2. **Separate required and optional components.** A required hook, helper,
   server or skill must fail eligibility if unsupported. A portable host may
   legitimately ignore an extension; our task contract may not.
3. **Treat transformations as versioned outputs.** Keep one logical method
   identity with native and model-specific variants. Each changed rendering
   needs its digest and applicable review; converting a restricted subagent
   into a skill does not preserve its isolation automatically.
4. **Measure the effective budget.** The composer checks its own body today.
   Native clients can limit the combined instructions or skill listing and
   use different units. Include aliases, wrappers and inherited material;
   preserve required fields when reducing optional context.
5. **Make package activation atomic.** Download and verify every required
   file into a staging area, check dependencies and collisions, then activate
   one complete version. An incomplete helper set must never appear ready.
6. **Keep code and state apart.** Reviewed code stays immutable; task output,
   plugin writable data and proposed state updates have separate scoped paths.
   A fresh process receives committed effect identities so retries cannot
   silently replay external actions.
7. **Plan an explicit state transition.** A successful harness answer is a
   candidate. The host checks the expected state version, schema, independent
   acceptance and effect results before making a new state current. A resume
   must name its exact task/session rather than choose a global last session.
8. **Show compatibility honestly in search and onboarding.** Display the
   file kinds, required runtime, activation method, observed client version,
   last qualification and missing requirements. Separate "format checked",
   "discovered", "context observed", "executed" and "task accepted".
9. **Benchmark the alternatives.** Compare explicit task input, verified
   native files and supported embedded context with the same task and model.
   Compare optional context expansion as well as reduction. Measure accepted
   work, failure recovery, cost, elapsed time and preparation overhead.

## Initial choices and ordered fallback

These proposals extend the existing configuration dimensions; they are not
new authorities or universal minimum-context rules.

| Dimension | Initial choice | Eligible alternatives, in order | Discriminating check |
|---|---|---|---|
| Assignment delivery | Explicit native launch/session text for engine-controlled starts | Verified native entrypoint for manual starts; supported embedded context; refuse missing essentials | Remove input or introduce an override; task markers must not silently vanish. |
| Native layout | Exact observed client/version/surface profile | Another qualified native rendering; another permitted harness; refuse | Same package under a different surface must not inherit qualification. |
| Activation | Required component explicitly registered and trusted | Independently qualified equivalent preserving semantics; refuse | Disable the required hook or helper and confirm preparation fails. |
| Context quantity | Complete task essentials plus selected relevant material | Add evidence, choose another representation or model variant within authority | Both expanded and reduced forms retain constraints and are compared on accepted work. |
| State continuation | Fresh process with host-selected snapshot | Exact same-task resume under policy; repaired snapshot after conflict; refuse stale update | Two results based on one version cannot both overwrite current state. |
| Delivery transport | Existing authenticated package downloads and local placement | Qualified portable plugin or skill extension; refuse missing capability | Retrieving a manifest without a required body cannot produce a ready package. |

## Continuous qualification

Run the saved no-model discovery probes whenever a supported client version,
renderer, native profile or package standard changes. Pin the source revision
and record failures beside successors. A scheduled research pass should
compare source digests and release notes, open an existing-roadmap finding
and propose updated tests. It must not auto-install a new client or promote
material just because documentation changed.

For each supported surface, keep positive, negative, unrelated and ambiguous
task cases. Include override precedence, inherited instructions, missing
dependencies, duplicate names, truncation, unsupported extensions, stale
state, cancellation and external-effect retry cases. Native startup probes
are the inexpensive first gate. Provider-backed task trials and independent
acceptance are the next gate, under the existing declared model authority.

The files produced by this research are research records and test tooling.
They add no approved library items and establish no universal compatibility.
