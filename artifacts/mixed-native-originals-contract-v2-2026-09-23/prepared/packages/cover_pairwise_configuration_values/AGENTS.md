# Cover pairs of configuration values

This candidate supplies a reusable tool for one focused task. Preserve the
current task assignment when composing this instruction with a per-step brief.

## First steps

1. Confirm that the task needs this exact method: Construct deterministic test rows that cover every pair of values across two to six independent configuration factors.
2. Read `contracts/input.schema.json` and the method limits below. Build an input
   object from the supplied evidence; do not guess missing values.
3. After the host authorizes local execution, run the selected immutable script
   with JSON on standard input. The example demonstrates the interface:

   ```bash
   python3 -I -S -B tools/cover_pairwise_configuration_values.py < examples/input.json
   ```

4. Compare the result with `contracts/output.schema.json` and the task's own
   acceptance rule. The synthetic example output is in `examples/output.json`.
   A successful structure does not make the supplied facts correct.

## Method limits

Uses greedy uncovered-pair selection. The result is not claimed to use the minimum number of rows. Constraints between factors are unsupported and must be resolved before calling.

The program accepts at most 32 KiB of UTF-8 JSON and document depth 16. It refuses
duplicate keys, non-finite numbers, extra root fields and method-specific invalid
inputs. Finite mathematically integral numeric literals such as 1.0 are normalized
to integers before method validation; Booleans stay distinct. Nonintegral values
do not become integer fields through rounding. Decimal/scientific numeric tokens
have at most 1024 characters and an exponent between -4096 and 4096. Overflow and
nonzero underflow beyond a finite binary float are refused before conversion;
nonintegral values otherwise use Python's finite float representation.
It emits at most 64 KiB of JSON. Refusal is exit 2 with
`{"error":"invalid_input"}`; success is exit 0 with the result object. A host
must bound time and memory and supply only approved input. The script reads no
task files, credentials or environment values and makes no network or subprocess
calls. The interpreter reads the script and standard-library modules. It writes
only standard output. No instruction here grants execution authority.

## Acceptance and provenance

`verification/cases.json` contains original synthetic success and refusal cases.
They test this method, not a customer's real outcome. This package is original
candidate work by Codex (OpenAI family), method
`codex_original_mixed_native_authoring/v2`. No third-party code or prose was
copied. The included repository MIT notice applies to the authored candidate;
it is not a claim of rights over outside task data. Independent exact-byte
review, native loading and task acceptance remain required.
