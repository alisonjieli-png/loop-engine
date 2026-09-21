# Restore capitalisation of person and company names

Decide capitalisation token by token, with a confidence that names every doubtful decision. A value fully in upper case or fully in lower case carries no case information, so every token must be decided.

## When to use it

Use it when a name or company column mixes correctly written values with values in all upper case or all lower case.

## Steps

1. Leave null markers and values without letters unchanged.
2. When the value has mixed case, keep a token fully in upper case (`IBM`) and a token that starts with a capital and has another capital (`PayPal`). Step 4 decides every other token. A token such as `iPhone` or `eBay` is not kept.
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
- `AA CAREERS` gives the proposal `AA Careers` at 0.75 and is held for review.
- `JOHN VAN DER BERG` gives `John van der Berg` at 0.78 and is held.
- `Acme Widgets` and `PayPal Holdings` are unchanged at 1.0.
- `iPhone Repair` becomes `Iphone Repair` at 0.95. With the exception entry `iphone: iPhone` it is unchanged at 1.0.

## Known-wrong example

A generic title case function turns `IBM SERVICES OF AMERICA` into `Ibm Services Of America`. This method also has two known weak spots. First, for `MACHINE TOOLS INC` the `Mac` prefix rule proposes `MacHine Tools Inc`. At 0.8 the proposal is held and the input is kept. The repair is the exception entry `machine: Machine`. Lowering the threshold would apply the wrong value. Second, `eBay Store` becomes `Ebay Store` at 0.95. At an apply threshold of 0.9 this wrong value is applied, not held. The repair is an exception entry such as `ebay: eBay`. The column also protects the token when at least two mixed case values show the same form.

## What to record

- Each proposal with its named reasons, its confidence and its outcome.
- Every exception entry that was added, with the value that showed the need.

## Source

- `src/loop_engine/code_nodes/text_conformance_operations.py`: `case_normalize`.
- `src/loop_engine/data/text_conformance_catalogs.yaml`: the particle, minor word, preserved token, prefix and surname exception lists.

Licence: MIT. Compiled from revision 381efec. The operations module uses only the Python standard library.
