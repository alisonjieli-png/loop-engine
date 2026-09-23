# Target site map for the restored website (decided 2026-09-23 by the integrating session)

The owner, 2026-09-23: "with the new design you removed so many header pages, footer pages, and other things.
You need to recover those and work that into the new and improved design." Nothing that existed may disappear
without a written reason. Every page below keeps the redesign's look (tokens in web_assets/architecture.css and
service.css, Geist, the placeholder mark, lighter bands).

## Header, signed out, desktop, in this order
Baltor mark and wordmark (/) | Get started (/connect) | How it works (/how-it-works) | Use cases (/use-cases, new hub)
| Library (/#library) | Pricing (/pricing) | Docs (/docs) || Sign in (/login) | one primary action:
"Request an invitation" (/waitlist) while account creation is closed, "Create account" (/signup) once it opens.
Signed in: Workspace (/app), Account (/account), Administration (/admin, operator only), Sign out; no Sign in.
Phone and narrow screens: one menu button holding every link above, working without the page script.

## Footer: four groups plus a base row
- Product: Get started (/connect), How it works (/how-it-works), Library (/#library), Pricing (/pricing), First example (/examples)
- Use cases: Use cases (/use-cases), the four benefit pages (/overnight, /context, /model-choice, /tool-choice) and the
  four audience pages (/for/coding-agents, /for/engineering-teams, /for/comparing-tools, /for/protocol-and-client)
- Documentation: Docs (/docs), the documentation pages (/docs/<page>: getting set up, searching and retrieving,
  serving and connections, troubleshooting, your account, usage and what you pay for), Access and data (/security),
  Status (/status)
- Company: What Baltor is (/docs/what-baltor-is), Request an invitation (/waitlist), Sign in (/login),
  Privacy notice (/privacy), Terms of service (/terms), Open-source notices (/assets/third-party-notices.txt)
- Base row: the mark, "Baltor.AI", the year, and the operator line the privacy notice already publishes.

## Hostname surfaces (the root address of each hostname)
baltor.ai and www.baltor.ai: the homepage. docs.baltor.ai: the Docs view. status.baltor.ai: the Status view.
examples.baltor.ai: the First example view. demo.baltor.ai: the homepage demonstration of one step.
app.baltor.ai: the Workspace (/app). Every other address on every hostname serves the same page as on baltor.ai,
and every page names https://baltor.ai/<address> as its canonical address.

## Ownership while the work runs in parallel
- Header and footer markup, the homepage, Get started and the shared styles: the UI agent (worktree r22-ui).
- New pages add their views, routes and checks but do NOT edit the header or footer; each reports the links it
  needs, and the integrating session adds them to the footer groups above.

## Addendum (same day)
- /waitlist is its own focused page again (as in release 17): the redesign's form, a short headline and what happens
  next. Get started step 1 links to it. The header's primary action keeps opening /waitlist.
- The header fit is checked at 1440, 1024, 860 and 390 pixels: one row at 1440 and 1024, the menu at 860 and below.

## Revision after the owner's second message (same day), which replaces the header and Get started sections above
The owner: "not every page needs to be in the header ... I think we need to have 'Get Setup' which is a guide on how to
get setup and 'get started' is the sign up and registration/pay funnel." And: "We need to get all of the pages that we
built fully working and fully live, there is no point in building a page if we can't show it."

- "Get set up" (visible spelling; the verb form of the owner's "Get Setup") is the setup guide at /setup, view id
  `setup`. /connect stays as an alias of the same view so earlier links and emails keep working.
- "Get started" is the sign-up, registration and payment funnel at /get-started: 1 create your account (email only),
  2 confirm your email, 3 choose a password, 4 subscribe to Baltor Pro ($29 a month; an operator entitlement covers
  invited users), 5 get set up (links /setup). While account creation is closed, step 1 is the invitation request.
- Header, signed out: How it works | Use cases | Library | Pricing | Docs || Sign in | primary "Get started"
  (/get-started) in every state; the label never switches.
- Header, signed in: Workspace | Get set up | Library | Docs || Account | Sign out (+ Administration for the operator).
- Footer Product group: Get started (/get-started), Get set up (/setup), How it works, Library, Pricing, First example.
- Every built page ships and is reachable from the footer, a hub (Use cases, Docs) or another page; only /auth/*
  and the /connect alias may be unlinked, each with its reason in the contract.
- Pages added to the plan: /models (bring your own model access; model guidance) and /machine-fit (what your machine
  can run), both in the footer's Documentation group and the Docs index.

## Scroll budget (owner, same day: "improve the design so people don't have to scroll down so far to get all of the details")
Live release 20 at 1440x900: homepage 7,046 px (7.8 screens), price first at y=5,001, hero band 1,249 px, seven bands
with 112 px padding top and bottom (1,812 px of padding); How it works 6,144 px; at 390 the homepage is 14 screens.
Rules: the first screen at 1440x900 shows the h1, the lead line and the one primary action (homepage and pricing: the
price too); band padding at most 64 px at desktop, 40 px on phones; homepage and How it works at most 4,000 px at
1440; every other page at most 3 screens (2,700 px), documentation pages exempt but with in-page contents in the first
screen when longer; at 390 at most twice the desktop screens; no dark bands. Compress by layout, never by cutting content.
