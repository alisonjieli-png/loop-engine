# Measure whether catalogue search returns the right references

Kind: executable local measurement. No provider account, model key or network
access is needed. Nothing is deployed and no body is loaded.

A customer's coding tool asks the hosted service for what one step needs and
reads the first few references. If the wrong three come back, every later step
is worse. This example measures how often the right reference comes back and
where in the order it lands, over the starter catalogue in
`examples/29_intelligence_service/starter-catalogue`.

## Run it

```bash
python examples/30_search_quality/run.py
python examples/30_search_quality/measure.py
python examples/30_search_quality/measure.py --policy default --failures
```

`run.py` runs the measurement and checks what it reports: every catalogue item
is asked for, the declared default beats the deployed search on the requests
held back, the requests this catalogue cannot answer are counted, and every
failure names the request. It exits non-zero when one of those stops holding.

`measure.py` with no arguments compares every named policy and prints the
table. With `--policy default --failures` it runs one policy and prints every
query it failed, by name. Add `--report <path>` to save the whole comparison,
including each policy's failed queries and the requests this catalogue cannot
answer but answered anyway.

## What is measured

| File | What it holds |
|---|---|
| `relevance-judgements.json` | 354 requests and the catalogue items that should be returned for each |
| `measure.py` | the runner, the named policies compared, and the report |
| `run.py` | the example's own checks over what the measurement reports |
| `report-2026-09-21.json` | the saved comparison this repository's checks defend |

The numbers reported for each policy are:

- `found_at_all`, whether a wanted item appears anywhere in the first twenty.
- `recall_at_1`, `recall_at_3`, `recall_at_10`, whether it appears that high.
- `mean_reciprocal_rank`, one number for where it lands on average.
- `failed_queries`, every query whose wanted item was below the third position
  or missing, listed by name with what came back instead.
- `answered_confidently`, how many requests this catalogue cannot serve were
  answered with references anyway.

An average hides failures, so the failing queries are listed rather than
counted. `measure.py --failures` prints them.

## Where the judgements come from

```text
relevance-judgements.json
├── starter_catalogue_search_queries/v1   105 queries, taken unchanged from the
│   ├── written by the author of the item purposes           catalogue's own file
│   └── written by an adversarial reviewer after the purposes existed
└── written_for_this_measurement          249 queries written from the titles
    ├── one to four per catalogue item, usually two, in the words a
    │   customer's tool would send
    └── ten requests this catalogue cannot answer, kept so that a confident
        wrong answer is visible rather than invisible
```

The first group is not independent evidence and is reported separately. The
starter catalogue's own `REVIEW.md` records that the item purposes were given
the words those queries used until every one passed, so a good score on them
says the smoke check still works, not that search is good. The second group was
written from each item's title and declared tags before any ranking was
measured against it, by the engineering session of 21 September 2026, which
wrote no item purpose and changed no catalogue item.

Every catalogue item is expected by at least one query in the second group, so
no item is measured only by the group that was fitted to it.

## The split that keeps the comparison honest

Each query carries `development` or `held_back`, decided from the text of the
query itself: the first eight hexadecimal characters of its SHA-256 digest,
read as a number, leave no remainder when divided by four. A policy is chosen
by reading the development group. The held-back group is reported beside it. No
result can move a query between the groups, and the rule is checked in
`tools/test_search_quality.py`.

Of the 354 queries, 261 are development and 93 are held back.

## What the measurement is not

This is a ranking measurement over a fixed set of queries. It is not a
full-system Loop Engine benchmark: no task population runs, no model is
called, nothing is executed, nothing is accepted and no cost is incurred. It
answers one question about one ordering. The items themselves remain
candidates until an independent review approves them.
