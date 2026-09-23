# Search effect selection repair

Kind: dated implementation handoff. Candidate only; no commit or deployment.

## Reproduction and repair

Base: `1920296c00ced18e47992ae05237f4a2923666f0`, in the detached
`search-effects` worktree. The named check
`test_search_can_select_an_authorized_effectful_item` registers an approved,
granted item declaring `spawns_process`. Before the repair, an explicit
provisioning list returns that item, search without effects withholds it, and
search with the same effect selection returns `unknown_request_field`.
The failed owning run is preserved in `known-wrong-before.txt`.

The repair adds the optional `authority_effects` selector at the existing
HTTP retrieval boundary and protocol tool. It reuses the provisioning list's
array shape and the canonical `EFFECTS` vocabulary. Unknown values, duplicate
entries and malformed arrays are refused before the index is queried, even
when no candidate could match. Unknown fields remain refused.

The callback that authorizes search candidates passes the selector into
`invoke_for_principal(..., LIST_OPERATION)`. Its account, scope, exact grant,
qualification and body-access decisions remain authoritative. The final
search snapshot check remains in place. The selector does not grant execution
permission, mutate grants or cause the service to read a body or run a tool.
The service has no tenant execution-effect policy to widen; this is metadata
eligibility under the caller's separately established local permissions.

Omitting effects, an empty array or a selection that does not cover the item's
requirements still withholds that item. A metadata-only credential may see
permitted metadata but its returned `body_allowed` is false and its download
is refused. Another account without grants sees no item. A disabled account
or a credential without the metadata scope is refused.

## Version and client changes

The direct request advances to `service_retrieval_request/v2`. Version 1,
unknown future versions and missing versions are refused without fallback.
The endpoint remains `/api/v1/retrieval`; `service_retrieval_result/v1` is
unchanged. Public capabilities advertise `retrieval.request_record_type` and
`authority_effects: metadata_eligibility_only`.

The protocol's tool list advertises the current closed input schema. Its
existing supported protocol versions are unchanged. The schema and validator
are shared by the protocol and direct HTTP paths. Current repository callers,
component interaction records and active technical contract references move
to v2. Historical evidence remains unchanged. The ranking algorithm is
unchanged; selecting an extra irrelevant effect produces identical hits,
ranks and scores in both lexical and hybrid cases.

## Verification

Evidence lives under
[`artifacts/search-effect-authority-2026-09-23`](../../artifacts/search-effect-authority-2026-09-23/).

| Check | Result | Record |
| --- | --- | --- |
| Focused HTTP/protocol cases | 10 passed | `owning-tests-final.txt` |
| Complete owning HTTP suite | 573 passed, none skipped | `http-owning-suite.json` |
| Homepage and client-journey caller regressions | 91 passed | `caller-regressions.txt` |
| Removed-guard controls | Five detected | `guard-mutations.json` |
| New test module Ruff | Passed | `ruff-new-tests-final.txt` |
| Changed documentation Markdown | Six files passed | `markdown-check.txt` |

The five mutants remove effect forwarding, widen omitted selection to all
effects, remove early effect validation, accept old record versions, and
remove the final authority snapshot check. Each makes its named regression
fail. Every focused test verifies zero body reads and zero download usage.
All requests stay on loopback, with temporary fixture state and no model or
external provider calls. The client-journey regressions do not run a real
native-client model task or qualify an external provider.

The existing HTTP module has 15 full-Ruff findings on the base, unchanged by
this repair. The before/after rule counts are preserved; this lane does not
claim that unrelated source has no lint findings.

An independent source review and replay by `interop_standards` found no material
blocker. It checked `http.py` at SHA-256
`e113363d2271270c8fafc17e80fbd2a187171f49637692c3a8fde265026ee759`
and reran the ten focused cases in the qualified project environment. Its
separate review record is in the root integration tree. The first independent
attempt used an incompatible system protocol library; the qualified replay
passed and that environment mismatch is retained in its record.

## Integration

Apply the core patch and then `search-effect-docs.patch`. The latter is a
small delta against the restored guides already in the root integration tree.
Its before/after document digests are recorded in `docs-delta/binding.json`.
It updates the request version and replaces the earlier search-limitation
workaround with explicit effect selection. It does not overwrite those guides
with their older main-line bodies.

Rebuild the documentation bodies and records index after integration. Run the
documentation source/index checks and the required complete integration gates
on the merged tree. The core worktree intentionally does not include the other
lane's restored guide bodies, so this report does not claim that an unmerged
combination has passed those gates. Preserve the root release's current cache,
asset-version, badge and Get started changes when applying the one-line client
request-version changes. No production endpoint was mutated in this lane.
