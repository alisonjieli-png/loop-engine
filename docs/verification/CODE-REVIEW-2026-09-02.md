# Code review, 2026-09-02: full pass, Kaggle cells, and the gap list

> **Point-in-time record.** This report describes the tree as it stood on its
> own date. Several findings below were closed afterwards; see
> `docs/verification/LIVE-KAGGLE-DIAGNOSTIC-2026-09-02.md` for what changed and
> which items no longer stand. Nothing here has been edited after the fact.

This review follows the audit of 2026-09-01 (`EVERYTHING-IS-A-LOOP-AUDIT-2026-09-01.md`).
It covers the whole tree as pushed in `d396728` plus the changes made in this pass, and
answers four questions: does the code run without errors, can the Kaggle cells be pasted
into Kaggle as they are, what did live use-case runs show, and what still stands between
the current system and the mesh architecture the product definition describes.

## 1. Whole-tree health

| Check | Result |
|---|---|
| `compileall` over `src`, `devtools`, `kaggle` | clean |
| Bare `except:` or `except Exception: pass` in `src` | none |
| Stubs (`TODO`, `FIXME`, `NotImplementedError` outside refusals) | none; four `NotImplementedError` sites are explicit unsupported-operation refusals in intelligence layers and n-gram retrieval |
| Clean install of the pushed `main` archive into a fresh environment, which is the Kaggle install path | install ok, doctor exit 0, base self-test 1774 of 1774 with optional adapters reported as not tested, and the new runtime modules import from the installed package |
| `python -m build` | sdist and wheel built |
| Full self-test, conformance, hardcoding audit | see section 7 |

## 2. Kaggle cells: copy-paste readiness

The three cells are single files that read every path and switch from one configuration
block, take the provider key from a Kaggle secret with an environment fallback, download the
`main` archive from GitHub, install it, run `doctor` and `configure`, probe the provider, and
run one solve with `--allow-local-execution` because Kaggle has no Docker. Verified this pass:

- Offline stage (no key, no network) passes for all three cells on binary, regression, and
  multiclass synthetic competitions.
- Cell 01 (Ollama Cloud) solved two live synthetic competitions end to end; numbers in section 3.
- Cell 02 (Tactical Engineering only) passed preflight and solve stages against a loopback
  OpenAI-compatible mock, which exercises its key handling, endpoint override, deadline, and
  stage records. Its live run needs `TACTICAL_API_KEY`, which is not present here.
- Cell 03 (three providers) needs all three keys for the live stages; its offline stage passes.
- Fixed in this pass: stale "Based on main @ commit" headers, missing notebook settings in the
  README (Internet on, no accelerator, secret names), and the harness now covers three target
  shapes. One local-only lesson: a stale mock server on a reused port made a cell look broken;
  the harness should pick a free port when it starts a mock.

What a Kaggle user still has to do by hand: enable Internet, add the secret named in the cell
header, and accept that the cell installs from `main` (there is no pinned release yet).

## 3. Live use-case runs

| Run | Result | Calls / passes | Input tokens | Wall clock |
|---|---|---|---|---|
| Binary classification, 200 rows (2026-09-01) | Practitioner VERIFIED_WORKING; public terminal mis-typed, fixed the same night; ROC-AUC 0.936 on 3 folds | 113 / 13 | 3.80M | 1612 s |
| Regression, 200 rows | COMPLETED_VERIFIED; ridge RMSE 1.74 ± 0.07, R² 0.77 on 3 folds | 27 / 4 | 0.69M | 471 s |
| Multiclass, 200 rows | BLOCKED_MATERIAL_INPUT with no artifacts; the run stopped to ask a question that was not a question. Cause found and fixed in this pass | 73 / 9 | not reported per call | 1468 s |
| Binary, 200 rows, after the fixes | cut off by the harness time cap before a terminal, having written a solution, a test, and a verification script across two project attempts; no repeated-call refusals and no rejected capability calls occurred | 67 / 9 | not reported per call | 1418 s |

Three observations. Cost varied fourfold between tasks of the same size, so cost is not yet
predictable per task region. Provider-reported input tokens exceeded the estimator by 10 to 45
percent by stage; the estimate is now recorded per call, so it can be calibrated. The multiclass
run and a Tactical Engineering run on a real competition both spent their budget on failures the
runtime could have prevented, which is what section 4 addresses.

## 4. Two live stalls and the general fix

Two runs failed for reasons that had nothing to do with the model or the network, and both were
fixed generally rather than for the task that exposed them.

**A rejected call repeated for twenty passes.** On a real Kaggle competition the model asked the
source capability for an absolute dataset directory. The capability refused with exact text
naming the admitted paths. The model read that text, wrote its own diagnosis (a type error that
was not there), and proposed the same call again. Soft reset and cold restart reframed the prose
but not the action, so the run spent its whole budget on one refused call. Three changes close
this for every capability:

- A refusal is now typed. A capability rejection carries a closed reason code, the arguments that
  were refused, the admitted values with their total, and a repair hint written by the runtime.
  It survives the exception wrapping of the Solution graph and travels back on the result packet.
- The runtime states what it knows. Every model packet now carries a runtime facts block: the
  admitted source manifest, the workspace root, the execution isolation, the granted permissions,
  and the fence view. The paths the model was guessing were already in the run's own state.
- Exact repetition is made impossible. A per-run fence remembers each failed capability and
  argument identity; after the policy count the identical call is refused without execution, with
  the last rejection attached. A different argument set stays admissible, so the model keeps its
  authority to choose. The fence names no task and no capability.

**A run blocked on text that was not a question.** The multiclass run stopped after 73 calls with
the blocking question "None for this orientation step; the task is sufficiently specified...".
The model had written prose meaning "nothing to ask" into the question slot, and any non-empty
entry became a blocking terminal. A deterministic screen now decides what may pause a run: text
must be phrased as a question and must not open with one of a closed set of no-question phrases.
Screened entries are kept as recorded limitations, never dropped and never blocking.

## 5. Built in this pass

- A raising step handler now leaves an honest terminal (`handler_exception`,
  INTERNAL_PROTOCOL_ERROR) and re-raises; before, 12 of 1000 probe runs left no terminal event.
- Region evidence before the first model call: saved runs in the task's region are projected
  into statistics and an advisory shortcut decision, the context budget variant is chosen from
  recorded prompt experiments with a seeded exploration rate, and the decision is recorded on
  the outcome and handed to the model as one advisory block.
- OpenCode as a Loop realization: a process adapter with a handshake, default starting
  instructions from a versioned prompt resource, isolated directory, digest-stored raw events,
  normalized model turns and tool events, changed-file artifacts, and wall-clock cancellation.
  Live P7 evidence is in `docs/evidence/opencode-harness-smoke-2026-09-02.json`.
- Kaggle harness: three competition kinds; cells and README corrected.

## 6. Gaps, capability issues, and architecture issues

Ordered by what blocks the product definition most. Audit ids in brackets.

### Must fix next

- **1.** Storage and transfer carry no Loop identity [4.1, 4.3, 4.10]: artifact writes and graph
   edge transfers happen through service calls and closure arguments with no owner Loop and no
   port event. The manifest records what a model saw; nothing yet records which Loop moved data.
- **2.** Definition versions are inert [5.4, 15.3]: 16 digests behind one `1.0.0`. A version policy
   (which body fields are interface, when a bump is required, when requalification follows) is
   the smallest change that makes handshakes meaningful.
- **3.** No schema-version registry [5.6, 15.2]: 738 hand-spelled `/vN` strings in 190 files. One
   passive registry with a migration reader at the boundaries removes a whole class of drift.
- **4.** The in-process ledger accepts forged events [PR-21 and the structures probe]: `record()` is
   the only writer, but any code can append. A per-ledger sealing key, like the approval
   authority added yesterday, is the consistent fix.
- **5.** Portfolio lineage [12.8, 5.2]: candidates, evaluations, graph versions, and context packs are
   separate stores with no cross-references. The Kaggle path produces one solution per run, not a
   portfolio; the multi-solution promise is unproven on a real task.

### Capability issues

- **6.** Cost per task is unpredictable (fourfold between two runs of equal size); nothing yet caps a
   run by expected cost or chooses a cheaper realization for a known region.
- **7.** The estimator undercounts tokens by 10 to 45 percent by stage; the calibration is recorded
   but not applied to the budget.
- **8.** No run resumes or forks another; a cancelled Kaggle run restarts from nothing.
- **9.** Verification of ML quality is model-written: the generated `verification.json` differs per
   run and the Practitioner's verdict trusts the artifacts it produced. An independent
   evaluator Loop with a held-out split is missing [P8].
- **10.** Only one external harness has a process adapter (OpenCode). Codex, Claude Code, Hermes, and
    Aider are installed and unproven; the same-task benchmark [PR-20] has never run.
- **11.** Tactical Engineering and Mistral routes are live-untested in this environment; the Kaggle
    cells for them are mock-verified only.
- **12.** The user feedback lane (Studio click to typed record to new proposal or fork) is not
    exercised end to end [14.6].

### Architecture issues

- **13.** Declared context blocks are not what the model reads. Every packet declares typed
    `LLMContextBlock` values with trust classes and manifests, but the renderer builds prompt text
    from a fixed map of packet fields. A block declared and never mapped is invisible to every
    model, silently. That is how the runtime facts block was added, manifested, and read by
    nothing until a live probe caught it. The blocks should be the rendering source of truth, with
    the layout policy ordering them; until then a self-test guards the facts path.
- **14.** The Practitioner kernel is a private ten-node loop inside one owner step [3.6]; either give
    each pass Loop identity or record why the fusion is intentional and reconstructable.
- **15.** Strict atomic primitives cost 5000 to 6500 times a native operation with no physical fusion
    [3.8, 6.10]; `physical_fusion_requires_logical_history` has no consumer.
- **16.** Loop ids are process-local counters [11.2]; the handoff namespaces them, but there is no
    global identity, addressing, or transport [11.3, 11.4]. The fabric today is one process plus
    a verified merge.
- **17.** Two tool interfaces exist [9.1]: solution-registry tools emit records inside Loops, while
    model-led tool actions travel a separate path through the Practitioner.
- **18.** Region statistics, frontier snapshots, and prompt experiments are projections rebuilt from
    saved results; nothing writes them at run time, so a live run cannot consult its own
    frontier yet.
- **19.** The static instruction text is re-sent on every call [8.9, 13.10]; packets are not ordered
    for provider prefix caching.
- **20.** Studio has no views for the frontier, context flow, portfolio, or reuse [11.x of the mandate].
- **21.** The handler-exception terminal, the failed-final-step terminal, and the supervision policy are
    new semantics; consumers that read `LoopResult.accepted` were checked once and should be
    covered by a conformance rule.

## 7. Toward the mesh: the next increments in order

- **1.** Ledger sealing key and Loop-owned artifact writes (issues 1 and 4), because every later
   claim rests on the history being trustworthy and complete.
- **2.** Definition version policy and the schema registry (issues 2 and 3), so handshakes between
   Loops and harnesses can check something real.
- **3.** Run-time frontier and experiment records written by the Practitioner itself, then a solve
   pre-check that can skip reasoning for a region with enough verified evidence (issues 17, 6).
- **4.** A second process adapter (Codex or Claude Code) plus the same-task benchmark across the five
   installed harnesses (issue 10), then a portfolio run where two harness Loops and one native
   Loop compete on the clamp fixture and the Kaggle micro-competition (issue 5).
- **5.** Independent evaluator Loop with a held-out split for ML tasks (issue 9).
- **6.** Global Loop identity and a transport for the handoff envelope (issue 15).

## 8. Gates and live evidence for this pass

| Gate | Result |
|---|---|
| Full self-test | 1802 of 1802 checks pass |
| Architecture conformance | every zero-tolerance gate passes on the live tree |
| Hardcoding audit against the baseline, failing on new high findings | passes; the new findings are allowlisted with per-literal rationale |
| Architecture map freshness | regenerated and current |
| Byte-compile over the source, devtools, and Kaggle trees | clean |
| Kaggle offline harness, three cells by three competition kinds | 9 of 9 pass |
| Kaggle cell 02 preflight and solve against a loopback mock | both pass, 4 mock requests |

Live evidence produced in this pass:

- OpenCode as a Loop, run against Ollama Cloud through the harness boundary. The record is in
  the evidence directory. One task run completed with a real edit and an independent unit test at
  exit 0, and a second run was cancelled at its wall-clock budget with an honest budget-exhausted
  terminal.
- A regression competition solved end to end by cell 01 against Ollama Cloud.
- A multiclass competition run that exposed the blocking-question defect fixed in section 4.
- A binary competition run after the fixes, which reached real generated-project attempts with a
  solution, a test, and a verification script, and recorded no refused or repeated capability
  calls. It was stopped by the local time cap rather than by a stall, so it is evidence that the
  stall class is gone, not evidence of a verified competition result.
- A clean install of the pushed archive into a fresh environment, which is what a Kaggle cell
  does: install ok, doctor exit 0, base self-test 1774 of 1774, and the new runtime modules
  import from the installed package.

Not proved here: a live Tactical Engineering run, which needs its API key in the environment. Its
cell is verified against a loopback mock at both the preflight and solve stages, which exercises
the key handling, endpoint override, route plan, deadline, and stage records, but not the
provider itself.
