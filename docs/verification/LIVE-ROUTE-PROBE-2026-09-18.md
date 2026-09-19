# Live route probe and the folder intake rehearsal

Date: 2026-09-18. This record answers one question with observations rather
than opinion: can the engine take a problem folder today and solve it end to
end, and is the authorized live model route usable. It records a failed live
trial, as the repository rules require, and names what blocks the next live
qualification.

## What was attempted

| Step | Command | Result |
|---|---|---|
| Folder intake, deterministic, with the fast path flag | `solve --file INSTRUCTIONS.md --dataset <folder> --practitioner-mode deterministic --allow-fast-path` | Refused before work with a typed reason: the fast path allowance applies to model-led runs because the deterministic mode already runs exact resolution |
| Folder intake, deterministic | the same without the fast path flag | `CAPABILITY_GAP`: the preserved work and the remaining constraint were returned, the limitations named `semantic_orientation` and `verified_result`, and the next action read "Configure a supported model route or install a compatible capability" |
| Live route probe with a strict total ceiling | `models probe ollama_cloud --authorize-model-calls --max-model-calls 1 --max-total-tokens 70000` | Refused before any dispatch with `token_bound_unavailable`, zero physical calls |
| Live route probe with the explicit unbounded total authorization | the same with `--allow-unbounded-total-tokens` | One physical call, `provider_responded` false, `failure_code` `usage_limit_reached` |

The problem folder held an instruction file and a five-row supplier file
with case, legal suffix, spelled-out separator, typed domain, and duplicate
defects, so that a successful run would have exercised the detection and
correction family this session landed.

## What the observations mean

Observed. The folder intake works: an instruction file plus a directory of
materials is accepted, and the run reaches orientation. A deterministic run
of an unseen problem stops at `CAPABILITY_GAP` because semantic orientation
needs a model, and it says so instead of inventing a result.

Observed. The one authorized live route is exhausted. The provider answered
one probe call with a usage limit, so no live run can be qualified until the
allowance is restored or another route is authorized. No further live calls
were made after that answer.

Observed. A strict total-token ceiling is unusable on this path today. The
gateway takes a `token_bound_resolver` and nothing installs one, so
`--max-total-tokens` refuses before dispatch with `token_bound_unavailable`
whatever the number. The only live path is the explicit
`--allow-unbounded-total-tokens` authorization bounded by a call count. That
is a real gap between a declared control and a usable one.

Inferred. Because the probe never dispatched in the strict case and the
provider answered immediately in the unbounded case, the usage limit is a
provider allowance, not a credential or transport fault.

Missing. Everything this session landed that only a live run can qualify:
the fast path decision on a real task, route separation with two authorized
routes, the noise injection and convergence work on model-led cells, the
detection and correction family consumed by a solve, the seeded intelligence
in retrieval, the typed decision route against a real judge, and the
resource supervisor against real harness processes.

## What this blocks and what it does not

It does not block offline work. Every boundary landed this session is
verified by its own checks and mutants on an exported tree, and the
standalone export path runs without the engine.

It blocks the claim that the engine can take an unseen problem folder and
produce a verified solution today, because that path needs semantic
orientation, and orientation needs a model route with allowance.

## Next steps

1. Restore the Ollama Cloud allowance, or authorize a second route, so a
   matched live rerun can qualify the changes since commit `d3bda30`.
2. Install a qualified token bound resolver, or state in the command help
   that a strict total ceiling needs one, so the declared control is either
   usable or honestly described (roadmap S-4.11).
3. Run the folder rehearsal again with a live route and record the outcome
   beside this record.
