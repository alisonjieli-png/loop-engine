# The first live campaign cells, September 14, 2026

Observed facts from the two task-database campaign workers the Codex
session launched at 00:32 UTC against Ollama Cloud, read from the cells'
exported records under
`.loop-engine-dev/fabric-readiness-20260913-N8fyhI/live-flash` and
`live-pro` at 02:19 UTC, after both workers had stopped. Calls are the
checkpoint count of each cell's step history (one checkpoint per model
invocation); tokens are the provider-reported usage in each cell's exported
outcome. Nothing here is an independent evaluation of any deliverable.

## Flash route (`deepseek-v4-flash:0731`, thirteen cells)

| Task | Terminal | Calls | Tokens | Seconds | Artifacts | Fallback level |
|---|---|---:|---:|---:|---:|---|
| CS-001 | COMPLETED_VERIFIED | 44 | 869,960 | 206 | 4 | none |
| FIN-001 | VERIFICATION_FAILED | 69 | 1,293,050 | 328 | 2 | none |
| OPS-001 | VERIFICATION_FAILED | 144 | 3,544,102 | 884 | 2 | none |
| DA-001 | NO_PROGRESS | 100 | 2,448,712 | 700 | 0 | none |
| AE-001 | BLOCKED_MATERIAL_INPUT | 168 | 4,387,273 | 1,071 | 0 | none |
| ML-001 | BLOCKED_MATERIAL_INPUT | 232 | 7,269,654 | 1,596 | 0 | none |
| PM-001 | PROVIDER_UNAVAILABLE | 60 | 1,390,299 | 475 | 0 | none |
| BA-001, DE-001, HR-001, MKT-001, SCM-001, SEC-001 | failed before any call | 0 | 0 | 0 | 0 | registered_alternatives |

Flash total: 817 calls and 21,203,050 tokens over seven executed cells; six
cells never reached a model because every cell whose grid level was
`registered_alternatives` refused to load an uninstalled alternative
harness (`HarnessProcessError` at the trial boundary). PM-001 ended when
the allowance ran out mid-cell.

## Pro route (`deepseek-v4-pro:0813`, three cells)

| Task | Terminal | Calls | Tokens | Seconds | Artifacts | Fallback level |
|---|---|---:|---:|---:|---:|---|
| AE-001 | NO_PROGRESS | 18 | 366,139 | 102 | 0 | none |
| BA-001 | failed before any call | 0 | 0 | 0 | 0 | registered_alternatives |
| CS-001 | cancelled by the operator | 489 | about 21 million by the checkpoint log | about 4,700 | none accepted | none |

The CS-001 pro cell had made 320 calls and consumed 13,795,386 tokens by
01:30 UTC (13,532,969 prompt, 262,417 completion), with sixty verification
rounds and no accepted result; it was cancelled at 489 calls. Each call
carried about twenty thousand prompt tokens, growing as context accumulated.

## What the allowance bought

Roughly forty million provider-reported tokens in ninety minutes, one
verified solution, and the weekly allowance spent again at 02:04 UTC (the
flash worker's next access check was refused with `usage_limit_reached`).
The median executed cell cost about a hundred calls and 2.4 million
tokens. At that cost the declared grid (1,771 tasks by 320 configurations)
is not reachable on a weekly allowance; the grid needs explicit per-cell
call and pass ceilings as configuration levels, which the owner's rules
require to be declared rather than implied.

## What each terminal meant here

- `COMPLETED_VERIFIED`: the Practitioner's own verification accepted the
  delivered artifacts. Independent task-specific evaluation has not run.
- `VERIFICATION_FAILED`: artifacts were delivered and the verifier's
  verdict was repair when the run ended.
- `NO_PROGRESS`: the run stopped honestly with no verified artifact.
- `BLOCKED_MATERIAL_INPUT`: the run decided it could not proceed without
  material it did not have, after 168 and 232 calls.
- `PROVIDER_UNAVAILABLE`: the allowance ran out during the cell.
- Failed before any call: the trial boundary refused to load the fallback
  order because an alternative harness is not installed on this host.

## Fixed on main after these observations

- An uninstalled alternative registers as unavailable instead of failing
  the assignment (`b5a6293`); the runner's dispatch must pass
  `allow_unavailable=True` for alternatives.
- The kernel applies the supervision policy's unaccepted-pass count to its
  own passes when no budget is declared and climbs the ladder to the honest
  stop after twenty-seven refused passes by default (`0e229d0`), and shows
  the next pass the supervision knowns as facts (`911456b`). On this
  evidence that stop would have ended ML-001 and the pro CS-001 cell at
  roughly a third of their spend.
- Schema repair is told which declared field failed (`6f06219`), after the
  pro AE-001 cell spent twelve admissions on an unnamed `minItems`.
- Every checkpoint of a store verifies from one reading (`d409459`).

## Open

- Explicit per-cell call and pass ceilings as grid levels, and the
  relaunch from a snapshot at or after `911456b`.
- Prompt size: about twenty thousand tokens per call by the tenth call, so
  context delivery and compaction levels deserve a matched comparison.
- Independent evaluation of the one verified solution and the two
  delivered-but-refused ones.
- Reconciliation of the cancelled pro occurrence before its queue moves.
