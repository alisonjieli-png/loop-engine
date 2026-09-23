# Signup merged with documentation and search v2

Kind: dated isolated integration record. No commit, deployment or activation.

## Baseline and ownership

This worktree, `signup-integrated`, started at
`1920296c00ced18e47992ae05237f4a2923666f0`, then copied the integration tree's
changed and new files. The immutable local baseline tree is
`e441fa68ee2549e85981f00247b665a24506ef7f`. It includes documentation, retrieval
request v2, cache and asset versioning, branding guards and the retired-origin
scan repair. The temporary Git tree is a snapshot, not a commit or branch.

The aggregate patch is relative to that snapshot, not directly to `1920296c`.
It does not include the coordinator's unrelated model-accounting or generation
changes as new edits. The coordinator's integration worktree was only read.

## Applied changes

- Applied the frozen signup implementation and restored-customer-guide delta.
- Resolved the one route-function conflict by preserving documentation routing
  and rendering, then adding the signup and confirmation titles.
- Merged the read-only hosted website checks with existing documentation and
  retired-origin checks.
- Rebuilt the served documentation from the canonical guides.
- Included the independent signup QA report and its exact evidence files.

The signup behavior and its repaired session boundaries remain those described
in [the implementation handoff](SIGNUP-FLOW-RESTORED-2026-09-23.md). Independent
scope and limitations are in
[the independent QA record](SIGNUP-INDEPENDENT-QA-2026-09-23.md).

## Verification of the combined tree

Evidence is under
[`artifacts/signup-integration-2026-09-23`](../../artifacts/signup-integration-2026-09-23/).

| Check | Result | Record |
| --- | --- | --- |
| Focused signup policy, search authority and documentation tests | 49 passed | `focused-tests-first.txt` |
| Account-email owning checks | 87 passed | `account-email-combined.json` |
| Documentation index and source facts | Seven pages, 418 facts, no findings | `docs-index-check.json` |
| Documentation browser | 81 passed | `docs-browser-combined.json` |
| Complete workspace browser | 589 passed, 105 of 105 mutants detected | `browser-combined.json` |
| Existing behavior survival | Ten comparisons passed | `survival.json` |

The survival record compares the parsed bodies of `_search`, `_validate_search`,
`_verify_search_snapshot`, `http_retrieval_schema` and
`http_provisioning_schema` with the snapshot. They are unchanged. The header,
footer, terms and documentation markup are identical to the snapshot, and the
entire asset/page owner `web_pages.py` is unchanged. The search tests separately
exercise effect selection, denied scopes/grants, version refusal and final
authority revalidation through the real local transports.

All browser and protocol traffic uses loopback fixtures. No provider, email,
model, production-state or registration-setting operation was performed.
These checks do not replace the required complete CI gates on the final main
line or the live provider prerequisites recorded by signup QA.

## Applying

Apply the single aggregate patch to the coordinator's integration snapshot.
Do not apply the original signup patch or the separate guide delta again.
Regenerate the records index after all delivery lanes have been combined.
The handoff includes a target-file baseline binding so that any subsequent
change in a touched file is visible before applying the patch.

Registration remains disabled in host configuration. Provider public-signup
closure, administration link generation, sender delivery, password policy and
the real confirmation/account journey still require the documented live checks
before registration opens.
