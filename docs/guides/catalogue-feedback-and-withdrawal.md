# Catalogue feedback and withdrawal

Kind: operator guide to the feedback edge of the served library, the nightly
rescan and the weekly upstream check (roadmap S-6.199).

The "Approval of intelligence items" row of the decision table in AGENTS.md
publishes an item after one screening review and lets feedback withdraw it
afterwards. This page says what is built for that today, what each tool does,
what still needs a person, and what the host needs. Current behaviour and
planned behaviour are kept apart.

## Current behaviour

```text
Feedback on a served item
├── report   a signed-in customer names the item, the digest they saw and a reason
│   ├── over /api/v1/provisioning, operation report, record service_provisioning_request/v2
│   ├── over the protocol tool provisioning_report
│   └── from the signed-in pages: the detail panel of the library table and every search result card
├── flag     a staff member whose role holds catalogue.flag (the superadmin role today)
│   └── over /api/v1/provisioning, operation flag, from a signed-in browser session
├── rule     Community: the first report withdraws; Verified: a second account's report or a flag withdraws
├── record   every report and flag is a catalogue_item_report/v1 record in the service store
├── effect   a withdrawal is the same catalogue_withdrawal/v1 record an operator writes, so the refresher
│            leaves the item out within its interval, a read answers item_withdrawn at once, and no later
│            release or rollback serves that item version again
└── page     the public library page lists every withdrawal since the release with its note
```

The report edge lives in `src/loop_engine/core/service_runtime/catalogue_reports.py`.
Its checks are `catalogue_report_checks.py` beside it, run by the self-test.
The customer page [Searching and retrieving](service-searching-and-retrieving.md)
documents the request, the answer and the refusal codes.

A report counts once for each account and item version. An anonymous caller
holds no account and is refused before anything is written. A host key never
holds a staff role, so a flag from a service token is refused with
`staff_role_required`. A host that serves its catalogue without a refresher
refuses reports with `catalogue_reports_unavailable`, because the withdrawal
would not reach the served view.

## The review queue

Every report and flag marks its item version `queued` for the full review.
`review_queue` in `catalogue_reports.py` lists the queued item versions with
their counts, reasons and whether they are withdrawn. The full review itself is
the existing independent review of the candidate material, and reinstatement is
a new review of new bytes: a withdrawn item version is never served again, and
a release that lists it is refused with `catalogue_release_lists_withdrawn_item`.

## The nightly rescan

`tools/rescan_served_catalogue.py` reads the active release and the body store
of one host file and runs the deterministic rules that apply to every served
item whatever profile reviewed it: the licence is on the panel's accepted list,
the panel's static safety rules over every text file, the declared effects are
valid and a shell block declares the process effect, and the panel's secret
patterns over every file and the item record. Without `--withdraw` it lists
what fails a rule now and exits with status 2 when anything does. With
`--withdraw` it records the durable withdrawal of each failing item version
with a note that names the failing rules. Every run writes a record under
`artifacts/served-catalogue-rescans/`.

```bash
PYTHONPATH=src:tools python tools/rescan_served_catalogue.py --host /data/host.json
PYTHONPATH=src:tools python tools/rescan_served_catalogue.py --host /data/host.json --withdraw
```

The format and duplicate kinds of the review are not rescanned. The format
rules are bound to the review profile of the candidate and to material the
store does not hold, such as the licence texts a licensed import cites. The
duplicate rule is a merge decision between served items, never a withdrawal.
The record names both under `not_rescanned`.

## The weekly upstream check

`tools/check_upstream_sources.py` groups the served imported items by
repository, reads the repository host once for each repository, and lists a
repository that answers 404, a licence the repository declares that differs
from the one an item carries, a published security advisory, and an archived
repository. It withdraws nothing; a finding is a reason for a person to
withdraw with `loop-engine service withdraw-catalogue-item` or to re-review.
Reads need `--authorize-network-reads`, are bounded by `--max-repositories`
(30 by default) and use the host's public interface without a credential.
Every run writes a record under `artifacts/upstream-source-checks/`.

```bash
PYTHONPATH=src:tools python tools/check_upstream_sources.py --host /data/host.json --authorize-network-reads
```

This is a bounded first version. A licence the host cannot detect
(`NOASSERTION`) raises no finding, and a repository the host did not answer for
is recorded as `upstream_unknown`.

## What the host needs

Reports need no new host setting. They need what the hosted service already
has: the `catalogue` section of `/data/host.json` with the `store` source, so
the service runs its catalogue refresher, and `runtime.writes_authorized` set to
true, which the service already needs to record usage. A flag needs a staff
member in the `staff` list of the `accounts` block with the `superadmin` role.

The two tools run from cron on the Machine, beside the daily job:

```text
15 3 * * *   the nightly rescan with --withdraw, from the checked-out release tree
30 4 * * 1   the weekly upstream check with --authorize-network-reads
```

Both write their records under `artifacts/`; the records are copied into the
repository by the session that reviews them, like every other dated record.

## Planned behaviour

- The full review of a queued item version, started from the queue rather than
  from a candidate folder, and the reinstatement path that serves new bytes
  after it.
- A rescan of the format rules for each review profile, once the store keeps the
  review-time material an imported package cites.
- An account setting that lets a customer see their own reports and their
  outcomes on the signed-in pages.
- A withdrawal made by the upstream check itself for a repository that is gone
  with a licence that no longer allows the copy, once the licence decision can
  be read back from the host's answer.
