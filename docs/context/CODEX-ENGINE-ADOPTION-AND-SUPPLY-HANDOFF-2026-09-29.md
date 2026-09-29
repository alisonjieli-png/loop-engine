# Codex handoff: engine adoption research, the reviewer calibration repair, and component supply

Kind: dated handoff for the next session, September 29, 2026. Written for OpenAI Codex
picking up this work cold. It records what was done, what is running, what was measured, what
is still open, and the exact commands to continue. Nothing here adopts an engine, installs a
product, or grants a licence.

Read [AGENTS.md](../../AGENTS.md) first. It holds the commit, push, release and authority
rules that govern everything below. This document is a handoff, not an instruction hierarchy.

## 1. Read this first: the state in one screen

```text
Branch and revision
└── main, last pushed head 40b78a20, rebased over the concurrent directory commits
    4b8f1de8 (model directory) and fc00e417 (MCP directory)

Working tree, mine and uncommitted
├── M tools/component_qualification/sampled_review.py      the repair in section 3
├── M tools/test_component_qualification.py                the check for it
├── M src/loop_engine/core/service_runtime/catalogue_attributes.py   creative vocabulary
├── M tools/test_catalogue_attributes.py
└── ?? tools/test_reference_artifacts.py

Working tree, NOT mine, concurrent work, do not touch
├── M docs/context/START-HERE.md
└── ?? docs/context/COMPONENT-FACTORY-AND-LOCAL-COMPONENT-STORES-2026-09-29.md

New research records written this session
├── docs/research/EXTERNAL-SYSTEMS-2026-09-29.md
└── docs/research/GAME-AND-3D-ENGINES-2026-09-29.md

Running right now
└── the full sampled independent review over 10 generator batches with ollama.kimi-k2.6
    ledger  /home/username/.le-ci-tmp/qual/all-fast/ledger-kimi-full.jsonl
    result  /home/username/.le-ci-tmp/qual/all-fast/review-kimi-full.json
    log     /home/username/.le-ci-tmp/qual/all-fast/review-kimi-full.log

The live number, and why it has not moved
└── https://baltor.ai reports data-library-count 23,901
    61,523 components passed the fast deterministic qualification
    0 of them are admitted, because no reviewer installation had passed calibration
    section 3 explains the bug, the repair, and the fix
```

## 2. What the owner asked for, in order

These are the owner's own words from September 29, 2026, condensed without adding
interpretation. Every one is a live instruction, not a discussion topic.

1. Reference and research other systems like OpenHands, and consider whether the website
   should support cloud solutioning as a pay-as-you-go system with more advanced systems and
   custom processes that break large tasks into smaller tasks, where each task is a node and
   each node is a harness, and to explore the difference between doing that on the server and
   locally.
2. Compete with `https://www.revid.ai/claude-motion-graphics`.
3. Research all of it, along with all of the earlier prompts, and continue generating more
   qualified files that can be served, improving everything and learning from the research,
   the files, the adjustments, the systems and the tools, aligned with generating more value
   for customers, more functionality, and the north star, including
   `https://github.com/walkinglabs/learn-harness-engineering`.
4. Learn the AI-engineering discipline list: harness engineering rather than prompt
   engineering; context engineering rather than long prompts; prompt caching against semantic
   caching; KV cache management, eviction, reuse and memory pressure; prefill against decode
   latency; continuous batching, paged attention and throughput; speculative decoding against
   quantization against distillation; INT8, INT4, FP8, AWQ, GPTQ and when quantization hurts
   quality; structured output failures, schema validation, repair loops and fallback chains;
   function calling reliability, tool contracts, argument validation and idempotency; agent
   guardrails, loop budgets, tool budgets and termination; model routing, graceful fallback
   and degraded-mode UX; RAG chunking, embeddings, hybrid search, reranking and freshness;
   retrieval evals for recall, precision, grounding, attribution and citation quality; golden
   sets, regression, adversarial, model-as-judge and human evals; observability as a
   first-class discipline; cost attribution per feature, workflow, tenant and user journey;
   prompt injection defence, data leakage prevention and permission boundaries; multi-tenant
   isolation, cache safety and cross-user contamination; fine-tuning against in-context
   learning against retrieval against distillation and when each is the wrong tool; the
   latency, quality, cost and reliability trade across the inference stack; production
   failure modes including hallucinated tool calls, malformed JSON, stale retrieval, runaway
   agents and silent eval regressions; and shipping as reliable infrastructure rather than
   demos.
5. Ask why the website still shows only 23,901 packages, why it has not increased, and demand
   aggressive improvement with visible checkpoints and deployments so new components are
   visible on the public website.
6. Review the work on baltor.ai, popular skills, popular tools, popular harness plugins,
   Hermes, OpenClaw and similar, and generate a list of skills, plugins and harness components
   useful for any task, any job description and any title, ideating from 100 thousand to 10
   million artifacts.
7. Expand aggressively into creative: SVG, reference images, templates, OpenPose images,
   masks, 3D models, STL files, 3D files, autocode styles, all of which could be reference
   files a harness analyzes and understands, plus reference files for code-based traditional
   harness components. Also the technical side: deduplication, BigQuery, entity linking,
   PostgreSQL entity linking, vector database choice, understanding the universe of Kubernetes
   and of Fly.io, Render.io, BigQuery, GCP, AWS, blockchain.
8. Research `https://github.com/topoteretes/cognee`, plus more 3D, full video game, web game
   and other game engines, and 3D real-world coding frameworks, knowledge and physics.
9. Research what OpenAI is launching today, including sign in with ChatGPT and plugins, and
   what that does to Baltor's design, MVP and go to market.
10. Research a high-quality, up-to-date RSS source list harnesses can query, a queueing system,
    and a retrieval and ingestion system for internal file component material, and how to
    incorporate the owner's GitHub profiles, websites, documentation sites, and browser, chat
    and link history.
11. Find the skills, tools and showcases where people use large language models to make
    full parametric, rendered, programmatic video, visual design, graphic design, animation.
12. Find applications, engines, forks and variations that do 2D Mario-style games or 3D space
    battle style renders.
13. Most recent instruction: document everything done, next steps and all messages so that
    OpenAI Codex can pick this up. That is this document.

## 3. The one real repair: why the library count was stuck

This is the most important finding of the session and it is a code defect, not a capacity
limit. If you take one thing from this handoff, take this.

### 3.1 What the owner saw

The public website reports `data-library-count 23,901` and has not moved. The fast
qualification had qualified 61,523 components, all sitting on disk. The owner's complaint is
correct and the reason was not visible from the outside.

### 3.2 The chain of cause

```text
admission refuses a batch whose sampled review is not admissible
└── a review is not admissible unless its reviewer passed calibration that day
    └── calibration is a live model call to one reviewer installation
        └── every Ollama Cloud installation answered "the provider's model listing does
            not name this model" and made zero calls
            └── because tools/component_qualification/sampled_review.py built the
                ReviewerContext without the provider model listing
                    └── a gateway reviewer declares itself unavailable when
                        context.model_listing is None or does not name its model
```

The sampled review therefore reported `stopped: reviewer_not_calibrated`, or
`calibration_incomplete` with `calls: 0`, for every batch. The components were not refused on
their merits. They were withheld by a panel that never asked anyone a question.

The Tactical endpoint reviewer, `tactical.gemma-4-coding-abliterated`, is a
`provider_binding` engine and does not use the listing, so it did answer. It answered
badly: it approved three of the four known-wrong controls on the single-control pass
(`control_38d4`, `control_9bb0`, `control_e137`), which is exactly the exclusion the panel
is designed to enforce. The guard worked. The wiring did not.

### 3.3 The repair, in `tools/component_qualification/sampled_review.py`

The panel is now given the same model listing the daily catalogue review already reads:

```python
def _listed_model_versions() -> dict:
    from tools.candidate_review.reviewers.gateway import listed_model_versions
    return listed_model_versions()


def _panel(root, ledger, authorized, prechecks):
    ...
    resolver, listing = None, None
    if authorized:
        from tools import operator_credentials
        resolver = operator_credentials.resolve
        read = _listed_model_versions()
        listing = read["models"] if read.get("ok") else None
    context = ReviewerContext(model_listing=listing, repository=root, credential_resolver=resolver)
```

Reading the listing is a listing, not a model call, and the key stays in the environment.

### 3.4 The check, written before the repair

Two checks in `tools/test_component_qualification.py`, in `ReviewAdapterTests`. The first
fails without the repair and is the known-wrong case:

- `test_an_authorized_panel_offers_the_provider_model_listing_to_its_reviewers` asserts the
  context carries the listing and the credential resolver when model calls are authorized.
  Without the repair the listing is `None` and the assertion fails. The mutant is deleting
  the two lines that read the listing.
- `test_an_unauthorized_panel_reads_no_provider_listing` asserts the inverse, so the repair
  cannot be made to read the provider without authority.

Run them with `PYTHONPATH=src:tools .venv/bin/python -m unittest
tools.test_component_qualification`. Twenty-eight checks pass. The wider set of fifty-two
checks across the qualification, catalogue attribute, reference artifact and homepage
demonstration modules also passes.

### 3.5 Which reviewer qualified, and which did not

Measured on September 29, 2026, live, against the five frozen native controls. The known-good
control `control_71af` expects approve; the four known-wrong controls `control_c902`,
`control_38d4`, `control_9bb0` and `control_e137` each expect reject.

| Reviewer | Single pass | Mixed batch of 12 | Admissible | Detail |
|---|---|---|---|---|
| `ollama.kimi-k2.6` | **qualified** | **qualified** | **yes** | No false approvals. The full run used this reviewer. |
| `ollama.deepseek-v4-pro` | failed_calibration | qualified | no | Approved all three sampled known-wrong controls on the single pass. |
| `tactical.gemma-4-coding-abliterated` | failed_calibration | qualified | no | Approved three known-wrong controls; the panel excluded it, correctly. |
| `codex.gpt-6-sol` | calibration_incomplete | calibration_incomplete | no | The account's Codex allowance is exhausted until 2026-10-03. |

`ollama.glm-5.3` also reached `mixed: qualified` but failed the single pass. `qwen3.5:397b` is
named in `panel.json` but is not served by the provider, so it can never become eligible until
the panel is updated.

Only `kimi-k2.6` is admissible today. It planned 68 model calls across the 10 batches, and the
full run is in flight.

## 4. The measured supply, and what is still missing to serve it

```text
Import store, 12 GB
└── /home/username/baltor-library/import-store
    records.db holds 259,874 records, and those are not 259,874 unique useful files:
    159,307 candidates, 73,135 ideas, 22,029 superseded, 5,402 source_state, 1 withdrawn

Fast deterministic qualification, complete
└── /home/username/.le-ci-tmp/qual/all-fast
    qualification.jsonl, 215,299,830 bytes, 78,334 lines
    run.json records checked 78,334, qualified 61,523, refused 16,811
    qualifier_revision f4b4d090, 28.74 components per second, 2,483,148 per day
    per batch: openapi 1.1.0@8b1487df4626 18,986 of 22,107
              openapi 1.5.0@31331b5d59cc 11,220 of 13,703
              openapi 1.1.0@f2975696e537 10,763 of 10,765
              openapi 1.0.0@8b1487df4626  6,598 of  8,585
              json_schemas 1.1.0           355 of  9,142
              mcp_registry                   7,354 of  7,690
              function_extracts             1,767 of  1,776
              program_installs               4,099 of  4,100
              data_tables                      381 of    456

Already published
└── /home/username/baltor-bundles/daily-2026-09-29-10
    bundle.json, 23,901 items, 68,822 blobs
    bundle digest 004830981ba4606b2e9273dfb600332d678b7fd962ecba14fe0c11d30f6632e8
    active release 777f1c374003e7cf404c43d79be92e41f21d25053eff565c01590920cc1a266f
    every blob was already on the Fly volume, so the delta publish uploaded nothing

The gap
└── 23,901 items are in the active release, but the homepage counts only 15,146,
    because served_item_count() filters through approved_bindings() and the 8,755
    newer items are not yet approved by the admission path
```

## 5. Next steps, in the order they should be taken

### 5.1 Finish the sampled review and admit, which is what moves the number

Check the run in flight, then admit:

```bash
cd /home/username/loop-engine
tail -c 400 /home/username/.le-ci-tmp/qual/all-fast/review-kimi-full.log

PYTHONPATH=src:tools .venv/bin/python tools/qualify_generated_components.py admit \
  --qualification /home/username/.le-ci-tmp/qual/all-fast \
  --review /home/username/.le-ci-tmp/qual/all-fast/review-kimi-full.json \
  --store-root /home/username/baltor-library/import-store \
  --output /home/username/baltor-library/admitted-2026-09-29 \
  --recorded-at 2026-09-29
```

Then check the composition against the live bundle before combining, bundling and publishing:

```bash
PYTHONPATH=src:tools .venv/bin/python tools/qualify_generated_components.py composition \
  --bundle /home/username/baltor-bundles/daily-2026-09-29-10/bundle.json \
  --admitted /home/username/baltor-library/admitted-2026-09-29 \
  --output /home/username/.le-ci-tmp/qual/composition-2026-09-29.json
```

The composition check is not optional. The Library composition row in the
[decision table](../../AGENTS.md) caps skills, and a 61,523-component batch of API operations
and protocol servers would breach the balanced mix if admitted whole without that report.

If a batch is withheld, record the reason and move on. Do not lower the acceptance number to
force a batch through.

### 5.2 Commit what this session changed, and only that

Do not stage the whole tree. `docs/context/START-HERE.md` and
`docs/context/COMPONENT-FACTORY-AND-LOCAL-COMPONENT-STORES-2026-09-29.md` are concurrent work
by another session and are not ours to commit or reformat.

```bash
git add docs/research/EXTERNAL-SYSTEMS-2026-09-29.md \
        docs/research/GAME-AND-3D-ENGINES-2026-09-29.md \
        src/loop_engine/core/service_runtime/catalogue_attributes.py \
        tools/component_qualification/sampled_review.py \
        tools/test_component_qualification.py \
        tools/test_catalogue_attributes.py \
        tools/test_reference_artifacts.py
```

Commit message should say the reviewer was given the provider model listing, that the check
fails without it, and that reference-artifact vocabulary was added. Push in the same turn
when continuous integration passes.

### 5.3 Wire the creative vocabulary into admission, not just the attribute module

`catalogue_attributes.py` now declares the new forms, kinds, asset roles, pose layouts and
mask polarities, and `asset_role_problems()` returns what an artifact still has to declare.
The validator is currently reached only by its own test. It must be called from the admission
path, or the vocabulary is decoration. That is the next concrete change to that module.

### 5.4 The 10 second and 10 MB transport problem

Still not solved at the root. The current state is a working workaround: `sh -c` wrapping for
non-service commands, and shard-prefix pagination over 256 hex prefixes for remote digest
listing, which reduced a whole-volume listing from one 10 MB response to bounded pages.

The actual fix is a different transport, and it should be the next structural change:

- compute the delta locally from the previous bundle, so the server is asked for specific
  digests rather than for a directory listing;
- move bodies over SFTP rather than through command output;
- start long operations detached and poll a small sentinel file, because
  `fly machine exec` has an effective response ceiling of about ten seconds even with
  `--timeout 900`;
- never ask one call to return the whole `/data` tree.

A first failed delta folder may still exist at
`/data/incoming/delta-daily-2026-09-29-10-1790690514` on the machine. Remove it once the new
transport is in place.

### 5.5 The remaining deployment and verification gaps

- `mail.baltor.ai` has no A or AAAA record and returns `000`; the other nine checked
  hostnames return `200`. DNS repair needs provider authority.
- `check_hosted_website.mjs` reported 91 of 92 with the sole failure
  `hosted_browser_journey_completed` timing out under load. Rerun on an idle machine before
  treating it as a defect.
- `tools/pre_push_check.sh` has not been rerun since the fast qualification work; the last
  full self-test recorded was 3688 of 3688.
- Release record `artifacts/release-48-2026-09-29/release.json` still carries
  `ci_run: null` and does not describe the later catalogue publication. A new release record
  is needed once the admitted batch ships.
- Local disk is at about 94 percent used.

## 6. What the research produced, and what to do with it

Two new dated records. Both are research, and neither adopts anything by itself.

### 6.1 `docs/research/EXTERNAL-SYSTEMS-2026-09-29.md`

Covers eight areas the owner asked about. The decisions it records:

| System | Verdict | Reason |
|---|---|---|
| OpenHands `software-agent-sdk` | Adopt behind the `step_executor` slot, MIT, one engine beside a Baltor-native default | The repository the owner named is now a browser client; the runtime moved. Its conversation is a long-lived accumulating context, which is not our unit of work, so only its loop, tools, condenser and sandbox are reused. |
| cognee | Copy the pattern, not the tool. Apache-2.0 | Its shared-identity cross-store contract is exactly what our serving path needs. Its unit is a dataset of memory, and it answers inside the retrieval layer, which a per-step system must not do. |
| HyperFrames | Build first, Apache-2.0 | The only permissively licensed, agent-native, deterministic code-rendered video engine with a hosted render path. |
| Manim CE | Second, MIT | The technical explainer lane. |
| Godot 4 | The game and 3D lane, MIT | The only binary that runs headless and writes deterministic frames. |
| Miniflux, CommaFeed | The source registry engines, both Apache-2.0 | Polling, conditional GET and per-feed errors are already built. |
| RSSHub, FreshRSS, Karakeep | Refuse, AGPL-3.0 | Network copyleft. |
| Remotion | Refuse | Per-render fees, a mandatory licence key, mandatory telemetry, and Terms that forbid letting users upload their own code. |
| Houdini, TouchDesigner, Defold, Paper, pen.dev | Refuse | Non-commercial clauses, resolution caps and wordmarks. |
| OpenAI's plugin catalog and Agents API | Watch, and it changes the argument | A first-party plugin directory makes search and fetch a commodity, so evidence and maintained capability are the moat. |

### 6.2 `docs/research/GAME-AND-3D-ENGINES-2026-09-29.md`

Answers the 2D Mario-style and 3D space battle questions. The decisions:

- **2D:** Godot 4 with `CharacterBody2D` first, Phaser 4 second, Excalibur.js third. The
  failure that breaks generated platformers is a TileSet with no Physics Layer, so tiles never
  collide, and the game falls through a floor that renders perfectly.
- **3D:** Godot 4.7 with Jolt Physics, both MIT, and Jolt's continuous collision detection on
  by default. The failure that breaks generated space games is choosing `CharacterBody3D` for a
  Newtonian ship, and a physics engine without CCD, which lets a projectile pass through a
  hull at one metre per step.
- **A determinism contract** any such component must satisfy: fixed timestep decoupled from
  the render, simulation driven from the physics step, one seeded random source, no wall clock
  in the simulation, no GPU in the simulation path, recorded frame-indexed input, and typed
  assertions rather than eyeballed renders.
- **The opening:** no permissively licensed, genuinely 3D, ship-versus-ship dogfight with clean
  assets exists. That gap is component-shaped, not product-shaped.

### 6.3 The engine-catalogue lesson worth repeating

Almost every famous open-source game is unservable, and the reason is split licensing. Code
and assets are licensed separately, and the two rarely agree: SuperTux is GPL with CC BY-SA
data, Pekka Kana 2 is GPL with non-commercial art, Lyle in Cube Sector has no OSI licence and
third-party music, and one faithful Asteroids clone is MIT code over Atari assets. Check both
halves before anything enters a library.

## 7. The architecture rules that constrain the work above

These come from [AGENTS.md](../../AGENTS.md) and
[CONSTITUTION](../../docs/architecture/CONSTITUTION.md), and each one shaped a decision in
this handoff.

- **The executable graph vertex is the Loop.** A class whose name ends in `Node` is refused.
  The owner's "each task is a node and each node is a harness" is the existing
  [discrete cognitive or act step Loop node](../../docs/context/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-HANDOFF-2026-09-12.md):
  a bounded assignment that starts a fresh harness holding only the context that step needs.
  No new runtime, and the phrase is not shortened.
- **Every functional component sits behind a fixed, typed, versioned edge.** That is why
  OpenHands, Miniflux, CommaFeed, Rapier, Jolt and HyperFrames are all candidates behind
  existing slots rather than new subsystems.
- **A project taken from elsewhere enters as an engine adapter**, pinned to its source
  revision and licence, running in the container its trust requires, beside a Baltor-native
  engine passing the same conformance kit, or with a recorded reason it needs none.
- **The producer never approves its own work**, and a sampled review is only admissible when
  its reviewer passed calibration that day. Section 3.5 is this rule being enforced, not
  bypassed.
- **The public site does not display runtime vocabulary.** Cloud solutioning, per-step
  harnesses and pay-as-you-go are described in plain words on the website; the exact terms stay
  in the technical records.
- **A record that an older release must not honour needs a new record version.**

## 8. The infrastructure and authority facts a successor needs

- Fly: organization `baltor`, app `baltor-pilot`, region `iad`, one Machine at 1 CPU and
  2 GB, environment `pilot`. `FLY_DEPLOY_ENABLED` is restored to `false` after every deploy.
  `FLY_APPROVED_MONTHLY_USD` is 50 and must not be exceeded.
- Use `/home/username/loop-engine/tools/fly_operator.py --account baltor` for Fly commands.
  Bare `flyctl` has no token in the environment.
- `tools/operator_credentials.py inventory` reports the credentials present. `OLLAMA_API_KEY`
  is set. Cloudflare DNS and Supabase auth settings are not granted, which is why
  `mail.baltor.ai` cannot be fixed from here.
- Model calls are authorized through Ollama Cloud within the owner's existing subscription,
  with a declared ceiling and every call written to the review ledger. `codex.gpt-6-sol` is
  exhausted until 2026-10-03.
- The owner's own direction of September 23, 2026 stands: customers bring their own harness
  and their own model access. Nothing in this session changes that, and the OpenAI research
  strengthens the case.
- Multi-machine serving still depends on the unmerged `/home/username/.le-cons2-h2`, which
  has 19 commits. It is not merged and must not be described as available.
- Telemetry counters remain undeployed at
  `/home/username/baltor-private/saved-work-2026-09-28/telemetry/`, because the approved
  privacy notice says successful requests are not logged. An aggregate-only design is the
  only way forward, and it needs a named decision.

## 9. The commands that matter, collected

```bash
cd /home/username/loop-engine

# The checks for this session's repair and vocabulary
PYTHONPATH=src:tools .venv/bin/python -m unittest \
  tools.test_component_qualification tools.test_catalogue_attributes \
  tools.test_reference_artifacts tools.test_homepage_demonstration

# The full self-test, which last recorded 3688 of 3688 before this session's changes
PYTHONPATH=src:tools .venv/bin/python -m loop_engine --self-test

# The pre-push gate, which has not been rerun since the fast qualification work
bash tools/pre_push_check.sh

# The hosted site checks, which last reported 91 of 92
node tools/check_hosted_website.mjs https://baltor.ai /home/username/.le-ci-tmp/website-r50.json

# A real fresh-account journey, which passed 2 of 2
BALTOR_JOURNEY_STATE=/home/username/.le-ci-tmp/jstate/state.json \
  node tools/fresh_account_journey.mjs --fresh-only

# The live count the owner is watching
curl -s https://baltor.ai/ | grep -oE "data-library-count>[0-9,]+"

# The Fly transport, which is where the 10 second and 10 MB limits bite
.venv/bin/python tools/publish_catalogue_delta.py \
  daily-2026-09-29-10 /home/username/baltor-bundles/daily-2026-09-29-10 \
  004830981ba4606b2e9273dfb600332d678b7fd962ecba14fe0c11d30f6632e8
```

Note that the last command takes the **bundle** digest, not the items digest. Passing the
items digest was an earlier mistake and is worth not repeating.

## 10. What remains open, plainly

1. The admitted batch is not yet published, so the website number has not moved. That is
   section 5.1 and it is the owner's live complaint.
2. `asset_role_problems()` is not yet called by admission.
3. The 10 second and 10 MB transport is worked around, not solved.
4. `mail.baltor.ai` has no DNS.
5. The browser journey timeout is unconfirmed as either a real defect or load noise.
6. The release record does not describe the published catalogue.
7. Telemetry is blocked on a privacy decision.
8. Multi-machine serving is unmerged.
9. The creative and engineering supply lines have no creative, 3D, video or audio programs in
   `tools/supply_lines/program_sources.json` yet; the HyperFrames, Manim, Godot, Miniflux and
   physics decisions in section 6 have not been turned into supply lines.
10. The AI-engineering discipline list in owner instruction 4 has been researched in
    conversation but not yet written as a decision-pack catalogue with one component per
    discipline, a decisive test, and a freshness date.
