# Universal component and strict primitive report

Status: `PARTIAL, FINAL ASSURANCE NOT YET COMPLETE`

Starting revision: `f9bd2bc3419d28c029fe7af6eb558214c9c7a628`

This report records the current implementation evidence. It does not claim
that repository-wide strict primitive migration or final publication assurance
is complete.

## Implemented vertical slice

- `Loop` remains the sole runtime and graph-vertex type.
- `LoopComponentDefinition` and `LoopComponentRef` provide passive component
  identity, kind, payload digest, lifecycle, provenance, scope, compatibility,
  and refs.
- Static components cannot carry permissions or effects.
- Settings, personas, guidance, question portfolios, prompt profiles, and the
  Context Intelligence portfolio have component definitions.
- `LLMWorkPacket`, `WorkDirective`, `LLMContextBlock`, and
  `PromptAssemblySnapshot` are passive typed records.
- Context selection runs through an Intelligence-role Loop.
- Prompt assembly runs through a deterministic Practitioner-role Loop.
- Packet projection, JSON serialization, sequence ordering, text combination,
  UTF-8 sizing, token estimation, packet serialization, and model-output JSON
  parsing run through registered deterministic atomic Loops.
- `LoopValue` and `LoopValueRef` preserve producer, contract, source refs,
  digest, lineage, privacy, materialization, and verification.
- Native operations for the protected path are confined to
  `loop/intrinsic_kernel.py`.
- Generated project validation rejects offline network imports and projects
  that ignore every supplied researched input. A documentation mention or
  source comment does not count as input use.
- Safe fetched-resource basenames are preserved so a fetched `adult.data`
  resource is materialized as `inputs/adult.data` when names do not conflict.
- A stalled-progress signal activates separate diagnosis, changed-strategy,
  alternative-strategy, and adjudication model calls. It does not choose an
  immediate deterministic terminal route.
- Each recovery-panel result has one bounded semantic repair attempt.
- Blocking verification gaps reference registered task acceptance criteria.
  Advisory improvements and proposed new requirements remain separate.
- A standalone Ollama qualification lab renders one prompt per component case
  and audits saved runs without importing Loop Engine internals.
- Component inventory generation runs through a deterministic Practitioner
  Loop.

## Focused checks

Current focused results:

```text
adaptive Practitioner acceptance: 21/21 passed
adaptive Practitioner focused checks: 6/6 passed
generated project checks: 15/15 passed
adaptive capability checks: 2/2 passed
component contract checks: 5/5 passed
Context Intelligence checks: 7/7 passed
LLM work packet checks: 3/3 passed
strict primitive conformance checks: 4/4 passed
standalone qualification lab: 3/3 passed
zero-tolerance architecture gates: all passed
```

The final complete offline suite reported `1457/1457` with zero provider
calls after the input-use and recovery-contract changes.

## Clean package evidence

The final wheel and source archive passed `twine check`. The wheel was installed
with all declared dependencies into a new Python 3.10 environment outside the
checkout.

```text
wheel SHA-256: 00383e304a01e2844de997fa28d4cc4245697c95b88158963cf2b954bf631ea3
source archive SHA-256: 59b069c7ad57201aca0da1eb4b6dc9dc5f619445bbd00d73a0a8fd922a050749
pip check: passed
installed conformance: passed
installed self-test: 1456/1456 passed, zero provider calls
installed deterministic unseen task: NOT COMPLETED, zero model calls
installed Studio port 0: HTTP 200 on 127.0.0.1:43423
```

The installed and source suites have the same focused adaptive, generated
project, and capability test counts. The installed aggregate reports one fewer
check than the source checkout; that count difference has not been isolated.

## Generated audit artifacts

```text
artifacts/architecture/component_inventory.jsonl
artifacts/architecture/component_interactions.jsonl
artifacts/architecture/folder_map.json
artifacts/architecture/string_blob_findings.jsonl
artifacts/architecture/redundancy_findings.jsonl
artifacts/architecture/context_handoff_findings.jsonl
artifacts/architecture/generalization_candidates.jsonl
```

The current inventory contains 2,422 file, symbol, and explicit-component
records. The exact count changes as files and symbols change, so regenerate it
after the final implementation batch.

## Strict migration boundary

The protected adaptive prompt path has zero direct f-string, string-add,
`join`, `format`, or JSON operations outside the intrinsic kernel.

The repository-wide audit currently contains 3,141 exact native semantic
operation findings across established code. They are listed by file, symbol,
line, and operation. This is a migration backlog, not an allowlist and not a
passing strict-completion claim.

Repository-wide strict primitive migration remains `NOT YET PROVEN`.

## Live flagship evidence

The current public `task build` path completed the flagship modeling task:

```text
run_id: adaptive-918578b8fbd533b81a4907e4
passes: 2
model_calls: 16
fetched sources: 1
generated project attempts: 1
Run History events: 9,639
Run History chain: intact
final route: stop_success
status: VERIFIED_WORKING
```

Independent reopening confirmed:

```text
reports/model_comparison.pdf: 3,924 bytes, PDF header and EOF valid
reports/model_comparison.html: 3,562 bytes, HTML parser accepted
metrics.json: 7,627,489 bytes, JSON object accepted
project setup command: passed
project execution command: passed
project verification command: passed
```

The project consumed the fetched California housing CSV locally in a
network-disabled execution container. This run proves the flagship path, not
all unseen tasks.

## Changed-task and recovery evidence

A materially changed classification task exposed a real loop defect. Its first
run created deterministically valid Markdown, JSON, and fold-assignment files,
then repeated research and verification without integrating a repair:

```text
run_id: adaptive-daf9a253a0a186ad35f28a01
passes: 24
model_calls: 130
research decisions: 21
project deterministic checks: passed
Run History events: 75,129
final route: repair
```

The standalone lab flagged post-project research excess, repeated verification
gaps, a long unresolved run, and verified artifact state that was not terminal.

After recovery-panel and task-horizon repairs, another bounded run reached real
construction, rejected four projects that ignored supplied inputs, executed a
fifth project, diagnosed its missing data-file failure, generated two competing
recovery strategies, and selected one evidence-backed repair:

```text
run_id: adaptive-63e4b5a53903fd1707342e65
passes: 12
model_calls: 128
project attempts: 1
recovery directives: 1
Run History events: 72,821
final route: repair
```

That run ended when its declared pass budget was exhausted before the selected
repair could execute. It is useful recovery evidence, not changed-task success.

The latest source now preserves safe fetched filenames, rejects documentation-
only input references, gives every recovery result a semantic repair attempt,
and simplifies adjudication to selecting one already validated proposal.

A bounded changed-task rerun then completed without another core source change:

```text
run_id: adaptive-b0ed2b836ffe5a8ca6583d8c
passes: 2
model_calls: 16
input artifact: inputs/adult.zip
input-use validation: passed
project commands: 4/4 passed
verified artifacts: report.md, report.json
fold assignments: 3,000
Run History events: 9,624
Run History chain: intact
final route: stop_success
status: VERIFIED_WORKING
```

Independent inspection confirmed three requested model entries: logistic
regression, random forest, and scaled support-vector classifier. The JSON
contains the seed, five-fold contract, input digest, metrics, and exact fold
assignments.

The standalone black-box lab audited both successful runs. It returned `PASS`
with no findings for the flagship run and the changed-task run. The same lab
returned `FAIL` for the earlier 24-pass stuck run and preserved its exact
progress, verification, and terminal-state defects.

## Remaining gates

- Finish the typed global, long-, medium-, short-, parent-, and local handoff
  contract with demand-pull context.
- Add conditional question selection and rejected-question evidence.
- Migrate remaining protected product paths to atomic Loop primitives.
- Build and install a clean wheel and run the public CLI.
- Commit, push main, inspect required GitHub Actions, and repair failures.
- Run independent adversarial assurance and mutation tests.
