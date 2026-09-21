# Canonicalize company legal suffixes

Write legal suffixes such as Inc, LLC, Ltd and GmbH in one declared style, and send doubtful suffixes to review.

## When to use it

Use it on company name columns where one company appears as `Acme Widgets, Inc.`, `ACME WIDGETS INC` and `Acme Widgets Incorporated`. Use it before duplicate detection and before reporting.

## Steps

1. Keep a map from every written form to one canonical form. `inc` and `incorporated` give `Inc`. `corp` and `corporation` give `Corp`. `ltd` and `limited` give `Ltd`. `co` and `company` give `Co`. `llc` gives `LLC` and `gmbh` gives `GmbH`.
2. Read at most the last two tokens of the value. Remove `.`, `,` and `;` from a token and lower its case before the lookup. Never treat the first token as a suffix, so a company named `Inc` alone stays unchanged.
3. Choose one style: short without a period (the default), short with a period, or the long form (`Incorporated`, `Corporation`, `Limited`, `Company`). A suffix written in all upper case never gets a period.
4. Choose what happens to a comma before the suffix: remove it (the default), keep it or add it.
5. Keep a second table of ambiguous suffixes, because they are also ordinary words or initials. Each has a confidence: `as` 0.5, `spa` 0.6, `cv`, `ug` and `kg` 0.7, `ab` 0.75, `sa`, `pc` and `kk` 0.8, `ag` and `co` 0.85.
6. A rewrite without an ambiguous suffix has confidence 0.97. A rewrite that involves an ambiguous suffix takes the lowest table value. A value that does not change has confidence 1.0.

## Checks

- `Acme Widgets, Inc.` becomes `Acme Widgets Inc` at 0.97.
- `Holding Co., Ltd.` gives the proposal `Holding Co Ltd` at 0.85, so the value is held for review.
- `Banco Popular s.a.` gives the proposal `Banco Popular SA` at 0.8, so the value is held for review.
- A null marker such as `n/a` is unchanged.

## Known-wrong example

A rule writes every trailing `as` in upper case, so `nordic fish as` becomes `nordic fish AS` without review. `AS` is a Norwegian company form and `as` is also an English word. This method proposes the same text at confidence 0.5. That is below the escalation threshold of 0.6, so the value goes to a model, to research or to a person, and the input is kept.

## What to record

- The chosen style and comma setting.
- Each rewrite with its reasons, for example `suffix_canonicalized:Inc` and `ambiguous_suffix:co`.
- Every held or escalated value with the proposal that was not applied.

## Source

- `src/loop_engine/code_nodes/text_conformance_operations.py`: `suffix_canonicalize`.
- `src/loop_engine/data/text_conformance_catalogs.yaml`: the legal suffix map, the ambiguous suffix table and the long forms.

Licence: MIT. Compiled from revision eb757bc. The operations module uses only the Python standard library.
