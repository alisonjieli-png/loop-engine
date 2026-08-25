# Build the Loop Engine architecture showcase

Use this prompt in a new Codex or OpenCode session rooted at
`/home/username/loop-engine`.

## Goal

Build a presentation-first architecture showcase for a developer who has not
seen Loop Engine. Export the same canonical slide data to an interactive HTML
player, PowerPoint, PDF, MP4, WebM, poster, contact sheet, and SRT captions.

The explanation must move from the whole system to one Loop, then to a useful
worked example. Use plain English. Do not use em dashes, en dashes, newspaper
language for run history, store-payment language for evidence, biological
relationship terms, or retired decision-spine names.

The title slide must read:

```text
LOOP ENGINE
Loops are all you need.
```

## Read current authority first

Read these files before editing the showcase:

- `AGENTS.md`
- `README.md`
- `humanizer-context.md`
- `docs/contracts/README.md`
- `docs/architecture/TAXONOMY-ONTOLOGY-AND-CLASS-MAP.md`
- `docs/architecture/LOOP-ENGINE-ARCHITECTURE-DRIFT-AUDIT-2026-08-25.md`
- `docs/components/loop-object/README.md`
- `docs/components/loop-object/LOOP-PROFILE-ONTOLOGY.md`
- `docs/components/practitioner/README.md`
- `docs/components/intelligence-layers/README.md`
- `docs/components/solution-canvas/README.md`
- `docs/components/static-architecture/README.md`
- `src/loop_engine/loop/loop_definition.py`
- `src/loop_engine/loop/runtime_context.py`
- `src/loop_engine/loop/loop_profile_catalog.py`
- `src/loop_engine/code_nodes/solution_graph.py`
- `src/loop_engine/code_nodes/solution_canvas.py`
- `src/loop_engine/loop/canvas.py`

Use code as authority when a document is stale. Do not invent a profile,
executor, capability group, benchmark result, or current feature.

## Architecture that every slide must preserve

### One runtime

Every executable graph vertex is a `Loop`. Practitioner, Intelligence, and
Solution are roles of that one runtime.

Passive candidates, files, services, ports, edges, prompts, packages, and
reports are not executable graph vertices.

### Complete Loop definition

```text
Loop
├── LoopDefinition
│   ├── definition ID, semantic version, and content digest
│   ├── registered role profile and version
│   ├── typed input and output roles
│   ├── supported modes and installed executors
│   ├── step profile
│   ├── loop condition and exit condition
│   ├── configuration facts
│   └── permissions, effects, and required capabilities
├── LoopRuntimeContext
│   ├── Intelligence Search and Retrieval
│   ├── Web Research
│   ├── Custom Plugins
│   └── internal runtime mechanics
├── graph relationship
└── ordered event history
```

### Three run modes

- `deterministic`: code, rules, retrieval, or execution lead. No language
  model call.
- `hybrid`: code leads. A language model may resolve a bounded semantic step.
- `non_deterministic`: a language model leads semantic work. Loop Engine still
  controls tools, permissions, budgets, events, and verification.

Mode belongs to each Loop. A graph, pipeline, or Canvas does not own one mode.
A deterministic Loop may spawn a non-deterministic Loop, and the reverse is
also valid when the definitions and restricted runtime contexts permit it.

A mode without an installed executor fails before work.

### Five relationship kinds

- Starting
- Spawned by
- Queried by
- Retrieved by
- Connected from

Use Spawned by for real dynamic delegated work. Use Queried by for an
Intelligence query. Use Retrieved by for a selected Intelligence item. Use
Connected from for typed Solution DAG value flow.

### Registered profile tree

Show only the current catalog:

```text
Practitioner
├── reference nine-step
├── compact five-step
├── research
├── solver
├── verifier
├── self-improvement
└── code execution

Intelligence
├── cross-layer search
├── materialize selected reference
├── Context: serve, search, frame
├── Code: resolve, invoke, load package or repository
├── Runtime History and Solution: search, replay, compare
└── User Feedback: serve, scope, interpret

Solution
├── atomic component
├── pipeline
├── router and fallback
├── ensemble
└── validator
```

Do not add experimenter, builder, reviewer, repairer, output formatter, or
ensemble member as registered profiles.

### Four persistent intelligence layers

1. Context Intelligence
2. Code Intelligence
3. Runtime History and Solution Intelligence
4. User Feedback Intelligence

Runtime Memory is temporary. It is not a fifth layer.

### Three Static Architecture groups

Show exactly:

1. Intelligence Search and Retrieval
2. Web Research
3. Custom Plugins

Do not place providers, models, workspaces, approvals, stores, Runtime Memory,
event history, reports, playback, MCP, skills, or trace export beside these as
peer groups. They belong inside internal runtime mechanics. They may appear on
a later detail slide under that label.

### One graph authority

`LoopGraphDefinition` is the authoritative versioned and digest-bound DAG.
Every vertex carries an exact `LoopDefinitionRef`. Every edge names typed
source and target roles. A conversion uses an explicit Adapter Loop.

`SolutionSpec` and `Canvas` build or project the graph. They are not separate
graph authorities. Canvas candidates remain passive until selection and graph
projection.

The current in-process Solution runner executes deterministic leaves only.
Do not animate a built-in hybrid or non-deterministic Solution leaf as a
working feature.

### Self-improvement

Self-improvement is a Practitioner task. It reviews a bounded population,
searches current intelligence, and stages candidate changes. Independent
review remains visible. Do not draw a separate custom Practitioner system.

## Slide sequence

Use one main idea per slide. Keep titles short. Use at least these scenes:

1. **Loop Engine.** Subtitle: "Loops are all you need."
2. **Architecture map.** Four Intelligence layers, Loop Practitioner,
   Solution Canvas, and the three Static Architecture groups. Add a small
   note that self-improvement is a later Practitioner task.
3. **One Loop object.** Reveal the complete definition and runtime context.
4. **A Loop is a typed graph vertex.** Show input, bounded work, output, loop
   condition, and exit condition.
5. **Three run modes.** Compare deterministic, hybrid, and non-deterministic.
6. **Mode belongs to each Loop.** Show mixed-mode edges and spawning.
7. **Roles and profiles.** Show the exact catalog tree.
8. **Relationships have different meanings.** Show Starting, Spawned by,
   Queried by, Retrieved by, and Connected from.
9. **Loop Practitioner.** Use a simple step view: orient, decide next, plan,
   act, verify. State that this is a simplified view of versioned profiles.
10. **Practitioner spawning.** Show bounded research and verification work
    returning typed results.
11. **Four Intelligence layers.** Show all four branches.
12. **Intelligence is Loop work.** Query, rank references, retrieve one item,
    materialize, return.
13. **Context Intelligence.** Questions, methods, constraints, formats, and
    verification lenses.
14. **Code Intelligence.** Typed functions, packages, repositories, and large
    systems behind small references.
15. **Prior work and user feedback.** Keep the two branches distinct.
16. **Solution Canvas.** Show a matrix of candidate components and viable
    paths. Candidates are passive.
17. **One authoritative Solution DAG.** Project selected candidates into
    `LoopGraphDefinition` with typed edges.
18. **Static Architecture.** Show only the three public groups.
19. **Internal runtime mechanics.** Show providers, settings, workspaces,
    approvals, stores, Runtime Memory, events, reports, playback, MCP, skills,
    and trace export as internal support, not peer architecture groups.
20. **Worked task.** Find source websites, collect PDFs, extract records,
    build a clean table, train candidate models, and verify the result.
21. **Source discovery.** A research Practitioner queries Context and User
    Feedback Intelligence, then uses Web Research.
22. **PDF inventory.** Deterministic Loops record source, document identity,
    pages, extraction method, and failures.
23. **Extraction routes.** Separate native text, table, and OCR routes. Show
    explicit verifier and fallback Loops.
24. **Data pipeline.** Connected Solution Loops normalize, validate, and write
    model-ready data through typed ports.
25. **Candidate models.** Practitioner Loops build alternatives. Deterministic
    verifier Loops compare them under one evaluator.
26. **Compiled Solution Canvas.** Show the reusable selected DAG for new input.
27. **Run History and playback.** Transform the same ordered events into live
    graph, playback, model-call, intelligence-use, and Solution views.
28. **Self-improvement stays separate.** A later Practitioner task stages
    candidates and stops before approval.
29. **Current limits.** Full value schemas, semantic Solution executors,
    compatibility composition, and the deferred internal event-log class
    rename.
30. **End state.** Use these lines:

```text
Every executable graph vertex is a Loop.
Every Loop has its own definition, role, mode, contract, and limits.
The Practitioner builds. The Solution graph runs. Run History explains.
```

Extra slides are acceptable when they split a crowded idea. Do not combine
several architecture boundaries into one unreadable diagram.

## Visual system

- Practitioner Loops: blue circles.
- Intelligence Loops: violet circles.
- Solution Loops: green circles.
- Static Architecture: gray service containers.
- Deterministic mode: solid outline.
- Hybrid mode: double outline.
- Non-deterministic mode: dotted outline with restrained motion.
- Accepted: green marker.
- Failed or refused: red marker.
- Candidate: amber marker.

Use arrows only for spawning, queries, retrieval, typed value flow, and
returned results. Label the relationship. Do not turn a service or record into
a circle that looks like a Loop.

Use a light background, strong contrast, large text, fixed title and footer
zones, and a readable 16:9 layout. Provide a reduced-motion mode.

## Deliverables

Keep one canonical data object for slide facts, labels, relationships, timing,
and captions. Every renderer must read that object.

Produce:

```text
showcase/
├── README.md
├── index.html
├── styles.css
├── showcase-data.js
├── player.js
├── record-video.mjs
├── export-slides.mjs
├── package.json
├── captions.srt
├── assets/
│   ├── loop-engine-architecture.pptx
│   ├── loop-engine-architecture.pdf
│   ├── loop-engine-architecture.mp4
│   ├── loop-engine-architecture.webm
│   ├── poster.png
│   └── contact-sheet.png
└── tests/
    ├── smoke.mjs
    └── visual-audit.mjs
```

Use the repository's actual filenames when the existing showcase differs.
Do not create duplicate showcase folders.

The browser player must support play, pause, restart, previous scene, next
scene, scrubbing, 0.5x, 1x, 1.5x, and 2x speed, keyboard controls, captions,
scene selection, reduced motion, and deterministic recording mode.

Target 1920 by 1080, 30 frames per second, and about 90 to 120 seconds. Export
both MP4 and WebM from the same deterministic timeline used by the player.

## Verification

Do not stop after file creation.

1. Run Markdown, JavaScript, and showcase smoke checks.
2. Serve the page over local HTTP and test all controls in a real browser.
3. Inspect the first slide, architecture map, Loop definition, profile tree,
   Intelligence flow, Solution DAG, worked example, current limits, and final
   slide.
4. Test 1920 by 1080 and 1280 by 720. Check for clipped text.
5. Export PowerPoint, PDF, MP4, WebM, poster, contact sheet, and captions.
6. Render the PowerPoint and PDF. Inspect every slide for overflow.
7. Decode both videos completely with `ffmpeg`.
8. Verify duration, resolution, frame rate, stream types, file sizes, and
   hashes independently of the export script.
9. Inspect frames sampled from the encoded videos.
10. Confirm that one writer produced the media. Never run two export processes
    against the same output paths.

## Architecture failure conditions

The showcase fails if it:

- creates another operational runtime;
- shows a service, file, record, candidate, or edge as a Loop;
- gives a Canvas or pipeline one inherited mode;
- lists an invented profile as registered;
- presents more than three public Static Architecture groups;
- shows a mode granting permissions;
- merges Runtime Memory into persistent intelligence;
- automatically approves self-improvement output;
- describes sequential Solution work as Spawned by;
- shows a semantic Solution leaf executing through the current deterministic
  adapter;
- uses a small task run as a general benchmark claim;
- uses retired public terminology.

## Handoff

Return clickable paths, exact local-server and export commands, test results,
browser results, slide count, video duration, resolution, frame rate, file
sizes, full-decode results, and any remaining limitation. Do not commit or push
unless the user explicitly asks in that session.
