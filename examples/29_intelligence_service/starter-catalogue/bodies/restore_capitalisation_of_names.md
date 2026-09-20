# Restore capitalisation of person and company names

Decide capitalisation token by token, with a confidence that names every doubtful decision. A value written fully in upper case or fully in lower case carries no case information, so every token in it must be decided.

## When to use it

Use it when a name or company column mixes correctly written values with values in all upper case or all lower case.

## Steps

1. Leave null markers and values without letters unchanged.
2. When the value has mixed case, keep its existing capitals, for example `iPhone` and `IBM`, and only check first letters.
3. Otherwise split the value on spaces and then on hyphens. Note whether each token is first, inner or last.
4. For each token, use the first rule that matches:
   - keep a token that contains digits;
   - use an exact entry in the surname exception list (`macdonald` gives `MacDonald`, `macy` gives `Macy`);
   - use a casing that the column itself proves;
   - case a legal suffix that is not the first token like its canonical form (`INC` gives `Inc`, `LLC` stays `LLC`);
   - keep a preserved token in upper case (`IBM`, `USA`, `HVAC`);
   - write a single letter in upper case;
   - write `O'Brien` for a single letter `O`, `D` or `L` before an apostrophe;
   - write a particle such as `van`, `der`, `de` or `la` in lower case unless it is first, at confidence 0.8, and mark it ambiguous;
   - write a minor word such as `and`, `of` or `the` in lower case in an inner position;
   - give an internal capital after the prefixes `Mc` (0.97), `Fitz` (0.9) and `Mac` (0.8);
   - keep a token without vowels in upper case (0.9), keep a token of one or two letters in upper case (0.75, ambiguous), and capitalise a token of three letters (0.85, ambiguous);
   - otherwise capitalise the first letter.
5. Start from a base confidence of 0.92 when case information is absent and 0.95 when it is present. The confidence is the lowest signal used, minus 0.02 for each ambiguous decision after the first.

## Checks

- `ACME CORPORATION` becomes `Acme Corporation` at 0.92.
- `IBM SERVICES OF AMERICA` becomes `IBM Services of America`.
- `AA CAREERS` gives the proposal `AA Careers` at 0.75, so the value is held for review.
- `JOHN VAN DER BERG` gives `John van der Berg` at 0.78, so the value is held for review.
- `Acme Widgets` is unchanged at 1.0.

## Known-wrong example

A generic title case function turns `IBM SERVICES OF AMERICA` into `Ibm Services Of America`. This method also has a known weak spot. For `MACHINE TOOLS INC` the `Mac` prefix rule proposes `MacHine Tools Inc`. The confidence is 0.8, so the proposal is held and the input is kept. The repair is an exception entry `machine: Machine`. Lowering the threshold would apply the wrong value.

## What to record

- Each proposal with its named reasons, its confidence and its outcome.
- Every exception entry that was added, with the value that showed the need.

## Source

- `src/loop_engine/code_nodes/text_conformance_operations.py`: `case_normalize`.
- `src/loop_engine/data/text_conformance_catalogs.yaml`: the particle, minor word, preserved token, prefix and surname exception lists.

Licence: MIT. Compiled from revision 381efec. The operations module uses only the Python standard library.
