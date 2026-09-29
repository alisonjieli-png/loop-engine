# External systems to reference, adopt, or reject: agents, memory, rendering, games, and feeds

Kind: dated research record for September 29, 2026. Every repository, page, price and
licence below was read on September 29, 2026, United States Eastern time. The
[roadmap](../roadmap/roadmap.yaml) remains the only task authority. Nothing in this record
adopts an engine, installs a product, changes a contract, or makes a public claim. Where a
subagent could not verify a fact, the entry says so instead of filling the gap.

This record covers eight areas the owner asked about on September 29, 2026: agent runtimes
that could sit behind the harness executor slot, long-term memory platforms, agentic
retrieval patterns, code-driven video and audio, game engines, procedural 3D and physics,
a self-hosted feed registry, and the OpenAI platform launches of the same day.

## 1. The short answers

```text
Adopt behind the harness executor slot
└── OpenHands software-agent-sdk, wrapped as one step executor, MIT
    └── only its loop, tools, condenser and sandbox; never its conversation as our unit

Copy the pattern, do not adopt the tool
├── cognee, Apache-2.0, the cross-store identity and citation contract
└── Promnesia, one resource has many encounters with different meanings

Serve as components, gated by licence
├── HyperFrames, Apache-2.0, the shipped code-rendered video lane
├── Manim Community Edition, MIT, the technical explainer lane
├── Godot 4, MIT, the game and 3D lane
└── Miniflux, Apache-2.0, the source registry engine

Refuse for a paid hosted product
├── Remotion, proprietary, per-render fees and a clause that forbids exactly our service
├── Houdini, Apprentice is non-commercial, 1080p capped and wordmarked
├── TouchDesigner, the free tier is "not for paying projects"
├── Defold, the licence forbids commercialising a Game Engine Product
├── RSSHub, Karakeep and FreshRSS, AGPL-3.0
└── Paper and pen.dev, proprietary, no hosted right granted
```

## 2. OpenHands, behind the harness executor slot

The owner asked about `https://github.com/OpenHands/OpenHands`. The answer is more
specific than the question. That repository is now **Agent Canvas**, a TypeScript browser
client. The agent runtime moved to `OpenHands/software-agent-sdk`, a Python SDK plus an
Agent Server. The V0 model in the question, with its EventStream, `AgentState` and
microagents, is archived in `OpenHands/legacy` and renamed in V1: EventStream became a
typed `Event` framework, `AgentState` became `ConversationState`, and microagents became
skills under `.agents/skills/`.

Licence is MIT on both repositories, "Copyright (c) 2025 OpenHands contributors". Commercial
use, modification and redistribution are permitted with the notice retained. Their own
documentation warns: "Each public repository includes its own license. Check the repository
you use or modify instead of assuming one license applies to the entire ecosystem."

The narrowest well-typed edge is a single-task executor, wrapping
`openhands.sdk.Conversation` with a `RemoteWorkspace`, `max_iteration_per_run` and
`max_budget_per_run` set per step. Reuse as-is: `openhands.tools`, the `Event` taxonomy, the
condenser, the workspace lifecycle, the LiteLLM wrapper, the metrics classes. Rewrite: our
own loop, exit condition, acceptance, permission and effect policy. Their `ConfirmationPolicy`
and `SecurityAnalyzer` are not our typed authority model and we would not delegate permission
to them.

Three risks, stated plainly. First, churn: the V0 to V1 migration is mid-flight and
destructive, and `max_budget_per_run` was added and then found unreachable through the public
`Conversation(...)` factory. Second, coupling: the `LLM` class is a LiteLLM wrapper, and
resumption validates that persisted tools must match, which couples our step state to their
tool set. Third, soft limits: the budget is checked after each step, inherited wholesale by
sub-agents, and silently inert where LiteLLM has no pricing.

Recommendation: adopt it as one engine behind the `step_executor` slot with a Baltor-native
per-step executor as the default, and evaluate only on the loop-plus-tools value. Do not adopt
its conversation as our unit of work, because our unit is a discrete cognitive or act step Loop
node that starts a fresh harness holding only that step's context.

## 3. cognee, the memory platform, and the one contract worth copying

`https://github.com/topoteretes/cognee`, Apache-2.0, "Copyright 2024 Topoteretes UG". Its own
tagline: "Cognee is a free open-source AI memory platform that gives AI agents persistent
long-term memory across sessions." At 31.2k stars with a commit on September 27, 2026 and
PyPI 1.6.1, it is active and moving fast.

The idea worth copying is the **shared-identity cross-store contract**. One identifier links
the relational provenance row, the vector chunk, and the graph node, so a vector hit can return
the whole record with its `data_id` and `chunk_id` citation. That is exactly the property our
serving path needs, and it is what keeps offered, fetched, loaded, used and verified separable.

The idea not to copy is **answering inside the retrieval layer**. `recall()` spends a model
call to write a completion; `only_context=True` exists precisely to bypass that. In a per-step
system the step's own model answers, so retrieval must return evidence only.

The licensing trap is documented by the project itself. Its README routes the two most
valuable capabilities, production small-model extraction and Postgres as a graph store, to
licensed products. A second trap is scale evidence: its BEAM results are a vendor
self-evaluation with an LLM judge, retrieval settings tuned on the same question set at 10M,
and the project calls that run "exploratory".

Recommendation: a source of patterns, not a tool to adopt. Its unit is a dataset of memory,
not the exact files and tools one step needs, and adopting it would put a graph database, a
vector database and a model call inside every step's critical path.

## 4. Agentic retrieval: the five production patterns, and where each already lives here

The owner supplied four enterprise agentic retrieval designs and asked for more. The useful
finding is that every one of them is already a named engine slot in
[`engine_slots.yaml`](../../src/loop_engine/data/engine_slots.yaml), not a new architecture.

```text
Sequential chain, the Uber shape
└── query rewrite, then tool routing, then a context merge, then a self-check
    └── already: retrieval_lexical_stage, retrieval_vector_stage,
        retrieval_rerank_stage, model_call_strategy

Router pattern
└── intent to a domain, then to a store, a schema or a live API
    └── already: catalogue_search_policy, intelligence_search_retrieval_port,
        web_research_port, custom_plugins_port

Evaluator and optimizer loop
└── generate, parse, refuse on failure, rewrite and retry
    └── already: response_evaluator, ranking_strategy, failure_journal

Schema pruning
└── strip non-execution-critical columns before the payload reaches a model
    └── already: model_call_strategy, the context budget fields on a step

Provenance before answer
└── every retrieved item carries its source identity and a citation
    └── already: harness_intelligence identity and the cognee contract in section 3
```

The honest assessment of the enterprise claims: the structural patterns are well established
and the numbers in circulating write-ups are vendor statements. We take the patterns and build
the evidence ourselves, through the existing per-step engine edge, rather than importing a
framework whose unit of work is a dataset.

## 5. Code-driven video, audio and 3D: what is production-safe today

### 5.1 The licence shortlist for a paid hosted render service

| System | Licence | Safe to embed | The trap |
|---|---|---|---|
| HyperFrames | Apache-2.0 | Yes | None found. A bundled `mediabunny` is MPL-2.0, file-level copyleft. |
| Manim Community Edition | MIT | Yes | None legal. The worker image needs LaTeX, dvisvgm, Cairo and Pango. |
| Blender | GPL-3.0-or-later, Cycles Apache-2.0 | Yes in principle | The popular MCP addon refuses to run headless; that is a technical limit, not a legal one. |
| Remotion | Proprietary "Remotion License" | **No** | $0.01 per render with a $100 monthly minimum, a mandatory licence key, mandatory per-render telemetry, and Terms that forbid letting end users upload their own Remotion code without written approval. |
| SideFX Houdini | Commercial, proprietary | **No** | Apprentice is non-commercial only, capped at 1080p, wordmarked outside `.picnc`, cannot share a pipeline with commercial Houdini, and needs a licence server. |
| TouchDesigner | Free tier non-commercial | **No** | "For personal use or learning. Not for paying projects", capped at 1280 by 1280, 10 keys per account. The MIT tdmcp server does not license TouchDesigner. |
| Penpot MCP | MPL-2.0 | Yes, as a design canvas | It is not a render engine; it belongs in a different product lane. |
| Paper | Proprietary desktop app | **No** | MCP is bound to a running local desktop app on 127.0.0.1; no headless server. |
| pen.dev | Proprietary EULA | **No** | "licensed, not sold"; personal and professional use only, no hosted right. |

**Build HyperFrames first.** It is the only candidate that is simultaneously permissively
licensed, agent-native in plain HTML with no build step, deterministic in the sense that the
same input gives the same frames, and already distributed for hosted authoring with a Lambda
render path. Its headless command is `npx hyperframes render`, with `init`, `lint`, `check`,
`snapshot` and `preview` beside it. The artifact is an editable `index.html` with `data-*`
timing attributes; the MP4 is a derived export, not the source.

**One more finding worth carrying.** Roboto Studio's write-up documents the failure mode the
owner's creative direction predicts: separately prompted scenes drifted, with "font sizes
ranged from 14 to 19px for the same role, gaps ran from 2 to 22px with no scale, tint
opacities wandered between 8 and 18%". Their fix was to move the rules out of prose and into
code: a shared component kit, named easing roles so scene code never names a raw curve, and
deletion of the non-compliant primitive rather than deprecation. That is the shape of a
served component: a skill plus a tested implementation library, not a Markdown file.

### 5.2 Audio, honestly

There is no mature DAW-as-code project. What exists is synthesis libraries of reference
quality, and MCP servers that wrap a hosted model. The production technique is text to speech
plus forced alignment plus a timeline render, not synthesis: one documented project computes
"slide durations from actual WAV length" and produces "word-level captions" with faster-whisper.
A library entry in this lane should be a measured recipe, not a dependency on a 24-star
Python package.

### 5.3 Headless WebGPU is the weak point

Headless WebGPU in a browser produces a blank canvas where the canvas should be, documented
in a three.js forum thread. three.js's own end-to-end harness runs WebGPU on a software
rasterizer. Any 3D component in this library must render headlessly through a path that is
already proven, and must keep a WebGL2 fallback.

## 6. Game engines: ranking by agent fit and by licence reality

```text
Safe to embed in a paid product
├── Godot 4, MIT, text scene format, one-line headless build, run, benchmark, movie capture
├── Babylon.js, Apache-2.0, a first-class NullEngine that runs a scene graph with no canvas
├── Phaser 4, MIT, a Phaser.HEADLESS mode and a shipped agent skills tree
├── PlayCanvas, MIT, WebGL2 and WebGPU, code-first, ships its own agent skills
├── Three.js, PixiJS, Ruffle, LÖVE, all permissive
└── Bevy, MIT OR Apache-2.0, but breaking releases every quarter make it a research target

The customer must bring a licence
├── Unity, Pro seats at $2,310 a year each, triggered by our own revenue crossing $200K
└── Unreal, 5 percent lifetime royalty above $1M, or $1,850 a seat a year

Prohibited for a hosted generator
├── Defold, "You do not sell or otherwise commercialise the Work ... as a Game Engine
│   Product", and "Game Engine Product" expressly includes "the software used to show the
│   created content"
├── Kaboom.js, the site states it is no longer maintained
└── Cocos Creator, the runtime is MIT but the editor is a closed proprietary binary
```

The five hardest problems, which are the same five the owner's creative direction names:

1. **Unresolved asset references.** A syntactically valid scene can still reference nothing.
   The symptom is invisible geometry or a crash on first load.
2. **Collision that does not match the visual.** A default collider, a box on a
   non-uniformly scaled mesh, or a static body whose navigation was never baked. Godot's
   `--debug-collisions` exists because this fails silently.
3. **Camera and coordinate-frame errors.** Y-up right-handed, Y-up left-handed, and
   -Z-forward conventions all coexist, and a naive `lookAt` produces an upside-down view that
   renders fine and is unplayable.
4. **A scene, not a game.** Geometry, lighting, no state machine, no spawner, no HUD, no win
   condition, no reset. This is the dominant failure, and it is why "playable" must be a
   check rather than an intent.
5. **Frame-rate-dependent logic and performance collapse.** Physics-step logic, unbatched
   draw calls, per-frame allocation, unbounded spawning. Sixty frames a second in an editor
   is not a measurement of the customer's machine.

On "Astra Space Adventures": **not identified.** No product of that exact title was found.
The name is close to several real and unrelated things, and "Astra" is heavily overloaded in
games. The honest answer is that we do not know which one was meant, and guessing would put a
fabricated product in a research record. It is recorded here as unknown rather than resolved.

## 7. Procedural 3D and physics: what the evidence actually says

Geometry generation is production-feasible today. CadQuery is Apache-2.0, "was built to be
used as a Python library without any GUI", and its headless CLI emits STL **and SVG previews**,
which makes the inspect step cheap. OpenSCAD is GPL-2.0 and ships a headless WASM build.
Blender renders headlessly with `blender -b file.blend -E CYCLES -s 10 -e 500 -t 2 -a`, and
Cycles is the documented choice because it "is able to run without display".

Physics is not. Three measurements, quoted:

- Code-driven simulation beats one-shot generation: 82.5 percent correct on the benchmark's
  full criterion, against 52.5 percent for the strongest of ten text-to-video models.
- Models alone are not enough: the best configuration in a second study achieved a 21.5
  percent pass rate, "current models have potential to generate correct simulations but lack
  the consistency to do so reliably".
- Running is not correct: in an audit of 220 generated cases, 39 to 40 percent were runnable
  but solved the wrong physics, because "a generated input file can run, mesh, and converge
  while encoding governing equations that differ from the user's intent".

That last number is the design rule for this library. A physics component is admissible only
when deterministic invariants are checked, never because the script ran. Rapier is Apache-2.0
and scriptable headlessly in Rust, WASM and Python; MuJoCo is Apache-2.0 with offscreen
rendering; Bullet3 is zlib; cannon-es is MIT. One of those becomes the engine behind the
process confinement and workspace slots, and each earns its own component only with an
invariant test attached.

## 8. A self-hosted source registry and ingestion queue

### 8.1 The engine shortlist

| System | Licence | Safe for a paid product | What it gives |
|---|---|---|---|
| Miniflux | Apache-2.0 | Yes | Polling, conditional GET through `etag_header` and `last_modified_header`, per-feed `parsing_error_message`, scraper rules, OPML, discovery. |
| CommaFeed | Apache-2.0 | Yes | A second independent parser, Google Reader and Fever APIs, an embedded H2 mode with no infrastructure. |
| pg-boss | MIT | Yes | Durable scheduling and retries in Postgres, so no Redis. |
| RSSHub | AGPL-3.0 | Only unmodified and separate | Route generators for sites without a feed; the Puppeteer path needs Chromium. |
| FreshRSS, Karakeep, nitter | AGPL-3.0 | No | FreshRSS XPath scraping, Karakeep bookmark hoarding, nitter is archived. |
| Tiny Tiny RSS | GPL-3.0 | Any derivative stays copyleft | Readability plus an `af_php` plugin system. |
| Readwise Reader, Feedmail | Closed | No | Hosted services, not self-hostable. |

**Miniflux is the ingestion engine**, with CommaFeed as a second engine behind the same fixed
edge and the same conformance kit, which is precisely the rule the engine slot catalogue
already states. What Baltor still builds: the source registry, quality assessment, the
approval and publication path, per-step context assembly, the durable job contract, and the
mapping from an entry to a served component package. Miniflux knows nothing of provenance,
licence, review or tiers.

### 8.2 Two queues, not one

```text
Processing queue: has the material been acquired and transformed?
Discovered -> Queued -> Fetched -> Parsed -> Indexed, with retry and a dead letter

Consideration inbox: should we use, adapt, test, publish or reject it?
Unreviewed -> Proposed -> Accept, or Reuse existing, or Dismiss, or Defer
```

Successful ingestion must never mean approved context or an installed component. A dismissed
candidate stays searchable with its reason, so another research loop does not rediscover it.
A reader's unread flag is not an ingestion queue; reading and processing are different states,
and the queue needs its own durable cursor and ledger.

### 8.3 The arXiv feeds, confirmed

The official documentation is at `https://info.arxiv.org/help/rss.html`, which states: "RSS 2.0
and ATOM news feed pages are available for all active subject areas within arXiv. Feeds are
updated daily at midnight Eastern Standard Time." The pattern is
`https://rss.arxiv.org/rss/<category>` and the Atom equivalent under `/atom/`. For the six
subjects the owner named: `cs.AI`, `cs.LG`, `cs.CL`, `cs.SE`, `cs.DC` and `cs.IR`.
Combinations use a plus sign, and the documentation warns "Limit 2000 results", so each poll
must be capped and paged rather than unioned without bound. Two operational facts to encode:
arXiv "has an empty feed on Saturday/Sundays and on occasional arXiv holidays", and item GUIDs
are versioned, so deduplication is on the bare identifier, not the versioned GUID.

### 8.4 Link and encounter history

The concept worth taking is Promnesia's: **one resource has many encounters, each with its
own meaning and permission**. A repository the owner saw in a chat, bookmarked, later evaluated
and rejected is four facts, not one preference. Every importer therefore writes a coverage
record with the historical window, the last successful import, and the explicit excluded,
unsupported and unauthorized lists, so missing data never becomes false confidence.

Two hard limits. GitHub's general events timeline is capped at 300 events and covers only the
past 30 days, so it is not a lifetime archive. Chrome's history API defaults to the previous 24
hours and at most 100 results unless the parameters change, and its permission includes
modification, so read-only has to be enforced by the implementation rather than assumed from
the permission name.

## 9. The OpenAI platform, September 29, 2026

Verified on the day. OpenAI held DevDay 2026 with "more than 20 major announcements across
ChatGPT, Codex, our models, and entirely new forms of working with AI", describing ChatGPT as
"a shared surface where humans and agents can collaborate and where developers can directly
launch new native experiences to our collective 1.2B weekly users".

What matters for this library, with each claim marked as the page's own or our inference:

1. **The extension mechanism is plugins**, bundling skills, MCP servers, browser extensions
   and hooks, with live documentation at `https://developers.openai.com/plugins`. Custom GPTs
   are being retired in favour of plugins. (Page's own.)
2. **A public plugin catalog exists and third parties may publish**, with a submission review
   and "Rankings now prioritize plugins people keep using after installation". (Page's own.)
   A registry that serves only skills and instructions is therefore substitutable; a registry
   that serves reviewed executable capabilities with evidence and provenance is not.
3. **The agent runtime is being absorbed.** The Agents API runs Codex's harness hosted, with
   subagents, compaction and skills. (Page's own.) Compete on material selection and
   verification, not on orchestration.
4. **Cached input is cheap**: GPT-6.1 Sol is "$2 per million input tokens, $0.10 per million
   cached input tokens, and $10 per million output tokens". (Page's own.) Inference: per-step
   cost is a weaker selling point than quality, so the measured claim we still need is about
   accepted work, not tokens.
5. **Format interoperability is available today**: the manifest schema is public and Codex
   plugins support a `skills` directory plus an MCP configuration. (Page's own.) Shipping our
   components in that shape is a low-cost, concrete deliverable.
6. **Our own position is unchanged and better argued.** Customers bring their own harness and
   their own model access. The owner's September 23, 2026 direction stands. What changed is
   that a first-party plugin directory makes the "search and fetch the reviewed library"
   surface a commodity, and makes the evidence and the maintained capability the moat.

## 10. What follows from this record

1. The `step_executor` slot gains OpenHands as one candidate engine, written as an adapter
   with a pinned revision and its own conformance kit run, beside a Baltor-native default.
   Nothing is adopted until that kit passes alone.
2. The cross-store identity and citation contract from cognee is written into our typed
   serving edge, so offered, fetched, loaded, used and verified stay separable at the record
   level.
3. HyperFrames becomes the first shipped creative capability, with a parameter schema, a
   source directory, a render command, a preview and a preservation test. Manim follows for
   technical explainers.
4. Godot 4 is the game and 3D lane, with `--headless`, `--write-movie` and
   `--debug-collisions` as the observe-and-diagnose step rather than a prose claim.
5. Miniflux is the source registry engine behind a new slot, with CommaFeed as the second
   engine behind the same edge, and a processing queue and a consideration inbox kept
   separate.
6. Every new component carries a licence verdict, a hard-constraint check, a counterexample,
   and a statement of what was not tested.

## 11. Sources

- `https://github.com/OpenHands/OpenHands` and `https://github.com/OpenHands/software-agent-sdk`
- `https://github.com/topoteretes/cognee` and `https://docs.cognee.ai/`
- `https://github.com/heygen-com/hyperframes`
- `https://www.remotion.dev/docs/terms` and `https://www.remotion.dev/docs/license/faq`
- `https://robotostudio.com/blog/how-to-use-remotion-agent-skills-with-claude-code`
- `https://www.sidefx.com/learn/talks/ai-inside-houdini-not-instead-of-it/`
- `https://github.com/Pantani/tdmcp`
- `https://github.com/ManimCommunity/manim`
- `https://github.com/ahujasid/blender-mcp` and `https://docs.blender.org/manual/en/latest/advanced/command_line/render.html`
- `https://github.com/cadquery/cadquery` and `https://openscad.org/about.html`
- `https://github.com/dimforge/rapier`, `https://github.com/google-deepmind/mujoco`,
  `https://github.com/bulletphysics/bullet3`, `https://github.com/code4fukui/cannon-es`
- Godot licence text, `https://godotengine.org/license/`, and the Godot command-line
  documentation for `--headless`, `--write-movie` and `--debug-collisions`
- Defold License 1.0 section 4(a), `https://defold.com/product/license/`
- `https://miniflux.app/features.html` and `https://github.com/miniflux/v2`
- `https://github.com/Athou/commafeed` and `https://github.com/timgit/pg-boss`
- `https://github.com/DIYgod/RSSHub`, `https://github.com/FreshRSS/FreshRSS`,
  `https://github.com/hoarder-app/hoarder`
- `https://info.arxiv.org/help/rss.html`
- `https://openai.com/news/`, `https://developers.openai.com/plugins`,
  `https://platform.openai.com/docs/changelog`,
  `https://help.openai.com/en/articles/20001256`
- `https://walkinglabs/learn-harness-engineering` and
  `https://github.com/walkinglabs/awesome-harness-engineering`
- `https://www.revid.ai/claude-motion-graphics`
- The owner's own messages of September 29, 2026, which supplied the enterprise agentic
  retrieval write-ups, the browser-game market figures and the creative rendering catalog.
