# Restore capitalisation of person and company names

Decide capitalisation token by token, with a confidence for every doubtful decision. A value all in upper case or all in lower case carries no case information.

## When to use it

Use it when a name or company column mixes correct values with values in all upper case or all lower case.

## Steps

1. Leave null markers and values without letters unchanged.
2. Split the value on spaces and then on hyphens. Note whether each token is first, inner or last, and whether the value has mixed case.
3. For each token, use the first rule that matches:
   - keep a token that contains digits;
   - use an exact entry in the surname exception list (`macdonald` gives `MacDonald`, `macy` gives `Macy`);
   - use a casing that the column itself proves;
   - case a legal suffix that is not the first token like its canonical form (`INC` gives `Inc`, `LLC` stays `LLC`);
   - keep a preserved token in upper case (`IBM`, `USA`, `HVAC`);
   - in a mixed case value only, keep a token of two or more letters that is fully in upper case, and keep a token that starts with a capital and has another capital (`PayPal`); `iPhone` and `eBay` are not kept;
   - write a single letter in upper case;
   - write `O'Brien` for a single letter `O`, `D` or `L` before an apostrophe;
   - write a particle such as `van`, `der`, `de` or `la` in lower case unless it is first, at 0.8, marked ambiguous;
   - write a minor word such as `and`, `of` or `the` in lower case in an inner position;
   - give an internal capital after the prefixes `Mc` (0.97), `Fitz` (0.9) and `Mac` (0.8);
   - keep a token without vowels (0.9) or of one or two letters (0.75, ambiguous) in upper case, and capitalise a token of three letters (0.85, ambiguous);
   - otherwise capitalise the first letter.
4. Start from 0.92 when case information is absent and 0.95 when it is present. The confidence is the lowest signal used, minus 0.02 for each ambiguous decision after the first.

## Checks

- `ACME CORPORATION` becomes `Acme Corporation` at 0.92.
- `IBM SERVICES OF AMERICA` becomes `IBM Services of America`.
- `AA CAREERS` gives the proposal `AA Careers` at 0.75 and is held.
- `JOHN VAN DER BERG` gives `John van der Berg` at 0.78 and is held.
- `Acme Widgets` and `PayPal Holdings` are unchanged at 1.0.
- `iPhone Repair` becomes `Iphone Repair` at 0.95. With the exception entry `iphone: iPhone` it is unchanged at 1.0.
- `PayPal INC` becomes `PayPal Inc` at 0.95. Only `PayPal` is kept, because the suffix rule comes first.

## Known-wrong example

A generic title case function turns `IBM SERVICES OF AMERICA` into `Ibm Services Of America`. This method has two known weak spots. For `MACHINE TOOLS INC` the `Mac` prefix rule proposes `MacHine Tools Inc` at 0.8, which is held, and the repair is the entry `machine: Machine`; a lower threshold would apply the wrong value. `eBay Store` becomes `Ebay Store` at 0.95. At an apply threshold of 0.9 this wrong value is applied, not held, and the repair is an entry such as `ebay: eBay`. The column also protects the token when at least two mixed case values show the same form.

## What to record

- Each proposal with its reasons, confidence and outcome.
- Every exception entry added, with the value that showed the need.

## Source

- `src/loop_engine/code_nodes/text_conformance_operations.py`: `case_normalize`.
- `src/loop_engine/data/text_conformance_catalogs.yaml`: the particle, minor word, preserved token, prefix and surname exception lists.

Licence: MIT. Compiled from revision 9a483df. The operations module uses only the Python standard library.
