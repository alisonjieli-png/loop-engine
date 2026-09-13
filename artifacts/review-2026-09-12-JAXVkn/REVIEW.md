# Loop Engine review and saved-run evidence

Read the [design memo](../../docs/research/COGNITIVE-STEP-HARNESS-DIRECTION-2026-09-12.md)
for the intended system, context handoff, continued candidate production,
harness selection, intelligence admission, and the proposed proof sequence.
This appendix records what supports that memo and what remains uncertain.

This is a local review artifact. It is not a product catalog, a new runtime,
or an approval to run a campaign. The owner explicitly redirected the work
to review and documentation. No new model calls or task campaigns were
started by this review. Earlier local diagnostic checks are identified below.

## Review snapshot and coverage

The starting checkout was main at
0cb7b86cb7f5b1f6a6b1b798da4e0a4a1469e00f, one commit ahead of the locally
recorded origin/main. It had 52 modified tracked files and extensive
untracked work. Those changes predated this review. Several Codex, Claude,
OpenCode, Python, and related processes were present; a matching working
directory did not establish ownership.

The census ran from 08:15:38 to 08:28:53 UTC on 2026-09-12. It enumerated
3,577,616 file entries and 358,986 directories without following directory
symlinks. Reported file lengths sum to 486,220,465,118 bytes. This is a
logical sum, not deduplicated allocated disk usage.

All 1,721 tracked files were read and hashed. Of these, 1,713 decoded as text
and eight were binary. The content inventory includes 90,186 text files,
864,400,774 bytes, and 14,020,393 lines across current code, references,
experiments, and saved material. All 466 production Python modules received
an AST inventory. Current source and selected contract paths showed no digest
drift in the recorded follow-up comparison.

These counts describe coverage levels. They do not mean that a human-equivalent
line-by-line semantic review occurred for every dependency, imported dataset,
binary, or transcript. Close reading concentrated on the runtime, harness and
context boundaries, output lifecycle, graph execution, reuse, verification,
current changes, relevant session decisions, and saved Tactical evidence.
The database deliberately records exhaustive_line_by_line_semantic_review=false.

The inventories are useful precisely because unreviewed meaning is not
silently relabeled as verified behavior.

## Where the work lives

| Location | Role in this review |
|---|---|
| src/loop_engine | Active package. One Loop runtime, contracts, adapters, storage mechanics, and public solving |
| docs and top-level contracts | Current authority documents mixed with dated proposals and evidence |
| embodiments and devtools/embodiment_lab | Canonical launch and placement experiments, plus explicit harness configurations |
| devtools/embodiment_axes | Thirty controlled design alternatives across seven experimental axes |
| overnight | Reference implementation of separately composed steps, bounded state, ledger pull, and solution export |
| new_overnight_build | Reference implementation of task folders, composition, frame manifests, candidate reuse, and output packaging |
| speculative_prompting and vigil | Reference application, intake, worktree, privacy, evaluation, and delivery designs |
| solver-lab | Independently owned experiment copies with their own provenance and evaluators |
| taedri.dev and taedri-* copies | Historical/reference material. The taedri.dev copy alone accounts for 2,188,691 enumerated files |
| artifacts, benchmarks, case-studies, and local run directories | Evidence with different populations, evaluators, and maturity |
| /home/username/task_database | 318 raw task directories and eight adapted tasks, observed by directory inventory |
| /home/username/task-campaign-runs and /home/username/probe-work | Saved Tactical campaign and diagnostic records |

The owner's clarification resolves the main organization ambiguity: copied
embodiments are useful design references. They are not automatically active
parts of the Loop Engine distribution. No reference folder was moved,
merged, or deleted.

Recommended cleanup is initially documentary: identify the active package,
label reference copies by provenance, and record which saved results use
which copy. Moving directories should follow an ownership and reference check,
especially while other sessions and long-running processes use absolute paths.
Preserve unique source, failed attempts, and session history.

## Session history

The scoped inventory contains 715 transcript/session records:

| Store | Direct Loop Engine records | Related records and probes |
|---|---:|---:|
| Codex | 50 rollout files | 13 |
| Claude Code | 36 transcript files | 582 |
| OpenCode | 21 database sessions | 13 |

The direct Codex set includes five top-level threads and their subordinate
rollouts according to the thread index. The direct Claude set contains four
top-level transcript files plus 32 subordinate files. The direct OpenCode set
contains 12 top-level sessions and nine subordinate sessions. These are not
715 independent human conversations. Forked context, tool results, summaries,
and unrelated requests made from the same working directory are distinguishable
from original design instructions.

The separate Codex history index contributed 166 relevant entries across eight
session IDs, all with an associated selected rollout. The scope covers the
available local stores; deleted, inaccessible, or externally retained sessions
cannot be inferred from this inventory.

Cloud Code was interpreted as Claude Code because that is the relevant local
store. Pi is the installed harness family corresponding to the owner's
references to Pi/Py.

The recurring intent across the sessions is consistent:

- Let models interpret unfamiliar work through explicit cognitive operations.
  Do not replace semantic judgment with task-name or filename shortcuts.
- Treat context, question forms, procedures, and output shapes as reusable
  intelligence.
- Make separately configured harness instances real alternatives, with
  controlled comparisons and visible limitations.
- Preserve both the investigative work and an executable delivered Solution.
- Learn from exact outcomes while retaining independent verification,
  applicability checks, and failures.
- Keep several possible embodiments available instead of declaring a universal
  winner from a small demonstration.

Historical requests to push, run providers, or modify another project were
treated as evidence of that session's work, not fresh authority for this review.
Raw private prompts and transcript bodies were not copied into the review database.

## Saved Tactical records

The frozen read-only summary is dated 2026-09-12 at 08:53:19 UTC. It includes
surviving cell files under /home/username/task-campaign-runs and canonical
events from their saved runs, plus the selected demosolve, foldertask,
wineprobe, and oc-winetask probe locations.

| Population | Surviving cell files | Reported gate passes | Cell files with unknown model-call count |
|---|---:|---:|---:|
| full2 | 24 | 2 | 9 |
| batch2 | 24 | 1 | 0 |
| paced1 | 3 | 0 | 0 |
| batch3, partial snapshot | 10 | 0 | 2 |
| full1 | 1 | 0 | 0 |
| Four earlier pilot directories | 4 | 0 | 4 |

There are 66 cell records and 73 saved event files in this scope. The event
files contain 273,828 events, including 3,362 model-invocation records.
3,356 name provider tactical and model gemma-4-coding-abliterated. Six have
unknown identity and token fields.

Known input tokens total 67,629,533 and known output tokens total 1,831,776.
These are recorded subtotals. They do not include every health probe or
recover overwritten attempts, and they are not an independently reconciled
provider invoice. Model identity here means the identity recorded by the
integration, not a verified statement about the server's weights or hardware.
No local-inference or frontier-model equivalence claim follows.

The positive gate records are:

| Campaign | Task | Harness | Recorded score | Engine terminal |
|---|---|---|---:|---|
| full2 | 20-newsgroups-ciphertext-challenge | OpenCode | 1.0000 | BLOCKED_MATERIAL_INPUT |
| full2 | Kannada-MNIST | OpenCode | 1.0000 | BLOCKED_MATERIAL_INPUT |
| batch2 | 20-newsgroups-ciphertext-challenge | Codex | 0.7438 | BLOCKED_MATERIAL_INPUT |

A post-run gate pass is not an engine-verified task completion. All three
retain the blocking terminal above, with artifact bridging recorded separately.
At an earlier read, full2/report.json reported one passing gate while two
surviving cell files reported passes. That discrepancy must remain visible.

The campaigns changed prompts, evaluation-contract attachment, budgets,
environment preparation, endpoint pacing, and outage recovery. They are useful
diagnostic populations, not one controlled harness comparison. A combined
success percentage would obscure these differences.

Saved failure descriptions include unavailable endpoints, formatting and
admission failures, exhausted call budgets, missing output interfaces, missing
artifacts, and scores below the configured floor. Their relative contributions
require event-level attribution. An outer act count alone cannot identify
which cognitive work happened inside it.

## Findings that affect the next proof

### F01. The adapted holdouts do not protect the answer

Observed source: all eight gate scripts pass the complete row, including the
target, to predict(dict(row)). They also derive the holdout from the same
training archive made available to the candidate.

The saved OpenCode solutions for the two perfect scores load the complete
training CSV and fit their RandomForest models on it. The evaluator later
samples that same CSV. Those results cannot establish generalization to
unseen rows.

Before the review-only clarification, a synthetic control used the unchanged
eight gate scripts with 100 toy rows. A predictor that merely returns the
supplied target scored 1.0000 and passed all eight. Constant controls were also
retained; their behavior on the toy population is not a statement about the
original dataset baselines.

The required correction is structural: freeze the split before candidate
training, expose only training data, predict from feature-only inputs in an
isolated process, and score sealed labels separately. The exact metric,
including class averaging, needs an explicit contract. Retain label-copying,
training-set memorization, wrong-output, and constant-output controls.

Sources: the gate scripts under /home/username/task_database/adapted,
the two saved solution.py files in full2, and the imported gate-review.json
document in the review database.

### F02. The new verifier boundary does not terminate descendant work

[verifier_execute.py](../../src/loop_engine/core/verifier_execute.py) launches
bash on the host and applies a subprocess timeout to that process. It does
not establish an operating-system sandbox or terminate its entire process
group. The campaign's separate gate launch has the same host-execution shape.
Those scripts can import model-authored candidate code.

A finite canary returned a timeout after about 0.101 seconds, then its
descendant wrote a marker after the parent had returned. The marker was
confined to this review's own temporary directory.

The helper also captures complete stdout/stderr before keeping a tail, despite
declaring MAX_OUTPUT_BYTES. Its returned tail is not a byte limit. Before
qualification, this boundary needs the existing workspace authority,
source-bound verifier identity, process-tree cancellation, bounded capture,
and an honest unknown-effect outcome where termination cannot be confirmed.

The current campaign bridges solution.py into the gate directory after solve
returns. The mid-solve verifier runs from the gate's parent directory.
That integration also needs an explicit binding to the candidate being
evaluated, rather than reliance on whichever file happens to be present.

### F03. The new output fields break old definition digests

[LoopDefinition](../../src/loop_engine/loop/loop_definition.py) still emits
loop_definition/v1 while adding output_type and max_outputs to the canonical
digest body. The reader accepts the old key set but then computes the new
digest.

The review generated a real record with the committed encoder. The committed
reader accepted it. The current encoder/reader accepted a new record. The
current reader rejected the unchanged committed record with a content-digest
mismatch.

This affects exact references and saved graph/definition compatibility. A
versioned encoding or explicit migration must validate the original digest
and preserve the meaning of historical references. Ignoring or silently
recomputing the saved digest would remove the integrity property.

### F04. Output cardinality does not fully describe continued production

[LoopContract](../../src/loop_engine/loop/loop_contract.py) currently uses the
consumer's output_type to decide whether it can receive a multiple-output
producer. Changing only the consumer's output cardinality changes the
connection verdict while its input roles remain identical.

This is a contract-design issue to resolve before connecting live portfolios.
Input cardinality, response schema, production lifecycle, and serving policy
need independent meanings. The design memo makes the owner's early-answer,
continued-improvement requirement explicit.

### F05. The new trajectory reward is not a qualified learning label

[trajectory_reward](../../src/loop_engine/code_nodes/run_analytics.py) exists,
so a claim that the repository contains no reward record at all is stale.
However, it derives parts of its score from step names and substrings.

An empty event list receives completion credit and scores 3/6. Structural
act/verify markers combined with an artifact-missing note can score 6/6.
The adjacent comparison helper also converts an unknown score to zero and
then reports a measured quality gain.

These records should remain unqualified diagnostics. Training or policy
promotion needs exact issued outcomes, artifact identity, evaluator identity,
metric direction, missing-value handling, and local decision attribution.
No training run or weight update was established by this review.

### F06. Retry and report identity lose information

[task_campaign.py](../../tools/task_campaign.py) deletes an existing cell
directory when staging the same task and arm. Its report merges by task/arm,
which replaces earlier rows. A retry therefore does not inherently retain a
separate immutable attempt.

This limits reconstruction of the complete Tactical denominator. Future
campaigns need distinct attempt identities and explicit selection/regrading
records. Solving, artifact validity, gate validity, acceptance, and promotion
must stay separate. Missing call totals cannot be filled with zero or an
unqualified subtotal.

### F07. Accepted parameters do not establish model capacity

The September 10 note records successful requests with large max_tokens
parameters and short natural completions. That establishes request
acceptance, not the model's actual maximum output length.

The current fit-window helper uses the existing character-based token
estimate. Its result is an explicit allocation, but the calculation does not
become an exact tokenizer bound by being recorded in a typed object.
Keep provider capacity, per-request allocation, context fit, and total-run
authority distinct. The saved source does not establish a new exact maximum.

### F08. Several earlier gap statements are too broad

The repository already contains:

- governed deterministic capability reuse, including a configured adaptive
  Practitioner seam;
- lexical/vector retrieval and SimHash metadata;
- graph serialization and JSON/Mermaid rendering;
- a dependency-wave executor and serial dependency-plan construction;
- reactive activations, independent candidate evaluations, and portfolio
  serving.

The missing claim is qualified product integration, not universal absence of
these components. A static import or a profile name in a log is not proof of
execution either.

The kernel calculates its inner passes inside the outer Loop's act handler.
Its other outer positions are explicitly structural markers. Therefore the
earlier argument that zero outer calibrate/integrate events proves those
functions never execute is invalid. Inner pass records and semantic calls
must be inspected.

The copied implementations contain useful reference mechanisms, but their
proof does not automatically transfer to the canonical runtime.

## Earlier evidence and documentation corrections

The saved T1 report records 17/19 transport passes. The September 10
full-solve note records 14/17 passes with fixture replies. These demonstrate
different boundaries and must not be presented as model-quality wins.

The September 9 harness inventory is explicitly provisional. It records 11
projects completing real-inference component phases, 33 model calls, and 30
verified task/harness pairs out of 34 attempted and 36 planned, over three
function tasks. Its provider was Ollama Cloud, not the Tactical campaign.
The populations cannot be pooled.

The [novel-task report](../../docs/verification/UNSEEN-NOVEL-TASK-CAMPAIGN-2026-09-06.md)
contains later corrections to its initial 10/10 and 9/10 account. Three
prompts contradicted their cases, and the claimed 10 percent false-acceptance
rate was not established by the retained audit. Its corrected population was
prepared separately. Use the correction section, not the opening summary
alone.

The packaged showcase has 26 slides. Its PowerPoint text, captions, existing
montages, poster, and selected rendered PDF pages were inspected. The PDF is
image-based: ordinary text extraction returned no meaningful page text.
Slide 9 and slide 26 still describe missing non-deterministic/hybrid Solution
execution even though the current component contract supports those modes
with compatible executors and exact authority. The visual artifacts should
be treated as dated illustrations, not a current complete implementation map.
Video playback was not performed.

Source PDF: :codex-file-citation{path="/home/username/loop-engine/showcase/assets/loop-engine-showcase.pdf" purpose="source"}.
Source deck: [loop-engine-showcase.pptx](../../showcase/assets/loop-engine-showcase.pptx).

## Diagnostic checks completed before the owner deferred execution

| Check | Observation |
|---|---|
| Dependency-wave fixture | 5/5 reported checks passed |
| Governed capability reuse | 33/33 passed |
| Canonical Loop checks | 52/52 passed |
| Harness process contract checks | 11/11 passed |
| Independent probe review checks | 14/14 reported checks passed |
| Semantic harness integration fixture | 15/15 passed |
| Repository structural conformance | 466 files indexed, no reported problems |
| Isolated wheel build and fresh base install | Completed; pip check passed |
| Fresh installed conformance | All reported gates passed |
| Unfiltered checkout self-test and conformance | Stopped incomplete after traversing copied Taedri campaign records |
| Fresh installed full self-test | Failed with Disk quota exceeded during artifact writing, followed by history errors; no all-pass result |
| Hardcoding audit attempt | Terminated with status 143; no verdict retained |

The build and clean-install checks used the available Python 3.14 environment,
not the repository's complete Python 3.10-to-3.12 CI matrix. Optional adapters
were not independently installed and qualified by that base install.
The initial attempt to call harness_semantic_checks.self_test used the wrong
entry point; the module's actual run_checks entry point produced the 15/15
result above.

These checks prove narrow properties. They do not establish current full
system correctness. No further tests, model calls, or campaigns were
initiated after the owner's review-only clarification.

## Database-managed review data

[review.duckdb](review.duckdb) is a derived local review projection.
[query_review.sql](query_review.sql) contains read-only example queries.
[manage_review.py](manage_review.py) imports the earlier evidence and exports
JSON through DuckDB COPY. It does not invoke Loop Engine, providers, gates,
or task runners.

The database contains file inventory, source-file metadata, tracked-file
digests, session records, Tactical cells, saved history summaries, findings,
and the source documents used to derive them. Original histories, managed
record databases, and repository changes remain under their existing owners.
The initial bounded-memory import failed and was resumed with fewer threads
and a larger memory allowance; this was an audit-data import failure, not a
Loop Engine task result.

Generated JSON and compressed indexes are exports, not an alternative product
source of truth. The database and exports remain local. The Markdown memo
records the design in the repository; no commit or publication occurred.

The review's temporary package snapshot and clean test environment were
removed after their work ended. They were generated copies under the review's
private temporary directory. The original source, built wheel, digests, and
diagnostic records remain available for reconstruction. No supplied reference
project or historical run directory was deleted.
