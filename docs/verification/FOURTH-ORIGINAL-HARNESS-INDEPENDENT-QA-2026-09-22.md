# Independent rereview of the fourth harness candidate batch

Kind: dated candidate-only verification, September 22 and 23, 2026 local time. This
read-only review covers the [fourth isolated batch](../../artifacts/first-party-harness-candidates-2026-09-22-wave-4-ops/README.md).
It does not approve, promote, serve or measure any item.

The original exact-byte [manifest](../../artifacts/first-party-harness-candidates-2026-09-22-wave-4-ops/manifest-pre-repair-2026-09-22.json)
has SHA-256 `53df3f4cebe130bbdbef612ce9bcb35344631c7053ce68f5804b1844a28ecb1b`.
The first repair draft has SHA-256
`7c264fe671faa3021e0df3063cc43e2445e996c1db13bb7b2b3261d95d99d6ab`.
The [first rereviewed successor manifest](../../artifacts/first-party-harness-candidates-2026-09-22-wave-4-ops/manifest-rereview-blocked-2026-09-23.json)
has SHA-256
`2cb6c04918dc7aa05b331186f7120b8f020542a7afcd82843456fcdfb58c4696`.
The [final successor manifest](../../artifacts/first-party-harness-candidates-2026-09-22-wave-4-ops/manifest.json)
has SHA-256
`f5790bedba8efded222d87a5d819a44d4def6dadb8982bd529e23a4c0437791a`.
Each successor binds 12 native `SKILL.md` files and 12 review notes. Their
repository revision is a research starting revision, not a commit
containing these candidate bytes.

## Four counterexamples replayed

I reread the three changed skills and their review notes. The calculations
below independently replay the cases against the rules now written in those
files. They are checks of the procedure's meaning, not tests that a model or
native client follows it.

| Case | Expected result from successor instructions | Rereview |
|---|---|---|
| An order already has reserved stock | In [stock allocation](../../artifacts/first-party-harness-candidates-2026-09-22-wave-4-ops/packages/data/allocate-scarce-stock-by-promised-service/SKILL.md), gross on-hand 12 less 4 reserved for A leaves 8 free. A and B each ordered 10; A needs only 6 new units. Under A-first priority, A gets 6 new and B gets 2. A's 4 reserved plus 6 new equals its 10-unit unfilled demand. | The successor explicitly links reservations to orders and lots, caps incremental demand, and preserves per-pool and per-order conservation. The arithmetic checks. |
| Inbound stock arrives after an order's promise | The same skill compares a future lot's evidenced stock-ready time with the order's required ready time, derived from the promise and handling or transit lead time. A lot ready on the 12th cannot cover a promise requiring ready stock on the 10th. A late existing reservation remains committed until authorized release but does not count as on-time coverage. | The successor explicitly checks both new and existing future reservations. The temporal comparison checks. |
| Partial monetary credit precedes a return | In [return credit](../../artifacts/first-party-harness-candidates-2026-09-22-wave-4-ops/packages/project/reconcile-return-credit-to-original-sale/SKILL.md), an eligible original sale amount of 100 less a prior partial credit of 40 leaves at most 60 additional currency units, although one unit remains eligible by count. | Separate line-level quantity and monetary headroom now prevent 40 plus 100 from being called eligible. Missing credit links hold the proposal. The arithmetic checks. |
| An accrual is replaced by a posted invoice | In [cost variance](../../artifacts/first-party-harness-candidates-2026-09-22-wave-4-ops/packages/data/explain-work-package-cost-variance/SKILL.md), an 8,000 original accrual and an 8,000 signed reversal leave zero open accrual. With posted actual 8,000 and residual commitment zero, known exposure is 8,000, not 24,000. | The successor requires cost-event and clearing links. If actual and accrual both remain positive without a clearing link, it withholds a final figure. The arithmetic checks. |

## Blocker found in the first successor

The stock allocation skill under the blocked `2cb6c049` manifest removed its
prior instruction to keep an order ineligible when its hold,
item, location or priority status is unresolved. The new inputs list stock
holds but no order-specific hold state. Step 4 mentions "eligible demand"
without an explicit order eligibility test.

Discriminating case: A is the highest-priority order but has an active
customer or order hold; B is releasable. The successor's quantity and timing
checks could all pass while it proposed scarce free stock for A. The finding
required per-order identity, item, location, active-hold, release and priority
status before ranking, with unknown status held for customer policy resolution.

## Final successor rereview on September 23

I reread the exact final [allocation skill](../../artifacts/first-party-harness-candidates-2026-09-22-wave-4-ops/packages/data/allocate-scarce-stock-by-promised-service/SKILL.md)
and [review note](../../artifacts/first-party-harness-candidates-2026-09-22-wave-4-ops/review-notes/allocate-scarce-stock-by-promised-service.md)
against the blocked predecessor. The final successor changes only those two
candidate files; the return-credit and cost-variance body and note hashes are
unchanged from `2cb6c049`. I independently replayed all five cases against
the final text:

| Case | Result required by the final text |
|---|---|
| Existing reservation | Gross stock 12 less 4 reserved for A leaves 8 free. With both orders eligible, A-first priority permits 6 **new** units to A and 2 to B. A's existing 4 plus new 6 equals its 10 ordered units. |
| Late inbound | An inbound lot ready on the 12th cannot count toward on-time coverage requiring stock ready on the 10th. This applies to existing reservations too; a late reservation remains blocked until authorized release. |
| Partial earlier credit | Original eligible sale value 100 less earlier monetary credit 40 leaves at most 60 further credit. An unknown prior-credit link holds the result. |
| Accrual settlement | Original accrual 8,000 plus signed reversal negative 8,000 leaves zero open accrual. Posted actual 8,000 plus open accrual zero plus residual commitment zero gives known exposure 8,000. A missing clearing link with positive accrual and actual holds the final total. |
| Held, mismatched or unknown order | With 4 units reserved for held A and 8 free units, A receives zero **new** units; eligible B may receive at most 8, while A's 4 remain committed. A wrong item or location also excludes it. Unknown hold, release or priority status excludes the order and, when it could outrank B, blocks a final lower-priority proposal unless the supplied policy permits skipping it. |

The final stock skill requires evidence for item and revision, fulfillable
location, active holds, release and per-order priority status before ranking.
It keeps the gross-to-free, per-order quantity and future-stock timing gates
from the prior repair. These are static instruction and independent arithmetic
checks, not model-execution or native-client tests. I found no remaining
counterexample in these five fixtures, but this is not item approval.

## Other checks and limits

- The final successor [whole-batch check](../../artifacts/first-party-harness-candidates-2026-09-22-wave-4-ops/check_batch_clean.py)
  passed: candidate body and note hashes match the manifest; no symlink or
  generated cache was found.
- The [source checker](../../artifacts/first-party-harness-candidates-2026-09-22-wave-4-ops/check_source_refs.py)
  passed for 12 distinct task references, with four checker tests passing.
  Each task ID and occupation pair also matched one row in the exact pinned
  O*NET® 31.0 `task_statements.csv` source ZIP. None overlapped the 21 IDs in
  the earlier occupation method brief. This checks source identity, not
  legal originality or domain validity.
- `skills-ref==0.1.0` validated all 12 native package folders. This checks
  file format, not the method's effect or usefulness.
- The saved final-successor local search result still reports 10 of 12 expected
  candidates first and five of five unrelated queries with no match. The
  two retrieval misses remain. Those author-written probes do not test
  hosted search or a large catalogue.

All 12 items remain candidates. The repaired text has not been tested with a
native harness on a real task, and no independent approval or customer
benefit is established. The [roadmap](../roadmap/roadmap.yaml) remains the
task authority.
