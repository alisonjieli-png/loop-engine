# Pre-packaged intelligence, job-description seeds, and prompt dimensions

Date: 2026-09-18. Owner direction the same day, in short: ship basic
intelligence with the engine (address standardization, name and company
parsing, email and phone validation and recovery, fuzzy duplicate detection,
malformed field detection with correction), organize Context Intelligence
by job description so the questions, facts, and reusable code a person in a
given role, company, country, and language would use can be generated at
scale, and treat prompt construction elements and response-style requests
as dimensions to optimize. This record verifies the candidate sources and
packages, names what each would give the engine, and states what is not yet
known. Every package row was read from the package index and the repository
on 2026-09-18.

## Candidate packages for detection and correction nodes

| Need | Package | Version | License | Repository activity | What it gives a node |
|---|---|---|---|---|---|
| United States address components | `usaddress` | 0.5.16 | MIT | datamade, 1,637 stars, pushed 2025-08-07 | Conditional random field parsing of unstructured United States addresses into typed components |
| United States postal standardization | `usaddress-scourgify` | 0.7.1 | MIT | 243 stars, pushed 2026-08-07 | Cleaning to USPS Publication 28 and RESO conventions, built on `usaddress` |
| International address parsing | `postal` (bindings to libpostal) | 1.1.11 | MIT | openvenues/libpostal, 4,890 stars, pushed 2026-05-13 | Statistical parsing and normalization of addresses in many countries; needs the C library and its data files |
| Person and company names | `probablepeople` | 0.5.6 | MIT | datamade, 622 stars, pushed 2025-05-15 | Parses romanized names and company names into components |
| Person names | `nameparser` | 2.3.0 | LGPL | not checked | Splits a human name into title, first, middle, last, suffix |
| Phone numbers | `phonenumbers` | 9.0.39 | Apache-2.0 | 3,773 stars, pushed 2026-09-18 | Google's numbering-plan library: parse, validate, format to E.164 for every region |
| Email syntax and deliverability | `email-validator` | 2.3.0 | Unlicense | 1,448 stars, pushed 2026-06-26 | Syntax and optional deliverability checks with normalization |
| DNS lookups for mail exchangers | `dnspython` | 2.8.0 | ISC | not checked | The lookup `email-validator` uses when deliverability is requested |
| Fuzzy string similarity | `rapidfuzz` | 3.14.6 | MIT | 4,129 stars, pushed 2026-09-12 | Fast similarity metrics for blocking and scoring |
| Phonetic and edit distances | `jellyfish` | 1.2.1 | MIT | not checked | Soundex, Metaphone, Jaro-Winkler, and edit distances |
| Record deduplication with learning | `dedupe` | 3.0.3 | MIT | 4,511 stars, pushed 2025-07-29 | Active-learning entity resolution over records |
| Probabilistic linkage at scale | `splink` | 4.0.17 | MIT | 2,413 stars, pushed 2026-09-18 | Fellegi-Sunter linkage on DuckDB, Spark, and warehouses |
| Record linkage toolkit | `recordlinkage` | 0.16 | BSD-3-Clause | 1,061 stars, pushed 2024-02-21 | Indexing, comparison, and classification steps as a toolkit |
| Standard numbers and codes | `python-stdnum` | 2.2 | LGPL-2.1 | 593 stars, pushed 2026-08-15 | Validation of national identifiers, tax numbers, and many code formats |
| Bank account numbers | `schwifty` | 2026.7.3 | MIT | not checked | IBAN and BIC parsing and validation |
| Countries, subdivisions, languages | `pycountry` | 26.2.16 | LGPL-2.1 | not checked | ISO country, subdivision, language, currency, and script tables |
| Geocoding clients | `geopy` | 2.5.0 | MIT | not checked | Clients for external geocoders; every call is a network effect |
| Language detection | `lingua-language-detector` | 2.2.0 | Apache-2.0 | not checked | Accurate detection on short and mixed text; requires Python 3.12 |
| Language detection, lighter | `langdetect` | 1.0.9 | Apache-2.0 | not checked | Port of Google's detector |
| Dates in many formats | `dateparser` | 1.4.3 | not stated on the index | not checked | Parses dates in many languages and formats |
| Prices and currencies | `price-parser` | 0.5.1 | not stated on the index | not checked | Extracts amount and currency from text |
| Chemistry | `rdkit` | 2026.3.6 | BSD-3-Clause | not checked | Cheminformatics: parsing, canonical forms, descriptors |
| Static embeddings | `model2vec` | 0.9.0 | MIT | 2,210 stars, pushed 2026-09-17 | Small static embeddings; already in the `data` extra |
| Sentence embeddings | `sentence-transformers` | 6.1.0 | not stated on the index | not checked | Embeddings, retrieval, and reranking with larger models |
| Vector columns in Postgres | `pgvector` | 0.5.0 | not stated on the index | not checked | The client side of a server database with vectors |

Two facts worth recording. The package named `pypostal` on the index is
an unrelated letter-mailing client; the libpostal binding is `postal`.
And `nameparser`, `pycountry`, and `python-stdnum` are LGPL, which is
compatible with an MIT engine as a dependency but must be declared as such.

Each of these belongs behind the same typed correction record that text
conformance uses: a proposed value, a confidence, named reasons, and an
outcome of applied, held, escalated, or unchanged. A package that needs a
network call (`geopy`, deliverability checks in `email-validator`) declares
that effect on its capability handshake, and a node that wraps it runs only
under a network permission. None of these packages is a dependency yet;
each becomes an optional extra when its node lands (roadmap step S-1.10).

## Standards the nodes must cite

| Standard | What it fixes | Status on 2026-09-18 |
|---|---|---|
| USPS Publication 28, Postal Addressing Standards | Address elements, last line, delivery line, street suffix abbreviations (Appendix C), secondary unit designators, state abbreviations, business address compression | Current edition dated October 2024 on the USPS Postal Explorer site |
| E.164 | International phone number format | Implemented by `phonenumbers` |
| RFC 5321 and RFC 6531 | Email address syntax | Implemented by `email-validator` |
| ISO 3166, ISO 639, ISO 4217 | Country, language, and currency codes | Implemented by `pycountry` |

## Seeds for job-description intelligence

| Source | Scale | Terms | Why it fits |
|---|---|---|---|
| O*NET 31.0 database (United States Department of Labor) | 1,016 occupations; 18,838 task statements; 74,702 work activity rows; 54,269 job titles; software skills, knowledge, abilities, work context | Creative Commons Attribution 4.0 | Structured tasks and activities per occupation are exactly the seed the owner described: for a person in this role, these are the activities, so these are the questions, facts, and code they use |
| ESCO (European Commission) | 3,039 occupations; 13,939 skills; 28 languages | Free to consult and download; the page read does not state a formal license | Multilingual occupation and skill labels give the country and language axis the owner asked for |

The generation pipeline (roadmap step S-1.11) takes an occupation, its
tasks, a company, a country, and a language, and produces candidate
question forms, facts, and reusable code seeds. Every generated item is a
candidate in Context or Code Intelligence until an independent review
approves it, as the intelligence rules require. Nothing generated becomes
active because it was generated.

## Prompt elements and response style as dimensions

The owner's list of prompt elements maps to slots the prompt resource
bundle already types: task background, context background, atomic
information, inputs and outputs, expectations, and format. The new
dimension is response style: a request for concise answers, for only what
was asked, or for a full answer. A terse style has a measured community
history: the "caveman" prompt family on GitHub (for example
kuba-guzik/caveman-micro, 172 stars, a six-line prompt of 85 tokens
that its author reports outperformed a 552-token original) reduces tokens
by instructing the model to drop filler. The vendor documentation for
Claude lists clarity, examples, structure with tags, role prompting,
thinking, and prompt chaining as the technique families and points to a
living best-practices page. Neither source is evidence about this engine;
both are reasons to make response style a declared axis and measure it on
verified outcomes and tokens (roadmap step S-2.7). The efficiency question
form added on 2026-09-18 already asks whether inputs and outputs are too
big before a step.

## Middleware and microservice hosting

The Core Architecture already separates the three public ports from
internal mechanics, and the host runtime binding records frozen schemas and
callable identities for host-owned operations. The missing pieces for a
microservice deployment are typed request and response records per port,
idempotency keys on effects, and authority propagation across a process
boundary (roadmap step S-2.8). No research source is needed for those; the
existing effect approval and lineage records define what must cross the
wire.

## What was not verified

- Repository activity was not checked for `nameparser`, `jellyfish`,
  `pycountry`, `geopy`, `dateparser`, `price-parser`, `rdkit`,
  `sentence-transformers`, `pgvector`, `schwifty`, or the language detectors.
- ESCO's reuse license was not found on the page read; the download page
  must be read before ESCO data is packaged.
- No package above was installed or run; accuracy claims are the authors'.
- The "caveman" token figures are the author's report, not a measurement
  made here.
