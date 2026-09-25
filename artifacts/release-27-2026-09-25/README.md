# Release 27 evidence, September 25, 2026

Fly release 27 of `baltor-pilot` went live at 10:24 UTC from main
`f902d915bd7f8586762da2962311b6271767e1fd` after continuous integration run
36120351397 passed, through deployment run 36123608871. The image is
`sha256:28b246e158312396f20b0c47d5f31553aa6e589eebfa4d0cfa773bf25388021e`;
the rollback target is release 26. The record is
[`pilot-release-27.json`](../architecture-audit-2026-09-19/pilot-release-27.json).

## What a person sees now

- The homepage hero shows the working directory one step of a task gets, and
  three demonstrations run start to finish: a simple task, a long job overnight
  and a Kaggle solution.
- Each hostname opens its own page, and the site has demonstration, status,
  examples and case study pages and the four /for pages, which answered 404
  before this release.
- The phrases the owner called meaningless are gone from every page.
- Eight fixes from the persona journeys: sign-up, sign-in, setup, prices,
  Security, the Pi link and the phone menu.
- The deck opens at deck.baltor.ai and /deck, and a free directory of protocol
  servers and agent APIs opens at /directory.

Earlier the same morning, on release 26, new and existing customer accounts
started following the catalogue release, so the next catalogue release
reaches every customer without a redeploy (`catalogue-follow-*.json`).

## How it was checked

| Check | Result |
|---|---|
| What a person sees: 41 pages at desktop and phone width, light and dark, and 8 hostnames (`people/report-after-the-load-wait.json`) | no problem; 83 links checked |
| The customer's search and download with the homepage digest guard | 8 of 8 |
| The service transport and isolation | 19 of 19 |

Advice: 135 of 135 addresses answer on nine hostnames with identical
capabilities, the Pi extension matches on all nine, and the detailed browser
rules pass 215 of 215. The first run of the people check timed out on the two
directory addresses because it waited until every request stopped; both open
in about half a second with their heading, and the check now waits for the
load and a short moment (`people/report.json` keeps the first run). The
screenshots are kept outside the repository.
