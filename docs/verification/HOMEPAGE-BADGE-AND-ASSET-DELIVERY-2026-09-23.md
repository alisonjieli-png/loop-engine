# Homepage badge removal and public asset delivery

Kind: local repair and verification, September 23, 2026. Base revision
`d2e20413`. Live verification follows the checked release.

## Decisions and implementation

The owner asked to remove the pill above the homepage headline. The opening
now starts directly at the heading, and the two unused pill styles are removed.
Both local and hosted browser checks reject reintroducing that element. The
surrounding product explanation remains. The unmeasured "nothing drifts"
sentence now describes limiting drift as a design aim; the named homepage
claim check rejects the former absolute statement.

The responsive lab recorded 503 responses during four simultaneous page loads.
Its evidence identifies uncached assets and the proxy's 32-request hard limit
as likely contributors. The repair does not claim that inference is a measured
capacity model. It makes these bounded changes:

- Declared packaged non-HTML assets receive five-minute public caching and an
  exact-byte entity tag. Matching conditional GET and HEAD requests return 304.
- Served HTML appends each direct asset's digest as a version query so a new
  page selects current scripts, styles and icons after a release.
- HTML, APIs, protocol replies, errors and refused hosts retain `no-store`.
- Public pages and files support HEAD with matching content metadata and no body.
- Fly's proxy allowance becomes 64 requests soft and 128 hard, keeping the
  existing single machine, memory size and separate eight-operation API pool.

Version queries are cache-busters, not immutable-address enforcement: a caller
that supplies an old query can still receive current bytes after its cache
expires. Font references inside CSS retain their unversioned addresses and a
five-minute freshness window. No long-lived `immutable` claim is made.

## Evidence and preserved failures

| Observation | Result |
|---|---|
| Existing page against the new opening rule | Rejected: first element was a paragraph and one category pill existed. |
| Seven new HTTP checks before repair | Failed on cache policy, validators, asset versions and HEAD behavior. |
| The same HTTP checks after repair | Seven pass, including private/error responses and refused hosts. |
| Homepage and HTTP owning tests together | Fifteen pass. |
| Three removed asset guards | All detected: public caching, validator matching and versioned references. |
| First browser run after product changes | 483 of 549 passed. The old bare-URL interceptors missed versioned scripts, so the planted JavaScript failures were not applied. Brand and footer checks also assumed bare filenames. |
| Repaired browser test bindings | 551 of 551 pass, with all 91 removed-guard controls detected. Exact origin, path and version are checked; stale, missing, duplicate and foreign-origin bindings are rejected. |
| Independent review | No blocker in the scoped repair; seven HTTP tests, 48 Python 3.11 configuration tests, 15 asset metadata/conditional checks and three authenticated dynamic response checks passed. |

The [independent report](RELEASE-FIX-INDEPENDENT-QA-2026-09-23.md)
records source identities and limitations. The
[release evidence directory](../../artifacts/release-unblock-2026-09-23/)
preserves the initial failures and successor outputs. Browser checks were
adapted to the new URLs while preserving actual mutation coverage; no skipped
mutant was counted as detected.

The full audit initially reported three new endpoint findings. They were the
reserved `.invalid` strings in the new foreign-origin negative controls,
never network destinations. Each exact finding is registered as a test
fixture with an owner, reason and expiry in the existing allowlist. The
runtime endpoint rules and audit threshold remain unchanged.

The [Python 3.11 repair](PYTHON311-REVIEW-IMPORT-REPAIR-2026-09-23.md)
is included because the current main revision cannot pass that required job.
Full checks on the composed tree, GitHub checks for its exact committed
revision, guarded deployment and live hostname checks remain required.

Decision: ship these repairs together after those gates. Then repeat the
bounded four-page live test and measure resource failures and cache behavior.
The wider page-restoration patches and catalogue adjudication retain their
separate recorded acceptance requirements.
