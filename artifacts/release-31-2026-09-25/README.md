# Release 31 evidence, September 25, 2026

Fly release 31 of `baltor-pilot` went live at 16:29 UTC from main
`eaabbe62aae1f85f7866b3c21c9b13fcd2bed6f5` after continuous integration run
36158116005 passed, through deployment run 36160821801. The image is
`sha256:bf5ab28b2383601787a464d1b2978b6bb91a3d434926b4f1db30220d0cc68942`;
the rollback target is release 30. The record is
[`pilot-release-31.json`](../architecture-audit-2026-09-19/pilot-release-31.json).

## What a person sees now

- An item a search offers can be downloaded from the same page: the website's
  download button and the Pi extension ask the way search asks, with version
  2 of the provisioning request. Before this release an item that reads files
  was offered by search and then refused.
- Each search result on the website shows its library tier, Verified or
  Community.
- The published meaning of Verified says that the first catalogue, approved on
  September 21, 2026, was written and reviewed before the two-family rule and
  is reviewed again by two other model families when they are available.

## How it was checked

| Check | Result |
|---|---|
| What a person sees: 44 pages at desktop and phone width, light and dark, and 8 hostnames | no problem; 338 links checked |
| The customer's search and download with the homepage digest guard | 8 of 8 |
| The service transport and isolation | 19 of 19 |

Advice: 135 of 135 addresses answer, the Pi extension matches on all nine
hostnames, and 216 of 216 detailed browser rules pass on baltor.ai.

Right after this release the first Community catalogue release was published
without a redeploy; its evidence is in
[the Community release folder](../community-release-2026-09-25/README.md).

The screenshots are kept outside the repository.
