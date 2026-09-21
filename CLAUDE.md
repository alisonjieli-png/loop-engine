# Claude Code instructions for Loop Engine

@AGENTS.md

@ASTRA.md

Start with the [September 21 session handoff](docs/context/SESSION-HANDOFF-2026-09-21.md).
It is the current picture: what is live, what is approved and not yet
deployed, what is running on which branch, the open defects and the reason
the build is red. Another harness picking this work up starts there.

Then read the [takeover checkpoint](docs/context/TAKEOVER-CHECKPOINT-2026-09-20.md).
It records the verified live state, the repairs made on September 20, the
open findings, the private beta definition and the working cycle for
changes, tests, checkpoints and releases. The north star and the ordered
initiatives are in [AGENTS.md](AGENTS.md#north-star-and-current-initiatives).

The earlier [Fable 5.1 handoff](docs/context/FABLE-5-1-HANDOFF-2026-09-20.md)
and [development checkpoint](docs/context/DEVELOPMENT-CHECKPOINT-2026-09-20.md)
remain valid as dated snapshots of the previous developer session. The
machine-readable work authority is [roadmap.yaml](docs/roadmap/roadmap.yaml),
with seventeen delivery packages. The single development HTML is generated
from the roadmap and the source; do not edit it by hand and do not start
another dashboard.

Use the [prepared credential handoff](docs/guides/developer-credential-handoff.md)
for the existing connections. Never print the header-helper output, repeat
account creation or work around a recorded permission gap.

## Authority recorded on September 20, 2026

The owner asked Claude Code to continue all of the previous developer's work,
to commit reviewed work to `main` and to deploy the private pilot to Fly.
That authority covers this continuing work. It does not cover:

- model calls, live charges or public registration;
- publishing candidate intelligence without the owner's approval of each item;
- destroying or deleting an application, a volume, a domain record, a name
  server delegation, a provider resource or a secret. Ask in the current
  conversation before any such operation, even though the connections allow it.

## Owner direction recorded on September 20, 2026, in the evening

The owner told engineering to stop bringing back decisions that engineering
can make. Decide, write down the reason, and move on. When a choice is
uncertain, research it, measure it or test two versions instead of asking.
The target is a system that is ready for paying customers. These judgment
calls were made under that direction and stand until the owner changes them:

| Decision | Choice and reason |
|---|---|
| Approval of intelligence items | Delegated to an independent review process. Reviewers who did not write an item approve or reject it against written criteria, and the approval record names them. A producer still never approves its own work. The owner can withdraw any item. |
| Price | One plan, Baltor Pro, 29 United States dollars each month. Comparable entry plans cost 19 to 29 dollars. Search is free, the measured unit is one downloaded item, and there is no overage billing at launch. Invited beta users are free through an operator entitlement. |
| Payments | Everything is built and qualified in Stripe test mode. A live account needs the owner's identity and bank verification, which engineering cannot do, so going live is one credential change after that. |
| Sign-up email | The service creates the confirmation link through the identity provider's administration interface and sends its own email, so the whole journey stays on the baltor.ai domain and needs no change to provider settings that engineering cannot reach. |
| Browsing for signed-in users | The owner's words were heard as browsing the intelligence layers. Signed-in users get a catalogue browser grouped by the four layers. |
| Public positioning | The category line is harness and agent optimized operation, the owner's phrase. |

Ask the owner only for what engineering truly cannot do: a legal
commitment, spending beyond the recorded allowance, or a destructive
operation listed above.

Never tell the owner to rotate, revoke or re-create a credential. That
includes one pasted into a chat window and a full secret live payment key.
The owner gave this instruction twice. State a genuine risk once if it is
new, then store the credential and continue. Keep controls that prevent an
accident, such as refusing a test key where a live key is required, and
record an override the owner has chosen rather than arguing with it.

Live payments are activated. The live account is `acct_1UHZ972IF9bCskLc`,
separate from the sandbox, with charges and payouts enabled and nothing
outstanding. Its key is in the system keyring under `stripe-live` and
reaches a command only through `tools/operator_credentials.py`.

Verify current source and provider state before relying on a dated result.
Read the relevant component guide before implementation and preserve
concurrent work.

These are development instructions, not executable harness configuration.
Do not enable native tools or goals merely because an instruction file
describes them.
