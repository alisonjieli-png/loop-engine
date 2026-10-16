# Community posts

Kind: drafts for two communities whose self-promotion rules were read on
October 16, 2026, and the reasons other communities were left out. Nothing has
been posted. Facts come from the [fact sheet](../fact-sheet.md). Both forums
expect posts that reflect the author's own thinking, so treat each draft as a
starting point and rewrite it in your own words.

## Cursor Community Forum, Showcase category

Rules, read at <https://forum.cursor.com/guidelines> on October 16, 2026 at
14:35 UTC:

- "Sharing what you've built with or for Cursor is welcome and it's one of the
  best parts of this community. The Showcase category is an especially great
  place for this."
- "Contribute first. Be a community member, not just a marketer. Answer
  questions, share knowledge, and participate in discussions before linking
  your projects."
- "Be upfront. If you're sharing something you sell or profit from, say so."
- "Posts generated entirely by AI will likely be removed. While AI tools can
  help you draft or refine your writing, posts should reflect your own
  thoughts and understanding."

The Showcase category's own description reads "Show off what you've built
either using Cursor, or built to share with other Cursor users!" Before
posting, answer a few questions in the Support or Discussions categories, as
the rules ask.

Title: `Baltor: a file library your Cursor agent can search over MCP`

```text
I built Baltor, and I'm sharing it here because it plugs into Cursor as an MCP server. To be upfront: it is my product and the full library is a paid plan ($49 a month). Some of it is free, listed at the end.

What it does in Cursor: your agent gets Baltor's search and download tools. When a step needs a skill, a script, a rule file or an MCP server setting, the agent searches, gets a short list back (name, purpose, source, licence, version, checksum) and downloads only the item it picked, at that exact version. Anything that needs file, network or process access is only offered to a step that declares it.

Setup: add https://baltor.ai/mcp as a remote MCP server and Cursor asks you to sign in, or add the key-based entry to .cursor/mcp.json in your project (or ~/.cursor/mcp.json). That entry names the BALTOR_SERVICE_TOKEN environment variable, never the key itself, so start Cursor from a terminal where it is set. You can check it in Cursor Settings under MCP. Full steps: https://baltor.ai/setup

Free parts: Agent Feeds, curated source collections your agent reads before it chooses a model or a tool, is free through December 31, 2026, and the public feeds need no account. Public Good components are free with an account.

I'd like feedback from Cursor users in particular: did the entry work the first time, and what did your agent search for that it didn't find?
```

## OpenAI Developer Community, Codex category

Rules, read at <https://community.openai.com/guidelines> on October 16, 2026
at 14:35 UTC:

- "Share the cool things you have built, but avoid repetitive or overly
  promotional posts. Contributions should be relevant to OpenAI products,
  developer work, or the category's purpose."
- Please don't "Promote or advertise services unrelated to OpenAI products,
  developer work, or the category's purpose." "Spamming other members with
  pitches or other forms of self-promotion will not be tolerated." Please
  don't "Cross-post the same issue in multiple topics or categories."

The Codex category covers "Discussions related to ChatGPT's coding tools and
abilities, such as the Codex agent". The draft leads with the setup, which is
useful to Codex users whether or not they subscribe. Post it once, in that one
category.

Title: `Giving Codex exact-version skills and tools over MCP, with OAuth`

```text
I've been connecting Codex to a library of harness files over MCP and wanted to share the setup, because the OAuth flow is two commands:

codex mcp add baltor --url https://baltor.ai/mcp
codex mcp login baltor

The second command opens a browser sign-in with an explicit consent screen. Your Baltor password is not handed to Codex, and the server never asks for your model key. A Baltor key in an environment variable also works for setups without OAuth.

Once connected, Codex can search the library and download only what a step needs: a skill, a subagent or command definition, a hook, an MCP server setting or a code module. Search returns short references (purpose, source, licence, version, checksum), never file bodies, so it doesn't flood the context. Downloads are exact versions with a SHA-256 checksum for each file, and anything that needs file, network or process access is only offered when the step declares it.

Disclosure: I built this (Baltor). The full library is a paid plan at $49 a month. Agent Feeds, curated source collections for decisions such as choosing a coding model, is free through December 31, 2026, and the public feeds need no account: https://baltor.ai/feeds/collections/coding-benchmarks.md

If you use Codex with MCP servers, I'd like to know whether the login worked for you and what you would want a step to fetch.
```

## Checked and left out

| Community | What was found on October 16, 2026 | Decision |
| --- | --- | --- |
| Reddit (for example r/LocalLLaMA, r/ClaudeAI, r/mcp) | Read-only requests from this network were answered "You've been blocked by network security", so no subreddit's rules could be read. | No draft. Read each subreddit's rules in your own browser first; many limit self-promotion and some refuse AI-written posts. |
| DEV Community | The [AI-assisted article guidelines](https://dev.to/guidelines-for-ai-assisted-articles-on-dev) (last updated April 8, 2024) say such articles should not "Promote any business, program, or course (including your own)." The [organization guide](https://dev.to/help/organizations/maximizing-your-dev-organization) asks to "avoid overly promotional content" and points to DEV Advertising. | No draft, because an engineering draft is AI-assisted. A technical article you write yourself remains possible. |
| Lobsters | The [about page](https://lobste.rs/about) keeps self-promotion "less than a quarter of one's stories and comments", lets members flag content "designed to promote a commercial service" as spam, closes the show tag to users in their first 70 days and admits members by invitation. | Not suitable for a launch post. |
| Indie Hackers | No posting-rules page was found; the guideline addresses tried answered 404. | No draft until the rules are found. |
| Hugging Face forums | The [guidelines](https://discuss.huggingface.co/guidelines) prohibit spam, and the Show and Tell category is for Spaces, models and datasets. | Not a fit for Baltor. |
| Hacker News | Covered by the [Show HN kit](show-hn.md). Comments must not contain generated or AI-edited text. | Owner writes the post and every reply. |
