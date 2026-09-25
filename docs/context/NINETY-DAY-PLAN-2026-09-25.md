# Ninety-day plan of September 25, 2026

Kind: dated engineering record for the owner. The roadmap
([roadmap.yaml](../roadmap/roadmap.yaml)) remains the only task authority;
this record holds the measurements and the decisions behind the steps it
names (S-6.198 to S-6.204, and the updated S-6.69 and S-6.197).

The owner asked, in the evening of September 25, 2026, for a step back over
the next 90 days towards 100,000 in monthly or yearly revenue, for the
measured time each kind of step takes, and for aggressive efficiency: 10,000
harness components fully live, searchable, retrievable and usable, more
demos and clearer quickstarts, a simpler review before publication with an
ongoing feedback process that can unpublish or flag an item, and every
open decision resolved by engineering's own judgement.

## Where things stand today

| Measure | Value on September 25, 2026 | Record |
|---|---|---|
| Paying subscribers | 0 active, trialing or past-due subscriptions; 0 customers; 2 checkout sessions started, 0 finished | Live Stripe account, counts only |
| Accounts | 18 identity accounts, 9 confirmed; 2 made September 20 and 16 on September 24, the day of the release 24 checks | Identity provider, counts only |
| Served packages | 93 (42 Verified, 51 Community), active catalogue release `2e23bfaa`, the fifth release | `catalogue-status` on the live service |
| Approved and waiting | 316 packages in `community-release-2`, bundle digest `a8d659d5…`, waiting for the host licence policy that release 35 loads | `release-folders/community-release-2/combine-report.json` |
| Supply on disk | 58,787 imported packages indexed; 81 percent pass the prechecks and 96 percent of those pass the screen, so about 45,000 are approvable | `review-batches/batch-001-pilot/prechecks.json`, `imported-pilot-1/writer-report.json` |
| Pages and hostnames | 47 pages, 8 hostnames | `web_site_map.json` |

At 29 dollars a month, 100,000 monthly revenue is 3,449 subscribers, 100,000
yearly revenue is 288, and 10,000 monthly revenue is 345.

## How long each kind of step takes

| Step | Measured | Target by October 25 |
|---|---|---|
| Push to green continuous integration | 22 to 25 minutes (25 green runs, September 24 and 25); failed runs 7 to 17 minutes | 12 minutes or less (S-6.200) |
| Failed first runs | 6 of 31 pushes on September 25, each costing a cycle plus the fix | under 5 percent (S-6.200) |
| Deploy workflow | 2 to 3 minutes (24 dispatches since September 20) | unchanged |
| Live checks after a deploy | about 10 minutes on eight hostnames; the record is written by hand | 6 minutes, record by the train |
| Push to live, first time green | about 40 minutes; releases 26 to 34 on September 25 | 25 minutes or less |
| A page from first commit to live | 49 minutes (the library page, one failed run included); building a page is hours by hand | a page record to live in 60 minutes (S-6.201) |
| A subdomain demo | about a day by hand (September 24: /demo, /demo/kaggle, /overnight) | 60 minutes from a demo record (S-6.201) |
| Export 2,000 packages | about 16 minutes | unattended (S-6.197) |
| Prechecks on 2,000 | minutes; 384 refused | unchanged |
| Screening review | 52.5 seconds a call of 12 packages; 240 packages in 18 minutes; 223 approved, 10 rejected; about 55,000 input tokens a call | shorter screen, 24 a call if the context holds (S-6.199) |
| Approvals to a live release | about 10 minutes by hand plus a 60 second swap | unattended every six hours (S-6.197) |
| Serving at 1,000, 5,000 and 10,000 | not measured; the 100,000-row synthetic probe of September 22 is the only larger one | measured before each mark (S-6.203) |

## The review process, changed

Recorded as the "Approval of intelligence items" row of the AGENTS.md
decision table and as roadmap step S-6.199. Before publication: the
deterministic prechecks, pinned provenance, and one screening call for up to
12 packages by one calibrated reviewer from a family that did not produce
them, answering the written criteria of the material; then automatic
publication as Community by the daily job. A shorter four-question screen
was measured the same night on the 240-package pilot: it approved 7 of the
10 packages the written criteria rejected, so the written criteria stay the
questions of the one call (52 seconds for 12 packages). After publication:
a report button on every item, withdrawal within a minute on a signed-in
customer's report (a Verified item needs a staff flag or two customers), a
nightly rescan with the current rules, a weekly upstream check,
second-family reviews that upgrade to Verified or withdraw, and a kept
record for every withdrawal.

## The thirteen decisions

The owner: "use your best judgement to resolve all of these". Each row of
the decision table now stands as engineering's decision with its reason; the
rows changed on September 25 are Delegated decisions (new), Approval of
intelligence items, Price (annual Baltor Pro at 290), Hosting plans (volume
and memory within the allowance), A library of 100,000 harness files (dated
marks) and Library tiers (the screen and the feedback withdrawal). The
others stand unchanged.

## The ninety days, in order

1. September 26 to October 2: release 35, the 316-package release, the
   daily job on cron, the report route and withdrawal rules, sharded
   continuous integration and the pre-push hook, serving measured at 1,000
   and 5,000; 10,000 served by October 5; the decision red-team study
   (S-6.198) run against the rules engine and the Tactical model.
2. October 3 to October 25: paged listing and one indexable page per item at
   10,000; quickstarts for seven harnesses with nightly connection checks
   (S-6.202); the page and demo generators and three subdomain demos
   (S-6.201); Team, Studio and annual Baltor Pro on sale once checked;
   registry and plugin listings; second-family passes; the weekly number
   (S-6.204).
3. October 26 to November 24: 30,000 to 60,000 packages; author
   submissions; opt-in telemetry and the outcome join; design partners
   (S-6.186); benchmark pages (S-6.173, S-6.185); payments outside the
   United States (S-6.195); the trust section (S-6.194).
4. November 25 to December 24: 100,000 packages on the index-file and
   object-storage engines; Kaggle write-ups; the YC package; the second
   factor and OAuth (S-6.193).

## Revenue arithmetic

With assumed rates of 2 percent of visitors making an account and 10
percent of accounts paying, 345 subscribers need 172,500 visitors in 90
days, about 1,900 a day; 288 need 144,000. No visitor count exists yet;
S-6.204 measures the rates. Engineering's part is what a visitor can find
and try: item pages, quickstarts, demos, listings and plans above Pro. The
owner's part is the audiences engineering cannot reach: social profiles,
the newsletter, LinkedIn, Show HN and YC. Nothing here is a revenue
forecast.

## Sources

The GitHub run history of `ci.yml` and `fly-pilot.yml`; the release records
`pilot-release-23.json` to `pilot-release-34.json`; `git log` of main since
September 18; the review ledger `ledger-tactical.jsonl`, the pilot writer
report, the batch prechecks record and the community-release-2 combine
report under `/home/username/baltor-library`; the live catalogue status; the
live billing and identity counts; `web_site_map.json`; the 100,000-row
serving probe of September 22.
