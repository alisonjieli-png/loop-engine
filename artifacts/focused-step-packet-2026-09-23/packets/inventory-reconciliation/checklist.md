# First actions and acceptance

## Before work

- [ ] Owning host checks the expected run, step, context version, state version and exact payload digests.
- [ ] Owning host supplies real sandbox and effect authority; this candidate packet supplies none.
- [ ] Check that every movement uses the same unit and period and that each required quantity is present.
- [ ] Compute closing units as opening plus receipts minus shipments plus adjustment; compute available units as closing minus held.
- [ ] Compare computed available units with reported available units; return a discrepancy without changing inventory.

## Before handoff

- [ ] The output SKU equals the supplied SKU; every arithmetic term comes from this input.
- [ ] The discrepancy is computed available units minus reported available units; zero means matches, otherwise needs_review.
- [ ] Do not mutate any stock balance. A host verifier checks arithmetic and scope before accepting a result.
- [ ] Owning host checks the JSON Schema and the separate semantic acceptance conditions.
- [ ] Record remaining uncertainty; a proposed answer is not an accepted result.
