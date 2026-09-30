# September 30: release 55 and the ordered delivery plan

Kind: dated handoff. Read [AGENTS.md](../../AGENTS.md#commit-push-and-release-authority),
the current task and the actual Git/process state before continuing. The
[roadmap](../roadmap/roadmap.yaml) owns status; the
[delivery and business plan](../roadmap/DELIVERY-SEQUENCE.md) owns the current
sequence and acceptance gates. This record grants no additional authority.

## Released and checked

Reviewed inherited work and the new changes reached main in `9dbd9958`.
The CI wording correction followed in `5a9c6e2c`, which passed CI run
`36772005998` and is the source of live Fly release 55. The
[release record](../../artifacts/architecture-audit-2026-09-19/pilot-release-55.json)
and [release notes](../../artifacts/release-55-2026-09-30/README.md) name its
image, rollback, live checks and failed-workflow reconciliation.

The image is running and healthy. The guarded deployment placed it, then the
synchronous grant step hit a Machines API timeout. No prior grant process was
running before one bounded detached confirmation was started; that confirmation
finished in 213.536 seconds with exit zero. Billing confirmation passed without
a policy change, ended paid access, new account or provider call. The deployment
switch is off. The failed workflow remains recorded as failed.

Live checks: 90 public route checks over ten hostnames, 227 website browser
checks, seven game interaction/export checks and six Blender reopen checks.
The live [Ashen Wilds example](https://baltor.ai/demo/ashen-wilds) exports editable
geometry, four rigs and sixteen clips. Gameplay remains JavaScript. The live
[MCP shortlist](https://baltor.ai/top-mcps) uses dated source links and stars
within an editorial selection, not a quality or Baltor-usage ranking.

The active catalogue is unchanged at `f817b2b3…`: 30,746 packages and 96,064
distinct files. This application release published no new catalogue packages.
Npm discovery rotation, complete-package resources and import-cache invalidation
are committed; the 79-file FFmpeg skill archive is not thereby admitted.

## Customer and history evidence

The [review record](../verification/SESSION-REVIEW-AND-CUSTOMER-PROOFS-2026-09-30.md)
has the exact scope. A real new account passed signup, sign-in, scoped-key,
client search/download, native placement and byte verification. Automatic
native activation and a demanding accepted task remain separate.

Four OpenCode/Gemma 4 calls compared an eight-row task with and without the
downloaded skill. Both normalized every value correctly. The action scorer
over-specified one label, so its apparent benefit is invalid. Preserve those
original results and the diagnosis. Do not advertise an accuracy or latency gain.

The history inventory covers 156 previous project sessions and 569 top-level
prompt entries. Long entries were initially inspected through excerpts; all
assistant, delegated and command bodies were not fully reviewed. The audit is
not a completed semantic review of every turn. Private histories stay private.

Two Reddit34 API reads succeeded; the integrated read produced 20 research
work orders from 25 posts, not components. No recurring Reddit intake, model
expansion or publication timer was activated. The key is in Secret Service;
47 requests remained in the provider's reported allowance after those reads.

## Decisions and next work

1. Repair deployment grant confirmation before the next application rollout.
   `apply_host_grants` still builds the complete serving index to count grants.
   Billing already uses `load_host_billing_context`; the September 29 description
   of billing's full-index load is historical. Keep outcome reconciliation,
   exact source checks, the grant checks and paid-access protection.
2. Freeze a realistic customer pipeline comparison, including quality,
   standardization and entity matching. Reuse native harness and usage-capture
   infrastructure, use live customer retrieval, keep acceptance cases out of
   the harness workspace and prove the scorer's known-wrong controls before
   counted calls. Then do an editable creative revision task. The plan covers
   the remaining parametric, debugging and Kubernetes families.
3. Make retrieval failures replayable and traceable, then compare scoped caches
   and a selectable Rust engine on matched relevance, access and cost tests.
   Hosted search is still Python/SQLite FTS5 plus character-hash vectors.
4. Build the supported video-intake, timestamped explanation, component selection,
   harness preparation, editable variation and clean-reopen chain. It does not
   exist end to end today. Missing effects must remain explicit gaps.
5. Continue complete-package admission, broader native files and recurring source
   work through the current pipeline. Keep prompts, templates, guidance,
   reference data, tests, executable code and creative assets in the mix.
   Source rights and independent admission still control publication.

The plan also records OpenAI plugin eligibility and limits, OAuth and publisher
verification, Blender execution profiles, support-chat recovery, model updates
including a possible Gemini 4 release, deployment caching/deltas and freshness
through the harness. No OpenAI plugin is published; no new legal pages were
approved or published. The unmerged support worktree at
`/home/username/.le-support-20260924` was preserved and inspected, not merged.

Three regulatory research questions now separate authoritative legal changes
from performance evidence and require jurisdiction/as-of/effective-date checks.
The 76 knowledge-radar, pipeline and model-watch checks passed, including an
expired legal-listing fixture. This is internal context repair, not legal advice
or worldwide legal qualification. The wider harness freshness gates remain work.

## Evidence and local housekeeping

Private material is under
`/home/username/baltor-private/session-review-20260930-GYFErD`.
It contains preserved inherited changes, failed attempts, audit projections,
customer reports, screenshots, the paired trial, live checks and Blender output.
It also contains protected account and native credential-store state; never
copy it wholesale into public artifacts or model context.

The local full self-test passed 3,688 checks; browser checks passed 958 with
197 negative controls. Earlier tool runs failed on stale calibration source
bindings, a static route parser, cached assets changing during a run and this
machine's `/tmp` execution behavior. The repairs and focused reruns passed,
then CI passed the exact release across its Python-version matrix. The normal
provenance, path and package-digest guards were not removed.

A first local wheel included one retired Python module from the old build
cache. A clean source export removed that contamination and matched all 793
current module paths. CI's clean installation is the exact-release check.
Preserve the failed wheel and report; use a clean build/export and compare
the wheel inventory with source rather than trusting a successful build exit.

No future-model account, rendering subscription, extra infrastructure or ad
purchase was made. Existing scheduled jobs were not replaced by the new readers.
