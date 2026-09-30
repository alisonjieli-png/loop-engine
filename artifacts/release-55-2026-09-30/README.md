# Release 55: editable creative example and delivery housekeeping

Fly release 55 serves revision `5a9c6e2c5c768c1747754eca28a3101563477eca`.
Its [release record](../architecture-audit-2026-09-19/pilot-release-55.json)
binds the image, rollback to release 54 and verification evidence.

The public [Ashen Wilds demo](https://baltor.ai/demo/ashen-wilds) has original
Three.js characters, sword combat, three enemy waves, animation and lighting
controls, and GLB export. The scene downloaded from the live site passed the
browser checks, rendered in Blender and reopened in a fresh process with 892
meshes, four rigs and sixteen animation actions. It is not automatic video
recreation or evidence of an advantage over a model working without Baltor.

The release also includes audience-specific use cases, clearer manual harness
setup, a dated [MCP shortlist](https://baltor.ai/top-mcps), complete-package
resource handling, bounded source-intake tools and the updated delivery plan.
Large packages remain bounded by manifest and payload bytes; the old arbitrary
64-file cap no longer rejects otherwise valid packages.

## Checks and the deployment failure

CI run `36772005998` passed on the exact released revision in 395 seconds.
Its self-test job took 391 seconds. The first candidate's documentation job
failed because the prose checker treated CSS selectors as runtime terminology;
the narrow repair includes a real-search test that still refuses retired words
in the adjacent README, HTML and JavaScript.

Deployment run `36773368916` built and checked the image, then placed it on Fly.
The following grant-confirmation command received HTTP 408 after 65 seconds.
The workflow therefore remains recorded as failed. The deployment switch was
turned off. No new deploy was started to hide or repeat that result.

A read-only process check found no original grant command running. One bounded
detached invocation of the existing command then finished with exit zero in
213.536 seconds, retaining its reservation, output and exit record on the
volume. It preserved the account following the active 30,746-package release
and registered no accounts. Billing confirmation passed with no policy change,
no ended paid access and no provider call; checkout and portal match the host.

The grant command still builds the full search index to count grants. Billing
already has a lightweight loader. Fixing grant loading and durable workflow
confirmation is the next release-reliability repair, not a reason to remove
the check or extend a synchronous call indefinitely.

Live verification passed:

- 50 health/page/capability requests over all ten hostnames, with identity
  provider health also answering successfully.
- 40 new-route and exact-asset checks across those same hostnames.
- 227 public website browser checks.
- Seven live game interaction/export checks and six Blender reopen checks.
- Four rollback key-state checks against the real release 54 image, using
  synthetic local state and no container network.

The active catalogue remains `f817b2b3…`: 30,746 packages, 96,064 distinct files
and 130,568 file placements. This application release admitted no additional
library packages. Candidate intake, static checks, independent approval and
publication remain separate stages.

## Current plan and limits

The [delivery plan](../../docs/roadmap/DELIVERY-SEQUENCE.md) now orders customer
proofs, realistic with-and-without tasks, retrieval correctness and tracing,
Rust/cache qualification, video-to-harness recreation, broader file families,
model updates, OpenAI distribution and faster deployment. It includes legal
and other time-sensitive context, with current verification separate from
cached or historical material.

The [customer and history review](../../docs/verification/SESSION-REVIEW-AND-CUSTOMER-PROOFS-2026-09-30.md)
records the real new-account journey, latency samples, the four-call paired
test's invalid action scorer, source reads and incomplete semantic coverage of
the prior sessions. No general benefit claim follows from that small trial.

Private evidence is under
`/home/username/baltor-private/session-review-20260930-GYFErD`.
Do not publish that folder wholesale: it includes protected account state and
credential stores alongside the safe reports whose hashes the release record
names. Failed attempts remain preserved.
