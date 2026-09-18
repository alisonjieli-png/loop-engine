# Business paths for Loop Engine: own startup, partnering, joining for equity, and licensing

Date: 2026-09-18. Roadmap step S-5.2 (requirement R-13 in
`docs/roadmap/FABRIC-ROADMAP-2026-09-18.md`). This record is research only.
It does not decide anything. The owner decides.

Every fact below carries the URL it was read from and the date it was read.
All reading happened on 2026-09-18. The word "unverified" marks anything that
could not be confirmed from a primary source (the company's own page,
repository, or job board) or a reputable secondary source (an investor's own
page, an accelerator's company page, or a named press report). No number
was invented; where a number could not be found, the cell says so. Nothing
was purchased and no company was contacted. This record is not legal,
tax, or financial advice.

Inputs read first: the competitive landscape and monetization record
(`docs/research/COMPETITIVE-LANDSCAPE-AND-MONETIZATION-2026-09-18.md`), the
branding record (`docs/research/BRANDING-OPTIONS-2026-09-18.md`), the
packaging tiers guide (`docs/guides/packaging-tiers-and-hosted-service.md`),
and the Business rows of the fabric roadmap.

## Starting position

Observed in the repository on 2026-09-18:

- Loop Engine is published under the MIT license (`LICENSE`), has one
  author, no company, no revenue, no operated hosted endpoint, no published
  price, and no payment provider (packaging tiers guide, section "What this
  guide does not claim").
- The metering units that fit its thesis are verified completions, avoided
  model calls, optimize hours, and judgment depth. Outcome and verification
  records, reading one's own history, exports, and refusals are never
  metered (packaging tiers guide).
- Roadmap steps S-4.4 (deployment), S-4.5 (billing), and S-4.6 (package
  index publication) are "Blocked until the owner supplies the account".
  The service software (S-4.2), the worker image (S-4.1), and the tiers
  (S-4.3) exist offline.
- The landscape record's lessons: do not compete on memory; charge the
  engineering loop by the hour and the selector by avoided cost; put
  governance, not the engine, behind the paid line.

## The four paths in one tree

```text
Business paths for a one-author MIT engine
├── (a) Own startup
│   ├── open-source traction first, then a pre-seed or seed round
│   └── first paid product: a hosted, metered tier of the open engine
├── (b) Partnering
│   ├── integration partner of a memory or evaluation vendor
│   ├── referral or reseller partner (published terms exist)
│   └── startup programs (credits and discounts, not revenue)
├── (c) Joining for equity
│   ├── roles that name agent memory, evaluation, or harness work
│   └── equity norms at seed and Series A
└── (d) Licensing
    ├── MIT core with a paid hosted tier (no license change)
    ├── MIT core with a separately licensed directory
    └── time-delayed or source-available licenses (changes the MIT promise)
```

## How facts are labeled

- Observed: read on a primary or reputable secondary page on 2026-09-18,
  with the URL beside it.
- Inferred: a conclusion drawn from observed facts; the reasoning is stated.
- Assumed: a working assumption stated so it can be challenged.
- Missing or unverified: not found, not readable, or found only in a
  headline without a body.

## Evidence from the landscape companies

### Latest funding round or acquisition

All sources read 2026-09-18.

| Company | Latest round or acquisition found | Amount | Date | Lead investor or acquirer, and other investors named | Source | Status |
|---|---|---|---|---|---|---|
| Mem0 | A round reported on Y Combinator's company page | $24 million | October 2025 | Y Combinator, Peak XV, and Basis Set are named; no lead is named on the pages read | [Y Combinator company page](https://www.ycombinator.com/companies/mem0); [Mem0 investors page](https://mem0.ai/investors) | Amount and investors observed on a reputable secondary source; lead unverified |
| Zep | No round with an amount found | unverified | unverified | About page names Root Ventures, Y Combinator, and Engineering Capital, "Plus angels at industry-leading companies including Vercel, Google, and Airtable"; founded 2023; Y Combinator batch Winter 2024, team size 10 | [Zep about page](https://www.getzep.com/about/); [Y Combinator company page](https://www.ycombinator.com/companies/zep-ai) | Investors observed; amount unverified |
| Supermemory | First round, announced by the founder | $3 million | 2025-10-06 | "led by Susa Ventures (Shaheer), Browder Capital, SF1.vc", with participation from angels the post names as Dane Knecht of Cloudflare, Theo Browne, David Cramer, and Julian Weisser | [Supermemory funding post](https://supermemory.ai/blog/supermemory-raises-3-million-and-building-the-best-memory-engine-for-llms) | Observed |
| Cognee | Seed | $7.5 million | 2026-02-19 | Pebblebed (lead), "with participation from 42CAP and Vermilion Ventures, and angel investors from Google DeepMind, n8n, and Snowplow" | [Cognee seed announcement](https://www.cognee.ai/cognee-raises-seven-million-five-hundred-thousand-dollars-seed); [Cognee newsroom](https://www.cognee.ai/newsroom) | Observed |
| Honcho (Plastic Labs) | Pre-seed | $5.4 million | Announced 2025-05-10 | "from Variant, White Star Capital, & Betaworks", with participation from Mozilla Ventures, Seed Club Ventures, Greycroft, and Differential Ventures, and angels Scott Moore, NiMA Asghari, and Thomas Howell | [Plastic Labs launch post](https://plasticlabs.ai/blog/posts/Launching-Honcho;-The-Personal-Identity-Platform-for-AI) | Observed |
| MemOS (MemTensor) | No round found on the company site or its news page | unverified | unverified | The site states the company was incubated by the Shanghai Institute for Advanced Study of Algorithms with academician E Weinan as chief scientific advisor, and names Alibaba Cloud and Huawei Cloud as ecosystem partners | [MemTensor company site](https://www.memtensor.cn/); [MemTensor news page](https://www.memtensor.cn/h-col-246.html) | Funding unverified |
| Hindsight (Vectorize) | Seed | $3.6 million | April 2024 | True Ventures (lead); DIG Ventures also shown as an investor; company founded January 2024 | [Vectorize about page](https://vectorize.io/about) | Observed |
| Letta | Seed | $10 million | 2024-09-23 | Felicis states that it led Letta's $10 million seed round, joined by Sunflower Capital, Essence VC, and Jeff Dean; the home page adds Clem Delangue, Cris Valenzuela, Jordan Tigani, Tristan Handy, Barry McCardel, and Robert Nishihara | [Felicis announcement](https://www.felicis.com/insight/letta); [Letta home page](https://www.letta.com/) | Observed; any later round unverified (the March 2026 company post could not be fetched) |
| Synth | No round found | unverified | unverified | none named | [Synth home page](https://www.usesynth.ai/); [Synth blog](https://www.usesynth.ai/blog) | Unverified |
| Tellurio | No round found | unverified | unverified | none named | [Tellurio home page](https://tellurio.ai/); [Tellurio blog](https://tellurio.ai/blog) | Unverified |
| LangWatch | Pre-seed | €1 million | 2025-02-25 | "led by Passion Capital, with great support from Volta Ventures and Antler" | [LangWatch funding post](https://langwatch.ai/blog/langwatch-ai-announcing-1m-funding-round-to-bring-the-power-of-evaluations-to-ai-teams) | Observed |
| Not Diamond | No round with an amount found | unverified | unverified | About page lists angel investors by name, including Jeff Dean, Julien Chaumond, Ion Stoica, Akshay Kothari, Arash Ferdowsi, Guillermo Rauch, and Olivier Pomel | [Not Diamond about page](https://www.notdiamond.ai/about); [Not Diamond blog](https://www.notdiamond.ai/blog) | Investors observed; amount unverified |
| TypeSafe (Jev) | No round found | unverified | unverified | "We're backed by top-tier investors who share our vision" with no names | [TypeSafe team page](https://www.typesafe.ai/team) | Unverified |
| PrismML (Bonsai) | No round with an amount found | unverified | unverified | A headline from The Information dated 2026-07-09, linked from the company's news page, calls it "Khosla-Backed"; the article body was not read | [PrismML news page](https://prismml.com/news); [PrismML about page](https://prismml.com/about) | Investor from a headline only; amount unverified |
| Osmosis (Gulp AI Inc.) | No round with an amount found | unverified | unverified | Angels named: Paul Graham, Guillermo Rauch, Misha Laskin, Erik Bernhardsson, Bryant Chou, Sara Du, Matteo Franceschetti, Waseem AlShikh, Troy Demmer; lead investors shown as logos without names; founded 2024 | [Osmosis about page](https://osmosis.ai/about); [Osmosis blog](https://osmosis.ai/blog) | Unverified |
| Adaptive ML | Acquisition by Datadog | Terms not disclosed | 2026-06-30 | Datadog. Earlier: a $20 million seed led by Index Ventures with ICONIQ Capital, Motier Ventures, Databricks Ventures, IRIS, and HuggingFund by Factorial, and angels Xavier Niel, Olivier Pomel, Dylan Patel, and Tri Dao (the post is dated 2024-09-01; a media item from March 2024 reports the same $20 million) | [Datadog announcement](https://www.datadoghq.com/blog/datadog-acquires-adaptive-ml/); [Adaptive ML post](https://www.adaptive-ml.com/post/joining-datadog); [Adaptive ML seed post](https://www.adaptive-ml.com/post/adaptive-raises-seed); [Adaptive ML media list](https://www.adaptive-ml.com/blog?category=Media) | Acquisition observed; amount not disclosed by either party |
| Distyl | No round with an amount found | unverified | unverified | "Backed by leading investors including Coatue, OpenAI, Lightspeed, Microsoft, and Khosla Ventures"; the newsroom returned 404 at two addresses and the blog index shows no funding post | [Distyl home page](https://www.distyl.ai/); [Distyl blog](https://distyl.ai/blog) | Investors observed; amount unverified |

Counts: eight of seventeen companies have a verified amount and date
(Supermemory, Cognee, Honcho, Hindsight, Letta, LangWatch, Adaptive ML's
seed, and Mem0 through a secondary source). One acquisition is verified with
undisclosed terms. Nine amounts stayed unverified.

### Partner or integration programs, and hiring in this area

All sources read 2026-09-18. Job titles are quoted as written, except that a
dash inside a title was replaced by a comma because this repository refuses
dashes in prose.

| Company | Partner or integration program | Open roles that mention agent memory, evaluation, or harness work | Source |
|---|---|---|---|
| Mem0 | No partner program page found. Startup program: three months of the Pro plan free, described as "$1000 of value, Free for 3 Months", with a private Slack channel and onboarding, "valid only for new users". The integrations page lists agent frameworks, coding tools, voice platforms, and workflow tools, with no instructions for a third party to be listed. | "Research Engineer - Agent Memory" (San Francisco); also "Forward Deployed Engineer" and "Full Stack Engineer" | [Startup program](https://mem0.ai/startup-program); [Integrations](https://mem0.ai/integrations); [Careers](https://mem0.ai/careers) |
| Zep | No partner page (404). The pricing page says: "Fast growing venture-capital funded startup? Get Zep Enterprise at an emerging company price." | "Member of Technical Staff: Research" ($180,000 to $250,000 salary and 1.00 percent to 1.50 percent equity), whose description names "evaluation harnesses for retrieval, memory quality, and agent task completion" and memory extraction models; "Head of Forward Deployed Engineering" ($220,000 to $270,000 and 1.20 percent to 1.75 percent equity); "Marketing Manager" ($120,000 to $180,000 and 0.15 percent to 0.35 percent equity); San Francisco or remote in the United States | [Pricing](https://www.getzep.com/pricing); [Careers](https://www.getzep.com/careers/) |
| Supermemory | No partner program found. Startup program: "Qualifying early-stage startups and academic research teams get the Scale plan free for three months, including its included usage, plus dedicated support." | "Founding Research Engineers" and "Founding Backend / Infrastructure Engineers" (San Francisco, remote options); the posting names "context and harness engineering" as ideal knowledge; equity vested in the company, which the posting values at more than $200,000 and growing; senior level $120,000 to $250,000 and entry to mid-level $20,000 to $120,000, adjusted for the local market | [Pricing](https://supermemory.ai/pricing); [Open roles](https://binary.so/UeNYHHE) |
| Cognee | Partner program with four partner types: integration partners ("Databases, data tooling and infrastructure that connect to cognee"), agent and framework partners, implementation partners, and education and community partners. Benefits: "A direct line to the engineers who build cognee", "Cloud credits for building, benchmarking and running pilots with your customers", and exposure to a community the page sizes at more than 30,000 GitHub stars and more than 5 million software development kit runs a month. "We read every application and reply within a week." The pricing page adds "Startup pricing applies to pre-Series B companies" (punctuation changed). | "Principal Platform Engineer" and "Principal Python Engineer" (United States, European Union, remote), "AI Engineer, Working Student" (Berlin); none names memory, evaluation, or harness work in the title | [Partner program](https://www.cognee.ai/consulting); [Pricing](https://www.cognee.ai/pricing); [Careers](https://www.cognee.ai/careers) |
| Honcho (Plastic Labs) | No partner program. Startup program for startups with under $5 million raised: "$1,000 in credits. 12 months subsidized pricing." Enterprise plans include forward-deployed engineers. | Careers page dated 2024-08-24 lists "Member of Technical Staff - ML Evals", "Member of Technical Staff - Honcho Core Engineer", and "Member of Technical Staff - Forward Deployed Engineer"; whether these are open today is unverified | [Honcho home page](https://honcho.dev/); [Careers](https://plasticlabs.ai/blog/careers/Working-at-Plastic) |
| MemOS (MemTensor) | Partner logos shown (Alibaba Cloud, China Telecom, Trip, Anker, Haier, and others); no program text | A recruitment portal is linked; its roles were not read (unverified) | [MemOS site](https://memos.openmem.net/); [MemTensor site](https://www.memtensor.cn/) |
| Hindsight (Vectorize) | No program. "We offer hands-on implementation services, team training, and architecture consulting to get your agents learning faster." | Only generic categories (full-stack, backend, infrastructure, machine learning, and operations engineers; product; sales); "Competitive compensation and equity"; remote-first | [Vectorize home page](https://vectorize.io/); [Careers](https://vectorize.io/careers) |
| Letta | No partner page (404); customer case studies only | "Research Engineer / Scientist, Memory", "Research Engineer / Scientist, Post-Training", "Research Engineer / Scientist, Self-Improvement", "Software Engineer, Agent Harness" (San Francisco) | [Join us](https://www.letta.com/join-us/) |
| Synth | None found | None found | [Synth home page](https://www.usesynth.ai/) |
| Tellurio | None found | None found | [Tellurio home page](https://tellurio.ai/) |
| LangWatch | Partner program with published terms. Referral partners: "20% commission on the first annual license", "No upfront investment". Reseller partners: "Revenue share up to 45%", "Dedicated support per customer", "Advanced technical training". Aimed at partners "across Europe and Latin America". A partnership with adesso was announced on 2025-03-27. | The careers site is a Notion page that did not render; roles unverified | [Partner program](https://langwatch.ai/partners); [Blog index](https://langwatch.ai/blog); [Careers](https://langwatchcareers.notion.site/langwatchcareers) |
| Not Diamond | None found | The about page lists six open positions including "Enterprise Technical Account Engineer", "Forward Deployed Engineer", and "Member of Technical Staff"; the careers page did not render | [About](https://www.notdiamond.ai/about); [Careers](https://notdiamond.notion.site/) |
| TypeSafe (Jev) | None found | Read from the job board's programming interface: "Member of Technical Staff, Model Capabilities" (description mentions evaluation and optimization), "Member of Technical Staff, Backend/Platform", "Member of Technical Staff, Infrastructure (Kubernetes Specialist)", "Developer Advocate", "Founding Marketer", and "Member of Staff" under "Create your own role"; all in the San Francisco office, five days a week in person | [Job board](https://jobs.ashbyhq.com/typesafe-ai); [Job board data](https://api.ashbyhq.com/posting-api/job-board/typesafe-ai); [Team page](https://www.typesafe.ai/team) |
| PrismML (Bonsai) | None found ("Supported organizations" shown as logos) | "Senior AI/ML Engineer, Post-Training Platform", "Senior AI/ML Engineer, Forward Deployment", "Staff AI/ML Engineer, Large-Scale Systems", "Senior AI/ML Engineer, Kernel Optimization", "Staff AI/ML Engineer, Edge & Consumer AI", "AI/ML Engineer, Developer Relations", "Technical Recruiter" (Pasadena or San Francisco) | [Careers](https://prismml.com/careers) |
| Osmosis (Gulp AI Inc.) | None found | No titles listed; "If you want to work on the bleeding-edge of technology and help shape how AI agents improve, we'd love to talk." | [About](https://osmosis.ai/about) |
| Adaptive ML | A partnership with Hewlett Packard Enterprise was announced in April 2025 (post title: "HPE Partners with Adaptive ML to Deploy Reinforcement Fine-Tuning in its Private Cloud AI Offering"); customer announcements for AT&T and Manulife | The about page says "14 jobs" on an external board; titles were not read (unverified). The team now sits inside Datadog. | [Media list](https://www.adaptive-ml.com/blog?category=Media); [About](https://www.adaptive-ml.com/about) |
| Distyl | None found; services-led deployments | Read from the job board's programming interface: 24 roles, including "AI Engineer, Evaluation", "Research Engineers, Agents" (description mentions memory), "Applied AI Researcher, System Self-Improvement", "Applied AI Researcher, Benchmarking", "Applied AI Researcher, System Discovery" (description mentions harness), and "Applied AI Researcher, Post-Training"; San Francisco, London, and New York. The careers page promises "Competitive salary and meaningful equity". | [Job board data](https://api.ashbyhq.com/posting-api/job-board/Distyl); [Careers](https://distyl.ai/careers) |

Counts: two companies publish partner terms (Cognee and LangWatch). Five
publish a startup credit or discount program (Mem0, Supermemory, Honcho,
Zep, Cognee). Ten of seventeen have at least one open role whose title or
description names agent memory, evaluation, harness, or self-improvement
work (Mem0, Zep, Supermemory, Honcho as of 2024, Letta, Not Diamond in
part, TypeSafe, PrismML in part, Distyl, and Vectorize in generic form).

## Path (a): own startup

### What comparable companies raised and what they sold first

All sources read 2026-09-18. Stars, licenses, and repository creation
dates come from the GitHub programming interface on that date.

| Company | First or seed round | First paid product, as sold today | Open-source signal |
|---|---|---|---|
| Supermemory | $3 million, 2025-10-06 | Hosted plans: Free $0 with $5 of credits, Pro $19, Max $100, Scale $399 per month, Enterprise custom; every call draws from a monthly balance ([pricing](https://supermemory.ai/pricing)) | MIT, 30,219 stars, repository created 2024-02-27 ([repository](https://api.github.com/repos/supermemoryai/supermemory)) |
| Cognee | $7.5 million seed, 2026-02-19 | Cloud: Free with 1 million tokens; Standard $1.00 per million tokens plus $5 per additional workspace; Enterprise as a bring-your-own-cloud engagement ([pricing](https://www.cognee.ai/pricing)) | Apache 2.0, 30,812 stars, created 2023-08-16 ([repository](https://api.github.com/repos/topoteretes/cognee)) |
| Hindsight (Vectorize) | $3.6 million seed, April 2024, raised before Hindsight existed | Hindsight Cloud, pay as you go: retain $10.00 per million tokens, recall $0.75 per million, reflect $0.05 per call, storage $0.25 per million tokens per month; self-hosted free ([pricing](https://vectorize.io/pricing)) | MIT, 23,900 stars, created 2025-10-30 ([repository](https://api.github.com/repos/vectorize-io/hindsight)) |
| Letta | $10 million seed, 2024-09-23 | Letta Cloud: Free; Pro $20 per month; developer plan $20 per month plus $0.10 per active agent per month plus $0.00015 per second of tool execution; Teams $20 per seat; Enterprise ([pricing](https://docs.letta.com/letta-code/pricing)) | Apache 2.0, 24,789 stars, created 2023-10-11 ([repository](https://api.github.com/repos/letta-ai/letta)) |
| Honcho (Plastic Labs) | $5.4 million pre-seed, announced 2025-05-10 | Usage: ingestion $2.00 per million tokens; reasoning from $0.001 to $0.50 per query by depth ([Honcho](https://honcho.dev/)) | GNU Affero General Public License version 3, 7,244 stars, created 2023-09-10 ([repository](https://api.github.com/repos/plastic-labs/honcho)) |
| Mem0 | $24 million, October 2025 (reported by Y Combinator's page; the round name is not stated there) | Platform: Hobby free, Starter $19, Pro $249 per month, Enterprise custom, metered in add and retrieval requests ([pricing](https://mem0.ai/pricing)) | Apache 2.0, 65,598 stars, created 2023-06-20 ([repository](https://api.github.com/repos/mem0ai/mem0)) |
| LangWatch | €1 million pre-seed, 2025-02-25 | Developer €0; Growth €29 per core seat per month with 200,000 events included; Enterprise ([pricing](https://langwatch.ai/pricing)) | Apache 2.0, 4,815 stars, created 2023-09-09 ([repository](https://api.github.com/repos/langwatch/langwatch)) |
| Zep | Amount unverified | Zep Cloud: free 10,000 credits per month; Flex $125 per month with 50,000 credits; Flex Plus $375 with 200,000 credits; Enterprise ([pricing](https://www.getzep.com/pricing)) | Graphiti Apache 2.0, 30,990 stars, created 2024-08-08 ([repository](https://api.github.com/repos/getzep/graphiti)) |
| Adaptive ML | $20 million seed, 2024 | Adaptive Engine, an enterprise platform with no public price ([seed post](https://www.adaptive-ml.com/post/adaptive-raises-seed)) | Not open source |

Observed: in every verified case, the first paid product was a hosted,
usage-metered version of the same engine that is free to self-host. The
verified first rounds of the memory and evaluation companies range from
€1 million to $10 million. The larger rounds ($20 million for Adaptive ML,
$24 million for Mem0) went to a training-infrastructure company founded by
a known model team and to the repository with the most stars.

Inferred: for Loop Engine, the comparable sequence is open-source traction
first, then a small round, with the hosted tier (hosted intelligence and
hosted compute, as the packaging tiers guide describes them) as the first
paid product. The metering units are already defined, which the landscape
record noted is rare (only one vendor publishes a never-metered list).

Assumed: the owner's time is the main capital; no outside money exists
today; the first customer would be a team that already runs agents and
wants verified completions rather than more memory.

What the path depends on (observed in the roadmap): a cloud account
(S-4.4), a payment provider (S-4.5), a package index account (S-4.6), and a
frontier model key for unseen-task runs (S-3.5). All four are owner-only
resources. A company registration, a bank account, and a legal review of
the license and terms are also needed and are not in the roadmap.

## Path (b): partnering

### Programs found

Observed (sources in the table above, read 2026-09-18):

- Cognee runs a partner program that accepts integration partners, agent
  and framework partners, implementation partners, and education partners,
  and gives priority technical support, cloud credits for pilots, and
  exposure to its community. Applications are answered within a week.
- LangWatch runs a partner program with published money terms: 20 percent
  commission on the first annual license for referrals, and revenue share
  up to 45 percent for resellers, aimed at Europe and Latin America.
- Mem0, Supermemory, Honcho, Zep, and Cognee run startup programs. These
  give credits or discounts to a young company that uses their product;
  they do not pay the partner.
- Adaptive ML announced a distribution partnership with Hewlett Packard
  Enterprise before its acquisition, which shows that a post-training
  vendor sells through a hardware and cloud partner rather than a
  developer program.
- No program of any kind was found at Hindsight (services instead), Letta,
  Synth, Tellurio, Not Diamond, TypeSafe, PrismML, Osmosis, MemTensor
  (logos only), or Distyl.

### What an integration with Loop Engine would look like

Inferred from the programs above and from Loop Engine's own contracts:

| Partner type | Companies | What Loop Engine would supply | Which metering unit applies | Fit |
|---|---|---|---|---|
| Memory vendor as a store adapter | Cognee, Mem0, Supermemory, Zep, Hindsight, Letta, MemOS | An adapter behind the catalog store contract that reads the vendor's memory as candidate Context Intelligence, plus Run History records that say which memory records contributed to a verified completion and which model calls were avoided | Verified completions and avoided model calls on the Loop Engine side; the vendor keeps its own ingestion or retrieval unit | Good. The landscape record's strongest evidence (the SenseLab benchmark) is that memory without outcome-grounded selection hurts; the outcome record is what the vendor lacks. Cognee's integration partner track and cloud credits are the concrete entry point. |
| Evaluation vendor | LangWatch | Independent verification reports and registered deterministic graders exported as evaluation traces; or, in the other direction, reselling LangWatch's evaluations to Loop Engine users | Judgment depth | Workable. LangWatch pays 20 percent on referrals and up to 45 percent as a reseller, which is revenue without a hosted service of one's own; the same terms cut the other way once Loop Engine has a hosted judgment service that LangWatch partners could resell. |
| Optimization vendor | Tellurio, Synth | A shared frozen suite and honest coverage reports; a Loop Engine configuration grid run inside their optimize hours | Optimize hours | Unclear. No program was found at either company; Tellurio's repository could not be found through the GitHub programming interface today. |
| Routing or typed-decision vendor | Not Diamond, TypeSafe | A route behind the model call boundary; Loop Engine records whether a model call was needed at all | Avoided model calls | Complementary. Not Diamond prices its fee below the savings it claims, which is the same shape as the avoided-model-call unit; TypeSafe's typed decisions match the judgment model kind in the model ontology. No program was found at either. |
| Services-led deployer | Distyl, Osmosis, Adaptive ML (now Datadog) | Loop Engine as the run, verification, and record layer inside an engagement | Verified completions | Possible only through a direct engagement; no program exists. |

Constraint that every partner must accept (observed in the packaging tiers
guide): outcome and verification records, exports, and refusals are never
metered, and prompt bodies never enter the metering ledger.

What the path depends on: a payment method to receive a commission, a
signed partner agreement, and at least one working adapter with a recorded
run. It does not depend on a cloud account, a payment provider integration,
or a frontier model key.

## Path (c): joining for equity

### Who is hiring in this area

Observed (sources in the hiring table above, read 2026-09-18). The roles
whose titles or descriptions come closest to Loop Engine's work:

- Letta: "Software Engineer, Agent Harness" and "Research Engineer /
  Scientist, Self-Improvement" (San Francisco).
- Zep: "Member of Technical Staff: Research", which names evaluation
  harnesses for retrieval, memory quality, and agent task completion, at
  $180,000 to $250,000 and 1.00 percent to 1.50 percent equity.
- Distyl: "AI Engineer, Evaluation", "Applied AI Researcher, System
  Self-Improvement", "Applied AI Researcher, Benchmarking", and
  "Research Engineers, Agents" (San Francisco, London, New York).
- Mem0: "Research Engineer - Agent Memory" (San Francisco).
- Supermemory: "Founding Research Engineers", naming context and harness
  engineering, with remote options.
- TypeSafe: "Member of Technical Staff, Model Capabilities" (San Francisco,
  in person).
- PrismML: post-training platform and kernel optimization roles (Pasadena
  or San Francisco).

Not Diamond, LangWatch, Adaptive ML, and MemTensor list roles on pages that
could not be read today; their fit is unverified. Synth, Tellurio, and
Osmosis list no roles.

### Public evidence about equity norms

| Source | What it says | Status |
|---|---|---|
| Index Ventures, Rewarding Talent handbook ([page](https://www.indexventures.com/rewardingtalent/), read 2026-09-18) | Seed-stage benchmarks from United States startups: a senior engineer 1.00 percent of fully diluted equity, a mid-level engineer 0.45 percent, a junior engineer 0.15 percent. At Series A the handbook sizes grants as a share of base salary: director of engineering 75 percent, senior engineer 50 percent, individual engineer 33 percent. It notes that European candidates are on average more risk-averse than candidates in the United States and may be less willing to compromise on salary, and that grant sizes stay the same in cash terms while the number of options declines as the valuation rises. | Observed on the investor's own page |
| Holloway Guide to Equity Compensation ([section](https://www.holloway.com/g/equity-compensation/sections/typical-employee-equity-levels), read 2026-09-18) | Citing Leo Polovets's 2014 survey of AngelList postings: hire number 1 up to 2 to 3 percent; hires 2 to 5 up to 1 to 2 percent; hires 6 to 7 up to 0.5 to 1 percent; hires 8 to 14 up to 0.4 to 0.8 percent. After a Series A: lead engineer 0.5 to 1 percent, senior engineer 0.33 to 0.66 percent, manager or junior engineer 0.2 to 0.33 percent. The guide stresses these are maximums, "not typical", and that outcomes are "highly situational". | Observed; the underlying survey is from 2014 |
| Zep job postings ([careers](https://www.getzep.com/careers/), read 2026-09-18) | A ten-person company with a Winter 2024 accelerator batch posts 1.00 to 1.50 percent for a research engineer and 1.20 to 1.75 percent for a head of forward-deployed engineering, with salary. | Observed, primary; consistent with the Index seed benchmark for a senior engineer |
| Supermemory job posting ([open roles](https://binary.so/UeNYHHE), read 2026-09-18) | Equity vested in the company, valued by the posting at more than $200,000 and growing, for founding engineers, with senior salary $120,000 to $250,000; no percentage stated. | Observed, primary; the percentage is unverified |
| Distyl and Vectorize careers pages (read 2026-09-18) | "Competitive salary and meaningful equity" ([Distyl](https://distyl.ai/careers)); "Competitive compensation and equity" ([Vectorize](https://vectorize.io/careers)). | Observed; no numbers |
| Carta compensation reports | Three addresses on carta.com returned 403 today. | Unverified; not read |

Inferred: a senior engineer joining a seed-stage company in this area
should expect an offer in the range the Index benchmark and the Zep
postings agree on, roughly 1 percent to 1.5 percent of fully diluted
equity with salary, and a fraction of that at Series A. The value of that
equity depends on outcomes the postings do not state (valuation, option
strike price, vesting, dilution).

Assumed: an employment agreement would assign new inventions to the
employer. The existing Loop Engine code stays available to everyone under
the MIT license, including the owner, but the owner's ability to keep
developing it could be limited by such an agreement. This is a matter for
the specific contract and for legal advice, not for this record.

What the path depends on: none of the owner-only resources. It depends on
the owner's willingness to give up control of the roadmap and on the
outcome of interviews.

## Path (d): licensing

### How comparable open-core companies draw the line

Every license text below was read on 2026-09-18 through the GitHub
programming interface at the repository's default branch, or on the
license's own site.

| Company | Core license | Paid or restricted part | How the line is drawn | Source |
|---|---|---|---|---|
| PostHog | MIT Expat | Everything under the `ee/` directory is under the PostHog Enterprise License | The enterprise directory "may only be used in production, if you (and any entity that you represent) have agreed to, and are in compliance with, the PostHog Subscription Terms of Service" and hold "a valid PostHog Enterprise license for the correct number of user seats"; modifying and publishing patches stays allowed | [LICENSE](https://github.com/PostHog/posthog/blob/master/LICENSE); [ee/LICENSE](https://github.com/PostHog/posthog/blob/master/ee/LICENSE) |
| Infisical | MIT Expat | Everything under any `ee/` directory is under the Infisical Enterprise License | Same wording pattern as PostHog: production use only under the subscription terms with a valid license for the seat count | [LICENSE](https://github.com/Infisical/infisical/blob/main/LICENSE); [backend/src/ee/LICENSE.md](https://github.com/Infisical/infisical/blob/main/backend/src/ee/LICENSE.md) |
| Chatwoot | MIT Expat | Everything under the `enterprise/` directory is under its own license | Same directory pattern | [LICENSE](https://github.com/chatwoot/chatwoot/blob/develop/LICENSE) |
| Twenty | GNU Affero General Public License version 3 | Files marked with the comment `@license Enterprise` are under a commercial license; the development toolkit packages are MIT | A marker comment per file, plus MIT for the pieces that customers embed | [LICENSE](https://github.com/twentyhq/twenty/blob/main/LICENSE) |
| Formbricks | GNU Affero General Public License version 3 | `apps/web/modules/ee` under its own license; client packages MIT | Directory for the paid part, MIT for the client libraries | [LICENSE](https://github.com/formbricks/formbricks/blob/main/LICENSE) |
| n8n | Sustainable Use License | Source files with `.ee.` in the name need an n8n Enterprise License | A filename marker inside a source-available license | [LICENSE.md](https://github.com/n8n-io/n8n/blob/master/LICENSE.md) |
| Sentry | Functional Source License 1.1 with an Apache 2.0 future license | The whole codebase; each version converts to Apache 2.0 two years after release | Time delay instead of a directory; the license site says you "can do anything with FSL software except undermine its producer" | [LICENSE.md](https://github.com/getsentry/sentry/blob/master/LICENSE.md); [license site](https://fsl.software/) |
| Elastic | Elastic License 2.0 | The whole codebase | Three limitations: no providing the software "as a hosted or managed service", no circumventing license keys, no removing notices | [license page](https://www.elastic.co/licensing/elastic-license) |
| Grafana | GNU Affero General Public License version 3 | Hosted cloud and enterprise features | Copyleft plus hosting | [repository](https://api.github.com/repos/grafana/grafana) |
| Supermemory | MIT | Hosted cloud plans | No license change; hosting is the product | [LICENSE](https://github.com/supermemoryai/supermemory/blob/main/LICENSE) |
| Hindsight (Vectorize) | MIT | Hindsight Cloud | No license change; hosting is the product | [LICENSE](https://github.com/vectorize-io/hindsight/blob/main/LICENSE) |
| Mem0 | Apache 2.0 | Platform plans, on-premises and audit features at Enterprise | No license change; hosting and governance are the product | [LICENSE](https://github.com/mem0ai/mem0/blob/main/LICENSE) |
| Letta | Apache 2.0 | Letta Cloud | No license change | [LICENSE](https://github.com/letta-ai/letta/blob/main/LICENSE) |
| LangWatch | Apache 2.0 | Hosted plans and enterprise features | No license change | [LICENSE.md](https://github.com/langwatch/langwatch/blob/main/LICENSE.md) |
| Honcho (Plastic Labs) | GNU Affero General Public License version 3 | Hosted platform | Copyleft plus hosting | [LICENSE](https://github.com/plastic-labs/honcho/blob/main/LICENSE) |

Observed: every memory and evaluation vendor in the landscape that is open
source keeps a permissive or copyleft license on the whole engine and sells
hosting. The companies that restrict a part of the repository do it with a
directory (PostHog, Infisical, Chatwoot, Formbricks), a file marker (Twenty,
n8n), or a time delay (Sentry). No comparable company was found that
relicensed an MIT core to a restrictive license and kept the "MIT core"
description.

### How each pattern would apply to Loop Engine

Inferred, with the packaging tiers guide as the constraint (the engine is
never behind the paid line; governance and hosting are):

| Option | What changes in the repository | What it protects | Cost and risk |
|---|---|---|---|
| Keep MIT for everything and sell hosting (Supermemory, Hindsight pattern) | Nothing | Nothing in the code; the paid value is the operated service, the kept-current intelligence, and the records | Lowest cost. A competitor may host the same code; the moat is the verified records and the reuse they enable, as the landscape record concluded. |
| MIT root with a separately licensed directory for the external intelligence tier (PostHog, Infisical pattern) | A `LICENSE` that names the directory, a directory license that permits production use only with a subscription, and a conformance check that keeps the engine outside that directory | The paid external intelligence tier of requirement R-10 and the governance features | Low cost; well-trodden wording exists. Contributions to that directory need a contributor agreement. The MIT promise for the engine stays intact because the engine never moves into the directory. |
| Keep the paid tier out of the repository entirely and serve it only behind authentication | Nothing in the repository; the tier lives in the hosted service | The same tier, with no license question at all | Lowest legal cost; the packaging tiers guide already describes external intelligence access as authenticated. The risk is that a customer cannot self-host that tier. |
| Time-delayed license for the whole repository (Sentry pattern) | The root license changes | The whole engine for two years per version | Changes the MIT promise, contradicts the "MIT core" position, and would need every contributor's agreement. Not compatible with the current description. |

A legal review is needed before any of these is adopted; this record does
not adopt one.

## Decision criteria

Inferred from the evidence above. "Owner-only resources" means the cloud
account, the payment provider account, the package index account, and the
frontier model key that the roadmap lists as blocking.

| Criterion | (a) Own startup | (b) Partnering | (c) Joining for equity | (d) Licensing |
|---|---|---|---|---|
| Time to first revenue | Longest: needs the hosted proof of concept, a price, and a first customer; every verified comparable sold a hosted tier after open-source traction | Shortest with published terms: a LangWatch referral pays on the first annual license; a Cognee integration gives credits, not cash | Immediate salary on hire; equity value is deferred and uncertain | None by itself; it shapes what (a) and (b) can charge for |
| Capital needed | Comparable first rounds were €1 million to $10 million; before a round, the owner's time plus cloud and model costs | Near zero beyond the owner's time and an adapter | None | Legal review only |
| Control retained | Full until investors join; a lead investor at seed takes a board role in the usual case (assumed, not verified here) | Full over Loop Engine; the partner controls its platform and terms | Lowest; the employer sets the roadmap; new inventions are assigned by contract (assumed) | Full; a license is a unilateral choice until contributors join |
| Dependence on owner-only resources | Highest: all four are required (S-4.4, S-4.5, S-4.6, S-3.5) | Low: a payment method to receive a commission; no cloud account, payment provider, or frontier key is required for an adapter | None | None |
| Risk | Highest: the memory market is crowded and priced to the floor; TensorZero was archived; Adaptive ML exited to an observability vendor | Low; the main risk is that a partner program yields credits and attention but no revenue, or that a partner changes terms | Low financial risk; the risk is to control and to continued work on Loop Engine | Low if a directory or hosted-only pattern is used; high if the root license changes |
| Evidence needed before a decision | A hosted proof of concept with a health endpoint (S-4.4), one recorded paying run, measured avoided model calls on a real task family, and a first customer's willingness to pay in the metering units | One working adapter with a recorded verified completion that names the partner's records; an accepted partner application; one paid referral or reseller deal | A written offer stating salary, equity percentage, strike price, vesting, and the invention assignment clause; a comparison against the benchmarks above | A legal opinion on the chosen pattern; a conformance check that keeps the engine outside any restricted directory |

## Recommendation

This is a research view. The owner decides. The paths are not exclusive,
and the evidence supports a sequence rather than a single choice:

1. Licensing first, because it costs almost nothing and is reversible: keep
   MIT on the engine, decide between "hosted-only" and "separately licensed
   directory" for the external intelligence tier after a legal review, and
   add the conformance check that keeps the engine outside any restricted
   directory. This does not need any owner-only resource.
2. Partnering second, because it is the only path with published money
   terms today and it produces exactly the evidence the other paths need:
   a memory vendor adapter behind the catalog store contract, with Run
   History records that show verified completions and avoided model calls
   on that vendor's memory. Cognee's integration partner track (credits,
   engineer access, a reply within a week) is the concrete entry point,
   and LangWatch's referral or reseller terms are the only cash on offer
   without a hosted service.
3. Own startup only after that evidence exists: a hosted proof of concept
   that answers on a public endpoint, one paying run, and a measured
   avoided-model-call rate on a real task family. Every verified comparable
   raised its first round with open-source traction and sold a hosted tier
   first. The metering units are ready; the accounts are not.
4. Joining for equity as the fallback with the most certain income and the
   least control. The job market for this exact work exists today (Letta's
   agent harness and self-improvement roles, Zep's evaluation harness role
   with a posted 1.00 to 1.50 percent, Distyl's evaluation and
   self-improvement roles). An offer should be compared against the Index
   and Holloway benchmarks and read for its invention assignment clause.

Reasoning: the landscape record showed that no memory vendor executes,
verifies, or keeps executable capability, and that a memory vendor's own
benchmark found memory without outcome-grounded selection harmful. The
cheapest way to prove that Loop Engine's outcome records are worth paying
for is to attach them to a vendor's memory through a partner program and
record the result, not to build a competing memory product. That evidence
raises the value of every other path.

Assumptions behind the recommendation:

- The owner wants to keep developing Loop Engine.
- The owner's time is the main capital and no outside money exists today.
- The roadmap's blocked steps stay blocked until the owner supplies the
  accounts; nothing in this record unblocks them.
- Partner programs will accept a one-author open-source project; Cognee's
  page states no company-size requirement, but acceptance is not verified.
- Nothing here is legal, tax, or financial advice; the license and
  employment questions need a professional.

## Facts that stayed unverified or missing

- Funding amounts for Zep, Not Diamond, TypeSafe, PrismML, Osmosis,
  Distyl, Synth, Tellurio, and MemTensor. Investors are named on the pages
  of Zep, Not Diamond, Osmosis, and Distyl; PrismML's investor comes from
  a headline only.
- The lead investor of Mem0's $24 million round; the accelerator's page
  names three investors without a lead, and Mem0's own pages give
  testimonials without amounts.
- The financial terms of Datadog's acquisition of Adaptive ML; neither
  party disclosed them.
- Any Letta round after the 2024 seed; the March 2026 company post could
  not be fetched at two addresses.
- Current roles at LangWatch, Not Diamond, Adaptive ML, and MemTensor,
  whose careers pages did not render or were not read; and whether the
  2024 Plastic Labs roles are still open.
- Carta's compensation reports, which returned 403 at three addresses.
- Tellurio's repository, which the GitHub programming interface reported
  as not found today, as the landscape record also noted.
- Whether any partner program accepts a project without a registered
  company.

## Sources

Every URL below was read on 2026-09-18.

Repository documents (paths, not links): `LICENSE`,
`docs/research/COMPETITIVE-LANDSCAPE-AND-MONETIZATION-2026-09-18.md`,
`docs/research/BRANDING-OPTIONS-2026-09-18.md`,
`docs/guides/packaging-tiers-and-hosted-service.md`,
`docs/roadmap/FABRIC-ROADMAP-2026-09-18.md`.

Company pages:

- [Mem0 home](https://mem0.ai/), [Mem0 blog](https://mem0.ai/blog), [Mem0 investors](https://mem0.ai/investors), [Mem0 careers](https://mem0.ai/careers), [Mem0 startup program](https://mem0.ai/startup-program), [Mem0 integrations](https://mem0.ai/integrations), [Mem0 pricing](https://mem0.ai/pricing), [Y Combinator page for Mem0](https://www.ycombinator.com/companies/mem0)
- [Zep home](https://www.getzep.com/), [Zep about](https://www.getzep.com/about/), [Zep careers](https://www.getzep.com/careers/), [Zep blog](https://blog.getzep.com/), [Zep pricing](https://www.getzep.com/pricing), [Y Combinator page for Zep](https://www.ycombinator.com/companies/zep-ai)
- [Supermemory home](https://supermemory.ai/), [Supermemory blog](https://supermemory.ai/blog), [Supermemory update post](https://supermemory.ai/blog/an-update-to-supermemory), [Supermemory funding post](https://supermemory.ai/blog/supermemory-raises-3-million-and-building-the-best-memory-engine-for-llms), [Supermemory pricing](https://supermemory.ai/pricing), [Supermemory open roles](https://binary.so/UeNYHHE)
- [Cognee home](https://www.cognee.ai/), [Cognee about](https://www.cognee.ai/about-us), [Cognee careers](https://www.cognee.ai/careers), [Cognee newsroom](https://www.cognee.ai/newsroom), [Cognee seed announcement](https://www.cognee.ai/cognee-raises-seven-million-five-hundred-thousand-dollars-seed), [Cognee partner program](https://www.cognee.ai/consulting), [Cognee pricing](https://www.cognee.ai/pricing)
- [Plastic Labs home](https://plasticlabs.ai/), [Plastic Labs blog](https://plasticlabs.ai/blog), [Plastic Labs posts](https://plasticlabs.ai/blog/posts), [Plastic Labs launch and funding post](https://plasticlabs.ai/blog/posts/Launching-Honcho;-The-Personal-Identity-Platform-for-AI), [Plastic Labs careers](https://plasticlabs.ai/blog/careers/Working-at-Plastic), [Honcho home and pricing](https://honcho.dev/)
- [MemOS site](https://memos.openmem.net/), [MemTensor site](https://www.memtensor.cn/), [MemTensor news](https://www.memtensor.cn/h-col-246.html)
- [Vectorize home](https://vectorize.io/), [Vectorize about](https://vectorize.io/about), [Vectorize careers](https://vectorize.io/careers), [Vectorize pricing](https://vectorize.io/pricing)
- [Letta home](https://www.letta.com/), [Letta blog](https://www.letta.com/blog/), [Letta announcement post](https://www.letta.com/blog/announcing-letta/), [Letta join us](https://www.letta.com/join-us/), [Letta pricing](https://docs.letta.com/letta-code/pricing), [Felicis announcement of the Letta seed](https://www.felicis.com/insight/letta)
- [Synth home](https://www.usesynth.ai/), [Synth blog](https://www.usesynth.ai/blog)
- [Tellurio home](https://tellurio.ai/), [Tellurio blog](https://tellurio.ai/blog)
- [LangWatch home](https://langwatch.ai/), [LangWatch about](https://langwatch.ai/about-us), [LangWatch partners](https://langwatch.ai/partners), [LangWatch blog](https://langwatch.ai/blog), [LangWatch funding post](https://langwatch.ai/blog/langwatch-ai-announcing-1m-funding-round-to-bring-the-power-of-evaluations-to-ai-teams), [LangWatch pricing](https://langwatch.ai/pricing), [LangWatch careers](https://langwatchcareers.notion.site/langwatchcareers)
- [Not Diamond home](https://www.notdiamond.ai/), [Not Diamond about](https://www.notdiamond.ai/about), [Not Diamond blog](https://www.notdiamond.ai/blog), [Not Diamond careers](https://notdiamond.notion.site/)
- [TypeSafe home](https://www.typesafe.ai/), [TypeSafe team](https://www.typesafe.ai/team), [TypeSafe job board](https://jobs.ashbyhq.com/typesafe-ai), [TypeSafe job board data](https://api.ashbyhq.com/posting-api/job-board/typesafe-ai)
- [PrismML home](https://www.prismml.com/), [PrismML about](https://prismml.com/about), [PrismML news](https://prismml.com/news), [PrismML careers](https://prismml.com/careers)
- [Osmosis home](https://osmosis.ai/), [Osmosis about](https://osmosis.ai/about), [Osmosis blog](https://osmosis.ai/blog)
- [Adaptive ML home](https://www.adaptive-ml.com/), [Adaptive ML about](https://www.adaptive-ml.com/about), [Adaptive ML media list](https://www.adaptive-ml.com/blog?category=Media), [Adaptive ML seed post](https://www.adaptive-ml.com/post/adaptive-raises-seed), [Adaptive ML acquisition post](https://www.adaptive-ml.com/post/joining-datadog), [Datadog acquisition announcement](https://www.datadoghq.com/blog/datadog-acquires-adaptive-ml/)
- [Distyl home](https://www.distyl.ai/), [Distyl careers](https://distyl.ai/careers), [Distyl blog](https://distyl.ai/blog), [Distyl job board data](https://api.ashbyhq.com/posting-api/job-board/Distyl)

Equity sources:

- [Index Ventures, Rewarding Talent](https://www.indexventures.com/rewardingtalent/)
- [Holloway Guide to Equity Compensation, typical employee equity levels](https://www.holloway.com/g/equity-compensation/sections/typical-employee-equity-levels)

License sources:

- [PostHog LICENSE](https://github.com/PostHog/posthog/blob/master/LICENSE), [PostHog ee/LICENSE](https://github.com/PostHog/posthog/blob/master/ee/LICENSE)
- [Infisical LICENSE](https://github.com/Infisical/infisical/blob/main/LICENSE), [Infisical enterprise license](https://github.com/Infisical/infisical/blob/main/backend/src/ee/LICENSE.md)
- [Chatwoot LICENSE](https://github.com/chatwoot/chatwoot/blob/develop/LICENSE)
- [Twenty LICENSE](https://github.com/twentyhq/twenty/blob/main/LICENSE)
- [Formbricks LICENSE](https://github.com/formbricks/formbricks/blob/main/LICENSE)
- [n8n LICENSE.md](https://github.com/n8n-io/n8n/blob/master/LICENSE.md)
- [Sentry LICENSE.md](https://github.com/getsentry/sentry/blob/master/LICENSE.md), [Functional Source License site](https://fsl.software/)
- [Elastic License 2.0](https://www.elastic.co/licensing/elastic-license)
- [Supermemory LICENSE](https://github.com/supermemoryai/supermemory/blob/main/LICENSE), [Hindsight LICENSE](https://github.com/vectorize-io/hindsight/blob/main/LICENSE), [Mem0 LICENSE](https://github.com/mem0ai/mem0/blob/main/LICENSE), [Letta LICENSE](https://github.com/letta-ai/letta/blob/main/LICENSE), [LangWatch LICENSE.md](https://github.com/langwatch/langwatch/blob/main/LICENSE.md), [Honcho LICENSE](https://github.com/plastic-labs/honcho/blob/main/LICENSE)

Repository facts (license, stars, creation date, default branch) were read
through the GitHub programming interface at `https://api.github.com/repos/`
followed by the repository name, for: mem0ai/mem0, getzep/graphiti,
supermemoryai/supermemory, topoteretes/cognee, plastic-labs/honcho,
MemTensor/MemOS, vectorize-io/hindsight, letta-ai/letta,
langwatch/langwatch, Tellurio-AI/afnio (not found), PostHog/posthog,
Infisical/infisical, calcom/cal.com, n8n-io/n8n, grafana/grafana,
chatwoot/chatwoot, getsentry/sentry, twentyhq/twenty, and
formbricks/formbricks.

Pages that could not be read today and are therefore not sources:
Carta compensation pages (403 at three addresses), the Distyl newsroom
(404 at two addresses), Letta's March 2026 company post (404 at two
addresses), the Zep and Letta partner pages (404), and the Notion careers
pages of LangWatch and Not Diamond (rendered empty).
