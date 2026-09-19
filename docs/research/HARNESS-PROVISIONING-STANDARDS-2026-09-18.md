# Harness provisioning standards, read on 2026-09-18

Kind: research record. Every claim below carries the page it was read from and
the date it was read. Claims are marked documented when the cited page states
them, and inferred when this record draws a conclusion the page does not state.
Nothing here is a statement about Loop Engine behavior; the Loop Engine section
at the end separates what is implemented from what is proposed.

## Why this was read

Coding harnesses have started to agree on where an instance finds its
instructions, its skills, its tools, and its packages. If that agreement is
real, then a system that launches harness instances does not need to rebuild
each harness. It needs to decide what each instance should be given, hand it
over in the form that harness reads, record what was actually loaded, and
measure whether the configuration was worth its cost. This record establishes
which parts of that are settled by a published format and which parts every
system still has to solve for itself.

## What could not be read

State the gaps first. The Zed rules page returned a not found status, so the
specification source in the Zed repository was read instead. Several OpenAI
Codex documentation paths redirect, and one of them returns not found; the
working page is the agent configuration page cited below. The Model Context
Protocol registry documentation page returned a title with no body. Two domains
that carry the name of the foundation now stewarding AGENTS.md are parked
domain sale pages and are not the foundation.

## AGENTS.md

### Governance and what the format specifies

The AGENTS.md project states that it is stewarded by the Agentic AI Foundation
under the Linux Foundation, and the technical charter in the project repository
records adoption on 8 December 2025, with the project license stated as MIT and
documentation under Creative Commons Attribution 4.0. The canonical repository
moved from the OpenAI organization to the AGENTS.md organization. Documented,
from <https://agents.md/> and the technical charter file in
<https://github.com/agentsmd/agents.md>.

The format specifies almost nothing. The project's own questions and answers
state that there are no required fields, that the file is ordinary Markdown,
that the closest file to the edited file wins, and that a large repository
should use nested files. The site calls it a simple open format and does not
call it a specification or a standard. Documented.

Inferred: the only portable content in AGENTS.md is a file name and one
precedence sentence. Size limits, merge order, and whether a nested file
replaces or adds to its parent are decided by each harness, and the harnesses
do not agree. A system that emits one instruction tree and expects the same
context in every harness will not get it.

### What each harness actually does

Every row was read from that vendor's own page on 2026-09-18 or 2026-09-19.

| Harness | Reads | Behavior when its own file also exists | Documented ceiling |
|---|---|---|---|
| OpenAI Codex | `AGENTS.override.md`, then `AGENTS.md`, from the repository root down to the working directory | the override file beats the standard file at the same level; other names are ignored unless listed in the fallback setting | 32 kibibytes by default, and it stops adding files at the limit |
| Claude Code | `AGENTS.md` and `.claude/AGENTS.md` | by default, if any `CLAUDE.md` or `CLAUDE.local.md` exists at or above the working directory, only those are read and `AGENTS.md` is ignored; a setting selects both, or managed files only | guidance of about two hundred lines per file, not enforced |
| Cursor | `AGENTS.md` at the project root, and nested files | offered as an alternative to the rules directory; the page does not state which wins | none stated |
| Gemini command line interface | `GEMINI.md` by default; `AGENTS.md` only when the context file name setting lists it | the setting takes a list, and the contents of every file found are joined | none stated |
| Zed | one of nine names in a fixed order, with `AGENTS.md` seventh and `CLAUDE.md` eighth | the first matching file is used and the rest are ignored | none stated |
| OpenCode | `AGENTS.md`, falling back to `CLAUDE.md`, walking up from the working directory | all of them are combined | none stated |
| Factory | `AGENTS.md`, and `CLAUDE.md` for compatibility | nested files refine the root, and project files override personal defaults | eighty thousand characters at first load, forty thousand for later discovery |
| Amp | `AGENTS.md`, falling back per directory to `AGENT.md` or `CLAUDE.md` | the standard name wins inside its own directory | none stated |
| GitHub Copilot | one or more `AGENTS.md` files anywhere in the repository | the nearest file takes precedence, and a repository wide file and a path matching file are both used | none stated |
| Visual Studio Code | the workspace root `AGENTS.md`, with nested files marked experimental | settings toggle both behaviors | none stated |
| Windsurf | `AGENTS.md` in any directory, through the same rules engine as its own rule files | root level files carry no front matter and are always on | six thousand characters for the global file, twelve thousand per workspace rule file |
| Aider | `CONVENTIONS.md`, and only when the user passes it | the Aider page does not mention `AGENTS.md` at all | none stated |

Documented, each from the vendor page. The AGENTS.md site lists twenty four
adopters; a logo on that site is a claim by the project, not by the vendor, so
adopters not confirmed from their own pages are not treated as confirmed here.

### How many repositories use it

The project states over sixty thousand open source projects. Documented, from
<https://agents.md/>.

A direct measurement through the GitHub code search interface returned
approximately 972,800 for the standard file name, and also returned a figure
for `SKILL.md` that is larger than the plausible number of files on the service
while a stricter path query for the same name returned zero. Observed and
rejected: those totals are ranking estimates, not counts, and this record does
not quote them as adoption figures.

## Skills

### The published format

The Agent Skills format is published at <https://agentskills.io/specification>
and states that it was developed by Anthropic and released as an open standard.
The specification page carries no version number. Documented.

The complete front matter surface is six fields. `name` and `description` are
required; `name` is limited to sixty four characters of lower case letters,
digits, and single hyphens, and must match the directory it sits in;
`description` is limited to one thousand and twenty four characters. The
optional fields are `license`, `compatibility` at five hundred characters,
`metadata` as a map of strings, and `allowed-tools` as a space separated list
that the specification itself marks experimental, with support that may vary
between implementations. Documented.

Progressive disclosure is a recommendation about layout, not a protocol: names
and descriptions at roughly one hundred tokens are loaded for every skill,
the body under five thousand tokens is loaded on activation, and scripts,
references, and assets are loaded only when needed. Documented.

### The directory convergence

Five harnesses now read the same vendor neutral skills directory, `.agents`,
alongside their own: OpenAI Codex, the Gemini command line interface, GitHub
Copilot, Cursor, and Factory. Cursor also reads the Claude and Codex
directories for compatibility. Documented, from each vendor's page.

Inferred: `.agents` is becoming for skills what `AGENTS.md` is for
instructions, a convention that several vendors adopted without a specification
behind it. Writing there is a bet on convention, not a contract.

### Four vocabularies, one file name

This is where the open standard frays, and it matters for anyone who ships
skills to more than one harness.

- Claude Code reads roughly twenty fields beyond the six, and rejects unknown
  keys when a skill is uploaded to its hosted product. Its combined description
  limit is one thousand five hundred and thirty six characters, where the open
  specification states one thousand and twenty four for the description alone.
- Cursor reads seven fields, adopts two of Claude Code's extensions, adds two
  of its own, and does not list `allowed-tools`.
- OpenAI Codex keeps the two required fields in the skill file and moves
  capability and policy into a separate sidecar file, including tool
  dependencies and whether implicit invocation is allowed.
- The Devin command line interface reads nine fields including a permissions
  block with allow, deny, and ask scopes, and its page does not reference the
  open standard.

Documented, from each vendor's page. One file name, four incompatible front
matter vocabularies, and two different limits for the same field.

### Skills over the Model Context Protocol

The skills extension to the Model Context Protocol reached final status on
13 September 2026, five days before this reading. Documented, from
<https://modelcontextprotocol.io/extensions/skills/overview>.

It is the only provisioning format read here that makes integrity verification
mandatory. Every skill entry carries a manifest naming, for each file, a
location, a SHA-256 digest, and a byte size. A host must restrict reads to the
retained manifest, must verify size and digest before use, and must compare
parsed front matter field by field against the entry. A persisted approval must
bind to the complete set of locations and digests, and a changed, added, or
removed file revokes that approval. Servers should stay under five hundred and
twelve files or sixteen mebibytes per skill. Skill content is to be treated as
untrusted input, and host side code execution or a permission grant requires
explicit approval per skill. Documented.

## The Model Context Protocol

The current protocol version is 2026-07-28, and versions are dated by the last
backward incompatible change rather than incremented for compatible ones. The
previous revision is 2025-11-25. Governance sits with a Linux Foundation
project series, with the code and specification under Apache 2.0. Documented,
from <https://modelcontextprotocol.io/specification/versioning> and
<https://modelcontextprotocol.io/community/governance>.

The current revision is a large breaking change. Sessions and the session
identifier are removed, the initialization handshake is removed and the
protocol is stateless, a discovery call becomes mandatory, a listen method
replaces the earlier subscription mechanism, results carry a result type, and
list and read results carry a time to live and a cache scope. Roots, sampling,
and logging are deprecated, as is the earlier event stream transport and
dynamic client registration. The minimum deprecation window is twelve months.
Documented, from the changelog for that revision.

Two transports are standard: standard input and output to a client launched
subprocess, and streamable Hypertext Transfer Protocol to a single endpoint.
Documented.

There is no specification for how a host declares which servers to run. The
file that several harnesses read, `.mcp.json`, is a Claude Code convention that
others have partly copied with different field names and different scope
models. OpenCode publishes a schema for its configuration file. Documented.

The registry is in preview with a frozen interface and a warning that breaking
changes or data resets may occur. Package entries carry a registry type, an
identifier, a version, and a transport, and an integrity digest exists for
bundle packages only. Documented.

## Plugins and marketplaces

One harness publishes a full plugin manifest and marketplace format. A plugin
may carry skills, commands, agents, hooks, protocol servers, language server
entries, executables, and typed user configuration, where a configuration field
may be marked sensitive so that it is masked and stored in secure storage.
Dependencies carry version constraints. Documented, from
<https://code.claude.com/docs/en/plugins-reference>.

The marketplace format carries the best developed pinning in this survey. A
source may be a repository with a branch or tag and an immutable commit, where
the commit wins when both are present; an archive with a SHA-256 digest that is
verified on every download and fails the install on mismatch, with caps of two
hundred and fifty six mebibytes and twenty thousand entries; a package registry
entry with a version range; or a local path, which is not pinned. Documented.

Cryptographic signing is documented nowhere. This was checked specifically in
the plugin reference, the bundle manifest specification, the protocol registry,
and the Gemini extension reference. Digests yes, signatures no. Documented
absence.

## What carries integrity, and what declares permission

| Format | Digest | Signature | Version pin |
|---|---|---|---|
| `AGENTS.md` | none | none | none |
| `SKILL.md` on a file system | none | none | none, the format has no version field |
| skills over the protocol | SHA-256 per file, mandatory, verified before use | none | the manifest replaces versioning |
| protocol server declarations | none | none | only what the command line in the entry pins |
| protocol registry entry | a file digest for bundle packages only | not documented | a version string |
| plugin marketplace entry | a digest for archive sources, enforced | not documented | version, branch, commit, package range |
| development container feature | a digest in the lock file, and a resolved digest for registry sources | not documented | a version tag plus the lock file |

Documented, each from the format's own page.

On permission, the answer is short. No vendor neutral format states what an
instance is allowed to do. The one candidate field in the skills format is
marked experimental by its own specification, one major harness omits it
entirely, and in the harness that does implement it the field is documented as
not gated by workspace trust. Effects such as file writes, network access,
spending, and external changes are declared nowhere in the instruction or skill
formats. The only enforcement point that exists in any of these products is a
tool level hook, which is one vendor's mechanism. Documented, including the
statement from one vendor's own memory documentation that instructions are
context rather than enforced configuration.

## What a provisioning system still has to solve

These are gaps in the published formats, not judgements about any product.

1. Fetching a large body an instance was told about. Progressive disclosure is
   a layout recommendation. Only the protocol extension defines how a reference
   is addressed, authorized, and fetched when the instance does not already
   hold the file system that carries it.
2. Pinning and verifying a whole set. A lock file exists for containers and per
   item pinning exists for one plugin format, but nothing pins one instance
   configuration, meaning this instruction revision with these skills and these
   servers and these hooks, as a single verifiable unit.
3. No integrity at all on the two most used formats. A system that ships
   instruction files and file system skills must compute and record its own
   digests, because no consumer will check.
4. No signatures anywhere. Provenance today is the repository someone trusted.
5. No portable statement of authority. Anything a system wants to say about
   what an instance may do has to be carried in its own typed fields and
   enforced at its own boundary.
6. Precedence is not portable. Closest wins, first match wins, join from the
   root down, both apply, and one file suppresses the other are five different
   resolutions of the same situation, all documented by different vendors.
7. Ceilings differ by an order of magnitude and truncation is silent. Thirty
   two kibibytes, eighty thousand characters, twelve thousand characters, and
   nothing stated are all real values from vendor pages.
8. Almost no harness documents any confirmation that a file was loaded. File
   presence is not proof of loading, and only one vendor documents an
   observable signal for it.
9. No vendor neutral record describes a whole provisioned instance. The closest
   published format is one vendor's agent definition front matter.
10. Skill identity and collision across sources is per harness and mostly
    undocumented, except in the protocol extension, which had to solve it
    explicitly.

## What Loop Engine does about it

Implemented on 2026-09-18, with offline checks and killed mutants, and no live
harness run behind it yet: `core/instance_instructions` composes one
instruction file for each harness instance before its adapter runs. The
standard file name is the default, and the second name a particular harness
reads is data in a table with that harness's documented ceiling beside it, so a
file over the ceiling is refused rather than truncated where nobody sees it.
The Claude Code entry writes an import rather than a copy, which is the
documented compatibility path when that harness would otherwise ignore the
standard file. The body is composed from typed fields, so a model cannot write
its own instructions. A section that names an effect the step does not hold
refuses the dispatch before the instance starts, because a file describing
authority the instance lacks teaches the instance to try. A digest travels in a
trailing marker, verification recomputes it rather than trusting it, and a file
the engine did not write is left alone.

Proposed, not implemented: the provisioning manifest of step S-2.2, which would
name every item an instance may fetch with its kind, identity, digest, size,
license, and declared effects, and the record of what was placed against what
was used against whether the outcome was verified. The gaps above say what that
manifest has to carry that no published format provides: a digest on everything
including instruction files, one pin over the whole set, a typed statement of
authority, and a confirmation that the instance loaded what it was given
rather than an assumption that it did.

The intelligence layers already hold the pieces that decide what goes into an
instance. Context Intelligence holds instruction elements, question forms, and
packs as records with identity and digest, with bodies kept behind references.
Code Intelligence holds capabilities with contracts, tests, effects, and
digests. Runtime History and Solution Intelligence holds what a configuration
cost and whether an independent check accepted it, which is the evidence that
would eventually support a claim about which provisioning set is efficient. The
heuristic adoption policy stands between that evidence and any learned rule: an
exact atomic fingerprint is the only exception below the declared one million
runs.

## Sources

All read 2026-09-18 or 2026-09-19.

- <https://agents.md/> and <https://github.com/agentsmd/agents.md>
- <https://agentskills.io/specification>
- <https://code.claude.com/docs/en/memory>, <https://code.claude.com/docs/en/skills>,
  <https://code.claude.com/docs/en/mcp>, <https://code.claude.com/docs/en/plugins-reference>,
  <https://code.claude.com/docs/en/plugin-marketplaces>, <https://code.claude.com/docs/en/hooks>,
  <https://code.claude.com/docs/en/sub-agents>
- <https://learn.chatgpt.com/docs/agent-configuration/agents-md> and
  <https://learn.chatgpt.com/docs/build-skills>
- <https://cursor.com/docs/context/rules> and <https://cursor.com/docs/context/skills>
- <https://geminicli.com/docs/cli/skills/> and the Gemini command line interface repository
- <https://opencode.ai/docs/rules/> and <https://opencode.ai/docs/mcp-servers/>
- <https://aider.chat/docs/usage/conventions.html>
- the Zed repository rules specification source
- <https://ampcode.com/docs/customize/agents-md>
- <https://docs.factory.ai/cli/configuration/agents-md>
- <https://docs.devin.ai/onboard-devin/agents-md> and the Devin command line skill pages
- <https://docs.github.com/en/copilot/concepts/agents/about-agent-skills>
- <https://code.visualstudio.com/docs/copilot/customization/custom-instructions>
- <https://modelcontextprotocol.io/specification/versioning>,
  <https://modelcontextprotocol.io/specification/2026-07-28/basic/transports>,
  <https://modelcontextprotocol.io/extensions/skills/overview>,
  <https://modelcontextprotocol.io/community/governance>
- <https://github.com/modelcontextprotocol/registry> and
  <https://github.com/modelcontextprotocol/mcpb>
- <https://containers.dev> and the development container lock file specification
