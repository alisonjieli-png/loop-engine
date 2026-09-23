# Documentation restoration evidence

The completed implementation and integration instructions are in
[the documentation handoff](../../docs/verification/SITE-DOCUMENTATION-RESTORED-2026-09-23.md).

Current results: `index-frozen-check.json`, `python-docs-tests-final.txt`,
`full-workspace-browser.json`, `browser-frozen.json`,
`documentation-guard-controls-final.json`, `ruff-frozen.txt` and
`markdown-final.txt`. Their earlier failed attempts stay beside them.

`browser-before-client-guards-settled.json` is the valid initial browser
counterexample record. The earlier file without `settled` measured the initial
loading message too early; its empty-title failures were a test timing defect.
The settled run isolated the real index-shape and unexpected-head gaps.

`search-effect-authority-gap-v3.json` is the valid search/list comparison.
The first two attempts used mistaken fixture request shapes. All three scripts
and results remain available so that the distinction is visible.

`markdown-check.txt` is empty because the library module was invoked directly.
`markdown-final.txt` invokes the actual command entrypoint and records 11 files.

Browser screenshots are first-screen views. Their report records the full
rendered heights and width checks; the images are not claims of a complete
native harness task or live service release. The fixture uses no provider calls.
