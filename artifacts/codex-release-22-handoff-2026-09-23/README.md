# Deployment handoff to Claude Code, September 23, 2026

The owner has assigned continual deployment and application updates to Claude
Code. Codex now owns original package supply and the requested four research
lists of 1,000 skills, plugins, contracts and tools. No further deployment is
scheduled by this Codex session.

## Published state

- GitHub main: `231f51bb1facab517fbe915b08ea9ac85f913347`.
- CI `35910034548` passed, including Python 3.10, 3.11 and 3.12.
- Fly deployment `35912525199` passed; live Fly release 22.
- Image: `sha256:76088e33805ca933ade44ac6629e20b4b2a22ded0201c034b95fee481ead931a`.
- Deployment enable variable is false again.
- Image rollback: release 21, `sha256:4c82835554d45d22efa6a56753da2039a51e34278f1e6e5c3408524984b56857`.
- Published catalogue: `74d3c075b0447ea128cbc9797265ed5cee2246d67b45d166b586aa9691c56a75`.
- Catalogue rollback: `c824a1d2e2228d2caf9005057efd1085277393391d65d8a6dbdbf4743aeb6753`.
- Bundle: `10e2ea539a72b62d2115e98a7dbb3d347340f7ab54929a5f4a93208dad199807`.
- Same 43 existing approvals, mechanically carried to source `390643ef`; no
  new approval, withdrawal, tenant grant or registration activation.
- Uploaded staging archive/directory removed after publication. The private
  body store and local bundle retain their copies.

## Observed live checks

- Eight hostnames passed 132 browser checks each, 1,056 total.
- Health/capabilities/home/privacy: 32 of 32 HTTP 200, all hosts ready,
  registration false and retrieval request version 2.
- Exact catalogue check: 43 manifests and 43 body byte sequences matched the
  new digests, sizes and declared effects. 92 requests, 43 confirmed metered
  downloads, zero unknown download outcomes. Account-wide usage totals were
  unavailable to that standalone checker and remain unknown there.
- The ordinary service check passed all 16 HTTP/authentication/isolation checks
  and recorded one metered read. Its three SDK checks initially failed because
  the chosen research environment lacked the qualified MCP SDK.
- A full successor with the qualified environment stopped after four requests
  on a transient URLError; preserve that failed report.
- A separate read-only successor using the exact official-SDK code passed both
  legacy 2025-11-25 initialization and 2026-07-28 per-request negotiation, five
  tools and permitted search with no body loading. This successor made no
  metered reads or model calls. These are separate observations, not a claim
  that one 19-check run passed.

Every report is beside this file. Original outside-repository evidence remains
in `/home/username/.le-codex-build/release-22-evidence`.

## Claude continuation

Use a clean current main checkout. The shared `/home/username/loop-engine`
checkout is behind main with concurrent dirty files; do not reset it. The
integration checkout `/home/username/.le-codex-build/integration` is clean at
231f51bb. Its ignored `.venv` now points to the qualified MCP environment at
`/home/username/.le-wave2/mcp-revision/.venv-mcp2`.

Fold this new handoff/evidence into the next Claude-owned update and update the
current deployment record and roadmap, which still describe release 21 in
some current-view prose. Preserve the 390643ef source checkpoint's ancestry.
Public signup is still disabled; its provider configuration and sender/secret
qualification remain open in the already committed readiness report.

Codex's new supply is in
`artifacts/codex-component-supply-2026-09-23/`. It stays candidate-only and
separate from this live catalogue. The functional engine wrapping research is
already on main in
`docs/research/FUNCTIONAL-ENGINE-WRAPPING-RESEARCH-AND-IMPROVEMENTS-2026-09-23.md`.
