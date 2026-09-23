---
name: trace-numeric-rounding
description: Trace where rounding changes a computed result. Use when line totals, subtotals, or displayed values disagree by a small amount.
---

# Trace numeric rounding

## When to use

Use this when numeric results differ near a precision boundary. The correct result depends on the supplied scale, rounding mode, and stage at which rounding is required.

## Inputs

- Original values and their source precision, calculation order, and output scale.
- The approved rounding mode and whether rounding happens per line, at subtotal, or at final display.
- Any required arithmetic representation, and whether the available tooling supports it.
- A tolerance or exact equality rule for reconciliation.

## Procedure

1. Preserve the original decimal values as written. Do not silently infer extra precision from a displayed number.
2. Recompute intermediate results without premature rounding when the calculation method allows it. If the claimed rule requires exact decimal arithmetic, use an exact decimal representation. If that is unavailable, report the reconciliation as unverified rather than substituting binary floating-point arithmetic.
3. Apply the specified rounding mode at the specified stage. Separately compute plausible alternative stages to explain a difference, but do not substitute them for the approved rule.
4. Compare line amounts, subtotals, final total, and any remainder. Attribute each difference to a particular rounding operation or unresolved input.
5. Include a tie case and a value just beside it in a worked check.

## Completion check

Return original values, calculation sequence, scale, rounding mode, rounding stage, intermediate and final results, and reconciled difference. State whether the observed result follows the supplied rule, or is unverified because the required arithmetic was unavailable.

## Stop conditions

Stop before declaring one total correct if the rounding rule, stage, or required arithmetic is unavailable. Do not edit source values or set a tolerance merely to make a difference disappear.
