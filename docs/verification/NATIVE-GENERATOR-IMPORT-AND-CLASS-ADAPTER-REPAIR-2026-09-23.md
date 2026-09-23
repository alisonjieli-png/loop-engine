# Native generator import ownership and class adapter repair

September 23, 2026. This isolated patch starts from the integration checkout at
`1920296c00ced18e47992ae05237f4a2923666f0` plus its captured uncommitted assembly.
The exact before/after source hashes are in the
[repair evidence](../../artifacts/import-owner-repair-2026-09-23/README.md).
No provider calls, model calls, installation, generation approvals or integration
checkout edits occurred.

## Known-wrong cases

The parent's exact combined command reproduced **69 tests, one error**. Native
review imported `prepare_harness_candidates` by its bare name while generation
and tests imported `tools.prepare_harness_candidates`. The preparation script's
`sys.modules` alias then replaced the canonical slot during the bare import.
References already held by tests still named the earlier `PreparationError` class.
The actual duplicate-JSON refusal was correct, but its exception identity no longer
matched the owning contract.

Fresh-process controls reproduce both import orders. An adjacent bare staging
import in ingestion produced the same duplicate class problem. The old `python -m`
preparation entry also returned a traceback for an invalid native file digest rather
than its declared JSON refusal. Those failed controls remain beside their successors.

The generator's adapter hashing also assumed that every non-module adapter was an
instance. For the class returned by `CustomEndpoint.make_adapter`, that hashes
`type`, which has no source file. A new class-adapter check failed before the repair.
A valid adapter with no inspectable source now receives an explicit refusal rather
than an uncaught reflection error.

## Changes

- All active preparation and staging imports in these tools use `tools.*` as owner.
  Native review and ingestion no longer load duplicate bare modules.
- Preparation and staging CLI entries delegate to canonical `main` before defining
  another copy of their contracts. File-path and `python -m` invocation share the
  same definitions. The former `sys.modules` alias is removed.
- Generation, review and ingestion explicitly make the repository package root
  available where their documented file-path commands need it. This preserves
  outside-repository invocation with only `src` on `PYTHONPATH`.
- Adapter source binding distinguishes modules, classes and instances. A class is
  hashed through its owning source file. Missing source yields
  `implementation_source_unavailable`; changed bytes still refuse a resumed run
  before the injected gateway is called again.

No compatibility aliases, exception-class aliases, alternate journals or provider
routes were added. Existing serialized record shapes remain unchanged. The generator
continues to bind implementation digests and refuses changed resume bindings.

## Verification

The exact combined command now passes **72 tests**:

```sh
PYTHONPATH=src python -m unittest \
  tools.test_generate_original_native_candidates \
  tools.test_prepare_native_harness_candidates \
  tools.test_candidate_review_native_calibration \
  tools.test_provider_model_identity_reporting
```

The adjacent ingestion and native-review suites pass **46 tests**. Five direct CLI
help commands run successfully from outside the repository. A native-review CLI
preflight there returns its typed missing-catalogue refusal without creating a ledger.
Three in-memory class/source guard mutations are all detected. The eight changed
source modules introduce zero Ruff diagnostics; the new fault runner is clean.

The class adapter tests inject a gateway and make no live endpoint request. They
prove source binding and resume refusal, not Tactical connectivity or model capacity.
