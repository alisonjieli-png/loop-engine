# Public Good: six goals added, October 5, 2026

Six Community-admitted original packages are now in the live catalogue and in
the Public Good collection. They are the first entries for goals 7, 9, 11, 12,
14 and 15. The live collection now covers 11 of the 17 goals.

This is a catalogue and access-policy update. It is not an application
deployment. Release 62 still serves the application.

## What changed

| Measure | Before | After |
| --- | ---: | ---: |
| Catalogue packages | 30,751 | 30,757 |
| Public Good packages | 412 | 418 |
| Public Good distinct useful files | 1,011 | 1,029 |
| Public Good distinct files, with support files | not recorded | 1,753 |
| Goals with at least one package | 5 | 11 |

The useful-file count uses explicit reviewed paths only: each package's program
and its input and output schemas. Licences, tests, examples and invocation
cards are delivered but are not counted as useful files.

Goals with packages after the update: 4 (5 packages), 6 (1), 7 (1), 8 (2),
9 (1), 10 (4), 11 (1), 12 (1), 13 (2), 14 (1) and 15 (1). Goals 1, 2, 3, 5, 16
and 17 are still empty. The page keeps showing them as empty.

## The six packages

| Package | Goal and target | Job |
| --- | --- | --- |
| `baltor_degree_day_coverage` | 7, target 7.3 | Calculate heating and cooling degree days from bounded daily temperature extremes, and show calendar gaps and unit assumptions |
| `baltor_infrastructure_outage_accounting` | 9, target 9.1 | Reconcile overlapping outage records and unknown monitoring periods in a declared window, without double-counting downtime or treating missing monitoring as service |
| `baltor_transit_headway_audit` | 11, target 11.2 | Audit the departures of one stop, direction and service window for headway gaps, simultaneous departures and unobserved boundary periods |
| `baltor_waste_mass_balance` | 12, target 12.5 | Reconcile opening stock, incoming material, destination flows and closing stock in explicit mass units, and keep unexplained residuals |
| `baltor_marine_litter_density` | 14, target 14.1 | Check and aggregate one marine-litter survey's item counts by the area actually observed, and separate a measured zero from an unobserved category |
| `baltor_land_cover_transition` | 15, target 15.1 | Reconcile a complete land-cover transition matrix into opening and closing area, persistence, gross gains and losses, and net change for each class |

Each package is an original standard-library Python program that reads JSON on
standard input and writes JSON on standard output. It has input and output
schemas, tests and an MIT licence under the repository notice. Each grant
describes the package as a supporting calculation on caller-supplied data. It
is not an official indicator, complete target coverage or United Nations
endorsement.

Codex (OpenAI family) produced the packages on October 1. Kimi K2.6 (Moonshot
family) reviewed them in run `all17-environment-review-001` and approved all
six at the Community tier. The producer did not approve its own work. Their
earlier checks: 108 behaviour methods, 600 seeded oracle cases, and schema
validation of every example.

## Publication

The guarded delta publisher composed the additions onto the exact live
baseline.

- Base release: `9ed0fcd7a70ed541411ec564949c8ab2e74336f847c10388f8bdde023ce9855d`
  (full metadata snapshot `public-good-merged-20260930-1vVzpw/merged-bundle-delta`).
- Reconciliation request: six additions, no replacements, no withdrawals.
  Reconciliation digest
  `ee158de34c19b041a3d89cc331d9955739999fb29a4cf4b0b7ee07e640093ac9`.
- Bundle digest: `f8bd798518dbe18bf23b70633f8b9559ac4b53b19b0ec98ffd8bdfaa84f998ac`.
- New release: `e817bec22796bba8af9fb28ed34baf9714fa2b97758e415108f906d7d6a5a6ca`.
- Content digest: `fcfc9a662f05c1102e0cbad26bb15e61f247c9e2f85fe5505b7a0d42860091fd`.
- Transfer: 48 new blobs, 211,777 bytes, in one batch, plus the full
  manifests.

The reconciler verified all 96,120 baseline bodies. It kept every one of the
30,751 existing rows and versions unchanged. The live release and content
digests equal the reconciler's prediction on baltor.ai, app.baltor.ai and
baltor-pilot.fly.dev.

The reconciler needs every licence label the host accepts. The live catalogue
holds eight labels: MIT, MIT AND BSD-2-Clause, Apache-2.0, CC0-1.0, ISC,
BSD-3-Clause, BSD-2-Clause and CC-BY-4.0. With MIT alone it refused with
`item_license_not_accepted`, as it should.

The publication used the tools at `06c61876`. The open publication-path
defects concern withdrawals, replacements, oversized bundle lines and
interrupted remote operations. This change had none of these, and the live
catalogue had no withdrawn rows left out, so the defects could not refuse it.

## Access policy

- Previous policy version: `548011d4931e48c085aea26b6394dcad`.
- New policy version: `35a65b6c509a4575963ceaf879bf738f`.
- Request file digest:
  `99ab9fecb0d35b52b4268c7cf251ea65437fd37739789a70e62adf1173a55652`.
- Payload digest:
  `162adba1204d08b4ee89c9bb4944e107974ca9b5b514acfe3a4c488147e62939`.

The request keeps all 412 existing grants and the limits byte for byte and adds
six grants. The service's own `ProvisioningItemBinding.from_item` built the six
bindings. As a control, the same code rebuilt the bindings of all 412 applied
grants, and every one matched. On the host, the read-only plan verified 418
selected versions and 2,058 file placements against the new release before the
apply. The apply used the exact file digest. The public read-back on three
hosts shows policy `35a65b6c`, 418 packages, an account requirement and no
subscription requirement.

## Expiry: renew before October 31

Every Public Good grant expires at the end of October. 413 grants expire on
November 1, 2026 at 00:00 UTC, and the five September 30 originals expire on
October 31 at 00:00 UTC. The six new grants use the November 1 time, the same as
most of the collection. Unless a reviewed policy renews them first, free access
to the whole collection ends on those dates.

## Evidence

Private evidence is in `/home/username/baltor-private/public-good-six-20261005-1W8Czh`.
It holds the reconciliation request and result, the dry run, the publication
output, the policy preparation script, the policy file, and the plan and apply
results. Do not copy that folder into this repository.

The host keeps the publication receipt
`/data/incoming/delta-public-good-six-20261005-52c7f2ad2e79.publish.json` and
the policy file `/data/incoming/public-good-policy-2026-10-05-001.json`.
`/data/incoming` also holds about 4.0 GB of older staging files. The volume is
25 GB and 22% used. Removing old staging is a separate decision.

No model call, application deployment, schedule change or credential change
was made.
