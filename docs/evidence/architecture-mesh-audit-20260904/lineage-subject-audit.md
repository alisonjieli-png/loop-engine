# Current dirty-worktree lineage and integration audit

Inspected against HEAD 22ee44052b027ba96ce50c37e4cc6a659e1b91c8 with dirty files. No checkout changes or provider calls. Reproducer: /tmp/loop-engine-lineage-subject-probe.py. Saved observed output: /tmp/loop-engine-lineage-subject-probe-result.json.

Run with:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 /tmp/loop-engine-lineage-subject-probe.py
```

## Finding 1: a real evaluation record for B can give local credit to A

Observed. The exact-subject invariant is missing at core/stage_action_lineage.py:385-404. The function verifies that the supplied evaluation is the last stored evaluation object, belongs to the current admitted verifier stage, matches flags/verdict, and has the verifier's current pass. Separately, it checks that a caller-supplied result payload hashes to the supplied execution's result digest. There is no checked link from the evaluation to its evaluated action, execution, plan, or result digest.

The producer, core/adaptive_practitioner_verification.py:145-154, actually sends its plan and results to the model, but the persisted adaptive_verification/v1 record at lines 222-237 contains no exact subject references or result/plan digest. Hashing this record later does not recover the missing subject identity.

Reproduction uses the real verify_adaptive_results function with an injected response, not merely a hand-made evaluation. An action/result A is selected and executed at pass 1. A current verify stage at pass 2 evaluates only plan B and result B. Its exact persisted record says 'Accepted B, which is the only supplied result' and carries the criterion 'Evaluate subject B only'. Feeding that genuine record to record_action_verification with A's older action/execution/result references succeeds. A becomes local_verification=True and credit=helped under attribution_method=DIRECT_LOCAL_VERIFIER. The observed A/B result digests are different.

A later verification of the same old result can be legitimate. The defect is not that different passes are always forbidden. The required contract is an exact evaluation-subject binding, with an explicit temporal rule if delayed verification is allowed. Merely refusing all cross-pass calls would mask this specific reproduction but would not establish the underlying subject invariant.

Scope limit: the current normal adaptive wrapper at adaptive_practitioner.py:544-547 passes one plan/results bundle sequentially to both verification and lineage. I did not demonstrate a normal single-threaded public solve spontaneously swapping those arguments. The failure is in the claimed fail-closed lineage boundary and its ability to reject stale/mismatched internal evidence. Existing adversarial tests test stale selection, missing or wrong-role verifiers, detached evaluation dictionaries, changed execution results, and duplicate joins. They do not test a genuine last evaluation of a different subject.

Current docs cautiously claim exact action/result/verifier references and mechanism-only evidence. Any stronger assertion that foreign or stale evidence cannot create credit needs qualification: the tests establish selected identity refusals, not every mismatched evaluation-subject combination.

## Finding 2: adaptive integration does not partition accepted and speculative state

Observed at adaptive_practitioner.py:549-561. integrate_commit copies a selected result to facts.last_result and adds all its artifact references to state.artifacts for every verdict. It never conditions these writes on acceptance. The kernel invokes integration after verification regardless of verdict at loop/kernel.py:546-559.

The reproduction begins with accepted state, integrates a rejected result with verdict=repair and errors=('verification failed',), and observes the wrong result replacing facts.last_result and rejected.csv joining state.artifacts. A later accepted result C leaves rejected.csv in the map while facts.last_verification now says accept for C. The map itself has no per-artifact accepted/rejected state. _model_state forwards facts and artifact_refs on the next pass at adaptive_practitioner.py:93-100.

This is narrower than a persistent trusted-state promotion exploit. The rejected ResultPacket's errors are preserved in last_result, the contemporaneous repair evaluation is preserved, and the input PractitionerState remains unchanged in this probe. The state type itself is mutable and its derive operation makes shallow copies. Run History can retain the older failure. No evidence here shows independent Intelligence promotion or a semantic_runtime trusted-commit token being bypassed. The concrete gap is that the adaptive loop's 'integrate accepted work' description has no typed accepted/speculative partition in its current state maps, and its last-verification slot is insufficient to qualify every retained artifact later.

The default kernel is different: default_integrate_commit is a no-op and default_route adds accepted/provisionally accepted artifacts only. The adaptive implementation overrides that behavior.

## Secondary defect: unchecked best_index can end integration

Observed. verify_adaptive_results accepts int(value.get('best_index', 0)) at line 202 without checking the number of results. integrate_commit indexes record.results[record.evaluation.best_index] at line 554. The offline probe with one result and best_index=7 raises IndexError. This is a model-output validation gap, not a stage-credit authority grant. Negative indexes and booleans also receive no explicit rejection at the shown boundary.

## Inspected file identities

```text
879856313c8948c91c5a63bd726ba01b224f01816ee1fc9d5103efe11025efb0  src/loop_engine/core/stage_action_lineage.py
00ae7d8aa1fd80c83f3cd3f42ababa0f9d6a27391d2466cc5e55b2f655a938d3  src/loop_engine/core/stage_action_lineage_adversarial_checks.py
fbd909c680653c6dcbd449e368ec219129eb126333d29f990462ce9ad766d0b2  src/loop_engine/core/adaptive_practitioner.py
fd54a790bebfa3d34fce26e49db43925523eb15b814fe5507f77ca20c4f2109f  src/loop_engine/core/adaptive_practitioner_verification.py
```
