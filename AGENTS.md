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

Baltor gives each step of a customer's chosen harness the materials, methods,
tools, executable components and checks needed to complete useful work.
Creative production is now a first-class focus: editable motion, graphics,
parametric visuals, 3D scenes, audio and playable experiences. Technical
reference laboratories and reusable code stay in the same library.

The owner's September 29 direction keeps the target above one million distinct
served component files, with original implementations and native materials,
not just skills. A model should discover small contract cards, compose and
order qualified capabilities, and load source only when needed. Preserve
unchanged implementations instead of paying to generate them again. Every
executable graph vertex remains a Loop; passive files and frame operations do
not become separate model calls. The existing code-asset, solution-graph and
engine-slot contracts own this behavior.

Read [the current north star](docs/architecture/NORTH-STAR.md) before product,
architecture or prioritization decisions. It preserves earlier owner direction
and states the September 29 priorities. Read [owner decisions](docs/architecture/OWNER-DECISIONS.md)
for pricing, admission, library composition and historical rationale. Neither
file replaces the authority section below or the [roadmap](docs/roadmap/roadmap.yaml).

The next proof is one complete creative project that produces an attractive
result, survives a meaningful revision and reopens in a clean supported
environment. Candidate counts, format checks, downloads and native loading
are distinct from accepted work or measured benefit. Keep the no-extra-material
baseline eligible. Each functional component retains its fixed typed edge and
swappable engines; use existing code and qualified native tools first.

A discrete cognitive or act step Loop node retains the [complete behavioral
explanation](ASTRA.md#complete-behavioral-explanation). A renderer's frames or
scene objects are not additional Loop runtimes. Browser execution, an existing
harness, a paired computer and managed execution are separate profiles, with
separate identity, content access, inference funding and effect authority.

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
   Every functional component outside the fixed frame that the standard
   lists has one engine slot in
   [`engine_slots.yaml`](src/loop_engine/data/engine_slots.yaml). Each of its
   engines passes the slot's conformance kit alone, and components are also
   tested in groups and end to end. A project taken from GitHub or another
   source repository enters as an engine adapter pinned to its source
   revision and licence, runs in the container or sandbox that its trust
   requires, and gets a Baltor-native engine beside it that passes the same
   kit, or a recorded reason why its slot needs none; a host setting or an
   engine preference switches between them at run time without editing a
   caller.
   Before building, search existing projects, repositories, published designs
   and papers for something to use or adapt, and record what was found and
   why it was adopted, adapted or rejected. An engine is an adapter that a
   Loop uses, never a new runtime type. The
   [functional component standard](docs/architecture/FUNCTIONAL-COMPONENT-STANDARD.md)
   states each requirement once, with the check that enforces it. Its
   technical words have the meanings that
   [`terminology.yaml`](terminology.yaml) gives them, and quoted owner words
   keep the owner's meaning. The owner, September 21, 2026: "every
   functional unit should be wrapped so that we can replace the unit engine
   without impacting functional unit to unit edge communication". September
   22, 2026: engines "for each functional component so that the runtime can
   select the most efficient engine", and a search for "projects, repos,
   github, designs, or papers that we could use / leverage so we don't have
   to reinvent the wheel". September 23, 2026: "ways we can have functional
   components, that have multiple functional engines that are wrapped around
   a contract/edge/typed input output", "testing functional components
   individual, in groups", "contracting component functionality even if
   different engines operate the actual functional execution", "create a
   clear index and manage that to make sure discussions, nomeclature, and
   things are simple, non-conflicting, non-conflcated", "everytime we pull a
   project from github, we should containerize/wrap it as a functionality
   component then build our own variation and allow easy selection and swap
   out of functional engines that accomplish that task", and "a typed
   versioned component interface with selectable engines for all aspects of
   this project for maximum robustness, modularity, real time selection of
   preferences of engine".

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

The [owner decision table](docs/architecture/OWNER-DECISIONS.md) preserves the
dated decisions, reasons and current clarifications. Read it for intelligence
admission, pricing, composition and scope. It is linked here instead of
repeated in every harness's startup context.

## Detailed engineering guidance

The [engineering rules](docs/guides/repository-engineering-rules.md) preserve
the complete requirements previously held here. Read the relevant section
before changing its owning boundary.

## Pre-launch version policy

Keep versioned handshakes between independently deployed components. Refuse unsupported versions before effects. Preserve historical records without automatic legacy readers.
See [the complete rule](docs/guides/repository-engineering-rules.md#pre-launch-version-policy).

## One Loop runtime

Loop is the only executable graph vertex. Practitioner, Intelligence and Solution are roles; deterministic, hybrid and non-deterministic are modes. No concrete Node or Loop subclass is introduced. Low-level operations stay inside their owning Loop unless independent governance is required.
See [the complete rule](docs/guides/repository-engineering-rules.md#one-loop-runtime).

## Required architecture trees

Use the complete classification before specialized architecture branches. The detailed rules contain the full trees and precise terminology. Preserve the complete behavioral explanation in ASTRA.md.
See [the complete rule](docs/guides/repository-engineering-rules.md#required-architecture-trees).

## Typed boundaries and encapsulation

Keep typed, versioned requests, results and explicit failures at each edge. Separate discovery, selection, materialization, execution, evaluation, acceptance and promotion. Reuse existing registries and stores.
See [the complete rule](docs/guides/repository-engineering-rules.md#typed-boundaries-and-encapsulation).

## Intelligence rules

Retain the four persistent intelligence layers and separate temporary Runtime Memory. Harness, Loop-native and Open Knowledge Format families differ from layers. Any appropriate native file can be a component. Exact bytes, interpretation and use permissions remain separate.
See [the complete rule](docs/guides/repository-engineering-rules.md#intelligence-rules).

## Managed notes and records

Use loop-engine records or RecordOperationService for a managed collection. Preserve namespaces, versions, approval and immutable revisions. Ordinary source and documentation edits remain normal development work.
See [the complete rule](docs/guides/repository-engineering-rules.md#managed-notes-and-records).

## Models and providers

Real provider claims require observed calls and saved evidence. Never silently replace a failed call with synthetic output. Source-backed capacity, selected allocation, total authority and provider-reported usage are distinct. Secrets never enter reports or model context.
See [the complete rule](docs/guides/repository-engineering-rules.md#models-and-providers).

## Effects, workspaces, and external tools

Discovery is effect-free. File, shell, network, secret, model, spending and external effects require declared authority. Confine paths and sandbox untrusted code. Reconcile unknown external outcomes before retry. Content approval grants no effect.
See [the complete rule](docs/guides/repository-engineering-rules.md#effects-workspaces-and-external-tools).

## Evidence and benchmarks

Separate observed, inferred, assumed, missing and disputed facts. Report the complete attempt population, failures, exclusions, accounting and limits. Component checks are not full-system benchmarks; vendor demonstrations are not local qualification.
See [the complete rule](docs/guides/repository-engineering-rules.md#evidence-and-benchmarks).

## Public writing

Follow humanizer-context.md. Use Baltor and plain customer words on marketing pages. Preserve exact technical vocabulary and the complete behavioral explanation in technical documentation. Separate implemented and planned behavior. Read the dimension, flexible-composition and layered-wrapper requirements before changing those boundaries.
See [the complete rule](docs/guides/repository-engineering-rules.md#public-writing).
The [dimension requirement](docs/architecture/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md)
remains directly discoverable from every coding-agent entry route.

## Semantic integration from Taedri

Consult older or separate projects only for a verified gap, after reading REFERENCE-SOURCES.md. Map each invariant to an existing owner, preserve provenance and test integrated behavior. Do not import another authority system.
See [the complete rule](docs/guides/repository-engineering-rules.md#semantic-integration-from-taedri).

## Persistent general solving

Persist toward an accepted outcome within declared authority. Diagnose whether a failure belongs to the work, check or environment. Preserve useful provisional work and failed attempts. No task-specific universal runtime logic or review-based expansion of effect authority.
See [the complete rule](docs/guides/repository-engineering-rules.md#persistent-general-solving).

## Verification and completion

Use the smallest meaningful check, owning checks and required release gates on the exact candidate tree. Verify a changed guard with a known-wrong control. Use browser and native checks where needed. Report unfinished required work explicitly.
See [the complete rule](docs/guides/repository-engineering-rules.md#verification-and-completion).
