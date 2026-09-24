# Tactical generation binding evidence

September 23 to 24, 2026, United States Eastern. Three recorded model calls,
all to the owner's Tactical Engineering server under its TLS trust contract.
No credential is written in any file here. The
[binding record](../../docs/verification/TACTICAL-GENERATION-BINDING-2026-09-23.md)
explains the results.

- `trust-contract-listing-check-1.json`: a model listing through the new
  contract, and a wrong-pin control refused before any request. No model call.
- `measure_output_capacity.py`: the measurement script. It sends one streamed
  request per run and writes one secret-free record.
- `capacity-measurement-call-1.json`, `-2.json` and `-3.json`: the three
  calls. Calls 1 and 2 ended by the model itself. Call 3 streamed 105,574
  tokens, stalled, and was closed by the client after 300 seconds with no
  stop reason.
- `metadata-reads-after-measurement-1.json`: read-only routes. None states a
  sequence, input or output limit.
- `capacity-record.json`: `endpoint_output_capacity/v1` with an unknown
  maximum, every observation, and what the owner must supply.
- `family-evidence.json`: `generation_producer_family_evidence/v1` for the
  family `google`, with the Gemma 4 tokenizer reference and its limits.
- `check_removed_guards.py` and `removed-guards-*.json`: 21 in-memory
  removed-guard controls, all detected, with no provider call. The
  `20260924T050818` record ran before two catalogue-cited files were
  restored; `20260924T052546` binds the final source.
- `deferred-cited-source-edits.patch`: the failure-class and settings-loader
  edits that wait for the next starter catalogue re-anchor, because the
  catalogue pins both files' exact bytes.

Run the controls from the repository with the repository's Python
environment:

```sh
PYTHONPATH=src:tools python artifacts/tactical-generation-binding-2026-09-23/check_removed_guards.py
```
