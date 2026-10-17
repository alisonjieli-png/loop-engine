# Draft changes to the privacy notice for saved feeds

Kind: draft for the owner. Nothing here is published. The served notice at
`/privacy`, [PRIVACY-NOTICE.md](PRIVACY-NOTICE.md) and the terms stay exactly
as the owner approved them until the owner approves a change in their own
words. Engineering prepared this on October 16, 2026 for saved customer feeds
with a separate assignment for each agent (roadmap S-6.214.10), described in
[the service guide](../../src/loop_engine/core/service_runtime/README.md#saved-customer-feeds-for-agents).

## Why a change is proposed

Saved feeds keep three kinds of record in the service database:

- the feed settings a signed-in customer saves;
- which of their Baltor keys may read which saved feed;
- delivery history for each of those assignments.

Engineering read the notice approved on October 1, 2026 to decide whether it
already covers these records. It does not cover them clearly, for three
reasons.

1. The first section lets Baltor store inputs sent through forms and APIs "to
   provide requested features". The table covers "content you explicitly
   submit" and "connection and consent records, client metadata, granted
   scopes". Saved settings and key assignments fit those words. The table
   gives that content the purposes "To respond, reproduce problems, identify
   missing material and improve the service", and none of them names
   delivering a saved feed to the tools a customer chooses.
2. Delivery history records which key read which version of a feed, and when.
   The notice says the service records "the account, download, submission and
   connection events described above, rather than a general log of every
   successful request". Its usage row covers "One usage record for each
   downloaded item". Delivery history is a new kind of activity record that
   no row names.
3. Customers delete saved feeds themselves. The notice says "self-service
   deletion is not available", which would no longer be accurate for these
   records.

Until the owner approves a change, saved feeds stay switched off. The service
refuses a host setting that switches them on unless the served notice contains
the phrases "Saved feed settings" and "feed delivery history". A host file
alone therefore cannot start this collection.

## Change 1: a row in "What the service stores"

Proposed new row, after the row that begins "Connection and consent records":

> | Saved feed settings you choose for your agents, which of your Baltor keys may read each feed, and feed delivery history: for each key and feed version, when it was read, how many pages, items and bytes were sent and whether the read finished | To deliver the feeds you save to the tools you choose, show you what each tool read, and limit how often a feed is read | The service database on Fly, United States (`iad`) |

## Change 2: the deletion paragraph in "Backups and deletion"

Proposed replacement for the sentence "Requests are handled by an operator;
self-service deletion is not available.":

> Requests are handled by an operator; self-service deletion is not available,
> except for saved feeds. Deleting a saved feed on your account page removes
> its settings, its key assignments and their delivery history at once.
> Removing a key from a feed removes that assignment and its delivery history.
> Delivery history keeps the 20 most recent feed versions each key read, and
> older entries are removed as new ones are recorded.

The number 20 is the default of the host setting. If the operator sets
another number, this sentence changes with it.

## What stays the same

The bullet "It records the account, download, submission and connection
events described above, rather than a general log of every successful
request" stays true with the new row, because the new row is one of the
records "described above".

No email address, password, project file, prompt or model key enters these
records. The service does not store feed content: it builds each feed from the
public source directory and the public library notice when an agent reads it.
Saved settings are private to the account that saved them and are not used for
advertising.

## What changes when the owner approves

The owner's approval in their own words updates
[PRIVACY-NOTICE.md](PRIVACY-NOTICE.md), the `privacy` view of
`src/loop_engine/core/service_runtime/web_assets/index.html` with the same
words, the "Updated" line, and [the legal folder index](README.md). The
browser check that compares the served notice with the approved file then
holds the new text. A release that serves the approved notice is the first
release whose start check accepts a host file that switches saved feeds on.
