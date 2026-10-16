# Product Hunt launch draft

Kind: draft for the owner to post from their personal Product Hunt account,
prepared October 16, 2026. Nothing has been posted or scheduled. Facts come
from the [fact sheet](../fact-sheet.md).

## Rules that apply

Read at <https://www.producthunt.com/launch> on October 16, 2026 at 14:30 UTC:

- "The only real rule here is that you cannot ask people directly to upvote
  your product." "Instead, ask them to visit and comment."
- "Company accounts are prohibited." Post as yourself, and add yourself as
  the maker.
- "12:01 am Pacific Time is the best time to launch for makers that are
  planning ahead." A scheduled launch lets you sleep through the start.

The submission form shows its own character counters. The tagline and
description below are within 60 and 260 characters, which fits the form even
where it allows a longer description.

## Fields

| Field | Text | Length |
| --- | --- | --- |
| Name | Baltor | 6 characters |
| Tagline | Ready files and research for every step your agent takes | 56 characters |
| Description | Baltor connects Claude Code, Codex, OpenCode, Pi, Cursor and other MCP apps to a library of more than 1.5 million harness files. Your agent searches, picks one and downloads the exact version with its source and licence. Agent Feeds is free through 2026. | 254 characters |
| Website | <https://baltor.ai> | |
| Pricing | Paid, with a free plan: Agent Feeds is free through December 31, 2026, and Public Good components are free with an account | |
| Topics | Developer Tools, Artificial Intelligence, Productivity | 3 topics; each topic page answered 200 at 14:50 UTC |
| Thumbnail | The Baltor tile, [`favicon-192.png`](../../../../src/loop_engine/core/service_runtime/web_assets/favicon-192.png), or `baltor-mark.svg` rendered at 240 by 240 pixels | See the [press kit](../press-kit.md#logo-and-icon-files) |

Two other taglines, if the first one reads wrong on the day:

- Give your coding agent a head start (35 characters)
- Exact-version files your coding agent fetches over MCP (54 characters)

## Maker's first comment

Post this as the first comment right after the launch goes live. Edit it into
your own words; the bracketed lines are yours to write.

> Hi Product Hunt, I'm `[OWNER: your name]`, and I make Baltor.
>
> `[OWNER: one or two sentences on why you built it, from your own work.]`
>
> Baltor gives the coding agent you already run, whether that is Claude Code,
> Codex, OpenCode, Pi, Cursor or another MCP app, one library to search when a
> step needs something. The agent gets back a short list, picks one component
> and downloads exactly that version, with its source, licence and a checksum
> for every file. The library holds more than 1.5 million harness component
> files: skills, subagents, commands, hooks, MCP server settings, code modules
> and creative files such as Godot shaders and Blender tools.
>
> You can try parts of it free today:
>
> - Agent Feeds: curated source collections your agent reads before it picks a
>   model or a tool. Free through December 31, 2026, and the public feeds need
>   no key.
> - Public Good: free components for public-benefit work, with a free account.
> - AgentAFK: local overnight tools, as a free public preview.
>
> The whole library is the Pro plan at $49 a month. Baltor never asks for your
> model key; your harness keeps calling your own provider.
>
> I would love to hear which harness you use, whether the setup entry worked
> the first time, and what your agent went looking for and did not find.

## Gallery

Use the desktop screenshots from the [press kit](../press-kit.md#screenshots).
Product Hunt recommends 1270 by 760 pixels; the 1440 by 900 captures scale to
1270 by 794 and crop to 1270 by 760 without losing the heading. Engineering can
make the crops with Pillow:

```bash
python3 -c "
from PIL import Image
for name in ['home', 'library', 'component', 'connect', 'pricing']:
    image = Image.open(f'showcase/marketing/launch-2026-10/screenshots/{name}-desktop.webp')
    image.resize((1270, 794), Image.LANCZOS).crop((0, 0, 1270, 760)).save(f'/absolute/new/folder/{name}-1270x760.png')
"
```

| Order | Image | Caption |
| --- | --- | --- |
| 1 | `home-desktop.webp` | Give your agent a head start, from the harness you already use. |
| 2 | `library-desktop.webp` | More than 1.5 million files: skills, tools, code, MCP settings and more. |
| 3 | `component-desktop.webp` | Every component shows its files, licence, exact version and recorded checks. |
| 4 | `connect-desktop.webp` | Connect over MCP, the REST API or a feed link. Your model key stays yours. |
| 5 | `pricing-desktop.webp` | Agent Feeds is free through 2026. The whole library is $49 a month. |

## Shoutouts

Product Hunt asks makers to credit tools they built with. These are tools the
repository records using; pick the ones you want to name: Claude Code, Codex,
OpenCode, Fly.io, Cloudflare and Stripe.

## On the day

- Schedule the launch for 12:01 a.m. Pacific on the launch day the
  [runbook](../launch-runbook.md) names.
- Tell your own audiences that Baltor launched and invite them to visit and
  comment. Never ask for an upvote, in a post, a message or a newsletter.
- Answer every comment the same day. Engineering watches the live service and
  sends you fixes to mention.
