# Engine selection for every engine slot

Every functional component keeps one fixed, typed and versioned edge, and the
engines behind it are chosen at run time by one procedure. This guide covers
that procedure, which lives in `loop_engine.core.engines.selection`, the
attempt assessment in `loop_engine.core.engines.fallback`, and the evidence
ranking in `loop_engine.core.engines.evidence`. The design, with its reasons,
is [Engines behind fixed edges](../../architecture/ENGINES-BEHIND-FIXED-EDGES.md),
sections 8 and 10. Roadmap step S-6.30 owns the work.

The procedure is generic. A slot adds only its own requirement screen; every
other rule is the same for the step executor, the record store, model access
or a slot added later.

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

Selection is not a runtime type. `select_engine_as_loop` runs the decision
inside one deterministic Practitioner Loop with the exact profile
`practitioner.code_execution`, Spawned by the Loop that owns the work, or
Starting when nothing owns it yet. The registered boundary is "component
engine selection".

## What selection reads

```text
EngineSelectionRequest, one frozen object with one digest
├── the slot record (engine_slot/v1) and the host's slot configuration
├── the scope key and the exact scope of the step (operation contract, profile, evaluation)
├── candidates: one EngineCandidate per installed engine
│   ├── the host's installation, with its installation digest
│   ├── the descriptor the engine's own registry projected
│   └── its one qualification record, if any
├── the owning Loop's authority as eligibility reads it (SelectionAuthority)
├── Loop and harness preferences (engine_selection_override/v1)
├── the approved evidence snapshot, when the policy binds one
└── the phase: initial, or fallback with the transition and the authority consumed
```

The request digest is written into the decision, so every decision names
exactly what the selector read. `engine_selection_request/v1` is the shape
that digest covers.

## The procedure

1. **The host policy is read against its slot record.** `policy_widening`
   refuses a policy that asks for more than the slot allows: fallbacks on a
   slot whose ceiling is none, a failure kind the slot does not report, an
   installation of a kind the slot does not declare, a ranking engine the
   release does not ship, or an evidence minimum below the slot's floor. The
   decision is then `refused_policy`.
2. **The universe** is the installations the host declared and switched on.
   An engine a registry offers but the host did not install is refused when
   the request is built.
3. **Eligibility.** `screen_candidate` runs the screens in a fixed order and
   records every refusal, not only the first: `engine_retired`, then
   `engine_not_active`, `engine_deprecated_as_initial` or `engine_rejected`,
   then `engine_kind_not_allowed`, `edge_version_unsupported`,
   `engine_unavailable`, `engine_unqualified`, `qualification_expired` or
   `qualification_scope_mismatch`, the slot's own
   `capability_requirement_unsatisfied`, `permission_not_granted` and
   `budget_requirement_unsatisfied`. A screen removes and never reorders.
4. **The declared order** is the policy's initial engines that are eligible.
   When none is eligible and the policy falls back on an unavailable engine,
   the first eligible fallback serves before any dispatch.
5. **Preferences.** A Loop or a harness may pin, exclude or prefer, within the
   kinds the host permits for that sender. A preference can only narrow or
   reorder eligible installations. A pin to an ineligible engine refuses the
   request; nothing is substituted.
6. **Ranking** runs through the existing preference boundary. The declared
   order is always the last ranking engine. When the policy binds approved
   evidence, `MatchedEvidenceRanking` orders the declared engines by verified
   outcome first and by the rule's objective only to break ties. Below the
   rule's minimum of matched, reviewed records for any engine it raises
   `InsufficientEvidence`, the declared order decides, and the embedded
   ranking record becomes `configuration_preference_decision/v2`.
7. **The decision** is `engine_selection_decision/v2`. It lists every
   installed and enabled engine, every refusal, the order with and without
   preferences, the ranking, the evidence use, the chosen engine with
   propensity one, the fallback chain, and its selection basis and path.

## Pinned, preferred and automatic

The selection basis says how much freedom one choice had. It is derived and
checked, never asserted.

| Basis | When | Example |
|---|---|---|
| pinned | A pin applied, or a policy with one initial engine, no fallback and the declared order only | A run's caller pins one installation for that run |
| preferred | The declared order, narrowed or reordered by permitted preferences | The host's order with a harness preference for its second engine |
| automatic | Approved evidence at or above the slot's floor ranked the choice for the exact scope | A nightly step whose reviewed trials favor its second engine |

The selection path names how the engine was reached: `first_choice`,
`evidence_reordered`, `override_prefer`, `override_pin`, a fallback path
named by its failure kind, or `no_choice` when nothing was chosen. Every path
is deterministic, so its propensity is one.

## Recording, revalidation and fallback

`record_decision` writes the decision into the owning Loop's ledger before
any dispatch, in existing raw event kinds and families:
`capability.search.started` for the request, `capability.search.completed`
for the full decision, which carries every refusal, and `capability.selected`
for the bound engine. Each event carries the field `component` with the value
`engine_selection`. No event kind is added. A dispatch names the decision digest, and
`require_prior_decision` refuses one without it (`no_prior_decision`).
Immediately before use, `revalidate_binding` compares the chosen engine's
descriptor and installation digests with the decision; a replaced binary or
changed settings end the attempt as `engine_changed_after_selection`, never
as a fallback.

After an attempt, `assess_engine_attempt` reads what the envelope observed in
an `EngineAttemptOutcome` and returns a `FallbackAssessment`. Uncertain
effects or uncertain accounting stop the sequence. A terminal failure kind, a
pinned choice, a failure kind the policy does not name, or a slot ceiling
that forbids a second engine stop it too. Otherwise `fallback_request` builds
the next request, which carries the consumed authority forward and never
replenishes it.

## Evidence records

| Record | What it holds |
|---|---|
| `engine_evidence_rule/v1` | The method, the objective, the minimum matched records, the evaluator and the window; no threshold has a default in code |
| `engine_trial_evidence/v1` | One measured trial of one installation on one exact scope; an unknown count stays unknown |
| `engine_evidence_review/v1` | An independent review bound to one exact trial; an engine never reviews its own trial |
| `engine_evidence_snapshot/v1` | The approved trials and reviews selection reads at one moment |

Only the matched-quality method is built. The paired efficiency method is
designed and refused with `evidence_method_not_built` until it is.

## Checks

```bash
PYTHONPATH=src python3 -c "from loop_engine.core.engines.selection_checks import self_test; print(self_test()['all_passed'])"
PYTHONPATH=src python3 -c "from loop_engine.core.engines.evidence_checks import self_test; print(self_test()['all_passed'])"
```

Each check names its known-wrong case, and each removed-guard control deletes
one guard and passes only when its check then fails. One check replaces the
process, socket and web request functions with ones that fail, and selection
still decides: selection starts nothing and calls no model.
