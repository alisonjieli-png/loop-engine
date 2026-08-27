# Typed reuse-resolution report

## Verdict

`VERIFIED WORKING` for the scoped Solution-prior resolution slice.

This result does not complete universal parameterization, file-by-file
alignment, work-approach instrumentation, or Recursive Strategy Learning.

## Implemented path

```text
TaskFingerprintRequest
└── TaskFingerprint
    ├── current structured identity and digest
    ├── exact isolated reader for the pre-v1 five-field value
    └── CompatibilityAssessment
        ├── hard matches
        ├── hard failures
        ├── soft differences
        └── unknown dimensions

SolutionLibrary
└── ResolutionCandidate records
    └── ResolutionRequest
        └── Practitioner Loop
            └── ResolutionDecision
```

The implementation adds no runtime, role, graph authority, history authority,
or task-specific resolver subclass.

## Architecture-fit mapping

| Required semantics | Existing owner | Decision |
|---|---|---|
| Structured task identity | Solution Library fingerprint helper | Replace the delimiter-built value with `TaskFingerprintRequest` and `TaskFingerprint`; retain one exact legacy reader. |
| Compatibility evidence | Solution Library family filter | Extend into `CompatibilityAssessment`; text search remains candidate discovery only. |
| Resolver origin and selection | No complete typed owner | Add passive `ResolutionCandidate`, `ResolutionRequest`, and `ResolutionDecision`; execute selection through `Loop`. |
| Source lifecycle | Asset and intelligence owners | Preserve each native lifecycle; project only resolution eligibility. |
| Human authority | Existing approval and permission contracts | Keep orthogonal to `ResolutionOrigin`; add no human-resolution origin. |
| Delegated assignment | `DelegationSpec` and `LoopStartRequest` | Add no competing `DelegationEnvelope` in this batch. |
| Missing-value handling | `TaskTemplate`, `TemplateBinding`, and `WorkItemIR` | Extend with `RequirementPolicy` and `RequirementDisposition`; add no dataset-specific runtime or selector class. |
| Approach suitability and RSL | Work-approach checkpoint | Leave unimplemented until matched experiment and independent-review gates exist. |

## Contract decisions

- `TaskFingerprint` stores structured task facts and computes a canonical
  SHA-256 digest. Search text is only a projection.
- A required hard contract that is missing from a candidate fails closed.
- `ResolutionOrigin` is independent of Loop role, run mode, scheduling,
  placement, model thinking power, and human authority.
- `ResolutionEligibility` is a resolution projection. It does not replace the
  source object's lifecycle protocol.
- Candidate-only derived work cannot become executable reuse.
- Hard compatibility, eligibility, cost, latency, quality, and verification
  gates run before soft origin preferences.
- The deterministic selection operation executes through `Loop` and makes
  zero model calls.

## Flagship orientation behavior

The modeling request deliberately leaves the dataset and target unspecified.
Its registered template permits delegated choice only when the wording contains
an approved cue. The compiler records:

```text
dataset_source
├── state: delegated_choice
└── constraints: public, known license, permitted access, tabular, documented target

target_column
├── state: delegated_choice
├── depends on: dataset_source
└── constraints: documented, non-identifier, supported prediction operator
```

The compile step makes zero model calls and does not invent either value. A
request without a permitted cue receives `needs_clarification`. Future Orient
work must discover candidates through governed capabilities, apply the recorded
constraints, and create a typed resolution decision. If no candidate passes,
the Loop asks or abstains.

`InteractionMode.AUTONOMOUS` permits the same registered choice without a
wording cue. An optional `TaskFeedback` slot can supply a preferred dataset or
target. If a required value has no safe delegation policy, autonomous mode
returns `abstain_required`; it does not wait or fabricate an answer.

## Compatibility

Current Solution records emit a `task_fingerprint/v1` mapping. The isolated
reader accepts the former value only when it contains exactly five non-empty
pipe-separated fields with a registered scale band. Malformed values fail.
Current code never emits the old form.

## Proof

| Check | Result |
|---|---:|
| Task-fingerprint focused checks | 5 / 5 |
| Resolution focused checks | 6 / 6 |
| Solution-library integration checks | 5 / 5 |
| Template-model checks | 8 / 8 |
| Template-library checks | 5 / 5 |
| Task-compiler checks | 14 / 14 |
| Five text-task example | 5 tasks, 0 model calls |
| Semantic dictionary checks | 4 / 4 |
| Solve interaction checks | 4 / 4 |
| Complete source self-test | 1,361 / 1,361 |
| Conformance gates | 28 / 28 |
| New-file parameter-boundary findings | 0 |
| Repository parameter findings after this batch | 174 |

## Package proof

The source-controlled artifacts build and pass Twine metadata validation.

```text
08e561696daa8d9daebc49075d7d11e18bfadbf8cbf4795192faea18067e977b  loop_engine-0.1.0-py3-none-any.whl
63a8c4e068e51ff3fd05deb1e6f5e8c199bf825ad6f7ab4754fad2b479553c09  loop_engine-0.1.0.tar.gz
```

A fresh Python 3.10.20 environment installed the wheel and all declared
dependencies outside the source tree. The installed package passed 1,360 of
1,360 self-tests, 28 of 28 conformance gates, and `loop-engine doctor`.
Installed CLI proofs also covered autonomous compilation, optional dataset
feedback, and autonomous solve. The solve did not ask a question; it returned
`EXECUTOR_UNAVAILABLE` because the modeling executor remains unavailable.
The installed test count is one lower than the source count because one
repository-only check is unavailable outside a checkout.

## Remaining work

The next batch should adapt these producers into the same
`ResolutionCandidate` contract:

1. Capability Directory exact and parameterized capabilities.
2. `ProcedureDefinition` and `ProcedureStepSpec` records.
3. Solution Canvas composition candidates.
4. Analogy assessments and external-discovery results.
5. Novel-design candidates produced by the Practitioner procedure.

The adapters must preserve each source lifecycle, permission boundary, and
verification requirement. They must not create one universal status or bypass
`LoopGraphDefinition`.
