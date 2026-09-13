# Claude Fable 5.1 review of Loop Engine, 2026-09-13

This is the review requested in
[the review handoff](../context/CLAUDE-FABLE-5.1-REVIEW-HANDOFF-2026-09-13.md)
and its
[dimension discovery addendum](../context/CONFIGURATION-DIMENSION-DISCOVERY-ADDENDUM-2026-09-13.md).
It was performed by Claude Fable 5.1 on 2026-09-13 between 07:30 and 08:30
local time, read-only, with no provider call, no commit of other people's
work, and no change to any tracked file other than adding this report.

## Facts about the reviewed state

- Repository `/home/username/loop-engine`, branch `main`, `HEAD`
  `0cb7b86cb7f5b1f6a6b1b798da4e0a4a1469e00f`. The configured upstream
  `origin/main` is at `acfd826`, one commit behind.
- The working tree had 75 modified tracked files and 124 untracked paths.
  Under `src/loop_engine` alone, 55 tracked modules are modified and 46
  modules are untracked. The untracked modules include the entire harness
  subsystem that this review was asked to inspect: `core/harness_process.py`,
  `core/harness_process_relay.py`, `core/harness_semantic.py`,
  `core/harness_fallback.py`, `core/harness_configuration.py`,
  `core/harness_selection.py`, `core/harness_selection_records.py`,
  `core/harness_response_evaluation.py`, every `core/harness_*recipe*.py`
  module, `core/observation_expectations.py`, `core/model_prompt_envelope.py`,
  `core/recovery_learning.py`, and `core/verifier_execute.py`. Neither `HEAD`
  nor `origin/main` contains them. The last three CI runs on the pushed
  `main` (2026-09-08) all failed.
- The live Codex session that prepared the handoff was still writing during
  this review. It changed the handoff, the dimension document, and
  `architecture.yaml` between 07:37 and 07:39, and its rollout file was still
  growing at 07:41. The findings below were checked against the working
  tree bytes after those changes.
- The Bash tool was unavailable to this session (every command exited 1
  with no output), so probes were run through a monitored shell. Probe
  scripts and their outputs are in
  `.loop-engine-dev/fable-review-probe-20260913/` (ignored by git) with a
  copy under `artifacts/fable-review-20260913-p75Wml/probes/`.

## Summary

1. The new selection, evaluation, and recovery code is careful, small, and
   mostly does what its documentation says. Every targeted self-test rerun
   for this review passed, including the Bubblewrap process qualification
   (20 of 20), which is not part of the reported 3,940-check suite.
2. One defect undermines the central recovery contract: the model gateway's
   own route failover runs inside a harness attempt and inside the direct
   path. A registered evaluator's rejection is treated as
   `output_validation_failed`, so the gateway tries the next route, on
   another provider, even when the fallback policy forbids every kind of
   recovery. The semantic-rejection permission gate can therefore be
   bypassed without any harness switch (defects D1 and D2).
3. Selection evidence can be inflated by copying one Run History reference
   under a second trial identity; the policy deduplicates only `trial_id`.
   A copied successful record can change which harness ranks first, not
   only satisfy the minimum-evidence gate (D3).
4. The spawned task checkpoint reader accepts any record whose digest field
   is an empty string, and silently truncates non-integer counters in that
   case. This is a pre-existing weakness that the compatibility work did not
   close (D4).
5. `core/verifier_execute.py` runs an operator-declared script on the raw
   host: a one-second timeout leaves its descendant processes running, the
   declared output cap is never applied, and the partial output the error
   message promises is not returned (D5). It is on the product solve path.
6. The evaluator callback receives only the response text, and its Run
   History record does not carry the subject contract identity the handoff
   says is recorded (D6).
7. None of the reviewed implementation is reachable from the product command
   line: `loop-engine solve` binds at most one harness with no fallback
   policy, no selection policy, and no registered evaluator. The mechanisms
   are exercised only by fixtures and by the embodiment laboratory.
8. Of the 25 baseline dimensions, four have an ordered fallback in code
   (harness, model route, run mode, thinking power). The rest have an
   initial choice, a refusal, or nothing. No dimension has the full
   required record (initial value, required or absent or unknown state,
   ordered fallback, compatibility, transition trigger, authority, evidence,
   and outcome). Details are in the dimension table below.

### The owner's question

On 2026-09-13 the owner asked the Codex session whether the system is smart
enough to try the best harness for each individual cognitive or act step.
The accurate answer today is: it can try the next configured harness for one
semantic call, in a fixed order, after a typed failure, while preserving the
deadline, remaining calls, tokens, and prior failure observations. That path
is tested offline and was demonstrated live once on 2026-09-12 (one Pi to
OpenCode recovery). It can rank the configured harnesses from host-supplied,
reviewed trial evidence, but only inside one fixed model route and only when
a response expectation is bound; nothing learns that ranking. The gateway
can also change the provider underneath a harness attempt, which the harness
policy neither sees nor controls (D1). None of this is switched on by the
product command line.

## Observed defects

Each defect names the location, the exact condition, the expected behavior,
the observed behavior from a probe, and a regression check to add. Line
numbers refer to the working tree at review time.

### D1. Gateway route failover bypasses the semantic recovery permission

- Location: `src/loop_engine/core/model_gateway.py`, `ModelGateway.invoke`
  route loop (lines 1190 to 1226 continue to the next route after any failed
  attempt whose code is not in `_FAILOVER_FORBIDDEN_ERRORS`, line 635);
  `src/loop_engine/code_nodes/solution_model_port.py` lines 401 to 412 wrap
  the registered evaluator inside the gateway `validate` callback;
  `src/loop_engine/core/harness_semantic.py` line 459 passes the complete
  route set into `gateway.invoke` and lines 269 to 273 authorize every route
  for the harness. `ModelGatewayConfig.allow_failover` defaults to `True`
  (line 221, unchanged since 2026-08-26).
- Condition: two eligible routes; a registered evaluator rejects the first
  route's structurally admitted answer.
- Expected: per the harness recovery guide, a semantic rejection stops the
  step unless `HarnessFailureKind.SEMANTIC_REJECTED` is permitted, and
  "changing a harness never silently changes the model or provider". The
  dimension document requires cross-provider failover and evaluator-triggered
  repair to stay distinct.
- Observed, direct path (probe E): providers attempted `['alpha', 'beta']`,
  attempt error codes `['output_validation_failed', '']`, evaluation
  statuses `['rejected', 'passed']`, result `ok`, two physical calls charged,
  no harness assessment event, no record that a semantic rejection caused
  the second call.
- Observed, harness path (probe H): with `HarnessFallbackPolicy(('first',
  'second'), ())`, which permits no recovery at all, the first harness
  attempt made two provider calls (alpha rejected semantically, then beta),
  the attempt was assessed `response_admitted`, and the second harness was
  never used. The policy's empty `switch_on` had no effect.
- Related conflation: in the direct path, when a later route fails
  structurally after an earlier semantic rejection,
  `solution_model_port.py` lines 429 to 431 relabel the whole result
  `semantic_response_rejected` because only the last evaluation is consulted.
  The gateway's power escalation trigger `escalate_on` also fires on
  `output_validation_failed`, so an evaluator rejection can raise thinking
  power without a distinct permission.
- Regression checks to add: `semantic_rejection_does_not_fail_over_routes`
  (two-route fixture gateway, evaluator rejects route one, assert one physical
  call and error code `semantic_response_rejected` in the direct path) and
  `harness_attempt_cannot_change_provider_after_semantic_rejection` (same
  gateway behind a harness with an empty `switch_on`, assert one physical
  call and decision `failure_not_permitted_by_policy`).
- Candidate fix: give the evaluator verdict its own attempt error code
  (`semantic_response_rejected`) inside the gateway, add it to
  `_FAILOVER_FORBIDDEN_ERRORS` and exclude it from `escalate_on`, and let a
  separate explicit permission (not `allow_failover`) authorize
  evaluator-triggered route changes. Existing fixtures never see this because
  every fixture gateway has a single route.

### D2. Harness fallback policy does not govern the routes a harness attempt may use

This is the harness-side half of D1, recorded separately because it needs its
own contract. `HarnessSemanticBinding._invoke_one` (harness_semantic.py
lines 269 to 275) authorizes `model_routes` and
`authorized_model_identities` for every eligible route, so a single brokered
request can legitimately consume several providers. The recovery guide's
statement that a harness change never changes the model or provider is true
only for the harness switch itself. Regression check:
`harness_attempt_uses_exactly_the_primary_route_unless_route_failover_is_granted`.

### D3. Duplicate Run History references inflate matched selection evidence and can change the winner

- Location: `src/loop_engine/core/harness_selection_records.py`
  `HarnessSelectionPolicy.__post_init__` line 176 refuses duplicate
  `trial_id` only; `src/loop_engine/core/harness_selection.py` lines 52 to 72
  count records per harness against `minimum_records`; `subject_digest` is
  carried by every trial but never compared anywhere in the selector.
- Condition: two reviewed records for the same harness with different
  `trial_id` values and identical `history_ref` and `history_digest`.
- Expected: one Run History reference is one trial; `minimum_records` is a
  count of distinct trials.
- Observed (probe B): with `minimum_records=2`, the honest policy returned
  `insufficient_matched_reviewed_evidence` and preserved the configured
  order, while the policy with the copied record returned
  `ranked_matched_reviewed_evidence`, reported two matching records for the
  first harness, and listed the same history reference twice in
  `evidence_refs`. The first version of this report said duplicates could
  not change the ranking score because quality is a ratio. That is wrong
  when a harness has trials with different outcomes: duplicating only a
  successful trial raises the pooled ratio. Codex reproduced this, and
  acceptance scenario D3b confirms it: with `first` at 4 of 4 then 0 of 4
  and `second` at 3 of 4 then 2 of 4, the honest order is `second` then
  `first`; one copied successful record makes it `first` then `second`.
- Regression check: `duplicate_history_references_cannot_satisfy_minimum_records`.
- Candidate fix: refuse duplicate `(history_ref, history_digest)` and
  duplicate `subject_digest` per harness at policy construction, or count
  distinct references in `select_harness`.

### D4. Checkpoint reader accepts an unsigned record and coerces its counters

- Location: `src/loop_engine/loop/spawned_task_checkpoint.py` line 351
  (`if self.checkpoint_digest and self.checkpoint_digest != computed`) and
  `from_dict` lines 401 to 403 (`int(value[...])`). The same guard exists in
  `HEAD` at line 340, so this predates the compatibility work.
- Condition: a serialized checkpoint whose `checkpoint_digest` is an empty
  string.
- Expected: a record read from storage must carry a digest that matches its
  body; a fabricated or altered historical record must not load.
- Observed (probes A and F): a record with a tampered goal and an empty
  digest loaded, and the reader assigned it a fresh digest. The same
  tampering with the original digest was refused, and a record without the
  digest key was refused. A record with `update_count` of `2.9` and an empty
  digest loaded with `update_count` equal to `2`.
- Regression checks: `blank_checkpoint_digest_is_refused_on_read` and
  `non_integer_checkpoint_counters_are_refused`.
- Candidate fix: require a 64-character digest in `from_dict` while keeping
  the blank digest only for in-process construction, and validate counter
  types before conversion.

### D5. The raw-host verifier does not contain what it starts

- Location: `src/loop_engine/core/verifier_execute.py` lines 50 to 74.
  Registered on the product path by
  `src/loop_engine/core/adaptive_practitioner_capabilities.py` line 256, fed
  by `SolveRequest.verifier_path`.
- Condition: a declared verifier that starts a background process and then
  exceeds `timeout_seconds`.
- Expected: a timed-out verifier and everything it started stop; captured
  output is bounded by the declared `MAX_OUTPUT_BYTES`; the error carries the
  partial output it claims to retain.
- Observed (probe D): `subprocess.run` killed only the `bash` process. A
  descendant started by the script wrote a marker file three seconds after
  the one-second timeout, and two `sleep 30` processes were still alive.
  `MAX_OUTPUT_BYTES` (8192) is defined and never used; `capture_output=True`
  reads without bound. The raised `VerifierError` says "partial output
  retained" but carries no output attribute.
- Regression checks: `verifier_timeout_terminates_descendants`,
  `verifier_output_capture_is_bounded`,
  `verifier_timeout_error_carries_output_tail`.
- Candidate fix: `start_new_session=True` and `os.killpg` on timeout, a
  bounded reader, and the tail attached to the error. A better fix routes the
  verifier through the existing restricted workspace backends. The handoff is
  right that this path must not support any containment claim.

### D6. Evaluator records omit the subject contract, and the callback is input blind

- Location: `src/loop_engine/core/harness_response_evaluation.py`.
  `HarnessResponseEvaluator` carries `subject_contract_ref` and
  `subject_contract_digest` (lines 45 to 46) but `HarnessResponseEvaluation`
  (lines 63 to 73) records only the evaluator's own contract, digests, the
  semantic call, input and response digests, status, findings, and verifier
  Loop. The callback signature is `evaluate(text)` (line 47).
- Condition: the same evaluator applied to the same text under two different
  input digests.
- Expected per the handoff: "its subject contract and occurrence are
  recorded". The occurrence is recorded; the subject contract is not.
- Observed (probe C): both calls returned `passed`; the record keys are
  `contract_ref`, `implementation_digest`, `qualification_digest`,
  `semantic_call_id`, `input_digest`, `response_digest`, `status`,
  `finding_codes`, `verifier_loop_id`, plus the two constant refusal flags.
  The evaluator cannot tell a wrong-task or stale-oracle case apart because
  it never sees the input; the guide documents this limit correctly.
- Regression check: `evaluation_record_binds_the_subject_contract`.
- Candidate fix: add `subject_contract_ref` and `subject_contract_digest` to
  the record as `harness_response_evaluation/v2`, and define a version 2
  callback contract that receives the bound expectation and input digest so a
  host oracle can be tied to the actual input.

### D7. Definition reader error type and message

`LoopDefinition.from_dict` promises `LoopDefinitionError`, but a version 2
record with a cardinality on an undeclared role or a Boolean `max_items`
raises `LoopContractError` from `src/loop_engine/loop/loop_contract.py`
line 197 or 134 (probe F). A version 2 record whose `input_cardinalities`
list is valid but not sorted by role is refused with "content digest does not
match its content" even though its stored digest is correct; the real reason
is canonical ordering. Both are low severity. Regression check:
`definition_reader_raises_only_definition_errors`.

### D8. The legacy checkpoint helper always reports failure

`tools/make_checkpoint.py` (untouched by the cleanup) has the defects listed
in `checkpoints/README.md`. Inspection adds one more: `_run` concatenates
standard error with standard output, and the current self-test writes
progress lines to standard error, so `json.loads` in `_self_test` can never
succeed and every run reports `unknown` counts and exit status 1. This was
found by reading, not by running the helper, as the handoff requested.

## Inferred risks and missing proof

- R1. Host attestation of selection evidence. A `HarnessSelectionPolicy`
  file is trusted input: its content digest detects corruption, not forgery;
  `history_ref` and `history_digest` are never resolved; `reviewer_ref` is
  any label other than the trial or harness identity. The guide says so.
  The addendum's proposal "Observability and attribution" is the right place
  for a host signature or a store-backed reference check.
- R2. Population coverage. Matching uses `(population_digest, evaluator_ref,
  evaluator_digest)`. Trials with one observation and trials with one hundred
  observations on the same population are pooled by ratio. Documented, but
  the ranking has no minimum per-arm observation count.
- R3. Selection engages only when a response expectation is bound. Without
  one, `harness_selection_unavailable` is recorded and the configured order is
  used (probe G). Product invocations bind an expectation in only two places
  (`adaptive_practitioner_records.py` line 2489 and `recovery_learning.py`
  line 74), and no product path installs a selection policy or evaluator.
- R4. Exceptions raised by the Loop machinery around an evaluator (for
  example a spawn depth refusal) surface inside the gateway `validate`
  callback and become `output_validation_failed`, not `inconclusive`. Only
  exceptions inside the host callback itself become inconclusive.
- R5. Legacy campaign tooling (`examples/25_host_runtime`). Attempt retention
  is reasonable: per-task run directories, exclusive-create JSON, runner
  failure records, and a report written on interrupt. Evaluator leakage is
  mitigated by `feedback()` in `generalization_probe.py`, which removes
  expected values and truncates observed values above 1,024 bytes, but a
  candidate can still echo an input of at most 1,024 bytes back to the model
  through the observed value, which discloses small case arguments. The
  version 1 audit keeps its evidence under `/tmp` and its grid generator's
  "invalid variant" branch is dead code (`novel_task_audit.py` lines 51 to
  53), so the audit never exercised the period-separated grids the prompt
  described. The version 2 tooling addresses the evidence location; it has
  not run.
- R6. Native mechanisms (handoff question 6). The process adapter declares
  `configuration_isolation`, `credential_isolation`, `private_prompt_channel`,
  `private_raw_events`, `process_tree_cancellation`, and `model_routes`, with
  `isolation='os_sandbox'`. Tools, skills, plugins, and hooks are refused by
  `unmet_harness_requirements` because the adapter declares none of those
  features; that refusal is tested. Native instruction loading exists only in
  the experimental forks under `devtools/embodiment_lab` (nine live controls on
  2026-09-12). Process reuse is neither implemented nor tested: every attempt
  creates a fresh run directory and a fresh Bubblewrap process. Cancellation
  and credential isolation are tested by
  `harness_process_checks.qualification_checks`, which is Linux only and
  outside the base self-test; it passed 20 of 20 here.
- R7. The recovery guide's example configures `HarnessFailureKind.UNAVAILABLE`
  and `INCOMPATIBLE` as switch causes, but the semantic binding never produces
  `adapter_unavailable` through `assess_harness_attempt` for a shared
  configuration failure; those results return before an adapter launch and
  end the step. This is correct fail-closed behavior, but the example
  overstates what the causes do.
- R8. `ModelGatewayConfig.allow_failover` defaults to `True` at the class
  level. Product paths set it from the route plan length
  (`core/runtime_settings.py` line 514, `core/model_routing_selector.py`
  line 148), which means configuring two routes silently authorizes
  cross-provider failover. The dimension document requires an explicit
  authorization.
- R9. Governance conflict. The owner's standing instruction of 2026-09-02 was
  to commit and push every verified change to `main` immediately. The
  cleanup rewrote `docs/context/START-HERE.md` to forbid committing without
  a current authorization, and neither Codex session committed anything.
  The result is that the GitHub `main` branch is five days behind a working
  tree that holds the harness subsystem, the recovery work, and this cleanup,
  and the owner's notebooks that install from GitHub cannot see any of it.
  Which rule is current is the owner's decision; the two documents disagree.

## Answers to the ten priority questions

| Question | Answer |
|---|---|
| 1. Selection influenced by unmatched evidence, stale versions, different evaluators, unequal coverage, duplicates, unknowns | Unmatched populations, changed adapter versions, changed provider or model, changed scope digests, and rejected reviews are excluded (29 checks rerun, all pass). Duplicate Run History references pass the minimum-record gate (D3). Unequal per-arm observation counts pool by ratio (R2). Unknown measurements sort after known ones and never become zero. Host attestation is trust, not verification (R1). |
| 2. Evaluator bound to the input-dependent obligation | No. The callback sees only text; wrong-task and stale-oracle cases produce the same verdict (probe C). The subject contract is checked at registration and match time but is not in the Run History record (D6). |
| 3. Semantic rejection and inconclusive evaluation preserve usage, deadlines, failure history, effects, and registration | Across harness attempts: yes (42 fallback checks and 16 evaluation checks rerun, all pass; remaining deadline and calls are passed down; effects and uncertain accounting stop the step). Inside one attempt: no, because the gateway may spend additional provider calls on other routes before the harness policy is consulted (D1, D2). |
| 4. Historical encodings keep exact digest and meaning | Yes for the cases tried: version 1 definitions with and without output fields, version 2 checkpoints with the eight-field contract, refusals for version 3 definitions, version 1 checkpoints, cardinality on a version 1 record, undeclared roles, Boolean bounds, extra keys, and a version 2 checkpoint carrying multiple output (probe F). The blank-digest bypass in D4 is the exception. |
| 5. Each of the 25 dimensions | See the table below. Four dimensions have an ordered fallback in code; none has the complete required record. |
| 6. Native tools, skills, plugins, hooks, instruction loading, process reuse, cancellation, containment | Refusal of tools, skills, and plugins is tested; support is absent by design. Instruction loading is tested only in experimental forks. Process reuse is not implemented. Cancellation and credential isolation pass the Bubblewrap qualification (R6). |
| 7. `verifier_execute.py` | Not a sandbox: descendants survive the timeout, output capture is unbounded, partial output is dropped (D5). It sits on the product solve path. |
| 8. Old campaign evidence | The withdrawn claims stay withdrawn. Attempt retention is adequate; a small-input echo channel and a dead invalid-input branch remain in the version 1 tooling (R5). |
| 9. `tools/make_checkpoint.py` | Confirmed defects plus one more: it can never parse the current self-test output (D8). Not run. |
| 10. Mechanism tests versus live quality | Every count in the handoff is an offline mechanism count. No live call qualified selection or semantic recovery. Continued alternative-output production, portable Solution graph replay, and cross-task learning remain unestablished; the six live diagnostic runs on one task on 2026-09-12 solved none of them. |

## Status of the 25 baseline dimensions

Status words: implemented (a typed contract exists), tested (offline checks
exist), live (at least one real provider run exercised it), unsupported
(refused by design), planned (documented only). Fallback means an ordered
alternative that the runtime can select on a typed trigger.

| Dimension | Owning typed contracts | Initial choice | Ordered fallback | Status |
|---|---|---|---|---|
| Harness implementation and process initialization | `HarnessProcessSpec`, `HarnessSemanticBinding`, `HarnessFallbackPolicy`, `HarnessSelectionPolicy` | pinned adapter, command, mounts; optional reviewed ranking | ordered adapter identities gated by `HarnessFailureKind` | implemented, tested, live once (Pi to OpenCode); not reachable from the product command line; process reuse unsupported |
| Role profile | `LoopRoleIdentity`, `LoopProfileRef`, `resolve_profile` | exact versioned profile | none | implemented, tested; fallback planned |
| Step profile | `LoopConfig.framework`, `custom_steps` | atomic, compact, nine step, custom | none for step order | implemented, tested; fallback planned |
| Model | `ModelRoute`, `allowed_models`, `route_plan` | exact model per route | ordered routes under `allow_failover` and `max_route_attempts` | implemented, tested, live; D1 applies |
| Provider and route | `ProviderSpec`, `RouteRegistry`, `RoutePolicy`, `credential_ref` | exact provider and credential reference | same list as model; same-provider and cross-provider not separated | implemented, tested, live; R8 applies |
| Tools | `HarnessRunRequest.tool_refs`, `unmet_harness_requirements`, `HostRuntimeBinding` | engine-registered tools; harness-native tools refused | none per capability | implemented and tested for engine tools; unsupported for harness tools; fallback planned |
| Skills | `SkillAdmissionRecord`, `SkillRegistry` | reviewed skill by digest | none | implemented, tested, live once; fallback planned |
| Context Markdown files | Context Intelligence, `InformationResolver`, `context_refs` | selected references | none | implemented, tested, live variants measured; fallback planned |
| Harness-native instruction Markdown files | experimental forks only; `load_harness_binding` refuses extra fields | none in product | none | unsupported in product; nine live controls in experiments |
| Prompt-injected Markdown and prompt construction | `PromptResourceBundle`, `PromptSlotDefinition`, `ModelPromptEnvelopeBinding` | versioned templates and slots | none | implemented, tested; fallback planned |
| Plugins | `PluginBundleManifest`, `ResolvedPluginSnapshot` | passive bundle | none | implemented, tested; harness plugins unsupported; fallback planned |
| Hooks | `LifecycleExtensionDefinition`, `resolve_extensions` | resolved extension set | none | implemented, tested; fallback planned |
| Input contract | `LoopContract.input_roles`, `LoopInputCardinality`, `validate_loop_connection`, `LoopPortBinding` | typed ports and bounds | explicit Adapter Loop binding only | implemented, tested (21 checks) |
| Output contract | `output_type`, `max_outputs`, `ObservationExpectation`, `ModelResponseAdmissionPolicy` | schema-bound expectation | permitted normalization | implemented, tested, live admission results on 2026-09-12 |
| Supervisors and independent verifiers | `SupervisionPolicy`, `HarnessResponseEvaluator`, `IndependentVerificationPolicy` | registered evaluator | none; missing evaluator refuses | implemented, tested; not installed on any product path; D6 applies |
| Thinking power | `llm_thinking_power`, `ModelRouteAttemptSpec.thinking_power`, `allow_power_escalation`, `escalate_on` | per route | escalation ladder, opt in | implemented, tested; provider-unsupported state not modeled; D1 trigger overlap |
| Model-call strategy | `max_route_attempts`, `max_model_calls`, `HarnessFailureKind`, adaptive recovery panel | counted physical calls | distinct categories in the harness path, conflated in the gateway path | partial; D1 applies |
| Model generation settings | `temperature` only | temperature | none; unsupported settings are not refused | partial |
| Model output allocation | `ModelOutputCapability`, `ModelOutputAllocation`, `_fit_window` | source-backed capacity | alternative allocation within capacity | implemented, tested (15 checks) |
| Loop usage and orchestration | `DelegationSpec`, `SpawnedTaskManager`, reactive scheduler | serial spawned work | none; process reuse unsupported | partial |
| Run mode | `allowable_modes`, `preferred_modes`, `delegated_modes`, mode waterfall | mode per Loop | waterfall | implemented, tested |
| Intelligence and Runtime Memory | four layers, `InformationResolver`, `learned_memory_for_solve` | selected sources | none | implemented, tested; fallback planned |
| Workspace and execution environment | Bubblewrap process adapter, Docker workspace, restricted local workspace, raw-host verifier | declared sandbox | Docker unavailable falls back to restricted local; verifier has no fallback | partial; D5 applies |
| Budgets, permissions, and effect policy | `HarnessBudget`, gateway limits, `EffectApprovalService`, `LoopRuntimeContext.permissions` | explicit authorities | narrower only; never replenished | implemented, tested |
| Loop condition, exit condition, and output publication | `LOOP_CONDITIONS`, `EXIT_CONDITIONS`, reactive `CandidateOutput`, `OutputPortfolioSnapshot` | declared conditions | recovery paths through the adaptive Practitioner | implemented, tested; continued alternative production not live |

## The 21 proposed dimensions and six more

The addendum's 21 proposals are reasonable separations. Against the code,
they fall into three groups.

Already represented in part: state continuity and checkpointing
(`SpawnedTaskCheckpoint`, reactive leases), cancellation and effect
reconciliation (`run_harness_process` kills the process group; the verifier
does not), failure classification and escalation (`HarnessFailureKind`,
gateway error classification), evaluation coverage and calibration
(`IndependentVerificationPolicy`, counterexample gates), observability and
attribution (Run History, prompt envelopes), reuse and invalidation
(`adaptive_practitioner_reuse`, the capability flywheel), configuration
binding (`parameter_resolution` precedence), search strategy (reactive
portfolios, task frontier), output serving (reactive outputs), learning
transfer (`recovery_learning`, candidate only), schedule triggers (reactive
scheduler), dependency reproducibility (`HarnessProcessSpec` software
digests, pinned Docker image).

Partly represented: objective and risk policy (`HarnessSelectionPolicy` knows
two objectives and nothing about risk), task framing and uncertainty (intake
and the ask-when-material mode), reasoning and action method (planning),
context allocation and compression (`context_budget` estimates only),
privacy and retention (artifact confinement and effect approval; no recipient
policy), transport and backpressure (reference delivery; reactive at least
once), randomness (temperature only; no seed record).

Not represented: modality and semantic representation (no field in
`LoopContract`), information freshness and contradiction.

Six dimensions that neither list names and that changed outcomes in the
saved evidence or in this review:

1. Interaction mode and human authority. Existing: `InteractionMode` on the
   solve request and typed answer slots. Missing: who may answer, answer
   timeout, and the fallback (abstain, typed blocker, or autonomous
   assumption) when no human is available.
2. Response admission and normalization policy. Existing:
   `ModelResponseAdmissionPolicy`, `observation_expectations`. The 2026-09-12
   study showed that fence removal alone decided admission for three
   harnesses. Initial: strict or permitted normalizations; fallback: a
   formatting repair call or a provider structured-output mode, each counted.
3. Wire protocol and adapter recipe. Existing: the relay speaks chat
   completions, responses, Anthropic messages, and Google generate content.
   The wire is a compatibility decision with its own failure modes and should
   be recorded per attempt.
4. Model identity drift and revalidation. Existing: `model_identity_mismatch`
   and capability records. Missing: a trigger to revalidate a hosted model
   that changed behind a stable identifier, and what evidence expires when it
   does.
5. Cost estimation and price authority. Existing: `cost_state: unknown`
   everywhere. Missing: the price source, currency, and what a run may do
   when cost is unknown versus bounded.
6. Retry pacing and rate-limit policy. Existing: 429 classification and
   endpoint pacing in campaigns. Missing: a typed backoff and pacing policy
   separate from the model-call strategy, so a campaign cannot exhaust a
   provider by design.

## Recent Codex sessions

Two of the eight most recent Codex sessions ran in this repository. The
other six worked on unrelated projects.

Session `01a09478` (started 2026-09-12 07:15 UTC, 25 user turns) received the
owner's brief to review everything, the rule to write JSON through DuckDB,
the request to test more unseen tasks across all harness and context
combinations, the instruction to add "is this what I expected" checks (which
became `core/observation_expectations.py` and `core/recovery_learning.py`),
and the instruction that each step should be able to try several harnesses
(which became `core/harness_fallback.py`). Its own reports were candid: one
live Pi to OpenCode recovery, one OpenCode to Pi to Codex exhaustion, zero of
three runs on one fresh Kaggle-derived task, zero of six diagnostic runs, nine
distinct tasks in total, and a clear "not AGI" answer. It proposed the
shorthand "discrete-step Loop", was corrected twice, restored the full phrase
and explanation, and ended with the handoff before an account change. Nothing
was committed.

Session `01a096fd` (started 2026-09-12 18:59 UTC, nine user turns, still
running during this review) found five documentation problems, ran the
70-call configuration study, answered "Did it work?" with "the tested
mechanisms worked", answered the harness question with "it can try the next
configured harness, it does not learn which is best", then built the
selection and evaluation code, the cardinality and compatibility work, the
scan scope change, the 25-dimension document, the handoff and evidence
bundle, and finally the addendum with 21 proposals. It loosened the dimension
test from an exact count of 25 to a baseline-preserving check, which is the
right change. Its verification counts (3,940 source checks, 3,905 clean
installation checks, 175 targeted checks, 39 experiment tests) are
reproducible in spirit: every targeted component rerun for this review
passed. Nothing was committed.

Three statements from those sessions need correction. The handoff's claim
that the evaluator's subject contract is recorded is half true (D6). The
handoff's claim that recovery after a semantic rejection requires explicit
permission is true of the harness switch and false of the gateway route
switch (D1). The turn-one finding that "publication instructions conflict"
was resolved by removing the commit-and-push requirement from
`START-HERE.md`, which conflicts with the owner's standing instruction (R9).

## What this review did not do

No provider was called. No live qualification of selection or semantic
recovery was attempted. The 3,940-check suite was not rerun in full; the
targeted component suites and the Bubblewrap qualification were. Continued
alternative-output production, portable Solution graph replay, and cross-task
learning were not assessed beyond confirming that no evidence establishes
them. No fix was applied; every candidate fix above remains a candidate until
it is implemented with its regression check and verified through Loop Engine.

## Reproduction

Run from the repository root with the project interpreter:

```bash
export PYTHONPATH=src:devtools
export TMPDIR=$PWD/.loop-engine-dev/fable-review-probe-20260913/tmp
.venv/bin/python artifacts/fable-review-20260913-p75Wml/probes/probe_review.py
.venv/bin/python artifacts/fable-review-20260913-p75Wml/probes/probe_f.py
```

Probe sections A through H print `OBSERVED` lines; the outputs recorded at
review time are `probe-output.txt` and `probe-f-output.txt` beside the
scripts. The targeted self-tests were rerun with the results
`core.harness_selection 29/29`, `core.harness_response_evaluation 16/16`,
`core.harness_fallback 42/42`, `core.harness_semantic 15/15`,
`loop.loop_contract 21/21`, `loop.loop_definition_checks 18/18`,
`core.verifier_execute 5/5`, `loop.delegation_checkpoint_checks 10/10`, and
`core.harness_process_checks.qualification_checks 20/20`. The changed
dimension test ran 10 tests and passed, and the 21 proposals in
`architecture.yaml` all name an existing boundary file and appear in the
dimension document; the packaged copies of `architecture.yaml` and
`terminology.yaml` are byte-identical to the root files.

## Fixes applied on 2026-09-13

After Codex's assessment the owner asked for the defects to be fixed. The
fixes below follow Codex's guidance: each adds an explicit permission or a
stricter reader; none removes a configurable option.

| Defect | Fix | Regression checks |
|---|---|---|
| D1, D1b, D2 | `ModelGateway` records an evaluator's verdict on the attempt as `semantic_response_rejected` or `response_evaluation_inconclusive` (typed `ValidationVerdict` raised by the evaluator wrapper) and stops the invocation on that route. The new `ModelGatewayConfig.allow_evaluator_route_failover` permission, off by default, is the only way a verdict may move to another route. `assess_harness_attempt` classifies the verdict codes as evaluation outcomes, never as provider failures. | `evaluator_rejected_verdict_does_not_fail_over_to_another_route`, `evaluator_inconclusive_verdict_does_not_fail_over_to_another_route`, `explicit_permission_allows_evaluator_triggered_route_change`, `harness_attempt_cannot_change_provider_after_semantic_rejection` |
| D3, D3b | `HarnessSelectionPolicy` refuses two records that cite one Run History reference; `select_harness` counts distinct references toward `minimum_records`. Repeated trials of one subject with their own histories still count. | `one_history_reference_cannot_count_as_several_trials`, `distinct_repeated_trials_of_one_subject_still_count` |
| D4, D4b | `SpawnedTaskCheckpoint.from_dict` requires a stored SHA-256 digest and stored integer counters and text identities before any conversion; only in-process construction may leave the digest blank. | the extended `stale_version_tamper_and_invalid_state_fail_closed` case (five refusals) |
| D5 | `verifier_execute` starts the script in its own process group, kills the group after the deadline and after completion, keeps a bounded rolling output tail, and raises `VerifierError` with `output_tail`, `timed_out`, and `output_bytes_total`. The record is `verifier_execution/v2` and names its containment as a raw-host process group. | `verifier_timeout_terminates_descendants`, `verifier_timeout_error_carries_output_tail`, `verifier_output_capture_is_bounded` |
| D6 | `HarnessResponseEvaluation` carries `subject_contract_ref`, `subject_contract_digest`, and `context_aware` as `harness_response_evaluation/v2`; a two-parameter callback receives a `ResponseEvaluationContext` with the semantic call, input digest, and subject contract. | `evaluation_record_binds_the_subject_contract`, `context_aware_evaluator_receives_the_exact_occurrence` |
| D7 | `LoopDefinition.from_dict` raises only `LoopDefinitionError` and names unsorted cardinalities as the reason instead of a digest mismatch. | `stored_contract_faults_raise_only_definition_errors` |
| D9 | `InformationStorageBinding.from_storage_dict` requires a stored digest, an integer size, and list-typed collections. | `stored_binding_without_its_digest_is_refused` |
| Latent Practitioner branch | `adaptive_practitioner_records` treats the verdict codes as response repair work with the evaluation's finding codes, not as a transport failure. | covered by the gateway checks; no product path registers an evaluator yet |
| D8 | `tools/make_checkpoint.py` parses the JSON self-test summary from standard output and records a parse failure with the return code and output tails; keeps every command's return code, output, and launch error; refuses an existing target and an unconfined slug before any suite runs (exit code 2); writes `conformance.json` from the manifest produced during the run and refuses a stale one; lists untracked files. | `tools/test_make_checkpoint.py`, 20 tests |
| Legacy campaign tool | `tools/task_campaign.py` renames an existing cell directory instead of deleting it, bridges the `solution.py` named in the outcome's artifact list before falling back to the newest file and records which rule applied, verifies the health probe's certificate unless `--insecure-health-probe` is given, accepts every `model_gateway_result/` record version, and reports deferred cells separately from attempted ones. | `tools/test_task_campaign.py`, 22 tests |

The acceptance probe reports 11 of 11 scenarios passing after the fixes, and
the owning suites rerun at 31, 22, 42, 15, 8, 33, 19, and 10 checks passing
for selection, evaluation, fallback, semantic binding, verifier, information
access, definitions, and checkpoints. The two tool repairs pass 42 unit tests
together with the six existing `tools` tests (48 in the discover run).

## Repository alignment and merges on 2026-09-13

The owner then asked for the repository to be aligned, every branch merged
into `main`, and `main` pushed. The result is four commits on `main`:

| Commit | Content | Gates on that tree |
|---|---|---|
| `19001d1` | The fixes above, the previously untracked harness subsystem (46 core modules), the embodiment lab, the authored embodiment files, dated evidence summaries, the September 11 to 13 documents, and an extended `.gitignore` that keeps copied sibling repositories, embodiment runtimes, databases, archives, and run workspaces out of the history (390 files). Eight documentation links into git-ignored local trees were relinked or replaced; three small study summaries were copied into `artifacts/configuration-study-20260912-KRiBSo/`. | self-test 3,953 of 3,953; conformance all gates pass; repository conformance passed; embodiment lab 42 of 42; devtools self-test pass; qualification lab 3 of 3; tools tests 48 of 48 |
| `6aec2e2` | Merge of `origin/fork/reconciled`: Run History authorship and its check module, the reactive scheduler's transactional revisions, the archived 2026-09-07 review probes, allowlist entries with written reasons, and the reconciliation record. The admission module keeps both nesting-depth contracts (the branch's declared limit and main's discovered decoder limit). | self-test 3,974 of 3,974; conformance all gates pass; repository conformance passed; embodiment lab 42 of 42; tools 48 of 48 |
| `6bc1840` | `origin/fork/hardened-learning` recorded with the `ours` strategy: its ten commits were the fork's first pass, and the reconciled branch already chose one implementation per review item. | unchanged tree |
| `940065e` | Merge of `origin/overnight/opencode-step-instances`: composed OpenCode step instances, typed step state, the night budget, multi-path solving, the step and skill catalog, the overnight tools, and seven documents. Conflicting hunks in the five Practitioner modules that main rewrote took main's side; the auto-merge then dropped four definitions the branch's surviving hunks still used (an import in verification, the differential-verification operation, the artifact constraint block, and the `session_factory` seam on `ModelExecution`), which were restored by hand, and the eleven new modules were registered in the module map and the suite. The step-session self-test received its own JSON-only fixture because main's event parser no longer guesses a prose-wrapped object. The seven documents were brought to the CI language and structure rules (228 dash replacements, one retired term, fence languages, heading levels). | self-test 4,185 of 4,185; conformance all gates pass; repository conformance passed; embodiment lab 42 of 42; tools 48 of 48; devtools self-test pass; qualification lab 3 of 3; the twenty CI example scripts exit 0. On GitHub the self-test failed on every Python version because one step-session check assumed an installed `opencode` binary; the fix is in the follow-up cycle below. |
| `d833d9b`, `d77ec43` | `core.harness_layering`: the wrapper composition and native control ownership records from the layered harness proposal, the `allow_native_retry` permission on the fallback policy, and the wiring that stamps every harness attempt record with the declaration's digests and refuses a composition or native control that no executor implements. | self-test 4,208 of 4,208; conformance all gates pass; repository conformance passed; embodiment lab 42 of 42; harness fallback 49 of 49, semantic 15 of 15, layering 23 of 23 |
| `2f435a1` | The Codex session's `ASTRA.md` advisory note, the `CLAUDE.md` instruction files at the root and in `devtools/` and `embodiments/`, the layered harness proposal, and the pointers to them, committed as that session reported them complete with the CI language, structure, retired-term, and link checks passing locally. | documentation only |
| `0eeb5b1` | The hardcoding audit's allowlist can exclude one exact file that is not this project's source (`UPSTREAM_RECORD_COPY` or `GENERATED_EVIDENCE_RECORD`) with an owner, rationale, and expiry; the file is reported as skipped with its classification. The first entry is the copied release listing, whose 229 findings were the upstream project's own data. Measured on the export: exactly those findings disappear and no other finding id moves; the baseline is untouched and 484 new high findings remain visible. | devtools self-test pass (two new canaries) |
| `bd8f0e2`, `21c4930`, `c522f6c` | The audit's `--triage` worklist (499 findings for 236 owners, grouped by owner and classification, every decision undecided), then the first decided batches: the Practitioner command line derives the OpenCode step's credential variable from the provider specification instead of naming it by hand, thirteen environment-variable NAME reads in development tools are allowlisted with that reason, twenty reviewed address findings (provenance references, JSON Schema identifiers, documentation citations, loopback and scheme prefixes, the provider specification table) are allowlisted with their reasons, and a copied package-registry record is excluded by digest. Committed-tree count after these: 462 new high findings. Left undecided on purpose: a local Ollama endpoint in a development tool, the Tactical endpoint default in the campaign tool, the OpenAI client's duplicated endpoint constants, 326 closed-vocabulary strings, 94 deployment settings, and 38 prompt texts that belong in the prompt-resource system. | devtools self-test pass; tools 97 of 97 |
| `802f8a9` | `core.harness_layering_space`: the two layering dimensions become enumerable and indexable (control policies by mixed radix, compositions by lazy walk with the caller's depth and no invented ceiling, their product yielding validated bindings by index), so a configuration search can address them without materializing them. The map and manifest were rendered from the staged tree so the concurrent session's unstaged search work was not swept in. | self-test 4,350 of 4,350 on the staged tree; conformance all gates pass; 19 module checks |
| `d8caea2` | Two things under one message. This session's own change: the layering spaces rebuild from their records (three checks). Also carried, by mistake: the Codex session's wide-search work, which that session had staged in the shared index (the generation search space, search records, search adapters including the optional Optuna adapter and their checks, the wide-search controls in the embodiment laboratory, the run-path coverage test, the run-path and dimension coverage map and the Hyperlambda comparison in `docs/verification`, the `artifacts/wide-search-20260913-0U0br7` control results, and the related architecture, packaging, map, suite, and boundary-register updates). This session committed the whole index without checking its staged list first. The Codex session had reported that content passing 4,392 source checks and 4,357 clean-installation checks before the sweep, and the export of the head was re-verified afterwards; the commit message, not the content, is what is wrong, and the correction is recorded in the following empty commit. | see the following commit for the head verification |
| `27436da`, `c171e3d` | The overnight tool tests' git helper gained a 120 second bound after the tools discover run hung three times under load (every isolated rerun passed); the embodiment laboratory's frozen factor catalog gained the two layering dimensions (`wrapper_composition`: direct, instruction preparation then direct; `native_control`: owning Loop, supervised planning) with honest maturity labels, growing the Cartesian view from 51,840 to 207,360 configurations per task. | tools 97 of 97; embodiment lab 42 of 42 |
| `79765fa`, `bbae3dd` | Three contract concerns the Codex session reproduced in the layering records (ordered alternatives per failure kind under one decider, read-only validated data, NaN refused) and the adapter-declared native controls (`HarnessExecutionCapabilities.native_controls`) with construction-time refusals that keep "unsupported by this adapter" distinct from "not implemented yet". The manifest committed with `bbae3dd` recorded a failing scan because the fix cycle's in-progress files were on disk when it was regenerated; the next commit regenerates it. | harness fallback 52 of 52, semantic 15 of 15, layering 27 of 27, external harness 80 of 80 |

A read-only review of the merged overnight modules (probes under
`.loop-engine-dev/fable-review-probe-20260913/agent-review-overnight/` on the
owner's machine, rerunnable with the repository interpreter) found five high
findings: the workspace guard restores files through symlinks and outside
the workspace, the step prompt file is written through a pre-existing
symlink and keeps a pre-existing mode, the differential and metamorphic
oracles execute model-authored code on the host with the engine's working
directory and full environment (reachable by the model through the
`core.verify.differential` capability), cross-attempt scoring depends on
directory order, and unanimous failures or byte-identical copies are
promoted to acceptance. Seven medium and nine low findings accompany them,
with documentation claims the code did not honor (a dirty-tree refusal, kept
failed attempts, no fixed step timeouts, a guard rollback with no caller).
The fixes are the next cycle and are recorded in the commits that follow
this report.

Lessons that a later merge should apply: `forbidden_paths.json` on `main` is
compact single-line JSON, so a branch's change to it must be applied
semantically (load, change the key, dump in the same format), never by
textual merge; after any merge that favors one side for conflicting hunks,
run an undefined-name scan over every conflicted file, because the surviving
hunks of the other side may reference definitions the resolution dropped;
and the machine's temporary directory must sit outside the repository,
because the embodiment lab's reference preparer refuses a destination inside
the checkout and `/tmp` is quota-limited here.

CI on GitHub after `19001d1` and `6bc1840`: the documentation job (structure,
language, retired terms, local links, diagrams, showcase) passed for the
first time since the job was added, and the build job passed. The three
test jobs pass the self-test, the conformance gates, and the embodiment lab
and fail at the hardcoding delta gate, which was already red before this
session (3,641 new findings at `c259d86`). Measured on a clean export of
`19001d1` with the CI command: 713 new high or critical findings above the
2026-09-02 baseline, 343 of them in `src/loop_engine`, 229 in the copied
release record `embodiments/openinterpreter_rust/latest-release.json`, 51 in
research matrices under `docs/research`, 68 in `devtools`, and the one
critical finding an absolute home-directory path in
`devtools/embodiment_lab/systematic_catalog.py`, which now comes from the
environment. The entry page forbids refreshing that baseline to make the
gate pass; the repository's own route is a written-reason allowlist entry
per finding, or the abstraction the finding asks for. That triage is the
remaining required work for a green `main`.

After this session's usage limit ended the three fix groups mid-work, the
Codex session integrated their unfinished changes, verified them, and pushed
`2e0cf7b`; its record is
[the Astra integration review](ASTRA-INTEGRATION-REVIEW-2026-09-13.md). At
`2e0cf7b` the GitHub test jobs pass the self-test, the conformance gates,
the embodiment lab, and the tool checks on Python 3.10, 3.11, and 3.12 and
fail only at the hardcoding delta gate, which skips the later steps. Those
skipped steps were run on the owner's machine against `2e0cf7b` with the
workflow's commands and its pinned container image: the product solve
acceptance, the command-line acceptance, the README quickstart check, the
wheel build, a fresh installation with `pip check`, `doctor`, `setup`, the
installed Studio checks (19 of 19), and the installed-package command-line
acceptance all exit 0. The audit gate is therefore the only difference
between the hosted workflow and a green run.

Four evidence files stay untracked and unignored because they exceed the
size rule the alignment plan applied (a 700 KB hardcoding summary, a 2.4 MB
component inventory, a 550 KB temporary-directory check record, and a
250 KB diagnostics archive); a later decision can add or ignore them.

## Interfaces for the wider grid, for the Codex session

Added on 2026-09-13 after 14:00 local time, when the owner asked the Codex
session for more dimensions, a larger grid, every combination of routes and
harnesses, and awareness of which settings are available. The Codex session
answered that it would extend the existing model-route selector, the
reviewed-evidence harness selector, and the parameter resolver with a
versioned description of what each target can configure, a checked setter,
and a joint compatibility check. The following interfaces landed on `main`
the same afternoon and are meant to be consumed by that work rather than
duplicated by it.

| Interface | What it answers | Where |
|---|---|---|
| `layering_axes`, `layering_configuration_space` | The wrapper composition and native control policy of a harness as two `integer_range` axes of a `ConfigurationSpace`, bound to the layering space's digest; any proposal adapter addresses them with the other dimensions. | `generation.layering_axes` |
| `layering_binding`, `layering_fields` | Exact decoding of an address to its validated `LayeredHarnessBinding` and the inverse. | `generation.layering_axes` |
| `layering_exclusions`, `iter_admissible`, `refuse_inadmissible_proposals` | Admissibility under the run's outer fallback policy, per address, as a lazy walk, and as a separate filter record over one proposal batch. | `generation.layering_axes` |
| `classify_address`, `availability_summary`, `address_availability` | Which addresses execute today, which the outer policy refuses, and which are declarations without an executor (composition, undeclared control, declared control), with the reason the semantic binding raises. Counted without walking the compositions. | `core.harness_layering_availability`, `generation.layering_axes` |
| `load_layered_binding` | A host-authored layering declaration file read under the run's own outer policy. | `core.harness_configuration` |

Two facts matter for a joint compatibility check. First, the
availability projection is the semantic binding's own rule:
`HarnessSemanticBinding._refuse_undeclared_executor` calls
`executor_refusal`, so a setter that consults the projection refuses
exactly what invocation would refuse. Second, an adapter's declared native
controls come from `HarnessExecutionCapabilities.native_controls`, which
every registered adapter currently leaves empty; the projection therefore
reports every natively owned control as undeclared until an adapter
declares one, and every layered composition as lacking an executor. Both
are honest states, not defects. A capability description that wants to
say "this harness can own goal management natively" declares it there,
and the projection moves that policy from `adapter_does_not_declare` to
`declared_without_executor` until an executor exists.

### Review of the wide-search modules, and what was fixed

A read-only review agent probed `generation/space.py`, `search.py`,
`search_records.py`, `search_optuna.py`, and the embodiment laboratory's
wide-search control at `3907107` with executed probes (saved under
`.loop-engine-dev/fable-review-probe-20260913/agent-review-search/`).
It found the index arithmetic, laziness, shard partitioning, seeded
determinism, evidence refusals, record detachment, and authority boundary
sound, and thirteen defects, twelve of them fixed the same afternoon:

| Finding | Severity | Status |
|---|---|---|
| Exact-task identity keyed on the feature vector, so features attached later disconnected prior evidence and re-proposed observed addresses | high | fixed: `SearchTask.identity_digest` |
| One evaluation artifact counted as two trials under different ids | medium | fixed: `duplicate_evaluation_artifact` |
| Vector warm start spent its draws on the target task's own measurements | medium | fixed |
| The public entry point wrapped the typed refusal in a `LoopError` | medium | fixed |
| The aggregate gate hid the fifteen optimizer controls when Optuna is absent | medium | fixed: reported as not tested with the dependency named |
| The batch record did not carry seed, cursor, shard, batch size, draw limit | medium | fixed: `request` sub-record |
| The cursor is a bare integer, bound to neither space nor shard | medium | open; the batch now names the shard |
| The 120-Canvas control crashed mid-run without Optuna and wrote no summary | low | fixed: recorded status |
| No evaluator digest in the records | low | fixed: optional `evaluator_digest` |
| No typed readers for the search records | low | open |
| Dead or impossible conditional rules accepted silently | low | fixed: refused at construction |
| Empty-shard exhaustion inconsistent between adapters | low | fixed |
| Documentation claims partly unmet | low | fixed where behaviour changed |

### Hardcoding gate: a precision fault in the auditor, and what remains

The audit's triage worklist showed that of the 502 findings blocking the
delta gate at `5c062f1`, 109 were the key of a mapping read inside a
comparison (`decision.get("action") == "read"` reported `"action"`, not
`"read"`), 31 were `None` in an identity test, 17 were subscript indices,
and a few were empty-collection defaults. The auditor classed any literal
inside a comparison as the compared token and took its role from the
enclosing call name, so `decision.get(...)` made the key a "state
comparison". The literal context now records whether the literal is an
operand of the comparison, and both comparison classes require it.
Finding identities are unchanged and the baseline was not touched: the
misclassified findings drop to low, true vocabulary tokens keep their
class, and the new-high count against the frozen baseline fell from 502 to
335 in the shared working tree (318 on a clean export of the commit; the
difference is another session's uncommitted modules). The value compared
against a mapping read still
takes only the medium behaviour class, since no role word reaches it; that
asymmetry is known and left as is rather than raising hundreds of
existing medium findings to high in one change.

What remains needs decisions, not scanning: raw vocabulary tokens compared
directly (about 180, most in the Codex harness recipe and Practitioner
modules), environment values in confinement setups (about 85), prompt
texts (38), and four endpoint addresses.

The environment batch was decided the same afternoon. The sandbox's own
layout became the typed `ConfinedEnvironment` record in
`core.harness_confinement` (the auditor's proposed abstraction for it,
`typed_runtime_settings`), and seventy-nine findings in the harness
recipes, the laboratory, and the tools were allowlisted with written
reasons naming the variable and the confinement rule behind each: relay
placeholder credentials, the harnesses' own consent switches, workspace
locations, variable names read at the boundary, empty unset defaults, and
the verifier's minimal `PATH`. A `None` under an `environment` role is no
longer a deployment value. The committed tree's count fell from 318 to
225; what remains is the vocabulary tokens, the prompt texts, and the four
endpoint addresses.

The vocabulary batch followed. Where a closed vocabulary already had an
authority, the comparisons now name it: response evaluation statuses,
harness fallback decision reasons, harness run statuses, search
observation states, axis value kinds, evidence validity statuses,
generated-project command kinds and media types, and the stage-assistance
arms, whose tuple moved to the control manifest so the Practitioner
records, the lineage, the scope, and the solve runtime share one owner.
The auditor classes the versioned step-content record as the governed
prompt resource it is. The two OpenAI endpoints the client refuses to
deviate from, the laboratory's local Ollama address, the campaign tool's
health-probe default, Python's `mode` keyword name, and two record field
names carry written reasons. The committed tree's count fell from 225 to
140, a figure that now includes the configuration modules the Codex
session landed in `ccf5dce`. What remains is vocabulary in modules whose
authority does not exist yet (attempt statuses, terminal codes, event
types, run modes, laboratory serving modes), the fourteen prompts still
composed in code, and the new configuration modules' own vocabularies.

### The gate went green

Six batches on the afternoon of 2026-09-13 took the CI hardcoding delta
gate from 502 blocking findings to zero without touching the frozen
baseline. Two were precision faults in the auditor (a literal anywhere
inside a comparison counted as the compared token; a `None` under an
`environment` role counted as a deployment value), one was a missing
classification (the versioned step-content record and the frozen review
probes), and the rest were decisions: a typed confined environment for the
sandbox, closed vocabularies compared by name against the authorities
that already defined them (or new single owners where none existed), the
built-in OpenCode step prompts moved into the step-content record and the
verifier's prompts into the governed prompt module, and one hundred and
four written reasons for confinement values, endpoint contracts, external
format vocabularies, tool subcommands, and record field names. Every
batch was verified on a clean export of the staged index (self-test, all
27 conformance gates, repo conformance, devtools self-test) because the
shared working tree held the Codex session's uncommitted work.

## Addendum written while Codex evaluated the findings

Added on 2026-09-13 after 12:00 local time, while the live Codex session
was reading this report. It records corrections to the report, one
acceptance probe, and further findings from the legacy campaign tool.

### Corrections to this report

1. Probe safety. The first version of probe section D and of the verifier
   acceptance scenario matched and killed every `sleep 30` process on the
   machine. Codex pointed this out. Both probes now use a unique sleep
   duration and match it exactly, so only the probe's own descendants are
   touched. With that matching one descendant still survives the timeout, so
   D5 stands.
2. D3 fix refinement. Refusing repeated `subject_digest` values would also
   refuse legitimate repeated trials of the same subject, as Codex noted. The
   refined candidate fix deduplicates only `(history_ref, history_digest)`
   per harness. The acceptance probe carries a control that keeps two
   distinct trials on one subject counting.
3. Existing structures this report understated. Freshness:
   `ModelRouteAvailabilitySnapshot.is_fresh` and `usable` bind an observation
   time and an expiry time for route availability, and context classification
   carries freshness facets; what is missing is a source-age and contradiction
   policy for retrieved intelligence bodies. Pricing: `AstraPricingSpec` and
   `AstraCostExposure` bind a price source and a conservative maximum cost for
   the quarantined Astra route prototype, and the OpenRouter catalog carries
   prices; what is missing is a run-level cost authority for the providers
   the campaigns actually use, whose cost state remains unknown. Enumeration:
   `devtools/embodiment_lab/configuration_matrix.py` enumerates configuration
   cells for experiments; the product runtime has no equivalent. The proposal
   section should read "partly represented" for freshness and for cost, not
   "not represented". The three-way distinction Codex suggested, represented,
   connected to a workflow, and qualified in real use, is the right vocabulary
   for the next revision of the dimension table.

### Second correction round

Codex reproduced two stronger cases after the first addendum, and both are
confirmed by acceptance scenarios D1b and D3b:

1. An inconclusive evaluator verdict triggers the same gateway route
   failover as a rejection. In the direct path the second provider was
   called after an `inconclusive` verdict and the result was admitted with
   statuses `inconclusive` then `passed`. The recovery guide says an
   inconclusive evaluation stops recovery; inside the gateway it does not.
   D1 now covers rejection and inconclusive verdicts alike.
2. A duplicated successful trial changes the selected harness, not only the
   minimum-evidence gate. D3's severity is raised to high, and its body above
   is corrected.

### D9. The information binding reader has the same blank-digest bypass

- Location: `src/loop_engine/core/information_access.py`,
  `InformationStorageBinding.__post_init__` line 198
  (`if self.binding_digest and self.binding_digest != expected`) and
  `from_storage_dict` line 259, which passes the stored digest through as
  text. This is the reader documented for "a trusted binding store", the
  path the owner's centralized-storage design depends on. Today its only
  caller is a check, so the exposure is latent.
- Condition: a stored binding whose `binding_digest` is an empty string and
  whose `scope` was rewritten from `private_loop` to `public`.
- Expected: a binding read from storage must carry a digest that matches
  its body; scope, owner, authorized Loops, and required permissions are
  exactly the fields the digest exists to protect.
- Observed (probe `probe_binding_digest.py`): the tampered binding loaded
  with scope `public` and a fresh digest, and a resolver that attached it
  let an unrelated Loop materialize the private value. The same tampering
  with the original digest was refused. The value's own content digest still
  held, so integrity of the value is protected; access control is not.
- Regression check: `blank_binding_digest_is_refused_on_read`; acceptance
  scenario D9.
- Candidate fix: the same as D4. Require a 64-character digest in
  `from_storage_dict` and keep the blank digest only for in-process
  construction. The pattern `if self.<digest> and ...` should be searched
  for across every reader that accepts stored records.

### Third correction round

Codex's written assessment (12:17 UTC) confirmed D1, D3, D4, and D5 by
independent reproduction and raised four defects in this review's own
artifacts, all accepted:

1. The acceptance script printed failures and exited successfully. It now
   exits with status 1 whenever any scenario fails.
2. The checkpoint scenario combined two defects. It is split: D4 covers the
   blank digest, and a new D4b shows that a counter of `2.9` loads as `2`
   even when the digest is correct for the coerced body, because
   `from_dict` coerces before `__post_init__` verifies. `LoopDefinition.from_dict`
   does the opposite, hashing the raw body first, which is the right order.
3. The evaluator scenario compared a digest length. It now compares the
   exact `response_contract_digest` value.
4. Matching a descendant by a fixed sleep duration is not ownership, and
   concurrent probes could share the value. Both probes now record the
   descendant's PID from the script, confirm its command line under `/proc`,
   and kill only that PID.

Codex also corrected a fact in this report: the 2026-09-12 diagnostic
evidence is six runs on one task, not six tasks. The ten-questions table is
corrected. Its design guidance is also adopted here: fixes should add an
explicit permission for evaluator-triggered route changes rather than remove
route failover, keep legitimate repeated trials counting, and extend the
existing typed variation dimensions and conditional enumeration rather than
rebuild them.

### Acceptance probe

`artifacts/fable-review-20260913-p75Wml/probes/expected_after_fix.py` encodes
the expected post-fix behavior for D1 to D6 and D9 plus two controls and the
stronger cases. Against the reviewed tree it reports 1 of 11 scenarios
passing (the control) and exits with status 1; the recorded output is
`acceptance-baseline.txt` beside it. A candidate fix for one defect is
verified when its scenario passes and no other scenario regresses; the gate
is green only when every scenario passes. Run it with the same environment
as the other probes.

### Further findings in the legacy campaign tool

The handoff asked for an attempt-retention and evaluator-leakage review of
the legacy task campaign tooling. These findings about
`tools/task_campaign.py` come from inspection; the tool was not run.

- Attempt retention. `stage_cell` removes the whole cell directory before
  staging, so rerunning a cell destroys the previous attempt's workspace,
  solver output, and cell record on disk, while `write_report` still merges
  the previous cell record from `report.json`. A report can therefore cite an
  attempt whose artifacts no longer exist. `bridge_artifacts` copies the
  newest `attempt-*/solution.py` by modification time rather than the attempt
  the engine accepted, so a later failed attempt can be the one the gate
  scores.
- Evaluator leakage. Each task's `gate.sh` is both the campaign's final
  evaluator and the solver's mid-run verifier (`--verifier gate.sh`), so the
  model receives the holdout metric and floor in the verifier's output tail on
  every check. A gate pass reported by this tool is a result tuned against
  its own evaluator, not an independent held-out result. The evaluation
  contract appended to `task.txt` also tells the model how the gate calls
  `predict(row)`.
- Credential exposure. `endpoint_healthy` sends the campaign API key as a
  bearer token with TLS verification disabled (`check_hostname` off and
  `CERT_NONE`), which the engine's own per-endpoint TLS policy does not
  permit.
- Accounting. `_scan_outcome` counts physical calls only from
  `model_gateway_result/v1` records, so results that carry evaluations
  (`model_gateway_result/v2`) are missed by the crash-path fallback, and
  deferred cells count as attempted in the report.

### Latent branch gap in the adaptive Practitioner

`core/adaptive_practitioner_records.py` (lines 2517 to 2535) handles
`output_validation_failed` as a response repair and every other code as a
transport failure. Since `solution_model_port.py` now relabels evaluator
outcomes as `semantic_response_rejected` and
`response_evaluation_inconclusive`, a registered evaluator's rejection would
be published as `model.step.transport_failed`. No product path registers an
evaluator today, so this is latent; it becomes live the moment one is wired
in.
