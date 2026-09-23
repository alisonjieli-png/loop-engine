# Release 21 handoff: terms of service, owner records and the husky mark

Kind: dated handoff of September 23, 2026, written when the owner asked every
line of work to wrap up. It records what the release 21 line did, what is
left, every check that ran and every effect outside this machine. It changes
no authority; the
[commit, push and release authority](../../AGENTS.md#commit-push-and-release-authority)
section of AGENTS.md governs.

## Where the work is

The work is four commits in the detached worktree
`/home/username/.le-integration/r21`, on top of `abcad4f8`, which was
`origin/main` and live as Fly release 20 when the work began. Nothing was
pushed, deployed or changed on a live service. The worktree also holds the
three symbolic links the task asked for, `.venv`, `showcase/node_modules` and
`tools/architecture_report/node_modules`; they are not committed.

| Commit | Subject |
|---|---|
| `06b5f326` | Record the owner's approvals of September 23 in the authority section |
| `eedd9fcb` | Publish the approved terms of service at /terms |
| `90f48653` | Show the owner's husky tile as the mark and keep the summit mark |
| this commit | This handoff, one wording fix in `docs/legal/README.md` and the regenerated records index |

## What is done

1. The terms of service the owner approved on September 23, 2026 ("I have
   approved the terms") are published. `docs/legal/TERMS-OF-SERVICE.md` holds
   the nine sections of the draft word for word, with the title, the operator
   line, "Last changed: September 23, 2026", section 6 in the present tense
   and a line that links the privacy notice. No governing law clause was
   added. The draft stays as history and the legal README records the
   changes.
2. The website serves the terms at `/terms` the way it serves `/privacy`: an
   entry in the page table of `web_pages.py`, a terms view in `index.html`,
   the route and title in `service.js`. The footer links the terms instead of
   saying they are not published. The account creation form, shown only while
   the service reports that account creation is open, says above its button
   "By creating an account you agree to the terms of service and the privacy
   notice", with both linked.
3. The approved terms say beta twice, in sections 2 and 6, and the style rule
   retires that word from customer pages. The approved words were kept. The
   retired-word checks leave out the terms block only while it equals the
   approved file word for word; the legal README says why. A new wording
   needs the owner.
4. AGENTS.md records three owner decisions of September 23, 2026 in the
   authority section: the terms approval, the model direction (customers bring
   their own model access; engineering proves overnight work on Ollama Cloud
   with a cheap model such as Gemma 4) and the approval to open registration
   ("you can open it"), which engineering carries out once sign-up is
   email-first and the identity provider's own public sign-up is closed,
   because a live probe found that a second sign-up for an unconfirmed
   address keeps the first password. Registration stays closed until then.
   `tools/test_context_routes.py` holds all three by their words and dates.
5. The placeholder mark is replaced by variation 52 of the owner's logo
   sheet, a white husky head on a navy rounded tile, with the three icons
   drawn from it under the same file names. Variation 23, the summit, is kept
   in `docs/brand/` and is not served. The traced tile carried four white
   fragments of the sheet's paper outside its rounded corners; they were
   removed and the icons drawn again, and a new browser check fails when the
   mark or an icon shows white outside the tile.

The main session first asked for, then withdrew, a move of the sign-up form
to `POST /api/v1/account/signup` and a new `/auth/confirm` view. No file had
been changed for that request, so nothing was reverted and no attempt diff
exists.

## What a self-registered account would receive

Read from the code of this release and, read only, from the live host file
on September 23, 2026 (the Machine started at 10:47 UTC and its catalogue
refresher reported no view change since then).

- Today nobody can register. `registration_enabled` and
  `email_signup_enabled` are false, so the website shows no account form and
  a first sign-in of an unknown subject is refused with
  `account_registration_unavailable`, even for an address that registered at
  the identity provider's still open public sign-up. The host file has no
  `account_email` block, so `POST /api/v1/account/signup` answers 404.
- Once registration opens with this host file, a first sign-in creates the
  account `customer.<digest>` with the scopes `provisioning:metadata`,
  `provisioning:read`, `usage:read` and `billing:manage`, no entitlement,
  and a version 1 snapshot of the 43 `starter_identities`, as the service
  bound them when it started, each with its body allowed and metered.
- Before paying the account can search and list those items as metadata. In
  the browser it would see 34 of the 43, as the pilot owner does today; nine
  declare effects that a browser holds no authority for. Every download is
  refused with `body_forbidden`.
- The account can open checkout, because `billing:manage` is in
  `browser_identity.allowed_scopes` and checkout is installed. After the
  signed webhook records the subscription, the entitlement is bodies and each
  download of a granted item works and records one usage record.
- Its first personal key comes from the account page (`writes_authorized` is
  true): scopes `provisioning:metadata`, `provisioning:read` and
  `usage:read`, one day by default, seven days at most, ten active at most.
- Blocking or latent problems: the website form still uses the provider's
  public sign-up and there is no `/auth/confirm` view, which the email-first
  release will replace; and the starter snapshot is bound once, at service
  start. After a catalogue release is published without a restart, every new
  account gets bindings of the previous release, whose digests no longer
  match, so it sees nothing before or after paying until the service
  restarts. Setting `catalogue.new_accounts_follow_release` to true with
  `starter_identities` empty (the loader refuses both together) avoids it,
  and new accounts then follow the active release.

## What is left, in order

1. Merge the four commits to `main`. They sit directly on `abcad4f8`; if
   `main` moved, merge and check that every added line survived.
2. Release through the guarded workflow and run
   `tools/check_hosted_website.mjs` against every hostname. It has 13 new
   checks for the terms, the footer link, the consent sentence and the
   unpublished-terms rule; 7 of them fail until release 21 is live.
3. Record the release in the roadmap and in the current deployment section of
   `docs/architecture/MVP-CLIENT-SERVER.md`. This line did not edit the
   roadmap.
4. Before registration opens: email-first sign-up through the service route,
   a `/auth/confirm` view with the recovery form, the provider's public
   sign-up closed, the `account_email` block in the host file, and the
   catalogue setting above.
5. Ask the owner only if the word beta should leave the terms; the approved
   words stay until then.

## Checks and results

The continuous integration set ran on `90f48653` with
`ci-run-wt.sh` from the main session's scratchpad and
`PY_OVERRIDE=/home/username/.le-wave2/mcp-revision/.venv-mcp2/bin/python`.
Two runs of other lines shared the machine at the same time, with a load
average near 68.

| Stage | Exit | Counts |
|---|---|---|
| guard | 0 | 16 of 16, 3 of 3 controls detected |
| mdlint | 0 | 672 files, 0 issues |
| retired | 0 | no retired word |
| selftest | 1 | 3224 of 3225; see known failures |
| conformance | 0 | 32 gates, all pass |
| embodiment | 0 | 106 tests |
| tools | 0 | 849 tests |
| guides | 0 | 0 component guide findings |
| hardcoding | 0 | self-test pass, no new high finding |
| qualification | 0 | 3 tests |
| examples | 0 | 24 examples |
| browser | 0 | 532 of 532, 87 of 87 removed-guard controls detected |

Other runs:

- `tools/check_service_workspace.mjs` on the working tree: 530 of 530, then
  532 of 532 after the rule comparison checks, 87 of 87 controls. The same
  file against the page of `abcad4f8`: 501 of 532, the 31 failures all about
  `/terms`, the footer link and the consent sentence.
- `tools/check_hosted_website.mjs` against a local service through a copy of
  the main session's `hosted_local.mjs`: 94 of 94 with account creation
  closed, 93 of 93 open. Against the page of `abcad4f8`: 87 of 94, its seven
  terms checks failing.
- `tools/test_context_routes.py`: 20 of 20. Against the AGENTS.md of
  `abcad4f8` the three new rules report 12 missing phrases by name.
- `tools/test_service_documentation.py`: 18 of 18. With the `/terms` entry
  removed from the page table the check reports the address.
- Local links of the documentation: 672 files, 2700 links, no finding.
- The corner measurement of the new mark check: 735, 23, 682 and 545 light
  pixels outside the tile on the files as first traced, 0 on the published
  files.
- After this commit, which changes documents only: the markdown lint of the
  changed files, the records index test and the local links. The full set was
  not run again, because the owner asked for no new long runs.

## Known failures

The self-test failed one check, `a_request_in_flight_finishes_on_the_view_it_started_with`,
after 1,102 seconds instead of the usual 320, under the shared load. Its
module, `catalogue_serving_checks.py`, then passed 17 of 17 three times in a
row on the same export of `90f48653`, in 3 to 5 seconds each. Nothing in this
line touches catalogue serving. Run the self-test again on a quiet machine
before calling the set green.

## Commands to continue

```bash
cd /home/username/.le-integration/r21
git log --oneline abcad4f8..HEAD
PY_OVERRIDE=/home/username/.le-wave2/mcp-revision/.venv-mcp2/bin/python \
  /tmp/claude-1000/-home-username-loop-engine/81df4e9e-adbc-4fcf-9636-2fadc680611e/scratchpad/ci-run-wt.sh "$(git rev-parse HEAD)"
node tools/check_service_workspace.mjs /home/username/.le-ci-tmp/browser-NEW-NAME.json
node tools/check_hosted_website.mjs https://baltor.ai /home/username/.le-ci-tmp/hosted-NEW-NAME.json
```

The two browser checks refuse to overwrite a report, so each run needs a new
file name. Run the hosted check for every hostname in the current deployment
section after the release.

## Effects outside this machine

- Read only, on the Fly Machine `83733ea7779068` of `baltor-pilot`: one
  command that read `/data/host.json` and printed only chosen fields
  (Booleans, scope names, counts, the catalogue settings and the section
  names; the file holds environment references, not secret values), and one
  status read of the Machine.
- One public read of `https://app.baltor.ai/api/v1/health`.
- Nothing was written to any provider, the host file, a secret, the
  repository host or the live service. No model or provider call was made.

On this machine the work wrote temporary files under
`/home/username/.le-ci-tmp` (the `r21-` folders) and the continuous
integration script created its own export worktree at
`/home/username/.le-ci-export/90f48653c189c3f1fc989056d41fe46235555e49`.
