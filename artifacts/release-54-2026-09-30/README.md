# Release 54 and the September 30 catalogue update

The website is running release 54 from `1d35f6976264ee7188a7d4179e69fa6c171d57e2`.
CI run 36728313395 passed, and deployment run 36729597142 completed the image,
grants and billing-policy steps. The deployment setting was returned to false.

The public library page and homepage distinguish distinct files from packages.
The worker download, Compose configuration and operating guide are available
at `/worker` and `/docs/container-worker`. The deck no longer loads an unused
stylesheet. Scheduled MCP and model-directory updates are included.

The worker image includes OpenCode 1.17.9 and the Baltor text-response harness.
Publication run 36729360796 passed. The published image was pulled by digest
and passed twelve installed-process checks without an external model call:
`ghcr.io/alisonjieli-png/loop-engine@sha256:0cbfc345ccbd1fdf3dca6abba61d40eaff6ecf41e781eeecd211883cf37fd5aa`.
These checks establish installation and fresh process mechanics. The operating
guide states the execution profiles and their limits.

The independently approved catalogue additions were held by an old combined
schema that omitted `component_form`. Recombining the existing reviewed
material with the current schema declaration changed no prior package payload.
The published release adds 2,935 packages and 7,691 distinct files. It now
contains 30,746 packages and 96,064 distinct files. Existing package payload
digests all survived; the publication record's 27,811 changed item versions
reflect catalogue metadata changes, not new payload files.

The website passed 226 anonymous browser checks. After catalogue activation,
60 route and population checks passed across ten origins. The visitor pass
opened 60 pages in 249 views and checked 357 links. Its two failures were the
same external GitHub destination returning 503 through the directory link;
the focused repeat observed Baltor's 302 and GitHub's 200. The original failed
report remains retained. The published worker passed twelve checks.

The [release record](../architecture-audit-2026-09-19/pilot-release-54.json)
pins the source, images, rollback and evidence. The
[inventory reconciliation](../library-audit-2026-09-30/README.md) explains
candidate, qualification and publication counts.
