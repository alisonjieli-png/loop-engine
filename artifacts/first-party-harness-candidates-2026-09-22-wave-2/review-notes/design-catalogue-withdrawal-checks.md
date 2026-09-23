# Candidate review: design catalogue withdrawal checks

Status: candidate only. No independent approval, withdrawal, release, or measured benefit.

- Original basis: first-party negative-check design based on the repository's served-manifest and grant lifecycle analysis. No external catalogue implementation or legal retention rule was copied.
- Facets: catalogue release engineer, search engineer, or access reviewer; subscription intelligence service; item withdrawal stage; harness and model do not change entitlement.
- Search phrasings: "If we pull this skill, could an old client still download it?"; "Write tests for revoking one library item without losing the audit record."
- Typed input/output concept: `ItemVersion`, `ReleaseManifest`, `GrantState`, `IndexState`, `CachePolicy`, `RollbackImage[]`, and `WithdrawalProposal` to `WithdrawalCheckMatrix`.
- Effects: read-only test design. No grant revocation, manifest edit, deletion, deployment, or rollback.
- Positive fixture: the new release removes one item from active search and refuses a stale granted body reference at final read; the rollback image can parse the withdrawal record. The matrix tests both allowed and refused accounts.
- Known-wrong fixture: an item disappears from search, but a saved body URL and an older image still serve it. A check that tests search alone and claims withdrawal complete must fail.
- Nearest overlap and distinction: starter `run_a_release_check_list_before_deploying` covers general deployment checks; `write_a_rollback_plan_before_the_release` plans a way back. This method targets item withdrawal across search, grants, body authorization, stale caches, and incompatible rollback readers.
- Limits: test design is not execution evidence. Retention and rollback eligibility need the service's actual policy and versions; independent review should include a rank-to-read race.
