# Candidate review: reconcile-inventory-availability

Status: candidate only. No admission, licence, native-use result, or benefit claim is attached to these bytes.

- Original source basis: Written in original words for this batch from general inventory-accounting reasoning after inspecting the 123 starter bodies and first 24 packages. The [Agent Skills specification](https://agentskills.io/specification) informed layout only. No copied company policy or external taxonomy.
- Job, company archetype, and project facets: inventory analyst or fulfillment manager; a retailer, distributor, or parts operation; stock-availability reconciliation before an allocation or storefront rollout.
- Model applicability: general text-capable harnesses; benefit with any specific model is unmeasured.
- Conceptual typed input: `StockKey`, `Cutoff`, `OnHandObservations`, `Reservations`, `Holds`, `AvailabilityRule`.
- Conceptual typed output: `AvailabilityReconciliation` with included and excluded quantities, active commitments, calculated availability, displayed value, and exceptions.
- Effect intent: read-only analysis. No reservation, transfer, release, purchase, or sale is authorized.
- Positive fixture: At one location and cutoff, ten eligible units are on hand, four are actively reserved, and two are under a separate sellability hold. Under a supplied rule that subtracts both, availability is four.
- Known-wrong fixture: A display reports ten available because it equates physical on-hand with sellable stock, or subtracts the same reservation twice under two identifiers. Either conclusion fails the keyed reconciliation.
- Nearest overlap: Starter `check_a_table_join_before_trusting_it.md` prevents join multiplication. First-batch `validate-aggregate-grain` prevents summing stock snapshots across dates. This candidate reconciles stock status, active commitments, and availability at one cutoff and location.
- Limitations: Inventory rules differ by organization, including in-transit and consigned goods. A reviewer should test expired reservations, location pooling, and a hold that is already excluded from eligible stock.
- Customer search phrasings: "Why does the site say ten units are available when six are already committed or held?"; "Are we selling stock twice because reservations are missing from this availability number?"
