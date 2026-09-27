# Weekly number records

Kind: dated records of the weekly number (roadmap S-6.204), written by
`tools/weekly_number.py`. Each file is named `weekly-number-YYYY-MM-DD-N.json`
and carries the record type `weekly_number/v1`. A run never overwrites an
earlier record: the next free number is used, and an earlier attempt stays
beside its successor.

## What a record holds

Current behaviour, as of September 26, 2026:

| Part | Source | What is counted |
|---|---|---|
| Accounts | The identity provider's administration interface, credential reference `supabase-secret` | Accounts made and confirmed, all time and in the seven-day window, by day; the accounts the live journey checks make (address prefix `baltor-check-`) counted apart; accounts the provider marks deleted and still lists counted apart; the provider's reported total kept beside the listed total |
| Billing | The live billing account, credential reference `stripe-live`, read requests only | Paying subscriptions (active, trialing or past due), subscriptions by status, customers, checkout sessions started and finished |
| Library served | The public health and capabilities records of `https://baltor.ai` | Packages served, the active catalogue release, its digest, item count and build time |
| Release cycle times | The records `artifacts/architecture-audit-2026-09-19/pilot-release-N.json`, read through the fields of their own version: `deployment_evidence/v1` (releases up to 37) and `pilot_release_record/v1` (from release 38, September 27, 2026). A record of any other type makes the release source unavailable and names the file; a record without a deployment time is listed under `left_out` | Releases in the window, the latest release, minutes from the source commit to live for each, failed first attempts where the version records them (unknown for `pilot_release_record/v1`) |
| Library cycle times | The daily job's folders under `/home/username/baltor-library/daily/` (`counts.json` and `journal.jsonl`) | Slots in the window, minutes from the slot's start to served, review minutes, exported, approved and rejected counts |
| Funnel rates | The parts above | Presented as measured only when every source involved holds seven days of data; otherwise the record says how many days exist and keeps the plan's assumed rate beside it |

Every count that may mix engineering's own accounts and check journeys with
customers carries `mixes_test_journeys: true` and a note that says why. The
record holds counts and dates only: no address, no customer identifier, no
raw provider answer and no credential. Three named checks refuse a record
before it is written: raw content in the text, a mixed count without its
mark, and a rate presented as measured before a week of data.

The account listing is read whole. The provider names the whole count in a
response header and may return fewer rows a page than asked for, so the
reader follows that total across pages, ends on an empty page when the
header is absent, counts a row that a new account shifted onto the next
page once, and marks the identity source unavailable when the listing comes
back shorter than the reported total, rather than recording a smaller
number. The record keeps `total` (listed) and `reported_total` (the header)
side by side.

## How it runs

By hand, from the repository root, with the two references resolved from the
system keyring through `tools/operator_credentials.py`:

```text
DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus .venv/bin/python tools/weekly_number.py
```

Or under the credential helper, which places the values in the environment of
the command and never prints them:

```text
python3 tools/operator_credentials.py run --ref stripe-live --ref supabase-secret -- .venv/bin/python tools/weekly_number.py
```

A missing credential refuses the whole run before any request, with exit
code 2 and a line that names the reference and its environment variable,
never a value. A test-mode key under the live reference is refused the same
way. When a source cannot be read, the record is still written with that
source marked `unavailable` and its status code, the table says INCOMPLETE,
and the exit code is 1.

Every Monday at 06:10 UTC, cron runs the command and appends its output to
`/home/username/.le-ci-tmp/weekly-number-cron.log`. The entry, printed by
`tools/weekly_number.py --print-cron`, was installed on September 26, 2026
and replaced the same day with this shape:

```text
10 1,2 * * 1 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus TMPDIR=/home/username/.le-ci-tmp/weekly-number bash -lc '[ "$(date -u +\%H)" = 06 ] || exit 0; R=/home/username/loop-engine; [ -f "$R/tools/weekly_number.py" ] || R=/home/username/.le-agent-weekly-number; cd "$R" && echo "$(date -u +\%FT\%TZ) $R" && /home/username/loop-engine/.venv/bin/python tools/weekly_number.py' >> /home/username/.le-ci-tmp/weekly-number-cron.log 2>&1
```

cron on this machine runs in the system's local time (America/New_York) and
has no time zone setting for one entry, so the entry fires at 01:10 and 02:10
local time on Mondays and the guard lets only the run at 06:10 UTC go on,
under both daylight saving settings. This is the pattern the cron manual
gives for a task in another time zone. The command runs from the shared
checkout `/home/username/loop-engine` once the tool is merged there, and
from the worktree that wrote it until then, in the shape of the quickstart
check's entry; the log names the tree each run used. The first scheduled run
is Monday, September 28, 2026 at 06:10 UTC.

## The records of September 26, 2026

Three records were written by real read-only runs, at 12:50, 12:51 and
16:29 UTC, through the keyring, with no charge, no write request and no
model call. Every run gave the same counts.

| Measure | This week | All time | Mark |
|---|---|---|---|
| Accounts made | 18 | 18 | mixed; 6 match the check journey prefix; 2 made on September 20 and 16 on September 24, the day of the release 24 checks; the third record adds that the provider reports 18 in its header and marks 2 of them deleted while still listing them |
| Accounts confirmed | 9 | 9 | mixed; 4 of the confirmed are check journeys |
| Paying subscriptions | | 0 | mixed |
| Customers | 0 | 0 | mixed |
| Checkout sessions started | 2 | 2 | mixed; both expired, started September 21 |
| Checkout sessions finished | 0 | 0 | mixed |
| Packages served | | 6,398 | release `856bff51`; the health record's build time read 11:54 UTC in the first two runs and 13:24 UTC in the third, the same release |
| Releases to Fly | 14 | 14 | commit to live median 25.9 minutes (20.7 to 39.0); 10 failed first attempts over the 11 releases that record them |
| Library slots run | 3 | 3 | start to served median 100.6 minutes over the 2 slots with a publish entry; review median 64.2 minutes; 4,769 approved of 6,000 exported |
| Visitors | | | not measured; no request counter exists |
| Rate visitors to accounts | | | not measured; the plan assumed 2 percent |
| Rate accounts to paying | | | not measured; 5 days of data, a week is needed; the plan assumed 10 percent |
| Rate checkout started to finished | | | not measured; 5 days of data |

The records differ in two places. `weekly-number-2026-09-26-1.json` left
two accounts undated (`unreadable_dates: 2`) because the time parser did not
read a fractional second of fewer than six digits under Python 3.10, which
the identity provider sends. The parser was repaired, the case joined the
unit tests, and `weekly-number-2026-09-26-2.json` reads every date.
`weekly-number-2026-09-26-3.json` was written after the listing was made to
follow the provider's reported total; it adds `reported_total` (18, read in
one request) and `deleted` (2). All three records are kept.

## Not in this package

- The staff page that shows the week and its trend. The record is written
  for it; no page reads it yet.
- The visitor count: requests to customer pages by distinct address, metadata
  only, kept under the retention rule. Until it exists the rate from visitors
  to accounts stays "not measured".

## Limits

- The check-journey prefix separates only the accounts the live journey
  checks make. The owner's and engineering's other accounts cannot be told
  apart from customers by their fields, so the account and billing counts
  stay marked as mixed.
- An account the provider marks deleted stays in the listing and in the
  provider's reported total, so `total` keeps it and `deleted` names it.
- A daily slot's start is the creation time of its folder, which the job
  makes at its start. A slot whose journal has no publish entry has no served
  time and is left out of the start-to-served summary.
- The commit-to-live time needs the source revision in the local git
  history; otherwise it is unknown and left out of the summary.
- The seven-day window ends at the run time, so a Monday run covers the
  previous Monday 06:10 UTC to this one.
