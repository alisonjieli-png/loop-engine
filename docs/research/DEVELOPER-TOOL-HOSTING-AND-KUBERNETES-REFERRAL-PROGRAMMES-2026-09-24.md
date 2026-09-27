# Developer tool, hosting and Kubernetes referral programmes

Kind: dated research record, September 24, 2026, night. It extends the
[first record](AFFILIATE-ADVERTISING-AND-LISTING-INCOME-2026-09-24.md) and
the [second record](INFRASTRUCTURE-AND-AI-SERVICE-REFERRAL-INCOME-2026-09-24.md)
of the same day, whose text stays as it was. The owner asked, in their words:
"Research more affilaite programs to hosting, kubernetes, mail sending, tools
and programs like railway, cursor, LLM tools, developer tools, hosting,
infrastructure, render.io, kubernetes, node hosting, vercel, etc, we need to
have a list of these on the website along with context file that can be
placed into harness working directories so that the harness is aware of
them". Nothing was joined, no account was created, no form was submitted and
no email was sent. The [roadmap](../roadmap/roadmap.yaml) remains the task
authority.

## What this record adds

- **25 more services, checked on September 24, 2026** from their own pages.
  The owner's list named 66 services and products. 26 of those names are new
  here and make 25 rows, because Codeium is now Windsurf; the other 40 were
  covered by the first two records.
- **A machine-readable list of all 145 services** checked across the three
  records, at
  `artifacts/affiliate-programmes-2026-09-24/programmes.json`. The directory
  line generates the website list and the harness context file from it.
- **One ranking for all three records.** It replaces the second record's
  ranking.
- **Rules for the harness context file**, which change one decision of the
  first record.

The scope is the second record's: only money that Baltor earns by referring
its users to a service. Baltor pays no affiliates of its own and pays for no
downloads.

## How this was checked

Each new page was read only when the site's `robots.txt` allowed it for any
reader; no page was refused. No page of Ollama or OpenRouter was read again,
because their terms refuse automated access, as the second record explains.
The rest of the method is the first record's: vendor sitemaps, footers and
programme pages over HTTPS, no search engine, and "Not stated" wherever the
pages read did not say.

## New findings

Read on September 24, 2026. "Window" is the cookie or attribution period.

| Service | Category | Programme | Pays, and for how long | Window | Payout | Restrictions | Sign-up and source |
|---|---|---|---|---|---|---|---|
| MailerSend | Email sending | Affiliate programme on Trackdesk | "20% recurring commission for up to 12 months on paid plans"; "There's no cap" | 90 days | Sales held 30 days, paid from a $50 balance. The questions page says weekly on Fridays through Tipalti (PayPal, direct deposit or wire); the terms say PayPal only, within 45 days of a claim | No paid search ads such as Google Ads or Bing Ads; no cookie overwriting, iframes, hidden links or pop-ups | [programme](https://www.mailersend.com/affiliate/program), [terms](https://www.mailersend.com/legal/affiliate-program-terms) |
| Windsurf (formerly Codeium) | AI coding tools | Referral programme for paying customers | Flex Credits; the amount appears on the referral page and was not captured | Not stated | Credits | Self-referrals and fake accounts disqualify; rewards may be capped; terms updated February 27, 2025 | [referrals](https://windsurf.com/refer), [terms](https://windsurf.com/refer/terms-of-service) |
| Civo | Managed Kubernetes | Partner programme with deal registration; ambassador programme | No link programme. Ambassadors receive "a complimentary $1000 Civo credit" | | | | [partners](https://www.civo.com/partners), [ambassadors](https://www.civo.com/ambassadors) |
| Qovery | Managed Kubernetes | Partner programme | "Earn uncapped commissions on every deal"; rate not published | | | Partner application | [partners](https://www.qovery.com/partners) |
| Heroku | App hosting | No programme found | | | | | Consulting and Elements partner programmes only |
| AWS Amplify | App hosting | No link programme | | | | | The AWS Partner Network is for resale, consulting and technology partners |
| Rancher (SUSE) | Managed Kubernetes | No programme found | | | | | The home page links SUSE's partner finder only |
| Portainer | Managed Kubernetes | No programme found | | | | | Reseller partner pages only |
| Porter | Managed Kubernetes | No programme found | | | | | Home page and sitemap |
| Plunk | Email sending | No programme found | | | | | Home page and sitemap |
| GitHub Copilot | AI coding tools | No programme found | | | | | The Copilot page links the GitHub partner programme only |
| Continue | AI coding tools | No programme found | | | | | Home page |
| Tabnine | AI coding tools | No programme found | | | | | `tabnine.com` now redirects to `tricentis.com` |
| Replit | AI coding tools | No programme found | | | | | Home page; the partners page renders by script and was not read |
| Bolt | AI coding tools | No programme found | | | | | `bolt.new` and `stackblitz.com` home pages |
| Warp | AI coding tools | No programme found | | | | | `warp.dev/referral-program` returns not found; home page |
| Zed | AI coding tools | No programme found | | | | | A campus ambassador programme for students only |
| JetBrains AI | AI coding tools | No programme found | | | | | Partner, reseller and content creator pages |
| LiteLLM | Model tools | No programme found | | | | | A reseller terms page only |
| Linear | Developer tools | No programme found | | | | | Home page and sitemap |
| Auth0 | Developer tools | No programme found | | | | | Marketplace and technology partner pages only |
| Algolia | Developer tools | No programme found | | | | | Partner programme tiers for agencies, with no referral fee |
| Cloudinary | Developer tools | No programme found | | | | | Solution partner pages only |
| Inngest | Developer tools | No programme found | | | | | Home page and sitemap |
| Trigger.dev | Developer tools | No programme found | | | | | Home page and sitemap |

## The owner's list, by category

The evidence for services covered earlier is in the first two records and in each row of `programmes.json`.

- **Managed Kubernetes.** DigitalOcean Kubernetes falls under DigitalOcean's
  affiliate programme (10% of a new user's spend for a year, through CJ).
  Akamai's Linode Kubernetes Engine falls under Akamai Cloud's referral, which
  pays credit only. Vultr Kubernetes Engine falls under Vultr's referral,
  read only from an archived copy. Qovery pays partners commissions on closed
  deals at a rate it does not publish. Civo, Scaleway Kapsule, OVHcloud,
  Hetzner, Rancher, Portainer, Northflank and Porter show no link programme.
- **Node and app hosting.** Railway and Netlify pay cash on published terms,
  and DigitalOcean App Platform falls under DigitalOcean's programme. Vercel's
  affiliate terms are public but its rates are not. Render, Heroku, Koyeb,
  Fly.io and Cloudflare Workers and Pages show none; AWS Amplify has only the
  AWS Partner Network.
- **Email sending.** MailerSend and Postmark pay cash; Postmark's programme is
  limited to a small group of partners at first. Brevo pays a fixed reward it
  does not state. SendGrid pays only on enterprise deals. Mailgun publishes no
  terms. Resend, Mailjet, SparkPost, Loops and Plunk show none.
- **AI coding and model tools.** Lovable pays up to $100 per first-time
  subscriber. v0 paid its ambassadors $10 and $30 per referral. Windsurf pays
  its paying customers in credits. Cursor "ended the referral program due to
  increased levels of fraud". GitHub Copilot, Continue, Tabnine, Replit, Bolt,
  Warp, Zed, JetBrains AI, OpenRouter, LiteLLM and Portkey show none.
- **Developer tools.** 1Password pays through CJ. Twilio pays only on
  enterprise deals. Notion's programme is closed to new affiliates, and
  Doppler's referral programme pays nothing. Sentry, PostHog, Linear,
  Supabase, Neon, Clerk, Auth0, Stripe, Algolia, Cloudinary, Upstash,
  Inngest, Trigger.dev and Tailscale show none.

## One ranking for all three records

Ranked by fit with Baltor's users, who are developers running coding
harnesses and bringing their own models, then by value per paying user, then
by friction. It replaces the second record's ranking. A directory row is
named only where the service's own company publishes it; the second record
explains the two Docker rows still waiting for a match.

| Rank | Service | Terms in brief | Directory rows |
|---|---|---|---|
| 1 | Apify | 20% for 3 months, then 30%, no time limit, cap $2,500 per customer | `com.apify/apify-mcp-server` |
| 2 | Firecrawl | 25% for 12 months, then 15% while subscribed | `io.github.firecrawl/firecrawl-mcp-server` |
| 3 | Novita AI | 10% of all spend for 180 days, no cap; can-I-run presets `a100-80-sxm`, `h100-sxm`, `rtx-4090` | `docker/novita`, waiting for a match |
| 4 | Railway | 15% of 12 months of invoices, plus template kickbacks | `com.railway/mcp` |
| 5 | RunPod | Credits, then 10% cash after 25 spending referrals; can-I-run presets `h100-sxm`, `a100-80-sxm`, `l40s`, `rtx-4090`, `rtx-5090` | None |
| 6 | Vast.ai | 3% of lifetime spend, up to 75% cashable | None |
| 7 | DigitalOcean | 10% of spend for 12 months through CJ, across Droplets, App Platform, Kubernetes and graphics processor machines | None |
| 8 | Netlify | 20% for up to 12 months | None |
| 9 | MailerSend | 20% for up to 12 months, 90-day window, $50 minimum | None |
| 10 | Bright Data | 50% revenue share; per-customer cap $1,000 or $2,500 | `io.github.brightdata/brightdata-mcp` |
| 11 | UptimeRobot | 20% for the life of the subscription | `com.uptimerobot/uptimerobot` |
| 12 | Postmark | 20% for 12 months; limited partner group | None |
| 13 | Pinecone | Rate not published | `docker/pinecone`, waiting for a match |
| 14 | Vercel and v0 | Vercel's rates not published; v0 ambassadors $10 and $30 per referral | `com.vercel/vercel-mcp`, `io.github.vercel/next-devtools-mcp` |
| 15 | Make | 35% for 12 months, Wise only | `com.make/mcp-server` |
| 16 | n8n | 30% for 12 months, 100 euro minimum | None |
| 17 | Better Stack | 25% of net revenue for the first year | None |
| 18 | Kinde | 20% of fees for 12 months | None |
| 19 | 1Password | $2 per signup and 25% of the first payment | None |
| 20 | Lovable | Up to $100 per first-time subscriber | `dev.lovable/mcp` |
| 21 | ScrapingBee | 25% for the life of the customer, capped at $62.25 a month | None |
| 22 | Axiom | 5% of eligible revenue for 12 months | `co.axiom/mcp` |
| 23 | Hostinger | From 40%, rising with volume | `io.github.hostinger/hostinger-api-mcp` |
| 24 | Kit | 50% of the first year, recurring at higher levels | None |
| 25 | beehiiv | 50% to 60% for a year | None |
| 26 | Webflow | 50% of the first subscription for up to 12 months | `com.webflow/mcp` |
| 27 | Monday.com | Up to 100% of first-year sales, by level | `com.monday/monday.com` |
| 28 to 31 | Name.com, Spaceship, Hover, Namecheap | Domain commissions; only if a starter adds a domain step | None |

## The machine-readable list

`artifacts/affiliate-programmes-2026-09-24/programmes.json`, record type
`baltor_referral_programme_list/v1`, holds one row for each of the 145
services the three records checked:

| Status | Rows |
|---|---|
| Cash on published or archived terms (`cash`) | 30 |
| Credit that can partly become cash (`partial_cash`) | 2 |
| A programme without a published rate (`rate_unpublished`) | 7 |
| Credit or promotion only (`credit_or_promotion_only`) | 7 |
| Enterprise or partner deals only (`enterprise_only`) | 8 |
| A programme that pays nothing (`no_compensation`), closed (`closed`) or discontinued (`discontinued`) | 3 |
| Not known (`unknown`) | 4 |
| No programme found (`none_found`) | 84 |

Each row gives the service, its category, its canonical address, the
programme's status, kind, network, pay, duration, window, payout,
restrictions, sign-up and terms addresses, the addresses read, the evidence
state and the retrieval date. It also gives the rank, the relationship kind
the row takes once a programme account is active, the directory rows the
vendor itself publishes, the Docker rows waiting for a match, the models
directory rows and can-I-run presets, and the starter decision that names
the service. The directory rows come from the directory build of 17:58
Coordinated Universal Time (35,278 rows), read only. Each row also keeps the
registry namespaces and code owners used for the match, so the directory
line can recompute them on every new build. Every row stays with no
commercial relationship until the owner's programme account is active.

## Rules for the harness context file

The owner asked for a context file that a harness can load from its working
directory. The first record's second engineering decision kept paid links
out of agent instructions, because a harness can relay or open a link
without a person seeing its label. The context file keeps the owner's
request and that protection together, with four rules that
`programmes.json` carries as `harness_context_rules`:

1. List every service with its canonical address. A paid link, where one
   exists, is a separate field.
2. When the harness shows a person a paid link, it puts the words Paid link
   beside it and tells them that Baltor earns money if they sign up or buy
   through the link, and that it does not raise their price.
3. The harness chooses a service by what the task needs, never by whether it
   has a paid link.
4. The harness never opens a paid link, creates an account or signs up on
   the person's behalf. The person decides.

Reason: section 255.5 of the Endorsement Guides requires the connection to
be disclosed to the person who sees the recommendation, and the guidance
quoted in the first record asks for the disclosure next to the link. When a
harness relays the recommendation, the disclosure has to travel with the
link. Rule 4 also keeps every sign-up a person's own act, which several
programmes require when they ban self-referrals and bot or fake accounts.

## What stays unknown and what needs the owner

Unknown: the Windsurf credit amount, which the referral page shows only in
script; Qovery's commission rate; and the items the second record lists
(Perplexity, Mailgun's terms, the unpublished rates of Vercel, Pinecone,
Composio and Brevo, Bright Data's cap and Vultr's current terms).

The owner's part is unchanged from the second record: identity checks with
each programme or network, tax details, and bank and payout accounts. The
main session confirms whether accepting each programme's terms falls inside
the authority the owner gave on September 24.

## Sources

All read on September 24, 2026. Pages of the earlier records are listed
there.

- [MailerSend programme](https://www.mailersend.com/affiliate/program) and [terms](https://www.mailersend.com/legal/affiliate-program-terms)
- [Windsurf referrals](https://windsurf.com/refer) and [terms](https://windsurf.com/refer/terms-of-service)
- [Civo partners](https://www.civo.com/partners) and [ambassadors](https://www.civo.com/ambassadors); [Qovery partners](https://www.qovery.com/partners)
- [Heroku partnering](https://www.heroku.com/partnering/); [AWS Amplify](https://aws.amazon.com/amplify/); [Portainer partners](https://www.portainer.io/become-a-partner); [Rancher](https://www.rancher.com/)
- [Algolia partner tiers](https://www.algolia.com/partner-program/algolia-partner-program-tiers); [Cloudinary partners](https://cloudinary.com/partners)
- [GitHub Copilot](https://github.com/features/copilot); [JetBrains AI](https://www.jetbrains.com/ai/); [LiteLLM reseller terms](https://www.litellm.ai/reseller-terms)
- Home pages and sitemaps of Continue, Tabnine, Replit, Bolt, StackBlitz, Warp, Zed, Porter, Plunk, Linear, Auth0, Inngest and Trigger.dev
