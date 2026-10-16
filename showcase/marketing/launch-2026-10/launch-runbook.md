# Launch runbook

Kind: launch-day operating plan, prepared October 16, 2026. It names who does
what, in which order, how the live service is watched and how a bad change is
undone. The owner posts and signs in under their own identity; engineering
prepares, checks, fixes and rolls back. Facts come from the
[fact sheet](fact-sheet.md). Authority for releases and rollbacks is the
[commit, push and release authority](../../../AGENTS.md#commit-push-and-release-authority)
section of AGENTS.md; this runbook adds none.

## Dates

| Day | Date | What happens |
| --- | --- | --- |
| Gate day | Monday, October 26, 2026 | Every go or no-go gate below is checked |
| Launch day 1 | Tuesday, October 27, 2026 | Product Hunt, LinkedIn, X and the newsletter |
| Launch day 2 | Wednesday, October 28, 2026 | Show HN, then the two community posts |
| Follow-up | Thursday, October 29, 2026 | Replies, the launch report, and launch numbers into the Y Combinator draft |

Why these dates: the launch lands before the Y Combinator deadline of
November 2, 2026 at 8 p.m. Pacific, so real launch numbers can go into the
application. Product Hunt and Show HN fall on separate days because a solo
maker needs to stay in each thread all day, and Hacker News should not be
linked from the other channels. Daylight saving time holds until November 1,
so on these dates Eastern time is UTC minus 4 and Pacific time is UTC minus 7.

If a gate fails, move the two launch days to Wednesday, November 4 and
Thursday, November 5, after the Y Combinator deadline and clear of Election
Day on November 3. From
November 1, Eastern time is UTC minus 5 and Pacific time is UTC minus 8; the
local times in the timeline stay the same.

## Go or no-go gates

Check each gate on the gate day. A failed required gate moves the launch; the
launch never goes around a broken path.

| Gate | Owner of the check | Required | How it is checked |
| --- | --- | --- | --- |
| 1. Email capacity for sign-ups. Every sign-up sends a confirmation email through Resend. The recorded plan is Resend Free, which Resend limits to 100 emails a day; Pro costs $20 a month with no daily limit (resend.com/pricing, read October 16, 2026). | Owner decides; engineering reads the plan | Yes | The owner upgrades the plan or records that 100 emails a day is accepted. Spending beyond the recorded allowance is the owner's decision under AGENTS.md. |
| 2. A support channel that answers within hours. Today the [support page](https://baltor.ai/support) lists only postal mail and the public issue tracker. | Owner names the destination; engineering wires it | Yes | A test message sent to the new address reaches the owner. Until then, the launch threads and the issue tracker are the only fast routes. |
| 3. Public Good access renewed. The current grants expire on October 31 and November 1, 2026 (UTC). | Engineering | Yes | The guarded policy path renews the grants; a signed-in account downloads one Public Good file afterwards. |
| 4. Every hostname answers. | Engineering | Yes | The live pulse passes on every hostname; health is ready with all required checks. |
| 5. What a visitor sees works on desktop and phone. | Engineering | Yes | The person-oriented site check passes on `https://baltor.ai`. |
| 6. Each harness named in the posts connects. | Engineering, with the owner for any sign-in that needs a personal account | Yes | One connection and one download from each of Claude Code, Codex, OpenCode, Pi and Cursor. Remove any name that fails from every draft. |
| 7. A new person can sign up. | Engineering | Yes | A fresh address receives the link, sets a password and reaches the subscription step. No charge is made. |
| 8. Payments look healthy. | Owner | Yes | The Stripe dashboard shows the live checkout and no unexplained failed payments. |
| 9. The facts in the drafts are still true. | Engineering | Yes | The fact sheet values are read again; drafts change where a value changed. |
| 10. The owner's two launch days are free. | Owner | Yes | Calendar |
| 11. No feature release during the launch window. | Engineering | Yes | From 5 p.m. Eastern on the gate day until 8 p.m. Eastern on launch day 2, only reviewed fixes are released. |

## Timeline

Times are Eastern Daylight Time and Pacific Daylight Time for the recommended
dates.

### Gate day, Monday, October 26

| Eastern | Pacific | Who | Task |
| --- | --- | --- | --- |
| 9:00 a.m. | 6:00 a.m. | Engineering | Run gates 3 to 7 and 9. Capture fresh screenshots and compare them with the press kit. |
| 12:00 p.m. | 9:00 a.m. | Owner | Decide gates 1, 2, 8 and 10. Fill the placeholders in every draft. |
| 3:00 p.m. | 12:00 p.m. | Engineering | Update the fact sheet and drafts where a fact changed. Start the release freeze at 5 p.m. Eastern. |
| 5:00 p.m. | 2:00 p.m. | Owner | Go or no-go. On go, schedule the Product Hunt launch for 12:01 a.m. Pacific. |

### Launch day 1, Tuesday, October 27

| Eastern | Pacific | Who | Task |
| --- | --- | --- | --- |
| 3:01 a.m. | 12:01 a.m. | Product Hunt | The scheduled launch goes live. |
| 3:15 a.m. | 12:15 a.m. | Engineering | Pulse, health and capabilities checks. |
| 6:30 a.m. | 3:30 a.m. | Owner | Post the maker's first comment if it is not up yet; answer overnight comments. |
| 7:00 a.m. | 4:00 a.m. | Engineering | Person-oriented site check; read the email count against the daily limit. |
| 8:30 a.m. | 5:30 a.m. | Owner | LinkedIn post. |
| 9:30 a.m. | 6:30 a.m. | Owner | X thread. |
| 10:30 a.m. | 7:30 a.m. | Owner | Newsletter send. |
| Every hour, 9 a.m. to 9 p.m. | 6 a.m. to 6 p.m. | Engineering | Pulse, health, email count and error review; tell the owner about any fix. |
| 12:00 p.m. | 9:00 a.m. | Owner and engineering | Midday review: sign-ups, emails sent, errors, support messages. Decide on any fix. |
| 5:00 p.m. | 2:00 p.m. | Owner | Reply round on Product Hunt, LinkedIn and X. |
| 11:00 p.m. | 8:00 p.m. | Owner | Last Product Hunt reply round of the day. |

### Launch day 2, Wednesday, October 28

| Eastern | Pacific | Who | Task |
| --- | --- | --- | --- |
| 7:00 a.m. | 4:00 a.m. | Engineering | Pulse and site check; overnight summary for the owner. |
| 8:30 a.m. | 5:30 a.m. | Owner | Submit Show HN by hand, from the personal account. Stay in the thread. |
| 1:00 p.m. | 10:00 a.m. | Owner | Cursor Community Forum post in Showcase, after the contributions its rules ask for. |
| 2:00 p.m. | 11:00 a.m. | Owner | OpenAI Developer Community post in the Codex category. |
| Every hour, 9 a.m. to 9 p.m. | 6 a.m. to 6 p.m. | Engineering | The same checks as day 1. |
| 6:00 p.m. | 3:00 p.m. | Owner | Final reply round on every thread. |
| 8:00 p.m. | 5:00 p.m. | Engineering | End the release freeze. Write the launch report. |

### Follow-up, Thursday, October 29

| Eastern | Pacific | Who | Task |
| --- | --- | --- | --- |
| 10:00 a.m. | 7:00 a.m. | Owner | Answer remaining comments. Put the real sign-up, subscription and feedback numbers into the Y Combinator draft. |
| 11:00 a.m. | 8:00 a.m. | Engineering | Turn every reported defect into a roadmap item or a fix, and record what changed. |

## Who does what

| The owner | Engineering |
| --- | --- |
| Signs in to Product Hunt, Hacker News, LinkedIn, X, beehiiv and the forums, and posts by hand | Keeps the fact sheet and drafts true to the live service |
| Writes the Show HN body and every Hacker News reply in their own words | Runs the gates, the hourly checks and the person-oriented site check |
| Decides the email plan, the support address and any spending | Wires the support address once the owner names it, and renews Public Good access |
| Reads Stripe, Resend and the Administration view, and shares counts | Fixes defects through reviewed commits, releases them and checks them live |
| Answers comments and support messages | Rolls back a bad release and tells the owner what changed |
| Never asks anyone to upvote | Never posts, emails people or changes a provider setting outside the release path |

## Monitoring during the launch

### Live checks

Run from a current checkout of `main`. All of them read only and send no
credential, except where noted.

| Check | Command | Passes when |
| --- | --- | --- |
| Live pulse, every hostname | `python3 tools/check_live_pulse.py --output /absolute/new/pulse.json` | Every page answers, health is ready with its required checks, every host reports the same capabilities |
| Health | `curl -sS https://baltor.ai/api/v1/health` | `ready` is true and every required check passed |
| Library and registration | `curl -sS https://baltor.ai/api/v1/capabilities` | `registration_available` is true and the file count matches the posts |
| What a visitor sees | `node tools/check_live_site_for_people.mjs https://baltor.ai /absolute/new/folder` | Each page opens with its heading and no script error, at desktop and phone widths |
| Screenshots still match | `node showcase/marketing/launch-2026-10/capture-screenshots.mjs /absolute/new/folder` | Twelve images, every page answers 200, nothing scrolls sideways |
| Scheduled pulse | The "Live pulse" workflow in GitHub Actions, every six hours at 17 minutes past the hour, or dispatched by hand | The run is green |

The Node checks need the pinned browser tools from
`npm ci --prefix showcase --ignore-scripts --no-audit --no-fund`.

### Dashboards

| Dashboard | Who reads it | Watch for |
| --- | --- | --- |
| Fly, application `baltor-pilot` | Engineering | Machine health, memory against the 4 GB machine, response times, error logs |
| Cloudflare | Engineering | Worker errors and request volume on the nine Baltor hostnames |
| Resend | Owner, or engineering with read access | Emails sent today against the plan's daily limit, bounces |
| Stripe | Owner | Checkout sessions, new subscriptions, failed payments, disputes |
| Administration view on baltor.ai | Owner | New accounts and their plan state |
| GitHub Actions | Engineering | Continuous integration on any fix, and the live pulse |

The internal systems portal is not a source of launch facts; use the live
records and the dashboards above.

### When to act

| Signal | Action |
| --- | --- |
| Health not ready, or a host failing the pulse | Engineering investigates at once and tells the owner; roll back if the latest release caused it |
| Emails sent today near the plan's daily limit | The owner decides on the plan upgrade; meanwhile the owner posts the delayed-email answer below |
| Memory or response times climbing on the single machine | Engineering looks for a hot path; the owner pauses new promotion until it settles |
| A defect reported in a thread | Engineering reproduces it, fixes it through the normal reviewed path and gives the owner a one-line reply to post |

## Rollback

| What went wrong | Who | How |
| --- | --- | --- |
| A release made the service worse | Engineering | Deploy the saved release 92 image, `sha256:aa73def135cddf3b27a45c39d8b37e0083b609ae922a2744cc8bb5e3449315ec`, with the saved configuration (`fly deploy --image`); no host-file restore is needed. Then run the live pulse. See the [hosting procedure](../../../docs/guides/hosting-and-deployment-procedures.md) and the [current deployment](../../../docs/architecture/MVP-CLIENT-SERVER.md#current-deployment). |
| An edge release made pages worse | Engineering | Return to the retained edge deployment `6231d769-3582-42c8-b648-1e9bc28e849a`, version `4165d810-05a0-43a6-a41d-3bf70bcd29f7`, then read the pages back. |
| A library component is broken or unsafe | Engineering | Withdraw it through the next library release; every later release honours the withdrawal. |
| A post states something wrong | Owner | Edit the post where the platform allows it, or reply in the thread with the correction. Engineering corrects the fact sheet and drafts. |
| A release done after the gate day must be undone | Engineering | Roll back to the image that was live on the gate day and record why. |

Record every rollback with its reason, as the working cycle requires.

## Support answers

Answer templates for the threads and the support route. Adapt the wording;
keep the facts.

**I did not get the sign-up email.** "Thanks for trying Baltor. Sign-up emails
can take a few minutes, so please check your spam folder. If nothing arrives
within 15 minutes, try once more from <https://baltor.ai/get-started>. Sending
the request many times does not speed it up. If it still does not arrive,
`[OWNER: the support route you set up for launch]`."

**Which harnesses does it work with?** "Setup guides cover Claude Code, Codex,
OpenCode, Pi and the Baltor Harness, with ready entries for Cursor, VS Code
and Gemini CLI. Any app that speaks MCP over Streamable HTTP connects to the
same address, `https://baltor.ai/mcp`. The steps are at
<https://baltor.ai/setup>."

**Do you see my code or my model key?** "No model key, ever: your harness keeps
calling your own provider. Baltor receives your searches and downloads, not
your project files. The privacy notice has the details:
<https://baltor.ai/privacy>."

**What do I get for $49 a month?** "The whole library, searchable from your
harness over MCP or the API. One component at the version you chose counts once
a month, and there is no overage billing. Model usage stays with your own
provider."

**Is Agent Feeds really free? Will I be charged later?** "Agent Feeds is free
through December 31, 2026 (Eastern), with no automatic charge. A paid feed
subscription will only start if you opt in."

**Can I try it without paying?** "Yes. The public feeds need no account, the
component pages and gallery are open, and the local overnight tools are a free
preview. Public Good components are free with an account. The full library is
Pro."

**Is Max available?** "Max is listed at $99 a month and is not sold during the
public preview. The local overnight tools it builds on are free to try now
and stay included with Pro."

**How do I cancel?** "From your account page, at any time. You keep access
until the end of the period you paid for."

**Can I get a refund?** "`[OWNER: your refund decision. The published terms
cover cancellation, not refunds.]`"

**Where do the files come from, and what about licences?** "Every component
names its source and licence, and nothing is served before it passes
automated checks of layout, licence, provenance, secrets and declared
effects. You can inspect each component's files and licence before you
download it."

**A component is broken, unsafe or uses my work without permission.** "Thank
you for telling us. Please report it from your harness after the download, or
through the support page, with the component's name. We withdraw components
that fail review, and every later library release keeps the withdrawal."

**Please delete my account.** "The privacy notice explains how: write to the
contact address it lists and name the account. An operator handles the
request; self-service deletion is not available yet."

**Do you have a team plan?** "Not yet. If your team would use one, tell us
what it needs: seats, private components, an allowlist or audit logs."

**Is it open source?** "The engine behind Baltor is open source under the MIT
licence on GitHub. The hosted library is a paid service."

**Is the service down?** "Thanks for the report. The status page at
<https://baltor.ai/status> shows whether the service is working right now.
We are looking at it and will reply here when it is fixed."

## Known limits

State these plainly when they come up. None of them is a reason to hide the
launch.

- **Email capacity.** On Resend Free, sign-up and recovery emails stop at 100
  a day until the next day, so new people cannot finish signing up.
- **Support route.** The support page offers postal mail and the public issue
  tracker only, until the owner sets up a launch support address.
- **One machine.** The service runs on one Fly machine (2 shared CPUs, 4 GB)
  in one region, with a bounded number of concurrent operations for each
  account. It is not a multi-region service.
- **Browser qualification.** The latest full browser run passed all 4,715
  assertions across 20 hosts, but 21 canceled background fetches keep its
  strict result false. The pages work; that diagnosis is still open.
- **Harness checks.** The setup page lists OAuth for several apps; the
  recorded end-to-end OAuth check is from Claude Code (October 9, 2026). Gate
  6 checks the rest before launch.
- **No measured savings.** No time, token or cost saving is published, and
  the published data cleanup study found no benefit on its test.
- **Preview features.** Overnight / AFK Work is a local preview; there is no
  hosted execution, and Max is not sold.
- **Founding places.** The founding offer has few places and the number left
  is not public, so the posts leave it out.
- **Public Good dates.** The access grants expire on October 31 and
  November 1, 2026 unless renewed (gate 3).
- **AgentBriefs** is not live and is not part of this launch.
