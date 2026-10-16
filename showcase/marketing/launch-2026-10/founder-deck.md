# Baltor founder deck

Kind: ten-slide founder deck in Markdown, prepared October 16, 2026, for
launch conversations, investor meetings and the Y Combinator interview. Each
section is one slide: what goes on the slide, the speaker notes and the
sources. Facts come from the [fact sheet](fact-sheet.md); refresh the counts
and prices on the day you present. The live website deck at
<https://baltor.ai/deck> covers the same product for visitors, and the two
should not make different promises.

Lines in `[OWNER: ...]` are facts only the owner has. Leave a placeholder out
of the slide rather than guessing it.

## Slide 1: The problem

On the slide: **Coding agents start every step without the right files.**

- A small step carries far more context than it needs.
- The skills, tools and settings that would help are scattered across many
  sites and repositories, with unclear licences and versions.
- Agents rewrite code that already exists, and the output is paid for again.
- People relay newsletters and posts to keep their agents current.

**Speaker notes.** Open with the experience every developer who runs Claude
Code, Codex or Cursor recognizes: you spend time assembling the agent's
working folder, hunting for a skill or an MCP server, checking whether it is
safe and current, and pasting yesterday's news into a chat so the agent
chooses well. `[OWNER: one moment when this cost you real time.]` The point to
land is that the agent is capable; what it lacks is the right material at the
right step.

**Sources.** Customer problems in the repository README, "The problems it
answers"; the "meat proxy" framing from the live campaign at
<https://dontbeameatproxy.si>.

## Slide 2: Why now

On the slide: **The formats became standards. Choosing and trusting the right
file did not.**

- Agent Skills became an open standard on December 18, 2025. AGENTS.md and
  the Model Context Protocol now sit with the Agentic AI Foundation under the
  Linux Foundation.
- In SkillsBench (June 2026), curated skills raised the mean pass rate from
  33.9 to 50.5 percent on 87 tasks; skills an agent wrote for itself scored
  8.1 to 11.5 points below no skills at all.
- A February 2026 study confirmed 157 of 98,380 skills from two registries as
  malicious.

**Speaker notes.** Every major harness now reads the same kinds of file, so
one library can serve all of them. The evidence says good material helps and
self-written material does not, and supply alone is not trust: someone has to
check the source, licence and declared effects of every file before a step
runs it. That is the job Baltor does once, for every harness.

**Sources.** The "Why now" slide of the live deck at <https://baltor.ai/deck>,
which records each figure's source (agentskills.io, agents.md, SkillsBench on
arXiv and the February 2026 study on arXiv).

## Slide 3: The product

On the slide: **One library, delivered one step at a time.**

- The harness searches and gets short references: name, purpose, source,
  licence, version and checksum. No file bodies.
- The step downloads only the component it chose, at that exact version.
- A component that needs file, network or process access goes only to a step
  that declares it.
- Three offerings: Agent Feeds to decide, Harness Files to build, Overnight /
  AFK Work to keep working.
- The customer keeps their own model access. Baltor never asks for a model
  key.

**Speaker notes.** The category name is harness and agent optimized operation.
A harness is the program that runs a coding agent. Baltor does not replace it
or call models for the customer; it supplies the material each step needs and
checks it on the way. Agent Feeds gives agents curated sources and comparison
questions before a decision, Harness Files is the library, and Overnight /
AFK Work is a set of local tools, in public preview, for long bounded runs on
the customer's own worker.

**Sources.** Fact sheet, "The product in one paragraph", "Library" and
"Accounts and connection".

## Slide 4: The demo path

On the slide: **From a component page to a file in the harness, in three
minutes.**

1. Open a component page, such as CMYK halftone print screens: its recorded
   render, 11 files, MIT licence and exact version.
2. Connect Claude Code with two commands from the Get set up page and sign in
   with OAuth.
3. Paste the line the page offers: "Search Baltor for 'CMYK halftone print
   screens' and show me its files before downloading."
4. The agent searches, shows the files and downloads that version; every file
   matches its checksum.
5. The free path: one feed link in `AGENTS.md`, read before the agent chooses
   a model.

**Speaker notes.** Rehearse on a clean machine the day before. Step 3 needs an
account with the library, either a Pro subscription or a founding place. Never
show a key or the Administration view on screen. If the network fails, show
the recorded screenshots from the press kit and say that you are showing a
recording. A recorded end-to-end OAuth check from Claude Code passed on
October 9, 2026.

**Sources.** Component page <https://baltor.ai/gallery/post-halftone-dots>;
Get set up page <https://baltor.ai/setup>; the
[OAuth check record](../../../artifacts/quickstart-checks/quickstart-oauth-check-2026-10-09-2.json);
screenshots in the [press kit](press-kit.md#screenshots).

## Slide 5: The library

On the slide: **1,560,856 files your harness can pick up.**

- 13 kinds, in 256,380 harness components. Identical files count once.
- Code modules, contract schemas, skills, MCP server settings, subagents,
  commands, instruction files, rules, plugin manifests, hooks, harness
  settings and 3D models.
- Every component carries its source, licence, exact version and a checksum
  for each file.
- Next milestone: two million distinct served files.

**Speaker notes.** The largest kinds are code modules (131,369 components)
and contract schemas (91,157), then skills (11,358) and MCP server settings
(7,823). Every component passes deterministic checks before it is served:
layout, digests, licences, provenance, secrets, declared effects and
duplicates. Sampled review continues after publication and withdraws what it
rejects. Creative material is part of the same library: Godot shaders,
Blender tools and procedural textures, each shown with the render its check
recorded.

**Sources.** Capabilities record and library page, October 16, 2026, 14:25
UTC; README, "How the library grows"; north star for the milestone.

## Slide 6: Harness support

On the slide: **Works with the harness the customer already runs.**

- Setup guides: Claude Code, Codex, OpenCode, Pi and the Baltor Harness.
- Ready entries: Cursor, VS Code and Gemini CLI. Any other app that speaks MCP
  uses the same address.
- OAuth sign-in for Claude Code, Claude on the web and Claude Desktop,
  Cursor, VS Code, Codex and OpenCode, or a Baltor key from the environment.
- Three routes: MCP, the REST and OpenAPI tool server, and feed links that
  need no key.

**Speaker notes.** The homepage also lists protocol connections for Cursor,
Gemini CLI, GitHub Copilot, Windsurf, Cline, Roo Code, Kilo Code, Aider,
Goose, Amp, Kiro, Zed, Qwen Code, Crush, Factory Droid, Hermes Agent and
OpenClaw. Recorded checks include the Claude Code OAuth check of October 9 and
a September 23 run in which Gemma 4 31B in Pi, through Ollama Cloud, searched
the library, installed a skill and used it in a new session. A downloadable
container worker ships with OpenCode and the Baltor Harness.

**Sources.** Get set up page and homepage, October 16, 2026; the
[Pi and Gemma 4 case study](https://baltor.ai/case-studies/pi-and-gemma-4).

## Slide 7: Brands

On the slide: **One backend, several front doors.**

| Site | For |
| --- | --- |
| baltor.ai | The combined site for all three offerings |
| AgentFeeds, agentfeeds.si | 19 decision collections, 60 registered sources |
| AgentFoundry, getagentfoundry.si | 376 public component examples |
| AgentAFK, agentafk.si | Local overnight tools, free public preview |
| AgentStudios, agentstudios.si | Working files for creative projects |
| Don't be a meat proxy, dontbeameatproxy.si | The AgentFeeds campaign |
| Baltor Public Good | Free components for all 17 Sustainable Development Goals |

**Speaker notes.** Each site speaks to one audience and leads to the same
account, library and setup flow. That gives several acquisition channels
without several products to maintain. Public Good holds 448 components and
1,984 files, free to anyone with an account, within fair-use limits.

**Sources.** Fact sheet, "Brands and sites" and "Public Good".

## Slide 8: Pricing

On the slide: **Start free. Add the library when you build.**

| Plan | Price |
| --- | --- |
| Basic, Agent Feeds | $9 a month, free through December 31, 2026 |
| Pro, Agent Feeds + Harness Files | $49 a month |
| Max, with Overnight / AFK Work | $99 a month, listed, not sold during the public preview |
| Public Good | Free with an account |

- The billing unit is one downloaded component at one version, counted once a
  month. No overage charges.

**Speaker notes.** Customers bring their own model access, so Baltor's cost
of service is hosting and delivery, not inference. Payments run through
Stripe checkout and the customer portal, live since September 21, 2026.
Customers cancel from their account page. The local overnight tools stay
included with Pro.

**Sources.** <https://baltor.ai/pricing>, read October 16, 2026 at 14:25 UTC;
the payments decision in the repository's AGENTS.md.

## Slide 9: Traction

On the slide: **Live, shipping daily, and measured in the open.**

- Application release 93 live since October 15, 2026, across 20 public
  hostnames, with registration open.
- The library grew from 96,120 files on October 1 to 1,560,856 on October 9.
- 1,725 commits since August 25, 2026.
- Paying subscriptions: `[OWNER: number today]`. Monthly recurring revenue:
  `[OWNER: amount today]`. Accounts: `[OWNER: number today]`.

**Speaker notes.** Lead with velocity: a live paid service, five brand sites
and a library past 1.5 million files, all shipped since late August.
`[OWNER: one line on the team, if you want one on this slide.]` State
customer numbers exactly as the dashboards show them on the day, without
rounding up. Baltor publishes its own measurements, including
the September data cleanup study, which found no benefit on that test; the
next studies use harder tasks with the same frozen design.

**Sources.** [Current deployment](../../../docs/architecture/MVP-CLIENT-SERVER.md#current-deployment);
release records 60, 70 and 80 and the October 9
[publication record](../../../artifacts/architecture-audit-2026-09-19/catalogue-creative-originals-2026-10-09.json);
`git rev-list --count f2ae304e`; Stripe and the Administration view for the
owner's numbers.

## Slide 10: Roadmap and ask

On the slide: **What comes next, and what would speed it up.**

- Two million distinct served files, then ten million.
- Saved feeds assigned to individual agents, with hosted delivery.
- Paired customer tasks with and without Baltor, published either way.
- Creative production: imports, media jobs and a reference-video demo.
- A team plan: one governed library across every harness a team uses.
- The ask: `[OWNER: amount, terms and use of funds]`, and introductions to
  developers and teams who run coding agents every day.

**Speaker notes.** Every item is a plan, in the order the delivery sequence
sets, not a shipped feature. Say which one the money accelerates first.
`[OWNER: the two or three introductions you want from this audience.]` For Y
Combinator, the standard deal is $500,000 on two SAFEs, and the Winter 2027
deadline is November 2, 2026 at 8 p.m. Pacific.

**Sources.** [North star](../../../docs/architecture/NORTH-STAR.md);
[delivery sequence](../../../docs/roadmap/DELIVERY-SEQUENCE.md);
<https://www.ycombinator.com/apply> and <https://www.ycombinator.com/deal>,
read October 16, 2026.
