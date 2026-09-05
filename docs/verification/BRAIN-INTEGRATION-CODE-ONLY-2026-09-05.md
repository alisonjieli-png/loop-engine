# Code-only delivery and external caller repairs

The reported duration-parser failure was reproduced from the saved run and
its unchanged 467-byte task file. The immediate blocker was a project contract
that required command-produced files even when the requested deliverables were
source code and tests. Five admitted candidate previews had
`expected_artifacts: []` and a real `python -m unittest` verification command.
The constructor rejected them before source generation.

The [evidence export](../evidence/brain-integration-verification-2026-09-05.json)
records exact commands, hashes, run identities, accounting, and scope limits.
The [frozen generated files and independent oracle](../evidence/brain-integration-20260905/README.md)
are published as reproducible evidence fixtures, not built-in solver logic.

After the contract correction, the unchanged task reached
`COMPLETED_VERIFIED` in one pass with eight real model calls. Docker executed
25 unit tests and the public result returned both authored Python files.
Independent tests then found two malformed-string cases the generated tests
missed. The resulting model-authored repair was recovered from exact
checkpoints and passed 179 independent checks and 34 unit tests. That recovery
was operator-assisted, not proof of an autonomous cross-run resume service.
A subsequent normal public repair run, using the same broken source and the
same independent feedback, also passed all 179 checks and 34 unit tests without
manual source edits or checkpoint rebinding.

The smaller reported seconds-conversion task also completed in one pass with
eight real calls. It passed its three unit tests and 24 independent formula
checks. No task name, duration grammar, or industry route was added to the
runtime.

## Verified causes

| Boundary | Observed defect | Correction |
|---|---|---|
| Project shape | Empty command-produced outputs made a valid code-only task incomplete. Later attempts invented scripts to write the requested scripts. | Authored source files are deliverables. An empty `expected_artifacts` list is valid when an actual zero-exit verification command is required. |
| Candidate parsing | Non-object array members were discarded and values were coerced before validation. The resulting error hid which field was wrong. | Validate each field and array position first. Refuse wrong types with content-free field/index diagnostics. |
| Instruction intake | `--file` read the text, then exposed its origin as an uninspected external data reference. | `CapturedInstructionProvenance` binds the already-captured text, digest, and origin. External data references and permissions remain separate. |
| Source/output collision | A repair could author a file at the path reserved for a supplied input and fail after partial materialization. | Refuse equal or overlapping input/output paths before writes and return a distinct-output-path repair hint. |
| Failed attempts | Only returned executor results entered the attempt list. An exception caused every retry to reuse `attempt-1`. | Record each started execution, including failures and cancellation. A retry receives a new directory. Failed records cannot be accepted as verified results. |
| Workspace inspection | The reader used `services.workspace`, which the production service object does not have. | Read through the actual confined `workspace_base`, including preserved partial attempts, while refusing path and symlink escapes. |
| Cancellation accounting | The public adapter converted unknown calls to zero. A saved cancellation had 44 known completed calls. | `solve_outcome/v5` preserves a nullable total, known subtotal, and accounting-completeness flag. Legacy v3/v4 records remain readable without rewriting them. |

Per-file generation already existed before this work. The observed incomplete
candidate errors do not establish JSON string escaping as their cause. File
bodies still use the existing per-file response contract; streaming file-body
emission and automatic decomposition of oversized files are not implemented by
this change.

Ollama's official documentation says Cloud does not support structured outputs.
The Cloud route no longer advertises provider-enforced schema output. Prompted
JSON and local validation remain available. Adding an unsupported `format`
field would not establish constrained decoding. See
[Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs),
checked on 2026-09-05.

The older duration run also records an output-limit failure at an 8,192-token
requested allocation, not at the default 65,536-token capacity. Its history
retains that failure separately from the empty-artifact contract failures.

## Live evidence

All reported live calls used the exact
`ollama_cloud / cloud.default / deepseek-v4-flash:0731` route. The new launches
had no call-count, pass-count, total-token, or monetary ceiling. Provider
capacity, effect permissions, and sandbox limits remained enforced.

| Run | Result | Physical calls | Seconds | Independent evidence |
|---|---|---:|---:|---|
| Historical duration task `adaptive-21f1ccc9c72f0acd9b703bb8` | `NO_PROGRESS`; no project executed | 25 | 462.539 | Saved chain intact; five incomplete code-only candidate previews. |
| Corrected intake/contract, `adaptive-b78daa66cada87357dd9c741` | Two authored source files; 25 unit tests passed | 8 | 131.226 | 170/179 checks; two newline cases and seven non-string exception cases required follow-up. |
| Smaller task, `adaptive-12e6c7d1970cdfdd1aafd91d` | Two authored source files; three unit tests passed | 8 | 66.026 | 24/24 independent formula checks. |
| Feedback repair, `adaptive-dadfc5e6b5b24bf8eb61f7d0` | Operator-cancelled at a demonstrated infrastructure dead end | Unknown, with 44 known completed calls | 849.057 | Saved history and generated-file checkpoints preserved; the interrupted call has incomplete accounting. |
| Exact checkpoint execution, `duration-checkpoint-execution` | Saved model-authored files executed without editing their bodies | 0 new model calls | Recorded in execution history | 179/179 independent checks; 34/34 unit tests. Operator-assisted continuation. |
| Normal public repair after infrastructure fixes, `adaptive-51141ecb49499529308e8197` | `COMPLETED_VERIFIED`, v5 result, two repaired source files | 15 | 218.547 | 179/179 unchanged independent checks; 34/34 unit tests. No manual source edits. |

The checkpoint continuation recovered the exact candidate from its saved packet,
matched each file's checkpoint key and contract digest, verified the stored
content digest, and used the existing generated-project executor in a fresh
Docker workspace. It did not ask another model to regenerate the files.

The independent duration oracle covers integer Y/M/D/H/M/S unit forms, the
three user examples, zero and large values, 128 generated arithmetic
compositions, malformed strings, and predictable non-string refusal. Weeks,
fractions, signed durations, and complete ISO-8601 conformance remain outside
the demonstrated scope. Non-string handling was clarified by explicit repair
feedback; the original function's annotation accepted strings.

These runs are diagnostic cases, not unseen holdouts or a controlled estimate of
average performance improvement. No Kaggle dataset was downloaded or submitted.
No Kaggle score or 100-task completion is claimed.

## Caller contract

Use `solve_task(SolveRequest(...))` or `loop-engine solve --format json` as the
product entry point. Keep progress on its separate channel and inspect the
terminal result and artifact records. A source file returned with
`artifact_origin: authored_source` is not a command-produced dataset or score.
Keep the consuming project's independent test and approval gates.

New public results use `solve_outcome/v5`. Consumers must handle:

```json
{
  "model_calls": null,
  "model_call_accounting_complete": false,
  "model_calls_known_subtotal": 44
}
```

This means the exact total is unknown and 44 calls are accounted for. It does
not mean zero spending. Existing v3/v4 saved results remain readable. No
new v5 result replaces missing usage or cost with zero. The historical v4
cancellation that incorrectly reported zero remains unchanged as evidence of
the defect.

Call and pass limits should come from the user or an explicit authorized
policy. The earlier agent-imposed 50-call guard was withdrawn. The framework's
existing `None` defaults are retained; this work adds no replacement ceiling.

## Verification and remaining work

The first code-only checkpoint passed 2,867 source tests, 2,822 clean-base-wheel
tests, and 27 conformance checks in each environment. All 475 runtime bodies
matched the source, wheel, sdist, and clean installation. The later
attempt-tracking and v5-accounting changes have a separate final verification
record; the earlier counts do not qualify later source bytes.

Final verification passed 2,894/2,894 source tests, 2,849/2,849 applicable
clean-base-wheel tests, and 27/27 conformance checks in each environment. Build,
offline installation, dependency checks, CLI help, and all 475 runtime-body
comparisons passed. The base wheel explicitly omitted seven optional adapter
families. The offline checks made no provider calls.

The first final-check attempt found two fixture defects: a test bypassed the
owning history boundary, and a fixture label used a retired term. Both were
corrected without changing production logic, and the initial failures remain
in the evidence. Those test-only file edits occurred during the final live
repair, so full-checkout byte freezing is not claimed for that live run.
The final package checks use the corrected frozen source snapshot.

The separate CI hardcoding audit remains unresolved. Its findings were not
hidden by replacing the baseline or widening the allowlist. Broader harness
integration, native structured-output wiring for supported providers,
automatic checkpoint resumption, and universal task quality remain unproven.
