# Build the Loop Engine architecture showcase and diagram video

Use this prompt in a completely new Codex chat. Work in the Loop Engine
repository at `/home/username/loop-engine`.

## Goal

Build a polished, self-contained HTML, CSS, SVG, and JavaScript architecture
showcase that explains Loop Engine from the highest level to the lowest level.
It must also export a real diagram video that shows loops starting other loops,
returning results, using intelligence, building a Solution Canvas, and recording
the run for live viewing and playback.

The result is for a developer seeing Loop Engine for the first time. The reader
may use English as a second language. Use plain, direct sentences. Avoid hype,
AI slang, vague abstractions, em dashes, en dashes, and accounting metaphors.
Use report, record, log, or evidence when one of those words is accurate.

## Work from the current repository

Do not rely only on this prompt. Read the current files before designing:

- `README.md`
- `humanizer-context.md`
- `docs/components/README.md`
- `docs/components/loop-object/README.md`
- `docs/components/loop-object/LOOP-PROFILE-ONTOLOGY.md`
- `docs/components/practitioner/README.md`
- `docs/components/intelligence-layers/README.md`
- `docs/components/intelligence-layers/INTELLIGENCE-AS-LOOPS.md`
- `docs/components/intelligence-layers/INTELLIGENCE-PORTFOLIOS.md`
- `docs/components/solution-canvas/README.md`
- `docs/components/static-architecture/README.md`
- `docs/components/self-improvement/README.md`
- `docs/guides/spawned-loop-delegation.md`
- `docs/guides/reports.md`
- `docs/guides/studio-runtime-views.md`
- `src/loop_engine/loop/loop_profile_catalog.py`
- `src/loop_engine/loop/loop_profile_ontology.py`
- `src/loop_engine/loop/delegation_runtime.py`
- `src/loop_engine/static_architecture/intelligence_portfolio.py`
- `src/loop_engine/code_nodes/solution_canvas.py`
- `src/loop_engine/static_architecture/studio_server.py`

Check `AGENTS.md` or other repository instructions if present. Preserve
unrelated and concurrent changes. Use the current code as authority when a
document is stale. If code and documentation disagree, make the showcase state
the verified current behavior and list the disagreement in its README.

## Core architecture to communicate

There is one operational runtime object: `Loop`.

Each Loop is one node with:

- a goal;
- a typed input and output contract;
- an operational relationship;
- a role profile;
- a run mode;
- a step profile;
- a work budget;
- a loop condition and an exit condition;
- an outgoing relationship;
- a spawning Loop ID only when it is genuinely Spawned;
- Spawned Loop IDs when it starts other work;
- an event history in the Run History.

Relationship, role, and profile are separate dimensions:

```text
Loop object
├── Operational relationship
│   ├── Starting
│   ├── Spawned by
│   ├── Queried by
│   ├── Retrieved by
│   └── Connected from
└── Role profile
    ├── Practitioner
    │   └── may be Starting or a genuinely Spawned subproblem
    ├── Intelligence
    │   ├── Intelligence Query Loop is Queried by a Practitioner
    │   └── Intelligence Item Loops are Retrieved by the Query Loop
    └── Solution
        ├── Starting Solution Loop
        ├── deterministic pipeline Loops are Connected from
        └── dynamic branches may be Spawned by
```

Do not create a second runtime for any role. `Sub` and the legacy `spawned`
topology value remain compatibility language for a real spawn. They do not
describe queries, retrieval, or deterministic pipeline connections.

The showcase must include this complete classification tree. Do not compress
it into one row of labels:

```text
Operational runtime type
└── Loop
    ├── Identity
    │   ├── Loop ID
    │   ├── profile version
    │   └── spawning Loop ID for a real Spawned by relationship
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
    │   ├── atomic
    │   ├── compact
    │   ├── reference nine-step
    │   └── custom
    ├── Typed contract
    │   ├── named input ports
    │   ├── named output ports
    │   └── compatibility checks
    ├── Operating settings
    │   ├── work and call budgets
    │   ├── permissions and allowed effects
    │   ├── workspace and network policy
    │   └── exit condition
    ├── Model settings when model use is allowed
    │   ├── thinking power
    │   ├── provider and model route
    │   ├── exact maximum output capability
    │   └── retry and failover policy
    └── Evidence
        ├── Run History events
        ├── returned result
        ├── validation outcome
        └── Spawned Loop IDs
```

This tree defines separate classification axes. The showcase must teach the
meaning of each one:

- Runtime type is always `Loop`.
- Topology is Starting or Spawned.
- Role is Practitioner, Intelligence, or Solution.
- A profile is a reusable, versioned behavior preset inside a role.
- A category organizes purpose, domain, or retrieval metadata. It does not
  create another runtime class.
- A mode is deterministic, hybrid, or non-deterministic.
- A step profile defines ordered work steps.
- Settings define contracts, budgets, permissions, effects, model routes, and
  stopping behavior.
- Thinking power applies only when the mode and permissions allow a model. It
  is not a fourth mode.

The role profiles expand as follows:

```text
Practitioner
├── researcher
├── solver
├── experimenter
├── builder
├── verifier
├── reviewer
├── repairer
├── code executor
└── self-improvement task

Intelligence
├── search and rank
├── select
├── materialize
├── frame for the current task
├── invoke Code Intelligence
├── replay or compare prior work
└── interpret User Feedback Intelligence

Solution
├── component
├── pipeline
├── validator
├── router
├── fallback
├── ensemble member
└── output formatter
```

Also show Intelligence role profiles beneath the four intelligence layers.
The layer classifies the persistent item. The role profile classifies what the
Intelligence Loop is doing with that item:

```text
Intelligence Loop role
├── Context Intelligence
│   ├── search questions and methods
│   ├── select reviewed lenses
│   ├── materialize selected context
│   └── frame context for the current task
├── Code Intelligence
│   ├── search typed capability cards
│   ├── check compatibility and effects
│   ├── materialize a selected package or callable
│   └── invoke it through a Loop
├── Runtime History and Solution Intelligence
│   ├── search comparable runs
│   ├── replay saved evidence
│   └── compare prior solutions
└── User Feedback Intelligence
    ├── search scoped guidance
    ├── check authority and relevance
    └── interpret guidance for the current task
```

Each Loop has one of three run modes:

- `deterministic`: code, rules, calculations, retrieval, or execution with no
  language-model call;
- `hybrid`: code leads and a model may resolve a bounded semantic step;
- `non_deterministic`: a model leads the semantic work while Loop Engine keeps
  control of tools, permissions, limits, logging, and verification.

A spawning Loop and its Spawned Loop may use different modes. Show these
relationships separately from query, retrieval, and connection edges:

- a non-deterministic Practitioner queries a deterministic Intelligence Query Loop;
- a non-deterministic Practitioner starts two non-deterministic candidate
  Spawned Practitioners with different Context Intelligence;
- an Intelligence Query Loop retrieves a deterministic Code Intelligence Item Loop;
- a non-deterministic Spawned synthesis Practitioner compares the candidates;
- a deterministic verifier rejects or accepts the result;
- a failed result spawns a non-deterministic repair Practitioner;
- a Starting Solution Loop connects deterministic Solution components.

Show that role and mode form independent axes:

```text
Practitioner Loop
├── deterministic
├── hybrid
└── non-deterministic, with model-led semantic work

Intelligence Loop
├── deterministic
├── hybrid
└── non-deterministic, with model-led framing or interpretation

Solution Loop
├── deterministic
├── hybrid
└── non-deterministic, when an execution adapter supports it
```

Keep current implementation coverage honest. The universal Loop contract can
represent all nine role and mode combinations. If the current Solution Canvas
runner lacks a separate hybrid or non-deterministic execution adapter, show
that limitation explicitly instead of animating it as shipped behavior.

The animation must include one full spawning graph with modes on every Loop:

```text
Starting Practitioner [non-deterministic]
├── Spawned Intelligence search [deterministic]
│   ├── Context search [deterministic]
│   ├── Code search [deterministic]
│   ├── Runtime History and Solution search [deterministic]
│   └── User guidance search [deterministic]
├── Candidate Practitioner A [non-deterministic]
│   ├── Code Intelligence selection [deterministic]
│   └── Code execution [deterministic]
├── Candidate Practitioner B [non-deterministic]
│   ├── Code Intelligence selection [deterministic]
│   └── Code execution [deterministic]
├── Synthesis Practitioner [non-deterministic]
├── Verifier [deterministic]
│   └── Repair Practitioner [non-deterministic, only after failure]
└── Compiled Solution Canvas
    └── Spawned Solution components [deterministic in the current runner]
```

Then show a later request starting the compiled Canvas directly:

```text
Starting Solution [deterministic in the current runner]
├── validate input
├── transform
├── execute selected capability
├── verify output
├── apply fallback when authorized
└── format output
```

The four persistent intelligence layers are:

1. Context Intelligence
2. Code Intelligence
3. Runtime History and Solution Intelligence
4. User Feedback Intelligence

Runtime Memory is separate and lasts only for the current run. A Markdown file,
skill, transcript, checkpoint, or vector row is a source format, not an
intelligence layer. Imported items remain candidates until independent review.

Static Architecture has three public capability groups:

- Intelligence Search and Retrieval
- Web Research
- Custom Plugins

Providers, model gateway, typed settings, workspaces, approvals, stores,
Runtime Memory, Run History, reports, playback, and trace export are internal
runtime mechanics. Do not draw them as peer Static Architecture components.

The Loop Practitioner builds and verifies work. The Solution Canvas describes
what runs for a new input. Self-improvement is a Practitioner task. It is not a
fourth runtime role, and it cannot approve its own candidates.

## Required showcase scenes

Create a deterministic animation timeline with named scenes. The user must be
able to play, pause, replay, scrub, step forward, step backward, and change the
speed. The same timeline must drive the browser experience and video export.

### Scene 1: One Loop object

Start with one large circle labeled `Loop`. Reveal goal, typed contract, role,
mode, step profile, budget, exit condition, and Run History events around it.

### Scene 2: Position and role

Split the view into the orthogonal position and role trees. Show that every
role can be a Starting Loop or Spawned Loop. Do not show Starting Solution without also
showing Starting Practitioner and Starting Intelligence. Expand this scene into the
complete runtime, topology, role, profile, category, mode, step, contract, and
settings tree before moving to the task example.

### Scene 3: One non-deterministic task enters

Show a real-shaped task entering a Starting Practitioner. Use a useful task such as
building and validating a small data pipeline or model, not hello world.

### Scene 4: Intelligence portfolio

The Starting Practitioner queries a deterministic Intelligence Query Loop.
Show it retrieve Intelligence Item Loops across all four layers. Return seven
distinct reviewed lenses:

- first principles;
- alternatives or analogy;
- missing information;
- failure or adversarial risks;
- cost and resource discipline;
- verification and evaluation;
- output contract and format.

Show exact `LoopRef` cards returning to the querying Practitioner. Keep large bodies behind
references. Show an empty layer honestly when it has no matching record.

### Scene 5: Candidate Spawned Practitioners

Start two non-deterministic Spawned Practitioner loops. Give them different
Context portfolios. Animate their private contexts separately. They may read
shared Runtime Memory, but one Spawned Practitioner must not receive another
Spawned Practitioner's private
history.

Keep a visible spawning graph at the side of the scene. Add each new Spawned Loop
when it starts. Label every Loop node with role profile, node mode, typed ports,
loop condition, exit condition, outgoing relationship, status, and spawning
Loop ID. Animate the result returning along the same spawn edge.

### Scene 6: Code Intelligence

Each candidate searches registered Code Intelligence. Show small typed cards,
then materialize only the selected callable or package. Show that discovery is
effect-free and execution begins only after selection and permission checks.

### Scene 7: Synthesis, verification, and repair

Return candidate outputs to a non-deterministic Spawned synthesis Practitioner. Run a
deterministic verifier. Show both branches:

- accepted result continues;
- failed result spawns a failure-specific repair Practitioner and returns to
  verification.

### Scene 8: Solution Canvas

The Practitioner compiles a Solution Canvas. Show a Starting Solution Loop and
typed Connected Solution Loops for validation, transformation, execution,
verification, and output formatting. Use a Spawned Solution Loop only for a
dynamic fallback, repair, route, or ensemble branch. Animate values moving
only across compatible typed ports.

### Scene 9: Static Architecture

Pull back to show the three Static Architecture capability groups around every
role: Intelligence Search and Retrieval, Web Research, and Custom Plugins.
Show Loops using them through typed, permitted calls. Do not add internal
runtime mechanics to this peer architecture block.

### Scene 10: Run History, live view, and playback

Show every Loop event flowing into one ordered Run History. Then transform the
same events into a live graph, playback timeline, model-call panel,
intelligence-consumption panel, approvals panel, and Solution Canvas view.

### Scene 11: Self-improvement is a Practitioner task

Show a later Starting Practitioner receiving a normal self-improvement task.
It reviews a bounded historical population, searches current intelligence,
and stages candidate improvements. Do not draw a separate self-improvement
system or custom Practitioner type. End before promotion. A separate review
decision must remain visible.

### Scene 12: End state

End with three short statements:

```text
Everything that performs work is a Loop.
Every Loop has its own role, mode, contract, budget, and exit condition.
The Practitioner builds. The Solution Canvas runs. The Run History explains.
```

## Visual design

Use an information-first visual system:

- Practitioner loops: blue
- Intelligence loops: violet
- Solution loops: green
- Static Architecture: neutral gray
- deterministic mode: solid outline
- hybrid mode: double outline
- non-deterministic mode: animated dotted glow
- accepted: green status marker
- failed or refused: red status marker
- candidate: amber status marker

Use circles for Loop objects. Use distinct arrow labels for dynamic spawning,
Intelligence queries, Intelligence retrieval, typed Solution connections, and
returned results. Do not turn services, files, prompts,
or intelligence records into fake executable graph vertices.

Use a light background, strong contrast, large labels, and restrained motion.
Avoid decorative gradients that reduce legibility. Support 16:9 desktop and a
readable narrow layout. Add a reduced-motion mode.

## Deliverables

Create the dedicated `showcase/` folder with:

```text
showcase/
├── README.md
├── index.html
├── styles.css
├── architecture-data.js
├── diagram.js
├── timeline.js
├── controls.js
├── record-video.mjs
├── assets/
│   ├── poster.png
│   ├── loop-engine-architecture.webm
│   └── loop-engine-architecture.mp4
└── tests/
    └── showcase-smoke.mjs
```

Keep architecture facts in one small data object. Rendering and animation must
read that object. Do not duplicate labels and relationships throughout the
JavaScript.

The page must work from a small local HTTP server. Do not require a build step
for viewing. Use browser-native HTML, CSS, SVG, Canvas, and JavaScript. A small
recording dependency is acceptable, but pin its version and explain it.

The video must be a real exported artifact, not a plan. Target 1920 by 1080,
30 frames per second, and 75 to 120 seconds. Export WebM and MP4. If MP4
requires `ffmpeg`, detect it and fail with a clear command instead of silently
omitting the file. Capture from the same deterministic timeline used by the
interactive page.

## Interaction and accessibility

Include:

- play and pause;
- timeline scrubber;
- previous and next scene;
- 0.5x, 1x, 1.5x, and 2x speed;
- restart;
- scene list;
- visible captions for every scene;
- keyboard controls;
- reduced motion;
- no autoplay audio;
- semantic labels and sufficient contrast.

Add a query parameter or JavaScript API for deterministic recording, such as
`?record=1`, that starts at scene 1, disables manual controls, uses fixed
timing, and signals completion.

## Verification

Do not stop after writing files.

1. Start the local server.
2. Open the page in a real browser.
3. Inspect the initial view, at least four middle scenes, failure and repair,
   Solution Canvas, and the final view.
4. Test play, pause, scrub, previous, next, speed, restart, and reduced motion.
5. Check the browser console for errors.
6. Verify that no label clips at 1920 by 1080 and 1280 by 720.
7. Export the video.
8. Inspect the poster and several video frames.
9. Verify duration, resolution, frame rate, file sizes, and that MP4 and WebM
   both open.
10. Run the smoke test from a clean checkout path.

## Architecture accuracy gates

The showcase fails if it does any of the following:

- creates a second operational runtime type;
- treats `sub` as a different runtime instead of Spawned topology;
- gives only Solution a Starting Loop;
- conflates Loop role, run mode, step profile, or thinking power;
- uses `type` for a role, profile, category, or mode without qualification;
- hides which settings apply to every Loop and which apply only to model use;
- shows a role or profile without its place in the complete Loop tree;
- shows mode as inherited from a spawning Loop;
- shows model use granting file, network, secret, or spending permission;
- merges Runtime Memory into persistent intelligence;
- treats files or skills as one generic memory layer;
- promotes self-improvement candidates automatically;
- calls a component probe a full-system benchmark;
- uses stale internal terms when the current code has a different public name.

## Final handoff

Return:

- clickable paths to every deliverable;
- the exact local server command;
- the exact video export command;
- browser and video verification results;
- any architecture disagreement found in current repository files;
- file sizes and duration for both videos;
- a short list of what remains incomplete, if anything.

Do not commit or push unless the user explicitly asks in that new chat.
