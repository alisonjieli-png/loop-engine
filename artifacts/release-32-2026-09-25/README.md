# Release 32 evidence, September 25, 2026

Fly release 32 of `baltor-pilot` went live at 17:57 UTC from main
`0d2b1da3e724ae296e20e51420306e0ca4a8b55f` after continuous integration run
36167480569 passed, through deployment run 36170064918. The image is
`sha256:4bf4ca874e9683daaee713b8bd93e6877234cb3428b7834203fc9860dc1c3b32`;
the rollback target is release 31. The record is
[`pilot-release-32.json`](../architecture-audit-2026-09-19/pilot-release-32.json).

## What a person sees now

- The catalogue browser of a signed-in account lists the Community items
  beside the Verified ones. Each row starts with its tier, Verified or
  Community, and the detail of an item names it too.

## How it was checked

| Check | Result |
|---|---|
| What a person sees: 44 pages at desktop and phone width, light and dark, and 8 hostnames | no problem; 338 links checked |
| The customer's search and download, with Verified and Community searches and the homepage digest guard | 9 of 9 |
| The service transport and isolation | 19 of 19 |

Advice: 135 of 135 addresses answer, the Pi extension matches on all nine
hostnames, and 216 of 216 detailed browser rules pass on baltor.ai.

Before the push the local browser suite passed 907 of 907 checks and detected
all 183 removed-guard controls, three of them new for the tier labels. Its
first run had failed one check that went stale in release 30, when the
homepage started showing the live count; the browser suite does not run in
continuous integration, and roadmap step S-6.180 proposes a nightly run.

The screenshots are kept outside the repository.
