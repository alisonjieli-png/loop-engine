# Component interfaces and the flow of intelligence

Date: 2026-09-18. Owner direction: document how each component interfaces
with the others, how intelligence querying happens, how code reuse happens,
how the other intelligence layers are consumed, how a harness inside a Loop
uses plugins, tools, and context to reach the core components, the query
and retrieval engines, and the intelligence layers; and look for
inconsistencies and opportunities. This record is written from the source
as it stands after commit `b1fbcdc` and names the module at every hop.

## One solve, hop by hop

```text
A task enters and leaves
├── intake: templates/intake captures the instruction text, digest, and source refs
├── request: core/adaptive_practitioner_records.AdaptivePractitionerRequest binds task,
│   mode, workspace, supervision, verification policy, and dependencies
├── fast path: core/adaptive_practitioner_deterministic tries registered resolvers
│   inside a Practitioner Loop; a verified result ends the run with zero model calls
├── orientation and steps: core/adaptive_practitioner runs the step profile; each step
│   asks through strings/question_engine forms with a registered response contract
├── intelligence: core/intelligence_layers.query_intelligence fans one need across the
│   four layers through core/retrieval.Retriever inside a Loop and returns references
├── capabilities: core/capability_directory serves surfaces (search, string bank,
│   contract and logic registries, model gateway, supplied surfaces) with cost capture
├── model calls: core/model_gateway resolves a route, renders the packet, admits or
│   repairs the response, and accounts tokens; core/model_call_contract types the request
├── effects: loop/effect_approval binds each effect to an approval; workspaces confine
├── verification: core/independent_verification runs an isolated probe and issues a report
├── review: core/independent_failure_review classifies a failed check and confirms it
├── records: core/run_history, core/model_call_records, core/operation_cost_records
└── publication: code_nodes/solutions_space adds the verified canvas as a member
```

## How intelligence is queried

`query_intelligence(IntelligenceSearchRequest)` receives the need and a
mapping of layer name to records, normalizes the records, wraps each as a
classified record with its layer, and runs one `Retriever.search` inside a
Loop (`as_loop`). It reports every layer it could not query as unqueried
and never skips one silently. The result is a list of hits with layer,
identity, and score; the body is not loaded. Materialization is a second
step through `loop/intelligence_loops.serve_record_as_loop`, which serves
the full record only after selection and permission checks. The catalog
package answers the same question for stored records with
`IntelligenceQuery` (layers, source collections, artifact kinds,
lifecycle, namespaces, attributes) through any adapter, and the composite
catalog refuses conflicting materializations of one identity.

## How code reuse happens

```text
Reuse of code
├── an execution that succeeded produces a reuse opportunity (core/reusable_capability_flywheel)
├── an assessment with verified source success authorizes a candidate registration
├── the candidate keeps the observed operation family and the exact artifact digest,
│   or a generalization record that binds source and candidate digests
├── admission moves it to a qualified capability with a qualification digest
├── a qualified capability is a DeterministicTaskResolver the fast path can try
└── every use writes reuse evidence and an operation cost record
```

The fast path (`run_deterministic_attempt`) asks each resolver whether it
supports the task, runs a supporting one inside a Practitioner Loop, and
accepts only a result whose `verified` is true; otherwise the trace names
the failure and recommends semantic orientation. The text conformance
resolver is the first packaged resolver; the specialist resolver is the
first trained one, and it never reports `verified` true.

## How the layers are consumed

| Layer | Serve | Search | Frame or invoke | Where the body loads |
|---|---|---|---|---|
| Context Intelligence | `serve_record_as_loop` | the Retriever over string records; the string bank surface | prompt resource bundle slots | after selection |
| Code Intelligence | capability directory `get` and `run`; resolvers | the code node registries; the same Retriever | invocation through the directory with policy | at invocation, inside a Loop |
| Runtime History and Solution Intelligence | run history load; solutions space | replay and compare; the same Retriever over run records | stage assistance material | at replay |
| User Feedback Intelligence | the advice store | consult and advice_for | typed task feedback slots | at consult |

Runtime Memory is separate: `runtime_memory_write` refuses without the
run's board, so no note lands outside its run.

## How a harness inside a Loop reaches the core

A discrete cognitive or act step Loop node may run on the custom
Practitioner or on a native harness (OpenCode, Codex, Pi, and the other
registered recipes). Either way the owning Loop provides what the step
receives:

```text
What a step receives
├── context files and instruction files, by exact revision, through step provisioning
│   (core/opencode_step_provision, core/step_content, core/opencode_step_layers)
├── tools and plugins through adapters: core/mcp_adapter and core/mcp_sdk_transport for
│   MCP servers, core/custom_endpoint for OpenAI-compatible endpoints, the plugin
│   discovery for project plugins; each is a capability surface with a handshake
├── intelligence through the capability directory's search and get endpoints, which
│   cross the Loop envelope, never a bare store call
├── the model gateway for any model call, with the route, contract, and suggested output
├── effect approval for every file, network, or external action
└── the run's Runtime Memory board for notes scoped to the run
```

The native harness receives the same semantic packet the custom path
renders; its completion is an observation, and the owning Loop performs
the semantic and task checks.

## Inconsistencies found

1. `default_directory` has no runtime caller. The solve path constructs
   its own dependencies, so the standard directory with its surfaces,
   fallbacks, and now cost capture is exercised by checks but not by a
   live solve. Opportunity: the solve request's dependencies should be
   built from a directory so every capability call is captured and every
   supplied surface is reachable (roadmap S-2.2).
2. The string bank (`core/store_serve.SolverStore`) appends to an
   organization overlay file directly, outside the catalog contract, and
   question forms live in code. This is the file-edit path the storage
   decision retires (S-2.10).
3. Two grid vocabularies exist: `generation/model/campaign.py` search
   strategies and the new `ParameterSpace` strategies. The optimizer uses
   two names drawn from the campaign vocabulary; the node grid uses none.
   Opportunity: one strategy vocabulary owned by one module, with the
   optimizer, the node grid, and the campaign naming it (S-2.4).
4. Versioning semantics exist twice: `memory/storage` keeps versions per
   record for the four-memory demonstration, and `catalog/versioning` keeps
   revisions for any catalog record. The four-memory store should become a
   catalog adapter or read through the catalog (S-2.10).
5. The reuse evidence label is computed but not consulted by the Retriever
   at retrieval time, so an outcome changes what a record is worth without
   yet changing what is retrieved. Opportunity: a ranking term from the
   posterior, measured on the fixture suite (S-1.12).
6. The implementation decision is written by conformance escalations but
   the Practitioner's route step does not consult it before a model call;
   the efficiency review is a record with no step that writes it. Both
   are the S-2.1 wiring.
7. Cost capture covers directory calls; model gateway calls carry token
   accounting but do not write an operation cost record. One record per
   physical model call closes the gap (S-1.5 follow-up).
8. The shared memory writer identity is a parameter. Inside the service
   surface it must be the authenticated tenant, never a request field
   (S-4.2 follow-up).
9. The dependency ratchet keeps `core` from importing more of
   `code_nodes`, and the surface registration inversion respects it, but
   the solve runtime in `code_nodes` still reaches back into `core` for
   nearly everything. The layering question the owner raised stays open.

## Opportunities

- Build the run's capability directory from one `SurfaceRegistration` list
  per deployment profile, so demo, self-hosted, and hosted runs differ only
  in which surfaces and stores are registered.
- Route every model call through `ModelCallRequest` so non-text kinds and
  typed-decision models enter through the same boundary as text.
- Serve question forms and prompt resources as catalog records so a
  hosted tenant can version and audit them.
- Make the efficiency review the first step of every model-led step and
  the implementation decision the gate before the call.
