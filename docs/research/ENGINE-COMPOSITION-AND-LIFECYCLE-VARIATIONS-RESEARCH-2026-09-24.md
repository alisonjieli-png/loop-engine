# Engine composition and lifecycle variations: research record

Kind: dated research record. It proposes; it changes no code, record, check
or roadmap entry, and it grants no authority. The roadmap stays the only task
authority.

Date: September 23 and 24, 2026 (New York time). Third version, written on
September 24 after the adversarial verifications of that morning. The first
version is kept beside this file as
`ENGINE-COMPOSITION-AND-LIFECYCLE-VARIATIONS-RESEARCH-attempt-1-2026-09-24-0153.md`.

Intended path: `docs/research/ENGINE-COMPOSITION-AND-LIFECYCLE-VARIATIONS-RESEARCH-2026-09-24.md`.

Base: `origin/main` at `e6346075` (September 24, 10:15). Nothing under `src/`
changed between `3d48a36c` (09:39) and `e6346075`; the one new commit adds a
daily research watch workflow and its summary tool (ran: `git diff --stat`).
Every repository probe that this record relies on and that could run offline
was run again on an export of `e6346075` (section 7).

It records the research behind the
[functional component standard](../architecture/FUNCTIONAL-COMPONENT-STANDARD.md)
and extends two records that are already on `main`: the
[functional engine wrapping research](FUNCTIONAL-ENGINE-WRAPPING-RESEARCH-AND-IMPROVEMENTS-2026-09-23.md)
and the [ecosystem edge map](ECOSYSTEM-EDGE-MAP-2026-09-23.md). It does not
repeat their content, and it does not repeat the component standard review of
September 23, which it credits where the standard uses its findings.

Nothing in any repository or worktree was changed. No model was called, no
provider was written to, and no secret was read.

Evidence labels, used on every finding:

- **ran**: a probe or check was executed. "ran, writer" means it ran for this
  record on an export of `e6346075`; otherwise the research line or verifier
  that ran it is named in brackets.
- **source**: read in repository source or in an outside primary source whose
  version and date are given.
- **claim**: stated elsewhere and not rechecked for this record.

## 1. Summary

1. The owner asked on September 23 for functional components with several
   engines behind a typed edge, tests alone and in groups, one index of
   names, containerized or wrapped outside projects beside our own variation,
   and selection of engines in real time. Most of the vocabulary already
   exists as typed records in `core/engines/`, and almost none of it runs: 45
   slots, 38 candidate, 7 planned, 0 active; no module outside the package
   writes an engine record; no shared selector exists (ran, writer).
2. The index already drifts. Library ingestion keeps a second `EngineSlot`
   class and its own selection record; two tool families keep their own
   selection records; three engine identifiers name two implementations each;
   four working slots are missing from the catalogue while the index reports
   zero findings (ran, writer; source).
3. Composition happens at two levels. Fallback, cascade, routing and shadow
   comparison are features of one slot's policy. Pipeline, branches and
   merge, race, partitioned, fused and router forms need a composite engine in
   a strategy slot above the slots it combines. The Loop runtime's concurrent
   join is parked, it is not a race, and thread branches cannot be stopped
   (ran [selection line and its verifiers]).
4. Four live defects break an invariant that the repository states, and each
   has a known-wrong case that ran on `e6346075`: the model gateway moves to a
   second route after an inconclusive evaluation when route change is
   permitted; a protocol request whose header and body name different
   revisions is served under the older revision with a metered read; model
   token streams return success after an in-band provider error; and a model
   call's timeout bounds each socket read, not the call (ran, writer).
5. The lifecycle mechanisms exist as islands reached only from the self-test,
   and several record statements are false or permissive: hibernation records
   steps it did not perform and quiesces with a signal whose default action
   ends the process; an expired work lease can still commit, and its times
   come from the holder; a Docker cleanup block is lost between adapter
   objects on the live solve path (ran [lifecycle line and both verifiers]).
6. Change is not recorded as change. A rejected catalogue release is rebuilt
   at every check, the health answer never names it, and a restart refuses to
   start although the previous release is stored and verified; a retry by
   request identity is refused after a catalogue swap and a new identity is
   metered again (ran, writer; first found by the activation line and its
   verifier).
7. Semantics at the edges are weaker than the records suggest: the exact
   contract match mode treats true, 1 and 1.0 as equal; JSON Schema `format`
   is not asserted, a pure engine fetches a remote schema reference, and an
   unknown dialect is read as the newest; one time rule answers differently on
   Python 3.10 and 3.12; two store engines drop unknown keys (ran, writer and
   the lines named in section 6).
8. Selection records accept decisions that break the design: a decision can
   overturn the host's declared order with no evidence; the propensity is not
   tied to how the choice was made; an exact pin cannot be expressed; a pin
   can be dropped by the next decision (ran, writer).
9. Outside claims mostly hold in primary sources, with corrections: DataFusion
   pushdown answers are work splits, not compatibility verdicts; expiry is not
   final in every lease system; OpenFeature's `DEFAULT` reason means a
   pre-configured value; NVIDIA Triton keeps the old model after a failed
   reload only in a mode it does not recommend; Temporal's version statuses
   are inactive, current, ramping, draining, drained and created (source,
   verifiers).
10. Twenty-six discriminating qualification trials, each with a known-wrong
    case, are listed in section 9. None needs a model call. Twenty-four have
    a fixture form that can run on every push; five also have, or only have,
    a release or live drill; one waits for a live concurrency owner in the
    Loop runtime.

## 2. Where these mechanisms sit

The complete classification comes first, as `AGENTS.md` requires.

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

Every variation below is an internal mechanic that a classified Loop uses. A
composition whose parts need their own goal, authority, acceptance or Run
History identity is a Solution composition of Loops, never an engine.

```text
Variation families, and where each lands
├── Wrapping: how an implementation sits behind an edge
│   └── engine slot, engine adapter, Baltor-native engine, wrapper layer
├── Selection: which engine serves this invocation
│   └── selection mode (how many serve) and selection basis (pinned, preferred, automatic)
├── Composition: how several engines make one answer
│   ├── selection level: fallback, cascade, routing, shadow comparison
│   └── engine level: composite engine in a strategy slot
├── Lifecycle: how instances start, are shared, change and stop
│   └── call pattern, instance lifetime, instance owner, engine lease,
│       owned resource record, engine availability snapshot
├── Change: how a new configuration or engine takes over
│   └── binding facts (desired, prepared, routable, observed, rejected),
│       engine swap and its swap rule, swap qualification
├── Support and semantics: what an engine promises per request
│   └── required and advisory fields, compatibility verdict, work split,
│       validation profile, conversion declaration, stream semantics
├── Isolation and execution: where and how the code runs
│   └── execution fields; the process_confinement and workspace_backend slots
├── Testing: how an engine and a group are proven
│   └── conformance kit, composition test, journey test, lifecycle drill
└── Rule writing and names: how the standard itself stays checkable
    └── statement identifiers, one key word, named checks, one term per concept
```

## 3. What this record is built from

| Source | Revision read | Verifier verdict, in short |
|---|---|---|
| Repository grounding line | `56639ee6` | Counts confirmed on two revisions. Corrections: a ranking engine (`resolve_preference`) and a harness selector exist; the settings refusal must use typed settings records, not key names; the DataFusion mapping was refuted; the line missed the committed wrapping research and the parked Loop scheduling vocabulary |
| Testing line | `56639ee6` | Two verifiers, the second on `2658b7bb`. Term cap, store key shapes, installer leftovers, layout rows and crash typing confirmed. Corrections: the served search already breaks ties by identity; the served policy gap was already recorded in `SEARCH-QUALITY.md`; `read` and `fstat` faults escape untyped; the qualification record has no producer field; a kit report record already exists; interaction labels cannot generate kit sections; a scheduled workflow now exists; the Pi extension is a second separately deployed client |
| Selection and composition line | `56639ee6` | Two verifiers, the second on `2658b7bb`. Exact pins, propensity and the parked join confirmed. Corrections: the declared order can be overturned without evidence; the live gateway already runs an evaluator-gated cascade and breaks the inconclusive rule; pins are lost across decisions; composites must be compared with `loop_graph_definition/v2` and the planned `ModelCallStrategy`; the race and Solution composition rest on parked modules; package name C1 is taken; noise makes comparisons futile rather than letting a worse engine pass |
| Lifecycle and isolation line | `56639ee6` | Two verifiers, the second on `2658b7bb`. Hibernation false steps, work lease expiry, ledger gaps and residency confirmed. Corrections: quiesce by SIGUSR1 ends the process; a graceful stop cannot reach the sandboxed process through the owned group; the wait is not a stop confirmation; work lease times come from the holder; existing records (`ModelRouteAvailabilitySnapshot`, `overnight_residency/v1`, `DockerResourceLimits`) should be extended; condition, generation and resource claim collide; the Triton claim holds only in POLL mode |
| Rule and names line | `231f51bb` | Two verifiers, the second on `2658b7bb`. Rule text and vocabulary tests confirmed. Corrections: S-6.84 is on `main`; the statement check prototype missed five evasions; some named existing checks do not test their statement; the rule text shifted authority to `terminology.yaml`; "containerize" was read as a refusal; four library slots make "every component has one slot" false today |
| Protocol revisions line (attempt 5) | `e8069610` | Its verifier's probes (`vmr-work`) reproduce the era classification defect; the writer ran them again on `e6346075` |
| Validation, conversion and streaming line | `f6a7fb2c` | Its verifier's probes (`vvc-work`) reproduce the format, reference, time, count, canonical form and stream findings, and add a lone surrogate, schema cost and replacement growth |
| Selection, activation and transition line | `e8069610` | Its verifiers' probes (`verify-at`) reproduce A to G and add a restart after a rejected release, the swap with real release-following grants and worker shares with the default pool |
| Qualification tools line | `f6a7fb2c` | Its verifier's probe (`verify-qt`) reproduces the trickled model call in buffer and stream modes and the accounting labels |
| Component standard review | `da5db8aa` | Proposed fourteen rules and a `selection_basis` field; its writer trial found the executable bit lost by the confined writer; its gaps G1 to G14 are credited in the standard |

## 4. The variations

### 4.1 Wrapping: how an implementation sits behind an edge

| Variation | What it separates | Primary source, version and date | Where it lands | Verdict | Label |
|---|---|---|---|---|---|
| Ports and adapters | The application from its run-time devices; "a technology-specific adapter converts it into a usable procedure call" | Cockburn, "The Hexagonal (Ports and Adapters) Architecture", read September 24, 2026 | Edge contract is the port; each engine is an adapter; a kit's fixture engine is the test adapter | adopt as the explanatory frame | source (writer, first version) |
| Semantic translation (anti-corruption layer) | Two subsystems "that don't share the same semantics" | Microsoft Architecture Center, page dated May 28, 2026 | The engine adapter translates; no outside type crosses the edge (LE-EDGE-007) | adopt | source |
| Strangler fig | Gradual replacement behind a facade that shifts requests | Microsoft Architecture Center, page dated May 29, 2026 | Slot selection moves work from one engine to another by host policy | adopt as the replacement procedure | source |
| Provider and factory | An implementation from its configured instances | Backstage backend services, v1.55.1 (September 21, 2026): plugin and root scopes, root services depend only on root services, circular dependencies stop the backend, duplicate installations from version ranges | The slot's factory table; `ADAPTER_FACTORIES` pairs a settings record with each kind | adopt | source |
| Driver, dispatch and hooks | One plugin per name; a subset chosen per call; every plugin under a name | stevedore 5.9.1 (August 20, 2026), commit `93f5914d`: `DriverManager` raises `NoMatches` and, by default, `MultipleMatches`; `NameDispatchExtensionManager` filters per call; exceptions in `map` are "logged and ignored" unless `propagate_map_exceptions=True` | Driver is one_of, dispatch is set_of, hooks are the proposed all_of | adopt the mapping; reject the dependency and its swallowed exceptions | source |
| Wrapper layers around one call | Ordered, around-call layers | pluggy documentation (registration order decides, `firstresult`); the repository's layered harness wrappers | Wrapper layers with declared control ownership, inside one installation | adapt; order is declared, never registration order | source (component standard review) |
| Composite engine | An outer capability from its internal graph | Outside draft only | A strategy slot above nested slots; the composition is the descriptor's capability record | adapt | claim for the draft; source for the nesting rules |
| Backend partitioning and fusion | Parts of one request assigned to different implementations | ONNX Runtime 1.30.0 (September 10, 2026): `GetCapability` per subgraph; `AddNodesToFuse` forbids an unsupported node on a path between fused nodes; CPU fallback on by default; assignment recording off by default | Partitioned and fused composite forms, with a declared residual and recorded assignment | adapt; reject the silent defaults | source |
| Controller and worker | Resource preparation from frequent execution | Ray Serve (Ray 2.58.0, August 23, 2026): settings that keep replicas and settings that restart them; `max_ongoing_requests` default 5 | Preparation at the slot's binding phase (LE-INSTANCE-015); change classes for settings | adapt | source |
| Desired-state reconciliation | Desired spec from observed status | Kubernetes API conventions (`03ffbd01`, July 14, 2026): `observedGeneration`; "conditions are observations and not, themselves, state machines"; level-based, not edge-based | Binding facts in the bindings report (LE-STATUS-006); sequence numbers, not "generations" | adopt | source |
| Sidecar | A separate lifetime shared by many callers | Dapr 1.18 (runtime v1.18.4, September 9, 2026): pluggable components started before the runtime; conformance for Beta, certification for Stable | the `local_service` invocation mechanism; readiness as an availability snapshot | adapt; a sidecar never holds authority | source |
| Subprocess plugin | Address space and crash isolation | HashiCorp go-plugin v1.8.0 (April 29, 2026): "only designed to work over a local [reliable] network"; the magic cookie "is not a security measure, just a UX feature"; a killed client "cannot be started again" | `supervised_subprocess`; a handshake proves compatibility, never authorization; a restart is a new instance identity | adopt | source |
| WebAssembly component | Exactly the linked imports and opened folders | Wasmtime 49.0.0 (September 21, 2026): an instance can do only what "it has been explicitly linked with"; `wasmtime-wasi` denies all addresses by default; fuel is deterministic, epochs cost "around a 10% slowdown" | A later engine kind only with its kit (LE-ISOLATE-007) | watch | source |

### 4.2 Selection: which engine serves an invocation

| Variation | Primary source, version and date | Lesson taken | Rejected part | Label |
|---|---|---|---|---|
| Pinned for a whole run, upgrade only at a boundary | Temporal API `46ee8b82` (September 8, 2026), server 1.32.0, Python SDK 1.33.0: a pinned workflow stays on its version "until completion" and "Patching is not needed"; pinned overrides are inherited by the workflows a pinned workflow starts, by its retries and by continue-as-new and cron runs; version statuses are inactive, current, ramping, draining, drained and created | Pin lifetime and inheritance (LE-SELECT-008); ramps sticky by task identity; draining before archiving, stated as an exception to "a deprecated engine is never an initial choice" (LE-SELECT-019) | The activity exception that sends part of a pinned run to the current version | source |
| Named selection policies and a delegate | ONNX Runtime 1.30.0: seven named device policies since 1.22 and a delegate returning at most eight devices | Ranking objectives and ranking engines | Silent CPU fallback | source |
| Feature flag providers and a composite provider | OpenFeature specification v0.9.0 (July 29, 2026): reasons STATIC, DEFAULT, TARGETING_MATCH, SPLIT, CACHED, DISABLED, UNKNOWN, STALE, ERROR, where DEFAULT means "fell back to a pre-configured value (no dynamic evaluation occurred or dynamic evaluation yielded no result)"; a Multi-Provider with FirstMatch, FirstSuccessful and Comparison; status precedence FATAL, NOT_READY, ERROR, STALE, READY | DEFAULT is the nearest match to Baltor's declared order after insufficient evidence; the reason list models the selection path; the precedence models a composite's computed availability | Requirement 1.4.10, which returns the default value on any abnormal execution; no flag service inside selection | source |
| Learned routers and cascades | RouteLLM `0b64fdaf` (August 10, 2024; PyPI 0.2.0); FrugalGPT, arXiv 2305.05176v1 (May 9, 2023); OpenRouter documentation (read September 24, 2026): the Auto Router "degrades gracefully to a default model set" and silently ignores `allowed_models`, `excluded_models` and `cost_tier` sent under the other plugin identifier; Not Diamond 1.7.0 (May 22, 2026); LiteLLM 1.102.1 (September 23, 2026): three allowed failures and a five-second cooldown by default, `simple-shuffle` by default | A router's rule and threshold are part of its identity; the edge result names the engine that answered; a cascade needs a declared gate; a remote engine's reported identity is compared with the pin | Market-driven pools (not pinnable); fallback on any error; cross-provider fallback after a content refusal; learned thresholds before the one-million-run rule | source |
| Conservative exploration | Wu, Shariff, Lattimore and Szepesvari, ICML 2016 (PMLR 48): cumulative reward at least (1 - alpha) times the default arm's "for all t" | The declared incumbent is the baseline; a ramp stops conservatively | Any bandit before the adoption threshold | source |
| Safe policy improvement and logging | Thomas and others, ICML 2015; Kazerouni and others, NeurIPS 2017; Vowpal Wabbit 9.11.6 (`action:cost:probability`); Agarwal and others, arXiv 1606.03966v2 | Exact logged propensity from day one | Online learning in production | source (abstracts and the label format) |
| Shadow traffic and noise | Envoy v1.39.1 (August 27, 2026): mirroring is "fire and forget", and "If not specified, all requests to the target cluster will be mirrored"; Istio 1.31.1 (September 21, 2026) mirrors 100 percent when `mirrorPercentage` is absent; Scientist v1.6.5 (December 16, 2024) advises calibrating noise with the control on both sides; Diffy `6f01a56c` (May 18, 2026) compares a primary with a secondary | Mark comparison traffic; a missing rate means zero; measure the incumbent's disagreement with itself before spending allowance (LE-SELECT-018) | Mirroring everything when no rate is set | source |
| Hedging | gRPC proposal A6: hedge only methods "safe to execute multiple times"; cancel outstanding hedges on the first non-error response | Races only over engines safe to run twice, with loser cancellation where attempts run (LE-COMPOSE-010) | none | source |

A simulation of the design's paired loss gate (200 subjects, confidence 0.95)
showed what noise does: with a deterministic incumbent and a loss margin of
0.05, an identical challenger passed every time; with a noisy incumbent, every
challenger failed, an identical one included. Noise wastes comparison
allowance; it does not let a worse engine pass (ran [selection verifier,
September 24]).

### 4.3 Composition: how several engines make one answer

| Variation | Primary source, version and date | Lesson taken | Label |
|---|---|---|---|
| Declared and resolved plans with enforcers | Graefe and McKenna, "The Volcano Optimizer Generator", ICDE 1993; Graefe, "The Cascades Framework", IEEE Data Engineering Bulletin 18(3), 1995 (goal = expression plus property vector; a task "results either in a plan or a failure"; the `UNDEFINED` default of a property check) | A declared engine composition of slots and a resolved composition of exact engines; conversions are explicit positions; unknown coverage is not coverage | source |
| Calling conventions and converters | Apache Calcite 1.42.0 (May 28, 2026): "converting data has a runtime cost"; `VolcanoCost.isLe` returns early and compares only the row count | Every multi-part cost declares how its parts compare | source |
| Per-request pushdown answers | DataFusion 55.1.0 (September 11, 2026): Unsupported (the default for every filter), Inexact ("DataFusion applies an additional Filter operation after the scan"), Exact; all three keep the query result correct | These are work splits for advisory optimizations, never compatibility verdicts; a required semantic refuses when unsupported (LE-SUPPORT-005) | source |
| Required and ignorable extensions | Substrait extensions (latest release v0.103.1): an optimization "May be ignored by a consumer"; an enhancement "Cannot be ignored by a consumer" | Required and advisory request fields (LE-SUPPORT-001) | source |
| Analysis invalidation | MLIR pass management: "all analyses are assumed to be invalidated by a pass" unless preserved | A dependency change invalidates exactly its dependents (LE-SUPPORT-009) | source |
| Ordered filter chains | Envoy HTTP filters (docs 1.40.0-dev): decoders run A, B, C and encoders in reverse | Wrapper layers declare their order | source |
| Solution graphs in this repository | `loop_graph_definition/v2` in `code_nodes/solution_graph.py` (single, average, vote, weighted_average, ordered_fallback, select_best, gating_router), interpreted by the Solution Canvas; parked with its interpreter | Compositions whose parts need their own governance stay Solution graphs; composite engines add no second graph record | source |
| The planned strategy slot | `ModelCallStrategy.plan(request, allowance)` and `run(plan, model_access)` in the design row of `model_call_strategy` | The declared and resolved composition already split for the one strategy slot that exists | source [selection verifier] |

### 4.4 Lifecycle: how instances start, are shared, change and stop

| Variation | Primary source, version and date | Lesson taken | Label |
|---|---|---|---|
| Shared model residency | Ollama v0.32.6 (installed here) and v0.34.4 (published September 23, 2026, 02:24 UTC), `server/sched.go`: a reference count prevents unloading while a request is in flight; a request's keep-alive overwrites the runner's timer only when the request carries one; an idle runner with a keep-alive of 0 or less unloads at once; changed options reload the model (except for MLX models); the server context is `num_ctx` times the parallel slots | Residency is the server's state; holders take engine leases on it; the keep time sent is the longest among live holders (LE-INSTANCE-026) | source |
| Sleep and reload of model servers | vLLM 0.30.0 (September 22, 2026) sleep levels 1 and 2; NVIDIA Triton 2.72.0 (August 31, 2026): "When reloading a model fails, the already loaded model will be unchanged" is written only for the POLL model control mode, which the same page says "is not recommended for use in production environments"; under EXPLICIT the existing model "should be explicitly unloaded prior to the updated version being loaded" | A failed preparation keeps the previous configuration serving (LE-STATUS-007) is a design choice recorded here, not a lesson taken from Triton | source [lifecycle verifier, September 24] |
| Leases | etcd v3.7.2 (September 22, 2026): renewing an expired lease returns `ErrLeaseNotFound`; Vault documentation v2.x: revocation "prevents any further renewals", revoking a token revokes its leases, but nothing says revocation blocks new secrets; Kubernetes client-go (master): the current leader may renew its own expired lease when nobody took it | Expiry final at use, judged by the owner's clock, with a maximum lifetime, is a choice this repository records (LE-INSTANCE-005, LE-INSTANCE-016, LE-INSTANCE-017); a withdrawn credential issuing nothing is a new policy (LE-INSTANCE-006) | source |
| Pools | SQLAlchemy 2.0.54 (September 15, 2026): pre-ping, recycle, `recreate()`; Python 3.14 `ProcessPoolExecutor(max_tasks_per_child=...)` | A pool is one engine instance with member instances; recycling bounds carried state | source |
| Circuit breakers and bulkheads | resilience4j v2.4.0 (March 14, 2026); Polly 8.8.0 (September 14, 2026): one breaker per downstream authority, failure ratio 0.1, break 5 seconds; Envoy "circuit breaking" means connection and request limits (1,024 connections per cluster by default) | A route that failures set aside is an expiring route availability snapshot with a reason, and its probe is a counted model call (LE-STATUS-012); a shared instance declares its concurrency and queue bounds (LE-INSTANCE-027) | source |
| Sagas and compensation | Garcia-Molina and Salem, "Sagas", SIGMOD 1987; Microsoft Compensating Transaction pattern (page dated April 16, 2026): "Compensating transactions are eventually consistent operations and can fail" | Cleanup and compensation stay apart (LE-INSTANCE-010) | source |
| Process control | Linux `pidfd_send_signal(2)` and control groups version 2 (`populated`, `cgroup.kill`) on this host; `signal(7)`: SIGUSR1 has the default action Term; `bwrap(1)`: `--new-session` calls `setsid()` | An owned handle is a process file descriptor or a control group; a quiesce request never uses a signal whose default ends the process; a graceful stop reaches the sandboxed process; a stop is confirmed by observation (LE-LIFETIME-006, LE-LIFETIME-007, LE-ISOLATE-005) | source; ran [lifecycle verifier, September 24] |
| Tool server restarts | Model Context Protocol 2026-07-28, standard input and output transport: close input, wait, then SIGTERM and SIGKILL; after an unexpected exit "the client SHOULD restart it", and in-flight requests "are simply lost and the client can retry them" | A lost tool call with effects stays `effects_uncertain`; the protocol's retry permission never covers an external effect (LE-INSTANCE-025) | source |

### 4.5 Change: desired, prepared, routable, observed and rejected

| Variation | Primary source, version and date | Lesson taken | Label |
|---|---|---|---|
| Acknowledged is not applied | Envoy xDS protocol, v1.39.1: an ACK "does not mean that the configuration has been applied successfully"; "a NACK does not necessarily mean that none of the resources were accepted"; the configuration dump keeps `error_state` with the rejected version, its reason and time until the next success; resending a rejected set causes "needless work" | Binding facts keep desired, prepared, routable, observed and rejected apart (LE-STATUS-006); a rejected release is rebuilt on a capped backoff (LE-STATUS-008) | source [activation line] |
| Generations and progress | Kubernetes v1.37.1 (September 23, 2026): `observedGeneration`; `kubectl rollout status` waits for the generation to be observed first; `progressDeadlineSeconds` only reports a stall; EndpointSlice keeps `serving`, `terminating` and `ready` apart | A stall is reported with the desired configuration it concerns; draining work is not ready work | source [activation line] |
| Drain and replay | Temporal documentation `f82283a5` (September 18, 2026): Draining and Drained are counted from open pinned work; replay the histories of recent open and closed work through new code and "Fail CI if any error is encountered during replay" | A swap qualification replays the old engine's recorded state and work in flight (LE-INSTANCE-014) | source [activation line] |
| Prepare, analyse, switch, keep the old one briefly | Argo Rollouts v1.10.0 (August 27, 2026): the preview service before the active switch; `postPromotionAnalysis` rolls back; `scaleDownDelaySeconds` default 30; an Inconclusive analysis pauses | Evidence from the prepared engine gates the switch; inconclusive stops | source [activation line] |
| Initialize, observe ready, shut down the old one | OpenFeature v0.9.0 1.1.2.2 to 1.1.2.4 and 2.8.1: the provider "is the sole source" of its ready event; the old provider is shut down once nothing uses it | Readiness is observed from the engine, never inferred from a returned call | source [activation line] |
| Expand and contract for stateful engines | "Parallel Change" (Martin Fowler's site, May 13, 2014); PostgreSQL 18.6 `indisready`, `indisvalid`, `indislive`; Elasticsearch aliases swap "in a single atomic operation" and refuse writes without a write index | A stateful swap keeps "kept current", "trusted for reads" and "retired" apart; migrate with an atomic pointer | source [activation line] |
| Request, durable task and effect | Model Context Protocol 2026-07-28 cancellation ("MAY ignore"), the tasks extension (SEP-2663, cancellation is "cooperative"); Stripe idempotent requests return "the same result" and error on different parameters | Request outcome, task outcome and effect state are three fields (LE-INSTANCE-023); a retry by identity is answered from the first result (LE-INSTANCE-021) | source [activation line] |
| The platform the service releases on | Fly.io configuration reference (`superfly/docs` `423eea2d`, September 23, 2026): `immediate` replaces machines "without waiting for health checks to pass"; canary and blue-green "cannot be used for Machines with attached volumes"; uvicorn 0.52.4 graceful shutdown timeout unset in the service | Preparation happens inside the new release before it serves (LE-STATUS-009) | source [activation line] |

### 4.6 Support, semantics, conversions and streams

| Variation | Primary source, version and date | What was checked here | Label |
|---|---|---|---|
| Format as annotation or assertion | JSON Schema 2020-12 (draft-bhutton-json-schema-validation-01, June 16, 2022), section 7.2: assertion mode "MUST be disabled by default"; core section 8.1.2: an unrecognized required vocabulary means the schema "MUST" be refused | jsonschema 4.26.0 accepts "not a date" for `date-time` with and without a checker (its optional packages are absent), accepts the misspelled keyword `requried`, and reads an unknown `$schema` as 2020-12 with only a deprecation warning; the continuous integration step "Validate benchmark registry" accepts `as_of: "not a date"` (LE-SUPPORT-006) | source; ran [validation line and its verifier] |
| Remote references | Model Context Protocol 2026-07-28: implementations "MUST NOT automatically dereference `$ref` values that resolve to a network URI" | The library ingestion engine `connection_schema_validator`, declared pure, opens a connection to `models.dev` for an `opencode.json` that names a model; the protocol client adapter fetches a tool schema's remote `$ref` (LE-ENGINE-011) | ran, writer; first found by the validation line |
| Unknown fields and integers across encodings | protobuf.dev proto3 and ProtoJSON guides; protobuf 7.36.0 | An older binary reader keeps a newer field; the ProtoJSON reader refuses it, or loses it when told to ignore unknown fields; int64 is written as a string; a bare large integer is kept exact by Python although the guide says "should" be coerced to double | ran [validation line and its verifier] |
| Coercion | Pydantic 2.13.4 strict and lax modes | Strict refuses `12.0`, `true` and `"12"` for an integer; lax refuses `12.5`; unknown fields are ignored by default | ran [validation line] |
| Shared memory versus copies | Apache Arrow v25.0.1 C data interface and IPC; pyarrow 25.0.1 | The C interface shares the source buffer and marks the export released; IPC copies 8,000,280 bytes for one million int64 values; six cast losses are each off by default | ran [validation line and its verifier] |
| Loss classes | Java SE 25 chapter 5 (widening can lose precision); Avro 1.12.0 schema resolution; Unicode Standard Annex 15 (Unicode 18.0.0, August 12, 2026); RFC 8785 and RFC 7493; MLIR dialect conversion (full, partial, analysis) | A conversion declaration needs an information class, permitted losses, unknown-input and failure rules, equivalence, ownership and effects (LE-SUPPORT-008, LE-SUPPORT-010) | source [validation line] |
| Canonical forms | RFC 8785; RFC 8259 section 6 (no NaN) | Six canonical JSON functions give two byte forms for "é" and three outcomes for NaN; one passes `default=str`, so a set gives a different digest under each of four hash seeds (LE-SUPPORT-011) | ran [validation line and its verifier] |
| One time rule, several interpreters | Python 3.14.7 documentation for `datetime.fromisoformat` ("Changed in version 3.11") | Python 3.10 refuses six inputs that 3.11, 3.12 and 3.14 accept, among them the valid RFC 3339 time `2026-09-23T12:00:00.5Z`, and 3.11 and later cut nine fraction digits to six (LE-SUPPORT-012) | ran [validation verifier on 3.10, 3.11, 3.12 and 3.14] |
| Streams | WHATWG server-sent events (September 22, 2026): CR, LF or CRLF, multi-line data joined with LF; gRPC flow control ("There is the potential for a deadlock if both the client and server are doing synchronous reads"); Reactive Streams 1.0.4 (bounded buffers); Kafka 4.2 `acks`; RabbitMQ confirms; Ollama `errors.mdx` (an error "returned as an object" mid-stream); Anthropic streaming (`overloaded_error`; handle unknown event types); OpenAI OpenAPI 2.3.0 (usage may be missing after an interruption) | Through `ModelGateway.invoke`, an error after some text returns success with the partial text on both wires, on a local and on a cloud counted-generation route; malformed and two-line events and typed parts are lost; carriage-return endings fail as `model_identity_mismatch`; 5,120,000 characters are accepted for 8 tokens; keep-alives stretch a timeout (LE-LIFETIME-005) | ran, writer; first found by the validation line |
| Peer protocol leniency | Agent Client Protocol schema `schema-v1.23.0` and `schema-v2.0.0-alpha.5` (September 18, 2026); the reference crate's `serde_util.rs` on `main` ("outer failures are swallowed silently") | The version 1 schema forbids no extra field (120 `additionalProperties: true`); schema-strict and reference-lenient are two profiles (LE-SUPPORT-014) | ran and source [validation line] |

### 4.7 Isolation and execution

The outside list of bindings (function, subprocess, HTTP, Model Context
Protocol, WebAssembly) mixes dimensions: HTTP is a transport, the Model
Context Protocol an application protocol, a subprocess a process relationship
and WebAssembly an executable format. The committed wrapping research reached
the same finding (its section 8), and the lifecycle verifier found a third
vocabulary in the edge map. The standard therefore uses separate execution
fields (LE-ISOLATE-001) and a fixed order of choice: required isolation, then
state and lifetime, then placement, then measured overhead (LE-ISOLATE-002).
On this machine a process started in a median of 10.4 milliseconds and a
container in 230.4 milliseconds (claim, repository measurement of September
18).

For the Model Context Protocol, "mcp" is not one binding (source and ran
[protocol revisions line]):

- revision 2026-07-28 removes the `initialize` exchange and protocol sessions
  and carries the version and client capabilities on every request; a
  "handle" is an ordinary string that a tool returns and later accepts
  (SEP-2567);
- the library `mcp` 2.2.0 (September 7, 2026) routes by header only and has
  "no version allowlist, no way to reject or disable an era", so Baltor's
  selector is the only enforcement of the served set;
- the era classification rule alone decides whether a mixed request is
  served, so a qualification names the revision, the era with its
  classification rule version, the transport, the extension profile, the
  authorization profile, the implementation revision and the host's served
  set;
- the official conformance runner 0.2.0-alpha.11 passes most scenarios, with
  failures that need an applicability baseline.

### 4.8 Testing

| Variation | Primary source, version and date | Lesson taken | Label |
|---|---|---|---|
| One kit every implementation passes | Kubernetes `csi-test` v5.6.0 (August 25, 2026); Dapr component conformance tests and certification levels; pandas extension array tests; SQLAlchemy dialect compliance suite; OpenTelemetry Collector v0.161.0 generated component tests | A conformance kit per slot, sections closed by declared capability, sections generated only from closed fields (LE-TEST-015) | source [testing line] |
| Consumer-driven contracts | Pact specification version 4; pact-python 3.4.1 with pact-python-ffi 0.5.8.0 (September 17, 2026); Pact documentation: "You cannot expect a field to not be present in a response" | Expectation files per released client version (LE-TEST-006); absence rules need a provider check (LE-TEST-012) | ran and source [qualification tools line] |
| Schema-driven HTTP fuzzing | Schemathesis 4.28.0 (September 22, 2026): baseline entries with a reason and an expiry; event-stream validation; in-process testing | It found real gaps between published schemas and enforcement; it proves only what a schema states, and Baltor publishes no response schema (LE-EDGE-010) | ran [qualification tools line] |
| Properties, state machines and metamorphic relations | Hypothesis 6.168.1 (September 23, 2026): the `ci` profile is derandomized with no deadline and no example database | Repeatable properties on every push; failures pinned as explicit examples; profiles calibrated with named mutants (2 of 6 survived at 50 examples, none at 200) (LE-TEST-014) | ran [qualification tools line] |
| Combinatorial rows | PICT main `ab76c25` (September 8, 2026); NIST ACTS Basic 1.0; allpairspy 2.5.1; NIST CCMCL | PICT order 2 covered all valid pairs of 306 valid configurations in 17 rows and order 3 all triples in 59, confirmed by CCMCL; ACTS Basic ignores constraints while printing "Coverage has been verified!"; allpairspy under-covers silently; PICT's documented `ISPOSITIVE([p])` form is skipped with exit 0 (LE-TEST-011) | ran [qualification tools line] |
| Network faults | Toxiproxy 2.12.0 (March 18, 2025): `reset_peer` forwards nothing; `timeout` 0 closes when the upstream closes; `packet_loss` is on main only | TCP faults between two real processes end in typed records; a trickled model answer is not bounded by its timeout (LE-INSTANCE-020) | ran [qualification tools line and its verifier] |
| Mutation | Cosmic Ray 8.7.0 (August 9, 2026): any test command, but the local distributor mutates the code in place and serially; mutmut 3.8.0 (September 12, 2026) needs pytest and `fork` | Cosmic Ray on an exported tree with one module's self-test as the command | source [testing verifier] |
| Fault injection | SQLite testing page (updated April 21, 2026): failure at operation n for a rising n, once and then continuously | Lifecycle drills through declared seams (LE-TEST-007) | source |
| Containers in tests | Testcontainers for Python 4.15.0 (July 24, 2026): its reaper mounts the container daemon socket read-write | Plain `docker` behind the recorded command runner stays the default (LE-TEST-008) | source |
| Combinations in theory | Kuhn, Wallace and Gallo, IEEE Transactions on Software Engineering 30(6), 418 to 421, 2004 | All pairs of engines on every push, the full matrix at night | source |
| Protocol conformance | Model Context Protocol conformance runner 0.2.0-alpha.11; Agent Client Protocol schema tags (no official conformance repository in its organization) | Run per revision with a reasoned expected-failures file; pin the schema tag, not the crate version | source [protocol revisions line; testing verifiers] |

### 4.9 Writing the rule and the standard

| Practice | Primary source, version and date | Taken |
|---|---|---|
| Capital key words with one meaning | RFC 2119 (1997) and RFC 8174 (2017), BCP 14 | Adopted for the standard's statements, exactly one key word each; the Constitution keeps its own definitions and does not cite BCP 14 |
| A recommendation says when it may be set aside; rationale kept apart | Google AIP-8 (`780e9301`) and AIP-190 (`90ab3aba`); API linter v2.4.0 (September 10, 2026), whose local disable comment carries `aip.dev/not-precedent`, while `--disable-rule` and a configuration file also disable rules | "Set aside when" on every SHOULD; reasons in the design and research records; exceptions local and never precedent |
| Compliance per statement, unknown kept unknown | OpenTelemetry specification v1.61.0 (September 14, 2026) | A "Today" line on every statement |
| Maturity apart from interface stability | Envoy `EXTENSION_POLICY.md` (`f552b698`, September 10, 2026) | Engine lifecycle apart from edge contract versions |
| Decisions superseded, never deleted | Backstage architecture decision records (`33c81904`, September 9, 2026) | Withdrawn statements keep their identifiers |

## 5. The outside claims, checked

The owner pasted two sets of outside research on September 23 (summarized in
`CHATGPT-ENGINE-WRAPPING-VARIATIONS.md` and
`CHATGPT-PROTOCOLS-ROLLOUT-QUALIFICATION.md` beside this record's draft). Their
own files, a "Functional Component Standard v0.1" with four schemas and 42
checks, are not on this machine, so those counts stay claims.

| Outside claim | Verdict | Where it lands |
|---|---|---|
| Support replacement at several levels: a whole engine, a stage inside it, or a shared backend | Holds: nested slots and strategy slots express it | LE-SLOT-007, LE-COMPOSE-001 |
| A component boundary is not automatically a container boundary | Holds | LE-ISOLATE-002 |
| Own the functional boundaries, admit upstream and native engines, keep a native track | Holds; the roadmap calls it the Baltor-native engine track; hosted providers get not_applicable with a reason | LE-OUTSIDE-003 |
| Seven separated wrapper duties; the semantic adapter grows no scheduler, retry loop or state database | Holds; each duty has one owner here | standard section 2, LE-ENGINE-003 |
| Dependency injection is a design boundary, not a permission sandbox | Holds | LE-ISOLATE-003 |
| Definition, configuration, instance, lease, session, invocation, state | Content holds; the outside names are mapped to existing records or retired | standard section 3 |
| Ten rankers share one loaded model through separate leases; closing one lease must not unload it | Holds; Ollama's reference count behaves this way; the repository has no shared instance yet | LE-INSTANCE-004, LE-INSTANCE-026 |
| Six "lifecycle profiles" | Content holds; the name collides with "lifecycle" and "profile" | three fields and a swap rule, standard section 4 |
| Inspecting support launches nothing | Already a rule: discovery is effect-free; one slot names an observation as its comparison | LE-ENGINE-008, LE-SUPPORT-002 |
| Four responsibilities: control, execution, state and resources, evidence | Holds; scheduling belongs to the Loop runtime only | the envelope Loop |
| Composition forms; logical and physical plans; pinning a composite freezes its parts; qualified parts do not qualify the composite; no averaged confidence | Holds; the plan words collide with "plan"; the served search gap is a missing binding, not an emergent composition failure | LE-COMPOSE-001 to 015 |
| Support per request as exact, inexact, unsupported | Corrected: these are work splits for advisory optimizations | LE-SUPPORT-004, LE-SUPPORT-005 |
| Optimization hints can be ignored; unknown required semantics fail | Holds (Substrait) | LE-SUPPORT-001, LE-SUPPORT-002 |
| Alive, ready, capacity, qualified and result verified stay apart | Holds; three subjects: instance, installation, result | standard section 8 |
| Desired versus effective configuration; desired may be pending or rejected | Holds (Kubernetes, Envoy); the Triton support holds only in POLL mode | LE-STATUS-006, LE-STATUS-007 |
| Resource cleanup versus business compensation | Holds (Sagas; Microsoft) | LE-INSTANCE-010 |
| Conversions declare types, loss, ownership, effects and cost | Holds; four loss classes are too few | LE-SUPPORT-008 |
| Cache identity needs a dependency graph and explicit invalidation | Holds (MLIR) | LE-SUPPORT-009 |
| Middleware is ordered and versioned; authorization precedes cached results; retry has one owner and one budget | Holds; the catalogue already checks a withdrawal before a cached body read; the retry field is free text today | LE-EDGE-012, LE-ENGINE-004, LE-ENGINE-005 |
| A pinned remote endpoint does not prove the server's implementation | Holds; the gateway compares a reported model with the route; Baltor's own server reports a constant version | LE-SELECT-007, LE-ISOLATE-001 |
| Execution boundaries: function, subprocess, WebAssembly, sidecar, remote | Holds as separate dimensions, not one list | LE-ISOLATE-001 |
| PIN, PREFER and AUTO at a project, user, run or "node" scope | The three hold as a selection basis; the scopes map onto existing parameter sources | LE-SELECT-005, LE-SELECT-016 |
| "Real time" selection means the next eligible call, with transition rules for stateful engines | Holds | LE-SELECT-014, LE-LIFETIME-003 |
| Separate the descriptor from a request-support checker | Holds; the slot field `requirement_comparison` is the home, and 3 of its 7 filled values compare a request with a declaration | LE-SUPPORT-002 |
| Separate the selector from an activation controller | Holds as selection versus binding facts and availability snapshots; "activation" names reactive Loop runs | LE-STATUS-001, LE-STATUS-006 |
| Separate the execution specification from resource leases | Holds; the service already pins one view per request and rechecks permission at completion | LE-INSTANCE-004, LE-INSTANCE-016 |
| Separate the request, the durable task and the external effect | Holds; the service answers 504 while the effect commits later | LE-EDGE-013, LE-INSTANCE-023 |
| Separate engine qualification from transition qualification | Holds as the swap qualification; the qualification lab's `state_transition` unit cannot qualify a swap | LE-INSTANCE-014 |
| Model Context Protocol 2026-07-28 removes initialization and sessions; qualify by revision, transport, extension profile and implementation revision | Holds; three more terms: the era classification rule, the authorization profile and the host's served set | LE-EDGE-009, LE-ISOLATE-001 |
| An xDS acknowledgment does not prove application; a rejection can accompany partial acceptance | Holds | LE-STATUS-006 |
| JSON Schema `format` may be an annotation; identical schemas behave differently under different validator settings | Holds, with three more settings: installed optional packages, the interpreter and remote reference fetching | LE-SUPPORT-006 |
| ProtoJSON and binary protobuf differ on unknown fields and integers | Holds | LE-SUPPORT-008 |
| Streams need buffer limits, ordering scope, acknowledgment meaning, replay and partial-result rules | Holds; the repository's stream readers fail the partial-result rule | LE-EDGE-011, LE-LIFETIME-005 |
| Hypothesis, Pact, Schemathesis, NIST ACTS and Toxiproxy play complementary roles; none proves universal interchangeability | Holds; ACTS Basic ignores constraints, so PICT is used for rows | LE-TEST-006, LE-TEST-011, LE-TEST-014 |
| Implement controllers and registries first as ordinary modules; containers only where isolation, resources or deployment justify them | Holds for modules; no controller class is added, and the owners that exist (refresher, host loader, envelope) keep the moments | LE-SLOT-003, LE-ISOLATE-002 |
| Data movement between partitions can erase the gains of partitioned or fused execution | Not measured | claim |

## 6. What was checked against the repository

Findings in the order of the standard's groups. "Confirmed" means an
adversarial verifier reproduced it; "writer" means it ran for this record on
`e6346075`.

| # | Finding | Evidence | Statement |
|---:|---|---|---|
| 1 | 45 slots: 38 candidate, 7 planned, 0 active; one_of 27, set_of 11, derived 7; index valid with 0 findings; 30 slots name a suite, 28 collected; 0 of 37 descriptor projections and 7 of 37 factory tables resolve | ran, writer; confirmed by two verifiers | LE-SLOT-002 |
| 2 | 53 interaction rows; 46 joined by exactly one slot, 7 Loop runtime rows by none; 40 of the 93 contract names are defined in no Python file, in 28 rows, 3 of them active and 1 a partial mapping; `model_invocation_request/v1` appears in no Python file | ran, writer | LE-EDGE-002, LE-EDGE-008 |
| 3 | The retry field holds 39 distinct free labels; delivery 32, privacy 34, verification 39, repair 27, timeout 16, cancellation 8, failure 9 | ran, writer; first counted by the testing verifier | LE-EDGE-012, LE-TEST-015 |
| 4 | For a two-key record, SQLite and DuckDB return nine keys and drop unknown keys that the other three store engines keep | ran [testing line]; confirmed and widened by both verifiers | LE-EDGE-004 |
| 5 | The installer as released at `56639ee6` is refused with `unsupported_version`; the installer imports the service's constant; the Pi extension negotiates but is checked only byte for byte | ran [qualification tools line]; source [testing verifiers] | LE-EDGE-006, LE-TEST-006 |
| 6 | A protocol request whose header names 2025-11-25 while its body names 2026-07-28 or 2099-01-01 is served under 2025-11-25 rules with a read and a usage record, also on a host that serves only 2025-11-25; no stored record names a revision | ran, writer; first found by the protocol revisions line | LE-EDGE-009, LE-STATUS-011 |
| 7 | The advertised `intelligence_search` schema accepts six kinds of input that the service refuses; no tool publishes an `outputSchema` | ran [validation line; qualification tools line] | LE-EDGE-010 |
| 8 | A read that passes its deadline is answered 504 while its usage record commits later; a cancelled read commits later; with the default pool, four timed-out reads hold four of an account's shares and a retry is refused 429; the rows declare `inherited_request_cancellation` | ran, writer; first found by the activation line and its verifier | LE-EDGE-013 |
| 9 | Four library ingestion slots are missing from the catalogue and `library_ingestion_source` lists kinds the code lacks, while the index reports 0 findings | ran, writer | LE-SLOT-001 |
| 10 | Two rows still list `core/service_runtime/http.py` as constructing `Retriever`; the check tests file existence only | source [testing verifiers] | LE-SLOT-004 |
| 11 | Library ingestion keeps its own `EngineSlot` and `library_engine_selection/v1`; `tools/candidate_review` and `tools/opencode_generation_lanes.py` keep record families of their own | ran, writer; source | LE-SLOT-009, LE-SLOT-010 |
| 12 | `material_install_layout` cannot become active while its five layout rows live in `tools/` | source [testing verifier, September 24] | LE-SLOT-011 |
| 13 | `skillspector_static`, `datasketch_minhash_lsh` and `builtin_static_rules` each name two classes; the skills-ref validator is wrapped twice; five `native_*` pre-check engines wrap other engines | source [repository grounding line and its verifier] | LE-ENGINE-002, LE-COMPOSE-006 |
| 14 | Installation settings accept `api_key_env`, `allow_network`, `spending_limit_usd`, `budget_tokens`, `max_cost_usd`, `allow_failover`, `network_hosts`, `permissions`, `token_env`, `secret_ref` and more; only `api_key` is refused | ran, writer | LE-ENGINE-006 |
| 15 | A step engine that raises under a call ceiling ends as `budget_exhausted` with `model_call_accounting_incomplete` | ran [testing line]; confirmed on `2658b7bb` | LE-ENGINE-009 |
| 16 | The pure engine `connection_schema_validator` opens a connection to `models.dev` when an `opencode.json` names a model | ran, writer | LE-ENGINE-011 |
| 17 | The ledger lets `stopped` become `running` and accepts a heartbeat for a hibernated instance; a second live reservation per instance is accepted | ran [lifecycle line]; confirmed by both verifiers | LE-INSTANCE-003, LE-INSTANCE-008 |
| 18 | An expired work lease can start, renew and commit when no claim ran in between; every time comes from the holder; one heartbeat moved a lease to the year 2100 and blocked later claims | ran [lifecycle line and its verifier, September 24] | LE-INSTANCE-005, LE-INSTANCE-016, LE-INSTANCE-017 |
| 19 | An expired credential lease renews to live, and revoking a credential does not block the next issue; both are asserted on purpose by the module's self-test; `resolve` takes no holder identity | ran [lifecycle line]; source [verifiers] | LE-INSTANCE-005 to 007 |
| 20 | After an unconfirmed Docker cleanup, a new `DockerWorkspace` object writes and starts a second container; the solve runtime builds a new object for every command | ran and source [lifecycle line and both verifiers] | LE-INSTANCE-009 |
| 21 | A trickled model answer completes after 8.41 seconds (buffer) and 11.6 seconds (stream) against a 1-second timeout; a refused connection counts as one physical request; a close with no byte reads as `response_received` | ran, writer; first found by the qualification tools line | LE-INSTANCE-020, LE-INSTANCE-024 |
| 22 | After a catalogue swap with release-following grants, retries of one request identity are refused with `meter_commit_unknown` while the store's own answer is `usage_identity_conflict`, and a new identity is metered again | ran, writer; first found by the activation line | LE-INSTANCE-021, LE-INSTANCE-022 |
| 23 | Two endpoint declarations for one model send keep-alive 36000, 0, 36000, 0 and context lengths 8192, 2048, 8192, 2048 without a conflict check | ran [lifecycle verifier, September 24] | LE-INSTANCE-026 |
| 24 | The gateway and the endpoint adapter hold no concurrency limit, and nothing reads the route snapshot's `available_concurrency` or `queue_depth`; no module outside the checks constructs a route availability snapshot | source, writer; lifecycle verifier | LE-INSTANCE-027, LE-STATUS-012 |
| 25 | Hibernation with the module's own controller records `checkpoint_verified` and `publication_fenced`; its quiesce step sends SIGUSR1, which ended Bubblewrap and opened a Node.js debugger on `127.0.0.1:9229`; SIGTERM to the owned group never reaches the sandboxed process; the wait for Bubblewrap is not a stop confirmation (11 of 30 trials) | ran [lifecycle line and its verifier, September 24] | LE-STATUS-005, LE-LIFETIME-006, LE-LIFETIME-007, LE-ISOLATE-005 |
| 26 | The model token stream readers return success after an in-band error on both wires, through the gateway, on a local and on a cloud counted-generation route | ran, writer | LE-LIFETIME-005 |
| 27 | A pin cannot name `opencode@1.2.3`; the installation record names no engine version | ran, writer | LE-SELECT-007, LE-INSTANCE-002 |
| 28 | A decision can select `goose` over the declared-first `opencode` with evidence `not_requested` at propensity 1/1 or 1/2; evidence marked used with `changed_order: false` over a reordered ranking is accepted | ran, writer; first found by the selection verifiers | LE-SELECT-009 |
| 29 | A declared-order first choice is accepted at propensity 1/2 and 1/1000 | ran, writer | LE-SELECT-013 |
| 30 | A `record_store` policy with an ordered fallback, and objective overrides outside the slot's objectives, are accepted; a per-sender objective permission cannot be written | ran, writer | LE-SELECT-002, LE-SELECT-017 |
| 31 | A Loop sender may claim `explicit_invocation` precedence | ran, writer | LE-SELECT-016 |
| 32 | A fallback decision that omits its predecessor's pin is accepted, and no field names the decision before it; a pinned decision with no fallbacks and `no_fallback: false` is accepted | ran, writer; first found by the selection verifier, September 24 | LE-SELECT-021, LE-SELECT-022 |
| 33 | With evaluator route change permitted, an inconclusive verdict moved the call to a second route and served its answer | ran, writer; first found by the selection verifier, September 24 | LE-COMPOSE-015 |
| 34 | `FallbackTransition` names no evaluator, score or threshold | ran, writer | LE-COMPOSE-011 |
| 35 | The parked `first_success` join waits for every branch and returns the slower one by branch identifier; a first-completed join over thread branches could not stop the loser | ran [selection line and its verifier] | LE-COMPOSE-010 |
| 36 | The exact and canonical contract match modes treat true, 1 and 1.0 as equal | ran, writer | LE-SUPPORT-007 |
| 37 | `pyproject.toml` requires `jsonschema>=4.20` without a pin; none of 13 JSON Schema call sites asserts formats or pins references | source [validation line] | LE-SUPPORT-006 |
| 38 | A provider count of 12.9, `true` or `"12"` is stored as provider-reported by the harness adapters and as unknown by the gateway; a request count of 1.9 is one physical call | ran [validation line and its verifier] | LE-INSTANCE-019 |
| 39 | Harness output bytes that are not UTF-8 are replaced without a count; 400,003 raw bytes within the 1 MiB cap become 1,200,003 bytes after decoding | ran [validation verifier] | LE-SUPPORT-010 |
| 40 | A lone surrogate in a request gives HTTP 500 `operation_failed` on the REST route, a parse error at 2025-11-25 and a tool error at 2026-07-28 | ran [validation verifier] | LE-SUPPORT-006 (validation profile, text rules) |
| 41 | A schema pattern with nested repetition takes 1.41 seconds for 24 characters, and a tool schema with 20,000 `anyOf` branches is admitted at discovery after 17.12 seconds | ran [validation verifier] | LE-SUPPORT-006 (validation profile limits) |
| 42 | The qualification guard compares the reviewer only with the engine; there is no producer field; `store_conformance/v1` is already a kit report record | source [testing verifiers] | LE-STATUS-003, LE-TEST-003 |
| 43 | A rejected desired catalogue release is built three times in three checks; the refresher status and the health answer name neither it nor its revision; a restart then refuses to start although the previous release is stored and verified | ran, writer; first found by the activation line and its verifier | LE-STATUS-006 to 008 |
| 44 | The release deploys with `--strategy immediate` and applies grants and billing afterwards; in that window the health answer passes every catalogue check while the list is empty | source; ran [activation line] | LE-STATUS-009 |
| 45 | A request word after the twelfth is never read in the default lexical mode; equal scores follow insertion order in the engine-side search only | ran [testing line]; corrected by its verifiers | LE-TEST-010 |
| 46 | The served search ranks as `SERVED_BEFORE_2026_09_21`, not as the declared default (held-back mean reciprocal rank 0.7373 against 0.7832 at depth 20), as `SEARCH-QUALITY.md` limitation 3 records | ran [testing line and verifiers] | standard adoption step 5 |
| 47 | The installer leaves hidden `.partial` files after a kill; a failed read-back after placement reports a refusal; `read` and `fstat` faults escape untyped and stop the run | ran [testing line]; widened by its verifiers | LE-TEST-007 |
| 48 | A layout row may place two served kinds at one file location | ran [testing line]; confirmed | standard adoption step 6 |
| 49 | The confined writer keeps bytes and creates every file with mode 0o644 | ran [component standard review's writer trial] | LE-OUTSIDE-007 |
| 50 | Two workflows run on a schedule (`live-pulse.yml`, `research-watch.yml`); no kit, drill, binary or model journey does; eight red runs came from a test that needed a real provider key; the tools suite names no skip | source, writer; testing verifier | LE-TEST-009, LE-TEST-013 |
| 51 | The retrieval self-test downloads model weights from the Hugging Face hub when its cache is empty; the model2vec stage names no revision and records `hf-cache-pin` | ran, writer; source, writer | LE-TEST-013, LE-OUTSIDE-002 |
| 52 | The research watch holds 17 sources, none of them the outside projects behind today's engine adapters; its protocol entry names the 2025-11-25 page | source, writer | LE-OUTSIDE-008 |
| 53 | The rendered ambiguity register lacks SEM-025; ten public class names are defined in more than one module; `resolved_terms()` lets a later section replace an earlier one; the vocabulary gate refuses only retired names in documents | ran [rule and names line]; confirmed by both verifiers | LE-NAME-001, LE-NAME-004, LE-NAME-005 |
| 54 | Roadmap text uses "three modes", "wrapper engine", "Harness File Profile" and "contract test kit", and the vocabulary gate does not scan YAML | source, writer | LE-NAME-008 |

## 7. Probes and checks run for this record

All on an export of `e6346075` in the scratch folder `writer-run-3/`, with the
repository's virtual environment (Python 3.10.20), bytecode writing off, and
temporary and home folders inside the scratch folder unless stated. Every
probe except `probe_interaction_rows.py` was first written by a research line,
a verifier or the second writer run, and each gave the same result as on
`3d48a36c`, apart from the number of connection attempts noted below.

| Probe or check | Result on `e6346075` |
|---|---|
| `slot_counts.py` | 45 slots, valid, 0 findings; the counts of finding 1 |
| `probe_interaction_rows.py` (new) | findings 2 and 3 |
| `probe_local_slots.py` | five local library slots, four not catalogued; the shared and local `EngineSlot` are different classes |
| `probe_records.py` | pins (A1 to A8), declared order (B1 to B5), propensity (C1, C2), policy against slot (D1), objectives (E1 to E3), cascade (F1 to F4), precedence (G1, G2) as in findings 27 to 34 |
| `installation_probe.py` | finding 14 |
| `probe_gateway_cascade.py` | finding 33, with the permission off as a control that stops correctly |
| `probe_exact_match.py` | finding 36 |
| `p_ingestion_net.py` | finding 16, with the network blocked by a recorder |
| `p_gateway_stream.py` | finding 26 |
| `v_t2_trickle.py` | finding 21 |
| `probe_verify_at.py`, `probe_verify_at_w2.py` | findings 8, 22 and 43 |
| `probe_vmr.py` | finding 6, and the constant server version `1.0.0` |
| `probe_retrieval_selftest_network.py` | finding 51: 16 checks pass while the network is blocked, after two attempts to reach `huggingface.co` with an empty cache (one attempt with a warm folder on `3d48a36c`) |
| The hardened statement check, `standard_statement_check_v2.py` | 176 statements, 0 findings on the standard; each of 13 planted defects and evasions refused, and all seven defects refused together |
| The vocabulary gate, the naming, semantic and architecture contract self-tests, the route check and the link check | see the rule 6 proposal, section "What was checked" |

## 8. What stays a claim

- The outside research's own files (the "Functional Component Standard v0.1",
  four schemas and 42 checks) are not on this machine.
- The registration digest covers the declaration and the class, not the code
  bytes; one candidate gateway row may repeat an active row (wave A problems
  21 and 12, not rechecked).
- The DBOS 3.0.0 trial in which an interrupted external action ran again, and
  the FastMCP 4.0.5 trial in which an allowlist alone still exposed a
  destructive endpoint (ecosystem edge map author's trials).
- The agent-harness audit's binary conversion and ownership findings
  (committed research of September 23).
- The median start times of 10.4 milliseconds for a process and 230.4 for a
  container (repository measurement of September 18).
- That a live Ollama server alternating between two declarations unloads and
  reloads as its source predicts; no model call was made, and a live trial
  needs local model calls that the recorded authority does not name.
- That the live service shows the empty-list window after a
  catalogue-changing release: the workflow comments say so for release 12,
  and the probe used the repository's fixture.
- Named-client protocol observations recorded in commit `3b64ab44`.
- The Kazerouni and Thomas abstracts, the Vowpal Wabbit label format, the
  Decision Service paper and the Not Diamond interface (read as abstracts and
  documentation only).
- That data movement between partitions can erase the gains of partitioned or
  fused execution.
- The estimate that the per-push kit tier fits in about one minute per
  continuous integration leg; its trials sum to about 51 seconds before any
  composition test or journey.

## 9. Discriminating qualification trials

Each trial names the known-wrong case that must fail, so that a trial which
passes everything proves nothing. Proof levels are those of
`engine_qualification/v1`: `local_contract`, `real_provider`,
`held_out_comparison`, `end_to_end` and `operational_drill`. "Today" says what
the known-wrong case does on `e6346075`.

| # | Trial | Setup | Known-wrong case that must fail | Pass condition | Proof level | Today | Statements | Authority needed |
|---:|---|---|---|---|---|---|---|---|
| T1 | In-process against subprocess on one contract | The Agent Skills reference validator as two installations of one engine: the in-process `skills_ref` library and the `agentskills` command as a supervised subprocess; the same kit | The subprocess form inherits the host environment (a probe sees a planted variable) or returns a different key set | Both pass every kit section; the reports differ only in their execution fields and measured times | `local_contract` | not built; the two forms carry two identifiers today | LE-ISOLATE-001, LE-EDGE-004, LE-ENGINE-002 | none |
| T2 | Two installations and a preference change during a run | One engine installed twice with different settings; a preference change between attempt 2 and attempt 3 of one run | The running attempt rebinds to the new installation | Attempts 1 and 2 keep their decision; attempt 3 uses the new one; the decisions show why | `local_contract` | no selector exists | LE-SELECT-014, LE-LIFETIME-003 | none |
| T3 | Shared model with separate engine leases | A loopback stand-in that implements Ollama v0.32.6 reference counting; ten holders with different keep times; one holder releases; one request with a different context length | A keep time of 0 sent while another holder is live; a silent reload for a different context length | Residency stays while any lease is live; the longest keep time is sent; the different request is refused or routed with a reason | `local_contract` | both known-wrong cases are accepted | LE-INSTANCE-004, LE-INSTANCE-026 | none; a live variant needs a local model and its owner's authority |
| T4 | Atomic against fused composition | A fused engine and its unfused composition on a fixed evaluation set | The fused run leaves one Run History record, or drops one position's filtering | Identical results and one record per logical position | `local_contract` | no composite exists | LE-COMPOSE-009 | none |
| T5 | Unknown advisory field against unknown required field | One request with an unknown advisory field, one with an unknown required field | An engine that ignores a required filter and returns a wider result | The advisory field is recorded as ignored; the required one refuses before effect with zero engine calls | `local_contract` | required features exist for harnesses only | LE-SUPPORT-001 to 003 | none |
| T6 | Partial conversion and exact matching | A bounded_lossy conversion feeding a port that accepts loss, then an exact-match port; `true` against `1` through the exact mode | The lossy conversion accepted into the exact port; `1` accepted as exactly `true` | The first connection passes with the loss counted; the second is refused before execution; exact matching separates types | `local_contract` | `1` is accepted as exactly `true`; any adapter name is accepted | LE-SUPPORT-007, LE-SUPPORT-008 | none |
| T7 | Selective invalidation | A composite with two nested installations; change one nested installation; change an unrelated timeout inside the qualified range; change the embedding space of an index | Qualification kept after the nested change, or dropped after the unrelated change; the index reused under a new space | Exactly the dependents are invalidated | `local_contract` | only embedding spaces are checked | LE-COMPOSE-006, LE-SUPPORT-009, LE-INSTANCE-013 | none |
| T8 | Blocked member and backpressure | An all_of slot with one slow member; a shared instance with a declared concurrency and queue bound | Unbounded waiting, or a full queue reported as an engine failure that triggers a fallback | Waiting is measured in the admission phase; a full queue answers capacity; no fallback happens | `local_contract` | no limit exists on the model path | LE-SELECT-003, LE-INSTANCE-027 | none |
| T9 | Uncertain external effect not replayed | A fixture tool server over standard input and output whose tool writes a file; the server is killed after the write and before the reply | The tool call retried automatically after the restart, as the protocol allows for stateless requests | The attempt ends `effects_uncertain`; no fallback and no retry; reconciliation by a stable key | `local_contract` | a transport failure ends `failed` with `transport_failed` | LE-INSTANCE-025, LE-LIFETIME-004 | none |
| T10 | Restart with durable state compatibility | A store written under format version 1; restart with an engine that declares version 2; a release that writes a new catalogue state version | The version 2 engine reads version 1 silently; a rollback image refuses to start against the new state version | Refusal before any effect; the same format is accepted; a release writes only a state version its predecessor reads | `local_contract`, then a release drill | the catalogue state marker refuses unknown versions; no release has raised it | LE-INSTANCE-013, LE-STATUS-010 | none; a release for the drill |
| T11 | Desired B while A serves, with a restart | A host declares release or engine B while A serves; B's preparation fails, the process restarts, then B is repaired | A stopped although B failed; B rebuilt at every check; health silent about B; the restart refuses to start | A keeps serving, also after the restart; B is recorded as rejected with its reason and rebuilt on a backoff; the repaired B swaps in at the next check | `local_contract` with fixtures; `operational_drill` on the service | three builds in three checks, B absent from health, and the restart refuses with `body_digest_mismatch` | LE-STATUS-006 to 008 | none for fixtures; a release for the drill |
| T12 | Preparation failure recovered through owned resource records | A container preparation is killed after its pending record is written; the host restarts | A new adapter object starts a second container while the first is unconfirmed | The reconciliation Loop finds the pending record, confirms by inspection and releases it, or keeps it unknown and blocks reuse | `local_contract` with Docker | the block is lost with the adapter object | LE-INSTANCE-009 | none |
| T13 | Pin an unavailable engine; overturned declared order | A pin on an engine made unavailable; a decision whose ranking reverses the declared order without evidence | A fallback runs under the pin; the reversed decision is accepted | The step fails with the pinned engine named; the reversed decision is refused | `local_contract` | the reversed decision is accepted | LE-SELECT-006, LE-SELECT-009; D-28-T01 | none |
| T14 | Exact pin and run pin inheritance | A run pinned to `opencode` at version X; version X+1 installed during the run; a retry, a fallback decision and a Spawned Loop inside the run | The retry picks X+1; the fallback decision drops the pin | Every later decision of the run uses X or refuses with `pinned_identity_mismatch`, and names its predecessor | `local_contract` | an exact pin cannot be written; a pin-dropping fallback is accepted | LE-SELECT-007, LE-SELECT-008, LE-SELECT-021 | none |
| T15 | A kit that discriminates | The step executor kit with two fixture engines and one broken engine; a mutated kit that accepts the broken engine; the same kit in a container with an egress probe | The broken engine passes; the mutated kit passes its own test; the egress probe succeeds | Both engines pass, the broken one fails, the mutated kit fails, the egress probe fails | `local_contract` | no kit loops over engines | LE-TEST-001, LE-TEST-002, LE-TEST-008; D-27-T02 | none |
| T16 | Swap qualification of a stateful engine | `record_store` swapped from `local.sqlite` to a second engine: drain, fence the old writer, export, check, import, switch in one conditional step | Two separate engine qualifications counted as a swap; a late write of the old owner accepted | The swap has its own qualification naming both installations and a population; the late write is fenced | `operational_drill` | the qualification record refuses a field that names a previous installation | LE-INSTANCE-014 | a release for the live drill |
| T17 | Protocol era classification | Requests with header 2025-11-25 and body metadata 2026-07-28 or 2099-01-01; the same on a host serving only 2025-11-25; a per-request `initialize`; a handshake `initialize` | The mixed request served with a read and a usage record | HTTP 400 with -32020 (or -32022 on the rollback host) and no effect; the handshake still works | `local_contract`, then the live check on every hostname | served with a read and a usage record | LE-EDGE-009, LE-STATUS-011 | a release for the live check |
| T18 | Stream error semantics | Loopback servers sending an error object then the end marker, an Ollama error line, malformed and two-line events, typed content parts, oversized output and slow keep-alives, through the gateway | Any of these reported as a complete answer; a timeout stretched by keep-alives | Each ends incomplete with a typed reason and a provisional candidate, or is counted where the provider documents it; a total deadline holds | `local_contract` | success with the partial text | LE-LIFETIME-005, LE-EDGE-011 | none |
| T19 | Lease expiry at use | A work lease past expiry with no claim in between, with times from the scheduler's own clock; a heartbeat far in the future; an expired credential lease; a revoked held credential | Start, heartbeat or commit accepted; a lease moved past its maximum; renewal returns live; issue after revocation succeeds | Every use after expiry is refused by the owner's clock; renewal stops at the maximum; revocation stops issue until the credential is held again | `local_contract` | all known-wrong cases are accepted | LE-INSTANCE-005, LE-INSTANCE-006, LE-INSTANCE-016, LE-INSTANCE-017 | none |
| T20 | Race with loser cancellation | Three harness attempts with delays of 0.05, 0.2 and 0.35 seconds, cancelled where harness attempts run, once the Loop runtime has a live concurrency owner | The slower attempt returned by identifier; losers left running; a cancelled attempt charged as zero | The fastest answer returns; the losers' process groups are ended; their usage is recorded as known or unknown; race outcomes never enter ranking evidence | `local_contract` | the parked join waits for all and picks by identifier | LE-COMPOSE-010 | none; restoring the parked parallel runner is a recorded owner decision |
| T21 | An inconclusive gate never escalates | The gateway's two-route fixture with evaluator route change permitted and a rejected, then an inconclusive, verdict | The inconclusive verdict moves the call to the second route and serves its answer | A rejected verdict may change route with the permission; an inconclusive one stops with `response_evaluation_inconclusive` and one call | `local_contract` | two calls and the second answer served | LE-COMPOSE-015, LE-COMPOSE-011 | none |
| T22 | Retry by identity across a catalogue swap | A metered read whose answer is lost; a real publish and refresher swap with release-following grants; retries with the same identity; one with a new identity | The same identity refused as `meter_commit_unknown`; a new identity metered again | The retry returns the first bytes once from the usage row's binding, or refuses with a definite code when the bytes are gone | `local_contract`, then a D-30 release drill | refused three times; two usage records | LE-INSTANCE-021, LE-INSTANCE-022 | none; a release for the drill |
| T23 | A whole-call deadline | A loopback model server that answers in 100-byte pieces with pauses shorter than the timeout, in buffer and stream modes; a refused port; a close with no byte | Completion after 8 to 12 seconds against a 1-second deadline; a refused connection counted as sent | The call ends by its deadline on the monotonic clock; a refused connection counts zero physical requests | `local_contract`, then Toxiproxy at night | 8.41 and 11.6 seconds; one physical request for a refused port | LE-INSTANCE-020, LE-INSTANCE-024 | none |
| T24 | No network during validation or kits | The ingestion validator on an `opencode.json` that names a model; a tool schema with a remote `$ref`; the retrieval self-test with an empty cache; all with socket creation recorded and refused | Any connection attempt | Validation refuses unresolvable remote references before any connection; kits use weights pinned by revision and cached before the run | `local_contract` | connections to `models.dev` and `huggingface.co` | LE-ENGINE-011, LE-TEST-013, LE-OUTSIDE-002 | none |
| T25 | A quiesce request with no lethal default | The real `ProcessTreeController` against a real Bubblewrap-confined process that installs a handler, and against a Node.js process | The process ends on the quiesce signal; a debugger port opens; hibernation records a fence it did not perform | The process pauses through a typed channel; the report stops at `checkpoint_written` unless the controller verifies and fences | `local_contract` | SIGUSR1 ends Bubblewrap and opens the Node.js debugger | LE-LIFETIME-006, LE-STATUS-005 | none |
| T26 | Release version matrix | Pact version 4 files for every supported installer version and for the Pi extension, verified against a release candidate; a strict response schema for search hits | The installer as released at `56639ee6` passes; a body leaked into search hits passes | The old installer fails with a named mismatch before release, or is still served under its declared version; the body leak fails the schema check | `local_contract`, at every release | no release reads a consumer contract; the service refuses the old installer with `unsupported_version`; the leak passes the pact | LE-EDGE-006, LE-TEST-006, LE-TEST-012 | none |

No trial needs a model call. Twenty-four trials have a fixture form that can
run on every push: T1 to T15 without T16, T17 to T19, and T21 to T26 (T12 with
Docker, T23 also at night through Toxiproxy). T10, T11, T17 and T22 add a
release or live drill, and T16 is a drill only. T3 has a live variant that
needs a local model and its owner's authority, and T20 waits for a live
concurrency owner in the Loop runtime.

## 10. What not to adopt, and why

| Outside default | Source | Reason |
|---|---|---|
| Return the default value on any abnormal evaluation | OpenFeature requirement 1.4.10 | A failed choice must never look like a deliberate one |
| Fallback on any error; parameters optional; data collection allowed; a hosted router that degrades to a default pool and ignores options sent under another identifier | OpenRouter provider, fallback and Auto Router documentation | Fallback only on declared failure kinds within the slot's ceiling; hosted pools cannot be pinned |
| Fallback to another provider after a content refusal | LiteLLM content-policy fallbacks | A new data recipient needs permission, and failover needs `allow_failover` |
| Unsupported parts sent to a default provider; assignment recording off | ONNX Runtime 1.30.0 session options | The residual is declared or refused, and assignment is always recorded |
| Mirror all traffic when no rate is set | Istio `mirrorPercentage`; Envoy `runtime_fraction` | The comparison allowance is zero without a grant |
| Part of a pinned run sent to the current version | Temporal activity routing | Nothing below a pin is substituted |
| Exceptions logged and swallowed; a driver call returning nothing | stevedore defaults | An engine error is a typed failure kind |
| A three-part cost compared on one part | Calcite `VolcanoCost.isLe` | Each rule declares its objective and comparison |
| Learned routers, learned thresholds, market-driven pools | RouteLLM, FrugalGPT, the OpenRouter Auto Router | Heuristics wait for the one-million-run rule |
| A flag service read at selection time | The outside research | Selection reads no network and uses versioned, digested policies |
| A second graph record for composite engines | The selection line's first proposal | `loop_graph_definition/v2`, the planned `ModelCallStrategy` and the decision record already hold compositions |
| One enumeration for every binding | The lifecycle line's first proposal | The binding dimensions compose; they are not exclusive values |
| Keep the old model after a failed reload by polling the model folder | Triton POLL mode, which its own page does not recommend for production | The previous configuration keeps serving by an explicit rule and a rejected record, not by a side effect of polling |
| Replace machines before their dependencies are ready | Fly `--strategy immediate` as the release uses it today | Preparation happens inside the new release before it serves |
| Route by protocol header only | `mcp` 2.2.0 ("header-only era-routing for now") | Baltor classifies by the body first and enforces its served set |
| Treat a consumer contract as proof of absence | Pact | Absence rules need a provider-side check or a strict response schema |
| Constraint-free pairwise generation that reports verified coverage | NIST ACTS Basic 1.0 | Coverage is measured independently, and constraint warnings fail the run |
| Fetch remote schema references during validation | python-jsonschema's default retrieval | Protocol revision 2026-07-28 forbids it, and it breaks a pure engine's declared effects |

## 11. Decisions made, with reasons

The decisions are recorded once, in the standard's section "Decisions taken,
with reasons". In short: one standard linked from rule 6; BCP 14 key words,
one per statement; live defects repaired before the words land; the library
slots catalogued before rule 6 says every component has a slot; the selection
basis instead of a new mode; a fourth selection mode, all_of; the engine
composition as the composite's capability record; concurrent forms after a
live concurrency owner exists; engine adapter and wrapper layer as separate
terms; Baltor-native engine in prose with `own_code` and `own_fork` in code;
harness compatibility profile and conformance kit as the single names; three
instance fields and a swap rule; availability snapshots, owned resource
records, fencing tokens and sequence numbers instead of conditions, resource
claims and generations; binding facts instead of an activation controller;
engine swap and swap qualification instead of transition; lease rules with
the owner's clock and a maximum; separate execution fields; typed settings
records; one version change for the engine records; residency through the
existing overnight residency record and the route snapshot; peer protocol
checks that name their profile; and no outside default that substitutes
silently.

## 12. Limits

- No engine, harness or model ran against a real provider, and the live
  service was not contacted.
- The writer ran the fourteen probe scripts of section 7 on `e6346075`.
  Every other probe result comes from the line or verifier named with it.
- Outside pages were read on September 23 and 24, 2026. Pages without a
  version are identified by their page date or commit.
- The validation, activation, qualification tools and protocol revisions lines
  have verifier probe folders but no verifier report file; their verdicts are
  taken from those probes, which the writer re-ran where they matter.

## 13. Files

Under `/tmp/claude-1000/-home-username-loop-engine/4d86b429-7c1c-493e-b03d-37b529827fe7/scratchpad/components/`:

| File | What it holds |
|---|---|
| `FUNCTIONAL-COMPONENT-STANDARD-DRAFT.md`, `AGENTS-RULE-6-PROPOSAL.md`, `TERMINOLOGY-PROPOSAL.yaml` | The standard, the rule text and the terminology and register entries |
| `*-attempt-1-2026-09-24-0153.*`, `FUNCTIONAL-COMPONENT-STANDARD-DRAFT-attempt-2-2026-09-24-1027.md` | Earlier attempts, kept beside their successors |
| `repo-grounding.md`, `testing.md`, `selection-composition.md`, `lifecycle-isolation.md`, `rule-and-names.md`, `mcp-revisions.md`, `validation-conversion.md`, `activation-transition.md`, `qualification-tools.md` | The research lines |
| `repo-grounding-verification.md`, `testing-verification.md`, `testing-verification-2026-09-24.md`, `selection-composition-verification.md`, `selection-composition-verification-2.md`, `verify-lifecycle-isolation.md`, `lifecycle-isolation-adversarial-check-2026-09-24.md`, `rule-and-names-adversarial-verification.md`, `rule-and-names-adversarial-verification-2026-09-24.md`; the folders `vvc-work/`, `verify-at/`, `verify-qt/`, `vmr-work/` | The verifiers |
| `writer-run-3/probes/*_e6346075.out` and the scripts beside them | The probes of section 7 |
| `writer-run-3/statement_check_draft3.out`, `writer-run-3/statement_check_mutants_draft3.out`, `writer-run-3/mutants/` | The statement check and its planted defects |
| `writer-run-3/variant/` and its check outputs | The export of `e6346075` with the proposals applied, where the rule, vocabulary, route and link checks ran |
