# Resolve a literal named template

This candidate supplies a reusable tool for one focused task. Preserve the
current task assignment when composing this instruction with a per-step brief.

## First steps

1. Confirm that the task needs this exact method: Replace declared ${name} placeholders exactly once with supplied literal strings and refuse missing or unused variables.
2. Read `contracts/input.schema.json` and the method limits below. Build an input
   object from the supplied evidence; do not guess missing values.
3. After the host authorizes local execution, run the selected immutable script
   with JSON on standard input. The example demonstrates the interface:

   ```bash
   python3 -I -S -B tools/resolve_literal_named_template.py < examples/input.json
   ```

4. Compare the result with `contracts/output.schema.json` and the task's own
   acceptance rule. The synthetic example output is in `examples/output.json`.
   A successful structure does not make the supplied facts correct.

## Method limits

Replacement text is not rescanned. This does not escape shell, HTML, SQL or another target syntax. Treat the result as text; a separate context-aware encoder is required before any such use.

The program accepts at most 32 KiB of UTF-8 JSON and document depth 16. It refuses
duplicate keys, non-finite numbers, extra root fields and method-specific invalid
inputs. It emits at most 64 KiB of JSON. Refusal is exit 2 with
`{"error":"invalid_input"}`; success is exit 0 with the result object. A host
must bound time and memory and supply only approved input. The script reads no
task files, credentials or environment values and makes no network or subprocess
calls. The interpreter reads the script and standard-library modules. It writes
only standard output. No instruction here grants execution authority.

## Acceptance and provenance

`verification/cases.json` contains original synthetic success and refusal cases.
They test this method, not a customer's real outcome. This package is original
candidate work by Codex (OpenAI family), method
`codex_original_mixed_native_authoring/v1`. No third-party code or prose was
copied. The included repository MIT notice applies to the authored candidate;
it is not a claim of rights over outside task data. Independent exact-byte
review, native loading and task acceptance remain required.
