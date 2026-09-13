# Harness capability matrix

What Loop Engine needs from an external coding harness, and what it must never
delegate to one. Written 2026-09-10 from the constitution, architecture.yaml,
the harness contracts and recipes, the intelligence-layer guides, and the
host-runtime experiment. Sources are cited per section.

## How to read this file

- Each row is a capability a harness either provides or does not.
- "Field status" describes the best observed behavior in current harnesses.
  It is observed evidence, not a promotion of any harness.
- The final section divides all capabilities into two groups: what a harness
  must provide, and what Loop Engine must own. A harness that owned the second
  group would be a second runtime, which the constitution forbids.
- This matrix pairs with the tiered trial pipeline (T0-T5). Static rows are
  graded at T0-T1; dynamic gates are tested at T2-T4; only finalists run T5.
  See the constitution's benchmark rules before citing any result.

## Constitution and governing rules

- Every executable graph vertex is a Loop (LE-NODE-001..009). A harness is an
  adapter used by a Loop, never a second runtime type (AGENTS.md, ADR-EXTERNAL-
  HARNESS-REALIZATIONS).
- Harness completion is not task acceptance (architecture.yaml invariant).
- An adapter declaration is not permission, and not independent qualification
  (architecture.yaml invariant; HarnessExecutionCapabilities docstring).
- Post-run budget checks do not claim preemptive enforcement (invariant;
  HarnessBudget is explicitly a post-run acceptance contract in the ADR).
- Imported and self-generated intelligence stays candidate-only until an
  independent process approves it (AGENTS.md, LE-INTEL-003).
- Fork ancestry does not establish adapter equivalence (HARNESSES research doc).
- Published results from another harness may be cited only as external
  evidence with exact population, model, version, evaluator, source, and
  limitations (AGENTS.md).

## 1. Machine interface

| # | Capability | Why it matters | Field status |
|---|---|---|---|
| 1.1 | Headless non-interactive mode | The Loop dispatches; no human at a TUI | OpenCode `run`, gptme, Codewhale |
| 1.2 | Structured event stream with a stable schema | Feeds the event normalizer; prose is unaccountable | OpenCode `--format json` |
| 1.3 | JSON-RPC or SDK embedding | Cleanest transport; no argv prompts | Pi (json mode), Hermes |
| 1.4 | Prompt via stdin, never argv | argv leaks through `ps`; secret hygiene | Hermes recipe requires it |
| 1.5 | Machine-readable version and digest reporting | Pinned identity in evidence refs | All pinned recipes |
| 1.6 | Typed exit codes: failure vs refusal vs timeout | `safe_harness_error_code` taxonomy | Rare; usually a fork patch |
| 1.7 | Stream parsable without a live terminal | Headless capture cannot depend on TUI internals | The `$bunfs` TUI-native-lib failure class is the counterexample |

## 2. Model and transport boundary

| # | Capability | Why it matters | Field status |
|---|---|---|---|
| 2.1 | Custom provider endpoint (OpenAI-compatible base URL) | Every recipe requires a `127.0.0.1` loopback relay to the ModelGateway | Nearly universal |
| 2.2 | Provider-reported usage per call (tokens in/out/cache, cost) | Accounting stays gateway-owned; missing is unknown, never zero | OpenCode `step_finish.tokens` |
| 2.3 | Exact output-capacity setting | `ModelOutputAllocation` binds to a real knob | pydantic_ai precedent |
| 2.4 | Model allow and deny list | Frozen comparison arms; no provider drift | Config files |
| 2.5 | Gateway-style auth and catalog reuse | Saves time on flows; credentials still pass through the Loop boundary, never around it | Kilo, Cline recipes |
| 2.6 | No silent failover or fallback | Retry, same-provider fallback, and cross-provider failover stay distinct | Must be patchable off |
| 2.7 | Reasoning tokens reported separately from answer tokens | `tokens.reasoning` accounting and evidence hygiene | OpenCode; most do not |
| 2.8 | Capacity resolved from a source-backed record | No invented defaults; unknown capacity is an explicit unknown result | AGENTS.md model rules |

## 3. Tool and effect management

| # | Capability | Why it matters | Field status |
|---|---|---|---|
| 3.1 | Per-tool disable lists with exact names | Effect-policy floor; no wildcards | Cline, Crush, Qwen recipes carry exact lists |
| 3.2 | Tool-to-effect classification possible | `_TOOL_EFFECTS` vocabulary: read, write, process, network, secret | Any harness, via mapping table |
| 3.3 | Synchronous allow or deny hook per tool call | Prevention before effect, not post-hoc logging | Claude Code hooks are the pattern to generalize |
| 3.4 | Dry-run or plan mode | Verification arms without effects | Several |
| 3.5 | Structured tool-call and result events (no bodies) | Run History completeness without leaking material | OpenCode |
| 3.6 | Opt-in tools only; no ambient write defaults | LE-PERM-001 spirit | Almost none; patch-level |
| 3.7 | MCP client support so tools are external adapters | Tools stay adapters, not graph vertices; catalog parity | Goose, Pi |
| 3.8 | Unknown tools and undeclared parameters refused | The tool-message translation refuses DTDs, unknown tools, duplicate params | Loop Engine's own bridge; harness must not reopen the hole |

## 4. Context and information passing

| # | Capability | Why it matters | Field status |
|---|---|---|---|
| 4.1 | Bounded, counted context injection | Context Intelligence serves typed references under a hydration ceiling | Recipes enforce it |
| 4.2 | No ambient context reads outside the grant | The `.gitignore`-on-readonly-mount and HOME-credential failures | Patch-level |
| 4.3 | Progressive disclosure; skills load on selection | CoreBundle to InstanceGrant to InstanceSelection pipeline | OpenCode skills, OpenHands triggered context |
| 4.4 | Session resume with explicit state | Spawned-Loop retry identity | OpenCode sessions |
| 4.5 | Visible, counted compaction | Budget enforcement; no magic context | OpenCode `/compact` |
| 4.6 | AGENTS.md and rules-file loading | Already the Loop Engine convention | Nearly all harnesses |
| 4.7 | Resolve once, pass exact | No re-derivation or paraphrase between steps | RESOLVE-ONCE-PASS-EXACT.md |
| 4.8 | Prompt and invocation encapsulation | No prompt text in argv, environment, or logs | PROMPT-AND-INVOCATION-ENCAPSULATION.md |

## 5. Skills, plugins, and resources

| # | Capability | Why it matters | Field status |
|---|---|---|---|
| 5.1 | Skills as files with a manifest | SkillRegistry admission; candidate-only until approved | SKILL.md convention across the field |
| 5.2 | Plugin manifests with declared resources | Frozen capability cards; no ambient plugin authority | Pi package manifests |
| 5.3 | List-then-load resource catalog | Discovery is effect-free; materialization follows selection and permission | Loop Engine selector protocol; OpenCode skills approximate it |
| 5.4 | Prompt templates as versioned data | `strings.prompt_fragments` equivalence | Several |
| 5.5 | Load success observable per resource | The experiment caught a run where both skill calls failed yet the process exited zero | Loop Engine qualification check; harness exit codes alone are insufficient |
| 5.6 | Plugin bundle distribution matches lifecycle contract | Lifecycle extension without a second registry | PLUGIN-BUNDLE-DISTRIBUTION.md, lifecycle extension contract |

## 6. Isolation and containment

| # | Capability | Why it matters | Field status |
|---|---|---|---|
| 6.1 | Runs in a network-none container with read-only mounts | Instance builder and Bubblewrap tier | Loop Engine Dockerfile proves OpenCode |
| 6.2 | Relocatable config and state directories | The EACCES and ambient-HOME failure classes | Patch-level |
| 6.3 | No TUI-native-lib extraction dependency for headless runs | The live `libopentui` `/tmp` failure | Headless modes avoid it |
| 6.4 | No update or telemetry channels, or hard disable | No uncommitted external effects | Patch-level |
| 6.5 | Non-root, UID-mappable execution | Workspace file ownership | The `ocd` container pattern |
| 6.6 | Staged expected metadata instead of relaxing read-only mounts | OpenCode tried to create `.opencode/.gitignore` on the read-only mount | The corrected instance image |

## 7. Process supervision and budgets

| # | Capability | Why it matters | Field status |
|---|---|---|---|
| 7.1 | Dies on SIGTERM within the provider timeout | Supervision between bridge frames does not preempt an in-flight call; the provider timeout still applies | Mostly fine |
| 7.2 | Preemptive limits: model calls, total tokens, cost, wall time, output, spawned tasks | Enforced before the effect; `unmet_harness_requirements` names each | gptme and Crush have partial knobs; usually a patch |
| 7.3 | No daemon or zombie persistence | Fresh instance per responsibility | OpenCode serve-versus-run distinction |
| 7.4 | Structured final artifact | Typed output port; candidate capture by the artifact manager | OpenCode final JSON |
| 7.5 | One adapter invocation per owning Loop | architecture.yaml invariant | Loop-side rule the harness must not force to break |
| 7.6 | Process supervision external to the harness | Layer-2 supervisor owns lifecycle | herdr is the field's design reference |

## 8. Records, replay, and evaluation

| # | Capability | Why it matters | Field status |
|---|---|---|---|
| 8.1 | Full event export with no hidden conversation | Run History and playback; export gates demand reproducible source | OpenCode, Crush |
| 8.2 | Deterministic replay support (recorded inputs, seeds) | Runtime-history replay arm | Rare; Loop Engine owns it |
| 8.3 | Cross-run comparison data | Frozen-arm gates: tokens, time, tool failures, repair, incorrect acceptance | Loop Engine ledger |
| 8.4 | Evaluation hooks with queryable exit criteria | Independent evaluation; harness completion is not acceptance | mini-swe precedent |
| 8.5 | Published benchmark evidence must match exactly to be comparable | Mixed population, model, version, or evaluator comparisons are unfair | examples/16 audit rule |

## 9. Forkability and vetting cost

| # | Capability | Why it matters | Field status |
|---|---|---|---|
| 9.1 | Permissive license (MIT or Apache-2.0) | Vetted-mirror fork carries notices | All top candidates |
| 9.2 | Small audit surface (Rust, Go, Python) | Per-release re-qualification cost scales with code size | Codewhale, herdr (Rust), kimi-cli (Python) |
| 9.3 | Stable extension seams that survive upgrades | Carried patches stay small | Pi extension host |
| 9.4 | Slow release cadence | The sync treadmill: 1.17.9 to 1.18.29 broke model namespaces in three weeks | Pi over OpenCode |
| 9.5 | Upstream receptivity to merged patches | The cheapest carried patch is one upstream maintains | Varies |

## 10. Cognitive-state fingerprinting and semantic identity

| # | Capability | Why it matters | Field status |
|---|---|---|---|
| 10.1 | Typed task fingerprint emission (`TaskFingerprint/v1`) | Dedup, compatibility, and routing (terminology: `core.term.task_fingerprint`) | Nobody; closest is a repo-map hash |
| 10.2 | Deterministic, ordered procedure population | The fingerprint requires an exact semantic fingerprint with an explicit empty state | No harness guarantees ordering |
| 10.3 | Compatibility assessment between tasks | Flywheel search-and-eligibility input (`CompatibilityAssessment`) | Absent; Loop Engine value-add |
| 10.4 | Execution-context fingerprints, narrow and labeled | Plans, extensions, capabilities, settings, context, intelligence, environment, verification each state which differences require revalidation; one opaque hash over unrelated state is prohibited | Absent (EXECUTION-CONTEXT-FINGERPRINTS.md) |
| 10.5 | Typed session handoff, not screenshots | `session_handoff/v1` schema with packet digest, worktree, claims, evidence records, loading plan, validity | Absent; field "handoffs" are lossy prose |
| 10.6 | Context handoff ontology | Handoff is evidence about a checkout, not architecture authority | Absent (CONTEXT-HANDOFF-ONTOLOGY.md) |

## 11. Reusability: the capability flywheel

| # | Capability | Why it matters | Field status |
|---|---|---|---|
| 11.1 | Candidate-only imported intelligence | No promotion from retrieval, a score, or model confidence | Every harness auto-activates skills; all violate |
| 11.2 | Asynchronous harvesting of solutions into a capability library | Solutions die in session logs otherwise | Absent |
| 11.3 | Discovery, eligibility, ranking, selection kept separate | Flywheel search and eligibility stages | No harness separates them |
| 11.4 | Solution Library records bound to evidence and digests | Authoritative records and projections | OpenCode sessions are untyped |
| 11.5 | Import rules for other harnesses' files and history | EXTERNAL-HARNESS-IMPORTS.md defines the four-way classification | Loop Engine owns the format; harnesses only need exportable events |
| 11.6 | Hybrid assistance profiles recorded, not implied | Flywheel hybrid assistance | Absent |
| 11.7 | Failures retained with equal prominence | Trust and failure handling; benchmark rules | No harness keeps failures as records |
| 11.8 | Repair creates a new version and digest, never rewrites | Quarantine, rollback to the same exact qualified version | Absent |

## 12. Intelligence layers

| # | Capability | Why it matters | Field status |
|---|---|---|---|
| 12.1 | Query and retrieval as first-class relationships | Search returns ranked `LoopRef` values, never bodies | RAG blobs everywhere; no graph operations |
| 12.2 | List-then-load across all four layers | Discovery effect-free; materialization after selection, digest check | Partial in OpenCode skills; no permission gate |
| 12.3 | One search across all four layers | Context, Code, Runtime History, User Feedback federated | Absent; each harness has one private silo |
| 12.4 | User Feedback Intelligence: serve, scope, interpret | Feedback as scoped guidance, not telemetry | Absent |
| 12.5 | Context Intelligence: serve, search, frame | Hierarchy under a hydration ceiling (CONTEXT-HIERARCHY.md) | Token-budget stuffing, untyped |
| 12.6 | Code Intelligence: resolve, invoke, load | Immutable source identity, license state, version, deps, digest | Aider's repo map approximates |
| 12.7 | Runtime Memory separate and run-scoped | Not a fifth layer, not persistent | Every harness memory feature violates this |
| 12.8 | Importer classifies source format explicitly | A Markdown file can be any layer; item type and source reference decide | Loop Engine importer; harness "memory" conflates |

## 13. Static architecture governance

| # | Capability | Why it matters | Field status |
|---|---|---|---|
| 13.1 | Boundary registry registration | Runtime type Loop with an exact registered profile (AGENTS.md) | Nothing registers as governed boundaries |
| 13.2 | Architecture conformance hooks | Import-boundary tests; architecture.yaml sync | No harness ships architecture tests |
| 13.3 | Component ontology and folder map | Ontology, interactions, folder map as data | Absent |
| 13.4 | Semantic data dictionary adherence | Terms resolve to terminology.yaml source-of-truth symbols | Absent; ad-hoc vocabulary |
| 13.5 | Documentation authority hierarchy | README, CONSTITUTION, architecture.yaml, then code (LE-DOC-001) | Absent |

## 14. Database and records management

| # | Capability | Why it matters | Field status |
|---|---|---|---|
| 14.1 | Managed records discipline | RecordOperationService; never rewrite rows, revisions, or views; expected-revision writes; unknown commits are not successes | No harness obeys; the 303G unvacuumed session DB is the live counterexample |
| 14.2 | Immutable revisions plus current-reference metadata | SCOPED-RECORD-OPERATIONS ADR | Absent |
| 14.3 | Exact-revision export | JSON views from pinned revisions (examples/24) | Lossy transcripts instead |
| 14.4 | Schema, namespace, write-approval preservation | Managed records guide | Absent |
| 14.5 | Session-store growth hygiene | WAL and vacuum supervision is an operations requirement | No harness manages own-DB growth |

## 15. The division: harness provides versus Loop Engine owns

This is the normative core of the matrix. A harness that owned the right
column would be a second runtime, which the constitution forbids.

```text
Harness must provide (substrate)
├── 1    Machine interface: headless, structured events, stdin prompts
├── 2    Model transport plumbing: endpoint, usage reporting, output knobs
├── 3    Tool registry surface: exact disable lists, effect-mappable calls
├── 4    Bounded context injection and resume primitives
├── 5    Skills and plugins as declarable, list-then-load files
├── 6    Sandbox tolerability: relocatable state, no telemetry, no TUI libs
├── 7    Obedient process behavior: dies on signal, no daemons, final artifact
└── 8    Exportable complete event history

Loop Engine must own (never delegated)
├── 10   Task fingerprints, compatibility, execution-context fingerprints
├── 11   The flywheel: harvesting, eligibility, promotion, repair, quarantine
├── 12   All four intelligence layers plus run-scoped Runtime Memory
├── 13   Boundary registry, conformance, ontology, semantic dictionary
├── 14   Managed records, revisions, exports, session-store hygiene
├── 7.2  Preemptive budgets (the harness exposes knobs; the host enforces)
├── 8    Replay, comparison, evaluation, acceptance
└── all  Authority: permissions, approvals, verification, promotion
```

Sections 10 through 14 are empty across the entire field not because they are
hard but because they are the product. Fork patches therefore target only
sections 1 through 9 gaps (veto hooks, event-schema pins, budget kills, config
isolation, telemetry removal). A fork patch touching sections 10 through 14
would duplicate the runtime.

## 16. Grading and trial pipeline

Static matrix rows grade at T0 and T1 (desk and stub-relay checks). Dynamic
gates test at T2 through T4. Only finalists run T5.

```text
T0  Static: license, docs, pinned-version audit surface
T1  Transport: headless run, schema parse, stdin prompt, exit codes, usage
T2  Containment: network-none, read-only mounts, no ambient config or creds
T3  Budget: kill at N calls, tokens, wall time; verify no effect after kill
T4  Effects: disable lists, veto hooks, effect classification
T5  Frozen-arm comparison: same task, provider, information, evaluator
```

- T5 never runs before T0 through T4 pass.
- Token accounting is a T1 stub-relay check, not a real-spend item. Real token
  efficiency is only measured inside T5 for the two or three finalists.
- One successful instance is a working path, not general improvement.
- Failures and unavailable arms are retained as evidence.
- First registered T5 arms: OpenCode (proven), Pi (fork-base candidate),
    Codewhale (small-audit-surface candidate). Gateway-harness recipes
    (Kilo, Cline) stay static-graded until a task needs their catalog.

## Sources

- AGENTS.md; docs/architecture/CONSTITUTION.md (LE-NODE, LE-PERM, LE-INTEL,
  LE-DOC, LE-VERSION, LE-RUNTIME, LE-PLUGIN, LE-GOV, LE-TRUST)
- architecture.yaml `external_harness_execution` invariants and unproven list
- src/loop_engine/core/harness_execution_contracts.py;
  external_harness.py; opencode_harness_adapter.py; the pinned
  `harness_*recipe*.py` modules (Cline 3.0.61, Kilo 7.5.16, Hermes 0.21.1,
  ForgeCode 2.13.21, Crush 0.92.0, Qwen Code 0.23.1, Mistral Vibe 2.25.0,
  gptme 0.33.0, nanocode, mini-swe, Goose, Gemini, OpenCode)
- docs/research/HARNESSES-AS-OPTIONAL-LOOP-EXECUTORS-2026-09-06.md
- docs/architecture/ADR-EXTERNAL-HARNESS-REALIZATIONS.md;
  ADR-HOST-OWNED-EXECUTION.md; ADR-REUSABLE-CAPABILITY-FLYWHEEL.md;
  ADR-REASONED-OUTPUT-ALLOCATION.md; EXECUTION-CONTEXT-FINGERPRINTS.md;
  CONTEXT-HANDOFF-ONTOLOGY.md; RESOLVE-ONCE-PASS-EXACT.md;
  PROMPT-AND-INVOCATION-ENCAPSULATION.md; PLUGIN-BUNDLE-DISTRIBUTION.md;
  HCF-CONCEPT-FIT.md; SEMANTIC-RUNTIME.md
- docs/contracts/README.md; docs/contracts/session-handoff.schema.json
- docs/components/intelligence-layers/ (README, INTELLIGENCE-AS-LOOPS,
  EXTERNAL-HARNESS-IMPORTS, REUSABLE-CAPABILITY-FLYWHEEL,
  RUNTIME-HISTORY-AND-SOLUTION-INTELLIGENCE, USER-FEEDBACK-INTELLIGENCE,
  CONTEXT-HIERARCHY, CODE-INTELLIGENCE-TEMPLATES)
- terminology.yaml (`core.term.task_fingerprint` family,
  `core.term.execution_context_fingerprint`)
- examples/16_compare_complex_harnesses; examples/25_host_runtime
  (OPENCODE-INSTANCES.md, opencode_stdio_bridge.mjs,
  opencode_gateway_bridge.py, resource selection, novel-task campaign)
