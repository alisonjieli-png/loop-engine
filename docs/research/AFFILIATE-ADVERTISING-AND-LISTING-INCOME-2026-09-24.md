# Affiliate, advertising and listing income from the public lists

Kind: dated research record, September 24, 2026. The owner asked the same
day: "also in our public lists of tools, saas, websites, etc that compliment
our Baltor system, could we make money via advertising/affiliate? That could
be a good way to increase monetization". This record answers from the
vendors' own pages, the regulators' own texts and the lists as they were
being built that day. Nothing was joined, no account was created, no form was
submitted and no email was sent. The [roadmap](../roadmap/roadmap.yaml)
remains the task authority. The owner's standing authority is in
[AGENTS.md](../../AGENTS.md#commit-push-and-release-authority).

## The answer in short

Yes, with limits. The public lists can carry paid links, a separate band of
ads and a few other offers without changing what they list or in which order.
The money per sale is small, so this is a supplement to Baltor Pro, not a
second business.

- **Most services in the lists today pay nothing.** The pages and sitemaps
  read for Fly.io, Supabase, Stripe, Resend, Cloudflare, Render, Neon and
  Clerk (the starter's defaults and most of its fallbacks) show no affiliate
  or referral programme. None of the eleven hosted model providers in the
  models directory runs a link programme for its model service. The nearest
  are Google's Google Cloud affiliate programme, Anthropic's enterprise
  referral agreement and Cerebras's ambassador credits.
- **The paying programmes sit in web data, automation, monitoring, hosting
  fallbacks, graphics processor rental, newsletters and domains.** Twelve
  rows of the Model Context Protocol directory are published by a vendor with
  an open programme: Apify, Firecrawl, Bright Data, UptimeRobot, Make,
  Railway, Lovable, Hostinger, Axiom, Webflow, Monday.com and Wix (Wix
  publishes no rates). Notion also publishes a row, but its programme is
  closed to new affiliates.
- **Top five to join first, all verified from live vendor pages today:**
  Apify, Firecrawl, Railway, Bright Data and UptimeRobot. Their terms are in
  [Recommended order to join](#recommended-order-to-join).
- **The row design holds, with refinements backed by the rules, chiefly:** label
  commercial links "Paid link", not "Affiliate link"; label paid placements
  "Ad", not "Sponsored"; show one plain sentence above any list that holds a
  paid link; add a relationship kind for Baltor's own services; state how each
  list is ordered; put paid links only on rows the vendor itself publishes.
- **No advertising network now.** EthicalAds asks for 50,000 page views a
  month and, like Carbon Ads, loads a script from another company, which the
  published privacy notice rules out. Ads that Baltor sells and serves itself
  fit the notice.
- **Counting clicks needs no new personal data** if the count is kept per link
  per day with no address, cookie, browser detail or account, and only on
  pages everyone sees. The privacy notice still needs one new row and a short
  section about links to other companies. Both need the owner's approval.
- **What needs the owner:** accepting each programme's terms, tax forms,
  payout accounts and identity checks with the programme or its network,
  approving the disclosure wording and approving the privacy notice change.
  The full list is in [What needs the owner](#what-needs-the-owner).

```text
Income the public lists can carry
├── Paid links: affiliate and referral programmes, each link labelled Paid link
├── Ads: sold by Baltor, served from Baltor, in their own band labelled Ad
├── Template revenue shares: Railway template kickbacks, Vast.ai template links
├── Baltor's own referral offer: Stripe promotion codes at checkout
└── Page sponsorship: a named sponsor on a research page, with no say in it
```

## How this was checked

- **Date.** Every page was read on September 24, 2026 (Coordinated Universal
  Time) unless a row says otherwise.
- **Method.** The session's web search allowance was already spent, so no
  search engine was used. Each vendor's programme page was found through the
  vendor's own sitemap, footer or documentation, then read directly over
  HTTPS. Terms hidden in collapsed questions were read from the page's own
  data.
- **Blocked pages.** Namecheap, Spaceship, GoDaddy and Vultr refused automated
  reads (HTTP 403). For those, the Internet Archive's most recent copy of the
  vendor's own page was read, and the row names the capture date. An archived
  copy is weaker evidence than a live page.
- **Unknown stays unknown.** A cell that says "Not stated" means the pages
  read did not say it. No rate was estimated. Full agreements that sit behind
  a network login (Impact, CJ, PartnerStack) were not read.
- **The lists.** The Model Context Protocol directory, the models directory
  and the stack starter were read from their working trees at about 17:46
  Coordinated Universal Time. They were uncommitted work of other sessions
  and may change before they reach `main`.
- **Storage.** The retrieved pages are third-party text and stay outside the
  repository. This record keeps only addresses, short quotations and facts.

## What the lists contain today

**Model Context Protocol and agent API directory.** 35,279 rows from four
sources, in 26 categories. Every row carries `commercial_relationship` with
kind `none`. The rows whose publisher is the vendor itself, and whose vendor
runs a programme, are:

| Vendor | Row | Programme |
|---|---|---|
| Apify | `com.apify/apify-mcp-server` | Affiliate, FirstPromoter |
| Firecrawl | `io.github.firecrawl/firecrawl-mcp-server` | Affiliate, Dub |
| Bright Data | `io.github.brightdata/brightdata-mcp` | Affiliate, PartnerStack |
| UptimeRobot | `com.uptimerobot/uptimerobot` | Affiliate, direct |
| Make | `com.make/mcp-server` | Affiliate, direct |
| Railway | `com.railway/mcp` | Affiliate and template kickbacks, direct |
| Lovable | `dev.lovable/mcp` | Affiliate, Impact |
| Hostinger | `io.github.hostinger/hostinger-api-mcp` | Affiliate, own platform |
| Axiom | `co.axiom/mcp` | Partner rewards, Dub |
| Webflow | `com.webflow/mcp` | Affiliate, PartnerStack |
| Monday.com | `com.monday/monday.com` | Affiliate, PartnerStack |
| Notion | `com.notion/mcp` | Closed to new affiliates |
| Wix | `com.wix/mcp` | Affiliate, rates not published |

Vendor rows with no programme include `com.supabase/mcp`, `com.neon/mcp`,
`com.stripe/mcp` and `com.cloudflare.mcp/mcp`.

**Models, endpoints and can-I-run directory.** Eleven hosted providers
(OpenAI, Anthropic, Google Gemini API, Mistral AI, Groq, Cerebras, Together
AI, Fireworks AI, DeepInfra, OpenRouter, Ollama Cloud), six local runtimes
(Ollama, LM Studio, llama.cpp server, vLLM, SGLang, MLX LM) and four harnesses
(OpenCode, Pi, Codex, Claude Code). None of the hosted providers runs a link
programme. The only paying neighbours are graphics processor rentals that a
can-I-run answer could suggest when a model does not fit local hardware.

**Stack starter `saas_web_app_starter`.** Defaults: Next.js, Fly.io,
Supabase, Stripe, Resend, Cloudflare DNS and GitHub Actions. Fallbacks:
FastAPI, Render, Railway, Neon with Clerk, Postmark, Paddle, Lemon Squeezy,
the registrar's own DNS and manual deploys. Railway and Postmark are the only
named services with a cash programme; Paddle's referral pays Paddle credit.

## Programme terms from the vendors' pages

Retrieved September 24, 2026 unless the State column says otherwise. "Window"
is the cookie or attribution period.

### Hosting and deployment

| Service | In our lists | Programme and network | What it pays | Window | Payout | Restrictions | Page and sign-up | State |
|---|---|---|---|---|---|---|---|---|
| Railway affiliate | Starter hosting fallback; vendor row | Direct, from the Railway dashboard's referrals page | 15% of the first 12 months of invoices of a new customer; the new customer gets $20 in credits | Not stated | Withdraw to GitHub Sponsors or Buy Me a Coffee | Not stated | [railway.com/affiliate-program](https://railway.com/affiliate-program), [docs](https://docs.railway.com/community/affiliate-program) | Live |
| Railway template kickbacks | Starter could ship as a Railway template | Direct | 15% of the usage cost of users who deploy your template, plus 10% (25% in total) while you answer their questions | For as long as the deployments run (no end stated) | Railway credits by default, or cash through Stripe Connect; minimum $0.01; no cash in some countries such as Brazil, China and Russia | Template published in the marketplace; Railway's terms apply | [docs.railway.com/templates/kickbacks](https://docs.railway.com/templates/kickbacks) | Live |
| DigitalOcean affiliate | Obvious next: hosting and graphics processors | CJ | "10% commission each month, for an entire year" on a new paying user's spend | Not stated | Through CJ; not stated on the page | Not stated; "Anyone can join" | [digitalocean.com/affiliates](https://www.digitalocean.com/affiliates) | Live |
| DigitalOcean referral | Same | In-product | $25 after the referred user reaches $25 in billings | Not applicable | Credit | Not stated | [digitalocean.com/referral-program](https://www.digitalocean.com/referral-program) | Live |
| Vultr referral | Obvious next | In-product | "earn up to $100"; the referred user must be active more than 30 days | Not stated | Issued the business day after the 1st and 15th of each month; form not stated | Not stated | vultr.com/company/referral-program | Archived copy of August 12, 2026; live page refused automated reads |
| Akamai Cloud (Linode) referral | Obvious next | In-product | You: a $25 non-expiring credit after the new user is active 90 days and spends $25; new user: $100 credit for 60 days | Not applicable | Credit only | You must first spend $25 yourself | [techdocs.akamai.com referral program](https://techdocs.akamai.com/cloud-computing/docs/referral-program) | Live |
| Hostinger | Vendor row; sells managed OpenClaw, Hermes Agent, n8n and graphics processor hosting | Own platform | "It starts at 40% and grows depending on sales volume" | Not stated | Not stated | Agreement linked, not read | [hostinger.com/affiliates](https://www.hostinger.com/affiliates) | Live |
| Google Cloud | Obvious next | CJ | "a cash reward for every new eligible user"; amount not published; tiered | Not stated | Through CJ | "No social media or email promotion is permitted"; full terms after acceptance | [cloud.google.com/affiliate-program](https://cloud.google.com/affiliate-program) | Live |

### Identity, email and newsletters

| Service | In our lists | Programme and network | What it pays | Window | Payout | Restrictions | Page and sign-up | State |
|---|---|---|---|---|---|---|---|---|
| Kinde | Obvious next: identity | Direct, from the Kinde account | 20% of subscription fees for 12 months; the new customer gets a $50 credit valid 3 months | Not stated | Bank transfer within 30 days after month end, with a recipient-generated tax invoice; goods and services tax status asked | "Self-referrals are not valid" | [kinde.com/refer](https://www.kinde.com/refer/) | Live |
| Postmark | Starter email fallback | Rewardful | "20% commission of each referred billing, for a period of up to 12 months" (agreement); one sentence of its questions page says two years | 60-day first-party cookie, first touch; the sign-up must pay within 60 days | PayPal, monthly, from 60 days after sign-up; $100 minimum; tax form within 90 days or commissions are forfeited | No paid advertising, search or social pages; no "Postmark" in a domain name; no bulk email; no use of your own link; at first "limited to a select group of partners" | [Postmark programme questions](https://postmarkapp.com/support/article/postmark-affiliate-referral-partner-program-faq), [agreement](https://postmarkapp.com/postmark-affiliate-referral-program-agreement) | Live |
| Brevo | Obvious next | PartnerStack | "a fixed reward"; amount not stated | 90 days | Monthly through PartnerStack | Needs a website with traffic and an email address on that website's domain; no multi-level marketing | [brevo.com/partners/affiliates](https://www.brevo.com/partners/affiliates/) | Live |
| Kit | Obvious next: newsletters | PartnerStack | 50% of the first 12 months; after that 10%, 15% or 20% at 10, 50 or 100 paying referrals a year | Not stated | Not stated | Pay-per-click referrals do not count toward the higher levels | [kit.com/affiliate](https://kit.com/affiliate) | Live |
| beehiiv | Obvious next: newsletters | Dub | 50% after the first conversion, then 55% and 60% by level, for a year; the new customer gets a 14-day trial and 20% off 3 months | 60 days | The 15th of each month, through Dub | "Search ads on Bing or Google, especially on branded terms or domain names, are prohibited"; no sign-up with your own link | [beehiiv.com/partners](https://www.beehiiv.com/partners) | Live |
| Mailgun | Obvious next | A referral form | Not stated | Not stated | Not stated | Not stated | [mailgun.com/email-referrals](https://www.mailgun.com/email-referrals/) | Live, no terms published |

### Domains

| Service | In our lists | Programme and network | What it pays | Window | Payout | Restrictions | Page and sign-up | State |
|---|---|---|---|---|---|---|---|---|
| Name.com | Starter DNS fallback ("your registrar") | Impact | 20% on domain registrations, 30% on WordPress hosting, 50% on yearly web hosting and SSL certificates; new customers only | Not stated | Through Impact | Excludes transfers, premium domains, renewals and upgrades | [name.com/affiliates](https://www.name.com/affiliates) | Live |
| Hover | Same | Impact | 20% per sale, "a one-time payout" | Not stated | "Regularly scheduled payouts" | Not stated | [hover.com/affiliates](https://www.hover.com/affiliates) | Live |
| Spaceship | Same | Impact | From 25% on domain registrations and transfers; from 50% on hosting and email | 30 days | Monthly, $10 minimum | Brand terms as negative keywords in paid search; brand not in ad copy; only the programme's own coupons; no purchases by yourself | spaceship.com/affiliate-program | Archived copy of September 16, 2026 |
| Namecheap | Same | Impact, or CJ | Commission on a new customer's first purchase; rates on a separate page that was not captured | Not captured | Impact: electronic funds transfer or PayPal, $10 minimum. CJ: direct deposit, cheque or Payoneer, $50 (or €25 or £25) minimum | Not captured | namecheap.com/affiliates | Archived copy of September 18, 2026 |
| GoDaddy | Same | CJ | "competitive commission"; rate not stated | Not stated | Through CJ | Not stated | godaddy.com/affiliate-programs | Archived copy of September 21, 2026 |
| Porkbun | Same | Ambassador programme, direct | $0.00 for .com, .dev, .io, .ai, .app, .net and .org; 15% of email and shared hosting | 90 days | PayPal on the 15th, for commissions at least 15 days old | "The affiliate program has been discontinued" | [porkbun.com/affiliate](https://porkbun.com/affiliate) | Live |

### Graphics processor rental

| Service | In our lists | Programme and network | What it pays | Window | Payout | Restrictions | Page and sign-up | State |
|---|---|---|---|---|---|---|---|---|
| RunPod | Can-I-run: rent a graphics processor | Direct | Referral: you and the new user each get a random $5 to $500 credit when they spend $10; 3% of their Pod and 5% of their Serverless spend for 6 months, in credits. Affiliate status after 25 spending referrals: 10% of all spend | Not stated | Credits expire after 90 days; cash only at affiliate status | "Self-referrals and referral manipulation are prohibited" | [runpod.io referral and affiliate program](https://www.runpod.io/referral-and-affiliate-program) | Live |
| Vast.ai | Same | Direct | 3% of a referred client's lifetime spend, as credits; a public template link also carries your referral | Life of the account | Up to 75% can be withdrawn through Stripe Connect, PayPal or Wise, from a dedicated referral account | No paid search, display, video or social ads on Vast.ai brand terms; no ads linking directly to vast.ai; one referral account; effective September 15, 2026 | [docs.vast.ai referral program](https://docs.vast.ai/guides/reference/referral-program) | Live |
| Hyperbolic | Same | Direct | $5 credit to you and $6 to the new user after they verify and top up $5 within 14 days | 14 days | Credit | Not stated | [hyperbolic.ai referral program](https://www.hyperbolic.ai/blog/referral-program) | Live (post of May 2, 2025) |

### Monitoring and observability

| Service | In our lists | Programme and network | What it pays | Window | Payout | Restrictions | Page and sign-up | State |
|---|---|---|---|---|---|---|---|---|
| UptimeRobot | Vendor row | Direct, from the dashboard; "no approval" | "20% LIFETIME (recurring) commission from each full price payment" | 30 days | PayPal, monthly, $100 minimum; may wait until two different users are referred | No coupon sites; no pay-per-click ads with a direct link; no brand names in ads, domains or social profiles; no self-referrals | [uptimerobot.com/affiliate](https://uptimerobot.com/affiliate/) | Live |
| Better Stack | Obvious next | Direct, from the account | 25% of net revenue for the first year | Last referrer wins | PayPal, $100 minimum, after the referred user's 60-day money-back period | "You should not spam" | [betterstack.com/affiliates](https://betterstack.com/affiliates) | Live |
| Axiom | Vendor row | Dub | 5% of eligible revenue for a referred customer's first 12 months | Not stated | Cash by the methods available in your country, or Axiom compute credits | Subject to Axiom approval | [axiom.co/partner-program](https://axiom.co/partner-program) | Live |

### Automation, web data and agent tools

| Service | In our lists | Programme and network | What it pays | Window | Payout | Restrictions | Page and sign-up | State |
|---|---|---|---|---|---|---|---|---|
| Apify | Vendor row; more than 300 rows mention Apify | FirstPromoter | 20% for the first 3 months, then 30%, with no time limit, up to $2,500 per customer (up to $5,000 at 50 or more active customers) | Not stated | PayPal, bank transfer or Wise within the first 15 days of each month; needs three referred customers and $100; or 115% as Apify usage | No Google, Facebook, Instagram, LinkedIn or similar pay-per-click ads | [apify.com/partners/affiliate](https://apify.com/partners/affiliate) | Live |
| Firecrawl | Vendor row | Dub | 25% for 12 months, then 15% while the customer stays subscribed; standard plans only | Not stated | Dub's schedule; bank or PayPal | "Paid search ads aren't allowed under this program, including branded-keyword campaigns"; no self-referrals, bots or unauthorized resellers | [firecrawl.dev/affiliates](https://www.firecrawl.dev/affiliates) | Live; "Tool directories" are invited to apply |
| Bright Data | Vendor row | PartnerStack | 50% revenue share with no time limit; the cap is "up to $1,000 per customer" in the questions and "Up to $2.5K per customer" on the landing page | 90 days | PayPal, Stripe or Bright Data credits (5% more); $25 minimum; usually by the 20th of each month | Not stated on the pages read | [brightdata.com/affiliate](https://brightdata.com/affiliate), [questions](https://brightdata.com/affiliate/faq) | Live; the two caps disagree |
| ScrapingBee | Obvious next | Direct | 25% recurring for the life of the customer, capped at $62.25 a month per customer | Not stated | PayPal, $50 minimum, held 30 days for refunds | "Self referral is forbidden" | [scrapingbee.com/affiliates](https://www.scrapingbee.com/affiliates/) | Live |
| Make | Vendor row | Direct, from the Make profile | 35% for 12 months from the referred user's registration; subscriptions only | Not applicable | Wise only; $100 and three unique paying users before each payout | Not stated on the help page | [help.make.com/affiliate-program](https://help.make.com/affiliate-program) | Live |
| n8n | Obvious next: automation | PartnerStack | 30% of net earnings for 12 months on n8n Cloud | Not stated | PayPal, monthly, €100 minimum | "it is not permitted to run any kind of paid ad campaigns" | [n8n.io/affiliates](https://n8n.io/affiliates/) | Live |

### Developer tools and site builders

| Service | In our lists | Programme and network | What it pays | Window | Payout | Restrictions | Page and sign-up | State |
|---|---|---|---|---|---|---|---|---|
| Lovable | Vendor row | Impact | "up to $100 for each first-time subscriber" | Not stated | Monthly, "low minimum threshold" | Not stated | [lovable.dev/partners/affiliates](https://lovable.dev/partners/affiliates) | Live |
| 1Password | Obvious next | CJ | "$2 for each completed signup and 25% of the first year or month's payment ($2 minimum)" | Not stated | Through CJ | Not stated | [1password.com/affiliate](https://1password.com/affiliate) | Live |
| Webflow | Vendor row | PartnerStack | 50% of a new customer's first subscription for up to 12 months; more on renewals at higher levels | 90 days, first touch | Through PartnerStack | Publish content within 30 days; no coupon or deal sites, sub-affiliate networks or low-traffic sites | [webflow.com/solutions/affiliates](https://webflow.com/solutions/affiliates) | Live |
| Monday.com | Vendor row | PartnerStack | "up to 100% commission on the first year's sales" by level | Not stated | PayPal or Stripe, monthly | Not stated | [monday.com/affiliate-program](https://monday.com/affiliate-program) | Live |
| Notion | Vendor row | PartnerStack | Up to $50 per activated sign-up and 20% of year-one revenue | 180 days, last click | Through PartnerStack | "Program is currently not accepting new affiliates" | [notion.com/affiliates](https://www.notion.com/affiliates) | Live, closed |
| Wix | Vendor row | Not stated | Not stated | Not stated | "recurring payouts" | Not stated | [wix.com/about/affiliates](https://www.wix.com/about/affiliates) | Live, rates not published |
| Vercel v0 ambassadors | Obvious next | Application | $10 per Premium referral and $30 per Team referral, for accepted ambassadors | Not stated | Not stated | Not stated | [Vercel post of July 29, 2025](https://vercel.com/blog/join-the-v0-ambassador-program) | Live |

### Credit-only and non-cash programmes

These reward with the vendor's own credit or free resources, so they only
help if Baltor uses the service itself: Convex (both teams get more free
resources), Paddle ("Refer your community for Paddle credit"), Hyperbolic,
Akamai Cloud and the DigitalOcean referral. Turso's content partners and
Cerebras's ambassadors get promotion, credits or event budgets, not a share
of sales. Doppler's referral programme says "there is no financial or other
compensation". Anthropic's referral partner programme pays a fee from a table
in a signed agreement for introducing an executive buyer, which is enterprise
sales work, not a link.

## Services checked with no programme found

| Service | In our lists | What was found |
|---|---|---|
| Fly.io | Starter default; Baltor's own host | Nothing in the sitemap or on the pricing page |
| Supabase | Starter default; vendor row | Technology and agency partner programme; its master agreement has no referral fee |
| Stripe | Starter default; vendor row | Nothing in the parts of the sitemap read; the matches were careers pages |
| Resend | Starter default | Nothing in the sitemap or on the pricing page |
| Cloudflare | Starter default; vendor row | A partners page for agencies and technology partners |
| Render | Starter fallback | Solution partners only |
| Neon | Starter fallback; vendor row | Partner programme for platforms; the creator programme page now opens the community page |
| Clerk, WorkOS, Stytch | Clerk is a starter fallback | Nothing in the sitemaps |
| Lemon Squeezy | Starter fallback | Not determined: its affiliate terms page was read only in part |
| OpenAI, Google Gemini API, Mistral AI, Groq, Together AI, Fireworks AI, DeepInfra, OpenRouter, Ollama Cloud | Models directory | Nothing found; Fireworks AI and Together AI list technology partners; part of OpenAI's sitemap refused automated reads |
| Hetzner | Obvious next | `hetzner.com/cloud/referral-program` now serves the Cloud product page with no referral terms |
| Modal, Lambda, TensorDock | Obvious next | Nothing found; Lambda lists partners |
| Sentry, PostHog, Langfuse, Checkly | Obvious next | Sentry sponsors open source; PostHog has a register-interest form that names "Affiliate program" as a category |
| Cursor | Obvious next | "Cursor ended the referral program due to increased levels of fraud" |
| Zapier, Pipedream, Activepieces | Obvious next | Nothing found |
| Browserbase, Tavily, Exa | Directory rows | Partner forms and tracks for integrations; Exa names "Revenue Share" for business partners, not a link programme |
| Ghost, Buttondown, Loops, Mailchimp | Obvious next | Nothing found; Buttondown and Ghost write about newsletter sponsorships |
| Tailscale, ngrok, JetBrains | Obvious next | Partnership, reseller or consulting programmes only |
| GitHub | Starter default | Not checked |

## Recommended order to join

The order weighs four things, most important first:

1. **Fit.** A named default or fallback in a starter, or a row the vendor
   publishes itself, ranks above an "obvious next" service that no list
   names yet.
2. **Value per sale,** from the vendor's own figures in
   [Income: formulas and sourced figures](#income-formulas-and-sourced-figures).
3. **Friction.** Approval, payout thresholds, closed or limited programmes,
   and rules Baltor could break by accident.
4. **Cash.** Cash ranks above credit that Baltor would not use.

| Order | Programme | Why here |
|---|---|---|
| 1 | Apify | Vendor row in the directory's web data category, and more than 300 rows mention Apify. No time limit and a cap of $2,500 per customer. Review in about three business days |
| 2 | Firecrawl | Vendor row. The page invites "Tool directories". 25% for a year, then 15% for as long as the customer pays |
| 3 | Railway | The only paying service the starter names, plus a vendor row. No approval step. Template kickbacks pay a share of usage for as long as a starter deployed from a Baltor template runs |
| 4 | Bright Data | Vendor row. 50% revenue share, a 90-day window and a $25 minimum. The cap must be read from the agreement at sign-up because the two pages disagree |
| 5 | UptimeRobot | Vendor row. 20% for the life of the subscription, no approval, and a sourced example of $5.60 a month per $28 plan |
| 6 | Make | Vendor row. 35% for 12 months; payouts need $100 and three paying users, by Wise only |
| 7 | n8n | Automation, an obvious next row. 30% for 12 months, €100 minimum |
| 8 | Better Stack and Kinde | Monitoring and identity, obvious next. 25% of net revenue and 20% of fees for a year, paid in cash |
| 9 | DigitalOcean | Hosting and graphics processors, obvious next. 10% of spend for a year, through CJ |
| 10 | Vast.ai and RunPod | Can-I-run rentals. Vast.ai lets up to 75% of its 3% credit be cashed out; RunPod pays credits until 25 spending referrals |
| 11 | Kit and beehiiv | Only when Baltor lists newsletter tools. The highest value per sale in this record |
| 12 | Postmark | The starter's email fallback, but the programme is limited to a small group of partners and bans paid search and social promotion |
| 13 | Hostinger, Lovable, Axiom, Webflow, Monday.com | Vendor rows with lower fit or unknown prices |
| 14 | Name.com, Spaceship, Hover, Namecheap | Only if a starter adds a domain step; a new .com at Name.com earns about $2.60 |

Not recommended now: Notion (closed), Porkbun (pays nothing on common
extensions), Google Cloud (bans social and email promotion and publishes no
amount), Brevo and Wix (amounts not published) and every credit-only
programme for a service Baltor does not use.

### The top five, with the terms verified today

1. **Apify** ([page](https://apify.com/partners/affiliate)). FirstPromoter at
   `affiliate.apify.com`. 20% for the first three months, then 30%, "No time
   limits on commissions", up to $2,500 per customer while Baltor has fewer
   than 50 active referred customers. Paid by PayPal, bank transfer or Wise in
   the first 15 days of each month once there are three referred customers
   and $100. Pay-per-click advertising is banned.
2. **Firecrawl** ([page](https://www.firecrawl.dev/affiliates)). Dub at
   `partners.dub.co/firecrawl`. 25% of every payment for 12 months, then 15%
   for as long as the customer stays subscribed. Scale and Enterprise
   contracts pay nothing. Paid search, including brand keywords, is banned.
3. **Railway** ([affiliate](https://docs.railway.com/community/affiliate-program),
   [kickbacks](https://docs.railway.com/templates/kickbacks)). 15% of the
   first 12 months of a new customer's invoices, withdrawn to GitHub Sponsors
   or Buy Me a Coffee. Separately, 15% of the usage of deployments made from a
   published template, plus 10% while answering users' questions, as credits
   or as cash through Stripe Connect.
4. **Bright Data** ([page](https://brightdata.com/affiliate),
   [questions](https://brightdata.com/affiliate/faq)). PartnerStack. 50%
   revenue share for as long as the customer is active, capped per customer
   at $1,000 or $2,500 (the pages disagree). 90-day cookie. PayPal, Stripe or
   credits with a 5% bonus; $25 minimum.
5. **UptimeRobot** ([page](https://uptimerobot.com/affiliate/)). In the
   dashboard with no approval. 20% of every full-price payment for the life
   of the subscription. 30-day cookie. PayPal once a month from $100. Coupon
   sites, pay-per-click ads that link to UptimeRobot, brand names in ads and
   self-referrals are banned.

## Developer advertising networks

| Network | Privacy | Traffic floor | Share and pay | Content and placement rules | Page |
|---|---|---|---|---|---|
| EthicalAds (Read the Docs) | "No tracking"; targeting by page content and geography; visitor network addresses used in real time for geography and fraud checks, logs with addresses and browser details deleted after 10 days; no behavioural targeting | "at least 50,000 pageviews per month", with occasional exceptions | "70% revenue share"; "around $2.50 per 1,000 pageviews" for mostly European and North American traffic; paid monthly by the 15th, $50 minimum; PayPal, Open Collective, GitHub Sponsors or bank transfer through Stripe | The only ad on the page; above the fold; not inside the main content; at least 0.1% click-through rate | [publishers](https://www.ethicalads.io/publishers/), [policy](https://www.ethicalads.io/publisher-policy/), [privacy](https://www.ethicalads.io/privacy-policy/) |
| Carbon Ads (BuySellAds) | "contextual and cookieless"; "We use pixels, not cookies" for premium campaigns | Not published; "by invitation only" and judged on monthly page views | Share not published; a typical range of $1.20 to $2.30 per 1,000 impressions; earnings deposited within 30 days and withdrawable within 60; PayPal $20, cheque $50, wire $500 plus a $35 fee | "Carbon is an exclusive network"; no other ad networks on pages where Carbon appears (in-house promotions limited to logos or text links); "Don't modify or self-host the script"; above the fold; target click-through rate 0.07% | [questions](https://www.carbonads.net/faq), [placement policy](https://www.carbonads.net/placement-policy), [BuySellAds](https://www.buysellads.com/publishers) |

Both networks load a script from their own servers into the page. The
published [privacy notice](../legal/PRIVACY-NOTICE.md) says "It runs no
analytics, advertising or tracking scripts. Every script on the site is
served from the site itself." Either network would break that sentence, and
changing it is the owner's decision. Carbon's exclusivity would also block
the ads that Baltor sells itself. BuySellAds mentions an API integration, but
its terms were not read.

## Rules that apply

This section is an engineering reading of the texts, not legal advice.

### United States: Federal Trade Commission

- **The Endorsement Guides** (16 CFR Part 255, revised by 88 FR 48102 of
  July 26, 2023). Section 255.5(a): "When there exists a connection between
  the endorser and the seller of the advertised product that might materially
  affect the weight or credibility of the endorsement, and that connection is
  not reasonably expected by the audience, such connection must be disclosed
  clearly and conspicuously." Example 11 is a review blog with affiliate
  links; "the reviews should clearly and conspicuously disclose the
  compensation". Section 255.0(f) defines clear and conspicuous as "difficult
  to miss (i.e., easily noticeable) and easily understandable by ordinary
  consumers", and on the internet "the disclosure should be unavoidable".
  Example 9 of 255.5 says that when an advertiser rewards people for posting
  about it, "the advertiser should take steps to ensure that these
  disclosures are being provided".
- **The Endorsement Guides questions page.** "Consumers might not understand
  that 'affiliate link' means that the person placing the link is getting
  paid for purchases made through the link." And: "'Paid link' right next to
  an affiliate link should be an adequate disclosure of the nature of the
  link." "Commissionable link" is "probably not a clear disclosure". A single
  disclosure on the home page "won't be sufficient", and a button labelled
  DISCLOSURE that links to a full disclosure is "easily avoidable". Links
  that earn nothing need no disclosure.
- **.com Disclosures** (March 2013): "Place the disclosure as close as
  possible to the triggering claim", and design pages so that scrolling is
  not needed to find it.
- **Native Advertising: A Guide for Businesses** (December 2015): "Terms
  likely to be understood include 'Ad,' 'Advertisement,' 'Paid
  Advertisement,' 'Sponsored Advertising Content,' or some variation
  thereof." Consumers may read "Sponsored by [X]" to mean that an advertiser
  "funded or 'underwrote' but did not create or influence the content".
- **Rule on consumer reviews and testimonials** (16 CFR 465.6): a business
  may not misrepresent that a website it controls "provides independent
  reviews or opinions ... about a category of businesses, products, or
  services including the business or one or more of the products or services
  it sells". Baltor's lists include categories where Baltor sells a service,
  so Baltor's own rows must be marked.

### United Kingdom

- **The Committee of Advertising Practice code** (the United Kingdom
  advertising code), rules 2.1 ("Marketing communications must be obviously
  identifiable as such"), 2.3 and 2.4. Rules 2.3 and 2.4 now reflect Schedule
  20 of the Digital Markets, Competition and Consumers Act 2024, whose
  paragraph 12 bans paid editorial promotion "without making that clear" and
  has been in force since April 6, 2025.
- **The Advertising Standards Authority's advice on affiliate marketing.**
  The Committee of Advertising Practice code applies to affiliate
  content, and "Both the business and the affiliate marketer are
  responsible". Where only some links are affiliate links, the content about
  those products "(and the links themselves) should be identifiable as
  advertising". Placing an identifier such as "(Ad)" before that content "is
  likely to be acceptable", and so is a statement at the beginning that
  explains which marker means advertising. A disclaimer at the bottom "is
  unlikely to be sufficient", and a "generic and ambiguous disclaimer which
  indicates that the author 'may' receive a commission is unlikely to be
  acceptable".

### European Union

- **Unfair Commercial Practices Directive,** Annex I point 11 (paid
  editorial content "without making that clear") and point 11a, added by
  Directive (EU) 2019/2161: "Providing search results in response to a
  consumer's online search query without clearly disclosing any paid
  advertisement or payment specifically for achieving higher ranking of
  products within the search results."
- **The same directive, Article 7(4a):** when consumers can search products
  "offered by different traders", general information on "the main
  parameters determining the ranking" and "the relative importance of those
  parameters" must be available "in a specific section of the online
  interface that is directly and easily accessible from the page where the
  query results are presented".
- **Electronic Commerce Directive, Article 6:** a commercial communication
  "shall be clearly identifiable as such", "the natural or legal person on
  whose behalf the commercial communication is made shall be clearly
  identifiable", and promotional offers such as discounts "shall be clearly
  identifiable as such, and the conditions which are to be met to qualify for
  them shall be easily accessible". The last part applies to Baltor's own
  referral discount.

### Google Search

- "Mark links that are advertisements or paid placements (commonly called
  paid links) with the sponsored value." `nofollow` "is still an acceptable
  way to flag them, though sponsored is preferred" (page updated December
  10, 2025).
- **Thin affiliation** (spam policies, updated August 28, 2026): pages whose
  affiliate product descriptions "are copied directly from the original
  merchant without any original content or added value". "Good affiliate
  sites add value by offering meaningful content or features", such as
  "navigation of products or categories, and product comparisons".
- **Link spam** includes "Text advertisements or text links that don't block
  ranking credit". Two Model Context Protocol directories sell exactly that:
  MCP.so advertises "dofollow placement" and mcpservers.org sells a $39
  "Premium Submit" with "priority in search results" and a "Dofollow link".
  Baltor will sell neither.

## The design, verified and refined

| Element of the decided design | Verdict | Evidence | Change |
|---|---|---|---|
| A typed `commercial_relationship` object kept apart from editorial fields | Keep | Section 255.5 needs the connection disclosed; a separate field makes "ranking never reads it" checkable | None |
| Kinds `none`, `affiliate`, `referral`, `sponsored` | Refine | 16 CFR 465.6 and the business-relationship wording of 255.5(a) | Add kind `owned` for Baltor's own services, labelled "Baltor's own service"; ranking never reads it either |
| Visible label "Affiliate link" beside the link | Reverse the wording | The questions page says "affiliate link" alone may not be understood and "Paid link" is adequate | Label every affiliate and referral link "Paid link", including credit-only referral links |
| Label "Sponsored" on paid placements | Reverse the wording | The native advertising guide prefers "Ad"; the Advertising Standards Authority's examples use "Ad" | Label each placement "Ad"; head the band "Ads" |
| `rel="sponsored noopener"` | Keep | Google prefers `sponsored` for paid links | If the counter below is built, also disallow `/out/` in `robots.txt` |
| A disclosure section on the page | Keep, but not alone | The questions page: a single home-page disclosure is not enough and a DISCLOSURE link is avoidable; the Advertising Standards Authority: a bottom disclaimer is unlikely to be enough | Add one visible sentence directly above any list or starter section that shows an active paid link |
| Sponsored placements only in their own labelled band | Keep | Point 11a of Annex I; the native advertising guide | At most three ads a page, each naming the advertiser, never inside search results or a ranked list |
| Ranking, order, filtering and inclusion never read commercial fields, with a mutant check | Keep and extend | Point 11a; Article 7(4a) | Extend the check: a paid link never replaces a row's own links; the page never rewrites `outbound_link` per visitor; the list-top sentence appears exactly when a paid link is active |
| Every row ships `none` until the owner joins | Keep | Joining is a legal commitment | None |
| The directory's paid-links text says the order uses "only the listing facts shown on this page" | Refine | Article 7(4a) asks for the main parameters and their relative importance | State the default order in words: more sources first, then publisher listings before community ones, then listings with a description, then by name |
| Link text "Go to the product" | Refine | Clear commercial intent (rule 2.3 of the Committee of Advertising Practice code) | Name the destination, for example "Sign up at Apify", and show the plain address beside it |
| Where paid links may appear | New rule | Thin affiliation; the honesty of a row that sends a reader to a sign-up page | Only on rows whose publisher is the vendor, and in human-facing starter notes; never in agent instructions, skills or scripts, where a harness could follow a link without a person seeing the label |

## Click counting and the privacy notice

**What the notice promises today** (identical on the live
<https://baltor.ai/privacy> page and in
[PRIVACY-NOTICE.md](../legal/PRIVACY-NOTICE.md), compared on September 24):
"It sets no cookies and uses no browser storage for your sign-in", "It runs
no analytics, advertising or tracking scripts. Every script on the site is
served from the site itself.", "It keeps no log of requests that succeed" and
"It does not sell or share your data." Its table lists everything the service
stores.

**The counter engineering proposes.**

- Every outbound link in the public lists points to
  `/out/{list}/{row}` on baltor.ai. The server answers with a redirect to the
  address in the published list: the reviewed `outbound_link` when the
  relationship is active, otherwise the row's plain address. An unknown row
  gets "not found", so the path can never redirect to an address the list
  does not hold.
- The handler reads only the path. It adds one to a count kept per list, row
  and day in Coordinated Universal Time, in memory, and writes the counts to
  the service database every few minutes. It never reads or keeps the network
  address, browser details, the referring page, a cookie or an account.
- The server that sends each list page adds one to a count of views per list
  per day under the same rules, because the advertising networks' floors and
  any advertiser's price depend on page views.
- The response carries `Cache-Control: no-store` and `X-Robots-Tag: noindex`,
  and `robots.txt` disallows `/out/`.
- Links on pages that only one signed-in account can see are never counted.
- Daily rows are kept 400 days and then folded into monthly totals.
- The page still shows each row's plain address as text, so a reader sees
  where a link goes before following it.

**Does "no new personal data" hold?** Yes, for Baltor's own count, under the
conditions above. Recital 26 of the General Data Protection Regulation says
"The principles of data protection should therefore not apply to anonymous
information, namely information which does not relate to an identified or
identifiable natural person". A count per link per day that never saw an address, a cookie or an
account cannot be tied to a person by any means Baltor holds. Nothing is
stored on or read from the visitor's device. The United Kingdom's rule on
device storage and access (regulation 6 of the Privacy and Electronic
Communications Regulations, as replaced on February 5, 2026) now also covers
"collecting or monitoring information automatically emitted by the terminal
equipment", and its statistics exception excludes that kind of collection.
That is why the handler must not read browser details or the address, not
even to filter bots.

It stops holding in three cases:

1. A count taken on a page that only one account can see identifies what
   that account did.
2. A link that carries a visitor, session or account identifier in its sub-ID
   would pass personal data to the programme. Outbound links are fixed
   strings from the reviewed record and carry only Baltor's own partner code
   and, at most, the list and row.
3. The visit itself is not Baltor's to control. When a person follows any
   link, the company they visit, and for a paid link its affiliate network,
   receives the visit and may set its own cookies under its own notice. This
   is not new data that Baltor stores, but the notice should say so.

**What the notice needs** (drafts in
[Drafts for the owner's approval](#drafts-for-the-owners-approval)): one new
table row for the counts, and a short section about links to other
companies. The sentence "It keeps no log of requests that succeed" stays
true, because a daily total is not a log of requests. The counter ships only
after the owner approves the change. Until then, clicks and sales come from
each programme's own dashboard.

## Income: formulas and sourced figures

No traffic figure is assumed. The formulas take measured inputs.

```text
Monthly income from paid links = sum over programmes p of
    follows(p) x paid_conversion_rate(p) x value_per_paying_customer(p)

follows(p)                 measured by the counter, or by the programme dashboard
paid_conversion_rate(p)    measured by the programme dashboard after 30 days
value_per_paying_customer  from the vendor's own terms and prices, below

Paying customers per year that equal one Baltor Pro year ($29 x 12 = $348)
    = 348 / first-year value per paying customer
```

| Programme | First-year value per paying customer (sourced figures) | Customers per Baltor Pro year |
|---|---|---|
| Railway affiliate, Hobby at its $5 minimum | 15% x $5 x 12 = $9 | about 39 |
| Railway affiliate, Pro at its $20 minimum | 15% x $20 x 12 = $36 | about 10 |
| Railway template kickback | 15% (25% with the support bonus) of the template's usage cost; Railway's example: $200 of usage pays up to $50 | Depends on usage |
| Apify, Starter at $19 a month | 20% x $19 x 3 + 30% x $19 x 9 = $62.70, and 30% after that up to the cap | about 6 |
| Firecrawl, Hobby at $16 a month billed yearly | 25% x $192 = $48, then 15% a year | about 7 |
| UptimeRobot, its own $28 a month example | 20% x $28 x 12 = $67.20, every year while subscribed | about 5 |
| Better Stack, its own $100 a month example | $300 in the first year | about 1.2 |
| ScrapingBee, Freelance at $49 a month | 25% x $49 x 12 = $147, every year | about 2.4 |
| Postmark, Basic at $15 a month | 20% x $15 x 12 = $36 | about 10 |
| n8n, Starter at €20 a month billed yearly | 30% x €240 = €72, less tax differences | Not converted |
| Kit, Creator at $390 billed yearly | 50% x $390 = $195 | about 1.8 |
| beehiiv, Scale at $517 billed yearly | 50% x $517 = $258.50 at the first level | about 1.3 |
| Vast.ai, its own example | $30 of credit per $1,000 of lifetime spend | Credit, not cash |
| Name.com, a new .com at the $12.99 shown on the page | 20% x $12.99 = $2.60 | about 134 |
| Lovable | Up to $100 per first-time subscriber | at least 3.5 |
| DigitalOcean, Kinde, Make, Axiom, Webflow, Monday.com, Bright Data | Rate known, price not read; value = rate x the customer's spend over the paid period | Unknown |

**Advertising unit rates,** as the networks state them: EthicalAds about $2.50
per 1,000 page views for mostly European and North American traffic, which is
$125 a month at its 50,000 page view floor; Carbon Ads $1.20 to $2.30 per
1,000 impressions. Ads that Baltor sells itself have no published rate yet;
the only market figures read today are MCP.so's asking prices of $399, $699
and $1,299 a month, and nothing shows how many of them sell.

**What stays unknown until measured:** traffic to each list, the share of
visitors who follow a link, the share of those who pay, the plans they
choose, whether each programme accepts Baltor, and the full agreements
behind network logins. The counters measure the first two, the programme
dashboards the next two, and joining settles the last two. After 30 days the
order to join is recomputed from measured follows times the values above.

## Other income from the public lists

### Free vendor-claimed listings

The cheapest claim path already exists. A vendor that publishes or corrects
its entry in the official Model Context Protocol registry, which verifies the
publisher's domain or GitHub account, is read by the directory every day. For
rows from other sources, a claim is a DNS TXT record or a file at a fixed
path on the vendor's domain. The vendor supplies facts and evidence, and
Baltor writes the row. Claims stay free forever, because a verified publisher
already sorts before a community listing in the default order: a paid claim
would be paid ranking. Writing the row ourselves also keeps editorial control
and means Baltor does not publish text written by vendors.

### Labelled paid placements

Ads are sold directly, at a flat monthly price, for the "Ads" band only. The
image and text are served from baltor.ai, with no script and no tracking
pixel from the advertiser, and the link carries `rel="sponsored noopener"`.
Each ad names the advertiser and is labelled "Ad". An ad never changes a
row's place, never appears inside search results and never passes ranking
credit. Selling starts only after 30 days of measured traffic, with advertiser
terms and prices that the owner approves. Impression and follow counts for an
advertiser come from the same kind of daily count as above.

### Baltor's own referral offer through Stripe promotion codes

Baltor's existing checkout already has an `allow_promotion_codes` setting.
Stripe's own documentation confirms that a promotion code wraps a coupon and
can be limited to "a specific customer, redemption limit, and expiration
date", to first-time customers and to a minimum amount, and that a customer
balance credit "can only reduce the amount due on the next invoice".

- Each Baltor Pro customer gets one personal promotion code, restricted to
  first-time customers, with the referrer's Baltor account identifier in the
  code's metadata and no email address.
- The new customer pays half of the first month ($14.50 off).
- After the new customer's second paid invoice, the referrer receives one
  month ($29) as a customer balance credit, at most 12 a year.
- No credit is given when the new customer pays with the referrer's payment
  method or is the referrer's own account, and each new customer earns the
  referrer at most one credit.
- Referrers are told, in the offer's terms, to say that they receive a credit
  when they share a code, and Baltor checks public posts it finds (Example 9
  of 255.5). The conditions are published on a page that checkout links to
  (Electronic Commerce Directive, Article 6).
- This uses Stripe discounts, not Baltor's own promotion code grants, which
  give access without payment and would be a second way in.

One referred customer who pays twice costs Baltor $43.50, a month and a half
of Baltor Pro. The referrer's credit waits for a second paid month because
fraud is the known failure: Cursor "ended the referral program due to
increased levels of fraud". Comparable double-sided offers read today: Railway
gives a new customer $20 in credits, Kinde $50 and beehiiv 20% off three
months.

### Sponsorship of the blog or research pages

One sponsor per page, shown at the top as "Sponsored by X. X paid for this
sponsorship and did not write, review or change this page." That wording
matches what the native advertising guide says readers take from "Sponsored
by". The sponsor's link carries `rel="sponsored noopener"`, and the page's
content is written and published as it would be without a sponsor.

### Template revenue shares

Railway pays 15% of the usage of deployments made from a published template,
and a Vast.ai template link carries the referral. A Baltor starter published
as a Railway template would earn from its own users' usage. The starter's
hosting note must then say so beside the link, and Fly.io stays the default
for the editorial reason the starter records.

## Drafts for the owner's approval

Not for publication until the owner approves them.

**Label beside each affiliate or referral link:** `Paid link`

**Sentence directly above a list or starter section that shows an active paid
link:**

> Links marked Paid link are ads: Baltor earns money when you sign up or buy
> through them. They do not change which services we list or their order.

**Heading and label for the band of paid placements:** heading `Ads`, each
item labelled `Ad`.

**Short affiliate disclosure** (for the `#paid-links` section):

> Some links on this page are paid links. When you sign up or buy through a
> link marked Paid link, the company pays Baltor, and it does not raise the
> price you pay. We add a paid link only to a service that is already on the
> list for its own reasons, and the service's plain address is shown beside
> it. Paid links, ads and payments never decide which services we list or
> their order.

**Editorial independence statement:**

> Baltor decides what goes on these lists and how they are ordered. The
> order uses only the facts shown on each page, and a starter's
> recommendations follow the reasons written in its notes. No company can pay
> for a place on a list, a better position, a badge or a review. A company can correct facts
> about its own listing, and we check them before we change anything; we
> write every listing ourselves. Ads appear only in the band marked Ads, apart
> from the lists. Where Baltor sells a service of its own, that listing is
> marked "Baltor's own service". If you think a listing is wrong, tell us in
> the public issue tracker of the repository.

**Privacy notice, new row in "What the service stores":**

| Data | Why | Where |
|---|---|---|
| How many times each list page was viewed, each link in the public lists was followed and each ad was shown, per day, with no network address, browser detail, cookie or account | To learn which listed services people want, to check the reports of the affiliate programmes Baltor belongs to and to report to advertisers | The service database |

**Privacy notice, new section "Links to other companies":**

> The public lists link to other companies. Some links are paid links, marked
> Paid link: Baltor earns money when you sign up or buy through them. When you
> follow any link you leave Baltor. The company you visit, and for a paid link
> its affiliate network, can see your visit and may set its own cookies under
> its own privacy notice. Baltor does not send them your email address, your
> account or your network address, and a link carries only Baltor's own
> partner code.

## Engineering decisions and reasons

1. **Keep the typed design and refine it before its first release.** Labels
   become "Paid link" and "Ad", kind `owned` is added, and link text names
   the destination. Reason: the Federal Trade Commission's own examples and
   the Advertising Standards Authority's advice, quoted above. The
   `commercial_relationship` reader is not on `main` yet, so version 1 can
   change without a new record version; if version 1 has shipped by then, the
   new labels need version 2.
2. **Paid links only on rows the vendor publishes, and in human-facing
   starter notes.** Never in agent instructions, skills or scripts, and never
   in place of a row's own links. Reason: a harness can open a link without a
   person seeing its label, and a paid link on a third-party row would send a
   reader somewhere other than the thing listed.
3. **One disclosure sentence above any list that shows a paid link,** kept
   together with the per-link label and the section. Reason: proximity is the
   Federal Trade Commission's test, and the Advertising Standards Authority
   accepts a statement at the beginning that explains the marker.
4. **State how each list is ordered,** in words, where the results are shown.
   Reason: Article 7(4a) of the Unfair Commercial Practices Directive.
5. **No advertising network now.** Reason: EthicalAds needs 50,000 page views
   a month; both networks load another company's script, which the published
   privacy notice rules out; Carbon's exclusivity would block Baltor's own
   ads. Revisit when measured traffic passes 50,000 page views a month, and
   only with an approved privacy notice change.
6. **Sell ads directly, served by Baltor, in the Ads band only,** after 30
   days of measured traffic. Reason: it keeps the "every script is served
   from the site itself" promise and never sells ranking or ranking credit.
7. **Measure follows with the first-party counter described above,** only
   after the owner approves the notice change. Reason: the order to join
   should come from measured demand, and the counter needs no new personal
   data.
8. **Join programmes in the order given above,** and recompute the order
   after 30 days of counts.
9. **Standing rules for every programme:** never use Baltor's own links for
   Baltor's own accounts, never buy search ads on a partner's brand, never
   present Baltor as a coupon or deal site, never put a visitor, session or
   account identifier in a link, and switch a paid link on only after
   checking that it does not raise the price a visitor pays. Reason: these
   are the rules the programmes read today forbid most often (UptimeRobot,
   Firecrawl, Apify, Spaceship, Vast.ai, beehiiv, Postmark, n8n), and the
   disclosure promises the price.
10. **Watch the terms of every joined programme.** Add each terms page to
    `tools/research_source_watch.json`, which the daily research watch reads.
    Reason: terms moved often in what was read today (Vast.ai changed its
    rules on September 15, 2026; Cursor and Porkbun ended programmes; Notion
    closed its programme; Neon's creator programme page is gone).
11. **Baltor's referral offer uses Stripe promotion codes** with the terms in
    the section above. Reason: it stays inside the one sign-up and payment
    path, and waiting for a second paid month is the defence against the
    fraud that ended Cursor's programme.
12. **Vendor claims stay free, and Baltor writes every row.** Reason: a
    verified publisher already sorts first, so a paid claim would be paid
    ranking.

## What needs the owner

1. **Accept each programme's terms.** This is a legal commitment. In order:
   Apify (FirstPromoter), Firecrawl (Dub), Railway (affiliate, and later
   template kickbacks), Bright Data (PartnerStack), UptimeRobot, then Make,
   n8n, Better Stack, Kinde and DigitalOcean (CJ). Each page is linked in the
   tables above.
2. **Tax details.** Each programme or network asks for a tax form, such as a
   Form W-9 for a United States business. Postmark forfeits commissions if
   the form is not filed within 90 days; Kinde asks for goods and services
   tax status.
3. **Payout accounts and identity checks,** which only the owner can pass:
   PayPal (UptimeRobot, Better Stack, n8n, ScrapingBee, Postmark), Wise (Make,
   and optionally Apify), Stripe Connect or Stripe Express (Railway cash
   kickbacks, and Dub for Firecrawl, Axiom and beehiiv), GitHub Sponsors or Buy
   Me a Coffee (Railway affiliate withdrawals), and the network accounts
   (PartnerStack, FirstPromoter, CJ, Impact).
4. **A role mailbox on the baltor.ai domain** for programme accounts. Brevo,
   for example, refuses public email domains. No personal address goes into
   the repository.
5. **Approve the disclosure wording:** the label, the list-top sentence, the
   Ads band, the short disclosure and the editorial independence statement
   above.
6. **Approve the privacy notice change** (the new row and the new section)
   before the counter or any ad ships.
7. **Approve the referral offer's terms** before it is switched on. It adds a
   section to the terms of service and a privacy notice row for the record
   that links a referrer to a new customer.
8. **Approve advertiser terms and prices** before any ad or page sponsorship
   is sold.

Nothing here needs spending, and every other choice is an engineering
decision recorded above.

## Sources

All retrieved September 24, 2026, unless noted.

Rules and guidance:

- [Endorsement Guides, 16 CFR Part 255](https://www.law.cornell.edu/cfr/text/16/part-255), with [255.0](https://www.law.cornell.edu/cfr/text/16/255.0) and [255.5](https://www.law.cornell.edu/cfr/text/16/255.5)
- [FTC's Endorsement Guides: What People Are Asking](https://www.ftc.gov/business-guidance/resources/ftcs-endorsement-guides-what-people-are-asking)
- [.com Disclosures, March 2013](https://www.ftc.gov/business-guidance/resources/com-disclosures-how-make-effective-disclosures-digital-advertising)
- [Native Advertising: A Guide for Businesses, December 2015](https://www.ftc.gov/business-guidance/resources/native-advertising-guide-businesses)
- [16 CFR 465.6](https://www.law.cornell.edu/cfr/text/16/465.6)
- [Committee of Advertising Practice code, section 2](https://www.asa.org.uk/type/non_broadcast/code_section/02.html) and [Advertising Standards Authority advice on affiliate marketing](https://www.asa.org.uk/advice-online/affiliate-marketing.html)
- [Digital Markets, Competition and Consumers Act 2024, Schedule 20](https://www.legislation.gov.uk/ukpga/2024/13/schedule/20)
- [Directive (EU) 2019/2161, Article 3](https://www.legislation.gov.uk/eudr/2019/2161/article/3) and [Directive 2005/29/EC, Annex I](https://www.legislation.gov.uk/eudr/2005/29/annex/I)
- [Directive 2000/31/EC as adopted](https://www.legislation.gov.uk/eudr/2000/31/contents)
- [General Data Protection Regulation, recitals](https://www.legislation.gov.uk/eur/2016/679/introduction)
- [Privacy and Electronic Communications Regulations, regulation 6](https://www.legislation.gov.uk/uksi/2003/2426/regulation/6) and [Schedule A1](https://www.legislation.gov.uk/uksi/2003/2426/schedule/A1)
- [Google: qualify outbound links](https://developers.google.com/search/docs/crawling-indexing/qualify-outbound-links), [spam policies](https://developers.google.com/search/docs/essentials/spam-policies), [high quality reviews](https://developers.google.com/search/docs/specialty/ecommerce/write-high-quality-reviews)
- [Stripe coupons and promotion codes](https://docs.stripe.com/billing/subscriptions/coupons), [promotion code API](https://docs.stripe.com/api/promotion_codes/create), [customer balance](https://docs.stripe.com/billing/customer/balance), [Checkout discounts](https://docs.stripe.com/payments/checkout/discounts)

Advertising and listing prices:

- [EthicalAds publishers](https://www.ethicalads.io/publishers/), [questions](https://www.ethicalads.io/publishers/faq/), [policy](https://www.ethicalads.io/publisher-policy/), [privacy](https://www.ethicalads.io/privacy-policy/)
- [Carbon Ads questions](https://www.carbonads.net/faq), [placement policy](https://www.carbonads.net/placement-policy), [join](https://www.carbonads.net/join), [BuySellAds publishers](https://www.buysellads.com/publishers)
- [MCP.so advertise](https://mcp.so/advertise), [mcpservers.org submit](https://mcpservers.org/submit)

Programme pages: linked in each table row. Pricing pages used for values:
[Railway](https://railway.com/pricing), [Apify](https://apify.com/pricing),
[Firecrawl](https://www.firecrawl.dev/pricing),
[Postmark](https://postmarkapp.com/pricing), [Kit](https://kit.com/pricing),
[beehiiv](https://www.beehiiv.com/pricing), [n8n](https://n8n.io/pricing/).
Programme networks: [Dub payouts](https://dub.co/help/article/receiving-payouts)
(bank payouts through Stripe Express with no fee, or USDC with a 0.5% fee;
automatic above $10).

Archived copies from the Internet Archive, because the live pages refused
automated reads: Namecheap affiliates (captured September 18, 2026),
GoDaddy affiliate programs (September 21, 2026), Spaceship affiliate program
(September 16, 2026) and Vultr referral program (August 12, 2026).

Related records: [business paths](BUSINESS-PATHS-2026-09-18.md) and
[competitive landscape and monetization](COMPETITIVE-LANDSCAPE-AND-MONETIZATION-2026-09-18.md).
