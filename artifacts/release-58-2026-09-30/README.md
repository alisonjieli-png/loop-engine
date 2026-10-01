# Release 58 OAuth and Public Good delivery

Public Good is linked from the main header at `/public-good`. Its initial
collection has ten already-admitted packages and fourteen distinct useful
files. Browsing metadata is public. Downloading a selected version requires
an enabled account, but no paid subscription. Ordinary private and paid
access remains separate.

OAuth is live at the existing `/mcp` endpoint. The flow uses the normal
account, explicit consent, authorization codes, S256 proof keys, exact resource
binding, scoped tokens, expiry, refresh rotation and revocation. No long-lived
API key needs to be copied into a prompt. Existing key clients remain supported.

The [release record](../architecture-audit-2026-09-19/pilot-release-58.json)
names the exact source, image and rollback. CI 36806897008 and guarded
deployment 36807534138 passed. The `pilot` deployment gate is off.

## Checks and limits

Final checks cover ten hostnames: 2,118 browser assertions, 50 route requests,
147 documentation assertions and 57 Public Good assertions. Earlier failures
remain in the private audit. One final host rerun used the unchanged deployed
web-asset snapshot; a comparison against newer uncommitted assets was invalid
and is not counted as production evidence.

A live customer probe completed sign-in, explicit consent, code exchange,
MCP search and exact delivery of one 2,363-byte instruction file. It checked
refresh, narrower scopes and revocation of its newly created QA delegation.
Paid usage did not increase. The account already has founding free monthly
access, so that probe does not establish an unpaid production journey.
Synthetic account, HTTP and browser checks cover the unpaid route. The
owner's actual dot and marketplace submission remain untested.

The production Python 3.12 image passed fifty focused OAuth checks after
repairing the SDK exception interaction and byte-exact issuer metadata.
Public Good final delivery checks prevent late or over-size responses from
creating successful-delivery records. These records are not yet the requested
per-download activity timeline or proof that the client received the bytes.

## Maintenance and supply

Two read-only policy plans exceeded 180 seconds because the ordinary loader
validated the whole catalogue. Neither installed a policy. A reviewed
selected-version operator retained full release membership checks and verified
all files of the selected versions. The live plan took 0.2041 seconds and the
guarded apply 0.1652 seconds. This is a maintenance observation, not a
controlled search benchmark or evidence for rewriting search in Rust.

The application release did not change the 30,746-package, 96,064-distinct-file
catalogue. A larger free-access selection and five new independently admitted
original packages are separate publication work. Targets of one thousand
useful Public Good files and coverage of every SDG remain unfinished at this
release. Supporting manifests, licences and repeated bytes do not inflate
the useful-file count.

Private evidence is retained under
`/home/username/baltor-private/release58-20260930-VrOYyv` and
`/home/username/baltor-private/oauth-20260930-QGXZyh`.
Do not publish these directories wholesale: customer-operation state and
credential handling belong outside the public repository.
