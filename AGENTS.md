# Loop Engine instructions for coding agents

This file governs work inside the Loop Engine repository. It is intentionally
short. Follow the linked component documents for details.

## Repository identity

- Repository: `/home/username/loop-engine`
- Remote: `https://github.com/alisonjieli-png/loop-engine.git`
- Product and repository name: Loop Engine
- Python distribution and command: `loop-engine`
- Python import: `loop_engine`
- Public README title: Baltor. The owner retired the earlier title,
  Building with Loops, on September 22, 2026.

Loop Engine is a standalone repository. `/home/username/taedri.dev` is a
separate project and may be consulted as a design reference. Do not merge the
repositories or copy whole files, registries, naming systems, or governance
documents from Taedri.

## North star and current initiatives

Baltor is the public brand. Loop Engine is the repository, the Python package
and the technical name. The product is a hosted intelligence service plus a
local engine. Customers run their own harness and their own models. The
service gives each step of a task the information, skills, tools and reusable
code that the step needs, within the budget and permissions the customer sets.

The north star, in the owner's words of September 22, 2026: make coding
harnesses and multi-agent systems as efficient as possible, so that they
become a frontier harness, a frontier multi-agent system or a frontier
fabric that can solve any unseen task in the most efficient way. That means
the exact amount of context for each step, reusing code instead of
rewriting it, the right amount of intelligence and heuristics for each
decision, and small models doing much more, including work that runs
overnight. The task can be anything: building a pipeline, research, data
work, or software. Turning a complex problem into a solution that can be
used again is one benefit of this, not the north star. Success means
accepted work under the customer's constraints; it does not mean the fewest
tokens, steps or model calls.

The default design gives every step its own harness. The engine breaks the
work into focused steps, and each step is a discrete cognitive or act step
Loop node that runs in a unique, freshly started harness holding only the
context that small step needs, so no harness suffers the context rot of a
long, overloaded session. Read the
[complete behavioral explanation](ASTRA.md#complete-behavioral-explanation)
before describing one.

The customers are developers, teams and agentic systems. A developer can
leave a local model running overnight (for example Gemma 4) and wake up to
finished work; an agentic system can solve large problems with smaller,
cheaper models and the right context for each step. Baltor Pro connects the
customer's client to a searchable library of anything that drops into a
harness: AGENTS.md and other context files, skills, plugins and protocol
server configurations. A paying customer authenticates (today through the
Model Context Protocol endpoint), searches, retrieves the chosen material,
and starts a harness for the step with exactly that material.

The product answers six customer problems: too much context for a small
task, an expensive model for every decision, missing domain expertise,
paying to rewrite code that already exists, the same mistakes appearing
again, and large multi-step, long-horizon problems that small and cheap
models cannot finish alone. The benefits are drafts, not measured claims,
until the [benefit evidence guide](docs/guides/launch-benefits-and-evidence.md)
says otherwise: solving complex and long-horizon problems and producing
reusable solutions, lower cost through cheaper models and fewer tokens, work
that finishes overnight, and optimization, including turning
non-deterministic work into deterministic solutions. Use cases to prove and
show: a developer connects Baltor so that tickets are worked overnight on a
local model; a developer cleans a data set without asking an expensive model
to do simple transformations; a full solve of a data science competition from
task to submission.

Every functional component is wrapped behind a fixed, typed, versioned edge
with one or more swappable engines behind it, at the component level and
above and below it. A harness or a Loop may send engine preferences within
its authority, and the runtime selects the most efficient eligible engine by
declared order and recorded evidence. The folder structure should follow the
components and their engines. The earlier custom loop-node engine may return
as one more engine behind the same executor edge. Before building any
component, search for existing projects, repositories, designs and papers to
reuse, and record the decision.

```text
Current initiatives, in priority order
├── 1. One main line, live and checked (roadmap package D-18)
│   ├── Every branch and worktree merged, silent merge losses restored
│   ├── Releases only from a committed revision whose checks passed, then
│   │   automated checks on every live hostname
│   ├── One home for rules and authority; every README matches reality
│   └── Website fixes from the persona review; sign-up email switched on
├── 2. Private beta for invited users (D-17)
│   ├── Personal accounts and personal client keys
│   ├── Every approved harness intelligence item shipped
│   └── One native client that demonstrably loads selected material and
│       finishes a checked step in its own harness
├── 3. Engines behind fixed edges for every functional component (D-19)
│   ├── The shared engine framework, harness preferences, evidence ranking
│   ├── The harness executor slot: one harness per step, Agent Client
│   │   Protocol first
│   └── Search and retrieval engines with a relevance floor
├── 4. Demonstrations, case studies and benchmarks with and without Baltor,
│      each on its own subdomain (competitions, data cleanup, agent benchmarks)
├── 5. Evidence for the launch benefits, under explicit model authority (D-07 to D-09)
├── 6. Durable cloud records, files and retrieval (D-05)
└── 7. Continuing work: research, the Y Combinator package, removal of unused
       pre-launch compatibility, and reproduced defects (D-12, S-6.26, S-6.27)
```

The authoritative task state is [roadmap.yaml](docs/roadmap/roadmap.yaml) and
its [generated status](docs/roadmap/CONTINUATION-STATUS.md). The
[takeover checkpoint](docs/context/TAKEOVER-CHECKPOINT-2026-09-20.md) records
the working cycle for changes, tests, checkpoints and releases, the private
beta definition, and the live state and open findings of September 20. The
newest dated handoff, named in the [context route](docs/context/START-HERE.md),
records the live state since then. Follow the working cycle. In short:

- Write the check for the known-wrong case before the repair. A removed guard
  must fail a named check.
- Record state in the roadmap and regenerate the status file. Do not start a
  second task list, dashboard or plan.
- Save every report under a new name. Keep failed attempts beside their
  successors.
- Release only from a committed revision whose continuous integration run
  passed, deploy by image digest, and keep the previous image for rollback.
- A record that an older release must not honor needs a new record version,
  so that the older release refuses it.
- Offered, fetched, loaded, used and verified are separate facts. A count of
  passing checks is not a working customer journey.

## Start here

Before material work, inspect the current branch, revision, dirty state,
active processes, and concurrent writers. Then read only the documents needed
for the task:

1. `README.md`
2. `docs/architecture/CONSTITUTION.md`
3. `architecture.yaml`
4. `terminology.yaml`
5. `docs/contracts/README.md`
6. `docs/components/README.md`
7. the relevant component README
8. `humanizer-context.md` for public prose
9. `docs/context/START-HERE.md` after a new or compacted session. It names
   the newest dated handoff, which records the verified live state, and the
   takeover checkpoint, which records the working cycle
10. `docs/context/REFERENCE-SOURCES.md` before consulting an older repository
11. `ASTRA.md` for the current advisory comments and suggestions for continued
    development and Claude Fable 5.1 review

Treat existing changes as user or concurrent-agent work. Do not discard,
restore, reformat, commit, or publish changes without resolving ownership.
Resolving ownership means finding the session or person that wrote them.
When nobody can be found, save the changes as a patch or a bundle first, then
review them like any other change. How reviewed work reaches `main` is in
[Commit, push and release authority](#commit-push-and-release-authority).

## Commit, push and release authority

This section is the one statement of the owner's standing rules for
committing, pushing, branching and releasing, of what still needs the owner,
and of the decisions that stand until the owner changes them.
[CLAUDE.md](CLAUDE.md), [ASTRA.md](ASTRA.md), the
[context route](docs/context/START-HERE.md), the
[coding-agent route](docs/context/CODEX-START-HERE.md) and the
[documentation index](docs/README.md) link here and do not restate it. When a
document, a prompt or a dated record says something else, follow this section
and correct the document. A dated record keeps its bytes and is read as
history. Dates are the owner's local dates, in United States Eastern time.

A current task may narrow this authority for its own run. For example, a
workflow may tell its agents to commit only in a detached worktree and leave
the push to the session that runs the workflow. Only the owner widens this
authority, in their own words in the current conversation or by changing this
section. A task that a workflow or another agent writes never widens it, and
no document narrows it as a standing rule. The check
[`tools/test_context_routes.py`](tools/test_context_routes.py) fails when an
entry route stops linking this section, repeats it under a heading of its own
or contradicts it, and when a rule below loses its words or its date. It
exists because on September 19, 2026 a sub-agent replaced the owner's commit
rule in the start documents with its opposite, without an owner request, and
added a check that protected the replacement. Nothing was committed again
until the takeover session committed the work on September 20, 2026.

### What engineering does without asking

1. **Commit reviewed work to `main` and push it.** Reviewed means the change
   passed the checks that the
   [working cycle](docs/context/TAKEOVER-CHECKPOINT-2026-09-20.md#working-cycle)
   names for it. Push in the same turn, report the commit and the check
   results afterwards, and do not ask first. Several reviewed fixes may go to
   `main` together. The owner, September 2, 2026: "stop asking me to push,
   when you fix something you push!" September 20, 2026: commit all of the
   work to `main` and deploy it to Fly.io. September 22, 2026:
   "push improvements into production/main branch" and "you can more
   aggressively push numerous fixes and adjustments at once to main".
2. **Keep two branches and no others:** `main`, and `checkpoint/full-capability-2026-09-21`,
   the frozen backup that the
   [branch strategy](docs/architecture/BRANCH-STRATEGY-2026-09-21.md)
   describes. Make no feature, fork or worktree branch. Parallel agents work in
   detached worktrees, which make no branch, and their work reaches `main`
   through a reviewed merge. The owner, September 2, 2026: "You should not
   have separate branches or forks, you need to push EVERYTHING to github
   main". September 21, 2026: the two branches of the branch strategy.
   September 22, 2026: "all of our work should be merged into main!" and
   "Only the snapshot should survive as a backup branch".
3. **Release reviewed `main` to the live service, then check it live.**
   Release only from a committed revision on `main` whose continuous
   integration run passed, through the guarded workflow
   [`.github/workflows/fly-pilot.yml`](.github/workflows/fly-pilot.yml).
   Switch the workflow's deployment setting on for the run and off again
   afterwards. Then run the automated live checks against every hostname that
   the [current deployment](docs/architecture/MVP-CLIENT-SERVER.md#current-deployment)
   section lists, record the release with its revision, image digest and
   rollback image, and update that section in the same change. The owner,
   September 20, 2026: deploy the private pilot to Fly.io, with the release
   steps of the working cycle recorded the same day. September 22, 2026:
   "make sure we are deploying and updating fly.io" and "you should do full
   automated QA of all aspects as well yourself once it is live, using the
   real website endpoint".
4. **Decide instead of asking, and write the reason down.** When a choice is
   uncertain, research it, measure it or test two versions. Put the reason
   where the next session will find it: the commit message, the roadmap, the
   dated handoff, or the decision table below. The owner, September 20, 2026,
   in the evening, objected to "asking me to make decisions when you can make
   your own judgement decisions or A/B test". September 22, 2026: "Use your
   best judgement, document it". September 23, 2026: "You need to stop asking
   me for stupid 'decisions for you', your just is to use best practices, or
   implemeent necessary tools to collect data then make a decision. We don't
   need real paid device for testing." A report therefore ends with the
   decisions made and their reasons, never with a list of questions; where
   data is missing, build the tool that collects it, then decide.
5. **Never tell the owner to rotate, revoke or re-create a credential.** This
   covers a credential pasted into a chat window and a full secret live
   payment key. State a genuine new risk once, store the credential in the
   system keyring and continue. Keep the controls that prevent an accident,
   such as refusing a test key where a live key is required, and record an
   override the owner has chosen instead of arguing with it. The owner,
   September 19, 2026, to the previous developer session, and again on
   September 21, 2026: "NEVER tell me to rotate or revoke an API key".
6. **Build every functional component so that its engine can be swapped,
   and look for existing work first.** A component, or a graph of components,
   has a fixed, typed and versioned edge, one or more engines behind it, room
   for custom variations, and runtime selection by declared order and
   recorded evidence. A new engine is added without changing its callers.
   Before building, search existing projects, repositories, published designs
   and papers for something to use or adapt, and record what was found and
   why it was adopted, adapted or rejected. An engine is an adapter that a
   Loop uses, never a new runtime type. The owner, September 21, 2026: "every
   functional unit should be wrapped so that we can replace the unit engine
   without impacting functional unit to unit edge communication". September
   22, 2026: engines "for each functional component so that the runtime can
   select the most efficient engine", and a search for "projects, repos,
   github, designs, or papers that we could use / leverage so we don't have
   to reinvent the wheel".

### What still needs the owner, in the current conversation

Ask in the current conversation before any of these, even when a prepared
connection would allow it:

- destroying or deleting an application, a volume, a domain record, a name
  server delegation, a provider resource or a secret (September 20, 2026);
- spending beyond the recorded allowance. The
  [deployment scope](artifacts/architecture-audit-2026-09-19/pilot-deployment-authority.json)
  of September 19, 2026 allows 50 United States dollars a month and 10
  dollars of setup for infrastructure, and nothing for model calls
  (September 20, 2026);
- a legal commitment, such as publishing terms of service or a privacy
  notice. The [drafts](docs/legal/README.md) wait for the owner
  (September 20, 2026). On September 22, 2026 the owner approved the privacy
  notice, with Baltor.AI as the operator and the postal contact address
  1428 Bryn Mawr St, Saxton, PA 16678. On September 23, 2026 the owner
  approved the terms of service, in their words "I have approved the terms",
  and the terms are published at `/terms`. On September 24, 2026 the owner
  approved the privacy notice changes drafted that day for support messages,
  chat, replies drafted with a model provider and aggregate link counting, in
  their words "I approve the privacy notice"; the published notice must match
  those drafts and add no other use of personal data. The same day the owner
  took on advertising spend: "I will manage adspend". Engineering prepares
  landing pages, measurement and written instructions, and spends nothing on
  advertising itself. Later the same day the owner authorized engineering to
  carry out every item on the owner action pages it had prepared, in their
  words "you have my explicit authorization to implement and deploy all":
  the paid link wording, the referral programme, the plans above Baltor Pro,
  competition entries, the partner mailbox, repository licences and the
  newsletter and social drafts. What stays with the owner is only what
  engineering cannot do: their own hardware, their personal sign-ins and
  posts, identity, tax and bank details, and submitting the YC application
  from the founder's account;
- identity or bank verification with a provider, which only the owner can
  complete (September 20, 2026).

The authority recorded on September 20, 2026 does not cover model calls, live
charges or opening public registration. On September 22, 2026 the owner widened
it for model calls, in their own words: "A model budget, we can just use Ollama
cloud, you already have the key", and "You can use Claude Code, Kimi 3, GLM
5.3, and other Ollama models as well as Codex models to conduct the review".
Model calls may therefore run through Ollama Cloud with the key already in the
environment, within the owner's existing subscription and with no extra
purchase, and through the Codex and Claude Code command lines, for review,
generation and measurement. Every call is recorded with its model, usage and
outcome, and a run stops before a declared ceiling. On September 23, 2026 the
owner said that Ollama Cloud is enough and that nothing needs to run locally:
"we'd be better off just using Ollama Cloud, we don't actually need the model
running locally on our system", and more fully: "Remember, Baltor is not a
tool to run models, people are expected to bring their own API key, or auth,
or API + auth to be able to access whatever system they have Ollama + local
model at 127.0.0.1, Ollama cloud, another system in their house on a local IP
running local AI endpoint, etc. We can still prove out overnight solving using
cheap/local models using Ollama Cloud and something like Gemma 4". Customers
therefore bring their own model access: a key, a sign-in or both, for
whatever model system they run. Engineering's overnight proof runs use Ollama
Cloud with a cheap model such as Gemma 4, not a local download of the
model. Live charges still stay outside the authority. A customer paying
through the live checkout is the product working, not a charge that
engineering makes. On September 23, 2026 the owner approved opening public
registration: "you can open it". Engineering opens it once sign-up is
email-first, with the address first, then the emailed link, then the choice
of a password, and once the identity provider's own public sign-up is
closed. A live probe of the identity provider that day found that a second
sign-up request for an unconfirmed address keeps the first password and
cancels the first link, so whoever registers an address first would set its
password and the real owner of the address would activate that account by
confirming it. Until both changes are live, registration stays closed.
On September 24, 2026 engineering could not close the provider's own sign-up:
the provider authorization's refresh was refused, and a refused refresh needs
the provider's sign-in again. The owner had said on September 23, 2026: "You do
not need my input to fix these remaining 'needs you' items, you can use your
judgement to fix these". Release 24 closes that way in at the service instead.
An account that Baltor's own sign-up did not create cannot sign in or activate,
and it is archived and replaced when the owner of its address signs up through
Baltor. A live check that day registered an address through the provider's own
sign-up first, and after Baltor's sign-up the provider refused that first
password. Engineering therefore counted the second change as live and opened
registration on September 24, 2026. Closing the provider's own sign-up is still
worth doing once its authorization is renewed.
Intelligence is published only after
the independent review process in the decision table approves it, and a
producer never approves its own work. Everything else that engineering can
decide, it decides.

### How reviewed work reaches `main` without losing any of it

These practices come from engineering, not from the owner. Each one answers a
recorded loss.

- After a merge, check that every line the merged branch added is still
  present, as well as running the checks. On September 22, 2026 automatic
  merges dropped branch content with no conflict while service smoke and the
  conformance gates still passed. The
  [September 22 handoff](docs/context/SESSION-HANDOFF-2026-09-22.md) lists
  what was lost.
- Before any command that can discard work, such as a reset, a stash drop or
  a forced checkout, save the work as a bundle or a patch. Never drop a stash
  or reset a checkout that another session shares.
- Squash-merge a branch whose history holds key-shaped test fixtures, and
  never bypass the repository host's push protection (September 21, 2026).
- Do not rewrite the published history of `main`. The checkpoint branch stays
  at revision `a3bd0f1`.

### Decisions that stand until the owner changes them

On September 20, 2026, in the evening, the owner told engineering to stop
bringing back decisions that engineering can make. The target is a system that
is ready for paying customers. These judgment calls were made under that
direction. Each stands until the owner changes it.

| Decision | Choice and reason |
|---|---|
| Approval of intelligence items | Delegated to an independent review process. Reviewers who did not write an item approve or reject it against written criteria, and the approval record names them. A producer still never approves its own work. The owner can withdraw any item. |
| Price | One plan, Baltor Pro, 29 United States dollars each month. Comparable entry plans cost 19 to 29 dollars. Search is free, the measured unit is one downloaded item, and there is no overage billing at launch. The first 10 accounts from Baltor's own sign-up hold Baltor Pro free each month, and a superadmin can grant or revoke free monthly Baltor Pro for any account (the owner, September 23, 2026). |
| Payments | Live since September 21, 2026. The first call was to build and qualify everything in Stripe test mode and to wait for the owner's identity and bank verification. The owner activated the live account and supplied its key that morning. The live account `acct_1UHZ972IF9bCskLc` is separate from the sandbox `acct_1UHZ9KCCxLfArYED`, with charges and payouts enabled and nothing outstanding. Checkout and the customer portal were proven against the deployed service and nobody was charged, as the [live payments record](artifacts/architecture-audit-2026-09-19/live-payments-enabled-1.json) shows. The key is in the system keyring under `stripe-live` and reaches a command only through `tools/operator_credentials.py`. |
| Sign-up email | The service creates the confirmation link through the identity provider's administration interface and sends its own email, so the whole journey stays on the baltor.ai domain and needs no change to provider settings that engineering cannot reach. |
| Browsing for signed-in users | The owner's words were heard as browsing the intelligence layers. Signed-in users get a catalogue browser grouped by the four layers. It reached `main` and the live service in release 13 on September 22, 2026. |
| Public positioning | The category line is harness and agent optimized operation, the owner's phrase. |
| Hosting plans | Stay on the free Supabase and Resend plans. The owner, September 22, 2026: "Why do we need supabase and resend paid plans? I thought we don't need that?" The free limits (a project pauses after a week without activity; 100 emails a day) fit an invited beta; engineering keeps the identity project active and watches the email cap, and asks again only when usage nears a limit. |
| Public registration | Open since September 24, 2026, release 24. There is one way in: Baltor's own sign-up, with the address first, then the emailed link, then the password. Staff roles are fixed in code (superadmin, developer and analytics), and the host file only names who holds one. The reason and the live evidence are in the authority text above and in the [release 24 record](artifacts/architecture-audit-2026-09-19/pilot-release-24.json). |
| Operator and contact | Baltor.AI, 1428 Bryn Mawr St, Saxton, PA 16678, United States, as the owner gave on September 22, 2026. The privacy notice names it. |
| A library of 100,000 harness files | The owner, September 22, 2026: 10,000 fully searchable, retrievable, indexed harness intelligence files; material without a licence that allows direct copying is used only as inspiration for an original rewrite; reviews by Claude Code, Kimi, GLM, other Ollama models and Codex models; managed releases of new files; user settings with good defaults. Later the same evening: "we need to move towards a fully working SaaS, better UI/UX, and 100K harness files". So 10,000 is the first milestone and 100,000 the target, counted as distinct approved packages of any file type a harness reads, as the Intelligence rules define harness intelligence. Engineering's plan is roadmap step S-6.40 and the steps it names. |
| Library tiers | Every served item shows one of two labels. **Verified**: approved against the written criteria by independent reviewers from at least two model families that did not produce it, with every automated check passing. **Community**: a file whose licence allows direct copying and whose provenance is pinned, or a candidate from a family other than its reviewer's, that passes every automated check (licence allowlist, provenance, secret and safety scanners, and its own tests where it has code) and one independent review by a family that did not produce it; it is labelled Community everywhere and a search filter can exclude it. No family ever approves what that family produced, and a Community item becomes Verified only through the full review. Reason: on September 24, 2026 the owner asked for 1,000 and more harness components fully live and for permissively licensed material of every file type, while only one outside review family was reachable (the Tactical server was unreachable and the Ollama Cloud and Codex allowances were spent). |
| Plans above Baltor Pro | The owner delegated the choice on September 24, 2026: "Proceed with all of this, you don't need my decision for these, use your best judgement". Baltor Pro stays at 29 United States dollars a month. Studio at 99 dollars a month adds private projects and versioned workflows with more storage; Team at 299 dollars a month adds seats, roles, a shared private library, budgets and approvals; an Organization plan is priced on request later. A plan is sold only when its features pass their checks, and its Stripe price is created in the same release. Reason: the owner's goal of $100K MRR within 90 days needs plans above one individual subscription, and nothing is sold before it works. |
| Kaggle and OpenML showcases | The owner, September 24, 2026: "you should use your own judgement to enter a variety of Kaggle competitions or other openML problems, solutioning, building examples, that can showcase baltor", and "you have my go ahead to draft kaggle notebooks, systems, folders, experiement, ideate, learn". Engineering chooses and enters competitions and OpenML tasks that showcase Baltor, follows each competition's rules, and keeps code for a running competition off the public repository when its rules require sharing on Kaggle. For the Gemma 4 Developer Agent tracks engineering drafts the paper and the package, and the owner reviews them before the final submissions. |

## Pre-launch version policy

The owner confirmed on September 19 that Loop Engine has not launched and
has no users requiring old interfaces. Do not add or retain compatibility
code solely for pre-launch record shapes, imports, aliases, or constructors.
Update in-repository callers and tests to the current contract together.
Keep explicit component, profile, record, and adapter versions, exact digests,
and compatibility handshakes. Reject unsupported versions before effects.
An incompatible version is not permission to silently downgrade or reinterpret
fields. Preserve historical evidence bytes without making them active runtime
inputs. See the [version policy](docs/architecture/ADR-PRELAUNCH-VERSIONED-CONTRACTS.md)
for the distinction between contract versioning and legacy support.

The owner's later September 19 clarification also requires deliberate runtime
compatibility between independently deployed component versions. Negotiate
the mutually supported protocol, schema, capabilities, and qualified adapter
at initialization and validate the selected binding at use. Continuous
integration tests this logic; it does not replace runtime negotiation. This
does not revive obsolete pre-launch formats or permit automatic field guessing.
Refuse a downgrade that loses required semantics, integrity, or authority checks.

## One Loop runtime

Every executable graph vertex is a Loop. Do not create another operational
runtime type.

Before creating a class whose name ends in `Node`:

1. Stop.
2. Confirm that no active first-party `*Node` class is permitted.
3. Represent the concept as a typed object consumed by `Loop`, a
   `LoopProfileSpec`, a payload, a reference, a result, a report, a policy,
   a contract, an artifact, or a RepositoryEntity.
4. Retired serialized `kind: loop_node` records are unsupported runtime input.
   Preserve historical files without an automatic migration reader.
5. Do not create a Node subclass. The canonical Loop class refuses subclassing
   at class-creation time.

Before creating a new top-level folder:

1. Identify its stable architectural boundary.
2. Explain why attributes, records, or catalog queries are insufficient.
3. Add a README and architecture contract.
4. Add import-boundary tests.
5. Update `architecture.yaml`.
6. Create an architecture decision record when the architectural model changes.

Do not infer executable behavior from prose, tags, labels, filenames,
folder names, examples, or comments. Permissions, contracts, routing,
budgets, compatibility, and lifecycle must come from structured typed
fields.

Keep these dimensions separate:

```text
Loop
├── Operational relationship
│   ├── Starting
│   ├── Spawned by
│   ├── Queried by
│   ├── Retrieved by
│   └── Connected from
├── Role: Practitioner, Intelligence, or Solution
├── Mode: deterministic, hybrid, or non-deterministic
├── Step profile: atomic, compact, reference nine-step, or custom
├── Typed input and output contract
├── Loop condition and exit condition
├── Budget and permissions
└── Run History records
```

A Starting Loop has no incoming Loop relationship. A Spawned Loop records one
spawning Loop ID. A spawning Loop and a Loop it spawns may use different
modes. A mode never grants file, network, secret, model, spending, or
external-effect authority. Active readers and writers must reject retired
topology fields. Historical evidence may retain them without runtime support.

Keep semantic relationships distinct. A Starting Practitioner may spawn a
Practitioner subproblem Loop and query an Intelligence Query Loop. That Query
Loop retrieves Intelligence Item Loops and returns typed references or
material. A Starting Solution runs deterministic pipelines through Connected
Solution Loops. Use Spawned Solution Loops only for a real dynamic branch,
fallback, repair, or ensemble member.

A Loop is the only executable graph vertex. Every displayed Loop names its
role and exact profile, its own mode, typed input and output ports, loop
condition, exit condition, and graph relationships. Passive records, services,
ports, slots, and edges are not graph vertices. A Canvas or pipeline does not
have one execution mode. It may declare only a policy for the modes permitted
on its member Loops.

Every operational boundary must appear in the existing
`core.boundary_registry` with runtime type `Loop` and either an
exact registered role profile or a validated typed profile source. Static
Architecture has only three public capability groups: Intelligence Search and
Retrieval, Web Research, and Custom Plugins. Providers, settings, workspaces,
approvals, stores, Runtime Memory, Run History, reports, playback, and provider
adapters are internal runtime mechanics. A capability or internal mechanic is
not a graph vertex, but the work that uses it must be owned by a classified
Loop. Missing, extra, unknown, unversioned, or role-incompatible boundaries
fail conformance.

Self-improvement is a Practitioner task. It stages candidates for independent
review and cannot approve its own work.

## Required architecture trees

Use text trees or Mermaid trees whenever a document explains three or more
architecture branches. A flat paragraph is not enough for the Loop hierarchy.
Start with the complete classification tree before showing a specialized
branch.

```text
Operational runtime type
└── Loop
    ├── Operational relationship
    │   ├── Starting
    │   ├── Spawned by
    │   ├── Queried by
    │   ├── Retrieved by
    │   └── Connected from
    ├── Role
    │   ├── Practitioner
    │   ├── Intelligence
    │   └── Solution
    ├── Versioned role profile
    ├── Purpose and domain categories
    ├── Run mode
    │   ├── deterministic
    │   ├── hybrid
    │   └── non-deterministic, with model-led semantic work
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition
    ├── Exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the selected mode permits a model
    └── Run History records
```

Use the words precisely:

- Runtime type answers, "What operational object runs?" The answer is always
  `Loop`.
- Relationship answers, "How did this Loop enter the active structure?" The
  answer is Starting, Spawned by, Queried by, Retrieved by, or Connected from.
- Role answers, "What broad responsibility does it have?" The answer is
  Practitioner, Intelligence, or Solution.
- Profile answers, "Which reusable versioned behavior preset does this Loop
  use?"
- Category answers, "How is this work classified for search, organization, or
  reporting?" A category does not create a class or runtime.
- Mode answers, "How is this Loop allowed to resolve its work?"
- Step profile answers, "Which ordered steps can it run?"
- Settings answer, "Which contracts, budgets, permissions, provider routes,
  thinking power, and conditions apply?"
- Loop and exit conditions answer, "When may this Loop continue, and exactly
  when does it finish?"
- Graph relationships answer, "Was this Loop starting, spawned, queried,
  retrieved, or connected from another Loop?"

Show the role profile branches when the document discusses role-specific
behavior:

```text
Loop role profiles
├── Practitioner
│   ├── reference nine-step
│   ├── compact five-step
│   ├── research
│   ├── solver
│   ├── verifier
│   ├── code execution
│   └── self-improvement task
├── Intelligence
│   ├── cross-layer search and materialize
│   ├── Context Intelligence
│   │   └── serve, search, and frame
│   ├── Code Intelligence
│   │   └── resolve, invoke, and load
│   ├── Runtime History and Solution Intelligence
│   │   └── search, replay, and compare
│   └── User Feedback Intelligence
│       └── serve, scope, and interpret
└── Solution
    ├── atomic component
    ├── pipeline
    ├── router and fallback
    ├── ensemble
    └── validator
```

The Loop runtime defines three modes. A registered profile and an installed
executor may support a subset. The in-process Solution runner supports all
three modes when a compatible executor and exact model authority are supplied;
without them, it returns a typed unavailable-executor failure. Thinking power
and model routing apply only when a hybrid or non-deterministic Loop is
authorized to call a model. They are not additional run modes.

## Typed boundaries and encapsulation

- Prefer small immutable data classes and named configuration objects over
  long positional argument lists or unstructured keyword dictionaries.
- Give every Loop and Solution connection explicit typed input and output
  ports. Refuse incompatible connections before execution.
- Version public contracts, Loop profiles, serialized records, and adapter
  handshakes.
- Keep role, mode, step profile, effort budget, thinking power, provider, and
  effect permissions as separate fields.
- Separate discovery, eligibility, ranking, selection, materialization,
  execution, evaluation, acceptance, and promotion.
- Extend existing registries and event vocabularies. Do not create parallel
  stores, event systems, runtime classes, or sources of truth.

## Intelligence rules

The four persistent intelligence layers are:

1. Context Intelligence
2. Code Intelligence
3. Runtime History and Solution Intelligence
4. User Feedback Intelligence

Runtime Memory is separate, temporary, and scoped to one run. Source formats
such as Markdown, skills, repositories, packages, transcripts, and vectors do
not define new intelligence layers.

Owner direction, September 21, 2026: intelligence material is also organized
by family, which names what the material is built to follow. A family is not
a layer, and a layer is not a family; an item's family is derived from the
layer that holds its body, so the two axes cannot disagree.

```text
Intelligence families
├── Loop-native intelligence
│   ├── built for the Loop runtime
│   └── bodies live in the four persistent layers
├── Harness intelligence
│   ├── any file a standard harness picks up from its working directory
│   │   or its step configuration: instruction files such as AGENTS.md
│   │   and CLAUDE.md, skills with their scripts, references and assets,
│   │   tools and reusable code, subagent and command definitions, hooks,
│   │   plugin declarations and protocol server configurations
│   ├── for harnesses such as Codex, OpenCode, Claude Code and Pi
│   └── bodies keep their own identity in the harness_local source layer,
│       never a second copy of a body a Loop-native layer owns
└── Open Knowledge Format intelligence
    ├── generalized knowledge in open formats
    ├── shaped by no harness and no runtime
    └── classified into a persistent layer by meaning
```

The owner, September 22, 2026: "when we say harness intelligence, we mean
any type of file that can be placed into a harness working directory and
pickedup by the harness, not just MD files, it can also be tools, skills,
agents.md, codex.md, etc". A served item is therefore a package of one or
more files of any type a harness reads, each file with its own digest and
its own place in the step's working directory or configuration. Today the
served items are single Markdown files; multi-file packages and their
placement are roadmap work (S-6.62 and S-6.44).

The private beta serves harness intelligence first: the drop-in files a
customer's existing harness can use immediately. Loop-native and Open
Knowledge Format material remain part of the library and are served through
the same contracts.

Searching, selecting, materializing, framing, invoking, replaying, and
interpreting intelligence are Loop operations. Search returns small typed
references. Load a large body only after selection and permission checks.

Imported and self-generated intelligence remains candidate-only until an
independent process approves it. Never infer promotion from retrieval,
execution, a good score, or model confidence.

Code Intelligence must include an immutable source identity, provenance,
license state, version, dependency information, typed contract, effects,
tests, independent verification, and a digest before it is active.

## Managed notes and records

For a host-configured managed note or report collection, use
`loop-engine records` or `RecordOperationService`. Do not directly rewrite its
database rows, current-reference metadata, immutable revision artifacts, or a
future generated view. Preserve schema, namespace, expected revision, and exact
write approval. Unknown commits are not successes.

Ordinary source-code, schema, test, and hand-authored documentation edits remain
permitted within the task. This does not migrate Run History or historical
reports. Reuse the existing catalog/artifact contracts rather than creating a
parallel store. See `docs/guides/queryable-records-and-storage.md` and
`examples/24_managed_records/` for the current bounded tool.

## Models and providers

- Use real configured providers for provider integration and performance
  claims. A stub or injected transport may test a local contract, but it does
  not prove provider integration or model quality.
- Never silently replace a failed model call with canned or synthetic output.
- Resolve output capacity from a source-backed record for the exact provider
  and model. Without an explicit allocation, request that full capacity, not
  an invented smaller default. A reasoning Loop or user may supply a typed
  `ModelOutputAllocation` within the known capacity, bound to the route and
  decision evidence. Capacity, selected allowance, and total-run authority
  are separate. Unknown capacity requires an explicit unknown result; do not
  turn a total budget or semantic size estimate into a provider limit.
- Keep retry, same-provider fallback, cross-provider failover, formatting
  repair, evaluator-triggered repair, and task replanning distinct.
- Do not enable failover unless the run contract explicitly permits it.
- Preserve provider-reported token usage. Missing usage and cost remain
  unknown, not zero.
- Never write API keys, authorization headers, private prompts, or raw secrets
  to source files, events, reports, or exported traces.

## Effects, workspaces, and external tools

- Discovery must be effect-free.
- File writes, shell commands, network access, model calls, spending, and
  external mutations require explicit typed authority.
- Bind approvals to the exact requested effect. A changed effect needs a new
  decision.
- Use path-confined workspaces. Refuse path traversal, symlink escape, and
  unsafe overwrite.
- Run untrusted code in a declared sandbox with bounded resources and network
  policy.
- MCP tools, skills, providers, and external harnesses are adapters used by
  Loops. They are not executable graph vertices or new runtime types.
- Do not replay a committed external effect silently.

## Evidence and benchmarks

State observed, inferred, assumed, missing, and disputed facts separately.
Preserve failures and excluded attempts with the same prominence as successes.

A full-system Loop Engine benchmark requires:

```text
frozen real task population
  -> Starting Practitioner
  -> reviewed Context and executable Code Intelligence
  -> bounded Spawned Loops
  -> candidate comparison and verification
  -> compiled and executed Solution Canvas
  -> independent evaluator
  -> verified Run History, playback, and report
```

A component test, provider probe, deterministic replay, or partial path is not
a full-system benchmark. Report the exact denominator, selection rule, metric
direction, evaluator, failures, physical model calls, token-accounting
completeness, elapsed time, cost state, artifacts, and limitations.

For the current first benchmark campaign, selected solutioning runs are
non-deterministic. Deterministic Spawned Loops may retrieve, execute, validate,
and grade. Do not turn that campaign choice into a universal product rule.

Published results from another harness may be cited as external evidence only
with exact task population, model, harness version, evaluator, source, and
limitations. Do not imply a fair head-to-head comparison when those controls
differ.

## Public writing

Follow `humanizer-context.md`.

- The owner-facing marketing website uses Baltor and plain words such as
  task, each step, tools, model, information and results. Do not display Loop,
  Loop node, Loop Engine, runtime classification or role profiles on the
  homepage, How it works or their shared footer. Keep exact runtime terms and
  complete behavioral explanations in technical documentation and GitHub.
  This presentation rule does not rename classes, contracts or the repository.
- Do not use shorthand or introduce abbreviated aliases in explanations,
  documentation, prompts, or handoffs. Repeat the full descriptive term even
  after defining it. Preserve exact existing code identifiers and contract
  fields rather than renaming them through prose.
- Preserve the full phrase "discrete cognitive or act step Loop node" and its
  complete behavioral explanation. Do not shorten the phrase, remove "node,"
  substitute an acronym, or replace the explanation with a label. Read
  [the complete explanation and session handoff](docs/context/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-HANDOFF-2026-09-12.md).
  This describes an executable graph vertex implemented by the canonical
  `Loop`; it does not introduce a runtime class, role, or mode. Exact existing
  code identifiers remain unchanged.
- Preserve the complete initial configuration and ordered fallback priorities
  for each dimension in
  [the configuration dimension requirement](docs/architecture/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md).
  Read it before changing configuration, selection, recovery, or experiment
  coverage. Do not reduce the requirement to harness and model choice or
  mistake a documented requirement for implemented and qualified behavior.
  The recorded dimensions are a required baseline, not an exhaustive list or
  a maximum. Actively identify additional dimensions, refinements, and
  interactions. Map each proposal to an existing owning boundary, state its
  initial and fallback choices, and define a discriminating test. Keep
  proposals distinct from approved contracts and qualified implementations.
- Follow the [flexible cognitive and action composition direction](docs/architecture/FLEXIBLE-COGNITIVE-AND-ACTION-COMPOSITION.md)
  and [configuration grid search guide](docs/guides/configuration-grid-search-and-optimization.md)
  when extending behavior or designing comparisons. Support additional steps,
  prompts, questions, intelligence, actions, and resource combinations as well
  as compact procedures. Do not make minimal step count, prompt count, context,
  or model use the universal objective. Preserve supported alternatives and
  test both additions and removals. Artificial general intelligence is a
  research ambition, not a new runtime, role, mode, or achieved capability claim.
- Consider [layered harness wrappers and native control](docs/architecture/LAYERED-HARNESS-WRAPPERS-AND-NATIVE-CONTROL.md)
  as independent configuration dimensions. Wrapper depth and order need not be
  fixed. Resolve ownership of each native control, initial choices, and
  fallback priorities explicitly. Wrappers remain internal mechanics unless
  their work needs a separately governed canonical Loop. Native controls
  never grant broader authority or replace independent task acceptance.
  An outer Loop Engine Loop may govern a native harness's inner loop. Keep
  cumulative authority, retry ownership, cancellation, and independent
  acceptance explicit across both. Read `ASTRA.md` for the advisory criteria.
- Use plain English suitable for a reader using English as a second language.
- Start at the highest level and move toward details.
- Use direct statements, useful examples, and ordinary names.
- Avoid hype, AI slang, em dashes, en dashes, decorative slogans, and vague
  evidence metaphors.
- In public documents, prefer report, record, log, contract, event history, or
  evidence when that word is accurate.
- Keep current behavior separate from planned behavior.
- Do not publish benchmark or provider claims that exceed saved evidence.
- Marketing language and factual claims are different. Evaluative and
  aspirational words are free: a reader takes them as enthusiasm, not as a
  measurement. A number, a comparison to a named product, the words
  guaranteed or always applied to an outcome, an invented customer, or a
  capability the product lacks are statements of fact and need evidence.
  The [product style guide](docs/guides/product-style-guide.md) holds the
  test to apply.

## Semantic integration from Taedri

Port an idea from `/home/username/taedri.dev` only when it fills a verified
Loop Engine gap.

For each proposed port:

1. State the invariant in plain language.
2. Map it to an existing Loop Engine component and public term.
3. Check that no equivalent contract already exists.
4. Implement the smallest typed extension at the authoritative boundary.
5. Add positive, negative, ambiguous, adversarial, and unrelated tests when
   the risk warrants them.
6. Record provenance and the exact source revision used for design input.
7. Verify the integrated behavior through Loop Engine, not through a copied
   Taedri test harness.

Do not import Taedri-specific authority levels, campaign paths, business
claims, internal identifiers, or legacy terminology merely because they exist.
The reference-source map is in `docs/context/REFERENCE-SOURCES.md`.

## Persistent general solving

The owner's September 14 direction is recorded as proposed invariants in the
[Constitution](docs/architecture/CONSTITUTION.md#proposed-invariants-from-owner-direction)
and designed in the
[persistent general solving decision record](docs/architecture/ADR-PERSISTENT-GENERAL-SOLVING-AND-CONTRACT-FAILURE-REVIEW.md).
Apply it to engine behavior and to your own development work:

- Build general mechanisms. Do not add control flow, prompts, or checks
  written for one task, dataset, or benchmark.
- Persist within declared authority. Turn a failure into a typed next action.
  End only for a verified result, exhausted declared authority, a question
  that only the owner can answer, a cancellation, or a provider outage
  recorded for resumption, and record which one.
- When a check fails, first decide whether the work, the check, or the
  environment is wrong, and record why. Do not weaken a check to make it
  pass. A revised check must still reject a known-wrong answer.
- Never let a review waive a permission, secret, network, spending, sandbox,
  or external effect contract.
- Treat a tool written during a run as a candidate until a different process
  qualifies it.
- Never end work on a fixed attempt count. When the same failure repeats,
  change the approach: quote the failure, narrow the request to the failing
  part, try another registered method, or carry the best result forward as
  provisional with its findings recorded.
- Work like a person with one project folder. The proposed task working
  folder gathers supplied files, unpacked archives, downloads, generated
  work, and outputs, persists across attempts, and is shared with Spawned
  Loops through scoped views. Its first parts are implemented: supplied
  archives are unpacked into a materials folder that the source inventory
  walks, supplied binary files can be selected for a project's inputs, and
  new task database campaign spaces supply every attachment as a source
  file. Downloads kept as files and scoped views for Spawned Loops are not
  implemented yet.
- Run live experiments only under explicit owner authority. Record every
  trial, including failures and outages, keep runners waiting through a
  provider outage within a declared wait, and stop before an allowance is
  drained.
- Before committing, run the continuous integration commands on an export of
  the exact tree, lint the full documentation scope, and confirm with mutants
  that each new check fails when its behavior is removed.

## Verification and completion

Run the smallest relevant check first, then the owning component checks,
self-test, conformance, clean installation, examples, and browser or playback
checks when the claim depends on them.

Do not report completion from intent, file presence, narrow tests, or an
unverified diagram. Completion requires current evidence for every requested
behavior and no known required work left.
