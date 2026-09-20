# Practitioner runtime components

Kind: internal implementation boundary inside Core Architecture.

The canonical `Loop` owns execution. This package separates the adaptive
Practitioner's capability descriptions and stage observation machinery from
its request records and run-service lifecycle.

| Module | Owns | Does not own |
|---|---|---|
| `capabilities` | The one existing adaptive capability descriptor collection. | Selection, permission grants, execution, or another registry. |
| `observations` | Stage fingerprints, exposure, assistance decisions, and bounded instrumentation failure records. | Independent acceptance, promotion, persistent storage, or another runtime. |
| `provisioning` | Immutable assignment choices, selected catalogue reference snapshots, guardrail snapshots, and preparation authority. | Resource admission, body installation, native loading, task effect grants, or another catalogue. |

Callers import capability descriptions and observation helpers from their
owning modules. There are no compatibility-only forwarding modules. Helpers
receive the existing run services and use the existing typed records and
owning Loop ledger. They must not import `core.adaptive_practitioner_records`,
which would recreate the dependency cycle this extraction removes.
Shared validation errors live in
`core.adaptive_practitioner_validation`.

Add a component here only when it has a coherent ownership boundary and
existing public-path checks. Update the architecture map with every module.
Do not infer dispatch or authority from its filename or descriptive text.
