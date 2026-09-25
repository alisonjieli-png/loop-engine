# Community catalogue release 2: 316 packages, September 25, 2026

Kind: dated release record for the second Community catalogue release
(roadmap S-6.119, S-6.196 and S-6.69). Bodies stay outside the repository.

## What was published

| Fact | Value |
|---|---|
| Release identity | `c7208dc813ab0197e989adc243c802fd867675f0335fa229587ecdab45bcfd46` |
| Bundle digest | `a8d659d5916da38c969b8c52e6dc593b507dd6f57d6195a1007f2aa47833c00e` |
| Content digest | `5819538984a63d1912f3ee45f00aee2300722b1a12c2e4d8d8f552862c3d0a7e` |
| Items | 316: 42 Verified and 274 Community, of which 223 are imported packages approved by the Tactical screen of the 240-package pilot and 51 are the original candidates of release 1 |
| Added, changed, withdrawn | 223 added, 93 changed (every earlier item re-anchored by the combine step), 0 durable withdrawals |
| Published | 22:35 UTC, without a redeploy; the service's view was built at 22:36 UTC (`built_at` 1790375782) and the library page lists 316 items |
| Host licence policy | `service_host_license_policy/v1` accepting MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, CC0-1.0 and CC-BY-4.0, set in the host file before Fly release 35 loaded it; the bundle was built with the same `--accept-license` list |
| Source folders | `/home/username/baltor-library/release-folders/community-release-2` (combine report: 622 rows, 316 approved, 267 relabelled sources), from `reviewed-2026-09-25/imported-pilot-1` (223 approved, 10 rejected) and the release 1 folders |
| Accounts | Every customer account and `pilot-owner` follow the active release (`already_following`); `baltor-admin`, `pilot-boundary` and the three billing-check accounts stay on their fixed lists (`not_granted_every_item`), as the isolation rule requires |

## Live retrieval check

The check asks as a customer with version 2 requests: search, the tier on
the hit, a Verified-only search, one metered download, and the withdrawn
item. Every attempt is kept.

| Attempt | Item | Result | Why |
|---|---|---|---|
| `live-retrieval-1.json` | `import_marketplace_superpowers_marketplace_d2debfe35a1d` (kind tool) | search did not find it; download failed | The item declares effects beyond `reads_fs`, so a read-only request cannot receive it, and its identity words do not rank it in the top ten. The check needs an item a read-only request may receive. |
| `live-retrieval-2.json` | the same | the same | Repeated after the refresher had swapped; same cause. |
| `live-retrieval-3.json` | `import_rules_020_agent_skill_authoring_840b5b945fdb` (instruction file, `reads_fs`) | search found it with the Community tier; the download answered 503 `meter_commit_unknown` | The check reused one fixed request identity (`community-check-2`) across runs; the service keeps one durable usage acknowledgment per request identity and refuses a reused one with another item, on purpose. |
| `live-retrieval-4.json` | the same | passed 6 of 6 | The check now derives each request identity from the item and the time. The served body's digest `7b483316…` equals the bundle's reference digest; the served body is the package descriptor (`{"files": [...]}`), since an imported package is served as its file inventory. |

## What this does not establish

The 223 imported packages were approved by one family (Tactical, Google) under
the full eight-criterion imported review, so they are Community. No customer
has yet retrieved one in their own harness; the check above is engineering's
own account. Search ranking for imported packages by their identity words is
weak; the library page lists them by purpose.
