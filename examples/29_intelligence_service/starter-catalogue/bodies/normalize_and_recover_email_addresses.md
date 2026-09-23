# Normalize and recover email addresses

Normalize valid addresses, repair the common ways people spoil an address, and refuse to guess when a value stays invalid or ambiguous.

## When to use it

Use it on email columns that contain wrappers such as `mailto:`, spelled out symbols such as `at` and `dot`, doubled punctuation or mistyped domains.

## Steps

1. Leave null markers unchanged.
2. Replace spelled out symbols from a declared table: the words `at` and `dot` with a space on each side, and the bracketed forms `(at)`, `[at]`, `{at}`, `(dot)`, `[dot]` and `{dot}`. Confidence 0.9.
3. Repair punctuation slips from a declared table: `@@`, `..`, `,com` and `.com.` at 0.9, `@.` and `.@` at 0.85. Remove a trailing period or comma at 0.92.
4. Correct the domain from a declared table of typed domains, each with its own confidence. `gmail.con` gives `gmail.com` at 0.9. `gmail.co` gives `gmail.com` at only 0.7, because it is also a plausible real domain.
5. Normalize: trim, remove a `mailto:` prefix and angle brackets, and write the domain in lower case. The part before `@` is written in lower case by default. A parameter keeps it as written.
6. Refuse a value with more than one `@`, a semicolon, a comma or a space. Leave it unchanged at 0.5 with the reason `ambiguous_address`.
7. Refuse a value whose shape is still invalid. Leave it unchanged at 0.3 with the reason `unrecoverable_shape`.
8. Use the lowest confidence among the repairs. A valid address that needs no change has confidence 1.0.

The three tables are data. A caller can replace or extend them.

## Checks

- `John.Smith at Example dot com` becomes `john.smith@example.com` at 0.9.
- `sam@@example..com,` becomes `sam@example.com` at 0.9.
- `ana@example.com; bo@example.com` is unchanged and escalated.
- A column report keeps exact counts for applied, held, escalated and unchanged values.

## Known-wrong example

A script rewrites `maria@gmail.co` to `maria@gmail.com` without review. The typed domain can be real, so the message would reach another person. This method proposes the rewrite at 0.7. That is below the apply threshold of 0.9, so the value is held and the input is kept.

## What to record

- The tables that were used, with their versions.
- Each repair with its reasons, for example `symbol_word:at` and `domain:gmail.con->gmail.com`.
- The counts for each outcome.

## Source

- `src/loop_engine/code_nodes/field_recovery.py`: `recover_email`, `recover_column` and `RecoveryTables`.
- `src/loop_engine/code_nodes/text_conformance_operations.py`: `email_normalize`.

Licence: MIT. Compiled from revision a0ca182. The two modules depend only on each other and on the Python standard library.
