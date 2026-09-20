# Code Intelligence admission, inline identity, and retrieval repairs

Date: September 19, 2026. Kind: implemented repair and scoped verification.
The original intelligence audit and its probes remain a pre-repair snapshot.
This record describes the subsequent changes and their current evidence.
The owner's later direction says there are no launched users and removes the
requirement for legacy compatibility. Active readers now require current
contracts. Earlier compatibility readers added in this batch were removed.

Direct Code Intelligence execution now requires the existing `CapabilityAuthority` to
resolve a current registered asset and its exact admission record before
materialization. The selected reference must match the authoritative identity,
version, complete handshake, body locator, body digest, and qualification
digest. The entry point must be among the admitted entry points. A candidate,
a populated admission-reference string without authority, missing records,
changed contracts, altered stored evidence, and revoked admission all refuse
before the materializer runs.

The direct helper's installed executor runs pure deterministic callables.
It reports an unavailable executor for declared effectful work or modes it
does not support. A known licence state is required. Effectful and model-led
work still needs its appropriate governed executor and authority; these
changes do not redefine the modes supported by the Loop runtime.

## Current qualification and reference contracts

| Record or interface | Current behavior |
|---|---|
| `code_asset_spec/v2` | Carries `qualification_version` equal to `code_asset_qualification/v2`. Its qualification digest includes the exact separate data references as well as the existing dependency, code-body, contract, effect, mode, and entry-point identity. |
| `code_asset_admission/v2` | The current exact proof record. Changing a data reference or dependency invalidates the old proof. The admitted code body and separate data references must have immutable typed identities. |
| Other Code Intelligence schema or qualification versions | Active readers refuse with typed unsupported-version or requalification diagnostics. Historical artifact bytes are preserved, but are not automatically converted into current runtime records. |
| `IntelligenceItemHandshake.qualification_digest` | Small identity field that binds a selected Code Intelligence reference to its qualified configuration, including separate data references. |
| `intelligence_item_ref/v2` | The active reference wire shape. Its reader requires the explicit version marker and current handshake fields. It does not map `loop_ref`, `role`, or `modes` wire aliases. |
| Current references without a body digest | May represent unavailable metadata, but refuse materialization with `intelligence_payload_identity_unavailable`. Content identity cannot be recovered from a locator alone. |

Inline intelligence now has one shared value projection used during both
selection and loading. Selection measures the exact finite JSON value and
preserves its version. Materialization recomputes that value's digest and
rejects changed content, including a supplied materialization object that
claims the old digest for different text.

`SolverStore` search cards now include measured inline digests for the explicit
layer projections. They contain no body. The caller chooses the layer when
constructing its typed reference; the store does not infer the layer from a
title or tag. This preserves the older store-search-to-reference path while
giving it a measured body identity. New cards produce current versioned
references; they do not enable an older wire reader.

## Retrieval behavior

`top_n` now limits the combined four-layer result and reference lists, and it
must be a positive integer when supplied. Required facets establish the
eligible set before rank fusion. A filtered search considers the complete
local backend ranking so a short initial pool cannot hide an eligible match.
Preference bonuses participate in sorting before final truncation.

This complete local ranking is a correctness tradeoff. It can require more
work than the earlier small pool; no performance improvement is claimed.
Backend filter pushdown remains a separate optimization to qualify against
the same result contract.

SQLite and LanceDB retrieval exceptions now raise `RetrievalUnavailableError`
instead of returning an empty list. The four-layer boundary preserves that
unavailability after the canonical search Loop records its failure. A valid
empty search remains a normal empty result.

One previous fixture requested three results while requiring all four layers
to appear in four results. Its requested count was corrected to four. The
new independent one-result check still rejects the old multiplied-limit
behavior; the correctness requirement was not weakened.

## Changed paths

- `src/loop_engine/core/code_intelligence_assets.py`
- `src/loop_engine/core/code_intelligence_asset_checks.py`, a new check helper
  inside the existing Code Intelligence boundary; the original collected
  `self_test` remains the facade.
- `src/loop_engine/loop/loop_capsule.py`
- `src/loop_engine/core/intelligence_layers.py`
- `src/loop_engine/core/retrieval.py`
- `src/loop_engine/core/reusable_capability_resolution.py`, which passes the
  existing authoritative admission into direct execution.
- `src/loop_engine/core/intelligence_portfolio_checks.py`, whose callable
  fixtures now install exact authoritative test admission.
- `src/loop_engine/core/store_serve.py`

`intelligence_portfolio.py` was inspected and tested but did not need changes.
No solve dependency construction, export code, solutions-space code, roadmap,
generated map, or manifest was edited in this batch.

## Verification

[The current-contract verification results](intelligence-current-contract-verification-results.json)
contain exact source hashes. The [runner](intelligence-access-verification.py)
executes the real public reference and execution paths with bounded fixtures,
and replaces mutant callables only within its own process.

All 175 owning and dependent checks passed. They cover Code Intelligence assets, selected
references, four-layer queries, retrieval, the older store, intelligence
portfolios, governed reuse, capability Loops, Intelligence Loops, and the
Practitioner's orientation capability surface. All 15 mutants were detected.
They remove admission, dataset binding, qualification identity, unsupported-version
refusal, stored-evidence integrity, selected-contract checks, executor limits,
inline-body integrity, version preservation, result bounds, facet handling,
preference sorting, or explicit backend failure.

The [first mutation attempt](intelligence-access-initial-mutation-attempt.json)
is retained. It passed 168 then-current checks but detected only ten of eleven
mutants. The missed mutant patched a function's defining module while the
test helper retained an earlier direct-import alias. The runner now patches
those exact consumer aliases too. At that point the stale-proof refusal and its
known-wrong expectation were unchanged, and the corrected run detected the
mutant. The owner's subsequent direction removed the old readers entirely;
the final matrix instead checks refusal of unsupported active contract versions.

No live provider or cloud operation ran. The existing retrieval tests used
installed local embedding weights with offline mode enabled. There is no
new model-quality, deployment, or full-system benchmark claim. No commit was
made. The coordinating agent owns full-tree integration, generated-map
updates, clean installation, and final release verification.

## Remaining boundaries

Materializers and binders remain host-supplied adapters. Exact stored admission
does not itself authenticate an external verifier organization or execute its
tests again; those responsibilities belong to the existing qualification and
host authority process. This batch does not install a general package
downloader, repository sandbox, or effectful direct Code executor.

The default solve catalog's source scope, orientation reference projection,
tenant disclosure rules, persistent hosted metering, and export verification
remain separately owned work. The repair addresses INT-02, INT-03, INT-07,
and the result-bound, filtering, preference, and failure-state parts of INT-10.
The broader audit is not complete merely because these checks pass.
