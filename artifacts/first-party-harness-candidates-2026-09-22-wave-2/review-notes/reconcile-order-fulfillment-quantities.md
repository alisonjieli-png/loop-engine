# Candidate review: reconcile-order-fulfillment-quantities

Status: candidate only. No admission, licence, native-use result, or benefit claim is attached to these bytes.

- Original source basis: Written in original words for this batch from general order-line accounting reasoning after inspecting the 123 starter bodies and first 24 packages. The [Agent Skills specification](https://agentskills.io/specification) informed layout only. No employer policy or third-party procedure was copied.
- Job, company archetype, and project facets: fulfillment analyst or customer operations specialist; a retailer, distributor, or manufacturer; backlog audit or order-to-shipment reconciliation.
- Model applicability: general text-capable harnesses; no measured benefit for a particular model.
- Conceptual typed input: `AcceptedOrderLines`, `FulfillmentEvents`, `Cutoff`, `RecognitionRules`, `UnitRules`.
- Conceptual typed output: `OrderLineQuantityLedger` with recognized dispositions, open quantities, unmatched events, and exceptions.
- Effect intent: read-only analysis. No shipment, cancellation, refund, or correction is authorized.
- Positive fixture: An accepted order line has ten units. Two units are effectively cancelled, and two distinct shipments contain four and three units. With a supplied rule that these dispositions close quantity, one unit remains open.
- Known-wrong fixture: The four-unit shipment event is retried with the same event identity. Counting both copies yields a negative open balance and a false over-shipment; the repeat needs the supplied idempotency rule and cannot become another shipment.
- Nearest overlap: Starter `make_a_data_pipeline_safe_to_run_again.md` concerns safe reruns of a writer. First-batch `rebuild-state-from-ordered-events` reconstructs an entity's status. This candidate reconciles quantities and partial dispositions at the order-line grain, where one status such as "shipped" hides an open balance.
- Limitations: Return and substitution rules vary. A reviewer should test cross-line allocations, cancelled-after-shipped events, and returns that may or may not reopen the obligation.
- Customer search phrasings: "Which part of this order is still open after partial shipments and cancellation?"; "Are retry events making our fulfilled quantity larger than the order?"
