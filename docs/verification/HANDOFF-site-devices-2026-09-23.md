# Handoff: website responsive lab

Kind: verification handoff. Written on September 23, 2026 by the session
that built the responsive lab, when the owner asked every line of work to
wrap up. The work is partial: the lab is built and tested, and a bounded
capture ran against the live site; the full sweep, the comparison with
other websites and the review of every screenshot did not run.

Worktree: `/home/username/.le-integration/site-devices`, detached, started
at `243a8811` (main, live as Fly release 20). No branch was made and nothing
was pushed.

## What is done

- [capture_website_devices.mjs](../../tools/capture_website_devices.mjs):
  the lab. Screenshots of the first screen and the full page, a scroll run
  in steps of 80 percent of the screen, anchor jumps, the phone menu,
  disclosures and tab sets, and the measures listed in the
  [guide](../guides/website-responsive-lab.md). It also writes one contact
  sheet per page, compares with an earlier metrics record (`--compare`) and
  measures other websites read-only (`--benchmark`).
- [website_devices.json](../../tools/website_devices.json): 20 devices, 13
  special cases (text at 200 percent, dark, reduced motion, WebKit, Firefox,
  throttled), the release 20 pages, the pages of the target site map, the
  budgets and the thresholds.
- [website-responsive-lab.md](../guides/website-responsive-lab.md): how to
  run it. The web assets README was left alone because other sessions are
  editing it.
- [WEBSITE-RESPONSIVE-LAB-2026-09-23.md](WEBSITE-RESPONSIVE-LAB-2026-09-23.md):
  14 findings ranked by severity, each with a fix in the site's tokens and
  class names, and what was checked and found sound.
- Two metrics records in `artifacts/website-audit-2026-09-23/`: attempt 1
  (degraded, kept) and attempt 2 (the result).
- Firefox 153.0 and WebKit 26.5 were installed for Playwright under
  `~/.cache/ms-playwright`.

## What is left, in order

1. Run the whole lab against live release 20, every device and special case,
   14 pages and seven hostnames (command below). About 700 captures; at two
   page loads at once, expect well over an hour.
2. Run the comparison with eight to ten developer tool websites, homepage
   and pricing page only, at 1440x900 and 390x844, with `--benchmark`, and
   add the table to a new dated report.
3. Review every screenshot and contact sheet device by device, including
   the widths from 860 to 1100 pixels, and ask one or two reviewers for a
   second opinion on the contact sheets. Record where they disagree.
4. Phase B: fix the findings in the integrated build, then rerun the lab
   against it with `--compare` pointing at the attempt 2 record.

## Checks run and their results

| Check | Result |
|---|---|
| `node --check tools/capture_website_devices.mjs` after every edit | Passed |
| Launch of Chromium, Firefox and WebKit at 390x844 against the live homepage | All three loaded it with status 200 |
| Lab attempt 1, 24 captures, four page loads at once | 24 finished, 0 errors; several loads received 503 answers for style sheets and scripts, one rendered unstyled. Kept as a failed attempt |
| Lab attempt 2, 48 captures, two page loads at once | 48 finished, 0 errors, 0 degraded, 0 retried |
| WebKit console error source, 1 capture | 3 refused inline styles for 3 screenshots, so they come from the lab |
| Overlap measure after skipping closed disclosures, 4 captures | 0 overlaps, where attempt 2 had listed false ones |
| Hardcoding audit, unchanged worktree at `243a8811` | Exit 0; 632 high, as on main |
| Hardcoding audit with the two lab files | Exit 0; 632 high, no new high; medium findings from 19,408 to 19,420 |
| Hardcoding audit after the last tool edit | Exit 0; 632 high, no new high; 19,420 medium |
| Markdown structure, `markdownlint-cli2` 0.23.2 over the declared set | 673 files, 0 issues, after renumbering the report's findings |
| The two retired-language searches of the documentation job, on the three new documents | No match |
| Conformance, self-test and tool tests | Not run: this change adds no Python and no source the gates read |
| Vale | Not run; it is not installed on this workstation |
| Local links and section anchors | Checked by a short script on the three new documents, every link and anchor resolves; the link checker itself was not run |

## Known failures and limits

- The attempt 2 record lists false overlaps inside closed disclosures and
  anchor jumps from links in hidden views. Both measures were corrected in
  the tool after the run; the report says so where it uses them.
- In the attempt 2 record the first screenshot of the dark case shows the
  footer, because the appearance switch is in the footer. The tool now
  scrolls back to the top before that screenshot. The dark measures are not
  affected.
- The layout shift of `/connect` varies with the service answer time: 0.13
  in attempt 1 and none in attempt 2 at 390x844.

## Commands to continue

From the worktree root. Each run needs a new screenshot folder and a new
metrics path.

```bash
ln -s /home/username/loop-engine/showcase/node_modules showcase/node_modules
node tools/capture_website_devices.mjs \
  --base https://baltor.ai \
  --hosts https://www.baltor.ai,https://app.baltor.ai,https://docs.baltor.ai,https://status.baltor.ai,https://examples.baltor.ai,https://demo.baltor.ai,https://baltor-pilot.fly.dev \
  --out /home/username/.le-ci-tmp/site-audit/devices-full-1 \
  --metrics artifacts/website-audit-2026-09-23/responsive-metrics-live-release-20-full-1.json \
  --concurrency 2
```

Against a local build, replace `--base` with the local origin, drop
`--hosts`, add `--page-set all` and
`--compare artifacts/website-audit-2026-09-23/responsive-metrics-live-release-20.json`.

## Live and external effects

- About 90 signed-out page loads of the live site, from 8 configurations,
  plus their assets, in bursts of two to four at once. Attempt 1 drew 503
  answers from the live service for some assets.
- A few `curl` reads of each of the eight hostnames and of the style sheet
  headers.
- Downloads of the Firefox and WebKit builds from the Playwright download
  host.
- No form was submitted, no account or key was used, nothing was deployed or
  pushed, and no other website was loaded.
