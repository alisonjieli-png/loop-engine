# Factory report 2026-09-26

## Stage minutes per slot

| Slot | export | prechecks | calibrate | review | write | combine | bundle | publish | check | counts | Wall | Reviewer busy | Utilization | Approved |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-09-26 | 0.0 | 13.43 | 1.97 | 63.52 | 11.2 | 0.08 | 0.08 | unknown | unknown | 5.98 | 96.27 | 53.3 | 0.554 | 1647 |
| 2026-09-26-04 | 0.37 | 16.92 | 2.63 | 66.58 | 13.12 | 0.12 | 0.1 | 2.85 | 0.02 | 0.0 | 102.7 | 54.4 | 0.529 | 1536 |
| 2026-09-26-10 | 0.38 | 15.4 | 0.82 | 64.2 | 14.22 | 0.18 | 0.18 | 3.13 | 0.03 | 0.0 | 98.55 | 52.4 | 0.531 | 1586 |
| 2026-09-26-16 | 12.32 | unknown | unknown | unknown | unknown | unknown | unknown | unknown | unknown | unknown | 12.32 | 0.0 | 0.0 | unfinished: prechecks failed: raise CandidateReviewError(code, message)  |

## Review lane

| Measure | Value |
|---|---|
| reviewer | tactical.gemma-4-coding-abliterated |
| items per busy hour | 1873.4 |
| approved per busy hour | 1787.9 |
| seconds per item | 1.922 |
| mean call seconds | 22.6 |
| mean busy minutes per slot | 53.3 |
| utilization of cadence | 0.148 |
| utilization of slot wall | 0.538 |

## Cost per admitted package

| Measure | Value |
|---|---|
| stage seconds per approved | {"bundle": 0.004, "calibrate": 0.068, "check": 0.0, "combine": 0.004, "counts": 0.075, "export": 0.008, "prechecks": 0.574, "publish": 0.113, "review": 2.446, "write": 0.483} |
| reviewer seconds per approved | 2.01 |
| charged tokens per approved | 6533.8 |
| wall minutes per approved | 0.062 |
| infrastructure usd per approved at current rate | 0.00026 |
| model cost usd | unmetered |

## Waste

| Measure | Value |
|---|---|
| slots in journals | 4 |
| unanswered review calls | 4 |
| unanswered review seconds | 10.5 |
| items left without a verdict | 104 |
| calibration retries | 1 |
| calibration not qualified verdicts | 2 |
| calibration attempts moved aside | 1 |
| moved aside calibration seconds | 35.4 |
| failed stage notes | 5 |
| slots that needed a restart | 3 |
| late start minutes | 21.43 |
| unfinished slots | ["2026-09-26-16"] |
| approvals lost with them | 0 |
| review startup minutes per slot | 12.1 |

## Stock

| Measure | Value |
|---|---|
| stored candidates | 58787 |
| exported so far | 10000 |
| exports drawn | 5 |
| not reviewable | 991 |
| eligible remaining | 47796 |
| held by repository ceiling in last export | 13626 |
| full exports the policy supports (2000 at 15 per repository) | 18 (36000 candidates) |
| draw of the export after them | 1791 |
| drawable within 80 exports | 45568 |

## Generation lanes of /home/username/loop-engine/.loop-engine-dev/overnight-2026-09-24/batch

| Lane | Candidates | Per active hour | Mean attempt seconds | Beside a review | Alone | Retries | Outcomes |
|---|---|---|---|---|---|---|---|
| lane-ollama-gpt-oss-20b | 133 | 7.0 | 96.3 | None (0) | 96.3 (175) | 150 | {"candidate_written": 133, "failed_candidate_shape": 3, "failed_provider": 39} |
| lane-ollama-gemma4-31b | 135 | 8.4 | 36.7 | None (0) | 36.7 (148) | 35 | {"candidate_written": 135, "failed_candidate_shape": 1, "failed_provider": 12} |
| lane-ollama-glm-53-flash | 135 | 15.0 | 57.4 | None (0) | 57.4 (140) | 13 | {"candidate_written": 135, "failed_provider": 5} |
| lane-tactical-gemma4 | 8495 | 236.0 | 6.2 | 23.0 (286) | 5.7 (9373) | 4974 | {"candidate_written": 8495, "failed_candidate_shape": 1020, "failed_provider": 5} |
| lane-ollama-nemotron-30b | 3 | 0.5 | 212.8 | None (0) | 212.8 (9) | 16 | {"candidate_written": 3, "failed_candidate_shape": 1, "failed_provider": 5} |
| lane-ollama-kimi-k3 | 3 | 0.5 | 242.9 | None (0) | 242.9 (8) | 12 | {"candidate_written": 3, "failed_provider": 5} |

## Storage

12479 bytes a package in the newest bundle (6398 packages, 79838252 bytes); the volume of 1000000000 bytes holds 80137 packages at this size; marks beyond it: [100000].

## Projection at the current rate

Served now: 6398. Approved per slot: 1589.7. Slots a day: 4.0. Approved a day: 6358.7. Eligible remaining in the store: 47796. Stock ceiling at the measured yield: 44395; at the current export policy: 42624. Serving capacity declared: 25000 (reached in 2.9 days at this rate). Generated candidates waiting for a reviewer of another family: 8904 (yield not measured, outside the ceiling).

| Mark | Short | Days | Date | Reachable from the current stock | Reachable at the current export policy | Within the serving capacity |
|---|---|---|---|---|---|---|
| 10000 | 3602 | 0.6 | 2026-09-27 | True | True | True |
| 30000 | 23602 | 3.7 | 2026-09-30 | True | True | False |
| 100000 | 93602 | 14.7 | 2026-10-11 | False | False | False |

If slots ran back to back (14.5 a day): 23082.0 approved a day, the stock exhausted in 1.6 days.
