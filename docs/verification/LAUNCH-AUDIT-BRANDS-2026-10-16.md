# Launch audit of the brand websites, October 16, 2026

The owner, October 8: "get this ready for launch, adversarially validate every
single page, all marketing language, nomeclature, ideas, standards, index,
documents, how to, test it out, variations, side by side comparisons ...
subdomains". This record covers the ten public brand hosts that the shared
service serves besides Baltor: AgentFeeds, AgentFoundry, AgentStudios, AgentAFK
and the Don't be a meat proxy campaign, each at its apex and `www` name. A
separate audit covers `baltor.ai`, its subdomains and the signed-in journey.

It also records the diagnosis of the 21 canceled HTTP 200 metadata fetches that
keep the release 93 twenty-host browser matrix's strict results false
(S-6.35.06 and S-6.35.08), and what the AgentBriefs launch still needs.

Every source fix below is committed for review and is not live until the next
guarded release. The live hosts ran release 93 (`bdc45955`) throughout; its
brand renderers and brand assets are byte-identical to `main` at `f2ae304e`,
where this work started.

## Scope, method and effects

| Brand | Apex and `www` | Kind | Routes in source |
| --- | --- | --- | --- |
| AgentFeeds | `agentfeeds.si`, `www.agentfeeds.si` | Account-enabled | 40 (19 collection pages) |
| AgentFoundry | `getagentfoundry.si`, `www.getagentfoundry.si` | Account-enabled | 392 (376 example pages) |
| AgentStudios | `agentstudios.si`, `www.agentstudios.si` | Account-enabled | 394 (376 example and 2 media pages) |
| AgentAFK | `agentafk.si`, `www.agentafk.si` | Public-only | 12 |
| Don't be a meat proxy | `dontbeameatproxy.si`, `www.dontbeameatproxy.si` | Public-only campaign | 5 |

- **Route inventory.** Every route came from the renderers' own route lists,
  843 in all, plus each brand's `robots.txt`, `sitemap.xml`, `llms.txt` and
  client configuration file.
- **HTTP crawl.** 2,672 sequential GET and HEAD requests over one keep-alive
  connection per host, with a pause between requests: every route on the apex
  and on `www`, 794 linked same-site targets, 70 external links, plain HTTP on
  all ten names and refusal probes.
- **Browser pass.** Chrome 148.0.7778.178 through Playwright, 409 page loads
  at 390x844 and 1440x900 in light and dark: every non-detail route, five
  example detail pages per creative brand and both media pages, plus the five
  `www` roots.
- **Signed-out controls.** 70 checks up to each control's real local effect:
  filters, searches, pagination, copy buttons, browser-local saves,
  reading-profile and task-list downloads, the campaign's decision picker and
  media playback.
- **Accessibility probes.** Chrome's own accessibility tree for headings and
  brand links, keyboard focus, phone menus and word joins at phone width.

No form that creates or signs in to an account was submitted. No provider,
DNS, registrar or deployment change was made. The private evidence is in
`~/baltor-private/claude-takeover-20261015-dhycum/ops/launch-audit-brands/`
(`taska/` and `taskb/` reports and scripts with digests, and three small
images).

## What passed

- All 843 apex routes answered 200, and every `www` route behaved as the
  release 93 contract says: public HTML answers 301 to the same apex path,
  and origin-local paths such as `/login`, `/saved` and `/plan` stay on `www`.
- Plain HTTP answers 301 to HTTPS on all ten names.
- Every page carries a strict content policy (`default-src 'none'`,
  `frame-ancestors 'none'`, `form-action 'none'`), `X-Frame-Options: DENY`,
  `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer` and a
  Permissions-Policy. No public page sets a cookie.
- The public-only views refuse `/mcp`, `/signup`, OAuth discovery and
  `/api/v1/account/identity` with 404. The account-enabled brands publish their
  own OAuth issuer and MCP resource. Another brand's assets and Baltor's
  `service.js` answer 404 on every brand host.
- Every page has its own canonical address, `lang="en"`, one visible `h1` and
  a meta description. Every image has `alt` text and dimensions.
- The browser pass found no sideways scroll, broken image, console error,
  page error or failed subresource of 400 or higher in 409 loads. The skip
  link is the first focus stop with a visible indicator on every page except
  `/auth/confirm`. Contrast failures appeared only on the disabled "Previous"
  pagination button, which WCAG exempts.
- 68 of 70 signed-out control checks passed. The two failures are the
  AgentFeeds search defect below, at both widths. Downloads were real: the
  AgentFoundry and AgentStudios client configuration names its own origin,
  the reading-profile builder produced `profile.json` and `READING.md`, the
  run desk produced `baltor-tasks.txt`, and both original media demos played.
- Checkable facts matched live data and source: 19 collections, 60 sources and
  the 2026-10-09 documentation date; 376 public examples on AgentFoundry and
  378 on AgentStudios; 448 Public Good components; the three MCP tool names;
  the client's Python 3.10 requirement; the $9 AgentFeeds price, free through
  December 31, 2026; the approved operator address.
- The trial, invitation, status, unpublished-terms and retired-phrase rules in
  `tools/public_wording_rules.mjs` had no hits on brand copy, and no page used
  an em or en dash or spelled out the currency. The runtime-word rule matched
  only ordinary English "loop" in component descriptions and the repository
  name inside AgentAFK's setup commands. "Packages" appears in collection data
  about third-party software packages.

## Findings

Severity is the effect on a visitor at launch. "Fixed" means fixed in source
in the named commit; it reaches the live hosts with the next release.

| # | Host | Page | Check | Severity | Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | AgentFeeds, AgentFoundry, AgentAFK, campaign (apex and `www`) | Any unknown address | Brand error page | Medium | The shared fallback links `/assets/service.css`, `/assets/architecture.css` and `/assets/baltor-mark.svg`, which brand hosts refuse, so it renders unstyled with a broken image. It tells AgentAFK and campaign visitors "nothing is wrong with your account or your key". On the campaign its "Search the docs" and "Status" links are 404. Image 1. | Fixed `1f44c597` |
| 2 | `agentstudios.si` | `/` below 720 px | Headline | Medium | "Working files forcreative projects.": the phone CSS hides the `<br>`. Chrome's accessibility tree reads the same. Image 2. | Fixed `c297cb59` |
| 3 | `agentfeeds.si` | `/collections` | Search | Medium | The placeholder suggests "coding, finance or design"; "finance", "design" and "security" each found 0 of 19 collections because only title and group were indexed. | Fixed `1523735f` |
| 4 | `agentfeeds.si` | `/collections`, `/saved` | Status wording | Low | "1 collections saved in this browser." | Fixed `1523735f` |
| 5 | `agentfeeds.si`, `dontbeameatproxy.si` | `/pricing`, `/questions` | Price wording | Low | "$9 / month" and "$9 per month" beside Baltor's "$9 a month". No price changed. | Fixed `1523735f` |
| 6 | `getagentfoundry.si`, `agentstudios.si` | Every page at 390 px | Phone menu | Low | Escape left the menu open (`aria-expanded` stayed `true`); the other three brands close it. | Fixed `a690e65a` |
| 7 | All five brands | All 843 pages | Link previews | Low | `og:description` absent on four brands; `og:site_name` and `twitter:card` absent on all five. | Fixed `aec7a628` |
| 8 | `agentafk.si`, `dontbeameatproxy.si` | Every page | Content policy | Low | `connect-src` admitted the identity provider on views with no identity client. | Fixed `8cf432e6` |
| 9 | All five brands | Marketing copy | Owner rule of October 1 on negative language | Low | 70 sentences described what a product or feature does not do. | Fixed `52a75586`, `4dca841c` |
| 10 | AgentFoundry, AgentStudios | `/library`, `/examples` | Matrix strict result | Low | 21 canceled HTTP 200 metadata fetches; see the Task B section. | Attribution `f67995f0`; checker adoption open |
| 11 | All ten brand hosts | Every page | `Strict-Transport-Security` | Medium | Absent on all 843 HTML pages; plain HTTP does redirect. | Open: the copy-polish agent adds the header for brand hosts |
| 12 | All five brands | Every page | `og:image` | Medium | No brand has a raster share image, so shared links show no picture. | Open: one 1200x630 image per brand is a design task |
| 13 | AgentFoundry, AgentStudios | `/examples`, `/library` | Weight | Low | The largest pages are 100,449 and 102,350 compressed bytes (447,845 and 461,511 bytes of HTML) because all 376 or 378 cards are rendered at once. | Open |
| 14 | All five brands | Versioned assets | Caching | Low | `site.css`, `site.js` and `mark.svg?v=<sha256>` are served `Cache-Control: no-store`, so each view downloads them again. | Open |
| 15 | `agentstudios.si` | `/examples`, `/library` | Duplicate content | Low | The two addresses serve the same 461,511-byte page, each canonical to itself, with the same title. | Open |
| 16 | All five brands | `/favicon.ico` | Icon | Low | 404 on every host; pages declare their SVG mark, so browsers show it. | Open |
| 17 | AgentFeeds, AgentFoundry, AgentStudios | Account routes, `/help`, `/docs` | Page titles | Low | Seven account routes, `/login` and `/signup` included, are titled "Your account"; `/help` and `/docs` share "Help". | Open: account routes belong to the signed-in journey work |
| 18 | AgentFoundry, AgentStudios | `/examples`, `/library` | Heading order | Low | Card titles are `h3` directly under the page `h1`. | Open |
| 19 | All five brands | Header and footer links | Target size | Low | Many links are 17 to 21 px tall; their spacing likely meets the WCAG 2.2 exception. | Open |
| 20 | AgentFeeds, AgentFoundry, AgentStudios | `/auth/confirm` | Skip link | Low | The first Tab stop is a content link, not the skip link. | Open: signed-in journey work |
| 21 | All five brands | `/privacy` | Duplicate `id` | Low | `privacy-contact` appears twice inside the approved privacy article, which is served byte for byte. | Open: changing approved legal bytes needs the owner |
| 22 | `agentafk.si` | `/pricing` | Nomenclature | Low | "Max subscriptions are not sold during this public preview." names Baltor's Max plan, which AgentAFK never introduces. The sentence matches baltor.ai's plan copy. | Open: plan copy is the owner's |
| 23 | baltor.ai and `agentfeeds.si` | Pricing | Nomenclature | Info | Baltor names the $9 plan's feature "Agent Feeds"; the brand is "AgentFeeds". `web_assets/README.md` records the split as deliberate. | No change |
| 24 | `agentfeeds.si` | `/collections/creative-mcp-servers` | "Reviewed" wording | Info | "Third-party code that Baltor has not reviewed." is a safety disclosure in collection data, not a count or qualifier of library items. | Kept |
| 25 | `agentfeeds.si` | Collection pages | External links | Info | `fred.stlouisfed.org` timed out and `sec.gov` answered 403 to this workstation's non-browser client. | Open: recheck from a browser |

### Negative wording that stays

After the rewrite, a negative remains only where it is a required factual
limit. The kept categories are:

- **Billing.** "No automatic charge", "This page does not start a
  subscription", "Creating an account does not start a subscription", "Paid
  checkout is not offered on this standalone site", "Queue call limits do not
  cap your provider bill" and the AgentAFK hosted-execution and Max plan lines.
- **Security and safety.** Credential and key warnings, "Do not use a file
  whose integrity check failed" and "Do not repeat an uncertain external
  action".
- **Claims.** "The queue does not guarantee task completion, lower spending
  or measured token savings."
- **Privacy.** "This campaign adds no account form or advertising tracker."
- **Access.** "No account or payment required" on AgentAFK's home.
- **Interface states.** Empty-state and error messages, HTTP 304 wording, the
  media fallback text and the campaign's `noscript` note.
- **Instructions to an agent and the campaign's own voice.** The agent prompt
  text and the campaign name and headline.
- **Data.** Component limits and media provenance from catalogue records and
  `gallery-media/media.json`, and collection notes from
  `feed_source_collections.json`.

Account and sign-in pages were left to the signed-in journey work.

## Task B: the 21 canceled metadata fetches

### The population

The selected release 93 attempt (`live93-public-03/report.json`, with the same
21 rows as attempt 2) recorded each as a GET `fetch`, status 200,
`canceled: true`, `net::ERR_ABORTED`, with no request identity, timing or
byte count. Matching the rows to the checker's view sequence gives:

| Host | Width | Views that issued the read | Address | Count |
| --- | --- | --- | --- | --- |
| `getagentfoundry.si` | 1440, 390 | `/library` | `/api/v1/public-good?query=&page=1` | 2 |
| `www.getagentfoundry.si` (served by the apex after the 301) | 1440, 390 | `/library` | same, on the apex | 2 |
| `agentstudios.si` | 1440, 390 | `/examples`, `/library`, then both again in the AgentStudios sequence | same | 8 |
| `www.agentstudios.si` | 1440, 390 | the same four views | same, on the apex | 8 |
| `www.agentstudios.si` | 1440 | `/library` search for "water" | `/api/v1/public-good?query=water&page=1` | 1 |

The initiator is the brand `site.js` reader: `load()` calls `read()` at page
start for the empty query and from the search form for "water". `read()`
fetches with `credentials:'omit'`, `redirect:'error'`, `cache:'no-store'` and
a 15-second `AbortController`, reads the body through a stream reader to the
end with a 1 MiB ceiling, then parses JSON. Both scripts were byte-identical
to release 93 (`fa0df161...` and `74f1dd15...`) during the reproduction.

### What the reproduction observed

All runs used the exact live views, the frozen checker's own request guard and
transport denial imported read-only, and per-request instrumentation on both
sides: the DevTools network events with their timestamps, and an
observation-only page probe recording each fetch call, reader chunk, end of
body, cancel, abort and the page's status text.

1. **Every canceled read had delivered its whole body.** On every affected
   view the read ended with `loadingFailed`, `net::ERR_ABORTED`, canceled,
   0.3 to 2.3 ms after the last data chunk. In the same millisecond the page's
   reader reached the end of the body with every byte (18,870 for the empty
   query, 4,952 for "water"), and the page then rendered "448 matching
   components" with 20 result cards. No page code called `reader.cancel()`,
   `abort()` or saw an abort signal. The next navigation came 500 ms or more
   later; context close came seconds later.
2. **Neither the checker nor the transport causes it.** It occurs without
   the checker's request guard; with Brotli, zstd and identity encoding (with
   identity, `Content-Length` 18,870 and 18,870 bytes received); and over
   HTTP/2 and with HTTP/2 disabled.
3. **The consumption pattern decides it.** On the same endpoint, from the
   same page, every stream-reader pattern (the site's exact `read()`, no
   signal, default options, `releaseLock`, `for await`) drew the canceled
   report in 25 of 30 attempts. `response.text()` and
   `response.arrayBuffer()` finished normally in 12 of 12.
4. **It reproduces locally.** The exact rendered AgentFoundry page and
   `site.js` on loopback, with the saved live body, drew the report after a
   complete body in 3 of 6 attempts that delivered the body in several writes,
   and in 0 of 3 single-write attempts.
5. **Real failures share the signature.** An oversize body ends the same way
   about 1 ms after its last chunk, with the page's `reader.cancel()` at
   1,048,596 bytes and "The service response was too large." shown. A stall
   ends the same way after the 15-second abort. A truncated body ends as
   `ERR_CONTENT_LENGTH_MISMATCH`, not canceled. Navigating away mid-body left
   no network terminal event on the page session at all, matching the failed
   navigation controls in the earlier diagnosis. Chrome keeps no response body
   for any canceled request, so network events alone cannot separate a
   complete body from these failures.
6. **The attribution holds on live data.** One bounded live run repeated the
   frozen checker's sequence on the four affected origins at both widths:
   22 canceled reads (19 empty-query, 3 "water"), all with a page-side end of
   body and matching bytes, 0 unattributed, 0 unfinished, 852 requests.

### Decision

The canceled reports are a benign Chrome reporting race at the end of a
stream-reader body, not a delivery failure. The visitor's page received and
displayed the complete typed collection each time. The product readers stay as
they are, because their streaming ceiling and timeout are deliberate defenses,
and the race appears only when a page reads the body through a stream.

Commit `f67995f0` adds a narrow attribution to `tools/check_hosted_website.mjs`
instead of a blanket exemption. A canceled `fetch` counts as delivered only
when an observation-only page probe proves, for that one request, an end of
body with exactly the network's byte count and no cancel, abort or read error.
The probe is joined to the request by URL and start time; an ambiguous or
distant join yields no evidence. Its tests include a real-Chromium case where
the oversize failure keeps the same network signature and stays a failure,
and mutation controls that weaken the rule or the join and fail.

### What the evidence does not settle

- The release 93 rows themselves carry no request-level evidence. That they
  are the same race is an inference from the same views, request population,
  signature and scripts; their strict false result stays as recorded.
- Which Chromium component emits the report, whether a public Chromium issue
  describes it, and whether other browsers behave the same were not
  established.
- The attribution fixes classification, not accounting: the checker still
  lacks an encoded transfer size for these requests. The page's Resource
  Timing entry carried one in every reproduced case (for example 5,263 bytes
  for a zstd body), which a successor checker could record as page-reported
  accounting.

### Next step for the coordinating session

Give the twenty-host checker a successor that installs `streamedFetchObserver`
and classifies failures with `createStreamedFetchAccounting`, then run the
matrix once after the next release with `MEM_MAX=6G`. Every other failure
class keeps its current strictness.

## AgentBriefs launch list

The owner bought `agentbriefs.si`. Observed on October 16, read-only:

- **DNS host.** Namecheap BasicDNS (`dns1` and `dns2.registrar-servers.com`).
- **Apex.** `A 192.64.119.204`: Namecheap's redirect service, which answers
  HTTP 302 to `http://www.agentbriefs.si/`; HTTPS on the apex timed out.
- **`www`.** A Namecheap parking page over HTTP; HTTPS failed during the TLS
  handshake.
- **Mail.** Namecheap email forwarding: five `eforward` MX records and an SPF
  `TXT` record.
- **Missing.** No `AAAA` and no `CAA` record.
- **Reference.** `agentstudios.si` uses Cloudflare name servers, `A` and
  `AAAA` records pointing at the shared Fly application, and `www` as a
  `CNAME` to its Fly application hostname.

Provider steps, for the owner or the coordinating session (this audit made
none):

1. Choose the DNS host. Moving `agentbriefs.si` to Cloudflare matches the other
   brand domains and needs a Cloudflare zone and a name server change at
   Namecheap.
2. Replace the parking and redirect records with an apex `A` and `AAAA` for the
   `baltor-pilot` application, read from `fly ips list` at the time, and a
   `www` `CNAME` to its Fly application hostname, without the Cloudflare proxy,
   as for the other brands. Optionally add `CAA` for Let's Encrypt.
3. Add Fly certificates for `agentbriefs.si` and `www.agentbriefs.si` and
   confirm issuance on both names.
4. Decide whether to keep Namecheap email forwarding. Sending account mail
   from the brand domain would also need sender records.
5. Admit both origins in the host configuration (`allowed_hosts`,
   `allowed_origins`, `brand_profiles`) in a guarded release with a recorded
   rollback.

Source work, for engineering:

1. Add `agentbriefs` to `BRAND_NAMES` with display name "AgentBriefs", raise
   `MAXIMUM_BRAND_PROFILES` from 10 to 12, and register the renderer in
   `brand_pages.renderer_for`.
2. Build `agentbriefs_pages.py` from `design/prototypes/agentbriefs/`: its own
   pages, exact assets, `robots.txt`, `sitemap.xml`, `llms.txt`, an
   `error_page`, link-preview tags and the approved legal pages. Launch it as a
   public-only view, so CompanyDNA stays memory-only and there is no upload,
   sign-up or payment until S-6.35.09 qualifies one company-context-to-decision
   path.
3. Extend the owning tests: renderer routes and assets, the standalone
   boundary refusals for a public-only view, the `www` redirect pair, the brand
   error page, the content policy without the identity provider, browser layout
   at 390 and 1440, and the twenty-host matrix as a twenty-two-host matrix.
4. Owner decisions before any private company context is accepted: privacy
   notice and terms coverage for company context, any price (the $299 and
   $799 monthly figures are hypotheses only), and the OpenAI program path for
   hosted plan usage.
5. Launch qualification on both names: public DNS, verified TLS, the 301 from
   `www`, `Strict-Transport-Security`, link previews, and a full browser pass
   like this one.

## Commits

| Commit | Subject |
| --- | --- |
| `f67995f0` | Attribute Chrome's canceled report for complete streamed fetch bodies only with page proof |
| `1f44c597` | Give AgentFeeds, AgentFoundry, AgentAFK and the campaign their own error pages |
| `c297cb59` | Keep the AgentStudios phone headline from joining two words |
| `1523735f` | Make AgentFeeds collection search find its own suggested topics |
| `a690e65a` | Close the AgentFoundry and AgentStudios phone menus with Escape |
| `aec7a628` | Add link-preview metadata to every brand page |
| `8cf432e6` | Drop the identity provider from public-only brand page CSP |
| `52a75586` | Say what AgentAFK and the campaign give visitors instead of what they lack |
| `4dca841c` | Say what AgentFeeds, AgentFoundry and AgentStudios give instead of what they lack |
