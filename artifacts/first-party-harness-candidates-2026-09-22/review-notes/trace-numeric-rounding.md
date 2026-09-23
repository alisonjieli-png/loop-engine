# Candidate review: trace-numeric-rounding

Status: candidate only. The exact `packages/data/trace-numeric-rounding/SKILL.md` bytes need independent review before admission.

- Original authoring and source basis: Written for this batch by a Codex research subagent. The [Agent Skills specification](https://agentskills.io/specification) informed the file structure. [Python's decimal documentation](https://docs.python.org/3/library/decimal.html) was checked for decimal arithmetic and configurable rounding. No external prose was copied. License and originality remain review decisions.
- Applicability facets: invoices, usage totals, scientific tables, reports, scoring calculations; wherever decimal output is rounded.
- Search phrasings (author-supplied discovery aids, not evaluation queries): "Why is the invoice total one cent different from the sum of its lines?"; "Where did the rounding difference appear between subtotal and display?"
- Typed input and output concept: Inputs are `NumericValues`, `CalculationOrder`, `Scale`, `RoundingMode`, `RoundingStage`, and required arithmetic representation. Output is `RoundingTrace` with intermediate values, final value, alternative-stage comparison, reconciled difference, and verified or unverified status.
- Declared effects: read-only analysis. No billing record or source value is changed.
- Known-good example: Three lines are each 0.005, and the supplied rule is decimal half-up rounding to two places on each line. The displayed line amounts total 0.03.
- Known-wrong example: Round the unrounded sum 0.015 once to 0.02, then claim it follows the per-line policy.
- Overlap search: `write_a_regression_test_that_pins_a_defect.md` mentions a rounding defect as an illustration. No starter body specifies tracing a scale, rounding mode, and stage through a numeric calculation.
- Limitations to check: The rule may require another rounding mode or stage. The skill leaves the answer unresolved when those are missing or when exact decimal arithmetic is required but unavailable. A reviewer should check a tie, a nearby non-tie, and an exact-decimal-unavailable case that must not be declared correct from binary floating-point output.
