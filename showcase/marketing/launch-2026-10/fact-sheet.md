# Baltor launch fact sheet

Kind: dated reference for the October 2026 launch drafts. Every checkable fact
in this kit comes from this page. Each row names its source and when it was
read. Live reads are signed-out GET requests to the public sites on Friday,
October 16, 2026, between 14:25 and 14:45 UTC (10:25 to 10:45 a.m. Eastern),
called the read window below. Where a read has an exact time, the row gives
it. Recorded facts come from release records in this repository.

Read the live value again on the posting day. Prices, counts and plan details
change with releases. When a value differs, correct the draft and this page
before posting.

## The product in one paragraph

Baltor gives the AI harness a person already uses, such as Claude Code, Codex,
OpenCode, Pi or Cursor, source-backed research and ready files for each step of
a task. A harness searches one library over MCP or the API, inspects a short
result and downloads the exact version it chose. The person keeps their own
model access. Baltor's positioning line is harness and agent optimized
operation.

## Library

| Fact | Value | Source and read time |
| --- | --- | --- |
| Distinct files in the library | 1,560,856. Identical shared files count once. | `GET https://baltor.ai/api/v1/capabilities`, field `result.library.file_population.distinct_files`, 14:25:24 UTC. The [library page](https://baltor.ai/library) heading showed the same number at 14:40:27 UTC. |
| Harness components (items that group one or more files) | 256,380 | Same read, fields `served_items` and `file_population.packages`. Say "files" in marketing copy; this row is for reference. |
| File placements | 2,254,815, of which 693,959 repeat a file already counted elsewhere in the library | Same read, fields `file_placements` and `duplicate_file_placements` |
| Kinds of harness file | 13: skills, instruction files, rules, subagents, commands, hooks, plugin manifests, plugin marketplaces, MCP server settings, harness settings, contract schemas, code modules and 3D models | [Library page](https://baltor.ai/library), "What is in it", read window |
| Components by kind | Code modules 131,369; contract schemas 91,157; skills 11,358; MCP server settings 7,823; subagents 3,865; commands 3,771; instruction files 2,268; rules 1,675; plugin manifests 1,656; plugin marketplaces 733; hooks 652; harness settings 49; 3D models 4 | Library page, same read. The kinds sum to 256,380. |
| Recorded library release | Release `29a2bc33c313`, state revision 41, confirmed October 9, 2026 at 18:13 UTC: 256,380 components and 1,560,856 distinct files after adding 413 components and 3,187 new files, with nothing replaced or withdrawn | [Publication record](../../../artifacts/architecture-audit-2026-09-19/catalogue-creative-originals-2026-10-09.json). The library page says this release has been served since October 15, 2026 at 8:52 UTC. |
| Next library milestone | Two million distinct served files | [North star](../../../docs/architecture/NORTH-STAR.md). A target, not a count. |
| What each download carries | Source, licence and exact version, with a SHA-256 checksum for every file | Homepage and library page, read window |
| Declared effects | A component that needs file, network or process access is offered only to a step that declares it | Homepage; capabilities field `library.step_effects` |
| Example component page | CMYK halftone print screens: a Godot shader, MIT, 11 files, 174.9 KB, rendered in Godot 4.7.2 by its recorded check | [Component page](https://baltor.ai/gallery/post-halftone-dots), read window; screenshot `component-desktop.webp`, 14:40:30 UTC |

## Plans and prices

| Plan | Price | What it includes | Source |
| --- | --- | --- | --- |
| Basic, Agent Feeds | $9 a month standard price, free through December 31, 2026 (Eastern) | Curated source collections as JSON Feed, Markdown and RSS for each agent. No automatic charge; a paid subscription needs the customer's opt-in. | [Pricing](https://baltor.ai/pricing), 14:25:39 UTC; screenshot `pricing-desktop.webp`, 14:41:06 UTC |
| Pro, Agent Feeds + Harness Files | $49 a month | The whole library through MCP or the API. Model usage is separate. Cancel any time from the account page. | Same page; [Get started](https://baltor.ai/get-started) shows "Subscribe for $49 a month" |
| Max, Agent Feeds + Harness Files + Overnight / AFK Work | $99 a month, listed | The page says "Max subscriptions are not sold during this public preview." The local overnight tools are a free public preview and stay included with Pro. | Same page |

The measured unit is one downloaded component: one item at the version the
harness chose counts once a month. A search, a second look at the same result
and a refused download are not downloads. There is no overage billing.
Source: the pricing page and the homepage questions, same read.

Founding offer: the capabilities record reported `founding_offer_open: true`
at 14:25:24 UTC. The [deck](https://baltor.ai/deck) states that the first 10
accounts created through Baltor's sign-up hold Pro free each month. The number
of places left is not public; a signed-in account without a plan sees it. The
drafts leave this offer out because the places can run out within minutes of a
launch post.

## Accounts and connection

| Fact | Value | Source and read time |
| --- | --- | --- |
| Registration | Open. Sign-up is email first: the address, then the emailed link, then a password the person chooses. | Capabilities field `website.registration_available: true`, 14:25:24 UTC; Get started page |
| MCP endpoint | `https://baltor.ai/mcp`, Streamable HTTP, protocol revisions `2025-11-25` and `2026-07-28` | Capabilities, `protocol` |
| Sign-in for MCP apps | OAuth authorization code with PKCE and explicit consent, or a Baltor key read from the `BALTOR_SERVICE_TOKEN` environment variable | Capabilities, `authorization_server`; [Get set up](https://baltor.ai/setup) |
| Other routes | The REST API with a Baltor key, an OpenAPI tool server for apps such as Open WebUI, and public feed links that need no account or key | Get set up page, read window; screenshot `connect-desktop.webp`, 14:40:33 UTC |
| Model keys | "Baltor never asks for a model key." | Homepage questions |

## Harness support

| Claim to use | Source |
| --- | --- |
| Setup guides for Claude Code, Codex, OpenCode, Pi and the Baltor Harness | Get set up page and homepage, read window |
| Ready connection entries for Cursor, VS Code and Gemini CLI | Get set up page |
| Any other app that speaks MCP over Streamable HTTP connects to the same address | Get set up page |
| OAuth sign-in is listed for Claude Code, Claude on the web and Claude Desktop, Cursor, VS Code, Codex and OpenCode | Get set up page |
| A recorded end-to-end OAuth check from Claude Code passed on October 9, 2026 at 18:52 UTC | [Check record](../../../artifacts/quickstart-checks/quickstart-oauth-check-2026-10-09-2.json) |
| Gemma 4 31B in Pi, through Ollama Cloud, searched the library, installed a skill, and a new Pi session loaded and used it (one check on September 23, 2026) | [Case study](https://baltor.ai/case-studies/pi-and-gemma-4) |
| The homepage also lists MCP connections for Cursor, Gemini CLI, GitHub Copilot, Windsurf, Cline, Roo Code, Kilo Code, Aider, Goose, Amp, Kiro, Zed, Qwen Code, Crush, Factory Droid, Hermes Agent and OpenClaw | Homepage, read window. These are protocol connections, not tested file placement. |

## Brands and sites

All six answered HTTP 200 over HTTPS at 14:26:55 UTC, signed out.

| Site | Headline | What a visitor can do today |
| --- | --- | --- |
| [baltor.ai](https://baltor.ai) | "Give your agent a head start." | The combined site for all three offerings: library, feeds, overnight tools, setup guides, gallery, Public Good |
| [AgentFeeds](https://agentfeeds.si) | "Good decisions start upstream." | 19 decision collections, 60 registered sources, source documentation checked 2026-10-09. Public feeds, no account or model key. |
| [AgentFoundry](https://getagentfoundry.si) | "Start with something that works." | 376 public component examples, Public Good search and connection setup |
| [AgentAFK](https://agentafk.si) | "Leave a task. Keep the limits." | Local overnight tools, a free public preview. No account or payment. No hosted execution. |
| [AgentStudios](https://agentstudios.si) | "Working files for creative projects." | Visual components, editable source, and two original demos: Copper Current (motion) and First Light (music) |
| [Don't be a meat proxy](https://dontbeameatproxy.si) | "Don't be a meat proxy." | An AgentFeeds campaign: copy one instruction that points an agent at a source collection |

AgentBriefs (`agentbriefs.si`) did not answer within 25 seconds at 14:26 UTC.
Its domain purchase is owner-confirmed, and its site is not live. Leave it out
of launch copy.

## Public Good

| Fact | Value | Source and read time |
| --- | --- | --- |
| Collection | 448 harness components, 1,984 distinct files, 1,128 distinct useful files | `GET https://baltor.ai/api/v1/public-good`, 14:44:24 UTC |
| Coverage | All 17 Sustainable Development Goals have at least one component | Same read, `goals` |
| Access | Free with an enabled Baltor account; no paid plan, no proof of nonprofit status | Same read; [Public Good page](https://baltor.ai/public-good) |
| Fair use | Up to 60 requests and 64 MiB of responses per account each hour | Same read, `limits_description` |
| Grant dates | The current access grants expire on October 31 and November 1, 2026 (UTC) unless renewed | [October 15 handoff](../../../docs/context/SESSION-HANDOFF-2026-10-15-CLAUDE-TAKEOVER.md) |

## Live service and release

| Fact | Value | Source |
| --- | --- | --- |
| Application release | Release 93, created October 15, 2026 at 08:52:42 UTC, image `sha256:e5a4519b…`, source `bdc45955` | [Current deployment](../../../docs/architecture/MVP-CLIENT-SERVER.md#current-deployment); [release 93 record](../../../artifacts/architecture-audit-2026-09-19/pilot-release-93.json) |
| Rollback target | Release 92, image `sha256:aa73def1…`, no host-file restore needed | Same |
| Health | Ready, with all three required checks passing | `GET https://baltor.ai/api/v1/health`, read window |
| Public hostnames in the release check | 20: nine Baltor hosts, the direct Fly host and ten brand hosts | Current deployment |
| Development | 1,725 commits on `main` at revision `f2ae304e`; the first is dated August 25, 2026 | `git rev-list --count f2ae304e` |
| Operator | Baltor.AI, 1428 Bryn Mawr St, Saxton, PA 16678 | Footer of every site |

## Published measurements

| Study | Result as published | Source |
| --- | --- | --- |
| Data cleanup with and without library material (September 22 to 23, 2026) | Clearly better in 0 of 4 task families and clearly worse in 1; 45 to 446 percent more prompt tokens per step with the material. Baltor published it anyway. | [Case study](https://baltor.ai/case-studies/data-cleanup) |
| Pi and Gemma 4 (September 23, 2026) | Search, install, load and use of one skill in a fresh Pi session | [Case study](https://baltor.ai/case-studies/pi-and-gemma-4) |

No study has published a time, token or cost saving. Do not state one.

## Not established: do not claim

- customers, testimonials, logos, user counts or revenue (the owner supplies
  these from the account dashboards on the day; see the placeholders below);
- time, token or money savings, or better task results;
- ranked "best tool right now" answers, push alerts or a maintained news
  stream;
- hosted execution, cloud supervision, Max subscriptions or team plans;
- AgentBriefs, automatic reference-video recreation or a ChatGPT directory
  listing;
- that library components are "reviewed" (owner rule: count files, not
  review states).

## Placeholders the owner fills on the posting day

- `[OWNER: paying subscriptions today]` from the Stripe dashboard.
- `[OWNER: monthly recurring revenue today]` from the Stripe dashboard.
- `[OWNER: accounts created]` from the Administration view on baltor.ai.
- `[OWNER: one sentence on why you built this]`, in your own words.
