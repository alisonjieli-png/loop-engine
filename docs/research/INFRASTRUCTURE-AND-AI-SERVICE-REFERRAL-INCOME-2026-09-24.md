# Referral income from infrastructure and AI services

Kind: dated research record, September 24, 2026, evening. It extends the
[first record of the same day](AFFILIATE-ADVERTISING-AND-LISTING-INCOME-2026-09-24.md),
whose text stays as it was. Later that day the owner narrowed the question,
in their words: "I wanted you to research SaaS services, hosting, like
Ollama, Fly.io, MCP services, mailgun, hosting, sending, and other
infrastructure and model serving and LLM as a service affilaite systems that
we can make money on. We don't want to pay for downloads or pay our own
affiliates." Nothing was joined, no account was created, no form was
submitted and no email was sent. The [roadmap](../roadmap/roadmap.yaml)
remains the task authority.

## What changed since the first record

- **Scope.** Only money that Baltor earns when it refers its users to an
  infrastructure or AI service. Anything where Baltor pays others is out: no
  cash affiliate programme of Baltor's own and no payment for downloads.
- **Withdrawn from the first record.** Its design for Baltor's own referral
  offer (half off the first month, and a $29 credit to the referrer) is
  withdrawn. The free-month referral that the owner approved is separate and
  stands; its terms are recorded by the main session, not here. Ads and page
  sponsorships were not part of the narrowed question, so the first record's
  sections on them stay as reference only and nothing more is proposed.
- **Owner decisions since then** ([AGENTS.md](../../AGENTS.md#commit-push-and-release-authority)
  as of `7c6a626b`). The owner approved the privacy notice changes drafted
  that day, including aggregate link counting, in their words "I approve the
  privacy notice". The owner then authorized engineering "to implement and
  deploy all" of the owner action items, naming among them the paid link
  wording and the partner mailbox. What stays with the owner is "their own
  hardware, their personal sign-ins and posts, identity, tax and bank
  details".
- **Terms of use.** The models directory's source notes record that Ollama's
  terms "refuse 'automated means to access our services without
  permission'" and that section 7 of OpenRouter's terms "refuses software
  that scrapes or copies information on the site". The first pass of this
  research had already made a handful of automated reads of public Ollama
  and OpenRouter pages (their pricing and documentation pages and their
  sitemaps) before that note was read. No further reads of either site were
  made, and nothing from them is kept beyond the fact that no programme was
  seen.

## The answer in short

The owner named 64 services. Most pay nothing for a referral.

| Result | Services |
|---|---|
| Cash for referrals, with a published rate | Novita AI, Railway, Netlify, DigitalOcean, Postmark, Apify |
| Cash for referrals, archived page only | Vultr |
| Credit that can partly become cash | RunPod, Vast.ai |
| A programme exists but the rate is not published | Vercel, Pinecone, Brevo, Composio |
| Credit or promotion only | Hyperbolic, Cerebras, Akamai Cloud (Linode), Turso |
| Enterprise deals only | SendGrid (Twilio), Amazon SES (AWS Partner Network) |
| Not known | Perplexity (pages refuse automated reads), Mailgun (a referral form with no published terms) |
| No programme found | 43 services, including Ollama and Ollama Cloud, OpenRouter, Fly.io, Together AI, Groq, Fireworks AI, DeepInfra, Replicate, fal, Supabase, Neon, Resend, Cloudflare, Smithery, Zapier, Langfuse, Helicone, LangSmith and Portkey |

The owner's own examples, directly:

- **Ollama and Ollama Cloud:** no programme found.
- **Fly.io:** no programme found.
- **Mailgun:** no cash programme is published. There is a referral form with
  no terms, and the Mailgun Maverick programme pays in "swag, exclusive
  events, various challenges with rewards, and beta release products".
- **Model Context Protocol services:** Apify pays cash (and, from the first
  record, Firecrawl and Bright Data); Composio takes affiliate applications
  without published terms; Smithery, Zapier, Pipedream, Klavis, Glama and
  mcp.run show none.
- **Model serving and model APIs:** only Novita AI pays cash on published
  terms. RunPod and Vast.ai pay credit that can partly become cash;
  Hyperbolic and Cerebras give credit. None of the eleven hosted providers in
  the models directory runs a link programme.

The ranked list of programmes worth joining is in
[Ranked programmes worth joining](#ranked-programmes-worth-joining).

## How this was checked

The method is the first record's: each vendor's own sitemap, footer and
programme pages, read over HTTPS on September 24, 2026, with no search
engine, because the session's web search allowance was spent. Terms hidden
in collapsed questions were read from the page's own data. A cell left empty
or marked "Not stated" means the pages read did not say it. No rate was
estimated.

## Programmes by category

"Window" is the cookie or attribution period. Every page was read on
September 24, 2026.

### Model APIs and model serving

| Service | Programme | Pays, and for how long | Window | Payout | Restrictions | Sign-up and source |
|---|---|---|---|---|---|---|
| Novita AI | Affiliate programme on Tapfiliate | "10% commission on every referral's spending for the first 180 days", "with no limit" | 60 days | Not stated on the pages read | Not stated on the pages read | [novita.ai/affiliate-new](https://novita.ai/affiliate-new), sign-up at `affiliates.novita.ai` |
| RunPod | Referral, then affiliate status | Referral: a random $5 to $500 credit for both sides when the new user spends $10, and 3% of Pod and 5% of Serverless spend for 6 months, in credits. After 25 spending referrals: 10% of all spend | Not stated | Credits expire after 90 days; cash only at affiliate status | "Self-referrals and referral manipulation are prohibited" | [runpod.io referral and affiliate program](https://www.runpod.io/referral-and-affiliate-program) |
| Vast.ai | Referral | 3% of a referred client's lifetime spend, as credit | Life of the account | Up to 75% withdrawable through Stripe Connect, PayPal or Wise, from a dedicated referral account | No paid ads on Vast.ai brand terms; no ads that link straight to vast.ai; one referral account; effective September 15, 2026 | [docs.vast.ai referral program](https://docs.vast.ai/guides/reference/referral-program) |
| Hyperbolic | Referral credit; separate enterprise partner programme | $5 credit to you and $6 to the new user after they top up $5 within 14 days. Partner programme (post of August 11, 2025): 1% of a referred customer's revenue in its first six months, for deals signed within 180 days | 14 days | Credit; partner commissions quarterly | Partner leads must be new and qualified | [referral](https://www.hyperbolic.ai/blog/referral-program), [partner programme](https://www.hyperbolic.ai/blog/introducing-hyperbolic-partner-program) |
| Cerebras | Ambassador programme | Compute credits and event budgets, not a share of sales | | | | [cerebras.ai/ambassadors](https://www.cerebras.ai/ambassadors) |
| Perplexity | Not known | | | | | Every page tried returned HTTP 403, and no archived copy was found |
| Ollama and Ollama Cloud | No programme found | | | | | Pricing and home pages and the documentation sitemap; see the terms of use note above |
| OpenRouter | No programme found | | | | | Sitemap and documentation pages; see the terms of use note above |
| Together AI | No programme found | | | | | Sitemap: technology partners only |
| Fireworks AI | No programme found | | | | | Sitemap: technology partners only |
| Groq | No programme found | | | | | Sitemap: newsroom partnerships only |
| DeepInfra | No programme found | | | | | Sitemap |
| Replicate | No programme found | | | | | Sitemap |
| fal | No programme found | | | | | Sitemap and pricing page |
| SambaNova | No programme found | | | | | Sitemap: press partnerships only |
| Mistral AI | No programme found | | | | | Sitemap |
| Cohere | No programme found | | | | | Partners page for technology and consulting partners |
| Lambda | No programme found | | | | | Partners page |
| Modal | No programme found | | | | | Home and pricing pages |
| Baseten | No programme found | | | | | Pricing page links a partner contact form only |

### Hosting and deployment

| Service | Programme | Pays, and for how long | Window | Payout | Restrictions | Sign-up and source |
|---|---|---|---|---|---|---|
| Railway | Affiliate, and template kickbacks | Affiliate: 15% of a new customer's first 12 months of invoices; the new customer gets $20 in credits. Kickbacks: 15% of the usage of deployments made from your published template, plus 10% while you answer its users' questions | Not stated | Affiliate: withdraw to GitHub Sponsors or Buy Me a Coffee. Kickbacks: credits, or cash through Stripe Connect, minimum $0.01 | Kickbacks need a template in Railway's marketplace | [affiliate](https://docs.railway.com/community/affiliate-program), [kickbacks](https://docs.railway.com/templates/kickbacks) |
| Netlify | Ecosystem Partners on PartnerStack | "20% revenue share for up to 12 months on eligible self-serve new business" | Not stated | Through PartnerStack | Not stated; no need to be a Netlify customer; not exclusive | [netlify.com/partners](https://www.netlify.com/partners/), application at `dash.partnerstack.com/application?company=netlify&group=ecosystempartners` |
| DigitalOcean | Affiliate on CJ; also an in-product referral | Affiliate: "10% commission each month, for an entire year". Referral: $25 credit after the new user's billings reach $25 | Not stated | Through CJ; referral in credit | "Anyone can join" | [digitalocean.com/affiliates](https://www.digitalocean.com/affiliates), [referral](https://www.digitalocean.com/referral-program) |
| Vercel | Affiliate Marketing Terms (updated July 8, 2025), paid through Dub | Rates are in "Program Guidelines" that were not found in public; fees are "one-time payments unless expressly stated otherwise". The v0 ambassador programme paid $10 per Premium and $30 per Team referral (post of July 29, 2025) | Not stated | Through Dub | Acceptance at Vercel's discretion. No paid advertising of the link "including via Google, Facebook, Twitter"; no brand keywords; no coupon sites; no cookie stuffing; no buying for yourself; an advertising disclosure is required; a link must come down within 24 hours on request | [terms](https://vercel.com/legal/affiliate-marketing-terms) |
| Vultr | Referral | "earn up to $100"; the new user must be active more than 30 days | Not stated | Issued the business day after the 1st and 15th of each month | Not stated | vultr.com/company/referral-program: archived copy of August 12, 2026; the live page refused automated reads |
| Akamai Cloud (Linode) | Referral | $25 non-expiring credit after the new user is active 90 days and spends $25; the new user gets $100 of credit for 60 days | Not applicable | Credit only | You must first spend $25 | [techdocs.akamai.com referral program](https://techdocs.akamai.com/cloud-computing/docs/referral-program) |
| Fly.io | No programme found | | | | | Sitemap and pricing page |
| Render | No programme found | | | | | Sitemap: solution partners only |
| Koyeb | No programme found | | | | | Sitemap |
| Northflank | No programme found | | | | | Sitemap |
| Hetzner | No programme found | | | | | `hetzner.com/cloud/referral-program` serves the Cloud product page with no referral terms |
| OVHcloud | No programme found | | | | | 22 sitemaps searched for referral and affiliate pages; reseller programmes only |
| Scaleway | No programme found | | | | | 9 sitemaps searched; partner space only |
| Cloudflare | No programme found | | | | | Partners page for agencies and technology partners |

### Email sending

| Service | Programme | Pays, and for how long | Window | Payout | Restrictions | Sign-up and source |
|---|---|---|---|---|---|---|
| Postmark | Affiliate on Rewardful | "20% commission of each referred billing, for a period of up to 12 months" | 60-day first-party cookie, first touch | PayPal monthly from $100, starting 60 days after sign-up; tax form within 90 days or commissions are forfeited | No paid advertising, search or social pages; no own link; at first "limited to a select group of partners" | [questions](https://postmarkapp.com/support/article/postmark-affiliate-referral-partner-program-faq), [agreement](https://postmarkapp.com/postmark-affiliate-referral-program-agreement) |
| Brevo | Affiliate on PartnerStack | "a fixed reward"; amount not stated | 90 days | Monthly through PartnerStack | A website with traffic and an email address on its domain | [brevo.com/partners/affiliates](https://www.brevo.com/partners/affiliates/) |
| SendGrid (Twilio) | Partner referral addendum for enterprise deals | 10% of the first-year Minimum Spend Amount for one service, 15% for several; the deal must be at least $25,000 a year for at least 12 months | Registered opportunities | Within 90 days of the order start; for several services, the last third of the fee after adoption targets are met | For registered partners only | [twilio-partner-referral-addendum](https://www.twilio.com/en-us/legal/twilio-partner-referral-addendum) |
| Amazon SES | AWS Partner Network: resale, consulting and technology partners | No link programme | | | | [aws.amazon.com/partners](https://aws.amazon.com/partners/) |
| Mailgun | Not known | A referral form with no published terms; the Mailgun Maverick programme rewards community members with "Gunners (aka Mailgun employees), swag, exclusive events, various challenges with rewards, and beta release products" | | | Mavericks sign a non-disclosure agreement | [referral form](https://www.mailgun.com/email-referrals/), [Maverick terms](https://www.mailgun.com/about/partners/mailgun-maverick-terms-and-conditions/) |
| Resend | No programme found | | | | | Sitemap and pricing page |
| Mailjet | No programme found | | | | | Sitemap: glossary pages only |
| SparkPost | No programme found | | | | | Sitemap |
| Loops | No programme found | | | | | `loops.so/affiliates` opens the home page |

### Model Context Protocol and agent-tool platforms

| Service | Programme | Pays, and for how long | Window | Payout | Restrictions | Sign-up and source |
|---|---|---|---|---|---|---|
| Apify | Affiliate on FirstPromoter | 20% for the first 3 months, then 30%, with no time limit, up to $2,500 per customer (up to $5,000 at 50 or more active customers) | Not stated | PayPal, bank transfer or Wise within the first 15 days of each month, once there are three referred customers and $100; or 115% as Apify usage | No pay-per-click ads on Google, Facebook, Instagram, LinkedIn or similar | [apify.com/partners/affiliate](https://apify.com/partners/affiliate), sign-up at `affiliate.apify.com` |
| Composio | "Affiliate Partnership" is one choice on the partnership application form | Not published | | | | [composio.dev/partnerships](https://composio.dev/partnerships) |
| Smithery | No programme found | | | | | Sitemap and home page |
| Zapier (its protocol server) | No programme found | | | | | Sitemap |
| Pipedream | No programme found | | | | | Sitemap |
| Klavis | No programme found | | | | | The home page now offers coding-agent training data |
| Glama | No programme found | | | | | Home page; the pricing page needs a sign-in |
| mcp.run | No programme found | | | | | `mcp.run` now opens `turbomcp.ai` |

### Databases and vector stores

| Service | Programme | Pays, and for how long | Window | Payout | Restrictions | Sign-up and source |
|---|---|---|---|---|---|---|
| Pinecone | Affiliate programme and a referral programme, both on PartnerStack | "earn commission by creating valuable content and applications"; rate not published | Not stated | Through PartnerStack | Not stated | [pinecone.io/partners](https://www.pinecone.io/partners/), applications at `dash.partnerstack.com/application?company=pinecone&group=affiliateprogram` |
| Turso | Content partner programme | Promotion and editorial help, no share of sales | | | | [turso.tech/partners/content](https://turso.tech/partners/content) |
| Supabase | No programme found | | | | | Partner programme for technology and agency partners; its master agreement has no referral fee |
| Neon | No programme found | | | | | The creator programme page now opens the community page |
| Upstash | No programme found | | | | | Sitemap |
| MongoDB Atlas | No programme found | | | | | Sitemap: a community creator programme only |
| Qdrant Cloud | No programme found | | | | | Partners page |
| Weaviate | No programme found | | | | | Partners page |
| Zilliz | No programme found | | | | | Partners page |

### Model observability and routers

| Service | Programme | Pays, and for how long | Window | Payout | Restrictions | Sign-up and source |
|---|---|---|---|---|---|---|
| Langfuse | No programme found | | | | | Partners page lists integration partners |
| Helicone | No programme found | | | | | Home page and sitemap |
| LangSmith (LangChain) | No programme found | | | | | LangChain Partner Network for services firms |
| Portkey | No programme found | | | | | Home page and sitemap |

## Ranked programmes worth joining

Ranked by fit with Baltor's users, who are developers running coding
harnesses and bringing their own models, then by value per paying user,
then by how much friction the programme has. This list merges this record
with the first one, because web data services (Firecrawl, Bright Data) and
monitoring (UptimeRobot) fall inside the infrastructure the owner described.
A directory row is named only where the service's own company publishes it.

| Rank | Programme | Why here | Directory rows it applies to | Models directory rows it applies to |
|---|---|---|---|---|
| 1 | Apify | Agent tools for harnesses, cash with no time limit, cap of $2,500 per customer, published terms | `com.apify/apify-mcp-server` | None |
| 2 | Firecrawl | Web data for harnesses; 25% for a year, then 15% for as long as the customer pays; invites "Tool directories" | `io.github.firecrawl/firecrawl-mcp-server` | None |
| 3 | Novita AI | The only model API and graphics processor service with cash on published terms: 10% of all spend for 180 days, no cap. It offers "200+ Model APIs" and graphics processor rentals, and publishes a Claude Code guide | `docker/novita` (Novita Labs' own server, listed through the Docker catalog with its lister not yet matched) | No row today. It would apply to a Novita AI hosted-provider row, and to can-I-run answers for cards its pages name: `a100-80-sxm`, `h100-sxm` and `rtx-4090` |
| 4 | Railway | The only hosting service the starter names that pays; affiliate plus template kickbacks for a starter published as a Railway template | `com.railway/mcp` | None |
| 5 | RunPod | Graphics processor rental for people who run their own models; credits first, 10% cash after 25 spending referrals | None (only a third-party row) | Can-I-run answers for cards its pricing page lists: `h100-sxm`, `a100-80-sxm`, `l40s`, `rtx-4090` and `rtx-5090` |
| 6 | Vast.ai | Graphics processor rental; 3% of lifetime spend, up to 75% cashable; template links carry the referral | None | Can-I-run answers that suggest renting a card; the pricing page's text named no cards, so which presets match was not checked |
| 7 | DigitalOcean | Hosting and graphics processor machines; 10% of spend for a year, through CJ | None (only third-party rows) | Can-I-run answers for cards its GPU Droplets page lists: `h100-sxm`, `a100-80-sxm` and `l40s` |
| 8 | Netlify | Hosting for what harness users build; 20% for up to 12 months | None | None |
| 9 | Bright Data | Web data; 50% revenue share with a 90-day window; its two pages disagree on the per-customer cap | `io.github.brightdata/brightdata-mcp` | None |
| 10 | UptimeRobot | Monitoring; 20% for the life of the subscription, no approval | `com.uptimerobot/uptimerobot` | None |
| 11 | Postmark | Email sending, the starter's fallback; 20% for 12 months, but open at first only to a small group of partners | None (only third-party rows) | None |
| 12 | Pinecone | Vector store; programme on PartnerStack, rate not published | `docker/pinecone` (Pinecone's own assistant server, listed through the Docker catalog with its lister not yet matched) | None |
| 13 | Vercel | Hosting; rates not public and the rules forbid any paid promotion of the link | `com.vercel/vercel-mcp`, `io.github.vercel/next-devtools-mcp` | None |
| 14 | Make | Automation; 35% for 12 months, paid by Wise | `com.make/mcp-server` | None |

Two rows above are Docker catalog entries whose lister is not verified.
Under the first record's rule that paid links sit only on rows the vendor
publishes, `docker/novita` and `docker/pinecone` get a paid link only once
the directory matches them to the vendor, for example when the vendor lists
the same server in the official registry.

Not worth joining now: Composio and Brevo until they publish rates;
Hyperbolic, Cerebras, Akamai Cloud and Turso, which pay in credit or
promotion; SendGrid and Amazon SES, which pay only on enterprise deals; and
Vultr until its live page can be read.

## Value per paying user, from the vendors' own figures

| Programme | Value per paying user (sourced figures only) |
|---|---|
| Novita AI | 10% of everything the user spends in their first 180 days |
| Netlify | 20% x $9 x 12 = $21.60 on the Personal plan; 20% x $20 x 12 = $48 on Pro |
| DigitalOcean | 10% x spend x 12; $4.80 on the $4 a month Droplet the pricing page lists as the lowest |
| Vast.ai | $30 of credit per $1,000 of lifetime spend, of which up to $22.50 can become cash |
| RunPod | $5 to $500 of credit at random, plus 3% or 5% of six months of spend in credit, until affiliate status |
| Apify, Firecrawl, Railway, Postmark, UptimeRobot | As in the first record: $62.70, $48, $9 to $36, $36 and $67.20 in the first year on the plans named there |

The formula of the first record still applies: income equals measured
follows times the measured share who pay times these values. The aggregate
link counter the owner approved measures the follows; each programme's
dashboard measures who pays.

## What stays unknown

- Perplexity's programme, if any: its pages refused automated reads and no
  archived copy was found. A person can read it in a browser.
- Mailgun's referral terms: the form publishes none, and this research
  submits no forms.
- The rates of Vercel, Pinecone, Composio and Brevo, which the pages read do
  not publish.
- Bright Data's per-customer cap ($1,000 on one page, $2,500 on another).
- Vultr's current terms, read only from an archived copy of August 12, 2026.

## What needs the owner

Under the authority recorded in AGENTS.md on September 24, the paid link
wording and the partner mailbox are engineering's to carry out, and the
aggregate link counting change to the privacy notice is approved. Whether
accepting a programme's terms falls inside the same authorization is for the
main session to confirm against the owner action page; this record joins
nothing. What only the owner can supply:

1. Identity checks that a programme or its network asks for, such as
   Stripe Connect, Dub, PartnerStack, Tapfiliate, FirstPromoter, CJ or
   Rewardful onboarding.
2. Tax details, such as a Form W-9. Postmark forfeits commissions without a
   tax form within 90 days.
3. Bank and payout details: bank accounts, PayPal, Wise, and the GitHub
   Sponsors or Buy Me a Coffee account that Railway's affiliate withdrawals
   need.

## Sources

All read on September 24, 2026, unless the row says otherwise. Pages first
read for the [first record](AFFILIATE-ADVERTISING-AND-LISTING-INCOME-2026-09-24.md)
are listed there.

- [Novita AI affiliate](https://novita.ai/affiliate-new) and its sign-up page `affiliates.novita.ai`
- [Hyperbolic partner programme](https://www.hyperbolic.ai/blog/introducing-hyperbolic-partner-program)
- [Netlify partners](https://www.netlify.com/partners/) and [pricing](https://www.netlify.com/pricing/)
- [Vercel affiliate marketing terms](https://vercel.com/legal/affiliate-marketing-terms) and [partners](https://vercel.com/partners)
- [DigitalOcean Droplet pricing](https://www.digitalocean.com/pricing/droplets)
- [Twilio partner referral addendum](https://www.twilio.com/en-us/legal/twilio-partner-referral-addendum)
- [AWS Partner Network](https://aws.amazon.com/partners/)
- [Mailgun Maverick](https://www.mailgun.com/about/partners/maverick/) and [its terms](https://www.mailgun.com/about/partners/mailgun-maverick-terms-and-conditions/)
- [Composio partnerships](https://composio.dev/partnerships)
- [Pinecone partners](https://www.pinecone.io/partners/), [Qdrant partners](https://qdrant.tech/partners/), [Weaviate partners](https://weaviate.io/partners), [Zilliz partners](https://zilliz.com/partners)
- [Cohere partners](https://cohere.com/partners), [LangChain Partner Network](https://www.langchain.com/langchain-partner-network), [Langfuse partners](https://langfuse.com/partners)
- Sitemaps and home pages of fal, SambaNova, Baseten, Modal, Smithery, Klavis, Glama, turbomcp.ai (where `mcp.run` now leads), MongoDB, SendGrid, Mailjet, SparkPost, OVHcloud, Scaleway, Helicone and Portkey
- The directory and models directory rows, read from their working trees at about 18:00 Coordinated Universal Time (35,278 directory rows)
