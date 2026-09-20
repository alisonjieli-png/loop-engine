# Capability patch mutation verification

Completed 2026-09-19 at 16:55 UTC on the uncommitted `main` tree based on
`48cc954322691e492aad69a465ba470a112730e7`.

Result: 14 of 14 known-wrong mutants were killed by named owning regression
checks. There were zero mutation setup failures and zero surviving mutants.
The unmodified and restored suites both passed 55 of 55 checks: capability
directory 39/39 and capability Loops 16/16. Runtime source hashes were identical
before and after the experiment.

The reproducible runner is [capability-mutation-controls.py](capability-mutation-controls.py).
The complete machine-readable evidence is
[capability-mutation-controls-results.json](capability-mutation-controls-results.json).
The review consulted the earlier
[independent recheck](capability-independent-recheck.py). The runner uses
separate focused local probes to establish each mutant's actual bad behavior.

## Exact method

Run from `/home/username/loop-engine`:

```bash
.venv/bin/python artifacts/architecture-audit-2026-09-19/capability-mutation-controls.py
```

Each case requires exactly one matching source fragment in the chosen
function. The runner compiles the changed function in memory, installs it only
inside its owned process, and restores it before the next case. For the default
directory function, it also changes the owning check module's imported alias so
the regression actually exercises the mutant.

A mutant is counted as killed only when both conditions hold:

- An independent local probe observes its intended known-wrong behavior.
- An explicitly named existing owning regression reports `passed=false`.

Failure to find or compile the mutation is a setup failure, not a kill. An
unexplained exception without the named failing regression is inconclusive,
not a kill. The report retains exact original/replacement fragments, expected
test names, mutation-function hashes, probe observations, suite counts,
exceptions, and failing records.

## Controls and outcomes

| Removed behavior | Observed known-wrong behavior | Decisive regression |
| --- | --- | --- |
| Negotiation supported-version guard | Unknown version negotiates successfully. | `unknown_protocol_version_refuses_negotiation_and_dispatch` |
| Dispatch supported-version guard | Unknown-version endpoint executes. | `unknown_protocol_version_refuses_negotiation_and_dispatch` |
| Handshake sequence copying | Caller appends `writes_fs` to already constructed authority fields. | `handshake_copies_caller_owned_sequences` |
| Invocation-policy version sequence copying | Caller extends an existing supported-version list. | `explicit_supported_version_is_required_and_immutable` |
| Scalar text validation | Mutable `privacy_class=[]` is accepted. | `all_scalar_handshake_fields_refuse_mutable_or_unbounded_values` |
| Finite timeout validation | A non-finite timeout is accepted. | `all_scalar_handshake_fields_refuse_mutable_or_unbounded_values` |
| Replacement endpoint cleanup | Old undeclared endpoint remains registered. | `replacement_removes_old_endpoints_and_fallbacks` |
| Replacement fallback cleanup | Old fallback remains registered. | `replacement_removes_old_endpoints_and_fallbacks` |
| Dispatch handshake-digest pin | Changed declaration executes under a previously selected digest. | `handshake_drift_refuses_before_any_endpoint_or_fallback` |
| Dispatch callable pin | An alternate implementation executes instead of the selected callable. | `callable_swap_refuses_before_any_endpoint_or_fallback` |
| One local callable lookup | A changing endpoint descriptor substitutes a second callable after binding. | `directory_binds_the_callable_locally_only_once` |
| Missing model executor as unavailable | The absent model path reports success. | `an_absent_model_executor_is_unavailable_not_a_canned_success` |
| Governed policy forwarding | A failed primary automatically executes its alternate. | `canonical_capability_loop_forwards_pinned_no_fallback_policy` |
| Governed explicit automatic-fallback refusal | A caller's automatic-fallback policy is accepted inside a single governed attempt. | `a_single_attempt_refuses_automatic_fallback_authority` |

## Failed attempts and accounting

All 14 setups succeeded on their first saved attempt. No setup failure was
discarded or counted as a kill.

The handshake-sequence-copy mutant first recorded the explicit failed copying
check, then the owning directory suite stopped with
`ValueError: pure excludes every other effect` when later registration
revalidated the mutated object. A trace hook retained the already evaluated
failing record. This case counts as killed because the independent probe
observed the changed effects and the intended named regression returned false,
not because the suite later raised. Its incomplete mutant-suite execution is
preserved in the machine-readable evidence.

Some mutants produce secondary failures after a shared test fixture's call
list has changed. Those are not claimed as independent additional defects.
Each kill uses the intended named regression and its separate bad-behavior
probe. The baseline and final restored suite are both complete and passing.

## Source identity

```text
5818da8f86bd4ee4336bd4a350b1e357e213f95bb9ea4dbf0cef1568b4c8b960  src/loop_engine/core/capability_directory.py
2e8c66a9cb70b34498e233455b6e5a059258155e32d82ab3c5ccf0321a5398db  src/loop_engine/core/capability_directory_checks.py
051f8f4b89972f4a22c99fa729c8d908568c4baa87275fa0e926f6702b2dcdd5  src/loop_engine/core/capability_invocation.py
9b585f824bee84d9908392dae561b4e7170dedfa16ffd7f1ce562a729ea9d670  src/loop_engine/loop/capability_loops.py
8522da37cbb1b56c4e0dcbcd98d5cb5a3bfeb8911db2fbad9d202ee83770fa8b  artifacts/architecture-audit-2026-09-19/capability-independent-recheck.py
680a4cd1b540cbf7610ab91d34db0fdf78013f02950c917b1ce3abe72dd2e102  artifacts/architecture-audit-2026-09-19/capability-mutation-controls.py
a3f98b0faf65cb8a8a918d55a58cc53cbeafa74556847be4583779d2f2a102de  artifacts/architecture-audit-2026-09-19/capability-mutation-controls-results.json
```

Only this report, the artifact runner, and its results were written. No runtime
source, map, provider configuration, existing evidence, or shared launch record
was edited. The endpoint probes only append local trace values. No provider
call, network operation, endpoint filesystem effect, deployment, or payment
occurred. These checks establish local regression discrimination, not provider
quality, multi-process race freedom, sandboxing, or full release qualification.
