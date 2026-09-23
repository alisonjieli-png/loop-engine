# Score a possible duplicate pair by its weakest field

Build one comparison key for each field, measure named signals for each field, and let the weakest field set the confidence of the pair. A strong match on one field never hides a mismatch on another.

## When to use it

Use it when deciding whether two customer, company or contact rows describe the same entity.

## Steps

1. Build the keys:
   - name: fold case, remove punctuation, and drop trailing tokens that are in the declared legal suffix list, but never the only token;
   - address: fold case, remove punctuation, and expand whole word abbreviations such as `st`, `ave`, `n` and `ste`;
   - email: the normalized address, or empty text when the value is not an address;
   - phone: the last ten digits when the value has at least seven digits.
2. Compare a field only when both rows have a value for it.
3. For email and phone, measure key equality only. For name and address, also measure the share of common tokens and a character sequence ratio.
4. The similarity of a field is 1.0 when the keys are equal. Otherwise it is the better of the two text signals.
5. The confidence of the pair is the lowest field similarity. A pair with no compared field has confidence 0.
6. Classify with two thresholds: duplicate at or above 0.92, possible at or above 0.75, otherwise distinct.

## Checks

- `Acme Widgets, Inc.` and `ACME WIDGETS INC` have the same name key. `12 N Main St., Ste 4` and `12 North Main Street Suite 4` have the same address key.
- With equal name, address, email and phone keys, the pair is a duplicate at 1.0.
- Against such a row, `Acme Widgets` at `12 N Main St`, without an email or a phone, is a possible pair at 0.833.

## Known-wrong example

Two rows share an email and a phone, so a matcher merges them. One row is `Beta Holdings LLC` at `9 Oak Ave` and the other is `ACME WIDGETS INC` at another address. A shared mailbox and a shared switchboard are common. Here the name similarity is 0.24 and the address similarity is 0.15, so the confidence of the pair is 0.15 and the rows stay distinct.

## What to record

- Every compared pair with its signals for each field, its confidence and its outcome.
- The two thresholds and the abbreviation table that were used.

## Source

- `src/loop_engine/code_nodes/duplicate_detection.py`: `name_key`, `address_key`, `email_key`, `phone_key`, `compare_keys`, `field_similarity`, `pair_confidence` and `classify`.

Licence: MIT. Compiled from revision 40fce69. The sequence ratio comes from the Python standard library module `difflib`.
