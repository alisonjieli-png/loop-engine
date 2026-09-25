# Communities, chat distribution and the Recipe Rescue helper

Kind: dated research record for the owner's requests of September 24, 2026.
The primary sources were read on September 25, 2026 (UTC). It reports what
was read and decided and the build plan that follows. It creates no
community, bot, invitation or payment, makes no model call and approves no
library material. The [roadmap](../roadmap/roadmap.yaml) remains the task
authority: the build work entered it as proposed steps S-6.149 to S-6.157.
The numbers start at S-6.149 because the
[publishing research](PUBLISHING-INTO-BALTOR-2026-09-24.md) holds S-6.140 to
S-6.148 on `main`, and other lines of work in flight on September 24 and 25
had claimed S-6.100 to S-6.134 and S-6.160 onward.

Source state: Baltor was read on `main` at `dbf2389c`, and the record was
rebased onto `b2f3df8d`, which added the publishing research. Discord's developer
documentation was read in Discord's own documentation repository at
`30017dee`. The operational setup kit (server layout, roles, rules, welcome
messages, Telegram and Messenger settings, the first challenge brief,
invitations and the owner's account steps) is private and stays outside this
repository, in `/home/username/baltor-private/community-2026-09-24/`.

## Summary

- **One community, three ways in.** A Discord server is the workshop, a
  Telegram channel inside a Telegram Community is the low-noise update
  stream, and a small Messenger cohort of about 25 people is run by hand.
  Nobody has to join every place, and the owner's newsletter and existing
  groups stay where they are.
- **The platforms changed in 2026, and the changes favor a small helper.**
  Telegram bots gained guest mode on May 8 (one reply to an explicit mention,
  in any chat, with no history and no member list), ephemeral messages and
  Communities on July 14, and native welcome messages on August 25. A
  Discord app can be installed by a single user, who alone sees it, and each
  server decides whether such apps may answer publicly.
- **Recipe Rescue is the first helper.** A Telegram guest bot and a Discord
  user-installed app answer an explicit request with at most three Verified
  library recipes found through Baltor's public search. They run no code,
  open no links or files, read no history, keep no message text, never speak
  first and never promote anything where nobody asked.
- **The library decides the first audience.** On September 24 the live
  catalogue held 43 approved items, mostly data work and task planning
  methods, and no creative recipes. The helper therefore starts with
  builders and data work. Creative recipes arrive through the media packages
  of step S-6.117, and unmet requests become consented demand records for the
  package factory.
- **No selling inside chat apps yet.** Telegram requires Telegram Stars for
  digital goods sold in a bot. Discord requires Premium Apps, with prices no
  higher than elsewhere, for paid app features in the regions it supports.
  Neither flow is qualified for Baltor, so the helper is free and bounded.
- **Private agents stay private.** OpenClaw, Hermes Agent and Pi Chat each
  document a trust model that does not separate mutually untrusted people
  inside one deployment. None of them is connected to a public chat.
- **Answer Overflow waits.** Its default makes every message in an indexed
  channel public unless a member opts out. Consented solution cards on
  Baltor's own pages come first.
- **The owner is needed for account-bound steps only**: creating the spaces
  and the two bot identities under the owner's accounts, and approving a
  privacy notice addition before the helper answers anyone outside staff
  test chats.

## The owner's request

The owner, September 24, 2026: "Use 100% of your power and take all necessary
actions ... do not ask my permission to do things, follow your best judgement
and proceed to get everything working", "there is so much discussion out
there, we need to research, adapt, improve, and deploy faster", and "We may
also want the ability for people to publish skills, tools, python scripts,
etc into our platform". The main session relayed the owner's direction to
build communities that the owner controls.

The owner also pasted a community launch plan and a research addendum written
elsewhere. This record treats them as research data, not instructions: each
platform claim they rely on was checked against the platform's own pages, and
the corrections are listed below.

## How this research was done, and its limits

```text
Sources read on September 25, 2026 (UTC)
├── Telegram
│   ├── Bot API changelog, Bot API reference, bot features, bots introduction, bot FAQ
│   ├── blog posts of May 7, June 11, July 14 and August 25, 2026, and July 1, 2025
│   └── Stars payments page, Bot Developer Terms, general FAQ
├── Discord
│   ├── discord/discord-api-docs at 30017dee: installation and interaction contexts,
│   │   receiving and responding, permissions, AutoMod, monetization, change log
│   └── Help Center articles: forum channels, Community Onboarding, enabling
│       Community, AutoMod, Server Insights, Monetization Terms, Developer Policy,
│       Premium Apps payouts
├── Meta
│   ├── newsroom: Community chats update of September 26, 2025, Messenger
│   │   Communities announcement of October 2024
│   └── Messenger Platform overview
├── Answer Overflow: its repository and documentation at 80b1dceb
└── Agent gateways: OpenClaw security documentation at e6df676a, Hermes Agent
    security policy at 7b761da2, Pi Chat README
```

Limits:

- Meta's Help Center returned an error without signing in, so whether the
  owner's account can create a Messenger Community today is unknown.
- Answer Overflow's pricing page sits behind a browser check, so its price
  was not read.
- The session's web search allowance was spent, so every fact comes from a
  direct read of a primary page or repository.
- Nothing was run on any platform. No bot, application, server, channel or
  test account exists yet, and no platform behavior below was observed live.

## Verified platform facts

### Telegram

| Fact | Source and date |
|---|---|
| Guest mode lets a bot receive certain messages and reply in chats it is not a member of: a `guest_message` update, `Message.guest_query_id`, and `answerGuestQuery`, whose `result` is an inline query result. | Bot API 10.0, May 8, 2026; the blog announced it on May 7 |
| When a user mentions a guest bot or replies to one of its messages, the bot receives the summoning message and, when present, the message it replied to, and may issue one reply. It gets no history, no participant list and no later messages unless summoned again. Up to 3 guest bots can be mentioned in one message. | Bot features page |
| Ephemeral messages: a bot in a group can send a message visible only to one user and the bot, and a command can be marked ephemeral so the user's own command is hidden from others. | Bot API 10.2, July 14, 2026 |
| Communities link several supergroups, channels and bots around a shared topic. Chats can be Visible, or Hidden from everyone except community admins and that chat's members. Communities are collaborative by default: any member can add chats unless the setting is restricted. | Bot API 10.2 and the blog, July 14, 2026 |
| Groups and channels support native welcome messages that only new members see, set by the owner with no bot. Developers can put buttons inside messages and pair them with ephemeral messages. Administrators gained a `can_send_welcome_messages` right. | Blog, August 25, 2026; Bot API 10.3, August 24, 2026 |
| Privacy mode is on by default. A bot added to a group as an administrator receives every message. | Bot features page |
| Bots cannot start conversations. A user must add the bot to a group or message it first. | Bots introduction |
| Bot-to-bot communication must be enabled in @BotFather, and bots that use it must prevent loops: deduplicate repeated messages, rate limit, and enforce a maximum interaction depth or timeout. | Bot features page; Bot API 10.0 |
| Managed bots: a bot can ask a user to create a bot that it then manages, through a request button or a `t.me/newbot/...` link. | Bot API 9.6, April 3, 2026 |
| Join request queries let a guard bot screen people before they join a group. | Bot API 10.1 and the blog, June 11, 2026 |
| Digital goods and services sold by a bot must be paid for exclusively in Telegram Stars. A bot that sells them must answer `/paysupport`. Refunds are deducted from the bot's balance, Stars can be unavailable for up to 21 days, and the developer reward value is 0.013 United States dollars per Star. | Stars payments page; Bot Developer Terms, section 6.2 |
| Rate guidance: about one message per second in one chat, at most 20 messages per minute in a group, and about 30 messages per second for broadcasts. | Bot FAQ |
| Groups and channels are cloud chats with client-server encryption. Only secret chats are end-to-end encrypted. | Telegram FAQ |
| A webhook can require a secret, which Telegram sends in the `X-Telegram-Bot-Api-Secret-Token` header. | Bot API reference |

The Bot FAQ still says that bots never see messages from other bots. The
features page and Bot API 10.0 document the newer Bot-to-Bot Communication
Mode, so the FAQ section is out of date.

### Discord

| Fact | Source |
|---|---|
| An app can be installed to a server, to a user, or both. A user-installed app is visible only to the authorizing user, across that user's servers, direct messages and group messages, and must respect the user's permissions where it is used. | Application resource documentation |
| Commands declare installation contexts (`integration_types`) and interaction contexts (`contexts`: `GUILD`, `BOT_DM`, `PRIVATE_CHANNEL`). | Application commands documentation |
| A message command appears on a message's context menu and delivers the whole selected message, including its content, without the Message Content intent. | Application commands; privileged intent guide |
| An app must send its first response within 3 seconds; the interaction token then lasts 15 minutes. A user-installed app that is not installed in the server may send at most 5 followup messages per interaction. | Receiving and responding |
| An interactions endpoint must answer `PING` and verify the `X-Signature-Ed25519` and `X-Signature-Timestamp` headers on every request, refusing a bad signature with status 401. | Interactions overview |
| The Use External Apps permission decides whether user-installed apps may answer publicly in a server. Without it their answers are visible only to the person who used them. It does not apply to apps also installed to that server. | Permissions documentation |
| Forum channels need Community enabled; tags can be required, and posts move to Older Posts after 3 days of inactivity by default. | Forum Channels FAQ |
| Community needs a verified email level, the explicit media filter for all members, a rules channel and a community updates channel. Server Discovery is limited to servers with more than 1,000 members and to Partnered and Verified servers. | Enabling Your Community Server |
| Community Onboarding needs at least 7 default channels, at least 5 of which let everyone view and send messages. | Community Onboarding FAQ |
| Members with Administrator or Manage Server are always exempt from AutoMod filter rules. A server has at most 6 keyword rules, each with up to 10 regular expressions of up to 260 characters, and a block message of up to 150 characters. | AutoMod FAQ; AutoMod documentation |
| Server Insights applies to Community servers with more than 500 members. | Server Insights FAQ |
| Premium Apps sell user subscriptions, guild subscriptions (every member of the server is entitled), and durable or consumable one-time purchases. Monetization needs a verified app owned by a team, an owner aged 18 or over, two-factor sign-in, and links to terms and a privacy policy. Payouts run through Stripe for teams in the United States, the European Union and the United Kingdom. | Monetization documentation |
| On desktop and browser, Premium Apps pay 6 percent in payment processing and a 15 percent platform fee (the Growth Tier) until the developer team's Premium Apps reach 1,000,000 United States dollars in total payments, then 30 percent. Mobile transactions are not available for Premium Apps. Server Subscriptions are a separate programme. | Monetization Terms, Schedule 1 |
| Since October 7, 2024, where Premium Apps is supported, an app's paid features must be purchasable through Premium Apps at prices no higher than through other payment options. | Developer Policy |
| Age assurance is rolling out: parent-set spending limits may block purchases. Apps with discovery enabled cannot contain age-restricted commands. | Change log, September 22, 2026; application commands |

### Messenger

| Fact | Source |
|---|---|
| Community chats in Facebook Groups ended on October 5, 2025. Meta's notice names Messenger Communities and WhatsApp Communities as alternatives. | Meta newsroom, update of September 26, 2025 |
| Messenger Communities were announced for small and medium communities: topic-based chats inside one community, managed without a Facebook Group, grown through Facebook friends or a QR code. | Meta newsroom, October 2024 |
| A business can message a person only after the person writes first, and should answer within 24 hours. The overview says nothing about bots inside group chats or Messenger Communities. | Messenger Platform overview |
| Current availability of Messenger Communities in a given account is unknown: Meta's Help Center could not be read without signing in. | Not read |

### Answer Overflow

| Fact | Source |
|---|---|
| MIT licence. It publishes selected Discord channels as web pages. | Repository at `80b1dceb` |
| New servers default to treating all messages in indexed channels as public; members opt out with `/manage-account`. Consent can also come from forum guidelines or membership screening. | Documentation: displaying messages, forum guidelines consent |
| Indexing runs about every 6 hours. Content stays on Answer Overflow for up to 7 days after indexing is disabled, and in Google for an unknown time. Answer Overflow has no control over what Google indexes. | Documentation: indexing |
| The public platform is supported by advertising; a paid plan indexes content on the community's own domain. The price was not read. | Changelog and documentation |

### Agent gateways that connect to chat

| Project | What its own documentation says |
|---|---|
| OpenClaw (`e6df676a`) | One trust boundary per gateway: a single operator, or a team whose members trust each other. It is not a hostile multi-tenant boundary for mutually adversarial users sharing one agent or gateway. |
| Hermes Agent (`7b761da2`, MIT) | Every network-exposed adapter needs an allowlist, and inside the allowed set all callers are equally trusted. It does not model per-caller capabilities inside one adapter. |
| Pi Chat (Apache-2.0) | Each connected Discord or Telegram channel gets its own micro virtual machine, but account-wide memory and skills are mounted into every one, and all outbound HTTP and TLS is open by default. |

## Corrections to the pasted research input

1. Telegram guest mode shipped in Bot API 10.0 on May 8, 2026; the blog post
   is dated May 7.
2. The input said Hermes gates only slash commands between administrators and
   users. Its security policy says all allowlisted callers are equally
   trusted, with no per-caller capabilities inside one adapter. The
   conclusion stands: an allowed sender is not containment.
3. Answer Overflow's default is public with opt-out, which the input did not
   say.
4. The input did not mention three facts that change the design: the Use
   External Apps permission, the 5-followup limit for user-installed apps,
   and that Premium Apps has no mobile transactions.

The other platform claims that the plan relies on matched the primary pages.

## Decisions made and why

| Decision | Choice and reason |
|---|---|
| One community | One community with three ways in. Three separate communities would compete for one small audience and triple the moderation work. |
| Discord | Community mode and full onboarding from day one, because forums and onboarding both need Community. The layout has 10 default channels, 5 of them open to everyone for viewing and sending. Stewards get no Manage Server permission, so AutoMod applies to them. Use External Apps is off for members, which keeps other people's promotional apps private in Baltor's own server. |
| Telegram | A channel inside a Telegram Community with adding chats restricted to admins, a native welcome message, and a discussion group only when a steward is available. |
| Messenger | A human-run cohort. Meta documents no interface for a bot in a Messenger Community. |
| Payments in chat apps | None at launch. A paid capability inside Telegram or Discord needs the Stars or Premium Apps flow qualified first, with refunds, entitlement checks and accounting that records platform and payment fees separately from Baltor's own subscription revenue. |
| Answer Overflow | Not installed. Revisit when the help forum holds 50 solved posts whose writers consented, with Answer Overflow set to treat messages as private unless consented. |
| Recipe Rescue scope | Search and a fixed recipe card, Verified tier only, deterministic, no model call. A narrow, checkable answer earns its place in a conversation; general chat does not, and a model could invent a dependency. |
| Recipe Rescue privacy | The helper processes platform user identifiers and message text. The owner approved the privacy notice drafts of September 24 and no other use of personal data, so the helper answers only staff test chats until the owner approves an addition. |
| Commercial fields | A helper answer never carries a price, discount code, referral code or sponsored link, following the rule that ranking and inclusion never read commercial relationship fields. |
| Contributions | Posting in a community is never a library submission. A member who wants a recipe, skill, tool or script in the library submits it through the author submission path that the [publishing research](PUBLISHING-INTO-BALTOR-2026-09-24.md) designs (steps S-6.140 to S-6.148): a namespace, a submission confirmed by a signed-in person, automated checks, independent review into the Community tier, and contributor terms. That record reaches the same conclusion from the same input: a message in a chat channel never becomes a library item. The community's part is to point people to that path. |

## The Recipe Rescue helper

### What it does

A person asks for a recipe in words, where they already are:

- in Telegram, by mentioning the bot in any chat, or with `/recipe` in the
  owned group;
- in Discord, with `/recipe` or with the message command "Find a recipe for
  this" on any message.

The helper searches Baltor's reviewed library and answers with at most three
recipe cards, or with "No reviewed recipe fits this yet". A **qualified
library recipe** is a served package in the Verified tier, as the
[decision table](../../AGENTS.md#decisions-that-stand-until-the-owner-changes-them)
defines it, whose public card fields are complete: purpose, kind, files with
their placement for at least one harness, licence, declared effects, and the
identity of its review record. An item without complete card fields is never
an answer.

A card would look like this. The fields come from the served item
`find_duplicate_records_with_blocking_keys`; the page address is proposed in
step S-6.149 and does not exist yet.

```text
Find duplicate records with blocking keys
Verified · MIT · skill, 1 file · declares no effects
Finds duplicate customer, company or contact records without comparing every
row with every other row: groups rows by blocking keys, compares inside the
groups, and reports oversized groups it skipped.
Claude Code: .claude/skills/<name>/SKILL.md · Codex: .agents/skills/<name>/SKILL.md
Open in Baltor: https://baltor.ai/r/find_duplicate_records_with_blocking_keys

Found by search in Baltor's reviewed library. Not run on your files.
[Useful] [Not useful] [Ask Baltor to make this recipe]
```

### What it never does

- Speak unprompted, message anyone first, join a chat on its own, or reply
  to another bot.
- Run code, open links, read attachments or images, or read chat history.
- Store message text, except when the asker presses "Ask Baltor to make this
  recipe".
- Show Community tier or unreviewed items, or invent an answer when the
  search finds nothing or fails.
- Include prices, discount codes, referral codes, sponsored links or sign-up
  pressure.
- Take a payment or sell anything inside Telegram or Discord.

### Where it sits in the runtime

Everything in this section is proposed. None of the records, the engine slot
or the public search edge exists yet; steps S-6.149 to S-6.152 build them.
Start from the complete classification.

```text
Operational runtime type
└── Loop
    ├── Operational relationship
    │   ├── Starting
    │   ├── Spawned by
    │   ├── Queried by
    │   ├── Retrieved by
    │   └── Connected from
    ├── Role
    │   ├── Practitioner
    │   ├── Intelligence
    │   └── Solution
    ├── Versioned role profile
    ├── Purpose and domain categories
    ├── Run mode
    │   ├── deterministic
    │   ├── hybrid
    │   └── non-deterministic, with model-led semantic work
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition
    ├── Exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the selected mode permits a model
    └── Run History records
```

Each answer is one Loop:

```text
Recipe Rescue answer Loop
├── Operational relationship: Starting, one per explicit chat request
├── Role: Intelligence
├── Versioned role profile: intelligence.search@1.0.0
├── Run mode: deterministic, no model settings
├── Typed input: recipe_rescue_request/v1
│   ├── channel, invocation kind, request text of at most 300 characters
│   └── keyed hashes of the requester and the conversation
├── Typed output: recipe_rescue_answer/v1
│   └── at most three recipe cards, or an abstention with its reason
├── Loop condition: none, one search per request
├── Exit condition: one answer sent, or a typed refusal
├── Budget and permissions: one public search, one platform reply, no files,
│   no outbound fetch, no model, no spending
└── Run History records: recipe_rescue_event/v1, which holds no message text
```

The chat platforms are adapters behind a fixed edge, not new runtime types:

```text
chat_request_channel engine slot (proposed)
├── Edge: platform update in, recipe_rescue_request/v1 out;
│   recipe_rescue_answer/v1 in, one platform reply out
├── Engines
│   ├── telegram_guest_mode: guest_message and answerGuestQuery
│   ├── telegram_group_command: ephemeral /recipe in the owned group
│   ├── discord_interactions: /recipe and the message command,
│   │   user-installed and server-installed
│   └── later engines behind the same edge: Telegram inline mode,
│       Slack, a website search box
└── Shared request gate, before any search
    ├── platform authenticity: webhook secret token or Ed25519 signature
    ├── explicit invocation only; bot senders ignored; one reply per request
    ├── host setting, allowlist stage and blocklist
    ├── per requester, per conversation and global limits
    └── refusal of text that looks like a key, which is neither echoed nor kept
```

The search itself is a new public edge over the existing catalogue search:

| Field | Public recipe search |
|---|---|
| Request | `public_recipe_search_request/v1`: query of at most 300 characters, at most 3 results, channel name |
| Tier | Verified only, fixed by the edge; a caller cannot widen it |
| Response | `public_recipe_search_result/v1`: identity, kind, purpose, tier label, licence, declared effects, file count and placement, public page address; or an abstention below the relevance floor |
| Withheld | Bodies, scores, backend names, paging cursors, internal attributes, commercial relationship fields |
| Limits | The published allowance of step S-6.39, counted per caller and per address, with the helper's own per-requester limits on top |

### Records and measures

`recipe_rescue_event/v1` records the channel, the invocation kind, the
outcome (answered, abstained, refused), the item identities shown, keyed
hashes of the requester and conversation, the hour, the catalogue release and
the policy version. It has no field that can hold message text, and a check
refuses one. A Useful or Not useful press is a User Feedback Intelligence
record tied to the answer. "Ask Baltor to make this recipe" is the only path
that keeps the request text, after a key-shaped text check, as a demand
record for the package factory.

Measures, always with raw counts and denominators: requests, answers with at
least one recipe, abstentions, Useful and Not useful presses, opens of the
recipe link as an aggregate count per channel, sign-ups whose first visit
carried a helper link tag as an aggregate count, requesters active on two or
more days, and consented unmet requests.

### Rollout and gates

| Stage | Who can use it | Gate to enter |
|---|---|---|
| A. Offline | Nobody | Contracts, the public search edge, the gate and both adapters pass loopback checks with recorded platform payloads, with the host setting off |
| B. Staff test chats | Owner and engineering accounts, allowlisted chats and a test server | The owner has created the bot identities; tokens reached the keyring and the release secrets; every check below passes live |
| C. Everyone who asks | Anyone who explicitly invokes it | The owner approved the privacy notice addition in their own words |
| D. Partner pilots and listing | Communities whose operators said yes in writing; the Discord App Directory | Four weeks of stage C measures with no unresolved safety report |

### Checks that must fail when a guard is removed

Each is a named check with a removed-guard control:

1. A Telegram update without the right secret header, and a Discord request
   with a bad signature, get no search and no reply.
2. A message that does not invoke the helper, and a message sent by a bot,
   get no reply.
3. A second reply to the same guest query or interaction is refused.
4. A request containing a link or a file causes no outbound request other
   than Baltor's search and the platform's own reply call.
5. A Community tier item, or a Verified item with incomplete card fields, is
   never shown.
6. A fourth result, a paging cursor, a score or a backend name never reaches
   the reply.
7. A reply containing a price, code or sponsored link is refused.
8. Text that looks like a key is refused, not echoed and not stored.
9. The event record refuses a message text field.
10. In a Discord server, the first answer is visible only to the asker, and
    Share posts publicly only after the asker presses it and only where the
    asker may send messages.
11. With the host setting off, or outside the stage allowlist, nothing is
    searched and nothing is recorded; at most a fixed "not open yet" reply is
    sent.
12. When the search fails, the reply says so plainly and never substitutes a
    stored or invented recipe.
13. The request over the per-requester limit is refused before any search.

## Community launch, in brief

The private kit holds the details. The first week: the owner creates the
spaces and bot identities; engineering applies the Discord layout from a
spec through a one-time setup app and runs the checks as an ordinary member,
because AutoMod exempts the owner; stewards seed three examples and publish
the first challenge; about 25 willing people are invited first. The first
challenge asks each participant to make one small piece and to write the
recipe for it, in the same shape as a library recipe card, so that a good
recipe can become a library candidate if its maker submits it through the
author submission path.

Community measures count useful work, not activity: first useful result
within 7 days, repeat useful use on days 8 to 14, help posts that end with a
fix, an accepted next step or an honest "unresolved", peer help, steward time,
and paid accounts that arrived through a community link, after direct costs.
Accepting an invitation is not activation, and identities are never joined
across platforms.

## Later, not now

- A Discord Activity: a shared remix room for the owner's parametric scenes,
  after the standalone scene exists. Discord documents referral and share
  links for Activities.
- A community operator plan: Discord guild subscriptions and Telegram
  managed bots could let an operator provide the helper to members. Both need
  the payment gate and token ownership rules first.
- Telegram inline mode as a second engine, for people who prefer to pick a
  recipe and send it themselves.
- Telegram suggested posts for reviewed guest tutorials, only after the
  channel has a clear editorial rhythm, and never as a way to buy a Verified
  label.

## Build items and roadmap steps

| Step | Build item |
|---|---|
| S-6.149 | The public recipe search edge and public recipe pages, inside the S-6.39 allowance |
| S-6.150 | Recipe Rescue core: the `chat_request_channel` engine slot, the request gate, the answer Loop, the records and the host setting |
| S-6.151 | The Telegram engines: guest mode and the ephemeral group command |
| S-6.152 | The Discord engine: user-installed and server-installed interactions, private answers first |
| S-6.153 | Community spaces: the Discord layout applied from the spec by a one-time setup app, the declared bot credential names, the ordinary member checks and the community measures log |
| S-6.154 | Consented solution cards on Baltor's own pages |
| S-6.155 | Unmet recipe requests as consented demand records for the package factory |
| S-6.156 | The chat payments gate: nothing sold in chat until the Stars and Premium Apps flows are qualified |
| S-6.157 | Research watch sources for the chat platforms |

## What needs the owner

Only what needs the owner's own accounts or a legal commitment:

1. Create the Discord server, the Discord developer team with its two
   applications, the Telegram channel and Community, and the Telegram bot in
   @BotFather, then store each token with the keyring tool.
2. Check whether the Messenger app offers a community.
3. Approve the privacy notice addition for the helper.
4. Send the invitations from the owner's own newsletter and profiles.

## Sources

Telegram:

- [Bot API changelog](https://core.telegram.org/bots/api-changelog)
- [Bot API reference](https://core.telegram.org/bots/api)
- [Bot features](https://core.telegram.org/bots/features)
- [Bots introduction](https://core.telegram.org/bots)
- [Bot FAQ](https://core.telegram.org/bots/faq)
- [Stars payments](https://core.telegram.org/bots/payments-stars)
- [Bot Developer Terms](https://telegram.org/tos/bot-developers)
- [Telegram FAQ](https://telegram.org/faq)
- Blog: [May 7, 2026](https://telegram.org/blog/ai-bot-revolution-11-new-features),
  [June 11, 2026](https://telegram.org/blog/watch-apps-and-more),
  [July 14, 2026](https://telegram.org/blog/communities-editor-invisible-messages),
  [August 25, 2026](https://telegram.org/blog/welcome-messages-buttons-TG-13),
  [March 31, 2026](https://telegram.org/blog/ai-editor-mighty-polls-and-more),
  [July 1, 2025](https://telegram.org/blog/checklists-suggested-posts)

Discord:

- [discord-api-docs repository](https://github.com/discord/discord-api-docs), read at `30017deef2a18229dbd21f36c7b865169dd26b6b`
- [Forum Channels FAQ](https://support.discord.com/hc/en-us/articles/6208479917079-Forum-Channels-FAQ)
- [Community Onboarding FAQ](https://support.discord.com/hc/en-us/articles/11074987197975-Community-Onboarding-FAQ)
- [Enabling Your Community Server](https://support.discord.com/hc/en-us/articles/360047132851-Enabling-Your-Community-Server)
- [AutoMod FAQ](https://support.discord.com/hc/en-us/articles/4421269296535-AutoMod-FAQ)
- [Server Insights FAQ](https://support.discord.com/hc/en-us/articles/360032807371-Server-Insights-FAQ)
- [Monetization Terms](https://support.discord.com/hc/en-us/articles/5330075836311-Monetization-Terms)
- [Developer Policy](https://support-dev.discord.com/hc/en-us/articles/8563934450327-Discord-Developer-Policy)
- [Premium Apps Payout](https://support-dev.discord.com/hc/en-us/articles/17299902720919-Premium-Apps-Payout)

Meta:

- [Community chats notice, updated September 26, 2025](https://about.fb.com/news/2022/09/community-chats-on-messenger-and-facebook/)
- [Messenger Communities announcement, October 2024](https://about.fb.com/news/2024/10/facebook-local-tab-messenger-communities-ai/)
- [Messenger Platform overview](https://developers.facebook.com/docs/messenger-platform/overview)

Answer Overflow and agent gateways:

- [Answer Overflow repository](https://github.com/AnswerOverflow/AnswerOverflow), read at `80b1dceb10e1abbf42ce3c301697e8958727b791`
- [OpenClaw gateway security](https://github.com/openclaw/openclaw/blob/main/docs/gateway/security/index.md), read at `e6df676ad11163215954b234aa3238536586534c`
- [Hermes Agent security policy](https://github.com/NousResearch/hermes-agent/blob/main/SECURITY.md), read at `7b761da2de4979e424510ca7022bf9527aa65b68`
- [Pi Chat](https://github.com/earendil-works/pi-chat)
