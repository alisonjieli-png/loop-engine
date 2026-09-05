# Loop Engine commit history audit

Updated local-object scope: 158 commit objects, consisting of 131 current-ref commits, 18 reflog-only commits, and 9 additional unreachable objects. The main body reviews current-ref history; the supplement at the end covers the other 27.

Scope: 131 commits reachable from all local refs, ending at 22ee44052b027ba96ce50c37e4cc6a659e1b91c8. The same 131 are reachable from main. There are no merge commits and no unmerged side-branch-only commits. The checkpoint branch/tag points to 40156e10eedd14aa2bd2113356a5bd5da3b3c5f3 and the showcase worktree points to 3491e2369639361893819ac6975a21bec47ea68c.

This is an architecture-history review. Every commit message and diff statistic was read. All 3,260 no-renames changed-path entries across 1,262 unique historical paths were collected and summarized by component. Large path listings were summarized, not all individually interpreted. Selected architecture patches were inspected; this is not a claim of full semantic line-by-line review of every diff. Seven small complete diffs were read (listed below); the eight architecture anchors listed below received selected file/hunk inspection, some output was truncated. The initial release adds 58,400 lines, a1a534c adds 99,337, and fa4fb04 adds 173,402. Counts include generated data and evidence, not just Python.

No checkout file was edited, no commit changed, no provider invoked, and no old benchmark rerun. The dirty current worktree has substantial uncommitted changes and is a separate evidence surface.

## Principal findings

1. The repository has repeatedly improved the architecture while correcting claims that earlier tests did not justify. Conformance pass counts are useful point-in-time observations, not proof of all advertised behavior. The history itself establishes this: 2895981 reports CI failing on every push despite local gate reports; 6bcd54e reports product acceptance broken since 9dc646b because a positional fixture was out of step with new source orientation.

2. The one-runtime identity survived a terminology detour. 5d22a1d introduced a passive ontology.LoopNode while claiming a one-LoopNode ontology and documenting its package as the only concrete runtime. The concrete executor was still Loop. dc2b3f2 replaced the record with LoopDefinitionRecord, removed the Node class allowlist, and left only a legacy serialized-reader boundary. Current instructions intentionally prohibit restoring the older naming. A historical LoopNode title is not an alternate present runtime.

3. Broad early execution claims need exact artifact review. f3bf732 introduced a fallback branch that fabricated StepOutcome(output=f'{step}:recovered:{fb}', confidence=0.6). It remained until 903d453, which replaced it with real handler execution, fixed failed final steps being classified accepted, counted direct spawn descendants, and added typed supervision. This does not establish that every old run used the bad branch; it means a pre-fix green test or accepted terminal alone cannot prove correct execution.

4. The generated-project evidence boundary was too weak until 9dc646b. A model could author an expected output file itself, and the artifact validator could accept fabricated metrics and a tiny constant submission without computing them. The fix separates authored paths from expected generated artifacts. e6d8b77 then recorded a real 286,571-row Kaggle result; d5519a4 corrected the report to include a same-day failed second model run and supplied the missing workspace-read operation. An isolated successful terminal is not evidence of consistent generalization.

5. The stage evidence stack at committed HEAD is still a shadow mechanism. At 22ee440, adaptive_practitioner_records.py:290-326 assigns a TEMPLATE_OFFER arm and records input stage shapes in convergence.note. Searching stage_arms at that revision finds assignment, convergence counting, and result serialization only. No prompt changes use that assignment. Therefore these counts cannot establish an assisted-versus-fresh effect or response-template convergence. b43d76d explicitly corrected an earlier 'full loop is closed' overstatement.

6. 22ee440 adds the API for local stage signals but does not wire a live stage producer to it. Its runtime changes are outcome_vector.py and stage_store.py. adaptive_practitioner_records.py:325-326 adds rows without local signals; run_stages.py:59-71 supplies only the containing run's fate. No production stage_store.observe call is present at that revision. Local credit support is a component feature, and the commit title must not be read as proof that the whole product already records causal stage credit. Dirty worktree changes may address part of this, so distinguish the two surfaces.

7. Model-demand advice is weaker than its 'proven' spelling implies. At HEAD, model_demand.py:128-166 gates on twelve total rows, aggregates the lossy helped property across routes, and ignores OutcomeVector.granularity. Many observations from one run or eleven unrelated/unknown rows plus a single successful route can satisfy the total-count gate. It is only recorded advice at HEAD, not executable route selection, but it is not a trustworthy causal training target or qualified cheap-model policy.

8. Cross-run sharing remains explicit. e59a28d adds LOOP_ENGINE_STAGE_STORE because default run directories isolate every run's stages. run_stages.py:38-43 still follows that behavior at committed HEAD. The two-run unit fixture uses the same directory. A normal deployment without a shared override must not be described as accumulating one campaign-wide stage corpus.

## Architecture development

- f3bf732 starts with a broad legacy package: recursive Loop, kernel, multiple decision modules, static_architecture services, strings, and evidence/examples.
- 00b3e41, c395d43, and 15bc5e9 expand Context/Code Intelligence, Loop-owned capabilities, versioned roles/profiles/settings, and a model gateway.
- a1a534c adds the major substrate: exact definitions, Loop relationships, runtime context, bounded spawned-task manager, effect approvals, workspace adapters, structured Run History, MCP/skills/harness adapters, and benchmark evidence.
- 25c524a strengthens exact definition binding and graph ownership; e0f002c retires old decision architecture; 9b4ef5f tightens harness separation.
- 5d22a1d renames static_architecture to core, adds catalog adapters, working/episodic/semantic/procedural memory, generation/foundry, development assurance, Constitution and machine contracts. cd0a9cd adds a bounded parallel runner and demonstrations. These memory functions are not the same classification axis as the four persistent Intelligence layers.
- 40156e1 and 51e539e add compile-bind/template intake and durable candidate journaling. dc2b3f2 repairs semantic identity and proves an offline governed learning vertical slice. The learning report explicitly limits its matched no-memory result to a deterministic fixture.
- f264e00 and 0680778 add typed resolution and model-assisted task compilation. f4e54fb makes task build public. Those commits do not mean task compilation performs the requested material work.
- d6eac04 introduces the self-orienting adaptive Practitioner and physical capability path. a2afd14 delivers the product solve API/CLI, reviewed projects, and qualification artifacts. 5592006 makes public solving LLM-first, lets the model pick its action, removes implicit effort caps, and renames compile_bind_task to standardize_task.
- fa4fb04 adds transactional semantic execution and candidate capability harvesting/reuse, with independent qualification. 7c157a9 through 1e265c3 add typed facets and layered similarity; similarity is expressly prior-not-proof and grants no execution authority.
- 2855ae2 through 903d453 harden retry/failover/streaming, output accounting, context bounds, execution isolation, and typed supervision. 8b12954's automatic host fallback is tightened by 903d453 to require explicit local-execution authority.
- 9ef4284 through 7987978 largely repair concrete production failures: repeated action fences, true source paths/roles, generated artifacts, measured capacities, missing workspace reads, visibility of diagnostics, and facts about the actual executor.
- 34b61c0 adds frame_alternatives, forecast_outcome, and calibrate as optional kernel steps. a67525a records that the tested skip-profile arm changed no model-call count because optional defaults are deterministic. Naming more steps does not itself establish new semantic ability.
- ff855ed adds run eligibility for infrastructure, semantic, and comparison questions. 408c018 reports twelve structurally verified Kaggle tasks but eleven mixed infrastructure/semantic runs and only one comparison-eligible run. Two trap tasks still produced hard classes where probabilities were expected.
- c23be37 through 025c7d4 add explicit semantic choice and recovery and then fix bounds initially described in prose without enforcement. d71e3d1 repairs missing persisted decision-ownership records and admits that the 1.0 autonomy ratio covers only instrumented decisions.
- 51ba3c1 adds response-template negotiation as a component; 340d657 links outcomes, c3b242d/f5aa913 define stage identity/indexing/model-demand evidence, 415536f/0b64541/94f8f64/e59a28d wire recording and shadow consultation, b43d76d repairs assignment and labels, and 22ee440 adds local outcome representation. The final stage of this chain still requires product evidence beyond local representation.

## Supersession examples

| Earlier claim or behavior | Correcting commit | What can be concluded |
|---|---|---|
| One LoopNode ontology | dc2b3f2 | Current runtime is Loop; passive definition records are LoopDefinitionRecord. |
| MCP SDK 2.x support in 6fa72e5 | c0c4600 then c38bfad | Change reverted; supported dependency pinned below 2. |
| Automatic host fallback in 8b12954 | 903d453 | Host execution requires explicit permission and has weaker isolation. |
| Accepted step sequence / fabricated fallback | 903d453 | Actual failure and actual fallback execution must be observed. |
| Artifact exists therefore was computed | 9dc646b | Authored files must not fulfill expected-generated-artifact checks. |
| First successful Kaggle report in e6d8b77 | d5519a4 | Include the omitted failed second run; no leaderboard claim. |
| Selection telemetry is optional | c8ad774 | Nested selection_report had actually blocked orientation before fix. |
| Conformance pass means clean CI | 2895981 and 6bcd54e | Local narrow gates and hosted/product gates had diverged. |
| Fixed retry choices are semantic reasoning | c23be37 and 5971e76 | Runtime continuity decisions and model-owned recovery are separate. |
| Choice adjustment bounds enforced | 025c7d4 | Enforcement began with typed ParameterSpec, not the earlier prose. |
| Stage controls measure template convergence | b43d76d and HEAD producer inspection | Occurrence assignment was fixed, but HEAD still does not withhold prompt treatment. |
| Full learning loop closed | b43d76d | Recording and shadow consultation only at that checkpoint. |
| Stage credit implemented by 22ee440 | HEAD producer inspection | Data structure/API implemented, live local evidence integration unproven. |

## Coverage by commit

M/P means message, full path inventory collected, component/path summary and diff statistics reviewed. H means selected architecture file patches or hunks also inspected. D means a complete small diff also read. These marks do not assert old tests were rerun. The machine-readable inventory contains exact full hashes, bodies, and all changed paths.

| # | Commit | Changes | Coverage | Architectural area | Subject |
|---:|---|---:|---|---|---|
| 1 | f3bf732 | 240 | M/P + H | Initial architecture and Intelligence | Initial release: Loop Engine |
| 2 | 00b3e41 | 116 | M/P | Initial architecture and Intelligence | feat: add Context Intelligence and improvement loops |
| 3 | c395d43 | 51 | M/P | Initial architecture and Intelligence | feat: expand loop-native intelligence architecture |
| 4 | b32679f | 2 | M/P | Initial architecture and Intelligence | ci: allow Mermaid rendering on hosted runners |
| 5 | 15bc5e9 | 76 | M/P | Initial architecture and Intelligence | feat: standardize loop profiles settings and evaluation |
| 6 | 3491e23 | 1 | M/P | Initial architecture and Intelligence | ci: move hosted actions to Node 24 runtimes |
| 7 | a1a534c | 449 | M/P | Canonical definitions and historical cleanup | checkpoint: consolidate Loop Engine architecture and evidence |
| 8 | 25c524a | 57 | M/P + H | Canonical definitions and historical cleanup | refactor: bind versioned Loop definitions and canonical graphs |
| 9 | b66a5ef | 36 | M/P | Canonical definitions and historical cleanup | docs: align taxonomy with canonical Loop architecture |
| 10 | 0eea01a | 21 | M/P | Canonical definitions and historical cleanup | docs: add verified Loop Engine architecture showcase |
| 11 | e0f002c | 30 | M/P | Canonical definitions and historical cleanup | refactor: retire legacy decision architecture |
| 12 | c04e8cd | 1 | M/P | Canonical definitions and historical cleanup | ci: keep retired architecture terms out |
| 13 | 9b4ef5f | 32 | M/P | Canonical definitions and historical cleanup | feat: harden harness integrations and comparisons |
| 14 | 5d22a1d | 478 | M/P + H | Core, four-memory model, templates | refactor: one LoopNode ontology, core architecture, memory, and devtools assurance |
| 15 | cd0a9cd | 12 | M/P | Core, four-memory model, templates | feat: flagship ensemble, four-memory demo, parallel runner, glossary |
| 16 | b36fee0 | 7 | M/P | Core, four-memory model, templates | chore: add dated development checkpoint system |
| 17 | 40156e1 | 4 | M/P | Core, four-memory model, templates | feat: add compile_bind_task node to the Practitioner kernel |
| 18 | 5fc3d3d | 1 | M/P + D | Core, four-memory model, templates | fix: make MemoryIdentity validation portable across Python 3.10-3.14 |
| 19 | 55c78de | 6 | M/P | Core, four-memory model, templates | docs: fix Markdown lint violations in AGENTS.md and the prompts annexes |
| 20 | 51e539e | 15 | M/P | Onboarding and model-assisted task compilation | feat: task templates, five-step demo CLI, durable learning candidates, example 21 |
| 21 | de77b85 | 2 | M/P | Onboarding and model-assisted task compilation | test: add open-ended capability scenario catalog |
| 22 | 4e2eff3 | 1 | M/P | Onboarding and model-assisted task compilation | fix: separate HF hub outage from broken install in the model2vec canary |
| 23 | 6fa72e5 | 2 | M/P + D | Onboarding and model-assisted task compilation | fix: support MCP SDK 2.x and restore stale static-architecture doc paths |
| 24 | c0c4600 | 2 | M/P + D | Onboarding and model-assisted task compilation | Revert "fix: support MCP SDK 2.x and restore stale static-architecture doc paths" |
| 25 | c38bfad | 2 | M/P + D | Onboarding and model-assisted task compilation | fix: pin MCP SDK below 2.x and repair the stale doc paths |
| 26 | 6a26978 | 2 | M/P | Onboarding and model-assisted task compilation | fix: make main green on all required CI jobs |
| 27 | dc2b3f2 | 206 | M/P + H | Onboarding and model-assisted task compilation | feat: prove core paths and restore canonical Loop semantics |
| 28 | 0f2791e | 3 | M/P | Onboarding and model-assisted task compilation | docs: record verified checkpoint handoff |
| 29 | 571d533 | 3 | M/P | Onboarding and model-assisted task compilation | fix: make showcase text clipping audit font-safe |
| 30 | 9ca80fd | 10 | M/P | Onboarding and model-assisted task compilation | docs: define work-approach optimization checkpoint |
| 31 | 6edc618 | 5 | M/P | Onboarding and model-assisted task compilation | docs: record published onboarding proof |
| 32 | f264e00 | 39 | M/P | Onboarding and model-assisted task compilation | feat: add typed autonomous resolution |
| 33 | 57efe4c | 3 | M/P | Onboarding and model-assisted task compilation | docs: record autonomous resolution proof |
| 34 | c203aa2 | 18 | M/P | Onboarding and model-assisted task compilation | ci: verify five live Ollama text scenarios |
| 35 | 9fcc4d1 | 6 | M/P | Onboarding and model-assisted task compilation | docs: record live Ollama CI proof |
| 36 | 831b6f9 | 1 | M/P | Onboarding and model-assisted task compilation | docs: add clean virtual environment setup |
| 37 | f0163fb | 1 | M/P | Onboarding and model-assisted task compilation | docs: make clean environment boundary explicit |
| 38 | 0680778 | 17 | M/P | Onboarding and model-assisted task compilation | feat: add provider-assisted task compilation |
| 39 | 1fc9f0d | 1 | M/P | Onboarding and model-assisted task compilation | docs: wrap long task compile examples |
| 40 | d7fbb22 | 15 | M/P | Onboarding and model-assisted task compilation | fix: make onboarding clear and responsive |
| 41 | 6095ecb | 12 | M/P | Onboarding and model-assisted task compilation | feat: accept direct provider keys for compile tests |
| 42 | 63919a3 | 1 | M/P | Onboarding and model-assisted task compilation | docs: put Ollama key in flagship command |
| 43 | f4e54fb | 8 | M/P | Onboarding and model-assisted task compilation | feat: make task build the public command |
| 44 | 5414ef4 | 1 | M/P | Onboarding and model-assisted task compilation | docs: replace README with a working quickstart |
| 45 | f9bd2bc | 1 | M/P | Onboarding and model-assisted task compilation | ci: stop requiring a README diagram |
| 46 | d6eac04 | 87 | M/P | Adaptive product solve and extensions | feat: add self-orienting practitioner and component qualification |
| 47 | a7db02f | 3 | M/P | Adaptive product solve and extensions | fix: separate live provider proof from semantic grading |
| 48 | a2afd14 | 149 | M/P | Adaptive product solve and extensions | feat: deliver product-first verified solve path |
| 49 | 2c38638 | 34 | M/P | Adaptive product solve and extensions | docs: add downloadable task library and fresh-machine CI |
| 50 | 43ba285 | 1 | M/P | Adaptive product solve and extensions | docs: use canonical spawned Loop terminology |
| 51 | 8356c57 | 50 | M/P | Adaptive product solve and extensions | feat: add drop-in extensions and free provider routing |
| 52 | 0394f56 | 82 | M/P | Adaptive product solve and extensions | Make the product quickstart executable and inspectable |
| 53 | 74d8fe4 | 2 | M/P | Adaptive product solve and extensions | Remove retired condition wording from public docs |
| 54 | 6ca17f2 | 1 | M/P | Adaptive product solve and extensions | Keep credentialed Kaggle example out of default CI |
| 55 | 4a3a185 | 1 | M/P + D | Adaptive product solve and extensions | Make reactive overlap proof independent of runner speed |
| 56 | 5592006 | 87 | M/P + H | Adaptive product solve and extensions | Make public solving LLM-first and unbound |
| 57 | e197a3e | 1 | M/P | Adaptive product solve and extensions | Remove stale product acceptance call ceiling |
| 58 | fa4fb04 | 140 | M/P | Reusable capability and similarity foundations | Add semantic runtime, reusable capability flywheel, and self-orienting abstraction work |
| 59 | e74ac2d | 3 | M/P | Reusable capability and similarity foundations | Lead README with human-like solve story and refresh hardcoding CI baseline |
| 60 | c5ac5af | 1 | M/P | Reusable capability and similarity foundations | Keep colleague framing self-directed and broaden the reuse story |
| 61 | f24c481 | 4 | M/P | Reusable capability and similarity foundations | Extend interrogation bank and question forms, fix string identity defects |
| 62 | 7c157a9 | 6 | M/P | Reusable capability and similarity foundations | Add deterministic task facet observations for hierarchical compatibility |
| 63 | 9cc9590 | 7 | M/P | Reusable capability and similarity foundations | Containerize task similarity finding as core infrastructure |
| 64 | 1e265c3 | 3 | M/P | Reusable capability and similarity foundations | Fix order-dependent facet indexing and wire reuse observation through solve |
| 65 | 1098be8 | 2 | M/P | Reusable capability and similarity foundations | Validate every web fetch redirect hop before connecting |
| 66 | 025f232 | 4 | M/P | Reusable capability and similarity foundations | Fix source-selection deadlock and add typed model-call transparency |
| 67 | 2855ae2 | 13 | M/P | Provider reliability and execution controls | Add transport retries, TLS classification, and cross-provider failover |
| 68 | 8b12954 | 3 | M/P | Provider reliability and execution controls | Fall back to the restricted local sandbox when Docker is unavailable |
| 69 | 59282d0 | 2 | M/P | Provider reliability and execution controls | Terminate non-progressing runs honestly instead of churning forever |
| 70 | 9168977 | 6 | M/P | Provider reliability and execution controls | Add exact model IO tracing and non-progress escalation ladder |
| 71 | b817e51 | 6 | M/P | Provider reliability and execution controls | Trace exact model IO on stderr by default; --quiet-model-io reduces it |
| 72 | f8f355e | 2 | M/P | Provider reliability and execution controls | Seed Mistral model output capabilities from published documentation |
| 73 | ab048a3 | 13 | M/P | Provider reliability and execution controls | Add self-orienting streaming, route health learning, and usage diagnostics |
| 74 | 863506e | 5 | M/P | Provider reliability and execution controls | Add explicit per-endpoint TLS verification policy |
| 75 | a2f7102 | 1 | M/P | Provider reliability and execution controls | Research SKILL.state execution against cache economics |
| 76 | 517e321 | 6 | M/P | Provider reliability and execution controls | Add self-contained Kaggle notebook cells to the repository |
| 77 | ba8088b | 5 | M/P | Provider reliability and execution controls | Make the Kaggle cells runnable locally with a staged check harness |
| 78 | 903d453 | 39 | M/P + H | Runtime failures, metrics, and observability corrections | Bound model context, type the Loop's guards, and make terminals honest |
| 79 | d396728 | 4 | M/P | Runtime failures, metrics, and observability corrections | Add the everything-is-a-Loop adversarial audit mandate, report, and scorecard |
| 80 | 9ef4284 | 32 | M/P | Runtime failures, metrics, and observability corrections | Refuse repeated failed calls, state runtime facts, screen blocking questions |
| 81 | 6af4ee3 | 1 | M/P | Runtime failures, metrics, and observability corrections | Record the post-fix live run and the clean-install proof in the review |
| 82 | bc6a5b9 | 5 | M/P | Runtime failures, metrics, and observability corrections | Stop the Kaggle cells guessing where the data is and what it is called |
| 83 | 9dc646b | 20 | M/P | Runtime failures, metrics, and observability corrections | Stop the runtime guessing about files, and stop typed results counting as produced |
| 84 | 94522e9 | 9 | M/P | Runtime failures, metrics, and observability corrections | Let a real competition into the workspace, and make every refusal state itself |
| 85 | 17438c4 | 12 | M/P | Runtime failures, metrics, and observability corrections | Measure every capacity on the solutioning path instead of declaring it |
| 86 | 2895981 | 8 | M/P | Runtime failures, metrics, and observability corrections | Repair the red CI gates and the pointers that had gone stale |
| 87 | 0deb08b | 127 | M/P | Runtime failures, metrics, and observability corrections | Review the whole tree with static analysis and fix what it found |
| 88 | 25f25b3 | 3 | M/P | Runtime failures, metrics, and observability corrections | Stop the Kaggle cells asserting why a secret lookup failed |
| 89 | 191752a | 5 | M/P | Runtime failures, metrics, and observability corrections | Give every prompt block its own slice of the packet |
| 90 | 6bcd54e | 3 | M/P | Runtime failures, metrics, and observability corrections | Answer the source-role call in the product acceptance fixture |
| 91 | 47d35c8 | 11 | M/P | Runtime failures, metrics, and observability corrections | Record what the model draws on, so the portfolio can grow on evidence |
| 92 | 34b61c0 | 11 | M/P | Runtime failures, metrics, and observability corrections | Widen the universe of options and add three steps to reason in |
| 93 | e6d8b77 | 1 | M/P | Runtime failures, metrics, and observability corrections | Record the first verified solve on the real competition |
| 94 | d5519a4 | 10 | M/P | Runtime failures, metrics, and observability corrections | Let a run read back the file it produced, and correct the Kaggle record |
| 95 | 0aa32d7 | 11 | M/P | Runtime failures, metrics, and observability corrections | Put each Kaggle output where its reader is |
| 96 | 6d01965 | 8 | M/P | Runtime failures, metrics, and observability corrections | Leave the Kaggle working root holding the submission and one directory |
| 97 | a67525a | 9 | M/P | Runtime failures, metrics, and observability corrections | Name the cognitive vocabulary, and what this runtime does not have |
| 98 | c71fa29 | 16 | M/P | Runtime failures, metrics, and observability corrections | Name the layer a run reached, and record the ladder that found it |
| 99 | ff855ed | 8 | M/P | Runtime failures, metrics, and observability corrections | Gate every run on which questions it is eligible to answer |
| 100 | a3c6d65 | 4 | M/P | Evidence eligibility and benchmark breadth | Stop a class name from naming a layer, and read the provider's own answer |
| 101 | 8676d86 | 1 | M/P | Evidence eligibility and benchmark breadth | Merge the duplicate Fixed heading the last commit introduced |
| 102 | 0e25274 | 4 | M/P | Evidence eligibility and benchmark breadth | Let a diagnostic say what it found |
| 103 | c8ad774 | 4 | M/P | Evidence eligibility and benchmark breadth | Stop an optional record from ending runs at orientation |
| 104 | 71bf761 | 3 | M/P | Evidence eligibility and benchmark breadth | Try again when the answer never arrived, and when a limit says wait |
| 105 | 78e4834 | 4 | M/P | Evidence eligibility and benchmark breadth | Stop saving a dataset into the record that describes it |
| 106 | 7987978 | 4 | M/P | Evidence eligibility and benchmark breadth | Say which machine the code runs on, and let a deployment choose it |
| 107 | 9e11931 | 3 | M/P | Evidence eligibility and benchmark breadth | Give an empty answer its own retry budget |
| 108 | 408c018 | 25 | M/P | Evidence eligibility and benchmark breadth | Record the twelve-competition campaign and its evidence |
| 109 | 5a1f563 | 11 | M/P | Evidence eligibility and benchmark breadth | Hear what a run reports, named in advance or not |
| 110 | 327db17 | 5 | M/P | Semantic choice, negotiation, and decision outcomes | Treat surplus as information wherever a model is parsed |
| 111 | 6bff838 | 2 | M/P | Semantic choice, negotiation, and decision outcomes | Judge the work by reading it, and derive the verdict from what was read |
| 112 | cb1d75a | 2 | M/P | Semantic choice, negotiation, and decision outcomes | Generate cases from the shape of a trap, and check them before use |
| 113 | 738bcdf | 4 | M/P | Semantic choice, negotiation, and decision outcomes | Publish the run's outputs when the engine is on PYTHONPATH, not only pip |
| 114 | 138c844 | 8 | M/P | Semantic choice, negotiation, and decision outcomes | Say when a run was asked to reason and could not |
| 115 | 8d9044f | 4 | M/P | Semantic choice, negotiation, and decision outcomes | Fit the ceiling to the window, and make a budget that can ask for less |
| 116 | c23be37 | 11 | M/P | Semantic choice, negotiation, and decision outcomes | Put choices to the model in one shape, and count who made them |
| 117 | 5971e76 | 7 | M/P | Semantic choice, negotiation, and decision outcomes | Let reasoning choose the recovery, and keep the table for continuity only |
| 118 | d71e3d1 | 1 | M/P + D | Semantic choice, negotiation, and decision outcomes | Save the ownership record where readers actually look |
| 119 | 025c7d4 | 4 | M/P | Semantic choice, negotiation, and decision outcomes | Enforce the bounds the model is told are enforced |
| 120 | 51ba3c1 | 6 | M/P | Semantic choice, negotiation, and decision outcomes | Offer the response shape instead of imposing it |
| 121 | 340d657 | 10 | M/P | Stage evidence and shadow consultation | Join every decision forward to what became of it |
| 122 | c3b242d | 7 | M/P | Stage evidence and shadow consultation | Name the cognitive situation, and keep a control arm against believing it |
| 123 | f5aa913 | 8 | M/P | Stage evidence and shadow consultation | Fingerprint at several scales, keep them, and fit a model ladder |
| 124 | 415536f | 4 | M/P | Stage evidence and shadow consultation | Make the fingerprint stack live, so runs accumulate stages |
| 125 | 0b64541 | 2 | M/P | Stage evidence and shadow consultation | Keep the stages of runs that fail, and prove retrieval across domains |
| 126 | 94f8f64 | 8 | M/P | Stage evidence and shadow consultation | Close the loop: runs read what earlier runs recorded |
| 127 | e59a28d | 1 | M/P + D | Stage evidence and shadow consultation | Let one store serve a whole campaign |
| 128 | e2a24e5 | 7 | M/P | Stage evidence and shadow consultation | Draw the architecture from a typed model instead of by hand |
| 129 | b43d76d | 5 | M/P + H | Stage evidence and shadow consultation | Correct four defects that would have made the evidence worthless |
| 130 | e32b7ac | 3 | M/P | Stage evidence and shadow consultation | Add guidance written from building the solver rather than designing it |
| 131 | 22ee440 | 8 | M/P + H | Stage evidence and shadow consultation | Give credit to the stage that earned it, not to every stage in the run |

## Supplemental local-object history: 27 additional commits

The initial scope above was all current refs. A broader local-object audit found 158 commit objects: 131 reachable from current refs, 18 additional commits reachable only through reflogs, and 9 commit objects reachable from neither refs nor reflogs. Thus the 131-commit branch-history statement does not exhaust local abandoned history. No remote or pruned objects can be inferred from this count.

Every additional commit message was read (byte-identical repeated messages were compared), and every first-parent/root changed-path inventory was collected and summarized. These extra inventories contain 1693 path-change entries. Four WIP/stash-like commits have two parents, so unlike the active main history this supplemental population does contain merge-shaped objects. Their path comparisons below use the first parent; their index-parent snapshots are listed separately. No stash was applied and no abandoned code was restored.

Findings:

- The reflog retains three identical-tree versions of each of four early development stages: initial taedri-loop release, optional tabular dependencies, universal front door, and Python 3.10 syntax repair. They are 12 distinct commit objects but four distinct source snapshots. Count them individually for history coverage, not as independent engineering or benchmark replications.
- The old universal-front-door message explicitly calls this repository a projection of a monorepo and advertises zero-call structural task interpretation. Those statements are historical, abandoned design context. Current AGENTS.md instead defines a standalone Loop Engine repository, and 5592006 makes the product solve path LLM-first. Do not reinstate the sync script or old inference authority on the strength of reflog history.
- 2369c72 renames taedri_loop to loop_intelligence; 4e0789b, 0c045c6, and 702684e revise the README. The three modes-as-permission wording in 4e0789b is superseded by current explicit separation of run mode and effect authority.
- f30d698 is an abandoned version of a2afd14's product-solve commit. Direct tree comparison shows differences only under artifacts/product-proof, including retained raw runs and changed proof summaries. The runtime source is identical between these two versions. Its extra saved material is not a distinct implementation or independent benchmark success.
- 8733fdb (On main: grading wiring) is a stash-like child of HEAD plus an index snapshot. Its full first-parent patch was read: it adds _grade_stage and sets local_verification=True after output-contract admission, and False for BaseException. That abandoned wiring concretely conflates output admission with correctness. It is not committed main; the current dirty implementation now separates output_admitted and local_verification. It helps explain why a later audit explicitly repaired this distinction.
- 0661ec0, 0d8491f, and a30c1a4 are abandoned WIP snapshots over already inventoried main commits, touching respectively seven semantic-decision plumbing files, 119 static-analysis/cleanup files, and 21 runtime/Kaggle/observability files. Their messages make no independent completed-feature claim.
- 4010b11, 7472b0a, 93e394f, and f5c57d5 are index snapshots identical to their first-parent trees. bbf2a0d and 6e3d88d are empty-root commits with no message and the standard empty tree. These six objects contain no changed-file implementation to assess.

| Commit | Reachability | First-parent/root path changes | Subject |
|---|---|---:|---|
| 0661ec08a17a745378640e8f2d3fbe319dbc9ae9 | unreachable-object | 7 | WIP on main: 8d9044f Fit the ceiling to the window, and make a budget that can ask for less |
| 0c045c6adf7fe7295339ab89390c11546431622a | reflog-only | 1 | docs(readme): precise nomenclature — loop / run mode (deterministic·hybrid·non-deterministic) / profile (step template); rebuild diagrams |
| 0d8491f9187829594bd59a6aa243d80d67ed556d | unreachable-object | 119 | WIP on main: 2895981 Repair the red CI gates and the pointers that had gone stale |
| 1863f6b4527671e8040df2536f9201dd17ff310d | reflog-only | 10 | Make the core dependency-free and the tabular domain optional |
| 195dacd60d0949544fa880aa9a31210ef445eec4 | reflog-only | 17 | A universal front door: say what you want, it works out the rest |
| 1d38d53bb07fcd3ed2a18bd6e7809e9eb3d5ba86 | reflog-only | 10 | Make the core dependency-free and the tabular domain optional |
| 2369c72eadea6ac3d8ae5f286a23bed89e0b0e91 | reflog-only | 391 | refactor: rename package to loop-intelligence (author Alie Jie Li); remove taedri identity |
| 26b437b9bc6bafe8f623e13cc578c7d772ffa75d | reflog-only | 17 | A universal front door: say what you want, it works out the rest |
| 3ae718a0d093d07f26fe05655105280f737905f5 | reflog-only | 6 | fix: PEP 701 f-string broke Python 3.10/3.11, and add the gate for it |
| 3ba4974f5c2af1470031b4a31dbc70559bbf2dc3 | reflog-only | 269 | Initial release: taedri-loop 0.1.0 |
| 4010b1103d18d47851f51e37e9da95e2ec81345f | unreachable-object | 0 | index on main: d396728 Add the everything-is-a-Loop adversarial audit mandate, report, and scorecard |
| 440919edd659ecd1cedf9c54d122378444191a29 | reflog-only | 6 | fix: PEP 701 f-string broke Python 3.10/3.11, and add the gate for it |
| 4e0789b1dd0a895c9e162bd4f1697f7afe29d6eb | reflog-only | 1 | docs(readme): stronger diagrams and runnable examples — nine-step loop, three modes as permission, child spawning, capability search |
| 6e3d88db30fc15f0f72a3a567dce6e18b668f6e3 | unreachable-object | 0 | (empty root; no message) |
| 702684e80fe89f16740052e028700708100c03eb | reflog-only | 1 | docs(readme): rename and simplify Building with Loops |
| 725f2ab8ebb5c2e7f18883d7fe443bfa213417c7 | reflog-only | 6 | fix: PEP 701 f-string broke Python 3.10/3.11, and add the gate for it |
| 7472b0acefdd56fd6919f0c021c9b0a231381c1e | unreachable-object | 0 | index on main: 8d9044f Fit the ceiling to the window, and make a budget that can ask for less |
| 8733fdba7022becd9b1bac69fd382039891a4fff | unreachable-object | 1 | On main: grading wiring |
| 9308dd4969260db2a745dab1bf153ae9812cb88e | reflog-only | 10 | Make the core dependency-free and the tabular domain optional |
| 93e394f8f3049e7a5a66b3e91140ed6e08265693 | unreachable-object | 0 | index on main: 2895981 Repair the red CI gates and the pointers that had gone stale |
| 992084f52aa7e60cb1cfa73bde85c1552c4afd81 | reflog-only | 269 | Initial release: taedri-loop 0.1.0 |
| a09b5095d58f312977fe38e8ed33afb24af5db5d | reflog-only | 269 | Initial release: taedri-loop 0.1.0 |
| a30c1a43d8340e0b9d48d06af29317974fe3abd3 | unreachable-object | 21 | WIP on main: d396728 Add the everything-is-a-Loop adversarial audit mandate, report, and scorecard |
| b541d28c3e9e88261703a53203d065e03e7f3548 | reflog-only | 17 | A universal front door: say what you want, it works out the rest |
| bbf2a0d2637442336f7ed52876e10fcceeb203b9 | reflog-only | 0 | (empty root; no message) |
| f30d69878f4fd55117b3fb60bde88b0e1ab21315 | reflog-only | 245 | feat: deliver product-first verified solve path |
| f5c57d545570662b4c692c9493aeb4013a41fcd3 | unreachable-object | 0 | index on main: 22ee440 Give credit to the stage that earned it, not to every stage in the run |

Supplemental machine-readable inventory: `/tmp/loop-engine-additional-27-commit-inventory.json`. The coverage limits of the main report still apply: messages, inventories and summaries across all objects, selected semantic patch review, not every full historical diff line. The full first-parent diff of 8733fdb was additionally read.
