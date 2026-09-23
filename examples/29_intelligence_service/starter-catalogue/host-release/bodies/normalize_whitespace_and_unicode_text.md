# Normalize whitespace and Unicode text without losing information

Clean the invisible problems in text first: odd spaces, split accents, zero-width characters and typographic quotes. Keep every change that loses information as an explicit choice.

## When to use it

Use it as the first cleaning pass on any text column, before capitalisation, legal suffix, phone, email or website rules. Those rules read the cleaned text.

## Steps

1. Replace non-breaking spaces, other Unicode space characters, tabs and line breaks with an ordinary space.
2. Trim both ends, then collapse each run of spaces to one space. These whitespace changes lose nothing. Give them a confidence of 0.99.
3. Compose characters to Unicode Normalization Form C, so that a letter and a separate accent mark become one character (confidence 0.99).
4. Remove zero-width characters: the zero-width space, non-joiner and joiner, the word joiner and the byte order mark (confidence 0.98).
5. Replace typographic single and double quotes with straight quotes (confidence 0.95). A parameter can switch this off.
6. Keep characters outside ASCII by default and record the reason `non_ascii_retained`.
7. Treat folding to ASCII as a declared choice with three settings. `never` is the default. `hold` proposes the folded form at confidence 0.5, so a reviewer decides. `apply` gives 0.9, because the data owner chose folding. Folding uses a declared map first, for example the German sharp s becomes `ss`, and then removes accent marks.
8. Use the lowest confidence among the changes as the confidence of the whole correction.

## Checks

- A value with a non-breaking space, a tab and doubled spaces between `Acme`, `Widgets` and `Inc` becomes `Acme Widgets Inc` at 0.99.
- `zero`, a zero-width space, then `width` becomes `zerowidth` at 0.98.
- With the default setting `Straße` stays `Straße`.
- Running the pass a second time changes nothing.

## Known-wrong example

A cleaning script folds every value to ASCII, so `Straße` becomes `Strasse` and `José` becomes `Jose` in the stored data. The change cannot be undone and nobody chose it. With the `hold` setting the folded form is only a proposal at 0.5. It goes to review and the stored value stays as written.

## What to record

- Each changed value with its named reasons and its confidence.
- The folding setting and who chose it.

## Source

- `src/loop_engine/code_nodes/text_conformance_operations.py`: `whitespace_normalize`, `unicode_normalize` and `ascii_fold`.
- `src/loop_engine/data/text_conformance_catalogs.yaml`: the declared folding map.

Licence: MIT. Compiled from revision d893bba. The operations module uses only the Python standard library.
