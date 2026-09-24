# Accounts release: one way in, staff roles and free monthly Baltor Pro

Kind: dated implementation and verification record. Local checks only. Nothing
was pushed, deployed, or changed on a live service, a provider or a host file.

## What the owner asked for

On September 23, 2026 the owner wrote: "We don't want weird orphaned ways of
signing up, we want a complete fully working SaaS, we can have superadmin
accounts, and developer accounts, and analytics accounts with various
permissions that are hardcoded for internal staff but nothing else weird."
The same day: "for testing and verification can you make the first 10 users
be free (they get monthly for free) and also allow me to manage users in a
superadmin dashboard and grant some of them free monthly status". The owner
also asked for no beta and no invitation-only wording. The roadmap steps are
S-6.65 and S-6.85.

## What was built

```text
Accounts release
├── One way in (account_origin.py)
│   ├── a sign-up creates the user through the identity provider's
│   │   administration interface, marked in app_metadata, and writes the
│   │   service's own record, service_account_origin/v1
│   ├── every sign-in and every activation needs both marks, or it is
│   │   refused with account_origin_unverified
│   ├── any other account under the address is archived, deleted at the
│   │   provider and replaced by a fresh marked account, except an account
│   │   the service already holds a sign-in for, which waits for the marking
│   │   command
│   └── `loop-engine service mark-accounts` lists, then applies, the marks
│       for accounts that predate the guard
├── Staff roles fixed in code (account_policy.py)
│   ├── superadmin: every permission
│   ├── developer: service diagnostics only
│   └── analytics: account and usage counts only
├── Superadmin administration (account_administration.py, the page)
│   ├── overview, account list, and four actions: grant or revoke free
│   │   monthly Baltor Pro, disable or enable an account
│   └── one request identity per action, an audit record with each, and the
│       session rechecked when the write commits
└── Free monthly Baltor Pro (free_monthly.py)
    ├── the operator entitlement with a grant kind, ending each month and
    │   renewed by a periodic task until revoked
    └── the founding offer for the first accounts that finish sign-up,
        ten by default, race-safe against one counter
```

The component guide, [the hosted intelligence service](../components/service-runtime/README.md#one-way-in),
explains each part for a reader. The source guide,
[src/loop_engine/core/service_runtime/README.md](../../src/loop_engine/core/service_runtime/README.md),
holds the rule list and the guard table.

## Decisions and reasons

- The mark lives in two places, the provider's `app_metadata` and the
  service's own record, and both are required. Only the administration
  interface writes `app_metadata`, and only this service writes its record, so
  neither the provider's public sign-up nor someone holding the administration
  key alone can open an account. It also retires the invitation command as a
  way in: its users carry another mark and are refused until marked.
- The sign-up creates the marked user first and only then asks for the link,
  instead of letting link generation create an unmarked user. A user is never
  unmarked between two requests, and the link must name the user that was
  prepared.
- The archive of a replaced account keeps its provider identity, creation
  time, confirmation state, last sign-in and a SHA-256 digest of the address,
  not the address. The lead asked for the address; the owner-approved privacy
  notice lists no address in the service database outside the waiting list,
  so the notice decides. The replacement account at the provider holds the
  address, and its provider identity is in the same record.
- Replacing an account deletes it at the provider. Supabase removes its
  sessions with the user and its refresh tokens with the sessions (foreign keys
  with cascading deletion, read in the provider's published schema). Such an
  account holds no service credential: a service sign-in, and every personal
  key, needs an activation that both marks allow.
- The lead's rule was to replace every unmarked account under the address. An
  account the service already holds a sign-in for is the one exception: it
  predates the guard, so it is a person the service already admitted, and a
  public sign-up request that deleted it would let anyone who knows an address
  end that person's account and its history. It cannot open without the marks
  either way; its owner is sent the usual notice, and the marking command
  admits it. The replacement's archive write also requires that no sign-in is
  bound, so a binding made meanwhile stops the replacement.
- "Free monthly" reuses the operator entitlement record with `grant_kind`,
  ending at the end of the current calendar month and renewed by a periodic
  task. An older release honours such a record for at most one month and never
  longer, so no new record version is needed.
- "Fewer than 10 accounts hold the founding offer" counts current holders, so
  a revoked founding place goes to the next account that finishes sign-up. The
  decision is kept for each account and made once, when its account is first
  activated after Baltor's sign-up; accounts created by the marking command are
  not considered.
- Analytics reads counts and never an address. The account list with
  addresses is a superadmin permission.
- Staff roles apply only to signed-in browser sessions. A host service key
  never holds one, so the existing administrator key keeps exactly its token
  administration and nothing more.
- A host file that names a permission, a fourth role, a field of its own or
  another record version is refused before the service serves anything.

## Prior art

- The attack is the one named in "Pre-hijacked Accounts: An Empirical Study of
  Security Failures in User Account Creation on the Web" (Sudhodanan and
  Paverd, USENIX Security 2022): an attacker creates an account under the
  victim's address before the victim does. The paper's defence, verify the
  identifier before the account can be used and do not keep what an unverified
  creator set, is adopted: the service opens only accounts it created, and
  replaces anything else under the address when its owner arrives.
- Supabase's own advice is to switch public sign-ups off at the project. That
  setting needs the owner (OWNER-03). The service-side guard makes the setting
  advised rather than required, and the two together are stronger.
- Role-based access control with roles mapped to permissions in code and
  users mapped to roles in configuration is core role-based access control
  (Ferraiolo and Kuhn, 1992; ANSI INCITS 359-2004). Keeping roles in the
  provider's JSON Web Token claims, a common Supabase pattern, was rejected: it
  would make the provider's administration interface a second place that can
  grant a role.
- The provider interface facts rest on the provider's published source: the
  administration user listing takes a `filter` that is a substring match on
  the address, `app_metadata` updates merge key by key, a user deletion is a
  hard deletion by default, and sessions and refresh tokens are deleted with
  their user. A live probe of these facts was not made.

## Checks and results

Evidence is under
[`artifacts/accounts-one-way-in-2026-09-24`](../../artifacts/accounts-one-way-in-2026-09-24/).

The full runs are on the accounts release `cd5d7a2` and its catalogue anchor
`a527740`, with this record on top, rebased onto main at `14722d5`, using the
qualified Python 3.10 interpreter. Main then gained one more commit,
`6d0b758`, which touches none of these files and none of the catalogue's cited
sources; the three commits were rebased onto it as `db18890` and `641ae2f`,
the catalogue was anchored to `db18890` the same way, and the checks named
after the table were run again on that result.

| Check | Result | Record |
|---|---|---|
| The one way in, `account_origin_checks.py` | 22 of 22 passed | `owning-checks.json` |
| Staff roles, administration and free monthly, `account_administration_checks.py` | 30 of 30 passed | `owning-checks.json` |
| Browser identity, `browser_identity_checks.py` | 37 of 37 passed | `owning-checks.json` |
| Service smoke, every service check module | 640 of 640 passed | `service-smoke.json` |
| Workspace browser suite, `tools/check_service_workspace.mjs` | 680 of 680 passed; 124 of 124 removed-guard controls detected | `browser-suite-summary.json` |
| Full self-test | 3438 of 3438 passed | `suite-results.json` |
| Conformance | all 32 gates pass | `suite-results.json` |
| Tools suite, run with an empty environment and no provider key | 1373 tests OK, 2 skipped | `suite-results.json` |
| Hardcoding delta gate, failing on new high findings | no new high finding | `suite-results.json` |
| Markdown lint of the changed documents | no issue | |

Earlier attempts are kept beside these results. Before the rebase the full
self-test failed two checks: the six new modules were not in the architecture
map, and this record linked to the evidence folder before it existed; both
were repaired. After the rebase the tools suite failed eleven tests: the
records index did not list this record, the starter catalogue still pinned the
host loader's bytes at `390643e`, and the architecture report's browser
library was not installed in the worktree. The index was rebuilt, the
catalogue was anchored again, and the library was linked from the shared
checkout. The first browser run after the anchor then failed two checks and
one control, because the homepage demonstration still showed two body digests
from before the anchor; the demonstration now shows the new digests. Main
moved again before this was reviewed, so the work was rebased a second time
and the catalogue anchored again, from main's own catalogue, to `cd5d7a2`;
the first anchor never reached main, and every check above was run again on
the result.

On the final rebase onto `6d0b758` these were run again: the three owning
modules, 22, 30 and 37 of each passed; the catalogue, records index and
component guide tests, 185 OK with 1 skipped; the full self-test, 3438 of
3438; conformance, all 32 gates; the tools suite with an empty environment,
1376 tests OK with 2 skipped; and the hardcoding gate, no new high finding.
The browser suite was not repeated, because that main commit changes no page,
fixture or service file.

Every known-wrong case has a removed-guard control that must fail the named
check; the table in the source guide lists them. The controls rebuild the
guarded function from its own source with the guard changed, in memory, and a
control whose text no longer matches the source refuses to run.

## What the release needs

These fields and secrets are needed on the host. None was changed here.

1. Secrets, set through standard input from the system keyring and never
   printed: `BALTOR_IDENTITY_SERVICE_KEY`, the identity project's server key,
   which starts with `sb_secret_`, and `BALTOR_MAIL_API_KEY`, the mail
   provider's key, which starts with `re_`. The identity key serves the
   sign-up link, the one way in, the marking command and the superadmin
   account list.
2. Release the committed revision through the guarded workflow. The image
   carries the guard, so browser sign-ins of accounts that predate it are
   refused until step 4 runs; service keys are not affected.
3. In `/data/host.json`, after a backup, add two blocks and restart:
   - `account_email`, record `service_account_email_configuration/v1`, as in
     the [sign-up handoff](HANDOFF-signup-2026-09-23.md), with
     `identity_origin` equal to `browser_identity.project_url`,
     `identity_service_key_ref` set to `env:BALTOR_IDENTITY_SERVICE_KEY`,
     `mail_api_key_ref` set to `env:BALTOR_MAIL_API_KEY` and `allow_network`
     true. Keep `signup_enabled` false for now.
   - `accounts`, record `service_account_policy/v1`, with `staff`, a list of
     entries each with `role` (superadmin, developer or analytics) and either
     `provider_user_id` or `email`; the owner's entry is a superadmin. Add
     `founding_free_monthly_accounts` only to choose another number than ten.
4. Run the marking command on the host, read its plan, then apply it:

   ```bash
   loop-engine service mark-accounts --config /data/host.json
   loop-engine service mark-accounts --config /data/host.json --apply --expected-plan <plan_digest>
   ```

   Then sign in as the owner and open the Administration view.
5. Open registration: set `account_email.signup_enabled`,
   `browser_identity.registration_enabled` and
   `browser_identity.email_signup_enabled` to true, and restart. The existing
   `http.request_limits` block already states `Fly-Client-IP`, which open
   sign-up requires.
6. Check that `GET /api/v1/capabilities` reports `registration_available`
   true and that the health record reports `free_monthly_renewal_current`.
   Then run one live journey with a fresh address, one with an address first
   registered through the provider's own public sign-up, which must end with
   the provider's first password refused, and one founding account.

## Limits

- The checks use the stand-in identity project and loopback listeners. They
  do not prove the live provider's answers for administration user creation,
  lookup, deletion and marking; the first live journey is that proof.
- The number of provider requests a sign-up makes now depends on who held the
  address, so the time an answer takes can differ. The status and the bytes do
  not.
- The service observes that the address was confirmed and that the account
  was activated. That the person chose a password before activation is the
  page's order of steps, not something the service can observe.
- The account list reads every provider user on each request. It needs paging
  before many thousands of accounts.
- Release 23, which this change was rebased onto, removed the invitation,
  waiting list and trial words from every customer page. The owner-approved
  privacy notice still describes the waiting list in its table; it is a legal
  text that changes only with the owner. The account and Get started pages say
  "Your account includes Baltor Pro" for a founding or free monthly account,
  and release 23's own wording, "Your account covers Baltor Pro", stays for
  any other granted account.
- The invitation command, operator-issued customer keys and the waiting list
  still exist. The guard refuses the accounts they would make until the
  marking command marks them; retiring them as history is the rest of S-6.85.
- The privacy notice's table names "an account record that links your sign-in
  to your account", which covers the origin record. It does not name the
  replacement record, which holds a digest of an address and the identity of a
  deleted sign-in, or the staff audit record. Neither holds an address; a
  notice change that names them is a legal text and waits for the owner.
- Account deletion on request is a manual procedure today. It must now also
  remove the account's origin record, any replacement record naming it and
  the staff audit records that name its account.
