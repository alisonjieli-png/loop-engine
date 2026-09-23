# Native review calibration, September 23, 2026

Status: implemented and verified offline in the existing review worker.
No provider call, real approval, publication or deployment occurred.
The five fixture packages contribute zero new library supply.

## Frozen controls

The [versioned calibration set](../../tools/candidate_review/resources/native-calibration/calibration-set.json)
pins the entire candidate inventory and each canonical package digest. It
adapts the independently tested scheduling package from the contract-v2 cohort.
The original cohort remains unchanged.

| Neutral identity | Expected decision | Discriminating fact |
| --- | --- | --- |
| `control_71af` | approve | Correct earliest-time schedule; the example waits for all prerequisites. |
| `control_c902` | reject | Takes the earliest predecessor finish instead of the latest. A three-task input distinguishes duration 5 from the required 6. |
| `control_38d4` | reject | The tool accepts duration 101 and emits it correctly, while the mutated successful-output schema caps duration at 100. |
| `control_9bb0` | reject | An indirect callback writes a private note, despite no declared file-write effect. |
| `control_e137` | reject | Claims a scheduling method exists on the cited `CataloguePackage` class; the exact source contains no such method. |

All five pass the static native prechecks. This is deliberate: they measure
semantic review rather than whether a model repeats a deterministic refusal.
The trusted label verifier ran the scripts only inside the existing Bubblewrap
environment with no network or host home. The effect control wrote only in
that temporary namespace; a trusted runner observed the file there. The source
claim was checked against the exact cited source syntax tree. The
[observations](../../artifacts/native-review-calibration-2026-09-23/control-label-verification.json)
bind every result to the whole package digest.

## Reused contracts and new versions

`NativeCalibrationSet` reads `candidate_native_review_calibration_set/v1` and
produces the existing calibration-item/request pairs. It sends ordinary exact
native requests through the existing ReviewPanel and reviewer engines. The
existing evaluator and its exclusion rule are reused. There is no new
approval store or review runtime.

Native control records use `candidate_native_review_calibration_item/v1` and
include the exact package digest. Export validation binds every native control
call to its typed subject and digest. A candidate decision from a reviewer
excluded by calibration is refused by the export reader as well as the panel.
The worker's existing version-two ledger preserves invalid answers, observed
model identity, unknown usage and call budgets. The hosted approval source
format does not change.

Ground-truth decisions and defect explanations stay in the calibration set
and evaluation record. They are absent from reviewer prompts and candidate
item metadata. The reviewer receives the complete ordinary package tree,
source evidence and written criteria. Unsupported set versions, changed
inventory or package digests, and starter/native format confusion are refused
before provider discovery or review.

## Continuing the bounded pilot

Use the existing command with a new ledger and record path:

```bash
PYTHONPATH=src:tools python tools/review_catalogue_candidates.py \
  --content-profile native-original --calibrate \
  --catalogue artifacts/PREPARED_NATIVE_BATCH --repository . \
  --ledger artifacts/NATIVE_REVIEW_RUN/ledger.jsonl \
  --count 12 --seed FIRST_NATIVE_SAMPLE \
  --call-ceiling 0 --token-ceiling 0 \
  --record artifacts/NATIVE_REVIEW_RUN/review.json \
  --recorded-at 2026-09-23
```

The zero ceilings above perform no model work. The integrating session chooses
explicit ceilings and the existing model-call authorization flag for a real
pilot. Calibration spends from the same total allowance before candidate
review. An explicit alternative calibration file must use the native set
contract. The default native path never falls back to the starter set.

The five controls are a small diagnostic population. They do not establish
a false-approval rate, independence between model errors, or broad production
risk bounds. A reviewer that rejects everything may record no false approvals
and a false refusal; that observation remains visible. The campaign must still
inspect quality and throughput before scaling.

## Offline checks

The [evidence directory](../../artifacts/native-review-calibration-2026-09-23/README.md)
preserves the initial missing-module attempt and subsequent runs. Tests cover
complete package binding, hidden labels, static eligibility, false approval
exclusion, benign false refusals, invalid responses, unknown usage, actual
next-phase exclusion, native command selection and persisted control digests.
Every positive approval in these tests is explicitly a fixture result and
cannot be exported as a real reviewer decision.

Independent engineering review of this worker change and its curated labels
remains a gate for the integrating session before a real provider pilot. The
roadmap remains the task authority; this artifact adds no second task list.
