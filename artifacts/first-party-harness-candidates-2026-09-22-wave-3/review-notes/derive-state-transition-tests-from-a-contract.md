# Candidate review: derive state-transition tests from a contract

Status: candidate only. No independent approval, native load, licence assignment, or measured benefit.

- Source and originality: Original procedure written for this batch. Need inspiration is task `15-1252.00 / 21669` in the pinned [O*NET® 31.0 Database inventory](../../occupation-grid-research-2026-09-22/README.md) by the U.S. Department of Labor, Employment and Training Administration, under [Creative Commons Attribution 4.0](https://www.onetcenter.org/license_db.html). No task prose or third-party skill text was copied; the agency did not approve or test this candidate.
- Facets: Stateful application developer or tester; order, job or account lifecycle; exact state/event contract supplied by project.
- Typed input/output concept: `State[]`, `Event[]`, `TransitionRule[]`, `Invariant[]`, `EffectContract[]` to `TransitionTestPlan` and `CoverageGap[]`.
- Effects: Read-only test design. No fixture write, state change, test run or external call.
- Good fixture: A payment state machine allows `pending → paid` on a confirmed capture and refuses `paid → unpaid` without a reversal event. The plan includes both paths and an interruption after capture before local acknowledgement.
- Known-wrong fixture: A test suite executes only the successful `pending → paid` path and calls the machine covered. It misses an unsupported direct `paid → unpaid` transition and could allow a state change without a reversal effect. The method must report the forbidden edge gap.
- Search phrasings: “Which transitions are missing from our order lifecycle tests?”; “Can this event move a completed job back to pending without the required reversal?”
- Nearest overlap and distinction: Starter `choose_test_cases_from_boundaries_and_classes` covers input categories; `write_a_regression_test_that_pins_a_defect` pins one failure. This method derives edge, guard, forbidden and interruption cases from a versioned state transition contract.
- Limits: The state contract, event order and effect identity must be supplied. The test plan cannot prove actual implementation behavior without an independent run.
