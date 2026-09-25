# Fly release 36, September 25, 2026

Kind: dated release record. The typed record is
[pilot-release-36.json](../architecture-audit-2026-09-19/pilot-release-36.json).

| Fact | Value |
|---|---|
| Source revision | `cd0794772a9d1da35b074457f88a4272f58ed57c` on `main` |
| Continuous integration | run 36199029654, passed (22:57 to 23:20 UTC) |
| Browser suite on this revision | nightly workflow run 36199031805, started by hand (22:57 to 23:08 UTC): 909 of 909 checks, 183 of 183 removed-guard controls |
| Deployment | guarded workflow run 36200624566 (23:20 to 23:23 UTC); the Machine restarted at 23:23 UTC |
| Image | `sha256:b1198bff6eb3d0f7175d1261098f866d1e690a5b835f1030ba08169e473a6567` |
| Rollback | release 35, image `sha256:2778dce49bc303977543af49ee06f4529a09f4741ae437ec63e2e15d8820f210` |
| Live checks | people 45 pages, 188 views, 8 hostnames, 310 links, 0 problems; catalogue 9 of 9; service 19 of 19; 135 of 135 addresses answer 200; Pi extension 9 of 9; detailed browser rules 216 of 216 |
| Host file | unchanged |
| Catalogue after the restart | release `11a2974d…`, 1,629 packages, built from the store at 23:23 UTC; see [community-release-3](../community-release-3-2026-09-25/README.md) |

The release carries the request screening station, the `text_model_json`
engine kind, the rules engine's screening answerer, the gateway's
credential passthrough and the decision red team (S-6.198). Nothing a
visitor sees on the website changed; the library page shows the 1,629
packages of the catalogue release published a minute before the restart.
The train ran unattended from the push.
