# Baltor client artifact

Kind: dated client architecture and customer-journey input, September 23,
2026. This document accompanies the handbook and maps proposed behavior to
[D-17-T03 and D-17-T04](../roadmap/roadmap.yaml),
[S-6.42 and S-6.44](../roadmap/roadmap.yaml), and
[S-6.61 and S-6.62](../roadmap/roadmap.yaml). The roadmap remains the task
authority. The [native instance experiment](HARNESS-INDEPENDENT-INSTANCES-2026-09-22.md),
[placement research](NATIVE-HARNESS-INTELLIGENCE-PLACEMENT-2026-09-22.md),
[selected-material operating guide](../guides/native-client-material-loading.md),
and [credential delegation research](CUSTOMER-ENDPOINTS-AND-CREDENTIAL-DELEGATION-2026-09-22.md)
support the current-state and design distinctions below.

## Purpose and boundary

The customer runs their own harness and models. The hosted Baltor service
searches and delivers approved intelligence. The local Loop Engine host
selects the eligible material and starts a separately initialized harness
for a focused step under that step's budget and permissions. A served item is
a package of one or more files a supported client actually picks up from
its working directory or step configuration. Instruction files, skills with
scripts and references, executable tools, plugins and protocol connections
are possible package contents. A file extension, folder name or label does
not grant a permission or prove native use.

The complete behavioral account is in
[ASTRA.md](../../ASTRA.md#complete-behavioral-explanation): a discrete
cognitive or act step Loop node is an independently governed instance of the
Loop runtime for one clearly defined cognitive step or action. It receives
the context, instructions, skills, plugins, tools and working files relevant
to that assignment. It can use a separately initialized harness, inspect
results, change approach and repeat within its declared completion
conditions. It can publish candidate outputs while continuing; publishing
does not itself finish the assignment. A consequential external action
requires exact authorization each time and protection against duplicate
delivery. The client's process is an adapter under the owning Loop.

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

The service, installer, credential broker, workspace, native process and
placement record are internal mechanics or adapters. They are not additional
executable graph vertices. Searching, selecting, materializing and
evaluating intelligence are work owned by classified Loops. The
[four persistent intelligence layers](../../AGENTS.md#intelligence-rules)
remain separate from the harness-intelligence family.

## What exists and what still needs qualification

| Surface | Observed or implemented behavior | Limit |
|---|---|---|
| Hosted service | The saved [live readiness record](../verification/SAAS-LIVE-READINESS-AND-CUSTOMER-JOURNEY-2026-09-22.md) describes 43 packaged single-Markdown items, personal client keys, search and metered download, with public registration and checkout closed. | The active packaged bodies were not native multi-file skill folders. An offer or download is not a loaded, used or accepted step. |
| Selected-material installer | [`tools/install_selected_material.py`](../../tools/install_selected_material.py) previews references and manifests, then installs and asks OpenCode to list the installed item under explicit authorization. Its local and loopback checks verify exact bytes. | The operating guide says only OpenCode has an installer layout profile, and no hosted-service native-load run was recorded there. |
| Fresh native instances | No-model probes tested Codex 0.155.1, OpenCode 1.18.32, Claude Code 2.1.280 and Pi 0.73.1 with isolated per-step material. | Those probes show the material reached native prompt input or tool listings. They did not establish model use or a verified customer result. |
| Customer-side model relay | The confined harness process can call an existing local model relay with a dummy compatibility key while the host retains its real provider route. | The checked path is text-only. A full native tool bridge, per-use credential resolution and multi-client qualification are planned. |
| Native protocol connection | Codex, Claude Code and OpenCode have tested or documented protocol configuration locations. | The pinned Pi version has no native Model Context Protocol client. Connection config presence alone does not prove initialization, tool use or permission. |

The current service's protocol versions and the native client's negotiated
binding must be checked at initialization and at use. A server that supports
two protocol revisions does not make every client, plugin or local candidate
compatible with both. The [roadmap's protocol entry](../roadmap/roadmap.yaml)
holds the current qualified service revisions.

## Proposed one-step client journey

This is the intended customer path. Each transition should produce a typed,
versioned observation tied to the same task, step, package and client
identities.

1. The invited customer signs in, creates a personal Baltor client key and
   connects a supported harness. The key belongs to the hosted library
   access path and stays with the customer-side host.
2. A focused step declares its typed input, expected output, permitted
   effects, model authority and limits. The step's owning Loop selects a
   client and qualified layout profile.
3. The host searches the approved active library. Search returns small
   references. It checks client support, rights, exact release, entitlement,
   declared effects, relevance and the customer's library settings before
   fetching a body.
4. The host downloads selected packages, verifies package and per-file
   digests, and prepares a placement record. A package can have several
   source files; reviewed client renderings have their own exact identities.
   Changed bytes require their own review.
5. The host creates a fresh task root, clean home and isolated client
   configuration. It materializes only the selected files to paths supported
   by that exact client version. Task materials and outputs have separate
   scopes. The placement record stays outside the model-writable folder.
6. The client starts under the qualified adapter. A native discovery or
   prompt-input probe records selected and inherited sources. Any unexpected
   ancestor instruction, global skill, bundled extension or untrusted
   project configuration is handled under an explicit profile decision.
7. The customer-side host resolves authorized model and tool connections.
   The client sees only its scoped local facade where supported. The real
   provider and third-party credentials stay in the host or the relevant
   upstream tool process.
8. The client works on its assignment. Physical model calls, native turns,
   tool calls, retries, cancellation and results are related to the owning
   Loop's budget and Run History. Completion reported by the client is a
   candidate result. Independent checks decide whether the step is accepted.
9. The host closes the process, local capabilities and temporary scopes.
   Reuse of approved methods or verified code in another step still creates
   a new placement decision under that step's authority.

The [one-harness-per-step product intent](../../README.md#one-harness-for-each-step)
does not require only one model turn or one attempt. An owning Loop may
continue or choose a permitted different harness after a failure while
preserving cumulative budget, prior effects and acceptance conditions.

## Native layout profiles

These paths are the observed starting points for the pinned client versions
in the [placement research](NATIVE-HARNESS-INTELLIGENCE-PLACEMENT-2026-09-22.md).
They are candidate entries for a versioned layout profile, not a promise
that each file kind is already served or supported by the installer.

| Client and tested version | Step instruction | Selected skill and connection path |
|---|---|---|
| Codex 0.155.1 | `work/AGENTS.md` | `work/.agents/skills/<name>/SKILL.md`; isolated `CODEX_HOME/config.toml` or trusted `work/.codex/config.toml` for a Model Context Protocol server. |
| Claude Code 2.1.280 | `work/CLAUDE.md`, optionally importing `AGENTS.md` | `work/.claude/skills/<name>/SKILL.md`; project `.mcp.json` and supported isolated settings. |
| OpenCode 1.18.32 | `work/AGENTS.md` | `work/.opencode/skills/<name>/SKILL.md`; `work/opencode.json` for supported protocol connections. |
| Pi 0.73.1 | `work/AGENTS.md` | `work/.pi/skills/<name>/SKILL.md`; isolated `PI_CODING_AGENT_DIR`. A protocol server needs a separately qualified extension. |

`CODEX.md` is not Codex's default instruction file. The
[configured-fallback probe](../../artifacts/harness-intelligence-format-pilot-2026-09-22/context/CODEX-MD-CONFIGURED-FALLBACK-2026-09-22.json)
found that Codex 0.155.1 ignored it with the default fallback list and read
it when an isolated configuration explicitly named it. Every layout profile
must bind the exact client version, settings, trust requirements, source
paths, render rules, collisions, native discovery probe and activation rule.

An isolated working directory by itself is insufficient: the native
instance experiment observed global skills and ancestor instructions under
some configurations. A clean home, controlled parent directory and explicit
record of bundled sources are part of the proposed default. Plugins,
scripts, hooks and configuration files receive a stronger effect and
dependency review than passive text. A multi-file skill is one package with
individually hashed files. Client-specific renderings or model-conditioned
wording are versions or variants of that package, not extra independent
methods in the library count.

## Customer endpoints and credentials

The hosted intelligence service receives the Baltor library credential for
authorized search and download. It does not need the customer's model or
third-party tool credential. The local host has three distinct identities to
manage: library access, model endpoint access, and each external tool
server's access. They must never be substituted for one another.

The [credential research](CUSTOMER-ENDPOINTS-AND-CREDENTIAL-DELEGATION-2026-09-22.md)
recommends a customer-side connection and credential broker. The existing
confined process already relays model calls through a local socket. A planned
extension would resolve a private credential reference at the physical call,
bind it to one selected endpoint, and expose only authorized model and tool
operations to the fresh client. The host retains exact effect approval,
expiry, use ceiling and cumulative accounting. A client that cannot use the
bridge needs a separately qualified, narrower-trust profile for one process;
raw keys are not written into step files, command lines, exported traces or
the hosted library.

| Customer setup | Required interpretation |
|---|---|
| Model server at `127.0.0.1` | That address belongs to the calling network namespace. The customer-side host can reach a local service if it runs in the right namespace. A container or remote Baltor server cannot infer access to the customer's laptop. |
| Local Ollama without authentication | A qualified route can use `auth_scheme: none`. A local address does not prove that the chosen model stays local; signed-in Ollama may forward to cloud under customer settings. |
| Ollama Cloud or another provider key | Resolve the customer's credential only for the selected provider origin and model route. Record source-backed output capacity, allowed spending and actual usage. |
| Model Context Protocol server | The host owns an exact server connection and credential audience. A per-step bridge filters tools and effects; protocol configuration copied into a folder does not itself authorize a tool. |
| Native client account | If a qualified adapter uses the client's own login, state which usage and cancellation controls are observable. Refuse an assignment that requires an unavailable control. |

The first customer setup screen should ask for the selected client and
version, whether the model endpoint is local or cloud, the reachable address
from the customer-side host, a credential **reference** when needed, allowed
tools, and a spending or call budget. It should test reachability and version
compatibility without exposing secrets. Defaults should favor the customer's
existing local configuration and minimal permitted tools, but every route
remains an explicit typed choice. A fallback never silently changes
provider, effect permission, output allocation or network location.

## Evidence ladder and customer acceptance

The client experience needs a visible ladder of facts for each selected
package. A later fact never erases a failed or missing earlier fact.

| Fact | Evidence needed |
|---|---|
| Offered | The active release and this account's grant named the package. |
| Fetched | The response bytes matched the selected version and digest. |
| Placed | Every package file landed at its qualified native destination with the matching digest. |
| Discovered | The exact client listed or observed the selected path and rejected unselected inherited material. |
| Loaded | The client's own prompt-input or tool record shows the selected content or tool schema entering the step. A listing alone does not satisfy this fact. |
| Used | A native event or inspected model turn shows a specific selected item being read, cited, invoked or applied. |
| Verified | An independent evaluator accepts the step output against its contract. |
| Helpful | A matched comparison establishes that the package improved the chosen outcome under the same task, model, harness version and budget. |

The current [installer guide](../guides/native-client-material-loading.md)
reaches client-reported listing in its local OpenCode checks and explicitly
leaves model-turn use and independent help unproven. The [private beta
gate](../verification/SAAS-LIVE-READINESS-AND-CUSTOMER-JOURNEY-2026-09-22.md)
still needs an invited person's live search, selected fetch, native load and
accepted step under a named release. The user interface should display the
highest proved state, with failures and unknowns visible. It should not turn
client discovery, a model's confidence or a producer's self-review into an
approval or success claim.

## Discriminating checks for the client boundary

| Known-wrong setup | Required result |
|---|---|
| Put a selected skill in another client's path, or place `CODEX.md` under default Codex settings | Native load remains unproven and the step refuses a loaded claim. |
| Add an unselected global skill or ancestor instruction | The isolated launch detects or excludes it and reports the exact source. |
| Change a script, reference, connection file or package manifest after approval | Per-file and package digest checks refuse placement or activation. |
| Insert a symlink escape, duplicate native destination or unsupported plugin kind | Materialization refuses before client launch. |
| Supply a provider key in a downloaded configuration, command line or report | The boundary refuses the value before a process starts and does not echo it. |
| Point a container at the host's `127.0.0.1` without a route | Reachability fails explicitly; no silent public bind or provider switch occurs. |
| Ask a step to invoke another step's tool or use an expired local capability | The broker refuses the exact call before the upstream effect. |
| Disconnect after an external mutation with unknown completion | Record unknown completion and reconcile it; no automatic replay occurs. |
| Return a native success message without the required output or independent check | The owning Loop retains a candidate result and does not accept the step. |

Qualification should run against the exact installed client version and a
frozen task. A successful local no-model probe establishes placement and
load behavior only. A model-backed accepted step, measured with and without
selected material under matched conditions, is the evidence for the claimed
customer benefit. The [roadmap](../roadmap/roadmap.yaml) records the build
and release state.
