# Engine framework wave A: integration record, September 23, 2026

This record keeps the integrator's report for the first wave of the engine
framework (roadmap package D-19, steps S-6.30, S-6.31, S-6.42 and S-6.61). The
integration line ended at `a557586`, reached `main` in the merge `5c188ab`,
and went live in Fly release 17 from `381cc52`. The release record is
[`pilot-release-15.json`](../../artifacts/architecture-audit-2026-09-19/pilot-release-15.json).

## What was integrated

Five packages, merged in this order, each with a plain merge followed by a
separate commit for its entries in shared files:

1. F1, the engine records. Its six modules moved into `core/engines/` as
   `records.py`, `host_records.py`, `selection_records.py`,
   `decision_records.py`, `records_checks.py` and
   `selection_records_checks.py`. Nothing imported them at their old paths.
2. F2, the catalogue of 45 engine slots.
3. F11, the live dependency guards, which collect thirteen suites again.
4. X2, the step executor adapter contract.
5. X1, the harness recipe catalogue.

The integrator added one check nobody asked for:
`the_step_executor_slot_record_names_the_contract_kinds_version_and_edges`.
It fails if the X2 contract constants and the F2 `step_executor` slot record
drift apart. Which of the two should read the other is left to package X5.

## How it was checked

- Line survival: 0 lost lines on all five merges. A second audit found every
  added line in the final tree except 52 changed on purpose: 48 import and
  docstring lines from the F1 move and 4 lines from two F2 fixes.
- One merge conflict, in `EXTERNAL-HARNESS-ADAPTERS.md`, where X2 and X1 both
  added sections at the same place. Both were kept whole, X2 first.
- Problems that appeared only when the packages met `main` or each other, all
  fixed: F2's catalogue named a protocol check that `main` had replaced
  (`08dfc44`); F2's slot check used a suite that F11 collects again as its
  example of a parked suite (`98e34de`); `main`'s stricter guide checker
  rejected two check names in X1's guide text (`9490c5f`); X2 changed a file
  the starter catalogue cites, so the catalogue was anchored again
  (`a557586`, all 43 approvals carried).
- Gates on `a557586`: conformance, 32 gates pass; self-test 3,059 of 3,059
  with no provider call; tools 827 tests; component guides with documented
  checks, 0 findings; hardcoding audit with no new high finding; embodiment
  106; qualification 3; examples 24 of 24; browser 406 of 406 with 56 of 56
  planted faults caught; markdown lint 0 issues; records index current.

## Open problems, by roadmap step

### S-6.30, the engine framework

- Problem 1: The descriptor and installation digests leave out the facts that change
   over time: availability, qualification, lifecycle and the enabled switch.
   The reuse key of package F3 must include digests of those facts.
- Problem 2: Policy validation that depends on the slot is not built: the fallback
   limit and allowed fallback kinds, evidence objectives, the sample floor,
   which engine kinds a slot allows, and the binding site.
- Problem 3: Three embedded records are checked by type only.
   `configuration_preference_decision` accepts unknown fields and a version 2
   that no package defines; the fields of `engine_evidence_rule` and
   `engine_comparison_policy` are never read.
- Problem 4: Retiring one engine version cannot be checked at the slot level, and the
   five embodiment `qualification.json` files are not yet engine
   qualification records.
- Problem 5: Installation settings still accept keys that carry authority (network
   permission, spending limits, `api_key_env`). Settings should name a
   credential lease through a typed field.
- Problem 6: The nesting rule relies on the caller. Disputed: a sending Loop may claim
   the top precedence (explicit invocation).
- Problem 7: A step executor qualification without a ladder rung is accepted, and
   admission does not compare the qualification's engine with the
   installation's.
- Problem 8: F1 is proven only at the local contract level: nothing calls the records
   yet, and no check refuses an unqualified "the engine" in documents.
- Problem 9: `boundary_report()` does not yet include the slot index.
- Problem 10: The list of places that construct engines directly was found by hand;
  more `Retriever(` and `SQLiteRecordStore(` sites exist.
- Problem 11: About 25 candidate interaction rows name record types that no code
  defines yet.
- Problem 12: One candidate row describes the same gateway edge as an existing active
  row.
- Problem 13: 19 of the 37 run-time slots declare an "unavailable" answer their edge
  does not produce yet. The 8 release-time slots have no interaction row.
  Two design statements do not match the code.
- Problem 14: `run_history_export` and `web_research_port` still name parked suites
  (`otel_export`, `web_search`); `custom_plugins_port`'s suite is now
  collected.
- Problem 15: The evidence floor for each slot (10 or 30) is not recorded as a decision.
- Problem 16: When later packages land the symbols and boundaries the catalogue lists
  as planned (X3, F3, M3, N1, S-6.61, X5, R1, D1, M1, F9), the catalogue must
  change in the same commit. The slot check enforces this.
- Problem 17: The dependency ratchet sees only imports that run at load time. Counting
  imports inside functions gives 544 modules and 198 uncollected suites;
  41 exemptions remain, and imports through `importlib` are not followed.
- Problem 18: The tuple of suites that left the baseline is append-only only by
  convention. Treat it as owned by the integration desk, or move the
  baseline into `forbidden_paths.json` beside the other ratchets.
- Problem 19: `event_vocabulary` has no parked suite, so F3 need not wait on F11. The
  parked count is 47 plus one exception, not 48. Architecture sections
  18.3, 8.7 and 18.4 still call `capability_directory` and
  `heuristic_adoption` parked.

### S-6.31, the harness executor slot

- Problem 20: Decide which source, the contract constants or the slot record, reads
  the other. The new check only detects drift.
- Problem 21: The registration digest covers the declaration and the class, not the
  code bytes, and the configured adapter does not declare its runner.
- Problem 22: Package X3 must create exactly `step_run_request/v1` and
  `step_run_result/v1` and call
  `require_adapter_contract(..., edge=STEP_EDGE)`.
- Problem 23: Adapter information can still be built with empty contract fields, and
  two check modules use fixtures without them.
- Problem 24: The time limit now reads the envelope's clock, which includes the start
  of the Loop and the capture of output; tight budgets may reach it.
- Problem 25: Binding does not refuse an installed version outside the recipe's pinned
  version.
- Problem 26: `instruction_style` is recorded but never read; the instruction writer
  still picks files by harness identifier.
- Problem 27: The recipe loader checks a module's bytes, then reads the file again to
  run it; it should compile the bytes it checked.
- Problem 28: `openinterpreter_rust` fails its transport gate, before and after X1; not
  investigated.
- Problem 29: The new process specification version changes adapter versions, so
  earlier harness selection evidence no longer matches. This is intended.
- Problem 30: Vale, lychee and the product solve acceptance step were not run.

### S-6.42, a fresh instance for every step

- Problem 31: Only loading is proven. Model use, cancellation and the acceptance rungs
  wait for model authority and package X11.
- Problem 32: The offline check does not cover parallel instances, network refusals or
  bundled items. Its harness version pins differ from the embodiment pins
  without a recorded reconciliation, and the evidence keeps each recipe's
  digest but not its text.
- Problem 33: Harness-specific limits: Claude Code in bare mode lists no skills, the
  kept-home control does not discriminate for Claude Code or Pi, Pi's
  software development kit launcher and Pi protocol servers are untested,
  and ZCode is not installed.

### S-6.61, the credential broker

- Problem 34: the local broker (keychain, a short-lived key for each step, a
  protocol gateway, a recorded fallback) is not built. Adding the three planned
  broker slots to the design document is a decision for the integration desk
  or the owner.

## Roadmap evidence corrections the verifiers asked for

- F1: 31 checks and 29 controls, at the new module paths.
- F11: 27 of 27 mutants; 339 literals, all low severity.
- X2: add the commits `315cd86`, `7f80a0a` and `73fdde7`; 43 mutants; one
  new medium finding (`hardcoding.24ab69f8682ac9d352ab1193`); the contract
  suite now has 12 checks.
