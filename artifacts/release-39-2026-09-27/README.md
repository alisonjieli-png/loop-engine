# Release 39: one component library

Fly release 39 applied commit `e5d21e899c6d6c8b7791288aa9ef762917e483bc`
on September 27, 2026 at 03:58:55 UTC. It removes the customer-facing
Verified and Community split, combines kind counts, and keeps source,
licence, effects and review details available for each component.

## Release and reconciliation

The [release record](release.json) binds the source tree, image, previous
image, continuous integration and checks. Continuous integration run
[36292492189](https://github.com/alisonjieli-png/loop-engine/actions/runs/36292492189)
passed. Deployment workflow
[36292845987](https://github.com/alisonjieli-png/loop-engine/actions/runs/36292845987)
failed after applying the correct image: its grant-following command exceeded
the remote command's twenty-second deadline.

The operator checked the running image and process state, inspected the
command's repeat behavior, and replayed the exact grant application with an
explicit 120-second timeout. The existing account followed the catalogue
with 7,806 items. Applying billing policy made no change and created no
remote account. The workflow failure remains recorded; successful
reconciliation does not change its conclusion. The deployment gate was
closed and read back as false.

## Live checks

- All ten hostnames passed root, health, registration and visible-heading
  checks. Sixty versioned asset digests matched the committed source.
- The visitor check covered 54 pages, 225 views and 319 links with no
  reported problem and saved 108 screenshots.
- Authenticated catalogue checks passed nine of nine. Service and protocol
  checks passed nineteen of nineteen.
- The public library showed 7,806 components across eleven kinds in one
  combined count table. Ten public pages and guides had no visible class
  labels or selectors.
- A real signed-in test account browsed the six-column table and opened a
  manifest. A 390-pixel follow-up exposed horizontal page scrolling from the
  long customer identifier heading. This is an open finding at release 39.

The following source patch wraps that heading and makes the sample source
appendix collapsible. Its local tests do not establish that the patch is
already deployed. The original sample body remains unchanged.

The exact exported release tree passed all sixteen local preflight gates.
Earlier browser checks passed 941 of 941 cases and 195 guard controls;
the later Pi guide and authority wording received their own checks. One
documentation layout advisory remains: the index exceeds a duplicated
1,800-pixel content-order budget while retaining correct order and navigation.
Its failed result remains visible under the owner's human-oriented release
policy.

These observations establish the recorded public and selected account
journeys. They do not establish paid conversion, every native harness, or a
model-driven end-to-end task. Private evidence stays under
`/home/username/baltor-private/ui-deploy-20260926` and
`/home/username/baltor-private/growth-20260927/fresh-run-001`.
