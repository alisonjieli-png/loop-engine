# Sign-up links a superadmin sends, and a confirmation page that waits

Kind: dated implementation and verification record. Local checks only. Nothing
was pushed, deployed, or changed on a live service, a provider or a host file.

## What the owner asked for

On September 24, 2026, after release 24 opened registration, the owner asked,
through the main session, for a way to let a superadmin type email addresses
and invite people to sign up:

- a superadmin enters one address or a small batch, and may tick "include free
  monthly Baltor Pro";
- no second way in: Baltor's own sign-up starts, email first, with the same
  account marks;
- the person gets one email that says who invited them and links to the same
  `/auth/confirm` page, where they choose their password;
- free monthly Baltor Pro is granted when the account opens, if it was ticked;
- a caller who is not a superadmin, an address that already has an account, a
  batch over the limit and a repeat within the allowance that sign-up keeps are
  refused, each with a named check and a removed-guard control;
- each batch writes an audit record in the same write, carries a request
  identity, and keeps digests instead of addresses;
- the pending account shows in the account list until it opens;
- no public page gains invitation wording, because this is a staff tool.

The same request asked for one fix on the confirmation page: keep Confirm
disabled, with a short loading note, until the sign-in settings are ready. The
roadmap step is S-6.99 (written as S-6.91 in the worktree and renumbered at the merge, because S-6.91 was taken on main by then).

## What was built

```text
Staff sign-up links
├── The staff route /api/v1/admin/sign-up-links (http.py)
│   ├── a governed Loop operation, like every service route
│   ├── the request body is never kept in a failure record
│   └── the staff session is rechecked, as for every staff action
├── The operation (staff_sign_up_links.py)
│   ├── StaffSignUpLinkRequest: at most ten addresses, each once
│   ├── the permission accounts.send_sign_up_links, superadmin only
│   ├── the request identity reserved in the audit record first
│   ├── for each address
│   │   ├── an open account: refused, and no message
│   │   ├── the allowance for one address used up: refused, and no message
│   │   └── otherwise: AccountOrigins.prepare_signup with both marks, one
│   │       generated link, and one message naming the sender
│   └── one write: the pending records and the completed audit record
├── Activation (browser_identity.py)
│   └── complete_on_activation, before the founding offer: the pending record
│       is completed, with free monthly Baltor Pro in the same write when
│       it was asked for
├── The Administration view (index.html, service.js)
│   ├── a form: addresses, the free monthly box, and one button
│   └── each pending account: "Sign-up link sent", with its date, "waiting
│       for this person to choose a password"
└── The confirmation page (index.html, service.js)
    └── Confirm is served disabled with "Loading the sign-in settings…",
        and enabled only once the sign-in settings have loaded
```

Two parts of the account email adapter were opened for this use without a
change in behavior: the link request and its checks moved from `_token_hash`
into `generated_link`, and `confirm_link`, `identity_secret` and
`send_message` name what the adapter already did. The staff entry in the
host's `accounts` block gained an optional `name`, the name the message gives
for its sender.

The component guide,
[the hosted intelligence service](../components/service-runtime/README.md#sign-up-links-a-superadmin-sends),
explains the feature for a reader. The source guide,
[src/loop_engine/core/service_runtime/README.md](../../src/loop_engine/core/service_runtime/README.md#sign-up-links-a-superadmin-sends),
holds the rule list and the guard table.

## Decisions and reasons

- A sign-up link is Baltor's own sign-up, started by a staff member. The
  identity provider's own invitation, `inviteUserByEmail` in Supabase, was
  rejected: it creates the user without the service's marks, it sends the
  provider's own message template with a link to the provider's address, which
  is a provider setting engineering cannot reach, and its link has its own
  type, which the confirmation page would have to accept as a second flow. The
  owner's rule is one way in, and the standing decision on sign-up email keeps
  the whole journey on the baltor.ai domain.
- The words in the Administration view are "sign-up link", and no served file
  uses a word that starts with "invit". The browser suite already checks every
  customer string of every served file for invitation wording, and the owner
  barred invitation-only wording on September 23. The message itself says
  "invited you", because the owner asked that it say who invited the person.
  A message is not a public page.
- The account is created with a password that nobody chose and nobody learns,
  as in public sign-up, and the person chooses their own on the confirmation
  page. A staff member never sets or sees a password.
- A sign-up link counts against the same allowance for one address as a public
  sign-up, three an hour by default. A staff member cannot send one person more
  messages than a visitor could ask for, and a public sign-up right after a
  staff link meets the same count.
- "Already has an account" means an account the service holds a sign-in for,
  or a confirmed account with both marks. It is checked before anything is
  counted or sent. A sign-up still waiting for its confirmation gets a fresh
  link, as a public sign-up would.
- Ten addresses at most. A batch of ten makes up to about fifty requests to the
  identity provider and the mail sender, which fits inside the page's request
  time of 35 seconds.
- The request identity is reserved before the first provider request. An
  interrupted batch stays in progress under its identity and is never sent
  again under it, because a message may already have gone out.
- The records hold a SHA-256 digest of each address, as the replacement archive
  of the accounts release does. The owner-approved privacy notice lists no
  address in the service database outside the waiting list; the account list
  reads addresses from the identity provider.
- Free monthly Baltor Pro is granted in the same write that completes the
  pending record, when the account opens, and before the founding offer is
  weighed. An account that came in by a staff link with free monthly takes no
  founding place, which stays for someone who came on their own.
- The message names the sender by the optional `name` of the staff entry, or
  by the staff member's verified address. The name is checked like the other
  staff fields: up to 64 letters, digits, spaces, points, hyphens or
  apostrophes.
- The confirmation page is served with Confirm disabled and the loading note
  shown, so the page is safe before its script runs. The script enables Confirm
  only when the sign-in client exists, and when the settings fail it hides the
  note and says that the link was not used.

## Prior art

- Supabase's published administration interface offers `inviteUserByEmail`
  and `generateLink` with the type `invite`. Both were rejected for the reasons
  above, from the published documentation; neither was probed live.
  `generateLink` with the type `signup`, which the public sign-up already
  uses, was adopted.
- Invitation flows in software-as-a-service products usually keep a pending
  invitation with its own token and expiry. Here the identity provider's
  confirmation link is the token, and the pending record keeps only what the
  service needs: the provider user, a digest of the address, the sender and
  the free monthly choice.

## Checks and results

Evidence is under
[`artifacts/staff-sign-up-links-2026-09-24`](../../artifacts/staff-sign-up-links-2026-09-24/).

The check results are added with the evidence files, in the commit after the change.

Every known-wrong case has a removed-guard control that must fail the named
check; the table in the source guide lists them. The Python controls rebuild
the guarded function from its own source with the guard changed, in memory,
and a control whose text no longer matches the source refuses to run. The
browser controls change the served page script in memory only.

## What the release needs

No new secret and no new host field is required.

1. The feature uses what release 24 already has on the host: the
   `account_email` block with `signup_enabled` true and the identity service
   key, and the `accounts` block with its staff list. A staff member whose
   role is superadmin sees the form in the Administration view.
2. The optional `name` in a staff entry, such as "Sam at Baltor", sets how the
   message names its sender. Add it only after this release is running:
   release 24 refuses a staff entry with a field it does not know, so the
   field must come out again before any rollback to release 24. Without it,
   the message names the staff member's verified address.
3. After the release, send one link from the Administration view to a fresh
   test address with free monthly ticked. Open the message, check that it
   names the sender, choose a password on `/auth/confirm`, and check that the
   account opens with free monthly Baltor Pro and leaves the pending list.
   Then send to the same address again and check that it is refused as an
   account that already exists, with no second message.

## Limits

- The checks use the stand-in identity project and loopback listeners. The
  live identity provider's answers were not probed for this feature; the live
  journey above is that proof.
- The link lasts as long as the identity provider's setting for email links
  allows. The live project's value was not read. A person who opens the link
  too late asks for a new one on the sign-up page, and free monthly Baltor Pro
  still starts when the account opens, because the pending record stays.
- The allowance for one address is kept in process memory, as for public
  sign-up, so a restart starts it again.
- A batch interrupted after its reservation leaves any account it prepared
  without a pending record, so that account opens without the free monthly
  grant. A superadmin grants it from the account list.
- The privacy notice's table does not name the pending record or the staff
  audit record. Neither holds an address; a notice change that names them is a
  legal text and waits for the owner.
