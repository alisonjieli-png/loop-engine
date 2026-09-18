# Claude Fable 5.1 review of Loop Engine, September 18, 2026

This review covers the repository as of September 18, 2026, the two Codex
sessions of September 14, the OpenCode session of September 15 and 16, and
the live campaign records those sessions left behind. It reviews committed
revision `1108218` on `main`, whose hosted continuous integration run passed,
and the uncommitted working tree on top of it.

Every check in this review was offline. No provider or model call was made.
Each finding is either reproduced by a command on the recorded evidence, with
the path named, or labeled as a reading of the code or records. Session
records were read from the Codex rollout files under `~/.codex/sessions` and
from the OpenCode session database under `~/.local/share/opencode`.

## Summary

- `main` is green through `1108218`. Batch 12 of this session's verifier work
  (undeclared file naming and two verifier prompt statements) is committed
  after this review as the next revision; its exact tree passed the full gate
  battery on September 14.
- The working tree holds three unfinished streams that share files: this
  session's failed-check review (September 14, uncommitted), the OpenCode
  session's three runtime mechanisms and six documents (September 15 and
  16, uncommitted), and 718 MB of experiment output inside the checkout.
- On an export of that combined tree, the full self-test passes (4903 of
  4903 checks) and conformance passes with an unchanged manifest, but the
  hardcoding delta gate fails on seven new high findings and the
  documentation job would fail on two defects. The tree cannot be pushed as
  it stands.
- The live evidence moved. The September 14 rerun on `2aaa5d5` verified 3 of
  27 planned trials, none at the 60-call ceiling. The September 16
  qualification campaign, run on the combined working tree, verified 4 of 4
  trials in its verifier lane. Two of those four were accepted through the
  new per-criterion judgment cases, which is the first live evidence for
  that mechanism. The denominator is four trials on one provider lane.
- Two general defects still end runs that hold correct work: the verifier
  refuses every later attempt once the producer's file set changes (22
  refusals at zero calls in one trial), and a run can spend its calls
  returning a result that does not exist while the model's own verify step
  accepts a resolution package (43 calls in one trial).
- The Codex sessions of September 14 are already reconciled into `main`.
  Their last request, a file-by-file review into a summary folder, produced
  nothing; the Codex process is still running and has been idle since.

## Repository state

```text
Repository on September 18, 11:07
├── main = origin/main = 1108218 (CI success on 419e914, 93e761e, 1108218)
├── Working tree
│   ├── 29 modified tracked files
│   ├── 13 untracked files
│   │   ├── 3 from this session (failed-check review, its checks, prompts)
│   │   ├── 6 documents from the OpenCode session
│   │   └── 4 artifact files from September 8 reviews
│   └── .loop-engine-dev/stub-experiments-20260916/ (718 MB, untracked, not ignored)
└── Processes holding the worktree
    ├── codex gpt-5.6-sol --yolo (pid 64310, started September 14, idle since 12:04)
    ├── opencode --auto (pid 4085520, started September 15, idle since September 16 13:25)
    └── this session's rerun monitor (owned, harmless)
```

Authorship of the working tree, by modification time:

| Window | Files | Author |
|---|---|---|
| September 14, 20:05 to 20:22 | `independent_failure_review.py`, its checks, `verification_prompts.py`, `independent_judgment.py`, `independent_probe_review.py`, `adaptive_practitioner_verification.py`, `boundary_registry.py`, `_self_test.py`, `architecture_map.py`, the architecture map, the decision record, the Codex handoff | this session, batch 13 |
| September 15, 13:03 to 13:08 | `supervision_policy.py`, `adaptive_practitioner_routing.py`, `stage_action_lineage_adversarial_checks.py` | OpenCode session |
| September 15, 17:04 to 17:16 | `adaptive_practitioner_records.py`, `adaptive_practitioner.py`, `adaptive_practitioner_acceptance_checks.py`, `solve_runtime.py`, `solve_request_adaptation.py`, `__main__.py`, `solve_cli.py` | OpenCode session |
| September 15, 18:20 to 18:25 | `independent_verification.py`, `prompt_fragments.py`, `independent_probe_planning.py`, the two verifier check modules, `CHANGELOG.md` | OpenCode session, on top of this session's batch 12 edits |
| September 16, 04:18 to 13:21 | `adaptive_practitioner_feedback_checks.py`, `task_database_campaign.py`, six new documents, `ASTRA.md`, the conformance manifest | OpenCode session |

Nothing from either concurrent session was committed. The OpenCode session
used `git stash push` on named paths twice on September 15 and restored them;
no stash from it remains. It also read this session's transcript to recover
context, and it updated the feedback check fixture that this session's
uncommitted failed-check review had made stale, so the combined tree passes.

## Gate status of the combined working tree

Run on September 18 on an export of the tree (tracked files plus untracked
source and documents, without the experiment folder), with no opencode binary
on PATH and a cleared environment:

| Gate | Result |
|---|---|
| Conformance | ALL GATES PASS, manifest unchanged (532 files scanned) |
| Full offline self-test | PASSED, 4903 of 4903 checks, 0 provider calls |
| Focused checks of every touched module | supervision policy 13, routing 11, lineage adversarial 41, acceptance flows 41, feedback 4, verification 6, solve runtime 18, request adaptation 20, independent verification 182, judgment 16, failed-check review 18, probe review 14, boundary register 11, adaptive Practitioner 63, all passing |
| Hardcoding delta gate | FAILS, 7 blocking new high findings (see finding 2) |
| markdownlint, full CI scope (328 files) | 1 issue: `docs/architecture/PRACTITIONER-SOLUTIONING-AND-SOLUTION-CANVAS-SPACES.md` lacks a final newline |
| Retired public language search | FAILS: `docs/research/EXTERNAL-NOOA-OO-AGENTS-2026-09-16.md` lines 21, 35, and 58 use the phrase parent-child, which contains a retired topology word |
| Lab, tools, examples, acceptance battery | not rerun on the combined tree; last full battery passed on the batch 12 tree on September 14 |

The OpenCode session ran the full self-test three times on September 16
(04:52, 11:27, 11:58) and recorded 4903 of 4903 each time; its own task list
said 4901 of 4903 at one point, which its later runs superseded. It ran two
inline mutants (the phase gate disabled, the fast path removed) rather than a
mutant per new check, and no mutant for the probe binding refusal.

## The Codex sessions of September 14

Two rollouts, both `gpt-5.6-sol` with `--yolo`, in this repository:

- 07:57 to 08:42, 3 owner prompts, 151 commands. The owner asked why a task
  ever ends blocked or incomplete and described the best-available
  resolution a capable person would produce. Codex implemented the
  `task_resolution_package/v1` slice, the runtime facts for it, and the
  typed clarification rule.
- 08:42 to 12:04, 12 owner prompts, 415 commands, one compaction. The owner
  asked for action vectors on every cognitive step, the same behavior for
  the custom Practitioner and for OpenCode, Codex, and Pi, component
  separation with independent tests, and a human-like solving process.
  Codex implemented the outcome vector, work-function lineage, and the
  cross-harness policy packet.

Those edits ended at 10:18. This session backed the tree up at 11:47 as
`refs/backup/codex-inflight-20260914` (`a49c6f8`) and reconciled it into
`main` in `96fba39`, `aca062f`, and the following commits; `main` contains
the backup's content plus later fixes. The last prompt, at 12:04, asked for a
file-by-file review with sub-agents summarized into a "Luna Max summary
folder". The rollout records `task_complete` two seconds later with no
command, no message, and no folder; none exists under the home directory.
The Codex process has been idle since and has changed nothing.

## The OpenCode session of September 15 and 16

Session `ses_f5a30539effeYcS8lchNC4VXPp`, titled "Loop-engine project and
DeepSeek harness review", ran from September 15 12:04 to September 16 13:25
on `glm-5.3-flash` through the `opencode-go` provider (28.4 million input
tokens, 276 thousand output tokens, 45 owner prompts, 966 assistant
messages). The owner's prompts moved from a review of this project and the
DeepSeek harness, through research on harness engineering and frontier
companies, to atomic harness instances per reasoning step, adaptable rules,
reuse tiers, a universal reasoned fallback before any deterministic fallback,
a complete constitution document, and the separation of the Practitioner
solutioning space from the Solution Canvas. The final prompt, "Review the
recent actions on this project", received no answer before the session went
idle.

What the session delivered, and what the evidence shows:

```text
OpenCode deliverables
├── Runtime mechanisms (offline checks pass; no live qualification)
│   ├── budget-phase routing: SupervisionPolicy 1.3.0 gains
│   │   budget_phase_thresholds; the route step demotes exploration routes
│   │   to repair or reframe when remaining call authority falls below a
│   │   declared fraction; campaigns pass the thresholds as a setting
│   ├── fast-path allowance: allow_fast_path_resolution on the request and
│   │   the public solve request, --allow-fast-path on the command line;
│   │   a model-led run may run exact resolvers before its first model call
│   └── probe subject binding: plan validation refuses a probe that infers
│       the subject location from its own file path; the design, file, and
│       review prompts state the /workspace/subject/<name> binding
├── Documents (untracked)
│   ├── docs/COMPLETE-PROJECT-CONSTITUTION.md (739 lines, a synthesis with
│   │   an explicit authority order)
│   ├── four architecture direction documents (adaptive cognition,
│   │   adaptable policies, reuse tiers, the two spaces)
│   ├── docs/research/EXTERNAL-NOOA-OO-AGENTS-2026-09-16.md
│   └── CHANGELOG "Added on 2026-09-15" and six ASTRA.md paragraphs
├── Experiments (.loop-engine-dev/stub-experiments-20260916/, 718 MB, not a product boundary)
│   ├── atomic Kaggle pipeline: one digest call decomposes a task, one
│   │   OpenCode instance per component, assembled and gated
│   ├── multi-harness proof of concept with a reasoned fallback selector
│   └── the finding that the campaign gates leaked their holdout
└── Campaigns (Ollama Cloud, ceiling 150)
    ├── proactive-20260915: 14 rows, 0 verified, stopped on usage_limit_reached
    └── qualification-20260916: 5 rows, 4 verified in the verifier lane
```

The holdout finding deserves emphasis. The session found that the
task-campaign gates shuffled the full training file, scored a 20 percent
subset, and let the staged solution train on the full file, so every gate
score recorded on September 10 was in-sample (0.766 in-sample against 0.613
honest on the passing 20-newsgroups run). The corrected gate exists only
inside the experiment folder. The campaign gate in `devtools` is unchanged.

The reasoned fallback selector the owner asked for ("before any deterministic
fallback, a reasoning call receives the context and the candidate list and
selects") exists only as `reasoned_fallback.py` in the experiment folder with
four self-checks. Nothing in `src/loop_engine` applies it. The engine's own
deterministic fallbacks (the deterministic route after a failed route call,
the panel's reframe after an unavailable recovery panel, the derived
dispositions after an inadmissible method assessment) are unchanged.

## Live evidence

### The September 14 rerun on `2aaa5d5`

`.loop-engine-dev/live-rerun-v3-20260914.ShZN`, Ollama Cloud, attachment
files supplied, 27 planned trials, 28 rows because one outage trial was
rerun.

| Ceiling | Trials | Verified | Budget exhausted | Verification failed | Other |
|---|---|---|---|---|---|
| 60 | 9 | 0 | 8 | 0 | PM-001 NO_PROGRESS at 43 calls |
| 150 | 9 | 1 (ML-001 flash, 113 calls) | 2 | 6 | |
| none | 10 | 2 (OPS-001 flash, 46 calls; AE-001 pro, 39 calls on the outage rerun) | 0 | 7 | 1 provider outage |

Where verification failed, the recorded verifier reports show four causes:

1. Oracle reviews refused keyword probes of natural-language deliverables:
   21 refusals in DA-001 at no ceiling, 8 in AE-001, 5 in CS-001. This is
   the case that batch 11's per-criterion judgment addresses; the rerun ran
   before batch 11 existed.
2. The retained check refused every later attempt whose file set differed
   from the cached probe's: 22 refusals at zero calls in CS-001 pro at no
   ceiling, 7 in FIN-001 at 150 (finding 4).
3. Verifier calls reached the model output limit: 3 in DA-001, 1 each in
   CS-001 and FIN-001 (finding 6).
4. A planned file response repeated an invalid shape: 2 in PM-001.

PM-001 at 60 calls is a distinct failure. No project ever ran and no
workspace was created, yet the model chose RETURN_RESULT nine times, each
time stating that `product_brief.md` and `acceptance_examples.md` existed in
the workspace, and the model's own verify step recorded `accept` nine times
for the resolution package that RETURN_RESULT had published. The route guard
demoted every `stop_success` because the presented result had not passed any
check, the stall ladder ran, and the run ended `stop_unprofitable` (finding
5).

### The OpenCode campaigns

`proactive-20260915-kR7wQm` (flash and pro, ceiling 150, on the working tree
of September 15): pro CS-001 VERIFICATION_FAILED at 138 calls, pro AE-001
PROVIDER_UNAVAILABLE at 103, and after two resumptions HR-001
BUDGET_EXHAUSTED at 150, MKT-001 VERIFICATION_FAILED at 114, SCM-001
VERIFICATION_FAILED at 78 (the probe inferred the subject location, which
led to the binding fix), SEC-001 NO_PROGRESS at 20, BA-001
BLOCKED_MATERIAL_INPUT at 150 with a complete resolution package and
material questions about undefined terms, DE-001 provider unavailable. No
trial was verified. The runner stopped on `usage_limit_reached`.

`qualification-20260916-mQ9vXk` (flash, ceiling 150, on the working tree of
September 16, which contains batches 11 to 13 and the three OpenCode
mechanisms):

| Lane | Task | Result | Calls | How it was verified |
|---|---|---|---|---|
| verifier | MKT-001 | COMPLETED_VERIFIED | 40 | one exact case after two refused reviews |
| verifier | FIN-001 | COMPLETED_VERIFIED | 134 | one subset case after two refused plans and one refused review |
| verifier | SCM-001 | COMPLETED_VERIFIED | 60 | six judged cases, one per criterion, plus one exact case |
| verifier | DA-001 | COMPLETED_VERIFIED | 23 | four judged cases, one per criterion |
| phase_default | CS-001 | PROVIDER_UNAVAILABLE | 54 | the provider allowance ran out |

Every judged case was grounded: the stored judgment quotes a passage that
appears in the printed deliverable (for example DA-001's before-and-after
rate table and SCM-001's "No order is placed" line). Plan validation refused
a judged case that named several criteria, and the designer repaired it in
the next attempt. In the September 14 rerun the same DA-001 task spent 206
calls and 21 refused reviews without acceptance. The failed-check review was
never exercised, because no report in these trials failed. The campaign's
`status.json` records no engine commit or digest, so these results are
re-runnable only from the campaign's own runtime snapshot folder.

## Findings

Each finding names its evidence and the owning boundary. Severity is by
effect on landing the work and on verified outcomes.

### 1. The documentation job would fail

`docs/research/EXTERNAL-NOOA-OO-AGENTS-2026-09-16.md` uses the phrase
parent-child on three lines, which the retired-language search matches, and
`docs/architecture/PRACTITIONER-SOLUTIONING-AND-SOLUTION-CANVAS-SPACES.md`
lacks a final newline. Both are one-line fixes in the OpenCode session's
files.

### 2. The hardcoding delta gate is red

Seven new high findings block the gate on the combined tree:

| Location | Literal | Author |
|---|---|---|
| `strings/verification_prompts.py` lines 26 and 36 | the two review prompt texts, classified as unowned resources | this session |
| `core/adaptive_practitioner.py` line 165 | `'hybrid'`, `'non_deterministic'` | OpenCode |
| `core/adaptive_practitioner_records.py` line 1479 | `'deterministic'` | OpenCode |
| `core/adaptive_practitioner_routing.py` lines 161 and 176 | `'explore'`, `'conserve'` | OpenCode |

The prompt module needs an allowlist entry with a reason, as the other
governed prompt constants have, or its constants move into the fragment
registry. The five vocabulary literals should read the registered mode and
phase tuples (`BUDGET_PHASES` already exists in `supervision_policy.py`).

### 3. 718 MB of experiment output sits inside the checkout

`.loop-engine-dev/stub-experiments-20260916/` holds 17 run folders and 5 diagnostic folders
beside its scripts and README. It is untracked and not ignored, the root
disk is at 92 percent, and the CodeGraph index walks the checkout. Its
scripts read credentials only from environment variables and its logs hold
no key-shaped values; it is safe to keep but not here. Move it under
`.loop-engine-dev` or outside the repository and record the location in the
README that describes it.

### 4. A changed file set turns the retained check into a dead end

Owner: `core/independent_verification.py` (`_probe`) and the producer's view
of independent reports in `core/adaptive_practitioner_verification.py`.

Evidence: CS-001 pro at no ceiling, attempt 1 passed its own checks with one
authored file. Attempt 2's manifest declared `independent/loop385/checks/
probe.py` and `run_probe.py`, the verifier Loop's own file names, and every
later attempt kept them. The cached probe bundle's path list no longer
matched the subject inventory, so the verifier raised "retained regression
interface changed; restore its subject paths before acceptance" 22 times at
zero calls, and the run spent 256 calls. FIN-001 at 150 shows the same
refusal seven times.

Two defects combine. The producer imitated the verifier's probe because the
verification record that reaches the model carries the verifier's execution
record with its workspace path and command lines. And the reuse rule, which
exists so that path drift cannot make a failing oracle disappear, refuses
instead of re-planning. The persistence direction requires a typed next
action: design a check for the new interface with the retained failing cases
attached as untrusted feedback and key the cache by task and interface, and
give the producer a bounded view of a failed report (failed cases, expected
and observed values, notes) without the verifier's paths, while refusing
producer files under `independent/`.

### 5. RETURN_RESULT with no result, accepted by the model's own verifier

Owner: `core/adaptive_practitioner.py` (`core.finish`),
`core/practitioner_runtime_facts.py`, and
`core/adaptive_practitioner_verification.py`.

Evidence: PM-001 at 60 calls (above). The runtime facts for RETURN_RESULT
name the attempt that would be presented, but when none exists the action
still publishes a resolution package as the result, and the verify step may
return `accept` for it. The route guard held, so no false success was
published, but 43 calls went to a loop that could never end well. The fix is
general: the verify step refuses `accept` when the presented result is a
`task_resolution_package/v1`, because that record is by definition
unverified, and the facts state that no task result exists to return, so a
return is not offered as completion.

### 6. Verifier calls that reach the output limit still end reports

Evidence: five reports in the September 14 rerun ended with
`output_limit_reached`. Recovery reasoning now runs in campaigns (`93e761e`)
and a declined recovery is recorded, but the only options are retry on the
same route and abandon. A bounded re-plan (fewer criteria per design call, a
smaller packet, a per-file request) is the missing option. Owner:
`core/independent_verification.py` and the recovery option set.

### 7. The 60-call ceiling verifies nothing

Every 60-call flash cell spent its whole allowance. A pass costs about four
model calls (orient, decide, verify, route) and each independent
verification attempt three to ten more. The OpenCode session's budget-phase
routing is a reasonable general mechanism for this, but it has no live
evidence: its one paired trial ended on a provider outage. The next rerun
should declare thresholds on half its cells and keep the other half as
controls.

### 8. The campaign gates leaked their holdout

Evidence: the OpenCode session's measurement (finding recorded in
`.loop-engine-dev/stub-experiments-20260916/atomic-kaggle-pipeline/README.md` and in the
working tree's `ASTRA.md`). Every gate score recorded for the September 10
campaign arms is in-sample. The gate in `devtools` still performs the leaked
split. Fix the gate to hold out before staging, attach the correction to the
recorded scores, and do not cite those scores as out-of-sample. Owner:
`devtools/embodiment_lab/task_database_campaign.py` and the task catalog's
gate definitions.

### 9. Documentation debt in the new documents

The new documents use LSH, LoRA, LLM, OO, and DAG without the full term, and
the experiment README uses PoC; the public writing rule asks for full
descriptive terms. The constitution's Part 10 lists the failed-check review,
budget-phase routing, and the fast-path allowance as implemented; they exist
only in the working tree, and Part 19 labels their live qualification as
pending. The constitution should say "in the working tree, not on main"
until they land, or land first.

### 10. Three agents shared one worktree without a landing owner

The Codex process has been idle for four days and the OpenCode process for
two, both holding terminal sessions on the same checkout. The OpenCode
session's work depends on this session's uncommitted batch 13, and the
campaign status files record no engine commit. Nothing was lost, but the
combined tree has no single owner and no gated commit. The landing order
below resolves it.

### 11. The frontier research workflow did not run

This session launched a six-topic research workflow on September 14. Every
agent failed on the weekly usage limit, which resets on September 20. No
research record exists from it; nothing in the repository cites it.

## Recommended sequence

1. Land batch 12 (this review's companion commit) and this review.
2. Fix findings 1 and 2, then land batch 13 and the OpenCode runtime work as
   gated commits: the failed-check review; the three mechanisms; the
   documents. Each commit runs the export gates and the mutant scripts.
3. Move the experiment folder out of the checkout (finding 3).
4. Implement findings 4 and 5; both are small and general, and both remove a
   way for a run to spend its whole allowance on work it cannot finish.
5. Fix the campaign gate leak and annotate the recorded scores (finding 8).
6. Run the next matched rerun on the landed commit at the 150-call ceiling:
   criterion judgment and the failed-check review on for every cell,
   budget-phase thresholds on half the cells, engine commit recorded in the
   status file, and compare against the September 14 rerun.

## Decisions for the owner

- Whether this session may land the OpenCode session's uncommitted work
  under its own verification, or whether that session should finish and
  commit it.
- Whether the idle Codex and OpenCode terminal sessions may be stopped; this
  session only stops processes it owns.
- Which provider allowance the next rerun may use; the Ollama allowance ran
  out on September 16 and the Tactical endpoint was reachable that day.
