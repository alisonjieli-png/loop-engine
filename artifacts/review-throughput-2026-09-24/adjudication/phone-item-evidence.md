# Measured evidence about normalize_phone_numbers, for its adjudication

Kind: evidence supplied to the independent review of the catalogue item
`normalize_phone_numbers`. It quotes a dated study; it is not an instruction
to the reviewer, and it approves or rejects nothing.

## The question

The item is approved and served. A controlled study then measured that a
cheap model given this item did worse on telephone numbers than the same model
without it. Judge the item's exact bytes against the written criteria with this
evidence in view, as for any review. If the item fails a criterion, say in your
reasons whether a narrowed version would meet the criteria (the same method,
with its limits stated so that a reader does not apply it where it is wrong),
or whether the method must be replaced by another one.

## What the study measured

Source: `case-studies/data-cleanup-with-and-without-baltor/REPORT-2026-09-22.md`,
a frozen, pre-registered comparison on a synthetic population disclosed as
synthetic, with every telephone number in a range reserved for fiction. The
phone family has 38 rows; 7 of them should be held for review, and 1 more may
be held or repaired. A step passes at record accuracy 0.90 or more with no
wrong change to a correct value.

| Arm | Record accuracy by repetition | Mean | Passed |
|---|---|---|---|
| cheap cloud model, no material | 1.000, 0.974, 1.000 | 0.991 | 3 of 3 |
| cheap cloud model, with this item | 0.842, 0.842, 0.842 | 0.842 | 0 of 3 |
| larger cloud model, no material | 1.000, 0.974, 0.974 | 0.983 | 3 of 3 |

What the item changed, row by row, over three repetitions, with the count
without the item first (quoted from section 6 of the report):

- United Kingdom numbers with a `(0)` trunk prefix: 6 of 6 right without the
  item, 0 of 6 with it; the model kept the 0, as in `+4402079460168`.
- Numbers dialled with the 011 exit prefix: 6 of 6 against 0 of 6; the model
  held them instead.
- The area code 015: 3 of 3 against 0 of 3; the model added `+1`.
- The `+415` number with an impossible length: 2 of 3 against 0 of 3; the model
  kept it as international.

The report's reading: each of these follows the item's written digit-count
rule, which does not cover trunk prefixes, exit prefixes, area code validity or
country number lengths. It is evidence about one model, one harness and one
population; it does not establish harm in every setting.
