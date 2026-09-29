# Release 48: the supply line lands

Fly release 48 ran `39248e46a81070a78a8ea366b167ad9ff25aacc6` on September 29,
2026. It is the release that changes the shape of the library.

## Why this release exists

The served library held 6,326 skills against 77 code modules and 69 contract
schemas. Most of what a customer could download was instruction text, which is the
composition the owner named as not good enough. This release lands the 58-commit
supply line that produces the missing kinds:

- one tested client per operation of a licensed OpenAPI specification, with the
  APIs.guru and Google discovery modes
- a JavaScript module with TypeScript declarations in every API package, so the
  library is not Python-only
- pinned program install recipes with published checksums, and a Homebrew
  catalogue mode for binaries
- JSON Schema components from SchemaStore, each with a small validator and its
  own examples as its tests
- 444 reference data tables, function extracts, and the component form attribute
  so every item names the form it is

The generator is `tools/build_library_supply.py`, with ten lines: mcp-registry,
openapi, openapi-directory, openapi-discovery, programs, functions, schemas,
api-schemas, data-tables and report. Each line requires an explicit
`--authorize-network-reads` and `--authorize-store-writes` before it stores
candidates, so no run has produced components for this release yet.

## How it landed

The train was built in a detached worktree and picked with the recorded
cherry-pick tooling. Three allowlist conflicts were resolved by rebuilding the
file from main's entries plus every entry the supply line adds that main lacks:
35 new entries, 1,170 in total, and main's version kept for the one entry both
sides carried with different content. That rebuild is the one judgement call in
the merge and it is stated here so a reviewer can check it.

All 19 local gates passed on the train and again on main after the merge.
Continuous integration and deployment both succeeded and the deployment setting
was read back as false.

## Live evidence

The visitor check passed 57 pages, 237 views, nine hostnames and 353 links with
zero reported problems. All nine hostnames answer 200.

The catalogue and hosted service check suites have **not** been re-run for this
release and the record says so.

## The room this makes

The volume is 25 GB, extended from 3 GB after release 46 filled the smaller one
and took the site down. At the measured 77 kilobytes a package that is about
330,000 packages against 15,146 served now, so storage stops being the binding
constraint on the library for the first time.
