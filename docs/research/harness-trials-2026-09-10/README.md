# Harness trial campaign: data over review

Frozen protocol for the first live comparison round. Review (T0) picked the
arms; from here, numbers decide. Status: registered, not yet run.

## Arms

| Arm | ID | Version | Why in the trial |
|---|---|---|---|
| OpenCode | `opencode` | 1.18.29 | Proven adapter path; control arm |
| Pi | `pi` | latest MIT release | JSON-RPC machine contract; fork-base candidate |
| Codewhale | `codewhale` | latest MIT release | Small Rust audit surface; vetting-cost candidate |
| Crush | `crush` | 0.92.0 | Native preemptive budget knobs (T3 probe) |
| gptme | `gptme` | 0.33.0 | Python-auditable; budget flags (T3 probe) |

All arms run the same provider route, the same model, the same task
population, and the same independent evaluator. Differences are recorded, not
adjusted away.

## Measurements

Every arm records: physical model calls, provider-reported token usage
(input, output, reasoning, cache), cost state, wall time, startup time, tool
calls by effect class, failed tool calls, repair attempts, final artifact
digest, and evaluator verdict. Missing usage stays unknown, never zero.

## Gates

- T1 transport: headless run against the stub relay; event schema parse;
  stdin prompt; exit codes; usage accounting. No model spend.
- T2 containment: network-none container, read-only workspace, scrubbed env;
  ambient-credential probe must fail closed.
- T3 budget: kill at N model calls and wall time; verify no effect after kill.
  Crush and gptme additionally test native budget knobs against supervisor
  kills, labeled as separate arms if their enforcement differs.
- T4 effects: exact tool disable lists; veto refusal; effect classification.
- T5 frozen comparison: only T1-T4 passers. Same task set, same information,
    same model, independent evaluator. One success is a working path, not a
    general claim.

## Population

Small frozen set of text tasks with machine-checkable postconditions, drawn
from the existing examples corpus (novel-task campaign shape). Tasks with no
checkable postcondition are excluded. Failures are retained with the same
prominence as successes.

## Fairness rules

- Arms receive identical prompts, identical context packets, identical
  budgets.
- Any arm that cannot accept the relay endpoint or the stdin packet is
  recorded as unavailable for that gate, not adapted around.
- No post-hoc prompt tuning between arms. Prompt changes restart the arm.
- Published benchmark numbers from other harnesses may not substitute for a
  missing arm.

## Evidence

- Per-run JSONL records under `artifacts/harness-trials-2026-09-10/` (git
  excluded), one file per arm-gate-run, with digests.
- Summary table is generated from the records, never hand-written.
- This campaign is non-deterministic where a model runs; that is a campaign
  choice recorded here, not a product rule.
