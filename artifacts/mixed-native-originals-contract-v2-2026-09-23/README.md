# Original native methods: contract successor

This is a repaired version of the same twelve logical method packages. It adds
**zero new package-count credit**. The current cohort has 96 payload paths and
85 distinct payload byte digests. Approval and hosted counts remain zero.
Use [prepared/items.json](prepared/items.json); the
[prior cohort](../mixed-native-originals-2026-09-23/prepared-final/items.json)
and all its evidence remain unchanged.

The [version binding](successor-bindings.json) maps every prior package digest
to its current digest. Producer family stays `openai`; the recorded authoring
method is now `codex_original_mixed_native_authoring/v2`. No old producer record
or manifest was silently rewritten.

## Why the successor was needed

An independent reviewer found two contract mismatches in the initial cohort:

1. JSON Schema treats finite `1.0` as an integer, while the strict Python integer
   helper rejected its floating-point representation. Scheduling, packing,
   functional-dependency values and token-bucket inputs were affected.
2. The functional-dependency tool ignored an unrelated nested field, but its
   schema incorrectly required every field in every row to be a scalar.

The reviewer otherwise completed 302 bounded executions against the frozen
cohort without finding an algorithm-output defect. That evidence belongs to
the prior cohort and is not substituted for testing the changed bytes here.

## Repairs

JSON decoding now classifies decimal/scientific numeric literals using the
standard-library `Decimal` before binary rounding can hide a fractional part.
Finite mathematically integral values such as `1.0` and `1e0` become Python
integers. Booleans remain distinct. The separate rational-expression grammar
still rejects floating literals because it parses expression text separately.

Numeric tokens are bounded to 1,024 characters and exponents between -4,096 and
4,096. Overflow and nonzero underflow outside finite binary-float representation
are refused. Before converting an integral Decimal to an integer, its adjusted
exponent is bounded to 308. These controls prevent a short literal such as
`1e1000000000` from requesting an enormous integer allocation. Nonintegral values
otherwise retain Python's finite-float representation and remain ineligible for
the methods' strict integer fields.

The functional-dependency schema now permits irrelevant columns containing
bounded JSON. The tool still checks the named determinant/dependent columns for
their bounded scalar domain, required presence and distinct Boolean/integer
values. Those data-dependent checks cannot be expressed solely by a static
schema because the selected column names are supplied in the input. The native
usage guide states that boundary explicitly.

## Evidence on the current bytes

| Check | Result |
| --- | --- |
| [New cases before repair](known-wrong-before-repair.json) | Seven cases were written first; five failed against the unchanged old cohort. |
| [New cases after repair](contract-cases-after-repair.json) | All seven pass, including integral representations and selected versus ignored nested fields. |
| [Full package fixtures](behavior-and-algorithm-mutants.json) | All 58 cases pass on the current package digests; all twelve wrong-algorithm mutations are detected. |
| [Numeric boundary controls](numeric-boundaries-and-guard-controls.json) | Twelve raw-literal/grammar probes pass; two additional guard mutations are detected. |
| [Candidate staging](staging-report.json) | Twelve candidate records acknowledged atomically; zero normal-search hits and twelve title-probe review hits within the first three results. |

The raw-literal controls include oversized exponents, overflow, nonintegral
values that binary floating point would round to an integer, Boolean inputs,
the method's maximum integer, and a value just beyond it. Removing the Decimal
classification admits the near-integer counterexample and is detected. Removing
the selected-column scalar check admits a nested selected value and is detected.

Execution reused the existing minimal Bubblewrap verifier: no mounted home,
no network, cleared environment, read-only candidate script, synthetic input,
two-second CPU limit, 256 MiB memory limit and four-second wall timeout. No model
provider was called, and no native harness installation or loading qualification
was performed.

## Review status and reproduction

The predecessor's independent reviewer is replaying the frozen independent
corpus against this successor. Preparation, deterministic checks and that replay
do not constitute independent admission. The root session owns the later model
review and any publication.

```bash
PYTHONPATH=src python3 artifacts/mixed-native-originals-contract-v2-2026-09-23/verify_packages.py \
  --packages artifacts/mixed-native-originals-contract-v2-2026-09-23/prepared/packages \
  --report /a/new/report.json --mutants
```

The generator and verification files are engineering tools outside the delivery
packages. The payloads reuse the original native package factory without changing
its frozen implementation or adding another storage mechanism or runtime.
