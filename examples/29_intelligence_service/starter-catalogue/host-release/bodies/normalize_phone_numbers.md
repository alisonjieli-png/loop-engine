# Normalize phone numbers only when the digit count is explainable

Rewrite a phone number to an international form when its digits can be explained. Leave every other value unchanged and send it to review.

## When to use it

Use it on phone columns with mixed punctuation, extensions and missing country codes. Use it before comparing or joining on phone numbers.

## Steps

1. Leave null markers unchanged.
2. Separate a trailing extension written as `ext`, `ext.`, `extension` or `x` followed by one to six digits.
3. Remember whether the value starts with `+`, then remove every character that is not a digit.
4. Decide by the digit count:
   - the value started with `+` and has 8 to 15 digits: keep it as international, confidence 0.93;
   - a default country code is declared and the digit count equals the national length: add the country code, confidence 0.95;
   - the digits start with the declared country code, followed by a full national number: add `+`, confidence 0.95;
   - no default country code is declared and the count equals the national length: return the digits alone at confidence 0.7, so the value is held;
   - any other count: leave the value unchanged at confidence 0.35 and record `digit_count_unexpected` with the count, so the value is escalated.
5. When extensions are kept, put the extension back after the number: a space, the word `ext`, a space and the digits.

The national length is a parameter. Its default is 10. The default country code is a parameter with no default.

## Checks

- With default country code 1, `(415) 555-0100` becomes `+14155550100` at 0.95.
- With default country code 1, `415-555-0100 ext. 12` becomes `+14155550100 ext 12`.
- `+44 20 7946 0958` becomes `+442079460958` at 0.93.
- `555-0100` is unchanged and escalated, with the reason `digit_count_unexpected:7`.

## Known-wrong example

A script adds country code 1 to every ten digit number in a customer table that covers several countries. Numbers from other countries now look valid and are wrong. Without a declared default country code this method returns the digits alone at 0.7, which holds the value. Padding a seven digit number with a guessed area code is wrong for the same reason.

## What to record

- The declared default country code and national length, and who declared them.
- Each rewrite with its reason, and each held or escalated value.

## Source

- `src/loop_engine/code_nodes/text_conformance_operations.py`: `phone_normalize`.

Licence: MIT. Compiled from revision a0ca182. The operations module uses only the Python standard library.
