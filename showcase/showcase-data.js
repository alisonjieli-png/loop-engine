export const showcaseData = {
  meta: {
    title: "Loop Engine",
    subtitle: "Loops are all you need.",
    brand: "Loop Engine architecture showcase",
    width: 1920,
    height: 1080,
    framesPerSecond: 30,
    statusLabel: "Architecture contract",
    proofLabel: "Current implementation status is stated where needed."
  },
  ui: {
    documentTitle: "Loop Engine architecture showcase",
    stageLabel: "Loop Engine architecture presentation",
    controlsLabel: "Presentation controls",
    scenesLabel: "Presentation slides",
    captionLabel: "Current slide caption",
    play: "Play",
    pause: "Pause",
    previous: "Previous",
    next: "Next",
    restart: "Restart",
    timeline: "Presentation timeline",
    speed: "Speed",
    reducedMotion: "Reduce motion",
    sceneCounterTemplate: "Slide {current} of {total}",
    slideLabel: "Slide",
    speedOptions: [
      { value: 0.5, label: "0.5x" },
      { value: 1, label: "1x" },
      { value: 1.5, label: "1.5x" },
      { value: 2, label: "2x" }
    ],
    recordingFileName: "loop-engine-architecture.webm",
    recordingUnsupported: "This browser cannot record the Canvas presentation as WebM."
  },
  palette: {
    background: "#F8FAFC",
    paper: "#FFFFFF",
    ink: "#0F172A",
    muted: "#475569",
    faint: "#E2E8F0",
    line: "#CBD5E1",
    practitioner: "#2563EB",
    practitionerSoft: "#DBEAFE",
    intelligence: "#7C3AED",
    intelligenceSoft: "#EDE9FE",
    solution: "#15803D",
    solutionSoft: "#DCFCE7",
    static: "#64748B",
    staticSoft: "#F1F5F9",
    improvement: "#B45309",
    improvementSoft: "#FEF3C7",
    danger: "#B91C1C",
    dangerSoft: "#FEE2E2",
    accepted: "#15803D",
    candidate: "#B45309"
  },
  roles: {
    practitioner: { label: "Practitioner Loop", color: "practitioner", soft: "practitionerSoft" },
    intelligence: { label: "Intelligence Loop", color: "intelligence", soft: "intelligenceSoft" },
    solution: { label: "Solution Loop", color: "solution", soft: "solutionSoft" },
    static: { label: "Static Architecture", color: "static", soft: "staticSoft" },
  },
  modes: {
    deterministic: {
      label: "Deterministic",
      style: "solid",
      lead: "Code, rules, retrieval, or calculation leads.",
      model: "No language-model call."
    },
    hybrid: {
      label: "Hybrid",
      style: "double",
      lead: "Code leads. A model may resolve one bounded semantic step.",
      model: "A real model call is optional and recorded when used."
    },
    nonDeterministic: {
      label: "Non-deterministic or LLM-driven",
      style: "dotted",
      lead: "A model leads the semantic work.",
      model: "A real model attempt is required for model-led success."
    }
  },
  slides: [
    {
      id: "title",
      durationSeconds: 3,
      kind: "title",
      kicker: "Architecture showcase",
      title: "Loop Engine",
      subtitle: "Loops are all you need.",
      caption: "Loop Engine uses one operational runtime object for every executable graph vertex.",
      annotation: "This presentation separates the architecture contract from current implementation status.",
      visual: {
        statement: "Every executable graph vertex is a Loop.",
        marks: ["Practitioner", "Intelligence", "Solution"]
      }
    },
    {
      id: "architecture-overview",
      durationSeconds: 5,
      kind: "overview",
      kicker: "Bird's-eye view",
      title: "One system, four clear parts",
      subtitle: "The Practitioner builds. The Canvas describes what runs. Intelligence and Static Architecture support the work.",
      caption: "Self-improvement is a Practitioner task profile. It is not a fifth system part.",
      annotation: "Implemented. Established constructor calls remain visible as compatibility composition.",
      visual: {
        flow: [
          { label: "Loop Practitioner", role: "practitioner", detail: "understand, build, verify" },
          { label: "Solution Canvas", role: "solution", detail: "candidate Solution graphs" }
        ],
        intelligence: {
          label: "Four Intelligence Layers",
          role: "intelligence",
          items: ["Context", "Code", "Run and Solution", "User Feedback"]
        },
        staticArchitecture: {
          label: "Static Architecture",
          role: "static",
          items: ["Intelligence Search and Retrieval", "Web Research", "Custom Plugins"]
        }
      }
    },
    {
      id: "loop-object",
      durationSeconds: 3.5,
      kind: "loop-object",
      kicker: "The Loop object",
      title: "A Loop is one typed operational node",
      subtitle: "It has a stable definition, a run instance, and explicit graph relationships.",
      caption: "Ports, records, files, edges, and services are not additional operational node types.",
      annotation: "Implemented. One immutable definition binds profile, contract, modes, conditions, capabilities, version, and digest.",
      visual: {
        loopLabel: "Loop",
        profileLabel: "versioned definition",
        input: "Typed input ports",
        output: "Typed output ports",
        fields: [
          "Versioned role profile",
          "Selected run mode",
          "Step profile",
          "Loop condition",
          "Exit condition",
          "Budget and permissions",
          "Graph relationships",
          "Run History events"
        ]
      }
    },
    {
      id: "typed-flow",
      durationSeconds: 3.5,
      kind: "typed-flow",
      kicker: "Typed boundaries",
      title: "Input, work, validated output",
      subtitle: "A connection runs only when the source output matches the destination input.",
      caption: "Schema version, shape, optionality, units, and encoding belong in the port contract.",
      annotation: "Current port checks use role labels. Full value-schema enforcement remains planned.",
      visual: {
        input: { label: "Input value", type: "pdf_document@2", example: "document.pdf" },
        loop: { label: "Extraction Loop", role: "solution", mode: "deterministic", profile: "solution.component@1" },
        output: { label: "Output value", type: "table_rows@3", example: "validated rows" },
        check: "Connection check before execution"
      }
    },
    {
      id: "definition-and-instance",
      durationSeconds: 3.8,
      kind: "two-column",
      kicker: "Identity and execution",
      title: "Definition first, instance second",
      subtitle: "The definition states what may run. The instance records one actual run.",
      caption: "A graph vertex should resolve to an exact definition ID, version, and content digest.",
      annotation: "Implemented. Every current Loop event includes its exact definition ID, version, and content digest.",
      visual: {
        columns: [
          {
            label: "LoopDefinition",
            role: "static",
            items: ["ID, semantic version, digest", "role and exact profile", "typed ports and settings schema", "supported modes and effects"]
          },
          {
            label: "LoopInstance",
            role: "practitioner",
            items: ["instance ID and definition reference", "selected mode and validated input", "status, counters, and relationships", "outputs and Run History references"]
          }
        ]
      }
    },
    {
      id: "deterministic-mode",
      durationSeconds: 3.2,
      kind: "mode",
      kicker: "Run mode 1 of 3",
      title: "Deterministic",
      subtitle: "Code, rules, retrieval, or calculation leads the work.",
      caption: "A deterministic Loop records zero physical model calls.",
      annotation: "Example: validate a schema, calculate a metric, or retrieve an exact reference.",
      visual: {
        mode: "deterministic",
        loopLabel: "Schema validation Loop",
        steps: ["read typed input", "apply rules", "return typed result"],
        control: "Loop Engine controls permissions, budget, logging, and verification."
      }
    },
    {
      id: "hybrid-mode",
      durationSeconds: 3.4,
      kind: "mode",
      kicker: "Run mode 2 of 3",
      title: "Hybrid",
      subtitle: "Code leads. A real model may resolve one bounded semantic step.",
      caption: "The model path is optional. If used, its physical call and usage must be recorded.",
      annotation: "Example: code extracts a table and a model resolves one ambiguous column heading.",
      visual: {
        mode: "hybrid",
        loopLabel: "Ambiguity resolution Loop",
        steps: ["run deterministic extraction", "resolve bounded ambiguity", "validate the result"],
        control: "Model use does not grant file, network, secret, or spending permission."
      }
    },
    {
      id: "non-deterministic-mode",
      durationSeconds: 3.4,
      kind: "mode",
      kicker: "Run mode 3 of 3",
      title: "Non-deterministic or LLM-driven",
      subtitle: "A real model leads the semantic work while Loop Engine keeps control.",
      caption: "A mode label without a physical model attempt is not model-led execution.",
      annotation: "Example: compare competing research plans, then return a structured recommendation for verification.",
      visual: {
        mode: "nonDeterministic",
        loopLabel: "Research planning Loop",
        steps: ["read bounded context", "deliberate with a real model", "return typed proposal"],
        control: "Tools, limits, approvals, history, and verification remain explicit."
      }
    },
    {
      id: "mode-comparison",
      durationSeconds: 4.5,
      kind: "comparison",
      kicker: "One choice per run",
      title: "Each Loop instance selects one mode",
      subtitle: "The graph and Canvas do not inherit one mode. Connected Loops may select different permitted modes.",
      caption: "A deterministic Loop can spawn a non-deterministic Loop, and the reverse is also valid when permissions allow it.",
      annotation: "Current Solution Canvas execution supports deterministic components. Other Solution modes fail preflight.",
      visual: {
        headers: ["Question", "Deterministic", "Hybrid", "Non-deterministic"],
        rows: [
          ["What leads?", "code or rules", "code", "real model"],
          ["Model involved?", "no", "only if needed", "yes"],
          ["Best fit", "repeatable work", "bounded ambiguity", "open semantic work"],
          ["Still controlled", "effects and limits", "effects and limits", "effects and limits"]
        ]
      }
    },
    {
      id: "loop-role-hierarchy",
      durationSeconds: 4.2,
      kind: "hierarchy",
      kicker: "Profiles organize purpose",
      title: "One Loop runtime, three role branches",
      subtitle: "Role, mode, profile, category, and graph relationship stay separate.",
      caption: "A spawned Loop is still the same runtime type. Its role profile states why it exists.",
      annotation: "Profiles are versioned behavior presets. They do not create another runtime class.",
      visual: {
        trunk: "Loop",
        branches: [
          { label: "Practitioner", role: "practitioner", items: ["reference and compact", "research", "solver", "verifier", "self-improvement and code execution"] },
          { label: "Intelligence", role: "intelligence", items: ["Context", "Code", "Runtime History and Solution", "User Feedback"] },
          { label: "Solution", role: "solution", items: ["atomic component", "pipeline", "router and fallback", "ensemble", "validator"] }
        ]
      }
    },
    {
      id: "practitioner-profile",
      durationSeconds: 4,
      kind: "steps",
      kicker: "Practitioner profile",
      title: "A Practitioner Loop decides what work is useful next",
      subtitle: "A simple presentation profile uses five steps. Runtime profiles may contain different steps.",
      caption: "The Loop repeats only while its loop condition is true and its budget allows more work.",
      annotation: "The reference nine-step profile remains available. Custom profiles are valid when bounded and versioned.",
      visual: {
        loopLabel: "Practitioner Loop",
        steps: ["Orient", "Decide next", "Plan how", "Act", "Verify"],
        repeatLabel: "not accepted: continue",
        exitLabel: "accepted: exit"
      }
    },
    {
      id: "spawned-loops",
      durationSeconds: 4.2,
      kind: "spawn",
      kicker: "Deliberation and delegation",
      title: "A Practitioner can spawn focused Loops",
      subtitle: "Each spawned Loop has its own profile, mode, typed contract, budget, and exit condition.",
      caption: "Private context stays isolated. Typed results return to the Loop that requested the work.",
      annotation: "The typed lifecycle manager exists. Standard hybrid and non-deterministic spawned executors are not complete.",
      visual: {
        starting: { label: "Starting Practitioner", role: "practitioner", mode: "nonDeterministic" },
        spawned: [
          { label: "Source research", role: "practitioner", mode: "nonDeterministic", relation: "SPAWNED_BY" },
          { label: "Schema check", role: "practitioner", mode: "deterministic", relation: "SPAWNED_BY" },
          { label: "Failure repair", role: "practitioner", mode: "hybrid", relation: "SPAWNED_BY" }
        ],
        returnLabel: "typed results return"
      }
    },
    {
      id: "shared-access",
      durationSeconds: 4,
      kind: "access",
      kicker: "Shared access",
      title: "Every Loop should access the same three shared groups",
      subtitle: "Typed service ports provide Intelligence Search and Retrieval, Web Research, and Custom Plugins.",
      caption: "Permissions decide which service operations are available. A run mode never expands authority.",
      annotation: "Implemented. Each Loop carries a permission-limited LoopRuntimeContext with exactly these three public groups.",
      visual: {
        loops: [
          { label: "Practitioner", role: "practitioner" },
          { label: "Intelligence", role: "intelligence" },
          { label: "Solution", role: "solution" }
        ],
        context: {
          label: "Static Architecture",
          items: ["Intelligence Search and Retrieval", "Web Research", "Custom Plugins"]
        }
      }
    },
    {
      id: "intelligence-overview",
      durationSeconds: 4,
      kind: "pillars",
      kicker: "Four persistent layers",
      title: "Intelligence is organized by what it contributes",
      subtitle: "Every intelligence operation is a Loop. Passive content is materialized only after selection and permission checks.",
      caption: "Runtime Memory is separate. It is temporary and lasts only for the current run.",
      annotation: "Search, select, retrieve, frame, invoke, replay, compare, and interpret are Intelligence Loop profiles.",
      visual: {
        pillars: [
          { label: "Context Intelligence", detail: "questions, methods, checks, formats", role: "intelligence" },
          { label: "Code Intelligence", detail: "versioned executable capability", role: "intelligence" },
          { label: "Run and Solution Intelligence", detail: "saved work, failures, comparisons", role: "intelligence" },
          { label: "User Feedback Intelligence", detail: "advice, corrections, constraints", role: "intelligence" }
        ]
      }
    },
    {
      id: "context-intelligence",
      durationSeconds: 3.5,
      kind: "intelligence-branch",
      kicker: "Intelligence branch 1 of 4",
      title: "Context Intelligence",
      subtitle: "Reusable questions and ways of thinking help a Loop examine the task from several angles.",
      caption: "Search returns a small typed reference. A Retrieved Context Intelligence Loop materializes the selected content.",
      annotation: "Imported prompts and skills remain candidates until independent review approves them.",
      visual: {
        branch: "Context Intelligence Loop",
        role: "intelligence",
        operations: ["search and rank", "retrieve", "frame for this task"],
        items: ["first principles", "missing information", "failure risks", "evaluation questions", "output contracts"]
      }
    },
    {
      id: "code-intelligence",
      durationSeconds: 3.5,
      kind: "intelligence-branch",
      kicker: "Intelligence branch 2 of 4",
      title: "Code Intelligence",
      subtitle: "A callable, package, repository, or tool becomes usable only through an exact versioned contract.",
      caption: "Discovery is effect-free. Invocation begins after selection, compatibility checks, and permission checks.",
      annotation: "Large bodies stay behind references until the selected Code Intelligence Loop needs them.",
      visual: {
        branch: "Code Intelligence Loop",
        role: "intelligence",
        operations: ["search", "select", "materialize", "invoke"],
        items: ["source identity", "version and digest", "typed ports", "effects", "tests", "license and dependencies"]
      }
    },
    {
      id: "run-solution-intelligence",
      durationSeconds: 3.6,
      kind: "intelligence-branch",
      kicker: "Intelligence branch 3 of 4",
      title: "Runtime History and Solution Intelligence",
      subtitle: "Saved work provides starting points, failures, repairs, measurements, and reusable Solution graphs.",
      caption: "Intelligence Loops search, replay, or compare exact saved records. Missing evidence remains visible.",
      annotation: "The architecture uses one public name for this branch. Legacy storage names need migration readers.",
      visual: {
        branch: "Run and Solution Intelligence Loop",
        role: "intelligence",
        operations: ["search history", "replay", "compare"],
        items: ["run graphs", "decisions", "failures", "repairs", "measurements", "Solution definitions"]
      }
    },
    {
      id: "user-feedback-intelligence",
      durationSeconds: 3.5,
      kind: "intelligence-branch",
      kicker: "Intelligence branch 4 of 4",
      title: "User Feedback Intelligence",
      subtitle: "User advice, corrections, priorities, constraints, approvals, and vetoes remain explicit.",
      caption: "A deterministic Loop can return exact guidance. An authorized model-led Loop can frame it for the current task.",
      annotation: "Interpretation never changes the original user record or grants a new permission.",
      visual: {
        branch: "User Feedback Intelligence Loop",
        role: "intelligence",
        operations: ["retrieve exact guidance", "interpret when authorized"],
        items: ["advice", "corrections", "sources", "priorities", "constraints", "approvals and vetoes"]
      }
    },
    {
      id: "solution-canvas",
      durationSeconds: 4.5,
      kind: "matrix",
      kicker: "What runs for a new input",
      title: "The Solution Canvas keeps several working routes",
      subtitle: "Each cell refers to a versioned Solution Loop. Typed edges connect the selected graph.",
      caption: "Selection, fallback, routing, and ensembles must be explicit Solution Loops, not hidden edge behavior.",
      annotation: "Implemented. SolutionSpec and Canvas now build or project one authoritative LoopGraphDefinition.",
      visual: {
        columns: ["Capture", "Extract", "Normalize", "Model", "Verify"],
        rows: [
          { label: "Route A", cells: ["browser", "table parser", "schema map", "boosted trees", "holdout"] },
          { label: "Route B", cells: ["HTTP client", "OCR parser", "rule map", "linear model", "holdout"] },
          { label: "Fallback", cells: ["saved files", "manual review", "repair", "baseline", "contract check"] }
        ],
        status: ["candidate", "working", "fallback"]
      }
    },
    {
      id: "canonical-dag",
      durationSeconds: 4.5,
      kind: "dag",
      kicker: "One graph authority",
      title: "Loops connect into one typed directed acyclic graph",
      subtitle: "Repetition stays inside a Loop. Edges carry values and relationships, not hidden work.",
      caption: "Starting, Spawned by, Queried by, Retrieved by, and Connected from describe different relationships.",
      annotation: "Implemented. Every vertex resolves an exact versioned and digest-bound LoopDefinition.",
      visual: {
        vertices: [
          { id: "task", label: "Starting Practitioner", role: "practitioner", x: 220, y: 360 },
          { id: "query", label: "Intelligence query", role: "intelligence", x: 650, y: 280 },
          { id: "item", label: "Retrieved intelligence", role: "intelligence", x: 1060, y: 280 },
          { id: "solution1", label: "Starting Solution", role: "solution", x: 650, y: 560 },
          { id: "solution2", label: "Connected Solution", role: "solution", x: 1060, y: 560 },
          { id: "formatter", label: "Output formatter", role: "solution", x: 1470, y: 560 }
        ],
        edges: [
          { from: "task", to: "query", label: "QUERIED_BY" },
          { from: "query", to: "item", label: "RETRIEVED_BY" },
          { from: "task", to: "solution1", label: "builds" },
          { from: "solution1", to: "solution2", label: "CONNECTED_FROM" },
          { from: "solution2", to: "formatter", label: "CONNECTED_FROM" }
        ],
        terminal: { label: "Typed result value", type: "model_report@1", from: "formatter" }
      }
    },
    {
      id: "static-architecture",
      durationSeconds: 4.2,
      kind: "services",
      kicker: "Three shared groups",
      title: "Static Architecture has three public groups",
      subtitle: "Every Loop can call these groups through typed, permission-limited service requests.",
      caption: "The groups provide reusable access. They are not additional operational nodes.",
      annotation: "Other runtime mechanics stay internal and do not appear as peer architecture components.",
      visual: {
        center: { label: "Any Loop", role: "practitioner" },
        groups: [
          "Intelligence Search and Retrieval",
          "Web Research",
          "Custom Plugins"
        ]
      }
    },
    {
      id: "worked-task-overview",
      durationSeconds: 4.2,
      kind: "workflow",
      kicker: "Worked task",
      title: "From public websites to a tested model",
      subtitle: "The task combines web research, PDF extraction, data engineering, model building, and verification.",
      caption: "Every executable step is a Loop with its own typed ports, selected mode, conditions, and history.",
      annotation: "This is the proposed first end-to-end proof task. It is not a completed benchmark claim.",
      visual: {
        steps: [
          { label: "Discover sites", role: "practitioner" },
          { label: "Download PDFs", role: "solution" },
          { label: "Inspect structure", role: "practitioner" },
          { label: "Extract records", role: "solution" },
          { label: "Normalize data", role: "solution" },
          { label: "Build candidates", role: "practitioner" },
          { label: "Verify and repair", role: "practitioner" },
          { label: "Canvas compiler", role: "practitioner" }
        ]
      }
    },
    {
      id: "worked-sources-pdfs",
      durationSeconds: 4.2,
      kind: "worked-stage",
      kicker: "Worked task, stage 1",
      title: "Find reliable sources and inspect every PDF",
      subtitle: "The Practitioner queries Intelligence before selecting search, download, and parsing capabilities.",
      caption: "Discovery remains effect-free. Network and file operations start only after exact permission checks.",
      annotation: "Different PDFs may require different extraction routes. One parser is not assumed to fit every document.",
      visual: {
        loops: [
          { label: "Source discovery", role: "practitioner", mode: "nonDeterministic" },
          { label: "PDF download", role: "solution", mode: "deterministic" },
          { label: "Document inventory", role: "solution", mode: "deterministic" },
          { label: "Structure inspection", role: "practitioner", mode: "hybrid" }
        ],
        questionsLabel: "Context and User Feedback questions",
        questions: ["Which sources are authoritative?", "Which dates and entities are in scope?", "Are tables, scans, and footnotes handled?"]
      }
    },
    {
      id: "worked-data-models",
      durationSeconds: 4.2,
      kind: "worked-stage",
      kicker: "Worked task, stage 2",
      title: "Build trusted data before building models",
      subtitle: "Selected Code Intelligence Loops extract, normalize, validate, and assemble model-ready records.",
      caption: "Competing model candidates remain separate until an independent verifier compares them.",
      annotation: "Runtime History and Solution Intelligence supplies known failures, repair patterns, and evaluation geometry.",
      visual: {
        loops: [
          { label: "Extract records", role: "solution", mode: "deterministic" },
          { label: "Normalize schema", role: "solution", mode: "deterministic" },
          { label: "Leakage check", role: "practitioner", mode: "deterministic" },
          { label: "Model candidates", role: "practitioner", mode: "nonDeterministic" }
        ],
        questionsLabel: "Intelligence questions",
        questions: ["What is missing or duplicated?", "Can future data leak into training?", "Which baseline and split prove useful performance?"]
      }
    },
    {
      id: "worked-verify-record",
      durationSeconds: 4.5,
      kind: "verify-compile",
      kicker: "Worked task, stage 3",
      title: "Verify, repair, compile, and record",
      subtitle: "A deterministic verifier accepts a candidate or starts a failure-specific repair Loop.",
      caption: "The selected Solution graph enters the Canvas. The same ordered events power live view and playback.",
      annotation: "A report explains what ran. It does not turn one successful task into a general success rate.",
      visual: {
        candidate: { label: "Candidate output", role: "practitioner" },
        verifier: { label: "Deterministic verifier", role: "practitioner" },
        accepted: { label: "Solution Canvas", role: "solution", relation: "accepted" },
        repair: { label: "Repair Loop", role: "practitioner", relation: "failed check" },
        runHistory: {
          label: "Run History",
          items: ["ordered Loop events", "typed values", "model attempts", "effects and approvals", "live view and playback"]
        }
      }
    },
    {
      id: "practitioner-improvement-profile",
      durationSeconds: 5,
      kind: "final",
      kicker: "Practitioner task profile",
      title: "Self-improvement uses the same Practitioner Loop",
      subtitle: "A Practitioner can review a bounded run population and stage candidates. Independent review remains separate.",
      caption: "The architecture is clear. The remaining work is to consolidate the runtime and prove one real end-to-end task.",
      annotation: "Remaining gaps: full value schemas and built-in hybrid or non-deterministic Solution executors.",
      visual: {
        practitionerTasks: ["research", "build and test", "verify and repair", "self-improvement"],
        reviewLabel: "Independent review decides promotion",
        statements: [
          "Every executable graph vertex is a Loop.",
          "Each Loop selects one mode and follows one versioned definition.",
          "The Solution Canvas runs. The Run History explains what happened."
        ]
      }
    }
  ]
};

export default showcaseData;
