# Baltor website redesign brief for Claude Code Design

Kind: a working brief, written on September 26, 2026, for a design and copy
pass over every page and view of baltor.ai. Paste it whole into Claude Code
Design. It describes what exists, why it exists, what must stay, what may
change, and where the biggest gains are. The reviewer has the authority to
redesign and rewrite every page and view within the rules in section 2, and
is asked to use its own judgement wherever this brief says "open".

The owner's direction, in their words: "a lot of the front end marketing
language and design is OK, but can be improved by claude code, especially to
be more startupy, less verbose, more easy to read marketing language, and
more technical stuff moved into the docs subdomain".

## 1. What Baltor is, in one paragraph

Baltor is a hosted library of files that coding agents pick up from a working
directory: skills with their scripts, instruction files, rules, subagents,
commands, hooks, plugin manifests, protocol server settings, contract schemas
and code modules. A person connects the harness they already run (Claude
Code, Codex, OpenCode, Pi or the free open-source Baltor Harness) to the
library. Each step of a task searches the library, downloads only the files
it chose, and places them where the harness reads them, so every step starts
with the right material and nothing else. Customers bring their own model
access and their own keys; Baltor never runs anything on their computer. One
plan, Baltor Pro, $29 a month for the whole library, with one downloaded item
as the measured unit and no overage billing. As of today the library serves
6,398 reviewed packages (42 Verified, 6,356 Community) and grows by about
1,500 a slot, four slots a day.

The public brand is Baltor. The engine, the repository and the Python package
are Loop Engine. That technical name never appears on the marketing pages.

## 2. The rules the redesign works inside

These come from the owner and from the checks that run on every release. A
page that breaks one fails a named check, so the redesign must keep them.

### 2.1 Words

- Plain English for a reader using English as a second language. Short
  sentences. No em dashes or en dashes.
- Marketing language is free: evaluative and aspirational words need no
  proof. A number, a comparison to a named product, "guaranteed" or "always"
  about an outcome, an invented customer, or a capability the product lacks
  is a statement of fact and needs a saved record behind it.
- No runtime vocabulary on the marketing pages: never "Loop", "Loop
  Engine", "runtime", "role profile", "Practitioner", "Intelligence layer"
  or "Solution" on the homepage, How it works, the use-case pages, the
  pricing page or the shared header and footer. Say task, step, files, tools,
  model, information, results. The exact terms live in the technical
  documentation and on GitHub.
- A short list of retired words is refused anywhere in public prose (old
  names for a record and for a task hierarchy, and a two-word label for the
  next step). The exact list is in the repository's continuous integration
  workflow under "Refuse retired public language". Use record, report, log,
  evidence and step instead.
- The price is written "$29 a month", with the dollar sign, never the
  currency's name spelled out.
- No "invitation only", "waitlist", "beta" or "coming soon" language. The
  product reads as fully working, because it is.
- No status tags, badges or fluff that says nothing ("New", "Beta", "AI
  powered"). Every element has a clear purpose or it goes.
- Say "Verified" and "Community" for the two library labels, exactly.
- The owner's positioning phrase is "harness and agent optimized operation".
  It may sit beside energetic headline copy; it is not the headline itself.

### 2.2 Layout and structure

- Every page, route, header link, footer link and section that exists today
  stays, or is removed with an inventory row that names the reason. Sections
  may be merged, shortened, reordered and rewritten, but a page's subject is
  not dropped silently. Cuts are restored into the new design when they were
  wrong.
- One primary action per view. The primary action is Get started, and its
  label never switches with the access state.
- At most one dark band per view. Section padding is one of 0, 32, 40, 48 or
  64 pixels on desktop and 0, 16, 24, 32 or 40 on a phone. The content
  container is 1,312 pixels wide at most, reading text 640, a lead paragraph
  760, with a 64 pixel edge on desktop and 16 on a phone.
- Page height: a long page (the homepage, How it works) at most 4,000
  pixels; a normal page at most 2,700. Documentation pages are exempt but get
  a contents list after 2,700 pixels. No empty vertical run over 240 pixels.
- Text contrast at least 4.5 to 1, tap targets at least 44 pixels, lines at
  most 80 characters. Typefaces are Geist and Geist Mono.
- The header is one row at 1,440 and 1,024 pixels and a menu at 860 and
  390. It holds, signed out: Baltor, How it works, Use cases, Library,
  Pricing, Docs, Get set up, Sign in, and the primary Get started. Signed in:
  Baltor, Workspace, Get set up, Library, Docs, Account, Sign out. An
  operator also sees Administration.
- The footer has four groups (Product, Use cases, Documentation, Company) and
  a base row with the operator, Baltor.AI, and its postal address, 1428 Bryn
  Mawr St, Saxton, PA 16678. Every link listed in section 4 stays reachable.
- The price appears in the first screen of the homepage and the pricing page.
- The pages are one HTML application (index.html with one section for each
  view) plus a few pages the service renders on its own from data: the
  library page, the model directory, the endpoints, Can I run it, the MCP
  directory and the documentation pages. The rendered pages share the same
  header and footer.

### 2.3 Facts that must stay true on the page

- Baltor Pro is $29 a month, one plan, cancel any time from the account page,
  one downloaded item is the measured unit, no overage billing. The first
  accounts from Baltor's own sign-up hold Baltor Pro free each month while
  founding places last.
- Sign-up is email first: the address, then the emailed link, then the
  password chosen on the page the link opens. Creating an account does not
  start a subscription.
- Connecting gives Baltor no permission to run anything on the customer's
  computer. Customers bring their own model access; Baltor never asks for a
  model key.
- Every download names its exact version and is checked against its digest
  on the customer's side. Every served item names its source, licence and
  review. Items that declare file, network or process effects go only to a
  step that declares that authority.
- The data cleanup case study found that library items did not help on that
  test and one made results worse. That sentence stays honest wherever the
  case study is summarised.
- Legal pages (privacy notice, terms of service) keep their text; only their
  layout may change.

## 3. Where the biggest gains are

Ranked by what a visitor sees first and by how much the current copy holds
them back.

1. **The homepage says too much and asks for too little.** Six bands, a
   hero of forty words, a nine-question FAQ and a full pricing summary. A
   startup homepage makes one promise in the first screen, proves it in the
   second, prices it in the third and asks once. Target: under 2,500 pixels
   on desktop, a headline of at most eight words, a subhead of at most
   twenty, one demonstration, three use cases, the price, one closing ask.
2. **Technical detail lives on marketing pages.** How it works names the
   four intelligence layers, protocol facts, digests, request versions and
   effect vocabularies. The use-case pages explain mechanisms. Move every
   sentence a buyer does not need into the documentation (docs.baltor.ai),
   keep one plain sentence on the marketing page, and link.
3. **Every page carries the same two buttons.** Get started and Get set up
   appear on nearly every view, sometimes twice. Keep the primary once per
   view; make the secondary specific to the page (See the demonstration,
   Read the docs, Browse the library).
4. **Sentences are long and careful where they could be short and sure.**
   The copy was written to be exact and defensible. Keep the facts, halve
   the words. Prefer verbs to nouns: "Each step gets only the files it
   needs" beats "The working directory each step of your task needs, built
   on demand from a vetted library and placed where your harness reads it".
5. **The library is the product and the pages under-sell it.** 6,398
   reviewed packages of twelve kinds is a number worth a headline; the
   homepage library band shows six kind names and a number. Show the
   breadth (every kind), the freshness (four releases a day) and the
   review (every file reviewed before it is served), with the counts read
   live from the service where the page can.
6. **The signed-in workspace reads like a console.** Headings such as
   "Intelligence workspace", "Selected material" and "Service access" come
   from the engine's vocabulary. The workspace is a person's library and
   search; name it that way.
7. **Voice.** The pages are correct and calm; they are not yet confident.
   A startup voice is direct, concrete and a little bold. It says what the
   product does for the reader in the second person and does not hedge
   twice in one sentence.

Open to the reviewer: the visual identity (palette, type scale within Geist,
spacing rhythm, illustration or none), the hero composition, whether the
homepage keeps a FAQ, the order of the use-case pages, the names of the
sections, the tone of every button label, the wording of every headline and
paragraph, and the layout of every page within the rules above.

## 4. Every page and view

Each entry names the address, the audience, what the page does today, what
must stay, what is open, and the opportunity. "Copy today" quotes the current
headline and lead so the reviewer can judge the change.

### 4.1 Marketing pages (signed out)

#### Home, `/`

- Audience: a developer or a team lead who has never heard of Baltor.
- Today: a long page. Hero "The perfect harness working directory for each
  task or subtask." with the subhead "Your agent searches a vetted library,
  and Baltor places the instructions, skills, tools and settings it chose
  where your harness reads them", a price line, Get started and Get set up.
  Then "See it work" with three demonstration cards (Clean a customer file,
  Run a long job while you sleep, From the metric to the submission), "The
  library" with six kind tiles and a live count, "What it makes possible"
  with three use cases, "Built for teams that check the details" (Your keys
  stay yours, Exact versions, Nothing runs on your computer), a pricing
  summary, "Questions, answered" and a closing band.
- Must stay: the price in the first screen, the three use cases, the library
  count read from the service, the three trust facts, one demonstration
  entry, the links to /demo, /demo/kaggle, /library, /pricing, /security,
  /privacy, /overnight, /efficiency and /learning.
- Open: everything else, including the headline, the number and order of
  bands, the FAQ, the illustration.
- Opportunity: the largest. Cut to one promise, one proof, one price, one
  ask. A startup hero for this product could say what a step gets and what
  the person gets back: finished work, less spend, no rewriting. Show the
  library as the reason to believe: twelve kinds of file, thousands of
  packages, every one reviewed, growing daily.

#### How it works, `/how-it-works`

- Audience: a visitor who wants to understand the mechanism before trusting
  it.
- Today: "Big problems. Clear steps." A four-step illustrated example
  (Understand the input, Choose an approach, Build or reuse, Check the
  result), then bands on giving each step a starting point, using smaller
  models for smaller decisions, six questions about wasted effort (too much
  context, an expensive model for every decision, missing expertise,
  rewriting code, repeated mistakes), the four building blocks (Context,
  Code, Runtime History and Solution, User Feedback Intelligence) with a
  caption that the hosted service provides a small example, and "Available
  today".
- Must stay: the plain explanation of steps, the fact that customers keep
  control and keys, the "Available today" honesty, the link to the docs.
- Open: the four-block section is the clearest candidate to move to the
  documentation; the six questions could become three; the illustration
  could become the demonstration.
- Opportunity: halve it. Three moves (break the task into steps, give each
  step its files, check the result), one illustration, one link to the
  demonstration and one to the docs for the mechanism.

#### Use cases, `/use-cases`

- Audience: a visitor choosing which story matches their problem.
- Today: "What teams do with Baltor." and three cards linking to the three
  use-case pages.
- Must stay: the three use cases and their links.
- Open: the card design, whether the audience pages (for coding agents, for
  engineering teams, for comparing tools, for protocol and client work) are
  listed here too.
- Opportunity: small. Make each card lead with the outcome and one concrete
  line.

#### Solve complex problems overnight, `/overnight`

- Today: "Solve complex problems overnight." Hand a big job to a small or
  local model before you log off. Bands: how a night of work runs, what you
  need (a model you can reach, a harness, an account), one harness per step.
- Must stay: the claim is a design claim, not a measured one; the page must
  not promise finished work as a fact. The "what you need" list.
- Open: structure, illustration, the level of mechanism detail.
- Opportunity: this is the most startup-shaped promise on the site. Lead
  with the morning: what a person finds when they come back, and what it
  cost. Keep the mechanism to one paragraph and link the docs.

#### More efficient operation, `/efficiency`

- Today: "More efficient operation." Four bands: only the context a step
  needs, smaller models for smaller decisions, reuse code instead of
  writing it again, the right tools, not every tool.
- Must stay: no measured saving is claimed unless a saved record supports
  it. The four ideas.
- Open: the four ideas could be four short lines in one band.
- Opportunity: make it about money and time, in the reader's terms, without
  inventing a percentage.

#### Learning and optimization, built in, `/learning`

- Today: "Learning and optimization, built in." Every run leaves a record,
  the next task starts smarter, measured not guessed, a library that keeps
  getting better.
- Must stay: "designed to" wording where the behaviour is a design, and the
  fact that every run leaves a record.
- Open: everything else.
- Opportunity: shortest of the three; this can be one strong paragraph and
  a link to the case studies.

#### For coding agents, `/for/coding-agents`

- Today: "Your coding agent should not start from nothing." Only what the
  step needs, find the code before writing it again, keep the large model
  for the hard part, your machine stays yours, built for the harness you
  run, one plan.
- Must stay: the audience, the one-plan fact, the list of harnesses.
- Open: the six bands can be three.

#### For engineering teams, `/for/engineering-teams`

- Today: "Every agent on your team, working from the same expertise." One
  reviewed library, reviewed before it is served, keys that belong to a
  person, one account for each person.
- Must stay: one account per person and one person's keys per account (a
  fact of the product today; team plans are planned, not sold).
- Open: everything else.
- Opportunity: say plainly that team plans are coming and that today each
  person subscribes; do not sell a seat that does not exist.

#### For comparing tools, `/for/comparing-tools`

- Today: "What Baltor is, and what it costs." The price, what counts, a
  record you can read, what Baltor is not.
- Must stay: "What Baltor is not" (not a model host, not an agent to
  install, not a framework) and the price facts.
- Open: layout; this page could become a comparison table with honest
  rows.

#### For protocol and client work, `/for/protocol-and-client`

- Today: "The protocol, the client and the setup." The facts, references
  first and bodies second, versions on purpose, ask the service first.
- Must stay: the page exists for the technical reader; it may become mostly
  links into the docs with a three-line summary.
- Opportunity: this is where technical content belongs on the marketing
  side, so keep it exact and short, and move the long form to the docs.

#### Pricing, `/pricing`

- Today: "One plan. The whole library." Baltor Pro is for one person and
  the devices that person connects. A plan card with the founding-places
  note, "What the price does not cover", how usage is counted, how to stop
  paying, what we do not claim, common questions.
- Must stay: every fact in section 2.3, the founding-places note while it
  is true, the link to how review works, the honest "what we do not claim".
- Open: the card design, the order, the FAQ length.
- Opportunity: one card, three facts under it, the questions trimmed to the
  four people actually ask (what counts as a download, can I cancel, do I
  need a model key, is there a team plan).

#### Examples and case studies, `/examples`

- Today: "See Baltor at work." One task in five steps (link to /demo), three
  case studies (data cleanup, Pi and Gemma 4, sign-up protection), and "Try
  your first search" in four steps that prepares a query in the workspace.
- Must stay: the three case studies with honest one-line summaries, the
  demonstration link.
- Open: whether the "first search" walkthrough stays here or moves to Get
  set up.

#### Demonstration, `/demo` and `/demo/kaggle`

- Today: two step-by-step players. The data cleanup task in five steps
  (Profile the columns, Split the addresses, Find duplicates, Propose
  merges, Hand over the copy) and the Kaggle competition in six (Fix the
  metric, Audit the splits, Train a baseline, Find where it fails, Check the
  score holds, Write the submission). Each shows, for a chosen harness
  (Claude Code, Codex, OpenCode, Pi), the search each step ran, the file it
  chose and where it was placed, recorded from the library. Bands: Real
  searches, Your agent chooses, What a measured run found.
- Must stay: the searches and results are recorded, not invented; the four
  harness tabs; the link to the measured case study.
- Open: the player's visual design, the amount of explanation around it.
- Opportunity: these are the best pages on the site. Put one of them on the
  homepage in place of prose.

#### Case studies, `/case-studies/data-cleanup`, `/case-studies/pi-and-gemma-4`, `/case-studies/sign-up-protection`

- Today: three honest write-ups. Data cleanup: the items did not help on
  this test and one made results worse, with results by family, what
  changed because of it, what it does not show, limits and method. Pi and
  Gemma 4: the harness, the model, the key, what happened, try it yourself,
  what it does not show. Sign-up protection: the risk, what Baltor does, the
  live check, limits.
- Must stay: every measured statement and every "what it does not show"
  section. These pages are evidence.
- Open: layout and length of the surrounding prose; a summary box at the
  top of each.

#### The library, `/library` (rendered from the served catalogue)

- Today (as of this brief): counts by every kind of harness file and by
  label (Verified, Community), what the labels mean, one item printed in
  full, a band that sends visitors to create an account for the searchable
  table, and what the served release added, changed and withdrew. No item is
  listed one by one before sign-up; no size or digest is shown.
- Must stay: no listing before sign-up, counts by kind and label, one item
  in full, the release band with withdrawals and their notes, no search
  backend named.
- Open: the visual design of the counts (a table today; could be tiles or a
  bar), the copy of the intro and the sign-up band.
- Opportunity: this page can carry the "reason to believe": the breadth and
  freshness of the library, live.

#### MCP server and agent API directory, `/directory` and `/mcp-directory`

- Today: a free searchable list of MCP servers and agent APIs with where to
  get each, how it connects and how it signs in; category chips, filters
  (offering, origin, transport, authentication), a scrollable list, one page
  for each listing. Refreshed by a scheduled workflow.
- Must stay: every fact carries its source and the day it was read; the
  ordering rule is stated in words; no paid placement.
- Open: the visual design; it is not yet linked from the footer (see the
  site map's unlinked reason) and should be.

#### Models, `/models`; Endpoints, `/endpoints`; Can I run it, `/can-i-run`

- Today: rendered directories with one page per model and per endpoint,
  every fact sourced and dated, a price older than 30 days marked, and a
  hardware check that runs in the page and sends nothing.
- Must stay: sourcing, dating, the commercial relationship rule (every row
  carries "none" and ordering never reads it), the hardware formula.
- Open: the visual design of the tables and the detail pages, the intro
  copy.
- Opportunity: these are traffic pages; give each a short, confident intro
  and a clear link to what Baltor does with the model the reader picked.

#### Deck, `/deck`

- Today: the Baltor deck, problem, product, market and plan, every number
  tied to a saved record.
- Must stay: the numbers and their records.
- Open: slide design and wording.

#### Status, `/status`

- Today: live readings from the service: required checks, the library
  release, accounts and payment, connections, other checks, what the page
  covers, what to do if a harness cannot connect.
- Must stay: the readings are live and the required checks decide.
- Open: presentation.

#### Access and data boundaries, `/security`

- Today: "Know what you share. Control what can run." Service access and
  model access are separate, selected files do not grant execution
  authority, how review works, what reaches this service, current
  operational limits, before sensitive work.
- Must stay: every boundary statement; the "how review works" anchor is
  linked from pricing.
- Open: this page is half marketing and half documentation. Keep a short,
  confident trust page here and move the operational detail to the docs.

#### Privacy notice, `/privacy` and Terms of service, `/terms`

- Today: legal text approved by the owner, with the operator's name and
  address.
- Must stay: the text. Only layout changes.

### 4.2 The funnel and the account (signed out to signed in)

#### Get started, `/get-started` (also `/waitlist`, an old address)

- Audience: a visitor ready to try it.
- Today: "Get started with Baltor." Three cards in order: create your
  account (email address, then the link, then the password), sign in,
  subscribe to Baltor Pro ($29 a month). Links to /setup, /privacy, /terms.
- Must stay: the order (account, sign in, subscribe), the email-first flow,
  the price, the links to the privacy notice and the terms.
- Open: layout, the amount of explanation.
- Opportunity: this is the checkout. Make it one column, three numbered
  steps, and nothing else.

#### Choose your password, `/auth/confirm`

- Today: the page the confirmation email opens. Set a password of at least
  12 characters; states when a link cannot be used; confirms when the
  password is set.
- Must stay: the three states and the rule.
- Open: wording and layout.

#### Sign in, `/login` (and `/auth/callback`)

- Today: "Welcome back." Sign in with email, forgot your password, sign in
  with a service key, disconnect.
- Must stay: both sign-in routes (email for people, service key for
  operators and checks), the forgotten-password link.
- Open: the service-key form can be smaller and lower; most visitors use
  email.

#### Account status, `/signup`

- Today: the state of your account and where to create one; a create-account
  form that sends the confirmation.
- Must stay: it works as an alternative entry.
- Open: it could fold into Get started; keep the address.

#### Get set up, `/setup` (also `/connect` and `/docs/getting-set-up`)

- Audience: a person with an account who wants their first download.
- Today: "Three steps to your first download." 1. Get access (create the
  account, what Baltor Pro includes). 2. Connect your harness (a
  configuration for each harness with copy buttons, a connection test, a
  client token). 3. Search and download (open the first example). Captions
  about what a green connection does and does not prove, and the MIT
  licence of the engine.
- Must stay: every harness's configuration entry, the connection test, the
  distinction between connection and useful completion, the links to the
  account and the docs.
- Open: structure and copy. This page could become a tabbed guide, one tab
  per harness, with the three steps inside each tab.
- Opportunity: the most valuable page after the checkout; make the first
  download happen in five minutes and say so.

### 4.3 The signed-in application

#### Workspace, `/app`

- Audience: a customer with an account.
- Today: "Find material for your next task." Sections: service access (the
  endpoint, copy button), search (a query box, mode, results as cards with
  a Verified or Community badge, the step-function tags, and a details
  disclosure with source, licence, effects and access), and the library: a
  searchable, sortable table of every file the account may see (purpose,
  kind of file, label, step functions, licence, declared effects, written
  for), with a search box and three filters, a detail panel that opens a row,
  and a fetch button for Baltor Pro accounts.
- Must stay: the search and the table, the details a person checks before
  fetching (source, licence, effects, label), the fetch flow with its
  digest check, no size and no digest column in the table.
- Open: names ("Intelligence workspace", "Selected material", "Service
  access" are engine words), the arrangement, the empty states, the visual
  design of results and table.
- Opportunity: call it the library. Search on top, the table under it, the
  detail panel on the right, and the account's status in one line.

#### Account, `/account`

- Today: "Access and usage." Current service identity, connect your
  development tools (client tokens, shown once), recorded usage,
  subscription access (check availability, subscribe, manage). A dashboard
  navigation with Overview, Connect, Keys, Library, Usage, Billing.
- Must stay: tokens shown once and never recoverable, the usage record,
  the billing entry, the navigation.
- Open: layout and names.

#### Administration, `/admin` (staff only)

- Today: accounts, sign-up links, test tokens. Not indexed.
- Must stay: it is a staff tool; plain and functional.
- Open: nothing a visitor sees.

### 4.4 Documentation (docs.baltor.ai opens `/docs`)

- Pages: Documentation home (Set up, search and download; the pages list;
  run the engine on your machine; technical runtime reference), Getting set
  up, Searching and retrieving, Serving and connections, Troubleshooting,
  Your account, Usage and what you pay for, What Baltor is, Access and data,
  Status, Models, Endpoints, Can I run it.
- Today: the documentation pages are generated from Markdown sources in the
  repository and checked against the service source: every field name,
  record version, address, refusal code and command they mention must exist.
  So a sentence moved from a marketing page into the docs may name exact
  fields, and a sentence on a marketing page may not.
- Must stay: the checks above. A documentation page that names a field the
  service does not serve fails the build.
- Open: the documentation home's structure, the order of pages, and a
  "reference" section that receives everything moved off the marketing
  pages: the four intelligence layers, the protocol versions, the effect
  vocabulary, the review process in full, the meaning of Verified and
  Community in full, the operational limits.
- Opportunity: give the docs a clear front door (three paths: connect a
  harness, search and download, understand what you pay for) and a
  reference section that holds the technical material moved out of the
  marketing pages, so the marketing pages can be short.

### 4.5 Shared chrome

- Header: see section 2.2. The brand mark is the husky head on a navy tile,
  traced from the owner's variation 52; never redrawn. The favicon is the
  same mark.
- Footer: four groups and the base row. The MCP directory should gain a
  footer link in the Product group.
- Open: the visual treatment of both, the order inside each footer group.

## 5. Voice and copy guidance for the rewrite

- Second person, present tense, active verbs. "Your agent searches the
  library" not "The library is searched by the harness".
- One idea per sentence. Twenty words is long.
- Lead with the outcome for the reader, then the mechanism in one line, then
  the proof or the link.
- Concrete over abstract: "a skill with its scripts" beats "material".
- Numbers only where a record backs them; the library counts are live and
  may be shown.
- Headlines: at most eight words, no full stop needed, no colon constructions
  ("Baltor: the library for…").
- Button labels name the action and the object: Get started, See the
  demonstration, Browse the library, Read the docs.
- Keep the honest sentences. The site's credibility comes from saying what
  a test did not show. Shorten them; do not remove them.

## 6. How the redesign is checked

- Every page renders at 1,440, 1,024, 860 and 390 pixels wide and in
  landscape on a phone; screenshots of every page and view, signed out and
  signed in, are reviewed before a release.
- The site map (the typed record of every page, its group, its links and
  its scroll budget) is updated with every added, removed or moved page
  and link, with a reason for each removal.
- The public-language checks (retired words, the price phrase, the
  runtime vocabulary) and the layout checks (heights, padding, containers,
  one primary action, one dark band) run in continuous integration.
- The documentation checks hold every technical page to the service
  source.
- Releases go out in small slices: one page or one band at a time, each
  live within the hour, so nothing waits for a big-bang launch.

## 7. What the reviewer may decide alone, and what it may not

The reviewer decides the design, the structure within the rules, and every
word of marketing copy. It may merge, split, reorder and rename sections. It
may move technical content to the documentation and write the documentation
page that receives it. It may propose a new page with its site map row.

The reviewer does not change a fact in section 2.3, the legal text, the
price, a claim's evidence, the header's link set, a footer link's presence,
or the checks. Where it wants one of those changed, it writes the proposal
and the reason beside the page, and the owner or engineering decides.
