# Release 26 evidence, September 25, 2026

Fly release 26 of `baltor-pilot` went live at 08:46 UTC from main
`f371ef2c47ea99337c0a1b931288992120cfb7a6` after continuous integration run
36112660683 passed, through deployment run 36114550607. The image is
`sha256:863bec3ef5294949c9a3567046d6cb2238a54d1ae85e13e7e6c4839a2b8b3a80`;
the rollback target is release 25. The record is
[`pilot-release-26.json`](../architecture-audit-2026-09-19/pilot-release-26.json).

## What changed

Mostly work a visitor does not see: the functional component standard,
decision stations, the review engines and the two-family quorum, the licensed
import, and the Verified and Community library tiers. The homepage lost the
filler line under its buttons. The deploy workflow now releases any checked
revision on main even after main moves on, so lines no longer stop pushing
during a release. The engine selector and the staff tools were held for a
release of their own.

## How it was checked

The owner asked on September 25, 2026 for checks that are "more flexible,
reasonable, and human oriented". Two kinds of check decided this release:

| Check | Result |
|---|---|
| What a person sees: every page of the site map at desktop and phone width, light and dark (`people/report.json`; the screenshots are kept outside the repository) | 0 problems on every built page; 5 pages the site map listed but nothing built answer 404, as before this release |
| The customer's search and download with the homepage digest guard | 7 of 7 |
| The service transport and isolation | 19 of 19 |

Advice, which does not decide: 135 of 135 public addresses answer 200 on nine
hostnames with identical capabilities, the Pi extension is served byte for
byte on all nine, and the detailed hosted browser rules pass 161 of 163 on
baltor.ai. The two failures are rules that still expect the line the owner
retired; release 27 updates them.
