# Author repair: order eligibility before scarce-stock priority

Kind: candidate-only author repair record, September 23, 2026 local time. It responds to the [independent read-only QA finding](../../docs/verification/FOURTH-ORIGINAL-HARNESS-INDEPENDENT-QA-2026-09-22.md). This document is a request for independent rereview, not an approval.

The [blocked successor manifest](manifest-rereview-blocked-2026-09-23.json) has SHA-256 `2cb6c04918dc7aa05b331186f7120b8f020542a7afcd82843456fcdfb58c4696`. Its quantity and arrival-time repairs passed the prior independent counterexamples, but its order hold, item and location gate had disappeared. A subsequent [eligibility draft manifest](manifest-eligibility-draft-2026-09-23.json) has SHA-256 `cd9aa2174ec956b7ebd2884609a6d77e0e8cba2bf592051ebfa587a354d9eef3`; author self-check found it had not named each order's priority status as an input. The current [successor manifest](manifest.json) has SHA-256 `f5790bedba8efded222d87a5d819a44d4def6dadb8982bd529e23a4c0437791a`. Only [the allocation skill](packages/data/allocate-scarce-stock-by-promised-service/SKILL.md) and its [review note](review-notes/allocate-scarce-stock-by-promised-service.md) changed between the blocked successor and current manifests.

The skill now requires the effective per-order eligibility rule and each order's exact item, revision, fulfillable location, active holds, release state and priority status at the decision cutoff. It checks those fields before applying priority. A held or mismatched order gets no new allocation. An unknown hold, release or priority status excludes the order and blocks a final proposal to a lower-priority order unless the supplied policy explicitly permits skipping the unresolved order. Existing reservations stay committed and blocked until separate release authority; they are not made free by a hold. The previous per-pool conservation, order reservation cap and future stock-ready-time tests remain.

Discriminating cases for rereview use gross usable on-hand 12, including 4 units already reserved for A, so 8 units are free. A and B each ordered 10.

| Case | Required result from the current instructions |
|---|---|
| A has an active order hold; B requests the matching item at the fulfillable location and is releasable. | A gets **0 new** units and B gets at most **8 new** units under the supplied policy. A's existing 4 stay blocked, not donated to B or counted as fulfillable while held. |
| A is releasable, item and location match, and A-first priority status is evidenced. | A's incremental demand is 6, so an A-first policy yields at most 6 new units to A and 2 to B. |
| A's hold, release or priority status is unknown. | A receives no new allocation. A final lower-priority proposal for B is withheld unless the supplied skip rule permits it. |
| A's item or location does not match this stock pool. | A receives no new allocation from this pool, regardless of priority. |
| An inbound lot becomes stock-ready after an order's required stock-ready time. | Neither a new allocation nor an existing reservation against that lot counts as on-time coverage; its committed units are not silently freed. |

The [final local search receipt](SEARCH-EVALUATION-AFTER-PRIORITY-GATE-2026-09-23.json) binds the current manifest and retains 10 of 12 expected top-one matches and five of five unrelated abstentions. The [eligibility-draft receipt](SEARCH-EVALUATION-AFTER-ELIGIBILITY-REPAIR-2026-09-23.json) remains beside it. The two existing task-query misses remain. These are author-written development searches, not hosted or native-use evidence. Candidate approval remains **none** pending an independent reviewer of the exact successor bytes.
