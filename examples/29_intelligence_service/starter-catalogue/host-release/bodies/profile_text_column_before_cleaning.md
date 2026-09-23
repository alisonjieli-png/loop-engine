# Profile a text column before cleaning it

Measure what a text column contains, then propose cleaning rules from the measurements. The profile changes no data.

## When to use it

Use it before any cleaning of names, companies, emails, phones or websites in a table. Use it whenever the column name does not prove what the values are.

## Steps

1. Count null markers first. Values such as an empty text, `n/a`, `-`, `unknown` and `null` are counted and left out of the other counts.
2. For every other value, count these signals: all upper case, all lower case, mixed case, leading, trailing or doubled spaces, nonstandard space or zero-width characters, characters outside ASCII, digits, email-like shape, website-like shape, phone-like shape, and a legal suffix as the last word.
3. Reduce each value to a character pattern. Use the first rule that matches: an upper case letter becomes `A`, a lower case letter `a`, a digit `9`, and any other character outside ASCII `U`. Repeats collapse, so `2026-09-18` becomes `9+-9+-9+`. Keep the five most common patterns.
4. Turn each count into a share of all values.
5. Propose whitespace and Unicode rules first, because later operations read cleaned text.
6. When at least half of the values are email-like, propose only the email rule for that column. Do the same for website-like and phone-like columns.
7. Otherwise propose a capitalisation rule when at least 5 percent of values are all upper case, or when at least 5 percent are all lower case while other values are mixed case. Propose a legal suffix rule when at least 5 percent of values end in a legal suffix.
8. Attach to each proposal the share that justified it.

## Checks

- The profile reports the total, the counts, the shares and the top patterns.
- An accented letter is still a letter in the pattern, so `José` gives `Aa+` and not `Aa+U`. Read the count of characters outside ASCII, not the pattern, to find accents.
- Every proposed rule names its evidence. A rule without evidence is not proposed.
- No value in the table changed.

## Known-wrong example

A column named `contact` is assumed to hold names, so a capitalisation rule is applied. The profile shows that 80 percent of the values are email-like. The correct proposal is the email rule alone. Capitalising would have damaged the addresses.

## What to record

- The profile for each column and the version of the exception lists that were used.
- Each proposed rule with its evidence, and whether it was kept, changed or dropped.

## Source

- `src/loop_engine/code_nodes/text_conformance_operations.py`: `profile_column`, `induce_pattern` and `duckdb_profile_sql`, which writes five of the counts as one DuckDB query.
- `src/loop_engine/code_nodes/text_conformance.py`: `propose_rules` and the validate endpoint.

Licence: MIT. Compiled from revision 379c271. The operations module uses only the Python standard library.
