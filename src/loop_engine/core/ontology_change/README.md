# Ontology change planning

Kind: functional component, engine slot `ontology_change_planning`
(planned: its engines, edge and conformance kit exist; no Loop calls it yet,
so it has no registered work boundary). It follows the
[functional component standard](../../../../docs/architecture/FUNCTIONAL-COMPONENT-STANDARD.md)
and came from the owner's direction of October 5, 2026 to learn from, recreate,
fork and improve the ideas the owner shares. The prior-art record is
[Open Ontologies prior art](../../../../docs/research/OPEN-ONTOLOGIES-PRIOR-ART-2026-10-05.md).

## Runtime classification

```text
Operational runtime type
└── Loop
    ├── Operational relationship
    │   ├── Starting
    │   ├── Spawned by
    │   ├── Queried by
    │   ├── Retrieved by
    │   └── Connected from
    ├── Role
    │   ├── Practitioner
    │   ├── Intelligence
    │   └── Solution
    ├── Versioned role profile
    ├── Purpose and domain categories
    ├── Run mode
    │   ├── deterministic
    │   ├── hybrid
    │   └── non-deterministic, with model-led semantic work
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition
    ├── Exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the selected mode permits a model
    └── Run History records
```

A plan is computed for a Loop that owns the step; the component is not a
runtime, a role or a mode. Its engines are adapters that the owning Loop
uses, and choosing one grants no authority.

## What it does

```text
ontology_change_planning
├── edge (contract.py, edge version 1)
│   ├── ontology_change_request/v1   base ontology, its digest, the change, profile, bounds, locks
│   ├── ontology_change_plan/v1      bound to the base and proposed digests; new and lost entailed
│   │                                triples, affected terms, locks checked and touched, the verdict
│   │                                word, checked traces, plan_digest
│   └── ontology_change_failure/v1   one closed code: base_digest_mismatch, change_invalid, ...
├── envelope (component.py): read, bind the digest, screen and select through
│   engine_selection_decision/v1, dispatch, check every listed trace, write the plan
├── engines (engines.py is the factory table)
│   ├── baltor_native_rules   native_engine.py: RDFS and OWL 2 RL closure in the standard library
│   └── open_ontologies_cli   open_ontologies_engine.py: Open Ontologies v2.0.1, pinned by commit
│                             d1187190 and the asset's SHA-256, run in bubblewrap with no network
├── store (store.py): compare-and-swap apply, enforced locks, approval naming the plan's digest,
│   checked rollback, an append-only journal
├── trace_checker.py: re-derives every step by pattern, shares no code with any engine
└── conformance.py: the kit both engines pass alone, with known-wrong controls
```

Rule tables: `rdfs` is rdfs2, rdfs3, rdfs5, rdfs7, rdfs9 and rdfs11; `owl-rl`
adds prp-trp, prp-symp, prp-inv1, prp-inv2, eq-sym, scm-eqc1, scm-eqp1,
scm-dom1, scm-dom2, scm-rng1 and scm-rng2. These are the seventeen fixed-arity
rules Open Ontologies v2.0.1 evaluates for the same profile names, with the
premise order its Lean checker reads, so both engines compute the same
closures and either engine's traces can be checked by either checker.

## What it fixes in the outside project

| Gap in Open Ontologies v2.0.1 | Here |
|---|---|
| A plan stores the proposed Turtle and apply recomputes against the live store, so a store changed between plan and apply is overwritten | The plan names the base digest; apply is a compare-and-swap and refuses `stale_base` |
| Locked IRIs only appear as warnings in the plan | Every term the store locks must be checked by the plan and untouched, by assertion or by entailment, or apply refuses `locked_term` |
| Any client that can call `onto_apply` applies; `force` skips the monitor | Apply needs an approval reference that names the plan's digest; there is no force mode |
| Rollback clears the store and loads a labelled snapshot | Rollback restores only while the store still holds the state the apply wrote, and checks the restored digest |
| The certificate covers the engine's own run | Every listed consequence's trace is checked by an independent checker before the plan exists |

## Selection

The declared order is the native engine, then the adapter
(`engine_selection_policy/v1`). Every installed engine is screened: enabled,
available (the adapter needs Linux x86_64, `/usr/bin/bwrap` and the pinned
file), able to take the profile and the graph (the adapter refuses blank
nodes), and, when the host requires evidence, holding a passing conformance
report for its exact descriptor digest. The decision is recorded as
`engine_selection_decision/v1` before dispatch; a failure kind the policy
names moves to the next eligible engine with a fallback decision. Evidence
gates eligibility and never ranks: the kit's own results are not reviewed
evidence.

## Checks

```bash
PYTHONPATH=src:tools python -m unittest tools.test_ontology_change
PYTHONPATH=src python -c "from loop_engine.core.ontology_change.conformance import self_test; print(self_test())"
```

To run the adapter's half, point `LOOP_ENGINE_OPEN_ONTOLOGIES_BINARY` at the
release asset `open-ontologies-x86_64-unknown-linux-gnu` of v2.0.1, and
`LOOP_ENGINE_OPEN_ONTOLOGIES_CHECKER` at `oo-cert-x86_64-unknown-linux-gnu` for
the Lean cross-check. Without them that half is reported as not tested, with
the reason. Nothing here downloads or re-hosts the binaries.

## Limits

- No Loop calls the component yet, so the slot is planned and has no boundary.
- Seventeen rules: no `owl:sameAs` replacement, no list rules, no clash
  detection, no description-logic reasoning. A conservative verdict says only
  that this rule table derives nothing new over the base's names.
- The adapter refuses blank nodes, and its traces are the binary's first
  derivations, which may differ between runs.
- The store is one folder on one machine; it is not the record store slot.
