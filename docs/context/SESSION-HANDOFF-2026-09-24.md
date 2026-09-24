# Session handoff, September 24, 2026

This is the newest dated handoff. It records what is live after release 24,
what the owner asked for on September 24, 2026, what engineering decided and
why, every line of work in flight with its worktree, the scheduled jobs, and
the ordered work that remains. It was written while the session was still
running; a later record of the same day gets a new file name. The roadmap
remains the task authority, and the
[commit, push and release authority](../../AGENTS.md#commit-push-and-release-authority)
section of AGENTS.md remains the one statement of what engineering may do.

## What is live

- The Fly app `baltor-pilot` runs release 24, built from `main` at
  `961dc906`, image
  `sha256:e538318deef9ab06aeb34f591d2617aae7296879b0efdbaf72f54a69bdf1c7ab`,
  deployed at 12:47 UTC. The
  [release record](../../artifacts/architecture-audit-2026-09-19/pilot-release-24.json)
  holds the checks and the rollback: release 23 predates the account origin
  guard, so rolling back needs the two host blocks removed first.
- Public registration has been open since 13:00 UTC. Sign-up is email first,
  through Baltor's own flow. An account created at the identity provider first
  is refused and replaced. The provider's own public sign-up could not be
  closed at the source, because the management authorization refresh was
  refused with status 422; the service guard covers it, as the registration
  paragraph in AGENTS.md records.
- The founding offer gives the first 10 accounts Baltor Pro free each month.
  After the checking accounts were cleaned up, 0 of 10 places were used.
- Staff roles are fixed in code: superadmin, developer and analytics. Two
  superadmin staff accounts, both the owner's, are listed in the host file.
- The active catalogue release is `69da7ead` with 43 items, published without
  a redeploy.
- Nine hostnames answer: baltor.ai, www, app, docs, status, examples, demo,
  deck and baltor-pilot.fly.dev. The deck hostname has its DNS records, an
  issued certificate and a host allowance; it shows the homepage until the
  deck page lands.
- Release 24 live checks: 163 of 163 browser checks on each hostname with
  registration open, catalogue 7 of 7, service 19 of 19, account journeys 11
  of 11, and the staff dashboard 10 of 12. The two failures were mistakes in
  the checking script, recorded in the
  [release 24 evidence](../../artifacts/release-24-2026-09-24/README.md).

## Scheduled jobs

```text
Scheduled jobs
├── Live pulse (.github/workflows/live-pulse.yml)
│   ├── every six hours at minute 17, read only, no secret
│   ├── asks every hostname and the identity provider's health address,
│   │   which keeps the free identity project active
│   └── first run 36007128856 passed
├── Research watch (.github/workflows/research-watch.yml)
│   ├── daily at 07:41 UTC, bounded reads, no model call
│   ├── sources in tools/research_source_watch.json
│   ├── opens or updates the issue "Research watch: sources changed"
│   └── first run 36011495071 passed
└── Research team (a schedule inside one Claude Code session)
    ├── every second day at 06:43 local time
    ├── ends with the session, and at the latest seven days after
    │   September 24
    └── re-arm it in a new session with the prompt at the end of this file
```

## What the owner asked for on September 24

In order, quoted where the exact words matter.

1. Deployment and checks: "You may have to have more flexible rules and
   tests, have we completed a correct deployment".
2. Free accounts that staff can see and upgrade: "Do we allow people to create
   a free account so that I can see the free accounts in the backend and give
   them prildeges".
3. Superadmins who invite people by email, a review of candidates and harness
   files, the library counts, an updated README, and more demo, showcase and
   case study pages and subdomains.
4. Throughput: 100,000 fully vetted, searchable and usable files, then at
   least 1,000 more a day, from permissively licensed sources and our own
   generation.
5. A question about free services such as Supabase, Resend, Vercel, GitHub
   Actions, Cloudflare, PostHog and Sentry.
6. "we need to have a continuously updating database of millions of skills,
   tooks, code, functions, plugins, contracts, rules, agents, agent support
   files, agent support code, etc that coding harnesses can detect and freely
   use".
7. More agents working at once: agents that browse the sign-up flows like
   customers, with screenshots; search engine optimization and a blog; demo
   and deck subdomains; scale and swappable engines; custom harnesses and
   custom loop-nodes; a public directory of third-party services and the
   Model Context Protocol servers they offer; and starter setups, in their
   words "custom harness packages that include context about services to use,
   Fly, Supabase, etc with fallbacks, so that users can just launch an LLM
   from that preconfigured folder".
8. Separation, containerization and swappable engines for reasoning and
   decision steps as opposed to build steps.
9. Laya and Toolsmith research, and "we should have research teams run
   regularly to see new developments".
10. Jev has paused its sign-ups; which similar services could be built in.
11. A staff Model Context Protocol server or interface for managing users,
    searching users and data, activity logs, credits, custom email and
    offline sign-ups, and "can we easily add more files and searchable
    database entries without having to go through a full deploy".
12. Other providers of Jev-like reasoning, and a public list of model
    endpoints and local models with a can-I-run page.
13. A simpler homepage: the hero shows the harness working directory for a
    task or subtask, built on demand with no manual search and no manual
    setup, and no worked example, followed by three links to start-to-finish
    demos. Demos of the owner's publications on their own subdomains,
    including gemma4_comp, llm-safety-framework and two Kaggle writeups, and
    the Gemma 4 Developer Agent paper track and competition. Research on how
    to present them, a search of the owner's repositories, and sample tasks
    that verify a user's installation and account.
14. Research on the Procedural Graphs paper (arXiv 2609.09153) and similar
    work, "to see what functionality, advanced graph, network, logic,
    hueriatistcs, and facapabilities would help us create a better product
    and manage a better product", and a question about affiliate and
    advertising income from the public lists.

## Decisions made and why

| Decision | Choice and reason |
|---|---|
| Registration | Opened at 13:00 UTC with the service guard. The owner approved opening on September 23 and told engineering to use its judgement on the remaining items. The provider-side closure waits for a working management authorization; the guard makes it unnecessary for safety. |
| Homepage hero | A directory tree for one step, assembled for that step on demand, with no worked example, and three demo cards: a simple task, a long task that runs overnight, and a Kaggle solution from start to finish. Three cards keep the first screen within the homepage scroll budget; long and overnight tasks share one card. |
| Affiliate and advertising income | Every row of a public list carries a typed `commercial_relationship` object kept apart from the editorial fields. Ranking, ordering, filtering and inclusion never read it, and a check with a known-wrong mutant enforces that. Each commercial link is labelled beside the link and uses `rel="sponsored noopener"`. Sponsored placements, if ever used, sit in their own labelled band. Every row ships with no commercial relationship until the owner joins programmes, because trust in the lists is what gives them value and joining a programme is a legal commitment with tax and payout details. |
| Research cadence | Daily source checks run in GitHub Actions with no model call. The model-backed research team runs every second day inside the session and may only write reports and roadmap proposals. |
| Live pulse location | GitHub-hosted runners, because this workstation's TLS handshakes to Fly's edge stall. |
| Jev | "jev is full, pause signed ups" was read as Jev pausing its own sign-ups. Baltor registration stays open. Alternatives to Jev go behind the typed decision edge as engines. |
| Sentry and PostHog | Not added. Both change what the privacy notice must say, which is the owner's decision. |

## Lines of work in flight

Every line works in a detached worktree with no branch, commits there and
does not push. The session merges finished lines into release 25. If this
session ends first, the next session opens each worktree, runs
`git -C <worktree> log origin/main..HEAD` and `git -C <worktree> status`,
saves any uncommitted work as a patch before anything else, reviews it, and
merges it.

| Line | Worktree |
|---|---|
| Superadmin invitations and the Confirm button fix | `/home/username/.le-accounts/invite-release` |
| Hostname surfaces, demo and case study pages, the new hero | `/home/username/.le-showcase-20260924` |
| Staff Model Context Protocol server and staff interface | `/home/username/.le-admin-mcp-20260924` |
| Public directory of third-party services and their protocol servers | `/home/username/.le-directory-20260924` |
| Models, endpoints and can-I-run directory | `/home/username/.le-models-20260924` |
| Licensed import at the scale of millions | `/home/username/.le-import-20260924` |
| Serving millions of items: tiers, search, anti-scraping | `/home/username/.le-serve-millions-20260924` |
| Review throughput: the three-family panel, batching, the Tactical server | `/home/username/.le-review-throughput-20260924` |
| Engine selector, custom harnesses and the custom loop-node engine | `/home/username/.le-engines-20260924` |
| Typed decision stations and alternatives to Jev | `/home/username/.le-decisions-20260924` |
| Stack starter packages | `/home/username/.le-starters-20260924` |
| Search engine optimization and the blog | `/home/username/.le-seo-blog-20260924` |
| The deck page | `/home/username/.le-deck-20260924` |
| Laya and Toolsmith research | `/home/username/.le-toolsmith-research-20260924` |
| Procedural Graphs research | `/home/username/.le-procedural-graphs-20260924` |
| Affiliate and advertising research | `/home/username/.le-affiliate-research-20260924` |
| Research on showcasing the owner's publications and repositories | `/home/username/.le-showcase-research-20260924` |
| Sample tasks that verify a user's setup | `/home/username/.le-sample-tasks-20260924` |
| Library inventory and review | `/home/username/.le-inventory-20260924` |

Two more runs have no worktree of their own: the functional component
standard, which writes its reports to the session's working folder, and the
persona journeys, which use the live site. Each persona that registers takes
a founding place; release those places after the run.

## Ordered work that remains

1. Merge the finished lines into release 25, run the full suites on an export
   of the exact tree, release through the guarded workflow, run the live
   checks one hostname at a time, and record release 25.
2. Rerun the persona journeys on release 25 and release the founding places
   they take.
3. Grow the library towards 100,000 approved packages through import and
   review throughput. Write the community tier decision into the AGENTS.md
   decision table before any community item is served.
4. Turn the research records into roadmap steps: Procedural Graphs, Laya and
   Toolsmith, the showcases of the owner's work, and affiliate income.

## What needs the owner

- Affiliate programmes: accepting each programme's terms, giving tax and
  payout details, and approving the disclosure wording.
- Any change to the privacy notice, for example for Sentry, PostHog or click
  logging beyond aggregate counts.
- Optional: signing in again to the identity provider's management
  connection, so that engineering can also close the provider's own public
  sign-up at the source.
- Any Kaggle submission or public notebook.

## Model and usage allowances

- Ollama Cloud: the weekly allowance was spent in the week that ended on
  September 24. The review throughput line re-probes it with one recorded
  call before any batch and stops on a spent allowance.
- The owner's Tactical server: available, with a verified output capacity of
  65,536 tokens and block format version two.
- Claude Code: the weekly usage limit stopped every agent and workflow until
  13:00 Eastern on September 24. All of them were resumed after the reset.

## Known traps

- TLS handshakes from this workstation to Fly's edge stall. Run live checks
  one hostname at a time, or from GitHub-hosted runners.
- Four browsers at once trip the per-address rate limiter. Run hosted browser
  checks one after another.
- Run hosted checks from the released worktree, and take item digests from
  its manifest.
- New hardcoding allowlist entries go inside `entries:`, before
  `excluded_paths:`.
- `/tmp` is a 31 GB memory-backed disk and was 77 percent full. Use a
  temporary folder under the home folder.
- The shared checkout `/home/username/loop-engine` holds other sessions'
  uncommitted work. Never reset it.

## Research team prompt

To re-arm the research team in a new session, create a recurring schedule
(for example every second day at 06:43) with this prompt:

```text
Research team run for Baltor (recurring, set up on September 24, 2026 at the
owner's request: "we should have research teams run regularly to see new
developments"). Do this with a small workflow of at most 4 research agents
plus 1 writer:
1. Read the newest open GitHub issue titled "Research watch: sources changed"
   and the latest research-watch artifact (gh run list --workflow
   research-watch.yml), then read every changed source.
2. Sweep new developments since the last digest in docs/research/ about:
   coding harnesses (Claude Code, Codex, OpenCode, Pi, Gemini CLI and
   others); agent tool-calling, tool routing and tool-making (toolsmith,
   router and coach patterns); skills, plugin and MCP registries, and the MCP
   specification; typed decision engines and model routers; licensed sources
   of harness files; relevant papers. Use primary sources with dates, and
   keep unknowns unknown.
3. Write docs/research/RESEARCH-DIGEST-<today's date>.md in plain English
   (humanizer-context.md, no em or en dashes). Say what changed, why it
   matters to Baltor, and the proposed roadmap changes with their owning
   steps. Add proposals to docs/roadmap/roadmap.yaml only as new or extended
   steps with verify, adversarial, acceptance and evidence fields, and keep it
   valid with tools/build_continuation_status.py.
4. Run markdownlint and the records index builder, commit in a detached
   worktree of origin/main, rebase and push to main. The effect policy is
   reports and roadmap proposals only: never deploy, publish a catalogue
   release or approve a candidate.
Report the digest path and the three most important developments.
```
