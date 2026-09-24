# Persona journeys on the live site, September 24, 2026

Kind: dated verification record. Five scripted customer personas used the live
Baltor site in a real browser on September 24, 2026, between 14:09 and 17:10
UTC (10:09 a.m. to 1:10 p.m. Eastern). Every run met Fly release 24, image
`sha256:e538318deef9ab06aeb34f591d2617aae7296879b0efdbaf72f54a69bdf1c7ab`,
built from main `961dc906`. This record merges the five persona reports into
one ranked list. The persona runs created three live accounts, created no
client token and took no payment. The follow-up checks for this record only
read public pages, the Fly release list, the persona evidence and the source.

The screenshots and video frames are in `assets/persona-journeys-2026-09-24/`
beside this record.
[The evidence README](../../artifacts/persona-journeys-2026-09-24/README.md)
lists every file, the screenshots left out as duplicates, and the paths of the
videos, which stay outside the repository.

## Summary

- Sign-up works. All three personas that tried it went from an email address
  to an active account with Baltor Pro, about 15 to 20 seconds into their
  recordings, including their detours and the wait for the email.
- No persona reached its whole goal. The main reason is finding 1: the
  confirmation email sends the customer to `baltor-pilot.fly.dev`, and the rest
  of the journey stays there. The signed-in session does not exist on
  `baltor.ai`, and the personal connection entry names
  `https://baltor-pilot.fly.dev/mcp`.
- One reported blocker was wrong. The data scientist's script reported that the
  password step hung. Its own recording shows the page reached step 5, signed
  in, about one second after the click. What the recordings do show, in all
  three sign-ups, is a false "This link cannot be used. ... Nothing was
  changed." panel for a quarter to half a second after the password was
  accepted (finding 4).
- Ranked result: 3 blockers, 6 major, 8 minor and 2 polish findings. Six
  test-tooling gaps are listed separately and are not counted as product
  findings.
- The record ends with the
  [ten fixes that would help most](#the-ten-fixes-that-would-help-most), each
  with its page and exact element.

## Personas, goals and outcomes

Time to first value means the time from the first frame of a persona's
recording to the first frame that shows what the persona came for. For the
three sign-ups, that is the step 5 screen "Your account includes Baltor Pro",
read from frames sampled every eighth to quarter second. The persona reports
used different measures, so the table keeps their numbers and says what each
one measured.

| Persona | Goal | Reached | Time to first value | Account |
| --- | --- | --- | --- | --- |
| The Claude Code developer: a solo developer who uses Claude Code daily and wants tickets worked overnight on a cheaper model | Sign up, open the Claude Code entry on Get set up, create one client token and copy the entry | No. The account held Baltor Pro, but the entry named the Fly hostname, and the script never created a token | About 14.6 seconds on the recording, and 11.2 seconds of summed step time. The report recorded no value | `baltoruser7927449a2bae@uberip.com` |
| The data scientist: cleans messy tables and has heard that small models can do it with the right instructions | Find evidence that small models clean tables with Baltor, then sign up | Partly. The account held Baltor Pro, although the script reported a failure. No data cleanup example was found | About 20.2 seconds on the recording. The report's 44.72 seconds is the time until the script stopped | `baltordse30a7833c9de@uberip.com`; the report said unknown, the recording shows it finished |
| The engineering lead: compares Baltor with other skill registries before buying seats for a team | Decide, without signing up, whether Baltor is trustworthy enough to recommend: security, privacy, terms, how items are vetted, what happens to company code | Yes, with a negative answer for the team. The lead would open one personal account to keep evaluating the library and would not bring the team yet | 11.7 seconds to read seven trust pages, which is the run's total time. How items are vetted was never answered | None |
| The Pi and OpenCode developer: runs Pi and OpenCode with local and cloud models and dislikes vendor lock-in | Learn how Baltor works with Pi and OpenCode, read the Pi extension, sign up and check the connection | No. The account held Baltor Pro on the Fly hostname. Back on `baltor.ai` the site showed a signed-out visitor, so no token and no connection check | About 15.5 seconds on the recording. The report's 18.6 seconds is the run's total time | `baltorpis@uberip.com` |
| The phone visitor: saw Baltor mentioned on social media and opens it on a phone | Understand Baltor in under a minute and start the sign-up | Partly. The visitor reached Get started, but the test inbox could not be created, so no address was entered | 12.6 seconds to reach Get started, as recorded | None |

Method, in short: each persona ran Chromium through Playwright, mostly clicked
the visible links and buttons a person would click, saved a screenshot after
every step and a video of the whole run, and used a disposable mail.tm inbox
for sign-up. The phone visitor used a 390 by 844 viewport with touch and a phone
user agent. The desktop personas used 1440 by 900, except the data scientist
at 1280 by 800. No script wrote a password, a token or an email body to its
report.

## Accounts and founding places

| Address | Persona | State |
| --- | --- | --- |
| `baltoruser7927449a2bae@uberip.com` | Claude Code developer | Confirmed, password set, founding offer applied |
| `baltordse30a7833c9de@uberip.com` | Data scientist | Confirmed, password set, founding offer applied, shown at 20.35 seconds of its recording |
| `baltorpis@uberip.com` | Pi and OpenCode developer | Confirmed, password set, founding offer applied |
| Two addresses, not recorded | Data scientist, first two runs at 14:28 and 17:03 UTC | Sign-up requested and never confirmed, because the script read the link wrongly (test-tooling gap 2) |

No client token was created and no checkout was opened. The founding offer
applied to each confirmed account, so no Subscribe button appeared.

The scripts never stored the passwords or the inbox credentials, so nobody can
sign in to these three accounts or recover them. Each one shows "As one of the
first accounts, it is free each month." The
[release 24 record](../../artifacts/release-24-2026-09-24/README.md) read 0 of
10 founding places used after its own checks. Unless a real person signed up in
between, these test accounts now hold 3 of the 10 places. The superadmin
Administration view states the current count as "Founding places used: N of
10".

Decision: this change does not touch the live accounts. The next operator step
is to revoke the founding offer on the three accounts and switch them off from
the superadmin dashboard. Both actions are audited and reversible, and a
revoked founding place becomes free again, as `free_monthly.py` states.
Switching them off also closes one path: if mail.tm ever releases one of these
addresses, its next holder could reset the Baltor password through recovery,
which is open. Deleting the accounts would need the owner. Future persona runs
should keep their inbox credential and password in the system keyring, never
in a report, reuse their accounts, and return any founding place they take, as
`tools/check_live_account_journeys.mjs --staff-step` does when it revokes the
free monthly grant of its checking accounts.

## How the findings were merged and ranked

Severity:

- Blocker: the persona could not reach its goal because of it, or a public page
  states something false about access, security or money.
- Major: the persona reached the step only with extra effort or doubt, or a
  question the persona came to answer stayed unanswered.
- Minor: friction or wording that the persona noticed and that did not change
  the outcome.
- Polish: consistency and presentation.

Findings that describe the same problem were merged and keep every piece of
evidence. "Personas met" counts the personas whose run met the problem, whether
the persona reported it or its screenshots and recording show it. The order is
severity first, then personas met. Ties put corrections of something wrong
first, new content second, and product or policy work last.

Changes from the severities that the personas reported:

- The data scientist's blocker "the password step hangs" is withdrawn as a
  script error (test-tooling gap 1). The defect its screenshot pointed at is
  finding 4, major.
- The data scientist's major finding about the confirmation link joins
  finding 1, a blocker.
- The phone visitor's major finding "could not enter an address" and its minor
  finding "no email within 15 seconds" are test-tooling gaps 3 and 5.
- The engineering lead's overall verdict and the Claude Code developer's run
  notes are summaries, not findings. Their content is in
  [what worked](#what-worked) and in test-tooling gap 4.
- Four separate observations about the free founding offer became finding 10.
- Findings 4, 5, 12 and 18 were not reported as such by the personas. They
  were found while merging, in the personas' own recordings and screenshots,
  and each is checked against the source.

## Ranked findings

| Rank | Severity | Finding | Personas met | Reported by |
| --- | --- | --- | --- | --- |
| 1 | Blocker | Sign-up moves the customer to the Fly hostname and leaves them there | 3 | Claude Code developer, data scientist, Pi and OpenCode developer |
| 2 | Blocker | The Security and How it works pages say public sign-up is closed | 1 | Engineering lead |
| 3 | Blocker | A team cannot buy seats, while the homepage speaks to teams | 1 | Engineering lead |
| 4 | Major | A false "This link cannot be used" panel appears after the password is accepted | 3 | Data scientist, as a hang; seen in all three recordings during the merge |
| 5 | Major | A signed-in visitor cannot run the connection check from Get set up | 2 | Pi and OpenCode developer; seen in the Claude Code developer's screenshots |
| 6 | Major | The Pi extension path is plain text, not a link | 1 | Pi and OpenCode developer |
| 7 | Major | The phone menu's named control is a hidden 1 pixel checkbox under the logo | 1 | Phone visitor |
| 8 | Major | Nothing explains who vets library items, or how | 1 | Engineering lead |
| 9 | Major | "What happens to company code" is answered with "do not send it yet", without dates | 1 | Engineering lead |
| 10 | Minor | Price statements ignore the founding offer | 5 | Data scientist, engineering lead, phone visitor, Claude Code developer; seen in the Pi and OpenCode developer's screenshots |
| 11 | Minor | Test accounts hold founding places that nobody can use | 3 | Pi and OpenCode developer; the other two found during the merge |
| 12 | Minor | The password button accepts a click before the page can use it (fixed on main since) | 1 | Seen in the Pi and OpenCode developer's recording during the merge |
| 13 | Minor | An internal Get started button carries an outbound arrow | 1 | Engineering lead |
| 14 | Minor | The security page is named "Access and data" and linked only from the footer | 1 | Engineering lead |
| 15 | Minor | The account page shows internal identity vocabulary | 1 | Claude Code developer |
| 16 | Minor | The confirmation email took up to 10.5 seconds, and the page sets no expectation | 1 | Data scientist |
| 17 | Minor | No data cleanup example or case study | 1 | Data scientist |
| 18 | Polish | Signed-in pages still show signed-out prompts | 1 | Seen in the Claude Code developer's screenshots during the merge |
| 19 | Polish | Only the Pi tab names a checked version | 1 | Pi and OpenCode developer |

Screenshot links below point into `assets/persona-journeys-2026-09-24/`. Line
numbers refer to main `a8e82cb2`, the revision this record was committed on.
The live site ran release 24, built from `961dc906`; where main has changed a
cited behavior since then, the finding says so.

### 1. Sign-up moves the customer to the Fly hostname and leaves them there

Blocker. Personas met: 3 (Claude Code developer, data scientist, Pi and
OpenCode developer).

**What happened.** The confirmation email links to
`https://baltor-pilot.fly.dev/auth/confirm`, not to `baltor.ai`. The data
scientist saw the same host in all three of its runs. The password page, the
plan step, Get set up and the account page then all stayed on the Fly
hostname. Three things follow:

- The customer chooses a password on a hostname that appears nowhere else on
  the site, straight after following a link in an email. The data scientist
  noted that a person cannot easily tell that host from a phishing link.
- The personal Claude Code entry on the signed-in Get set up page reads
  `"url": "https://baltor-pilot.fly.dev/mcp"`. A signed-out visit to
  `https://baltor.ai/setup` prints `https://baltor.ai/mcp`.
- When the Pi and OpenCode developer went back to `https://baltor.ai/setup`,
  the site showed a signed-out visitor: Sign in and Get started in the header,
  and only "Sign in to check access" on the Pi tab. Its screenshots after
  sign-up are byte-identical to the ones taken before sign-up. No client token
  was created and the connection check never ran.

**Evidence.**
[claude-code-developer/07-open-confirmation-link.png](assets/persona-journeys-2026-09-24/claude-code-developer/07-open-confirmation-link.png),
[claude-code-developer/09-plan-step.png](assets/persona-journeys-2026-09-24/claude-code-developer/09-plan-step.png),
[claude-code-developer/11-select-claude-code-tab.png](assets/persona-journeys-2026-09-24/claude-code-developer/11-select-claude-code-tab.png)
(the entry and the endpoint name the Fly hostname),
[data-scientist/10-open-confirmation-link.png](assets/persona-journeys-2026-09-24/data-scientist/10-open-confirmation-link.png),
[pi-opencode-user/09-open-confirmation-link.png](assets/persona-journeys-2026-09-24/pi-opencode-user/09-open-confirmation-link.png),
[pi-opencode-user/11-return-to-setup-signed-in.png](assets/persona-journeys-2026-09-24/pi-opencode-user/11-return-to-setup-signed-in.png)
and
[pi-opencode-user/12-open-pi-tab-signed-in.png](assets/persona-journeys-2026-09-24/pi-opencode-user/12-open-pi-tab-signed-in.png).
The data scientist's inbox log recorded the link as
`baltor-pilot.fly.dev/auth/confirm` with the parameters `token_hash` and
`type`, in each run.

**Cause, from the source.** Three separate causes combine:

- `AccountEmailAdapter.confirm_link()` builds the emailed link from the host
  file's `http.public_base_url`
  (`src/loop_engine/core/service_runtime/account_email.py`, line 740). The live
  value is `https://baltor-pilot.fly.dev`. The other account messages (lines
  658 and 659) and the staff sign-up links added on main in `9cc54e14`
  (`staff_sign_up_links.py` line 157) use the same address. The same value
  also sets the protocol resource and the identity callback address
  (`http.py` lines 597, 1404 and 1434). The
  [September 23 read-only audit](SIGNUP-LIVE-READINESS-READONLY-2026-09-23.md),
  the [release 24 record](../../artifacts/release-24-2026-09-24/README.md) and
  the [current deployment](../architecture/MVP-CLIENT-SERVER.md#current-deployment)
  section each record this as open. These journeys show what it costs a
  customer.
- Get set up fills every connection entry from the page's own address,
  `location.origin` (`web_assets/service.js` lines 706, 707 and 790), so the
  entry names whichever hostname served the page.
- The sign-in session lives in page memory only: `createIdentityClient` passes
  `persistSession:false` (`service.js` lines 110 and 111), and the Security page
  says so. A session made on one hostname cannot exist on another, and any full
  page load ends it, on any hostname. That last point is read from the source;
  no persona reloaded a signed-in page on the same hostname.

The recorded sign-up email decision in
[AGENTS.md](../../AGENTS.md#decisions-that-stand-until-the-owner-changes-them)
says the service sends its own email "so the whole journey stays on the
baltor.ai domain". The live journey does not.

**Expected.** The emailed link, every page after it and every generated
connection entry use `https://baltor.ai`, and a signed-in person stays signed
in on the brand hostname.

**Fix.** Fixes 1 and 5 below.

### 2. The Security and How it works pages say public sign-up is closed

Blocker. Personas met: 1 (engineering lead).

**What happened.** The Security page, titled "Access and data", says under
"Current operational limits": "Public account creation is not open. Access
comes from your operator, who can issue and revoke test tokens." Its closing
notice says to agree on the data policy "with your operator". The "Available
today" notice on How it works says: "Public account creation, paid
subscriptions and automatic setup of every step are not open yet", and that a
person with an account "can sign in with a service token". The Get started
button beside both notices opens a working five-step self-service sign-up with
no operator in it. Public registration opened at 13:00 UTC that day, and
payments have been live since September 21, 2026.

**Evidence.**
[team-lead-evaluator/03-03-security-access-and-data.png](assets/persona-journeys-2026-09-24/team-lead-evaluator/03-03-security-access-and-data.png),
[team-lead-evaluator/02-02-how-it-works.png](assets/persona-journeys-2026-09-24/team-lead-evaluator/02-02-how-it-works.png),
[team-lead-evaluator/12-get-started-view-only.png](assets/persona-journeys-2026-09-24/team-lead-evaluator/12-get-started-view-only.png).

**Cause.** Static text in `web_assets/index.html`, line 379 for the Security
page and line 321 for How it works, written before registration and payments
opened. It also contradicts the owner's account model of one way in, with no
hand-issued access.

**Expected.** The page that a careful buyer trusts most states the live facts.

**Fix.** Fix 3 below.

### 3. A team cannot buy seats, while the homepage speaks to teams

Blocker for this persona's goal. It is a product gap, not a defect. Personas
met: 1 (engineering lead).

**What happened.** The homepage has a section headed "Built for teams that
check the details." and one headed "Three things teams do with Baltor." The
pricing page answers "Can a team share one account?" with "Not today. One
account holds one person's keys. Shared accounts and team billing are later
work." The pricing page also says, under its heading and before the price,
"Baltor Pro is for one person and the devices that person connects." A lead
who came to buy seats cannot do it.

**Evidence.**
[team-lead-evaluator/10-pricing-faq.png](assets/persona-journeys-2026-09-24/team-lead-evaluator/10-pricing-faq.png),
[team-lead-evaluator/06-06-pricing.png](assets/persona-journeys-2026-09-24/team-lead-evaluator/06-06-pricing.png),
[team-lead-evaluator/01-01-homepage.png](assets/persona-journeys-2026-09-24/team-lead-evaluator/01-01-homepage.png).

**Cause.** No team seats or central billing exist, and the roadmap has no step
for them. The customers named in AGENTS.md are developers, teams and agentic
systems.

**Fix.** Fix 10 below.

### 4. A false "This link cannot be used" panel appears after the password is accepted

Major. Personas met: 3 (every persona that set a password).

**What happened.** After "Set password and continue", the page shows "Setting
your password…". The password is then accepted, and for a quarter to half a
second the card changes to "This link cannot be used. It has expired, it was
used already, or a newer message replaced it. Nothing was changed." with an
"Ask for a new link" button, while "Setting your password…" stays below it.
Then the funnel opens at step 5, signed in, with Baltor Pro. The data
scientist's script read this sequence as a hang (test-tooling gap 1).

The times below are frames taken from each recording.

| Recording | "Setting your password…" | False panel | Step 5, signed in |
| --- | --- | --- | --- |
| Data scientist | 19.30 and 19.80 seconds | 19.95 seconds | 20.35 seconds |
| Claude Code developer | 13.6 to 14.2 seconds | 14.35, 14.42 and 14.50 seconds | 14.65 seconds |
| Pi and OpenCode developer | about 14.8 to 15.05 seconds | 15.30 and 15.36 seconds | 15.60 seconds |

**Evidence.**
[video-frames/data-scientist-19.30s-setting-your-password.png](assets/persona-journeys-2026-09-24/video-frames/data-scientist-19.30s-setting-your-password.png),
[video-frames/data-scientist-19.95s-false-link-panel.png](assets/persona-journeys-2026-09-24/video-frames/data-scientist-19.95s-false-link-panel.png),
[video-frames/data-scientist-20.35s-step-5-signed-in.png](assets/persona-journeys-2026-09-24/video-frames/data-scientist-20.35s-step-5-signed-in.png),
[video-frames/claude-code-developer-14.42s-false-link-panel.png](assets/persona-journeys-2026-09-24/video-frames/claude-code-developer-14.42s-false-link-panel.png),
[video-frames/pi-opencode-user-15.30s-false-link-panel.png](assets/persona-journeys-2026-09-24/video-frames/pi-opencode-user-15.30s-false-link-panel.png),
and the data scientist's screenshot
[data-scientist/11-confirm-password-attempt-1.png](assets/persona-journeys-2026-09-24/data-scientist/11-confirm-password-attempt-1.png).

**Cause, inferred from the source and consistent with every frame.** After
`updateUser` succeeds, the password handler sets `confirmation = null` and
calls `connectService()` (`service.js` lines 438 and 440; the function is at
line 234). `connectService()` starts with `disconnect()` (line 127), and
`disconnect()` calls `showConfirmation()`, which with no confirmation hides the
password step and shows `#confirm-unusable` (`index.html` line 224). The panel
stays up while the activation request and the session request run. On a slow
connection it would stay longer, up to the 35 second request timeout
(`service.js` line 204).

**Why it matters.** The panel says "Nothing was changed" after the password
was changed. One automated customer believed it. A person may press "Ask for
a new link" during the panel.

**Fix.** Fix 2 below.

### 5. A signed-in visitor cannot run the connection check from Get set up

Major. Personas met: 2 (Claude Code developer, Pi and OpenCode developer).

**What happened.** On the signed-in Get set up page, the Claude Code
developer's screenshot shows "Connected as customer.…" and a header with
Account and Sign out, but "Test service connection" is disabled and the only
other control is "Sign in to check access", which leads to the sign-in page.
The page does not say that the check needs a client token, or where to create
one. The Pi and OpenCode developer's goal, "sign up and check the connection",
ended at the same control, although finding 1 had already signed it out.

**Evidence.**
[claude-code-developer/11-select-claude-code-tab.png](assets/persona-journeys-2026-09-24/claude-code-developer/11-select-claude-code-tab.png),
[pi-opencode-user/12-open-pi-tab-signed-in.png](assets/persona-journeys-2026-09-24/pi-opencode-user/12-open-pi-tab-signed-in.png).

**Cause.** `#test-protocol` is disabled whenever `authenticationMode` is
`browser_identity` (`service.js` lines 254 and 871), because the check runs
with a client token. The "Sign in to check access" link is static
(`index.html` line 353). Client tokens are created on the account page behind
the "Load client tokens" button (`#refresh-client-access`, `index.html`
line 281).

**Fix.** Fix 4 below.

### 6. The Pi extension path is plain text, not a link

Major. Personas met: 1 (Pi and OpenCode developer).

**What happened.** The Pi tab says: "Save the extension this website serves at
/assets/pi/baltor.ts as .pi/extensions/baltor.ts in your project folder, and
read it first: Pi runs every extension in that folder with your permissions."
The path is not a link, a button or a code block with a copy control. The
persona's scan of the tab found no link to the file. The file itself is
served: it answered 200 on both hostnames in the follow-up check.

**Evidence.**
[pi-opencode-user/12-open-pi-tab-signed-in.png](assets/persona-journeys-2026-09-24/pi-opencode-user/12-open-pi-tab-signed-in.png),
which is byte-identical to the persona's `03-open-pi-tab.png`.

**Cause.** The Pi recipe's `configuration_note` in
`web_assets/client-recipes.json`, line 79, is rendered as text.

**Fix.** Fix 8 below.

### 7. The phone menu's named control is a hidden 1 pixel checkbox under the logo

Major. Personas met: 1 (phone visitor).

**What happened.** The phone menu is a checkbox, `#menu-toggle`, with the
accessible name "Show the menu". It is clipped to 1 by 1 pixel and sits under
the header logo, so a tap at its position lands on the logo link. The 44 by 44
pixel icon that a person sees and taps is a `label` marked
`aria-hidden="true"`. The persona measured both elements with
`getBoundingClientRect` and `elementFromPoint`. Inferred, not tested with a
screen reader: a person exploring the screen by touch finds no control where
the icon is drawn.

**Evidence.**
[mobile-visitor/01-01-homepage-landing.png](assets/persona-journeys-2026-09-24/mobile-visitor/01-01-homepage-landing.png),
[mobile-visitor/03-03-open-menu.png](assets/persona-journeys-2026-09-24/mobile-visitor/03-03-open-menu.png).

**Cause.** `index.html` line 24 and `web_assets/architecture.css` line 159.

**Fix.** Fix 9 below.

### 8. Nothing explains who vets library items, or how

Major. Personas met: 1 (engineering lead).

**What happened.** The homepage says Baltor "finds them, vets them" and shows
"43 vetted packages in this release". Pricing promises "New vetted additions"
that "pass review". No page says who reviews an item or against what. The
deepest page the lead read, What Baltor is, defines `host_attested` as "the
host's attestation, not a new review performed by the download", which reads
to a buyer like the absence of review.

**Evidence.**
[team-lead-evaluator/01-01-homepage.png](assets/persona-journeys-2026-09-24/team-lead-evaluator/01-01-homepage.png),
[team-lead-evaluator/06-06-pricing.png](assets/persona-journeys-2026-09-24/team-lead-evaluator/06-06-pricing.png),
[team-lead-evaluator/09-docs-what-baltor-is.png](assets/persona-journeys-2026-09-24/team-lead-evaluator/09-docs-what-baltor-is.png).
A search of `index.html` and every page under `web_assets/docs` found the
words vetted, vets and pass review on the homepage, pricing and Get set up,
and no explanation of the review anywhere.

**Cause.** Missing content. The rule exists: the approval decision in
[AGENTS.md](../../AGENTS.md#decisions-that-stand-until-the-owner-changes-them)
says reviewers who did not write an item approve or reject it against written
criteria, the approval record names them, and a producer never approves its
own work.

**Fix.** Fix 7 below.

### 9. "What happens to company code" is answered with "do not send it yet", without dates

Major. Personas met: 1 (engineering lead).

**What happened.** The Security page says: "Do not send private customer
content yet. The final retention policy, deletion workflow and consent
controls remain launch work". It also says the service is "not a multi-region
service, an availability guarantee, an independent security audit or a
compliance certification." The lead called this candid and trust-building, but
without a date it answers the question with "not yet". The published privacy
notice already describes deletion on request and five-day database snapshots,
so part of the Security page's sentence is out of date.

**Evidence.**
[team-lead-evaluator/03-03-security-access-and-data.png](assets/persona-journeys-2026-09-24/team-lead-evaluator/03-03-security-access-and-data.png),
[team-lead-evaluator/04-04-privacy-notice.png](assets/persona-journeys-2026-09-24/team-lead-evaluator/04-04-privacy-notice.png).

**Fix.** Engineering can point the Security page's "What reaches this service"
section at the privacy notice's "Backups and deletion" section and name what
remains: self-service deletion, consent controls and an independent security
review. Dates for those, and any change to the privacy notice, are legal
commitments that need the owner. This is why the fix is not in the ten below.

### 10. Price statements ignore the founding offer

Minor. Personas met: 5.

**What happened.** Before sign-up, nothing mentions the founding offer: the
pricing card shows $29 a month, and the pricing answer to "Is there a free
plan?" says only that the Baltor Harness is free. The data scientist, the
engineering lead and the phone visitor each looked for a free offer before
signing up and could not find it. After sign-up, step 5 says "As one of the
first accounts, it is free each month", while the line under the page heading
still says "Create your account, subscribe to Baltor Pro for $29 a month and
connect your harness." The step list also marks "Subscribe to Baltor Pro, $29
a month, cancel any time" as done for an account that never subscribed. The
Claude Code developer reported the heading line, and the same screen appears
in the data scientist's recording and the Pi and OpenCode developer's
screenshots.

**Evidence.**
[team-lead-evaluator/10-pricing-faq.png](assets/persona-journeys-2026-09-24/team-lead-evaluator/10-pricing-faq.png),
[data-scientist/04-pricing.png](assets/persona-journeys-2026-09-24/data-scientist/04-pricing.png),
[mobile-visitor/06-06-pricing.png](assets/persona-journeys-2026-09-24/mobile-visitor/06-06-pricing.png),
[team-lead-evaluator/12-get-started-view-only.png](assets/persona-journeys-2026-09-24/team-lead-evaluator/12-get-started-view-only.png),
[claude-code-developer/09-plan-step.png](assets/persona-journeys-2026-09-24/claude-code-developer/09-plan-step.png)
(byte-identical to the Pi and OpenCode developer's `10-set-password.png`),
[video-frames/data-scientist-20.35s-step-5-signed-in.png](assets/persona-journeys-2026-09-24/video-frames/data-scientist-20.35s-step-5-signed-in.png).

**Cause.** `.funnel-price` (`index.html` line 202) is static. The step list
marks steps done by position (`service.js` line 481). The founding offer text
exists only in the plan-state table (`service.js` line 454).

**Fix.** Fix 6 below.

### 11. Test accounts hold founding places that nobody can use

Minor, operational. Personas met: 3 (every persona that signed up).

The Pi and OpenCode developer reported that its run used one founding place.
The recordings show that all three sign-ups did. See
[accounts and founding places](#accounts-and-founding-places) for the state,
the decision and the next operator step.

### 12. The password button accepts a click before the page can use it

Minor. Personas met: 1 (Pi and OpenCode developer).

**What happened.** For about two seconds the Pi and OpenCode developer's
clicks on "Set password and continue" were answered in red: "This page is
still loading its sign-in settings. Wait a moment, then try again. Your link
was not used." The button stayed enabled. The next click worked. The
[release 24 record](../../artifacts/release-24-2026-09-24/README.md) saw the
same refusal from its own check script and asked for the button to stay
disabled until the settings load.

**Evidence.**
[video-frames/pi-opencode-user-13.50s-settings-still-loading.png](assets/persona-journeys-2026-09-24/video-frames/pi-opencode-user-13.50s-settings-still-loading.png).

**Cause in release 24.** `#confirm-button` (`index.html` line 223) was enabled
before `openBrowserIdentity()` created the identity client (`service.js` line
886), and the submit handler then refused (`service.js` line 419).

**Status.** Fixed on main in `9cc54e14`, roadmap step S-6.99, after these runs:
`showConfirmation()` now keeps `#confirm-button` disabled and shows a loading
note until the identity client exists. Customers get it with the next
release.

### 13. An internal Get started button carries an outbound arrow

Minor. Personas met: 1 (engineering lead).

The pricing card's Get started button, `#pricing-primary` (`index.html`
line 179), ends with an arrow that usually marks a link leaving the site. It
opens `/get-started` on the same site. Evidence:
[team-lead-evaluator/06-06-pricing.png](assets/persona-journeys-2026-09-24/team-lead-evaluator/06-06-pricing.png).
Fix: remove the arrow span, and keep that glyph for links that leave
`baltor.ai`.

### 14. The security page is named "Access and data" and linked only from the footer

Minor. Personas met: 1 (engineering lead).

The page at `/security` is called "Access and data" in its eyebrow and in the
footer's Documentation column (`index.html` line 439), and the header does not
link it. A buyer who scans for the word security can miss it. Evidence:
[team-lead-evaluator/01-01-homepage.png](assets/persona-journeys-2026-09-24/team-lead-evaluator/01-01-homepage.png)
(footer) and
[team-lead-evaluator/03-03-security-access-and-data.png](assets/persona-journeys-2026-09-24/team-lead-evaluator/03-03-security-access-and-data.png).
Fix: label the footer link "Security, access and data".

### 15. The account page shows internal identity vocabulary

Minor. Personas met: 1 (Claude Code developer).

"Current service identity" lists Tenant and Namespace, both a long
`customer.` value, Scopes such as `billing:manage, provisioning:metadata,
provisioning:read, usage:read`, and Access `bodies`, with no explanation.
Evidence:
[claude-code-developer/13-confirm-signed-in-on-account.png](assets/persona-journeys-2026-09-24/claude-code-developer/13-confirm-signed-in-on-account.png).
Cause: `connectService()` fills `#account-facts` (`index.html` line 280) with
the raw principal fields. Fix: one plain line above the table, for example
"This lets Baltor confirm your plan and count your downloads", and the raw
fields behind a disclosure.

### 16. The confirmation email took up to 10.5 seconds, and the page sets no expectation

Minor. Personas met: 1 (data scientist).

The email arrived in 9.01 seconds in the data scientist's final run, and in
9.05 and 10.49 seconds in its earlier runs. The Claude Code developer waited
3.94 seconds and the Pi and OpenCode developer about 5 seconds. The message
after "Create account" (`signupSent`, `service.js` line 347) does not say how
long the email can take. Evidence:
[data-scientist/09-wait-for-confirmation-email.png](assets/persona-journeys-2026-09-24/data-scientist/09-wait-for-confirmation-email.png).
Fix: say in that message how long the email can take, for example "The email
usually arrives within a minute."

### 17. No data cleanup example or case study

Minor. Personas met: 1 (data scientist).

The homepage shows one recorded step, splitting address lines in a customer
file, but no page links a data cleanup example, case study or result. The
[use cases](assets/persona-journeys-2026-09-24/data-scientist/02-use-cases.png),
[efficiency](assets/persona-journeys-2026-09-24/data-scientist/03-efficiency.png),
[pricing](assets/persona-journeys-2026-09-24/data-scientist/04-pricing.png)
and [docs](assets/persona-journeys-2026-09-24/data-scientist/05-docs.png)
screenshots show what the persona read. Fix: the data cleanup demonstration
that roadmap step S-6.37 already plans, linked from Use cases and Efficient
operation.

### 18. Signed-in pages still show signed-out prompts

Polish. Personas met: 1 (Claude Code developer).

Signed in, Get set up still opens with "Create your account", a Get started
button and "Already have an account? Sign in", and the account page's
Subscription access panel says "Connect to check this service's billing
configuration." while the page is connected. Evidence:
[claude-code-developer/11-select-claude-code-tab.png](assets/persona-journeys-2026-09-24/claude-code-developer/11-select-claude-code-tab.png),
[claude-code-developer/13-confirm-signed-in-on-account.png](assets/persona-journeys-2026-09-24/claude-code-developer/13-confirm-signed-in-on-account.png).
Fix: hide the account step and the sign-in prompts for a signed-in visitor,
and load the billing state when the account page opens.

### 19. Only the Pi tab names a checked version

Polish. Personas met: 1 (Pi and OpenCode developer).

The Pi tab says it was "Checked end to end with Pi 0.73.1 and Gemma 4 31B
through Ollama Cloud on September 23, 2026". The Codex and OpenCode tabs say
their configuration is documented and native end-to-end qualification is
pending. The persona's report wrote the version as 0.7.31; the page says
0.73.1. The difference is honest, but a developer who compares harness support
reads OpenCode as less finished. Evidence:
[pi-opencode-user/06-open-opencode-tab.png](assets/persona-journeys-2026-09-24/pi-opencode-user/06-open-opencode-tab.png).
Fix: when Codex and OpenCode pass the same end-to-end check, give their tabs
the same dated line.

## Test-tooling gaps

These are faults in the persona scripts or their inbox provider, not in the
product. They are not counted above.

1. **The data scientist's reported hang.** The script saved its screenshot 0.49
   seconds after the click, while the page still said "Setting your
   password…". It then waited 20 seconds for `#confirm-button` to become
   visible and enabled for a second click, but the page had already moved to
   step 5. The script also read the page address right after the click, so it
   recorded `/auth/confirm`. Its follow-up sign-in with a deliberately wrong
   password got the generic failure, which cannot say whether an account
   exists
   ([data-scientist/verify-03-result.png](assets/persona-journeys-2026-09-24/data-scientist/verify-03-result.png)).
   The recording settles it: the account exists and holds the founding offer.
2. **The data scientist's first two runs.** Both reported "the confirmation
   link did not lead to a password-setup form". The script had taken the link
   from the email's HTML without decoding `&amp;`, so the page received
   `amp;type` instead of `type` and correctly refused the link. A mail client
   decodes it. The third run fixed the decoding. Each earlier run left one
   unconfirmed sign-up.
3. **mail.tm refused `baltor-persona-` addresses.** The phone visitor's report
   counts seven answers of 422 "not valid" and one 429 over about four minutes,
   so it never had an address to enter and its sign-up was not exercised. The
   runs recorded three explanations. The phone visitor suspected abuse
   detection on the shared prefix. The Pi and OpenCode developer's probe
   concluded that mail.tm refuses local parts longer than about 9 to 12
   characters. The Claude Code developer's and the data scientist's probes
   isolated the word "persona". Local parts of 22 and 20 characters were
   accepted, at about 14:18 and 17:05 UTC, which contradicts the length
   explanation. The word explanation fits every observation, but mail.tm has
   not confirmed it.
4. **The Claude Code developer's last two steps.** The script never pressed
   "Load client tokens" on the account page, and it looked for the signed-out
   header link `data-nav="get-set-up-guide"` while the signed-in header uses
   `data-nav="get-set-up"`. Client token creation and the signed-in copy of
   the connection entry were therefore not exercised. The first draft of its
   report listed both as blockers; its final report withdrew them.
5. **The phone visitor's empty inbox check.** "No email within 15 seconds" has
   no meaning, because no address was submitted. The browser's own "Please
   fill out this field" message is what
   [mobile-visitor/09-09-submit-create-account.png](assets/persona-journeys-2026-09-24/mobile-visitor/09-09-submit-create-account.png)
   shows.
6. **Different timing fields.** The reports' `time_to_value_seconds` measured
   different things: nothing for the Claude Code developer, the time until the
   script stopped for the data scientist, the whole run for the engineering
   lead and the Pi and OpenCode developer, and the time to reach Get started for
   the phone visitor. The persona table uses one definition.

Changes for the next persona run: keep inbox credentials and passwords in the
system keyring and reuse the accounts; use local parts without the word
"persona"; decode HTML entities in email links; wait for the next page state
instead of the old button; press "Load client tokens"; select header links by
their text; and give the phone visitor an inbox prepared before the run.

## What worked

- Sign-up from an email address to an active account with Baltor Pro worked
  for every persona that tried it, in about 14.6, 15.5 and 20.2 seconds of
  recording, including detours and the email wait. The email arrived in 3.94
  to 10.49 seconds.
- No broken links. The engineering lead checked all 34 same-site links on the
  seven pages it read, and each answered 200. No persona recorded a broken
  link.
- Four of five runs recorded no console error. The fifth is described in
  [console errors](#console-errors).
- Strict response headers, recorded by the engineering lead: a content
  security policy of `default-src 'none'; script-src 'self'` with the other
  sources limited to the site and the identity provider, `X-Frame-Options:
  DENY`, `Referrer-Policy: no-referrer`, `X-Content-Type-Options: nosniff`,
  and a permissions policy that blocks camera, microphone and geolocation.
- Wording that personas said earned trust: the privacy notice's table of what
  is stored, where and why; the pricing page's "What we do not claim"; the
  connection check's statement that it runs no work and spends no model
  credits; and the Pi tab's dated end-to-end check.
- On the phone viewport, the menu opened and closed, and Use cases, Pricing
  and Get started rendered and worked.

## Console errors

The Pi and OpenCode developer's run logged one "Failed to load resource: the
server responded with a status of 404", without the address of the resource.
Its own audit of every same-site link on `/setup` found no 404 on `baltor.ai`.
The follow-up for this record loaded `/`, `/setup`, `/get-started`,
`/auth/confirm`, `/account` and `/assets/pi/baltor.ts` on both
`baltor-pilot.fly.dev` and `baltor.ai`, signed out: 12 loads, every one 200,
no response of 400 or above and no console error. The 404 most likely came
from a signed-in request during the confirmation flow on the Fly hostname.
That is inferred; the resource is still unidentified. The other two sign-ups
went through the same flow with no console error.

## The ten fixes that would help most

1. **Keep the whole journey on `baltor.ai`.** Page: the confirmation email,
   `/auth/confirm` and Get set up. Elements: the host file's
   `http.public_base_url`, now `https://baltor-pilot.fly.dev`, which
   `confirm_link()` builds every emailed link from (`account_email.py` line
   740); and the connection entries `#protocol-url`, `#setup-endpoint` and
   every tab's code block, which `service.js` lines 706, 707 and 790 fill from
   `location.origin`. Set the base address to `https://baltor.ai` after adding
   the `baltor.ai` addresses to the identity provider's redirect list. The same
   value also moves the protocol resource and the identity callback (`http.py`
   lines 597, 1404 and 1434), so check a client connection after the change.
   Fill the entries from the `resource` address that
   `/.well-known/oauth-protected-resource/mcp` already publishes. Then rerun
   `tools/check_live_account_journeys.mjs`. Closes the main cause of finding 1.
2. **Remove the false "This link cannot be used" panel.** Page:
   `/auth/confirm`. Element: `#confirm-unusable` (`index.html` line 224),
   shown by `disconnect()` (`service.js` line 127) inside `connectService()`
   (line 234) after the password was accepted. Keep the password card with a
   "Password set. Opening your account…" status until step 5 opens. Add a
   browser check that fails when `#confirm-unusable` is visible after
   `updateUser` succeeded. Closes finding 4.
3. **State the live access facts on Security and How it works.** Pages:
   `/security`, "Current operational limits" and the closing notice, and
   `/how-it-works`, the "Available today" notice. Elements: `index.html`
   lines 379 and 321. Say that anyone can create an account through Get
   started, that people sign in with their email address and password, and
   that client tokens come from the account page. Remove the operator and test
   token wording. Add a check that fails when a page says account creation is
   closed while the service reports registration open. Closes finding 2.
4. **Give a signed-in visitor a path to the connection check.** Page:
   `/setup`, "Check the service connection". Elements: `#test-protocol`,
   disabled for a browser sign-in (`service.js` lines 254 and 871), and the
   static "Sign in to check access" link (`index.html` line 353). For a
   signed-in visitor, replace the link with "Create a client token", which
   opens the account page's token panel, and say in one line that the check
   runs with a client token. Closes finding 5.
5. **Keep a signed-in person signed in across a reload.** Page: every
   signed-in page. Element: `createIdentityClient` (`service.js` lines 110 and
   111), which passes `persistSession:false`. Keep the identity session for
   the life of the browser tab in session storage, keep client tokens in page
   memory as today, and update the Security page sentence "Closing or
   reloading the page clears that connection." Reason: a reload, a new tab or a
   typed address signs a person out today, which is what ended the Pi and
   OpenCode developer's session. Session storage survives a reload and ends
   with the tab, and the content security policy `script-src 'self'` limits
   the script that could read it. Closes the remaining cause of finding 1.
6. **Make every price statement follow the founding offer.** Pages:
   `/get-started` and `/pricing`. Elements: `.funnel-price` under
   `#funnel-title` (`index.html` line 202), the step list that `service.js`
   line 481 marks done by position, and the answer to "Is there a free plan?"
   (`index.html` line 196). Drive the heading line and step 4 from the plan
   state that the step 5 card already reads (`founding_free_monthly`,
   `service.js` line 454). State the offer on the pricing page while places
   remain, from a count the service publishes. Closes finding 10.
7. **Say who reviews library items, and against what.** Pages: `/security`, a
   new "How review works" section, and `/docs/what-baltor-is`, including its
   `host_attested` row. Link the section from the homepage sentence "Baltor
   finds them, vets them" (`index.html` line 34) and the pricing line "New
   vetted additions". Describe the approval rule in plain words, and only what
   the approval records support. Closes finding 8.
8. **Link the Pi extension.** Page: `/setup`, Pi tab. Element: the Pi recipe's
   `configuration_note` in `client-recipes.json` line 79. Render
   `/assets/pi/baltor.ts` as a link to the served file, with a copy action,
   next to the sentence that tells the reader to read it first. Closes finding
   6.
9. **Put the phone menu's name on the control people touch.** Page: every
   page at phone width. Elements: `#menu-toggle` (`index.html` line 24),
   clipped to 1 pixel by `architecture.css` line 159, and the visible
   `label.menu-button`, marked `aria-hidden="true"`. Use one visible button
   that carries the name "Show the menu", `aria-expanded` and
   `aria-controls="main-nav"`, or remove `aria-hidden` from the label, give it
   the name and move the checkbox off the logo. Closes finding 7.
10. **Tell teams, where the homepage speaks to them, that each person holds
    their own account, and record team seats as roadmap work.** Page: the
    homepage. Elements: the sections headed "Three things teams do with
    Baltor." and "Built for teams that check the details." (`index.html` lines
    81 and 108). Add the pricing answer's own words, "One account holds one
    person's keys. Shared accounts and team billing are later work.", and open
    a roadmap step for team seats and central billing. Closes the copy part of
    finding 3.

The other fixes are in their findings: 9 (the dates need the owner), 11 (an
operator step), 12 (already fixed on main, waiting for a release) and 13 to
19.

## Roadmap and follow-up

- Roadmap step S-6.33, website fixes from the persona and interface reviews,
  owns fixes 2 to 10. Its acceptance, "A first-time visitor can see what is in
  the library, create an account, and follow Get started to a working
  connection without contradictions, on every hostname", is not met: findings
  1, 2, 4, 5 and 10 are contradictions on that path.
- Fix 1 changes the live host file and the identity provider's settings, and
  fix 5 changes how the browser keeps a sign-in, so both follow the release
  steps of the
  [working cycle](../context/TAKEOVER-CHECKPOINT-2026-09-20.md#working-cycle).
- Roadmap steps S-6.85 and S-6.89 own the accounts and the founding offer
  (findings 10 and 11). Step S-6.99 holds the fix for finding 12. Step S-6.37
  plans the data cleanup demonstration (finding 17). No step covers team
  seats (finding 3).
- Roadmap step S-6.55 asks for a persona review record after every release.
  This is the record for release 24.
- This change adds this record, its 43 images in
  `assets/persona-journeys-2026-09-24/`, the evidence README and the
  regenerated records index. It does not change the roadmap, the site or any
  live account.

## Limits

- Five scripted personas, one run each, and three runs for the data scientist.
  They are automation guided by a model, not people. Their judgments about
  trust and clarity are model-written.
- Not exercised: checkout and payment (the founding offer skipped them),
  client token creation, the connection check, the Codex and OpenCode flows
  beyond reading their tabs, a sign-up on the phone viewport, and a reload of
  a signed-in page.
- The phone visitor was Chromium with a phone viewport, touch and a phone user
  agent, not a real phone.
- Screenshots and recordings are from release 24 on September 24, 2026. Line
  numbers refer to main `a8e82cb2`.
