# Configuration dimension discovery: review addendum

The owner clarified that the configuration inventory must extend beyond the
dimensions originally listed. The first 25 entries are a required baseline,
not an exhaustive list or a maximum. Future agents must actively identify
missing choices and useful refinements instead of waiting for the owner to
name them.

The owner reports arranging a Claude Fable 5.1 review. No review findings have
been received or attributed to that reviewer in this addendum. This document
supplements the [earlier review handoff](CLAUDE-FABLE-5.1-REVIEW-HANDOFF-2026-09-13.md)
and [frozen review archive](../../artifacts/fable-review-20260913-p75Wml/source-review.zip).
The archive and its test reports remain unchanged. Read this addendum with
the current [configuration dimension document](../architecture/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md),
which retains the complete behavioral explanation and classification trees.

## Additional review scope

The configuration document records additional proposals. Some separate
choices already combined in broad baseline entries; others affect several
entries at once. They include context compression and ordering, ambiguity and
uncertainty, information freshness, caching and invalidation, delivery
guarantees, reasoning and action methods, checkpoint continuity, cancellation,
privacy, reproducibility, exploration, evaluator calibration, configuration
binding, downstream feedback, and learning transfer.

Each proposal names initial and fallback decisions and an existing boundary
to inspect. A named boundary is a starting point for review, not proof that
the proposed behavior exists. The proposals are not independently
approved new capabilities. Their number is not a progress measure, and the
expanded list is still not exhaustive.

The machine-readable design inventory is version 1.1.0 under
`loop_dimensions.configuration_design` in `architecture.yaml`, with an exact
packaged copy. It marks the inventory non-exhaustive and the additional
entries proposed for review. The baseline-preservation check allows additions
while still refusing omission of the original required entries.

## Questions for the review

1. Which controllable choices can change the outcome while the harness and
   model remain fixed? Distinguish settings from observed task facts, derived
   metrics, categories, and permission grants.
2. Which proposed dimensions already have an adequate typed representation?
   Reuse that representation. Split or extend an existing contract only when
   a concrete missing decision requires it.
3. Which interactions make individually valid settings fail together?
   Examine context compression with model choice, process reuse with privacy,
   streaming with cancellation, and concurrency with shared authority.
4. For each useful proposal, what is the initial choice, ordered fallback
   policy, transition trigger, compatibility rule, and decisive experiment?
   Preserve failures and counterexamples. Treat unsupported combinations as
   explicit refusals, not as unfinished configuration to guess at runtime.
5. What else is missing from both the original inventory and these additions?
   Classify suggestions as an existing representation, refinement, missing
   choice, interaction, or unresolved question. Record why an idea is accepted,
   merged, deferred, or rejected.

Keep the design space open while freezing each experiment's comparison
population and candidate settings. Extensibility does not permit unknown
executable fields, new runtime types, weaker contracts, automatic promotion,
or broader effect authority.

## Change and evidence boundary

This follow-up changes documentation, the passive architecture inventory,
and its development checks. It does not implement the proposed mechanisms,
call a provider, or modify production Python. The earlier source and
clean-installation counts belong to their original snapshots. They are not
new qualification of these proposals.

While another reviewer is inspecting the shared workspace, preserve their
changes and avoid silently replacing the source they are reviewing. New
review findings must identify their actual source revision and working-file
digests rather than assuming the earlier archive is the latest state.
