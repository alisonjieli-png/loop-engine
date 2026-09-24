# Release 23 live evidence, September 24, 2026

Kind: release evidence. The release record is
[`pilot-release-23.json`](../architecture-audit-2026-09-19/pilot-release-23.json).

Fly release 23 serves main revision `bcd05095` as image
`sha256:5fc60a3ded5522b0a6e8b4b3dc96e007f7bb39d5786d8c87993cb18662d6a10b`.
Continuous integration run 35986097491 passed on that exact revision, and the
guarded workflow run 35987773322 deployed it at 10:34 UTC. The deployment
setting was switched back to false afterwards. Rollback is Fly release 22,
image `sha256:76088e33805ca933ade44ac6629e20b4b2a22ded0201c034b95fee481ead931a`.
The host file was not changed.

## What the release changed

- The homepage leads with the library and names every harness Baltor sets up.
- Three use-case pages: `/overnight`, `/efficiency` and `/learning`, with the
  hub `/use-cases`.
- Get started is the sign-up and payment funnel. Get set up is the guide.
- No customer page offers an invitation, a waiting list or free search.
- Pi and the Baltor Harness have steps on the guide. The Pi extension is served
  at `/assets/pi/baltor.ts`.
- The terms of service carry the owner-authorized amendments to sections 2
  and 6.

## What was checked on the live service

| Check | Result | Files |
|---|---|---|
| Fifteen public addresses on eight hostnames | 120 of 120 answered 200 | `http-surfaces.tsv` |
| Capabilities on the eight hostnames | one identical record | `capabilities-*.json` |
| Health on the eight hostnames | ready, 3 of 3 required checks | `health-*.json` |
| Served Pi extension | 8 of 8 byte for byte the committed file | `pi-extension-digests.tsv` |
| Hosted browser acceptance | 163 of 163 on each hostname | `browser-*.json` |
| Catalogue | 6 of 6; 34 items offered, 9 withheld | `catalogue-check-2.json` |
| Service transport and isolation | 19 of 19, with the official protocol client | `service-check-2.json` |

## Failed first attempts, kept beside their successors

- The browser check ran first on four hostnames at once from one address. Each
  stopped at the examples step after a 30 second wait (`browser-baltor.ai.json`,
  `browser-www.baltor.ai.json`, `browser-app.baltor.ai.json` and
  `browser-baltor-pilot.fly.dev.json`). Run one hostname at a time, each
  passed 163 of 163 (the `-sequential-2` files). The cause is inferred, not
  measured: four anonymous browsers from one address can reach the service's
  limit of 30 refused attempts in 60 seconds.
- The first catalogue check found no key registered for `baltor.ai`
  (`catalogue-check.log`). The key is registered under
  `baltor-pilot.fly.dev`, and the successor names it with `--credential-host`.
- The first service check passed 16 of 17 executed checks, then stopped: the
  release worktree had no `.venv` link to the qualified protocol environment
  (`service-check.json`). With the link, the successor passed 19 of 19.

The service checks made two metered diagnostic reads on the `pilot-owner`
account. No model was called. Registration stays closed.
