# The first Community catalogue release, September 25, 2026

At 16:38 UTC the live service switched to catalogue release
`2e23bfaa4ab38ffa5539130774e7b2503aeeef6f42d578d29674733de8a50823`, published
without a redeploy from bundle `4e0484b76924a2d907c7a42bd088ba44b0123f365cf78d3ea8a81d9100f04e9e`
on top of Fly release 31. The previous release was `69da7ead21f9`.

## What changed in the library

| Change | Count |
|---|---|
| Community items added: each passed every automated check and one review by a model family that did not write it (Claude reviewing candidates of other families) | 51 |
| First-catalogue items kept as Verified, with the exception the meaning of Verified states | 42 |
| Items withdrawn durably: `normalize_phone_numbers`, after the data cleanup study measured 0.842 with it against 0.991 without it | 1 |
| Items served | 93 |

The homepage shows the live count from the capabilities record, which read 93
after the service's refresher swapped to the release (health:
`catalogue_release.refresher.swaps` 1).

## How it was checked as a customer

The operator check `check_live_community_retrieval.py` (kept with the operator
tools, outside the repository) used the diagnostic account `pilot-owner`:

| Report | Result |
|---|---|
| [live-retrieval-check-1-before-the-refresh.json](live-retrieval-check-1-before-the-refresh.json) | failed: it ran within the 60 seconds before the running service picked up the release; search found no Community item and the download was refused |
| [live-retrieval-check-2.json](live-retrieval-check-2.json) | 6 of 6: search finds the Community item and labels it Community, a Verified-only search leaves it out, the downloaded bytes match the digest, the download names the Community tier, and the withdrawn phone item is not served |

The deciding catalogue check first failed one of its eight checks after the
publish ([catalogue-check-1-before-the-check-knew-community.json](catalogue-check-1-before-the-check-knew-community.json)):
it required every search hit to be approved by the starter review record,
while search now also returns Community items. The work was right and the
check was out of date. The check now asks each query twice: narrowed to
Verified, where every hit must be approved by the review record, and with the
account's own setting, where every other hit must be a Community item labelled
Community. It passed 9 of 9 against the live service
([catalogue-check-2.json](catalogue-check-2.json)): 10 Verified items and 15
Community items over two queries, one withdrawal.

No model was called for these checks.
