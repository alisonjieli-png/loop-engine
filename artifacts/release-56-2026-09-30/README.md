# Release 56

Fly release 56 deployed `e089582c` on September 30, 2026. Its CI and guarded
deployment workflow passed. The deployment gate is off. The
[release record](../architecture-audit-2026-09-19/pilot-release-56.json) names
the exact source, image and release 55 rollback image.

Grant maintenance skips the unused web bootstrap and search build, while
retaining body, policy, withdrawal and catalogue-state checks. The workflow
reserves a bounded operation once and polls its saved result after a lost
reply. Grant confirmation took 46.152 seconds; the preceding recorded operation
took 213.536 seconds. This is a deployment observation, not a search-latency
benchmark. Billing confirmation took 0.831 seconds, changed no policy and ended
no paid access.

The website deck and explanatory pages describe the broader file library and
editable browser demo. The plan includes customer activity, free Public Good
components starting with worker protection, owner-generated B-roll, large-media
delivery and the creative-sourcing research. These additions to the plan are
not claims that those services have launched.

[Captioned marketing drafts](../marketing-drafts-2026-09-30/README.md) include
a thirty-second portrait video and a two-minute landscape pitch, with editable
sources and captions. They have no narration or music and use no outside footage.

## Checks and remaining gap

The deployed container passed 22 image checks and 744 service checks. Local
self-tests passed 3,688 checks. Browser checks passed 958 checks and all 197
negative controls. The live pulse passed 50 requests over ten hostnames. The
hostname browser checks passed 2,110 checks in total after correcting the
standalone-page assumptions in the checker. The live game passed seven checks,
including revision and export. A real existing engineering account passed
sign-in, scoped-key, search and verified-download checks. This is not a new
customer-task or model-benefit benchmark.

The catalogue check passed seven of nine checks. The remaining failures found
older demo hashes presented beside a newer live catalogue. The current client
received the correct active version; the guided examples need explicit snapshot
scope and a source binding. That correction is the next release. Do not report
the release 56 catalogue check as entirely passing.

The initial candidate CI run `36784056225` failed on an unlisted-page link and
raw operator-mode tokens. The corrected revision passed `36785879432` without
loosening the guards. Earlier draft, browser, credential and rollback-probe
failures remain in the private audit records. No new catalogue packages were
published: the active release still contains 30,746 packages and 96,064 distinct
files. The million-file target remains unfinished.
