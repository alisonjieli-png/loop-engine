# Fly release 35, September 25, 2026

Kind: dated release record. The typed record is
[pilot-release-35.json](../architecture-audit-2026-09-19/pilot-release-35.json).

| Fact | Value |
|---|---|
| Source revision | `2cc06eb7810d3d3088bad30a0cc42fbfa005d4a3` on `main` |
| Continuous integration | run 36194030862, passed (21:54 to 22:19 UTC) |
| Browser suite on this revision | nightly workflow run 36194061979, started by hand: 909 of 909 checks, 183 of 183 removed-guard controls |
| Deployment | guarded workflow run 36196169822 (22:19 to 22:22 UTC); the Machine restarted at 22:22:20 UTC |
| Image | `sha256:2778dce49bc303977543af49ee06f4529a09f4741ae437ec63e2e15d8820f210` |
| Rollback | release 34, image `sha256:a914f340558115a940de44eed8712037f887744867adf3e47517ed5150868936` |
| Live checks | people 45 pages, 188 views, 8 hostnames, 339 links, 0 problems; catalogue 9 of 9; service 19 of 19; 135 of 135 addresses answer 200; Pi extension 9 of 9; detailed browser rules 216 of 216 |
| Host file | `license_policy` set at 21:43 UTC (backup `/data/host.json.before-license-policy-20260925T214308`), loaded by this restart |
| After the restart | the 316-package Community release was published at 22:35 UTC without a redeploy; see [community-release-2](../community-release-2-2026-09-25/README.md) |

The release carries the imported-package review reader (S-6.196) and the
wording reconciliation (S-6.181). The release train ran unattended from the
push: it waited for continuous integration, dispatched the guarded workflow,
switched the deployment setting off again and ran the live checks.
