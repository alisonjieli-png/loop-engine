# Show HN kit

Kind: posting kit for the owner, prepared October 16, 2026. Nothing has been
posted. Facts come from the [fact sheet](../fact-sheet.md).

## Why this kit has no finished body

Hacker News asks for posts written by hand. The rules, read on October 16,
2026 at 14:30 UTC:

- "Please don't put generated text in HN posts." and, for comments, "Don't
  post generated text or AI-edited text." ([guidelines](https://news.ycombinator.com/newsguidelines.html))
- "Write your text by hand. Don't use an LLM to generate any of it (not even
  a tiny bit, including to edit or spruce it up)." ([moderator's Show HN tips](https://news.ycombinator.com/item?id=22336638),
  edited March 28, 2026)
- "Show HN is for something you've made that other people can play with."
  "Please make it easy for users to try your thing out, ideally without
  barriers such as signups or emails." "Please don't ask friends to upvote or
  comment." ([Show HN rules](https://news.ycombinator.com/showhn.html))
- "Drop any language that sounds like marketing or sales." "Include text
  giving the backstory of how you came to work on this, and explaining what's
  different about it." "Don't have your username be that of your company or
  project." (moderator's tips)

So this kit gives title candidates, the link, the facts to cover and the
likely questions. The owner writes every sentence of the body and every reply
in their own words. A pasted draft would break the rule and can get the post
killed.

## Title

Pick one, or write your own in the same plain style. Each is under 80
characters including "Show HN: ". Avoid numbers in the title; the guidelines
ask moderators to crop gratuitous ones.

1. `Show HN: Baltor, a library of files your coding agent fetches for each step`
   (75 characters)
2. `Show HN: Baltor, skills, tools and code your coding agent fetches over MCP`
   (74 characters)
3. `Show HN: Baltor, exact-version harness files for Claude Code, Codex and Pi`
   (74 characters)

## Link

Submit `https://baltor.ai` with no tracking parameters. Several things on it
work without an account, which is what the Show HN rules ask for:

- a feed link an agent can read with no key:
  <https://baltor.ai/feeds/collections/coding-benchmarks.md>;
- component pages with their recorded renders, licences and file lists, for
  example <https://baltor.ai/gallery/post-halftone-dots>;
- the playable Ashen Wilds demo: <https://baltor.ai/demo/ashen-wilds>;
- the public capabilities record:
  `curl https://baltor.ai/api/v1/capabilities`.

## What the body should cover

Write it yourself, in this order, in a few short paragraphs. The facts in each
point are there for accuracy, not as sentences to copy.

1. **What it is.** A library your existing harness searches over MCP or the
   API. A step downloads only the component it chose, at an exact version.
2. **What to try in thirty seconds without an account.** Put the feed link
   above into `AGENTS.md` or `CLAUDE.md` and ask the agent to read it before
   choosing a model.
3. **Backstory.** `[OWNER: why you built it, from your own experience]`.
4. **How it works.** MCP over Streamable HTTP at `https://baltor.ai/mcp`, with
   OAuth (PKCE, explicit consent) or a Baltor key read from an environment
   variable. Search returns short references (name, purpose, source, licence,
   version, checksum), never file bodies, and at most 50 results. A download
   names the exact version and a SHA-256 checksum per file. A component that
   needs file, network or process access is offered only to a step that
   declares it.
5. **Where the files come from.** 1,560,856 distinct files across 13 kinds;
   identical files count once. Most of the count is code modules and contract
   schemas; there are also skills, subagents, commands, hooks, rules and MCP
   server settings. Sources are original first-party generation and outside
   projects whose licences allow reuse; every component passes deterministic
   checks (layout, digests, licences, provenance, secrets, declared effects,
   duplicates) before it is served, and sampled review continues after
   publication and withdraws what it rejects. Source: the repository README,
   "How the library grows".
6. **What it costs.** Agent Feeds is free through December 31, 2026. The whole
   library is $49 a month. Public Good components are free with an account.
   The local overnight tools are a free preview. Baltor never asks for a model
   key.
7. **What feedback you want.** One or two specific questions, for example:
   which harness you use and whether its setup entry worked first time, and
   what you wanted a step to fetch that was not there.

## Likely questions and the facts to answer with

Answer in your own words. These are facts, not lines.

| Question | Facts |
| --- | --- |
| How is this different from a skills directory or an MCP registry? | One connection serves many kinds of harness file, plus feeds for decisions. Every result carries source, licence, exact version and checksum, and declared effects are checked before a step receives a file. Say what is different; do not say "better" about a named product. |
| Where do 1.5 million files come from? | Fact sheet, "Library", and README "How the library grows". Most of the count is code modules (131,369 components) and contract schemas (91,157). |
| Does it actually help? | The published data cleanup study found no benefit on that test and one family got worse; Baltor published it anyway. No time or token saving is claimed. |
| Malicious or broken skills? | Deterministic checks run before publication; withdrawal after a rejected sample or a report. A checksum proves the bytes, not that a file suits the task. Downloaded files never run on their own; the harness decides. |
| Do you see my code or my model key? | Baltor never asks for a model key. Searches and downloads reach the service; local project files are not uploaded. See the [privacy notice](https://baltor.ai/privacy). |
| Is it open source? | The engine behind Baltor is MIT on GitHub; the hosted library is a paid service. |
| Why MCP and not a git repository? | Exact versions on demand, a step gets only what it asks for, keys can be revoked per tool, and one connection works across harnesses. |
| Who is behind it? | `[OWNER: your answer]` |

## On the day

- Post from your personal HN account, by hand, between 8:00 and 10:00 a.m.
  Eastern on a weekday. The [launch runbook](../launch-runbook.md) names the
  recommended day.
- Do not link the HN thread from LinkedIn, X or the newsletter, and do not ask
  anyone to upvote or comment.
- Stay in the thread for the day. Answer with facts. When something is broken,
  say so, fix it and reply when the fix is live.
- Include links to earlier HN threads about Baltor, if there are any:
  `[OWNER: earlier HN threads, or none]`.
