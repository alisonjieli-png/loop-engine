# Fly release 37, September 26, 2026

Kind: dated release record. The typed record is
[pilot-release-37.json](../architecture-audit-2026-09-19/pilot-release-37.json).

| Fact | Value |
|---|---|
| Source revision | `43b421f8c0be90e98ae32b0994aa8ba9ecb8e7f0` on `main` |
| Continuous integration | run 36243640251, passed (12:59 to 13:22 UTC), after two refused revisions: `edcc77a3` (a docs folder without its charter README) and `76e14faa` (the generated records index not regenerated) |
| Deployment | guarded workflow run 36244935164 (13:22 to 13:25 UTC); the Machine restarted at 13:25 UTC |
| Image | `sha256:7e0603e219fe21ca934d9459f8bc94a734ce2f31baaf4da8a8ae63c3edd382f8` |
| Rollback | release 36, image `sha256:b1198bff6eb3d0f7175d1261098f866d1e690a5b835f1030ba08169e473a6567` |
| Live checks | people 45 pages, 188 views, 8 hostnames, 310 links, 0 problems; catalogue 9 of 9; service 19 of 19; 135 of 135 addresses answer 200; Pi extension 9 of 9; detailed browser rules 216 of 216 |
| Host file | unchanged |
| Catalogue after the restart | release `856bff51…`, 6,398 packages, built from the store; see [community-release-6](../community-release-6-2026-09-26/README.md) |

What a person sees differently: the library page at `/library` now counts the
library by every kind of file a harness picks up and by its label, shows one
item in full, and sends the visitor to create an account instead of listing
items one by one with their sizes and digests. A signed-in account's library
is one searchable, sortable table with the purpose, the kind of file, the
label, the step functions, the licence, the declared effects and the tools
each file is written for. Search results show step function tags once a
release carries them; the first tagged release is the next daily slot's.

The release also carries the day's engine work that a visitor does not see:
the balanced kind mix of the export, the executable-code route at Community,
the step function tagging slot, the served attribute declarations and the
list-row attributes (S-6.205, S-6.206, S-6.208), plus the scheduled refreshes
of the MCP directory and the model directory. The train ran unattended from
the push after the two refused revisions were repaired.
