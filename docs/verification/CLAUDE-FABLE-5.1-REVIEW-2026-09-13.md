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
| 10. Mechanism tests versus live quality | Every count in the handoff is an offline mechanism count. No live call qualified selection or semantic recovery. Continued alternative-output production, portable Solution graph replay, and cross-task learning remain unestablished; the last live diagnostic runs on 2026-09-12 solved zero of six tasks. |

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

### Acceptance probe

`artifacts/fable-review-20260913-p75Wml/probes/expected_after_fix.py` encodes
the expected post-fix behavior for D1 to D6 plus two controls and the two
stronger cases. Against the reviewed tree it reports 1 of 9 scenarios passing
(the control); the recorded output is `acceptance-baseline.txt` beside it. A
candidate fix for one defect is verified when its scenario passes and no
other scenario regresses. Run it with the same environment as the other
probes.

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
