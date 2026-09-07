# History review and Overnight integration requirements

The configured Kaggle account has 1,049 unique entered competitions. That
confirms access breadth, not completed solutions. The local history also
contains real external scores, incomplete campaigns, and false acceptances.
Those results must remain separate.

This hand-authored report summarizes a local, read-only review. It exports no
credentials, membership list, raw private prompts, or conversation bodies.
The implementation and new live tests are in the
[adaptive host report](ADAPTIVE-HOST-GENERALIZATION-2026-09-06.md).

## Observed coverage

The first scan covered 39 Codex rollouts, 55 matching Claude transcripts, and
19 OpenCode sessions or fragments. It counted 142,074 selected records. These
include repeated context, tool output, and subagent transcripts, not 142,074
independent observations. Semantic review selected relevant user requests,
diagnoses, outcomes, and referenced artifacts; it did not read every record
as a separate claim.

Three additional deleted Codex rollouts remained open in project processes.
Read-only, fixed-prefix reads covered 47,084,075 bytes and 8,205 complete
records without moving the writers' file offsets, restoring a file, or
stopping a process. Once the last descriptor closes, such material may no
longer be recoverable through this interface.

The engine-record inventory covered 181 selected files and 63 event streams.
All 46 current-format Run History chains passed integrity checks, covering
25,595 events. Another 17 legacy histories contained 540 parsed events; this
review did not migrate or rewrite them. Chain integrity does not establish
task correctness or provider integration.

Editor discovery checked 21 VS Code workspace manifests, 162 chat/edit files,
and 22 workspace-state databases without finding project chat matches. One
global terminal-history entry matched. No matching Aider history was found at
the inspected locations. Remote-only conversations, unregistered stores, and
deleted files with no retained descriptor remain unknown.

Kaggle pagination reached a terminal empty page after 1,049 distinct entered
competition records. There were 56 listing reads including confirmations,
zero downloads, and zero submissions. The initial inventory's parser
diagnostic is preserved: the CLI returned `No competitions found` rather than
a JSON empty list. A separate completion receipt records that correction.

## Findings that affect current work

| Evidence | Interpretation and limit |
|---|---|
| Repeated user requests seek generalized tasks, actual execution and grading, and no agent-invented spending or 50-call ceiling. | Keep domain knowledge in capabilities and intelligence. Capacity, total authority, disclosure, and effect approval remain separate. |
| The Overnight prototype certified the Gantt result `a(0,2), b(2,7), c(2,3), d(7,9)` after independent checks. Other queued tasks failed. | One correct artifact is useful evidence, not proof of a generally successful unattended executor. |
| The prototype produced seven-unit and nine-leaf decomposition plans. Its reviewed logs still described the trimmed A/B and queue as running. | No terminal result was found for those particular experiments. A saved plan does not prove execution of its parts. |
| Prototype source could use `any_solved` as parent success and lacked typed dependency-result bindings. It forced splitting after failures. | Require independent whole-task acceptance and explicit result flow. Classify transport, authority, verification, and semantic failures before choosing to split. |
| Older reports blamed duration failures on prompt size and thinking controls. Later traces found valid code-only previews rejected because expected outputs were empty. | The historical single-cause diagnosis is disputed. Source-only admission and output-limit failures were distinct mechanisms. |
| Historical Kaggle summaries contain public scores and submission IDs. Other campaigns record only accessible files or structurally accepted artifacts. | The review did not reconfirm old scores against Kaggle. It does not establish 100 independently scored unfamiliar tasks. |
| A saved cold-to-warm interval proof records ten cold model calls, 208 independent qualification cases, exact promotion, and a zero-model warm run. | The proof used inline harvesting and an injected persistent resolver. It does not prove automatic universal reuse. |

The separate Overnight repository was inspected at
`86d857357a983a2dd0b7d0cc2ccb961b862ad290`. Its experimental Loop Engine clone
was at `690303f3ee97669f638da950daca665b747f450d` with substantial dirty work.
These are historical reference sources, not the current implementation at
`1ea13357c9d46d261fa4164fced0ef0b0249a36e` plus the reviewed patch.

## Integration boundary

Use Loop Engine's existing host interface for reasoning over a host-owned
workspace. The Overnight daemon should keep its protected repository gates,
path and Git policy, privacy checks, local effect authority, and human review
of branch proposals. A hosted reasoner can return proposals to that local
execution arm; it need not own the machine or replace the verifier.

The current task does not modify Overnight, connect Jira, accept new
competition rules, publish results, push branches, or merge proposals.
Concrete follow-on tasks and their acceptance tests are listed in the
[adaptive host report](ADAPTIVE-HOST-GENERALIZATION-2026-09-06.md#bounded-follow-on-work).

## Local evidence

The private review directory is
`/tmp/loop-engine-history-review.InZxfr`. Its `history-findings.md` gives source
anchors and historical caveats. The accompanying inventories retain source
hashes, selected record positions, chain checks, and Kaggle completion
metadata. Raw chat bodies were not copied there. This temporary location is
not a permanent archive; the repository summary intentionally retains only
the nonsecret findings needed for continued development.
