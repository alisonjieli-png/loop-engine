# Loop Engine and related systems: review and experimental build plans

Review date: 2026-09-07, America/New_York. This is a review and design deliverable, not an implementation or deployment. Proposed variants below have not been built by this review.

Loop Engine is the strongest foundation in this collection for governed execution, typed composition, independent verification, and durable asynchronous work. The smaller engines provide useful, more direct experiments in tool use, bounded state, repair workflows, and script reuse. The evidence does not establish that OpenCode per step is generally better than native Loop execution. They solve different parts of the problem and should be compared behind the same task and verification contracts.

Several claims in the supplied build documents are false on the inspected code, even though the repositories' test suites pass. The most urgent work is to repair acceptance, reuse transactions, evaluator controls, and the wiring of declared settings. Adding more named capabilities before those repairs would increase the gap between the documentation and behavior.

## 1. Scope, revisions, and meaning of evidence

All tracked file identities in the six located repositories were inventoried with byte counts and SHA-256 digests. The accompanying inventory is not a claim that every line received individual inspection. The review traces representative production paths across the complete component families below, runs the available local suites, and adds targeted executable probes. Branches were inspected through Git without checking them out or merging them.

| Source | Revision inspected | Coverage and limits |
|---|---|---|
| `/home/username/loop-engine` | `5d4e7c4e14d65975e046a05b3493ce8faec0e2ed`, then `692db36b718df490ddddce835a04919a239c0eef` | Architecture, solve, memory, admission, authority, reuse, host operations, reactive work, portfolios, checkpoints, adapters, benchmarks, CI. The intervening change contains four documentation files; tested runtime code is unchanged. |
| `/home/username/overnight` | `bde78862b50a55f6d8751f39206e4f7227aa2a68`, then `c1d3efdc02bf2284312b65e8474791762cf666d1` | Both repair and recursive paths, session, admission, routing, memory, transports, sandbox, batch runner, all 1,000 task-folder identities. The later commit adds the universal document and a task memory database. |
| `/home/username/new_overnight_build` | `44854dabeddde69ced8ae5815a20440331b0787b`, then `3d89c713c074356ef8c6e5a8c72d2881546a3551` | Solver, catalog, patch tool, composer, library, distill, rollback, modes, context, tickets, benchmark records, SaaS boundaries. The intervening changes are documentation, not new runtime implementations. |
| `/home/username/vigil` | `872e2db937b8ad1f46d2fa8542e1fbb687c0615a`, then `ea2b414ca1677e41159be01733a66bd4e4a17a9a` | Candidate lifecycle, gate and regression paths, intake, isolation, delivery, fingerprints and router. The later change adds a build document. |
| `/home/username/speculative_prompting` | `86d857357a983a2dd0b7d0cc2ccb961b862ad290` | TypeScript daemon execution and state, product architecture, privacy, sync and control-plane tests, research and integration documents. Existing untracked briefs remain user/concurrent work. |
| `/home/username/ollama-loop-behavior-lab` | `e3501f32626b1634a47e48d4a1c5897e0d1e0bef` | Additional independent reference discovered during the search: qualification, liveness, hierarchical execution, observability, and full unit suite. This is not assumed to be the requested `loop-node` repository. |
| Loop Engine `origin/overnight/opencode-step-instances` | `a8b964e425cc2a746d8f4bdad5363576d7cba695` | Source inspection of multi-path worktrees, provisioning, checkpoint and solution-retention mechanisms, plus harness launch. No branch-wide test rerun. |
| Loop Engine `origin/fork/reconciled` | `94bf890e67c6d87fe50ae08147ffc64152ea6be1` | Source inspection of supervision changes, history authorship, reconciliation record. Not treated as main or as a qualified replacement. |
| Loop Engine `origin/fork/hardened-learning` | `3c89f735fd68107a40c17ebdb0bb121ef15d76cc` | Revision and lineage identified; the reconciled branch is the selected source for the relevant follow-up. Not a separate full audit. |
| `/home/username/overnight-docs` | No Git revision | Reference collection, including reconciliation, transport, earlier audits, build briefs, and harness failure notes. Historical claims require current-code confirmation. |
| `~/loop-node` | Not located | No matching directory found in the scoped home-directory search. Exact path requested. No coverage is claimed for an unidentified repository. |

Agent processes were active in several of these directories. The review did not interrupt them, edit implementation files, commit, merge, push, or publish. The report and its diagnostic artifacts are new review outputs.

Evidence labels in this report mean:

| Label | What it establishes |
|---|---|
| Reproduced | The review executed the behavior using disposable fixtures or an existing test. A fixture model does not establish provider quality. |
| Source | The named current call path or implementation was inspected. This is weaker than an execution result. |
| Saved run | An existing record was inspected. Its population, evaluator, route, and limitations remain part of the claim. |
| Proposed | A design and qualification plan, not current behavior. |
| Missing | Not located, not connected, or not established by this review, as specified. |

## 2. Fresh checks

| Check | Observed result | Practical limit |
|---|---|---|
| Loop Engine full self-test | 3,412 / 3,412; 438.472 seconds; reports 0 provider calls | Offline checks, including embedded component tests. Not 3,412 benchmark tasks. |
| Loop Engine conformance | All 27 displayed gates passed | Architectural conformance does not establish end-to-end feature reachability or task correctness. |
| Loop Engine hardcoding delta audit | Exit 1; 3,032 new findings in the audit output; 12,926 material findings overall | Static findings need disposition. These counts are not counts of demonstrated software defects. |
| Latest Loop Engine GitHub CI | Failed for Python 3.10, 3.11, and 3.12 at `Self-orientation and hardcoding delta gates`; documentation and distribution jobs succeeded | [Run for 692db36](https://github.com/alisonjieli-png/loop-engine/actions/runs/34182700323). A locally green self-test is not green CI. |
| overnight pytest | 89 passed, 13.94 seconds | The default suite includes a test that launches OpenCode. That test ran, but it does not assert a successful provider reply or record its physical-call/cost completeness. Do not label this entire suite provider-free. |
| vigil pytest | 178 passed, 1 explicitly deselected, 23.40 seconds | The deselected test is the live OpenCode transport probe. Local fixtures include actual temporary Git and sandbox operations. |
| new_overnight_build pytest | 74 passed, 151.07 seconds | Scripted model transport, generated local resources, and local HTTP fixtures. |
| TypeScript daemon | 477 passed in 26 test files | Executed under Node 22.22.1, below the project's declared Node >=24.15. This does not qualify the required runtime version. |
| TypeScript shared / DB / web | 22 / 28 / 123 passed; 7 DB and 33 web checks skipped | Database URLs deliberately unset. No shared database was mutated. Database integration and browser behavior remain unqualified by these runs. |
| Independent behavior lab | 137 tests passed, 23.728 seconds | Scripted/local component evidence, not a fresh live model qualification. |

Python checks here used the available Python 3.14 interpreter. No new model-performance campaign was run. Existing live runs were read, not repeated against their already-used holdouts.

## 3. Findings that change the build plan

P1 means fix before relying on the affected acceptance, containment, or benchmark claim. P2 means a feature or experiment can misbehave or be misleading. These priorities are review judgments, not CVSS ratings.

| Priority | Finding and evidence | Required correction |
|---|---|---|
| P1 | **A distill step can invalidate a verified deliverable without invalidating the result.** A scripted build wrote a correct file; distill replaced it with incorrect text; `Solver.solve` returned `status=verified`, `verified=true`. Reproduced. [solver.py:219](/home/username/new_overnight_build/poc/solver.py:219) | Freeze the accepted artifact set, isolate distillation, and rerun the authoritative acceptance checks after the final effect that could change delivery. |
| P1 | **A void run can publish a reusable verified solution.** A fixture changed `.gate/check.py` to `pass`; the run ended `void`, but its library contained a `verified` record. Harvest commits before the final integrity decision. Reproduced. [library.py:289](/home/username/new_overnight_build/poc/library.py:289) | Stage the candidate, validate the original evaluator and frozen subject, then commit qualification. Invalid producer runs must not leave executable qualified assets. |
| P1 | **Failed replay does not restore every touched file.** A deleted script stayed deleted and an unrelated modified helper retained its changed bytes. `restore` iterates currently existing files; the solver saves original bodies only for `sol.files`. Reproduced. [library.py:74](/home/username/new_overnight_build/poc/library.py:74), [solver.py:523](/home/username/new_overnight_build/poc/solver.py:523) | Replay in a disposable complete workspace or transactional overlay; test deletion, rename, new files, nested outputs, binary outputs, and input mutation. |
| P1 | **The sandbox selection does not cover all code execution.** In the PoC, library replay/qualification uses `default_runner`, and gates use a separate host subprocess. In overnight, the recursive/batch gate paths bypass the sandbox hook in the separate `OvernightLoop`. Source. [library.py:154](/home/username/new_overnight_build/poc/library.py:154), [batch_runner.py:138](/home/username/overnight/tools/batch_runner.py:138) | Route build commands, gates, distill qualification, and replay through one explicitly selected execution boundary. Test the final launched process, not just the sandbox command builder. |
| P1 | **overnight records an admission refusal and still applies the reply.** A complete prompt echo was recorded `rejected:echo`; the next record was `orienter:ok`, and the echoed hypothesis entered state. Reproduced. [recursive_solver.py:700](/home/username/overnight/core/recursive_solver.py:700) | Make admission disposition control patch application. A failed repair must never leave its rejected patch eligible for application. |
| P1 | **The 1,000-folder corpus contains systematically malformed data.** `make_csv(path, header, rows)` is called with rows and header reversed. Census: 400 malformed CSVs across 200 tasks. Reproduced by parsing headers. [gen_corpus_1000.py:48](/home/username/overnight/tools/gen_corpus_1000.py:48) | Correct and version the generator, regenerate into a new population, validate every resource contract before model evaluation, and preserve the invalid population's identity. |
| P1 | **All 100 file-transform gates contain an invalid pandas chained comparison.** After reconstructing the intended input in a disposable fixture, a correct transform failed with `ValueError: The truth value of a Series is ambiguous`. Reproduced; matching defect found in 100 gates. [gen_corpus_1000.py:140](/home/username/overnight/tools/gen_corpus_1000.py:140) | Qualify each oracle with both a correct reference and deliberately wrong controls. Parenthesize the boolean comparisons and verify counts against original inputs. |
| P1 | **Loop Engine's unsuccessful-pass ceiling does not supervise the open profile.** An `open`, deterministic, `accepted_success` Loop remained nonterminal after 50 distinct failed attempts while its declared unsuccessful-pass ceiling was 9. Reproduced with a bounded probe. [recursive_loop.py:1302](/home/username/loop-engine/src/loop_engine/loop/recursive_loop.py:1302) | Define supervision for open profiles explicitly. The reconciled branch offers an iteration-backstop design, but it needs integration and tests that distinguish an intentional ongoing series from one stuck activation. |
| P2 | **Model tiers are metadata-only in overnight's inspected session path.** `model_tier=fixture/strong` still launched `-m fixture/base`. Reproduced with captured launch arguments. [recursive_solver.py:673](/home/username/overnight/core/recursive_solver.py:673), [opencode_step_session.py:449](/home/username/overnight/core/opencode_step_session.py:449) | Bind the selected exact route into the executable request; assert actual launch/provider identity and authority for every retry as well. |
| P2 | **Three declared transport arms do not deliver as claimed.** `env` supplied no package environment variable; `stdin` passed no input bytes; `ledger-ref` raised `PackageError` because the session builds only a procedure part. Reproduced with an injected transport. [opencode_step_session.py:385](/home/username/overnight/core/opencode_step_session.py:385), [node_package.py:264](/home/username/overnight/core/node_package.py:264) | Use the selected transport's execution path and construct actual named parts. Verify payload hashes at the consumer for every arm. |
| P2 | **Procedural mining queries the wrong SQLite connection.** A fresh `TypedMemoryStore.mine_procedure(HistoryDB(...))` raised `OperationalError: no such table: task_history`. Reproduced. [typed_memory.py:172](/home/username/overnight/core/typed_memory.py:172) | Query the supplied history authority. Also use recorded step kinds, filter by family, and preserve distinct verified-run identities. |
| P2 | **Semantic-memory promotion has no independent-review enforcement.** An empty match string and empty reviewer promoted a fixture fact, which was served as truth. Reproduced. [typed_memory.py:146](/home/username/overnight/core/typed_memory.py:146) | Bind an exact candidate revision to an authenticated review decision and separate promotion authority. A reviewer string or run suffix is not independence. |
| P2 | **The shortcut drift guard is optional and its solver caller does not activate it.** `propose_shortcut` needs `engine_root` and `profile_dict`; `RecursiveSolver.run` passes neither. Missing fingerprints also pass the guarded branch. Source. [recursive_solver.py:312](/home/username/overnight/core/recursive_solver.py:312), [run_history.py:268](/home/username/overnight/core/run_history.py:268) | Require a validated execution-context binding before dispatch, including missing-identity refusal; return structured drift reasons. |
| P2 | **A profile switch is overwritten.** `RuntimeProfile(memory=False)` produced `solver.memory_enabled=True` with default constructor arguments. Reproduced. [recursive_solver.py:246](/home/username/overnight/core/recursive_solver.py:246) | Resolve precedence once and record it. Test profiles against executed behavior so an ablation cannot silently re-enable treatment. |
| P2 | **The new learned-memory hook serves irrelevant high-confidence facts.** A target-column/stratified-split claim was served to `render HTML calendar`. Its test named “unrelated task is not served” accepts both `nothing_matched` and `served`. Reproduced. [solve_learned_memory.py:205](/home/username/loop-engine/src/loop_engine/code_nodes/solve_learned_memory.py:205), [query.py:201](/home/username/loop-engine/src/loop_engine/memory/query/query.py:201) | Establish applicability before ranking; assert negative retrieval behavior. Keep this advisory until benefit and negative transfer are measured. |
| P2 | **The learned-memory hook can raise outside its advertised failure boundary.** A fixture `PermissionError` from `journal_file.stat()` escaped the solve helper because the stat is before its `try`. Reproduced. [solve_learned_memory.py:106](/home/username/loop-engine/src/loop_engine/code_nodes/solve_learned_memory.py:106) | Put filesystem inspection and read validation under the typed unavailable-result boundary; revalidate against concurrent replacement. |
| P2 | **vigil's data-driven router is not connected to its candidate loop.** Source search finds `vigil.router` use in tests but no production `decide`/`record_outcome` integration in `vigil.loop` or CLI. Source. [router.py](/home/username/vigil/vigil/router.py), [loop.py:122](/home/username/vigil/vigil/loop.py:122) | Wire decision, actual selected arm, outcome, and censored attempt into one run identity; verify the setting changes the path. |
| P2 | **Benchmark call totals conflate model-bearing nodes with physical model calls.** The PoC benchmark computes calls as the number of nodes with nonzero input tokens; a harness node can contain multiple provider turns. Source. [bench.py:58](/home/username/new_overnight_build/poc/bench.py:58) | Count physical `step_finish` calls separately, retain cache and reasoning dimensions, and preserve unknown usage instead of converting it to zero. |

The ML corpus gate is also too weak for a model-quality claim: after fixing only the malformed schema in a disposable fixture, copied dummy sample predictions plus a `pass` Python file passed the unchanged gate. This establishes submission-format acceptance, not training, holdout performance, or honest tuning.

These findings do not erase the successful runs. They narrow what those runs establish and identify failure paths absent from the current tests.

## 4. Corrections to the supplied universal specification

The 21-point checker mostly counts catalog entries and searches for strings. It cannot justify “every factual claim machine-verified.” Several of its passing checks coexist with the failures above.

| Specification claim | Correct interpretation |
|---|---|
| All advanced features are wired | Some are live, some optional, some API-only, some recorded without affecting behavior, and some broken. The evidence level must belong to an exact entry point and configuration. |
| Loop Engine memory has zero solve callers | Superseded by commit `83ecee6`: approved semantic claims now enter the ordinary solve advisory mapping. This is not evidence that episodic/procedural learning or warm reuse is automatic. Active stage-assistance experiment arms use a separate path. |
| Distill is read-only | The PoC catalog gives distill `builder()` permissions because it writes a script. A safer alternative is a read-only proposal whose typed file delta is applied by an authorized engine operation. These are two different implementations. |
| Verify with bash and no edit is read-only | Bash can write. True read-only work needs operating-system constraints or no shell, plus controlled custom tools. |
| `.gate/` and `context.db` hashing proves integrity | It detects the inspected changes at the measured moments. It does not prevent read leakage, write-and-restore attacks, forged allowed events, mutation between observations, or mutations to untracked WAL/other authorities. |
| Only an exit code is evidence | It is evidence of that process result. Whether the gate measures the requested task must be established separately. The corpus shows both false red and weak green outcomes. |
| A number in inputs is a parameter; only output-only numbers are answers | Useful subtraction for a recitation heuristic, not a semantic definition. An answer may equal an input accidentally; a program constant may legitimately equal an output. Expressions, encodings, binary assets, nested files, and small values evade the current scan. |
| Token-free implies cheap in every sense | It removes model inference calls. Code execution, verification, storage, and data transfer still consume time and resources. |
| Fixed-size P/S/O means all harness context is constant | It bounds the between-Loop packet under a fixed bounded schema. A tool-using harness may accumulate a conversation within the step. Total provider tokens need separate measurement. |
| Custom-tool schema means every provider enforces constrained decoding | OpenCode supports typed tool arguments and validation. Provider-side constrained generation must be qualified per exact route; it is not proven by the generated TypeScript source. |
| Every sandbox uses a pinned image and never downgrades | overnight defaults to mutable `python:3.12-slim`; its Docker arguments omit several protections claimed in prose. vigil's `auto` mode can use `none` with a reported reason; explicit `bwrap` refuses when unavailable. The PoC's step sandbox leaves network shared. |
| All six transports work | Three inspected session arms fail as described above. `blob` and `hybrid` currently package the full rendered prompt as one `procedure` part, so “per-part” attribution is mostly one bucket. |
| Untracked files are not dirty | Generated caches need exclusions. Untracked user source and data still need preservation and isolation. A categorical exemption is unsafe. |
| Never commit applies to all systems | overnight retains uncommitted attempts; vigil deliberately commits on a branch and can publish when configured. This is a delivery-policy difference to model explicitly. |
| Repeating a successful pattern twice proves a reusable procedure | Two observations are a minimum sample rule, not proof of generalization, causal benefit, or independent qualification. |
| Parallel arms are almost free; success is `1 - product(1-p)` | That probability assumes independence. Local models contend for GPU memory and compute; errors are correlated; joining all arms and returning first verified have different latency. Measure throughput and correlation. |

## 5. Complete architecture coverage map

The reference classification remains:

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

This review includes all nine package ownership groups from `architecture_map.py`: ontology, loop, strings, code_nodes, core, catalog, memory, generation, and templates, plus package plumbing, devtools, examples, integrations, benchmarks, and the presentation surface. “Included” means inventoried and covered at the boundary level shown below, not individually proved in every configuration.

| Component family | Current Loop Engine implementation | Useful counterpart / gap to investigate |
|---|---|---|
| Runtime identity, definitions, roles and relationships | One Loop; exact definitions and graph references; conformance checks | Other engines use their own step classes. Adapt their behavior into profiles rather than importing a second runtime. |
| Step profiles and conditions | Reference nine-step, compact, custom, open; continuation and exit separate | PoC catalog offers useful cognitive procedures. Open-profile supervision needs repair. |
| Task intake and clarification | Typed original input, answer slots, autonomous abstention, source admission | vigil CI/JUnit/transcript intake; TS byte-offset intake and rejected-proposal memory. |
| Planning and task contracts | Versioned plan and task slices; dependency contracts | PoC adaptive divide-on-failure is a useful selectable strategy, not a universal rule. |
| Typed values and Solution DAGs | Definition pins, graph validation, adapters and named port roles | Full units, shapes, encodings, and field constraints are not enforced at every edge. |
| Native semantic execution | ModelGateway plus typed admission and acceptance | Lowest process overhead. Physical capabilities depend on installed bindings. |
| Transactional semantic runtime | Candidate output, issued verification, effect authorization and trusted-state commit | Useful for interpretation without a conventional function body. API/component evidence is not a general solver-quality claim. |
| Model routing and three modes | Per-Loop mode and exact model authority; explicit fallback | overnight's metadata-only tiers show why wire identity must be observed. |
| Response admission and schemas | Deterministic normalization plus optional schema validation | PoC writable-field `emit_patch` is a useful additional channel; partial application needs cross-field transaction rules. |
| Prompt construction and context budgets | Versioned fragments, work packets, manifests, compaction decisions | overnight horizons and PoC head/tail views are simple alternatives to compare. |
| Information references and materialization | Scope, authority, byte limit, identity and digest checks | Existing adaptive reference delivery is refused where the consumer cannot materialize it. Build a broker, not a raw shared DB grant. |
| Information-theory measurements | Offline update, predictive-state and state-policy assessments | Current measurements grant no routing/promotion authority. Held-out usefulness and calibration remain missing. |
| Four persistent intelligence layers | Context; Code; Runtime History and Solution; User Feedback | Keep layer identity distinct from formats, embeddings, memory views, and storage backends. |
| Search and ranking | Lexical/vector seams, eligibility, selection and materialization contracts | overnight TF-IDF is lexical; it is not paraphrase understanding and its inspected norm uses only overlapping terms. |
| Runtime Memory and learned records | Temporary working state plus typed episodic, semantic and procedural records; governed journal | New solve hook currently projects semantic claims only. Relevance and error handling need fixes. |
| Fingerprints | Task, stage, execution-context and progress identities serve different purposes | vigil hierarchical routing keys add statistical backoff; they do not grant reuse authority. |
| Reuse and distillation | Code-asset admission, flywheel, optional opportunity observation, qualification/promotion, deterministic invocation | PoC proves a narrow live reuse path but lacks transactional guarantees. Wire Loop Engine's optional ports in one supported host configuration. |
| Reusable container/service capabilities | Typed capability/host seams and package/repository concepts | Pulling and wiring arbitrary reviewed OCI services is not an established product path. It needs image, license, contract, effects and lifecycle bindings. |
| Workspaces and code execution | Restricted local and hardened Docker implementations; explicit authority | vigil contributes hermetic settings and instruction quarantine; qualify execution coverage across all paths. |
| MCP, skills, plugins and extensions | Existing registries, versioned handshakes, candidate admission and drift refusal | A custom tool is privileged engine code; its implementation needs its own scope checks. |
| Web research and provider adapters | Registered capabilities/internal adapters through owned Loops | A catalog entry or installed key is not evidence of a working live route. |
| Host operations and independent gates | Host-owned effects, state-bound observations, completion checks and separate verifier | Natural integration point for vigil and the TS local agent; arbitrary host callback security remains a host responsibility. |
| Failure classification and recovery | Typed failure, diagnosis/recovery panel, supervised resets, explicit budget/authority termination | Distinguish transport retry, formatting repair, task replanning, process restart and external-effect reconciliation. |
| Parallel work | `parallel_runner`, conflict-aware branch/join contracts, development execution; async delegation | Adaptive Practitioner spawning is presently serial. The overnight branch has parallel independent worktrees and a final selector. |
| Durable reactive work | SQLite activation/lease state, fencing, attempts, optional heartbeat and asynchronous workers | A host must install handlers, history and heartbeat policy. A generic always-on service is not automatically provided by the solve CLI. |
| Restart and checkpoint | Typed checkpoint restore; running/queued Spawned work restored as interrupted | Restoring metadata is not resuming a coroutine or safely repeating an effect. TS intake cursor resume is a different capability. |
| Best results and result portfolios | Immutable candidate/evaluation records; verified top-k, Pareto and as-of projections | Build periodic evaluation and publication into the host service. Randomized candidate generation is separate from serving verified output. |
| Run History and playback | Chained records, saved outcome binding, usage completeness, projections and trace export | Digests establish consistency, not automatically authenticated authorship. Reconciled-branch signing is not wired throughout the live runtime. |
| Governance and self-improvement | Candidate isolation, independent review and explicit promotion | Repeated task success and model confidence must never self-promote code or policy. |
| Managed records and catalogs | Record operations, artifact contracts, existing stores and projections | Reuse them for notes and reports; do not add one database per new “memory type.” |
| Benchmarking and qualification | Registry, native evidence, host examples, independent qualification lab, repaired campaign version 2 | Some version-1 campaign claims have later corrections. A fresh population is needed for a fresh unseen-task claim. |
| Product setup and delivery | CLI, settings, doctor, host API, Studio/report assets and package checks | TS contributes devices, sync, organizations and control plane; vigil contributes a practical branch/PR workflow. Browser and production deployment were not requalified here. |

The current static solve import closure is 240 of 430 shipped Python modules, with all eight declared required modules reachable. This is a static upper-bound approximation that also follows imports inside functions and tests. It is not 240 modules observed performing useful work. Unreached modules may legitimately belong to another entry point.

The complete role-profile branches relevant to adaptation are:

```text
Loop role profiles
├── Practitioner
│   ├── reference nine-step
│   ├── compact five-step
│   ├── research
│   ├── solver
│   ├── verifier
│   ├── code execution
│   └── self-improvement task
├── Intelligence
│   ├── cross-layer search and materialize
│   ├── Context Intelligence: serve, search, and frame
│   ├── Code Intelligence: resolve, invoke, and load
│   ├── Runtime History and Solution Intelligence: search, replay, and compare
│   └── User Feedback Intelligence: serve, scope, and interpret
└── Solution
    ├── atomic component
    ├── pipeline
    ├── router and fallback
    ├── ensemble
    └── validator
```

## 6. System comparison

| System | Main implementation method | Strength and flexibility | Fragility / current limit | Best contribution |
|---|---|---|---|---|
| Loop Engine main | Typed Loop runtime, native model gateway, capability/host execution, optional reactive machinery | Most complete authority, lifecycle, composition, verification, and history model | Many optional paths; some offline research surfaces; open-profile supervision defect; CI audit fails | Shared governed runtime and acceptance boundary |
| Loop Engine overnight branch | OpenCode per step, provisioning, parallel worktrees, final path selection, retained attempts | Explores several models and preserves alternatives | Branch-specific lineage; selector waits for all futures; snapshot retention is not reasoning resume; agreement is not correctness | Parallel attempt and retention experiments |
| Loop Engine reconciled fork | Alternative supervision and history-authorship hardening | Useful fixes to compare against main's current gaps | Different baseline; some authorship wiring still missing; no full branch qualification in this review | Small, independently reproved hardening changes |
| overnight | Recursive OpenCode/gateway solver plus a separate repair loop, profile experiments, ledger pull, 1,000 fixtures | Broad experimental knobs and fast iteration | Several knobs do not affect execution; broken corpus generation/oracles; default completion can consult model-carried metrics | Horizon views and transport experiment scaffolding after repair |
| new_overnight_build | Adaptive attempt/split, writable-field patch tool, static/model/hybrid composers, script harvest/replay | Strongest compact demonstration of reuse on different input instances; generated ticket resources | Stale acceptance after distill, nontransactional harvest/rollback, host replay/gates, incomplete accounting | Patch channel, baseline experiments and regeneration workflow |
| vigil | CI-failure intake, hermetic OpenCode steps, attempts, regression checks, branch delivery | Most direct repair-product flow; clear operator controls and negative outcomes | Serial candidates; router unconnected; step network stays open; no durable continuous portfolio | Intake, quarantine, regression checks, cancellation and delivery discipline |
| speculative_prompting | TypeScript local daemon generates structured edits; engine applies and gates; optional web control plane | Product setup, sync schemas, privacy, local state, rejection memory and byte-offset intake | Model's file view is preselected; richer lesson/audit surfaces remain design; no full process sandbox | Local execution arm and product/control-plane shell |
| Independent behavior lab | Small typed reference runtime and qualification scenarios | Separates activity from progress; tests liveness, hierarchy, atomic granularity and evidence grades | Independent reference, not a production substitute or proof of generalization | Black-box conformance and falsification cases |

## 7. Seven experimental embodiments

These are proposed combinations of execution, context, scheduling and reuse policies. They are not seven new runtime classes. Every executable operation integrated into Loop Engine remains a classified Loop with an exact versioned profile, typed ports, conditions, authority and history. A harness process, a scheduler, a storage service and a container are implementation mechanics.

| Variant | Concrete design | Build boundary and sequence | Benefit to test | Failure/fallback and qualification |
|---|---|---|---|---|
| **A. Native compact solver** | Starting Practitioner uses native model calls and a compact bounded state packet; deterministic Solution Loops perform mechanical work | Extend existing `SolveRequest`, adaptive work packets and host capabilities. Add an explicit context policy, then an optional writable-field patch adapter | Process overhead and exact accounting; simplest matched baseline | Missing capability yields a typed gap. Test schema rejection, original-task preservation, no-key deterministic behavior, and independent acceptance |
| **B. Isolated OpenCode per action** | Native decisions; one isolated OpenCode instance for an action needing repository tools | Extend the existing external-harness/host bridge. Pin image/config/tools; add a reviewed writable-workspace profile with frozen evaluator outside it | Rich file/tool agency with bounded damage and independent history | Missing qualified profile refuses. Test no credentials in worker, denied network, process-tree cancellation, cross-Loop file denial, and real edits followed by host verification |
| **C. Per-run OpenCode server with fresh sessions** | One server process per run; a fresh session and explicit packet per Loop | Implement behind the same harness adapter, using OpenCode's server API. Preserve model authority at the host; make process reuse independent of conversation reuse | Startup savings without mandatory history growth | Server failure marks affected requests interrupted/unknown as appropriate. Test session isolation, reconnect deduplication, config drift, cancelled requests, and identical payload/usage accounting. Prefix-cache benefit must be measured |
| **D. Local agent under a Loop Engine host** | Loop Engine owns reasoning/acceptance; vigil or the TS daemon owns local worktrees and registered machine operations | Bind existing local operations through `HostRuntimeBinding`; preserve engine-issued operation IDs, scoped grants and frozen host completion gates | Reuse the strongest runtime and the most practical operator workflow without a repository merger | Offline agent queues or refuses exact work; changed checkout/state requires a fresh bound decision. Test unauthorized delivery, duplicate operations, missing devices, malformed observations, and optional sync with no private bodies |
| **E. Parallel verified portfolio** | Independent candidate Loops run in isolated workspaces; independent verifier assesses each; first verified may be returned while further candidates improve the portfolio | Use `development_execution`, `parallel_runner`, existing delegation contracts and `reactive_outputs`. Compare first-success, all, quorum and ensemble explicitly | Time to first verified answer, final quality, throughput per hardware-hour | Failed/cancelled candidates stay recorded. Test shared-resource limits, overlapping writes, stale completions, correlated wrong answers, atomic incumbent replacement, and loser cancellation |
| **F. Durable continuous solver** | A persistent responsibility creates finite activations on schedules, new information or verification expiry; consumers read versioned results while work continues | Wire the existing reactive scheduler/worker, exact handlers, history policy, heartbeat, output store and information resolver into one supported host service | Useful output during long runs; restart recovery; repeated improvement with bounded resource consumption | Lease recovery is not silent effect replay. Test crashes at every transition, duplicate triggers, stale fences, reconciliation, restart without provider conversation, policy/version drift and as-of reads |
| **G. Reuse-first executable capability system** | Search reviewed code/package/service assets; deterministic invocation on exact compatible input region; model-led build/distill only on a real gap | Connect existing capability need/resolution/harvest ports in a host profile. Add the smallest typed OCI/service realization contract at the existing capability boundary | Repeated-task savings, lower time to first answer, fewer implementation errors | Missing or drifted assets refuse or fall back under an explicit policy. Test fresh-instance replay, environment drift, stale approval, hostile outputs, image failure, cleanup, negative transfer and independent promotion |

Recommended build order is A as a stable control, B and D for useful agency, G after transaction repairs, then E and F for scale and durability. C is a measured optimization, not a prerequisite. Keep all admitted variants selectable; a better result in one task family does not justify deleting another method.

For each variant, prepare one immutable experiment manifest naming:

```text
variant and version
source revisions + exact Loop definitions/profiles
task-population digest + split identity
model route + capacity/allocation + permitted effects
context policy + state schema + transport
workspace/image/environment identity
concurrency/queue/CPU/GPU/memory policy
reuse and learning state at start
independent evaluator identity + correctness controls
timeout/cancellation/restart/reconciliation policy
selected metrics + complete outcome and usage records
```

Do not implement all combinations at once. Establish each single axis under a matched control, then measure the combinations justified by those results.

## 8. Context transport and the shared ledger

The useful default is a small engine-resolved packet plus scoped references for optional material. The long-horizon task/authority, medium-horizon accepted plan and findings, and short-horizon observation belong to separately identifiable parts. They can travel in one private file, several files, or a frame without becoming separate databases.

| Transport | Useful when | Cost / failure point | Current status |
|---|---|---|---|
| In-process packet | Native Loop implementation | No process transport; still has model/context cost | Existing Loop Engine path |
| One private content-addressed file | Stable small launch packet | Mount/access/digest checks; file lifetime | Working pattern in the smaller engines |
| Several scoped files | Distinct reusable packet parts | More attachment metadata; still injected content | Saved transcript measurement exists; not a universal token price |
| Framed stdin/stdout | Brokered isolated harness | Framing, bounds, cancellation and deadlock handling | Existing read-only Loop Engine bridge |
| Model-requested pull by reference | Large optional corpus or missing evidence | Extra model/tool turn, latency, authorization and load amplification | Prototype mechanism; overnight's reference-only launch is currently broken |
| Environment payload | Special controlled adapter experiment | Size limits, inheritance, crash dumps and missing consumer contract | overnight's session does not deliver its declared payload |
| Full argv payload | Deliberate local experiment only | Per-argument and total argv/environment limits; process visibility | Unsuitable as the normal product transport |

A reference should bind content identity, contract, scope and requesting Loop. It should not reveal or grant a raw database path. Search should return small typed references; the host then checks eligibility, access and size before materializing a chosen body. Runtime writes append through the authority; DuckDB can query a read projection. A model should not receive unrestricted SQL over the authoritative Run History.

The supplied push experiment reports 3,540 input tokens / 46.5 seconds for one file, 3,973 / 48.1 for four files, and 6,434 / 74.4 for a pull of the same 2,320-byte material. Those are three observations from one setup, not a universal 10,000-token break-even. This review located the numbers in the reference router/documentation but did not independently requalify that transport experiment's raw records.

For a measured policy, let `B` be the tokens of optional material, `q` its probability of being needed, and `R` the marginal tool-round overhead. With no cache effects, pulling is cheaper in expected tokens only when `(1-q)B > qR`. Latency, cache reads, quality loss on missed information, and local resource contention need separate terms. Fit these from matched runs, not from constant seed prices.

## 9. Asynchronous work, restarts, and continuously available results

These capabilities are distinct:

| Capability | Existing basis | What must still be integrated or qualified |
|---|---|---|
| Parallel independent attempts | Loop Engine branch runner; main parallel execution contracts | Delivery of first verified result before all attempts finish; resource contention; cancellation accounting |
| Async execution in one process | `AsyncReactiveWorker.run_many` | Host service setup and bounded pool behavior for the chosen adapters |
| Durable admission and lease recovery | `SQLiteReactiveScheduler`, fencing and recovery | Cold-process handler/profile re-registration, crash windows and effect reconciliation |
| Saved task state | Spawned-task checkpoints and state stores | Running work restores as interrupted. A new attempt must resume from validated data, not an assumed live coroutine |
| Existing best answer | Candidate/evaluation/portfolio snapshots and as-of query | Bind serving to exact input freshness, schema and evaluator policy; keep payload accessible through the resolver |
| Randomized exploration | Typed exploration and scheduling vocabulary | An enum does not install Thompson sampling or successive halving. Current scheduler orderings are FIFO, priority aging, earliest deadline and seeded random |
| Best-so-far retention | Portfolio contracts; branch ratchet prototype | Peer agreement can retain a candidate but cannot certify task correctness. Freeze the independently verified incumbent |

The proposed continuous lifecycle is:

```text
Trigger admitted with immutable input identity
  -> lease claimed, exact Loop activated
  -> candidate produced in isolated scope
  -> independent verification and freshness checks
  -> append candidate/evaluation and new portfolio version
  -> readers receive the current verified result
  -> policy may admit another finite activation

Crash or cancellation
  -> retain prior verified portfolio
  -> fence the old attempt
  -> reconcile any unknown effect
  -> start a new bounded attempt if policy permits
```

Offer separate queries for `best_verified`, `verified_top_k`, `pareto`, `all_attempted`, and an optional seeded random sample of eligible verified candidates. Random exploration must not silently replace a verified result with an unverified candidate. If the task asks for experimental/provisional output, expose that as an explicit status and contract.

On cheap local models, optimize verified tasks per hardware-hour, time to first verified result, and the quality-over-time curve. Tokens remain an observed cost dimension because they consume compute and context capacity even when marginal billing is small. Record energy/CPU/GPU occupancy if those become limiting. Maintain exploration statistics conditional on selection; observing the expensive arm only after a cheap failure does not estimate its unconditional success rate.

## 10. Containerization choices

Execution placement and reusable asset packaging are separate axes. An OCI image may package a tool, but discovery of the image does not authorize pulling or executing it.

| Layer | Suitable experiment | Strength | Fragility / required checks |
|---|---|---|---|
| Confined host process | Trusted development diagnostics | Minimal startup and compatibility overhead | No OS isolation; shell code has host privileges. Explicit local authority only |
| Git worktree | Parallel source changes | Separates files and branches | Shares machine, kernel, resources and services; not a sandbox |
| bubblewrap | Local Linux worker with a narrow filesystem view | Cheap namespace/filesystem composition | Security is defined by the actual arguments. Qualify network, writable mounts, tool binaries, resources and process termination |
| Hardened Docker/OCI | Repeatable toolchain and isolated evaluator | Digest-pinned environment, configurable filesystem/network/resource policies | Daemon/host-kernel trust; mounts and credentials can defeat isolation; image distribution and startup costs |
| gVisor (`runsc`) | Stronger isolation for compatible container workloads | Userspace application-kernel boundary and OCI integration | Syscall compatibility and overhead; benchmark actual filesystem/data workloads |
| Firecracker microVM | Higher-isolation multi-tenant worker experiment | KVM guest-kernel boundary | Images, guest agents, networking, observability and lifecycle increase operations work |

The existing Loop Engine bridge is the strongest inspected baseline: network disabled, read-only root, capability drop, no-new-privileges, explicit user, resource limits, read-only instance bundle, and model calls brokered over frames. A writable action worker needs a separately qualified exact profile. No new containerization layer was installed or benchmarked by this review.

Primary references: [bubblewrap's security model](https://github.com/containers/bubblewrap#sandbox-security), [Docker run controls](https://docs.docker.com/engine/containers/run/), [gVisor architecture and tradeoffs](https://gvisor.dev/docs/), and [Firecracker architecture](https://firecracker-microvm.github.io/).

## 11. Memory, distillation, and cross-system learning

Do not create new persistent intelligence layers simply to add more memory views.

| Question | Preferred owner / representation | Promotion and use |
|---|---|---|
| What is happening now? | Run-scoped working state / Runtime Memory | Temporary; exact owner and state revision |
| What happened? | Episodic view over Run History and Runtime History and Solution Intelligence | Query events/results, including failures; do not duplicate the authoritative log |
| What seems true? | Reviewed semantic claims in the appropriate existing intelligence layer | Evidence, applicability, contradictions, freshness and independent review |
| What procedure may help? | Candidate procedural record and exact executable/profile references | Evidence from multiple independent tasks; negative-transfer controls; explicit qualified fallback |
| What code or complete solution can run? | Code Intelligence and Runtime History and Solution Intelligence | Immutable digest, license/dependencies/contracts/effects, independent verification and promotion |
| What does the user prefer or reject? | User Feedback Intelligence | Scoped explicit feedback; rejection memory and telemetry are not truth about task correctness |

The hardcode probe confirms the intended subtraction for literal numbers: three output-only literals are flagged; the same numbers present in context are not flagged. The equivalent `1500+30`, `700+24`, `990+8` recitation is not flagged. Therefore the detector should produce suspiciousness evidence, not a proof of generalization.

A stronger distillation qualification uses frozen original inputs, a clean workspace, no readable previous deliverables or evaluator secrets, independently generated fresh instances, metamorphic properties, mutation controls, and exact output comparison. Every write is covered by final subject/evaluator integrity checks before an asset is made eligible. Evaluate semantically different tasks in the same shape as negative controls.

The saved PoC benchmark supports a narrow result: data-quality and KPI-report, seed 101 cold versus seed 202 warm, both 10/10. Cold input totals were 235,895 + 207,580 = 443,475; durations 395.5 + 308.0 = 703.5 seconds. Warm input totals were zero, durations 3.1 + 4.2 = 7.3 seconds, with two stored capability IDs. This review read [results.json](/home/username/new_overnight_build/bench/20260907-200804/results.json) and the corresponding log. It did not reproduce the live solves or establish generalization beyond two repeated shapes. The discovered integrity defects prevent treating that success as broad qualification of the library.

## 12. A benchmark program that makes the variants comparable

First qualify the task population. Every generated folder needs a versioned manifest with task and input identities, original specification, allowed operations, reference-solution provenance, independent evaluator, positive and negative controls, and leakage boundaries. An intentionally impossible/wrong-expectation task needs an honesty evaluator; its failure is not an ordinary unsolved task.

Use the existing 1,000-folder corpus as an invalidated development population until repaired. Do not repair the old bytes and continue calling the population frozen. Produce a new version and keep the old defect report.

Suggested staged experiments:

1. **Oracle qualification:** all resources parse; independent references pass; wrong, blank, constant, leaked and test-edited answers fail. Confirm correct behavior for empty work, ambiguity, and wrong expectations.
2. **Mechanism fixtures:** every transport, mode, retry, cancellation, restart and reuse transaction. No model-quality claims from these fixtures.
3. **Balanced pilot:** select task families requiring different tool depth, data formats, dependency structure and ambiguity. Freeze assignments before execution. Compare A, B and D first; include a single capable action as the baseline.
4. **Reuse test:** cold qualification population, new instances, held-out task families, and drifted environments. Count qualification and failed reuse overhead. Report the exact number of eligible/matched/invoked/verified/promoted assets.
5. **Parallel/continuous test:** E and F under equal hardware and wall budgets. Record time to first verified answer, best quality over time, throughput, failure correlation, queue time, stale results, cancellation waste and restart recovery.
6. **Larger population:** expand only after controls pass. Split by generator/template/repository as well as seed. A thousand near-clones do not provide a thousand independent estimates of generalization.

Every result row should retain task/source revision, experiment assignment, environment, exact model/harness, physical model calls, reported token components and completeness, wall/queue time, cost known/unknown, evaluator version, failures and exclusions, candidate/acceptance/promotion states, artifacts and limitations. Re-execute alternatives; substituting outputs into logged trajectories is not a causal treatment run.

For long-running exploration, separate a development score from a final untouched evaluator. Repeatedly choosing the best candidate on the same hidden test turns that test into training feedback. Report family-level uncertainty and paired outcomes; do not extrapolate 2/2, 14/14 or 29/29 to broad autonomy.

## 13. How to keep capabilities wired

A module-import inventory is useful but insufficient. The reviewed failures require a behavior inventory.

For every supported capability/configuration, bind:

```text
entry point + exact profile/configuration
  -> admitted typed request
  -> selected operation/adapter
  -> actual execution observation
  -> accepted or refused result
  -> current-state-bound Run History
  -> independent assertion of the promised behavior
```

Extend Loop Engine's existing boundary registry, conformance rules and test entry points. Do not create a second runtime, event vocabulary, store, or promotion authority. Add expected ownership and observed coverage to the existing record/registry model.

The essential tests are paired: on changes behavior; off removes that behavior; invalid configuration refuses; unavailable dependency follows the declared fallback; a bypass attempt fails; a restart preserves the outcome/effect boundary. Mutation tests should prove that removing the actual call or ignoring the returned disposition makes the test fail.

Examples: `strong_model` must change the captured route, not metadata; admission refusal must leave state unchanged; `sandbox=bwrap` must reach the code-running process; `ledger-ref` must let a restricted consumer retrieve exactly its payload; a drifted asset must never execute; a retired candidate must disappear from eligibility; a corrupt journal must produce a typed status; a later candidate must not overwrite an earlier independently verified result.

Keep four dashboards separate: static presence, exercised integration, saved live evidence, and measured comparative benefit. None implies the next.

## 14. Per-system improvement plans

| System | First work | Then | Avoid |
|---|---|---|---|
| Loop Engine main | Close the current CI audit disposition; fix open-profile supervision and learned-memory boundary/relevance tests | Ship one supported host configuration connecting qualified harness execution, reuse, durable work and result serving; qualify the missing end-to-end path | Enabling every offline research prototype by default or claiming every module belongs on every solve |
| overnight | Fix admission, actual routing/transport, memory querying/promotion and sandbox coverage; version and qualify the corpus | Use profile-level behavior tests and independent benchmark records; merge proven ideas semantically into the chosen host boundary | Expanding declarations without executable consumers or weakening fixtures to bypass the intended path |
| new_overnight_build | Make acceptance/harvest/replay transactional and use the selected sandbox for every effect | Freeze context/evaluator/asset identities; improve physical-call accounting; retain the patch tool and useful ticket generator | Promoting solely because another run ID passed the same mutable gate |
| vigil | Connect the router to real outcomes; add a schema-derived patch tool and evaluator integrity controls | Host-backed reuse, rejection memory, durable candidate admission and optional portfolio solving | Treating the existing seeded routing numbers as calibrated probabilities or parallel capacity as unlimited |
| TypeScript product | Qualify supported Node and isolated DB integration; maintain explicit sync/privacy boundaries | Expose the local executor as a typed host adapter, connect rich ranking only after tests, add durable state/effect reconciliation | Rebuilding Loop Engine's reasoning/governance inside the web app or confusing local intake resume with execution resume |
| Reconciled/overnight branches | Reproduce each desirable invariant against current main independently | Port minimal fixes with exact provenance and shared conformance; measure parallel selection and retention | Wholesale merging of histories, naming systems, catalogs or authority implementations |
| Independent behavior lab | Keep it independent and use public differential adapters | Import its failure scenarios as external qualification cases with exact revisions | Using it as another production runtime inside Loop Engine |

## 15. Primary research that informs these plans

[SKILL.state](https://arxiv.org/html/2608.26263v2) supports testing explicit execution state instead of append-only history. Its limitations directly matter here: a fixed sufficient state may not be known, earlier discarded observations can become relevant, and trajectory-oriented tasks need history. Its reported setting does not qualify concurrent multi-writer merges. The local implementation should therefore retain an authoritative history and test compact-state sufficiency rather than promise universal constant space.

[Google's controlled agent-scaling study](https://research.google/blog/towards-a-science-of-scaling-agent-systems-when-and-why-agent-systems-work/) supports task-dependent topology selection. It does not establish that more agents or per-step processes improve these repositories. Measure the single-worker baseline, parallelizable and sequential families, coordination cost, and independently checked outcomes.

[OpenCode server documentation](https://opencode.ai/docs/server/) provides the process/session alternative; [custom tools](https://opencode.ai/docs/custom-tools/) provide typed tool validation. Treat configuration/session isolation and actual provider behavior as separate qualifications. These support variants B and C, not an automatic assertion of caching or constrained decoding.

[Erlang supervision](https://www.erlang.org/doc/system/sup_princ.html) is useful design input for restart scope and intensity. [Temporal's durable-execution guide](https://assets.temporal.io/durable-execution.pdf) is useful for comparing persisted workflow state, retries and idempotency. A Temporal-style external scheduler could be an additional infrastructure experiment if one authority is selected explicitly; it should not silently compete with the existing scheduler. Neither framework makes an external effect exactly-once merely by replaying control state.

[Ray's resource model](https://docs.ray.io/en/latest/ray-core/scheduling/resources.html) illustrates why scheduling admission and actual resource isolation are separate. This matters for local-model portfolios: logical concurrency declarations do not create GPU capacity or guarantee constant per-arm latency.

These sources were checked during the review. Their benchmark numbers and performance statements are external evidence, not results produced by this workspace.

## 16. Handoff and remaining qualification

The recommended shared foundation is Loop Engine's existing runtime and authority boundaries, with small engines retained as independently measurable adapters or reference implementations. The first concrete integration target is one host-owned task path with the PoC's structured patch channel, vigil's practical worktree/regression controls, and Loop Engine's independent acceptance and governed reuse. Continuous portfolios should be the next explicit lifecycle integration, not a promise inferred from an `async` method.

The review is complete for the named, located scope at the evidence levels above. It is not a complete security audit, a fresh model benchmark, an independent rerun of every historical claim, or a full branch-by-branch test qualification. `~/loop-node` remains unidentified. Current live-provider performance, supported-Node DB/browser integration, all optional configurations, every referenced older experiment, and the seven proposed embodiments remain separately unqualified.

Useful local learning sources, in priority order:

| Reference | Why read it |
|---|---|
| [Loop Engine current ways of running](/home/username/loop-engine/docs/context/WAYS-OF-RUNNING.md) and [component map](/home/username/loop-engine/docs/components/README.md) | Current boundaries and configurable paths; cross-check against the findings here |
| [Loop Engine improvement plan](/home/username/loop-engine/docs/implementation/IMPROVEMENT-PLAN-2026-09-07.md) | Existing owners and proposed integration work |
| [Loop Engine execution review](/home/username/loop-engine/docs/verification/CODE-REVIEW-2026-09-07.md) | Reproduced historical defects and evaluator problems; use later fixes for status |
| [Context transport research](/home/username/loop-engine/docs/research/NODE-CONTEXT-TRANSPORT-AND-LEDGER-REFERENCES-2026-09-07.md) | Reference/broker design and transport alternatives; environment-size claims need correction |
| [PoC reuse note](/home/username/new_overnight_build/docs/06-reuse-modes-and-context.md) and [saved cold/warm rows](/home/username/new_overnight_build/bench/20260907-200804/results.json) | The useful negative experiment and narrow successful reuse proof |
| [vigil blueprint](/home/username/vigil/docs/BLUEPRINT.md) and [build document](/home/username/vigil/docs/BUILD-AN-OVERNIGHT-SOLVER.md) | Repair-product lineage, isolation and delivery choices |
| [TS integration seams](/home/username/speculative_prompting/docs/agi-fabric-integration.md) and [reasoning research](/home/username/speculative_prompting/docs/research/reasoning-engine.md) | Product/engine split and measurement pitfalls; source claims still need their stated controls |
| [Reconciliation record](/home/username/overnight-docs/RECONCILIATION-2026-09-07.md) | Why branch claims conflict and which invariants merit independent retesting |
| [Behavior lab README](/home/username/ollama-loop-behavior-lab/README.md) | Independent qualification, liveness and hierarchical examples |
| [overnight universal specification](/home/username/overnight/docs/UNIVERSAL-LOOP-NODE-SYSTEM.md) | Broad idea inventory; use the correction table here before treating VERIFIED labels as current behavior |

The accompanying diagnostic scripts operate only on temporary fixtures and injected model sessions, except the corpus probes, which execute reviewed gates in copied workspaces. The repository inventory contains identities and hashes, not file bodies or credentials. These artifacts make the reproduced claims reviewable without altering the implementations.

## 17. Follow-up research and transition to implementation, 2026-09-08

The user subsequently authorized building independent embodiments and source mirrors in this project. The implementation is indexed in [embodiments](../../embodiments/README.md). This review's source revisions and test results remain the earlier snapshot; they must not be applied automatically to newer source mirrors.

The additional `/home/username/adversarial_coding_for_large_code_bases` directory was inspected. It is not a Git repository. Its README and HTML implement a 32-slide deck and a 20-scenario simulator with authored examples. It is a useful review-taxonomy source, not an executed autonomous coding engine. The combined HTML is 266,877 bytes. No model-execution claim is made for it, and the presentation was not rerendered by this review.

The raw saved context experiment was located at `/tmp/claude-1000/-home-username-overnight/ccec1abe-ced2-4a05-8317-17f74913c930/scratchpad/ctx_results.log`. Its rows confirm the supplied push/multiple-file/pull numbers and four markers per arm, with reported cache reads zero. This upgrades the numbers from transcript-only to inspected saved-log evidence, not an independent rerun or a universal break-even.

The assertion that vigil “never ran” is not established by an empty default state directory. The archived `vigil-blueprint.html` in the same scratchpad includes a claimed real CLI run, its outcome excerpt and 71,472 input tokens. The underlying original run directory was not recovered here, so that live claim remains historical and not independently requalified. Absence of one default directory is not evidence of absence of all prior executions.

The overnight catalog was counted directly: 16 kinds, of which seven, not six, select `gateway`: `decide-next`, `decomposer`, `observe`, `standardize`, `plan`, `verify`, `summarize`. Both gateway and process paths exist, but a matched live experiment still needs corrected route/accounting behavior. The inspected gateway entry also charges at both `invoke` and `_invoke_gateway`; that source-level issue should be resolved before treating session counters as physical calls.

The task directory census found 1,000 directories and two database files at the later observation. Counting `iterdir()` entries gives 1,002, not 1,002 benchmark folders. The malformed-CSV and gate findings above remain bound to their inspected source revision.

Further corrections to the proposed embodiments: process reuse does not automatically remove model prefix tokens; forked sessions do not establish a provider cache hit; two observations do not support a general per-class conclusion; crashes and censored attempts must remain in the population; and single-process execution need not imply identical permissions if the selected adapter can enforce a narrower per-call grant. These are variables to qualify rather than universal architecture properties.
