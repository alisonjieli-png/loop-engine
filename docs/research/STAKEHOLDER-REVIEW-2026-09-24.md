# Stakeholder review of September 24, 2026: product, onboarding, growth, trust and the website

Ported to main on September 25, 2026 from commit `3a9fe1d6`, which stayed in a worktree: the steps it added are numbered S-6.181 to S-6.195 here, because S-6.177 to S-6.180 were taken on main that day.

Kind: dated research record, September 24 and 25, 2026. It reports how a
panel review of Baltor was run, which findings independent verification
confirmed, which it refuted, and which line of work owns each action. It
implements nothing, changes no public page and approves no legal text. The
[roadmap](../roadmap/roadmap.yaml) remains the task authority. The confirmed
actions that had no owning step entered the roadmap as steps S-6.181 to
S-6.195.

Scope: product value, onboarding, growth, trust and the website. The review
also produced findings about investment, fundraising, company matters and
hiring. Those are kept in a private record outside the repository and are not
repeated here.

Source state:

- The panels read a private review pack assembled on September 24, 2026
  between 22:05 and 22:45 UTC against `main` at `c93c201f`, the revision that
  Fly release 25 served, and visited the live site on September 24 and 25.
- Verification read `main` at `af800171` and `f0f8c508`, the lines of work in
  flight, and the live site (Fly release 26) on September 25, 2026 between
  about 09:00 and 09:25 UTC.
- This record was written on `main` at `38c5121e`. Its author rechecked the
  live health and capabilities records, the domain records and the GitHub
  repository settings on September 25, 2026 at 09:38 UTC.

## Summary

- **One truth on every public surface is the strongest finding.** 214 of 250
  personas in all 25 panels raised it. The website states unbuilt behavior in
  the present tense, contradicts itself about access, and the README names an
  old release and a review claim that the review record does not support.
  Most fixes are small.
- **Baltor's own negative study is both the main objection and the main
  reason for trust.** The data cleanup study found the served material better
  in 0 of 4 families and worse on phone numbers, at 45 to 446 percent more
  prompt tokens. Panels asked Baltor to lead with it, withdraw the harmful
  item, and make "use nothing extra" a measured answer.
- **No outside person is recorded finishing a task, and nothing counts it.**
  The staff dashboard mixes engineering's own release checks with customer
  downloads. Design partners and one weekly counts-only number come first.
- **The first journey leaves baltor.ai, and nobody can see the library before
  paying.** The emailed sign-up link opens on the Fly hostname, a reload signs
  a person out, and "Browse the library" ends at a sign-in prompt.
- **"Vetted" is weaker than the words around it.** All 43 approvals were
  carried to new bytes, one named reviewer comes from the producer's model
  family, and the item measured as harmful is still served.
- **The owner's simpler hero and three demonstration links have broad
  support, on conditions.** The directory tree must come from a recorded
  step in one harness's layout, a demonstration link needs a saved run, and
  publication pages need a Baltor run behind them.
- **Nobody is named and nobody can be reached.** baltor.ai has no mail
  exchanger record, private vulnerability reporting is switched off while
  `SECURITY.md` points to it, and `/about` and `/contact` answer 404.
- **Two release hazards were found.** The privacy notice on `main` now carries
  a sentence about keeping the sign-in in the browser tab that the owner has
  not approved, and release 28 would publish the Fly hostname in every
  connection entry unless the host file moves first.

## How the review worked

### Panels and personas

The review ran 25 panels of 10 fictional personas, 250 in total. Five groups
of 50 took part: three groups that fund companies (investors, venture funds
and angels), prospective employees, and users, partners and gatekeepers. Each
persona read the shared review pack, visited the live site, and recorded a
decision, objections and improvements. Each panel merged its improvements,
counted votes and gave each a score for impact from 1 to 5 and for effort
(small, medium or large).

The personas are role-plays. A count shows where concerns cluster across
different backgrounds. It is not market demand, and no persona statement is a
real commitment, customer or endorsement.

### Clustering into themes

All 515 merged improvements and 276 top objections from the 25 panel files
were assigned to ten themes. An item that combined several points was
assigned to every theme it addressed. A persona counts once per theme when it
raised or endorsed any item in that theme. Impact is the vote-weighted mean of
the panels' impact scores, and the score of a theme is the number of personas
multiplied by its impact. The clustering scripts are kept with the private
review material.

The top two themes lead clearly. Themes 3 to 9 sit within 90 points of each
other (755 to 667), and counting improvements alone reorders them. Treat the
middle as a tie and sequence it by effort and dependency.

### Independent verification

Separate verification agents checked every item of every theme against the
repository and the live site, and gave each a verdict: confirmed, partly
confirmed, already in progress, or refuted in part. Each verdict names its
evidence, the line of work that owns the action, whether the repository rules
allow the action, and whether it needs the owner. This record reports those
verdicts. Where a verdict corrected a panel's figure, this record uses the
corrected figure.

### The ten themes

| Rank | Theme | Personas | Panels | Impact | Score | Reported |
|---|---|---|---|---|---|---|
| 1 | One truth on every public surface | 214 | 25 | 4.90 | 1,050 | Here |
| 2 | Company, fundraising and hiring matters | 175 | 23 | 4.63 | 811 | Private record |
| 3 | From first visit to first used item | 188 | 25 | 4.02 | 755 | Here |
| 4 | Turn the negative study into proof | 161 | 25 | 4.62 | 744 | Here |
| 5 | Outside users, counted | 166 | 22 | 4.40 | 731 | Here |
| 6 | Focus and continuity | 175 | 23 | 4.04 | 706 | Here, product and trust parts |
| 7 | The owner's hero and three demonstrations | 166 | 24 | 4.16 | 691 | Here |
| 8 | Who runs Baltor, and real channels | 159 | 23 | 4.26 | 677 | Here, trust and contact parts |
| 9 | Make "vetted" checkable | 156 | 24 | 4.27 | 667 | Here |
| 10 | Ready for teams, businesses and buyers abroad | 136 | 24 | 3.89 | 528 | Here |

Of the 50 user, partner and gatekeeper personas, 3 said yes, 22 maybe and 25
no. Each yes was a test, not a recommendation: a free founding sign-up in
Claude Code, a free founding sign-up to test the Pi path, and one paid month
to test the Pi path, the only standard harness with a dated end to end check.
The decisions of the other four groups are in the private record.

## Confirmed findings, ranked

### 1. One truth on every public surface

What was confirmed:

- **Unbuilt behavior in the present tense.** The homepage cards say the Baltor
  Harness breaks a task into small steps and gives each one only the files it
  needs, and that it can start a fresh harness for every step. `/overnight`
  says every step asks the library for its files. `/efficiency` says "Spend
  less on each task", that a smaller or local model "can take on work that
  would otherwise need a large one" and that proven scripts are reused.
  `/learning` says "Every run teaches the next one". The records disagree: the
  setup guide and the Baltor Harness recipe say the engine does not search or
  download from Baltor by itself yet, the README lists a fresh standard
  harness per step as not open, and the How it works page says token savings
  and overnight completion are not established. All 43 served items are
  single Markdown skills, so there is no served code to reuse.
- **Placement claims.** The hero says Baltor puts each file where the harness
  reads it, and the library band says each file lands there: skills,
  instructions, tools and settings. Only the Pi extension installs a skill,
  into `.pi/skills/<name>/`. The protocol tools search and return bytes. The
  Claude Code, Codex and OpenCode recipes read "native end-to-end
  qualification is pending". The deck repeats the claim.
- **Access contradictions.** How it works, `/security`, `/login` and `/setup`
  said sign-up is closed or that an operator issues tokens. Commit `35144f06`,
  now on `main`, fixes all four. Release 28 still serves an operator panel on
  `/setup` without the `hidden` attribute, and `service.js` still says
  "Operator service tokens remain separate".
- **The public capabilities record.** At 09:38 UTC on September 25 it reported
  `registration_available` true beside `access_profile` `operator_provisioned`
  and `waitlist_available` true. No line of work changes either field.
- **The privacy notice.** It says payments are "Planned, when billing opens"
  and that the service never receives prompts. Checkout has been live since
  September 21, and the site's own Access and data page says search text
  reaches the server. The notice is legal text, so the owner approves any
  correction.
- **The README.** On `main` at `38c5121e` it says "Fly release 24" while
  release 26 is live, and it says each of the 43 skills was "approved by three
  independent reviewers from model families other than the one that wrote
  it". The review record names reviewer one as a Claude model, the producer's
  family, names no model for the other two, and shows all 43 approvals carried
  from an earlier review.
- **Status.** The footer's "Service available" is true when shown, but
  `status.baltor.ai` served the homepage and the health record's release
  reference is empty. Release 27 adds a `/status` page.
- **Harness names without their state.** The homepage row, the FAQ and the
  pricing page list five harnesses with no qualification state beside them.
- **The existing check is narrow.** The hero check reads only the hero band
  and would pass every sentence above.
- **Team headings.** "Three things teams do with Baltor" and "What teams do
  with Baltor" sit beside the pricing answer that a team cannot share one
  account today.

Actions:

| Action | Owning line or step | Who acts |
|---|---|---|
| Rewrite the listed sentences: present tense only for what runs today, "designed to" for unbuilt behavior, and remove "Spend less" and the small-model sentence unless a saved run supports them | Showcase line, roadmap S-6.33 and S-6.67 | Engineering |
| Make the hero and library band name what does the work today: the agent searches and downloads the chosen skill; in Pi, the extension installs it. Fix the deck sentence | Showcase line; deck line (S-6.121) | Engineering |
| Serve the register panel by default on `/setup`, remove the operator panel and the `service.js` wording, add a no-JavaScript known-wrong case | Release 28 and persona fixes line; S-6.85 | Engineering |
| Compute `access_profile` from the live registration state or remove it in a new record version, and switch off the waiting list block while keeping its data | S-6.85 (one way in) | Engineering |
| Correct the README release line (link the current deployment section instead), the review sentence and the tier line, with a check that fails on a stale release | `implement_now` for the main session; S-6.34 | Engineering |
| Link the footer status text to `/status` and fill the release reference at deploy | Showcase line; S-6.35 and S-6.68 | Engineering |
| Show one plain state line per harness from `client-recipes.json` | New step S-6.181 | Engineering |
| Widen the claims check to the rendered pages, the README, the deck and the capabilities record, with a claims register | New step S-6.181 | Engineering |
| Change the two team headings and keep speaking to teams | Showcase line | Engineering |
| Redline the privacy notice (payments present tense; search text reaches the service) | New step S-6.192; support line | Owner approves |

### 2. From first visit to first used item

What was confirmed:

- **The founding offer.** No page on the live release names the first 10 free
  accounts each month. Release 27, now on `main`, adds the offer to `/pricing`
  and Get started from a true or false field, so no page can show how many
  places are left.
- **The journey leaves baltor.ai.** The live identity record reports
  `session_persistence` `page_memory` and a redirect address on
  `baltor-pilot.fly.dev`. The release 25 journey recorded the emailed link on
  that host. The guides name `app.baltor.ai` while the homepage names
  `https://baltor.ai/mcp`, and no page lists the hosts a corporate proxy must
  allow.
- **Release hazard one.** Commit `9803ca47`, now on `main`, keeps the sign-in
  in the tab's session storage and changes the privacy notice to say so. Its
  own message says the sentence needs the owner's approval, and no approval is
  recorded in `docs/legal/README.md` or `AGENTS.md`.
- **Release hazard two.** Release 28 commit `62163b00` fills every connection
  entry from the address the service publishes. Because the host file's public
  base address is still the Fly hostname, a visitor on baltor.ai would copy
  `https://baltor-pilot.fly.dev/mcp`. No roadmap step recorded the host file
  move.
- **Discovery.** On the live release every route and every hostname served
  the same page with one title and no Open Graph, card or canonical tags, and
  `robots.txt`, `sitemap.xml` and `llms.txt` answered 404. Release 27 adds
  page metadata, the crawler files and a page for each hostname. The GitHub
  description reads "A Python engine for deterministic, hybrid, and
  non-deterministic task loops.", with no homepage, no topics and no
  releases, and the install lines fetch the moving `main` archive. The
  official protocol server registry returns nothing for Baltor.
- **The library is hidden before payment.** "Browse the library" ends at "Sign
  in to browse", and the workspace prints "Installed vector method:
  deterministic_character_hash". All 43 served bodies are MIT-licensed in the
  public repository. The homepage already shows two real items with their
  name, kind, licence, size and digest.
- **Native harness proof.** Only Pi carries a dated end to end check, and no
  saved record of that September 23 run was found. The protocol tools are
  described as "Authorized intelligence ..." and "Search authorized metadata
  only". Authentication is by host key only, no page has Windows steps, and
  the local 7B model wrote its tool calls as text in 37 of 37 steps.
- **What 29 dollars buys.** The homepage example fetched from GitHub hashes to
  the digest the site shows. The pricing page lists six kinds of material
  while every served item is a skill. The cost of producing and reviewing one
  approved item is not measured.
- **Documentation for people.** The served documentation shows raw request
  records and internal values such as `host_attested`, has no glossary and no
  accessibility statement, and every page ships the hidden staff view.
  Versioned assets are cached for 300 seconds.

Actions:

| Action | Owning line or step | Who acts |
|---|---|---|
| Ship the founding offer lines and add the number of places left, with a fallback when the counter cannot be read | Release 27 line; S-6.89 | Engineering |
| Move the host file's public base address to `https://baltor.ai` before or with release 28, and add a release check on the emailed link host and the published protocol address | New step S-6.182 | Engineering (main session) |
| Hold release 27 until the owner approves the session storage sentence, or take `9803ca47` out | Main session | Owner decides |
| Replace `app.baltor.ai` in the guides, and list the proxy hosts on `/security` | New step S-6.182 | Engineering |
| Set the GitHub description, homepage and topics, cut a tagged release with a pinned install, and publish the registry entry | New step S-6.183 | Engineering |
| Add `llms.txt` and one wide share image for the main pages | SEO and blog line; S-6.46 and S-6.67 | Engineering |
| Remove the vector method sentence, then build a signed-out library page | New step S-6.184, with S-6.39 | Engineering |
| Plain protocol tool descriptions, with a check | S-6.33 | Engineering |
| Rerun the Pi journey with a saved record, then Claude Code, Codex and OpenCode, and update each recipe only from its own record | Sample tasks line; S-6.9 and S-6.66 | Engineering |
| Say on `/pricing` what is free and what Baltor Pro adds, and list only served kinds | Showcase line | Engineering |
| A glossary, a first-ten-minutes article per harness, and an accessibility statement after a keyboard and screen-reader pass | Support line | Engineering |

### 3. Turn the negative study into proof

What was confirmed:

- **Search cannot answer "nothing".** The live search joins up to 12 query
  words in a full-text index and keeps every match, next to a deterministic
  character hash. A local probe on the served 43 items returned five
  references for "bake a chocolate cake recipe" and for two other off-topic
  requests. A judged set exists in `examples/30_search_quality` (354 requests,
  10 with no right answer), and the served policy returned references for all
  10. The serving-at-scale line has a relevance floor calibrated on synthetic
  items, with no explicit none-applies answer yet.
- **One study, near the ceiling.** The only completed with-and-without study
  used 143 synthetic rows and three repetitions, and the cheap model already
  scored 0.948 to 1.000 without material. Three repetitions detect only large
  effects. The SkillsBench pilot exists only as a proposal.
- **The overnight study has not run.** Its frozen design (311 rows, Gemma 4
  31B through Pi on Ollama Cloud) has used 3 of its 600 requests, and its
  checks pass on `main`.
- **No evidence page.** The data cleanup case study on `main` leads with the
  negative result, but it is not linked from the homepage body, `/efficiency`
  or `/overnight`. It says the full report is public without linking it, and
  "We stopped showing the phone item" reads as if the item was removed. It is
  still served.
- **No outcome records.** The service records one usage row per download. It
  records no search, use or acceptance outcome, while `/use-cases` and
  `/learning` describe learning in the present tense.

Actions:

| Action | Owning line or step | Who acts |
|---|---|---|
| Return an explicit none-applies result when the floor withholds every hit, measure the floor on the served release with held-back and no-answer requests, and publish a retrieval report with every catalogue release | Serving-at-scale line; S-6.32 and S-6.70 (not S-6.93) | Engineering |
| Tell the harness in the tool description and the Pi guidance that downloading nothing is a valid choice | Serving-at-scale line | Engineering |
| Freeze and run one outside study: SkillsBench v1.1 with no material, the raw skill, Baltor's selection allowed to add nothing, the forced bundle and the oracle | New step S-6.185 | Engineering, within the owner's model authority |
| Run the frozen overnight study exactly as frozen, then put a nothing-extra arm and a local-hardware arm in a successor design | S-6.37 (no line owns the run yet) | Engineering |
| Generate a dated evidence page from one claims register, and link it from the pages that make the claims | New step S-6.181 | Engineering |
| Link the report from the case study and correct the phone sentence | `implement_now` for the main session | Engineering |
| A local, off-by-default outcome record per item and step; any upload waits for an approved notice change | S-6.41, with S-6.51 and S-6.95 | Engineering, then the owner |
| A third-party-judged result through the Gemma 4 Developer Agent tracks (paper November 12, final entry December 2), reported whatever it is | S-6.90 | Engineering drafts; the owner submits |

### 4. Outside users, counted

What was confirmed:

- **Nothing outside is recorded.** No outside user, paying customer,
  activation or retention figure exists. The release 25 dashboard read 7
  accounts, 0 paid, 0 of 10 founding places, 6 switched off and 93 downloads
  in 30 days. The overview counts every usage row with no tenant filter, and
  every release check downloads as the host tenant, so the 93 include
  engineering's own checks.
- **The acceptance case cannot pass.** The only case with a person outside
  engineering, D-17-T03, is written for a closed, invited beta.
- **Growth drafts need corrections.** The private launch kits are careful
  about platform rules, but the newsletter vote has no coding path, one kit
  says the approved notice covers sign-up counts per link tag (the approval
  covers only list page views, list link follows and ad impressions), roadmap
  S-6.59 plans a reply finder measured on the website, and the referral line
  stores digests without a privacy notice row.
- **No partner door.** `/contact` and `/partners` answer 404. The owner
  authorized a partner mailbox on September 24, and the support line builds it
  without showing the address anywhere.

Actions:

| Action | Owning line or step | Who acts |
|---|---|---|
| Split host, staff and test downloads from customer downloads, with a check and a mutant | Staff tools line; new step S-6.186 | Engineering |
| One counts-only weekly read for the analytics role and one weekly number: outside accounts with a download in the last seven days | New step S-6.186 | Engineering |
| Rewrite D-17-T03 for open registration, and run 10 to 20 outside developers and 3 to 5 teams through a task they chose, with a written criterion and a without-Baltor baseline | New step S-6.186 | Engineering; recruiting posts are the owner's |
| Correct the kits: a coding path in the vote, platform reports instead of per-tag counts, and a person who writes and posts every reply | Private go-to-market kit; S-6.59 wording | Engineering drafts |
| Draft the referral privacy row before referrals switch on | Referrals line | Owner approves |
| Show the partner address on `/contact` once inbound mail works | Support line | Engineering |

### 5. Focus and continuity

What was confirmed:

- **Too many lines at once.** At `38c5121e` the roadmap holds 226 steps, 2 of
  them live qualified, and all 8 release gates read "Not verified". Part of
  that is stale bookkeeping: S-6.16 and the `payment_authority` decision still
  read as pending although payments are live, and S-6.10 is proposed while 43
  items are served. The September 24 handoff lists 19 lines of work.
- **Continuity for customers.** The terms have no notice period, deletion is
  by post, there is no data export, and no incident runbook exists (S-6.68
  requires one).
- **The wedge is a hypothesis.** The dated comparison in
  `docs/research/FRONTIER-HARNESS-POSITIONING-AND-EXPERIMENTS-2026-09-22.md`
  lacks Radius from Pi's publisher, the skills.sh audits and the native
  marketplaces. The part that is checked live: delivery gated by declared
  effects and licence and pinned to exact bytes, with 34 of 43 items offered
  and 9 withheld from a step without the authority.
- **The newcomer path.** The repository has never had a pull request, has no
  code of conduct or templates, keeps Discussions off, and `AGENTS.md` is
  8,184 words. A self-test with only the serving extra reported FAILED with
  3,410 of 3,411 checks passing: the one failure is `duckdb`, an optional
  dependency that the same summary lists as not tested. It printed "about a
  minute" and took 294.8 seconds.
- **How the code is written.** At `af800171`, 692 of 889 commits on `main`
  carry a Claude co-author trailer, including 50 of 57 commits that touch the
  web assets. `main` is not protected and has no rulesets. The README,
  `CONTRIBUTING.md` and `SECURITY.md` say nothing about agent-written code.

Actions:

| Action | Owning line or step | Who acts |
|---|---|---|
| One dated focus decision in the roadmap: three measures until November 2 (outside people through the whole journey, one recorded result, one truth), each paused step named with its reason | `implement_now` for the main session (continuation decisions, D-18) | Engineering |
| An incident runbook exercised once, an operator guide, and a factual continuity answer | S-6.68; new step S-6.194 | Engineering |
| A new dated comparison with Radius, the skills.sh audits and the native marketplaces, and the wedge stated as a labelled hypothesis | S-6.22 | Engineering |
| Report an optional dependency as not run instead of failed, and print the measured duration | `implement_now` (S-6.27 reproduced defects) | Engineering |
| A two-page start for people, a code of conduct, templates and labelled first issues | S-6.34 | Engineering |
| A public statement of how Baltor is built, and a review by a second model family before a change to identity, billing, access or deployment code is pushed | New step S-6.187 | Engineering; branch protection is the owner's |

### 6. The owner's hero and three demonstrations

The owner asked on September 24 for a simpler hero that shows the working
directory each step receives, built on demand with no manual search or setup,
and three links to demonstrations from simple tasks to overnight and Kaggle
work. Panels that took a view backed a directory-tree hero, including 8 of 10
developer relations personas and 9 of 10 data and machine learning student
personas.

What was confirmed:

- **The hero is already on `main`** (commit `7d3e6d26`, the rebased copy of
  `5be7869f`), labelled "Example layout". The tree matches no single harness:
  it puts `AGENTS.md` beside `.claude/skills` and `.mcp.json`, while Claude
  Code reads `.claude/skills` and Codex reads `.agents/skills`. It shows kinds
  the library does not serve (a per-step `AGENTS.md`, `.mcp.json`,
  `lib/blocking_keys.py`). A recorded native placement exists to draw from:
  the E01 pilot, in which Claude Code and Codex listed every placed skill with
  no model call.
- **Height and size.** The homepage on `main` at `f0f8c508` measured 3,929 pixels at desktop
  width and 7,683 at phone width, 181 pixels over the 7,502-pixel phone
  budget. The tree is a 13-pixel preformatted block that scrolls sideways at
  390 pixels. The budget check is not run in continuous integration.
- **No demonstration has run.** `/demo` and `/demo/kaggle` replay real
  searches and digests but no model run, output, score, time or cost. "A
  Kaggle competition, start to finish" contradicts the page's own line that it
  is not a competition score. Two recorded runs exist (the data cleanup study
  and the Pi check), and neither stands behind a demonstration page.
- **Publications.** Nothing on baltor.ai links the owner's published work, and
  `papers.baltor.ai` and `media.baltor.ai` have no domain record. Kaggle shows
  the red-teaming writeup with an Honorable Mention in the Overall Track, and
  the Gemma 4 Good writeup with no prize. The safety framework's continuous
  integration has failed since March 8, 2026, GitHub reads its licence as
  NOASSERTION, and its README shows a static test-count badge. The DueCare
  site answers 503.
- **Media.** None of the 43 served items is a media item, and multi-file
  packages are not served yet.

On the owner's request for more advanced research on presentation: most of it
exists. The page anatomy in
[the showcase research](OWNER-PUBLICATIONS-AND-REPOSITORY-SHOWCASE-2026-09-24.md#the-page-anatomy-baltor-should-use)
covers the result strip, the step timeline, each step's working directory
with digests, a terminal replay, the same task without Baltor, time, tokens
and cost, the independent check, failures and a reproduce block. What is
missing is a reusable run record viewer (S-6.110) and share images.

Actions:

| Action | Owning line or step | Who acts |
|---|---|---|
| Keep the owner's headline and "no manual search, no manual setup", tied to what works today; move instructions, tools and reused code into a "designed to" sentence | Showcase line; S-6.67 | Engineering |
| Redraw the tree in one harness's native layout from the E01 record, keep "Example layout", render it as a nested list at 16 pixels that wraps at 390, and cut 181 pixels from the phone page | Showcase line | Engineering |
| Retitle `/demo/kaggle` and the card to say what the page shows, and add a check that a "start to finish" page has a run record | `implement_now` in the showcase line | Engineering |
| Render `/demo` from the saved data cleanup records, then run the same population with a Codex arm, a no-material arm and a nothing-extra arm | S-6.110 with S-6.161 (no line yet) | Engineering |
| Build `/papers` first, with exact citations and the states "recorded" and "not yet run"; point `papers.baltor.ai` at it only once it exists | S-6.111 (no line yet) | Engineering |
| Correct the DueCare figure in the September 24 research record: the current reading is 89.1 against 88.1 on gemma4:31b, not 87.1 against 84.9 | S-6.112 | Engineering |
| Prepare the safety framework repair as a patch; pushing it, the licence notice, the DueCare site and the dataset visibility are the owner's | S-6.113 | Owner |
| Keep the media lane behind the coding demonstrations; first a seeded render pilot | S-6.116 and S-6.117 | Engineering |

### 7. Who runs Baltor, and real channels

What was confirmed:

- **Contact is by post only.** baltor.ai has no mail exchanger record, and
  `mail.baltor.ai` has none either. Sign-up mail sets no reply address, so a
  reply most likely reaches no mailbox (inferred from the domain records, not
  tested by sending).
- **The security contact does not work.** `/.well-known/security.txt` answers
  404, `SECURITY.md` points to GitHub private vulnerability reporting, which
  answered `enabled: false` on September 25, and `SECURITY.md` covers only the
  library, not the hosted service.
- **Channels are built but not merged.** The support line adds `/help`,
  `/changelog` and `/contact`, and `support@` and `partners@` through
  Cloudflare Email Routing. Its domain plan is not applied.
- **No page names a person.** `/about`, `/team`, `/careers` and `/jobs` answer
  404. Naming the founder reverses a recorded direction, so it is the owner's
  decision.
- **No press or community home.** `/press` and `/community` answer 404. The
  community plan is already decided in S-6.152 and S-6.153.

Actions:

| Action | Owning line or step | Who acts |
|---|---|---|
| Switch on GitHub private vulnerability reporting and confirm it reads true | `implement_now`; new step S-6.190 | Engineering |
| Rebase the support line with a line-survival check, apply the mail plan, release `/help`, `/changelog` and `/contact` | Support line (S-6.130 and S-6.131) | Engineering |
| Serve `security.txt`, add "Report a security problem" to `/security`, cover the hosted service in `SECURITY.md`, set a reply address on account mail | Support line; new step S-6.190 | Engineering |
| Promise no response time until ticket records measure one | Support line | Engineering |
| Build `/about`, `/work-with-us` and `/press` from public facts, with the founder block held for the owner's decision | New step S-6.188 | Engineering; naming is the owner's |

### 8. Make "vetted" checkable

What was confirmed:

- **The phone item.** In the frozen study the served phone skill scored 0.842
  against 0.991 without it. Numbers written with a `(0)` trunk prefix went
  from 6 of 6 right to 0 of 6, and numbers dialled with `011` from 6 of 6 to
  0 of 6. The item is still served, the health record reports 0 withdrawn,
  and `/learning` says items that stop working are withdrawn. The durable
  withdrawal command has never been used. The only adjudication verdict came
  from a model that later failed reviewer calibration, so no valid decision
  exists.
- **The review record.** The record shows 0 approvals as reviewed and 43 by
  carry. All 129 approving decisions have an empty reason. An outside panel of
  four model families approved 0 of 30 comparable starter items, and 29 of
  those 30 had passed the same round that approved the 43. The tier code
  labels an approval with no named tier as Verified (inferred from the code),
  a label the rules reserve for approval by two non-producer families.
- **The generation pipeline.** One generation lane switches off certificate
  verification for its OpenCode process and uses a refusal-removed model. A
  certificate hostname with an offensive word appears in 24 tracked files,
  and the private model server is named in 49 files. `AGENTS.md` carries the live
  payment account identifier and a keyring entry name, which are not secrets.
  Nothing from that lane is served, and deterministic prechecks run before
  any review.
- **The supply chain.** Releases are unsigned. The Pi extension compares
  downloaded bytes only with digests from the same server that serves the
  extension. Declared effects are self-declared, and no threat model is
  written. The bodies and the extension are identical to files in the public
  repository, so a second source exists that no client uses yet.
- **Depth.** The served set is 43 single-file skills: about 16 data cleanup,
  7 machine learning evaluation, 15 agent method and 5 engineering items.
- **Outside authors.** There is no submission route yet (planned in S-6.140
  to S-6.148). The importer's user agent names no contact, there is no
  opt-out, and the neutrality rule covers only the directory page.

Actions:

| Action | Owning line or step | Who acts |
|---|---|---|
| Write the known-wrong check first, then withdraw the phone item with a typed record and the withdrawal command, publish a readable withdrawal line, and repair it only as new bytes | Review throughput line; S-6.47, S-6.83 and S-6.162 | Engineering |
| Fix the tier default so unrecorded reviewer families are never labelled Verified | Review throughput line | Engineering |
| Re-review the 43 under the two-family rule when two calibrated families are reachable, and publish a review card per item | Review throughput line; S-6.63 | Engineering |
| Pause or pin the generation lane, add the hygiene checks, move the two identifiers out of `AGENTS.md` | New step S-6.189 | Engineering; the certificate is the owner's |
| Publish a threat model, sign catalogue releases outside the serving machine, verify them in the installers and the Pi extension | New step S-6.190 | Engineering |
| Give the importer a contact and an opt-out before any outside item is served | Import line; S-6.145 | Engineering |
| Extend the neutrality rule to library search, starter defaults and step selection | Directory line | Engineering |

### 9. Ready for teams, businesses and buyers abroad

What was confirmed:

- **Operations.** One Machine, one encrypted 1 GB volume with snapshots kept
  five days, deploys that restart the only Machine, a live pulse every six
  hours, an empty release reference, request limits held in process memory,
  a host file outside Git, and a last restore drill on September 20 on an
  older image. The free email plan allows 100 messages a day and nothing
  counts them. The architecture record calls durable records (D-05) required
  before a paid public launch.
- **The Team plan** is decided but not on sale, and no organization or seat
  code exists in any line. `/security` says "Do not send private customer
  content yet".
- **The privacy notice and terms** do not name Resend, which sends sign-up
  mail, and have no lawful basis, transfer basis, minimum age, governing law,
  refund statement, founding offer terms or copyright complaint route.
- **Identity.** No second factor exists for staff roles, the only
  authentication mode is a host key, and OAuth is not installed.
- **Web basics.** No `Strict-Transport-Security` header, a DMARC policy of
  `p=none` with no report address, and no CAA record.
- **Abroad.** Checkout sends no tax or Managed Payments parameter. The live
  payments record says Managed Payments is on for the account by default. No
  checkout with an address outside the United States is recorded.

Actions:

| Action | Owning line or step | Who acts |
|---|---|---|
| Snapshot the volume before each deploy and fill the release reference | S-6.35 | Engineering |
| A timed restore of a current snapshot, host configuration in Git, status history and checks every 15 minutes, an email send counter | D-05, D-15, S-6.68, S-6.79 | Engineering |
| Build the Team plan before selling it | New step S-6.191 | Engineering; contracts are the owner's |
| One consolidated privacy notice and terms draft | New step S-6.192 | Owner approves |
| A second factor for staff, then OAuth for the protocol endpoint | New step S-6.193 | Engineering; enrolment is the owner's |
| The header through S-6.33; CAA, DMARC reports, a trust section and a continuity answer | S-6.33; new step S-6.194 | Engineering |
| Ask for Managed Payments on every checkout and record sandbox renewals with addresses abroad | New step S-6.195 | Engineering |

## Refuted findings and why

1. **"Coming" and "Being built" labels.** The owner retired status tags on
   September 23, and the page checks refuse "planned", "being built" and
   "being prepared". Unbuilt behavior is described in a full sentence with
   "designed to", which the product style guide allows.
2. **Stop addressing teams.** `AGENTS.md` names teams as customers, "built
   for" is free marketing language, and a redesign keeps every page. Only the
   two headings that say teams already use Baltor change.
3. **Stated response times.** The support line's own rule forbids promising a
   response time, and a guarantee needs evidence. Measured times can be
   published once ticket records exist. Separate privacy and press mailboxes
   are not needed.
4. **Redirect every request on the Fly and app hostnames.** The live payment
   webhook is registered on `app.baltor.ai`, so only browser page requests may
   be redirected. The emailed link does not pass through the identity
   provider's redirect list.
5. **"No judged queries."** A judged set of 354 requests exists, 10 of them
   with no right answer. Its limits are real: engineering wrote it, and it
   covers the 123-item catalogue, not the 43 served items.
6. **S-6.93 owns the relevance floor.** S-6.93 is the step tool menu. The
   relevance floor belongs to S-6.32 and S-6.70.
7. **The DueCare figure of 87.1 against 84.9.** It comes from an early draft.
   The current results read 89.1 against 88.1 on gemma4:31b over 7,958 pairs,
   and full material scored above the core set for three small-sample models.
   Only the direction holds, on the four large-sample models.
8. **Add a nothing-extra arm to the overnight study, and publish dollars per
   accepted task.** The frozen design forbids new arms after the freeze, and a
   subscription gives no cost per request. The study already uses the harder
   population and a no-material arm. Requests, tokens and seconds per
   accepted step can be published.
9. **Give founding places to design partners.** The first 10 sign-ups of a
   month take them automatically, and the posts promise them publicly.
   Superadmin sign-up links with free monthly Baltor Pro take no founding
   place.
10. **The owner approved funnel counting on September 24.** The approved row
    counts only list page views, list link follows and ad impressions. Six of
    the seven funnel stages can be derived from records the notice already
    lists; first search and route metrics need a new approved row.
11. **Partner reasons "open models served" and "evidence independent of any
    vendor".** Baltor is not a model provider, and the only studies are
    Baltor's own.
12. **Show "US$29".** The owner's September 23 direction keeps "$29 a month"
    on marketing pages. Currency and tax wording in the terms is the owner's.
13. **"No tax is collected."** Unproven: Managed Payments may apply by account
    default. The fix is an explicit parameter and sandbox evidence.
14. **Move durable records onto the free database plan.** That plan has no
    automatic daily backups, and a second instance before D-05 would create a
    second SQLite authority.
15. **A licence warranty for client deliverables.** It widens liability;
    licence evidence per item answers the same question.
16. **OpenID Connect or SAML sign-in now.** It would add a second way into an
    account, against the standing one-way-in decision. It waits for a paying
    team and the owner.
17. **Pause library scale entirely.** It would shrink the paid offer, and the
    owner's 100,000-item target stands. Review throughput stays inside the
    journey measure.
18. **Branch protection with a required human review.** It needs pull
    requests from side branches, which the owner's branch rule forbids, and a
    second person. A path-scoped review by a second model family is the
    engineering step; the rest is the owner's.
19. **Open a Discord only when outside people answer each other.** It
    contradicts the recorded community decision without new evidence. GitHub
    Discussions stays off, and the reason is recorded.
20. **Runtime words on customer pages and uncompressed pages.** "Loop node"
    appears only in the collapsed technical reference on `/docs`, which the
    rules keep, and pages are already compressed with Brotli (the homepage is
    35,856 bytes on the wire).
21. **Publish every item openly.** A full public listing conflicts with the
    anti-scraping rule of S-6.39. The preview is capped to the Verified tier
    with counts for the rest.
22. **Founding places held by test accounts.** Out of date: after release 25
    returned them, 0 of 10 were in use.
23. **The hero wording "Being built:".** The checks refuse it. The hero was
    already adopted as `7d3e6d26`; commit `46d9f251` is an orphaned copy.

## Facts by kind

- **Observed by verification on September 25, 2026, 09:00 to 09:25 UTC:** the
  live copy and its contradictions, the 404 answers for `/about`, `/careers`,
  `/contact`, `/status`, `robots.txt`, `sitemap.xml` and `security.txt`,
  hostnames serving the homepage, the GitHub metadata, the empty registry
  search, the DueCare site answering 503, and the page heights.
- **Observed by this record at 09:38 UTC:** the health record (43 items, 0
  withdrawn, empty release reference), the capabilities record
  (`operator_provisioned` and an open waiting list beside open registration),
  no mail exchanger record, DMARC `p=none`, no CAA record, private
  vulnerability reporting off, and the README lines on `main` at `38c5121e`.
- **Recorded, not rechecked:** the data cleanup and overnight study records,
  the release 25 dashboard, the carried approvals, the generation lane
  settings, the commit counts at `af800171`, and the self-test log.
- **Inferred:** that the 93 downloads are mostly or all internal, that a reply
  to sign-up mail reaches no mailbox, and that the 43 items reach harnesses
  labelled Verified.
- **Missing:** any outside user who finished a task, any paying customer,
  activation or retention data, the cost of one approved item, any overnight
  run, any code reuse measurement, native runs for Claude Code, Codex and
  OpenCode, and the September 23 Pi run log.
- **Figures that changed with time:** founding places (3 of 10 at one check,
  0 of 10 after release 25), commit counts (648 of 845 at `c93c201f`, 692 of
  889 at `af800171`), and homepage heights (live, `main` and the unmerged
  hero were measured at different revisions).

## New roadmap steps

Each step records which of the three focus measures it serves, so the main
session can pause the rest until November 2.

| Step | Purpose |
|---|---|
| S-6.181 | One truth: a claims register, an evidence page, harness states beside their names, and a check over the website, README, deck and capabilities record |
| S-6.182 | The whole first journey on baltor.ai: the public base address, the emailed link and a release check |
| S-6.183 | The front door outside baltor.ai: the GitHub page, a tagged release with a pinned install, and a registry listing |
| S-6.184 | A library page anyone can open, with downloads kept behind an account |
| S-6.185 | A pre-registered with-and-without study on an outside population |
| S-6.186 | Design partners and one weekly counts-only number |
| S-6.187 | How Baltor is built with AI coding agents, and a second-family review of sensitive changes |
| S-6.188 | Company pages from public facts |
| S-6.189 | Generation hygiene |
| S-6.190 | Supply-chain trust for served material |
| S-6.191 | The Team plan, built before it is sold |
| S-6.192 | One privacy notice and terms revision, approved by the owner |
| S-6.193 | Identity controls: a second factor for staff, then OAuth |
| S-6.194 | A trust section and the web basics a reviewer checks first |
| S-6.195 | Payable outside the United States |

## What still needs the owner

- Approving or removing the session storage sentence before release 27
  deploys.
- One consolidated privacy notice and terms revision.
- Whether public pages may name the founder.
- Posting on the owner's channels, profiles and newsletter, and any programme,
  paid placement or advertising.
- Competition entries and submissions from the owner's accounts.
- The certificate on the owner's model server, and changes to the owner's own
  repositories and sites.
- Branch protection and a human reviewer.
- Contracts, including a data processing agreement for a first team.
- Spending beyond the recorded allowance.

## What this record does not establish

- The personas are fictional. Their counts are not demand, and their
  decisions are not commitments.
- No account was created, no form submitted, no email sent and nothing posted
  during the review.
- Some figures are recorded rather than rechecked, and some changed between
  checks; the facts section names them.
- This record changes no page, no legal text and no catalogue. The actions
  above are routed to their owning lines, and the roadmap holds their state.
