# Release 38: the orange redesign

Deployed September 27, 2026 at 01:19 UTC, or September 26 at 9:19 PM Eastern.
The owner asked Codex to complete the interrupted Claude deployment. The release
combines the foundation, homepage, library, account, funnel, content and
documentation/state work, including the captured uncommitted refinements.

## Exact release

- Source: `13caeb2039c28681e8c8793cfede80255e6f033a`.
- Tree: `540874361ba01306d6fcc857a6203e459f2ac614`.
- Image: `registry.fly.io/baltor-pilot@sha256:e3af395c828eeea9726369cd08c70deb7dcb13096abdfe47edab26b7ea684e7e`.
- Previous image retained: `registry.fly.io/baltor-pilot@sha256:7e0603e219fe21ca934d9459f8bc94a734ce2f31baaf4da8a8ae63c3edd382f8`.
- [Successful continuous integration](https://github.com/alisonjieli-png/loop-engine/actions/runs/36284690803).
- [Successful guarded deployment](https://github.com/alisonjieli-png/loop-engine/actions/runs/36285062623).
- `FLY_DEPLOY_ENABLED` was returned to `false` and read back after the run.

The [release record](release.json) records identities, counts and limitations.

## What changed and what was checked

All 24 changed page sections were retained during integration. The shared
navigation was preserved. The integration repaired initial server-rendered view
selection, restored-account loading order, cached documentation tabs, standalone
subdomain Home links and enlarged-text overflow. Regression cases and removed-rule
controls accompany the repairs.

All sixteen local preflight gates passed on the exact exported tree, including
3,683 self-test checks. Continuous integration passed twenty required jobs;
the manual model job was skipped. The bounded final layout checks passed twenty
responsive cases, twenty-four public-page cases, navigation, disclosures, search
and ten known-wrong controls.

The [full local browser report](browser-checks.json) passed 930 of 931 checks and
detected all 191 guard mutations. Its remaining case-study length finding is
preserved. The owner subsequently authorized larger case-study budgets; that
policy change is a separately checked follow-up. It does not remove page content.

## Live verification

- Ten hostnames returned the expected root page and healthy dependencies. Their
  versioned assets match the committed source.
- Fifty public-address checks passed, with consistent capabilities and a healthy
  identity provider.
- The [visitor check](people-checks.json) passed 54 pages, 225 views and 348 links
  with no problems. It saved 108 screenshots. A separate
  [visible-heading check](visible_headings-checks.json) confirms the four
  single-page-application subdomain roots; the main report's first-heading field
  can otherwise name a hidden homepage heading.
- [Catalogue checks](catalogue-checks.json): nine of nine passed.
- [Service and protocol checks](service-checks.json): nineteen of nineteen passed.
  An earlier probe expected five tools; the service correctly exposes six. The
  repaired probe checks exact tool names and rejects missing, extra, substituted
  and duplicate names. Its regression tests and failed earlier result are retained.

`redteam.baltor.ai` had no DNS record, certificate or host allowance at takeover.
The deployment added three DNS records without overwriting existing records,
confirmed all six authoritative answers, obtained a valid certificate and added
the exact host and origin. The previous host configuration remains backed up on
the service volume.

These checks establish deployment, public visitor behavior, transport, disclosure
and selected download integrity. They do not establish a new user's complete
paid journey, a native harness task or a full-system benchmark. The owner's later
request for a fresh customer journey is separate work.

## Follow-up direction

The owner requested broader audiences, practical beginner tutorials, enterprise
packages, audience-specific acquisition pages, advertising variants, additional
harnesses and compact component variants. Those requests belong to the existing
roadmap and component supply programme. Their proposals are not current product
claims or a promise of monthly recurring revenue.
