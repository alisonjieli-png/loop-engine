# Owner requests ledger, October 2026

Kind: dated ledger of the owner's requests of October 1 to 16, 2026, one row
for each request, kept as a context record. It continues the
[September 2026 ledger](OWNER-REQUESTS-LEDGER-2026-09.md) with the same
columns, the same six state words and the same rules about quoting. The
[roadmap](../roadmap/roadmap.yaml) remains the only task authority; this
ledger checks whether the roadmap and the live service answer what the owner
asked, and it grants nothing. The owner's standing rules are in the
[commit, push and release authority](../../AGENTS.md#commit-push-and-release-authority)
section of AGENTS.md, which this ledger does not restate.

The owner asked on October 15, 2026, and again on October 16, for a
measurement of every historical prompt: chunk the prompts, separate pasted
material, find the historical directions, vectorize them, and measure desire
and to-do completion. This ledger is the durable part of that measurement, so
that every session sees which asks are done and which are open.

## Measurement

A private, read-only measurement ran on October 15, 2026 over the owner's
prompt histories. Only aggregates appear here. The raw prompts, chunks,
labels and reviewer judgments stay in private files on the owner's
workstation, and nothing was sent anywhere.

What was measured:

- 3,623 prompts from four harness histories, dated in Eastern time: Codex
  1,501 (September 4 to October 15), OpenCode 1,635 (June 21 to October 13),
  Antigravity 130 (October 13 to 15) and Claude Code 357 (September 1 to
  October 15). From October 1 to 16 the four lanes carried 558, 50, 130 and
  56 prompts, 794 in all.
- 18,290 chunks. 5,316 are actionable by the measurement's rules and 12,933
  belong to Baltor by their project folder or their words. After status
  checks, bare continue prompts, references and resends within the hour are
  set aside, 3,024 Baltor asks remain, with 2,105 distinct texts.
- 16 directions and 1,429 to-dos. The measurement also counted 113 status
  checks, 22 bare continue prompts and 1,132 resends within an hour.

How it was measured:

- Collection redacted 5,922 credential-shaped values before anything was
  written.
- Paste separation kept the owner's leading and trailing sentences apart
  from pasted logs, agent replies, documents and templates. 434 prompts
  carried pasted material; for 83 prompts no owner words could be separated,
  and a marked 400-character lead stands in for them.
- Chunking split the owner's words into sentences and "also" clauses and
  typed each chunk by rules: direction, question, constraint, approval,
  complaint, status check and others.
- Labelling put 2,680 distinct chunk texts into a written taxonomy of 16
  directions, with a kind, an actionable flag and a short to-do. 875 texts
  were labelled as not the owner's words and left out, so 2,964 measured
  asks carry a direction. A to-do groups the labelled asks that share a
  to-do text.
- Vectoring combined TF-IDF word and word-pair vectors, reduced to 160
  dimensions, with offline static embeddings at a weight of 0.75, and
  grouped the asks into 79 topics for repeat detection.
- Desire: a chunk's emphasis is 1.0, plus 0.5 for each intensifier word (at
  most six), 0.5 for each word in capitals (at most four), 0.3 for each
  exclamation mark (at most five) and 1.0 when it matches the status-question
  pattern. Recency halves every 14 days before October 16, 00:00 UTC. Desire
  now sums emphasis times recency; lifetime desire sums emphasis.
- Completion: reviewers read the agents' replies in 19 slices of the Codex,
  OpenCode and Antigravity sessions and judged 1,698 asks: 212 done and
  verified, 571 done as claimed, 523 partial, 148 not done, 26 contradicted,
  21 deferred and 197 unknown. 984 judgments joined a measured ask in the
  same lane within three days at a text similarity of at least 0.25, and 970
  of those joined a labelled direction. A direction's completion is the mean
  of 1.0 for verified, 0.6 for claimed, 0.35 for partial, 0.1 for deferred
  and 0 otherwise. Unmet desire is desire now times one minus completion.

The 16 directions, by desire now:

| Direction | Asks | Distinct | Desire now | Lifetime desire | Completion | Unmet desire now | Judged asks |
|---|---|---|---|---|---|---|---|
| Library scale and supply (LIB) | 340 | 173 | 441.3 | 772.6 | 0.33 | 295.2 | 94 |
| Planning and tracking (PLAN) | 225 | 97 | 271.8 | 483.0 | 0.60 | 108.4 | 68 |
| Infrastructure and releases (OPS) | 240 | 103 | 261.6 | 448.5 | 0.40 | 157.2 | 68 |
| Core architecture (ARCH) | 585 | 386 | 225.4 | 992.3 | 0.43 | 128.5 | 177 |
| Creative and media (MEDIA) | 110 | 63 | 185.2 | 285.5 | 0.27 | 136.1 | 27 |
| Autonomy and working style (AUTONOMY) | 237 | 121 | 162.4 | 478.6 | 0.46 | 87.1 | 66 |
| Website and product experience (SITE) | 167 | 117 | 139.9 | 304.2 | 0.39 | 85.3 | 59 |
| Testing and evidence (QA) | 170 | 90 | 135.2 | 303.5 | 0.34 | 88.8 | 51 |
| Harnesses and agent execution (AGENTS) | 324 | 232 | 134.8 | 501.1 | 0.44 | 75.0 | 129 |
| Research and prior art (RESEARCH) | 143 | 110 | 120.7 | 277.3 | 0.51 | 59.1 | 47 |
| Feeds and discovery (FEEDS) | 106 | 45 | 116.5 | 191.5 | 0.29 | 83.2 | 18 |
| Cross-agent review and coordination (REVIEW) | 153 | 118 | 89.8 | 263.4 | 0.47 | 47.9 | 82 |
| Brands and domains (BRANDS) | 51 | 43 | 62.3 | 79.4 | 0.69 | 19.3 | 29 |
| Business and growth (BIZ) | 49 | 32 | 38.9 | 75.5 | 0.33 | 26.1 | 18 |
| Machine and file housekeeping (MACHINE) | 40 | 39 | 19.9 | 63.1 | 0.52 | 9.5 | 26 |
| Security, privacy and legal (TRUST) | 24 | 21 | 18.3 | 42.5 | 0.69 | 5.7 | 11 |

To-do completion: of the 1,429 to-dos, 792 carry at least one judgment. By
their most frequent judged outcome, 106 are done and verified, 260 done as
claimed, 267 partial, 65 not done, 13 contradicted, 4 deferred and 77
unknown; 637 have no judgment. 141 to-dos were asked three times or more and
1,113 once.

Selection for this ledger: 386 to-dos have an ask between October 1 and 16 in
Eastern time. The rows cover the 52 of them asked three times or more, 36
more that hold an ask with an emphasis of 3.0 or higher, and the asks that a
reviewer judged at the highest emphasis (48 judgments, two of which fall on
September 30 in Eastern time and stay out). Asks that want the same thing
share a row, which leaves 66 rows, R-111 to R-176. Six to-dos about media
production in the separate social video and media project folders are left
to that project's owner. Rows R-177 to R-182 hold the owner's prompts of
October 15 and 16 to Claude Code, which the collected corpus predates. They
were added by hand from the conversation that the coordinating session
relayed, not from the corpus, so they carry no measured count.

Limits:

- Paste separation and chunking follow rules, so they can keep pasted text
  or drop owner text. Every quote in rows R-111 to R-176, and the October 8
  quote in R-178, is an exact excerpt of a chunk the measurement kept as the
  owner's words, and each was read by hand. The other quotes of rows R-177
  to R-182 are the words the coordinating session relayed, with no corpus
  chunk to check them against.
- Emphasis counts words, so long sentences score higher. The extra point
  goes to the status-question pattern, not to complaint wording.
- Repeat counts include the same prompt sent to several sessions or project
  folders, and resends. They measure insistence, not distinct requests.
- Reviewers judged the agents' replies, not the live service. Their
  outcomes were hints only; each row's state was judged again from the
  roadmap, the release records and the live sites.
- The Claude Code lane has no completion review, and the measurement ends
  on October 15. Asks below the selection thresholds have no row; the owner
  decision table keeps decisions such as the October 11 price change.
- Dates convert UTC to Eastern time by subtracting four hours, which holds
  for the whole window.

## How to read the table

- One row is one request, or several asks that want the same thing, in the
  date order of the first ask.
- "The owner's words" quotes at most 40 words exactly as recorded, typing
  errors included, and names the date of each quote that falls after the
  row's date. An ellipsis marks words trimmed from a longer sentence.
  Pasted material, addresses, names other than the owner's brands and
  credentials are never quoted. A summary says so.
- "Source" names the harness lane and the Eastern date of the first ask
  with its measured count, then each later ask the row covers. "Measured N
  times" is the measurement's count for the to-do the words belong to,
  resends included; where the words carry no labelled to-do, it counts the
  separate prompts that carried them, a resend within the hour counted once.
  A row added by hand names an owner prompt to Claude Code and its date.
- "Roadmap steps" names the steps (S-6.214) or subtasks (S-6.214.12) that
  answer the request, or `none`.
- "State today" is one of the six words of the September ledger: `live` (a
  customer or a person can use it on the live service), `on main` (merged
  and pushed, not released, or a rule or record that needs no release),
  `building` (a line is committed or running), `proposed` (a roadmap step
  exists and no build has started), `blocked` (waits on a named condition)
  or `not started` (no step and no build).
- "Gap" says in one sentence what is missing when the state is not live.
- Rows R-111 to R-182 were written on October 16, 2026 from `main` at
  `df963c20`, the release records, the
  [current deployment](../architecture/MVP-CLIENT-SERVER.md#current-deployment)
  section and GET reads of the public sites that day: `baltor.ai` with its
  pricing, todo and changelog pages, `demo.baltor.ai`, `examples.baltor.ai`,
  `agentfeeds.si`, `getagentfoundry.si`, `agentafk.si`, `agentstudios.si`,
  `dontbeameatproxy.si`, `agentbriefs.si` and `systems.baltor.ai`.

## Requests

| Id | Date | The owner's words | Source | Roadmap steps | State today | Evidence | Gap |
|---|---|---|---|---|---|---|---|
| R-111 | 2026-10-01 | "all 17 SDG's need to be populated, all connections and functionality need to be wired up" and "We need to have files for all 17 goals and more, and be more creative" (October 5) | owner prompt history, Codex, 2026-10-01; measured 1 time; again Claude Code, 2026-10-05 (1 time); Codex, 2026-10-06 (1 time) | S-6.216, S-6.216.01 | live | Public Good serves 448 groups and 1,128 distinct useful files across all 17 goals since the October 8 SDG addition (current deployment); policy a4b61a97 renewed all 448 grants on October 16 until February 1, 2027 (public-good-renewal-2026-10-16.json); the header links /public-good | Deeper and more creative material for each goal (S-6.216.01) is ready and not started. |
| R-112 | 2026-10-01 | "We need to test all aspects of it harness downlaod, setup, various harness types, automatic harness, olalma, etc" and "tests on this PC using baltor connected to baltor as a customer using a custom harness or opencode harness" (October 8) | owner prompt history, Codex, 2026-10-01; measured 2 times; again Codex, 2026-10-08 (16 times); Codex, 2026-10-13 (1 time) | S-6.24, S-6.24.02, S-6.202 | proposed | On release 60 (October 1) an engineering account passed live OAuth through /mcp and downloaded one exact instruction file; an ordinary account without a plan later ran a downloaded Public Good tool in an isolated custom harness (current deployment); neither is a native OpenCode journey | S-6.24.02 (verify OpenCode and another harness against live Baltor) is ready with no recorded run, and quickstarts checked every night (S-6.202) are proposed. |
| R-113 | 2026-10-01 | "Do not ask me to make decisions, I want you to do all" (October 8) and "avoid stopping just to ask me questions that can be defferred until later, you have my explicit permission to keep building out more files" (October 13) | owner prompt history, Codex, 2026-10-01 (words not quoted); measured 1 time; again Codex, 2026-10-08 (24 times); Claude Code, 2026-10-09 (22 times); Antigravity, 2026-10-13 (2 times); Codex, 2026-10-13 (3 times) | none | on main | AGENTS.md rule 4 (decide instead of asking) holds the owner's September words, and the October 15 engineering continuation in OWNER-DECISIONS says work does not wait for the original harness; the measurement counted 22 bare continue prompts and 113 status checks | Rule 4 cites only September words, and the October 15 history review found that silence between reports drove repeated prompts in every lane. |
| R-114 | 2026-10-01 | "stop with the weird negative language about what baltor isn't what features don't do, and other things on the website" | owner prompt history, Codex, 2026-10-01; measured 2 times | S-6.33 | proposed | The homepage read on October 16 still has a 'What Baltor is not' section that begins 'Not a model provider', beside several other 'is not' notes | The negative section and wording are live, and the website fix step S-6.33 holds no task for them. |
| R-115 | 2026-10-01 | "we need to develop thoutsands of component files, harness files, skills, tools, executables, etc that will help these tools" and "better blender creation, better freecad, better openscad, better godot, better inkscape" | owner prompt history, Codex, 2026-10-01; measured 3 times; again Claude Code, 2026-10-08 (1 time) | S-6.215, S-6.214.15, S-6.201 | building | The October 9 evening publication added 413 original creative components (Godot shaders and components, Blender tools, procedural textures, geometry and mesh algorithms) and 3,187 distinct files (catalogue-creative-originals-2026-10-09.json); AgentStudios presents creative filters since release 92 | Coverage for each tool is unmeasured: FreeCAD, OpenSCAD, Inkscape, Kdenlive, KiCad, GIMP and QGIS have no recorded cohort, and S-6.214.15 lists leads, not integrations. |
| R-116 | 2026-10-01 | "have keyword multiplication searches accrossas a wide number of dimensions" and "we need a massiev factory of dimensions, grid, combinations, processes, steps, to be able to generate more harness component files" (October 8) | owner prompt history, Codex, 2026-10-01; measured 1 time; again Codex, 2026-10-05 (2 times); Codex, 2026-10-08 (22 times); Codex, 2026-10-08 (2 times) | S-6.215.13, S-6.179, S-6.53 | building | The October 8 twelve-hour campaign plan in DELIVERY-SEQUENCE.md sets an atom and composition grid; the atomic factory's API-contract cohort (31,459 packages) and a constraint-case cohort (6,357) went live on October 9; S-6.215.13 holds 5,389 unprocessed API atoms as a research frontier | No keyword-multiplication discovery engine exists, and the factory's sustained production rate is unmeasured (S-6.215.13). |
| R-117 | 2026-10-01 | "even basic function with regex to standardize an email, or detect slang, or do some basic text operations that are useful can be helpful" and "get more atomic about skills, files, very specific use cases" (October 8) | owner prompt history, Codex, 2026-10-01; measured 2 times; again Codex, 2026-10-08 (24 times); Codex, 2026-10-15 (2 times) | S-6.215.13, S-6.217 | building | Release 62 holds twelve micro-component reports with 108 exact attachments as candidates, not admitted; the October 9 API-contract and constraint-case publications are small single-purpose files; the October 15 work order in OWNER-DECISIONS names string utilities and logic packs as fallback supply | The micro-component batch for email handling, text cleanup and lookup is not admitted or served. |
| R-118 | 2026-10-01 | "Can you open the baltor north star in text editor, that will give me EVERYTHING I need to inform my dot abaout and more" | owner prompt history, Codex, 2026-10-01; measured 2 times | none | live | The North Star is the one current direction document, and /dot-context and /dot-feedback serve Dot its briefs since release 61 (October 1) | None recorded; the owner's own Dot session and its access renewal remain untested (release 62 handoff), and no roadmap step owns the Dot pages. |
| R-119 | 2026-10-01 | "just a general policy that we may receive things to improve our services, make it even more flexible to allow uploads and reading and other functionality" | owner prompt history, Codex, 2026-10-01; measured 3 times | S-6.12.01, S-6.192 | live | The general submission privacy notice went live in release 62 (October 4), and Dot sends findings and passive text and code files through /admin (release 62 handoff) | Private-by-default customer submissions (S-6.12.01) are ready and not built. |
| R-120 | 2026-10-05 | "review this entire project, all codex sessions, additional useful/tangential files on disk" and "aggressively scan other files, other project, ingest, interoogate, and improve them and generate file components" | owner prompt history, Claude Code, 2026-10-05; measured 1 time; again Codex, 2026-10-05 (1 time) | S-6.207, S-6.207.04, S-6.207.05 | building | S-6.207.04 defines 1,000 questions with 75 source-backed answers across creative-project chunks, and three original camera and timing helpers pass the isolated-package checks; turning approved findings into candidates (S-6.207.05) is proposed | No component drawn from the owner's other projects is admitted or served. |
| R-121 | 2026-10-05 | "we need to capture all of the AI news, releases, etc, daily things" | owner prompt history, Claude Code, 2026-10-05; measured 1 time | S-6.214, S-6.214.09, S-6.82 | building | The research watch read all 50 of its daily sources after the October 15 repair; /models, /endpoints and /directory refresh daily; AgentFeeds serves curated collections, not continuously collected articles (release 90) | No maintained daily news feed is served, and useful source-backed feeds (S-6.214.09) are ready and not built. |
| R-122 | 2026-10-05 | "We need to aggressively get to 1 million files and more quicker deployments, better architecture" | owner prompt history, Codex, 2026-10-05; measured 1 time; again Codex, 2026-10-06 (1 time); Codex, 2026-10-06 (1 time) | S-6.215, S-6.215.07, S-6.215.08, S-6.215.09 | live | The library serves 1,560,856 distinct files in 256,380 packages since the October 9 publications (current deployment), up from 1,353,029 on October 8; an ordinary account downloaded a new package after each publication | None for the one million mark; deployment speed is row R-123. |
| R-123 | 2026-10-06 | "I need more deployments, updates, pushes, faster, better, etc." and "quicker deployments and updates and simultaneous, multi-agent processes to divide and conquer intelligently" (October 8) | owner prompt history, Codex, 2026-10-06; measured 1 time; again Codex, 2026-10-08 (5 times) | S-6.35, S-6.35.01, S-6.200 | live | Fly release 78 was live on October 8 and release 93 on October 15, each through the guarded workflow; parallel agents work in detached worktrees (October 15 handoffs) | Continuous integration in 12 minutes (S-6.200) is building; the full local pre-push run took 684 to 692 seconds on October 15. |
| R-124 | 2026-10-06 | "Put together a clear todo list, improvements, checklist, and active working plan with all procedures, next steps, comments, gantt chart style, etc" | owner prompt history, Codex, 2026-10-06; measured 46 times | S-6.17, S-6.212 | live | DELIVERY-SEQUENCE.md holds the October 7 active execution plan with a priority and phase-based Gantt view, DEVELOPMENT-TRACKER.md is the ordered task checklist generated from the roadmap, and the unlinked /todo page served on October 16 lists the open steps by delivery package | The plan is live, and 231 of its 270 steps are open (the /todo page, October 16). |
| R-125 | 2026-10-06 | "I think Cloudflare provides an amazing set of services that can either supplement or completely replace fly.io for some things, however, we still may need significant control over our custom search and retreival" | owner prompt history, Codex, 2026-10-06 (the benefits question); measured 46 times; again Codex, 2026-10-06 (1 time); Codex, 2026-10-06 (41 times); Codex, 2026-10-06 (1 time); Codex, 2026-10-07 (35 times) | S-6.13, S-6.13.01, S-6.13.02, S-6.13.03 | building | The nine Baltor hostnames serve public files from the Cloudflare Worker and forward dynamic requests to Fly, and R2 holds verified copies of every served body; body delivery, custom search and Supabase identity stay selected (current deployment); CLOUDFLARE-HOSTING-2026-10-05.md and the October 8 handoff explain the choices | Authenticated R2 delivery (S-6.13.01) and the sign-in boundary review (S-6.13.03) are ready and not started; collectors and durable jobs on Cloudflare (S-6.13.02) are proposed. |
| R-126 | 2026-10-06 | "you can be aggressive and you are allowed to make the site go down" | owner prompt history, Codex, 2026-10-06; measured 41 times | none | on main | OWNER-DECISIONS (Feeds and Components offerings, October 6) and the North Star record that the owner permits website downtime during optimization; integrity, authorization and rollback still apply | None; a permission needs no step, and no planned downtime is recorded. |
| R-127 | 2026-10-06 | "document each to do, subtask, step, what is next, and ireatively complete tasks one by one making visible progress on each one" (October 8) | owner prompt history, OpenCode, 2026-10-06 (a status question); measured 3 times; again Codex, 2026-10-07 (2 times); Codex, 2026-10-08 (1 time); Codex, 2026-10-08 (1 time); Antigravity, 2026-10-13 (16 times) | S-6.35.02, S-6.212 | building | S-6.35.02 (a progress checkpoint after every completed subtask) is building with a tracker view that passes local tests; the measurement counted 113 status checks; the October 15 Claude handoff asks for a short report after each prompt and release | No checkpoint is published for each completed subtask, and the unlinked /changelog still ended at release 92 when read on October 16. |
| R-128 | 2026-10-06 | "have thousands of dimensions of different search tools, processing tools, digestion tools, and layers, and have thousands of configurations for each one of those layers" | owner prompt history, OpenCode, 2026-10-06; measured 3 times; again OpenCode, 2026-10-06 (1 time) | S-6.52, S-6.32, S-6.32.01, S-6.74 | proposed | The served search is one custom SQLite engine (current deployment); comparing equivalent search engines across process boundaries (S-6.32.01) is ready, and more retrieval engines (S-6.52) are proposed | No configuration grid over search, processing and digestion layers exists. |
| R-129 | 2026-10-06 | "a newsletter-style product for AI agents that will curate information and news and feeds that are directly relevant to subscribers' AI agents" and "get a website up to agentfeeds.si" (October 13) | owner prompt history, OpenCode, 2026-10-06; measured 3 times; again Codex, 2026-10-13 (4 times) | S-6.214, S-6.35.06, S-6.214.11 | live | AgentFeeds is live at agentfeeds.si since release 90 (October 13): 19 curated collections from 60 distinct sources in JSON, RSS and Markdown, with reading profiles for each agent; 414 live checks passed | Collections are curated, not continuously collected, and saved hosted feeds and their delivery (S-6.214.10, S-6.214.11) are proposed. |
| R-130 | 2026-10-07 | "get up to 10 million, and add new areas, more ingestion, more related to design, media, animation, templates, layering templates, media layering, masks" | owner prompt history, OpenCode, 2026-10-07; measured 1 time; again Codex, 2026-10-07 (25 times); Codex, 2026-10-08 (1 time); Codex, 2026-10-08 (1 time) | S-6.215, S-6.215.13 | building | 1,560,856 distinct files are served (current deployment) and 341,902 reconciled files wait unpublished (October 15 Claude handoff); the October 9 creative publication added 413 Godot, Blender, texture and geometry components | About 8.4 million files short of ten million, and no sustained production-to-serving rate is measured. |
| R-131 | 2026-10-07 | "how can people customize their own feeds if they want specific agents to consume specific feeds or info" | owner prompt history, Codex, 2026-10-07; measured 35 times | S-6.214.12, S-6.214.10, S-6.214.11 | live | S-6.214.12 is live-qualified: AgentFeeds lets a person build a distinct reading profile for each agent and download it (release 90) | Profiles are local downloads; saved preferences for each agent (S-6.214.10) and their delivery (S-6.214.11) are proposed. |
| R-132 | 2026-10-07 | "ALL of our tensorart image generations along with meta data, model details, etc and improve baltor's ability to visualize things" | owner prompt history, Codex, 2026-10-07; measured 31 times; again Codex, 2026-10-08 (9 times, a new access key, not quoted) | S-6.201.01 | blocked | S-6.201.01 is blocked: the supplied key is stored, browser connector access is unavailable, and local site sessions did not identify the account | Waits on access to the target account without forwarding cookies to a third party. |
| R-133 | 2026-10-07 | "review if Replit would be helpful at all" and "realistically plan out a gantt chart and task list of things that I'd need to do to start onboarding customers, marketing, applying for funding, scaling" | owner prompt history, Codex, 2026-10-07; measured 29 times | S-6.204.02, S-6.204.01, S-6.186 | on main | DELIVERY-SEQUENCE.md records the Replit decision (optional, with no measured advantage for the production migration), the customer launch schedule and the funding shortlist with its application checks | Launch, funding and startup-credit material (S-6.204.02) and onboarding measurement (S-6.204.01) are ready and not started. |
| R-134 | 2026-10-07 | "look at kaggle hackathons, papers, etc to develope code, unique strings, intelligence, data cleaning, data transformation, calculation, processing, architecturting" | owner prompt history, Codex, 2026-10-07; measured 1 time; again Codex, 2026-10-07 (25 times) | S-6.216.01, S-6.215.13 | proposed | Public Good starts with DueCare worker-protection material and holds 1,128 useful files; useful SDG and competition-derived materials (S-6.216.01) are ready | No cohort drawn from competitions or papers is recorded as admitted. |
| R-135 | 2026-10-07 | "I believe we need more engines, more portability, more modularity, 4 engines sounds very small and it seems like we aren't breaking things up into microservices enough" (October 13) | owner prompt history, Codex, 2026-10-07 (separation, microservices and engine units); measured 25 times; again Codex, 2026-10-08 (12 times); Antigravity, 2026-10-13 (2 times) | S-6.30, S-6.74, S-6.72, S-6.32.01 | building | engine_slots.yaml declares 55 engine slots (S-6.30 building), and the October 13 portability decision adds language and placement as implementation dimensions (LANGUAGES-AND-COMPONENTS.md) | Run-time engine selection (S-6.74) and contract test kits (S-6.72) are proposed, and the matched Python, process and Rust comparison (S-6.32.01) is ready and not run. |
| R-136 | 2026-10-08 | "adversarially validate every single page, all marketing language, nomeclature, ideas, standards, index, documents, how to, test it out, variations, side by side comparisons" | owner prompt history, Codex, 2026-10-08; measured 21 times; again Antigravity, 2026-10-14 (2 times) | S-6.67.01, S-6.181, S-6.35.06 | building | Route audits covered 71 pages and 293 views at releases 87 and 88 and 75 pages and 309 views at release 89; the release 93 matrix passed 4,715 assertions on twenty hosts and retained 21 canceled metadata fetches | No adversarial review of every claim exists: the claims register (S-6.181) is proposed, the page review (S-6.67.01) is ready, and the release 93 strict result stays false. |
| R-137 | 2026-10-08 | "prove out the ability for the system to scan, find, document, ingest, consider, and build out file components and details based on scans of public and popular and useful web surfaces" | owner prompt history, Codex, 2026-10-08; measured 19 times; again Codex, 2026-10-08 (12 times) | S-6.81, S-6.214.06 | building | tools/read_trendshift.py made one authorized public read on October 8 and parsed five of 25 rows without publishing (October 8 handoff); source scouts (S-6.81) are building | No component built from a scanned web surface is admitted or served. |
| R-138 | 2026-10-08 | "there is so much useful information on reddit in reddit forums, subreddits, etc about useful tools, especially for AI design and AI game design, we can utilize rapidapi to scrape those on a daily basis" | owner prompt history, Codex, 2026-10-08; measured 19 times | S-6.214.03, S-6.214.04, S-6.214.05 | building | tools/read_reddit_research.py reads the owner's selected Reddit endpoint with observed requests (October 8 handoff), and S-6.214.03 classified 29 provider operation examples and got six usable responses from twelve probes | No daily Reddit collection runs; shared quotas and the rights and privacy checks (S-6.214.04, S-6.214.05) are ready and not started. |
| R-139 | 2026-10-08 | "a package is a group of files, from a marketing perspective can't we just say files?" | owner prompt history, Codex, 2026-10-08; measured 17 times | S-6.33 | live | The homepage read on October 16 counts '1,560,856 files in the library today', and packages appear only in a documentation link title; OWNER-DECISIONS (October 8) keeps packages as the technical grouping | None recorded. |
| R-140 | 2026-10-08 | "review the past 24 hours of prompts, actions, harness actions, directions, details, suggestions, turns, etc that I have done and fully understand the direction" | owner prompt history, Codex, 2026-10-08; measured 12 times; again Codex, 2026-10-11 (1 time); Codex, 2026-10-13 (4 times); Antigravity, 2026-10-13 (1 time) | S-6.217.01, S-6.210 | on main | S-6.217.01 is offline-verified: the October 9 to 11 window of 241 records mapped sixteen owner requests to 25 obligation groups; the release 90 handoff records a 72-hour audit of October 10 to 13; this ledger covers October 1 to 16 | Each review covers a fixed window, and nothing reruns it when new prompts arrive. |
| R-141 | 2026-10-08 | "WE NEED TO ALWAYS ASK OURSELF IF THERE ARE OPEN SOURCE PROJECTS THAT CAN HELP US OUT RATHER THAN RECREATE THINGS" | owner prompt history, Codex, 2026-10-08; measured 12 times | S-6.75, S-6.163 | on main | AGENTS.md rule 6 requires a search of existing projects, repositories, designs and papers before any build, with the reason for adopting, adapting or rejecting what was found | An upstream engine beside a Baltor-native engine for every adopted project (S-6.75) is proposed. |
| R-142 | 2026-10-08 | "YOU NEED TO DIRECTLY SHOW ME WHAT ADDITIONAL api KEYS TO PROVIDE AND SERVICES TO SETUP" | owner prompt history, Codex, 2026-10-08; measured 12 times; again Codex, 2026-10-08 (9 times); Codex, 2026-10-08 (7 times) | none | on main | tools/operator_credentials.py inventory reports each credential reference with its presence and format, never its value, and the October 8 handoff names the references prepared but still empty | The inventory does not check live entitlement, so a present key can still be refused by its provider. |
| R-143 | 2026-10-08 | "LETS TAKE ON THE PERSONA OF cto, CFO, ADVISOR, COMPETITOR, INVESTOR, ETC" | owner prompt history, Codex, 2026-10-08; measured 1 time; again Codex, 2026-10-08 (1 time); Codex, 2026-10-08 (9 times) | S-6.55 | proposed | Persona reviews after every release (S-6.55) are proposed, and the October 15 owner decision says simulated personas do not establish deployed behavior | No review of Baltor from these personas is recorded on main. |
| R-144 | 2026-10-08 | "create a nice handoff document because I will be switching to a new OpenAI account" | owner prompt history, Codex, 2026-10-08; measured 3 times; again Codex, 2026-10-09 (1 time) | none | on main | SESSION-HANDOFF-2026-10-08.md records account and provider continuity for the account change, and the handoffs of October 11 to 15 continue it | None; a handoff needs no step, and the private closing checkpoint stays outside the repository. |
| R-145 | 2026-10-08 | 'we should not have a "planned" or "coming soon" or anything on the front end' and "We should get everything setup, rather than having empty future promises" | owner prompt history, Codex, 2026-10-08; measured 1 time; again Codex, 2026-10-08 (1 time) | S-6.33 | live | Neither phrase appears on the homepage or the pricing page read on October 16, and working early tools carry the Public preview label (OWNER-DECISIONS, October 8 continuation) | None recorded. |
| R-146 | 2026-10-08 | "how far away are we from turning this into a plugin, a service, an openAI app, or something else that can capture the aduience in chatgpt" | owner prompt history, Codex, 2026-10-08; measured 7 times | S-6.102.01, S-6.102.02, S-6.183 | building | S-6.102.01 is building: OAuth client registration admits the documented Claude, Cursor, VS Code and Codex callbacks, docs/guides/chatgpt-app.md holds the tests, and the October 5 live proof passed 23 of 23 checks | The fresh-account live presentation check has not run after a release, and plugin review (S-6.102.02) waits on the owner's identity verification. |
| R-147 | 2026-10-08 | "read the files in chunks, prioritize them" and "ask hundreds to thousands of questions for each chunk" (the share's network address is left out) | owner prompt history, Codex, 2026-10-08; measured 4 times | S-6.207.01, S-6.207.04, S-6.207.05 | building | S-6.207.01 inventoried 65,382 files, including 1,550 conversation files, before its scan stopped at the 40 GiB floor with 453 directories queued; the October 15 selected-scope inventory read 2,700 files with zero scanner errors | No thousand-question chunk review is complete, and coverage of the whole share is unproven. |
| R-148 | 2026-10-08 | "on the SMB share there is an entire coding session that developed a rapidapi registery of thousands of API endpoints" | owner prompt history, Codex, 2026-10-08; measured 3 times | S-6.207.02, S-6.207.03 | building | S-6.207.02 is offline-verified: the session was hashed and split into 46,836 private chunks, its 13 oversized records into 777 redacted fragments | The two missing native databases and the discovery module (S-6.207.03) are not recovered. |
| R-149 | 2026-10-08 | "adding more harness component files with a goal of getting us to 2 million harness component files very quickly" | owner prompt history, Codex, 2026-10-08; measured 2 times; again Codex, 2026-10-11 (1 time) | S-6.215.14, S-6.215.06 | building | The October 11 reconciliation verified 341,902 new bodies (S-6.215.06), still unpublished on October 15; published, they would raise the count from 1,560,856 to 1,902,758 | 439,144 files short of two million (S-6.215.14 proposed); the reconciled delta waits for its guarded publication and would still leave 97,243. |
| R-150 | 2026-10-08 | "How can we get around and resolve the 4MiB per-record resolution, do we need to split these json files" | owner prompt history, Codex, 2026-10-08; measured 3 times | none | not started | No record on main names this limit or how it was resolved; tools/overnight_queue_state.py and tools/export_organization_opportunities.py each cap a record or an input at 4 MiB | The limit's owner and the chosen fix are unrecorded. |
| R-151 | 2026-10-08 | "a large number of feeds from 10,000+ sources" and "very creative, making unique, extremely detailed, even esoteric feeds, data based feeds" (October 12) | owner prompt history, Codex, 2026-10-08; measured 1 time; again OpenCode, 2026-10-12 (1 time); Antigravity, 2026-10-13 (1 time) | S-6.214.01, S-6.214.02, S-6.214.06, S-6.214.07, S-6.214.08, S-6.214.09 | building | The North Star records the target of feeds from more than 10,000 qualified upstream sources; AgentFeeds serves 60 distinct source references (release 90), and S-6.214.03 is normalizing supplied provider operations | Canonical source counting and the census (S-6.214.01, S-6.214.02) are ready and not started, so progress toward 10,000 is unmeasured. |
| R-152 | 2026-10-08 | "1 crazy problem that still exists, is that we don't have the 3 clearly seperated plans!" and "if it makes sense to have the pricing in a pricing section not in the hero" | owner prompt history, Codex, 2026-10-08; measured 2 times; again Codex, 2026-10-08 (1 time) | S-6.12.04, S-6.12.03 | live | S-6.12.04 is live-qualified (release 83: three cards outside the hero), and the homepage read on October 16 shows Basic at $9, Pro at $49 and Max at $99 a month, with Max as a public preview | S-6.12.03 stays building because hosted Max work is not sold. |
| R-153 | 2026-10-08 | "better organize our growing list of APIs for internal research and design and actions as well as APi cloud tools that will be available to users and their harnesses" | owner prompt history, Codex, 2026-10-08; measured 5 times | S-6.218, S-6.218.01, S-6.218.02, S-6.214.04 | proposed | Tenant-scoped hosted live tools (S-6.218) are proposed; its first two subtasks, the tool boundary and provider qualification, are ready | No live API tool is offered, and no freshness or compatibility monitor runs on provider endpoints. |
| R-154 | 2026-10-09 | "make sure we have consistent, best practice, startup design for EVERY single page" and "Can we intelligently integrate all of these, into the live baltor.ai website" | owner prompt history, Codex, 2026-10-09; measured 3 times; again Codex, 2026-10-09 (1 time); Codex, 2026-10-11 (1 time) | S-6.35.03, S-6.67.01 | live | S-6.35.03 is published: release 87 serves the Claude-export design, and its route audit covered 71 pages, 293 views and 830 links with no problem (October 11 handoff) | The complete page and design review (S-6.67.01) is ready and not started, and the standalone sites keep their own designs. |
| R-155 | 2026-10-11 | "we should have ongoing lists and prioritizations of internal research ideas going from numerous steps, spiderying style searches that generate more searches, and more ideas and a swarm of agents" | owner prompt history, Codex, 2026-10-11; measured 1 time | S-6.214.13, S-6.76 | proposed | Bounding and prioritizing follow-up research (S-6.214.13) is ready: the October 11 inspection named the scheduler and managed-record boundaries and proposed 24 known-wrong controls | No frontier admission increment is implemented. |
| R-156 | 2026-10-13 | "No, I want seperate! seperate branding, we have baltor.ai that offers all 3" and "Do we have live websites up on the new domains, what is taking so long?" | owner prompt history, Codex, 2026-10-13; measured 2 times; again Codex, 2026-10-13 (1 time) | S-6.35.06, S-6.35.07, S-6.35.08 | live | Release 90 launched AgentFeeds, release 91 AgentFoundry, AgentAFK and the Don't be a meat proxy campaign, and release 92 AgentStudios; each apex answered HTTP 200 on October 16 | S-6.35.06 stays building for signed-in journeys and the 21 canceled metadata fetches, and agentbriefs.si did not answer on October 16. |
| R-157 | 2026-10-13 | "we just build out things on the side and make notes in files and folders for codex to add in" | owner prompt history, OpenCode, 2026-10-13; measured 2 times; again Antigravity, 2026-10-13 (1 time) | S-6.29 | building | The October 15 Claude handoff saved the shared checkout's 347 staged paths, OpenCode research of October 6 to 7 and 12 to 13, as a patch, and the October 15 takeover preserved the Antigravity workspace before integration | The saved side work is not yet reviewed for adoption into main. |
| R-158 | 2026-10-13 | "All important links that I provide should be saved and processed so I never have to post them again and we can have a database of sources, links, etc." | owner prompt history, Codex, 2026-10-13; measured 3 times | S-6.214.13, S-6.214.05 | proposed | The knowledge radar's curated_seed engine takes official links a person declares, unverified until a link check resolves them (tools/knowledge_radar/README.md), and S-6.214.13 is ready | Links the owner posts in sessions are not collected into that intake. |
| R-159 | 2026-10-13 | "queuing tasks from raw data and prioritizing them" and "self learning queueing system, think of something like airflow but for agents, priortizations, dependencies, graph based tasks" | owner prompt history, Codex, 2026-10-13; measured 1 time; again Antigravity, 2026-10-13 (1 time) | S-6.24.03 | building | S-6.24.03 is building: a reproduced defect that reopened dismissed work is repaired and 140 related tests pass; AgentAFK at agentafk.si is a browser-local Preview without hosted execution (release 91) | Customer queue delivery, learned ranking and its comparison against fixed rules are unqualified. |
| R-160 | 2026-10-13 | "start marketing plans, start generating full marketing videos" | owner prompt history, Codex, 2026-10-13; measured 2 times | S-6.201.03, S-6.204.02 | proposed | A rights-cleared product demonstration (S-6.201.03) is proposed after the accepted creative proof, and DELIVERY-SEQUENCE.md keeps the marketing video plan | No marketing video or launch plan is published. |
| R-161 | 2026-10-13 | "all of our AI images and AI videos and templates uploaded as resources" and "get all of our AI images tagged and uploaded" | owner prompt history, Codex, 2026-10-13; measured 2 times; again Antigravity, 2026-10-13 (1 time) | S-6.201.04, S-6.117, S-6.35.05 | building | Release 89 serves /random image, video and music discovery with 329 image previews, one original video and one music cue (S-6.35.05 published), and S-6.201.04 is building | The owner's media collection is not tagged, uploaded or admitted, and the fresh Kaggle media proof (S-6.201.04) is not reproduced. |
| R-162 | 2026-10-13 | "getting up to 10 million harness components 1 million feed items fully benchmarks, decision support, etc and 1 million photos 200K audio uploads" | owner prompt history, Codex, 2026-10-13; measured 1 time | S-6.215, S-6.214, S-6.201 | on main | OWNER-DECISIONS (consumer value and resource goals) and the North Star record the four targets as goals, not inventories | Only served files are counted live (1,560,856); feed items, photos and audio have no measured baseline. |
| R-163 | 2026-10-13 | "using opencode or some other harness + baltor to solve kaggle problems, especially advanced, difficult problems, hackathons, competitions" | owner prompt history, Codex, 2026-10-13; measured 1 time | S-6.90, S-6.185, S-3.5 | proposed | OWNER-DECISIONS (difficult competition work) records the direction with frozen tasks and matched budgets with and without Baltor; S-6.90 is proposed and S-3.5 is blocked | No trial on a competition or enterprise problem is recorded. |
| R-164 | 2026-10-13 | "a servive that lets people sync, type in, import, or manually share their job descriptions, technologies, major plans, goals, etc" | owner prompt history, Codex, 2026-10-13; measured 3 times | S-6.35.09 | building | S-6.35.09 is building: the local-only AgentBriefs prototype in design/prototypes/agentbriefs/ passed 124 producer and 53 independent browser checks, and the owner confirmed buying agentbriefs.si on October 15 | agentbriefs.si did not answer on October 16, and no registrar, DNS, certificate or company-context proof exists. |
| R-165 | 2026-10-13 | "all hard coded things can be loops that adjust based on the input and output, all tests can be loops etc" (October 14) and "feels like we should fix this rather than just breaking down tasks into smaller components" (October 14) | owner prompt history, Codex, 2026-10-13 (a call ceiling, words not quoted); measured 1 time; again Antigravity, 2026-10-14 (3 times); Antigravity, 2026-10-14 (1 time) | none | not started | AGENTS.md requires each model run to stop before a declared ceiling; no record explains the 12-call value or how a ceiling should follow the task | No step makes a ceiling adapt to measured need, and the cause of the Antigravity output-limit error is unrecorded. |
| R-166 | 2026-10-13 | "avoiding full rebuilds, allowing quick updates and deployments to packages, delta based deployments, and updates" | owner prompt history, Antigravity, 2026-10-13; measured 4 times | S-6.78, S-6.79, S-6.197 | building | Catalogue releases already publish as guarded deltas without an application release (S-6.215.07 and S-6.215.12, both published on October 9) | Application changes still ship as full image releases; the release train (S-6.78) and feature flags (S-6.79) are proposed. |
| R-167 | 2026-10-13 | "how do we actually emulate and test everything from a user landing on a landing page to signing up, to confirming, to payment" and "every page, every setting, every click, every sign up" (October 14) | owner prompt history, Antigravity, 2026-10-13 (make sure everything can serve users); measured 1 time; again Antigravity, 2026-10-13 (2 times); Antigravity, 2026-10-14 (1 time) | S-6.55, S-6.35.06, S-6.182 | building | The release 93 matrix covered twenty hosts and 200 signed-out views, and the live pulse reads 50 rows; local OAuth controls do not establish live signed-in continuity (October 15 takeover handoff) | No recorded journey goes from landing through sign-up, confirmation, payment and harness connection on each site, and persona reviews after each release (S-6.55) are proposed. |
| R-168 | 2026-10-13 | "we can have data based router that based on all of the traces and history and oeprations it can find the most efficient engine for search and retreival for that particular request" | owner prompt history, Antigravity, 2026-10-13; measured 1 time | S-6.74, S-6.51, S-6.32.01 | proposed | Pinned, preferred and automatic engine selection (S-6.74) and learning from retrieval (S-6.51) are proposed, and search runs one engine | No engine is chosen from recorded traces. |
| R-169 | 2026-10-14 | "think about features, that users of each website/plan/fucntion would want, how they would set this up, manage things in UI/UX, via MCP, what visualizations, dashboard pages, telemetry, storage they would want" | owner prompt history, Antigravity, 2026-10-14; measured 3 times | S-6.38, S-6.204.01 | proposed | BRAND-FRONTEND-BACKEND-INTEGRATION.md maps each site's journeys to backend owners and gates, and a familiar customer dashboard (S-6.38) is proposed | No dashboard, visualization or telemetry page exists for a site beyond its account pages. |
| R-170 | 2026-10-14 | "does this allow passing information in a variety of formats, like direct passing of variables, functions, kwargs, parameters, objects, passing database storage locations, URLs, pointers, files, file locations" | owner prompt history, Antigravity, 2026-10-14; measured 3 times | S-6.30 | proposed | DELIVERY-SEQUENCE.md requires flexible fields and pointer carriers to negotiate supported versions and authority before use, under S-6.30 | No pointer-carrying edge from the reviewed designs is integrated. |
| R-171 | 2026-10-14 | "I have provided and can continue to provide thousands of new API endpoints, API keys, etc, how can we put them into a database that is searchable, retreivabale by RAG" | owner prompt history, Antigravity, 2026-10-14; measured 14 times | S-6.214.03, S-6.218.02, S-6.207.03 | building | S-6.214.03 is building over the supplied provider operations, and credential values stay in the system keyring, outside every record (October 11 handoff) | No searchable endpoint database exists, and the earlier registry's artifacts (S-6.207.03) are unrecovered. |
| R-172 | 2026-10-14 | "for internal work (not public facing) we can leverage google drive" and "I could have kaggle workers start up, grab some tasks" | owner prompt history, Antigravity, 2026-10-14; measured 8 times | none | not started | OWNER-DECISIONS (portable workers, October 13) keeps task identity in the backend and requires a task-bound grant for any remote worker; Kaggle production offload is not qualified | No step names Google Drive as internal storage or a Kaggle worker that claims tasks. |
| R-173 | 2026-10-14 | "also can you research mcp market" | owner prompt history, Antigravity, 2026-10-14; measured 5 times | S-6.22 | proposed | /directory lists MCP servers and refreshes daily, and SHARED-RESEARCH-SERVICE-LANDSCAPE-2026-09-27.md lists MCP Market among protocol server directories (50,866 servers on September 27) | No research record after October 14 answers the request. |
| R-174 | 2026-10-14 | "I really like that fuel your agents style, and we should ab/b test accross all surfaces" | owner prompt history, Antigravity, 2026-10-14; measured 3 times | S-6.204.01 | proposed | The homepage read on October 16 leads with 'Give your agent a head start.' and has no fuel wording; onboarding measurement (S-6.204.01) is ready | No A/B test or visitor measurement exists to compare the two lines. |
| R-175 | 2026-10-15 | "using multiple sub-agents, go through and review the entire chat history with antigravity/gemini/agy" and "pickup the baton and continue creating to do lists, justifying to do, implementing improvements" | owner prompt history, Codex, 2026-10-15; measured 2 times; again Codex, 2026-10-15 (1 time) | S-6.217.01, S-6.35.10, S-6.35.11 | building | The October 15 takeover handoff records the review of 67 Antigravity conversations, and its first repair, the public redirect (S-6.35.10), is live-qualified in release 93 | The systems portal binding (S-6.35.11) is ready, and the reviewed queue, worker and engine candidates wait for integration. |
| R-176 | 2026-10-15 | "Consider the following as well:" (the material that followed is not quoted) | owner prompt history, Codex, 2026-10-15 (first measured on 2026-09-24); measured 3 times | S-6.217, S-6.214.13 | building | The next action of S-6.217.01 carries the pasted-research obligations into their owners, and the October 11 handoff keeps the supplied 1,500-topic and Superpowers summaries as leads under S-6.214.13 | No record lists which pasted items were adopted, deferred or rejected. |
| R-177 | 2026-10-15 | "...chunk, separate, historical directions, vectoring, desire measurement, todo list measurement, etc of all historical prompts" | owner prompt to Claude Code, 2026-10-15, again 2026-10-16; added by hand, after the collected corpus | S-6.210 | building | The measurement section above, rows R-111 to R-182 and the report of tools/owner_requests_ledger.py over both monthly ledgers; the raw prompts, labels and judgments stay private | The measurement is a one-off private run with no scheduled rerun, and each row's state is judged by hand. |
| R-178 | 2026-10-16 | "I also need you to get everything ready for launch", with the October 8 definition of row R-136: "adversarially validate every single page, all marketing language, nomeclature..." | owner prompt to Claude Code, 2026-10-16; the October 8 definition is in the owner prompt history, Codex, 2026-10-08, measured 21 times | S-6.67.01, S-6.181, S-6.35.06 | building | Parallel launch-readiness agents started on October 16 (coordinating session), and this ledger's base revision df963c20 holds none of their results; the release 93 matrix passed 4,715 assertions on twenty hosts and retained 21 canceled metadata fetches | No adversarial review of every page and claim is complete, and the release 93 strict result stays false. |
| R-179 | 2026-10-16 | "In addition to confirming EVERY single surface and function and component is ready for launch and paying customers..." | owner prompt to Claude Code, 2026-10-16 | S-6.35.06, S-6.35.08, S-6.182, S-6.66 | building | Parallel agents started this work on October 16; new Pro checkout selects the verified $49 monthly Price (release 88), and every site answered HTTP 200 on October 16, but the public checks cover no real sign-up, email, consent or payment journey on the new domains (current deployment) | No paid journey from sign-up through confirmation, checkout and harness connection is recorded for each site. |
| R-180 | 2026-10-16 | "...we should also try more demos, tests, E2E tests, including using baltor.ai and similar systems to monitor, recreate, redo, side by side comparison of popular coding projects, such as coderabbit lists, github lists of common projects, kaggle, etc..." | owner prompt to Claude Code, 2026-10-16 | S-6.37, S-6.185, S-6.173 | building | Parallel agents started this work on October 16; demo.baltor.ai and examples.baltor.ai answered HTTP 200, and the homepage links a real model and harness run, a quality and token comparison and a competition workflow; the North Star says the current simple examples establish no general benefit | No side-by-side recreation of popular coding projects from public lists or Kaggle is recorded, and the matched studies (S-6.185, S-6.173) are proposed. |
| R-181 | 2026-10-16 | "...and also show how agentbriefs can suggest ways to improve upon them as new technologies, systems, architectures, are released" | owner prompt to Claude Code, 2026-10-16 | S-6.35.09, S-6.214 | building | Parallel agents started this work on October 16; the AgentBriefs prototype in design/prototypes/agentbriefs/ is local-only with synthetic company fixtures (S-6.35.09), and agentbriefs.si did not answer on October 16 | No AgentBriefs suggestion exists for a real project, and no maintained feed of new technologies drives one. |
| R-182 | 2026-10-16 | "we may want to further enforce our infrastructure layering and rules so we have functional components, which are wrapped in multiple layers including flexible edges with objects, pointers, etc that can change, compatibility/handshake layer..." | owner prompt to Claude Code, 2026-10-16 | S-6.30, S-6.84 | building | Parallel agents started this work on October 16; AGENTS.md rule 6 and FUNCTIONAL-COMPONENT-STANDARD.md define the fixed typed edge, swappable engines and conformance kits, engine_slots.yaml declares 55 slots, and DELIVERY-SEQUENCE.md requires flexible fields and pointer carriers to negotiate versions and authority before use | The standard written into the development rules with a check for each rule (S-6.84) is proposed, and no layered pointer edge is integrated. |

## How this ledger is checked

Current behaviour, on `main` with this record:

- [`tools/owner_requests_ledger.py`](../../tools/owner_requests_ledger.py)
  reads, when no `--ledger` is given, every monthly ledger in `docs/context`
  named `OWNER-REQUESTS-LEDGER-YYYY-MM.md`, oldest month first, so today the
  September ledger and this one, and reports their rows together against the
  roadmap. It lists every request whose named steps are not live in the
  roadmap (a live step or subtask is `live_qualified` or `published`), every
  request whose state is not `live`, every request with no step, every
  roadmap step that no request names directly or through a subtask, and
  every step identifier that the roadmap does not know. A row may name a
  subtask, and the subtask's own status decides whether it is live. A request
  identifier that two ledgers share is refused. The dated record under
  [`artifacts/owner-requests/`](../../artifacts/owner-requests/README.md) has
  the record type `owner_requests_report/v2`, with the list of ledgers read
  and the counts of each. `--ledger PATH` reads one explicit file instead,
  `--summary PATH` also writes a Markdown summary, and `--check` writes
  nothing and fails on an unknown step identifier or a malformed row.
- [`tools/test_owner_requests_ledger.py`](../../tools/test_owner_requests_ledger.py)
  runs the tool on fixture ledgers and a fixture roadmap. Its known-wrong
  controls include an October row that names a step the roadmap lacks, an
  unknown subtask and an identifier that two ledgers share. It also checks
  the committed ledgers: every step identifier exists, every row falls in its
  ledger's month, October's identifiers continue from R-110, and a run from
  the repository root with no `--ledger` reads both ledgers.
- The daily cron entry installed on September 27, 2026 runs the tool at
  06:30 UTC from the workstation's main checkout with no `--ledger`
  argument, so it reads both ledgers. It writes the day's record under
  `$HOME/.le-ci-tmp/owner-requests/records/` and the summary to
  `$HOME/.le-ci-tmp/owner-requests/latest.md`.

## What this ledger does not do

- It does not change the roadmap. A state above that disagrees with a step's
  roadmap status is a finding for the integrating session, listed by the
  tool.
- It publishes no private material. No raw prompt, pasted text, chunk,
  label file or reviewer report enters the repository; the quotes are short
  exact excerpts of the owner's own words.
- It is not a complete list of October asks. Asks below the selection
  thresholds have no row, and the asks of September 27 to 30 fall between
  this ledger and the September one.
- It records no approval, budget or permission. Where a row quotes an
  approval, as R-119 and R-126 do, the owner decision table and AGENTS.md
  hold the decision.
