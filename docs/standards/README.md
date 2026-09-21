# Engineering standards

Kind: engineering standards.

This folder holds the short set of rules that a new developer or coding agent
follows when changing Loop Engine. Each rule describes what the code does
today and names the file that shows it. When a standard and the code differ,
the code and its checks are the fact. Correct the standard in the same change.

These documents do not grant authority. [AGENTS.md](../../AGENTS.md), the
[Constitution](../architecture/CONSTITUTION.md) and the typed contracts govern
the work. The standards do not replace them. They collect the working habits
that those documents and the source already require.

## Read in this order

| Order | Document | Question it answers |
|---|---|---|
| 1 | [Names and nomenclature](NAMES-AND-NOMENCLATURE.md) | Which word do I use, and how do I name a record, an error code or a check? |
| 2 | [Records, versions and compatibility](RECORDS-VERSIONS-AND-COMPATIBILITY.md) | How do I define a record, and when does it need a new version? |
| 3 | [Checks and evidence](CHECKS-AND-EVIDENCE.md) | How do I prove a change, which gate covers what, and how do I save the result? |
| 4 | [Service interface conventions](SERVICE-INTERFACE-CONVENTIONS.md) | How does a route of the hosted service accept a request and answer it? |
| 5 | [Languages and components](LANGUAGES-AND-COMPONENTS.md) | Which language and library does each component use, and how do I add one? |

## What does not belong here

- Architecture decisions belong in [the architecture folder](../architecture/README.md).
- Task instructions belong in [the operating guides](../guides/README.md).
- Dated results belong in [verification reports](../verification/README.md)
  or in the evidence folders that the [records index](../RECORDS-INDEX.md) lists.
- The state of the running service belongs in the
  [current deployment](../architecture/MVP-CLIENT-SERVER.md#current-deployment)
  section and in the
  [takeover checkpoint](../context/TAKEOVER-CHECKPOINT-2026-09-20.md).

## How to change a standard

1. Find the source file or check that shows the behavior.
2. Change the standard and cite that file.
3. Keep each document under 200 lines. Link to the owning document instead
   of repeating it.
4. Follow the [documentation style](../STYLE.md) and
   [humanizer-context.md](../../humanizer-context.md).
