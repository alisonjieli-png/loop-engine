# Baltor delivery and business plan

Kind: current execution order. Updated September 30, 2026. The
[roadmap](roadmap.yaml) owns task status, the [north star](../architecture/NORTH-STAR.md)
owns product direction, and [AGENTS.md](../../AGENTS.md#commit-push-and-release-authority)
owns authority. This page orders that work and states what each stage must prove.

## Product and revenue

Baltor helps a person's chosen harness complete useful creative and technical
work with relevant knowledge, reusable implementations and checks. Customers
should be able to keep the result, revise it and use it again. The library
includes executable programs, Python distributions, binaries, container
images and recipes, workflows, reference data, skills, assets and editable
projects. An installation method or programming language is a searchable
attribute, not a separate product.

Keep the targets of more than one million distinct served files, more than
one million useful packages, and $100,000 in monthly recurring revenue.
They are different measures. A package needs a reusable job; repeated files
and parameter permutations do not establish additional capabilities. Revenue
requires paying subscriptions, not free accounts, model calls or downloads.

Sell the existing Baltor Pro subscription through Baltor's website. Position
the offer around complete work: an editable game scene, a repaired animation,
a reusable data operation, or a production recipe that survives revision.
Measure activation, repeat use, retention, support effort and delivery cost.
Do not sell the planned higher tiers or managed execution before their
features work. Existing pricing and infrastructure allowances stay governed
by [owner decisions](../architecture/OWNER-DECISIONS.md) and AGENTS.md.

The first customer paths are Engineers, Designers and AI Agents. Each needs a
specific example, a supported setup route, the exact downloadable material and
a useful first result. A newcomer should not need to understand the internal
runtime or own a machine capable of running a large model.

## Execution choices and Blender setup

Model inference, harness execution and rendering have different resource
requirements. A small computer can run a harness that calls a cloud model;
that does not establish that it can render a large 3D scene. Offer profiles
according to measured requirements:

| Profile | What it provides | Work still required |
| --- | --- | --- |
| Existing desktop tools | Detect the installed harness, Blender or game engine and connect a compatible adapter | Version, operation, permission and small-scene checks for each supported combination |
| Guided installation | A pinned official installation recipe, dependencies and a verification command | Supported operating-system instructions, restart detection and recovery after an interrupted install |
| Downloadable worker | OpenCode and the Baltor text-response harness in a container | Real task comparisons and native tool profiles beyond the installed process checks |
| Browser | Play, inspect and revise supported Three.js scenes without a local model | Device performance, export, reload, mobile input and reduced-effects checks |
| Headless render container | A pinned Blender runtime and repeatable batch rendering | Image build, CPU/GPU profiles, mounts, resource limits, cancellation and clean reopen |
| Customer-controlled remote worker | The customer's existing machine or cloud endpoint performs permitted work | Pairing, identity, scoped credentials, reconnection and result delivery |
| Baltor-managed execution | An eventual option for customers who need hosted compute | Demand and cost measurement, isolation, accounting, quotas and an explicit release; unavailable today |

Start by detecting an existing installation. Offer a native install for
interactive Blender work and a container for repeatable background rendering.
Do not require a new container for every render frame or every small step.
Container choice, harness process lifetime and model access remain separate.
The setup package should contain the capability description, supported versions,
official download or image identity, prerequisites, installation procedure,
first working example, expected output and repair instructions.

## ChatGPT and Codex distribution

Individual developers are eligible: complete individual verification to publish
under your name, or business verification for a company name. A Platform
organization/project and submission access are needed; this is not an
incorporation requirement for individual submission. The current flow uploads
a plugin ZIP, resolves scans, submits for review and publishes after approval.
Include the MCP connection in the initial package. See
[OpenAI's submission instructions](https://developers.openai.com/plugins/deploy/submission),
checked September 30, 2026. The owner's actual account eligibility and verified
publisher identity have not been inspected.

Build a plugin around the same catalogue and account entitlement. Its first
tools should search the library, inspect a component and retrieve selected
material. Keep internal research, private session history and staff operations
outside that customer interface. Plugin review and published availability
are separate from an MCP server answering a local test.

Current OpenAI rules permit existing paid accounts to access included features
through a plugin. They prohibit digital subscription sales and upgrade
promotion inside the plugin, including links that initiate checkout. Baltor's
website remains the subscription sales channel. The plugin can serve existing
subscribers; it is not a direct marketplace subscription sale or a promised
revenue-sharing programme. See the
[plugin guidelines](https://developers.openai.com/plugins/plugin-guidelines).
Use a task-focused plugin interface. Embedding the existing website's pricing
and checkout navigation would carry those sales actions into the plugin.

Optional ChatGPT plan usage has its own eligibility, authorization and
accounting. Keep it distinct from Baltor's subscription and from permission to
execute a task. The
[sign-in guidance](https://developers.openai.com/siwc/ui-ux-guidelines)
requires that distinction. The current live Baltor capabilities do not advertise
an installed OAuth authorization server. Implement and test the required
sign-in path before submitting an authenticated plugin.

Use an established identity provider for OAuth 2.1, with resource and issuer
metadata, authorization-code/PKCE, scoped tokens and per-request validation.
Website sign-in and a manually copied client key do not establish this flow.
See [authentication requirements](https://developers.openai.com/plugins/build/auth).

The first submission should expose Baltor's own qualified search, inspection
and download operations, with optional scoped setup skills. Keep local Blender,
arbitrary shell access, internal research and future hosted rendering out of
its initial promise. A downloadable recipe is not remote execution. Choose no
custom UI initially unless an artifact preview adds a tested customer benefit.

Prepare five positive and three negative review cases, a recorded demonstration,
production HTTPS endpoint, domain verification, precise tool annotations and
reviewer credentials. Make the review account work without an email/MFA step;
do not weaken normal customer signup to achieve that. The
[submission validation requirements](https://developers.openai.com/plugins/deploy/submission-errors)
also require accessible website, support, privacy and terms URLs. Submission
and approval are not yet established for Baltor.

Review the existing approved legal pages against the implemented plugin flow.
Explain the data received from OpenAI, its use, recipients, retention, deletion
and user controls; ordinary request metadata is still part of that review.
Do not collect API keys through chat or tool arguments. These are requirements
of the [plugin guidelines](https://developers.openai.com/plugins/plugin-guidelines),
not a claim that today's Baltor notice already covers new media or remote
execution. Draft any required changes for owner approval before publishing
them. Keep the publisher's verified identity consistent with the operator and
support information; do not invent a company or claim business verification.

Engineering owns implementation, tests, the domain challenge and submission
package. The owner completes personal identity verification and any new legal
approval or account agreement that requires them. No company formation, new
purchase, legal acceptance or public submission occurred in this review.

## Delivery order

Take the next unfinished stage, scope one usable release, implement it, test
positive and known-wrong cases, commit and push to main, wait for that revision's
continuous integration, deploy through the guarded workflow, check the live
hostnames and record the release. Then move to the next stage. Keep each
release small enough that its result and rollback are clear.

Finish the acceptance gate before presenting an outcome as available. Record
correctness, elapsed time, resource use and remaining limits on the exact
candidate. Independent source research can continue within its allowance,
but it must not delay a ready customer fix or start an unreviewed migration.

1. **Reconcile and preserve the current work.** Account for inherited changes,
   source identities, failed checks and prior-session instructions. Correct
   stale startup links and implementation claims. Keep a coverage record for
   the conversation audit; parsing a transcript does not mean its entire
   contents received semantic review. Commit reviewed work without losing
   unrelated work.
2. **Prove the first customer journey.** Start from a new address, confirm the
   email, choose a password, sign in, create a scoped personal key, connect a
   supported harness, search, download, verify bytes and complete a small task.
   Test on desktop and a narrow layout. Record every manual step and failure.
   The September 30 sign-up, sign-in, scoped-key, search, complete download and
   byte verification passed. Automatic activation in a native harness and a
   useful accepted task remain separate gates.
   Include setup help and a clear support handoff. Recover and review the
   existing support implementation before buying or rebuilding a chat service.
3. **Measure whether the material helps.** Freeze the same task, model, harness,
   input files and acceptance checks for runs with and without Baltor. Include
   setup time, retrieval, physical calls, provider-reported usage, retries,
   human intervention and accepted outputs. Keep failures and the no-extra-material
   baseline. Start with the demanding customer-task matrix below, not another
   short text-cleanup example. A single useful example is not a general savings claim.
4. **Finish complete package delivery.** Preserve scripts, resources, contracts
   and dependencies for npm/skills packages and other native formats. Support
   pinned official install recipes where they are more useful than copying an
   entire runtime. Qualify binary size, interrupted transfers and clean installs.
   These are S-6.40, S-6.81 and S-6.215 delivery work, not merely catalogue entries.
5. **Ship the first creative proof.** Finish the browser fantasy arena, inspect
   its rig and animation clips, export an editable scene, make a meaningful
   revision and reopen it in a clean supported environment. Exercise movement,
   attacks, enemies, collisions, failure and restart. Qualify Blender import and
   rendering separately. Package reusable parts after independent admission.
6. **Make retrieval diagnosable, correct and faster.** First join request,
   catalogue, engine, selected file version, download and outcome records.
   Reproduce slow, irrelevant, stale, wrong-format and missing-result cases.
   Compare relevance, permissions and cold/warm latency on a frozen population.
   Qualify caching and a selectable Rust engine independently; switch only
   when the comparison justifies it. This is S-6.32 and S-6.51. Hosted search
   currently uses SQLite FTS5 and deterministic hash vectors, not Rust or a
   learned semantic embedding model.
7. **Prove reference video to editable variation.** Accept a supported video
   upload or permitted URL, explain its shots and effects with timestamps,
   retrieve the needed tools and files, and produce an executable harness
   brief. Recreate one bounded example, revise it and reopen the editable
   project. Separate observed effects from guesses about the original tools.
   This extends S-6.116 and S-6.117; its acceptance gate is below. It is not a
   current customer capability.
8. **Activate recurring source-to-component production.** Use the existing
   knowledge radar, managed records and scheduler. Run declared API/feed reads,
   deduplicate leads, investigate the source, choose reuse or original work,
   prepare complete candidates, independently review them and publish accepted
   additions. Pin scheduled code to a reviewed revision. Report API quota,
   source coverage, failures and the count reaching each stage. This is S-6.214.
9. **Expand orchestration and execution choices.** A task can contain several
   steps, each executed by a fresh or qualified retained harness. Add observed
   session status, concurrency allocation, cancellation, restart, artifact
   handoff and independent acceptance through existing runtime and engine
   contracts. A tmux dashboard is an operating interface, not another runtime.
   Then qualify remote execution for customers who need it. This extends
   S-6.30 and S-6.42.
10. **Launch the supported acquisition paths.** Publish task-specific pages,
   reusable demos, setup guides and evidence-backed comparisons. Prepare the
   ChatGPT/Codex plugin for review with the same account access. Use the owner's
   newsletter and approved marketing work for acquisition; engineering does
   not purchase advertising. Measure first use and retention before adding
   paid features.
11. **Scale the parts that show value.** Expand distinct admitted capabilities,
    publication throughput and serving capacity toward S-6.215. Use observed
    customer failures, repeated tasks and successful revisions to choose the
    next components. Keep the million-file, package and revenue measures
    visible without treating one as proof of another.

## Customer-task comparison programme

The September 30 owner request adds eight task families. Use a real customer
account, the shipped setup instructions, a pinned native harness and the same
Ollama Cloud model route in both arms. The with-Baltor arm must discover and
download from the live service as a customer would. Hand-pasted material and
private unapproved candidates are separately labelled experiments, not this
customer proof. If search finds nothing suitable, record abstention and let
the harness continue within its ordinary budget.

| Family | Task to freeze | Acceptance beyond a plausible answer |
| --- | --- | --- |
| Pipeline building | Join several input formats into an incremental, restartable data pipeline with schema drift and duplicate arrivals | Runnable project, correct outputs, idempotent rerun, recovery after an injected interruption and clean installation |
| Data quality | Find and handle missing values, invalid ranges, contradictory records and malformed input without silently discarding rows | Row-level issue report, explicit quarantine, conservation checks and held-out defect recall with false positives |
| Data standardization | Normalize mixed dates, units, encodings, names and addresses while retaining ambiguous values | Exact transformation provenance, locale/unit correctness, reversibility where promised and no guessed correction of valid data |
| Entity matching | Match records with misspellings, sparse identifiers, shared addresses and near-identical people or companies | Held-out pair precision/recall, cluster consistency, explicit uncertain matches and no unsupported merge |
| 3D generation | Build a scene from a multi-part brief with editable geometry, materials, camera, animation and a later structural change | Native artifact, rendered views, declared scene constraints, successful revision and clean reopen; a text description is not completion |
| Parametric generation | Produce a reusable constrained model or scene generator, then change dimensions and seed | Valid outputs across held-out parameters, reproducibility, geometric checks and honest rejection of impossible combinations |
| Advanced debugging | Repair a seeded cross-module failure in an unfamiliar codebase with misleading symptoms | Root-cause explanation, minimal patch, failing-before/passing-after regression, held-out tests and no unrelated damage |
| Kubernetes | Diagnose and repair a small deployment with configuration, readiness, resource or networking defects | Valid manifests, declared security/resource constraints, rollout and recovery in an isolated local test cluster; offline validation alone is labelled partial |

Implement one representative data pipeline first, including quality,
standardization and matching stages, then a separate creative revision task.
Release their replayable evidence before expanding the matrix. Kubernetes
tests must not touch production clusters; no cloud cluster purchase is implied.
These tasks extend D-06, D-09 and S-6.173. Keep the outside-population study
under S-6.185 as a separate check against overfitting to Baltor's own examples.

For each case, commit the inputs, declared tools, task specification, treatment,
budgets, seeds, scoring rules and known-wrong controls before counted calls.
Keep hidden acceptance cases outside the harness's workspace. Use the same
environment, model settings and capability permissions; the only intended
difference is Baltor access. Keep equal total budgets and record Baltor's
retrieval/setup overhead inside its arm. Counterbalance order, repeat trials
and distinguish cold setup from reuse. Choose tasks before seeing results;
do not keep only the cases Baltor wins.

The side-by-side view should show both actual artifacts or renders, acceptance
results, failed attempts, elapsed time, physical calls, input/output/cache
tokens, tool activity, retries and human repairs. Report monetary cost only
when it is established. Include download/install time, exact component versions,
missing material and wrong-file incidents. Lower tokens on unfinished work are
not savings. Freeze a decision rule and enough repetitions for any statistical
claim; a small pilot is a diagnostic, not a percentage-improvement headline.

## Reference-video sales demo

The first promise is narrow: **show a supported reference, get an explained
production plan, then make an editable variation**. Do not promise that Baltor
can recover the exact source project, identify every original tool or reproduce
any video. The browser arena and Blender export are building blocks, not proof
of video understanding or automatic recreation.

```text
Upload or permitted URL
  → validate and inspect media → timestamped shot/effect breakdown
  → retrieve qualified components → missing-capability and cost report
  → choose execution profile → harness steps and prompts
  → render → compare → revise → export and clean reopen
```

Deliver this as successive checked increments under S-6.116 and S-6.117:

1. **Intake and inspection.** Begin with one short, owner-supplied or
   rights-cleared clip. Record its digest, duration, codecs, resolution, frame
   rate, audio and permitted use. Bound file size, decode time and work. Reject
   unsupported or corrupt files clearly. URL intake must block private-network
   targets, recheck redirects and DNS resolution, and respect source access
   restrictions; an upload remains available when a platform cannot be read.
2. **Explain the reference.** Produce timestamped shots, camera and object
   motion, transitions, typography, composition, lighting, audio cues and
   visible effects. Label observations, uncertain interpretations and unknowns.
   Recognizing an effect does not identify the software that originally made it.
3. **Make the plan executable.** Map each operation to an existing typed
   component, exact version and engine, or name the missing capability. Include
   required files, assets, MCP/tools, dependencies, setup checks, prompts,
   resource estimates and acceptance checks. Select browser, native, container
   or remote execution; do not silently buy rendering or model access.
4. **Render and vary one example.** Start with a short motion-graphics reference
   with known source, before arbitrary live-action or complex character motion.
   Keep a shot specification and editable project. Change text, palette, timing
   and aspect ratio while preserving approved content. Pose extraction and
   retargeting are a separate qualified extension, not an assumed video feature.
5. **Accept and demonstrate.** Save the reference, breakdown, retrieved versions,
   generated instructions, rendered result, meaningful revision and clean-reopen
   evidence. Measure complete elapsed time, model usage, manual repairs and
   failures. Test a clip requiring an unavailable tool: it must report the gap,
   not invent a matching file or claim completion. Publish only cleared media.

The marketing demonstration should let a visitor inspect what Baltor understood,
what it reused and what changed. Show a successful bounded example and its
limits before offering general video recreation as a paid feature.

## Retrieval quality, tracing and speed

Use existing service observability and usage records, not a parallel logging
system. A correlation identity should connect search, filters, catalogue release,
selected engine and version, cache status, ranked item versions and digests,
fetch, installation and the customer's reported outcome. Capture stage timings
for authorization, candidate generation, ranking, serialization and transfer;
separate client network time from server work. Keep raw prompts, media, response
bodies, credentials and account email out of ordinary telemetry. Diagnostic
content needs a separate consent and retention path.

Freeze judged queries for exact identity, task phrasing, synonyms, file type,
dependencies, no suitable match, restricted access and withdrawn versions.
Measure top-k relevance, accepted no-answer decisions, wrong-file rate,
compatibility, complete delivery, p50/p95/p99 latency, memory and index refresh
time. State the sample size: six serial requests cannot establish a reliable
tail-latency target or production capacity. Keep tuning cases apart from held-out
cases. Every confirmed failure gets a small replayable regression fixture with
the expected outcome and the affected release.

Try low-cost changes first: query work, bounded candidate sets, reuse of an
immutable index, compression and cache placement. Compare Python and Rust
engines behind the same typed edge on identical inputs, machine limits and
catalogue bytes. A faster engine must preserve authorization, withdrawals,
relevance and exact file delivery; a warm-cache win must include misses,
invalidation and concurrent callers. Record the rollout and rollback decision.

## Capability families to develop

These are requested families and their first acceptance targets. Their
presence here does not mean all the tooling is implemented or admitted.

| Family | Reusable components | First complete proof |
| --- | --- | --- |
| Fantasy and science-fiction games | Characters, goblins, equipment, enemies, controllers, encounters, terrain, lighting, collision and input checks | A playable browser scene, revision, export and clean reopen |
| Rigging and motion | Video pose extraction, confidence/occlusion records, skeleton mapping, rest-pose conversion, retargeting, contact cleanup and animation export | A supplied dance clip transferred onto two different rigs, with visible checks for foot sliding and timing |
| 3D modeling and printing | Parametric CAD, mesh repair, units, wall thickness, orientation, supports, slicer profiles and toolpath preview | A dimensioned model with checked geometry and a reproducible slice for a declared machine/material profile; no unrequested printer dispatch |
| Social video and 2D graphics | Explainable layouts, Ken Burns motion, comparison panels, listicles, quizzes, questionnaires, caption timing, audio mapping and render checks | A source-linked video and an editable variant with different text, timing and aspect ratio |
| Playable short formats | Skill-based arcade challenges, obstacle courses, location guesses, timers, scoring and immediate restart | A game with clear rules, tested controls and a fair, reproducible failure condition |
| Software and reference work | Executables, Python packages, API clients, maintained lists, algorithms, data schemas, n8n workflows and installation recipes | Retrieval, dependency resolution and an independently checked useful operation |
| Multi-session work | Step briefings, native harness adapters, shared artifact references, schedules, resource allocation and review | Several concurrent steps with cancellation and restart, no context or credential leakage, and an accepted combined result |

Tripo's [prompt library](https://www.tripo3d.ai/3d-prompts/categories/games)
is a source of workflow ideas. Record whether a source includes a playable
result, editable project, actual input prompt, reusable code or only a
showcase claim. The requested `nicos.gameart` identity still needs a verified
source link. Study presentation and interaction without copying assets or
claiming their results as Baltor measurements.

## More useful file forms and source coverage

Expand the package mix through S-6.214 and S-6.215. A harness should be able to
download a prompt template, a decision guide or a dataset as readily as code.
Use the current compiler and package roles; these files do not create new
runtime types or independent model calls.

| Material | What the complete package should contain |
| --- | --- |
| Prompts and prompt templates | Task and use conditions, typed parameters, model-independent instructions, versioned model-specific notes when needed, example inputs, expected output schema and failure cases |
| Best-practice and decision guides | Scope, dated primary sources, rationale, trade-offs, contraindications, alternatives and a refresh condition; distinguish advice from measured results |
| Task and harness templates | Step briefs, dependency order, selected-material references, declared effects, budgets, checkpoints, acceptance checks and recovery instructions |
| Reference and example files | Schemas, small datasets, mappings, taxonomies, fixtures, good and known-wrong outputs, source period, units, rights and quality checks |
| Executable and creative material | Functions, programs, workflows, installation recipes, shaders, scene generators, rigs, clips, CAD, renderer inputs and editable native projects with dependencies |

Every candidate records its original author or source URL, immutable revision
or observation date, licence/reuse permission, intended use, supporting files,
checks performed and known limits. A link or a post suggesting an idea does
not grant copying rights. Write original guidance from verified sources when
copying is not permitted; do not turn private session transcripts into public
templates. Keep common implementations shared instead of publishing trivial
prompt rewordings as distinct capabilities.

The evidence trail is: owner request or research lead, dated source record,
reuse decision, candidate, independent admission, published package/version,
customer use and observed result. Keep it in the existing managed records and
registries. The conversation-audit record explicitly names its unreviewed
portions. New ideas enter the owning roadmap step rather than another parallel
to-do list.

## New model releases, including Gemini 4

Use the existing `watch_model_releases.py` and knowledge-radar invalidation
path. Its current watched listings include models.dev, Hugging Face and the
LiteLLM retirement map; it does not establish complete coverage of vendor
announcements. Add qualified primary release-note bindings where that gap
matters, with a permitted read method, quota, validator and failed-read state.
Do not report a timer as active without checking its pinned code and run record.

On September 30, Google's [July 21 announcement](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-3-6-flash-3-5-flash-lite-3-5-flash-cyber/)
describes Gemini 4 as a pre-training effort. This review found no Gemini 4
entry in the [Gemini API release notes](https://ai.google.dev/gemini-api/docs/changelog).
That is a bounded source check, not a prediction of launch date or proof that
no private access exists. Gemini 4 and Gemma 4 are different model families;
the earlier Ollama trials used Gemma 4.

When a model becomes accessible, verify its exact identifier, route, supported
inputs, tool calls, structured output, context and output capacities, usage
accounting, prices and retention terms. Keep vendor claims separate from our
observed calls. Add or update the provider adapter behind the current typed
interface, then run the frozen customer-task comparisons and negative controls.
Publish the measured compatibility and decide whether to offer it, specialize
its prompts or change a declared preference. Preserve rollback and the prior
model's evidence. No speculative default switch, new paid account or extra
model purchase is authorized by a release announcement.

## Caching and retrieval costs

The September 30 live check observed `public, max-age=300` on the website's
JavaScript, an ETag on that asset, and `no-store` on the homepage and API
capabilities. The serving code also builds one index per catalogue view.
No Cloudflare KV response cache or Rust search migration was established by
this check.

First measure public asset delivery and repeated retrieval independently.
Cache public assets at the edge when their exact version and invalidation
behavior are qualified. Cache reusable ranking computation inside an immutable
catalogue view, then apply current account access and withdrawal checks before
returning results. A cache must not bypass download authorization or usage
accounting. A request for fresh results needs an explicit bypass.

Do not introduce a global cache of raw model responses or follow-up suggestions
under the assumption that hashing the prompt makes the content anonymous.
Predictable prompts can be guessed, and responses may repeat private input.
Any such future feature needs scoped ownership, retention, deletion and
privacy choices, plus keys bound to model, prompt version, material, settings
and relevant permissions. It is not part of the current hosted library.

Cloudflare KV has eventual consistency; updates can take 60 seconds or more
to appear elsewhere. It is unsuitable as the authority for immediate access
revocation, entitlements or withdrawals. See
[Cloudflare's consistency documentation](https://developers.cloudflare.com/kv/concepts/how-kv-works/)
and [cache behavior](https://developers.cloudflare.com/cache/concepts/default-cache-behavior/).
Cache eligibility and a faster Rust implementation solve different problems;
compare them against the same measured workload before changing the serving
engine or buying infrastructure.

## Source programme and housekeeping

The [community registry](../../tools/knowledge_radar/community-sources-v1.json)
contains the owner's design, game, modeling, graphics and video sources.
Begin with DesignAndAI, aigamedev, TopologyAI, comfyui, threejs,
proceduralgeneration and StableDiffusion, then rotate the remaining sources
within the provider's actual allowance. Community posting rules from supplied
research are leads to recheck before any post. Reading through an authorized
API does not grant redistribution rights or permission to post.

The RapidAPI Reddit34 reader has made observed requests to DesignAndAI and
aigamedev. The second read returned 25 posts and produced 20 source-linked
research work orders through the existing scheduler. These are leads, not
published components. Its key lives in the system keyring. Other supplied
RapidAPI services, including reddapi, reddit3 and Searx Search API, need their
exact endpoint contracts and account allowance checked before activation.

Housekeeping accompanies each release: reconcile dirty work and its owner,
update the current deployment record, regenerate indexes from their sources,
check links and diagrams against actual constructors and settings, preserve
failed attempts, and remove stale claims from customer copy. Do not delete
old worktrees or histories merely because they are old. Inspect their state
and preserve unreconciled work first.

Use [the writing context](../../humanizer-context.md) across setup, system
messages, source comments, prompts, documentation and marketing. Keep exact
contract names in technical material and use ordinary task language in the
customer journey.

The support worktree at `/home/username/.le-support-20260924`, revision
`0769ca5e`, contains an earlier help centre and chat implementation that is
absent from current main. It also has four modified files. Its changes are
preserved; they are not evidence of a deployed chat service. Review its account
boundaries, retention, model-draft controls and approved privacy wording before
integrating it. Show automated replies honestly and base any promised response
time on observed staff coverage.
