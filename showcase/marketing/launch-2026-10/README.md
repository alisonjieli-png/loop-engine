# Baltor launch kit, October 2026

Kind: launch kit, prepared by engineering on October 16, 2026 for the owner to
launch Baltor from their personal accounts. Everything here is a draft. Nothing
has been posted, emailed, submitted or scheduled, and no account was created.
The owner signs in, posts and replies under their own identity; engineering
keeps the facts true, runs the checks and fixes what breaks.

Every checkable fact in the kit comes from the [fact sheet](fact-sheet.md),
which names its live source and read time or its release record. Read the live
values again on the gate day and correct the drafts where they changed.

## What is in the kit

| Item | Use it for | How to use it |
| --- | --- | --- |
| [Fact sheet](fact-sheet.md) | The single source of counts, prices, harness names, brands and dates | Check it first; every draft defers to it |
| [Show HN kit](announcements/show-hn.md) | Hacker News | Titles, link and a fact outline. Write the body and every reply by hand: Hacker News refuses generated or AI-edited text |
| [Product Hunt](announcements/product-hunt.md) | Product Hunt | Name, tagline, description, maker's first comment, five gallery captions and topics, within the field limits |
| [LinkedIn](announcements/linkedin.md) | The owner's LinkedIn profile | Edit into your voice, add one screenshot, post |
| [X thread](announcements/x-thread.md) | The owner's X account | Eight posts, each within 280 characters as X counts them |
| [Newsletter](announcements/newsletter.md) | The owner's beehiiv newsletter | Subject, preview text and the issue, led by creative work |
| [Communities](announcements/communities.md) | The Cursor Community Forum and the OpenAI Developer Community | Two drafts with the rules they follow, and why other communities were left out |
| [Press kit](press-kit.md) | Journalists, partners and listings | Boilerplate at 50, 100 and 250 words, contact lines, logo and icon files, screenshots with alt text |
| [Founder deck](founder-deck.md) | Investor meetings and the Y Combinator interview | Ten slides with speaker notes and sources |
| [Launch runbook](launch-runbook.md) | The gate day and both launch days | Gates, timeline in Eastern and Pacific time, who does what, monitoring, rollback, support answers and known limits |
| [Media inventory](media-inventory.md) | Videos, cards and images | Which are current, which need a refresh and the command for each |
| [Screenshots](screenshots/capture-record.json) | Every channel | Twelve fresh WebP captures of the live sites, with their capture record |
| [`capture-screenshots.mjs`](capture-screenshots.mjs) | Refreshing the screenshots | Read-only capture of the six pages at two sizes; tested by `capture-screenshots.test.mjs` |

## Launch-day order

The [runbook](launch-runbook.md) has the full timeline and the reasons.

1. **Monday, October 26, the gate day.** Engineering runs the live checks and
   refreshes the facts. The owner decides on email capacity, the support
   address and payments, fills the placeholders, then gives the go and
   schedules Product Hunt.
2. **Tuesday, October 27, 12:01 a.m. Pacific (3:01 a.m. Eastern).** The
   scheduled Product Hunt launch goes live. The owner posts the maker's first
   comment when they wake.
3. **8:30 a.m. Eastern.** LinkedIn post.
4. **9:30 a.m. Eastern.** X thread.
5. **10:30 a.m. Eastern.** Newsletter.
6. **Wednesday, October 28, 8:30 a.m. Eastern (5:30 a.m. Pacific).** Show HN,
   written by hand. The owner stays in the thread.
7. **1:00 p.m. Eastern.** Cursor Community Forum, Showcase category.
8. **2:00 p.m. Eastern.** OpenAI Developer Community, Codex category.
9. **Thursday, October 29.** Replies, the launch report, and the real numbers
   into the Y Combinator draft before the November 2 deadline.

Engineering checks the live service every hour from 9 a.m. to 9 p.m. Eastern
on both launch days. Nobody asks anyone to upvote, and the Hacker News thread
is not linked from the other channels.

## Decisions made, and why

| Decision | Reason |
| --- | --- |
| Product Hunt and Show HN on separate days, October 27 and 28 | A solo maker has to stay in each thread all day, and both land before the Y Combinator deadline so the launch numbers can go into the application. The fallback is November 4 and 5. |
| No finished Show HN body | Hacker News asks for text written by hand and refuses LLM-generated or LLM-edited words, so the kit gives facts and structure instead. |
| The founding offer stays out of the posts | Only a few places exist and the number left is not public; a launch could use them up within minutes and make the posts wrong. |
| Show HN links to `https://baltor.ai` | The rules ask for something people can try without signing up; the homepage leads to the feeds, component pages, demo and setup guides, all usable without an account. |
| Copy says "files" | The owner's October 8 direction. The fact sheet keeps the component count for reference. |
| Two communities, not more | The Cursor forum and the OpenAI forum publish rules that allow sharing your own work with disclosure. Reddit's rules could not be read from this network; DEV, Lobsters, Indie Hackers and the Hugging Face forums were checked and left out for the reasons in the communities file. |
| AgentFeeds is the brand-site screenshot | It is the free, no-account path that most posts point to. |
| AgentBriefs and Max stay out of the posts | AgentBriefs is not live; Max is listed and not sold during the public preview. |
| Release freeze during the launch window | From 5 p.m. Eastern on the gate day to 8 p.m. Eastern on launch day 2, only reviewed fixes are released, so the posted screenshots and facts stay true. |

## Placeholders the owner fills

| File | Placeholder |
| --- | --- |
| [Fact sheet](fact-sheet.md) | Paying subscriptions today; monthly recurring revenue today; accounts created; one sentence on why you built this |
| [Show HN kit](announcements/show-hn.md) | Why you built it; who is behind it; earlier HN threads, or none |
| [Product Hunt](announcements/product-hunt.md) | Your name; one or two sentences on why you built it |
| [LinkedIn](announcements/linkedin.md) | One sentence on why you built it |
| [Newsletter](announcements/newsletter.md) | Greeting or merge field; opening line; how long you have been building; sign-off; newsletter name |
| [Press kit](press-kit.md) | Founder name and title as they should be printed |
| [Founder deck](founder-deck.md) | A moment the problem cost you time; paying subscriptions, monthly recurring revenue and accounts today; a team line, if wanted; amount, terms and use of funds; the introductions you want |
| [Launch runbook](launch-runbook.md) | The support route set up for launch; your refund decision |

## Rules every draft follows

- Every number, price, harness name, brand and date comes from the fact sheet.
  Nothing in the kit invents traction, customers, testimonials, revenue or
  benchmark results.
- Say files, not packages. Do not describe the library as "reviewed".
- No em dashes or en dashes, no exclamation marks and no emoji.
- Never ask for an upvote. Invite people to visit and comment.
- Hacker News text is written by hand. The forum drafts are starting points
  to rewrite in your own words, as their rules ask.
