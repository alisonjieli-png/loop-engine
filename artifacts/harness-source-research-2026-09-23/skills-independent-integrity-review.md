# Independent skill-index integrity review

September 23, 2026. **Pass for the reviewed evidence scope.** No source list or
upstream file was changed and no network/model call was made.

The [successor report](skills-independent-integrity-review-successor.json) binds
`skills-ranked.jsonl` at SHA-256
`708d27199ae43e0d962b611ab56dc30defea2cb54c9c1e16cee52f2279661375`.

- 1,000 records, unique research IDs, unique instruction SHA-256 values and unique
  canonical-repository-ID/skill-name groups.
- 81 repository address strings, representing **80 canonical GitHub repository
  IDs**. `shadcn/ui` and `shadcn-ui/ui` address the same repository.
- 1,028 native projections checked, including every representative.
- Exact cached instruction bytes agree with SHA-256, byte count, Git blob SHA,
  the pinned complete tree, source path and commit URL.
- Every representative and alias has a matching successful anonymous raw-content
  request record. Repository metadata is explicitly public and not archived.
- All reported licenses agree with the captured repository metadata; every
  `license_verified` flag remains false.
- Rank sequence, six-decimal score arithmetic, descending priority, the
  forty-per-repository-address cap, and research-only status flags pass.
- The source index remained byte-identical during review.

The [first report](skills-independent-integrity-review.json) preserves a verifier
false positive. Its digest-to-request map retained only one request, although
both repository aliases returned the same tree-response bytes. The repaired
verifier keeps all request bindings per digest and checks the correct one for
each row. The source data did not need repair.

This checks counts and evidence binding. It does not approve the skills, validate
every YAML/Agent Skills rule, resolve their dependency closures, execute tools,
clear licenses, qualify native loading or establish useful task performance.
