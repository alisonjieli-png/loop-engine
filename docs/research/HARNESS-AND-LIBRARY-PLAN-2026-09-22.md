# Harness and library plan for roadmap steps S-6.38 to S-6.42

Kind: dated research record, prepared by a Claude Code research agent on September 22, 2026 and reviewed before commit. The roadmap remains the only task authority.

Written September 22, 2026. The repository was
read at `5aa224c` on `main`; two commits by other sessions landed during this
work (`230c91e`, `0f1c690`), and the roadmap was read again at `0f1c690`.
This session changed nothing in the repository, made no branch and pushed
nothing. No model was called. No payment, account, key or
provider setting was touched. The only network reads were two
unauthenticated requests to `https://baltor.ai`, two public registry queries,
read-only GitHub API calls and the documentation pages listed in section 11.

## 0. Inputs, labels and dates

Inputs:

- The four research reports in this folder: `HARNESS-FORKS.md`,
  `INDEPENDENT-INSTANCES.md`, `LIBRARY-SOURCES.md` and
  `FAMILIAR-UX-AND-GUARDRAILS.md`. Each verified its
  facts on September 22, 2026. Two of them read the repository at older
  revisions (`74aa21e`, `4249eca`); every repository fact this plan relies on
  was read again at `5aa224c`.
- Roadmap steps S-6.38 to S-6.42 in `docs/roadmap/roadmap.yaml`, their
  dependencies S-6.30 to S-6.33, the delivery packages D-17, D-18 and D-19,
  and the owner actions OWNER-16 to OWNER-18 (read only, at `0f1c690`). The
  two new commits changed no source file this plan relies on; they extended
  the roadmap text of S-6.31, S-6.40, S-6.42 and S-6.45 (finding 12).
- The concurrent, uncommitted note
  `docs/research/LIBRARY-SCALE-AND-PAID-ACQUISITION-READINESS-2026-09-22.md`,
  read for consistency.
- The owner directions of September 22 in the memory notes
  `library-moat-and-growth.md` and `north-star-frontier-harness.md`.
- New checks made for this plan. Section 11 lists each with its page and the
  date read.

Labels used in the text:

- **Observed**: read on September 22, 2026 on the named page, file or API.
- **Reported**: carried from one of the four reports, which observed it on
  September 22, 2026.
- **Author claim**: a number a third party publishes about its own work.
  Baltor has not reproduced it.
- **Decision**: an engineering decision made under the owner's September 20
  direction ("decide, write down the reason, and move on"), with its reason.
- **Owner**: one of the few items only the owner can decide.

The web search allowance of this session was already used up, so every new
fact was read directly from its page or through the GitHub API.

Each step of a task is a discrete cognitive or act step Loop node; its
complete behavioral explanation is in `ASTRA.md`. This plan is about the
separately initialized harness process that performs one such step, the
library that supplies it, and the account that pays for it.

## 1. Answer first

| Step | Recommendation |
|---|---|
| S-6.38 dashboard and account lifecycle | Nine familiar pages. Stripe's portal deep links and Supabase do the billing and identity work. Start with API keys that last 90 days, because today's one-day default breaks every configured harness. |
| S-6.39 search access policy | First close two open doors found today: `provisioning_list` returns the whole library in one call, and search responses and the public capabilities page name the engines and return scores. Then count per account in the existing durable record store: unique item versions downloaded and distinct references seen. |
| S-6.40 ingestion worker | Start with the official protocol server registry in link mode (34,900 entries, open, incremental) behind a licence gate and NVIDIA SkillSpector's static scan, staged as candidates. Review capacity, which needs a model-review allowance, is the real bottleneck. |
| S-6.41 harness run records | One metadata-only step record that names a source for every fact (offered, fetched, loaded, used, accepted). Feed it first from Baltor's own per-step runs and from the harnesses' own OpenTelemetry output, which Claude Code and Codex already redact by default. |
| S-6.42 harness landscape | Turn the scratchpad isolation test into a repeatable repository check at pinned versions, using the bubblewrap runner the engine already has. Support Pi and OpenCode through a package and a plugin. Start both forks as the owner asked, but keep their core changes near zero until a measurement justifies one. |

The three highest-leverage actions (section 9):

1. Prove one fresh harness per step as a repeatable check at pinned versions.
2. Close the open doors and make access and quotas durable.
3. Start registry ingestion in link mode and ask for the model-review
   allowance.

## 2. What changed since the four reports

| # | Finding | Evidence | Effect on the plan |
|---|---|---|---|
| 1 | The whole served library can be listed in one call. | The protocol tool `provisioning_list` and `POST /api/v1/provisioning` with `operation: "list"` return every offered item with no page limit and `metered: false` (`provisioning_server.py` `_list`, `provisioning_mcp.py` `TOOL_OPERATIONS`, `http.py` `_validate_provisioning`; observed at `5aa224c`). | A search window alone protects nothing while this is open. S-6.39 starts here. |
| 2 | Engines and scores are disclosed. | Each search hit carries `score` (the fused rank value) and `modes`; the response names the `backend` (`http.py` `_search`). The public, unauthenticated `GET /api/v1/capabilities` names `sqlite_fts5` and `deterministic_character_hash` (observed live, about 22:40 UTC). | The owner asked that retrieval engines stay private. Remove them from customer and public responses; keep them in operator traces. |
| 3 | The durable store is SQLite on one machine, not Supabase Postgres. | Records live in `SQLiteRecordStore` on the `/data` volume (`storage.py`); `fly.toml` runs one machine; Supabase is used for identity only (`browser_identity.py`, `account_email.py`). | `FAMILIAR-UX-AND-GUARDRAILS.md` proposed Supabase Postgres for counters. Decision: keep counters in the existing record store beside the durable usage records, and add a release check that refuses a second machine while counters are machine-local. Reason: one store, one transaction with the usage write, no new dependency; D-05 is the recorded path to shared records. |
| 4 | Key lifetime has a hard ceiling. | `_validate_limits` in `access.py` refuses a maximum above 2,592,000 seconds (30 days); the customer policy defaults to 86,400 seconds (one day) and allows 604,800 (seven days). The Account page asks for "Expires after (minutes)" and says "client token". | The 90-day and one-year choices in `FAMILIAR-UX-AND-GUARDRAILS.md` need the ceiling raised under a new policy record version. |
| 5 | Search has no offset. | A request may ask `top_n` from 1 to 50 and cannot page (`http.py`). | The harvesting path is many distinct queries, so count distinct references per account, not offsets. |
| 6 | Harness versions moved today. | The isolation test ran Pi 0.73.1 under the old package name `@mariozechner/pi-coding-agent`; Baltor pins `@earendil-works/pi-coding-agent` 0.85.1 in `embodiments/pi`; upstream released Pi v0.87.1 at 19:43 UTC. OpenCode was tested at 1.18.32; `embodiments/opencode` pins 1.17.9. Codex was tested at 0.155.1; upstream released 0.156.0 at 19:51 UTC. | A loading result binds to one exact version. The Pi result does not yet cover the pinned version. |
| 7 | Claude Code has a documented clean mode. | The headless page says `--bare` skips hooks, skills, custom commands, subagents, plugins, protocol servers, auto memory and `CLAUDE.md`; it is "the recommended mode for scripted and SDK calls" and "will become the default for `-p` in a future release"; it needs an API key because it never reads the subscription login. Without `--bare`, `-p` runs a project's hooks and `.mcp.json` servers with no trust prompt. | Decision: `--bare` with explicit flags is the primary Claude Code recipe. The `CLAUDE_CONFIG_DIR` recipe that `INDEPENDENT-INSTANCES.md` proved stays the fallback for people who sign in with a subscription. Reason: bare mode is documented, deterministic and future-default, and it closes the hook and server start-up risk. |
| 8 | The engine already has isolation machinery. | `harness_process.py` starts each harness in bubblewrap with `--unshare-all --clearenv`, a private `HOME=/work/home`, a private `/tmp`, read-only software mounts and a broker socket that records every model request before forwarding it. `node_provisioning.py` writes the step folder and records what was offered and withheld. `instance_instructions.py` already writes a `CLAUDE.md` that imports `AGENTS.md`. The closed style list in `HarnessProcessSpec` has no Claude Code entry. | S-6.42 needs recipes and proof, not new isolation code. |
| 9 | The owner asked to start building both forks; the research advises no hard fork now. | S-6.50 evidence: "The owner asked to start building both forks". `HARNESS-FORKS.md`: do not hard-fork now; if forking, fork Pi. | Resolution in section 7: start both as thin forks whose Baltor behavior lives in a package or plugin, with a ratchet on changed upstream lines. |
| 10 | "Search is free" is superseded. | The September 20 decision table in `CLAUDE.md` says search is free; the September 22 direction says search is for paying users with a small free quota. | Update the decision table when the policy ships. |
| 11 | Maintained scanners for malicious skills exist. | NVIDIA SkillSpector (Apache-2.0, 18,108 stars) has a static mode with no model call and a batch scanner. Snyk agent-scan (Apache-2.0) sends material to Snyk's analysis service and needs a Snyk token. A February 2026 study of 98,380 skills confirmed 157 malicious ones and says its dataset and detection pipeline are public (arXiv 2602.06547). | SkillSpector's static mode is the first safety engine for S-6.40 and S-6.45; the study's dataset and SkillSpector's own fixtures are the first candidates for the regression set, after a licence check. |
| 12 | The roadmap grew while this plan was written. | Commit `0f1c690`: S-6.31 now requires "a qualification ladder recorded for each harness: connected, material listed, material loaded, step finished, independently accepted" and "a fresh process for each step rather than a reused session"; S-6.40 requires "a versioned per-source provenance contract for outside material" and "a multi-file package contract for skills"; S-6.42 adds ZCode through its app-server path; S-6.45 adds validation of every rendered `SKILL.md` with the reference validator. | The plan uses the ladder for harness classification, drops a warm shared OpenCode server as a way to run steps, and makes the registry candidate record the first instance of the provenance contract. |

## 3. S-6.38 A familiar customer dashboard with the full account lifecycle

Roadmap: paid-only pages; renew an expired subscription, update payment,
cancel, delete the account, export data; usage, request log and trace views;
connection, query, protocol and key handling that feel familiar. Adversarial:
a cancelled or expired account loses paid pages and paid search at once; a
deleted account leaves no usable key; an export never includes another
tenant.

### Current state (observed at `5aa224c`) (S-6.38)

- One page serves `/`, `/app`, `/login`, `/signup`, `/account`, `/admin`,
  `/connect`, `/examples`, `/security`, `/docs`, `/how-it-works` and
  `/pricing` (`web_pages.py`).
- Keys: called "client tokens"; shown once; revocable; prefix `le_`; at most
  10 active; one-day default, seven-day maximum, 30-day ceiling (`access.py`,
  `index.html`).
- Billing: Checkout sessions, and a portal session limited to `customer`,
  `configuration` and `return_url` (`stripe_sessions.py`). A webhook ledger
  moves a tenant between metadata access and body access with `valid_until`
  (`billing.py`).
- Usage: `GET /api/v1/usage` returns totals per unit (`runtime.py`
  `usage_for`).
- Missing: data export, account deletion, request log page, usage charts,
  trace page.

### Recommended design (S-6.38)

- Nine pages named as users of Context7, OpenRouter and Vercel expect
  (`FAMILIAR-UX-AND-GUARDRAILS.md` 4.1): Overview, Connect, API keys, Library, Usage, Logs, Traces,
  Billing, Settings. Paid-only: the Library beyond the free window, Traces,
  and history older than seven days. Export and deletion are never paid-only.
- Stripe does the billing work through portal deep links, one button per
  task (observed on Stripe's deep-link page): `payment_method_update`,
  `subscription_cancel` (needs the subscription identifier),
  `subscription_update` and `customer_update`, each with an
  `after_completion` redirect back to Billing. The server fills the customer
  and subscription from the tenant record and never from the request.
  Resubscribe after a full cancellation starts a new Checkout on the same
  customer, because Stripe cannot reactivate a cancelled subscription
  (Reported).
- Supabase does identity: sign-in, multi-factor authentication with `aal2`
  for sensitive actions (Reported), and server-side `auth.admin.deleteUser`,
  which needs the service role key and must run only on a server (observed).
  Decision: hard delete, not soft delete. Reason: soft deletion is also
  irreversible and keeps a hashed identifier that has no product use.
- Baltor builds three things itself: Resubscribe, Export my data and Delete
  my account. Export and deletion share one implementation with the tenant
  export and deletion drill already on the roadmap (D-15-T04, S-6.6), so the
  service has one data lifecycle, not two.
- Deletion order: step up (fresh sign-in, or `aal2` when enabled); revoke
  every key; cancel billing at once; delete tenant records, usage history
  and run records; delete the identity; send a confirmation email. Keep the
  Stripe customer and its invoices (`FAMILIAR-UX-AND-GUARDRAILS.md` decision; reason: invoices are
  accounting records and a deleted Stripe customer cannot be restored). How
  long they are kept is the owner's legal decision.
- Connection follows the common pattern (`FAMILIAR-UX-AND-GUARDRAILS.md` 3.2): one remote protocol
  endpoint with `Authorization: Bearer` and the key read from an environment
  variable (`claude mcp add ... --header`, Codex `bearer_token_env_var`,
  OpenCode `{env:VAR}`). Later: OAuth sign-in for the protocol endpoint (the
  service already publishes `/.well-known/oauth-protected-resource`) and a
  `baltor setup` command in the style of `npx ctx7 setup`.

### What to reuse (S-6.38)

- Outside: the Stripe customer portal and its flows, Smart Retries and
  entitlement events (Reported); Supabase admin deletion and multi-factor
  authentication; naming and page layout from Context7, OpenRouter and
  Vercel (Reported).
- Inside: the webhook ledger (`billing.py`), the access service
  (`access.py`), usage totals (`runtime.py`), the promotion path that grants
  invited beta users Pro through an operator entitlement, the account email
  sender (`account_email.py`), and the OAuth protected resource routes.

### First increment: API keys that last (S-6.38)

Why first: the private beta (D-17) needs personal keys that a harness can
keep. Today a configured harness stops working after one day by default and
after seven days at most.

1. Write the known-wrong checks below first; the lifetime and naming checks
   fail today.
2. Call them API keys in every customer-facing place: the Account page, Get
   started and the client recipes. Internal identifiers keep their names.
3. Offer expiry choices of 30, 90 and 365 days, default 90, in a new version
   of the customer access policy record, so an older release refuses a policy
   it cannot enforce. The administrator policy is unchanged.
4. Show created, last used, expiry and scopes. Keep show-once and immediate
   revocation.
5. Send a reminder seven days before expiry through the existing account
   email sender.
6. Add `GET /api/v1/account/key`, authenticated by the key itself, returning
   the plan, entitlement state, expiry and, after S-6.39, the remaining
   allowances. It never returns key material.
7. Optional in the same increment: a distinctive prefix for new keys (for
   example `baltor_sk_` plus a checksum) so a leaked key is easy to spot, as
   Context7 does with `ctx7sk-` (Reported). Current `le_` keys expire within
   seven days, so no compatibility reader is needed.

Next increments, in order: the Billing page with the deep links, Resubscribe
and a past-due banner; Export and Delete with step-up; the Usage and Logs
pages; the Traces page once S-6.41 records exist.

### Known-wrong checks (S-6.38)

| Check | Known-wrong case | Required result | Guard removal that must make it fail |
|---|---|---|---|
| Key lifetime policy | A key requested for 90 or 365 days (fails today with `access_lifetime_exceeded`) | Accepted only from the allowed set after the change; 400 days refused | Accept any lifetime |
| Expired key | A key past `expires_at` | Refused on the next request with a named code | Skip the expiry comparison |
| Ended plan loses paid access at once | `customer.subscription.deleted` delivered in Stripe test mode | The next search above the free window, the next download and the paid pages refuse for the same key | Read entitlement from a cache without revalidation |
| Cancel at period end | Clock moved past `valid_until` while `cancel_at_period_end` is true | Access continues until the date and is refused at the first request after it | Compare against the wrong field |
| Portal bound to the caller | A portal request that names another customer or subscription | The server ignores request identifiers and uses the tenant record | Take the customer from the request |
| Deleted account leaves no usable key | Deletion of a disposable account | Every key of the tenant refused, the identity cannot sign in, tenant rows gone | Delete the identity but not the keys |
| Export holds one tenant | Two seeded tenants | Tenant A's archive has no row, digest or key identifier of tenant B | Drop the tenant filter |
| Export and deletion stay free | A cancelled account | Both still work | Apply the paid-page gate to Settings |
| Step-up | A sign-in older than the step-up window | Deletion, export and key creation refused | Skip the freshness check |
| Key never shown again | List and status endpoints | No key material in any response or stored record | Return the stored secret |
| One name | Customer-facing pages and recipes | "API key" everywhere, "client token" nowhere (fails today) | Restore the old wording |

### Owner decisions (S-6.38)

- **Owner**, OWNER-16 (already open): the legal entity, the contact address,
  and approval of the terms and privacy text. Add to that text what an
  export contains, what deletion removes, and how long invoices and the
  billing ledger are kept after deletion. Retention is a legal commitment.
- **Owner**, one standing approval: that engineering may delete disposable
  test accounts it creates for live lifecycle checks. The recorded authority
  asks before deletions, and a deletion drill on the live site deletes an
  identity and cancels a subscription.
- Not needed: a live charge. Flows that need a paid subscription are
  qualified in Stripe test mode. On the live site, engineering checks the
  flows that need no subscription (payment method and billing details) for an
  engineering test customer, and checks that entitlement changes take effect
  through the operator entitlement. A real paid run is optional and only at
  the owner's request.

## 4. S-6.39 Search access policy: protect the library, with a free quota

Roadmap: search limited to paying users, with a small view for others; a
free tier with a limited key; rate and volume limits per key and per address;
retrieval engines and rankings never exposed. Adversarial: a client that
pages through search to list the whole library is refused before it sees
more than its allowance; a free key over quota is refused with the reason and
the upgrade path.

### Current state (observed at `5aa224c` and live) (S-6.39)

- Any signed-in caller with the metadata scope can search, up to 50 results
  per query (live capabilities: `limits.search_results = 50`).
- `provisioning_list` returns the whole offered library in one unmetered
  call (finding 1).
- Scores, modes and engine names are disclosed (finding 2).
- The only limiter counts refused sign-in attempts per address and states
  its own scope as `memory_of_one_service_process` (`request_limits.py`).
- Each search rebuilds a retriever over the tenant's whole listing
  (`http.py` `_search`). That is also a scale limit for S-6.32 and S-6.52.

### Recommended design (S-6.39)

- One typed, versioned host record, `search_access_policy/v1`, holding for
  each plan: results per query, searches per day and per month, distinct
  references per 30 days, unique item versions downloaded per month,
  requests per minute per key, and active keys. It is the setting of an
  access-policy engine slot (S-6.30), so a later counter engine (for example
  a shared store) replaces one adapter, not the call sites.
- One enforcement point. The web routes and the protocol tools already meet
  in `DurableProvisioningBinding.invoke_for_principal`; the search route
  calls it too. A quota checked in one entry point and not the other is the
  first thing a harvester finds.
- Two counting units, with reasons:
  - Bodies: unique item versions downloaded per account per month. A repeat
    download of the same version is free, so a fresh harness per step that
    fetches the same item again is not punished (`FAMILIAR-UX-AND-GUARDRAILS.md` 4.5).
  - References: distinct item references returned per account in a rolling
    30 days, counting search, listing and browsing alike. A real user's
    distinct count levels off at the items their work needs; a harvester's
    grows with every query. This separates the two even when each query is
    small.
  - Quotas belong to the account, not the key.
- Listing: a customer's `list` returns their own shelf (items they fetched
  or pinned), paged. The whole-catalogue listing becomes an operator
  operation. Browsing by the four layers, which the September 20 decisions
  give signed-in users, counts against the same reference allowance, with a
  page window.
- Responses carry references and short descriptions. They never carry
  scores, fusion values, mode lists or engine names. A coarse match label
  (good, fair, poor) replaces the score, so S-6.32 can still report a poor
  match honestly. Public capabilities describe search in plain words without
  naming engines. Operator traces keep the full detail.
- Refusals: HTTP 429 with `Retry-After`; the `RateLimit-Policy` and
  `RateLimit` fields of the current IETF draft
  (draft-ietf-httpapi-ratelimit-headers-11, May 23, 2026, still an
  Internet-Draft, observed); and a body naming the quota, the reset time and
  the upgrade link. Also send the `RateLimit-Limit`, `RateLimit-Remaining`
  and `RateLimit-Reset` fields that Context7 sends (Reported), for clients
  written against them.
- The edge is a coarse outer guard only. Cloudflare counts by header value
  only on Enterprise with Advanced Rate Limiting (observed), so per-key and
  per-account counting belongs in the service.
- Harvesting signals go to a review queue rather than a silent block:
  sequential or dictionary-like query streams, many queries with no
  downloads, and near-total novelty of the references returned.
- The free tier is built and qualified behind a host switch that stays off
  until the owner gives the public-registration go.

Starting settings (Decision: starting values, changed only on recorded
refusal and upgrade evidence; none is a measurement):

| Setting | Free | Pro (29 dollars a month) and invited beta |
|---|---|---|
| Results per query | 10 | 100 |
| Searches | 200 a month, at most 20 a day | Fair use, ceiling 5,000 a day |
| Distinct references per rolling 30 days | 500 | 20,000, with a review flag at 10,000 |
| Unique item versions downloaded per month | 25 | 2,000 |
| Requests per minute per key | 10 | 60 |
| Active keys | 1 | 10 |

All rows except the distinct-reference row come from `FAMILIAR-UX-AND-GUARDRAILS.md` 4.6; that row
is new here. At 20,000 references and 2,000 bodies a month, copying a
one-million-item library would take about 50 paid account-months for the
references and about 500 for the bodies. That is arithmetic, not a claim
about attacker behavior.

### What to reuse (S-6.39)

- Inside: the durable usage record path (`record_usage`, `usage_for`) and
  its idempotent acknowledgment; the tenant concurrency limiter; the host
  record style of `ServiceRequestLimits`.
- Outside: Cloudflare Turnstile on sign-up and free-key creation (free plan,
  Reported); window precedents from Google (100 results), GitHub (1,000) and
  Algolia `paginationLimitedTo` (Reported); the IETF rate limit fields.

### First increment: close the open doors, then count (S-6.39)

1. Write the listing check and the disclosure check first; both fail today.
2. Make a customer's `list` return their own shelf, paged at 50; move the
   whole-catalogue listing to the operator scope and update the protocol
   tool description.
3. Remove `score`, `modes` and `backend` from customer search responses and
   engine names from public capabilities; add the coarse match label and a
   plain limitation sentence.
4. Add durable per-account counters in the existing record store for
   searches, distinct references and unique item versions. Write the download
   counter in the same transaction as the usage record.
5. Install `search_access_policy/v1` with the Pro and invited-beta row
   active and the Free row present but switched off.
6. Return 429 refusals with the headers and body above, and show remaining
   allowances in `GET /api/v1/account/key`.
7. Add a release check that refuses more than one service machine while the
   counters are machine-local.

### Known-wrong checks (S-6.39)

| Check | Known-wrong case | Required result | Guard removal that must make it fail |
|---|---|---|---|
| No whole-library listing | A customer key calls `provisioning_list` on a catalogue larger than one page (fails today) | At most one page of the tenant's own shelf; never an item it has not fetched or pinned | Return every offered item |
| No engine disclosure | Any customer or public response (fails today) | No score, fusion value, mode list or engine name | Add the fields back |
| Harvesting by distinct queries | A scripted client issuing thousands of distinct queries | New references stop at the allowance, known references still return, the account is queued for review | Count searches only |
| Free key over quota | The 201st search in a month; the 26th unique body | Refused with the quota name, reset time and upgrade link; a repeat download of a known version still succeeds | Count repeat downloads |
| Account, not key | A second key on the same account | Shares the same counters | Key-scoped counters |
| Counters survive restart | A restart in the middle of a period | Counts unchanged | In-memory counters |
| One machine while counters are local | A host file declaring two machines | Release check refuses | Skip the check |
| One enforcement point | The same quota through the web route and the protocol tool | Both refuse at the same count | Enforce in one route only |
| Anonymous refused | A search with no key | Refused | Allow anonymous search |
| Free tier off by default | A sign-up without an invitation while the switch is off | Refused | Default the switch to on |

### Owner decisions (S-6.39)

- **Owner**: the public-registration go that turns the free tier on. The
  recorded authority excludes public registration (`CLAUDE.md`, D-17). It
  should follow OWNER-16 (terms and privacy approved) and OWNER-18 (paid
  identity and email plans; OWNER-18 records that the Supabase Free plan
  pauses a project after a week of inactivity and the Resend free plan sends
  at most 100 emails a day).
- **Owner**: the terms-of-service clause that forbids bulk extraction and
  resale (legal text, part of OWNER-16).
- Not needed: the quota numbers, windows, headers and review signals are
  engineering settings.

## 5. S-6.40 Grow the library: a scheduled ingestion worker

Roadmap: scan public repositories, skill directories and plugin and server
registries on a schedule; licence gate (permissive material imported with
its licence and source, other material recreated as original work);
deduplication and quality scoring; every new item a candidate until
independent reviewers approve it; progress measured. Adversarial: no verbatim
import without an accepted licence; no self-approval; duplicates merged.

### Current state (observed at `5aa224c`) (S-6.40)

- The catalogue holds 123 items: 49 reviewed, 43 approved (all by carry),
  6 rejected, 74 not reviewed (`reviews.json`, record
  `starter_catalogue_independent_review/v2`).
- `HostLicensePolicy` accepts MIT only by default; a host file may replace
  the list (`http_entrypoint.py`). `tools/prepare_harness_candidates.py`
  accepts only the repository's own MIT licence and makes no network call.
- `skill_registry.py` parses `SKILL.md` front matter into a searchable card
  and refuses an admission record whose reviewer is the skill itself.
- Supply (Reported, `LIBRARY-SOURCES.md`): about 6.34 million `SKILL.md`, 0.97
  million `AGENTS.md` and 0.79 million `CLAUDE.md` files on GitHub; 34,900
  current official registry entries; in a sample biased toward popular
  repositories, 62 percent permissive and 25 percent with no licence; 9 to 36
  percent exact duplicates.

### Recommended design (S-6.40)

Adopt the slot design in `LIBRARY-SOURCES.md` section 6 (source, fetch, licence
gate, deduplication, quality, recreate and staging engines on an hourly,
daily and weekly schedule, owned by a Practitioner task that never approves
an item), with five changes:

1. Safety engine: NVIDIA SkillSpector in static mode (`--no-llm`, batch scan,
   JSON and SARIF output) is the first engine. Its model stage stays off
   until a model-review allowance exists. Snyk agent-scan is not a default
   engine, because it sends material to Snyk's analysis service, needs a Snyk
   token and starts protocol servers to read their tool lists. The Cisco
   scanner's licence shows as unrecognized on GitHub and needs a file-level
   check before use.
2. The regression set comes before import (S-6.45): the scanner, and every
   later reviewer change, must reject a fixed set of malicious fixtures and
   accept a fixed set of benign ones before any outside body is imported.
3. Candidates are catalog records written through the existing record store
   contracts, not a new database and not more JSON in the repository. Reason: `AGENTS.md` forbids
   parallel stores, and 34,900 entries do not belong in git.
4. Protocol server items are served as generated configuration. For each
   registry entry, Baltor writes the harness-specific configuration (Claude
   Code `.mcp.json`, a Codex `config.toml` table, OpenCode `opencode.json`)
   from registry facts (name, version, endpoint or package) plus its own
   short factual description from a template. No author text is copied, so
   link mode needs no body licence.
5. The worker runs away from the production machine (on the workstation or
   in continuous integration at first). It writes candidates only. The served
   catalogue changes only through the existing release path: review record,
   manifest build, grants.

Decision on counting: every public library number means approved, active
packages; candidate counts stay internal. Reason: S-6.40 publishes size only
from evidence, and the concurrent library-scale note shows that candidates,
approved, loaded and helpful packages are different milestones.

Review at volume stays three layers, each recorded with reviewer names
(`LIBRARY-SOURCES.md` 6): deterministic checks that can only reject; a reviewer
that did not produce the item approves or rejects against the written
criteria; a human spot audit of a random sample decides whether a batch is
served. The owner can withdraw any item.

The component gets its own folder with one module per engine, following
S-6.30's folder rule. A new component folder needs the README, architecture
contract, import-boundary test and `architecture.yaml` entry that `AGENTS.md`
requires.

### What to reuse (S-6.40)

- Official registry: `GET /v0.1/servers` with `version=latest`,
  `updated_since` and cursor paging. Observed: a query with
  `updated_since=2026-09-21T00:00:00Z` returned entries updated on September
  22 and a `nextCursor`.
- GH Archive for change detection and a single GitHub App within GitHub's
  published limits (Reported).
- licensee (MIT) for repository licences; scancode-toolkit (Apache-2.0
  overall, CC-BY-4.0 for its reference data, observed in its README) for
  file-level scans.
- datasketch (MIT) for MinHash with locality-sensitive hashing.
- The Agent Skills specification and `skills-ref validate` as the structural
  gate (observed: `name` 1 to 64 lowercase letters, digits and single inner
  hyphens, matching the folder; `description` 1 to 1,024 characters).
- skills.sh and Smithery APIs for signals only, within their terms
  (Reported).
- Inside: `skill_registry.py`, `tools/stage_intelligence_candidates.py`,
  `tools/build_host_catalogue_manifest.py`, the carry rules of D-17-T06, and
  the S-6.30 engine framework when it lands.

### First increment: the official registry in link mode (S-6.40)

1. Write the checks below first.
2. Source engine `mcp_official_registry`: one full sync, then
   `updated_since`. Keep each raw `server.json` with its fetch time and
   digest as evidence.
3. Normalize each entry into a candidate record that is the first instance
   of the versioned per-source provenance contract S-6.40 now requires:
   origin (the registry and the server name), immutable revision (the
   version with the registry's `updatedAt`), source digest (of the raw
   `server.json`), licence evidence (the repository licence finding from
   licensee, cached) and fetch date. Add transports, endpoint or package
   identifiers, the repository address, duplicate links (exact by name and
   version; Smithery's `ai.smithery/` copies linked to their originals) and
   the template description. Each registry entry carries a status and its
   change time (observed value `active`); a status change or a vanished entry
   withdraws the candidate, or the served item, back to review.
4. Deterministic rejection checks: https endpoints only; no credential or
   token-shaped value in an address or header; package identifiers that
   resolve; a readable repository.
5. Stage everything as `not_reviewed`; nothing enters the served manifest.
6. Record entries, rejections by reason, licence findings and duplicates.
   Publish no size claim.
7. Send a first batch (for example the 500 entries with the strongest usage
   signals) to independent review through the existing path.

Next increments: the multi-file package contract for skills (scripts,
references and assets, each with its own digest and licence evidence), then
the GitHub skills crawl (topic seeds, awesome lists, GH Archive) with the
licence gate, `skills-ref` validation, SkillSpector's static scan and MinHash
merging, where verbatim import uses only the allowed SPDX list, which moves
into the host file; then the Claude Code and Codex marketplace manifests;
then recreation of valuable link-only items, only with a model allowance.

### Known-wrong checks (S-6.40)

| Check | Known-wrong case | Required result | Guard removal that must make it fail |
|---|---|---|---|
| No verbatim import without an accepted licence | A fixture repository with no licence; one with an unrecognized licence and no file-level licence | Outcome link or refuse, never verbatim | Skip the licence gate |
| Proprietary text never imported or recreated | A fixture carrying the source-available licence of the four Anthropic document skills | Refused for verbatim and for recreation | Allow recreation for any link-only item |
| Exact duplicate merged | A byte-identical copy from a second repository | One item; provenance gains the second source | Add it as a new item |
| Near duplicate merged, distinct item kept | A copy with a changed title line; a different skill with a similar name | The first merged, the second kept | Similarity threshold of zero |
| Malicious set rejected | The S-6.45 regression set | Every malicious fixture refused with a named reason; every benign fixture accepted | An accept-all scanner |
| No self-approval | A candidate whose reviewer equals its producer | Refused | Drop the reviewer comparison |
| Staging never serves | A staged batch | The served manifest and grants are unchanged, and customer search returns no candidate | Write into the manifest |
| Withdrawal follows the source | A registry entry whose status changes, or that disappears | The candidate or served item returns to review | Ignore status |
| Incremental sync misses nothing | A weekly full sync compared with the running `updated_since` sync | The same entry set, or the difference recorded | Skip reconciliation |
| Size claims come from the review record | A page that states a library count | Equals the approved count in the review record | Hard-code the count |

### Owner decisions (S-6.40)

- **Owner**: a model-review allowance. OWNER-17 covers measuring the launch
  benefits only, so reviewing and recreating items needs a wider scope or a
  new owner action naming the models and a monthly ceiling. Without it,
  served growth is limited to what the current review process approves by
  hand.
- **Owner**, inside OWNER-16's legal text: a takedown route in the terms for
  authors who object to an item.
- Not needed: the licence allow list, link-only rules and clean-room
  recreation rules are engineering rules that carry out the owner's September
  22 direction; they are not legal advice (`LIBRARY-SOURCES.md` 5). Glama and
  SkillsMP data are not needed, because their terms forbid bulk use or need a
  written agreement and the same material is on GitHub.

## 6. S-6.41 Harness run records for self-improvement

Roadmap: how each harness and step broke a problem down, which items it
loaded and whether the step was accepted; outcomes per model, harness and
item; consent and privacy settings, metadata only by default; records that
feed engine selection and library quality. Adversarial: no raw prompts, code
or data without explicit opt-in; no credential in a record.

### Current state (observed at `5aa224c`) (S-6.41)

- Engine records: `HarnessRunResult` with model call and tool event records
  (`external_harness.py`); outcome vectors; the provisioning record of what a
  step was offered and what was withheld (`node_provisioning.py`).
- Service records: durable usage with request identity; a failure journal
  (`observability.py`).
- Policy already on the roadmap: structural telemetry by default, with raw
  content, embeddings and training reuse behind explicit consent (D-15);
  client-reported telemetry never counts as independent verification
  (S-4.13).
- Missing: a customer step record, a consent setting, and retention and
  export for such records.

### Recommended design (S-6.41)

One versioned record, `harness_step_record/v1`, metadata only, with no free
text:

- Identities: tenant, run, step, parent step, and a digest of the plan that
  shows how the problem was broken down.
- Harness identity and exact version, recipe digest, isolation mode
  (sandboxed, recipe only or unknown).
- Model provider and model identifier as reported; token usage as reported
  or unknown; elapsed and cold-start time.
- Items: for each item identity, version and digest, five separate facts,
  offered, fetched, loaded, used and accepted, each with its source: service
  observed, sandbox observed, harness reported or client reported. The facts
  must nest (used requires loaded, loaded requires fetched, fetched requires
  offered). Only service-observed and sandbox-observed facts may be called
  verified.
- Outcome: accepted by an independent check, rejected, or unknown, with the
  identity of the check.
- Refusal and exit codes.

Sources, in the order to build them:

1. Baltor's own per-step runs (S-6.42). The broker already records every
   model request, so "loaded" can be observed directly: the item's text is in
   the request or it is not.
2. The harnesses' own OpenTelemetry output, collected locally by the Baltor
   client and reduced to the record. Claude Code: `CLAUDE_CODE_ENABLE_TELEMETRY=1`;
   prompts and tool details redacted by default; events such as
   `claude_code.tool_result` and `claude_code.api_request` (observed). Codex:
   an `[otel]` table, off by default, `log_user_prompt = false` by default,
   events `codex.api_request`, `codex.tool_decision` and `codex.tool_result`
   (observed). Pi through its extension events and OpenCode through plugin
   hooks (Reported); the OpenCode command-line page lists no OpenTelemetry
   setting (observed).
3. Export uses the names of the OpenTelemetry generative AI conventions
   (`invoke_agent`, `execute_tool`, `gen_ai.request.model`). They moved to
   the `open-telemetry/semantic-conventions-genai` repository (Apache-2.0)
   and are still marked Development (observed), so pin the version used.

Consent (Decision on the shape; the default is the owner's): service-side
request records are the service's own logs and are kept for the account.
Client-side step records have a per-account setting with three values: off,
metadata, and metadata with content. Content is never collected without its
own explicit opt-in and never used for training without a separate consent.
Step records are included in export and removed by deletion.

First uses, in order: item quality (fetched but never loaded; loaded but
never used; used and accepted); then engine selection evidence under the
D-19 minimum-sample rule; then S-6.51's analysis of items fetched together.

### What to reuse (S-6.41)

Run History and outcome vector records; the durable usage acknowledgment
(S-6.6); the Claude Code and Codex OpenTelemetry events; the OpenTelemetry
generative AI conventions; the secret-shaped text detector in
`instance_instructions.py` for the credential check.

### First increment (S-6.41)

Define the record and its validator, produce records from Baltor's own
no-model loading-proof runs (S-6.42 first increment), store them as Run
History, and show them to the operator. No customer ingestion yet.

### Known-wrong checks (S-6.41)

| Check | Known-wrong case | Required result | Guard removal that must make it fail |
|---|---|---|---|
| No content by default | A prompt, code or data string in any field | Refused unless the account opted into content | Allow free text |
| No credential | A key-shaped or token-shaped value | Refused | Skip the scan |
| Facts nest | "Used" without "loaded", or "loaded" without "fetched" | Refused | Drop the nesting rule |
| Client claims stay client claims | A client-reported acceptance labelled verified | Refused; stored as client reported | Accept labels as sent |
| Fetched matches the service | A record claiming a fetch the service never served to that tenant | Refused | Skip the cross-check against usage records |
| Consent honored | An account with step records off | Nothing stored | Ignore the setting |
| Minimum sample | Evidence below the declared minimum | Ranking and engine order unchanged | Reorder on any evidence |
| Deletion reaches records | Account deletion | No step record of the tenant remains | Leave run records behind |

### Owner decisions (S-6.41)

- **Owner**, inside OWNER-16's privacy text: whether client-side metadata
  records are on by default with a notice and a one-click off switch
  (engineering recommends this; it is common for developer tools) or off
  until the customer turns them on; the retention period (engineering
  proposes 13 months); and whether metadata from consenting accounts may
  improve ranking for all customers in aggregate.

## 7. S-6.42 Harness landscape: forks and independent instances

Roadmap: Pi and OpenCode supported out of the box; forks studied, including
NVIDIA's work on Pi; a measured decision on an own fork; a tested answer for
Codex, Claude Code, OpenCode and Pi on starting an independent instance with
new files for one step. Adversarial: a harness that cannot start an isolated
instance with only the step files is marked unsupported, not assumed to work.

### Current state (S-6.42)

- Loading-level proof with no model call (observed by `INDEPENDENT-INSTANCES.md`):
  Codex 0.155.1, OpenCode 1.18.32 and Claude Code 2.1.280 each put exactly
  the step's instruction file, skill and protocol server into the request, and
  nothing from decoy global files. Pi 0.73.1 did so for instruction files and
  skills and has no native protocol client. The documented configuration
  variable alone leaked for three of the four; an empty `HOME` closed every
  measured leak; Pi and Claude Code also read instruction files above the step
  folder.
- Engine: the bubblewrap runner, confinement record, provisioning writer and
  instruction writer (finding 8); pinned embodiments for Pi 0.85.1 and
  OpenCode 1.17.9; `embodiments/opencode_per_step` and
  `embodiments/process_per_step` are marked planned.
- Research (Reported, `HARNESS-FORKS.md`): Pi over OpenCode for any fork; a Pi
  package and an SDK launcher first; OpenCode through a plugin and inline
  configuration; a research fork only. The owner asked to start building both
  forks (S-6.50).

### Recommended design (S-6.42)

Two launch modes, one recipe record per harness and exact version:

- Engine side (Linux): the existing bubblewrap runner. The sandbox already
  removes the home and parent-folder leaks, so a recipe adds only what the
  harness needs inside it: flags, a configuration folder, switches for
  bundled items.
- Customer side (any operating system, S-6.48): a clean environment, an
  empty `HOME`, the harness's own configuration variable, and the step folder
  as its own git root under a clean parent, as `INDEPENDENT-INSTANCES.md` proved.

Recipes, as starting values to be proven at the pinned version:

| Harness | Recipe |
|---|---|
| Codex | `CODEX_HOME` per step holding `[mcp_servers.*]` and `[skills.bundled] enabled = false`; `codex exec --ephemeral --json`; the step folder as its own git root. |
| OpenCode | `OPENCODE_CONFIG_DIR` and the four `XDG_*` folders per step; `--pure`; `OPENCODE_DISABLE_CLAUDE_CODE=1`, `OPENCODE_DISABLE_AUTOUPDATE=1`, `OPENCODE_DISABLE_MODELS_FETCH=1`. Not a warm `opencode serve` with a session per step: S-6.31 now requires a fresh process for each step rather than a reused session. If start-up time proves costly, that is a measured case for the fork work below. The built-in `customize-opencode` skill always appears and is listed as known. |
| Claude Code | Primary: `claude -p --bare` with `--append-system-prompt-file <step>/AGENTS.md`, `--add-dir <step>` for its `.claude/skills`, `--mcp-config <file>` and `--settings <file>`. Fallback for subscription sign-in: `CLAUDE_CONFIG_DIR` per step, a `CLAUDE.md` that imports `AGENTS.md`, `--strict-mcp-config`, a clean parent or `claudeMdExcludes`, and telemetry off unless the customer chose it. |
| Pi | Primary: the SDK launcher, one `createAgentSession()` per step with `SessionManager.inMemory()` and a custom `ResourceLoader` that supplies exactly the step's skills, context files and extensions (observed on the Pi SDK page). Fallback: `--no-session --no-context-files --append-system-prompt <file> --no-skills --skill <path> --offline` with `PI_CODING_AGENT_DIR` per step. Protocol servers only through an extension, for example `pi-mcp-adapter` (MIT), which also reads a global `~/.config/mcp/mcp.json`, so the empty-home rule must cover it. |
| Agent Client Protocol route (S-6.31) | `session/new` takes an absolute `cwd` that must be used wherever the agent process was started, and a list of protocol servers (standard input and output required; HTTP optional) (observed). One adapter reaches OpenCode, Goose and the registry adapters for Claude Code, Codex and Pi. The process environment still needs the recipe above. |

Support out of the box:

- Pi: a Baltor Pi package (extension plus skills) with `baltor_search` and
  `baltor_load` tools that call the Baltor service with the key from the
  environment, return references first and bodies after selection, and emit
  offered, fetched and loaded events. SoL-Pi (MIT, a standalone extension
  that installs on an unmodified Pi and is pinned to Pi 0.85.1, observed) is
  an optional configuration, off by default, to be measured. Its published
  savings are author claims; on Terminal-Bench it solved fewer tasks than Pi
  (Reported).
- OpenCode: remote protocol server configuration with the key from the
  environment, skills in `.agents/skills`, and a small plugin that emits the
  loaded events.

Forks (Decision, honoring the owner's ask): start both forks now at recorded
upstream revisions with their licences recorded (S-6.50), but put Baltor
behavior in the package or plugin, which the unmodified harness can also
load. A change enters a fork's core only when the extension surface cannot
express it and a comparison on the same frozen tasks shows a gain. Reason:
the owner asked for both forks, and the research shows that the cost of a
fork is the merge work on every changed upstream line (Kilo runs a
30-minute release watcher, a merge agent and a marker check on every changed
line; Reported). Candidate core changes, in order: start-up time per step
(measure it first), a strict mode that loads only a signed manifest (Codex
and OpenCode have no switch to stop `AGENTS.md` walk-up), verified loading
events, and a permission system for Pi. Maintenance rules (Reported): a
marker on every changed upstream line, a `changes.md` beside each changed
folder, a scheduled upstream watcher, and a continuous-integration ratchet on
changed lines that may only fall. Claude Code cannot be forked: its licence
reads "All rights reserved" (observed).

### What to reuse (S-6.42)

- Inside: `harness_process.py`, `harness_confinement.py`,
  `node_provisioning.py`, `instance_instructions.py`, the pinned embodiments.
- Outside: the Pi SDK and extension interface; SoL-Pi; `pi-mcp-adapter`
  (MIT, 1,530 stars); `pi-acp` (MIT, 693 stars); OpenCode `serve` and
  plugins; Claude Code `--bare`; Codex `exec`; the Agent Client Protocol
  registry (Apache-2.0); NVIDIA's ProRL-Agent-Server (Apache-2.0), whose
  launcher presets for six harnesses are prior art for recipe records
  (Reported).
- The scratchpad test kit in `harness-tests/common/`: the decoy layout, the
  capture endpoint, the protocol stub and the one-call proof script.

### First increment: a repeatable loading proof at pinned versions (S-6.42)

1. Move the scratchpad method into a repository check that writes each run
   to a new folder. (The earlier run deleted older files in place; do not
   repeat that.)
2. For Codex, OpenCode, Claude Code and Pi at the exact versions the
   embodiments pin (Pi 0.85.1; move OpenCode's pin to the tested 1.18.32 or
   test 1.17.9; add pins for Codex and Claude Code), run both launch modes
   with three step markers and a broker or capture endpoint that records the
   first request and then refuses it, so no model is called. The
   customer-side mode also plants decoys in a fake home and in a parent
   folder; the engine-side mode checks that only the step markers and the
   listed bundled items reach the request.
3. Record for each harness: step markers present, decoys absent, protocol
   server started, bundled items listed, cold-start time to the first
   request, request size, exact version and recipe digest. Write the result
   as roadmap evidence and as the first `harness_step_record/v1` records.
4. Record each harness on the S-6.31 qualification ladder: connected,
   material listed, material loaded (all three reachable without a model
   call), then step finished and independently accepted (these need the
   one-call proof and later real steps). A harness that has not reached
   "material loaded" is unsupported for one harness per step; one that loads
   instruction files and skills but not protocol servers is recorded as such.
5. Re-run on every pinned-version change. An installed version newer than the
   recipe's is unqualified until proven.

Next increments: the one-call proof that the model used the material (the
existing script refuses to start without owner approval), local model first;
the Pi package and the OpenCode plugin; the customer-side launcher (S-6.48),
including a lead harness that starts a spawned harness process for each step;
then Goose, Crush, Gemini CLI, Hermes Agent and OpenClaw through the same
check, and ZCode through its app-server path with isolation, cancellation and
native loading tested before any support is listed.

### Known-wrong checks (S-6.42)

| Check | Known-wrong case | Required result | Guard removal that must make it fail |
|---|---|---|---|
| Empty home required | Codex with only `CODEX_HOME`; OpenCode without an empty home | Decoy skill appears and the check fails (observed in variant A) | A recipe without the home rule |
| Parent instruction files | Pi without `--no-context-files`; Claude Code without bare mode or excludes; both under a parent with `AGENTS.md` | Decoy appears and the check fails (observed) | Drop the flag |
| Claude Code instruction file | Non-bare Claude Code with only `AGENTS.md` | Step marker absent, so loaded is false (observed) | Count file presence as loaded |
| Discovery is not loading | A protocol tool listed but its material never in the request | Not counted as loaded (D-17-T04) | Count the listing |
| An exit is not loading | A run that returns a session identifier and exit code 0 while the request lacks the step marker | Not counted as loaded (S-6.31 ladder) | Count a clean exit as loaded |
| No protocol server without support | Pi without an extension | Marked unsupported for protocol servers | Assume support |
| Version drift | Installed version differs from the recipe's | Unqualified until re-proven | Ignore versions |
| Parallel instances | Two steps at once | Neither sees the other's skills or servers | Share configuration folders |
| No silent network | Outside connections during a proof run | Refused and recorded | Open network |
| The check can fail | The proof run with `AGENTS.md` deleted | Step marker absent and the check fails | A check that always passes |

### Owner decisions (S-6.42)

- **Owner**: a model-call allowance for the one-call proof. The local Ollama
  model costs nothing but is still a model call under the recorded
  authority; it covers OpenCode, Pi and Codex. Claude Code in bare mode needs
  an Anthropic API key and Codex without a local model needs an OpenAI key,
  so those runs need a small paid allowance. OWNER-17's scope would need to
  include this.
- Not needed: the fork decision, which is engineering's and is recorded
  above.

## 8. Order of work

The roadmap makes S-6.40 wait for S-6.30 and S-6.41 and S-6.42 wait for
S-6.31; both are proposed, not built. Decision: do not wait. The first
increments are checks and one source engine with a typed edge; the framework
can adopt them later without changing a call site, and the loading evidence
is what S-6.31 needs to choose its first engine.

```text
Parallel start (separate files, separate owners)
├── Access and quotas: S-6.39 first increment, then S-6.38 first increment
│   ├── close the list and disclosure doors (their checks fail today)
│   ├── durable per-account counters and search_access_policy/v1
│   ├── API keys that last, key status endpoint
│   └── then Billing deep links, Export and Delete, Usage and Logs pages
├── Harness proof: S-6.42 first increment with S-6.41 record definition
│   ├── loading proof at pinned versions, both launch modes
│   ├── first harness_step_record/v1 records and cold-start numbers
│   └── then one-call proof (owner allowance), Pi package, OpenCode plugin,
│       customer-side launcher, thin forks (S-6.50)
└── Library growth: S-6.45 regression set, then S-6.40 first increment
    ├── registry source in link mode, staged candidates, first review batch
    └── then GitHub skills crawl with licence gate, scan and merge
```

## 9. The three highest-leverage actions

1. **Prove one fresh harness per step as a repeatable check at pinned
   versions** (S-6.42 first increment, with the S-6.41 record). A fresh
   harness per step is the default design and the north star's
   differentiator. The kit exists (the scratchpad tests and the bubblewrap
   runner), so the cost is small. It turns "offered, fetched, loaded" into
   evidence, produces the first step records and the cold-start numbers that
   decide whether a fork is worth its maintenance, and unblocks S-6.44,
   S-6.48, S-6.49, S-6.50 and the D-17 requirement for a native client that
   loads selected material in its own harness.
2. **Close the open doors and make access durable** (S-6.39 and S-6.38 first
   increments). Today one call lists the whole library and the public
   capabilities page names the engines, both against the owner's moat
   direction; the only limiter lives in process memory; and one-day keys
   break harness configurations before the beta can prove anything. The free
   tier, public registration and a larger library all depend on this.
3. **Start registry ingestion in link mode and ask for the model-review
   allowance** (S-6.40 first increment with the S-6.45 regression set). The
   official registry is open, complete and incremental, and link mode copies
   no author text, so it needs no body licence. It moves the library from 43 served items toward tens
   of thousands of reviewable candidates, and it measures the true bottleneck,
   review capacity, in numbers the owner can use to set the allowance.

## 10. Owner decisions in one place

| # | Decision | Steps | Why only the owner | Engineering proposal |
|---|---|---|---|---|
| 1 | Approve the terms and privacy text (extends OWNER-16): export contents, what deletion removes, invoice and ledger retention after deletion, the clause against bulk extraction and resale, a takedown route, and the run-record data policy | S-6.38, S-6.39, S-6.40, S-6.41 | Legal commitment | Engineering drafts each clause for approval |
| 2 | Default for client-side run records: on for metadata with a notice and a one-click off switch, or off until chosen; retention period; aggregate use for ranking | S-6.41 | Privacy commitment | On for metadata with notice, content always opt-in, 13 months |
| 3 | Public-registration go that turns on the free tier | S-6.39 | Outside the recorded authority (D-17) | After decisions 1 and OWNER-18 |
| 4 | Paid identity and email plans (OWNER-18, already open) | S-6.39 | Spending above the allowance | Supabase Pro and Resend Pro before the free tier |
| 5 | Model-call allowance covering item review, recreation and the one-call loading proof (extends OWNER-17) | S-6.40, S-6.42 | Model calls and spending | Local model first at no spend; a small monthly ceiling for review |
| 6 | Standing approval to delete disposable test accounts that engineering creates for live lifecycle checks | S-6.38 | The recorded authority asks before deletions | Only accounts engineering created, each deletion logged |

Everything else in this plan is an engineering decision, recorded with its
reason where it is made.

## 11. Facts checked for this plan

All read on September 22, 2026.

| # | Fact | Source |
|---|---|---|
| 1 | Portal flow types `payment_method_update`, `subscription_cancel` (subscription identifier required), `subscription_update`, `subscription_update_confirm`, `customer_update`; `after_completion` redirect | <https://docs.stripe.com/customer-management/portal-deep-links> |
| 2 | draft-ietf-httpapi-ratelimit-headers-11, May 23, 2026, active Internet-Draft; defines `RateLimit-Policy` and `RateLimit` | <https://datatracker.ietf.org/doc/draft-ietf-httpapi-ratelimit-headers/> |
| 3 | SoL-Pi is a standalone extension that installs on an unmodified Pi, MIT, pinned to Pi 0.85.1; repository created 2026-09-02, 2,899 stars | <https://github.com/NVlabs/SoL-Pi> and GitHub API |
| 4 | Claude Code `--bare` skips hooks, skills, custom commands, subagents, plugins, protocol servers, auto memory and `CLAUDE.md`; recommended for scripts; future default for `-p`; needs an API key; flags to add material back; without it `-p` runs project hooks and `.mcp.json` servers with no trust prompt | <https://code.claude.com/docs/en/headless> |
| 5 | Pi SDK: `createAgentSession()`, `SessionManager.inMemory()` "when the host does not want session files", custom `ResourceLoader` "when the host owns resource storage and discovery completely" | <https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/docs/sdk.md> |
| 6 | Registry `GET /v0.1/servers` with cursor paging; a live query with `version=latest` and `updated_since` returned entries updated on 2026-09-22 and a `nextCursor` (22:33 UTC) | <https://github.com/modelcontextprotocol/registry> (generic API reference) and <https://registry.modelcontextprotocol.io> |
| 7 | Generative AI conventions moved to `open-telemetry/semantic-conventions-genai` (Apache-2.0, created 2026-05-05); agent spans marked Development; operations include `create_agent`, `invoke_agent` and `execute_tool` | GitHub API, `docs/gen-ai/gen-ai-agent-spans.md` |
| 8 | Claude Code telemetry: `CLAUDE_CODE_ENABLE_TELEMETRY`; prompts and tool details redacted by default; event and metric names | <https://code.claude.com/docs/en/monitoring-usage> |
| 9 | Codex telemetry: `[otel]` off by default; exporters `none`, `otlp-http`, `otlp-grpc`; `log_user_prompt = false` by default; `codex.api_request`, `codex.tool_decision`, `codex.tool_result` | <https://learn.chatgpt.com/docs/config-file/config-advanced> |
| 10 | OpenCode: `--pure`, `run --format json --dir --attach`, `OPENCODE_CONFIG_CONTENT`, `OPENCODE_CONFIG_DIR`, `OPENCODE_DISABLE_CLAUDE_CODE`, `OPENCODE_DISABLE_AUTOUPDATE`, `OPENCODE_DISABLE_MODELS_FETCH`; no telemetry variable on that page | <https://opencode.ai/docs/cli/> |
| 11 | Latest releases: Pi v0.87.1 (2026-09-22 19:43 UTC), OpenCode v1.18.32 (2026-09-21 22:51 UTC), Codex rust-v0.156.0 (2026-09-22 19:51 UTC) | GitHub API |
| 12 | Licences and stars: pi-mcp-adapter MIT 1,530; pi-acp MIT 693; licensee MIT 912; datasketch MIT 2,967; agentskills Apache-2.0 25,602; Agent Client Protocol registry Apache-2.0; Kilo MIT 27,390; ProRL-Agent-Server Apache-2.0 843; scancode-toolkit shown as unrecognized on GitHub, README states Apache-2.0 overall and CC-BY-4.0 for reference datasets | GitHub API |
| 13 | NVIDIA SkillSpector: Apache-2.0, 18,108 stars, created 2026-03-21; static analysis with an optional model stage; `--no-llm`; batch scanning; SARIF; Pi and OpenCode extensions. Its README cites "Agent Skills in the Wild" (Liu et al., 2026): 42,447 skills collected, 31,132 analyzed, 26.1 percent with a vulnerability, 5.2 percent likely malicious (author claims; the paper was not read) | GitHub API, README |
| 14 | Snyk agent-scan: Apache-2.0, 3,080 stars; needs `SNYK_TOKEN`; uses Snyk's analysis API; starts standard-input protocol servers to read tool lists | GitHub API, README |
| 15 | Cisco skill-scanner: licence unrecognized on GitHub, 2,544 stars | GitHub API |
| 16 | Agent Skills field rules and `skills-ref validate` | <https://agentskills.io/specification> |
| 17 | Cloudflare counts by header only on Enterprise with Advanced Rate Limiting; Free periods 10 seconds; Pro up to one minute | <https://developers.cloudflare.com/waf/rate-limiting-rules/> |
| 18 | Supabase `deleteUser` needs the service role key and runs only on a server; soft deletion is not reversible | <https://supabase.com/docs/reference/javascript/auth-admin-deleteuser> |
| 19 | Agent Client Protocol `session/new`: absolute `cwd`; protocol servers over standard input and output (required), HTTP and server-sent events (optional) | <https://agentclientprotocol.com/protocol/session-setup> |
| 20 | Claude Code licence: "All rights reserved. Use is subject to Anthropic's Commercial Terms of Service." | GitHub `anthropics/claude-code` `LICENSE.md` |
| 21 | Live Baltor: `limits.search_results = 50`; retrieval `lexical_backend: sqlite_fts5`, `vector_backend: deterministic_character_hash`; health 200 (about 22:40 UTC) | <https://baltor.ai/api/v1/capabilities>, /api/v1/health |
| 22 | Workstation: codex-cli 0.155.1, opencode 1.18.32, Claude Code 2.1.280 | Local version commands |
| 23 | Registry entries carry `_meta["io.modelcontextprotocol.registry/official"]` with `status` (observed `active`), `statusChangedAt`, `publishedAt`, `updatedAt` and `isLatest` | <https://registry.modelcontextprotocol.io/v0.1/servers> |
| 24 | "Do Not Mention This to the User": Detecting and Understanding Malicious Agent Skills in the Wild (Liu and others, submitted February 6, 2026): 98,380 skills from two registries, 157 malicious skills confirmed; dataset and detection pipeline stated to be public | <https://arxiv.org/abs/2602.06547> |
| 25 | Roadmap additions in commit `0f1c690` to S-6.31, S-6.40, S-6.42 and S-6.45 | `git diff 5aa224c 0f1c690 -- docs/roadmap/roadmap.yaml` |
| 26 | Repository facts at `5aa224c`: `access.py` lifetimes and 30-day ceiling; `http.py` `top_n` 1 to 50, `_search` fields, route table; `provisioning_server.py` `_list`; `provisioning_mcp.py` tools; `stripe_sessions.py` portal fields; `request_limits.py` process memory; `storage.py` SQLite; `fly.toml` one machine; `harness_process.py` bubblewrap arguments and style list; `instance_instructions.py` style files; `node_provisioning.py`; `embodiments/pi` 0.85.1 and `embodiments/opencode` 1.17.9; `reviews.json` totals; `DEFAULT_ACCEPTED_LICENSES = ("MIT",)`; key prefix `le_` | Repository, read only |

## 12. Not verified, disputed or open

- `HARNESS-FORKS.md` says Pi ships a `pi-telemetry` package; not verified here.
- SkillSpector's rates and SoL-Pi's savings are author claims. SoL-Pi solved
  fewer Terminal-Bench tasks than Pi (Reported).
- The distinct-reference allowances (500 and 20,000) are starting settings,
  not measurements; the other quota numbers are starting settings from `FAMILIAR-UX-AND-GUARDRAILS.md`.
- OpenCode's `/tmp/opencode` is shared between instances outside the
  sandbox, and one OpenCode capture run hung once for an unknown reason
  (Reported). Both need a recorded answer in the loading check.
- The Claude Code primary recipe (`--bare` with explicit flags) is documented
  but has not been run by Baltor; the fallback recipe rests on
  `CLAUDE_CONFIG_DIR` behavior observed at 2.1.280 only. Every recipe in
  section 7 is a starting value until the loading check proves it.
- Codex 0.156.0 was released on September 22 after the isolation test, which
  proved the Codex recipe at 0.155.1 only.
- Whether the registry's `server.json` fields carry any licence terms: the
  registry states none for its data (Reported). This plan serves generated
  configuration from facts, not copied text, which does not depend on the
  answer.
- The roadmap's dependency of S-6.40 on S-6.30 and of S-6.41 and S-6.42 on
  S-6.31 is relaxed here for first increments only (section 8); the roadmap
  itself was not edited.
