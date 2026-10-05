# Release 62: private Dot work and general submission policy

The broader privacy notice and private Dot work log are live. The
[release record](../architecture-audit-2026-09-19/pilot-release-62.json) binds
source `75e3cabde6b4f25f4a7f015312f7aead7eafd009`, CI 37250819264,
deployment 37251239136 and the observed Fly image. Completion was October 5
UTC, October 4 in the owner's time zone. The deployment gate is off.
Release 61 is the rollback image. No credential or host configuration changed.

## Available interfaces

Authorized administrators can use `/admin#dot-work` to save research, test
results, component candidates, source links and UTF-8 text/code files, read
reports and reply. `GET/POST /api/v1/admin/work`, `staff_work_read` and
`staff_work_submit` use the same managed records. The
[operating guide](../../docs/guides/customer-feedback-and-requests.md) states
exact fields, permissions and limits.

The owner-approved [privacy notice](../../docs/legal/PRIVACY-NOTICE.md)
covers voluntary submissions and authorized data exchange for operation and
improvement, not only staff submissions. Individual permissions still apply.
Uploads do not execute code, publish components, call models or transfer
content to unrelated services. Public Dot briefs retain noindex and navigation
exclusion; they are public content, not confidential storage.

## Fresh verification

- All ten hostnames passed 2,118 browser assertions and fifty additional
  exact-brief, capability, anonymous-refusal and readiness checks.
- Public Good/Dot passed sixty checks, including all 1,011 useful file digests.
- Twelve private micro-component reports passed exact name, content, byte-count
  and hash readback for 108 attachments containing 86 distinct digests. Exact
  repeated requests returned the same records. The upload used 37 requests,
  no new credential, no model call and no catalogue publication.
- The browser created two labelled synthetic reports, including a reply.
  Save, read, exact BOM/CRLF download and reconnect passed. Its first attempt
  passed fourteen of fifteen checks, then timed out because the probe clicked
  mobile sign-out without opening the menu. A GET/HEAD-only continuation
  passed seventeen checks on desktop and phone, including clearing private
  details and unsaved drafts. It repeated no report writes.

Locally, 959 browser checks and all 197 known-wrong controls passed, alongside
63 Dot/work-log/site-map, 67 context/documentation, 64 supply and eight final
Dot tests. Exact-candidate CI and conformance passed. Thirty-three supply
audit findings were reviewed as JSON Schema syntax, inert examples and
credential-variable names. Exact finding/owner exceptions passed thirty-three
original and thirty-three changed-literal controls; no classifier or baseline
was relaxed. Private upload-verifier and deployment-binding defects were also
repaired and tested. All failed attempts remain in the private evidence.

## Counts and limits

The catalogue remains 30,751 packages and 96,120 distinct files. Its release ID
and state revision were unchanged after private uploads. Public Good remains
412 packages and 1,011 useful files, with explicit associations in five goals.
Private candidates and repeated support files do not increase those counts.

The first work-log profile accepts sixteen UTF-8 files, 64 KiB each and
256 KiB total, subject to transport limits. There is no automatic expiry.
Lists return at most one hundred matches by UTC day/task, with a completeness
flag. It is not a binary repository, exclusive task queue or automatic publisher.

The actual owner's Dot session was not used. Ordinary customer OAuth does not
inherit administrator permission. Browser restoration saves the access token,
but `service.js` configures automatic provider refresh off. Continuous Dot
administration and renewal need a separate test; no live expiry duration is
inferred from source defaults. Customer OAuth evidence from release 60 was
not rerun. No schedule, outreach, advertisement or purchase was started.

Full customer acceptance, supported-harness breadth, confinement, chart
publication, sustained load/recovery, all-SDG supply and measured benefit
remain open. The old scheduled catalogue publisher remains fenced.
Private evidence is under `release62-dot-20261001-AYlypd` in the authorized
workspace. Private report bodies, account identities and credentials are not
included in this public record.
