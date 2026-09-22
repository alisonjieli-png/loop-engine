# Catalogue search quality

Owner: `core.harness_intelligence_search`. Measurement:
`examples/30_search_quality`. Saved result:
`examples/30_search_quality/report-2026-09-21.json`.

A customer's coding tool asks the hosted service for what one step needs and
reads the first few references. If the wrong three come back, every later step
is worse. Before 21 September 2026 nobody could say how often that happened,
because nothing measured it. This document records what search did, what it
does now, how the change was measured and what is still wrong.

## What search did before this measurement

Read from `core.service_runtime.http.ServiceHttpApplication._search` and
`core.retrieval.record_search_text` on 21 September 2026.

The deployed service answers a search by building one record for each item the
tenant may already see, and handing those records to the shared retrieval
engine:

- The record's title is the item's purpose.
- The record's description is the item's purpose again.
- The record's keywords are the item's identity, its kind and its source layer.
- Everything else about the item, including its declared tags, never reaches
  the index. No body is ever indexed.

The engine's lexical backend is SQLite full text search with BM25 ranking. It
splits text on anything that is not a letter or a digit, lowercases it, matches
a record when it holds any word of the request, and orders by BM25. So the
purpose counts twice, the identity, kind and source layer once each, and two
spellings of the same word meet only when they are the same word after case
folding. `search` is called with `mode` defaulting to `lexical`, so the vector
channel does not run.

Three things were wrong with that, and only the first is about ranking.

1. Nothing named the comparison. The way a request was compared with an item
   lived in the argument defaults of a retrieval call, so it could not be
   stated, changed or measured. The rule in this repository since 18 September
   is that every contract names its matching mode.
2. Nothing measured the result. A count of passing checks is not a working
   customer journey, and the catalogue's own query file is a smoke check whose
   expected answers were written into the item purposes.
3. The index was rebuilt on every request. One search over a catalogue that
   changed for nobody read every item, built a full text index and threw it
   away.

## What it does now

`core.harness_intelligence_search` holds one typed contract,
`CatalogueSearchPolicy`, and the search reads only what that policy declares.

```text
Catalogue search policy
├── Match mode, strict to open, from core.contract_matching
│   ├── exact             the words meet letter for letter, case included
│   ├── canonical         lower case, straight quotes, single spaces
│   ├── purpose           canonical, plus one general spelling and plural fold
│   ├── semantic_blocked  purpose, with declared tag dimensions equal exactly
│   │                     and a coverage floor below which nothing is returned
│   └── model_judged      beyond deterministic reach; names the judgment
│                         contract a separate step must answer, and ranks nothing
├── Fields read, each with a whole number weight
│   └── identity, purpose, kind, source_layer, tags, styles
├── Retrieval mode: lexical, vector or hybrid
├── Common term ceiling: a word most of the catalogue holds separates nothing
└── Coverage floor: how much of the request an item must hold to be returned
```

Every searchable field is named in a policy, and a weight of zero records that
the field was considered and is deliberately not read. A policy grants nothing:
it never loads a body, never changes an item and never decides that an item may
be disclosed. `core.provisioning_server` still settles that, and the search
only orders references the caller is already allowed to see.

`PreparedCatalogueSearch` builds one policy's reading of one set of items once
and answers many requests from it. Because blocking happens before anything is
ranked, a prepared search is bound to the exact tag request it was prepared for
and refuses any other rather than quietly answering for it.

## The measurement

- Population: 354 requests, each with the catalogue items that should be
  returned for it, in `examples/30_search_quality/relevance-judgements.json`.
- Catalogue: the 123 published items of
  `examples/29_intelligence_service/starter-catalogue` on 21 September 2026.
- Every catalogue item is expected by at least one request, and by at least one
  written for this measurement, so no item is measured only by the group that
  was fitted to it.
- Ten of the 354 requests are ones this catalogue cannot answer. They are kept
  so that a confident wrong answer is visible rather than invisible.

The requests come from two groups, reported separately.

| Group | Count | What it is worth |
|---|---|---|
| `starter_catalogue_search_queries/v1` | 105 | Not independent. The catalogue's own `REVIEW.md` records that item purposes were given the words these queries used until every one passed. A good score means the smoke check still works. |
| `written_for_this_measurement` | 249 | Written from each item's title and declared tags, in the words a customer's tool would send, before any ranking was measured against them. |

Each request carries `development` or `held_back`, decided from the text of the
request alone: the first eight hexadecimal characters of its SHA-256 digest,
read as a number, leave no remainder when divided by four. 261 are development
and 93 are held back. Policies were chosen by reading the development group
only. No result can move a request between the groups, and
`tools/test_search_quality.py` checks that the split still follows from the
text.

Reported for each policy: whether a wanted item appears at all, where it lands,
and the name of every request whose wanted item fell below the third position
or did not appear.

## The comparison

Fifteen policies over the same 354 requests, at depth twenty. The saved
report holds a sixteenth name, `default`, which is the same policy as the new
default row and is measured again under that name so a reader can see the two
agree. `devR@1` is the
share of answerable development requests whose wanted item came first,
`heldR@3` the share of held-back requests whose wanted item was in the first
three, `MRR` the mean reciprocal rank, `fails` the number of requests whose
wanted item was below third or missing, and `unansw` how many of the ten
unanswerable requests were answered with references anyway.

| Policy | devR@1 | heldR@1 | devR@3 | heldR@3 | devMRR | heldMRR | fails | unansw |
|---|---|---|---|---|---|---|---|---|
| served_before (the deployed search) | 0.694 | 0.630 | 0.833 | 0.837 | 0.772 | 0.737 | 57 | 10 |
| exact, purpose and identity | 0.667 | 0.630 | 0.802 | 0.826 | 0.749 | 0.733 | 66 | 10 |
| canonical, purpose only | 0.651 | 0.554 | 0.786 | 0.728 | 0.731 | 0.663 | 79 | 10 |
| canonical, purpose and identity | 0.694 | 0.630 | 0.829 | 0.837 | 0.772 | 0.738 | 58 | 10 |
| purpose fold, purpose only | 0.663 | 0.620 | 0.798 | 0.783 | 0.741 | 0.718 | 71 | 10 |
| **purpose fold, purpose and identity (the new default)** | **0.694** | **0.707** | **0.849** | **0.848** | **0.778** | **0.783** | **52** | **10** |
| purpose fold, with declared tags | 0.691 | 0.707 | 0.849 | 0.848 | 0.776 | 0.783 | 52 | 10 |
| purpose fold, with tags, kind and source layer | 0.691 | 0.696 | 0.849 | 0.848 | 0.775 | 0.777 | 52 | 10 |
| purpose fold, identity weighted above purpose | 0.710 | 0.674 | 0.821 | 0.870 | 0.779 | 0.774 | 57 | 10 |
| purpose fold, common term ceiling one fifth | 0.687 | 0.674 | 0.849 | 0.848 | 0.770 | 0.769 | 52 | 10 |
| semantic blocked on language, floor one fifth | 0.691 | 0.707 | 0.841 | 0.804 | 0.771 | 0.765 | 58 | 10 |
| purpose fold, coverage floor one fifth | 0.694 | 0.707 | 0.841 | 0.804 | 0.773 | 0.765 | 58 | 10 |
| purpose fold, coverage floor three tenths | 0.691 | 0.685 | 0.818 | 0.794 | 0.757 | 0.738 | 65 | 8 |
| purpose fold, coverage floor two fifths | 0.643 | 0.620 | 0.706 | 0.707 | 0.675 | 0.658 | 101 | 8 |
| purpose fold, coverage floor one half | 0.568 | 0.522 | 0.587 | 0.587 | 0.578 | 0.550 | 142 | 4 |

The baseline row is not an invented straw man.
`tools/test_search_quality.py` builds the records exactly as
`ServiceHttpApplication._search` builds them, hands them to the same
retrieval engine, and requires the same first three as the baseline policy
for all 354 requests. A policy that reads fewer fields fails that same
comparison, which is what makes it worth running. Two limits are worth
stating: the comparison uses a copy of that method's record construction read
from the source on 21 September 2026, not a call to the running service, and
it compares the ordering only.

## What changed, and what the numbers say

The declared default is now the `purpose` match mode reading the purpose twice
and the identity once.

- Against the deployed search, the held-back requests gained most: first
  position 0.630 to 0.707, and mean reciprocal rank 0.737 to 0.783. On the
  development requests the same change gained 0.833 to 0.849 at three and
  0.772 to 0.778 in mean reciprocal rank.
- The gain is larger on the requests held back than on the requests the policy
  was chosen from. So this is not a fit to the development set. It is the
  opposite of the failure that holding back is there to catch.
- Reading the identity as well as the purpose is worth more than the fold.
  Purpose alone reaches 0.798 at three; adding the identity reaches 0.849.
  Both matter: canonical with the identity reaches 0.829, the fold adds the
  rest.
- The strictest mode was measured rather than assumed. Exact, letter for
  letter with case, reaches 0.802 at three, below canonical with the identity
  and well below the fold. It does better than it should, and the reason is
  worth knowing: this catalogue's identities are already lower case with
  underscores, and only the first word of each purpose is capitalised, so the
  two sides happen to agree on case most of the time. A catalogue whose items
  carried ordinary capitalised titles would punish exact matching much harder.
  It is not the mode to declare for a search.
- The declared tags, the kind and the source layer were measured and are not
  read. All 123 items declare exactly the same two tags, `lifecycle` candidate
  and `language` English, all 123 are the kind skill, and the source layer has
  only two values across them, 102 and 21. A field every item answers the same
  way separates nothing and slightly dilutes the words that do. They are
  declared at weight zero, which records that they were considered. Re-measure
  when the catalogue carries tags that differ between items.
- A coverage floor was measured at four settings. It is not worth it at this
  catalogue size: a floor of one half silences six of the ten requests the
  catalogue cannot answer but drops recall at three from 0.849 to 0.587, and a
  floor of one fifth silences none of them while already dropping held-back
  recall at three from 0.848 to 0.804. The default carries no floor.
- The change is not free. It fixed twelve requests the deployed search failed
  and broke seven it answered, for a net five. The seven are named in the
  section below.

## The two groups of requests do not agree, and that is the point

The same default policy, on the same catalogue, scores very differently
depending on who wrote the request.

| Group | Requests | recall at 1 | recall at 3 | mean reciprocal rank |
|---|---|---|---|---|
| `starter_catalogue_search_queries/v1` | 105 | 0.838 | 0.990 | 0.906 |
| `written_for_this_measurement` | 239 answerable | 0.636 | 0.787 | 0.724 |

The first row is the catalogue's own smoke check, whose expected answers were
written into the item purposes. Reading only that row would say search finds
the right item 99 times in 100. The second row is what happens when the
request was written from the item's title rather than into its purpose: the
right item is first for roughly six requests in ten. Fifty-one of the
fifty-two failures are in the second group and one is in the first. A count of
passing checks is not a working customer journey.

## Which requests fail

All fifty-two are in the saved report and are printed by
`measure.py --policy default --failures`. Fifteen of them return the wanted
item nowhere in the first twenty. Three patterns account for most of them.

1. A near neighbour wins. The catalogue now holds several items that answer
   nearly the same need, for example reviewing a change for correctness beside
   reviewing a change for what is missing. The request `break a big job into
   pieces that can run in parallel` expects
   `plan_and_split_work_with_explicit_joins`, which comes back tenth, and gets
   `split_a_large_request_into_assignable_parts` first. A reviewer might accept
   that answer. The judgements were written before any ranking was measured and
   have not been revised afterwards, because revising an expectation to match a
   result is how a measurement stops measuring anything.
2. The request and the purpose share no word. `tidy up the homepage column`
   expects the item about website addresses, whose purpose never says homepage.
   No amount of folding reaches that; it needs either a word in the purpose or
   a comparison beyond the lexical one.
3. A common word carries the request. `the app feels slow where do i even
   start` matches every item that mentions time or speed. The common term
   ceiling was measured as a remedy and made the numbers slightly worse.

The seven requests the change broke, all of which the deployed search answered
within the first three: `group the mistakes into types`, `half the writes went
through and half did not`, `remove weird invisible characters from my data`,
`telephone numbers are in ten different formats`, `the same customer is in both
the training and the test set`, `when is a fix safe enough to apply without a
person`, and `works on my machine but fails on the server`.

## What is still wrong

1. All ten requests this catalogue cannot answer are still answered with
   references, by every policy that carries no coverage floor and by the
   lowest floor. A floor of three tenths or two fifths silences two of the
   ten, and a floor of one half silences six, and each costs far more recall
   than it saves. This is an open finding, not a solved problem. A request the
   catalogue cannot serve should be answered with an explicit nothing, and the
   deterministic instrument for that has not been found yet.
2. Fifty-two of the 344 answerable requests still fail: the wanted item is
   below third or absent, and fifteen of those return it nowhere in the first
   twenty. They are named above and in the saved report.
3. The hosted service does not use this contract yet.
   `ServiceHttpApplication._search` still builds its own records and calls the
   retrieval engine directly, so the deployed behaviour is the baseline row,
   not the default row. Wiring it is a change inside `core.service_runtime`,
   which this work did not touch.

## Running it

```bash
python examples/30_search_quality/run.py
python examples/30_search_quality/measure.py
python examples/30_search_quality/measure.py --policy default --failures
PYTHONPATH=src:tools python -m unittest tools.test_search_quality -v
```

The measurement calls no model, needs no network access and loads no body.
