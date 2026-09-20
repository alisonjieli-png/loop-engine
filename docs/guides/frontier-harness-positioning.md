# Frontier harness positioning

Kind: product language and technical-option exploration, pending owner approval.

The owner requested all relevant options after distinguishing public wording
from programming language and runtime. The options below cover both, plus
configuration and integration contracts. They do not rename the repository,
add a runtime, or approve publication.

## Recommended direction

Use Baltor as a candidate public brand and explain the product as an
intelligence and control layer around the harnesses a customer chooses.
Loop Engine remains the current engine and repository name.

For technical readers, "frontier-model workflows" describes the intended
environment. It must not imply that this product is itself a frontier model,
that it outperforms another harness, or that every frontier provider is qualified.

## Copy candidates

| Direction | Heading | Supporting explanation |
|---|---|---|
| Plain, recommended starting point | Give your harness the context for its task. | Select relevant material, run work in your own environment, and inspect what was verified. |
| Technical | An intelligence and control layer for frontier-model workflows. | Use versioned context, explicit permissions and recorded outcomes around your selected model and harness. |
| Developer infrastructure | Build agent workflows with scoped context and explicit permissions. | Keep retrieval, execution and verification behind replaceable interfaces, with one owning Loop runtime. |

## Product-positioning alternatives

| Position | Meaning | Fit and caution |
|---|---|---|
| Intelligence for agent harnesses | The service supplies task-relevant context and reusable material to existing clients. | Closest to the first hosted product. Explain qualification and local execution. |
| Intelligence and control for frontier-model workflows | The system combines context delivery with task authority, history and verification. | Recommended technical positioning, with a plain-English explanation. Frontier describes intended model workflows, not benchmark leadership. |
| A local-first agent harness | The product is the main interface that drives a model and its tools. | Valid for a future complete local experience, but may obscure that the first release reuses native harnesses. |
| A runtime for agent workflows | Developers define assignments and connect tools, models and stores through contracts. | Accurate engine-level framing; less immediately clear to a non-developer buyer. |
| An agent control plane | The system manages scope, routing, resource limits, records and acceptance around execution. | Useful enterprise architecture language. It implies substantial operations and lifecycle guarantees that still need qualification. |
| Adaptive retrieval and context infrastructure | Search, ranking, feedback and materialization are the primary product. | Useful for the retrieval service, but actual learned improvement must be measured before claiming it. |
| A harness orchestration platform | The product selects and supervises several native harnesses. | Fits the longer-term portfolio direction. Runtime selection and native context use are not yet fully qualified. |
| Verification infrastructure for agents | Independent checks and outcome records are the primary value. | A defensible specialist direction when exact verification scope is stated; not a guarantee that every answer is correct. |
| Reusable intelligence platform | Context, code, history and human guidance become governed reusable resources. | Broad enough for the four layers; needs concrete examples so it does not sound abstract. |
| An agent operating system | The product suggests a complete execution and resource environment. | Too broad for the present release. It risks implying isolation, device control and lifecycle coverage that are not established. |

These positions are alternatives, not ten simultaneous homepage claims.
Choose one primary explanation and place the rest in technical documentation
where the relevant behavior is implemented and tested.

## Brand choices

| Choice | Use |
|---|---|
| Baltor publicly, Loop Engine internally | Recommended candidate. Use the existing owner-held domain while retaining current repository, command, import and contract identities. |
| Loop Engine everywhere | Keeps one name, but existing software uses that name and the exact .com and .dev are registered. |
| Baltor powered by Loop Engine | Makes the relationship explicit on technical and About pages. Avoid making visitors learn two names in the headline. |
| A new public name | Consider if naming review rules out Baltor or user testing shows persistent confusion. Do not restart the implementation to change a brand. |

The near-name Balto already operates an AI product. None of these choices is
a legal-clearance conclusion. Domain ownership alone does not settle naming
rights or customer confusion.

These are proposed positioning statements, not an availability announcement.
Any published version needs a visible development-stage label until the
corresponding user journey is qualified. A paid service claim needs the hosted
account and billing evidence as well.

## Terms to keep distinct

| Term | What it should mean in our copy |
|---|---|
| Model | The selected reasoning or generation provider, under an exact route and authority. |
| Native harness | The existing process that manages its model interaction, tools and context. |
| Loop Engine | The current runtime and contracts governing assignments, authority, records and acceptance. |
| Baltor | Candidate public product brand, not a new runtime class or intelligence layer. |
| Self-improvement | Proposed changes evaluated and independently accepted, not automatic truth or guaranteed continuous gains. |

Anthropic describes a harness through environment preparation, persistent
progress and end-to-end checks. LangChain uses the term for the non-model
machinery around an agent. Pi calls itself a minimal agent harness. These
sources support the vocabulary, not a claim that Loop Engine has implemented
or qualified every behavior they discuss.
[Anthropic](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents),
[LangChain](https://www.langchain.com/blog/the-anatomy-of-an-agent-harness),
[Pi](https://pi.dev/).

## Implementation language and runtime choices

| Choice | What changes | Recommendation |
|---|---|---|
| Python domain with a TypeScript website and selected adapters | Preserve the existing domain, catalogue, authority and verification code. Use a web interface and separate adapters where their libraries require it. | Recommended starting point. |
| Python-only application | Keep the service and local command in one language; render a simpler interface from the server. | Suitable for a small operator-facing release or local tool. It need not become the permanent frontend constraint. |
| TypeScript-first server and runtime | Share types with the website and integrate JavaScript-native harnesses directly. | A valid new-project choice, but rewriting the current Python authority would add migration and regression risk. |
| Python service with a Go local worker | Keep domain rules in Python and put selected process or transport operations behind a compiled worker contract. | Consider only for a measured packaging or lifecycle need. It adds another implementation and release boundary. |
| Python service with a Rust local worker | Isolate selected native process, resource or filesystem mechanisms behind the same contracts. | A possible later systems boundary, not a necessary rewrite for the first release. |
| Java, Kotlin or C# integration | Add an adapter for an organization already using those ecosystems. | Demand-driven interoperability, not an additional first-release platform requirement. |

AutoRAG's reviewed package uses TypeScript and requires Node.js 24 or newer.
That supports a separate adapter process; it does not require converting the
Python service. A different-language adapter still needs exact schemas,
capability negotiation, cancellation, authority and accounting.
[Pinned package](https://github.com/Marker-Inc-Korea/AutoRAG/blob/be20a32200dc5f5b130af01684939c66fc33fbc5/package.json).

## Configuration and contract language choices

| Form | Appropriate purpose | Boundary |
|---|---|---|
| Typed Python objects | In-process application and adapter composition. | Current contracts remain authoritative; validation precedes effects. |
| Versioned JSON | Requests, results, references, manifests and portable protocol messages. | Recommended interchange representation with explicit schema versions. |
| YAML | Human-authored settings and workflow descriptions. | Compile and validate into the same canonical records; do not create another runtime or infer permissions from prose. |
| TOML | Compact application and package configuration. | Useful where the host ecosystem already uses it; avoid a duplicate settings authority. |
| Natural-language requests | User goals, explanations and candidate plans. | A model may propose structure, but text cannot grant authority or activate code. |
| A custom domain-specific language | A later ergonomic authoring layer over existing contracts. | Build only if it removes a demonstrated authoring problem. Do not make it a first-release dependency. |

These formats can coexist when they compile to one authority. They should not
each define their own task semantics or silently reinterpret older records.

## Execution and connection choices

Use direct calls for small trusted operations. Use a separate process when a
native harness or different-language engine needs isolation or its own
lifecycle. Use the existing web or Model Context Protocol surface for remote
clients. A message queue or a binary remote protocol is a later deployment
choice, not a requirement for every atomic operation.

The canonical Loop remains the outer authority. LangGraph can be an optional
implementation detail of an adopted component, but is not required. Introduce
another orchestration backend only when it replaces identified responsibilities
and preserves exact state, retries, cancellation, budgets and acceptance.

## Proposed first combination

Baltor as a candidate public brand; an intelligence and control layer as the
product explanation; Loop Engine as the existing runtime; Python domain code;
TypeScript for the website and JavaScript-native adapters; versioned JSON for
interchange; optional validated YAML for authoring; local customer execution.
The owner still chooses the public brand. Live integrations and learning gains
remain separately qualified behavior.

## Wording to avoid for the present release

Do not use "frontier-grade", "state of the art", "autonomous employee",
"continuously gets smarter", "guaranteed outcomes", or "everything stays
local" as present capability claims. The current evidence does not establish
those statements. "Harness of harnesses" is also a poor opening explanation:
it hides the practical distinction between supplying intelligence, governing
a task and running a native harness.

The public How it works page should begin with the customer's task and where
execution happens, then explain context selection, preparation, work,
verification and retained outcomes. Detailed runtime taxonomy belongs in the
architecture reference, not in the first sentence a new visitor reads.
